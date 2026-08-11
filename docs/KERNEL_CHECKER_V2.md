# Explicit-arithmetic kernel checker v2

MH-033 makes every successful arithmetic derivation in the kernel result
observable and replayable. The current boundary is governed by accepted
`MH-C-KERNEL-CHECKER-002` at SHA-256
`1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e`.
It supersedes the immutable v1 contract without changing the Python entry
point `mathhead.kernel.checkers.check_proof_term`. The current closed wire
schema is `docs/contracts/schemas/kernel-checker-result-v2.schema.json`.

## What changed from v1

The v1 checker independently recomputed the right mathematical decisions, but
its successful result retained only the proof term, derived statement, and work
count. Residue evaluations, CRT coprimality calculations, induction differences,
and coefficient comparisons existed only transiently inside the checker.

A v2 `verified` result additionally contains exactly one immutable arithmetic
evidence object and its full SHA-256 identity. The checker derives this object,
serializes it inside the result, and derives it again whenever the result is
validated or parsed. Removing, changing, reordering, truncating, substituting,
or relabeling any evidence step makes the result fail closed. Invalid and
exhausted results contain no statement, evidence, evidence identity, or
authority.

The v1 contract, schema, and documentation remain historical evidence. V1 wire
bytes are explicitly rejected as an unsupported schema; there is no implicit
upgrade because they do not contain the arithmetic record required by v2.

## Evidence algebra

The four exact proof rules map one-to-one onto four evidence variants:

- `ResidueEvidence` contains one `ResidueEvaluation` for every class from zero
  through `modulus - 1`. Each row records the exact integer polynomial value
  and the exact quotient and zero remainder returned by positive-modulus
  `divmod`.
- `CRTEvidence` recursively contains every divisibility premise's evidence,
  one deterministic extended-Euclidean `BezoutWitness` for every premise pair,
  and one `ProductStep` for every factor in the final modulus product.
- `SumInductionEvidence` records both evaluations at one, the coefficients of
  `g(n-1)`, the coefficients of `g(n)-g(n-1)`, and the normalized zero
  coefficients of `g(n)-g(n-1)-f(n)`.
- `PolynomialIdentityEvidence` records both normalized rational polynomials
  and the normalized zero coefficients of their difference.

These classes have closed public constructors, frozen slots, immutable tuple
ownership, blocked subclassing and pickling, and identity-preserving copying.
They have no authority field and are not general producer `Evidence` envelopes.
Only a complete recomputed `CheckerResult` can assign `checker_attestation`.

## Canonical identity and budgets

`checker_result_to_bytes` emits sorted compact ASCII JSON with one trailing
newline. It binds the v2 schema, checker and proof-term contracts, checker
implementation identity, canonical proof-term bytes, statement, complete
evidence object, evidence SHA-256, verdict, diagnostic, work count, and result
SHA-256. `parse_checker_result` accepts exact bytes only, rejects duplicate and
unknown fields and floats, refuses v1, then independently recreates and compares
the entire result byte-for-byte.

The v2 ceilings are 64 MiB for a result envelope, 1,000,000 deterministic
logical steps, 100,000 retained evidence items and residue classes, and 16,384
bits for every derived integer or rational numerator or denominator. All MH-031
depth, node, coefficient, CRT-part, input-byte, and input-integer limits still
apply. Work or retention that cannot fit is classified `BUDGET_EXHAUSTED` and
leaves no partial evidence.

## Trust boundary

The measured checker closure is six internal modules and seven standard-library
roots, below the frozen maxima of twelve and nine. The new internal module is
`mathhead.kernel.arithmetic_evidence`. The closure still has no third-party,
solver, CAS, discovery-producer, floating-point, dynamic-import, filesystem,
process, network, environment, clock, randomness, UI, or MCP dependency.

The remaining trusted arithmetic primitives are now named precisely: CPython
exact integer multiply, add, floor division, remainder, and immutable
containers; `Fraction`; `math.comb`; the checker-owned deterministic extended
Euclidean loop; canonical JSON; and SHA-256. Their complete observations appear
in evidence whenever the verified tier claims a derivation. Approximate and
transcendental legacy math remains non-authoritative and outside this closure.

## Validation

```bash
python tools/validate_kernel_checker.py
python -m unittest discover -s tests/kernel_checker -v
python tools/contract_artifacts.py verify \
  --contract MH-C-KERNEL-CHECKER-002 --run-validators --require-bound
python tools/validate_trust_base.py
python tools/project_status.py check
```
