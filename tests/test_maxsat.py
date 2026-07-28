"""
MaxSAT: satisfy the mandatory (hard) constraints while satisfying the MOST
(weighted) soft constraints. Resolution of over-constrained / conflicting requests.
"""
from mathhead.core.logic import max_satisfy


def test_two_of_three_soft():
    # p and not p can't both hold -> at most 2/3 (one of them + q)
    r = max_satisfy([], ["p", "not(p)", "q"])
    assert r.status == "optimal"
    assert r.satisfied_weight == 2
    assert r.total_weight == 3


def test_conflicting_soft_under_hard():
    r = max_satisfy(["x > 0"], ["x < 5", "x > 10"])
    assert r.status == "optimal"
    assert r.satisfied_weight == 1


def test_weights_prefer_heavier_constraint():
    r = max_satisfy([], ["p", "not(p)"], weights=[3, 1])
    assert r.status == "optimal"
    assert r.satisfied == [0]          # p (weight 3) preferred
    assert r.satisfied_weight == 3


def test_all_soft_satisfiable():
    r = max_satisfy([], ["p", "q"])
    assert r.satisfied_weight == 2
    assert r.total_weight == 2


def test_hard_infeasible_is_unsat():
    r = max_satisfy(["x > 5", "x < 3"], ["p"])
    assert r.status == "unsat"


def test_bad_weights_and_empty_soft_rejected():
    assert max_satisfy([], []).status == "error"
    assert max_satisfy([], ["p", "q"], weights=[1]).status == "error"   # length mismatch
