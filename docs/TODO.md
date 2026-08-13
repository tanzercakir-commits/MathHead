# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-055 - Add content-addressed safe caching

**Goal:** reuse only a previously completed and independently checked governed
result whose complete mathematical context, execution configuration, accepted
contracts, implementations, evidence chain, trust policy, and audited run
identity still match exactly; every uncertain or changed relation must become an
explicit non-hit and must never inherit authority from cache metadata.

**Scope:** add a dependency-minimal pure cache-decision boundary and a separate
effectful immutable cache-store boundary. The pure boundary owns canonical key
construction, eligibility, entry validation, and hit/miss classification. The
store boundary owns bounded persistence, lookup, and enumeration of exact
key-to-run bindings. Neither boundary may change the accepted MH-054 audited-run,
replay, or store semantics, and neither may treat a cache record as evidence or
as a new execution.

Derive every candidate key from a closed canonical inventory that includes the
exact current problem session and head, normalized mathematical input, reading
and domain assumptions, proof-obligation and canonical-context identities,
capability route and deterministic plan, selected descriptor and plugin,
producer and checker components, execution bindings and executable identities,
input artifact inventory, evidence and certificate formats, initial parent and
child budget limits, accepted contract and schema identities, implementation
and configuration identities, and active trust-transition policy. Missing,
surplus, duplicate, ambiguous, stale, noncanonical, or unsupported inventory is
not keyable.

Time, insertion order, process identity, host identity, path spelling, workspace
location, environment values, random values, TTL, LRU state, mutable aliases,
and a `latest` pointer must not enter the key or decide a hit. Any changed
session event, assumption, obligation, route, plan, plugin, descriptor,
executable, checker, configuration, budget, contract, schema, implementation,
evidence format, or trust policy must deterministically produce a different key
or an explicit non-hit.

Start with the narrowest eligibility table: only a complete freshly replayed
MH-054 run whose exact terminal result is independently checked `proved` or
`refuted`, whose selected Evidence/Certificate chain remains valid, and whose
trust tier is permitted by the current accepted policy may be stored or reused.
Unsupported, inconclusive, cancelled, exhausted, invalid, producer-failed,
verifier-failed, cleanup-failed, protocol-failed, partially persisted, or
otherwise non-authoritative outcomes are ineligible. The table is closed and
versioned; later expansion requires a new contract version.

A lookup hit must load the exact referenced run through the accepted MH-054
store boundary and perform a fresh complete replay before returning. It must
reconstruct the key and eligibility decision from the freshly loaded bundle and
the current request, validate the original logical report, result, selected
evidence, checker agreement, and trust transition, and prove that no producer or
checker process ran during lookup. The hit returns a distinct immutable cache
result that links the historical audited run; it does not fabricate a new run,
new ledger, new Evidence, new Certificate, or stronger verdict. Cache metadata
has an explicit zero-authority ceiling.

A genuine miss may be handed by an outer coordinator to the unchanged MH-054
execution path, after which an eligible completed run may be offered to the
cache store. Neither cache contract owns or invokes that execution. Corrupt,
conflicting, incomplete, stale, or unreadable cache state is classified
separately from an absent key and is never repaired, overwritten, normalized,
or silently converted into a hit. The caller may execute normally after a
closed non-hit result, but the cache boundary itself must not rerun producers or
rewrite the damaged entry.

Persist cache records in a separate explicit absolute root so the accepted
MH-054 store layout remains unchanged. Records bind one complete canonical key
to one exact audit manifest, logical report, terminal result, evidence chain,
and run reference identity. Install content and immutable key references
append-only with the reference last; deduplicate only exact bytes; make
same-key/same-record writers converge; reject same-key/different-record
conflicts; and freshly validate all visible records during load and listing.
Paths are effect-only and excluded from canonical identity.

Reuse the strict descriptor-relative, bounded-read, regular-file, ownership,
mode, link-count, ancestor-stability, relocation, atomic-install, cleanup,
directory-sync, and concurrency principles qualified by MH-054. Reject root,
relative, traversal, symlink/reparse-point, hardlink, non-regular, wrong-mode,
oversized, digest-mismatched, replaced, partial, or conflicting state. Bound
keys, entries, objects, record bytes, inventory size, nesting, strings,
integers, filesystem operations, listing work, diagnostics, and concurrent
writers. Interrupted work may leave unreachable exact content but may never
expose a valid cache hit.

The legacy `mathhead.cache` memoizer and discovery `DiskCache` remain historical
or heuristic compatibility surfaces. MH-055 must not relabel their entries as
governed evidence, import them into the trusted boundary, or weaken their
legacy compatibility behavior. Cache eviction, remote/distributed caches,
public CLI/MCP/SDK surfaces, user cancellation/refusal presentation, and new
theory producers remain outside this task.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted current versions
of the problem-session, canonical-normalization, capability-registry,
deterministic-planner, isolated-worker, proof-search-portfolio, ResourceBudget,
EngineResult, Evidence, Certificate, and trust-transition contracts. The active
audit and cache supersession graph is `MH-C-AUDITED-RUN-005`,
`MH-C-RUN-AUDIT-REPLAY-005`, `MH-C-RUN-AUDIT-STORE-006`,
`MH-C-SAFE-CACHE-002`, and `MH-C-SAFE-CACHE-STORE-002`. Before production
implementation, separately propose, independently prescreen, and accept:

- `MH-C-SAFE-CACHE-002` for the canonical request, key, eligibility table,
  entry, validation, and reuse decision; and
- `MH-C-SAFE-CACHE-STORE-002` for immutable persistence, lookup, listing,
  capability outcomes, and fresh audited-run replay.

Freeze byte-oriented public signatures; all closed schemas and exact-type
inputs; complete key dimensions and ordering; contract, source, configuration,
budget, evidence, and trust identities; eligibility and status/reason tables;
authority ceiling; replay-before-hit order; no-execution-on-hit guarantee;
miss-to-execution handoff; canonical result identity; store layout and commit
point; conflict, dedupe, relocation, capability, interruption, and concurrency
semantics; and every finite resource ceiling.

The contracts must forbid partial or prefix keys; caller-authored trust,
eligibility, cache entries, hits, reports, or audit identities; reuse across any
changed key dimension; recorded-status self-attestation; replay omission;
producer or checker execution on lookup; evidence repair; authority minted from
cache metadata; old-ledger presentation as a new execution; caching of closed
ineligible outcomes; dynamic imports; ambient discovery; shell execution;
machine-path or secret retention; time-based validity; eviction; overwrite;
mutable aliases; unbounded reads or scans; path escape; link following; and any
write outside the explicit cache root.

**Validators:** cover miss, eligible write, fresh hit, repeated hit, relocation,
same-key dedupe, different-key isolation, and exact byte stability across fresh
processes and hash seeds. Prove that a hit performs zero worker invocation and
zero producer or checker execution while still running the accepted pure replay
validators and performing accepted store load and complete audit replay. Mutate
every individual key dimension and require a distinct key or non-hit; include
cross-session, changed-assumption, obligation, route, plan,
descriptor, plugin, executable, artifact, checker, configuration, parent/child
budget, contract, schema, implementation, evidence-format, and trust-policy
substitutions.

Exercise every eligible and ineligible terminal outcome; forged eligibility,
entry, result, report, Evidence, Certificate, checker decision, trust tier, run
reference, and audit object; missing, surplus, duplicate, reordered, truncated,
repaired-hash, stale, noncanonical, oversized, wrong-exact-type, bool-as-int,
float, duplicate-key, NUL, non-NFC, deep-nesting, and post-validation mutation
cases. Require all invalid relations to remain non-authoritative and prove that
cache state cannot raise the original checker tier.

Exercise empty/new/existing roots, concurrent same/different-key writers,
same-key conflict, interruption at every install/sync/cleanup stage, unsupported
platform capabilities, full storage, permission and I/O failures, orphan
content, partial references, corrupt records and audit objects, bounded reads
and listings, wrong types/modes/owners, ancestor replacement, symlink/reparse-
point and hardlink cases, traversal and root paths, and fresh-replay failure
after lookup. Require an independent validator that reconstructs schemas, key
closure, eligibility, store identities, fresh replay, authority ceiling, and
zero-execution hit behavior without importing production cache helpers.

Add accepted-contract and schema checks, unit and adversarial suites, immutable
value checks, frozen deterministic reports, documentation, trust and fact
inventories, clean-wheel qualification, Ruff, compileall, project-status, core,
coverage, and exact-head Linux/macOS/Windows gates. Do not weaken configured
selection, thresholds, timeouts, or negative matrices to obtain a pass.

**Done when:** both accepted cache contracts and all closed schemas are
content-addressed and implementation-bound; every key dimension is complete and
independently reconstructed; only freshly replayed checked proof/refutation runs
are eligible; hit lookup invokes no worker and executes no producer or checker,
while retaining pure replay validation and minting no new authority; every
changed or invalid relation becomes an explicit non-hit;
immutable storage remains atomic, relocatable, bounded, and conflict-safe; all
frozen reports and inventories are current; and every required local and
exact-head gate passes.

**Dependencies:** MH-043 through MH-046 provide canonical context and session
history; MH-050 and MH-051 provide exact routing and plans; MH-052 and MH-053
provide isolated executions, reconciled budgets, checker agreement, and
terminal results; MH-054 provides the only auditable, replayable, durable run
identity eligible for reuse. MH-056 later owns public cancellation/refusal
semantics, MH-060 through MH-067 add theory producers/checkers, and MH-090
through MH-093 expose public interfaces.

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
