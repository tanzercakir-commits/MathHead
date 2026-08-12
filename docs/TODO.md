# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-042 - Normalize domains and assumptions

**Goal:** turn every accepted MH-041 reading projection into one explicit,
bounded, content-addressed domain-and-assumption context without strengthening,
weakening, solving, or merging the declared mathematics. Number systems,
variable domains, interval bounds, modular carriers, finite enumerations,
collection finiteness, products, total or partial function spaces,
theory-structure parameters, dimensions, regularity or graph-class predicates,
nonzero restrictions, side conditions, and other declared assumptions must
remain machine-readable facts with exact origin and applicability.

**Scope:** consume only canonical successful MH-041 result bytes and revalidate
their embedded accepted intake and reading analysis before use. Normalize each
candidate independently; never combine unresolved alternatives or transfer a
fact between readings. Define a closed fact algebra that distinguishes domain
declarations, memberships, bounds, exclusions, equalities and disequalities,
finiteness, cardinality, modular, shape/dimension, regularity, theory-class,
function-totality, given, domain-constraint, side-condition, and explicitly
unsupported predicates. Every fact must bind its reading, originating domain
or assumption and statement/expression IDs, source spans, exact canonical
fragment digest, dependency IDs, and a derivation rule from a frozen rule
catalogue. Preserve declaration order where semantic and use only contractually
safe structural normalization; record unsupported or opaque constructs rather
than guessing. Do not perform alpha-renaming, commutative or algebraic
rewriting, assumption sorting for context identity, satisfiability checking,
logical implication, equivalence, proof-obligation decomposition, solving, or
proof checking; MH-043 and MH-044 own those later boundaries.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-PROBLEM-INTAKE-001`, and
`MH-C-READING-ANALYSIS-002` identities. Before implementation, propose,
independently prescreen, and accept
`MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001` plus closed input/result, normalized context, fact, and
rule-catalogue schemas. Freeze the exact byte-oriented public
signature; accepted upstream status and identity checks; per-reading topology;
all eight ProblemIR domain variants and six builtin carriers; assumption-role
semantics; permitted structural extraction and normalization rules; origin,
dependency, and source-span preservation; ordering and duplicate policy;
unsupported and diagnostic taxonomy; canonical serialization and SHA-256
identities; immutable result surface; non-authority statement; dependency
closure; and finite ceilings for bytes, readings, domains, assumptions,
statements, expressions, facts, dependencies, strings, integers, nesting,
graph work, runtime, and memory. The contract must forbid default-domain
inference, undeclared assumptions, heuristic operator interpretation,
cross-reading fact leakage, semantic strengthening or weakening, hidden
deduplication, contradiction-to-success conversion, producer/solver/checker
calls, adapter fallback, partial identities, and exception-to-success behavior.

**Validators:** cover boolean, natural, integer, rational, real, and complex
builtin domains; finite domains; open, closed, half-open, and unbounded integer,
rational, and real intervals; modular domains; finite, infinite, and unknown
sets, sequences, and multisets; nested products; nullary and higher-arity total
and partial function spaces; parameterized theory structures; and variables,
definitions, expressions, and quantifier binders that reference them. Cover
given, domain-constraint, and side-condition assumptions, including explicit
membership, nonzero, lower/upper bounds, equality/disequality, finiteness,
cardinality, dimension/shape, graph class, regularity, and opaque theory
predicates where present in the accepted operator vocabulary. Independently
recompute every extracted fact, rule ID, origin link, dependency closure,
fragment digest, ordering decision, candidate/context identity, unsupported
record, and top-level result digest. Require identical outputs across repeated
processes, hash seeds, Python 3.10 through 3.14, and Linux/macOS/Windows. Reject
invalid or exhausted upstream results, unresolved-selection forgery,
noncanonical bytes, stale hashes, missing or extra candidates, dangling or
cross-reading origins, unknown rule IDs, false derivations, omitted or surplus
facts, illegal duplicate collapse, reordered semantic inputs, NUL/non-NFC text,
unknown fields, floats, bool-as-int, subclasses, pickling, mutation, cycles,
oversized/deep data, and validation-work exhaustion without returning a partial
context. Prove the production module imports no natural-language or legacy
parser, NLP/LLM, solver, CAS, discovery producer, checker, filesystem, process,
environment, network, clock, randomness, dynamic-import, CLI, or MCP owner. Add
contract, schema, unit, property/adversarial, independent validator and frozen
report, documentation, trust inventory, clean-wheel, Ruff, compileall,
project-status, core, coverage, and exact-head remote gates.

**Done when:** the accepted contract, schemas, and frozen rule catalogue are
content-addressed and bound; every successful reading receives one independently
reproducible context; every emitted fact is complete, source-backed, and
derivable only by a reviewed structural rule; all declared domain variants and
assumption roles remain explicit; unsupported predicates remain visible and
non-authoritative; unresolved readings stay separate; no undeclared fact,
semantic equivalence claim, satisfiability verdict, solver call, hidden merge,
partial artifact, or mathematical authority is possible; frozen reports and
trust inventories are current; and every local and exact-head gate passes.

**Dependencies:** MH-041 is done and supplies replay-complete per-reading
projections and explicit choice state. MH-021 fixes ProblemIR domain and
assumption wire semantics; MH-027 and MH-028 supply independent conformance and
reference scenarios. MH-043 owns obligation decomposition and MH-044 owns
alpha-renaming, commutative normalization, assumption ordering, and context
hashes, so this task must expose sufficient provenance without pre-empting
either boundary.

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
