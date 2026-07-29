"""Discovery Track M4/M5 — proof-artifact provenance, hashing, and deterministic replay."""
import pytest

from mathhead.discovery.kernel import CRT, Residue, check, prove_divides
from mathhead.discovery.provenance import (
    KERNEL_VERSION,
    axioms_used,
    proof_hash,
    replay,
)

_N3_MINUS_N = (0, -1, 0, 1)          # n³ − n
_N5_MINUS_N = (0, -1, 0, 0, 0, 1)    # n⁵ − n


def test_axioms_used_lists_every_rule():
    _thm, term = prove_divides(30, _N5_MINUS_N)           # CRT over RESIDUE(2),(3),(5)
    assert axioms_used(term) == {"CRT", "RESIDUE(m=2)", "RESIDUE(m=3)", "RESIDUE(m=5)"}


def test_axioms_used_for_a_bare_residue():
    assert axioms_used(Residue(2, _N3_MINUS_N)) == {"RESIDUE(m=2)"}


def test_proof_hash_is_deterministic_and_order_independent():
    a = CRT((Residue(2, _N3_MINUS_N), Residue(3, _N3_MINUS_N)))
    b = CRT((Residue(3, _N3_MINUS_N), Residue(2, _N3_MINUS_N)))   # premises swapped
    assert proof_hash(a) == proof_hash(b)                  # canonical ⇒ order-independent
    assert len(proof_hash(a)) == 16


def test_different_proofs_have_different_hashes():
    h6 = proof_hash(CRT((Residue(2, _N3_MINUS_N), Residue(3, _N3_MINUS_N))))
    h30 = proof_hash(prove_divides(30, _N5_MINUS_N)[1])
    assert h6 != h30


def test_kernel_version_participates_in_the_hash():
    import mathhead.discovery.provenance as prov
    term = Residue(2, _N3_MINUS_N)
    h1 = proof_hash(term)
    old = prov.KERNEL_VERSION
    try:
        prov.KERNEL_VERSION = "9.9"                        # a kernel-version bump...
        assert proof_hash(term) != h1                     # ...invalidates the artifact hash
    finally:
        prov.KERNEL_VERSION = old
    assert KERNEL_VERSION == "1.0"


def test_replay_reproduces_the_same_theorem_and_hash():
    _thm, term = prove_divides(6, _N3_MINUS_N)
    r1, r2 = replay(term), replay(term)
    assert r1 == r2 == check(term) and r1.modulus == 6
    assert proof_hash(term) == proof_hash(term)


def test_provenance_rejects_non_terms():
    with pytest.raises(TypeError):
        axioms_used(("not", "a", "term"))
    with pytest.raises(TypeError):
        proof_hash(42)
