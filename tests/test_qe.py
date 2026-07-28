"""
Quantifier elimination (ROADMAP H3) — eliminate_quantifiers.

Z3 `qe` over Presburger arithmetic turns a quantified linear formula into an
equivalent quantifier-free one, and doubles as a decision procedure (collapse to
True/False). Best-case (real QE results), honesty (residual quantifier reported,
grammar rejection), determinism.
"""
from mathhead.core.qe import eliminate_quantifiers as qe
from mathhead.router import route


def test_qe_interval_nonempty():
    # ∃x. a ≤ x ≤ b  ⟺  a ≤ b  (a quantifier-free condition, not a constant)
    r = qe("exists(x, (a <= x) and (x <= b))")
    assert r.status == "ok" and r.reason_code == "QE_DONE"
    assert r.result is not None and r.equivalent_to is None


def test_qe_empty_integer_interval_is_false():
    # ∃x∈ℤ. 0 < x < 1 is FALSE (no integer strictly between)
    r = qe("exists(x, (x > 0) and (x < 1))")
    assert r.status == "ok" and r.equivalent_to == "false"


def test_qe_evenness_becomes_divisibility():
    # ∃y. x = 2y  ⟺  x ≡ 0 (mod 2)
    r = qe("exists(y, x == 2*y)")
    assert r.status == "ok"
    assert "%" in r.result  # a modular (divisibility) condition


def test_qe_valid_statement_is_true():
    r = qe("forall(x, implies(x > 5, x > 3))")
    assert r.status == "ok" and r.equivalent_to == "true"


def test_qe_identity_is_true():
    r = qe("forall(x, x + 0 == x)")
    assert r.equivalent_to == "true"


def test_qe_nonlinear_rejected():
    # the kernel grammar forbids variable*variable (nonlinear) → clean PARSE_ERROR
    assert qe("x*y > 0").status == "error"


def test_qe_syntax_error_rejected():
    r = qe("exists(x, x = 1)")
    assert r.status == "error" and r.reason_code == "PARSE_ERROR"


def test_qe_router_wiring():
    r = route("eliminate_quantifiers", {"formula": "exists(y, x == 2*y)"})
    assert r.status == "ok"


def test_qe_determinism():
    outs = [qe("exists(x, (a <= x) and (x <= b))").result for _ in range(5)]
    assert len(set(outs)) == 1
