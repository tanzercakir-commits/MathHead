# SAT replay v1

`mathhead.kernel.sat` is MathHead's sole dependency-minimal authority boundary
for SAT assignments and RUP-only DRUP refutations. It is governed by
`MH-C-SAT-REPLAY-001` at SHA-256
`0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50`.
The result schema is bound at
`e7bccaba76958f185a94d7570b5c65972a855dd99888c04269074491506ef242`.

## Canonical inputs

The checker accepts exact `bytes`, strict printable ASCII, LF endings, single
spaces, no comments, and one trailing LF per record. Canonical CNF starts with:

```text
p mathhead-cnf 1 <variable-count> <clause-count>
```

Each following clause contains sorted, unique, nonzero signed literals and a
zero terminator. Clauses are unique and lexicographically sorted; tautologies
are forbidden; the variable count equals the greatest literal magnitude.

A SAT certificate binds the exact CNF hash and contains one complete ordered
assignment:

```text
p mathhead-sat-assignment 1 <cnf-sha256>
v -1 2 3 0
```

A supported UNSAT certificate is explicitly RUP-only DRUP:

```text
p mathhead-drup 1 <cnf-sha256>
a 1 -2 0
d -1 3 0
a 0
```

Every addition is checked by assuming its negation and running deterministic
unit propagation to conflict before insertion. A deletion removes the newest
active exact match and grants no authority. Retaining already-entailed deleted
clauses is a sound fallback only for this RUP-only format. A
`p mathhead-drat 1 ...` header is recognized but returns `FORMAT_UNSUPPORTED`;
RAT steps are never interpreted as RUP.

## Result and authority

`check_sat_certificate(cnf, certificate)` returns an immutable
`SATReplayResult` with one of `verified`, `refuted`, `invalid`, `unsupported`,
or `exhausted`. Only `verified` carries `checker_attestation`. Every other
outcome carries `authority=none`, including malformed bytes, a false claim, a
wrong CNF hash, an unsupported format, and deterministic budget exhaustion.

Canonical result serialization recomputes the complete decision. Parsing
requires the exact CNF and certificate bytes again and compares every result
field and identity with a fresh replay.

## Compatibility

`mathhead.drat:check_unsat_proof` and
`mathhead.discovery.rup_check:check_drup_proof` preserve their legacy
collection inputs and result labels. They canonicalize into the versioned byte
format and translate the kernel outcome; neither adapter implements unit
propagation or constructs checker authority.

## Validation

```bash
python tools/validate_sat_replay.py
python -m unittest discover -s tests/sat_replay -v
python tools/contract_artifacts.py verify --contract MH-C-SAT-REPLAY-001
```

The checker closure is one internal module and five standard-library roots:
`__future__`, `dataclasses`, `hashlib`, `json`, and `typing`. It imports no
solver, CAS, clock, filesystem, process, network, randomness, dynamic import,
discovery, router, CLI, MCP, or producer module.
