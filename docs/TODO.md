# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-036 - Close the external Lean verification loop

**Goal:** replace the legacy written-only Lean export with one versioned,
content-addressed external proof-assistant boundary. Exporting source must remain
non-authoritative; only a successful run of the exact pinned Lean toolchain over
the exact generated theorem bytes may issue `external_proof_assistant`
authority, and that authority must survive independent provenance replay.

**Scope:** define a deterministic exporter for the supported arithmetic
proof-term fragment, a closed execution request and result algebra, a bounded
effect adapter for invoking Lean without a shell, and a dependency-minimal pure
validator that binds the original proof term and checker result to the theorem
statement, generated source, project files, toolchain lock and binary identity,
command, sanitized environment policy, exit status, bounded stdout and stderr,
and output artifacts. Generate stable namespaces and identifiers; reject
unsupported terms rather than inserting axioms or opaque assumptions; forbid
`sorry`, `admit`, `axiom`, `unsafe`, native-oracle shortcuts, undeclared imports,
and unpinned dependencies; separate `export_written`, `check_unavailable`,
`check_failed`, `check_exhausted`, and `externally_verified` outcomes; persist
all inputs and observations through the MH-035 run-bundle model; and turn the
legacy discovery exporter into a clearly non-authoritative compatibility
adapter. The runner owns process and filesystem effects but never decides
authority; the pure validator must recompute every identity and apply the
contracted authority lattice from exact bytes alone.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`,
`MH-C-PROOF-TERM-001`, `MH-C-KERNEL-CHECKER-002`, and
`MH-C-PROVENANCE-REPLAY-001`. Before implementation, propose, prescreen, and
accept one new MH-C-LEAN-VERIFICATION-001 contract with closed request and
result schemas. It must freeze the exporter, runner, and pure-validator APIs;
the supported proof fragment and exact statement correspondence; canonical
source and project bytes; toolchain and dependency pinning; process,
environment, filesystem, and artifact rules; authority and status/reason
algebras; provenance roles and cross-links; and finite limits for source,
artifacts, output, paths, identifiers, theorem count, integers, elaboration
heartbeats, memory, and wall time. No new authoritative Lean runtime path may
precede acceptance of those exact contract bytes.

**Validators:** canonical export and result round trips across processes,
Python 3.10 through 3.14, and Linux/macOS/Windows; byte-identical source for
residue, CRT, finite-sum induction, and polynomial-identity proof terms; one
pinned Linux CI job that installs from the committed lock, records exact Lean
and dependency identities, compiles every supported positive fixture, and
imports the successful result through provenance replay; deterministic
unavailable behavior on platforms without Lean; and clean-wheel import and
export smoke tests. Adversarially cover forged success, export-only promotion,
statement substitution, changed assumptions or domains, wrong proof/checker
identity, toolchain or lock drift, PATH substitution, symlinks and traversal,
shell injection, hostile names and Unicode, undeclared imports, forbidden Lean
constructs, stale or truncated logs, exit-code mismatch, missing or extra
artifacts, tampered object hashes, timeout and output exhaustion, corrupted
`.olean` data, copied/mutated/pickled/subclassed results, and replay under a
different provenance bundle. Prove that the pure validator has no filesystem,
process, network, clock, environment, dynamic-import, solver, CAS, discovery,
or Lean dependency. Run Ruff, compileall, project status, core, solver,
discovery, slow, docs, release, clean-wheel smoke, coverage, and exact
same-head GitHub gates.

**Done when:** the repository owns a reproducible pinned Lean project and every
supported positive fixture is compiled by Lean in CI; exact successful process
evidence can be independently validated and replayed as
`external_proof_assistant` authority; written, unavailable, failed, exhausted,
unsupported, stale, forged, or mismatched exports deterministically remain
non-authoritative; generated source contains no trust-widening escape hatch;
the toolchain, theorem, Python checker, and provenance identities are all bound;
and every local and same-head remote gate passes.

**Dependencies:** MH-030 through MH-035 are done and supply the authority
lattice, immutable proof terms, arithmetic evidence, dependency-minimal
checkers, SAT replay, and content-addressed provenance. MH-037 will red-team the
completed Lean boundary together with every remaining trust-tier transition.

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
