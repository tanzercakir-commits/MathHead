"""Discovery v2B0/B1/B2 — conjecture DB, exact spectral certificates, the adaptive hunter."""
import random
from fractions import Fraction

from mathhead.discovery.adaptive_search import (
    ah_calibration,
    double_star,
    hunt,
    random_tree,
    tree_matching_number,
)
from mathhead.discovery.conjecture_db import (
    AH_SPECTRAL_MATCHING,
    CHI_LE_DELTA,
    CONJECTURES,
    CONN_HAMILTONIAN,
    lambda1_power,
    small_n_guard,
)
from mathhead.discovery.families import cycle, star
from mathhead.discovery.objects import Graph
from mathhead.discovery.rich_invariants import matching_number
from mathhead.discovery.spectral_cert import lambda1_below, sqrt_bound_above


# --- exact certification layer -------------------------------------------------------------------
def test_lambda1_below_is_exact_at_the_boundary():
    c4 = cycle(4)                                          # λ₁(C4) = 2 exactly
    assert not lambda1_below(c4, Fraction(2))              # strict: 2 < 2 is false
    assert lambda1_below(c4, Fraction(20001, 10000))
    assert not lambda1_below(c4, Fraction(19, 10))
    assert sqrt_bound_above(Fraction(29, 10), 9) and not sqrt_bound_above(Fraction(3), 9)


def test_star_equality_is_refused_by_the_certifier():
    # K_{1,8}: λ₁ = √8, μ = 1 → exact equality → NOT a counterexample, certificate must be None
    assert AH_SPECTRAL_MATCHING.certify(star(9)) is None


def test_second_equality_family_double_star_12_12():
    # engine-certified: D(12,12), n=26 has λ₁ = 4 EXACTLY and slack exactly 0 → refused
    g = double_star(12, 12)
    assert g.n == 26 and matching_number(g) == 2
    assert AH_SPECTRAL_MATCHING.certify(g) is None


# --- formalization guard -------------------------------------------------------------------------
def test_formalization_guard_no_violation_on_small_graphs():
    # the transcribed statement HOLDS exhaustively for all connected graphs n ≤ 6 — if this fails,
    # OUR FORMALIZATION is wrong (the guard's whole purpose)
    rep = small_n_guard(AH_SPECTRAL_MATCHING, 6)
    assert rep.formalization_ok and rep.graphs_checked >= 130


# --- the calibration result (v2B2) ---------------------------------------------------------------
def test_calibration_finds_certified_witnesses_smallest_n18():
    found = ah_calibration(24)
    assert found and found[0]["n"] == 18                   # D(7,8) with subdivided centre edge
    assert {(w["a"], w["b"]) for w in found if w["n"] == 19} >= {(8, 8)}   # the Wagner-shape witness
    for w in found:
        assert w["certificate"].certainty == "exact_integer_certificate"
        assert AH_SPECTRAL_MATCHING.in_domain(w["graph"])   # every witness inside the stated domain


def test_plain_double_stars_certified_from_n27():
    assert AH_SPECTRAL_MATCHING.certify(double_star(12, 13)) is not None    # n=27
    assert AH_SPECTRAL_MATCHING.certify(double_star(13, 13)) is not None    # n=28
    assert AH_SPECTRAL_MATCHING.certify(double_star(11, 11)) is None        # n=24 — still holds


# --- the hunter machinery ------------------------------------------------------------------------
def test_smoke_hunts_find_certified_witnesses_instantly():
    o1 = hunt(CHI_LE_DELTA, n=4, seed=0, steps=300)
    assert o1.status == "certified_counterexample" and o1.certificate["chi"] > o1.certificate["Delta"]
    o2 = hunt(CONN_HAMILTONIAN, n=5, seed=0, steps=300)
    assert o2.status == "certified_counterexample"


def test_tree_matching_number_agrees_with_exact():
    rng = random.Random(11)
    for _ in range(120):
        n = rng.randrange(2, 12)
        es = random_tree(n, rng)
        assert tree_matching_number(es, n) == matching_number(Graph(n, frozenset(es)))


def test_power_iteration_anchors():
    assert abs(lambda1_power(cycle(5)) - 2.0) < 1e-9
    assert abs(lambda1_power(double_star(12, 12), 400) - 4.0) < 1e-6      # analytic λ₁ = 4


def test_hunts_and_calibration_are_deterministic():
    a = hunt(CHI_LE_DELTA, n=4, seed=3, steps=200)
    b = hunt(CHI_LE_DELTA, n=4, seed=3, steps=200)
    assert (a.status, a.steps, a.best_score) == (b.status, b.steps, b.best_score)
    assert [w["n"] for w in ah_calibration(20)] == [w["n"] for w in ah_calibration(20)]


def test_db_entries_carry_the_honesty_fields():
    for c in CONJECTURES.values():
        assert c.status in {"refuted_in_literature", "open"} and c.source and c.domain
    assert "TRANSCRIPTION CAVEAT" in AH_SPECTRAL_MATCHING.notes    # the human source-check is recorded
