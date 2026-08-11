# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-024 - Accept the EngineResult contract

**Goal:** freeze one canonical, solver-neutral result envelope before evidence,
plugins, planners, workers, caches, or user interfaces depend on verdict,
partial-result, or replay semantics.

**Scope:** stable result and replay identities; ProblemIR, TheoryContext, and
ResourceBudget bindings; execution outcome versus mathematical verdict;
epistemic tier and trust dependencies; selected and alternative readings;
assumptions and discharged obligations; exact and one-sided bounds; witnesses,
counterexamples, proof and certificate references; producer provenance;
consumed-budget snapshots; structured diagnostics; unsupported, ambiguous,
unknown, cancelled, exhausted, truncated, disagreement, and verifier-failure
states; canonical ordering, serialization, extensions, and hard ceilings.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`, and
`MH-C-RESOURCE-BUDGET-001`; this task will propose and accept a new versioned
EngineResult artifact before implementation.

**Validators:** closed schema and tagged-union checks; exact canonical identity
and cross-artifact hash bindings; verdict, execution, epistemic, reading,
assumption, bound, witness, certificate, provenance, diagnostic, and budget
compatibility; no producer self-attestation or hidden non-success state;
unknown-field, overflow, malformed-reference, contradictory-state, and
adversarial mutation rejection; Ruff and project status.

**Done when:** two independent implementations have enough normative detail to
serialize the same result to identical bytes and reach the same fail-closed
validity decision; proof, refutation, exactness, and trust cannot be inferred
from producer labels alone; cancellation, exhaustion, truncation, ambiguity,
unsupported input, disagreement, and verifier failure cannot be ordinary
success.

**Dependencies:** `MH-021`, `MH-022`, and `MH-023` (done); independent Evidence
and Certificate semantics, plugin behavior, conformance suites, cross-layer
fixtures, and runtime enforcement remain assigned to MH-025 through MH-028 and
later implementation tasks.

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
