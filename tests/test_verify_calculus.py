"""
Doğrulama katmanı II (ROADMAP I1) — kalkülüs & matris iddia türleri:
verify_derivative / verify_integral / verify_limit / verify_series /
verify_matrix_identity.

AI'ın "türev/integral/limit/seri/matris" iddialarını bağımsız denetler.
Best + worst + dürüst kenar durumları (+C sabit farkı, sembolik matris).
"""
from mathhead.core.verify import (
    verify_derivative,
    verify_integral,
    verify_limit,
    verify_matrix_identity,
    verify_series,
)


# ---------------------------- verify_derivative --------------------------- #
def test_derivative_correct():
    r = verify_derivative("x**3", "x", "3*x**2")
    assert r.status == "valid" and r.reason_code == "EQUAL"


def test_derivative_wrong_gives_correct():
    r = verify_derivative("x**3", "x", "3*x")
    assert r.status == "invalid"
    assert r.details["correct"] == "3*x**2"


def test_derivative_second_order():
    assert verify_derivative("x**3", "x", "6*x", order=2).status == "valid"


def test_derivative_malicious_rejected():
    assert verify_derivative("__import__('os')", "x", "0").status == "error"


# ----------------------------- verify_integral ---------------------------- #
def test_integral_correct():
    assert verify_integral("2*x", "x", "x**2").status == "valid"


def test_integral_constant_tolerated():
    # +C: x²+5 de geçerli antitürev (dürüst — sabit farkı hoş görülür)
    assert verify_integral("2*x", "x", "x**2 + 5").status == "valid"


def test_integral_wrong():
    assert verify_integral("2*x", "x", "x**3").status == "invalid"


def test_integral_trig():
    assert verify_integral("cos(x)", "x", "sin(x)").status == "valid"


# ------------------------------ verify_limit ------------------------------ #
def test_limit_correct():
    assert verify_limit("sin(x)/x", "x", "0", "1").status == "valid"


def test_limit_at_infinity():
    assert verify_limit("1/x", "x", "oo", "0").status == "valid"


def test_limit_wrong():
    r = verify_limit("sin(x)/x", "x", "0", "0")
    assert r.status == "invalid"
    assert r.details["correct"] == "1"


# ------------------------------ verify_series ----------------------------- #
def test_series_correct():
    # exp(x) 3. mertebe: 1 + x + x²/2
    assert verify_series("exp(x)", "x", "0", 3, "x**2/2 + x + 1").status == "valid"


def test_series_wrong():
    assert verify_series("exp(x)", "x", "0", 3, "x**2 + x + 1").status == "invalid"


# ------------------------- verify_matrix_identity ------------------------- #
def test_matrix_identity_equal():
    assert verify_matrix_identity([["1", "2"], ["3", "4"]],
                                  [["1", "2"], ["3", "4"]]).status == "valid"


def test_matrix_identity_symbolic_equal():
    # a+a = 2a (sembolik denklik yakalanır)
    assert verify_matrix_identity([["a + a"]], [["2*a"]]).status == "valid"


def test_matrix_identity_different_cell():
    r = verify_matrix_identity([["1", "2"], ["3", "4"]], [["1", "2"], ["3", "5"]])
    assert r.status == "invalid"
    assert r.details["cell"] == [1, 1]


def test_matrix_identity_dimension_mismatch():
    r = verify_matrix_identity([["1", "2"]], [["1"], ["2"]])
    assert r.status == "invalid"
    assert "boyut" in r.explanation


# ------------------------------ determinizm ------------------------------- #
def test_verify_calculus_determinism():
    for _ in range(5):
        assert verify_derivative("x**3", "x", "3*x**2").status == "valid"
        assert verify_integral("2*x", "x", "x**2 + 5").status == "valid"
        assert verify_limit("1/x", "x", "oo", "0").status == "valid"
