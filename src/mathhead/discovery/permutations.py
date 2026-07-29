"""
mathhead.discovery.permutations — a THIRD object domain (after graphs and arithmetic), proving the
engine's object model generalizes (roadmap N/O/P over a new type).

Permutations of {0,…,n−1} get the same treatment as graphs: generate the whole ensemble, measure
exact invariants (inversions, descents, fixed points, cycles), and DISCOVER ensemble laws from the
data — then attach the structural argument that explains each, with its conclusion checked on the
sample:

  * |S_n| = n!                    — counting (pinned to OEIS A000142).
  * Σ_{π∈S_n} fix(π) = n!         — each of the n positions is fixed in (n−1)! permutations.
  * Σ_{π∈S_n} inv(π) = n!·C(n,2)/2 — each of the C(n,2) pairs is inverted in exactly half of S_n
                                     (π ↔ its reversal pairs inv(π) with C(n,2)−inv(π)).

Honest bound n ≤ 7 (7! = 5040); no silent cap. Deterministic (itertools order, memoized).
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations as _iter_perms
from math import comb, factorial

from .objects import MathObject

_MAX_N = 7
_CACHE: dict = {}


@dataclass(frozen=True)
class Permutation(MathObject):
    """A permutation of {0,…,n−1} as the image tuple: perm[i] is where i maps to."""
    perm: tuple

    @property
    def n(self) -> int:
        return len(self.perm)


def generate_permutations(n: int) -> list:
    """All n! permutations of {0,…,n−1}. Honest-bounded at n ≤ 7. Memoized, deterministic."""
    if n > _MAX_N:
        raise ValueError(f"generation is honestly bounded at n<= {_MAX_N} (n! blows up); asked n={n}")
    if n not in _CACHE:
        _CACHE[n] = [Permutation(p) for p in _iter_perms(range(n))]
    return list(_CACHE[n])


def count_permutations(n: int) -> int:
    return len(generate_permutations(n))


# ------------------------------ invariants -------------------------------- #
def inversions(p: Permutation) -> int:
    """# of pairs i<j with perm[i] > perm[j]."""
    a = p.perm
    return sum(1 for i in range(len(a)) for j in range(i + 1, len(a)) if a[i] > a[j])


def descents(p: Permutation) -> int:
    """# of positions i with perm[i] > perm[i+1]."""
    a = p.perm
    return sum(1 for i in range(len(a) - 1) if a[i] > a[i + 1])


def fixed_points(p: Permutation) -> int:
    return sum(1 for i, v in enumerate(p.perm) if i == v)


def num_cycles(p: Permutation) -> int:
    a, seen, c = p.perm, [False] * p.n, 0
    for i in range(p.n):
        if not seen[i]:
            c += 1
            j = i
            while not seen[j]:
                seen[j] = True
                j = a[j]
    return c


# ------------------------------ discovered laws --------------------------- #
@dataclass
class PermutationLaw:
    statement: str
    holds_upto: int
    verified: bool
    explanation: str
    closed_form: str


def _sum_over(fn, n: int) -> int:
    return sum(fn(p) for p in generate_permutations(n))


def discover_permutation_laws(max_n: int = 6) -> list:
    """Compute each ensemble sum over S_n for n≤max_n, compare to its closed form, and attach the
    structural explanation. `verified` iff the empirical sum matches the formula on every n."""
    ns = range(1, max_n + 1)
    laws = []

    laws.append(PermutationLaw(
        "|S_n| = n!", max_n,
        all(count_permutations(n) == factorial(n) for n in ns),
        "there are n choices for the first image, n−1 for the next, …, so n! permutations",
        "n!"))

    laws.append(PermutationLaw(
        "sum_(π in S_n) fix(π) = n!", max_n,
        all(_sum_over(fixed_points, n) == factorial(n) for n in ns),
        "each of the n positions is fixed in exactly (n−1)! permutations, so the total is n·(n−1)! = n!",
        "n!"))

    laws.append(PermutationLaw(
        "sum_(π in S_n) inv(π) = n! · C(n,2) / 2", max_n,
        all(_sum_over(inversions, n) == factorial(n) * comb(n, 2) // 2 for n in ns),
        "each of the C(n,2) pairs is inverted in exactly half of S_n (π ↔ its reversal pairs "
        "inv(π) with C(n,2)−inv(π)), so the total is C(n,2)·n!/2",
        "n! * n*(n-1) / 4"))

    return laws
