# MathHead — Development Notes

This file is not a work log (→ `Progress.md`), a to-do list (→ `Todo.md`), or a
decision record (→ `DECISIONS.md`). It is the idea/observation notebook that feeds
the project's **direction** — unhurried notes meant to mature.

---

## 2026-07-28 — What does "learn math/physics, not coding" mean? (direction note)

The "math" that tech leaders (e.g. Jensen Huang) mean is not mechanical
**computation** (AI already does that). Three layers:

1. **The math that runs AI:** linear algebra (tensors/matrices), probability &
   statistics (uncertainty/inference), multivariable calculus & optimization
   (gradient/training), information theory (entropy).
2. **The math of rigorous thinking — the lasting human edge:** mathematical logic
   & proof, discrete math / combinatorics / graphs, abstraction & algebraic
   structure.
3. **The deepest reading, a way of thinking:** modeling reality from first
   principles (physics), turning a messy problem into **a precise mathematical
   statement**, and the rigor of not "computing" but "**why is it true**"
   (proof / verification).

**What it means for MathHead (critical):** MathHead lives precisely in layers 2
and 3 — not *computation* but **verifiable reasoning + modeling**. Once AI writes
the code, the bottleneck shifts upward: from "how do I write it" → to "what
exactly is the problem, is my inference correct, how do I verify the answer".
MathHead's thesis (giving AI a deterministic, robust, **proof-producing** engine)
sits right in the middle of that shift.

**Direction confirmation:** `prove` (step-by-step proof), FOL
(predicate/quantifier), `enumerate`, Track B reductions (problem → precise
statement) — leaning on the *logic / proof / modeling* axis rather than
computation is the right bet. So the direction so far is consistent with this
thesis; it makes sense to keep the weight here going forward.

**Honest balance:** "never learn to code at all" is an exaggeration; what actually
gets devalued is coding as *syntax labor*. Understanding systems + steering AI and
**verifying** it is still very valuable — which, again, means rigor / math.
