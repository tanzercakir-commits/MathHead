"""
mathhead.discovery.nonlinear_relations — non-linear (degree-2) relation discovery (roadmap O2, richer).

`relations.py` mines LINEAR laws via the integer null space of the affine feature matrix (it rediscovers
the Handshake Lemma). Many real identities are not linear, though — `num_edges = n(n−1)/2` on complete
graphs is quadratic. This module extends the exact null-space machinery to a DEGREE-2 polynomial feature
map: it augments the invariants with every pairwise product invᵢ·invⱼ (and squares invᵢ²) and mines the
null space of THAT matrix, so any relation `Σ cᵢⱼ·invᵢ·invⱼ + Σ cᵢ·invᵢ + c₀ = 0` holding across the
whole sample surfaces. On complete graphs it rediscovers `2·num_edges = num_vertices² − num_vertices`.

It reports only the genuinely NON-LINEAR laws (at least one product coefficient nonzero) — the linear
ones already belong to `relations.py`. Same exact rational arithmetic (no floats), same HONESTY: a
discovered law is `status="empirical"` — true over the SAMPLE, a conjecture, NOT a proven theorem.
Honest bound: degree 2 only; a cubic identity (e.g. num_triangles = C(n,3) on Kₙ) is beyond this map and
is deliberately NOT forced — it simply will not appear, rather than being mislabelled.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations_with_replacement
from typing import Iterable

import sympy

from .invariants import NUMERIC_INVARIANTS, evaluate


@dataclass
class NonlinearLaw:
    kind: str                        # "polynomial_equality" (degree 2)
    expression: str                  # human-readable, e.g. "2*num_edges = num_vertices^2 - num_vertices"
    coeffs: dict = field(default_factory=dict)   # {feature_name: int}, nonzero only
    const: int = 0
    degree: int = 2
    status: str = "empirical"        # holds over the sample; a conjecture, not a theorem
    holds_over: str = ""
    support: int = 0


def _primitive(ints: list) -> list:
    g = math.gcd(*[abs(x) for x in ints if x]) or 1
    ints = [x // g for x in ints]
    for x in ints:
        if x:
            if x < 0:
                ints = [-y for y in ints]
            break
    return ints


def _feature_names(names: list) -> list:
    """Linear terms followed by every product/square invᵢ·invⱼ (i ≤ j) — the degree-2 feature basis."""
    products = [f"{a}*{b}" if a != b else f"{a}^2" for a, b in combinations_with_replacement(names, 2)]
    return list(names) + products


def _feature_row(obj, names: list) -> list:
    vals = {nm: evaluate(obj, nm) for nm in names}
    linear = [vals[nm] for nm in names]
    products = [vals[a] * vals[b] for a, b in combinations_with_replacement(names, 2)]
    return linear + products + [1]                       # trailing 1 = affine term


def _is_product(feature: str) -> bool:
    return "*" in feature or "^" in feature


def _invariants_in(feature: str) -> set:
    """The invariant names appearing in a feature: 'a*b'→{a,b}, 'a^2'→{a}, 'a'→{a}."""
    return set(feature.replace("^2", "").split("*"))


def _reducible(coeffs: dict, const: int) -> bool:
    """True if the law factors as (a lower law)·(a common invariant): every term shares one invariant
    and there is no standalone constant. Such a law is just a known relation multiplied through — e.g.
    `2·num_edges·max_degree = sum_degrees·max_degree` is only Handshake × max_degree — so we drop it."""
    if const != 0 or not coeffs:
        return False
    sets = [_invariants_in(f) for f in coeffs]
    return bool(set.intersection(*sets))


def _render(coeffs: dict, const: int, feats: list) -> str:
    """Render `Σ cᵢ·featᵢ + const = 0` as a readable 'A = B' (positive terms left, negative right)."""
    left, right = [], []
    for nm in feats:
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


def _varying_names(objs: list, names: list) -> list:
    """Keep only invariants that take ≥2 distinct values over the sample. A constant invariant belongs
    to `discover_constants`; multiplying by it just spawns degenerate laws (X = X·const), so it is
    excluded from the degree-2 feature map."""
    return [nm for nm in names if len({evaluate(o, nm) for o in objs}) >= 2]


def discover_polynomial_laws(objects: Iterable, invariant_names=None, holds_over: str = "") -> list:
    """Exact degree-2 laws holding across ALL `objects`. Returns only the genuinely non-linear ones
    (≥1 product coefficient), each status='empirical'. Empty if none or no data."""
    names0 = list(invariant_names or NUMERIC_INVARIANTS)
    objs = list(objects)
    if not objs:
        return []
    names = _varying_names(objs, names0)                 # constants → discover_constants, not here
    feats = _feature_names(names)
    rows = [_feature_row(o, names) for o in objs]
    laws = []
    for v in sympy.Matrix(rows).nullspace():
        denoms = [sympy.Rational(x).q for x in v]
        scale = int(sympy.ilcm(*denoms)) if denoms else 1
        ints = _primitive([int(sympy.Rational(x) * scale) for x in v])
        coeffs = {feats[i]: ints[i] for i in range(len(feats)) if ints[i]}
        if not any(_is_product(nm) for nm in coeffs):    # skip purely-linear laws (relations.py owns them)
            continue
        if _reducible(coeffs, ints[-1]):                 # skip (lower law)·invariant, e.g. Handshake×deg
            continue
        laws.append(NonlinearLaw(
            kind="polynomial_equality",
            expression=_render(coeffs, ints[-1], feats),
            coeffs=coeffs, const=ints[-1], degree=2,
            status="empirical",
            holds_over=holds_over or f"{len(objs)} sampled objects",
            support=len(objs),
        ))
    laws.sort(key=lambda law: (len(law.coeffs), law.expression))   # deterministic
    return laws
