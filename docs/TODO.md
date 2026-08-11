# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-035 - Make provenance content-addressed and replayable

**Goal:** replace truncated, representation-dependent provenance with one
versioned run-bundle boundary whose identity and replay verdict bind the exact
canonical ProblemIR, TheoryContext, TheoryPlugin descriptor/version,
ResourceBudget, Evidence, Certificate, and CheckerResult bytes. A bundle is an
audit object, never authority by itself; only a fresh independent checker replay
may recover the authority already permitted by its accepted checker contract.

**Scope:** add a dependency-minimal `mathhead.kernel.provenance` verifier for a
canonical manifest plus immutable content-addressed objects. Require complete
SHA-256 digests, byte lengths, media/schema identifiers, one occurrence of each
required semantic role, explicit optional-role policy, deterministic ordering,
and exact cross-links between the run identity, producer report, evidence,
certificate, checker request, checker result, contract, implementation,
configuration, resource budget, and trust dependencies. Recompute every object
identity before interpretation; dispatch only allowlisted, versioned kernel
replayers; recompute and compare the checker result; fail closed on missing,
extra, duplicate, stale, aliased, noncanonical, unsupported, mismatched, or
over-budget content. Add a non-authoritative filesystem adapter that writes
validated objects and manifests atomically into a fan-out SHA-256 store,
refuses traversal, links, mutation, collisions, and partial commits, and can
reload a large bundle without trusting filenames or directory state. Retire the
legacy 16-hex proof hash as an authority claim while retaining a clearly named
compatibility adapter.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`, the accepted
ProblemIR, TheoryContext, ResourceBudget, EngineResult, Evidence, Certificate,
TheoryPlugin, proof-term, checker, and SAT-replay contracts. Before runtime
implementation, propose, prescreen, and accept one new
`MH-C-PROVENANCE-REPLAY-001` contract with a closed run-manifest schema. The
contract must freeze the pure verifier API, canonical JSON and binary-object
rules, required and optional roles, replay dispatch, authority lattice,
full-digest identities, atomic store layout, status/reason algebra, and finite
limits for manifest/object/aggregate bytes, entries, nesting, strings, replay
steps, diagnostics, and filesystem components. No new replay or persistence
implementation may precede acceptance of those exact bytes.

**Validators:** canonical round trips and identity stability across processes,
Python 3.10 through 3.14, and Linux/macOS/Windows; complete proof-term and SAT
happy-path replay; producer-only and unsupported-format outcomes; store/reload
equivalence for multi-megabyte streamed objects; crash-before-rename recovery;
and deterministic diagnostics. Adversarially cover truncation, bit flips,
reordering, substitution across runs, forged hashes and lengths, wrong schemas
or media types, missing/extra/duplicate roles, dangling or cyclic references,
mixed checker contracts/implementations/configurations, stale contexts or
budgets, result self-attestation, noncanonical manifests, Unicode/NUL/path
attacks, symlinks, hard links, collisions, concurrent writes, short reads,
oversized objects/manifests/collections, mutation, aliasing, copying, pickling,
subclassing, and replay exhaustion. Measure the import/source closure and prove
that the pure verifier has no solver, CAS, clock, filesystem, process, network,
dynamic-import, transport, or discovery dependency. Run Ruff, compileall,
project status, core, solver, discovery, slow, docs, release, clean-wheel
smoke, coverage, and exact same-head GitHub gates.

**Done when:** one accepted boundary makes every supported checker-attested run
independently reproducible from exact bytes alone; any partial or mismatched
bundle deterministically loses authority; persisted bundles are immutable,
atomic, content-addressed, and independently reloadable; legacy provenance can
no longer be mistaken for full replay evidence; the measured kernel closure
remains within the MH-030 budget; and every local and same-head remote gate
passes.

**Dependencies:** MH-030 through MH-034 are done and provide the frozen trust
inventory, immutable proof/evidence formats, dependency-minimal checkers, and
SAT replay. MH-036 will bind external Lean execution into the same provenance
model, and MH-037 will red-team all remaining trust-tier transitions.

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
