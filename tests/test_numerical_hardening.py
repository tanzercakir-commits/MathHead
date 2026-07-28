"""
Hardening — numerical methods (ROADMAP G4 [S]) — property-based accuracy +
determinism + fuzz across Track G.

The properties ARE the numerical guarantees: a returned root has a tiny residual,
Simpson is exact on cubics, Lagrange interpolation recovers the generating
polynomial, RK4 matches the analytic solution, and verify_numeric agrees with
evaluate_precision (self-consistency of the precision bridge).
"""
import math

import hypothesis.strategies as st
import sympy
from hypothesis import assume, given, settings

from mathhead.compute import (
    cross_check_numeric,
    evaluate_precision,
    find_root_newton,
    interpolate,
    numerical_integrate,
    runge_kutta,
    verify_numeric,
)

_CFG = settings(max_examples=40, deadline=None)


# ------------------------------ root residual ----------------------------- #
@_CFG
@given(st.integers(2, 60))
def test_newton_returns_a_true_root(c):
    # a returned root really satisfies f(root) ≈ 0
    r = find_root_newton(f"x**2 - {c}", "x", float(c))
    assume(r.status == "ok")
    assert r.result["residual"] < 1e-8


# ------------------------- quadrature exactness --------------------------- #
@_CFG
@given(st.integers(-3, 3), st.integers(-3, 3), st.integers(-3, 3), st.integers(-3, 3))
def test_simpson_is_exact_on_cubics(a, b, c, d):
    # composite Simpson is exact for polynomials of degree ≤ 3
    expr = f"{a}*x**3 + {b}*x**2 + {c}*x + {d}"
    r = numerical_integrate(expr, "x", 0, 2)
    exact = a * 4 + b * sympy.Rational(8, 3) + c * 2 + d * 2
    assert abs(r.result["value"] - float(exact)) < 1e-6


# ------------------------ interpolation recovery -------------------------- #
@_CFG
@given(st.integers(-5, 5), st.integers(-5, 5), st.integers(-5, 5))
def test_interpolation_recovers_quadratic(a, b, c):
    # points sampled from a·x² + b·x + c → interpolant reproduces the value elsewhere
    pts = [[k, a * k * k + b * k + c] for k in range(4)]
    r = interpolate(pts, 5)
    assert int(r.result["value"]) == a * 25 + b * 5 + c


# ---------------------------- RK4 accuracy -------------------------------- #
@_CFG
@given(st.integers(1, 3))
def test_rk4_matches_exponential(k):
    # y' = k·y, y(0)=1 → e^{k·x}; at x=1 → e^k
    r = runge_kutta(f"{k}*y", 0, 1, 1)
    assert abs(r.result["y_end"] - math.exp(k)) < 1e-4


# ---------------------- precision-bridge consistency ---------------------- #
@_CFG
@given(st.sampled_from(["pi", "E", "sqrt(2)", "sqrt(3)", "pi**2", "exp(1)", "log(2)"]))
def test_verify_numeric_agrees_with_evaluate_precision(expr):
    # the precision bridge is self-consistent: verify(expr, evaluate(expr)) is a match
    val = evaluate_precision(expr, 25).result
    assert verify_numeric(expr, val, 1e-15).result["match"] is True


@_CFG
@given(st.integers(-3, 3), st.integers(-3, 3), st.integers(1, 4))
def test_cross_check_always_agrees_for_polynomials(a, b, pt):
    # a polynomial is unambiguous → the symbolic and numeric paths must agree
    r = cross_check_numeric(f"{a}*x**2 + {b}*x", "x", str(pt))
    assert r.result["agree"] is True


# ---------------------------- fuzz / determinism -------------------------- #
@_CFG
@given(st.text(max_size=16))
def test_numerical_tools_never_crash(s):
    assert find_root_newton(s, "x", 1.0).status in {"ok", "error"}
    assert evaluate_precision(s, 10).status in {"ok", "error"}


def test_numerical_hardening_determinism():
    for _ in range(5):
        assert numerical_integrate("x**2", "x", 0, 3).result["value"] == 9.0
        assert interpolate([[0, 1], [1, 3], [2, 7]], 5).result["value"] == "31"
        assert verify_numeric("pi", "3.14", 1e-6).result["match"] is False
