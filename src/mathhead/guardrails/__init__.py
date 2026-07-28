"""
mathhead.guardrails — The fence (guardrails).

The code embodiment of the user's working principle "Architectural safety
measures: must not step outside the fence." The engine cannot go BEYOND the
limits set here.

Three kinds of fence:
    1) Input validation -> validate_input(): count/length/depth limits and
       syntax checks. (wall #2: block over-assumption, reject the ambiguous.)
    2) Resource limit   -> solver_config(): timeout. The solver cannot run
       forever (a defense against undecidability).
    3) Determinism      -> solver_config(): a fixed seed, so that
       "same input -> same output". (wall #3: suppress non-determinism.)
"""
from __future__ import annotations

import ast

MAX_STATEMENTS: int = 256          # max number of statements per request
MAX_EXPRESSION_CHARS: int = 4_000  # single-expression length limit
MAX_AST_DEPTH: int = 64            # nesting depth limit


class GuardrailError(ValueError):
    """A fence was violated. The request is rejected; the engine does not enter."""


def _depth(node: ast.AST, level: int = 0) -> int:
    children = list(ast.iter_child_nodes(node))
    if not children:
        return level
    return max(_depth(c, level + 1) for c in children)


def validate_input(statements: list[str]) -> None:
    """Validates input against the fences; raises `GuardrailError` on violation.

    Never silently truncates/fixes — it rejects cleanly (honesty + predictability).
    """
    if not isinstance(statements, list):
        raise GuardrailError("statements must be a list")
    if len(statements) == 0:
        raise GuardrailError("at least one statement is required")
    if len(statements) > MAX_STATEMENTS:
        raise GuardrailError(
            f"at most {MAX_STATEMENTS} statements are processed (got: {len(statements)})"
        )
    for i, s in enumerate(statements):
        if not isinstance(s, str) or not s.strip():
            raise GuardrailError(f"[{i}] empty or invalid statement")
        if len(s) > MAX_EXPRESSION_CHARS:
            raise GuardrailError(
                f"[{i}] statement too long (>{MAX_EXPRESSION_CHARS} characters)"
            )
        try:
            tree = ast.parse(s, mode="eval")
        except SyntaxError as exc:
            raise GuardrailError(f"[{i}] syntax error: {exc.msg}") from exc
        if _depth(tree) > MAX_AST_DEPTH:
            raise GuardrailError(f"[{i}] expression too deep (>{MAX_AST_DEPTH} levels)")


def solver_config(timeout_ms: int, seed: int = 42):
    """Produces a deterministic, time-limited `z3.Solver`.

    Fixed seed -> reproducibility; timeout -> worst-case bound. So the same
    input yields the same result every time and the engine never hangs.
    """
    import z3

    # Global seeds (key names may change across versions -> try safely).
    for key in ("smt.random_seed", "sat.random_seed"):
        try:
            z3.set_param(key, seed)
        except Exception:  # noqa: BLE001 - determinism setting is best-effort
            pass

    solver = z3.Solver()
    solver.set("timeout", int(timeout_ms))
    try:
        solver.set("random_seed", seed)
    except Exception:  # noqa: BLE001
        pass
    return solver
