"""
mathhead.discovery.product — the single-door product API (v3P0 + v4F1 + v4F2): `check(statement)`.

The product promise: bring your conjecture — the engine refutes it (with a witness), proves it (with a
kernel proof), or tells you exactly how far it survived. One call, one honest envelope:

    >>> check("6 | n^3 - n")                      # → proved, kernel_verified, proof hash
    >>> check("5 | n^3 - n")                      # → refuted, witness n=2 (value 6 ≢ 0 mod 5)
    >>> check("n^2 + n ≡ 0 (mod 2)")              # → proved, kernel_verified (reduce to 2 | p−q)
    >>> check("sum_(i=1..n) i = n*(n+1)/2")       # → proved, kernel_verified (SumInduction)
    >>> check("sum_(i=1..n) i <= n^2")            # → proved, solver_verified (kernel closed form + z3)
    >>> check("num_triangles <= num_edges")       # → refuted, smallest graph witness in hand
    >>> check("sum_degrees == 2*num_edges")       # → open (equality NEVER 'proved' from a finite scan)
    >>> check("clique_number <= chromatic_number")  # → open, no counterexample up to the stated bound

Supported statement forms (the v4F2 product surface — parsed deterministically, never guessed):
  * modular:      "m | poly(n)"  or  "m divides poly(n)"
  * congruence:   "p(n) ≡ q(n) (mod m)"  or ASCII  "p(n) = q(n) mod m"   (reduced to m | (p−q);
                  integer-coefficient polynomials in n only — anything else is an honest refusal)
  * sum identity: "sum_(i=1..n) f(i) = g(n)"   (f in i, g in n; rational closed forms fine)
  * sum bound:    "sum_(i=1..n) f(i) <= g(n)"  or ">="  — smallest-n witness first; survivors get a
                  proof ATTEMPT: kernel-verified closed form, then the z3 real-relaxation (n ≥ 1 real
                  ⇒ n ≥ 1 integer — the SOUND direction; a real counterexample is NOT a witness, but
                  an INTEGER z3 hint is re-verified by exact arithmetic and only then refutes)
  * graph bound:  "invA <= [k*]invB [+ c]", the mirrored ">=", and equalities "invA == [k*]invB [+ c]"
                  over the rich+classic invariants, checked counterexample-first on ALL connected
                  graphs up to `max_n` (an equality that survives is OPEN, never proved). The
                  quantifier domain of such a claim is AMBIGUOUS, so the envelope additionally
                  carries `readings`: formalize's three candidate readings (A connected — the main
                  verdict itself / B all graphs incl. disconnected / C fixed order n = max_n), each
                  with its own honest verdict and tier — the answer to "is it true?" can genuinely
                  depend on which question the text is asking, and the envelope says so
  * permutation:  "all perms of n: invA <= invB" (also ">=" / "==") over inversions, descents,
                  major_index, fixed_points, cycles (alias num_cycles); the right side may instead
                  be an exact-rational
                  expression in n ("all perms of n: inversions <= n*(n-1)/2"). ALL of S_1..S_cap is
                  scanned (cap = min(max_n, 7) — the honest n! wall); a violation refutes with the
                  permutation in hand; a survivor is OPEN — a finite scan never proves the claim
  * partitions:   "partitions(n, odd) == partitions(n, distinct)" over the filters odd | distinct |
                  all — both counts exhaustively compared for every n <= 20; equal counts stay OPEN
                  (for the odd/distinct pair the engine additionally verifies Glaisher's constructive
                  bijection per n — still not a universal machine proof, and it says so)
  * compositions: "compositions(n) == g(n)" — the exact count vs the formula for every n <= 12; when
                  g(n) is 2^(n-1) the engine re-verifies the cut-point bijection per n (same honesty)
Anything else → verdict "unsupported" with the recognized structure + suggested instruments (X2 map) —
an honest refusal, never a fabricated answer. Route-wide guard: any numeric constant (literal or
evaluated) beyond 4000 digits is refused up front — CPython's int↔str conversion raises past ~4300
digits, and the engine refuses rather than crashes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_SUM_WITNESS_BOUND = 40          # smallest-n witness scan bound for comparative sum inequalities
_DIRECT_SUM_BOUND = 10_000       # up to here, integer hints are re-verified by DIRECT summation
_MAX_MODULUS = 10**6             # residue exhaustion beyond this is an honest refusal, not a hang
_MAX_CONST_DIGITS = 4000         # constants beyond this many digits are refused ROUTE-WIDE:
_CONST_LIMIT = 10 ** _MAX_CONST_DIGITS   # CPython int↔str conversion raises past ~4300 digits,
                                 # so the engine refuses up front — never a crash (v4F2)
_OVERSIZED = (f"a numeric constant exceeds {_MAX_CONST_DIGITS} digits — refused up front "
              "(CPython int↔str conversion overflows past ~4300 digits)")


@dataclass
class CheckResult:
    statement: str
    structure: str
    verdict: str                 # "proved" | "refuted" | "open" | "unsupported"
    tier: str                    # the epistemic tier of the verdict (the product's soul)
    witness: dict = field(default_factory=dict)
    checked_up_to: str = ""
    proof_hash: str = ""
    instruments: tuple = ()
    notes: str = ""
    # Quantifier-ambiguous graph bounds only: the THREE candidate readings (formalize's A/B/C —
    # A connected / B all graphs / C fixed order n), each with its OWN honest verdict and tier.
    # The main envelope above IS reading A (backward compatible: everything else is unchanged);
    # readings is ADDITIONAL information. Empty tuple for every other structure.
    readings: tuple = ()


def _oversized_constant(*exprs) -> bool:
    """True when any exact numeric atom in the given sympy expressions has more than
    _MAX_CONST_DIGITS digits (numerator or denominator) — the route-wide guard behind every
    'constant exceeds 4000 digits' refusal. Checked WITHOUT string conversion (bit-level)."""
    import sympy
    return any(abs(a.p) >= _CONST_LIMIT or a.q >= _CONST_LIMIT
               for expr in exprs for a in expr.atoms(sympy.Rational))


def _too_big(x) -> bool:
    """An EVALUATED exact value too large to print or certify (same guard, at evaluation time)."""
    import sympy
    try:
        r = sympy.Rational(x)
    except (TypeError, ValueError):
        return False
    return abs(r.p) >= _CONST_LIMIT or r.q >= _CONST_LIMIT


def _check_modular(stmt: str, m: int, expr: str) -> CheckResult:
    import sympy

    from .kernel import KernelError, prove_divides
    from .provenance import proof_hash as _hash
    if m < 1:
        return CheckResult(stmt, "modular_divisibility", "unsupported", "none",
                           instruments=("kernel.prove_divides",),
                           notes=f"the modulus must be a positive integer (got {m}) — "
                                 "the engine refuses to guess")
    if m > _MAX_MODULUS:
        return CheckResult(stmt, "modular_divisibility", "unsupported", "none",
                           instruments=("kernel.prove_divides",),
                           notes=f"residue exhaustion over {m} residues is infeasible; "
                                 "bound = 10^6 — the engine refuses to guess")
    try:
        expanded = sympy.expand(sympy.sympify(expr))
        if _oversized_constant(expanded):                          # v4F2: refusal, never a crash
            return CheckResult(stmt, "modular_divisibility", "unsupported", "none",
                               instruments=("kernel.prove_divides",),
                               notes=f"{_OVERSIZED} — the engine refuses to guess")
        poly = _int_poly_in_n(expanded)
    except (KernelError, sympy.SympifyError, sympy.PolynomialError, TypeError, ValueError) as exc:
        # v4F1 honesty fix: poly_from_sympy would silently int()-TRUNCATE rational coefficients
        # ("2 | n/2" became a FALSE kernel proof) and crash on foreign symbols. Refuse instead.
        return CheckResult(stmt, "modular_divisibility", "unsupported", "none",
                           instruments=("kernel.prove_divides",),
                           notes=f"could not read the right side as an integer-coefficient "
                                 f"polynomial in n ({exc}) — the engine refuses to guess")
    try:
        _thm, term = prove_divides(m, poly)
        return CheckResult(stmt, "modular_divisibility", "proved", "kernel_verified",
                           checked_up_to="all integers n (universal proof)", proof_hash=_hash(term),
                           instruments=("kernel.prove_divides",),
                           notes="proved by residue exhaustion/CRT in the LCF-style kernel")
    except KernelError:
        from .nt_chain import walk_divisibility_chain
        walk = walk_divisibility_chain(m, poly, "forall")
        bad = next(r for r, v in enumerate(walk.residue_table) if v != 0)
        return CheckResult(stmt, "modular_divisibility", "refuted", "exact_integer_certificate",
                           witness={"n": bad, "value_mod_m": walk.residue_table[bad]},
                           checked_up_to="decided exactly (finite residue table)",
                           instruments=("nt_chain.walk_divisibility_chain",),
                           notes=f"residue n≡{bad} (mod {m}) gives a nonzero value — the claim is false")


# --- polynomial congruence: p(n) ≡ q(n) (mod m)  /  ASCII: p(n) = q(n) mod m --------------------

_CONG = re.compile(r"^\s*(.+?)\s*(?:≡|=)\s*(.+?)\s*(?:\(\s*mod\s+(\d+)\s*\)|mod\s+(\d+))\s*$")


def _cong_unsupported(stmt: str, why: str) -> CheckResult:
    return CheckResult(stmt, "polynomial_congruence", "unsupported", "none",
                       instruments=("kernel.prove_divides",),
                       notes=f"{why} — the congruence surface covers integer-coefficient "
                             "polynomials in n only; the engine refuses to guess")


def _int_poly_in_n(expr) -> tuple:
    """sympy expr → kernel integer-coefficient poly tuple (low→high). Raises KernelError when the
    expression is not a univariate integer-coefficient polynomial in n (poly_from_sympy would
    silently TRUNCATE rationals via int() — this bridge refuses instead)."""
    import sympy

    from .kernel import KernelError, _norm
    n = sympy.Symbol("n")
    if expr.free_symbols - {n}:
        raise KernelError(f"free symbols other than n: {expr.free_symbols - {n}}")
    poly = sympy.Poly(sympy.expand(expr), n)
    coeffs = list(reversed(poly.all_coeffs()))
    if not all(c.is_integer for c in coeffs):
        raise KernelError("non-integer coefficients")
    return _norm(tuple(int(c) for c in coeffs))


def _check_congruence(stmt: str, lhs: str, rhs: str, m: int) -> CheckResult:
    import sympy

    from .kernel import KernelError, prove_divides
    from .provenance import proof_hash as _hash
    if m < 1:
        return _cong_unsupported(stmt, f"modulus must be a positive integer (got {m})")
    if m > _MAX_MODULUS:
        return _cong_unsupported(stmt, f"residue exhaustion over {m} residues is infeasible; "
                                       "bound = 10^6")
    try:
        p = sympy.expand(sympy.sympify(lhs))
        q = sympy.expand(sympy.sympify(rhs))
        if _oversized_constant(p, q):                              # v4F2: refusal, never a crash
            return _cong_unsupported(stmt, _OVERSIZED)
        p_poly, q_poly = _int_poly_in_n(p), _int_poly_in_n(q)   # noqa: F841 — validates BOTH sides
        d_poly = _int_poly_in_n(p - q)
    except (KernelError, sympy.SympifyError, sympy.PolynomialError, TypeError, ValueError) as exc:
        return _cong_unsupported(stmt, f"could not read both sides as integer-coefficient "
                                       f"polynomials in n ({exc})")
    try:
        _thm, term = prove_divides(m, d_poly)
        return CheckResult(stmt, "polynomial_congruence", "proved", "kernel_verified",
                           checked_up_to="all integers n (universal proof)", proof_hash=_hash(term),
                           instruments=("kernel.prove_divides",),
                           notes=f"reduced to {m} | (p − q), then proved by residue exhaustion/CRT "
                                 "in the LCF-style kernel")
    except KernelError:
        from .nt_chain import walk_divisibility_chain
        walk = walk_divisibility_chain(m, d_poly, "forall")
        nsym = sympy.Symbol("n")
        bad = next(r for r, v in enumerate(walk.residue_table) if v != 0)
        return CheckResult(stmt, "polynomial_congruence", "refuted", "exact_integer_certificate",
                           witness={"n": bad, "lhs_mod_m": int(p.subs(nsym, bad)) % m,
                                    "rhs_mod_m": int(q.subs(nsym, bad)) % m,
                                    "difference_mod_m": walk.residue_table[bad]},
                           checked_up_to="decided exactly (finite residue table)",
                           instruments=("nt_chain.walk_divisibility_chain",),
                           notes=f"residue n≡{bad} (mod {m}): the two sides differ mod {m} — "
                                 "the claim is false")


def _check_sum(stmt: str, f_expr: str, g_expr: str) -> CheckResult:
    import sympy

    from .kernel import KernelError, poly_from_sympy_q, prove_sum_identity
    from .provenance import proof_hash as _hash
    i, n = sympy.Symbol("i"), sympy.Symbol("n")
    ff0, gg0 = sympy.sympify(f_expr), sympy.sympify(g_expr)
    if _oversized_constant(ff0, gg0):                              # v4F2: refusal, never a crash
        return CheckResult(stmt, "sum_identity", "unsupported", "none",
                           instruments=("kernel.prove_sum_identity",),
                           notes=f"{_OVERSIZED} — the engine refuses to guess")
    f_poly = poly_from_sympy_q(str(sympy.expand(ff0.subs(i, n))))
    g_poly = poly_from_sympy_q(str(sympy.expand(gg0)))
    try:
        _thm, term = prove_sum_identity(f_poly, g_poly)
        return CheckResult(stmt, "sum_identity", "proved", "kernel_verified",
                           checked_up_to="all n >= 1 (induction, kernel-checked)", proof_hash=_hash(term),
                           instruments=("kernel.prove_sum_identity",),
                           notes="base case + telescoping step verified as exact polynomial identities")
    except KernelError:
        ff = sympy.sympify(f_expr)
        gg = sympy.sympify(g_expr)
        acc = 0
        for k in range(1, 30):
            acc += ff.subs(i, k)
            if sympy.simplify(acc - gg.subs(n, k)) != 0:
                return CheckResult(stmt, "sum_identity", "refuted", "exact_integer_certificate",
                                   witness={"n": k, "lhs_sum": str(acc), "rhs": str(gg.subs(n, k))},
                                   instruments=("kernel.prove_sum_identity",),
                                   notes="smallest n where the two sides disagree — exact arithmetic")
        return CheckResult(stmt, "sum_identity", "open", "bounded_check",
                           checked_up_to="n <= 29 agree, but no kernel proof found",
                           notes="agreement without proof — honestly open")


# --- comparative sum inequality: sum_(i=1..n) f(i) <= g(n)  (and >=) ----------------------------

_SUM_INEQ = re.compile(r"^\s*sum_\(i=1\.\.n\)\s*(.+?)\s*(<=|>=)\s*(.+)$")


def _sum_closed_form(ff, partial_sums: list):
    """Kernel-verified closed form of Σ_{i=1..n} f(i) (or None): interpolate the exact partial sums,
    then let the kernel prove the SumInduction identity. Returns (closed_expr, proof_term) or None."""
    import sympy

    from .kernel import KernelError, poly_from_sympy_q, prove_sum_identity
    i, n = sympy.Symbol("i"), sympy.Symbol("n")
    try:
        f_poly = poly_from_sympy_q(str(sympy.expand(ff.subs(i, n))))
        n_pts = len(f_poly) + 2                     # deg(Σf) = deg(f) + 1 → deg(f)+2 points suffice
        pts = list(zip(range(1, n_pts + 1), partial_sums[:n_pts]))
        closed = sympy.expand(sympy.interpolate(pts, n))
        g_poly = poly_from_sympy_q(str(closed))
        _thm, term = prove_sum_identity(f_poly, g_poly)
        return closed, term
    except (KernelError, sympy.SympifyError, sympy.PolynomialError, TypeError, ValueError):
        return None


def _verify_integer_hint(ff, gg, rel, cand, closed):
    """z3's real counterexample, taken as a HINT only: if its n is an integer >= 1, re-verify the
    claimed violation by exact arithmetic (direct summation up to _DIRECT_SUM_BOUND; beyond that,
    exact evaluation of the kernel-verified closed form). Returns (n, lhs_exact, rhs_exact, method)
    for a GENUINE violation, else None — a non-integer or unconfirmed hint upgrades nothing."""
    import sympy
    if isinstance(cand, bool) or not isinstance(cand, (int, float)):
        return None
    if not float(cand).is_integer() or cand < 1:
        return None
    k0 = int(cand)
    i, n = sympy.Symbol("i"), sympy.Symbol("n")
    try:
        if k0 <= _DIRECT_SUM_BOUND:
            lhs = sum((ff.subs(i, j) for j in range(1, k0 + 1)), sympy.Integer(0))
            method = "direct exact summation"
        else:
            lhs = closed.subs(n, k0)          # kernel-verified closed form, exact rational eval
            method = "kernel-verified closed form, exact evaluation"
        rhs = gg.subs(n, k0)
        if _too_big(lhs) or _too_big(rhs):                # cannot print/certify → upgrades nothing
            return None
        delta = sympy.simplify(lhs - rhs)
        if not delta.is_number:
            return None
        violated = delta.is_positive if rel == "<=" else delta.is_negative
        if violated is not True:
            return None
        return k0, lhs, rhs, method
    except (sympy.SympifyError, TypeError, ValueError):
        return None


def _check_sum_inequality(stmt: str, f_expr: str, rel: str, g_expr: str) -> CheckResult:
    import sympy

    from .provenance import proof_hash as _hash
    i, n = sympy.Symbol("i"), sympy.Symbol("n")
    try:
        ff = sympy.sympify(f_expr)
        gg = sympy.sympify(g_expr)
    except (sympy.SympifyError, TypeError, ValueError) as exc:
        return CheckResult(stmt, "sum_inequality", "unsupported", "none",
                           notes=f"could not parse the two sides ({exc}) — the engine refuses to guess")
    if _oversized_constant(ff, gg):                                # v4F2: refusal, never a crash
        return CheckResult(stmt, "sum_inequality", "unsupported", "none",
                           notes=f"{_OVERSIZED} — the engine refuses to guess")
    # 1) smallest-n witness search, exact arithmetic
    acc, sums = sympy.Integer(0), []
    for k in range(1, _SUM_WITNESS_BOUND + 1):
        acc = acc + ff.subs(i, k)
        sums.append(acc)
        if _too_big(acc) or _too_big(gg.subs(n, k)):               # evaluated blow-up: refuse too
            return CheckResult(stmt, "sum_inequality", "unsupported", "none",
                               notes=f"{_OVERSIZED.replace('a numeric constant', 'an evaluated value')}"
                                     f" at n={k} — the engine refuses to guess")
        delta = sympy.simplify(acc - gg.subs(n, k))          # LHS − RHS at n=k
        if not delta.is_number:
            return CheckResult(stmt, "sum_inequality", "unsupported", "none",
                               notes="the sides did not evaluate to numbers (stray free symbols?) — "
                                     "the engine refuses to guess")
        violated = delta.is_positive if rel == "<=" else delta.is_negative
        if violated is None:                                  # sign not decidable exactly → refuse
            return CheckResult(stmt, "sum_inequality", "unsupported", "none",
                               notes=f"could not decide the exact sign of LHS−RHS at n={k} — "
                                     "the engine refuses to guess")
        if violated:
            return CheckResult(stmt, "sum_inequality", "refuted", "exact_integer_certificate",
                               witness={"n": k, "lhs_sum": str(acc), "rhs": str(gg.subs(n, k))},
                               checked_up_to=f"smallest violating n found at n={k}",
                               instruments=("exact partial-sum scan",),
                               notes="smallest n where the inequality fails — exact arithmetic")
    # 2) no witness → proof ATTEMPT: kernel closed form for Σf, then z3 over the reals (n ≥ 1).
    #    Real-relaxation soundness: valid for all real n ≥ 1 ⇒ valid for all integer n ≥ 1.
    scanned = f"no counterexample among n <= {_SUM_WITNESS_BOUND} (exact scan)"
    cf = _sum_closed_form(ff, sums)
    if cf is None:
        return CheckResult(stmt, "sum_inequality", "open", "no_counterexample_within_bound",
                           checked_up_to=scanned,
                           instruments=("exact partial-sum scan",),
                           notes="no kernel-verified polynomial closed form for the sum — no proof "
                                 "route; NOT proved, honestly open")
    closed, term = cf
    diff = sympy.expand(gg - closed) if rel == "<=" else sympy.expand(closed - gg)
    from mathhead.core.inequality import prove_inequality
    res = prove_inequality(f"({diff}) >= 0", assumptions=["n >= 1"])
    if res.status == "valid":
        return CheckResult(stmt, "sum_inequality", "proved", "solver_verified",
                           checked_up_to="all integers n >= 1 (closed form + real-relaxation proof)",
                           instruments=("kernel.prove_sum_identity", "core.inequality.prove_inequality"),
                           notes=f"closed form kernel_verified; inequality step z3 — chain: "
                                 f"sum = {closed} (kernel hash {_hash(term)}); then "
                                 f"({diff}) >= 0 for all REAL n >= 1 (z3 NRA), which covers "
                                 "the integers")
    if res.status == "invalid":
        # The real model is only a HINT. If it lands on an integer n >= 1, re-verify the violation
        # by EXACT arithmetic, independently of z3 — only then is it a refutation.
        upgraded = _verify_integer_hint(ff, gg, rel, (res.witness or {}).get("n"), closed)
        if upgraded is not None:
            k0, lhs_exact, rhs_exact, method = upgraded
            return CheckResult(stmt, "sum_inequality", "refuted", "exact_integer_certificate",
                               witness={"n": k0, "lhs_sum": str(lhs_exact), "rhs": str(rhs_exact),
                                        "exact": method},
                               checked_up_to=f"violation at n={k0} verified exactly; "
                                             f"no violation among n <= {_SUM_WITNESS_BOUND}",
                               instruments=("core.inequality.prove_inequality",
                                            "exact integer re-verification"),
                               notes="z3 proposed the integer point; the violation was re-verified "
                                     "by exact arithmetic with no solver in the loop (not "
                                     "necessarily the smallest witness)")
        return CheckResult(stmt, "sum_inequality", "open", "no_counterexample_within_bound",
                           checked_up_to=scanned,
                           instruments=("kernel.prove_sum_identity", "core.inequality.prove_inequality"),
                           notes=f"closed form kernel_verified (sum = {closed}) but z3 found a REAL "
                                 f"counterexample {res.witness} — a real counterexample is NOT an "
                                 "integer witness, so the claim is neither proved nor refuted here; "
                                 "honestly open")
    if res.status == "error":
        return CheckResult(stmt, "sum_inequality", "open", "no_counterexample_within_bound",
                           checked_up_to=scanned,
                           instruments=("kernel.prove_sum_identity", "core.inequality.prove_inequality"),
                           notes=f"closed form kernel_verified (sum = {closed}) but the inequality "
                                 f"step was rejected by the z3 grammar/parse layer "
                                 f"({res.explanation}) — no proof route; NOT proved, honestly open")
    return CheckResult(stmt, "sum_inequality", "open", "no_counterexample_within_bound",
                       checked_up_to=scanned,
                       instruments=("kernel.prove_sum_identity", "core.inequality.prove_inequality"),
                       notes=f"closed form kernel_verified (sum = {closed}) but the z3 NRA solver "
                             "could not decide the inequality step (solver unknown) — "
                             "NOT proved, honestly open")


# --- graph invariant bounds and equalities ------------------------------------------------------

_GRAPH_STMT = re.compile(r"^\s*(\w+)\s*(<=|>=|==|=)\s*(?:(\d+)\s*\*\s*)?(\w+)\s*(?:\+\s*(\d+))?\s*$")


def graph_statement_grammar():
    """The ONE compiled grammar of the graph-bound surface `invA <= / >= / == [k*]invB [+ c]`.
    Every consumer (this route and formalize's candidate builder) matches against this same
    object, so the two surfaces are structurally incapable of drifting apart."""
    return _GRAPH_STMT


def graph_invariant_registry() -> dict:
    """The invariant registry the graph-bound route resolves names against (rich + classic +
    the report extras) — shared with formalize so every candidate reading sees the SAME names."""
    from .conjecture_service import service_invariants
    from .invariants import evaluate as _ev
    invs = dict(service_invariants())
    for extra in ("num_vertices", "num_triangles", "sum_degrees", "num_components"):
        invs.setdefault(extra, lambda g, _x=extra: _ev(g, _x))
    return invs


def _reading_summary(r: CheckResult) -> str:
    """One compact line of evidence for a reading: the witness values for a refutation (edges
    elided — the count is enough at a glance; the full object rides `formalize()`), the stated
    scan bound otherwise. Nothing is invented — every field comes off the reading's envelope."""
    if r.witness:
        vals = ", ".join(f"{k}={v}" for k, v in r.witness.items() if k != "edges")
        edges = r.witness.get("edges")
        out = (f"counterexample: {vals}"
               + (f" ({len(edges)} edges)" if isinstance(edges, list) else ""))
        # diameter/radius return the DOCUMENTED -1 sentinel on disconnected graphs (see
        # rich_invariants) — a refutation riding that value is an artifact of the convention,
        # not a fact about graphs, and the summary must say so.
        if any(k not in ("n", "edges") and v == -1 for k, v in r.witness.items()):
            out += (" — disconnected sentinel: the refutation is definitional "
                    "(invariant = -1 on a disconnected graph), not graph-theoretic")
        return out
    return r.checked_up_to


def _attach_readings(res: CheckResult, stmt: str, max_n: int) -> CheckResult:
    """The quantifier ambiguity, surfaced ON the product envelope: attach formalize's three
    candidate readings (A connected / B all graphs / C fixed order n = max_n), each evaluated
    honestly through formalize's own path. Reading A is BY CONSTRUCTION the main envelope
    (candidate A delegates to check()'s semantics), so it is reused, not recomputed — no extra
    scan, no recursion. The main verdict/tier/witness stay exactly reading A; the tiers inside
    readings are formalize's own honest tiers, never upgraded here."""
    from .formalize import (_MAX_ORDER, candidate_formalizations, differences,
                            evaluate_candidate)
    if not 2 <= max_n <= _MAX_ORDER:
        res.notes += (f"; quantifier readings not evaluated: max_n={max_n} is outside the "
                      f"formalization wall 2 <= max_n <= {_MAX_ORDER}")
        return res
    cands = candidate_formalizations(stmt, max_n=max_n, fixed_n=max_n)
    deltas = {d["pair"][1]: d for d in differences(cands) if d["pair"][0] == "A"}
    readings, verdicts = [], []
    for cand in cands:
        r = res if cand.label == "A" else evaluate_candidate(cand)
        if cand.label == "A":
            delta = "check()'s own reading (baseline)"
        else:
            d, parts = deltas[cand.label], []
            if d["only_first"]:
                parts.append("drops [" + ", ".join(d["only_first"]) + "]")
            if d["only_second"]:
                parts.append("adds [" + ", ".join(d["only_second"]) + "]")
            delta = "vs A: " + "; ".join(parts)
        verdicts.append(r.verdict)
        readings.append({
            "label": cand.label,
            "statement_formal": f"for all G in [{cand.domain}]: {cand.statement}",
            "assumption_delta": delta,
            "verdict": r.verdict,
            "tier": r.tier,
            "witness_summary": _reading_summary(r),
        })
    res.readings = tuple(readings)
    if len(set(verdicts)) > 1:
        split = ", ".join(f"{e['label']}: {e['verdict']}" for e in readings)
        res.notes += (f"; quantifier ambiguity: the verdict CHANGES with the reading "
                      f"({split}) — the answer depends on which question the statement is "
                      "asking; see readings")
    else:
        res.notes += (f"; quantifier ambiguity: 3 readings evaluated — all agree "
                      f"({verdicts[0]}); see readings")
    return res


def _check_graph_bound(stmt: str, max_n: int) -> CheckResult | None:
    res = _graph_bound_verdict(stmt, max_n)
    return res if res is None else _attach_readings(res, stmt, max_n)


def _graph_bound_verdict(stmt: str, max_n: int) -> CheckResult | None:
    m = graph_statement_grammar().match(stmt)
    if not m:
        return None
    lhs, rel, k, rhs, c = (m.group(1), m.group(2), int(m.group(3) or 1),
                           m.group(4), int(m.group(5) or 0))
    rel = "==" if rel == "=" else rel
    structure = "graph_equality" if rel == "==" else "graph_inequality"
    invs = graph_invariant_registry()
    if lhs not in invs or rhs not in invs:
        return None
    from .nauty_scale import geng_available, geng_graphs
    if geng_available():
        graphs = [g for n in range(2, max_n + 1) for g in geng_graphs(n, connected=True)]
    else:
        from .generate import generate_graphs
        from .invariants import evaluate
        graphs = [g for n in range(2, max_n + 1) for g in generate_graphs(n)
                  if evaluate(g, "num_components") == 1]
    holds = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b}[rel]
    checked = 0
    for g in graphs:
        va, vb = invs[lhs](g), invs[rhs](g)
        checked += 1
        if not holds(va, k * vb + c):
            return CheckResult(stmt, structure, "refuted", "exact_integer_certificate",
                               witness={"n": g.n, "edges": sorted(g.edges), lhs: va, rhs: vb},
                               checked_up_to=f"first counterexample among connected graphs, n={g.n}",
                               instruments=("counterexample-first scan",),
                               notes="smallest-order witness; values computed exactly"
                                     + ("" if rel != "==" else
                                        " (equality broken — either direction convicts)"))
    if rel == "==":
        return CheckResult(stmt, structure, "open", "no_counterexample_within_bound",
                           checked_up_to=f"ALL {checked} connected graphs with 2 <= n <= {max_n}",
                           instruments=("counterexample-first scan",),
                           notes=f"universal claim not proved; holds for all connected graphs up to "
                                 f"n={max_n} — a finite scan NEVER proves an equality")
    return CheckResult(stmt, structure, "open", "no_counterexample_within_bound",
                       checked_up_to=f"ALL {checked} connected graphs with 2 <= n <= {max_n}",
                       instruments=("counterexample-first scan",),
                       notes="survived exhaustive small-order attack; NOT proved — honestly open")


# --- permutation invariant bounds: "all perms of n: invA <= invB-or-g(n)"  (v4F2) ---------------

_MAX_PERM_N = 7                  # the honest n! wall (7! = 5040); generate_permutations refuses beyond
_PERM_PREFIX = re.compile(r"^\s*all\s+perms\s+of\s+n\b")
_PERM_STMT = re.compile(r"^\s*all\s+perms\s+of\s+n\s*:\s*(\w+)\s*(<=|>=|==|=)\s*(.+?)\s*$")
_PERM_INVARIANT_NAMES = ("inversions", "descents", "major_index", "fixed_points",
                         "cycles (alias num_cycles)")


def _perm_invariants() -> dict:
    from . import permutations as perms
    return {"inversions": perms.inversions, "descents": perms.descents,
            "major_index": perms.major_index, "fixed_points": perms.fixed_points,
            "cycles": perms.num_cycles, "num_cycles": perms.num_cycles}


def _perm_unsupported(stmt: str, why: str) -> CheckResult:
    return CheckResult(stmt, "permutation_bound", "unsupported", "none",
                       instruments=("permutations.generate_permutations",),
                       notes=f"{why} — the permutation surface is 'all perms of n: "
                             "invA <= / >= / == invB-or-g(n)' with invariants "
                             f"{', '.join(_PERM_INVARIANT_NAMES)} and g(n) an exact-rational "
                             "expression in n; the engine refuses to guess")


def _check_perm_bound(stmt: str, max_n: int) -> CheckResult | None:
    if not _PERM_PREFIX.match(stmt):
        return None
    m = _PERM_STMT.match(stmt)
    if not m:
        return _perm_unsupported(stmt, "could not read the claim after 'all perms of n'")
    lhs, rel, rhs = m.group(1), "==" if m.group(2) == "=" else m.group(2), m.group(3)
    structure = "permutation_equality" if rel == "==" else "permutation_inequality"
    invs = _perm_invariants()
    if lhs not in invs:
        return _perm_unsupported(stmt, f"unknown left invariant '{lhs}'")
    rhs_fn, expr = invs.get(rhs), None
    if rhs_fn is None:
        import sympy
        nsym = sympy.Symbol("n")
        try:
            expr = sympy.expand(sympy.sympify(rhs))
        except (sympy.SympifyError, TypeError, ValueError) as exc:
            return _perm_unsupported(stmt, f"the right side is neither a known invariant nor a "
                                           f"readable expression in n ({exc})")
        if expr.free_symbols - {nsym}:
            return _perm_unsupported(stmt, f"the right side has free symbols other than n "
                                           f"({expr.free_symbols - {nsym}})")
        if _oversized_constant(expr):                              # v4F2: refusal, never a crash
            return _perm_unsupported(stmt, _OVERSIZED)
    from fractions import Fraction

    from .permutations import generate_permutations
    holds = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b}[rel]
    cap, checked = max(1, min(max_n, _MAX_PERM_N)), 0
    for k in range(1, cap + 1):
        rv = None
        if expr is not None:
            import sympy
            val = expr.subs(sympy.Symbol("n"), k)
            try:
                rat = sympy.Rational(val)
                rv = Fraction(int(rat.p), int(rat.q))
            except (TypeError, ValueError):
                return _perm_unsupported(stmt, f"the right side does not evaluate to an exact "
                                               f"rational at n={k}")
            if _too_big(rat):                                      # evaluated blow-up: refuse too
                return _perm_unsupported(stmt, _OVERSIZED + f" when evaluated at n={k}")
        for p in generate_permutations(k):
            la = invs[lhs](p)
            rb = invs[rhs](p) if rhs_fn is not None else rv
            checked += 1
            if not holds(la, rb):
                rb_out = rb if isinstance(rb, int) else (int(rb) if rb.denominator == 1 else str(rb))
                rhs_key = rhs if rhs_fn is not None else "rhs"      # expression key would collide w/ 'n'
                return CheckResult(stmt, structure, "refuted", "exact_integer_certificate",
                                   witness={"n": k, "perm": list(p.perm), lhs: la, rhs_key: rb_out},
                                   checked_up_to=f"first counterexample found in S_{k} "
                                                 f"(every permutation of every smaller n scanned)",
                                   instruments=("exhaustive S_n scan",),
                                   notes="explicit permutation witness (one-line notation); both "
                                         "sides recomputed exactly"
                                         + ("" if rel != "==" else
                                            " (equality broken — either direction convicts)"))
    if max_n < 1:
        capped = f" (max_n={max_n} < 1 clamped to n=1 — S_1 is the smallest scannable ensemble)"
    elif max_n > _MAX_PERM_N:
        capped = f" (scan honestly capped at n={_MAX_PERM_N}: n! growth)"
    else:
        capped = ""
    return CheckResult(stmt, structure, "open", "no_counterexample_within_bound",
                       checked_up_to=f"ALL {checked} permutations over every n <= {cap}{capped}",
                       instruments=("exhaustive S_n scan",),
                       notes="survived the exhaustive scan of every S_n up to the bound — a finite "
                             "scan never proves the universal claim; NOT proved, honestly open")


# --- partition counting identities: "partitions(n, odd) == partitions(n, distinct)"  (v4F2) -----

_PARTITION_ID_BOUND = 20         # p(20) = 627 — exhaustive per-n counting stays instant
_PART_PREFIX = re.compile(r"^\s*partitions\s*\(")
_PART_STMT = re.compile(r"^\s*partitions\s*\(\s*n\s*(?:,\s*(\w+)\s*)?\)\s*(?:==|=)\s*"
                        r"partitions\s*\(\s*n\s*(?:,\s*(\w+)\s*)?\)\s*$")


def _partition_filters() -> dict:
    from .partitions import into_distinct_parts, into_odd_parts
    return {"odd": into_odd_parts, "distinct": into_distinct_parts, "all": lambda _p: True}


def _part_unsupported(stmt: str, why: str) -> CheckResult:
    return CheckResult(stmt, "partition_count_identity", "unsupported", "none",
                       instruments=("partitions.generate_partitions",),
                       notes=f"{why} — the partition surface is exactly "
                             "'partitions(n, odd|distinct|all) == partitions(n, odd|distinct|all)' "
                             "('parts <= k' filters and closed-form right sides are NOT supported); "
                             "the engine refuses to guess")


def _check_partition_identity(stmt: str) -> CheckResult | None:
    if not _PART_PREFIX.match(stmt):
        return None
    m = _PART_STMT.match(stmt)
    if not m:
        return _part_unsupported(stmt, "could not read the statement as a two-sided partition count")
    fl, fr = (m.group(1) or "all"), (m.group(2) or "all")
    filters = _partition_filters()
    if fl not in filters or fr not in filters:
        bad = fl if fl not in filters else fr
        return _part_unsupported(stmt, f"unknown partition filter '{bad}'")
    from .partitions import generate_partitions
    for k in range(1, _PARTITION_ID_BOUND + 1):
        parts = generate_partitions(k)
        a = sum(1 for p in parts if filters[fl](p))
        b = sum(1 for p in parts if filters[fr](p))
        if a != b:
            return CheckResult(stmt, "partition_count_identity", "refuted",
                               "exact_integer_certificate",
                               witness={"n": k, f"count_{fl}": a, f"count_{fr}": b},
                               checked_up_to=f"smallest n where the two counts differ (n={k})",
                               instruments=("exhaustive partition counting",),
                               notes=f"both families of partitions of {k} enumerated exhaustively; "
                                     "the counts differ — the identity is false")
    notes = (f"the two counts agree exactly for every n <= {_PARTITION_ID_BOUND} — "
             "NOT proved, honestly open")
    instruments = ("exhaustive partition counting",)
    if {fl, fr} == {"odd", "distinct"}:
        from .bijections import certify_euler_bijection
        if certify_euler_bijection(_PARTITION_ID_BOUND).verified:
            notes += ("; constructive bijection (Glaisher) verified for every n <= "
                      f"{_PARTITION_ID_BOUND} — classical theorem, universal step not "
                      "machine-checked here")
            instruments = ("exhaustive partition counting", "bijections.certify_euler_bijection")
    return CheckResult(stmt, "partition_count_identity", "open", "no_counterexample_within_bound",
                       checked_up_to=f"all n <= {_PARTITION_ID_BOUND}, both counts exact",
                       instruments=instruments, notes=notes)


# --- composition counting identity: "compositions(n) == g(n)"  (v4F2) ---------------------------

_COMPOSITION_ID_BOUND = 12       # 2^11 = 2048 compositions at n=12 — exhaustive stays instant
_COMP_PREFIX = re.compile(r"^\s*compositions\s*\(")
_COMP_STMT = re.compile(r"^\s*compositions\s*\(\s*n\s*\)\s*(?:==|=)\s*(.+?)\s*$")


def _comp_unsupported(stmt: str, why: str) -> CheckResult:
    return CheckResult(stmt, "composition_count_identity", "unsupported", "none",
                       instruments=("compositions.generate_compositions",),
                       notes=f"{why} — the composition surface is 'compositions(n) == g(n)' with "
                             "g an expression in n (filtered composition counts are NOT supported); "
                             "the engine refuses to guess")


def _cutpoint_verified(k: int) -> bool:
    """Re-verify the cut-point bijection {compositions of k} ↔ {subsets of {1..k−1}} from the PUBLIC
    pieces (injective + onto all 2^(k−1) subsets + round-tripping inverse) — check() trusts its own
    verification, not another module's flag."""
    from .compositions import composition_to_cutset, cutset_to_composition, generate_compositions
    comps = generate_compositions(k)
    images = {composition_to_cutset(c) for c in comps}
    if not (len(comps) == len(images) == (1 << (k - 1))):
        return False
    return all(cutset_to_composition(k, composition_to_cutset(c)).parts == c.parts for c in comps)


def _check_composition_identity(stmt: str) -> CheckResult | None:
    if not _COMP_PREFIX.match(stmt):
        return None
    m = _COMP_STMT.match(stmt)
    if not m:
        return _comp_unsupported(stmt, "could not read the statement as 'compositions(n) == g(n)'")
    import sympy
    nsym = sympy.Symbol("n")
    try:
        expr = sympy.sympify(m.group(1))
    except (sympy.SympifyError, TypeError, ValueError) as exc:
        return _comp_unsupported(stmt, f"could not parse the right side ({exc})")
    if expr.free_symbols - {nsym}:
        return _comp_unsupported(stmt, f"free symbols other than n: {expr.free_symbols - {nsym}}")
    if _oversized_constant(expr):                                  # v4F2: refusal, never a crash
        return _comp_unsupported(stmt, _OVERSIZED)
    from .compositions import count_compositions
    for k in range(1, _COMPOSITION_ID_BOUND + 1):
        c = count_compositions(k)
        try:
            rat = sympy.Rational(expr.subs(nsym, k))               # pi etc. → honest refusal: the
        except (TypeError, ValueError):                            # tier PROMISES integer arithmetic
            return _comp_unsupported(stmt, f"the right side does not evaluate to an exact "
                                           f"rational at n={k}")
        if _too_big(rat):                                          # evaluated blow-up: refuse too
            return _comp_unsupported(stmt, _OVERSIZED + f" when evaluated at n={k}")
        if c * rat.q != rat.p:
            return CheckResult(stmt, "composition_count_identity", "refuted",
                               "exact_integer_certificate",
                               witness={"n": k, "compositions_count": c, "rhs": str(rat)},
                               checked_up_to=f"smallest n where count and formula differ (n={k})",
                               instruments=("exhaustive composition counting",),
                               notes=f"all compositions of {k} enumerated exhaustively; the count "
                                     "disagrees with the right side — the identity is false")
    notes = (f"the exact count matches the formula for every n <= {_COMPOSITION_ID_BOUND} — "
             "NOT proved, honestly open")
    instruments = ("exhaustive composition counting",)
    if sympy.simplify(expr - 2 ** (nsym - 1)) == 0 and all(
            _cutpoint_verified(k) for k in range(1, _COMPOSITION_ID_BOUND + 1)):
        notes += ("; constructive bijection (cut-point) verified for every n <= "
                  f"{_COMPOSITION_ID_BOUND} — classical theorem, universal step not "
                  "machine-checked here")
        instruments = ("exhaustive composition counting",
                       "compositions.composition_to_cutset (cut-point bijection)")
    return CheckResult(stmt, "composition_count_identity", "open", "no_counterexample_within_bound",
                       checked_up_to=f"all n <= {_COMPOSITION_ID_BOUND}, count vs formula exact",
                       instruments=instruments, notes=notes)


def check(statement: str, max_n: int = 7) -> CheckResult:
    """The product's single door. Parse deterministically, route to the right instrument, return an
    honest verdict envelope. Unrecognized input → 'unsupported' + suggestions, never a guess."""
    s = statement.strip()
    if re.search(rf"\d{{{_MAX_CONST_DIGITS + 1},}}", s):           # v4F2: literal monsters refused
        return CheckResult(s, "oversized_constant", "unsupported", "none",
                           notes=f"a numeric literal in the statement exceeds {_MAX_CONST_DIGITS} "
                                 "digits — refused up front (CPython int↔str conversion overflows "
                                 "past ~4300 digits); the engine refuses to guess")
    m = re.match(r"^\s*(\d+)\s*(?:\||divides)\s*(.+)$", s)
    if m:
        return _check_modular(s, int(m.group(1)), m.group(2))
    m = _CONG.match(s)
    if m:
        return _check_congruence(s, m.group(1), m.group(2), int(m.group(3) or m.group(4)))
    m = _SUM_INEQ.match(s)                          # before the identity form: '<=' contains '='
    if m:
        return _check_sum_inequality(s, m.group(1), m.group(2), m.group(3))
    m = re.match(r"^\s*sum_\(i=1\.\.n\)\s*(.+?)\s*=\s*(.+)$", s)
    if m:
        return _check_sum(s, m.group(1), m.group(2))
    res = _check_perm_bound(s, max_n)
    if res is not None:
        return res
    res = _check_partition_identity(s)
    if res is not None:
        return res
    res = _check_composition_identity(s)
    if res is not None:
        return res
    res = _check_graph_bound(s, max_n)
    if res is not None:
        return res
    from .technique_map import classify_statement, suggest_techniques
    structure = classify_statement(s)
    return CheckResult(s, structure, "unsupported", "none",
                       instruments=tuple(p for _n, p, _t in suggest_techniques(s)),
                       notes="statement form not in the supported surface (modular 'm | p(n)'; "
                             "congruences 'p(n) ≡ q(n) (mod m)'; sum identities and comparative "
                             "sum inequalities 'sum_(i=1..n) f(i) = / <= / >= g(n)'; graph "
                             "invariant bounds/equalities 'invA <= / >= / == [k*]invB [+ c]'; "
                             "permutation bounds 'all perms of n: invA <= / >= / == invB-or-g(n)'; "
                             "partition counting identities "
                             "'partitions(n, odd|distinct|all) == partitions(n, ...)'; the "
                             "composition identity 'compositions(n) == g(n)' — set-partition/Bell "
                             "counts are NOT yet supported); "
                             "suggested instruments listed — the engine refuses to guess")
