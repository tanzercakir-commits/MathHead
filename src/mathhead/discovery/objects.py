"""
mathhead.discovery.objects — typed mathematical object model (roadmap Track N0).

The discovery engine works on *mathematical objects* it can generate, canonicalize, and
measure. This module defines the object model. We start with the finite simple graph (the
roadmap's v0.1 domain: finite combinatorics + graph theory), behind a minimal `MathObject`
base so more object types (integer sequences, finite models, matrices, ...) can slot in later
without changing the generator/invariant machinery.

Design: objects are IMMUTABLE and hashable, so they can be deduplicated, cached, and used as
dict keys — determinism is a first-class concern here, mirroring MathHead's contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class MathObject:
    """Base for a typed mathematical object. Subclasses set `kind` and stay immutable+hashable."""

    kind: str = "object"


@dataclass(frozen=True)
class Graph(MathObject):
    """A finite simple graph on vertices 0..n-1 (undirected, no loops, no multi-edges).

    `edges` is a frozenset of (i, j) tuples with 0 <= i < j < n. `n` is stored explicitly so
    isolated vertices are represented faithfully (a graph is not just its edge set).
    """

    n: int
    edges: frozenset  # frozenset[tuple[int, int]], each (i, j) with 0 <= i < j < n
    kind = "graph"

    def __post_init__(self) -> None:
        if self.n < 0:
            raise ValueError("n must be >= 0")
        for e in self.edges:
            if not (isinstance(e, tuple) and len(e) == 2):
                raise ValueError(f"edge must be a 2-tuple: {e!r}")
            i, j = e
            if not (0 <= i < j < self.n):
                raise ValueError(f"edge {e!r} must satisfy 0 <= i < j < n={self.n}")

    @classmethod
    def from_edges(cls, n: int, edges: Iterable) -> "Graph":
        """Build a graph, normalizing each edge to (min, max) and dropping duplicates."""
        norm = set()
        for (a, b) in edges:
            if a == b:
                raise ValueError(f"loops are not allowed: ({a}, {b})")
            norm.add((a, b) if a < b else (b, a))
        return cls(n, frozenset(norm))

    def has_edge(self, i: int, j: int) -> bool:
        a, b = (i, j) if i < j else (j, i)
        return (a, b) in self.edges

    def neighbors(self, v: int) -> set:
        out: set = set()
        for (a, b) in self.edges:
            if a == v:
                out.add(b)
            elif b == v:
                out.add(a)
        return out

    def degree(self, v: int) -> int:
        return sum(1 for e in self.edges if v in e)

    def degrees(self) -> tuple:
        """Degree of every vertex, indexed by vertex 0..n-1."""
        d = [0] * self.n
        for (a, b) in self.edges:
            d[a] += 1
            d[b] += 1
        return tuple(d)

    @property
    def num_edges(self) -> int:
        return len(self.edges)
