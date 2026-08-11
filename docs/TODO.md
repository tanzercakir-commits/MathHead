# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-025 - Accept Evidence and Certificate contracts

**Goal:** freeze independent, content-addressed Evidence and Certificate
envelopes so producer output cannot become a verified mathematical claim by
self-labeling, mutation, missing bytes, or replay drift.

**Scope:** artifact versus checker-result separation; evidence and certificate
type registries; exact subject, ProblemIR, TheoryContext, assumption, obligation,
producer, checker, implementation, configuration, and environment bindings;
canonical byte identity; format and semantic-version compatibility; dependency
closure; independent verification outcomes; deterministic replay inputs and
observations; unsupported, invalid, inconclusive, cancelled, exhausted,
truncated, verifier-failure, and disagreement states; namespaced extensions and
hard resource ceilings.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-CONTRACT-ARTIFACTS-002`,
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-RESOURCE-BUDGET-001`, and `MH-C-ENGINE-RESULT-001`; accepted
`MH-C-EVIDENCE-001` is bound at SHA-256
`c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3` and
accepted `MH-C-CERTIFICATE-001` is bound at SHA-256
`0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740`.

**Validators:** closed Draft 2020-12 schemas plus independent semantic
validators; exact canonical identities and cross-envelope hash bindings;
acyclic dependency closure; producer/checker role separation; compatibility,
trust, replay, result, diagnostic, and terminal-budget invariants; malformed,
unknown-field, duplicate-key, version-confusion, self-attestation,
substitution, omission, cycle, overflow, and adversarial mutation rejection;
Ruff and project status.

**Done when:** two independent implementations have enough normative detail to
serialize equivalent Evidence and Certificate values to identical bytes and
reach the same fail-closed verification decision; certificate validity is a
checker observation under explicit trust dependencies rather than a producer
claim; missing, changed, unsupported, inconclusive, interrupted, or
resource-limited replay can never be reported as verified.

**Dependencies:** `MH-021` through `MH-024` are done. Runtime checker kernels,
broader contract conformance, cross-layer golden fixtures, and theory-specific
certificate semantics remain assigned to MH-030 through MH-037, MH-027,
MH-028, and MH-060 through MH-067.

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
