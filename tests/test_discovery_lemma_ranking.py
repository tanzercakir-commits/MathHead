"""Discovery T2 — rank candidate lemmas by importance × likelihood."""
from mathhead.discovery.knowledge_graph import KnowledgeGraph
from mathhead.discovery.lemma_ranking import next_lemma, rank_lemmas


def _graph():
    g = KnowledgeGraph()
    g.add_node("theorem", "6 | n**3 - n", id="thm:1")
    g.add_node("axiom", "RESIDUE(m=6)", id="ax:1")
    g.add_edge("thm:1", "depends_on", "ax:1")
    g.add_node("conjecture", "A: near+entangled", id="c:A", status="open")
    g.add_edge("c:A", "related_to", "thm:1")
    g.add_edge("c:A", "related_to", "ax:1")
    g.add_node("conjecture", "B: isolated", id="c:B", status="open")
    g.add_node("conjecture", "R: refuted", id="c:R", status="refuted")
    return g


def test_important_and_reachable_goal_ranks_highest():
    ranked = rank_lemmas(_graph())
    assert ranked[0].goal == "c:A"                     # entangled AND near proved ground
    assert ranked[0].priority == max(r.priority for r in ranked)


def test_isolated_goal_ranks_below_a_connected_one():
    ranked = {r.goal: r for r in rank_lemmas(_graph())}
    assert ranked["c:A"].priority > ranked["c:B"].priority


def test_resolved_goals_are_excluded():
    goals = {r.goal for r in rank_lemmas(_graph())}
    assert "c:R" not in goals and "thm:1" not in goals and "ax:1" not in goals


def test_components_are_exposed_and_bounded():
    for r in rank_lemmas(_graph()):
        assert 0.0 <= r.importance <= 1.0 and 0.0 <= r.likelihood <= 1.0
        assert 0.0 <= r.priority <= 1.0


def test_weights_are_adjustable():
    # pure-importance weighting ranks by entanglement alone
    ranked = rank_lemmas(_graph(), w_importance=1.0, w_likelihood=0.0)
    assert ranked[0].goal == "c:A" and ranked[0].priority == ranked[0].importance


def test_next_lemma_returns_top_and_none_when_empty():
    assert next_lemma(_graph()).goal == "c:A"
    assert next_lemma(KnowledgeGraph()) is None


def test_ranking_is_deterministic():
    a = rank_lemmas(_graph())
    b = rank_lemmas(_graph())
    assert [(r.goal, r.priority) for r in a] == [(r.goal, r.priority) for r in b]
