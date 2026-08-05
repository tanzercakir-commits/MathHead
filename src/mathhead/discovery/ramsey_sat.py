"""
mathhead.discovery.ramsey_sat — the SAT frontier: Ramsey-type finite problems (v2C1, Kademe 3).

Heule's programme (Boolean Pythagorean triples, Schur 5) settled OPEN finite combinatorics with SAT
solvers. This is the engine's on-ramp: encode "K_n admits a 2-colouring of its edges with no red K_s
and no blue K_t" as CNF and let the solver decide. Semantics, exactly:

    SAT  at n  ⟹  R(s,t) > n      (a colouring EXISTS — and we hold it in hand)
    UNSAT at n ⟹  R(s,t) ≤ n      (no colouring exists)

Honesty tiers, kept separate: a SAT verdict is upgraded to `independently_verified_witness` — the
returned colouring is re-checked by BRUTE FORCE (every s-subset scanned for a red clique, every
t-subset for a blue one) with no solver in the loop; an UNSAT verdict stays `solver_verified`
(kernel-grade UNSAT needs DRAT proof logging — recorded as the honest next step, not claimed).

Calibration anchors (classical): R(3,3)=6 — SAT at 5 (the pentagon 2-colouring), UNSAT at 6;
R(3,4)=9 — SAT at 8, UNSAT at 9.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


def _edge_vars(n: int) -> dict:
    """1-based CNF variable per edge of K_n; TRUE = red, FALSE = blue."""
    return {e: i + 1 for i, e in enumerate(combinations(range(n), 2))}


def ramsey_cnf(n: int, s: int, t: int):
    """CNF for: no red K_s and no blue K_t in a 2-colouring of K_n's edges."""
    ev = _edge_vars(n)
    clauses = []
    for sub in combinations(range(n), s):               # no all-red K_s: some edge blue
        clauses.append([-ev[e] for e in combinations(sub, 2)])
    for sub in combinations(range(n), t):               # no all-blue K_t: some edge red
        clauses.append([ev[e] for e in combinations(sub, 2)])
    return ev, clauses


def _check_colouring(n: int, s: int, t: int, red: set) -> bool:
    """INDEPENDENT witness check — pure brute force, no solver: no red K_s, no blue K_t."""
    for sub in combinations(range(n), s):
        if all(e in red for e in combinations(sub, 2)):
            return False
    for sub in combinations(range(n), t):
        if all(e not in red for e in combinations(sub, 2)):
            return False
    return True


@dataclass
class RamseyVerdict:
    n: int
    s: int
    t: int
    satisfiable: bool
    meaning: str                    # "R(s,t) > n" | "R(s,t) <= n"
    certainty: str                  # "independently_verified_witness" | "solver_verified"
    red_edges: tuple = ()           # the witness colouring, when SAT


def ramsey_decide(n: int, s: int, t: int) -> RamseyVerdict:
    """Decide the K_n instance with a SAT solver; SAT witnesses are re-verified independently."""
    from pysat.solvers import Glucose3
    ev, clauses = ramsey_cnf(n, s, t)
    with Glucose3(bootstrap_with=clauses) as solver:
        sat = solver.solve()
        model = solver.get_model() if sat else None
    if not sat:
        return RamseyVerdict(n, s, t, False, f"R({s},{t}) <= {n}", "solver_verified")
    pos = {v for v in model if v > 0}
    red = {e for e, var in ev.items() if var in pos}
    if not _check_colouring(n, s, t, red):              # the solver lied? never accept silently
        raise RuntimeError("SAT model failed the independent witness check — refusing the verdict")
    return RamseyVerdict(n, s, t, True, f"R({s},{t}) > {n}",
                         "independently_verified_witness", tuple(sorted(red)))


def bracket_ramsey(s: int, t: int, n_lo: int, n_hi: int):
    """Decide every n in [n_lo, n_hi]; returns the verdicts + the bracketed value when the SAT→UNSAT
    flip happens inside the range (R(s,t) = first UNSAT n), else an honest partial bracket."""
    verdicts = [ramsey_decide(n, s, t) for n in range(n_lo, n_hi + 1)]
    value = None
    for i in range(1, len(verdicts)):
        if verdicts[i - 1].satisfiable and not verdicts[i].satisfiable:
            value = verdicts[i].n
    if verdicts and not verdicts[0].satisfiable and value is None:
        value = None                                     # flip not inside range — no claim
    return {"verdicts": verdicts, "ramsey_value": value,
            "note": "value = first UNSAT n, valid only when the SAT->UNSAT flip is inside the range; "
                    "SAT verdicts carry independently verified witnesses, UNSAT are solver_verified "
                    "(DRAT logging = the recorded next step toward kernel-grade UNSAT)"}
