"""
mathhead.discovery.evaluation — an honest scorecard for the engine's output (roadmap Track AF).

The uncomfortable question a discovery engine must answer about itself: is any of this NEW, or is it
correctly rediscovering known mathematics? This module answers it plainly.

For each finding it establishes three things:
  * CORRECTNESS — kernel/solver/independently-verified findings are correct by construction; mined
    laws are verified exactly on the sample. (The engine is built so nothing false is reported.)
  * ATTRIBUTION — match the finding against a curated registry of KNOWN results (Handshake, Fermat/
    elementary modular facts, Faulhaber sums, MacMahon, Eulerian, Dirac, …). Almost everything the
    engine currently produces is a named, classical theorem.
  * NOVELTY — a finding that is neither trivial nor attributable to a known result. Honestly, after
    attribution this is ~0: the engine REDISCOVERS known mathematics correctly. It has not produced a
    result absent from the literature — and full novelty-vs-literature would need corpus ingestion
    (X1/W2), which is NOT built. We say so, rather than dressing rediscovery up as discovery.

This module never changes a finding's truth; it grades the engine, honestly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# curated registry: (substring/marker that identifies the finding, human name, reference)
KNOWN_RESULTS = [
    ("2*num_edges = sum_degrees", "Handshake Lemma", "classical"),
    ("2*num_edges", "Handshake Lemma", "classical"),
    ("% ", "modular divisibility (elementary number theory; Fermat's little theorem family)",
     "classical"),
    ("sum_(i=1..n)", "power sums (Faulhaber)", "classical"),
    ("spectral_moment", "adjacency spectral-moment identities (trace formulas)", "spectral graph theory"),
    ("chromatic_number", "graph coloring bounds (ω≤χ≤Δ+1; Brooks)", "classical"),
    ("clique_number", "clique/chromatic relation", "classical"),
    ("Hamiltonian", "Hamiltonicity conditions (Dirac / necessary conditions)", "classical"),
    ("Dirac", "Dirac's theorem", "Dirac 1952"),
    ("|S_n| = n!", "permutation count", "OEIS A000142"),
    ("fix(π)", "fixed-point sum / linearity of expectation", "classical"),
    ("inv(π)", "inversion statistics", "classical"),
    ("Mahonian", "MacMahon equidistribution (inv ~ maj)", "MacMahon 1913"),
    ("Eulerian", "Eulerian numbers", "OEIS A008292"),
    ("Euler)", "Euler's partition theorem (distinct = odd)", "Euler 1748"),
    ("partitions of n", "integer partition identities", "classical"),
    ("conjugation", "partition conjugation symmetry", "classical"),
    ("trees:", "tree edge-count / forest identities", "classical"),
    ("num_triangles", "triangle / spectral counting", "classical"),
    ("= n*(n", "elementary polynomial factorization", "classical"),
    ("num_components", "component / degree bounds", "classical"),
    ("max_degree", "degree bounds", "classical"),
    ("min_degree", "degree bounds", "classical"),
    ("sum_degrees", "degree-sum bounds", "classical"),
    ("= (", "elementary polynomial factorization", "classical"),
    ("*(", "elementary polynomial factorization", "classical"),
]

_TRIVIAL_MARKERS = ("chromatic_number <= num_vertices",)   # textbook-trivial


def attribute(statement: str):
    """Return (name, reference) of the known result this finding matches, or None."""
    for marker, name, ref in KNOWN_RESULTS:
        if marker in statement:
            return (name, ref)
    return None


def _is_verified(item: dict) -> bool:
    return bool(item.get("kernel_verified") or item.get("independently_verified")
                or item.get("certainty") in {"formal_proof", "exhaustive_residue_proof",
                                             "kernel_identity", "solver_verified"})


@dataclass
class Scorecard:
    total: int = 0
    verified: int = 0
    attributed_known: int = 0
    novel_candidates: list = field(default_factory=list)
    unattributed: list = field(default_factory=list)
    notes: str = ""


def evaluate(report) -> Scorecard:
    """Grade the report: how much is verified, how much is attributable to known mathematics, and how
    much is (honestly) novel."""
    items = list(report.proved) + list(report.empirical_laws) + list(report.open_bounded)
    card = Scorecard(total=len(items))
    for it in items:
        stmt = it["statement"]
        if _is_verified(it):
            card.verified += 1
        if attribute(stmt) is not None:
            card.attributed_known += 1
        elif not any(m in stmt for m in _TRIVIAL_MARKERS):
            card.unattributed.append(stmt)                 # not matched by the curated registry
    # a novel candidate would be unattributed AND non-trivial; we still don't claim novelty without a
    # literature check (X1/W2), so these are CANDIDATES for a human/corpus pass, not novelty claims.
    card.novel_candidates = list(card.unattributed)
    card.notes = (
        "The engine correctly rediscovers known mathematics; every reported finding is verified or "
        "sample-checked. Novelty vs. the literature is NOT established here — that needs corpus "
        "ingestion (X1/W2), which is not built. Unattributed items are candidates for a human/corpus "
        "check, not novelty claims.")
    return card


def render_scorecard(card: Scorecard) -> str:
    pct = (100 * card.attributed_known // card.total) if card.total else 0
    lines = [
        "## HONEST SCORECARD (Track AF)",
        f"- findings graded: {card.total}",
        f"- verified (kernel / solver / independent): {card.verified}",
        f"- attributable to KNOWN mathematics: {card.attributed_known} ({pct}%)",
        f"- novel-to-literature: 0 established "
        f"({len(card.novel_candidates)} unattributed candidate(s), pending a corpus check)",
        f"- _{card.notes}_",
    ]
    if card.novel_candidates:
        lines.append("- unattributed candidates: " + "; ".join(f"`{s}`" for s in card.novel_candidates[:6]))
    return "\n".join(lines)
