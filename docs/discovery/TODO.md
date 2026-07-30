# Discovery Engine — TODO (done / next / open)

> **The three tracking files (nothing else):**
> 1. `docs/IDEAL-ENGINE-ROADMAP.md` — **PLAN**: the frozen 103-phase v1 plan + the user-approved
>    **v2 extension (Real Discovery Program, 16 phases)** appended 2026-07-30. Both guarded.
> 2. `docs/discovery/TODO.md` (this file) — **TODO**: done / next / open. Updated every task.
> 3. `docs/discovery/PROGRESS.md` — **CHANGELOG**: narrative log + rationale. Updated every task.
>
> (`DECISIONS.md` is a frozen ADR archive; `SAMPLE-REPORT.md` is generated engine output — neither is
> a tracker.) This file is the short at-a-glance view: where we are, what's next, what we will NOT fake.

_Last updated: 2026-07-30 · 65 modules · 438 discovery tests · 30 phases ✅ full, of 103 v1 + 16 v2 (across 21 tracks)._

## Done — by cluster

**Trust / judge (M, Q, R)**
- Proof KERNEL, LCF-style, forge-guarded — 3 judgments: Divides (RESIDUE/CRT), SumIdentity, PolyIdentity.
- Trust base SHRUNK: RESIDUE derived from the factor theorem, CRT derived from Bézout, and SumInduction
  derived from the kernel's own PolyIdentity (the induction STEP `g(n)=g(n−1)+f(n)` is now an explicit
  kernel-checked identity, base = eval at n=1) — all three now theorems, not axioms —
  `congruence.py` + `sum_derivation.py`. **M-floor COMPLETE:** the last "elementary integer divisibility"
  hand-wave is now explicit — `m|a∧m|b⇒m|a+b` and `m|a⇒m|a·k` get constructive witnesses + a 4624-case
  exhaustive check (0 failures), resting only on ℤ's ring axioms — `divisibility.py`.
- Axiom-MINIMAL proof search (AB1): of the kernel-checked proofs of `m|p(n)` (direct RESIDUE vs
  CRT-over-prime-powers), pick the fewest-axiom one — `6|n³−n` needs RESIDUE(6) alone — `axiom_minimize.py`.
- Provenance (hash + axiom list + replay), independent second checker, adversarial soundness battery
  (600+ false claims, 0 breaches).
- Counterexample-first refutation with minimal witnesses; epistemic-status vocabulary + 4-rung ladder.

**Matter / measure (N, O)**
- SIX object domains through one pipeline: graphs, arithmetic, permutations, integer partitions,
  set partitions, and COMPOSITIONS — each pinned to an OEIS oracle. Compositions add a constructive gem:
  #{comps of n} = 2^(n−1) PROVED by the cut-point bijection (comp ↔ subset of {1..n−1}) — `compositions.py`.
- Exact invariants per domain; linear-law mining (Handshake, spectral identities); frontier bridge
  (χ, Hamiltonicity via MathHead SAT/UNSAT).
- NON-LINEAR (degree-2) law mining: same exact null-space over a polynomial feature map; rediscovers
  `2·num_edges = n²−n` on Kₙ, filters reducible (lower-law × invariant) laws, honest empirical status —
  `nonlinear_relations.py`.
- RATIO & MONOTONICITY mining (P0 breadth): constant ratios (Handshake as `sum_degrees/num_edges = 2`) +
  monotonic trends over an ordered family; exact (Fraction), empirical — `pattern_mining.py`. Junk-filtered
  (W0 breadth): fake constant-invariant "trends" + accidental both-constant ratios dropped — `trivial_filter.py`.
- Conjecture NORMALIZE + DEDUP across miners (P5): one canonical linear-form key collapses duplicates
  (Handshake as a linear law AND as a ratio → one, corroboration 2); keeps provenance — `conjecture_normalize.py`.

**Discover / prove / explain (P, S, T, W)**
- Discover→refute→PROVE closed in arithmetic (kernel-verified); constructive certificates (graphs);
  constructive BIJECTIONS (Glaisher/Euler, conjugation, Foata/Mahonian).
- Explanations: algebraic (factorization), structural (double counting, clique bound, cycle degree),
  bijective. Interestingness ranking (heuristic). Cross-domain analogy detection (P3).
- Reverse-engineering to the GENERAL principle (P2): lifts `6|n³−n` (3 consecutive ints) to the
  parametric law `k! | product of k consecutive ints ∀k`, kernel-verifying k=1..K; honest on the ∀k
  quantifier and refuses to force a generalization where none exists (`n⁵−n`) — `generalize.py`.
- Resource-bounded strategy PORTFOLIO + budget manager (S2): races direct-residue vs CRT-prime-powers
  under a shared step-budget (cheapest-first); winner = lowest-cost kernel-checked proof; honest
  status solved / unsolved / exhausted (says "exhausted", never a fake proof) — `portfolio.py`.
- Strategy-failure LOG (S3, S→Y loop): feeds portfolio exhausted→timeout / unsolved→dead_end into the
  failure memory (idempotent) + per-strategy diagnostics surfacing the bottleneck — `strategy_log.py`.

**Knowledge / grade / direct (X, Y, AC, AF, T)**
- Knowledge graph + impact analysis; failure memory (negative knowledge); research director
  (goal-driven, cross-cycle) — now selects its next goal by IMPORTANCE × LIKELIHOOD (T2 `rank_lemmas`
  wired into AC0), closing the discover→prioritize→pursue loop. Honest scorecard + cited catalog (0 novel).
- Goal↔knowledge GAP measure (T0): BFS distance from a goal to proved ground + open dependencies →
  a [0,1] gap; ranks open goals closest-to-reach first (complements impact's entanglement) — `gap.py`.
- Lemma ranking by IMPORTANCE × LIKELIHOOD (T2): fuses impact's entanglement with gap's proximity-to-proof
  into one transparent priority; `next_lemma` = the director's next target (heuristic, not learned) —
  `lemma_ranking.py`.
- Algorithm→proof BRIDGE (AA4, S/M): links a discovered algorithm to its warrant — residue-exhaustion →
  kernel Theorem (universal), greedy-coloring/max-clique → constructive certificate (witnessed); honest
  about the strength gap, never conflated — `algorithm_proof.py`.
- Verified representation-transform registry (U0): graph↔matrix + composition↔subset (round-trip),
  graph→degseq (preserves Handshake), divisibility→residue-table (decides, agrees with kernel); confirms
  the ENCODERS are faithful — complements O4's value-consistency check — `representations.py`.
- Number-theory representation CHAIN (U1): walks a divisibility claim Diophantine→modular→finite-residue
  →decision; ∀ kernel-confirmed, ∃ surfaces the honest gap (`5|n³−n` false ∀ but true ∃); explicit ledger
  of chain links walked vs not (lattice/SAT/alg-geometry) — `nt_chain.py`.
- One deterministic report — now SURFACES the new miners: degree-2 laws (in the well-determined regime,
  guarded against small-n overfitting) + a P5 CORROBORATION line (Handshake found by linear AND ratio
  miners, ×2). Object-model infra (parametric families N4, generic serialization N3).

## Automation

Bookkeeping is automated at three levels (no longer a manual chore):
- **commit-time (local):** `scripts/hooks/pre-commit` auto-refreshes `SAMPLE-REPORT.md` + this file's
  stats line, re-stages them, and blocks the commit if the PLAN shrank. Activate once per clone:
  `git config core.hooksPath scripts/hooks`.
- **CI:** a dedicated `trackers` job runs `scripts/gen_status.py --check`.
- **test suite:** `tests/test_trackers.py` enforces the plan integrity + sample freshness in pytest.

Manual escape hatch: `python scripts/gen_status.py` (refresh) / `--check` (verify).

## Progress toward the goal

**~55 / 103** phases touched (fully-done ✅ count is in the auto stats line above). **Track N COMPLETE
(N0–N6); Track O complete (O0–O4).** 28 fully ✅; 12 remain 🔴 open-research (won't fake) ⇒ achievable
ceiling ≈ 91, so ~36 achievable phases remain (many are deepening partials to full). **User check-in at
49 done** — next at 59 (4 to go). Recently done: AB1, P2, T0, S2, AA4, U0, T2, U1, P5, S3; M-floor now COMPLETE
(SumInduction + elementary divisibility — M2, deepening); SIXTH domain compositions; NON-LINEAR degree-2 +
RATIO/MONOTONICITY mining (O2/P0); director goal-selects via T2 (AC0); report surfaces new miners (AC2);
W0-breadth junk filter for new patterns; T3 proof-trees now cover sum identities. **Emphasis: value/depth
over marginal new-phase touches.**

## v2 — REAL DISCOVERY PROGRAM (the new primary workstream)

User-approved 2026-07-30. Strategy: genuine novelty lives in EXPONENTIAL HAYSTACKS (a specific witness /
formula / structure), not in small-object laws; novelty is only ever claimed via EXTERNAL channels (OEIS
referee acceptance, self-verifying counterexample witness, Lean kernel check). Kademe 1 → 4 in the PLAN's
v2 section (16 phases, guarded). AE2's honest hunt sealed the lesson: 40 findings → 4 unattributed-in-
catalog → ALL four textbook family formulas. Catalog-miss ≠ literature-novel, proven on our own output.

Progress: **v2A3 ✅** (PSLQ hunt — rediscovered 6ζ(2)=π², 90ζ(4)=π⁴, √2, φ at 220-digit verification;
honest Nones for e-π/noise). **v2A1 ✅, v2A0/A2 🟢** (OEIS radar live — 11 sequences computed from the
engine's own generators; 9 land exactly on their OEIS pins incl. derangements A000166 & connected graphs
A001349; 2 PENDING external lookup: triangle-free `1,1,2,3,7,14,38` and χ=3 `0,0,0,1,3,16,84` — human
checks oeis.org; runtime auto-query correctly refused, robots.txt respected).
Next up (Kademe 1): v2A4 nauty/geng scale → v2A5 rich invariants → Kademe 2 counterexample hunter.

## Next — prioritized candidates

**DISCOVERY-MINING SUBSYSTEM COMPLETE end-to-end:** build (linear/nonlinear/ratio/monotone) → dedup (P5)
→ surface in report (AC2) → drive the director (AC0/T2) → log strategy failures (S3/Y) → junk-filter (W0).
That whole loop is now wired and tested — the last three proposed items (report wiring, S3, W0 breadth)
plus the AC0 director wiring are all done.

**Honest note:** easily-reachable NEW phases are thin; remaining high-value work is DEPTH (harden ~26
touched-partials to fully-✅) or a couple of stretch items. Prioritizing VALUE over touched-count.

1. **Depth: X0 knowledge-graph edges** — infer `generalizes`/`specializes` edges (reserved but not
   populated) from the P2 generalization + subclass structure. Richer semantic graph.
2. **Depth: proof_tree for sum identities** — extend T3 proof-dependency trees to the SumInduction proofs
   (currently only modular/CRT). Rounds out proof-tree coverage.
3. **X2 notation/technique map** — problem-structure → applicable-technique lookup (feeds S1 selection).
4. **M6 Lean bridge** — export a kernel proof to an external checker for cross-sealing (stretch, external dep).

## Open — will NOT fake (🔴 honest boundary)

- **Novel mathematics.** 0 established; genuine novelty needs a real literature corpus (X1 full ingest)
  AND exploration beyond elementary/small-object territory. Not claimed.
- **Universal graph/combinatorial proofs.** Structural arguments + bijections are sample-verified;
  the universal step is classical, recorded not machine-checked.
- **Learned models** (interestingness W3, proof-guidance S4, representation search U2) — transparent
  heuristics only; a learned/RL model with human feedback is out of scope.
- **New concept/definition generation (Z), independence analysis (AB2/AB3)** — research frontier.
