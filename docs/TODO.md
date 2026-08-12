# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-050 - Replace keyword routing with a typed capability registry

**Goal:** replace tool-name and description keyword similarity with a bounded,
content-addressed capability registry that decides routing eligibility only from
the exact owned IR fragment, requested operation and evidence type, accepted
contract identities, cost model, platform availability, and current
TheoryContext. A registry decision may authorize a later planner to consider a
capability, but it must never execute a plugin, infer mathematical truth, select
a user reading, revive stale session evidence, or grant producer output checker
authority.

**Scope:** implement a dependency-minimal pure registry and routing boundary over
explicitly supplied canonical TheoryPlugin descriptor bytes. Registration must
independently validate every descriptor, bind its full content identity, stable
plugin/version identity, distinct producer and checker identities, accepted
contract and schema compatibility, declared fragment, evidence/certificate
formats, integer cost model, lifecycle, effects, replay modes, dependencies,
platforms, and hard limits without importing an entry point or inspecting the
host. Duplicate byte-identical registration is idempotent; logical-ID/version,
component, capability, format, dependency, or namespace collisions fail closed
for the complete registry rather than choosing by load order.

Route one exact obligation from a replay-validated successful canonical
normalization artifact and its exact current TheoryContext/session revision.
Derive the fragment summary from accepted bytes rather than trusting a
caller-supplied label, then filter capabilities by exact theory, domain,
quantifier, expression, relation, arithmetic, feature, size, version, platform,
effect, operation, evidence, certificate, replay, dependency, and availability
constraints. Emit immutable canonical registry, request, candidate,
incompatibility, and result records. Every candidate binds the descriptor,
capability, operation, producer/checker, context, obligation, input artifact,
cost derivation, required evidence/certificate formats, dependencies, declared
effects, and replay identities. Order eligible candidates deterministically by
estimated cost ascending, priority descending, capability ID, plugin ID, and
version; retain explicit dimension-level reasons for every rejected capability.

Remove keyword overlap as a routing mechanism. The legacy `recommend_tool`
surface may remain only as an explicitly non-authoritative compatibility notice
or exact-name lookup; prose tokens, substrings, descriptions, display names,
catalogue insertion order, profile labels, and tool popularity must not affect
typed eligibility or ranking. Runtime loading, entry-point discovery, plugin
initialization, planning/fallback policy, worker isolation, execution,
verification, caching, and theory-specific mathematical semantics remain owned
by later tasks.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-THEORY-CONTEXT-001`,
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`,
`MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`,
`MH-C-THEORY-PLUGIN-001`, `MH-C-CANONICAL-NORMALIZATION-001`,
`MH-C-PROBLEM-SESSION-001`, and `MH-C-PROBLEM-SESSION-STORE-001`
identities. Before implementation, propose, independently prescreen, and accept
a new versioned capability-registry contract with closed availability,
registry-entry, registry, route-request, cost-derivation, candidate,
incompatibility, and route-result schemas. Freeze exact byte-oriented public
signatures; pure effect
boundaries; descriptor admission; registry conflict and idempotency rules;
upstream replay and current-context binding; operation and evidence-format
negotiation; dependency closure; exact fragment containment; availability and
platform vocabulary; deterministic cost/ranking/tie policy; rejection reasons;
canonical serialization and SHA-256 preimages; immutable result surfaces; and
finite ceilings for input/output bytes, descriptors, versions, capabilities,
operations, formats, dependencies, fragment dimensions, candidates,
incompatibilities, diagnostics, strings, integers, nesting, validation and
routing work, runtime, and memory.

The contract must forbid keyword, regex, edit-distance, embedding, LLM, display-
name, description, or import-order routing; dynamic imports, entry-point scans,
filesystem, environment, network, subprocess, solver, clock, randomness, and
plugin execution in the pure boundary; caller-forged fragment summaries;
partial or repaired upstream artifacts; stale or cross-session contexts;
undeclared dependencies, effects, formats, or platform assumptions; producer/
checker substitution; unsupported-version fallback; collision resolution by
last writer; hidden cost terms; float costs; authority escalation; partial
registries or partial success; and exception-to-supported behavior. Closed
`routed`, `unsupported`, `ambiguous`, `invalid`, and `exhausted` outcomes must
carry no executable handle or mathematical verdict, and every non-routed result
must contain no selected capability.

**Validators:** cover empty, one-plugin, multi-version, multi-plugin, and
byte-identical duplicate registries; exact supported and unsupported fragments;
every fragment dimension and boundary; decision, construction, verification,
and explanation operations; Evidence and Certificate format/version
negotiation; exact and unavailable platforms; declared and forbidden effects;
dependency chains; optional and required extensions; lowest-cost selection;
priority and lexical ties; deterministic full candidate ordering; explicit
rejection projections; context and session revision changes; supported and
unsupported obligations; and the legacy recommendation surface without keyword
selection.

Require an independent validator to parse canonical descriptors and upstream
artifacts itself, recompute descriptor and registry identities, dependency
closure, fragment summaries, compatibility, cost terms, candidate ordering,
every incompatibility reason, route identity, and top-level result without
importing production registry helpers. Require byte-identical results across
repeated processes, hash seeds, Python 3.10 through 3.14, and
Linux/macOS/Windows. Reject duplicate or conflicting IDs, versions, components,
capabilities, namespaces and formats; dependency cycles or missing hashes;
forged current context, session, obligation, fragment, cost, priority,
availability, evidence or certificate requirements; stale/cross-reading input;
reordered semantic data; unknown fields; duplicate JSON keys; floats;
bool-as-int; NUL/non-NFC text; subclasses; mutation; pickling; oversized/deep
values; and budget exhaustion without a partial registry or candidate set. Add
contract, schema, unit, property/adversarial, independent-validator,
frozen-report, documentation, trust-inventory, clean-wheel, Ruff, compileall,
project-status, core, coverage, and exact-head remote gates.

**Done when:** the accepted contract and every closed schema are
content-addressed and bound; canonical plugin descriptors form one deterministic
collision-free registry without importing or executing plugin code; an exact
current obligation/context routes only to fully compatible candidates with
independently reproducible cost and ordering; every rejection exposes a closed
machine-readable reason; changed context, session, availability, dependency,
format, effect, or platform identity cannot reuse a prior route; keyword and
description similarity have no routing influence; no registry result claims
truth or checker authority; frozen reports and trust inventories are current;
and every local and exact-head gate passes.

**Dependencies:** MH-026 supplies the accepted declarative TheoryPlugin
contract and its exact containment/cost semantics; MH-040 through MH-045 supply
the replayable owned IR, contexts, obligations, normalization, and unsupported
boundaries; MH-046 supplies current session/revision identity and stale-evidence
invalidation. MH-051 owns strategy planning and fallbacks, MH-052 through MH-056
own isolated execution, portfolios, audit, caching, cancellation and refusal,
MH-060 through MH-067 own real theory-plugin slices, and MH-090 through MH-093
own stable public CLI/MCP/SDK exposure. The legacy task-name dispatcher remains
a compatibility surface until those interface migrations and cannot serve as
authority for this registry.

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
