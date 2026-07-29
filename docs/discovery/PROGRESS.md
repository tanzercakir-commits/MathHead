# Discovery Engine — Progress log

> WHAT we did, WHEN, WHY — append-only, newest on top. The subproject that follows
> `docs/IDEAL-ENGINE-ROADMAP.md`. Rationale of design choices goes to
> `docs/discovery/DECISIONS.md`.

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
