# MathHead — Todo

> **This file's job:** what to do RIGHT NOW and the priorities. Changes constantly.
> The target architecture stays fixed in `Plan.md`.
>
> Markers: `[ ]` open · `[~]` in progress · `[x]` done

---

## Active goal: **v1 — Reasoning Checker** → CORE DONE ✅

### P0 — Foundation (core)

- [x] **T1** `guardrails`: `validate_input` + `solver_config` (fixed seed + timeout)
- [x] **T2** `translate`: Python `ast` → Z3, sort inference, linearity fence
- [x] **T3** `check_entailment` (¬conclusion UNSAT + counterexample)
- [x] **T4** `check_consistency` (sat/unsat + `unsat core`)
- [x] **T5** `find_model`

### P1 — End to end

- [x] **T6** `router.route` (3 primitives) + `server → router`
- [x] **T7** tests: best/worst + **determinism (×50)** + guardrail → **17/17 green**
- [x] **T8** real MCP client: **live stdio integration test** added
  (`tests/test_mcp_live.py` — subprocess + JSON-RPC end to end) ✅ (Phase 11)

### P2 — Polish / next

- [ ] **T9** enrich the `explanation` (embed the counterexample into the sentence on invalid)
- [ ] **T10** golden scenarios (`tests/fixtures/*.json`)
- [x] **T11** v1.1: Real numbers + `∀`/`∃` quantifiers ✅
- [x] **T12** v2: `compute/` (SymPy) — solve / simplify / derivative-integral ✅
- [x] **T13** v2+: calculus & systems — limit / series / solve_system ✅
- [x] **T14** v2+: linear algebra (matrix) — determinant / eigenvalue / inverse / rank ✅
- [x] **T15** v2+: linear algebra II — matmul / Ax=b / eigenvector / rref / nullspace / LU ✅
      (ROADMAP Phase 1 · 161 tests · 30 tools)
- [x] **T16** ROADMAP Phase 2 [S]: determinism + property (det/Ax=b/simplify) + fuzz ✅ (169 tests)
- [x] **T17** ROADMAP Phase 3: number theory ✅ (187 tests, 37 tools)
- [x] **T18** ROADMAP Phase 4: combinatorics & discrete ✅ (205 tests, 42 tools, Fibonacci→Binet)
- [x] **T19** ROADMAP Phase 5 [S]: taxonomy + golden fixtures + benchmark ✅ (242 tests)
- [x] **T20** ROADMAP Phase 6: multivariable analysis ✅ (258 tests, 49 tools, ODE included)
- [x] **T21** ROADMAP Phase 7: probability & statistics ✅ (273 tests, 54 tools, 7 distributions)
- [x] **T22** ROADMAP Phase 8 [S]: coverage 87% + benchmark fence + auto API ref ✅ (330 tests)
- [x] **T23** ROADMAP Phase 9: inequality proof (Z3 NRA) ✅ (345 tests, 57 tools, AM-GM proof)
- [x] **T24** ROADMAP Phase 10: Track B + verifiable certificate ✅ (357 tests, 59 tools)
- [x] **T25** ROADMAP Phase 11 [S]: live MCP test + contract check + version 0.2.0 (RC) ✅ (417 tests)

### 🎉 ROADMAP Phases 1–11 DONE — engine 24→59 tools, 146→417 tests, 87% coverage

### Track C — differentiating direction (verification layer)

- [x] **C1** core verifier: verify_equality/solution/steps ✅ (438 tests, 62 tools)
- [x] **C2** independent certificate (stdlib checker, without z3/sympy — proven) ✅
- [x] **C3** cross-check (Z3 ⋈ SymPy) ✅ (447 tests, 63 tools, +determinism fix ADR-0020)
- [x] **C4** benchmark (LLM-trap set, 100% catch + regression fence) ✅

### 🎉 TRACK C DONE — verification layer (64 tools, 477 tests). MathHead = the judge of AI.

### D–K roadmap APPROVED (a: all of it, suggested order I→D→E→F→G→H→J→K). Quality>speed.

- [x] **I1** new verification types (derivative/integral/limit/series/matrix) ✅ (505 tests, 69 tools)
- [x] **I2** natural language → formal + round-trip ✅ (523 tests, 70 tools, recognize-or-reject)
- [x] **Repo language → English** ✅ (docstrings/comments/user-strings/docs/data prose;
      Anglicized output keys; bilingual TR+EN NL *input* kept as a feature) — 523/523 green
- [x] **I3** full derivation proof check (verify_derivation — operation-replay justification) ✅ (542 tests, 71 tools)
- [x] **I4** certificate extension — 8 new stdlib kinds (matrix/number-theory/probability) ✅ (553 tests)
- [x] **I5** [S] hardening — property/determinism/fuzz across the I-track ✅ (564 tests)

### 🎉 TRACK I DONE — Verification Layer II (71 tools, 564 tests). Next: **D → E → F → G → H → J → K**.

- [x] **D1** vector calculus — divergence/curl/laplacian/directional_derivative/line_integral ✅ (591 tests, 76 tools, +π/e)
- [x] **D2** integral transforms — Laplace/Fourier/Z (+inverses) ✅ (614 tests, 81 tools)
- [x] **D3** diff-eq II — ode_system/ode_ivp(IVP+BVP)/classify_ode/solve_pde ✅ (635 tests, 85 tools)
- [ ] **D4** complex analysis · **D5** [S]
- [ ] then: E → F → G → H → J → K (full list in ROADMAP)

**Productization (on the user, no rush):** PyPI (0.2.0), release, tutorial.

---

## Finished in this session

- [x] v0: skeleton + design files
- [x] v1 core **works** (real Z3): 3 primitives, unsat core, counterexample, meta
- [x] MCP end to end (3 tools registered, clean JSON), 17/17 tests green
- [x] Repo on GitHub; CI (Actions) set up
- [x] **v1.1**: quantifiers (∀/∃) + Real → 25/25 tests green
- [x] **v2**: compute layer (SymPy) — solve/simplify/derivative/integral → 37/37 tests green
- [x] **Track B seed**: problem→SAT reduction (Pythagorean + pigeonhole) → 42/42 green
- [x] **v1.2**: predicates + individuals (classical syllogism works) → 51/51 green
- [x] **CLI**: `mathhead` terminal tool (11 commands + --json)
- [x] **v3 proof generation** (step-by-step ND: MP/MT/DS/∀/∃/RAA) + **model enumeration** → 84/84
- [x] **optimization** (Z3 Optimize / MaxSMT): optimize an objective under constraints → 90/90
- [x] **MaxSAT** (soft/weighted constraints): satisfy the most soft constraints → 96/96
- [x] **hardening**: property-based tests (hypothesis) + determinism made precise → 103/103
- [x] **equivalence & classification** (equivalent / classify): tautology/contradiction/contingent → 110/110
- [x] **calculus & systems** (limit / series / solve_system): one-sided + infinite point,
  Taylor, multivariable system (linear+nonlinear, honest empty solution) → **128/128**, MCP **20 tools**
- [x] **linear algebra (matrix)** (determinant / inverse / eigenvalues / rank): symbolic cells,
  honest error on singular matrix, complex eigenvalue + multiplicity → **146/146**, MCP **24 tools**
- [x] **Track B / van der Waerden**: W(2,3..5) known values reproduced (honest) → 61/61
- [x] **Track B / Schur**: S(2)=4, S(3)=13 reproduced; S(4)≥44 (honest wall) → 65/65
- [x] **v3 / proof generation**: minimal core + natural deduction (syllogism step by step) → 72/72
