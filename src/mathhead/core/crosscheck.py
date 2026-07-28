"""
mathhead.core.crosscheck — ÇAPRAZ DENETİM (Z3 ⋈ SymPy), ROADMAP Track C3.

**Öne geçiren fikir:** Aynı iddiayı İKİ BAĞIMSIZ motorla doğrula; mutabakat şart.
- SymPy (CAS, sembolik) ve Z3 (SMT, gerçel karar) birbirinden bağımsız çalışır.
- İkisi de "denk" derse → **mutabakat** (tek-motorlu rakiplerin veremeyeceği güven).
- İkisi çelişirse → **ANLAŞMAZLIK**: çoğu zaman ince bir konuyu (ör. tanım kümesi /
  domain tuzağı) açığa çıkarır ve insana bayrak kaldırır (dürüst 'unknown').

Örnek (fark yaratan): `(x²-1)/(x-1)` vs `x+1` — SymPy sembolik "denk" der; Z3 gerçel
bölme semantiğiyle `x=1`'de ayrışır → **anlaşmazlık** → domain tuzağı yakalanır.

Not: Z3 tarafı yalnız polinom/rasyonel gerçel ifadeleri denetler; `sin/exp/log`
gibi ifadelerde Z3 "desteklenmiyor" der ve tek-motor (SymPy) kararına düşülür.
"""
from __future__ import annotations

import time
from typing import Any

import sympy
import z3

from mathhead.compute import ComputeError, _meta, _parse
from mathhead.core.inequality import _IneqError, _translate
from mathhead.core.verify import VerifyResult, _equal_verdict
from mathhead.guardrails import solver_config

__all__ = ["cross_check"]


def _sympy_equal(left: str, right: str) -> str:
    """SymPy tarafı (DETERMİNİSTİK): 'equal' | 'not_equal' | 'undecided' | 'error'.

    Ortak deterministik yardımcı `verify._equal_verdict` (simplify + sabit-nokta
    karşıörnek; `.equals()`'in rastgeleliği YOK) — çapraz denetim de deterministik.
    """
    syms: dict[str, Any] = {}
    try:
        le = _parse(left, syms)
        re = _parse(right, syms)
        if isinstance(le, sympy.Equality) or isinstance(re, sympy.Equality):
            return "error"
    except ComputeError:
        return "error"
    return _equal_verdict(le, re, syms)[0]


def _z3_equal(left: str, right: str) -> tuple[str, dict | None]:
    """Z3 tarafı: ('equal'|'not_equal'|'undecided'|'unsupported', karşıörnek?)."""
    rvars: dict[str, Any] = {}
    try:
        lz = _translate(left, rvars)
        rz = _translate(right, rvars)
    except (_IneqError, SyntaxError, ValueError):
        return "unsupported", None
    if z3.is_bool(lz) or z3.is_bool(rz):     # karşılaştırma değil, ifade beklenir
        return "unsupported", None
    solver = solver_config(5_000, 42)
    solver.add(z3.Not(lz == rz))
    res = solver.check()
    if res == z3.unsat:
        return "equal", None
    if res == z3.sat:
        model = solver.model()
        cx = {}
        for name, const in rvars.items():
            val = model.eval(const, model_completion=True)
            cx[name] = str(val)
        return "not_equal", cx
    return "undecided", None


def cross_check(left: str, right: str) -> VerifyResult:
    """`left` = `right` iddiasını Z3 ve SymPy ile BAĞIMSIZ doğrular; mutabakat arar.

    valid → iki motor da 'denk' (CONSENSUS_EQUAL) ya da tek motor doğruladı
    (SINGLE_ENGINE). invalid → iki motor da 'denk değil'. unknown →
    **ENGINES_DISAGREE** (motorlar çelişiyor; ince konu/domain bayrağı) ya da ikisi
    de kararsız (CROSS_UNDECIDED).
    """
    t0 = time.perf_counter()
    sym = _sympy_equal(left, right)
    if sym == "error":
        return VerifyResult("error", "PARSE_ERROR",
                            "cross_check: ifade ayrıştırılamadı (ya da denklem verildi).",
                            None, _meta(t0))
    z3v, cx = _z3_equal(left, right)
    details = {"sympy": sym, "z3": z3v}
    if cx:
        details["z3_counterexample"] = cx

    decisive = {"equal", "not_equal"}
    # her iki motor da kararlı
    if sym in decisive and z3v in decisive:
        if sym == z3v:
            if sym == "equal":
                return VerifyResult("valid", "CONSENSUS_EQUAL",
                                    "iki bağımsız motor (Z3 + SymPy) DENK diyor (mutabakat).",
                                    details, _meta(t0))
            return VerifyResult("invalid", "CONSENSUS_NOT_EQUAL",
                                f"iki motor da DENK DEĞİL diyor (mutabakat); karşıörnek: {cx}.",
                                details, _meta(t0))
        # çelişki — ince konu bayrağı (çoğunlukla domain / tanım kümesi)
        return VerifyResult(
            "unknown", "ENGINES_DISAGREE",
            f"MOTORLAR ÇELİŞİYOR — SymPy: {sym}, Z3: {z3v}. Genelde ince bir konu "
            f"(tanım kümesi/domain, bölme, kök dalı). İnsan gözü gerekir. "
            f"Z3 karşıörneği: {cx}.",
            details, _meta(t0))
    # yalnız bir motor karar verebildi
    if sym in decisive:
        status = "valid" if sym == "equal" else "invalid"
        return VerifyResult(status, "SINGLE_ENGINE",
                            f"yalnız SymPy karar verdi: {sym} (Z3: {z3v}). Tek-motor, "
                            f"çapraz doğrulama yok (güven daha düşük).", details, _meta(t0))
    if z3v in decisive:
        status = "valid" if z3v == "equal" else "invalid"
        return VerifyResult(status, "SINGLE_ENGINE",
                            f"yalnız Z3 karar verdi: {z3v} (SymPy: {sym}). Tek-motor, "
                            f"çapraz doğrulama yok (güven daha düşük).", details, _meta(t0))
    return VerifyResult("unknown", "CROSS_UNDECIDED",
                        f"hiçbir motor karar veremedi (SymPy: {sym}, Z3: {z3v}).",
                        details, _meta(t0))
