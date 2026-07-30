"""Discovery T0 — measure the gap between a goal and current knowledge."""
from types import SimpleNamespace

from mathhead.discovery.gap import frontier_gaps, measure_gap
from mathhead.discovery.knowledge_graph import KnowledgeGraph, from_report


def _graph():
    g = KnowledgeGraph()
    g.add_node("theorem", "6 | n**3 - n", id="thm:1")
    g.add_node("axiom", "RESIDUE(m=6)", id="ax:1")
    g.add_edge("thm:1", "depends_on", "ax:1")
    g.add_node("conjecture", "near claim", id="c:near", status="open")
    g.add_edge("c:near", "related_to", "thm:1")                 # 1 hop from proved ground
    g.add_node("conjecture", "big claim", id="c:dep", status="open")
    g.add_node("conjecture", "helper lemma", id="c:lem", status="open")
    g.add_edge("c:dep", "depends_on", "c:lem")                  # rests on an unproved lemma
    g.add_edge("c:dep", "related_to", "thm:1")
    g.add_node("conjecture", "isolated bound", id="c:iso", status="open")   # no path to proof
    g.add_node("conjecture", "false claim", id="c:ref", status="refuted")
    return g


def test_proved_and_refuted_goals_are_resolved_with_zero_gap():
    g = _graph()
    proved = measure_gap(g, "thm:1")
    assert proved.status == "proved" and proved.resolved and proved.gap_score == 0.0
    refuted = measure_gap(g, "c:ref")
    assert refuted.status == "refuted" and refuted.resolved and refuted.gap_score == 0.0


def test_open_goal_near_proof_has_smaller_gap_than_isolated_one():
    g = _graph()
    near = measure_gap(g, "c:near")
    iso = measure_gap(g, "c:iso")
    assert near.status == "open" and near.distance_to_known == 1
    assert iso.distance_to_known is None and iso.gap_score == 1.0
    assert near.gap_score < iso.gap_score


def test_open_dependency_widens_the_gap():
    g = _graph()
    near = measure_gap(g, "c:near")        # same distance (1), but no open dependency
    dep = measure_gap(g, "c:dep")          # distance 1 AND one unproved lemma to discharge
    assert dep.open_dependencies == ["c:lem"]
    assert dep.gap_score > near.gap_score


def test_unknown_goal_is_reported_honestly():
    g = _graph()
    m = measure_gap(g, "does-not-exist")
    assert m.status == "unknown" and not m.resolved and m.gap_score == 1.0


def test_frontier_ranks_smallest_gap_first_and_excludes_resolved():
    g = _graph()
    front = frontier_gaps(g)
    ids = [m.goal for m in front]
    assert "c:ref" not in ids and "thm:1" not in ids            # resolved nodes excluded
    assert ids[0] == "c:near"                                   # closest to reach ranked first
    scores = [m.gap_score for m in front]
    assert scores == sorted(scores)                            # ascending gap


def test_from_report_integration_measures_every_open_conjecture():
    report = SimpleNamespace(
        proved=[{"statement": "6 | n**3 - n", "axioms": ["RESIDUE(m=6)"], "kernel_verified": True}],
        empirical_laws=[{"statement": "sum_degrees = 2 * num_edges", "scope": "n<=5"}],
        refuted=[{"statement": "num_triangles <= num_edges is false-ish", "counterexample": "K4"}],
        open_bounded=[{"statement": "num_edges <= max_degree * num_vertices"}],
    )
    g = from_report(report)
    front = frontier_gaps(g)
    assert all(m.status == "open" for m in front)
    # deterministic
    assert [m.goal for m in front] == [m.goal for m in frontier_gaps(g)]


def test_measure_is_deterministic():
    g = _graph()
    assert measure_gap(g, "c:dep") == measure_gap(g, "c:dep")
