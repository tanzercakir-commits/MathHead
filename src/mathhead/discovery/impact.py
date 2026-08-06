"""
mathhead.discovery.impact — impact analysis over the knowledge graph (roadmap Track X3).

Given the typed knowledge graph (X0), answer the structural "so what?" questions — honestly, over the
engine's OWN current knowledge (not a literature it hasn't ingested yet):

  * load-bearing axioms — which inference rule the most theorems rest on (`depends_on` in-degree).
    If RESIDUE(m=2)/CRT support many proofs, they are the leverage points: strengthen or break one
    and many results move.
  * most-connected findings — the nodes with the highest total degree (hubs of the current web).
  * open frontier — the OPEN conjectures with the most `related_to` links: the unresolved statements
    most entangled with what's already known, hence the highest-impact ones to settle next.
  * generalizations — the parametric laws (P2-fed `generalizes` edges, v4F6) ranked by how many
    proved instances each covers, with the honest "what if the law fell?" answer computed from the
    graph: an instance with its own `depends_on` axiom support keeps its kernel proof — only the
    common explanation is lost; an instance WITHOUT independent support would lose its only warrant.

All are exact graph computations — counts and degrees, not guesses. This is descriptive impact within
the engine's knowledge; ingesting external open problems (to say "this settles conjecture C from the
literature") is Track X1/W2, still open.
"""
from __future__ import annotations


def _in_degree(graph, node_id: str, relation: str) -> int:
    return sum(1 for e in graph.edges if e.dst == node_id and e.relation == relation)


def _degree(graph, node_id: str) -> int:
    return sum(1 for e in graph.edges if e.src == node_id or e.dst == node_id)


def load_bearing_axioms(graph, k: int = 5) -> list:
    """Axioms ranked by how many theorems depend on them — the leverage points of the proof web."""
    axioms = [(n.statement, _in_degree(graph, n.id, "depends_on")) for n in graph.by_kind("axiom")]
    axioms.sort(key=lambda sc: (-sc[1], sc[0]))               # deterministic
    return [{"axiom": a, "supports": c} for a, c in axioms[:k]]


def most_connected(graph, k: int = 5) -> list:
    """The highest-degree nodes — hubs of the current knowledge web."""
    ranked = [(n, _degree(graph, n.id)) for n in graph.nodes.values()]
    ranked.sort(key=lambda sc: (-sc[1], sc[0].kind, sc[0].statement))
    return [{"kind": n.kind, "statement": n.statement, "degree": d} for n, d in ranked[:k]]


def open_frontier(graph, k: int = 5) -> list:
    """OPEN conjectures ranked by how entangled they are (`related_to` degree) with known results —
    the highest-impact statements to settle next."""
    opens = [n for n in graph.by_kind("conjecture") if n.attrs.get("status") == "open"]
    scored = [(n, sum(1 for e in graph.edges
                      if e.relation == "related_to" and (e.src == n.id or e.dst == n.id)))
              for n in opens]
    scored.sort(key=lambda sc: (-sc[1], sc[0].statement))
    return [{"statement": n.statement, "entanglement": d} for n, d in scored[:k]]


def generalization_impact(graph, k: int = 5) -> list:
    """Parametric laws (nodes with outgoing `generalizes` edges) ranked by instance coverage, each
    with the exact structural answer to "what happens to the instances if the law fell?". HONEST:
    the P2 instances are independently kernel-proved (their own `depends_on` axiom edges), so a
    falling law costs them their common EXPLANATION, never their proofs — and the code checks that
    per instance instead of asserting it."""
    laws = [n for n in graph.nodes.values()
            if any(e.src == n.id and e.relation == "generalizes" for e in graph.edges)]
    out = []
    for law in laws:
        instances = graph.specializations_of(law.id)
        with_own_proof = sum(1 for i in instances if graph.neighbors(i, "depends_on"))
        if with_own_proof == len(instances):
            consequence = ("all instances keep their own kernel proofs (independent depends_on "
                           "support); only the common explanation is lost")
        else:
            consequence = (f"{len(instances) - with_own_proof} instance(s) have no independent "
                           f"proof support and would lose their only warrant")
        out.append({"law": law.statement, "instances": len(instances),
                    "independently_proved_instances": with_own_proof,
                    "if_the_law_fell": consequence})
    out.sort(key=lambda d: (-d["instances"], d["law"]))        # deterministic
    return out[:k]


def impact_summary(graph) -> dict:
    """One structural impact picture over the whole graph."""
    return {
        "load_bearing_axioms": load_bearing_axioms(graph),
        "most_connected": most_connected(graph),
        "open_frontier": open_frontier(graph),
        "generalizations": generalization_impact(graph),
    }
