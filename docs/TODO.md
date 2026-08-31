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

A cancellation intent is immutable canonical data that binds one unique intent
ID, an origin source from the closed set `user`, `parent`, or `supervisor`, a
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
origin and intent ID. Neither fact may overwrite the other.

Classify `user_cancellation` only when an origin=`user` intent was committed
before launch, the same armed event was passed to the sole audited run, fresh
replay proves that the worker actually observed cancellation, child cleanup and
parent reconciliation succeeded, and no higher-precedence internal failure
occurred. A token supplied after execution, an unanchored old audit, a final
event state, or a set event that the completed worker never observed cannot
produce user cancellation. An unanchored cancelled audit remains
`cancellation_origin_unproven` or supervisor/parent cancellation according to
the governed evidence. This mechanism commits a claimed origin; authenticating
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

Producer failure derives only from producer-phase launch, exit, protocol, or
Evidence-construction failure. Verifier failure derives only from the bound
checker phase, including checker launch, exit, protocol, Certificate, or
verification-replay failure. Checker disagreement, invalid evidence, and
producer/verifier refusal remain explicit unless the accepted closed table maps
the exact source otherwise. Supervisor, coordinator, cleanup, audit
construction, fresh replay, cross-layer invariant, and impossible-relation
failures are internal errors and may not be laundered into either component.

Internal results carry bounded stable codes and phases without traceback,
exception prose, raw diagnostics, argv, paths, environment values, secrets,
host identity, or machine-specific spelling. `MemoryError`,
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
reason, classification and precedence row, origin and observer where present,
resource dimensions where present, selected evidence/checker identities where
present, and an explicit zero-authority ceiling. It may link an already checked
proof or refutation but must not create new Evidence, Certificate, audit
history, budget ledger, verdict, trust transition, or authority. Identical
canonical inputs and complete replayed evidence produce byte-identical result
bytes across fresh processes, hash seeds, and supported platforms; clock,
scheduling, arrival order, event identity, paths, PIDs, signals, exception
text, and host state never enter the identity.

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
one new versioned execution-disposition contract for the additive outer
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
cancellation, unbound and origin-unproven cancellation, parent and supervisor
cancellation, every resource-exhaustion dimension, route-level unsupported
input, unsupported isolation, producer refusal, verifier refusal, producer
launch/exit/protocol/Evidence failure, checker launch/exit/protocol/Certificate
failure, verifier replay failure, and injected coordinator, cleanup, audit, and
replay invariant failure. Preserve separate ambiguity, truncation,
inconclusive, disagreement, invalid-evidence, and invalid-request outcomes.

Prove by call-count and identity observation that valid planned execution calls
the audited boundary exactly once, passes the same exact Event instance,
derives the portfolio request from the anchored budget, never launches work for
an early outcome, never retries, and completes fresh replay before
presentation. Cover an event already set, set during producer work, set during
checker work, never set, and set only after successful completion; intent
without event, event without armed intent, mismatched intent/request, reserved
extension collision, reused or cross-run intent, substituted base or anchored
budget, repaired hashes, and forged cancellation IDs must fail closed without
false user attribution.

Mutate every request, intent, route, plan, budget anchor, portfolio request,
manifest, object, report, event, worker observation, ledger, attempt, phase,
reason, selected artifact, contract, schema, implementation, configuration,
and trust-policy relation. Include missing, surplus, duplicate, reordered,
truncated, repaired-hash, noncanonical, oversized, wrong-exact-type,
bool-as-int, float, duplicate-key, NUL, non-NFC, excessive-nesting, subclass,
mutation, copy, and pickle attacks. Require an independent validator to
reconstruct schemas, the pre-execution anchor, exact-once ordering, fresh audit
replay, classification precedence, cause/phase mapping, resource dimensions,
and authority ceiling without importing production disposition helpers.

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
