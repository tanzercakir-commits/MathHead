"""Discovery Track Q0 — counterexample-first refutation (the engine's default: kill it first)."""
from mathhead.discovery import (
    bound_conjectures,
    generate_graphs,
    is_tree,
    refute,
    subclass_laws,
)


def _graphs_up_to(n: int) -> list:
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def _bound(statement: str):
    return next(c for c in bound_conjectures(_graphs_up_to(5)) if c.statement == statement)


def test_false_bound_is_refuted_with_minimal_counterexample():
    # "num_triangles <= num_edges" looks true up to n=5, then dies at n=6.
    r = refute(_bound("num_triangles <= num_edges"), max_n=6)
    assert r.status == "refuted"
    assert r.detail["num_triangles"] == 16 and r.detail["num_edges"] == 14   # T > E
    assert r.detail["n"] == 6 and r.counterexample.num_edges == 14           # minimal by edges


def test_true_bound_survives_as_bounded_not_proven():
    r = refute(_bound("min_degree <= max_degree"), max_n=6)
    assert r.status == "no_counterexample_within_bound"      # honest: NOT "proved"
    assert r.counterexample is None and r.bound_n == 6


def test_true_subclass_theorem_survives():
    ev1 = next(c for c in subclass_laws(_graphs_up_to(6), is_tree, "trees")
               if c.statement == "trees: num_vertices = num_edges + 1")
    r = refute(ev1, max_n=6)
    assert r.status == "no_counterexample_within_bound"
    assert r.checked == 14                                    # all 14 trees on n<=6 checked


def test_full_loop_kills_exactly_the_artifact():
    # generate bounds from n<=5 data, then attack each up to n=6 — exactly one should die.
    bounds = bound_conjectures(_graphs_up_to(5))
    results = [refute(c, max_n=6) for c in bounds]
    refuted = [r for r in results if r.status == "refuted"]
    assert len(refuted) == 1
    assert refuted[0].statement == "num_triangles <= num_edges"
