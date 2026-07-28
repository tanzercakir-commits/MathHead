"""
Hardening — analysis (ROADMAP D5 [S]) — property-based identities + a numerical
cross-check + determinism/fuzz across Track D (vector calculus, transforms,
complex analysis).

Notably DOGFOODS the verification layer: identities like ∇²f = ∇·(∇f) are checked
with MathHead's own `verify_equality`.
"""
import hypothesis.strategies as st
import sympy
from hypothesis import given, settings

from mathhead.compute import (
    complex_parts,
    curl,
    divergence,
    fourier_transform,
    gradient,
    inverse_fourier_transform,
    laplace_transform,
    laplacian,
    residue,
)
from mathhead.core.verify import verify_equality

_CFG = settings(max_examples=40, deadline=None)
_XYZ = ["x", "y", "z"]
_terms = st.sampled_from(
    ["x", "y", "z", "x*y", "y*z", "x*z", "x**2", "y**2", "z**2", "x*y*z", "x**2*y"]
)
_scalar = st.lists(_terms, min_size=1, max_size=3).map(lambda ts: " + ".join(ts))
_vfield = st.lists(_terms, min_size=3, max_size=3)


# --------------------- vector-calculus identities ------------------------- #
@_CFG
@given(_scalar)
def test_curl_of_gradient_is_zero(f):
    # ∇×(∇f) ≡ 0 for any scalar field
    g = gradient(f, _XYZ).result
    assert curl(g, _XYZ).result == ["0", "0", "0"]


@_CFG
@given(_vfield)
def test_divergence_of_curl_is_zero(comps):
    # ∇·(∇×F) ≡ 0 for any vector field
    c = curl(comps, _XYZ).result
    assert divergence(c, _XYZ).result == "0"


@_CFG
@given(_scalar)
def test_laplacian_equals_div_of_grad(f):
    # ∇²f = ∇·(∇f) — checked with MathHead's OWN verifier (dogfooding)
    lap = laplacian(f, _XYZ).result
    div_grad = divergence(gradient(f, _XYZ).result, _XYZ).result
    assert verify_equality(lap, div_grad).status == "valid"


# ---------------------- numerical cross-check ----------------------------- #
@_CFG
@given(_scalar)
def test_curl_of_gradient_zero_numerically(f):
    # Independent of symbolic simplification: evaluate ∇×(∇f) at sample points → 0
    comps = curl(gradient(f, _XYZ).result, _XYZ).result
    x, y, z = sympy.symbols("x y z")
    for px, py, pz in ((1, 2, 3), (-2, 1, 4), (5, -3, 2)):
        for c in comps:
            val = sympy.sympify(c).subs({x: px, y: py, z: pz})
            assert abs(complex(val)) < 1e-9


# ------------------------- transform round-trip --------------------------- #
@_CFG
@given(st.sampled_from(["exp(-x**2)", "2*exp(-x**2)", "exp(-3*x**2)"]))
def test_fourier_roundtrip_recovers_original(f):
    fwd = fourier_transform(f)
    assert fwd.status == "ok"
    back = inverse_fourier_transform(fwd.result)
    assert back.status == "ok"
    assert verify_equality(back.result, f).status == "valid"


# ------------------------ complex reconstruction -------------------------- #
@_CFG
@given(st.integers(-6, 6), st.integers(-6, 6), st.integers(-6, 6), st.integers(-6, 6))
def test_complex_parts_matches_product_formula(a, b, c, d):
    # (a+bi)(c+di) = (ac − bd) + (ad + bc)i
    r = complex_parts(f"({a} + {b}*I)*({c} + {d}*I)")
    assert r.status == "ok"
    assert int(r.result["real"]) == a * c - b * d
    assert int(r.result["imag"]) == a * d + b * c


# ---------------------------- fuzz / determinism -------------------------- #
@_CFG
@given(st.text(max_size=20))
def test_analysis_tools_never_crash(s):
    assert laplace_transform(s).status in {"ok", "error"}
    assert residue(s, "z", "0").status in {"ok", "error"}
    assert laplacian(s, ["x"]).status in {"ok", "error"}


def test_analysis_determinism():
    for _ in range(5):
        assert curl(["-y", "x", "0"], _XYZ).result == ["0", "0", "2"]
        assert residue("1/(z**2 + 1)", "z", "I").result == "-I/2"
        assert laplace_transform("t").result == "s**(-2)"
