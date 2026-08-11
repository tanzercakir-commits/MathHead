# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-023 - Accept the resource Budget contract

**Goal:** freeze one canonical, compositional resource-accounting model before
engine results, evidence, plugins, planners, workers, or caches can depend on
what it means to remain within a declared budget.

**Scope:** stable budget, lease, and consumption identities; wall-time and CPU
limits; peak and retained memory; solver-call and generated-object counts;
proof, evidence, output, and diagnostic sizes; canonical nesting limits;
cancellation, deadlines, exhaustion, and truncation reasons; deterministic
reservation, child allocation, refund, reconciliation, and conservation;
platform-independent units, serialization, validation errors, and hard
resource ceilings.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, and `MH-C-THEORY-CONTEXT-001`; this task will propose
and accept a new versioned Budget artifact before implementation.

**Validators:** closed schema and tagged-union checks; exact nonnegative integer
units; canonical ordering, serialization, and identity; dimension and limit
closure; child-allocation conservation with no double-spend or double-refund;
monotonic consumption and deadline rules; explicit cancellation, exhaustion,
partial-output, and truncation semantics; unknown-field, overflow, malformed
state, and adversarial mutation rejection; Ruff and project status.

**Done when:** two independent implementations have enough normative detail to
serialize the same budget state and accounting transition to identical bytes;
no timeout, cancellation, truncation, or exhausted dimension can be reported
as ordinary success; the proposal is accepted under its exact SHA-256 and all
representative conservation and authority mutations fail closed.

**Dependencies:** `MH-022` (done); result/evidence formats, runtime enforcement,
worker isolation, and cross-layer fixtures remain assigned to MH-024 through
MH-028 and MH-052.

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
