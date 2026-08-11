# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-010 - Correct optional dependency test contracts

Make core and optional solver profiles self-consistent without deleting
coverage. Dependencies: `MH-003`, `MH-004`.

### MH-011 - Bound finite graph enumeration defaults

Add explicit budget semantics and safe fallback limits. Dependencies: `MH-003`,
`MH-004`.

### MH-012 - Make all command surfaces encoding-safe

Cover Windows locale, redirected output, JSON, and human-readable output.
Dependencies: `MH-003`, `MH-004`.

## Next

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
