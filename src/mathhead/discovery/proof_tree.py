"""
mathhead.discovery.proof_tree — expose the STRUCTURE of a proof (roadmap T3, a tractable slice).

A proof is not a yes/no; it rests on lemmas. This module reconstructs the proof-dependency tree of
an arithmetic finding from the strategy that proved it — no extra solver calls, deterministic:

  * modulus-factoring → the goal rests on one `≡ 0 (mod pᵢ^{eᵢ})` lemma per prime power (each proved
    by induction), combined by CRT;
  * residue-exhaustion → a single complete finite case-split (leaf);
  * induction (prime modulus) → a single inductive proof (leaf).

This is the honest first step of intermediate-lemma discovery (T): it does not invent lemmas
(the open 🔴 part), it makes the lemmas an existing proof already uses explicit and checkable.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .strategy import factor_prime_powers


@dataclass
class ProofNode:
    claim: str
    method: str                       # "CRT" | "induction" | "residue-exhaustion"
    certainty: str
    children: list = field(default_factory=list)
    note: str = ""


def proof_tree(finding) -> ProofNode:
    """Reconstruct the proof-dependency tree of a proved arithmetic finding."""
    goal = finding.claim
    if finding.verdict != "proved":
        return ProofNode(goal, finding.method, finding.certainty, note="not proved")
    if finding.method == "modulus-factoring":
        lemmas = [ProofNode(f"({finding.expression}) % {pp} == 0", "induction", "formal_proof")
                  for pp in factor_prime_powers(finding.modulus)]
        return ProofNode(goal, "CRT", "formal_proof", lemmas,
                         "coprime prime-power lemmas combined by the Chinese Remainder Theorem")
    if finding.method == "residue-exhaustion":
        return ProofNode(goal, "residue-exhaustion", "exhaustive_residue_proof",
                         note=f"finite case-split: all {finding.modulus} residues checked")
    return ProofNode(goal, "induction", "formal_proof")


def render_tree(node: ProofNode, indent: int = 0) -> str:
    """A readable ASCII proof tree."""
    pad = "    " * indent
    head = f"{pad}{node.claim}   [{node.method}, {node.certainty}]"
    if node.note:
        head += f"  — {node.note}"
    lines = [head] + [render_tree(c, indent + 1) for c in node.children]
    return "\n".join(lines)
