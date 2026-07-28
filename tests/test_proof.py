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
