"""
Cross-check (ROADMAP Track C3) — cross_check: Z3 ⋈ SymPy agreement.

Distinguishing feature: two INDEPENDENT engines. When they agree, high confidence;
when they conflict (e.g. domain trap), flag it. Best + worst + honest single-engine path.
"""
from mathhead.core.crosscheck import cross_check


def test_consensus_equal():
    r = cross_check("(x+1)**2", "x**2 + 2*x + 1")
    assert r.status == "valid"
    assert r.reason_code == "CONSENSUS_EQUAL"
    assert r.details["sympy"] == "equal" and r.details["z3"] == "equal"


def test_consensus_not_equal():
    r = cross_check("2*x", "3*x")
    assert r.status == "invalid"
    assert r.reason_code == "CONSENSUS_NOT_EQUAL"


def test_engines_disagree_on_domain_trap():
    # DISTINGUISHING: (x²-1)/(x-1) vs x+1 — SymPy 'equal', Z3 'not_equal' at x=1.
    # The disagreement exposes the domain trap (two independent witnesses).
    r = cross_check("(x**2 - 1)/(x - 1)", "x + 1")
    assert r.status == "unknown"
    assert r.reason_code == "ENGINES_DISAGREE"
    assert r.details["sympy"] == "equal"
    assert r.details["z3"] == "not_equal"


def test_single_engine_transcendental():
    # sin²+cos²=1 — Z3 doesn't support it (transcendental), only SymPy decides
    r = cross_check("sin(x)**2 + cos(x)**2", "1")
    assert r.status == "valid"
    assert r.reason_code == "SINGLE_ENGINE"
    assert r.details["z3"] == "unsupported"


def test_single_engine_root_branch():
    # sqrt(x²) = x is WRONG (|x| ≠ x, x<0). SymPy catches it; Z3 doesn't support it.
    r = cross_check("sqrt(x**2)", "x")
    assert r.status == "invalid"
    assert r.reason_code == "SINGLE_ENGINE"


def test_cross_check_rejects_equation():
    assert cross_check("x == 2", "x").status == "error"


def test_cross_check_determinism():
    # ADR-0020: .equals() randomness removed; sqrt(x²) must now be stable.
    for _ in range(10):
        assert cross_check("(x+1)**2", "x**2 + 2*x + 1").reason_code == "CONSENSUS_EQUAL"
        assert cross_check("(x**2 - 1)/(x - 1)", "x + 1").reason_code == "ENGINES_DISAGREE"
        assert cross_check("sqrt(x**2)", "x").status == "invalid"   # deterministic
