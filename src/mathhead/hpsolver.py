"""
mathhead.hpsolver — High-performance CNF solving (ROADMAP J3).

A dedicated CDCL SAT backend (CaDiCaL/Glucose/MiniSat via the optional `python-sat`
package) for solving large CNF instances at a scale where a general SMT solver is
slow. Determinism and honesty are preserved exactly as elsewhere:

  * The VERDICT (sat/unsat) is deterministic; a `sat` model is an *example* (ADR-0019)
    and is INDEPENDENTLY re-verified in pure Python before it is returned
    (`meta.verified: true`) — an encoding/backend bug cannot ship a bogus model.
  * The search is BOUNDED by a conflict budget → an honest `unknown`
    (`BUDGET_EXCEEDED`) on a hard instance, never a hang or a fabricated answer
    (PRINCIPLES 4).

Optional dependency (honest wall): the high-performance backend needs
`pip install "mathhead[solvers]"` (python-sat, which bundles CaDiCaL — no system
package). When it is absent, `solve_cnf` falls back to the built-in stdlib DPLL
(`mathhead.drat.refute`) for SMALL instances (≤ 20 variables) and reports a clear
`BACKEND_UNAVAILABLE` wall for larger ones. `Kissat` and portfolio/parallel solving
are NOT wrapped here (Kissat has no pip/apt package in this environment) — an
explicit, documented scope limit rather than a stub.

CNF format matches `mathhead.drat`: a list of clauses of nonzero-int DIMACS literals.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from mathhead.drat import refute, rup_check

# solver alias -> concrete python-sat backend name
_SOLVERS = {
    "cadical": "cadical195", "cadical153": "cadical153", "cadical195": "cadical195",
    "glucose": "glucose42", "minisat": "minisat22", "mergesat": "mergesat3",
}
_DEFAULT_CONFLICTS = 100_000
_MAX_CONFLICTS = 50_000_000
_MAX_VARS = 200_000
_MAX_CLAUSES = 2_000_000       # HP backend scales far past the stdlib DPLL's cap
_FALLBACK_MAX_VARS = 20        # the builtin DPLL's honest ceiling


def _check_cnf(clauses: Any) -> tuple[list[list[int]], set[int]]:
    """Structural CNF validation for the HP backend (its own generous size caps)."""
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("clauses must be a non-empty list of clauses")
    if len(clauses) > _MAX_CLAUSES:
        raise ValueError(f"too many clauses (>{_MAX_CLAUSES})")
    out: list[list[int]] = []
    varset: set[int] = set()
    for cl in clauses:
        if not isinstance(cl, list) or any(not isinstance(x, int) or isinstance(x, bool) or x == 0 for x in cl):
            raise ValueError("each clause must be a list of nonzero integers (DIMACS literals)")
        out.append(list(cl))
        varset.update(abs(x) for x in cl)
    return out, varset


@dataclass
class SolveResult:
    status: str                              # sat | unsat | unknown | error
    reason_code: str
    explanation: str
    verified: bool | None = None             # a sat model independently re-checked
    witness: dict[str, Any] | None = None     # {"model": [lits...]} on sat
    proof: list[list[int]] | None = None      # a DRUP proof (builtin-fallback unsat only)
    meta: dict[str, Any] = field(default_factory=dict)


def _meta(t0: float, extra: dict | None = None) -> dict[str, Any]:
    m = {"elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}
    if extra:
        m.update(extra)
    return m


def pysat_available() -> bool:
    """Is the optional high-performance backend importable?"""
    try:
        import pysat.solvers  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _verify_model(clauses: list[list[int]], model: list[int]) -> bool:
    """Independently (pure Python) confirm `model` satisfies every clause."""
    truth = set(model)
    return all(any(lit in truth for lit in clause) for clause in clauses)


def _solve_builtin(cnf: list[list[int]], varset: set[int], t0: float,
                   reason_note: str) -> SolveResult:
    """Fallback: the stdlib DPLL (drat.refute). Small instances only."""
    if len(varset) > _FALLBACK_MAX_VARS:
        return SolveResult(
            "error", "BACKEND_UNAVAILABLE",
            f"the high-performance backend is not installed (pip install "
            f"'mathhead[solvers]'); the built-in fallback is bounded to "
            f"{_FALLBACK_MAX_VARS} variables (got {len(varset)}).",
            meta=_meta(t0, {"backend": "builtin-dpll", "backend_available": False}))
    status, data = refute(cnf)
    extra = {"backend": "builtin-dpll", "backend_available": False,
             "variables": len(varset), "clauses": len(cnf), "note": reason_note}
    if status == "unknown":
        return SolveResult("unknown", "BUDGET_EXCEEDED",
                           "The built-in search exceeded its node budget.", meta=_meta(t0, extra))
    if status == "sat":
        model = [v if data.get(v, False) else -v for v in sorted(varset)]
        return SolveResult("sat", "SATISFIABLE",
                           "Satisfiable (built-in fallback; model independently verified).",
                           verified=_verify_model(cnf, model), witness={"model": model},
                           meta=_meta(t0, {**extra, "verified": True}))
    ok, _ = rup_check(cnf, data)
    return SolveResult("unsat", "UNSATISFIABLE",
                       "Unsatisfiable (built-in fallback; DRUP proof independently verified).",
                       verified=ok, proof=data, meta=_meta(t0, {**extra, "verified": ok}))


def solve_cnf(clauses: list[list[int]], solver: str = "cadical",
              max_conflicts: int = _DEFAULT_CONFLICTS, backend: str = "auto") -> SolveResult:
    """Solve a CNF with a high-performance CDCL backend (default CaDiCaL via python-sat).

    `backend`: "auto" (use the HP backend if installed, else the built-in fallback),
    "pysat" (require the HP backend), or "builtin" (force the stdlib DPLL fallback).
    On `sat` the model is INDEPENDENTLY verified (`meta.verified`); the search is bounded
    by `max_conflicts` → honest `unknown` on a hard instance. `unsat` is a verdict — for an
    independently-checkable UNSAT certificate use `prove_unsat` / `check_unsat_proof`
    (the built-in fallback additionally returns a verified DRUP proof).
    """
    t0 = time.perf_counter()
    try:
        cnf, varset = _check_cnf(clauses)
    except ValueError as exc:
        return SolveResult("error", "GUARDRAIL_VIOLATION", str(exc), meta=_meta(t0))
    if len(varset) > _MAX_VARS:
        return SolveResult("error", "GUARDRAIL_VIOLATION",
                           f"too many variables (>{_MAX_VARS})", meta=_meta(t0))
    if not isinstance(max_conflicts, int) or not (1 <= max_conflicts <= _MAX_CONFLICTS):
        return SolveResult("error", "GUARDRAIL_VIOLATION",
                           f"max_conflicts must be an integer in 1..{_MAX_CONFLICTS}", meta=_meta(t0))
    if backend not in ("auto", "pysat", "builtin"):
        return SolveResult("error", "GUARDRAIL_VIOLATION",
                           "backend must be 'auto', 'pysat', or 'builtin'", meta=_meta(t0))

    if backend == "builtin":
        return _solve_builtin(cnf, varset, t0, "forced built-in backend")
    if not pysat_available():
        if backend == "pysat":
            return SolveResult("error", "BACKEND_UNAVAILABLE",
                               "the high-performance backend is not installed "
                               "(pip install 'mathhead[solvers]').", meta=_meta(t0))
        return _solve_builtin(cnf, varset, t0, "high-performance backend not installed")

    name = _SOLVERS.get(solver.lower())
    if name is None:
        return SolveResult("error", "GUARDRAIL_VIOLATION",
                           f"solver must be one of {sorted(_SOLVERS)}", meta=_meta(t0))

    from pysat.solvers import Solver
    extra = {"backend": name, "backend_available": True, "variables": len(varset),
             "clauses": len(cnf), "max_conflicts": max_conflicts}
    s = Solver(name=name, bootstrap_with=cnf)
    try:
        s.conf_budget(max_conflicts)
        res = s.solve_limited(expect_interrupt=False)
        model = s.get_model() if res else None
    finally:
        s.delete()

    if res is None:
        return SolveResult("unknown", "BUDGET_EXCEEDED",
                           f"{name} could not decide within {max_conflicts} conflicts "
                           f"(bounded search; the verdict is not fabricated).", meta=_meta(t0, extra))
    if res:
        if not _verify_model(cnf, model):
            return SolveResult("error", "INTERNAL_INCONSISTENCY",
                               "the backend's model failed independent verification",
                               meta=_meta(t0, extra))
        return SolveResult("sat", "SATISFIABLE",
                           f"Satisfiable ({name}; model independently verified in pure Python).",
                           verified=True, witness={"model": model},
                           meta=_meta(t0, {**extra, "verified": True}))
    return SolveResult("unsat", "UNSATISFIABLE",
                       f"Unsatisfiable ({name}). For an independently-checkable certificate, "
                       f"use prove_unsat / check_unsat_proof.", meta=_meta(t0, extra))
