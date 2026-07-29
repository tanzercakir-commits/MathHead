"""
mathhead.discovery.coloring — the graph domain's bridge to the SAT/UNSAT FRONTIER (roadmap O1
frontier-bridge). Chromatic number χ(g) is computed exactly by backtracking (an ordinary
invariant), then INDEPENDENTLY CONFIRMED through MathHead's `graph_coloring` frontier tool: a
proper χ-coloring exists (`sat`, and the witness is independently verified inside MathHead) AND no
(χ−1)-coloring exists (`unsat`, an impossibility proof). Two orthogonal authorities — our
backtracking and MathHead's Z3 reduction — agreeing is the "don't trust one prover" check applied
to a genuinely NP-hard invariant.

We also mine coloring INEQUALITIES over the sample — the classic sandwich  ω ≤ χ ≤ Δ+1  — and
REFUTE the plausible-but-false  χ ≤ Δ. Refute-first reports the MINIMAL witness: not the classic
triangle (χ=3 vs Δ=2) but the single vertex (χ=1 vs Δ=0), which breaks it even more minimally.

MathHead's graph_coloring is 1-indexed, so our 0-indexed vertices are shifted +1; `n` is passed
explicitly so isolated (edge-free) vertices are still counted.
"""
from __future__ import annotations

from dataclasses import dataclass

from mathhead.router import route

from .invariants import chromatic_number, clique_number, max_degree, num_vertices
from .objects import Graph


def _shifted_edges(g: Graph) -> list:
    """MathHead's graph_coloring is 1-indexed; shift 0-indexed vertices +1."""
    return [[u + 1, v + 1] for (u, v) in g.edges]


def _colorable(g: Graph, k: int) -> str:
    """MathHead frontier verdict for 'can g be k-colored?': 'sat' | 'unsat' | other."""
    return route("graph_coloring", {"edges": _shifted_edges(g), "colors": k, "n": g.n}).status


@dataclass
class ColoringVerification:
    n: int
    chi: int
    confirmed: bool             # χ colors suffice AND χ−1 do not — both authorities agree
    certainty: str              # "solver_verified" | "trivial"


def verify_chromatic_number(g: Graph) -> ColoringVerification:
    """Confirm the backtracking χ(g) against MathHead's frontier: `sat` at χ, `unsat` at χ−1.
    For χ ≤ 1 (empty graph or no edges) the claim is trivial and MathHead is not invoked."""
    chi = chromatic_number(g)
    if chi <= 1:
        return ColoringVerification(g.n, chi, True, "trivial")
    sat_at_chi = _colorable(g, chi) == "sat"
    unsat_below = _colorable(g, chi - 1) == "unsat"
    return ColoringVerification(g.n, chi, sat_at_chi and unsat_below, "solver_verified")


def _chi(g: Graph) -> int:
    return chromatic_number(g)


def _omega(g: Graph) -> int:
    return clique_number(g)


def _delta(g: Graph) -> int:
    return max_degree(g)


def _delta_plus_1(g: Graph) -> int:
    return max_degree(g) + 1


def _n_verts(g: Graph) -> int:
    return num_vertices(g)


# (statement, lhs, rhs) — the claim is lhs(g) <= rhs(g)
_BOUNDS = [
    ("clique_number <= chromatic_number", _omega, _chi),          # true  (ω ≤ χ)
    ("chromatic_number <= max_degree + 1", _chi, _delta_plus_1),  # true  (greedy / Brooks)
    ("chromatic_number <= num_vertices", _chi, _n_verts),         # true
    ("chromatic_number <= max_degree", _chi, _delta),             # FALSE (min witness K1: χ=1, Δ=0)
]


@dataclass
class ColoringBoundFinding:
    statement: str
    status: str                    # "no_counterexample_within_bound" | "refuted"
    certainty: str = "bounded_check"
    counterexample: dict = None


def coloring_bounds(graphs) -> list:
    """Check each candidate coloring inequality counterexample-first (ascending graph size ⇒ a
    MINIMAL counterexample). χ, ω, Δ are EXACT integer invariants, so a survivor is exactly checked
    over the whole finite sample — `bounded_check` (exact within the bound), not a numerical guess."""
    out = []
    for statement, lhs, rhs in _BOUNDS:
        ce = None
        for g in graphs:
            if g.n == 0:
                continue
            if lhs(g) > rhs(g):
                ce = {"n": g.n, "edges": sorted(g.edges), "lhs": lhs(g), "rhs": rhs(g)}
                break
        status = "refuted" if ce else "no_counterexample_within_bound"
        out.append(ColoringBoundFinding(statement, status, "bounded_check", ce))
    return out
