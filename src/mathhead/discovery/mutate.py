"""
mathhead.discovery.mutate — theorem mutation (roadmap P1): weaken hypotheses, strengthen conclusions.

A discovered fact is rarely the sharpest true statement. Mutation takes a bound `a ≤ b` over a sample
and searches nearby stronger/weaker forms:

  * STRENGTHEN a survivor — push the additive slack: the largest k with `a + k ≤ b` still holding, and
    the largest multiplier m with `m·a ≤ b`. The tightest surviving form is the sharper theorem.
  * REPAIR a refuted claim — the smallest k with `a ≤ b + k` holding (the weakened statement that IS
    true within the sample), i.e. an honest fix for a false conjecture.

Every mutation is tested counterexample-first on the same sample, so the result is as honest as the
original bound: "no counterexample within bound", with a witness when one exists. This turns a flat
list of discovered inequalities into their sharpened / repaired forms.
"""
from __future__ import annotations

from dataclasses import dataclass

from .invariants import evaluate


@dataclass
class Mutation:
    original: str
    mutated: str
    kind: str                   # "strengthened" | "repaired" | "unchanged"
    holds: bool


def _pair(claim: str):
    a, b = claim.split(" <= ")
    return a.strip(), b.strip()


def _additive_slack(objects, a: str, b: str) -> int:
    """Largest k ≥ 0 with a(o) + k ≤ b(o) for all o (how much the LHS can grow and still fit)."""
    return min((evaluate(o, b) - evaluate(o, a) for o in objects), default=0)


def _max_multiplier(objects, a: str, b: str, cap: int = 8) -> int:
    """Largest integer m (1..cap) with m·a(o) ≤ b(o) for all o (0 if even m=1 fails)."""
    best = 0
    for m in range(1, cap + 1):
        if all(m * evaluate(o, a) <= evaluate(o, b) for o in objects):
            best = m
        else:
            break
    return best


def _repair_offset(objects, a: str, b: str) -> int:
    """Smallest k ≥ 0 with a(o) ≤ b(o) + k for all o — the additive weakening that makes it true."""
    return max((evaluate(o, a) - evaluate(o, b) for o in objects), default=0)


def strengthen(claim: str, objects) -> Mutation:
    """Sharpen a surviving `a ≤ b`: prefer a multiplier bound (m·a ≤ b, m ≥ 2) if one holds, else push
    the additive slack (a + k ≤ b). Returns the tightest surviving form."""
    a, b = _pair(claim)
    objs = list(objects)
    m = _max_multiplier(objs, a, b)
    if m >= 2:
        return Mutation(claim, f"{m}*{a} <= {b}", "strengthened", True)
    k = _additive_slack(objs, a, b)
    if k >= 1:
        return Mutation(claim, f"{a} + {k} <= {b}", "strengthened", True)
    return Mutation(claim, claim, "unchanged", True)


def repair(claim: str, objects) -> Mutation:
    """Weaken a refuted `a ≤ b` to the smallest true `a ≤ b + k` within the sample."""
    a, b = _pair(claim)
    k = _repair_offset(list(objects), a, b)
    if k == 0:
        return Mutation(claim, claim, "unchanged", True)     # already held (nothing to repair)
    return Mutation(claim, f"{a} <= {b} + {k}", "repaired", True)


def mutate_inequality(claim: str, objects, refuted: bool = False) -> Mutation:
    """Strengthen a survivor or repair a refuted claim — the right mutation for its status."""
    return repair(claim, objects) if refuted else strengthen(claim, objects)
