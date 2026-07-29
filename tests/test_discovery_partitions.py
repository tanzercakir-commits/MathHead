"""Discovery — a FOURTH object domain (integer partitions): counts, Euler's theorem, conjugation."""
import pytest

from mathhead.discovery.partitions import (
    Partition,
    conjugate,
    count_partitions,
    discover_partition_laws,
    generate_partitions,
    into_distinct_parts,
    into_odd_parts,
    largest_part,
    num_parts,
)


def test_partition_counts_match_oeis_a000041():
    assert [count_partitions(n) for n in range(11)] == [1, 1, 2, 3, 5, 7, 11, 15, 22, 30, 42]


def test_generation_is_honestly_bounded():
    with pytest.raises(ValueError):
        generate_partitions(31)


def test_every_generated_partition_sums_to_n_and_is_non_increasing():
    for p in generate_partitions(7):
        assert p.total == 7
        assert list(p.parts) == sorted(p.parts, reverse=True)


def test_euler_distinct_equals_odd_counts_oeis_a000009():
    counts = [sum(into_distinct_parts(p) for p in generate_partitions(n)) for n in range(1, 9)]
    assert counts == [1, 1, 2, 2, 3, 4, 5, 6]                # OEIS A000009
    for n in range(1, 12):
        d = sum(into_distinct_parts(p) for p in generate_partitions(n))
        o = sum(into_odd_parts(p) for p in generate_partitions(n))
        assert d == o                                        # Euler's theorem


def test_conjugation_is_an_involution_and_swaps_largest_with_count():
    p = Partition((4, 2, 1))
    assert conjugate(p).parts == (3, 2, 1, 1)
    for q in generate_partitions(6):
        c = conjugate(q)
        assert conjugate(c).parts == q.parts                 # involution
        assert largest_part(c) == num_parts(q)               # transpose swaps the two
        assert c.total == q.total


def test_discovered_partition_laws_verify():
    laws = discover_partition_laws(15)
    assert len(laws) == 2 and all(L.verified and L.explanation for L in laws)
    assert any("Euler" in L.statement for L in laws)
    assert any("conjugation" in L.statement for L in laws)
