# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-031 - Define immutable proof-term types

**Goal:** replace forgeable legacy theorem objects at the new trusted boundary
with one frozen, typed, canonical proof-term algebra. Normal public APIs must
not be able to create, mutate, deserialize, copy, or promote a theorem claim
without structural validation and a later checker decision.

**Scope:** define exact tagged nodes for the supported P3 kernel fragment,
including residue, CRT, finite-sum induction, and polynomial-identity evidence;
separate untrusted proof terms from checker-issued theorem results; control all
public construction and parsing paths; deeply freeze collections and values;
bind canonical JSON bytes and content identity; enforce cycle, depth, node,
integer-size, and payload budgets; provide a stable error taxonomy; make rule
dispatch exhaustive; and keep any legacy adapter explicitly non-authoritative.
The design must leave room for later rule registration without allowing an
unknown tag, unknown field, subclass, mutable alias, or implementation detail
to acquire authority.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`, and the accepted P2
ProblemIR, TheoryContext, ResourceBudget, EngineResult, Evidence, Certificate,
and TheoryPlugin boundaries. Before implementation, propose, pre-screen, and
accept a closed proof-term contract that fixes constructors, wire form,
canonical identity, budgets, error classes, trust semantics, and the exact
implementation binding. Proof-term validity is structural only; mathematical
authority remains exclusively assigned to the dependency-minimal checker in
MH-032.

**Validators:** closed Draft 2020-12 schema and repository-owned validator;
dependency-minimal and full-environment byte agreement; canonical round trips;
positive fixtures for every rule; and adversarial tests for direct constructor
calls, `object.__new__`, dataclass replacement, pickle, copy and deepcopy,
mutable aliases, subclassing, invalid tags and fields, duplicate JSON keys,
non-canonical encodings, cycles, excess depth, excess nodes, oversized
integers, stale hashes, and forged theorem promotion. Add source and import-
boundary checks, exact implementation binding, Ruff, project status, core,
docs, release, clean-install, and same-head GitHub gates.

**Done when:** public proof-term values are deeply immutable and either valid
by controlled construction or rejected during canonical parsing; all forged
or mutated values fail closed at the checker boundary; no public constructor
can mint checker authority; every supported node has one canonical encoding
and bounded validation path; the implementation stays inside the MH-030 target
dependency budget; and all local and same-head remote gates pass.

**Dependencies:** MH-030 is done and supplies the closed trust inventory and
migration ownership. Checker evaluation and theorem issuance remain MH-032;
internal arithmetic evidence remains MH-033; SAT replay, provenance, Lean, and
trust-tier red-team work remain MH-034 through MH-037.

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
