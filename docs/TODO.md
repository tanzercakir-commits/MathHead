# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-052 - Enforce budgets in isolated workers

**Goal:** execute already-planned producer work only inside supervised isolated
workers whose complete process trees are bounded by the accepted parent and
child resource budgets. The supervisor may enforce effects and report exact
outcomes, but process exit, returned bytes, logs, elapsed time, or successful
cleanup never grant mathematical authority.

**Scope:** implement a dependency-minimal worker protocol and supervisor for
SymPy, pure-Python enumeration, SMT, and external-process strategies. Consume
exact canonical planner output and reserve the selected child request from an
accepted parent `ResourceBudget` before process creation. The worker request
must bind the plan, strategy, capability and plugin descriptor identities,
operation, payload and artifact identities, argv/environment policy, working
directory policy, expected evidence formats, child lease, and implementation
protocol without accepting callables, live plugin objects, implicit imports,
shell text, inherited secrets, or unbound ambient configuration.

Keep policy validation pure and process control effect-only. Define a closed
canonical worker request, platform-capability record, usage/accounting record,
bounded artifact record, diagnostic record, and terminal worker result. The
result must distinguish completed producer output from refusal, unsupported
isolation, wall-time exhaustion, CPU exhaustion, memory exhaustion, output or
diagnostic exhaustion, cancellation, signal/exit failure, protocol failure,
invalid artifacts, launch failure, cleanup failure, and internal supervisor
failure. No failure may retain partial evidence as a successful result.

Enforce hard wall deadlines, CPU and address-space or committed-memory limits,
bounded stdin/stdout/stderr and protocol frames, exact solver-call/generated-
object/proof/evidence/output/diagnostic/nesting accounting, and one-time child
lease reconciliation. Launch every worker in a fresh process containment unit;
on timeout, exhaustion, cancellation, malformed protocol, parent loss, or
shutdown, terminate and reap the worker plus every descendant, including
grandchildren that ignore graceful termination. Prove postcondition checks for
no live descendant, closed pipes/handles, reconciled budget, and no reusable
partial result.

Provide explicit Linux, macOS, and Windows adapters. POSIX supervision must use
a fresh session/process group, inherited resource ceilings where supported,
monotonic parent deadlines, group termination and deterministic reaping.
Windows supervision must use a fresh process group plus a Job Object configured
to kill the complete tree on close and enforce supported process/job memory
limits. Every unavailable primitive or unverifiable containment state must be
reported as a closed unsupported/refused outcome before producer execution;
portable capability differences may not silently weaken the requested budget.

Use argument vectors only, a minimal allowlisted environment, an explicit
validated non-root working directory policy, non-inheritable handles, bounded
binary pipes, and a versioned framed protocol. Reject shell expansion, relative
executable ambiguity, PATH-based substitution, NUL/non-NFC values, duplicate
keys, floats, bool-as-int, repaired hashes, surplus artifacts, unbounded output,
PID reuse assumptions, absolute machine paths in canonical results, clock/PID
identities, and caller claims about exit, resource use, or cleanup.

MH-052 owns worker launch, containment, hard resource enforcement, exact
supervisor accounting, and tree cleanup only. It does not choose strategies,
run portfolios, validate mathematical certificates, promote producer output,
persist audit histories, cache results, expose public CLI/MCP/SDK entry points,
or define user-facing cancellation/refusal policy; those remain with MH-053
through MH-056 and MH-090 through MH-093.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-RESOURCE-BUDGET-001`, `MH-C-ENGINE-RESULT-001`, `MH-C-EVIDENCE-001`,
`MH-C-CERTIFICATE-001`, `MH-C-THEORY-PLUGIN-001`,
`MH-C-CAPABILITY-REGISTRY-001`, and deterministic-planner contract. Before
implementation, propose, independently prescreen, and accept a new versioned
isolated-worker supervisor contract with closed request, platform capability,
resource usage, artifact, diagnostic, and result schemas.

Freeze byte-oriented public signatures; exact plan/strategy/descriptor and
artifact preconditions; containment and launch rules; platform capabilities;
deadline and memory semantics; lease reservation and reconciliation; protocol
framing; environment, argv and working-directory allowlists; output retention
and truncation; complete terminal taxonomy; graceful/forced shutdown sequence;
tree-liveness and handle-cleanup postconditions; canonical result identity;
authority ceiling; and finite ceilings for requests, artifacts, frames, output,
diagnostics, processes, descendants, handles, strings, integers, nesting,
runtime, CPU, memory, and cleanup time.

The contract must forbid in-process producer execution; `shell=True`; dynamic
entry-point discovery; ambient PATH, locale, proxy, credential, token, home or
temporary-directory inheritance; caller-selected signals or raw handles;
unbounded `communicate`; detached or breakaway descendants; success inferred
from exit code alone; best-effort limits presented as enforced limits;
wall-clock identities; unreconciled leases; orphaned descendants; exception to
success conversion; partial evidence promotion; worker self-attestation; and
any mathematical authority issued by the supervisor.

**Validators:** cover successful bounded producers for all four strategy
families; unavailable producer/runtime; refusal before launch; exact lease
reservation and reconciliation; wall and CPU loops; incremental and immediate
memory pressure; oversized stdin/stdout/stderr/frame/evidence/diagnostics;
normal exit, nonzero exit, signal, crash, malformed/truncated/duplicate frames,
startup failure, parent cancellation, parent interruption, cleanup failure, and
worker attempts to forge accounting or result identities.

Exercise child and grandchild trees, ignored graceful termination, rapid exit,
PID/handle churn, pipe backpressure, descendant-held pipes, inherited-handle
attacks, shell metacharacters, hostile environment values, executable and cwd
substitution, concurrent supervisors, fork/spawn behavior, and repeated cleanup.
Platform tests must assert actual tree death and memory/wall containment using
Linux process groups and limits, macOS process groups and available limits, and
Windows Job Objects; unsupported platform primitives must produce the exact
closed capability outcome rather than a skipped or weakened success.

Require an independent validator to reconstruct the request, protocol frames,
lease arithmetic, resource totals, terminal status, artifact inventory,
diagnostics and canonical result identity without importing production
supervisor helpers. Require byte-identical semantic results across repeated
processes, hash seeds, Python 3.10 through 3.14, and Linux/macOS/Windows after
excluding explicitly nonsemantic PID, handle and monotonic-clock observations.
Add contract, schema, unit, adversarial, independent-validator, frozen-report,
documentation, trust-inventory, clean-wheel, Ruff, compileall, project-status,
core, coverage, and exact-head remote gates.

**Done when:** the accepted isolated-worker contract and closed schemas are
content-addressed and implementation-bound; SymPy, pure-Python enumeration,
SMT and external commands can execute only under an exact reserved child lease;
hard wall and supported hard memory ceilings are demonstrably enforced; timeout,
exhaustion, cancellation, failure and parent loss leave no live descendant or
unreconciled budget; canonical results never contain machine-specific authority;
no output bypasses later checkers; frozen reports and trust inventories are
current; and every local and exact-head gate passes.

**Dependencies:** MH-023 defines accepted conserved resource arithmetic and
MH-051 supplies exact deterministic plans and child requests. MH-025 through
MH-028 define result, evidence, certificate and plugin authority ceilings;
MH-050 supplies typed capability and lifecycle declarations. MH-053 consumes
the supervisor for portfolio execution, MH-054 records its audit events, MH-055
keys reusable outcomes, MH-056 owns public cancellation/refusal semantics, and
MH-060 through MH-067 provide the first real supervised theory producers.

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
