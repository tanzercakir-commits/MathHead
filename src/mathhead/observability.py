"""
mathhead.observability — Structured metrics + resource limits (ROADMAP K3).

Every result already carries `meta` (engine, elapsed_ms, seed, timeout_ms — PRINCIPLES 9,
"traceability is mandatory"). This module aggregates that traceability into a live,
queryable picture WITHOUT changing any result:

  * `observe` — a decorator on `router.route` that records each call's (task, status,
    elapsed_ms) into an in-memory aggregate (counters + timing sums + a bounded ring of
    recent calls). Transparent: it returns the result unchanged.
  * `engine_metrics` (via `metrics_result`) — a snapshot: total calls, status
    distribution, per-tool call counts / average & max latency, and the recent-call log.
  * `resource_limits` — the ACTIVE fences (statement/expression/depth caps, default
    timeout & seed, solver variable bounds). Makes the guardrails introspectable.

Determinism is untouched: metrics are observational side state; results are unchanged.
`reset_metrics()` gives a clean slate (test isolation / a fresh session).
"""
from __future__ import annotations

import functools
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Callable

_RECENT_MAX = 50
_calls: Counter = Counter()                 # task -> count
_statuses: Counter = Counter()              # status -> count
_timing: dict[str, list] = {}               # task -> [count, total_ms, max_ms]
_recent: deque = deque(maxlen=_RECENT_MAX)  # recent {task, status, elapsed_ms}
_total = {"calls": 0}


def record(task: str, status: str, elapsed_ms: float) -> None:
    """Record one engine call into the aggregate metrics."""
    _calls[task] += 1
    _statuses[status] += 1
    t = _timing.setdefault(task, [0, 0.0, 0.0])
    t[0] += 1
    t[1] += elapsed_ms
    t[2] = max(t[2], elapsed_ms)
    _recent.append({"task": task, "status": status, "elapsed_ms": round(elapsed_ms, 3)})
    _total["calls"] += 1


def observe(fn: Callable) -> Callable:
    """Decorator for `route`: time the call and record (task, status, elapsed_ms)."""

    @functools.wraps(fn)
    def wrapper(task, payload):
        t0 = time.perf_counter()
        result = fn(task, payload)
        elapsed = (time.perf_counter() - t0) * 1000
        record(task, str(getattr(result, "status", "unknown")), elapsed)
        return result

    return wrapper


def metrics() -> dict[str, Any]:
    """A snapshot of the aggregated metrics (plain dict)."""
    per_tool = {
        task: {"calls": t[0], "avg_ms": round(t[1] / t[0], 3) if t[0] else 0.0, "max_ms": round(t[2], 3)}
        for task, t in sorted(_timing.items())
    }
    return {
        "total_calls": _total["calls"],
        "distinct_tools": len(_calls),
        "by_status": dict(sorted(_statuses.items())),
        "top_tools": [t for t, _ in _calls.most_common(10)],
        "per_tool": per_tool,
        "recent": list(_recent),
    }


def reset_metrics() -> None:
    """Clear all recorded metrics (test isolation / fresh session)."""
    _calls.clear()
    _statuses.clear()
    _timing.clear()
    _recent.clear()
    _total["calls"] = 0


def limits() -> dict[str, Any]:
    """The engine's ACTIVE resource fences (introspection of the guardrails)."""
    from mathhead import drat, hpsolver
    from mathhead.core import modal
    from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS
    from mathhead.guardrails import MAX_AST_DEPTH, MAX_EXPRESSION_CHARS, MAX_STATEMENTS

    return {
        "max_statements": MAX_STATEMENTS,
        "max_expression_chars": MAX_EXPRESSION_CHARS,
        "max_ast_depth": MAX_AST_DEPTH,
        "default_timeout_ms": DEFAULT_TIMEOUT_MS,
        "default_seed": DEFAULT_SEED,
        "modal_max_worlds": modal._MAX_WORLDS,
        "prove_unsat_max_vars": drat._MAX_VARS_PROVE,
        "prove_unsat_max_nodes": drat._MAX_NODES,
        "hpsolver_max_vars": hpsolver._MAX_VARS,
        "hpsolver_default_conflicts": hpsolver._DEFAULT_CONFLICTS,
        "memoization_capacity": _memo_capacity(),
    }


def _memo_capacity() -> int:
    from mathhead.cache import _CAPACITY
    return _CAPACITY


# --------------------------------------------------------------------------- #
# Result contracts
# --------------------------------------------------------------------------- #
@dataclass
class MetricsResult:
    status: str
    reason_code: str
    explanation: str
    metrics: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class LimitsResult:
    status: str
    reason_code: str
    explanation: str
    limits: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def metrics_result() -> MetricsResult:
    t0 = time.perf_counter()
    m = metrics()
    return MetricsResult("ok", "METRICS",
                         f"{m['total_calls']} engine calls across {m['distinct_tools']} tools; "
                         f"status distribution {m['by_status']}.",
                         m, {"engine": "observability", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)})


def limits_result() -> LimitsResult:
    t0 = time.perf_counter()
    return LimitsResult("ok", "LIMITS", "The engine's active resource fences (hard guardrails).",
                        limits(), {"engine": "observability",
                                   "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)})
