"""Discovery Track M1/M2 — the minimal LCF-style proof kernel: only checked terms mint theorems,
false claims are rejected, theorems can't be forged, and rule side-conditions are enforced."""
import pytest

from fractions import Fraction

from mathhead.discovery.kernel import (
    CRT,
    KernelError,
    Residue,
    SumInduction,
    Theorem,
    check,
    poly_from_sympy_q,
    prove_divides,
    prove_sum_identity,
)

_N3_MINUS_N = (0, -1, 0, 1)          # n³ − n
_N5_MINUS_N = (0, -1, 0, 0, 0, 1)    # n⁵ − n
_N2_PLUS_1 = (1, 0, 1)               # n² + 1  (NOT divisible by 4)
_4N = (0, 4)                         # 4n


def test_residue_rule_proves_an_atomic_fact():
    thm = check(Residue(2, _N3_MINUS_N))          # 2 | n³−n
    assert isinstance(thm, Theorem) and thm.modulus == 2


def test_crt_composes_coprime_moduli():
    thm = check(CRT((Residue(2, _N3_MINUS_N), Residue(3, _N3_MINUS_N))))   # 6 | n³−n
    assert thm.modulus == 6


def test_prover_builds_and_kernel_checks_a_theorem():
    thm, term = prove_divides(30, _N5_MINUS_N)     # 30 | n⁵−n via 2·3·5
    assert thm.modulus == 30
    assert isinstance(term, CRT) and {r.modulus for r in term.parts} == {2, 3, 5}


def test_false_claim_is_rejected_no_theorem_escapes():
    with pytest.raises(KernelError):
        check(Residue(4, _N2_PLUS_1))              # 4 ∤ n²+1 (n=0 → 1)
    with pytest.raises(KernelError):
        prove_divides(4, _N2_PLUS_1)               # the prover's term fails the kernel too


def test_theorems_cannot_be_forged():
    with pytest.raises(PermissionError):
        Theorem(6, _N3_MINUS_N)                    # direct construction is blocked (LCF guard)


def test_crt_rejects_non_coprime_moduli():
    # both premises are residue-valid for 4n, but gcd(2,4)=2 ⇒ CRT side-condition fails
    check(Residue(2, _4N))                         # sanity: each premise holds on its own
    check(Residue(4, _4N))
    with pytest.raises(KernelError, match="coprime"):
        check(CRT((Residue(2, _4N), Residue(4, _4N))))


def test_crt_rejects_mismatched_polynomials():
    with pytest.raises(KernelError, match="SAME polynomial"):
        check(CRT((Residue(2, _N3_MINUS_N), Residue(3, _N5_MINUS_N))))


def test_non_integer_coefficients_are_rejected():
    with pytest.raises(KernelError):
        check(Residue(2, (0.5, 1)))                # fragment is integer-polynomial only


def test_unknown_proof_term_is_rejected():
    with pytest.raises(KernelError):
        check(("not", "a", "term"))


def test_kernel_is_deterministic():
    a = check(CRT((Residue(2, _N3_MINUS_N), Residue(3, _N3_MINUS_N))))
    b = check(CRT((Residue(3, _N3_MINUS_N), Residue(2, _N3_MINUS_N))))
    assert a == b and a.modulus == 6              # same theorem regardless of premise order


# --- second judgment: polynomial SUM identities (SumInduction) --------------------------------

def test_sum_induction_proves_gauss_sum():
    # Σi = n(n+1)/2 — rational closed form
    g = (Fraction(0), Fraction(1, 2), Fraction(1, 2))
    thm = check(SumInduction((0, 1), g))
    assert thm.kind == "SumIdentity"
    with pytest.raises(AttributeError):
        _ = thm.modulus                            # SumIdentity theorems have no modulus


def test_sum_induction_via_sympy_bridge():
    f = poly_from_sympy_q("2*i - 1", "i")
    g = poly_from_sympy_q("n**2", "n")
    thm, _term = prove_sum_identity(f, g)          # Σ(2i−1) = n²
    assert thm.kind == "SumIdentity"


def test_sum_induction_rejects_a_false_closed_form():
    with pytest.raises(KernelError, match="step"):
        check(SumInduction((0, 1), poly_from_sympy_q("n**2", "n")))   # Σi ≠ n²


def test_sum_induction_rejects_a_wrong_base_case():
    # g(n) = n(n+1)/2 + 1 has the right step but g(1)=2 ≠ f(1)=1
    g = (Fraction(1), Fraction(1, 2), Fraction(1, 2))
    with pytest.raises(KernelError, match="base"):
        check(SumInduction((0, 1), g))


def test_crt_will_not_compose_a_sum_identity():
    # the two judgments don't mix: a SumIdentity premise is not a Divides theorem
    g = (Fraction(0), Fraction(1, 2), Fraction(1, 2))
    with pytest.raises(KernelError):
        check(CRT((SumInduction((0, 1), g), Residue(2, _N3_MINUS_N))))
