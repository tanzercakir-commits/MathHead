# MathHead reconstruction TODO

This is the sole live queue for `MH-RECONSTRUCTION-V1`. Completion authority is
`docs/PROGRESS.md`; stable definitions and gates are in `docs/PLAN.md`.

## Now

### MH-033 - Internalize derived arithmetic evidence

**Goal:** ensure every arithmetic derivation named by a verified kernel tier is
present in the canonical proof artifact and independently replayed, rather than
remaining an unobservable primitive inside the checker. Preserve MH-032's small,
effect-free authority boundary while making its residue, CRT, induction,
polynomial-equality, and divisibility reasoning inspectable and mutation-safe.

**Scope:** supersede the v1 checker result with a v2 result under the unchanged
`check_proof_term(term: object) -> CheckerResult` entry point. Add a closed,
immutable arithmetic-evidence algebra: residue-class evaluations bind every
checked class, exact value, quotient, and zero remainder; CRT evidence binds
the recursively verified premises, pairwise extended-GCD/Bezout witnesses, and
cumulative modulus-product derivation; finite-sum induction evidence binds both
base evaluations plus the shifted closed-form and exact zero step-polynomial
coefficients; polynomial identity evidence binds normalized operands and their
exact zero difference. A verified result must contain exactly the evidence
variant required by its proof term, a canonical evidence identity, and no
unrecorded successful arithmetic decision. Invalid or exhausted results retain
no evidence authority. Keep all values exact, constructor-controlled, deeply
immutable, canonically serialized, deterministically budgeted, and replayed
without producer, solver, CAS, transport, filesystem, clock, process, or network
dependencies. Retain the MH-032 API as the compatibility surface, but make v1
serialized results historical and non-current after explicit supersession.

**Contracts:** `MH-C-WORKFLOW-001`, `MH-C-TRUST-BASE-001`,
`MH-C-PROOF-TERM-001`, `MH-C-EVIDENCE-001`, `MH-C-CERTIFICATE-001`, and
`MH-C-KERNEL-CHECKER-001`. Before implementation, propose, prescreen, and accept
`MH-C-KERNEL-CHECKER-002` with the exact v2 evidence algebra, closed result
schema, compatibility/refusal behavior, implementation binding, canonical
identity, evidence-size and arithmetic budgets, and supersession link. No v2
checker or arithmetic-evidence implementation may precede acceptance of those
exact bytes.

**Validators:** closed Draft 2020-12 result/evidence schema; exact evidence and
result round trips; all four verified-rule variants; independent recomputation
of every residue row, quotient, remainder, extended-GCD coefficient, Bezout
identity, cumulative product, base value, shift coefficient, difference
coefficient, and normalized polynomial coefficient; equivalence with the
MH-032 mathematical verdict on the retained supported fragment; stable refusal
when evidence cardinality, bytes, steps, depth, nodes, coefficient count, CRT
parts, or integer size exceed the v2 budget; and adversarial rejection for
missing, reordered, duplicated, truncated, forged, stale, mismatched, aliased,
wrong-variant, or unknown evidence. Include `object.__new__`, mutation, copying,
pickling, subclass, duplicate JSON key, unknown field, noncanonical bytes,
contract/schema/implementation drift, legacy-object, producer-assertion, and
hidden-success-path attacks. Re-measure the complete source/import closure and
run Ruff, compileall, project status, core, docs, release, clean-wheel smoke,
coverage, and exact same-head GitHub gates.

**Done when:** every `checker_attestation` emitted by the current checker result
format contains one complete canonical arithmetic-evidence object whose exact
replay is necessary and sufficient for that verified result; changing or
omitting any claimed arithmetic step fails closed; no successful residue, CRT,
induction, divisibility, or polynomial comparison remains only in transient
checker state; v1 results are explicitly refused as superseded rather than
silently upgraded; the measured checker closure remains inside the MH-030
budget; and all local and same-head remote gates pass.

**Dependencies:** MH-030 through MH-032 are done and provide the frozen trust
inventory, immutable proof terms, and dependency-minimal checker. MH-034 will
add adversarial SAT/UNSAT replay, MH-035 will bind whole-run provenance, MH-036
will add external Lean authority, and MH-037 will red-team every remaining
trust-tier transition.

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
