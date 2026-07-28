"""
Property-based (özellik temelli) testler — `hypothesis` ile rastgele formüller
üretip DEĞİŞMEZLERİ (invariants) doğrular. Amaç: motorun *güvenilirliği* —
hiç çökmemesi, araçların birbiriyle tutarlı olması, türeticinin sağlamlığı.
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


# Rastgele iyi-biçimli önermeler mantığı formülü (birkaç değişken üzerinde).
formulas = st.recursive(st.sampled_from(_VARS), _extend, max_leaves=6)

_KNOWN = {"valid", "invalid", "sat", "unsat", "unknown", "error"}
_CFG = settings(max_examples=60, deadline=None)


# ------------------------------ çökme yok --------------------------------- #
@_CFG
@given(st.text(max_size=40))
def test_never_crashes_on_arbitrary_text(s):
    # Girdi ne olursa olsun: bilinen bir statü döner, exception fırlatmaz.
    assert check_consistency([s]).status in _KNOWN


@_CFG
@given(st.text(max_size=40))
def test_simplify_never_crashes(s):
    assert simplify(s).status in {"ok", "error"}


# ------------------ araçlar arası tutarlılık (soundness) ------------------- #
@_CFG
@given(formulas, formulas)
def test_entailment_iff_negation_unsat(a, b):
    # A ⊨ B  ⟺  {A, ¬B} tutarsız  (mantığın temel özdeşliği; iki araç çapraz kontrol)
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
    # GARANTİ: aynı girdi -> aynı VERDICT (status). Tanık (witness) bir örnektir;
    # birden çok geçerli model varsa hangisinin döndüğü değişebilir (bkz. ADR-0019).
    first = check_consistency([a]).status
    for _ in range(3):
        assert check_consistency([a]).status == first


# ------------------------- türetici sağlamlığı ---------------------------- #
@_CFG
@given(formulas, formulas)
def test_prover_never_proves_invalid(a, b):
    p = prove_entailment([a], b)
    if p.proof_steps is not None:                     # bir türetim kurulduysa
        assert check_entailment([a], b).status == "valid"   # gerçekten geçerli olmalı
    if p.used_premises is not None:
        assert all(i == 0 for i in p.used_premises)   # tek öncül var (indeks 0)
