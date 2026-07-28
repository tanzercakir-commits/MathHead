"""
v3 — ispat üretimi: minimal çekirdek + doğal tümdengelim (natural deduction).

Bayrak testi: klasik silogizmin adım adım türetimi.
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
    # evrensel örnekleme adımı var
    assert any(s["rule"].startswith("evrensel örnekleme") for s in r.proof_steps)


def test_modus_ponens_chain():
    r = prove_entailment(["p", "implies(p, q)", "implies(q, r)"], "r")
    assert r.status == "valid"
    assert r.proof_steps[-1]["formula"] == "r"


def test_and_elimination():
    r = prove_entailment(["a and b"], "a")
    assert r.status == "valid"
    assert any(s["rule"] == "∧-ayıklama" for s in r.proof_steps)


def test_minimal_core_excludes_unused_premise():
    r = prove_entailment(["p", "implies(p, q)", "unused"], "q")
    assert r.status == "valid"
    assert r.used_premises == [0, 1]  # 'unused' (indeks 2) çekirdekte yok


def test_invalid_gives_counterexample_no_steps():
    r = prove_entailment(["Man(socrates)"], "Mortal(socrates)")
    assert r.status == "invalid"
    assert r.proof_steps is None
    assert r.witness is not None


def test_arithmetic_valid_but_no_nd_steps():
    # Z3 geçerli der; ND türetimi bu parça için kurulamaz -> dürüst fallback
    r = prove_entailment(["x > 5"], "x > 0")
    assert r.status == "valid"
    assert r.proof_steps is None
    assert r.used_premises == [0]


# ---------------------- genişletilmiş kurallar (v3.1) --------------------- #
def test_modus_tollens():
    r = prove_entailment(["implies(p, q)", "not(q)"], "not(p)")
    assert r.status == "valid"
    assert any(s["rule"] == "modus tollens" for s in r.proof_steps)


def test_disjunctive_syllogism():
    r = prove_entailment(["p or q", "not(p)"], "q")
    assert r.status == "valid"
    assert any(s["rule"] == "ayrık tasım" for s in r.proof_steps)


def test_proof_by_cases_via_raa():
    # p->r, q->r, p∨q ⊨ r  (doğrudan kurulamaz; çelişkiden/RAA ile)
    r = prove_entailment(["implies(p, r)", "implies(q, r)", "p or q"], "r")
    assert r.status == "valid"
    assert r.proof_steps[-1]["rule"] == "çelişkiden ispat (RAA)"


def test_de_morgan():
    r = prove_entailment(["not(p or q)"], "not(p)")
    assert r.status == "valid"
    assert any(s["rule"] == "De Morgan" for s in r.proof_steps)


# ------------------ varoluşsal (∃) akıl yürütme (v3.2) -------------------- #
def test_existential_elimination_and_introduction():
    # ∃x P(x), ∀x (P(x)->Q(x))  ⊨  ∃x Q(x)
    r = prove_entailment(
        ["exists(x, P(x))", "forall(x, implies(P(x), Q(x)))"], "exists(x, Q(x))"
    )
    assert r.status == "valid"
    assert any("varoluşsal eleme" in s["rule"] for s in r.proof_steps)
    assert r.proof_steps[-1]["rule"].startswith("varoluşsal içe alma")


def test_existential_introduction_simple():
    r = prove_entailment(["P(a)"], "exists(x, P(x))")
    assert r.status == "valid"
    assert r.proof_steps[-1]["rule"].startswith("varoluşsal içe alma")
