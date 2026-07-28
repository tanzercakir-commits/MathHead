"""
Bağımsız sertifika denetleyicisi (ROADMAP Track C2) — check_certificate.

Öne geçiren özellik: MathHead'in ÜRETTİĞİ sonuç, o sonucu üreten motordan
(Z3/SymPy) BAĞIMSIZ, yalnız stdlib bir checker'la yeniden doğrulanabilir.
En kritik test: modülün z3/sympy'yi FİİLEN yüklemediğini (alt-süreçle) kanıtlamak.
"""
import subprocess
import sys

from mathhead.certificate import check_certificate as cc
from mathhead.frontier import subset_sum


# ----------------------- BAĞIMSIZLIK (killer kanıt) ----------------------- #
def test_checker_is_engine_independent():
    # mathhead.certificate import edilince z3/sympy sys.modules'e GİRMEMELİ.
    code = (
        "import sys, mathhead.certificate; "
        "bad=[m for m in ('z3','sympy') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"checker bağımsız değil, yüklenen: {r.stdout} {r.stderr}"


# --------------------------- uçtan uca döngü ------------------------------ #
def test_end_to_end_subset_sum_then_independent_check():
    # 1) Motor (Z3) subset_sum çözer  2) tanığı bağımsız checker'a ver  3) tutmalı
    res = subset_sum([3, 34, 4, 12, 5, 2], 9)
    assert res.status == "sat"
    cert = {"kind": "subset_sum", "numbers": [3, 34, 4, 12, 5, 2],
            "target": 9, "indices": res.witness["indices"]}
    out = cc(cert)
    assert out.status == "verified"
    assert out.verified is True


# ------------------------------ türler ------------------------------------ #
def test_subset_sum_refuted():
    r = cc({"kind": "subset_sum", "numbers": [3, 4, 2], "target": 9, "indices": [0, 1]})
    assert r.status == "refuted"


def test_graph_coloring_verified_and_refuted():
    assert cc({"kind": "graph_coloring", "edges": [[1, 2], [2, 3], [1, 3]],
               "colors": 3, "coloring": {"1": 0, "2": 1, "3": 2}}).status == "verified"
    assert cc({"kind": "graph_coloring", "edges": [[1, 2]], "colors": 2,
               "coloring": {"1": 0, "2": 0}}).status == "refuted"


def test_solution_exact_verified_and_refuted():
    ok = cc({"kind": "solution", "expression": "x**2 - 4", "symbol": "x", "value": "2"})
    assert ok.status == "verified" and ok.exact is True
    bad = cc({"kind": "solution", "expression": "x**2 - 4", "symbol": "x", "value": "3"})
    assert bad.status == "refuted"


def test_solution_rational_exact():
    # 1/2 kökü: 2x - 1 = 0  ->  tam (Fraction) doğrulanır
    r = cc({"kind": "solution", "expression": "2*x - 1", "symbol": "x", "value": "1/2"})
    assert r.status == "verified" and r.exact is True


def test_not_equal_counterexample_check():
    # geçerli karşıörnek: 2x ≠ 3x @ x=1
    assert cc({"kind": "not_equal", "left": "2*x", "right": "3*x",
               "point": {"x": "1"}}).status == "verified"
    # geçersiz karşıörnek: x+x = 2x her yerde -> refuted
    assert cc({"kind": "not_equal", "left": "x+x", "right": "2*x",
               "point": {"x": "5"}}).status == "refuted"


def test_inequality_counterexample_exact():
    # x²-x @ 1/2 = -1/4 < 0  ->  'x²-x >= 0' iddiasının karşıörneği (tam)
    r = cc({"kind": "inequality_counterexample", "expression": "x**2 - x",
            "point": {"x": "1/2"}, "relation": ">="})
    assert r.status == "verified" and r.exact is True


def test_transcendental_is_numerical_not_exact():
    r = cc({"kind": "solution", "expression": "sin(x)", "symbol": "x", "value": "0"})
    assert r.status == "verified" and r.exact is False   # dürüst: sayısal


# ------------------------------ güvenlik ---------------------------------- #
def test_malicious_expression_rejected():
    assert cc({"kind": "solution", "expression": "__import__('os')",
               "symbol": "x", "value": "0"}).status == "error"


def test_unknown_kind_rejected():
    assert cc({"kind": "quantum"}).status == "error"


def test_determinism():
    for _ in range(5):
        assert cc({"kind": "solution", "expression": "x**2 - 4",
                   "symbol": "x", "value": "2"}).verified is True
