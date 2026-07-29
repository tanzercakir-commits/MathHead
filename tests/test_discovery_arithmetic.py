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


def test_judge_is_honestly_unknown_never_faked():
    # the higher-degree induction steps are beyond Z3 here -> honest 'unknown', not a fake proof
    f = _by_expr()
    assert f["n**5 - n"].verdict == "unknown"
    assert f["n**3 - n"].verdict in {"proved", "unknown"}   # never "refuted" (the law is true)


def test_overshoot_modulus_is_refuted_counterexample_first():
    # claiming a modulus larger than the truth dies before the judge
    assert first_counterexample(_consec(2), 4, 40) == 1        # n(n+1) not ≡0 mod 4 (n=1 -> 2)
    assert first_counterexample(_pow_minus_n(3), 12, 40) == 2  # n^3-n not ≡0 mod 12 (n=2 -> 6)


def test_discovered_modulus_helper():
    assert discovered_modulus(_consec(2)) == 2
    assert discovered_modulus(_pow_minus_n(5)) == 30
