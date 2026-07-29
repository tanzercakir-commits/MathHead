"""Discovery Track O2 — automatic relation discovery (empirical linear laws + constants).

Headline: the engine must REDISCOVER the Handshake Lemma (sum_degrees = 2*num_edges) from the
generated graphs alone — an independent, checkable milestone for O2 (as A000088 was for N1).
"""
from mathhead.discovery import (
    discover_constants,
    discover_linear_laws,
    evaluate,
    generate_graphs,
)


def _graphs_up_to(n: int) -> list:
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_rediscovers_handshake_lemma():
    laws = discover_linear_laws(_graphs_up_to(5))
    assert len(laws) == 1                                  # exactly one universal law, no noise
    law = laws[0]
    assert law.kind == "linear_equality"
    assert law.coeffs == {"num_edges": 2, "sum_degrees": -1} and law.const == 0
    assert law.expression == "2*num_edges = sum_degrees"   # Handshake Lemma


def test_discovered_law_actually_holds_on_every_object():
    # tie the discovered law back to the data: 2*E - S = 0 for every sampled graph
    objs = _graphs_up_to(5)
    law = discover_linear_laws(objs)[0]
    for g in objs:
        total = sum(c * evaluate(g, nm) for nm, c in law.coeffs.items()) + law.const
        assert total == 0


def test_law_is_labeled_empirical_not_proven():
    law = discover_linear_laws(_graphs_up_to(5), holds_over="graphs n<=5")[0]
    assert law.status == "empirical"                       # a conjecture, NOT a theorem
    assert law.support == 53 and law.holds_over == "graphs n<=5"


def test_no_spurious_laws_with_more_data():
    # more data must not invent new "laws" — still just handshake
    laws = discover_linear_laws(_graphs_up_to(6))
    assert len(laws) == 1 and laws[0].coeffs == {"num_edges": 2, "sum_degrees": -1}


def test_discover_constants():
    cons = discover_constants(generate_graphs(4))          # all have exactly 4 vertices
    by_name = {c["invariant"]: c["value"] for c in cons}
    assert by_name.get("num_vertices") == 4
    assert "num_edges" not in by_name                      # edge count varies -> not constant


def test_deterministic_and_empty():
    a = discover_linear_laws(_graphs_up_to(4))
    b = discover_linear_laws(_graphs_up_to(4))
    assert [x.expression for x in a] == [x.expression for x in b]
    assert discover_linear_laws([]) == []
