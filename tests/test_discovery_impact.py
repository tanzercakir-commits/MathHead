"""Discovery Track X3 — structural impact analysis over the knowledge graph."""
from mathhead.discovery import run_report
from mathhead.discovery.impact import (
    generalization_impact,
    impact_summary,
    load_bearing_axioms,
    most_connected,
    open_frontier,
)
from mathhead.discovery.knowledge_graph import from_report


def _graph():
    return from_report(run_report(max_n=5))


def test_load_bearing_axioms_are_ranked_by_support():
    lb = load_bearing_axioms(_graph())
    assert lb and lb[0]["supports"] >= lb[-1]["supports"]     # descending
    # RESIDUE(m=2) supports the most proofs (n(n+1), n²−n, n³−n, n⁵−n, n⁷−n, …)
    top = {a["axiom"]: a["supports"] for a in lb}
    assert top.get("RESIDUE(m=2)", 0) >= 4
    assert "CRT" in top


def test_most_connected_returns_hubs_by_degree():
    mc = most_connected(_graph(), k=3)
    assert len(mc) == 3
    assert mc[0]["degree"] >= mc[1]["degree"] >= mc[2]["degree"]


def test_open_frontier_only_lists_open_conjectures():
    g = _graph()
    of = open_frontier(g)
    open_stmts = {n.statement for n in g.by_kind("conjecture") if n.attrs.get("status") == "open"}
    assert of and all(o["statement"] in open_stmts for o in of)
    assert of[0]["entanglement"] >= of[-1]["entanglement"]     # descending


def test_impact_summary_has_all_sections_and_is_deterministic():
    g = _graph()
    a, b = impact_summary(g), impact_summary(g)
    assert set(a) == {"load_bearing_axioms", "most_connected", "open_frontier", "generalizations"}
    assert a == b                                             # exact, deterministic


# --- v4F6: what happens to the instances if the general law fell? (exact, from the graph) -------

def test_generalization_impact_answers_if_the_law_fell():
    gi = generalization_impact(_graph())
    assert len(gi) == 1                                       # the one P2-fed parametric law
    law = gi[0]
    assert "k!" in law["law"] and law["instances"] == 5
    # every instance carries its OWN kernel proof, so the honest consequence is explanation-loss only
    assert law["independently_proved_instances"] == 5
    assert "keep their own kernel proofs" in law["if_the_law_fell"]


def test_generalization_impact_flags_instances_without_own_support():
    from mathhead.discovery.knowledge_graph import KnowledgeGraph
    g = KnowledgeGraph()
    law = g.add_node("law", "toy general law")
    ax = g.add_node("axiom", "AX")
    proved = g.add_node("theorem", "instance with own proof")
    g.add_edge(proved, "depends_on", ax)
    naked = g.add_node("theorem", "instance without own proof")
    for t in (proved, naked):
        g.add_edge(law, "generalizes", t)
        g.add_edge(t, "specializes", law)
    gi = generalization_impact(g)
    assert gi[0]["instances"] == 2 and gi[0]["independently_proved_instances"] == 1
    assert "1 instance(s) have no independent proof support" in gi[0]["if_the_law_fell"]
