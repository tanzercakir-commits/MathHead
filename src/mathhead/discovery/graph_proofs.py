"""
mathhead.discovery.graph_proofs — CONSTRUCTIVE certificates for the surviving frontier LAWS
(roadmap: discover → refute → *prove*, graph domain).

The coloring laws that survived refutation (OPEN, ADR-D0020) are upgraded here from *observed*
("the inequality held on the sample") to *constructively certified* ("here is an explicit witness
that realizes the bound on every graph, independently re-checked"):

  * χ ≤ Δ+1  — a GREEDY (first-fit) proper coloring is CONSTRUCTED; a checker re-verifies it is
               proper AND uses ≤ Δ+1 colors. Universal reason: when a vertex is colored, its ≤ Δ
               already-colored neighbors block ≤ Δ colors, so a (Δ+1)-palette always has a free one.
  * χ ≤ n    — the identity (all-distinct) coloring is trivially proper.
  * ω ≤ χ    — a maximum CLIQUE is exhibited; its ω pairwise-adjacent vertices need ω distinct
               colors, so χ ≥ ω. The lower bound is DOUBLE-confirmed by MathHead: the clique cannot
               be (ω−1)-colored (`graph_coloring` → unsat).

HONEST STATUS — read this. Each certificate is `constructive_bounded`: an explicit, independently
re-checked witness over graphs up to the bound n. That is strictly stronger than `bounded_check`,
but it is NOT a universal proof. The universal ARGUMENT (greedy always fits; a clique forces its
size) is recorded on the certificate for the reader, but it is not machine-verified — a universal
∀G proof needs the logic/kernel layer (roadmap 🔴, far off). We deliberately do NOT label these
PROVED. A constructed, checked witness is exactly what we have, and we say so.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from mathhead.router import route

from .invariants import chromatic_number, clique_number, max_degree, num_vertices
from .objects import Graph


def greedy_coloring(g: Graph) -> dict:
    """First-fit proper coloring over vertices 0..n−1: give each vertex the smallest color not used
    by an already-colored neighbor. Uses ≤ Δ+1 colors (≤ Δ neighbors block ≤ Δ colors)."""
    adj = [set() for _ in range(g.n)]
    for (u, v) in g.edges:
        adj[u].add(v)
        adj[v].add(u)
    color: dict = {}
    for v in range(g.n):
        used = {color[u] for u in adj[v] if u in color}
        c = 0
        while c in used:
            c += 1
        color[v] = c
    return color


def max_clique(g: Graph) -> tuple:
    """Return the vertex set of a maximum clique (largest pairwise-adjacent set), as a tuple."""
    if g.n == 0:
        return ()
    for size in range(g.n, 1, -1):
        for combo in combinations(range(g.n), size):
            if all(g.has_edge(a, b) for a, b in combinations(combo, 2)):
                return combo
    return (0,) if g.n else ()


@dataclass
class Certificate:
    law: str
    graph_key: str            # canonical description of the graph the certificate is for
    kind: str                 # "upper" (a construction meets the bound) | "lower" (a witness forces it)
    witness: dict             # the coloring / clique realizing the bound
    checked: bool             # independent checker re-verified the witness
    certainty: str = "constructive_bounded"
    argument: str = ""        # the universal reason (recorded, NOT machine-verified)
    extra: dict = field(default_factory=dict)


def _coloring_is_proper(g: Graph, color: dict) -> bool:
    return all(color[u] != color[v] for (u, v) in g.edges)


def certify_chi_le_delta_plus_1(g: Graph) -> Certificate:
    """Construct a greedy coloring and certify χ(g) ≤ Δ(g)+1 by exhibiting it."""
    color = greedy_coloring(g)
    colors_used = len(set(color.values())) if g.n else 0
    ok = _coloring_is_proper(g, color) and (g.n == 0 or colors_used <= max_degree(g) + 1)
    return Certificate(
        "chromatic_number <= max_degree + 1", _key(g), "upper",
        {"coloring": color, "colors_used": colors_used},
        ok, "constructive_bounded",
        "greedy first-fit: ≤ Δ colored neighbors block ≤ Δ colors, so a (Δ+1)-palette always frees one",
    )


def certify_chi_le_n(g: Graph) -> Certificate:
    """Certify χ(g) ≤ n by the identity (all-distinct) coloring — trivially proper."""
    color = {v: v for v in range(g.n)}
    ok = _coloring_is_proper(g, color) and len(set(color.values())) <= num_vertices(g)
    return Certificate(
        "chromatic_number <= num_vertices", _key(g), "upper",
        {"coloring": color, "colors_used": g.n},
        bool(ok), "constructive_bounded",
        "assign every vertex a distinct color: no two vertices share a color, so no edge is monochromatic",
    )


def certify_omega_le_chi(g: Graph, *, solver_confirm: bool = True) -> Certificate:
    """Certify ω(g) ≤ χ(g) by exhibiting a maximum clique. Its vertices are pairwise adjacent, so any
    proper coloring gives them distinct colors ⇒ χ ≥ ω. Optionally DOUBLE-confirm via MathHead: the
    clique is not (ω−1)-colorable (`graph_coloring` → unsat)."""
    clique = max_clique(g)
    omega = len(clique)
    pairwise = all(g.has_edge(a, b) for a, b in combinations(clique, 2))
    ok = pairwise and omega == clique_number(g) and omega <= chromatic_number(g)
    extra = {}
    if solver_confirm and omega >= 2:
        # the induced clique K_ω cannot be (ω−1)-colored — an independent solver lower bound on χ
        edges = [[a + 1, b + 1] for a, b in combinations(range(omega), 2)]   # graph_coloring is 1-indexed
        extra["clique_not_(omega-1)_colorable"] = (
            route("graph_coloring", {"edges": edges, "colors": omega - 1, "n": omega}).status == "unsat"
        )
        ok = ok and extra["clique_not_(omega-1)_colorable"]
    return Certificate(
        "clique_number <= chromatic_number", _key(g), "lower",
        {"clique": list(clique), "clique_size": omega},
        bool(ok), "constructive_bounded",
        "a clique's pairwise-adjacent vertices need pairwise-distinct colors, so χ ≥ ω",
        extra,
    )


def _key(g: Graph) -> str:
    return f"n={g.n},E={sorted(g.edges)}"


def check_certificate(cert: Certificate, g: Graph) -> bool:
    """INDEPENDENT re-check of a certificate against g — re-validates the witness from scratch, not
    trusting how it was built (M-spirit). Returns True iff the witness genuinely realizes the bound."""
    w = cert.witness
    if cert.law == "chromatic_number <= max_degree + 1":
        color = w["coloring"]
        return (_coloring_is_proper(g, color)
                and (g.n == 0 or len(set(color.values())) <= max_degree(g) + 1))
    if cert.law == "chromatic_number <= num_vertices":
        color = w["coloring"]
        return _coloring_is_proper(g, color) and len(set(color.values())) <= num_vertices(g)
    if cert.law == "clique_number <= chromatic_number":
        clique = w["clique"]
        return (all(g.has_edge(a, b) for a, b in combinations(clique, 2))
                and len(clique) <= chromatic_number(g))
    return False


def certify_frontier_laws(graphs, *, solver_confirm: bool = True) -> list:
    """Produce constructive certificates for the surviving coloring laws over the sample and
    INDEPENDENTLY re-check each. Every returned certificate has `checked=True` iff its witness
    survived the independent re-check on its graph. `solver_confirm=False` skips the MathHead
    lower-bound double-check on ω≤χ (structural certificates only — fast path for the report)."""
    out = []
    for g in graphs:
        if g.n == 0:
            continue
        certs = [
            certify_chi_le_delta_plus_1(g),
            certify_chi_le_n(g),
            certify_omega_le_chi(g, solver_confirm=solver_confirm),
        ]
        for cert in certs:
            cert.checked = cert.checked and check_certificate(cert, g)   # independent gate
            out.append(cert)
    return out
