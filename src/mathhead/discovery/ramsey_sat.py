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

A third boundary (the symmetry road): `ramsey_decide_case_split` refutes hard instances through a
max-red-degree case split. The split is NOT an implied lemma — it preserves satisfiability through
documented relabelling arguments, so its UNSAT verdicts carry their own tiers
(`solver_verified_unsat_by_symmetry_case_split[_with_rup_checked_cases]`), whose `solver_verified`
head says exactly what remains unchecked by machine: the covering argument itself.

Calibration anchors (classical): R(3,3)=6 — SAT at 5 (the pentagon 2-colouring), UNSAT at 6;
R(3,4)=9 — SAT at 8, UNSAT at 9.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations


def _edge_vars(n: int) -> dict:
    """1-based CNF variable per edge of K_n; TRUE = red, FALSE = blue."""
    return {e: i + 1 for i, e in enumerate(combinations(range(n), 2))}


# THE ENGINE'S OWN Ramsey brackets — every value here was established BY THIS MODULE, pinned by
# tests in test_discovery_ramsey_sat.py (or, where a leg is a long run, recorded in
# docs/discovery/SCALE-RUNS.md). Derived degree lemmas cite ONLY this table, so the
# self-referential chain is explicit: R(3,3) and R(3,4) fed R(3,5); R(3,5) fed R(3,6) (v4F5's
# lemmas powered the case split that refuted n=18). A value may be added ONLY once the engine has
# bracketed it itself — never from the literature — and each entry names its weakest link: the
# first three have RUP-checked UNSAT legs; (3,6)'s UNSAT leg is `solver_verified_unsat_by_
# symmetry_case_split` (Cadical195's word on 16 case formulas + the documented, machine-UNchecked
# covering argument — see `ramsey_decide_case_split`), so every future lemma citing R(3,6)
# inherits that weaker provenance.
_OWN_BRACKETS: dict = {
    (3, 3): 6,      # witnessed at 5, refuted at 6   (test_r33_bracketed_exactly)
    (3, 4): 9,      # witnessed at 8, refuted at 9   (test_r34_bracketed_exactly)
    (3, 5): 14,     # witnessed at 13, refuted at 14 (test_r35_and_r44_bracketed_...)
    (3, 6): 18,     # witnessed at 17 (independently_verified_witness, SCALE-RUNS Koşu 2a; pinned
                    # by test_r36_bracket_entry_and_its_honest_provenance); refuted at 18 by the
                    # two-level symmetry case split, Cadical195, 239 s (SCALE-RUNS Koşu 4 —
                    # solver's word + prose covering argument, NOT a RUP-checked proof).
                    # Koşu 6/6b (2026-08-06) re-established the same verdict with Glucose42 and
                    # BACKWARD-RUP-certified 14 of the 16 case proofs; (5,4)/(5,5) ended
                    # budget_exceeded (no verdict on those proofs), so the tier stands UNCHANGED
                    # — a partial set of certified cases never upgrades anything
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
      * s == 3, (3, t−1) ∈ `_OWN_BRACKETS` (today t ∈ {4, 5, 6, 7}) — blue side: N_blue(v) must
        avoid red K₃ AND blue K_{t−1} (else blue K_t with v); hence |N_blue(v)| ≤ R(3,t−1)−1,
        DERIVED from the engine's own bracket table, never hard-coded: R(3,3)=6 gives blue ≤ 5 for
        t=4, R(3,4)=9 gives blue ≤ 8 for t=5, R(3,5)=14 gives blue ≤ 13 for t=6, R(3,6)=18 gives
        blue ≤ 17 for t=7. The self-referential lemma chain GROWS: R(3,3)/R(3,4) fed R(3,5);
        R(3,5) fed R(3,6) (v4F5 lemmas + the case split); R(3,6) now stands ready for t=7 — with
        the WEAKER provenance its bracket-table entry records (case-split UNSAT leg).
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


@dataclass
class RamseyCase:
    """One case of the max-red-degree split: the sub-formula with max-red-degree fixed to `d`
    (and, under `second_level`, red-degree(1) fixed to `d1`)."""
    d: int
    status: str                     # "unsat" | "sat" | "timeout"
    seconds: float
    d1: int | None = None           # second-level sub-case: red-degree(1) = d1 (None: no level 2)
    constraint: str = ""            # THIS case's constraint, spelled out exactly as encoded
    rup_checked: bool = False       # this case's DRUP proof re-checked by the independent RUP checker
    rup_lemmas: int = 0
    rup_status: str = ""            # the checker's own verdict on this case's proof: "verified" |
    #                                 "refuted" | "not_rup_checkable" | "budget_exceeded" |
    #                                 "error" | "" (no check attempted / certify=False)
    note: str = ""


@dataclass
class CaseSplitVerdict:
    """Verdict of `ramsey_decide_case_split`. `outcome` is one of:

      * "sat"    — some case is SAT; the witness satisfies the BASE formula (a case model is a
        base model), so this is the normal SAT path: `independently_verified_witness`.
      * "unsat"  — EVERY case is UNSAT; via the documented covering argument this refutes the
        base formula. Tier: `solver_verified_unsat_by_symmetry_case_split` (or the
        `..._with_rup_checked_cases` variant when every case's proof passed the RUP checker).
      * "undecided_within_budget" — at least one case hit the per-case budget. NO claim about
        R(s,t) at this n is made or implied; a timeout is never a result, and a partial set of
        UNSAT cases proves nothing about the base formula.
    """
    n: int
    s: int
    t: int
    outcome: str                    # "sat" | "unsat" | "undecided_within_budget"
    meaning: str                    # "R(s,t) > n" | "R(s,t) <= n" | "no verdict: ..."
    certainty: str                  # tier; "" when undecided (no verdict earns no tier)
    cases: tuple = ()               # RamseyCase per attempted case, in order
    lemmas_used: tuple = ()         # derived (implied) lemmas shared by every case
    case_constraint: str = ""       # the constraint SCHEMA; exact per-case text on each RamseyCase
    red_edges: tuple = ()           # witness colouring when outcome == "sat"
    solver_name: str = "glucose3"   # the solver that decided the cases
    note: str = ""


def _case_split_ids(n: int, s: int, t: int, second_level: bool):
    """The PRODUCTION case list of the max-red-degree split, extracted so tests can machine-check
    the covering claim by exhaustion at small n (`test_case_split_covering_chain_is_machine_
    checked_by_exhaustion_at_small_n`). Returns ([(d, d1-or-None), ...], d_max).

    Two truncations, both sound and both keeping every emitted constraint literally true:

      * d_max = min(t-1, n-1) for s == 3 (t-1 implied by the base formula, n-1 trivial), n-1
        otherwise — a case d > n-1 could not even pin N_red(0) = {1..d} inside the vertex set;
      * second-level sub-cases with d1 > n - d are DEGENERATE and skipped: vertex 1 cannot have
        d1-1 red neighbours inside {d+1..n-1} (only n-1-d vertices live there), and the covering
        argument lands every colouring at d1 = red-degree(1) <= 1 + (n-1-d) = n - d."""
    d_max = min(t - 1, n - 1) if s == 3 else n - 1
    ids: list = []
    for d in range(d_max + 1):
        if second_level and d >= 1:
            ids += [(d, d1) for d1 in range(1, min(d, n - d) + 1)]
        else:
            ids.append((d, None))
    return ids, d_max


def _case_constraint_clauses(n: int, ev: dict, d: int, top: int, fix_neighbourhood: bool,
                             d1: int | None = None):
    """Clauses for case D=`d` of the max-red-degree split: red-degree(0) = d and
    red-degree(v) <= d for every other vertex. With `fix_neighbourhood`, the equality at vertex 0
    is replaced by the strictly stronger unit assignment N_red(0) = {1..d}; with `d1` also set
    (the second level, s=3 + fix_neighbourhood only), vertex 1's red neighbourhood is pinned to
    {0} ∪ {d+1..d+d1-1} outright (see the covering argument in `ramsey_decide_case_split` for
    why every variant preserves satisfiability). Returns (clauses, description, new_top)."""
    from pysat.card import CardEnc, EncType
    if d1 is not None and not fix_neighbourhood:         # defence in depth: the level-2 covering
        raise ValueError("d1 requires fix_neighbourhood=True — the second-level argument needs "
                         "N_red(0) = {1..d} to be pinned (see ramsey_decide_case_split)")
    clauses = []
    if fix_neighbourhood:
        clauses += [[ev[(0, u)]] if u <= d else [-ev[(0, u)]] for u in range(1, n)]
        desc = (f"N_red(0) = {{1..{d}}} as unit clauses (subsumes red-degree(0) = {d}) "
                f"+ red-degree(v) <= {d} for every v >= 1")
    else:
        lits0 = [ev[(0, u)] for u in range(1, n)]
        enc = CardEnc.equals(lits=lits0, bound=d, top_id=top, encoding=EncType.seqcounter)
        clauses += enc.clauses
        top = max(top, enc.nv)
        desc = f"red-degree(0) = {d} (seqcounter equals) + red-degree(v) <= {d} for every v >= 1"
    if d1 is not None:                                   # second level: N_red(1) fully pinned
        want = set(range(d + 1, d + d1))                 # the d1-1 red neighbours besides vertex 0
        clauses += [[ev[(1, u)]] if u in want else [-ev[(1, u)]] for u in range(2, n)]
        desc += (f"; second level: N_red(1) = {{0}} ∪ {{{d + 1}..{d + d1 - 1}}} as unit clauses "
                 f"(red-degree(1) = {d1})")
    for v in range(1, n):
        lits = [ev[(min(v, u), max(v, u))] for u in range(n) if u != v]
        enc = CardEnc.atmost(lits=lits, bound=d, top_id=top, encoding=EncType.seqcounter)
        clauses += enc.clauses
        top = max(top, enc.nv)
    return clauses, desc, top


def _solve_case_in_child(formula, conn) -> None:
    """Child-process case solve (Cadical path): send (result, model) back and exit. Runs in a
    forked process so the parent can enforce a wall-clock budget by terminating it — pysat's
    Cadical195 `interrupt()` cannot stop a running search (verified 2026-08-06), so in-process
    budgets are impossible for it; killing the process is the only honest budget."""
    from pysat.solvers import Cadical195
    with Cadical195(bootstrap_with=formula) as solver:
        res = solver.solve()
        model = solver.get_model() if res else None
    conn.send((res, model))
    conn.close()


def ramsey_decide_case_split(n: int, s: int, t: int, budget_per_case_s: float | None = None,
                             certify: bool = True, strengthen: bool = True,
                             fix_neighbourhood: bool = False, second_level: bool = False,
                             solver_name: str = "glucose3",
                             rup_visit_budget: int | None = None) -> CaseSplitVerdict:
    """Decide the K_n instance by a case split on the maximum red degree — a SYMMETRY argument,
    not an implied lemma, so it gets its own honesty tier (never the implied-lemma tiers).

    THE COVERING ARGUMENT (documented here and on the verdict — NOT machine-checked; that is
    exactly why the UNSAT tier below keeps its `solver_verified` head):

      1. Case D's formula is base (+ the implied degree lemmas when `strengthen`) + the constraint
         "red-degree(0) = D and red-degree(v) <= D for all v". Every case model is a base model,
         so ANY case SAT => base SAT — the SAT direction needs no symmetry at all.
      2. Conversely let chi be ANY colouring satisfying the base formula, and let
         D* = max_v red-degree(v). Pick a vertex w attaining D* and relabel the vertices by the
         transposition (0 w). Relabelling is an automorphism of K_n: the base clause set (every
         s-subset, every t-subset) is invariant under it, and the per-vertex degree lemmas form a
         permutation-invariant family, so the relabelled colouring still satisfies base(+lemmas)
         — and now red-degree(0) = D* with every red-degree <= D*: it satisfies case D*.
         With `fix_neighbourhood=True`, apply a SECOND relabelling that fixes vertex 0 and maps
         N_red(0) onto {1..D*} (possible: it permutes only vertices 1..n-1); it is again an
         automorphism fixing 0's red degree and permuting the degree-bound family, so the result
         satisfies the stronger unit-clause case. This is NOT lex-leader symmetry breaking and no
         completeness-of-breaking is claimed — only satisfiability preservation.
      3. The case range covers every possible D*: for s == 3, red-degree(v) <= t-1 holds in EVERY
         base-satisfying colouring (N_red(v) is pairwise blue, else a red K_3 with v; t of them
         would be a blue K_t) so D* in {0..min(t-1, n-1)} (the n-1 clamp is trivial: no vertex
         has n neighbours); for other s the range is {0..n-1}, trivially complete. Hence:
         EVERY case UNSAT => base UNSAT => R(s,t) <= n.
      4. `second_level=True` (s == 3 with `fix_neighbourhood` ONLY — both facts below lean on
         red-triangle-freeness and on N_red(0) = {1..D}) refines every case D >= 1 into sub-cases
         d1 in {1..min(D, n-D)} that pin vertex 1's red neighbourhood to {0} ∪ {D+1..D+d1-1}
         outright. Coverage: a case-D colouring chi'' has red edge (0,1), so 0 ∈ N_red(1) and
         d1 := red-degree(1) ∈ {1..D}; no red edge joins 1 to {2..D} (it would close a red K_3
         with vertex 0, both being red neighbours of 0), so N_red(1) \\ {0} ⊆ {D+1..n-1} with
         d1-1 members — which also bounds d1 <= 1 + (n-1-D) = n - D, so sub-cases past that are
         degenerate and `_case_split_ids` skips them; a THIRD relabelling fixing {0..D} pointwise
         and mapping those members onto {D+1..D+d1-1} is again an automorphism preserving base,
         the degree-lemma family, N_red(0) = {1..D} and every case-D constraint — chi'' lands in
         sub-case (D, d1). The sub-cases of D exhaust case D, so "every sub-case UNSAT => base
         UNSAT" still holds. This whole relabelling chain is machine-checked BY EXHAUSTION at
         small n in `test_case_split_covering_chain_is_machine_checked_by_exhaustion_at_small_n`
         — which pins the PATTERN, not any particular large-n claim: at scale the argument
         remains prose, and the tiers below stay `solver_verified`.

    Tiers, honestly separated:

      * some case SAT  -> `independently_verified_witness` (witness re-checked by brute force
        against the BASE constraints — the normal SAT path, symmetry plays no role);
      * every case UNSAT, every case's DRUP proof re-checked by the independent RUP checker ->
        `solver_verified_unsat_by_symmetry_case_split_with_rup_checked_cases`. Each RUP check
        certifies ONE case formula's unsatisfiability; the covering argument above (that the
        cases exhaust the base formula) is prose, machine-UNchecked — the tier name says
        "case_split" and keeps `solver_verified` first for exactly that reason, and it is
        deliberately NOT any `independently_verified_*` tier;
      * every case UNSAT but some proof unavailable/unchecked ->
        `solver_verified_unsat_by_symmetry_case_split` (per-case rup status on `cases`);
      * ANY case timeout (and none SAT) -> outcome `undecided_within_budget`, NO tier, NO claim:
        a partial set of UNSAT cases proves nothing and is never reported as a result.

    Proof checking (`certify=True`) goes through the independent BACKWARD checker
    (`rup_check.check_drup_backward`, drat-trim's marking idea): only the lemmas in the final
    conflict's derivation cone are RUP-checked, which is what makes the multi-million-lemma
    proofs of the hard R(3,6)@18 cases checkable in pure Python at all. Each case records the
    checker's own verdict on `rup_status` — "verified" | "refuted" | "not_rup_checkable" |
    "budget_exceeded" | "error" — and `rup_checked` stays a bool that is True ONLY for
    "verified"; a `budget_exceeded` check is never a result and silently costs the
    `..._with_rup_checked_cases` tier, honestly.

    Solvers, honestly bounded: `solver_name="glucose3"` (default) and `"glucose42"` enforce
    `budget_per_case_s` in-process via interrupt and support `certify` (their DRUP output is
    RUP-only, so a marked lemma's RUP failure honestly refutes the proof).
    `solver_name="cadical195"` runs each case in a forked child process killed at the budget —
    pysat's Cadical195 `interrupt()` cannot stop a running search (verified 2026-08-06: a 1 s
    interrupt timer left the solve running past 30 s) — and REFUSES `certify=True`: pysat's
    CaDiCaL proof tracing writes a TRUNCATED file (verified 2026-08-06 on all three cadical
    backends: the binary DRAT stream ends mid-step with the concluding ⊥ missing — the
    tracer's tail is never flushed through the pysat API), so no checkable proof can be
    obtained, and the honest response is refusal rather than a silent downgrade. (The RAT-step
    boundary documented in `rup_check` — Cadical emits DRAT-family proofs whose RAT steps a
    RUP-only checker can never validate, only report `not_rup_checkable` — would apply even if
    complete proofs were obtainable.)"""
    import multiprocessing as mp
    from threading import Timer
    from time import perf_counter

    from pysat.solvers import Glucose3, Glucose42

    from .rup_check import check_drup_backward
    if solver_name not in ("glucose3", "glucose42", "cadical195"):
        raise ValueError(f"unsupported solver_name {solver_name!r}: "
                         "glucose3 | glucose42 | cadical195")
    if solver_name == "cadical195" and certify:
        raise ValueError("certify=True requires glucose3 or glucose42: pysat's CaDiCaL proof "
                         "tracing yields truncated proofs (the concluding steps are never "
                         "flushed — verified 2026-08-06), and Cadical's DRAT-family output is "
                         "outside the RUP checker's documented soundness argument anyway — no "
                         "honest RUP tier is available for it, so it is refused rather than "
                         "silently downgraded")
    if second_level and (s != 3 or not fix_neighbourhood):
        raise ValueError("second_level requires s == 3 and fix_neighbourhood=True — its covering "
                         "argument uses red-triangle-freeness and N_red(0) = {1..D} (docstring)")
    ev, base = ramsey_cnf(n, s, t)
    top = max(ev.values())
    lemmas: tuple = ()
    if strengthen:
        extra, lemmas, top = _degree_lemmas(n, s, t, ev, top)
        base = base + extra
    case_ids, d_max = _case_split_ids(n, s, t, second_level)
    range_note = (f"D in 0..{d_max} covers every colouring: s=3 implies red-degree <= "
                  f"min(t-1, n-1) (t-1 from the base formula itself, n-1 trivial)" if s == 3
                  else f"D in 0..{d_max} is trivially complete")
    schema = ("per case (D, d1): "
              + ("N_red(0) = {1..D} as unit clauses" if fix_neighbourhood
                 else "red-degree(0) = D (seqcounter equals)")
              + " + red-degree(v) <= D for every v >= 1"
              + ("; second level (D >= 1): N_red(1) = {0} ∪ {D+1..D+d1-1} as unit clauses, "
                 "d1 in 1..min(D, n-D)" if second_level else "")
              + " — each case's exact instantiation rides its RamseyCase.constraint")
    cases: list = []
    for d, d1 in case_ids:
        case_clauses, desc, _ = _case_constraint_clauses(n, ev, d, top, fix_neighbourhood, d1)
        formula = base + case_clauses
        t0 = perf_counter()
        proof = None
        if solver_name in ("glucose3", "glucose42"):
            glucose_cls = Glucose3 if solver_name == "glucose3" else Glucose42
            with glucose_cls(bootstrap_with=formula, with_proof=certify) as solver:
                if budget_per_case_s is not None:
                    timer = Timer(budget_per_case_s, solver.interrupt)
                    timer.start()
                    res = solver.solve_limited(expect_interrupt=True)
                    timer.cancel()
                else:
                    res = solver.solve()
                model = solver.get_model() if res else None
                proof = solver.get_proof() if (res is False and certify) else None
        else:                                            # cadical195: budget = kill the child
            ctx = mp.get_context("fork")
            parent_conn, child_conn = ctx.Pipe(duplex=False)
            proc = ctx.Process(target=_solve_case_in_child, args=(formula, child_conn))
            proc.start()
            child_conn.close()
            res = model = None
            if parent_conn.poll(budget_per_case_s):     # poll(None) blocks until an answer
                try:
                    res, model = parent_conn.recv()
                except EOFError as exc:                  # a dead child is an ERROR, never a verdict
                    proc.join()
                    raise RuntimeError("case-solver child process died without a verdict — "
                                       "refusing to record anything") from exc
                proc.join()
            else:
                proc.terminate()
                proc.join()
            parent_conn.close()
        dt = perf_counter() - t0
        if res is None:                                  # interrupted: a timeout, NEVER a result
            cases.append(RamseyCase(d, "timeout", dt, d1, desc,
                                    note=f"budget {budget_per_case_s}s exceeded; no claim"))
            continue
        if res:                                          # SAT: the normal witness path
            pos = {v for v in model if v > 0}
            red = {e for e, var in ev.items() if var in pos}
            if not _check_colouring(n, s, t, red):
                raise RuntimeError("SAT model failed the independent witness check — "
                                   "refusing the verdict")
            cases.append(RamseyCase(d, "sat", dt, d1, desc,
                                    note="witness re-checked by brute force"))
            return CaseSplitVerdict(
                n, s, t, "sat", f"R({s},{t}) > {n}", "independently_verified_witness",
                tuple(cases), lemmas, schema, tuple(sorted(red)), solver_name,
                note="a case model is a base model — SAT needs no symmetry argument; "
                     "witness re-checked by brute force against the BASE constraints")
        case = RamseyCase(d, "unsat", dt, d1, desc)
        if certify:
            kwargs = {} if rup_visit_budget is None else {"visit_budget": rup_visit_budget}
            rup = check_drup_backward(formula, proof, proof_format="drup", **kwargs)
            case.rup_status = rup.status
            if rup.ok:
                case.rup_checked, case.rup_lemmas = True, rup.lemmas_checked
                case.note = ("case-formula DRUP proof re-checked by the independent backward "
                             f"RUP checker ({rup.lemmas_checked} of {rup.total_lemmas} lemmas "
                             "in the derivation cone)")
            else:
                case.note = f"RUP check did not pass ({rup.status}): {rup.message}"
        else:
            case.note = "certify=False: DRUP proof not requested"
        proof = None                                     # a hard case's proof can be huge — drop it
        cases.append(case)
    if any(c.status == "timeout" for c in cases):
        timed_out = [(c.d, c.d1) if c.d1 is not None else c.d
                     for c in cases if c.status == "timeout"]
        return CaseSplitVerdict(
            n, s, t, "undecided_within_budget",
            f"no verdict on R({s},{t}) at n={n}: a timeout is never a result", "",
            tuple(cases), lemmas, schema, solver_name=solver_name,
            note=f"case(s) {timed_out} exceeded the {budget_per_case_s}s per-case budget; "
                 f"the remaining UNSAT cases prove NOTHING about the base formula and are "
                 f"recorded only as run data")
    all_rup = all(c.rup_checked for c in cases)
    tier = ("solver_verified_unsat_by_symmetry_case_split_with_rup_checked_cases" if all_rup
            else "solver_verified_unsat_by_symmetry_case_split")
    return CaseSplitVerdict(
        n, s, t, "unsat", f"R({s},{t}) <= {n}", tier, tuple(cases), lemmas, schema,
        solver_name=solver_name,
        note=f"every case ({len(cases)} in all) UNSAT; {range_note}; the covering argument (any "
             f"base colouring relabels into some case — see ramsey_decide_case_split's "
             f"docstring) is documented prose, NOT machine-checked, which is why this tier "
             f"keeps its solver_verified head even when every per-case proof is RUP-checked")


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
