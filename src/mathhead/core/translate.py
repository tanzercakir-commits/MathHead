"""
mathhead.core.translate
========================

Girdi ifadesi -> Z3 nesnesi çevirimi (parsing + translation).

Tasarım (ADR-0009/0010/0013): Python `ast` ile ayrıştır, düğümleri **beyaz
liste** ile süz, **iki geçişte** çevir (infer: sort çıkarımı + scope; build: Z3).

v1.2 dili (fragment):
  * Boolean: `and`, `or`, `not`, `implies(a,b)`, `iff(a,b)`, `xor(a,b)`
  * Nicelik belirteçleri: `forall(x, gövde)`, `exists(x, gövde)`
  * **Yüklemler / ilişkiler (yorumsuz):** `Man(x)`, `Loves(a, b)` — birey (sort U)
    üzerinden Bool döndürür. **Bireyler:** ad olan sabit/değişkenler (`socrates`).
    (Klasik silogizmi mümkün kılar.)
  * Aritmetik: `+`, `-`, `*` (DOĞRUSAL); Karşılaştırma: `< <= == != >= >` (zincir)
  * Üç sort: `bool`, sayısal (`Int`/`Real`; ondalık varsa Real), `ind` (birey/U).
    Sort bağlamdan çıkarılır; çelişki -> ParseError (sessiz varsayım yok).

Sınır (v1.2): yüklem argümanları **birey adı** olmalı (yorumsuz fonksiyon terimleri
`f(x)` ve yüklem-içi aritmetik henüz yok). Nicelik belirteçleri + yüklemler FOL'u
yarı-karar verilebilir yapar; Z3 `unknown` dönebilir (dürüstçe raporlanır).
"""
from __future__ import annotations

import ast
import itertools
from typing import Any

import z3

_BOOL_FUNCS = {"implies", "iff", "xor"}
_QUANTIFIERS = {"forall", "exists"}

# Bireyler (individuals) için yorumsuz sort. Aynı adla yeniden çağrı aynı sortu verir.
_U = z3.DeclareSort("U")

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
    try:
        return ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ParseError(f"sözdizimi hatası: {exc.msg}") from exc


def _has_float(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(tree)
    )


def _contains_name(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) for n in ast.walk(node))


def _need(produced: str, expected: str, node: ast.AST) -> None:
    if produced != expected:
        raise ParseError(
            f"tür uyuşmazlığı: '{expected}' beklenirken '{produced}' bulundu "
            f"({type(node).__name__})"
        )


class _Translator:
    """İki geçişli çevirmen: infer (sort) + build (Z3). Serbest semboller ve
    yüklemler bir problem (ifade kümesi) boyunca paylaşılır."""

    def __init__(self, has_real: bool):
        self.has_real = has_real
        self.sorts: dict[str, str] = {}      # serbest değişken -> "bool"|"num"|"ind"
        self.symbols: dict[str, Any] = {}    # serbest değişken -> z3 sabiti
        self.preds: dict[str, int] = {}      # yüklem adı -> arite
        self._pred_funcs: dict[str, Any] = {}  # yüklem adı -> z3.Function
        self.bound: dict[int, str] = {}      # id(quantifier düğümü) -> çözülmüş sort
        self._counter = itertools.count()

    def _make_const(self, name: str, sort: str) -> Any:
        if sort == "bool":
            return z3.Bool(name)
        if sort == "ind":
            return z3.Const(name, _U)
        return z3.Real(name) if self.has_real else z3.Int(name)

    @staticmethod
    def _scope_of(name: str, env: list[dict]) -> dict | None:
        for scope in reversed(env):
            if name in scope:
                return scope
        return None

    # ================= PASS 1: SORT ÇIKARIMI ==================
    def infer(self, node: ast.AST, expected: str, env: list[dict]) -> None:
        if isinstance(node, ast.BoolOp):
            _need("bool", expected, node)
            for value in node.values:
                self.infer(value, "bool", env)
        elif isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                _need("bool", expected, node)
                self.infer(node.operand, "bool", env)
            elif isinstance(node.op, (ast.USub, ast.UAdd)):
                _need("num", expected, node)
                self.infer(node.operand, "num", env)
            else:
                raise ParseError(f"desteklenmeyen tekli operatör: {type(node.op).__name__}")
        elif isinstance(node, ast.Compare):
            _need("bool", expected, node)
            self.infer(node.left, "num", env)
            for op, comp in zip(node.ops, node.comparators):
                if type(op) not in _CMP:
                    raise ParseError(f"desteklenmeyen karşılaştırma: {type(op).__name__}")
                self.infer(comp, "num", env)
        elif isinstance(node, ast.BinOp):
            _need("num", expected, node)
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
                raise ParseError(f"yalnızca +, -, * desteklenir ({type(node.op).__name__} değil)")
            self.infer(node.left, "num", env)
            self.infer(node.right, "num", env)
            if isinstance(node.op, ast.Mult) and _contains_name(node.left) and _contains_name(node.right):
                raise ParseError("doğrusal olmayan çarpım (değişken*değişken) desteklenmiyor")
        elif isinstance(node, ast.Call):
            self._infer_call(node, expected, env)
        elif isinstance(node, ast.Name):
            self._assign(node.id, expected, env)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                _need("bool", expected, node)
            elif isinstance(node.value, (int, float)):
                _need("num", expected, node)
            else:
                raise ParseError(f"desteklenmeyen sabit: {node.value!r}")
        else:
            raise ParseError(f"izin verilmeyen ifade düğümü: {type(node).__name__}")

    def _assign(self, name: str, sort: str, env: list[dict]) -> None:
        if name in self.preds:
            raise ParseError(f"'{name}' bir yüklem; aynı zamanda değişken olamaz")
        scope = self._scope_of(name, env)
        table = scope if scope is not None else self.sorts
        current = table.get(name)
        if current is None:
            table[name] = sort
        elif current != sort:
            raise ParseError(f"'{name}' hem '{current}' hem '{sort}' olarak kullanılamaz")

    def _infer_call(self, node: ast.Call, expected: str, env: list[dict]) -> None:
        if not isinstance(node.func, ast.Name):
            raise ParseError("yalnızca ad ile fonksiyon çağrısına izin var")
        fname = node.func.id
        if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
            raise ParseError("fonksiyon çağrısında keyword/yıldız argüman yok")

        if fname in _BOOL_FUNCS:
            _need("bool", expected, node)
            if len(node.args) != 2:
                raise ParseError(f"{fname} tam 2 argüman ister")
            self.infer(node.args[0], "bool", env)
            self.infer(node.args[1], "bool", env)
        elif fname in _QUANTIFIERS:
            _need("bool", expected, node)
            if len(node.args) != 2 or not isinstance(node.args[0], ast.Name):
                raise ParseError(f"{fname}(değişken, gövde) bekler; 1. argüman değişken adı olmalı")
            var = node.args[0].id
            scope: dict[str, str | None] = {var: None}
            env.append(scope)
            self.infer(node.args[1], "bool", env)
            env.pop()
            self.bound[id(node)] = scope[var] or "ind"  # kullanılmadıysa birey say
        else:
            # Yorumsuz yüklem: P(bireyler...) -> Bool
            _need("bool", expected, node)
            if fname in self.sorts or self._scope_of(fname, env) is not None:
                raise ParseError(f"'{fname}' bir değişken; aynı zamanda yüklem olamaz")
            arity = len(node.args)
            if self.preds.get(fname, arity) != arity:
                raise ParseError(f"'{fname}' yüklemi farklı arite ile kullanıldı")
            self.preds[fname] = arity
            for arg in node.args:
                if not isinstance(arg, ast.Name):
                    raise ParseError(f"v1.2: '{fname}' argümanları birey adı (değişken/sabit) olmalı")
                self.infer(arg, "ind", env)

    # ==================== PASS 2: İNŞA ========================
    def build(self, node: ast.AST, env: list[dict]) -> Any:
        if isinstance(node, ast.BoolOp):
            parts = [self.build(v, env) for v in node.values]
            return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return z3.Not(self.build(node.operand, env))
            val = self.build(node.operand, env)
            return -val if isinstance(node.op, ast.USub) else val
        if isinstance(node, ast.Compare):
            return self._build_compare(node, env)
        if isinstance(node, ast.BinOp):
            left = self.build(node.left, env)
            right = self.build(node.right, env)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            return left * right
        if isinstance(node, ast.Call):
            return self._build_call(node, env)
        if isinstance(node, ast.Name):
            scope = self._scope_of(node.id, env)
            if scope is not None:
                return scope[node.id]
            if node.id not in self.symbols:
                self.symbols[node.id] = self._make_const(node.id, self.sorts[node.id])
            return self.symbols[node.id]
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return z3.BoolVal(node.value)
            if isinstance(node.value, int):
                return z3.RealVal(node.value) if self.has_real else z3.IntVal(node.value)
            return z3.RealVal(node.value)
        raise ParseError(f"izin verilmeyen ifade düğümü: {type(node).__name__}")

    def _build_compare(self, node: ast.Compare, env: list[dict]) -> Any:
        prev = self.build(node.left, env)
        clauses = []
        for op, comp in zip(node.ops, node.comparators):
            right = self.build(comp, env)
            clauses.append(_CMP[type(op)](prev, right))
            prev = right
        return clauses[0] if len(clauses) == 1 else z3.And(*clauses)

    def _build_call(self, node: ast.Call, env: list[dict]) -> Any:
        fname = node.func.id
        if fname in _BOOL_FUNCS:
            a = self.build(node.args[0], env)
            b = self.build(node.args[1], env)
            if fname == "implies":
                return z3.Implies(a, b)
            if fname == "iff":
                return a == b
            return z3.Xor(a, b)
        if fname in _QUANTIFIERS:
            var = node.args[0].id
            sort = self.bound[id(node)]
            const = self._make_const(f"__b{next(self._counter)}_{var}", sort)
            env.append({var: const})
            body = self.build(node.args[1], env)
            env.pop()
            return z3.ForAll([const], body) if fname == "forall" else z3.Exists([const], body)
        # Yorumsuz yüklem
        arity = self.preds[fname]
        if fname not in self._pred_funcs:
            self._pred_funcs[fname] = z3.Function(fname, *([_U] * arity), z3.BoolSort())
        return self._pred_funcs[fname](*[self.build(a, env) for a in node.args])


def translate_all(expressions: list[str]) -> tuple[list[Any], dict[str, Any]]:
    """Bir ifade listesini ortak bağlamda çevirir (paylaşımlı serbest semboller,
    yüklemler ve bireyler). Returns: (z3_ifadeleri, serbest_semboller)."""
    trees = [parse(e) for e in expressions]
    has_real = any(_has_float(t) for t in trees)
    tr = _Translator(has_real)
    for tree in trees:
        tr.infer(tree.body, "bool", [])
    z3_exprs = [tr.build(tree.body, []) for tree in trees]
    return z3_exprs, tr.symbols


def to_z3(expression: str, symbols: dict[str, Any] | None = None, sorts: dict | None = None) -> Any:
    """Tek bir ifadeyi Z3'e çevirir (geri uyumluluk sarmalayıcısı)."""
    exprs, syms = translate_all([expression])
    if symbols is not None:
        symbols.update(syms)
    return exprs[0]
