"""
v3 — proof generation: minimal core + natural deduction.

Flagship test: step-by-step derivation of the classic syllogism.
"""
from mathhead.core.proof import prove_entailment


def test_syllogism_proof_steps():
    r = prove_entailment(
        ["forall(x, implies(Man(x), Mortal(x)))", "Man(socrates)"],
        "Mortal(socrates)",
    )
    assert r.status == "valid"
    assert r.proof_steps is not None
    last = r.proof_steps[-1]
    assert last["formula"] == "Mortal(socrates)"
    assert last["rule"] == "modus ponens"
    # universal instantiation step present
    assert any(s["rule"].startswith("universal instantiation") for s in r.proof_steps)


def test_modus_ponens_chain():
    r = prove_entailment(["p", "implies(p, q)", "implies(q, r)"], "r")
    assert r.status == "valid"
    assert r.proof_steps[-1]["formula"] == "r"


def test_and_elimination():
    r = prove_entailment(["a and b"], "a")
    assert r.status == "valid"
    assert any(s["rule"] == "conjunction elimination" for s in r.proof_steps)


def test_minimal_core_excludes_unused_premise():
    r = prove_entailment(["p", "implies(p, q)", "unused"], "q")
    assert r.status == "valid"
    assert r.used_premises == [0, 1]  # 'unused' (index 2) not in core


def test_invalid_gives_counterexample_no_steps():
    r = prove_entailment(["Man(socrates)"], "Mortal(socrates)")
    assert r.status == "invalid"
    assert r.proof_steps is None
    assert r.witness is not None


def test_arithmetic_valid_but_no_nd_steps():
    # Z3 says valid; ND derivation can't be built for this fragment -> honest fallback
    r = prove_entailment(["x > 5"], "x > 0")
    assert r.status == "valid"
    assert r.proof_steps is None
    assert r.used_premises == [0]


# ---------------------- extended rules (v3.1) --------------------- #
def test_modus_tollens():
    r = prove_entailment(["implies(p, q)", "not(q)"], "not(p)")
    assert r.status == "valid"
    assert any(s["rule"] == "modus tollens" for s in r.proof_steps)


def test_disjunctive_syllogism():
    r = prove_entailment(["p or q", "not(p)"], "q")
    assert r.status == "valid"
    assert any(s["rule"] == "disjunctive syllogism" for s in r.proof_steps)


def test_proof_by_cases_via_raa():
    # p->r, q->r, p∨q ⊨ r  (not directly derivable; via contradiction/RAA)
    r = prove_entailment(["implies(p, r)", "implies(q, r)", "p or q"], "r")
    assert r.status == "valid"
    assert r.proof_steps[-1]["rule"] == "proof by contradiction (RAA)"


def test_de_morgan():
    r = prove_entailment(["not(p or q)"], "not(p)")
    assert r.status == "valid"
    assert any(s["rule"] == "De Morgan" for s in r.proof_steps)


# ------------------ existential (∃) reasoning (v3.2) -------------------- #
def test_existential_elimination_and_introduction():
    # ∃x P(x), ∀x (P(x)->Q(x))  ⊨  ∃x Q(x)
    r = prove_entailment(
        ["exists(x, P(x))", "forall(x, implies(P(x), Q(x)))"], "exists(x, Q(x))"
    )
    assert r.status == "valid"
    assert any("existential elimination" in s["rule"] for s in r.proof_steps)
    assert r.proof_steps[-1]["rule"].startswith("existential introduction")


def test_existential_introduction_simple():
    r = prove_entailment(["P(a)"], "exists(x, P(x))")
    assert r.status == "valid"
    assert r.proof_steps[-1]["rule"].startswith("existential introduction")
