# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-027 - Build contract conformance tests

**Goal:** prove that every P2 foundation contract has one executable,
cross-contract conformance boundary that detects schema, artifact, validator,
semantic, and future implementation drift before runtime code can claim
compatibility.

**Scope:** enumerate the active accepted P2 contract closure; validate exact
manifest IDs, states, paths, hashes, proposal bytes, canonical encoding,
normative schema identities, Draft 2020-12 closure, declared validator
commands, dependency hashes, supersession, and target bindings; exercise
unknown and missing fields, malformed values, duplicate keys, signature and
hash drift, absent or failing validators, contradictory requirements, budget
and authority confusion, and synthetic implementation-side changes without
editing immutable accepted artifacts.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`,
`MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`, and
`MH-C-THEORY-PLUGIN-001`. Accepted contract and proposal bytes remain
immutable; conformance mutations operate only on isolated copies.

**Validators:** a dependency-minimal repository conformance command and
focused unittest suite; exact active-contract inventory and dependency DAG;
schema meta-validation and representative positive instances; canonical byte,
manifest, proposal, validator-reference, target-binding, supersession, and
semantic-contradiction checks; adversarial isolated-copy mutations for every
required failure class; Ruff, project status, core, docs, release, and clean
install gates.

**Done when:** the accepted P2 closure passes as one deterministic report;
each required negative class is proven to fail closed without mutating source
artifacts; a synthetic implemented target can pass only with its exact
signature and source hash while implementation-side signature, source,
validator, schema, contract, or dependency drift is rejected; conformance
validity grants no mathematical authority.

**Dependencies:** MH-020 through MH-026 are done. Golden cross-layer task
fixtures remain assigned to MH-028; production dataclasses, protocols,
registries, workers, kernels, and theory implementations remain in later
phases.

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
