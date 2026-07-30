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
from .coloring import coloring_bounds, verify_chromatic_number
from .conjectures import bound_conjectures
from .generate import generate_graphs
from .graph_proofs import certify_frontier_laws
from .hamiltonicity import hamiltonicity_laws, verify_hamiltonicity
from .identities import run_identity_discovery
from .invariants import is_forest, is_tree
from .novelty import novel_subclass_laws
from .objects import Graph
from .refute import refute
from .relations import discover_linear_laws
from .sequences import run_sequence_discovery


@dataclass
class DiscoveryReport:
    proved: list = field(default_factory=list)          # formally proved (by the judge)
    empirical_laws: list = field(default_factory=list)  # hold on the sample; NOT proven
    refuted: list = field(default_factory=list)         # killed, with a minimal counterexample
    open_bounded: list = field(default_factory=list)    # survived the attack; unproven
    frontier: list = field(default_factory=list)        # NP-hard invariant VALUES solver-confirmed
    meta: dict = field(default_factory=dict)
    explanations: list = field(default_factory=list)    # structure explaining a result (factorization)


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


def _frontier_laws(max_n: int):
    """Mine the FRONTIER (NP-hard invariant) laws — coloring bounds + Hamiltonicity implications —
    counterexample-first over the graph sample. Pure/local (χ, ω, Hamiltonicity are exact
    invariants); the survivors are `bounded_check` (OPEN), the killed ones REFUTED."""
    graphs = [g for n in range(max_n + 1) for g in generate_graphs(n)]
    survived, refuted = [], []

    # which surviving laws we hold a constructive certificate for (every instance re-checked).
    # solver_confirm=False → structural certificates only, so the report stays fast/deterministic.
    by_law: dict = {}
    for c in certify_frontier_laws(graphs, solver_confirm=False):
        by_law.setdefault(c.law, []).append(c.checked)
    certified = {law for law, oks in by_law.items() if oks and all(oks)}

    for f in list(coloring_bounds(graphs)) + list(hamiltonicity_laws(graphs)):
        if f.status == "refuted":
            refuted.append({"statement": f.statement, "status": "refuted",
                            "counterexample": f.counterexample, "source": "frontier"})
        else:
            note = f"frontier · {f.certainty}"
            is_certified = f.statement in certified
            if is_certified:
                note += " · constructively certified over the sample (constructive_bounded)"
            survived.append({"statement": f.statement, "status": f.status, "note": note,
                             "source": "frontier", "certified": is_certified})
    return survived, refuted


def _frontier_confirmations() -> list:
    """Exercise the two-authority check IN the report: a handful of representative NP-hard invariant
    VALUES, each confirmed by MathHead's solver (χ via graph_coloring sat@χ∧unsat@χ−1; Hamiltonicity
    via hamiltonian_path). This is provenance — the values are `solver_verified`, distinct from the
    (bounded_check) laws above."""
    k3 = Graph.from_edges(3, [(0, 1), (1, 2), (0, 2)])
    k4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
    c5 = Graph.from_edges(5, [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)])
    p4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3)])
    out = []
    for name, g in (("K4", k4), ("K3", k3)):
        v = verify_chromatic_number(g)
        out.append({"invariant": "chromatic_number", "graph": name, "value": v.chi,
                    "confirmed": v.confirmed, "certainty": v.certainty,
                    "method": "MathHead graph_coloring: sat@χ ∧ unsat@χ−1"})
    for name, g in (("C5", c5), ("P4", p4)):
        v = verify_hamiltonicity(g)
        out.append({"invariant": "is_hamiltonian", "graph": name, "value": v.hamiltonian,
                    "confirmed": v.confirmed, "certainty": v.certainty,
                    "method": "MathHead hamiltonian_path(cycle=True)"})
    return out


def run_report(max_n: int = 6) -> DiscoveryReport:
    """Run the full pipeline (graphs + arithmetic + frontier) and assemble the organized, honest
    report."""
    empirical, refuted, survived = _graph_findings(max_n)
    proved, open_bounded = [], list(survived)

    front_survived, front_refuted = _frontier_laws(max_n)
    open_bounded.extend(front_survived)
    refuted.extend(front_refuted)

    for f in run_arithmetic_discovery():
        item = {"statement": f.claim, "modulus": f.modulus}
        if f.verdict == "proved":
            proved.append({**item, "status": "proved", "certainty": f.certainty,
                           "independently_verified": f.independently_verified,
                           "kernel_verified": f.kernel_verified,
                           "proof_hash": f.proof_hash, "axioms": list(f.axioms)})
        elif f.verdict == "refuted":
            refuted.append({**item, "status": "refuted"})
        else:
            open_bounded.append({**item, "status": "no_counterexample_within_bound",
                                 "note": f"judge: {f.certainty}"})

    explanations = []
    for f in run_identity_discovery():                  # kernel-verified factorizations (+ why)
        if f.kernel_verified:
            proved.append({"statement": f"{f.expression} = {f.factored}", "status": "proved",
                           "certainty": "kernel_identity", "kernel_verified": True,
                           "proof_hash": f.proof_hash, "axioms": list(f.axioms)})
        if f.consecutive_run:
            explanations.append({
                "identity": f"{f.expression} = {f.factored}",
                "explains": f"{f.divisibility_explained} | {f.expression}",
                "reason": f"product of {f.consecutive_run} consecutive integers "
                          f"⇒ divisible by {f.consecutive_run}! = {f.divisibility_explained}"})

    # graph-domain structural explanations (double counting, clique bound, cycle degree)
    from .structural_explanations import structural_explanations
    explanations.extend(structural_explanations(
        [g for n in range(max_n + 1) for g in generate_graphs(n)]))

    # third object domain: permutation ensemble laws (discovered + structurally explained)
    from .permutations import discover_distribution_laws, discover_permutation_laws
    for law in discover_permutation_laws(6):
        if law.verified:
            empirical.append({"statement": law.statement, "status": "empirical",
                              "scope": "permutations S_n (n≤6)", "support": None})
            explanations.append({"identity": law.statement,
                                 "explains": "over all permutations of [n]",
                                 "reason": law.explanation, "status": "structural_argument",
                                 "verified": True})
    from .bijections import certify_mahonian_bijection
    _foata = certify_mahonian_bijection(7)                   # Foata's Φ: inv(Φ)=maj (Mahonian)
    for dl in discover_distribution_laws(7):                 # Mahonian / Eulerian distribution facts
        if dl.verified:
            empirical.append({"statement": dl.statement, "status": "empirical",
                              "scope": "permutations S_n (n≤7), distribution-level", "support": None})
            if "Mahonian" in dl.statement and _foata.verified:   # upgraded to a verified bijection
                explanations.append({
                    "identity": dl.statement, "explains": "the distribution over S_n",
                    "reason": f"{dl.explanation} — {_foata.detail} (constructive_bijection, verified "
                              f"n≤{_foata.holds_upto})",
                    "status": "constructive_bijection", "verified": True})
            else:
                explanations.append({"identity": dl.statement, "explains": "the distribution over S_n",
                                     "reason": dl.explanation, "status": "structural_argument",
                                     "verified": True})

    # fourth object domain: integer partition facts (Euler's distinct=odd, conjugation), upgraded to
    # CONSTRUCTIVE BIJECTIONS where the explicit bijection is verified on the sample
    from .bijections import certify_partition_bijections
    from .partitions import discover_partition_laws
    _bijections = {("Euler" if "Euler" in c.theorem else "conjugation"): c
                   for c in certify_partition_bijections(15)}
    for pl in discover_partition_laws(15):
        if pl.verified:
            empirical.append({"statement": pl.statement, "status": "empirical",
                              "scope": "partitions of n (n≤15)", "support": None})
            key = "Euler" if "Euler" in pl.statement else "conjugation"
            cert = _bijections.get(key)
            if cert and cert.verified:                   # explicit bijection exhibited + re-checked
                explanations.append({
                    "identity": pl.statement, "explains": "over partitions of n",
                    "reason": f"{pl.explanation} — {cert.detail} (constructive_bijection, verified "
                              f"n≤{cert.holds_upto})",
                    "status": "constructive_bijection", "verified": True})
            else:
                explanations.append({"identity": pl.statement, "explains": "over partitions of n",
                                     "reason": pl.explanation, "status": "structural_argument",
                                     "verified": True})

    # fifth object domain: set partitions (Bell numbers, Stirling 2nd kind)
    from .set_partitions import discover_set_partition_laws
    for sl in discover_set_partition_laws(8):
        if sl.verified:
            empirical.append({"statement": sl.statement, "status": "empirical",
                              "scope": "set partitions of [n] (n≤8)", "support": None})
            explanations.append({"identity": sl.statement, "explains": "over set partitions of [n]",
                                 "reason": sl.explanation, "status": "structural_argument",
                                 "verified": True})

    for s in run_sequence_discovery():
        stmt = f"sum_(i=1..n) {s.term} = {s.closed_form}"
        if s.verdict == "proved":
            proved.append({"statement": stmt, "status": "proved", "certainty": s.certainty,
                           "independently_verified": s.independently_verified,
                           "kernel_verified": s.kernel_verified,
                           "proof_hash": s.proof_hash, "axioms": list(s.axioms)})
        elif s.verdict == "refuted":
            refuted.append({"statement": stmt, "status": "refuted",
                            "counterexample": {"note": "not a polynomial identity"}})
        else:
            open_bounded.append({"statement": stmt, "status": "unknown"})

    from mathhead.guardrails import MAX_STATEMENTS  # noqa: F401  (touch to assert import health)
    from .failure_memory import FailureMemory, populate_from_refutations
    from .provenance import KERNEL_VERSION
    kernel_axioms = sorted({a for it in proved for a in it.get("axioms", [])})

    # negative knowledge (Track Y): fold the refutations into a failure memory + reusable lessons
    memory = FailureMemory()
    populate_from_refutations(
        memory, [(x["statement"], {"status": "refuted",
                                   "counterexample": x.get("counterexample", {})}) for x in refuted])
    top_lesson = memory.lessons()[0] if memory.lessons() else None
    meta = {
        "mathhead_version": getattr(mathhead, "__version__", "?"),
        "solver_seed": 42,
        "graph_bound_n": max_n,
        "determinism": "memoized generation + fixed seed -> same report every run",
        "kernel_version": KERNEL_VERSION,
        "kernel_axioms": kernel_axioms,   # every rule/primitive the kernel proofs rest on (M5)
        "dead_ends": len(memory.records()),                 # negative knowledge recorded (Y)
        "top_lesson": top_lesson,         # the witness that refutes the most conjectures (Y2)
    }

    # interestingness ranking across all buckets (Track W1) — heuristic, transparent
    from .interestingness import rank
    all_items = proved + empirical + refuted + open_bounded
    meta["most_interesting"] = [{"statement": s.statement, "score": s.total}
                                for s, _ in rank(all_items)[:5]]
    report = DiscoveryReport(proved, empirical, refuted, open_bounded,
                             _frontier_confirmations(), meta, explanations)
    from .epistemic_ladder import ladder_summary                  # 4-rung solidity axis (AA3)
    from .evaluation import evaluate                              # honest scorecard (AF)
    from .impact import impact_summary                            # structural impact analysis (X3)
    from .knowledge_graph import from_report as _kg_from_report   # semantic graph of findings (X0)
    _kg = _kg_from_report(report)
    report.meta["knowledge_graph"] = _kg.summary()
    report.meta["impact"] = impact_summary(_kg)
    report.meta["ladder"] = ladder_summary(report)
    _card = evaluate(report)
    report.meta["scorecard"] = {
        "total": _card.total, "verified": _card.verified,
        "attributed_known": _card.attributed_known, "novel_established": 0,
        "unattributed": len(_card.unattributed)}
    from .analogy import find_analogies                            # cross-domain analogies (P4)
    report.meta["analogies"] = [
        {"technique": a.technique, "domains": list(a.domains)} for a in find_analogies(report)]
    return report


def render(report: DiscoveryReport) -> str:
    """Render the report as readable Markdown."""
    lines = ["# MathHead — Discovery Run Report", ""]
    lines.append(f"_MathHead {report.meta.get('mathhead_version')} · seed "
                 f"{report.meta.get('solver_seed')} · graphs n≤{report.meta.get('graph_bound_n')} "
                 f"· {report.meta.get('determinism')}_")
    if report.meta.get("kernel_axioms"):
        lines.append(f"_kernel v{report.meta.get('kernel_version')} · axioms: "
                     f"{', '.join(report.meta['kernel_axioms'])}_")
    if report.meta.get("dead_ends"):
        lesson = report.meta.get("top_lesson") or {}
        extra = (f"; top witness refutes {lesson['refutes']}" if lesson.get("refutes", 0) > 1 else "")
        lines.append(f"_negative knowledge: {report.meta['dead_ends']} dead end(s) recorded{extra}_")
    kg = report.meta.get("knowledge_graph")
    if kg:
        lines.append(f"_knowledge graph: {kg['nodes']} nodes · {kg['edges']} edges "
                     f"({', '.join(f'{k}×{v}' for k, v in sorted(kg['by_kind'].items()))})_")
    impact = report.meta.get("impact")
    if impact and impact.get("load_bearing_axioms"):
        lb = impact["load_bearing_axioms"][0]
        lines.append(f"_impact: most load-bearing axiom `{lb['axiom']}` supports {lb['supports']} "
                     f"theorems_")
    ladder = report.meta.get("ladder")
    if ladder:
        lines.append("_solidity (AA3): " + " · ".join(f"{k}={v}" for k, v in ladder.items()) + "_")
    lines.append("")

    def section(title, items, fmt):
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append("_none_")
        for it in items:
            lines.append(f"- {fmt(it)}")
        lines.append("")

    top = report.meta.get("most_interesting") or []
    if top:
        lines.append("## MOST INTERESTING (heuristic ranking — Track W1, not a learned measure)")
        for it in top:
            lines.append(f"- {it['score']:.3f} · `{it['statement']}`")
        lines.append("")

    section("PROVED (formal — by the judge)", report.proved,
            lambda it: f"`{it['statement']}` — {it.get('certainty', '')}"
                       + ("  ✓ independently verified" if it.get("independently_verified") else "")
                       + (f"  ⊢ kernel-verified [{it['proof_hash']}]" if it.get("kernel_verified")
                          else ""))
    section("REFUTED (killed, with a minimal counterexample)", report.refuted,
            lambda it: f"`{it['statement']}` — counterexample: {it.get('counterexample', {})}")
    section("DISCOVERED (empirical — holds on the sample, NOT proven)", report.empirical_laws,
            lambda it: f"`{it['statement']}` — {it.get('scope', '')} (support {it.get('support', '?')})")
    section("OPEN (survived the attack; unproven — no_counterexample_within_bound)", report.open_bounded,
            lambda it: f"`{it['statement']}` — {it.get('note', it.get('status', ''))}")
    section("FRONTIER (NP-hard invariant VALUES — independently confirmed by MathHead's solver)",
            report.frontier,
            lambda it: f"{it['invariant']}({it['graph']}) = {it['value']} — "
                       f"{'✓ confirmed' if it.get('confirmed') else '✗ UNCONFIRMED'} "
                       f"({it.get('certainty', '')}; {it.get('method', '')})")
    section("EXPLANATIONS (structure explaining a result — kernel-verified factorization)",
            report.explanations,
            lambda it: f"`{it['identity']}` explains `{it['explains']}` — {it['reason']}")
    analogies = report.meta.get("analogies")
    if analogies:
        lines.append("## CROSS-DOMAIN ANALOGIES (same proof technique across domains — Track P3)")
        for a in analogies:
            lines.append(f"- **{a['technique']}** spans: {', '.join(a['domains'])}")
        lines.append("")
    sc = report.meta.get("scorecard")
    if sc:
        lines.append("## HONEST SCORECARD (Track AF — is any of this NEW?)")
        lines.append(f"- {sc['total']} findings · {sc['verified']} verified · "
                     f"{sc['attributed_known']} attributable to KNOWN mathematics · "
                     f"**{sc['novel_established']} novel-to-literature established**")
        lines.append("- _the engine correctly REDISCOVERS known mathematics; novelty vs. the "
                     "literature is not established (needs corpus ingestion, X1/W2 — not built)_")
        lines.append("")
    return "\n".join(lines)
