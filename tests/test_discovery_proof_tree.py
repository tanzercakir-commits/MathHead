"""Discovery Track T3 (slice) — reconstruct a proof's dependency tree (its lemmas), made explicit."""
from fractions import Fraction

from mathhead.discovery import run_arithmetic_discovery
from mathhead.discovery.proof_tree import proof_tree, render_tree, sum_proof_tree


def _by_expr():
    return {f.expression: f for f in run_arithmetic_discovery(check_upto=40)}


def test_crt_proof_exposes_its_prime_power_lemmas():
    tree = proof_tree(_by_expr()["n**3 - n"])          # proved via modulus-factoring (2*3)
    assert tree.method == "CRT"
    child_claims = {c.claim for c in tree.children}
    assert child_claims == {"(n**3 - n) % 2 == 0", "(n**3 - n) % 3 == 0"}
    assert all(c.method == "induction" for c in tree.children)


def test_residue_proof_is_a_complete_leaf():
    tree = proof_tree(_by_expr()["n**5 - n"])          # proved via residue-exhaustion
    assert tree.method == "residue-exhaustion" and tree.children == []
    assert "30 residues" in tree.note


def test_prime_modulus_proof_is_a_single_induction():
    tree = proof_tree(_by_expr()["n*(n+1)"])           # mod 2, one induction
    assert tree.method == "induction" and tree.children == []


def test_render_is_readable():
    text = render_tree(proof_tree(_by_expr()["n**3 - n"]))
    assert "(n**3 - n) % 6 == 0" in text and "CRT" in text
    assert "% 2 == 0" in text and "% 3 == 0" in text   # the lemmas are shown, indented


def test_sum_identity_tree_exposes_base_and_step_lemmas():
    # Σ_{i=1}^n i = n(n+1)/2 → f=(0,1), g=(0,1/2,1/2)
    tree = sum_proof_tree((0, 1), (0, Fraction(1, 2), Fraction(1, 2)), "sum i = n(n+1)/2")
    assert tree.method == "SumInduction" and tree.certainty == "formal_proof"
    methods = {c.method for c in tree.children}
    assert methods == {"evaluation", "PolyIdentity"}          # base case + kernel-checked step
    step = next(c for c in tree.children if c.method == "PolyIdentity")
    assert step.certainty == "kernel_verified"


def test_false_sum_identity_tree_is_not_proved():
    tree = sum_proof_tree((0, 1), (0, 0, 1), "sum i = n^2")   # false
    assert tree.certainty == "unknown" and tree.children == [] and "not proved" in tree.note


def test_sum_tree_render_and_determinism():
    a = sum_proof_tree((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))
    b = sum_proof_tree((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))
    assert render_tree(a) == render_tree(b) and "SumInduction" in render_tree(a)
