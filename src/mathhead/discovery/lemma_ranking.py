"""
mathhead.discovery.lemma_ranking — rank candidate lemmas by importance × likelihood (roadmap T2).

The research director faces a queue of open goals and must pick which to attack next. Two exact
structural signals already exist but pull in different directions: `impact.py` (X3) measures IMPORTANCE
(how entangled a conjecture is with known results — settling it moves a lot), and `gap.py` (T0) measures
proximity-to-proof (how reachable it is with current knowledge). A goal can be important yet unreachable,
or reachable yet peripheral. T2 fuses them into one actionable priority:

  * importance — the goal's `related_to` entanglement, normalized to [0,1] over the current open set;
  * likelihood — `1 − gap_score` from the gap measure (near proved ground ⇒ close to 1);
  * priority   — a transparent weighted sum `w_imp·importance + w_lik·likelihood` (default 0.5/0.5).

`rank_lemmas` returns the open goals in descending priority — the ones both worth settling AND within
reach first. HONEST: this is a transparent HEURISTIC over two exact signals (not a learned model — that
is W3/S4, 🔴), every component is exposed for audit, and it ranks ATTENTION only, never truth. Weights
are explicit and adjustable; ties break deterministically by goal id.
"""
from __future__ import annotations

from dataclasses import dataclass

from .gap import measure_gap

_GOAL_KINDS = ("conjecture", "open_problem")


@dataclass
class RankedLemma:
    goal: str                   # goal node id
    statement: str
    importance: float           # normalized entanglement in [0,1]
    likelihood: float           # 1 − gap_score (proximity to proof) in [0,1]
    priority: float             # w_imp·importance + w_lik·likelihood


def _entanglement(graph, goal_id: str) -> int:
    return sum(1 for e in graph.edges
               if e.relation == "related_to" and (e.src == goal_id or e.dst == goal_id))


def rank_lemmas(graph, k: int = 5, w_importance: float = 0.5, w_likelihood: float = 0.5) -> list:
    """Open goals ranked by `w_imp·importance + w_lik·likelihood`, highest first. Importance is the
    entanglement normalized over the open set; likelihood is 1 − gap_score. Deterministic."""
    opens = []
    for n in graph.nodes.values():
        if n.kind not in _GOAL_KINDS:
            continue
        gm = measure_gap(graph, n.id)
        if gm.status != "open":                       # skip resolved (proved / refuted)
            continue
        opens.append((n, gm))
    if not opens:
        return []
    max_ent = max(_entanglement(graph, n.id) for n, _ in opens) or 1
    ranked = []
    for n, gm in opens:
        importance = _entanglement(graph, n.id) / max_ent
        likelihood = 1.0 - gm.gap_score
        priority = w_importance * importance + w_likelihood * likelihood
        ranked.append(RankedLemma(
            n.id, n.statement, round(importance, 4), round(likelihood, 4), round(priority, 4)))
    ranked.sort(key=lambda r: (-r.priority, r.goal))
    return ranked[:k]


def next_lemma(graph):
    """The single highest-priority open goal to attack next, or None if none are open."""
    ranked = rank_lemmas(graph, k=1)
    return ranked[0] if ranked else None
