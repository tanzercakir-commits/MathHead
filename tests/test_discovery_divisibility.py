"""Discovery M-floor — the elementary integer-divisibility lemmas, explicit and checked."""
from mathhead.discovery.divisibility import (
    absorption_lemma,
    additive_lemma,
    verify_lemmas,
    witness_divides,
)


def test_witness_divides_returns_the_quotient_or_none():
    assert witness_divides(6, 30) == 5
    assert witness_divides(6, 31) is None
    assert witness_divides(0, 5) is None                    # no division by zero modulus


def test_additive_lemma_has_a_reconstructing_witness():
    lemma = additive_lemma(6, 12, 18)                      # 6|12 ∧ 6|18 ⇒ 6|30
    assert lemma.verified and lemma.witness == 5 and lemma.target == 30
    assert 6 * lemma.witness == lemma.target               # exact reconstruction


def test_absorption_lemma_has_a_reconstructing_witness():
    lemma = absorption_lemma(6, 12, 7)                     # 6|12 ⇒ 6|(12·7)=84
    assert lemma.verified and lemma.witness == 14 and lemma.target == 84
    assert 6 * lemma.witness == lemma.target


def test_lemma_fails_honestly_when_a_premise_does_not_hold():
    lemma = additive_lemma(6, 13, 18)                     # 6 ∤ 13
    assert not lemma.premises_hold and not lemma.verified


def test_absorption_matches_the_residue_derivation_usage():
    # exactly the step congruence.py leans on: n≡r (mod m) ⇒ m|(n−r), so m|(n−r)·q(n)
    m, n, r, q_at_n = 6, 13, 1, 42        # n−r = 12 divisible by 6; q(n)=42 arbitrary
    lemma = absorption_lemma(m, n - r, q_at_n)
    assert lemma.verified and lemma.target == (n - r) * q_at_n
    assert m * lemma.witness == (n - r) * q_at_n


def test_exhaustive_sweep_has_zero_failures():
    r = verify_lemmas(8)
    assert r.verified and r.failures == 0
    assert r.additive_checks > 2000 and r.absorption_checks > 2000
    assert r.certainty == "bounded_check" and "ring axioms" in r.trust_base


def test_verification_is_deterministic():
    assert verify_lemmas(6) == verify_lemmas(6)
