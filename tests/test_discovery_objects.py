"""Discovery Track N0 — typed object model (Graph)."""
import pytest

from mathhead.discovery import Graph


def test_from_edges_normalizes_and_dedups():
    g = Graph.from_edges(3, [(1, 0), (0, 1), (2, 1)])   # unordered + duplicate
    assert g.edges == frozenset({(0, 1), (1, 2)})
    assert g.num_edges == 2


def test_degrees_and_neighbors():
    g = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3)])   # star K1,3
    assert g.degrees() == (3, 1, 1, 1)
    assert g.degree(0) == 3
    assert g.neighbors(0) == {1, 2, 3}
    assert g.has_edge(3, 0) and not g.has_edge(1, 2)


def test_isolated_vertices_are_kept():
    g = Graph(5, frozenset({(0, 1)}))    # 3 isolated vertices
    assert g.n == 5 and g.degrees() == (1, 1, 0, 0, 0)


def test_immutable_and_hashable():
    g1 = Graph.from_edges(3, [(0, 1), (1, 2)])
    g2 = Graph.from_edges(3, [(2, 1), (1, 0)])
    assert g1 == g2 and len({g1, g2}) == 1        # usable as set/dict keys


@pytest.mark.parametrize("n,edges", [
    (-1, []),                       # negative n
    (3, [(0, 3)]),                  # vertex out of range
    (3, [(1, 1)]),                  # loop (as raw tuple, i<j fails)
])
def test_construction_rejects_bad_input(n, edges):
    with pytest.raises(ValueError):
        Graph(n, frozenset(edges))


def test_from_edges_rejects_loops():
    with pytest.raises(ValueError):
        Graph.from_edges(3, [(1, 1)])
