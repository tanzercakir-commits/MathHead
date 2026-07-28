"""
Mathematical induction (ROADMAP H1) — prove_by_induction.

Z3 cannot do induction natively; we add it as a sound meta-rule (base + step).
Best-case (real theorems proved), honesty (base-fail → invalid, step-fail/solver-
unknown → unknown, NEVER a fake proof), grammar rejection, and determinism.
"""
from mathhead.core.induction import prove_by_induction
from mathhead.router import route


# ------------------------------ proved -------------------------------------- #
def test_parity_of_consecutive_product():
    # n(n+1) is always even
    r = prove_by_induction("(n*(n+1)) % 2 == 0", "n", 0)
    assert r.status == "valid"
    assert r.reason_code == "PROVED_BY_INDUCTION"
    assert r.base_case == {"claim": "(n*(n+1)) % 2 == 0", "at": 0, "holds": True}
    assert r.inductive_step["holds"] is True
    assert [s["rule"] for s in r.proof_steps] == ["base case", "inductive step", "induction principle"]
    assert r.proof_steps[-1]["refs"] == [1, 2]


def test_divisibility_by_three_cubic():
    # n^3 - n is divisible by 3 (a classic induction exercise)
    r = prove_by_induction("(n**3 - n) % 3 == 0", "n", 0)
    assert r.status == "valid"
    assert r.reason_code == "PROVED_BY_INDUCTION"


def test_inequality_square_ge_self():
    r = prove_by_induction("n**2 >= n", "n", 0)
    assert r.status == "valid"


def test_polynomial_identity():
    r = prove_by_induction("(n+1)**2 == n**2 + 2*n + 1", "n", 0)
    assert r.status == "valid"


def test_start_offset():
    # n^2 >= 2n holds for n >= 2 (fails at n=1) — start=2 makes it provable
    r = prove_by_induction("n**2 >= 2*n", "n", 2)
    assert r.status == "valid"
    assert r.base_case["at"] == 2


# ------------------------------ honest walls -------------------------------- #
def test_base_case_fails_is_invalid():
    # ∀n≥0. n>=5 is false (n=0 refutes it) → the BASE fails
    r = prove_by_induction("n >= 5", "n", 0)
    assert r.status == "invalid"
    assert r.reason_code == "BASE_FAILED"
    assert r.base_case["holds"] is False


def test_step_fails_is_unknown_not_invalid():
    # base P(0): 0<3 holds; step fails at k=2 (2<3 but 3<3 false). Induction is
    # inconclusive → unknown (NOT invalid — we never overclaim).
    r = prove_by_induction("n < 3", "n", 0)
    assert r.status == "unknown"
    assert r.reason_code == "STEP_FAILED"
    assert r.inductive_step["holds"] is False
    assert r.inductive_step["counterexample"] == {"n": 2}


def test_hard_nonlinear_step_is_unknown():
    # n(n+1)(n+2) divisible by 6 is TRUE, but Z3 cannot decide the nonlinear step →
    # honest unknown (a wall), never a fabricated proof.
    r = prove_by_induction("(n*(n+1)*(n+2)) % 6 == 0", "n", 0)
    assert r.status == "unknown"
    assert r.reason_code == "SOLVER_UNKNOWN"


# ------------------------------ grammar / guardrails ------------------------ #
def test_extra_symbol_rejected():
    r = prove_by_induction("n + m >= 0", "n", 0)
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_non_boolean_claim_rejected():
    r = prove_by_induction("n + 1", "n", 0)
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_float_constant_rejected():
    r = prove_by_induction("n >= 1.5", "n", 0)
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_bad_var_rejected():
    r = prove_by_induction("n >= 0", "1n", 0)
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


# ------------------------------ routing / determinism ----------------------- #
def test_router_wiring():
    r = route("prove_by_induction", {"claim": "n**2 >= n", "var": "n", "start": 0})
    assert r.status == "valid"


def test_determinism():
    for _ in range(5):
        a = prove_by_induction("(n*(n+1)) % 2 == 0", "n", 0)
        b = prove_by_induction("(n*(n+1)) % 2 == 0", "n", 0)
        assert a.status == b.status == "valid"
        assert a.proof_steps == b.proof_steps
