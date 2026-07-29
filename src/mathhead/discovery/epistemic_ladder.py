"""
mathhead.discovery.epistemic_ladder — one principled "how solid is it?" axis (roadmap Track AA3).

The engine has accumulated a rich certainty vocabulary (empirical, bounded_check, numerical_check,
constructive_bounded, structural_argument, solver_verified, formal_proof, kernel_verified…). This
module collapses it onto the document's FOUR rungs, so every finding sits at one honest level:

  L1 DISCOVERED_HEURISTIC — mined from data, not yet attacked. Transient: in a finished report it is
     ~0 (everything reported has already been refute-tested), so its throughput is the raw conjecture
     count, reported separately.
  L2 EMPIRICALLY_VALIDATED — holds exactly over the sample / survived refutation, but NOT universally
     proven (mined laws, surviving bounds, structural arguments whose conclusion is checked).
  L3 FORMALLY_SPECIFIED — backed by a machine-checkable certificate on instances: a solver-confirmed
     invariant value, or a constructive certificate realizing a bound.
  L4 FORMALLY_PROVED — universally proven AND independently / kernel verified.

The ladder never changes a finding's truth — it just names, honestly and uniformly, how far up the
evidence goes. Refuted items are off-ladder (they are negative knowledge, Track Y).
"""
from __future__ import annotations

LEVELS = (
    "DISCOVERED_HEURISTIC",     # L1
    "EMPIRICALLY_VALIDATED",    # L2
    "FORMALLY_SPECIFIED",       # L3
    "FORMALLY_PROVED",          # L4
)

_FORMAL_CERTAINTIES = {
    "formal_proof", "exhaustive_residue_proof", "kernel_identity", "solver_verified_proof",
}


def _proved_rung(item: dict) -> str:
    """A PROVED-bucket item: L4 if it is universally proven and independently/kernel verified, else
    L3 (specified/solver-confirmed but not independently sealed)."""
    if item.get("kernel_verified") or item.get("independently_verified"):
        return "FORMALLY_PROVED"
    if item.get("certainty") in _FORMAL_CERTAINTIES:
        return "FORMALLY_PROVED"
    return "FORMALLY_SPECIFIED"


def classify(report) -> dict:
    """Assign every (non-refuted) finding to a rung. Returns {level: [statement, …]}."""
    out: dict = {lvl: [] for lvl in LEVELS}

    for it in report.proved:
        out[_proved_rung(it)].append(it["statement"])

    for it in getattr(report, "frontier", []):               # solver-confirmed invariant VALUES
        if it.get("confirmed"):
            out["FORMALLY_SPECIFIED"].append(f"{it['invariant']}({it['graph']})={it['value']}")

    for it in report.open_bounded:                           # survivors: L3 if constructively certified
        out["FORMALLY_SPECIFIED" if it.get("certified") else "EMPIRICALLY_VALIDATED"].append(
            it["statement"])

    for it in report.empirical_laws:                         # mined, hold on the sample
        out["EMPIRICALLY_VALIDATED"].append(it["statement"])

    for ex in getattr(report, "explanations", []):
        if ex.get("status") == "constructive_bijection":     # explicit bijection exhibited + verified
            out["FORMALLY_SPECIFIED"].append(ex["identity"])
        elif ex.get("status") == "structural_argument":      # conclusion-checked prose argument
            out["EMPIRICALLY_VALIDATED"].append(ex["identity"])

    return out


def ladder_summary(report) -> dict:
    """Counts per rung — the report's one-line 'solidity distribution'."""
    c = classify(report)
    return {lvl: len(c[lvl]) for lvl in LEVELS}


def rung_of(statement: str, report) -> str | None:
    """The rung a given statement sits at (or None if it isn't a non-refuted finding)."""
    c = classify(report)
    for lvl in reversed(LEVELS):                             # highest rung wins if it appears twice
        if statement in c[lvl]:
            return lvl
    return None
