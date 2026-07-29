"""
mathhead.discovery.refute — counterexample-first refutation (roadmap Track Q0 + Q4-lite).

The engine's DEFAULT stance toward a conjecture is to try to KILL it, not to prove it. `refute`
scans generated objects in ascending size for a counterexample and returns either the MINIMAL
counterexample (smallest n, then fewest edges) or an honest `no_counterexample_within_bound`.

A survivor is NOT proven — it is `no_counterexample_within_bound`, exactly the epistemic status
MathHead already uses (a bounded honesty, never a fabricated "theorem"). Proving a survivor
(handing the algebraically-reducible ones to the MathHead judge) is the next track (R); the
purely combinatorial survivors may stay empirically-supported until a structural proof is added.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .generate import generate_graphs
from .invariants import invariant_vector


@dataclass
class RefutationResult:
    statement: str
    status: str                   # "refuted" | "no_counterexample_within_bound"
    checked: int                  # in-scope objects tested
    bound_n: int                  # searched up to this n
    counterexample: object = None
    detail: dict = field(default_factory=dict)


def refute(conjecture, max_n: int = 6) -> RefutationResult:
    """Counterexample-first search up to n = max_n. Returns the minimal counterexample if the
    conjecture is refuted, else an honest bounded 'no counterexample within bound'."""
    checked = 0
    for n in range(max_n + 1):
        counters = []
        for g in generate_graphs(n):
            if not conjecture.scope(g):
                continue
            checked += 1
            if not conjecture.claim(g):
                counters.append(g)
        if counters:
            best = min(counters, key=lambda g: (g.num_edges, sorted(g.edges)))
            iv = invariant_vector(best)
            detail = {name: iv.get(name) for name in conjecture.witnesses}
            detail.update({"n": best.n, "edges": sorted(best.edges)})
            return RefutationResult(conjecture.statement, "refuted", checked, max_n, best, detail)
    return RefutationResult(
        conjecture.statement, "no_counterexample_within_bound", checked, max_n)
