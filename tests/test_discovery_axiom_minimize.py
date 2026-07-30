"""Discovery AB1 — prove a modular fact with the fewest axioms."""
from mathhead.discovery.axiom_minimize import (
    candidate_proofs,
    minimal_axiom_proof,
    minimal_axioms_for,
)
from mathhead.discovery.kernel import poly_from_sympy

_N3 = poly_from_sympy("n**3 - n")     # 6 | n³−n
_N5 = poly_from_sympy("n**5 - n")     # 30 | n⁵−n


def test_direct_residue_is_axiom_minimal_over_crt():
    best = minimal_axiom_proof(6, _N3)
    assert best.strategy == "direct-residue" and best.axioms == ("RESIDUE(m=6)",)
    assert best.n_axioms == 1                              # one axiom beats CRT's three


def test_both_proofs_are_offered_and_kernel_checked_for_composite_modulus():
    strategies = {c.strategy for c in candidate_proofs(30, _N5)}
    assert strategies == {"direct-residue", "crt-prime-powers"}
    # the CRT proof is valid but larger
    crt = next(c for c in candidate_proofs(30, _N5) if c.strategy == "crt-prime-powers")
    assert crt.n_axioms == 4 and "CRT" in crt.axioms


def test_prime_modulus_has_only_the_direct_proof():
    cands = candidate_proofs(2, poly_from_sympy("n**2 - n"))
    assert len(cands) == 1 and cands[0].strategy == "direct-residue"


def test_convenience_from_expression():
    best = minimal_axioms_for("n**5 - n", 30)
    assert best.strategy == "direct-residue" and best.axioms == ("RESIDUE(m=30)",)


def test_minimization_is_deterministic():
    assert minimal_axiom_proof(6, _N3) == minimal_axiom_proof(6, _N3)
