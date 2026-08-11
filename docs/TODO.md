# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-030 - Inventory and minimize the trust base

**Goal:** open P3 with one complete, machine-readable trusted-computing-base
inventory that makes every current and intended authority claim explicit,
assigns it to the smallest replayable boundary, and fails closed when a new
trust-bearing primitive or dependency appears without review.

**Scope:** repository entry points and transitive imports for parsing,
canonical JSON and Unicode handling, hashing, integer and rational arithmetic,
certificate and DRUP/DRAT checking, Z3, SymPy and other producer backends,
external processes, the Python runtime and standard library, operating-system
and platform assumptions, package and environment resolution, and the future
Lean boundary. For each surface record owner, role, authority tier, exact
dependency or primitive, trusted bytes and provenance, attack and failure
modes, required-versus-excluded status, current-versus-target state, and the
task that removes or narrows it.

**Contracts:** `MH-C-WORKFLOW-001`, the accepted P2 contract set, the MH-027
conformance report, and the MH-028 reference bundle with stable identity
`4132b29b69600f8ff48477515853f66bb748c7337735c00db8e634987f70ddca`.
This task classifies existing authority; it must not silently widen any public
contract or promote producer output to mathematical truth.

**Validators:** a closed canonical inventory schema, deterministic repository
report and repository-owned validator; exact owner, role, tier, boundary,
dependency, import, primitive, provenance, risk, migration, and exclusion
inventories; static import-graph and isolated subprocess probes; dependency-
minimal and full-environment agreement; negative mutations for unknown,
missing, duplicate, stale, cyclic, unauthorised, or authority-escalating
entries; Ruff, project status, core, docs, release, and clean-install gates.

**Done when:** every trust-bearing surface reachable from supported entry
points is classified, every claim maps to an explicit current owner and a
minimal target owner, parser/serializer/hash/arithmetic/runtime/solver/proof-
assistant boundaries are named precisely, the future checker kernel has a
closed allowlist and denylist with a reproducible import budget, and any
undocumented primitive or dependency that could grant authority fails closed.

**Dependencies:** MH-020 through MH-028 are done. Immutable proof terms,
dependency-minimal checkers, internal arithmetic evidence, hardened SAT/UNSAT
replay, provenance implementation, Lean replay, and the trust-tier red team
remain assigned to MH-031 through MH-037; this inventory assigns those
migrations without claiming their implementations already exist.

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
