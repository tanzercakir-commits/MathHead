# MathHead — Progress / ChangeLog

> **This file's job:** WHAT we did, WHEN, WHY — an append-only log. Newest on top.
> The *rationale* of small design decisions goes to `DECISIONS.md`, the *summary* of
> the work done goes here.

---

## 2026-07-28 — H4 · modal logic (K/T/D/B/S4/S5)

**Done — 1 new logic tool (155 total):**

- `check_modal` (new `core/modal.py`): propositional modal-logic validity by BOUNDED Kripke
  model checking. `box(φ)`=□, `dia(φ)`=◇, plus and/or/not, implies/iff, across the normal
  systems K, T, D, B, S4, S5 (frame conditions on accessibility:
  reflexive/transitive/symmetric/serial). Searches for a countermodel over W worlds as a
  pure-Boolean Z3 problem.
- Wired router + MCP (155 tools) + CLI (`modal`) + `tests/test_modal.py` (12) → **1048/1048 green**.

**Verified — the correspondence theorems come out exactly right:** the K axiom
□(p→q)→(□p→□q) is valid in every system; T (□p→p) becomes valid exactly with reflexivity
(invalid in K); 4 (□p→□□p) needs transitivity (valid from S4); 5 (◇p→□◇p) only in S5;
D (□p→◇p) holds on serial frames (valid in T). A countermodel carries the worlds, the
accessibility relation, the valuation, and the refuting world.

**Honest scope (🔴 frontier):** a countermodel is a DEFINITIVE refutation; a positive result
is `VALID_BOUNDED` — "no countermodel with up to W worlds" (bounded model checking), not an
unconditional proof. All six systems have the finite-model property, so a small W settles
the standard axioms; the bound is always surfaced in the explanation and meta. Temporal
(LTL) operators are deliberately left as a future extension (careful scope).

**Decision:** ADR-0025 (bounded Kripke model checking; definitive refutation vs. bounded
validity, stated honestly).

**Next:** H5 — [S] Track H hardening.

## 2026-07-28 — H3 · proof generation II (quantifier elimination)

**Done — 1 new logic tool (154 total):**

- `eliminate_quantifiers` (new `core/qe.py`): Z3's `qe` tactic over Presburger arithmetic
  turns a quantified LINEAR formula into an equivalent QUANTIFIER-FREE one — genuine proof
  depth, and a decision procedure for quantified LIA/LRA (collapses to True for a valid
  statement, False for an unsatisfiable one). Input uses the kernel grammar
  (`forall`/`exists`, `+ - *`, comparisons, `and`/`or`/`not`, `implies`/`iff`).
- Wired router + MCP (154 tools) + CLI (`qe`) + `tests/test_qe.py` (9) → **1034/1034 green**.

**Verified (real QE results, integer-aware):** ∃x. a≤x≤b ⟶ a≤b; ∃x. 0<x<1 ⟶ False
(no integer strictly between); ∃y. x=2y ⟶ x%2=0 (x even); ∀x. x>5→x>3 ⟶ True.

**Honest wall:** on a nonlinear/undecidable fragment where a residual quantifier remains,
the tool returns `unknown`/`QE_INCOMPLETE` (the residual is reported, never dropped);
nonlinear input is already rejected by the kernel grammar; a `TryFor` time bound →
`SOLVER_TIMEOUT`.

**Decision:** ADR-0024 (QE via Z3 `qe` + honest residual-quantifier detection).

**Next:** H4 — modal/temporal logic (K/S4 basics, careful scope).

## 2026-07-28 — H2 · SMT theories (bit-vectors, EUF, arrays, strings)

**Done — 4 new logic tools (153 total):**

- New `core/smt.py` opens four more of Z3's decision theories, each with the SAME shape
  as the kernel's entailment/consistency primitives — `check_<theory>(assumptions,
  goal=None)`: goal → entailment (valid/invalid + witness), goal=None → consistency
  (sat/unsat).
  - `check_bitvector` — fixed-width BV (`& | ^ ~ << >> + - *`, (un)signed compares):
    bit tricks, masks, overflow.
  - `check_uninterpreted` — equality + uninterpreted functions/predicates (EUF, congruence).
  - `check_arrays` — `select`/`store` (McCarthy axioms; array names inferred).
  - `check_strings` — concat/`length`/`contains`/`prefixof`/`suffixof`, literals.
- Wired router + MCP (153 tools) + CLI (`bitvector`/`uf`/`arrays`/`strings`) +
  `tests/test_smt.py` (24) → **1023/1023 green**.

**Verified (real theory theorems):** BV x^y^y==x valid, x|y≠x+y refuted with a bit-level
counterexample, (x&(x-1))==0 finds a power of two; EUF a==b ⊨ f(a)==f(b); array
read-over-write (same & different index); string length(x+y)==length(x)+length(y), and
solving x+"b"=="ab" → x="a".

**Determinism (ADR-0019 honored):** the VERDICT is stable; a multi-solution counterexample
witness is an *example* (may vary among equally-valid ones) — tests assert verdict
stability, not a pinned witness.

**Decision:** ADR-0023 (extra theories as focused tools sharing ONE entailment/consistency
driver; the kernel grammar is untouched).

**Next:** H3 — proof generation II (quantifier elimination + deeper derivations).

## 2026-07-28 — H1 · induction proofs (Track H begins)

**Done — 1 new proof tool (149 total):**

- `prove_by_induction` (new `core/induction.py`): mathematical induction over the
  integers. Z3 CANNOT do induction natively (the schema is not first-order SMT; a naive
  ∀n.P(n) over nonlinear arithmetic returns `unknown`). We add it as a SOUND META-RULE:
  Z3 checks the BASE case P(start) and the INDUCTIVE STEP P(k)→P(k+1); the induction
  principle then yields ∀n≥start.P(n). Dedicated single-variable nonlinear-int
  mini-translator (`+ - * ** % //`) feeding Z3 NIA/LIA.
- Wired router + MCP (149 tools) + CLI (`induction`) + `tests/test_induction.py` (14)
  → **990/990 green**.

**Verified (real theorems proved):** n(n+1) even; n³−n divisible by 3; n²≥n; the
identity (n+1)²=n²+2n+1; n²≥2n from start=2.

**Honest walls (PRINCIPLES 2/3 — never a fake proof):** base-case failure → `invalid`
(the claim is false; n=start is a counterexample, e.g. `n>=5`); inductive-step failure
→ `unknown`/`STEP_FAILED` with the counterexample k (NOT `invalid` — the claim may still
be true by another argument, e.g. `n<3` fails the step at k=2); Z3 `unknown` on a hard
nonlinear step → `unknown`/`SOLVER_UNKNOWN` (e.g. n(n+1)(n+2) divisible by 6 is TRUE but
the step exceeds the decision procedure).

**Decision:** ADR-0022 (induction = sound meta-rule over two Z3 subgoal checks).

**Next:** H2 — SMT theories (arrays, bit-vectors, strings, uninterpreted functions).

## 2026-07-28 — G4 [S] · numerical hardening → TRACK G DONE 🎉

**Done**

- New `tests/test_numerical_hardening.py` (8): the property tests ARE the numerical guarantees.
  Tests only — no new tools.
- **Guarantees proven on random input:** a returned Newton root has residual < 1e-8; composite
  Simpson is EXACT on cubics; Lagrange interpolation recovers the generating quadratic;
  RK4 of y'=k·y matches e^{k·x}; the precision bridge is self-consistent (verify_numeric agrees
  with evaluate_precision); symbolic and numeric paths agree for polynomials.
- **Fuzz + determinism.** **974/974 green.**

**Milestone:** Track G (Numerical Methods) COMPLETE — root-finding & quadrature (G1), numerical
linalg & RK4 (G2), the precision bridge (G3), all hardened (G4). All numerical work is
deterministic (fixed mpmath precision) and honest about convergence — numerics that still fit the
engine's "reliable, auditable" mission (verify_numeric / cross_check_numeric extend the audit theme).

**Next:** Track H (Logic & Proof Depth) — roadmap order H → J → K.

## 2026-07-28 — G3 · precision bridge (arbitrary precision + symbolic↔numeric)

**Done — 3 new compute tools (148 total):**

- `evaluate_precision` (a constant to N significant figures — e.g. π to 50 digits),
  `verify_numeric` (verify a CLAIMED numerical value against the exact high-precision value —
  the numeric analogue of the Track C verifiers), `cross_check_numeric` (SYMBOLIC↔NUMERIC
  cross-validation of f(point): two independent evaluation paths must AGREE — a bug detector,
  the same philosophy as the Track C `cross_check`).
- Wired router + MCP (148 tools) + CLI (`precision`/`verify-numeric`/`cross-check-numeric`) +
  `tests/test_precision.py` (13) → **966/966 green**.

**Verified:** π to 50 digits; verify_numeric accepts 3.14159265358979 and REJECTS 3.14 as π;
symbolic and numeric agree for sin²+cos²=1 at x=1.3, x³−2x at x=3 (=21), and exp at 0.

**Alignment:** this phase directly serves the product mission — `verify_numeric` and
`cross_check_numeric` extend the "audit AI answers" theme into the numerical domain.

**Next:** G4 [S] — numerical hardening → closes Track G.

## 2026-07-28 — G2 · numerical linear algebra & ODE

**Done — 3 new compute tools (145 total):**

- `numerical_eigenvalues` (mpmath.eig; complex eigenvalues as `a ± b*I`), `condition_number`
  (κ = σ_max/σ_min; `null` when singular), `runge_kutta` (classic RK4 IVP solver → final value +
  a sampled trajectory).
- Deterministic (fixed `mpmath.workdps(30)`). Wired router + MCP (145 tools) + CLI
  (`num-eigenvalues`/`condition-number`/`rk4`) + `tests/test_numerical_linalg.py` (11) → **947/947 green**.

**Verified:** eig([[2,1],[1,2]]) = {1,3}; eig(rotation) = ±i; κ(diag(2,1))=2, κ(I)=1, singular→∞;
RK4 of y'=y → e, y'=x → x²/2 (2 at x=2), y'=2x+1 → x²+x (12 at x=3).

**Next:** G3 — precision bridge (arbitrary-precision eval, symbolic↔numeric cross-validation, error bounds).

## 2026-07-28 — G1 · root-finding & numerical analysis (Track G begins)

**Done — 5 new compute tools (142 total):**

- `find_root_newton`, `find_root_bisection` (needs a sign change), `find_root_secant`,
  `numerical_integrate` (composite Simpson/trapezoid), `interpolate` (Lagrange polynomial).
- **Deterministic numerics:** all numerical work runs inside `mpmath.workdps(30)` (fixed
  precision, no global side effects) and results are rounded — same input → same output
  (ADR-0019 holds even for iterative methods). Non-convergence is flagged (`converged:false`),
  never hidden.
- Wired router + MCP (142 tools) + CLI (`newton`/`bisection`/`secant`/`num-integrate`/
  `interpolate`) + `tests/test_numerical.py` (14) → **929/929 green**.

**Verified:** Newton & bisection & secant all find √2; Newton finds the Dottie number
(cos x = x → 0.739085); Simpson is exact on x² over [0,3] = 9; trapezoid of sin over [0,π] ≈ 2;
Lagrange interpolation of (0,1),(1,3),(2,7) = x²+x+1, value at 3 = 13, and recovers a known line.

**Honest walls:** bisection refuses without a sign change; an expression with extra free
symbols is rejected; non-convergence is surfaced, not papered over.

**Next:** G2 — numerical linear algebra & ODE (numerical eigenvalues, condition number, RK4).

## 2026-07-28 — F4 [S] · probability/stats hardening → TRACK F DONE 🎉

**Done**

- New `tests/test_probability_hardening.py` (9): the property tests ARE the defining facts.
  Tests only — no new tools.
- **Invariants proven on random input:** a Bayes posterior ∈ [0,1]; uninformative evidence
  (likelihood = false-alarm) leaves the prior unchanged; a Markov stationary π is a FIXED POINT
  of P (one more step changes nothing) and sums to 1; Cov(X,X) = Var(X); correlation = 1 for
  positively-linear data; a χ² p-value ∈ [0,1]; a Lagrange point satisfies its constraint;
  a positive-weighted sum of squares is convex.
- **Determinism** spot checks. **905/905 green.**

**Milestone:** Track F (Probability, Statistics & Optimization) COMPLETE — probability II (F1),
inferential statistics (F2), symbolic optimization (F3), all hardened (F4). p-values are
numerical-but-deterministic (mpmath); everything else stays exact.

**Next:** Track G (Numerical Methods) — roadmap order G → H → J → K.

## 2026-07-28 — F3 · optimization II (symbolic)

**Done — 3 new compute tools (137 total):**

- `critical_points` (unconstrained ∇f=0, each classified local_min/local_max/saddle/
  inconclusive by the Hessian's definiteness), `lagrange_multipliers` (equality-constrained;
  solves ∇f=Σλᵢ∇gᵢ, gᵢ=0 → points + multipliers + objective value), `check_convexity`
  (Hessian test → convex/concave/neither/undetermined). Pure SymPy; variables treated as REAL
  (so e.g. exp(x) resolves as convex).
- **Scope note:** linear/integer programming over reals/ints is already covered by the Z3
  `optimize` tool (sort inference gives Int without decimals, Real with) — F3 adds the SYMBOLIC
  layer that Z3 doesn't do (explicit multipliers, Hessian classification, global convexity).
- Wired router + MCP (137 tools) + CLI (`critical-points`/`lagrange`/`convexity`) +
  `tests/test_optimization2.py` (13) → **896/896 green**.

**Verified:** x²+y² → local min at (0,0), convex; x²−y² → saddle, neither; x³−3x → max at −1,
min at 1; max x·y s.t. x+y=10 → (5,5), λ=5, f=25; exp(x) convex (real-variable assumption).

**Next:** F4 [S] — probability/stats hardening → closes Track F.

## 2026-07-28 — F2 · inferential statistics

**Done — 6 new compute tools (134 total):**

- `t_test` (one-sample vs μ / Welch two-sample), `z_test` (known σ), `chi_square_test`
  (goodness-of-fit), `anova_oneway`, `confidence_interval` (t-based), `linear_regression`
  (OLS + slope test). Each returns the statistic, df, and p-value.
- **p-values via mpmath** — the incomplete gamma/beta functions (χ²/t/F CDFs) are computed
  at high precision with mpmath (already a SymPy dependency; NO new package) and rounded.
  Deterministic: same input → same output (ADR-0019 preserved even for numerical stats).
- Wired router + MCP (134 tools) + CLI (`t-test`/`z-test`/`chi2-test`/`anova`/`conf-interval`/
  `regression`) + `tests/test_statistics2.py` (15) → **877/877 green**.

**Verified against textbook values:** χ²([10,20,30,40] vs uniform) = 20, df=3, p≈0.0002;
one-way ANOVA of [1,2,3],[4,5,6],[7,8,9] → F=27, df=(2,6); 95% CI of [2,4,6,8,10] =
[2.07, 9.93]; regression of y≈2x → slope 2.0, r²=1.0; identical-mean samples → p=1.

**Next:** F3 — optimization II (linear/integer programming, Lagrange multipliers, KKT/convex).

## 2026-07-28 — F1 · probability II (Track F begins)

**Done — 6 new compute tools (128 total):**

- `bayes_theorem` (→ {posterior, evidence}), `covariance` (population/sample), `correlation`
  (Pearson ρ), `markov_stationary` (stationary π of a row-stochastic matrix), `markov_step`
  (initial·Pᵏ), `joint_marginal` (P(X)/P(Y) from a joint table). All EXACT (SymPy rationals).
- Wired router + MCP (128 tools) + CLI (`bayes`/`covariance`/`correlation`/`markov-stationary`/
  `markov-step`/`marginal`) + `tests/test_probability2.py` (18) → **850/850 green**.

**Verified:** the base-rate case (prior 1%, sens 90%, false-alarm 5%) → posterior 2/13
(≈15%, the classic base-rate lesson); Cov population 7/8, sample 7/6; ρ=±1 for perfectly
linear data; stationary π of [[1/2,1/2],[1/4,3/4]] = [1/3, 2/3]; 2-step evolution [1,0]→[3/8,5/8].

**Honesty:** zero evidence (Bayes), zero variance (correlation), and a non-row-stochastic
transition matrix are rejected — no fabricated probabilities.

**Next:** F2 — inferential statistics (z/t/χ²/ANOVA tests, confidence intervals, p-values, regression).

## 2026-07-28 — E6 [S] · algebra/discrete hardening → TRACK E DONE 🎉

**Done**

- New `tests/test_algebra_hardening.py` (12): the property tests ARE the classic theorems.
  Tests only — no new tools.
- **Theorems proven as properties** on random input: Lagrange (|generated subgroup of Sₘ|
  divides m!), Euler-φ multiplicativity (φ(mn)=φ(m)φ(n) for coprime), Σ_{d|n} φ(d)=n,
  Σ_{d|n} μ(d)=[n=1], Pell solutions satisfy x²−n·y²=1, Bₙ=Σ S(n,k) (second kind),
  the Catalan–binomial identity Cₙ=C(2n,n)/(n+1) (cross-checked against stdlib `math.comb`),
  permutation sign is multiplicative, and QR reconstructs A.
- **Fuzz + determinism** across the number/combinatorics tools. **821/821 green.**

**Milestone:** Track E (Algebra & Discrete Structures) COMPLETE — permutation groups (E1),
linear algebra III (E2), graph theory (E3, pure stdlib), number theory II (E4),
combinatorics II (E5), all hardened (E6). Engine grew 89→122 tools this track.

**Next:** Track F (Probability, Statistics & Optimization) — roadmap order F → G → H → J → K.

## 2026-07-28 — E5 · combinatorics II

**Done — 6 new compute tools (122 total):**

- `catalan_number`, `bell_number`, `stirling_number` (first/second kind), `derangements`
  (!n, the inclusion-exclusion classic), `generating_function_coefficient` ([xⁿ] of a GF's
  series), `necklace_count` (distinct necklaces under rotation — Burnside/Pólya).
- Wired router + MCP (122 tools) + CLI (`catalan`/`bell`/`stirling`/`derangements`/
  `gf-coeff`/`necklaces`) + `tests/test_combinatorics2.py` (14) → **809/809 green**.

**Verified:** C₅=42, B₅=52; S(5,2) second=15, first=50; !4=9, !0=1; [x⁶] of the Fibonacci
GF 1/(1−x−x²) = 13 (=F₇) and [x³](1+x)⁵ = 10 (=C(5,3), a GF↔binomial cross-check);
necklaces(4,2)=6, necklaces(6,3)=130.

**Next:** E6 [S] — algebra/discrete hardening (Lagrange's theorem, Euler-φ identities, etc.) → closes Track E.

## 2026-07-28 — E4 · number theory II

**Done — 7 new compute tools (116 total):**

- `euler_totient` (φ), `mobius` (μ), `continued_fraction` (rational → term list),
  `continued_fraction_sqrt` (√n → {a0, period}), `quadratic_residue` (→ {is_residue,
  jacobi_symbol}), `primitive_root` (smallest, or null if none), `pell_solution`
  (fundamental x²−n·y²=1). SymPy-backed; used the NON-deprecated import path for the
  Jacobi symbol (`sympy.functions.combinatorial.numbers`).
- Wired router + MCP (116 tools) + CLI (`totient`/`mobius`/`cfrac`/`cfrac-sqrt`/
  `quad-residue`/`primitive-root`/`pell`) + `tests/test_numbertheory2.py` (18) → **782/782 green**.

**Verified:** φ(12)=4, μ(30)=−1, μ(12)=0; CF(415/93)=[4,2,6,7]; √23=[4;(1,3,1,8)];
2 is a QR mod 7 (jacobi +1), 3 is not (−1); primitive root of 7 is 3; Pell n=13 → (649,180).

**Honesty:** `primitive_root(8)` → null (none exists for 8); `pell_solution(9)` → null
(perfect square has only the trivial solution) — both stated, not fabricated.

**Next:** E5 — combinatorics II (generating functions, inclusion-exclusion, Catalan/Bell/Stirling, Polya).

## 2026-07-28 — E3 · graph theory (pure stdlib, deterministic)

**Done — 6 new compute tools (109 total):**

- `shortest_path` (Dijkstra/BFS), `connected_components` (union-find), `minimum_spanning_tree`
  (Kruskal), `max_flow` (Edmonds-Karp = min cut), `maximum_matching` (bipartite, Kuhn),
  `is_isomorphic` (backtracking + degree pruning, ≤10 nodes).
- **PURE STDLIB — no networkx.** In keeping with the project's minimal-dependency ethos
  (z3+sympy+mcp, stdlib-only certificate checker), the graph algorithms are hand-written and
  **deterministic by construction** (sorted neighbor iteration, tie-break counters).
- Wired router + MCP (109 tools) + CLI (`shortest-path`/`components`/`mst`/`max-flow`/
  `matching`/`isomorphic`, edges as JSON) + `tests/test_graph.py` (16) → **751/751 green**.

**Verified:** weighted shortest path 0→2→1→3 = 4; components counts an isolated node;
MST of a triangle = 3 (+ forest when disconnected); max flow = min cut = 5; bipartite
matching size 2; relabeled triangles isomorphic (with mapping), K₁,₃ vs P₄ pruned by degree.

**Honesty:** an unreachable target returns `{path: null}` (no fabricated path); a non-bipartite
input to matching, or graphs >10 nodes to isomorphism, are rejected honestly.

**Next:** E4 — number theory II (continued fractions, quadratic residue, primitive root, Pell, Euler φ / Möbius).

## 2026-07-28 — E2 · linear algebra III (decompositions & matrix functions)

**Done — 9 new compute tools (103 total — crossed 100):**

- `singular_values`, `qr_decomposition` (→ {Q, R}), `cholesky_decomposition` (→ {L}),
  `gram_schmidt` (orthonormal), `pseudoinverse` (A⁺), `matrix_exponential` (e^A),
  `jordan_form` (→ {P, J}), `characteristic_polynomial`, `least_squares`.
- All symbolic/exact (SymPy). Preconditions checked honestly: Cholesky requires
  symmetric positive-definite (else COMPUTE_FAILED); exp/Jordan/charpoly require square.
- Wired router + MCP (103 tools) + CLI (`singular-values`/`qr`/`cholesky`/`gram-schmidt`/
  `pinv`/`matrix-exp`/`jordan`/`charpoly`/`least-squares`) + `tests/test_linalg3.py` (14)
  → **723/723 green**.

**Verified:** σ([4,0;3,−5]) = [2√10, √10]; Q·R reconstructs A (checked in-test); Cholesky
[4,2;2,3]=[2,0;1,√2]; e^[[0,1],[0,0]]=[[1,1],[0,1]]; charpoly diag(2,3)=λ²−5λ+6; least
squares through (1,1),(2,2),(3,2) → intercept 2/3, slope 1/2.

**Next:** E3 — graph theory (shortest path, connectivity, matching, max-flow/min-cut, MST, isomorphism).

## 2026-07-28 — E1 · abstract algebra: permutation groups (Track E begins)

**Done — 5 new compute tools (94 total):**

- `permutation_order`, `permutation_parity` (even/odd), `permutation_compose`
  (left-to-right → result array + order), `group_order(name, degree)` (named groups
  symmetric/alternating/cyclic/dihedral → order + abelian), `generated_group(generators)`.
- Backed by `sympy.combinatorics`; permutations in **array form** (0-indexed image list).
  Invalid permutations (non-bijections) and unknown group names are rejected honestly.
- Wired router + MCP (94 tools) + CLI (`perm-order`/`perm-parity`/`perm-compose`/
  `group-order`/`gen-group`) + `tests/test_algebra.py` (18) → **691/691 green**.

**Verified:** order of (0 1 2) = 3; 3-cycle even, transposition odd; |S₃|=6 non-abelian,
|A₄|=12, |C₆|=6 abelian, |Dₙ|=2n; a 3-cycle + a transposition generate S₃ (order 6).

**Honest wall:** full ring/field structure theory is deferred — E1 covers the concrete,
well-supported permutation-group layer; broader abstract structures are a larger effort.

**Next:** E2 — linear algebra III (SVD, QR, Cholesky, Gram-Schmidt, pseudo-inverse, matrix exp, Jordan).

## 2026-07-28 — D5 [S] · analysis hardening → TRACK D DONE 🎉

**Done**

- New `tests/test_analysis_hardening.py` (8): property-based (hypothesis) + a numerical
  cross-check + determinism/fuzz across Track D. Tests only — no new tools.
- **Identities proven on random fields:** ∇×(∇f) ≡ 0, ∇·(∇×F) ≡ 0, and ∇²f = ∇·(∇f)
  — the last one checked with MathHead's OWN `verify_equality` (dogfooding the verifier).
- **Numerical cross-check:** ∇×(∇f) evaluated at sample points is ~0 (independent of
  symbolic simplification). **Round-trip:** ℱ then ℱ⁻¹ recovers the Gaussian family.
  **Complex:** `complex_parts` matches the (a+bi)(c+di) product formula for random ints.
- **Safety:** transforms/residue/laplacian never crash on random junk. **664/664 green.**

**Milestone:** Track D (Analysis & Transforms) COMPLETE — vector calculus (D1), integral
transforms (D2), differential equations II (D3), complex analysis (D4), all hardened (D5).
Engine grew 71→89 tools; the compute grammar gained the constants π, e, I (ADR-0021).

**Next:** Track E (Algebra & Discrete Structures) — roadmap order E → F → G → H → J → K.

## 2026-07-28 — D4 · complex analysis (residue / contour / Laurent / re-im)

**Done — 4 new compute tools (89 total):**

- `residue` (Res(f, z₀); pole may be complex), `contour_integral` (∮ = 2πi·Σ Res over the
  enclosed poles the caller supplies — the residue theorem), `laurent_series` (expansion
  with negative powers), `complex_parts` (→ `{real, imag}`).
- Parser: `I` (imaginary unit) added to `_CONSTS` — ADR-0021 extended. Safe: the only `I`
  in tests is an eigenvalue OUTPUT assertion (unaffected); no input used `I` as a variable.
- Wired router + MCP (89 tools) + CLI (`residue`/`contour`/`laurent`/`complex-parts`) +
  `tests/test_complex.py` (13) → **656/656 green**.

**Verified:** Res(1/z,0)=1, Res(1/(z²+1),I)=−I/2, residue at a regular point = 0 (correct,
not an error); ∮1/(z²+1) enclosing I = π (residue theorem), both poles → 0; Laurent of
exp(z)/z² has z⁻² and 1/z terms; (2+3i)(1−i) → {5, 1}; e^{iπ} → {−1, 0} (Euler's identity).

**Next:** D5 [S] — analysis hardening (∇×∇f=0, ∇·(∇×F)=0 + numerical checks) → closes Track D.

## 2026-07-28 — D3 · differential equations II (systems / IVP+BVP / classify / PDE)

**Done — 4 new compute tools (85 total):**

- `solve_ode_system` (systems of ODEs), `solve_ode_ivp` (initial **or** boundary
  conditions — one tool covers IVP and BVP), `classify_ode` (SymPy's solution-method
  classification), `solve_pde` (first-order linear via `pdsolve`).
- **Refactor:** extracted a shared `_parse_diffeq(equation, func_names, var_names)` —
  one ODE/PDE parser for the whole family (multiple functions, multiple variables;
  prime `y'`/`y''` **and** the `D(func, var, …)` partial marker). `solve_ode` now uses
  it too (behavior preserved — its 16 tests stay green).
- Wired router + MCP (85 tools) + CLI (`ode-system`/`ode-ivp`/`classify-ode`/`pde`) +
  `tests/test_diffeq.py` (13) → **635/635 green**.

**Verified:** f'=g, g'=-f → sin/cos pair; y''+y=0 with y(0)=0,y'(0)=1 → sin(x) (IVP);
y(0)=0, y(pi/2)=1 → sin(x) (BVP, uses the π constant); classify(y'+y) includes
`1st_linear`/`separable`; u_x+u_y=0 → u=F(x−y).

**Honest wall:** general PDE (heat/wave via separation of variables) is beyond SymPy's
`pdsolve` — those return `COMPUTE_FAILED` rather than a fabricated closed form. Only the
first-order linear class `pdsolve` supports is claimed.

**Next:** D4 — complex analysis (residue, contour integral, Laurent series, evaluation).

## 2026-07-28 — D2 · integral transforms (Laplace / Fourier / Z)

**Done — 5 new compute tools (81 total):**

- `laplace_transform` (ℒ{f(t)}(s)) + `inverse_laplace_transform` (ℒ⁻¹, Heaviside factor),
  `fourier_transform` (ℱ) + `inverse_fourier_transform` (ℱ⁻¹), `z_transform` (unilateral
  Z, closed form + ROC extracted from SymPy's Piecewise).
- Wired router + MCP (81 tools) + CLI (`laplace`/`inv-laplace`/`fourier`/`inv-fourier`/
  `z-transform`) + `tests/test_transforms.py` (14) → **614/614 green**.

**Verified (transform pairs + round-trips):** ℒ{t}=1/s², ℒ{sin t}=1/(s²+1),
ℒ⁻¹{1/s²}=t·H(t); ℒ{e^{3t}}→1/(s−3)→back to e^{3t}; ℱ{e^{−x²}}=√π·e^{−π²k²} and its
inverse round-trips; Z{1}=z/(z−1), Z{aⁿ}=z/(z−a), Z{n}=z/(z−1)².

**Honesty:** when SymPy cannot find a closed form (e.g. ℒ{1/t}), the tool returns
`error`/`COMPUTE_FAILED` — it never passes off an unevaluated `LaplaceTransform(...)` /
`Sum(...)` object as the answer.

**Next:** D3 — differential equations II (ODE systems, higher order, BVP; basic PDE).

## 2026-07-28 — D1 · vector calculus (Track D begins)

**Context:** Started Track D (Analysis & Transforms). D1 = the vector-calculus
differential operators + line integral, complementing the existing `gradient`.

**Done — 5 new compute tools (76 total):**

- `divergence` (∇·F = Σ ∂Fᵢ/∂xᵢ), `curl` (∇×F, 3-D only — honest error otherwise),
  `laplacian` (∇²f = Σ ∂²f/∂xᵢ²; 0 ⟺ harmonic), `directional_derivative` (∇f·û,
  NORMALIZED direction), `line_integral` (∫_C F·dr along a parametrized curve).
- Wired router + MCP (76 tools) + CLI (`divergence`/`curl`/`laplacian`/`dir-deriv`/
  `line-integral`) + `tests/test_vector_calculus.py` (17) → **591/591 green**.

**Verified (identities):** curl(∇f)=0 (conservative field), div of a solenoidal field
= 0, Laplacian of a harmonic function = 0, directional derivative normalizes (dir (3,4)
→ /5), line integral of (y,x) over t↦(t,t²) = 1.

**Parser upgrade (ADR-0021):** `pi`/`E` are now recognized CONSTANTS in the compute
grammar (were free symbols). Surfaced by a circle line-integral returning `sin(4·pi)/2`
instead of `0`. Minimal, expression-parse only; declared variables unaffected; no
existing test used them as input variables. The whole Analysis track needs π and e.

**Honest wall:** surface integrals and the Green/Stokes/Gauss theorems are deferred —
they need region/surface modeling (a larger effort than the differential operators).

**Next:** D2 — integral transforms (Laplace/inverse, Fourier/inverse, Z-transform).

## 2026-07-28 — I5 [S] · I-track hardening → TRACK I DONE 🎉

**Done**

- New `tests/test_i_track_hardening.py` (11): property-based (hypothesis) + determinism +
  fuzz across the Verification Layer II additions. No new features/tools — reliability only.
- **Invariants proven on random input:** the genuine A·B always verifies (perturbed →
  refuted); a linear equation solved by subtract-then-divide is always `DERIVATION_VALID`;
  extended-Euclid Bézout coefficients always verify; a true prime factorization always
  verifies; SymPy's derivative is always accepted by `verify_derivative`.
- **Safety:** `verify_derivation` / `interpret` / `check_certificate` never crash on random
  junk (always a valid status). **Determinism:** same input → same verdict across runs.
- **564/564 green.**

**Milestone:** Track I (Verification Layer II) is COMPLETE — verify_derivation (I3), the I1
claim types, natural-language interpret (I2), and 13 certificate kinds (I4), all hardened.
This is the product's differentiator: MathHead as the deterministic *auditor* of AI reasoning.

**Next:** Track D (Analysis & Transforms) — the roadmap order is D → E → F → G → H → J → K.

## 2026-07-28 — I4 · certificate extension (matrix / number-theory / probability, stdlib)

**Context:** Continued the D–K roadmap at I4 — extend the independent (stdlib-only)
certificate checker (Track C2) to more result types. No new tools: new certificate
KINDS flow through the existing `check_certificate` (router/MCP/CLI unchanged).

**Done — 8 new certificate kinds** (`certificate.py`, exact `Fraction` where possible):

- Matrix: `matrix_product` (A·B == claimed), `matrix_inverse` (A·inv == I),
  `linear_system` (A·x == b). Checking is a matmul — cheaper than solving.
- Number theory: `factorization` (∏ pᵉ == n AND each p prime via stdlib trial division),
  `bezout_gcd` (g = a·x+b·y ∧ g|a ∧ g|b ⟹ g = gcd), `modular_inverse` ((a·inv) mod m == 1),
  `chinese_remainder` (x ≡ residues[i] mod moduli[i]).
- Probability: `expectation` (Σp == 1 ∧ Σ pᵢ·vᵢ == E), exact.

**Honesty at the center**

- **Engine independence preserved:** a subprocess test proves the new kinds still do
  NOT import z3/sympy (stdlib `fractions`/`math`/`ast` only). End-to-end test: SymPy
  inverts a matrix → the stdlib checker independently confirms A·inv == I.
- `factorization` honestly refuses (`error`) if a claimed prime factor exceeds the
  trial-division bound (10¹²) — it will not *assert* primality it cannot check.
- Exact vs numeric surfaced via `exact` (Fraction → exact; float → tolerance).

- `tests/test_certificate.py` +11 (23 total) → **553/553 green**. Regenerated api-reference
  (check_certificate now lists all 13 kinds).

**Next:** I5 [S] — hardening (determinism/property/fuzz sweep across the I-track additions).

## 2026-07-28 — I3 · full derivation proof check (operation-replay justification)

**Context:** After the repo→English conversion, resumed the approved D–K roadmap at I3.

**Done**

- New `verify_derivation(steps, operations)` in `core/verify.py`: audits a multi-step
  derivation by **REPLAYING** each transition's cited operation on the previous line and
  checking (deterministically) that it produces the stated next line. This is the
  **justification audit** — deeper than `verify_steps` (which only asks "are consecutive
  lines equal?"). It answers "does the RULE you cited actually yield this step?".
- **Equation-aware:** steps may be equations (`L == R`) or expressions; an operation on
  an equation applies to both sides. Supported ops: `add`/`subtract`/`multiply`/`divide`
  (value required) + `simplify`/`expand`/`factor`.
- End to end: router + MCP (**71 tools**) + CLI (`check-derivation --ops JSON`) +
  `tests/test_verify_derivation.py` (17) + 2 reason codes (`DERIVATION_VALID`,
  `STEP_UNJUSTIFIED`) in taxonomy/docs → **542/542 green**.

**Honesty at the center**

- Unjustified step → `STEP_UNJUSTIFIED` with `first_bad_step`, the operation cited, what
  it WOULD produce vs. the claimed line, and a counterexample (e.g. `2x+3=7` --subtract 3-->
  `2x=5` is caught; correct is `2x=4`).
- **Domain wall:** multiply/divide by a non-constant (contains the variable) may change the
  solution set → reported as a `domain_caveats` note (still mechanically valid, honestly flagged).
- Guardrails: unknown op / divide-by-zero / missing value → `GUARDRAIL_VIOLATION`;
  wrong operations length / <2 steps / malicious input → `PARSE_ERROR`. No fabrication.

**Also:** fixed a hidden Turkish assert message (`eksik`/`fazla`→`missing`/`extra` in
`test_mcp_layer.py`) that the English-conversion scan missed (no special TR letters).

**Next:** I4 — certificate extension (matrix / number-theory / probability certificates, stdlib).

## 2026-07-28 — Repo language → English (developer-experience hardening)

**Context:** The user requires the project repo language to be English ("proje repo dili
ingilizce olması lazım"). Everything that is prose or user-facing is now English;
structural/identifier layers are untouched.

**Done**

- **Translated to English:** all docstrings, comments, user-facing strings
  (explanation/reason messages), CLI help/labels/metavars, docs (`*.md`), the
  package `description` (PyPI-visible), and data-file prose (`llm_traps.json`
  categories + `_comment` + `llm_error`, `golden.json` `_comment`).
- **Anglicized output dict keys** (for a fully-English API surface):
  `classify` witnesses `doğru_kılan`/`yanlış_kılan` → `true_witness`/`false_witness`;
  frontier `kirmizi_sayisi`/`mavi_sayisi`/`guvercin`/`kutu` →
  `red_count`/`blue_count`/`pigeons`/`holes` (also fixed a latent `"not"`→`"note"` key typo).
- **Fixed source↔test string couplings** exposed by the sweep: proof rule names
  (`ayrık tasım`→`disjunctive syllogism`, `çelişkiden ispat (RAA)`→`proof by
  contradiction (RAA)`, `varoluşsal ...`→`existential ...`, etc.), plus
  `not invertible` / `no inverse` / `no solution` / `parametric` / `dimensions`.
- Regenerated `docs/api-reference.md` from the English docstrings (freshness test green).
- Full suite re-run after every batch → **523/523 green**.

**Kept on purpose (NOT a translation gap):** the **bilingual TR+EN NL input** feature.
`core/nl.py` keeps its Turkish input regex patterns (türev/ifadesinin/göre/…); the TR
input examples in `test_nl.py`, `test_taxonomy.py`, `README.md`, and this log are the
feature being demonstrated/tested, not untranslated prose.

**Honest walls / notes**

- CI gate (`.github/workflows/ci.yml`) is **pytest-only** → green (523).
- `ruff check .` reports **26 pre-existing `E702`** (compact `stmt; stmt` argparse style
  in `cli.py`) — present at HEAD, never a CI gate, author's deliberate style. Left as-is
  to keep this change scoped to the language conversion (no unrelated code churn). Flagged
  here as an optional future cleanup.

**Next:** resume the approved D–K roadmap at **I3** (full derivation proof check).

## 2026-07-28 — I2 · natural language → formal (recognize-or-reject + round-trip)

**Done**

- New `core/nl.py` + `interpret`: rule-based, bilingual (TR+EN) NL→formal.
  **Design principle RECOGNIZE-OR-REJECT** (no guessing — antidote to "wall #2"/
  over-assumption). Round-trip: formal→NL `restatement` ("what I understood", confirm-then-trust).
- End to end: router (1) + MCP (**70 tools**) + CLI (`interpret`) + `tests/test_nl.py`
  (18) + 3 reason_code (UNDERSTOOD/AMBIGUOUS/UNRECOGNIZED) → **523/523 green**.

**Verified (honesty at the center)**

- TR postfix ("x**3 ifadesinin x e göre türevi"), TR GCD postfix, EN prefix — all
  understood; `restatement` restates what was understood.
- **NO GUESSING:** an unrecognized sentence → `UNRECOGNIZED` (interpretation=None); a bare
  expression ("x squared plus one") is rejected; a two-reading input ("factorize 91 is 91
  prime") → `AMBIGUOUS` (candidate list, clarify). The infinity word → oo.

**Note:** MathHead is NOT trying to be a full NL parser (that's the LLM's job + a source
of assumptions); only a transparent, limited, confirmable bridge. Honest scope.

**Next:** I3 full derivation proof check (rule-based).

## 2026-07-28 — I1 · verification layer II (calculus & matrix claims)

**Context:** The user approved the D–K roadmap (option a), in the suggested order (I→D→…→K),
emphasizing "don't break work discipline, quality>speed". First phase: I1.

**Done**

- `core/verify.py` extended: `verify_derivative`, `verify_integral`, `verify_limit`,
  `verify_series`, `verify_matrix_identity`. Reused the shared deterministic `_equal_verdict`
  (ADR-0020); NO new reason_code (EQUAL/NOT_EQUAL/UNDECIDED).
- End to end: router (5) + MCP (**69 tools**) + CLI (`verify-derivative/integral/
  limit/series/matrix`) + `tests/test_verify_calculus.py` (20) → **505/505 green**.

**Verified (honest edge cases)**

- On a wrong derivative/limit/series, `details.correct` gives the correct value.
- **integral +C honesty:** `∫2x = x²+5` is also valid (differentiate-and-compare →
  the constant difference is tolerated). `verify_matrix_identity` catches symbolic cases
  (`a+a=2a`), reports dimension/first-differing-cell. Malicious input is rejected.

**Next (suggested order):** I2 natural language→formal (🔴). Note: I2 targets "wall #2"
directly; with a careful + honest round-trip.

## 2026-07-28 — Track C4 · LLM-trap benchmark (ALL OF C DONE 🎉)

**Done**

- `benchmarks/llm_traps.json` (14 traps) + `benchmarks/run.py` harness +
  `tests/test_benchmark_traps.py` (regression fence) + `docs/benchmark-results.md`.
- Traps → MathHead adjudicates: missing/wrong solution, wrong identity, domain
  trap, wrong inequality, root branch, faulty step, primality, arithmetic, modular,
  Diophantine. → **477/477 green**.

**Differentiating (measured)**

- **Catch rate 100% (14/14).** MathHead catches every classic LLM error pattern with the
  correct corrective verdict.
- **NO false positives:** the "true_positive" control (`sin²+cos²=1`) is not flagged as
  wrong — we don't just catch errors, we also don't break correct answers.
- **HONEST framing:** a reproducible demonstration (MathHead's adjudication accuracy),
  NOT a live LLM A/B — that's work the user would run with a real model.

**🎉 TRACK C (the differentiating direction) DONE:** C1 verifier · C2 independent certificate ·
C3 cross-check · C4 benchmark. Engine: **64 MCP tools, 477 tests.** MathHead is now
"the independent judge of AI reasoning" — it catches errors, its certificate is verified
independently of the solver, it cross-confirms with two engines, and its edge is measured.

**Next (on the user):** productization (PyPI 0.2.0 / release / tutorial) or a call for
a new direction.

## 2026-07-28 — Track C2 · INDEPENDENT CERTIFICATE checker ("don't trust us")

**Done**

- New `mathhead/certificate.py` (deliberately OUTSIDE `core`) + `check_certificate`:
  re-verifies a result independently of the engine that PRODUCED it, using only the
  **stdlib** (`ast`+`fractions`) → `verified`/`refuted`. Exact when possible (Fraction),
  otherwise numeric (float+tolerance, `exact=false`, honest).
- End to end: router (1) + MCP (**64 tools**) + CLI (`check-certificate`, JSON) +
  `tests/test_certificate.py` (13) + new status `verified/refuted` + 2 reason_code.
  → **461/461 green**.

**Differentiating (evidence)**

- **INDEPENDENCE PROVEN VIA SUBPROCESS:** after `import mathhead.certificate`,
  `z3`/`sympy` are NOT in `sys.modules`. The checker is genuinely engine-independent.
- End-to-end loop: Z3 solves subset_sum → the witness is `verified` in the independent checker.
  Kinds with exact arithmetic: `x²-x @ ½ = -¼ < 0` (inequality counterexample), `2x≠3x @1`.
- Honesty: transcendental (`sin(x)@0`) → numeric, `exact=false`; malicious → rejected.

**Next (Track C):** C4 benchmark (LLM-trap set + measured edge). The LAST C.

## 2026-07-28 — Track C3 · cross-check (Z3 ⋈ SymPy) + determinism fix

**Done**

- New `core/crosscheck.py` + `cross_check`: verifies an equivalence claim INDEPENDENTLY
  with Z3 and SymPy; reports consensus/disagreement/single-engine.
- End to end: router (1) + MCP (**63 tools**) + CLI (`cross-check`) +
  `tests/test_crosscheck.py` (7) + 5 new reason_code (taxonomy). → **447/447**.

**Differentiating (empirical)**

- Identity `(x+1)²=x²+2x+1` → **CONSENSUS_EQUAL** (both engines agree).
- **Domain trap** `(x²-1)/(x-1)` vs `x+1` → **ENGINES_DISAGREE** (SymPy 'equal',
  Z3 'not_equal' at x=1) — two independent witnesses exposed the subtle issue.
- Transcendental `sin²+cos²=1` → **SINGLE_ENGINE** (Z3 doesn't support it, honest).

**BUG→FIX (determinism, ADR-0020):** `.equals()` does internal random sampling
(`sqrt(x²)` vs `x` varied between calls). The equivalence decision was purged of `.equals()`
→ shared deterministic `verify._equal_verdict` (simplify + fixed-point counterexample).
`verify_equality`/`verify_steps`/`cross_check` share it; 10/10 stable.
The core principle (determinism) was preserved and the verdict got stronger (with counterexample).

**Next (Track C):** C2 independent certificate · C4 benchmark.

## 2026-07-28 — Track C1 · VERIFICATION LAYER (differentiating direction — AI reasoning auditor)

**Direction decision:** The user said "focus on what sets us ahead" → the choice: get ahead
on **trust**, not raw compute. A verification layer that turns the product from "just another
CAS" into an independent *judge* of AI claims (ROADMAP Track C).

**Done**

- New module `core/verify.py` + `VerifyResult`: `verify_equality`,
  `verify_solution`, `verify_steps`.
- End to end: router (3) + MCP (**62 tools**) + CLI (`verify-eq/verify-solution/
  verify-steps`) + `tests/test_verify.py` (15) → **438/438 green**. 10 new
  reason_code added to the taxonomy + api-reference.

**Verified (differentiating features = what naive checking misses)**

- **DOMAIN trap:** `(x²-1)/(x-1)` vs `x+1` → `EQUAL_ON_COMMON_DOMAIN` + `x=1`
  divergence warning (symbolically "equal" but undefined at x=1 — caught).
- **COMPLETENESS:** `x²=4, {2}` → `SOLUTION_INCOMPLETE` (-2 missed); `{2,3}` →
  `SOLUTION_INCORRECT` (3 is wrong); `x+sin(x)=0, {0}` → `COMPLETENESS_UNKNOWN`
  (the value is correct but not all can be verified — honest).
- **STEP:** `(x+1)²=x²+1` → `STEP_INVALID` at the first transition + counterexample x=1.

**Next (Track C):** C2 independent certificate · C3 cross-check (Z3⋈SymPy) ·
C4 benchmark. The user approved the direction ("let's not drift from the goal").

## 2026-07-28 — Phase 11 [S] · big hardening + RC (LAST PHASE — 1–11 DONE 🎉)

**Done**

- **Live MCP integration test** (`tests/test_mcp_live.py`): starts the server as a REAL
  subprocess over `stdio`, handshakes with an MCP client, lists 59+ tools, and calls tools
  from 5 layers, verifying the JSON response. Todo T8 (live stdio) is effectively closed.
- **Contract check** (`tests/test_contract.py`, 59): EVERY tool conforms to the
  `status + reason_code + explanation + meta(elapsed_ms)` contract — a machine check
  (breaks if one violates it).
- **Version freeze (RC):** `0.1.0 → 0.2.0` (pyproject + `__init__`); CHANGELOG
  finalized as `[0.2.0] — 2026-07-28`. Ruff cleanup (13 auto-fixes). → **417/417 green**,
  87% coverage.

**Verified**

- The full stack works end to end: subprocess → JSON-RPC → FastMCP → router →
  Z3/SymPy. "Live stdio connection" is now test-assured.
- All of phases 1–11 are done: **24→59 tools, 146→417 tests.** The engine stands solid
  on three legs (logic/Z3 · compute/SymPy · Track B/SAT).

**Next (on the user):** productization — PyPI publish (0.2.0), GitHub release,
tutorial. The engine side is done in the ROADMAP; a new direction depends on the user's call.

## 2026-07-28 — Phase 10 · Track B extension + verifiable certificate

**Done**

- 2 new NP-complete reductions: `graph_coloring` (graph k-coloring), `subset_sum`.
- **Verifiable certificate:** the `sat` witness is re-checked INDEPENDENTLY of Z3, in
  pure Python → `meta.verified=true`. If the check fails, an `UNEXPECTED_SAT`
  error (an encoding-bug fence).
- End to end: router (2) + MCP (**59 tools**) + CLI (`graph-coloring/subset-sum`) +
  `tests/test_frontier.py` (+8) → **357/357 green**. API ref + taxonomy + mcp-layer
  up to date.

**Verified (honest walls, empirical)**

- K3 → 3 colors sat (verified), 2 colors unsat; K4 → 3 colors unsat (chromatic 4).
  `subset_sum([3,34,4,12,5,2],9)` → `{3,4,2}` (verified); `→100` unsat.
- **HONEST ASYMMETRY:** an independent DRAT/LRAT certificate for `unsat` needs a
  DIMACS+drat-trim pipeline → documented as a WALL in `docs/track-b-results.md`. Positive
  evidence is verified independently of the solver; negative evidence is Z3's decision (DRAT is future work).

**Next:** Phase 11 [S] — live MCP integration test + contract check + version freeze (RC). LAST PHASE.

## 2026-07-28 — Phase 9 · inequality proof & nonlinear (Z3 NRA)

**Done**

- New module `core/inequality.py`: a nonlinear ast→Z3 translator (Real, `**` polynomial,
  comparisons + connectives) + 3 operations: `prove_inequality`, `prove_nonnegative`,
  `find_real_solution`. Method: `∀x.P(x)` → `¬P(x)` UNSAT (proof-by-refutation).
- End to end: router (3) + MCP (**57 tools**) + CLI (`prove-inequality/
  prove-nonnegative/real-solve`) + `tests/test_inequality.py` (15) →
  **345/345 green**. API reference + taxonomy + mcp-layer tests updated.

**Verified (honest walls, empirical)**

- **AM-GM** `x²+y²≥2xy` → valid; `x²+1≥2x` → valid; under assumptions `x>0,y>0 ⊨
  x+y>0` → valid. False `x²≥x` → counterexample `x=0.5`. Circle∩line → real
  solution `±√2/2`; `x²=-1` → no real solution.
- Honesty: non-bool target / variable exponent (non-polynomial) / malicious → rejected;
  NRA `unknown` is first-class. No new reason_code (taxonomy fixed).

**Next:** Phase 10 — Track B extension + verifiable UNSAT certificate (DRAT/LRAT).

## 2026-07-28 — Phase 8 [S] · hardening-3 (coverage + API ref + benchmark fence)

**Done**

- **Coverage:** `pytest-cov` + `[tool.coverage]` (branch). `tests/test_mcp_layer.py`
  (55): calls the 54 MCP tools end to end (in-process) + keeps them in sync with the
  registered set (breaks when a new tool is added). Coverage **85% → 87%**; `mcp_server.py`
  67%→97%, `router` 82%→98%.
- **Auto API reference:** `scripts/gen_api_reference.py` generates `docs/api-reference.md`
  (54 tools) from the MCP-registered tools; `test_api_reference.py` enforces freshness
  (single source of truth = the registered tools).
- **Benchmark fence:** a generous 10 s upper-bound test for catastrophic slowdown
  (catches O(2^n)/hang, not timing jitter). → **330/330 green**.

**Verified**

- The coverage gain is genuine: the MCP wrappers are now tested end to end (correctly wired
  to the router). The remaining uncovered lines are mostly rare error branches.
- The API reference is generated deterministically (registration order); docs = code.

**Next:** Phase 9 — inequality proof & nonlinear (Z3 NRA + SOS).

## 2026-07-28 — Phase 7 · probability & statistics (mean/var/std/median + distribution)

**Done**

- 5 new operations: descriptive `mean`, `variance` (population/sample), `standard_deviation`,
  `median` (exact/rational) + a unified `distribution` (sympy.stats, 7 distributions).
- End to end: router (5) + MCP (**54 tools**) + CLI (`mean/variance/std/median/
  distribution`) + `tests/test_statistics.py` (15) → **273/273 green**.

**Verified (honest walls, empirical)**

- mean=5, population var=4, sample var=32/7, std=2, median 9/2 (exact fraction).
- `binomial(10,½)@3` → E=5, Var=5/2, cdf=11/64, pmf=15/128; `normal(μ,σ)` symbolic
  → E=μ, Var=σ²; `P(Z≤1.96)` exact (erfc), ≈0.975.
- Honesty: symbolic data / unknown distribution / wrong parameter count → rejected.

**Next:** Phase 8 [S] — coverage + benchmark regression fence + documentation consolidation.

## 2026-07-28 — Phase 6 · multivariable analysis (grad/Jacobian/Hessian/∫/Σ/Π/ODE)

**Done**

- 7 new operations: `gradient`, `jacobian`, `hessian`, `definite_integral`,
  `summation`, `product`, `solve_ode` (ODE, `dsolve`).
- A safe mini-parser for `solve_ode`: `y'`/`y''` (prime marks) → `D(y,k)` →
  `Derivative`; `=`→`==`; non-whitelisted name/call is rejected.
- End to end: router (7) + MCP (**49 tools**) + CLI (`gradient/jacobian/hessian/
  defint/sum/product/ode`) + `tests/test_multivariable.py` (16) → **258/258 green**.

**Verified (honest walls, empirical)**

- `∇(x²y+sin y)=[2xy, x²+cos y]`; Hessian symmetric; `∫₀³x²=9`, `∫₀^∞e^{-x}=1`;
  `Σ_{1}^{n} i = n²/2+n/2` (closed form); `Π_{1}^{5} i = 120`.
- ODE: `y'=y → C1·e^x`; `y''+y=0 → C1 sin+C2 cos`; `y'=xy → C1·e^{x²/2}`.
- Honesty: unsolvable ODE (`y''=y²x`) → COMPUTE_FAILED; malicious/undefined →
  rejected.

**Next:** Phase 7 — probability & statistics (distributions, expected value/variance).

## 2026-07-28 — Phase 5 [S] · hardening-2 (taxonomy + golden + benchmark)

**Done**

- **Error taxonomy:** `docs/error-taxonomy.md` — the canonical list of all `status`/`reason_code`
  values. `tests/test_taxonomy.py` (4): scans 44 representative calls, enforces every code
  against the documented set + the "error → no fabricated result" invariant.
- **Golden fixtures:** `tests/fixtures/golden.json` (32 scenarios) + a data-driven
  `tests/test_golden.py` — a fence against silent breakage of known outputs.
- **Benchmark:** `scripts/benchmark.py` (baseline, no time threshold) + a smoke
  test. → **242/242 green**.

**Verified**

- Baseline (N=15, median): the slowest is `recurrence` ~43ms, `pigeonhole` ~8ms,
  the rest <4ms. Number theory <0.1ms.
- A false alarm was debunked: the `classify('or(...)')` "error" was actually invalid grammar
  (`or` is infix in Python); the correct form `p or not(p)` → tautology. The tool is sound.
- No new tool/CLI (deliberate hardening). The API surface stays fixed at 42 tools.

**Next:** Phase 6 — multivariable analysis (gradient/Jacobian/Hessian/definite
integral/series sum/ODE).

## 2026-07-28 — Phase 4 · combinatorics & discrete (perm/comb/factorial/partition/recurrence)

**Done**

- 5 new operations: `permutations`, `combinations`, `factorial`, `partition_count`,
  `solve_recurrence` (linear recurrence closed-form, `rsolve`).
- A safe mini-parser for `solve_recurrence`: `func(...)` calls + `var`
  + arithmetic; `=`→`==` normalization; non-whitelisted name/call is rejected.
- End to end: router (5) + MCP (**42 tools**) + CLI (`perm/comb/factorial/
  partitions/recurrence`) + `tests/test_combinatorics.py` (18) → **205/205 green**.

**Verified (honest walls, empirical)**

- `P(10,3)=720`, `C(10,3)=120`, `10!`, `p(10)=42`, `p(100)=190569292`.
- **Fibonacci** `y(n)=y(n-1)+y(n-2)` → Binet closed form; `Fib(10)=55` verified by
  substitution. `y(n)=2y(n-1)` → `2**n`.
- Honesty: nonlinear `y(n)=y(n-1)**2` → no closed form (COMPUTE_FAILED);
  `k>n` → 0; malicious/undefined name → rejected.

**Note (bug→fix):** `ast.parse(mode="eval")` didn't accept `=` (assignment). A single `=`
was normalized to `==` → the Compare handler took over. Caught empirically.

**Next:** Phase 5 [S] — error taxonomy + golden fixtures + benchmark skeleton.

## 2026-07-28 — Phase 3 · number theory (gcd/lcm/prime/factorize/modinv/CRT/Diophantine)

**Done**

- 7 new operations: `gcd`, `lcm`, `is_prime`, `factorize`, `modular_inverse`,
  `chinese_remainder` (CRT), `linear_diophantine`. Input is safe integers
  (`_parse_int`: ast-whitelist + integer check; "2**10" allowed, no symbols).
- End to end: router (7 tasks) + MCP (**37 tools**) + CLI (`gcd/lcm/isprime/
  factorize/modinv/crt/diophantine`) + `tests/test_numbertheory.py` (18) →
  **187/187 green**. Docs up to date.

**Verified (honest walls, empirical)**

- `factorize(360)=2³·3²·5`; `is_prime(91)=False` (7·13); `CRT([3,5,7],[2,3,2])→23
  (mod 105)`; `Diophantine 3x+6y=9 → (3-2t₀, t₀)`.
- Honesty: `modular_inverse(4,8)` → no inverse (gcd≠1); CRT `[4,6],[1,2]` →
  incompatible; `Diophantine 2x+4y=5` → empty list (gcd(2,4)∤5); `factorize(1)=[]`.

**Next:** Phase 4 — combinatorics & discrete (permutation/combination, binomial,
partition, recurrence).

## 2026-07-28 — Phase 2 [S] · hardening-1 (property + determinism + fuzz)

**Done**

- `tests/test_compute_properties.py` (8 property tests): mathematical invariants for the
  compute layer + parser fuzz + determinism check.
- Invariants: `det(A·B)=det(A)·det(B)`, `det(Aᵀ)=det(A)`, `Ax=b` roundtrip,
  `simplify` idempotent. Fuzz: random/malicious text & malformed matrices → no crash,
  only `ok|error`. → **169/169 green**, stable across 3 hypothesis seeds.

**Verified**

- The security invariant was also verified by property testing: no non-whitelisted
  input runs code / leaks an exception.
- No new tool/CLI (deliberate — this is a hardening phase). The API surface stays fixed.

**Next:** Phase 3 — number theory (gcd/lcm, prime, factorize, modular inverse/CRT,
Diophantine).

## 2026-07-28 — Phase 1 · complete linear algebra (matmul/Ax=b/eigvec/rref/nullspace/LU)

**Done**

- 6 new operations: `matrix_multiply`, `matrix_solve` (Ax=b matrix form),
  `eigenvectors`, `rref` (+pivots), `nullspace`, `lu_decomposition`.
- End to end: router (6 tasks) + MCP (**30 tools**) + CLI (`matmul`/`matsolve`/
  `eigenvectors`/`rref`/`nullspace`/`lu`) + `tests/test_linalg.py` (15) →
  **161/161 green**. Docs up to date.

**Verified (honest walls, empirical)**

- `Ax=b`: unique `{x0:6,x1:4}`; **inconsistent → empty list** (no fabrication);
  **infinite → parametric** `{x0: "3 - x1", x1: "x1"}` + "parametric" in the explanation.
- matmul dimension mismatch (`A.cols≠B.rows`) → error; nullspace full-rank → trivial
  (empty); LU → L lower/U upper triangular. Eigenvectors sorted by eigenvalue (determinism).

**Next:** Phase 2 [S] — determinism check + property test expansion +
parser fuzz. (Target: autonomous up to Phase 11.)

## 2026-07-28 — linear algebra / matrix (det / inverse / eigenvalues / rank)

**Done**

- A matrix core in the compute layer: `determinant`, `matrix_inverse`,
  `eigenvalues` (+ algebraic multiplicity), `matrix_rank`. Input `list[list[str]]`,
  each cell filtered through the ast-whitelist → symbolic cells allowed.
- End to end: `router` (4 new tasks) + MCP (**24 tools — four new**) + CLI
  (`det`/`inverse`/`eigenvals`/`rank`, MATLAB-style `"1,2;3,4"` string) +
  `tests/test_matrix.py` (18 tests) → **146/146 green**. Docs up to date.

**Verified (honest walls, empirical)**

- `det[[a,b],[c,d]] = a*d - b*c` (symbolic works); `inv[[1,2],[3,4]] =
  [[-2,1],[3/2,-1/2]]`; the rotation matrix's eigenvalues `±i` (complex, exact form);
  in a defective matrix the single eigenvalue has **multiplicity 2** (not hidden).
- **Honesty:** a singular matrix (`[[1,2],[2,4]]`, det=0) → no fabricated inverse,
  `COMPUTE_FAILED` + "not invertible" message. A non-square determinant → rejected.
- The security invariant is preserved: `__import__` in a cell → rejected.
- Determinism: eigenvalues sorted by `value` → stable across calls (ADR-0019).

**Next (future session):** matrix multiplication + `Ax=b` (linear system matrix
form) + eigenvector; or deepening the proof/logic side.
(Product/PyPI is the user's evening.)

## 2026-07-28 — calculus & systems (limit / series / solve_system)

**Done**

- The compute layer (SymPy) expanded: `limit` (finite/infinite point + one-sided `+`/`-`),
  `series` (Taylor expansion to `order`-th order around a point, `removeO`),
  `solve_system` (multivariable system; linear + nonlinear).
- Wired end to end: `router` (3 new tasks) + MCP (**20 tools — three new**) +
  CLI (`limit`, `series`, `solve-system`) + `tests/test_calculus.py` (18 tests)
  → **128/128 green**. Docs: `mcp-api.md`, `README.md`, `CHANGELOG.md` up to date.

**Verified (honest walls, empirical)**

- `lim x→0 sin(x)/x = 1`, `lim x→∞ 1/x = 0`, `lim n→∞ (1+1/n)^n = e` (a known
  constant reproduced); `exp(x)` 5th-order Taylor correct.
- `solve_system` is **honest**: a contradictory system → empty list (no fabrication); nonlinear
  (circle ∩ line) → two solutions; free variable → parametric.
- The security invariant is preserved: a non-whitelisted call (`__import__`) is rejected.

**Next (future session):** linear algebra (matrix) — determinant, eigenvalue,
inversion. (Product/PyPI is the user's evening.)

## 2026-07-28 — logical equivalence & classification

**Done**

- `logic.equivalent` (A ≡ B; equivalent if `a XOR b` is UNSAT) + `logic.classify`
  (tautology / contradiction / contingent). Router + MCP (**17th tool — two new**) + CLI
  (`equiv`, `classify`) + tests → **110/110 green**.
- For `not_equivalent`, a differentiating witness; for `contingent`, a true + false witness.

**Next (future sessions):** logical equivalence/classification; performance; (product is your evening).

## 2026-07-28 — hardening: property-based tests (hypothesis)

**Done**

- `tests/test_properties.py`: invariants over random formulas with `hypothesis` —
  never crashing, `A⊨B ⟺ {A,¬B} inconsistent`, self-entailment, `enumerate ⟺ consistency`,
  derivation soundness. Added `hypothesis` as a dev dependency.
- **Property testing caught a REAL weakness:** the witness (model) could vary between
  calls (multiple valid models). The determinism claim was made precise:
  **the verdict is guaranteed, the witness is an example** (ADR-0019); don't-cares were
  pinned to a canonical default. `PRINCIPLES` / `Plan` updated.
- **103/103 green** (including 7 property tests).

**Next (future sessions):** logical equivalence/classification; performance.

## 2026-07-28 — MaxSAT (soft/weighted constraints)

**Done**

- `logic.max_satisfy` + `MaxSatResult`: satisfy the mandatory (hard) constraints and satisfy
  the MOST (weighted) soft constraints (`z3.Optimize.add_soft`). Router + MCP
  (**15th tool**) + CLI (`mathhead maxsat`) + tests → **96/96 green**.
- Weighted selection verified (the heavier constraint is preferred); if `hard` can't be satisfied, unsat.
- New decision: ADR-0018.

**Next (future sessions):** logical equivalence/classification; performance;
(product/release in the evening, on you).

## 2026-07-28 — optimization (Z3 Optimize / MaxSMT)

**Done**

- `logic.optimize` + `OptimizeResult` + `translate.translate_objective`: max/min a numeric
  objective under constraints (`z3.Optimize`). Router + MCP (**14th tool**) + CLI
  (`mathhead optimize`) + tests → **90/90 green**.
- Honest edge cases: `unbounded`, `unsat` (infeasible), open-bound
  (ε — supremum/infimum not exactly attainable).
- New decision: ADR-0017.

**Next (future sessions):** logical equivalence/classification; performance;
(product/release in the evening, on you).

## 2026-07-28 — model enumeration (all-SAT)

**Done**

- `logic.enumerate_models` + `ModelSet`: count the DISTINCT models satisfying a formula
  (via blocking clauses). The `exhaustive` flag is honest: all of them, or a limit.
- Router + MCP (**13th tool**) + CLI (`mathhead enumerate`) + tests → **84/84**.

**Honesty:** Over an infinite domain (unbounded Int/Real) `exhaustive=False` — "there
could be more" is stated explicitly.

**Next (future sessions):** logical equivalence/classification; performance;
(product/release in the evening, on you).

## 2026-07-28 — v3.2 · existential (∃) reasoning in the proof generator

**Done**

- `core/proof.py`: **∃-elimination** (a fresh witness constant; `∀`-elimination uses it too) +
  **∃-introduction** (goal `∃x.ψ`, if `ψ[t]` was derived). Context/witness management.
- Inferences like `∃x P(x), ∀x(P→Q) ⊨ ∃x Q(x)` step by step. Tests + regression
  → **78/78 green**.
- New decision: ADR-0016. The classical FOL natural-deduction fragment is largely complete.

**Honesty:** Arithmetic derivation and some mixed quantifier patterns are still absent →
Z3's decision is retained (without steps).

**Next (future sessions):** exporting the proof to LaTeX/text; performance;
(release in the evening, on you).

## 2026-07-28 — v3.1 · proof generator extended (RAA + MT/DS)

**Done**

- `core/proof.py` rule set: modus tollens, disjunctive syllogism, double negation,
  De Morgan; + a second strategy, **proof by contradiction (RAA)** → indirect proofs like
  proof by cases come out step by step.
- Tests (MT / DS / RAA / De Morgan) + regression → **76/76 green**.
- New decision: ADR-0015.

**Honesty:** Existential (∃) elimination and arithmetic derivation are still absent → Z3's decision
is retained (without steps).

**Next (future sessions):** ∃-elimination; GitHub release + PyPI (in the evening, on you).

## 2026-07-28 — v3 · proof generation (step by step) (same session)

**Done**

- `core/proof.py`: entailment + WHY. (1) minimal premise core (unsat core),
  (2) forward-chaining **natural deduction** derivation (modus ponens, ∧-elimination,
  iff, universal instantiation). Classical syllogism step by step.
- New MCP tool `prove` (**12th tool**) + CLI `mathhead prove` + tests → **72/72**.
- New decision: ADR-0014.

**Honesty:** The deriver is limited to the propositional + predicate + universal fragment;
for arithmetic / `or`-`not` / existential no derivation can be built → Z3's decision is retained,
without steps (it says "no derivation").

**Next (future sessions):** extending the deriver (or-elim, existential);
GitHub release; PyPI (from your home).

## 2026-07-28 — Optimization attempt · symmetry breaking (honest: mixed result)

**Done**

- Color-symmetry breaking added to `frontier` (optional `symmetry_break`; correctness
  locked to tests). Measurement: it sped up small/UNSAT cases; **slowed down SAT**
  (S(4)=44: 35s → 48s); W(2,5) at 2 colors unchanged (factor 2).
- **Honest result:** naive symmetry breaking did NOT get past the wall (S(4)=45, W(2,6)) →
  default is **off**. The real wall needs research-grade SAT techniques.
  Detail: `docs/track-b-results.md`.

**Next (future sessions):** productization (PyPI); different speedup techniques.

## 2026-07-28 — Track B · Schur numbers (known values reproduced)

**Done**

- `frontier.schur_number_coloring`: r-color sum-free partition of {1..n}. Router + MCP
  (**11th tool**) + CLI (`mathhead schur n r`) + tests → **65/65 green**.
- Honest attack: S(2)=4, S(3)=13 reproduced **exactly** (n=5, n=14 impossibility
  proofs); for S(4), S(4) ≥ 44 was verified (n=44 sat, ~25 s), the upper bound (n=45)
  hit the wall. Detail: `docs/track-b-results.md`.

**Honest result:** S(5)=160 and the open S(6) are unreachable in this environment. No false victory.

**Next (future sessions):** PyPI package; scale/solver; v3 proof generation.

## 2026-07-28 — Track B · van der Waerden (known values reproduced)

**Done**

- `frontier.van_der_waerden_coloring`: an r-color coloring of {1..n} with no monochromatic
  k-term arithmetic progression. Router + MCP (**10th tool**) + CLI
  (`mathhead vdw n k`) + tests → **61/61 green**.
- **An honest attack on the open-problem class** (user request): the engine **reproduced**
  the values W(2,3)=9, W(2,4)=35, **W(2,5)=178** with the SAME SAT method
  (each a genuine impossibility proof; W(2,5) ~61 s). Detail + honest
  compute-wall: `docs/track-b-results.md`.

**Honest result:** No open problem was SOLVED (W(2,6)=1132 and the open W(2,7) are beyond
this environment). But research values were produced verifiably and the location of the
wall was shown transparently. No false victory.

**Next (future sessions):** PyPI package; scale/solver improvement; v3 proof generation.

## 2026-07-28 — CLI · terminal interface (same session)

**Done**

- `mathhead` CLI (argparse): entail / consistent / model / simplify / solve /
  diff / integrate / pigeonhole / pythagorean; `--json`; meaningful exit codes
  (0 result, 1 error, 2 unknown). A thin shell wired to the same `router`.
- `pyproject` script entry (`mathhead`); README + CI badge. → **56/56 green**.

**Next (future sessions):** PyPI package, function terms, v3 proof generation.

## 2026-07-28 — v1.2 · predicates + individuals (same session)

**Done**

- `translate`: a third sort `U` (individual) + uninterpreted predicates (`Man(x)`, `Loves(a,b)`).
- The classical syllogism works: `∀x.(Man(x)→Mortal(x))`, `Man(socrates)` ⊨ `Mortal(socrates)`.
- Name-collision / arity / argument-sort checks (rejects cleanly). NO new MCP tool
  (the language got richer; the existing 3 logic tools cover it).
- Tests: syllogism + relational + contradiction + guardrail → **51/51 green**.
- New decision: ADR-0013.

**Decision:** In v1.2 predicate arguments are individuals only; function terms (`f(x)`)
go to the next release. Predicates+quantifiers increase undecidability; `unknown` is possible,
soundness is preserved.

**Next (future sessions — no rush):** uninterpreted function terms;
v3 proof generation; deepening Track B (graph coloring/Schur); productization
(PyPI package, CLI, README badges, usage guide).

## 2026-07-28 — v2.1 · Track B seed (same session)

**Done**

- `frontier/`: demos of reducing a problem to SAT — Boolean Pythagorean
  coloring + pigeonhole impossibility proof.
- 2 MCP tools (**9** total). Tests: **independent verification** of the generated coloring
  (no monochromatic triple) + PHP proof → **42/42 green**.
- New decision: ADR-0012.

**Decision:** The Track B "method" works (reduction → Z3). Honesty: small scale;
not the famous results themselves, but the same method. The external contract did NOT change.

**Next:** scale/CDCL limits, more reductions (graph coloring, Schur),
or v1.2 (predicate symbols).

## 2026-07-28 — v2 · compute layer (SymPy) (same session)

**Done**

- `compute/`: ast-whitelist → SymPy translator (NO `sympify`/`eval` — security).
- 4 operations: `simplify`, `solve`, `differentiate`, `integrate` + `ComputeResult`.
- `router` routes compute tasks; 4 new tools in MCP (**7** total).
- Tests: compute + security (`__import__` / rejection of unknown functions) →
  **37/37 green**.
- New decision: ADR-0011.

**Decision:** Compute is a layer separate from logic; input is still whitelisted. If SymPy
can't solve in closed form, an honestly unevaluated result. The external contract (existing tools)
did NOT change.

**Next:** Track B seed (reducing a combinatorial problem to SAT) / T9.

## 2026-07-28 — v1.1 · quantifiers + Real (same session)

**Done**

- `translate` split into two passes (infer/sort + build); scope management.
- `forall(x, …)` / `exists(x, …)`: bound-constant mangling → no variable capture.
- Real number support: if there's a decimal constant, numeric domain = Real (otherwise Int).
- `logic` now uses `translate_all` (shared context + correct domain).
- The Real model value is read (`3/2` → `1.5`).
- Tests: quantifier + Real + capture + **soundness** (never a wrong answer under ∀∃;
  `unknown` if needed) → **25/25 green**.
- New decision: ADR-0010.

**Decision:** Quantifiers weaken decidability; `unknown` is first-class, **soundness**
is preserved. The external contract (ReasoningResult, MCP) did NOT change.

**Next:** T9 (enrich explanation) / v2 (SymPy compute).

## 2026-07-28 — v1 · core works (same session)

**Done**

- `guardrails`: `validate_input` (size/depth/syntax) + `solver_config`
  (fixed seed + timeout → determinism).
- `core/translate`: a Python `ast`-based, whitelisted parser → Z3; sort
  inference (Bool/Int); linearity fence (rejects var*var); chained comparison.
- `core/logic`: `check_entailment` (¬conclusion UNSAT + counterexample), `check_consistency`
  (sat/unsat + **unsat core**), `find_model`. Traceable `meta`.
- `router.route` wires the 3 primitives; `mcp_server` → router → core.
- Tests: best/worst + **determinism (×50)** + guardrail → **17/17 green**.
- Live MCP: 3 tools registered (`entailment`/`consistency`/`model`), clean JSON output.
- New decision: ADR-0009 (ast-based parser + a decidable v1 fragment).

**Decision:** The v1 language is deliberately **decidable** (Presburger + propositions);
Real/∀∃/nonlinear deferred to v1.1+. The external contract (ReasoningResult, MCP signatures)
did NOT change.

**Verified:** `pytest` 17/17; z3 5.0.0; end-to-end route → Z3 → JSON.

**Next:** T9 (enrich explanation) / v1.1 (Real + quantifiers).

## 2026-07-28 — v0.1 · vision correction (same session)

**Changed**

- The goal split into two tracks: **Track A** (verifiable core, near term) +
  **Track B** (attack on hard/open problems, the North Star, v3+). The project owner's
  feedback: solving open problems should also be a first-class goal.
- `Plan.md` §2 rewritten (with SMT/SAT's track record of solving open problems:
  Boolean Pythagorean Triples 2016, Keller dimension 7 2020, Schur 5 2017).
- New decision: `DECISIONS.md` ADR-0008.

**Decision:** Track B scope = problems reducible to satisfiability + proof
verification. The v1 scope did NOT change (still Track A / Reasoning Checker).

## 2026-07-28 — v0 · skeleton & design (this session)

**Set up**

- Project skeleton: `src/mathhead/{core, compute, router, guardrails, server}` + `tests/` + `docs/`
- The return contract `ReasoningResult` frozen: `status / reason_code / explanation / witness / meta`
- MCP server skeleton (FastMCP, 3 tools: `entailment` / `consistency` / `model`) — stub
- Guardrail constants + signatures: `validate_input`, `solver_config`
- Design files: `Plan.md`, `Todo.md`, `Progress.md`, `PRINCIPLES.md`, `DECISIONS.md`
- `docs/`: `architecture.md`, `mcp-api.md`, `glossary.md`
- Tests: `test_smoke` (passes) + `test_logic` (spec, `xfail` for now)

**Architectural decisions** (summary — detail in `DECISIONS.md`)

- ADR-0001: Orchestrating a proven solver instead of a from-scratch FOL engine
- ADR-0002: Logic core = **Z3** (SMT); compute = **SymPy** (CAS)
- ADR-0003: Language = **Python**; MCP SDK = **FastMCP** (`mcp[cli]`)
- ADR-0004: External API/contract **frozen early**

**Verified**

- The core imports cleanly with no external dependency; the `ReasoningResult`
  contract and `is_conclusive()` work as expected.

**Next step:** `Todo` → T1 (guardrails) → T2 (translate) → T3 (entailment).

---

<!-- New entries are added ABOVE this line. Template:
## YYYY-MM-DD — vX · title
**Done** …  **Decision** …  **Verified** …  **Next** …
-->
