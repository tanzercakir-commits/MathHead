"""
mathhead.discovery.report — one honest run report (roadmap AC2 + provenance AF-lite).

Runs the discovery pipeline across both domains and assembles ONE organized picture: what was
PROVED (formally, by the judge), what was DISCOVERED empirically (holds on the sample, not
proven), what was REFUTED (with a minimal counterexample), and what stays OPEN (survived the
attack but unproven). Every item carries an honest status — nothing is dressed up. Even a run
that proves little yields a valuable, organized artifact ("even a failure is a result").

Deterministic: generation is memoized, the solver seed is fixed — the same report every run.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import mathhead

from .arithmetic import run_arithmetic_discovery
from .conjectures import bound_conjectures
from .generate import generate_graphs
from .invariants import is_forest, is_tree
from .novelty import novel_subclass_laws
from .refute import refute
from .relations import discover_linear_laws
from .sequences import run_sequence_discovery


@dataclass
class DiscoveryReport:
    proved: list = field(default_factory=list)          # formally proved (by the judge)
    empirical_laws: list = field(default_factory=list)  # hold on the sample; NOT proven
    refuted: list = field(default_factory=list)         # killed, with a minimal counterexample
    open_bounded: list = field(default_factory=list)    # survived the attack; unproven
    meta: dict = field(default_factory=dict)


def _graph_findings(max_n: int):
    graphs = [g for n in range(max_n + 1) for g in generate_graphs(n)]
    empirical, refuted, survived = [], [], []

    for law in discover_linear_laws(graphs, holds_over=f"all graphs n<={max_n}"):
        empirical.append({"statement": law.expression, "status": "empirical",
                          "scope": f"all graphs n<={max_n}", "support": law.support})
    for label, pred in (("trees", is_tree), ("forests", is_forest)):
        for c in novel_subclass_laws(graphs, pred, label):   # drop restricted-universals (W0)
            empirical.append({"statement": c.statement, "status": "empirical",
                              "scope": label, "support": c.support})

    for c in bound_conjectures([g for n in range(max_n) for g in generate_graphs(n)]):
        r = refute(c, max_n=max_n)
        if r.status == "refuted":
            refuted.append({"statement": c.statement, "status": "refuted",
                            "counterexample": r.detail})
        else:
            survived.append({"statement": c.statement, "status": r.status,
                             "checked": r.checked, "bound_n": r.bound_n})
    return empirical, refuted, survived


def run_report(max_n: int = 6) -> DiscoveryReport:
    """Run the full pipeline (graphs + arithmetic) and assemble the organized, honest report."""
    empirical, refuted, survived = _graph_findings(max_n)
    proved, open_bounded = [], list(survived)

    for f in run_arithmetic_discovery():
        item = {"statement": f.claim, "modulus": f.modulus}
        if f.verdict == "proved":
            proved.append({**item, "status": "proved", "certainty": f.certainty})
        elif f.verdict == "refuted":
            refuted.append({**item, "status": "refuted"})
        else:
            open_bounded.append({**item, "status": "no_counterexample_within_bound",
                                 "note": f"judge: {f.certainty}"})

    for s in run_sequence_discovery():
        stmt = f"sum_(i=1..n) {s.term} = {s.closed_form}"
        if s.verdict == "proved":
            proved.append({"statement": stmt, "status": "proved", "certainty": s.certainty})
        elif s.verdict == "refuted":
            refuted.append({"statement": stmt, "status": "refuted",
                            "counterexample": {"note": "not a polynomial identity"}})
        else:
            open_bounded.append({"statement": stmt, "status": "unknown"})

    from mathhead.guardrails import MAX_STATEMENTS  # noqa: F401  (touch to assert import health)
    meta = {
        "mathhead_version": getattr(mathhead, "__version__", "?"),
        "solver_seed": 42,
        "graph_bound_n": max_n,
        "determinism": "memoized generation + fixed seed -> same report every run",
    }
    return DiscoveryReport(proved, empirical, refuted, open_bounded, meta)


def render(report: DiscoveryReport) -> str:
    """Render the report as readable Markdown."""
    lines = ["# MathHead — Discovery Run Report", ""]
    lines.append(f"_MathHead {report.meta.get('mathhead_version')} · seed "
                 f"{report.meta.get('solver_seed')} · graphs n≤{report.meta.get('graph_bound_n')} "
                 f"· {report.meta.get('determinism')}_")
    lines.append("")

    def section(title, items, fmt):
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append("_none_")
        for it in items:
            lines.append(f"- {fmt(it)}")
        lines.append("")

    section("PROVED (formal — by the judge)", report.proved,
            lambda it: f"`{it['statement']}` — {it.get('certainty', '')}")
    section("REFUTED (killed, with a minimal counterexample)", report.refuted,
            lambda it: f"`{it['statement']}` — counterexample: {it.get('counterexample', {})}")
    section("DISCOVERED (empirical — holds on the sample, NOT proven)", report.empirical_laws,
            lambda it: f"`{it['statement']}` — {it.get('scope', '')} (support {it.get('support', '?')})")
    section("OPEN (survived the attack; unproven — no_counterexample_within_bound)", report.open_bounded,
            lambda it: f"`{it['statement']}` — {it.get('note', it.get('status', ''))}")
    return "\n".join(lines)
