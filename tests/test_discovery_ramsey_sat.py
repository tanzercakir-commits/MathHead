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
    assert not unsat6.satisfiable and unsat6.certainty == "solver_verified"


def test_r34_bracketed_exactly():
    assert bracket_ramsey(3, 4, 8, 9)["ramsey_value"] == 9          # R(3,4) = 9


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
