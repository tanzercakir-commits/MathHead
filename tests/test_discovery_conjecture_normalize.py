"""Discovery P5 — normalize + deduplicate conjectures across mining sources."""
from types import SimpleNamespace

from mathhead.discovery.conjecture_normalize import (
    _canonical,
    from_law,
    normalize_conjectures,
)
from mathhead.discovery.families import complete
from mathhead.discovery.pattern_mining import constant_ratios
from mathhead.discovery.relations import discover_linear_laws

_KN = [complete(n) for n in range(2, 8)]


def _law(coeffs, const, expr):
    return SimpleNamespace(coeffs=coeffs, const=const, expression=expr)


def test_sign_and_scale_variants_share_one_canonical_key():
    a = _canonical({"num_edges": 2, "sum_degrees": -1}, 0)     # 2E − Σdeg = 0
    b = _canonical({"sum_degrees": 1, "num_edges": -2}, 0)     # Σdeg − 2E = 0  (the ratio's equation)
    c = _canonical({"num_edges": 4, "sum_degrees": -2}, 0)     # scaled ×2
    assert a == b == c


def test_handshake_is_corroborated_by_the_linear_and_ratio_miners():
    norm = normalize_conjectures(linear=discover_linear_laws(_KN), ratios=constant_ratios(_KN))
    handshake = next(nc for nc in norm if "num_edges" in nc.representative
                     and "sum_degrees" in nc.representative)
    assert handshake.corroboration == 2                        # found independently as a law AND a ratio
    assert {s[0] for s in handshake.sources} == {"linear", "ratio"}


def test_distinct_conjectures_are_not_over_merged():
    laws = [_law({"a": 1, "b": -1}, 0, "a = b"), _law({"a": 1, "c": -1}, 0, "a = c")]
    norm = normalize_conjectures(linear=laws)
    assert len(norm) == 2


def test_nonlinear_law_does_not_collide_with_a_linear_one():
    lin = _law({"num_edges": 1, "sum_degrees": -1}, 0, "num_edges = sum_degrees")
    quad = _law({"num_edges^2": 1, "sum_degrees": -1}, 0, "num_edges^2 = sum_degrees")
    norm = normalize_conjectures(linear=[lin], nonlinear=[quad])
    assert len(norm) == 2                                       # distinct feature sets ⇒ distinct keys


def test_results_sorted_most_corroborated_first():
    norm = normalize_conjectures(linear=discover_linear_laws(_KN), ratios=constant_ratios(_KN))
    corr = [nc.corroboration for nc in norm]
    assert corr == sorted(corr, reverse=True)


def test_provenance_is_preserved():
    law = _law({"a": 1, "b": -1}, 0, "a = b")
    norm = normalize_conjectures(linear=[law])
    assert norm[0].sources == [("linear", "a = b")]


def test_empty_input_gives_empty_output():
    assert normalize_conjectures() == []


def test_from_law_and_normalization_are_deterministic():
    law = _law({"a": 2, "b": -1}, 0, "2a = b")
    assert from_law(law) == from_law(law)
    n1 = normalize_conjectures(linear=discover_linear_laws(_KN))
    n2 = normalize_conjectures(linear=discover_linear_laws(_KN))
    assert [nc.representative for nc in n1] == [nc.representative for nc in n2]
