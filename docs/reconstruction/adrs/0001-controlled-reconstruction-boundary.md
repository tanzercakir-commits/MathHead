# MH-ADR-0001: Controlled reconstruction boundary

**Status:** Accepted  
**Accepted:** 2026-08-11  
**Decision topic:** preserve-rebuild-boundary

## Context

MathHead contains verified mathematical routines, certificates, adversarial
tests, benchmark evidence, user-facing contracts, orchestration code, and a
large exploratory discovery subproject. Treating all of it as equally trusted
would preserve known architectural faults; replacing all of it would discard
the strongest evidence and repeat solved mathematical work.

## Decision

The programme is a controlled reconstruction, not a blank rewrite and not an
in-place cosmetic refactor. Every legacy asset is classified before migration:

- **Preserve as an oracle:** mathematically valuable algorithms, independent
  checkers, exact witnesses, certificate corpora, negative/adversarial tests,
  error and epistemic taxonomies, and benchmark fixtures whose claims can be
  replayed. Preserved code is not automatically trusted; its behavior is an
  input to differential tests.
- **Rebuild behind accepted contracts:** environment selection, cross-layer
  data models, parsing boundaries, routing/planning, budgets and isolation,
  result/evidence envelopes, caching identities, public adapters, and any
  component whose present API mixes production with verification.
- **Quarantine in the laboratory:** conjecture generation, novelty and
  interestingness scoring, heuristic strategy selection, unbounded search,
  literature-association heuristics, and experimental reports. Laboratory
  output cannot serialize as a supported proof claim.
- **Retire only with evidence:** dead or contradictory paths are removed only
  after their authority is indexed and overlapping behavior has a passing
  replacement fixture or an explicit incompatibility decision.

The stable engine and the discovery laboratory are separate authority zones.
Discovery may submit candidates and artifacts to the engine; it may not mint
engine verdicts or become a dependency of the trusted kernel.

## Consequences

Legacy files can remain while new vertical slices are built. File count or
module movement is not progress by itself. A preserved algorithm crosses into
the supported engine only through an accepted contract, bounded producer,
independent checker where claimed, and adversarial tests.

A stronger but historically inaccurate trust claim is never kept merely for
backward compatibility.

## Rejected alternatives

- A full rewrite, because it discards executable mathematical evidence.
- Keeping the current architecture and renaming layers, because ownership and
  trust boundaries would remain ambiguous.
- Treating all discovery results as engine capabilities, because exploration
  and proof authority have different failure modes.
