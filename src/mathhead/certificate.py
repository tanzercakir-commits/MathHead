"""
mathhead.certificate — BAĞIMSIZ SERTİFİKA DENETLEYİCİSİ (ROADMAP Track C2).

**Öne geçiren fikir:** "Bize güvenme, checker'ı kendin çalıştır." MathHead'in bir
sonucu (witness / karşıörnek / boyama), o sonucu ÜRETEN motordan (Z3/SymPy)
BAĞIMSIZ, küçük ve okunur bir denetleyiciyle yeniden doğrulanabilir olmalı.

Bu modül BİLEREK yalnız Python **standart kütüphanesini** kullanır — `z3` YOK,
`sympy` YOK (bu, `core`'un dışında durmasının ve `import` zincirinin sebebi;
`tests/test_certificate.py` bunu alt-süreçte kanıtlar). Aritmetik mümkün olduğunca
`fractions.Fraction` ile **tam** (exact) yapılır; transandantal fonksiyon girerse
`math` ile sayısal (float + tolerans) denetime düşülür ve bu dürüstçe belirtilir.

Sertifika türleri (kendi kendine yeten sözlükler):
- subset_sum        · {numbers, target, indices}
- graph_coloring    · {edges, colors, coloring}
- solution          · {expression, symbol, value}  (kalıntı 0 mı)
- not_equal         · {left, right, point}          (karşıörnek: left ≠ right)
- inequality_counterexample · {expression, point, relation}  (poli. o noktada ihlal)
"""
from __future__ import annotations

import ast
import math
import time
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

__all__ = ["CertificateResult", "check_certificate"]

_TOL = 1e-9

# ast Call -> stdlib fonksiyonu (transandantal → sayısal/float).
_FUNCS = {
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "exp": math.exp, "log": math.log, "sqrt": math.sqrt, "Abs": abs,
}


@dataclass
class CertificateResult:
    status: str                       # verified | refuted | error
    reason_code: str                  # CERTIFICATE_VALID | CERTIFICATE_INVALID | PARSE_ERROR
    explanation: str
    verified: bool = False
    exact: bool = True                # tam (Fraction) mı, sayısal (float) mı
    meta: dict[str, Any] = field(default_factory=dict)


class _CertError(ValueError):
    pass


def _num(value: Any) -> Any:
    """Girdiyi tam sayı/kesir (Fraction) ya da float'a çevirir."""
    if isinstance(value, bool):
        raise _CertError("boolean sayı değil")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return value
    s = str(value).strip()
    try:
        return Fraction(s)               # "3", "1/2", "-4" → tam
    except (ValueError, ZeroDivisionError):
        return float(s)                  # "0.5", "1e3" → float


def _eval(node: ast.AST, env: dict[str, Any]) -> Any:
    """ast ifadesini env altında değerlendirir. Fraction (tam) ya da float."""
    if isinstance(node, ast.BinOp):
        lft, rgt = _eval(node.left, env), _eval(node.right, env)
        op = node.op
        if isinstance(op, ast.Add):
            return lft + rgt
        if isinstance(op, ast.Sub):
            return lft - rgt
        if isinstance(op, ast.Mult):
            return lft * rgt
        if isinstance(op, ast.Div):
            if rgt == 0:
                raise _CertError("sıfıra bölme")
            return lft / rgt
        if isinstance(op, ast.Pow):
            if isinstance(lft, Fraction) and isinstance(rgt, Fraction) and rgt.denominator == 1:
                return lft ** int(rgt)          # tam üs → Fraction (exact)
            return float(lft) ** float(rgt)     # aksi halde float
        raise _CertError(f"izin verilmeyen işleç: {type(op).__name__}")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return _eval(node.operand, env)
        raise _CertError("izin verilmeyen tekli işleç")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise _CertError(f"izin verilmeyen fonksiyon: {node.func.id}")
        return float(fn(*[float(_eval(a, env)) for a in node.args]))
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise _CertError(f"tanımsız değişken: {node.id}")
        return env[node.id]
    if isinstance(node, ast.Constant):
        return _num(node.value)
    raise _CertError(f"izin verilmeyen ifade: {type(node).__name__}")


def _evaluate(expression: str, env: dict[str, Any]) -> Any:
    tree = ast.parse(str(expression).strip(), mode="eval")
    return _eval(tree.body, env)


def _is_zero(value: Any) -> tuple[bool, bool]:
    """(sıfır mı, tam mı). Fraction → tam eşitlik; float → tolerans."""
    if isinstance(value, Fraction):
        return value == 0, True
    return abs(float(value)) < _TOL, False


def _env(point: dict[str, Any]) -> dict[str, Any]:
    return {str(k): _num(v) for k, v in point.items()}


def _ok(msg: str, exact: bool = True) -> CertificateResult:
    return CertificateResult("verified", "CERTIFICATE_VALID", msg, True, exact)


def _no(msg: str, exact: bool = True) -> CertificateResult:
    return CertificateResult("refuted", "CERTIFICATE_INVALID", msg, False, exact)


def _bad(msg: str) -> CertificateResult:
    return CertificateResult("error", "PARSE_ERROR", msg, False, True)


def check_certificate(certificate: dict[str, Any]) -> CertificateResult:
    """Bir sertifikayı z3/sympy'den BAĞIMSIZ (yalnız stdlib) yeniden doğrular.

    verified → sertifika tutuyor; refuted → tutmuyor (sonuç YANLIŞ); error → biçim.
    """
    t0 = time.perf_counter()
    result = _check_impl(certificate)
    result.meta = {"engine": "stdlib-certificate",
                   "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}
    return result


def _check_impl(certificate: dict[str, Any]) -> CertificateResult:
    if not isinstance(certificate, dict):
        return _bad("sertifika bir sözlük olmalı")
    kind = certificate.get("kind")
    try:
        if kind == "subset_sum":
            nums = certificate["numbers"]
            target = certificate["target"]
            idx = certificate["indices"]
            if not all(isinstance(i, int) and 0 <= i < len(nums) for i in idx):
                return _bad("indices aralık dışı")
            total = sum(nums[i] for i in idx)
            return (_ok(f"seçilen alt küme toplamı {total} = hedef {target}.")
                    if total == target else
                    _no(f"toplam {total} ≠ hedef {target}."))

        if kind == "graph_coloring":
            edges = certificate["edges"]
            colors = certificate["colors"]
            coloring = {str(k): v for k, v in certificate["coloring"].items()}
            for u, v in edges:
                cu, cv = coloring.get(str(u)), coloring.get(str(v))
                if cu is None or cv is None:
                    return _bad(f"köşe {u} ya da {v} için renk yok")
                if not (0 <= cu < colors and 0 <= cv < colors):
                    return _no(f"renk aralık dışı ({u}:{cu}, {v}:{cv}, colors={colors}).")
                if cu == cv:
                    return _no(f"komşu {u}-{v} aynı renkte ({cu}) — geçersiz boyama.")
            return _ok(f"{len(edges)} kenarın hiçbirinde tek renk yok; boyama geçerli.")

        if kind == "solution":
            env = {str(certificate["symbol"]): _num(certificate["value"])}
            residual = _evaluate(certificate["expression"], env)
            zero, exact = _is_zero(residual)
            note = "" if exact else " (sayısal, tolerans)"
            return (_ok(f"kalıntı 0{note}: değer denklemi sağlıyor.", exact)
                    if zero else
                    _no(f"kalıntı {residual} ≠ 0{note}: değer çözüm değil.", exact))

        if kind == "not_equal":
            env = _env(certificate["point"])
            lv = _evaluate(certificate["left"], env)
            rv = _evaluate(certificate["right"], env)
            zero, exact = _is_zero(lv - rv)
            note = "" if exact else " (sayısal)"
            return (_no(f"noktada eşit çıktı ({lv} = {rv}){note}: karşıörnek GEÇERSİZ.", exact)
                    if zero else
                    _ok(f"noktada {lv} ≠ {rv}{note}: karşıörnek doğrulandı.", exact))

        if kind == "inequality_counterexample":
            env = _env(certificate["point"])
            val = _evaluate(certificate["expression"], env)
            rel = certificate.get("relation", ">=")
            fval = float(val)
            violated = fval < -_TOL if rel == ">=" else (
                fval > _TOL if rel == "<=" else None)
            if violated is None:
                return _bad(f"desteklenmeyen relation: {rel} (>= veya <=)")
            exact = isinstance(val, Fraction)
            note = "" if exact else " (sayısal)"
            return (_ok(f"ifade değeri {val}, '{rel} 0' İHLAL ediliyor{note}: "
                        f"karşıörnek doğrulandı.", exact)
                    if violated else
                    _no(f"ifade değeri {val}, '{rel} 0' ihlal edilmiyor{note}: "
                        f"karşıörnek geçersiz.", exact))

        return _bad(f"bilinmeyen sertifika türü: {kind!r}")
    except (KeyError, TypeError) as exc:
        return _bad(f"eksik/bozuk alan: {exc}")
    except _CertError as exc:
        return _bad(f"değerlendirme hatası: {exc}")
    except (ValueError, ZeroDivisionError) as exc:
        return _bad(f"sayısal hata: {exc}")
