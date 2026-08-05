"""
mathhead.discovery.product — the single-door product API (v3P0): `check(statement)`.

The product promise: bring your conjecture — the engine refutes it (with a witness), proves it (with a
kernel proof), or tells you exactly how far it survived. One call, one honest envelope:

    >>> check("6 | n^3 - n")                      # → proved, kernel_verified, proof hash
    >>> check("5 | n^3 - n")                      # → refuted, witness n=2 (value 6 ≢ 0 mod 5)
    >>> check("sum_(i=1..n) i = n*(n+1)/2")       # → proved, kernel_verified (SumInduction)
    >>> check("num_triangles <= num_edges")       # → refuted, smallest graph witness in hand
    >>> check("clique_number <= chromatic_number")  # → open, no counterexample up to the stated bound

Supported statement forms (v1 of the product surface — parsed deterministically, never guessed):
  * modular:      "m | poly(n)"  or  "m divides poly(n)"
  * sum identity: "sum_(i=1..n) f(i) = g(n)"   (f in i, g in n; rational closed forms fine)
  * graph bound:  "invA <= invB [+ c]"  or  "invA <= k*invB"  over the rich+classic invariants,
                  checked counterexample-first on ALL connected graphs up to `max_n`
Anything else → verdict "unsupported" with the recognized structure + suggested instruments (X2 map) —
an honest refusal, never a fabricated answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


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
    from .kernel import KernelError, poly_from_sympy, prove_divides
    from .provenance import proof_hash as _hash
    poly = poly_from_sympy(expr)
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


_INEQ = re.compile(r"^\s*(\w+)\s*<=\s*(?:(\d+)\s*\*\s*)?(\w+)\s*(?:\+\s*(\d+))?\s*$")


def _check_graph_bound(stmt: str, max_n: int) -> CheckResult | None:
    from .conjecture_service import service_invariants
    m = _INEQ.match(stmt)
    if not m:
        return None
    lhs, k, rhs, c = m.group(1), int(m.group(2) or 1), m.group(3), int(m.group(4) or 0)
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
    checked = 0
    for g in graphs:
        va, vb = invs[lhs](g), invs[rhs](g)
        checked += 1
        if not va <= k * vb + c:
            return CheckResult(stmt, "graph_inequality", "refuted", "exact_integer_certificate",
                               witness={"n": g.n, "edges": sorted(g.edges), lhs: va, rhs: vb},
                               checked_up_to=f"first counterexample among connected graphs, n={g.n}",
                               instruments=("counterexample-first scan",),
                               notes="smallest-order witness; values computed exactly")
    return CheckResult(stmt, "graph_inequality", "open", "no_counterexample_within_bound",
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
                       notes="statement form not in the supported surface; suggested instruments "
                             "listed — the engine refuses to guess")
