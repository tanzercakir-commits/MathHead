"""
mathhead.discovery.analogy — cross-domain analogy detection (roadmap Track P3).

With five domains and a rich explanation layer, the engine can notice when the SAME proof technique
recurs across genuinely different objects — a modest, honest step toward "understanding" rather than
mere collection. It tags each explained finding with its technique (double counting, constructive
bijection, recurrence, factorization, …) and reports the techniques that span two or more domains.

This is structural pattern-matching over the explanation texts the engine already produced, and it is
labelled as such — it claims a shared PROOF SHAPE, not a deep equivalence. But the shapes it surfaces
are real: double counting underlies both the Handshake Lemma (graphs) and Σ fix(π)=n! (permutations);
a constructive bijection proves Euler (partitions), Mahonian (permutations), and conjugation.
"""
from __future__ import annotations

from dataclasses import dataclass


def _technique(item: dict) -> str | None:
    text = f"{item.get('reason','')} {item.get('identity','')} {item.get('statement','')}".lower()
    if item.get("status") == "constructive_bijection" or "bijection" in text:
        return "constructive bijection"
    if "double counting" in text or "double count" in text:
        return "double counting"
    if "recurrence" in text:
        return "recurrence"
    if "consecutive integers" in text or "factoriz" in text:
        return "factorization"
    if "induction" in text:
        return "induction"
    return None


def _domain(item: dict) -> str:
    s = (f"{item.get('scope','')} {item.get('statement','')} {item.get('identity','')} "
         f"{item.get('explains','')}").lower()
    if any(w in s for w in ("graph", "chromatic", "hamilton", "num_edges", "num_vertices",
                            "deg", "clique", "handshake")):
        return "graphs"
    if any(w in s for w in ("s_n", "permutation", "inv", "maj", "π")):
        return "permutations"
    if "set partition" in s or "bell" in s or "stirling" in s:
        return "set partitions"
    if "partition" in s:
        return "integer partitions"
    if "%" in s or "sum_(" in s or "= n" in s or " mod " in s:
        return "arithmetic"
    return "other"


@dataclass
class Analogy:
    technique: str
    domains: tuple          # the distinct domains this technique appears in
    instances: list         # (domain, statement) pairs


def find_analogies(report) -> list:
    """Techniques that recur across TWO OR MORE domains — the cross-domain analogies."""
    items = list(getattr(report, "explanations", [])) + list(report.empirical_laws)
    by_technique: dict = {}
    for it in items:
        tech = _technique(it)
        if tech is None:
            continue
        dom = _domain(it)
        stmt = it.get("identity") or it.get("statement", "")
        by_technique.setdefault(tech, []).append((dom, stmt))

    analogies = []
    for tech, insts in by_technique.items():
        domains = tuple(sorted({d for d, _ in insts}))
        if len(domains) >= 2:                       # spans multiple domains ⇒ an analogy
            # one representative statement per domain, for readability
            seen, reps = set(), []
            for d, s in insts:
                if d not in seen:
                    seen.add(d)
                    reps.append((d, s))
            analogies.append(Analogy(tech, domains, reps))
    analogies.sort(key=lambda a: (-len(a.domains), a.technique))
    return analogies
