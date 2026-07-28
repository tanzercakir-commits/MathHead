"""
mathhead.core.smt — Extra SMT theories (ROADMAP H2).

The logic kernel (`core/logic.py`) covers Booleans, linear arithmetic and
uninterpreted predicates. This module opens up four more of Z3's decision
theories, each as a focused tool with the SAME shape as the kernel's
entailment/consistency primitives:

    check_<theory>(assumptions, goal=None)
      * goal given  → ENTAILMENT: do the assumptions entail the goal?
                       (⋀assumptions ∧ ¬goal UNSAT → valid; SAT → invalid + witness)
      * goal = None → CONSISTENCY: are the assumptions jointly satisfiable?
                       (SAT → sat + model; UNSAT → contradiction)

Theories:
  * `check_bitvector`   — fixed-width bit-vectors (BV): & | ^ ~ << >> + - *,
                          (un)signed comparisons. Bit tricks / overflow / masks.
  * `check_uninterpreted` — equality + uninterpreted functions/predicates (EUF):
                          congruence reasoning (a==b ⊨ f(a)==f(b)).
  * `check_arrays`      — arrays with `select`/`store` (McCarthy axioms).
  * `check_strings`     — the string/sequence theory: concat (+), `length`,
                          `contains`, `prefixof`, `suffixof`, literals.

All four return the shared `ReasoningResult` contract. Determinism (fixed seed),
honesty (`unknown` is first-class; no silent assumptions — an unexpected symbol or
sort clash is a clean PARSE_ERROR) hold exactly as in the kernel.
"""
from __future__ import annotations

import ast
import time
from typing import Any, Callable

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS, ReasoningResult
from mathhead.guardrails import GuardrailError, solver_config, validate_input

_U = z3.DeclareSort("U")  # shared uninterpreted sort (same name → same sort)


class SmtParseError(ValueError):
    """A theory expression violated its (deliberately small) grammar."""


def _meta(t0: float, seed: int, timeout_ms: int, theory: str) -> dict[str, Any]:
    return {
        "engine": f"z3-{theory}",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


def _parse(expr: str) -> ast.AST:
    if not isinstance(expr, str) or not expr.strip():
        raise SmtParseError("expression must be a non-empty string")
    try:
        return ast.parse(expr, mode="eval").body
    except SyntaxError as exc:
        raise SmtParseError(f"syntax error: {exc.msg}") from exc


def _decide(
    assumptions_z3: list[Any],
    goal_z3: Any | None,
    read_model: Callable[[z3.ModelRef], dict[str, Any]],
    theory: str,
    t0: float,
    seed: int,
    timeout_ms: int,
) -> ReasoningResult:
    """Shared entailment/consistency driver for every theory."""
    solver = solver_config(timeout_ms, seed)
    for a in assumptions_z3:
        solver.add(a)
    if goal_z3 is not None:
        solver.add(z3.Not(goal_z3))
        res = solver.check()
        if res == z3.unsat:
            return ReasoningResult("valid", "ENTAILED",
                                   f"The goal follows from the assumptions ({theory} theory): "
                                   f"assumptions ∧ ¬goal is unsatisfiable.",
                                   None, _meta(t0, seed, timeout_ms, theory))
        if res == z3.sat:
            return ReasoningResult("invalid", "COUNTEREXAMPLE_FOUND",
                                   f"The goal does NOT follow: found an assignment satisfying the "
                                   f"assumptions but refuting the goal ({theory} theory).",
                                   read_model(solver.model()), _meta(t0, seed, timeout_ms, theory))
    else:
        res = solver.check()
        if res == z3.sat:
            return ReasoningResult("sat", "CONSISTENT",
                                   f"The assumptions are jointly satisfiable ({theory} theory); "
                                   f"witness is one satisfying assignment.",
                                   read_model(solver.model()), _meta(t0, seed, timeout_ms, theory))
        if res == z3.unsat:
            return ReasoningResult("unsat", "CONTRADICTION",
                                   f"The assumptions are contradictory ({theory} theory); "
                                   f"no assignment satisfies them all.",
                                   None, _meta(t0, seed, timeout_ms, theory))
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ReasoningResult("unknown", code, f"The solver could not decide ({reason}).",
                           None, _meta(t0, seed, timeout_ms, theory))


def _run(assumptions: list[str], goal: str | None, translate, theory: str,
         seed: int, timeout_ms: int) -> ReasoningResult:
    """Guardrail + translate + decide (shared across theories)."""
    t0 = time.perf_counter()
    if not isinstance(assumptions, list) or (goal is not None and not isinstance(goal, str)):
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "assumptions must be a list; goal must be a string or null",
                               None, _meta(t0, seed, timeout_ms, theory))
    to_check = [*assumptions] + ([goal] if goal is not None else [])
    if not to_check:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION",
                               "provide at least one assumption or a goal",
                               None, _meta(t0, seed, timeout_ms, theory))
    try:
        validate_input(to_check)
    except GuardrailError as exc:
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", str(exc),
                               None, _meta(t0, seed, timeout_ms, theory))
    try:
        a_z3, g_z3, read_model = translate(assumptions, goal)
    except SmtParseError as exc:
        return ReasoningResult("error", "PARSE_ERROR", str(exc),
                               None, _meta(t0, seed, timeout_ms, theory))
    return _decide(a_z3, g_z3, read_model, theory, t0, seed, timeout_ms)


# =========================================================================== #
# 1) BIT-VECTORS
# =========================================================================== #
def _bv_translate(assumptions: list[str], goal: str | None, width: int, signed: bool):
    syms: dict[str, Any] = {}

    def var(name: str) -> Any:
        if name not in syms:
            syms[name] = z3.BitVec(name, width)
        return syms[name]

    def build(node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            parts = [build(v) for v in node.values]
            return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return z3.Not(build(node.operand))
            if isinstance(node.op, ast.Invert):
                return ~build(node.operand)
            if isinstance(node.op, ast.USub):
                return -build(node.operand)
            raise SmtParseError(f"unsupported unary op: {type(node.op).__name__}")
        if isinstance(node, ast.Compare):
            left = build(node.left)
            clauses = []
            for op, comp in zip(node.ops, node.comparators):
                right = build(comp)
                clauses.append(_bv_cmp(op, left, right, signed))
                left = right
            return clauses[0] if len(clauses) == 1 else z3.And(*clauses)
        if isinstance(node, ast.BinOp):
            a, b = build(node.left), build(node.right)
            op = node.op
            if isinstance(op, ast.BitAnd):
                return a & b
            if isinstance(op, ast.BitOr):
                return a | b
            if isinstance(op, ast.BitXor):
                return a ^ b
            if isinstance(op, ast.LShift):
                return a << b
            if isinstance(op, ast.RShift):
                return (a >> b) if signed else z3.LShR(a, b)
            if isinstance(op, ast.Add):
                return a + b
            if isinstance(op, ast.Sub):
                return a - b
            if isinstance(op, ast.Mult):
                return a * b
            raise SmtParseError(f"unsupported bit-vector operator: {type(op).__name__}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("implies", "iff"):
            if len(node.args) != 2:
                raise SmtParseError(f"{node.func.id} requires exactly 2 arguments")
            a, b = build(node.args[0]), build(node.args[1])
            return z3.Implies(a, b) if node.func.id == "implies" else (a == b)
        if isinstance(node, ast.Name):
            return var(node.id)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return z3.BoolVal(node.value)
            if not isinstance(node.value, int):
                raise SmtParseError("bit-vector constants must be integers")
            return z3.BitVecVal(node.value, width)
        raise SmtParseError(f"disallowed bit-vector node: {type(node).__name__}")

    def top(expr: str) -> Any:
        z = build(_parse(expr))
        if not z3.is_bool(z):
            raise SmtParseError("each assumption/goal must be a boolean formula")
        return z

    a_z3 = [top(a) for a in assumptions]
    g_z3 = top(goal) if goal is not None else None

    def read_model(m: z3.ModelRef) -> dict[str, Any]:
        out = {}
        for name, const in sorted(syms.items()):
            val = m.eval(const, model_completion=True)
            n = val.as_long() if z3.is_bv_value(val) else None
            if n is not None and signed and n >= (1 << (width - 1)):
                n -= (1 << width)
            out[name] = n
        return out

    return a_z3, g_z3, read_model


def _bv_cmp(op: ast.AST, a: Any, b: Any, signed: bool) -> Any:
    if isinstance(op, ast.Eq):
        return a == b
    if isinstance(op, ast.NotEq):
        return a != b
    if signed:
        return {ast.Lt: a < b, ast.LtE: a <= b, ast.Gt: a > b, ast.GtE: a >= b}[type(op)]
    fn = {ast.Lt: z3.ULT, ast.LtE: z3.ULE, ast.Gt: z3.UGT, ast.GtE: z3.UGE}.get(type(op))
    if fn is None:
        raise SmtParseError(f"unsupported bit-vector comparison: {type(op).__name__}")
    return fn(a, b)


def check_bitvector(assumptions: list[str], goal: str | None = None, width: int = 32,
                    signed: bool = False, *, timeout_ms: int = DEFAULT_TIMEOUT_MS,
                    seed: int = DEFAULT_SEED) -> ReasoningResult:
    """Reason over fixed-width bit-vectors (BV theory).

    Grammar: `& | ^ ~ << >> + - *`, comparisons (`== != < <= > >=`, unsigned unless
    `signed=True`), `and/or/not`, `implies`/`iff`. Names are `width`-bit vectors;
    integer literals are BV constants. `goal` given → entailment (a validity proof
    with a bit-level counterexample if it fails); `goal=None` → consistency.
    """
    if not isinstance(width, int) or not (1 <= width <= 256):
        t0 = time.perf_counter()
        return ReasoningResult("error", "GUARDRAIL_VIOLATION", "width must be an integer in 1..256",
                               None, _meta(t0, seed, timeout_ms, "bitvector"))
    return _run(assumptions, goal, lambda a, g: _bv_translate(a, g, width, signed),
                "bitvector", seed, timeout_ms)


# =========================================================================== #
# 2) UNINTERPRETED FUNCTIONS + EQUALITY (EUF)
# =========================================================================== #
def _euf_translate(assumptions: list[str], goal: str | None):
    consts: dict[str, Any] = {}
    funcs: dict[str, Any] = {}       # name -> z3.Function (U..→U)
    preds: dict[str, Any] = {}       # name -> z3.Function (U..→Bool)
    kinds: dict[str, str] = {}       # name -> 'const'|'func'|'pred'

    def _claim(name: str, kind: str) -> None:
        if kinds.setdefault(name, kind) != kind:
            raise SmtParseError(f"symbol {name!r} used as both {kinds[name]} and {kind}")

    def term(node: ast.AST) -> Any:
        if isinstance(node, ast.Name):
            _claim(node.id, "const")
            return consts.setdefault(node.id, z3.Const(node.id, _U))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            _claim(name, "func")
            fn = funcs.get(name)
            if fn is None:
                fn = funcs[name] = z3.Function(name, *([_U] * len(node.args)), _U)
            if fn.arity() != len(node.args):
                raise SmtParseError(f"function {name!r} used with inconsistent arity")
            return fn(*[term(a) for a in node.args])
        raise SmtParseError("EUF terms are names or f(...) applications only")

    def formula(node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            parts = [formula(v) for v in node.values]
            return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return z3.Not(formula(node.operand))
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                raise SmtParseError("EUF atoms are single == / != comparisons (U has no order)")
            left, right = term(node.left), term(node.comparators[0])
            return left == right if isinstance(node.ops[0], ast.Eq) else left != right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in ("implies", "iff"):
                if len(node.args) != 2:
                    raise SmtParseError(f"{name} requires exactly 2 arguments")
                a, b = formula(node.args[0]), formula(node.args[1])
                return z3.Implies(a, b) if name == "implies" else (a == b)
            _claim(name, "pred")
            fn = preds.get(name)
            if fn is None:
                fn = preds[name] = z3.Function(name, *([_U] * len(node.args)), z3.BoolSort())
            if fn.arity() != len(node.args):
                raise SmtParseError(f"predicate {name!r} used with inconsistent arity")
            return fn(*[term(a) for a in node.args])
        raise SmtParseError("EUF formulas: ==/!=, predicates P(...), and/or/not, implies/iff")

    a_z3 = [formula(_parse(a)) for a in assumptions]
    g_z3 = formula(_parse(goal)) if goal is not None else None

    def read_model(m: z3.ModelRef) -> dict[str, Any]:
        return {name: str(m.eval(c, model_completion=True)) for name, c in sorted(consts.items())}

    return a_z3, g_z3, read_model


def check_uninterpreted(assumptions: list[str], goal: str | None = None, *,
                        timeout_ms: int = DEFAULT_TIMEOUT_MS,
                        seed: int = DEFAULT_SEED) -> ReasoningResult:
    """Reason with equality and uninterpreted functions/predicates (EUF theory).

    Terms are names (`a`) and applications (`f(a, b)`) over one abstract sort; atoms
    are `==`/`!=` and predicates `P(...)`, combined with `and/or/not`/`implies`/`iff`.
    Congruence is built in: `["a == b"]` entails `f(a) == f(b)`. `goal` → entailment;
    `goal=None` → consistency.
    """
    return _run(assumptions, goal, _euf_translate, "uf", seed, timeout_ms)


# =========================================================================== #
# 3) ARRAYS (select / store — McCarthy)
# =========================================================================== #
def _sort_of(name: str) -> Any:
    return {"Int": z3.IntSort(), "Real": z3.RealSort()}.get(name)


def _arr_translate(assumptions: list[str], goal: str | None, index_sort: str, value_sort: str):
    isort, vsort = _sort_of(index_sort), _sort_of(value_sort)
    if isort is None or vsort is None:
        raise SmtParseError("index_sort/value_sort must be 'Int' or 'Real'")
    arrays: dict[str, Any] = {}
    scalars: dict[str, Any] = {}

    # pre-pass: a name that is the FIRST argument of select/store is an array.
    array_names: set[str] = set()
    for expr in [*assumptions] + ([goal] if goal is not None else []):
        for n in ast.walk(_parse(expr)):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in ("select", "store") and n.args
                    and isinstance(n.args[0], ast.Name)):
                array_names.add(n.args[0].id)

    def arr(name: str) -> Any:
        if name not in arrays:
            arrays[name] = z3.Array(name, isort, vsort)
        return arrays[name]

    def scal(name: str) -> Any:
        if name not in scalars:
            scalars[name] = z3.Const(name, vsort)
        return scalars[name]

    def term(node: ast.AST) -> Any:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid == "select" and len(node.args) == 2:
                return z3.Select(term(node.args[0]), term(node.args[1]))
            if fid == "store" and len(node.args) == 3:
                return z3.Store(term(node.args[0]), term(node.args[1]), term(node.args[2]))
            raise SmtParseError("array calls are select(a,i) or store(a,i,v)")
        if isinstance(node, ast.BinOp):
            a, b = term(node.left), term(node.right)
            if isinstance(node.op, ast.Add):
                return a + b
            if isinstance(node.op, ast.Sub):
                return a - b
            if isinstance(node.op, ast.Mult):
                return a * b
            raise SmtParseError(f"unsupported scalar operator: {type(node.op).__name__}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -term(node.operand)
        if isinstance(node, ast.Name):
            return arr(node.id) if node.id in array_names else scal(node.id)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return z3.RealVal(node.value) if value_sort == "Real" else z3.IntVal(node.value)
        raise SmtParseError(f"disallowed array/scalar node: {type(node).__name__}")

    def formula(node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            parts = [formula(v) for v in node.values]
            return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return z3.Not(formula(node.operand))
        if isinstance(node, ast.Compare):
            left = term(node.left)
            clauses = []
            for op, comp in zip(node.ops, node.comparators):
                right = term(comp)
                fn = {ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
                      ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
                      ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b}.get(type(op))
                if fn is None:
                    raise SmtParseError(f"unsupported comparison: {type(op).__name__}")
                clauses.append(fn(left, right))
                left = right
            return clauses[0] if len(clauses) == 1 else z3.And(*clauses)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("implies", "iff"):
            if len(node.args) != 2:
                raise SmtParseError(f"{node.func.id} requires exactly 2 arguments")
            a, b = formula(node.args[0]), formula(node.args[1])
            return z3.Implies(a, b) if node.func.id == "implies" else (a == b)
        raise SmtParseError("array formulas: ==/!=/<.., and/or/not, implies/iff over select/store terms")

    try:
        a_z3 = [formula(_parse(a)) for a in assumptions]
        g_z3 = formula(_parse(goal)) if goal is not None else None
    except z3.Z3Exception as exc:
        raise SmtParseError(f"sort error (mixed array/scalar use?): {exc}") from exc

    def read_model(m: z3.ModelRef) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name, c in sorted(scalars.items()):
            val = m.eval(c, model_completion=True)
            out[name] = val.as_long() if z3.is_int_value(val) else str(val)
        return out

    return a_z3, g_z3, read_model


def check_arrays(assumptions: list[str], goal: str | None = None, index_sort: str = "Int",
                 value_sort: str = "Int", *, timeout_ms: int = DEFAULT_TIMEOUT_MS,
                 seed: int = DEFAULT_SEED) -> ReasoningResult:
    """Reason about arrays with `select(a, i)` and `store(a, i, v)` (array theory).

    A name first used as the array argument of select/store is an array; other names
    are scalars of `value_sort` ('Int'/'Real'). The McCarthy axioms are built in, e.g.
    `select(store(a, i, v), i) == v` is entailed. `goal` → entailment; `goal=None` →
    consistency.
    """
    return _run(assumptions, goal, lambda a, g: _arr_translate(a, g, index_sort, value_sort),
                "arrays", seed, timeout_ms)


# =========================================================================== #
# 4) STRINGS / SEQUENCES
# =========================================================================== #
def _str_translate(assumptions: list[str], goal: str | None):
    syms: dict[str, Any] = {}

    def var(name: str) -> Any:
        if name not in syms:
            syms[name] = z3.String(name)
        return syms[name]

    def term(node: ast.AST) -> Any:
        if isinstance(node, ast.Name):
            return var(node.id)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return z3.StringVal(node.value)
            if isinstance(node.value, int) and not isinstance(node.value, bool):
                return z3.IntVal(node.value)
            raise SmtParseError("string constants are text or integers")
        if isinstance(node, ast.BinOp):
            a, b = term(node.left), term(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
                a_str, b_str = _is_seq(a), _is_seq(b)
                if isinstance(node.op, ast.Add) and a_str and b_str:
                    return z3.Concat(a, b)
                if not a_str and not b_str:  # integer arithmetic (e.g. on lengths)
                    return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b}[type(node.op)]
                raise SmtParseError("'+' joins two strings or two integers, not a mix")
            raise SmtParseError(f"unsupported string operator: {type(node.op).__name__}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid, args = node.func.id, [term(a) for a in node.args]
            if fid == "length" and len(args) == 1:
                return z3.Length(args[0])
            if fid == "concat" and len(args) >= 2:
                return z3.Concat(*args)
            if fid == "at" and len(args) == 2:
                return z3.SubString(args[0], args[1], z3.IntVal(1))
            raise SmtParseError(f"unsupported string function: {fid}")
        raise SmtParseError(f"disallowed string node: {type(node).__name__}")

    def formula(node: ast.AST) -> Any:
        if isinstance(node, ast.BoolOp):
            parts = [formula(v) for v in node.values]
            return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return z3.Not(formula(node.operand))
        if isinstance(node, ast.Compare):
            left = term(node.left)
            clauses = []
            for op, comp in zip(node.ops, node.comparators):
                right = term(comp)
                if isinstance(op, ast.Eq):
                    clauses.append(left == right)
                elif isinstance(op, ast.NotEq):
                    clauses.append(left != right)
                elif type(op) in (ast.Lt, ast.LtE, ast.Gt, ast.GtE):
                    if _is_seq(left) or _is_seq(right):
                        raise SmtParseError("order comparisons apply to integers (e.g. length), not strings")
                    clauses.append({ast.Lt: left < right, ast.LtE: left <= right,
                                    ast.Gt: left > right, ast.GtE: left >= right}[type(op)])
                else:
                    raise SmtParseError(f"unsupported comparison: {type(op).__name__}")
                left = right
            return clauses[0] if len(clauses) == 1 else z3.And(*clauses)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fid = node.func.id
            if fid in ("implies", "iff"):
                if len(node.args) != 2:
                    raise SmtParseError(f"{fid} requires exactly 2 arguments")
                a, b = formula(node.args[0]), formula(node.args[1])
                return z3.Implies(a, b) if fid == "implies" else (a == b)
            args = [term(a) for a in node.args]
            if fid == "contains" and len(args) == 2:
                return z3.Contains(args[0], args[1])
            if fid == "prefixof" and len(args) == 2:
                return z3.PrefixOf(args[0], args[1])
            if fid == "suffixof" and len(args) == 2:
                return z3.SuffixOf(args[0], args[1])
            raise SmtParseError(f"unsupported string predicate: {fid}")
        raise SmtParseError("string formulas: ==/!=, contains/prefixof/suffixof, and/or/not, implies/iff")

    try:
        a_z3 = [formula(_parse(a)) for a in assumptions]
        g_z3 = formula(_parse(goal)) if goal is not None else None
    except z3.Z3Exception as exc:
        raise SmtParseError(f"string sort error: {exc}") from exc

    def read_model(m: z3.ModelRef) -> dict[str, Any]:
        out = {}
        for name, c in sorted(syms.items()):
            val = m.eval(c, model_completion=True)
            out[name] = val.as_string() if hasattr(val, "as_string") else str(val)
        return out

    return a_z3, g_z3, read_model


def _is_seq(z: Any) -> bool:
    try:
        return z.sort().kind() == z3.Z3_SEQ_SORT
    except Exception:  # noqa: BLE001
        return False


def check_strings(assumptions: list[str], goal: str | None = None, *,
                  timeout_ms: int = DEFAULT_TIMEOUT_MS,
                  seed: int = DEFAULT_SEED) -> ReasoningResult:
    """Reason about strings/sequences (string theory).

    Terms: string variables, `"literals"`, `+`/`concat(...)` (concatenation),
    `length(s)`, `at(s, i)`. Predicates: `contains`, `prefixof`, `suffixof`, plus
    `==`/`!=` and integer comparisons on lengths. `goal` → entailment (e.g.
    `length(x + y) == length(x) + length(y)` is valid); `goal=None` → consistency
    (e.g. `["x + \"b\" == \"ab\""]` → sat with `x = "a"`).
    """
    return _run(assumptions, goal, _str_translate, "strings", seed, timeout_ms)
