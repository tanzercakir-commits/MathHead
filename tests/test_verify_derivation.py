"""
Full derivation proof check (ROADMAP I3) — verify_derivation.

Deeper than verify_steps: it REPLAYS each transition's cited operation and checks
that the operation actually produces the stated next line (the JUSTIFICATION audit),
for equations as well as expressions.

Best-case (justified derivations) + worst-case (unjustified step, bad operation,
guardrails) + honesty (domain caveat, undecidable, no fabrication) + determinism.
"""
from mathhead.core.verify import verify_derivation


# ------------------------------ justified -------------------------------- #
def test_equation_solving_is_justified():
    # 2x+3=7 --subtract 3--> 2x=4 --divide 2--> x=2
    r = verify_derivation(
        ["2*x + 3 == 7", "2*x == 4", "x == 2"],
        [{"op": "subtract", "value": "3"}, {"op": "divide", "value": "2"}],
    )
    assert r.status == "valid"
    assert r.reason_code == "DERIVATION_VALID"


def test_expression_expand_is_justified():
    r = verify_derivation(["(x + 1)**2", "x**2 + 2*x + 1"], [{"op": "expand"}])
    assert r.status == "valid"


def test_factor_is_justified():
    r = verify_derivation(["x**2 - 1", "(x - 1)*(x + 1)"], [{"op": "factor"}])
    assert r.status == "valid"


def test_add_then_simplify_is_justified():
    # x - 5 = 0 --add 5--> x = 5
    r = verify_derivation(["x - 5 == 0", "x == 5"], [{"op": "add", "value": "5"}])
    assert r.status == "valid"


def test_multiply_constant_is_justified():
    # x/2 = 3 --multiply 2--> x = 6
    r = verify_derivation(["x/2 == 3", "x == 6"], [{"op": "multiply", "value": "2"}])
    assert r.status == "valid"


# --------------------------- unjustified (honest) ------------------------- #
def test_wrong_arithmetic_is_unjustified():
    # claims 'subtract 3' but wrote 2x=5 (should be 2x=4)
    r = verify_derivation(["2*x + 3 == 7", "2*x == 5"], [{"op": "subtract", "value": "3"}])
    assert r.status == "invalid"
    assert r.reason_code == "STEP_UNJUSTIFIED"
    assert r.details["first_bad_step"] == 1
    assert "2*x == 4" in r.details["expected"]


def test_wrong_expand_forgets_cross_term():
    # (x+1)**2 --expand--> x**2 + 1  (missing 2x)
    r = verify_derivation(["(x + 1)**2", "x**2 + 1"], [{"op": "expand"}])
    assert r.status == "invalid"
    assert r.reason_code == "STEP_UNJUSTIFIED"
    assert r.details["counterexample"] is not None


def test_first_bad_step_is_located_in_the_middle():
    # step1->2 ok (subtract 3), step2->3 WRONG (claims divide 2 but 2x=4 -> x=3)
    r = verify_derivation(
        ["2*x + 3 == 7", "2*x == 4", "x == 3"],
        [{"op": "subtract", "value": "3"}, {"op": "divide", "value": "2"}],
    )
    assert r.status == "invalid"
    assert r.details["first_bad_step"] == 2


def test_type_mismatch_expression_vs_equation():
    # operation would keep it an expression, but the claimed next line is an equation
    r = verify_derivation(["x + 1", "x == 1"], [{"op": "add", "value": "0"}])
    assert r.status == "invalid"


# ------------------------------ honesty walls ----------------------------- #
def test_multiply_by_variable_flags_domain_caveat():
    # x = 2 --multiply x--> x**2 = 2x : mechanically valid, but solution set may change
    r = verify_derivation(["x == 2", "x**2 == 2*x"], [{"op": "multiply", "value": "x"}])
    assert r.status == "valid"
    assert r.details.get("domain_caveats")
    assert any("solution set" in c for c in r.details["domain_caveats"])


# ------------------------------ guardrails -------------------------------- #
def test_unknown_operation_rejected():
    r = verify_derivation(["x == 2", "x == 2"], [{"op": "teleport"}])
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_divide_by_zero_rejected():
    r = verify_derivation(["x == 2", "x == 2"], [{"op": "divide", "value": "0"}])
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_missing_value_rejected():
    r = verify_derivation(["x == 2", "x == 2"], [{"op": "subtract"}])
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_operations_length_must_match():
    # 3 steps need exactly 2 operations
    r = verify_derivation(["x == 2", "x == 4", "x == 8"], [{"op": "add", "value": "2"}])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_too_few_steps_rejected():
    assert verify_derivation(["x == 2"], []).status == "error"


def test_malicious_input_rejected():
    r = verify_derivation(["__import__('os')", "x"], [{"op": "simplify"}])
    assert r.status == "error"


# ------------------------------ determinism ------------------------------- #
def test_derivation_determinism():
    steps = ["2*x + 3 == 7", "2*x == 4", "x == 2"]
    ops = [{"op": "subtract", "value": "3"}, {"op": "divide", "value": "2"}]
    for _ in range(5):
        r = verify_derivation(steps, ops)
        assert r.status == "valid" and r.reason_code == "DERIVATION_VALID"
