"""
v1.1 — quantifiers (∀/∃) + Real numbers.

Scope: universal/existential truth, Int vs Real distinction, prevention of
variable capture and SOUNDNESS against undecidability (the engine never produces
a wrong answer; if it can't decide it says 'unknown').
"""
from mathhead.core import check_consistency, check_entailment, find_model


# ------------------------- Quantifiers --------------------------- #
def test_universal_tautology_is_valid():
    # ∀x. (x > 2 -> x > 1)  always true
    r = check_entailment([], "forall(x, implies(x > 2, x > 1))")
    assert r.status == "valid"


def test_false_universal_is_unsat():
    # ∀x∈ℤ. x > 0  false (x = 0)
    r = check_consistency(["forall(x, x > 0)"])
    assert r.status == "unsat"


def test_existential_witness_kind_is_domain_sensitive():
    # ∃x. 1 < x < 2  -> NONE in Int (unsat)
    assert check_consistency(["exists(x, 1 < x and x < 2)"]).status == "unsat"


# ------------------------------- Real ------------------------------------- #
def test_exists_real_between_bounds_is_sat():
    # decimal constant -> Real domain -> a solution like 1.5 exists
    r = check_consistency(["exists(x, 1.0 < x and x < 2.0)"])
    assert r.status == "sat"


def test_real_model_is_between_bounds():
    r = find_model(["x > 1.0", "x < 2.0"])
    assert r.status == "sat"
    assert isinstance(r.witness["x"], float)
    assert 1.0 < r.witness["x"] < 2.0


# ----------------------- Guardrail / scope / soundness ------------------- #
def test_nonlinear_inside_quantifier_is_rejected():
    r = check_consistency(["forall(x, x*x > 0)"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_no_variable_capture_between_free_and_bound():
    # (x > 0)  ∧  (∀x. x > 5): free x must not mix with bound x -> unsat
    r = check_consistency(["x > 0 and forall(x, x > 5)"])
    assert r.status == "unsat"


def test_soundness_no_fabrication_on_hard_quantifier():
    # ∀x ∃y. y > x  (Int) is TRUE. The engine must say either 'sat' (correct) or
    # 'unknown' (honest); must NEVER say 'unsat' (wrong). Soundness guarantee.
    r = check_consistency(["forall(x, exists(y, y > x))"], timeout_ms=1500)
    assert r.status in ("sat", "unknown")
    if r.status == "unknown":
        assert r.is_conclusive() is False
