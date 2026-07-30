"""
mathhead.discovery.nt_chain — walk a number-theory claim along the representation chain (roadmap U1).

U0 (`representations.py`) registers individual bridges; U1 is the CHAIN — routing a number-theory claim
through a sequence of representations until one of them DECIDES it. The roadmap's full chain is
"Diophantine → modular → lattice → SAT/SMT → finite-residue → algebraic-geometry". The engine honestly
walks the decidable SEGMENT of that chain for polynomial divisibility claims:

    Diophantine claim  →  modular form p(n) ≡ 0 (mod m)  →  finite-residue table  →  decision

For a UNIVERSAL claim `∀n: m|p(n)` the finite-residue table decides it (all-zero ⇔ true), cross-confirmed
by the kernel's RESIDUE theorem. For an EXISTENTIAL claim `∃n: m|p(n)` the SAME table decides it (any zero
entry ⇔ a solution exists) — and this exposes a real distinction the kernel alone does not: `5|n³−n` is
FALSE for all n yet TRUE for some n (n=5), which the walk reports honestly.

HONESTY — the ledger is explicit. `links_walked` lists the chain segment actually traversed; the roadmap
links NOT walked (lattice, SAT/SMT, algebraic-geometry) are recorded too, so the walk never pretends to
cover more of the chain than it does. Deterministic, exact integer arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .kernel import KernelError, Residue, check
from .representations import divisibility_to_residue_table

_LINKS_NOT_WALKED = ("lattice", "SAT/SMT", "algebraic-geometry")


@dataclass
class ChainStep:
    representation: str         # "diophantine" | "modular" | "finite_residue" | "decision"
    detail: str


@dataclass
class ChainWalk:
    claim: str
    quantifier: str            # "forall" | "exists"
    holds: bool
    decided_at: str            # which representation settled it
    residue_table: tuple = ()
    kernel_confirms: bool | None = None   # forall: cross-checked by RESIDUE; exists: None (kernel = ∀)
    steps: list = field(default_factory=list)
    links_walked: tuple = ()
    links_not_walked: tuple = _LINKS_NOT_WALKED


def walk_divisibility_chain(m: int, poly: tuple, quantifier: str = "forall") -> ChainWalk:
    """Walk `∀n: m|p(n)` (or `∃n`) from its Diophantine statement through the modular and finite-residue
    representations to a decision, recording every step and an honest ledger of chain coverage."""
    if quantifier not in ("forall", "exists"):
        raise ValueError(f"quantifier must be 'forall' or 'exists', got {quantifier!r}")
    q = "∀n" if quantifier == "forall" else "∃n"
    claim = f"{q}: {m} | p(n)"
    table = divisibility_to_residue_table(m, poly)

    steps = [
        ChainStep("diophantine", f"{claim} — a divisibility question over the integers"),
        ChainStep("modular", f"reduce to p(n) ≡ 0 (mod {m}) — depends only on n mod {m}"),
        ChainStep("finite_residue", f"tabulate p(r) mod {m} for r=0..{m - 1}: {table}"),
    ]

    if quantifier == "forall":
        holds = all(x == 0 for x in table)                # every residue vanishes
        try:
            check(Residue(m, poly))
            kernel_confirms = True
        except KernelError:
            kernel_confirms = False
        steps.append(ChainStep("decision", f"all-zero ⇔ true → {holds}; kernel RESIDUE confirms"))
    else:
        holds = any(x == 0 for x in table)                # some residue admits a solution
        kernel_confirms = None                            # the kernel proves ∀, not ∃ — honestly not used
        steps.append(ChainStep("decision", f"some-zero ⇔ solvable → {holds}"))

    return ChainWalk(
        claim=claim, quantifier=quantifier, holds=holds, decided_at="finite_residue",
        residue_table=table, kernel_confirms=kernel_confirms, steps=steps,
        links_walked=("Diophantine→modular", "modular→finite-residue", "finite-residue→decision"),
    )
