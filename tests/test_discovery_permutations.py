"""Discovery — a THIRD object domain (permutations): generation, invariants, discovered laws."""
import pytest
from math import comb, factorial

from mathhead.discovery.permutations import (
    Permutation,
    count_permutations,
    descents,
    discover_permutation_laws,
    fixed_points,
    generate_permutations,
    inversions,
    num_cycles,
)


def test_count_matches_factorial_oeis_a000142():
    assert [count_permutations(n) for n in range(7)] == [factorial(n) for n in range(7)]


def test_generation_is_honestly_bounded():
    with pytest.raises(ValueError):
        generate_permutations(8)                       # 8! is past the honest bound


def test_invariants_on_known_permutations():
    identity = Permutation((0, 1, 2, 3))
    assert inversions(identity) == 0 and descents(identity) == 0
    assert fixed_points(identity) == 4 and num_cycles(identity) == 4
    reverse = Permutation((3, 2, 1, 0))
    assert inversions(reverse) == comb(4, 2)           # every pair inverted
    assert fixed_points(reverse) == 0                  # a fixed point needs perm[i]==i
    two_cycles = Permutation((1, 0, 3, 2))             # (0 1)(2 3)
    assert num_cycles(two_cycles) == 2 and fixed_points(two_cycles) == 0


def test_discovered_laws_all_verify_on_the_sample():
    laws = discover_permutation_laws(6)
    assert {L.statement for L in laws} == {
        "|S_n| = n!",
        "sum_(π in S_n) fix(π) = n!",
        "sum_(π in S_n) inv(π) = n! · C(n,2) / 2",
    }
    assert all(L.verified for L in laws)
    assert all(L.explanation for L in laws)            # every law carries its structural reason


def test_inversion_sum_matches_closed_form_directly():
    # Σ inv over S_3 = 0+1+1+2+2+3 = 9 = 3! · C(3,2)/2
    assert sum(inversions(p) for p in generate_permutations(3)) == factorial(3) * comb(3, 2) // 2 == 9


def test_fixed_point_sum_is_n_factorial():
    for n in range(1, 7):
        assert sum(fixed_points(p) for p in generate_permutations(n)) == factorial(n)


def test_generation_is_deterministic():
    assert [p.perm for p in generate_permutations(4)] == [p.perm for p in generate_permutations(4)]
