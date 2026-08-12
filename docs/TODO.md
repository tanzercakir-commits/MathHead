# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-051 - Implement a deterministic planner

**Goal:** transform one validated typed capability-routing result for an exact
current obligation into a finite, canonical, replayable strategy plan with
explicit prerequisites, expected evidence, resource requests, success/stop
conditions, and typed fallback rules. Planning may order already-admitted
capabilities for later execution, but it must never load or run a plugin, call a
model, invent a capability, change the selected mathematical reading, claim a
proof, or upgrade producer output into checker authority.

**Scope:** implement a dependency-minimal pure planner over canonical bytes. It
must independently validate the accepted capability-route result and bind the
route, registry, request, session head, TheoryContext, obligation, fragment,
availability, descriptor, capability, component, dependency, evidence-format,
certificate-format, replay, effect, priority, and exact integer cost identities
used by every planned strategy. A non-routed, stale, incomplete, ambiguous,
invalid, exhausted, or repaired route produces no executable plan or partial
strategy set.

Represent a plan as an immutable content-addressed directed acyclic graph. Each
strategy has a stable identity, the exact candidate it derives from, ordered
prerequisites, expected Evidence and Certificate contracts/formats, declared
effects, replay mode, an integer resource request derived without floats, and
closed success, refusal, exhaustion, cancellation, verifier-failure, and
fallback transitions. Every transition names one typed outcome and one exact
next strategy or terminal state; all nodes are reachable, every fallback target
is later in the canonical order, and cycles, hidden branches, duplicate
capability use, dangling targets, or implicit exception fallbacks fail closed.

Preserve the registry's deterministic cost/priority ordering as the default
strategy order. Any permitted policy transformation must be an explicit closed
canonical input, must not make an incompatible candidate eligible, and must
have a completely specified deterministic comparison key. Define whether
unsupported, exhausted, cancelled, producer error, checker inconclusive,
checker disagreement, verifier failure, and invalid evidence stop or fall back;
never treat any of them as success. Make counterexample-first behavior explicit
only when the candidate and obligation contracts declare a sound witness path;
do not infer it from names, descriptions, prose, or mathematical folklore.

The planner outputs intent only. Worker creation, operating-system isolation,
hard wall/memory enforcement, process-tree termination, plugin import and
initialization, execution, certificate checking, portfolio concurrency,
runtime retry, persistent cache, cancellation propagation, refusal UI, and
public CLI/MCP/SDK exposure remain owned by MH-052 through MH-056 and MH-090
through MH-093.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`, `MH-C-EVIDENCE-001`,
`MH-C-CERTIFICATE-001`, `MH-C-THEORY-PLUGIN-001`,
`MH-C-CAPABILITY-REGISTRY-001`, `MH-C-PROBLEM-SESSION-001`, and current
normalization/context identities. Before implementation, propose,
independently prescreen, and accept a new versioned deterministic-planner
contract with closed policy, planning-request, prerequisite, evidence
expectation, resource request, strategy node, transition, and planning-result
schemas.

Freeze exact byte-oriented public signatures; route and current-session
preconditions; allowed planning policies; canonical node and transition order;
cost and resource arithmetic; prerequisite and dependency closure; Evidence and
Certificate expectations; terminal states; fallback outcome matrix; DAG and
reachability rules; identity preimages; immutable value surfaces; pure effects;
authority ceilings; and finite ceilings for input/output bytes, candidates,
strategies, prerequisites, transitions, dependency depth, diagnostics, strings,
integers, nesting, nodes, planning work, runtime, and memory.

The contract must forbid keyword, regex, edit-distance, embedding, LLM,
description, display-name, popularity, import-order, clock, randomness, or
historical-success planning; dynamic imports, entry-point scans, filesystem,
environment, network, subprocess, solver, plugin, or checker execution in the
pure boundary; caller-forged candidates or costs; stale/cross-session route
reuse; undeclared prerequisites, formats, effects, dependencies, or outcomes;
fallback to an incompatible or earlier strategy; cycles; exception-to-success;
partial plans; producer authority; and any result containing an executable
callable or live plugin handle.

**Validators:** cover one and many routed candidates; all four capability kinds
and operations; empty/non-routed input; exact registry order; cost, priority,
and lexical ordering; explicit policy variants; prerequisite closure; Evidence
and Certificate requirements; dependencies; effect and replay propagation;
resource request arithmetic and saturation; every engine/checker outcome;
single and multi-hop fallback; terminal success/refusal/exhaustion/cancellation/
verifier-failure; unreachable nodes; cycles; dangling or backward targets;
duplicate candidate use; and route/session/context changes.

Require an independent validator to parse and recompute the accepted route,
strategy ordering, prerequisites, evidence expectations, resource terms,
transition matrix, reachability, acyclicity, terminal coverage, node identities,
and complete plan identity without importing production planner helpers.
Require byte-identical output across repeated processes, hash seeds, Python 3.10
through 3.14, and Linux/macOS/Windows. Reject unknown or missing fields,
duplicate JSON keys, floats, bool-as-int, NUL/non-NFC text, noncanonical bytes,
stale or repaired hashes, reordered semantic data, mutation, subclassing,
pickling, oversized/deep values, and budget exhaustion without partial state.
Add contract, schema, unit, property/adversarial, independent-validator,
frozen-report, documentation, trust-inventory, clean-wheel, Ruff, compileall,
project-status, core, coverage, and exact-head remote gates.

**Done when:** the accepted planner contract and closed schemas are
content-addressed and implementation-bound; a routed exact current obligation
produces one deterministic canonical acyclic plan whose every strategy,
prerequisite, expected artifact, resource term, terminal, and fallback is
independently reproducible; non-routed or stale input yields no partial plan;
no hidden model, plugin execution, keyword selection, or authority escalation is
possible; frozen reports and trust inventories are current; and every local and
exact-head gate passes.

**Dependencies:** MH-050 supplies validated compatible candidates, explicit
incompatibilities, exact costs, registry order, and current route identity;
MH-040 through MH-046 supply canonical obligations, context, normalization, and
session freshness. MH-052 enforces the resource requests in isolated workers,
MH-053 executes proof/search portfolios, MH-054 audits producer/checker
separation, MH-055 owns cache and deterministic replay, MH-056 owns cancellation
and refusal behavior, and MH-060 through MH-067 supply real theory strategies.

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
