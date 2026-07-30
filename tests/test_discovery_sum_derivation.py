"""Discovery M-floor — DERIVE the sum-induction rule from the kernel's PolyIdentity (explicit step)."""
from fractions import Fraction as F

import pytest

from mathhead.discovery.kernel import Identity, KernelError, SumInduction, check
from mathhead.discovery.sum_derivation import (
    check_sum_derivation,
    derive_sum_identity,
    sum_induction_is_derivable,
)

# (name, f_poly, g_poly) for well-known polynomial sums Σ_{i=1}^n f(i) = g(n)
_KNOWN = [
    ("Σ1 = n", (1,), (0, 1)),
    ("Σi = n(n+1)/2", (0, 1), (0, F(1, 2), F(1, 2))),
    ("Σi² = n(n+1)(2n+1)/6", (0, 0, 1), (0, F(1, 6), F(1, 2), F(1, 3))),
    ("Σi³ = (n(n+1)/2)²", (0, 0, 0, 1), (0, 0, F(1, 4), F(1, 2), F(1, 4))),
    ("Σ(2i−1) = n²", (-1, 2), (0, 0, 1)),
]


@pytest.mark.parametrize("name,f,g", _KNOWN)
def test_known_sums_are_derivable_from_polyidentity(name, f, g):
    d = derive_sum_identity(f, g)
    assert d.verified and d.base_ok and d.step_kernel_verified, name
    assert check_sum_derivation(d), name                       # independent checker agrees


def test_the_explicit_step_is_a_standalone_kernel_polyidentity():
    # the WHOLE point: the induction step g(n) = g(n−1)+f(n) is a PolyIdentity the kernel accepts
    # on its own — SumInduction is not needed as a primitive.
    d = derive_sum_identity((0, 1), (0, F(1, 2), F(1, 2)))
    thm = check(Identity(d.step_lhs, d.step_rhs))              # kernel accepts the bare step identity
    assert thm.kind == "PolyIdentity"
    assert "SumInduction" not in d.trust_base and "PolyIdentity" in d.trust_base


@pytest.mark.parametrize("name,f,g", _KNOWN)
def test_derivation_agrees_with_the_kernel_suminduction_rule(name, f, g):
    # cross-consistency: the derived route accepts EXACTLY what the primitive SumInduction rule accepts
    kernel_accepts = True
    try:
        check(SumInduction(f, g))
    except KernelError:
        kernel_accepts = False
    assert sum_induction_is_derivable(f, g) == kernel_accepts, name


def test_false_closed_form_is_rejected_both_ways():
    # Σi ≠ n²: base holds (1=1) but the step fails, so neither route accepts it
    d = derive_sum_identity((0, 1), (0, 0, 1))
    assert d.base_ok and not d.step_kernel_verified and not d.verified
    assert not check_sum_derivation(d)
    with pytest.raises(KernelError):
        check(SumInduction((0, 1), (0, 0, 1)))                 # kernel rejects it too


def test_base_case_mismatch_is_caught():
    # g(1) ≠ f(1): Σi claimed = n(n+1)/2 + 1 breaks the base case
    d = derive_sum_identity((0, 1), (1, F(1, 2), F(1, 2)))
    assert not d.base_ok and not d.verified


def test_derivation_is_deterministic():
    a = derive_sum_identity((0, 1), (0, F(1, 2), F(1, 2)))
    b = derive_sum_identity((0, 1), (0, F(1, 2), F(1, 2)))
    assert a == b
