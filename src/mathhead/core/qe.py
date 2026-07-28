"""
mathhead.core.qe — Quantifier elimination (ROADMAP H3, proof depth II).

Given a quantified formula over linear integer/real arithmetic (Presburger),
Z3's `qe` tactic produces an EQUIVALENT quantifier-free formula. That is a genuine
piece of proof depth: it turns `∃`/`∀` statements into an explicit, checkable
condition, and it doubles as a decision procedure for quantified LIA/LRA
(the result collapses to `True` for a valid statement, `False` for an
unsatisfiable one).

Examples (integer-aware):
    ∃x. a ≤ x ∧ x ≤ b            ⟶   a ≤ b
    ∃x. 0 < x ∧ x < 1            ⟶   False        (no integer strictly between)
    ∃y. x = 2·y                  ⟶   x % 2 = 0    (x is even)
    ∀x. (x > 5) → (x > 3)        ⟶   True

Input uses the SAME grammar as the logic kernel (`core/translate.py`):
`forall(x, …)` / `exists(x, …)`, linear `+ - *`, chained comparisons, `and`/`or`/
`not`, `implies`/`iff`. Honesty: nonlinear/undecidable fragments where Z3 cannot
fully eliminate leave a residual quantifier — reported as `QE_INCOMPLETE`
(`unknown`), never silently dropped.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS
from mathhead.core.translate import ParseError, translate_all
from mathhead.guardrails import GuardrailError, validate_input


@dataclass
class QEResult:
    """Output of `eliminate_quantifiers`."""

    status: str                              # ok | unknown | error
    reason_code: str                         # QE_DONE | QE_INCOMPLETE | PARSE_ERROR | ...
    explanation: str
    result: str | None = None                # the quantifier-free equivalent formula
    equivalent_to: str | None = None         # "true" | "false" | None (if it collapsed)
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, seed: int, timeout_ms: int) -> dict[str, Any]:
    return {
        "engine": "z3-qe",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


def _has_quantifier(expr: Any) -> bool:
    """Is there a residual quantifier anywhere in the expression tree?"""
    stack, seen = [expr], set()
    while stack:
        node = stack.pop()
        nid = node.get_id()
        if nid in seen:
            continue
        seen.add(nid)
        if z3.is_quantifier(node):
            return True
        stack.extend(node.children())
    return False


def eliminate_quantifiers(
    formula: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> QEResult:
    """Eliminate quantifiers from `formula`, returning an equivalent quantifier-free
    formula (Z3 `qe` over linear integer/real arithmetic).

    `ok` → `result` is the quantifier-free equivalent; if it collapses to a constant,
    `equivalent_to` is `"true"` (the statement is valid) or `"false"` (unsatisfiable).
    `unknown`/`QE_INCOMPLETE` → Z3 left a residual quantifier (nonlinear/undecidable
    fragment) — reported honestly, never dropped.
    """
    t0 = time.perf_counter()
    try:
        validate_input([formula])
    except GuardrailError as exc:
        return QEResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))
    try:
        z3_list, _ = translate_all([formula])
    except ParseError as exc:
        return QEResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    goal = z3.Goal()
    goal.add(z3_list[0])
    tactic = z3.TryFor(z3.Then(z3.Tactic("qe"), z3.Tactic("simplify")), int(timeout_ms))
    try:
        expr = tactic(goal).as_expr()
    except z3.Z3Exception:
        return QEResult("unknown", "SOLVER_TIMEOUT",
                        "Quantifier elimination did not finish within the time limit.",
                        meta=_meta(t0, seed, timeout_ms))

    if _has_quantifier(expr):
        return QEResult(
            "unknown", "QE_INCOMPLETE",
            "Z3 could not fully eliminate the quantifiers (a nonlinear/undecidable fragment); "
            "a residual quantifier remains — reported honestly rather than dropped.",
            result=str(expr), meta=_meta(t0, seed, timeout_ms))

    if z3.is_true(expr):
        return QEResult("ok", "QE_DONE",
                        "The quantified statement is valid: quantifier elimination reduces it to True.",
                        result="True", equivalent_to="true", meta=_meta(t0, seed, timeout_ms))
    if z3.is_false(expr):
        return QEResult("ok", "QE_DONE",
                        "The quantified statement is unsatisfiable: quantifier elimination reduces it to False.",
                        result="False", equivalent_to="false", meta=_meta(t0, seed, timeout_ms))
    return QEResult("ok", "QE_DONE",
                    "Eliminated the quantifiers; the result is an equivalent quantifier-free formula.",
                    result=str(expr), meta=_meta(t0, seed, timeout_ms))
