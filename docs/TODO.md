# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-015 - Remove version and documentation drift

**Goal:** replace hand-maintained package, test, tool, profile, and executable
example claims with a single generated and fail-closed project-facts boundary.

**Scope:** single-source package SemVer, dynamic build metadata, canonical live
project facts, generator-owned README claims, strict example manifest and source
directives, declared profile ownership, and exact pytest validator node IDs.

**Contracts:** `MH-C-PROJECT-FACTS-001`, `MH-C-WORKFLOW-001`.

**Validators:** accepted contract hash/signature, package/wheel/CLI/changelog
version agreement, live pytest and MCP enumeration, canonical facts and README
regeneration, example schema/coverage/selection, docs profile, release smoke,
Ruff, and project status.

**Done when:** one editable version literal drives source and package metadata;
test/tool/profile claims regenerate from live sources; every published
executable result example has one profile and a passing exact validator; all
other command snippets are explicitly classified with a reason.

**Dependencies:** `MH-014` (done); project-facts contract accepted under the
project owner's programme-wide acceptance authority.

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
