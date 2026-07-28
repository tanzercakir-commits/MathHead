"""
Hardening — I-track (ROADMAP I5 [S]) — property-based + determinism + fuzz across
the Verification Layer II additions: verify_derivation (I3), the I1 verify_* claims,
interpret (I2), and the I4 certificate kinds.

Goal (same as the compute-layer hardening): (a) never crash on random input
(safety), (b) mathematical invariants hold, (c) same input → same output
(determinism; ADR-0019).
"""
import math

import hypothesis.strategies as st
import sympy
from hypothesis import given, settings

from mathhead.certificate import check_certificate as cc
from mathhead.core.nl import interpret
from mathhead.core.verify import verify_derivation, verify_derivative

_CFG = settings(max_examples=60, deadline=None)
_CERT_STATUS = {"verified", "refuted", "error"}
_VERIFY_STATUS = {"valid", "invalid", "unknown", "error"}
_NL_STATUS = {"ok", "unknown", "error"}

_cell = st.integers(min_value=-9, max_value=9)
_row2 = st.lists(_cell, min_size=2, max_size=2)
_mat2 = st.lists(_row2, min_size=2, max_size=2)


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    """Extended Euclid (stdlib): returns (g, x, y) with a*x + b*y == g."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


# ------------------------------ no crash (fuzz) -------------------------- #
@_CFG
@given(st.lists(st.text(max_size=12), min_size=0, max_size=4))
def test_verify_derivation_never_crashes(steps):
    # Arbitrary junk steps with a fixed op list: returns a valid status, never throws.
    ops = [{"op": "simplify"}] * max(0, len(steps) - 1)
    assert verify_derivation(steps, ops).status in _VERIFY_STATUS


@_CFG
@given(st.text(max_size=40))
def test_interpret_never_crashes(text):
    assert interpret(text).status in _NL_STATUS


@_CFG
@given(st.dictionaries(st.text(max_size=6), st.text(max_size=6), max_size=4))
def test_check_certificate_never_crashes(cert):
    # Random dicts (missing/garbage fields) → error, never an exception.
    assert cc(cert).status in _CERT_STATUS


# --------------------- mathematical invariants --------------------------- #
@_CFG
@given(_mat2, _mat2)
def test_matrix_product_certificate_true_product_verifies(a, b):
    # The genuine A·B always verifies; a perturbed product is refuted.
    prod = [[sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
    A = [[str(x) for x in row] for row in a]
    B = [[str(x) for x in row] for row in b]
    P = [[str(x) for x in row] for row in prod]
    assert cc({"kind": "matrix_product", "a": A, "b": B, "product": P}).status == "verified"
    P[0][0] = str(prod[0][0] + 1)                       # perturb one cell
    assert cc({"kind": "matrix_product", "a": A, "b": B, "product": P}).status == "refuted"


@_CFG
@given(st.integers(min_value=1, max_value=5), st.integers(min_value=-6, max_value=6),
       st.integers(min_value=-9, max_value=9))
def test_verify_derivation_linear_solve_is_justified(a, root, b):
    # a*x + b == c  (c = a*root + b)  --subtract b--> a*x == a*root  --divide a--> x == root
    c = a * root + b
    steps = [f"{a}*x + {b} == {c}", f"{a}*x == {a * root}", f"x == {root}"]
    ops = [{"op": "subtract", "value": str(b)}, {"op": "divide", "value": str(a)}]
    assert verify_derivation(steps, ops).reason_code == "DERIVATION_VALID"


@_CFG
@given(st.integers(min_value=1, max_value=200), st.integers(min_value=1, max_value=200))
def test_bezout_certificate_from_extended_euclid_verifies(a, b):
    g, x, y = _egcd(a, b)
    assert g == math.gcd(a, b)
    cert = {"kind": "bezout_gcd", "a": str(a), "b": str(b),
            "g": str(g), "x": str(x), "y": str(y)}
    assert cc(cert).status == "verified"


@_CFG
@given(st.integers(min_value=2, max_value=5000))
def test_factorization_certificate_true_factors_verify(n):
    # Engine-agnostic property: the genuine prime factorization always verifies.
    factors = [[str(p), str(e)] for p, e in sympy.factorint(n).items()]
    assert cc({"kind": "factorization", "n": str(n), "factors": factors}).status == "verified"


@_CFG
@given(st.integers(min_value=-9, max_value=9), st.sampled_from(["x**2", "x**3", "sin(x)", "exp(x)"]))
def test_verify_derivative_agrees_with_sympy(_coef, expr):
    # The true derivative (computed by SymPy) is always accepted as valid.
    d = str(sympy.diff(sympy.sympify(expr), sympy.Symbol("x")))
    assert verify_derivative(expr, "x", d).status == "valid"


# ------------------------------ determinism ------------------------------- #
@_CFG
@given(st.integers(min_value=1, max_value=5), st.integers(min_value=-6, max_value=6))
def test_derivation_determinism(a, root):
    c = a * root
    steps = [f"{a}*x == {c}", f"x == {root}"]
    ops = [{"op": "divide", "value": str(a)}]
    first = verify_derivation(steps, ops).reason_code
    for _ in range(3):
        assert verify_derivation(steps, ops).reason_code == first


@_CFG
@given(st.integers(min_value=2, max_value=500))
def test_factorization_certificate_determinism(n):
    factors = [[str(p), str(e)] for p, e in sympy.factorint(n).items()]
    cert = {"kind": "factorization", "n": str(n), "factors": factors}
    first = cc(cert).status
    for _ in range(3):
        assert cc(cert).status == first


def test_interpret_determinism():
    for _ in range(5):
        assert interpret("derivative of x**3 with respect to x").reason_code == "UNDERSTOOD"
        assert interpret("48 ile 36 en büyük ortak bölen").interpretation["task"] == "gcd"
