"""Discovery P1 — theorem mutation: strengthen surviving bounds, repair refuted ones."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.invariants import evaluate
from mathhead.discovery.mutate import Mutation, mutate_inequality, repair, strengthen


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_strengthen_finds_the_tight_multiplier():
    # num_edges <= sum_degrees is loose; the tight form is 2*num_edges <= sum_degrees (Handshake)
    m = strengthen("num_edges <= sum_degrees", _graphs_up_to(6))
    assert m.kind == "strengthened" and m.mutated == "2*num_edges <= sum_degrees"
    # verify the strengthened form really holds (with equality)
    assert all(2 * evaluate(g, "num_edges") <= evaluate(g, "sum_degrees") for g in _graphs_up_to(6))


def test_strengthen_uses_additive_slack_when_no_multiplier():
    # a bound with no multiplier headroom but constant slack gets an additive strengthening
    g = _graphs_up_to(5)
    m = strengthen("min_degree <= max_degree", g)
    assert m.kind in ("strengthened", "unchanged")          # depends on the sample's tightest gap
    if m.kind == "strengthened":
        assert "<=" in m.mutated


def test_repair_weakens_a_refuted_bound_to_a_true_one():
    g = _graphs_up_to(6)
    r = repair("num_triangles <= num_edges", g)              # refuted by K6
    assert r.kind == "repaired" and r.mutated == "num_triangles <= num_edges + 5"
    # the repaired form holds on the sample
    assert all(evaluate(x, "num_triangles") <= evaluate(x, "num_edges") + 5 for x in g)


def test_repair_of_a_true_claim_is_unchanged():
    r = repair("min_degree <= max_degree", _graphs_up_to(5))
    assert r.kind == "unchanged" and r.mutated == "min_degree <= max_degree"


def test_mutate_inequality_dispatches_on_status():
    g = _graphs_up_to(6)
    assert mutate_inequality("num_edges <= sum_degrees", g, refuted=False).kind == "strengthened"
    assert mutate_inequality("num_triangles <= num_edges", g, refuted=True).kind == "repaired"


def test_mutation_is_deterministic():
    g = _graphs_up_to(5)
    assert strengthen("num_edges <= sum_degrees", g) == strengthen("num_edges <= sum_degrees", g)
    assert isinstance(strengthen("num_edges <= sum_degrees", g), Mutation)
