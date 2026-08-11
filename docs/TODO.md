# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-011 - Bound finite graph enumeration defaults

**Goal:** replace unsafe finite-graph defaults with explicit bounded behavior.

**Scope:** pure-Python limits, fast-backend selection, resource budgets,
truncation/refusal semantics, and product/CLI regression tests.

**Contracts:** `MH-C-GRAPH-BUDGET-001`, `MH-C-WORKFLOW-001`.

**Validators:** graph budget unit, timeout, negative, CLI, and legacy
differential checks plus the relevant product profile.

**Done when:** the default path cannot enumerate an unsafe search silently and
larger requests require a declared fast capability or return an honest result.

**Dependencies:** `MH-003` (done), `MH-004` (done); graph-budget contract
accepted under the project owner's programme-wide acceptance authority.

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
