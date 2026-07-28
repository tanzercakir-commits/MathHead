"""
mathhead.compute — Symbolic computation layer (CAS, SymPy-based).

v2: `simplify`, `solve`, `differentiate`, `integrate`. SEPARATE from the logic
kernel (Z3); the goal here is **computation**, not proof.

Safety (PRINCIPLES: no silent eval): input is again parsed with Python `ast`,
filtered through a **whitelist**, and converted to a SymPy object. Unsafe paths
like `sympify`/`eval` are NOT used. Unlike the logic layer, here `*`/`**`
(exponent) and nonlinear expressions are allowed (necessary for computation).

Return contract: `ComputeResult` (status ok|error, operation, result, ...).
Undecidability/failure is reported honestly (e.g. if SymPy cannot solve an
integral it returns an unevaluated `Integral(...)` — nothing is hidden).
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import Any

import sympy

MAX_EXPRESSION_CHARS: int = 4_000

# Allowed functions (ast Call -> SymPy). Whitelist; everything else is rejected.
_FUNCS = {
    "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
    "asin": sympy.asin, "acos": sympy.acos, "atan": sympy.atan,
    "sinh": sympy.sinh, "cosh": sympy.cosh, "tanh": sympy.tanh,
    "exp": sympy.exp, "log": sympy.log, "sqrt": sympy.sqrt, "Abs": sympy.Abs,
}

# Recognized mathematical constants: a bare name matching one of these is the
# CONSTANT, not a free symbol (so `pi`, `E`, `I` mean π, e, and the imaginary unit).
# Variable names declared via `_symbol` are unaffected — a declared variable stays one.
_CONSTS = {"pi": sympy.pi, "E": sympy.E, "I": sympy.I}


class ComputeError(ValueError):
    """Input-grammar/expression violation. A clear error, no silent assumptions."""


@dataclass
class ComputeResult:
    status: str                       # "ok" | "error"
    operation: str                    # simplify | solve | differentiate | integrate
    result: Any = None                # str or list[str]
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
# ast -> SymPy (whitelist)
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
        raise ComputeError(f"unsupported operator: {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        val = _to_sympy(node.operand, syms)
        if isinstance(node.op, ast.USub):
            return -val
        if isinstance(node.op, ast.UAdd):
            return val
        raise ComputeError(f"unsupported unary operator: {type(node.op).__name__}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ComputeError(f"allowed functions: {', '.join(sorted(_FUNCS))}")
        if node.keywords or any(isinstance(a, ast.Starred) for a in node.args):
            raise ComputeError("no keyword/star arguments in a function call")
        return _FUNCS[node.func.id](*[_to_sympy(a, syms) for a in node.args])
    if isinstance(node, ast.Name):
        if node.id in _CONSTS:
            return _CONSTS[node.id]
        if node.id not in syms:
            syms[node.id] = sympy.Symbol(node.id)
        return syms[node.id]
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise ComputeError("boolean constant is invalid in computation")
        if isinstance(node.value, int):
            return sympy.Integer(node.value)
        if isinstance(node.value, float):
            return sympy.Float(node.value)
        raise ComputeError(f"unsupported constant: {node.value!r}")
    raise ComputeError(f"disallowed expression node: {type(node).__name__}")


def _parse(expression: str, syms: dict[str, Any]) -> Any:
    if not isinstance(expression, str) or not expression.strip():
        raise ComputeError("empty or invalid expression")
    if len(expression) > MAX_EXPRESSION_CHARS:
        raise ComputeError(f"expression too long (>{MAX_EXPRESSION_CHARS} characters)")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ComputeError(f"syntax error: {exc.msg}") from exc
    body = tree.body
    if isinstance(body, ast.Compare):  # equation: a == b
        if len(body.ops) == 1 and isinstance(body.ops[0], ast.Eq):
            return sympy.Eq(_to_sympy(body.left, syms), _to_sympy(body.comparators[0], syms))
        raise ComputeError("only a single '==' equality is supported")
    return _to_sympy(body, syms)


def _symbol(name: str, syms: dict[str, Any]) -> Any:
    if not isinstance(name, str) or not name.isidentifier():
        raise ComputeError(f"invalid variable name: {name!r}")
    if name not in syms:
        syms[name] = sympy.Symbol(name)
    return syms[name]


def _error(operation: str, msg: str, t0: float, code: str = "PARSE_ERROR") -> ComputeResult:
    return ComputeResult("error", operation, None, msg, code, _meta(t0))


# --------------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------------- #
def simplify(expression: str) -> ComputeResult:
    """Simplifies an expression algebraically."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
    except ComputeError as exc:
        return _error("simplify", str(exc), t0)
    try:
        result = sympy.simplify(expr)
    except Exception as exc:  # noqa: BLE001 - SymPy failure is reported honestly
        return _error("simplify", f"could not simplify: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "simplify", str(result), f"'{expression}' simplified.", "OK", _meta(t0))


def solve(equation: str, symbol: str) -> ComputeResult:
    """Solves an equation (e.g. 'x**2 == 4', or 'x**2 - 4' assuming '=0')."""
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
        return _error("solve", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "solve", result,
        f"found {len(result)} solution(s) for '{symbol}'.", "OK", _meta(t0),
    )


def differentiate(expression: str, symbol: str, order: int = 1) -> ComputeResult:
    """Takes the order-th derivative of the expression with respect to `symbol`."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("derivative order must be an integer ≥ 1")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
    except ComputeError as exc:
        return _error("differentiate", str(exc), t0)
    try:
        result = sympy.diff(expr, var, order)
    except Exception as exc:  # noqa: BLE001
        return _error("differentiate", f"could not differentiate: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "differentiate", str(result),
        f"d^{order}/d{symbol}^{order} ('{expression}') computed.", "OK", _meta(t0),
    )


def integrate(expression: str, symbol: str) -> ComputeResult:
    """Takes the indefinite integral of the expression w.r.t. `symbol` (+C not shown).

    If SymPy cannot solve the integral in closed form it returns an unevaluated
    `Integral(...)` — this is not hidden; it is honestly reflected in the result.
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
        return _error("integrate", f"could not integrate: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult(
        "ok", "integrate", str(result),
        f"∫ '{expression}' d{symbol} computed (+C).", "OK", _meta(t0),
    )


def _parse_point(point: str, syms: dict[str, Any]) -> Any:
    """Limit/series point: recognizes infinities (oo/inf), parses the rest via the grammar."""
    p = point.strip().lower()
    if p in ("oo", "inf", "infinity", "+oo", "+inf"):
        return sympy.oo
    if p in ("-oo", "-inf", "-infinity"):
        return -sympy.oo
    return _parse(point, syms)


def limit(expression: str, symbol: str, point: str = "0", direction: str = "both") -> ComputeResult:
    """Limit of the expression as `symbol` -> `point`. direction: both / + / - (one-sided).

    `point` may be infinite: "oo" or "-oo".
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    dir_map = {"both": "+-", "+": "+", "-": "-", "+-": "+-"}
    try:
        if direction not in dir_map:
            raise ComputeError("direction must be 'both', '+' or '-'")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
    except ComputeError as exc:
        return _error("limit", str(exc), t0)
    try:
        result = sympy.limit(expr, var, pt, dir_map[direction])
    except Exception as exc:  # noqa: BLE001
        return _error("limit", f"could not compute limit: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "limit", str(result),
                         f"lim {symbol}→{point} '{expression}' = {result}.", "OK", _meta(t0))


def series(expression: str, symbol: str, point: str = "0", order: int = 6) -> ComputeResult:
    """Taylor/series expansion of the expression around `symbol` = `point` to order `order`."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("order must be an integer ≥ 1")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
    except ComputeError as exc:
        return _error("series", str(exc), t0)
    try:
        result = expr.series(var, pt, order).removeO()
    except Exception as exc:  # noqa: BLE001
        return _error("series", f"could not expand series: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "series", str(result),
                         f"series of '{expression}' ({symbol}={point}, order {order}).", "OK", _meta(t0))


def solve_system(equations: list[str], symbols: list[str]) -> ComputeResult:
    """Solves a SYSTEM of equations for multiple variables.

    Equations may be `a == b` (Eq) or a plain expression assuming `=0`.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(equations, list) or not equations:
            raise ComputeError("the equation list cannot be empty")
        if not isinstance(symbols, list) or not symbols:
            raise ComputeError("the variable list cannot be empty")
        eqs = [_parse(e, syms) for e in equations]
        variables = [_symbol(s, syms) for s in symbols]
    except ComputeError as exc:
        return _error("solve_system", str(exc), t0)
    try:
        sols = sympy.solve(eqs, variables, dict=True)
        result = [{str(k): str(v) for k, v in sol.items()} for sol in sols]
    except Exception as exc:  # noqa: BLE001
        return _error("solve_system", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_system", result,
                         f"found {len(result)} solution(s).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Linear algebra (matrices) — SymPy Matrix. Input: list[list[str]]; each cell
# is again filtered by the ast whitelist (symbolic cells allowed: [["a","b"],["c","d"]]).
# --------------------------------------------------------------------------- #
def _parse_matrix(matrix: list[list[str]], syms: dict[str, Any]) -> Any:
    """list[list[str]] -> sympy.Matrix. Validated as rectangular + non-empty."""
    if not isinstance(matrix, list) or not matrix:
        raise ComputeError("matrix cannot be empty")
    rows = []
    width: int | None = None
    for row in matrix:
        if not isinstance(row, list) or not row:
            raise ComputeError("each row must be a non-empty list")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ComputeError("all rows must have the same length (rectangular)")
        rows.append([_parse(str(cell), syms) for cell in row])
    return sympy.Matrix(rows)


def determinant(matrix: list[list[str]]) -> ComputeResult:
    """Determinant of a square matrix (symbolic cells allowed)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("determinant requires a square matrix")
    except ComputeError as exc:
        return _error("determinant", str(exc), t0)
    try:
        result = sympy.simplify(M.det())
    except Exception as exc:  # noqa: BLE001
        return _error("determinant", f"could not compute determinant: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "determinant", str(result),
                         f"det = {result}.", "OK", _meta(t0))


def matrix_inverse(matrix: list[list[str]]) -> ComputeResult:
    """Inverse of a square matrix (A⁻¹). If singular (det=0) it honestly returns an error."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("inverse requires a square matrix")
    except ComputeError as exc:
        return _error("matrix_inverse", str(exc), t0)
    try:
        det = sympy.simplify(M.det())
        if det == 0:
            return _error("matrix_inverse",
                          "matrix is not invertible (singular, det = 0)",
                          t0, "COMPUTE_FAILED")
        inv = M.inv()
        result = [[str(sympy.simplify(inv[i, j])) for j in range(inv.cols)]
                  for i in range(inv.rows)]
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_inverse", f"could not invert: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_inverse", result,
                         "A⁻¹ computed.", "OK", _meta(t0))


def eigenvalues(matrix: list[list[str]]) -> ComputeResult:
    """Eigenvalues of a square matrix + algebraic multiplicity.

    Returns: `[{"value": ..., "multiplicity": n}, ...]` — sorted by str
    (determinism; ADR-0019). Complex/irrational values are returned in exact form.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("eigenvalues require a square matrix")
    except ComputeError as exc:
        return _error("eigenvalues", str(exc), t0)
    try:
        ev = M.eigenvals()  # {value: multiplicity}
        result = sorted(
            ({"value": str(val), "multiplicity": int(mult)} for val, mult in ev.items()),
            key=lambda d: d["value"],
        )
    except Exception as exc:  # noqa: BLE001
        return _error("eigenvalues", f"could not compute eigenvalues: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "eigenvalues", result,
                         f"{len(result)} distinct eigenvalue(s).", "OK", _meta(t0))


def matrix_rank(matrix: list[list[str]]) -> ComputeResult:
    """Rank of a matrix (number of linearly independent rows/columns). Need not be square."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("matrix_rank", str(exc), t0)
    try:
        result = int(M.rank())
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_rank", f"could not compute rank: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_rank", result,
                         f"rank = {result} ({M.rows}×{M.cols} matrix).", "OK", _meta(t0))


def _mat_out(M: Any) -> list[list[str]]:
    """SymPy Matrix -> list[list[str]] (cells simplified)."""
    return [[str(sympy.simplify(M[i, j])) for j in range(M.cols)] for i in range(M.rows)]


def matrix_multiply(a: list[list[str]], b: list[list[str]]) -> ComputeResult:
    """Product of two matrices A·B. If inner dimensions mismatch, an honest error."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(a, syms)
        B = _parse_matrix(b, syms)
        if A.cols != B.rows:
            raise ComputeError(
                f"dimension mismatch: A {A.rows}×{A.cols} · B {B.rows}×{B.cols} "
                f"(A columns = B rows required)"
            )
    except ComputeError as exc:
        return _error("matrix_multiply", str(exc), t0)
    try:
        result = _mat_out(A * B)
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_multiply", f"could not multiply: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_multiply", result,
                         f"A·B = {A.rows}×{B.cols} matrix.", "OK", _meta(t0))


def matrix_solve(matrix: list[list[str]], rhs: list[str]) -> ComputeResult:
    """Solves the linear system `A x = b` in matrix form.

    Returns: a list of solution dicts (`x0, x1, ...`). Empty list = **no solution**
    (inconsistent); free variables appear parametrically (honest).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(matrix, syms)
        if not isinstance(rhs, list) or not rhs:
            raise ComputeError("the right-hand side (b) cannot be empty")
        if len(rhs) != A.rows:
            raise ComputeError(
                f"len(b) must equal the number of rows of A (A {A.rows}×{A.cols}, b {len(rhs)})"
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
        return _error("matrix_solve", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    if not result:
        return ComputeResult("ok", "matrix_solve", [],
                             "no solution (inconsistent system).", "OK", _meta(t0))
    free = sorted({str(s) for tup in tuples for expr in tup for s in expr.free_symbols})
    note = f" (free: {', '.join(free)} → parametric)" if free else ""
    return ComputeResult("ok", "matrix_solve", result,
                         f"solution found{note}.", "OK", _meta(t0))


def eigenvectors(matrix: list[list[str]]) -> ComputeResult:
    """Eigenvalue + algebraic multiplicity + eigenvector(s). Sorted by eigenvalue (determinism)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("eigenvectors require a square matrix")
    except ComputeError as exc:
        return _error("eigenvectors", str(exc), t0)
    try:
        data = M.eigenvects()  # [(eigenvalue, multiplicity, [column vector(s)])]
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
        return _error("eigenvectors", f"could not compute eigenvectors: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "eigenvectors", result,
                         f"eigenvectors for {len(result)} distinct eigenvalue(s).", "OK", _meta(t0))


def rref(matrix: list[list[str]]) -> ComputeResult:
    """Reduced row echelon form + pivot columns."""
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
        return _error("rref", f"could not compute rref: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "rref", result,
                         f"pivot columns: {result['pivots']}.", "OK", _meta(t0))


def nullspace(matrix: list[list[str]]) -> ComputeResult:
    """A basis of the null space (kernel). Empty list = only zero (trivial)."""
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
        return _error("nullspace", f"could not compute null space: {exc}", t0, "COMPUTE_FAILED")
    note = "only the zero vector (trivial)" if not result else f"{len(result)} basis vector(s)"
    return ComputeResult("ok", "nullspace", result, f"null space: {note}.", "OK", _meta(t0))


def lu_decomposition(matrix: list[list[str]]) -> ComputeResult:
    """LU decomposition: A = P·L·U. Returns: `L`, `U` matrices + `perm` (row swaps)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("LU requires a square matrix")
    except ComputeError as exc:
        return _error("lu_decomposition", str(exc), t0)
    try:
        L, U, perm = M.LUdecomposition()
        result = {"L": _mat_out(L), "U": _mat_out(U), "perm": [list(p) for p in perm]}
    except Exception as exc:  # noqa: BLE001
        return _error("lu_decomposition", f"could not LU-decompose: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "lu_decomposition", result,
                         "A = P·L·U decomposition.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Number theory — over INTEGERS. Input is again filtered by the ast whitelist
# (e.g. "2**10" allowed); if the result is not an integer it is rejected.
# --------------------------------------------------------------------------- #
def _parse_int(value: Any, name: str = "value") -> int:
    """Safely converts the input to an integer. Symbols / non-integers are rejected."""
    syms: dict[str, Any] = {}
    expr = _parse(str(value), syms)
    if syms:
        raise ComputeError(f"{name} must be an integer (cannot contain a symbol)")
    val = sympy.simplify(expr)
    if not getattr(val, "is_Integer", False):
        raise ComputeError(f"{name} must be an integer")
    return int(val)


def gcd(a: Any, b: Any) -> ComputeResult:
    """Greatest common divisor of two integers."""
    t0 = time.perf_counter()
    try:
        A, B = _parse_int(a, "a"), _parse_int(b, "b")
    except ComputeError as exc:
        return _error("gcd", str(exc), t0)
    result = int(sympy.igcd(A, B))
    return ComputeResult("ok", "gcd", result, f"gcd({A}, {B}) = {result}.", "OK", _meta(t0))


def lcm(a: Any, b: Any) -> ComputeResult:
    """Least common multiple of two integers."""
    t0 = time.perf_counter()
    try:
        A, B = _parse_int(a, "a"), _parse_int(b, "b")
    except ComputeError as exc:
        return _error("lcm", str(exc), t0)
    result = int(sympy.ilcm(A, B))
    return ComputeResult("ok", "lcm", result, f"lcm({A}, {B}) = {result}.", "OK", _meta(t0))


def is_prime(n: Any) -> ComputeResult:
    """Is `n` prime? (deterministic primality test — SymPy `isprime`)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
    except ComputeError as exc:
        return _error("is_prime", str(exc), t0)
    result = bool(sympy.isprime(N))
    return ComputeResult("ok", "is_prime", result,
                         f"{N} {'is prime' if result else 'is not prime'}.", "OK", _meta(t0))


def factorize(n: Any) -> ComputeResult:
    """Factorizes `n` into primes. Returns: `[{prime, exponent}, ...]` (ascending)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 1:
            raise ComputeError("a positive integer is required (n ≥ 1)")
    except ComputeError as exc:
        return _error("factorize", str(exc), t0)
    try:
        fac = sympy.factorint(N)
        result = [{"prime": int(p), "exponent": int(e)} for p, e in sorted(fac.items())]
    except Exception as exc:  # noqa: BLE001
        return _error("factorize", f"could not factorize: {exc}", t0, "COMPUTE_FAILED")
    pretty = " · ".join(f"{d['prime']}^{d['exponent']}" if d["exponent"] > 1 else str(d["prime"])
                        for d in result) or "1 (no prime factors)"
    return ComputeResult("ok", "factorize", result, f"{N} = {pretty}.", "OK", _meta(t0))


def modular_inverse(a: Any, m: Any) -> ComputeResult:
    """Multiplicative inverse of `a` modulo `m`. If none (gcd(a,m)≠1), an honest error."""
    t0 = time.perf_counter()
    try:
        A, M = _parse_int(a, "a"), _parse_int(m, "m")
        if M < 2:
            raise ComputeError("modulus m must be ≥ 2")
    except ComputeError as exc:
        return _error("modular_inverse", str(exc), t0)
    try:
        result = int(sympy.mod_inverse(A, M))
    except ValueError:
        return _error("modular_inverse",
                      f"{A} has no inverse mod {M} (gcd(a, m) ≠ 1)", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "modular_inverse", result,
                         f"{A}⁻¹ ≡ {result} (mod {M}).", "OK", _meta(t0))


def chinese_remainder(moduli: list[Any], residues: list[Any]) -> ComputeResult:
    """Chinese Remainder Theorem (CRT): solves x ≡ residues[i] (mod moduli[i]).

    Returns: `{"x": ..., "modulus": ...}` (smallest non-negative solution +
    combined modulus). If the system has no solution (incompatible moduli), an honest error.
    """
    t0 = time.perf_counter()
    try:
        if not isinstance(moduli, list) or not isinstance(residues, list):
            raise ComputeError("moduli and residues must be lists")
        if len(moduli) != len(residues) or not moduli:
            raise ComputeError("moduli and residues must have equal, non-empty length")
        mods = [_parse_int(x, "modulus") for x in moduli]
        res = [_parse_int(x, "residue") for x in residues]
    except ComputeError as exc:
        return _error("chinese_remainder", str(exc), t0)
    from sympy.ntheory.modular import crt as _crt
    out = _crt(mods, res)
    if out is None:
        return _error("chinese_remainder",
                      "no solution (moduli are incompatible)", t0, "COMPUTE_FAILED")
    x, mod = int(out[0]), int(out[1])
    return ComputeResult("ok", "chinese_remainder", {"x": x, "modulus": mod},
                         f"x ≡ {x} (mod {mod}).", "OK", _meta(t0))


def linear_diophantine(a: Any, b: Any, c: Any) -> ComputeResult:
    """Solves the linear Diophantine equation `a·x + b·y = c` over INTEGERS.

    Returns: parametric solution(s) `[{"x": ..., "y": ...}]` (parameter `t_0`).
    Empty list = no integer solution (gcd(a,b) ∤ c) — honest.
    """
    t0 = time.perf_counter()
    try:
        A, B, C = _parse_int(a, "a"), _parse_int(b, "b"), _parse_int(c, "c")
        if A == 0 and B == 0:
            raise ComputeError("a and b cannot both be 0")
    except ComputeError as exc:
        return _error("linear_diophantine", str(exc), t0)
    try:
        x, y = sympy.symbols("x y")
        sols = sympy.diophantine(A * x + B * y - C)
        result = [{"x": str(t[0]), "y": str(t[1])} for t in sols]
    except Exception as exc:  # noqa: BLE001
        return _error("linear_diophantine", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    if not result:
        return ComputeResult("ok", "linear_diophantine", [],
                             f"no integer solution (gcd({A},{B}) ∤ {C}).", "OK", _meta(t0))
    return ComputeResult("ok", "linear_diophantine", result,
                         f"{A}x + {B}y = {C} parametric solution.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Combinatorics & discrete — permutations/combinations, factorial,
# integer partitions, closed-form solution of linear recurrences.
# --------------------------------------------------------------------------- #
def permutations(n: Any, k: Any) -> ComputeResult:
    """P(n, k) = n·(n-1)···(n-k+1) — ordered selection of `k` from `n` objects."""
    t0 = time.perf_counter()
    try:
        N, K = _parse_int(n, "n"), _parse_int(k, "k")
        if N < 0 or K < 0:
            raise ComputeError("n and k cannot be negative")
    except ComputeError as exc:
        return _error("permutations", str(exc), t0)
    result = int(sympy.ff(N, K))
    return ComputeResult("ok", "permutations", result, f"P({N}, {K}) = {result}.", "OK", _meta(t0))


def combinations(n: Any, k: Any) -> ComputeResult:
    """C(n, k) = binom(n, k) — unordered selection of `k` from `n` objects. 0 if k>n."""
    t0 = time.perf_counter()
    try:
        N, K = _parse_int(n, "n"), _parse_int(k, "k")
        if N < 0 or K < 0:
            raise ComputeError("n and k cannot be negative")
    except ComputeError as exc:
        return _error("combinations", str(exc), t0)
    result = int(sympy.binomial(N, K))
    return ComputeResult("ok", "combinations", result, f"C({N}, {K}) = {result}.", "OK", _meta(t0))


def factorial(n: Any) -> ComputeResult:
    """n! — product of the first `n` positive integers (0! = 1)."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 0:
            raise ComputeError("n cannot be negative (factorial undefined)")
    except ComputeError as exc:
        return _error("factorial", str(exc), t0)
    result = int(sympy.factorial(N))
    return ComputeResult("ok", "factorial", result, f"{N}! = {result}.", "OK", _meta(t0))


def partition_count(n: Any) -> ComputeResult:
    """p(n) — the number of ways to write `n` as a sum of positive integers."""
    t0 = time.perf_counter()
    try:
        N = _parse_int(n, "n")
        if N < 0:
            raise ComputeError("n cannot be negative")
    except ComputeError as exc:
        return _error("partition_count", str(exc), t0)
    from sympy.functions.combinatorial.numbers import partition as _partition
    result = int(_partition(N))
    return ComputeResult("ok", "partition_count", result,
                         f"p({N}) = {result} (partition count).", "OK", _meta(t0))


def solve_recurrence(recurrence: str, func: str = "y", var: str = "n",
                     initial: dict[str, Any] | None = None) -> ComputeResult:
    """Solves a linear recurrence relation to CLOSED FORM (`rsolve`).

    E.g. `recurrence="y(n) = y(n-1) + y(n-2)"`, `initial={"0":"0","1":"1"}` →
    the closed form of Fibonacci (Binet). If there is no closed form, an honest error.
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
            raise ComputeError("disallowed operator")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_tr(node.operand)
            if isinstance(node.op, ast.UAdd):
                return _tr(node.operand)
            raise ComputeError("disallowed unary operator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func:
                if len(node.args) != 1:
                    raise ComputeError("the recurrence function takes a single argument")
                return F(_tr(node.args[0]))
            if node.func.id in _FUNCS:
                return _FUNCS[node.func.id](*[_tr(a) for a in node.args])
            raise ComputeError(f"disallowed call: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id == var:
                return varsym
            raise ComputeError(f"disallowed name: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
        raise ComputeError("could not parse expression")

    try:
        src = str(recurrence).strip()
        if "=" in src and "==" not in src:      # assignment-style '=' -> '==' (for eval mode)
            src = src.replace("=", "==", 1)
        body = ast.parse(src, mode="eval").body
        if isinstance(body, ast.Compare):
            if len(body.ops) != 1 or not isinstance(body.ops[0], ast.Eq):
                raise ComputeError("only the '==' comparison is supported")
            expr = _tr(body.left) - _tr(body.comparators[0])
        else:
            expr = _tr(body)
        inits = {F(int(str(kk))): _parse(str(vv), {}) for kk, vv in initial.items()}
    except ComputeError as exc:
        return _error("solve_recurrence", str(exc), t0)
    except (SyntaxError, ValueError) as exc:
        return _error("solve_recurrence", f"could not parse: {exc}", t0)
    try:
        sol = sympy.rsolve(expr, F(varsym), inits)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_recurrence", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    if sol is None:
        return _error("solve_recurrence", "no closed form found", t0, "COMPUTE_FAILED")
    result = str(sympy.simplify(sol))
    return ComputeResult("ok", "solve_recurrence", result,
                         f"{func}({var}) = {result}.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Multivariable calculus — gradient/Jacobian/Hessian,
# definite integral, summation/product (Σ/Π), ordinary differential equation (ODE).
# --------------------------------------------------------------------------- #
def gradient(expression: str, variables: list[str]) -> ComputeResult:
    """∇f — partial derivatives of `expression` w.r.t. each variable (list)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or not variables:
            raise ComputeError("the variable list cannot be empty")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("gradient", str(exc), t0)
    try:
        result = [str(sympy.diff(expr, v)) for v in vs]
    except Exception as exc:  # noqa: BLE001
        return _error("gradient", f"could not compute gradient: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "gradient", result,
                         f"∇f (variables: {', '.join(variables)}).", "OK", _meta(t0))


def jacobian(expressions: list[str], variables: list[str]) -> ComputeResult:
    """Jacobian matrix — the partial-derivative matrix of a vector-valued function."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(expressions, list) or not expressions:
            raise ComputeError("the expression list cannot be empty")
        if not isinstance(variables, list) or not variables:
            raise ComputeError("the variable list cannot be empty")
        fs = [_parse(e, syms) for e in expressions]
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("jacobian", str(exc), t0)
    try:
        result = _mat_out(sympy.Matrix(fs).jacobian(vs))
    except Exception as exc:  # noqa: BLE001
        return _error("jacobian", f"could not compute Jacobian: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "jacobian", result,
                         f"J = {len(fs)}×{len(vs)} matrix.", "OK", _meta(t0))


def hessian(expression: str, variables: list[str]) -> ComputeResult:
    """Hessian matrix — the second partial-derivative matrix of a scalar function (symmetric)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or len(variables) < 1:
            raise ComputeError("at least one variable is required")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("hessian", str(exc), t0)
    try:
        result = _mat_out(sympy.hessian(expr, vs))
    except Exception as exc:  # noqa: BLE001
        return _error("hessian", f"could not compute Hessian: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "hessian", result,
                         f"H = {len(vs)}×{len(vs)} matrix.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# D1 — vector calculus: the differential operators (divergence / curl / Laplacian /
# directional derivative) + the line integral. Complements the existing gradient.
# --------------------------------------------------------------------------- #
def divergence(field: list[str], variables: list[str]) -> ComputeResult:
    """∇·F — divergence of a vector field: Σ ∂Fᵢ/∂xᵢ (field and variables match in length)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(field, list) or not field:
            raise ComputeError("the field cannot be empty")
        if not isinstance(variables, list) or len(variables) != len(field):
            raise ComputeError("field and variables must have equal length")
        fs = [_parse(e, syms) for e in field]
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("divergence", str(exc), t0)
    try:
        result = str(sympy.simplify(sum(sympy.diff(fs[i], vs[i]) for i in range(len(fs)))))
    except Exception as exc:  # noqa: BLE001
        return _error("divergence", f"could not compute divergence: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "divergence", result,
                         f"∇·F = {result} (variables: {', '.join(variables)}).", "OK", _meta(t0))


def curl(field: list[str], variables: list[str]) -> ComputeResult:
    """∇×F — curl of a 3-D vector field (requires exactly 3 components and 3 variables)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(field, list) or len(field) != 3:
            raise ComputeError("curl requires a 3-component field")
        if not isinstance(variables, list) or len(variables) != 3:
            raise ComputeError("curl requires exactly 3 variables")
        fx, fy, fz = (_parse(e, syms) for e in field)
        x, y, z = (_symbol(v, syms) for v in variables)
    except ComputeError as exc:
        return _error("curl", str(exc), t0)
    try:
        result = [
            str(sympy.simplify(sympy.diff(fz, y) - sympy.diff(fy, z))),
            str(sympy.simplify(sympy.diff(fx, z) - sympy.diff(fz, x))),
            str(sympy.simplify(sympy.diff(fy, x) - sympy.diff(fx, y))),
        ]
    except Exception as exc:  # noqa: BLE001
        return _error("curl", f"could not compute curl: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "curl", result,
                         f"∇×F = {result} (variables: {', '.join(variables)}).", "OK", _meta(t0))


def laplacian(expression: str, variables: list[str]) -> ComputeResult:
    """∇²f — Laplacian of a scalar field: Σ ∂²f/∂xᵢ²."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or not variables:
            raise ComputeError("the variable list cannot be empty")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
    except ComputeError as exc:
        return _error("laplacian", str(exc), t0)
    try:
        result = str(sympy.simplify(sum(sympy.diff(expr, v, 2) for v in vs)))
    except Exception as exc:  # noqa: BLE001
        return _error("laplacian", f"could not compute Laplacian: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "laplacian", result,
                         f"∇²f = {result} (variables: {', '.join(variables)}).", "OK", _meta(t0))


def directional_derivative(expression: str, variables: list[str],
                           direction: list[str]) -> ComputeResult:
    """Dᵤf — directional derivative ∇f·û along the NORMALIZED `direction`."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(variables, list) or not variables:
            raise ComputeError("the variable list cannot be empty")
        if not isinstance(direction, list) or len(direction) != len(variables):
            raise ComputeError("direction and variables must have equal length")
        expr = _parse(expression, syms)
        vs = [_symbol(v, syms) for v in variables]
        dvec = [_parse(d, syms) for d in direction]
    except ComputeError as exc:
        return _error("directional_derivative", str(exc), t0)
    try:
        norm = sympy.sqrt(sum(d ** 2 for d in dvec))
        if norm == 0:
            return _error("directional_derivative", "the direction vector cannot be zero",
                          t0, "COMPUTE_FAILED")
        grad = [sympy.diff(expr, v) for v in vs]
        raw = sum(grad[i] * dvec[i] for i in range(len(vs)))
        result = str(sympy.simplify(raw / norm))
    except Exception as exc:  # noqa: BLE001
        return _error("directional_derivative", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "directional_derivative", result,
                         f"Dᵤf = {result} (unit direction).", "OK", _meta(t0))


def line_integral(field: list[str], variables: list[str], parametrization: list[str],
                  param: str, lower: str, upper: str) -> ComputeResult:
    """∫_C F·dr — line integral of a vector field along a parametrized curve.

    Each variable = parametrization[i](param); the integrand is Σ Fᵢ(r(t))·(drᵢ/dt),
    integrated over `param` = lower..upper.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(field, list) or not field:
            raise ComputeError("the field cannot be empty")
        if not (isinstance(variables, list) and isinstance(parametrization, list)
                and len(variables) == len(field) == len(parametrization)):
            raise ComputeError("field, variables and parametrization must have equal length")
        fs = [_parse(e, syms) for e in field]
        vs = [_symbol(v, syms) for v in variables]
        t = _symbol(param, syms)
        rs = [_parse(p, syms) for p in parametrization]
        a = _parse_point(str(lower), syms)
        b = _parse_point(str(upper), syms)
    except ComputeError as exc:
        return _error("line_integral", str(exc), t0)
    try:
        subs = dict(zip(vs, rs))
        integrand = sum(fs[i].subs(subs) * sympy.diff(rs[i], t) for i in range(len(fs)))
        result = str(sympy.simplify(sympy.integrate(sympy.simplify(integrand), (t, a, b))))
    except Exception as exc:  # noqa: BLE001
        return _error("line_integral", f"could not compute line integral: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "line_integral", result,
                         f"∫_C F·dr = {result} ({param}: {lower}..{upper}).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# D2 — integral transforms: Laplace & inverse, Fourier & inverse, Z-transform.
# Each honestly reports COMPUTE_FAILED when SymPy cannot find a closed form (the
# unevaluated *Transform(...) / Sum(...) object is not passed off as an answer).
# --------------------------------------------------------------------------- #
def laplace_transform(expression: str, t_var: str = "t", s_var: str = "s") -> ComputeResult:
    """Laplace transform ℒ{f(t)}(s) = ∫₀^∞ f(t)·e^(−st) dt."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        t = _symbol(t_var, syms)
        s = _symbol(s_var, syms)
    except ComputeError as exc:
        return _error("laplace_transform", str(exc), t0)
    try:
        result = str(sympy.laplace_transform(expr, t, s, noconds=True))
    except Exception as exc:  # noqa: BLE001
        return _error("laplace_transform", f"could not transform: {exc}", t0, "COMPUTE_FAILED")
    if "LaplaceTransform(" in result:
        return _error("laplace_transform",
                      f"no closed-form Laplace transform found (result: {result}).",
                      t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "laplace_transform", result,
                         f"ℒ{{f}}({s_var}) = {result}.", "OK", _meta(t0))


def inverse_laplace_transform(expression: str, s_var: str = "s", t_var: str = "t") -> ComputeResult:
    """Inverse Laplace transform ℒ⁻¹{F(s)}(t) (unilateral → Heaviside factor is expected)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        s = _symbol(s_var, syms)
        t = _symbol(t_var, syms)
    except ComputeError as exc:
        return _error("inverse_laplace_transform", str(exc), t0)
    try:
        result = str(sympy.inverse_laplace_transform(expr, s, t))
    except Exception as exc:  # noqa: BLE001
        return _error("inverse_laplace_transform", f"could not transform: {exc}", t0, "COMPUTE_FAILED")
    if "InverseLaplaceTransform(" in result:
        return _error("inverse_laplace_transform",
                      f"no closed-form inverse found (result: {result}).", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "inverse_laplace_transform", result,
                         f"ℒ⁻¹{{F}}({t_var}) = {result}.", "OK", _meta(t0))


def fourier_transform(expression: str, x_var: str = "x", k_var: str = "k") -> ComputeResult:
    """Fourier transform (SymPy convention: ∫ f(x)·e^(−2πi·k·x) dx)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        x = _symbol(x_var, syms)
        k = _symbol(k_var, syms)
    except ComputeError as exc:
        return _error("fourier_transform", str(exc), t0)
    try:
        result = str(sympy.fourier_transform(expr, x, k))
    except Exception as exc:  # noqa: BLE001
        return _error("fourier_transform", f"could not transform: {exc}", t0, "COMPUTE_FAILED")
    if "FourierTransform(" in result:
        return _error("fourier_transform",
                      f"no closed-form Fourier transform found (result: {result}).",
                      t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "fourier_transform", result,
                         f"ℱ{{f}}({k_var}) = {result}.", "OK", _meta(t0))


def inverse_fourier_transform(expression: str, k_var: str = "k", x_var: str = "x") -> ComputeResult:
    """Inverse Fourier transform ℱ⁻¹{F(k)}(x)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        k = _symbol(k_var, syms)
        x = _symbol(x_var, syms)
    except ComputeError as exc:
        return _error("inverse_fourier_transform", str(exc), t0)
    try:
        result = str(sympy.inverse_fourier_transform(expr, k, x))
    except Exception as exc:  # noqa: BLE001
        return _error("inverse_fourier_transform", f"could not transform: {exc}", t0, "COMPUTE_FAILED")
    if "InverseFourierTransform(" in result:
        return _error("inverse_fourier_transform",
                      f"no closed-form inverse found (result: {result}).", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "inverse_fourier_transform", result,
                         f"ℱ⁻¹{{F}}({x_var}) = {result}.", "OK", _meta(t0))


def z_transform(expression: str, n_var: str = "n", z_var: str = "z") -> ComputeResult:
    """Unilateral Z-transform Z{x[n]}(z) = Σ_{n≥0} x[n]·z^(−n) (closed form + ROC)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        n = _symbol(n_var, syms)
        z = _symbol(z_var, syms)
    except ComputeError as exc:
        return _error("z_transform", str(exc), t0)
    roc = None
    try:
        raw = sympy.summation(expr * z ** (-n), (n, 0, sympy.oo))
        if isinstance(raw, sympy.Piecewise) and raw.args:
            first = raw.args[0]
            result = str(sympy.simplify(first.expr))
            roc = first.cond
        else:
            result = str(sympy.simplify(raw))
    except Exception as exc:  # noqa: BLE001
        return _error("z_transform", f"could not transform: {exc}", t0, "COMPUTE_FAILED")
    if "Sum(" in result:
        return _error("z_transform",
                      f"no closed-form Z-transform found (result: {result}).", t0, "COMPUTE_FAILED")
    note = f" (ROC: {roc})" if roc is not None else ""
    return ComputeResult("ok", "z_transform", result,
                         f"Z{{x[{n_var}]}}({z_var}) = {result}{note}.", "OK", _meta(t0))


def definite_integral(expression: str, symbol: str, lower: str, upper: str) -> ComputeResult:
    """Definite integral ∫ₐᵇ f dx. Bounds may be infinite ("oo"/"-oo")."""
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
        return _error("definite_integral", f"could not compute integral: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "definite_integral", result,
                         f"∫[{lower},{upper}] {expression} d{symbol} = {result}.", "OK", _meta(t0))


def summation(expression: str, index: str, lower: str, upper: str) -> ComputeResult:
    """Summation Σ — sum of `expression` for `index` = lower..upper (may be closed form)."""
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
        return _error("summation", f"could not compute sum: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "summation", result,
                         f"Σ({index}={lower}..{upper}) {expression} = {result}.", "OK", _meta(t0))


def product(expression: str, index: str, lower: str, upper: str) -> ComputeResult:
    """Product Π — product of `expression` for `index` = lower..upper."""
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
        return _error("product", f"could not compute product: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "product", result,
                         f"Π({index}={lower}..{upper}) {expression} = {result}.", "OK", _meta(t0))


def _parse_diffeq(equation: str, func_names: list[str], var_names: list[str]):
    """Parses an ODE/PDE string to `(expr = LHS − RHS, func_map, var_map)`.

    Shared by the whole differential-equation family. Derivatives: prime notation
    (`y'`, `y''` — w.r.t. the FIRST variable) or the marker `D(func, ...)` whose args
    are either an integer order (single-variable) or explicit variables (partials).
    Only the declared function/variable names, whitelisted elementary functions,
    arithmetic, and the constants `pi`/`E` are allowed; everything else is rejected.
    """
    import re
    var_map = {v: sympy.Symbol(v) for v in var_names}
    func_map = {f: sympy.Function(f) for f in func_names}
    primary = var_map[var_names[0]]

    def _applied(name: str) -> Any:
        return func_map[name](*[var_map[v] for v in var_names])

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
            raise ComputeError("disallowed operator")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_tr(node.operand)
            if isinstance(node.op, ast.UAdd):
                return _tr(node.operand)
            raise ComputeError("disallowed unary operator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid == "D":                       # derivative marker
                if not node.args or not isinstance(node.args[0], ast.Name) \
                        or node.args[0].id not in func_map:
                    raise ComputeError("D(...)'s first argument must be a declared function")
                base = _applied(node.args[0].id)
                rest = node.args[1:]
                if len(rest) == 1 and isinstance(rest[0], ast.Constant) \
                        and isinstance(rest[0].value, int) and not isinstance(rest[0].value, bool):
                    return sympy.Derivative(base, primary, rest[0].value)
                diffvars = []
                for a in rest:
                    if not (isinstance(a, ast.Name) and a.id in var_map):
                        raise ComputeError("D(...) differentiation args must be declared variables")
                    diffvars.append(var_map[a.id])
                if not diffvars:
                    raise ComputeError("D(...) needs an order or at least one variable")
                return sympy.Derivative(base, *diffvars)
            if fid in func_map:
                return _applied(fid)
            if fid in _FUNCS:
                return _FUNCS[fid](*[_tr(a) for a in node.args])
            raise ComputeError(f"disallowed call: {fid}")
        if isinstance(node, ast.Name):
            if node.id in var_map:
                return var_map[node.id]
            if node.id in func_map:
                return _applied(node.id)
            if node.id in _CONSTS:
                return _CONSTS[node.id]
            raise ComputeError(f"disallowed name: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
        raise ComputeError("could not parse expression")

    src = str(equation).strip()
    for name in func_names:                      # y', y'' -> D(y,1), D(y,2)
        src = re.sub(rf"\b{re.escape(name)}('+)",
                     lambda m, nm=name: f"D({nm},{len(m.group(1))})", src)
    if "=" in src and "==" not in src:
        src = src.replace("=", "==", 1)
    try:
        body = ast.parse(src, mode="eval").body
    except (SyntaxError, ValueError) as exc:
        raise ComputeError(f"could not parse: {exc}") from exc
    if isinstance(body, ast.Compare):
        if len(body.ops) != 1 or not isinstance(body.ops[0], ast.Eq):
            raise ComputeError("only the '==' comparison is supported")
        return _tr(body.left) - _tr(body.comparators[0]), func_map, var_map
    return _tr(body), func_map, var_map


def solve_ode(equation: str, func: str = "y", var: str = "x") -> ComputeResult:
    """Solves an ordinary differential equation (ODE). Derivative: `y'`, `y''` (prime).

    E.g. `"y' = y"` → `Eq(y(x), C1*exp(x))`; `"y'' + y = 0"` → C1·sin + C2·cos.
    If it cannot be solved (no closed form), an honest error.
    """
    t0 = time.perf_counter()
    try:
        expr, func_map, var_map = _parse_diffeq(equation, [func], [var])
    except ComputeError as exc:
        return _error("solve_ode", str(exc), t0)
    try:
        applied = func_map[func](var_map[var])
        sol = sympy.dsolve(expr, applied)
        result = [str(s) for s in sol] if isinstance(sol, list) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_ode", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_ode", result,
                         f"ODE solution ({func}({var})).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# D3 — differential equations II: ODE systems, initial/boundary value problems,
# ODE classification, and (limited) first-order linear PDEs. Built on the shared
# `_parse_diffeq`. Honest COMPUTE_FAILED whenever SymPy finds no closed form.
# --------------------------------------------------------------------------- #
def solve_ode_system(equations: list[str], functions: list[str],
                     var: str = "x") -> ComputeResult:
    """Solves a SYSTEM of ODEs for `functions` of a single variable `var`.

    E.g. `["f' = g", "g' = -f"]`, `["f", "g"]` → f, g as sin/cos combinations.
    """
    t0 = time.perf_counter()
    try:
        if not isinstance(equations, list) or not equations:
            raise ComputeError("the equation list cannot be empty")
        if not isinstance(functions, list) or not functions:
            raise ComputeError("the function list cannot be empty")
        parsed = []
        func_map = var_map = None
        for eq in equations:
            expr, func_map, var_map = _parse_diffeq(eq, functions, [var])
            parsed.append(sympy.Eq(expr, 0))
    except ComputeError as exc:
        return _error("solve_ode_system", str(exc), t0)
    try:
        applied = [func_map[f](var_map[var]) for f in functions]
        sol = sympy.dsolve(parsed, applied)
        result = [str(s) for s in sol] if isinstance(sol, (list, tuple)) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_ode_system", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_ode_system", result,
                         f"ODE system solution ({', '.join(functions)}).", "OK", _meta(t0))


def solve_ode_ivp(equation: str, conditions: list[str], func: str = "y",
                  var: str = "x") -> ComputeResult:
    """Solves an ODE with initial/boundary conditions (IVP **or** BVP).

    `conditions`: e.g. `["y(0)=1", "y'(0)=0"]` (initial) or `["y(0)=0", "y(1)=2"]`
    (boundary). A `pi` in a point is allowed (e.g. `y(pi/2)=1`).
    """
    import re
    t0 = time.perf_counter()
    csyms: dict[str, Any] = {}
    try:
        if not isinstance(conditions, list) or not conditions:
            raise ComputeError("at least one condition is required")
        expr, func_map, var_map = _parse_diffeq(equation, [func], [var])
        F, varsym = func_map[func], var_map[var]
        ics = {}
        for c in conditions:
            m = re.match(rf"^\s*{re.escape(func)}('*)\(([^)]+)\)\s*=\s*(.+)$", str(c).strip())
            if not m:
                raise ComputeError(f"bad condition (expected {func}(point)=value): {c!r}")
            order = len(m.group(1))
            point = _parse_point(m.group(2), csyms)
            value = _parse(m.group(3), csyms)
            key = (F(varsym).diff(varsym, order).subs(varsym, point) if order
                   else F(varsym).subs(varsym, point))
            ics[key] = value
    except ComputeError as exc:
        return _error("solve_ode_ivp", str(exc), t0)
    try:
        sol = sympy.dsolve(expr, F(varsym), ics=ics)
        result = [str(s) for s in sol] if isinstance(sol, list) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_ode_ivp", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_ode_ivp", result,
                         f"ODE solution with {len(conditions)} condition(s).", "OK", _meta(t0))


def classify_ode(equation: str, func: str = "y", var: str = "x") -> ComputeResult:
    """Returns SymPy's classification of the ODE — the applicable solution methods."""
    t0 = time.perf_counter()
    try:
        expr, func_map, var_map = _parse_diffeq(equation, [func], [var])
    except ComputeError as exc:
        return _error("classify_ode", str(exc), t0)
    try:
        kinds = list(sympy.classify_ode(expr, func_map[func](var_map[var])))
    except Exception as exc:  # noqa: BLE001
        return _error("classify_ode", f"could not classify: {exc}", t0, "COMPUTE_FAILED")
    if not kinds:
        return _error("classify_ode", "no known classification (honest).", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "classify_ode", kinds,
                         f"ODE classification ({len(kinds)} method(s); first: {kinds[0]}).",
                         "OK", _meta(t0))


def solve_pde(equation: str, func: str = "u", variables: list[str] | None = None) -> ComputeResult:
    """Solves a first-order linear PDE (SymPy `pdsolve`). Partials via `D(u, x)`, `D(u, y)`.

    HONEST scope: only the limited class SymPy's `pdsolve` supports (mostly first-order
    linear); anything else → `COMPUTE_FAILED`. E.g. `"D(u,x) + D(u,y) = 0"` → `u = F(x - y)`.
    """
    t0 = time.perf_counter()
    try:
        if not isinstance(variables, list) or len(variables) < 2:
            raise ComputeError("a PDE needs at least 2 variables")
        expr, func_map, var_map = _parse_diffeq(equation, [func], variables)
    except ComputeError as exc:
        return _error("solve_pde", str(exc), t0)
    try:
        applied = func_map[func](*[var_map[v] for v in variables])
        sol = sympy.pdsolve(expr, applied)
        result = [str(s) for s in sol] if isinstance(sol, list) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_pde", f"could not solve (PDE support is limited): {exc}",
                      t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_pde", result,
                         f"PDE solution ({func}({', '.join(variables)})).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# D4 — complex analysis: residue, contour integral (residue theorem), Laurent
# series, and real/imaginary splitting. `I` is the imaginary unit (see _CONSTS),
# so poles/points like `I`, `-I`, `2+I` parse directly.
# --------------------------------------------------------------------------- #
def residue(expression: str, symbol: str, point: str) -> ComputeResult:
    """Residue Res(f, z₀) of `expression` at `point` (may be complex, e.g. `I`).

    (A residue of 0 at a regular point is the correct answer, not an error.)
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse(str(point), syms)
    except ComputeError as exc:
        return _error("residue", str(exc), t0)
    try:
        result = str(sympy.residue(expr, var, pt))
    except Exception as exc:  # noqa: BLE001
        return _error("residue", f"could not compute residue: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "residue", result,
                         f"Res(f, {point}) = {result}.", "OK", _meta(t0))


def contour_integral(expression: str, symbol: str, poles: list[str]) -> ComputeResult:
    """∮_C f dz by the RESIDUE THEOREM = 2πi·Σ Res(f, pole) over the ENCLOSED `poles`.

    The caller supplies the poles inside the contour; e.g. `1/(z**2+1)` enclosing `I` → π.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(poles, list) or not poles:
            raise ComputeError("provide the poles enclosed by the contour (non-empty list)")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pts = [_parse(str(p), syms) for p in poles]
    except ComputeError as exc:
        return _error("contour_integral", str(exc), t0)
    try:
        total = sum((sympy.residue(expr, var, p) for p in pts), sympy.Integer(0))
        result = str(sympy.simplify(2 * sympy.pi * sympy.I * total))
    except Exception as exc:  # noqa: BLE001
        return _error("contour_integral", f"could not integrate: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "contour_integral", result,
                         f"∮_C f dz = 2πi·Σ Res = {result} ({len(pts)} pole(s) enclosed).",
                         "OK", _meta(t0))


def laurent_series(expression: str, symbol: str, point: str = "0",
                   order: int = 6) -> ComputeResult:
    """Laurent series of `expression` around `point` up to `order` (includes negative powers).

    E.g. `exp(z)/z**2` around `0` → `z**(-2) + 1/z + 1/2 + z/6 + …`.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("order must be an integer >= 1")
        expr = _parse(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
    except ComputeError as exc:
        return _error("laurent_series", str(exc), t0)
    try:
        result = str(expr.series(var, pt, order).removeO())
    except Exception as exc:  # noqa: BLE001
        return _error("laurent_series", f"could not expand: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "laurent_series", result,
                         f"Laurent series of {expression} around {symbol}={point}.",
                         "OK", _meta(t0))


def complex_parts(expression: str) -> ComputeResult:
    """Splits a complex expression into real and imaginary parts → `{real, imag}`.

    E.g. `(2 + 3*I)*(1 - I)` → `{"real": "5", "imag": "1"}`.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _parse(expression, syms)
    except ComputeError as exc:
        return _error("complex_parts", str(exc), t0)
    try:
        expanded = sympy.expand_complex(expr)
        result = {"real": str(sympy.simplify(sympy.re(expanded))),
                  "imag": str(sympy.simplify(sympy.im(expanded)))}
    except Exception as exc:  # noqa: BLE001
        return _error("complex_parts", f"could not split: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "complex_parts", result,
                         f"real = {result['real']}, imag = {result['imag']}.", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# E1 — abstract algebra: permutation groups. Permutations are given in ARRAY form
# (0-indexed image list), e.g. [1, 2, 0] is the cycle (0 1 2). Backed by
# sympy.combinatorics; invalid permutations are rejected honestly.
# --------------------------------------------------------------------------- #
def _perm(arr: Any) -> Any:
    """Builds a sympy Permutation from array form; rejects non-permutations."""
    from sympy.combinatorics import Permutation
    if not isinstance(arr, list) or not arr:
        raise ComputeError("a permutation must be a non-empty list (array form)")
    try:
        vals = [int(x) for x in arr]
    except (ValueError, TypeError) as exc:
        raise ComputeError("permutation entries must be integers") from exc
    if sorted(vals) != list(range(len(vals))):
        raise ComputeError(f"not a valid permutation of 0..{len(vals) - 1}: {vals}")
    return Permutation(vals)


def permutation_order(permutation: list) -> ComputeResult:
    """Order of a permutation (smallest k with σᵏ = identity). E.g. `[1,2,0]` → 3."""
    t0 = time.perf_counter()
    try:
        p = _perm(permutation)
    except ComputeError as exc:
        return _error("permutation_order", str(exc), t0)
    return ComputeResult("ok", "permutation_order", int(p.order()),
                         f"order = {int(p.order())}.", "OK", _meta(t0))


def permutation_parity(permutation: list) -> ComputeResult:
    """Parity of a permutation: `even` or `odd` (sign +1 / −1)."""
    t0 = time.perf_counter()
    try:
        p = _perm(permutation)
    except ComputeError as exc:
        return _error("permutation_parity", str(exc), t0)
    parity = "even" if p.is_even else "odd"
    return ComputeResult("ok", "permutation_parity", parity,
                         f"{parity} permutation (sign {1 if p.is_even else -1}).", "OK", _meta(t0))


def permutation_compose(permutations: list) -> ComputeResult:
    """Composes permutations left-to-right (σ₁ then σ₂ …); returns the result + its order.

    All permutations must share the same degree (length).
    """
    t0 = time.perf_counter()
    try:
        if not isinstance(permutations, list) or len(permutations) < 2:
            raise ComputeError("at least 2 permutations are required")
        perms = [_perm(x) for x in permutations]
        if len({p.size for p in perms}) != 1:
            raise ComputeError("all permutations must have the same degree (length)")
    except ComputeError as exc:
        return _error("permutation_compose", str(exc), t0)
    prod = perms[0]
    for p in perms[1:]:
        prod = prod * p
    result = {"array_form": list(prod.array_form), "order": int(prod.order())}
    return ComputeResult("ok", "permutation_compose", result,
                         f"composition = {result['array_form']} (order {result['order']}).",
                         "OK", _meta(t0))


def group_order(name: str, degree: int) -> ComputeResult:
    """Order (+ whether abelian) of a named group of the given degree.

    `name`: `symmetric` (Sₙ), `alternating` (Aₙ), `cyclic` (Cₙ), `dihedral` (Dₙ).
    """
    from sympy.combinatorics.named_groups import (
        AlternatingGroup,
        CyclicGroup,
        DihedralGroup,
        SymmetricGroup,
    )
    t0 = time.perf_counter()
    named = {"symmetric": SymmetricGroup, "alternating": AlternatingGroup,
             "cyclic": CyclicGroup, "dihedral": DihedralGroup}
    try:
        key = str(name).strip().lower()
        if key not in named:
            raise ComputeError(f"unknown group {name!r} (use: {', '.join(sorted(named))})")
        if not isinstance(degree, int) or degree < 1:
            raise ComputeError("degree must be an integer >= 1")
    except ComputeError as exc:
        return _error("group_order", str(exc), t0)
    try:
        G = named[key](degree)
        result = {"order": int(G.order()), "abelian": bool(G.is_abelian)}
    except Exception as exc:  # noqa: BLE001
        return _error("group_order", f"could not build the group: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "group_order", result,
                         f"|{key} group of degree {degree}| = {result['order']} "
                         f"({'abelian' if result['abelian'] else 'non-abelian'}).", "OK", _meta(t0))


def generated_group(generators: list) -> ComputeResult:
    """Order (+ abelian, degree) of the permutation group generated by `generators`.

    Each generator is a permutation in array form; all must share the same degree.
    E.g. `[[1,2,0],[1,0,2]]` generates S₃ (order 6).
    """
    from sympy.combinatorics import PermutationGroup
    t0 = time.perf_counter()
    try:
        if not isinstance(generators, list) or not generators:
            raise ComputeError("provide at least one generator")
        gens = [_perm(g) for g in generators]
        if len({g.size for g in gens}) != 1:
            raise ComputeError("all generators must have the same degree (length)")
    except ComputeError as exc:
        return _error("generated_group", str(exc), t0)
    try:
        G = PermutationGroup(gens)
        result = {"order": int(G.order()), "abelian": bool(G.is_abelian), "degree": int(G.degree)}
    except Exception as exc:  # noqa: BLE001
        return _error("generated_group", f"could not build the group: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "generated_group", result,
                         f"generated group order = {result['order']} "
                         f"({'abelian' if result['abelian'] else 'non-abelian'}, "
                         f"degree {result['degree']}).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# E2 — linear algebra III: decompositions & matrix functions (SVD singular values,
# QR, Cholesky, Gram-Schmidt, pseudo-inverse, matrix exp, Jordan form, char.
# polynomial, least squares). All symbolic (exact) via SymPy; honest errors when a
# decomposition's precondition fails (e.g. Cholesky needs positive-definite).
# --------------------------------------------------------------------------- #
def singular_values(matrix: list[list[str]]) -> ComputeResult:
    """Singular values σᵢ of a matrix (√ of the eigenvalues of AᵀA), largest first."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("singular_values", str(exc), t0)
    try:
        result = [str(s) for s in M.singular_values()]
    except Exception as exc:  # noqa: BLE001
        return _error("singular_values", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "singular_values", result,
                         f"{len(result)} singular value(s).", "OK", _meta(t0))


def qr_decomposition(matrix: list[list[str]]) -> ComputeResult:
    """QR decomposition A = Q·R (Q orthonormal columns, R upper-triangular)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("qr_decomposition", str(exc), t0)
    try:
        Q, R = M.QRdecomposition()
        result = {"Q": _mat_out(Q), "R": _mat_out(R)}
    except Exception as exc:  # noqa: BLE001
        return _error("qr_decomposition", f"could not decompose: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "qr_decomposition", result, "A = Q·R.", "OK", _meta(t0))


def cholesky_decomposition(matrix: list[list[str]]) -> ComputeResult:
    """Cholesky decomposition A = L·Lᵀ (L lower-triangular). Needs symmetric positive-definite."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("cholesky_decomposition", str(exc), t0)
    try:
        L = M.cholesky()
        result = {"L": _mat_out(L)}
    except Exception as exc:  # noqa: BLE001
        return _error("cholesky_decomposition",
                      f"not symmetric positive-definite (Cholesky requires it): {exc}",
                      t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "cholesky_decomposition", result, "A = L·Lᵀ.", "OK", _meta(t0))


def gram_schmidt(vectors: list[list[str]], normalize: bool = True) -> ComputeResult:
    """Gram-Schmidt orthogonalization of a list of vectors (orthonormal if `normalize`)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(vectors, list) or not vectors:
            raise ComputeError("provide at least one vector")
        cols = [sympy.Matrix([_parse(c, syms) for c in v]) for v in vectors]
    except ComputeError as exc:
        return _error("gram_schmidt", str(exc), t0)
    try:
        from sympy import GramSchmidt
        ortho = GramSchmidt(cols, bool(normalize))
        result = [[str(x) for x in vec] for vec in ortho]
    except Exception as exc:  # noqa: BLE001
        return _error("gram_schmidt", f"could not orthogonalize (are the vectors independent?): {exc}",
                      t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "gram_schmidt", result,
                         f"{len(result)} orthogonal{'/normal' if normalize else ''} vector(s).",
                         "OK", _meta(t0))


def pseudoinverse(matrix: list[list[str]]) -> ComputeResult:
    """Moore-Penrose pseudo-inverse A⁺ (generalizes the inverse to non-square/singular A)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
    except ComputeError as exc:
        return _error("pseudoinverse", str(exc), t0)
    try:
        result = _mat_out(M.pinv())
    except Exception as exc:  # noqa: BLE001
        return _error("pseudoinverse", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "pseudoinverse", result,
                         f"A⁺ = {len(result)}×{len(result[0])} matrix.", "OK", _meta(t0))


def matrix_exponential(matrix: list[list[str]]) -> ComputeResult:
    """Matrix exponential e^A (square matrix). E.g. e^[[0,1],[0,0]] = [[1,1],[0,1]]."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("matrix must be square")
    except ComputeError as exc:
        return _error("matrix_exponential", str(exc), t0)
    try:
        result = _mat_out(M.exp())
    except Exception as exc:  # noqa: BLE001
        return _error("matrix_exponential", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "matrix_exponential", result, "e^A.", "OK", _meta(t0))


def jordan_form(matrix: list[list[str]]) -> ComputeResult:
    """Jordan canonical form A = P·J·P⁻¹ → returns `{P, J}` (J block-diagonal)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("matrix must be square")
    except ComputeError as exc:
        return _error("jordan_form", str(exc), t0)
    try:
        P, J = M.jordan_form()
        result = {"P": _mat_out(P), "J": _mat_out(J)}
    except Exception as exc:  # noqa: BLE001
        return _error("jordan_form", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "jordan_form", result, "A = P·J·P⁻¹ (Jordan form).", "OK", _meta(t0))


def characteristic_polynomial(matrix: list[list[str]], symbol: str = "lambda") -> ComputeResult:
    """Characteristic polynomial det(A − λI) of a square matrix (variable `symbol`)."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        M = _parse_matrix(matrix, syms)
        if M.rows != M.cols:
            raise ComputeError("matrix must be square")
        lam = sympy.Symbol(symbol)
    except ComputeError as exc:
        return _error("characteristic_polynomial", str(exc), t0)
    try:
        result = str(M.charpoly(lam).as_expr())
    except Exception as exc:  # noqa: BLE001
        return _error("characteristic_polynomial", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "characteristic_polynomial", result,
                         f"det(A − {symbol}·I) = {result}.", "OK", _meta(t0))


def least_squares(matrix: list[list[str]], rhs: list[str]) -> ComputeResult:
    """Least-squares solution of A·x ≈ b (minimizes ‖A·x − b‖) — overdetermined systems."""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(matrix, syms)
        if not isinstance(rhs, list) or not rhs:
            raise ComputeError("the right-hand side vector cannot be empty")
        if len(rhs) != A.rows:
            raise ComputeError(f"rhs length {len(rhs)} != number of rows {A.rows}")
        b = sympy.Matrix([_parse(v, syms) for v in rhs])
    except ComputeError as exc:
        return _error("least_squares", str(exc), t0)
    try:
        x = A.solve_least_squares(b)
        result = [str(v) for v in x]
    except Exception as exc:  # noqa: BLE001
        return _error("least_squares", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "least_squares", result,
                         f"least-squares solution ({len(result)} component(s)).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# E3 — graph theory (pure stdlib, deterministic by construction — no networkx).
# Edges are `[u, v]` or `[u, v, weight]`; nodes are ints/strings inferred from the
# edges (+ an optional explicit node list to include isolated vertices).
# --------------------------------------------------------------------------- #
def _gw(x: Any) -> Any:
    """Parses an edge weight: int when possible, else float."""
    try:
        return int(x)
    except (ValueError, TypeError):
        try:
            return float(x)
        except (ValueError, TypeError) as exc:
            raise ComputeError(f"bad edge weight: {x!r}") from exc


def _graph(edges: Any, *, directed: bool, weighted: bool) -> tuple[set, dict]:
    """Builds (node set, adjacency {u: [(v, w), ...]}) from an edge list."""
    if not isinstance(edges, list):
        raise ComputeError("edges must be a list of [u, v] (or [u, v, weight])")
    adj: dict[Any, list] = {}
    nodes: set = set()
    for e in edges:
        if not isinstance(e, list) or len(e) < 2:
            raise ComputeError(f"each edge needs at least [u, v]: {e!r}")
        u, v = e[0], e[1]
        w = _gw(e[2]) if weighted and len(e) >= 3 else 1
        nodes.add(u)
        nodes.add(v)
        adj.setdefault(u, []).append((v, w))
        adj.setdefault(v, []).append((u, w)) if not directed else None
        if directed:
            adj.setdefault(v, [])
    return nodes, adj


class _DSU:
    """Union-find (disjoint set)."""

    def __init__(self, items):
        self.p = {x: x for x in items}

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb
            return True
        return False


def shortest_path(edges: list, source: Any, target: Any, directed: bool = False,
                  weighted: bool = False) -> ComputeResult:
    """Shortest path source→target (Dijkstra if `weighted`, else BFS). Honest if unreachable."""
    import heapq
    t0 = time.perf_counter()
    try:
        nodes, adj = _graph(edges, directed=directed, weighted=weighted)
        if source not in nodes:
            raise ComputeError(f"source {source!r} is not a node")
        if target not in nodes:
            raise ComputeError(f"target {target!r} is not a node")
    except ComputeError as exc:
        return _error("shortest_path", str(exc), t0)
    dist = {source: 0}
    prev: dict[Any, Any] = {}
    pq = [(0, 0, source)]           # (dist, tiebreak-counter, node) — deterministic order
    counter = 1
    seen = set()
    while pq:
        d, _, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == target:
            break
        for v, w in sorted(adj.get(u, []), key=lambda t: (str(t[0]), t[1])):
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                pq.append((nd, counter, v))
                counter += 1
                heapq.heapify(pq)
    if target not in dist:
        return ComputeResult("ok", "shortest_path", {"path": None, "length": None},
                             f"no path from {source} to {target} (unreachable).", "OK", _meta(t0))
    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()
    result = {"path": path, "length": dist[target]}
    return ComputeResult("ok", "shortest_path", result,
                         f"length {dist[target]} via {len(path)} node(s).", "OK", _meta(t0))


def connected_components(edges: list, nodes: list | None = None,
                         directed: bool = False) -> ComputeResult:
    """Connected components (weakly connected if `directed`). Returns count + is_connected + components."""
    t0 = time.perf_counter()
    try:
        node_set, adj = _graph(edges, directed=False, weighted=False)  # weak connectivity
        if nodes:
            node_set |= set(nodes)
    except ComputeError as exc:
        return _error("connected_components", str(exc), t0)
    if not node_set:
        return _error("connected_components", "the graph has no nodes", t0)
    dsu = _DSU(node_set)
    for u in adj:
        for v, _w in adj[u]:
            dsu.union(u, v)
    groups: dict[Any, list] = {}
    for x in node_set:
        groups.setdefault(dsu.find(x), []).append(x)
    comps = [sorted(g, key=str) for g in groups.values()]
    comps.sort(key=lambda g: str(g[0]))
    result = {"count": len(comps), "is_connected": len(comps) == 1, "components": comps}
    return ComputeResult("ok", "connected_components", result,
                         f"{len(comps)} component(s); {'connected' if len(comps) == 1 else 'disconnected'}.",
                         "OK", _meta(t0))


def minimum_spanning_tree(edges: list) -> ComputeResult:
    """Minimum spanning tree/forest (Kruskal, undirected). Returns the chosen edges + total weight."""
    t0 = time.perf_counter()
    try:
        node_set, _adj = _graph(edges, directed=False, weighted=True)
        parsed = []
        for e in edges:
            w = _gw(e[2]) if len(e) >= 3 else 1
            parsed.append((w, e[0], e[1]))
    except ComputeError as exc:
        return _error("minimum_spanning_tree", str(exc), t0)
    if not node_set:
        return _error("minimum_spanning_tree", "the graph has no nodes", t0)
    dsu = _DSU(node_set)
    chosen = []
    total = 0
    for w, u, v in sorted(parsed, key=lambda t: (t[0], str(t[1]), str(t[2]))):
        if dsu.union(u, v):
            chosen.append([u, v, w])
            total += w
    connected = len(chosen) == len(node_set) - 1
    result = {"edges": chosen, "total_weight": total, "spans_all": connected}
    note = "" if connected else " (graph disconnected — spanning FOREST)"
    return ComputeResult("ok", "minimum_spanning_tree", result,
                         f"total weight {total}, {len(chosen)} edge(s){note}.", "OK", _meta(t0))


def max_flow(edges: list, source: Any, sink: Any) -> ComputeResult:
    """Maximum flow source→sink (Edmonds-Karp). By max-flow-min-cut, this equals the min-cut capacity.

    Directed edges `[u, v, capacity]`.
    """
    from collections import deque
    t0 = time.perf_counter()
    try:
        if source == sink:
            raise ComputeError("source and sink must differ")
        cap: dict = {}
        nodes: set = set()
        for e in edges:
            if not isinstance(e, list) or len(e) < 3:
                raise ComputeError(f"each edge needs [u, v, capacity]: {e!r}")
            u, v, c = e[0], e[1], _gw(e[2])
            if c < 0:
                raise ComputeError("capacities must be non-negative")
            cap[(u, v)] = cap.get((u, v), 0) + c
            cap.setdefault((v, u), cap.get((v, u), 0))
            nodes.add(u)
            nodes.add(v)
        if source not in nodes or sink not in nodes:
            raise ComputeError("source/sink must be nodes of the graph")
    except ComputeError as exc:
        return _error("max_flow", str(exc), t0)
    adj: dict = {}
    for (u, v) in cap:
        adj.setdefault(u, set()).add(v)
    flow = 0
    while True:
        parent = {source: None}
        q = deque([source])
        while q:
            u = q.popleft()
            for v in sorted(adj.get(u, ()), key=str):
                if v not in parent and cap[(u, v)] > 0:
                    parent[v] = u
                    q.append(v)
        if sink not in parent:
            break
        # bottleneck
        path_flow = None
        v = sink
        while v != source:
            u = parent[v]
            path_flow = cap[(u, v)] if path_flow is None else min(path_flow, cap[(u, v)])
            v = u
        v = sink
        while v != source:
            u = parent[v]
            cap[(u, v)] -= path_flow
            cap[(v, u)] += path_flow
            v = u
        flow += path_flow
    return ComputeResult("ok", "max_flow", {"max_flow": flow, "min_cut": flow},
                         f"max flow = min cut = {flow}.", "OK", _meta(t0))


def maximum_matching(edges: list, left: list) -> ComputeResult:
    """Maximum bipartite matching (Kuhn's augmenting paths). `left` = the left-partition nodes."""
    t0 = time.perf_counter()
    try:
        if not isinstance(left, list) or not left:
            raise ComputeError("provide the left-partition node list")
        left_set = set(left)
        adj: dict = {u: [] for u in left_set}
        for e in edges:
            if not isinstance(e, list) or len(e) < 2:
                raise ComputeError(f"each edge needs [u, v]: {e!r}")
            u, v = e[0], e[1]
            if u in left_set and v in left_set:
                raise ComputeError(f"edge {e!r} is within the left partition (not bipartite)")
            if u in left_set:
                adj[u].append(v)
            elif v in left_set:
                adj[v].append(u)
            else:
                raise ComputeError(f"edge {e!r} touches no left node")
    except ComputeError as exc:
        return _error("maximum_matching", str(exc), t0)
    match_r: dict = {}

    def _try(u, visited):
        for v in sorted(adj[u], key=str):
            if v not in visited:
                visited.add(v)
                if v not in match_r or _try(match_r[v], visited):
                    match_r[v] = u
                    return True
        return False

    for u in sorted(left_set, key=str):
        _try(u, set())
    pairs = sorted(([u, v] for v, u in match_r.items()), key=lambda p: str(p[0]))
    result = {"size": len(pairs), "matching": pairs}
    return ComputeResult("ok", "maximum_matching", result,
                         f"maximum matching size = {len(pairs)}.", "OK", _meta(t0))


def is_isomorphic(edges1: list, edges2: list, nodes1: list | None = None,
                  nodes2: list | None = None) -> ComputeResult:
    """Are two (undirected) graphs isomorphic? Backtracking with degree pruning (small graphs)."""
    t0 = time.perf_counter()

    def _build(edges, extra):
        nodes, _a = _graph(edges, directed=False, weighted=False)
        if extra:
            nodes |= set(extra)
        adjset = {x: set() for x in nodes}
        for e in edges:
            adjset[e[0]].add(e[1])
            adjset[e[1]].add(e[0])
        return sorted(nodes, key=str), adjset

    try:
        n1, a1 = _build(edges1, nodes1)
        n2, a2 = _build(edges2, nodes2)
    except ComputeError as exc:
        return _error("is_isomorphic", str(exc), t0)
    if len(n1) > 10:
        return _error("is_isomorphic", "graphs too large for the backtracking check (>10 nodes)",
                      t0, "COMPUTE_FAILED")
    e1 = sum(len(a1[x]) for x in n1) // 2
    e2 = sum(len(a2[x]) for x in n2) // 2
    deg1 = sorted(len(a1[x]) for x in n1)
    deg2 = sorted(len(a2[x]) for x in n2)
    if len(n1) != len(n2) or e1 != e2 or deg1 != deg2:
        return ComputeResult("ok", "is_isomorphic", {"isomorphic": False, "mapping": None},
                             "not isomorphic (node/edge count or degree sequence differ).",
                             "OK", _meta(t0))
    mapping: dict = {}
    used: set = set()

    def _bt(i):
        if i == len(n1):
            return True
        u = n1[i]
        for v in n2:
            if v in used or len(a1[u]) != len(a2[v]):
                continue
            ok = all((mapping[w] in a2[v]) for w in a1[u] if w in mapping)
            if ok:
                mapping[u] = v
                used.add(v)
                if _bt(i + 1):
                    return True
                used.discard(v)
                del mapping[u]
        return False

    if _bt(0):
        return ComputeResult("ok", "is_isomorphic",
                             {"isomorphic": True, "mapping": {str(k): str(v) for k, v in mapping.items()}},
                             "isomorphic (an explicit mapping was found).", "OK", _meta(t0))
    return ComputeResult("ok", "is_isomorphic", {"isomorphic": False, "mapping": None},
                         "not isomorphic (no adjacency-preserving bijection exists).", "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# E4 — number theory II: Euler φ, Möbius μ, continued fractions (rational + √n
# periodic), quadratic residues, primitive roots, Pell equation. Backed by SymPy's
# (deterministic) number theory. Non-existence (e.g. no primitive root) is honest.
# --------------------------------------------------------------------------- #
def _intarg(x: Any, name: str = "value") -> int:
    try:
        return int(x)
    except (ValueError, TypeError) as exc:
        raise ComputeError(f"{name} must be an integer, got {x!r}") from exc


def euler_totient(n: Any) -> ComputeResult:
    """Euler's totient φ(n) — the count of integers in 1..n coprime to n. E.g. φ(12) = 4."""
    t0 = time.perf_counter()
    try:
        val = _intarg(n, "n")
        if val < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("euler_totient", str(exc), t0)
    result = int(sympy.totient(val))
    return ComputeResult("ok", "euler_totient", result, f"φ({val}) = {result}.", "OK", _meta(t0))


def mobius(n: Any) -> ComputeResult:
    """Möbius function μ(n): 0 if n has a squared prime factor, else (−1)^(number of prime factors)."""
    t0 = time.perf_counter()
    try:
        val = _intarg(n, "n")
        if val < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("mobius", str(exc), t0)
    result = int(sympy.mobius(val))
    return ComputeResult("ok", "mobius", result, f"μ({val}) = {result}.", "OK", _meta(t0))


def continued_fraction(numerator: Any, denominator: Any = 1) -> ComputeResult:
    """Continued-fraction expansion of the rational numerator/denominator → list of terms.

    E.g. 415/93 → `[4, 2, 6, 7]`.
    """
    t0 = time.perf_counter()
    try:
        p = _intarg(numerator, "numerator")
        q = _intarg(denominator, "denominator")
        if q == 0:
            raise ComputeError("denominator cannot be 0")
    except ComputeError as exc:
        return _error("continued_fraction", str(exc), t0)
    result = [int(t) for t in sympy.continued_fraction(sympy.Rational(p, q))]
    return ComputeResult("ok", "continued_fraction", result,
                         f"[{'; '.join(map(str, result))}] ({p}/{q}).", "OK", _meta(t0))


def continued_fraction_sqrt(n: Any) -> ComputeResult:
    """Periodic continued fraction of √n → `{a0, period}` (empty period if n is a perfect square)."""
    t0 = time.perf_counter()
    try:
        val = _intarg(n, "n")
        if val < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("continued_fraction_sqrt", str(exc), t0)
    cf = sympy.continued_fraction_periodic(0, 1, val)
    a0 = int(cf[0])
    period = [int(x) for x in cf[1]] if len(cf) > 1 and isinstance(cf[1], list) else []
    result = {"a0": a0, "period": period}
    return ComputeResult("ok", "continued_fraction_sqrt", result,
                         f"√{val} = [{a0}; {period} repeating]" if period else f"√{val} = {a0} (exact).",
                         "OK", _meta(t0))


def quadratic_residue(a: Any, n: Any) -> ComputeResult:
    """Is `a` a quadratic residue mod `n`? Returns `{is_residue, jacobi_symbol}`.

    For a prime modulus the Jacobi symbol equals the Legendre symbol (+1 residue, −1 non-residue).
    """
    from sympy.functions.combinatorial.numbers import jacobi_symbol
    from sympy.ntheory.residue_ntheory import is_quad_residue
    t0 = time.perf_counter()
    try:
        av = _intarg(a, "a")
        nv = _intarg(n, "n")
        if nv < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("quadratic_residue", str(exc), t0)
    try:
        is_res = bool(is_quad_residue(av, nv))
        jac = int(jacobi_symbol(av, nv)) if nv % 2 == 1 else None
    except Exception as exc:  # noqa: BLE001
        return _error("quadratic_residue", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    result = {"is_residue": is_res, "jacobi_symbol": jac}
    return ComputeResult("ok", "quadratic_residue", result,
                         f"{av} is {'a' if is_res else 'NOT a'} quadratic residue mod {nv}.",
                         "OK", _meta(t0))


def primitive_root(n: Any) -> ComputeResult:
    """Smallest primitive root modulo `n` (a generator of the group of units), or honest none.

    A primitive root exists only for n = 1, 2, 4, pᵏ, or 2pᵏ (p an odd prime).
    """
    from sympy.ntheory.residue_ntheory import primitive_root as _pr
    t0 = time.perf_counter()
    try:
        nv = _intarg(n, "n")
        if nv < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("primitive_root", str(exc), t0)
    try:
        root = _pr(nv)
    except Exception as exc:  # noqa: BLE001
        return _error("primitive_root", f"could not compute: {exc}", t0, "COMPUTE_FAILED")
    if root is None:
        return ComputeResult("ok", "primitive_root", None,
                             f"no primitive root exists modulo {nv} (honest).", "OK", _meta(t0))
    return ComputeResult("ok", "primitive_root", int(root),
                         f"smallest primitive root mod {nv} = {int(root)}.", "OK", _meta(t0))


def pell_solution(n: Any) -> ComputeResult:
    """Fundamental solution (x, y) of the Pell equation x² − n·y² = 1 (y > 0).

    E.g. n=2 → (3, 2); n=13 → (649, 180). If n is a perfect square, there is no
    non-trivial solution (honest).
    """
    from sympy.solvers.diophantine.diophantine import diop_DN
    t0 = time.perf_counter()
    try:
        nv = _intarg(n, "n")
        if nv < 1:
            raise ComputeError("n must be a positive integer")
    except ComputeError as exc:
        return _error("pell_solution", str(exc), t0)
    if sympy.sqrt(nv).is_integer:
        return ComputeResult("ok", "pell_solution", None,
                             f"n = {nv} is a perfect square — x² − {nv}y² = 1 has only the trivial "
                             f"solution (honest).", "OK", _meta(t0))
    try:
        sols = diop_DN(nv, 1)
    except Exception as exc:  # noqa: BLE001
        return _error("pell_solution", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    if not sols:
        return _error("pell_solution", "no fundamental solution found", t0, "COMPUTE_FAILED")
    x, y = sols[0]
    result = {"x": int(x), "y": int(abs(y))}
    return ComputeResult("ok", "pell_solution", result,
                         f"fundamental solution: {result['x']}² − {nv}·{result['y']}² = 1.",
                         "OK", _meta(t0))


# --------------------------------------------------------------------------- #
# Probability & statistics.
# Descriptive: mean/variance/std/median (data list, exact/rational).
# Distributions: E[X]/Var/std + P(X≤k)/density via sympy.stats (symbolic, exact).
# --------------------------------------------------------------------------- #
def _parse_data(data: list[Any]) -> list[Any]:
    """Converts a numeric data list to SymPy numbers (symbols are rejected)."""
    if not isinstance(data, list) or not data:
        raise ComputeError("the data list cannot be empty")
    syms: dict[str, Any] = {}
    vals = [_parse(str(x), syms) for x in data]
    if syms:
        raise ComputeError("data must be numeric (cannot contain a symbol)")
    return vals


def mean(data: list[Any]) -> ComputeResult:
    """Arithmetic mean (exact/rational result)."""
    t0 = time.perf_counter()
    try:
        vals = _parse_data(data)
    except ComputeError as exc:
        return _error("mean", str(exc), t0)
    result = str(sympy.simplify(sum(vals) / len(vals)))
    return ComputeResult("ok", "mean", result, f"mean = {result} (n={len(vals)}).", "OK", _meta(t0))


def variance(data: list[Any], sample: bool = False) -> ComputeResult:
    """Variance. sample=True → sample (divides by n-1), otherwise population (n)."""
    t0 = time.perf_counter()
    try:
        vals = _parse_data(data)
        n = len(vals)
        if sample and n < 2:
            raise ComputeError("sample variance requires at least 2 observations")
    except ComputeError as exc:
        return _error("variance", str(exc), t0)
    mu = sum(vals) / n
    denom = (n - 1) if sample else n
    result = str(sympy.simplify(sum((v - mu) ** 2 for v in vals) / denom))
    kind = "sample" if sample else "population"
    return ComputeResult("ok", "variance", result, f"{kind} variance = {result}.", "OK", _meta(t0))


def standard_deviation(data: list[Any], sample: bool = False) -> ComputeResult:
    """Standard deviation = √variance (the sample option is the same as variance)."""
    t0 = time.perf_counter()
    try:
        vals = _parse_data(data)
        n = len(vals)
        if sample and n < 2:
            raise ComputeError("a sample requires at least 2 observations")
    except ComputeError as exc:
        return _error("standard_deviation", str(exc), t0)
    mu = sum(vals) / n
    denom = (n - 1) if sample else n
    var = sum((v - mu) ** 2 for v in vals) / denom
    result = str(sympy.simplify(sympy.sqrt(var)))
    return ComputeResult("ok", "standard_deviation", result,
                         f"standard deviation = {result}.", "OK", _meta(t0))


def median(data: list[Any]) -> ComputeResult:
    """Median. With an even number of observations, the mean of the middle two."""
    t0 = time.perf_counter()
    try:
        vals = _parse_data(data)
    except ComputeError as exc:
        return _error("median", str(exc), t0)
    try:
        srt = sorted(vals, key=lambda v: float(v))
    except (TypeError, ValueError):
        return _error("median", "data must be real numbers (could not sort)", t0, "COMPUTE_FAILED")
    n = len(srt)
    mid = n // 2
    med = srt[mid] if n % 2 == 1 else (srt[mid - 1] + srt[mid]) / 2
    result = str(sympy.simplify(med))
    return ComputeResult("ok", "median", result, f"median = {result}.", "OK", _meta(t0))


# Name -> (constructor, parameter names). Extensible registry.
_DIST_NAMES = ("normal", "binomial", "poisson", "exponential", "uniform",
               "bernoulli", "geometric")


def distribution(name: str, params: list[Any], at: Any = None) -> ComputeResult:
    """Properties of a named distribution: E[X], Var, std (symbolic/exact).

    If `at` is given, `P(X ≤ at)` (cdf) and the density/pmf at `at` are also added.
    Supported: normal(mu,sigma), binomial(n,p), poisson(lambda), exponential(rate),
    uniform(a,b), bernoulli(p), geometric(p).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        key = str(name).strip().lower()
        if key not in _DIST_NAMES:
            raise ComputeError(f"unsupported distribution: {name} (valid: {', '.join(_DIST_NAMES)})")
        if not isinstance(params, list) or not params:
            raise ComputeError("the parameter list cannot be empty")
        pvals = [_parse(str(p), syms) for p in params]
    except ComputeError as exc:
        return _error("distribution", str(exc), t0)
    try:
        from sympy.stats import (
            Bernoulli,
            Binomial,
            E,
            Exponential,
            Geometric,
            Normal,
            P,
            Poisson,
            Uniform,
            density,
            std,
            variance,
        )
        ctors = {
            "normal": Normal, "binomial": Binomial, "poisson": Poisson,
            "exponential": Exponential, "uniform": Uniform,
            "bernoulli": Bernoulli, "geometric": Geometric,
        }
        X = ctors[key]("X", *pvals)
        result: dict[str, Any] = {
            "mean": str(sympy.simplify(E(X))),
            "variance": str(sympy.simplify(variance(X))),
            "std": str(sympy.simplify(std(X))),
        }
        if at is not None:
            av = _parse(str(at), syms)
            result["cdf_at"] = str(sympy.simplify(P(X <= av)))
            result["density_at"] = str(sympy.simplify(density(X)(av)))
    except ComputeError as exc:
        return _error("distribution", str(exc), t0)
    except Exception as exc:  # noqa: BLE001
        return _error("distribution", f"could not compute distribution: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "distribution", result,
                         f"properties of the {key} distribution.", "OK", _meta(t0))
