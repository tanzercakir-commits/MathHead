# MathHead contracts

Contracts in this directory are intent artifacts. They are written and frozen
before the critical implementation that they govern.

## Active contracts

- `PROJECT_STATUS_CONTRACT_V1.md` governs PLAN, TODO, PROGRESS, status
  transitions, and their validators.
- `PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md` governs how critical Python function
  contracts are proposed, accepted, attached to code, and verified.

## Contract rule

An implementation may not edit the contract that authorized it. A behavioral
change requires a new contract version, a migration note, and fresh acceptance.

