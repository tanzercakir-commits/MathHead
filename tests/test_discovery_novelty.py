"""Discovery Track W0 — 'interestingness': keep subclass-specific laws, drop restricted-universals."""
from mathhead.discovery import (
    generate_graphs,
    is_subclass_specific,
    is_tree,
    novel_subclass_laws,
    subclass_laws,
)


def _sample():
    return [g for n in range(6) for g in generate_graphs(n)]      # n<=5


def test_restricted_universal_is_not_specific():
    laws = {c.statement: c for c in subclass_laws(_sample(), is_tree, "trees")}
    handshake = laws["trees: 2*num_edges = sum_degrees"]          # holds on EVERY graph
    edge_count = laws["trees: num_vertices = num_edges + 1"]      # fails off trees
    assert not is_subclass_specific(handshake, _sample())
    assert is_subclass_specific(edge_count, _sample())


def test_novel_filter_keeps_real_tree_facts_only():
    kept = {c.statement for c in novel_subclass_laws(_sample(), is_tree, "trees")}
    assert "trees: num_vertices = num_edges + 1" in kept          # E = V - 1 (real tree fact)
    assert "trees: num_triangles = 0" in kept                     # trees are triangle-free
    assert "trees: 2*num_edges = sum_degrees" not in kept         # handshake restriction, dropped
