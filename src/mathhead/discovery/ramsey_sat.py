"""
mathhead.discovery.ramsey_sat — the SAT frontier: Ramsey-type finite problems (v2C1, Kademe 3).

Heule's programme (Boolean Pythagorean triples, Schur 5) settled OPEN finite combinatorics with SAT
solvers. This is the engine's on-ramp: encode "K_n admits a 2-colouring of its edges with no red K_s
and no blue K_t" as CNF and let the solver decide. Semantics, exactly:

    SAT  at n  ⟹  R(s,t) > n      (a colouring EXISTS — and we hold it in hand)
    UNSAT at n ⟹  R(s,t) ≤ n      (no colouring exists)

Honesty tiers, kept separate: a SAT verdict is upgraded to `independently_verified_witness` — the
returned colouring is re-checked by BRUTE FORCE (every s-subset scanned for a red clique, every
t-subset for a blue one) with no solver in the loop. An UNSAT verdict (v4F0, closing the "DRAT
logging = next step" debt) asks the solver for its DRUP proof and re-checks it with the
INDEPENDENT pure-Python RUP checker (`rup_check`, the J2 `mathhead.drat` idea at this frontier —
no solver in the loop), earning `independently_verified_unsat_proof`. Two honest boundaries:

  * with `strengthen=True` the proof refutes the STRENGTHENED formula (base + derived lemmas),
    not the bare encoding — the tier says so verbatim:
    `independently_verified_unsat_proof_of_strengthened_formula`, lemma list on the verdict;
  * if the proof cannot be obtained or checked within budget, the verdict FALLS BACK to plain
    `solver_verified(_with_derived_lemmas)` with the reason on `unsat_proof_note` — the upgrade
    is never claimed without the check actually passing.

Calibration anchors (classical): R(3,3)=6 — SAT at 5 (the pentagon 2-colouring), UNSAT at 6;
R(3,4)=9 — SAT at 8, UNSAT at 9.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


def _edge_vars(n: int) -> dict:
    """1-based CNF variable per edge of K_n; TRUE = red, FALSE = blue."""
    return {e: i + 1 for i, e in enumerate(combinations(range(n), 2))}


# THE ENGINE'S OWN Ramsey brackets — every value here was established BY THIS MODULE (SAT witness
# at R−1 independently re-checked by brute force, UNSAT at R with the RUP-checked proof), pinned by
# tests in test_discovery_ramsey_sat.py. Derived degree lemmas cite ONLY this table, so the
# self-referential chain is explicit: R(3,3) and R(3,4) fed R(3,5); R(3,5) now feeds R(3,6) (v4F5).
# A value may be added ONLY once the engine has bracketed it itself — never from the literature.
_OWN_BRACKETS: dict = {
    (3, 3): 6,      # witnessed at 5, refuted at 6   (test_r33_bracketed_exactly)
    (3, 4): 9,      # witnessed at 8, refuted at 9   (test_r34_bracketed_exactly)
    (3, 5): 14,     # witnessed at 13, refuted at 14 (test_r35_and_r44_bracketed_...)
}


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
    certainty: str                  # SAT: "independently_verified_witness";
    #                                 UNSAT: "independently_verified_unsat_proof" |
    #                                 "independently_verified_unsat_proof_of_strengthened_formula" |
    #                                 (fallback) "solver_verified(_with_derived_lemmas)"
    red_edges: tuple = ()           # the witness colouring, when SAT
    lemmas_used: tuple = ()         # derived (implied) lemmas added to help UNSAT — each documented
    unsat_proof_checked: bool = False   # DRUP proof re-checked by the independent RUP checker
    unsat_proof_lemmas: int = 0     # lemmas in the checked proof (0 when no proof was checked)
    unsat_proof_note: str = ""      # honest provenance: what was checked / why the check was skipped


def _degree_lemmas(n: int, s: int, t: int, ev: dict, top: int):
    """DERIVED (implied) per-vertex degree bounds — sound strengthenings, each a documented theorem
    of the base formula, so adding them preserves satisfiability exactly:

      * s == 3:  red-degree(v) ≤ t−1. Proof: two red neighbours joined red ⇒ red K₃; so N_red(v) is
        pairwise blue; t red neighbours would be a blue K_t. Self-contained.
      * s == 3, (3, t−1) ∈ `_OWN_BRACKETS` (today t ∈ {4, 5, 6}) — blue side: N_blue(v) must avoid
        red K₃ AND blue K_{t−1} (else blue K_t with v); hence |N_blue(v)| ≤ R(3,t−1)−1, DERIVED
        from the engine's own bracket table, never hard-coded: R(3,3)=6 gives blue ≤ 5 for t=4,
        R(3,4)=9 gives blue ≤ 8 for t=5, R(3,5)=14 gives blue ≤ 13 for t=6. The self-referential
        lemma chain GROWS (v4F5): R(3,3)/R(3,4) fed R(3,5); R(3,5) now feeds R(3,6).
      * s == t == 4:  red- and blue-degree(v) ≤ 8. Proof: N_red(v) must avoid red K₃ (else red K₄
        with v) AND blue K₄; hence |N_red(v)| ≤ R(3,4)−1 = 8 — where R(3,4)=9 is THE ENGINE'S OWN
        bracket (this module, independently witnessed at 8, solver-refuted at 9). Blue symmetric.

    Returns (clauses, lemma_descriptions, new_top)."""
    from pysat.card import CardEnc, EncType
    clauses, lemmas = [], []
    if s == 3:
        bound = t - 1
        for v in range(n):
            lits = [ev[(min(v, u), max(v, u))] for u in range(n) if u != v]
            enc = CardEnc.atmost(lits=lits, bound=bound, top_id=top, encoding=EncType.seqcounter)
            clauses += enc.clauses
            top = max(top, enc.nv)
        lemmas.append(f"red-degree <= {bound} per vertex (N_red pairwise blue; t red nbrs = blue K_t)")
        # blue side: N_blue(v) must avoid red K3 AND blue K_{t-1} (else blue K_t with v)
        # ⟹ |N_blue(v)| <= R(3,t-1)-1 — DERIVED from the engine's own bracket table, so the lemma
        # exists exactly when the engine has bracketed R(3,t-1) itself (today t ∈ {4, 5, 6}).
        r3 = _OWN_BRACKETS.get((3, t - 1))
        blue_bound = None if r3 is None else r3 - 1
        if blue_bound is not None:
            for v in range(n):
                lits = [ev[(min(v, u), max(v, u))] for u in range(n) if u != v]
                enc = CardEnc.atmost(lits=[-x for x in lits], bound=blue_bound, top_id=top,
                                     encoding=EncType.seqcounter)
                clauses += enc.clauses
                top = max(top, enc.nv)
            lemmas.append(f"blue-degree <= {blue_bound} per vertex (N_blue avoids red K3 + blue "
                          f"K{t - 1} ⟹ |N_blue| <= R(3,{t - 1})-1 = {blue_bound}; "
                          f"R(3,{t - 1})={blue_bound + 1} is the engine's OWN bracket)")
    elif s == 4 and t == 4:
        bound44 = _OWN_BRACKETS[(3, 4)] - 1                  # derived, same table as the blue side
        for v in range(n):
            lits = [ev[(min(v, u), max(v, u))] for u in range(n) if u != v]
            for sign, name in ((1, "red"), (-1, "blue")):
                enc = CardEnc.atmost(lits=[sign * x for x in lits], bound=bound44, top_id=top,
                                     encoding=EncType.seqcounter)
                clauses += enc.clauses
                top = max(top, enc.nv)
        lemmas.append(f"red/blue-degree <= {bound44} per vertex (|N_c(v)| <= R(3,4)-1 = {bound44}; "
                      f"R(3,4)={bound44 + 1} is the engine's OWN bracket from this module)")
    return clauses, tuple(lemmas), top


def ramsey_decide(n: int, s: int, t: int, strengthen: bool = False,
                  certify_unsat: bool = True) -> RamseyVerdict:
    """Decide the K_n instance with a SAT solver; BOTH verdict kinds are re-verified independently.

    SAT → the witness colouring is re-checked by brute force (`independently_verified_witness`).
    UNSAT → with `certify_unsat=True` (the default) the solver's DRUP proof is re-checked by the
    independent pure-Python RUP checker; on success the tier is `independently_verified_unsat_proof`
    — or, with `strengthen=True`, `independently_verified_unsat_proof_of_strengthened_formula`,
    because the refuted formula is base + derived lemmas, NOT the bare encoding (the lemma list
    rides the verdict). If the proof cannot be verified within budget the tier honestly falls back
    to `solver_verified(_with_derived_lemmas)` and `unsat_proof_note` says why.

    `strengthen=True` adds the DERIVED degree lemmas (implied ⇒ equisatisfiable)."""
    from pysat.solvers import Glucose3
    ev, clauses = ramsey_cnf(n, s, t)
    lemmas = ()
    if strengthen:
        extra, lemmas, _top = _degree_lemmas(n, s, t, ev, max(ev.values()))
        clauses = clauses + extra
    with Glucose3(bootstrap_with=clauses, with_proof=certify_unsat) as solver:
        sat = solver.solve()
        model = solver.get_model() if sat else None
        proof = solver.get_proof() if (not sat and certify_unsat) else None
    if not sat:
        fallback = "solver_verified_with_derived_lemmas" if lemmas else "solver_verified"
        if not certify_unsat:
            return RamseyVerdict(n, s, t, False, f"R({s},{t}) <= {n}", fallback, (), lemmas,
                                 unsat_proof_note="certify_unsat=False: DRUP proof not requested")
        from .rup_check import check_drup_lines
        res = check_drup_lines(clauses, proof)
        if res.ok:
            tier = ("independently_verified_unsat_proof_of_strengthened_formula" if lemmas
                    else "independently_verified_unsat_proof")
            scope = ("the STRENGTHENED formula (base encoding + the derived lemmas listed in "
                     "lemmas_used)" if lemmas else "the base encoding")
            return RamseyVerdict(
                n, s, t, False, f"R({s},{t}) <= {n}", tier, (), lemmas,
                unsat_proof_checked=True, unsat_proof_lemmas=res.lemmas_checked,
                unsat_proof_note=f"DRUP proof of {scope} re-checked by the pure-Python RUP "
                                 f"checker (no solver in the loop): {res.message}")
        # The check did not pass — NEVER claim the upgraded tier; say exactly what happened.
        return RamseyVerdict(
            n, s, t, False, f"R({s},{t}) <= {n}", fallback, (), lemmas,
            unsat_proof_note=f"independent RUP check did not pass ({res.status}): {res.message}")
    pos = {v for v in model if v > 0}
    red = {e for e, var in ev.items() if var in pos}
    if not _check_colouring(n, s, t, red):              # the solver lied? never accept silently
        raise RuntimeError("SAT model failed the independent witness check — refusing the verdict")
    return RamseyVerdict(n, s, t, True, f"R({s},{t}) > {n}",
                         "independently_verified_witness", tuple(sorted(red)), lemmas)


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
                    "SAT verdicts carry independently verified witnesses, UNSAT verdicts carry "
                    "DRUP proofs re-checked by the independent RUP checker (falling back to "
                    "solver_verified, honestly labelled, only if the check cannot be completed)"}
