# MH-ADR-0005: Trust-base and evidence language

**Status:** Accepted  
**Accepted:** 2026-08-11  
**Decision topic:** trust-terminology

## Context

Legacy documents use proof, verification, checking, solver confirmation,
certificate, witness, and kernel language at different strengths. The
reconstructed engine needs consistent terms before freezing result schemas.

## Decision

The following terms constrain every later contract and interface:

- A **producer** searches, solves, simplifies, enumerates, or proposes an
  artifact. Producers are untrusted for the truth of their own claim.
- A **witness** is concrete data for a claim or counterclaim. It becomes
  evidence only after the named validation procedure accepts it.
- A **certificate** is a versioned, canonical artifact intended for replay by a
  named checker. Possessing a certificate is not the same as checking it.
- A **checker** is the implementation that validates one owned certificate
  format. Its code and declared primitives are inside that claim's trust base.
- The **kernel** is the smallest constructor-controlled collection of checkers
  allowed to mint kernel-accepted theorem objects. “Kernel” is not a synonym
  for all solver or core code.
- The **trust base** is the complete set of code, runtimes, arithmetic and
  serialization primitives, external tools, assumptions, and environment facts
  that must behave correctly for a particular claim. It is recorded per result,
  not implied by a package name.
- **Replay** means re-running the declared checker against canonical input,
  context, budget identity, and artifact versions. Matching a cached verdict
  without those identities is not replay.
- **Independent** means the checker does not reuse the producer's decisive
  algorithm or unvalidated conclusion. A second call to the same backend is a
  cross-check, not independent verification.

Epistemic language is monotone and evidence-bound:

- **sampled/numerical evidence** supports only observations over stated points
  and tolerances;
- **bounded evidence** supports only the enumerated or searched domain and
  budget;
- **solver-confirmed** means the named backend returned a result under recorded
  assumptions and limits, without an independently replayed certificate;
- **checker-verified** means a named certificate checker accepted the artifact;
- **kernel-accepted** means the dependency-minimal kernel minted the theorem;
- **externally checked** means a separately versioned external proof environment
  compiled or replayed the exported artifact.

These labels do not automatically collapse into a universal `proved` verdict.
Later EngineResult contracts will define exact tiers and mappings, but may not
promote a result above the strongest completed evidence transition.

The planner, routing policy, discovery heuristics, novelty catalog, ranking,
cache, producer explanations, and prose renderer are outside the truth trust
base. They may influence attention or presentation, never mint a stronger
claim.

## Consequences

Every supported claim can name what was trusted, what was checked, what was
bounded, and what remains open. “Unknown,” “unsupported,” disagreement, timeout,
and invalid evidence remain valid outcomes rather than being coerced into a
guess.

## Rejected alternatives

- A single confidence score, because probability and proof strength are not one
  ordered quantity.
- Calling all Z3 or SymPy results verified, because a producer cannot certify
  itself merely by returning successfully.
- Treating human-readable explanations as proof artifacts, because prose is not
  canonical replay evidence.
