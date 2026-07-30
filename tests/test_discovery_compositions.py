"""Discovery — a SIXTH object domain: integer compositions + the cut-point bijection."""
from math import comb

from mathhead.discovery.compositions import (
    Composition,
    composition_to_cutset,
    compositions_into_k_parts,
    count_compositions,
    cutset_to_composition,
    discover_composition_laws,
    generate_compositions,
    num_parts,
)


def test_composition_count_is_two_to_the_n_minus_one():
    assert [count_compositions(n) for n in range(1, 9)] == [2 ** (n - 1) for n in range(1, 9)]


def test_every_generated_composition_sums_to_n_and_has_positive_parts():
    for n in range(1, 8):
        comps = generate_compositions(n)
        assert all(c.total == n and all(p >= 1 for p in c.parts) for c in comps)
        assert len({c.parts for c in comps}) == len(comps)          # all distinct (ordered)


def test_cut_point_bijection_round_trips_and_hits_all_subsets():
    for n in range(1, 9):
        comps = generate_compositions(n)
        images = {composition_to_cutset(c) for c in comps}
        assert len(images) == len(comps) == (1 << (n - 1))          # injective + onto all 2^(n-1) subsets
        assert all(cutset_to_composition(n, composition_to_cutset(c)).parts == c.parts for c in comps)


def test_specific_cutset_mapping():
    assert composition_to_cutset(Composition((1, 2, 1))) == frozenset({1, 3})
    assert cutset_to_composition(4, {1, 3}).parts == (1, 2, 1)
    assert composition_to_cutset(Composition((4,))) == frozenset()   # single part → no cuts


def test_compositions_into_k_parts_is_binomial():
    for n in range(1, 8):
        for k in range(1, n + 1):
            actual = sum(1 for c in generate_compositions(n) if num_parts(c) == k)
            assert actual == compositions_into_k_parts(n, k) == comb(n - 1, k - 1)


def test_discovered_laws_hold_with_honest_status():
    laws = discover_composition_laws(10)
    assert all(law.verified for law in laws)
    count_law = next(law for law in laws if "2^(n−1)" in law.statement)
    assert count_law.certainty == "constructive_bijection"          # proved by an explicit witness map


def test_generation_is_deterministic():
    assert [c.parts for c in generate_compositions(6)] == [c.parts for c in generate_compositions(6)]
