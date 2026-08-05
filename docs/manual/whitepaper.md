# Whitepaper (draft)

**MathHead: calibrated verdicts for finite mathematics.**

**Abstract.** We describe a mathematics engine whose organizing principle is *epistemic honesty*:
every verdict carries a tier stating exactly what kind of knowledge it is, witnesses are
self-verifying, and the engine's self-audit (all findings attributed to known mathematics; 0
novel-to-literature established) is published in its own scorecard.

**1 · The kernel.** An LCF-style proof kernel (forge-guarded `Theorem` type) with three judgments:
modular divisibility, sum identities, polynomial identities. Its trust base is *derived*, not
assumed: residue exhaustion follows from the factor theorem, CRT from Bézout, the induction step of
SumInduction from the kernel's own polynomial-identity rule, and the elementary divisibility lemmas
carry constructive witnesses. Proof artifacts are hashed and replayable; an independent checker
re-verifies without the kernel.

**2 · The instruments.** Counterexample-first refutation over all connected graphs (nauty-scale,
class-by-class cross-validated); exact rich invariants (α, γ, ν, girth, diameter, radius; Petersen-
and König-anchored); pure-integer spectral certificates (Sylvester positive-definiteness by
fraction-free Bareiss + integer square comparisons) with an independent interval-arithmetic route
that agrees 7/7 and answers *undecided* at equality; SAT Ramsey bracketing with brute-force-reverified
witnesses and derived degree lemmas listed on every strengthened verdict; seeded adversarial hunts
(simulated annealing over graphs, trees, and set families); PSLQ constant relations under a
two-precision protocol; a FunSearch-style program-evolution loop whose winning closed forms are
independently proved by the kernel; Lean 4 export (decide-over-ZMod ≡ residue exhaustion).

**3 · Results (all reproducible by CI).** R(3,3)=6, R(3,4)=9, R(3,5)=14, R(4,4)=18 engine-bracketed —
the R(3,5)/R(4,4) UNSAT sides use degree lemmas justified by the engine's own R(3,4) bracket; the
transcribed Aouchiche–Hansen statement refuted by integer-certified witnesses from n=18 (the Wagner
shape at n=19 rediscovered); the Frankl equality wall measured (best slack +1 across universes 6–11);
9 counting sequences land exactly on their OEIS pins.

**4 · Limitations, stated plainly.** Everything above is rediscovery or rediscovery-grade; novelty
against the literature is not claimed and cannot be claimed without corpus ingestion and human
review. Plain `solver_verified` UNSATs are not kernel-grade (DRAT logging is the recorded next
step). The Lean export awaits an external `lake build`.

*Draft status: to be expanded into a preprint; see CITATION.cff for how to cite the software.*
