# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-034 - Harden SAT and UNSAT certificate replay

**Goal:** replace the two divergent legacy RUP/DRUP checkers with one
versioned, dependency-minimal replay boundary that can independently attest a
SAT witness or a supported UNSAT proof while treating every solver, encoder,
transport, legacy result, and unversioned proof stream as untrusted producer
input.

**Scope:** introduce a closed canonical CNF representation, a versioned SAT
assignment certificate, an explicitly RUP-only DRUP proof format with addition
and deletion records, and one immutable replay-result algebra under
`mathhead.kernel.sat`. Bind exact CNF bytes, certificate format and bytes,
complete SHA-256 identities, checker and contract identity, deterministic
resource accounting, verdict, reason, diagnostics, authority, and replay
statistics. Check SAT by evaluating every literal and clause against the exact
assignment. Check UNSAT by bounded reverse unit propagation with deterministic
watched-literal state, exact deletion semantics, incremental line processing,
and empty-clause or final-conflict closure. Name DRUP and DRAT separately:
accept only the contracted RUP fragment, classify genuine RAT steps and unknown
formats as unsupported, and never route them through deletion fallback. Keep
PySAT, DPLL, Ramsey encoding, timers, files, processes, discovery, routing,
MCP, and all producers outside the checker closure. Replace
`mathhead.drat:check_unsat_proof` and
`mathhead.discovery.rup_check:check_drup_proof` with non-authoritative
compatibility adapters to the new checker without silently changing their
documented legacy shapes.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`,
`MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`, and
`MH-C-KERNEL-CHECKER-002`. Before implementation, propose, prescreen, and
accept a new `MH-C-SAT-REPLAY-001` contract and closed result schema fixing the
exact CNF, SAT-witness, DRUP-stream, result, compatibility, authority,
canonicalization, identity, format-version, and implementation bindings. The
contract must distinguish supported DRUP from unsupported DRAT/RAT and bind
finite limits for input and output bytes, variables, clauses, literals, clause
width, proof records, record width, literal magnitude, watch occurrences,
deletions, visits, propagation assignments, and logical steps. No new SAT
checker implementation or legacy authority upgrade may precede acceptance of
those exact bytes.

**Validators:** canonical round trips for CNF, SAT witness, DRUP stream, and
all replay outcomes; exact SAT-clause evaluation; hand-built and solver-emitted
UNSAT proofs; cross-check against exhaustive truth tables on bounded CNFs and
against both legacy checkers on their valid common fragment; deterministic
replay across Python 3.10 through 3.14 and Linux, macOS, and Windows; byte-chunk
boundary equivalence without whole-proof line-list materialization, plus
explicit CRLF rejection at the canonical boundary and adapter normalization;
stable invalid, unsupported, refuted, and exhausted outcomes.
Adversarially cover booleans and non-integers, zero and oversized literals,
empty/missing/duplicate/tautological clauses, repeated and nonexistent
deletions, unknown operations and versions, genuine RAT-only steps, missing or
embedded terminators, huge lines, excessive variables/clauses/width/records,
truncation, reordering, proof-for-wrong-CNF substitution, forged hashes,
noncanonical bytes, mutation, aliasing, `object.__new__`, copying, pickling,
subclassing, producer labels, visit exhaustion, and malformed watch state.
Measure the complete source/import closure; prove zero PySAT, Z3, SymPy,
solver, clock, filesystem, process, network, dynamic-import, and transport
dependencies; run Ruff, compileall, project status, core, solver, discovery,
slow, docs, release, clean-wheel smoke, coverage, and exact same-head GitHub
gates.

**Done when:** one accepted and bound checker independently replays every SAT or
supported DRUP claim that can reach a checker-attested tier; the exact CNF and
certificate bytes are necessary to reproduce that authority; malformed,
unsupported, RAT-only, false, incomplete, mismatched, stale, and over-budget
inputs cannot verify or retain partial authority; both legacy checker entry
points delegate without preserving their former hidden trust; PySAT and all
other producers remain producer-only; the measured closure stays inside the
MH-030 kernel budget; and all local and same-head remote gates pass.

**Dependencies:** MH-030 through MH-033 are done and provide the frozen trust
inventory, immutable proof/evidence boundary, and current dependency-minimal
checker. MH-035 will bind complete run provenance and large persisted replay
bundles, MH-036 will add external Lean authority, and MH-037 will red-team all
remaining tier transitions.

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
