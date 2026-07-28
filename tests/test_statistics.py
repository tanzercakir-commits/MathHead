"""
Probability & statistics (ROADMAP Phase 7) — descriptive statistics (mean/variance/
std/median) + named distributions (E/Var/std, cdf/pmf).

Descriptive results exact/rational; distributions symbolic/exact. Best + worst + honesty.
"""
from mathhead.compute import (
    distribution,
    mean,
    median,
    standard_deviation,
    variance,
)

_DATA = ["2", "4", "4", "4", "5", "5", "7", "9"]


# ------------------------------ descriptive ---------------------------------- #
def test_mean():
    assert mean(_DATA).result == "5"


def test_variance_population():
    assert variance(_DATA).result == "4"


def test_variance_sample():
    # sample variance (n-1) — differs from population
    assert variance(_DATA, sample=True).result == "32/7"


def test_std_population():
    assert standard_deviation(_DATA).result == "2"


def test_median_even():
    # 8 observations -> average of the middle two (4+5)/2 = 9/2
    assert median(_DATA).result == "9/2"


def test_median_odd():
    assert median(["3", "1", "2"]).result == "2"


def test_stats_symbol_rejected():
    assert mean(["x", "2"]).status == "error"


def test_variance_sample_needs_two():
    assert variance(["5"], sample=True).status == "error"


# ------------------------------ distributions -------------------------------- #
def test_distribution_normal_symbolic():
    r = distribution("normal", ["mu", "sigma"])
    assert r.status == "ok"
    assert r.result["mean"] == "mu"
    assert r.result["variance"] == "sigma**2"


def test_distribution_binomial_moments():
    r = distribution("binomial", ["10", "1/2"])
    assert r.result["mean"] == "5"
    assert r.result["variance"] == "5/2"


def test_distribution_binomial_cdf_pmf():
    # P(X<=3) and pmf@3 (exact fraction)
    r = distribution("binomial", ["10", "1/2"], at="3")
    assert r.result["cdf_at"] == "11/64"
    assert r.result["density_at"] == "15/128"


def test_distribution_poisson():
    r = distribution("poisson", ["2"])
    assert r.result["mean"] == "2"
    assert r.result["variance"] == "2"


def test_distribution_unknown_rejected():
    assert distribution("weibull", ["1"]).status == "error"


def test_distribution_wrong_param_count_rejected():
    # normal requires two parameters
    assert distribution("normal", ["0"]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_statistics_determinism():
    for _ in range(5):
        assert mean(_DATA).result == "5"
        assert distribution("binomial", ["10", "1/2"]).result["mean"] == "5"
