"""
Linear algebra III (ROADMAP E2) — decompositions & matrix functions:
singular_values / qr / cholesky / gram_schmidt / pseudoinverse /
matrix_exponential / jordan_form / characteristic_polynomial / least_squares.

Best-case (known exact values) + worst-case (precondition failures) + honesty +
determinism.
"""
from mathhead.compute import (
    characteristic_polynomial,
    cholesky_decomposition,
    gram_schmidt,
    jordan_form,
    least_squares,
    matrix_exponential,
    pseudoinverse,
    qr_decomposition,
    singular_values,
)


# ---------------------------- singular_values ----------------------------- #
def test_singular_values_exact():
    r = singular_values([["4", "0"], ["3", "-5"]])
    assert r.status == "ok"
    assert r.result == ["2*sqrt(10)", "sqrt(10)"]


# ------------------------------- QR --------------------------------------- #
def test_qr_reconstructs_matrix():
    # Q·R must equal A (verified numerically via sympy on the string output)
    import sympy
    A = [["1", "1"], ["0", "1"], ["1", "0"]]
    r = qr_decomposition(A)
    assert r.status == "ok"
    Q = sympy.Matrix([[sympy.sympify(c) for c in row] for row in r.result["Q"]])
    R = sympy.Matrix([[sympy.sympify(c) for c in row] for row in r.result["R"]])
    assert (Q * R) == sympy.Matrix([[1, 1], [0, 1], [1, 0]])


# ----------------------------- Cholesky ----------------------------------- #
def test_cholesky_positive_definite():
    r = cholesky_decomposition([["4", "2"], ["2", "3"]])
    assert r.status == "ok"
    assert r.result["L"] == [["2", "0"], ["1", "sqrt(2)"]]


def test_cholesky_not_positive_definite_rejected():
    r = cholesky_decomposition([["1", "2"], ["2", "1"]])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


# ---------------------------- Gram-Schmidt -------------------------------- #
def test_gram_schmidt_orthonormal():
    r = gram_schmidt([["1", "1", "0"], ["1", "0", "1"]])
    assert r.status == "ok"
    # first normalized vector has unit-length components
    assert r.result[0] == ["sqrt(2)/2", "sqrt(2)/2", "0"]


# ---------------------------- pseudoinverse ------------------------------- #
def test_pseudoinverse_column_vector():
    r = pseudoinverse([["1"], ["2"]])
    assert r.status == "ok"
    assert r.result == [["1/5", "2/5"]]


# ------------------------- matrix_exponential ----------------------------- #
def test_matrix_exp_nilpotent():
    # e^[[0,1],[0,0]] = I + N = [[1,1],[0,1]]
    r = matrix_exponential([["0", "1"], ["0", "0"]])
    assert r.result == [["1", "1"], ["0", "1"]]


def test_matrix_exp_non_square_rejected():
    assert matrix_exponential([["1", "2", "3"]]).status == "error"


# ---------------------------- jordan_form --------------------------------- #
def test_jordan_form_defective_matrix():
    # [[2,1],[0,2]] is already a Jordan block
    r = jordan_form([["2", "1"], ["0", "2"]])
    assert r.status == "ok"
    assert r.result["J"] == [["2", "1"], ["0", "2"]]


# ---------------------- characteristic_polynomial ------------------------- #
def test_characteristic_polynomial_diagonal():
    # det(diag(2,3) - λI) = (2-λ)(3-λ) = λ² - 5λ + 6
    r = characteristic_polynomial([["2", "0"], ["0", "3"]])
    assert r.result == "lambda**2 - 5*lambda + 6"


def test_characteristic_polynomial_non_square_rejected():
    assert characteristic_polynomial([["1", "2", "3"]]).status == "error"


# ---------------------------- least_squares ------------------------------- #
def test_least_squares_overdetermined():
    # best fit line through (1,1),(2,2),(3,2): intercept 2/3, slope 1/2
    r = least_squares([["1", "1"], ["1", "2"], ["1", "3"]], ["1", "2", "2"])
    assert r.status == "ok"
    assert r.result == ["2/3", "1/2"]


def test_least_squares_dim_mismatch_rejected():
    assert least_squares([["1", "1"], ["1", "2"]], ["1"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_linalg3_determinism():
    for _ in range(5):
        assert singular_values([["4", "0"], ["3", "-5"]]).result == ["2*sqrt(10)", "sqrt(10)"]
        assert matrix_exponential([["0", "1"], ["0", "0"]]).result == [["1", "1"], ["0", "1"]]
        assert characteristic_polynomial([["2", "0"], ["0", "3"]]).result == "lambda**2 - 5*lambda + 6"
