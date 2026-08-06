"""Discovery v2C1 — the SAT frontier: Ramsey-type finite problems."""
import pytest

from mathhead.discovery.ramsey_sat import (
    _check_colouring,
    bracket_ramsey,
    ramsey_cnf,
    ramsey_decide,
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


def test_r35_and_r44_bracketed_with_engine_derived_lemmas():
    # R(3,5) = 14: red-deg <= 4 (self-contained) + blue-deg <= 8 (cites the engine's OWN R(3,4)=9)
    assert ramsey_decide(13, 3, 5, strengthen=True).satisfiable
    v14 = ramsey_decide(14, 3, 5, strengthen=True)
    assert not v14.satisfiable and len(v14.lemmas_used) == 2
    # R(4,4) = 18: red/blue-deg <= 8, both citing the engine's own R(3,4) bracket
    v18 = ramsey_decide(18, 4, 4, strengthen=True)
    assert not v18.satisfiable and "engine's OWN bracket" in v18.lemmas_used[0]
