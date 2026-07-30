"""
mathhead.discovery.rich_invariants — the rich invariant library (v2A5, Real Discovery Program).

Open graph-theory conjectures (the Graffiti corpus, Wagner's RL-refuted list) live on invariants the
engine did not have: independence number α, domination number γ, matching number ν, girth, diameter,
radius. This module adds them — EXACT computations (no heuristics), honest small-n scope (exponential
brute force where needed, documented), with classical anchors as tests:

  * Petersen graph: α=4, γ=3, ν=5, girth=5, diam=2 — the textbook anchor, all six checked;
  * König's theorem on bipartite graphs: ν = n − α — verified across the bipartite family (a LAW used
    as a cross-check oracle, exactly like the family closed-forms in `families.py`).

Conventions (explicit, not silent): girth = 0 for acyclic graphs; diameter/radius = -1 for disconnected
graphs (documented sentinels — the hunter restricts to connected classes anyway, via geng -c). These
invariants live in their OWN registry (`RICH_INVARIANTS`) so the v1 feature pipeline stays byte-stable;
the Kademe-2 counterexample hunter consumes them directly.
"""
from __future__ import annotations

from itertools import combinations

from .objects import Graph


def _adj(g: Graph) -> list:
    adj = [set() for _ in range(g.n)]
    for (u, v) in g.edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def independence_number(g: Graph) -> int:
    """α(g): the largest set of pairwise NON-adjacent vertices. Exact (branch on the first vertex)."""
    adj = _adj(g)

    def best(avail: frozenset) -> int:
        if not avail:
            return 0
        v = min(avail)
        without = best(avail - {v})                       # v excluded
        with_v = 1 + best(avail - {v} - adj[v])           # v included ⇒ its neighbours excluded
        return max(without, with_v)

    return best(frozenset(range(g.n)))


def domination_number(g: Graph) -> int:
    """γ(g): the smallest set whose closed neighbourhoods cover every vertex. Exact (size sweep)."""
    if g.n == 0:
        return 0
    adj = _adj(g)
    closed = [adj[v] | {v} for v in range(g.n)]
    everything = set(range(g.n))
    for k in range(1, g.n + 1):
        for combo in combinations(range(g.n), k):
            if set().union(*(closed[v] for v in combo)) == everything:
                return k
    return g.n


def matching_number(g: Graph) -> int:
    """ν(g): the maximum number of pairwise disjoint edges. Exact (branch on the first vertex)."""
    adj = _adj(g)

    def best(avail: frozenset) -> int:
        live = [v for v in sorted(avail) if adj[v] & avail]
        if not live:
            return 0
        v = live[0]
        out = best(avail - {v})                           # v stays unmatched
        for u in sorted(adj[v] & avail):
            out = max(out, 1 + best(avail - {v, u}))      # v matched to u
        return out

    return best(frozenset(range(g.n)))


def girth(g: Graph) -> int:
    """Length of the shortest cycle; 0 if the graph is acyclic (explicit convention)."""
    adj = _adj(g)
    best = 0
    for s in range(g.n):                                  # BFS from each vertex
        dist, parent = {s: 0}, {s: None}
        queue = [s]
        for v in queue:
            for u in sorted(adj[v]):
                if u not in dist:
                    dist[u], parent[u] = dist[v] + 1, v
                    queue.append(u)
                elif parent[v] != u:                      # non-tree edge closes a cycle through s's tree
                    cycle = dist[v] + dist[u] + 1
                    if best == 0 or cycle < best:
                        best = cycle
    return best


def _eccentricities(g: Graph):
    """Per-vertex eccentricity, or None if g is disconnected (or empty)."""
    if g.n == 0:
        return None
    adj = _adj(g)
    eccs = []
    for s in range(g.n):
        dist = {s: 0}
        queue = [s]
        for v in queue:
            for u in sorted(adj[v]):
                if u not in dist:
                    dist[u] = dist[v] + 1
                    queue.append(u)
        if len(dist) != g.n:
            return None                                   # disconnected
        eccs.append(max(dist.values()))
    return eccs


def diameter(g: Graph) -> int:
    """max eccentricity; -1 for disconnected/empty graphs (explicit sentinel, not a silent 0)."""
    eccs = _eccentricities(g)
    return -1 if eccs is None else max(eccs)


def radius(g: Graph) -> int:
    """min eccentricity; -1 for disconnected/empty graphs (explicit sentinel)."""
    eccs = _eccentricities(g)
    return -1 if eccs is None else min(eccs)


RICH_INVARIANTS: dict = {
    "independence_number": independence_number,
    "domination_number": domination_number,
    "matching_number": matching_number,
    "girth": girth,
    "diameter": diameter,
    "radius": radius,
}


def petersen() -> Graph:
    """The Petersen graph — outer C5 (0-4), inner pentagram (5-9), spokes i—i+5."""
    outer = [(i, (i + 1) % 5) for i in range(5)]
    inner = [(5 + i, 5 + (i + 2) % 5) for i in range(5)]
    spokes = [(i, i + 5) for i in range(5)]
    return Graph.from_edges(10, outer + inner + spokes)
