# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-032 - Extract dependency-minimal certificate checkers

**Goal:** make mathematical authority a property that only a small,
independent checker boundary can issue. The checker must consume the immutable
MH-031 proof-term algebra, revalidate its complete graph, evaluate the supported
mathematics exactly, and return an immutable attestation without trusting any
producer, solver, interface, transport, or orchestration code.

**Scope:** define and implement a closed checker request and result model for
the residue, CRT, finite-sum induction, and polynomial-identity rules; bind the
exact statement, proof term, governing contract identities, checker
implementation identity, deterministic resource accounting, verdict, and
classified diagnostics; evaluate all arithmetic with integers and
`Fraction`; make rule dispatch exhaustive and fail closed; prevent public
construction, copying, pickling, subclassing, `object.__new__` forgery, stale
identity, and legacy `Theorem` values from crossing the authority boundary;
and provide explicit non-authoritative adapters for legacy inputs. The checker
closure must remain within twelve internal modules and nine approved standard
library roots, with no third-party, dynamic-import, clock, filesystem, process,
network, randomness, solver, CAS, UI, MCP, or discovery-producer dependency.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`,
`MH-C-PROOF-TERM-001`, `MH-C-EVIDENCE-001`, and `MH-C-CERTIFICATE-001`.
Before implementation, propose, prescreen, and accept a new canonical
`MH-C-KERNEL-CHECKER-001` contract that fixes the supported statement
fragment, checker request/result ABI, exact verdict and error taxonomy,
attestation construction authority, resource budgets, implementation binding,
legacy migration behavior, and complete dependency boundary. No checker code
may precede acceptance of the exact contract bytes.

**Validators:** closed Draft 2020-12 schemas and repository-owned validators;
positive evaluation for all four proof rules; exact rational and integer
boundary cases; canonical request/result round trips; independent statement
recomputation; and adversarial rejection for false residues, inconsistent or
non-coprime CRT parts, wrong induction bases or steps, unequal or malformed
polynomials, hidden variables, forged and uninitialized terms/results, cycles,
excess depth/nodes/coefficients/parts/integer bits, duplicate or unknown JSON
fields, stale hashes, contract or implementation drift, producer/checker
identity aliasing, legacy theorem promotion, and unsupported rules. Add source
closure and denied-import tests, deterministic replay, legacy differential
tests, exact implementation binding, Ruff, project status, core, docs, release,
clean-install, and same-head GitHub gates.

**Done when:** only the dependency-minimal checker can mint an immutable
checker attestation; every accepted attestation deterministically binds and
replays the exact statement and canonical MH-031 term; malformed, false,
unsupported, exhausted, forged, stale, and mismatched inputs produce stable
non-promoting failures; the legacy forgeable theorem representation cannot
cross the new boundary; the actual import closure meets the MH-030 budget; and
all local and same-head remote gates pass.

**Dependencies:** MH-030 and MH-031 are done and supply the frozen trust budget
and structural proof terms. MH-033 will move currently hidden derived
arithmetic into evidence; MH-034 will harden SAT proof replay; MH-035 will bind
complete provenance; MH-036 will add external Lean authority; and MH-037 will
red-team all remaining trust-tier transitions.

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
