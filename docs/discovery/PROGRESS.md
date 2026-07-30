# Discovery Engine — Progress log (CHANGELOG)

> WHAT we did, WHEN, WHY — append-only, newest on top. Updated every task, alongside `TODO.md`.
> One of the three tracking files: PLAN=`docs/IDEAL-ENGINE-ROADMAP.md` (frozen) · TODO=`TODO.md`
> (done/next) · CHANGELOG=this file. Each entry now carries its own rationale inline (the older
> `DECISIONS.md` ADR archive is frozen — no longer grown).

---

## 2026-07-30 — v2A3 ✅ PSLQ constant-formula hunt + 2 real bugs caught by the fuzzer

**v2A3 (`pslq_hunt.py`) — the Real Discovery Program's first completed phase.** The BBP formula for π was
found by an integer-relation search, not a human derivation; this is that instrument on mpmath, with the
honesty protocol as the design core. TWO-PRECISION PROTOCOL: a relation is discovered at 60 digits and
re-verified FROM SCRATCH at 220 — an artifact that only "holds" at low precision dies at the second gate.
NOISE REJECTION: bounded coefficient height; unrelated constants must yield None. Calibration results:
rediscovered **6ζ(2)=π², 90ζ(4)=π⁴, √2→x²−2, φ→x²−x−1** (residuals ~10⁻²²⁰), and honestly returned None
for e-π, γ-ln2, the noise-control literal, and π-as-algebraic. Status is ALWAYS `numerical_conjecture` —
PSLQ evidence is not proof, and the kernel cannot check transcendental identities; we never label these
proved. 8 tests. Roadmap v2A3 ✅ (ADR-D0060).

**Two REAL pre-existing bugs found by Hypothesis (the property fuzzer) during this increment — both
fixed:** (1) `compute.simplify` was not idempotent (`x*(-x-1)` re-simplified to `-x*(x+1)` — sympy's
simplify is not a canonical form); fixed with a bounded fixpoint loop so `simplify(simplify(e)) ==
simplify(e)`. (2) `find_root_newton('1/0', …)` crashed with a raw `KeyError: 'ComplexInfinity'` from
sympy's lambdify printer instead of returning an honest error; the compile step is now guarded. Neither
was caused by this session's work — the fuzzer simply hit the examples now and pinned them; exactly the
verification culture working as intended. Full suite **1742 green**, ruff clean.

---

## 2026-07-30 — AE2 honest hunt RAN + v2 REAL DISCOVERY PROGRAM approved & formalized ⭐

**The hunt (AE2, `candidate_hunt.py`):** wide net (6 parametric families + the all-graphs sample, all
miners) → every finding attributed against the catalog → **40 findings, 36 attributed, 4
"unattributed-in-catalog" candidates — and all FOUR turned out to be textbook family formulas** (Cₙ: V=E;
Pₙ/star: V=E+1; wheel: 2V=E+2). The lesson is now proven on our own output: catalog-miss ≠
literature-novel. The module carries that caveat as its centerpiece, and the AE2 goal itself stays
honestly OPEN. 4 tests.

**The program (v2, PLAN extension):** with the user's explicit approval, the answer to "how could GENUINE
discovery happen?" is now formalized as a 16-phase, 4-tier extension appended to the PLAN — original 103
untouched (v2 IDs are lowercase `v2A0…` so they cannot inflate the guarded count; new guard pins v2=16;
`test_trackers` enforces both). Strategy: novelty lives in exponential haystacks (specific witnesses /
formulas / structures — precedents: Wagner's RL counterexamples, FunSearch cap-set, BBP/PSLQ, Heule SAT,
Graffiti, Ramanujan Machine), and it is only ever claimed via EXTERNAL channels: OEIS referee acceptance,
self-verifying counterexample witnesses, Lean kernel checks. Kademe 1 (OEIS radar, PSLQ hunt, nauty
scale, rich invariants) is buildable in this container; Kademe 4 is the honest moonshot (🔴). Full suite
**1733 green**, trackers refreshed (stats line now reports v1 + v2).

---

## 2026-07-30 — T3 depth: proof-dependency trees now cover sum identities

Extended `proof_tree.py` with `sum_proof_tree`. The proof-tree slice (T3) reconstructed the lemma
structure of MODULAR proofs (CRT → prime-power lemmas; residue → complete case-split leaf) but not sum
identities. It now does: by the explicit derivation from this session's `sum_derivation`, a SumInduction
proof of `Σ_{i=1}^n f(i) = g(n)` rests on TWO lemmas — a BASE case `g(1) = f(1)` (an evaluation) and an
induction STEP `g(n) = g(n−1) + f(n)` (a kernel-checked PolyIdentity) — and the tree exposes exactly those,
each with its honest method + certainty. A false claim yields an `unknown`/`not proved` root, no children.
Same honest T3 discipline as the modular tree (it does not invent lemmas — 🔴 — it makes the ones an
existing proof already uses explicit), now closing the sum-identity gap and reusing the trust-shrinking
work from earlier this session. 4 new tests; full suite **1729 green**, ruff clean. HONEST accounting:
DEEPENS the already-✅ T3, count stays ~55/103.

---

## 2026-07-30 — W0 breadth: junk-filter the new ratio & monotone patterns

New `trivial_filter.py` (Track W0, breadth). W0 (`novelty.py`) already dropped restricted-universal
subclass laws; the newer `pattern_mining` miners needed the same hygiene. Two exact, sample-grounded
filters: a MONOTONIC trend on a CONSTANT invariant is junk (a constant sequence is trivially both non-
decreasing and non-increasing — so `num_components non_decreasing` on complete graphs, where
num_components ≡ 1, is a fake "trend") — dropped; and a CONSTANT RATIO whose two sides are BOTH constant
over the sample is accidental (fixed only because neither varies) — dropped, while a ratio with at least
one varying side, like `sum_degrees/num_edges = 2` (Handshake), is a genuine relation and kept. The
filters only ever REMOVE — never invent or relabel — and are a strict subset of the raw output (a test
pins that). Verified: on Kₙ the fake num_components trend is dropped while the five real strictly-
increasing trends survive; on a single graph every ratio is accidental and all are dropped. 6 tests; full
suite **1726 green**, ruff clean. HONEST accounting: DEEPENS the already-✅ W0, count stays ~55/103 —
raises the signal-to-noise of the new miners rather than adding a checkbox.

---

## 2026-07-30 — S3: record proof-strategy failures into the failure memory (S→Y loop)

New `strategy_log.py` (Track S3). S2's portfolio reports an honest status per problem — solved / unsolved
/ exhausted — but until now a non-solution just evaporated. S3 is the feedback edge from S2 into Track Y
(`failure_memory`): `exhausted` → a `timeout` record (a resource failure — the budget could afford no
strategy), `unsolved` → a `dead_end` record (strategies ran, none settled it), `solved` → nothing (a
success is not a failure). Recording is idempotent (the memory dedups by fingerprint), so re-logging a
failed problem never inflates the count. Alongside the logging, `diagnose_portfolio` aggregates exact
per-strategy statistics — times launched, times SKIPPED as unaffordable, times it won — and exposes the
`bottleneck`: the strategy most often skipped. On a battery mixing tight and ample budgets, the bottleneck
is `direct-residue` (the O(m) full sweep, skipped whenever CRT fits a smaller budget) — a real, actionable
insight the engine now keeps instead of silently re-deriving. This closes the S→Y loop: portfolio dead
ends accumulate alongside refuted conjectures in the shared negative-knowledge store. 7 tests; full suite
**1720 green**, ruff clean. Roadmap S3 🟢 (newly touched; progress ~55/103, next user check-in at 59 — 4
away).

---

## 2026-07-30 — Report wiring: the new miners now SURFACE in run_report (AC2 depth)

Modified `report.py`. The batch's new discovery miners (non-linear degree-2 laws, ratio/monotone
patterns, P5 dedup) were built but not visible in the engine's ONE deterministic report — half-wired.
This surfaces them, honestly. New `_richer_laws(max_n)`: (1) mines degree-2 laws and adds them as fresh
empirical findings — but ONLY in the WELL-DETERMINED regime (samples > features), because degree-2 mining
OVERFITS when the sample is small (at n≤4, 19 graphs ≪ 36 features → a huge null space of sample-true-but-
meaningless laws; the guard skips them rather than polluting the report — a real honesty save caught while
testing); (2) runs P5 `normalize_conjectures` across the linear + non-linear + ratio miners and adds a
`meta["corroboration"]` list of facts found by MORE THAN ONE miner. Result: at n≤6 the report carries the
clean `4·num_edges² = sum_degrees²` degree-2 law, and at every n a corroboration line — `2·num_edges =
sum_degrees` found by BOTH the linear and ratio miners (×2), rendered as
`_corroboration (P5): 1 fact(s) found by >1 miner …_`. SAMPLE-REPORT.md regenerated to match. 2 new report
tests pin the wiring; full suite **1713 green**, ruff clean. HONEST accounting: DEEPENS the already-✅ AC2,
count stays ~54/103 — it makes the batch's capabilities actually USED in the primary output, and the
overfitting guard keeps the addition honest rather than noisy.

---

## 2026-07-30 — AC0 wiring: the director now goal-selects via T2 (loop closed)

Modified `director.py` (Track AC0). The research director previously picked its next goal from raw
IMPACT (entanglement — the most-connected open conjecture). It now picks from `lemma_ranking.rank_lemmas`
(T2), which fuses that entanglement (importance) with `gap`'s proximity-to-proof (likelihood) into one
priority — closing the discover → prioritize → pursue loop with the T0/T2 signals built this batch. The
policy degrades gracefully: when no open goal is near proved ground (likelihood uniform), priority
reduces to entanglement, so behaviour is never worse than before; when some goals ARE reachable, the
director prefers the important-AND-reachable one. `CycleResult` now carries `top_lemma`
(statement/priority/importance/likelihood) so the choice is auditable, and a test pins that the director's
pick is exactly `rank_lemmas`' top on the same report. The existing frontier-targeting test was updated
to assert the new (strictly richer) policy — an honest policy improvement, not a weakening. Rule-based and
deterministic still (an honest AC0, not a learned planner — that stays 🔴). Full suite **1711 green**,
ruff clean. HONEST accounting: DEEPENS the already-touched AC0, count stays ~54/103 — it makes the
director genuinely use the new signals rather than adding a checkbox.

**Note on trajectory:** with this, the batch's new discovery signals (gap, lemma-ranking) are not just
built but WIRED into the researcher. The easily-reachable NEW phases are now thin; remaining high-value
work is depth (hardening ~26 partials toward fully-✅). Prioritizing value over touched-count from here.

---

## 2026-07-30 — P5: normalize + deduplicate conjectures across miners

New `conjecture_normalize.py` (Track P5). The engine now mines conjectures from several sources — linear
laws (`relations`), degree-2 laws (`nonlinear_relations`), constant ratios (`pattern_mining`) — and they
OVERLAP: the Handshake Lemma surfaces as the linear law `2·num_edges = sum_degrees` AND as the ratio
`sum_degrees/num_edges = 2`, the same equation in different clothes. P5 puts every linear-form conjecture
into one CANONICAL key (divide by the gcd to primitive form, then fix the sign so the alphabetically-first
feature is positive) so duplicates collapse and multi-source agreement becomes visible. A ratio `A/B =
p/q` is first turned into the relation `q·A − p·B = 0` before keying, so it collides with the equivalent
linear law — verified: over Kₙ, Handshake is reported ONCE with corroboration = 2 (found independently as
a law and as a ratio), instead of twice. HONEST: dedups by exact equality of the LINEAR NORMAL FORM only —
non-linear laws are keyed on their product feature names so a quadratic never collides with a linear law,
it never over-merges genuinely-different conjectures, and it carries every source forward as provenance so
a merge is auditable. 8 tests; full suite **1710 green**, ruff clean. Roadmap P5 🟢 (newly touched;
progress ~54/103, next user check-in at 59 — 5 away).

---

## 2026-07-30 — U1: walk a number-theory claim along the representation chain

New `nt_chain.py` (Track U1). Where U0 registers individual bridges, U1 is the CHAIN — routing a claim
through a sequence of representations until one DECIDES it. The roadmap's full chain is "Diophantine →
modular → lattice → SAT/SMT → finite-residue → algebraic-geometry"; the engine honestly walks the
decidable SEGMENT for polynomial divisibility: Diophantine → modular `p(n)≡0 (mod m)` → finite-residue
table → decision. For a UNIVERSAL claim the all-zero table decides it, cross-confirmed by the kernel's
RESIDUE theorem; for an EXISTENTIAL claim the SAME table decides it (any zero ⇔ a solution), which exposes
a real distinction the kernel alone does not — `5|n³−n` is FALSE for all n yet TRUE for n=5, and the walk
reports both truthfully. The honesty is in the ledger: `links_walked` lists the segment actually
traversed and `links_not_walked` names the roadmap links it does NOT cover (lattice, SAT/SMT,
algebraic-geometry), so the walk never pretends to span more of the chain than it does. Builds on U0's
residue-table bridge. 8 tests; full suite **1702 green**, ruff clean. Roadmap U1 🟢 (newly touched;
progress ~53/103, next user check-in at 59 — 6 away).

---

## 2026-07-30 — Ratio & monotonicity pattern mining (P0 breadth)

New `pattern_mining.py`. P0 is "pattern mining: equality / inequality / MONOTONICITY / periodicity /
asymptotic / forbidden-structure"; equalities (linear + degree-2) and inequalities were already covered,
so this adds two more of the listed kinds, exactly. CONSTANT RATIOS: invariant pairs (A,B) with A/B one
exact rational across the sample (skipping pairs where B=0 anywhere; keeping only the ≥1 direction to drop
the inverse duplicate) — this rediscovers the Handshake Lemma in RATIO form, `sum_degrees/num_edges = 2`,
on every edge-having family. MONOTONIC TRENDS: over objects sorted by a key invariant, which invariants
move strictly/weakly monotonically — on Kₙ ordered by num_vertices, num_edges / sum_degrees / num_triangles
/ max_degree all strictly increase. Exact `Fraction` arithmetic (a reported ratio is exact, not a float),
and the same honesty as the rest of O2/P0: every pattern is `status="empirical"` — sample-true conjecture,
not a theorem; monotonicity is a statement over the given ordering, not a universal-trend proof. 7 tests;
full suite **1694 green**, ruff clean. HONEST accounting: DEEPENS the already-✅ P0, so the touched count
stays ~52/103.

---

## 2026-07-30 — T2: rank candidate lemmas by importance × likelihood

New `lemma_ranking.py` (Track T2). The research director faces a queue of open goals; two exact signals
already exist but pull apart — `impact.py` (X3) measures IMPORTANCE (entanglement with known results) and
`gap.py` (T0) measures proximity-to-proof. A goal can be important yet unreachable, or reachable yet
peripheral. T2 fuses them into one actionable priority: importance = `related_to` entanglement normalized
over the open set, likelihood = `1 − gap_score`, priority = a transparent weighted sum (default 0.5/0.5,
adjustable). `rank_lemmas` returns open goals highest-priority first — both worth settling AND within
reach; `next_lemma` gives the single top target for the director (AC0). Verified on a hand-built graph: a
near+entangled conjecture outranks an isolated one, and resolved (proved/refuted) nodes are excluded.
HONEST: a transparent heuristic over two EXACT structural signals — not a learned model (that is W3/S4,
🔴) — every component exposed for audit, and it ranks ATTENTION only, never truth. 7 tests; full suite
**1687 green**, ruff clean. Roadmap T2 🟢 (newly touched; progress ~52/103, next user check-in at 59).

---

## 2026-07-30 — U0: a verified registry of representation transforms

New `representations.py` (Track U0). The engine already crosses between representations everywhere —
graph↔matrix, graph↔SAT, divisibility↔finite-residue, composition↔subset. U0 makes that plurality
EXPLICIT and VERIFIED: each bridge is registered with the guarantee it offers and a check that confirms
it on a sample. Where O4 (`cross_check`) confirms invariant VALUES agree across computation paths, U0
confirms the TRANSFORMS themselves are faithful — a complementary net that catches a broken
encoder/decoder, not just a mismeasured number. Three honest guarantee kinds: round_trip (invertible —
graph↔adjacency-matrix and composition↔cut-point-subset both satisfy decode∘encode = identity over the
whole sample), invariant_preserving (lossy but keeps a stated invariant — graph→degree-sequence preserves
Σdeg = 2|E|), and decision (the target representation DECIDES a claim — the residue table [p(r) mod m] is
all-zero iff the kernel proves m|p(n); the two verdicts must AGREE, checked on a 4-case battery incl.
6|n³−n true and 5∤n³−n false). All four bridges faithful; a False would be a real encoding bug. Caught a
genuine latent issue while building: the decoder must emit canonical `frozenset` edges or round-trip
equality silently fails against `generate_graphs` — exactly the kind of encoder bug this registry exists
to catch. 7 tests; full suite **1680 green**, ruff clean. Roadmap U0 🟢 (newly touched; progress
~51/103, next user check-in at 59).

---

## 2026-07-30 — Non-linear (degree-2) relation mining (richer O2)

New `nonlinear_relations.py` — `relations.py` mines only LINEAR laws (null space of the affine feature
matrix). Many real identities are quadratic (`num_edges = n(n−1)/2` on complete graphs), so this extends
the SAME exact null-space machinery to a DEGREE-2 polynomial feature map: it augments the invariants with
every pairwise product invᵢ·invⱼ and square invᵢ², then mines the null space of that matrix. Two honest
guards keep the output meaningful: (1) constant invariants are dropped from the feature map (a constant
like num_components≡1 only spawns degenerate X = X·const laws — those belong to `discover_constants`);
(2) REDUCIBLE laws that factor as (a lower law)·(a common invariant) are filtered — e.g.
`2·num_edges·max_degree = sum_degrees·max_degree` is just Handshake × max_degree, not a new fact.
Results: on complete graphs it rediscovers `num_vertices + 2·num_edges = num_vertices²` (i.e. 2·num_edges
= n²−n, the edge count C(n,2)) plus other genuine Kₙ identities; on the rich all-graphs sample it returns
only `4·num_edges² = sum_degrees²` (the square of Handshake) — honestly finding NO new universal quadratic
law, rather than manufacturing one. Same exact rational arithmetic, same honesty contract: every law is
`status="empirical"` (sample-true conjecture, not a theorem), degree-2 bounded (a cubic identity like
num_triangles = C(n,3) is deliberately not forced). 6 tests, each verifying the mined law holds EXACTLY
over the sample; full suite **1673 green**, ruff clean. HONEST accounting: DEEPENS the already-✅ O2, so
the touched count stays ~50/103.

---

## 2026-07-30 — M-floor COMPLETE: elementary divisibility lemmas made explicit

New `divisibility.py` (Track M, kernel floor — completes the trust-base thread). After `congruence.py`
(RESIDUE, CRT) and `sum_derivation.py` (SumInduction), the kernel's trusted base read "PolyIdentity +
elementary integer divisibility". That last phrase was the one remaining hand-wave — the two lemmas the
derivations lean on were cited, never exhibited. This module exhibits them: ADDITIVE (`m|a ∧ m|b ⇒
m|a+b`, witness quotient a/m + b/m, from distributivity ms+mt=m(s+t)) and ABSORPTION (`m|a ⇒ m|a·k`,
witness (a/m)·k, from associativity (ms)k=m(sk)). These are EXACTLY the steps in the RESIDUE derivation:
n≡r ⇒ m|(n−r), ABSORPTION gives m|(n−r)·q(n)=p(n)−p(r), ADDITIVE combines with m|p(r) to get m|p(n) — a
test pins that correspondence. Each instance carries a constructive witness verified by exact integer
arithmetic; `verify_lemmas(8)` exhausts 4624 cases (2312 additive + 2312 absorption) with ZERO failures.
HONEST status: `bounded_check` + constructive witness per instance; the universal ∀ rests on ℤ's ring
axioms (distributivity/associativity) — the bedrock the whole kernel already stands on, recorded not
re-proved (there is no "below"). Net effect: the entire kernel trust base is now auditable — exact
polynomial identity + these elementary lemmas + induction, nothing hand-waved. 7 tests; full suite
**1667 green**, ruff clean. HONEST accounting: DEEPENS the already-touched M2, so the count stays ~50/103
— it closes a rigor gap, not a checkbox.

---

## 2026-07-30 — AA4: connect a discovered algorithm to its proof (the S/M bridge)

New `algorithm_proof.py` (Track AA4). The engine discovers algorithms that DECIDE or CONSTRUCT
(residue-exhaustion decides `m|p(n)`; greedy first-fit colors a graph; a max-clique search witnesses ω).
AA4 is the bridge that, for such an algorithm's output, attaches the proof object justifying it AND
labels — honestly — the MODALITY and STRENGTH of that justification, without re-proving anything: it
LINKS the strategy/algorithm layer (S, AA) to the proof layer (M, certificates). A modular decision
algorithm links to a KERNEL Theorem (modality "kernel", `kernel_verified` — a universal ∀n machine proof
with hash + axioms); a greedy-coloring / max-clique algorithm links to a CONSTRUCTIVE certificate
(modality "certificate", `constructive_bounded` — an explicit witness over the sample, NOT ∀G). WHY it
matters: every discovered algorithm now carries its warrant, and the bridge is honest about the gap
between the two strengths — it never labels a graph certificate `kernel_verified`, and it reports
`verified=False` (not a fabricated proof) when the underlying check fails (e.g. the false claim
`5∤n³−n`). Reuses `prove_divides` + the `graph_proofs` certificates — pure linking, no duplication.
7 tests; full suite **1660 green**, ruff clean. Roadmap AA4 🟡→🟢 (newly touched; progress ~50/103,
next user check-in at 59).

---

## 2026-07-30 — Sixth object domain: integer compositions (cut-point bijection)

New `compositions.py` — a SIXTH domain through the same pipeline (after graphs, arithmetic, permutations,
integer partitions, set partitions). A composition of n is an ORDERED tuple of positive parts summing to
n. The gem is a clean CONSTRUCTIVE bijection: the cut-point map sends a composition (a₁,…,a_k) to its set
of partial sums {a₁, a₁+a₂, …} ⊆ {1,…,n−1}; it is explicit and invertible (`cutset_to_composition`
round-trips every composition) and lands on ALL 2^(n−1) subsets — so it PROVES #{compositions of n} =
2^(n−1) (OEIS A011782) constructively, at the same honesty level (`constructive_bijection`) as
Euler/Glaisher in `bijections.py`, not by count-and-hope. Also mines #{comps into k parts} = C(n−1,k−1)
(stars and bars, bounded_check). Honest bound n ≤ 15 (2^14 comps), no silent cap; deterministic,
memoized. WHY it matters: the architecture absorbed a sixth type with ZERO changes to the report /
ladder / explanations / scorecard — more evidence the object+invariant+law pipeline is genuinely
domain-independent. 7 tests; full suite **1653 green**, ruff clean. HONEST accounting: this DEEPENS the
Matter/Discover clusters (N0 "combinatorial obj" is already ✅), so the touched-phase count stays 49/103
— a real new domain, not a new checkbox. N0 line updated to "six domains" (ADR-D0047).

---

## 2026-07-30 — S2: resource-bounded strategy portfolio + budget manager  ⭐ user check-in @ 49

New `portfolio.py` (Track S2). S0 is the strategy registry and S1 the classifier that picks a portfolio;
S2 RUNS several strategies under one shared budget and accounts for the resource each consumes. For a
modular claim `m | p(n)` the kernel offers two strategies with very different costs: direct-residue (a
single sweep at m, cost ≈ m) and crt-prime-powers (a sweep at each prime power + a CRT combine, cost
≈ Σpᵢ^{eᵢ} + #parts — far cheaper for composite m: 30 → 13 vs 30). The executor models an idealized
PARALLEL race under a shared step-budget, deterministically (no OS threads / wall-clock — reproducibility
first): it launches affordable strategies cheapest-first while cumulative cost fits the budget, runs each
(kernel-checked), and names the WINNER as the lowest-cost strategy that actually proves it — the one that
would finish first in a real race — plus a full cost ledger. Honest `status`: **solved** (winner named),
**unsolved** (strategies ran but none proved it — e.g. a FALSE claim → refuted, surfaced not hidden), or
**exhausted** (budget too small to launch anything — says so, names the costs it could not afford). By
construction it never reports a proof it did not kernel-check. Verified: 6|n³−n at budget 100 → direct
wins (cost 6 < CRT 7); 30|n⁵−n at budget 15 → only CRT affordable, wins; budget 5 → exhausted; 5∤n³−n →
unsolved/refuted. 7 tests; full suite **1646 green**, ruff clean.

**⭐ USER CHECK-IN — 49 touched reached.** This is the ~10-phase notification the user asked for. State
of play: 103 phases / 21 tracks (plan frozen, guarded), **28 fully ✅**, **~49 touched** (✅ + real
partials). 12 phases are 🔴 honest open-research boundaries I will NOT fake (novel-to-literature math,
learned/RL models, forcing/independence AB2–3, missing-concept prediction T1/S4), so the achievable
ceiling is ≈ 91 → **~42 achievable phases remain**. Roadmap S2 🟡→🟢 (newly touched). This batch since
the last check-in: AB1 (axiom-minimal proofs), M-floor SumInduction derivation, P2 (generalization),
T0 (gap measure), S2 (portfolio) — plus the trust base is now fully shrunk (RESIDUE, CRT, AND
SumInduction all derived, no longer primitives). Next check-in at 59.

---

## 2026-07-30 — T0: goal ↔ knowledge gap measurement

New `gap.py` (Track T0). `impact.py` (X3) ranks the open frontier by ENTANGLEMENT (how many known
results a conjecture links to); T0 answers the complementary question — for a specific goal, how FAR is
it from established ground? It reports, all as exact graph computations, the goal's `status`
(proved/refuted → resolved, gap 0; else open/unknown), `distance_to_known` (BFS hops to the nearest
proved theorem/lemma/axiom, or None if no path reaches proof), `open_dependencies` (the transitive
`depends_on` nodes still unresolved — the concrete lemmas to discharge), and a `gap_score ∈ [0,1]`
(0 resolved, →1 as the goal gets farther / more dependent, exactly 1.0 when no path to proved ground
exists). `frontier_gaps` ranks open goals SMALLEST-gap first — the ones closest to being settled with
what is already known — a prioritization distinct from impact's centrality. WHY it matters: it gives the
research director a proximity-to-proof signal, not just a centrality one; a heavily-entangled conjecture
can still be unreachable, and a lightly-linked one may be nearly in hand. Honest boundary surfaced by
the measure itself: "known ground" is the engine's OWN proved theorems/axioms, so a goal in a domain
with no proved anchor (e.g. a graph bound while only arithmetic is kernel-proved) truthfully shows a
large gap — a real limitation made visible, not hidden. 7 tests (proved/refuted resolve to 0, near
< isolated, open-dependency widens the gap, unknown reported honestly, frontier ordering + from_report
integration, determinism); full suite **1639 green**, ruff clean. Roadmap T0 🟡→🟢 (newly touched;
progress ~48/103 — user check-in at 49 is 1 away).

---

## 2026-07-30 — P2: reverse-engineer a finding into its general principle

New `generalize.py` (Track P2). Where `identities.py` EXPLAINS one finding (`6|n³−n` holds because
`n³−n = (n−1)n(n+1)` is 3 consecutive integers, so `3!=6` divides it), P2 lifts that explanation over a
PARAMETER: from "3 consecutive ⇒ 3!" it proposes the general law "for every k, the product of k
consecutive integers is divisible by k!", then kernel-verifies the family for k=1..K — each
`k! | ∏_{i=0}^{k−1}(n+i)` is universal in n and proved by the kernel's RESIDUE rule (1|n, 2|n(n+1),
6|n(n+1)(n+2), 24|…, 120|…, 720|…). The specific finding is reported as the k=3 instance. HONEST on the
quantifier: each tested instance is kernel_verified, but the ∀k statement is the classical
binomial-integrality theorem `C(n,k)=∏/k! ∈ ℤ` — a cited structural_argument, NOT machine-proved for
unboundedly many k. Crucially it REFUSES to force a generalization where the structure isn't there:
`30|n⁵−n` is true but `n⁵−n = n(n−1)(n+1)(n²+1)` has a non-linear factor, so it is not a consecutive
product — `generalize` returns `generalized=False` rather than inventing a bogus law. Builds on
`identities` (reuses its consecutive-run detector), no duplication. 8 tests; full suite **1632 green**,
ruff clean. Roadmap P2 🟡→🟢 (newly touched; progress ~47/103, user check-in at 49 is 2 away).

---

## 2026-07-30 — M-floor: SumInduction DERIVED (the induction step made explicit)

New `sum_derivation.py` (Track M, kernel floor — deepens M2). Third and last of the kernel's leaf
rules loses its black-box status. `congruence.py` already derived RESIDUE (from the factor theorem) and
CRT (from Bézout); this does the same for `SumInduction`. The claim `Σ_{i=1}^n f(i) = g(n)` reduces to
two explicit, independently-checkable facts: a BASE case `g(1) = f(1)` (an evaluation at n=1, not an
axiom) and an induction STEP `g(n) = g(n−1) + f(n)` — a UNIVERSAL polynomial identity that is handed to
the kernel's OWN `PolyIdentity` (`Identity`) rule and checked exactly in rational arithmetic. So
SumInduction is no longer a trusted primitive; it is a THEOREM about PolyIdentity + evaluation +
induction over ℕ. WHY it matters: it finishes shrinking the kernel's trust base to a single algebraic
core (exact polynomial identity) plus elementary arithmetic — the same move that made RESIDUE honest,
now applied to sums. Verified on Σ1=n, Σi=n(n+1)/2, Σi²=n(n+1)(2n+1)/6, Σi³=(n(n+1)/2)², Σ(2i−1)=n².
A parametrized test asserts the derived route accepts EXACTLY what the primitive SumInduction rule
accepts (birebir cross-consistency), and an independent no-kernel checker re-verifies base + step.
14 tests; full suite **1624 green**, ruff clean. Honest accounting: this DEEPENS the already-touched M2
(trust-base shrinking), so the touched-phase count stays ~46/103 — real rigor, not a new checkbox.

---

## 2026-07-30 — AB1: axiom-minimal proof search ("how little must we assume?")

New `axiom_minimize.py` (Track AB, independence/foundations). A theorem can rest on different axiom
sets; AB1 asks which kernel-checked proof uses the SMALLEST one. For a modular claim `m|p(n)` the
kernel offers (at least) two proof terms: a DIRECT residue sweep at `m` (footprint `{RESIDUE(m)}`, one
rule) and a CRT decomposition over prime powers (`{CRT, RESIDUE(p₁^a₁), …}`, several rules). The module
enumerates both, keeps only those the kernel actually accepts (`check`), reads each footprint off the
provenance layer (`axioms_used`), and returns the fewest-axiom proof (ties broken deterministically).
Result: `6|n³−n` is provable by `RESIDUE(6)` ALONE — the CRT proof, though valid, is not axiom-minimal
(3 rules vs 1); `30|n⁵−n` likewise reduces to `RESIDUE(30)`. WHY it matters: it makes the trust
question ("how little do we need to assume?") mechanical and honest, and it's the natural companion to
`congruence.py`'s trust-base shrinking. Reuses the existing kernel + provenance — no new axioms
introduced. 5 tests; full suite **1610 green**, ruff clean. Roadmap AB1 ✅ (progress ~46/103; user
check-in at 49 is 3 phases away).

---

## 2026-07-30 — P1 theorem mutation + systematic P0 conjecture generation

**Systematic P0** `feature_conjectures.py`: instead of a few hand-picked bounds, generate ALL pairwise
invariant inequalities from the O3 feature table and test each refute-first (42 conjectures on the
graph invariants → 11 survive, 31 refuted with minimal witnesses). **P1** `mutate.py` — theorem
mutation: STRENGTHEN a survivor (largest multiplier / additive slack) or REPAIR a refuted claim
(smallest weakening that holds). Striking result: mutation sharpens the loose `num_edges ≤ sum_degrees`
into `2·num_edges ≤ sum_degrees` — i.e. it rediscovers the tight Handshake identity as the sharpest
form; and repairs the K6-refuted `num_triangles ≤ num_edges` into `… ≤ num_edges + 5`. Every mutation
is re-tested counterexample-first, so it's as honest as the original bound. 12 tests; full suite
**1605 green**, ruff clean. Roadmap P1 ✅ (progress ~45/103).

---

## 2026-07-30 — O4: multi-path invariant consistency cross-check

The verification engine now verifies its OWN measurements. New `cross_check.py`: compute each
invariant by INDEPENDENT routes and confirm agreement — |E| four ways (edge count, Handshake Σdeg/2,
trace(A²)/2, MathHead's Σλ²/2) and #triangles three ways (combinatorial, trace(A³)/6, MathHead Σλ³/6).
`all_consistent` runs it over all graphs n≤5 AND the adversarial stress set: 0 disagreements — a
self-test of the invariant + spectral code (any route mismatch is a real bug caught). 5 tests; full
suite **1593 green**, ruff clean. Roadmap O4 ✅ (progress ~44/103).

---

## 2026-07-30 — N-track COMPLETE: object store (N6) + adversarial generators (N5)

Finished the whole object-model track (N0–N6). **N6** `object_store.py`: a content-deduplicated store
with an inverted index on invariant values — `add` (idempotent) then `query(chromatic_number=3,
num_triangles=0)` returns C₅ (triangle-free yet 3-chromatic — a nice fact the store surfaces by set
intersection). Built on N3 (hash dedup) + O1 (invariants). **N5** `adversarial_objects.py`: random /
adversarial / extreme generators — degenerate (edgeless, disconnected), extreme (K_n, K_n−e), and
seeded-random — assembled into a `stress_set`; every invariant runs over all 61 stress objects with
**0 crashes** (robustness confirmed), and seeded randomness is reproducible.

That closes Track N entirely (typed objects, canonical generation, iso-elimination, serialization,
families, adversarial, store). 10 tests; full suite **1588 green**, ruff clean. Roadmap N5, N6 ✅.

---

## 2026-07-30 — Object-model infrastructure: parametric families (N4) + generic serialization (N3)

Two untouched N-track phases done. **N4** `families.py`: named parametric graph families at ANY size
— K_n, C_n, P_n, star, wheel, K_{a,b} — plus `stratified_sample`, so discoveries/bounds can be probed
on infinite families and tests get diverse structure. Each family's invariants match a KNOWN closed
form (K_n: C(n,2) edges, χ=ω=n; C_n: χ=2/3; …), so it doubles as a cross-check oracle for the invariant
code. **N3** `serialize.py`: one generic canonicaliser over ALL five object types (frozen dataclasses)
→ `content_hash`, `reproducible_sort`, `deduplicate`; deterministic, stdlib-only. 12 tests (families 6
+ serialize 6); full suite **1578 green**, ruff clean. Roadmap: N4, N3 marked ✅ (22/103 fully done,
41/103 touched).

---

## 2026-07-30 — Tracker automation completed with a commit-time git hook

Closed the automation loop locally: `scripts/hooks/pre-commit` runs `gen_status.py` on every commit —
refreshes SAMPLE-REPORT.md + TODO's stats line, re-stages them, and blocks the commit if the frozen
PLAN shrank. Activated here via `git config core.hooksPath scripts/hooks` (one-liner per clone; graceful
skip if deps aren't installed, since CI is the hard gate). So the trackers now stay current at three
levels — commit hook (local), the `trackers` CI job, and `tests/test_trackers.py` — with no manual
step. Docs/tooling only.

---

## 2026-07-30 — Tracker automation: plan-integrity guard + sample freshness in CI

Wired the bookkeeping into automation so it can't silently drift. New `scripts/gen_status.py`:
`refresh` regenerates `SAMPLE-REPORT.md` and rewrites TODO.md's stats line from the live engine;
`--check` guards the frozen PLAN (asserts exactly **103 phases across 21 tracks** — the full to-do
list can never be silently lost) and that the sample report is in sync (code = docs). New
`tests/test_trackers.py` enforces all of it inside pytest, and a dedicated `trackers` CI job gives a
fast early signal. So: the plan is guarded, the sample stays current, and "did we lose the list?" is
now answered by CI, not memory. 4 tests (discovery + tracker suite); full suite green, ruff clean.

Verified the plan is intact: 103 phases / 21 tracks, byte-for-byte since the original roadmap commit
(f034464).

---

## 2026-07-30 — Report surfaces the shrunk trust base (M-floor made visible)

Closed the loop from the RESIDUE/CRT derivations: the flagship report header now shows the trust base
— "RESIDUE derived from the factor theorem (7/7), CRT from Bézout (7/7) — primitives are theorems, not
axioms". `meta.trust_base` carries the counts; computed from the arithmetic findings' `residue_derivable`
/`crt_derivable` flags. Small polish, but it makes the deepest result (a shrunk kernel trust base)
legible in the one artifact a reader sees. 1 test (discovery suite 272); full suite **1562 green**,
ruff clean. (Rationale inline; DECISIONS.md frozen.)

---

## 2026-07-30 — Bookkeeping: consolidated to THREE fixed tracking files

Tidied the record-keeping to a fixed, minimal set (no more ad-hoc new docs): **PLAN** =
`IDEAL-ENGINE-ROADMAP.md` (frozen full plan) · **TODO** = `TODO.md` (done/next/open, updated every
task) · **CHANGELOG** = `PROGRESS.md` (this file, updated every task). Renamed STATUS.md → TODO.md;
removed ARCHITECTURE.md (redundant with TODO's done-section + code); froze DECISIONS.md as an ADR
archive (ADR-D0001…D0042) with future rationale folded inline here. Also fixed four entries misdated
07-29 → 07-30 and the analogy label P4 → P3. Docs only; suite unaffected.

---

## 2026-07-30 — Structured known-results catalog (X1/W2): the auditable basis for "0 novel"

The scorecard's attribution was a flat substring list; now it's a structured, cited KNOWLEDGE BASE.
New `known_results.py`: 21 entries across 5 domains, each with name, reference (author-year or OEIS),
domain, and identifying markers. `evaluation.attribute` sources from it (single source of truth; the
dead inline list removed). `attributed_findings(report)` pairs every finding with the known theorem it
matches + citation — the auditable basis for the honest "rediscovery, not discovery" verdict (48
findings, 100% attributed, 0 novel). Delivered a "Rediscovered Mathematics" catalog artifact grouped
by domain. A real literature corpus would EXTEND this catalog; the 0-novel verdict does not change
until one is ingested. 4 tests (discovery suite 271); full suite **1561 green**, ruff clean. ADR-D0042.

---

## 2026-07-30 — Shrinking the kernel's trusted base: RESIDUE DERIVED from the factor theorem (M-floor)

The honest caveat carried by every kernel ADR — "RESIDUE is a trusted PRIMITIVE, not derived" — is now
removed for the modular fragment. New `congruence.py` DERIVES the residue principle, using the kernel's
OWN `PolyIdentity` rule (no new trusted machinery):

- for each residue r, the FACTOR THEOREM gives p(x) − p(r) = (x − r)·q_r(x) — verified EXACTLY as a
  kernel PolyIdentity (the universal step: it holds for all x, hence all integers n);
- for n ≡ r (mod m): m | (n − r), so m | (n − r)·q_r(n) = p(n) − p(r); with the residue check m | p(r),
  we get m | p(n). Ranging r over all residues covers every n.

So residue-exhaustion is no longer a black box — it is a THEOREM about the factor theorem plus
elementary integer divisibility. An independent checker re-verifies the whole derivation WITHOUT the
kernel. All 7 modular family laws are now `residue_derivable` (6|n³−n, 30|n⁵−n, 42|n⁷−n, …); false
claims (4∤n²+1) are correctly not derivable — the factor identities still hold, but the residues don't
vanish.

The trusted base for the modular fragment shrank from "residue-exhaustion" to "the factor theorem
(exact polynomial arithmetic, already in the kernel) + m|a∧m|b⇒m|a+b, m|a⇒m|a·k". 6 tests (discovery
suite 261); full suite **1551 green**, ruff clean. ADR-D0040. Roadmap M (kernel floor).

**Next:** derive SumInduction/PolyIdentity likewise, or corpus-backed novelty.

---

## 2026-07-30 — Cross-domain analogy detection (P3)

With five domains and a rich explanation layer, the engine now notices when the SAME proof technique
recurs across genuinely different objects. New `analogy.py` tags each explained finding with its
technique (double counting, constructive bijection, recurrence, factorization, …) and reports the
techniques that span two or more domains. On the report it finds: **constructive bijection** spanning
permutations (Mahonian) and integer partitions (Euler/conjugation); **recurrence** spanning
permutations (Eulerian) and set partitions (Stirling). Honest: it claims a shared PROOF SHAPE (pattern
match over the explanation texts), not a deep equivalence — but the shapes are real. Surfaced as a
CROSS-DOMAIN ANALOGIES section. 4 tests (discovery suite 267); full suite **1557 green**, ruff clean.
ADR-D0041. Roadmap P4.

---

## 2026-07-30 — M-floor continued: CRT derived from Bézout

The other modular primitive, CRT, is now derived too. `congruence.derive_crt(m1,m2)`: extended Euclid
gives s·m1 + t·m2 = 1, so x = x·(s·m1+t·m2) = s·m1·x + t·m2·x, each term divisible by m1·m2 (using
m2|x, m1|x) ⇒ m1·m2 | x. So CRT's soundness reduces to Bézout (checkable extended Euclid) + elementary
divisibility, not a trusted composition primitive. `crt_chain_is_derivable` verifies every pair of the
prime-power moduli; all 7 arithmetic family findings carry `crt_derivable=True`, non-coprime pairs
rejected. Independent re-check confirms the Bézout identity and coprimality. Both modular primitives
(RESIDUE, CRT) are now theorems, not axioms. 2 tests (discovery suite 263); full suite **1553 green**,
ruff clean. Extends ADR-D0040.

---

## 2026-07-29 — Consolidation: ARCHITECTURE.md, an honest synthesis of the whole engine

After 5 domains, the kernel, constructive certificates/bijections, and the meta layers, wrote
`docs/discovery/ARCHITECTURE.md` — a coherent, code-backed synthesis of the engine: the pipeline
(generate→measure→mine→conjecture→refute→prove→verify→explain→organize→grade), the five domains, the
proof kernel + its three companions (provenance, checker, adversary), the certainty hierarchy and the
four-rung ladder, the explanation layer (algebraic/structural/bijective), and the director.

Crucially it ends with "What is deliberately NOT done" — no novel mathematics (0 established), no
universal graph/combinatorial proofs (bounded), the kernel's primitives trusted not derived, the
heuristics not learned. Every number in it is introspected from the live engine (36 modules, 254
tests, 40 ADRs, ladder L2=37/L3=10/L4=17, scorecard 0 novel), not aspirational. Delivered to the user.

Docs only; no code change. Full suite unaffected (1544 green).

**Next:** the deeper frontier — corpus-backed novelty (X1/W2) or deriving the kernel primitives (M).

---

## 2026-07-29 — A FIFTH domain: set partitions (Bell & Stirling numbers)

Another structurally distinct domain — partitions of a SET (not an integer). New `set_partitions.py`
generates all set partitions of [n] via restricted-growth strings (honest bound n≤9, B(9)=21147,
pinned to OEIS A000110 = Bell numbers), measures invariants (block count, largest block, singletons),
and discovers two facts with an independent cross-check:

- **B(n) = Σ_k S(n,k)** — Bell is the row-sum of the Stirling numbers of the 2nd kind (every partition
  has some k blocks).
- **#{partitions with k blocks} = S(n,k)** — the block-count distribution matches S(n,k) computed
  INDEPENDENTLY from the Stirling recurrence S(n,k)=k·S(n−1,k)+S(n−1,k−1) (OEIS A008277) — a real
  cross-check.

FIVE domains now flow through the identical pipeline (graphs, arithmetic, permutations, integer
partitions, set partitions). Folded into the report; scorecard attributes Bell/Stirling as known, so
novelty stays honestly 0.

8 tests (discovery suite 255); full suite **1544 green**, ruff clean. ADR-D0039.

**Next:** corpus-backed novelty (X1/W2), a deeper kernel, or consolidate the whole engine into one
synthesis document.

---

## 2026-07-29 — Foata's bijection: the Mahonian equidistribution now constructively proven too

Extended the constructive-bijection treatment to the permutation Mahonian fact. Implemented Foata's
SECOND fundamental transformation Φ — and, honestly, PINNED DOWN the exact variant empirically: a
parametrized search over cut-predicate and shift direction found the one (cut after ≤a when the last
letter ≤a, else after >a; shift each block's last letter to the front) for which Φ is a bijection of
S_n with inv(Φ(π)) = maj(π), verified through n=8. The verification IS the correctness check — a wrong
transformation would fail the bijection/statistic test and never ship.

`certify_mahonian_bijection` verifies it on n≤7; the report upgrades the Mahonian explanation from
`structural_argument` to `constructive_bijection`. Three equidistributions are now constructively
proven (Foata/Mahonian, Glaisher/Euler, conjugation) — FORMALLY_SPECIFIED (L3) rose to 10.

2 net new tests (discovery suite 247); full suite **1536 green**, ruff clean. ADR-D0038 (extended).

**Next:** corpus-backed novelty (X1/W2), a deeper kernel, or a fifth domain.

---

## 2026-07-29 — Constructive bijections: PROVING the partition equidistributions (Glaisher + conjugation)

An equidistribution is best proven by exhibiting a BIJECTION — so the engine now does, and checks it.
New `bijections.py` builds the classical bijections explicitly and verifies each really is a bijection
on the sample, upgrading the two partition facts from `structural_argument` (conclusion counted) to
`constructive_bijection` (explicit map, re-checked injective + onto):

- **Euler distinct=odd** — GLAISHER's bijection: an odd part v of multiplicity m ↦ the distinct parts
  v·2^b over the binary digits b of m; the inverse splits a distinct part = odd·2^k into 2^k copies.
  Verified injective, onto, and round-tripping for every n≤18 — a genuine constructive proof of
  Euler's theorem (bounded).
- **conjugation** — transpose the Young diagram; verified to swap 'largest part' with 'number of parts'
  and to self-invert, so it bijects the two families.

The ladder recognizes the upgrade: `constructive_bijection` explanations now sit at FORMALLY_SPECIFIED
(L3), which rose 7→9. Honest ceiling: bounded (n≤18), the universal argument recorded not
machine-checked. This is the partition analogue of the graph constructive certificates (graph_proofs).

6 tests (discovery suite 245); full suite **1534 green**, ruff clean. ADR-D0038.

**Next:** Foata's bijection for Mahonian (inv~maj), corpus-backed novelty (X1/W2), or a deeper kernel.

---

## 2026-07-29 — A FOURTH domain: integer partitions, and Euler's distinct=odd theorem rediscovered

The most number-theoretic domain yet. New `partitions.py` gives integer partitions the standard
treatment — generate them all (honest bound n≤30, pinned to OEIS A000041 = p(n)), exact invariants
(number of parts, largest part, distinctness/parity, conjugate), and two discovered ensemble facts:

- **Euler's theorem** — #{partitions of n into DISTINCT parts} = #{partitions into ODD parts}, for
  every n (rediscovered by counting BOTH families and finding them equal; the sequence 1,1,2,2,3,4,5,6
  is OEIS A000009). A genuinely beautiful equidistribution, found from raw data.
- **conjugation symmetry** — #{largest part = k} = #{exactly k parts}, via transposing the Young
  diagram (conjugation is verified to be an involution that swaps the two statistics).

Both fold into the report (DISCOVERED + EXPLANATIONS), attributed as known (Euler 1748) so the honest
scorecard stays 0-novel. Four domains now flow through the identical pipeline (graphs, arithmetic,
permutations, partitions) — the architecture is domain-agnostic, demonstrated four times over.

6 tests (discovery suite 239); full suite **1528 green**, ruff clean. ADR-D0037.

**Next:** corpus-backed novelty (X1/W2), a deeper kernel, or push a distribution discovery toward a
machine-checked bijective proof.

---

## 2026-07-29 — Red-team the verifier: 600+ false claims, 0 breaches

A verification engine is only worth its soundness — so attack it. New `adversarial.py` runs a
systematic battery of FALSE claims and confirms every one is rejected:

- **600+ false modular claims** — enumerate small integer polynomials × moduli 2..6, keep the (m, p)
  where `m | p(n) ∀n` is actually FALSE, feed each to `prove_divides`: all must raise. 0 accepted.
- wrong sum closed forms, bogus factorizations (Identity), illegal rule applications (non-coprime CRT,
  mismatched polynomials, a SumIdentity fed to CRT), and direct theorem FORGERY — all rejected.
- the independent checker is attacked with false modular claims too — all rejected.
- **positive controls** (6|n³−n, 30|n⁵−n, Σi=n(n+1)/2) confirm the verifier still ACCEPTS truths —
  so it's sound, not merely rejecting everything.

Result: 613 attempts, **0 breaches**, 3/3 controls pass, `sound=True`. It can't prove the verifier
complete, but it demonstrates soundness on a broad, deterministic adversarial sweep — a single breach
(a false claim minted as a Theorem) would be a hard failure of the engine's whole premise. Kept as a
STANDALONE soundness harness (not wired into per-report generation — verification hardening is a
separate concern from discovery reporting).

7 tests (discovery suite 233); full suite **1522 green**, ruff clean. ADR-D0036.

**Next:** corpus-backed novelty (X1/W2), a deeper kernel (derive the primitives), or a new domain.

---

## 2026-07-29 — The honest scorecard (Track AF): is any of this actually NEW?

The uncomfortable question a discovery engine must ask itself — and answer plainly. New
`evaluation.py` grades the engine's own output on three axes:

- CORRECTNESS — kernel/solver/independently-verified findings are correct by construction; mined laws
  are sample-checked. Nothing false is reported (17/45 verified, the rest exactly checked).
- ATTRIBUTION — each finding matched against a curated registry of KNOWN results (Handshake, Fermat/
  elementary modular facts, Faulhaber sums, MacMahon, Eulerian, Dirac, factorizations…). Result:
  **100% attributable to known mathematics**.
- NOVELTY — **0 novel-to-literature established.** The engine correctly REDISCOVERS known mathematics;
  it has not produced a result absent from the literature. And full novelty-vs-literature isn't even
  measurable here — that needs corpus ingestion (X1/W2), which is NOT built. We say so rather than
  dressing rediscovery up as discovery.

The report gained a HONEST SCORECARD section with that headline. This is the project's honesty ethos
turned on itself: the machinery is validated (it rediscovers real theorems correctly and verifiably),
but it is not — yet — a source of new mathematics, and the scorecard states it in the report itself.

6 tests (discovery suite 226); full suite **1515 green**, ruff clean. ADR-D0035. Roadmap AF1.

**Next:** the honest path to actual novelty needs corpus ingestion (X1/W2) so "known" is checked
against a real library, not a curated list — or push the engine into a domain where it might find
something genuinely open.

---

## 2026-07-29 — The research director (Track AC): a goal-driven loop with cross-cycle memory

The engine stopped being a collection of modules and became a RESEARCHER. New `director.py`
(`ResearchDirector`) runs discovery CYCLES and carries state between them:

- cross-cycle STATE (AC3) — one `FailureMemory` accumulates dead ends across ALL cycles, deduped by
  fingerprint (a 3-cycle session learns 7→11→12 unique dead ends, never re-walking a closed branch); a
  `seen` set tracks which findings are new each cycle (51 → 3 → 0 as the sample stabilizes); the
  ladder distribution is recorded per cycle so progress is visible.
- strategy SELECTION (AC0) — after each cycle the director reads the impact analysis (the open
  frontier) and the ladder and proposes the next goal: settle the highest-impact open conjecture if
  one exists, else widen the bound / push validated laws toward proof. `run_session` then FOLLOWS its
  own recommendation into the next cycle.

Honest scope: the policy is deterministic and rule-based — an honest AC0, not a learned planner (that
is later work). The director decides WHAT to look at next; it never decides what is TRUE (it only reads
the report, never blesses a result).

6 tests (discovery suite 220); full suite **1509 green**, ruff clean. ADR-D0034. Roadmap AC0/AC3.

**Next:** a learned/heuristic strategy upgrade, a fourth domain, or push a structural argument to a
machine-checked proof.

---

## 2026-07-29 — Distribution-level discoveries: the engine rediscovers MacMahon & Eulerian

A step up from sum laws — the engine now discovers facts about whole DISTRIBUTIONS, not just totals.
Added `major_index` (maj), `statistic_distribution`, and an independent `eulerian_number` recurrence
to the permutations domain, then two distribution discoveries verified on n≤7:

- **Mahonian equidistribution** — inv and maj have the SAME distribution over S_n for every n
  (MacMahon's theorem, rediscovered from data by comparing the two distributions directly).
- **Eulerian numbers** — the descent distribution matches A(n,k) computed independently from the
  Eulerian recurrence A(n,k) = (k+1)A(n−1,k) + (n−k)A(n−1,k−1) (OEIS A008292).

Both fold into the report (DISCOVERED + EXPLANATIONS). These are honest: verified exactly on n≤7, with
the classical argument recorded (MacMahon has a bijective proof; Eulerian the recurrence) but not
machine-checked — `structural_argument`. The engine finding two named theorems from the raw ensemble
is the point.

5 tests (discovery suite 214); full suite **1503 green**, ruff clean. ADR-D0033.

**Next:** the research-director orchestrator (AC — cross-cycle state, goal-driven loop), or a fourth
domain, or push a distribution discovery toward a machine-checked proof.

---

## 2026-07-29 — A THIRD object domain: permutations (the object model generalizes)

The engine's object model was built to extend beyond graphs — this proves it. New `permutations.py`
gives permutations of {0,…,n−1} the same treatment: generate the whole ensemble S_n (honest bound
n≤7, pinned to OEIS A000142 = n!), measure exact invariants (inversions, descents, fixed points,
cycles), and DISCOVER ensemble laws from the data, each with the structural argument that explains it:

- `|S_n| = n!` — counting.
- `Σ_{π∈S_n} fix(π) = n!` — each of the n positions is fixed in (n−1)! permutations.
- `Σ_{π∈S_n} inv(π) = n!·C(n,2)/2` — each pair is inverted in half of S_n (π ↔ its reversal pairs
  inv(π) with C(n,2)−inv(π)).

All three verify on n≤6. Folded into the report: the laws enter DISCOVERED and their reasons the
EXPLANATIONS section (now 9: 3 algebraic + 3 graph + 3 permutation). Same honest layering as graphs —
discovered from data, explained structurally, conclusion checked on the sample.

7 tests (discovery suite 209); full suite **1498 green**, ruff clean. ADR-D0032. Roadmap: N/O/P over a
new object type.

**Next:** more permutation structure (cycle-type distribution, Mahonian inv/maj equidistribution), or
the research-director orchestrator (AC), or a fourth domain.

---

## 2026-07-29 — The epistemic ladder (AA3): one honest solidity axis over everything

The engine had accumulated a sprawling certainty vocabulary (empirical, bounded_check, numerical_check,
constructive_bounded, structural_argument, solver_verified, formal_proof, kernel_verified…). New
`epistemic_ladder.py` collapses it onto the document's FOUR rungs and classifies every finding:

- L1 DISCOVERED_HEURISTIC — mined, not yet attacked (transient; ~0 in a finished report).
- L2 EMPIRICALLY_VALIDATED — holds over the sample / survived refutation, not universally proven
  (mined laws, surviving bounds, structural arguments).
- L3 FORMALLY_SPECIFIED — a machine-checkable certificate on instances (solver-confirmed χ/Hamiltonicity
  values, constructively-certified bounds).
- L4 FORMALLY_PROVED — universally proven AND independently/kernel verified.

On the report: L2=23, L3=7, L4=17. The header shows the solidity distribution; `meta.ladder` carries
it. Honest by construction: the ladder never changes a finding's truth, it just names uniformly how
far the evidence goes; refuted items are OFF the ladder (negative knowledge, Y).

7 tests (discovery suite 202); full suite **1491 green**, ruff clean. ADR-D0031. Roadmap AA3.

**Next:** a new domain surface, or connect the ladder to the loop (promote findings up the rungs as
evidence accrues), or the research-director orchestrator (AC0/AC3).

---

## 2026-07-29 — "Explain why" reaches the graph domain: structural arguments for the laws

The explanatory thread crossed from arithmetic to graphs. New `structural_explanations.py` attaches
the classical STRUCTURAL argument behind each mined graph law and verifies its conclusion on every
sample graph:

- `2·|E| = Σ deg(v)` (the Handshake Lemma) — DOUBLE COUNTING the incidences {(v,e): v∈e}: sum by
  vertex → Σ deg(v); sum by edge → 2·|E|; the double count is checked exactly on all 52 graphs.
- `ω ≤ χ` — the clique's pairwise-adjacent vertices force distinct colors, so χ ≥ ω.
- `Hamiltonian ⟹ δ ≥ 2` — a cycle enters/leaves each vertex by two distinct edges.

These join the kernel-verified factorization explanations in the report's EXPLANATIONS section (now 6:
3 algebraic + 3 structural). HONEST label: each is a `structural_argument` — a genuine universal
argument in prose whose CONCLUSION is re-checked on the sample; the prose reasoning itself isn't
machine-checked (that needs the graph side of the kernel, still future), so NOT "proved".

5 tests (discovery suite 195); full suite **1484 green**, ruff clean. ADR-D0030.

**Next:** the epistemic ladder (AA3 — assign each finding a rung: discovered → empirical → certified →
kernel-proved), or a new domain, or push the graph kernel so a structural argument becomes machine-checked.

---

## 2026-07-29 — Factorizations that EXPLAIN the divisibilities (third kernel judgment: PolyIdentity)

A genuinely mathematical increment — the engine now explains WHY, not just THAT. Kernel gained a third
judgment `PolyIdentity` (p(n) = q(n) ∀n, via the `Identity` rule: p − q ≡ 0 — sound & complete). New
`identities.py` factors each polynomial and INDEPENDENTLY certifies the factorization with the kernel
(expand(p) must equal expand(factored) — it does not trust sympy.factor; a wrong factorization fails
the check).

The payoff is explanatory and ties threads together: when the factors are CONSECUTIVE integers, the
product is divisible by k!. So the engine reports `n³ − n = n(n−1)(n+1)` explains `6 | n³−n` (three
consecutive integers ⇒ divisible by 3! = 6) — the algebraic STRUCTURE explaining the modular NUMBER
found separately in arithmetic.py. Both kernel-checked. Report gains an EXPLANATIONS section and the
factorization identities enter PROVED (certainty `kernel_identity`); POLY_IDENTITY joins the axiom
manifest.

9 tests (6 identities + 2 kernel + 1 report; discovery suite 190); full suite **1479 green**, ruff
clean. ADR-D0029. Roadmap: algebraic-identity surface + M1 (third judgment).

**Next:** more explanatory links (why a bound is tight; why a law holds structurally), or a new domain,
or external-corpus novelty (X1/W2).

---

## 2026-07-29 — Impact analysis (Track X3): load-bearing axioms, hubs, the open frontier

New `impact.py` runs structural "so what?" analysis over the knowledge graph — all exact graph
computations, no guessing. `load_bearing_axioms` ranks inference rules by how many theorems depend on
them (RESIDUE(m=2) supports 6 proofs, CRT 5 — the leverage points: break one and many results move);
`most_connected` finds the hubs; `open_frontier` ranks OPEN conjectures by how entangled
(`related_to`) they are with known results — the highest-impact statements to settle next. The report
header now shows the most load-bearing axiom; `meta.impact` carries the full picture.

Honest scope: this is impact WITHIN the engine's own knowledge — descriptive centrality/leverage.
Saying "this settles conjecture C from the literature" needs external open-problem ingestion (X1/W2),
still open. 4 tests (discovery suite 181); full suite **1470 green**, ruff clean. ADR-D0028. Roadmap X3.

**Next:** ingest an external corpus for real novelty checks (X1/W2), or wire failure-memory into the
loop, or push a new domain surface.

---

## 2026-07-29 — Knowledge graph (Track X0): findings become a typed semantic graph

Findings stopped being a flat list. New `knowledge_graph.py`: a typed graph where nodes are
theorems / laws / conjectures / counterexamples / axioms and edges are typed relations. `from_report`
populates it, asserting only edges the engine can be CERTAIN of — `depends_on` (theorem → the kernel
axioms it rests on), `refuted_by` (conjecture → its counterexample witness), and symmetric
`related_to` (two statements sharing an invariant). On the report: ~48 nodes, ~123 edges (11
theorems, 7 axioms, 6 laws, 20 conjectures, 4 counterexamples).

Deliberately NOT fabricated: `generalizes`/`equivalent_to` edges — those need real entailment checks
(a judged pass, later X3), so the schema reserves the relations but the populator doesn't guess them
(tested). Ships a deterministic Mermaid export for visualization. The report header now shows the
graph summary; `meta.knowledge_graph` carries the counts.

9 tests (8 knowledge_graph + 1 report; discovery suite 177); full suite **1466 green**, ruff clean.
ADR-D0027. Roadmap X0. This is the substrate X3 (impact analysis) and W2 (novelty-vs-literature) run
over.

**Next:** impact analysis (X3 — which open problem would a result touch), or wire failure-memory into
the refute loop, or a new domain surface (AE — generate a genuinely new small lemma).

---

## 2026-07-29 — Interestingness ranking (Track W1): rank findings, transparently

The engine can now RANK what it found, not just list it. New `interestingness.py` scores each finding
by the document's components — novelty · generality · surprise · usefulness · compression ·
connectivity − triviality — each a named, deterministic proxy computed from the finding and its peers,
combined with documented (hand-set) weights into a [0,1] score that carries its full per-component
breakdown, so a ranking is always explainable.

On the real report it behaves sensibly: strong universal facts (composite modulus, kernel-verified —
n³−n mod 6, n⁵−n mod 30) top the list; the handshake lemma ranks high; the textbook-trivial χ≤n bound
sinks to 0.0 (low novelty + triviality penalty). The report gained a MOST INTERESTING section (top 5)
and `meta.most_interesting`.

HONEST framing, in the module and the report header: this is a HEURISTIC, not a learned or
ground-truth measure — a learned interestingness model with human feedback is Track W3 and stays OPEN.
It ranks and explains; it never decides what is true.

9 tests (8 interestingness + 1 report; discovery suite 169); full suite **1457 green**, ruff clean.
ADR-D0026. Roadmap W1.

**Next:** the knowledge-graph schema (X0 — store findings + relations: generalizes/refutes/equivalent),
or wire failure-memory `seen` into the refute loop, or a new domain surface.

---

## 2026-07-29 — Negative knowledge (Track Y): the engine remembers its dead ends

A discovery engine that forgets its failures re-walks them. New `failure_memory.py`: every closed
branch — a refuted conjecture, a timeout, a useless lemma, a dead-end transform (Y0) — is recorded
under a canonical FINGERPRINT (Y1: whitespace-normalized, kind-aware content hash), so `seen(...)`
lets the loop skip a dead end it already walked, and `record` is idempotent. `lessons()` distills
REUSABLE lessons (Y2): it clusters refuted conjectures by the WITNESS that killed them — a witness
that refutes many conjectures is a high-value probe to try FIRST on new look-alikes.

Wired into the report: the refutations feed a `FailureMemory`; the header now shows
`negative knowledge: N dead end(s) recorded` (and the top witness when it refutes more than one).
`populate_from_refutations` accepts both dict and dataclass refutation results and returns how many
NEW dead ends were learned (repeats skipped — the whole point). Pure/deterministic; not part of the
trust base (it's an efficiency-and-memory layer beside the judge).

8 tests (7 failure_memory + 1 report; discovery suite 160); full suite **1448 green**, ruff clean.
ADR-D0025. Roadmap Y0/Y1/Y2.

**Next:** interestingness scoring (Track W1 — rank findings by novelty/generality/surprise/…), or the
knowledge-graph schema (X0), or wire failure-memory `seen` into the refute loop to actually skip.

---

## 2026-07-29 — Kernel fragment widened: a second judgment (SUM identities), sequences now kernel-verified

The kernel grew from one judgment to two. `Theorem` now carries a `kind`: `Divides` (RESIDUE/CRT, as
before, with `modulus`/`poly` kept as backward-compatible accessors) and the new `SumIdentity`
(∀n≥1, Σf(i)=g(n)). New rule `SumInduction`: verify base g(1)=f(1) AND that the telescoping step
g(n)−g(n−1)−f(n) is the ZERO polynomial — sound and complete for polynomial sums. It needed RATIONAL
polynomial arithmetic (Fraction), since closed forms like n(n+1)/2 aren't integer — added exact
`_norm_q`/`_poly_sub_q`/`_poly_shift_back_q` and a `poly_from_sympy_q` bridge; the Divides fragment
stays integer (RESIDUE is only sound over ℤ).

Wired into `sequences.py`: all four polynomial sum identities (Σi=n(n+1)/2, Σi², Σi³, Σ(2i−1)=n²) are
now BOTH independently verified AND `kernel_verified` (axiom SUM_INDUCTION, with proof hash); the
non-polynomial Σ2^i stays refuted (no kernel proof). The report surfaces them the same way —
SAMPLE-REPORT.md now has 11 kernel-verified facts (7 modular + 4 sums) and SUM_INDUCTION in the axiom
manifest. The two judgments don't mix: CRT rejects a SumIdentity premise (tested).

11 tests (5 kernel + 1 sequences new; discovery suite 152); full suite **1440 green**, ruff clean.
ADR-D0024. Roadmap M1 (fragment widened).

**Next:** widen further (derive RESIDUE from ring/induction primitives — the deeper kernel), or open a
new track: AC1 (wire the full 16-step loop) or a fresh domain surface.

---

## 2026-07-29 — Proof provenance, hashing & replay (M4/M5): every theorem shows its axioms

The kernel proofs became auditable artifacts. New `provenance.py`: `axioms_used(term)` lists the
EXACT rules/primitives a theorem rests on (M5 — e.g. n⁵−n mod 30 → {CRT, RESIDUE(m=2), RESIDUE(m=3),
RESIDUE(m=5)}); `proof_hash(term)` is a deterministic, order-independent, kernel-versioned content
hash (M4 — same proof ⇒ same hash across processes, a version bump invalidates it); `replay(term)`
re-runs the kernel for byte-for-byte reproducibility.

Wired through: each `ArithmeticFinding` now carries `proof_hash` + `axioms`; the report prints
`⊢ kernel-verified [<hash>]` per fact and a kernel-axiom manifest in the header (`kernel v1.0 ·
axioms: CRT, RESIDUE(m=2), …, RESIDUE(m=8)`). Honest touch: n(n+1)(n+2)(n+3) mod 24 openly shows it
leaned on RESIDUE(m=8) (24 = 8·3) — nothing about the derivation is hidden. SAMPLE-REPORT.md
regenerated (7 hashed, axiom-listed proofs).

9 tests (7 provenance + 2 arithmetic; discovery suite 146); full suite **1434 green**, ruff clean.
ADR-D0023. Roadmap M4/M5.

**Next:** widen the kernel fragment (a rule class for the sum identities, or derive RESIDUE from more
primitive steps), or open a new track — the closed-loop connector (AC1), or the next domain surface.

---

## 2026-07-29 — Kernel wired into the arithmetic pipeline: every modular proof is `kernel_verified`

The kernel stopped being standalone. `discover_and_prove` now, for every proved modular finding,
converts the polynomial (`kernel.poly_from_sympy` — the optional sympy bridge, kept out of the
stdlib core), emits a proof TERM via `prove_divides`, and lets the LCF kernel mint the Theorem —
recording `kernel_verified` on the finding. All 7 family laws (n(n+1)…, n³−n mod 6, n⁵−n mod 30,
n⁷−n mod 42) are now BOTH `independently_verified` (checker.py, the M3 second checker) AND
`kernel_verified` (M1/M2). The report surfaces `⊢ kernel-verified` beside `✓ independently verified`;
SAMPLE-REPORT.md regenerated (7 kernel-verified facts).

Why this is stronger than the old flag: `kernel_verified` is proof-CARRYING — a false claim would
raise inside the kernel (the residue sweep fails, the guarded constructor blocks fabrication), so the
Theorem's mere existence is the evidence. Two independent confirmations now stand behind each modular
fact: the orthogonal residue re-check AND the kernel's rule-checked term.

2 net new tests (discovery suite 137); full suite **1426 green**, ruff clean. Extends ADR-D0022.

**Next:** widen the kernel fragment (e.g. derive RESIDUE from more primitive rules, or add a rule
class for the sum identities), or push into a new track — proof replay / axiom-provenance (M4/M5),
or the next domain surface.

---

## 2026-07-29 — A real PROOF KERNEL (M1/M2): theorems exist only if a proof term checks

The deepest step yet toward the "ideal engine" thesis (§1, the trustworthy kernel). New `kernel.py`
is a minimal LCF-style proof kernel: a `Theorem` can be created ONLY by the kernel's inference rules
— its constructor is guarded (`Theorem(...)` raises; only the module-private `_mint` builds one), so
every Theorem in the system is, by construction, the output of a checked rule.

Fragment (honest scope): judgments `Divides(m, p)` = "∀n∈ℤ, m | p(n)" for integer polynomials p, two
rules — RESIDUE (exhaust residues 0..m−1; a complete, sound decision procedure for the atomic
judgment) and CRT (compose pairwise-coprime moduli about the same p). A separate, UNTRUSTED prover
(`prove_divides`) factors m into prime powers, builds the term, and hands it to the kernel — the
Theorem is only as good as the kernel check.

What the tests pin down: valid proofs mint theorems (6|n³−n, 30|n⁵−n); a FALSE claim is rejected and
no theorem escapes (4∤n²+1); theorems can't be forged (`Theorem()` raises); CRT enforces its
side-conditions (rejects non-coprime moduli and mismatched polynomials); non-integer coefficients and
unknown terms are rejected; the kernel is order-independent.

TRUST BASE stated plainly in the module: sound IF the residue sweep and the CRT rule are sound (a few
auditable lines). RESIDUE is the trusted primitive — NOT yet derived from ring/induction axioms
(later M-track). Stdlib-only core, like the independent checker.

10 tests (discovery suite 135); full suite green, ruff clean. ADR-D0022. Roadmap M1/M2.

**Next:** bridge the kernel into the arithmetic pipeline — proved modular findings emit a
kernel-checked proof term and earn a new `kernel_verified` status (stronger than
`independently_verified`), with `checker.py` as the independent second checker (M3) cross-checking
the kernel.

---

## 2026-07-29 — Certificates surfaced in the report (OPEN coloring laws now show "certified")

Closed the loop from the previous increment: the report's OPEN coloring laws now carry their
constructive-certificate status. `report._frontier_laws` runs `certify_frontier_laws(...,
solver_confirm=False)` (structural fast path — keeps the report deterministic and solver-call-free)
and annotates the three certified laws (χ≤Δ+1, χ≤n, ω≤χ) with "constructively certified over the
sample (constructive_bounded)" plus a `certified=True` flag. Hamiltonicity implications (no
certificate) stay unmarked. Certified still means OPEN — never PROVED. `solver_confirm` threaded
through `certify_frontier_laws` so module tests keep the MathHead double-check while the report skips
it. 1 net new report test (discovery suite 125); full suite **1414 green**, ruff clean. Extends
ADR-D0020/D0021.

---

## 2026-07-29 — First step from "discover + refute" to "discover + PROVE" (graph domain)

The surviving coloring laws were OPEN — "the inequality held on the sample," nothing more. New
`graph_proofs.py` upgrades three of them from *observed* to *constructively certified*: the engine
now CONSTRUCTS an explicit witness realizing each bound and an independent checker re-validates it on
every graph (156 certificates up to n≤6, 0 check failures):

- `χ ≤ Δ+1` — a GREEDY (first-fit) proper coloring, re-checked proper AND ≤ Δ+1 colors (never
  exceeded Δ+1 on any graph).
- `χ ≤ n`   — the identity (all-distinct) coloring, trivially proper.
- `ω ≤ χ`   — a maximum CLIQUE, its lower bound DOUBLE-confirmed by MathHead (the clique K_ω is not
  (ω−1)-colorable → `graph_coloring` unsat). Two authorities again.

The independent checker rejects fakes (tested): a monochromatic "coloring" of K4 and a fake K4 inside
P4 both fail the re-check — M-spirit, don't trust the constructor.

HONEST STATUS — deliberately NOT overclaimed. Each certificate is `constructive_bounded`: an
explicit, re-checked witness over graphs up to the bound — strictly stronger than `bounded_check`,
but NOT a universal ∀G proof. The universal argument (greedy always fits; a clique forces its size)
is RECORDED on each certificate, but machine-verifying it needs the logic/proof-term kernel (Track
M1/M2, 🟡, unstarted). So these stay OPEN epistemically; what's new is that we now hold the
constructive certificate, not just the observation. No fake PROVED.

9 tests (discovery suite 124); full suite **1413 green**, ruff clean. ADR-D0021. Roadmap R1 (first
slice: constructive graph certificates).

**Next:** wire the certificates into the report (annotate the OPEN coloring laws "constructively
certified over the sample"), or push toward the kernel (M1) that would let a universal step be
checked — the real bridge OPEN → PROVED for graphs.

---

## 2026-07-29 — Frontier work folded into the flagship report (χ + Hamiltonicity now visible)

Two increments added frontier modules (χ, Hamiltonicity) that the run report didn't show — the
flagship artifact had drifted behind the engine's real reach. Closed that gap. `report.py` now:

- mines the frontier LAWS (coloring bounds + Hamiltonicity implications) into the honest epistemic
  buckets — survivors (ω≤χ≤Δ+1, Dirac, the necessary conditions) → OPEN (`bounded_check`), the
  killed ones (χ≤Δ, connected⟹Hamiltonian) → REFUTED with their counterexamples;
- adds a new FRONTIER section exercising the two-authority check IN the report: representative
  NP-hard invariant VALUES — χ(K4)=4, χ(K3)=3, Hamiltonicity of C5 / P4 — each independently
  confirmed by MathHead's solver (`solver_verified`), distinct from the bounded_check laws.

Kept the epistemic taxonomy pure: the frontier LAWS take their honest status (OPEN/REFUTED); only
the invariant VALUES are `solver_verified`. Honest placement of Dirac: OPEN, not PROVED — the engine
rediscovered the STATEMENT and failed to refute it on n≤5, but has NOT proven it. SAMPLE-REPORT.md
regenerated (now carries the FRONTIER section).

2 net new report tests (discovery suite 115); full suite **1404 green**, ruff clean. ADR-D0020.

**Next:** a third frontier invariant, or start proving the surviving frontier laws (lift Dirac /
the sandwich from OPEN toward PROVED with a real argument).

---

## 2026-07-29 — Second frontier invariant: Hamiltonian cycles + Dirac's theorem rediscovered

The graph→frontier bridge widened to a second NP-complete invariant. New `hamiltonicity.py`:
`is_hamiltonian(g)` (Hamiltonian cycle?) is decided locally by backtracking, then INDEPENDENTLY
CONFIRMED by MathHead's `hamiltonian_path(cycle=True)` — `sat` ⟺ Hamiltonian. All 53 graphs up to
n≤5 agree between the two engines (0 mismatches); n<3 is a convention edge case handled locally.

The engine mined the Hamiltonicity implications and REDISCOVERED **Dirac's theorem** from data
(`n≥3 ∧ δ ≥ n/2 ⟹ Hamiltonian`, survives, support 7) alongside the necessary conditions
(`Hamiltonian ⟹ connected`, `⟹ δ≥2`). It REFUTED `connected ⟹ Hamiltonian` with the minimal
STRUCTURAL witness — the 3-path P₃ (connected, no cycle). I scoped that claim to n≥3 on purpose so
the witness is structural, not the n<3 convention artifact — a deliberate honesty call (contrast the
coloring increment, where the degenerate K1 witness WAS the honest minimal one).

Bridge note: `hamiltonian_path` is 0-indexed (unlike `graph_coloring`), so no vertex shift here.

8 new tests (discovery suite 113); full suite **1402 green**, ruff clean. ADR-D0019. Roadmap O1.

**Next:** a third frontier invariant, or fold the frontier confirmations (χ, Hamiltonicity) into the
run report as first-class `solver_verified` provenance.

---

## 2026-07-29 — Graph domain reaches the SAT/UNSAT FRONTIER: chromatic number, two authorities

The graph domain crossed from exact-arithmetic invariants into the NP-hard frontier — and did it
with a double check. New `coloring.py`: χ(g) is computed exactly by backtracking (an ordinary
invariant, `chromatic_number` / `clique_number` now in the registry), then INDEPENDENTLY CONFIRMED
by MathHead's `graph_coloring` frontier tool — `sat` at χ colors AND `unsat` at χ−1 (an
impossibility proof). Our backtracking and MathHead's Z3 reduction are orthogonal authorities; both
agreeing is the "don't trust one prover" principle applied to a genuinely NP-hard invariant. Every
graph up to n≤5 has its χ confirmed this way; χ≤1 (edgeless) is trivial and skips the solver.

It also mines the classic coloring sandwich `ω ≤ χ ≤ Δ+1` (all survive the sample) and REFUTES
`χ ≤ Δ`. Honest surprise: refute-first reports the MINIMAL witness — not the textbook triangle
(χ=3 vs Δ=2) but the single vertex (χ=1 vs Δ=0), which breaks it more minimally. The engine found
a smaller counterexample than the human default; the test now records that (exact `bounded_check`,
not proven-for-all). Bridge quirk handled: `graph_coloring` is 1-indexed, so vertices shift +1 and
`n` is passed explicitly (isolated vertices counted).

9 new tests (discovery suite 105); full suite **1394 green**, ruff clean. ADR-D0018. Roadmap: O1
frontier-bridge slice + coloring invariants.

**Next:** more frontier invariants (independence number via `subset`/SAT, Hamiltonicity), or fold
`verify_chromatic_number` provenance into the report.

---

## 2026-07-29 — Independent verification extended to the sum-identity proofs

Closed the gap: now EVERY proved fact in the report is independently verified, not just the modular
ones. New `checker.check_sum_identity` re-verifies a sum identity Σf(i)=g(n) independently of the
MathHead proof — the base case plus the step g(n)−g(n−1)=f(n) as a COMPLETE polynomial-identity
check (evaluate at deg+2 points; a degree-D polynomial vanishing at D+1 points is identically zero).

`Σi = n(n+1)/2`, `Σi² = …`, `Σi³ = (n(n+1)/2)²`, `Σ(2i−1) = n²` are all now
`independently_verified=True`; the refuted `Σ2^i` is `False`. The report shows `✓ independently
verified` on every proved item across both proof families. 1 test (discovery suite 96); full suite
1385 green, ruff clean. Extends ADR-D0016/D0017.

---

## 2026-07-29 — Independent verification is now first-class: every proof is re-checked

The checker isn't optional anymore. `discover_and_prove` now runs `check_proof(proof_tree(finding),
fn)` on every proved fact and records `independently_verified` on the finding; the report surfaces
it (`✓ independently verified`).

So every proved arithmetic fact in the engine is confirmed by a checker independent of the prover —
the CRT reasoning is structurally re-checked, the claims re-verified by the complete residue method.
Trust shifted from "the strategy said so" to "an independent checker confirmed it", visible in the
report. A proof the checker couldn't confirm would ship as `independently_verified=False` (loud),
never silently. 2 tests; full suite 1384 green, ruff clean. ADR-D0017.

**Next:** extend independent verification to the sum-identity proofs, or more surface — the pipeline
absorbs it.

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
