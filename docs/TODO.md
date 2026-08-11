# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-020 - Implement Python contract artifact tooling

**Goal:** turn the accepted Python contract-first workflow into one strict,
transactional repository tool for proposal, pre-screen, acceptance, binding,
and deterministic verification reports.

**Scope:** versioned contract schema validation, canonical JSON and SHA-256
identity, exact proposal/accepted separation, deterministic pre-screen reports,
atomic manifest acceptance, callable signature/type binding, validator
existence and execution state, supersession rules, and fail-closed CLI exits.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-STATUS-001`, and `MH-C-ENV-002`.

**Validators:** strict unknown/missing/type rejection, canonical serialization,
proposal immutability, pre-screen non-acceptance, atomic acceptance rollback,
hash and signature drift, missing/ambiguous validators, supersession errors,
deterministic report identity, mutation/negative tests, dependency-free status
execution, Ruff, and project status.

**Done when:** one repository-owned command can pre-screen a proposal without
granting acceptance, accept only an exact successfully pre-screened artifact,
bind an implementation to its accepted identity, and reproduce a canonical
verification report; every partial, stale, ambiguous, or tampered transition
fails closed without corrupting the manifest or contract artifacts.

**Dependencies:** `MH-017` (done); `MH-C-WORKFLOW-001` and the project status
contract are already accepted programme authorities.

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
