"""
Kombinatorik & ayrık (ROADMAP Aşama 4) — permütasyon/kombinasyon, faktöriyel,
tam sayı bölüntüleri, doğrusal özyineleme (recurrence) kapalı-form çözümü.

Best-case + worst-case (negatif, doğrusal olmayan, kötücül) + dürüstlük
(kapalı form yoksa hata) + determinizm.
"""
import sympy

from mathhead.compute import (
    combinations,
    factorial,
    partition_count,
    permutations,
    solve_recurrence,
)


# ----------------------------- permutations ------------------------------- #
def test_permutations_basic():
    assert permutations(10, 3).result == 720


def test_permutations_k_gt_n_is_zero():
    # 5 nesneden 7'li sıralı seçim imkânsız -> 0
    assert permutations(5, 7).result == 0


def test_permutations_negative_rejected():
    assert permutations(-1, 2).status == "error"


# ----------------------------- combinations ------------------------------- #
def test_combinations_basic():
    assert combinations(10, 3).result == 120


def test_combinations_symmetry():
    # C(n,k) = C(n,n-k)
    assert combinations(10, 3).result == combinations(10, 7).result


def test_combinations_k_gt_n_is_zero():
    assert combinations(5, 7).result == 0


# ------------------------------- factorial -------------------------------- #
def test_factorial_basic():
    assert factorial(6).result == 720


def test_factorial_zero():
    assert factorial(0).result == 1


def test_factorial_negative_rejected():
    assert factorial(-3).status == "error"


# ---------------------------- partition_count ----------------------------- #
def test_partition_10():
    assert partition_count(10).result == 42


def test_partition_zero():
    # p(0) = 1 (boş bölüntü)
    assert partition_count(0).result == 1


# ---------------------------- solve_recurrence ---------------------------- #
def test_recurrence_fibonacci_closed_form():
    # y(n)=y(n-1)+y(n-2), y0=0, y1=1 -> kapalı form; Fib(10)=55 doğrula
    r = solve_recurrence("y(n) = y(n-1) + y(n-2)", "y", "n", {"0": "0", "1": "1"})
    assert r.status == "ok"
    n = sympy.symbols("n")
    val = sympy.simplify(sympy.sympify(r.result).subs(n, 10))
    assert val == 55


def test_recurrence_geometric():
    # y(n)=2·y(n-1), y0=1 -> 2**n
    r = solve_recurrence("y(n) = 2*y(n-1)", "y", "n", {"0": "1"})
    assert r.status == "ok"
    assert r.result == "2**n"


def test_recurrence_equality_form_accepted():
    # '==' de kabul edilir
    r = solve_recurrence("y(n) == 3*y(n-1)", "y", "n", {"0": "1"})
    assert r.result == "3**n"


def test_recurrence_nonlinear_honest_error():
    # Doğrusal olmayan -> kapalı form yok, uydurma yok
    r = solve_recurrence("y(n) = y(n-1)**2", "y", "n", {"0": "2"})
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_recurrence_malicious_rejected():
    assert solve_recurrence("__import__('os')", "y", "n", {}).status == "error"


def test_recurrence_unknown_name_rejected():
    # Tanımsız fonksiyon adı (z) -> reddedilir
    assert solve_recurrence("y(n) = z(n-1)", "y", "n", {"0": "1"}).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_combinatorics_determinism():
    for _ in range(5):
        assert combinations(10, 3).result == 120
        assert partition_count(10).result == 42
        assert solve_recurrence("y(n) = 2*y(n-1)", "y", "n", {"0": "1"}).result == "2**n"
