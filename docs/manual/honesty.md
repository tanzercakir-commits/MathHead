# The Honesty Contract

MathHead's product is not answers — it is *calibrated* answers. Three rules, enforced in code and CI:

1. **Every verdict carries its epistemic tier.** A kernel proof, a solver verdict, and an empirical
   observation are different kinds of knowledge; they are never conflated.
2. **Witnesses are self-verifying.** A refutation ships the object and the exact arithmetic that
   convicts it; SAT witnesses are re-checked by brute force with no solver in the loop; spectral
   certificates use pure integer arithmetic (Sylvester/Bareiss + integer square tests).
3. **The engine refuses to guess.** Unsupported input → `unsupported` with suggested instruments.
   An exhausted hunt → `not_found_within_budget`. A bound is always stated (`checked up to n=…`).

The tiers, strongest first:

| tier | meaning |
|---|---|
| `kernel_verified` | universal machine proof in the LCF-style kernel, with a proof hash |
| `formal_proof` | discovery-report certainty of a judge-proved induction (modular or sum); a kernel-verified sum identity carries this label — the kernel's SumInduction term re-derives the step with its own PolyIdentity rule, so the finding is not left at the step-checker's weaker `solver_verified` |
| `exact_integer_certificate` | self-verifying witness, pure integer arithmetic |
| `finite_domain_exhaustion` | a FIXED-order claim decided by complete enumeration of its finite domain (one representative per isomorphism class; the invariants are isomorphism-invariant) — an exhaustion proof, not a witness; unbounded universal claims can never carry this tier |
| `independently_verified_witness` | solver output re-verified by brute force |
| `independently_verified_unsat_proof` | the solver's DRUP refutation re-checked by a pure-Python RUP checker — no solver in the loop |
| `independently_verified_unsat_proof_of_strengthened_formula` | RUP-checked refutation of the base formula PLUS derived lemmas — the proof is of the strengthened formula, not the bare encoding; the lemma list rides the verdict |
| `solver_verified_with_derived_lemmas` | solver verdict; every added lemma listed on the verdict |
| `solver_verified` | plain solver verdict — the fallback when a DRUP proof cannot be obtained or checked within budget, and the tier of a proof chain whose weakest link is a solver (e.g. a comparative sum bound: kernel-verified closed form, then the z3 NRA inequality step — the verdict names the chain) |
| `constructive_bounded` | explicit checked witness over a stated sample — not a universal proof |
| `interval_certified` | certified enclosure (directed rounding); refuses strictness at equality |
| `numerical_conjecture` | two-precision PSLQ evidence — never presented as proof |
| `no_counterexample_within_bound` | survived exhaustive attack to the stated bound — honestly open |
| `empirical` | held on the sample; a conjecture, nothing more |

A fourth rule follows from the first three: **ambiguity is surfaced, not resolved silently.**
A graph-bound text like `num_vertices <= num_edges + 1` does not say *which* quantifier domain it
means, so every graph-bound verdict also carries `readings` — the three candidate readings
(A connected graphs, `check()`'s own baseline / B all graphs including disconnected / C one fixed
order, a complete finite domain), each with its own verdict at its own tier from the table above
(no new tiers were invented for this). When the verdict changes with the reading, the note says
so in as many words: the answer depends on which question the statement is asking.

One consequence worth stating plainly: in a full self-audit the engine attributed **all** of its
findings to known mathematics — `0 novel-to-literature established` — and says so in its own
scorecard. A tool that would fake that number would fake anything.
