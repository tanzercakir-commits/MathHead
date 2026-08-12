# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-044 - Implement canonical normalization

**Goal:** turn every accepted MH-043 per-reading proof-obligation graph into a
bounded, content-addressed canonical normalization artifact whose semantic
identities are invariant under capture-safe alpha-renaming, catalogue-authorized
commutative permutations, and declared assumption ordering, while retaining an
exact trace to every original declaration, context, obligation, edge, source
span, choice, witness placeholder, status, and strategy record. Canonical form
must be a representation identity only; it must never become a proof,
equivalence oracle, simplifier verdict, or permission to merge readings.

**Scope:** consume only canonical successful MH-043 result bytes and replay-
validate the complete accepted MH-040 through MH-043 chain before use. Normalize
each reading and root goal independently; unresolved alternatives remain
separate and no canonical hash may compare, select, merge, or transfer facts
between readings. Define a closed normal-form algebra and trace model for
reachable domains, variables, expressions, relations, logical and quantified
statements, definitions, assumptions, local contexts, obligation fragments,
choices, witness placeholders, and graph references. Alpha-normalize only bound
variables and definition parameters by lexical owner, depth, and declared
position; preserve free-variable identity, binder order, domain, scope,
shadowing, and capture boundaries. Reorder operands only for exact rule-
catalogue entries whose operator, arity, domain, and theory preconditions are
all satisfied; preserve multiplicity, and do not infer associativity,
idempotence, identity, inverse, distributivity, or cancellation from
commutativity. Canonically order inherited assumptions and local hypotheses by
role and normalized content while preserving duplicates, origins, dependency
closure, source spans, and a reversible occurrence map. Emit original-to-
canonical and canonical-to-original occurrence traces, rule applications,
unsupported records, normalized local-context identities, normalized
obligation-fragment identities, per-graph identities, and one top-level result
identity. Preserve graph topology, root and goal ownership, child and
prerequisite edges, statuses, choices, witnesses, and strategy metadata exactly;
this task may add comparison keys but cannot solve, discharge, rank, or alter an
obligation.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002`, `MH-C-PROBLEM-INTAKE-001`,
`MH-C-READING-ANALYSIS-002`,
`MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001`, and
`MH-C-PROOF-OBLIGATION-DECOMPOSITION-001` identities. Before implementation,
propose, independently prescreen, and accept a new versioned canonical-
normalization contract plus closed normal-form, occurrence-trace, normalized-
context, normalized-obligation, rule-catalogue, and top-level result schemas.
Freeze the exact byte-oriented public signature; accepted upstream
status and identity checks; alpha-equivalence namespace and capture rules;
operator/property authority and exact commutative allowlist; operand comparison
keys and stable tie policy; assumption-role, multiplicity, origin, dependency,
and ordering policy; graph and reading separation; trace completeness and
reversibility; supported and unchanged/opaque taxonomy; canonical serialization
and SHA-256 identities; immutable result surface; non-authority statement; and
finite ceilings for bytes, readings, goals, graphs, obligations, contexts,
domains, variables, binders, definitions, assumptions, facts, expressions,
relations, statements, operands, occurrences, traces, rule applications,
dependencies, source spans, strings, integers, nesting, normalization work,
runtime, and memory. The contract must forbid free-variable renaming,
capture, binder reordering, undeclared algebraic laws, heuristic operator-name
interpretation, duplicate collapse, provenance loss, source rewriting,
cross-reading canonical equivalence, status or edge changes, solver or checker
calls, producer fallback, partial identities, and exception-to-success behavior.

**Validators:** cover nested and shadowed `forall`, `exists`, and
`exists_unique` binders; definition parameters; free versus bound variables;
capture hazards; vacuous and repeated binders; logical `and`, `or`, and exact
symmetric relations; every catalogue-approved expression operator and domain
guard; noncommutative application, implication, ordered relations, tuple,
conditional, function argument, quantifier, goal, child, prerequisite, and
witness order; duplicate operands; equal comparison keys; all three assumption
roles; repeated equal assumptions with distinct origins; inherited local
hypotheses; multiple contexts and goals; every domain kind; unsupported and
opaque fragments; shared substructure; and unresolved and resolved readings.
Use metamorphic pairs that differ only by bound names, approved commutative
permutations, or assumption order and require equal semantic identities, while
single changes to free variables, binder position, multiplicity, role, domain,
noncommutative order, source-backed structure, graph edges, status, choice,
witness, strategy, or reading require a different relevant identity. An
independent validator must recompute every lexical namespace, normalized node,
comparison key, rule match, operand order, occurrence trace, assumption order,
context closure, graph binding, unsupported record, digest, and top-level result
without calling production helpers. Require byte-identical outputs across
repeated processes, hash seeds, Python 3.10 through 3.14, and
Linux/macOS/Windows. Reject invalid or exhausted upstream results,
noncanonical bytes, stale hashes, escaped or captured binders, false rule
applications, unauthorized reorderings, erased duplicates, incomplete or
ambiguous traces, cross-reading references, forged invariant hashes, reordered
semantic inputs, NUL/non-NFC text, unknown fields, floats, bool-as-int,
subclasses, pickling, mutation, oversized/deep values, and normalization-work
exhaustion without returning partial forms. Prove the production module imports
no natural-language or legacy parser, NLP/LLM, solver, CAS, discovery or proof
producer, planner, checker, filesystem, process, environment, network, clock,
randomness, dynamic import, CLI, or MCP owner. Add contract, schema, unit,
metamorphic/property and adversarial tests, an independent validator and frozen
report, documentation, trust inventory, clean-wheel, Ruff, compileall,
project-status, core, coverage, and exact-head remote gates.

**Done when:** the accepted contract, schemas, and frozen normalization-rule
catalogue are content-addressed and bound; every successful reading and goal has
one independently reproducible normalized graph view; alpha-equivalent bound
forms, authorized commutative permutations, and assumption-order variants have
the same contracted semantic identities; all non-equivalent or unauthorized
changes remain distinguishable; every original occurrence has a complete
reversible trace with multiplicity, role, origin, dependency, and source
provenance intact; graph topology and workflow metadata are unchanged;
unsupported structures remain exact and visible; no reading selection,
semantic simplification, equality inference, satisfiability verdict, witness,
strategy success, proof, refutation, checker result, partial artifact, or
mathematical authority is possible; frozen reports and trust inventories are
current; and every local and exact-head gate passes.

**Dependencies:** MH-043 is done and supplies complete per-reading obligation
graphs, local contexts, choices, witness duties, structural statuses, strategy
metadata, and exact upstream replay bytes. MH-021 fixes ordered ProblemIR and
scope semantics; MH-022 fixes theory-context vocabulary; MH-023 fixes finite
budgets; MH-027 and MH-028 supply independent conformance and reference
scenarios. MH-045 owns human-facing unsupported explanations; MH-046 owns
persistent session revision and replay; MH-047 through MH-050 own capability
discovery, planning, execution, aggregation, and escalation, so this task must
provide stable comparison identities without pre-empting those decisions.

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
