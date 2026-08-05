# MathHead

**Bring your conjecture — MathHead refutes it (with a witness), proves it (with a kernel proof), or
tells you exactly how far it survived.**

A deterministic mathematics engine whose product is *trustworthy verdicts*: every answer carries an
**epistemic tier**, every witness is **self-verifying**, and anything the engine cannot decide is
reported as exactly that — never dressed up.

What it does today (each claim locked by CI tests):

- **Proves** modular facts and sum identities in an LCF-style proof kernel — forge-guarded, its trust
  base fully *derived* (residue exhaustion, CRT, and induction are theorems in it, not axioms).
- **Refutes** graph conjectures counterexample-first over *all* connected graphs (nauty-scale), with
  exact invariants including independence, domination, matching, girth, diameter, radius.
- **Certifies** spectral counterexamples in pure integer arithmetic — no floats in any verdict.
- **Brackets Ramsey numbers**: R(3,3)=6 · R(3,4)=9 · R(3,5)=14 · R(4,4)=18, SAT witnesses re-verified
  independently, derived lemmas listed on every strengthened UNSAT.
- **Hunts live** on open problems (Frankl union-closed) and says `not_found_within_budget` when that
  is the truth.
- **Exports to Lean 4** for external cross-sealing of its kernel theorems.

Start with the [Quickstart](quickstart.md); read the [Honesty Contract](honesty.md) — it is the
product's soul.
