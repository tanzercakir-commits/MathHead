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

from mathhead.core.translate import ParseError, translate_all, translate_objective
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


@dataclass
class ModelSet:
    """`enumerate_models` çıktısı: bir formülü sağlayan (farklı) modeller kümesi."""

    status: str                              # sat|unsat|unknown|error
    reason_code: str
    explanation: str
    models: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    exhaustive: bool = False                 # True: TÜM modeller bulundu (unsat'a ulaşıldı)
    meta: dict[str, Any] = field(default_factory=dict)


def enumerate_models(
    statements: list[str],
    *,
    limit: int = 10,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ModelSet:
    """İfadeleri sağlayan FARKLI modelleri (en fazla `limit` tane) numaralandırır.

    Yöntem: çöz → modeli kaydet → o modeli **blokla** (farklı atama zorla) → tekrar.
    `unsat`'a ulaşılırsa küme tüketildi (`exhaustive=True`, tüm modeller bulundu);
    `limit`'e ulaşılırsa daha fazlası olabilir (sonsuz alanlarda — ör. sınırsız
    tam sayı/Real — bu beklenir, dürüstçe belirtilir).
    """
    t0 = time.perf_counter()
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        return ModelSet("error", "GUARDRAIL_VIOLATION", "limit 1..1000 tam sayı olmalı",
                        meta=_meta(t0, seed, timeout_ms))

    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return ModelSet(err.status, err.reason_code, err.explanation, meta=err.meta)

    solver = solver_config(timeout_ms, seed)
    for expr in z3_list:
        solver.add(expr)
    free = [const for name, const in symbols.items() if not name.startswith("__track_")]

    models: list[dict[str, Any]] = []
    while len(models) < limit:
        result = solver.check()
        if result == z3.unsat:
            if models:
                return ModelSet("sat", "ALL_MODELS_FOUND",
                                f"{len(models)} model bulundu — tümü (başka yok).",
                                models, len(models), True, _meta(t0, seed, timeout_ms))
            return ModelSet("unsat", "CONTRADICTION",
                            "İfadeler çelişkili; hiç model yok.",
                            [], 0, True, _meta(t0, seed, timeout_ms))
        if result != z3.sat:
            return ModelSet("unknown", "SOLVER_UNKNOWN",
                            f"Çözücü karar veremedi ({solver.reason_unknown()}); "
                            f"{len(models)} model bulunmuştu.",
                            models, len(models), False, _meta(t0, seed, timeout_ms))
        model = solver.model()
        models.append(_witness(model, symbols))
        if free:
            solver.add(z3.Or(*[c != model.eval(c, model_completion=True) for c in free]))
        else:  # serbest değişken yok (kapalı formül) -> en çok bir model
            solver.add(z3.BoolVal(False))

    return ModelSet("sat", "MODELS_FOUND",
                    f"{limit} model bulundu (sınıra ulaşıldı; daha fazlası olabilir).",
                    models, limit, False, _meta(t0, seed, timeout_ms))


@dataclass
class OptimizeResult:
    """`optimize` çıktısı: kısıtlar altında bir amacı en iyileyen çözüm."""

    status: str                              # optimal|unbounded|unsat|unknown|error
    reason_code: str
    explanation: str
    objective_value: Any = None              # optimal amaç değeri
    sense: str = ""                          # "max" | "min"
    witness: dict[str, Any] | None = None    # optimumu sağlayan atama
    meta: dict[str, Any] = field(default_factory=dict)


def _opt_value(val: Any) -> Any:
    try:
        if z3.is_int_value(val):
            return val.as_long()
        if z3.is_rational_value(val):
            return float(val.as_fraction())
    except Exception:  # noqa: BLE001
        pass
    return None


def optimize(
    constraints: list[str],
    objective: str,
    sense: str = "max",
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> OptimizeResult:
    """Kısıtları sağlayıp `objective` sayısal amacını en büyük/küçük yapan çözümü bul.

    sense: "max"/"maximize" veya "min"/"minimize". Z3 Optimize (optimization
    modulo theories) çekirdeği. `unbounded` (sınırsız), `unsat` (uygun çözüm yok),
    `unknown` durumları dürüstçe raporlanır.
    """
    t0 = time.perf_counter()
    s = sense.lower()
    if s in ("max", "maximize"):
        is_max = True
    elif s in ("min", "minimize"):
        is_max = False
    else:
        return OptimizeResult("error", "GUARDRAIL_VIOLATION",
                              "sense 'max' veya 'min' olmalı", meta=_meta(t0, seed, timeout_ms))
    if not isinstance(objective, str) or not objective.strip():
        return OptimizeResult("error", "GUARDRAIL_VIOLATION",
                              "amaç (objective) boş olamaz", meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input(constraints)
    except GuardrailError as exc:
        return OptimizeResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))
    try:
        c_z3, o_z3, symbols = translate_objective(constraints, objective)
    except ParseError as exc:
        return OptimizeResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    opt = z3.Optimize()
    try:
        opt.set("timeout", int(timeout_ms))
    except Exception:  # noqa: BLE001
        pass
    for c in c_z3:
        opt.add(c)
    handle = opt.maximize(o_z3) if is_max else opt.minimize(o_z3)
    sense_str = "max" if is_max else "min"

    result = opt.check()
    if result == z3.unsat:
        return OptimizeResult("unsat", "INFEASIBLE",
                              "Kısıtlar birlikte sağlanamıyor; uygun çözüm yok.",
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))
    if result != z3.sat:
        return OptimizeResult("unknown", "SOLVER_UNKNOWN",
                              f"Çözücü karar veremedi ({opt.reason_unknown()}).",
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))

    value = handle.value()
    py = _opt_value(value)
    if py is None:
        text = str(value)
        if "oo" in text or "*oo" in text:
            return OptimizeResult("unbounded", "UNBOUNDED",
                                  f"Amaç {'üstten' if is_max else 'alttan'} sınırsız (optimum yok).",
                                  sense=sense_str, meta=_meta(t0, seed, timeout_ms))
        return OptimizeResult("optimal", "OPEN_BOUND",
                              f"En iyi değer {'supremum' if is_max else 'infimum'} = {text} "
                              f"(açık sınır; tam ulaşılamaz).",
                              objective_value=text, witness=_witness(opt.model(), symbols),
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))
    return OptimizeResult("optimal", "OPTIMAL",
                          f"En iyi ({sense_str}) '{objective}' = {py}.",
                          objective_value=py, witness=_witness(opt.model(), symbols),
                          sense=sense_str, meta=_meta(t0, seed, timeout_ms))


@dataclass
class MaxSatResult:
    """`max_satisfy` çıktısı: zorunlu kısıtları sağlayıp EN ÇOK (ağırlıklı) yumuşak
    kısıtı sağlayan çözüm (MaxSAT)."""

    status: str                              # optimal|unsat|unknown|error
    reason_code: str
    explanation: str
    satisfied: list[int] = field(default_factory=list)     # sağlanan soft indeksleri
    unsatisfied: list[int] = field(default_factory=list)   # sağlanamayan soft indeksleri
    satisfied_weight: Any = 0
    total_weight: Any = 0
    witness: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def max_satisfy(
    hard: list[str],
    soft: list[str],
    weights: list[int] | None = None,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> MaxSatResult:
    """Zorunlu (`hard`) kısıtları sağlayıp EN ÇOK (ağırlıklı) `soft` kısıtı sağla.

    Aşırı-kısıtlı/çelişen isteklerde "hepsini değil, en iyisini" bulur (MaxSAT).
    `weights` verilmezse her soft kısıt 1 ağırlıkta. `hard` sağlanamıyorsa `unsat`.
    """
    t0 = time.perf_counter()
    if not isinstance(hard, list) or not isinstance(soft, list) or len(soft) == 0:
        return MaxSatResult("error", "GUARDRAIL_VIOLATION",
                            "hard liste, soft en az bir öğeli liste olmalı",
                            meta=_meta(t0, seed, timeout_ms))
    if weights is None:
        weights = [1] * len(soft)
    elif (not isinstance(weights, list) or len(weights) != len(soft)
          or not all(isinstance(w, int) and w > 0 for w in weights)):
        return MaxSatResult("error", "GUARDRAIL_VIOLATION",
                            "weights, soft ile aynı uzunlukta pozitif tam sayılar olmalı",
                            meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input([*hard, *soft])
    except GuardrailError as exc:
        return MaxSatResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))
    try:
        z3_list, symbols = translate_all([*hard, *soft])
    except ParseError as exc:
        return MaxSatResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    hard_z, soft_z = z3_list[:len(hard)], z3_list[len(hard):]
    opt = z3.Optimize()
    try:
        opt.set("timeout", int(timeout_ms))
    except Exception:  # noqa: BLE001
        pass
    for h in hard_z:
        opt.add(h)
    for expr, weight in zip(soft_z, weights):
        opt.add_soft(expr, weight)

    result = opt.check()
    if result == z3.unsat:
        return MaxSatResult("unsat", "HARD_INFEASIBLE",
                            "Zorunlu (hard) kısıtlar birlikte sağlanamıyor; çözüm yok.",
                            total_weight=sum(weights), meta=_meta(t0, seed, timeout_ms))
    if result != z3.sat:
        return MaxSatResult("unknown", "SOLVER_UNKNOWN",
                            f"Çözücü karar veremedi ({opt.reason_unknown()}).",
                            total_weight=sum(weights), meta=_meta(t0, seed, timeout_ms))

    model = opt.model()
    satisfied = [i for i, expr in enumerate(soft_z)
                 if z3.is_true(model.eval(expr, model_completion=True))]
    sat_set = set(satisfied)
    unsatisfied = [i for i in range(len(soft)) if i not in sat_set]
    sat_w = sum(weights[i] for i in satisfied)
    total_w = sum(weights)
    return MaxSatResult(
        "optimal", "OPTIMAL",
        f"{len(satisfied)}/{len(soft)} yumuşak kısıt sağlandı (ağırlık {sat_w}/{total_w}).",
        satisfied, unsatisfied, sat_w, total_w, _witness(model, symbols),
        _meta(t0, seed, timeout_ms),
    )
