"""
v1.2 — uninterpreted predicates + individuals: true relational FOL.

The flagship test here is the classic syllogism: the canonical example showing
that a logic engine is "first-order".
"""
from mathhead.core import check_consistency, check_entailment


def test_classic_syllogism():
    # All men are mortal; Socrates is a man  ⊨  Socrates is mortal
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
    # P(a) and ∀x.¬P(x) contradict. Engine must say 'unsat' (correct) or 'unknown' (honest);
    # must NEVER say 'sat' (wrong).
    r = check_consistency(["P(a)", "forall(x, not(P(x)))"])
    assert r.status in ("unsat", "unknown")


# --------------------------- guardrail / sort ----------------------------- #
def test_predicate_argument_must_be_individual():
    r = check_consistency(["P(2)"])  # number is not an individual
    assert r.status == "error"
    assert r.reason_code == "PARSE_ERROR"


def test_inconsistent_arity_rejected():
    assert check_consistency(["P(a)", "P(a, b)"]).status == "error"


def test_predicate_and_variable_name_clash_rejected():
    # 'p' can't be both a predicate and a variable in the same problem
    assert check_consistency(["p", "p(a)"]).status == "error"
