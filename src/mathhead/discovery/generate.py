"""
mathhead.discovery.generate — canonical object generation (roadmap Track N1).

Generates all NON-isomorphic simple graphs on n vertices by enumerating labeled graphs and
deduplicating via the canonical key (Track N2). Brute enumeration is 2^(n choose 2) labeled
graphs, so it is honest-bounded: fast for n <= 6, slow for n = 7, refused beyond. No silent
cap — exceeding the bound raises, per the project's "honest walls" principle. Orderly /
McKay generation (to push n higher) is the planned N1 optimization on the roadmap.

Correctness is pinned against OEIS A000088 (number of graphs on n nodes): 1, 1, 2, 4, 11, 34,
156, 1044, ... — `count_non_isomorphic(n)` must reproduce this sequence.
"""
from __future__ import annotations

from .canonical import canonical_key, graph_from_key
from .objects import Graph

_BRUTE_MAX_N = 7  # 2^21 labeled graphs at n=7; beyond this brute enumeration is infeasible


def all_pairs(n: int) -> list:
    return [(i, j) for i in range(n) for j in range(i + 1, n)]


def generate_graphs(n: int) -> list:
    """One representative Graph per isomorphism class on n vertices (in canonical form).

    Returned in a deterministic order (sorted by canonical key). Raises ValueError for
    n > 7 — an honest bound, not a silent truncation.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if n > _BRUTE_MAX_N:
        raise ValueError(
            f"brute generation is bounded at n <= {_BRUTE_MAX_N} "
            f"(2^(n choose 2) labeled graphs); orderly generation (McKay) is roadmap N1-opt"
        )
    pairs = all_pairs(n)
    m = len(pairs)
    seen: dict = {}
    for mask in range(1 << m):
        edges = frozenset(pairs[b] for b in range(m) if (mask >> b) & 1)
        key = canonical_key(Graph(n, edges))
        if key not in seen:
            seen[key] = graph_from_key(key)
    return [seen[k] for k in sorted(seen)]


def count_non_isomorphic(n: int) -> int:
    """Number of non-isomorphic simple graphs on n vertices (OEIS A000088)."""
    return len(generate_graphs(n))
