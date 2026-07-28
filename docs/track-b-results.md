# Track B — Honest Results Log

This file records the results that MathHead's `frontier/` layer **actually
establishes / proves** via SAT reduction. The goal is honesty: cleanly separating
**reproduced known values** (verification) from those that are **open /
unreachable**. No fake victories.

> **Method:** reduce the problem to 2-color (or r-color) *satisfiability*, solve
> with Z3. This is **the same** method that computes the relevant research values
> — the only difference is scale.

## Pigeonhole

`n+1` pigeons, `n` boxes → **unsat** (proof of the theorem), for every `n`. ✓
An example of proving a classic theorem by reduction.

## Boolean Pythagorean triples

2-coloring of `{1..n}` with no monochromatic Pythagorean triple (a²+b²=c²).

- Small `n`: `sat` (a coloring is found and **independently verified**). ✓
- Known result from the open problem: impossible at `n=7825` (Heule et al., 2016,
  ~200 TB proof) — this scale is **far** beyond this environment.

## van der Waerden numbers W(2, k)  ·  *computed in this session*

Can we color `{1..n}` with 2 colors and no monochromatic `k`-term arithmetic
progression? `W(2,k)` = the smallest `n` at which coloring becomes impossible.

| Number | Known value | Engine's result | Time |
|---|---|---|---|
| W(2,3) | 9 | n=8 `sat`, **n=9 `unsat`** ✓ | ~6 ms |
| W(2,4) | 35 | n=34 `sat`, **n=35 `unsat`** ✓ | ~40 ms |
| W(2,5) | 178 | n=177 `sat`, **n=178 `unsat`** ✓ | ~61 s |

Each `unsat` is **a real impossibility proof**: the set `{1..W}` cannot be
2-colored without a monochromatic `k`-term arithmetic progression. These values
match the research results in the literature exactly — i.e. the engine
**reproduced them with the same method** (W(2,5)=178 was first determined in 1978).

## Schur numbers S(r)  ·  *computed in this session*

Can `{1..n}` be partitioned into `r` colors with no `x + y = z` in any color class
(each class **sum-free**)? `S(r)` = the largest `n` that can be partitioned.

| Number | Known value | Engine's result | Time |
|---|---|---|---|
| S(2) | 4 | n=4 `sat`, **n=5 `unsat`** ✓ | ~5 ms |
| S(3) | 13 | n=13 `sat`, **n=14 `unsat`** ✓ | ~0.3 s |
| S(4) | 44 | n=44 **`sat`** → S(4) ≥ 44 verified | ~25 s |

S(2) and S(3) were **fully** reproduced (both directions = an exact proof of the
value). For S(4) the lower bound (S(4) ≥ 44) is verified; the upper bound
(n=45 `unsat`) did not finish in ~1.5 min in this environment → wall. **S(5)=160**
is known but enormous (Heule 2017, ~2 PB proof). **S(6) is still OPEN.**

## Optimization attempt: symmetry breaking

To push the wall further, constraints that break color-permutation symmetry were
tried (2-color: first element fixed; r-color: lex-leader). `sat`/`unsat` **does
not change** (correctness is preserved — locked by tests). But the effect turned
out **mixed**:

| Case | Without symmetry | With symmetry | Result |
|---|---|---|---|
| S(3) n=14 (unsat) | ~0.23 s | ~0.0 s | sped up |
| W(2,5) n=178 (unsat, 2-color) | ~61 s | ~65 s | unchanged (factor 2) |
| S(4) n=44 (sat, 4-color) | ~35 s | ~48 s | **slowed down** (overhead) |

**Honest conclusion:** Naive color-symmetry breaking is no magic wand — it helps
on small/UNSAT cases, but on SAT cases the added constraints impose overhead and
can hurt. So the default is **off** (it remains as an optional `symmetry_break`
flag, its correctness guaranteed by tests). Crossing the real wall (S(4)=45,
W(2,6)) requires research-grade SAT techniques (streamlining, specialized solvers,
parallelism) — that is a matter of *scale/engineering*, not of the *method*.

## Honest limit (compute wall)

- The practical limit in this environment is **~W(2,5)** (n≈178, ~1 min).
- **W(2,6) = 1132**: *known* but enormous (required specialized SAT solvers /
  clusters) — unreachable in this container.
- **W(2,7)**: its exact value is **OPEN** (known lower bound ≥ 3703). The engine's
  method is correct but this scale is unreachable → honestly `unknown`.

## Conclusion

MathHead did **not solve** an open problem — the ones that are solved required
supercomputation. But it **reproduced, verifiably,** research-grade values
(W(2,3..5) and Schur S(2..3), S(4)≥44) with the same method, and transparently
showed exactly where the wall begins.
This is Track B's thesis: *the method is real; as scale grows, the compute limit
kicks in.* Scaling up (a stronger solver, parallelism, a cluster) is engineering
work — the method does not change.

## Phase 10 — new reductions + verifiable certificate

**New reductions (NP-complete):**

- `graph_coloring(edges, colors)` — graph k-coloring. K3 → 3 colors sat, 2 colors
  unsat (odd cycle); K4 → 3 colors unsat (chromatic number 4). Independently
  verified.
- `subset_sum(numbers, target)` — subset sum. `[3,34,4,12,5,2]→9` sat (`{3,4,2}`);
  `→100` unsat.

**Verifiable certificate (honest status):**

- **Positive (`sat`):** the witness is a certificate and is re-checked
  INDEPENDENTLY of Z3, in pure Python → `meta.verified=true`. This makes the
  positive evidence verifiable independently of the solver and in polynomial time
  (it catches encoding/translation errors).
- **Negative (`unsat`) — WALL:** an independently-checkable **DRAT/LRAT**
  certificate requires a DIMACS-level CDCL SAT solver + a `drat-trim`-style checker
  pipeline. Z3's internal proof object is in its own format (not DRAT). Building
  this is out of scope for this round; we **honestly** return the `unsat` result
  and note that a DRAT certificate is not yet produced. Future work.
