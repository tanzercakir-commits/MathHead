"""
Integral transforms (ROADMAP D2) — Laplace & inverse, Fourier & inverse, Z-transform.

Best-case (known transform pairs) + round-trip (transform then invert) + honesty
(no closed form → COMPUTE_FAILED, never an unevaluated object) + determinism.
"""
from mathhead.compute import (
    fourier_transform,
    inverse_fourier_transform,
    inverse_laplace_transform,
    laplace_transform,
    z_transform,
)


# ------------------------------ Laplace ----------------------------------- #
def test_laplace_of_t():
    r = laplace_transform("t")
    assert r.status == "ok"
    assert r.result == "s**(-2)"


def test_laplace_of_exponential():
    # ℒ{e^{a t}} = 1/(s - a)
    assert laplace_transform("exp(a*t)").result == "1/(-a + s)"


def test_laplace_of_sine():
    # ℒ{sin t} = 1/(s² + 1)
    assert laplace_transform("sin(t)").result == "1/(s**2 + 1)"


def test_inverse_laplace_recovers_time_domain():
    # ℒ⁻¹{1/s²} = t·Heaviside(t)
    r = inverse_laplace_transform("1/s**2")
    assert r.status == "ok"
    assert "t*Heaviside(t)" in r.result


def test_laplace_roundtrip_exponential():
    # t-domain → s-domain → back to t-domain (with Heaviside)
    f = laplace_transform("exp(3*t)")
    assert f.result == "1/(s - 3)"
    back = inverse_laplace_transform(f.result)
    assert "exp(3*t)" in back.result


def test_laplace_no_closed_form_is_honest():
    # 1/t has no (finite) Laplace transform → honest error, not an unevaluated object
    r = laplace_transform("1/t")
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


# ------------------------------ Fourier ----------------------------------- #
def test_fourier_of_gaussian():
    r = fourier_transform("exp(-x**2)")
    assert r.status == "ok"
    assert r.result == "sqrt(pi)*exp(-pi**2*k**2)"


def test_fourier_roundtrip():
    # ℱ then ℱ⁻¹ recovers the original Gaussian
    fwd = fourier_transform("exp(-x**2)")
    back = inverse_fourier_transform(fwd.result)
    assert back.status == "ok"
    assert back.result == "exp(-x**2)"


# ------------------------------ Z-transform ------------------------------- #
def test_z_transform_unit_step():
    # Z{1} = z/(z-1)  (closed form extracted from the Piecewise)
    r = z_transform("1")
    assert r.status == "ok"
    assert r.result == "z/(z - 1)"


def test_z_transform_geometric():
    # Z{a^n} = z/(z-a)
    assert z_transform("a**n").result == "z/(-a + z)"


def test_z_transform_ramp():
    # Z{n} = z/(z-1)²
    assert z_transform("n").result == "z/(z - 1)**2"


# ------------------------------ safety ------------------------------------ #
def test_malicious_rejected():
    assert laplace_transform("__import__('os')").status == "error"
    assert z_transform("__import__('os')").status == "error"


# ------------------------------ determinism ------------------------------- #
def test_transform_determinism():
    for _ in range(5):
        assert laplace_transform("t").result == "s**(-2)"
        assert z_transform("1").result == "z/(z - 1)"
        assert fourier_transform("exp(-x**2)").result == "sqrt(pi)*exp(-pi**2*k**2)"
