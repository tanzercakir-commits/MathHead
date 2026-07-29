"""Discovery — second arithmetic generator: discover-and-prove SUM identities (via MathHead)."""
import sympy

from mathhead.discovery.sequences import run_sequence_discovery

_n = sympy.Symbol("n")


def _by_term():
    return {f.term: f for f in run_sequence_discovery()}


def _cf(finding):
    return sympy.simplify(sympy.sympify(finding.closed_form) - 0)


def test_discovers_and_proves_the_classic_sums():
    f = _by_term()
    assert sympy.simplify(_cf(f["i"]) - _n * (_n + 1) / 2) == 0          # Σi = n(n+1)/2
    assert sympy.simplify(_cf(f["2*i - 1"]) - _n**2) == 0                # Σ(2i-1) = n²
    assert sympy.simplify(_cf(f["i**3"]) - (_n * (_n + 1) / 2) ** 2) == 0  # Σi³ = (n(n+1)/2)²


def test_all_polynomial_sums_are_proved_by_mathhead():
    for term in ("i", "i**2", "i**3", "2*i - 1"):
        finding = _by_term()[term]
        assert finding.verdict == "proved" and finding.certainty == "solver_verified"


def test_non_polynomial_sum_is_refuted_not_forced():
    # Σ 2^i is not polynomial: the fit diverges beyond the sample and is refuted, not forced.
    assert _by_term()["2**i"].verdict == "refuted"


def test_every_proved_sum_identity_is_independently_verified():
    # each proved closed form is re-checked independently of the MathHead proof (base + step)
    for term in ("i", "i**2", "i**3", "2*i - 1"):
        assert _by_term()[term].independently_verified


def test_every_proved_sum_identity_is_kernel_verified():
    # each proved closed form also carries a kernel SumInduction proof term with provenance (M1–M5)
    for term in ("i", "i**2", "i**3", "2*i - 1"):
        f = _by_term()[term]
        assert f.kernel_verified and f.axioms == ("SUM_INDUCTION",)
        assert len(f.proof_hash) == 16
    assert _by_term()["2**i"].kernel_verified is False   # non-polynomial: no kernel proof


def test_run_is_deterministic():
    a = [f.closed_form for f in run_sequence_discovery()]
    b = [f.closed_form for f in run_sequence_discovery()]
    assert a == b
