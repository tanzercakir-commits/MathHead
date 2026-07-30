"""
mathhead.discovery.conjecture_normalize — normalize + deduplicate conjectures across sources (P5).

The engine now mines conjectures from several miners — linear laws (`relations`), degree-2 laws
(`nonlinear_relations`), constant ratios (`pattern_mining`) — and they OVERLAP: the Handshake Lemma
surfaces as the linear law `2·num_edges = sum_degrees` AND as the ratio `sum_degrees/num_edges = 2`. Those
are the SAME equation in different clothes. P5 puts every linear-form conjecture into one CANONICAL key
so duplicates collapse and multi-source agreement becomes visible (corroboration), instead of the same
fact being reported three times.

The canonical form of a linear relation `Σ cᵢ·featᵢ + c₀ = 0`: divide the whole vector by the gcd of its
coefficients (primitive form), then fix the sign so the alphabetically-first feature has a positive
coefficient. `2·num_edges − sum_degrees = 0` and `sum_degrees − 2·num_edges = 0` (the ratio's equation)
reduce to the identical key. A ratio `A/B = p/q` becomes the relation `q·A − p·B = 0` before keying.

HONEST: this dedups by exact algebraic equality of the LINEAR NORMAL FORM only — it does not claim two
genuinely different conjectures are the same, and it carries every source forward as provenance so a
merge is always auditable. Non-linear laws with product terms are keyed on their feature names too, so a
quadratic and a linear law never collide. Deterministic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction


def _canonical(coeffs: dict, const: int):
    """Primitive, sign-fixed canonical key for `Σ cᵢ·featᵢ + const = 0` — hashable and deterministic."""
    items = {k: int(v) for k, v in coeffs.items() if v}
    values = list(items.values()) + ([int(const)] if const else [])
    g = math.gcd(*[abs(v) for v in values]) or 1
    items = {k: v // g for k, v in items.items()}
    c = int(const) // g
    first = min(items) if items else None                 # alphabetically-first feature
    if first is not None and items[first] < 0:            # fix sign so it is positive
        items = {k: -v for k, v in items.items()}
        c = -c
    return (tuple(sorted(items.items())), c)


def from_law(law) -> tuple:
    """(canonical_key, rendered) for a DiscoveredLaw / NonlinearLaw (has `.coeffs`, `.const`, `.expression`)."""
    return _canonical(dict(law.coeffs), law.const), law.expression


def from_ratio(rp) -> tuple:
    """(canonical_key, rendered) for a RatioPattern `A/B = p/q` → the relation `q·A − p·B = 0`."""
    r = Fraction(rp.ratio)
    coeffs = {rp.numerator: r.denominator, rp.denominator: -r.numerator}
    return _canonical(coeffs, 0), f"{rp.numerator}/{rp.denominator} = {rp.ratio}"


@dataclass
class NormalizedConjecture:
    key: tuple                          # the canonical algebraic key
    representative: str                 # one readable rendering
    sources: list = field(default_factory=list)   # [(source_kind, expression), ...]

    @property
    def corroboration(self) -> int:
        """How many DISTINCT source kinds independently found this conjecture."""
        return len({kind for kind, _ in self.sources})


def normalize_conjectures(*, linear=None, nonlinear=None, ratios=None) -> list:
    """Canonicalize conjectures from every miner, collapse duplicates, and keep provenance. Returns
    NormalizedConjecture objects sorted deterministically, most-corroborated first."""
    groups: dict = {}
    for kind, items, extract in (
        ("linear", linear or [], from_law),
        ("nonlinear", nonlinear or [], from_law),
        ("ratio", ratios or [], from_ratio),
    ):
        for it in items:
            key, rendered = extract(it)
            g = groups.setdefault(key, NormalizedConjecture(key, rendered))
            g.sources.append((kind, rendered))
    out = list(groups.values())
    out.sort(key=lambda nc: (-nc.corroboration, -len(nc.sources), nc.representative))
    return out
