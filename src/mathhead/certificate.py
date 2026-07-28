"""
mathhead.certificate — INDEPENDENT CERTIFICATE CHECKER (ROADMAP Track C2).

**The edge it gives:** "Don't trust us, run the checker yourself." A MathHead
result (witness / counterexample / coloring) must be re-verifiable by a small,
readable checker that is INDEPENDENT of the engine that PRODUCED it (Z3/SymPy).

This module DELIBERATELY uses only the Python **standard library** — NO `z3`,
NO `sympy` (that is why it stays outside `core` and off the `import` chain;
`tests/test_certificate.py` proves this in a subprocess). Arithmetic is done
**exactly** with `fractions.Fraction` whenever possible; if a transcendental
function appears, it falls back to a numeric (float + tolerance) check, and
this is stated honestly.

Certificate kinds (self-contained dicts):
- subset_sum        · {numbers, target, indices}
- graph_coloring    · {edges, colors, coloring}
- solution          · {expression, symbol, value}  (is the residual 0)
- not_equal         · {left, right, point}          (counterexample: left ≠ right)
- inequality_counterexample · {expression, point, relation}  (poly. violated at that point)
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

# ast Call -> stdlib function (transcendental → numeric/float).
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
    exact: bool = True                # exact (Fraction) or numeric (float)
    meta: dict[str, Any] = field(default_factory=dict)


class _CertError(ValueError):
    pass


def _num(value: Any) -> Any:
    """Converts the input to an integer/fraction (Fraction) or a float."""
    if isinstance(value, bool):
        raise _CertError("boolean is not a number")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        return value
    s = str(value).strip()
    try:
        return Fraction(s)               # "3", "1/2", "-4" → exact
    except (ValueError, ZeroDivisionError):
        return float(s)                  # "0.5", "1e3" → float


def _eval(node: ast.AST, env: dict[str, Any]) -> Any:
    """Evaluates an ast expression under env. Returns a Fraction (exact) or a float."""
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
                raise _CertError("division by zero")
            return lft / rgt
        if isinstance(op, ast.Pow):
            if isinstance(lft, Fraction) and isinstance(rgt, Fraction) and rgt.denominator == 1:
                return lft ** int(rgt)          # integer exponent → Fraction (exact)
            return float(lft) ** float(rgt)     # otherwise float
        raise _CertError(f"disallowed operator: {type(op).__name__}")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            return -_eval(node.operand, env)
        if isinstance(node.op, ast.UAdd):
            return _eval(node.operand, env)
        raise _CertError("disallowed unary operator")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        fn = _FUNCS.get(node.func.id)
        if fn is None:
            raise _CertError(f"disallowed function: {node.func.id}")
        return float(fn(*[float(_eval(a, env)) for a in node.args]))
    if isinstance(node, ast.Name):
        if node.id not in env:
            raise _CertError(f"undefined variable: {node.id}")
        return env[node.id]
    if isinstance(node, ast.Constant):
        return _num(node.value)
    raise _CertError(f"disallowed expression: {type(node).__name__}")


def _evaluate(expression: str, env: dict[str, Any]) -> Any:
    tree = ast.parse(str(expression).strip(), mode="eval")
    return _eval(tree.body, env)


def _is_zero(value: Any) -> tuple[bool, bool]:
    """(is zero, is exact). Fraction → exact equality; float → tolerance."""
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
    """Re-verifies a certificate INDEPENDENTLY of z3/sympy (stdlib only).

    verified → the certificate holds; refuted → it does not (result is WRONG); error → malformed.
    """
    t0 = time.perf_counter()
    result = _check_impl(certificate)
    result.meta = {"engine": "stdlib-certificate",
                   "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}
    return result


def _check_impl(certificate: dict[str, Any]) -> CertificateResult:
    if not isinstance(certificate, dict):
        return _bad("certificate must be a dict")
    kind = certificate.get("kind")
    try:
        if kind == "subset_sum":
            nums = certificate["numbers"]
            target = certificate["target"]
            idx = certificate["indices"]
            if not all(isinstance(i, int) and 0 <= i < len(nums) for i in idx):
                return _bad("indices out of range")
            total = sum(nums[i] for i in idx)
            return (_ok(f"selected subset sums to {total} = target {target}.")
                    if total == target else
                    _no(f"sum {total} ≠ target {target}."))

        if kind == "graph_coloring":
            edges = certificate["edges"]
            colors = certificate["colors"]
            coloring = {str(k): v for k, v in certificate["coloring"].items()}
            for u, v in edges:
                cu, cv = coloring.get(str(u)), coloring.get(str(v))
                if cu is None or cv is None:
                    return _bad(f"no color for vertex {u} or {v}")
                if not (0 <= cu < colors and 0 <= cv < colors):
                    return _no(f"color out of range ({u}:{cu}, {v}:{cv}, colors={colors}).")
                if cu == cv:
                    return _no(f"adjacent {u}-{v} share the same color ({cu}) — invalid coloring.")
            return _ok(f"no edge among {len(edges)} is monochromatic; coloring is valid.")

        if kind == "solution":
            env = {str(certificate["symbol"]): _num(certificate["value"])}
            residual = _evaluate(certificate["expression"], env)
            zero, exact = _is_zero(residual)
            note = "" if exact else " (numeric, tolerance)"
            return (_ok(f"residual 0{note}: the value satisfies the equation.", exact)
                    if zero else
                    _no(f"residual {residual} ≠ 0{note}: the value is not a solution.", exact))

        if kind == "not_equal":
            env = _env(certificate["point"])
            lv = _evaluate(certificate["left"], env)
            rv = _evaluate(certificate["right"], env)
            zero, exact = _is_zero(lv - rv)
            note = "" if exact else " (numeric)"
            return (_no(f"equal at the point ({lv} = {rv}){note}: counterexample INVALID.", exact)
                    if zero else
                    _ok(f"at the point {lv} ≠ {rv}{note}: counterexample verified.", exact))

        if kind == "inequality_counterexample":
            env = _env(certificate["point"])
            val = _evaluate(certificate["expression"], env)
            rel = certificate.get("relation", ">=")
            fval = float(val)
            violated = fval < -_TOL if rel == ">=" else (
                fval > _TOL if rel == "<=" else None)
            if violated is None:
                return _bad(f"unsupported relation: {rel} (>= or <=)")
            exact = isinstance(val, Fraction)
            note = "" if exact else " (numeric)"
            return (_ok(f"expression value {val} VIOLATES '{rel} 0'{note}: "
                        f"counterexample verified.", exact)
                    if violated else
                    _no(f"expression value {val} does not violate '{rel} 0'{note}: "
                        f"counterexample invalid.", exact))

        return _bad(f"unknown certificate kind: {kind!r}")
    except (KeyError, TypeError) as exc:
        return _bad(f"missing/corrupt field: {exc}")
    except _CertError as exc:
        return _bad(f"evaluation error: {exc}")
    except (ValueError, ZeroDivisionError) as exc:
        return _bad(f"numeric error: {exc}")
