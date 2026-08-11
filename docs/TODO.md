# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-014 - Split test profiles

**Goal:** replace the monolithic test command with explicit, bounded ownership
for every supported product and governance gate.

**Scope:** status/runtime helpers plus core, solver, discovery, docs, live-mcp,
slow, and release profiles; dependencies, markers, platform/Python support,
timeouts, coverage preservation, CI routing, and full-history baseline replay.

**Contracts:** `MH-C-ENV-002`, `MH-C-WORKFLOW-001`.

**Validators:** profile schema and ownership, dependency isolation, negative
marker selection, per-profile budgets, unchanged coverage floor, full-history
baseline replay, CI dispatcher ownership, and supported-platform checks.

**Done when:** every test belongs to an explicit profile, fast jobs no longer
run an auxiliary monolithic full suite, solver/live/slow work is isolated, and
coverage remains a required bounded CI gate at 85 percent or higher.

**Dependencies:** `MH-003` (done), `MH-010` through `MH-013` (done); environment
v2 accepted under the project owner's programme-wide acceptance authority.

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
