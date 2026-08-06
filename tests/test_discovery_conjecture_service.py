"""Discovery v2C0 — the Graffiti-style conjecture service (sharpness-ranked feed)."""
from mathhead.discovery.conjecture_service import run_service, scale_sweep, service_invariants
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


# ---- v4F5 scale path (mechanism pins only — the real n=8 run lives in SCALE-RUNS.md) ----

def test_small_n_survivor_count_is_pinned():
    # the v2C0 baseline the scale sweep measures against: 330 candidates, 74 survivors at n <= 6
    feed = run_service(6)
    assert feed.tested == 330 and len(feed.survivors) == 74 and feed.graphs == 142


def test_scale_sweep_is_consistent_with_the_survivor_filter():
    # mechanism invariant at small n (fast): alive ⊆ survivors(n_max), refuted ∩ survivors(n_max) = ∅
    sweep = scale_sweep(n_small=4, n_max=5)
    big = {s.statement for s in run_service(5).survivors}
    assert sweep.small_survivor_count == len(run_service(4).survivors)
    assert sweep.scale_graphs == 21                          # connected graphs on 5 vertices
    assert set(sweep.alive) <= big
    assert all(r.statement not in big for r in sweep.refuted)
    assert len(sweep.alive) + len(sweep.refuted) == sweep.small_survivor_count


def test_scale_sweep_witnesses_really_violate():
    invs = service_invariants()
    sweep = scale_sweep(n_small=4, n_max=5)
    assert sweep.refuted                                     # growing the haystack kills something
    for r in sweep.refuted:
        n, edges = r.counterexample
        g = Graph(n, frozenset(edges))
        lhs_name, rest = r.statement.split(" <= ")
        assert invs[lhs_name](g) == r.lhs_value              # recomputed, not trusted
        if rest.startswith("2*"):
            assert r.lhs_value > 2 * invs[rest[2:]](g)
        elif " + " in rest:
            rhs_name, c = rest.split(" + ")
            assert r.lhs_value > invs[rhs_name](g) + int(c)
        else:
            assert r.lhs_value > invs[rest](g)


def test_scale_sweep_is_deterministic_and_only_demotes():
    a, b = scale_sweep(4, 5), scale_sweep(4, 5)
    assert a.alive == b.alive
    assert [(r.statement, r.counterexample) for r in a.refuted] == \
           [(r.statement, r.counterexample) for r in b.refuted]
    assert "cannot upgrade a tier" in a.note
