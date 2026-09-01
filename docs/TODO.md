# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-056 - Define cancellation and refusal semantics

**Goal:** add one closed, adapter-neutral execution-disposition boundary that
performs at most one accepted audited run and presents its terminal state
without collapsing user cancellation, budget exhaustion, unsupported input,
internal error, producer failure, or verifier failure into a generic error.
Every classification must derive from precommitted intent and freshly replayed
governed evidence, and presentation metadata must never create mathematical
authority.

**Scope:** implement one additive effectful coordinator around the accepted
routing, planning, and `execute_audited_run` boundaries. It must classify valid
route or planning outcomes that stop before execution without launching work.
For a valid planned request it must bind every semantic input and any optional
canonical cancellation intent before the first execution effect, derive the
actual initial parent budget and portfolio request from that binding, invoke
exactly one audited run, freshly replay the returned complete audit bundle, and
derive one immutable canonical disposition result. It must not change or
supersede the accepted planner, worker, portfolio, audit, replay, store, cache,
ResourceBudget, EngineResult, Evidence, Certificate, or trust-transition
behavior.

A cancellation intent is immutable canonical data that binds one
invocation-scoped intent ID, an origin source from the closed set `user`,
`parent`, or `supervisor`, a
closed reason code, the exact invocation inputs, accepted policy identity, and
the base parent-budget identity. The disposition request and the live
`threading.Event` are armed together or absent together. Before constructing
the portfolio request, the coordinator must commit the disposition-request
identity into one reserved namespaced extension of the initial parent budget.
The accepted portfolio and audit graphs must then bind that anchored budget.
Stripping only the reserved extension must reproduce the exact base budget.
This structural precommitment must make it impossible to retrofit a different
intent into an existing genuine audit under the repository's SHA-256 integrity
model.

The live event remains an effect-only object and never enters canonical bytes
through object identity, final state, timestamp, thread, handle, PID, or memory
address. The coordinator retains the exact event instance for the call and
passes that same instance unchanged to the sole audited execution. The result
must keep origin source and observer source separate: the current worker ledger
records a bare observed event as `source: supervisor` with its local
cancellation ID, while the anchored request may establish a distinct upstream
origin and intent ID. Neither fact may overwrite the other. Audit v5 omits the
child-budget bytes, so MH-056 may derive `observer_source=supervisor` only from
the replayed worker status plus the accepted worker contract, and must retain
`observer_cancellation_id=null` rather than claim that local ID was replayed.

Classify `user_cancellation` only when an origin=`user` intent was committed
before launch, the same armed event was passed to the sole audited run, fresh
replay proves that the worker actually observed cancellation, child cleanup and
parent reconciliation succeeded, and no higher-precedence internal failure
occurred. A token supplied after execution, an unanchored old audit, a final
event state, or a set event that the completed worker never observed cannot
produce user cancellation. `cancellation_origin_unproven` remains a closed
historical-verifier catalogue value but is unreachable from this strict fresh
coordinator: a stale, substituted, or unanchored audit returned across its
accepted boundary is the higher-precedence internal-error relation. A later
separately contracted historical-audit verifier may expose the reserved value
without presenting that history as a new MH-056 execution. This mechanism
commits a claimed origin; authenticating
the physical human or remote principal requires signatures or attestation and
is outside this task.

Freeze a closed two-axis disposition and cause catalogue with an explicit
precedence table. At minimum preserve checked proof, checked refutation,
ambiguity, user cancellation, parent cancellation, supervisor cancellation,
origin-unproven cancellation, budget exhaustion, unsupported input,
unsupported execution environment, producer refusal, verifier refusal,
truncation, inconclusive execution, checker disagreement, invalid evidence,
producer failure, verifier failure, invalid request, and internal error. The
six distinctions required by the PLAN must have different canonical cause
codes. Retain the exact upstream status and reason separately so normalization
never erases governed evidence, and never infer a class from prose, exception
text, missing output, or filename.

Budget exhaustion requires an accepted prelaunch insufficient-capacity
decision or exact parent/child ledger evidence that identifies the exhausted
resource dimensions. Wall time, CPU, memory, solver calls, generated objects,
proof, evidence, output, diagnostics, and nesting remain resource outcomes, not
user cancellation, unsupported input, mathematical refutation, or internal
error. A producer Evidence or checker Certificate that merely self-reports
`exhausted` is respectively a producer or verifier refusal unless accepted
ledger evidence independently establishes resource exhaustion.

Unsupported input derives only from a governed structural or capability
refusal for the exact current context. `ISOLATION_UNSUPPORTED` and missing host
capabilities are environment refusal, not unsupported mathematics. Producer
Evidence marked unsupported and checker Certificate marked unsupported remain
producer and verifier refusals. Unsupported, ambiguity, absent strategies, and
exhaustion never mean false, disproved, inconsistent, or impossible.

For route `NO_COMPATIBLE_CAPABILITY`, classify each exact incompatibility group
identified by descriptor and capability. Structural blockers are
`AMBIGUITY_UNSUPPORTED`, `ARITHMETIC_MISMATCH`,
`CAPABILITY_KIND_MISMATCH`, `CERTIFICATE_FORMAT_MISMATCH`, `DOMAIN_MISMATCH`,
`EVIDENCE_FORMAT_MISMATCH`, `EXPRESSION_KIND_MISMATCH`, `FEATURE_FORBIDDEN`,
`FEATURE_REQUIRED`, `LIMIT_EXCEEDED`, `OPERATION_MISMATCH`,
`QUANTIFIER_MISMATCH`, `RELATION_KIND_MISMATCH`, and `THEORY_MISMATCH`.
Availability blockers are `DEPENDENCY_UNAVAILABLE`, `EFFECT_FORBIDDEN`,
`EXTENSION_UNAVAILABLE`, `LIFECYCLE_UNAVAILABLE`, `PLATFORM_UNAVAILABLE`, and
`PYTHON_VERSION_UNAVAILABLE`. An empty descriptor inventory, or at least one
group with no structural blocker and one or more availability blockers, is
unsupported execution environment; otherwise it is unsupported input.
`REPLAY_MODE_UNAVAILABLE` must be recomputed: it is structural when the mode is
absent from the descriptor operation or plugin supported-replay set, and
availability-only when both intrinsic sets support it but the exact
availability set does not.

Producer failure derives only from a complete replayable producer-phase
exit, protocol, Evidence-construction failure, or the accepted exact producer
launch-precondition relation. Verifier failure derives only from a complete
replayable bound-checker exit, protocol, Certificate, verification failure, or
the accepted exact checker launch-precondition relation. A final producer
`refused/LAUNCH_FAILED` may map to `producer_failure` only when fresh complete
replay proves outer `failed/LAUNCH_FAILED`, final outcome `producer_error`, no
Evidence, checker not started, the matching producer worker observation,
unchanged parent ledger for that refused worker, and a terminal failed
transition. The checker analogue requires outer
`verifier_failed/LAUNCH_FAILED`, a completed producer with validated Evidence,
checker `refused/LAUNCH_FAILED`, no decision or Certificate, the matching
checker observation, unchanged checker ledger, and a terminal verifier-failed
transition. Both exact branches retain `portfolio_relation=exact` and
`portfolio_outcome_kind=launch_refused`. An earlier fallback launch refusal never outranks the final
terminal attempt. A real low-level worker `failed/LAUNCH_FAILED` that lacks
containment and reconciliation and therefore cannot survive the accepted
portfolio and audit graph as complete phase evidence is an internal audit
error; a replay-complete but mismatched launch relation is an audit-relation
internal error with `portfolio_relation=invalid`. `EXECUTABLE_INVALID` requires
another exact discriminator: a replayed `refused` worker is component refusal
with `executable_refused`, while a replayed `invalid` worker is internal error
with `executable_invalid` and `WORKER_EXECUTABLE_INVARIANT`. MH-056 must not invent a component-specific claim from an
incomplete relation. Checker disagreement, invalid evidence, and
producer/verifier refusal remain explicit unless the accepted closed table maps
the exact source otherwise. Supervisor, coordinator, cleanup, audit
construction, fresh replay, cross-layer invariant, and impossible-relation
failures are internal errors and may not be laundered into either component.

Reproduce all 49 accepted `run-logical-report-v3` portfolio status/reason pairs
in one exhaustive result table. Every pair must have one ordinary cause, one
exact internal owner, or one named governed discriminator. In particular,
`inconclusive/CHECKER_INCONCLUSIVE` is `verifier_refusal` only for a freshly
replayed Certificate verdict `unsupported` with
`certificate_unsupported`, and `inconclusive_execution` only for verdict
`inconclusive` with `certificate_inconclusive`; a missing or mismatched
decision/Certificate relation is `AUDIT_RELATION_INVALID`.

Map exact replay-complete `failed|verifier_failed` worker-invalid reasons
`REQUEST_INVALID`, `PLAN_INVALID`, `STRATEGY_MISMATCH`, and `BUDGET_INVALID`
to coordinator diagnostics `WORKER_REQUEST_INVARIANT`,
`WORKER_PLAN_INVARIANT`, `WORKER_STRATEGY_INVARIANT`, and
`WORKER_BUDGET_INVARIANT`. Map `TREE_CLEANUP_FAILED` only to
`cleanup/CLEANUP_INVARIANT`, `SUPERVISOR_FAILED` only to
`coordinator/SUPERVISOR_INVARIANT`, and exact `invalid` portfolio reasons to
`PORTFOLIO_INPUT_INVARIANT` or `PORTFOLIO_EXECUTION_INVARIANT`. A broken
required relation instead has `portfolio_relation=invalid` and
`audit/AUDIT_RELATION_INVALID`. Worker-origin, cleanup, and supervisor rows
require the exact role-specific final attempt, observation, ledger, and
transition. `PORTFOLIO_INPUT_INVALID` instead requires the accepted prelaunch
shape with no attempts or worker observations, null portfolio ledger endpoints,
and unchanged forensic ledger. `PORTFOLIO_EXECUTION_INVALID` preserves and
replays the accepted zero-or-partial attempt/ledger prefix and never fabricates
a final failure attempt.

Every invalid or internal result carries exactly one static diagnostic; ordinary
results carry none. Its ID is
`execution_disposition.<phase>.<lowercase_code>`, subject is null, related
identities are empty, and its self-hash is independently recomputed with only
that hash field null. No alternative ID, arbitrary content identity, second
diagnostic, traceback, exception prose, raw diagnostic, argv, path, environment
value, secret, host identity, or machine-specific spelling is retained. `MemoryError`,
`KeyboardInterrupt`, and `SystemExit` propagate according to accepted cleanup
behavior and are never serialized as success, cancellation, refusal, producer
failure, or verifier failure.

For executable input, invoke `execute_audited_run` exactly once. Perform no
hidden retry, speculative run, direct worker launch, producer or checker call,
cache lookup or write, audit-store write, or fallback outside the already
accepted portfolio graph. Early invalid, unsupported, ambiguous, or exhausted
route/planning outcomes launch no work. Once audited execution begins, no
ordinary outcome may invoke it again. Current safe-cache entries remain
historical checked proof/refutation reuse only and cannot serve as cancellation
or refusal evidence or be presented as a new MH-056 execution.

The canonical result must bind the complete disposition request, base and
anchored parent-budget identities, optional intent, fresh replay result, audit
manifest, logical report, terminal portfolio result, exact upstream status and
reason, `portfolio_relation`, governed `portfolio_outcome_kind`, classification
and precedence row, origin and observer where present,
resource dimensions where present, selected evidence/checker identities where
present, and an explicit zero-authority ceiling. It may link an already checked
proof or refutation but must not create new Evidence, Certificate, audit
history, budget ledger, verdict, trust transition, or authority. Identical
canonical inputs and complete replayed evidence produce byte-identical result
bytes across fresh processes, hash seeds, and supported platforms; clock,
scheduling, arrival order, event identity, paths, PIDs, signals, exception
text, and host state never enter the identity.

The result must expose an explicit nullable `cancellation_armed` field and
close request cancellation identity to exactly three shapes: no validated
request gives request/invocation/armed/intent `null/null/null/null`; an
unarmed validated request gives `SHA/SHA/false/null`; an armed validated
request gives `SHA/SHA/true/SHA`. Every nonnull value must equal the retained
validated request's request SHA, invocation SHA, armed flag, and independently
recomputed embedded intent SHA. A swapped, copied, arbitrary, or repaired
intent digest is an internal bundle-relation failure even for a
non-cancellation result.

Prelaunch evidence must follow a closed milestone matrix. Raw request failure
retains no validated or downstream identity. Request-phase mismatches retain
only a validated request; routing failure retains no planning or budget
evidence and either no route pair or exact `invalid/INVALID_INPUT`; planner
failure retains routed evidence plus exact `invalid/INVALID_INPUT`; post-plan
binding failure retains exact `planned/PLANNED`; execution-input failure adds
no budget; reserved-extension collision and budget-anchor failure retain only
the validated base budget beyond the plan; portfolio-request failure may also
retain the validated anchor but no portfolio request. `not_started` always
omits audit, report, replay, portfolio-result, provenance, and terminal status,
but does not erase a legitimately reached base, anchor, or portfolio-request
milestone. Coordinator limit exhaustion occurs before validated retention or
effect. No generic coordinator or classification-invariant result branch may
reuse any reached milestone.

This task defines the shared semantic record that later adapters must consume.
It does not freeze Python API v2, assign CLI exit codes, choose HTTP or MCP
status codes, localize prose, install signal handlers, add adapter retry logic,
create theory producers, expand cache eligibility, or merge the draft branch.
Those remain assigned to MH-060 through MH-067 and MH-090 through MH-095.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted current
capability-registry, deterministic-planner, isolated-worker,
proof-search-portfolio, ResourceBudget, EngineResult, Evidence, Certificate,
problem-session, execution-provenance, trust-transition,
`MH-C-AUDITED-RUN-005`, `MH-C-RUN-AUDIT-REPLAY-005`,
`MH-C-RUN-AUDIT-STORE-006`, `MH-C-SAFE-CACHE-002`, and
`MH-C-SAFE-CACHE-STORE-002` identities. Before production implementation,
separately propose, independently prescreen, and accept
the new versioned `MH-C-EXECUTION-DISPOSITION-001` contract for the additive outer
coordinator, pre-execution request and budget anchor, exact-once audited
execution, fresh replay, closed classification table, and immutable
adapter-neutral result.

Freeze the byte-oriented target and signature; closed disposition-request,
cancellation-intent, classification, diagnostic, and result schemas; exact
base-budget-to-anchored-budget derivation; reserved extension ownership;
intent/event pairing and lifetime; early-outcome and sole-call ordering;
cancellation observation and terminal precedence; disposition, cause, source,
observer, phase, resource-dimension, and authority tables; replay-before-
presentation behavior; immutable result surfaces; canonical hashes; exception
behavior; and finite ceilings for every input, intent, audit object, report,
result, diagnostic, string, integer, nesting, attempt, event, artifact, and
replay operation.

The contract must forbid post-hoc user attribution; unanchored-origin claims;
caller-authored audit, replay, ledger, phase, class, cause, verdict,
retryability, or authority; classification from free text, exception names,
exit-code folklore, final event state, timing, missing output, or filename;
cancellation/exhaustion collapse; input/environment/producer unsupported
collapse; producer/verifier/internal collapse; exception-to-success;
unvalidated or partial audit use; producer or checker rerun during
presentation; hidden retries; cache authority; audit mutation; dynamic import
or shell execution by the coordinator; ambient signal discovery; raw
traceback, path, environment, credential, argv, or failed-output retention;
mutable aliases; and unbounded parsing or replay.

**Validators:** exercise checked proof and refutation plus every required
non-success class with real governed artifacts: preobserved and mid-run user
cancellation, parent and supervisor cancellation, every resource-exhaustion
dimension, route-level unsupported
input, unsupported isolation, producer refusal, verifier refusal, replayable
producer exit/protocol/Evidence failure, replayable checker
exit/protocol/Certificate failure, and injected producer/checker launch,
coordinator, cleanup, audit, and replay invariant failure. Exercise both
replay-complete `refused/LAUNCH_FAILED` component mappings, prove that a prior
launch-refusal fallback does not outrank a later terminal result, and exercise
a genuine low-level `failed/LAUNCH_FAILED` to prove internal error when the
accepted graph cannot retain complete phase evidence. Mutate the final attempt
and worker-observation relation to prove replay-complete mismatches also fail
closed as internal. Preserve separate ambiguity, truncation,
inconclusive, disagreement, invalid-evidence, and invalid-request outcomes.
Exercise the reserved origin-unproven catalogue shape independently, and inject
genuine stale or unbound cancelled history to prove that this coordinator
returns internal error and never retrofits user attribution.

Independently reconstruct the accepted 49-pair portfolio matrix. Exercise every
exact internal pair for both producer and checker roles where applicable, the
refused-versus-invalid `EXECUTABLE_INVALID` discriminator, and the
unsupported-versus-inconclusive Certificate discriminator. Mutate each pair's
status, reason, relation, outcome kind, final attempt, worker observation,
ledger, transition, decision, Certificate verdict, code, and phase so no pair
can cross into another cause or a generic internal branch.

Prove by call-count and identity observation that valid planned execution calls
the audited boundary exactly once, passes the same exact Event instance,
derives the portfolio request from the anchored budget, never launches work for
an early outcome, never retries, and completes fresh replay before
presentation. Cover an event already set, set during producer work, set during
checker work, never set, and set only after successful completion; intent
without event, event without armed intent, mismatched intent/request, reserved
extension collision, reuse against a changed invocation ID or semantic input,
substituted base or anchored budget, repaired hashes, and forged cancellation
IDs must fail closed without false user attribution. Also mutate every result
request, invocation, armed, and intent field independently, including swapped
valid intent digests on non-cancellation results, and reject every shape except
the exact retained-request projection. Byte-identical reuse of
the exact same canonical invocation is observationally the same invocation;
this stateless boundary makes no durable global single-use claim.

Mutate every request, intent, route, plan, budget anchor, portfolio request,
manifest, object, report, event, worker observation, ledger, attempt, phase,
reason, selected artifact, contract, schema, implementation, configuration,
and trust-policy relation. Include missing, surplus, duplicate, reordered,
truncated, repaired-hash, noncanonical, oversized, wrong-exact-type,
bool-as-int, float, duplicate-key, NUL, non-NFC, excessive-nesting, subclass,
mutation, copy, and pickle attacks. Require an independent validator to
reconstruct schemas, the pre-execution anchor, exact-once ordering, fresh audit
replay, classification precedence, cause/phase mapping, resource dimensions,
and authority ceiling without importing production disposition helpers. For
every static diagnostic independently reconstruct its ID and own-null self-hash,
then reject altered ID, code, phase, subject, related identities, hash, a second
diagnostic, and repaired outer hashes.

Add accepted-contract and schema checks, unit, property/adversarial, and
fresh-process suites, frozen deterministic reports, updated documentation,
trust and project-fact inventories, clean-wheel qualification, Ruff,
compileall, project-status, core, coverage, and exact-head
Linux/macOS/Windows gates. Do not weaken configured selection, thresholds,
timeouts, cleanup assertions, or negative matrices to obtain a pass.

**Done when:** the accepted execution-disposition contract and every closed
schema are content-addressed and implementation-bound; optional user
cancellation is committed into the exact initial audited execution before work
and cannot be attributed post hoc; fresh replay preserves user cancellation,
budget exhaustion, unsupported input, internal error, producer failure, and
verifier failure as separate canonical causes; all other governed terminal
outcomes remain explicit; no disposition creates or upgrades mathematical
authority; P5 reference audit fixtures remain byte-stable; frozen reports and
inventories are current; and every required local and exact-head gate passes.

**Dependencies:** MH-023 and MH-024 define resource and result semantics;
MH-050 through MH-053 provide typed routing, deterministic plans, isolated
workers, exact child-ledger reconciliation, producer/checker phase separation,
and terminal portfolio outcomes; MH-054 provides complete replayable audit
evidence; MH-055 permits only exact checked historical reuse. MH-060 is the
next implementation handoff and must consume this shared outcome taxonomy for
the first verified theory slice. MH-090 through MH-095 later expose the same
record through Python, CLI, MCP, compatibility, observability, and executable
documentation without reclassifying it.

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
