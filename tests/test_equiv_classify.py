"""Logical equivalence (`equivalent`) and classification (`classify`)."""
from mathhead.core.logic import classify, equivalent


def test_de_morgan_equivalence():
    assert equivalent("not(p or q)", "not(p) and not(q)").status == "equivalent"


def test_implication_rewrite_equivalence():
    # implies(p, q) ≡ (not p) or q
    assert equivalent("implies(p, q)", "not(p) or q").status == "equivalent"


def test_not_equivalent_has_witness():
    r = equivalent("p", "q")
    assert r.status == "not_equivalent"
    assert r.witness is not None


def test_classify_tautology():
    assert classify("p or not(p)").status == "tautology"


def test_classify_contradiction():
    assert classify("p and not(p)").status == "contradiction"


def test_classify_contingent_has_both_witnesses():
    r = classify("p and q")
    assert r.status == "contingent"
    assert "true_witness" in r.witness and "false_witness" in r.witness


def test_malformed_input_is_error():
    assert equivalent("(", "p").status == "error"
    assert classify(")").status == "error"
