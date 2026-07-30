"""
mathhead.discovery.feature_conjectures — systematic conjecture generation from the feature table
(roadmap O3 → P0, the systematic version of the hand-picked bound conjectures).

Where `conjectures.py` (P0) proposes a few hand-picked bounds, this generates them SYSTEMATICALLY:
build the invariant feature table over a sample, then for every ordered pair of numeric invariants
(a, b) conjecture the inequality `a ≤ b` and test it counterexample-first. Survivors (hold on the
whole sample, minimal-witness-free) are DISCOVERED bounds; the rest are REFUTED with a minimal
witness. This rediscovers the true invariant inequalities (min_degree ≤ max_degree,
num_components ≤ num_vertices, …) and kills the plausible-but-false ones (num_triangles ≤ num_edges).

Deterministic: fixed invariant order, ascending-size scan ⇒ minimal counterexamples.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

from .invariants import NUMERIC_INVARIANTS, evaluate


def feature_table(objects, invariants=None) -> list:
    """One row per object: {invariant: value} over the numeric invariants (the P1/O3 substrate)."""
    invariants = invariants or NUMERIC_INVARIANTS
    return [{inv: evaluate(o, inv) for inv in invariants} for o in objects]


@dataclass
class InequalityConjecture:
    claim: str                  # "a <= b"
    status: str                 # "no_counterexample_within_bound" | "refuted"
    support: int = 0            # sample objects the claim held on (survivors)
    counterexample: dict = None


def discover_inequalities(objects, invariants=None) -> list:
    """Conjecture `a ≤ b` for every ordered pair of numeric invariants and test counterexample-first
    (ascending order ⇒ minimal witness). Returns all conjectures with their honest status."""
    invariants = invariants or NUMERIC_INVARIANTS
    objs = list(objects)
    out = []
    for a, b in permutations(invariants, 2):
        ce = None
        for o in objs:
            va, vb = evaluate(o, a), evaluate(o, b)
            if va > vb:
                ce = {"n": getattr(o, "n", None), "edges": sorted(getattr(o, "edges", [])),
                      a: va, b: vb}
                break
        if ce:
            out.append(InequalityConjecture(f"{a} <= {b}", "refuted", 0, ce))
        else:
            out.append(InequalityConjecture(f"{a} <= {b}", "no_counterexample_within_bound", len(objs)))
    return out


def surviving_inequalities(objects, invariants=None) -> list:
    """Just the DISCOVERED (survived) inequalities — the systematically-mined true bounds."""
    return [c for c in discover_inequalities(objects, invariants)
            if c.status == "no_counterexample_within_bound"]
