# MathHead repository instructions

## Source of truth

- Read `docs/PLAN.md`, `docs/TODO.md`, and `docs/PROGRESS.md` before
  substantial work.
- `docs/PLAN.md` defines task identity, dependencies, and acceptance criteria.
- `docs/TODO.md` is the only live queue and may contain at most five tasks in
  `Now`.
- `docs/PROGRESS.md` is append-only evidence. Never edit, delete, or reorder an
  older entry.
- Root `Plan.md`, `Todo.md`, `Progress.md`, and the discovery status records are
  legacy evidence, not current status authority. Preserve them unchanged.

## Status transitions

- Use `python tools/project_status.py check` before and after status work.
- Use the repository tool for partial and completed transitions; never update a
  task as done by hand.
- Until `MH-002` is completed under its negative and cross-platform validators,
  only `record-partial` is authorized for reconstruction tasks. Do not invoke
  `record-done`.
- Never bypass, remove, skip, or relabel a failing configured validator.
- A green project-status job is not evidence that the product test matrix is
  green.

## Contract-first implementation

- Critical functions require a proposed and separately accepted contract before
  implementation. Follow
  `docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md`.
- Keep accepted contracts separate from code and content-address them.
- Do not change an accepted contract during its implementation. A behavioral
  change requires a new contract version and migration record.
- Public APIs, parsers, proof/certificate checkers, trust-tier transitions,
  resource budgets, status transitions, and serialization are always critical.
- Do not claim a function or task complete until every validator required by
  its accepted contract and PLAN entry passes.

## Development discipline

- Work only on a task present in TODO `Now` and keep changes within its scope.
- Preserve unrelated user changes and the legacy compatibility corpus.
- Prefer typed, immutable Python boundary objects and independent checkers over
  producer self-attestation.
- Keep discovery and heuristic producers outside the trusted kernel.
- Record honest partial progress when a required product check remains red.
