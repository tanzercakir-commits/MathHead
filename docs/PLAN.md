# MathHead reconstruction programme

**Plan ID:** `MH-RECONSTRUCTION-V1`  
**Status semantics:** this file defines work and gates; completion exists only
in `docs/PROGRESS.md`.  
**Programme strategy:** preserve proven mathematical assets, rebuild critical
boundaries, and migrate by verified vertical slices.

## 1. North star

MathHead will be a deterministic, extensible mathematical reasoning engine in
which a mathematician can supply a problem, definitions, assumptions, a theory
context, and a resource budget, then receive one of:

- a checked proof with replayable evidence;
- an exact counterexample or witness;
- a bounded experimental result with explicit limits;
- an honest open, unsupported, ambiguous, timeout, or verifier-failure result.

The engine must distinguish solving, checking, experimenting, and conjecturing.
It must never promote evidence from one level into another implicitly.

## 2. Product principles

1. Contract before critical implementation.
2. The checker, not the producer, determines the final trust tier.
3. Assumptions, domain, quantifiers, and resource limits are explicit data.
4. Counterexample-first search precedes expensive proof search when sound.
5. Every accepted result is reproducible from a portable evidence bundle.
6. Experimental discovery is isolated from the stable engine.
7. Unsupported is a successful honest outcome, not a reason to guess.
8. A red required validator prevents completion and release.
9. Breadth follows verified vertical slices; tool count is not a success metric.
10. Local, CI, wheel, CLI, MCP, and notebook surfaces share the same contracts.

## 3. Target architecture

```text
interfaces (Python / CLI / MCP / notebook)
                 |
problem intake -> readings -> ProblemIR + TheoryContext
                 |
planner -> budget supervisor -> theory plugin portfolio
                 |                    |
                 |              untrusted producers
                 |                    |
                 +---- evidence / certificate
                                      |
                         independent kernel/checkers
                                      |
                      EngineResult + replay bundle

discovery lab -> candidates only -> promotion gate -> stable theory plugins
```

The architectural components are:

- `kernel`: proof objects, certificate checking, trust tiers, provenance;
- `engine`: normalization, planning, budgets, orchestration, replay;
- `theories`: independently testable mathematical domain plugins;
- `lab`: conjecture generation, bounded searches, novelty and failure memory;
- `interfaces`: versioned adapters with no mathematical authority.

## 4. Global gates

### G0 - Status integrity

PLAN/TODO/PROGRESS validation, append-only history, contract hashes, and
transactional status transitions pass.

### G1 - Fast development gate

G0, lint, type/API checks, contract verification, dependency-minimal core tests,
and import/wheel smoke tests pass.

### G2 - Full product gate

G1, all supported operating systems/Python versions, optional profiles,
documentation examples, deterministic replay, security, and performance gates
pass.

### G3 - Mathematical trust gate

Every result tier is backed by its promised evidence; independent checkers pass
negative/mutation suites; trust-base claims match actual proof artifacts.

### G4 - Release gate

G2 and G3 pass from a clean tagged source tree; external proof checks required
by the release pass; version, docs, examples, and evidence bundle agree.

## 5. Programme phases and task registry

### P0 - Governance, baseline, and safe adoption

Goal: create one trustworthy control plane without rewriting historical
records or hiding the red baseline.

#### MH-000 - Establish the governed reconstruction baseline

Create the local tracked workspace, preserve the audited source SHA, freeze the
programme/status contracts, create the authoritative PLAN/TODO/PROGRESS set,
and record known limitations. Validators: `status`.

#### MH-001 - Adopt repository-owned project-status automation

Run safe adoption against the exact `docs/` paths; vendor the Python tool,
tests, hook, workflow, and config; leave the hook inactive until validated.
Validators: `status`.

#### MH-002 - Enforce task-aware status transitions

Implement the frozen status contract: task-specific profiles/evidence,
append-only merge-base checks, exact-case paths, partial red evidence, atomic
rollback, and no DONE on missing/skipped/red validators. Validators: `status`
plus negative transition tests.

#### MH-003 - Define one reproducible developer environment

Provide documented clean-install commands for Windows and Linux, pinned core
and optional profiles, UTF-8 process behavior, and a single command dispatcher
used locally and in CI. Validators: `fast` bootstrap subset.

#### MH-004 - Capture the immutable legacy baseline

Record commit, package metadata, test collection, pass/fail categories, CI run
links, benchmark results, known platform failures, and performance hot spots in
a machine-readable baseline artifact. Validators: baseline schema and replay.

#### MH-005 - Index legacy status and architecture records

Map root and discovery records to current phases as historical evidence,
without editing them. Identify obsolete, conflicting, and still-valid claims.
Validators: document-link and uniqueness check.

#### MH-006 - Freeze reconstruction ADRs

Record preserve/rebuild boundaries, package ownership, migration strategy,
compatibility policy, and trust-base terminology. Validators: ADR index check.

**P0 exit:** G0 passes; the baseline remains honestly red at product level;
every next task is traceable to this PLAN.

### P1 - Restore a portable green legacy baseline

Goal: make the current product reproducible before architectural migration.

#### MH-010 - Correct optional dependency test contracts

Separate core and solver extras; skip or select tests by declared capability;
ensure `[dev]` never imports an undeclared optional dependency.

#### MH-011 - Bound finite graph enumeration defaults

Replace the unsafe pure-Python `max_n=7` default with a budget-aware policy;
require a fast backend for larger searches and expose honest truncation.

#### MH-012 - Make all command surfaces encoding-safe

Eliminate Turkish Windows console crashes while preserving Unicode-capable
output; add redirected-console and non-UTF-8 locale tests.

#### MH-013 - Define portable live MCP test semantics

Separate application defects from managed-environment pipe restrictions;
provide deterministic subprocess cleanup and platform capability skips.

#### MH-014 - Split test profiles

Define `core`, `solver`, `discovery`, `docs`, `live-mcp`, `slow`, and `release`
profiles with explicit dependencies and time budgets.

#### MH-015 - Remove version and documentation drift

Generate version/test/tool claims from one source; execute every published
example under its declared profile.

#### MH-016 - Make the full supported CI matrix green

Require all supported OS/Python jobs, solver profile, reproducibility, package
build, docs, and status checks. Do not delete coverage to achieve green.

#### MH-017 - Freeze the legacy compatibility corpus

Capture representative successful, refuted, unsupported, timeout, and error
results for differential migration; normalize only unstable metadata.

**P1 exit:** G2 passes on the legacy architecture and remains green for three
consecutive clean CI runs.

### P2 - Contract-first Python foundation

Goal: define the new engine's semantics before writing its critical code.

#### MH-020 - Implement Python contract artifact tooling

Implement `MH-C-WORKFLOW-001`: strict schemas, proposal/pre-screen/acceptance
separation, canonical hashes, signature binding, and deterministic reports.

#### MH-021 - Accept the ProblemIR contract

Define typed variables, domains, quantifiers, expressions, relations,
definitions, goals, source spans, ambiguity, and canonical serialization.

#### MH-022 - Accept the TheoryContext contract

Define axioms, definitions, imported lemmas, local hypotheses, consistency
state, namespaces, revisions, and dependency hashes.

#### MH-023 - Accept the resource Budget contract

Define wall time, CPU, memory, solver calls, generated objects, proof size,
cancellation, truncation, nesting, and child-budget accounting.

#### MH-024 - Accept the EngineResult contract

Define verdicts, epistemic tiers, readings, assumptions, bounds, witness,
certificate, provenance, budget consumption, diagnostics, and replay identity.

#### MH-025 - Accept Evidence and Certificate contracts

Separate producer artifacts from checker verdicts; define versioning,
canonicalization, trust dependencies, and replay failure behavior.

#### MH-026 - Accept the TheoryPlugin contract

Define capability declaration, supported IR fragment, planning cost, solve,
check, explain, cancellation, deterministic replay, and compatibility rules.

#### MH-027 - Build contract conformance tests

Verify schema rejection, signature drift, hash drift, missing validators,
unknown fields, unsatisfiable requirements, and implementation-side changes.

#### MH-028 - Freeze cross-layer reference fixtures

Create minimal golden tasks covering proof, refutation, ambiguity, unsupported,
timeout, backend disagreement, invalid certificate, and replay.

**P2 exit:** all foundational contracts have explicit owner acceptance; G1
passes without importing legacy solver implementations into the new core.

### P3 - Extract the trusted kernel and evidence model

Goal: make every trust claim match a small, replayable checker boundary.

#### MH-030 - Inventory and minimize the trust base

Classify parser, arithmetic primitives, external solvers, Python runtime,
serialization, hashing, and proof-assistant boundaries.

#### MH-031 - Define immutable proof-term types

Implement constructor-controlled proof objects whose invariants cannot be
created through normal public APIs without validation.

#### MH-032 - Extract dependency-minimal certificate checkers

Check stable certificate formats without importing Z3, SymPy, MCP, or discovery
producers.

#### MH-033 - Internalize derived arithmetic evidence

Ensure residue, CRT, induction, and divisibility derivations appear in proof
artifacts when the tier claims them rather than remaining hidden primitives.

#### MH-034 - Harden SAT/UNSAT certificate replay

Version RUP/DRAT-facing evidence, malformed-proof limits, streaming behavior,
and adversarial rejection.

#### MH-035 - Make provenance content-addressed and replayable

Hash canonical IR, context, plugin version, budget, evidence, and checker
result; reject partial or mismatched bundles.

#### MH-036 - Close the external Lean verification loop

Export in a versioned environment, compile in CI where required, import the
result as external evidence, and distinguish written from checked exports.

#### MH-037 - Red-team every trust-tier transition

Mutation-test checkers, forge proof objects, corrupt hashes, swap assumptions,
truncate certificates, and force backend disagreement.

**P3 exit:** G3 passes for the supported kernel fragment; documentation names
every remaining trusted primitive precisely.

### P4 - Problem and theory analysis layer

Goal: turn a mathematical problem into explicit readings and proof obligations.

#### MH-040 - Define a syntax-neutral intake API

Accept structured Python input first; keep natural-language and LaTeX adapters
outside the trusted parser boundary.

#### MH-041 - Represent ambiguity as alternative readings

Produce stable alternative quantifier/domain interpretations with differences
and required user choices; never choose silently.

#### MH-042 - Normalize domains and assumptions

Make number systems, graph classes, regularity, dimensions, nonzero/domain
restrictions, and finiteness explicit.

#### MH-043 - Build proof-obligation decomposition

Split goals into typed obligations with dependencies, local contexts, status,
and admissible solving strategies.

#### MH-044 - Implement canonical normalization

Normalize alpha-renaming, commutative forms, assumption ordering, and context
hashes without changing mathematical meaning.

#### MH-045 - Produce structured unsupported explanations

Name the exact unsupported construct, nearest owned fragment, and safe next
formalization step.

#### MH-046 - Create persistent problem sessions

Support definitions, lemmas, failed attempts, open obligations, context
revision, and replay without letting stale evidence survive a context change.

**P4 exit:** the reference fixture set reaches stable ProblemIR and obligations
without invoking a solver.

### P5 - Planner, orchestration, and resource control

Goal: select and supervise methods without granting producers epistemic trust.

#### MH-050 - Replace keyword routing with a typed capability registry

Route by owned IR fragment, evidence type, cost model, and context rather than
tool-name keyword similarity.

#### MH-051 - Implement a deterministic planner

Generate ordered candidate strategies with explicit prerequisites, expected
evidence, fallback rules, and no hidden model call.

#### MH-052 - Enforce budgets in isolated workers

Apply wall-time and memory boundaries to SymPy, pure Python enumeration, and
external processes as well as SMT; terminate complete process trees safely.

#### MH-053 - Implement a proof/search portfolio

Run compatible strategies under child budgets, prefer counterexamples, record
inconclusive outcomes, and require checker agreement for promotion.

#### MH-054 - Make every run auditable and replayable

Record plan, chosen plugin, normalized input, budgets, artifacts, checker
results, and deterministic event ordering without secrets or machine paths.

#### MH-055 - Add content-addressed safe caching

Cache only by complete context and contract identities; never reuse evidence
across changed assumptions, checker versions, or trust policies.

#### MH-056 - Define cancellation and refusal semantics

Distinguish user cancellation, budget exhaustion, unsupported input, internal
error, producer failure, and verifier failure.

**P5 exit:** all untrusted producer work is budgeted and isolated; reference
fixtures replay to byte-stable logical reports.

### P6 - Verified theory-plugin vertical slices

Goal: migrate mathematical capability by end-to-end proof, not by module count.

Every slice includes formal input, solver, evidence, independent checker,
explanation, negative/property tests, budget behavior, and interface examples.

#### MH-060 - Modular arithmetic and divisibility slice

Use existing residue/divisibility assets as the first migration oracle and
fully expose derivations in evidence.

#### MH-061 - Polynomial identities and inequalities slice

Handle domains and side conditions explicitly; distinguish symbolic identity,
bounded sampling, and solver proof.

#### MH-062 - Integer equations and elementary number theory slice

Cover gcd conditions, modular inverses, primality/factor evidence, and bounded
Diophantine searches with exact witnesses.

#### MH-063 - Finite combinatorics slice

Migrate permutations, partitions, compositions, recurrences, and bijection
evidence with clear finite-domain contracts.

#### MH-064 - Graph theory slice

Separate labeled/unlabeled and connected/all graph readings; require explicit
generation backends, size bounds, and structural versus exhaustive evidence.

#### MH-065 - Calculus and analysis slice

Represent domains, branches, regularity, constants of integration, singular
points, and symbolic-versus-numeric evidence.

#### MH-066 - Linear algebra slice

Represent scalar domains, dimensions, exact/approximate arithmetic, tolerance,
and independently checkable matrix identities or decompositions.

#### MH-067 - Logic and satisfiability slice

Migrate entailment, consistency, models, modal/bit-vector fragments, unsat
evidence, and explicit decidability limits.

**P6 exit:** at least four diverse theory slices pass G3 and one clean public
API; legacy and new outputs agree wherever their contracts overlap.

### P7 - Mathematician workspace and explanation

Goal: support sustained theory work rather than isolated calculator calls.

#### MH-070 - Build versioned theory workspaces

Manage definitions, assumptions, imported results, namespaces, and context
consistency with immutable revisions.

#### MH-071 - Expose lemma and obligation dependency graphs

Show what is proved, assumed, open, refuted, load-bearing, or invalidated by a
context change.

#### MH-072 - Implement proof-state interaction

Allow users to inspect obligations, choose readings, add lemmas, restrict
domains, and resume bounded searches.

#### MH-073 - Generate evidence-grounded explanations

Explain what was checked, why the tier follows, what remains open, and how a
counterexample violates the statement without inventing proof steps.

#### MH-074 - Add LaTeX import/export adapters

Keep parsing ambiguities visible; produce stable mathematical rendering and
machine-readable artifacts alongside prose.

#### MH-075 - Add a first-class Python/notebook API

Offer typed construction, rich display, replay, and evidence inspection without
requiring MCP or parsing console text.

#### MH-076 - Export portable research bundles

Package problem, context, contracts, plan, evidence, check results, and software
versions for independent replay.

**P7 exit:** a mathematician can conduct and resume a multi-lemma problem
session entirely through stable APIs and reproduce it elsewhere.

### P8 - Isolate and rebuild the discovery laboratory

Goal: preserve exploratory strengths without contaminating stable proof claims.

#### MH-080 - Move discovery behind a laboratory boundary

Remove imports from the trusted kernel into discovery; require explicit lab
profiles and experimental result types.

#### MH-081 - Contract conjecture generation

Record generation grammar, sample domain, novelty basis, ranking inputs, and no
claim stronger than candidate.

#### MH-082 - Standardize counterexample-first campaigns

Use reproducible generators, shrinking, exact witnesses, search coverage, and
budget reports.

#### MH-083 - Make novelty assessment evidence-based

Record catalog/search scope, date, exact matches, unresolved similarity, and
never equate absence in a local catalog with novelty.

#### MH-084 - Preserve negative knowledge and failed strategies

Key failures by normalized goal/context/method/budget and prevent stale failure
reuse after relevant changes.

#### MH-085 - Version experiment manifests

Capture seeds, generators, backends, hardware-independent budgets, artifacts,
and replay commands.

#### MH-086 - Define the lab-to-engine promotion gate

Require an accepted theory contract, stable evidence format, independent
checker, adversarial tests, and G3 before experimental work becomes a supported
engine capability.

**P8 exit:** no laboratory result can serialize as `proved` without crossing
the stable checker and promotion boundary.

### P9 - Stable interfaces and compatibility

Goal: expose one semantic engine consistently through multiple adapters.

#### MH-090 - Freeze the Python API v2

Use typed objects and structured results as the primary compatibility surface.

#### MH-091 - Rebuild the CLI as a serialization adapter

Support UTF-8-safe human output and canonical JSON, stable exit codes, stdin,
files, cancellation, and no logic unique to CLI.

#### MH-092 - Rebuild MCP profiles over the same API

Expose small task-oriented profiles, schema discovery, budgets, sessions, and
evidence retrieval without advertising raw tool count as intelligence.

#### MH-093 - Define schema and compatibility versioning

Separate package, API, contract, evidence, and replay-format versions with
explicit migration behavior.

#### MH-094 - Add privacy-safe observability

Record bounded metrics and reason codes without raw problem text, secrets,
absolute paths, or unstable timestamps in canonical artifacts.

#### MH-095 - Make all documentation examples executable

Bind each example to a profile, budget, expected semantic result, and CI test.

**P9 exit:** Python, CLI, and MCP yield semantically identical results for the
same canonical request and evidence policy.

### P10 - Hardening, security, and performance

Goal: make failure bounded, diagnosable, and non-promoting.

#### MH-100 - Refresh the threat and trust models

Cover parsers, symbolic blowups, solver processes, certificate bombs, plugin
loading, caches, artifacts, and interface inputs.

#### MH-101 - Enforce process and artifact isolation

Constrain CPU, memory, files, environment, child processes, output size, and
temporary artifact lifetime.

#### MH-102 - Expand property and fuzz testing

Fuzz parsers, IR round trips, domain boundaries, cancellation, malformed
evidence, and cross-platform serialization.

#### MH-103 - Add differential and mutation testing

Compare legacy/new solvers and deliberately weaken checkers to prove tests
detect trust regressions.

#### MH-104 - Establish performance budgets and ratchets

Track representative latency, memory, generated objects, certificate size, and
replay cost by profile; gate statistically meaningful regressions.

#### MH-105 - Prove deterministic logical replay

Run repeated and relocated checkouts across supported systems; normalize only
declared operational metadata.

#### MH-106 - Harden dependencies and reproducible builds

Pin compatible profiles, audit licenses/vulnerabilities, build wheels from clean
source, and verify dependency-minimal checkers.

#### MH-107 - Exercise failure injection and recovery

Kill workers, corrupt caches, exhaust budgets, remove optional tools, interrupt
sessions, and verify honest recoverable outcomes.

**P10 exit:** G2 and G3 pass under adversarial and resource-constrained runs.

### P11 - Mathematical validation and release

Goal: prove usefulness and trust with real mathematical workflows.

#### MH-110 - Build a stratified mathematical evaluation corpus

Include routine, adversarial, ambiguous, unsupported, bounded, proof-checking,
and multi-lemma problems with independently reviewed expected outcomes.

#### MH-111 - Define end-to-end mathematician workflows

Evaluate formalization, theory construction, counterexample analysis, proof
repair, certificate replay, and research-bundle exchange.

#### MH-112 - Run an external usability pilot

Observe mathematicians using the engine without developer intervention; record
task success, trust calibration, confusion, and missing theory support.

#### MH-113 - Commission an independent correctness audit

Audit trust claims, kernel/checkers, evidence formats, tier promotion, resource
failure, and a sample of theory plugins.

#### MH-114 - Prepare the first reconstruction release

Produce clean packages, migration guide, supported-scope statement, examples,
evidence bundle, known limits, and rollback instructions.

#### MH-115 - Enable protected release governance

Require status, full product, mathematical trust, reproducible build, and
release evidence checks before merge/tag.

#### MH-116 - Hold the v2 go/no-go review

Release only if G4, the independent audit, and pilot acceptance criteria pass;
otherwise record partial evidence and continue without relabeling maturity.

**P11 exit:** a tagged release is independently installable, replayable, and
honestly scoped for mathematician use.

### P12 - Sustainable extension

Goal: let new theories grow without expanding the trusted core.

#### MH-120 - Publish the theory-plugin SDK

Provide templates, contract schemas, checker patterns, budgets, fixtures, and
promotion rules.

#### MH-121 - Publish contributor and reviewer playbooks

Document contract review, status transitions, mathematical evidence review,
security review, and release responsibilities.

#### MH-122 - Validate a third-party theory plugin

Have an external contributor implement and promote a bounded plugin without
modifying the kernel.

#### MH-123 - Establish the long-term research programme

Prioritize theory coverage and discovery campaigns by mathematical value,
checker feasibility, user demand, and reproducible evidence rather than tool
count.

**P12 exit:** extension is demonstrated without trust-base growth or status
process exceptions.

## 6. Milestones

| Milestone | Required phases | Meaning |
| --- | --- | --- |
| M0 Governed baseline | P0 | One honest control plane and frozen baseline |
| M1 Green legacy | P1 | Existing product is portable and reproducible |
| M2 Contracted core | P2-P3 | New semantics and trusted evidence boundary exist |
| M3 Reasoning vertical | P4-P6 first slice | One full problem-to-certificate path works |
| M4 Multi-theory alpha | P6-P9 | Several verified theories and stable interfaces |
| M5 Mathematician preview | P7-P10 | Sessions, explanation, isolation, and replay work |
| M6 Reconstruction release | P11 | Audited, piloted, reproducible public release |

## 7. Programme success measures

- Required CI pass rate: 100%, never averaged across red jobs.
- Certificate replay pass rate for claimed verified tiers: 100%.
- Unsupported/ambiguous/timeout outcomes are calibrated and never promoted.
- Every supported theory has independent negative and mutation coverage.
- Every published example is executable and version-bound.
- The minimal checker profile does not import producer solvers.
- The default request completes or terminates within its declared budget.
- A clean source checkout can reproduce release evidence.
- External mathematicians can distinguish assumptions, evidence, and limits
  without reading implementation code.

## 8. Explicit non-goals for this programme

- Promising solutions to arbitrary famous open problems.
- Treating natural-language generation as proof.
- Treating bounded search as a universal theorem.
- Growing MCP tool count before semantic integration.
- Rewriting proven domain assets merely for stylistic uniformity.
- Preserving backward compatibility with incorrect or overstated trust claims.

