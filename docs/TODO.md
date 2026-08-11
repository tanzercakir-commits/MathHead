# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-003 - Define one reproducible developer environment

**Goal:** implement the accepted portable environment contract through one
repository-owned dispatcher used by developers and CI.

**Scope:** accepted-contract binding, pinned profile dependencies, Windows and
Linux policy, UTF-8 subprocess behavior, bounded execution, clean-install
smokes, tests, and setup documentation; no product algorithm changes.

**Contracts:** `MH-C-ENV-001`, `MH-C-WORKFLOW-001`.

**Validators:** `fast`; the accepted hash, callable signature, profile manifest,
negative process outcomes, status/core checks, and runtime/release clean smokes
must pass.

**Done when:** local validators and remote Ubuntu/Windows environment checks are
green without weakening any product or governance gate.

**Dependencies:** explicit owner acceptance received; `MH-002`, `MH-006`.

**Next handoff:** `MH-004`.

## Next

### MH-004 - Capture the immutable legacy baseline

Create the machine-readable source/test/CI/benchmark/performance baseline used
for differential migration. Dependencies: `MH-003`.

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
