"""
mathhead.discovery.object_store — a queryable object store indexed by invariant (roadmap N6).

Built on N3 (content-hash dedup) and O0/O1 (the invariant registry): a store you can fill with objects
and then QUERY by invariant value — "every graph with χ = 3", "num_edges = 6 and num_triangles = 0".
Adding is idempotent (content-hash dedup), and each object is indexed under every (invariant, value)
pair, so queries are set intersections. This is the substrate targeted discovery and feature-table
work read from.

Deterministic: returned lists are in reproducible (content-hash) order.
"""
from __future__ import annotations

from collections import defaultdict

from .invariants import INVARIANTS
from .serialize import content_hash, reproducible_sort


class ObjectStore:
    """A content-deduplicated object store with an inverted index on invariant values."""

    def __init__(self, invariants: dict | None = None) -> None:
        # name -> callable; default to the graph invariant registry (the richest set)
        self._invariants = dict(invariants) if invariants is not None else dict(INVARIANTS)
        self._by_hash: dict = {}                                   # hash -> object
        self._index: dict = defaultdict(lambda: defaultdict(set))  # inv_name -> value -> {hash}

    def add(self, obj) -> str:
        """Add one object (idempotent by content hash). Returns its hash."""
        h = content_hash(obj)
        if h not in self._by_hash:
            self._by_hash[h] = obj
            for name, fn in self._invariants.items():
                try:
                    val = fn(obj)
                except Exception:                                 # noqa: BLE001 (invariant N/A for obj)
                    continue
                try:
                    self._index[name][val].add(h)
                except TypeError:                                 # unhashable invariant value — skip index
                    pass
        return h

    def add_all(self, objs) -> None:
        for o in objs:
            self.add(o)

    def by_invariant(self, name: str, value) -> list:
        """All stored objects whose invariant `name` equals `value`."""
        hashes = self._index.get(name, {}).get(value, set())
        return reproducible_sort(self._by_hash[h] for h in hashes)

    def query(self, **filters) -> list:
        """Objects matching ALL invariant=value filters (set intersection over the index)."""
        if not filters:
            return self.all()
        sets = []
        for name, value in filters.items():
            sets.append(self._index.get(name, {}).get(value, set()))
        matched = set.intersection(*sets) if sets else set()
        return reproducible_sort(self._by_hash[h] for h in matched)

    def all(self) -> list:
        return reproducible_sort(self._by_hash.values())

    def invariant_values(self, name: str) -> list:
        """The distinct values seen for an invariant (sorted)."""
        return sorted(self._index.get(name, {}))

    def __len__(self) -> int:
        return len(self._by_hash)
