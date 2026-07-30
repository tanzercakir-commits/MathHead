"""
mathhead.discovery.compositions — a SIXTH object domain (integer compositions), proving the pipeline
generalizes yet again (roadmap N/O/P over another type, with a constructive-bijection gem).

A composition of n is an ORDERED tuple of positive integers summing to n — the ordered cousin of a
partition. Same treatment as the other five domains: generate them all, measure exact invariants, and
DISCOVER ensemble facts, the centrepiece being a clean CONSTRUCTIVE bijection:

  * number of compositions of n = 2^(n−1) for n ≥ 1 (OEIS A011782: 1,1,2,4,8,16,…);
  * compositions of n into exactly k parts = C(n−1, k−1) (stars and bars);
  * the PROOF of the count: the CUT-POINT bijection — a composition (a₁,…,a_k) of n ↔ the subset of
    partial sums {a₁, a₁+a₂, …} ⊆ {1,…,n−1} (the "cut points"). It is an explicit, invertible map onto
    ALL 2^(n−1) subsets, so it proves the count constructively — not by counting-and-hoping.

Honest bound n ≤ 15 (2^14 = 16384 compositions); no silent cap. The count law's status is
`constructive_bijection` (an explicit witness verified injective + onto on the sample), the same honesty
level as Euler/Glaisher in `bijections.py` — NOT a universal machine proof, but a real bijective witness.
Deterministic, memoized.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import comb

from .objects import MathObject

_MAX_N = 15
_CACHE: dict = {}


@dataclass(frozen=True)
class Composition(MathObject):
    """A composition of an integer as an ORDERED tuple of positive parts (sum = the integer)."""
    parts: tuple

    @property
    def total(self) -> int:
        return sum(self.parts)


def _gen(n: int):
    if n == 0:
        yield ()
        return
    for first in range(1, n + 1):
        for rest in _gen(n - first):
            yield (first, *rest)


def generate_compositions(n: int) -> list:
    """All compositions of n as ordered tuples. Honest-bounded at n ≤ 15 (2^(n−1) grows). Memoized."""
    if n > _MAX_N:
        raise ValueError(f"generation is honestly bounded at n<= {_MAX_N} (2^(n-1) grows); asked n={n}")
    if n not in _CACHE:
        _CACHE[n] = [Composition(c) for c in _gen(n)] if n > 0 else [Composition(())]
    return list(_CACHE[n])


def count_compositions(n: int) -> int:
    return len(generate_compositions(n))


def compositions_into_k_parts(n: int, k: int) -> int:
    """C(n−1, k−1) — the exact number of compositions of n into exactly k positive parts."""
    if n < 1 or k < 1 or k > n:
        return 0
    return comb(n - 1, k - 1)


# ------------------------------ invariants -------------------------------- #
def num_parts(c: Composition) -> int:
    return len(c.parts)


def largest_part(c: Composition) -> int:
    return max(c.parts) if c.parts else 0


def first_part(c: Composition) -> int:
    return c.parts[0] if c.parts else 0


# ------------------------------ the cut-point bijection ------------------- #
def composition_to_cutset(c: Composition) -> frozenset:
    """A composition (a₁,…,a_k) of n ↦ its set of partial sums {a₁, a₁+a₂, …, a₁+…+a_{k−1}} ⊆ {1,…,n−1}."""
    cuts, acc = [], 0
    for part in c.parts[:-1]:
        acc += part
        cuts.append(acc)
    return frozenset(cuts)


def cutset_to_composition(n: int, cutset) -> Composition:
    """The inverse: cut points {c₁<…<c_{k−1}} ⊆ {1,…,n−1} ↦ the composition (c₁, c₂−c₁, …, n−c_{k−1})."""
    prev, parts = 0, []
    for c in sorted(cutset):
        parts.append(c - prev)
        prev = c
    parts.append(n - prev)
    return Composition(tuple(parts))


# ------------------------------ discovered laws --------------------------- #
@dataclass
class CompositionLaw:
    statement: str
    holds_upto: int
    verified: bool
    certainty: str
    explanation: str


def discover_composition_laws(max_n: int = 12) -> list:
    """Ensemble discoveries over compositions of 1..max_n, each with its honest status + explanation."""
    ns = range(1, max_n + 1)
    laws = []

    # count = 2^(n−1), PROVED constructively by the cut-point bijection onto all subsets of {1..n−1}
    bij_ok = all(_cutpoint_bijection_holds(n) for n in ns)
    laws.append(CompositionLaw(
        "#{compositions of n} = 2^(n−1)  (OEIS A011782)", max_n, bij_ok, "constructive_bijection",
        "the cut-point map sends a composition to its set of partial sums ⊆ {1,…,n−1}; it is an explicit "
        "bijection onto ALL 2^(n−1) subsets (verified injective + onto with a round-tripping inverse)."))

    # compositions into k parts = C(n−1, k−1), stars and bars
    kparts_ok = all(
        sum(1 for c in generate_compositions(n) if num_parts(c) == k) == compositions_into_k_parts(n, k)
        for n in ns for k in range(1, n + 1))
    laws.append(CompositionLaw(
        "#{compositions of n into k parts} = C(n−1, k−1)  (stars and bars)", max_n, kparts_ok,
        "bounded_check",
        "choosing k−1 of the n−1 gaps between n units as cut points gives exactly the k-part "
        "compositions; counts confirmed for every (n,k) on the sample."))

    return laws


def _cutpoint_bijection_holds(n: int) -> bool:
    """The cut-point map is a bijection {compositions of n} ↔ {subsets of {1,…,n−1}} with a
    round-tripping inverse — the constructive proof that #compositions = 2^(n−1)."""
    comps = generate_compositions(n)
    images = [composition_to_cutset(c) for c in comps]
    all_subsets = 1 << (n - 1)                                     # 2^(n−1)
    if len(images) != len(set(images)) or len(set(images)) != all_subsets:
        return False                                              # not injective, or not onto all subsets
    return all(cutset_to_composition(n, composition_to_cutset(c)).parts == c.parts for c in comps)
