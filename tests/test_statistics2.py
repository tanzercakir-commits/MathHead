"""
Inferential statistics (ROADMAP F2) — t_test / z_test / chi_square_test /
anova_oneway / confidence_interval / linear_regression.

p-values are numerical (mpmath, deterministic). Best-case (known results) +
sanity (identical samples → p≈1) + worst-case + determinism.
"""
from mathhead.compute import (
    anova_oneway,
    chi_square_test,
    confidence_interval,
    linear_regression,
    t_test,
    z_test,
)


# -------------------------------- t_test ---------------------------------- #
def test_t_one_sample_at_mean_is_insignificant():
    # sample mean == mu → t = 0, p = 1
    r = t_test([5.1, 4.9, 5.2, 4.8, 5.0], None, 5.0)
    assert r.status == "ok"
    assert r.result["t_statistic"] == 0.0
    assert r.result["p_value"] == 1.0


def test_t_two_sample_welch():
    r = t_test([1, 2, 3, 4, 5], [2, 3, 4, 5, 6])
    assert r.result["t_statistic"] == -1.0
    assert r.result["df"] == 8.0


def test_t_too_few_rejected():
    assert t_test([1]).status == "error"


# -------------------------------- z_test ---------------------------------- #
def test_z_test_at_mean():
    r = z_test([100, 102, 98, 101, 99], 100, 2)
    assert r.result["z_statistic"] == 0.0
    assert r.result["p_value"] == 1.0


def test_z_test_bad_sigma_rejected():
    assert z_test([1, 2, 3], 2, 0).status == "error"


# --------------------------- chi_square_test ------------------------------ #
def test_chi_square_goodness_of_fit():
    # observed [10,20,30,40] vs uniform 25 → χ² = 20, df = 3, p ≈ 0.0002
    r = chi_square_test([10, 20, 30, 40], [25, 25, 25, 25])
    assert r.result["chi_square"] == 20.0
    assert r.result["df"] == 3
    assert r.result["p_value"] < 0.001


def test_chi_square_zero_expected_rejected():
    assert chi_square_test([1, 2], [0, 2]).status == "error"


# ---------------------------- anova_oneway -------------------------------- #
def test_anova_significant():
    # clearly separated groups → large F, tiny p
    r = anova_oneway([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    assert r.result["f_statistic"] == 27.0
    assert r.result["df_between"] == 2
    assert r.result["df_within"] == 6
    assert r.result["p_value"] < 0.01


def test_anova_one_group_rejected():
    assert anova_oneway([[1, 2, 3]]).status == "error"


# ------------------------- confidence_interval ---------------------------- #
def test_confidence_interval_symmetric_about_mean():
    r = confidence_interval([2, 4, 6, 8, 10], 0.95)
    assert r.result["mean"] == 6.0
    # symmetric: mean − lower == upper − mean
    assert abs((r.result["mean"] - r.result["lower"]) - (r.result["upper"] - r.result["mean"])) < 1e-9


def test_confidence_interval_bad_level_rejected():
    assert confidence_interval([1, 2, 3], 1.5).status == "error"


# --------------------------- linear_regression ---------------------------- #
def test_regression_recovers_line():
    # y ≈ 2x → slope ≈ 2, r² ≈ 1
    r = linear_regression([1, 2, 3, 4, 5], [2.1, 4.0, 6.1, 7.9, 10.1])
    assert abs(r.result["slope"] - 2.0) < 0.05
    assert r.result["r_squared"] > 0.99


def test_regression_perfect_line():
    r = linear_regression([1, 2, 3, 4], [2, 4, 6, 8])
    assert r.result["slope"] == 2.0
    assert r.result["r_squared"] == 1.0


def test_regression_zero_variance_x_rejected():
    assert linear_regression([2, 2, 2], [1, 2, 3]).status == "error"


# ------------------------------ determinism ------------------------------- #
def test_statistics2_determinism():
    for _ in range(5):
        assert chi_square_test([10, 20, 30, 40], [25, 25, 25, 25]).result["chi_square"] == 20.0
        assert anova_oneway([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).result["f_statistic"] == 27.0
        assert linear_regression([1, 2, 3, 4], [2, 4, 6, 8]).result["slope"] == 2.0
