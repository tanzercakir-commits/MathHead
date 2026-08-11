# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

## Next

### MH-004 - Capture the immutable legacy baseline

Create the machine-readable source/test/CI/benchmark/performance baseline used
for differential migration. Dependencies: `MH-003`.

### MH-006 - Freeze reconstruction ADRs

Record preserve/rebuild boundaries, package ownership, migration strategy,
compatibility policy, and trust-base terminology in new append-only ADRs.
Dependencies: `MH-005`.

### MH-010 - Correct optional dependency test contracts

Make core and optional solver profiles self-consistent without deleting
coverage. Dependencies: `MH-003`, `MH-004`.

### MH-011 - Bound finite graph enumeration defaults

Add explicit budget semantics and safe fallback limits. Dependencies: `MH-003`,
`MH-004`.

### MH-012 - Make all command surfaces encoding-safe

Cover Windows locale, redirected output, JSON, and human-readable output.
Dependencies: `MH-003`, `MH-004`.

## Later

- `MH-013` through `MH-017`: finish the portable green legacy baseline.
- `MH-020` through `MH-028`: contract-first Python foundation.
- `MH-030` through `MH-037`: trusted kernel and evidence model.
- `MH-040` through `MH-056`: problem analysis, planner, and budgets.
- `MH-060` through `MH-067`: verified theory-plugin vertical slices.
- `MH-070` through `MH-086`: mathematician workspace and discovery lab.
- `MH-090` through `MH-107`: stable interfaces and hardening.
- `MH-110` through `MH-123`: validation, release, and sustainable extension.

## Blocked

### MH-003 - Define one reproducible developer environment

**External dependency:** explicit project-owner acceptance of proposed contract
`MH-C-ENV-001` at SHA-256
`63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87`.

**Resume condition:** move the unchanged accepted artifact into the accepted
contract set, update its manifest state, and return this task to `Now`.
