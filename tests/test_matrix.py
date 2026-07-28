"""
Linear algebra (matrix) — SymPy Matrix layer:
determinant / matrix_inverse / eigenvalues / matrix_rank.

Best-case (known correct) + worst-case (singular, non-square, malicious input) together.
Cells may be symbolic; determinism consistent with ADR-0019.
"""
from mathhead.compute import determinant, eigenvalues, matrix_inverse, matrix_rank


# ---------------------------- determinant --------------------------------- #
def test_det_numeric_2x2():
    r = determinant([["1", "2"], ["3", "4"]])
    assert r.status == "ok"
    assert r.result == "-2"


def test_det_symbolic():
    # Symbolic cells: det[[a,b],[c,d]] = ad - bc
    assert determinant([["a", "b"], ["c", "d"]]).result == "a*d - b*c"


def test_det_identity_3x3():
    r = determinant([["1", "0", "0"], ["0", "1", "0"], ["0", "0", "1"]])
    assert r.result == "1"


def test_det_non_square_rejected():
    r = determinant([["1", "2", "3"], ["4", "5", "6"]])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# --------------------------- matrix_inverse ------------------------------- #
def test_inverse_2x2():
    r = matrix_inverse([["1", "2"], ["3", "4"]])
    assert r.status == "ok"
    assert r.result == [["-2", "1"], ["3/2", "-1/2"]]


def test_inverse_singular_honest_error():
    # Singular matrix (det=0) -> no fabrication, honest error
    r = matrix_inverse([["1", "2"], ["2", "4"]])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"
    assert "not invertible" in r.explanation


def test_inverse_non_square_rejected():
    assert matrix_inverse([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# ---------------------------- eigenvalues --------------------------------- #
def test_eigenvalues_diagonal():
    r = eigenvalues([["2", "0"], ["0", "3"]])
    assert r.status == "ok"
    assert r.result == [
        {"value": "2", "multiplicity": 1},
        {"value": "3", "multiplicity": 1},
    ]


def test_eigenvalues_complex():
    # Rotation matrix -> complex eigenvalues ±i (honestly in exact form)
    r = eigenvalues([["0", "-1"], ["1", "0"]])
    values = {d["value"] for d in r.result}
    assert values == {"I", "-I"}


def test_eigenvalues_defective_multiplicity():
    # Single eigenvalue, algebraic multiplicity 2 (not hidden)
    r = eigenvalues([["2", "1"], ["0", "2"]])
    assert r.result == [{"value": "2", "multiplicity": 2}]


def test_eigenvalues_non_square_rejected():
    assert eigenvalues([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# ---------------------------- matrix_rank --------------------------------- #
def test_rank_full():
    assert matrix_rank([["1", "0"], ["0", "1"]]).result == 2


def test_rank_deficient():
    # Second row is a multiple of the first -> rank 1
    assert matrix_rank([["1", "2"], ["2", "4"]]).result == 1


def test_rank_non_square():
    # Need not be square
    assert matrix_rank([["1", "2", "3"], ["4", "5", "6"]]).result == 2


# ------------------------- security / worst-case -------------------------- #
def test_matrix_empty_rejected():
    r = determinant([])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_matrix_ragged_rejected():
    # Not rectangular -> rejected
    assert determinant([["1", "2"], ["3"]]).status == "error"


def test_matrix_malicious_cell_rejected():
    # Non-whitelisted call in cell -> rejected (security invariant)
    assert determinant([["__import__('os')", "1"], ["0", "1"]]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_matrix_determinism():
    # Same input -> same output (including eigenvalue order; ADR-0019)
    for _ in range(5):
        assert determinant([["1", "2"], ["3", "4"]]).result == "-2"
        assert matrix_inverse([["1", "2"], ["3", "4"]]).result == [["-2", "1"], ["3/2", "-1/2"]]
        assert eigenvalues([["2", "0"], ["0", "3"]]).result == [
            {"value": "2", "multiplicity": 1},
            {"value": "3", "multiplicity": 1},
        ]
