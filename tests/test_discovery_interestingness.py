"""Discovery Track W1 — a transparent, heuristic interestingness score with a per-component breakdown."""
from mathhead.discovery.interestingness import (
    WEIGHTS,
    Interestingness,
    rank,
    score,
    triviality,
)

_STRONG = {"statement": "(n**3 - n) % 6 == 0", "status": "proved", "modulus": 6,
           "kernel_verified": True}
_HANDSHAKE = {"statement": "2*num_edges = sum_degrees", "status": "empirical",
              "scope": "all graphs n<=6", "support": 156}
_TRIVIAL = {"statement": "chromatic_number <= num_vertices", "status": "no_counterexample_within_bound"}
_DEGENERATE = {"statement": "chromatic_number <= max_degree", "status": "refuted",
               "counterexample": {"n": 1, "lhs": 1, "rhs": 0}}


def test_score_has_all_components_and_is_in_range():
    s = score(_STRONG, [_STRONG, _HANDSHAKE])
    assert isinstance(s, Interestingness)
    assert set(s.components) == set(WEIGHTS)
    assert 0.0 <= s.total <= 1.0


def test_strong_universal_fact_beats_the_trivial_bound():
    ranked = rank([_STRONG, _HANDSHAKE, _TRIVIAL, _DEGENERATE])
    order = [s.statement for s, _ in ranked]
    assert order[0] == _STRONG["statement"]                 # composite modulus + kernel-verified + universal
    assert order[-1] == _TRIVIAL["statement"]               # tautological/textbook-trivial sinks


def test_proved_fact_is_maximally_general():
    assert score(_STRONG).components["generality"] == 1.0   # holds for all n
    assert score(_HANDSHAKE).components["generality"] == 0.8  # all graphs, but empirical


def test_kernel_verified_is_most_useful():
    assert score(_STRONG).components["usefulness"] == 0.9
    assert score(_HANDSHAKE).components["usefulness"] == 0.5


def test_refuted_is_surprising_but_degenerate_witness_is_penalized():
    s = score(_DEGENERATE)
    assert s.components["surprise"] == 0.9                   # a plausible claim that was false
    assert triviality(_DEGENERATE) >= 0.3                   # ...but the n=1 witness is degenerate


def test_trivial_bound_is_penalized_to_low_novelty():
    assert score(_TRIVIAL).components["novelty"] <= 0.2


def test_ranking_is_deterministic():
    items = [_STRONG, _HANDSHAKE, _TRIVIAL, _DEGENERATE]
    a = [(s.statement, s.total) for s, _ in rank(items)]
    b = [(s.statement, s.total) for s, _ in rank(items)]
    assert a == b


def test_connectivity_rewards_shared_invariants():
    a = {"statement": "num_edges <= num_vertices", "status": "empirical"}
    b = {"statement": "num_triangles <= num_edges", "status": "empirical"}   # shares num_edges
    lonely = {"statement": "is_hamiltonian => connected", "status": "empirical"}
    ctx = [a, b, lonely]
    assert score(a, ctx).components["connectivity"] > 0.0   # shares a token with b
