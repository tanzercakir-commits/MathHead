"""Discovery P2 — reverse-engineer a specific finding into the general principle it instantiates."""
from math import factorial

import sympy

from mathhead.discovery.generalize import (
    consecutive_product,
    general_principle,
    generalize,
)


def test_six_divides_n3_minus_n_generalizes_to_consecutive_product_law():
    g = generalize("n**3 - n", 6)
    assert g.generalized and g.run_length == 3 and g.specific_modulus == 6
    assert "consecutive integers" in g.principle and "k!" in g.principle


def test_all_lifted_instances_are_kernel_verified_with_factorial_moduli():
    g = generalize("n**3 - n", 6)
    assert len(g.instances) >= 3
    for inst in g.instances:
        assert inst.kernel_verified                     # kernel PROVED k! | ∏(n+i), universal in n
        assert inst.modulus == factorial(inst.k)


def test_consecutive_product_polynomial_is_correct():
    n = sympy.Symbol("n")
    for k in range(1, 6):
        expected = sympy.Poly(sympy.prod([n + i for i in range(k)]), n).all_coeffs()[::-1]
        assert list(consecutive_product(k)) == [int(c) for c in expected]


def test_general_principle_family_is_kernel_verified():
    fam = general_principle(5)
    assert [inst.k for inst in fam] == [1, 2, 3, 4, 5]
    assert all(inst.kernel_verified and inst.modulus == factorial(inst.k) for inst in fam)


def test_universal_claim_is_reported_honestly_not_as_proved():
    g = generalize("n**3 - n", 6)
    # each instance is kernel_verified, but the ∀k statement is only a cited structural argument
    assert g.instance_status == "kernel_verified"
    assert g.universal_status == "structural_argument"
    assert "binomial" in g.citation.lower() or "C(n,k)" in g.citation


def test_declines_when_there_is_no_consecutive_product_structure():
    # n⁵−n = n(n−1)(n+1)(n²+1): the n²+1 factor is not linear, so it is NOT a run of consecutive ints;
    # 30 | n⁵−n is a TRUE fact but not explained by this principle — the module must not force it.
    g = generalize("n**5 - n", 30)
    assert not g.generalized and g.run_length == 0


def test_declines_when_modulus_does_not_match_the_run_factorial():
    # 3 | n³−n is true, but the consecutive-run principle guarantees 3! = 6, not 3 — no clean lift
    g = generalize("n**3 - n", 3)
    assert not g.generalized


def test_generalization_is_deterministic():
    assert generalize("n**3 - n", 6) == generalize("n**3 - n", 6)
