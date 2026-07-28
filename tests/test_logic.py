"""
v1 DAVRANIŞ SPESİFİKASYONU — best-case / worst-case senaryolar (gerçek Z3).

Bunlar motorun v1 sözleşmesidir ve YEŞİL kalmalıdır. Kaynak: proje prensibi
"iyi tasarlanmış otomatik testler (best/worst case)".
"""
import pytest

from mathhead.core import check_consistency, check_entailment, find_model


# ----------------------------- BEST CASE ---------------------------------- #
def test_modus_ponens_is_valid():
    r = check_entailment(["p", "implies(p, q)"], "q")
    assert r.status == "valid"
    assert r.reason_code == "ENTAILED"
    assert r.is_conclusive()


def test_non_entailment_returns_counterexample():
    r = check_entailment(["p"], "q")
    assert r.status == "invalid"
    assert r.witness == {"p": True, "q": False}


def test_arithmetic_non_entailment_counterexample():
    r = check_entailment(["x > 0"], "x > 5")
    assert r.status == "invalid"
    assert 0 < r.witness["x"] <= 5  # öncülü sağlar, sonucu çürütür


def test_contradiction_is_unsat_with_core():
    r = check_consistency(["p", "not(p)"])
    assert r.status == "unsat"
    assert r.reason_code == "CONTRADICTION"
    assert r.witness["unsat_core_indices"] == [0, 1]


def test_consistent_set_is_sat_with_model():
    r = check_consistency(["x > 2", "x < 5", "p"])
    assert r.status == "sat"
    assert 2 < r.witness["x"] < 5
    assert r.witness["p"] is True


def test_find_model_linear_arithmetic():
    r = find_model(["x > 2", "x < 5"])
    assert r.status == "sat"
    assert 2 < r.witness["x"] < 5


def test_chained_comparison_entailment():
    # 1 < x < 5  ⊨  x < 10
    r = check_entailment(["1 < x", "x < 5"], "x < 10")
    assert r.status == "valid"


def test_iff_and_xor_are_contradictory():
    r = check_consistency(["iff(p, q)", "xor(p, q)"])
    assert r.status == "unsat"


# ------------------- WORST CASE / guardrails / dürüstlük ------------------- #
def test_nonlinear_multiplication_is_rejected():
    r = check_consistency(["x*y > 0"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_syntax_error_is_rejected():
    r = check_consistency(["("])
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_inconsistent_sort_is_rejected():
    # 'p' aynı problemde hem Bool (and) hem Int (>) olamaz -> sessiz varsayım yok
    r = check_consistency(["p and (p > 3)"])
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_empty_input_is_rejected():
    r = check_consistency([])
    assert r.status == "error"
    assert r.reason_code == "GUARDRAIL_VIOLATION"


def test_unknown_and_error_are_not_conclusive():
    assert check_consistency(["("]).is_conclusive() is False


# --------------------------- DETERMİNİZM (duvar #3) ------------------------ #
def test_determinism_same_input_same_output():
    query = (["x > 0", "x < 10"], "x < 5")  # invalid + karşıörnek
    first = check_entailment(*query)
    assert first.status == "invalid"
    for _ in range(50):
        r = check_entailment(*query)
        assert r.status == first.status
        assert r.witness == first.witness  # karşıörnek bile birebir aynı olmalı
