"""
Multivariable analysis (ROADMAP Phase 6) — gradient/Jacobian/Hessian, definite
integral, sum/product (Σ/Π), ordinary differential equation (ODE).

Best-case + worst-case (unsolvable ODE, malicious input) + honesty + determinism.
"""
from mathhead.compute import (
    definite_integral,
    gradient,
    hessian,
    jacobian,
    product,
    solve_ode,
    summation,
)


# ------------------------------- gradient --------------------------------- #
def test_gradient_basic():
    r = gradient("x**2*y + sin(y)", ["x", "y"])
    assert r.status == "ok"
    assert r.result == ["2*x*y", "x**2 + cos(y)"]


def test_gradient_unknown_function_rejected():
    assert gradient("foo(x)", ["x"]).status == "error"


# ------------------------------- jacobian --------------------------------- #
def test_jacobian_basic():
    r = jacobian(["x*y", "x + y"], ["x", "y"])
    assert r.status == "ok"
    assert r.result == [["y", "x"], ["1", "1"]]


# -------------------------------- hessian --------------------------------- #
def test_hessian_basic():
    r = hessian("x**2*y + sin(y)", ["x", "y"])
    assert r.status == "ok"
    assert r.result == [["2*y", "2*x"], ["2*x", "-sin(y)"]]


def test_hessian_symmetric():
    # Hessian is symmetric: H[0][1] == H[1][0]
    r = hessian("x**3 + x*y**2", ["x", "y"])
    assert r.result[0][1] == r.result[1][0]


# --------------------------- definite_integral ---------------------------- #
def test_definite_integral_finite():
    assert definite_integral("x**2", "x", "0", "3").result == "9"


def test_definite_integral_infinite():
    # ∫₀^∞ e^(-x) dx = 1
    assert definite_integral("exp(-x)", "x", "0", "oo").result == "1"


# ------------------------------ summation --------------------------------- #
def test_summation_closed_form():
    # Σ_{i=1}^{n} i = n(n+1)/2 = n²/2 + n/2  (closed form)
    assert summation("i", "i", "1", "n").result == "n**2/2 + n/2"


def test_summation_geometric():
    assert summation("2**i", "i", "0", "10").result == "2047"


# ------------------------------- product ---------------------------------- #
def test_product_factorial():
    # Π_{i=1}^{5} i = 120 = 5!
    assert product("i", "i", "1", "5").result == "120"


# ------------------------------- solve_ode -------------------------------- #
def test_ode_first_order():
    # y' = y  ->  y(x) = C1·e^x
    r = solve_ode("y' = y", "y", "x")
    assert r.status == "ok"
    assert r.result == "Eq(y(x), C1*exp(x))"


def test_ode_second_order_harmonic():
    # y'' + y = 0  ->  C1·sin(x) + C2·cos(x)
    r = solve_ode("y'' + y = 0", "y", "x")
    assert r.status == "ok"
    assert "sin(x)" in r.result and "cos(x)" in r.result


def test_ode_d_form():
    # D(y,1) notation is also accepted: y' = x·y -> C1·e^(x²/2)
    r = solve_ode("D(y,1) - x*y", "y", "x")
    assert r.status == "ok"
    assert "exp(x**2/2)" in r.result


def test_ode_unsolvable_honest_error():
    r = solve_ode("y'' = y**2*x", "y", "x")
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_ode_malicious_rejected():
    assert solve_ode("__import__('os')", "y", "x").status == "error"


# ------------------------------ determinism ------------------------------- #
def test_multivariable_determinism():
    for _ in range(5):
        assert gradient("x**2*y", ["x", "y"]).result == ["2*x*y", "x**2"]
        assert summation("i", "i", "1", "n").result == "n**2/2 + n/2"
        assert solve_ode("y' = y", "y", "x").result == "Eq(y(x), C1*exp(x))"
