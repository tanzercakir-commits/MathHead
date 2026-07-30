"""
mathhead.discovery.representations — a verified registry of representation transforms (roadmap U0).

The engine already crosses between representations everywhere — graph↔matrix (spectral), graph↔SAT
(coloring), divisibility↔finite-residue (kernel), composition↔subset (the cut-point bijection). U0 makes
that plurality EXPLICIT and, crucially, VERIFIED: each bridge is registered with the kind of guarantee it
offers and a check that confirms it on a sample. Where O4 (`cross_check`) confirms invariant VALUES agree
across computation paths, U0 confirms the TRANSFORMS themselves are faithful — a complementary safety net
that catches a broken encoder/decoder, not just a mismeasured number.

Three guarantee kinds, each honestly labelled:
  * round_trip          — the transform is INVERTIBLE: decode(encode(x)) == x (graph ↔ adjacency matrix,
                          composition ↔ cut-point subset);
  * invariant_preserving— the transform is lossy but preserves a stated invariant (graph → degree
                          sequence preserves Σdeg = 2|E|, the Handshake quantity);
  * decision            — the target representation DECIDES a claim (the residue table [p(r) mod m] is
                          all-zero iff the kernel proves m|p(n)) — the two verdicts must agree.

`verify_representations` runs every bridge over a sample and reports `faithful` per bridge; a False would
mean a real encoding bug. Deterministic, exact integer arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass

from .compositions import composition_to_cutset, cutset_to_composition, generate_compositions
from .kernel import KernelError, Residue, _norm, check
from .objects import Graph


# --- graph ↔ adjacency matrix (round trip) ------------------------------------------------------
def graph_to_adjacency(g: Graph) -> tuple:
    """A graph → its symmetric 0/1 adjacency matrix (row-major tuple of tuples)."""
    mat = [[0] * g.n for _ in range(g.n)]
    for (u, v) in g.edges:
        mat[u][v] = mat[v][u] = 1
    return tuple(tuple(row) for row in mat)


def adjacency_to_graph(mat: tuple) -> Graph:
    """A symmetric 0/1 adjacency matrix → the graph (edges i<j with mat[i][j]=1)."""
    n = len(mat)
    edges = frozenset((i, j) for i in range(n) for j in range(i + 1, n) if mat[i][j])
    return Graph(n, edges)


# --- graph → degree sequence (invariant-preserving: Σdeg = 2|E|) --------------------------------
def graph_to_degree_sequence(g: Graph) -> tuple:
    return tuple(sorted(g.degrees()))


# --- divisibility m|p(n) → residue table (decision) ---------------------------------------------
def divisibility_to_residue_table(m: int, poly: tuple) -> tuple:
    """The finite-residue representation of `m | p(n)`: [p(r) mod m for r in 0..m−1]. The universal
    claim holds iff this table is all-zero (p(n) mod m depends only on n mod m)."""
    p = _norm(poly)
    table = []
    for r in range(m):
        v = 0
        for c in reversed(p):
            v = (v * r + c) % m
        table.append(v % m)
    return tuple(table)


# --- the registry -------------------------------------------------------------------------------
@dataclass
class RepresentationBridge:
    name: str
    source: str
    target: str
    kind: str                   # "round_trip" | "invariant_preserving" | "decision"
    faithful: bool              # the guarantee checked out on the sample


def _graphs(bound: int = 5) -> list:
    from .generate import generate_graphs
    return [g for n in range(1, bound + 1) for g in generate_graphs(n)]


def verify_representations(graph_bound: int = 5) -> list:
    """Check every registered bridge on a sample; return one RepresentationBridge each with `faithful`."""
    graphs = _graphs(graph_bound)

    round_trip_ok = all(adjacency_to_graph(graph_to_adjacency(g)) == g for g in graphs)

    handshake_ok = all(sum(graph_to_degree_sequence(g)) == 2 * g.num_edges for g in graphs)

    comp_ok = True
    for n in range(1, 8):
        for c in generate_compositions(n):
            if cutset_to_composition(n, composition_to_cutset(c)).parts != c.parts:
                comp_ok = False
                break

    # residue-table decision must AGREE with the kernel verdict on a battery of (m, poly) cases
    cases = [(6, (0, -1, 0, 1)), (30, (0, -1, 0, 0, 0, 1)), (5, (0, -1, 0, 1)), (4, (0, 0, 1))]
    decision_ok = True
    for m, poly in cases:
        table_says = all(x == 0 for x in divisibility_to_residue_table(m, poly))
        try:
            check(Residue(m, poly))
            kernel_says = True
        except KernelError:
            kernel_says = False
        if table_says != kernel_says:
            decision_ok = False
            break

    return [
        RepresentationBridge("graph↔adjacency-matrix", "graph", "matrix", "round_trip", round_trip_ok),
        RepresentationBridge("composition↔cut-point-subset", "composition", "subset", "round_trip",
                             comp_ok),
        RepresentationBridge("graph→degree-sequence", "graph", "degree_sequence",
                             "invariant_preserving", handshake_ok),
        RepresentationBridge("divisibility→residue-table", "divisibility", "residue_table", "decision",
                             decision_ok),
    ]


def all_faithful(graph_bound: int = 5) -> bool:
    """True iff every registered representation bridge is faithful on the sample."""
    return all(b.faithful for b in verify_representations(graph_bound))
