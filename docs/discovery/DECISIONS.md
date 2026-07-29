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

<!-- New decision template:
## ADR-D#### — title
- **Status:** Proposed | Accepted | Superseded (ADR-D####) · YYYY-MM-DD
- **Context:** …
- **Decision:** …
- **Consequences:** …
-->
