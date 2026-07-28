# Changelog

All notable changes are kept here. Versioning follows [SemVer](https://semver.org/lang/tr/).

## [Unreleased]

### Added

- **Frontier reductions II (`n_queens`, `latin_square`, `sudoku_solve`, `hamiltonian_path`,
  `ramsey_coloring`, `tsp_decision`):** ROADMAP J1 — Track J begins. Six classic
  NP-complete/combinatorial reductions to Z3, each `sat` witness INDEPENDENTLY re-verified in
  pure Python (`meta.verified`). Reproduces known results (8-queens; unsat at n=2,3;
  **R(3,3)=6**; Hamiltonian path-but-no-cycle; decision-TSP via MTZ subtour elimination). MCP
  (**161 tools**) + CLI (`queens`/`latin`/`sudoku`/`hamilton`/`ramsey`/`tsp`) + 17 tests.
  ADR-0026. **1093 tests green.**
- **Track H hardening (`tests/test_h_track_hardening.py`, 16):** ROADMAP H5 — **TRACK H
  DONE**. Theorems as properties (proved induction theorems verified numerically to n=100k;
  BV identities incl. De Morgan checked on random values; EUF/array/string axioms; the QE
  divisibility correspondence) + INDEPENDENT modal countermodel verification (each Kripke
  countermodel re-checked by a pure-Python semantics, engine-independent) + modal duality +
  determinism. Tests only. **1064 tests green.** Track H (H1–H5): induction, SMT theories,
  quantifier elimination, modal logic — 149→155 tools.
- **Modal logic (`check_modal`):** ROADMAP H4. Propositional modal-logic validity in the
  normal systems K/T/D/B/S4/S5 by bounded Kripke model checking (`box`=□, `dia`=◇). New
  `core/modal.py`. A countermodel is a definitive refutation (`invalid`, with the frame +
  valuation as witness); a positive result is `VALID_BOUNDED` (no countermodel up to W
  worlds — honest about the bound). The classic correspondence theorems come out exactly
  right (T↔reflexive, 4↔transitive, 5↔S5). MCP (**155 tools**) + CLI (`modal`) + 12 tests.
  ADR-0025. **1048 tests green.** (Temporal/LTL deferred — careful scope.)
- **Quantifier elimination (`eliminate_quantifiers`):** ROADMAP H3 (proof depth II). Z3
  `qe` over Presburger arithmetic turns a quantified linear formula into an equivalent
  quantifier-free one, doubling as a decision procedure for quantified LIA/LRA
  (`exists(y, x == 2*y)` → `x % 2 == 0`; `exists(x, 0 < x and x < 1)` → `False`;
  `forall(x, x > 5 → x > 3)` → `True`). New `core/qe.py`; honest `QE_INCOMPLETE` when a
  residual quantifier remains. MCP (**154 tools**) + CLI (`qe`) + 9 tests. ADR-0024.
  **1034 tests green.**
- **SMT theories — bit-vectors, EUF, arrays, strings (`check_bitvector`,
  `check_uninterpreted`, `check_arrays`, `check_strings`):** ROADMAP H2. Four more of Z3's
  decision theories, each with the kernel's shape `check_<theory>(assumptions, goal=None)`
  (goal → entailment + counterexample; goal=None → consistency). New `core/smt.py`. BV bit
  tricks / masks / overflow with bit-level counterexamples; EUF congruence (`a==b ⊨
  f(a)==f(b)`); array McCarthy axioms (`select`/`store`); string
  concat/length/contains/prefix/suffix. MCP (**153 tools**) + CLI
  (`bitvector`/`uf`/`arrays`/`strings`) + 24 tests. ADR-0023. **1023 tests green.**
- **Mathematical induction (`prove_by_induction`):** ROADMAP H1 — Track H begins. Proves
  `∀ n ≥ start. P(n)` by induction, something Z3 CANNOT do natively (the induction schema
  is not first-order SMT). New `core/induction.py` checks the base case P(start) and the
  inductive step P(k)→P(k+1) with Z3 and applies the induction principle as a SOUND
  meta-rule. Single-variable nonlinear-int grammar (`+ - * ** % //`). Honest walls:
  base-fail → `invalid` (counterexample at start), step-fail → `unknown` (`STEP_FAILED`,
  inconclusive), hard nonlinear step → `unknown` (`SOLVER_UNKNOWN`) — never a fabricated
  proof. MCP (**149 tools**) + CLI (`induction`) + 14 tests. ADR-0022. **990 tests green.**
- **Natural language → formal (`interpret_natural`):** ROADMAP I2 — antidote to "wall #2"
  (over-assumption). Rule-based, bilingual (TR+EN), **RECOGNIZE-OR-REJECT**: does not guess on
  unrecognized/ambiguous input (`UNRECOGNIZED`/`AMBIGUOUS`). When it understands, it
  restates in NL what was understood via a **round-trip restatement** (confirm-then-trust).
  Recognized: derivative/integral/limit/solving/factorization/primality/GCD/equivalence.
  New `core/nl.py`. MCP (**70 tools**) + CLI (`interpret`) + 18 tests. 3 new reason_code.
- **Verification layer II — calculus & matrix claims (`verify_derivative`,
  `verify_integral`, `verify_limit`, `verify_series`, `verify_matrix_identity`):**
  ROADMAP I1. Independently checks AI's derivative/integral/limit/Taylor-series/matrix-identity
  claims (claim ≟ the computed correct one). `verify_integral` honestly tolerates the
  **+C constant difference** via a differentiate-and-compare method; on a wrong claim
  `details.correct` gives the correct value. MCP (**69 tools**) + CLI + 20 tests.
- **LLM-trap benchmark (Track C4):** `benchmarks/llm_traps.json` (14 classic LLM
  error patterns: missing/wrong solution, wrong identity, domain trap, wrong
  inequality, root branch, faulty step, primality, arithmetic, modular, Diophantine) +
  `benchmarks/run.py` harness + `tests/test_benchmark_traps.py` regression fence +
  `docs/benchmark-results.md`. **Catch rate 100%** (including the true-positive control
  — it does not mis-flag a correct answer). Honest framing: a reproducible
  demonstration, not a live LLM A/B.
- **Independent certificate checker (`check_certificate`):** ROADMAP Track C2.
  Re-verifies a result **INDEPENDENTLY** of the engine that PRODUCED it (Z3/SymPy), using
  only the Python stdlib (`ast`+`fractions`, exact arithmetic when possible) →
  `verified`/`refuted`. The new `mathhead/certificate.py` **actually does not import
  z3/sympy** (proven by a subprocess test — "don't trust us, run the checker"). Kinds:
  `subset_sum`, `graph_coloring`, `solution`, `not_equal`, `inequality_counterexample`.
  MCP (**64 tools**) + CLI (`check-certificate`) + 13 tests. New status:
  `verified`/`refuted` (added to the taxonomy).
- **Cross-check — Z3 ⋈ SymPy (`cross_check`):** ROADMAP Track C3. Verifies an equivalence
  claim with **two independent engines**; consensus required. `CONSENSUS_EQUAL/
  _NOT_EQUAL` (high confidence), `ENGINES_DISAGREE` (conflict → domain/subtle-issue
  flag — e.g. `(x²-1)/(x-1)` vs `x+1`), `SINGLE_ENGINE` (only one, e.g.
  SymPy for transcendentals). MCP (**63 tools**) + CLI (`cross-check`) + 7 tests.
- **Verification layer — AI reasoning auditor (`verify_equality`,
  `verify_solution`, `verify_steps`):** ROADMAP Track C1 — the "differentiating direction".
  Turns MathHead from "just another CAS" into an **independent judge of AI claims**.
  `verify_equality` catches equivalence **and domain divergence** (domain trap,
  `(x²-1)/(x-1)` vs `x+1` → x=1 warning); `verify_solution` checks correctness **and
  COMPLETENESS** (missing/wrong roots); `verify_steps` finds the first error in the step
  chain. New module `core/verify.py` + `VerifyResult`. MCP (**62 tools**) + CLI
  (`verify-eq/verify-solution/verify-steps`) + 15 tests. 10 new reason_code
  (added to the taxonomy).

## [0.2.0] — 2026-07-28

A big expansion of the engine: **24 → 59 MCP tools**, **146 → 357 tests**, coverage
**87%**. Phases 1–11 of the phased roadmap (`ROADMAP.md`) completed —
linear algebra, number theory, combinatorics, multivariable analysis, probability &
statistics, inequality proof (Z3 NRA) and an extended Track B; with three
hardening rounds in between (property/fuzz, taxonomy/golden, coverage/API-ref).

### Added

- **Track B extension + verifiable certificate (`graph_coloring`, `subset_sum`):**
  Phase 10. Two new NP-complete reductions (graph k-coloring, subset sum). **Positive
  certificate:** the `sat` witness is re-checked in pure Python, **independent** of Z3
  → `meta.verified=true` (caught even if there is an encoding bug). **Honest asymmetry:**
  an independent DRAT/LRAT certificate for `unsat` is explicitly documented as a WALL
  (`docs/track-b-results.md`). MCP (**59 tools**) + CLI (`graph-coloring/subset-sum`).
- **Inequality proof & nonlinear (`prove_inequality`, `prove_nonnegative`,
  `find_real_solution`):** Phase 9. **Proves** polynomial inequalities with Z3 nonlinear
  real arithmetic (NRA / nlsat) (proof-by-refutation: is `¬P` UNSAT) or gives a
  counterexample; finds real solutions to nonlinear constraints. AM-GM
  (`x²+y²≥2xy`), completing-the-square, etc. are proven. **Honesty:** `unknown`
  is first-class; a non-polynomial exponent / non-bool target is rejected. New module
  `core/inequality.py` (nonlinear Z3 translator). MCP (**57 tools**) + CLI
  (`prove-inequality/prove-nonnegative/real-solve`). +15 tests.
- **Probability & statistics (`mean`, `variance`, `standard_deviation`, `median`,
  `distribution`):** Phase 7. Descriptive statistics (exact/rational) + 7 named
  distributions via `sympy.stats` (`normal/binomial/poisson/exponential/uniform/
  bernoulli/geometric`): E[X]/Var/std (symbolic/exact) + `P(X≤k)`/density. MCP
  (**54 tools**) + CLI (`mean/variance/std/median/distribution`). +15 tests.
- **Multivariable analysis (`gradient`, `jacobian`, `hessian`, `definite_integral`,
  `summation`, `product`, `solve_ode`):** Phase 6. Gradient/Jacobian/Hessian,
  definite integral (including infinite bounds), sum/product (Σ/Π, closed form:
  `Σi = n²/2+n/2`) and **ODE solving** (`dsolve`; `y'`/`y''` or `D(y,k)`
  notation, safe parser). An honest error on an unsolvable ODE. MCP
  (**49 tools**) + CLI (`gradient/jacobian/hessian/defint/sum/product/ode`). +16 tests.
- **Combinatorics & discrete (`permutations`, `combinations`, `factorial`,
  `partition_count`, `solve_recurrence`):** Phase 4. Permutation/combination,
  factorial, integer partition count and **linear recurrence closed-form
  solution** (`rsolve` — Fibonacci → Binet). `solve_recurrence` reads the recurrence with a
  safe mini-parser (`=`/`==`, non-whitelisted names rejected); an honest error on a
  nonlinear relation. MCP (**42 tools**) + CLI (`perm/comb/factorial/
  partitions/recurrence`). +18 tests.
- **Number theory (`gcd`, `lcm`, `is_prime`, `factorize`, `modular_inverse`,
  `chinese_remainder`, `linear_diophantine`):** Phase 3. GCD/LCM over integers,
  deterministic primality, prime factorization, modular inverse, Chinese Remainder Theorem
  (CRT), linear Diophantine. **Honesty:** an error if the modular inverse doesn't exist / CRT
  is incompatible; an empty list if Diophantine has no integer solution. MCP (**37 tools**) + CLI
  (`gcd/lcm/isprime/factorize/modinv/crt/diophantine`). +18 tests.
- **Linear algebra II (`matrix_multiply`, `matrix_solve`, `eigenvectors`, `rref`,
  `nullspace`, `lu_decomposition`):** Phase 1 — linear algebra completed. `Ax=b`
  in matrix form (inconsistent → empty, infinite → parametric, honest); matrix multiplication
  (dimension-checked); eigenvector; RREF + pivots; null space (kernel) basis; LU
  decomposition. MCP (**30 tools**) + CLI (`matmul/matsolve/eigenvectors/rref/
  nullspace/lu`). +15 tests (`tests/test_linalg.py`).
- **Linear algebra / matrix (`determinant`, `matrix_inverse`, `eigenvalues`,
  `matrix_rank`):** over SymPy `Matrix`. Input `list[list[str]]` (cells can be
  symbolic → `det[[a,b],[c,d]] = a*d - b*c`). **Honesty:** no fabricated inverse for a
  singular matrix, `COMPUTE_FAILED`; eigenvalues give complex/irrational values in exact
  form + algebraic multiplicity (sorted → deterministic). MCP tools (**24 tools**) + `mathhead det/inverse/eigenvals/
  rank` CLI (`"1,2;3,4"` string). +18 tests (`tests/test_matrix.py`).
- **Calculus & systems (`limit`, `series`, `solve_system`):** the compute layer
  (SymPy) expanded. `limit` — finite/infinite point + one-sided (`+`/`-`);
  `series` — Taylor expansion around a point (to `order`-th order); `solve_system`
  — multivariable equation system (linear + nonlinear). **Honesty:**
  `solve_system` doesn't hide "no solution" by returning an empty list, and shows a free variable
  parametrically. MCP tools (**20 tools**) + `mathhead limit/series/
  solve-system` CLI. +18 tests (`tests/test_calculus.py`).
- **Proof generation (`prove`):** the *why* behind entailment — a minimal premise core
  (unsat core) + step-by-step **natural deduction**: modus ponens/tollens, disjunctive
  syllogism, ∧-elimination, iff, double negation, De Morgan, universal instantiation,
  **existential elimination/introduction (∃)**; and proof by cases via **proof by contradiction (RAA)**.
  Syllogism, ∃-inference and proof-by-cases step by step. MCP tool
  `prove` (12 tools) + `mathhead prove` CLI.
- **Model enumeration (`enumerate_models`):** returns all/multiple distinct models
  satisfying a formula (all-SAT, blocking clause); with the `exhaustive` flag it honestly
  states "all of them, or a limit". MCP tool (13 tools) + `mathhead
  enumerate` CLI.
- **Optimization (`optimize`):** finds the solution that maximizes/minimizes a numeric
  objective under constraints (Z3 Optimize / MaxSMT). `unbounded` / `unsat` /
  open-bound are reported honestly. MCP tool (14 tools) + `mathhead optimize` CLI.
- **MaxSAT (`max_satisfy`):** satisfies the mandatory (hard) constraints and the most
  (weighted) soft constraints — a resolution for over-constrained / conflicting requests. MCP
  tool (15 tools) + `mathhead maxsat` CLI.
- **Equivalence & classification (`equivalent`, `classify`):** are two expressions logically
  equivalent (A ≡ B); is a formula a tautology / contradiction / contingent. MCP (17 tools) +
  `mathhead equiv` / `mathhead classify` CLI.

### Changed / hardening

- **Determinism fix (ADR-0020):** the equivalence decision was purged of SymPy `.equals()`
  — it did internal random sampling (`sqrt(x²)` vs `x` varied between
  calls). A shared deterministic helper `verify._equal_verdict`
  (simplify + fixed-point counterexample); shared by `verify_equality`/`verify_steps`/
  `cross_check`. The verdict is now stable **and** stronger (with a counterexample).
- **Hardening-3 (ROADMAP Phase 8):** (1) **Coverage** — `pytest-cov`
  + `[tool.coverage]`; MCP layer test (`tests/test_mcp_layer.py`, calls 54 tools end
  to end + keeps them in sync with the registry) → coverage 85%→**87%** (mcp_server 67%→97%).
  (2) **Auto API reference** — `scripts/gen_api_reference.py` generates
  `docs/api-reference.md` from the MCP-registered tools; `tests/test_api_reference.py` enforces
  that it stays current. (3) **Benchmark regression fence** — a generous (10 s) upper-bound
  test for catastrophic slowdown.
- **Hardening-2 (ROADMAP Phase 5):** (1) **Error taxonomy** consolidated
  → `docs/error-taxonomy.md` (the canonical list of all `status`/`reason_code`) +
  `tests/test_taxonomy.py` enforces it (breaks if an undocumented code leaks). (2) **Golden
  fixtures** → `tests/fixtures/golden.json` (32 known input→output pairs) +
  `tests/test_golden.py` (regression fence). (3) **Benchmark skeleton** →
  `scripts/benchmark.py` (baseline; no time threshold) + a smoke test.
- **Hardening-1 (ROADMAP Phase 2) — compute layer property tests:**
  `tests/test_compute_properties.py`. Cross-checking mathematical invariants:
  `det(A·B)=det(A)·det(B)`, `det(Aᵀ)=det(A)`, `Ax=b` roundtrip (b=Ax → recover x),
  `simplify` idempotent. **Parser fuzz** (security): no crash on random/malicious text and
  malformed matrices, only `ok|error`. Determinism check
  (det/rank/eigenvalue/simplify) stable across 3 seeds.
- **Property-based tests (`hypothesis`):** invariants over random formulas
  (no crash, tools consistent, deriver sound). A test caught a weakness →
  **the determinism guarantee was made precise**: the *verdict* is deterministic, the *witness* is one
  valid example (can vary when there are multiple solutions) — ADR-0019.

## [0.1.0] — 2026-07-28

The first publishable release. A **deterministic**, first-order-logic-based math
reasoning, compute, and reduction engine that AI can use over **MCP**.

### Added

- **Logic core (Z3):** `entailment` / `consistency` / `find_model`;
  propositional logic + linear arithmetic + quantifiers (`∀`/`∃`) + Real
  numbers + uninterpreted predicates (`Man(x)`) → the classical syllogism works.
- **Compute layer (SymPy):** `simplify` / `solve` / `differentiate` / `integrate`.
- **Track B (SAT reduction):** pigeonhole, Boolean Pythagorean, van der
  Waerden (W(2,3..5) reproduced), Schur (S(2..3) reproduced).
  Detail: `docs/track-b-results.md`.
- **Interfaces:** MCP server (**11 tools**) + the `mathhead` command-line tool (`--json`).
- Determinism (fixed seed + timeout), guardrails, `unknown`/`error`
  as first-class output (honesty). **66 automated tests**, CI (GitHub Actions).

### Principles

Against context loss, over-assumption, and non-determinism: explicit principles
(`PRINCIPLES.md`), a decision log (`DECISIONS.md`, 13 ADRs), a progress log
(`Progress.md`), and a clear protocol (`docs/mcp-api.md`).
