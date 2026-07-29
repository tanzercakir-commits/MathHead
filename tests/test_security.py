"""
Security contract (ROADMAP L4).

These tests pin the properties SECURITY.md and docs/threat-model.md promise, so the
security posture is a checked invariant, not just prose:

  * T1 — no arbitrary code execution from an expression string (the compute allowlist
    walker; no sympify / eval / exec).
  * T2 — the guardrail size fence rejects oversized input cleanly.
  * T3 / §5 — the timeout model is asymmetric AND honest about it (Z3 is time-bounded;
    the SymPy path is not, and does not pretend to be).
"""
import pytest

from mathhead.router import route

# ------------- T1: no code execution via an expression string -------------- #
# Each of these, if the engine used sympify/eval, would be a code-exec or
# sandbox-escape vector. The allowlist AST walker must reject them as a clean error.
_CODE_EXEC = [
    "__import__('os').system('id')",
    "().__class__.__bases__",
    "x.__class__",
    "lambda: 1",
    "globals()",
    "open('/etc/passwd')",
    "eval('1+1')",
    "x if x else y",
]


@pytest.mark.parametrize("evil", _CODE_EXEC)
def test_expression_allowlist_rejects_code_execution(evil):
    r = route("simplify", {"expression": evil})
    assert r.status == "error", f"{evil!r} was not rejected"
    assert r.reason_code in {"PARSE_ERROR", "GUARDRAIL_VIOLATION", "COMPUTE_FAILED"}


def test_allowlist_still_accepts_legitimate_math():
    # the fence blocks attacks, not ordinary expressions
    assert route("simplify", {"expression": "sin(x)**2 + cos(x)**2"}).status == "ok"


# ------------- T2: the guardrail size fence (documented cap) ---------------- #
def test_guardrail_rejects_oversized_statement_count():
    r = route("entailment", {"premises": ["p"] * 5000, "conclusion": "p"})
    assert r.status == "error" and r.reason_code == "GUARDRAIL_VIOLATION"


def test_guardrail_rejects_overlong_expression():
    r = route("simplify", {"expression": "x+" * 3000 + "x"})
    assert r.status == "error"  # rejected up front, never processed


# ------------- T3 / §5: the honest, asymmetric timeout model ---------------- #
def test_z3_path_is_time_bounded_but_sympy_path_is_not():
    z3_meta = route("entailment", {"premises": ["p"], "conclusion": "p"}).meta
    sympy_meta = route("simplify", {"expression": "x + x"}).meta
    # Z3-backed results advertise the solver timeout they ran under...
    assert "timeout_ms" in z3_meta and z3_meta["timeout_ms"] > 0
    # ...the SymPy path carries NO wall-clock bound — exactly as threat-model.md §5 states.
    assert "timeout_ms" not in sympy_meta
    assert sympy_meta.get("engine") == "sympy"


def test_resource_limits_exposes_the_active_fences():
    lim = route("resource_limits", {}).limits
    for key in ("max_statements", "max_expression_chars", "max_ast_depth",
                "default_timeout_ms", "default_seed"):
        assert key in lim, f"resource_limits is missing the {key!r} fence"
    assert lim["default_timeout_ms"] > 0
