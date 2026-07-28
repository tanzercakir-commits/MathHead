"""
Sayı teorisi (ROADMAP Aşama 3) — gcd/lcm, asallık, çarpanlara ayırma,
modüler ters, Çin Kalan Teoremi (CRT), doğrusal Diophantine.

Best-case (bilinen değer) + worst-case (ters yok, çözümsüz sistem, sembol) +
dürüstlük (çözüm yok → boş / hata, gizleme yok).
"""
from mathhead.compute import (
    chinese_remainder,
    factorize,
    gcd,
    is_prime,
    lcm,
    linear_diophantine,
    modular_inverse,
)


# ------------------------------- gcd / lcm -------------------------------- #
def test_gcd_basic():
    assert gcd(48, 36).result == 12


def test_lcm_basic():
    assert lcm(4, 6).result == 12


def test_gcd_accepts_ast_power():
    # Girdi ast-whitelist ile süzülür: "2**10" = 1024 -> gcd(1024,48)=16
    assert gcd("2**10", 48).result == 16


def test_gcd_symbol_rejected():
    r = gcd("x", 2)
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# -------------------------------- is_prime -------------------------------- #
def test_is_prime_true():
    assert is_prime(97).result is True


def test_is_prime_false_composite():
    # 91 = 7·13 (gözle asal görünür ama değil)
    assert is_prime(91).result is False


# -------------------------------- factorize ------------------------------- #
def test_factorize_360():
    r = factorize(360)
    assert r.status == "ok"
    assert r.result == [
        {"prime": 2, "exponent": 3},
        {"prime": 3, "exponent": 2},
        {"prime": 5, "exponent": 1},
    ]


def test_factorize_one_is_empty():
    # 1'in asal çarpanı yok -> boş liste (dürüst)
    assert factorize(1).result == []


def test_factorize_nonpositive_rejected():
    assert factorize(-5).status == "error"
    assert factorize(0).status == "error"


# ----------------------------- modular_inverse ---------------------------- #
def test_modinv_exists():
    # 3·4 = 12 ≡ 1 (mod 11)
    assert modular_inverse(3, 11).result == 4


def test_modinv_none_honest_error():
    # gcd(4,8)=4 ≠ 1 -> ters yok, uydurma yok
    r = modular_inverse(4, 8)
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"
    assert "tersi yok" in r.explanation


# --------------------------- chinese_remainder ---------------------------- #
def test_crt_solvable():
    # x≡2(3), x≡3(5), x≡2(7) -> x=23 (mod 105)
    r = chinese_remainder([3, 5, 7], [2, 3, 2])
    assert r.status == "ok"
    assert r.result == {"x": 23, "modulus": 105}


def test_crt_inconsistent_honest_error():
    # mod 4 ≡1 ve mod 6 ≡2 bağdaşmaz -> çözüm yok
    r = chinese_remainder([4, 6], [1, 2])
    assert r.status == "error"
    assert "çözüm yok" in r.explanation


def test_crt_length_mismatch_rejected():
    assert chinese_remainder([3, 5], [1]).status == "error"


# --------------------------- linear_diophantine --------------------------- #
def test_diophantine_parametric():
    # 3x + 6y = 9 -> (3 - 2·t_0, t_0)
    r = linear_diophantine(3, 6, 9)
    assert r.status == "ok"
    assert r.result == [{"x": "3 - 2*t_0", "y": "t_0"}]


def test_diophantine_no_solution():
    # gcd(2,4)=2 ∤ 5 -> tam sayı çözüm yok (boş liste, dürüst)
    r = linear_diophantine(2, 4, 5)
    assert r.status == "ok"
    assert r.result == []


def test_diophantine_both_zero_rejected():
    assert linear_diophantine(0, 0, 5).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_numbertheory_determinism():
    for _ in range(5):
        assert factorize(360).result == [
            {"prime": 2, "exponent": 3},
            {"prime": 3, "exponent": 2},
            {"prime": 5, "exponent": 1},
        ]
        assert gcd(48, 36).result == 12
        assert chinese_remainder([3, 5, 7], [2, 3, 2]).result == {"x": 23, "modulus": 105}
