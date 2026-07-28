"""
Lineer cebir — tamamlama turu (Aşama 1):
matrix_multiply / matrix_solve (Ax=b) / eigenvectors / rref / nullspace /
lu_decomposition.

Best-case + worst-case (boyut uyumsuz, tutarsız sistem, kare-değil) + dürüstlük
(parametrik çözüm, trivial boş uzay) + determinizm.
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
    # A sütun (2) != B satır (1) -> dürüst hata
    r = matrix_multiply([["1", "2"]], [["1", "2"]])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# ---------------------------- matrix_solve -------------------------------- #
def test_matsolve_unique():
    r = matrix_solve([["1", "1"], ["1", "-1"]], ["10", "2"])
    assert r.status == "ok"
    assert r.result == [{"x0": "6", "x1": "4"}]


def test_matsolve_no_solution():
    # Tutarsız sistem -> boş liste (uydurma yok)
    r = matrix_solve([["1", "1"], ["1", "1"]], ["1", "2"])
    assert r.status == "ok"
    assert r.result == []


def test_matsolve_infinite_parametric():
    # Sonsuz çözüm -> serbest değişken parametrik görünür
    r = matrix_solve([["1", "1"], ["2", "2"]], ["3", "6"])
    assert r.status == "ok"
    assert r.result == [{"x0": "3 - x1", "x1": "x1"}]
    assert "parametrik" in r.explanation


def test_matsolve_dim_mismatch_rejected():
    # b uzunluğu satır sayısına eşit değil
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
    # Tam rank -> yalnız sıfır vektörü -> boş taban (dürüst)
    r = nullspace([["1", "0"], ["0", "1"]])
    assert r.status == "ok"
    assert r.result == []


# -------------------------- lu_decomposition ------------------------------ #
def test_lu_lower_upper_structure():
    r = lu_decomposition([["4", "3"], ["6", "3"]])
    assert r.status == "ok"
    L, U = r.result["L"], r.result["U"]
    # L alt üçgen (köşegen 1), U üst üçgen
    assert L[0][1] == "0"
    assert L[0][0] == "1" and L[1][1] == "1"
    assert U[1][0] == "0"


def test_lu_non_square_rejected():
    assert lu_decomposition([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_linalg_determinism():
    for _ in range(5):
        assert matrix_multiply([["1", "2"], ["3", "4"]], [["5", "6"], ["7", "8"]]).result == \
            [["19", "22"], ["43", "50"]]
        assert eigenvectors([["2", "0"], ["0", "3"]]).result[0]["eigenvalue"] == "2"
        assert nullspace([["1", "2"], ["2", "4"]]).result == [["-2", "1"]]
