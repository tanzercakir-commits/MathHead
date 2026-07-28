"""
Numerical analysis (ROADMAP G1) — find_root_newton / find_root_bisection /
find_root_secant / numerical_integrate / interpolate.

Numerical work is deterministic (fixed mpmath precision). Best-case (known roots/
integrals) + honesty (no sign change, non-convergence) + determinism.
"""
from mathhead.compute import (
    find_root_bisection,
    find_root_newton,
    find_root_secant,
    interpolate,
    numerical_integrate,
)


# ------------------------------ root-finding ------------------------------ #
def test_newton_sqrt2():
    r = find_root_newton("x**2 - 2", "x", 1.5)
    assert r.status == "ok"
    assert r.result["converged"] is True
    assert abs(r.result["root"] - 1.4142135623730951) < 1e-9


def test_newton_dottie_number():
    # fixed point of cos: cos(x) = x → x ≈ 0.739085
    r = find_root_newton("cos(x) - x", "x", 0.5)
    assert abs(r.result["root"] - 0.7390851332151607) < 1e-9


def test_bisection_sqrt2():
    r = find_root_bisection("x**2 - 2", "x", 1, 2)
    assert r.status == "ok"
    assert abs(r.result["root"] - 1.4142135623730951) < 1e-9


def test_bisection_requires_sign_change():
    r = find_root_bisection("x**2 + 1", "x", 0, 1)
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_secant_sqrt2():
    r = find_root_secant("x**2 - 2", "x", 1, 2)
    assert r.result["converged"] is True
    assert abs(r.result["root"] - 1.4142135623730951) < 1e-9


def test_newton_extra_symbol_rejected():
    assert find_root_newton("x*y", "x", 1).status == "error"


# --------------------------- numerical_integrate -------------------------- #
def test_simpson_exact_on_polynomial():
    # Simpson is exact for cubics → ∫₀³ x² dx = 9
    r = numerical_integrate("x**2", "x", 0, 3)
    assert r.status == "ok"
    assert r.result["value"] == 9.0


def test_trapezoid_sine_half_period():
    # ∫₀^π sin x dx = 2 (approx)
    import math
    r = numerical_integrate("sin(x)", "x", 0, math.pi, "trapezoid", 1000)
    assert abs(r.result["value"] - 2.0) < 1e-4


def test_numerical_integrate_bad_method_rejected():
    assert numerical_integrate("x", "x", 0, 1, "romberg").status == "error"


# ------------------------------ interpolate ------------------------------- #
def test_interpolate_quadratic():
    r = interpolate([[0, 1], [1, 3], [2, 7]])
    assert r.status == "ok"
    assert r.result["polynomial"] == "x**2 + x + 1"


def test_interpolate_value_at_point():
    r = interpolate([[0, 1], [1, 3], [2, 7]], 3)
    assert r.result["value"] == "13"


def test_interpolate_duplicate_x_rejected():
    assert interpolate([[0, 1], [0, 2]]).status == "error"


def test_interpolate_recovers_known_line():
    # points on y = 2x + 1 → interpolant is exactly 2*x + 1
    r = interpolate([[0, 1], [1, 3], [2, 5]])
    assert r.result["polynomial"] == "2*x + 1"


# ------------------------------ determinism ------------------------------- #
def test_numerical_determinism():
    for _ in range(5):
        assert find_root_newton("x**2 - 2", "x", 1.5).result["root"] == \
            find_root_newton("x**2 - 2", "x", 1.5).result["root"]
        assert numerical_integrate("x**2", "x", 0, 3).result["value"] == 9.0
        assert interpolate([[0, 1], [1, 3], [2, 7]]).result["polynomial"] == "x**2 + x + 1"
