"""
mathhead.discovery.spectral_bounds — real-valued spectral inequalities, NUMERICALLY checked.

Spectral graph theory is full of bounds on the largest adjacency eigenvalue (the spectral
radius). These are real-valued, so — unlike the exact integer moment identities — they are checked
NUMERICALLY. We label them honestly: `certainty="numerical_check"` (strong evidence over the
sample, not an exact proof). The engine discovers the classic sandwich

        average_degree  ≤  spectral_radius  ≤  max_degree

and REFUTES the plausible-but-false `spectral_radius ≤ average_degree` (a star already breaks it).

The spectrum comes from MathHead (`eigenvalues`); the radius is its largest value, evaluated to
high precision and taken real (symmetric ⇒ real spectrum), so comparisons are robust.
"""
from __future__ import annotations

from dataclasses import dataclass

import sympy

from .invariants import max_degree, num_edges, num_vertices
from .spectral import spectrum

_TOL = 1e-9


def spectral_radius(g) -> float:
    """Largest adjacency eigenvalue (numeric, real)."""
    if g.n == 0:
        return 0.0
    return max(float(sympy.re(sympy.N(v, 30))) for v, _ in spectrum(g))


def average_degree(g) -> float:
    return 2 * num_edges(g) / num_vertices(g) if g.n else 0.0


def _max_degree_f(g) -> float:
    return float(max_degree(g))


# (statement, lhs, rhs) — the claim is lhs(g) <= rhs(g)
_BOUNDS = [
    ("average_degree <= spectral_radius", average_degree, spectral_radius),   # true
    ("spectral_radius <= max_degree", spectral_radius, _max_degree_f),        # true
    ("spectral_radius <= average_degree", spectral_radius, average_degree),   # FALSE (non-regular)
]


@dataclass
class SpectralBoundFinding:
    statement: str
    status: str                    # "no_counterexample_within_bound" | "refuted"
    certainty: str = "numerical_check"
    counterexample: dict = None


def run_spectral_bounds(graphs) -> list:
    """Check each candidate spectral bound counterexample-first over the graphs (ascending size for
    a minimal counterexample). Numerical — labeled as such."""
    out = []
    for statement, lhs, rhs in _BOUNDS:
        ce = None
        for g in graphs:
            if g.n == 0:
                continue
            if lhs(g) > rhs(g) + _TOL:
                ce = {"n": g.n, "edges": sorted(g.edges),
                      "lhs": round(lhs(g), 3), "rhs": round(rhs(g), 3)}
                break
        status = "refuted" if ce else "no_counterexample_within_bound"
        out.append(SpectralBoundFinding(statement, status, "numerical_check", ce))
    return out
