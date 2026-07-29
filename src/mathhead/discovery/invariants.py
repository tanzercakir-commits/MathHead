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


def _adjacency_int(g: Graph) -> list:
    A = [[0] * g.n for _ in range(g.n)]
    for (a, b) in g.edges:
        A[a][b] = 1
        A[b][a] = 1
    return A


def _trace_of_power(g: Graph, k: int) -> int:
    """trace(A^k) = Σ λ^k over the adjacency spectrum — computed exactly by integer matmul."""
    n = g.n
    a = _adjacency_int(g)
    m = [row[:] for row in a]
    for _ in range(k - 1):
        m = [[sum(m[i][t] * a[t][j] for t in range(n)) for j in range(n)] for i in range(n)]
    return sum(m[i][i] for i in range(n))


def spectral_moment_2(g: Graph) -> int:
    """Σ λ² over the adjacency spectrum (= trace(A²)). A spectral quantity — the discovery engine
    is meant to REDISCOVER that it equals 2·|E|, so we don't hardcode that here."""
    return _trace_of_power(g, 2)


def spectral_moment_3(g: Graph) -> int:
    """Σ λ³ over the adjacency spectrum (= trace(A³)); the engine should find it is 6·(#triangles)."""
    return _trace_of_power(g, 3)


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


def is_forest(g: Graph) -> bool:
    """True iff the graph is acyclic. Detected STRUCTURALLY (union-find: an edge joining two
    already-connected vertices closes a cycle) — deliberately NOT via the E = V - C formula, so
    the discovery engine can rediscover that formula on forests without circularity."""
    parent = list(range(g.n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b) in g.edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        parent[ra] = rb
    return True


def is_tree(g: Graph) -> bool:
    """Connected and acyclic."""
    return is_connected(g) and is_forest(g)


def chromatic_number(g: Graph) -> int:
    """Minimum number of colors for a proper coloring (backtracking; exact for small n)."""
    if g.n == 0:
        return 0
    if not g.edges:
        return 1
    adj = [set() for _ in range(g.n)]
    for (u, v) in g.edges:
        adj[u].add(v)
        adj[v].add(u)
    color = [-1] * g.n

    def feasible(k: int) -> bool:
        def bt(v: int) -> bool:
            if v == g.n:
                return True
            for c in range(k):
                if all(color[u] != c for u in adj[v]):
                    color[v] = c
                    if bt(v + 1):
                        return True
                    color[v] = -1
            return False
        for i in range(g.n):
            color[i] = -1
        return bt(0)

    for k in range(1, g.n + 1):
        if feasible(k):
            return k
    return g.n


def clique_number(g: Graph) -> int:
    """Size of the largest clique (a set of pairwise-adjacent vertices)."""
    from itertools import combinations
    if g.n == 0:
        return 0
    for size in range(g.n, 1, -1):
        for combo in combinations(range(g.n), size):
            if all(g.has_edge(a, b) for a, b in combinations(combo, 2)):
                return size
    return 1


def is_hamiltonian(g: Graph) -> bool:
    """True iff g has a Hamiltonian CYCLE (a closed walk visiting every vertex exactly once).
    Standard convention: requires n ≥ 3. Decided STRUCTURALLY by backtracking from a fixed start
    vertex (exact for small n) — deliberately not via any sufficient-condition theorem, so the
    discovery engine can rediscover those (e.g. Dirac) without circularity."""
    n = g.n
    if n < 3:
        return False
    adj = [set() for _ in range(n)]
    for (u, v) in g.edges:
        adj[u].add(v)
        adj[v].add(u)
    visited = [False] * n
    visited[0] = True                       # fix vertex 0 as the start (kills rotation symmetry)

    def bt(v: int, count: int) -> bool:
        if count == n:
            return 0 in adj[v]              # all visited — can we close back to the start?
        for w in adj[v]:
            if not visited[w]:
                visited[w] = True
                if bt(w, count + 1):
                    return True
                visited[w] = False
        return False

    return bt(0, 1)


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
    "is_forest": is_forest,
    "is_tree": is_tree,
    "spectral_moment_2": spectral_moment_2,
    "spectral_moment_3": spectral_moment_3,
    "chromatic_number": chromatic_number,
    "clique_number": clique_number,
    "is_hamiltonian": is_hamiltonian,
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
