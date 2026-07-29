# Discovery Engine — Progress log

> WHAT we did, WHEN, WHY — append-only, newest on top. The subproject that follows
> `docs/IDEAL-ENGINE-ROADMAP.md`. Rationale of design choices goes to
> `docs/discovery/DECISIONS.md`.

---

## 2026-07-29 — Independent proof checker (M spirit): don't trust the prover, check the proof

The document's #1 principle, in a tractable form. New `checker.py` re-verifies a proof tree by an
orthogonal, minimal, stdlib-only method — and rejects anything it can't confirm.

- A modular claim `p(n) ≡ 0 (mod m)` is re-checked at every residue mod m — COMPLETE, and
  independent of HOW the proof was found (even an induction/Z3 proof is re-verified this way).
- A CRT node is checked for its REASONING too: prime-power moduli pairwise coprime, product = m,
  every lemma checks out.

It confirms the real proofs (n³−n mod 6 via CRT structure + residues; n⁵−n mod 30 via residues) and
REJECTS both a false claim (n²+1 ≡ 0 mod 4) and broken CRT reasoning (children mod 2·3 but goal mod
12). A buggy prover can no longer pass off a wrong theorem — the strongest honest status
(`independently_verified`). Scoped to the modular class where the check is complete. 5 new tests
(discovery suite 93); full suite 1382 green, ruff clean. ADR-D0016 (M1–M3 spirit).

---

## 2026-07-29 — Proof-dependency trees (T3 slice): make a proof's lemmas explicit

A small, budget-measured step into lemma discovery. New `proof_tree.py`: reconstruct a proved
finding's dependency tree from the winning strategy — no extra solver calls, deterministic.

```
(n**3 - n) % 6 == 0   [CRT, formal_proof]  — coprime prime-power lemmas combined by CRT
    (n**3 - n) % 2 == 0   [induction, formal_proof]
    (n**3 - n) % 3 == 0   [induction, formal_proof]

(n**5 - n) % 30 == 0  [residue-exhaustion, exhaustive_residue_proof]  — all 30 residues checked
```

So a proof is now legible as a tree of the lemmas it rests on. Honest scope: this does NOT invent
lemmas (the 🔴 open part of T) — it surfaces the ones an existing proof already uses, checkably.
Deliberately small (one module, no new solver load) to stay inside the weekly budget. 4 new tests
(discovery suite 88); full suite 1377 green, ruff clean. ADR-D0015. Roadmap T3.

---

## 2026-07-29 — Proof portfolio (S1) with a COMPLETE fallback: residue exhaustion

Turned the modular prover into a small portfolio, and gave it a complete fallback so it stops
leaving true facts as `unknown`.

**Done — `strategy.py::prove_by_residues`:** a COMPLETE decision procedure for `p(n) ≡ 0 (mod m)`
over all integers — for an integer-coefficient polynomial, p(n) mod m depends only on n mod m, so
checking all m residues is a rigorous finite case-split (a real proof). The arithmetic loop now
tries the elegant MathHead proofs first (induction → factoring+CRT) and falls back to residue
exhaustion, recording the winning method.

**Result — every modular law now PROVED, each by the right strategy:**
- `induction`: n(n+1) ≡ 0 mod 2, n²−n ≡ 0 mod 2
- `modulus-factoring` (CRT): n(n+1)(n+2) ≡ 0 mod 6, n³−n ≡ 0 mod 6
- `residue-exhaustion` (complete): n(n+1)(n+2)(n+3) ≡ 0 mod 24, n⁵−n ≡ 0 mod 30, n⁷−n ≡ 0 mod 42

Honest note: the earlier `unknown`s were a weakness of one method, not a real wall — this class is
decidable and the engine now decides it (certainty `exhaustive_residue_proof` for the case-split,
`formal_proof` for the induction/CRT proofs). The genuine walls remain (graph laws →
`not_applicable`, truly open problems → `unknown`). 2 tests updated + residue-completeness test;
full suite 1373 green, ruff clean. ADR-D0014. Roadmap S1 (portfolio).

**Next:** a heavier track (lemma discovery T / a real proof kernel M), or more discovery surface —
the portfolio and the four report buckets absorb it.

---

## 2026-07-29 — Spectral bounds (numerical) + a more robust modular prover

Extended the spectral thread to real-valued BOUNDS, and hardened the modular prover.

**Done — new `spectral_bounds.py`:** the spectral radius (largest eigenvalue, from MathHead)
evaluated numerically; candidate bounds checked counterexample-first and labeled honestly
`certainty="numerical_check"` (not a proof). The engine found the classic sandwich
**average_degree ≤ spectral_radius ≤ max_degree** (survives) and REFUTED the plausible
`spectral_radius ≤ average_degree` — a single edge on 3 vertices breaks it (λ=1 > ⅔). Exact
symbolic eigenvalue comparison was unreliable (SymPy's complex-radical forms won't order), so we
went numeric — and kept it OUT of the default report (per-graph eigenvalue cost).

**Robustness fix:** the modular prover was unified — `discover_and_prove` now always routes
through `prove_modular_divisibility` (prime m = one induction; composite = factor + CRT) with a
reliable 2500 ms budget, removing a flaky direct-then-fallback race that occasionally dropped
`n³−n mod 6` back to unknown under load. Run ~10 s, verdicts stable. ADR-D0013.

3 new tests (discovery suite 82); full suite 1372 green, ruff clean.

**Next:** more surface into the four buckets, or start a heavier track (lemma discovery T / a real
proof kernel M) — the pipeline stays orderly either way.

---

## 2026-07-29 — Interestingness (W0): keep subclass-specific laws, drop restricted-universals

A first filter against the "a machine can emit a million trivially-true statements" problem. New
`novelty.py`: a subclass law is INTERESTING only if it is specific to that subclass — i.e. its
claim FAILS somewhere in the full sample — not a universal law merely restricted to it.

**What it cleaned up:**
- Dropped `trees: 2*num_edges = sum_degrees` and the forests version — these are just the Handshake
  Lemma seen on a subclass (they hold on EVERY graph), no discovery about trees/forests.
- Kept the genuine characterizations: `trees: num_edges = num_vertices − 1`, `trees: triangle-free`,
  `forests: num_vertices = num_edges + num_components`.

Wired into `run_report`, so the DISCOVERED section is now higher-signal. 2 new tests (discovery
suite 79); full suite 1369 green, ruff clean. ADR-D0012. A tractable first step on the
interestingness problem the document flags as central — without pretending it is "solved".

**Next:** more interestingness (dedup equivalent laws, flag trivial bounds) or more discovery
surface — all into the same four report buckets.

---

## 2026-07-29 — Proof strategy (S): factor the modulus → prove parts → CRT — proving what one induction couldn't

The judge now has more than one route. New `strategy.py`: `prove_modular_divisibility` factors m
(MathHead `factorize`), proves each prime power by induction, and combines coprime successes by CRT.
The arithmetic loop tries a single induction first, then falls back to this strategy.

**What it upgraded (real new proofs):**
- `n³ − n ≡ 0 (mod 6)` and `n(n+1)(n+2) ≡ 0 (mod 6)` — each `unknown` under one induction — are now
  **PROVED** via 2·3 + CRT (`certainty=formal_proof`, `method=modulus-factoring`). The report's
  PROVED arithmetic facts went 2 → 4.
- The still-hard ones (`n⁵−n mod 30`, `n⁷−n mod 42`, the mod-24 case) stay honestly `unknown` — now
  the strategy NAMES the blocking prime power (e.g. the mod-3 step of n⁵−n) instead of a bare wall.

Timing kept safe (judge budget 1500 ms, memoized run ~14 s). 4 new tests (discovery suite 77);
full suite 1367 green, ruff clean. ADR-D0011. First step of the proof-strategy orchestrator (S).

**Next:** more routes in the portfolio (e.g. prove a product-of-consecutives fact by the "one of k
consecutive is divisible by k" argument) or more surface — all into the same four report buckets.

---

## 2026-07-29 — Sum identities: discover the formula from data, prove it by induction (2nd arithmetic generator)

A second arithmetic generator, and a richer discover→prove loop: the engine finds a SUM's closed
form from data and MathHead proves it.

**Done — new `sequences.py`:** for a term f(i), compute partial sums, **fit** a closed-form
polynomial g(n) by interpolation (P4 "guess the formula"), **refute** counterexample-first over a
larger range, then **prove** by induction — base case + MathHead verifying the step
g(n) − g(n−1) = f(n).

**What it found and proved, autonomously:**
- `Σ i = n(n+1)/2`, `Σ i² = n(2n²+3n+1)/6`, `Σ i³ = (n(n+1)/2)²`, `Σ (2i−1) = n²`
  — all **proved** (`solver_verified`, MathHead did the algebraic step).
- `Σ 2^i` (not polynomial): the fit matches the sample but diverges beyond it → **refuted**, not
  forced. The engine doesn't invent a formula where none exists.

Wired into `run_report` — the new generator feeds the same four honest buckets (PROVED / REFUTED /
DISCOVERED / OPEN) without reshaping the pipeline, exactly as claimed. 4 new tests (discovery
suite 73); full suite 1363 green, ruff clean. ADR-D0010. Roadmap P4 done.

**Next:** more of the same into the same buckets — spectral bounds, or mining relations among
named sequences (Fibonacci/Catalan) — the pipeline absorbs it.

---

## 2026-07-29 — Spectral invariants: the graph domain's first bridge to MathHead

The graph domain now flows through MathHead's compute spine for the first time — spectral graph
theory, discovered from data and confirmed by MathHead's eigenvalues.

**Done — new `spectral.py` + spectral moments in `invariants.py`:**
- Spectral moments Σλ², Σλ³ as fast exact invariants (= trace(A²), trace(A³) by integer matmul),
  registered but kept OUT of the default `NUMERIC_INVARIANTS` so existing miners are undisturbed.
- The actual spectrum via **MathHead's `eigenvalues`** tool (memoized per graph) → `spectrum`,
  `num_distinct_eigenvalues`, and `spectrum_confirms_moments` (MathHead as independent authority).

**What the engine discovered (real spectral graph theory, from data):**
- **Σλ² = 2·num_edges** and **Σλ³ = 6·num_triangles** (`discover_spectral_laws`).
- MathHead's actual eigenvalues independently CONFIRM those moments on every graph n≤5 — the
  cross-check the whole product is built for (three ways agree: matmul trace, MathHead spectrum,
  structural count).

**Fix on the way:** symbolic `simplify` of Σλ³ (irrational cubes) blew the 30 s test timeout;
switched to a 40-digit numeric evaluation + round (the sum is provably an integer = trace), and
took Re() to drop numerical noise. Spectral test ~1.5 s. 5 new tests (discovery suite 69); full
suite 1359 green, ruff clean. ADR-D0009. Roadmap O1 (spectral) done.

**Next:** more surface into the same four report buckets — a second arithmetic generator, or
spectral bounds (e.g. spectral radius vs max degree) — without reshaping the pipeline.

---

## 2026-07-29 — AC2: one honest run report — consolidation, not sprawl

Tied the two domains into a single organized artifact. New `report.py`: `run_report()` runs the
whole pipeline (graphs + arithmetic) and assembles a `DiscoveryReport` with four honest sections,
and `render()` emits Markdown with provenance (version/seed/bounds/determinism). Deterministic.

The current run (graphs n≤6) at a glance:
- **PROVED (2):** `n(n+1) ≡ 0 mod 2`, `n²−n ≡ 0 mod 2` (formal_proof).
- **REFUTED (1):** `num_triangles ≤ num_edges` (minimal counterexample T=16 > E=14, n=6).
- **DISCOVERED (8, empirical):** the Handshake Lemma + the tree/forest laws.
- **OPEN (15):** graph bounds that survived + arithmetic facts the judge left `unknown`
  (`n³−n ≡ 0 mod 6`, `n⁵−n ≡ 0 mod 30`, …) — discovered, unproven, honestly labeled.

Every item sits in exactly one bucket by its true status; nothing blurred. This is the
consolidation that keeps growth ORDERLY — future domains feed the same four honest buckets rather
than scattering. A rendered sample lives at `docs/discovery/SAMPLE-REPORT.md`. 5 new tests
(discovery suite 64); full suite 1354 green, ruff clean. ADR-D0008.

**Next:** more surface into the same buckets — widen the arithmetic family or add a spectral graph
invariant routed through MathHead — the report absorbs it without reshaping.

---

## 2026-07-29 — Arithmetic domain: the loop CLOSES — generate → refute → PROVE, autonomously

The first fully autonomous loop with a real proof at the end. New `arithmetic.py`: for a family
of polynomials p(n) the engine discovers the modulus from data (`m = gcd(p(1),p(2),…)`), refutes
counterexample-first, then hands the survivor to MathHead's induction judge.

**What the engine found and did, on its own:**
- Discovered the moduli from data: n(n+1)→2, n(n+1)(n+2)→6, ×4→24, n²−n→2, **n³−n→6** (stronger
  than the textbook "mod 3"), **n⁵−n→30** (stronger than Fermat's mod 5), n⁷−n→42.
- PROVED by induction the ones MathHead can decide: `n(n+1) ≡ 0 (mod 2)`, `n²−n ≡ 0 (mod 2)` →
  `certainty=formal_proof`.
- Honest `unknown` (never faked) on the higher-degree steps beyond Z3's reach.
- Killed overshoot claims (e.g. n(n+1) ≡ 0 mod 4) with a minimal counterexample before the judge.

**Speed/honesty:** the induction proof runs under a small `timeout_ms` budget (a smaller budget
just yields `unknown` sooner — the bound is a budget, not a lie); the full run is memoized. The
test file dropped from ~102 s to ~11 s. 6 new tests (discovery suite 59); full suite 1349 green,
ruff clean. ADR-D0007.

**This is the thesis, end to end:** discover, try to kill, prove what can be proved, and say
`unknown` out loud for the rest.

**Next:** widen the arithmetic family / add a second generator (e.g. mine relations among integer
sequences), or return to graphs and add a spectral invariant routed through MathHead — either way,
more surface for the same honest loop.

---

## 2026-07-29 — R: the judge bridge — MathHead actually proves/refutes (first real judge use)

The survivors from Q were `no_counterexample_within_bound` — not proven. Now the judge reaches
real verdicts.

**Done — new `judge.py`:** bridges the discovery layer to `mathhead.router.route`, mapping a
MathHead result to a `Verdict` (proved | refuted | unknown | not_applicable) that carries
MathHead's own `certainty`. Semantic helpers: `judge_induction`, `judge_inequality`,
`judge_identity`, `judge_entailment`, `judge_task`; plus `judge(conjecture)` that uses an
optional `mathhead` task on a Conjecture. ADR-D0006.

**The judge genuinely works:**
- `n(n+1)` even and `n³ − n ≡ 0 (mod 3)` → **proved by induction**, `certainty=formal_proof`.
- AM-GM `x² + y² ≥ 2xy` → **proved**, `certainty=solver_verified` (Z3).
- `x² ≥ x` (false over the reals) → **refuted**, with MathHead's witness `x = 0.5`.
- a graph law (`min_degree ≤ max_degree`, no `mathhead` task) → **`not_applicable`** — honest, not
  a fabricated verdict.

So `empirical → proved / refuted` happens only where MathHead's grammar truly reaches; the
combinatorial laws stay honestly out of scope. 6 new tests (discovery suite 53); full suite
green, ruff clean. The bridge is ready.

**Next:** an arithmetic / integer-sequence object domain — so the discovery loop AUTO-GENERATES
conjectures the judge can prove, closing generate → refute-first → PROVE end to end in a domain
where MathHead is the native judge.

---

## 2026-07-29 — P0 + Q0: conjecture generation + counterexample-first — the engine's character

The engine now GENERATES candidate laws and, by default, tries to KILL them before believing —
the "counterexample-first" stance. This is where discovery stops being bookkeeping.

**Done — new `conjectures.py` (P0) + `refute.py` (Q0):**
- **`subclass_laws`** — mine O2 laws on a predicate-defined subclass. On **trees** the engine
  rediscovers classic theorems from data: `num_triangles = 0`, `num_edges = num_vertices - 1`;
  on **forests** the correct weaker `num_vertices = num_edges + num_components` (NOT E=V-1). Added
  structural `is_forest`/`is_tree` invariants (cycle detection, not the E=V-C formula — no
  circularity).
- **`bound_conjectures`** — propose non-trivial inequalities `A <= B` holding on the sample.
- **`refute`** (counterexample-first, Q0 + minimal-CE Q4): bounded scan returning the MINIMAL
  counterexample or an honest `no_counterexample_within_bound` — never "proved".

**The character moment (the milestone):** from graphs with n<=5 the engine proposes 11 plausible
bounds (all true on <=5 vertices); a bounded attack up to n=6 then **kills exactly one** —
`num_triangles <= num_edges`, with the minimal counterexample **T=16 > E=14** on 6 vertices (K6
minus an edge) — while the other 10 survive as bounded-honest. True theorems (`trees: E=V-1`,
`trees: triangle-free`) survive.

**Fixes on the way (recorded honestly):** the refute loop was regenerating the n<=6 graph set
per conjecture (~38 s > the 30 s test timeout; the timeout's traceback even crashed pytest's
renderer). Fixed by **memoizing generation by n** (deterministic) + switching stored predicates
from lambdas to named closures. Full loop now ~3.6 s.

**Honesty (ADR-D0005):** survivors are `no_counterexample_within_bound`, the handoff to the judge
(R). The judge (MathHead) is deliberately NOT wired for graph theorems — it isn't the right tool
there; it enters for the algebraically-reducible survivors. 8 new tests (discovery suite 47);
full suite 1337 green, ruff clean.

**Next:** R — take a survivor that IS expressible in MathHead's grammar (or move a sub-demo to a
number-theory domain) and let the judge actually PROVE it — the first real use of MathHead as the
discovery engine's judge.

---

## 2026-07-29 — O2: automatic relation discovery — the engine rediscovers the Handshake Lemma

First real *discovery*: the engine finds a true theorem from data (not hardcoded).

**Done — new `relations.py` (Track O2):**
- **`discover_linear_laws`** — builds the affine feature matrix over the numeric invariants and
  reports the exact linear laws (integer null space, sympy rationals) holding across the whole
  sample. Each is a `DiscoveredLaw` with **`status="empirical"`** (a conjecture, not a theorem)
  + `holds_over` / `support`. ADR-D0004.
- **`discover_constants`** — invariants constant across a sample (e.g. `num_vertices=4` over all
  graphs on 4 vertices).
- Added `sum_degrees` as a numeric invariant + `NUMERIC_INVARIANTS` (the miner's columns) —
  deliberately NOT hardcoding `sum_degrees = 2E`; the engine must find it.

**Milestone (the O2 gate):** over all graphs with n ≤ 5 (53 objects) AND n ≤ 6 (209 objects),
the miner returns **exactly one** universal law — `2*num_edges = sum_degrees`, the **Handshake
Lemma** — with no spurious relations. As A000088 pinned generation, this pins discovery.

**Honesty:** the law ships as `empirical` (holds over the sample), never as "proved". That is
the handoff to the next tracks: a conjecture for the counterexample-first track (Q) to attack,
then the judge (R) to prove. 6 new tests; discovery suite now 39; full suite green, ruff clean.

**Next on the critical path:** P0/P1 — conjecture generation (bounds/inequalities, subclass laws
via mutation) → then **Q**, where MathHead becomes the judge that attacks each conjecture.

---

## 2026-07-29 — First stone: N0 + N2 + N1 + O0/O1 (the "matter" layer)

Kicked off the discovery engine — the layer that will (later) generate conjectures and hunt
counterexamples, using MathHead as its judge. Started exactly on the roadmap's v0.1 domain
(finite graphs) and its critical path, small but real, fully tested.

**Done — new `mathhead.discovery` package (`src/mathhead/discovery/`):**
- **N0 `objects.py`** — typed object model behind a minimal `MathObject` base; first type is the
  immutable, hashable finite simple `Graph` (explicit `n` so isolated vertices survive).
- **N2 `canonical.py`** — isomorphism elimination via a degree-refined permutation-minimum
  canonical key (correct, not just degree sequence — distinguishes C6 from 2·C3). ADR-D0002.
- **N1 `generate.py`** — canonical non-isomorphic generation, honest-bounded at n ≤ 7 (no silent
  cap), pinned to **OEIS A000088**. ADR-D0003.
- **O0/O1 `invariants.py`** — exact, deterministic graph invariants (edges, degree sequence,
  triangles, components, connectivity...) + a named registry and feature-vector accessor (O3-lite).

**Verification (the correctness gate):**
- `count_non_isomorphic(n)` reproduces **A000088 exactly for n = 0..6: 1, 1, 2, 4, 11, 34, 156**
  (n=6 in ~3.2 s) — an independent oracle for both generation and canonical labeling.
- Hard iso case handled: **C6 vs 2·C3** (same degree sequence, non-isomorphic) correctly
  separated — proves the canonical form goes beyond the degree sequence.
- **33 discovery tests green, ruff clean.** No MathHead code touched (additive subpackage).

**Deliberately NOT done yet (honest):** the judge (MathHead verify/counterexample/certificate)
is not wired in — it belongs at the refutation/proof tracks (Q/R), not the object layer.
Orderly/McKay generation (to pass n=7) and nauty-style canonicalization are logged as planned
N1/N2 optimizations, not needed for correctness now.

**Next on the critical path:** O2 (automatic invariant discovery) → P0/P1 (conjecture generation
from the invariant feature tables) → Q (counterexample-first, where MathHead becomes the judge).
