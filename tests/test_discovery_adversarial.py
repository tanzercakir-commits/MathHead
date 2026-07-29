"""Discovery — red-team the verifier: a battery of false claims the kernel/checker MUST all reject."""
from mathhead.discovery.adversarial import (
    attack_checker,
    attack_divides,
    attack_factorizations,
    attack_illegal_rules,
    attack_sum_identities,
    robustness_report,
)


def test_no_false_modular_claim_is_accepted():
    assert attack_divides() == []                      # 600+ false Divides claims, all rejected


def test_no_false_sum_identity_is_accepted():
    assert attack_sum_identities() == []


def test_no_bogus_factorization_is_accepted():
    assert attack_factorizations() == []


def test_illegal_rule_applications_and_forgery_are_blocked():
    assert attack_illegal_rules() == []                # non-coprime CRT, mismatched poly, forgery


def test_independent_checker_rejects_false_claims():
    assert attack_checker() == []


def test_full_battery_is_sound_with_passing_positive_controls():
    r = robustness_report()
    assert r.attempts >= 600                           # a broad sweep
    assert r.breaches == []                             # zero false claims minted a theorem
    assert r.positive_controls == 3 and r.positive_failures == []   # true claims still accepted
    assert r.sound is True


def test_battery_is_deterministic():
    a = robustness_report(divides_limit=200)
    b = robustness_report(divides_limit=200)
    assert (a.attempts, len(a.breaches), a.sound) == (b.attempts, len(b.breaches), b.sound)
