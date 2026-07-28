"""
mathhead.certainty — Epistemic strength + tool stability (ROADMAP L2).

An external review made a sharp point: a single `valid` hides very different epistemic
strengths — a Z3 decision, a SymPy computation, a *bounded* model check, an independently
re-checked certificate, and a numerical check are NOT the same kind of "true". This module
labels every result with its epistemic strength and every tool with a stability tier, both
carried in `meta` (additive — the frozen contract is untouched; ADR-0032).

`meta.certainty` — how strong is this result?
    formal_proof            an explicit derivation was produced (proof_steps)
    independent_certificate  re-checked independently of the producing engine (stdlib / two engines /
                             a witness verified in pure Python / a DRUP proof)
    solver_verified          a sound decision by Z3/SymPy (no separate certificate)
    bounded_check            true only up to a search bound (e.g. modal VALID_BOUNDED)
    symbolic_result          a CAS computation (correct symbolically; not a verification verdict)
    numerical_check          a numerical result within a tolerance / fixed precision
    unknown                  the engine could not decide (honest)
    error                    the input was rejected
    not_applicable           a non-mathematical tool (NL translation, observability)

`meta.stability` — how frozen is this tool? (the "stable core + experimental extended" model)
    stable        the verification core (the product's thesis) — treated as frozen
    provisional   solid but newer logic/proof surface; small changes possible
    experimental  the broad compute/CAS, frontier reductions, modal — may still change
    internal      observability/admin tools
"""
from __future__ import annotations

from typing import Any

# --- stability tiers ------------------------------------------------------- #
_STABLE = {  # the verification core = the differentiator
    "entailment", "consistency", "find_model", "prove", "equivalent", "classify",
    "verify_equality", "verify_solution", "verify_steps", "verify_derivation",
    "verify_derivative", "verify_integral", "verify_limit", "verify_series",
    "verify_matrix_identity", "cross_check", "check_certificate",
    "prove_unsat", "check_unsat_proof",
}
_PROVISIONAL = {  # solid but newer logic/proof surface
    "enumerate", "optimize", "maxsat", "entail_batch",
    "prove_inequality", "prove_nonnegative", "find_real_solution", "prove_by_induction",
    "check_bitvector", "check_uninterpreted", "check_arrays", "check_strings",
    "eliminate_quantifiers", "check_modal", "solve_cnf",
}
_INTERNAL = {"cache_stats", "engine_metrics", "resource_limits",
             "list_capabilities", "describe_tool", "recommend_tool"}
# everything else (compute CAS, numerical, frontier, NL) = experimental


def stability_of(task: str) -> str:
    if task in _STABLE:
        return "stable"
    if task in _INTERNAL:
        return "internal"
    if task in _PROVISIONAL:
        return "provisional"
    return "experimental"


# --- certainty (epistemic strength) ---------------------------------------- #
_NOT_APPLICABLE = _INTERNAL | {"interpret_natural"}
_NUMERICAL = {
    "find_root_newton", "find_root_bisection", "find_root_secant", "numerical_integrate",
    "interpolate", "numerical_eigenvalues", "condition_number", "runge_kutta",
    "evaluate_precision", "verify_numeric", "cross_check_numeric",
}
_INDEPENDENT = {"check_certificate", "cross_check", "prove_unsat", "check_unsat_proof"}
_FRONTIER = {  # sat witness independently verified (meta.verified) → independent; unsat → solver verdict
    "pythagorean_coloring", "pigeonhole", "van_der_waerden", "schur_number",
    "graph_coloring", "subset_sum", "n_queens", "latin_square", "sudoku_solve",
    "hamiltonian_path", "ramsey_coloring", "tsp_decision",
}
_SOLVER_VERIFIED = {  # sound engine decisions with no separate certificate
    "entailment", "consistency", "find_model", "equivalent", "classify", "enumerate",
    "optimize", "maxsat", "entail_batch", "prove", "prove_by_induction",
    "prove_inequality", "prove_nonnegative", "find_real_solution",
    "check_bitvector", "check_uninterpreted", "check_arrays", "check_strings",
    "eliminate_quantifiers", "verify_equality", "verify_solution", "verify_steps",
    "verify_derivation", "verify_derivative", "verify_integral", "verify_limit",
    "verify_series", "verify_matrix_identity",
}


def certainty_of(task: str, result: Any) -> str:
    """The epistemic strength of `result` from tool `task`."""
    status = getattr(result, "status", "") or ""
    if status == "error":
        return "error"
    if status == "unknown":
        return "unknown"
    if getattr(result, "proof_steps", None):          # an explicit derivation was built
        return "formal_proof"
    if task == "check_modal":
        return "bounded_check" if status == "valid" else "solver_verified"
    if task in _NOT_APPLICABLE:
        return "not_applicable"
    if task in _NUMERICAL:
        return "numerical_check"
    if task in _INDEPENDENT:
        return "independent_certificate"
    meta = getattr(result, "meta", {}) or {}
    if task in _FRONTIER or task == "solve_cnf":
        return "independent_certificate" if meta.get("verified") else "solver_verified"
    if task in _SOLVER_VERIFIED:
        return "solver_verified"
    return "symbolic_result"                          # the compute/CAS default


def annotate(task: str, result: Any) -> Any:
    """Attach `certainty` + `stability` to `result.meta` (additive; contract untouched)."""
    meta = getattr(result, "meta", None)
    if isinstance(meta, dict):
        meta.setdefault("certainty", certainty_of(task, result))
        meta.setdefault("stability", stability_of(task))
    return result
