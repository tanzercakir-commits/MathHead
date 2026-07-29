"""Discovery — a FIFTH object domain (set partitions): Bell numbers, Stirling, B(n)=ΣS(n,k)."""
import pytest

from mathhead.discovery.set_partitions import (
    count_set_partitions,
    discover_set_partition_laws,
    generate_set_partitions,
    largest_block,
    num_blocks,
    num_singletons,
    stirling2,
)


def test_bell_numbers_match_oeis_a000110():
    assert [count_set_partitions(n) for n in range(9)] == [1, 1, 2, 5, 15, 52, 203, 877, 4140]


def test_generation_is_honestly_bounded():
    with pytest.raises(ValueError):
        generate_set_partitions(10)


def test_every_partition_covers_exactly_the_ground_set():
    for sp in generate_set_partitions(5):
        elems = [x for b in sp.blocks for x in b]
        assert sorted(elems) == [0, 1, 2, 3, 4]            # a partition: disjoint blocks covering [n]


def test_stirling_numbers_match_known_rows():
    assert [stirling2(4, k) for k in range(1, 5)] == [1, 7, 6, 1]
    assert [stirling2(5, k) for k in range(1, 6)] == [1, 15, 25, 10, 1]


def test_block_count_distribution_matches_stirling():
    for n in range(1, 8):
        dist: dict = {}
        for sp in generate_set_partitions(n):
            dist[num_blocks(sp)] = dist.get(num_blocks(sp), 0) + 1
        assert dist == {k: stirling2(n, k) for k in range(1, n + 1) if stirling2(n, k)}


def test_bell_is_the_row_sum_of_stirling():
    for n in range(1, 9):
        assert count_set_partitions(n) == sum(stirling2(n, k) for k in range(n + 1))


def test_invariants_on_a_known_partition():
    from mathhead.discovery.set_partitions import SetPartition
    sp = SetPartition(((0,), (1, 2), (3,)), 4)
    assert num_blocks(sp) == 3 and largest_block(sp) == 2 and num_singletons(sp) == 2


def test_discovered_laws_verify():
    laws = discover_set_partition_laws(8)
    assert len(laws) == 2 and all(L.verified and L.explanation for L in laws)
