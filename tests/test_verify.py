"""
Verification layer (ROADMAP Track C1 — AI reasoning auditor):
verify_equality / verify_solution / verify_steps.

The differentiating features are tested here: (1) catching the DOMAIN trap, (2)
checking solution COMPLETENESS, (3) finding the first error in a step chain. Also honest
'unknown' paths and security.
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
    # DIFFERENTIATOR: (x²-1)/(x-1) and x+1 are symbolically equal BUT undefined at x=1.
    # We catch the error that a naive equality check MISSES.
    r = verify_equality("(x**2 - 1)/(x - 1)", "x + 1")
    assert r.status == "valid"
    assert r.reason_code == "EQUAL_ON_COMMON_DOMAIN"
    assert "x=1" in r.details["domain_caveat"]


def test_equality_rejects_equation_input():
    # left/right must be expressions, not an equation
    assert verify_equality("x == 2", "x").status == "error"


def test_equality_malicious_rejected():
    assert verify_equality("__import__('os')", "1").status == "error"


# ----------------------------- verify_solution ---------------------------- #
def test_solution_correct_and_complete():
    r = verify_solution("x**2 == 4", "x", ["2", "-2"])
    assert r.status == "valid"
    assert r.reason_code == "SOLUTION_VERIFIED"


def test_solution_incomplete_catches_missing():
    # DIFFERENTIATOR: {2} is incomplete — (-2) is missing. The most common AI error.
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
    # Value correct (0 + sin 0 = 0) but solve can't give all solutions -> honest unknown
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
    # DIFFERENTIATOR: classic (x+1)² = x²+1 error -> first broken transition
    r = verify_steps(["(x+1)**2", "x**2 + 1"])
    assert r.status == "invalid"
    assert r.reason_code == "STEP_INVALID"
    assert r.details["first_bad_step"] == 1
    assert r.details["counterexample"] is not None


def test_steps_pinpoints_middle_error():
    # First transition correct, second transition wrong
    r = verify_steps(["2*x + 2", "2*(x + 1)", "2*x + 3"])
    assert r.status == "invalid"
    assert r.details["first_bad_step"] == 2


def test_steps_needs_two():
    assert verify_steps(["x+1"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_verify_determinism():
    for _ in range(5):
        assert verify_equality("sin(x)**2 + cos(x)**2", "1").status == "valid"
        assert verify_solution("x**2 == 4", "x", ["2"]).reason_code == "SOLUTION_INCOMPLETE"
        assert verify_steps(["(x+1)**2", "x**2 + 1"]).details["first_bad_step"] == 1
