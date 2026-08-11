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

## Proposed contracts

- Accepted proposal source files remain under `proposed/` as immutable review
  evidence; their presence does not make them the active manifest target.

## Contract rule

An implementation may not edit the contract that authorized it. A behavioral
change requires a new contract version, a migration note, and fresh acceptance.
