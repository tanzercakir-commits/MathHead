# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-037 - Red-team every trust-tier transition

**Goal:** close P3 by proving that every supported transition among `none`,
`producer_report`, `solver_verdict`, `checker_attestation`, and
`external_proof_assistant` authority is explicit, byte-bound, independently
checked where promised, and fail-closed under attack. No parser, producer,
adapter, transport, effect owner, stored artifact, successful process, or
human-readable label may silently mint or preserve a stronger tier.

**Scope:** build one canonical transition catalogue and deterministic mutation
runner covering every current authority issuer, preserver, downgrade path, and
forbidden shortcut. Exercise proof-term construction and parsing, arithmetic
evidence, kernel checker results, SAT assignments and RUP certificates,
content-addressed provenance, pinned Lean execution and replay, legacy kernel
and SAT adapters, solver/CAS reports, approximate arithmetic, discovery
producers, dynamic imports, nauty processes, workers, clocks, randomness,
filesystem/process adapters, CLI output, and MCP transport. Mutations must forge
or copy closed objects, alter normal and hidden state, repair outer hashes after
semantic substitution, swap domains, assumptions, statements, contracts,
implementations, configurations, budgets, producer/checker identities, and
provenance roles, truncate or extend certificates and observations, exhaust
each finite limit, substitute executables and dependencies, race or mutate
stored bytes, and force deterministic backend agreement and disagreement.
Every attack has a named positive control, exact expected downgrade or rejection,
and stable diagnostic; the harness itself never grants mathematical authority.
Add a static authority-issuer audit so new call sites, tier strings, transition
edges, entry points, or unclassified effect paths fail the frozen report.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`,
`MH-C-PROOF-TERM-001`, `MH-C-KERNEL-CHECKER-002`,
`MH-C-SAT-REPLAY-001`, `MH-C-PROVENANCE-REPLAY-001`, and
`MH-C-LEAN-VERIFICATION-001`. Before adding the audit implementation, propose,
prescreen, and accept `MH-C-TRUST-TRANSITION-001` with closed transition-attempt,
audit-result, catalogue, and report schemas. It must freeze the tier lattice,
allowed issuers and preservers, required byte and freshness bindings, downgrade
and rejection algebra, mutation classes and coverage accounting, deterministic
ordering and identities, dependency-minimal pure audit API, static source audit,
and finite bounds for artifacts, mutations, diagnostics, nesting, strings,
integers, aggregate bytes, runtime, and memory. A mutation survivor, missing
positive control, unknown transition, incomplete coverage, stale report, or
unclassified authority site must make the contract validator fail.

**Validators:** canonical catalogue/result/report round trips and identical
identities across processes, Python 3.10 through 3.14, and Linux/macOS/Windows;
complete positive-path preservation for each permitted edge; and a 100-percent
kill rate for the normative deterministic mutant catalogue. Cover constructor,
`object.__new__`, field mutation, copying, pickling, subclassing, duplicate and
unknown JSON fields, noncanonical encodings, Unicode/NUL, oversized values,
hash-and-length repair, subject and assumption substitution, producer/checker
aliasing, replay self-attestation, missing/extra/reordered roles, stale bundles,
certificate truncation and trailing data, forged process success, toolchain and
PATH substitution, link/path attacks, timeout/output exhaustion, and backend
disagreement. Prove that approximate, solver, discovery, CLI, MCP, dynamic
import, worker, clock, random, nauty, filesystem, and process surfaces cannot
issue checker or Lean authority. Measure the pure auditor closure with zero
third-party, solver, CAS, discovery, filesystem, process, network, clock,
environment, randomness, dynamic-import, or transport dependencies. Run Ruff,
compileall, project status, core, solver, discovery, slow, docs, release,
clean-wheel smoke, coverage, and exact same-head GitHub gates; freeze a G3 exit
report binding every tested transition, mutation, expected outcome, source,
contract, artifact, and validator identity.

**Done when:** the accepted transition contract and schemas are bound; every
current permitted edge has a passing positive control; every normative mutant
is killed with the contracted rejection or downgrade; no unclassified issuer,
preserver, tier label, or effect-to-authority route remains; forced backend
disagreement, partial evidence, unsupported states, exhaustion, and all forged
or stale material remain non-authoritative; the trust inventory and docs name
every remaining Python, arithmetic, hashing, serialization, solver, runtime,
and Lean primitive precisely; the frozen G3 report is reproducible and current;
all local and exact-head remote gates pass; and the P3 exit condition in
`docs/PLAN.md` is satisfied.

**Dependencies:** MH-030 through MH-036 are done and provide the frozen trust
lattice, immutable proof terms, explicit arithmetic evidence, dependency-minimal
checkers, hardened SAT replay, content-addressed provenance, and pinned external
Lean authority. MH-040 may begin only after this task closes G3 for the supported
kernel fragment.

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
