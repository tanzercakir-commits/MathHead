"""
mathhead.discovery.set_partitions — a FIFTH object domain: partitions of a SET (Bell/Stirling).

Distinct in kind from integer partitions: here we partition the elements {0,…,n−1} into unlabeled
blocks. Same treatment — generate them all (via restricted-growth strings), measure exact invariants
(number of blocks, largest block, singletons), and discover ensemble facts with an independent
cross-check:

  * B(n) — the Bell numbers = number of set partitions (pinned to OEIS A000110).
  * B(n) = Σ_k S(n,k) — Bell is the row-sum of the Stirling numbers of the 2nd kind, where S(n,k) =
    #{partitions into exactly k blocks}. The block-count distribution is matched against S(n,k)
    computed INDEPENDENTLY from the Stirling recurrence S(n,k) = k·S(n−1,k) + S(n−1,k−1) (OEIS
    A008277) — a real cross-check, not a tautology.

Honest bound n ≤ 9 (B(9)=21147); no silent cap. Deterministic, memoized.
"""
from __future__ import annotations

from dataclasses import dataclass

from .objects import MathObject

_MAX_N = 9
_CACHE: dict = {}


@dataclass(frozen=True)
class SetPartition(MathObject):
    """A partition of {0,…,n−1} into blocks — a sorted tuple of sorted tuples (canonical)."""
    blocks: tuple
    n: int

    @property
    def num_blocks(self) -> int:
        return len(self.blocks)


def _rgs(n: int):
    """Restricted-growth strings of length n (in bijection with set partitions of [n])."""
    if n == 0:
        yield ()
        return
    a = [0] * n

    def gen(i: int, m: int):
        if i == n:
            yield tuple(a)
            return
        for v in range(m + 1):
            a[i] = v
            yield from gen(i + 1, max(m, v + 1))

    yield from gen(1, 1)


def _rgs_to_partition(a: tuple, n: int) -> SetPartition:
    groups: dict = {}
    for i, v in enumerate(a):
        groups.setdefault(v, []).append(i)
    blocks = tuple(sorted(tuple(sorted(b)) for b in groups.values()))
    return SetPartition(blocks, n)


def generate_set_partitions(n: int) -> list:
    """All set partitions of {0,…,n−1}. Honest-bounded at n ≤ 9. Memoized."""
    if n > _MAX_N:
        raise ValueError(f"generation is honestly bounded at n<= {_MAX_N} (Bell numbers grow); asked n={n}")
    if n not in _CACHE:
        _CACHE[n] = [_rgs_to_partition(a, n) for a in _rgs(n)] if n > 0 else [SetPartition((), 0)]
    return list(_CACHE[n])


def count_set_partitions(n: int) -> int:
    return len(generate_set_partitions(n))


# ------------------------------ invariants -------------------------------- #
def num_blocks(sp: SetPartition) -> int:
    return len(sp.blocks)


def largest_block(sp: SetPartition) -> int:
    return max((len(b) for b in sp.blocks), default=0)


def num_singletons(sp: SetPartition) -> int:
    return sum(1 for b in sp.blocks if len(b) == 1)


def stirling2(n: int, k: int) -> int:
    """Stirling number of the 2nd kind S(n,k) via the recurrence — computed INDEPENDENTLY of the
    ensemble, to cross-check the block-count distribution."""
    if k < 0 or k > n:
        return 0
    dp = [[0] * (k + 1) for _ in range(n + 1)]
    dp[0][0] = 1
    for i in range(1, n + 1):
        for j in range(1, k + 1):
            dp[i][j] = j * dp[i - 1][j] + dp[i - 1][j - 1]
    return dp[n][k]


# ------------------------------ discovered laws --------------------------- #
@dataclass
class SetPartitionLaw:
    statement: str
    holds_upto: int
    verified: bool
    explanation: str


def _block_count_distribution(n: int) -> dict:
    d: dict = {}
    for sp in generate_set_partitions(n):
        d[num_blocks(sp)] = d.get(num_blocks(sp), 0) + 1
    return d


def discover_set_partition_laws(max_n: int = 8) -> list:
    """Ensemble discoveries over set partitions of 1..max_n, each cross-checked independently."""
    ns = range(1, max_n + 1)
    laws = []

    laws.append(SetPartitionLaw(
        "B(n) = #{set partitions of [n]}  (Bell numbers)", max_n,
        all(count_set_partitions(n) == sum(stirling2(n, k) for k in range(n + 1)) for n in ns),
        "a set partition has some number k of blocks; summing S(n,k) over all k counts every "
        "partition exactly once, so B(n) = Σ_k S(n,k)."))

    laws.append(SetPartitionLaw(
        "#{set partitions of [n] with k blocks} = S(n,k)  (Stirling 2nd kind, A008277)", max_n,
        all(_block_count_distribution(n) == {k: stirling2(n, k)
                                             for k in range(1, n + 1) if stirling2(n, k)} for n in ns),
        "the block-count distribution obeys the Stirling recurrence "
        "S(n,k) = k·S(n−1,k) + S(n−1,k−1) (place element n in an existing block, k ways, or start a "
        "new one); computed independently and matched."))

    return laws
