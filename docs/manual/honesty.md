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
| `exact_integer_certificate` | self-verifying witness, pure integer arithmetic |
| `independently_verified_witness` | solver output re-verified by brute force |
| `solver_verified_with_derived_lemmas` | solver verdict; every added lemma listed on the verdict |
| `solver_verified` | plain solver verdict (DRAT logging is the recorded next step) |
| `constructive_bounded` | explicit checked witness over a stated sample — not a universal proof |
| `interval_certified` | certified enclosure (directed rounding); refuses strictness at equality |
| `numerical_conjecture` | two-precision PSLQ evidence — never presented as proof |
| `no_counterexample_within_bound` | survived exhaustive attack to the stated bound — honestly open |
| `empirical` | held on the sample; a conjecture, nothing more |

One consequence worth stating plainly: in a full self-audit the engine attributed **all** of its
findings to known mathematics — `0 novel-to-literature established` — and says so in its own
scorecard. A tool that would fake that number would fake anything.
