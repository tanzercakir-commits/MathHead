"""
Linear algebra — completion round (Phase 1):
matrix_multiply / matrix_solve (Ax=b) / eigenvectors / rref / nullspace /
lu_decomposition.

Best-case + worst-case (dimension mismatch, inconsistent system, non-square) + honesty
(parametric solution, trivial null space) + determinism.
"""
from mathhead.compute import (
    eigenvectors,
    lu_decomposition,
    matrix_multiply,
    matrix_solve,
    nullspace,
    rref,
)


# --------------------------- matrix_multiply ------------------------------ #
def test_matmul_2x2():
    r = matrix_multiply([["1", "2"], ["3", "4"]], [["5", "6"], ["7", "8"]])
    assert r.status == "ok"
    assert r.result == [["19", "22"], ["43", "50"]]


def test_matmul_identity():
    A = [["2", "5"], ["1", "3"]]
    assert matrix_multiply([["1", "0"], ["0", "1"]], A).result == A


def test_matmul_dim_mismatch_rejected():
    # A columns (2) != B rows (1) -> honest error
    r = matrix_multiply([["1", "2"]], [["1", "2"]])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# ---------------------------- matrix_solve -------------------------------- #
def test_matsolve_unique():
    r = matrix_solve([["1", "1"], ["1", "-1"]], ["10", "2"])
    assert r.status == "ok"
    assert r.result == [{"x0": "6", "x1": "4"}]


def test_matsolve_no_solution():
    # Inconsistent system -> empty list (no fabrication)
    r = matrix_solve([["1", "1"], ["1", "1"]], ["1", "2"])
    assert r.status == "ok"
    assert r.result == []


def test_matsolve_infinite_parametric():
    # Infinite solutions -> free variable appears parametrically
    r = matrix_solve([["1", "1"], ["2", "2"]], ["3", "6"])
    assert r.status == "ok"
    assert r.result == [{"x0": "3 - x1", "x1": "x1"}]
    assert "parametric" in r.explanation


def test_matsolve_dim_mismatch_rejected():
    # length of b is not equal to the number of rows
    assert matrix_solve([["1", "1"], ["1", "-1"]], ["10"]).status == "error"


# ---------------------------- eigenvectors -------------------------------- #
def test_eigenvectors_diagonal():
    r = eigenvectors([["2", "0"], ["0", "3"]])
    assert r.status == "ok"
    assert r.result == [
        {"eigenvalue": "2", "multiplicity": 1, "vectors": [["1", "0"]]},
        {"eigenvalue": "3", "multiplicity": 1, "vectors": [["0", "1"]]},
    ]


def test_eigenvectors_non_square_rejected():
    assert eigenvectors([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# -------------------------------- rref ------------------------------------ #
def test_rref_singular_3x3():
    r = rref([["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]])
    assert r.status == "ok"
    assert r.result["pivots"] == [0, 1]
    assert r.result["rref"] == [["1", "0", "-1"], ["0", "1", "2"], ["0", "0", "0"]]


# ------------------------------ nullspace --------------------------------- #
def test_nullspace_rank_deficient():
    r = nullspace([["1", "2"], ["2", "4"]])
    assert r.status == "ok"
    assert r.result == [["-2", "1"]]


def test_nullspace_trivial():
    # Full rank -> only the zero vector -> empty basis (honest)
    r = nullspace([["1", "0"], ["0", "1"]])
    assert r.status == "ok"
    assert r.result == []


# -------------------------- lu_decomposition ------------------------------ #
def test_lu_lower_upper_structure():
    r = lu_decomposition([["4", "3"], ["6", "3"]])
    assert r.status == "ok"
    L, U = r.result["L"], r.result["U"]
    # L lower triangular (diagonal 1), U upper triangular
    assert L[0][1] == "0"
    assert L[0][0] == "1" and L[1][1] == "1"
    assert U[1][0] == "0"


def test_lu_non_square_rejected():
    assert lu_decomposition([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_linalg_determinism():
    for _ in range(5):
        assert matrix_multiply([["1", "2"], ["3", "4"]], [["5", "6"], ["7", "8"]]).result == \
            [["19", "22"], ["43", "50"]]
        assert eigenvectors([["2", "0"], ["0", "3"]]).result[0]["eigenvalue"] == "2"
        assert nullspace([["1", "2"], ["2", "4"]]).result == [["-2", "1"]]
