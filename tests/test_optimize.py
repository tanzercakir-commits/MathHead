"""
Optimizasyon (optimization modulo theories, Z3 Optimize): kısıtlar altında bir
sayısal amacı en büyük/küçük yapmak. unbounded / infeasible dürüstçe raporlanır.
"""
from mathhead.core.logic import optimize


def test_maximize_bounded_integer():
    r = optimize(["x > 0", "x < 10"], "x", "max")
    assert r.status == "optimal"
    assert r.objective_value == 9
    assert r.witness["x"] == 9


def test_minimize_bounded_integer():
    r = optimize(["x > 0", "x < 10"], "x", "min")
    assert r.status == "optimal"
    assert r.objective_value == 1


def test_linear_objective_two_variables():
    r = optimize(["x <= 4", "y <= 5", "x >= 0", "y >= 0"], "3*x + 2*y", "max")
    assert r.status == "optimal"
    assert r.objective_value == 22
    assert r.witness == {"x": 4, "y": 5}


def test_unbounded_is_reported():
    r = optimize(["x > 0"], "x", "max")
    assert r.status == "unbounded"


def test_infeasible_constraints():
    r = optimize(["x > 5", "x < 3"], "x", "max")
    assert r.status == "unsat"


def test_bad_sense_rejected():
    assert optimize(["x > 0"], "x", "sideways").status == "error"
