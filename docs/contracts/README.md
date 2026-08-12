# MathHead contracts

Contracts in this directory are intent artifacts. They are written and frozen
before the critical implementation that they govern.

## Active contracts

- `PROJECT_STATUS_CONTRACT_V1.md` governs PLAN, TODO, PROGRESS, status
  transitions, and their validators.
- `PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md` governs how critical Python function
  contracts are proposed, accepted, attached to code, and verified.
- `MH-C-ENV-002.json` governs the repository-owned development dispatcher,
  dependency profiles, platform policy, time budgets, and clean-install smoke
  checks. It supersedes `MH-C-ENV-001.json` and is accepted at SHA-256
  `aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d`.
- `MH-C-BASELINE-001.json` governs canonical legacy-baseline capture and
  offline replay. It was explicitly accepted by the project owner at SHA-256
  `3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2`.
- `MH-C-GRAPH-BUDGET-001.json` governs bounded graph search planning,
  fail-closed backend selection, and honest refusal semantics for MH-011. It
  was accepted under the project owner's programme-wide acceptance authority
  at SHA-256
  `3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794`.
- `MH-C-ENCODING-001.json` governs deterministic locale-safe human and machine
  output for MH-012. It was accepted under the project owner's programme-wide
  acceptance authority at SHA-256
  `b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210`.
- `MH-C-LEGACY-COMPAT-001.json` governs deterministic legacy result capture,
  allowlisted unstable-metadata normalization, and fail-closed differential
  replay for MH-017. It was accepted under the project owner's programme-wide
  acceptance authority at SHA-256
  `53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412`.
- `MH-C-CONTRACT-ARTIFACTS-002.json` governs the transactional contract
  command itself. It supersedes the mechanically valid but operationally
  unportable `001` validator set and is accepted at SHA-256
  `602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750`.
- `MH-C-PROBLEM-IR-002.json` governs the solver-neutral, typed ProblemIR graph,
  source provenance, complete alternative readings, canonical identity, and
  enforceable structural budgets. It supersedes `001`, whose numeric-literal
  and nesting limits were not fully enforceable, binds
  `schemas/problem-ir-v1.schema.json`, and is accepted at SHA-256
  `6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286`.
- `MH-C-PROBLEM-INTAKE-001.json` governs exact built-in structured input,
  syntax-neutral canonical ProblemIR construction, closed immutable results,
  bounded diagnostics, deterministic identities, and the explicit absence of
  mathematical authority or adapter fallback. It binds
  `schemas/problem-intake-v1.schema.json` and
  `schemas/problem-intake-result-v1.schema.json` and is accepted under the
  project owner's programme-wide authority at SHA-256
  `855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc`.
- `MH-C-READING-ANALYSIS-002.json` governs deterministic projection of every
  already-declared ProblemIR reading, exact structural delta recomputation,
  explicit unresolved choice state, self-contained result replay, and the
  prohibition on text inference, semantic normalization, implicit selection,
  or mathematical authority. It supersedes the non-replayable `001`, binds
  `schemas/reading-projection-v2.schema.json` and
  `schemas/problem-readings-result-v2.schema.json`, and is accepted under the
  project owner's programme-wide authority at SHA-256
  `0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70`.
- `MH-C-THEORY-CONTEXT-001.json` governs canonical theory and local contexts,
  explicit epistemic authority, content-addressed imports and declarations,
  monotonic revisions, bounded consistency claims, and immutable identity. It
  binds `schemas/theory-context-v1.schema.json` and is accepted at SHA-256
  `d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d`.
- `MH-C-RESOURCE-BUDGET-001.json` governs canonical resource ledgers,
  compositional child reservations and reconciliation, monotonic wall, memory,
  and nesting observations, exact cumulative accounting, and explicit
  cancellation, exhaustion, and truncation outcomes. It binds
  `schemas/resource-budget-v1.schema.json` and is accepted at SHA-256
  `eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045`.
- `MH-C-ENGINE-RESULT-001.json` governs canonical solver-neutral result
  envelopes, separate execution and mathematical verdict states, independent
  trust attestation, partial outcomes, bounds, artifacts, provenance,
  diagnostics, resource snapshots, and replay identity. It binds
  `schemas/engine-result-v1.schema.json` and is accepted at SHA-256
  `6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370`.
- `MH-C-EVIDENCE-001.json` governs versioned, canonical, content-addressed
  producer artifacts, subject and provenance bindings, acyclic dependency
  closure, generation replay, resource outcomes, and the prohibition on
  producer self-attestation. It binds `schemas/evidence-v1.schema.json` and is
  accepted at SHA-256
  `c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3`.
- `MH-C-CERTIFICATE-001.json` governs independent checker observations,
  exact Evidence byte and header bindings, version compatibility, replay
  outcomes, verification artifacts, complete trust dependencies, and
  fail-closed verification verdicts. It binds
  `schemas/certificate-v1.schema.json`, depends on the accepted Evidence
  contract hash, and is accepted at SHA-256
  `0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740`.
- `MH-C-THEORY-PLUGIN-001.json` governs stable plugin and component identity,
  exact capability negotiation and deterministic cost routing, the fixed
  plan-cost/solve/check/explain ABI, isolated effects, child budgets,
  cancellation and replay, and producer/checker authority separation. It
  binds `schemas/theory-plugin-v1.schema.json`, depends on the six accepted
  foundation contracts, and is accepted at SHA-256
  `2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8`.
- `MH-C-TRUST-BASE-001.json` governs the complete static trusted-computing-base
  inventory, authority and role separation, import and effect ownership,
  deterministic entry-point closures, P3 migration ownership, and the closed
  dependency-minimal checker target. It binds
  `../trust/trust-base-v1.schema.json` and is accepted under the project
  owner's programme-wide authority at SHA-256
  `2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456`.
- `MH-C-PROVENANCE-REPLAY-001.json` governs complete content-addressed run
  manifests, exact foundation and checker artifact identity, allowlisted fresh
  checker replay, authority preservation without promotion, and the separate
  atomic filesystem adapter. It binds
  `schemas/provenance-manifest-v1.schema.json` and
  `schemas/provenance-replay-result-v1.schema.json` and is accepted at SHA-256
  `31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67`.
- `MH-C-LEAN-VERIFICATION-001.json` governs the pure four-rule Lean exporter,
  exact request and result bytes, pinned Lean 4.33 and mathlib dependency
  identities, shell-free bounded runner, fresh-only proof-assistant authority,
  provenance dispatch, and non-authoritative legacy adapter. It binds
  `schemas/lean-verification-request-v1.schema.json` and
  `schemas/lean-verification-result-v1.schema.json` and is accepted at SHA-256
  `b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a`.
- `MH-C-PROOF-TERM-001.json` governs the closed four-rule immutable proof-term
  algebra, constructor and deserialization boundaries, canonical JSON wire
  bytes, full content identity, exact numeric and graph budgets, stable error
  taxonomy, and explicit absence of mathematical authority before MH-032. It
  binds `schemas/proof-term-v1.schema.json` and is accepted under the project
  owner's programme-wide authority at SHA-256
  `20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac`.
- `MH-C-KERNEL-CHECKER-001.json` governs exact evaluation of the four proof
  rules, the immutable typed attestation, canonical replay ABI, stable
  verdict taxonomy, deterministic budgets, legacy non-promotion, and the
  dependency-minimal authority boundary. It binds
  `schemas/kernel-checker-result-v1.schema.json` and is accepted under the
  project owner's programme-wide authority at SHA-256
  `78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7`.

## Repository command

The workflow is performed by one dependency-light command:

```bash
python tools/contract_artifacts.py propose --input contract.json
python tools/contract_artifacts.py prescreen \
  --proposal docs/contracts/proposed/MH-C-EXAMPLE-001.json \
  --report docs/contracts/reports/MH-C-EXAMPLE-001.prescreen.json
python tools/contract_artifacts.py accept \
  --proposal docs/contracts/proposed/MH-C-EXAMPLE-001.json \
  --prescreen-report docs/contracts/reports/MH-C-EXAMPLE-001.prescreen.json \
  --expected-sha256 <exact-proposal-sha256> --authority <accepting-authority>
python tools/contract_artifacts.py verify --all \
  --check-report docs/contracts/reports/verification-v1.json
```

`prescreen` never grants acceptance. `accept` recomputes that report and uses a
recoverable transaction, so stale evidence, a changed proposal, a partial
filesystem update, or an ambiguous active target fails without advancing the
manifest. If a process is interrupted after the transaction journal is
prepared, run `python tools/contract_artifacts.py recover` before retrying.

## Foundation conformance

The active P2 closure is checked as one unit by
`tools/validate_contract_conformance.py`; see
`FOUNDATION_CONFORMANCE_V1.md` for the inventory, failure classes, future
implementation binding rule, and authority boundary. Refresh and verify its
deterministic report with:

```bash
python tools/validate_contract_conformance.py \
  --report docs/contracts/reports/foundation-conformance-v1.json
python tools/validate_contract_conformance.py \
  --check-report docs/contracts/reports/foundation-conformance-v1.json
python -m unittest discover -s tests/contract_conformance -v
```

## Foundation reference fixtures

The MH-028 golden cross-layer bundle is under `docs/fixtures/foundation-v1/`.
It composes independently loaded ProblemIR, TheoryContext, ResourceBudget,
TheoryPlugin, Evidence, Certificate, and EngineResult bytes for eight exact
success and failure scenarios. Its content-addressed payloads, checker results,
replay logs, dependency graph, absence variants, and authority boundary are
validated with:

```bash
python tools/validate_reference_fixtures.py
python -m unittest discover -s tests/reference_fixtures -v
```

See `docs/fixtures/README.md` for the stable bundle identity, regeneration
command, object-store layout, and non-promotion rules.

## Pinned external Lean verification

MH-036 is documented in `docs/LEAN_VERIFICATION_V1.md`. The portable suite
checks canonical exports and deterministic unavailable behavior without a Lean
installation; the dedicated Linux CI job separately acquires the exact locked
toolchain and compiles all four supported proof rules through fresh provenance
dispatch:

```bash
python -m unittest discover -s tests/lean_verification -v
python tools/validate_lean_verification.py
python tools/contract_artifacts.py verify \
  --contract MH-C-LEAN-VERIFICATION-001 --require-bound
```

## Trusted computing base

The MH-030 inventory and its deterministic static import report are under
`docs/trust/`. Validate the closed schema, exact contract and fixture bytes,
all 132 source modules, 35 import roots, 24 trust surfaces, twelve entry-point
closures, effect boundaries, migrations, and minimal-kernel budget with:

```bash
python tools/validate_trust_base.py
python -m unittest discover -s tests/trust_base -v
```

See `docs/trust/README.md` for current authority boundaries and the MH-031
through MH-037 minimization map.

## Syntax-neutral problem intake

MH-040 is documented in `docs/PROBLEM_INTAKE_V1.md`. The dependency-minimal
`mathhead.problem_intake` boundary accepts only explicit exact built-in Python
data and emits independently valid canonical ProblemIR bytes or one complete
failure result. It parses no prose or mathematical notation and always carries
`mathematical_authority: false`:

```bash
python -m unittest discover -s tests/problem_intake -v
python tools/validate_problem_intake.py
python tools/contract_artifacts.py verify \
  --contract MH-C-PROBLEM-INTAKE-001 --require-bound
```

## Alternative-reading analysis

MH-041 is documented in `docs/PROBLEM_READINGS_V2.md`. The pure
`mathhead.problem_readings` boundary projects every already-declared reading,
recomputes exact structural deltas, and preserves the caller's ambiguity state
without parsing text, inventing candidates, selecting a reading, normalizing
meaning, or granting mathematical authority:

```bash
python -m unittest discover -s tests/problem_readings -v
python tools/validate_problem_readings.py
python tools/contract_artifacts.py verify \
  --contract MH-C-READING-ANALYSIS-002 --require-bound
```

## Immutable proof terms

MH-031 is documented in `docs/PROOF_TERMS_V1.md`. The implementation lives in
`mathhead.kernel.proof_terms` and exposes only structurally valid,
non-authoritative values. Validate its accepted binding, closed schema,
canonical round trips, constructor hardening, forgery resistance, and fixed
resource ceilings with:

```bash
python -m unittest discover -s tests/proof_terms -v
python tools/contract_artifacts.py verify \
  --contract MH-C-PROOF-TERM-001 --require-bound
```

## Dependency-minimal kernel checker

MH-032 is documented in `docs/KERNEL_CHECKER_V1.md`. Only
`mathhead.kernel.checkers.check_proof_term` can issue the new immutable
`checker_attestation`; malformed, false, unsupported, forged, stale, and
exhausted candidates remain non-authoritative. Validate the accepted binding,
exact rules, canonical replay, legacy differential behavior, and measured
dependency closure with:

```bash
python tools/validate_kernel_checker.py
python -m unittest discover -s tests/kernel_checker -v
python tools/contract_artifacts.py verify \
  --contract MH-C-KERNEL-CHECKER-001 --require-bound
```

## Content-addressed provenance replay

MH-035 is documented in `docs/PROVENANCE_REPLAY_V1.md`. The pure
`mathhead.kernel.provenance` boundary verifies the complete object graph and
freshly reproduces an allowlisted checker result; `mathhead.provenance_store`
is an effect-only atomic adapter. Validate both schemas, immutable result,
adversarial substitution cases, store safety, and measured closure with:

```bash
python tools/validate_provenance_replay.py
python -m unittest discover -s tests/provenance_replay -v
python tools/contract_artifacts.py verify \
  --contract MH-C-PROVENANCE-REPLAY-001 --require-bound
```

## Trust-transition red team and G3

MH-037 is documented in `docs/TRUST_TRANSITIONS_V1.md`. The pure
`mathhead.kernel.trust_transitions` boundary audits exact policy bindings while
always returning `mathematical_authority: false`; the repository runner applies
semantic attacks to the real proof, SAT, provenance, and Lean boundaries. The
canonical catalogue and report under `docs/trust/` freeze eleven permitted
edges, eleven effect ceilings, five issuer sites, and 45 killed mutants:

```bash
python tools/validate_trust_transitions.py
python -m unittest discover -s tests/trust_transitions -v
python tools/contract_artifacts.py verify \
  --contract MH-C-TRUST-TRANSITION-001 --require-bound
```

## Proposed contracts

- Accepted proposal source files remain under `proposed/` as immutable review
  evidence; their presence does not make them the active manifest target.
- The MH-C-GRAPH-BUDGET-001 and MH-C-ENCODING-001 proposal sources are retained
  byte-identically as their immutable review evidence.
- The MH-C-LEGACY-COMPAT-001 proposal source is retained byte-identically as
  its immutable review evidence.
- Superseded accepted versions and their proposal sources remain immutable;
  they are historical evidence, not active implementation authorities.

## Contract rule

An implementation may not edit the contract that authorized it. A behavioral
change requires a new contract version, a migration note, and fresh acceptance.
