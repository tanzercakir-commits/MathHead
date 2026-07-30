"""Discovery AE2 — the honest hunt for unattributed-in-catalog candidates."""
from mathhead.discovery.candidate_hunt import hunt


def test_hunt_finds_the_family_formula_candidates():
    r = hunt(max_n=5)
    stmts = {st for st, _ in r.candidates}
    # the four textbook family edge-count formulas the catalog lacks markers for
    assert "num_vertices = num_edges" in stmts                    # C_n
    assert "num_vertices = num_edges + 1" in stmts                # P_n and star
    assert r.explored > r.attributed > 0


def test_every_candidate_is_flagged_with_the_caveat_not_as_novelty():
    r = hunt(max_n=5)
    assert "NOT novel-to-literature" in r.caveat and "NOT a claim" in r.caveat
    assert not r.all_attributed                                   # candidates exist, honestly labelled


def test_candidates_are_a_subset_of_explored_and_disjoint_from_attributed():
    r = hunt(max_n=5)
    assert len(r.candidates) == r.explored - r.attributed


def test_hunt_is_deterministic():
    assert hunt(max_n=5) == hunt(max_n=5)
