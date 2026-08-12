# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-046 - Create persistent problem sessions

**Goal:** create a bounded, content-addressed problem-session boundary that can
be closed and reopened without losing definitions, lemmas, failed attempts,
open obligations, accepted analysis artifacts, or their exact provenance. Every
change must create a new replayable revision, and a context change must make all
dependent evidence visibly stale before any caller can mistake it for current
evidence. Historical work remains auditable but can never silently survive as
authority for a different context.

**Scope:** separate a dependency-minimal pure transition/replay core from a
non-authoritative filesystem adapter. The core consumes exact canonical session
command bytes, an optional canonical parent revision, and the complete declared
artifact byte set; it validates every object before use and emits an immutable
revision result. The adapter persists only validated canonical objects and one
committed head reference beneath an explicit absolute store root, then reloads
all bytes and asks the core to replay them afresh. Filesystem state, object
names, mtimes, host paths, clocks, locale, process IDs, random values, and Python
object identity must not participate in session or revision identity.

Support root-session creation and typed commands for adding, replacing, or
retiring a problem analysis, definition, lemma record, attempt record, and
obligation state. Definitions retain their exact ProblemIR and TheoryContext
declaration identities. Lemma records retain the claimed statement, exact
context and dependency closure, producer artifact, checker/certificate or
explicit absence, provenance replay identity, and epistemic tier; recording a
lemma never verifies it or raises its tier. Failed attempts retain strategy,
inputs, observations, diagnostics, resource outcome, produced artifact
identities, and the obligations they attempted, without being retried during
replay. Open obligations retain their canonical obligation and context
identities, dependencies, lifecycle state, and only separately validated
evidence links.

Each accepted command creates exactly one child revision with a full parent
identity, monotonically increasing revision number, canonical event identity,
complete current-view identity, and deterministic invalidation projection.
Revising or retiring context-bearing input must traverse the exact dependency
graph: directly affected and transitively dependent analyses, lemmas, attempts,
obligations, explanations, evidence, certificates, and results remain in
history but move to an explicit stale state with the causal prior/new context
identities. Unchanged artifacts may remain current only when every declared
dependency and context identity is byte-exact. A stale record can return to the
current view only through a new command containing fresh independently accepted
evidence; hash equality, labels, copied verdict fields, or a reintroduced name
cannot revive it.

Use optimistic compare-and-swap semantics for the mutable head: a write names
the exact expected parent/head, concurrent or forked updates fail without
overwriting either history, and identical retries are idempotent. The store uses
immutable content objects, temporary-file plus fsync commit discipline, a
single atomic head replacement, strict ownership/link checks, and recovery that
accepts only the last fully committed replayable head. Orphaned temporary or
unreferenced objects may be reported but never interpreted as committed state;
garbage collection, remote synchronization, multi-host consensus, merging
divergent branches, encryption, and user-facing collaboration remain outside
this task.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-ENGINE-RESULT-001`, `MH-C-EVIDENCE-001`,
`MH-C-CERTIFICATE-001`, `MH-C-PROVENANCE-REPLAY-001`, and the complete
`MH-C-PROBLEM-INTAKE-001` through
`MH-C-UNSUPPORTED-EXPLANATION-001` analysis chain. Before implementation,
propose, independently prescreen, and accept versioned problem-session
transition/replay and persistence contracts with closed command, artifact-link,
definition, lemma, attempt, obligation-state, invalidation, event, revision,
result, and store-head schemas. Freeze exact public signatures and effect
boundaries; command algebra and lifecycle transitions; root, parent, event,
revision, view, object, and session identities; artifact admission and trust-
tier rules; dependency closure and invalidation semantics; history/current-view
separation; ordering, canonical bytes, SHA-256 preimages, immutable result
surfaces, compare-and-swap conflicts, idempotency, crash recovery, path policy,
and deterministic ceilings for input/output bytes, revisions, commands,
artifacts, definitions, lemmas, attempts, obligations, dependency edges,
invalidations, diagnostics, strings, integers, nesting, replay work, I/O,
runtime, and memory.

The contracts must forbid in-place revision mutation, history deletion,
undeclared dependencies, stale-to-current promotion, self-attested evidence,
trust-tier escalation, verifier or producer substitution, cross-session or
cross-reading leakage, name-based artifact rebinding, implicit context merge,
automatic conflict resolution, retrying failed work during replay, partial
results or partial commits, arbitrary caller-selected object paths, path escape,
symlink/reparse-point or hardlink acceptance, writable committed objects,
unbounded directory scans, pickle authority, host-dependent identity, network
or subprocess use by the core, and exception-to-success behavior. Closed
`updated`, `unchanged`, `conflict`, `invalid`, and `exhausted` outcomes must
distinguish successful state transitions from ordinary refusal; every
non-success outcome carries no new revision, head, or authority.

**Validators:** exercise root creation; byte-identical reopen and full-log
replay; definition add/replace/retire; lemma records at every permitted trust
tier; successful, failed, cancelled, timed-out, and exhausted attempts; opening,
blocking, discharging, reopening, and superseding obligations; supported and
unsupported analysis artifacts; unchanged-context retention; direct and
transitive context invalidation; unrelated-artifact retention; explicit fresh-
evidence revival; idempotent duplicate commands; stale expected heads;
concurrent writers; divergent children; interrupted writes at every commit
stage; orphan temporaries and objects; missing, truncated, reordered, duplicated,
or corrupted events and objects; and reopening after process termination.

Require the independent validator to parse canonical bytes itself and recompute
the complete event chain, revision numbering, dependency graph, current view,
stale closure and causes, trust ceilings, every object/revision/session digest,
and final head without importing production transition or persistence helpers.
Require byte-identical core results and logical store contents across repeated
processes, hash seeds, Python 3.10 through 3.14, and Linux/macOS/Windows. Reject
forged parent or context identities, cycles, missing or surplus dependencies,
repaired outer hashes, fabricated checked status, evidence from another session
or reading, stale evidence referenced as current, unknown commands or fields,
duplicate JSON keys, floats, bool-as-int, NUL/non-NFC text, subclasses, mutation,
pickling, oversized/deep values, budget exhaustion, root/path traversal,
symlink/reparse-point and hardlink state, ownership/mode drift, content
collisions, concurrent head replacement, and crash remnants without changing a
valid prior head. Add contract, schema, unit, property/adversarial, independent-
validator, frozen-report, atomic-store, failure-injection, documentation, trust
inventory, clean-wheel, Ruff, compileall, project-status, core, coverage, and
exact-head remote gates.

**Done when:** accepted contracts and every closed schema are content-addressed
and bound; a session can be created, revised, atomically persisted, reopened,
and independently replayed to the same exact head and current view; definitions,
lemmas, failed attempts, and open obligations retain complete immutable history
and provenance; every relevant context change deterministically marks all and
only dependent prior artifacts stale before the new head commits; stale or
self-attested evidence cannot discharge an obligation or regain authority;
optimistic conflicts and interrupted writes preserve the last valid head;
malformed, missing, corrupted, linked, escaped, over-budget, or cross-session
state fails closed; frozen reports and trust inventories are current; and every
local and exact-head gate passes.

**Dependencies:** MH-045 is done and completes the replayable MH-040 through
MH-045 analysis artifact chain. MH-022 supplies revisioned TheoryContext,
MH-024 through MH-026 define result, evidence, certificate, and plugin trust
semantics, and MH-035 supplies independently replayed content-addressed
provenance plus a hardened immutable-store pattern. MH-050 and MH-051 own
capability routing and planning, MH-052 through MH-056 own execution scheduling
and general resource/cancellation behavior, and MH-070 through MH-086 own the
interactive mathematician workspace, so this task persists and invalidates
declared artifacts but neither plans, solves, verifies, retries, merges, nor
presents collaborative sessions.

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
