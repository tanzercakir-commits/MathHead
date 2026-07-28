# MathHead — Roadmap (Phased)

> **This file's job:** The PHASE-BY-PHASE plan of progress. The user says "continue
> up to this phase"; the agent advances sequentially and autonomously up to it.
> Current fine-grained tasks are in `Todo.md`; what's been done is in `Progress.md`;
> the target architecture is in `Plan.md`. This file = the **order + milestones** view.

---

## Working protocol (mode)

- The user names a **target phase**: e.g. *"Continue up to Phase 5."*
- The agent proceeds sequentially **from 1 to the target**; it finishes each phase independently.
- **DONE criteria for every phase (immutable):**
  1. All tests green (`pytest` — verification gate / test-gated)
  2. `commit` + `push` (a separate commit per phase → clean state if interrupted)
  3. Docs up to date (`mcp-api.md` / `README` / `CHANGELOG`)
  4. `Progress.md` + `Todo.md` updated; the **honest wall**, if any, written down
- **Stops** at the target and gives a batch summary. If an irreversible decision comes
  up mid-way (e.g. breaking the external contract), it stops and asks. Otherwise it doesn't stop.
- Phases **can be reordered / skipped** — this is a plan, not a contract.

Status marker: `[ ]` pending · `[~]` in progress · `[x]` done · `[S]` = hardening

---

## A. Engine development (engineering — on the agent)

```
[x] Phase 0 · EXISTING CORE  (done — 146 tests, 24 MCP tools)
    ├─ Logic (Z3):   entailment/consistency/model/prove/equivalent/
    │                classify/enumerate/optimize/maxsat
    ├─ Compute (SymPy): simplify/solve/diff/integrate · limit/series/
    │                solve_system · det/inverse/eigenvalues/rank
    └─ Track B (SAT reduction): pigeonhole/pythagorean/vdW/Schur

[x] Phase 1 · Complete linear algebra  (done — 161 tests, 30 tools)
    └─ matrix multiplication, Ax=b (matrix form), eigenvector,
       rref/null space (nullspace), LU decomposition
       ↳ honest wall: report singular/inconsistent systems explicitly ✅

[x] Phase 2 · [S] Hardening-1  (done — 169 tests)
    └─ `compute` determinism check + property tests (hypothesis: det multiplicative/
       transpose, Ax=b roundtrip, simplify idempotent) + parser fuzz ✅

[x] Phase 3 · Number theory  (done — 187 tests, 37 tools)
    └─ gcd/lcm, primality test (isprime), factorization (factorint),
       modular inverse + CRT (Chinese Remainder Theorem), linear Diophantine ✅
       ↳ honest: no inverse / CRT incompatible → error; Diophantine unsolvable → empty

[x] Phase 4 · Combinatorics & discrete  (done — 205 tests, 42 tools)
    └─ permutation/combination, binomial, partition,
       recurrence relation closed-form solution ✅ (Fibonacci→Binet)

[x] Phase 5 · [S] Hardening-2  (done — 242 tests)
    └─ error taxonomy (docs/error-taxonomy.md + test_taxonomy) +
       golden scenarios (fixtures/golden.json, 32) + benchmark skeleton ✅

[x] Phase 6 · Multivariable analysis  (done — 258 tests, 49 tools)
    └─ gradient, Jacobian, Hessian, definite integral, series sum/product,
       basic ODE (differential equation) solving ✅
       ↳ honest: unsolvable ODE → COMPUTE_FAILED (no fabrication)

[x] Phase 7 · Probability & statistics  (done — 273 tests, 54 tools)
    └─ descriptive (mean/var/std/median) + 7 named distributions (E/Var/std +
       cdf/pmf, symbolic) ✅

[x] Phase 8 · [S] Hardening-3  (done — 330 tests, 87% coverage)
    └─ coverage (pytest-cov + MCP layer test 85%→87%) + benchmark fence +
       auto API reference (docs/api-reference.md, code=docs) ✅

[x] Phase 9 · Inequality proof & nonlinear  (done — 345 tests, 57 tools)
    └─ inequality proof via Z3 nonlinear real (NRA/nlsat) (AM-GM, completing-
       the-square) + real solution finding. core/inequality.py ✅
       ↳ honest wall: NRA is semi-decidable → unknown is first-class ✅
       ↳ note: CAD-based Z3 decision instead of an SOS certificate (stronger/complete)

[x] Phase 10 · Track B extension + certificate  (done — 357 tests, 59 tools)
    └─ new reductions: graph_coloring, subset_sum ✅
       → positive certificate: sat witness is INDEPENDENTLY verified (meta.verified) ✅
       ↳ honest asymmetry: unsat DRAT/LRAT = wall (needs a DIMACS pipeline), documented

[x] Phase 11 · [S] Big hardening (release prep)  (done — 417 tests, v0.2.0)
    └─ LIVE MCP integration test (subprocess+stdio+JSON-RPC) + contract check of all
       tools (59) + version freeze 0.1.0→0.2.0 (RC) ✅
```

**🎉 Phases 1–11 DONE.** Engine: 24→59 MCP tools, 146→417 tests, 87% coverage.
Productization (B) is on the user.

## B. Productization (your evening — separate track)

```
[ ] PyPI publish  ·  GitHub release  ·  example/tutorial notebooks
    (independent of the engine; the user does it — the agent focuses on the engine)
```

## C. Differentiating direction — VERIFICATION LAYER (AI reasoning auditor)

> **Thesis:** We get ahead on **trust**, not raw compute. AI is non-deterministic and
> makes things up; MathHead checks deterministically and gives independently verifiable
> certificates. It turns the product from "just another CAS" into **"the judge of AI reasoning"**.

```
[x] C1 · Core verifier (propose-and-check)  (done — 438 tests, 62 tools)
    └─ verify_equality (equivalence + DOMAIN trap), verify_solution (correctness +
       COMPLETENESS), verify_steps (find the first error in the step chain) ✅
       ↳ honest wall: domain divergence + completeness 'unknown' reported explicitly ✅
[x] C2 · Independent certificate — stdlib checker without Z3/SymPy (mathhead/certificate.py)  ✅
    ↳ independence PROVEN via subprocess; exact arithmetic (Fraction); verified/refuted
[x] C3 · Cross-check — Z3 ⋈ SymPy consensus (two independent witnesses)  (done — 447 tests, 63 tools)
    ↳ domain trap → ENGINES_DISAGREE; + determinism fix (ADR-0020)
[x] C4 · Benchmark — LLM-trap set (14) + 100% catch + regression fence  ✅
    ↳ benchmarks/ + docs/benchmark-results.md; honest: a demonstration, not a live A/B
```

**🎉 TRACK C DONE.** Verification layer: verifier + independent certificate +
cross-check + benchmark. MathHead = the independent judge of AI reasoning.

---

# PROPOSED — ALL ENGINE DEVELOPMENTS (D–K, awaiting approval)

> Activated on user approval; the user sets the order. Except productization (PyPI/
> release) — that's on the user. Difficulty: 🟢 quick (SymPy/Z3 ready) · 🟡 medium ·
> 🔴 hard/frontier. **[S]** = hardening in between.

## D. Analysis & Transforms
```
[x] D1 🟢 Vector calculus — divergence / curl / Laplacian / directional_derivative /
          line_integral ✅ (76 tools; +π/e constants ADR-0021). 🔴 surface integrals &
          Green/Stokes/Gauss theorems deferred (region/surface modeling — larger effort)
[x] D2 🟢 Integral transforms — Laplace & inverse, Fourier & inverse, Z-transform ✅
          (81 tools; honest COMPUTE_FAILED when no closed form; Z closed-form + ROC)
[x] D3 🟡 Differential equations II — solve_ode_system / solve_ode_ivp (IVP+BVP) /
          classify_ode / solve_pde ✅ (85 tools; shared _parse_diffeq; higher-order via solve_ode).
          🔴 general PDE (heat/wave separation) beyond pdsolve → honest COMPUTE_FAILED
[x] D4 🟡 Complex analysis — residue / contour_integral (residue theorem) / laurent_series /
          complex_parts ✅ (89 tools; +I imaginary-unit constant, ADR-0021 extended)
[x] D5 [S] Hardening — analysis identity properties (∇×∇f=0, ∇·(∇×F)=0, ∇²f=∇·∇f via the
          verifier) + numerical cross-check + transform round-trips ✅ (664 tests)
```

### 🎉 TRACK D DONE — Analysis & Transforms (vector calculus, transforms, diff-eq II, complex)

## E. Algebra & Discrete Structures
```
[x] E1 🟡 Abstract algebra — permutation groups: order/parity/compose, named-group order (+abelian),
          generated-group order ✅ (94 tools). 🔴 full ring/field structure theory deferred
[x] E2 🟢 Linear algebra III — singular values, QR, Cholesky, Gram-Schmidt, least squares,
          pseudo-inverse, matrix exp, Jordan form, characteristic polynomial ✅ (103 tools)
[x] E3 🟡 Graph theory — shortest_path, connected_components, MST, max_flow/min-cut,
          maximum_matching, is_isomorphic ✅ (109 tools; PURE STDLIB, deterministic, no networkx)
[x] E4 🟡 Number theory II — euler_totient, mobius, continued_fraction (+√n periodic),
          quadratic_residue, primitive_root, pell_solution ✅ (116 tools)
[x] E5 🟡 Combinatorics II — catalan/bell/stirling, derangements (incl-excl),
          generating_function_coefficient, necklace_count (Burnside/Pólya) ✅ (122 tools)
[ ] E6 [S] Hardening
```

## F. Probability, Statistics & Optimization
```
[ ] F1 🟡 Probability II — conditional & Bayes, joint/marginal distribution, covariance, Markov chain
[ ] F2 🟡 Inferential statistics — hypothesis test (z/t/χ²/ANOVA), confidence interval, p-value, regression
[ ] F3 🟡 Optimization II — linear programming (simplex), integer programming,
          Lagrange multipliers, KKT/convex
[ ] F4 [S] Hardening
```

## G. Numerical Methods
```
[ ] G1 🟢 Root & numerical analysis — Newton/bisection/secant, quadrature (Simpson/Gauss), interpolation
[ ] G2 🟡 Numerical linear algebra & ODE — numerical eigenvalue/solution, condition number, Runge-Kutta (RK4)
[ ] G3 🟡 Precision bridge — arbitrary precision (mpmath), symbolic↔numeric cross-validation, error bound
[ ] G4 [S] Hardening
```

## H. Logic & Proof Depth
```
[ ] H1 🔴 Induction proofs — mathematical induction (base+step; Z3 can't do this natively, special handling)
[ ] H2 🟡 SMT theories — arrays, bit-vectors, strings, uninterpreted functions
[ ] H3 🟡 Proof generation II — step-by-step derivation for more theories; quantifier elimination
[ ] H4 🔴 Modal/temporal logic — K/S4/LTL basics (optional/frontier, careful scope)
[ ] H5 [S] Hardening
```

## I. Verification Layer II (Track C continuation — DIFFERENTIATING)
```
[x] I1 🟢 New claim types — verify_limit / verify_derivative / verify_integral /
          verify_series / verify_matrix_identity ✅ (69 tools; +C constant difference honest)
[x] I2 🔴 Natural language → formal + BACK-translation (round-trip) ✅ (70 tools; RECOGNIZE-OR-REJECT,
          bilingual TR+EN, NO guessing — antidote to "wall #2")
[x] I3 🟡 Full derivation proof check — REPLAY each cited operation, confirm it produces the next line ✅
          (71 tools; equation-aware; DERIVATION_VALID / STEP_UNJUSTIFIED; honest domain caveat)
[x] I4 🟡 Certificate extension (C2 continuation) — matrix / number theory / probability certificates ✅
          (8 new stdlib kinds: matrix_product/inverse, linear_system, factorization, bezout_gcd,
           modular_inverse, chinese_remainder, expectation; engine-independence preserved)
[x] I5 [S] Hardening — property-based + determinism + fuzz across the I-track ✅ (564 tests)
```

### 🎉 TRACK I DONE — Verification Layer II (verify_derivation, I1 claim types, NL, 13 certificate kinds)

## J. Frontier — Track B extension
```
[ ] J1 🟡 New reductions — Ramsey (small), Latin squares, Sudoku, N-queens, Hamilton, TSP (decision)
[ ] J2 🔴 Verifiable UNSAT certificate (DRAT/LRAT) — the Phase 10 wall; DIMACS + drat-trim
[ ] J3 🟡 High-performance solver — CaDiCaL/Kissat integration (scale), parallel solving
[ ] J4 [S] Hardening
```

## K. Holistic Performance & Hardening (cross-cutting, at the end)
```
[ ] K1 🟡 Performance — cache (memoization), incremental solving (Z3 push/pop), parallel, timeout profile
[ ] K2 🟢 Coverage & fuzzing — fuzz all parsers, grammar formal spec, 95% coverage
[ ] K3 🟡 Observability — structured metrics/logs, resource limits, perf regression fence
[ ] K4 🟢 Version 1.0 freeze — full contract check, API stability, release notes
```

**Scale (honest):** ~37 phases. A multi-session effort; approvable piece by piece.
**Suggested order (value-first):** I (differentiating) → D → E → F → G → H → J → K;
but the order is entirely yours. Approval / a different order / narrowing scope — all fine.

---

## Where did we leave off?

The most current status is always at the top of `Progress.md`. A new session reads
it and this file first, then proceeds up to the target phase.
