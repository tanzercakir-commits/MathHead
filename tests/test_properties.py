"""
Property-based tests — generate random formulas with `hypothesis` and check
INVARIANTS. Goal: the engine's *reliability* — never crashing, tools being
consistent with each other, soundness of the prover.
"""
import hypothesis.strategies as st
from hypothesis import given, settings

from mathhead.compute import simplify
from mathhead.core.logic import check_consistency, check_entailment, enumerate_models
from mathhead.core.proof import prove_entailment

_VARS = ["p", "q", "r"]


def _extend(children):
    pair = st.tuples(children, children)
    return st.one_of(
        children.map(lambda a: f"not({a})"),
        pair.map(lambda t: f"({t[0]} and {t[1]})"),
        pair.map(lambda t: f"({t[0]} or {t[1]})"),
        pair.map(lambda t: f"implies({t[0]}, {t[1]})"),
        pair.map(lambda t: f"iff({t[0]}, {t[1]})"),
    )


# Random well-formed propositional logic formula (over a few variables).
formulas = st.recursive(st.sampled_from(_VARS), _extend, max_leaves=6)

_KNOWN = {"valid", "invalid", "sat", "unsat", "unknown", "error"}
_CFG = settings(max_examples=60, deadline=None)


# ------------------------------ no crash --------------------------------- #
@_CFG
@given(st.text(max_size=40))
def test_never_crashes_on_arbitrary_text(s):
    # Whatever the input: returns a known status, doesn't throw an exception.
    assert check_consistency([s]).status in _KNOWN


@_CFG
@given(st.text(max_size=40))
def test_simplify_never_crashes(s):
    assert simplify(s).status in {"ok", "error"}


# ------------------ cross-tool consistency (soundness) ------------------- #
@_CFG
@given(formulas, formulas)
def test_entailment_iff_negation_unsat(a, b):
    # A ⊨ B  ⟺  {A, ¬B} inconsistent  (fundamental logic identity; two tools cross-checked)
    ent = check_entailment([a], b)
    cons = check_consistency([a, f"not({b})"])
    assert (ent.status == "valid") == (cons.status == "unsat")


@_CFG
@given(formulas)
def test_self_entailment_always_valid(a):
    assert check_entailment([a], a).status == "valid"


@_CFG
@given(formulas)
def test_enumerate_iff_consistency(a):
    assert (check_consistency([a]).status == "sat") == (enumerate_models([a]).count > 0)


@_CFG
@given(formulas)
def test_verdict_determinism(a):
    # GUARANTEE: same input -> same VERDICT (status). The witness is one example;
    # if multiple valid models exist, which one is returned may vary (see ADR-0019).
    first = check_consistency([a]).status
    for _ in range(3):
        assert check_consistency([a]).status == first


# ------------------------- prover soundness ---------------------------- #
@_CFG
@given(formulas, formulas)
def test_prover_never_proves_invalid(a, b):
    p = prove_entailment([a], b)
    if p.proof_steps is not None:                     # if a derivation was built
        assert check_entailment([a], b).status == "valid"   # must actually be valid
    if p.used_premises is not None:
        assert all(i == 0 for i in p.used_premises)   # only one premise (index 0)
