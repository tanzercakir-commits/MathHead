"""
Graph theory (ROADMAP E3, pure stdlib) — shortest_path / connected_components /
minimum_spanning_tree / max_flow / maximum_matching / is_isomorphic.

Edges are [u,v] or [u,v,weight]. Best-case (known results) + worst-case (unreachable,
non-bipartite, bad source) + honesty + determinism.
"""
from mathhead.compute import (
    connected_components,
    is_isomorphic,
    max_flow,
    maximum_matching,
    minimum_spanning_tree,
    shortest_path,
)


# ---------------------------- shortest_path ------------------------------- #
def test_shortest_path_weighted():
    # 0→2(1)→1(2)→3(1) = 4 beats 0→1(4)
    r = shortest_path([[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 1], [2, 3, 5]], 0, 3, weighted=True)
    assert r.status == "ok"
    assert r.result["length"] == 4
    assert r.result["path"] == [0, 2, 1, 3]


def test_shortest_path_unweighted_bfs():
    assert shortest_path([[0, 1], [1, 2], [2, 3]], 0, 3).result["length"] == 3


def test_shortest_path_unreachable_is_honest():
    r = shortest_path([[0, 1], [2, 3]], 0, 3)
    assert r.status == "ok"
    assert r.result["path"] is None      # no fabricated path


def test_shortest_path_bad_source_rejected():
    assert shortest_path([[0, 1]], 9, 1).status == "error"


# ------------------------- connected_components --------------------------- #
def test_components_counts_isolated_node():
    # edges make {0,1} and {2,3}; node 4 is isolated → 3 components
    r = connected_components([[0, 1], [2, 3]], nodes=[0, 1, 2, 3, 4])
    assert r.result["count"] == 3
    assert r.result["is_connected"] is False


def test_components_connected():
    r = connected_components([[0, 1], [1, 2], [2, 0]])
    assert r.result["is_connected"] is True


# ------------------------ minimum_spanning_tree --------------------------- #
def test_mst_triangle():
    # triangle 0-1(1),1-2(2),0-2(3) → MST picks 1+2 = 3
    r = minimum_spanning_tree([[0, 1, 1], [1, 2, 2], [0, 2, 3]])
    assert r.result["total_weight"] == 3
    assert r.result["spans_all"] is True


def test_mst_disconnected_is_forest():
    r = minimum_spanning_tree([[0, 1, 1], [2, 3, 1]])
    assert r.result["spans_all"] is False


# -------------------------------- max_flow -------------------------------- #
def test_max_flow_value():
    r = max_flow([[0, 1, 3], [0, 2, 2], [1, 3, 2], [2, 3, 3], [1, 2, 1]], 0, 3)
    assert r.status == "ok"
    assert r.result["max_flow"] == 5
    assert r.result["min_cut"] == 5      # max-flow min-cut


def test_max_flow_source_equals_sink_rejected():
    assert max_flow([[0, 1, 1]], 0, 0).status == "error"


# ---------------------------- maximum_matching ---------------------------- #
def test_matching_bipartite():
    # left {0,1}; 0-2,0-3,1-2 → perfect matching of the left side (size 2)
    r = maximum_matching([[0, 2], [0, 3], [1, 2]], left=[0, 1])
    assert r.result["size"] == 2


def test_matching_non_bipartite_rejected():
    # an edge inside the left partition → not bipartite w.r.t. the given left set
    assert maximum_matching([[0, 1]], left=[0, 1]).status == "error"


# ----------------------------- is_isomorphic ------------------------------ #
def test_isomorphic_relabeled_triangle():
    r = is_isomorphic([[0, 1], [1, 2], [0, 2]], [["a", "b"], ["b", "c"], ["a", "c"]])
    assert r.result["isomorphic"] is True
    assert r.result["mapping"] is not None


def test_not_isomorphic_different_structure():
    # triangle vs path of 4 nodes
    r = is_isomorphic([[0, 1], [1, 2], [0, 2]], [[0, 1], [1, 2], [2, 3]])
    assert r.result["isomorphic"] is False


def test_isomorphic_degree_sequence_prunes():
    # star K1,3 vs path P4 — same nodes/edges, different degree sequence → not iso
    r = is_isomorphic([[0, 1], [0, 2], [0, 3]], [[0, 1], [1, 2], [2, 3]])
    assert r.result["isomorphic"] is False


# ------------------------------ determinism ------------------------------- #
def test_graph_determinism():
    for _ in range(5):
        assert shortest_path([[0, 1, 4], [0, 2, 1], [2, 1, 2], [1, 3, 1]], 0, 3,
                             weighted=True).result["length"] == 4
        assert max_flow([[0, 1, 3], [0, 2, 2], [1, 3, 2], [2, 3, 3], [1, 2, 1]], 0, 3).result["max_flow"] == 5
        assert minimum_spanning_tree([[0, 1, 1], [1, 2, 2], [0, 2, 3]]).result["total_weight"] == 3
