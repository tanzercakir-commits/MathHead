"""Discovery Track P0 — conjecture generation (subclass laws + inequality bounds)."""
from mathhead.discovery import (
    bound_conjectures,
    generate_graphs,
    is_forest,
    is_tree,
    subclass_laws,
)


def _graphs_up_to(n: int) -> list:
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_subclass_laws_on_trees_rediscover_classic_theorems():
    stmts = {c.statement for c in subclass_laws(_graphs_up_to(6), is_tree, "trees")}
    assert "trees: num_triangles = 0" in stmts               # trees are triangle-free
    assert "trees: num_vertices = num_edges + 1" in stmts    # E = V - 1


def test_forests_get_forest_formula_not_the_tree_formula():
    stmts = {c.statement for c in subclass_laws(_graphs_up_to(6), is_forest, "forests")}
    assert "forests: num_vertices = num_edges + num_components" in stmts   # V = E + C
    assert "forests: num_vertices = num_edges + 1" not in stmts            # forests may disconnect


def test_bound_conjectures_include_true_and_artifact_bounds():
    stmts = {c.statement for c in bound_conjectures(_graphs_up_to(5))}
    assert "min_degree <= max_degree" in stmts        # universally true
    assert "num_triangles <= num_edges" in stmts      # holds up to n=5, but a small-sample artifact


def test_conjecture_scope_and_claim():
    conj = next(c for c in bound_conjectures(_graphs_up_to(5))
                if c.statement == "num_triangles <= num_edges")
    k6 = generate_graphs(6)   # contains graphs that violate it
    violators = [g for g in k6 if conj.is_counterexample(g)]
    assert violators                                   # some n=6 graph refutes it
    assert conj.status == "empirical"                  # never labeled proven
