"""Discovery — the loop CLOSED end to end (generate → refute → PROVE) in the arithmetic domain."""
from mathhead.discovery import (
    discovered_modulus,
    first_counterexample,
    run_arithmetic_discovery,
)
from mathhead.discovery.arithmetic import _consec, _pow_minus_n


def _by_expr():
    return {f.expression: f for f in run_arithmetic_discovery(check_upto=40)}


def test_discovers_correct_moduli_from_data():
    f = _by_expr()
    assert f["n*(n+1)"].modulus == 2
    assert f["n*(n+1)*(n+2)"].modulus == 6
    assert f["n*(n+1)*(n+2)*(n+3)"].modulus == 24
    assert f["n**3 - n"].modulus == 6          # stronger than the naive "mod 3"
    assert f["n**5 - n"].modulus == 30         # 2*3*5, stronger than Fermat's mod 5


def test_every_discovered_law_survives_refutation():
    for f in run_arithmetic_discovery(check_upto=40):
        assert f.refute_status == "no_counterexample_within_bound"


def test_judge_proves_what_it_can():
    f = _by_expr()
    assert f["n*(n+1)"].verdict == "proved" and f["n*(n+1)"].certainty == "formal_proof"
    assert f["n**2 - n"].verdict == "proved" and f["n**2 - n"].certainty == "formal_proof"


def test_portfolio_proves_every_modular_law_with_the_right_strategy():
    # induction stalls on the harder ones, but the portfolio's complete fallback (residue
    # exhaustion) finishes them -- so every true modular law is proved, each by the winning method.
    findings = run_arithmetic_discovery(check_upto=40)
    assert all(f.verdict == "proved" for f in findings)
    methods = {f.method for f in findings}
    assert methods == {"induction", "modulus-factoring", "residue-exhaustion"}
    # the hardest ones are closed by the complete residue-exhaustion proof
    f = _by_expr()
    assert f["n**5 - n"].method == "residue-exhaustion"
    assert f["n**5 - n"].certainty == "exhaustive_residue_proof"


def test_every_proof_is_independently_verified():
    # each proved modular law is re-checked by the INDEPENDENT checker (not the prover)
    findings = run_arithmetic_discovery(check_upto=40)
    assert all(f.independently_verified for f in findings)


def test_overshoot_modulus_is_refuted_counterexample_first():
    # claiming a modulus larger than the truth dies before the judge
    assert first_counterexample(_consec(2), 4, 40) == 1        # n(n+1) not ≡0 mod 4 (n=1 -> 2)
    assert first_counterexample(_pow_minus_n(3), 12, 40) == 2  # n^3-n not ≡0 mod 12 (n=2 -> 6)


def test_discovered_modulus_helper():
    assert discovered_modulus(_consec(2)) == 2
    assert discovered_modulus(_pow_minus_n(5)) == 30
