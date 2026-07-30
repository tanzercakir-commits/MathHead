"""
mathhead.discovery.adversarial_objects — random / adversarial / extreme object generators (N4/N5).

Structured families (`families.py`) cover the "nice" cases; this covers the NASTY ones — the
degenerate, the extreme, and the seeded-random — so invariants and the discovery pipeline are
stress-tested against edge cases (empty graph, single vertex, disconnected unions, K_n and K_n−e,
dense/sparse randoms). A robust engine must not crash or mis-measure on these.

Randomness is SEEDED (`random.Random(seed)`) so every generator is reproducible.
"""
from __future__ import annotations

import random
from itertools import combinations

from .families import complete, cycle, empty, path, star
from .objects import Graph


def degenerate_graphs(n: int):
    """Degenerate / boundary graphs: edgeless, a lone edge, disconnected unions."""
    yield empty(n)                                          # all isolated
    if n >= 2:
        yield Graph.from_edges(n, [(0, 1)])                # one edge, rest isolated
    if n >= 4:
        yield Graph.from_edges(n, [(0, 1), (2, 3)])        # two disjoint edges (disconnected)
    if n >= 3:
        yield Graph.from_edges(n, [(0, 1), (1, 2)])        # a path fragment + isolated tail


def extreme_graphs(n: int):
    """Extreme graphs: complete, complete-minus-an-edge, and the structured extremes."""
    yield complete(n)
    if n >= 2:
        all_edges = list(combinations(range(n), 2))
        yield Graph.from_edges(n, all_edges[:-1])          # K_n − e (one edge short of complete)
        yield path(n)
        yield star(n)
    if n >= 3:
        yield cycle(n)


def random_graphs(n: int, count: int = 5, seed: int = 42, p: float = 0.5):
    """`count` seeded-random G(n, p) graphs — reproducible for a given seed."""
    rng = random.Random(seed)
    for _ in range(count):
        edges = [(i, j) for i, j in combinations(range(n), 2) if rng.random() < p]
        yield Graph.from_edges(n, edges)


def stress_set(max_n: int = 6, seed: int = 42) -> list:
    """A diverse adversarial stress set: degenerate + extreme + seeded-random, over sizes up to
    max_n. Deterministic for a given seed."""
    out = []
    for n in range(1, max_n + 1):
        out.extend(degenerate_graphs(n))
        out.extend(extreme_graphs(n))
        out.extend(random_graphs(n, count=3, seed=seed + n))
    return out
