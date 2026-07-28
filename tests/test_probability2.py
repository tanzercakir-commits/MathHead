"""
Probability II (ROADMAP F1) — bayes_theorem / covariance / correlation /
markov_stationary / markov_step / joint_marginal.

Exact (rational) arithmetic. Best-case (known values) + honesty (zero evidence /
zero variance / non-stochastic) + determinism.
"""
from mathhead.compute import (
    bayes_theorem,
    correlation,
    covariance,
    joint_marginal,
    markov_stationary,
    markov_step,
)


# ---------------------------- bayes_theorem ------------------------------- #
def test_bayes_base_rate():
    # prior 1%, sensitivity 90%, false-alarm 5% → posterior 2/13 (~15%)
    r = bayes_theorem("1/100", "9/10", "1/20")
    assert r.status == "ok"
    assert r.result["posterior"] == "2/13"
    assert r.result["evidence"] == "117/2000"


def test_bayes_certain_evidence():
    # likelihood 1, false-alarm 0 → posterior 1
    assert bayes_theorem("1/2", "1", "0").result["posterior"] == "1"


def test_bayes_out_of_range_rejected():
    assert bayes_theorem("2", "0.5", "0.1").status == "error"


def test_bayes_zero_evidence_is_honest():
    # likelihood 0 and false-alarm 0 → evidence 0 → undefined
    r = bayes_theorem("1/2", "0", "0")
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


# ------------------------- covariance / correlation ----------------------- #
def test_covariance_population():
    assert covariance([1, 2, 3, 4], [2, 4, 5, 4]).result == "7/8"


def test_covariance_sample():
    assert covariance([1, 2, 3, 4], [2, 4, 5, 4], sample=True).result == "7/6"


def test_correlation_perfect_positive():
    assert correlation([1, 2, 3, 4], [2, 4, 6, 8]).result == "1"


def test_correlation_perfect_negative():
    assert correlation([1, 2, 3], [3, 2, 1]).result == "-1"


def test_correlation_zero_variance_rejected():
    r = correlation([2, 2, 2], [1, 2, 3])
    assert r.status == "error"
    assert r.reason_code == "COMPUTE_FAILED"


def test_covariance_length_mismatch_rejected():
    assert covariance([1, 2], [1]).status == "error"


# ------------------------- markov_stationary/step ------------------------- #
def test_markov_stationary_distribution():
    r = markov_stationary([["1/2", "1/2"], ["1/4", "3/4"]])
    assert r.status == "ok"
    assert r.result == ["1/3", "2/3"]


def test_markov_stationary_non_stochastic_rejected():
    # rows don't sum to 1
    assert markov_stationary([["1", "1"], ["0", "1"]]).status == "error"


def test_markov_step_evolution():
    r = markov_step([["1/2", "1/2"], ["1/4", "3/4"]], [1, 0], 2)
    assert r.result == ["3/8", "5/8"]


def test_markov_step_zero_is_initial():
    assert markov_step([["1/2", "1/2"], ["1/4", "3/4"]], [1, 0], 0) .result == ["1", "0"]


# ---------------------------- joint_marginal ------------------------------ #
def test_joint_marginal_rows():
    # row sums (P over columns)
    assert joint_marginal([["1/8", "1/8"], ["1/4", "1/2"]], "row").result == ["1/4", "3/4"]


def test_joint_marginal_cols():
    assert joint_marginal([["1/8", "1/8"], ["1/4", "1/2"]], "col").result == ["3/8", "5/8"]


# ------------------------------ determinism ------------------------------- #
def test_probability2_determinism():
    for _ in range(5):
        assert bayes_theorem("1/100", "9/10", "1/20").result["posterior"] == "2/13"
        assert markov_stationary([["1/2", "1/2"], ["1/4", "3/4"]]).result == ["1/3", "2/3"]
        assert covariance([1, 2, 3, 4], [2, 4, 5, 4]).result == "7/8"
