"""
Lineer cebir (matris) — SymPy Matrix katmanı:
determinant / matrix_inverse / eigenvalues / matrix_rank.

Best-case (bilinen doğru) + worst-case (tekil, kare-değil, kötücül girdi) birlikte.
Hücreler sembolik olabilir; determinizm ADR-0019 ile uyumlu.
"""
from mathhead.compute import determinant, eigenvalues, matrix_inverse, matrix_rank


# ---------------------------- determinant --------------------------------- #
def test_det_numeric_2x2():
    r = determinant([["1", "2"], ["3", "4"]])
    assert r.status == "ok"
    assert r.result == "-2"


def test_det_symbolic():
    # Sembolik hücreler: det[[a,b],[c,d]] = ad - bc
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
    # Tekil matris (det=0) -> uydurma yok, dürüst hata
    r = matrix_inverse([["1", "2"], ["2", "4"]])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"
    assert "tersinir değil" in r.explanation


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
    # Döndürme matrisi -> karmaşık özdeğerler ±i (dürüstçe tam formda)
    r = eigenvalues([["0", "-1"], ["1", "0"]])
    values = {d["value"] for d in r.result}
    assert values == {"I", "-I"}


def test_eigenvalues_defective_multiplicity():
    # Tek özdeğer, cebirsel katlılık 2 (gizlenmez)
    r = eigenvalues([["2", "1"], ["0", "2"]])
    assert r.result == [{"value": "2", "multiplicity": 2}]


def test_eigenvalues_non_square_rejected():
    assert eigenvalues([["1", "2", "3"], ["4", "5", "6"]]).status == "error"


# ---------------------------- matrix_rank --------------------------------- #
def test_rank_full():
    assert matrix_rank([["1", "0"], ["0", "1"]]).result == 2


def test_rank_deficient():
    # İkinci satır birincinin katı -> rank 1
    assert matrix_rank([["1", "2"], ["2", "4"]]).result == 1


def test_rank_non_square():
    # Kare olması şart değil
    assert matrix_rank([["1", "2", "3"], ["4", "5", "6"]]).result == 2


# ------------------------- güvenlik / worst-case -------------------------- #
def test_matrix_empty_rejected():
    r = determinant([])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_matrix_ragged_rejected():
    # Dikdörtgen değil -> reddedilir
    assert determinant([["1", "2"], ["3"]]).status == "error"


def test_matrix_malicious_cell_rejected():
    # Beyaz liste dışı çağrı hücrede -> reddedilir (güvenlik değişmezi)
    assert determinant([["__import__('os')", "1"], ["0", "1"]]).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_matrix_determinism():
    # Aynı girdi -> aynı çıktı (özdeğer sırası dahil; ADR-0019)
    for _ in range(5):
        assert determinant([["1", "2"], ["3", "4"]]).result == "-2"
        assert matrix_inverse([["1", "2"], ["3", "4"]]).result == [["-2", "1"], ["3/2", "-1/2"]]
        assert eigenvalues([["2", "0"], ["0", "3"]]).result == [
            {"value": "2", "multiplicity": 1},
            {"value": "3", "multiplicity": 1},
        ]
