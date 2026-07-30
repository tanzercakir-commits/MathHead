"""Discovery N6 — queryable object store indexed by invariant."""
from mathhead.discovery import generate_graphs
from mathhead.discovery.invariants import chromatic_number, num_edges, num_triangles
from mathhead.discovery.object_store import ObjectStore


def _store_up_to(n):
    s = ObjectStore()
    s.add_all(g for k in range(n + 1) for g in generate_graphs(k))
    return s


def test_add_is_idempotent_by_content_hash():
    s = ObjectStore()
    s.add_all(generate_graphs(4))
    before = len(s)
    s.add_all(generate_graphs(4))                       # add the same graphs again
    assert len(s) == before


def test_query_returns_only_matching_objects():
    s = _store_up_to(5)
    q = s.query(chromatic_number=3, num_triangles=0)    # triangle-free but 3-chromatic (odd cycle)
    assert q                                            # C5 is the witness
    assert all(chromatic_number(g) == 3 and num_triangles(g) == 0 for g in q)


def test_by_invariant_matches_a_direct_scan():
    s = _store_up_to(5)
    direct = [g for g in s.all() if num_edges(g) == 6]
    assert len(s.by_invariant("num_edges", 6)) == len(direct)


def test_invariant_values_are_the_distinct_seen_values():
    s = _store_up_to(5)
    assert s.invariant_values("chromatic_number") == sorted(
        {chromatic_number(g) for g in s.all()})


def test_empty_query_returns_all_and_results_are_deterministic():
    s = _store_up_to(4)
    assert len(s.query()) == len(s)
    assert [g.n for g in s.all()] == [g.n for g in s.all()]   # reproducible order
