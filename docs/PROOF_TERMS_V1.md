# Immutable proof terms v1

MH-031 introduces a dependency-minimal proof representation under accepted
contract `MH-C-PROOF-TERM-001` at SHA-256
`20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac`.
The module is `mathhead.kernel.proof_terms`; its normative wire schema is
`docs/contracts/schemas/proof-term-v1.schema.json`.

## Authority boundary

A proof term is candidate structure, never a theorem. Factory construction,
canonical parsing, hashing, equality, copying, and serialization do not grant
mathematical authority. MH-032 will independently evaluate these values and is
the only planned boundary that may issue checker attestation.

The legacy `mathhead.discovery.kernel.Theorem` remains visible and forgeable
through deliberate `object.__new__` use. MH-031 does not relabel it or silently
claim that it has been sealed; replacing the checker-issued result belongs to
MH-032.

## Closed algebra

The v1 algebra has exactly four final frozen value types:

- `ResidueTerm`: a positive modulus and canonical integer polynomial;
- `CRTTerm`: one or more proof-term children in canonical byte order;
- `SumInductionTerm`: exact rational summand and closed-form polynomials;
- `PolynomialIdentityTerm`: exact rational left and right polynomials.

Public construction uses `residue`, `crt`, `sum_induction`, and
`polynomial_identity`. Class constructors are closed. Caller collections are
copied into tuples, rational values are normalized with `Fraction`, polynomial
trailing zeroes are removed, subclasses and pickle reduction are blocked, and
copy or deepcopy safely returns the same immutable value.

Python cannot prevent deliberate `object.__new__` and `object.__setattr__`
bypasses. Therefore every serialization, identity, parse, factory-composition,
and future checker boundary revalidates the complete reachable graph without
trusting constructor history. Missing fields, invalid exact types, forged
values, and active object cycles fail closed.

## Canonical wire and budgets

`proof_term_to_bytes` emits a closed envelope containing schema identity, one
term object, and the full SHA-256 of that term object's canonical bytes.
`parse_proof_term` accepts only exact `bytes` equal to that canonical encoding:
UTF-8, sorted keys, compact separators, ASCII escapes, no floats or duplicate
keys, and exactly one trailing newline.

Fixed ceilings are 1 MiB input, depth 64, 4,096 graph nodes, 4,096
coefficients per polynomial, 1,024 CRT parts, and 4,096 bits per integer.
The implementation imports only `__future__`, `dataclasses`, `fractions`,
`hashlib`, `json`, and `typing`; it has no solver, dynamic import, filesystem,
process, network, clock, random, environment, transport, or floating-point
capability.

## Validation

```bash
python -m json.tool docs/contracts/schemas/proof-term-v1.schema.json
python -m unittest discover -s tests/proof_terms -v
python tools/contract_artifacts.py verify \
  --contract MH-C-PROOF-TERM-001 --run-validators --require-bound
python tools/validate_trust_base.py
```
