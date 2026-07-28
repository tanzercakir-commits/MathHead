"""
Model enumeration (all-SAT): all / multiple distinct models of a formula.
"""
from mathhead.core.logic import enumerate_models


def test_all_boolean_models_exhaustive():
    r = enumerate_models(["p or q"])
    assert r.status == "sat"
    assert r.count == 3          # (T,F), (F,T), (T,T)
    assert r.exhaustive is True


def test_bounded_integer_models():
    r = enumerate_models(["x > 0", "x < 4"])
    assert r.exhaustive is True
    assert sorted(m["x"] for m in r.models) == [1, 2, 3]


def test_xor_has_exactly_two_models():
    r = enumerate_models(["xor(a, b)"])
    assert r.count == 2
    assert r.exhaustive is True


def test_unbounded_hits_limit_not_exhaustive():
    r = enumerate_models(["x > 0"], limit=5)
    assert r.count == 5
    assert r.exhaustive is False   # infinite domain; more exist


def test_contradiction_has_no_models():
    r = enumerate_models(["p", "not(p)"])
    assert r.status == "unsat"
    assert r.count == 0
    assert r.exhaustive is True


def test_limit_guardrail():
    assert enumerate_models(["p"], limit=0).status == "error"
    assert enumerate_models(["p"], limit=99999).status == "error"
