"""Discovery Track N2 — canonical labeling / isomorphism elimination."""
from mathhead.discovery import Graph, canonical_graph, canonical_key, is_isomorphic


def test_isomorphic_relabeling_detected():
    t1 = Graph.from_edges(3, [(0, 1), (1, 2), (0, 2)])
    t2 = Graph.from_edges(3, [(0, 2), (1, 2), (0, 1)])   # same triangle, relabeled
    assert is_isomorphic(t1, t2)
    assert canonical_key(t1) == canonical_key(t2)


def test_non_iso_via_degree_sequence():
    p4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3)])   # path, degrees 1,2,2,1
    star = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3)])  # star, degrees 3,1,1,1
    assert not is_isomorphic(p4, star)


def test_non_iso_with_SAME_degree_sequence():
    # The hard case the algorithm must handle: both 2-regular on 6 vertices, same degree
    # sequence, yet NOT isomorphic (C6 is connected; 2*C3 is not). Degree sequence alone
    # cannot tell them apart — the canonical labeling must.
    c6 = Graph.from_edges(6, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)])
    two_tri = Graph.from_edges(6, [(0, 1), (1, 2), (2, 0), (3, 4), (4, 5), (5, 3)])
    assert not is_isomorphic(c6, two_tri)
    assert canonical_key(c6) != canonical_key(two_tri)


def test_canonical_key_is_deterministic():
    g = Graph.from_edges(5, [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (1, 3)])
    assert canonical_key(g) == canonical_key(g)


def test_canonical_graph_is_idempotent_and_iso():
    g = Graph.from_edges(5, [(0, 2), (2, 4), (4, 1), (1, 3), (3, 0)])   # a 5-cycle, relabeled
    c = canonical_graph(g)
    assert is_isomorphic(g, c)
    assert canonical_key(c) == canonical_key(g)
    assert canonical_graph(c) == c            # already canonical -> fixed point


def test_cheap_rejects():
    a = Graph.from_edges(4, [(0, 1)])
    b = Graph.from_edges(5, [(0, 1)])         # different n
    c = Graph.from_edges(4, [(0, 1), (2, 3)])  # different edge count
    assert not is_isomorphic(a, b)
    assert not is_isomorphic(a, c)


def test_empty_graph():
    e = Graph(0, frozenset())
    assert canonical_key(e) == (0, 0)
