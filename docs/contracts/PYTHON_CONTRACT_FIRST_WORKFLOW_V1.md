# Python contract-first workflow v1

**Contract ID:** `MH-C-WORKFLOW-001`  
**Status:** FROZEN  
**Frozen on:** 2026-08-09  
**Inspired by:** the US project's proposal -> acceptance -> implementation ->
verification separation.

Python has no universally enforced native function-contract system. MathHead
therefore uses separate, content-addressed intent artifacts plus Python types,
runtime boundary checks, property tests, and independent result verification.

## 1. Scope

This workflow is mandatory for critical functions:

- public engine and plugin APIs;
- parsing and normalization boundaries;
- proof, certificate, and provenance constructors/checkers;
- epistemic-tier transitions;
- resource-budget and isolation boundaries;
- project-status transitions;
- persistent session or artifact serialization.

Private mechanical helpers may inherit an accepted caller contract when they do
not introduce new externally visible behavior or trust.

## 2. Fixed sequence

```text
prose requirement
  -> proposed contract artifact
  -> deterministic pre-screen
  -> separately stored accepted artifact
  -> implementation referencing the accepted hash
  -> deterministic and property-based verification
```

The implementation may not alter the accepted contract. Contract revision
creates a new ID/version and migration entry.

## 3. Contract artifact

Each critical surface receives a strict JSON artifact with these required
fields:

- `schema`: exact version identity;
- `contract_id`: stable, never reused;
- `target`: fully qualified Python name;
- `signature`: canonical parameters and return type;
- `requires`: typed preconditions;
- `ensures`: typed postconditions;
- `raises`: allowed exception conditions;
- `effects`: filesystem, process, network, cache, and mutation behavior;
- `determinism`: sources of variability and canonicalization rules;
- `budget`: time, memory, search, and cancellation behavior;
- `epistemics`: allowed verdicts and the evidence required for each;
- `invariants`: representation and lifecycle invariants;
- `validators`: exact tests/checkers required for acceptance;
- `supersedes`: prior contract ID or `null`.

Unknown fields fail closed. Paths are repository-relative. Canonical JSON uses
UTF-8, sorted keys, stable separators, and no clock, checkout path, random
value, or machine identity.

## 4. Proposal and acceptance boundary

- AI-proposed artifacts are stored separately and marked `proposed`.
- A deterministic pre-screen verifies schema, types, internal consistency,
  satisfiable preconditions where decidable, and validator references.
- Pre-screen success means reviewable, not correct intent.
- Accepted intent is a separate artifact with a distinct SHA-256.
- Critical programme-level contracts require explicit project-owner acceptance
  at a phase gate. The AI cannot attest that a human reviewed an artifact.
- Functions wholly derived from an already accepted programme contract may be
  batch-reviewed under that contract, but their individual hashes remain
  visible.

## 5. Python implementation binding

The implementation binds to the accepted artifact using a stable contract ID
and SHA-256 recorded in machine-readable metadata. Verification checks:

- the callable exists at the declared qualified name;
- `inspect.signature` matches the canonical signature;
- public types match frozen dataclasses, enums, `Literal` values, and
  `typing.Protocol` surfaces;
- implementation metadata carries the exact accepted hash;
- the accepted artifact is unchanged;
- every named validator exists and runs;
- no outcome outside the contract's verdict or exception set is emitted.

Runtime pre/post checks protect API boundaries in tests and diagnostic mode.
They do not replace independent proof/certificate checking.

## 6. Verification ladder

Each critical contract uses the applicable levels:

1. strict schema and hash validation;
2. static type checking and API signature tests;
3. example and negative tests;
4. Hypothesis/property tests over the supported domain;
5. differential tests against the legacy oracle where available;
6. mutation tests for checkers and trust transitions;
7. independent certificate replay without the producing solver;
8. external proof-assistant verification when claimed by the result tier.

`unknown`, `unsupported`, timeout, resource exhaustion, backend disagreement,
and verifier failure are distinct fail-closed outcomes.

## 7. Completion rule

A function is not complete merely because it returns expected examples. It is
complete only when its accepted contract hash is bound to the implementation,
all required validators pass, negative cases demonstrate fail-closed behavior,
and the project-status `record-done` transaction succeeds.

