"""Discovery Track X0 — a typed knowledge graph of findings + relations, built from the report."""
import pytest

from mathhead.discovery import run_report
from mathhead.discovery.knowledge_graph import KnowledgeGraph, from_report


def test_add_node_and_edge_with_validation():
    g = KnowledgeGraph()
    a = g.add_node("theorem", "A")
    b = g.add_node("axiom", "RESIDUE(m=2)")
    g.add_edge(a, "depends_on", b)
    assert g.neighbors(a, "depends_on") == [b]
    with pytest.raises(ValueError):
        g.add_node("not_a_kind", "x")
    with pytest.raises(ValueError):
        g.add_edge(a, "not_a_relation", b)
    with pytest.raises(KeyError):
        g.add_edge(a, "depends_on", "missing")


def test_ensure_node_deduplicates_by_id():
    g = KnowledgeGraph()
    g.ensure_node("axiom:CRT", "axiom", "CRT")
    g.ensure_node("axiom:CRT", "axiom", "CRT")
    assert len(g.by_kind("axiom")) == 1


def test_edges_are_deduplicated():
    g = KnowledgeGraph()
    a = g.add_node("theorem", "A")
    b = g.add_node("axiom", "X")
    g.add_edge(a, "depends_on", b)
    g.add_edge(a, "depends_on", b)
    assert len(g.edges) == 1


def test_from_report_builds_typed_nodes():
    g = from_report(run_report(max_n=5))
    s = g.summary()
    assert s["by_kind"]["theorem"] >= 7          # the modular + sum facts
    assert s["by_kind"]["axiom"] >= 3            # RESIDUE(m=2), CRT, ...
    assert s["by_kind"]["counterexample"] >= 3   # the refuted conjectures' witnesses


def test_theorems_depend_on_their_axioms():
    g = from_report(run_report(max_n=5))
    th = next(n for n in g.by_kind("theorem") if n.statement == "(n**3 - n) % 6 == 0")
    deps = {g.nodes[d].statement for d in g.neighbors(th.id, "depends_on")}
    assert {"CRT", "RESIDUE(m=2)", "RESIDUE(m=3)"} <= deps


def test_refuted_conjectures_link_to_a_counterexample():
    g = from_report(run_report(max_n=5))
    refuted = [n for n in g.by_kind("conjecture") if n.attrs.get("status") == "refuted"]
    assert refuted
    for c in refuted:
        assert g.neighbors(c.id, "refuted_by")   # each has a counterexample node


def test_no_fabricated_entailment_edges():
    # X0 asserts only structurally-certain edges; generalizes/equivalent_to need a judged pass
    g = from_report(run_report(max_n=5))
    rels = {e.relation for e in g.edges}
    assert rels <= {"depends_on", "refuted_by", "related_to"}
    assert "generalizes" not in rels and "equivalent_to" not in rels


def test_mermaid_export_is_deterministic():
    g = from_report(run_report(max_n=4))
    a, b = g.export_mermaid(), g.export_mermaid()
    assert a == b and a.startswith("graph LR")
