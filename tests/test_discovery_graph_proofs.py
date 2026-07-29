"""Discovery — CONSTRUCTIVE certificates for the surviving coloring laws (discover → refute → prove,
in its honest bounded form): explicit witnesses, independently re-checked; the checker rejects fakes."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.graph_proofs import (
    Certificate,
    certify_chi_le_delta_plus_1,
    certify_frontier_laws,
    certify_omega_le_chi,
    check_certificate,
    greedy_coloring,
    max_clique,
)
from mathhead.discovery.invariants import max_degree
from mathhead.discovery.objects import Graph


def _graphs_up_to(n):
    return [g for k in range(n + 1) for g in generate_graphs(k)]


_K4 = Graph.from_edges(4, [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
_C5 = Graph.from_edges(5, [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)])
_P4 = Graph.from_edges(4, [(0, 1), (1, 2), (2, 3)])


def test_greedy_coloring_is_proper_and_within_delta_plus_1():
    for g in _graphs_up_to(5):
        if g.n == 0:
            continue
        color = greedy_coloring(g)
        assert all(color[u] != color[v] for (u, v) in g.edges)          # proper
        assert len(set(color.values())) <= max_degree(g) + 1            # ≤ Δ+1 colors


def test_max_clique_is_a_clique_and_matches_clique_number():
    assert set(max_clique(_K4)) == {0, 1, 2, 3}
    for g in _graphs_up_to(4):
        c = max_clique(g)
        assert all(g.has_edge(a, b) for a in c for b in c if a < b)


def test_chi_le_delta_plus_1_certificate_realizes_the_bound():
    cert = certify_chi_le_delta_plus_1(_K4)
    assert cert.checked and cert.kind == "upper"
    assert cert.witness["colors_used"] <= max_degree(_K4) + 1
    assert cert.certainty == "constructive_bounded"        # honest: witnessed, not universally proved


def test_omega_le_chi_certificate_is_solver_double_confirmed():
    cert = certify_omega_le_chi(_K4)
    assert cert.checked and cert.kind == "lower"
    assert cert.witness["clique_size"] == 4
    assert cert.extra["clique_not_(omega-1)_colorable"] is True    # K4 not 3-colorable (MathHead)


def test_every_certificate_over_the_sample_passes_independent_check():
    certs = certify_frontier_laws(_graphs_up_to(5))
    assert certs and all(c.checked for c in certs)
    laws = {c.law for c in certs}
    assert "chromatic_number <= max_degree + 1" in laws
    assert "clique_number <= chromatic_number" in laws
    assert "chromatic_number <= num_vertices" in laws


def test_status_is_honestly_bounded_not_proved():
    # constructive_bounded is stronger than bounded_check but is NOT a universal proof
    for c in certify_frontier_laws(_graphs_up_to(3)):
        assert c.certainty == "constructive_bounded"
        assert c.argument                                  # the universal reason is recorded...
        # ...but nothing here claims PROVED / universal — that needs the logic kernel


def test_checker_rejects_a_tampered_coloring():
    # M-spirit: the independent checker must REJECT a witness that does not realize the bound
    cert = certify_chi_le_delta_plus_1(_K4)
    assert check_certificate(cert, _K4)                    # the honest one passes
    bad = Certificate(cert.law, cert.graph_key, "upper",
                      {"coloring": {0: 0, 1: 0, 2: 0, 3: 0}, "colors_used": 1},   # all same color
                      True, "constructive_bounded")
    assert check_certificate(bad, _K4) is False            # not proper (K4 edges monochromatic)


def test_checker_rejects_a_fake_clique():
    cert = certify_omega_le_chi(_P4)
    fake = Certificate("clique_number <= chromatic_number", cert.graph_key, "lower",
                       {"clique": [0, 1, 2, 3], "clique_size": 4}, True)   # P4 has no K4
    assert check_certificate(fake, _P4) is False


def test_certificates_are_deterministic():
    a = [(c.law, c.graph_key, c.checked) for c in certify_frontier_laws(_graphs_up_to(4))]
    b = [(c.law, c.graph_key, c.checked) for c in certify_frontier_laws(_graphs_up_to(4))]
    assert a == b
