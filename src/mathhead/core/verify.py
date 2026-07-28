"""
mathhead.core.verify — DOĞRULAMA KATMANI (AI muhakeme denetçisi).

**Öne geçiren fikir (ROADMAP Track C):** AI non-deterministiktir ve uydurur;
MathHead deterministik olarak DENETLER. Bu katman "öner-ve-denetle": bir AI (ya
da insan) matematiksel bir İDDİA sunar (bu ifade şuna denk / bu değerler çözüm /
bu adım zinciri doğru), MathHead bağımsız doğrular ve **karşıörnek + kanıt** verir.

Bu, ürünü "başka bir hesap makinesi" olmaktan çıkarıp AI muhakemesinin *yargıcı*
yapan farktır. Rakip CAS'lar cevap verir; biz cevabı DOĞRULARIZ.

Dürüstlük duvarları (bilerek yüzeye çıkarılır):
- **Domain tuzağı:** `(x²-1)/(x-1)` ile `x+1` sembolik denk görünür ama `x=1`'de
  tanımsızdır. Denklik "ortak tanım kümesinde" olarak nitelenir, ayrışma noktaları
  raporlanır (naif eşitlik kontrolünün KAÇIRDIĞI hata — bizim yakaladığımız).
- **Tamlık:** bir çözüm kümesinin TAM olduğunu her zaman doğrulayamayız (ör.
  transandantal denklem). Bu durum `unknown` olarak birinci sınıf raporlanır.

Güvenlik: girdi yine compute katmanının ast-whitelist ayrıştırıcısıyla süzülür.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any

import sympy

from mathhead.compute import (
    ComputeError,
    _meta,
    _parse,
    _parse_matrix,
    _parse_point,
    _symbol,
)

__all__ = [
    "verify_equality", "verify_solution", "verify_steps",
    "verify_limit", "verify_derivative", "verify_integral",
    "verify_series", "verify_matrix_identity",
]

_SAMPLE = (0, 1, 2, -1, 3, -2, 5)   # karşıörnek taraması için nokta kümesi


@dataclass
class VerifyResult:
    """Doğrulama çıktısı — ortak sözleşme (status/reason_code/explanation/meta)."""

    status: str                       # valid | invalid | unknown | error
    reason_code: str
    explanation: str
    details: dict[str, Any] | None = None    # karşıörnek / eksik-fazla / ilk hatalı adım
    meta: dict[str, Any] = field(default_factory=dict)


def _err(operation: str, msg: str, t0: float) -> VerifyResult:
    return VerifyResult("error", "PARSE_ERROR", f"{operation}: {msg}", None, _meta(t0))


def _as_expr(value: str, syms: dict[str, Any]) -> Any:
    """İfadeyi ayrıştırır; denklem (Eq) gelirse reddeder (burada ifade beklenir)."""
    parsed = _parse(value, syms)
    if isinstance(parsed, sympy.Equality):
        raise ComputeError("burada ifade beklenir, denklem değil")
    return parsed


def _counterexample(diff: Any, syms: dict[str, Any]) -> dict[str, Any] | None:
    """`diff` (= sol - sağ) sıfırdan farklı olan somut bir nokta bulur."""
    free = sorted(diff.free_symbols, key=str)
    if not free:
        val = sympy.simplify(diff)
        return None if val == 0 else {"value": str(val)}
    combos = itertools.product(_SAMPLE, repeat=len(free))
    for i, combo in enumerate(combos):
        if i > 400:                    # tarama sınırı (dürüst: kapsamlı değil)
            break
        subs = dict(zip(free, combo))
        try:
            val = sympy.simplify(diff.subs(subs))
        except Exception:              # noqa: BLE001
            continue
        if val.is_number and val != 0 and val.is_finite:
            point = {str(s): int(v) for s, v in subs.items()}
            return {"point": point, "difference": str(val)}
    return None


def _domain_diff(left: Any, right: Any) -> list[str]:
    """İki ifadenin tanım kümelerinin ayrıştığı (tekillik) noktaları toplar."""
    out: set[str] = set()
    for s in sorted(left.free_symbols | right.free_symbols, key=str):
        try:
            sl = sympy.singularities(left, s)
            sr = sympy.singularities(right, s)
        except Exception:              # noqa: BLE001
            continue
        for a, b in ((sl, sr), (sr, sl)):
            if getattr(a, "is_FiniteSet", False):
                for p in a:
                    try:
                        if not (getattr(b, "is_FiniteSet", False) and p in b):
                            out.add(f"{s}={p}")
                    except TypeError:
                        continue
    return sorted(out)


def _equal_verdict(le: Any, re: Any, syms: dict[str, Any]) -> tuple[str, dict | None]:
    """DETERMİNİSTİK denklik kararı: ('equal'|'not_equal'|'undecided', karşıörnek?).

    SymPy `.equals()` KULLANILMAZ — o içsel RASTGELE örnekleme yapar (aynı girdi →
    değişen sonuç), determinizm ilkesini (ADR-0019) ihlal ederdi. Bunun yerine:
    (1) `simplify(sol - sağ) == 0` → denk (deterministik), (2) sabit-nokta
    karşıörnek taraması → değilse `not_equal` + kanıt, (3) aksi halde `undecided`.
    """
    diff = le - re
    try:
        simplified = sympy.simplify(diff)
    except Exception:                        # noqa: BLE001
        simplified = diff
    if simplified == 0:
        return "equal", None
    cx = _counterexample(simplified, syms)
    if cx is not None:
        return "not_equal", cx
    return "undecided", None


def verify_equality(left: str, right: str) -> VerifyResult:
    """`left` ile `right` matematiksel olarak DENK mi? (AI'ın "= şuna eşittir"
    iddiasını denetler.)

    valid → denk; ayrıca tanım kümeleri ayrışıyorsa `EQUAL_ON_COMMON_DOMAIN` ile
    ayrışma noktaları raporlanır (domain tuzağı). invalid → `details.counterexample`
    farklı olduğu somut nokta. unknown → karar verilemedi (dürüst).
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        left_e = _as_expr(left, syms)
        right_e = _as_expr(right, syms)
    except ComputeError as exc:
        return _err("verify_equality", str(exc), t0)

    verdict, cx = _equal_verdict(left_e, right_e, syms)
    if verdict == "equal":
        caveat = _domain_diff(left_e, right_e)
        if caveat:
            return VerifyResult(
                "valid", "EQUAL_ON_COMMON_DOMAIN",
                f"ortak tanım kümesinde denk; ANCAK tanım kümeleri şurada ayrışıyor: "
                f"{', '.join(caveat)} (koşulsuz eşit DEĞİL).",
                {"domain_caveat": caveat}, _meta(t0))
        return VerifyResult("valid", "EQUAL", "ifadeler denk (doğrulandı).", None, _meta(t0))
    if verdict == "not_equal":
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"denk DEĞİL; karşıörnek: {cx}.", {"counterexample": cx}, _meta(t0))
    return VerifyResult("unknown", "UNDECIDED",
                        "denklik kararlaştırılamadı (dürüst: ne ispat ne çürütme).",
                        None, _meta(t0))


def verify_solution(equation: str, symbol: str, claimed: list[str]) -> VerifyResult:
    """`claimed` değerleri `equation`'ın çözümü mü — ve TAM mı? (AI'ın "çözümler
    şunlar" iddiasını denetler.)

    Her değer ikame ile denetlenir; ayrıca gerçek çözüm kümesiyle karşılaştırılıp
    EKSİK/FAZLA raporlanır. valid → doğru + tam; invalid → yanlış değer ya da eksik;
    unknown → değerler tutar ama TAMLIK doğrulanamadı (ör. transandantal).
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(claimed, list) or not claimed:
            raise ComputeError("iddia edilen çözüm listesi boş olamaz")
        parsed = _parse(equation, syms)
        expr = (parsed.lhs - parsed.rhs) if isinstance(parsed, sympy.Equality) else parsed
        var = _symbol(symbol, syms)
        claimed_vals = [_parse(c, syms) for c in claimed]
    except ComputeError as exc:
        return _err("verify_solution", str(exc), t0)

    checks = []
    for c in claimed_vals:
        try:
            residual = sympy.simplify(expr.subs(var, c))
            ok = bool(residual == 0)
        except Exception:                    # noqa: BLE001
            ok = False
        checks.append({"value": str(c), "satisfies": ok})
    wrong = [d["value"] for d in checks if not d["satisfies"]]

    # tamlık: gerçek çözüm kümesini bulmaya çalış
    actual = None
    try:
        actual = set(sympy.solve(expr, var))
    except (NotImplementedError, Exception):  # noqa: BLE001
        actual = None

    details: dict[str, Any] = {"checks": checks}
    if wrong:
        details["wrong_values"] = wrong
        return VerifyResult("invalid", "SOLUTION_INCORRECT",
                            f"şu iddia edilen değerler çözüm DEĞİL: {wrong}.",
                            details, _meta(t0))
    if actual is None:
        return VerifyResult("unknown", "COMPLETENESS_UNKNOWN",
                            "iddia edilen değerler çözüm; ANCAK tümü mü doğrulanamadı "
                            "(çözüm kümesi kapalı-formda bulunamadı).",
                            details, _meta(t0))
    claimed_set = set(claimed_vals)
    missing = sorted((actual - claimed_set), key=str)
    if missing:
        details["missing"] = [str(m) for m in missing]
        return VerifyResult("invalid", "SOLUTION_INCOMPLETE",
                            f"değerler doğru ama EKSİK; kaçan çözümler: "
                            f"{details['missing']}.", details, _meta(t0))
    return VerifyResult("valid", "SOLUTION_VERIFIED",
                        "iddia edilen çözümler doğru ve TAM (doğrulandı).",
                        details, _meta(t0))


def verify_steps(steps: list[str]) -> VerifyResult:
    """Bir ifade zincirini (her adım bir öncekiyle DENK olmalı) denetler ve İLK
    hatalı geçişi bulur. (AI'ın adım adım çözümünü "not verir".)

    valid → tüm geçişler denk; invalid → `details.first_bad_step` (1-tabanlı) ilk
    kırılan geçiş + karşıörnek; unknown → bir geçiş kararlaştırılamadı.
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(steps, list) or len(steps) < 2:
            raise ComputeError("en az 2 adım gerekir")
        exprs = [_as_expr(s, syms) for s in steps]
    except ComputeError as exc:
        return _err("verify_steps", str(exc), t0)

    undecided_at = None
    for i in range(len(exprs) - 1):
        verdict, cx = _equal_verdict(exprs[i], exprs[i + 1], syms)
        if verdict == "not_equal":
            return VerifyResult(
                "invalid", "STEP_INVALID",
                f"{i + 1}. adımdan {i + 2}. adıma geçiş HATALI "
                f"('{steps[i]}' ≠ '{steps[i + 1]}').",
                {"first_bad_step": i + 1, "from": steps[i], "to": steps[i + 1],
                 "counterexample": cx}, _meta(t0))
        if verdict == "undecided" and undecided_at is None:
            undecided_at = i + 1
    if undecided_at is not None:
        return VerifyResult("unknown", "UNDECIDED",
                            f"{undecided_at}. geçiş kararlaştırılamadı; gerisi tutarlı.",
                            {"undecided_step": undecided_at}, _meta(t0))
    return VerifyResult("valid", "STEPS_VALID",
                        f"{len(exprs)} adımın tüm geçişleri denk (doğrulandı).",
                        None, _meta(t0))


# --------------------------------------------------------------------------- #
# I1 — daha çok iddia türü: limit / türev / integral / seri / matris özdeşliği.
# Hepsi "AI'ın iddiası ≟ bağımsız hesaplanan doğru" — deterministik denklikle
# denetlenir (EQUAL/NOT_EQUAL/UNDECIDED). İntegral: türev-alıp-karşılaştır (dürüst).
# --------------------------------------------------------------------------- #
def _from_verdict(op: str, claimed: str, computed_desc: str,
                  le: Any, re: Any, syms: dict[str, Any], t0: float) -> VerifyResult:
    """`le` (iddia) ile `re` (hesaplanan) denk mi → ortak VerifyResult üretir."""
    verdict, cx = _equal_verdict(le, re, syms)
    if verdict == "equal":
        return VerifyResult("valid", "EQUAL",
                            f"{op}: iddia doğru (= {computed_desc}).", None, _meta(t0))
    if verdict == "not_equal":
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"{op}: iddia YANLIŞ. Doğrusu: {computed_desc}. Karşıörnek: {cx}.",
                            {"claimed": claimed, "correct": computed_desc, "counterexample": cx},
                            _meta(t0))
    return VerifyResult("unknown", "UNDECIDED",
                        f"{op}: kararlaştırılamadı (iddia: {claimed}, hesaplanan: {computed_desc}).",
                        None, _meta(t0))


def verify_derivative(expression: str, symbol: str, claimed: str,
                      order: int = 1) -> VerifyResult:
    """`d^order/d{symbol}^order (expression)` gerçekten `claimed` mı? (AI türev iddiası.)"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("türev mertebesi 1 veya daha büyük tam sayı olmalı")
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_derivative", str(exc), t0)
    try:
        computed = sympy.diff(expr, var, order)
    except Exception as exc:  # noqa: BLE001
        return _err("verify_derivative", f"türev alınamadı: {exc}", t0)
    return _from_verdict("türev", claimed, str(computed), claimed_e, computed, syms, t0)


def verify_integral(expression: str, symbol: str, claimed: str) -> VerifyResult:
    """`∫ expression d{symbol}` gerçekten `claimed` mı? (sabit farkı hoş görülür.)

    DÜRÜST yöntem: `claimed`'ın türevini alıp `expression`'a eşit mi bakılır
    (böylece +C belirsizliği doğal olarak aşılır).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_integral", str(exc), t0)
    try:
        d_claimed = sympy.diff(claimed_e, var)
    except Exception as exc:  # noqa: BLE001
        return _err("verify_integral", f"türev alınamadı: {exc}", t0)
    res = _from_verdict("integral", claimed, f"türevi {d_claimed}", d_claimed, expr, syms, t0)
    if res.status == "valid":
        res.explanation = (f"integral: iddia doğru — d/d{symbol}({claimed}) = {expr} "
                           f"(sabit farkı hoş görülür).")
    return res


def verify_limit(expression: str, symbol: str, point: str, claimed: str) -> VerifyResult:
    """`lim {symbol}→{point} expression` gerçekten `claimed` mı? (`point`/`claimed` `oo` olabilir.)"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
        claimed_v = _parse_point(str(claimed), syms)
    except ComputeError as exc:
        return _err("verify_limit", str(exc), t0)
    try:
        actual = sympy.limit(expr, var, pt)
    except Exception as exc:  # noqa: BLE001
        return VerifyResult("unknown", "UNDECIDED",
                            f"limit: bağımsız hesaplanamadı ({exc}).", None, _meta(t0))
    equal = False
    try:
        equal = bool(actual == claimed_v) or bool(sympy.simplify(actual - claimed_v) == 0)
    except Exception:  # noqa: BLE001
        equal = bool(actual == claimed_v)
    if equal:
        return VerifyResult("valid", "EQUAL",
                            f"limit: iddia doğru (lim {symbol}→{point} = {actual}).",
                            None, _meta(t0))
    return VerifyResult("invalid", "NOT_EQUAL",
                        f"limit: iddia YANLIŞ. Doğru limit: {actual} (iddia: {claimed}).",
                        {"claimed": str(claimed), "correct": str(actual)}, _meta(t0))


def verify_series(expression: str, symbol: str, point: str, order: int,
                  claimed: str) -> VerifyResult:
    """`expression`'ın `{symbol}={point}` civarı `order`. mertebe Taylor açılımı `claimed` mı?"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("order 1 veya daha büyük tam sayı olmalı")
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_series", str(exc), t0)
    try:
        computed = expr.series(var, pt, order).removeO()
    except Exception as exc:  # noqa: BLE001
        return _err("verify_series", f"seri açılamadı: {exc}", t0)
    return _from_verdict("seri", claimed, str(computed), claimed_e, computed, syms, t0)


def verify_matrix_identity(left: list[list[str]], right: list[list[str]]) -> VerifyResult:
    """İki matris (sembolik hücreler dahil) EŞİT mi? (AI matris özdeşliği iddiası.)

    Boyut farklıysa `NOT_EQUAL`; aksi halde her hücre deterministik denklikle
    denetlenir, ilk farklı hücre + karşıörnek raporlanır.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(left, syms)
        B = _parse_matrix(right, syms)
    except ComputeError as exc:
        return _err("verify_matrix_identity", str(exc), t0)
    if (A.rows, A.cols) != (B.rows, B.cols):
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"matris boyutları farklı: {A.rows}×{A.cols} ≠ {B.rows}×{B.cols}.",
                            {"left_shape": [A.rows, A.cols], "right_shape": [B.rows, B.cols]},
                            _meta(t0))
    undecided = None
    for i in range(A.rows):
        for j in range(A.cols):
            verdict, cx = _equal_verdict(A[i, j], B[i, j], syms)
            if verdict == "not_equal":
                return VerifyResult("invalid", "NOT_EQUAL",
                                    f"matrisler farklı: [{i}][{j}] hücresi eşit değil "
                                    f"({A[i, j]} ≠ {B[i, j]}).",
                                    {"cell": [i, j], "left": str(A[i, j]),
                                     "right": str(B[i, j]), "counterexample": cx}, _meta(t0))
            if verdict == "undecided" and undecided is None:
                undecided = [i, j]
    if undecided is not None:
        return VerifyResult("unknown", "UNDECIDED",
                            f"[{undecided[0]}][{undecided[1]}] hücresi kararlaştırılamadı; "
                            f"gerisi eşit.", {"undecided_cell": undecided}, _meta(t0))
    return VerifyResult("valid", "EQUAL",
                        f"matrisler eşit ({A.rows}×{A.cols}, tüm hücreler doğrulandı).",
                        None, _meta(t0))
