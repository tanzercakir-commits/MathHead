# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-040 - Define a syntax-neutral intake API

**Goal:** introduce the first target-architecture problem-analysis boundary:
one deterministic, dependency-minimal structured Python API that converts
explicit mathematical declarations into canonical ProblemIR bytes without
parsing prose, LaTeX, SymPy expressions, solver objects, Python source, or
interface-specific payloads. Successful intake proves representation validity
only; it never proves, solves, normalizes semantically, selects an ambiguous
reading, or grants mathematical authority.

**Scope:** inventory the accepted ProblemIR v1 schema and every legacy parser,
natural-language recognizer, MCP/CLI translation path, and fixture producer,
then freeze the supported structured construction algebra. Provide immutable
typed declarations or an equally closed public builder surface for source
identities and spans, domains, variables, expressions, relations, statements,
definitions, assumptions, goals, readings, ambiguity, and namespaced
extensions. Resolve symbolic local references into stable explicit IDs,
preserve every order that ProblemIR declares semantic, sort only registry and
set-valued data that the accepted contract permits, and return canonical bytes,
their SHA-256 identity, and bounded structured diagnostics. Keep input objects
distinct from ProblemIR wire objects so caller mutation, object identity,
mapping order, dataclass internals, repr output, hash randomization, locale,
platform, or process state cannot affect the result. Natural-language, LaTeX,
SymPy, AST/eval, CLI, MCP, files, network, solver, clock, randomness, dynamic
imports, and discovery code remain outside this boundary; existing legacy
parsers stay available only as explicitly non-authoritative adapters and are
not silently routed through the new API.

**Contracts:** follow `MH-C-WORKFLOW-001` and bind the already accepted
`MH-C-PROBLEM-IR-002`. Before implementation, propose, independently
prescreen, and accept a new critical problem-intake function contract plus
closed schemas for the input envelope and intake result. Freeze the public
signature, accepted input type algebra, reference and ID rules, canonical
construction algorithm, diagnostic taxonomy, success/failure algebra,
ProblemIR schema/contract hashes, dependency closure, non-authority statement,
and finite limits for bytes, entities, collection sizes, strings, integers,
numeric literals, nesting, validation work, runtime, and memory. The contract
must forbid partial ProblemIR success, implicit defaults that alter
mathematical meaning, unregistered fields, unknown object types, adapter
fallback, and any exception-to-success conversion.

**Validators:** round-trip every supported structured declaration into bytes
accepted independently by the existing ProblemIR validator; require identical
bytes and identities across repeated processes, Python hash seeds, Python 3.10
through 3.14, and Linux/macOS/Windows. Cover all ProblemIR tagged variants plus
the eight frozen foundation scenarios, multiple ordered goals and binders,
unresolved and resolved readings, source-span identities, lexical scope, and
extensions. Reject missing, duplicate, dangling, aliased, cyclic, out-of-scope,
ill-typed, noncanonical, NUL/non-NFC, bool-as-int, float, oversized, deeply
nested, mutated, forged, subclassed, pickled, and custom mapping/sequence
inputs with stable paths and reason codes. Prove caller objects are not retained
or mutated, failed intake returns no canonical ProblemIR identity, the module
imports no producer, solver, CAS, discovery, interface, filesystem, process,
environment, network, clock, randomness, or dynamic-import owner, and all
legacy text/LaTeX/AST/SymPy payloads are refused rather than guessed. Add
contract, unit, property/adversarial, independent validator, documentation,
clean-wheel, Ruff, compileall, project-status, core, coverage, and exact-head
remote gates.

**Done when:** the new accepted contract and schemas are content-addressed and
bound to the implementation; every supported structured Python construct
produces independently validated canonical ProblemIR bytes or one complete
bounded failure result; cross-process and cross-platform identities are stable;
no implicit ambiguity choice, semantic normalization, solver call, adapter
fallback, partial artifact, caller mutation, or mathematical authority is
possible; legacy natural-language and LaTeX routes are documented outside the
trusted boundary; the frozen intake report and trust inventory are current;
and all required local and exact-head gates pass.

**Dependencies:** MH-020 and MH-021 provide the accepted contract workflow and
ProblemIR v1 wire semantics; MH-027 and MH-028 provide conformance and reference
fixtures; MH-030 through MH-037 provide the closed trust and provenance model.
MH-041 consumes this stable intake result to represent alternative readings,
while MH-042 through MH-044 own domain/assumption normalization and semantic
canonicalization that this task must not perform.

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
