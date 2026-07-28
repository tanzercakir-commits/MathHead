"""
Precision bridge (ROADMAP G3) — evaluate_precision / verify_numeric /
cross_check_numeric.

Arbitrary precision + numeric-claim verification + SYMBOLIC↔NUMERIC cross-validation
(the same 'two independent paths must agree' philosophy as the Track C verifiers).
"""
from mathhead.compute import (
    cross_check_numeric,
    evaluate_precision,
    verify_numeric,
)


# --------------------------- evaluate_precision --------------------------- #
def test_pi_to_fifty_digits():
    r = evaluate_precision("pi", 50)
    assert r.status == "ok"
    assert r.result.startswith("3.14159265358979323846264338327950288419716939937")
    assert len(r.result.replace(".", "")) >= 50


def test_evaluate_constant_combination():
    # sqrt(2) + e
    r = evaluate_precision("sqrt(2) + E", 15)
    assert r.result.startswith("4.13249539083214")


def test_evaluate_with_free_symbol_rejected():
    assert evaluate_precision("x**2", 10).status == "error"


def test_evaluate_bad_digits_rejected():
    assert evaluate_precision("pi", 0).status == "error"


# ----------------------------- verify_numeric ----------------------------- #
def test_verify_numeric_correct_claim():
    r = verify_numeric("pi", "3.14159265358979", 1e-12)
    assert r.status == "ok"
    assert r.result["match"] is True


def test_verify_numeric_wrong_claim():
    r = verify_numeric("pi", "3.14", 1e-6)
    assert r.result["match"] is False


def test_verify_numeric_euler():
    assert verify_numeric("E", "2.718281828", 1e-6).result["match"] is True


def test_verify_numeric_symbol_rejected():
    assert verify_numeric("x", "1").status == "error"


# --------------------------- cross_check_numeric -------------------------- #
def test_cross_check_trig_identity():
    # sin²+cos² = 1 everywhere → symbolic and numeric agree at x=1.3
    r = cross_check_numeric("sin(x)**2 + cos(x)**2", "x", "1.3")
    assert r.status == "ok"
    assert r.result["agree"] is True


def test_cross_check_polynomial():
    # x³ − 2x at x=3 = 21 (both paths)
    r = cross_check_numeric("x**3 - 2*x", "x", "3")
    assert r.result["agree"] is True
    assert float(r.result["symbolic_value"]) == 21.0


def test_cross_check_transcendental():
    # exp(1) at x... use exp(x) at x=0 = 1
    r = cross_check_numeric("exp(x)", "x", "0")
    assert r.result["agree"] is True


def test_cross_check_extra_symbol_rejected():
    assert cross_check_numeric("x*y", "x", "1").status == "error"


# ------------------------------ determinism ------------------------------- #
def test_precision_determinism():
    for _ in range(5):
        assert evaluate_precision("pi", 30).result == evaluate_precision("pi", 30).result
        assert verify_numeric("pi", "3.14", 1e-6).result["match"] is False
        assert cross_check_numeric("sin(x)**2 + cos(x)**2", "x", "1.3").result["agree"] is True
