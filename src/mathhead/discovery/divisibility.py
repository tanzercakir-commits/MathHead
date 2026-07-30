"""
mathhead.discovery.divisibility — make the ELEMENTARY integer-divisibility lemmas explicit and checked
(roadmap M-floor completion).

`congruence.py` and `sum_derivation.py` shrank the kernel's trusted base to "PolyIdentity + elementary
integer divisibility". That last phrase was the one remaining hand-wave — the two divisibility lemmas
the derivations lean on were cited, never exhibited. This module makes them auditable, with an explicit
CONSTRUCTIVE witness (the quotient) for every instance and an exhaustive bounded check:

  * ADDITIVE:   m|a ∧ m|b ⇒ m|(a+b)   — witness quotient (a/m + b/m), from distributivity  ms+mt = m(s+t);
  * ABSORPTION: m|a ⇒ m|(a·k) ∀k       — witness quotient (a/m)·k,   from associativity   (ms)k = m(sk).

These are precisely the steps in the RESIDUE derivation: `m|(n−r)` (as n ≡ r) plus ABSORPTION gives
`m|(n−r)·q(n) = p(n)−p(r)`, and ADDITIVE combines it with `m|p(r)` to conclude `m|p(n)`.

HONEST status: each instance carries a constructive witness verified by EXACT integer arithmetic, and
`verify_lemmas` exhausts a bounded range with ZERO failures (`bounded_check`). The universal ∀ statement
rests on the ring axioms of ℤ (distributivity / associativity) — the bedrock the whole kernel already
stands on — recorded here as the structural reason, not re-proved from below (there is no "below").
"""
from __future__ import annotations

from dataclasses import dataclass


def witness_divides(m: int, a: int):
    """The quotient q with a = m·q if m | a, else None (the constructive witness of divisibility)."""
    if m == 0:
        return None
    return a // m if a % m == 0 else None


@dataclass
class DivLemma:
    name: str
    premises_hold: bool         # the m|… preconditions are met
    witness: int                # the quotient realizing the conclusion m | target
    target: int                 # the value claimed divisible by m
    reconstructs: bool          # m · witness == target  (exact integer check)

    @property
    def verified(self) -> bool:
        return self.premises_hold and self.reconstructs


def additive_lemma(m: int, a: int, b: int) -> DivLemma:
    """m|a ∧ m|b ⇒ m|(a+b), with the explicit witness quotient (a/m)+(b/m)."""
    qa, qb = witness_divides(m, a), witness_divides(m, b)
    premises = qa is not None and qb is not None
    witness = (qa + qb) if premises else 0
    return DivLemma("additive", premises, witness, a + b, premises and m * witness == a + b)


def absorption_lemma(m: int, a: int, k: int) -> DivLemma:
    """m|a ⇒ m|(a·k) for any integer k, with the explicit witness quotient (a/m)·k."""
    qa = witness_divides(m, a)
    premises = qa is not None
    witness = (qa * k) if premises else 0
    return DivLemma("absorption", premises, witness, a * k, premises and m * witness == a * k)


@dataclass
class LemmaReport:
    additive_checks: int
    absorption_checks: int
    failures: int
    verified: bool
    certainty: str = "bounded_check"
    trust_base: str = "ring axioms of ℤ (distributivity ms+mt=m(s+t), associativity (ms)k=m(sk))"


def verify_lemmas(bound: int = 8) -> LemmaReport:
    """Exhaustively confirm both lemmas over a bounded range: every modulus m∈1..bound, multiples
    a=m·s, b=m·t (|s|,|t|≤bound), and scalars |k|≤bound. Zero failures ⇒ the elementary divisibility
    base is sound on the whole sweep (bounded_check), each with a reconstructing constructive witness."""
    add_n = absorb_n = failures = 0
    rng = range(-bound, bound + 1)
    for m in range(1, bound + 1):
        for s in rng:
            a = m * s
            for t in rng:
                b = m * t
                lemma = additive_lemma(m, a, b)
                add_n += 1
                if not lemma.verified:
                    failures += 1
            for k in rng:
                lemma = absorption_lemma(m, a, k)
                absorb_n += 1
                if not lemma.verified:
                    failures += 1
    return LemmaReport(add_n, absorb_n, failures, failures == 0)
