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

<!-- New decision template:
## ADR-D#### — title
- **Status:** Proposed | Accepted | Superseded (ADR-D####) · YYYY-MM-DD
- **Context:** …
- **Decision:** …
- **Consequences:** …
-->
