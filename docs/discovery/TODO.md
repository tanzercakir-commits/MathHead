# Discovery Engine — TODO (done / next / open)

> **The three tracking files (nothing else):**
> 1. `docs/IDEAL-ENGINE-ROADMAP.md` — **PLAN**: the full 103-phase plan. FROZEN, does not change.
> 2. `docs/discovery/TODO.md` (this file) — **TODO**: done / next / open. Updated every task.
> 3. `docs/discovery/PROGRESS.md` — **CHANGELOG**: narrative log + rationale. Updated every task.
>
> (`DECISIONS.md` is a frozen ADR archive; `SAMPLE-REPORT.md` is generated engine output — neither is
> a tracker.) This file is the short at-a-glance view: where we are, what's next, what we will NOT fake.

_Last updated: 2026-07-30 · 46 modules · 303 discovery tests · 27 phases ✅ full, of 103 (across 21 tracks)._

## Done — by cluster

**Trust / judge (M, Q, R)**
- Proof KERNEL, LCF-style, forge-guarded — 3 judgments: Divides (RESIDUE/CRT), SumIdentity, PolyIdentity.
- Trust base SHRUNK: RESIDUE derived from the factor theorem, CRT derived from Bézout (both now theorems,
  not axioms) — `congruence.py`.
- Provenance (hash + axiom list + replay), independent second checker, adversarial soundness battery
  (600+ false claims, 0 breaches).
- Counterexample-first refutation with minimal witnesses; epistemic-status vocabulary + 4-rung ladder.

**Matter / measure (N, O)**
- FIVE object domains through one pipeline: graphs, arithmetic, permutations, integer partitions,
  set partitions — each pinned to an OEIS oracle.
- Exact invariants per domain; linear-law mining (Handshake, spectral identities); frontier bridge
  (χ, Hamiltonicity via MathHead SAT/UNSAT).

**Discover / prove / explain (P, S, T, W)**
- Discover→refute→PROVE closed in arithmetic (kernel-verified); constructive certificates (graphs);
  constructive BIJECTIONS (Glaisher/Euler, conjugation, Foata/Mahonian).
- Explanations: algebraic (factorization), structural (double counting, clique bound, cycle degree),
  bijective. Interestingness ranking (heuristic). Cross-domain analogy detection (P3).

**Knowledge / grade / direct (X, Y, AC, AF)**
- Knowledge graph + impact analysis; failure memory (negative knowledge); research director
  (goal-driven, cross-cycle). Honest scorecard + structured cited catalog (0 novel, auditable).
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

**~45 / 103** phases touched (fully-done ✅ count is in the auto stats line above). **Track N COMPLETE
(N0–N6); Track O complete (O0–O4).** Working through the ~52 achievable untouched phases; 12 remain 🔴
open-research (won't fake). Next user check-in at 49 touched (4 to go). Recently done: N3–N6, O4, P1.

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
