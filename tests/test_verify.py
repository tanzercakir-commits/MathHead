"""
Doğrulama katmanı (ROADMAP Track C1 — AI muhakeme denetçisi):
verify_equality / verify_solution / verify_steps.

Öne geçiren özellikler burada test edilir: (1) DOMAIN tuzağını yakalama, (2)
çözüm TAMLIĞINI denetleme, (3) adım zincirinde ilk hatayı bulma. Ayrıca dürüst
'unknown' yolları ve güvenlik.
"""
from mathhead.core.verify import verify_equality, verify_solution, verify_steps


# ----------------------------- verify_equality ---------------------------- #
def test_equality_identity():
    r = verify_equality("sin(x)**2 + cos(x)**2", "1")
    assert r.status == "valid"
    assert r.reason_code == "EQUAL"


def test_equality_not_equal_gives_counterexample():
    r = verify_equality("2*x", "3*x")
    assert r.status == "invalid"
    assert r.reason_code == "NOT_EQUAL"
    assert r.details["counterexample"] is not None


def test_equality_domain_trap():
    # ÖNE GEÇİREN: (x²-1)/(x-1) ile x+1 sembolik denk AMA x=1'de tanımsız.
    # Naif eşitlik kontrolünün KAÇIRDIĞI hatayı yakalarız.
    r = verify_equality("(x**2 - 1)/(x - 1)", "x + 1")
    assert r.status == "valid"
    assert r.reason_code == "EQUAL_ON_COMMON_DOMAIN"
    assert "x=1" in r.details["domain_caveat"]


def test_equality_rejects_equation_input():
    # left/right ifade olmalı, denklem değil
    assert verify_equality("x == 2", "x").status == "error"


def test_equality_malicious_rejected():
    assert verify_equality("__import__('os')", "1").status == "error"


# ----------------------------- verify_solution ---------------------------- #
def test_solution_correct_and_complete():
    r = verify_solution("x**2 == 4", "x", ["2", "-2"])
    assert r.status == "valid"
    assert r.reason_code == "SOLUTION_VERIFIED"


def test_solution_incomplete_catches_missing():
    # ÖNE GEÇİREN: {2} eksik — (-2) kaçıyor. AI'ın en sık hatası.
    r = verify_solution("x**2 == 4", "x", ["2"])
    assert r.status == "invalid"
    assert r.reason_code == "SOLUTION_INCOMPLETE"
    assert "-2" in r.details["missing"]


def test_solution_incorrect_catches_wrong_value():
    r = verify_solution("x**2 == 4", "x", ["2", "3"])
    assert r.status == "invalid"
    assert r.reason_code == "SOLUTION_INCORRECT"
    assert "3" in r.details["wrong_values"]


def test_solution_completeness_unknown_is_honest():
    # Değer doğru (0 + sin 0 = 0) ama solve tüm çözümleri veremez -> dürüst unknown
    r = verify_solution("x + sin(x) == 0", "x", ["0"])
    assert r.status == "unknown"
    assert r.reason_code == "COMPLETENESS_UNKNOWN"


def test_solution_empty_claim_rejected():
    assert verify_solution("x**2 == 4", "x", []).status == "error"


# ------------------------------ verify_steps ------------------------------ #
def test_steps_all_valid():
    r = verify_steps(["(x+1)**2", "x**2 + 2*x + 1", "x*(x + 2) + 1"])
    assert r.status == "valid"
    assert r.reason_code == "STEPS_VALID"


def test_steps_finds_first_error():
    # ÖNE GEÇİREN: klasik (x+1)² = x²+1 hatası -> ilk kırılan geçiş
    r = verify_steps(["(x+1)**2", "x**2 + 1"])
    assert r.status == "invalid"
    assert r.reason_code == "STEP_INVALID"
    assert r.details["first_bad_step"] == 1
    assert r.details["counterexample"] is not None


def test_steps_pinpoints_middle_error():
    # İlk geçiş doğru, ikinci geçiş hatalı
    r = verify_steps(["2*x + 2", "2*(x + 1)", "2*x + 3"])
    assert r.status == "invalid"
    assert r.details["first_bad_step"] == 2


def test_steps_needs_two():
    assert verify_steps(["x+1"]).status == "error"


# ------------------------------ determinizm ------------------------------- #
def test_verify_determinism():
    for _ in range(5):
        assert verify_equality("sin(x)**2 + cos(x)**2", "1").status == "valid"
        assert verify_solution("x**2 == 4", "x", ["2"]).reason_code == "SOLUTION_INCOMPLETE"
        assert verify_steps(["(x+1)**2", "x**2 + 1"]).details["first_bad_step"] == 1
