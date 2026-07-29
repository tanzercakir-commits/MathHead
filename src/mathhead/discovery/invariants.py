"""
mathhead.discovery.invariants — property & invariant evaluation (roadmap Track O0/O1).

Deterministic, exact graph invariants — the measurements the discovery loop later mines for
patterns (equalities, inequalities, forbidden structure) and assembles into feature tables.
All pure Python and exact; no randomness. Heavier / spectral invariants (routed through the
MathHead compute/judge spine) are a later addition — this first layer is standalone "matter".
"""
from __future__ import annotations

from .objects import Graph


def num_vertices(g: Graph) -> int:
    return g.n


def num_edges(g: Graph) -> int:
    return g.num_edges


def degree_sequence(g: Graph) -> tuple:
    """Non-decreasing degree sequence (an isomorphism invariant)."""
    return tuple(sorted(g.degrees()))


def max_degree(g: Graph) -> int:
    d = g.degrees()
    return max(d) if d else 0


def min_degree(g: Graph) -> int:
    d = g.degrees()
    return min(d) if d else 0


def sum_degrees(g: Graph) -> int:
    """Sum of all vertex degrees. (Equals 2*|E| — the Handshake Lemma; the discovery engine
    is meant to REDISCOVER that relation, so we do not hardcode it here.)"""
    return sum(g.degrees())


def num_triangles(g: Graph) -> int:
    """Number of 3-cliques (triangles)."""
    n = g.n
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            if not g.has_edge(i, j):
                continue
            for k in range(j + 1, n):
                if g.has_edge(i, k) and g.has_edge(j, k):
                    count += 1
    return count


def _components(g: Graph) -> list:
    """Connected components via union-find; returns a list of vertex sets."""
    parent = list(range(g.n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b) in g.edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    groups: dict = {}
    for v in range(g.n):
        groups.setdefault(find(v), set()).add(v)
    return list(groups.values())


def num_components(g: Graph) -> int:
    return 0 if g.n == 0 else len(_components(g))


def is_connected(g: Graph) -> bool:
    return g.n > 0 and num_components(g) == 1


# Named registry so the discovery loop can request invariants by name (feature tables, O3).
INVARIANTS = {
    "num_vertices": num_vertices,
    "num_edges": num_edges,
    "sum_degrees": sum_degrees,
    "degree_sequence": degree_sequence,
    "max_degree": max_degree,
    "min_degree": min_degree,
    "num_triangles": num_triangles,
    "num_components": num_components,
    "is_connected": is_connected,
}

# The integer-valued invariants — the columns the relation miner (O2) runs over. Excludes
# the tuple (degree_sequence) and the boolean (is_connected), which are not linear features.
NUMERIC_INVARIANTS = [
    "num_vertices", "num_edges", "sum_degrees", "num_triangles",
    "max_degree", "min_degree", "num_components",
]


def evaluate(g: Graph, name: str):
    """Evaluate one named invariant on g."""
    if name not in INVARIANTS:
        raise KeyError(f"unknown invariant {name!r}; known: {sorted(INVARIANTS)}")
    return INVARIANTS[name](g)


def invariant_vector(g: Graph, names=None) -> dict:
    """All (or the named) invariants of g as a dict — one row of a feature table (O3)."""
    names = names or list(INVARIANTS)
    return {name: evaluate(g, name) for name in names}
