"""
mathhead.discovery.bijections — CONSTRUCTIVE bijections for the partition equidistributions
(discover → prove, in its honest bounded form; the partition analogue of graph_proofs.py).

An equidistribution ("two families are equinumerate") is best PROVEN by exhibiting a bijection between
them. This module builds the classical bijections explicitly and an independent checker verifies each
really IS a bijection on the sample — upgrading the findings from `structural_argument` (conclusion
checked) to `constructive_bijection` (an explicit map, verified injective + onto):

  * Euler's distinct = odd — GLAISHER's bijection: an odd part v of multiplicity m maps, via the
    binary digits of m, to the distinct parts v·2^b; its inverse splits each distinct part = odd·2^k
    back into 2^k copies of the odd. Sum-preserving, and a genuine bijection (unique odd·2^k form).
  * conjugation symmetry — transposing the Young diagram is the bijection {largest part = k} ↔
    {exactly k parts}, and an involution.

HONEST status. Verified on partitions of n ≤ a bound — `constructive_bijection` (an explicit witness
map, re-checked), strictly stronger than a conclusion count, but still bounded, NOT a universal proof
(that the bijection works for ALL n is the classical argument, recorded not machine-checked).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .partitions import (
    Partition,
    conjugate,
    generate_partitions,
    into_distinct_parts,
    into_odd_parts,
    largest_part,
    num_parts,
)


def glaisher_odd_to_distinct(p: Partition) -> Partition:
    """Odd-part partition → distinct-part partition: part v of multiplicity m → parts v·2^b for each
    set bit b of m. All outputs are distinct (unique odd·2^b form) and the sum is preserved."""
    out = []
    for v, m in Counter(p.parts).items():
        b = 0
        while m:
            if m & 1:
                out.append(v * (1 << b))
            m >>= 1
            b += 1
    return Partition(tuple(sorted(out, reverse=True)))


def glaisher_distinct_to_odd(p: Partition) -> Partition:
    """Inverse: distinct part = odd·2^k → 2^k copies of the odd value."""
    out = []
    for part in p.parts:
        v, k = part, 0
        while v % 2 == 0:
            v //= 2
            k += 1
        out.extend([v] * (1 << k))
    return Partition(tuple(sorted(out, reverse=True)))


@dataclass
class BijectionCertificate:
    theorem: str
    holds_upto: int
    verified: bool
    certainty: str = "constructive_bijection"
    detail: str = ""


def _is_bijection(items, forward, in_pred, out_pred) -> bool:
    """forward maps every item satisfying in_pred to a distinct item satisfying out_pred, and hits
    every out_pred item exactly once (a genuine bijection on the finite family)."""
    domain = [x for x in items if in_pred(x)]
    codomain = {x.parts for x in items if out_pred(x)}
    images = [forward(x).parts for x in domain]
    return (len(images) == len(set(images))           # injective
            and set(images) == codomain               # onto the codomain exactly
            and len(images) == len(codomain))


def certify_euler_bijection(max_n: int = 15) -> BijectionCertificate:
    """Verify Glaisher's map is a bijection {odd-part partitions} → {distinct-part partitions} for
    every n ≤ max_n, and that its stated inverse really inverts it."""
    ok = True
    for n in range(1, max_n + 1):
        parts = generate_partitions(n)
        if not _is_bijection(parts, glaisher_odd_to_distinct, into_odd_parts, into_distinct_parts):
            ok = False
            break
        # inverse round-trips every odd partition
        if any(glaisher_distinct_to_odd(glaisher_odd_to_distinct(p)).parts != p.parts
               for p in parts if into_odd_parts(p)):
            ok = False
            break
    return BijectionCertificate(
        "Euler: #{distinct-part} = #{odd-part} partitions of n", max_n, ok,
        detail="Glaisher's bijection (odd part v^m ↔ distinct parts v·2^b) verified injective + onto "
               "with a round-tripping inverse")


def certify_conjugation_bijection(max_n: int = 15) -> BijectionCertificate:
    """Verify conjugation is a bijection {largest part = k} ↔ {exactly k parts} for each k, and an
    involution, for every n ≤ max_n."""
    ok = True
    for n in range(1, max_n + 1):
        parts = generate_partitions(n)
        # conjugation swaps largest_part and num_parts, and is an involution
        if any(largest_part(conjugate(p)) != num_parts(p)
               or conjugate(conjugate(p)).parts != p.parts for p in parts):
            ok = False
            break
        # so it bijects each 'largest part = k' class onto the 'exactly k parts' class
        by_largest = Counter(largest_part(p) for p in parts)
        by_count = Counter(num_parts(p) for p in parts)
        if by_largest != by_count:
            ok = False
            break
    return BijectionCertificate(
        "conjugation: #{largest part=k} = #{exactly k parts}", max_n, ok,
        detail="transpose of the Young diagram, verified to swap the two statistics and self-invert")


def certify_partition_bijections(max_n: int = 15) -> list:
    """All constructive partition bijection certificates."""
    return [certify_euler_bijection(max_n), certify_conjugation_bijection(max_n)]
