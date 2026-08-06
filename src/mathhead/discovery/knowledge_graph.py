"""
mathhead.discovery.knowledge_graph — a semantic graph of what the engine knows (roadmap Track X0).

Findings stop being a flat list and become a typed GRAPH: nodes are theorems / laws / conjectures /
counterexamples / axioms (and, later, definitions / open-problems), edges are typed relations —
`depends_on` (a theorem rests on an axiom), `refuted_by` (a conjecture died to a counterexample),
`related_to` (two statements share an invariant), plus room for `generalizes` / `implies`. This is the
substrate impact analysis (X3) and novelty-vs-literature (W2/X1) will later run over.

`from_report` populates the graph from a DiscoveryReport, adding only edges the engine can assert
WITHOUT guessing: structural `depends_on` from the kernel axiom lists, `refuted_by` from the
counterexamples, and symmetric `related_to` from shared invariant tokens.

`generalizes`/`specializes` (v4F6) are fed EXCLUSIVELY by the P2 generalization (`generalize.py`):
when a proved divisibility `m | p(n)` is kernel-detected to be an instance of the consecutive-product
law (p(n) is a product of k consecutive integers with m = k!, factorization kernel-certified, and the
lifted instances k=1..K each kernel-proved), the graph gets ONE law node plus
`law —generalizes→ theorem` and `theorem —specializes→ law` edges. A finding P2 honestly declines
(e.g. 30 | n⁵−n — no consecutive-product structure) gets NO edge. Subclass scopes (trees ⊂ graphs)
deliberately contribute nothing: the W0 filter drops restricted-universals, so the report never
contains a subclass law together with the universal law it restricts — there is no certain
scope-containment pair to assert. `equivalent_to`/`implies` stay reserved (no entailment checker).

Deterministic: nodes and edges are built in a fixed order; exports sort.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

KINDS = ("theorem", "lemma", "law", "conjecture", "counterexample", "definition",
         "open_problem", "axiom")
RELATIONS = ("depends_on", "refuted_by", "generalizes", "specializes", "equivalent_to",
             "implies", "related_to")

_KNOWN_INVARIANTS = {
    "num_vertices", "num_edges", "sum_degrees", "num_triangles", "max_degree", "min_degree",
    "num_components", "chromatic_number", "clique_number", "is_hamiltonian",
}


@dataclass
class Node:
    id: str
    kind: str
    statement: str
    attrs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    src: str
    relation: str
    dst: str


class KnowledgeGraph:
    """A typed store of nodes + relations. `add_node` auto-ids unless an id is given; `ensure_node`
    de-duplicates by explicit id (used for shared axioms)."""

    def __init__(self) -> None:
        self.nodes: dict = {}
        self.edges: list = []
        self._counter = 0

    def add_node(self, kind: str, statement: str = "", *, id: str | None = None, **attrs) -> str:
        if kind not in KINDS:
            raise ValueError(f"unknown node kind {kind!r}; known: {KINDS}")
        if id is None:
            id = f"{kind}:{self._counter}"
            self._counter += 1
        self.nodes[id] = Node(id, kind, statement, dict(attrs))
        return id

    def ensure_node(self, id: str, kind: str, statement: str = "", **attrs) -> str:
        if id not in self.nodes:
            self.nodes[id] = Node(id, kind, statement, dict(attrs))
        return id

    def add_edge(self, src: str, relation: str, dst: str) -> None:
        if relation not in RELATIONS:
            raise ValueError(f"unknown relation {relation!r}; known: {RELATIONS}")
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError("both endpoints must exist before adding an edge")
        e = Edge(src, relation, dst)
        if e not in self.edges:
            self.edges.append(e)

    def by_kind(self, kind: str) -> list:
        return [n for n in self.nodes.values() if n.kind == kind]

    def neighbors(self, id: str, relation: str | None = None) -> list:
        return [e.dst for e in self.edges
                if e.src == id and (relation is None or e.relation == relation)]

    def relations_of(self, id: str) -> list:
        return [e for e in self.edges if e.src == id or e.dst == id]

    def generalizations_of(self, id: str) -> list:
        """Node ids that GENERALIZE this node — outgoing `specializes` targets plus sources of
        incoming `generalizes` edges (robust to a single-direction edge), first-seen order."""
        out = [e.dst for e in self.edges if e.src == id and e.relation == "specializes"]
        out += [e.src for e in self.edges
                if e.dst == id and e.relation == "generalizes" and e.src not in out]
        return out

    def specializations_of(self, id: str) -> list:
        """Node ids that SPECIALIZE this node (its instances) — outgoing `generalizes` targets plus
        sources of incoming `specializes` edges, first-seen order."""
        out = [e.dst for e in self.edges if e.src == id and e.relation == "generalizes"]
        out += [e.src for e in self.edges
                if e.dst == id and e.relation == "specializes" and e.src not in out]
        return out

    def to_dict(self) -> dict:
        return {
            "nodes": [{"id": n.id, "kind": n.kind, "statement": n.statement, "attrs": n.attrs}
                      for n in self.nodes.values()],
            "edges": [{"src": e.src, "relation": e.relation, "dst": e.dst} for e in self.edges],
        }

    def summary(self) -> dict:
        kinds: dict = {}
        for n in self.nodes.values():
            kinds[n.kind] = kinds.get(n.kind, 0) + 1
        rels: dict = {}
        for e in self.edges:
            rels[e.relation] = rels.get(e.relation, 0) + 1
        return {"nodes": len(self.nodes), "edges": len(self.edges),
                "by_kind": kinds, "by_relation": rels}

    def export_mermaid(self) -> str:
        """A Mermaid `graph LR` rendering (deterministic; ids and edges sorted)."""
        lines = ["graph LR"]
        for nid in sorted(self.nodes):
            n = self.nodes[nid]
            label = (n.statement or n.kind).replace('"', "'")[:40]
            lines.append(f'  {_safe(nid)}["{n.kind}: {label}"]')
        for e in sorted(self.edges, key=lambda e: (e.src, e.relation, e.dst)):
            lines.append(f"  {_safe(e.src)} -->|{e.relation}| {_safe(e.dst)}")
        return "\n".join(lines)


def _safe(node_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", node_id)


def _invariant_tokens(statement: str) -> set:
    return set(re.findall(r"[A-Za-z_][A-Za-z_0-9]+", str(statement))) & _KNOWN_INVARIANTS


_MOD_CLAIM = re.compile(r"^\((?P<expr>.+)\) % (?P<m>\d+) == 0$")
_P2_LAW_ID = "law:P2:consecutive-product-k!"


def add_p2_generalization_edges(g: KnowledgeGraph, proved_theorems: list) -> list:
    """Feed `generalizes`/`specializes` edges from the P2 generalization (the ONLY source, v4F6).

    `proved_theorems` is a list of (theorem_node_id, proved_item_dict). For each proved modular
    divisibility `(p(n)) % m == 0`, ask `generalize.generalize(p, m)`; ONLY if it returns a
    kernel-backed lift (consecutive-run detected, m = k!, every tested instance kernel-proved) does
    the graph get the shared parametric-law node plus `law —generalizes→ theorem` and
    `theorem —specializes→ law`. An honest P2 decline (n⁵−n, n⁷−n) adds NOTHING — no guessed edges.
    Returns the theorem node ids that were linked. Deterministic (P2 is)."""
    from .generalize import generalize
    linked = []
    for tid, it in proved_theorems:
        m = it.get("modulus")
        match = _MOD_CLAIM.match(it.get("statement", "")) if m else None
        if not match:
            continue
        gen = generalize(match.group("expr"), int(m))
        if not gen.generalized:
            continue                          # honest: no consecutive-product structure ⇒ no edge
        if gen.universal_status != "structural_argument":
            # epistemic clamp: the ∀k statement is a CITED classical argument, never machine-proved
            # here — a P2 result claiming a machine tier for it is inflated and must fail loudly
            # rather than silently seed the graph with an overclaimed law node.
            raise ValueError(
                f"P2 lift for {match.group('expr')!r} claims universal_status="
                f"{gen.universal_status!r}; the ∀k law is not machine-proved — refusing to "
                "build generalizes edges on an inflated tier")
        lid = g.ensure_node(
            _P2_LAW_ID, "law", gen.principle,
            source="P2", parameter=gen.parameter,
            instance_status=gen.instance_status,           # per-k: kernel_verified (universal in n)
            universal_status=gen.universal_status,         # ∀k: structural_argument (cited, honest)
            citation=gen.citation,
            kernel_verified_k=[i.k for i in gen.instances if i.kernel_verified])
        g.add_edge(lid, "generalizes", tid)
        g.add_edge(tid, "specializes", lid)
        linked.append(tid)
    return linked


def from_report(report) -> KnowledgeGraph:
    """Build the knowledge graph from a DiscoveryReport — asserting only structurally-certain edges."""
    g = KnowledgeGraph()
    tagged = []   # (node_id, statement) for related_to inference over laws/theorems/conjectures
    arithmetic_proved = []   # (node_id, item) — candidates for P2 generalizes/specializes edges

    for it in report.proved:
        tid = g.add_node("theorem", it["statement"], certainty=it.get("certainty", ""),
                         kernel_verified=bool(it.get("kernel_verified")))
        for ax in it.get("axioms", []):
            aid = g.ensure_node(f"axiom:{ax}", "axiom", ax)
            g.add_edge(tid, "depends_on", aid)                 # theorem rests on axiom (certain)
        tagged.append((tid, it["statement"]))
        if it.get("modulus"):
            arithmetic_proved.append((tid, it))

    for it in report.empirical_laws:
        lid = g.add_node("law", it["statement"], scope=it.get("scope", ""))
        tagged.append((lid, it["statement"]))

    for it in report.refuted:
        cid = g.add_node("conjecture", it["statement"], status="refuted")
        xid = g.add_node("counterexample", str(it.get("counterexample", "")))
        g.add_edge(cid, "refuted_by", xid)                     # conjecture killed by witness (certain)
        tagged.append((cid, it["statement"]))

    for it in report.open_bounded:
        oid = g.add_node("conjecture", it["statement"], status="open")
        tagged.append((oid, it["statement"]))

    # symmetric related_to for shared invariants (honest structural link, no entailment claim)
    for i in range(len(tagged)):
        for j in range(i + 1, len(tagged)):
            (a_id, a_st), (b_id, b_st) = tagged[i], tagged[j]
            if _invariant_tokens(a_st) & _invariant_tokens(b_st):
                g.add_edge(a_id, "related_to", b_id)

    # generalizes/specializes fed ONLY by the P2 kernel-backed lift (v4F6) — never guessed
    add_p2_generalization_edges(g, arithmetic_proved)
    return g
