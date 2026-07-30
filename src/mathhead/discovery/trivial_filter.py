"""
mathhead.discovery.trivial_filter — extend the junk-theorem filter to the new patterns (roadmap W0).

W0 (`novelty.py`) already drops restricted-universal subclass laws — one guard against "a machine can emit
a million true-but-trivial statements". The newer miners (`pattern_mining`) need the same hygiene:

  * a MONOTONIC trend on a CONSTANT invariant is junk — a constant sequence is trivially both
    non-decreasing and non-increasing, so reporting `num_components non_decreasing with num_vertices`
    (num_components ≡ 1 on complete graphs) is a fake "trend"; drop it.
  * a CONSTANT RATIO between two invariants that are BOTH constant over the sample is accidental, not a
    structural law (their quotient is fixed only because neither varies); drop it. A ratio where at least
    one side varies — like `sum_degrees/num_edges = 2` (Handshake) — is a genuine relation and is kept.

These are exact, sample-grounded filters (an invariant is "constant" iff it takes one value over the
sample), and they only ever REMOVE trivial output — never invent or relabel. Deterministic.
"""
from __future__ import annotations

from .invariants import evaluate
from .pattern_mining import constant_ratios, monotonic_trends


def _is_constant(objects: list, invariant: str) -> bool:
    return len({evaluate(o, invariant) for o in objects}) <= 1


def nontrivial_trends(objects, key: str, invariant_names=None) -> list:
    """Monotonic trends with the fake ones removed: a trend on an invariant that is CONSTANT over the
    sample is not a trend at all."""
    objs = list(objects)
    return [t for t in monotonic_trends(objs, key, invariant_names)
            if not _is_constant(objs, t.invariant)]


def nontrivial_ratios(objects, invariant_names=None) -> list:
    """Constant ratios with the accidental ones removed: a ratio A/B where BOTH A and B are constant over
    the sample is not a structural law (fixed only because neither side varies)."""
    objs = list(objects)
    return [p for p in constant_ratios(objs, invariant_names)
            if not (_is_constant(objs, p.numerator) and _is_constant(objs, p.denominator))]
