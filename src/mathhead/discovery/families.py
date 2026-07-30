"""
mathhead.discovery.families — parametric object families + stratified sampling (roadmap N4).

Brute non-isomorphic generation is honest but bounded (n ≤ 7). Named PARAMETRIC families give the
engine specific structured objects at any size — K_n, C_n, P_n, stars, wheels, complete bipartite —
so discoveries and bounds can be probed on an infinite family (e.g. "does ω ≤ χ hold on K_n for large
n?"), and so tests get a stratified, diverse sample instead of only the small brute enumeration.

Each family's invariants have a KNOWN closed form, so this doubles as a correctness oracle for the
invariant code (a mini cross-check): K_n has C(n,2) edges and χ = ω = n; C_n has n edges and χ = 2/3;
a star has n−1 edges and χ = 2; etc.
"""
from __future__ import annotations

from itertools import combinations

from .objects import Graph


def complete(n: int) -> Graph:
    """K_n — every pair adjacent. C(n,2) edges, χ = ω = n."""
    return Graph.from_edges(n, list(combinations(range(n), 2)))


def empty(n: int) -> Graph:
    """The edgeless graph on n vertices. χ = 1 (n≥1)."""
    return Graph.from_edges(n, [])


def path(n: int) -> Graph:
    """P_n — a simple path. n−1 edges, χ = 2 (n≥2), not Hamiltonian."""
    return Graph.from_edges(n, [(i, i + 1) for i in range(n - 1)])


def cycle(n: int) -> Graph:
    """C_n (n ≥ 3) — n edges, χ = 2 if n even else 3, Hamiltonian."""
    if n < 3:
        raise ValueError("cycle needs n >= 3")
    return Graph.from_edges(n, [(i, (i + 1) % n) for i in range(n)])


def star(n: int) -> Graph:
    """Star K_{1,n−1} — one hub adjacent to n−1 leaves. n−1 edges, χ = 2."""
    return Graph.from_edges(n, [(0, i) for i in range(1, n)])


def wheel(n: int) -> Graph:
    """W_n (n ≥ 4) — a hub (vertex 0) joined to every vertex of a C_{n−1} on 1..n−1."""
    if n < 4:
        raise ValueError("wheel needs n >= 4")
    rim = [(i, i + 1) for i in range(1, n - 1)] + [(n - 1, 1)]
    spokes = [(0, i) for i in range(1, n)]
    return Graph.from_edges(n, rim + spokes)


def complete_bipartite(a: int, b: int) -> Graph:
    """K_{a,b} — every vertex of part A adjacent to every vertex of part B. a·b edges, χ = 2."""
    return Graph.from_edges(a + b, [(i, a + j) for i in range(a) for j in range(b)])


# name -> (callable, arity) ; arity 1 families take n, complete_bipartite takes (a, b)
FAMILIES = {
    "complete": complete,
    "empty": empty,
    "path": path,
    "cycle": cycle,
    "star": star,
    "wheel": wheel,
}


def stratified_sample(max_n: int = 8) -> list:
    """A diverse, structured sample across families up to size max_n — for targeted discovery and
    tests (complements the small brute enumeration with larger, named structure)."""
    out = []
    for n in range(1, max_n + 1):
        out.append(complete(n))
        out.append(empty(n))
        if n >= 2:
            out.append(path(n))
            out.append(star(n))
        if n >= 3:
            out.append(cycle(n))
        if n >= 4:
            out.append(wheel(n))
    for a in range(1, max_n // 2 + 1):
        for b in range(a, max_n - a + 1):
            out.append(complete_bipartite(a, b))
    return out
