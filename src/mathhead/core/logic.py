"""
mathhead.core.logic
====================

Motorun KALBİ: bir SMT çözücü (Z3) üzerine kurulu, deterministik akıl yürütme
ilkelleri (reasoning primitives).

Neden Z3? -> DECISIONS.md ADR-0002. FOL + hazır teoriler (doğrusal tam sayı
aritmetiği, eşitlik...) için dünya standardı; deterministik ve kanıtlanmış.

Dönüş Sözleşmesi (erken donduruldu — ADR-0004):
    valid / invalid  -> entailment (mantıksal gerektirme) sorusu
    sat   / unsat    -> consistency (tutarlılık) sorusu
    unknown          -> çözücü karar veremedi (undecidability'e DÜRÜST yanıt)
    error            -> girdi/guardrail/parse hatası
    "unknown" ve "error" birinci sınıf çıktılardır; ASLA gizlenmez.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.translate import ParseError, translate_all
from mathhead.guardrails import GuardrailError, solver_config, validate_input

DEFAULT_TIMEOUT_MS: int = 5_000
DEFAULT_SEED: int = 42


@dataclass
class ReasoningResult:
    """Tüm akıl yürütme ilkellerinin ortak, makine + insan okunur çıktısı."""

    status: str                              # valid|invalid|sat|unsat|unknown|error
    reason_code: str                         # ENTAILED, COUNTEREXAMPLE_FOUND, ...
    explanation: str                         # insan-okur açıklama
    witness: dict[str, Any] | None = None    # model (sat) / karşıörnek (invalid) / unsat core
    meta: dict[str, Any] = field(default_factory=dict)

    def is_conclusive(self) -> bool:
        """Sonuç kesin mi? (unknown/error -> False)."""
        return self.status not in ("unknown", "error")


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #
def _meta(t0: float, seed: int, timeout_ms: int) -> dict[str, Any]:
    return {
        "engine": "z3",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


def _error(code: str, msg: str, t0: float, seed: int, timeout_ms: int) -> ReasoningResult:
    return ReasoningResult("error", code, msg, None, _meta(t0, seed, timeout_ms))


def _py_value(val: Any) -> Any:
    """Z3 değerini sade Python değerine indirger (JSON-dostu)."""
    if z3.is_true(val):
        return True
    if z3.is_false(val):
        return False
    if z3.is_int_value(val):
        return val.as_long()
    if z3.is_rational_value(val):
        return float(val.as_fraction())   # Real: kesirli değeri ondalığa çevir
    return str(val)                        # cebirsel/irrasyonel: tam metin gösterim


def _witness(model: z3.ModelRef, symbols: dict[str, Any]) -> dict[str, Any]:
    """Modeli, çekirdek değişkenler için okunur bir sözlüğe çevirir.

    `model_completion=True` -> "don't care" değişkenlere de somut değer atanır,
    böylece çıktı her zaman tam ve deterministik olur. İç izleme (__track_) hariç.
    """
    out: dict[str, Any] = {}
    for name, const in symbols.items():
        if name.startswith("__track_"):
            continue
        out[name] = _py_value(model.eval(const, model_completion=True))
    return dict(sorted(out.items()))


def _unknown(solver: z3.Solver, t0: float, seed: int, timeout_ms: int) -> ReasoningResult:
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ReasoningResult(
        "unknown", code, f"Çözücü karar veremedi ({reason}).",
        None, _meta(t0, seed, timeout_ms),
    )


def _prepare(statements: list[str], t0: float, seed: int, timeout_ms: int):
    """Ortak ön adım: guardrail + çeviri. (result, z3_list, symbols) döner;
    result doluysa (hata) çağıran erken döner."""
    try:
        validate_input(statements)
    except GuardrailError as exc:
        return _error("GUARDRAIL_VIOLATION", str(exc), t0, seed, timeout_ms), None, None
    try:
        z3_list, symbols = translate_all(statements)
    except ParseError as exc:
        return _error("PARSE_ERROR", str(exc), t0, seed, timeout_ms), None, None
    return None, z3_list, symbols


# --------------------------------------------------------------------------- #
# İlkeller
# --------------------------------------------------------------------------- #
def check_entailment(
    premises: list[str],
    conclusion: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """`premises ⊨ conclusion` mı? (öncüller sonucu mantıksal gerektirir mi).

    Yöntem: (⋀ premises) ∧ ¬conclusion UNSAT ise entailment VARDIR.
      * UNSAT -> valid
      * SAT   -> invalid (witness = karşıörnek)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    if not isinstance(premises, list) or not isinstance(conclusion, str):
        return _error("GUARDRAIL_VIOLATION", "premises liste, conclusion metin olmalı", t0, seed, timeout_ms)

    err, z3_list, symbols = _prepare([*premises, conclusion], t0, seed, timeout_ms)
    if err is not None:
        return err
    *prem_z, concl_z = z3_list

    solver = solver_config(timeout_ms, seed)
    for p in prem_z:
        solver.add(p)
    solver.add(z3.Not(concl_z))

    result = solver.check()
    if result == z3.unsat:
        return ReasoningResult(
            "valid", "ENTAILED",
            "Sonuç öncüllerden mantıksal olarak çıkar (öncüller ∧ ¬sonuç tatmin edilemez).",
            None, _meta(t0, seed, timeout_ms),
        )
    if result == z3.sat:
        return ReasoningResult(
            "invalid", "COUNTEREXAMPLE_FOUND",
            "Öncülleri sağlayıp sonucu çürüten bir karşıörnek bulundu.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)


def check_consistency(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """İfadeler kümesi TUTARLI mı (aynı anda doğru olabilir mi)?

    Yöntem: ⋀ statements SAT mı?
      * SAT   -> sat   (witness = örnek atama/model)
      * UNSAT -> unsat (witness = çelişen alt küme / unsat core)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return err

    solver = solver_config(timeout_ms, seed)
    # unsat core için her ifadeyi izleme literaliyle ekle (assert_and_track).
    trackers: dict[str, int] = {}
    for i, expr in enumerate(z3_list):
        lit_name = f"__track_{i}"
        trackers[lit_name] = i
        solver.assert_and_track(expr, z3.Bool(lit_name))

    result = solver.check()
    if result == z3.sat:
        return ReasoningResult(
            "sat", "CONSISTENT",
            "İfadeler tutarlı; hepsini aynı anda sağlayan bir atama var.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    if result == z3.unsat:
        core_idx = sorted(trackers[str(c)] for c in solver.unsat_core())
        return ReasoningResult(
            "unsat", "CONTRADICTION",
            "İfadeler çelişkili; işaretli alt küme aynı anda sağlanamaz.",
            {
                "unsat_core_indices": core_idx,
                "unsat_core": [statements[i] for i in core_idx],
            },
            _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)


def find_model(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """İfadeleri sağlayan SOMUT bir model (değişken ataması) bulur.

      * SAT   -> sat (witness = model)
      * UNSAT -> unsat (model yok)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return err

    solver = solver_config(timeout_ms, seed)
    for expr in z3_list:
        solver.add(expr)

    result = solver.check()
    if result == z3.sat:
        return ReasoningResult(
            "sat", "MODEL_FOUND",
            "İfadeleri sağlayan somut bir model bulundu.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_MODEL",
            "İfadeleri sağlayan hiçbir model yok (küme çelişkili).",
            None, _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)
