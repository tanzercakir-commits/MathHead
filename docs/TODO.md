# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-017 - Freeze the legacy compatibility corpus

**Goal:** preserve representative legacy result semantics as deterministic,
machine-checkable fixtures before the architecture is replaced.

**Scope:** inventory public result envelopes and choose successful, refuted,
unsupported, timeout, and error cases; capture canonical outputs from the
legacy implementation; normalize only explicitly unstable metadata; add
differential replay, mutation, schema, and provenance validation.

**Contracts:** propose and accept `MH-C-LEGACY-COMPAT-001` before corpus
implementation; retain `MH-C-ENV-002` and `MH-C-WORKFLOW-001` as governing
environment and contract-workflow boundaries.

**Validators:** accepted contract hash/signature, complete outcome-category
coverage, exact source/provenance binding, allowlisted normalization only,
deterministic replay on all supported Python/OS jobs, mutation rejection,
unchanged 85 percent coverage floor, three consecutive clean G2 runs, Ruff,
and project status.

**Done when:** the committed corpus replays against the legacy architecture
without semantic drift on every supported environment; changing a stable
field, case input, provenance binding, or normalization rule fails closed; G2
has passed from clean commits three consecutive times.

**Dependencies:** `MH-016` (done); compatibility contract acceptance is covered
by the project owner's programme-wide acceptance authority.

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
