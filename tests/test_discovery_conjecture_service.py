"""Discovery v2C0 — the Graffiti-style conjecture service (sharpness-ranked feed)."""
from mathhead.discovery.conjecture_service import run_service, service_invariants
from mathhead.discovery.objects import Graph


def _feed():
    return run_service(5)


def test_classic_theorems_survive_as_sharp_bounds():
    stmts = {s.statement for s in _feed().survivors}
    for want in ("clique_number <= chromatic_number", "radius <= diameter",
                 "diameter <= 2*radius", "domination_number <= independence_number"):
        assert want in stmts


def test_false_inequalities_are_killed():
    stmts = {s.statement for s in _feed().survivors}
    assert "chromatic_number <= min_degree" not in stmts          # K_n kills it
    assert "diameter <= min_degree" not in stmts                  # paths kill it


def test_sharp_example_really_attains_equality():
    feed = _feed()
    invs = service_invariants()
    for s in feed.survivors[:8]:
        if not s.sharp_example:
            continue
        n, edges = s.sharp_example
        g = Graph(n, frozenset(edges))
        va, vb = invs[s.lhs](g), invs[s.rhs](g)
        assert va == (2 * vb if s.form == "A<=2B" else vb + s.const)   # equality, exactly


def test_dominated_offset_forms_are_dropped():
    feed = _feed()
    tight = {(s.lhs, s.rhs) for s in feed.survivors if s.form == "A<=B"}
    assert all(not (s.form == "A<=B+c" and (s.lhs, s.rhs) in tight) for s in feed.survivors)


def test_feed_is_honest_and_deterministic():
    a, b = _feed(), _feed()
    assert [s.statement for s in a.survivors] == [s.statement for s in b.survivors]
    assert all(s.status == "empirical" and "not a novelty claim" in s.caveat for s in a.survivors)
    assert a.survivors[0].sharp_count >= a.survivors[-1].sharp_count   # sharpest-first
