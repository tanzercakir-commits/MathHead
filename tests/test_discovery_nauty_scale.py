"""Discovery v2A4 — scale generation via nauty/geng, cross-validated against the pure generator."""
import pytest

from mathhead.discovery.nauty_scale import (
    cross_validate,
    decode_graph6,
    extended_radar_sequences,
    geng_available,
    geng_count,
    geng_graphs,
)

pytestmark = pytest.mark.skipif(not geng_available(), reason="nauty/geng not installed")


def test_geng_agrees_with_the_pure_generator_class_by_class():
    # equal canonical-key SETS for n<=5 and equal count at n=6 — two independent generators agree
    assert cross_validate()


def test_geng_extends_the_graph_count_sequence_correctly():
    # continuation of A000088 beyond the pure generator's honest bound
    assert [geng_count(n) for n in range(11)] == [
        1, 1, 2, 4, 11, 34, 156, 1044, 12346, 274668, 12005168]


def test_decoded_graphs_are_valid_and_complete():
    graphs = geng_graphs(5)
    assert len(graphs) == 34 and len({frozenset(g.edges) for g in graphs}) == 34
    assert all(g.n == 5 for g in graphs)


def test_decode_graph6_edge_cases():
    assert decode_graph6("C?").num_edges == 0            # n=4, empty
    k4 = decode_graph6("C~")                             # n=4, all bits set → K4
    assert k4.num_edges == 6


def test_filtered_counts_match_the_radar_small_n_values():
    # geng's -t class agrees with the engine's independently-computed triangle-free counts
    from mathhead.discovery.oeis_radar import extract_natural_sequences
    tri = next(s for s in extract_natural_sequences() if s.name == "triangle_free_graphs")
    geng_prefix = tuple(geng_count(n, triangle_free=True) for n in range(len(tri.terms)))
    assert geng_prefix == tri.terms                      # third independent path, same numbers


def test_extended_sequences_grow_the_pending_prefixes():
    seqs = extended_radar_sequences(9)
    assert len(seqs["triangle_free_graphs"]) == 10       # 10 terms for the human's OEIS lookup
    assert seqs["connected_graphs"][:7] == (1, 1, 1, 2, 6, 21, 112)


def test_hard_cap_refuses_rather_than_truncates():
    with pytest.raises(ValueError, match="refuse"):
        geng_graphs(9, hard_cap=1000)                    # 274668 > 1000 → explicit refusal


def test_generation_is_deterministic():
    a = [frozenset(g.edges) for g in geng_graphs(5)]
    b = [frozenset(g.edges) for g in geng_graphs(5)]
    assert a == b
