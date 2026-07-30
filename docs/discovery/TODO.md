# Discovery Engine — TODO (done / next / open)

> **The three tracking files (nothing else):**
> 1. `docs/IDEAL-ENGINE-ROADMAP.md` — **PLAN**: the full 103-phase plan. FROZEN, does not change.
> 2. `docs/discovery/TODO.md` (this file) — **TODO**: done / next / open. Updated every task.
> 3. `docs/discovery/PROGRESS.md` — **CHANGELOG**: narrative log + rationale. Updated every task.
>
> (`DECISIONS.md` is a frozen ADR archive; `SAMPLE-REPORT.md` is generated engine output — neither is
> a tracker.) This file is the short at-a-glance view: where we are, what's next, what we will NOT fake.

_Last updated: 2026-07-30 · 52 modules · 343 discovery tests · 28 phases ✅ full, of 103 (across 21 tracks)._

## Done — by cluster

**Trust / judge (M, Q, R)**
- Proof KERNEL, LCF-style, forge-guarded — 3 judgments: Divides (RESIDUE/CRT), SumIdentity, PolyIdentity.
- Trust base SHRUNK: RESIDUE derived from the factor theorem, CRT derived from Bézout, and SumInduction
  derived from the kernel's own PolyIdentity (the induction STEP `g(n)=g(n−1)+f(n)` is now an explicit
  kernel-checked identity, base = eval at n=1) — all three now theorems, not axioms —
  `congruence.py` + `sum_derivation.py`.
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

**Knowledge / grade / direct (X, Y, AC, AF, T)**
- Knowledge graph + impact analysis; failure memory (negative knowledge); research director
  (goal-driven, cross-cycle). Honest scorecard + structured cited catalog (0 novel, auditable).
- Goal↔knowledge GAP measure (T0): BFS distance from a goal to proved ground + open dependencies →
  a [0,1] gap; ranks open goals closest-to-reach first (complements impact's entanglement) — `gap.py`.
- One deterministic report; object-model infra (parametric families N4, generic serialization N3).

## Automation

Bookkeeping is automated at three levels (no longer a manual chore):
- **commit-time (local):** `scripts/hooks/pre-commit` auto-refreshes `SAMPLE-REPORT.md` + this file's
  stats line, re-stages them, and blocks the commit if the PLAN shrank. Activate once per clone:
  `git config core.hooksPath scripts/hooks`.
- **CI:** a dedicated `trackers` job runs `scripts/gen_status.py --check`.
- **test suite:** `tests/test_trackers.py` enforces the plan integrity + sample freshness in pytest.

Manual escape hatch: `python scripts/gen_status.py` (refresh) / `--check` (verify).

## Progress toward the goal

**~49 / 103** phases touched (fully-done ✅ count is in the auto stats line above). **Track N COMPLETE
(N0–N6); Track O complete (O0–O4).** 28 fully ✅; 12 remain 🔴 open-research (won't fake) ⇒ achievable
ceiling ≈ 91, so ~42 achievable phases remain (many are deepening partials to full). **User check-in at
49 REACHED** — next at 59. Recently done: N3–N6, O4, P1, AB1, P2, T0, S2; M-floor DEEPENED (SumInduction
derived — M2, already-touched); SIXTH domain compositions added (deepens N/O/P — N0 already ✅, so count
stays 49, but a real new domain with a constructive-bijection proof).

## Next — prioritized candidates

1. **Deeper kernel floor (M)** — derive/soundness-check the remaining primitives (integer-divisibility
   base facts; make SumInduction's induction step explicit). Highest-rigor, on the thread just advanced.
2. ~~**Report/ladder polish** — surface `residue_derivable`/`crt_derivable` in the rendered report.~~
   ✅ DONE (2026-07-30): report header now shows the M-floor trust base (RESIDUE 7/7, CRT 7/7).
3. **Sixth domain or richer invariants** — e.g. compositions / Young tableaux, or non-linear relation
   mining (products/ratios) that could surface an unattributed candidate honestly.
4. **M6 Lean bridge** — export a kernel proof to an external checker for cross-sealing (stretch).

## Open — will NOT fake (🔴 honest boundary)

- **Novel mathematics.** 0 established; genuine novelty needs a real literature corpus (X1 full ingest)
  AND exploration beyond elementary/small-object territory. Not claimed.
- **Universal graph/combinatorial proofs.** Structural arguments + bijections are sample-verified;
  the universal step is classical, recorded not machine-checked.
- **Learned models** (interestingness W3, proof-guidance S4, representation search U2) — transparent
  heuristics only; a learned/RL model with human feedback is out of scope.
- **New concept/definition generation (Z), independence analysis (AB2/AB3)** — research frontier.
