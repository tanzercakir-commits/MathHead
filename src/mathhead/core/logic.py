"""
mathhead.core.logic
====================

The HEART of the engine: deterministic reasoning primitives built on an SMT
solver (Z3).

Why Z3? -> DECISIONS.md ADR-0002. The world standard for FOL + built-in theories
(linear integer arithmetic, equality...); deterministic and battle-proven.

Return Contract (frozen early — ADR-0004):
    valid / invalid  -> entailment question
    sat   / unsat    -> consistency question
    unknown          -> solver could not decide (an HONEST answer to undecidability)
    error            -> input/guardrail/parse error
    "unknown" and "error" are first-class outputs; NEVER hidden.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import z3

from mathhead.core.translate import ParseError, translate_all, translate_objective
from mathhead.guardrails import GuardrailError, solver_config, validate_input

DEFAULT_TIMEOUT_MS: int = 5_000
DEFAULT_SEED: int = 42


@dataclass
class ReasoningResult:
    """Shared machine- and human-readable output of all reasoning primitives."""

    status: str                              # valid|invalid|sat|unsat|unknown|error
    reason_code: str                         # ENTAILED, COUNTEREXAMPLE_FOUND, ...
    explanation: str                         # human-readable explanation
    witness: dict[str, Any] | None = None    # model (sat) / counterexample (invalid) / unsat core
    meta: dict[str, Any] = field(default_factory=dict)

    def is_conclusive(self) -> bool:
        """Is the result conclusive? (unknown/error -> False)."""
        return self.status not in ("unknown", "error")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _meta(t0: float, seed: int, timeout_ms: int) -> dict[str, Any]:
    return {
        "engine": "z3",
        "z3_version": z3.get_version_string(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3),
        "seed": seed,
        "timeout_ms": timeout_ms,
    }


def _error(code: str, msg: str, t0: float, seed: int, timeout_ms: int) -> ReasoningResult:
    return ReasoningResult("error", code, msg, None, _meta(t0, seed, timeout_ms))


def _py_value(val: Any) -> Any:
    """Reduces a Z3 value to a plain Python value (JSON-friendly)."""
    if z3.is_true(val):
        return True
    if z3.is_false(val):
        return False
    if z3.is_int_value(val):
        return val.as_long()
    if z3.is_rational_value(val):
        return float(val.as_fraction())   # Real: convert the fractional value to a decimal
    return str(val)                        # algebraic/irrational: exact text representation


def _default_for(const: Any) -> Any:
    """CANONICAL default for an unconstrained (don't-care) variable -> determinism."""
    sort = const.sort()
    if sort == z3.BoolSort():
        return False
    if sort == z3.IntSort():
        return 0
    if sort == z3.RealSort():
        return 0.0
    return None


def _witness(model: z3.ModelRef, symbols: dict[str, Any]) -> dict[str, Any]:
    """Converts the model into a readable, DETERMINISTIC dictionary.

    For an unconstrained (don't-care) variable we assign the canonical default
    (False / 0) rather than Z3's volatile choice — so that "same input -> same
    witness" genuinely holds (verified by property test; see ADR-0019). Internal
    tracking literals (__track_) are excluded.
    """
    out: dict[str, Any] = {}
    for name, const in symbols.items():
        if name.startswith("__track_"):
            continue
        val = model.eval(const, model_completion=False)
        if z3.is_true(val) or z3.is_false(val) or z3.is_int_value(val) or z3.is_rational_value(val):
            out[name] = _py_value(val)
        else:  # unassigned (don't-care) -> canonical default
            out[name] = _default_for(const)
    return dict(sorted(out.items()))


def _unknown(solver: z3.Solver, t0: float, seed: int, timeout_ms: int) -> ReasoningResult:
    reason = solver.reason_unknown()
    code = "SOLVER_TIMEOUT" if reason == "timeout" else "SOLVER_UNKNOWN"
    return ReasoningResult(
        "unknown", code, f"Solver could not decide ({reason}).",
        None, _meta(t0, seed, timeout_ms),
    )


def _prepare(statements: list[str], t0: float, seed: int, timeout_ms: int):
    """Shared pre-step: guardrail + translation. Returns (result, z3_list, symbols);
    if result is set (error), the caller returns early."""
    try:
        validate_input(statements)
    except GuardrailError as exc:
        return _error("GUARDRAIL_VIOLATION", str(exc), t0, seed, timeout_ms), None, None
    try:
        z3_list, symbols = translate_all(statements)
    except ParseError as exc:
        return _error("PARSE_ERROR", str(exc), t0, seed, timeout_ms), None, None
    return None, z3_list, symbols


# --------------------------------------------------------------------------- #
# Primitives
# --------------------------------------------------------------------------- #
def check_entailment(
    premises: list[str],
    conclusion: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """Does `premises ⊨ conclusion` hold? (do the premises logically entail the conclusion).

    Method: if (⋀ premises) ∧ ¬conclusion is UNSAT, entailment HOLDS.
      * UNSAT -> valid
      * SAT   -> invalid (witness = counterexample)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    if not isinstance(premises, list) or not isinstance(conclusion, str):
        return _error("GUARDRAIL_VIOLATION", "premises must be a list, conclusion must be a string", t0, seed, timeout_ms)

    err, z3_list, symbols = _prepare([*premises, conclusion], t0, seed, timeout_ms)
    if err is not None:
        return err
    *prem_z, concl_z = z3_list

    solver = solver_config(timeout_ms, seed)
    for p in prem_z:
        solver.add(p)
    solver.add(z3.Not(concl_z))

    result = solver.check()
    if result == z3.unsat:
        return ReasoningResult(
            "valid", "ENTAILED",
            "The conclusion follows logically from the premises (premises ∧ ¬conclusion is unsatisfiable).",
            None, _meta(t0, seed, timeout_ms),
        )
    if result == z3.sat:
        return ReasoningResult(
            "invalid", "COUNTEREXAMPLE_FOUND",
            "Found a counterexample that satisfies the premises but refutes the conclusion.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)


def check_consistency(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """Is the set of statements CONSISTENT (can they all be true at once)?

    Method: is ⋀ statements SAT?
      * SAT   -> sat   (witness = sample assignment/model)
      * UNSAT -> unsat (witness = conflicting subset / unsat core)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return err

    solver = solver_config(timeout_ms, seed)
    # For the unsat core, add each statement with a tracking literal (assert_and_track).
    trackers: dict[str, int] = {}
    for i, expr in enumerate(z3_list):
        lit_name = f"__track_{i}"
        trackers[lit_name] = i
        solver.assert_and_track(expr, z3.Bool(lit_name))

    result = solver.check()
    if result == z3.sat:
        return ReasoningResult(
            "sat", "CONSISTENT",
            "The statements are consistent; there is an assignment satisfying all of them at once.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    if result == z3.unsat:
        core_idx = sorted(trackers[str(c)] for c in solver.unsat_core())
        return ReasoningResult(
            "unsat", "CONTRADICTION",
            "The statements are contradictory; the flagged subset cannot be satisfied simultaneously.",
            {
                "unsat_core_indices": core_idx,
                "unsat_core": [statements[i] for i in core_idx],
            },
            _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)


def find_model(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """Finds a CONCRETE model (variable assignment) satisfying the statements.

      * SAT   -> sat (witness = model)
      * UNSAT -> unsat (no model)
      * unknown/timeout -> unknown
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return err

    solver = solver_config(timeout_ms, seed)
    for expr in z3_list:
        solver.add(expr)

    result = solver.check()
    if result == z3.sat:
        return ReasoningResult(
            "sat", "MODEL_FOUND",
            "Found a concrete model satisfying the statements.",
            _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms),
        )
    if result == z3.unsat:
        return ReasoningResult(
            "unsat", "NO_MODEL",
            "No model satisfies the statements (the set is contradictory).",
            None, _meta(t0, seed, timeout_ms),
        )
    return _unknown(solver, t0, seed, timeout_ms)


@dataclass
class ModelSet:
    """Output of `enumerate_models`: the set of (distinct) models satisfying a formula."""

    status: str                              # sat|unsat|unknown|error
    reason_code: str
    explanation: str
    models: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    exhaustive: bool = False                 # True: ALL models found (unsat was reached)
    meta: dict[str, Any] = field(default_factory=dict)


def enumerate_models(
    statements: list[str],
    *,
    limit: int = 10,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> ModelSet:
    """Enumerates DISTINCT models (at most `limit` of them) satisfying the statements.

    Method: solve → record the model → **block** that model (force a different
    assignment) → repeat. If `unsat` is reached, the set is exhausted
    (`exhaustive=True`, all models found); if `limit` is reached, there may be more
    (in infinite domains — e.g. unbounded Int/Real — this is expected and reported
    honestly).
    """
    t0 = time.perf_counter()
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        return ModelSet("error", "GUARDRAIL_VIOLATION", "limit must be an integer in 1..1000",
                        meta=_meta(t0, seed, timeout_ms))

    err, z3_list, symbols = _prepare(statements, t0, seed, timeout_ms)
    if err is not None:
        return ModelSet(err.status, err.reason_code, err.explanation, meta=err.meta)

    solver = solver_config(timeout_ms, seed)
    for expr in z3_list:
        solver.add(expr)
    free = [const for name, const in symbols.items() if not name.startswith("__track_")]

    models: list[dict[str, Any]] = []
    while len(models) < limit:
        result = solver.check()
        if result == z3.unsat:
            if models:
                return ModelSet("sat", "ALL_MODELS_FOUND",
                                f"Found {len(models)} models — all of them (no more exist).",
                                models, len(models), True, _meta(t0, seed, timeout_ms))
            return ModelSet("unsat", "CONTRADICTION",
                            "The statements are contradictory; there are no models.",
                            [], 0, True, _meta(t0, seed, timeout_ms))
        if result != z3.sat:
            return ModelSet("unknown", "SOLVER_UNKNOWN",
                            f"Solver could not decide ({solver.reason_unknown()}); "
                            f"{len(models)} models had been found.",
                            models, len(models), False, _meta(t0, seed, timeout_ms))
        model = solver.model()
        models.append(_witness(model, symbols))
        if free:
            solver.add(z3.Or(*[c != model.eval(c, model_completion=True) for c in free]))
        else:  # no free variables (closed formula) -> at most one model
            solver.add(z3.BoolVal(False))

    return ModelSet("sat", "MODELS_FOUND",
                    f"Found {limit} models (limit reached; there may be more).",
                    models, limit, False, _meta(t0, seed, timeout_ms))


@dataclass
class OptimizeResult:
    """Output of `optimize`: a solution optimizing an objective under constraints."""

    status: str                              # optimal|unbounded|unsat|unknown|error
    reason_code: str
    explanation: str
    objective_value: Any = None              # optimal objective value
    sense: str = ""                          # "max" | "min"
    witness: dict[str, Any] | None = None    # assignment achieving the optimum
    meta: dict[str, Any] = field(default_factory=dict)


def _opt_value(val: Any) -> Any:
    try:
        if z3.is_int_value(val):
            return val.as_long()
        if z3.is_rational_value(val):
            return float(val.as_fraction())
    except Exception:  # noqa: BLE001
        pass
    return None


def optimize(
    constraints: list[str],
    objective: str,
    sense: str = "max",
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> OptimizeResult:
    """Find a solution satisfying the constraints that maximizes/minimizes the
    numeric `objective`.

    sense: "max"/"maximize" or "min"/"minimize". Z3 Optimize (optimization modulo
    theories) core. `unbounded`, `unsat` (no feasible solution), and `unknown`
    states are reported honestly.
    """
    t0 = time.perf_counter()
    s = sense.lower()
    if s in ("max", "maximize"):
        is_max = True
    elif s in ("min", "minimize"):
        is_max = False
    else:
        return OptimizeResult("error", "GUARDRAIL_VIOLATION",
                              "sense must be 'max' or 'min'", meta=_meta(t0, seed, timeout_ms))
    if not isinstance(objective, str) or not objective.strip():
        return OptimizeResult("error", "GUARDRAIL_VIOLATION",
                              "objective cannot be empty", meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input(constraints)
    except GuardrailError as exc:
        return OptimizeResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))
    try:
        c_z3, o_z3, symbols = translate_objective(constraints, objective)
    except ParseError as exc:
        return OptimizeResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    opt = z3.Optimize()
    try:
        opt.set("timeout", int(timeout_ms))
    except Exception:  # noqa: BLE001
        pass
    for c in c_z3:
        opt.add(c)
    handle = opt.maximize(o_z3) if is_max else opt.minimize(o_z3)
    sense_str = "max" if is_max else "min"

    result = opt.check()
    if result == z3.unsat:
        return OptimizeResult("unsat", "INFEASIBLE",
                              "The constraints cannot be satisfied together; no feasible solution.",
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))
    if result != z3.sat:
        return OptimizeResult("unknown", "SOLVER_UNKNOWN",
                              f"Solver could not decide ({opt.reason_unknown()}).",
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))

    value = handle.value()
    py = _opt_value(value)
    if py is None:
        text = str(value)
        if "oo" in text or "*oo" in text:
            return OptimizeResult("unbounded", "UNBOUNDED",
                                  f"The objective is unbounded {'above' if is_max else 'below'} (no optimum).",
                                  sense=sense_str, meta=_meta(t0, seed, timeout_ms))
        return OptimizeResult("optimal", "OPEN_BOUND",
                              f"Best value {'supremum' if is_max else 'infimum'} = {text} "
                              f"(open bound; not exactly attainable).",
                              objective_value=text, witness=_witness(opt.model(), symbols),
                              sense=sense_str, meta=_meta(t0, seed, timeout_ms))
    return OptimizeResult("optimal", "OPTIMAL",
                          f"Optimal ({sense_str}) '{objective}' = {py}.",
                          objective_value=py, witness=_witness(opt.model(), symbols),
                          sense=sense_str, meta=_meta(t0, seed, timeout_ms))


@dataclass
class MaxSatResult:
    """Output of `max_satisfy`: a solution satisfying the hard constraints while
    satisfying the MOST (weighted) soft constraints (MaxSAT)."""

    status: str                              # optimal|unsat|unknown|error
    reason_code: str
    explanation: str
    satisfied: list[int] = field(default_factory=list)     # indices of satisfied soft constraints
    unsatisfied: list[int] = field(default_factory=list)   # indices of unsatisfied soft constraints
    satisfied_weight: Any = 0
    total_weight: Any = 0
    witness: dict[str, Any] | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def max_satisfy(
    hard: list[str],
    soft: list[str],
    weights: list[int] | None = None,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    seed: int = DEFAULT_SEED,
) -> MaxSatResult:
    """Satisfy the mandatory (`hard`) constraints while satisfying the MOST
    (weighted) `soft` constraints.

    For over-constrained/conflicting requests, finds "the best, not all" (MaxSAT).
    If `weights` is not given, each soft constraint has weight 1. If `hard` cannot
    be satisfied, `unsat`.
    """
    t0 = time.perf_counter()
    if not isinstance(hard, list) or not isinstance(soft, list) or len(soft) == 0:
        return MaxSatResult("error", "GUARDRAIL_VIOLATION",
                            "hard must be a list, soft must be a list with at least one item",
                            meta=_meta(t0, seed, timeout_ms))
    if weights is None:
        weights = [1] * len(soft)
    elif (not isinstance(weights, list) or len(weights) != len(soft)
          or not all(isinstance(w, int) and w > 0 for w in weights)):
        return MaxSatResult("error", "GUARDRAIL_VIOLATION",
                            "weights must be positive integers of the same length as soft",
                            meta=_meta(t0, seed, timeout_ms))
    try:
        validate_input([*hard, *soft])
    except GuardrailError as exc:
        return MaxSatResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0, seed, timeout_ms))
    try:
        z3_list, symbols = translate_all([*hard, *soft])
    except ParseError as exc:
        return MaxSatResult("error", "PARSE_ERROR", str(exc), meta=_meta(t0, seed, timeout_ms))

    hard_z, soft_z = z3_list[:len(hard)], z3_list[len(hard):]
    opt = z3.Optimize()
    try:
        opt.set("timeout", int(timeout_ms))
    except Exception:  # noqa: BLE001
        pass
    for h in hard_z:
        opt.add(h)
    for expr, weight in zip(soft_z, weights):
        opt.add_soft(expr, weight)

    result = opt.check()
    if result == z3.unsat:
        return MaxSatResult("unsat", "HARD_INFEASIBLE",
                            "The mandatory (hard) constraints cannot be satisfied together; no solution.",
                            total_weight=sum(weights), meta=_meta(t0, seed, timeout_ms))
    if result != z3.sat:
        return MaxSatResult("unknown", "SOLVER_UNKNOWN",
                            f"Solver could not decide ({opt.reason_unknown()}).",
                            total_weight=sum(weights), meta=_meta(t0, seed, timeout_ms))

    model = opt.model()
    satisfied = [i for i, expr in enumerate(soft_z)
                 if z3.is_true(model.eval(expr, model_completion=True))]
    sat_set = set(satisfied)
    unsatisfied = [i for i in range(len(soft)) if i not in sat_set]
    sat_w = sum(weights[i] for i in satisfied)
    total_w = sum(weights)
    return MaxSatResult(
        "optimal", "OPTIMAL",
        f"{len(satisfied)}/{len(soft)} soft constraints satisfied (weight {sat_w}/{total_w}).",
        satisfied, unsatisfied, sat_w, total_w, _witness(model, symbols),
        _meta(t0, seed, timeout_ms),
    )


def equivalent(
    a: str, b: str, *, timeout_ms: int = DEFAULT_TIMEOUT_MS, seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """Are the two expressions logically EQUIVALENT? (same truth value in every model).

    Method: equivalent if `a XOR b` is unsatisfiable (UNSAT). If SAT, returns an
    assignment (witness) where they differ.
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare([a, b], t0, seed, timeout_ms)
    if err is not None:
        return err
    za, zb = z3_list
    solver = solver_config(timeout_ms, seed)
    solver.add(z3.Xor(za, zb))
    result = solver.check()
    if result == z3.unsat:
        return ReasoningResult("equivalent", "EQUIVALENT",
                               "The two expressions are logically equivalent (same truth value under every assignment).",
                               None, _meta(t0, seed, timeout_ms))
    if result == z3.sat:
        return ReasoningResult("not_equivalent", "NOT_EQUIVALENT",
                               "Not equivalent; there is an assignment where the two take different truth values.",
                               _witness(solver.model(), symbols), _meta(t0, seed, timeout_ms))
    return _unknown(solver, t0, seed, timeout_ms)


def classify(
    formula: str, *, timeout_ms: int = DEFAULT_TIMEOUT_MS, seed: int = DEFAULT_SEED,
) -> ReasoningResult:
    """Classify a formula: **tautology** (always true), **contradiction** (always
    false), or **contingent** (sometimes true, sometimes false).

    If contingent, witness: one assignment that makes it true and one that makes it
    false.
    """
    t0 = time.perf_counter()
    err, z3_list, symbols = _prepare([formula], t0, seed, timeout_ms)
    if err is not None:
        return err
    z = z3_list[0]
    sat_solver = solver_config(timeout_ms, seed)
    sat_solver.add(z)
    r_sat = sat_solver.check()                 # is there a true-making assignment?
    false_solver = solver_config(timeout_ms, seed)
    false_solver.add(z3.Not(z))
    r_false = false_solver.check()             # is there a false-making assignment?

    if r_sat == z3.unknown or r_false == z3.unknown:
        return ReasoningResult("unknown", "SOLVER_UNKNOWN",
                               "Solver could not decide.", None, _meta(t0, seed, timeout_ms))
    if r_sat == z3.unsat:
        return ReasoningResult("contradiction", "CONTRADICTION",
                               "Contradiction: the expression is not true under any assignment (always false).",
                               None, _meta(t0, seed, timeout_ms))
    if r_false == z3.unsat:
        return ReasoningResult("tautology", "TAUTOLOGY",
                               "Tautology: the expression is true under every assignment (always true).",
                               None, _meta(t0, seed, timeout_ms))
    witness = {
        "true_witness": _witness(sat_solver.model(), symbols),
        "false_witness": _witness(false_solver.model(), symbols),
    }
    return ReasoningResult("contingent", "CONTINGENT",
                           "Contingent: true under some assignments, false under others.",
                           witness, _meta(t0, seed, timeout_ms))
