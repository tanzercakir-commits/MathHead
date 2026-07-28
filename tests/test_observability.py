"""
Observability (ROADMAP K3) — structured metrics + resource limits + a perf fence.

The metrics collector aggregates every routed call's (task, status, elapsed_ms) without
changing any result; `resource_limits` exposes the active guardrails. A regression fence
asserts representative operations stay well within a generous time budget.
"""
import time

from mathhead.observability import metrics, reset_metrics
from mathhead.router import route


# ------------------------------ metrics ------------------------------------ #
def test_metrics_record_routed_calls():
    reset_metrics()
    route("simplify", {"expression": "x + x"})
    route("entailment", {"premises": ["p"], "conclusion": "p"})
    route("simplify", {"expression": "x + x"})
    snap = metrics()
    assert snap["total_calls"] >= 3
    assert snap["per_tool"]["simplify"]["calls"] >= 2
    assert "avg_ms" in snap["per_tool"]["simplify"] and "max_ms" in snap["per_tool"]["simplify"]
    assert snap["by_status"]  # some statuses recorded
    assert snap["recent"] and snap["recent"][-1]["task"] == "simplify"


def test_engine_metrics_tool():
    reset_metrics()
    route("consistency", {"statements": ["x > 0"]})
    r = route("engine_metrics", {})
    assert r.status == "ok" and r.reason_code == "METRICS"
    assert r.metrics["total_calls"] >= 1
    assert "elapsed_ms" in r.meta


def test_metrics_reset():
    route("simplify", {"expression": "1 + 1"})
    reset_metrics()
    assert metrics()["total_calls"] == 0


# --------------------------- resource limits ------------------------------- #
def test_resource_limits_tool():
    r = route("resource_limits", {})
    assert r.status == "ok" and r.reason_code == "LIMITS"
    for key in ("max_statements", "max_ast_depth", "default_timeout_ms", "default_seed",
                "prove_unsat_max_vars", "hpsolver_max_vars", "memoization_capacity"):
        assert key in r.limits
    assert r.limits["default_seed"] == 42          # the fixed determinism seed
    assert r.limits["max_statements"] >= 1


# ------------------------------ perf fence --------------------------------- #
def _under(budget_ms, task, payload):
    t0 = time.perf_counter()
    r = route(task, payload)
    elapsed = (time.perf_counter() - t0) * 1000
    assert elapsed < budget_ms, f"{task} took {elapsed:.0f}ms (budget {budget_ms}ms)"
    return r


def test_perf_regression_fence():
    # generous budgets — a regression guard, not a micro-benchmark
    _under(1500, "entailment", {"premises": ["p", "implies(p, q)"], "conclusion": "q"})
    _under(1500, "simplify", {"expression": "sin(x)**2 + cos(x)**2"})
    _under(1500, "prove_by_induction", {"claim": "(n*(n+1)) % 2 == 0", "var": "n", "start": 0})
    _under(3000, "n_queens", {"n": 8})
    _under(1500, "prove_unsat", {"clauses": [[1, 2], [-1, -2], [1, -2], [-1, 2]]})
    _under(1500, "check_bitvector", {"assumptions": [], "goal": "x ^ y ^ y == x", "width": 16})
    _under(2000, "solve_cnf", {"clauses": [[1, 2], [-1, 3], [-3]], "backend": "builtin"})
