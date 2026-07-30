"""Discovery P0 (breadth) — ratio & monotonicity pattern mining."""
from fractions import Fraction

from mathhead.discovery.families import complete
from mathhead.discovery.generate import generate_graphs
from mathhead.discovery.pattern_mining import constant_ratios, monotonic_trends

_KN = [complete(n) for n in range(2, 8)]           # K_2 .. K_7 (all have edges)
_ALL = [g for n in range(1, 6) for g in generate_graphs(n)]


def test_constant_ratio_rediscovers_handshake_as_a_ratio():
    ratios = {(p.numerator, p.denominator): p.ratio for p in constant_ratios(_KN)}
    assert ratios[("sum_degrees", "num_edges")] == Fraction(2)     # Σdeg / |E| = 2, exactly
    assert all(p.status == "empirical" for p in constant_ratios(_KN))


def test_ratio_skips_pairs_with_a_zero_denominator_somewhere():
    # over ALL graphs, edgeless graphs make num_edges 0 → sum_degrees/num_edges is undefined, skipped
    ratios = {(p.numerator, p.denominator) for p in constant_ratios(_ALL)}
    assert ("sum_degrees", "num_edges") not in ratios


def test_only_the_ge_one_direction_is_reported():
    for p in constant_ratios(_KN):
        assert p.ratio > 1                                          # the 1/2 inverse is deduped away


def test_monotonic_trends_over_complete_graphs():
    trends = {t.invariant: t.direction for t in monotonic_trends(_KN, "num_vertices")}
    for nm in ("num_edges", "sum_degrees", "num_triangles", "max_degree"):
        assert trends[nm] == "strictly_increasing"                 # all grow with n on Kₙ


def test_monotonic_direction_classification():
    # a decreasing invariant on a hand-ordered sample is caught as strictly_decreasing
    graphs = [complete(n) for n in range(2, 6)]
    # order by num_edges DESC → num_vertices is strictly decreasing along that order
    trends = {t.invariant: t.direction for t in monotonic_trends(graphs, "num_edges")}
    assert trends["num_vertices"] == "strictly_increasing"         # num_vertices grows with num_edges


def test_empty_and_singleton_samples_return_nothing():
    assert constant_ratios([]) == []
    assert monotonic_trends([complete(3)], "num_vertices") == []   # need >= 2 points for a trend


def test_mining_is_deterministic():
    assert [(p.numerator, p.denominator, p.ratio) for p in constant_ratios(_KN)] == \
           [(p.numerator, p.denominator, p.ratio) for p in constant_ratios(_KN)]
    assert [(t.invariant, t.direction) for t in monotonic_trends(_KN, "num_vertices")] == \
           [(t.invariant, t.direction) for t in monotonic_trends(_KN, "num_vertices")]
