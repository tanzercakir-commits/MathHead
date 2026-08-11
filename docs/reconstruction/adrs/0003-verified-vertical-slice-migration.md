# MH-ADR-0003: Verified vertical-slice migration

**Status:** Accepted  
**Accepted:** 2026-08-11  
**Decision topic:** migration-strategy

## Context

The product cannot pause for a big-bang architectural replacement, and module
parity would not prove semantic or trust parity. Migration must preserve an
honest product baseline while allowing individual capabilities to cross the new
boundaries independently.

## Decision

Migration uses a strangler pattern built from verified mathematical vertical
slices. Each promoted slice contains, in one reviewable path:

1. accepted input, context, budget, result, evidence, and plugin contracts;
2. canonical fixtures for proof, refutation, ambiguity, unsupported input,
   timeout, invalid evidence, and backend disagreement;
3. a bounded producer and explicit capability declaration;
4. an independent checker whenever the result tier claims independent or
   kernel verification;
5. evidence-grounded explanation, diagnostics, replay identity, and resource
   accounting;
6. differential tests against every overlapping legacy behavior plus negative,
   property, mutation, and platform tests;
7. one public adapter path with no unique mathematical logic.

The legacy path remains available through a transitional adapter until the
slice passes its required gate. Routing between legacy and reconstructed paths
is explicit, deterministic, observable, and reversible at the slice boundary.
No fallback may silently upgrade an unknown, bounded, or unsupported result.

A slice is removed from the legacy path only after evidence shows either
contract overlap with passing differential behavior or an accepted intentional
incompatibility. Commits are kept small enough that a failing slice can be
reverted without disturbing already promoted capabilities.

## Consequences

Progress is measured by end-to-end trusted behavior rather than directories or
rewritten line count. Initial work favors arithmetic/divisibility assets because
they already have replayable evidence, then deliberately adds diverse domains
to test that the architecture is not tailored to one theory.

## Rejected alternatives

- Layer-by-layer replacement, because no user-visible path becomes verifiable
  until the last layer lands.
- Automatic fallback to legacy on every new-engine failure, because it hides
  regressions and changes epistemic meaning.
- Deleting legacy tests after equivalent happy paths pass, because adversarial
  and platform evidence is part of the asset being preserved.
