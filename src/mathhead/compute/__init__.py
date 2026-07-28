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


def solve_ode(equation: str, func: str = "y", var: str = "x") -> ComputeResult:
    """Solves an ordinary differential equation (ODE). Derivative: `y'`, `y''` (prime).

    E.g. `"y' = y"` → `Eq(y(x), C1*exp(x))`; `"y'' + y = 0"` → C1·sin + C2·cos.
    If it cannot be solved (no closed form), an honest error.
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
            raise ComputeError("disallowed operator")
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -_tr(node.operand)
            if isinstance(node.op, ast.UAdd):
                return _tr(node.operand)
            raise ComputeError("disallowed unary operator")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "D":     # derivative marker: D(func, order)
                if len(node.args) != 2 or not (
                    isinstance(node.args[0], ast.Name) and node.args[0].id == func
                ) or not (isinstance(node.args[1], ast.Constant)
                          and isinstance(node.args[1].value, int)):
                    raise ComputeError("derivative must be of the form D(func, order)")
                return sympy.Derivative(F(varsym), varsym, node.args[1].value)
            if node.func.id == func:    # explicit y(x)
                return F(varsym)
            if node.func.id in _FUNCS:
                return _FUNCS[node.func.id](*[_tr(a) for a in node.args])
            raise ComputeError(f"disallowed call: {node.func.id}")
        if isinstance(node, ast.Name):
            if node.id == var:
                return varsym
            if node.id == func:
                return F(varsym)
            raise ComputeError(f"disallowed name: {node.id}")
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            return sympy.Integer(node.value) if isinstance(node.value, int) else sympy.Float(node.value)
        raise ComputeError("could not parse expression")

    try:
        src = str(equation).strip()
        # y', y'' ... -> D(y,1), D(y,2) ... (convert the prime into an ast-friendly call)
        src = re.sub(rf"{re.escape(func)}('+)",
                     lambda m: f"D({func},{len(m.group(1))})", src)
        if "=" in src and "==" not in src:
            src = src.replace("=", "==", 1)
        body = ast.parse(src, mode="eval").body
        if isinstance(body, ast.Compare):
            if len(body.ops) != 1 or not isinstance(body.ops[0], ast.Eq):
                raise ComputeError("only the '==' comparison is supported")
            expr = _tr(body.left) - _tr(body.comparators[0])
        else:
            expr = _tr(body)
    except ComputeError as exc:
        return _error("solve_ode", str(exc), t0)
    except (SyntaxError, ValueError) as exc:
        return _error("solve_ode", f"could not parse: {exc}", t0)
    try:
        sol = sympy.dsolve(expr, F(varsym))
        result = [str(s) for s in sol] if isinstance(sol, list) else str(sol)
    except Exception as exc:  # noqa: BLE001
        return _error("solve_ode", f"could not solve: {exc}", t0, "COMPUTE_FAILED")
    return ComputeResult("ok", "solve_ode", result,
                         f"ODE solution ({func}({var})).", "OK", _meta(t0))


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
