# Discovery Engine — Decision Log (ADR)

> Decisions for the math **discovery** engine (`mathhead.discovery`), the subproject that
> builds toward `docs/IDEAL-ENGINE-ROADMAP.md` on top of MathHead's judge spine. Same rule as
> the main `DECISIONS.md`: decisions are recorded with rationale and not silently changed; if
> the thinking changes, open a new ADR that supersedes the old one. Numbered `ADR-D####` to
> stay distinct from MathHead's `ADR-####`.

---

## ADR-D0001 — `discovery` starts as a subpackage of `mathhead` (packaging convenience)

- **Status:** Accepted · 2026-07-29 (Track N, first stone)
- **Context:** The discovery engine is architecturally the layer that *uses* MathHead (the
  judge). A clean long-term layout would make it a sibling package that depends on `mathhead`.
  But the repo is a hatchling src-layout tuned for one package, and fighting packaging on day
  one buys nothing.
- **Decision:** Start `discovery` as `src/mathhead/discovery/` — instantly importable, sharing
  the existing tests/CI/ruff/coverage discipline with zero packaging changes. Tests live in the
  repo's flat `tests/` as `test_discovery_*.py`. Records live in `docs/discovery/`.
- **Consequences:** Fast, honest start with full tooling reuse. The nesting is a *packaging*
  convenience, NOT a claim that discovery is subordinate to the judge — `discovery` will import
  `mathhead` (as its judge) at the refutation/proof tracks (Q/R), never the reverse. If the
  subproject outgrows this, it is promoted to a sibling package `mathdiscovery`; this ADR is
  the record of why it began nested.

---

## ADR-D0002 — Canonical form = degree-refined permutation-minimum (N2)

- **Status:** Accepted · 2026-07-29 (Track N2)
- **Context:** Isomorphism elimination needs a canonical key: identical iff isomorphic. The
  simplest correct key is the minimum adjacency bitmask over all n! vertex relabelings —
  correct but factorial. Degree sequence alone is NOT a valid key (e.g. C6 and 2·C3 share it
  but are not isomorphic).
- **Decision:** Compute the minimum bitmask over relabelings **restricted to those that order
  vertices by degree** (permute only within equal-degree blocks). This is isomorphism-invariant
  because an isomorphism preserves degree, so for isomorphic graphs the degree-consistent
  relabeling sets correspond and yield the same minimum. It collapses the factorial search
  whenever degrees differ, while staying exact (it still distinguishes same-degree-sequence
  non-isomorphic graphs — verified on C6 vs 2·C3).
- **Consequences:** Correct and fast enough for the v0.1 small-n domain (n! only for regular
  graphs). Worst case is still factorial for highly regular graphs; partition-backtracking
  refinement (nauty-style) is the planned N2 optimization, deferred until a real workload needs
  it. Correctness is pinned by the OEIS A000088 count test (see ADR-D0003).

---

## ADR-D0003 — Honest brute-generation bound (n ≤ 7) + OEIS A000088 as the oracle (N1)

- **Status:** Accepted · 2026-07-29 (Track N1)
- **Context:** Generating all non-isomorphic graphs by enumerating 2^(n choose 2) labeled
  graphs is exact but explodes: n=6 → 2^15 (fast), n=7 → 2^21 (slow), n=8 → 2^28 (infeasible).
- **Decision:** `generate_graphs(n)` refuses n > 7 with a clear `ValueError` — an honest wall,
  never a silent cap (mirrors MathHead's core principle). Correctness is pinned against **OEIS
  A000088** (1, 1, 2, 4, 11, 34, 156, …): the generator must reproduce this sequence exactly, a
  strong independent oracle for both generation and canonical labeling.
- **Consequences:** A trustworthy, self-checking "matter" layer from day one. Pushing beyond
  n=7 requires orderly / McKay generation (roadmap N1-opt), which will replace brute
  enumeration rather than raise the brute bound.

---

## ADR-D0004 — Relation discovery via the integer null space, labeled `empirical` (O2)

- **Status:** Accepted · 2026-07-29 (Track O2)
- **Context:** From the invariant feature table we want the engine to *find* the exact relations
  the objects obey (e.g. the Handshake Lemma), not have them hardcoded. Two risks: (1) floating
  point would make a "law" approximate; (2) reporting an empirical relation as if it were a
  proven theorem would violate the project's honesty contract.
- **Decision:** Build the affine feature matrix (numeric invariants + a constant column) over
  the sample and compute its **integer null space** with sympy (exact rationals, scaled to
  primitive integer vectors). Each basis vector is an exact linear law `Σ cᵢ·invᵢ + c₀ = 0`
  holding across every sampled object. Every result is a `DiscoveredLaw` with
  **`status="empirical"`** and a `holds_over` sample description — explicitly a *conjecture*, not
  a theorem. `sum_degrees` was added as a numeric invariant (NOT hardcoding `= 2E`; the miner
  must rediscover that relation). `is_connected` (bool) and `degree_sequence` (tuple) are
  excluded from the linear feature set.
- **Consequences:** The engine rediscovers the Handshake Lemma (`2*num_edges = sum_degrees`) from
  data with no spurious laws (verified for n≤5 and n≤6) — an independent O2 milestone mirroring
  A000088 for N1. The empirical labeling is the honest handoff to the next tracks: a discovered
  law is a conjecture that the counterexample-first track (Q) will attack and, if it survives,
  the judge (R) will prove. Exact arithmetic guarantees a reported law holds exactly on the
  sample. Null-space cost is negligible at this scale; if the invariant set grows large,
  column selection / incremental rank is the planned optimization.

---

## ADR-D0005 — Counterexample-first conjectures: empirical status + minimal counterexample (P0/Q0)

- **Status:** Accepted · 2026-07-29 (Track P0/Q0)
- **Context:** A discovery engine must generate candidate laws AND resist believing them. The
  external note is explicit: the default stance toward a conjecture is to try to KILL it before
  proving it. We also must never present an empirically-observed relation as a theorem.
- **Decision:** `conjectures.py` generates candidates — subclass linear laws (mine O2 laws on a
  predicate-defined subclass, e.g. trees) and inequality bounds `A <= B` between numeric
  invariants that hold on the sample. Every `Conjecture` is `status="empirical"` with an explicit
  `scope`/`claim`. `refute.py` is the DEFAULT action: a counterexample-first bounded scan that
  returns the **minimal** counterexample (smallest n, then fewest edges) if refuted, else
  `no_counterexample_within_bound` — never "proved". Predicates are named closures (not lambdas)
  so tracebacks render and behaviour is inspectable. Generation is memoized by n (deterministic),
  so the refute loop doesn't re-enumerate the same graph sets.
- **Consequences:** The engine visibly earns its beliefs: from n<=5 it proposes 11 plausible
  bounds, then a bounded attack up to n=6 KILLS exactly the one artifact
  (`num_triangles <= num_edges`, minimal counterexample T=16 > E=14 on 6 vertices, K6 minus an
  edge) while the rest survive as bounded-honest. True subclass theorems (`trees: E = V - 1`,
  `trees: num_triangles = 0`) survive the attack. A survivor is `no_counterexample_within_bound`
  — the honest handoff to the judge (R): the algebraically-reducible survivors go to MathHead for
  a real proof; purely combinatorial ones stay empirically-supported until a structural proof is
  added. This ADR deliberately does NOT claim the judge is wired for graph theorems — it is not;
  forcing MathHead where it adds nothing would violate the honesty this project is built on.

---

## ADR-D0006 — The judge bridge: hand expressible survivors to MathHead; be honest about the rest (R)

- **Status:** Accepted · 2026-07-29 (Track R)
- **Context:** Q produces survivors labeled `no_counterexample_within_bound` — empirically
  supported, not proven. The discovery engine needs a JUDGE to reach real verdicts. MathHead is
  that judge, but it only judges what its grammar can express (algebra, arithmetic, FOL) — not a
  purely combinatorial graph law.
- **Decision:** `judge.py` bridges the discovery layer to `mathhead.router.route`. It maps a
  MathHead result to a `Verdict` (`proved` | `refuted` | `unknown` | `not_applicable`) that
  carries MathHead's own `certainty` label, and exposes thin, semantic helpers
  (`judge_induction`, `judge_inequality`, `judge_identity`, `judge_entailment`, `judge_task`). A
  Conjecture may carry an optional `mathhead` task; `judge(conjecture)` submits it, and returns
  **`not_applicable`** when there is none — the honest answer for a combinatorial law, never a
  fabricated verdict. Refutations carry MathHead's witness/counterexample.
- **Consequences:** The first real use of MathHead as the discovery engine's judge. It genuinely
  PROVES (`n(n+1)` even and `n³−n ≡ 0 (mod 3)` by induction → `certainty=formal_proof`; AM-GM by
  Z3 → `solver_verified`) and REFUTES (`x² ≥ x` over the reals → `refuted` with witness x=0.5).
  A graph law comes back `not_applicable`, keeping the honesty contract: the judge upgrades
  `empirical → proved/refuted` only where it truly can. Auto-generating algebraically-expressible
  conjectures (an arithmetic / integer-sequence object domain, so the judge has a stream to
  prove) is the natural next domain — the bridge is now ready for it.

---

## ADR-D0007 — Arithmetic domain: the loop closes end to end (generate → refute → PROVE)

- **Status:** Accepted · 2026-07-29 (arithmetic domain; first closed loop)
- **Context:** In the graph domain the judge (MathHead) mostly returns `not_applicable` — graph
  laws are combinatorial. To exercise the FULL loop with a real proof at the end, we need a domain
  where MathHead is the native judge. Modular arithmetic of polynomials is exactly that.
- **Decision:** `arithmetic.py` runs, for a family of polynomials p(n): (1) **discover** the
  modulus from data as `m = gcd(p(1), p(2), …)` — the largest m dividing every sample, i.e. the
  counterexample-first-optimal claim; (2) **refute** counterexample-first over a larger range;
  (3) **judge** the survivor with MathHead `prove_by_induction`. The induction proof runs under a
  small `timeout_ms` budget (a smaller budget returns `unknown` sooner — honest, since the bound is
  a budget not a lie); the full run is memoized (deterministic).
- **Consequences:** The first fully autonomous generate→refute→PROVE loop. The engine discovers
  true, sometimes-stronger-than-expected facts — `n³−n ≡ 0 (mod 6)` (stronger than mod 3),
  `n⁵−n ≡ 0 (mod 30)` (stronger than Fermat's mod 5) — PROVES the ones whose induction step
  MathHead can decide (`n(n+1) ≡ 0 mod 2`, `n²−n ≡ 0 mod 2` → `certainty=formal_proof`), and returns
  an honest **`unknown`** on the higher-degree ones whose step is beyond Z3 — never a fabricated
  proof. Overshoot moduli (e.g. claiming mod 4 for n(n+1)) are killed with a minimal counterexample
  before the judge. This is the thesis realized end to end: discover, try to kill, prove what can be
  proved, and say `unknown` — out loud — for the rest.

---

## ADR-D0008 — One honest run report across domains (AC2 + provenance)

- **Status:** Accepted · 2026-07-29 (AC2)
- **Context:** The engine now spans two domains (graphs, arithmetic) with a full pipeline. Its
  output was scattered across function returns. The document's research loop asks for a single
  report where "even a failure is a valuable, organized result".
- **Decision:** `report.py` runs the pipeline across both domains and assembles ONE
  `DiscoveryReport` with four honest, mutually-exclusive-by-status sections — **PROVED** (formal,
  by the judge), **REFUTED** (killed, with a minimal counterexample), **DISCOVERED** (empirical,
  holds on the sample, not proven), **OPEN** (survived the attack, unproven). `render()` emits
  readable Markdown with provenance (MathHead version, seed, bounds, determinism note).
  Deterministic (memoized generation + fixed seed → the same report every run).
- **Consequences:** The engine's honesty is now legible at a glance: a reader sees exactly what is
  proved vs merely observed vs refuted vs open, never blurred. This is the consolidation that keeps
  growth orderly — new domains/generators feed the same four honest buckets rather than sprawling.

---

## ADR-D0009 — Spectral invariants: the graph domain's first bridge to MathHead

- **Status:** Accepted · 2026-07-29 (O1 spectral)
- **Context:** So far graph invariants were pure Python; only the arithmetic domain used MathHead
  (induction). Spectral graph theory needs eigenvalues — the natural point to bring the graph
  domain onto MathHead's compute spine — and it unlocks real discoverable identities.
- **Decision:** The spectral MOMENTS Σλ² , Σλ³ are ordinary fast invariants computed as
  trace(A²), trace(A³) by integer matmul (exact, instant); they are added to the registry (NOT to
  the default `NUMERIC_INVARIANTS`, so existing miners are undisturbed). The actual SPECTRUM is
  computed by **MathHead's `eigenvalues` tool** (`spectral.py`, memoized per graph) and used for
  genuinely spectral invariants (`num_distinct_eigenvalues`) and — on-thesis — as an INDEPENDENT
  authority: `spectrum_confirms_moments` checks that MathHead's Σλ^k equals the matmul trace(A^k).
  The eigenvalue power-sum is evaluated to 40 digits and rounded (it is provably an integer =
  trace), avoiding slow symbolic simplification of irrational cubes.
- **Consequences:** First time the graph domain flows through MathHead. `discover_spectral_laws`
  rediscovers real spectral graph theory from data — **Σλ² = 2·num_edges** and
  **Σλ³ = 6·num_triangles** — and MathHead's actual eigenvalues independently confirm those
  moments on every graph n≤5 (the cross-check MathHead was built for). Kept the default miner
  untouched (spectral moments live in a separate list) so growth stays orderly.

---

## ADR-D0010 — Sum-identity generator: discover a closed form from data, prove it by induction

- **Status:** Accepted · 2026-07-29 (P4; second arithmetic generator)
- **Context:** The arithmetic domain had one generator (divisibility). To exercise the judge on
  richer, discover-a-formula problems — and feed the same report buckets — we add sum identities.
- **Decision:** `sequences.py`: for a term f(i), compute partial sums S(n), **fit** a closed-form
  polynomial g(n) by interpolation (the "guess the formula" step, P4), **refute** counterexample-
  first over a range LARGER than the fit, and **prove** the survivor by induction — the base case
  plus MathHead verifying the inductive step g(n) − g(n−1) = f(n) (`verify_equality`,
  `solver_verified`). A non-polynomial sequence (Σ 2^i) fits the sample but diverges beyond it, so
  the extended check refutes it — the engine does not force a formula.
- **Consequences:** A fully autonomous discover→prove loop with real proofs: the engine finds and
  proves `Σi = n(n+1)/2`, `Σi² = n(2n²+3n+1)/6`, `Σi³ = (n(n+1)/2)²`, `Σ(2i−1) = n²`
  (`solver_verified`), and REFUSES the non-polynomial Σ 2^i (refuted, not forced). Wired into
  `run_report`, so the new generator feeds the same four honest buckets without reshaping the
  pipeline — growth stays orderly.

---

## ADR-D0011 — Proof-strategy orchestration: factor the modulus, prove the parts, combine by CRT

- **Status:** Accepted · 2026-07-29 (Track S)
- **Context:** A single induction can't prove `p(n) ≡ 0 (mod m)` for many composite m — Z3's step
  is too hard (n³−n mod 6, n(n+1)(n+2) mod 6 came back `unknown`). But m factors, and the CRT lets
  us combine coprime parts. The engine should try more than one proof route before giving up.
- **Decision:** `strategy.py::prove_modular_divisibility` factors m with MathHead's `factorize`,
  proves each prime power `p^e` by induction (MathHead), and — if ALL parts prove — concludes the
  composite by CRT (`formal_proof`, reason `PROVED_BY_CRT_FACTORING`). The arithmetic loop now
  tries a single induction first and falls back to this strategy (a mini portfolio; records the
  winning `method`). When a part is itself beyond induction it returns `unknown` and NAMES the
  blocking prime power — never a fabricated proof.
- **Consequences:** Two facts that a single induction left open are now genuinely PROVED —
  `n³−n ≡ 0 (mod 6)` and `n(n+1)(n+2) ≡ 0 (mod 6)` (each via 2·3) — lifting the report's PROVED
  bucket from 2 to 4 arithmetic facts. The still-hard ones (n⁵−n mod 30, n⁷−n mod 42, the mod-24
  case) stay honestly `unknown`, now with the blocking part named. First step of the proof-strategy
  orchestrator (S): more than one route, tried in order, honest about the wall.

---

## ADR-D0012 — A first interestingness filter: keep subclass-specific laws, drop restricted-universals

- **Status:** Accepted · 2026-07-29 (Track W0)
- **Context:** A discovery engine can emit a flood of true-but-uninteresting statements. A concrete
  case already in our output: `trees: 2*num_edges = sum_degrees` is just the Handshake Lemma seen
  on trees — it holds on EVERY graph, so it is no discovery ABOUT trees. It cluttered the report.
- **Decision:** `novelty.py::is_subclass_specific` — a subclass law is interesting iff its claim
  FAILS on at least one object in the full sample (so it is genuinely specific to the subclass, not
  a universal law restricted to it). `novel_subclass_laws` filters on this, and `run_report` uses
  it, so the DISCOVERED section keeps only real subclass facts.
- **Consequences:** The report drops the restricted-universals (`trees:`/`forests: 2E = S`) and
  keeps the genuine characterizations (`trees: E = V − 1`, `trees: triangle-free`, `forests:
  V = E + C`). Higher signal, honest, and a first tractable step against the interestingness
  problem the document flags as central — without pretending to have "solved" interestingness.

---

## ADR-D0013 — Real-valued spectral bounds, numerically checked (honest certainty)

- **Status:** Accepted · 2026-07-29 (spectral bounds; also unifies the modular prover)
- **Context:** Spectral graph theory's famous facts are BOUNDS on the largest eigenvalue (spectral
  radius), which is real (often irrational). Exact symbolic comparison proved unreliable — SymPy
  returns some eigenvalues in unsimplified complex-radical forms that won't order. But the moment
  identities were exact; we must not blur the two.
- **Decision:** `spectral_bounds.py` evaluates the spectral radius NUMERICALLY (largest eigenvalue
  from MathHead's spectrum, to 30 digits, real part) and checks candidate bounds counterexample-
  first, labeling every result `certainty="numerical_check"` — strong evidence over the sample, NOT
  a proof. Kept OUT of the default report (its per-graph eigenvalue cost is heavy). Separately, the
  arithmetic prover was unified: `discover_and_prove` always routes through
  `prove_modular_divisibility` (a prime modulus is a single induction; a composite one factors +
  CRT) with a reliable 2500 ms budget — removing a flaky direct-then-fallback race.
- **Consequences:** The engine discovers the classic sandwich **average_degree ≤ spectral_radius ≤
  max_degree** (survives) and REFUTES the plausible `spectral_radius ≤ average_degree` (a 3-vertex
  single edge breaks it: λ=1 > ⅔). Honesty preserved: exact facts stay exact, numerical ones are
  labeled `numerical_check`. The modular prover is now deterministic and fast (~10 s memoized).

---

## ADR-D0014 — A proof portfolio with a COMPLETE fallback: residue exhaustion

- **Status:** Accepted · 2026-07-29 (Track S1)
- **Context:** Induction (even with modulus-factoring + CRT) is incomplete for `p(n) ≡ 0 (mod m)`:
  it left n⁵−n mod 30, n⁷−n mod 42, the mod-24 case as `unknown`. But that class is DECIDABLE — for
  an integer-coefficient polynomial, p(n) mod m depends only on n mod m, so checking all m residues
  is a rigorous, complete proof (a finite case-split on n mod m).
- **Decision:** `strategy.py::prove_by_residues` implements that complete decision procedure. The
  arithmetic loop is now a small **portfolio (S1)**: try the elegant MathHead proofs first
  (induction for a prime modulus, factoring + CRT for a composite), and fall back to residue
  exhaustion, which always finishes. Each finding records the WINNING `method` and an honest
  `certainty` (`formal_proof` for the induction/CRT proofs, `exhaustive_residue_proof` for the
  complete case-split).
- **Consequences:** Every true modular law in the family is now PROVED, each by the appropriate
  strategy — induction (n(n+1) mod 2), modulus-factoring (n³−n mod 6), residue-exhaustion (n⁵−n mod
  30, n⁷−n mod 42). No loss of honesty: the earlier `unknown`s were a weakness of one method, not a
  real wall — the class is decidable and the engine now decides it. The honest walls that remain are
  the genuine ones (combinatorial graph laws → `not_applicable`; truly open problems → `unknown`).

---

## ADR-D0015 — Proof-dependency trees: make a proof's lemmas explicit (T3, a tractable slice)

- **Status:** Accepted · 2026-07-29 (Track T3)
- **Context:** A proof rests on lemmas, but ours were implicit inside the strategy code. Intermediate-
  lemma discovery (T) is largely 🔴 (inventing lemmas), but exposing the lemmas an existing proof
  ALREADY uses is tractable and useful.
- **Decision:** `proof_tree.py::proof_tree` reconstructs a proved arithmetic finding's dependency
  tree from the winning strategy — no extra solver calls, deterministic: a `modulus-factoring` proof
  becomes a CRT node over one `≡ 0 (mod pᵢ^{eᵢ})` induction lemma per prime power; a
  `residue-exhaustion` proof is a complete finite-case leaf; a prime-modulus proof is a single
  induction leaf. `render_tree` prints it.
- **Consequences:** Proofs are now legible as trees — e.g. `n³−n ≡ 0 (mod 6)` visibly rests on
  `mod 2` and `mod 3` lemmas combined by CRT. This is the honest first step of T: it does NOT invent
  lemmas (the open part), it surfaces the ones a proof already depends on, checkably. Deliberately
  scoped small (one module, no new solver load) to stay within budget.

---

## ADR-D0016 — An independent proof checker: don't trust the prover, check the proof (M spirit)

- **Status:** Accepted · 2026-07-29 (Track M1–M3 spirit)
- **Context:** Every proof so far was trusted because the strategy code produced it. The document's
  #1 principle is a small checker nothing can fool: the search/solver may be buggy, but an
  independent checker must catch it. A full Lean-style kernel is out of scope; an independent
  checker for our modular-polynomial proof class is tractable AND complete.
- **Decision:** `checker.py` re-verifies a proof tree by an orthogonal, minimal, stdlib-only method:
  a claim `p(n) ≡ 0 (mod m)` is re-checked at every residue mod m (COMPLETE, independent of how the
  proof was found — even an induction/Z3 proof is re-verified this way); a CRT node additionally
  checks the REASONING (prime-power moduli pairwise coprime, product = m, every lemma checks). It
  REJECTS anything it cannot confirm.
- **Consequences:** The engine's proofs are now independently verifiable — the strongest honest
  status (`independently_verified`, matching MathHead / §14). The checker confirms the real proofs
  (n³−n mod 6 via CRT, n⁵−n mod 30 via residues) and REJECTS both a false claim (n²+1 ≡ 0 mod 4) and
  broken CRT reasoning (children mod 2·3 but goal mod 12). A buggy prover can no longer pass off a
  wrong theorem. Scoped to the modular class (where the check is complete); other classes get an
  independent checker as their proofs mature — the honest, incremental path toward the kernel.

---

## ADR-D0017 — Independent verification is now first-class: every proof is re-checked

- **Status:** Accepted · 2026-07-29 (M3/R — pipeline integration)
- **Context:** The independent checker (ADR-D0016) existed but was standalone. The document's
  principle only bites if the checker is ALWAYS run — a proof nobody re-checks is a proof on trust.
- **Decision:** `discover_and_prove` now, on every proved finding, runs
  `check_proof(proof_tree(finding), fn)` — reconstructing the proof tree and re-verifying it with
  the independent checker — and stores the boolean on `ArithmeticFinding.independently_verified`.
  The report surfaces it (`✓ independently verified`).
- **Consequences:** Every proved arithmetic fact in the engine is now re-verified by a checker that
  is independent of the prover (orthogonal residue method for induction/CRT proofs; a separate
  stdlib implementation for residue proofs), and the CRT reasoning is structurally re-checked. Trust
  is no longer "the strategy said so" but "an independent checker confirmed it" — the honest default,
  visible in the report. A proof the checker could not confirm would ship with
  `independently_verified=False` (a loud signal), never silently.

---

## ADR-D0018 — Graph invariants reach the frontier: χ computed locally, confirmed by MathHead

- **Status:** Accepted · 2026-07-29 (O1 frontier-bridge — coloring)
- **Context:** The graph domain's bridges to MathHead so far were the exact spectral moments and the
  `eigenvalues` tool (linear-algebra spine). The roadmap's frontier tools (Z3/SAT reductions:
  `graph_coloring`, `subset_sum`, …) were unused from discovery. Chromatic number is the natural
  first frontier invariant — NP-hard, but MathHead already has an independently-verified
  `graph_coloring` reduction. Question: compute χ where, and trust which authority?
- **Decision:** Compute χ(g) (and ω) LOCALLY as ordinary exact invariants (backtracking / clique
  search) — cheap and deterministic for the n≤7 regime. Then, in `coloring.py`, INDEPENDENTLY
  CONFIRM that value against MathHead's frontier tool: `verify_chromatic_number` asserts `sat` at χ
  colors AND `unsat` at χ−1. Two orthogonal engines (our search + MathHead's Z3) must agree
  (`solver_verified`); χ≤1 is trivial and skips the solver. Coloring inequalities (`ω ≤ χ ≤ Δ+1`,
  the refuted `χ ≤ Δ`) are mined counterexample-first and labeled `bounded_check` — EXACT over the
  finite sample (integers), distinct from spectral bounds' `numerical_check`. Bridge mechanics:
  `graph_coloring` is 1-indexed, so vertices are shifted +1 and `n` passed explicitly.
- **Consequences:** The engine now spans exact arithmetic → spectral → NP-hard frontier, and the
  frontier invariant is not taken on one engine's word — a backtracking bug and a Z3-reduction bug
  would have to coincide to slip through. Refute-first proved its worth again: it reported the
  single vertex (χ=1 > Δ=0), not the classic triangle, as the minimal counterexample to `χ ≤ Δ` — a
  smaller witness than the human default. Scoped honestly: local χ is only tractable at small n
  (the honest bound of the whole graph domain); larger n would need the reduction as the primary
  compute, not just the confirmer — logged as the natural next frontier step.

---

## ADR-D0019 — Second frontier invariant (Hamiltonicity); scope the false claim to surface a structural witness

- **Status:** Accepted · 2026-07-29 (O1 frontier-bridge — hamiltonicity)
- **Context:** With χ bridged to MathHead's `graph_coloring` (ADR-D0018), the natural next frontier
  invariant is Hamiltonicity — MathHead already ships an independently-verified
  `hamiltonian_path(cycle=True)` reduction. Two wrinkles: (a) `hamiltonian_path` is 0-INDEXED,
  whereas `graph_coloring` was 1-indexed — the bridge code must not blindly copy the +1 shift; (b) a
  Hamiltonian CYCLE conventionally needs n≥3, but MathHead's reduction accepts a degenerate 2-cycle,
  so the two "definitions" diverge for n<3.
- **Decision:** Compute `is_hamiltonian` LOCALLY (backtracking from a fixed start vertex, exact for
  small n), then confirm against MathHead for n≥3 (where the definitions coincide exactly); n<3 is
  decided by convention locally and MathHead is NOT invoked. Mine the implications
  counterexample-first: the necessary conditions (`Hamiltonian ⟹ connected`, `⟹ δ≥2`), Dirac's
  sufficient condition (`n≥3 ∧ δ≥n/2 ⟹ Hamiltonian`), and the plausible-but-false
  `connected ⟹ Hamiltonian`. Crucially, SCOPE that false claim to `n≥3` so its minimal
  counterexample is the 3-path P₃ — a genuine STRUCTURAL witness — rather than the single vertex,
  whose "refutation" would be a pure artifact of the n<3 cycle convention.
- **Consequences:** A second NP-complete invariant is now cross-checked by two orthogonal engines
  (0/53 disagreements up to n≤5), and the engine rediscovered a real theorem (Dirac) from data next
  to the necessary conditions. The scoping decision is a deliberate contrast with ADR-D0018: there,
  refute-first's degenerate K1 witness (χ=1>Δ=0) was itself the honest, convention-free minimal
  counterexample and we embraced it; here, the degenerate n<3 witness would be a convention artifact,
  so we lift the premise to n≥3 to report the structural witness P₃. The principle is consistent —
  report the most honest minimal counterexample — even though it points opposite ways in the two
  cases. `is_hamiltonian` joins the boolean invariants (registry, not NUMERIC_INVARIANTS: it is not
  a linear feature). Local decision is only tractable at small n — the honest domain bound — with the
  reduction as the confirmer, not (yet) the primary compute.

---

## ADR-D0020 — Fold frontier work into the report; keep the epistemic taxonomy pure

- **Status:** Accepted · 2026-07-29 (AC2 — report integration)
- **Context:** ADR-D0018/D0019 added χ and Hamiltonicity as frontier invariants with their own
  modules and tests, but the flagship `run_report` still showed only the arithmetic/graph-law
  pipeline — the artifact had drifted behind the engine's real capability. The report is the whole
  point (one honest, organized picture), so the frontier work must appear. Question: WHERE — a new
  "solver-verified" bucket, or the existing PROVED/REFUTED/DISCOVERED/OPEN buckets?
- **Decision:** Split by KIND of claim. (1) The frontier LAWS (coloring bounds, Hamiltonicity
  implications) are epistemically identical to existing conjecture-and-survive findings, so they go
  into the SAME epistemic buckets: survivors → OPEN (`bounded_check`, `no_counterexample_within_bound`),
  killed → REFUTED with counterexample. They are NOT put in PROVED — the engine has not proven them
  (Dirac included: it rediscovered the statement and failed to refute it, nothing more). (2) The
  two-authority CONFIRMATION is about invariant VALUES, not law truth — a provenance fact — so it
  gets a separate `frontier` field / FRONTIER section listing representative values (χ(K4)=4, …) each
  `solver_verified` by MathHead. The epistemic taxonomy stays pure; the method contribution is
  visible but not conflated with proof.
- **Consequences:** The report now reflects the engine's real reach (arithmetic → graph laws →
  NP-hard frontier) in ONE artifact, and readers see both the honest status of each frontier law and
  the solver-confirmed invariant values behind them. Placing Dirac in OPEN rather than PROVED is a
  deliberate honesty call — a famous theorem is still "unproven, survived the attack" from the
  engine's standpoint, and saying so is the point. The frontier confirmations add a handful of
  deterministic MathHead calls to `run_report` (representative graphs only — NOT all 156, to keep the
  report fast); verifying the whole sample stays in the module tests. Natural next step logged: start
  actually PROVING the surviving frontier laws to lift them OPEN → PROVED.

---

## ADR-D0021 — Constructive certificates for graph laws; `constructive_bounded`, and refusing a fake PROVED

- **Status:** Accepted · 2026-07-29 (R1 slice — graph constructive certificates)
- **Context:** The surviving frontier coloring laws sat in OPEN with certainty `bounded_check` — "no
  counterexample within the bound." The tantalizing next step is to PROVE them (lift OPEN → PROVED).
  But the arithmetic proof engine (induction / residues / CRT) proves ∀n facts via decision
  procedures; there is NO analogous universal decision procedure for ∀G graph theorems, and no
  proof-term kernel yet (Track M1/M2 is 🟡, unstarted). The honest question: what proof-like object
  CAN we produce today, and how do we label it without lying?
- **Decision:** Produce CONSTRUCTIVE certificates, not universal proofs. For each provable law the
  engine emits an explicit witness that realizes the bound — a greedy coloring (χ≤Δ+1), the identity
  coloring (χ≤n), a maximum clique (ω≤χ) — and an INDEPENDENT checker re-validates the witness from
  scratch on every graph (M-spirit: don't trust the constructor; the checker is tested to reject a
  monochromatic fake coloring and a fake clique). The ω≤χ lower bound is additionally double-confirmed
  by MathHead (K_ω not (ω−1)-colorable → unsat). Label the result HONESTLY: a new certainty
  `constructive_bounded` — an explicit, re-checked witness over graphs up to the bound. It is strictly
  stronger than `bounded_check` but is NOT PROVED: the universal ARGUMENT is recorded on the
  certificate for the reader but is not machine-verified. The laws stay OPEN epistemically.
- **Consequences:** The graph domain takes its first real step from "discover + refute" toward
  "discover + prove," and does it without overclaiming — the gap to a universal ∀G proof is named
  precisely (it needs the proof-term kernel, M1/M2) rather than papered over. This mirrors the
  arithmetic path in spirit (construct a witness, then INDEPENDENTLY check it — ADR-D0016/D0017) but
  is honest that graphs lack the decision procedure that makes the arithmetic facts fully PROVED.
  `constructive_bounded` enters the certainty vocabulary between `bounded_check` and the solver/formal
  tiers. The clique certificate reuses the graph_coloring bridge (1-indexed, ADR-D0018), tying the
  lower bound to an independent solver. Logged next step: either surface these certificates in the
  report, or begin M1 (the kernel) — the only honest road to OPEN → PROVED for graph theorems.

---

## ADR-D0022 — A minimal LCF-style proof kernel; residue-exhaustion as the trusted primitive

- **Status:** Accepted · 2026-07-29 (M1/M2 — proof kernel)
- **Context:** The engine re-checks its modular proofs (ADR-D0016/17), but "re-check" still trusts
  the checker's ad hoc logic. The ideal-engine thesis (§1) wants a KERNEL: theorems admissible only
  through a fixed set of inference rules, with a proof represented as a term the kernel validates. A
  full kernel (proof-term DSL derived from ring + induction axioms, dependent types) is large 🟡/🔴
  work; the question was how to get a REAL, honest kernel now without faking the depth.
- **Decision:** Build a minimal LCF-style kernel over the fragment we already decide completely —
  `Divides(m, p)` for integer polynomials. `Theorem` is forge-guarded (guarded constructor; only the
  module-private `_mint` builds one, after a rule verifies), so a Theorem value IS a proof-carrying
  certificate. Two rules: RESIDUE (the kernel runs the full residue sweep — sound and complete for
  the atomic judgment because p(n) mod m depends only on n mod m for integer p) and CRT (pairwise
  coprime, same polynomial). The PROVER (`prove_divides`) is explicitly UNTRUSTED and separate: it
  emits a term; only the kernel's `check` mints the Theorem. Trust base is stated in the module:
  residue-exhaustion is the trusted PRIMITIVE, not derived from deeper axioms — that is deferred
  M-track work, and we say so rather than pretending otherwise.
- **Consequences:** The engine now has a genuine kernel: no false modular theorem can be minted
  (a false claim fails RESIDUE and raises; the guarded constructor blocks fabrication), and CRT
  reasoning is enforced structurally (non-coprime moduli / mismatched polynomials rejected). This is
  a stronger guarantee than the earlier re-check, and it is honestly scoped — the kernel covers the
  modular-polynomial class, and the residue primitive's own axiomatic derivation is future work. The
  LCF guard is Python's practical approximation of an abstract type (module encapsulation, documented
  as such — Python has no true private constructor). Natural next steps: (1) bridge proved arithmetic
  findings to emit kernel terms → a `kernel_verified` status, with `checker.py` the independent M3
  second checker; (2) later, widen the fragment and derive RESIDUE from more primitive rules.

---

## ADR-D0023 — Proof-artifact provenance is derived metadata, kept OUT of the trusted core

- **Status:** Accepted · 2026-07-29 (M4/M5 — provenance, hash, replay)
- **Context:** With the kernel minting theorems (ADR-D0022), the auditor's questions follow: which
  axioms does THIS theorem depend on (M5)? Can I store a proof and re-verify it later, byte-for-byte
  (M4)? Tempting to bolt these onto `Theorem`/`kernel.py`, but that would grow the trusted core.
- **Decision:** Put provenance in a SEPARATE `provenance.py` that operates on proof TERMS, never
  minting theorems (only `kernel.check` does). `axioms_used` walks the term and returns the full set
  of RESIDUE(m)/CRT rules; `proof_hash` hashes a CANONICAL (order-independent) term plus
  `KERNEL_VERSION`; `replay` just re-runs `check`. The arithmetic findings store `proof_hash` +
  `axioms`; the report prints per-fact hashes and a kernel-axiom manifest. The trusted core stays
  minimal and stdlib-only; provenance is derived, auditable metadata layered on top.
- **Consequences:** Every kernel proof is now a content-addressed, replayable artifact with a
  transparent axiom list — the honesty thesis made mechanical (a theorem literally shows what it
  rests on, including "uses residue-exhaustion at modulus 8"). Canonicalization makes the hash
  order-independent, so logically-identical proofs de-duplicate. Versioning means a future kernel
  change cleanly invalidates stale artifacts rather than silently colliding. Keeping this out of the
  core preserves the small, auditable trust base — provenance can have bugs without ever minting a
  false theorem. Sets up M-track continuations (proof storage/sharing, dependent-theorem graphs)
  without further touching the kernel.

---

## ADR-D0024 — Widen the kernel to a second judgment (SumIdentity) rather than a second kernel

- **Status:** Accepted · 2026-07-29 (M1 — fragment widening)
- **Context:** The sequences domain proved sum identities by induction + an independent polynomial
  check, but had no kernel proof (unlike the modular facts after ADR-D0022). Options: a separate
  little kernel for sums, or widen the one kernel to carry a second judgment. Sum closed forms are
  RATIONAL polynomials (n(n+1)/2), which the integer-only Divides fragment can't represent.
- **Decision:** Widen the SINGLE kernel. Generalize `Theorem` to `(kind, payload)` — `Divides` and
  `SumIdentity` — keeping `modulus`/`poly` as accessors that work for Divides and raise otherwise
  (backward compatible; existing tests untouched). Add the `SumInduction` rule (base case + zero
  telescoping step, a sound+complete decision procedure for polynomial sums) with exact RATIONAL
  polynomial arithmetic (Fraction) confined to the SumIdentity path; RESIDUE stays integer-only
  because its soundness argument (p(n) mod m depends only on n mod m) needs integer coefficients.
  Enforce non-mixing at the rule boundary: CRT rejects any premise that is not a Divides theorem.
- **Consequences:** One kernel, one forge-guarded `Theorem` type, one provenance/replay path now cover
  BOTH arithmetic domains — the proof story is unified (11 kernel-verified facts in the report:
  7 modular + 4 sums), and the LCF trust base grew by exactly one small, auditable rule. Keeping the
  rational arithmetic out of the Divides path preserves RESIDUE's soundness. The generalization was
  done without breaking the Divides API (accessor properties), so the widening cost nothing
  downstream. This is the pattern for future fragments (inequalities, identities): add a judgment +
  a rule to the same kernel, not a parallel one. Deeper work still deferred: deriving RESIDUE and
  SumInduction from more primitive ring/induction axioms (the "real" kernel floor).

---

## ADR-D0025 — Negative knowledge is a memory layer beside the judge, not part of the trust base

- **Status:** Accepted · 2026-07-29 (Track Y — failure memory)
- **Context:** The engine refutes conjectures and hits dead ends but forgets them between runs, so a
  longer research session would re-walk closed branches. Track Y wants a memory of failures. Risk:
  a "memory" that starts influencing what counts as proved would enlarge the trust base.
- **Decision:** Keep failure memory strictly an EFFICIENCY/MEMORY layer, never a proof authority.
  `failure_memory.py` records dead ends under canonical fingerprints (Y1) and offers `seen`
  (skip-if-already-walked) and `lessons` (Y2 — cluster refuted conjectures by the witness that
  killed them). It is pure and deterministic; it never mints or blesses a result. The report merely
  DISPLAYS a negative-knowledge summary. `populate_from_refutations` is tolerant of both dict and
  dataclass refutation results and reports how many NEW dead ends were learned.
- **Consequences:** The engine gains reusable negative knowledge — which witnesses are broad refuters,
  which branches are closed — without touching soundness: a bug in the memory can waste effort but can
  never make a false theorem pass. The witness-clustering lesson is genuinely reusable (a witness that
  killed many conjectures should be tried first on new ones), and it is honest about being heuristic.
  Fingerprint canonicalization means the same dead end truly collides regardless of spelling. Logged
  next step: wire `seen` into the refute loop so repeats are actually skipped (this increment builds
  and displays the memory; consuming it in the hot loop is the follow-up).

---

## ADR-D0026 — Interestingness is a transparent heuristic with a visible breakdown, labeled as such

- **Status:** Accepted · 2026-07-29 (W1 — interestingness scoring)
- **Context:** Findings need ranking (the report lists dozens). The document's interestingness notion
  is multi-component (novelty/generality/surprise/usefulness/compression/connectivity − triviality),
  but a genuinely LEARNED interestingness model with human feedback is Track W3 and explicitly open.
  Risk: a scoring function that looks authoritative would overclaim.
- **Decision:** Ship a HEURISTIC, and make its heuristic nature unmissable. Each component is a named,
  documented, deterministic proxy (e.g. compression = support-per-symbol; generality = universal >
  all-graphs > subclass); weights are hand-set and documented as NOT learned; the score object carries
  the full per-component breakdown so any ranking is explainable; and both the module docstring and the
  report section say plainly "heuristic, not a learned measure (W3 open)." It ranks and explains; it
  never gates truth.
- **Consequences:** The engine gains a reproducible, inspectable ranking that behaves sensibly on the
  real report (strong universal kernel-verified facts top; the trivial χ≤n bound sinks to 0.0), and a
  human can always see WHY. Because it is transparent and clearly labeled, it informs attention without
  masquerading as ground truth — the honest version of a feature the source itself flags as unsolved.
  The per-component design also makes W3 a clean future upgrade: replace the hand-set weights with
  learned ones, keep the components. It stays out of the trust base entirely (ranking ≠ proving).

---

<!-- New decision template:
## ADR-D#### — title
- **Status:** Proposed | Accepted | Superseded (ADR-D####) · YYYY-MM-DD
- **Context:** …
- **Decision:** …
- **Consequences:** …
-->
