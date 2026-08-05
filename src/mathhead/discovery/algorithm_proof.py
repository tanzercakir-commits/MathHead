"""
mathhead.discovery.algorithm_proof — connect a discovered ALGORITHM to the PROOF that certifies it
(roadmap AA4, the Track S/M bridge).

The engine discovers algorithms that DECIDE or CONSTRUCT (residue-exhaustion decides `m|p(n)`; greedy
first-fit colors a graph; a max-clique search witnesses ω). AA4 is the bridge that, for such an
algorithm's output, attaches the proof object that justifies it AND labels — honestly — the MODALITY and
STRENGTH of that justification. It does not re-prove anything; it LINKS the strategy/algorithm layer
(S, AA) to the proof layer (M, certificates), so every discovered algorithm carries its warrant:

  * a modular decision algorithm (residue-exhaustion / CRT) links to a KERNEL Theorem — modality
    "kernel", certainty `kernel_verified`: a universal, machine-checked ∀n proof (proof hash + axioms);
  * a greedy-coloring / max-clique algorithm links to a CONSTRUCTIVE CERTIFICATE — modality
    "certificate", certainty `constructive_bounded`: an explicit, independently re-checked witness over
    the sample, NOT a universal ∀G proof.

The bridge is honest about the gap between these two strengths: it never labels a graph certificate
`kernel_verified`, and it reports `verified=False` (not a fake proof) when the underlying check fails.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .graph_proofs import certify_chi_le_delta_plus_1, certify_omega_le_chi
from .kernel import KernelError, prove_divides
from .objects import Graph
from .provenance import axioms_used, proof_hash


@dataclass
class AlgorithmProof:
    algorithm: str              # the discovered procedure, e.g. "residue-exhaustion"
    claim: str                  # what its output asserts
    modality: str               # "kernel" | "certificate" — HOW it is justified
    certainty: str              # "kernel_verified" (universal) | "constructive_bounded" (witnessed)
                                # | "unproven" (the justification did NOT check out — never a tier)
    verified: bool              # the justification actually checked out
    evidence: dict = field(default_factory=dict)


def bridge_modular_algorithm(m: int, poly: tuple) -> AlgorithmProof:
    """Link the residue/CRT decision algorithm for `m | p(n)` to the KERNEL Theorem that proves it.
    certainty = kernel_verified (a universal ∀n machine proof) when the kernel accepts; else the link
    is verified=False with certainty="unproven" — the failure path never carries a proof tier's name
    (the algorithm reports the claim is not provable — no fabricated proof)."""
    claim = f"{m} | p(n) for all integers n"
    try:
        _thm, term = prove_divides(m, poly)
        return AlgorithmProof(
            "residue-exhaustion/CRT", claim, "kernel", "kernel_verified", True,
            {"proof_hash": proof_hash(term), "axioms": tuple(sorted(axioms_used(term))),
             "method": "modulus-factoring+CRT" if len(axioms_used(term)) > 1 else "residue-sweep"})
    except KernelError as exc:
        return AlgorithmProof(
            "residue-exhaustion/CRT", claim, "kernel", "unproven", False,
            {"reason": str(exc)})


def bridge_greedy_coloring(g: Graph) -> AlgorithmProof:
    """Link the greedy first-fit coloring algorithm to its constructive χ ≤ Δ+1 certificate."""
    cert = certify_chi_le_delta_plus_1(g)
    return AlgorithmProof(
        "greedy-first-fit-coloring", cert.law, "certificate", cert.certainty, cert.checked,
        {"colors_used": cert.witness.get("colors_used"), "argument": cert.argument,
         "graph_key": cert.graph_key})


def bridge_max_clique(g: Graph) -> AlgorithmProof:
    """Link the max-clique search algorithm to its constructive ω ≤ χ certificate (clique witness)."""
    cert = certify_omega_le_chi(g, solver_confirm=False)
    return AlgorithmProof(
        "max-clique-search", cert.law, "certificate", cert.certainty, cert.checked,
        {"omega": len(cert.witness.get("clique", ())), "argument": cert.argument,
         "graph_key": cert.graph_key})


def link_algorithm_to_proof(kind: str, **kwargs) -> AlgorithmProof:
    """Dispatch to the right bridge: kind='modular' (m, poly) | 'coloring' (g) | 'clique' (g)."""
    if kind == "modular":
        return bridge_modular_algorithm(kwargs["m"], kwargs["poly"])
    if kind == "coloring":
        return bridge_greedy_coloring(kwargs["g"])
    if kind == "clique":
        return bridge_max_clique(kwargs["g"])
    raise ValueError(f"unknown algorithm kind {kind!r}; known: modular, coloring, clique")
