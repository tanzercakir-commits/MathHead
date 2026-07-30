"""
mathhead.discovery.candidate_hunt — the HONEST hunt for unattributed candidates (roadmap AE2).

AE2's goal is stated ambitiously ("produce ≥1 correct, interesting lemma NOT in the literature"). This
module does the ONLY honest version of that: it casts a wide net (the miners over many graph families and
the all-graphs sample), attributes every finding against the engine's known-results catalog, and surfaces
the ones the catalog CANNOT place — as CANDIDATES for scrutiny, never as discoveries.

READ THIS CAVEAT — it is the point of the module, not boilerplate:
  * "unattributed" here means "not matched by the engine's ~21-entry catalog". That catalog is tiny; the
    territory (small graphs, elementary invariants) is among the most exhaustively mapped in mathematics.
  * An unattributed candidate is therefore almost certainly a KNOWN result the catalog simply lacks a
    marker for (e.g. a family-specific closed form, or an algebraic consequence of a listed law).
  * GENUINE novelty-vs-literature cannot be decided here. It needs a real corpus (X1, not built) AND
    human expert review. This module NEVER claims novelty; it produces a to-scrutinise list.

So a non-empty result is a prompt for skepticism, not a celebration. An empty result (everything
attributed) is an equally honest outcome — the engine confirming it walks well-trodden ground.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .evaluation import attribute
from .families import complete, complete_bipartite, cycle, path, star, wheel
from .generate import generate_graphs
from .nonlinear_relations import discover_polynomial_laws
from .relations import discover_linear_laws
from .trivial_filter import nontrivial_ratios

_CAVEAT = (
    "UNATTRIBUTED = not in the engine's ~21-entry catalog, NOT novel-to-literature. This territory is "
    "elementary and exhaustively mapped; each candidate is almost certainly a known result the catalog "
    "lacks a marker for. Genuine novelty needs a real corpus (X1, unbuilt) + human review. NOT a claim.")


@dataclass
class HuntResult:
    explored: int = 0
    attributed: int = 0
    candidates: list = field(default_factory=list)     # (statement, scope) unattributed-in-catalog
    caveat: str = _CAVEAT

    @property
    def all_attributed(self) -> bool:
        return not self.candidates


def _family_samples(max_size: int = 8) -> list:
    """(label, graphs) for several parametric families — a broader net than the all-graphs sample."""
    fams = [("complete", [complete(n) for n in range(2, max_size)]),
            ("cycle", [cycle(n) for n in range(3, max_size)]),
            ("path", [path(n) for n in range(2, max_size)]),
            ("star", [star(n) for n in range(2, max_size)]),
            ("wheel", [wheel(n) for n in range(4, max_size)]),
            ("bipartite", [complete_bipartite(a, b) for a in range(1, 4) for b in range(a, 5)])]
    return fams


def hunt(max_n: int = 6) -> HuntResult:
    """Cast the wide net, attribute everything, and collect the unattributed-in-catalog candidates."""
    findings = []   # (statement, scope)

    allg = [g for n in range(max_n + 1) for g in generate_graphs(n)]
    for law in discover_polynomial_laws(allg):                      # degree-2, universal over all graphs
        findings.append((law.expression, f"all graphs n<={max_n} (degree-2)"))

    for label, sample in _family_samples():
        for law in discover_linear_laws(sample, holds_over=label):
            findings.append((law.expression, f"{label} family"))
        for rp in nontrivial_ratios(sample):                        # junk-filtered ratios
            findings.append((f"{rp.numerator}/{rp.denominator} = {rp.ratio}", f"{label} family"))

    # dedup identical (statement, scope) pairs, deterministic order
    seen, uniq = set(), []
    for st, sc in findings:
        if (st, sc) not in seen:
            seen.add((st, sc))
            uniq.append((st, sc))
    uniq.sort()

    attributed = sum(1 for st, _ in uniq if attribute(st) is not None)
    candidates = [(st, sc) for st, sc in uniq if attribute(st) is None]
    return HuntResult(explored=len(uniq), attributed=attributed, candidates=candidates)
