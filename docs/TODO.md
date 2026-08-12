# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-041 - Represent ambiguity as alternative readings

**Goal:** turn every already-declared ProblemIR reading into one stable,
content-addressed interpretation projection with exact machine-readable
differences and an explicit choice state. The boundary consumes only a
canonical accepted MH-040 intake result, never invents an interpretation from
text, never treats a label or human summary as evidence of a structural
difference, and never selects a candidate on the user's behalf.

**Scope:** inventory the accepted ProblemIR reading, difference, ambiguity,
domain, variable, statement, assumption, and goal semantics plus every legacy
discovery reading surface. Implement one dependency-minimal pure analysis API
that revalidates the canonical accepted intake result, identifies the unique
base reading, and projects each candidate's definitions, assumptions, ordered
goals, source spans, and complete transitive entity closure into canonical
bytes and a stable SHA-256 identity. Compute deterministic structural deltas
against the declared base rather than trusting `differences` summaries:
quantifier changes must expose binder order, domains, and bodies; domain
changes must expose exact domain records and affected variables or
expressions; membership, scope, reference, goal-order, definition, assumption,
notation, parse, and other declared differences must retain explicit paths,
before/after identities, affected IDs, and source spans. Preserve unresolved,
resolved, and unambiguous states exactly; unresolved results expose one bounded
required-choice object and no selection, while resolved results retain every
alternative and the caller-declared selected reading. Reject false, missing,
duplicate, cyclic, chained, or misclassified differences instead of repairing
or guessing them. Domain equivalence, assumption normalization,
alpha-renaming, commutative normalization, parsing, solving, proof checking,
and interface presentation remain outside this task.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the accepted
`MH-C-PROBLEM-IR-002` and `MH-C-PROBLEM-INTAKE-001`. Before implementation,
propose, independently prescreen, and accept `MH-C-READING-ANALYSIS-002` plus
closed result and projection schemas. Freeze the exact byte-oriented public
signature, accepted intake
status and identity checks, base/candidate topology, transitive projection
algorithm, structural path and delta algebra, quantifier/domain classifiers,
choice-state rules, canonical serialization and hashing, immutable result
surface, diagnostic taxonomy, non-authority statement, dependency closure,
and finite ceilings for input/output bytes, candidates, entities, deltas,
paths, strings, integers, nesting, graph work, runtime, and memory. The
contract must forbid natural-language inference, candidate synthesis,
semantic equivalence claims, implicit selection, label-based classification,
partial success, producer or solver calls, adapter fallback, and
exception-to-success conversion.

**Validators:** cover unambiguous, unresolved, and resolved fixtures; pure
forall/exists and exists-unique splits; reordered and nested binders; builtin,
finite, interval, modular, collection, product, function, and theory-structure
domain alternatives; combined quantifier/domain/scope differences; alternate
assumption, definition, and ordered-goal sets; and source-backed notation and
parse differences. Independently recompute every projection closure, canonical
byte sequence, SHA-256 identity, before/after fragment digest, affected ID,
path, classification, base link, choice state, and top-level result digest.
Require identical outputs across repeated processes, hash seeds, Python 3.10
through 3.14, and Linux/macOS/Windows. Reject invalid or exhausted intake
results, forged or noncanonical bytes, stale hashes, absent or multiple bases,
unknown candidates, self/cyclic/chained alternatives, duplicate or empty
readings, false summaries, omitted or surplus structural deltas, wrong kinds,
goal-order erasure, dangling paths, irrelevant affected IDs, NUL/non-NFC text,
unknown fields, floats, bool-as-int, subclasses, pickling, mutation, oversized
and deeply nested data, and validation-work exhaustion without returning a
partial identity. Prove the module imports no natural-language or legacy
parser, NLP/LLM, solver, CAS,
discovery producer, checker, filesystem, process, environment, network, clock,
randomness, dynamic-import, CLI, or MCP owner. Add contract, unit,
property/adversarial, independent validator and frozen report, documentation,
trust inventory, clean-wheel, Ruff, compileall, project-status, core, coverage,
and exact-head remote gates.

**Done when:** the new accepted contract and schemas are content-addressed and
bound; every accepted reading has one independently reproducible complete
projection and every alternative has an exact nonempty structural delta from
the unique base; quantifier and domain interpretations are explicit without
semantic normalization; unresolved ambiguity cannot expose a selected
candidate and always carries the exact required choice; resolved ambiguity
retains all candidates and only the predeclared selection; false or incomplete
difference metadata fails closed; no text inference, alternative synthesis,
silent selection, solver call, partial artifact, or mathematical authority is
possible; legacy discovery readings are documented as non-authoritative
adapters; the frozen report and trust inventory are current; and every local
and exact-head gate passes.

**Dependencies:** MH-040 is done and supplies canonical accepted intake result
bytes over the accepted ProblemIR v1 representation. MH-021 fixes the reading
and ambiguity wire semantics, while MH-027 and MH-028 supply independent
conformance and reference scenarios. MH-042 owns domain and assumption
normalization, MH-043 owns proof-obligation decomposition, and MH-044 owns
semantic canonicalization; MH-041 must preserve those boundaries.

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
