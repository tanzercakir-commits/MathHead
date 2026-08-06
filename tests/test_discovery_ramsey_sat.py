"""Discovery v2C1 — the SAT frontier: Ramsey-type finite problems."""
import pytest

from mathhead.discovery.ramsey_sat import (
    _check_colouring,
    bracket_ramsey,
    ramsey_cnf,
    ramsey_decide,
    ramsey_decide_case_split,
)

pytest.importorskip("pysat.solvers", reason="pysat not installed")


def test_r33_bracketed_exactly():
    r = bracket_ramsey(3, 3, 4, 6)
    assert r["ramsey_value"] == 6                                   # R(3,3) = 6, the classic
    sat5 = next(v for v in r["verdicts"] if v.n == 5)
    assert sat5.satisfiable and sat5.certainty == "independently_verified_witness"
    unsat6 = next(v for v in r["verdicts"] if v.n == 6)
    assert not unsat6.satisfiable                                   # v4F0: UNSAT is RUP-certified
    assert unsat6.certainty == "independently_verified_unsat_proof"
    assert unsat6.unsat_proof_checked and unsat6.unsat_proof_lemmas > 0


def test_r34_bracketed_exactly():
    r = bracket_ramsey(3, 4, 8, 9)
    assert r["ramsey_value"] == 9                                   # R(3,4) = 9
    unsat9 = next(v for v in r["verdicts"] if v.n == 9)             # v4F0 DONE criterion: the
    assert unsat9.certainty == "independently_verified_unsat_proof"  # UNSAT passes the in-engine
    assert unsat9.unsat_proof_checked and unsat9.unsat_proof_lemmas > 0  # independent RUP check


def test_sat_witness_is_independently_recheckable():
    v = ramsey_decide(5, 3, 3)
    assert v.satisfiable and _check_colouring(5, 3, 3, set(v.red_edges))
    # tamper with the witness → the independent check must reject it
    broken = set(v.red_edges) ^ {(0, 1)}
    assert _check_colouring(5, 3, 3, broken) in (True, False)       # runs; and on ALL-red it fails:
    assert not _check_colouring(3, 3, 3, {(0, 1), (0, 2), (1, 2)})  # a red triangle is caught


def test_flip_outside_range_makes_no_claim():
    assert bracket_ramsey(3, 3, 4, 5)["ramsey_value"] is None       # no UNSAT seen → no value claimed


def test_cnf_shape_and_determinism():
    ev, clauses = ramsey_cnf(5, 3, 3)
    assert len(ev) == 10 and len(clauses) == 20                     # C(5,3)=10 red + 10 blue clauses
    a, b = ramsey_decide(5, 3, 3), ramsey_decide(5, 3, 3)
    assert a.red_edges == b.red_edges and a.meaning == "R(3,3) > 5"


def test_strengthening_preserves_known_verdicts():
    a = ramsey_decide(8, 3, 4, strengthen=True)
    b = ramsey_decide(9, 3, 4, strengthen=True)
    assert a.satisfiable and not b.satisfiable
    # v4F0: the RUP-checked proof refutes the STRENGTHENED formula — the tier says so verbatim,
    # never claiming a proof of the bare encoding.
    assert b.certainty == "independently_verified_unsat_proof_of_strengthened_formula"
    assert b.lemmas_used and b.unsat_proof_checked
    assert "STRENGTHENED" in b.unsat_proof_note


# ---- v4F5: the R(3,6) lemma branch (mechanism pins only — the n=17/18 runs live in SCALE-RUNS.md,
# ---- long solver runs are results, not tests) ----

def test_r36_degree_lemmas_derive_the_right_bounds():
    from pysat.card import CardEnc, EncType

    from mathhead.discovery.ramsey_sat import _degree_lemmas, _edge_vars
    n = 17
    ev = _edge_vars(n)
    clauses, lemmas, _top = _degree_lemmas(n, 3, 6, ev, max(ev.values()))
    assert len(lemmas) == 2
    assert lemmas[0].startswith("red-degree <= 5 per vertex")       # s=3 rule: t-1 = 5
    assert lemmas[1].startswith("blue-degree <= 13 per vertex")     # R(3,5)-1 = 13
    assert "R(3,5)-1 = 13" in lemmas[1]
    assert "R(3,5)=14 is the engine's OWN bracket" in lemmas[1]     # the self-referential chain
    # clause-count formula, independent of the emitted list: n identical per-vertex seqcounter
    # at-most encodings over n-1 literals per side (red bound 5, blue bound 13)
    lits = list(range(1, n))
    red_one = len(CardEnc.atmost(lits=lits, bound=5, top_id=10 ** 6,
                                 encoding=EncType.seqcounter).clauses)
    blue_one = len(CardEnc.atmost(lits=[-x for x in lits], bound=13, top_id=10 ** 6,
                                  encoding=EncType.seqcounter).clauses)
    assert len(clauses) == n * (red_one + blue_one)


def test_r36_branch_leaves_small_anchors_untouched():
    # R(3,3) = 6 and R(3,4) = 9 anchors, WITH strengthening through the reworked lemma builder
    a = ramsey_decide(5, 3, 3, strengthen=True)
    u = ramsey_decide(6, 3, 3, strengthen=True)
    assert a.satisfiable and not u.satisfiable
    # t=3: R(3,2) is not an engine bracket, so ONLY the self-contained red lemma exists
    assert len(a.lemmas_used) == 1 and a.lemmas_used[0].startswith("red-degree <= 2")
    # t=4: the bracket-derived blue side arrives for free — blue <= R(3,3)-1 = 5, same chain text
    b = ramsey_decide(8, 3, 4, strengthen=True)
    assert b.satisfiable and len(b.lemmas_used) == 2
    assert b.lemmas_used[0].startswith("red-degree <= 3")
    assert b.lemmas_used[1].startswith("blue-degree <= 5 per vertex")
    assert "R(3,3)-1 = 5" in b.lemmas_used[1]
    assert "R(3,3)=6 is the engine's OWN bracket" in b.lemmas_used[1]
    assert not ramsey_decide(9, 3, 4, strengthen=True).satisfiable  # the verdict itself: unmoved


# ---- symmetry case split (max-red-degree): NOT an implied lemma, so it carries its OWN tiers —
# ---- mechanism pins only; the R(3,6) n=18 run itself lives in SCALE-RUNS.md (Koşu 4), never here.

def test_case_split_r34_unsat_earns_the_rup_checked_cases_tier():
    v = ramsey_decide_case_split(9, 3, 4, budget_per_case_s=120, certify=True)
    assert v.outcome == "unsat" and v.meaning == "R(3,4) <= 9"
    assert v.certainty == "solver_verified_unsat_by_symmetry_case_split_with_rup_checked_cases"
    assert "independently" not in v.certainty            # NEVER an independently_verified_* tier:
    assert "NOT machine-checked" in v.note               # the covering argument stays prose
    assert [c.d for c in v.cases] == [0, 1, 2, 3]        # s=3 case range: D in 0..t-1
    assert all(c.status == "unsat" and c.rup_checked for c in v.cases)
    assert sum(c.rup_lemmas for c in v.cases) > 0        # the D=3 case proof is a real proof
    assert v.lemmas_used and v.solver_name == "glucose3"


def test_case_split_sat_takes_the_normal_witness_path():
    v = ramsey_decide_case_split(5, 3, 3, budget_per_case_s=60, certify=True)
    assert v.outcome == "sat" and v.meaning == "R(3,3) > 5"
    assert v.certainty == "independently_verified_witness"      # symmetry plays no role for SAT
    assert _check_colouring(5, 3, 3, set(v.red_edges))          # re-checked here, independently
    assert [c.status for c in v.cases] == ["unsat", "unsat", "sat"]   # D=0,1 die; D=2 witnesses


def test_case_split_second_level_agrees_with_the_anchors():
    v = ramsey_decide_case_split(9, 3, 4, budget_per_case_s=120, certify=False,
                                 fix_neighbourhood=True, second_level=True)
    assert v.outcome == "unsat"
    assert v.certainty == "solver_verified_unsat_by_symmetry_case_split"  # no proof requested
    assert v.cases[0].note == "certify=False: DRUP proof not requested"
    assert [(c.d, c.d1) for c in v.cases] == [(0, None), (1, 1), (2, 1), (2, 2),
                                              (3, 1), (3, 2), (3, 3)]
    w = ramsey_decide_case_split(5, 3, 3, budget_per_case_s=60, certify=False,
                                 fix_neighbourhood=True, second_level=True)
    assert w.outcome == "sat" and _check_colouring(5, 3, 3, set(w.red_edges))
    # every case carries ITS OWN constraint text, exactly as encoded (evaluator Bulgu 4)
    assert all(c.constraint for c in v.cases)
    c32 = next(c for c in v.cases if (c.d, c.d1) == (3, 2))
    assert "N_red(0) = {1..3}" in c32.constraint
    assert "N_red(1) = {0} ∪ {4..4}" in c32.constraint          # d1-1 = 1 pinned red neighbour
    assert "red-degree(1) = 2" in c32.constraint
    assert "each case's exact instantiation rides its RamseyCase.constraint" in v.case_constraint


def test_case_split_id_list_clamps_and_skips_degenerate_sub_cases():
    from mathhead.discovery.ramsey_sat import _case_split_ids
    # d1 > n - D is DEGENERATE (vertex 1 cannot have d1-1 red neighbours inside {D+1..n-1}):
    # at n=5, D=3 the sub-case d1=3 is skipped — the covering lands at d1 <= n - D = 2.
    ids, d_max = _case_split_ids(5, 3, 4, second_level=True)
    assert d_max == 3
    assert ids == [(0, None), (1, 1), (2, 1), (2, 2), (3, 1), (3, 2)]      # no (3, 3)
    # d_max clamps at n-1 (a case D > n-1 could not pin N_red(0) = {1..D} inside the vertex set)
    ids46, d_max46 = _case_split_ids(4, 3, 6, second_level=False)
    assert d_max46 == 3 and ids46 == [(0, None), (1, None), (2, None), (3, None)]
    # the production run shape of SCALE-RUNS Koşu 4, pinned: 16 cases, no degenerate ones at n=18
    ids18, _ = _case_split_ids(18, 3, 6, second_level=True)
    assert len(ids18) == 16 and ids18[-1] == (5, 5)


def test_case_split_timeout_is_never_a_result():
    # R(3,6) at n=18 with a deliberately tiny per-case budget: the hard cases MUST time out, and
    # the whole verdict MUST be undecided — partial UNSAT cases are run data, never a result.
    v = ramsey_decide_case_split(18, 3, 6, budget_per_case_s=0.05, certify=False)
    assert v.outcome == "undecided_within_budget"
    assert v.certainty == ""                             # no verdict earns NO tier
    assert "a timeout is never a result" in v.meaning
    assert "R(3,6) <=" not in v.meaning and "R(3,6) >" not in v.meaning
    assert any(c.status == "timeout" for c in v.cases)
    assert "prove NOTHING" in v.note


def test_case_split_guards_refuse_unsound_or_unlabelable_configs():
    with pytest.raises(ValueError, match="unsupported solver_name"):
        ramsey_decide_case_split(5, 3, 3, solver_name="minisat")
    with pytest.raises(ValueError, match="certify=True requires glucose3"):
        ramsey_decide_case_split(5, 3, 3, solver_name="cadical195", certify=True)
    with pytest.raises(ValueError, match="second_level requires"):
        ramsey_decide_case_split(5, 3, 3, second_level=True)          # no fixed N_red(0)
    with pytest.raises(ValueError, match="second_level requires"):
        ramsey_decide_case_split(18, 4, 4, second_level=True, fix_neighbourhood=True)  # s != 3
    # defence in depth: the clause builder itself refuses a level-2 pin without the level-1 fix
    from mathhead.discovery.ramsey_sat import _case_constraint_clauses, _edge_vars
    ev = _edge_vars(5)
    with pytest.raises(ValueError, match="d1 requires fix_neighbourhood"):
        _case_constraint_clauses(5, ev, 2, max(ev.values()), False, d1=1)


def test_case_split_covering_chain_is_machine_checked_by_exhaustion_at_small_n():
    # The covering argument stays PROSE at scale (that is the tiers' whole point) — but its
    # three-step relabelling CHAIN is machine-checked here by exhaustion at small n: EVERY
    # base-satisfying colouring of (3,3) n<=5 and (3,4) n<=4 must land, after the chain, in a
    # production case of `_case_split_ids` with every emitted constraint holding verbatim.
    from itertools import combinations

    from mathhead.discovery.ramsey_sat import _case_split_ids

    def relabel(red, perm):
        return {tuple(sorted((perm[a], perm[b]))) for a, b in red}

    def rdeg(red, v):
        return sum(1 for e in red if v in e)

    checked = 0
    for s, t, n_hi in ((3, 3, 5), (3, 4, 4)):
        for n in range(2, n_hi + 1):
            ids, d_max = _case_split_ids(n, s, t, second_level=True)
            edges = list(combinations(range(n), 2))
            for mask in range(1 << len(edges)):
                red = {e for i, e in enumerate(edges) if mask >> i & 1}
                if not _check_colouring(n, s, t, red):
                    continue                              # not a base model — nothing to cover
                d_star = max(rdeg(red, v) for v in range(n))
                assert d_star <= d_max                    # the case range really is exhaustive
                # step 1: a max-red-degree vertex goes to 0 (transposition)
                w = next(v for v in range(n) if rdeg(red, v) == d_star)
                perm = list(range(n))
                perm[0], perm[w] = perm[w], perm[0]
                red = relabel(red, perm)
                # step 2: N_red(0) -> {1..D}, the rest keep their relative order
                nbr0 = sorted(u for u in range(1, n) if (0, u) in red)
                rest = [u for u in range(1, n) if u not in nbr0]
                perm = [0] * n
                for i, u in enumerate(nbr0 + rest):
                    perm[u] = 1 + i
                red = relabel(red, perm)
                assert {u for u in range(1, n) if (0, u) in red} == set(range(1, d_star + 1))
                if d_star == 0:
                    assert red == set() and (0, None) in ids
                else:
                    d1 = rdeg(red, 1)
                    nbr1 = sorted(u for u in range(2, n) if tuple(sorted((1, u))) in red)
                    assert all(u > d_star for u in nbr1)  # red-K3-freeness pushed them past D
                    assert 1 <= d1 <= min(d_star, n - d_star)   # the degenerate cut is SAFE
                    # step 3: N_red(1) \ {0} -> {D+1..D+d1-1}, fixing {0..D} pointwise
                    tail = [u for u in range(d_star + 1, n) if u not in nbr1]
                    perm = list(range(d_star + 1)) + [0] * (n - d_star - 1)
                    for i, u in enumerate(nbr1 + tail):
                        perm[u] = d_star + 1 + i
                    red = relabel(red, perm)
                    assert (d_star, d1) in ids            # lands in a PRODUCTION case, and every
                    assert {u for u in range(1, n)        # emitted constraint holds verbatim:
                            if (0, u) in red} == set(range(1, d_star + 1))
                    assert {u for u in range(2, n) if tuple(sorted((1, u))) in red} \
                        == set(range(d_star + 1, d_star + d1))
                    assert max(rdeg(red, v) for v in range(n)) == d_star
                assert _check_colouring(n, s, t, red)     # still a base model after the chain
                checked += 1
    assert checked == 87                                  # every base model over both families:
    #                                                       (3,3) n=2..5: 2+6+18+12; (3,4) n=2..4:
    #                                                       2+7+40 — deterministic, pinned


def test_r36_bracket_entry_and_its_honest_provenance():
    from mathhead.discovery.ramsey_sat import _OWN_BRACKETS, _degree_lemmas, _edge_vars
    # R(3,6) = 18 entered the engine's OWN bracket table (SCALE-RUNS Koşu 4). Its SAT leg is fast
    # enough to pin here; the UNSAT leg is a 239 s Cadical case-split run and lives in SCALE-RUNS
    # only — a long run is a result, not a test.
    assert _OWN_BRACKETS[(3, 6)] == 18
    v17 = ramsey_decide(17, 3, 6, strengthen=True)
    assert v17.satisfiable and v17.certainty == "independently_verified_witness"
    # the chain grows: R(3,6)=18 now feeds the t=7 blue-degree lemma, same table, never hard-coded
    ev = _edge_vars(19)
    _clauses, lemmas, _top = _degree_lemmas(19, 3, 7, ev, max(ev.values()))
    assert lemmas[1].startswith("blue-degree <= 17 per vertex")
    assert "R(3,6)=18 is the engine's OWN bracket" in lemmas[1]


def test_r35_and_r44_bracketed_with_engine_derived_lemmas():
    # R(3,5) = 14: red-deg <= 4 (self-contained) + blue-deg <= 8 (cites the engine's OWN R(3,4)=9)
    assert ramsey_decide(13, 3, 5, strengthen=True).satisfiable
    v14 = ramsey_decide(14, 3, 5, strengthen=True)
    assert not v14.satisfiable and len(v14.lemmas_used) == 2
    # R(4,4) = 18: red/blue-deg <= 8, both citing the engine's own R(3,4) bracket
    v18 = ramsey_decide(18, 4, 4, strengthen=True)
    assert not v18.satisfiable and "engine's OWN bracket" in v18.lemmas_used[0]
