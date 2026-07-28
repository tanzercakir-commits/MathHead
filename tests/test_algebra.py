"""
Abstract algebra — permutation groups (ROADMAP E1) — permutation_order /
permutation_parity / permutation_compose / group_order / generated_group.

Permutations in ARRAY form (0-indexed images): [1,2,0] is the cycle (0 1 2).

Best-case (known groups) + worst-case (invalid permutation, unknown group) +
honesty + determinism.
"""
from mathhead.compute import (
    generated_group,
    group_order,
    permutation_compose,
    permutation_order,
    permutation_parity,
)


# ---------------------------- permutation_order --------------------------- #
def test_order_of_three_cycle():
    r = permutation_order([1, 2, 0])
    assert r.status == "ok"
    assert r.result == 3


def test_order_of_identity():
    assert permutation_order([0, 1, 2]).result == 1


def test_invalid_permutation_rejected():
    r = permutation_order([1, 1, 0])          # not a bijection
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# --------------------------- permutation_parity --------------------------- #
def test_parity_three_cycle_is_even():
    assert permutation_parity([1, 2, 0]).result == "even"


def test_parity_transposition_is_odd():
    assert permutation_parity([1, 0, 2]).result == "odd"


# -------------------------- permutation_compose --------------------------- #
def test_compose_two_permutations():
    r = permutation_compose([[1, 2, 0], [1, 0, 2]])
    assert r.status == "ok"
    assert r.result["array_form"] == [0, 2, 1]
    assert r.result["order"] == 2


def test_compose_size_mismatch_rejected():
    assert permutation_compose([[1, 0], [1, 2, 0]]).status == "error"


# ------------------------------ group_order ------------------------------- #
def test_symmetric_group_order():
    r = group_order("symmetric", 3)
    assert r.status == "ok"
    assert r.result == {"order": 6, "abelian": False}


def test_alternating_group_order():
    assert group_order("alternating", 4).result["order"] == 12


def test_cyclic_group_is_abelian():
    r = group_order("cyclic", 6)
    assert r.result == {"order": 6, "abelian": True}


def test_dihedral_group_order():
    # |Dₙ| = 2n
    assert group_order("dihedral", 5).result["order"] == 10


def test_unknown_group_rejected():
    assert group_order("quaternion", 8).status == "error"


def test_negative_degree_rejected():
    assert group_order("symmetric", 0).status == "error"


# ---------------------------- generated_group ----------------------------- #
def test_generated_symmetric():
    # a 3-cycle and a transposition generate all of S₃
    r = generated_group([[1, 2, 0], [1, 0, 2]])
    assert r.status == "ok"
    assert r.result["order"] == 6
    assert r.result["abelian"] is False


def test_generated_cyclic_from_single_generator():
    # a single 4-cycle generates C₄ (order 4, abelian)
    r = generated_group([[1, 2, 3, 0]])
    assert r.result == {"order": 4, "abelian": True, "degree": 4}


def test_generated_empty_rejected():
    assert generated_group([]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_algebra_determinism():
    for _ in range(5):
        assert permutation_order([1, 2, 0]).result == 3
        assert group_order("symmetric", 4).result["order"] == 24
        assert generated_group([[1, 2, 0], [1, 0, 2]]).result["order"] == 6
