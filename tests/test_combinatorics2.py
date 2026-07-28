"""
Combinatorics II (ROADMAP E5) — catalan_number / bell_number / stirling_number /
derangements / generating_function_coefficient / necklace_count.

Best-case (known values) + a cross-check (GF ↔ binomial) + worst-case + determinism.
"""
from mathhead.compute import (
    bell_number,
    catalan_number,
    derangements,
    generating_function_coefficient,
    necklace_count,
    stirling_number,
)


# ---------------------------- catalan / bell ------------------------------ #
def test_catalan_number():
    assert catalan_number(5).result == 42


def test_bell_number():
    assert bell_number(5).result == 52


def test_catalan_negative_rejected():
    assert catalan_number(-1).status == "error"


# ----------------------------- stirling ----------------------------------- #
def test_stirling_second_kind():
    assert stirling_number(5, 2).result == 15


def test_stirling_first_kind():
    assert stirling_number(5, 2, "first").result == 50


def test_stirling_bad_kind_rejected():
    assert stirling_number(5, 2, "third").status == "error"


# --------------------------- derangements --------------------------------- #
def test_derangements():
    # !4 = 9
    assert derangements(4).result == 9


def test_derangements_zero():
    # !0 = 1 (the empty permutation)
    assert derangements(0).result == 1


# ------------------ generating_function_coefficient ----------------------- #
def test_gf_fibonacci_coefficient():
    # [x^6] of 1/(1-x-x^2) = F_7 = 13
    r = generating_function_coefficient("1/(1 - x - x**2)", "x", 6)
    assert r.status == "ok"
    assert r.result == "13"


def test_gf_matches_binomial():
    # [x^3] of (1+x)^5 = C(5,3) = 10
    assert generating_function_coefficient("(1 + x)**5", "x", 3).result == "10"


def test_gf_malicious_rejected():
    assert generating_function_coefficient("__import__('os')", "x", 2).status == "error"


# ---------------------------- necklace_count ------------------------------ #
def test_necklace_count_small():
    # 4 beads, 2 colors, under rotation → 6
    assert necklace_count(4, 2).result == 6


def test_necklace_count_larger():
    assert necklace_count(6, 3).result == 130


def test_necklace_count_zero_rejected():
    assert necklace_count(0, 2).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_combinatorics2_determinism():
    for _ in range(5):
        assert catalan_number(10).result == 16796
        assert derangements(4).result == 9
        assert generating_function_coefficient("1/(1 - x - x**2)", "x", 6).result == "13"
