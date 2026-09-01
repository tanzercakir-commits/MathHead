# MathHead project-status contract v1

**Contract ID:** `MH-C-STATUS-001`  
**Status:** FROZEN  
**Frozen on:** 2026-08-09  
**Governs:** `docs/PLAN.md`, `docs/TODO.md`, `docs/PROGRESS.md`, the vendored
project-status tool, its hook, and its CI check.

This contract is separate from its implementation. It must not be edited while
the v1 status layer is implemented. A behavioral change requires v2.

## 1. Authority

1. `docs/PLAN.md` is the sole authority for stable goals, task identity,
   dependencies, phase order, acceptance criteria, and program exit gates. It
   carries no completion markers.
2. `docs/TODO.md` is the sole live work queue. It is not completion evidence.
3. `docs/PROGRESS.md` is the sole append-only state-transition and evidence
   ledger. A task is complete only after a valid `done` record exists here and
   the task has been consumed from TODO.
4. Root `Plan.md`, `Todo.md`, and `Progress.md`, plus the discovery records
   under `docs/discovery/`, are historical inputs. They remain unchanged during
   adoption and are not status authorities for the reconstruction programme.
5. `DECISIONS.md` remains the architectural-decision ledger. It does not
   replace PLAN or PROGRESS.

The repository config must preserve the exact case-sensitive paths:

```toml
plan = "docs/PLAN.md"
todo = "docs/TODO.md"
progress = "docs/PROGRESS.md"
```

## 2. Stable task identity

- Programme tasks use `MH-NNN`, where `NNN` is exactly three digits.
- A task is declared exactly once in PLAN with a level-four heading:
  `#### MH-NNN - Title`.
- TODO may reference only task IDs declared in PLAN.
- PROGRESS may reference only task IDs declared in PLAN.
- IDs are never reused, even after cancellation or replacement.
- A replacement task names the superseded ID in PLAN and PROGRESS.

## 3. TODO contract

TODO has exactly four queues: `Now`, `Next`, `Later`, and `Blocked`.

- `Now` contains at most five task headings.
- Every task block states its goal, scope, contract prerequisites, validators,
  completion evidence, dependencies, and next handoff.
- Only `Now` work may enter implementation.
- `Next` is ordered and ready after its dependencies.
- `Later` may group PLAN ranges but must not pretend that grouped tasks are
  active.
- `Blocked` requires a concrete external dependency and a resume condition.
- Checkboxes, prose claims, test counts, or phase counts are not completion
  authority.

## 4. PROGRESS contract

- History is newest first after the first `---` divider.
- Existing bytes below a new entry are immutable: no editing, reordering,
  cleanup, or retrospective correction.
- Corrections are new entries that reference the incorrect entry.
- Every entry records date, task, state, changed facts, learned facts,
  validator evidence, limitations, and exact next action.
- `partial` retains the task in TODO and may record failing validators honestly.
- `done` consumes the task from TODO and is forbidden unless all task validators
  and the applicable global gate pass.
- A transactional failure restores both TODO and PROGRESS exactly.

## 5. State transitions

Allowed transitions are:

```text
PLAN -> Next -> Now -> partial* -> done
                         |
                         +-> Blocked -> Now
```

- Moving a task between TODO queues is not completion.
- `record-partial` requires positive `changed`, `learned`, and `next` fields,
  plus honest validator results. It never claims a green gate implicitly.
- `record-done` requires the accepted contract hash, task-specific validator
  results, global validator profile, and evidence paths or immutable command
  output identities.
- A failing, skipped, missing, timed-out, or inconclusive required validator
  prevents `done`.
- Status tooling never invents evidence and never changes PLAN.

Until task-aware evidence enforcement is implemented and validated under
`MH-002`, agents may use `record-partial` only. They must not use
`record-done` for reconstruction tasks.

## 6. Validator profiles

The eventual status tool supports named profiles. Each PLAN task names one or
more profiles and may add task-specific validators.

### `status`

- project-status tool unit tests;
- reconstruction-plan structural validator;
- exact PLAN/TODO/PROGRESS path and case checks;
- append-only PROGRESS check against the merge base;
- TODO task and queue consistency.

### `fast`

- `status`;
- source lint;
- contract manifest and hash verification;
- fast, dependency-minimal core tests;
- import and package smoke test.

### `full`

- `fast`;
- all supported Python and operating-system test matrices;
- optional dependency profiles;
- documentation examples;
- wheel build and clean-install smoke tests;
- security, deterministic-replay, and performance-regression gates.

### `release`

- `full`;
- independent certificate replay corpus;
- external proof-assistant checks required by the release;
- release evidence bundle and version/documentation consistency;
- clean tagged-source rebuild.

No independent green status job may be presented as overall project health
while a required product validator is red.

## 7. Commit and CI behavior

- A substantive source, test, contract, workflow, or configuration change must
  carry a matching PROGRESS entry in the same commit.
- A pure append-only PROGRESS correction may stand alone.
- A TODO-only completion change is forbidden; completion is performed by the
  transactional record command.
- The pre-commit hook and CI invoke the same repository-owned Python tool.
- Hooks have no silent bypass. Missing Python, malformed config, unknown task,
  case mismatch, and unavailable required validator fail closed.
- Branch protection is enabled only after the new required checks are green on
  every supported matrix.

## 8. Adoption and migration

Adoption must:

1. preserve all legacy status files byte-for-byte;
2. select the exact `docs/PLAN.md`, `docs/TODO.md`, and `docs/PROGRESS.md` paths;
3. use `adopt --dry-run` before writing;
4. vendor the repository-owned Python tool and black-box tests;
5. run a second `adopt --dry-run` that proposes no changes;
6. run status tests and `check`;
7. leave the local hook inactive until its contract tests are green.

## 9. Acceptance criteria

This contract is implemented only when:

- all authority, queue, transition, rollback, exact-case, and append-only rules
  have positive and negative tests;
- `record-partial` can preserve honest red evidence;
- `record-done` rejects every missing or non-green required validator;
- a failed transition leaves TODO and PROGRESS byte-identical;
- Linux and Windows produce the same logical result;
- CI cannot show project-status green as a substitute for a red product gate.

