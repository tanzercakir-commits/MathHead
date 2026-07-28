"""
mathhead.cache — Deterministic memoization (ROADMAP K1).

Because every engine primitive is DETERMINISTIC (same input → same result,
PRINCIPLES 1), memoizing a pure operation is SAFE: a cache hit returns exactly the
result the function would have recomputed. This module provides a small bounded-LRU
`@memoize` decorator used on the hot, side-effect-free compute functions, plus
`cache_stats()` for observability.

Design choices that keep it honest:
  * A hit returns the SAME cached result object — byte-for-byte identical to a fresh
    computation — so determinism is *strengthened*, never weakened.
  * The cache is bounded (LRU eviction); it cannot grow without limit.
  * It is applied ONLY to pure functions with hashable arguments; anything stateful,
    randomized, or list-argument is deliberately left uncached.
"""
from __future__ import annotations

import functools
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable

_CAPACITY = 1024
_cache: "OrderedDict[tuple, Any]" = OrderedDict()
_stats = {"hits": 0, "misses": 0, "evictions": 0}


def memoize(fn: Callable) -> Callable:
    """Bounded-LRU memoization for a deterministic, hashable-argument function."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            key = (fn.__qualname__, args, tuple(sorted(kwargs.items())))
            hash(key)
        except TypeError:
            return fn(*args, **kwargs)          # unhashable args → never cache
        if key in _cache:
            _stats["hits"] += 1
            _cache.move_to_end(key)
            return _cache[key]                  # identical object → determinism preserved
        _stats["misses"] += 1
        result = fn(*args, **kwargs)
        _cache[key] = result
        if len(_cache) > _CAPACITY:
            _cache.popitem(last=False)
            _stats["evictions"] += 1
        return result

    wrapper.__wrapped__ = fn
    return wrapper


def cache_stats() -> dict[str, Any]:
    """Current cache statistics: hits, misses, hit-rate, size, capacity, evictions."""
    total = _stats["hits"] + _stats["misses"]
    return {
        "hits": _stats["hits"],
        "misses": _stats["misses"],
        "hit_rate": round(_stats["hits"] / total, 4) if total else 0.0,
        "size": len(_cache),
        "capacity": _CAPACITY,
        "evictions": _stats["evictions"],
    }


def reset_cache() -> None:
    """Clear the cache and statistics (used for test isolation / a fresh session)."""
    _cache.clear()
    _stats["hits"] = 0
    _stats["misses"] = 0
    _stats["evictions"] = 0


@dataclass
class CacheStats:
    """Output of the `cache_stats` tool (deterministic memoization observability)."""

    status: str
    reason_code: str
    explanation: str
    stats: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


def cache_stats_result() -> CacheStats:
    t0 = time.perf_counter()
    s = cache_stats()
    return CacheStats("ok", "CACHE_STATS",
                      f"Memoization cache: {s['hits']} hits / {s['misses']} misses "
                      f"(hit-rate {s['hit_rate']}), {s['size']}/{s['capacity']} entries.",
                      s, {"engine": "cache", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)})
