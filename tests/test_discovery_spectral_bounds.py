"""Discovery — real-valued spectral bounds, numerically checked (honest certainty)."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.spectral_bounds import run_spectral_bounds, spectral_radius


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_spectral_radius_of_complete_graph():
    assert abs(spectral_radius(generate_graphs(4)[-1]) - 3.0) < 1e-6   # λmax(K4) = n-1 = 3


def test_classic_sandwich_holds_and_false_variant_is_refuted():
    by_stmt = {f.statement: f for f in run_spectral_bounds(_graphs_up_to(4))}
    assert by_stmt["average_degree <= spectral_radius"].status == "no_counterexample_within_bound"
    assert by_stmt["spectral_radius <= max_degree"].status == "no_counterexample_within_bound"
    false = by_stmt["spectral_radius <= average_degree"]
    assert false.status == "refuted" and false.counterexample["n"] == 3   # a star/edge breaks it


def test_bounds_are_labeled_numerical_not_proven():
    for f in run_spectral_bounds(_graphs_up_to(3)):
        assert f.certainty == "numerical_check"        # honest: strong evidence, not a proof
