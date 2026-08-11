# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-021 - Accept the ProblemIR contract

**Goal:** freeze one canonical, typed, ambiguity-preserving problem
representation before any new parser, planner, theory plugin, or proof engine
depends on it.

**Scope:** variables and stable IDs; finite, numeric, symbolic, and structured
domains; quantifiers and binders; typed expressions and relations; definitions,
hypotheses, and ordered goals; source spans and source-document identity;
alternative readings and unresolved ambiguity; extension namespaces; schema
versioning; canonical serialization and content identity; validation errors and
resource limits.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`, and the new
`MH-C-PROBLEM-IR-002` artifact.

**Validators:** closed schema and enum checks, unique IDs, reference integrity,
scope and binder checks, source-span bounds, ambiguity preservation, canonical
ordering/serialization/hash rules, unknown-field and malformed-union rejection,
round-trip examples, deterministic pre-screen/acceptance evidence, Ruff, and
project status.

**Done when:** the ProblemIR schema and lifecycle semantics are explicit enough
for independent implementations to serialize the same mathematical problem to
identical bytes; the proposal is accepted under its exact SHA-256 and all
semantic contract validators fail closed on representative mutations.

**Dependencies:** `MH-020` (done); implementation and cross-layer fixtures
remain assigned to MH-027, MH-028, and later engine tasks.

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
