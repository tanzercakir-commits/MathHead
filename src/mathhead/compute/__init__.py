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


# --------------------------------------------------------------------------- #
# Lineer cebir (matris) — SymPy Matrix. Girdi: list[list[str]], her hücre
# yine ast-whitelist ile süzülür (sembolik hücre serbest: [["a","b"],["c","d"]]).
# --------------------------------------------------------------------------- #
def _parse_matrix(matrix: list[list[str]], syms: dict[str, Any]) -> Any:
    """list[list[str]] -> sympy.Matrix. Dikdörtgen + boş-değil doğrulanır."""
    if not isinstance(matrix, list) or not matrix:
        raise ComputeError("matris boş olamaz")
    rows = []
    width: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise ComputeError("her satır boş olmayan bir liste olmalı")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ComputeError("tüm satırlar aynı uzunlukta olmalı (dikdörtgen)")
        rows.append([_parse(str(cell), syms) for cell in row])
    return sympy.Matrix(rows)


def determinant(matrix: list[list[str]]) -> ComputeResult:
    """Kare bir matrisin determinantı (sembolik hücreler serbest)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("determinant için kare matris gerekir")
    except ComputeError as exc:
        return _error("determinant", str(exc), t0)
    try:
        result = sympy.simplify(M.det())
    except Exception as exc:  # noqa: BLE001
        return _error("determinant", f"determinant hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "determinant", str(result),
                         f"det = {result}.", "OK", _meta(t0))


def matrix_inverse(matrix: list[list[str]]) -> ComputeResult:
    """Kare bir matrisin tersi (A⁻¹). Tekil (det=0) ise DÜRÜSTÇE hata döner."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("ters için kare matris gerekir")
    except ComputeError as exc:
        return _error("matrix_inverse", str(exc), t0)
    try:
        det = sympy.simplify(M.det())
        if det == 0:
            return _error("matrix_inverse",
                          "matris tersinir değil (tekil/singular, det = 0)",
                          t0, "COMPUTE_FAILED")
        inv = M.inv()
        result = [[str(sympy.simplify(inv[i, j])) for j in range(inv.cols)]
                  for i in range(inv.rows)]
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_inverse", f"ters alınamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_inverse", result,
                         "A⁻¹ hesaplandı.", "OK", _meta(t0))


def eigenvalues(matrix: list[list[str]]) -> ComputeResult:
    """Kare bir matrisin özdeğerleri (eigenvalue) + cebirsel katlılık (multiplicity).

    Dönüş: `[{"value": ..., "multiplicity": n}, ...]` — str'e göre sıralı
    (determinizm; ADR-0019). Karmaşık/irrasyonel değerler tam formda döner.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("özdeğer için kare matris gerekir")
    except ComputeError as exc:
        return _error("eigenvalues", str(exc), t0)
    try:
        ev = M.eigenvals()  # {değer: katlılık}
        result = sorted(
            ({"value": str(val), "multiplicity": int(mult)} for val, mult in ev.items()),
            key=lambda d: d["value"],
        )
    except Exception as exc:  # noqa: BLE001
        return _error("eigenvalues", f"özdeğerler hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "eigenvalues", result,
                         f"{len(result)} farklı özdeğer.", "OK", _meta(t0))


def matrix_rank(matrix: list[list[str]]) -> ComputeResult:
    """Bir matrisin rankı (doğrusal bağımsız satır/sütun sayısı). Kare olması şart değil."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("matrix_rank", str(exc), t0)
    try:
        result = int(M.rank())
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_rank", f"rank hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_rank", result,
                         f"rank = {result} ({M.rows}×{M.cols} matris).", "OK", _meta(t0))


def _mat_out(M: Any) -> list[list[str]]:
    """SymPy Matrix -> list[list[str]] (hücreler sadeleştirilmiş)."""
    return [[str(sympy.simplify(M[i, j])) for j in range(M.cols)] for i in range(M.rows)]


def matrix_multiply(a: list[list[str]], b: list[list[str]]) -> ComputeResult:
    """İki matrisin çarpımı A·B. İç boyutlar uyumsuzsa DÜRÜSTÇE hata."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(a, syms)
        B = _parse_matrix(b, syms)
        if A.cols != B.rows:
            raise ComputeError(
                f"boyut uyumsuz: A {A.rows}×{A.cols} · B {B.rows}×{B.cols} "
                f"(A sütun = B satır olmalı)"
            )
    except ComputeError as exc:
        return _error("matrix_multiply", str(exc), t0)
    try:
        result = _mat_out(A * B)
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_multiply", f"çarpılamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_multiply", result,
                         f"A·B = {A.rows}×{B.cols} matris.", "OK", _meta(t0))


def matrix_solve(matrix: list[list[str]], rhs: list[str]) -> ComputeResult:
    """`A x = b` doğrusal sistemini matris formunda çözer.

    Dönüş: çözüm sözlükleri listesi (`x0, x1, ...`). Boş liste = **çözüm yok**
    (tutarsız); serbest değişken parametrik görünür (dürüst).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(matrix, syms)
        if not isinstance(rhs, list) or not rhs:
            raise ComputeError("sağ taraf (b) boş olamaz")
        if len(rhs) != A.rows:
            raise ComputeError(
                f"b uzunluğu A'nın satır sayısına eşit olmalı (A {A.rows}×{A.cols}, b {len(rhs)})"
            )
        bvec = sympy.Matrix([_parse(str(x), syms) for x in rhs])
    except ComputeError as exc:
        return _error("matrix_solve", str(exc), t0)
    try:
        xs = list(sympy.symbols(f"x0:{A.cols}"))
        sol = sympy.linsolve((A, bvec), *xs)
        tuples = list(sol)
        result = [{str(xs[i]): str(tup[i]) for i in range(len(xs))} for tup in tuples]
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_solve", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    if not result:
        return ComputeResult("ok", "matrix_solve", [],
                             "çözüm yok (tutarsız sistem).", "OK", _meta(t0))
    free = sorted({str(s) for tup in tuples for expr in tup for s in expr.free_symbols})
    note = f" (serbest: {', '.join(free)} → parametrik)" if free else ""
    return ComputeResult("ok", "matrix_solve", result,
                         f"çözüm bulundu{note}.", "OK", _meta(t0))


def eigenvectors(matrix: list[list[str]]) -> ComputeResult:
    """Özdeğer + cebirsel katlılık + özvektör(ler). Özdeğere göre sıralı (determinizm)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("özvektör için kare matris gerekir")
    except ComputeError as exc:
        return _error("eigenvectors", str(exc), t0)
    try:
        data = M.eigenvects()  # [(özdeğer, katlılık, [sütun vektör(ler)])]
        result = [
            {
                "eigenvalue": str(val),
                "multiplicity": int(mult),
                "vectors": [[str(vec[i]) for i in range(vec.rows)] for vec in vecs],
            }
            for val, mult, vecs in data
        ]
        result.sort(key=lambda d: d["eigenvalue"])
    except Exception as exc:  # noqa: BLE001
        return _error("eigenvectors", f"özvektörler hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "eigenvectors", result,
                         f"{len(result)} farklı özdeğer için özvektörler.", "OK", _meta(t0))


def rref(matrix: list[list[str]]) -> ComputeResult:
    """İndirgenmiş satır eşelon form (reduced row echelon form) + pivot sütunları."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("rref", str(exc), t0)
    try:
        R, pivots = M.rref()
        result = {"rref": _mat_out(R), "pivots": [int(p) for p in pivots]}
    except Exception as exc:  # noqa: BLE001
        return _error("rref", f"rref hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "rref", result,
                         f"pivot sütunları: {result['pivots']}.", "OK", _meta(t0))


def nullspace(matrix: list[list[str]]) -> ComputeResult:
    """Boş uzayın (null space / kernel) bir tabanı. Boş liste = yalnız sıfır (trivial)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("nullspace", str(exc), t0)
    try:
        ns = M.nullspace()
        result = [[str(vec[i]) for i in range(vec.rows)] for vec in ns]
    except Exception as exc:  # noqa: BLE001
        return _error("nullspace", f"boş uzay hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    note = "yalnızca sıfır vektörü (trivial)" if not result else f"{len(result)} temel vektör"
    return ComputeResult("ok", "nullspace", result, f"boş uzay: {note}.", "OK", _meta(t0))


def lu_decomposition(matrix: list[list[str]]) -> ComputeResult:
    """LU ayrıştırma: A = P·L·U. Dönüş: `L`, `U` matrisleri + `perm` (satır takasları)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("LU için kare matris gerekir")
    except ComputeError as exc:
        return _error("lu_decomposition", str(exc), t0)
    try:
        L, U, perm = M.LUdecomposition()
        result = {"L": _mat_out(L), "U": _mat_out(U), "perm": [list(p) for p in perm]}
    except Exception as exc:  # noqa: BLE001
        return _error("lu_decomposition", f"LU ayrıştırılamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "lu_decomposition", result,
                         "A = P·L·U ayrıştırması.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Sayı teorisi (number theory) — TAM SAYILAR üzerinde. Girdi yine ast-whitelist
# ile süzülür (ör. "2**10" serbest); sonuç tam sayı değilse reddedilir.
# --------------------------------------------------------------------------- #
def _parse_int(value: Any, name: str = "değer") -> int:
    """Girdiyi güvenle tam sayıya çevirir. Sembol / tam-olmayan reddedilir."""
    syms: dict[str, Any] = {}
    expr = _parse(str(value), syms)
    if syms:
        raise ComputeError(f"{name} tam sayı olmalı (sembol içeremez)")
    val = sympy.simplify(expr)
    if not getattr(val, "is_Integer", False):
        raise ComputeError(f"{name} tam sayı olmalı")
    return int(val)


def gcd(a: Any, b: Any) -> ComputeResult:
    """İki tam sayının en büyük ortak böleni (greatest common divisor)."""
    t0 = time.perf_counter()
    try:
        A, B = _parse_int(a, "a"), _parse_int(b, "b")
    except ComputeError as exc:
        return _error("gcd", str(exc), t0)
    result = int(sympy.igcd(A, B))
    return ComputeResult("ok", "gcd", result, f"gcd({A}, {B}) = {result}.", "OK", _meta(t0))


def lcm(a: Any, b: Any) -> ComputeResult:
    """İki tam sayının en küçük ortak katı (least common multiple)."""
    t0 = time.perf_counter()
    try:
        A, B = _parse_int(a, "a"), _parse_int(b, "b")
    except ComputeError as exc:
        return _error("lcm", str(exc), t0)
    result = int(sympy.ilcm(A, B))
    return ComputeResult("ok", "lcm", result, f"lcm({A}, {B}) = {result}.", "OK", _meta(t0))


def is_prime(n: Any) -> ComputeResult:
    """`n` asal mı? (deterministik asallık testi — SymPy `isprime`)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
    except ComputeError as exc:
        return _error("is_prime", str(exc), t0)
    result = bool(sympy.isprime(N))
    return ComputeResult("ok", "is_prime", result,
                         f"{N} {'asaldır' if result else 'asal değildir'}.", "OK", _meta(t0))


def factorize(n: Any) -> ComputeResult:
    """`n`'i asal çarpanlarına ayırır. Dönüş: `[{prime, exponent}, ...]` (artan)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 1:
            raise ComputeError("pozitif tam sayı gerekir (n ≥ 1)")
    except ComputeError as exc:
        return _error("factorize", str(exc), t0)
    try:
        fac = sympy.factorint(N)
        result = [{"prime": int(p), "exponent": int(e)} for p, e in sorted(fac.items())]
    except Exception as exc:  # noqa: BLE001
        return _error("factorize", f"çarpanlara ayrılamadı: {exc}", t0, "COMPUTE_FAILED")
    pretty = " · ".join(f"{d['prime']}^{d['exponent']}" if d["exponent"] > 1 else str(d["prime"])
                        for d in result) or "1 (asal çarpan yok)"
    return ComputeResult("ok", "factorize", result, f"{N} = {pretty}.", "OK", _meta(t0))


def modular_inverse(a: Any, m: Any) -> ComputeResult:
    """`a`'nın `m` modülünde çarpımsal tersi. Yoksa (gcd(a,m)≠1) DÜRÜSTÇE hata."""
    t0 = time.perf_counter()
    try:
        A, M = _parse_int(a, "a"), _parse_int(m, "m")
        if M < 2:
            raise ComputeError("modül m ≥ 2 olmalı")
    except ComputeError as exc:
        return _error("modular_inverse", str(exc), t0)
    try:
        result = int(sympy.mod_inverse(A, M))
    except ValueError:
        return _error("modular_inverse",
                      f"{A}'nın mod {M} tersi yok (gcd(a, m) ≠ 1)", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "modular_inverse", result,
                         f"{A}⁻¹ ≡ {result} (mod {M}).", "OK", _meta(t0))


def chinese_remainder(moduli: list[Any], residues: list[Any]) -> ComputeResult:
    """Çin Kalan Teoremi (CRT): x ≡ residues[i] (mod moduli[i]) sistemini çözer.

    Dönüş: `{"x": ..., "modulus": ...}` (en küçük negatif-olmayan çözüm + bileşik
    modül). Sistem çözümsüzse (moduller bağdaşmaz) DÜRÜSTÇE hata.
    """
    t0 = time.perf_counter()
    try:
        if not isinstance(moduli, list) or not isinstance(residues, list):
            raise ComputeError("moduli ve residues liste olmalı")
        if len(moduli) != len(residues) or not moduli:
            raise ComputeError("moduli ve residues eşit ve boş olmayan uzunlukta olmalı")
        mods = [_parse_int(x, "modül") for x in moduli]
        res = [_parse_int(x, "kalan") for x in residues]
    except ComputeError as exc:
        return _error("chinese_remainder", str(exc), t0)
    from sympy.ntheory.modular import crt as _crt
    out = _crt(mods, res)
    if out is None:
        return _error("chinese_remainder",
                      "çözüm yok (moduller bağdaşmıyor)", t0, "COMPUTE_FAILED")
    x, mod = int(out[0]), int(out[1])
    return ComputeResult("ok", "chinese_remainder", {"x": x, "modulus": mod},
                         f"x ≡ {x} (mod {mod}).", "OK", _meta(t0))


def linear_diophantine(a: Any, b: Any, c: Any) -> ComputeResult:
    """Doğrusal Diophantine denklemi `a·x + b·y = c`'yi TAM SAYILARDA çözer.

    Dönüş: parametrik çözüm(ler) `[{"x": ..., "y": ...}]` (parametre `t_0`).
    Boş liste = tam sayı çözüm yok (gcd(a,b) ∤ c) — dürüst.
    """
    t0 = time.perf_counter()
    try:
        A, B, C = _parse_int(a, "a"), _parse_int(b, "b"), _parse_int(c, "c")
        if A == 0 and B == 0:
            raise ComputeError("a ve b aynı anda 0 olamaz")
    except ComputeError as exc:
        return _error("linear_diophantine", str(exc), t0)
    try:
        x, y = sympy.symbols("x y")
        sols = sympy.diophantine(A * x + B * y - C)
        result = [{"x": str(t[0]), "y": str(t[1])} for t in sols]
    except Exception as exc:  # noqa: BLE001
        return _error("linear_diophantine", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    if not result:
        return ComputeResult("ok", "linear_diophantine", [],
                             f"tam sayı çözüm yok (gcd({A},{B}) ∤ {C}).", "OK", _meta(t0))
    return ComputeResult("ok", "linear_diophantine", result,
                         f"{A}x + {B}y = {C} parametrik çözüm.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Kombinatorik & ayrık (combinatorics) — permütasyon/kombinasyon, faktöriyel,
# tam sayı bölüntüleri, doğrusal özyineleme (recurrence) kapalı-form çözümü.
# --------------------------------------------------------------------------- #
def permutations(n: Any, k: Any) -> ComputeResult:
    """P(n, k) = n·(n-1)···(n-k+1) — `n` nesneden `k`'lı sıralı seçim."""
    t0 = time.perf_counter()
    try:
        N, K = _parse_int(n, "n"), _parse_int(k, "k")
        if N < 0 or K < 0:
            raise ComputeError("n ve k negatif olamaz")
    except ComputeError as exc:
        return _error("permutations", str(exc), t0)
    result = int(sympy.ff(N, K))
    return ComputeResult("ok", "permutations", result, f"P({N}, {K}) = {result}.", "OK", _meta(t0))


def combinations(n: Any, k: Any) -> ComputeResult:
    """C(n, k) = binom(n, k) — `n` nesneden `k`'lı sırasız seçim. k>n ise 0."""
    t0 = time.perf_counter()
    try:
        N, K = _parse_int(n, "n"), _parse_int(k, "k")
        if N < 0 or K < 0:
            raise ComputeError("n ve k negatif olamaz")
    except ComputeError as exc:
        return _error("combinations", str(exc), t0)
    result = int(sympy.binomial(N, K))
    return ComputeResult("ok", "combinations", result, f"C({N}, {K}) = {result}.", "OK", _meta(t0))


def factorial(n: Any) -> ComputeResult:
    """n! — ilk `n` pozitif tam sayının çarpımı (0! = 1)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 0:
            raise ComputeError("n negatif olamaz (faktöriyel tanımsız)")
    except ComputeError as exc:
        return _error("factorial", str(exc), t0)
    result = int(sympy.factorial(N))
    return ComputeResult("ok", "factorial", result, f"{N}! = {result}.", "OK", _meta(t0))


def partition_count(n: Any) -> ComputeResult:
    """p(n) — `n`'i pozitif tam sayı toplamı olarak yazma yollarının sayısı."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 0:
            raise ComputeError("n negatif olamaz")
    except ComputeError as exc:
        return _error("partition_count", str(exc), t0)
    from sympy.functions.combinatorial.numbers import partition as _partition
    result = int(_partition(N))
    return ComputeResult("ok", "partition_count", result,
                         f"p({N}) = {result} (bölüntü sayısı).", "OK", _meta(t0))


def solve_recurrence(recurrence: str, func: str = "y", var: str = "n",
                     initial: dict[str, Any] | None = None) -> ComputeResult:
    """Doğrusal özyineleme bağıntısını KAPALI FORMA çözer (`rsolve`).

    Ör: `recurrence="y(n) = y(n-1) + y(n-2)"`, `initial={"0":"0","1":"1"}` →
    Fibonacci'nin kapalı formu (Binet). Kapalı form yoksa DÜRÜSTÇE hata.
    """
    t0 = time.perf_counter()
    initial = initial or {}
    F = sympy.Function(func)
    varsym = sympy.Symbol(var, integer=True)

    def _tr(node: ast.AST) -> Any:
        if isinstance(node, ast.BinOp):
            lft, rgt = _tr(node.left), _tr(node.right)
            for typ, fn in (
                (ast.Add, lambda: lft + rgt), (ast.Sub, lambda: lft - rgt),
                (ast.Mult, lambda: lft * rgt), (ast.Div, lambda: lft / rgt),
                (ast.Pow, lambda: lft ** rgt),
            ):
                if isinstance(node.op, typ):
                    return fn()
            raise ComputeError("izin verilmeyen işleç")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_tr(node.operand)
            if isinstance(node.op, ast.UAdd):
                return _tr(node.operand)
            raise ComputeError("izin verilmeyen tekli işleç")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func:
                if len(node.args) != 1:
                    raise ComputeError("özyineleme fonksiyonu tek argüman alır")
                return F(_tr(node.args[0]))
            if node.func.id in _FUNCS:
                return _FUNCS[node.func.id](*[_tr(a) for a in node.args])
            raise ComputeError(f"izin verilmeyen çağrı: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id == var:
                return varsym
            raise ComputeError(f"izin verilmeyen ad: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
        raise ComputeError("ifade ayrıştırılamadı")

    try:
        src = str(recurrence).strip()
        if "=" in src and "==" not in src:      # atama-tarzı '=' -> '==' (eval modu için)
            src = src.replace("=", "==", 1)
        body = ast.parse(src, mode="eval").body
        if isinstance(body, ast.Compare):
            if len(body.ops) != 1 or not isinstance(body.ops[0], ast.Eq):
                raise ComputeError("yalnızca '==' karşılaştırması desteklenir")
            expr = _tr(body.left) - _tr(body.comparators[0])
        else:
            expr = _tr(body)
        inits = {F(int(str(kk))): _parse(str(vv), {}) for kk, vv in initial.items()}
    except ComputeError as exc:
        return _error("solve_recurrence", str(exc), t0)
    except (SyntaxError, ValueError) as exc:
        return _error("solve_recurrence", f"ayrıştırılamadı: {exc}", t0)
    try:
        sol = sympy.rsolve(expr, F(varsym), inits)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_recurrence", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    if sol is None:
        return _error("solve_recurrence", "kapalı form bulunamadı", t0, "COMPUTE_FAILED")
    result = str(sympy.simplify(sol))
    return ComputeResult("ok", "solve_recurrence", result,
                         f"{func}({var}) = {result}.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Çok değişkenli analiz (multivariable calculus) — gradyan/Jacobian/Hessian,
# belirli integral, toplam/çarpım (Σ/Π), sıradan diferansiyel denklem (ODE).
# --------------------------------------------------------------------------- #
def gradient(expression: str, variables: list[str]) -> ComputeResult:
    """∇f — `expression`'ın her değişkene göre kısmi türevleri (liste)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or not variables:
            raise ComputeError("değişken listesi boş olamaz")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("gradient", str(exc), t0)
    try:
        result = [str(sympy.diff(expr, v)) for v in vs]
    except Exception as exc:  # noqa: BLE001
        return _error("gradient", f"gradyan hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "gradient", result,
                         f"∇f (değişkenler: {', '.join(variables)}).", "OK", _meta(t0))


def jacobian(expressions: list[str], variables: list[str]) -> ComputeResult:
    """Jacobian matrisi — vektör-değerli fonksiyonun kısmi türev matrisi."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(expressions, list) or not expressions:
            raise ComputeError("ifade listesi boş olamaz")
        if not isinstance(variables, list) or not variables:
            raise ComputeError("değişken listesi boş olamaz")
        fs = [_parse(e, syms) for e in expressions]
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("jacobian", str(exc), t0)
    try:
        result = _mat_out(sympy.Matrix(fs).jacobian(vs))
    except Exception as exc:  # noqa: BLE001
        return _error("jacobian", f"Jacobian hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "jacobian", result,
                         f"J = {len(fs)}×{len(vs)} matris.", "OK", _meta(t0))


def hessian(expression: str, variables: list[str]) -> ComputeResult:
    """Hessian matrisi — skaler fonksiyonun ikinci kısmi türev matrisi (simetrik)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or len(variables) < 1:
            raise ComputeError("en az bir değişken gerekir")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("hessian", str(exc), t0)
    try:
        result = _mat_out(sympy.hessian(expr, vs))
    except Exception as exc:  # noqa: BLE001
        return _error("hessian", f"Hessian hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "hessian", result,
                         f"H = {len(vs)}×{len(vs)} matris.", "OK", _meta(t0))


def definite_integral(expression: str, symbol: str, lower: str, upper: str) -> ComputeResult:
    """Belirli integral ∫ₐᵇ f dx. Sınırlar sonsuz olabilir ("oo"/"-oo")."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        a = _parse_point(str(lower), syms)
        b = _parse_point(str(upper), syms)
    except ComputeError as exc:
        return _error("definite_integral", str(exc), t0)
    try:
        result = str(sympy.integrate(expr, (var, a, b)))
    except Exception as exc:  # noqa: BLE001
        return _error("definite_integral", f"integral hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "definite_integral", result,
                         f"∫[{lower},{upper}] {expression} d{symbol} = {result}.", "OK", _meta(t0))


def summation(expression: str, index: str, lower: str, upper: str) -> ComputeResult:
    """Toplam Σ — `index` = lower..upper için `expression` toplamı (kapalı form olabilir)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        idx = _symbol(index, syms)
        a = _parse_point(str(lower), syms)
        b = _parse_point(str(upper), syms)
    except ComputeError as exc:
        return _error("summation", str(exc), t0)
    try:
        result = str(sympy.summation(expr, (idx, a, b)))
    except Exception as exc:  # noqa: BLE001
        return _error("summation", f"toplam hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "summation", result,
                         f"Σ({index}={lower}..{upper}) {expression} = {result}.", "OK", _meta(t0))


def product(expression: str, index: str, lower: str, upper: str) -> ComputeResult:
    """Çarpım Π — `index` = lower..upper için `expression` çarpımı."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        idx = _symbol(index, syms)
        a = _parse_point(str(lower), syms)
        b = _parse_point(str(upper), syms)
    except ComputeError as exc:
        return _error("product", str(exc), t0)
    try:
        result = str(sympy.product(expr, (idx, a, b)))
    except Exception as exc:  # noqa: BLE001
        return _error("product", f"çarpım hesaplanamadı: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "product", result,
                         f"Π({index}={lower}..{upper}) {expression} = {result}.", "OK", _meta(t0))


def solve_ode(equation: str, func: str = "y", var: str = "x") -> ComputeResult:
    """Sıradan diferansiyel denklemi (ODE) çözer. Türev: `y'`, `y''` (üs işareti).

    Ör: `"y' = y"` → `Eq(y(x), C1*exp(x))`; `"y'' + y = 0"` → C1·sin + C2·cos.
    Çözülemezse (kapalı form yok) DÜRÜSTÇE hata.
    """
    import re
    t0 = time.perf_counter()
    F = sympy.Function(func)
    varsym = sympy.Symbol(var)

    def _tr(node: ast.AST) -> Any:
        if isinstance(node, ast.BinOp):
            lft, rgt = _tr(node.left), _tr(node.right)
            for typ, fn in (
                (ast.Add, lambda: lft + rgt), (ast.Sub, lambda: lft - rgt),
                (ast.Mult, lambda: lft * rgt), (ast.Div, lambda: lft / rgt),
                (ast.Pow, lambda: lft ** rgt),
            ):
                if isinstance(node.op, typ):
                    return fn()
            raise ComputeError("izin verilmeyen işleç")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_tr(node.operand)
            if isinstance(node.op, ast.UAdd):
                return _tr(node.operand)
            raise ComputeError("izin verilmeyen tekli işleç")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "D":     # türev işareti: D(func, mertebe)
                if len(node.args) != 2 or not (
                    isinstance(node.args[0], ast.Name) and node.args[0].id == func
                ) or not (isinstance(node.args[1], ast.Constant)
                          and isinstance(node.args[1].value, int)):
                    raise ComputeError("türev D(func, mertebe) biçiminde olmalı")
                return sympy.Derivative(F(varsym), varsym, node.args[1].value)
            if node.func.id == func:    # y(x) açık yazımı
                return F(varsym)
            if node.func.id in _FUNCS:
                return _FUNCS[node.func.id](*[_tr(a) for a in node.args])
            raise ComputeError(f"izin verilmeyen çağrı: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id == var:
                return varsym
            if node.id == func:
                return F(varsym)
            raise ComputeError(f"izin verilmeyen ad: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
        raise ComputeError("ifade ayrıştırılamadı")

    try:
        src = str(equation).strip()
        # y', y'' ... -> D(y,1), D(y,2) ... (üs işaretini ast-uyumlu çağrıya çevir)
        src = re.sub(rf"{re.escape(func)}('+)",
                     lambda m: f"D({func},{len(m.group(1))})", src)
        if "=" in src and "==" not in src:
            src = src.replace("=", "==", 1)
        body = ast.parse(src, mode="eval").body
        if isinstance(body, ast.Compare):
            if len(body.ops) != 1 or not isinstance(body.ops[0], ast.Eq):
                raise ComputeError("yalnızca '==' karşılaştırması desteklenir")
            expr = _tr(body.left) - _tr(body.comparators[0])
        else:
            expr = _tr(body)
    except ComputeError as exc:
        return _error("solve_ode", str(exc), t0)
    except (SyntaxError, ValueError) as exc:
        return _error("solve_ode", f"ayrıştırılamadı: {exc}", t0)
    try:
        sol = sympy.dsolve(expr, F(varsym))
        result = [str(s) for s in sol] if isinstance(sol, list) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_ode", f"çözülemedi: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_ode", result,
                         f"ODE çözümü ({func}({var})).", "OK", _meta(t0))
