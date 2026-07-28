"""
Combinatorics & discrete (ROADMAP Phase 4) — permutation/combination, factorial,
integer partitions, closed-form solution of linear recurrence.

Best-case + worst-case (negative, nonlinear, malicious) + honesty
(error if no closed form) + determinism.
"""
import sympy

from mathhead.compute import (
    combinations,
    factorial,
    partition_count,
    permutations,
    solve_recurrence,
)


# ----------------------------- permutations ------------------------------- #
def test_permutations_basic():
    assert permutations(10, 3).result == 720


def test_permutations_k_gt_n_is_zero():
    # ordered selection of 7 from 5 objects impossible -> 0
    assert permutations(5, 7).result == 0


def test_permutations_negative_rejected():
    assert permutations(-1, 2).status == "error"


# ----------------------------- combinations ------------------------------- #
def test_combinations_basic():
    assert combinations(10, 3).result == 120


def test_combinations_symmetry():
    # C(n,k) = C(n,n-k)
    assert combinations(10, 3).result == combinations(10, 7).result


def test_combinations_k_gt_n_is_zero():
    assert combinations(5, 7).result == 0


# ------------------------------- factorial -------------------------------- #
def test_factorial_basic():
    assert factorial(6).result == 720


def test_factorial_zero():
    assert factorial(0).result == 1


def test_factorial_negative_rejected():
    assert factorial(-3).status == "error"


# ---------------------------- partition_count ----------------------------- #
def test_partition_10():
    assert partition_count(10).result == 42


def test_partition_zero():
    # p(0) = 1 (empty partition)
    assert partition_count(0).result == 1


# ---------------------------- solve_recurrence ---------------------------- #
def test_recurrence_fibonacci_closed_form():
    # y(n)=y(n-1)+y(n-2), y0=0, y1=1 -> closed form; verify Fib(10)=55
    r = solve_recurrence("y(n) = y(n-1) + y(n-2)", "y", "n", {"0": "0", "1": "1"})
    assert r.status == "ok"
    n = sympy.symbols("n")
    val = sympy.simplify(sympy.sympify(r.result).subs(n, 10))
    assert val == 55


def test_recurrence_geometric():
    # y(n)=2·y(n-1), y0=1 -> 2**n
    r = solve_recurrence("y(n) = 2*y(n-1)", "y", "n", {"0": "1"})
    assert r.status == "ok"
    assert r.result == "2**n"


def test_recurrence_equality_form_accepted():
    # '==' is also accepted
    r = solve_recurrence("y(n) == 3*y(n-1)", "y", "n", {"0": "1"})
    assert r.result == "3**n"


def test_recurrence_nonlinear_honest_error():
    # Nonlinear -> no closed form, no fabrication
    r = solve_recurrence("y(n) = y(n-1)**2", "y", "n", {"0": "2"})
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_recurrence_malicious_rejected():
    assert solve_recurrence("__import__('os')", "y", "n", {}).status == "error"


def test_recurrence_unknown_name_rejected():
    # Undefined function name (z) -> rejected
    assert solve_recurrence("y(n) = z(n-1)", "y", "n", {"0": "1"}).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_combinatorics_determinism():
    for _ in range(5):
        assert combinations(10, 3).result == 120
        assert partition_count(10).result == 42
        assert solve_recurrence("y(n) = 2*y(n-1)", "y", "n", {"0": "1"}).result == "2**n"
