# MathHead — Decision Log (ADR)

> **This file's job:** to store the decisions that shape the project's direction *with their rationale*.
> A direct antidote to **wall #1** in your working principles (context loss — "dozens of small design
> decisions that never make it into the handover document"). Even a decision that looks small is
> written here; so that 6 months later the answer to "why did we do it this way?" isn't lost.
>
> **Format (ADR = Architecture Decision Record):** each decision has Status, Context,
> Decision, Consequences. Decisions are *not changed*; if the thinking changes, we open a new ADR and
> mark the old one as "superseded".

---

## ADR-0001 — Orchestrating a proven solver instead of a from-scratch FOL engine

- **Status:** Accepted · 2026-07-28
- **Context:** A "first-order-logic-based" engine can be built two ways: (a) writing a resolution/
  unification core from scratch, (b) wrapping a mature solver.
- **Decision:** (b). Writing from scratch is instructive but slow, error-prone, and a heavy
  maintenance burden; mature solvers carry decades of engineering.
- **Consequences:** We gain speed and reliability; we give up the learning value of "we wrote the
  engine's internals ourselves". The solver becomes a dependency (version management is needed).

## ADR-0002 — Logic core = Z3 (SMT), compute = SymPy (CAS)

- **Status:** Accepted · 2026-07-28
- **Context:** There are two different jobs — *reasoning/proof* (is a statement valid) and
  *compute* (solve integrals/equations). No single tool does both well.
- **Decision:** **Z3** for reasoning (FOL + theories, deterministic, powerful).
  **SymPy** for symbolic compute. The two are separate layers, connected by the router.
- **Consequences:** Each job goes to the right tool. It incurs the cost of two dependencies + one
  routing layer; in exchange, the "best tool" is used in each domain. v1 only brings
  Z3 to life; SymPy is deferred to v2.

## ADR-0003 — Language = Python, MCP SDK = FastMCP

- **Status:** Accepted · 2026-07-28
- **Context:** The engine will be exposed to AI over MCP. Ecosystem fit matters.
- **Decision:** **Python** — because the official MCP SDK (`mcp[cli]`, FastMCP), `z3-solver`,
  and `sympy` all have first-class Python support. The server uses the FastMCP `@mcp.tool()`
  pattern and runs locally over the `stdio` transport.
- **Consequences:** The lowest friction, the most mature library chain. Python's runtime
  speed is a cost; but the bottleneck is the solver (C++ Z3), not Python.

## ADR-0004 — External API/contract frozen early

- **Status:** Accepted · 2026-07-28
- **Context:** Non-determinism and context loss do the most harm as *contract drift*
  (a signature changes in one session, the next session is left incompatible).
- **Decision:** The `ReasoningResult` output shape and the MCP tool signatures are frozen in v0.
  The core body is filled in later, but the *external surface* doesn't change. If it must
  change, a new ADR is required.
- **Consequences:** Stability between the skeleton and the MVP; tests and clients can be written
  early. Flexibility decreases somewhat — a deliberate trade-off.

## ADR-0005 — v1 scope = "Reasoning Checker" (narrow vertical slice)

- **Status:** Accepted · 2026-07-28
- **Context:** The vision is broad (forward-looking, the most-needed area) but v1 was
  wanted to be "narrow & solid".
- **Decision:** v1 = three primitives (`entailment`, `consistency`, `model`) + the propositional-logic
  and linear-arithmetic fragment. Quantifiers, compute, and proof generation
  go to later releases.
- **Consequences:** A solid, end-to-end working foundation; the frontier vision is preserved in
  `Plan.md`, while today's work is kept small.

## ADR-0006 — `unknown` / `error` are first-class output

- **Status:** Accepted · 2026-07-28
- **Context:** FOL is semi-decidable; on some inputs the solver can't decide.
- **Decision:** The engine returns "I don't know" explicitly as `unknown`; a guardrail violation
  becomes `error`. A result is never fabricated.
- **Consequences:** The client (AI) can see the uncertainty and act accordingly; the engine
  stays trustworthy. The expectation of "always an answer" is given up — deliberately.

## ADR-0007 — The input grammar is restricted (whitelist)

- **Status:** Accepted · 2026-07-28
- **Context:** Free-text input is both an injection and an "over-assumption" risk.
- **Decision:** The engine only accepts expressions permitted by the explicitly defined grammar
  (see `docs/mcp-api.md`); it rejects the rest with `error`.
- **Consequences:** A safe and predictable surface; expressive power is limited at first.
  The grammar is extended via ADR as the need is proven.

## ADR-0008 — Solving frontier problems (Track B) is a first-class North Star

- **Status:** Accepted · 2026-07-28
- **Context:** The first draft said "we're not aiming to solve open mathematics"; the project
  owner clearly stated they *do* want to aim for it. There is also a track record of SMT/SAT solvers
  actually solving open problems (Boolean Pythagorean Triples 2016,
  Keller dimension 7 2020, Schur 5 2017).
- **Decision:** "Attacking hard/open problems" is a first-class goal (Track B);
  its scope is honestly bounded: questions reducible to finite/combinatorial satisfiability
  + proof verification/formalization. Track B is built on top of the verifiable core
  (Track A) and starts at v3+. v1 is still Track A.
- **Consequences:** The claim is raised but there's no false promise; "I solved it" is only valid
  with an independently verifiable certificate. Certificate generation/search will be added to the
  architecture later via a new ADR.

## ADR-0009 — Input parsing: Python `ast` + whitelist instead of a hand-written parser

- **Status:** Accepted · 2026-07-28
- **Context:** v1 needed an input language. Writing a lexer/grammar by hand takes time
  and has a wide error/attack surface.
- **Decision:** Take input in Python expression syntax, parse it with `ast.parse(mode="eval")`,
  and filter the nodes with a **whitelist**. Permitted: `and/or/not`,
  `implies/iff/xor`, `+ - *` (linear), comparisons, `Int`/`Bool`. The sort
  is inferred from context; a conflict → `PARSE_ERROR`.
- **Consequences:** A mature parser; precedence/parentheses for free; the attack surface is
  narrowed by the whitelist. The cost: the language is "Python-ish" (`==`, `!=`; implies/iff in function
  form). The v1 fragment was chosen to be **decidable** (Presburger + propositions)
  → mostly definite results, little "unknown".

## ADR-0010 — Quantifiers (∀/∃) + Real; a two-pass translator

- **Status:** Accepted · 2026-07-28
- **Context:** v1.1 wanted `∀`/`∃` and Real to make FOL genuinely "first-order". A quantifier
  introduces a bound variable; its sort is determined from the body
  (before construction) and it must not collide with a free variable (variable capture).
- **Decision:** The translator was split into two passes — (1) infer: scoped sort
  inference, (2) build: Z3 construction. A unique internal name (mangling) for bound constants →
  no capture. Numeric domain: Real if there's a decimal in the problem, otherwise Int.
- **Consequences:** Real FOL expressive power. The cost: decidability weakens,
  `unknown` is possible on some formulas (reported honestly; **soundness** is preserved —
  the engine never produces a wrong answer). Int/Real mixing and predicate symbols
  go to later releases.

## ADR-0011 — Compute layer: SymPy + ast-whitelist (separate from logic)

- **Status:** Accepted · 2026-07-28
- **Context:** v2 wanted symbolic compute (solve/simplify/derivative/integral) for "problem
  solving". This is not the same job as logic/proof (Z3).
- **Decision:** A separate `compute/` layer, with **SymPy**. Input is still filtered with Python `ast` +
  a whitelist (the insecurity of `sympify`/`eval` is NOT used). A separate
  `ComputeResult` contract. The router is the same; only new task names were added.
- **Consequences:** Each job goes to the right tool (logic→Z3, compute→SymPy). Security
  is preserved with the whitelist (e.g. `__import__` is rejected). If SymPy can't solve in closed
  form, it returns an honestly unevaluated result.

## ADR-0012 — Track B seed: programmatic reduction (frontier/)

- **Status:** Accepted · 2026-07-28
- **Context:** The Track B vision (attacking hard/open problems) needed to be shown concretely and
  working. The user input language isn't suitable for this (the problem
  encoding must be programmatic).
- **Decision:** A separate `frontier/` layer; it encodes problems directly into Z3
  (Boolean Pythagorean coloring, pigeonhole). The output is still the shared
  `ReasoningResult`. Two MCP tools were added.
- **Consequences:** The "reduce a problem to satisfiability" method is working.
  HONESTY: small examples are not the famous results *themselves*, but **the same method**
  (the n=7825 bound is ~200 TB; we use small n). Guardrail: large n → unknown/error.

## ADR-0013 — Uninterpreted predicates + individuals (3rd sort: U)

- **Status:** Accepted · 2026-07-28
- **Context:** Genuine relational FOL (the syllogism: "all men are mortal…") needed predicates
  (`P(x)`) and individuals (`socrates`); the earlier language was only Bool + numeric.
- **Decision:** A third sort `U` (individual, `z3.DeclareSort`). Uninterpreted
  predicates as `z3.Function(..., BoolSort())`. In v1.2 predicate arguments are only
  individual names (uninterpreted function terms `f(x)` and arithmetic inside predicates aren't
  there yet). Sort inference is 3-way; name collisions (predicate↔variable) are rejected.
- **Consequences:** The classical syllogism and rule application work. The cost: decidability
  weakens further; `unknown` is possible, **soundness** is preserved.
  Function terms go to the next release.

## ADR-0014 — Proof generation: Z3 verdict + minimal core + ND derivation

- **Status:** Accepted · 2026-07-28
- **Context:** "Valid" isn't enough; science/education need the WHY (step by step).
  Z3's raw proof objects aren't human-readable.
- **Decision:** `core/proof.py` — three layers: (1) Z3's sound verdict, (2) a minimal
  premise core (unsat core), (3) forward-chaining **natural deduction** for the propositional +
  predicate + universal fragment (modus ponens, ∧-elimination, iff-elimination,
  universal instantiation). The deriver is SOUND (only valid rules).
- **Consequences:** The classical syllogism is shown step by step. HONESTY: the deriver is limited
  to this fragment; for arithmetic / `or`-`not` / existential no derivation can be built →
  "Z3 confirmed it but there's no step-by-step derivation" (the verdict is still sound). New MCP tool
  `prove`, CLI `mathhead prove`.

## ADR-0015 — Extending the proof generator (MT, disjunctive syllogism, RAA)

- **Status:** Accepted · 2026-07-28
- **Context:** The first deriver only did forward chaining (MP, ∧, iff, ∀);
  it couldn't build many valid inferences involving `not`/`or` step by step.
- **Decision:** The rule set was extended: modus tollens, disjunctive
  syllogism, double negation, De Morgan (¬(A∨B)). Also a second strategy:
  if a direct one can't be found, **proof by contradiction (RAA)** — assume ¬conclusion and look for a
  contradiction. This yields indirect proofs like "proof by cases".
- **Consequences:** Coverage widened noticeably. Still absent: existential (∃) elimination,
  arithmetic derivation → for those Z3's decision is retained (without steps). The deriver stays sound.

## ADR-0016 — Existential (∃) reasoning in the proof generator

- **Status:** Accepted · 2026-07-28
- **Context:** `∃` was essential for classical FOL natural deduction; the deriver could only
  do propositional + universal.
- **Decision:** **∃-elimination** (a fresh witness constant; each `∃` is eliminated once, the witness
  is added to the set of individuals → `∀`-elimination uses it too) + **∃-introduction** (if the goal
  is `∃x.ψ` and `ψ[t]` was derived for some individual `t`, it is proven). Fresh constants
  are generated so as not to collide; the deriver stays sound (each result is also verified with
  Z3).
- **Consequences:** Inferences like `∃x P(x), ∀x(P→Q) ⊨ ∃x Q(x)` come out step by step.
  Still absent: arithmetic derivation, some nested/mixed quantifier patterns → Z3's decision
  is retained.

## ADR-0017 — Optimization: Z3 Optimize (optimization modulo theories)

- **Status:** Accepted · 2026-07-28
- **Context:** When you need not just ANY solution satisfying the constraints, but the solution that
  optimizes an objective (planning / resource allocation, etc.), SAT isn't enough.
- **Decision:** `logic.optimize` — a `z3.Optimize` core; constraints (bool) + numeric
  objective are translated in a shared context (`translate.translate_objective`). max/min.
- **Consequences:** For linear objectives/constraints it returns the optimum + witness. Honest edge
  cases are reported separately: `unbounded`, `unsat` (no feasible
  solution), open-bound (supremum/infimum via ε, not exactly attainable).

## ADR-0018 — MaxSAT: soft/weighted constraints (z3.Optimize.add_soft)

- **Status:** Accepted · 2026-07-28
- **Context:** Real problems are often over-constrained/conflicting — satisfying all of them
  is impossible; you need to "satisfy the most (or the highest-weighted)".
- **Decision:** `logic.max_satisfy` — `z3.Optimize.add_soft`. Mandatory (hard)
  constraints via `add`, preferred (soft) constraints via `add_soft(w)`. The satisfied softs are
  evaluated in the model and reported.
- **Consequences:** Weighted MaxSAT works (the heavier constraint is preferred). If `hard`
  can't be satisfied, `unsat`. A different question from the same family as Optimize (ADR-0017).

## ADR-0019 — Determinism: the verdict is guaranteed, the witness is an example

- **Status:** Accepted · 2026-07-28
- **Context:** A property-based test (`hypothesis`) caught that `check_consistency` could return a
  different WITNESS (model) on the same input: when there are multiple valid models
  (e.g. `iff(q,r)` → `{q:T,r:T}` or `{q:F,r:F}`), Z3 can pick a different one between
  calls. So the "same input → same output" claim didn't hold at the witness
  level.
- **Decision:** The guarantee was made precise: **the verdict (status: valid/invalid/sat/unsat…)
  is deterministic**; **the witness is a valid example** (which one is returned can vary when there are
  multiple solutions). Also, unconstrained (don't-care) variables
  are pinned to a canonical default (False/0).
- **Consequences:** The claim is now honest and verified by property testing. A fully canonical
  witness (lex-min) was not chosen because it's costly; the stability of the *answer*, which is the
  actual guarantee, is preserved.

---

## ADR-0020 — A deterministic path instead of `.equals()` in the equivalence decision

- **Status:** Accepted · 2026-07-28
- **Context:** The verification layer (Track C — `verify_equality`, `verify_steps`,
  `cross_check`) checked the equivalence of two expressions with SymPy `expr.equals(other)`.
  While developing the cross-check it was seen that `.equals()` does **RANDOM numeric sampling
  internally**: `sqrt(x**2)` vs `x` varied between `None`/`False` from call to call.
  This is contrary to the project's core principle of **determinism**
  (same input → same verdict; ADR-0019).
- **Decision:** `.equals()` was REMOVED from the equivalence decision. A shared deterministic
  helper `verify._equal_verdict`: (1) `simplify(left − right) == 0` → equivalent;
  (2) a fixed-point counterexample scan → if not, `not_equal` + evidence;
  (3) otherwise `undecided`. All deterministic.
- **Consequences:** The verdict is now stable (10/10 identical) **and stronger** (not_equal
  now carries a concrete counterexample). The cost: some equivalences that simplify can't resolve
  return `undecided` — but that beats a "flaky correct": honest uncertainty is consistent with the
  principle. `verify_equality`/`verify_steps`/`cross_check` share this helper.

## ADR-0021 — `pi` and `E` are recognized constants in the compute grammar

- **Status:** Accepted · 2026-07-28
- **Context:** The compute parser (`_to_sympy`) turned every bare name into a free
  `sympy.Symbol`, so `pi` and `E` became symbols, not π and e. A line integral around
  a circle (`param` up to `2*pi`) then returned `sin(4*pi)/2` instead of `0` — correct
  given `pi` as a symbol, but not the mathematical answer. The whole Analysis track (D)
  — transforms, complex analysis — routinely needs π and e.
- **Decision:** A small constant map `_CONSTS` is checked in the `ast.Name` branch of
  `_to_sympy` BEFORE creating a symbol. Only expression parsing is affected; a variable
  passed explicitly via `_symbol` (e.g. a `symbol`/`variables` argument) stays a variable.
  Initially `{pi, E}`; **extended to `I` (imaginary unit) for the D4 complex-analysis
  track** (residue/contour/Laurent/complex_parts). Scope stays intentionally minimal.
- **Consequences:** `pi`/`E` now mean the constants in any compute expression; the
  closed-loop line integral returns `0`. No existing test used `pi`/`E` as an input
  variable (the one `.result == "E"` case is an OUTPUT, unaffected). The specialized
  ODE/recurrence sub-parsers are left as-is for now (revisit in D3 if needed).

---

## ADR-0022 — Induction as a sound meta-rule over Z3 subgoal checks

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP H1 (Logic & Proof Depth) asks for induction proofs. Z3 has no
  native induction: the schema is second-order/meta, and a direct `∀n. P(n)` query over
  nonlinear integer arithmetic simply returns `unknown`. We still want deterministic,
  honest induction that fits the engine's contract.
- **Decision:** Implement induction as a META-RULE, not inside Z3. `core/induction.py`
  reduces `∀n≥start. P(n)` to two ordinary Z3 satisfiability checks — BASE (`¬P(start)`
  UNSAT) and STEP (`P(k) ∧ k≥start ∧ ¬P(k+1)` UNSAT) — over a dedicated single-variable
  nonlinear-int translator (Z3 NIA/LIA). Only if BOTH are discharged do we assert the
  universal conclusion; the induction principle itself is the (sound) glue. A separate
  `InductionResult` dataclass carries `base_case` / `inductive_step` / `proof_steps`.
- **Consequences:** Real theorems become provable (n(n+1) even, n³−n ≡ 0 mod 3, n²≥n).
  Honesty is preserved and sharpened: base-failure is `invalid` (a genuine
  counterexample at `start`), but step-failure is `unknown` (NOT `invalid` — the claim
  may still hold by another argument), and a solver `unknown` on a hard nonlinear step
  stays a first-class wall. Soundness rests on Z3's verdicts for the two subgoals plus
  the standard induction principle; completeness is explicitly not claimed (nonlinear
  steps can defeat the decision procedure).

---

## ADR-0023 — Extra SMT theories as focused tools over one entailment/consistency driver

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP H2 asks for bit-vectors, arrays, strings and uninterpreted
  functions. The kernel grammar (`core/translate.py`) is deliberately linear and
  single-sorted; bolting four new sorts (BV width, arrays, sequences, an abstract sort)
  onto it would risk the frozen contract and the existing tests.
- **Decision:** Add `core/smt.py` as a SEPARATE surface. Each theory is a small,
  self-contained parser feeding Z3's corresponding theory, and all four expose the
  identical shape `check_<theory>(assumptions, goal=None)` routed through ONE driver
  (`_decide`): `goal` → entailment (⋀assumptions ∧ ¬goal UNSAT → valid; SAT → invalid +
  witness), `goal=None` → consistency. They return the shared `ReasoningResult`, so the
  external contract (ADR-0004) is untouched.
- **Consequences:** Real theory theorems are checkable — BV identities with bit-level
  counterexamples, EUF congruence, McCarthy array axioms, string concat/length. The kernel
  grammar is unchanged and existing tools are unaffected. Determinism follows ADR-0019
  (stable verdict; a multi-solution witness is an example — tests assert verdict stability,
  not a pinned witness). Sort clashes and unexpected symbols are honest `PARSE_ERROR`s
  (Wall #2). Scope is intentionally minimal per theory; richer fragments can be added later
  without touching the driver.

---

## ADR-0024 — Quantifier elimination via Z3's `qe` tactic, with honest residual detection

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP H3 (proof generation II) wants quantifier elimination. Z3 exposes a
  `qe` tactic that is complete for linear integer/real arithmetic (Presburger) but may
  leave residual quantifiers on nonlinear/undecidable input.
- **Decision:** `core/qe.py` translates the formula with the existing kernel grammar,
  applies `Then(qe, simplify)` under a `TryFor` time bound, and renders the result with
  Z3's canonical string form. It then WALKS the result tree for any residual quantifier:
  if one remains, the tool returns `unknown`/`QE_INCOMPLETE` (honest) rather than
  pretending elimination succeeded; a `True`/`False` collapse is surfaced via
  `equivalent_to`.
- **Consequences:** QE serves both as a simplifier and as a decision procedure for
  quantified LIA/LRA (∃x. 0<x<1 → False; ∃y. x=2y → x%2=0; ∀x. x>5→x>3 → True). Output is
  Z3's canonical form (deterministic, if not always the prettiest infix). Nonlinear input
  is already rejected by the kernel grammar (Wall #2); time is bounded by `TryFor` →
  `SOLVER_TIMEOUT`. No contract change — `QEResult` is a plain dataclass returned via
  `asdict`.

---

## ADR-0025 — Modal logic by bounded Kripke model checking (definitive refutation, bounded validity)

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP H4 (optional/frontier, "careful scope") wants basic modal/temporal
  logic. Modal validity over a frame class is a ∀-over-frames statement; a complete
  decision procedure (tableaux, or the exponential finite-model bound) is a large effort and
  easy to get subtly wrong.
- **Decision:** `core/modal.py` reduces "is φ valid in system X?" to a search for a
  COUNTERMODEL over W worlds — a pure-Boolean Z3 encoding with one propositional variable
  per (world, atom) and per (world, world) accessibility edge, the system's frame conditions
  (reflexive/transitive/symmetric/serial) as constraints, and the standard Kripke semantics
  for □/◇ expanded into finite conjunctions/disjunctions. A satisfying assignment is a
  countermodel (φ fails at some world); UNSAT over ≤W worlds means no such small countermodel
  exists.
- **Consequences:** A countermodel is a DEFINITIVE, checkable refutation (status `invalid`).
  A negative search yields `valid`/`VALID_BOUNDED`, which is HONESTLY bounded — "valid over
  all frames of the class with up to W worlds", not an unconditional proof; the bound is in
  the explanation and `meta.bounded`. All of K/T/D/B/S4/S5 have the finite-model property, so
  a small W settles the standard axioms — verified by the correspondence theorems
  (T↔reflexive, 4↔transitive, 5↔S5). Determinism follows ADR-0019 (stable verdict; the
  countermodel witness is one example). Temporal logics (LTL/CTL) need ω-semantics
  (loops/fairness) and are deliberately out of scope; they can be added as a separate tool
  without disturbing this one.

---

## ADR-0026 — J1 reductions: independently-verified witnesses (and TSP via MTZ)

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP J1 adds classic NP-complete/combinatorial reductions (N-queens, Latin
  squares, Sudoku, Hamiltonian path/cycle, Ramsey, decision-TSP). They must fit the frontier
  philosophy: a positive answer should be a CHECKABLE certificate, not "trust the solver".
- **Decision:** Each reduction encodes the problem for Z3 and, on `sat`, RE-VERIFIES the
  extracted witness in pure Python before returning it (`meta.verified: true`) — permutation/
  diagonal checks for queens, row/col/box permutation checks for Sudoku/Latin, edge-membership
  along the order for Hamiltonian, no-monochromatic-clique for Ramsey, single-cycle-and-cost for
  TSP. If verification fails, the tool returns `UNEXPECTED_SAT` (an internal-inconsistency guard)
  rather than a possibly-bogus witness. TSP uses a directed-arc formulation with MTZ subtour
  elimination and a `Σ length ≤ budget` constraint.
- **Consequences:** Positive results carry an engine-independent certificate (an encoding bug is
  caught, not shipped). Known values are reproduced (N-queens unsat at 2/3, R(3,3)=6). The
  `unsat` side is still a bare Z3 verdict — its independent DRAT/LRAT certificate is the standing
  Phase-10 wall, addressed in J2. Sizes are capped for tractability (honest `error` above the
  cap); `unknown` stays first-class on timeout.

---

## ADR-0027 — Verifiable UNSAT: a self-contained DRUP producer + independent RUP checker

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP J2 must produce an INDEPENDENTLY-checkable certificate for UNSAT — the
  Phase-10 wall (a `sat` witness was already independently verified; `unsat` was only Z3's
  verdict). SETUP.md requires checking whether external tools (drat-trim / CaDiCaL / Kissat)
  can actually be installed, and marking an honest wall otherwise rather than shipping a stub.
- **Decision:** Go fully self-contained, stdlib-only, in `mathhead/drat.py` (which imports
  neither z3 nor sympy — preserving the `certificate.py` independence guarantee). Two halves:
  a reverse-unit-propagation (RUP) CHECKER that validates a DRUP proof (each lemma RUP over the
  accumulated formula, ending in the empty clause), and a PRODUCER — a DPLL search that emits a
  tree-resolution refutation as a DRUP proof (a resolvent of two clauses is RUP from them). The
  producer re-checks its own output with the independent checker before returning. `drat-trim`
  is not in apt, and PySAT's `get_proof()` returned EMPTY (uncheckable) proofs for genuinely-hard
  instances (e.g. PHP(3)) in this environment — an unreliable base, so it was rejected in favour
  of the self-contained path.
- **Consequences:** UNSAT results carry an engine-independent, polynomial-time-checkable
  certificate with NO external binary. Correctly reproduces pigeonhole refutations; correctly
  REJECTS incomplete/bogus proofs (an empty proof only verifies when the empty clause is directly
  RUP). The producer is bounded (≤20 variables + a node budget) — beyond that it is an honest
  `unknown`, never a fabricated certificate; `check_unsat_proof` accepts much larger proofs
  (checking is polynomial). Bridging the Z3-based `frontier` reductions to DIMACS CNF so their
  `unsat` cases emit certificates directly is a future enhancement.

---

## ADR-0028 — High-performance SAT as an OPTIONAL backend (verified model, conflict-bounded)

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP J3 wants CaDiCaL/Kissat-class performance for large CNF. SETUP.md requires
  checking real installability and preferring an honest wall over a stub. `python-sat` is
  pip-installable with bundled CaDiCaL/Glucose/MiniSat (no system package); `drat-trim`/`Kissat`
  are not available here.
- **Decision:** `mathhead/hpsolver.py` wraps python-sat as an OPTIONAL dependency (`[solvers]`
  extra; also in `[dev]` so tests exercise it). `solve_cnf(clauses, solver, max_conflicts,
  backend)` runs the CDCL backend under a CONFLICT BUDGET (`solve_limited`), so a hard instance
  returns `unknown`/`BUDGET_EXCEEDED` rather than hanging (PRINCIPLES 4). Every `sat` model is
  re-verified against the clauses in pure Python before it is returned (`meta.verified`) — a
  backend bug cannot ship a bogus model. When python-sat is absent, `backend="auto"` degrades to
  the built-in stdlib DPLL (`drat.refute`) for ≤20 variables (returning a verified DRUP proof on
  unsat) and reports `BACKEND_UNAVAILABLE` for larger inputs; `backend="pysat"` forces the HP
  backend (honest error if missing), `backend="builtin"` forces the fallback.
- **Consequences:** Large CNF SAT is fast (a 2500-var/63k-clause instance in ~0.1 s) with an
  engine-independent model check; the core engine keeps its minimal dependency set (z3/sympy/mcp)
  because the backend is optional. Determinism follows ADR-0019 (stable verdict; the model is one
  example). `Kissat` and portfolio/parallel solving are out of scope here (no package / larger
  effort) — stated honestly rather than stubbed. An UNSAT verdict from the HP backend is not a
  certificate; `prove_unsat`/`check_unsat_proof` (J2) remain the checkable-certificate path.

---

## ADR-0029 — Performance: memoization is safe because verdicts are deterministic; incremental entailment

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP K1 wants caching and incremental solving without disturbing the frozen
  contract or the determinism guarantee.
- **Decision:** Two additions. (1) `mathhead/cache.py` — a bounded-LRU `@memoize` applied ONLY to
  pure, hashable-argument compute functions. Determinism (PRINCIPLES 1) makes this safe: a hit
  returns the IDENTICAL cached result object, so a cached answer is indistinguishable from a fresh
  one (unhashable arguments bypass the cache; `cache_stats`/`reset_cache` give observability and
  test isolation). (2) `core/logic.entail_batch` — checks many conclusions against shared premises
  by asserting the premises ONCE and testing each conclusion in a Z3 `push`/`pop` scope; the
  per-conclusion verdict is identical to `check_entailment`, only the context is reused.
- **Consequences:** Repeated identical compute calls are served from memory with byte-identical
  results; a batch of related entailment queries avoids re-asserting the premises. No contract
  change (`BatchResult`/`CacheStats` are plain dataclasses carrying the standard
  status/reason/explanation/meta). `meta.elapsed_ms` on a cached compute result reflects the
  original computation — acceptable because the result is deterministically identical. Broader
  router-level caching and Z3 incremental reuse across other primitives are left as future,
  opt-in extensions.

---

## ADR-0030 — Observability as transparent side-state over the existing meta traceability

- **Status:** Accepted · 2026-07-28
- **Context:** ROADMAP K3 wants structured metrics/logs, introspectable resource limits, and a perf
  regression fence — without changing results or the determinism guarantee.
- **Decision:** `mathhead/observability.py` adds an `observe` decorator on `router.route` that times
  each call and records (task, status, elapsed_ms) into an in-memory aggregate (counters + timing
  sums + a bounded recent-call ring). `engine_metrics` returns a snapshot; `resource_limits` reads
  the active guardrail constants. Both are exposed as read-only tools. A perf fence test asserts
  representative operations stay within a generous budget.
- **Consequences:** The traceability already present in every result's `meta` (PRINCIPLES 9) becomes
  a queryable aggregate. Metrics are OBSERVATIONAL side-state — results are byte-identical with or
  without observation, so determinism is untouched; `reset_metrics` gives test isolation. The perf
  fence catches gross regressions without being a flaky micro-benchmark. Persisting metrics across
  process restarts and richer structured log sinks are left as future extensions.

---

## ADR-0031 — Version vocabulary, stable-core/experimental-extended, MCP-as-contract (Track L)

- **Status:** Accepted · 2026-07-28 (Track L — external-review response)
- **Context:** An external review flagged that the repo over-claimed maturity (the
  `Production/Stable` classifier) and carried self-contradictory version language: compute
  documented as "v2+ / empty in v1" though fully implemented; grammar "v1.2" vs package 1.0.0;
  the README exposing internal Python imports while claiming MCP is the only contract. These are
  honesty/clarity defects, not code bugs.
- **Decision:**
  1. **Maturity is Beta, not Production/Stable.** The MCP *contract* is frozen (SemVer 1.0.x) but
     release maturity (no PyPI, single-OS/Python CI) and the extended surface are not yet proven →
     classifier `4 - Beta`.
  2. **Stable core + experimental extended.** The verification surface (`verify_*`, `cross_check`,
     `check_certificate`, entailment/consistency/model, `prove_unsat`/`check_unsat_proof`) is the
     stable core; the broad CAS catalog, frontier reductions, and observability are experimental
     until per-tool stability metadata makes it explicit (L2).
  3. **A single version vocabulary:** package `1.0.x` · MCP contract `1` · input grammar `1.2` ·
     extended packs `experimental` — intentionally independent.
  4. **MCP is the supported contract; the Python API is internal.** `from mathhead.…` imports are
     convenience and NOT covered by the SemVer promise.
  5. **Positioning:** MathHead is a *deterministic verification + counterexample engine for
     AI-generated mathematics* (its own Track-C thesis); the compute catalog is supporting
     infrastructure.
- **Consequences:** The stale "v2+/empty-in-v1" language is removed and fenced by a docs test; the
  README states the boundary + vocabulary; the classifier is honest. No code/API change. Per-tool
  stability (L2), core-profile/capability-packs (L3), and release-credibility CI (L1) build on this.

---

## ADR-0032 — Epistemic-strength (`certainty`) + tool `stability`, carried in meta (additive)

- **Status:** Accepted · 2026-07-28 (Track L / L2)
- **Context:** The external review noted that a single `valid` conflates very different epistemic
  strengths (a Z3 decision, a SymPy computation, a *bounded* modal check, an independently
  re-checked certificate, a numerical check). It also asked for per-tool stability and a single
  machine-readable contract artifact. The MCP contract is frozen, so additions must be
  backward-compatible.
- **Decision:** `mathhead/certainty.py` classifies every result's epistemic strength (`certainty` ∈
  formal_proof / independent_certificate / solver_verified / bounded_check / symbolic_result /
  numerical_check / unknown / error / not_applicable) and every tool's stability tier
  (stable / provisional / experimental / internal). Both are injected into `meta` by the router's
  public `route` wrapper (`_dispatch` does the routing; `route` annotates) — ADDITIVE, so the frozen
  `status`/`reason_code`/`explanation`/`meta` envelope is untouched. `scripts/gen_contract.py` emits
  `docs/mcp-contract.json` (per-tool description + input schema + stability, plus the envelope and
  the vocabularies); a test enforces code = docs.
- **Consequences:** A caller can now tell a *formal proof* from a *bounded check* from a *symbolic
  result* without reading prose — the honesty the engine already practiced (e.g. modal
  `VALID_BOUNDED`) is now uniform and machine-readable. Stability makes "stable core (19 verification
  tools) + experimental extended (131)" concrete. **Adding a key to `meta` is explicitly NOT a
  breaking change** under this contract; the frozen surface is unaffected.

---

<!-- New decision template:
## ADR-XXXX — title
- **Status:** Proposed | Accepted | Superseded (ADR-YYYY) · YYYY-MM-DD
- **Context:** …
- **Decision:** …
- **Consequences:** …
-->
