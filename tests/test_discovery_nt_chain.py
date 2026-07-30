"""Discovery U1 — walk a number-theory claim along the representation chain."""
import pytest

from mathhead.discovery.nt_chain import walk_divisibility_chain

_N3 = (0, -1, 0, 1)      # n³ − n


def test_universal_claim_is_decided_and_kernel_confirmed():
    w = walk_divisibility_chain(6, _N3, "forall")
    assert w.holds and w.decided_at == "finite_residue" and w.kernel_confirms is True
    assert all(x == 0 for x in w.residue_table)


def test_the_forall_exists_distinction_is_surfaced_honestly():
    # 5 ∤ n³−n for ALL n, yet 5 | n³−n for SOME n (n=5 → 120) — the walk reports both truthfully
    forall = walk_divisibility_chain(5, _N3, "forall")
    exists = walk_divisibility_chain(5, _N3, "exists")
    assert forall.holds is False and exists.holds is True
    assert forall.residue_table == exists.residue_table          # same table, different quantifier


def test_universal_falsehood_is_not_kernel_confirmed():
    w = walk_divisibility_chain(5, _N3, "forall")
    assert not w.holds and w.kernel_confirms is False            # kernel agrees it is NOT universal


def test_existential_does_not_claim_kernel_confirmation():
    w = walk_divisibility_chain(6, _N3, "exists")
    assert w.kernel_confirms is None                            # kernel proves ∀, not ∃ — honestly unused


def test_chain_steps_are_in_representation_order():
    w = walk_divisibility_chain(6, _N3, "forall")
    assert [s.representation for s in w.steps] == [
        "diophantine", "modular", "finite_residue", "decision"]


def test_chain_coverage_ledger_is_explicit():
    w = walk_divisibility_chain(6, _N3, "forall")
    assert "modular→finite-residue" in w.links_walked
    assert set(w.links_not_walked) == {"lattice", "SAT/SMT", "algebraic-geometry"}   # honest: not covered


def test_invalid_quantifier_is_rejected():
    with pytest.raises(ValueError, match="quantifier"):
        walk_divisibility_chain(6, _N3, "maybe")


def test_walk_is_deterministic():
    a = walk_divisibility_chain(30, (0, -1, 0, 0, 0, 1), "forall")
    b = walk_divisibility_chain(30, (0, -1, 0, 0, 0, 1), "forall")
    assert a == b
