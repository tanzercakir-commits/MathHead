"""
mathhead.core.translate
========================

Girdi ifadesi -> Z3 nesnesi çevirimi (parsing + translation).

Tasarım kararı (DECISIONS ADR-0009): elle parser yazmak yerine Python'un kendi
`ast` modülünü kullanıyoruz ve düğümleri **beyaz liste** (whitelist) ile
süzüyoruz. Böylece:
  * olgun, iyi test edilmiş bir ayrıştırıcı (parser) kullanırız,
  * yalnızca izin verdiğimiz düğümler geçer; gerisi net reddedilir (guardrail),
  * operatör önceliği/parantez gibi işleri Python halleder.

v1 dili (fragment) — kasıtlı olarak KARAR VERİLEBİLİR (decidable) tutuldu:
  * Boolean: `and`, `or`, `not`, ve `implies(a,b)`, `iff(a,b)`, `xor(a,b)`
  * Aritmetik (tam sayı / Int): `+`, `-`, `*`  (DOĞRUSAL: değişken*değişken YASAK)
  * Karşılaştırma: `<`, `<=`, `==`, `!=`, `>=`, `>` (zincir destekli: 1 < x < 5)
  * Değişkenler: Bool veya Int; sort BAĞLAMDAN çıkarılır. Bir isim hem Bool hem
    Int kullanılırsa -> ParseError (sessiz varsayım yok).
  * Real sayılar ve ∀/∃ nicelik belirteçleri v1'de YOK (v1.1 hedefi).
"""
from __future__ import annotations

import ast
from typing import Any

import z3

_BOOL_FUNCS = {"implies", "iff", "xor"}

_CMP = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}


class ParseError(ValueError):
    """Girdi grameri ihlal edildi. Guardrail: net hata, sessiz varsayım YOK."""


def parse(expression: str) -> ast.Expression:
    """Tek bir ifadeyi güvenli kipte ayrıştırır (`ast`), hata -> ParseError."""
    try:
        return ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ParseError(f"sözdizimi hatası: {exc.msg}") from exc


def to_z3(
    expression: str,
    symbols: dict[str, Any] | None = None,
    sorts: dict[str, str] | None = None,
) -> Any:
    """Bir ifadeyi Z3 mantık nesnesine çevirir.

    Args:
        expression: gramere uygun mantık ifadesi.
        symbols: paylaşılan sembol tablosu (aynı isim -> aynı Z3 sabiti). Birden
            çok ifade arasında tutarlılık için çağıran (logic/router) besler.
        sorts: paylaşılan sort tablosu (isim -> "bool"|"int"); çelişki denetimi.
    """
    symbols = symbols if symbols is not None else {}
    sorts = sorts if sorts is not None else {}
    tree = parse(expression)
    return _translate(tree.body, "bool", symbols, sorts)


def translate_all(expressions: list[str]) -> tuple[list[Any], dict[str, Any]]:
    """Bir ifade listesini ortak sembol tablosuyla çevirir.

    Returns:
        (z3_ifadeleri, semboller). Semboller model/karşıörnek çıkarımında kullanılır.
    """
    symbols: dict[str, Any] = {}
    sorts: dict[str, str] = {}
    z3_exprs = [to_z3(e, symbols, sorts) for e in expressions]
    return z3_exprs, symbols


# --------------------------------------------------------------------------- #
# İç çeviri (top-down, beklenen-sort ile hem doğrulama hem inşa).
# --------------------------------------------------------------------------- #
def _expect(produced: str, expected: str, node: ast.AST) -> None:
    if produced != expected:
        raise ParseError(
            f"tür uyuşmazlığı: '{expected}' beklenirken '{produced}' bulundu "
            f"({type(node).__name__})"
        )


def _contains_name(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) for n in ast.walk(node))


def _symbol(name: str, sort: str, symbols: dict, sorts: dict) -> Any:
    if name in sorts:
        if sorts[name] != sort:
            raise ParseError(
                f"'{name}' hem '{sorts[name]}' hem '{sort}' olarak kullanılamaz"
            )
    else:
        sorts[name] = sort
        symbols[name] = z3.Bool(name) if sort == "bool" else z3.Int(name)
    return symbols[name]


def _translate(node: ast.AST, expected: str, symbols: dict, sorts: dict) -> Any:
    # Boolean bağlaçlar -----------------------------------------------------
    if isinstance(node, ast.BoolOp):
        _expect("bool", expected, node)
        parts = [_translate(v, "bool", symbols, sorts) for v in node.values]
        return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            _expect("bool", expected, node)
            return z3.Not(_translate(node.operand, "bool", symbols, sorts))
        if isinstance(node.op, (ast.USub, ast.UAdd)):
            _expect("int", expected, node)
            val = _translate(node.operand, "int", symbols, sorts)
            return -val if isinstance(node.op, ast.USub) else val
        raise ParseError(f"desteklenmeyen tekli operatör: {type(node.op).__name__}")

    if isinstance(node, ast.Call):
        return _translate_call(node, expected, symbols, sorts)

    if isinstance(node, ast.Compare):
        _expect("bool", expected, node)
        return _translate_compare(node, symbols, sorts)

    # Aritmetik -------------------------------------------------------------
    if isinstance(node, ast.BinOp):
        _expect("int", expected, node)
        if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            raise ParseError(
                f"yalnızca +, -, * desteklenir ({type(node.op).__name__} değil)"
            )
        left = _translate(node.left, "int", symbols, sorts)
        right = _translate(node.right, "int", symbols, sorts)
        if isinstance(node.op, ast.Mult) and _contains_name(node.left) and _contains_name(node.right):
            raise ParseError("doğrusal olmayan çarpım (değişken*değişken) v1'de yasak")
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        return left * right

    # Yapraklar -------------------------------------------------------------
    if isinstance(node, ast.Name):
        return _symbol(node.id, expected, symbols, sorts)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):  # bool, int'ten ÖNCE (bool ⊂ int)
            _expect("bool", expected, node)
            return z3.BoolVal(node.value)
        if isinstance(node.value, int):
            _expect("int", expected, node)
            return z3.IntVal(node.value)
        raise ParseError(f"desteklenmeyen sabit: {node.value!r}")

    raise ParseError(f"izin verilmeyen ifade düğümü: {type(node).__name__}")


def _translate_call(node: ast.Call, expected: str, symbols: dict, sorts: dict) -> Any:
    if not isinstance(node.func, ast.Name) or node.func.id not in _BOOL_FUNCS:
        raise ParseError("yalnızca implies/iff/xor fonksiyonlarına izin var")
    _expect("bool", expected, node)
    if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
        raise ParseError("fonksiyon çağrısında keyword/yıldız argüman yok")
    if len(node.args) != 2:
        raise ParseError(f"{node.func.id} tam 2 argüman ister (gelen: {len(node.args)})")
    a = _translate(node.args[0], "bool", symbols, sorts)
    b = _translate(node.args[1], "bool", symbols, sorts)
    if node.func.id == "implies":
        return z3.Implies(a, b)
    if node.func.id == "iff":
        return a == b
    return z3.Xor(a, b)


def _translate_compare(node: ast.Compare, symbols: dict, sorts: dict) -> Any:
    left = _translate(node.left, "int", symbols, sorts)
    clauses = []
    prev = left
    for op, comp in zip(node.ops, node.comparators):
        if type(op) not in _CMP:
            raise ParseError(f"desteklenmeyen karşılaştırma: {type(op).__name__}")
        right = _translate(comp, "int", symbols, sorts)
        clauses.append(_CMP[type(op)](prev, right))
        prev = right
    return clauses[0] if len(clauses) == 1 else z3.And(*clauses)
