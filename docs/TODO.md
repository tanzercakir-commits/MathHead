# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-022 - Accept the TheoryContext contract

**Goal:** freeze one canonical, immutable mathematical context before planners,
theory plugins, producers, or checkers can depend on contextual authority.

**Scope:** stable context and declaration IDs; namespaces and qualified names;
axioms, definitions, imported lemmas, and local hypotheses; dependency edges
and content hashes; import aliases and collision rules; consistency states and
the evidence that may justify them; parent revisions and monotonic derivation;
canonical serialization, identity, validation errors, and resource limits.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, and accepted `MH-C-THEORY-CONTEXT-001` at SHA-256
`d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d`.

**Validators:** closed schema and tagged-union checks, global and qualified-name
uniqueness, reference and namespace integrity, acyclic imports and declaration
dependencies, parent-revision and dependency-hash binding, consistency-state
epistemics, canonical ordering/serialization/hash rules, unknown-field and
malformed-state rejection, adversarial fixtures, Ruff, and project status.

**Done when:** two independent implementations have enough normative detail to
serialize the same theory context to identical bytes; no unchecked assertion is
silently promoted to a proved lemma or a consistent context; the proposal is
accepted under its exact SHA-256 and every semantic validator fails closed on
representative mutations.

**Dependencies:** `MH-021` (done); resource accounting, result/evidence formats,
runtime implementation, and cross-layer fixtures remain assigned to MH-023
through MH-028.

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
