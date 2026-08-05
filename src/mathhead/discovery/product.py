"""
mathhead.discovery.product — the single-door product API (v3P0 + v4F1): `check(statement)`.

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

Supported statement forms (the v4F1 product surface — parsed deterministically, never guessed):
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
                  graphs up to `max_n` (an equality that survives is OPEN, never proved)
Anything else → verdict "unsupported" with the recognized structure + suggested instruments (X2 map) —
an honest refusal, never a fabricated answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_SUM_WITNESS_BOUND = 40          # smallest-n witness scan bound for comparative sum inequalities
_DIRECT_SUM_BOUND = 10_000       # up to here, integer hints are re-verified by DIRECT summation
_MAX_MODULUS = 10**6             # residue exhaustion beyond this is an honest refusal, not a hang


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
        poly = _int_poly_in_n(sympy.expand(sympy.sympify(expr)))
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
    f_poly = poly_from_sympy_q(str(sympy.expand(sympy.sympify(f_expr).subs(i, n))))
    g_poly = poly_from_sympy_q(str(sympy.expand(sympy.sympify(g_expr))))
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
    # 1) smallest-n witness search, exact arithmetic
    acc, sums = sympy.Integer(0), []
    for k in range(1, _SUM_WITNESS_BOUND + 1):
        acc = acc + ff.subs(i, k)
        sums.append(acc)
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


def _check_graph_bound(stmt: str, max_n: int) -> CheckResult | None:
    from .conjecture_service import service_invariants
    m = _GRAPH_STMT.match(stmt)
    if not m:
        return None
    lhs, rel, k, rhs, c = (m.group(1), m.group(2), int(m.group(3) or 1),
                           m.group(4), int(m.group(5) or 0))
    rel = "==" if rel == "=" else rel
    structure = "graph_equality" if rel == "==" else "graph_inequality"
    from .invariants import evaluate as _ev
    invs = dict(service_invariants())
    for extra in ("num_vertices", "num_triangles", "sum_degrees", "num_components"):
        invs.setdefault(extra, lambda g, _x=extra: _ev(g, _x))
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


def check(statement: str, max_n: int = 7) -> CheckResult:
    """The product's single door. Parse deterministically, route to the right instrument, return an
    honest verdict envelope. Unrecognized input → 'unsupported' + suggestions, never a guess."""
    s = statement.strip()
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
                             "invariant bounds/equalities 'invA <= / >= / == [k*]invB [+ c]'); "
                             "suggested instruments listed — the engine refuses to guess")
