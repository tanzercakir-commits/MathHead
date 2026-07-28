"""
Natural language → formal (ROADMAP I2) — interpret: recognize-or-refuse + round-trip.

Key honesty property: DOES NOT GUESS. If recognized → formal task + NL
back-translation (restatement); if ambiguous → AMBIGUOUS; if unrecognized →
UNRECOGNIZED (no fabrication). Bilingual (TR + EN).
"""
from mathhead.core.nl import interpret


# ------------------------------ understood (EN) -------------------------- #
def test_derivative_en():
    r = interpret("derivative of x**3 with respect to x")
    assert r.status == "ok" and r.reason_code == "UNDERSTOOD"
    assert r.interpretation["task"] == "differentiate"
    assert r.interpretation["payload"] == {"expression": "x**3", "symbol": "x", "order": 1}


def test_limit_en():
    r = interpret("limit of sin(x)/x as x approaches 0")
    assert r.interpretation["task"] == "limit"
    assert r.interpretation["payload"]["point"] == "0"


def test_solve_en():
    r = interpret("solve x**2 == 4 for x")
    assert r.interpretation["task"] == "solve"


def test_is_prime_en():
    assert interpret("is 91 prime").interpretation["task"] == "is_prime"


# ------------------------------ understood (TR) -------------------------- #
# NOTE: Turkish input strings below exercise the bilingual TR feature — keep them.
def test_derivative_tr():
    r = interpret("x**3 ifadesinin x e göre türevi")
    assert r.status == "ok"
    assert r.interpretation["task"] == "differentiate"
    assert r.interpretation["payload"]["symbol"] == "x"


def test_integral_tr():
    assert interpret("2*x ifadesinin x e göre integrali").interpretation["task"] == "integrate"


def test_factorize_tr():
    r = interpret("360 sayısını çarpanlarına ayır")
    assert r.interpretation["task"] == "factorize"
    assert r.interpretation["payload"] == {"n": "360"}


def test_gcd_tr_postfix():
    r = interpret("48 ile 36 en büyük ortak bölen")
    assert r.interpretation["task"] == "gcd"
    assert r.interpretation["payload"] == {"a": "48", "b": "36"}


def test_is_prime_tr():
    assert interpret("97 asal mı").interpretation["task"] == "is_prime"


# --------------------------- round-trip (echo) ---------------------------- #
def test_restatement_present_and_descriptive():
    r = interpret("derivative of x**3 with respect to x")
    rs = r.interpretation["restatement"]
    assert "derivative" in rs and "x**3" in rs   # what was understood is restated
    assert "confirm" in r.explanation.lower()    # "confirm before trusting it"


def test_limit_infinity_word():
    # 'sonsuz' / 'infinity' → oo
    assert interpret("limit of 1/x as x approaches infinity").interpretation["payload"]["point"] == "oo"


# ------------------------------ HONESTY ----------------------------------- #
def test_unrecognized_is_refused_not_guessed():
    r = interpret("bu tamamen anlamsız bir cümle")
    assert r.status == "error" and r.reason_code == "UNRECOGNIZED"
    assert r.interpretation is None            # NO GUESSING


def test_bare_expression_refused():
    # A bare expression (no operation/question) is not recognized — not fabricated
    assert interpret("x squared plus one").status == "error"


def test_ambiguous_flagged_not_guessed():
    r = interpret("factorize 91 is 91 prime")
    assert r.status == "unknown" and r.reason_code == "AMBIGUOUS"
    tasks = {c["task"] for c in r.interpretation["candidates"]}
    assert tasks == {"factorize", "is_prime"}


def test_empty_input():
    assert interpret("").status == "error"


# ------------------------------ determinism ------------------------------- #
def test_nl_determinism():
    for _ in range(5):
        assert interpret("factorize 360").interpretation["payload"] == {"n": "360"}
        assert interpret("anlamsız").reason_code == "UNRECOGNIZED"
