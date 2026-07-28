"""
mathhead.router — Yönlendirme katmanı.

Görev: gelen bir görevi DOĞRU çözücü + ilkele yönlendirmek. Karar açık ve kurallı
(rule-based); "model sezgisiyle" değil. Bu, duvar #3'e (non-determinizm) karşı
mimari güvenliğin parçasıdır.

v1: mantık (Z3) — entailment / consistency / find_model.
v2: hesap (SymPy) — simplify / solve / differentiate / integrate.
Dış sözleşme (ADR-0004) sabit; yeni yetenekler yalnızca yeni görev adları ekler.
"""
from __future__ import annotations

from typing import Any

from mathhead import compute, frontier
from mathhead.compute import ComputeResult
from mathhead.core.inequality import (
    find_real_solution,
    prove_inequality,
    prove_nonnegative,
)
from mathhead.core.logic import (
    MaxSatResult,
    ModelSet,
    OptimizeResult,
    ReasoningResult,
    check_consistency,
    check_entailment,
    classify,
    enumerate_models,
    equivalent,
    find_model,
    max_satisfy,
    optimize,
)
from mathhead.core.proof import ProofResult, prove_entailment

__all__ = ["route"]


def _opts(payload: dict[str, Any]) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    for key in ("timeout_ms", "seed"):
        if key in payload and payload[key] is not None:
            opts[key] = payload[key]
    return opts


def route(task: str, payload: dict[str, Any]) -> (
    ReasoningResult | ComputeResult | ProofResult | ModelSet | OptimizeResult | MaxSatResult
):
    """Bir görevi uygun çözücü + ilkele yönlendirir.

    Mantık görevleri (Z3): entailment, consistency, find_model.
    Hesap görevleri (SymPy): simplify, solve, differentiate, integrate.
    """
    # --- Mantık çekirdeği (Z3) ---
    if task == "entailment":
        return check_entailment(payload["premises"], payload["conclusion"], **_opts(payload))
    if task == "consistency":
        return check_consistency(payload["statements"], **_opts(payload))
    if task == "find_model":
        return find_model(payload["statements"], **_opts(payload))
    if task == "prove":
        return prove_entailment(payload["premises"], payload["conclusion"], **_opts(payload))
    if task == "equivalent":
        return equivalent(payload["a"], payload["b"], **_opts(payload))
    if task == "classify":
        return classify(payload["formula"], **_opts(payload))
    if task == "enumerate":
        return enumerate_models(payload["statements"], limit=payload.get("limit", 10), **_opts(payload))
    if task == "optimize":
        return optimize(payload["constraints"], payload["objective"],
                        payload.get("sense", "max"), **_opts(payload))
    if task == "maxsat":
        return max_satisfy(payload["hard"], payload["soft"], payload.get("weights"), **_opts(payload))
    if task == "prove_inequality":
        return prove_inequality(payload["goal"], payload.get("assumptions"), **_opts(payload))
    if task == "prove_nonnegative":
        return prove_nonnegative(payload["expression"], payload.get("assumptions"), **_opts(payload))
    if task == "find_real_solution":
        return find_real_solution(payload["constraints"], **_opts(payload))

    # --- Hesap katmanı (SymPy) ---
    if task == "simplify":
        return compute.simplify(payload["expression"])
    if task == "solve":
        return compute.solve(payload["equation"], payload["symbol"])
    if task == "differentiate":
        return compute.differentiate(payload["expression"], payload["symbol"], payload.get("order", 1))
    if task == "integrate":
        return compute.integrate(payload["expression"], payload["symbol"])
    if task == "limit":
        return compute.limit(payload["expression"], payload["symbol"],
                             payload.get("point", "0"), payload.get("direction", "both"))
    if task == "series":
        return compute.series(payload["expression"], payload["symbol"],
                              payload.get("point", "0"), payload.get("order", 6))
    if task == "solve_system":
        return compute.solve_system(payload["equations"], payload["symbols"])
    if task == "determinant":
        return compute.determinant(payload["matrix"])
    if task == "matrix_inverse":
        return compute.matrix_inverse(payload["matrix"])
    if task == "eigenvalues":
        return compute.eigenvalues(payload["matrix"])
    if task == "matrix_rank":
        return compute.matrix_rank(payload["matrix"])
    if task == "matrix_multiply":
        return compute.matrix_multiply(payload["a"], payload["b"])
    if task == "matrix_solve":
        return compute.matrix_solve(payload["matrix"], payload["rhs"])
    if task == "eigenvectors":
        return compute.eigenvectors(payload["matrix"])
    if task == "rref":
        return compute.rref(payload["matrix"])
    if task == "nullspace":
        return compute.nullspace(payload["matrix"])
    if task == "lu_decomposition":
        return compute.lu_decomposition(payload["matrix"])

    # --- Sayı teorisi (number theory) ---
    if task == "gcd":
        return compute.gcd(payload["a"], payload["b"])
    if task == "lcm":
        return compute.lcm(payload["a"], payload["b"])
    if task == "is_prime":
        return compute.is_prime(payload["n"])
    if task == "factorize":
        return compute.factorize(payload["n"])
    if task == "modular_inverse":
        return compute.modular_inverse(payload["a"], payload["m"])
    if task == "chinese_remainder":
        return compute.chinese_remainder(payload["moduli"], payload["residues"])
    if task == "linear_diophantine":
        return compute.linear_diophantine(payload["a"], payload["b"], payload["c"])

    # --- Kombinatorik & ayrık ---
    if task == "permutations":
        return compute.permutations(payload["n"], payload["k"])
    if task == "combinations":
        return compute.combinations(payload["n"], payload["k"])
    if task == "factorial":
        return compute.factorial(payload["n"])
    if task == "partition_count":
        return compute.partition_count(payload["n"])
    if task == "solve_recurrence":
        return compute.solve_recurrence(
            payload["recurrence"], payload.get("func", "y"),
            payload.get("var", "n"), payload.get("initial"),
        )

    # --- Çok değişkenli analiz (multivariable) ---
    if task == "gradient":
        return compute.gradient(payload["expression"], payload["variables"])
    if task == "jacobian":
        return compute.jacobian(payload["expressions"], payload["variables"])
    if task == "hessian":
        return compute.hessian(payload["expression"], payload["variables"])
    if task == "definite_integral":
        return compute.definite_integral(payload["expression"], payload["symbol"],
                                         payload["lower"], payload["upper"])
    if task == "summation":
        return compute.summation(payload["expression"], payload["index"],
                                 payload["lower"], payload["upper"])
    if task == "product":
        return compute.product(payload["expression"], payload["index"],
                               payload["lower"], payload["upper"])
    if task == "solve_ode":
        return compute.solve_ode(payload["equation"], payload.get("func", "y"),
                                 payload.get("var", "x"))

    # --- Olasılık & istatistik ---
    if task == "mean":
        return compute.mean(payload["data"])
    if task == "variance":
        return compute.variance(payload["data"], payload.get("sample", False))
    if task == "standard_deviation":
        return compute.standard_deviation(payload["data"], payload.get("sample", False))
    if task == "median":
        return compute.median(payload["data"])
    if task == "distribution":
        return compute.distribution(payload["name"], payload["params"], payload.get("at"))

    # --- Frontier / Track B (programatik indirgeme -> Z3) ---
    if task == "pythagorean_coloring":
        return frontier.boolean_pythagorean_coloring(payload["n"], **_opts(payload))
    if task == "pigeonhole":
        return frontier.pigeonhole(payload["n"], **_opts(payload))
    if task == "van_der_waerden":
        return frontier.van_der_waerden_coloring(
            payload["n"], payload["k"], payload.get("colors", 2), **_opts(payload)
        )
    if task == "schur_number":
        return frontier.schur_number_coloring(payload["n"], payload["colors"], **_opts(payload))
    if task == "graph_coloring":
        return frontier.graph_coloring(payload["edges"], payload["colors"],
                                       payload.get("n"), **_opts(payload))
    if task == "subset_sum":
        return frontier.subset_sum(payload["numbers"], payload["target"], **_opts(payload))

    raise ValueError(f"bilinmeyen görev: {task!r}")
