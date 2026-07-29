"""Discovery — the 2nd graph→FRONTIER bridge: Hamiltonian cycles confirmed by MathHead's
hamiltonian_path, plus mined implications (Dirac rediscovered; connected⟹Hamiltonian refuted)."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.hamiltonicity import (
    ImplicationFinding,
    hamiltonicity_laws,
    verify_hamiltonicity,
)
from mathhead.discovery.invariants import is_hamiltonian
from mathhead.discovery.objects import Graph


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


_K3 = Graph.from_edges(3, [(0, 1), (1, 2), (0, 2)])                   # triangle → Hamiltonian
_P3 = Graph.from_edges(3, [(0, 1), (1, 2)])                          # path → not Hamiltonian
_C4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3), (0, 3)])          # 4-cycle → Hamiltonian
_K4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
_STAR4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3)])              # star → not Hamiltonian


# --- exact invariant on named graphs ----------------------------------------------------------

def test_is_hamiltonian_on_named_graphs():
    assert is_hamiltonian(_K3) is True
    assert is_hamiltonian(_C4) is True
    assert is_hamiltonian(_K4) is True
    assert is_hamiltonian(_P3) is False        # a path has no cycle
    assert is_hamiltonian(_STAR4) is False     # a star has no cycle
    assert is_hamiltonian(Graph.from_edges(2, [(0, 1)])) is False   # n<3 convention


# --- MathHead frontier confirms the backtracking answer ---------------------------------------

def test_mathhead_confirms_hamiltonian_cycle_of_C4():
    v = verify_hamiltonicity(_C4)
    assert v.hamiltonian and v.confirmed and v.certainty == "solver_verified"


def test_mathhead_confirms_non_hamiltonian_path():
    v = verify_hamiltonicity(_P3)
    assert v.hamiltonian is False and v.confirmed and v.certainty == "solver_verified"


def test_small_n_is_trivial_and_skips_mathhead():
    v = verify_hamiltonicity(Graph.from_edges(2, [(0, 1)]))
    assert v.hamiltonian is False and v.confirmed and v.certainty == "trivial"


def test_every_small_graph_hamiltonicity_is_confirmed_by_mathhead():
    for g in _graphs_up_to(5):
        if g.n == 0:
            continue
        assert verify_hamiltonicity(g).confirmed


# --- mined implications -----------------------------------------------------------------------

def test_necessary_conditions_hold_and_dirac_is_rediscovered():
    by_stmt = {f.statement: f for f in hamiltonicity_laws(_graphs_up_to(5))}
    assert by_stmt["Hamiltonian => connected"].status == "no_counterexample_within_bound"
    assert by_stmt["Hamiltonian => min_degree >= 2"].status == "no_counterexample_within_bound"
    dirac = by_stmt["(n>=3 and min_degree >= n/2) => Hamiltonian [Dirac]"]
    assert dirac.status == "no_counterexample_within_bound" and dirac.support > 0


def test_connected_does_not_imply_hamiltonian_minimal_witness_is_P3():
    by_stmt = {f.statement: f for f in hamiltonicity_laws(_graphs_up_to(5))}
    false = by_stmt["(connected and n>=3) => Hamiltonian"]
    assert false.status == "refuted"
    ce = false.counterexample
    assert ce["n"] == 3 and len(ce["edges"]) == 2          # P3: a connected 3-path, no cycle


def test_findings_are_labeled_bounded_check_and_deterministic():
    a = hamiltonicity_laws(_graphs_up_to(4))
    b = hamiltonicity_laws(_graphs_up_to(4))
    assert all(isinstance(f, ImplicationFinding) and f.certainty == "bounded_check" for f in a)
    assert [(f.statement, f.status) for f in a] == [(f.statement, f.status) for f in b]
