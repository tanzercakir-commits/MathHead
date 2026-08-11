# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-000 - Establish the governed reconstruction baseline

**Goal:** freeze the programme/status contracts, create the authoritative
records, preserve the audited source identity, and validate their structure.

**Scope:** repository metadata and documentation only; no product-code changes.

**Contracts:** `MH-C-STATUS-001`, `MH-C-WORKFLOW-001`.

**Validators:** `status`; project-status adoption dry-run must select the exact
case-sensitive `docs/PLAN.md`, `docs/TODO.md`, and `docs/PROGRESS.md` paths.

**Done when:** the repository-owned status layer is installed, its tests and
check pass, a second adoption dry-run proposes no changes, and the first
transactional PROGRESS record is written.

**Next handoff:** `MH-002` and `MH-003`.

### MH-001 - Adopt repository-owned project-status automation

**Goal:** install the repository-owned status CLI, tests, hook, CI workflow,
and exact-case configuration without overwriting any legacy tracker.

**Scope:** status automation and its integration files only.

**Contracts:** `MH-C-STATUS-001` is frozen and must not change.

**Validators:** `status`; the pre-adoption dry-run must be read-only and the
post-adoption dry-run must propose no changes.

**Done when:** the vendored tool, black-box tests, hook, workflow, and config
exist; all configured checks pass; legacy status files remain unchanged.

**Dependencies:** `MH-000`.

**Next handoff:** `MH-002`.

### MH-002 - Enforce task-aware status transitions

**Goal:** make PARTIAL honest under a red baseline and make DONE impossible
without task-specific green validators and accepted contract evidence.

**Scope:** status contract, vendored tool, hook, workflow, and black-box tests.

**Contracts:** `MH-C-STATUS-001` is frozen and must not change.

**Validators:** `status` plus rollback, append-only, case-sensitivity, missing
evidence, skipped validator, timeout, and red-validator negative tests.

**Done when:** every acceptance criterion in section 9 of the status contract
passes on Windows and Linux.

**Dependencies:** `MH-000`, `MH-001`.

**Next handoff:** activate the hook and require the status CI job.

### MH-005 - Index legacy status and architecture records

**Goal:** turn the root and discovery records into a searchable reconstruction
index without rewriting their historical content.

**Scope:** a new reconstruction index and its structural validator only.

**Contracts:** `MH-C-STATUS-001` and `MH-C-WORKFLOW-001`.

**Validators:** `status`; every indexed source exists, has one authority label,
and legacy files remain byte-identical.

**Done when:** obsolete, conflicting, historical, and still-valid claims are
mapped to the reconstruction phases with stable source paths.

**Dependencies:** `MH-000`.

**Next handoff:** `MH-006`.

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
