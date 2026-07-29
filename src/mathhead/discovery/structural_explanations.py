"""
mathhead.discovery.structural_explanations — WHY the graph laws hold, structurally (explain, don't
just assert).

The linear-law miner DISCOVERS `2·|E| = Σ deg(v)` from data; the frontier miner finds `ω ≤ χ` and the
Hamiltonicity necessary conditions. This module attaches the classical STRUCTURAL argument behind
each — double counting, the pigeonhole-style clique bound, the cycle-degree argument — and verifies
the argument's conclusion on every sample graph.

HONEST status. Each is a `structural_argument`: a genuine universal argument stated in prose, whose
CONCLUSION is re-checked on the sample. The prose reasoning itself is not machine-checked (that would
need the graph side of the kernel, still future) — so we say "structural_argument", not "proved". It
is the graph-domain companion to the kernel-verified algebraic explanations in `identities.py`.
"""
from __future__ import annotations

from .invariants import chromatic_number, clique_number, is_hamiltonian, min_degree


def _incidence_double_count_ok(g) -> bool:
    """Verify the double count: Σ_v deg(v) and Σ_e 2 both count the incidences {(v,e): v ∈ e}."""
    incidences = sum(1 for e in g.edges for _endpoint in e)      # = 2·|E|
    return sum(g.degrees()) == incidences == 2 * g.num_edges


def explain_handshake(graphs) -> dict:
    checked = [g for g in graphs if g.n]
    ok = all(_incidence_double_count_ok(g) for g in checked)
    return {
        "identity": "2·|E| = Σ deg(v)",
        "explains": "the Handshake Lemma",
        "reason": ("double counting the incidences {(v,e): v ∈ e}: summing by vertex gives Σ deg(v), "
                   "summing by edge gives 2·|E| (each edge has two endpoints) — so they are equal; "
                   f"verified on {len(checked)} graphs"),
        "status": "structural_argument",
        "verified": ok,
    }


def explain_clique_chromatic(graphs) -> dict:
    ok = all(clique_number(g) <= chromatic_number(g) for g in graphs if g.n)
    return {
        "identity": "ω ≤ χ",
        "explains": "why a clique lower-bounds the chromatic number",
        "reason": ("the ω pairwise-adjacent vertices of a maximum clique must receive ω DISTINCT "
                   "colors in any proper coloring, so at least ω colors are needed: χ ≥ ω; "
                   "verified on the sample"),
        "status": "structural_argument",
        "verified": ok,
    }


def explain_hamiltonian_min_degree(graphs) -> dict:
    ham = [g for g in graphs if g.n and is_hamiltonian(g)]
    ok = all(min_degree(g) >= 2 for g in ham)
    return {
        "identity": "Hamiltonian ⟹ min_degree ≥ 2",
        "explains": "a necessary condition for a Hamiltonian cycle",
        "reason": ("a Hamiltonian cycle enters and leaves every vertex by two DISTINCT edges, so each "
                   f"vertex has degree ≥ 2; verified on {len(ham)} Hamiltonian graphs"),
        "status": "structural_argument",
        "verified": ok,
    }


def structural_explanations(graphs) -> list:
    """All graph-domain structural explanations over the sample (each with its conclusion verified)."""
    return [
        explain_handshake(graphs),
        explain_clique_chromatic(graphs),
        explain_hamiltonian_min_degree(graphs),
    ]
