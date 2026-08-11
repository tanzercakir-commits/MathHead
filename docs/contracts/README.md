# MathHead contracts

Contracts in this directory are intent artifacts. They are written and frozen
before the critical implementation that they govern.

## Active contracts

- `PROJECT_STATUS_CONTRACT_V1.md` governs PLAN, TODO, PROGRESS, status
  transitions, and their validators.
- `PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md` governs how critical Python function
  contracts are proposed, accepted, attached to code, and verified.
- `MH-C-ENV-001.json` governs the repository-owned development dispatcher,
  dependency profiles, platform policy, time budgets, and clean-install smoke
  checks. It was explicitly accepted by the project owner at SHA-256
  `63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87`.
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

## Proposed contracts

- Accepted proposal source files remain under `proposed/` as immutable review
  evidence; their presence does not make them the active manifest target.
- The MH-C-GRAPH-BUDGET-001 and MH-C-ENCODING-001 proposal sources are retained
  byte-identically as their immutable review evidence.
- The MH-C-LEGACY-COMPAT-001 proposal source is retained byte-identically as
  its immutable review evidence.

## Contract rule

An implementation may not edit the contract that authorized it. A behavioral
change requires a new contract version, a migration note, and fresh acceptance.
