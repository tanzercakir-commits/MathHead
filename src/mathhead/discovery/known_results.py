"""
mathhead.discovery.known_results — a structured catalog of the KNOWN mathematics the engine touches
(roadmap X1/W2, the honest-novelty substrate).

The scorecard's earlier attribution was a flat substring list; this makes it a structured, cited,
extensible KNOWLEDGE BASE. Each entry names the theorem, its reference (author-year or OEIS), the
domain, and the markers that identify a matching finding. Attribution against this catalog is how the
engine decides a finding is "known" — and therefore how it honestly concludes it has found nothing
NOVEL. A real literature corpus would extend this catalog; the honest verdict does not change until
one is ingested.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnownResult:
    name: str
    reference: str
    domain: str
    markers: tuple          # substrings that identify a matching finding statement


CATALOG = (
    # graphs
    KnownResult("Handshake Lemma", "classical", "graphs", ("2*num_edges = sum_degrees", "2·|E|")),
    KnownResult("adjacency spectral-moment (trace) identities", "spectral graph theory", "graphs",
                ("spectral_moment",)),
    KnownResult("graph coloring bounds (ω≤χ≤Δ+1; Brooks)", "classical", "graphs",
                ("chromatic_number", "clique_number")),
    KnownResult("Hamiltonicity conditions (Dirac; necessary conditions)", "Dirac 1952", "graphs",
                ("Hamiltonian", "Dirac")),
    KnownResult("degree / component bounds", "classical", "graphs",
                ("max_degree", "min_degree", "num_components", "sum_degrees")),
    KnownResult("triangle / spectral counting", "classical", "graphs", ("num_triangles",)),
    KnownResult("tree edge-count / forest identities", "classical", "graphs", ("trees:",)),
    # arithmetic
    KnownResult("modular divisibility (Fermat's little theorem family)", "classical", "arithmetic",
                ("% ",)),
    KnownResult("power sums (Faulhaber)", "Faulhaber 1631", "arithmetic", ("sum_(i=1..n)",)),
    KnownResult("elementary polynomial factorization", "classical", "arithmetic", ("= (", "*(")),
    # permutations
    KnownResult("permutation count n!", "OEIS A000142", "permutations", ("|S_n| = n!",)),
    KnownResult("fixed-point sum (linearity of expectation)", "classical", "permutations", ("fix(π)",)),
    KnownResult("inversion statistics", "classical", "permutations", ("inv(π)",)),
    KnownResult("MacMahon equidistribution (inv ~ maj)", "MacMahon 1913", "permutations", ("Mahonian",)),
    KnownResult("Eulerian numbers", "OEIS A008292", "permutations", ("Eulerian",)),
    # integer partitions
    KnownResult("Euler's partition theorem (distinct = odd)", "Euler 1748", "integer partitions",
                ("Euler)",)),
    KnownResult("integer partition identities", "classical", "integer partitions", ("partitions of n",)),
    KnownResult("partition conjugation symmetry", "classical", "integer partitions", ("conjugation",)),
    # set partitions
    KnownResult("Bell numbers", "OEIS A000110", "set partitions", ("Bell numbers",)),
    KnownResult("Stirling numbers of the 2nd kind", "OEIS A008277", "set partitions", ("Stirling",)),
    KnownResult("set-partition enumeration", "classical", "set partitions", ("set partitions",)),
)


def attribute(statement: str) -> KnownResult | None:
    """The known result this finding matches, or None (an unattributed candidate)."""
    for kr in CATALOG:
        if any(m in statement for m in kr.markers):
            return kr
    return None


def catalog_size() -> int:
    return len(CATALOG)


def domains() -> tuple:
    return tuple(sorted({kr.domain for kr in CATALOG}))


def attributed_findings(report) -> list:
    """Every finding paired with the known result it matches (name + reference + domain) — the
    auditable basis for the scorecard's 'rediscovery, not discovery' verdict."""
    items = list(report.proved) + list(report.empirical_laws) + list(report.open_bounded)
    out = []
    for it in items:
        kr = attribute(it["statement"])
        out.append({
            "statement": it["statement"],
            "kernel_verified": bool(it.get("kernel_verified")),
            "certainty": it.get("certainty", ""),
            "known": kr.name if kr else None,
            "reference": kr.reference if kr else "—",
            "domain": kr.domain if kr else "unattributed",
        })
    return out
