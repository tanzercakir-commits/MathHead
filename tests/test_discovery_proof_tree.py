"""Discovery Track T3 (slice) — reconstruct a proof's dependency tree (its lemmas), made explicit."""
from fractions import Fraction

import pytest

from mathhead.discovery import run_arithmetic_discovery
from mathhead.discovery.proof_tree import (
    PROOF_TREE_COVERAGE,
    ProofNode,
    coverage_for,
    identity_proof_tree,
    proof_tree,
    render_tree,
    resolve_builder,
    sum_proof_tree,
    tree_or_reason,
)


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


# --- v4F6: T3 coverage inventory — every proved/certified kind has a tree OR an honest reason ---

def test_kernel_identity_gets_an_honest_leaf_tree():
    from mathhead.discovery.identities import run_identity_discovery
    f = next(x for x in run_identity_discovery() if x.expression == "n**3 - n")
    tree = identity_proof_tree(f)
    assert tree.certainty == "kernel_identity" and tree.children == []
    assert "no intermediate lemmas" in tree.note              # a leaf, and it says why
    assert "n**3 - n = n*(n - 1)*(n + 1)" in render_tree(tree)


def test_unverified_identity_tree_is_not_dressed_up():
    from mathhead.discovery.identities import IdentityFinding
    fake = IdentityFinding("n**2", "n*n", kernel_verified=False)
    tree = identity_proof_tree(fake)
    assert tree.certainty == "unknown" and "not kernel-verified" in tree.note


def test_every_coverage_entry_has_exactly_a_tree_or_an_honest_reason():
    assert PROOF_TREE_COVERAGE
    for cov in PROOF_TREE_COVERAGE:
        assert (cov.builder_ref is None) != (cov.reason is None)   # exactly one of the two
        if cov.builder_ref is not None:
            assert callable(resolve_builder(cov))                  # pinned: cannot drift
        else:
            assert len(cov.reason) > 40                            # a real reason, not a stub


def test_inventory_covers_every_certainty_the_live_report_emits():
    # the audit: collect every proved/certified certainty label the LIVE report actually emits,
    # and require the inventory to answer tree-or-reason for each — a new proved kind without
    # coverage fails here loudly
    from mathhead.discovery import run_report
    r = run_report(max_n=5)
    emitted = {it["certainty"] for it in r.proved if it.get("certainty")}
    emitted |= {it["certainty"] for it in r.frontier if it.get("confirmed")}
    emitted |= {"constructive_bounded" for it in r.open_bounded if it.get("certified")}
    emitted |= {ex["status"] for ex in r.explanations if ex.get("status") == "constructive_bijection"}
    assert {"formal_proof", "kernel_identity", "solver_verified", "constructive_bijection",
            "constructive_bounded"} <= emitted                # the audit really sees the kinds
    for certainty in sorted(emitted):
        builder, reason = tree_or_reason(certainty)           # KeyError here = uncovered kind
        assert (builder is None) != (reason is None)


def test_live_proved_sum_identities_are_tree_covered():
    # the evaluator's v4F6 finding, pinned: proved sums now carry formal_proof (kernel-backed),
    # the inventory maps them to a REAL tree via the kind-exact query, and the tree builds
    from mathhead.discovery import run_report
    sums = [it for it in run_report(max_n=5).proved if it["statement"].startswith("sum_")]
    assert sums and all(it["certainty"] == "formal_proof" and it["kernel_verified"] for it in sums)
    builder, reason = tree_or_reason("formal_proof", kind="sum_identity")
    assert builder is sum_proof_tree and reason is None
    tree = builder((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))   # Σi = n(n+1)/2
    assert tree.certainty == "formal_proof" and len(tree.children) == 2
    # and the kind-exact modular lookup still returns the modular builder
    assert tree_or_reason("formal_proof", kind="modular_divisibility")[0] is proof_tree
    with pytest.raises(KeyError):                       # unrecorded (kind, certainty) pair is loud
        tree_or_reason("formal_proof", kind="kernel_identity")


def test_certificate_kinds_get_reasons_not_fabricated_trees():
    for certainty in ("constructive_bijection", "constructive_bounded", "solver_verified",
                      "exact_integer_certificate", "independently_verified_witness",
                      "independently_verified_unsat_proof",
                      "independently_verified_unsat_proof_of_strengthened_formula",
                      "solver_verified_with_derived_lemmas", "interval_certified"):
        builder, reason = tree_or_reason(certainty)
        assert builder is None and reason                     # honest: no tree, and it says why
    # the check()-door kernel tier wraps kernel proof terms — those DO have trees
    assert tree_or_reason("kernel_verified")[0] is proof_tree


def test_tree_covered_kinds_resolve_to_the_right_builders():
    assert resolve_builder(coverage_for("exhaustive_residue_proof")) is proof_tree
    assert resolve_builder(coverage_for("kernel_identity")) is identity_proof_tree
    by_kind = {c.kind: c for c in PROOF_TREE_COVERAGE}
    assert resolve_builder(by_kind["sum_identity"]) is sum_proof_tree
    # and the builders really produce ProofNodes on live findings
    f = next(x for x in run_arithmetic_discovery(check_upto=40) if x.expression == "n**3 - n")
    assert isinstance(proof_tree(f), ProofNode)


def test_unknown_certainty_fails_loudly():
    with pytest.raises(KeyError):
        tree_or_reason("made_up_tier")
