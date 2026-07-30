"""Discovery N3 — generic object serialization, content-hash, reproducible ordering."""
import pytest

from mathhead.discovery import generate_graphs, generate_partitions, generate_permutations
from mathhead.discovery.serialize import (
    content_hash,
    deduplicate,
    reproducible_sort,
    serialize,
)
from mathhead.discovery.set_partitions import generate_set_partitions


def _one_of_each():
    return [generate_graphs(4)[5], generate_permutations(4)[7],
            generate_partitions(6)[3], generate_set_partitions(4)[2]]


def test_serialize_works_for_every_object_type():
    for obj in _one_of_each():
        s = serialize(obj)
        assert "kind" in s and "data" in s and s["kind"] == type(obj).__name__


def test_content_hash_is_deterministic_and_16_hex():
    for obj in _one_of_each():
        assert content_hash(obj) == content_hash(obj) and len(content_hash(obj)) == 16


def test_distinct_objects_hash_differently():
    hs = [content_hash(o) for o in _one_of_each()]
    assert len(set(hs)) == len(hs)                       # four different objects, four hashes


def test_reproducible_sort_is_order_independent():
    g = generate_graphs(5)
    assert reproducible_sort(g) == reproducible_sort(list(reversed(g)))


def test_deduplicate_drops_content_duplicates():
    g = generate_graphs(4)
    assert len(deduplicate(g + g)) == len(g)             # each graph appears once


def test_non_dataclass_is_rejected():
    with pytest.raises(TypeError):
        serialize(42)
