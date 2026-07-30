"""Discovery U0 — a verified registry of representation transforms."""
from mathhead.discovery.generate import generate_graphs
from mathhead.discovery.objects import Graph
from mathhead.discovery.representations import (
    adjacency_to_graph,
    all_faithful,
    divisibility_to_residue_table,
    graph_to_adjacency,
    graph_to_degree_sequence,
    verify_representations,
)


def test_every_registered_bridge_is_faithful():
    bridges = verify_representations()
    assert {b.name for b in bridges} == {
        "graph↔adjacency-matrix", "composition↔cut-point-subset",
        "graph→degree-sequence", "divisibility→residue-table"}
    assert all(b.faithful for b in bridges) and all_faithful()


def test_graph_matrix_round_trip_over_the_whole_sample():
    for n in range(1, 6):
        for g in generate_graphs(n):
            assert adjacency_to_graph(graph_to_adjacency(g)) == g   # decode∘encode = identity


def test_adjacency_matrix_is_symmetric_and_zero_one():
    g = Graph(3, frozenset({(0, 1), (1, 2)}))
    mat = graph_to_adjacency(g)
    assert all(mat[i][j] in (0, 1) for i in range(3) for j in range(3))
    assert all(mat[i][j] == mat[j][i] for i in range(3) for j in range(3))   # symmetric
    assert all(mat[i][i] == 0 for i in range(3))                             # no loops


def test_residue_table_decision_agrees_with_divisibility_truth():
    assert all(x == 0 for x in divisibility_to_residue_table(6, (0, -1, 0, 1)))       # 6 | n³−n
    assert any(x != 0 for x in divisibility_to_residue_table(5, (0, -1, 0, 1)))       # 5 ∤ n³−n
    assert all(x == 0 for x in divisibility_to_residue_table(30, (0, -1, 0, 0, 0, 1)))  # 30 | n⁵−n


def test_degree_sequence_preserves_handshake():
    for n in range(1, 6):
        for g in generate_graphs(n):
            assert sum(graph_to_degree_sequence(g)) == 2 * g.num_edges


def test_bridge_kinds_are_labelled():
    kinds = {b.name: b.kind for b in verify_representations()}
    assert kinds["graph↔adjacency-matrix"] == "round_trip"
    assert kinds["graph→degree-sequence"] == "invariant_preserving"
    assert kinds["divisibility→residue-table"] == "decision"


def test_verification_is_deterministic():
    a = verify_representations()
    b = verify_representations()
    assert [(x.name, x.faithful) for x in a] == [(x.name, x.faithful) for x in b]
