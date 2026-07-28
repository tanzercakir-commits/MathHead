"""
Optimization II — symbolic (ROADMAP F3) — critical_points / lagrange_multipliers /
check_convexity.

Best-case (known extrema) + classification (min/max/saddle) + honesty
(undetermined) + determinism.
"""
from mathhead.compute import (
    check_convexity,
    critical_points,
    lagrange_multipliers,
)


# ---------------------------- critical_points ----------------------------- #
def test_critical_point_local_min():
    r = critical_points("x**2 + y**2", ["x", "y"])
    assert r.status == "ok"
    assert r.result[0]["point"] == {"x": "0", "y": "0"}
    assert r.result[0]["classification"] == "local_min"


def test_critical_point_saddle():
    r = critical_points("x**2 - y**2", ["x", "y"])
    assert r.result[0]["classification"] == "saddle"


def test_critical_points_min_and_max():
    # x³ − 3x has a local max at −1 and a local min at 1
    r = critical_points("x**3 - 3*x", ["x"])
    kinds = {p["point"]["x"]: p["classification"] for p in r.result}
    assert kinds["-1"] == "local_max"
    assert kinds["1"] == "local_min"


def test_critical_points_empty_vars_rejected():
    assert critical_points("x**2", []).status == "error"


# --------------------------- lagrange_multipliers ------------------------- #
def test_lagrange_max_product_fixed_sum():
    # max x·y subject to x + y = 10 → (5, 5), λ = 5, f = 25
    r = lagrange_multipliers("x*y", ["x+y-10"], ["x", "y"])
    assert r.status == "ok"
    sol = r.result[0]
    assert sol["point"] == {"x": "5", "y": "5"}
    assert sol["multipliers"] == ["5"]
    assert sol["objective_value"] == "25"


def test_lagrange_accepts_equation_form():
    r = lagrange_multipliers("x*y", ["x+y==10"], ["x", "y"])
    assert r.result[0]["point"] == {"x": "5", "y": "5"}


def test_lagrange_no_constraint_rejected():
    assert lagrange_multipliers("x*y", [], ["x", "y"]).status == "error"


# ----------------------------- check_convexity ---------------------------- #
def test_convex_paraboloid():
    r = check_convexity("x**2 + y**2", ["x", "y"])
    assert r.result["verdict"] == "convex"
    assert r.result["hessian_definiteness"] == "positive_definite"


def test_concave_function():
    assert check_convexity("-x**2 - y**2", ["x", "y"]).result["verdict"] == "concave"


def test_neither_saddle_shape():
    assert check_convexity("x**2 - y**2", ["x", "y"]).result["verdict"] == "neither"


def test_convex_exponential_real_variable():
    # exp(x) is convex (needs the real-variable assumption to resolve)
    assert check_convexity("exp(x)", ["x"]).result["verdict"] == "convex"


def test_convexity_malicious_rejected():
    assert check_convexity("__import__('os')", ["x"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_optimization2_determinism():
    for _ in range(5):
        assert lagrange_multipliers("x*y", ["x+y-10"], ["x", "y"]).result[0]["objective_value"] == "25"
        assert check_convexity("x**2 + y**2", ["x", "y"]).result["verdict"] == "convex"
        assert critical_points("x**2 - y**2", ["x", "y"]).result[0]["classification"] == "saddle"
