"""
Numerical linear algebra & ODE (ROADMAP G2) — numerical_eigenvalues /
condition_number / runge_kutta.

Deterministic (fixed mpmath precision). Best-case (known values) + honesty
(singular → infinite) + determinism.
"""
from mathhead.compute import (
    condition_number,
    numerical_eigenvalues,
    runge_kutta,
)


# ------------------------- numerical_eigenvalues -------------------------- #
def test_eigenvalues_symmetric():
    # [[2,1],[1,2]] → eigenvalues 1 and 3
    r = numerical_eigenvalues([["2", "1"], ["1", "2"]])
    assert r.status == "ok"
    assert sorted(float(v) for v in r.result) == [1.0, 3.0]


def test_eigenvalues_complex():
    # rotation [[0,-1],[1,0]] → ±i
    r = numerical_eigenvalues([["0", "-1"], ["1", "0"]])
    assert any("I" in v for v in r.result)


def test_eigenvalues_non_square_rejected():
    assert numerical_eigenvalues([["1", "2", "3"]]).status == "error"


# ---------------------------- condition_number ---------------------------- #
def test_condition_number_diagonal():
    # κ(diag(2,1)) = 2/1 = 2
    assert condition_number([["2", "0"], ["0", "1"]]).result == 2.0


def test_condition_number_identity_is_one():
    assert condition_number([["1", "0"], ["0", "1"]]).result == 1.0


def test_condition_number_singular_is_infinite():
    r = condition_number([["1", "2"], ["2", "4"]])
    assert r.status == "ok"
    assert r.result is None                # infinite (honest)


# ------------------------------ runge_kutta ------------------------------- #
def test_rk4_exponential_growth():
    # y' = y, y(0)=1, to x=1 → e ≈ 2.71828
    r = runge_kutta("y", 0, 1, 1)
    assert r.status == "ok"
    assert abs(r.result["y_end"] - 2.718281828459045) < 1e-6


def test_rk4_quadratic():
    # y' = x, y(0)=0, to x=2 → y = x²/2 = 2
    r = runge_kutta("x", 0, 0, 2)
    assert abs(r.result["y_end"] - 2.0) < 1e-9


def test_rk4_linear_ode():
    # y' = 2x + 1, y(0)=0 → y = x² + x; at x=3 → 12
    r = runge_kutta("2*x + 1", 0, 0, 3)
    assert abs(r.result["y_end"] - 12.0) < 1e-6


def test_rk4_trajectory_endpoints():
    r = runge_kutta("y", 0, 1, 1)
    traj = r.result["trajectory"]
    assert traj[0] == [0.0, 1.0]
    assert traj[-1][0] == 1.0


def test_rk4_extra_symbol_rejected():
    assert runge_kutta("x + z", 0, 0, 1).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_numerical_linalg_determinism():
    for _ in range(5):
        assert sorted(float(v) for v in numerical_eigenvalues([["2", "1"], ["1", "2"]]).result) == [1.0, 3.0]
        assert condition_number([["2", "0"], ["0", "1"]]).result == 2.0
        assert runge_kutta("y", 0, 1, 1).result["y_end"] == runge_kutta("y", 0, 1, 1).result["y_end"]
