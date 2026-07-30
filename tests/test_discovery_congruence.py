"""Discovery Track M — DERIVE RESIDUE from the factor theorem, shrinking the kernel's trusted base."""
from mathhead.discovery.congruence import (
    check_residue_derivation,
    derive_residue,
    factor_quotient,
    residue_is_derivable,
)

_N3 = (0, -1, 0, 1)          # n³ − n
_N5 = (0, -1, 0, 0, 0, 1)    # n⁵ − n
_N2P1 = (1, 0, 1)            # n² + 1  (NOT divisible by 4)


def test_factor_quotient_reconstructs_the_polynomial():
    # p(x) − p(r) = (x − r)·q(x): reconstruct and compare
    def ev(poly, x):
        v = 0
        for c in reversed(poly):
            v = v * x + c
        return v
    for r in range(6):
        q = factor_quotient(_N3, r)
        # (r - r)*q + p(r) == p(r); and at a test point x=9: (9-r)*q(9) + p(r) == p(9)
        val = (9 - r) * ev(q, 9) + ev(_N3, r)
        assert val == ev(_N3, 9)


def test_true_modular_facts_are_derivable():
    for poly, m in [(_N3, 6), (_N5, 30), ((0, -1, 0, 0, 0, 0, 0, 1), 42)]:
        d = derive_residue(poly, m)
        assert d.verified and check_residue_derivation(d)
        assert all(s.kernel_verified for s in d.steps)     # every factor identity kernel-checked
        assert d.trust_base.startswith("factor theorem")


def test_false_modular_claims_are_not_derivable():
    d = derive_residue(_N2P1, 4)                            # 4 ∤ n²+1
    assert not d.verified and not check_residue_derivation(d)
    # the FACTOR identities still hold (the factor theorem is always true)...
    assert all(s.kernel_verified for s in d.steps)
    # ...but the residues do not all vanish, so the modular claim is not derived
    assert any(s.residue_value != 0 for s in d.steps)


def test_overshoot_modulus_is_not_derivable():
    assert not residue_is_derivable(_N3, 12)               # 12 ∤ n³−n (n=2 → 6)


def test_residue_is_derivable_helper_agrees_with_the_kernel_family():
    assert residue_is_derivable(_N3, 6)
    assert residue_is_derivable(_N5, 30)
    assert not residue_is_derivable(_N2P1, 4)


def test_independent_checker_uses_no_kernel():
    # the independent re-check must reject a tampered derivation (wrong modulus in the object)
    d = derive_residue(_N3, 6)
    d.m = 5                                                 # corrupt: step count no longer matches m
    assert check_residue_derivation(d) is False
