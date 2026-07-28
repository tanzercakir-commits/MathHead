"""
v2 — SymPy hesap katmanı: simplify / solve / differentiate / integrate.
Ayrıca beyaz-liste güvenliği (kötücül/bilinmeyen girdi reddi).
"""
from mathhead.compute import differentiate, integrate, simplify, solve


# ------------------------------ simplify ---------------------------------- #
def test_simplify_trig_identity():
    r = simplify("sin(x)**2 + cos(x)**2")
    assert r.status == "ok"
    assert r.result == "1"


def test_simplify_rational():
    assert simplify("(x**2 - 1)/(x - 1)").result == "x + 1"


# ------------------------------- solve ------------------------------------ #
def test_solve_quadratic():
    r = solve("x**2 == 4", "x")
    assert r.status == "ok"
    assert set(r.result) == {"-2", "2"}


def test_solve_linear():
    assert solve("2*x + 3 == 7", "x").result == ["2"]


def test_solve_expression_assumed_zero():
    assert set(solve("x**2 - 4", "x").result) == {"-2", "2"}


# --------------------------- differentiate -------------------------------- #
def test_first_derivative():
    assert differentiate("x**3 + 2*x", "x").result == "3*x**2 + 2"


def test_second_derivative():
    assert differentiate("x**3", "x", 2).result == "6*x"


# ------------------------------ integrate --------------------------------- #
def test_integrate_polynomial():
    assert integrate("2*x", "x").result == "x**2"


def test_integrate_trig():
    assert integrate("cos(x)", "x").result == "sin(x)"


# ----------------------- guardrail / güvenlik ----------------------------- #
def test_unknown_function_rejected():
    r = simplify("foo(x)")
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_malicious_import_rejected():
    # Beyaz liste dışı çağrı -> reddedilir (ör. __import__)
    assert simplify("__import__('os')").status == "error"


def test_syntax_error_rejected():
    r = simplify("2 * * x")
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"
