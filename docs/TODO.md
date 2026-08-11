# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-028 - Freeze cross-layer reference fixtures

**Goal:** finish P2 by freezing a minimal, canonical, content-addressed fixture
bundle that demonstrates how ProblemIR, TheoryContext, ResourceBudget,
TheoryPlugin, EngineResult, Evidence, and Certificate bytes compose across
success and failure boundaries without importing legacy solver behavior.

**Scope:** exact scenario IDs, source-independent canonical inputs, dependency
hashes, plugin routing, budget outcomes, engine execution and mathematical
verdicts, evidence payloads, certificate observations, trust dependencies,
diagnostics, replay identity, and bundle manifest ordering for proof,
refutation, ambiguity, unsupported input, timeout, backend disagreement,
invalid certificate, and replay mismatch. Fixtures must distinguish absent
artifacts from empty artifacts and must not promote producer output, timeout,
disagreement, invalidity, or replay failure to verified truth.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`,
`MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`, and
`MH-C-THEORY-PLUGIN-001`. The MH-027 conformance report is the required
structural closure; accepted contract, proposal, schema, and report bytes stay
immutable.

**Validators:** a closed canonical fixture-manifest schema, repository-owned
cross-layer validator, and focused tests; exact eight-scenario inventory;
per-artifact schema and semantic validation; content-addressed references and
acyclic dependency closure; deterministic regeneration and relocated-copy
replay; negative mutations for byte/hash/schema/order/dependency/verdict,
authority, trust, budget, disagreement, invalid-certificate, and replay drift;
Ruff, project status, core, docs, release, and clean install gates.

**Done when:** every golden scenario validates from independently loaded bytes,
the bundle regenerates byte-identically in a relocated checkout, all required
failure states remain explicit and non-promoting, corrupting any artifact or
binding fails closed, and the complete bundle has one stable SHA-256 identity
usable by later kernel, planner, worker, plugin, API, and evaluation tasks.

**Dependencies:** MH-020 through MH-027 are done. Production foundation types,
trusted kernels, worker isolation, planners, and theory implementations remain
assigned to P3 through P6; fixtures define their shared byte boundary without
claiming those implementations already exist.

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
