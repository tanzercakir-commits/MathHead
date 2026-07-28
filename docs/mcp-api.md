# MathHead — MCP API & Protocol

> The engine's **single contract** with the outside world. This file and
> `server/mcp_server.py` must match exactly; the signatures were **frozen early**
> (DECISIONS ADR-0004). The counterpart of your "clean protocol / API definition"
> requirement.

## Transport

- SDK: `mcp[cli]` (FastMCP), Python 3.10+
- Local run: `mathhead-server` or `python -m mathhead.server.mcp_server`
- Transport: `stdio` (for local MCP clients)

---

## Tools

### 1) `entailment(premises: list[str], conclusion: str) -> ReasoningResult`

Do the premises logically entail the conclusion? (`premises ⊨ conclusion`)

- `valid` → entails (`reason_code=ENTAILED`)
- `invalid` → does not entail; `witness` is a **counterexample** (`COUNTEREXAMPLE_FOUND`)
- `unknown` → the solver could not decide (`SOLVER_TIMEOUT` / `SOLVER_UNKNOWN`)

### 2) `consistency(statements: list[str]) -> ReasoningResult`

Can the statements be true at the same time? (consistency / satisfiability)

- `sat` → consistent; `witness` = an example assignment (model)
- `unsat` → contradictory; `witness` = the conflicting subset (**unsat core**)
- `unknown` → could not be decided

### 3) `model(statements: list[str]) -> ReasoningResult`

Returns a **concrete** example (variable assignment) that satisfies the
statements. `sat` → `witness` = model; `unsat` → no model; `unknown` → indeterminate.

### 4) `prove(premises: list[str], conclusion: str) -> ProofResult`

Entailment + **why**. If `valid`: `used_premises` (the minimal subset of premises
the conclusion rests on) + `proof_steps` (step-by-step natural deduction for the
propositional/predicate/universal part; if it cannot be built, the Z3 verdict is
kept, without steps). If `invalid`, `witness` = counterexample. Two strategies:
DIRECT forward chaining; failing that, BY CONTRADICTION (RAA). Step format:
`{step, formula, rule, refs}` — rules: `modus ponens`, `modus tollens`,
`disjunctive syllogism`, `conjunction elimination`, `iff elimination`,
`double negation`, `De Morgan`, `universal instantiation`,
`existential elimination`, `existential introduction`,
`proof by contradiction (RAA)`.

### 5) `enumerate_models(statements: list[str], limit: int = 10) -> ModelSet`

Enumerates the **distinct** models (at most `limit`) that satisfy the statements
(all-SAT; blocking-clause method). Returns: `models` (list), `count`,
`exhaustive` — `True` = all found (unsat was reached); `False` = the limit was
reached, and in an infinite domain (unbounded Int/Real) there may be more.

### 6) `optimize(constraints: list[str], objective: str, sense = "max") -> OptimizeResult`

Finds the solution that satisfies the constraints and makes the numeric
`objective` largest/smallest (`sense`: `max`/`min`) (Z3 Optimize —
*optimization modulo theories*). Returns: `status` ∈ {`optimal`, `unbounded`,
`unsat`, `unknown`, `error`}, `objective_value`, `witness` (the assignment that
achieves the optimum), `sense`. Unbounded (`unbounded`), no-feasible-solution
(`unsat`), and open-bound (supremum/infimum, not exactly reachable via ε) cases
are reported honestly.

### 7) `max_satisfy(hard: list[str], soft: list[str], weights=None) -> MaxSatResult`

Satisfies the mandatory (`hard`) constraints and satisfies AS MANY (weighted)
`soft` constraints as possible (MaxSAT). For over-constrained / conflicting
requests, "not all, but the best". Returns: `status`; if optimal, `satisfied` /
`unsatisfied` (soft indices), `satisfied_weight` / `total_weight`, `witness`. If
`hard` is unsatisfiable, `unsat`.

### 8) `equivalent(a: str, b: str) -> ReasoningResult`

Are the two expressions logically EQUIVALENT (same truth value under every
assignment)? `status` ∈ {`equivalent`, `not_equivalent`, `unknown`, `error`}; if
`not_equivalent`, `witness` = an assignment where the two differ.

### 9) `classify(formula: str) -> ReasoningResult`

Classifies a formula: `status` ∈ {`tautology` (always true), `contradiction`
(always false), `contingent` (sometimes true, sometimes false), `unknown`,
`error`}. If `contingent`, `witness` = a satisfying + a falsifying assignment.

---

## Input grammar (v1.2)

Input is written in **Python expression syntax**; the engine's parser (`ast`-based,
whitelisted — ADR-0009/0010) allows only the following and cleanly rejects the
rest. Because Python does the parsing, **operator precedence and parentheses**
work as expected.

| Category | Allowed | Note |
|---|---|---|
| Boolean connective | `and`, `or`, `not` | Python keywords |
| Boolean function | `implies(a, b)`, `iff(a, b)`, `xor(a, b)` | each takes exactly 2 arguments |
| Quantifier | `forall(x, body)`, `exists(x, body)` | `x` is the bound variable |
| Predicate / relation | `Man(x)`, `Loves(a, b)` | uninterpreted; arguments are **individuals** |
| Comparison | `<`, `<=`, `==`, `!=`, `>=`, `>` | chaining supported: `1 < x < 5` |
| Arithmetic | `+`, `-`, `*` | **linear**: `variable*variable` forbidden |
| Variable | `Bool` or numeric | sort inferred **from context** (below) |
| Constant | integer, decimal, `True`, `False` | decimal → Real |

**Sort inference (type):** whether a name is Boolean or Int is determined from its
usage — appearing inside a comparison/arithmetic → `Int`; inside a
connective/function or as a bare atom → `Bool`. If a name is used as both Bool and
Int **in the same problem**, the engine returns `error` (`PARSE_ERROR`) — no
silent assumptions (PRINCIPLES #2).

**Numeric domain (Int vs Real):** if the problem contains any **decimal** constant
(e.g. `2.0`), all numeric variables are **Real**, otherwise **Int** (a v1.1
simplification; no mixing within the same problem). It changes meaning:
`exists(x, 1 < x and x < 2)` is **unsat** over Int; over Real, with
`1.0 < x and x < 2.0`, it is **sat**.

**Still MISSING:** uninterpreted function terms (`f(x)` — returning an individual),
in-predicate arithmetic, nonlinear multiplication, set/array theories. (Predicates
`P(x)` and individual constants were **added** in v1.2 — the classic syllogism
works.) **Honest warning:** quantifiers make FOL semi-decidable; Z3 may return
`unknown` on some formulas (e.g. nested `∀∃`) — this is not hidden, it is reported
first-class (soundness: the engine never produces a wrong answer).

Example valid expressions: `p`, `implies(p, q)`, `p and (q or not(r))`, `1 < x < 5`,
`2*x + 3 <= y`, `forall(x, implies(x > 2, x > 1))`, `exists(x, 1.0 < x and x < 2.0)`.

---

## Output contract — `ReasoningResult`

| Field | Type | Meaning |
|---|---|---|
| `status` | str | `valid` \| `invalid` \| `sat` \| `unsat` \| `unknown` \| `error` |
| `reason_code` | str | machine-readable code (table below) |
| `explanation` | str | human-readable explanation |
| `witness` | dict \| null | model (sat) / counterexample (invalid) / unsat core |
| `meta` | dict | `engine`, `z3_version`, `elapsed_ms`, `seed`, `timeout_ms` |

### `reason_code` values

| Code | When |
|---|---|
| `ENTAILED` | entailment valid |
| `COUNTEREXAMPLE_FOUND` | entailment invalid, counterexample exists |
| `CONSISTENT` | statements consistent (sat) |
| `CONTRADICTION` | statements contradictory (unsat) |
| `MODEL_FOUND` | find_model: model found (sat) |
| `NO_MODEL` | find_model: no model (unsat) |
| `SOLVER_TIMEOUT` | timeout → unknown |
| `SOLVER_UNKNOWN` | solver could not decide → unknown |
| `PARSE_ERROR` | grammar violation → error |
| `GUARDRAIL_VIOLATION` | size/depth/symbol limit → error |

---

## Example (AI → MathHead)

**Request**

```json
{ "tool": "entailment",
  "premises": ["p", "implies(p, q)"],
  "conclusion": "q" }
```

**Response**

```json
{ "status": "valid",
  "reason_code": "ENTAILED",
  "explanation": "q follows from the premises by modus ponens.",
  "witness": null,
  "meta": { "engine": "z3", "z3_version": "4.13.x", "elapsed_ms": 3, "seed": 42 } }
```

**Counterexample example** — `entailment(["x > 0"], "x > 5")`

```json
{ "status": "invalid",
  "reason_code": "COUNTEREXAMPLE_FOUND",
  "explanation": "x = 1 satisfies the premise but not the conclusion.",
  "witness": { "x": 1 },
  "meta": { "engine": "z3", "elapsed_ms": 2, "seed": 42 } }
```

---

## Compute tools (v2 — SymPy)

Separate from the logic tools; symbolic **computation** (not proof). Input is
again filtered through the ast-whitelist (no `sympify`/`eval`). Here `*`, `/`,
`**` (power) and nonlinear expressions are **allowed**.

| Tool | Signature | Example |
|---|---|---|
| `simplify` | `simplify(expression)` | `sin(x)**2 + cos(x)**2` → `1` |
| `solve` | `solve(equation, symbol)` | `x**2 == 4`, `x` → `["-2","2"]` |
| `differentiate` | `differentiate(expression, symbol, order=1)` | `x**3+2*x`, `x` → `3*x**2 + 2` |
| `integrate` | `integrate(expression, symbol)` | `2*x`, `x` → `x**2` (+C) |
| `limit` | `limit(expression, symbol, point="0", direction="both")` | `sin(x)/x`, `x`, `0` → `1` |
| `series` | `series(expression, symbol, point="0", order=6)` | `exp(x)`, `x`, `0`, `5` → `x**4/24 + x**3/6 + x**2/2 + x + 1` |
| `solve_system` | `solve_system(equations: list[str], symbols: list[str])` | `["x+y==10","x-y==2"]`, `["x","y"]` → `[{"x":"6","y":"4"}]` |

**Allowed:** `+ - * / **`, unary `-`, symbols, numbers (integer/decimal),
functions `sin cos tan asin acos atan sinh cosh tanh exp log sqrt Abs`, and the
mathematical constants `pi` (π) and `E` (e). A bare `pi`/`E` is the constant, not a
free symbol; a variable you pass explicitly (e.g. a `symbol` argument) stays a
variable. `solve` input may be `a == b` (Eq) or a plain expression assumed `=0`.

**Vector calculus (D1):** `divergence(field, variables)` (∇·F), `curl(field,
variables)` (∇×F, 3-D only), `laplacian(expression, variables)` (∇²f),
`directional_derivative(expression, variables, direction)` (∇f·û, normalized),
`line_integral(field, variables, parametrization, param, lower, upper)` (∫_C F·dr).

**Integral transforms (D2):** `laplace_transform(expression, t_var="t", s_var="s")`,
`inverse_laplace_transform(...)`, `fourier_transform(expression, x_var="x", k_var="k")`,
`inverse_fourier_transform(...)`, `z_transform(expression, n_var="n", z_var="z")` (unilateral,
returns the closed form + ROC). Each returns `error`/`COMPUTE_FAILED` when SymPy finds no closed
form — an unevaluated transform object is never passed off as an answer.

**Differential equations II (D3):** `solve_ode_system(equations, functions, var)`,
`solve_ode_ivp(equation, conditions, func, var)` (IVP **or** BVP — conditions like
`"y(0)=0"`, `"y'(0)=1"`), `classify_ode(equation, func, var)`, and `solve_pde(equation,
variables, func)` (first-order linear only — honest `COMPUTE_FAILED` otherwise).
Derivative input across the ODE/PDE family: prime notation `y'`/`y''` (w.r.t. the first
variable) or the marker `D(func, var, …)` for explicit partials (e.g. `D(u,x)`).

**Complex analysis (D4):** `residue(expression, symbol, point)` (Res(f, z₀); `point` may be
complex, e.g. `I`), `contour_integral(expression, symbol, poles)` (∮ = 2πi·Σ Res over the
enclosed poles you supply), `laurent_series(expression, symbol, point="0", order=6)` (includes
negative powers), `complex_parts(expression)` (→ `{real, imag}`). `I` is the imaginary unit in
any compute expression.

**Abstract algebra — permutation groups (E1):** `permutation_order`, `permutation_parity`
(even/odd), `permutation_compose` (→ result array + order), `group_order(name, degree)` (named
groups `symmetric`/`alternating`/`cyclic`/`dihedral` → order + abelian), `generated_group(generators)`
(order + abelian + degree). Permutations are in **array form** — the 0-indexed image list, e.g.
`[1,2,0]` is the cycle (0 1 2).

**Linear algebra III (E2):** `singular_values`, `qr_decomposition` (→ `{Q, R}`),
`cholesky_decomposition` (→ `{L}`; symmetric positive-definite required), `gram_schmidt(vectors,
normalize=True)`, `pseudoinverse` (A⁺), `matrix_exponential` (e^A), `jordan_form` (→ `{P, J}`),
`characteristic_polynomial(matrix, symbol="lambda")`, `least_squares(matrix, rhs)`. All symbolic
(exact); a precondition failure (e.g. non-positive-definite Cholesky) is an honest `COMPUTE_FAILED`.

**Graph theory (E3, pure stdlib):** `shortest_path(edges, source, target, directed, weighted)`
(Dijkstra/BFS; `{path,length}`, honest `null` if unreachable), `connected_components(edges, nodes)`,
`minimum_spanning_tree(edges)` (Kruskal), `max_flow(edges, source, sink)` (Edmonds-Karp = min cut),
`maximum_matching(edges, left)` (bipartite, Kuhn), `is_isomorphic(edges1, edges2)` (backtracking,
≤10 nodes). Edges are `[u,v]` or `[u,v,weight]`; nodes are ints or strings.

**Number theory II (E4):** `euler_totient(n)` (φ), `mobius(n)` (μ), `continued_fraction(numerator,
denominator)` (→ term list), `continued_fraction_sqrt(n)` (→ `{a0, period}`), `quadratic_residue(a,
n)` (→ `{is_residue, jacobi_symbol}`), `primitive_root(n)` (smallest, or `null` if none — honest),
`pell_solution(n)` (fundamental x²−n·y²=1, or `null` for a perfect square).

**Combinatorics II (E5):** `catalan_number(n)`, `bell_number(n)`, `stirling_number(n, k,
kind="second")` (`first`/`second`), `derangements(n)` (!n, inclusion-exclusion),
`generating_function_coefficient(expression, symbol, n)` ([xⁿ] of a GF's series), `necklace_count(n,
colors)` (distinct necklaces under rotation — Burnside/Pólya).

**Probability II (F1):** `bayes_theorem(prior, likelihood, false_alarm)` (→ `{posterior, evidence}`),
`covariance(x, y, sample=False)`, `correlation(x, y)` (Pearson ρ), `markov_stationary(matrix)`
(stationary π of a row-stochastic matrix), `markov_step(matrix, initial, steps)` (initial·Pᵏ),
`joint_marginal(joint, axis="row")`. All exact (rationals); zero evidence / zero variance /
non-stochastic matrix are honest errors.

**Inferential statistics (F2):** `t_test(sample1, sample2=None, mu=0)` (one-sample or Welch
two-sample), `z_test(sample, mu, sigma)`, `chi_square_test(observed, expected)`,
`anova_oneway(groups)`, `confidence_interval(data, confidence=0.95)`, `linear_regression(x, y)`.
p-values are NUMERICAL — computed deterministically via mpmath's incomplete gamma/beta (SymPy's
own dependency; no new package), then rounded. Same input → same output.

**Optimization II — symbolic (F3):** `critical_points(expression, variables)` (∇f=0, each
classified `local_min`/`local_max`/`saddle`/`inconclusive` by the Hessian),
`lagrange_multipliers(objective, constraints, variables)` (equality-constrained; returns points +
multipliers + objective value), `check_convexity(expression, variables)` (Hessian test →
`convex`/`concave`/`neither`/`undetermined`). Variables are treated as real. (Linear/integer LP over
reals/ints is the existing `optimize` tool via Z3.)

**Calculus & systems:** `limit`'s point may be infinite (`point="oo"` / `"-oo"`)
and `direction` takes `"+"`/`"-"` for a one-sided limit. `series` returns a Taylor
expansion of order `order` around `point` (`removeO`). `solve_system` returns a
**list of solution dicts**: empty list = no solution (honest), multiple dicts =
multiple solutions (including nonlinear systems), free variables appear
parametrically.

### Linear algebra (matrix)

Input is **`list[list[str]]`** (lists of rows); each cell is again filtered
through the ast-whitelist and may be symbolic. In the CLI, a MATLAB-style string:
`"1,2;3,4"`.

| Tool | Signature | Example |
|---|---|---|
| `determinant` | `determinant(matrix)` | `[["1","2"],["3","4"]]` → `"-2"`; `[["a","b"],["c","d"]]` → `"a*d - b*c"` |
| `matrix_inverse` | `matrix_inverse(matrix)` | `[["1","2"],["3","4"]]` → `[["-2","1"],["3/2","-1/2"]]` |
| `eigenvalues` | `eigenvalues(matrix)` | `[["2","0"],["0","3"]]` → `[{"value":"2","multiplicity":1},{"value":"3","multiplicity":1}]` |
| `matrix_rank` | `matrix_rank(matrix)` | `[["1","2"],["2","4"]]` → `1` |
| `matrix_multiply` | `matrix_multiply(a, b)` | `[[1,2],[3,4]]·[[5,6],[7,8]]` → `[["19","22"],["43","50"]]` |
| `matrix_solve` | `matrix_solve(matrix, rhs)` | `A=[[1,1],[1,-1]]`, `b=["10","2"]` → `[{"x0":"6","x1":"4"}]` |
| `eigenvectors` | `eigenvectors(matrix)` | `[["2","0"],["0","3"]]` → `[{"eigenvalue":"2","multiplicity":1,"vectors":[["1","0"]]}, ...]` |
| `rref` | `rref(matrix)` | → `{"rref": [...], "pivots": [0,1]}` |
| `nullspace` | `nullspace(matrix)` | `[["1","2"],["2","4"]]` → `[["-2","1"]]` |
| `lu_decomposition` | `lu_decomposition(matrix)` | → `{"L":[...], "U":[...], "perm":[...]}` |

`determinant`/`matrix_inverse`/`eigenvalues`/`eigenvectors`/`lu_decomposition`
require a **square** matrix (otherwise `PARSE_ERROR`). **Honesty:** on a singular
(det=0) matrix `matrix_inverse` does not fabricate, it returns `COMPUTE_FAILED`;
`eigenvalues`/`eigenvectors` give complex/irrational values in exact form (`"I"`,
`"sqrt(2)"`) and state algebraic multiplicity explicitly, sorted by
`value`/`eigenvalue` (determinism — ADR-0019). `matrix_multiply` errors if the
inner dimensions mismatch (`A.cols ≠ B.rows`). `matrix_solve` (`Ax=b`) returns a
**list of solution dicts**: empty = no solution (inconsistent), free variables
parametric (`"3 - x1"`). `matrix_rank`/`rref`/`nullspace` also work on non-square
matrices; `nullspace` empty list = trivial (only zero).

### Number theory

Over the integers. Input is filtered through the ast-whitelist (`"2**10"`
allowed); if the result is not an integer, `PARSE_ERROR`.

| Tool | Signature | Example |
|---|---|---|
| `gcd` | `gcd(a, b)` | `48, 36` → `12` |
| `lcm` | `lcm(a, b)` | `4, 6` → `12` |
| `is_prime` | `is_prime(n)` | `97` → `true`; `91` → `false` |
| `factorize` | `factorize(n)` | `360` → `[{"prime":2,"exponent":3},{"prime":3,"exponent":2},{"prime":5,"exponent":1}]` |
| `modular_inverse` | `modular_inverse(a, m)` | `3, 11` → `4` |
| `chinese_remainder` | `chinese_remainder(moduli, residues)` | `[3,5,7],[2,3,2]` → `{"x":23,"modulus":105}` |
| `linear_diophantine` | `linear_diophantine(a, b, c)` | `3,6,9` → `[{"x":"3 - 2*t_0","y":"t_0"}]` |

**Honesty:** `modular_inverse` does not fabricate when no inverse exists
(gcd(a,m)≠1), `COMPUTE_FAILED`; `chinese_remainder` errors if the moduli are
incompatible; `linear_diophantine` returns an **empty list** when there is no
integer solution (gcd(a,b) ∤ c); `factorize(1)` = `[]` (no prime factors). The
Diophantine solution is parametric (parameter `t_0`).

### Combinatorics & discrete

| Tool | Signature | Example |
|---|---|---|
| `permutations` | `permutations(n, k)` | `10, 3` → `720` (k>n → `0`) |
| `combinations` | `combinations(n, k)` | `10, 3` → `120` |
| `factorial` | `factorial(n)` | `6` → `720` |
| `partition_count` | `partition_count(n)` | `10` → `42` |
| `solve_recurrence` | `solve_recurrence(recurrence, func="y", var="n", initial={})` | `"y(n)=y(n-1)+y(n-2)"`, `{"0":"0","1":"1"}` → Fibonacci closed form |

`solve_recurrence` reads the recurrence with a separate safe parser (`func` calls
+ `var` + arithmetic; `=` or `==` accepted; names/calls outside the whitelist are
rejected). **Honesty:** for a nonlinear / no-closed-form recurrence it does not
fabricate, it returns `COMPUTE_FAILED`. `permutations`/`combinations` give `0` for
`k>n` (combinatorially correct); negative input is rejected.

### Multivariable calculus

| Tool | Signature | Example |
|---|---|---|
| `gradient` | `gradient(expression, variables)` | `x**2*y+sin(y)`, `["x","y"]` → `["2*x*y","x**2 + cos(y)"]` |
| `jacobian` | `jacobian(expressions, variables)` | `["x*y","x+y"]`, `["x","y"]` → `[["y","x"],["1","1"]]` |
| `hessian` | `hessian(expression, variables)` | → symmetric 2nd-derivative matrix |
| `definite_integral` | `definite_integral(expression, symbol, lower, upper)` | `x**2`, `x`, `0`, `3` → `9`; bound may be `oo` |
| `summation` | `summation(expression, index, lower, upper)` | `i`, `i`, `1`, `n` → `n**2/2 + n/2` (closed form) |
| `product` | `product(expression, index, lower, upper)` | `i`, `i`, `1`, `5` → `120` |
| `solve_ode` | `solve_ode(equation, func="y", var="x")` | `"y'' + y = 0"` → `Eq(y(x), C1*sin(x) + C2*cos(x))` |

`solve_ode` reads the derivative as `y'`, `y''` (prime marks) or `D(y, k)`; it uses
a separate safe parser (`=`/`==`, names outside the whitelist are rejected).
**Honesty:** for an unsolvable ODE it does not fabricate, `COMPUTE_FAILED`.
`definite_integral`/`summation` bounds may be infinite (`oo`), and `summation`'s
upper bound may be symbolic (`n`).

### Probability & statistics

| Tool | Signature | Example |
|---|---|---|
| `mean` | `mean(data)` | `[2,4,4,4,5,5,7,9]` → `5` |
| `variance` | `variance(data, sample=False)` | population → `4`; `sample=True` → `32/7` |
| `standard_deviation` | `standard_deviation(data, sample=False)` | → `2` |
| `median` | `median(data)` | even n → average of the middle two (`9/2`) |
| `distribution` | `distribution(name, params, at=None)` | `binomial`,`["10","1/2"]`,`"3"` → `{mean:5, variance:5/2, cdf_at:11/64, density_at:15/128}` |

Descriptive statistics give **exact/rational** results (symbolic data is
rejected). `distribution` is **symbolic/exact** on top of `sympy.stats`: `E[X]`,
`Var`, `std`; if `at` is given, `P(X ≤ at)` (cdf) + density/pmf. Supported:
`normal(mu,sigma)`, `binomial(n,p)`, `poisson(lambda)`, `exponential(rate)`,
`uniform(a,b)`, `bernoulli(p)`, `geometric(p)`. An unknown distribution / wrong
number of parameters is rejected (honest).

**Output — `ComputeResult`:** `status` (`ok`|`error`), `operation`, `result`
(text or list of roots), `explanation`, `reason_code` (`OK`|`PARSE_ERROR`|
`COMPUTE_FAILED`), `meta` (`engine=sympy`, `sympy_version`, `elapsed_ms`).

**Honesty:** if SymPy cannot solve in closed form (e.g. `∫ exp(x**2) dx`) it does
not hide the result; it returns the unevaluated/special-function exact expression
(like `erfi(...)`).

---

## Inequality proof & nonlinear (Z3 NRA)

**Proves** polynomial inequalities via Z3's nonlinear real arithmetic (NRA /
nlsat) decision procedure, or gives a counterexample. Method: is `∀x. P(x)` →
`¬P(x)` UNSAT (proof by refutation). Here **nonlinear** input is allowed: `Real`
variables, `+ - * / **` (exponent = non-negative integer), `< <= > >= == !=`,
`and`/`or`/`not(...)`/`implies`/`iff`.

| Tool | Signature | Example |
|---|---|---|
| `prove_inequality` | `prove_inequality(goal, assumptions=None)` | `x**2 + y**2 >= 2*x*y` → `valid` |
| `prove_nonnegative` | `prove_nonnegative(expression, assumptions=None)` | `x**2 - 2*x + 1` → `valid` |
| `find_real_solution` | `find_real_solution(constraints)` | `["x**2+y**2==1","x==y"]` → `sat` |

Returns `ReasoningResult`: `prove_*` → `valid` (true everywhere) / `invalid`
(`witness` counterexample) / `unknown`. `find_real_solution` → `sat` (`witness` a
concrete point) / `unsat` / `unknown`. **Honesty:** NRA is decidable in theory but
Z3 may return `unknown`/timeout on a hard instance — reported first-class; if the
goal is not a comparison or the exponent is a variable (nonpolynomial),
`GUARDRAIL_VIOLATION`.

---

## Verification layer (AI reasoning auditor) — the direction that pulls ahead

The layer that turns MathHead from "just another CAS" into **a judge of AI
reasoning**. The AI presents a CLAIM; MathHead audits it independently and gives a
counterexample/warning.

| Tool | Signature | Example |
|---|---|---|
| `verify_equality` | `verify_equality(left, right)` | `(x**2-1)/(x-1)` vs `x+1` → `EQUAL_ON_COMMON_DOMAIN` (x=1 warning) |
| `verify_solution` | `verify_solution(equation, symbol, claimed)` | `x**2==4`, `x`, `["2"]` → `SOLUTION_INCOMPLETE` (-2 missed) |
| `verify_steps` | `verify_steps(steps)` | `["(x+1)**2","x**2+1"]` → `STEP_INVALID` (1st transition) |
| `cross_check` | `cross_check(left, right)` | `(x**2-1)/(x-1)` vs `x+1` → `ENGINES_DISAGREE` (domain!) |
| `verify_derivative` | `verify_derivative(expression, symbol, claimed, order=1)` | `x**3`,`x`,`3*x**2` → `EQUAL` |
| `verify_integral` | `verify_integral(expression, symbol, claimed)` | `2*x`,`x`,`x**2+5` → `EQUAL` (+C tolerated) |
| `verify_limit` | `verify_limit(expression, symbol, point, claimed)` | `sin(x)/x`,`x`,`0`,`1` → `EQUAL` |
| `verify_series` | `verify_series(expression, symbol, point, order, claimed)` | `exp(x)`,`x`,`0`,`3`,`x**2/2+x+1` → `EQUAL` |
| `verify_matrix_identity` | `verify_matrix_identity(left, right)` | `[[a+a]]` vs `[[2*a]]` → `EQUAL` (symbolic) |
| `check_certificate` | `check_certificate(certificate)` | `{kind:"subset_sum",...}` → `verified`/`refuted` (INDEPENDENT) |
| `interpret_natural` | `interpret_natural(text)` | `"the derivative of x**3 with respect to x"` → `UNDERSTOOD` + restatement |

**Why it pulls ahead (what a naive check misses):**

- `verify_equality` catches not only equivalence but also **domain divergence**:
  `(x²-1)/(x-1)` and `x+1` look symbolically equivalent but are undefined at
  `x=1` → `EQUAL_ON_COMMON_DOMAIN` + `details.domain_caveat`. On invalid, a
  concrete counterexample.
- `verify_solution` checks the values by substitution **and checks COMPLETENESS** —
  a missing root (`SOLUTION_INCOMPLETE` + `details.missing`) or a wrong root
  (`SOLUTION_INCORRECT` + `details.wrong_values`). If completeness cannot be
  verified in closed form, `COMPLETENESS_UNKNOWN` (honest).
- `verify_steps` "grades" a solution step by step: it gives the first broken
  transition (`details.first_bad_step`, 1-based) + a counterexample.
- `cross_check` verifies an equivalence claim with **two INDEPENDENT engines**
  (Z3 + SymPy): `CONSENSUS_EQUAL`/`_NOT_EQUAL` (agreement, high confidence),
  `ENGINES_DISAGREE` (conflict → subtle-case/domain flag), `SINGLE_ENGINE`
  (only one decided, e.g. only SymPy on transcendentals). The agreement of two
  independent witnesses is a confidence signal single-engine rivals cannot give.
- `verify_derivative`/`verify_integral`/`verify_limit`/`verify_series`/
  `verify_matrix_identity` independently audit the AI's calculus/matrix claims
  (claim ≟ independently computed correct value → `EQUAL`/`NOT_EQUAL`/`UNDECIDED`,
  `details.correct` gives the correct value). `verify_integral` uses a
  **differentiate-and-compare** method to honestly tolerate the +C constant
  difference.
- `interpret_natural` translates natural language (TR+EN) into a formal task but
  **RECOGNIZE-OR-REFUSE**: on unrecognized/ambiguous input it does not guess
  (`UNRECOGNIZED`/`AMBIGUOUS`). When it understands, it **restates in NL what it
  understood** via `interpretation.restatement` — the caller confirms before
  trusting (an antidote to the "2nd wall"). The returned `task`+`payload` is then
  passed to the relevant formal tool.
- `check_certificate` re-verifies a result **INDEPENDENTLY** of the engine that
  produced it (Z3/SymPy), using only the Python **stdlib** (`ast`+`fractions`,
  exact arithmetic where possible): `verified`/`refuted`. "Don't trust us, run the
  checker." Kinds: `subset_sum`, `graph_coloring`, `solution`, `not_equal`,
  `inequality_counterexample`. The module **does not actually import** z3/sympy
  (proven by a subprocess test). On transcendentals, numeric (float+tolerance,
  `exact:false`).

Returns `VerifyResult`: `status` (valid|invalid|unknown|error) + `reason_code` +
`explanation` + `details` (counterexample/missing/first-bad-step) + `meta`.

---

## Track B tools (frontier — SAT reduction)

Solves hard problems by **reducing them to satisfiability** / proves
impossibility. Input is programmatic (a number `n`); output is the common
`ReasoningResult`.

| Tool | Signature | Result |
|---|---|---|
| `pythagorean_coloring` | `pythagorean_coloring(n)` | `sat` (coloring) / `unsat` (impossible) |
| `pigeonhole` | `pigeonhole(n)` | `unsat` = pigeonhole principle proof |
| `van_der_waerden` | `van_der_waerden(n, k, colors=2)` | `unsat` = n ≥ W(colors,k) (proof) |
| `schur_number` | `schur_number(n, colors)` | `unsat` = n > S(colors) (proof) |
| `graph_coloring` | `graph_coloring(edges, colors, n=None)` | `sat` (coloring, verified) / `unsat` (chromatic number > colors) |
| `subset_sum` | `subset_sum(numbers, target)` | `sat` (subset, verified) / `unsat` (none) |

The results the engine actually proves/reproduces (an honest log, known vs open
distinction): `docs/track-b-results.md`.

**Honesty:** Small instances are not the famous results *themselves* but **the
same method** (the Boolean Pythagorean n=7825 bound is a ~200 TB proof; here small
n solves instantly). Large scale returns `unknown`/`error` — not hidden.

**Verifiable certificate:** when `graph_coloring`/`subset_sum` return `sat`, the
witness IS A CERTIFICATE and is re-checked in pure Python **independently** of Z3
→ `meta.verified: true` (caught even if there is an encoding error). **Honest
asymmetry:** producing an independently-checkable **DRAT/LRAT** certificate for
`unsat` requires a DIMACS-level SAT pipeline — this is documented explicitly as a
**wall** (the output gives `unsat` and notes it); details in
`docs/track-b-results.md`.
