"""Discovery O4 — multi-path invariant consistency check (the engine verifies its own measurements)."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.adversarial_objects import stress_set
from mathhead.discovery.cross_check import (
    all_consistent,
    cross_check,
    cross_check_num_edges,
    disagreements,
)


def test_num_edges_agrees_across_four_routes_on_K4():
    k4 = generate_graphs(4)[-1]
    c = cross_check_num_edges(k4)
    assert c.agree and set(c.methods.values()) == {6}   # count = Σdeg/2 = trace(A²)/2 = Σλ²/2 = 6
    assert len(c.methods) == 4                           # all four independent routes present


def test_num_triangles_agrees_across_routes_on_K4():
    k4 = generate_graphs(4)[-1]
    tri = next(c for c in cross_check(k4) if c.quantity == "num_triangles")
    assert tri.agree and set(tri.methods.values()) == {4}


def test_all_graphs_are_consistent_with_the_mathhead_spectral_route():
    graphs = [g for n in range(6) for g in generate_graphs(n)]
    assert all_consistent(graphs)                        # includes the MathHead Σλ^k route
    assert disagreements(graphs) == []


def test_pure_paths_are_consistent_on_the_adversarial_stress_set():
    # fast route (no MathHead): degenerate + extreme + random graphs must still cross-check
    assert all_consistent(stress_set(6), use_mathhead=False)


def test_cross_check_is_deterministic():
    g = generate_graphs(5)[10]
    a = [(c.quantity, c.methods) for c in cross_check(g)]
    b = [(c.quantity, c.methods) for c in cross_check(g)]
    assert a == b
