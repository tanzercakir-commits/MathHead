"""
mathhead.core.inequality — Eşitsizlik ispatı & nonlineer gerçel aritmetik (NRA).

Z3'ün doğrusal-olmayan gerçel aritmetik (nonlinear real arithmetic, NRA) karar
yordamıyla (nlsat / CAD) polinom eşitsizliklerini İSPATLAR ya da karşıörnek verir.

Yöntem: `∀x. P(x)` iddiasını `¬P(x)` UNSAT mı diye kontrol ederek ispatlarız
(ret-ile-ispat / proof by refutation). SAT → karşıörnek; UNSAT → geçerli.

Dürüstlük: NRA teoride karar-verilebilir (gerçel kapalı cisim) ama Z3 pratikte
zor örneklerde `unknown`/timeout dönebilir — bu birinci sınıf raporlanır.

Girdi grameri (compute'tan ayrı, burada NONLINEER serbest): değişkenler `Real`;
`+ - * / **` (üs = negatif-olmayan tam sayı), karşılaştırma `< <= > >= == !=`,
bağlaçlar `and`/`or`/`not(...)`/`implies(a,b)`/`iff(a,b)`. `eval`/`sympify` YOK.
"""
from __future__ import annotations

import ast
import time
from typing import Any

import z3

from mathhead.core.logic import (
    DEFAULT_SEED,
    DEFAULT_TIMEOUT_MS,
    ReasoningResult,
    _meta,
    _py_value,
)
from mathhead.guardrails import solver_config

__all__ = ["find_real_solution", "prove_inequality", "prove_nonnegative"]


class _IneqError(ValueError):
    """Eşitsizlik grameri ihlali (net hata, sessiz varsayım yok)."""


_CMP = {
    ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
}


def _node(node: ast.AST, rvars: dict[str, Any]) -> Any:
    """ast düğümü -> Z3 ifadesi (aritmetik ArithRef ya da mantıksal BoolRef)."""
    if isinstance(node, ast.BoolOp):
        vals = [_node(v, rvars) for v in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*vals)
        if isinstance(node.op, ast.Or):
            return z3.Or(*vals)
        raise _IneqError("izin verilmeyen bool işleci")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return z3.Not(_node(node.operand, rvars))
        if isinstance(node.op, ast.USub):
            return -_node(node.operand, rvars)
        if isinstance(node.op, ast.UAdd):
            return _node(node.operand, rvars)
        raise _IneqError("izin verilmeyen tekli işleç")
    if isinstance(node, ast.BinOp):
        lft, rgt = _node(node.left, rvars), _node(node.right, rvars)
        op = node.op
        if isinstance(op, ast.Add):
            return lft + rgt
        if isinstance(op, ast.Sub):
            return lft - rgt
        if isinstance(op, ast.Mult):
            return lft * rgt
        if isinstance(op, ast.Div):
            return lft / rgt
        if isinstance(op, ast.Pow):
            if not (isinstance(node.right, ast.Constant)
                    and isinstance(node.right.value, int) and node.right.value >= 0):
                raise _IneqError("üs negatif olmayan tam sayı olmalı (polinom)")
            return lft ** node.right.value
        raise _IneqError("izin verilmeyen işleç")
    if isinstance(node, ast.Compare):
        cur = _node(node.left, rvars)
        parts = []
        for op, comp in zip(node.ops, node.comparators):
            if type(op) not in _CMP:
                raise _IneqError("izin verilmeyen karşılaştırma")
            rn = _node(comp, rvars)
            parts.append(_CMP[type(op)](cur, rn))
            cur = rn
        return parts[0] if len(parts) == 1 else z3.And(*parts)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "implies" and len(node.args) == 2:
            return z3.Implies(_node(node.args[0], rvars), _node(node.args[1], rvars))
        if node.func.id == "iff" and len(node.args) == 2:
            return _node(node.args[0], rvars) == _node(node.args[1], rvars)
        raise _IneqError(f"izin verilmeyen çağrı: {node.func.id}")
    if isinstance(node, ast.Name):
        if node.id not in rvars:
            rvars[node.id] = z3.Real(node.id)
        return rvars[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return z3.RealVal(node.value)
    raise _IneqError("ifade ayrıştırılamadı")


def _translate(expr: str, rvars: dict[str, Any]) -> Any:
    return _node(ast.parse(str(expr).strip(), mode="eval").body, rvars)


def _real_witness(model: z3.ModelRef, rvars: dict[str, Any]) -> dict[str, Any]:
    """Gerçel değişkenlere somut bir nokta atar (kanonik tamamlama → determinizm)."""
    out = {name: _py_value(model.eval(const, model_completion=True))
           for name, const in rvars.items()}
    return dict(sorted(out.items()))


def _err(msg: str, t0: float, seed: int, timeout_ms: int) -> ReasoningResult:
    return ReasoningResult("error", "GUARDRAIL_VIOLATION", msg, None, _meta(t0, seed, timeout_ms))


def prove_inequality(goal: str, assumptions: list[str] | None = None,
                     timeout_ms: int = DEFAULT_TIMEOUT_MS,
                     seed: int = DEFAULT_SEED) -> ReasoningResult:
    """`goal` eşitsizliği TÜM gerçel değerler için (varsayımlar altında) geçerli mi?

    valid → her yerde doğru (¬goal UNSAT). invalid → `witness` bir karşıörnek.
    unknown → Z3 NRA karar veremedi (dürüst).
    """
    t0 = time.perf_counter()
    assumptions = assumptions or []
    rvars: dict[str, Any] = {}
    try:
        g = _translate(goal, rvars)
        assumps = [_translate(a, rvars) for a in assumptions]
    except (_IneqError, SyntaxError, ValueError) as exc:
        return _err(f"ayrıştırma hatası: {exc}", t0, seed, timeout_ms)
    if not z3.is_bool(g):
        return _err("hedef bir karşılaştırma/önerme olmalı (ör. 'x**2 >= 0')", t0, seed, timeout_ms)
    solver = solver_config(timeout_ms, seed)
    for a in assumps:
        solver.add(a)
    solver.add(z3.Not(g))
    res = solver.check()
    suffix = " (varsayımlar altında)" if assumptions else ""
    if res == z3.unsat:
        return ReasoningResult("valid", "ENTAILED",
                               f"eşitsizlik tüm gerçel değerler için geçerli{suffix}.",
                               None, _meta(t0, seed, timeout_ms))
    if res == z3.sat:
        wit = _real_witness(solver.model(), rvars)
        return ReasoningResult("invalid", "COUNTEREXAMPLE_FOUND",
                               f"eşitsizlik her yerde geçerli değil; karşıörnek: {wit}.",
                               wit, _meta(t0, seed, timeout_ms))
    return ReasoningResult("unknown", "SOLVER_UNKNOWN",
                           "Z3 NRA karar veremedi (zor örnek / timeout).",
                           None, _meta(t0, seed, timeout_ms))


def prove_nonnegative(expression: str, assumptions: list[str] | None = None,
                      timeout_ms: int = DEFAULT_TIMEOUT_MS,
                      seed: int = DEFAULT_SEED) -> ReasoningResult:
    """`expression ≥ 0` her gerçel değer için (varsayımlar altında) geçerli mi?

    Özel durum: kareler toplamı benzeri negatif-olmama iddiaları (ör. `x**2 - 2*x + 1`).
    """
    return prove_inequality(f"({expression}) >= 0", assumptions, timeout_ms, seed)


def find_real_solution(constraints: list[str],
                       timeout_ms: int = DEFAULT_TIMEOUT_MS,
                       seed: int = DEFAULT_SEED) -> ReasoningResult:
    """Doğrusal-olmayan kısıt kümesini GERÇEL sayılarda sağlayan bir nokta bulur.

    sat → `witness` somut bir çözüm; unsat → gerçel çözüm yok; unknown → karar yok.
    """
    t0 = time.perf_counter()
    rvars: dict[str, Any] = {}
    try:
        if not isinstance(constraints, list) or not constraints:
            raise _IneqError("kısıt listesi boş olamaz")
        cs = [_translate(c, rvars) for c in constraints]
    except (_IneqError, SyntaxError, ValueError) as exc:
        return _err(f"ayrıştırma hatası: {exc}", t0, seed, timeout_ms)
    if not all(z3.is_bool(c) for c in cs):
        return _err("her kısıt bir karşılaştırma/önerme olmalı", t0, seed, timeout_ms)
    solver = solver_config(timeout_ms, seed)
    for c in cs:
        solver.add(c)
    res = solver.check()
    if res == z3.sat:
        wit = _real_witness(solver.model(), rvars)
        return ReasoningResult("sat", "MODEL_FOUND", f"gerçel çözüm bulundu: {wit}.",
                               wit, _meta(t0, seed, timeout_ms))
    if res == z3.unsat:
        return ReasoningResult("unsat", "NO_MODEL", "gerçel çözüm yok (kısıtlar tutarsız).",
                               None, _meta(t0, seed, timeout_ms))
    return ReasoningResult("unknown", "SOLVER_UNKNOWN",
                           "Z3 NRA karar veremedi (zor örnek / timeout).",
                           None, _meta(t0, seed, timeout_ms))
