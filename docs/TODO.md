# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-010 - Correct optional dependency test contracts

**Goal:** make core and optional solver profiles self-consistent without
deleting coverage or importing undeclared backends.

**Scope:** extras ownership, capability-marked tests, Python-SAT import fences,
nauty executable alternatives, and solver preflight.

**Contracts:** `MH-C-ENV-001`, `MH-C-WORKFLOW-001`.

**Validators:** optional dependency contract, devtool tests, core profile, and
the Ubuntu solver bootstrap/preflight must pass.

**Done when:** `[dev]` remains Python-SAT-free, solver-only tests are selectable,
and both supported nauty executable names resolve without a silent skip.

**Dependencies:** `MH-003` (done), `MH-004` (done).

### MH-011 - Bound finite graph enumeration defaults

**Goal:** replace unsafe finite-graph defaults with explicit bounded behavior.

**Scope:** pure-Python limits, fast-backend selection, resource budgets,
truncation/refusal semantics, and product/CLI regression tests.

**Contracts:** `MH-C-WORKFLOW-001`; a task-specific critical contract is
required before implementation.

**Validators:** graph budget unit, timeout, negative, CLI, and legacy
differential checks plus the relevant product profile.

**Done when:** the default path cannot enumerate an unsafe search silently and
larger requests require a declared fast capability or return an honest result.

**Dependencies:** `MH-003` (done), `MH-004` (done).

### MH-012 - Make all command surfaces encoding-safe

**Goal:** make every command surface safe under Windows locale and redirected
output while preserving Unicode when supported.

**Scope:** CLI, discovery CLI, MCP/subprocess diagnostics, JSON and human
renderers, non-UTF-8 consoles, and redirected streams.

**Contracts:** `MH-C-WORKFLOW-001`; a task-specific critical contract is
required before implementation.

**Validators:** non-UTF-8 locale, redirected console, JSON, human output,
Windows, and negative encoding tests.

**Done when:** supported commands never crash on encodable/unsupported glyphs,
machine JSON stays canonical, and lossy fallback is explicit and deterministic.

**Dependencies:** `MH-003` (done), `MH-004` (done).

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
