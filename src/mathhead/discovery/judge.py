"""
mathhead.discovery.judge — the judge bridge (roadmap: discovery ↔ MathHead, the "kernel certifies").

This is the first real use of MathHead as the discovery engine's JUDGE. Track Q produces
conjectures that survive a bounded counterexample search — but a survivor is only
`no_counterexample_within_bound`, never proven. This module hands the algebraically-expressible
ones to MathHead for an actual verdict, upgrading the epistemic status:

    empirical / no_counterexample_within_bound   ─judge→   proved | refuted | unknown

MathHead does the real work — a formal proof by induction (`certainty=formal_proof`), a Z3
decision (`solver_verified`), a domain-aware equality check — and returns a witness when it
refutes. The `Verdict` carries MathHead's own certainty label, so we never overstate.

HONESTY: not every conjecture is judgeable this way. A purely combinatorial graph law
(e.g. the Handshake Lemma) is not expressible in MathHead's algebraic grammar, so `judge`
returns `not_applicable` for it rather than pretending. The judge is for the reducible ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from mathhead.router import route


@dataclass
class Verdict:
    status: str                   # "proved" | "refuted" | "unknown" | "not_applicable"
    certainty: str                # MathHead's meta.certainty (formal_proof / solver_verified / ...)
    reason_code: str
    detail: dict = field(default_factory=dict)   # witness / counterexample when refuted
    source_status: str = ""       # the raw MathHead status
    engine: str = "mathhead"


def _to_verdict(result) -> Verdict:
    """Map a MathHead result (valid/invalid/unknown/error) to a Verdict, carrying its certainty."""
    s = getattr(result, "status", "error")
    mapped = {"valid": "proved", "invalid": "refuted"}.get(s, "unknown")
    detail = {}
    witness = getattr(result, "witness", None)
    if witness:
        detail["counterexample" if mapped == "refuted" else "witness"] = witness
    return Verdict(
        status=mapped,
        certainty=(getattr(result, "meta", {}) or {}).get("certainty", "unknown"),
        reason_code=getattr(result, "reason_code", ""),
        detail=detail,
        source_status=s,
    )


def judge_task(task: str, payload: dict) -> Verdict:
    """Submit an arbitrary MathHead task to the judge and get a Verdict."""
    return _to_verdict(route(task, payload))


def judge_induction(claim: str, var: str = "n", start: int = 0) -> Verdict:
    """Prove `∀ {var} ≥ {start}. {claim}` by induction (MathHead). E.g. '(n*(n+1)) % 2 == 0'."""
    return judge_task("prove_by_induction", {"claim": claim, "var": var, "start": start})


def judge_inequality(goal: str, assumptions=None) -> Verdict:
    """Prove/refute a (nonlinear real) inequality over ALL reals (MathHead Z3 NRA). Refutation
    carries a counterexample."""
    return judge_task("prove_inequality", {"goal": goal, "assumptions": assumptions})


def judge_identity(a: str, b: str) -> Verdict:
    """Prove/refute that two expressions are equal (MathHead, domain-aware)."""
    return judge_task("verify_equality", {"left": a, "right": b})


def judge_entailment(premises, conclusion: str) -> Verdict:
    """Prove/refute that premises entail a conclusion (MathHead FOL)."""
    return judge_task("entailment", {"premises": list(premises), "conclusion": conclusion})


def judge(conjecture) -> Verdict:
    """Judge a discovery Conjecture. If it carries a `mathhead` task (it is algebraically
    expressible) submit it; otherwise return `not_applicable` — the honest answer for a purely
    combinatorial law, not a fabricated verdict."""
    task = getattr(conjecture, "mathhead", None)
    if not task:
        return Verdict(
            "not_applicable", "not_applicable", "OUT_OF_GRAMMAR",
            {"note": "not expressible in MathHead's algebraic grammar; needs a structural proof"},
        )
    return judge_task(task["task"], task["payload"])
