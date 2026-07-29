"""Discovery Track O0/O1 — property & invariant evaluation."""
import pytest

from mathhead.discovery import Graph, evaluate, invariant_vector
from mathhead.discovery.invariants import (
    INVARIANTS,
    degree_sequence,
    is_connected,
    num_components,
    num_edges,
    num_triangles,
)


def _complete(n: int) -> Graph:
    return Graph.from_edges(n, [(i, j) for i in range(n) for j in range(i + 1, n)])


def test_complete_graph_triangles():
    assert num_triangles(_complete(3)) == 1        # K3
    assert num_triangles(_complete(4)) == 4        # C(4,3)
    assert num_triangles(_complete(5)) == 10       # C(5,3)


def test_path_has_no_triangles_but_is_connected():
    p4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3)])
    assert num_triangles(p4) == 0
    assert is_connected(p4) and num_components(p4) == 1


def test_disconnected_components():
    g = Graph.from_edges(4, [(0, 1), (2, 3)])      # two disjoint edges
    assert num_components(g) == 2 and not is_connected(g)


def test_empty_graph_edges_case():
    e = Graph(0, frozenset())
    assert num_components(e) == 0 and not is_connected(e)
    iso = Graph(3, frozenset())                    # 3 isolated vertices
    assert num_components(iso) == 3 and num_edges(iso) == 0


def test_degree_sequence_is_iso_invariant():
    c5a = Graph.from_edges(5, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)])
    c5b = Graph.from_edges(5, [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)])   # relabeled 5-cycle
    assert degree_sequence(c5a) == degree_sequence(c5b) == (2, 2, 2, 2, 2)


def test_registry_and_vector():
    v = invariant_vector(_complete(3))
    assert set(v) == set(INVARIANTS)
    assert v["num_edges"] == 3 and v["is_connected"] is True


def test_unknown_invariant_raises():
    with pytest.raises(KeyError):
        evaluate(_complete(3), "no_such_invariant")
