# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-054 - Make every run auditable and replayable

**Goal:** make the governed MH-050 through MH-053 execution path produce one
complete, durable, content-addressed audit bundle whose deterministic logical
report can be independently replayed without rerunning an untrusted producer,
trusting recorded status fields, or exposing ambient secrets and machine paths.

**Scope:** add one audited orchestration entry point that accepts the exact
capability/planning inputs, open parent `ResourceBudget`, descriptor and
execution-binding inventories, session artifacts, executable identities, and
effect-only workspace inputs already required by MH-050 through MH-053. It must
freshly recompute the route and plan, execute the portfolio through the
unchanged MH-053 boundary, and capture a closed audit transcript at the points
where producer/checker requests and results have already passed their accepted
validators. The existing `run_portfolio` contract remains unchanged and cannot
be weakened, superseded by caller-authored observations, or made persistent.

Define closed canonical schemas for audit object records, deterministic events,
the manifest, the byte-stable logical report, replay results, and persistent
store records. A bundle must bind the exact capability route request/result,
planning request/result, portfolio request/result, normalized input and current
session objects, selected descriptor/plugin and execution binding, initial and
reconciled budget ledgers, input and validated produced artifacts, checker
decisions, Evidence/Certificate chain, attempt classifications, transitions,
and terminal outcome. Objects are stored by full SHA-256 and length; semantic
roles are closed, ordered, and unique even when identical object bytes dedupe in
the physical inventory.

Derive event order only from canonical lifecycle and planner/attempt order:
run-open, input/plan binding, strategy visit, producer completion, validated
evidence classification, checker completion and decision when reached,
transition selection, and run-close. Every event has a contiguous ordinal,
previous-event link, complete subject identities, and its own canonical digest.
No wall clock, monotonic sample, process arrival order, thread schedule, PID,
handle, signal spelling, temporary name, checkout path, executable path,
workspace root, host name, user name, environment value, or random identifier
may affect an event, manifest, bundle, report, or replay identity.

Retain only allowlisted governed content. The normalized mathematical input,
session events/artifacts, descriptors, bindings, ledgers, canonical Evidence,
Certificate, and checker decision bytes are explicit audited objects. Ambient
environment, inherited credentials, command shell text, raw argv, executable
or workspace paths, stdout/stderr that failed canonical artifact validation,
diagnostic payload text, traceback text, and arbitrary caller metadata are
excluded rather than heuristically redacted. Public event/report metadata is
derived from validated enums, IDs, digests, lengths, and safe resource fields;
callers cannot append free-form log fields or self-attested trust.

Replay must treat the manifest and every object as hostile bytes. It must
recompute canonicality, object inventory closure, role constraints, every
content identity and cross-link, the current session and normalized-input
binding, fresh capability route, fresh deterministic plan, portfolio request,
portfolio result, selected Evidence/Certificate/checker agreement, ledger and
attempt continuity, transition/event order, logical report, and final bundle
identity. Missing, surplus, duplicate, corrupt, stale, reordered, unsupported,
truncated, over-budget, or repaired data returns a closed non-authoritative
invalid/exhausted replay result; it never repairs a bundle or promotes a claim.
Replay verifies the recorded logical execution and accepted checker chain but
does not rerun a producer, infer mathematical truth, or mint new authority.

The logical report must be byte-identical for identical canonical semantic
inputs and worker semantic outcomes across fresh processes, hash seeds, Python
3.10 through 3.14, and Linux/macOS/Windows. It records normalized input, plan,
selected plugin/components, declared budget limits, artifact identities,
attempt/checker classifications, transitions, selected checked result, and
authority tier while excluding nonsemantic runtime accounting observations.
The full audit manifest separately preserves exact reconciled ledger identities
and all allowlisted execution evidence required for forensic inspection.

Persist bundles in an append-only, content-addressed local store. Write objects,
manifest, logical report, and immutable run reference atomically with the run
reference last; dedupe only exact bytes; fsync durable boundaries where the
platform supports them; and freshly replay before acknowledging or loading a
run. Store paths are effect-only and never enter canonical bytes. Refuse root,
relative, traversal, symlink/reparse-point, hardlink, non-regular, wrong-mode,
digest-mismatched, replaced, partial, or conflicting state. An interrupted
write may leave unreachable content objects but may never expose a committed
run, overwrite an existing different object, or convert corruption to success.
Enumeration is digest-sorted and validates every visible run; no clock-based or
mutable latest pointer defines authority.

MH-054 owns audit capture, logical replay, and durable run history only. It does
not reuse an outcome (MH-055), define public cancellation/refusal semantics
(MH-056), add theory producers/checkers (MH-060 through MH-067), expose the
CLI/MCP/SDK surface (MH-090 through MH-093), or merge the feature branch.

**Contracts:** follow `MH-C-WORKFLOW-001`; bind accepted
`MH-C-CAPABILITY-REGISTRY-001`, `MH-C-DETERMINISTIC-PLANNER-001`,
`MH-C-ISOLATED-WORKER-001`, `MH-C-PROOF-SEARCH-PORTFOLIO-001`,
`MH-C-PROBLEM-SESSION-001`, `MH-C-RESOURCE-BUDGET-001`,
`MH-C-ENGINE-RESULT-001`, `MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`,
`MH-C-THEORY-PLUGIN-001`, and applicable trust-transition contracts. Before
production implementation, separately propose, prescreen, and accept:

- `MH-C-AUDITED-RUN-001` for the audited orchestration and capture boundary;
- `MH-C-RUN-AUDIT-REPLAY-001` for hostile-byte replay and logical reporting;
- `MH-C-RUN-AUDIT-STORE-001` for append-only persistence, loading, and listing.

Freeze byte-oriented signatures, exact-type inputs, object roles, lifecycle and
event order, safe-field policy, excluded ambient data, schema/contract
identities, cross-link reconstruction, logical-report projection, replay status
and reason taxonomy, epistemic ceiling, immutable value surfaces, store layout,
atomic commit point, deduplication, durability behavior, platform capability
outcomes, and finite ceilings for input/object/manifest/report/store bytes,
objects, events, strategies, attempts, artifacts, diagnostics, strings,
integers, nesting, path components, and filesystem operations.

The contracts must forbid caller-authored events or reports; raw environment,
credentials, argv, paths, failed stdout/stderr, traceback or arbitrary metadata
retention; clock/PID/random ordering; producer rerun during replay; recorded
status self-attestation; missing/surplus object tolerance; partial replay;
result repair; stale context/session acceptance; checker substitution; Evidence
or Certificate promotion without fresh strict parsing; authority from audit
metadata; cache lookup/reuse; mutable latest pointers; overwrite; path escape;
link attacks; silently ignored corruption; and any persistence outside the
explicit store root.

**Validators:** exercise succeeded proof and refutation, unsupported,
inconclusive, invalid evidence, producer/verifier failure, checker rejection and
disagreement, exhaustion, cancellation, truncation, invalid prelaunch input,
single and fallback strategies, and every present/absent selected-artifact
combination. Prove exact event sequences, previous links, strategy and attempt
order, chosen descriptor/component binding, normalized input discovery, route
and plan recomputation, initial/intermediate/final ledger continuity, safe
metadata projection, and byte-identical logical reports across repeated fresh
processes and hash seeds.

Mutate every manifest/report/event/object field and identity; delete, append,
duplicate, reorder, truncate, cross-run swap, stale-session swap, descriptor or
binding swap, checker-decision swap, Evidence/Certificate swap, budget-ledger
swap, and repair outer hashes. Include duplicate JSON keys, unknown fields,
floats, bool-as-int, non-NFC and NUL strings, Unicode/path-shaped values,
secret-shaped environment/argv/diagnostic content, deep nesting, huge decimals,
oversized counts and bytes, immutable-value construction/subclass/pickle/copy
attacks, and memory/process-control exception propagation.

Exercise new/existing stores, exact dedupe, multiple runs, digest-sorted listing,
relocation, clean-wheel use, concurrent same/different-run writers, write and
replace interruption at every stage, disk-full/permission/unsupported-fsync
outcomes, orphan objects, partial references, corrupt objects/manifests/reports,
wrong permissions and file types, symlink/reparse-point and hardlink attacks,
ancestor replacement, traversal, root/relative paths, and load-time fresh replay.

Require an independent validator that reconstructs schemas, contracts, object
closure, safe-field policy, event chain, route/plan/portfolio links, budget
continuity, logical report, replay result, and store identities without
importing production audit helpers. Add frozen deterministic reports, trust and
fact inventories, documentation, clean-wheel, Ruff, compileall, project-status,
core, coverage, and exact-head Linux/macOS/Windows gates.

**Done when:** all three accepted contracts and their closed schemas are
content-addressed and implementation-bound; the audited entry point captures a
complete safe transcript for every terminal portfolio path; hostile-byte replay
reconstructs the exact logical report without producer execution or new
authority; reference reports are byte-stable across processes and supported
platforms; the append-only store is atomic, immutable, relocatable, and freshly
replayed on read; no ambient secret or machine path reaches canonical records;
all negative/adversarial/store cases fail closed; frozen reports and trust/fact
inventories are current; and every local and exact-head gate passes.

**Dependencies:** MH-046 supplies replayable session history and store-hardening
patterns; MH-050 supplies the exact normalized-session route; MH-051 supplies
the deterministic plan; MH-052 supplies supervised worker and ledger evidence;
MH-053 supplies attempts, checker agreement, and selected artifacts. MH-055 may
consume only complete MH-054 identities for caching, and MH-056 defines later
public cancellation/refusal presentation without rewriting audit history.

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
