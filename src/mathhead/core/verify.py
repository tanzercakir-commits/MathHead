"""
mathhead.core.verify — VERIFICATION LAYER (auditor of AI reasoning).

**The differentiating idea (ROADMAP Track C):** AI is non-deterministic and makes
things up; MathHead AUDITS deterministically. This layer is "propose-and-audit": an
AI (or human) presents a mathematical CLAIM (this expression equals that / these
values are solutions / this chain of steps is correct), MathHead independently
verifies it and provides **counterexample + proof**.

This is the difference that turns the product from "yet another calculator" into a
*judge* of AI reasoning. Rival CASs give an answer; we VERIFY the answer.

Honesty walls (deliberately surfaced):
- **Domain trap:** `(x²-1)/(x-1)` and `x+1` look symbolically equal but the former
  is undefined at `x=1`. Equality is qualified as "on the common domain" and the
  divergence points are reported (the error a naive equality check MISSES — the one
  we catch).
- **Completeness:** we cannot always verify that a solution set is COMPLETE (e.g. a
  transcendental equation). This case is reported first-class as `unknown`.

Security: input is still filtered through the compute layer's ast-whitelist parser.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any

import sympy

from mathhead.compute import (
    ComputeError,
    _meta,
    _parse,
    _parse_matrix,
    _parse_point,
    _symbol,
)

__all__ = [
    "verify_equality", "verify_solution", "verify_steps",
    "verify_limit", "verify_derivative", "verify_integral",
    "verify_series", "verify_matrix_identity", "verify_derivation",
]

_SAMPLE = (0, 1, 2, -1, 3, -2, 5)   # set of points for counterexample scanning


@dataclass
class VerifyResult:
    """Verification output — shared contract (status/reason_code/explanation/meta)."""

    status: str                       # valid | invalid | unknown | error
    reason_code: str
    explanation: str
    details: dict[str, Any] | None = None    # counterexample / missing-extra / first bad step
    meta: dict[str, Any] = field(default_factory=dict)


def _err(operation: str, msg: str, t0: float) -> VerifyResult:
    return VerifyResult("error", "PARSE_ERROR", f"{operation}: {msg}", None, _meta(t0))


def _as_expr(value: str, syms: dict[str, Any]) -> Any:
    """Parses the expression; rejects an equation (Eq) if given (an expression is expected here)."""
    parsed = _parse(value, syms)
    if isinstance(parsed, sympy.Equality):
        raise ComputeError("an expression is expected here, not an equation")
    return parsed


def _counterexample(diff: Any, syms: dict[str, Any]) -> dict[str, Any] | None:
    """Finds a concrete point where `diff` (= left - right) is nonzero."""
    free = sorted(diff.free_symbols, key=str)
    if not free:
        val = sympy.simplify(diff)
        return None if val == 0 else {"value": str(val)}
    combos = itertools.product(_SAMPLE, repeat=len(free))
    for i, combo in enumerate(combos):
        if i > 400:                    # scan limit (honest: not exhaustive)
            break
        subs = dict(zip(free, combo))
        try:
            val = sympy.simplify(diff.subs(subs))
        except Exception:              # noqa: BLE001
            continue
        if val.is_number and val != 0 and val.is_finite:
            point = {str(s): int(v) for s, v in subs.items()}
            return {"point": point, "difference": str(val)}
    return None


def _domain_diff(left: Any, right: Any) -> list[str]:
    """Collects the (singularity) points where the two expressions' domains diverge."""
    out: set[str] = set()
    for s in sorted(left.free_symbols | right.free_symbols, key=str):
        try:
            sl = sympy.singularities(left, s)
            sr = sympy.singularities(right, s)
        except Exception:              # noqa: BLE001
            continue
        for a, b in ((sl, sr), (sr, sl)):
            if getattr(a, "is_FiniteSet", False):
                for p in a:
                    try:
                        if not (getattr(b, "is_FiniteSet", False) and p in b):
                            out.add(f"{s}={p}")
                    except TypeError:
                        continue
    return sorted(out)


def _equal_verdict(le: Any, re: Any, syms: dict[str, Any]) -> tuple[str, dict | None]:
    """DETERMINISTIC equality decision: ('equal'|'not_equal'|'undecided', counterexample?).

    SymPy `.equals()` is NOT USED — it does internal RANDOM sampling (same input →
    varying result), which would violate the determinism principle (ADR-0019).
    Instead: (1) `simplify(left - right) == 0` → equal (deterministic), (2) fixed
    sample-point counterexample scan → if not, `not_equal` + proof, (3) otherwise
    `undecided`.
    """
    diff = le - re
    try:
        simplified = sympy.simplify(diff)
    except Exception:                        # noqa: BLE001
        simplified = diff
    if simplified == 0:
        return "equal", None
    cx = _counterexample(simplified, syms)
    if cx is not None:
        return "not_equal", cx
    return "undecided", None


def verify_equality(left: str, right: str) -> VerifyResult:
    """Are `left` and `right` mathematically EQUAL? (audits an AI's "= equals this"
    claim.)

    valid → equal; and if the domains diverge, the divergence points are reported
    via `EQUAL_ON_COMMON_DOMAIN` (domain trap). invalid → `details.counterexample`
    is a concrete point where they differ. unknown → could not decide (honest).
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        left_e = _as_expr(left, syms)
        right_e = _as_expr(right, syms)
    except ComputeError as exc:
        return _err("verify_equality", str(exc), t0)

    verdict, cx = _equal_verdict(left_e, right_e, syms)
    if verdict == "equal":
        caveat = _domain_diff(left_e, right_e)
        if caveat:
            return VerifyResult(
                "valid", "EQUAL_ON_COMMON_DOMAIN",
                f"equal on the common domain; BUT the domains diverge at: "
                f"{', '.join(caveat)} (NOT unconditionally equal).",
                {"domain_caveat": caveat}, _meta(t0))
        return VerifyResult("valid", "EQUAL", "the expressions are equal (verified).", None, _meta(t0))
    if verdict == "not_equal":
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"NOT equal; counterexample: {cx}.", {"counterexample": cx}, _meta(t0))
    return VerifyResult("unknown", "UNDECIDED",
                        "equality could not be decided (honest: neither proof nor refutation).",
                        None, _meta(t0))


def verify_solution(equation: str, symbol: str, claimed: list[str]) -> VerifyResult:
    """Are the `claimed` values solutions of `equation` — and are they COMPLETE?
    (audits an AI's "here are the solutions" claim.)

    Each value is checked by substitution; also compared against the true solution
    set and reported as MISSING/EXTRA. valid → correct + complete; invalid → wrong
    value or missing; unknown → the values hold but COMPLETENESS could not be
    verified (e.g. transcendental).
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(claimed, list) or not claimed:
            raise ComputeError("the claimed solution list cannot be empty")
        parsed = _parse(equation, syms)
        expr = (parsed.lhs - parsed.rhs) if isinstance(parsed, sympy.Equality) else parsed
        var = _symbol(symbol, syms)
        claimed_vals = [_parse(c, syms) for c in claimed]
    except ComputeError as exc:
        return _err("verify_solution", str(exc), t0)

    checks = []
    for c in claimed_vals:
        try:
            residual = sympy.simplify(expr.subs(var, c))
            ok = bool(residual == 0)
        except Exception:                    # noqa: BLE001
            ok = False
        checks.append({"value": str(c), "satisfies": ok})
    wrong = [d["value"] for d in checks if not d["satisfies"]]

    # completeness: try to find the true solution set
    actual = None
    try:
        actual = set(sympy.solve(expr, var))
    except (NotImplementedError, Exception):  # noqa: BLE001
        actual = None

    details: dict[str, Any] = {"checks": checks}
    if wrong:
        details["wrong_values"] = wrong
        return VerifyResult("invalid", "SOLUTION_INCORRECT",
                            f"these claimed values are NOT solutions: {wrong}.",
                            details, _meta(t0))
    if actual is None:
        return VerifyResult("unknown", "COMPLETENESS_UNKNOWN",
                            "the claimed values are solutions; BUT whether they are all of them "
                            "could not be verified (the solution set was not found in closed form).",
                            details, _meta(t0))
    claimed_set = set(claimed_vals)
    missing = sorted((actual - claimed_set), key=str)
    if missing:
        details["missing"] = [str(m) for m in missing]
        return VerifyResult("invalid", "SOLUTION_INCOMPLETE",
                            f"the values are correct but INCOMPLETE; missing solutions: "
                            f"{details['missing']}.", details, _meta(t0))
    return VerifyResult("valid", "SOLUTION_VERIFIED",
                        "the claimed solutions are correct and COMPLETE (verified).",
                        details, _meta(t0))


def verify_steps(steps: list[str]) -> VerifyResult:
    """Audits a chain of expressions (each step must be EQUAL to the previous one)
    and finds the FIRST bad transition. ("grades" an AI's step-by-step solution.)

    valid → all transitions equal; invalid → `details.first_bad_step` (1-based) the
    first broken transition + counterexample; unknown → a transition could not be
    decided.
    """
    import time
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(steps, list) or len(steps) < 2:
            raise ComputeError("at least 2 steps are required")
        exprs = [_as_expr(s, syms) for s in steps]
    except ComputeError as exc:
        return _err("verify_steps", str(exc), t0)

    undecided_at = None
    for i in range(len(exprs) - 1):
        verdict, cx = _equal_verdict(exprs[i], exprs[i + 1], syms)
        if verdict == "not_equal":
            return VerifyResult(
                "invalid", "STEP_INVALID",
                f"the transition from step {i + 1} to step {i + 2} is WRONG "
                f"('{steps[i]}' ≠ '{steps[i + 1]}').",
                {"first_bad_step": i + 1, "from": steps[i], "to": steps[i + 1],
                 "counterexample": cx}, _meta(t0))
        if verdict == "undecided" and undecided_at is None:
            undecided_at = i + 1
    if undecided_at is not None:
        return VerifyResult("unknown", "UNDECIDED",
                            f"transition {undecided_at} could not be decided; the rest are consistent.",
                            {"undecided_step": undecided_at}, _meta(t0))
    return VerifyResult("valid", "STEPS_VALID",
                        f"all transitions of the {len(exprs)} steps are equal (verified).",
                        None, _meta(t0))


# --------------------------------------------------------------------------- #
# I1 — more claim types: limit / derivative / integral / series / matrix identity.
# All are "the AI's claim ≟ the independently computed truth" — audited by
# deterministic equality (EQUAL/NOT_EQUAL/UNDECIDED). Integral: differentiate-and-
# compare (honest).
# --------------------------------------------------------------------------- #
def _from_verdict(op: str, claimed: str, computed_desc: str,
                  le: Any, re: Any, syms: dict[str, Any], t0: float) -> VerifyResult:
    """Is `le` (claim) equal to `re` (computed) → produces a shared VerifyResult."""
    verdict, cx = _equal_verdict(le, re, syms)
    if verdict == "equal":
        return VerifyResult("valid", "EQUAL",
                            f"{op}: the claim is correct (= {computed_desc}).", None, _meta(t0))
    if verdict == "not_equal":
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"{op}: the claim is WRONG. Correct: {computed_desc}. Counterexample: {cx}.",
                            {"claimed": claimed, "correct": computed_desc, "counterexample": cx},
                            _meta(t0))
    return VerifyResult("unknown", "UNDECIDED",
                        f"{op}: could not decide (claim: {claimed}, computed: {computed_desc}).",
                        None, _meta(t0))


def verify_derivative(expression: str, symbol: str, claimed: str,
                      order: int = 1) -> VerifyResult:
    """Is `d^order/d{symbol}^order (expression)` really `claimed`? (AI derivative claim.)"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("the derivative order must be an integer >= 1")
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_derivative", str(exc), t0)
    try:
        computed = sympy.diff(expr, var, order)
    except Exception as exc:  # noqa: BLE001
        return _err("verify_derivative", f"could not differentiate: {exc}", t0)
    return _from_verdict("derivative", claimed, str(computed), claimed_e, computed, syms, t0)


def verify_integral(expression: str, symbol: str, claimed: str) -> VerifyResult:
    """Is `∫ expression d{symbol}` really `claimed`? (a constant difference is tolerated.)

    HONEST method: differentiate `claimed` and check whether it equals `expression`
    (so the +C ambiguity is naturally overcome).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_integral", str(exc), t0)
    try:
        d_claimed = sympy.diff(claimed_e, var)
    except Exception as exc:  # noqa: BLE001
        return _err("verify_integral", f"could not differentiate: {exc}", t0)
    res = _from_verdict("integral", claimed, f"its derivative {d_claimed}", d_claimed, expr, syms, t0)
    if res.status == "valid":
        res.explanation = (f"integral: the claim is correct — d/d{symbol}({claimed}) = {expr} "
                           f"(a constant difference is tolerated).")
    return res


def verify_limit(expression: str, symbol: str, point: str, claimed: str) -> VerifyResult:
    """Is `lim {symbol}→{point} expression` really `claimed`? (`point`/`claimed` may be `oo`.)"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
        claimed_v = _parse_point(str(claimed), syms)
    except ComputeError as exc:
        return _err("verify_limit", str(exc), t0)
    try:
        actual = sympy.limit(expr, var, pt)
    except Exception as exc:  # noqa: BLE001
        return VerifyResult("unknown", "UNDECIDED",
                            f"limit: could not be computed independently ({exc}).", None, _meta(t0))
    equal = False
    try:
        equal = bool(actual == claimed_v) or bool(sympy.simplify(actual - claimed_v) == 0)
    except Exception:  # noqa: BLE001
        equal = bool(actual == claimed_v)
    if equal:
        return VerifyResult("valid", "EQUAL",
                            f"limit: the claim is correct (lim {symbol}→{point} = {actual}).",
                            None, _meta(t0))
    return VerifyResult("invalid", "NOT_EQUAL",
                        f"limit: the claim is WRONG. Correct limit: {actual} (claim: {claimed}).",
                        {"claimed": str(claimed), "correct": str(actual)}, _meta(t0))


def verify_series(expression: str, symbol: str, point: str, order: int,
                  claimed: str) -> VerifyResult:
    """Is `expression`'s order-`order` Taylor expansion around `{symbol}={point}` the `claimed` one?"""
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(order, int) or order < 1:
            raise ComputeError("order must be an integer >= 1")
        expr = _as_expr(expression, syms)
        var = _symbol(symbol, syms)
        pt = _parse_point(str(point), syms)
        claimed_e = _as_expr(claimed, syms)
    except ComputeError as exc:
        return _err("verify_series", str(exc), t0)
    try:
        computed = expr.series(var, pt, order).removeO()
    except Exception as exc:  # noqa: BLE001
        return _err("verify_series", f"could not expand the series: {exc}", t0)
    return _from_verdict("series", claimed, str(computed), claimed_e, computed, syms, t0)


def verify_matrix_identity(left: list[list[str]], right: list[list[str]]) -> VerifyResult:
    """Are two matrices (including symbolic cells) EQUAL? (AI matrix identity claim.)

    If the dimensions differ, `NOT_EQUAL`; otherwise each cell is audited by
    deterministic equality, and the first differing cell + counterexample is reported.
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        A = _parse_matrix(left, syms)
        B = _parse_matrix(right, syms)
    except ComputeError as exc:
        return _err("verify_matrix_identity", str(exc), t0)
    if (A.rows, A.cols) != (B.rows, B.cols):
        return VerifyResult("invalid", "NOT_EQUAL",
                            f"the matrix dimensions differ: {A.rows}×{A.cols} ≠ {B.rows}×{B.cols}.",
                            {"left_shape": [A.rows, A.cols], "right_shape": [B.rows, B.cols]},
                            _meta(t0))
    undecided = None
    for i in range(A.rows):
        for j in range(A.cols):
            verdict, cx = _equal_verdict(A[i, j], B[i, j], syms)
            if verdict == "not_equal":
                return VerifyResult("invalid", "NOT_EQUAL",
                                    f"the matrices differ: cell [{i}][{j}] is not equal "
                                    f"({A[i, j]} ≠ {B[i, j]}).",
                                    {"cell": [i, j], "left": str(A[i, j]),
                                     "right": str(B[i, j]), "counterexample": cx}, _meta(t0))
            if verdict == "undecided" and undecided is None:
                undecided = [i, j]
    if undecided is not None:
        return VerifyResult("unknown", "UNDECIDED",
                            f"cell [{undecided[0]}][{undecided[1]}] could not be decided; "
                            f"the rest are equal.", {"undecided_cell": undecided}, _meta(t0))
    return VerifyResult("valid", "EQUAL",
                        f"the matrices are equal ({A.rows}×{A.cols}, all cells verified).",
                        None, _meta(t0))


# --------------------------------------------------------------------------- #
# I3 — full derivation check: REPLAY each cited operation and confirm it really
# produces the next line (equation- or expression-aware). This is the JUSTIFICATION
# audit — not just "are consecutive lines equal?" (verify_steps), but "does the RULE
# you cited actually yield this step?". Grades a worked solution the way a teacher does.
# --------------------------------------------------------------------------- #
_DERIV_OPS = frozenset({"add", "subtract", "multiply", "divide",
                        "simplify", "expand", "factor"})
_VALUE_OPS = frozenset({"add", "subtract", "multiply", "divide"})


def _stmt_str(node: Any) -> str:
    """Renders a parsed step (equation or expression) back to a readable string."""
    if isinstance(node, sympy.Equality):
        return f"{node.lhs} == {node.rhs}"
    return str(node)


def _describe(op: str, value: Any) -> str:
    return f"{op} {value}" if value is not None else op


def _apply_operation(prev: Any, op: str, value: Any) -> Any:
    """Applies ONE cited operation to `prev` (an equation applies to both sides)."""
    is_eq = isinstance(prev, sympy.Equality)
    sides = [prev.lhs, prev.rhs] if is_eq else [prev]
    if op == "add":
        out = [s + value for s in sides]
    elif op == "subtract":
        out = [s - value for s in sides]
    elif op == "multiply":
        out = [s * value for s in sides]
    elif op == "divide":
        out = [s / value for s in sides]
    elif op == "simplify":
        out = [sympy.simplify(s) for s in sides]
    elif op == "expand":
        out = [sympy.expand(s) for s in sides]
    else:  # factor (op set is validated by the caller)
        out = [sympy.factor(s) for s in sides]
    return sympy.Eq(out[0], out[1]) if is_eq else out[0]


def _same_statement(expected: Any, actual: Any, syms: dict[str, Any]) -> tuple[str, dict | None]:
    """Deterministically decides whether two steps state the SAME thing.

    Both must be equations or both expressions. For equations `L1==R1` and
    `L2==R2`, they match if `(L1-R1)` equals `(L2-R2)` up to sign (sides may be
    swapped/negated). Returns ('equal'|'not_equal'|'undecided', counterexample?).
    """
    e_eq = isinstance(expected, sympy.Equality)
    a_eq = isinstance(actual, sympy.Equality)
    if e_eq != a_eq:
        return "not_equal", {"reason": "equation/expression type mismatch"}
    if e_eq:
        de = expected.lhs - expected.rhs
        da = actual.lhs - actual.rhs
        if _equal_verdict(de, da, syms)[0] == "equal":
            return "equal", None
        if _equal_verdict(de, -da, syms)[0] == "equal":
            return "equal", None
        try:
            cx = _counterexample(sympy.simplify(de - da), syms)
        except Exception:              # noqa: BLE001
            cx = None
        return ("not_equal", cx) if cx is not None else ("undecided", None)
    return _equal_verdict(expected, actual, syms)


def verify_derivation(steps: list[str], operations: list[dict[str, Any]]) -> VerifyResult:
    """Audits a multi-step derivation where each transition CITES an operation.

    For each transition the cited `operation` is REPLAYED on the previous line and
    the result is compared (deterministically) to the stated next line. This checks
    the JUSTIFICATION of each step — not merely that consecutive lines are equal.

    `steps`: list of >=2 strings, each an equation ('L == R') or an expression.
    `operations`: list with exactly `len(steps)-1` entries; each a dict
    `{"op": <add|subtract|multiply|divide|simplify|expand|factor>, "value": <str>}`
    (`value` is required for add/subtract/multiply/divide, ignored otherwise).

    valid → `DERIVATION_VALID` (every step follows from its cited operation).
    invalid → `STEP_UNJUSTIFIED` (`details.first_bad_step`, 1-based) — the cited
    operation does NOT produce the stated line (+ what it WOULD produce). unknown →
    `UNDECIDED`. error → `PARSE_ERROR` / `GUARDRAIL_VIOLATION` (bad or unusable input).
    """
    t0 = time.perf_counter()
    syms: dict[str, Any] = {}
    try:
        if not isinstance(steps, list) or len(steps) < 2:
            raise ComputeError("at least 2 steps are required")
        if not isinstance(operations, list) or len(operations) != len(steps) - 1:
            raise ComputeError("operations must have exactly len(steps)-1 entries (one per transition)")
        parsed = [_parse(s, syms) for s in steps]
    except ComputeError as exc:
        return _err("verify_derivation", str(exc), t0)

    # Validate + normalize operations up front (fail fast, honestly).
    normalized: list[tuple[str, Any]] = []
    for k, spec in enumerate(operations):
        if not isinstance(spec, dict) or "op" not in spec:
            return VerifyResult("error", "GUARDRAIL_VIOLATION",
                                f"verify_derivation: operation {k + 1} must be a dict with an 'op' key.",
                                None, _meta(t0))
        op = str(spec["op"]).strip().lower()
        if op not in _DERIV_OPS:
            return VerifyResult("error", "GUARDRAIL_VIOLATION",
                                f"verify_derivation: unknown operation {op!r} "
                                f"(supported: {', '.join(sorted(_DERIV_OPS))}).", None, _meta(t0))
        value = None
        if op in _VALUE_OPS:
            if spec.get("value") in (None, ""):
                return VerifyResult("error", "GUARDRAIL_VIOLATION",
                                    f"verify_derivation: operation '{op}' (step {k + 1}) requires a 'value'.",
                                    None, _meta(t0))
            try:
                value = _as_expr(str(spec["value"]), syms)
            except ComputeError as exc:
                return _err("verify_derivation", f"operation {k + 1} value: {exc}", t0)
            if op == "divide" and sympy.simplify(value) == 0:
                return VerifyResult("error", "GUARDRAIL_VIOLATION",
                                    f"verify_derivation: cannot divide by zero (step {k + 1}).",
                                    None, _meta(t0))
        normalized.append((op, value))

    undecided_at = None
    caveats: list[str] = []
    for i, (op, value) in enumerate(normalized):
        try:
            expected = _apply_operation(parsed[i], op, value)
            verdict, cx = _same_statement(expected, parsed[i + 1], syms)
        except Exception:              # noqa: BLE001
            undecided_at = undecided_at or (i + 1)
            continue
        # Honesty wall: multiply/divide by a non-constant may change the solution set.
        if op in ("multiply", "divide") and value is not None and value.free_symbols:
            caveats.append(f"step {i + 1}: '{op}' by a non-constant ({value}) may change the solution set")
        if verdict == "not_equal":
            return VerifyResult(
                "invalid", "STEP_UNJUSTIFIED",
                f"step {i + 2} is NOT justified: applying '{_describe(op, value)}' to "
                f"'{steps[i]}' gives '{_stmt_str(expected)}', not '{steps[i + 1]}'.",
                {"first_bad_step": i + 1, "operation": _describe(op, value),
                 "from": steps[i], "expected": _stmt_str(expected),
                 "claimed_next": steps[i + 1], "counterexample": cx}, _meta(t0))
        if verdict == "undecided" and undecided_at is None:
            undecided_at = i + 1
    if undecided_at is not None:
        return VerifyResult("unknown", "UNDECIDED",
                            f"transition {undecided_at} could not be decided; the rest are justified.",
                            {"undecided_step": undecided_at,
                             "domain_caveats": caveats or None}, _meta(t0))
    details: dict[str, Any] = {"steps": len(steps)}
    if caveats:
        details["domain_caveats"] = caveats
    return VerifyResult("valid", "DERIVATION_VALID",
                        f"all {len(operations)} steps are justified by their cited operations"
                        + (" (with domain caveats)." if caveats else " (verified)."),
                        details, _meta(t0))
