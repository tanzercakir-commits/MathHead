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
- `MH-C-PROBLEM-IR-001.json` governs the solver-neutral, typed ProblemIR graph,
  source provenance, complete alternative readings, and canonical identity. It
  binds `schemas/problem-ir-v1.schema.json` and is accepted at SHA-256
  `d705d82fcb6b7ac3b2f411f5a6d2cf01f80e4e8ebe71116ea8db9b91b639287b`.

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
