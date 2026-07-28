"""
v1.2 — yorumsuz yüklemler (predicates) + bireyler: gerçek ilişkisel FOL.

Buradaki bayrak testi klasik silogizmdir: bir mantık motorunun "first-order"
olduğunu gösteren kanonik örnek.
"""
from mathhead.core import check_consistency, check_entailment


def test_classic_syllogism():
    # Tüm insanlar ölümlüdür; Sokrates insandır  ⊨  Sokrates ölümlüdür
    r = check_entailment(
        ["forall(x, implies(Man(x), Mortal(x)))", "Man(socrates)"],
        "Mortal(socrates)",
    )
    assert r.status == "valid"
    assert r.reason_code == "ENTAILED"


def test_missing_premise_is_invalid():
    r = check_entailment(["Man(socrates)"], "Mortal(socrates)")
    assert r.status == "invalid"


def test_relational_rule_application():
    # ∀x∀y. Parent(x,y) → Ancestor(x,y);  Parent(alice,bob)  ⊨  Ancestor(alice,bob)
    r = check_entailment(
        ["forall(x, forall(y, implies(Parent(x, y), Ancestor(x, y))))", "Parent(alice, bob)"],
        "Ancestor(alice, bob)",
    )
    assert r.status == "valid"


def test_existential_predicate_is_consistent():
    assert check_consistency(["exists(x, Happy(x))"]).status == "sat"


def test_direct_contradiction_is_unsat():
    r = check_consistency(["P(a)", "not(P(a))"])
    assert r.status == "unsat"


def test_quantified_contradiction_is_sound():
    # P(a) ve ∀x.¬P(x) çelişir. Motor 'unsat' (doğru) ya da 'unknown' (dürüst)
    # demeli; ASLA 'sat' (yanlış) dememeli.
    r = check_consistency(["P(a)", "forall(x, not(P(x)))"])
    assert r.status in ("unsat", "unknown")


# --------------------------- guardrail / sort ----------------------------- #
def test_predicate_argument_must_be_individual():
    r = check_consistency(["P(2)"])  # sayı birey değil
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_inconsistent_arity_rejected():
    assert check_consistency(["P(a)", "P(a, b)"]).status == "error"


def test_predicate_and_variable_name_clash_rejected():
    # 'p' aynı problemde hem yüklem hem değişken olamaz
    assert check_consistency(["p", "p(a)"]).status == "error"
