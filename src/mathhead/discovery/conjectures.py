"""
mathhead.discovery.conjectures — conjecture generation (roadmap Track P0/P1).

Turns invariant data into *candidate laws to be attacked*. Two generators for now:

  * subclass_laws — restrict to a subclass (a predicate) and mine the exact linear laws that
    hold there (reuses O2). E.g. on trees it proposes "num_edges = num_vertices - 1" and
    "num_triangles = 0"; on forests "num_vertices = num_edges + num_components".
  * bound_conjectures — propose inequalities `A <= B` between numeric invariants that hold
    across the sample and are non-trivial (strict somewhere). Some are universally true; some
    are merely small-sample artifacts (e.g. "num_triangles <= num_edges" holds up to n=5 but
    fails at n=6) — surfacing those is exactly the point.

Every conjecture is `status="empirical"`: it held over the sample, it is NOT proven. The
counterexample-first track (`refute`) then tries to KILL each one before we believe it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .invariants import NUMERIC_INVARIANTS, evaluate
from .relations import discover_linear_laws


@dataclass
class Conjecture:
    """A candidate law. `scope` selects the objects it claims about; `claim` is the assertion on
    those objects. A graph refutes it iff it is in scope but the claim fails there."""

    kind: str                     # "subclass_law" | "inequality"
    statement: str                # human-readable
    scope: Callable               # g -> bool
    claim: Callable               # g -> bool (evaluated only where scope holds)
    witnesses: list = field(default_factory=list)   # invariant names to report at a counterexample
    status: str = "empirical"     # held over the sample; NOT proven
    holds_over: str = ""
    support: int = 0

    def is_counterexample(self, g) -> bool:
        return self.scope(g) and not self.claim(g)


def _always(g) -> bool:
    return True


def _law_claim(coeffs: dict, const: int) -> Callable:
    """Turn a linear law Σ cᵢ·invᵢ + const = 0 into a per-graph predicate (named closure)."""
    def claim(g) -> bool:
        return sum(c * evaluate(g, nm) for nm, c in coeffs.items()) + const == 0
    return claim


def _le_claim(a: str, b: str) -> Callable:
    """Predicate g -> (invariant a <= invariant b), binding a,b by value (named closure)."""
    def claim(g) -> bool:
        return evaluate(g, a) <= evaluate(g, b)
    return claim


def subclass_laws(objects, scope: Callable, label: str) -> list:
    """Mine exact linear laws on the subclass {g : scope(g)} and return them as Conjectures
    scoped to that subclass (to be refuted over a larger search)."""
    subset = [g for g in objects if scope(g)]
    out = []
    for law in discover_linear_laws(subset, holds_over=f"{label} (sample: {len(subset)})"):
        out.append(Conjecture(
            kind="subclass_law",
            statement=f"{label}: {law.expression}",
            scope=scope,
            claim=_law_claim(law.coeffs, law.const),
            witnesses=list(law.coeffs),
            holds_over=law.holds_over,
            support=len(subset),
        ))
    return out


def bound_conjectures(objects, invariant_names=None) -> list:
    """Propose non-trivial inequalities `A <= B` (numeric invariants) holding across the sample.
    Deterministic order."""
    names = list(invariant_names or NUMERIC_INVARIANTS)
    objs = list(objects)
    out = []
    for a in names:
        for b in names:
            if a == b:
                continue
            va = [evaluate(g, a) for g in objs]
            vb = [evaluate(g, b) for g in objs]
            if all(x <= y for x, y in zip(va, vb)) and any(x < y for x, y in zip(va, vb)):
                out.append(Conjecture(
                    kind="inequality",
                    statement=f"{a} <= {b}",
                    scope=_always,
                    claim=_le_claim(a, b),
                    witnesses=[a, b],
                    holds_over=f"{len(objs)} sampled objects",
                    support=len(objs),
                ))
    return out
