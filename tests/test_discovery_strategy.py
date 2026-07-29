"""Discovery Track S — proof-strategy: factor the modulus, prove each part, combine by CRT."""
from mathhead.discovery import (
    factor_prime_powers,
    prove_modular_divisibility,
    run_arithmetic_discovery,
)


def test_factor_prime_powers():
    assert factor_prime_powers(6) == [2, 3]
    assert factor_prime_powers(30) == [2, 3, 5]
    assert factor_prime_powers(12) == [4, 3]          # prime POWERS, not just primes


def test_crt_factoring_proves_what_one_induction_cannot():
    # a single induction leaves n^3 - n = 0 mod 6 as 'unknown'; factoring into mod 2 & mod 3 proves it
    v = prove_modular_divisibility("n**3 - n", 6)
    assert v.status == "proved" and v.certainty == "formal_proof"
    assert v.detail["prime_powers"] == [2, 3]


def test_honestly_reports_the_blocking_part():
    # n^5 - n = 0 mod 30: mod 2 and mod 5 fall, but the mod-3 induction step is beyond Z3 here
    v = prove_modular_divisibility("n**5 - n", 30)
    assert v.status == "unknown"
    assert 3 in v.detail["blocked_parts"]             # says WHICH part blocked, not a fake proof


def test_strategy_upgrades_the_arithmetic_findings():
    by_expr = {f.expression: f for f in run_arithmetic_discovery(check_upto=40)}
    up = by_expr["n**3 - n"]
    assert up.verdict == "proved" and up.method == "modulus-factoring"   # upgraded from unknown
    assert by_expr["n**5 - n"].verdict == "unknown"                      # still honest unknown
