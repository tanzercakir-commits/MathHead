"""
Hardening — probability, statistics & optimization (ROADMAP F4 [S]) —
property-based invariants + determinism + fuzz across Track F.

The properties ARE the defining facts: a Bayes posterior lives in [0,1], a Markov
stationary distribution is a fixed point of P, Cov(X,X)=Var(X), a correlation is
±1 for perfectly linear data, a Lagrange point satisfies its constraint, and a
sum of squares is convex.
"""
import hypothesis.strategies as st
import sympy
from hypothesis import assume, given, settings

from mathhead.compute import (
    bayes_theorem,
    chi_square_test,
    check_convexity,
    correlation,
    covariance,
    lagrange_multipliers,
    markov_stationary,
    markov_step,
    variance,
)

_CFG = settings(max_examples=40, deadline=None)
# a rational string in [0, 1]
_unit = st.integers(1, 9).flatmap(lambda q: st.integers(0, q).map(lambda p: f"{p}/{q}"))
# a rational string strictly in (0, 1)
_open = st.integers(2, 9).flatmap(lambda q: st.integers(1, q - 1).map(lambda p: f"{p}/{q}"))


# ------------------------------ Bayes ------------------------------------- #
@_CFG
@given(_unit, _unit, _unit)
def test_bayes_posterior_in_unit_interval(prior, likelihood, false_alarm):
    r = bayes_theorem(prior, likelihood, false_alarm)
    if r.status == "ok":
        v = sympy.Rational(r.result["posterior"])
        assert 0 <= v <= 1


@_CFG
@given(_unit, _unit)
def test_bayes_uninformative_evidence_keeps_prior(prior, x):
    # likelihood == false_alarm ⟹ E is independent of H ⟹ posterior == prior
    r = bayes_theorem(prior, x, x)
    if r.status == "ok":
        assert sympy.Rational(r.result["posterior"]) == sympy.Rational(prior)


# ------------------------------ Markov ------------------------------------ #
@_CFG
@given(_open, _open)
def test_markov_stationary_is_a_fixed_point(a, b):
    # π of [[a,1-a],[b,1-b]] must satisfy π·P == π (one more step changes nothing)
    P = [[a, f"1 - {a}"], [b, f"1 - {b}"]]
    r = markov_stationary(P)
    assume(r.status == "ok")
    pi = r.result
    stepped = markov_step(P, pi, 1)
    assert [sympy.Rational(x) for x in stepped.result] == [sympy.Rational(x) for x in pi]
    assert sum(sympy.Rational(x) for x in pi) == 1


# ---------------------- covariance / correlation -------------------------- #
@_CFG
@given(st.lists(st.integers(-9, 9), min_size=2, max_size=6))
def test_cov_of_x_with_itself_is_variance(xs):
    data = [str(x) for x in xs]
    c = covariance(data, data).result
    v = variance(data).result
    assert sympy.Rational(c) == sympy.Rational(v)


@_CFG
@given(st.lists(st.integers(-9, 9), min_size=3, max_size=6),
       st.integers(1, 5), st.integers(-5, 5))
def test_correlation_is_one_for_positive_linear(xs, a, b):
    assume(len(set(xs)) > 1)                       # x must not be constant
    ys = [str(a * x + b) for x in xs]
    assert correlation([str(x) for x in xs], ys).result == "1"


# -------------------------- statistics bounds ----------------------------- #
@_CFG
@given(st.lists(st.integers(1, 50), min_size=2, max_size=5))
def test_chi_square_pvalue_in_unit_interval(obs):
    avg = sum(obs) / len(obs)
    exp = [str(avg)] * len(obs)
    r = chi_square_test([str(o) for o in obs], exp)
    if r.status == "ok":
        assert 0 <= r.result["p_value"] <= 1


# ----------------------------- optimization ------------------------------- #
@_CFG
@given(st.integers(2, 30))
def test_lagrange_point_satisfies_the_constraint(c):
    r = lagrange_multipliers("x*y", [f"x + y - {c}"], ["x", "y"])
    assume(r.status == "ok")
    for sol in r.result:
        x = sympy.Rational(sol["point"]["x"])
        y = sympy.Rational(sol["point"]["y"])
        assert x + y == c


@_CFG
@given(st.integers(1, 5), st.integers(1, 5))
def test_positive_weighted_sum_of_squares_is_convex(a, b):
    assert check_convexity(f"{a}*x**2 + {b}*y**2", ["x", "y"]).result["verdict"] == "convex"


# ------------------------------ determinism ------------------------------- #
def test_probability_hardening_determinism():
    for _ in range(5):
        assert bayes_theorem("1/100", "9/10", "1/20").result["posterior"] == "2/13"
        assert markov_stationary([["1/2", "1/2"], ["1/4", "3/4"]]).result == ["1/3", "2/3"]
        assert check_convexity("x**2 + y**2", ["x", "y"]).result["verdict"] == "convex"
