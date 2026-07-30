"""
mathhead.discovery.pattern_mining — ratio & monotonicity pattern mining (roadmap P0 breadth).

P0 is "experimental pattern mining: equality / inequality / MONOTONICITY / periodicity / asymptotic /
forbidden-structure". `relations.py` covers equalities (linear) and `nonlinear_relations.py` degree-2;
`feature_conjectures.py` covers inequalities. This module adds two more P0 pattern kinds, exactly and
honestly:

  * CONSTANT RATIOS — invariant pairs (A, B) with A/B equal to one exact rational across the whole
    sample (B ≠ 0 everywhere). This rediscovers the Handshake Lemma in ratio form: sum_degrees / num_edges
    = 2 on every graph with an edge.
  * MONOTONIC TRENDS — over objects sorted by a chosen key invariant, which invariants move strictly
    monotonically (increasing / decreasing) or weakly (non-decreasing / non-increasing) with it. On the
    complete-graph family ordered by num_vertices, num_edges / sum_degrees / num_triangles all strictly
    increase.

Same honesty contract as the rest of O2/P0: every pattern is `status="empirical"` — it holds over the
SAMPLE, it is a conjecture, NOT a theorem. Exact arithmetic (`fractions.Fraction`) — a reported ratio is
exact, not a float approximation. Monotonicity is a sample statement over the given ordering, not a proof
of a universal trend.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import permutations
from typing import Iterable

from .invariants import NUMERIC_INVARIANTS, evaluate


@dataclass
class RatioPattern:
    numerator: str
    denominator: str
    ratio: Fraction
    status: str = "empirical"
    support: int = 0


@dataclass
class MonotonicTrend:
    invariant: str
    key: str
    direction: str              # "strictly_increasing" | "strictly_decreasing" | "non_decreasing" | "non_increasing"
    status: str = "empirical"
    support: int = 0


def constant_ratios(objects: Iterable, invariant_names=None) -> list:
    """Ordered invariant pairs (A, B) whose ratio A/B is a single exact rational across the sample,
    with B ≠ 0 on every object. Rediscovers sum_degrees / num_edges = 2 (Handshake, ratio form)."""
    names = list(invariant_names or NUMERIC_INVARIANTS)
    objs = list(objects)
    if not objs:
        return []
    out = []
    for a, b in permutations(names, 2):
        bvals = [evaluate(o, b) for o in objs]
        if any(v == 0 for v in bvals):
            continue                                     # ratio undefined somewhere → skip the pair
        ratios = {Fraction(evaluate(o, a), evaluate(o, b)) for o in objs}
        if len(ratios) == 1:
            r = next(iter(ratios))
            if r > 1:                                    # keep the ≥1 direction only (drops the inverse
                out.append(RatioPattern(a, b, r, support=len(objs)))   # duplicate and the trivial r=1)
    out.sort(key=lambda p: (p.numerator, p.denominator))
    return out


def monotonic_trends(objects: Iterable, key: str, invariant_names=None) -> list:
    """Over `objects` sorted by the `key` invariant, the invariants that move monotonically with it.
    Strict monotonicity is reported preferentially; weak (non-strict) otherwise. Ties in the key are
    kept in the sample's order (a weak trend then, honestly, cannot be strict)."""
    names = [nm for nm in (invariant_names or NUMERIC_INVARIANTS) if nm != key]
    objs = sorted(objects, key=lambda o: evaluate(o, key))
    if len(objs) < 2:
        return []
    trends = []
    for nm in names:
        seq = [evaluate(o, nm) for o in objs]
        d = _classify(seq)
        if d:
            trends.append(MonotonicTrend(nm, key, d, support=len(objs)))
    trends.sort(key=lambda t: (t.invariant,))
    return trends


def _classify(seq: list):
    diffs = [b - a for a, b in zip(seq, seq[1:])]
    if all(d > 0 for d in diffs):
        return "strictly_increasing"
    if all(d < 0 for d in diffs):
        return "strictly_decreasing"
    if all(d >= 0 for d in diffs):
        return "non_decreasing"
    if all(d <= 0 for d in diffs):
        return "non_increasing"
    return None
