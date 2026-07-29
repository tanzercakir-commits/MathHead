"""Discovery — the graph→FRONTIER bridge: chromatic number confirmed by MathHead's graph_coloring,
plus the classic coloring sandwich ω ≤ χ ≤ Δ+1 (and the refuted χ ≤ Δ)."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.coloring import (
    ColoringBoundFinding,
    coloring_bounds,
    verify_chromatic_number,
)
from mathhead.discovery.invariants import chromatic_number, clique_number
from mathhead.discovery.objects import Graph


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


# --- exact invariants on named graphs ---------------------------------------------------------

_K3 = Graph.from_edges(3, [(0, 1), (1, 2), (0, 2)])
_K4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
_C4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3), (0, 3)])           # even cycle → bipartite
_PATH3 = Graph.from_edges(3, [(0, 1), (1, 2)])
_EMPTY3 = Graph.from_edges(3, [])


def test_chromatic_number_of_named_graphs():
    assert chromatic_number(_K3) == 3          # triangle
    assert chromatic_number(_K4) == 4          # complete graph on 4
    assert chromatic_number(_C4) == 2          # even cycle is bipartite
    assert chromatic_number(_PATH3) == 2       # any path/tree with an edge
    assert chromatic_number(_EMPTY3) == 1      # no edges → one color


def test_clique_number_of_named_graphs():
    assert clique_number(_K4) == 4
    assert clique_number(_C4) == 2             # no triangle in a 4-cycle
    assert clique_number(_EMPTY3) == 1


# --- MathHead frontier confirms the backtracking χ (sat at χ, unsat at χ−1) --------------------

def test_mathhead_confirms_chromatic_number_of_K4():
    v = verify_chromatic_number(_K4)
    assert v.chi == 4 and v.confirmed and v.certainty == "solver_verified"


def test_mathhead_confirms_chromatic_number_of_triangle():
    v = verify_chromatic_number(_K3)
    assert v.chi == 3 and v.confirmed and v.certainty == "solver_verified"


def test_trivial_chromatic_number_skips_mathhead():
    v = verify_chromatic_number(_EMPTY3)       # χ=1 → trivial, MathHead not invoked
    assert v.chi == 1 and v.confirmed and v.certainty == "trivial"


def test_every_small_graph_chi_is_confirmed_by_mathhead():
    for g in _graphs_up_to(5):
        if g.n == 0:
            continue
        assert verify_chromatic_number(g).confirmed


# --- mined coloring inequalities --------------------------------------------------------------

def test_classic_coloring_sandwich_holds_and_chi_le_delta_is_refuted():
    by_stmt = {f.statement: f for f in coloring_bounds(_graphs_up_to(5))}
    assert by_stmt["clique_number <= chromatic_number"].status == "no_counterexample_within_bound"
    assert by_stmt["chromatic_number <= max_degree + 1"].status == "no_counterexample_within_bound"
    assert by_stmt["chromatic_number <= num_vertices"].status == "no_counterexample_within_bound"
    false = by_stmt["chromatic_number <= max_degree"]
    # the MINIMAL counterexample is the single vertex (χ=1 > Δ=0), found before the triangle —
    # refute-first reports the absolute smallest witness, not the classic (triangle) one.
    assert false.status == "refuted" and false.counterexample["n"] == 1
    assert false.counterexample["lhs"] == 1 and false.counterexample["rhs"] == 0


def test_bounds_are_labeled_bounded_check_not_proven():
    for f in coloring_bounds(_graphs_up_to(3)):
        assert isinstance(f, ColoringBoundFinding)
        assert f.certainty == "bounded_check"      # exact over the sample, not proven for all n


def test_coloring_bounds_are_deterministic():
    a = [(f.statement, f.status) for f in coloring_bounds(_graphs_up_to(4))]
    b = [(f.statement, f.status) for f in coloring_bounds(_graphs_up_to(4))]
    assert a == b
