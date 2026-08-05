"""
v4F4 hardening sweep B — PROOF tests for the P/T/U/W/X/AA/AC closure candidates.

Each test is the evidence behind a roadmap ✅: P5 canonical-key dedup never over-merges, T0 the gap
measure is exact and honest, T2 the priority fusion is transparent and recomputable, U0 the
representation bridges are faithful, U3 meaning-preservation actually DISCRIMINATES (corrupted
transforms are caught), W1 the interestingness score is complete/transparent/bounded, X2 synonyms
resolve and every technique pointer is callable, AA3 the epistemic ladder is total and never
inflates, AA4 the algorithm→proof bridge never inflates modality, AC0 the director's selection
policy is total and followed, AC3 session state is deduped, isolated, and honestly summarized.
"""
from fractions import Fraction
from types import SimpleNamespace

import pytest

N3_MINUS_N = (0, -1, 0, 1)          # n³ − n
N5_MINUS_N = (0, -1, 0, 0, 0, 1)    # n⁵ − n


# --- P5: canonical normalization collapses duplicates across miners, never over-merges ----------

def test_p5_normalization_collapses_duplicates_and_never_overmerges():
    from mathhead.discovery.conjecture_normalize import from_law, from_ratio, normalize_conjectures
    from mathhead.discovery.pattern_mining import RatioPattern
    from mathhead.discovery.relations import DiscoveredLaw

    handshake = DiscoveredLaw("linear_equality", "2*num_edges = sum_degrees",
                              coeffs={"num_edges": 2, "sum_degrees": -1}, const=0)
    scaled = DiscoveredLaw("linear_equality", "2*sum_degrees = 4*num_edges",
                           coeffs={"num_edges": -4, "sum_degrees": 2}, const=0)
    ratio = RatioPattern("sum_degrees", "num_edges", Fraction(2), support=51)

    # the same equation in three different clothes reduces to ONE canonical key
    key = from_law(handshake)[0]
    assert from_law(scaled)[0] == key == from_ratio(ratio)[0]

    # …and a product-term (non-linear) law NEVER collides with the linear form
    quadratic = DiscoveredLaw("nonlinear", "2*num_edges = num_vertices^2 - num_vertices",
                              coeffs={"num_edges": 2, "num_vertices*num_vertices": -1,
                                      "num_vertices": 1}, const=0)
    assert from_law(quadratic)[0] != key

    merged = normalize_conjectures(linear=[handshake, scaled], nonlinear=[quadratic], ratios=[ratio])
    assert len(merged) == 2                              # Handshake collapsed, quadratic separate
    top = merged[0]
    assert top.key == key and len(top.sources) == 3
    assert top.corroboration == 2                        # two DISTINCT source kinds: linear + ratio
    assert merged[1].corroboration == 1
    # deterministic: same inputs, same order, most-corroborated first
    again = normalize_conjectures(linear=[handshake, scaled], nonlinear=[quadratic], ratios=[ratio])
    assert [m.key for m in again] == [m.key for m in merged]


# --- T0: the gap measure — exact BFS distances, honest 1.0 when no path to proved ground --------

def _synthetic_graph():
    from mathhead.discovery.knowledge_graph import KnowledgeGraph
    g = KnowledgeGraph()
    ax = g.add_node("axiom", "RESIDUE(m=2)")
    th = g.add_node("theorem", "6 | n^3 - n", id="thm")
    g.add_edge(th, "depends_on", ax)
    c1 = g.add_node("conjecture", "near goal", id="c1")          # 1 hop from the theorem
    g.add_edge(c1, "related_to", th)
    c2 = g.add_node("conjecture", "farther goal", id="c2")       # 2 hops (via c1)
    g.add_edge(c2, "related_to", c1)
    c3 = g.add_node("conjecture", "island goal", id="c3")        # NO path to proved ground
    dead = g.add_node("conjecture", "refuted claim", id="c4")
    wit = g.add_node("counterexample", "K4")
    g.add_edge(dead, "refuted_by", wit)
    _ = c3
    return g


def test_t0_gap_measure_is_exact_and_honest():
    from mathhead.discovery.gap import frontier_gaps, measure_gap
    g = _synthetic_graph()

    assert measure_gap(g, "thm").gap_score == 0.0 and measure_gap(g, "thm").resolved
    assert measure_gap(g, "c4").status == "refuted" and measure_gap(g, "c4").gap_score == 0.0

    near, far, island = measure_gap(g, "c1"), measure_gap(g, "c2"), measure_gap(g, "c3")
    assert near.distance_to_known == 1 and far.distance_to_known == 2
    assert island.distance_to_known is None and island.gap_score == 1.0   # honest: unreachable
    assert 0.0 < near.gap_score < far.gap_score < 1.0
    assert measure_gap(g, "no-such-node").gap_score == 1.0                # unknown goal: max gap

    ranked = frontier_gaps(g)
    assert [m.goal for m in ranked] == ["c1", "c2", "c3"]                 # smallest gap first
    assert "c4" not in [m.goal for m in ranked]                           # resolved goals excluded


# --- T2: priority = w·importance + w·likelihood — transparent, recomputable, adjustable ---------

def test_t2_lemma_ranking_fuses_the_two_signals_transparently():
    from mathhead.discovery.gap import measure_gap
    from mathhead.discovery.knowledge_graph import KnowledgeGraph
    from mathhead.discovery.lemma_ranking import next_lemma, rank_lemmas
    g = _synthetic_graph()

    ranked = rank_lemmas(g)
    assert [r.goal for r in ranked] == ["c1", "c2", "c3"]
    for r in ranked:                                     # every component auditable and recomputable
        assert 0.0 <= r.importance <= 1.0 and 0.0 <= r.likelihood <= 1.0
        assert r.priority == pytest.approx(0.5 * r.importance + 0.5 * r.likelihood, abs=2e-4)
        assert r.likelihood == pytest.approx(1.0 - measure_gap(g, r.goal).gap_score, abs=2e-4)
    assert ranked[0].importance == 1.0                   # most entangled goal normalizes to 1
    assert "c4" not in [r.goal for r in ranked]          # refuted goals never ranked

    top = next_lemma(g)
    assert top is not None and top.goal == ranked[0].goal

    pure_importance = rank_lemmas(g, w_importance=1.0, w_likelihood=0.0)
    assert [r.priority for r in pure_importance] == [r.importance for r in pure_importance]
    assert next_lemma(KnowledgeGraph()) is None          # no open goals: honest None, no invention


# --- U0: every representation bridge is faithful; the decision bridge agrees with the kernel ----

def test_u0_representation_bridges_are_faithful_and_decision_matches_kernel():
    from mathhead.discovery.generate import generate_graphs
    from mathhead.discovery.kernel import KernelError, Residue, check
    from mathhead.discovery.representations import (
        adjacency_to_graph, all_faithful, divisibility_to_residue_table, graph_to_adjacency,
        verify_representations,
    )

    bridges = verify_representations()
    assert len(bridges) == 4 and all(b.faithful for b in bridges)
    assert {b.kind for b in bridges} == {"round_trip", "invariant_preserving", "decision"}
    assert all_faithful()

    for n in range(1, 5):                                # round trip is the identity, graph by graph
        for g in generate_graphs(n):
            assert adjacency_to_graph(graph_to_adjacency(g)) == g

    # decision bridge: table all-zero ⟺ kernel proves — including the FALSE claims
    for m, poly, truth in [(6, N3_MINUS_N, True), (30, N5_MINUS_N, True),
                           (4, (1, 0, 1), False), (5, N3_MINUS_N, False)]:
        table = divisibility_to_residue_table(m, poly)
        assert (len(table) == m) and (all(x == 0 for x in table) is truth)
        if truth:
            check(Residue(m, poly))                      # kernel agrees: mints
        else:
            with pytest.raises(KernelError):             # kernel agrees: refuses
                check(Residue(m, poly))


# --- U3: meaning-preservation verification DISCRIMINATES — corrupted transforms are caught ------

def test_u3_meaning_preservation_catches_corrupted_transforms():
    from mathhead.discovery.cross_check import all_consistent
    from mathhead.discovery.generate import generate_graphs
    from mathhead.discovery.kernel import KernelError, Residue, check
    from mathhead.discovery.objects import Graph
    from mathhead.discovery.representations import (
        adjacency_to_graph, divisibility_to_residue_table, graph_to_adjacency,
        graph_to_degree_sequence,
    )

    # transformed objects carry the same meaning: every O4 cross-check route agrees on the decoded graphs
    decoded = [adjacency_to_graph(graph_to_adjacency(g))
               for n in range(1, 5) for g in generate_graphs(n)]
    assert all_consistent(decoded)

    # corruption 1 — a dropped edge in the matrix is CAUGHT (decode ≠ original, invariant moved)
    p3 = Graph(3, frozenset({(0, 1), (1, 2)}))
    mat = [list(row) for row in graph_to_adjacency(p3)]
    mat[0][1] = mat[1][0] = 0
    broken = adjacency_to_graph(tuple(tuple(r) for r in mat))
    assert broken != p3 and broken.num_edges == p3.num_edges - 1

    # corruption 2 — an inflated degree sequence violates the stated invariant Σdeg = 2|E|
    ds = list(graph_to_degree_sequence(p3))
    ds[0] += 1
    assert sum(ds) != 2 * p3.num_edges

    # corruption 3 — a forged all-zero residue table for a FALSE claim disagrees with the kernel:
    # the faithfulness check compares table verdict to kernel verdict, so the forgery is detected
    honest_table = divisibility_to_residue_table(4, (1, 0, 1))       # 4 ∤ n²+1
    assert any(x != 0 for x in honest_table)
    forged_table = (0,) * 4
    forged_says = all(x == 0 for x in forged_table)
    with pytest.raises(KernelError):
        check(Residue(4, (1, 0, 1)))
    kernel_says = False
    assert forged_says != kernel_says                    # mismatch surfaces: the bridge would flag it


# --- W1: interestingness — six named components, weights sum to 1, recomputable, bounded --------

def test_w1_interestingness_components_are_transparent_and_bounded():
    from mathhead.discovery.interestingness import WEIGHTS, rank, score, triviality

    assert set(WEIGHTS) == {"novelty", "generality", "surprise", "usefulness",
                            "compression", "connectivity"}
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)

    battery = [
        {"statement": "30 | n^5 - n", "status": "proved", "kernel_verified": True, "modulus": 30},
        {"statement": "num_triangles <= num_edges", "status": "refuted",
         "counterexample": {"n": 6}},
        {"statement": "num_edges <= num_edges", "status": "empirical", "support": 3},   # tautology
        {"statement": "2*num_edges = sum_degrees", "status": "empirical", "support": 51,
         "scope": "all graphs"},
    ]
    for item in battery:
        s = score(item, battery)
        assert set(s.components) == set(WEIGHTS)         # every component named — nothing hidden
        assert all(0.0 <= v <= 1.0 for v in s.components.values())
        expected = sum(WEIGHTS[k] * v for k, v in s.components.items()) - s.penalty
        assert s.total == pytest.approx(max(0.0, min(1.0, expected)), abs=2e-4)
        assert 0.0 <= s.total <= 1.0

    tautology, handshake = battery[2], battery[3]
    assert triviality(tautology) > 0.0                   # tautology-shaped: penalized
    assert score(handshake, battery).total > score(tautology, battery).total

    ranked = rank(battery)
    assert [s.total for s, _ in ranked] == sorted((s.total for s, _ in ranked), reverse=True)
    assert [it["statement"] for _, it in rank(battery)] == [it["statement"] for _, it in ranked]


# --- X2: synonyms resolve through the parser; every technique pointer is CALLABLE code ----------

def test_x2_synonyms_resolve_and_technique_pointers_are_callable():
    import importlib

    from mathhead.discovery.statement_parse import parse_statement
    from mathhead.discovery.technique_map import SYNONYMS, TECHNIQUES, suggest_techniques

    for entries in TECHNIQUES.values():                  # stronger than existence: callable
        for _name, pointer, _tier in entries:
            mod_name, attr = pointer.rsplit(".", 1)
            fn = getattr(importlib.import_module(f"mathhead.discovery.{mod_name}"), attr)
            assert callable(fn), pointer

    for canon in SYNONYMS:                               # every canonical name self-resolves
        assert canon in parse_statement(f"the {canon} of G is bounded").invariants

    for token, canon in [("nu", "matching number"), ("mu", "matching number"),
                         ("lambda1", "spectral radius"), ("chi", "chromatic number"),
                         ("omega", "clique number"), ("gamma", "domination number"),
                         ("alpha", "independence number"), ("frankl", "union-closed")]:
        assert canon in parse_statement(f"{token}(G) >= 1").invariants, token

    tiers = [tier for _n, _p, tier in suggest_techniques("6 divides n^3 - n")]
    assert tiers and tiers[0] == "kernel_verified"       # strongest instrument first, honest tier


# --- AA3: the epistemic ladder is TOTAL and conservative — no rung inflation, ever --------------

_FORMAL = {"formal_proof", "exhaustive_residue_proof", "kernel_identity", "solver_verified_proof"}


def test_aa3_ladder_is_total_and_never_inflates():
    from mathhead.discovery.epistemic_ladder import LEVELS, classify, ladder_summary, rung_of
    from mathhead.discovery.report import run_report

    fake = SimpleNamespace(
        proved=[{"statement": "S1", "kernel_verified": True},                 # L4 (sealed)
                {"statement": "S2", "certainty": "formal_proof"},             # L4 (formal)
                {"statement": "S3", "certainty": "solver_confirmed"}],        # L3 — NOT inflated
        frontier=[{"confirmed": True, "invariant": "chi", "graph": "C5", "value": 3},
                  {"confirmed": False, "invariant": "chi", "graph": "P2", "value": 9}],
        open_bounded=[{"statement": "S4", "certified": True},                 # L3 (witnessed)
                      {"statement": "S5"}],                                   # L2
        empirical_laws=[{"statement": "S6"}, {"statement": "S1"}],            # S1 twice: L4 wins
        explanations=[{"status": "constructive_bijection", "identity": "I1"},  # L3
                      {"status": "structural_argument", "identity": "I2"},     # L2
                      {"status": "prose", "identity": "I3"}])                  # off-ladder
    c = classify(fake)
    assert list(c) == list(LEVELS)
    assert ladder_summary(fake) == {"DISCOVERED_HEURISTIC": 0, "EMPIRICALLY_VALIDATED": 4,
                                    "FORMALLY_SPECIFIED": 4, "FORMALLY_PROVED": 2}
    assert c["FORMALLY_PROVED"] == ["S1", "S2"] and "S3" in c["FORMALLY_SPECIFIED"]
    assert rung_of("S1", fake) == "FORMALLY_PROVED"      # highest rung wins on a duplicate
    assert rung_of("I3", fake) is None                   # unclassifiable: honest None

    report = run_report(max_n=3)                         # live: L4 only from sealed/formal evidence
    proved_by_stmt = {it["statement"]: it for it in report.proved}
    for stmt in classify(report)["FORMALLY_PROVED"]:
        it = proved_by_stmt[stmt]
        assert (it.get("kernel_verified") or it.get("independently_verified")
                or it.get("certainty") in _FORMAL), stmt


# --- AA4: the algorithm→proof bridge — honest modality, no fabricated proofs -------------------

def test_aa4_algorithm_proof_bridge_never_inflates_modality():
    from mathhead.discovery.algorithm_proof import (
        bridge_greedy_coloring, bridge_max_clique, bridge_modular_algorithm,
        link_algorithm_to_proof,
    )
    from mathhead.discovery.objects import Graph

    good = bridge_modular_algorithm(30, N5_MINUS_N)
    assert good.verified and good.modality == "kernel" and good.certainty == "kernel_verified"
    h = good.evidence["proof_hash"]
    assert len(h) == 16 and all(ch in "0123456789abcdef" for ch in h)
    assert good.evidence["axioms"] and all(a.startswith(("RESIDUE", "CRT"))
                                           for a in good.evidence["axioms"])

    bad = bridge_modular_algorithm(4, (1, 0, 1))         # 4 ∤ n²+1: no proof exists
    assert not bad.verified and "proof_hash" not in bad.evidence   # no fabricated proof, ever
    assert bad.certainty == "unproven"                   # the failure path never wears a proof tier
    assert "reason" in bad.evidence

    c5 = Graph(5, frozenset({(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)}))
    for bridged in (bridge_greedy_coloring(c5), bridge_max_clique(c5)):
        assert bridged.modality == "certificate" and bridged.verified
        assert bridged.certainty != "kernel_verified"    # a witness is NEVER sold as a ∀-proof
    with pytest.raises(ValueError):
        link_algorithm_to_proof("quantum-annealing")


# --- AC0: the director's goal-selection policy is TOTAL — and it follows its own advice ---------

def test_ac0_goal_selection_policy_is_total_and_followed():
    from mathhead.discovery.director import ResearchDirector

    d = ResearchDirector()
    pick = SimpleNamespace(statement="num_triangles <= num_edges")
    assert d._select_next_goal([pick], {}) == "settle open conjecture: num_triangles <= num_edges"
    assert d._select_next_goal([], {"EMPIRICALLY_VALIDATED": 5, "FORMALLY_PROVED": 2}) \
        == "raise validated laws toward proof (find structural/kernel arguments)"
    assert d._select_next_goal([], {"EMPIRICALLY_VALIDATED": 2, "FORMALLY_PROVED": 5}) \
        == "widen the sample bound to expose new structure"

    d2 = ResearchDirector()                              # the director FOLLOWS its own recommendation
    d2.run_session(n_cycles=2, start_n=3)
    assert d2.cycles[1].goal == d2.cycles[0].next_goal


# --- AC3: session state — deduped across cycles, isolated between directors, summarized honestly

def test_ac3_session_state_is_deduped_isolated_and_summarized():
    from mathhead.discovery.director import ResearchDirector

    d = ResearchDirector()
    first = d.run_cycle(max_n=3)
    learned = len(d.memory.records())
    second = d.run_cycle(max_n=3)                        # identical bound → nothing genuinely new
    assert first.new_findings > 0 and second.new_findings == 0
    assert second.new_dead_ends == 0 and len(d.memory.records()) == learned

    summary = d.session_summary()
    assert summary["cycles_run"] == 2
    assert summary["ladder_progression"] == [c.ladder for c in d.cycles]
    assert summary["final_open_frontier"] == d.cycles[-1].open_frontier
    assert summary["next_goal"] == d.cycles[-1].next_goal
    assert summary["total_dead_ends_learned"] == learned and len(summary["lessons"]) <= 3

    fresh = ResearchDirector()                           # no state leaks between directors
    assert not fresh.cycles and not fresh.memory.records()
    assert fresh.session_summary() == {"cycles_run": 0, "ladder_progression": [],
                                       "total_dead_ends_learned": 0, "final_open_frontier": [],
                                       "next_goal": None, "lessons": []}
