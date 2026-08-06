"""
mathhead.discovery.parallel_search — parallel sweep + disk cache (roadmap AG1, in-container slice).

SCOPE, stated honestly up front: this is the IN-CONTAINER slice of AG1 — multiprocessing on ONE
machine (the worker count is a parameter, and the RESULT is not allowed to depend on it) plus a
hash-keyed local disk cache with explicit invalidation. Multi-machine distribution (job queues,
remote workers, shared caches) is OUT of scope and not claimed. `SCOPE_NOTE` rides every result.

What makes the parallelism honest:
  * determinism by construction — work splits by graph ORDER (or Ramsey instance n), every worker
    task is a pure function of its picklable arguments, and the merge is a deterministic fold
    ordered by n. `sweep_graph_bound(..., workers=k)` returns the IDENTICAL SweepResult for every
    k >= 1 (pinned by test), and the reported witness is the smallest-order violation — the same
    counterexample-first discipline as the serial scan, recovered by the merge.
  * the cache degrades, it never guesses — entries are keyed by a content hash of
    (schema version, task); an entry that is corrupted, foreign, or from another schema version
    is a MISS and gets recomputed, never trusted. `invalidate()` clears the store explicitly.
    (The guarantee is against corruption/staleness; the correctness of a stored VALUE comes
    from the deterministic worker that produced it — see the DiskCache docstring.)
  * refusal, never guessing — an unparseable statement or an unknown invariant raises ValueError
    up front, before any worker is launched.
"""
from __future__ import annotations

import hashlib
import json
import multiprocessing
from dataclasses import dataclass, field
from pathlib import Path

SCOPE_NOTE = ("in-container slice: multiprocessing on one machine + a hash-keyed local disk "
              "cache; multi-machine distribution (job queues, remote workers, shared caches) "
              "is OUT of scope and not claimed")

_SCHEMA = "parallel-search-v1"      # bump to invalidate every existing cache entry at once

_REL = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b, "==": lambda a, b: a == b}


class DiskCache:
    """A hash-keyed local JSON cache with explicit invalidation. Every entry stores its schema
    version AND its full key; a mismatch (stale schema, hash collision, corruption, foreign
    file) is treated as a MISS and recomputed. Scope of the guarantee, honestly: it protects
    against CORRUPTION and STALENESS by degrading to recomputation — it cannot validate that a
    well-formed stored value was CORRECT when `put()` stored it; that correctness comes from
    the deterministic worker that produced the value, not from the cache."""

    def __init__(self, directory, schema: str = _SCHEMA):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.schema = schema
        self.hits = 0
        self.misses = 0

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(f"{self.schema}|{key}".encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    def get(self, key: str):
        """The stored value for `key`, or None (counted as a miss). Corrupted / foreign /
        stale-schema entries are misses by construction — never trusted."""
        try:
            payload = json.loads(self._path(key).read_text(encoding="utf-8"))
            if payload.get("schema") != self.schema or payload.get("key") != key:
                raise ValueError("stale or foreign cache entry")
            value = payload["value"]
        except (OSError, ValueError, KeyError):
            self.misses += 1
            return None
        self.hits += 1
        return value

    def put(self, key: str, value) -> None:
        self._path(key).write_text(
            json.dumps({"schema": self.schema, "key": key, "value": value}, sort_keys=True),
            encoding="utf-8")

    def invalidate(self) -> int:
        """Remove every entry (explicit cache invalidation). Returns the number removed."""
        n = 0
        for p in self.dir.glob("*.json"):
            p.unlink()
            n += 1
        return n


def _parse_graph_bound(statement: str):
    """Validate + destructure `invA <= / >= / == [k*]invB [+ c]` against the ONE product grammar
    and the classic invariant registry. Raises ValueError — refusal, never a guess."""
    from .invariants import INVARIANTS
    from .product import graph_statement_grammar
    m = graph_statement_grammar().match(statement)
    if not m:
        raise ValueError(f"not a graph-bound statement: {statement!r}")
    lhs, rel, k, rhs, c = (m.group(1), m.group(2), int(m.group(3) or 1),
                           m.group(4), int(m.group(5) or 0))
    rel = "==" if rel == "=" else rel
    for name in (lhs, rhs):
        if name not in INVARIANTS:
            raise ValueError(f"unknown invariant {name!r}; known: {sorted(INVARIANTS)}")
    return lhs, rel, k, rhs, c


def _scan_order(args) -> dict:
    """WORKER TASK: scan ALL connected graphs of one order for a violation. A pure function of
    its picklable (statement, n) argument — the same answer in any process, any worker count."""
    statement, n = args
    lhs, rel, k, rhs, c = _parse_graph_bound(statement)
    from .generate import generate_graphs
    from .invariants import evaluate
    holds = _REL[rel]
    checked = 0
    for g in generate_graphs(n):                     # deterministic order (canonical-key sorted)
        if evaluate(g, "num_components") != 1:
            continue
        checked += 1
        va, vb = evaluate(g, lhs), evaluate(g, rhs)
        if not holds(va, k * vb + c):
            # JSON-stable types only (lists, ints, strings): a cache round-trip must return the
            # BYTE-SAME structure a fresh computation returns — the cache can never change an answer.
            return {"n": n, "checked": checked,
                    "witness": {"n": n, "edges": [list(e) for e in sorted(g.edges)],
                                lhs: va, rhs: vb}}
    return {"n": n, "checked": checked, "witness": None}


def _decide_ramsey_instance(args) -> dict:
    """WORKER TASK: one Ramsey instance K_n vs (s, t). Only VERDICT-STABLE fields are returned
    (satisfiable / meaning / certainty) — the witness colouring is *an* example and may vary
    (ADR-0019 / threat-model T7), so it is deliberately not part of the mergeable record."""
    n, s, t = args
    from .ramsey_sat import ramsey_decide
    v = ramsey_decide(n, s, t)
    return {"n": n, "satisfiable": v.satisfiable, "meaning": v.meaning, "certainty": v.certainty}


def _run_tasks(worker, tasks: list, workers: int) -> list:
    """Execute the task list serially (workers <= 1) or on a Pool. The task set, the per-task
    function, and the caller's merge are all deterministic, so the split cannot change the
    answer — only the wall-clock."""
    if workers <= 1 or len(tasks) <= 1:
        return [worker(t) for t in tasks]
    with multiprocessing.Pool(min(workers, len(tasks))) as pool:
        return pool.map(worker, tasks)


def _cached_map(worker, key_of, tasks: list, workers: int, cache: DiskCache | None) -> list:
    """Cache-aware deterministic map: serve what the cache has, compute the rest (possibly in
    parallel), store fresh results. Output order matches `tasks` order regardless of cache state
    or worker count."""
    results: dict = {}
    fresh = []
    for t in tasks:
        got = cache.get(key_of(t)) if cache is not None else None
        if got is not None:
            results[t] = got
        else:
            fresh.append(t)
    for t, r in zip(fresh, _run_tasks(worker, fresh, workers)):
        if cache is not None:
            cache.put(key_of(t), r)
        results[t] = r
    return [results[t] for t in tasks]


@dataclass
class SweepResult:
    statement: str
    max_n: int
    verdict: str                      # "refuted" | "open" — same taxonomy as product.check
    tier: str                         # exact_integer_certificate | no_counterexample_within_bound
    witness: dict | None
    checked_per_order: tuple          # ((n, connected graphs checked), ...) — the full ledger
    scope_note: str = SCOPE_NOTE


def sweep_graph_bound(statement: str, max_n: int, workers: int = 1,
                      cache: DiskCache | None = None) -> SweepResult:
    """Parallel counterexample sweep of a graph bound/equality over ALL connected graphs with
    2 <= n <= max_n. Splits by order, merges deterministically (smallest-order witness wins) —
    the result is IDENTICAL for every worker count and any cache state."""
    _parse_graph_bound(statement)                            # refuse up front, before any worker
    from .generate import _BRUTE_MAX_N
    if max_n > _BRUTE_MAX_N:                                 # the generation wall, checked HERE:
        raise ValueError(                                    # one comparison, no worker launched
            f"max_n={max_n} exceeds the honest generation wall n <= {_BRUTE_MAX_N} "
            f"(2^(n choose 2) labeled graphs) — refused up front")
    tasks = [(statement, n) for n in range(2, max_n + 1)]
    rows = _cached_map(_scan_order, lambda t: f"graph_bound|{t[0]}|n={t[1]}", tasks,
                       workers, cache)
    rows.sort(key=lambda r: r["n"])                          # deterministic fold, order by n
    first = next((r for r in rows if r["witness"] is not None), None)
    return SweepResult(
        statement, max_n,
        "refuted" if first else "open",
        "exact_integer_certificate" if first else "no_counterexample_within_bound",
        dict(first["witness"]) if first else None,
        tuple((r["n"], r["checked"]) for r in rows))


@dataclass
class RamseySweep:
    s: int
    t: int
    verdicts: tuple                   # ({n, satisfiable, meaning, certainty}, ...) sorted by n
    ramsey_value: int | None          # first UNSAT n after a SAT n, iff the flip is in range
    scope_note: str = SCOPE_NOTE
    note: str = field(default="value = first UNSAT n, valid only when the SAT->UNSAT flip is "
                              "inside the range; witnesses are deliberately not merged "
                              "(a witness is AN example — ADR-0019)")


def sweep_ramsey(s: int, t: int, n_lo: int, n_hi: int, workers: int = 1,
                 cache: DiskCache | None = None) -> RamseySweep:
    """Decide every K_n instance in [n_lo, n_hi] (optionally in parallel), then apply the SAME
    bracket rule as `ramsey_sat.bracket_ramsey` in a deterministic merge."""
    tasks = [(n, s, t) for n in range(n_lo, n_hi + 1)]
    rows = _cached_map(_decide_ramsey_instance, lambda a: f"ramsey|{a[1]},{a[2]}|n={a[0]}",
                       tasks, workers, cache)
    rows.sort(key=lambda r: r["n"])
    value = None
    for prev, cur in zip(rows, rows[1:]):
        if prev["satisfiable"] and not cur["satisfiable"]:
            value = cur["n"]
    return RamseySweep(s, t, tuple(rows), value)
