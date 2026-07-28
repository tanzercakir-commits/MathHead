"""
mathhead.router — Routing layer.

Job: route an incoming task to the RIGHT solver + primitive. The decision is
explicit and rule-based, not "by model intuition". This is part of the
architectural safety against wall #3 (non-determinism).

v1: logic (Z3) — entailment / consistency / find_model.
v2: computation (SymPy) — simplify / solve / differentiate / integrate.
The external contract (ADR-0004) is fixed; new capabilities only add new task names.
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
from mathhead.certificate import CertificateResult, check_certificate
from mathhead.core.crosscheck import cross_check
from mathhead.core.nl import NLResult, interpret
from mathhead.core.verify import (
    VerifyResult,
    verify_derivation,
    verify_derivative,
    verify_equality,
    verify_integral,
    verify_limit,
    verify_matrix_identity,
    verify_series,
    verify_solution,
    verify_steps,
)

__all__ = ["route"]


def _opts(payload: dict[str, Any]) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    for key in ("timeout_ms", "seed"):
        if key in payload and payload[key] is not None:
            opts[key] = payload[key]
    return opts


def route(task: str, payload: dict[str, Any]) -> (
    ReasoningResult | ComputeResult | ProofResult | ModelSet | OptimizeResult | MaxSatResult
    | VerifyResult | CertificateResult | NLResult
):
    """Routes a task to the appropriate solver + primitive.

    Logic tasks (Z3): entailment, consistency, find_model.
    Computation tasks (SymPy): simplify, solve, differentiate, integrate.
    """
    # --- Logic kernel (Z3) ---
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

    # --- Verification layer (AI reasoning auditor) ---
    if task == "verify_equality":
        return verify_equality(payload["left"], payload["right"])
    if task == "verify_solution":
        return verify_solution(payload["equation"], payload["symbol"], payload["claimed"])
    if task == "verify_steps":
        return verify_steps(payload["steps"])
    if task == "verify_derivation":
        return verify_derivation(payload["steps"], payload["operations"])
    if task == "cross_check":
        return cross_check(payload["left"], payload["right"])
    if task == "verify_derivative":
        return verify_derivative(payload["expression"], payload["symbol"],
                                 payload["claimed"], payload.get("order", 1))
    if task == "verify_integral":
        return verify_integral(payload["expression"], payload["symbol"], payload["claimed"])
    if task == "verify_limit":
        return verify_limit(payload["expression"], payload["symbol"],
                            payload["point"], payload["claimed"])
    if task == "verify_series":
        return verify_series(payload["expression"], payload["symbol"],
                             payload["point"], payload["order"], payload["claimed"])
    if task == "verify_matrix_identity":
        return verify_matrix_identity(payload["left"], payload["right"])
    if task == "check_certificate":
        return check_certificate(payload["certificate"])
    if task == "interpret_natural":
        return interpret(payload["text"])

    # --- Computation layer (SymPy) ---
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

    # --- Number theory ---
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

    # --- Combinatorics & discrete ---
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

    # --- Multivariable calculus ---
    if task == "gradient":
        return compute.gradient(payload["expression"], payload["variables"])
    if task == "jacobian":
        return compute.jacobian(payload["expressions"], payload["variables"])
    if task == "hessian":
        return compute.hessian(payload["expression"], payload["variables"])
    if task == "divergence":
        return compute.divergence(payload["field"], payload["variables"])
    if task == "curl":
        return compute.curl(payload["field"], payload["variables"])
    if task == "laplacian":
        return compute.laplacian(payload["expression"], payload["variables"])
    if task == "directional_derivative":
        return compute.directional_derivative(payload["expression"], payload["variables"],
                                              payload["direction"])
    if task == "line_integral":
        return compute.line_integral(payload["field"], payload["variables"],
                                     payload["parametrization"], payload["param"],
                                     payload["lower"], payload["upper"])
    if task == "laplace_transform":
        return compute.laplace_transform(payload["expression"],
                                         payload.get("t_var", "t"), payload.get("s_var", "s"))
    if task == "inverse_laplace_transform":
        return compute.inverse_laplace_transform(payload["expression"],
                                                 payload.get("s_var", "s"), payload.get("t_var", "t"))
    if task == "fourier_transform":
        return compute.fourier_transform(payload["expression"],
                                         payload.get("x_var", "x"), payload.get("k_var", "k"))
    if task == "inverse_fourier_transform":
        return compute.inverse_fourier_transform(payload["expression"],
                                                 payload.get("k_var", "k"), payload.get("x_var", "x"))
    if task == "z_transform":
        return compute.z_transform(payload["expression"],
                                   payload.get("n_var", "n"), payload.get("z_var", "z"))
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
    if task == "solve_ode_system":
        return compute.solve_ode_system(payload["equations"], payload["functions"],
                                        payload.get("var", "x"))
    if task == "solve_ode_ivp":
        return compute.solve_ode_ivp(payload["equation"], payload["conditions"],
                                     payload.get("func", "y"), payload.get("var", "x"))
    if task == "classify_ode":
        return compute.classify_ode(payload["equation"], payload.get("func", "y"),
                                    payload.get("var", "x"))
    if task == "solve_pde":
        return compute.solve_pde(payload["equation"], payload.get("func", "u"),
                                 payload["variables"])
    if task == "residue":
        return compute.residue(payload["expression"], payload["symbol"], payload["point"])
    if task == "contour_integral":
        return compute.contour_integral(payload["expression"], payload["symbol"], payload["poles"])
    if task == "laurent_series":
        return compute.laurent_series(payload["expression"], payload["symbol"],
                                      payload.get("point", "0"), payload.get("order", 6))
    if task == "complex_parts":
        return compute.complex_parts(payload["expression"])

    # --- Abstract algebra (permutation groups) ---
    if task == "permutation_order":
        return compute.permutation_order(payload["permutation"])
    if task == "permutation_parity":
        return compute.permutation_parity(payload["permutation"])
    if task == "permutation_compose":
        return compute.permutation_compose(payload["permutations"])
    if task == "group_order":
        return compute.group_order(payload["name"], payload["degree"])
    if task == "generated_group":
        return compute.generated_group(payload["generators"])

    # --- Linear algebra III (decompositions & matrix functions) ---
    if task == "singular_values":
        return compute.singular_values(payload["matrix"])
    if task == "qr_decomposition":
        return compute.qr_decomposition(payload["matrix"])
    if task == "cholesky_decomposition":
        return compute.cholesky_decomposition(payload["matrix"])
    if task == "gram_schmidt":
        return compute.gram_schmidt(payload["vectors"], payload.get("normalize", True))
    if task == "pseudoinverse":
        return compute.pseudoinverse(payload["matrix"])
    if task == "matrix_exponential":
        return compute.matrix_exponential(payload["matrix"])
    if task == "jordan_form":
        return compute.jordan_form(payload["matrix"])
    if task == "characteristic_polynomial":
        return compute.characteristic_polynomial(payload["matrix"], payload.get("symbol", "lambda"))
    if task == "least_squares":
        return compute.least_squares(payload["matrix"], payload["rhs"])

    # --- Graph theory (pure stdlib) ---
    if task == "shortest_path":
        return compute.shortest_path(payload["edges"], payload["source"], payload["target"],
                                     payload.get("directed", False), payload.get("weighted", False))
    if task == "connected_components":
        return compute.connected_components(payload["edges"], payload.get("nodes"),
                                            payload.get("directed", False))
    if task == "minimum_spanning_tree":
        return compute.minimum_spanning_tree(payload["edges"])
    if task == "max_flow":
        return compute.max_flow(payload["edges"], payload["source"], payload["sink"])
    if task == "maximum_matching":
        return compute.maximum_matching(payload["edges"], payload["left"])
    if task == "is_isomorphic":
        return compute.is_isomorphic(payload["edges1"], payload["edges2"],
                                     payload.get("nodes1"), payload.get("nodes2"))

    # --- Number theory II ---
    if task == "euler_totient":
        return compute.euler_totient(payload["n"])
    if task == "mobius":
        return compute.mobius(payload["n"])
    if task == "continued_fraction":
        return compute.continued_fraction(payload["numerator"], payload.get("denominator", 1))
    if task == "continued_fraction_sqrt":
        return compute.continued_fraction_sqrt(payload["n"])
    if task == "quadratic_residue":
        return compute.quadratic_residue(payload["a"], payload["n"])
    if task == "primitive_root":
        return compute.primitive_root(payload["n"])
    if task == "pell_solution":
        return compute.pell_solution(payload["n"])

    # --- Combinatorics II ---
    if task == "catalan_number":
        return compute.catalan_number(payload["n"])
    if task == "bell_number":
        return compute.bell_number(payload["n"])
    if task == "stirling_number":
        return compute.stirling_number(payload["n"], payload["k"], payload.get("kind", "second"))
    if task == "derangements":
        return compute.derangements(payload["n"])
    if task == "generating_function_coefficient":
        return compute.generating_function_coefficient(payload["expression"], payload["symbol"],
                                                       payload["n"])
    if task == "necklace_count":
        return compute.necklace_count(payload["n"], payload["colors"])

    # --- Probability II ---
    if task == "bayes_theorem":
        return compute.bayes_theorem(payload["prior"], payload["likelihood"], payload["false_alarm"])
    if task == "covariance":
        return compute.covariance(payload["x"], payload["y"], payload.get("sample", False))
    if task == "correlation":
        return compute.correlation(payload["x"], payload["y"])
    if task == "markov_stationary":
        return compute.markov_stationary(payload["matrix"])
    if task == "markov_step":
        return compute.markov_step(payload["matrix"], payload["initial"], payload["steps"])
    if task == "joint_marginal":
        return compute.joint_marginal(payload["joint"], payload.get("axis", "row"))

    # --- Inferential statistics ---
    if task == "t_test":
        return compute.t_test(payload["sample1"], payload.get("sample2"), payload.get("mu", 0))
    if task == "z_test":
        return compute.z_test(payload["sample"], payload["mu"], payload["sigma"])
    if task == "chi_square_test":
        return compute.chi_square_test(payload["observed"], payload["expected"])
    if task == "anova_oneway":
        return compute.anova_oneway(payload["groups"])
    if task == "confidence_interval":
        return compute.confidence_interval(payload["data"], payload.get("confidence", 0.95))
    if task == "linear_regression":
        return compute.linear_regression(payload["x"], payload["y"])

    # --- Optimization II (symbolic) ---
    if task == "critical_points":
        return compute.critical_points(payload["expression"], payload["variables"])
    if task == "lagrange_multipliers":
        return compute.lagrange_multipliers(payload["objective"], payload["constraints"],
                                            payload["variables"])
    if task == "check_convexity":
        return compute.check_convexity(payload["expression"], payload["variables"])

    # --- Numerical methods (root-finding, quadrature, interpolation) ---
    if task == "find_root_newton":
        return compute.find_root_newton(payload["expression"], payload["symbol"], payload["x0"],
                                        payload.get("tolerance", 1e-12), payload.get("max_iter", 100))
    if task == "find_root_bisection":
        return compute.find_root_bisection(payload["expression"], payload["symbol"], payload["a"],
                                           payload["b"], payload.get("tolerance", 1e-12),
                                           payload.get("max_iter", 200))
    if task == "find_root_secant":
        return compute.find_root_secant(payload["expression"], payload["symbol"], payload["x0"],
                                        payload["x1"], payload.get("tolerance", 1e-12),
                                        payload.get("max_iter", 100))
    if task == "numerical_integrate":
        return compute.numerical_integrate(payload["expression"], payload["symbol"], payload["lower"],
                                           payload["upper"], payload.get("method", "simpson"),
                                           payload.get("intervals", 100))
    if task == "interpolate":
        return compute.interpolate(payload["points"], payload.get("at"))
    if task == "numerical_eigenvalues":
        return compute.numerical_eigenvalues(payload["matrix"])
    if task == "condition_number":
        return compute.condition_number(payload["matrix"])
    if task == "runge_kutta":
        return compute.runge_kutta(payload["rhs"], payload["x0"], payload["y0"], payload["x_end"],
                                   payload.get("steps", 100), payload.get("func", "y"),
                                   payload.get("var", "x"))

    # --- Probability & statistics ---
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

    # --- Frontier / Track B (programmatic reduction -> Z3) ---
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

    raise ValueError(f"unknown task: {task!r}")
