"""
mathhead.core.translate
========================

Input expression -> Z3 object translation (parsing + translation).

Design (ADR-0009/0010/0013): parse with Python `ast`, filter nodes through a
**whitelist**, translate in **two passes** (infer: sort inference + scope; build: Z3).

v1.2 language (fragment):
  * Boolean: `and`, `or`, `not`, `implies(a,b)`, `iff(a,b)`, `xor(a,b)`
  * Quantifiers: `forall(x, body)`, `exists(x, body)`
  * **Predicates / relations (uninterpreted):** `Man(x)`, `Loves(a, b)` — return
    Bool over individuals (sort U). **Individuals:** named constants/variables
    (`socrates`). (Makes the classical syllogism possible.)
  * Arithmetic: `+`, `-`, `*` (LINEAR); Comparison: `< <= == != >= >` (chained)
  * Three sorts: `bool`, numeric (`Int`/`Real`; Real if a decimal is present), `ind`
    (individual/U). The sort is inferred from context; a conflict -> ParseError (no
    silent assumptions).

Limit (v1.2): predicate arguments must be an **individual name** (uninterpreted
function terms `f(x)` and arithmetic inside predicates are not yet supported).
Quantifiers + predicates make FOL semi-decidable; Z3 may return `unknown` (reported
honestly).
"""
from __future__ import annotations

import ast
import itertools
from typing import Any

import z3

_BOOL_FUNCS = {"implies", "iff", "xor"}
_QUANTIFIERS = {"forall", "exists"}

# Uninterpreted sort for individuals. Re-declaring with the same name yields the same sort.
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
    """Input grammar violated. Guardrail: clear error, NO silent assumptions."""


def parse(expression: str) -> ast.Expression:
    try:
        return ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ParseError(f"syntax error: {exc.msg}") from exc


def _has_float(tree: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(tree)
    )


def _contains_name(node: ast.AST) -> bool:
    return any(isinstance(n, ast.Name) for n in ast.walk(node))


def _need(produced: str, expected: str, node: ast.AST) -> None:
    if produced != expected:
        raise ParseError(
            f"type mismatch: expected '{expected}' but found '{produced}' "
            f"({type(node).__name__})"
        )


class _Translator:
    """Two-pass translator: infer (sort) + build (Z3). Free symbols and predicates
    are shared across a problem (set of expressions)."""

    def __init__(self, has_real: bool):
        self.has_real = has_real
        self.sorts: dict[str, str] = {}      # free variable -> "bool"|"num"|"ind"
        self.symbols: dict[str, Any] = {}    # free variable -> z3 constant
        self.preds: dict[str, int] = {}      # predicate name -> arity
        self._pred_funcs: dict[str, Any] = {}  # predicate name -> z3.Function
        self.bound: dict[int, str] = {}      # id(quantifier node) -> resolved sort
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

    # ================= PASS 1: SORT INFERENCE ==================
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
                raise ParseError(f"unsupported unary operator: {type(node.op).__name__}")
        elif isinstance(node, ast.Compare):
            _need("bool", expected, node)
            self.infer(node.left, "num", env)
            for op, comp in zip(node.ops, node.comparators):
                if type(op) not in _CMP:
                    raise ParseError(f"unsupported comparison: {type(op).__name__}")
                self.infer(comp, "num", env)
        elif isinstance(node, ast.BinOp):
            _need("num", expected, node)
            if not isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
                raise ParseError(f"only +, -, * are supported (not {type(node.op).__name__})")
            self.infer(node.left, "num", env)
            self.infer(node.right, "num", env)
            if isinstance(node.op, ast.Mult) and _contains_name(node.left) and _contains_name(node.right):
                raise ParseError("nonlinear product (variable*variable) is not supported")
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
                raise ParseError(f"unsupported constant: {node.value!r}")
        else:
            raise ParseError(f"disallowed expression node: {type(node).__name__}")

    def _assign(self, name: str, sort: str, env: list[dict]) -> None:
        if name in self.preds:
            raise ParseError(f"'{name}' is a predicate; it cannot also be a variable")
        scope = self._scope_of(name, env)
        table = scope if scope is not None else self.sorts
        current = table.get(name)
        if current is None:
            table[name] = sort
        elif current != sort:
            raise ParseError(f"'{name}' cannot be used as both '{current}' and '{sort}'")

    def _infer_call(self, node: ast.Call, expected: str, env: list[dict]) -> None:
        if not isinstance(node.func, ast.Name):
            raise ParseError("only name-based function calls are allowed")
        fname = node.func.id
        if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
            raise ParseError("no keyword/star arguments in a function call")

        if fname in _BOOL_FUNCS:
            _need("bool", expected, node)
            if len(node.args) != 2:
                raise ParseError(f"{fname} requires exactly 2 arguments")
            self.infer(node.args[0], "bool", env)
            self.infer(node.args[1], "bool", env)
        elif fname in _QUANTIFIERS:
            _need("bool", expected, node)
            if len(node.args) != 2 or not isinstance(node.args[0], ast.Name):
                raise ParseError(f"{fname}(variable, body) expected; the 1st argument must be a variable name")
            var = node.args[0].id
            scope: dict[str, str | None] = {var: None}
            env.append(scope)
            self.infer(node.args[1], "bool", env)
            env.pop()
            self.bound[id(node)] = scope[var] or "ind"  # if unused, treat as individual
        else:
            # Uninterpreted predicate: P(individuals...) -> Bool
            _need("bool", expected, node)
            if fname in self.sorts or self._scope_of(fname, env) is not None:
                raise ParseError(f"'{fname}' is a variable; it cannot also be a predicate")
            arity = len(node.args)
            if self.preds.get(fname, arity) != arity:
                raise ParseError(f"predicate '{fname}' used with a different arity")
            self.preds[fname] = arity
            for arg in node.args:
                if not isinstance(arg, ast.Name):
                    raise ParseError(f"v1.2: '{fname}' arguments must be individual names (variables/constants)")
                self.infer(arg, "ind", env)

    # ==================== PASS 2: BUILD ========================
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
        raise ParseError(f"disallowed expression node: {type(node).__name__}")

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
        # Uninterpreted predicate
        arity = self.preds[fname]
        if fname not in self._pred_funcs:
            self._pred_funcs[fname] = z3.Function(fname, *([_U] * arity), z3.BoolSort())
        return self._pred_funcs[fname](*[self.build(a, env) for a in node.args])


def translate_all(expressions: list[str]) -> tuple[list[Any], dict[str, Any]]:
    """Translates a list of expressions in a shared context (shared free symbols,
    predicates and individuals). Returns: (z3_expressions, free_symbols)."""
    trees = [parse(e) for e in expressions]
    has_real = any(_has_float(t) for t in trees)
    tr = _Translator(has_real)
    for tree in trees:
        tr.infer(tree.body, "bool", [])
    z3_exprs = [tr.build(tree.body, []) for tree in trees]
    return z3_exprs, tr.symbols


def translate_objective(constraints: list[str], objective: str) -> tuple[list[Any], Any, dict[str, Any]]:
    """Translates the constraints (bool) and an objective expression (NUMERIC) in a
    shared context.

    For optimization: the variables in the objective must be the same Z3 constants
    as those in the constraints. Returns: (constraint_z3_list, objective_z3, symbols).
    """
    c_trees = [parse(c) for c in constraints]
    o_tree = parse(objective)
    has_real = any(_has_float(t) for t in [*c_trees, o_tree])
    tr = _Translator(has_real)
    for tree in c_trees:
        tr.infer(tree.body, "bool", [])
    tr.infer(o_tree.body, "num", [])            # the objective is numeric
    c_z3 = [tr.build(tree.body, []) for tree in c_trees]
    o_z3 = tr.build(o_tree.body, [])
    return c_z3, o_z3, tr.symbols


def to_z3(expression: str, symbols: dict[str, Any] | None = None, sorts: dict | None = None) -> Any:
    """Translates a single expression to Z3 (backward-compatibility wrapper)."""
    exprs, syms = translate_all([expression])
    if symbols is not None:
        symbols.update(syms)
    return exprs[0]
