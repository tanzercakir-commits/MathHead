"""Discovery P1 — systematic conjecture generation from the invariant feature table."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.feature_conjectures import (
    discover_inequalities,
    feature_table,
    surviving_inequalities,
)


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_feature_table_has_one_row_per_object():
    g = _graphs_up_to(4)
    ft = feature_table(g)
    assert len(ft) == len(g) and all("num_edges" in row for row in ft)


def test_systematic_generation_covers_all_ordered_pairs():
    conjectures = discover_inequalities(_graphs_up_to(5))
    # 7 numeric invariants ⇒ 7·6 = 42 ordered pairs
    assert len(conjectures) == 42
    assert all(c.status in ("no_counterexample_within_bound", "refuted") for c in conjectures)


def test_true_bounds_survive():
    by = {c.claim: c for c in discover_inequalities(_graphs_up_to(6))}
    assert by["min_degree <= max_degree"].status == "no_counterexample_within_bound"
    assert by["num_components <= num_vertices"].status == "no_counterexample_within_bound"


def test_false_bound_is_refuted_with_a_minimal_witness():
    by = {c.claim: c for c in discover_inequalities(_graphs_up_to(6))}
    tri = by["num_triangles <= num_edges"]                  # K6: 20 triangles > 15 edges
    assert tri.status == "refuted" and tri.counterexample["n"] == 6


def test_surviving_helper_returns_only_survivors():
    surv = surviving_inequalities(_graphs_up_to(5))
    assert surv and all(c.status == "no_counterexample_within_bound" for c in surv)


def test_generation_is_deterministic():
    a = [(c.claim, c.status) for c in discover_inequalities(_graphs_up_to(4))]
    b = [(c.claim, c.status) for c in discover_inequalities(_graphs_up_to(4))]
    assert a == b
