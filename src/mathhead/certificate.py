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
- matrix_product    · {a, b, product}               (A·B == product)
- matrix_inverse    · {matrix, inverse}             (A·inverse == I)
- linear_system     · {matrix, rhs, solution}       (A·x == b)
- factorization     · {n, factors: [[p, e], ...]}   (∏ pᵉ == n AND each p prime)
- bezout_gcd        · {a, b, g, x, y}               (g = a·x + b·y, g|a, g|b ⟹ g = gcd)
- modular_inverse   · {a, m, inverse}               ((a·inverse) mod m == 1)
- chinese_remainder · {moduli, residues, x}         (x ≡ residues[i] (mod moduli[i]))
- expectation       · {values, probabilities, expectation}  (Σp == 1 AND Σ pᵢ·vᵢ == E)
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


# --- I4 stdlib helpers: exact matrix + integer arithmetic (no z3/sympy) ---- #
_PRIME_BOUND = 10 ** 12          # trial-division confirms primality up to here


def _int(value: Any) -> int:
    """Coerces to a Python int (exact); rejects non-integers honestly."""
    n = _num(value)
    if isinstance(n, Fraction) and n.denominator == 1:
        return int(n.numerator)
    raise _CertError(f"expected an integer: {value!r}")


def _is_prime_trial(n: int) -> tuple[bool | None, bool]:
    """Deterministic stdlib primality by trial division. (is_prime|None, decided?)."""
    if n < 2:
        return False, True
    if n < 4:
        return True, True
    if n % 2 == 0:
        return False, True
    if n > _PRIME_BOUND:                 # honest: too large to confirm by trial division
        return None, False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False, True
        i += 2
    return True, True


def _cert_matrix(rows: Any) -> list[list[Any]]:
    """Parses a matrix to exact (Fraction) / float cells; rejects ragged/empty input."""
    if not isinstance(rows, list) or not rows or not all(isinstance(r, list) and r for r in rows):
        raise _CertError("matrix must be a non-empty list of non-empty rows")
    width = len(rows[0])
    if any(len(r) != width for r in rows):
        raise _CertError("ragged matrix (rows of unequal length)")
    return [[_num(c) for c in r] for r in rows]


def _matmul(A: list[list[Any]], B: list[list[Any]]) -> list[list[Any]]:
    if len(A[0]) != len(B):
        raise _CertError(f"dimension mismatch: {len(A)}×{len(A[0])} · {len(B)}×{len(B)}")
    return [[sum((A[i][k] * B[k][j] for k in range(len(B))), Fraction(0))
             for j in range(len(B[0]))] for i in range(len(A))]


def _matrix_equal(A: list[list[Any]], B: list[list[Any]]) -> tuple[bool, bool]:
    """(equal, exact) — cell-by-cell; Fraction → exact, float → tolerance."""
    if len(A) != len(B) or len(A[0]) != len(B[0]):
        return False, True
    exact = True
    for i in range(len(A)):
        for j in range(len(A[0])):
            zero, ex = _is_zero(A[i][j] - B[i][j])
            exact = exact and ex
            if not zero:
                return False, exact
    return True, exact


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

        # --- I4: matrix certificates (checking is cheaper than solving) ---
        if kind == "matrix_product":
            A = _cert_matrix(certificate["a"])
            B = _cert_matrix(certificate["b"])
            claimed = _cert_matrix(certificate["product"])
            prod = _matmul(A, B)
            equal, exact = _matrix_equal(prod, claimed)
            note = "" if exact else " (numeric)"
            return (_ok(f"A·B equals the claimed {len(prod)}×{len(prod[0])} product{note}.", exact)
                    if equal else
                    _no(f"A·B does NOT equal the claimed product{note}: the result is wrong.", exact))

        if kind == "matrix_inverse":
            A = _cert_matrix(certificate["matrix"])
            inv = _cert_matrix(certificate["inverse"])
            if len(A) != len(A[0]):
                return _bad("matrix must be square for an inverse")
            prod = _matmul(A, inv)
            n = len(A)
            identity = [[Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]
            equal, exact = _matrix_equal(prod, identity)
            note = "" if exact else " (numeric)"
            return (_ok(f"A·inverse == I ({n}×{n}){note}: the inverse is verified.", exact)
                    if equal else
                    _no(f"A·inverse != I{note}: the claimed inverse is wrong.", exact))

        if kind == "linear_system":
            A = _cert_matrix(certificate["matrix"])
            rhs = [_num(v) for v in certificate["rhs"]]
            sol = [_num(v) for v in certificate["solution"]]
            if len(A[0]) != len(sol):
                return _bad(f"solution length {len(sol)} != number of columns {len(A[0])}")
            if len(A) != len(rhs):
                return _bad(f"rhs length {len(rhs)} != number of rows {len(A)}")
            exact = True
            for i in range(len(A)):
                dot = sum((A[i][k] * sol[k] for k in range(len(sol))), Fraction(0))
                zero, ex = _is_zero(dot - rhs[i])
                exact = exact and ex
                if not zero:
                    note = "" if ex else " (numeric)"
                    return _no(f"row {i}: A·x = {dot} != b = {rhs[i]}{note}: not a solution.", exact)
            note = "" if exact else " (numeric)"
            return _ok(f"A·x == b for all {len(A)} rows{note}: the solution is verified.", exact)

        # --- I4: number-theory certificates ---
        if kind == "factorization":
            n = _int(certificate["n"])
            factors = certificate["factors"]
            product = 1
            for pair in factors:
                p, e = _int(pair[0]), _int(pair[1])
                if e < 1:
                    return _bad(f"exponent must be >= 1 (got {e})")
                is_p, decided = _is_prime_trial(p)
                if not decided:
                    return _bad(f"primality of {p} exceeds the trial-division bound "
                                f"({_PRIME_BOUND}); cannot confirm independently.")
                if not is_p:
                    return _no(f"{p} is NOT prime: this is not a prime factorization.")
                product *= p ** e
            return (_ok(f"the prime powers multiply to {n}: factorization verified.")
                    if product == n else
                    _no(f"the factors multiply to {product} != {n}: factorization is wrong."))

        if kind == "bezout_gcd":
            a, b = _int(certificate["a"]), _int(certificate["b"])
            g = _int(certificate["g"])
            x, y = _int(certificate["x"]), _int(certificate["y"])
            if g <= 0:
                return _no(f"g = {g} must be positive to be a gcd.")
            if a * x + b * y != g:
                return _no(f"a·x + b·y = {a * x + b * y} != g = {g}: Bézout identity fails.")
            if a % g != 0 or b % g != 0:
                return _no(f"g = {g} does not divide both a={a} and b={b}: not a common divisor.")
            return _ok(f"g = {g} = {a}·{x} + {b}·{y} and divides both ⟹ gcd verified.")

        if kind == "modular_inverse":
            a, m = _int(certificate["a"]), _int(certificate["m"])
            inv = _int(certificate["inverse"])
            if m <= 0:
                return _bad(f"modulus must be positive (got {m})")
            return (_ok(f"(a·inverse) mod m = ({a}·{inv}) mod {m} = 1: modular inverse verified.")
                    if (a * inv) % m == 1 % m else
                    _no(f"(a·inverse) mod m = {(a * inv) % m} != 1: the claimed inverse is wrong."))

        if kind == "chinese_remainder":
            moduli = [_int(v) for v in certificate["moduli"]]
            residues = [_int(v) for v in certificate["residues"]]
            x = _int(certificate["x"])
            if len(moduli) != len(residues):
                return _bad("moduli and residues must have equal length")
            for mod, res in zip(moduli, residues):
                if mod <= 0:
                    return _bad(f"modulus must be positive (got {mod})")
                if x % mod != res % mod:
                    return _no(f"x={x} mod {mod} = {x % mod} != {res % mod}: congruence fails.")
            return _ok(f"x = {x} satisfies all {len(moduli)} congruences: CRT solution verified.")

        # --- I4: probability certificate ---
        if kind == "expectation":
            values = [_num(v) for v in certificate["values"]]
            probs = [_num(p) for p in certificate["probabilities"]]
            claimed = _num(certificate["expectation"])
            if len(values) != len(probs):
                return _bad("values and probabilities must have equal length")
            psum = sum(probs, Fraction(0)) if all(isinstance(p, Fraction) for p in probs) else sum(map(float, probs))
            one_ok, ex1 = _is_zero(psum - 1)
            if not one_ok:
                return _no(f"probabilities sum to {psum} != 1: not a valid distribution.")
            exp = sum((values[i] * probs[i] for i in range(len(values))),
                      Fraction(0) if all(isinstance(v, Fraction) for v in values + probs) else 0)
            zero, ex2 = _is_zero(exp - claimed)
            exact = ex1 and ex2
            note = "" if exact else " (numeric)"
            return (_ok(f"Σp = 1 and Σ pᵢ·vᵢ = {exp} = claimed{note}: expectation verified.", exact)
                    if zero else
                    _no(f"Σ pᵢ·vᵢ = {exp} != claimed {claimed}{note}: the expectation is wrong.", exact))

        return _bad(f"unknown certificate kind: {kind!r}")
    except (KeyError, TypeError, IndexError) as exc:
        return _bad(f"missing/corrupt field: {exc}")
    except _CertError as exc:
        return _bad(f"evaluation error: {exc}")
    except (ValueError, ZeroDivisionError) as exc:
        return _bad(f"numeric error: {exc}")
