"""
Eşitsizlik ispatı & nonlineer gerçel aritmetik (ROADMAP Aşama 9) —
prove_inequality / prove_nonnegative / find_real_solution (Z3 NRA).

Best-case (bilinen eşitsizlikler) + worst-case (yanlış eşitsizlik → karşıörnek,
gramer ihlali) + dürüstlük (unknown/hata birinci sınıf).
"""
from mathhead.core.inequality import (
    find_real_solution,
    prove_inequality,
    prove_nonnegative,
)


# ---------------------------- prove_inequality ---------------------------- #
def test_square_nonnegative():
    r = prove_inequality("x**2 >= 0")
    assert r.status == "valid"
    assert r.reason_code == "ENTAILED"


def test_am_gm_two_vars():
    # x² + y² ≥ 2xy  ((x-y)² ≥ 0)
    assert prove_inequality("x**2 + y**2 >= 2*x*y").status == "valid"


def test_square_completion():
    # x² + 1 ≥ 2x  ((x-1)² ≥ 0)
    assert prove_inequality("x**2 + 1 >= 2*x").status == "valid"


def test_false_inequality_gives_counterexample():
    # x² ≥ x  0<x<1 için YANLIŞ -> karşıörnek
    r = prove_inequality("x**2 >= x")
    assert r.status == "invalid"
    assert r.reason_code == "COUNTEREXAMPLE_FOUND"
    assert r.witness is not None


def test_inequality_under_assumptions():
    # x>0, y>0  ⊨  x + y > 0
    assert prove_inequality("x + y > 0", ["x > 0", "y > 0"]).status == "valid"


def test_goal_must_be_boolean():
    # Salt aritmetik ifade (karşılaştırma değil) -> hata
    r = prove_inequality("x + 1")
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_non_polynomial_exponent_rejected():
    # Değişken üs (nonpolinom) -> reddedilir
    assert prove_inequality("x**y >= 0").status == "error"


def test_malicious_rejected():
    assert prove_inequality("__import__('os') >= 0").status == "error"


# --------------------------- prove_nonnegative ---------------------------- #
def test_nonnegative_perfect_square():
    # x² - 2x + 1 = (x-1)² ≥ 0
    assert prove_nonnegative("x**2 - 2*x + 1").status == "valid"


def test_nonnegative_false():
    # x² - 2x  x=1'de -1 < 0 -> karşıörnek
    r = prove_nonnegative("x**2 - 2*x")
    assert r.status == "invalid"


# --------------------------- find_real_solution --------------------------- #
def test_real_solution_exists():
    # Çember ∩ doğru -> gerçel çözüm var
    r = find_real_solution(["x**2 + y**2 == 1", "x == y"])
    assert r.status == "sat"
    assert r.witness is not None


def test_real_solution_none():
    # x² = -1 -> gerçel çözüm yok
    r = find_real_solution(["x**2 == -1"])
    assert r.status == "unsat"
    assert r.reason_code == "NO_MODEL"


def test_real_solution_empty_rejected():
    assert find_real_solution([]).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_inequality_determinism():
    for _ in range(5):
        assert prove_inequality("x**2 >= 0").status == "valid"
        assert prove_inequality("x**2 >= x").status == "invalid"
        assert find_real_solution(["x**2 == -1"]).status == "unsat"
