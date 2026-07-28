"""
Kalkülüs & sistemler — SymPy hesap katmanının genişlemesi:
limit / series (Taylor) / solve_system.

Best-case (bilinen doğru sonuç) + worst-case (dürüst hata / boş çözüm) birlikte.
"""
from mathhead.compute import limit, series, solve_system


# -------------------------------- limit ----------------------------------- #
def test_limit_sinc_at_zero():
    # Klasik: lim x→0 sin(x)/x = 1
    r = limit("sin(x)/x", "x", "0")
    assert r.status == "ok"
    assert r.result == "1"


def test_limit_at_infinity():
    # lim x→∞ 1/x = 0
    assert limit("1/x", "x", "oo").result == "0"


def test_limit_one_sided_plus():
    # lim x→0⁺ 1/x = +∞
    assert limit("1/x", "x", "0", "+").result == "oo"


def test_limit_one_sided_minus():
    # lim x→0⁻ 1/x = -∞
    assert limit("1/x", "x", "0", "-").result == "-oo"


def test_limit_euler_number():
    # lim n→∞ (1 + 1/n)^n = e  (dürüst güç: bilinen sabit yeniden üretilir)
    assert limit("(1 + 1/n)**n", "n", "oo").result == "E"


def test_limit_polynomial_finite_point():
    assert limit("x**2 + 1", "x", "2").result == "5"


def test_limit_bad_direction_rejected():
    r = limit("1/x", "x", "0", "sideways")
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_limit_unknown_function_rejected():
    # Beyaz liste dışı çağrı -> reddedilir (güvenlik değişmezi korunur)
    assert limit("foo(x)", "x", "0").status == "error"


# -------------------------------- series ----------------------------------- #
def test_series_exp():
    # exp(x) = 1 + x + x²/2 + x³/6 + x⁴/24 (5. mertebe)
    r = series("exp(x)", "x", "0", 5)
    assert r.status == "ok"
    assert r.result == "x**4/24 + x**3/6 + x**2/2 + x + 1"


def test_series_cos():
    assert series("cos(x)", "x", "0", 4).result == "1 - x**2/2"


def test_series_around_nonzero_point():
    # log(x), x=1 civarı: (x-1) - (x-1)²/2 + ...
    r = series("log(x)", "x", "1", 3)
    assert r.status == "ok"
    assert "x" in r.result  # somut açılım döner (değerlendirilmemiş değil)


def test_series_bad_order_rejected():
    r = series("exp(x)", "x", "0", 0)
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# ------------------------------ solve_system ------------------------------- #
def test_solve_system_unique():
    # x+y=10, x-y=2  ->  x=6, y=4
    r = solve_system(["x + y == 10", "x - y == 2"], ["x", "y"])
    assert r.status == "ok"
    assert r.result == [{"x": "6", "y": "4"}]


def test_solve_system_no_solution():
    # Çelişen kısıtlar -> boş liste (dürüst: "çözüm yok", uydurma yok)
    r = solve_system(["x + y == 1", "x + y == 2"], ["x", "y"])
    assert r.status == "ok"
    assert r.result == []


def test_solve_system_nonlinear_two_solutions():
    # Çember ∩ doğru -> iki çözüm
    r = solve_system(["x**2 + y**2 == 25", "x - y == 1"], ["x", "y"])
    assert r.status == "ok"
    xs = {sol["x"] for sol in r.result}
    assert xs == {"-3", "4"}


def test_solve_system_empty_rejected():
    r = solve_system([], ["x"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_solve_system_malicious_rejected():
    # Beyaz liste dışı çağrı -> reddedilir
    assert solve_system(["__import__('os') == 1"], ["x"]).status == "error"


# ------------------------------ determinizm -------------------------------- #
def test_calculus_determinism():
    # Aynı girdi -> aynı çıktı (verdict deterministik; ADR-0019 ile uyumlu)
    for _ in range(5):
        assert limit("sin(x)/x", "x", "0").result == "1"
        assert series("exp(x)", "x", "0", 5).result == "x**4/24 + x**3/6 + x**2/2 + x + 1"
        assert solve_system(["x + y == 10", "x - y == 2"], ["x", "y"]).result == [{"x": "6", "y": "4"}]
