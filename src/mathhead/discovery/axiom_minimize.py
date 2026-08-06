"""
mathhead.discovery.axiom_minimize — prove with the FEWEST axioms (roadmap AB1).

A theorem often admits several proofs resting on different axiom sets. AB1 asks: which proof uses the
SMALLEST / weakest axiom basis? For a modular claim `m | p(n)` the kernel offers (at least) two proof
terms:

  * a DIRECT residue sweep at m — axiom footprint {RESIDUE(m)} (one rule);
  * a CRT decomposition over prime powers — {CRT, RESIDUE(p₁^a₁), …} (several rules).

Both are kernel-checked; this module enumerates them, keeps only the ones the kernel accepts, and
returns the one with the fewest axioms. Result: `6 | n³−n` is provable by RESIDUE(6) ALONE — the CRT
proof, while valid, is not axiom-minimal. An honest answer to "how little do we need to assume?".
"""
from __future__ import annotations

from dataclasses import dataclass

from .kernel import CRT, KernelError, Residue, _factor_prime_powers, check, poly_from_sympy
from .provenance import axioms_used


@dataclass
class AxiomProof:
    strategy: str               # "direct-residue" | "crt-prime-powers"
    axioms: tuple               # sorted axiom footprint
    n_axioms: int


def _candidate_terms(m: int, poly: tuple):
    yield "direct-residue", Residue(m, poly)                  # one sweep at m
    pks = _factor_prime_powers(m)
    if len(pks) > 1:
        yield "crt-prime-powers", CRT(tuple(Residue(pk, poly) for pk in pks))


def candidate_proofs(m: int, poly: tuple) -> list:
    """All kernel-CHECKED proofs of `m | p(n)`, each with its axiom footprint."""
    out = []
    for name, term in _candidate_terms(m, poly):
        try:
            check(term)                                       # only keep proofs the kernel accepts
        except KernelError:
            continue
        ax = tuple(sorted(axioms_used(term)))
        out.append(AxiomProof(name, ax, len(ax)))
    return out


def minimal_axiom_proof(m: int, poly: tuple) -> AxiomProof | None:
    """The kernel-checked proof of `m | p(n)` with the FEWEST axioms (ties broken deterministically)."""
    cands = candidate_proofs(m, poly)
    if not cands:
        return None
    return min(cands, key=lambda p: (p.n_axioms, p.axioms))


def minimal_axioms_for(expr: str, m: int) -> AxiomProof | None:
    """Convenience: minimal-axiom proof for a polynomial expression string, e.g. ('n**3 - n', 6)."""
    try:
        return minimal_axiom_proof(m, poly_from_sympy(expr))
    except KernelError:
        return None


def proof_avoiding(m: int, poly: tuple, banned) -> AxiomProof | None:
    """AD0 control surface — BAN an axiom: the cheapest kernel-checked proof of `m | p(n)` whose
    axiom footprint avoids every banned axiom (names exactly as `axioms_used` spells them, e.g.
    'CRT' or 'RESIDUE(m=6)'). Returns None honestly when every kernel-accepted proof touches a
    banned axiom — a ban NEVER fabricates an alternative proof."""
    banned = frozenset(banned)
    for cand in sorted(candidate_proofs(m, poly), key=lambda p: (p.n_axioms, p.axioms)):
        if not banned.intersection(cand.axioms):
            return cand
    return None
