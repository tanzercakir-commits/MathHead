# Dependency-minimal kernel checker v1

> Historical format: MH-033 superseded this contract with
> `MH-C-KERNEL-CHECKER-002`. Current verified results use the explicit
> arithmetic-evidence v2 format documented in `KERNEL_CHECKER_V2.md`; v1 wire
> bytes are intentionally refused rather than upgraded.

MH-032 introduces the only boundary that can issue the immutable
`checker_attestation` used by the new kernel model. It is governed by accepted
contract `MH-C-KERNEL-CHECKER-001` at SHA-256
`78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7`.
The implementation is `mathhead.kernel.checkers`; the closed result schema is
`docs/contracts/schemas/kernel-checker-result-v1.schema.json`.

## Authority boundary

`check_proof_term(term)` accepts only the exact immutable MH-031 algebra. It
revalidates the complete graph, reruns the mathematical rule, accounts for
deterministic work, and returns an immutable `CheckerResult`. Only a
`verified` result has authority `checker_attestation` and a typed statement.
`invalid` and `exhausted` results have authority `none` and no statement.

Producer completion, proof-term construction, parsing, hashing, adapters,
legacy `Theorem` objects, solver verdicts, UI, MCP, and orchestration never
mint this attestation. Python deliberately leaves `object.__new__` reachable;
therefore result serialization and validation independently recompute the
entire decision. A forged or mutated object cannot cross that boundary as a
valid canonical result.

## Exact supported fragment

The checker implements four closed rules with integers and `Fraction` only:

- residue exhaustion evaluates an integer polynomial at every residue;
- CRT recursively verifies all premises, requires one polynomial and
  pairwise-coprime moduli, then derives the exact modulus product;
- finite-sum induction checks the base case and the exact polynomial identity
  `g(n) - g(n-1) - f(n) = 0`;
- polynomial identity compares normalized rational coefficient vectors.

Dispatch is by exact proof-term type. False, malformed, unsupported, forged,
or exhausted inputs return stable non-promoting reasons. The v1 reason codes
are `CHECKER_VALID`, `TERM_INVALID`, `UNSUPPORTED_TERM`,
`RESIDUE_COUNTEREXAMPLE`, `CRT_PREMISE_INVALID`,
`CRT_POLYNOMIAL_MISMATCH`, `CRT_NON_COPRIME`, `SUM_BASE_MISMATCH`,
`SUM_STEP_MISMATCH`, `POLYNOMIAL_MISMATCH`, and `BUDGET_EXHAUSTED`.

## Canonical result and replay

`checker_result_to_bytes` emits closed sorted compact ASCII JSON with one
trailing newline. It embeds the exact canonical proof-term bytes as lowercase
hex and binds the proof-term contract, checker contract, checker identity,
term identity, result identity, verdict, statement, diagnostic, and work
count with full SHA-256 values. `parse_checker_result` accepts exact `bytes`
only, rejects duplicate or unknown fields and floats, checks canonical bytes,
then reruns the checker and requires an identical result.

The fixed ceilings are 2,200,000 result-input bytes, 1,000,000 checker steps,
and 16,384 bits for derived integers, in addition to all MH-031 graph,
coefficient, part, input, and scalar limits.

## Dependency and legacy boundaries

The measured checker closure is five internal modules and seven standard
library roots, below the frozen limits of twelve and nine. It has no
third-party, discovery, solver, CAS, floating-point, dynamic-import,
filesystem, process, network, environment, clock, randomness, UI, or MCP
dependency.

`mathhead.legacy_kernel_adapter.adapt_legacy_proof_term` is an explicitly
non-authoritative migration path. It converts the four legacy proof-term
shapes through MH-031 factories, but rejects legacy `Theorem` values because
they are results rather than replayable evidence. The adapter never imports
the checker. Its output must still pass `check_proof_term` before it has any
authority.

## Validation

```bash
python tools/validate_kernel_checker.py
python -m unittest discover -s tests/kernel_checker -v
python tools/contract_artifacts.py verify \
  --contract MH-C-KERNEL-CHECKER-001 --run-validators --require-bound
python tools/validate_trust_base.py
python tools/project_status.py check
```
