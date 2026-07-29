"""Discovery — graph-domain structural explanations (WHY the laws hold), checked on the sample."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.structural_explanations import (
    explain_clique_chromatic,
    explain_hamiltonian_min_degree,
    explain_handshake,
    structural_explanations,
)


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


def test_handshake_double_count_verifies():
    e = explain_handshake(_graphs_up_to(5))
    assert e["verified"] is True
    assert e["identity"] == "2·|E| = Σ deg(v)"
    assert "double counting" in e["reason"] and e["status"] == "structural_argument"


def test_clique_chromatic_explanation_verifies():
    e = explain_clique_chromatic(_graphs_up_to(5))
    assert e["verified"] is True and e["identity"] == "ω ≤ χ"
    assert "DISTINCT colors" in e["reason"]


def test_hamiltonian_min_degree_explanation_verifies():
    e = explain_hamiltonian_min_degree(_graphs_up_to(5))
    assert e["verified"] is True
    assert "two DISTINCT edges" in e["reason"]


def test_all_structural_explanations_carry_a_verified_conclusion():
    exps = structural_explanations(_graphs_up_to(5))
    assert len(exps) == 3
    assert all(e["verified"] and e["status"] == "structural_argument" for e in exps)
    # honest: a structural argument, not a machine-checked proof
    assert all("proved" not in e["status"] for e in exps)


def test_explanations_render_shape_matches_report():
    # each explanation has the identity/explains/reason keys the report's EXPLANATIONS section renders
    for e in structural_explanations(_graphs_up_to(3)):
        assert {"identity", "explains", "reason"} <= set(e)
