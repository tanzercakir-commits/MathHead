# Discovery Engine — Progress log

> WHAT we did, WHEN, WHY — append-only, newest on top. The subproject that follows
> `docs/IDEAL-ENGINE-ROADMAP.md`. Rationale of design choices goes to
> `docs/discovery/DECISIONS.md`.

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
