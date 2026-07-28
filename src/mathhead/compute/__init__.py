"""
mathhead.compute — Sembolik hesap katmanı (CAS, SymPy tabanlı).

v2: `simplify`, `solve`, `differentiate`, `integrate`. Mantık çekirdeğinden
(Z3) AYRIDIR; buradaki amaç ispat değil **hesap**.

Güvenlik (PRINCIPLES: sessiz eval yok): girdi yine Python `ast` ile ayrıştırılıp
**beyaz liste** ile süzülür ve SymPy nesnesine çevrilir. `sympify`/`eval` gibi
güvensiz yollar KULLANILMAZ. Mantık katmanının aksine burada `*`/`**` (üs) ve
doğrusal olmayan ifadeler serbesttir (hesap için gerekli).

Dönüş sözleşmesi: `ComputeResult` (status ok|error, operation, result, ...).
Undecidability/başarısızlık dürüstçe raporlanır (ör. SymPy integrali
çözemezse değerlendirilmemiş `Integral(...)` döner — gizlenmez).
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import Any

import sympy

MAX_EXPRESSION_CHARS: int = 4_000

# İzinli fonksiyonlar (ast Call -> SymPy). Beyaz liste; gerisi reddedilir.
_FUNCS = {
    "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan,
    "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
    "exp": sympy.exp, "log": sympy.log, "sqrt": sympy.sqrt, "Abs": sympy.Abs,
}


class ComputeError(ValueError):
    """Girdi grameri/ifade ihlali. Net hata, sessiz varsayım yok."""


@dataclass
class ComputeResult:
    status: str                       # "ok" | "error"
    operation: str                    # simplify | solve | differentiate | integrate
    result: Any = None                # str veya list[str]
    explanation: str = ""
    reason_code: str = ""             # OK | PARSE_ERROR | COMPUTE_FAILED
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float) -> dict[str, Any]:
    return {
        "engine": "sympy",
        "sympy_version": sympy.__version__,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
    }


# --------------------------------------------------------------------------- #
# ast -> SymPy (beyaz liste)
# --------------------------------------------------------------------------- #
def _to_sympy(node: ast.AST, syms: dict[str, Any]) -> Any:
    if isinstance(node, ast.BinOp):
        left = _to_sympy(node.left, syms)
        right = _to_sympy(node.right, syms)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise ComputeError(f"desteklenmeyen operatör: {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        val = _to_sympy(node.operand, syms)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return val
        raise ComputeError(f"desteklenmeyen tekli operatör: {type(node.op).__name__}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ComputeError(f"izinli fonksiyonlar: {', '.join(sorted(_FUNCS))}")
        if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
            raise ComputeError("fonksiyon çağrısında keyword/yıldız argüman yok")
        return _FUNCS[node.func.id](*[_to_sympy(a, syms) for a in node.args])
    if isinstance(node, ast.Name):
        if node.id not in syms:
            syms[node.id] = sympy.Symbol(node.id)
        return syms[node.id]
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise ComputeError("boolean sabit hesapta geçersiz")
        if isinstance(node.value, int):
            return sympy.Integer(node.value)
        if isinstance(node.value, float):
            return sympy.Float(node.value)
        raise ComputeError(f"desteklenmeyen sabit: {node.value!r}")
    raise ComputeError(f"izin verilmeyen ifade düğümü: {type(node).__name__}")


def _parse(expression: str, syms: dict[str, Any]) -> Any:
    if not isinstance(expression, str) or not expression.strip():
        raise ComputeError("boş veya geçersiz ifade")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ComputeError(f"ifade çok uzun (>{MAX_EXPRESSION_CHARS} karakter)")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ComputeError(f"sözdizimi hatası: {exc.msg}") from exc
    body = tree.body
    if isinstance(body, ast.Compare):  # denklem: a == b
        if len(body.ops) == 1 and isinstance(body.ops[0], ast.Eq):
            return sympy.Eq(_to_sympy(body.left, syms), _to_sympy(body.comparators[0], syms))
        raise ComputeError("yalnızca tek '==' eşitliği desteklenir")
    return _to_sympy(body, syms)


def _symbol(name: str, syms: dict[str, Any]) -> Any:
    if not isinstance(name, str) or not name.isidentifier():
        raise ComputeError(f"geçersiz değişken adı: {name!r}")
    if name not in syms:
        syms[name] = sympy.Symbol(name)
    return syms[name]


def _error(operation: str, msg: str, t0: float, code: str = "PARSE_ERROR") -> ComputeResult:
    return ComputeResult("error", operation, None, msg, code, _meta(t0))


# --------------------------------------------------------------------------- #
# İşlemler
# --------------------------------------------------------------------------- #
def simplify(expression: str) -> ComputeResult:
    """Bir ifadeyi cebirsel olarak sadeleştirir."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
    except ComputeError as exc:
        return _error("simplify", str(exc), t0)
    try:
        result = sympy.simplify(expr)
    except Exception as exc:  # noqa: BLE001 - SymPy başarısızlığı dürüstçe raporlanır
        return _error("simplify", f"sadeleştirilemedi: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "simplify", str(result), f"'{expression}' sadeleştirildi.", "OK", _meta(t0))


def solve(equation: str, symbol: str) -> ComputeResult:
    """Bir denklemi (ör. 'x**2 == 4' veya '=0' varsayımıyla 'x**2 - 4') çözer."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        eq = _parse(equation, syms)
        var = _symbol(symbol, syms)
    except ComputeError as exc:
        return _error("solve", str(exc), t0)
    try:
        solutions = sympy.solve(eq, var, dict=False)
        result = [str(s) for s in solutions]
    except Exception as exc:  # noqa: BLE001
        return _error("solve", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "solve", result,
        f"'{symbol}' için {len(result)} çözüm bulundu.", "OK", _meta(t0),
    )


def differentiate(expression: str, symbol: str, order: int = 1) -> ComputeResult:
    """İfadenin `symbol`'e göre `order`. mertebeden türevini alır."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("türev mertebesi 1 veya daha büyük tam sayı olmalı")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
    except ComputeError as exc:
        return _error("differentiate", str(exc), t0)
    try:
        result = sympy.diff(expr, var, order)
    except Exception as exc:  # noqa: BLE001
        return _error("differentiate", f"türev alınamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "differentiate", str(result),
        f"d^{order}/d{symbol}^{order} ('{expression}') hesaplandı.", "OK", _meta(t0),
    )


def integrate(expression: str, symbol: str) -> ComputeResult:
    """İfadenin `symbol`'e göre belirsiz integralini alır (+C gösterilmez).

    SymPy integrali kapalı formda çözemezse değerlendirilmemiş `Integral(...)`
    döner — bu gizlenmez, dürüstçe result'a yansır.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
    except ComputeError as exc:
        return _error("integrate", str(exc), t0)
    try:
        result = sympy.integrate(expr, var)
    except Exception as exc:  # noqa: BLE001
        return _error("integrate", f"integral alınamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "integrate", str(result),
        f"∫ '{expression}' d{symbol} hesaplandı (+C).", "OK", _meta(t0),
    )


def _parse_point(point: str, syms: dict[str, Any]) -> Any:
    """Limit/seri noktası: sonsuzları (oo/inf) tanır, gerisini gramerle ayrıştırır."""
    p = point.strip().lower()
    if p in ("oo", "inf", "infinity", "+oo", "+inf"):
        return sympy.oo
    if p in ("-oo", "-inf", "-infinity"):
        return -sympy.oo
    return _parse(point, syms)


def limit(expression: str, symbol: str, point: str = "0", direction: str = "both") -> ComputeResult:
    """`symbol` -> `point` iken ifadenin limiti. direction: both / + / - (tek yön).

    `point` sonsuz olabilir: "oo" veya "-oo".
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    dir_map = {"both": "+-", "+": "+", "-": "-", "+-": "+-"}
    try:
        if direction not in dir_map:
            raise ComputeError("direction 'both', '+' veya '-' olmalı")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
    except ComputeError as exc:
        return _error("limit", str(exc), t0)
    try:
        result = sympy.limit(expr, var, pt, dir_map[direction])
    except Exception as exc:  # noqa: BLE001
        return _error("limit", f"limit hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "limit", str(result),
                         f"lim {symbol}→{point} '{expression}' = {result}.", "OK", _meta(t0))


def series(expression: str, symbol: str, point: str = "0", order: int = 6) -> ComputeResult:
    """İfadenin `symbol` = `point` etrafında `order`. mertebeden Taylor/seri açılımı."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("order 1 veya daha büyük tam sayı olmalı")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
    except ComputeError as exc:
        return _error("series", str(exc), t0)
    try:
        result = expr.series(var, pt, order).removeO()
    except Exception as exc:  # noqa: BLE001
        return _error("series", f"seri açılamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "series", str(result),
                         f"'{expression}' serisi ({symbol}={point}, {order}. mertebe).", "OK", _meta(t0))


def solve_system(equations: list[str], symbols: list[str]) -> ComputeResult:
    """Bir denklem SİSTEMİNİ birden çok değişken için çözer.

    Denklemler `a == b` (Eq) veya `=0` varsayımıyla düz ifade olabilir.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(equations, list) or not equations:
            raise ComputeError("denklem listesi boş olamaz")
        if not isinstance(symbols, list) or not symbols:
            raise ComputeError("değişken listesi boş olamaz")
        eqs = [_parse(e, syms) for e in equations]
        variables = [_symbol(s, syms) for s in symbols]
    except ComputeError as exc:
        return _error("solve_system", str(exc), t0)
    try:
        sols = sympy.solve(eqs, variables, dict=True)
        result = [{str(k): str(v) for k, v in sol.items()} for sol in sols]
    except Exception as exc:  # noqa: BLE001
        return _error("solve_system", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_system", result,
                         f"{len(result)} çözüm bulundu.", "OK", _meta(t0))
