# MH-ADR-0004: Compatibility and deprecation policy

**Status:** Accepted  
**Accepted:** 2026-08-11  
**Decision topic:** compatibility-policy

## Context

The legacy project describes its MCP surface as stable while many Python
modules are internal. Reconstruction will introduce typed v2 contracts and
multiple adapters. Compatibility must protect users without freezing known
incorrect trust claims or accidental implementation details.

## Decision

Compatibility attaches to named, versioned contracts—not file paths or backend
output formatting.

- The primary v2 compatibility surface is the typed Python contract and result
  model. CLI, MCP, and HTTP are serialization adapters over the same semantics.
- The accepted legacy MCP v1 signatures and response envelope remain supported
  through an explicit compatibility adapter until equivalent reference
  fixtures, a migration guide, and a declared removal release exist.
- Direct imports from legacy `core`, `compute`, `router`, `server`, and
  `discovery` modules are internal and receive no new SemVer guarantee.
- Additive schema evolution requires a declared minor contract revision.
  Removed fields, changed meanings, stricter accepted input, or weaker evidence
  require a major contract revision or a separately versioned adapter.
- Deprecation must be machine-visible and documented for at least one released
  minor line before removal. Removal cannot be based only on elapsed time.
- Error codes, verdict semantics, canonicalization, and evidence formats are
  versioned. Unknown trusted-schema fields fail closed; interface adapters may
  negotiate an explicitly supported version.
- A false or overstated trust claim is corrected immediately with a migration
  note and explicit reason. Compatibility never requires reporting sampled,
  bounded, solver-produced, or unchecked output as proved.

Backend versions, witnesses, explanations, timing, and incidental ordering are
not byte-compatible promises unless a contract explicitly makes them part of a
canonical replay artifact. Logical verdict stability and replay identity are
separate from witness presentation.

## Consequences

Users get an explicit migration path and stable semantic targets. Internal
architecture can change without pretending every Python function is public.
Adapters cannot invent semantics absent from the engine.

## Rejected alternatives

- Preserving every import and output byte, because it freezes accidental
  internals and backend rendering.
- Breaking v1 at the first v2 commit, because fixtures and migration evidence
  must exist first.
- Hiding corrected trust claims behind a legacy mode, because that would keep
  an unsafe interpretation alive.
