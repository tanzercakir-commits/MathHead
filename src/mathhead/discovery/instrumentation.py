"""
mathhead.discovery.instrumentation — opt-in metrics for the discovery surface (roadmap AG5,
in-container slice).

SCOPE, stated honestly up front: an IN-CONTAINER metrics slice. Counters live in this process,
snapshots are plain JSON, and NOTHING leaves the machine — no external telemetry, by privacy
design. "Cost tracking" here means what can be measured honestly in-process: wall-clock time,
call counts, verdict distribution, and solver invocations; cloud billing is out of scope and
not claimed. `PRIVACY_NOTE` rides every snapshot so the boundary travels with the data.

Rules (the same discipline as `mathhead.observability`, extended to the discovery product
surface — check / bracket / hunt / report):
  * OFF by default — when disabled, `observe` calls straight through and records nothing;
  * results are NEVER changed — metrics are observational side state only. `observe` returns
    the wrapped function's result untouched, enabled or not;
  * ISOLATION — metrics live on a `Collector` instance. The module-level functions delegate to
    one shared default collector for library users; anything that needs its own scope (the CLI's
    `--stats` flag, a test) creates a private `Collector()` and cannot clobber anyone else's
    counters;
  * deterministic snapshot SHAPE — keys are sorted; only the elapsed-ms numbers vary run-to-run
    (they are wall-clock measurements, honestly non-deterministic).
"""
from __future__ import annotations

import json
import time
from collections import Counter

PRIVACY_NOTE = ("in-container metrics slice: counters stay in this process and are emitted only "
                "as local JSON on request — no external telemetry (privacy); cost = wall-clock + "
                "call counts + solver invocations, cloud billing out of scope")


class Collector:
    """An isolated metrics collector: its own enable switch, its own counters. Two collectors
    never share state — resetting one cannot touch another."""

    def __init__(self, enabled: bool = False):
        self._on = bool(enabled)
        self._ops: dict = {}     # op -> {"calls", "outcomes", "total_ms", "max_ms", "solver_calls"}

    def enable(self) -> None:
        self._on = True

    def disable(self) -> None:
        self._on = False

    def enabled(self) -> bool:
        return self._on

    def reset(self) -> None:
        """Clear this collector's metrics (test isolation / a fresh session). Enablement as-is."""
        self._ops.clear()

    def record(self, op: str, outcome: str, elapsed_ms: float, solver_calls: int = 0) -> None:
        """Record one discovery-surface call. No-op unless this collector is enabled."""
        if not self._on:
            return
        slot = self._ops.setdefault(op, {"calls": 0, "outcomes": Counter(), "total_ms": 0.0,
                                         "max_ms": 0.0, "solver_calls": 0})
        slot["calls"] += 1
        slot["outcomes"][str(outcome)] += 1
        slot["total_ms"] += elapsed_ms
        slot["max_ms"] = max(slot["max_ms"], elapsed_ms)
        slot["solver_calls"] += int(solver_calls)

    def observe(self, op: str, fn, *args, _outcome=None, _solver_calls=None, **kwargs):
        """Run `fn(*args, **kwargs)` and (only if enabled) record its duration + outcome +
        solver-call count under `op`. The result is returned UNTOUCHED either way —
        instrumentation can never change an answer.

        `_outcome(result)` maps the result to a label (default "ok"); `_solver_calls(result)`
        maps it to the number of SAT/SMT solver invocations the call is known to have made
        (default 0)."""
        if not self._on:
            return fn(*args, **kwargs)
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - t0) * 1000
        self.record(op, _outcome(result) if _outcome else "ok", elapsed,
                    _solver_calls(result) if _solver_calls else 0)
        return result

    def snapshot(self) -> dict:
        """The collected metrics as a plain, JSON-ready dict (sorted keys; deterministic shape)."""
        ops = {}
        for op in sorted(self._ops):
            s = self._ops[op]
            ops[op] = {"calls": s["calls"],
                       "outcomes": dict(sorted(s["outcomes"].items())),
                       "total_ms": round(s["total_ms"], 3),
                       "max_ms": round(s["max_ms"], 3),
                       "solver_calls": s["solver_calls"]}
        return {"enabled": self._on,
                "note": PRIVACY_NOTE,
                "total_calls": sum(s["calls"] for s in self._ops.values()),
                "ops": ops}

    def dump_json(self, path: str | None = None) -> str:
        """The snapshot as a JSON string; optionally also written to `path` (a local file — the
        only place metrics ever go)."""
        text = json.dumps(self.snapshot(), indent=2, sort_keys=True)
        if path is not None:
            from pathlib import Path
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text


# The shared default collector for LIBRARY users. The module-level functions below delegate to
# it — the CLI deliberately does NOT use it (a `--stats` run builds a private Collector), so a
# CLI invocation can never reset or pollute a library user's counters.
_DEFAULT = Collector()


def enable() -> None:
    _DEFAULT.enable()


def disable() -> None:
    _DEFAULT.disable()


def enabled() -> bool:
    return _DEFAULT.enabled()


def reset() -> None:
    _DEFAULT.reset()


def record(op: str, outcome: str, elapsed_ms: float, solver_calls: int = 0) -> None:
    _DEFAULT.record(op, outcome, elapsed_ms, solver_calls)


def observe(op: str, fn, *args, _outcome=None, _solver_calls=None, **kwargs):
    return _DEFAULT.observe(op, fn, *args, _outcome=_outcome, _solver_calls=_solver_calls,
                            **kwargs)


def snapshot() -> dict:
    return _DEFAULT.snapshot()


def dump_json(path: str | None = None) -> str:
    return _DEFAULT.dump_json(path)
