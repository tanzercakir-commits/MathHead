"""
mathhead.discovery.relations — automatic relation / invariant discovery (roadmap Track O2).

Given a set of generated objects and their numeric invariants, find relationships that hold
across the WHOLE sample:

  * exact linear laws — via the integer null space of the affine feature matrix. Each basis
    vector is a law `Σ cᵢ·invᵢ + c₀ = 0` satisfied by every sampled object. (This is how the
    engine rediscovers, e.g., the Handshake Lemma `sum_degrees = 2·num_edges` from data.)
  * constant invariants — invariants that take a single value across the sample.

HONESTY (the project's core contract): a discovered law is `status="empirical"` — it holds
over the SAMPLE, it is NOT proven for all objects. It is a *conjecture*, ready to be attacked
by the counterexample-first track (Q) and, if it survives, proved via the judge (R). We never
label an empirical relation as a theorem.

Exact arithmetic throughout (sympy rationals) — no floating point, so a reported law holds
exactly on the sample, not approximately.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable

import sympy

from .invariants import NUMERIC_INVARIANTS, evaluate


@dataclass
class DiscoveredLaw:
    """An exact linear relation Σ cᵢ·invᵢ + const = 0 that held across the sample.

    `status` is always 'empirical': true over the sample, NOT proven universally.
    """

    kind: str                       # "linear_equality"
    expression: str                 # human-readable, e.g. "2*num_edges = sum_degrees"
    coeffs: dict = field(default_factory=dict)   # {invariant_name: int}, nonzero only
    const: int = 0
    status: str = "empirical"       # holds over the sample; a conjecture, not a theorem
    holds_over: str = ""
    support: int = 0                # number of objects it held over


def _primitive(ints: list) -> list:
    """Normalize an integer vector: divide by gcd, make the first nonzero entry positive."""
    g = math.gcd(*[abs(x) for x in ints if x]) or 1
    ints = [x // g for x in ints]
    for x in ints:
        if x:
            if x < 0:
                ints = [-y for y in ints]
            break
    return ints


def _render(coeffs: dict, const: int, names: list) -> str:
    """Render `Σ cᵢ·invᵢ + const = 0` as a readable 'A = B' (positives left, negatives right)."""
    left, right = [], []
    for nm in names:
        c = coeffs.get(nm, 0)
        if c == 0:
            continue
        term = nm if abs(c) == 1 else f"{abs(c)}*{nm}"
        (left if c > 0 else right).append(term)
    if const > 0:
        left.append(str(const))
    elif const < 0:
        right.append(str(abs(const)))
    return f"{' + '.join(left) or '0'} = {' + '.join(right) or '0'}"


def discover_linear_laws(objects: Iterable, invariant_names=None, holds_over: str = "") -> list:
    """Exact linear laws holding across ALL `objects` (the integer null space of the affine
    feature matrix). Returns DiscoveredLaw objects (status='empirical'); empty if none/no data.
    """
    names = list(invariant_names or NUMERIC_INVARIANTS)
    objs = list(objects)
    if not objs:
        return []
    rows = [[evaluate(o, nm) for nm in names] + [1] for o in objs]   # trailing 1 = affine term
    laws = []
    for v in sympy.Matrix(rows).nullspace():
        denoms = [sympy.Rational(x).q for x in v]
        scale = int(sympy.ilcm(*denoms)) if denoms else 1
        ints = _primitive([int(sympy.Rational(x) * scale) for x in v])
        coeffs = {nm: ints[i] for i, nm in enumerate(names) if ints[i]}
        const = ints[-1]
        laws.append(DiscoveredLaw(
            kind="linear_equality",
            expression=_render(coeffs, const, names),
            coeffs=coeffs, const=const,
            status="empirical",
            holds_over=holds_over or f"{len(objs)} sampled objects",
            support=len(objs),
        ))
    laws.sort(key=lambda law: (len(law.coeffs), law.expression))   # deterministic
    return laws


def discover_constants(objects: Iterable, invariant_names=None) -> list:
    """Invariants that are constant across the sample: [{invariant, value, support}, ...]."""
    names = list(invariant_names or NUMERIC_INVARIANTS)
    objs = list(objects)
    out = []
    for nm in names:
        vals = {evaluate(o, nm) for o in objs}
        if len(vals) == 1:
            out.append({"invariant": nm, "value": next(iter(vals)), "support": len(objs)})
    return out
