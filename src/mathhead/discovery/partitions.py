"""
mathhead.discovery.partitions — a FOURTH object domain (integer partitions), more number-theoretic
than the graph/permutation ensembles (roadmap N/O/P over another type).

Partitions of n get the same treatment: generate them all, measure exact invariants (number of parts,
largest part, distinctness/parity), and DISCOVER ensemble facts — including a genuine gem:

  * p(n) — the partition numbers (pinned to OEIS A000041).
  * Euler's theorem — #{partitions of n into DISTINCT parts} = #{partitions into ODD parts}, for every
    n (rediscovered by counting BOTH and finding them equal; pinned to OEIS A000009).
  * conjugation symmetry — #{partitions of n with largest part k} = #{partitions with exactly k parts}
    (the conjugate/transpose bijection).

Honest bound n ≤ 30 (p(30)=5604); no silent cap. Deterministic, memoized.
"""
from __future__ import annotations

from dataclasses import dataclass

from .objects import MathObject

_MAX_N = 30
_CACHE: dict = {}


@dataclass(frozen=True)
class Partition(MathObject):
    """A partition of an integer as a non-increasing tuple of positive parts (sum = the integer)."""
    parts: tuple

    @property
    def total(self) -> int:
        return sum(self.parts)


def _gen(n: int, max_part: int):
    if n == 0:
        yield ()
        return
    for first in range(min(n, max_part), 0, -1):
        for rest in _gen(n - first, first):
            yield (first, *rest)


def generate_partitions(n: int) -> list:
    """All partitions of n as non-increasing tuples. Honest-bounded at n ≤ 30. Memoized."""
    if n > _MAX_N:
        raise ValueError(f"generation is honestly bounded at n<= {_MAX_N} (p(n) grows); asked n={n}")
    if n not in _CACHE:
        _CACHE[n] = [Partition(p) for p in _gen(n, n)] if n > 0 else [Partition(())]
    return list(_CACHE[n])


def count_partitions(n: int) -> int:
    return len(generate_partitions(n))


# ------------------------------ invariants -------------------------------- #
def num_parts(p: Partition) -> int:
    return len(p.parts)


def largest_part(p: Partition) -> int:
    return p.parts[0] if p.parts else 0


def num_distinct_parts(p: Partition) -> int:
    return len(set(p.parts))


def into_distinct_parts(p: Partition) -> bool:
    return len(p.parts) == len(set(p.parts))


def into_odd_parts(p: Partition) -> bool:
    return all(part % 2 == 1 for part in p.parts)


def conjugate(p: Partition) -> Partition:
    """The conjugate (transpose) partition: column lengths of the Young diagram."""
    if not p.parts:
        return Partition(())
    return Partition(tuple(sum(1 for part in p.parts if part >= i) for i in range(1, p.parts[0] + 1)))


# ------------------------------ discovered laws --------------------------- #
@dataclass
class PartitionLaw:
    statement: str
    holds_upto: int
    verified: bool
    explanation: str


def discover_partition_laws(max_n: int = 15) -> list:
    """Ensemble discoveries over partitions of 1..max_n, each with its structural explanation."""
    ns = range(1, max_n + 1)
    laws = []

    laws.append(PartitionLaw(
        "#{partitions of n into DISTINCT parts} = #{partitions into ODD parts}  (Euler)", max_n,
        all(sum(into_distinct_parts(p) for p in generate_partitions(n))
            == sum(into_odd_parts(p) for p in generate_partitions(n)) for n in ns),
        "Euler's theorem: the generating functions ∏(1+x^k) and ∏1/(1−x^{2k−1}) are equal (a bijective "
        "proof exists). The engine confirms the two counts agree for every n."))

    laws.append(PartitionLaw(
        "#{partitions of n, largest part = k} = #{partitions of n, exactly k parts}  (conjugation)",
        max_n,
        all(_by_largest(n) == _by_numparts(n) for n in ns),
        "conjugating a partition (transpose its Young diagram) swaps 'largest part' with 'number of "
        "parts', giving a bijection between the two families."))

    return laws


def _by_largest(n: int) -> dict:
    d: dict = {}
    for p in generate_partitions(n):
        d[largest_part(p)] = d.get(largest_part(p), 0) + 1
    return d


def _by_numparts(n: int) -> dict:
    d: dict = {}
    for p in generate_partitions(n):
        d[num_parts(p)] = d.get(num_parts(p), 0) + 1
    return d
