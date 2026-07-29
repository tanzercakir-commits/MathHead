"""Discovery Track X3 — structural impact analysis over the knowledge graph."""
from mathhead.discovery import run_report
from mathhead.discovery.impact import (
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
    assert set(a) == {"load_bearing_axioms", "most_connected", "open_frontier"}
    assert a == b                                             # exact, deterministic
