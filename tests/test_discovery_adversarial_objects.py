"""Discovery N5 — random / adversarial / extreme object generators (robustness stress-test)."""
from math import comb

from mathhead.discovery.adversarial_objects import (
    degenerate_graphs,
    extreme_graphs,
    random_graphs,
    stress_set,
)
from mathhead.discovery.invariants import INVARIANTS, chromatic_number, is_connected, num_edges


def test_no_invariant_crashes_on_the_stress_set():
    crashes = []
    for g in stress_set(6):
        for name, fn in INVARIANTS.items():
            try:
                fn(g)
            except Exception as e:                          # noqa: BLE001 (we want to catch any)
                crashes.append((name, g.n, str(e)))
    assert crashes == []                                    # robust on degenerate + extreme + random


def test_extreme_includes_complete_and_complete_minus_edge():
    graphs = list(extreme_graphs(5))
    edges = sorted(num_edges(g) for g in graphs)
    assert comb(5, 2) in edges and comb(5, 2) - 1 in edges  # K5 and K5−e both present


def test_degenerate_includes_a_disconnected_graph():
    assert any(not is_connected(g) for g in degenerate_graphs(4))


def test_seeded_random_is_reproducible():
    a = [sorted(g.edges) for g in random_graphs(6, 5, seed=7)]
    b = [sorted(g.edges) for g in random_graphs(6, 5, seed=7)]
    assert a == b
    c = [sorted(g.edges) for g in random_graphs(6, 5, seed=8)]
    assert a != c                                           # a different seed gives different graphs


def test_stress_set_is_deterministic_and_nonempty():
    assert [g.n for g in stress_set(5)] == [g.n for g in stress_set(5)]
    assert len(stress_set(5)) > 20
