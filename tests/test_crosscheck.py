"""
Çapraz denetim (ROADMAP Track C3) — cross_check: Z3 ⋈ SymPy mutabakatı.

Öne geçiren özellik: iki BAĞIMSIZ motor. Anlaştıklarında yüksek güven; çeliştiklerinde
(ör. domain tuzağı) bayrak. Best + worst + dürüst tek-motor yolu.
"""
from mathhead.core.crosscheck import cross_check


def test_consensus_equal():
    r = cross_check("(x+1)**2", "x**2 + 2*x + 1")
    assert r.status == "valid"
    assert r.reason_code == "CONSENSUS_EQUAL"
    assert r.details["sympy"] == "equal" and r.details["z3"] == "equal"


def test_consensus_not_equal():
    r = cross_check("2*x", "3*x")
    assert r.status == "invalid"
    assert r.reason_code == "CONSENSUS_NOT_EQUAL"


def test_engines_disagree_on_domain_trap():
    # ÖNE GEÇİREN: (x²-1)/(x-1) vs x+1 — SymPy 'equal', Z3 x=1'de 'not_equal'.
    # Anlaşmazlık, domain tuzağını açığa çıkarır (iki bağımsız tanık).
    r = cross_check("(x**2 - 1)/(x - 1)", "x + 1")
    assert r.status == "unknown"
    assert r.reason_code == "ENGINES_DISAGREE"
    assert r.details["sympy"] == "equal"
    assert r.details["z3"] == "not_equal"


def test_single_engine_transcendental():
    # sin²+cos²=1 — Z3 desteklemiyor (transandantal), yalnız SymPy karar verir
    r = cross_check("sin(x)**2 + cos(x)**2", "1")
    assert r.status == "valid"
    assert r.reason_code == "SINGLE_ENGINE"
    assert r.details["z3"] == "unsupported"


def test_single_engine_root_branch():
    # sqrt(x²) = x YANLIŞ (|x| ≠ x, x<0). SymPy yakalar; Z3 desteklemez.
    r = cross_check("sqrt(x**2)", "x")
    assert r.status == "invalid"
    assert r.reason_code == "SINGLE_ENGINE"


def test_cross_check_rejects_equation():
    assert cross_check("x == 2", "x").status == "error"


def test_cross_check_determinism():
    # ADR-0020: .equals() rastgeleliği çıkarıldı; sqrt(x²) artık kararlı olmalı.
    for _ in range(10):
        assert cross_check("(x+1)**2", "x**2 + 2*x + 1").reason_code == "CONSENSUS_EQUAL"
        assert cross_check("(x**2 - 1)/(x - 1)", "x + 1").reason_code == "ENGINES_DISAGREE"
        assert cross_check("sqrt(x**2)", "x").status == "invalid"   # deterministik
