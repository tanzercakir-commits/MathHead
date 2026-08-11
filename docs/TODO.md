# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-026 - Accept the TheoryPlugin contract

**Goal:** freeze one canonical, version-negotiated TheoryPlugin boundary before
the registry, planner, worker isolation, checker kernel, or theory vertical
slices depend on capability, cost, execution, or compatibility semantics.

**Scope:** stable plugin and component identities; API and data-contract
versions; declarative supported ProblemIR and TheoryContext fragments;
required Evidence and Certificate formats and features; exact capability and
effect declarations; deterministic planning-cost estimates; solve, check, and
explain request/response bindings; child ResourceBudget leases; cancellation,
exhaustion, truncation, unsupported input, ambiguity, failure, and partial
results; producer/checker separation; replay identity; extension negotiation;
registration conflicts, lifecycle, concurrency, and hard ceilings.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`,
`MH-C-EVIDENCE-001`, and `MH-C-CERTIFICATE-001`. This task will propose and
accept the canonical TheoryPlugin contract without changing accepted
dependency bytes.

**Validators:** closed Draft 2020-12 schema plus an independent semantic
validator; exact manifest, capability, fragment, operation, component,
contract, format, budget, replay, lifecycle, effect, and compatibility
bindings; producer/checker role separation; deterministic ordering and cost;
malformed, unknown-field, duplicate-key, capability-overclaim, version
confusion, undeclared-effect, self-attestation, budget-alias, cancellation,
replay-drift, collision, overflow, and adversarial mutation rejection; Ruff
and project status.

**Done when:** two independent implementations have enough normative detail to
negotiate the same plugin compatibility, route the same supported fragment,
serialize the same operation envelope to identical bytes, and reach the same
fail-closed decision; cost estimation has no execution authority; solve cannot
self-certify; check cannot reuse its producer identity; explain cannot create
mathematical authority; interrupted or unsupported work cannot be ordinary
success.

**Dependencies:** `MH-021` through `MH-025` are done. Runtime protocols,
registries, worker isolation, conformance expansion, cross-layer fixtures, and
theory-specific implementations remain assigned to MH-027, MH-028, MH-040
through MH-047, MH-050 through MH-056, and MH-060 through MH-067.

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
