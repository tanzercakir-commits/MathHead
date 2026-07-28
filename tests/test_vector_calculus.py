"""
Vector calculus (ROADMAP D1) — divergence / curl / laplacian /
directional_derivative / line_integral.

Best-case (known identities) + worst-case (dimension mismatch, zero direction) +
honesty (error first-class) + determinism.
"""
from mathhead.compute import (
    curl,
    directional_derivative,
    divergence,
    laplacian,
    line_integral,
)


# ------------------------------ divergence -------------------------------- #
def test_divergence_radial_field():
    # ∇·(x², y², z²) = 2x + 2y + 2z
    r = divergence(["x**2", "y**2", "z**2"], ["x", "y", "z"])
    assert r.status == "ok"
    assert r.result == "2*x + 2*y + 2*z"


def test_divergence_of_solenoidal_is_zero():
    # F = (y, z, x) → ∇·F = 0 (divergence-free)
    assert divergence(["y", "z", "x"], ["x", "y", "z"]).result == "0"


def test_divergence_length_mismatch_rejected():
    r = divergence(["x", "y"], ["x"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# --------------------------------- curl ----------------------------------- #
def test_curl_rotational_field():
    # ∇×(-y, x, 0) = (0, 0, 2)
    r = curl(["-y", "x", "0"], ["x", "y", "z"])
    assert r.status == "ok"
    assert r.result == ["0", "0", "2"]


def test_curl_of_gradient_is_zero():
    # F = ∇(x*y*z) = (yz, xz, xy) is conservative → ∇×F = 0
    r = curl(["y*z", "x*z", "x*y"], ["x", "y", "z"])
    assert r.result == ["0", "0", "0"]


def test_curl_requires_three_dimensions():
    assert curl(["x", "y"], ["x", "y"]).status == "error"


# ------------------------------ laplacian --------------------------------- #
def test_laplacian_of_quadratic():
    # ∇²(x² + y² + z²) = 6
    assert laplacian("x**2 + y**2 + z**2", ["x", "y", "z"]).result == "6"


def test_laplacian_harmonic_is_zero():
    # x² - y² is harmonic → ∇²f = 0
    assert laplacian("x**2 - y**2", ["x", "y"]).result == "0"


def test_laplacian_empty_variables_rejected():
    assert laplacian("x**2", []).status == "error"


# ------------------------ directional_derivative -------------------------- #
def test_directional_derivative_axis():
    # D f along (1,0) of x²+y² = 2x
    assert directional_derivative("x**2 + y**2", ["x", "y"], ["1", "0"]).result == "2*x"


def test_directional_derivative_normalizes():
    # direction (3,4) has norm 5 → (2x·3 + 2y·4)/5 = 6x/5 + 8y/5
    r = directional_derivative("x**2 + y**2", ["x", "y"], ["3", "4"])
    assert r.result == "6*x/5 + 8*y/5"


def test_directional_derivative_zero_direction_rejected():
    r = directional_derivative("x**2", ["x"], ["0"])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


# ------------------------------ line_integral ----------------------------- #
def test_line_integral_along_parabola():
    # ∫_C (y, x)·dr, r(t)=(t, t²), t:0..1  →  ∫ (t²·1 + t·2t) dt = ∫ 3t² = 1
    r = line_integral(["y", "x"], ["x", "y"], ["t", "t**2"], "t", "0", "1")
    assert r.status == "ok"
    assert r.result == "1"


def test_line_integral_conservative_field_closed_loop():
    # Conservative F=(y, x) around a closed loop (unit circle) → 0
    r = line_integral(["y", "x"], ["x", "y"], ["cos(t)", "sin(t)"], "t", "0", "2*pi")
    assert r.status == "ok"
    assert r.result == "0"


def test_line_integral_length_mismatch_rejected():
    assert line_integral(["y", "x"], ["x", "y"], ["t"], "t", "0", "1").status == "error"


# ------------------------------ safety ------------------------------------ #
def test_malicious_field_rejected():
    assert divergence(["__import__('os')", "y"], ["x", "y"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_vector_calculus_determinism():
    for _ in range(5):
        assert divergence(["x**2", "y**2"], ["x", "y"]).result == "2*x + 2*y"
        assert curl(["-y", "x", "0"], ["x", "y", "z"]).result == ["0", "0", "2"]
        assert laplacian("x**2 - y**2", ["x", "y"]).result == "0"
