"""
mathhead.discovery.strategy_log — record proof-strategy failures into the failure memory (roadmap S3).

S2 (`portfolio`) runs a strategy portfolio under a budget and reports an honest status per problem —
`solved`, `unsolved` (ran but nothing proved it), or `exhausted` (budget too small to launch anything).
S3 is the feedback edge from S2 into Track Y (`failure_memory`): it turns those non-solutions into
NEGATIVE KNOWLEDGE the engine keeps, and it aggregates per-strategy DIAGNOSTICS so the bottleneck
strategies become visible (which strategy is most often unaffordable, which one usually wins).

The mapping into the existing failure-memory vocabulary is honest and minimal:
  * `exhausted`  → a `timeout`-kind record (a RESOURCE failure — the budget could not afford any strategy);
  * `unsolved`   → a `dead_end` record (strategies ran, none settled the claim);
  * `solved`     → nothing recorded (a success is not a failure).

Recording is idempotent (the failure memory dedups by fingerprint), so re-logging the same failed problem
does not inflate the count. The diagnostics are exact counts over the given runs — no inference. This
closes the S→Y loop: the portfolio's dead ends now accumulate alongside refuted conjectures, and a
strategy that keeps being skipped as too expensive is surfaced, not silently repeated.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_STATUS_TO_KIND = {"exhausted": "timeout", "unsolved": "dead_end"}


def log_portfolio_run(memory, run, problem_label: str):
    """Record a non-solved portfolio run into `memory` as negative knowledge. Returns the record
    fingerprint, or None if the run was solved (nothing to learn from a success)."""
    kind = _STATUS_TO_KIND.get(run.status)
    if kind is None:                                    # solved → not a failure
        return None
    detail = {
        "status": run.status, "modulus": run.modulus, "budget": run.budget, "spent": run.spent,
        "launched": [o.name for o in run.outcomes if o.launched],
        "skipped": [o.name for o in run.outcomes if not o.launched],
    }
    return memory.record(kind, f"portfolio failed on: {problem_label}", detail)


@dataclass
class StrategyDiagnostics:
    runs: int = 0
    solved: int = 0
    unsolved: int = 0
    exhausted: int = 0
    launched: dict = field(default_factory=dict)   # strategy → times launched
    skipped: dict = field(default_factory=dict)    # strategy → times skipped (unaffordable)
    wins: dict = field(default_factory=dict)        # strategy → times it was the winner

    @property
    def bottleneck(self):
        """The strategy most often skipped as unaffordable (the resource bottleneck), or None."""
        return max(self.skipped, key=lambda s: (self.skipped[s], s)) if self.skipped else None


def diagnose_portfolio(runs) -> StrategyDiagnostics:
    """Aggregate exact per-strategy statistics over a list of PortfolioRun objects."""
    d = StrategyDiagnostics()
    for run in runs:
        d.runs += 1
        d.solved += run.status == "solved"
        d.unsolved += run.status == "unsolved"
        d.exhausted += run.status == "exhausted"
        for o in run.outcomes:
            table = d.launched if o.launched else d.skipped
            table[o.name] = table.get(o.name, 0) + 1
        if run.winner:
            d.wins[run.winner] = d.wins.get(run.winner, 0) + 1
    return d


def log_and_diagnose(memory, runs, labels) -> StrategyDiagnostics:
    """Log every non-solved run into `memory` and return the aggregate diagnostics — the full S3 pass."""
    for run, label in zip(runs, labels):
        log_portfolio_run(memory, run, label)
    return diagnose_portfolio(runs)
