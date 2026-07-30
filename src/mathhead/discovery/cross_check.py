"""
mathhead.discovery.cross_check — multi-path invariant consistency check (roadmap O4).

The engine is a VERIFICATION engine, so it should verify its own measurements: compute the same
quantity by INDEPENDENT routes and confirm they agree. Two classic cases where several formulas must
coincide:

  * |E| four ways — direct edge count, the Handshake Lemma (Σ deg / 2), the spectral moment
    trace(A²)/2, and MathHead's own eigenvalue power-sum Σλ²/2.
  * #triangles three ways — the combinatorial count, trace(A³)/6, and MathHead's Σλ³/6.

If any route disagrees, that is a real bug caught. `all_consistent` runs the check over a whole
sample (including the adversarial stress set) — a self-test of the invariant + spectral code.
"""
from __future__ import annotations

from dataclasses import dataclass

from .invariants import (
    num_edges,
    num_triangles,
    spectral_moment_2,
    spectral_moment_3,
    sum_degrees,
)
from .spectral import eigen_power_sum


@dataclass
class CrossCheck:
    quantity: str
    methods: dict            # method name -> computed value
    agree: bool


def cross_check_num_edges(g, *, use_mathhead: bool = True) -> CrossCheck:
    methods = {
        "edge_count": num_edges(g),
        "handshake (Σdeg/2)": sum_degrees(g) // 2,
        "trace(A^2)/2": spectral_moment_2(g) // 2,
    }
    if use_mathhead and g.n:
        methods["MathHead Σλ^2/2"] = eigen_power_sum(g, 2) // 2
    return CrossCheck("num_edges", methods, len(set(methods.values())) == 1)


def cross_check_num_triangles(g, *, use_mathhead: bool = True) -> CrossCheck:
    methods = {
        "combinatorial": num_triangles(g),
        "trace(A^3)/6": spectral_moment_3(g) // 6,
    }
    if use_mathhead and g.n:
        methods["MathHead Σλ^3/6"] = eigen_power_sum(g, 3) // 6
    return CrossCheck("num_triangles", methods, len(set(methods.values())) == 1)


def cross_check(g, *, use_mathhead: bool = True) -> list:
    return [cross_check_num_edges(g, use_mathhead=use_mathhead),
            cross_check_num_triangles(g, use_mathhead=use_mathhead)]


def all_consistent(graphs, *, use_mathhead: bool = True) -> bool:
    """True iff every invariant agrees across all its independent computation routes, on every graph."""
    return all(c.agree for g in graphs for c in cross_check(g, use_mathhead=use_mathhead))


def disagreements(graphs, *, use_mathhead: bool = True) -> list:
    """The cross-checks that FAILED (empty ⇒ everything is consistent) — for diagnostics."""
    out = []
    for g in graphs:
        for c in cross_check(g, use_mathhead=use_mathhead):
            if not c.agree:
                out.append({"n": g.n, "edges": sorted(g.edges), "quantity": c.quantity,
                            "methods": c.methods})
    return out
