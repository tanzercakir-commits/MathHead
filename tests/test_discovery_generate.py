"""Discovery Track N1 — canonical non-isomorphic generation, pinned to OEIS A000088."""
import pytest

from mathhead.discovery import canonical_graph, canonical_key, generate_graphs
from mathhead.discovery.generate import count_non_isomorphic

# OEIS A000088 — number of graphs on n unlabeled nodes.
A000088 = [1, 1, 2, 4, 11, 34, 156]


@pytest.mark.parametrize("n,expected", list(enumerate(A000088)))
def test_counts_match_oeis_a000088(n, expected):
    assert count_non_isomorphic(n) == expected


def test_representatives_are_pairwise_non_isomorphic():
    graphs = generate_graphs(5)
    keys = {canonical_key(g) for g in graphs}
    assert len(keys) == len(graphs) == 34        # all distinct iso classes


def test_representatives_are_in_canonical_form():
    for g in generate_graphs(5):
        assert canonical_graph(g) == g           # generator returns canonical reps


def test_generation_is_deterministic():
    assert generate_graphs(4) == generate_graphs(4)


def test_honest_bound_beyond_brute():
    with pytest.raises(ValueError):
        generate_graphs(8)                        # refused, not silently truncated
