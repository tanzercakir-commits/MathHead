"""
mathhead.discovery.director — the research director: a goal-driven loop with cross-cycle state
(roadmap Track AC — AC0 strategy selection, AC3 long-running session).

Everything so far has been a single pass (`run_report`). The director turns the engine from a
collection of modules into a RESEARCHER that runs cycles, carries state between them, and picks its
next goal from what it just learned:

  * cross-cycle STATE (AC3) — one `FailureMemory` accumulates dead ends across ALL cycles (deduped by
    fingerprint, so a branch closed in cycle 1 is never re-walked in cycle 3); a `seen` set tracks
    which findings are new each cycle; the ladder distribution is recorded per cycle so progress is
    visible.
  * strategy SELECTION (AC0) — after each cycle the director ranks the open goals by IMPORTANCE ×
    LIKELIHOOD (`lemma_ranking`, T2 — fusing impact's entanglement with gap's proximity-to-proof) and
    proposes the next goal: pursue the highest-priority open conjecture if one exists, else widen the
    sample bound. This closes the discover → prioritize → pursue loop with the T0/T2 signals, degrading
    gracefully to pure entanglement when no open goal is near proved ground.

The policy is deterministic and rule-based (an honest AC0, not a learned planner — that is later
work). The director decides WHAT to look at next; it never decides what is TRUE.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .epistemic_ladder import ladder_summary
from .failure_memory import FailureMemory, populate_from_refutations
from .impact import open_frontier
from .knowledge_graph import from_report as _kg_from_report
from .lemma_ranking import rank_lemmas
from .report import run_report


@dataclass
class CycleResult:
    cycle: int
    goal: str
    max_n: int
    ladder: dict
    new_findings: int
    new_dead_ends: int
    open_frontier: list
    next_goal: str
    top_lemma: dict = field(default_factory=dict)   # T2 pick: {statement, priority, importance, likelihood}
    rationale: dict = field(default_factory=dict)   # AD1: auditable WHY behind next_goal (see _decide)


@dataclass
class ResearchDirector:
    """Runs discovery cycles with memory. State persists on the instance across `run_cycle` calls."""
    memory: FailureMemory = field(default_factory=FailureMemory)
    cycles: list = field(default_factory=list)
    _seen: set = field(default_factory=set)

    def _select_next_goal(self, ranked: list, ladder: dict) -> str:
        """AC0 policy: pursue the highest-PRIORITY open conjecture (importance × likelihood, T2); if
        none, raise validated laws toward proof, else widen the bound."""
        return self._decide(ranked, ladder)[0]

    def _decide(self, ranked: list, ladder: dict) -> tuple:
        """AD1 — the goal AND its auditable rationale: which branch of the total three-branch rule
        fired, and the exact INPUTS that made it fire. Every field is recomputable from the same
        inputs (the T2 priority is a transparent weighted sum, not a learned score) — a reviewer
        can re-derive the decision, which is the whole point: an auditable WHY, not a CoT dump."""
        ev = ladder.get("EMPIRICALLY_VALIDATED", 0)
        fp = ladder.get("FORMALLY_PROVED", 0)
        inputs: dict = {"open_goals_ranked": len(ranked),
                        "empirically_validated": ev, "formally_proved": fp}
        if ranked:
            top = ranked[0]
            pri = getattr(top, "priority", None)          # stays TOTAL over duck-typed goals
            imp = getattr(top, "importance", None)
            lik = getattr(top, "likelihood", None)
            inputs.update({"top_statement": top.statement, "top_priority": pri,
                           "top_importance": imp, "top_likelihood": lik})
            because = f"{len(ranked)} open goal(s) are ranked; the top one is pursued"
            if None not in (pri, imp, lik):
                because += (f" — priority {pri} = 0.5·importance({imp}) + "
                            f"0.5·likelihood({lik}) (T2 transparent fusion)")
            rationale = {
                "policy": "AC0 total three-branch rule (deterministic, not learned)",
                "branch": "settle",
                "because": because,
                "inputs": inputs}
            return f"settle open conjecture: {top.statement}", rationale
        if ev > fp:
            rationale = {
                "policy": "AC0 total three-branch rule (deterministic, not learned)",
                "branch": "raise",
                "because": (f"no open goal is ranked, and EMPIRICALLY_VALIDATED ({ev}) exceeds "
                            f"FORMALLY_PROVED ({fp}) — validated laws outnumber proofs, so raise "
                            "them toward proof"),
                "inputs": inputs}
            return "raise validated laws toward proof (find structural/kernel arguments)", rationale
        rationale = {
            "policy": "AC0 total three-branch rule (deterministic, not learned)",
            "branch": "widen",
            "because": (f"no open goal is ranked, and EMPIRICALLY_VALIDATED ({ev}) does not exceed "
                        f"FORMALLY_PROVED ({fp}) — nothing to settle or raise, so widen the sample"),
            "inputs": inputs}
        return "widen the sample bound to expose new structure", rationale

    def run_cycle(self, max_n: int = 4, goal: str = "explore the sample") -> CycleResult:
        """One research cycle: run the pipeline, fold results into cross-cycle state, choose next goal."""
        report = run_report(max_n=max_n)

        # cross-cycle negative knowledge (deduped across ALL prior cycles)
        new_dead_ends = populate_from_refutations(
            self.memory,
            [(x["statement"], {"status": "refuted", "counterexample": x.get("counterexample", {})})
             for x in report.refuted])

        # which findings are new this cycle
        statements = [it["statement"] for bucket in (report.proved, report.empirical_laws,
                                                     report.open_bounded) for it in bucket]
        new_findings = sum(1 for s in statements if s not in self._seen)
        self._seen.update(statements)

        ladder = ladder_summary(report)
        kg = _kg_from_report(report)
        frontier = open_frontier(kg)
        ranked = rank_lemmas(kg)                        # T2: importance × likelihood
        next_goal, rationale = self._decide(ranked, ladder)
        top = ranked[0] if ranked else None
        top_lemma = ({"statement": top.statement, "priority": top.priority,
                      "importance": top.importance, "likelihood": top.likelihood} if top else {})

        result = CycleResult(
            cycle=len(self.cycles) + 1, goal=goal, max_n=max_n, ladder=ladder,
            new_findings=new_findings, new_dead_ends=new_dead_ends,
            open_frontier=frontier[:3], next_goal=next_goal, top_lemma=top_lemma,
            rationale=rationale)
        self.cycles.append(result)
        return result

    def run_session(self, n_cycles: int = 3, start_n: int = 3) -> dict:
        """Run a multi-cycle research session, each cycle widening the bound, and summarize."""
        goal = "explore the sample"
        for i in range(n_cycles):
            res = self.run_cycle(max_n=start_n + i, goal=goal)
            goal = res.next_goal                       # the director follows its own recommendation
        return self.session_summary()

    def session_summary(self) -> dict:
        """The long-running-session picture (AC3): progress per cycle + accumulated negative knowledge."""
        return {
            "cycles_run": len(self.cycles),
            "ladder_progression": [c.ladder for c in self.cycles],
            "total_dead_ends_learned": len(self.memory.records()),
            "final_open_frontier": self.cycles[-1].open_frontier if self.cycles else [],
            "next_goal": self.cycles[-1].next_goal if self.cycles else None,
            "lessons": self.memory.lessons()[:3],
        }
