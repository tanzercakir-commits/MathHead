"""
mathhead.discovery.oeis_radar — natural-family sequence extraction + the OEIS radar (v2A0/A1/A2).

The lowest honest bar for a REAL discovery: a natural counting sequence, produced by a natural
construction, that is absent from the OEIS — submitted by a human, accepted by OEIS referees. The
acceptance IS the external validation (the same honesty channel as a self-verifying counterexample).

Three layers, all deterministic:
  * v2A1 EXTRACTION — `extract_natural_sequences()` computes counting sequences FROM THE ENGINE'S OWN
    generators (never hardcoded): per-domain totals (graphs, permutations, partitions, distinct
    partitions, Bell, compositions) and REFINED families (connected graphs, triangle-free graphs,
    derangements, involutions, graphs with χ=k …) — refined slices are where radar candidates live.
  * v2A0 LOOKUP — `LOCAL_CORPUS` holds OEIS prefixes already pinned/trusted in this codebase plus a few
    bulletproof classics; `match()` is prefix containment with a minimum overlap (≥5 terms) so junk
    can't match. This container cannot query oeis.org at runtime; anything unmatched is honestly marked
    `pending_external_lookup` — a QUERY TO RUN, never a discovery claim.
  * v2A2 RADAR — `radar()` splits extractions into matched (attributed, with A-number) vs pending. The
    pending report states the full path explicitly: external OEIS query → if absent, HUMAN-approved
    submission → referee acceptance = the discovery; anything short of that is nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .compositions import count_compositions
from .generate import generate_graphs
from .invariants import chromatic_number, evaluate
from .partitions import count_partitions, generate_partitions, into_distinct_parts
from .permutations import generate_permutations
from .set_partitions import count_set_partitions


@dataclass
class NaturalSequence:
    name: str
    domain: str
    description: str
    offset: int                 # index of the first term (OEIS convention)
    terms: tuple


# --- v2A0: the local corpus (prefixes pinned/trusted in this codebase + bulletproof classics) ----
LOCAL_CORPUS: dict = {
    "A000088": ("graphs on n nodes", (1, 1, 2, 4, 11, 34, 156, 1044)),
    "A000142": ("factorial n!", (1, 1, 2, 6, 24, 120, 720, 5040)),
    "A000041": ("partitions p(n)", (1, 1, 2, 3, 5, 7, 11, 15, 22, 30, 42)),
    "A000009": ("partitions into distinct parts", (1, 1, 1, 2, 2, 3, 4, 5, 6, 8, 10)),
    "A000110": ("Bell numbers", (1, 1, 2, 5, 15, 52, 203, 877)),
    "A011782": ("compositions 2^(n-1)", (1, 1, 2, 4, 8, 16, 32, 64, 128)),
    "A001349": ("connected graphs on n nodes", (1, 1, 1, 2, 6, 21, 112)),
    "A000166": ("derangements", (1, 0, 1, 2, 9, 44, 265, 1854)),
    "A000085": ("involutions", (1, 1, 2, 4, 10, 26, 76, 232)),
}

_MIN_OVERLAP = 5    # a match needs at least this many agreeing leading terms — junk can't sneak in


def match(seq: NaturalSequence):
    """A-number whose corpus prefix agrees with the sequence on ≥ _MIN_OVERLAP leading terms, or None."""
    for anum, (_name, prefix) in sorted(LOCAL_CORPUS.items()):
        k = min(len(prefix), len(seq.terms))
        if k >= _MIN_OVERLAP and tuple(seq.terms[:k]) == tuple(prefix[:k]):
            return anum
    return None


# --- v2A1: extraction from the engine's OWN generators (never hardcoded) -------------------------
def _graphs_upto(n_max: int) -> list:
    return [[g for g in generate_graphs(n)] for n in range(n_max + 1)]


def extract_natural_sequences(graph_n: int = 6, perm_n: int = 7, part_n: int = 10) -> list:
    """Counting sequences computed from the engine's generators — totals + refined families."""
    by_n = _graphs_upto(graph_n)
    perms = [list(generate_permutations(n)) for n in range(perm_n + 1)]
    out = [
        NaturalSequence("graphs", "graphs", "non-isomorphic simple graphs on n nodes", 0,
                        tuple(len(gs) for gs in by_n)),
        NaturalSequence("connected_graphs", "graphs", "connected graphs on n nodes", 0,
                        tuple(sum(1 for g in gs if evaluate(g, "num_components") <= 1) for gs in by_n)),
        NaturalSequence("triangle_free_graphs", "graphs", "triangle-free graphs on n nodes", 0,
                        tuple(sum(1 for g in gs if evaluate(g, "num_triangles") == 0) for gs in by_n)),
        NaturalSequence("chromatic_3_graphs", "graphs", "graphs on n nodes with chromatic number 3", 0,
                        tuple(sum(1 for g in gs if chromatic_number(g) == 3) for gs in by_n)),
        NaturalSequence("permutations", "permutations", "permutations of [n]", 0,
                        tuple(len(ps) for ps in perms)),
        NaturalSequence("derangements", "permutations", "permutations of [n] with no fixed point", 0,
                        tuple(sum(1 for p in ps if all(p.perm[i] != i for i in range(len(p.perm))))
                              for ps in perms)),
        NaturalSequence("involutions", "permutations", "permutations with p*p = identity", 0,
                        tuple(sum(1 for p in ps
                                  if all(p.perm[p.perm[i]] == i for i in range(len(p.perm))))
                              for ps in perms)),
        NaturalSequence("partitions", "integer partitions", "partitions of n", 0,
                        tuple(count_partitions(n) for n in range(part_n + 1))),
        NaturalSequence("distinct_partitions", "integer partitions", "partitions into distinct parts", 0,
                        tuple(sum(1 for p in generate_partitions(n) if into_distinct_parts(p))
                              for n in range(part_n + 1))),
        NaturalSequence("set_partitions", "set partitions", "set partitions of [n] (Bell)", 0,
                        tuple(count_set_partitions(n) for n in range(8))),
        NaturalSequence("compositions", "compositions", "compositions of n", 0,
                        tuple(count_compositions(n) for n in range(10))),
    ]
    return out


# --- v2A2: the radar ----------------------------------------------------------------------------
@dataclass
class RadarReport:
    matched: list = field(default_factory=list)    # (NaturalSequence, A-number)
    pending: list = field(default_factory=list)    # NaturalSequence — pending_external_lookup
    protocol: str = ("pending == a QUERY TO RUN against the real OEIS, nothing more. The path to a "
                     "discovery: external OEIS query -> if absent, HUMAN-approved submission -> referee "
                     "acceptance. Acceptance is the discovery; everything before it is a candidate.")


def radar(graph_n: int = 6, perm_n: int = 7, part_n: int = 10) -> RadarReport:
    """Split the extracted sequences into corpus-matched vs pending-external-lookup."""
    rep = RadarReport()
    for seq in extract_natural_sequences(graph_n, perm_n, part_n):
        anum = match(seq)
        (rep.matched.append((seq, anum)) if anum else rep.pending.append(seq))
    return rep
