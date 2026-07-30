"""Discovery v2A5 — the rich invariant library, anchored on classical exact values."""
from mathhead.discovery.families import complete, complete_bipartite, cycle, path, star
from mathhead.discovery.objects import Graph
from mathhead.discovery.rich_invariants import (
    RICH_INVARIANTS,
    diameter,
    domination_number,
    girth,
    independence_number,
    matching_number,
    petersen,
    radius,
)


def test_petersen_anchor_all_six_invariants():
    p = petersen()
    assert independence_number(p) == 4 and domination_number(p) == 3
    assert matching_number(p) == 5 and girth(p) == 5
    assert diameter(p) == 2 and radius(p) == 2            # the textbook values, all exact


def test_cycle_family_closed_forms():
    for n in range(3, 8):
        c = cycle(n)
        assert independence_number(c) == n // 2           # α(C_n) = ⌊n/2⌋
        assert matching_number(c) == n // 2               # ν(C_n) = ⌊n/2⌋
        assert girth(c) == n and diameter(c) == n // 2


def test_complete_and_star_closed_forms():
    for n in range(2, 7):
        assert independence_number(complete(n)) == 1 and domination_number(complete(n)) == 1
        assert girth(complete(n)) == (3 if n >= 3 else 0)
    for n in range(3, 7):
        s = star(n)
        assert domination_number(s) == 1                  # the hub dominates everything
        assert independence_number(s) == n - 1 and matching_number(s) == 1


def test_konig_theorem_on_the_bipartite_family():
    # König: on bipartite graphs, ν = n − α (max matching = min vertex cover) — a LAW as cross-check
    samples = [complete_bipartite(a, b) for a in range(1, 4) for b in range(a, 5)]
    samples += [path(n) for n in range(2, 7)] + [cycle(n) for n in (4, 6)]
    for g in samples:
        assert matching_number(g) == g.n - independence_number(g)


def test_acyclic_and_disconnected_conventions_are_explicit():
    p5 = path(5)
    assert girth(p5) == 0                                 # acyclic → 0, documented
    two_parts = Graph.from_edges(4, [(0, 1), (2, 3)])
    assert diameter(two_parts) == -1 and radius(two_parts) == -1   # disconnected sentinel


def test_registry_is_complete_and_deterministic():
    assert set(RICH_INVARIANTS) == {"independence_number", "domination_number", "matching_number",
                                    "girth", "diameter", "radius"}
    p = petersen()
    assert [f(p) for f in RICH_INVARIANTS.values()] == [f(p) for f in RICH_INVARIANTS.values()]
