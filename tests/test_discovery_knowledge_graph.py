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
    # X0 asserts only structurally-certain edges. Since v4F6, generalizes/specializes exist too —
    # but ONLY fed by the kernel-backed P2 lift; equivalent_to/implies stay reserved (no checker).
    g = from_report(run_report(max_n=5))
    rels = {e.relation for e in g.edges}
    assert rels <= {"depends_on", "refuted_by", "related_to", "generalizes", "specializes"}
    assert "equivalent_to" not in rels and "implies" not in rels
    # every generalizes edge starts at the single P2 law node — no other source may assert one
    for e in g.edges:
        if e.relation == "generalizes":
            assert g.nodes[e.src].attrs.get("source") == "P2"
        if e.relation == "specializes":
            assert g.nodes[e.dst].attrs.get("source") == "P2"


# --- v4F6: generalizes/specializes edges are BORN from the P2 run, queryable, and honest --------

def test_p2_generalization_edges_are_born_from_the_report():
    g = from_report(run_report(max_n=5))
    laws = [n for n in g.by_kind("law") if n.attrs.get("source") == "P2"]
    assert len(laws) == 1                                    # ONE shared parametric law node
    law = laws[0]
    assert "consecutive integers" in law.statement and "k!" in law.statement
    instances = {g.nodes[i].statement for i in g.specializations_of(law.id)}
    assert instances == {                                    # exactly the five kernel-backed lifts
        "(n*(n+1)) % 2 == 0", "(n*(n+1)*(n+2)) % 6 == 0", "(n*(n+1)*(n+2)*(n+3)) % 24 == 0",
        "(n**2 - n) % 2 == 0", "(n**3 - n) % 6 == 0"}


def test_generalization_edges_are_queryable_in_both_directions():
    g = from_report(run_report(max_n=5))
    th = next(n for n in g.by_kind("theorem") if n.statement == "(n**3 - n) % 6 == 0")
    ups = g.generalizations_of(th.id)
    assert len(ups) == 1 and g.nodes[ups[0]].attrs.get("source") == "P2"
    assert th.id in g.specializations_of(ups[0])             # the inverse query agrees
    # and the raw edge queries agree with the convenience API
    assert g.neighbors(ups[0], "generalizes") == g.specializations_of(ups[0])


def test_p2_decline_yields_no_edge_honestly():
    # 30 | n⁵−n and 42 | n⁷−n are TRUE but not consecutive-product instances — P2 declines,
    # so the graph must NOT connect them to the law (no guessed entailment)
    g = from_report(run_report(max_n=5))
    for stmt in ("(n**5 - n) % 30 == 0", "(n**7 - n) % 42 == 0"):
        th = next(n for n in g.by_kind("theorem") if n.statement == stmt)
        assert g.generalizations_of(th.id) == []


def test_p2_law_node_carries_honest_epistemic_attrs():
    g = from_report(run_report(max_n=5))
    law = next(n for n in g.by_kind("law") if n.attrs.get("source") == "P2")
    assert law.attrs["instance_status"] == "kernel_verified"          # per-k, universal in n
    assert law.attrs["universal_status"] == "structural_argument"     # ∀k: cited, NOT machine-proved
    assert law.attrs["kernel_verified_k"] == [1, 2, 3, 4, 5, 6]


def test_generalization_queries_on_a_hand_built_graph():
    g = KnowledgeGraph()
    law = g.add_node("law", "general law")
    t1 = g.add_node("theorem", "instance 1")
    t2 = g.add_node("theorem", "instance 2")
    g.add_edge(law, "generalizes", t1)
    g.add_edge(t1, "specializes", law)
    g.add_edge(law, "generalizes", t2)                       # single-direction edge on purpose
    assert g.specializations_of(law) == [t1, t2]
    assert g.generalizations_of(t1) == [law]
    assert g.generalizations_of(t2) == [law]                 # robust to a one-direction edge
    assert g.generalizations_of(law) == []


def test_inflated_universal_status_is_clamped_with_a_loud_error(monkeypatch):
    # epistemic clamp: if P2 ever returned a lift whose ∀k claim pretends to be machine-proved,
    # the edge builder must REFUSE (ValueError), not seed the graph with an overclaimed law node
    from importlib import import_module

    from mathhead.discovery.knowledge_graph import add_p2_generalization_edges
    gen_mod = import_module("mathhead.discovery.generalize")   # the module (package re-exports
    real = gen_mod.generalize                                  # shadow it with the function)

    def inflated(expr, m, k_max=6):
        g = real(expr, m, k_max)
        g.universal_status = "kernel_verified"               # the lie the clamp must catch
        return g

    monkeypatch.setattr(gen_mod, "generalize", inflated)
    g = KnowledgeGraph()
    tid = g.add_node("theorem", "(n**3 - n) % 6 == 0")
    with pytest.raises(ValueError, match="not machine-proved"):
        add_p2_generalization_edges(g, [(tid, {"statement": "(n**3 - n) % 6 == 0", "modulus": 6})])
    assert not any(e.relation in ("generalizes", "specializes") for e in g.edges)  # nothing seeded


def test_generalization_edges_are_deterministic():
    a, b = from_report(run_report(max_n=4)), from_report(run_report(max_n=4))
    ga = [(e.src, e.relation, e.dst) for e in a.edges if e.relation in ("generalizes", "specializes")]
    gb = [(e.src, e.relation, e.dst) for e in b.edges if e.relation in ("generalizes", "specializes")]
    assert ga and ga == gb


def test_mermaid_export_is_deterministic():
    g = from_report(run_report(max_n=4))
    a, b = g.export_mermaid(), g.export_mermaid()
    assert a == b and a.startswith("graph LR")
