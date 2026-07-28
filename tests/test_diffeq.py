"""
Differential equations II (ROADMAP D3) — solve_ode_system / solve_ode_ivp /
classify_ode / solve_pde.

Best-case (known solutions) + worst-case (bad conditions, unsupported PDE) +
honesty (COMPUTE_FAILED, no fabrication) + determinism.
"""
from mathhead.compute import (
    classify_ode,
    solve_ode_ivp,
    solve_ode_system,
    solve_pde,
)


# --------------------------- solve_ode_system ----------------------------- #
def test_system_harmonic_pair():
    # f' = g, g' = -f  ->  sin/cos combinations
    r = solve_ode_system(["f' = g", "g' = -f"], ["f", "g"])
    assert r.status == "ok"
    assert any("sin(x)" in s and "cos(x)" in s for s in r.result)


def test_system_empty_rejected():
    r = solve_ode_system([], ["f"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


# ----------------------------- solve_ode_ivp ------------------------------ #
def test_ivp_recovers_sine():
    # y'' + y = 0, y(0)=0, y'(0)=1  ->  sin(x)  (the constants are pinned down)
    r = solve_ode_ivp("y'' + y = 0", ["y(0)=0", "y'(0)=1"])
    assert r.status == "ok"
    assert r.result == "Eq(y(x), sin(x))"


def test_bvp_with_pi_boundary():
    # boundary value: y(0)=0, y(pi/2)=1  ->  sin(x)
    r = solve_ode_ivp("y'' + y = 0", ["y(0)=0", "y(pi/2)=1"])
    assert r.status == "ok"
    assert r.result == "Eq(y(x), sin(x))"


def test_ivp_first_order():
    # y' = y, y(0)=1  ->  exp(x)
    r = solve_ode_ivp("y' = y", ["y(0)=1"])
    assert r.status == "ok"
    assert "exp(x)" in r.result


def test_ivp_bad_condition_rejected():
    r = solve_ode_ivp("y' = y", ["nonsense"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_ivp_no_conditions_rejected():
    assert solve_ode_ivp("y' = y", []).status == "error"


# ------------------------------ classify_ode ------------------------------ #
def test_classify_linear_first_order():
    r = classify_ode("y' + y")
    assert r.status == "ok"
    assert "1st_linear" in r.result
    assert "separable" in r.result


def test_classify_malicious_rejected():
    assert classify_ode("__import__('os')").status == "error"


# -------------------------------- solve_pde ------------------------------- #
def test_pde_first_order_linear():
    # u_x + u_y = 0  ->  u(x,y) = F(x - y)
    r = solve_pde("D(u,x) + D(u,y) = 0", "u", ["x", "y"])
    assert r.status == "ok"
    assert "F(x - y)" in r.result


def test_pde_unsupported_is_honest():
    # heat equation u_t = u_xx is beyond pdsolve -> honest COMPUTE_FAILED
    r = solve_pde("D(u,t) - D(u,x,x) = 0", "u", ["t", "x"])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_pde_needs_two_variables():
    assert solve_pde("D(u,x) = 0", "u", ["x"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_diffeq_determinism():
    for _ in range(5):
        assert solve_ode_ivp("y'' + y = 0", ["y(0)=0", "y'(0)=1"]).result == "Eq(y(x), sin(x))"
        assert "1st_linear" in classify_ode("y' + y").result
