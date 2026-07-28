"""
mathhead.core.modal — Propositional modal logic (ROADMAP H4, careful scope).

Checks validity of a propositional MODAL formula in a chosen normal system by
BOUNDED Kripke model checking. A modal formula is valid in a frame class iff it
holds at every world of every frame in the class; we search instead for a
COUNTERMODEL — a Kripke frame (with the class's conditions) and a world where the
formula fails — encoded as a pure-Boolean Z3 satisfiability problem over `W` worlds.

    * a countermodel is found  → `invalid` (DEFINITIVE — a concrete Kripke refutation)
    * no countermodel ≤ W worlds → `valid` (`VALID_BOUNDED`) — valid over every frame
                                    of the class WITH UP TO `W` WORLDS.

HONESTY (this is the "careful scope" of a 🔴 frontier feature): a countermodel
refutes validity unconditionally, but a positive result is BOUNDED model checking —
it asserts "no countermodel up to W worlds", not an unconditional proof. All of
K, T, D, B, S4, S5 have the finite-model property, so for the standard axioms a
small `W` already settles it; raise `max_worlds` for more confidence. The bound is
always surfaced in the explanation and `meta`.

Systems (frame conditions on the accessibility relation R):
    K  — none            T  — reflexive          D  — serial
    B  — refl. + sym.    S4 — refl. + trans.     S5 — refl. + trans. + sym.

Grammar: propositional atoms (names), `box(φ)` (□, necessity), `dia(φ)` (◇,
possibility), `and`/`or`/`not`, `implies(a, b)`, `iff(a, b)`.
"""
from __future__ import annotations

import ast
import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.logic import DEFAULT_SEED, DEFAULT_TIMEOUT_MS
from mathhead.guardrails import GuardrailError, solver_config, validate_input

_RESERVED = {"box", "dia", "implies", "iff"}
_MAX_WORLDS = 12  # transitivity is O(W^3); keep the encoding tractable

# frame conditions per normal system
_SYSTEMS: dict[str, set[str]] = {
    "K": set(),
    "T": {"refl"},
    "D": {"serial"},
    "B": {"refl", "sym"},
    "S4": {"refl", "trans"},
    "S5": {"refl", "trans", "sym"},
}


class ModalParseError(ValueError):
    """The modal formula violated the grammar."""


@dataclass
class ModalResult:
    """Output of `check_modal`."""

    status: str                              # valid | invalid | unknown | error
    reason_code: str                         # VALID_BOUNDED | COUNTERMODEL_FOUND | ...
    explanation: str
    system: str = ""
    witness: dict[str, Any] | None = None    # the countermodel (worlds/valuation/R/false world)
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, seed: int, timeout_ms: int, extra: dict | None = None) -> dict[str, Any]:
    m = {
        "engine": "z3-modal",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }
    if extra:
        m.update(extra)
    return m


def _atoms(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id not in _RESERVED:
            found.add(n.id)
    return found


def check_modal(
    formula: str,
    system: str = "K",
    max_worlds: int = 6,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ModalResult:
    """Is the modal `formula` valid in the normal system `system` (bounded to
    `max_worlds` worlds)?

    `box(φ)` = □φ (necessity), `dia(φ)` = ◇φ (possibility). `invalid` → a concrete
    Kripke countermodel (definitive). `valid`/`VALID_BOUNDED` → no countermodel exists
    in any `system`-frame with up to `max_worlds` worlds (bounded model checking —
    honest about the bound). E.g. `implies(box(p), p)` is invalid in K but valid in T.
    """
    t0 = time.perf_counter()
    system = system.upper()
    if system not in _SYSTEMS:
        return ModalResult("error", "GUARDRAIL_VIOLATION",
                           f"system must be one of {sorted(_SYSTEMS)}", system=system,
                           meta=_meta(t0, seed, timeout_ms))
    if not isinstance(max_worlds, int) or not (1 <= max_worlds <= _MAX_WORLDS):
        return ModalResult("error", "GUARDRAIL_VIOLATION",
                           f"max_worlds must be an integer in 1..{_MAX_WORLDS}", system=system,
                           meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input([formula])
    except GuardrailError as exc:
        return ModalResult("error", "GUARDRAIL_VIOLATION", str(exc), system=system,
                           meta=_meta(t0, seed, timeout_ms))
    try:
        node = ast.parse(formula, mode="eval").body
    except SyntaxError as exc:
        return ModalResult("error", "PARSE_ERROR", f"syntax error: {exc.msg}", system=system,
                           meta=_meta(t0, seed, timeout_ms))

    atoms = sorted(_atoms(node))
    W = max_worlds
    val = {(w, a): z3.Bool(f"v_{w}_{a}") for w in range(W) for a in atoms}
    R = {(w, u): z3.Bool(f"R_{w}_{u}") for w in range(W) for u in range(W)}

    def ev(nd: ast.AST, w: int) -> Any:
        if isinstance(nd, ast.Name):
            if nd.id in _RESERVED:
                raise ModalParseError(f"{nd.id!r} is an operator, not an atom")
            return val[(w, nd.id)]
        if isinstance(nd, ast.UnaryOp) and isinstance(nd.op, ast.Not):
            return z3.Not(ev(nd.operand, w))
        if isinstance(nd, ast.BoolOp):
            parts = [ev(v, w) for v in nd.values]
            return z3.And(*parts) if isinstance(nd.op, ast.And) else z3.Or(*parts)
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name):
            fid, args = nd.func.id, nd.args
            if fid == "implies" and len(args) == 2:
                return z3.Implies(ev(args[0], w), ev(args[1], w))
            if fid == "iff" and len(args) == 2:
                return ev(args[0], w) == ev(args[1], w)
            if fid == "box" and len(args) == 1:
                return z3.And(*[z3.Implies(R[(w, u)], ev(args[0], u)) for u in range(W)])
            if fid == "dia" and len(args) == 1:
                return z3.Or(*[z3.And(R[(w, u)], ev(args[0], u)) for u in range(W)])
            raise ModalParseError(f"unsupported operator {fid!r} (use box/dia/implies/iff)")
        raise ModalParseError(f"disallowed node: {type(nd).__name__}")

    try:
        truth = [ev(node, w) for w in range(W)]
    except ModalParseError as exc:
        return ModalResult("error", "PARSE_ERROR", str(exc), system=system,
                           meta=_meta(t0, seed, timeout_ms))

    solver = solver_config(timeout_ms, seed)
    cond = _SYSTEMS[system]
    if "refl" in cond:
        for w in range(W):
            solver.add(R[(w, w)])
    if "sym" in cond:
        for w in range(W):
            for u in range(w + 1, W):
                solver.add(R[(w, u)] == R[(u, w)])
    if "trans" in cond:
        for w in range(W):
            for u in range(W):
                for v in range(W):
                    solver.add(z3.Implies(z3.And(R[(w, u)], R[(u, v)]), R[(w, v)]))
    if "serial" in cond:
        for w in range(W):
            solver.add(z3.Or(*[R[(w, u)] for u in range(W)]))

    solver.add(z3.Or(*[z3.Not(truth[w]) for w in range(W)]))  # a world where φ fails
    extra = {"system": system, "max_worlds": W, "bounded": True, "atoms": atoms}
    res = solver.check()
    if res == z3.sat:
        model = solver.model()
        false_world = next(w for w in range(W)
                           if z3.is_false(model.eval(truth[w], model_completion=True)))
        valuation = {w: {a: bool(z3.is_true(model.eval(val[(w, a)], model_completion=True)))
                         for a in atoms} for w in range(W)}
        edges = [[w, u] for w in range(W) for u in range(W)
                 if z3.is_true(model.eval(R[(w, u)], model_completion=True))]
        witness = {"worlds": list(range(W)), "accessibility": edges,
                   "valuation": valuation, "false_at_world": false_world}
        return ModalResult("invalid", "COUNTERMODEL_FOUND",
                           f"Not valid in {system}: found a Kripke countermodel where the formula "
                           f"fails at world {false_world} (definitive refutation).",
                           system=system, witness=witness, meta=_meta(t0, seed, timeout_ms, extra))
    if res == z3.unsat:
        return ModalResult("valid", "VALID_BOUNDED",
                           f"Valid in {system}: no countermodel exists in any {system}-frame with up "
                           f"to {W} worlds (bounded model checking; raise max_worlds for more "
                           f"confidence).", system=system, meta=_meta(t0, seed, timeout_ms, extra))
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ModalResult("unknown", code, f"The solver could not decide ({reason}).",
                       system=system, meta=_meta(t0, seed, timeout_ms, extra))
