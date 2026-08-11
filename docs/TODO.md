# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-016 - Make the full supported CI matrix green

**Goal:** make every required ENV-002 CI job pass on its declared operating
systems and Python versions without deleting coverage or weakening rejection.

**Scope:** normalize Python-version-dependent `ast.parse` failures at one
content-addressed expression-parser boundary, route all user expression parsers
through it, preserve caller-specific error envelopes, and repair any remaining
supported-matrix failures exposed by the full workflow.

**Contracts:** `MH-C-AST-PARSE-001`, `MH-C-ENV-002`, `MH-C-WORKFLOW-001`.

**Validators:** accepted contract hash/signature, deterministic malformed-input
and NUL rejection, direct and routed Hypothesis properties, core/discovery/docs/
solver/live/slow/release profiles, required coverage at 85 percent or higher,
all supported OS/Python jobs, Ruff, and project status.

**Done when:** all required jobs in a clean GitHub Actions run conclude success;
no supported Python leaks `SyntaxError`, `ValueError`, or `TypeError` from the
shared expression boundary; no test, matrix cell, or coverage gate is removed.

**Dependencies:** `MH-015` (done); parser normalization contract accepted under
the project owner's programme-wide acceptance authority.

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
