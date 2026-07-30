"""Discovery W0 (breadth) — filter trivial ratio & monotone patterns."""
from mathhead.discovery.families import complete
from mathhead.discovery.pattern_mining import constant_ratios, monotonic_trends
from mathhead.discovery.trivial_filter import nontrivial_ratios, nontrivial_trends

_KN = [complete(n) for n in range(2, 8)]


def test_constant_invariant_trend_is_dropped():
    # num_components ≡ 1 on complete graphs → a fake "non_decreasing" trend, must be filtered
    raw = {t.invariant for t in monotonic_trends(_KN, "num_vertices")}
    clean = {t.invariant for t in nontrivial_trends(_KN, "num_vertices")}
    assert "num_components" in raw and "num_components" not in clean


def test_real_trends_survive_the_filter():
    clean = {t.invariant: t.direction for t in nontrivial_trends(_KN, "num_vertices")}
    for nm in ("num_edges", "sum_degrees", "num_triangles"):
        assert clean[nm] == "strictly_increasing"


def test_handshake_ratio_survives_because_both_sides_vary():
    ratios = {(p.numerator, p.denominator) for p in nontrivial_ratios(_KN)}
    assert ("sum_degrees", "num_edges") in ratios                 # a genuine relation, kept


def test_accidental_ratio_over_a_single_object_is_dropped():
    # on one graph every invariant is constant, so every ratio is accidental → all filtered out
    single = [complete(3)]
    assert constant_ratios(single) != []                         # raw finds some
    assert nontrivial_ratios(single) == []                       # all dropped as accidental


def test_filters_only_remove_never_add():
    trends_clean = nontrivial_trends(_KN, "num_vertices")
    trends_raw = monotonic_trends(_KN, "num_vertices")
    assert len(trends_clean) <= len(trends_raw)
    assert all(t in trends_raw for t in trends_clean)


def test_filters_are_deterministic():
    assert nontrivial_trends(_KN, "num_vertices") == nontrivial_trends(_KN, "num_vertices")
    assert nontrivial_ratios(_KN) == nontrivial_ratios(_KN)
