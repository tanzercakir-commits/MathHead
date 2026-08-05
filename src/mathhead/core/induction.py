"""
mathhead.core.induction — Mathematical induction (ROADMAP H1).

Z3 cannot do induction natively: the induction *schema* is not part of first-order
SMT, so a naive `∀n. P(n)` query over nonlinear integer arithmetic simply returns
`unknown`. This module adds induction as a **sound meta-rule** layered on Z3.

    To prove   ∀ n ≥ start. P(n):
      1) BASE:  P(start) holds                        (Z3: ¬P(start) is UNSAT)
      2) STEP:  ∀ k ≥ start. P(k) → P(k+1)            (Z3: P(k) ∧ k≥start ∧ ¬P(k+1) UNSAT)
    If BOTH subgoals hold, the induction principle yields ∀ n ≥ start. P(n).

Each subgoal is an ordinary arithmetic satisfiability check that Z3 CAN often
decide (linear/nonlinear integer arithmetic — LIA/NIA). Honesty (PRINCIPLES 2/3):

  * BASE fails  → the claim is FALSE (n=start is a concrete counterexample) → `invalid`.
  * STEP fails  → this induction is INCONCLUSIVE (the claim might still be true by
                  another argument) → `unknown` (never `invalid`; we do not overclaim).
  * Z3 `unknown` on a subgoal (typical for hard nonlinear steps) → `unknown`,
                  reported plainly — we NEVER fabricate a "proved".

Grammar (a single integer variable): `+  -  *  **`(constant natural exponent)
`%`(mod) `//`(floor-div), chained comparisons, `and/or/not`, `implies(a, b)`.
Nonlinear products ARE allowed here (unlike the linear logic kernel) because the
whole point of induction is polynomial identities / divisibilities / inequalities.
Any free name other than the induction variable is rejected (no silent
assumptions — Wall #2).
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS
from mathhead.guardrails import GuardrailError, solver_config, validate_input

_MAX_EXPONENT = 12  # cap ** expansion so a request cannot blow up the encoding


class InductionParseError(ValueError):
    """The induction claim violates the (single-variable integer) grammar."""


@dataclass
class InductionResult:
    """Output of `prove_by_induction`."""

    status: str                                  # valid | invalid | unknown | error
    reason_code: str                             # PROVED_BY_INDUCTION | BASE_FAILED | ...
    explanation: str
    base_case: dict[str, Any] | None = None      # {"claim", "at", "holds", ...}
    inductive_step: dict[str, Any] | None = None  # {"claim", "holds", "counterexample"?}
    proof_steps: list[dict[str, Any]] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, seed: int, timeout_ms: int) -> dict[str, Any]:
    return {
        "engine": "z3+induction",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


# --------------------------------------------------------------------------- #
# ast -> Z3 (single integer variable, nonlinear arithmetic allowed)
# --------------------------------------------------------------------------- #
def _build(node: ast.AST, var: str, k: Any) -> Any:
    """Translate an ast node to a Z3 expression over the single integer var `k`."""
    if isinstance(node, ast.BoolOp):
        parts = [_build(v, var, k) for v in node.values]
        return z3.And(*parts) if isinstance(node.op, ast.And) else z3.Or(*parts)
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return z3.Not(_build(node.operand, var, k))
        if isinstance(node.op, ast.USub):
            return -_build(node.operand, var, k)
        if isinstance(node.op, ast.UAdd):
            return _build(node.operand, var, k)
        raise InductionParseError(f"unsupported unary operator: {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _build(node.left, var, k)
        clauses = []
        for op, comp in zip(node.ops, node.comparators):
            right = _build(comp, var, k)
            fn = {
                ast.Lt: lambda a, b: a < b, ast.LtE: lambda a, b: a <= b,
                ast.Gt: lambda a, b: a > b, ast.GtE: lambda a, b: a >= b,
                ast.Eq: lambda a, b: a == b, ast.NotEq: lambda a, b: a != b,
            }.get(type(op))
            if fn is None:
                raise InductionParseError(f"unsupported comparison: {type(op).__name__}")
            clauses.append(fn(left, right))
            left = right
        return clauses[0] if len(clauses) == 1 else z3.And(*clauses)
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Pow):
            if not (isinstance(node.right, ast.Constant) and isinstance(node.right.value, int)
                    and not isinstance(node.right.value, bool) and 0 <= node.right.value <= _MAX_EXPONENT):
                raise InductionParseError(
                    f"exponent must be a constant integer in 0..{_MAX_EXPONENT}")
            base = _build(node.left, var, k)
            result: Any = z3.IntVal(1)
            for _ in range(node.right.value):
                result = result * base          # expand into products (NIA-friendly)
            return result
        left = _build(node.left, var, k)
        right = _build(node.right, var, k)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.FloorDiv):
            return left / right                 # Z3 Int division is Euclidean floor-div
        raise InductionParseError(f"unsupported operator: {type(node.op).__name__}")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id == "implies" and len(node.args) == 2:
            return z3.Implies(_build(node.args[0], var, k), _build(node.args[1], var, k))
        raise InductionParseError(f"only implies(a, b) is a supported call (got {node.func.id!r})")
    if isinstance(node, ast.Name):
        if node.id != var:
            raise InductionParseError(
                f"unexpected symbol {node.id!r}; induction has a single variable {var!r}")
        return k
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            return z3.BoolVal(node.value)
        if isinstance(node.value, int):
            return z3.IntVal(node.value)
        raise InductionParseError("only integer constants are allowed (induction is over integers)")
    raise InductionParseError(f"disallowed expression node: {type(node).__name__}")


def _parse_claim(claim: str, var: str, k: Any) -> Any:
    if not isinstance(claim, str) or not claim.strip():
        raise InductionParseError("claim must be a non-empty string")
    try:
        tree = ast.parse(claim, mode="eval")
    except SyntaxError as exc:
        raise InductionParseError(f"syntax error: {exc.msg}") from exc
    try:
        expr = _build(tree.body, var, k)
    except z3.Z3Exception as exc:
        # e.g. a logical connective over non-boolean operands ('not(0)', 'implies(0,0) and n>1')
        # — syntactically admitted, ill-typed for Z3; a clean parse error, never a crash
        # (found by the K2 parser fuzzer).
        raise InductionParseError(f"ill-typed formula: {exc}") from exc
    if not z3.is_bool(expr):
        raise InductionParseError("the claim must be a boolean formula (a (in)equality or logical combination)")
    return expr


def _check(assertions: list[Any], timeout_ms: int, seed: int):
    """Return (z3-result, model-or-None) for the conjunction of `assertions`."""
    solver = solver_config(timeout_ms, seed)
    for a in assertions:
        solver.add(a)
    res = solver.check()
    return res, (solver.model() if res == z3.sat else None), solver


def prove_by_induction(
    claim: str,
    var: str = "n",
    start: int = 0,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> InductionResult:
    """Prove `∀ {var} ≥ {start}. {claim}` by mathematical induction.

    `claim` is a boolean formula over the single integer variable `var`
    (e.g. `"(n*(n+1)) % 2 == 0"`, `"n**2 >= n"`, `"(n**3 - n) % 3 == 0"`).

    Method: Z3 checks the BASE case and the INDUCTIVE STEP; the induction principle
    (a sound meta-rule) then yields the universal conclusion. See the module
    docstring for the honesty contract (base-fail → invalid; step-fail/solver-unknown
    → unknown — never a fabricated proof).
    """
    t0 = time.perf_counter()
    if not isinstance(var, str) or not var.isidentifier():
        return InductionResult("error", "GUARDRAIL_VIOLATION",
                               "var must be a valid identifier", meta=_meta(t0, seed, timeout_ms))
    if not isinstance(start, int) or isinstance(start, bool):
        return InductionResult("error", "GUARDRAIL_VIOLATION",
                               "start must be an integer", meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input([claim])
    except GuardrailError as exc:
        return InductionResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))

    k = z3.Int(var)
    try:
        p_k = _parse_claim(claim, var, k)
    except InductionParseError as exc:
        return InductionResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    p_base = z3.substitute(p_k, (k, z3.IntVal(start)))
    p_next = z3.substitute(p_k, (k, k + z3.IntVal(1)))

    # 1) BASE — is ¬P(start) unsatisfiable?
    base_res, base_model, _ = _check([z3.Not(p_base)], timeout_ms, seed)
    if base_res == z3.unknown:
        return InductionResult(
            "unknown", "SOLVER_UNKNOWN",
            f"The solver could not decide the base case P({start}); induction is inconclusive.",
            base_case={"claim": claim, "at": start, "holds": None},
            meta=_meta(t0, seed, timeout_ms))
    if base_res == z3.sat:  # ¬P(start) is satisfiable -> P(start) is FALSE
        return InductionResult(
            "invalid", "BASE_FAILED",
            f"Base case fails: P({start}) is false, so ∀ {var} ≥ {start}. {claim} does not hold "
            f"({var}={start} is a counterexample).",
            base_case={"claim": claim, "at": start, "holds": False},
            meta=_meta(t0, seed, timeout_ms))

    # 2) STEP — is [P(k) ∧ k≥start ∧ ¬P(k+1)] unsatisfiable?
    step_res, step_model, _ = _check([p_k, k >= z3.IntVal(start), z3.Not(p_next)], timeout_ms, seed)
    base_info = {"claim": claim, "at": start, "holds": True}
    if step_res == z3.unknown:
        return InductionResult(
            "unknown", "SOLVER_UNKNOWN",
            "Base case holds, but the solver could not decide the inductive step "
            "(P(k) → P(k+1)) for this claim; induction is inconclusive (an honest wall — "
            "the nonlinear step exceeded the decision procedure).",
            base_case=base_info,
            inductive_step={"claim": f"implies({claim}, {claim}[{var}:={var}+1])", "holds": None},
            meta=_meta(t0, seed, timeout_ms))
    if step_res == z3.sat:  # found k with P(k) but ¬P(k+1) -> step is not valid
        kv = step_model.eval(k, model_completion=True)
        counter = kv.as_long() if z3.is_int_value(kv) else str(kv)
        return InductionResult(
            "unknown", "STEP_FAILED",
            f"Base case holds, but the inductive step fails at {var}={counter}: P({counter}) holds "
            f"while P({counter}+1) does not. This particular induction does not go through, so the "
            f"claim is NEITHER proved nor disproved (it may still be true by another argument).",
            base_case=base_info,
            inductive_step={"claim": f"implies({claim}, {claim}[{var}:={var}+1])",
                            "holds": False, "counterexample": {var: counter}},
            meta=_meta(t0, seed, timeout_ms))

    # BOTH hold -> induction principle applies.
    proof_steps = [
        {"step": 1, "formula": f"{claim}   (at {var} = {start})", "rule": "base case", "refs": []},
        {"step": 2, "formula": f"implies({claim}, {claim}[{var} := {var}+1])   (for k ≥ {start})",
         "rule": "inductive step", "refs": []},
        {"step": 3, "formula": f"∀ {var} ≥ {start}. {claim}",
         "rule": "induction principle", "refs": [1, 2]},
    ]
    return InductionResult(
        "valid", "PROVED_BY_INDUCTION",
        f"Proved by induction: base case P({start}) holds and the inductive step "
        f"P(k) → P(k+1) holds for all k ≥ {start}, hence ∀ {var} ≥ {start}. {claim}.",
        base_case=base_info,
        inductive_step={"claim": f"implies({claim}, {claim}[{var}:={var}+1])", "holds": True},
        proof_steps=proof_steps,
        meta=_meta(t0, seed, timeout_ms))
