"""
Sağlamlaştırma-1 (ROADMAP Aşama 2) — hesap katmanı için property-based
(özellik temelli) testler + determinizm denetimi + parser fuzz.

Amaç: motorun *güvenilirliği*. Rastgele girdilerde (a) hiç çökmeme (güvenlik:
beyaz-liste sızıntısı yok), (b) matematiksel değişmezlerin korunması, (c) aynı
girdi → aynı çıktı (determinizm; ADR-0019).
"""
import hypothesis.strategies as st
from hypothesis import assume, given, settings

from mathhead.compute import (
    determinant,
    differentiate,
    eigenvalues,
    integrate,
    limit,
    matrix_multiply,
    matrix_rank,
    matrix_solve,
    series,
    simplify,
    solve,
)

_CFG = settings(max_examples=60, deadline=None)
_OK_OR_ERR = {"ok", "error"}

# --- stratejiler --------------------------------------------------------- #
_cell = st.integers(min_value=-9, max_value=9).map(str)
_row2 = st.lists(_cell, min_size=2, max_size=2)
_mat2 = st.lists(_row2, min_size=2, max_size=2)


def _extend(ch):
    pair = st.tuples(ch, ch)
    return st.one_of(
        pair.map(lambda t: f"({t[0]} + {t[1]})"),
        pair.map(lambda t: f"({t[0]} - {t[1]})"),
        pair.map(lambda t: f"({t[0]} * {t[1]})"),
    )


_exprs = st.recursive(st.sampled_from(["x", "y", "2", "3"]), _extend, max_leaves=5)


# ------------------------------ çökme yok (fuzz) -------------------------- #
@_CFG
@given(st.text(max_size=30))
def test_scalar_ops_never_crash(s):
    # Girdi ne olursa olsun: ok|error döner, exception fırlatmaz (güvenlik değişmezi).
    assert simplify(s).status in _OK_OR_ERR
    assert solve(s, "x").status in _OK_OR_ERR
    assert differentiate(s, "x").status in _OK_OR_ERR
    assert integrate(s, "x").status in _OK_OR_ERR
    assert limit(s, "x", "0").status in _OK_OR_ERR
    assert series(s, "x", "0", 3).status in _OK_OR_ERR


@_CFG
@given(st.lists(st.lists(st.text(max_size=6), min_size=1, max_size=3), min_size=1, max_size=3))
def test_matrix_ops_never_crash(m):
    # Düzensiz/kötücül/çöp hücreler bile çökmez (ragged, __import__, boş...).
    assert determinant(m).status in _OK_OR_ERR
    assert matrix_rank(m).status in _OK_OR_ERR


# --------------------- matematiksel değişmezler --------------------------- #
@_CFG
@given(_mat2, _mat2)
def test_det_multiplicative(a, b):
    # det(A·B) = det(A)·det(B)  (temel özdeşlik, iki araç çapraz kontrol)
    prod = matrix_multiply(a, b)
    assert prod.status == "ok"
    assert int(determinant(prod.result).result) == \
        int(determinant(a).result) * int(determinant(b).result)


@_CFG
@given(_mat2)
def test_det_transpose_invariant(a):
    # det(Aᵀ) = det(A)
    at = [[a[j][i] for j in range(len(a))] for i in range(len(a[0]))]
    assert int(determinant(at).result) == int(determinant(a).result)


@_CFG
@given(_mat2, st.lists(_cell, min_size=2, max_size=2))
def test_matsolve_roundtrip(a, x):
    # Tekil olmayan A ve seçili x için b=A·x kur; Ax=b çöz → x'i geri ver.
    assume(int(determinant(a).result) != 0)
    xcol = [[xi] for xi in x]
    b = matrix_multiply(a, xcol).result           # 2×1
    bvec = [row[0] for row in b]
    sol = matrix_solve(a, bvec)
    assert sol.result == [{"x0": x[0], "x1": x[1]}]


@_CFG
@given(_exprs)
def test_simplify_idempotent(s):
    # simplify(simplify(e)) == simplify(e)  (kararlı kanonik form)
    r1 = simplify(s)
    assert r1.status == "ok"
    assert simplify(r1.result).result == r1.result


# ------------------------------ determinizm ------------------------------- #
@_CFG
@given(_mat2)
def test_matrix_determinism(a):
    # Aynı girdi → aynı çıktı (det, rank, özdeğer). Verdict deterministik.
    d0 = determinant(a).result
    r0 = matrix_rank(a).result
    e0 = eigenvalues(a).result
    for _ in range(3):
        assert determinant(a).result == d0
        assert matrix_rank(a).result == r0
        assert eigenvalues(a).result == e0


@_CFG
@given(_exprs)
def test_scalar_determinism(s):
    first = simplify(s).result
    for _ in range(3):
        assert simplify(s).result == first
