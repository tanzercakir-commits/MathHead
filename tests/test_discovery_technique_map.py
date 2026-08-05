"""Discovery Q3 + X2 — interval path and the technique map."""
import importlib

from mathhead.discovery.interval_check import cross_check_certifiers, double_star_slack_interval
from mathhead.discovery.technique_map import TECHNIQUES, classify_statement, suggest_techniques


def test_interval_route_certifies_the_witnesses():
    assert double_star_slack_interval(13, 13).verdict == "violation_certified"
    assert double_star_slack_interval(11, 11).verdict == "no_violation_certified"


def test_equality_case_is_honestly_undecided():
    # D(12,12): the slack IS exactly zero — interval arithmetic must refuse to decide strictness
    assert double_star_slack_interval(12, 12).verdict == "undecided"


def test_two_independent_certifiers_agree():
    r = cross_check_certifiers([(10, 10), (11, 11), (12, 12), (12, 13), (13, 13), (14, 14)])
    assert r["consistent"] and not r["disagree"]


def test_every_technique_pointer_names_real_code():
    # the map cannot drift from the codebase: import every module.attr it mentions
    for entries in TECHNIQUES.values():
        for _name, pointer, _tier in entries:
            mod_name, attr = pointer.rsplit(".", 1)
            mod = importlib.import_module(f"mathhead.discovery.{mod_name}")
            assert hasattr(mod, attr), pointer


def test_classifier_routes_representative_statements():
    assert classify_statement("6 divides n^3 - n") == "modular_divisibility"
    assert classify_statement("sum_(i=1..n) i = n(n+1)/2") == "sum_identity"
    assert classify_statement("lambda1 + mu >= sqrt(n-1) + 1") == "spectral_bound"
    assert classify_statement("no monochromatic triangle in K_6") == "finite_coloring_ramsey"
    assert classify_statement("every union-closed family ...") == "set_family"
    assert classify_statement("num_triangles <= num_edges for any graph") == "graph_inequality"
    assert classify_statement("the weather tomorrow") == "unknown"


def test_suggestions_carry_verdict_tiers():
    s = suggest_techniques("6 divides n^3 - n")
    assert s and s[0][2] == "kernel_verified"
