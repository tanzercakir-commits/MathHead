"""
Complex analysis (ROADMAP D4) — residue / contour_integral / laurent_series /
complex_parts.

Best-case (known values) + residue theorem + Euler's identity + honesty (error
first-class) + determinism. `I` is the imaginary unit (compute constant).
"""
from mathhead.compute import (
    complex_parts,
    contour_integral,
    laurent_series,
    residue,
)


# -------------------------------- residue --------------------------------- #
def test_residue_simple_pole():
    # Res(1/z, 0) = 1
    r = residue("1/z", "z", "0")
    assert r.status == "ok"
    assert r.result == "1"


def test_residue_complex_pole():
    # Res(1/(z²+1), I) = -I/2
    assert residue("1/(z**2 + 1)", "z", "I").result == "-I/2"


def test_residue_at_regular_point_is_zero():
    # a regular point has residue 0 — the correct answer, not an error
    r = residue("z**2", "z", "1")
    assert r.status == "ok"
    assert r.result == "0"


def test_residue_malicious_rejected():
    assert residue("__import__('os')", "z", "0").status == "error"


# ---------------------------- contour_integral ---------------------------- #
def test_contour_residue_theorem():
    # ∮ 1/(z²+1) dz enclosing only the pole at I  =  2πi·Res = π
    r = contour_integral("1/(z**2 + 1)", "z", ["I"])
    assert r.status == "ok"
    assert r.result == "pi"


def test_contour_enclosing_both_poles_cancels():
    # enclosing both ±I → residues cancel → 0
    assert contour_integral("1/(z**2 + 1)", "z", ["I", "-I"]).result == "0"


def test_contour_empty_poles_rejected():
    r = contour_integral("1/z", "z", [])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# ----------------------------- laurent_series ----------------------------- #
def test_laurent_has_negative_powers():
    # exp(z)/z² = z^-2 + z^-1 + 1/2 + z/6 + ...
    r = laurent_series("exp(z)/z**2", "z", "0", 3)
    assert r.status == "ok"
    assert "z**(-2)" in r.result and "1/z" in r.result


def test_laurent_removable_singularity():
    # sin(z)/z has a removable singularity → ordinary Taylor part (1 - z²/6 + ...)
    r = laurent_series("sin(z)/z", "z", "0", 5)
    assert r.status == "ok"
    assert "z**(-1)" not in r.result


def test_laurent_bad_order_rejected():
    assert laurent_series("1/z", "z", "0", 0).status == "error"


# ------------------------------ complex_parts ----------------------------- #
def test_complex_parts_multiplication():
    # (2 + 3i)(1 - i) = 5 + i
    r = complex_parts("(2 + 3*I)*(1 - I)")
    assert r.status == "ok"
    assert r.result == {"real": "5", "imag": "1"}


def test_complex_parts_euler_identity():
    # e^{iπ} = -1  →  real -1, imag 0
    r = complex_parts("exp(I*pi)")
    assert r.result == {"real": "-1", "imag": "0"}


# ------------------------------ determinism ------------------------------- #
def test_complex_determinism():
    for _ in range(5):
        assert residue("1/(z**2 + 1)", "z", "I").result == "-I/2"
        assert contour_integral("1/(z**2 + 1)", "z", ["I"]).result == "pi"
        assert complex_parts("(2 + 3*I)*(1 - I)").result == {"real": "5", "imag": "1"}
