# MathHead Discovery Engine — Architecture

> A synthesis of what the `mathhead.discovery` engine is, what it proves, and — just as
> important — what it does not. Written to be honest: every claim here is backed by code and
> tests, and the limits are stated as plainly as the capabilities.

## What this is

`mathhead.discovery` is a mathematical **discovery + verification** engine built on top of
MathHead's judge/solver spine. It generates mathematical objects, measures them, conjectures
laws, attacks those laws with counterexamples, proves the survivors where it honestly can, and
assembles one deterministic report — with every finding carrying an honest epistemic status.

It currently spans **36 modules** and **254 tests** (full repository suite green), recorded across
**40 architecture decision records** (`DECISIONS.md`) and a running progress log (`PROGRESS.md`).

The single most important fact about it is stated by its own scorecard: it correctly **rediscovers
known mathematics** across five domains, and has **established zero results novel to the
literature**. The machinery is validated; it is not (yet) a source of new mathematics. It says so,
in the report, about itself.

## The pipeline (matter → … → grade)

```
 generate  →  measure   →  mine      →  conjecture →  refute     →  prove       →  verify
 (objects)    (invariants)  (relations)  (bounds/     (counter-     (kernel /     (independent
                                          laws)         example      certificate)   checker /
                                                        first)                      adversary)
      ↓                                                                                  ↓
   explain (why, structurally / bijectively)  →  organize (knowledge graph, impact)  →  grade
                                                                                       (ladder,
                                                                                        scorecard)
                                             ↑
                                    director (goal-driven multi-cycle loop, cross-cycle memory)
```

Each stage is a module (or several). Generation is pinned to OEIS oracles; relation mining finds
linear laws by null-space; refutation is counterexample-first and reports the minimal witness;
proving routes to the kernel or to constructive certificates; verification is done a second,
independent way; explanation attaches the structural reason; organization builds a typed graph and
its impact analysis; grading places every finding on a four-rung ladder and audits novelty.

## Five object domains

The object model (`objects.MathObject`) was built to generalize, and this is demonstrated five
times over — the report, ladder, explanations, and scorecard absorbed each new domain with **zero
structural change**:

- **graphs** — non-isomorphic generation (OEIS A000088), invariants, spectral moments, the
  coloring/Hamiltonicity FRONTIER (χ and Hamiltonicity confirmed by MathHead's SAT/UNSAT tools).
- **arithmetic** — modular divisibility and power sums, proven end to end and **kernel-verified**.
- **permutations** — S_n (A000142), inv/maj/descents/cycles, MacMahon and Eulerian distributions.
- **integer partitions** — p(n) (A000041), Euler's distinct=odd (A000009), conjugation.
- **set partitions** — Bell numbers (A000110), Stirling 2nd kind (A008277), B(n)=Σ S(n,k).

Together they cover graph theory, elementary number theory, and enumerative combinatorics.

## The trust core: a proof kernel

The heart is a minimal, LCF-style **proof kernel** (`kernel.py`). A `Theorem` can only be created
by the kernel's inference rules — its constructor is guarded, so every `Theorem` value in the
system is, by construction, the output of a checked rule. Three judgments:

- **Divides(m, p)** — `∀n, m | p(n)` — via RESIDUE (exhaust residues 0..m−1; complete for the
  atomic judgment) and CRT (compose pairwise-coprime moduli).
- **SumIdentity(f, g)** — `∀n≥1, Σf(i)=g(n)` — via SumInduction (base + zero telescoping step).
- **PolyIdentity(p, q)** — `p ≡ q` — used to independently certify factorizations.

The kernel is supported by three companions: `provenance.py` (a content hash, the exact axiom
list, and deterministic replay for every proof), `checker.py` (a second, orthogonal, stdlib-only
re-verification — "don't trust the prover"), and `adversarial.py` (a 600+ false-claim battery the
kernel and checker must reject, with positive controls; result: 0 breaches). The trust base is
stated plainly in the code: residue-exhaustion is the trusted primitive, not yet derived from ring
+ induction axioms — that deeper floor is future M-track work.

## The certainty hierarchy and the epistemic ladder

Findings carry fine-grained statuses (`empirical`, `bounded_check`, `numerical_check`,
`constructive_bounded`, `structural_argument`, `constructive_bijection`, `solver_verified`,
`kernel_verified`, …). These collapse onto one honest four-rung axis (`epistemic_ladder.py`):

```
L1 DISCOVERED_HEURISTIC   mined, not yet attacked (transient; ~0 in a finished report)
L2 EMPIRICALLY_VALIDATED  holds over the sample / survived refutation, not universally proven   (37)
L3 FORMALLY_SPECIFIED     machine-checkable certificate on instances (solver values, bijections) (10)
L4 FORMALLY_PROVED        universally proven AND independently / kernel verified                  (17)
```

The mapping is conservative: nothing reaches L4 without independent or kernel verification, so the
ladder cannot launder weak evidence into strong. Refuted items are off-ladder — they are negative
knowledge (`failure_memory.py`), fingerprinted so a closed branch is never re-walked.

## Explanation: "why", not just "that"

Beyond proving *that* a fact holds, the engine attaches *why*:

- **algebraic** — n³−n = n(n−1)(n+1) (a product of three consecutive integers ⇒ divisible by 3! = 6)
  EXPLAINS 6 | n³−n; the factorization is kernel-verified (PolyIdentity).
- **structural** — the Handshake Lemma by double counting; ω ≤ χ by the clique bound; Hamiltonian ⟹
  δ≥2 by the cycle-degree argument (universal arguments, conclusion-checked on the sample).
- **bijective** — three equidistributions are proven by an *explicit, verified* bijection: Glaisher
  (Euler distinct=odd), conjugation, and Foata's Φ (Mahonian inv~maj).

## Organization and direction

`knowledge_graph.py` turns findings into a typed graph (theorem/law/conjecture/counterexample/axiom
nodes; depends_on / refuted_by / related_to edges), asserting only structurally-certain edges.
`impact.py` reads it for load-bearing axioms, hubs, and the open frontier. `director.py` runs the
whole thing as a goal-driven multi-cycle loop with cross-cycle memory — it decides *what to look at
next*, never *what is true* (that stays with the kernel and checkers).

## What is deliberately NOT done (the honest limits)

- **No novel mathematics.** Everything found is a known theorem; the scorecard reports 0 novel, and
  full novelty-vs-literature isn't even measurable without corpus ingestion (not built).
- **No universal graph/combinatorial proofs.** Structural arguments and bijections are verified on a
  bounded sample; the universal step is classical, recorded but not machine-checked.
- **The kernel's primitives are trusted, not derived.** Residue-exhaustion and the induction/identity
  rules are the base; deriving them from deeper axioms is open M-track work.
- **The interestingness score and strategy policy are transparent heuristics, not learned** — a
  learned model with human feedback is explicitly out of scope (open research).

These are not oversights; they are the boundary between what the engine has *earned* and what it has
not, kept visible on purpose. The whole project is an argument that an honest engine is more useful
than an impressive-sounding one.
