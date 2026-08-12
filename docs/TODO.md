# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-045 - Produce structured unsupported explanations

**Goal:** turn every explicitly unsupported construct retained by the accepted
MH-040 through MH-044 analysis chain into a bounded, content-addressed,
machine-readable explanation that names the exact construct, identifies the
nearest currently owned fragment, and gives one safe next formalization step.
The explanation must preserve every source occurrence and make the support
boundary clearer without rewriting the problem, guessing user intent,
promising future capability, or treating unsupported as false, impossible, or
mathematically unresolved.

**Scope:** consume only canonical successful MH-044 result bytes and replay-
validate their complete embedded intake, reading, domain/assumption,
proof-obligation, and normalization chain before use. Cover every unsupported
index, `supported: false` normal form, opaque fact, and unsupported obligation
that is reachable from an accepted candidate; successful candidates with no
unsupported records receive an exact empty explanation set. Emit one stable
explanation target per source occurrence, retaining reading, registry, source
reference, semantic identity, obligation/context ownership, dependency closure,
source spans, occurrence traces, original construct kind, namespaced identifier
and arity or shape where present. Repeated or alpha-/commutative-equivalent
constructs may share a cause identity only while their distinct occurrences,
origins, multiplicity, and order remain explicit.

Classify the nearest owned fragment only through a frozen exact-match catalogue,
never through string similarity, edit distance, keyword routing, model output,
runtime plugin discovery, or solver behavior. Each catalogue entry must bind an
unsupported structural shape to an exact owner boundary, accepted contract and
fragment code, a machine action code, an explanation template, required missing
declarations or structure, and one conservative formalization recipe. Safe
recipes may ask the caller to express the construct with an already owned typed
relation, add an explicit definition or domain condition, split it into owned
sub-obligations, or retain it for a separately contracted capability; they must
not mutate ProblemIR, select a reading, invent an equivalence, silently drop a
condition, install or invoke a backend, or claim the proposed reformulation is
semantically valid. Provide deterministic English display text as a rendering
of the structured fields, while keeping codes and parameters authoritative for
later interfaces and localization.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-PROBLEM-INTAKE-001`,
`MH-C-READING-ANALYSIS-002`,
`MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001`,
`MH-C-PROOF-OBLIGATION-DECOMPOSITION-001`, and
`MH-C-CANONICAL-NORMALIZATION-001` identities. Before implementation, propose,
independently prescreen, and accept a new versioned unsupported-explanations
function contract plus closed unsupported-target, owned-fragment,
formalization-step, explanation, catalogue, and result schemas. Freeze the
exact byte-oriented public signature; successful upstream
status and identity checks; complete unsupported-source coverage; occurrence
and cause identity policy; exact construct naming; owner and nearest-fragment
vocabulary; catalogue matching and tie rules; generic fail-safe fallback;
action and template parameters; provenance, ordering, canonical serialization,
SHA-256 identities, immutable result surface, non-authority statement, and
finite ceilings for bytes, readings, graphs, contexts, obligations, facts,
forms, targets, causes, occurrences, dependencies, source spans, traces,
catalogue entries, template parameters, rendered code points, strings,
integers, nesting, explanation work, runtime, and memory.

The contract must forbid natural-language interpretation, semantic distance or
equivalence claims, heuristic nearest-fragment selection, unregistered advice,
source rewriting, unsupported-record omission, duplicate collapse, cross-
reading grouping or leakage, capability availability claims, automatic plugin
or backend selection, planner or solver calls, proof or checker inference,
truth or impossibility claims, partial explanation sets, authority escalation,
and exception-to-success behavior. `explained`, `invalid`, and `exhausted`
result states must be closed and ordinary failure states must contain no partial
targets, causes, explanations, catalogue matches, or output identity.

**Validators:** cover an entirely supported reading; exact supported and unknown
predicate assumptions at multiple arities; unsupported relation, logical, and
quantified assumption structures; repeated identical opaque facts with distinct
roles, origins, dependencies, and spans; shared canonical causes with separate
occurrences; multiple contexts and goals; inherited hypotheses; unresolved and
resolved readings; empty strategy sets; every frozen owner-fragment and action
code; exact catalogue matches, deterministic tie handling, and the generic
fallback. Require every upstream unsupported index and every `supported: false`
record to be covered exactly once as a target, every target to resolve to one
source-backed cause and explanation, and every explanation to resolve to one
catalogue entry or the explicit fallback. Verify that supported forms never
receive unsupported explanations and that no explanation crosses a reading or
changes a graph, context, obligation, status, choice, witness, strategy, trace,
or semantic identity.

An independent validator must recompute the unsupported inventory, occurrence
projection, cause grouping, exact construct descriptor, nearest owned fragment,
catalogue match, safe action parameters, display rendering, ordering, every
digest, and the top-level result without calling production helpers. Require
byte-identical output across repeated processes, hash seeds, Python 3.10 through
3.14, and Linux/macOS/Windows. Reject invalid or exhausted upstream results,
noncanonical bytes, stale hashes, forged support flags, missing or surplus
targets, ambiguous owners, false catalogue matches, unsafe or unregistered
steps, malformed template parameters, fabricated source spans or traces,
cross-reading references, reordered semantic inputs, NUL/non-NFC text, unknown
fields, floats, bool-as-int, subclasses, pickling, mutation, oversized/deep
values, and explanation-work exhaustion without a partial result. Prove the
production module imports no natural-language or legacy parser, NLP/LLM,
solver, CAS, discovery or proof producer, capability registry, planner,
checker, filesystem, process, environment, network, clock, randomness, dynamic
import, CLI, or MCP owner. Add contract, schema, unit, property/adversarial,
independent-validator and frozen-report coverage, documentation, trust inventory,
clean-wheel, Ruff, compileall, project-status, core, coverage, and exact-head
remote gates.

**Done when:** the accepted contract, closed schemas, and frozen explanation
catalogue are content-addressed and bound; every unsupported occurrence in every
successful reading is named exactly and mapped to one independently derivable
owner boundary, nearest owned fragment, and conservative next-step record;
duplicates and shared causes retain complete occurrence provenance; fully
supported inputs produce a valid empty explanation set; display text is a
deterministic rendering of authoritative structured codes and parameters; no
input artifact is rewritten and no support, equivalence, capability, solver,
proof, checker, verdict, or mathematical-authority claim is created; failure
and budget paths return no partial explanation artifact; frozen reports and
trust inventories are current; and every local and exact-head gate passes.

**Dependencies:** MH-044 is done and supplies replayable canonical forms,
unsupported semantic indexes, exact contexts and obligations, and reversible
occurrence traces; MH-043 retains structural unsupported statuses and source
topology; MH-042 retains opaque facts, roles, origins, and dependencies; MH-041
and MH-040 retain reading separation and exact source-backed declarations.
MH-050 owns runtime capability discovery and routing, MH-056 owns general
cancellation/refusal semantics, and MH-073 owns evidence-grounded mathematical
explanations, so this task is limited to deterministic support-boundary
diagnostics and safe formalization recipes.

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
