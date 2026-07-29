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
  * strategy SELECTION (AC0) — after each cycle the director reads the impact analysis (the open
    frontier — the most-entangled unresolved conjectures) and the ladder, and proposes the next goal:
    settle the highest-impact open conjecture if one exists, else widen the sample bound.

The policy is deterministic and rule-based (an honest AC0, not a learned planner — that is later
work). The director decides WHAT to look at next; it never decides what is TRUE.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .epistemic_ladder import ladder_summary
from .failure_memory import FailureMemory, populate_from_refutations
from .impact import open_frontier
from .knowledge_graph import from_report as _kg_from_report
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


@dataclass
class ResearchDirector:
    """Runs discovery cycles with memory. State persists on the instance across `run_cycle` calls."""
    memory: FailureMemory = field(default_factory=FailureMemory)
    cycles: list = field(default_factory=list)
    _seen: set = field(default_factory=set)

    def _select_next_goal(self, frontier: list, ladder: dict) -> str:
        """AC0 policy: pursue the highest-impact open conjecture; if none, widen the bound."""
        if frontier:
            return f"settle open conjecture: {frontier[0]['statement']}"
        if ladder.get("EMPIRICALLY_VALIDATED", 0) > ladder.get("FORMALLY_PROVED", 0):
            return "raise validated laws toward proof (find structural/kernel arguments)"
        return "widen the sample bound to expose new structure"

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
        frontier = open_frontier(_kg_from_report(report))
        next_goal = self._select_next_goal(frontier, ladder)

        result = CycleResult(
            cycle=len(self.cycles) + 1, goal=goal, max_n=max_n, ladder=ladder,
            new_findings=new_findings, new_dead_ends=new_dead_ends,
            open_frontier=frontier[:3], next_goal=next_goal)
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
