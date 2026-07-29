"""
mathhead.discovery.canonical — canonical labeling / isomorphism elimination (roadmap Track N2).

Two graphs are isomorphic iff they share a `canonical_key`. The key is the minimum
adjacency-bitmask over vertex relabelings, restricted to relabelings that order vertices by
degree.

Why degree-restriction is correct (not just faster): an isomorphism preserves degree, so for
two isomorphic graphs the degree-consistent relabeling sets correspond exactly and produce the
same set of bitmasks — hence the same minimum. The key stays isomorphism-invariant while the
factorial search collapses whenever degrees differ (only equal-degree blocks are permuted).

Correct and simple; cost is prod(block!) per graph (n! only for regular graphs). Enough for
the v0.1 domain (small n). Partition-backtracking refinement (nauty-style) is a planned
optimization (roadmap N2-opt), not needed for correctness.
"""
from __future__ import annotations

from itertools import permutations, product

from .objects import Graph


def _pair_index(n: int) -> dict:
    """Fixed lexicographic order of vertex pairs (i<j) -> bit position."""
    idx = {}
    b = 0
    for i in range(n):
        for j in range(i + 1, n):
            idx[(i, j)] = b
            b += 1
    return idx


def _degree_consistent_perms(degrees: tuple):
    """Yield relabelings p (new_vertex i corresponds to old vertex p[i]) that place vertices in
    blocks of non-decreasing degree, permuting freely within each equal-degree block."""
    n = len(degrees)
    order = sorted(range(n), key=lambda v: degrees[v])
    blocks = []
    i = 0
    while i < n:
        j = i
        while j < n and degrees[order[j]] == degrees[order[i]]:
            j += 1
        blocks.append(tuple(order[i:j]))
        i = j
    for combo in product(*[permutations(block) for block in blocks]):
        p: list = []
        for part in combo:
            p.extend(part)
        yield p


def canonical_key(g: Graph) -> tuple:
    """(n, canonical_bitmask): equal iff isomorphic. Deterministic."""
    n = g.n
    if n == 0:
        return (0, 0)
    idx = _pair_index(n)
    best = None
    for p in _degree_consistent_perms(g.degrees()):
        mask = 0
        for i in range(n):
            pi = p[i]
            for j in range(i + 1, n):
                if g.has_edge(pi, p[j]):
                    mask |= 1 << idx[(i, j)]
        if best is None or mask < best:
            best = mask
    return (n, best)


def canonical_graph(g: Graph) -> Graph:
    """The canonically-relabeled representative of g's isomorphism class."""
    return graph_from_key(canonical_key(g))


def graph_from_key(key: tuple) -> Graph:
    """Reconstruct the representative Graph from a canonical key (n, mask)."""
    n, mask = key
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    edges = frozenset(pairs[b] for b in range(len(pairs)) if (mask >> b) & 1)
    return Graph(n, edges)


def is_isomorphic(g1: Graph, g2: Graph) -> bool:
    """Are two graphs isomorphic? (cheap rejects on n / edge count, then canonical key.)"""
    if g1.n != g2.n or g1.num_edges != g2.num_edges:
        return False
    return canonical_key(g1) == canonical_key(g2)
