"""Discovery v2B3 — the LIVE hunt on Frankl's union-closed sets conjecture (open)."""
import pytest

from mathhead.discovery.frankl import (
    FRANKL_INFO,
    certify_violation,
    frequencies,
    guard_exhaustive,
    guard_sampled,
    hunt_frankl,
    is_union_closed,
    union_closure,
)


def test_union_closure_and_check():
    fam = union_closure([0b001, 0b010])
    assert fam == frozenset({0b001, 0b010, 0b011}) and is_union_closed(fam)
    assert not is_union_closed(frozenset({0b001, 0b010}))          # missing the union
    assert union_closure([1, 2, 4, 8, 16], cap=10) is None         # explicit refusal, no truncation


def test_frequencies_are_exact():
    fam = frozenset({0b001, 0b011, 0b111})
    assert frequencies(fam, 3) == [3, 2, 1]


def test_formalization_guard_exhaustive_small_universes():
    # EVERY union-closed family over universe 3 satisfies the conjecture — 121 of them, exhaustively.
    rep = guard_exhaustive(3)
    assert rep.union_closed == 121 and rep.formalization_ok


def test_power_set_equality_is_refused():
    # power set of [3]: every element in exactly half the sets (4 of 8) — 'at least half' HOLDS with
    # equality, so the certifier must refuse (the strict-inequality boundary, exact integers)
    assert certify_violation(frozenset(range(8)), 3) is None


def test_trivial_and_bogus_families_never_certify():
    assert certify_violation(frozenset(), 3) is None               # empty family
    assert certify_violation(frozenset({0}), 3) is None            # {∅} — excluded by the statement
    assert certify_violation(frozenset({0b001, 0b010}), 3) is None  # NOT union-closed → rejected


def test_live_hunt_reports_honestly():
    h = hunt_frankl(m=6, seed=0, steps=800)
    assert h.status in {"not_found_within_budget", "certified_counterexample"}
    if h.status == "not_found_within_budget":
        assert h.certificate is None and h.best_score >= 0         # no witness ⇒ no negative score kept
    else:                                                          # would refute a 45-year conjecture —
        assert h.certificate["certainty"] == "exact_integer_certificate"   # only with an exact witness


# ---- v4F5: the m >= 5 sampled guard (exhaustion refused there — sampling, honestly labelled) ----

def test_exhaustive_guard_refuses_m5_and_sampling_is_the_labelled_substitute():
    with pytest.raises(ValueError):                        # 2^(2^5) = 2^32 families: refuse
        guard_exhaustive(5)
    rep = guard_sampled(5, samples=300, seed=0)
    assert rep.violations == 0                             # a violation would refute Frankl
    assert 0 < rep.distinct_families <= rep.samples <= 300  # cap-refused draws are not counted
    assert rep.max_family_size >= 2
    assert "SAMPLED, not exhaustive" in rep.coverage and "proves NOTHING" in rep.coverage


def test_sampled_guard_is_deterministic_per_seed():
    a = guard_sampled(5, samples=200, seed=3)
    b = guard_sampled(5, samples=200, seed=3)
    assert (a.samples, a.distinct_families, a.max_family_size) == \
           (b.samples, b.distinct_families, b.max_family_size)
    c = guard_sampled(5, samples=200, seed=4)              # a different walk, still exact verdicts
    assert c.violations == 0


def test_hunt_is_deterministic_and_info_is_honest():
    a = hunt_frankl(m=6, seed=2, steps=400)
    b = hunt_frankl(m=6, seed=2, steps=400)
    assert (a.status, a.best_score, a.best_family_size) == (b.status, b.best_score, b.best_family_size)
    assert FRANKL_INFO["status"] == "open" and "OPEN" in FRANKL_INFO["source"]
