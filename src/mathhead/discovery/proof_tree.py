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


def sum_proof_tree(f_poly, g_poly, statement: str | None = None) -> ProofNode:
    """Reconstruct the proof-dependency tree of a SUM identity `Σ_{i=1}^n f(i) = g(n)`. By the explicit
    derivation (`sum_derivation`), a SumInduction proof rests on TWO lemmas: a base case `g(1) = f(1)`
    (an evaluation) and an induction STEP `g(n) = g(n−1) + f(n)` (a kernel-checked PolyIdentity). This
    makes those lemmas explicit — the same honest T3 slice as the modular tree, now for sums."""
    from .sum_derivation import derive_sum_identity
    d = derive_sum_identity(f_poly, g_poly)
    goal = statement or "sum_(i=1..n) f(i) = g(n)"
    if not d.verified:
        return ProofNode(goal, "SumInduction", "unknown", note="not proved")
    base = ProofNode(f"g(1) = f(1)  [{d.base_g} = {d.base_f}]", "evaluation", "arithmetic_check",
                     note="base case at n=1")
    step = ProofNode("g(n) = g(n−1) + f(n)", "PolyIdentity", "kernel_verified",
                     note="the induction step, verified as a kernel polynomial identity")
    return ProofNode(goal, "SumInduction", "formal_proof", [base, step],
                     "base case + kernel-checked telescoping step ⇒ induction over n ≥ 1")


def render_tree(node: ProofNode, indent: int = 0) -> str:
    """A readable ASCII proof tree."""
    pad = "    " * indent
    head = f"{pad}{node.claim}   [{node.method}, {node.certainty}]"
    if node.note:
        head += f"  — {node.note}"
    lines = [head] + [render_tree(c, indent + 1) for c in node.children]
    return "\n".join(lines)
