# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-053 - Implement a proof/search portfolio

**Goal:** execute the exact compatible strategy graph produced by MH-051 through
the supervised MH-052 boundary, under conserved child budgets, while preferring
independently checked counterexamples and granting no authority to producer
processes, worker exit status, orchestration order, or unverified artifacts.

**Scope:** implement a deterministic, dependency-minimal proof/search portfolio
that consumes one canonical planned result, the exact open parent
`ResourceBudget`, a closed execution manifest for every planned strategy, and
the complete content-addressed input artifact set. Revalidate the complete plan
and manifest before launch; reject missing, surplus, duplicate, stale, or
cross-plan bindings. Every producer and checker invocation must be constructed
by the portfolio and executed only through `supervise_worker`; the portfolio may
never accept callables, live plugins, caller-authored worker results, implicit
entry-point discovery, shell text, or ambient executable configuration.

Define closed canonical request, execution binding, attempt, checker decision,
inconclusive outcome, and terminal portfolio result schemas. Bind every value to
the accepted planner, isolated-worker, ResourceBudget, EngineResult, Evidence,
Certificate, TheoryPlugin, capability-registry, and trust-transition contracts.
Keep retained artifact bytes out of public metadata while binding them by exact
length, role, media type, digest, strategy, component, and invocation identity.

Execute only strategies reachable from the plan entry and follow the accepted
transition table exactly. Reserve no hidden budget: each producer and checker
gets an explicit unique child lease whose limit vector fits the current parent;
reconcile the exact returned parent ledger once per invocation and carry it into
the next launch. A launch, isolation, cleanup, protocol, cancellation, or
resource failure must remain distinct from a mathematical outcome. Exhaustion
and cancellation terminate; unsupported, producer failure, malformed or
uncheckable evidence, checker inconclusive, and checker disagreement follow the
planned fallback edge or become an honest terminal inconclusive result.

Classify candidate claims only from canonical producer artifacts and exact
checker output. A sound checked counterexample has portfolio precedence over a
checked proof result; deterministic ordering may defer proof promotion until
all compatible counterexample-capable strategies have either produced a
checked refutation or reached a terminal non-refutation outcome. If the accepted
v1 descriptors cannot prove that a strategy is counterexample-capable, preserve
the planner order and make that limitation explicit rather than inferring it
from names or payloads. Never equate search coverage, absence of a witness,
producer success, exit code zero, majority vote, agreement between producers,
or repeated identical bytes with proof.

Require independent checker agreement before any `proved` or `refuted`
promotion. The checker must be the exact planned checker component, run in a
separate isolated invocation, bind the producer artifact bytes and evidence
expectation, and emit a closed canonical decision. A promotion requires a
valid accepted Evidence/Certificate chain or an equally explicit accepted
checker result permitted by the planned evidence format, exact subject/context/
obligation/strategy identities, a supported verdict, and agreement on claim
kind and semantic digest. Checker rejection, disagreement, unsupported format,
invalid evidence, missing authority, or incomplete replay remains explicit and
non-authoritative.

Make the result byte-stable for identical semantic inputs by excluding PID,
handle, wall-clock, monotonic-clock, temporary path, platform spelling, and
arrival-race observations from canonical identity. Preserve deterministic plan
order, attempt order, transition selection, reason precedence, budget lineage,
artifact inventory, checker decisions, inconclusive records, and final result
identity. MH-053 owns in-memory orchestration and promotion decisions only. It
does not persist audit history, implement replay bundles, cache outcomes, define
public user cancellation/refusal surfaces, add CLI/MCP/SDK APIs, or implement
the first theory producers; those remain MH-054 through MH-056, MH-060 through
MH-067, and MH-090 through MH-093.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-DETERMINISTIC-PLANNER-001`, `MH-C-ISOLATED-WORKER-001`,
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`, `MH-C-EVIDENCE-001`,
`MH-C-CERTIFICATE-001`, `MH-C-THEORY-PLUGIN-001`,
`MH-C-CAPABILITY-REGISTRY-001`, and applicable trust-transition contracts.
Before production implementation, propose, independently prescreen, and accept
`MH-C-PROOF-SEARCH-PORTFOLIO-001` with all six closed schemas.

Freeze byte-oriented public signatures; exact plan, parent-ledger, execution-
manifest, descriptor, executable and artifact preconditions; producer/checker
invocation construction; lease naming and reconciliation; strategy and
transition ordering; counterexample-preference limits; checker independence and
agreement rules; promotion and inconclusive taxonomies; result identity;
authority ceiling; and finite ceilings for requests, strategies, invocations,
artifacts, artifact bytes, diagnostics, strings, integers, nesting, attempts,
runtime, CPU, memory, solver calls, generated objects, proof bytes, evidence
bytes, output bytes, and diagnostic bytes.

The contract must forbid in-process producer or checker execution; caller-
supplied worker outcomes or trust claims; dynamic imports; shell execution;
ambient PATH substitution; hidden retries or speculative launches; strategy
reordering from timing; unplanned parallel work; oversubscribed child budgets;
lease reuse; result repair; proof by timeout or failed search; producer self-
attestation; unchecked witness promotion; majority voting; checker substitution;
partial-evidence promotion; machine-specific canonical identities; persistence;
cache reuse; and any authority beyond an exact independently checked verdict.

**Validators:** cover empty, invalid, exhausted, and single/multi-strategy
plans; exact manifest closure; reachable graph execution; every planned
transition; deterministic fallback; successful checked proof and refutation;
counterexample precedence where capability is explicitly sound; absence of
unsound name-based preference; producer completion without evidence; malformed,
oversized, missing, duplicate, surplus, or cross-strategy artifacts; checker
acceptance, rejection, inconclusive, disagreement, crash, timeout, cancellation,
unsupported isolation, protocol failure, and cleanup failure.

Exercise exact child-limit construction, unique leases, sequential ledger
conservation, producer/checker budget separation, exhaustion before launch,
overrun reconciliation, parent cancellation, no retry after terminal outcomes,
attempt and diagnostic ceilings, adversarial worker metadata, forged checker
decisions, swapped executable or artifact identities, stale plan/context/session
heads, descriptor substitution, transition cycles, unknown outcomes, bool-as-
int, floats, duplicate JSON keys, non-NFC text, excessive nesting, and input
mutation after validation.

Require an independent validator to reconstruct all six schemas, contract and
dependency bindings, request and manifest closure, plan reachability,
producer/checker invocation identities, ledger arithmetic, transition choices,
counterexample preference, checker agreement, promotion authority, artifact and
inconclusive inventories, and canonical result identity without importing
production portfolio helpers. Require byte-identical semantic results across
fresh processes, hash seeds, Python 3.10 through 3.14, and Linux/macOS/Windows.
Add contract, schema, unit, adversarial, independent-validator, frozen-report,
documentation, trust-inventory, clean-wheel, Ruff, compileall, project-status,
core, coverage, and exact-head remote gates.

**Done when:** the accepted proof/search portfolio contract and six schemas are
content-addressed and implementation-bound; every compatible planned strategy
runs only through isolated producer/checker child budgets; all leases reconcile
exactly; checked counterexamples receive only the precedence justified by
explicit capability data; every failed or undecided path remains an exact
inconclusive outcome; no mathematical verdict is promoted without the exact
independent checker agreement; frozen reports and trust inventories are
current; and every local and exact-head gate passes.

**Dependencies:** MH-051 supplies the exact strategy graph and transitions;
MH-052 supplies supervised worker execution and conserved child ledgers;
MH-023 through MH-028 define budget, result, evidence, certificate, plugin, and
reference authority boundaries; MH-030 through MH-037 define checker trust and
promotion. MH-054 consumes portfolio events for audit/replay, MH-055 adds safe
caching, MH-056 owns public cancellation/refusal semantics, and MH-060 through
MH-067 provide the first supported portfolio producers and checkers.

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
