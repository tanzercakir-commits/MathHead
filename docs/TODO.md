# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-043 - Build proof-obligation decomposition

**Goal:** turn every accepted MH-042 per-reading domain-and-assumption context
and its ordered goals into one explicit, bounded, content-addressed proof-
obligation graph. Each obligation must expose exactly what must be established,
which local context and declarations apply, which other obligations it depends
on, why it has its current structural status, and which reviewed strategy
families are admissible, without executing a solver, checker, or proof search.

**Scope:** consume only canonical successful MH-042 result bytes and revalidate
the complete accepted MH-040 through MH-042 chain before use. Build one graph
per reading and preserve reading and goal order; unresolved alternatives remain
separate and no graph may select, compare, merge, or transfer context between
readings. Every declared goal receives a root obligation bound to its goal,
statement, exact canonical fragment, source spans, normalized fact context,
definition closure, binder scope, and dependency closure. Define a closed
obligation algebra for atomic propositions and relations, conjunction parts,
disjunction choices, implication conclusions under local hypotheses,
biconditional directions, universal bodies under bound variables, existential
witness construction and verification, unique-existence existence and
uniqueness components, domain and well-definedness side conditions, and
explicitly unsupported structures. Use only reviewed syntax-directed rules;
retain order and logical choice points, preserve symbolic witness placeholders,
and record non-decomposed or opaque nodes rather than guessing. Derive `ready`,
`waiting`, `choice_required`, and `unsupported` structural statuses solely from
the graph and local context; these statuses are workflow metadata, never truth
or proof verdicts. Attach admissible strategy-family IDs from a frozen
capability catalogue using exact structural and domain predicates, with reasons
and prerequisites; never claim that an admissible strategy will succeed. Do
not alpha-rename, reorder commutative operands or assumptions, simplify
expressions, infer implications, check satisfiability, synthesize witnesses,
solve obligations, run proof producers or checkers, or grant mathematical
authority; MH-044 and later planner/kernel tasks own those boundaries.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-PROBLEM-INTAKE-001`,
`MH-C-READING-ANALYSIS-002`, and
`MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001` identities. Before implementation,
propose, independently prescreen, and accept a new versioned proof-obligation
decomposition contract plus closed obligation, local-context, dependency-graph,
strategy-catalogue, and top-level result schemas. Freeze the exact byte-oriented
public signature; accepted upstream status and identity checks; per-reading and
ordered-goal topology; syntax-directed decomposition rules; obligation types,
status transitions, choice and witness placeholder semantics; local-context,
definition, binder, fact, origin, dependency, and source-span closure;
strategy-admissibility matching and non-success semantics; duplicate and
ordering policy; unsupported and diagnostic taxonomy; canonical serialization
and SHA-256 identities; immutable result surface; non-authority statement; and
finite ceilings for bytes, readings, goals, statements, expressions, binders,
facts, definitions, obligations, edges, contexts, strategies, choices, strings,
integers, nesting, graph work, runtime, and memory. The contract must forbid
cross-reading leakage, silent goal omission, circular dependencies, erased
choice points, implicit witness construction, heuristic strategy selection,
semantic normalization, contradiction-to-success conversion, producer,
solver, checker, adapter, filesystem, process, or network calls, partial
identities, and exception-to-success behavior.

**Validators:** cover atomic truth and every relation kind; nested `not`, `and`,
`or`, `implies`, and `iff`; ordered and nested `forall`, `exists`, and
`exists_unique`; multiple ordered goals; reading-specific definitions and all
three assumption roles; builtin, finite, interval, modular, collection,
product, function, and theory-structure contexts; domain restrictions and
well-definedness conditions; supported exact strategy matches; multiple
admissible strategies; no-match and opaque unsupported cases; shared
substructure without illegal semantic deduplication; and unresolved and
resolved alternative readings. Independently recompute every root and child
obligation, decomposition-rule ID, local-context closure, definition and fact
reference, binder scope, source fragment digest, dependency edge and
topological order, structural status, choice or witness placeholder,
strategy-family match and reason, graph identity, unsupported record, and
top-level result digest. Require identical outputs across repeated processes,
hash seeds, Python 3.10 through 3.14, and Linux/macOS/Windows. Reject invalid or
exhausted upstream results, forged or noncanonical bytes, stale hashes, missing
or surplus goals or obligations, cross-reading references, dangling or cyclic
edges, false local contexts, escaped binders, unknown rules or strategies,
wrong statuses, erased alternatives, fabricated witnesses, reordered semantic
inputs, NUL/non-NFC text, unknown fields, floats, bool-as-int, subclasses,
pickling, mutation, oversized/deep data, and validation-work exhaustion without
returning a partial graph. Prove the production module imports no natural-
language or legacy parser, NLP/LLM, solver, CAS, discovery or proof producer,
checker, filesystem, process, environment, network, clock, randomness, dynamic
import, CLI, or MCP owner. Add contract, schema, unit, property/adversarial,
independent validator and frozen report, documentation, trust inventory,
clean-wheel, Ruff, compileall, project-status, core, coverage, and exact-head
remote gates.

**Done when:** the accepted contract, schemas, and frozen decomposition and
strategy catalogues are content-addressed and bound; every goal in every
successful reading has one independently reproducible root and complete finite
obligation graph; every child, edge, local context, status, choice, placeholder,
and strategy match is source-backed and independently derivable by a reviewed
rule; logical alternatives and witness duties remain explicit; unresolved
readings remain separate; unsupported structures stay visible; no goal,
dependency, binder, fact, definition, or source origin is lost; no truth,
strategy-success, satisfiability, solver, checker, proof, partial artifact, or
mathematical authority claim is possible; frozen reports and trust inventories
are current; and every local and exact-head gate passes.

**Dependencies:** MH-042 is done and supplies complete per-reading normalized
facts with exact provenance while MH-041 supplies ordered goal projections and
choice state. MH-021 fixes ProblemIR statement and goal semantics; MH-022 fixes
TheoryContext vocabulary; MH-023 fixes finite budgets; MH-027 and MH-028 supply
independent conformance and reference scenarios. MH-044 owns alpha-renaming,
commutative and assumption normalization and stable semantic context hashes;
MH-045 owns user-facing unsupported explanations; MH-046 through MH-050 own
capability discovery, planning, execution, aggregation, and escalation, so this
task must expose deterministic metadata without pre-empting those decisions.

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
