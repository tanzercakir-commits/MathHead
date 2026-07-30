"""Discovery N4 — parametric object families; their invariants cross-check the invariant code."""
from math import comb

import pytest

from mathhead.discovery.families import (
    complete,
    complete_bipartite,
    cycle,
    empty,
    path,
    star,
    stratified_sample,
    wheel,
)
from mathhead.discovery.invariants import (
    chromatic_number,
    clique_number,
    is_hamiltonian,
    max_degree,
    num_edges,
)


def test_complete_graph_closed_forms():
    for n in range(1, 8):
        k = complete(n)
        assert num_edges(k) == comb(n, 2)
        assert chromatic_number(k) == n and clique_number(k) == n
        assert max_degree(k) == (n - 1 if n else 0)


def test_cycle_closed_forms():
    for n in range(3, 9):
        c = cycle(n)
        assert num_edges(c) == n
        assert chromatic_number(c) == (2 if n % 2 == 0 else 3)   # even bipartite, odd needs 3
        assert is_hamiltonian(c) is True                         # a cycle is Hamiltonian


def test_path_and_star_and_empty():
    for n in range(2, 8):
        assert num_edges(path(n)) == n - 1 and chromatic_number(path(n)) == 2
        assert num_edges(star(n)) == n - 1 and chromatic_number(star(n)) == 2
    assert num_edges(empty(5)) == 0 and chromatic_number(empty(5)) == 1


def test_wheel_and_complete_bipartite():
    w = wheel(6)                                                 # hub + C5
    assert num_edges(w) == 2 * 5 and chromatic_number(w) == 4     # odd rim ⇒ χ=4
    kb = complete_bipartite(3, 4)
    assert num_edges(kb) == 12 and chromatic_number(kb) == 2 and clique_number(kb) == 2


def test_family_guards():
    with pytest.raises(ValueError):
        cycle(2)
    with pytest.raises(ValueError):
        wheel(3)


def test_stratified_sample_is_diverse_and_deterministic():
    a = [g.n for g in stratified_sample(6)]
    b = [g.n for g in stratified_sample(6)]
    assert a == b and len(a) > 20                                # a broad, structured sample
