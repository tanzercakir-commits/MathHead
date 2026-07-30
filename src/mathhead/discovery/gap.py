"""
mathhead.discovery.gap — measure the GAP between a goal and current knowledge (roadmap T0).

`impact.py` (X3) ranks the open frontier by ENTANGLEMENT — how many known results a conjecture is linked
to. T0 asks the complementary question: for a specific goal, how FAR is it from established ground? A
conjecture entangled with many results can still be unreachable; one with a single link to a proved
theorem may be nearly in hand. Gap is about proximity-to-proof, not centrality.

For a goal node it reports, all as exact graph computations (BFS hops + counts, never guesses):
  * status — proved / refuted (already resolved, gap 0) or open / unknown;
  * distance_to_known — fewest edges to the nearest ESTABLISHED node (theorem / lemma / axiom), or None
    if no path reaches proved ground;
  * open_dependencies — the transitive `depends_on` nodes that are themselves unresolved (the concrete
    lemmas still to be discharged);
  * gap_score ∈ [0,1] — 0.0 resolved, →1.0 as the goal gets farther from / more dependent on the unknown;
    1.0 exactly when no path to proved ground exists.

`frontier_gaps` ranks the open conjectures SMALLEST-gap first — the goals closest to being settled with
what is already known. Honest boundary: "known ground" is the engine's OWN proved theorems/axioms; a goal
in a domain with no proved anchor (e.g. a graph bound while only arithmetic is kernel-proved) truthfully
shows a large gap — that is a real limitation the measure surfaces, not a defect.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

_ANCHOR_KINDS = ("theorem", "lemma", "axiom")
_GOAL_KINDS = ("conjecture", "open_problem")


def _is_anchor(node) -> bool:
    """Established ground: a proved theorem/lemma/axiom, or a law/conjecture explicitly marked proved."""
    return node.kind in _ANCHOR_KINDS or node.attrs.get("status") == "proved"


def _is_refuted(graph, node) -> bool:
    return node.attrs.get("status") == "refuted" or any(
        e.relation == "refuted_by" and e.src == node.id for e in graph.edges)


def _adjacency(graph) -> dict:
    adj = {nid: set() for nid in graph.nodes}
    for e in graph.edges:
        adj[e.src].add(e.dst)
        adj[e.dst].add(e.src)
    return adj


def _distance_to_anchor(graph, goal_id: str, adj: dict):
    """Fewest edges from the goal to the nearest established node (BFS), or None if unreachable."""
    seen = {goal_id}
    q = deque([(goal_id, 0)])
    while q:
        nid, d = q.popleft()
        if d > 0 and _is_anchor(graph.nodes[nid]):
            return d
        for nb in sorted(adj[nid]):
            if nb not in seen:
                seen.add(nb)
                q.append((nb, d + 1))
    return None


def _open_dependencies(graph, goal_id: str) -> list:
    """Transitive `depends_on` closure, keeping only nodes that are neither established nor refuted."""
    out, seen, stack = [], {goal_id}, [goal_id]
    while stack:
        cur = stack.pop()
        for e in graph.edges:
            if e.relation == "depends_on" and e.src == cur and e.dst not in seen:
                seen.add(e.dst)
                stack.append(e.dst)
                node = graph.nodes[e.dst]
                if not _is_anchor(node) and not _is_refuted(graph, node):
                    out.append(e.dst)
    return sorted(out)


def _known_links(graph, goal_id: str) -> int:
    """How many `related_to`/`implies` edges tie the goal to established or empirical (law) knowledge."""
    n = 0
    for e in graph.edges:
        if e.relation not in ("related_to", "implies"):
            continue
        other = e.dst if e.src == goal_id else e.src if e.dst == goal_id else None
        if other is None:
            continue
        node = graph.nodes[other]
        if _is_anchor(node) or node.kind == "law":
            n += 1
    return n


@dataclass
class GapMeasure:
    goal: str                       # goal node id
    statement: str
    status: str                     # "proved" | "refuted" | "open" | "unknown"
    resolved: bool
    distance_to_known: int | None   # BFS hops to nearest established node (None = no path to proof)
    open_dependencies: list = field(default_factory=list)
    known_links: int = 0            # related_to/implies ties to established or empirical knowledge
    gap_score: float = 0.0          # 0.0 resolved … 1.0 no path to proved ground


def measure_gap(graph, goal_id: str) -> GapMeasure:
    """Measure the gap between one goal node and the engine's established knowledge."""
    if goal_id not in graph.nodes:
        return GapMeasure(goal_id, "", "unknown", False, None, [], 0, 1.0)
    node = graph.nodes[goal_id]
    if _is_anchor(node):
        return GapMeasure(goal_id, node.statement, "proved", True, 0, [], 0, 0.0)
    if _is_refuted(graph, node):
        return GapMeasure(goal_id, node.statement, "refuted", True, 0, [], 0, 0.0)
    adj = _adjacency(graph)
    dist = _distance_to_anchor(graph, goal_id, adj)
    deps = _open_dependencies(graph, goal_id)
    links = _known_links(graph, goal_id)
    score = 1.0 if dist is None else 1.0 - 1.0 / (1 + dist + len(deps))
    return GapMeasure(goal_id, node.statement, "open", False, dist, deps, links, round(score, 4))


def frontier_gaps(graph, k: int = 5) -> list:
    """Open goals ranked SMALLEST-gap first — closest to being settled with current knowledge. Ties
    (e.g. all-unreachable) break toward the goal with the most links to known/empirical results."""
    goals = [n for n in graph.nodes.values()
             if n.kind in _GOAL_KINDS and not _is_anchor(n) and not _is_refuted(graph, n)]
    measures = [measure_gap(graph, n.id) for n in goals]
    measures.sort(key=lambda g: (g.gap_score, -g.known_links, g.statement))
    return measures[:k]
