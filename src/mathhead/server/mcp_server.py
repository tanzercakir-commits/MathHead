"""
mathhead.server.mcp_server
==========================

MathHead's MCP (Model Context Protocol) interface. An AI client (e.g. Claude)
accesses the engine's capabilities ONLY through the tools defined here. This
layer is where the "clear protocol & API definition" principle is applied.

SDK: `mcp` (FastMCP), Python 3.10+. Install: `pip install "mcp[cli]"`.
Run (locally): `mathhead-server`  or  `python -m mathhead.server.mcp_server`

Flow: server -> router -> (guardrails + core/Z3). Tool signatures and return
shape match docs/mcp-api.md exactly (ADR-0004: frozen early).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # guardrail: a clear message if the dependency is missing
    raise SystemExit(
        "MCP SDK not found. Install: pip install 'mcp[cli]'  (see pyproject.toml)"
    ) from exc

from mathhead.router import route

mcp = FastMCP("MathHead")


@mcp.tool()
def entailment(premises: list[str], conclusion: str) -> dict[str, Any]:
    """Do the premises LOGICALLY entail the conclusion? (premises ⊨ conclusion)

    Returns: a ReasoningResult dict. status ∈ {valid, invalid, unknown, error}.
    If invalid, `witness` contains a counterexample.
    For the expression grammar: docs/mcp-api.md.
    """
    return asdict(route("entailment", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def consistency(statements: list[str]) -> dict[str, Any]:
    """Can these statements ALL be true at once? (consistency / satisfiability)

    Returns: status ∈ {sat, unsat, unknown, error}. If sat, `witness` is an
    example assignment (model); if unsat, the conflicting subset (unsat core).
    """
    return asdict(route("consistency", {"statements": statements}))


@mcp.tool()
def model(statements: list[str]) -> dict[str, Any]:
    """Returns a CONCRETE example (variable assignment) satisfying the statements.

    Returns: status ∈ {sat, unsat, unknown, error}. If sat, `witness` = the model.
    """
    return asdict(route("find_model", {"statements": statements}))


@mcp.tool()
def prove(premises: list[str], conclusion: str) -> dict[str, Any]:
    """If the premises entail the conclusion, shows WHY — minimal core + step-by-step derivation.

    valid: `used_premises` (the required premises) + `proof_steps` (built for the
    propositional/predicate/universal part; if it cannot be built, the Z3 verdict is
    kept). invalid: `witness` counterexample.
    """
    return asdict(route("prove", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def equivalent(a: str, b: str) -> dict[str, Any]:
    """Are two expressions logically EQUIVALENT? (same truth value under every assignment)

    status ∈ {equivalent, not_equivalent, unknown, error}. If not_equivalent,
    `witness` = an assignment where the two take different truth values.
    """
    return asdict(route("equivalent", {"a": a, "b": b}))


@mcp.tool()
def classify(formula: str) -> dict[str, Any]:
    """Classify a formula: tautology / contradiction / contingent.

    status ∈ {tautology, contradiction, contingent, unknown, error}. If contingent,
    `witness` = one assignment that makes it true and one that makes it false.
    """
    return asdict(route("classify", {"formula": formula}))


@mcp.tool()
def enumerate_models(statements: list[str], limit: int = 10) -> dict[str, Any]:
    """Enumerates the DISTINCT models satisfying the statements (at most `limit`).

    Returns: `models` (list), `count`, `exhaustive` (True = all models found;
    False = the limit was reached, and there may be more in an infinite space).
    """
    return asdict(route("enumerate", {"statements": statements, "limit": limit}))


@mcp.tool()
def optimize(constraints: list[str], objective: str, sense: str = "max") -> dict[str, Any]:
    """Find the solution that satisfies the constraints and maximizes/minimizes (`sense`) the numeric `objective`.

    Returns: status ∈ {optimal, unbounded, unsat, unknown, error}; if optimal,
    `objective_value` + `witness` (the assignment achieving the optimum). (Z3 Optimize core.)
    """
    return asdict(route("optimize", {"constraints": constraints, "objective": objective, "sense": sense}))


@mcp.tool()
def max_satisfy(hard: list[str], soft: list[str], weights: list[int] | None = None) -> dict[str, Any]:
    """Satisfy the mandatory (`hard`) constraints and AS MANY (weighted) `soft` constraints as possible (MaxSAT).

    For over-constrained/conflicting requests, "not all, but the best". Returns: `status`;
    if optimal, `satisfied`/`unsatisfied` (soft indices), `satisfied_weight` /
    `total_weight`, `witness`. If `hard` cannot be satisfied, `unsat`.
    """
    return asdict(route("maxsat", {"hard": hard, "soft": soft, "weights": weights}))


# ----------------- Inequality proof & nonlinear (Z3 NRA) ------------------ #
@mcp.tool()
def prove_inequality(goal: str, assumptions: list[str] | None = None) -> dict[str, Any]:
    """Does the `goal` inequality hold for ALL real values (under the assumptions)?

    Z3 NRA (nonlinear real): valid → true everywhere; invalid → `witness` counterexample;
    unknown → could not be decided (honest). E.g. `"x**2 + y**2 >= 2*x*y"` → valid.
    """
    return asdict(route("prove_inequality", {"goal": goal, "assumptions": assumptions}))


@mcp.tool()
def prove_nonnegative(expression: str, assumptions: list[str] | None = None) -> dict[str, Any]:
    """Does `expression ≥ 0` hold for every real value (under the assumptions)?

    Sum-of-squares-like non-negativity claims (e.g. `x**2 - 2*x + 1`).
    """
    return asdict(route("prove_nonnegative", {"expression": expression, "assumptions": assumptions}))


@mcp.tool()
def find_real_solution(constraints: list[str]) -> dict[str, Any]:
    """Finds a point in the REALS satisfying a set of nonlinear constraints.

    sat → `witness` a concrete solution; unsat → no real solution; unknown → no decision.
    E.g. `["x**2 + y**2 == 1", "x == y"]` → sat.
    """
    return asdict(route("find_real_solution", {"constraints": constraints}))


# --------------- Verification layer (AI reasoning auditor) ---------------- #
@mcp.tool()
def verify_equality(left: str, right: str) -> dict[str, Any]:
    """Are two expressions EQUIVALENT? (independently checks an AI's "= equals this" claim.)

    valid → equivalent; `EQUAL_ON_COMMON_DOMAIN` → equivalent BUT the domains differ
    (a domain trap, `details.domain_caveat`). invalid → `details.counterexample`.
    unknown → could not be decided. E.g. `(x**2-1)/(x-1)` vs `x+1` → domain warning.
    """
    return asdict(route("verify_equality", {"left": left, "right": right}))


@mcp.tool()
def verify_solution(equation: str, symbol: str, claimed: list[str]) -> dict[str, Any]:
    """Are the `claimed` values solutions of `equation`, and are they COMPLETE? (an AI's solution claim.)

    valid → correct + complete; invalid → `SOLUTION_INCORRECT` (wrong value) or
    `SOLUTION_INCOMPLETE` (`details.missing` the missed solutions); unknown → the values
    hold but completeness could not be verified (e.g. transcendental). E.g. x²=4, {2} → incomplete (-2).
    """
    return asdict(route("verify_solution", {"equation": equation, "symbol": symbol,
                                            "claimed": claimed}))


@mcp.tool()
def verify_steps(steps: list[str]) -> dict[str, Any]:
    """In a chain of expressions, is each step EQUIVALENT to the previous — finds the first bad transition.

    (It "grades" an AI's step-by-step solution.) valid → all equivalent; invalid →
    `details.first_bad_step` (1-based) + counterexample. E.g. `(x+1)**2` → `x**2+1`
    is WRONG (breaks at step 2).
    """
    return asdict(route("verify_steps", {"steps": steps}))


@mcp.tool()
def verify_derivation(steps: list[str], operations: list[dict[str, Any]]) -> dict[str, Any]:
    """Audits a multi-step derivation by REPLAYING each transition's cited operation.

    Deeper than `verify_steps`: it checks the JUSTIFICATION of every step (does the
    rule you cited actually produce this line?), and handles equations, not just
    expressions. `operations` has one entry per transition (len = len(steps)-1), each
    `{"op": add|subtract|multiply|divide|simplify|expand|factor, "value": "<expr>"}`
    (value required for add/subtract/multiply/divide). valid → `DERIVATION_VALID`;
    invalid → `STEP_UNJUSTIFIED` (first unjustified step + what the operation WOULD
    yield). E.g. `2*x+3==7` --subtract 3--> `2*x==5` is unjustified (should be `2*x==4`).
    """
    return asdict(route("verify_derivation", {"steps": steps, "operations": operations}))


@mcp.tool()
def cross_check(left: str, right: str) -> dict[str, Any]:
    """Verifies the `left = right` claim INDEPENDENTLY with Z3 AND SymPy; seeks consensus.

    Agreement between two independent engines is a trust signal that single-engine
    rivals cannot provide. `CONSENSUS_EQUAL`/`CONSENSUS_NOT_EQUAL` → consensus; `ENGINES_DISAGREE`
    → the engines conflict (usually a domain trap — flag for a human);
    `SINGLE_ENGINE` → only one decided (e.g. transcendental → SymPy only).
    """
    return asdict(route("cross_check", {"left": left, "right": right}))


@mcp.tool()
def verify_derivative(expression: str, symbol: str, claimed: str, order: int = 1) -> dict[str, Any]:
    """Is `d^order/d{symbol}^order (expression)` really `claimed`? (an AI derivative claim.)

    valid → correct; invalid → `details.correct` the correct derivative + counterexample; unknown.
    """
    return asdict(route("verify_derivative", {"expression": expression, "symbol": symbol,
                                              "claimed": claimed, "order": order}))


@mcp.tool()
def verify_integral(expression: str, symbol: str, claimed: str) -> dict[str, Any]:
    """Is `∫ expression d{symbol}` really `claimed`? (a +C constant difference is tolerated.)

    Honest method: it checks whether the derivative of `claimed` equals `expression`.
    """
    return asdict(route("verify_integral", {"expression": expression, "symbol": symbol,
                                            "claimed": claimed}))


@mcp.tool()
def verify_limit(expression: str, symbol: str, point: str, claimed: str) -> dict[str, Any]:
    """Is `lim {symbol}→{point} expression` really `claimed`? (`point`/`claimed` may be `oo`.)"""
    return asdict(route("verify_limit", {"expression": expression, "symbol": symbol,
                                         "point": point, "claimed": claimed}))


@mcp.tool()
def verify_series(expression: str, symbol: str, point: str, order: int,
                  claimed: str) -> dict[str, Any]:
    """Is the order-`order` Taylor expansion of `expression` around `{symbol}={point}` really `claimed`?"""
    return asdict(route("verify_series", {"expression": expression, "symbol": symbol,
                                          "point": point, "order": order, "claimed": claimed}))


@mcp.tool()
def verify_matrix_identity(left: list[list[str]], right: list[list[str]]) -> dict[str, Any]:
    """Are two matrices (including symbolic cells) EQUAL? Dimension/first differing cell is reported."""
    return asdict(route("verify_matrix_identity", {"left": left, "right": right}))


@mcp.tool()
def interpret_natural(text: str) -> dict[str, Any]:
    """Turns a natural-language math expression into a FORMAL task (recognize-or-reject).

    An antidote to "wall #2" (over-assumption): it does NOT GUESS. ok+`UNDERSTOOD` →
    `interpretation` {task, payload, **restatement**} — the restatement is an NL
    re-statement of what was understood (CONFIRM BEFORE TRUSTING, then call that task+payload).
    unknown+`AMBIGUOUS` → multiple interpretations; error+`UNRECOGNIZED` → not recognized (write it formally).
    Bilingual (TR+EN): derivative/integral/limit/solving/factoring/primality/GCD/equivalence.
    """
    return asdict(route("interpret_natural", {"text": text}))


@mcp.tool()
def check_certificate(certificate: dict[str, Any]) -> dict[str, Any]:
    """Verifies a result INDEPENDENTLY of the engine that PRODUCED it (Z3/SymPy), using stdlib only.

    "Don't trust us, run the checker." status: `verified` (holds) / `refuted`
    (result is WRONG) / `error`. Kinds: `subset_sum`, `graph_coloring`, `solution`,
    `not_equal`, `inequality_counterexample`, `matrix_product`, `matrix_inverse`,
    `linear_system`, `factorization`, `bezout_gcd`, `modular_inverse`,
    `chinese_remainder`, `expectation`. Arithmetic is exact when possible (Fraction),
    otherwise numeric (float+tolerance, `exact=false`).
    """
    return asdict(route("check_certificate", {"certificate": certificate}))


# -------------------------- Computation (SymPy) --------------------------- #
@mcp.tool()
def simplify(expression: str) -> dict[str, Any]:
    """Simplifies an algebraic expression (e.g. 'sin(x)**2 + cos(x)**2' -> '1')."""
    return asdict(route("simplify", {"expression": expression}))


@mcp.tool()
def solve(equation: str, symbol: str) -> dict[str, Any]:
    """Solves an equation for a variable (e.g. 'x**2 == 4', symbol='x')."""
    return asdict(route("solve", {"equation": equation, "symbol": symbol}))


@mcp.tool()
def differentiate(expression: str, symbol: str, order: int = 1) -> dict[str, Any]:
    """Takes the order-th derivative of the expression with respect to `symbol`."""
    return asdict(route("differentiate", {"expression": expression, "symbol": symbol, "order": order}))


@mcp.tool()
def integrate(expression: str, symbol: str) -> dict[str, Any]:
    """Takes the indefinite integral of the expression w.r.t. `symbol` (+C)."""
    return asdict(route("integrate", {"expression": expression, "symbol": symbol}))


@mcp.tool()
def limit(expression: str, symbol: str, point: str = "0", direction: str = "both") -> dict[str, Any]:
    """Limit of the expression as `symbol` → `point`. direction: both | + | - (one-sided).

    `point` may be infinite ("oo" / "-oo"). E.g. 'sin(x)/x', x→0 = 1; '1/x', x→oo = 0.
    """
    return asdict(route("limit", {"expression": expression, "symbol": symbol,
                                  "point": point, "direction": direction}))


@mcp.tool()
def series(expression: str, symbol: str, point: str = "0", order: int = 6) -> dict[str, Any]:
    """Taylor/series expansion of the expression around `symbol`=`point` to order `order`.

    E.g. 'exp(x)', x=0, order=5 → 'x**4/24 + x**3/6 + x**2/2 + x + 1'.
    """
    return asdict(route("series", {"expression": expression, "symbol": symbol,
                                   "point": point, "order": order}))


@mcp.tool()
def solve_system(equations: list[str], symbols: list[str]) -> dict[str, Any]:
    """Solves a SYSTEM of equations for multiple variables.

    Returns: `result` = a list of solution dicts. Empty list = no solution; multiple
    dicts = multiple solutions; free variables appear parametrically (honest).
    """
    return asdict(route("solve_system", {"equations": equations, "symbols": symbols}))


# ----------------------- Linear algebra (matrices) ------------------------ #
@mcp.tool()
def determinant(matrix: list[list[str]]) -> dict[str, Any]:
    """Determinant of a square matrix. Cells may be numeric or symbolic.

    E.g. [["1","2"],["3","4"]] → "-2"; [["a","b"],["c","d"]] → "a*d - b*c".
    """
    return asdict(route("determinant", {"matrix": matrix}))


@mcp.tool()
def matrix_inverse(matrix: list[list[str]]) -> dict[str, Any]:
    """Inverse of a square matrix (A⁻¹). If singular (det=0), an HONEST error.

    Returns: `result` = the inverse matrix (row lists). If not invertible, status=error.
    """
    return asdict(route("matrix_inverse", {"matrix": matrix}))


@mcp.tool()
def eigenvalues(matrix: list[list[str]]) -> dict[str, Any]:
    """Eigenvalues of a square matrix + algebraic multiplicity.

    Returns: `result` = [{"value": ..., "multiplicity": n}, ...]. Complex/irrational
    values are returned in exact form (e.g. "I", "sqrt(2)"); sorted by value as str.
    """
    return asdict(route("eigenvalues", {"matrix": matrix}))


@mcp.tool()
def matrix_rank(matrix: list[list[str]]) -> dict[str, Any]:
    """Rank of a matrix (number of linearly independent rows/columns). Need not be square."""
    return asdict(route("matrix_rank", {"matrix": matrix}))


@mcp.tool()
def matrix_multiply(a: list[list[str]], b: list[list[str]]) -> dict[str, Any]:
    """Product of two matrices A·B. If inner dimensions (A columns = B rows) mismatch, an honest error."""
    return asdict(route("matrix_multiply", {"a": a, "b": b}))


@mcp.tool()
def matrix_solve(matrix: list[list[str]], rhs: list[str]) -> dict[str, Any]:
    """Solves the linear system `A x = b` in matrix form.

    Returns: `result` = solution dicts (`x0,x1,...`). Empty = no solution (inconsistent);
    free variables appear parametrically (honest).
    """
    return asdict(route("matrix_solve", {"matrix": matrix, "rhs": rhs}))


@mcp.tool()
def eigenvectors(matrix: list[list[str]]) -> dict[str, Any]:
    """Eigenvalue + algebraic multiplicity + eigenvector(s). Sorted by eigenvalue (determinism)."""
    return asdict(route("eigenvectors", {"matrix": matrix}))


@mcp.tool()
def rref(matrix: list[list[str]]) -> dict[str, Any]:
    """Reduced row echelon form (RREF) + pivot column indices."""
    return asdict(route("rref", {"matrix": matrix}))


@mcp.tool()
def nullspace(matrix: list[list[str]]) -> dict[str, Any]:
    """A basis of the null space (kernel). Empty list = only zero (trivial)."""
    return asdict(route("nullspace", {"matrix": matrix}))


@mcp.tool()
def lu_decomposition(matrix: list[list[str]]) -> dict[str, Any]:
    """LU decomposition: A = P·L·U. Returns: `L`, `U` matrices + `perm` (row swaps)."""
    return asdict(route("lu_decomposition", {"matrix": matrix}))


# ----------------------------- Number theory ------------------------------ #
@mcp.tool()
def gcd(a: str, b: str) -> dict[str, Any]:
    """Greatest common divisor of two integers (GCD)."""
    return asdict(route("gcd", {"a": a, "b": b}))


@mcp.tool()
def lcm(a: str, b: str) -> dict[str, Any]:
    """Least common multiple of two integers (LCM)."""
    return asdict(route("lcm", {"a": a, "b": b}))


@mcp.tool()
def is_prime(n: str) -> dict[str, Any]:
    """Is `n` prime? (deterministic primality test). Returns: `result` = true/false."""
    return asdict(route("is_prime", {"n": n}))


@mcp.tool()
def factorize(n: str) -> dict[str, Any]:
    """Factorizes `n` into primes. Returns: `[{"prime":p,"exponent":e}, ...]` (ascending)."""
    return asdict(route("factorize", {"n": n}))


@mcp.tool()
def modular_inverse(a: str, m: str) -> dict[str, Any]:
    """Multiplicative inverse of `a` modulo `m`. If none (gcd(a,m)≠1), an honest error."""
    return asdict(route("modular_inverse", {"a": a, "m": m}))


@mcp.tool()
def chinese_remainder(moduli: list[str], residues: list[str]) -> dict[str, Any]:
    """Chinese Remainder Theorem (CRT): x ≡ residues[i] (mod moduli[i]). If incompatible, an honest error.

    Returns: `result` = {"x": ..., "modulus": ...} (smallest non-negative solution).
    """
    return asdict(route("chinese_remainder", {"moduli": moduli, "residues": residues}))


@mcp.tool()
def linear_diophantine(a: str, b: str, c: str) -> dict[str, Any]:
    """Solves the equation `a·x + b·y = c` over INTEGERS (parameter `t_0`).

    Empty list = no integer solution (gcd(a,b) ∤ c) — honest.
    """
    return asdict(route("linear_diophantine", {"a": a, "b": b, "c": c}))


# ------------------------ Combinatorics & discrete ------------------------ #
@mcp.tool()
def permutations(n: str, k: str) -> dict[str, Any]:
    """P(n,k) — the number of ordered selections of `k` from `n` objects (0 if k>n)."""
    return asdict(route("permutations", {"n": n, "k": k}))


@mcp.tool()
def combinations(n: str, k: str) -> dict[str, Any]:
    """C(n,k) — the number of unordered selections of `k` from `n` objects (binomial coefficient)."""
    return asdict(route("combinations", {"n": n, "k": k}))


@mcp.tool()
def factorial(n: str) -> dict[str, Any]:
    """n! — the product of the first `n` positive integers (0! = 1)."""
    return asdict(route("factorial", {"n": n}))


@mcp.tool()
def partition_count(n: str) -> dict[str, Any]:
    """p(n) — the number of ways to write `n` as a sum of positive integers."""
    return asdict(route("partition_count", {"n": n}))


@mcp.tool()
def solve_recurrence(recurrence: str, func: str = "y", var: str = "n",
                     initial: dict[str, str] | None = None) -> dict[str, Any]:
    """Solves a linear recurrence relation to CLOSED FORM.

    E.g. `recurrence="y(n) = y(n-1) + y(n-2)"`, `initial={"0":"0","1":"1"}` →
    the closed form of Fibonacci. If there is no closed form (e.g. nonlinear), an honest error.
    """
    return asdict(route("solve_recurrence", {"recurrence": recurrence, "func": func,
                                             "var": var, "initial": initial}))


# ------------------------- Multivariable calculus ------------------------- #
@mcp.tool()
def gradient(expression: str, variables: list[str]) -> dict[str, Any]:
    """∇f — partial derivatives of `expression` w.r.t. each variable (list)."""
    return asdict(route("gradient", {"expression": expression, "variables": variables}))


@mcp.tool()
def jacobian(expressions: list[str], variables: list[str]) -> dict[str, Any]:
    """Jacobian matrix — the partial-derivative matrix of a vector-valued function."""
    return asdict(route("jacobian", {"expressions": expressions, "variables": variables}))


@mcp.tool()
def hessian(expression: str, variables: list[str]) -> dict[str, Any]:
    """Hessian matrix — the second partial-derivative matrix of a scalar function (symmetric)."""
    return asdict(route("hessian", {"expression": expression, "variables": variables}))


@mcp.tool()
def divergence(field: list[str], variables: list[str]) -> dict[str, Any]:
    """∇·F — divergence of a vector field: Σ ∂Fᵢ/∂xᵢ (field and variables must match in length)."""
    return asdict(route("divergence", {"field": field, "variables": variables}))


@mcp.tool()
def curl(field: list[str], variables: list[str]) -> dict[str, Any]:
    """∇×F — curl of a 3-D vector field. Requires exactly 3 components and 3 variables (e.g. x,y,z)."""
    return asdict(route("curl", {"field": field, "variables": variables}))


@mcp.tool()
def laplacian(expression: str, variables: list[str]) -> dict[str, Any]:
    """∇²f — Laplacian of a scalar field: Σ ∂²f/∂xᵢ². (0 ⟺ harmonic.)"""
    return asdict(route("laplacian", {"expression": expression, "variables": variables}))


@mcp.tool()
def directional_derivative(expression: str, variables: list[str],
                           direction: list[str]) -> dict[str, Any]:
    """Dᵤf — directional derivative ∇f·û along the NORMALIZED `direction` (same length as variables)."""
    return asdict(route("directional_derivative",
                        {"expression": expression, "variables": variables, "direction": direction}))


@mcp.tool()
def line_integral(field: list[str], variables: list[str], parametrization: list[str],
                  param: str, lower: str, upper: str) -> dict[str, Any]:
    """∫_C F·dr — line integral of a vector field along a curve parametrized by `param`.

    Each variable = parametrization[i](param); integrates Σ Fᵢ(r(t))·(drᵢ/dt) over lower..upper.
    E.g. F=(y,x), r(t)=(t, t²), t:0..1 → 1.
    """
    return asdict(route("line_integral",
                        {"field": field, "variables": variables, "parametrization": parametrization,
                         "param": param, "lower": lower, "upper": upper}))


@mcp.tool()
def laplace_transform(expression: str, t_var: str = "t", s_var: str = "s") -> dict[str, Any]:
    """Laplace transform ℒ{f(t)}(s) = ∫₀^∞ f(t)·e^(−st) dt. e.g. `t` → `s**(-2)`, `sin(t)` → `1/(s**2+1)`.

    Honest: if SymPy finds no closed form it returns `error`/`COMPUTE_FAILED`, not an
    unevaluated transform object.
    """
    return asdict(route("laplace_transform",
                        {"expression": expression, "t_var": t_var, "s_var": s_var}))


@mcp.tool()
def inverse_laplace_transform(expression: str, s_var: str = "s", t_var: str = "t") -> dict[str, Any]:
    """Inverse Laplace transform ℒ⁻¹{F(s)}(t). Unilateral → a `Heaviside(t)` factor is expected.

    e.g. `1/s**2` → `t*Heaviside(t)`, `1/(s-a)` → `exp(a*t)*Heaviside(t)`.
    """
    return asdict(route("inverse_laplace_transform",
                        {"expression": expression, "s_var": s_var, "t_var": t_var}))


@mcp.tool()
def fourier_transform(expression: str, x_var: str = "x", k_var: str = "k") -> dict[str, Any]:
    """Fourier transform (SymPy convention ∫ f(x)·e^(−2πi·k·x) dx). e.g. `exp(-x**2)` → `sqrt(pi)*exp(-pi**2*k**2)`."""
    return asdict(route("fourier_transform",
                        {"expression": expression, "x_var": x_var, "k_var": k_var}))


@mcp.tool()
def inverse_fourier_transform(expression: str, k_var: str = "k", x_var: str = "x") -> dict[str, Any]:
    """Inverse Fourier transform ℱ⁻¹{F(k)}(x) (inverse of `fourier_transform`)."""
    return asdict(route("inverse_fourier_transform",
                        {"expression": expression, "k_var": k_var, "x_var": x_var}))


@mcp.tool()
def z_transform(expression: str, n_var: str = "n", z_var: str = "z") -> dict[str, Any]:
    """Unilateral Z-transform Z{x[n]}(z) = Σ_{n≥0} x[n]·z^(−n) — closed form + ROC.

    e.g. `1` → `z/(z-1)`, `a**n` → `z/(z-a)`. Honest `COMPUTE_FAILED` if no closed form.
    """
    return asdict(route("z_transform",
                        {"expression": expression, "n_var": n_var, "z_var": z_var}))


@mcp.tool()
def definite_integral(expression: str, symbol: str, lower: str, upper: str) -> dict[str, Any]:
    """Definite integral ∫ₐᵇ f dx. Bounds may be infinite ("oo"/"-oo")."""
    return asdict(route("definite_integral", {"expression": expression, "symbol": symbol,
                                              "lower": lower, "upper": upper}))


@mcp.tool()
def summation(expression: str, index: str, lower: str, upper: str) -> dict[str, Any]:
    """Summation Σ — sum of `expression` for `index`=lower..upper (may be closed form).

    E.g. `"i", "i", "1", "n"` → `n**2/2 + n/2`.
    """
    return asdict(route("summation", {"expression": expression, "index": index,
                                      "lower": lower, "upper": upper}))


@mcp.tool()
def product(expression: str, index: str, lower: str, upper: str) -> dict[str, Any]:
    """Product Π — product of `expression` for `index`=lower..upper."""
    return asdict(route("product", {"expression": expression, "index": index,
                                    "lower": lower, "upper": upper}))


@mcp.tool()
def solve_ode(equation: str, func: str = "y", var: str = "x") -> dict[str, Any]:
    """Solves an ordinary differential equation (ODE). Derivative: `y'`, `y''` (prime).

    E.g. `"y' = y"` → `Eq(y(x), C1*exp(x))`. If it cannot be solved, an honest error.
    """
    return asdict(route("solve_ode", {"equation": equation, "func": func, "var": var}))


@mcp.tool()
def solve_ode_system(equations: list[str], functions: list[str], var: str = "x") -> dict[str, Any]:
    """Solves a SYSTEM of ODEs for `functions` of one variable. Primes: `f'`, `g''`.

    E.g. `["f' = g", "g' = -f"]`, `["f", "g"]` → f, g as sin/cos combinations.
    """
    return asdict(route("solve_ode_system",
                        {"equations": equations, "functions": functions, "var": var}))


@mcp.tool()
def solve_ode_ivp(equation: str, conditions: list[str], func: str = "y",
                  var: str = "x") -> dict[str, Any]:
    """Solves an ODE with initial/boundary conditions (IVP or BVP).

    `conditions` e.g. `["y(0)=1", "y'(0)=0"]` (initial) or `["y(0)=0", "y(1)=2"]`
    (boundary; `pi` allowed in a point). E.g. y''+y=0, y(0)=0, y'(0)=1 → `Eq(y(x), sin(x))`.
    """
    return asdict(route("solve_ode_ivp",
                        {"equation": equation, "conditions": conditions, "func": func, "var": var}))


@mcp.tool()
def classify_ode(equation: str, func: str = "y", var: str = "x") -> dict[str, Any]:
    """Classifies an ODE — the applicable SymPy solution methods (e.g. `separable`, `1st_linear`)."""
    return asdict(route("classify_ode", {"equation": equation, "func": func, "var": var}))


@mcp.tool()
def solve_pde(equation: str, variables: list[str], func: str = "u") -> dict[str, Any]:
    """Solves a first-order linear PDE (SymPy `pdsolve`). Partials via `D(u, x)`, `D(u, y)`.

    HONEST scope: only what `pdsolve` supports (mostly first-order linear); otherwise
    `COMPUTE_FAILED`. E.g. `"D(u,x) + D(u,y) = 0"`, `["x","y"]` → `Eq(u(x,y), F(x - y))`.
    """
    return asdict(route("solve_pde", {"equation": equation, "variables": variables, "func": func}))


@mcp.tool()
def residue(expression: str, symbol: str, point: str) -> dict[str, Any]:
    """Residue Res(f, z₀) of `expression` at the pole `point` (may be complex, e.g. `I`).

    `I` is the imaginary unit. E.g. `1/z` at `0` → `1`; `1/(z**2+1)` at `I` → `-I/2`.
    A residue of `0` at a regular point is the correct answer, not an error.
    """
    return asdict(route("residue", {"expression": expression, "symbol": symbol, "point": point}))


@mcp.tool()
def contour_integral(expression: str, symbol: str, poles: list[str]) -> dict[str, Any]:
    """∮_C f dz by the RESIDUE THEOREM = 2πi·Σ Res(f, pole) over the ENCLOSED `poles` you supply.

    E.g. `1/(z**2+1)` enclosing `["I"]` → `pi`; enclosing both `["I","-I"]` → `0`.
    """
    return asdict(route("contour_integral",
                        {"expression": expression, "symbol": symbol, "poles": poles}))


@mcp.tool()
def laurent_series(expression: str, symbol: str, point: str = "0",
                   order: int = 6) -> dict[str, Any]:
    """Laurent series of `expression` around `point` up to `order` — includes negative powers.

    E.g. `exp(z)/z**2` around `0` → `z**(-2) + 1/z + 1/2 + z/6 + …`.
    """
    return asdict(route("laurent_series",
                        {"expression": expression, "symbol": symbol, "point": point, "order": order}))


@mcp.tool()
def complex_parts(expression: str) -> dict[str, Any]:
    """Splits a complex expression into real and imaginary parts → `{real, imag}`.

    `I` is the imaginary unit. E.g. `(2 + 3*I)*(1 - I)` → `{"real":"5","imag":"1"}`;
    `exp(I*pi)` → `{"real":"-1","imag":"0"}`.
    """
    return asdict(route("complex_parts", {"expression": expression}))


# ---------------------- Abstract algebra (groups) ------------------------- #
@mcp.tool()
def permutation_order(permutation: list) -> dict[str, Any]:
    """Order of a permutation given in ARRAY form (0-indexed images). E.g. `[1,2,0]` → 3."""
    return asdict(route("permutation_order", {"permutation": permutation}))


@mcp.tool()
def permutation_parity(permutation: list) -> dict[str, Any]:
    """Parity of a permutation (array form): `even` or `odd`. E.g. `[1,0,2]` (a transposition) → odd."""
    return asdict(route("permutation_parity", {"permutation": permutation}))


@mcp.tool()
def permutation_compose(permutations: list) -> dict[str, Any]:
    """Composes permutations (array form) left-to-right; returns the result array + its order.

    All must share the same degree. E.g. `[[1,2,0],[1,0,2]]` → `{array_form:[0,2,1], order:2}`.
    """
    return asdict(route("permutation_compose", {"permutations": permutations}))


@mcp.tool()
def group_order(name: str, degree: int) -> dict[str, Any]:
    """Order (+ whether abelian) of a named group: `symmetric`/`alternating`/`cyclic`/`dihedral`.

    E.g. `symmetric`, 3 → `{order:6, abelian:false}`; `cyclic`, 6 → `{order:6, abelian:true}`.
    """
    return asdict(route("group_order", {"name": name, "degree": degree}))


@mcp.tool()
def generated_group(generators: list) -> dict[str, Any]:
    """Order (+ abelian, degree) of the permutation group generated by `generators` (array form).

    E.g. `[[1,2,0],[1,0,2]]` generates S₃ → `{order:6, abelian:false, degree:3}`.
    """
    return asdict(route("generated_group", {"generators": generators}))


# -------------------- Linear algebra III (decompositions) ----------------- #
@mcp.tool()
def singular_values(matrix: list[list[str]]) -> dict[str, Any]:
    """Singular values σᵢ of a matrix (largest first). E.g. `[[4,0],[3,-5]]` → `[2*sqrt(10), sqrt(10)]`."""
    return asdict(route("singular_values", {"matrix": matrix}))


@mcp.tool()
def qr_decomposition(matrix: list[list[str]]) -> dict[str, Any]:
    """QR decomposition A = Q·R (Q orthonormal columns, R upper-triangular) → `{Q, R}`."""
    return asdict(route("qr_decomposition", {"matrix": matrix}))


@mcp.tool()
def cholesky_decomposition(matrix: list[list[str]]) -> dict[str, Any]:
    """Cholesky A = L·Lᵀ (L lower-triangular) → `{L}`. Needs symmetric positive-definite (else error)."""
    return asdict(route("cholesky_decomposition", {"matrix": matrix}))


@mcp.tool()
def gram_schmidt(vectors: list[list[str]], normalize: bool = True) -> dict[str, Any]:
    """Gram-Schmidt orthogonalization of a list of vectors (orthonormal if `normalize`)."""
    return asdict(route("gram_schmidt", {"vectors": vectors, "normalize": normalize}))


@mcp.tool()
def pseudoinverse(matrix: list[list[str]]) -> dict[str, Any]:
    """Moore-Penrose pseudo-inverse A⁺ (works for non-square / singular A)."""
    return asdict(route("pseudoinverse", {"matrix": matrix}))


@mcp.tool()
def matrix_exponential(matrix: list[list[str]]) -> dict[str, Any]:
    """Matrix exponential e^A (square). E.g. `[[0,1],[0,0]]` → `[[1,1],[0,1]]`."""
    return asdict(route("matrix_exponential", {"matrix": matrix}))


@mcp.tool()
def jordan_form(matrix: list[list[str]]) -> dict[str, Any]:
    """Jordan canonical form A = P·J·P⁻¹ (J block-diagonal) → `{P, J}`."""
    return asdict(route("jordan_form", {"matrix": matrix}))


@mcp.tool()
def characteristic_polynomial(matrix: list[list[str]], symbol: str = "lambda") -> dict[str, Any]:
    """Characteristic polynomial det(A − λI) of a square matrix. E.g. diag(2,3) → `lambda**2 - 5*lambda + 6`."""
    return asdict(route("characteristic_polynomial", {"matrix": matrix, "symbol": symbol}))


@mcp.tool()
def least_squares(matrix: list[list[str]], rhs: list[str]) -> dict[str, Any]:
    """Least-squares solution of A·x ≈ b (minimizes ‖A·x − b‖) for overdetermined systems."""
    return asdict(route("least_squares", {"matrix": matrix, "rhs": rhs}))


# --------------------------- Graph theory --------------------------------- #
@mcp.tool()
def shortest_path(edges: list, source: Any, target: Any, directed: bool = False,
                  weighted: bool = False) -> dict[str, Any]:
    """Shortest path source→target. Edges `[u,v]` or `[u,v,weight]` (set `weighted`). Dijkstra/BFS.

    Returns `{path, length}`; `{path:null}` if unreachable (honest, not fabricated).
    """
    return asdict(route("shortest_path", {"edges": edges, "source": source, "target": target,
                                          "directed": directed, "weighted": weighted}))


@mcp.tool()
def connected_components(edges: list, nodes: list | None = None,
                         directed: bool = False) -> dict[str, Any]:
    """Connected components → `{count, is_connected, components}`. `nodes` adds isolated vertices."""
    return asdict(route("connected_components",
                        {"edges": edges, "nodes": nodes, "directed": directed}))


@mcp.tool()
def minimum_spanning_tree(edges: list) -> dict[str, Any]:
    """Minimum spanning tree/forest (Kruskal). Edges `[u,v,weight]` → `{edges, total_weight, spans_all}`."""
    return asdict(route("minimum_spanning_tree", {"edges": edges}))


@mcp.tool()
def max_flow(edges: list, source: Any, sink: Any) -> dict[str, Any]:
    """Maximum flow source→sink (Edmonds-Karp). Directed `[u,v,capacity]`. Equals the min-cut capacity."""
    return asdict(route("max_flow", {"edges": edges, "source": source, "sink": sink}))


@mcp.tool()
def maximum_matching(edges: list, left: list) -> dict[str, Any]:
    """Maximum bipartite matching (Kuhn). `left` = the left-partition nodes → `{size, matching}`."""
    return asdict(route("maximum_matching", {"edges": edges, "left": left}))


@mcp.tool()
def is_isomorphic(edges1: list, edges2: list, nodes1: list | None = None,
                  nodes2: list | None = None) -> dict[str, Any]:
    """Are two undirected graphs isomorphic? Backtracking + degree pruning (≤10 nodes) → `{isomorphic, mapping}`."""
    return asdict(route("is_isomorphic",
                        {"edges1": edges1, "edges2": edges2, "nodes1": nodes1, "nodes2": nodes2}))


# --------------------------- Number theory II ----------------------------- #
@mcp.tool()
def euler_totient(n: int) -> dict[str, Any]:
    """Euler's totient φ(n) — the count of 1..n coprime to n. E.g. φ(12) = 4."""
    return asdict(route("euler_totient", {"n": n}))


@mcp.tool()
def mobius(n: int) -> dict[str, Any]:
    """Möbius μ(n): 0 if a squared prime divides n, else (−1)^(#distinct primes). E.g. μ(30) = −1."""
    return asdict(route("mobius", {"n": n}))


@mcp.tool()
def continued_fraction(numerator: int, denominator: int = 1) -> dict[str, Any]:
    """Continued-fraction terms of the rational numerator/denominator. E.g. 415/93 → `[4,2,6,7]`."""
    return asdict(route("continued_fraction",
                        {"numerator": numerator, "denominator": denominator}))


@mcp.tool()
def continued_fraction_sqrt(n: int) -> dict[str, Any]:
    """Periodic continued fraction of √n → `{a0, period}`. E.g. √23 → `{a0:4, period:[1,3,1,8]}`."""
    return asdict(route("continued_fraction_sqrt", {"n": n}))


@mcp.tool()
def quadratic_residue(a: int, n: int) -> dict[str, Any]:
    """Is `a` a quadratic residue mod `n`? → `{is_residue, jacobi_symbol}` (Legendre when n is prime)."""
    return asdict(route("quadratic_residue", {"a": a, "n": n}))


@mcp.tool()
def primitive_root(n: int) -> dict[str, Any]:
    """Smallest primitive root mod `n` (generator of the units), or `null` when none exists (honest)."""
    return asdict(route("primitive_root", {"n": n}))


@mcp.tool()
def pell_solution(n: int) -> dict[str, Any]:
    """Fundamental solution of the Pell equation x² − n·y² = 1 → `{x, y}`. E.g. n=13 → `{x:649, y:180}`."""
    return asdict(route("pell_solution", {"n": n}))


# --------------------------- Combinatorics II ----------------------------- #
@mcp.tool()
def catalan_number(n: int) -> dict[str, Any]:
    """The n-th Catalan number Cₙ. E.g. C₅ = 42 (balanced parentheses, binary trees, …)."""
    return asdict(route("catalan_number", {"n": n}))


@mcp.tool()
def bell_number(n: int) -> dict[str, Any]:
    """The n-th Bell number Bₙ — partitions of an n-element set. E.g. B₅ = 52."""
    return asdict(route("bell_number", {"n": n}))


@mcp.tool()
def stirling_number(n: int, k: int, kind: str = "second") -> dict[str, Any]:
    """Stirling number of the `first` (cycles) or `second` (blocks) kind. E.g. S(5,2) 2nd = 15."""
    return asdict(route("stirling_number", {"n": n, "k": k, "kind": kind}))


@mcp.tool()
def derangements(n: int) -> dict[str, Any]:
    """Derangement count !n (permutations with no fixed point; inclusion-exclusion). E.g. !4 = 9."""
    return asdict(route("derangements", {"n": n}))


@mcp.tool()
def generating_function_coefficient(expression: str, symbol: str, n: int) -> dict[str, Any]:
    """Coefficient of `symbol`ⁿ in a generating function's series. E.g. `1/(1-x-x**2)` at 6 → 13 (F₇)."""
    return asdict(route("generating_function_coefficient",
                        {"expression": expression, "symbol": symbol, "n": n}))


@mcp.tool()
def necklace_count(n: int, colors: int) -> dict[str, Any]:
    """Distinct necklaces of `n` beads in `colors` colors under rotation (Burnside/Pólya). n=4,c=2 → 6."""
    return asdict(route("necklace_count", {"n": n, "colors": colors}))


# ------------------------ Probability & statistics ------------------------ #
@mcp.tool()
def mean(data: list[str]) -> dict[str, Any]:
    """Arithmetic mean of a list of numbers (exact/rational)."""
    return asdict(route("mean", {"data": data}))


@mcp.tool()
def variance(data: list[str], sample: bool = False) -> dict[str, Any]:
    """Variance. sample=True → sample (n-1); otherwise population (n)."""
    return asdict(route("variance", {"data": data, "sample": sample}))


@mcp.tool()
def standard_deviation(data: list[str], sample: bool = False) -> dict[str, Any]:
    """Standard deviation = √variance (the sample option is the same as variance)."""
    return asdict(route("standard_deviation", {"data": data, "sample": sample}))


@mcp.tool()
def median(data: list[str]) -> dict[str, Any]:
    """Median. With an even number of observations, the mean of the middle two."""
    return asdict(route("median", {"data": data}))


@mcp.tool()
def distribution(name: str, params: list[str], at: str | None = None) -> dict[str, Any]:
    """E[X]/Var/std (symbolic/exact) properties of a named distribution.

    If `at` is given, `P(X ≤ at)` (cdf) + density/pmf are added. Supported:
    normal(mu,sigma), binomial(n,p), poisson(lambda), exponential(rate),
    uniform(a,b), bernoulli(p), geometric(p).
    """
    return asdict(route("distribution", {"name": name, "params": params, "at": at}))


# ------------------- Frontier / Track B (SAT reduction) ------------------- #
@mcp.tool()
def pythagorean_coloring(n: int) -> dict[str, Any]:
    """Tries to 2-color {1..n} with no monochromatic Pythagorean triple.

    A Track B demonstration: sat -> a coloring was found; unsat -> an impossibility proof.
    (The same encoding as the ~200 TB proof that settled n=7825 in 2016; small scale.)
    """
    return asdict(route("pythagorean_coloring", {"n": n}))


@mcp.tool()
def pigeonhole(n: int) -> dict[str, Any]:
    """Proves that `n+1` pigeons cannot fit into `n` holes (the pigeonhole principle)."""
    return asdict(route("pigeonhole", {"n": n}))


@mcp.tool()
def van_der_waerden(n: int, k: int, colors: int = 2) -> dict[str, Any]:
    """Tries to `colors`-color {1..n} with no monochromatic k-term arithmetic progression.

    The core of computing the van der Waerden number W(colors,k): `unsat` -> n ≥ W (a proof).
    Known W values were computed with this method; large/open values return `unknown`.
    """
    return asdict(route("van_der_waerden", {"n": n, "k": k, "colors": colors}))


@mcp.tool()
def schur_number(n: int, colors: int) -> dict[str, Any]:
    """Tries to partition {1..n} into `colors` sum-free colors (the core of the Schur number S(colors)).

    `unsat` -> n > S(colors) (a proof). Known: S(2)=4, S(3)=13, S(4)=44, S(5)=160;
    S(6) is open.
    """
    return asdict(route("schur_number", {"n": n, "colors": colors}))


@mcp.tool()
def graph_coloring(edges: list[list[int]], colors: int, n: int | None = None) -> dict[str, Any]:
    """Colors a graph with `colors` colors (neighbors differ). NP-complete graph k-coloring.

    `sat` → a coloring (INDEPENDENTLY verified, `meta.verified`); `unsat` → chromatic
    number > colors. Vertices are 1-indexed; edges `[[u,v],...]`.
    """
    return asdict(route("graph_coloring", {"edges": edges, "colors": colors, "n": n}))


@mcp.tool()
def subset_sum(numbers: list[int], target: int) -> dict[str, Any]:
    """Does a subset of `numbers` sum to `target`? (NP-complete subset-sum).

    `sat` → the summing subset (an INDEPENDENTLY verified certificate); `unsat` → none.
    """
    return asdict(route("subset_sum", {"numbers": numbers, "target": target}))


def main() -> None:
    """Starts the server over stdio (for local MCP clients)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
