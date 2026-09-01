# Provenance replay v1

`mathhead.kernel.provenance` is the dependency-minimal boundary that turns a
set of stored run artifacts back into a fresh checker decision. It is governed
by `MH-C-PROVENANCE-REPLAY-001` at SHA-256
`31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67`.

## Bundle identity

The canonical manifest has schema `mathhead.provenance-manifest.v1`. Its full
SHA-256 is both the manifest identity and the bundle address. Every object
record binds an exact byte count, full SHA-256, media type, schema, governing
contract, role, and sorted dependency set. A proof-term bundle contains 12
roles; a SAT bundle contains 13. Missing, extra, repeated, reordered, aliased,
or dependency-mismatched records fail closed.

The common roles bind the exact ProblemIR, TheoryContext, TheoryPlugin
descriptor and version, ResourceBudget, Evidence, Certificate, EngineResult,
checker contract, checker source, checker configuration, and recorded checker
result. Dispatch-specific roles contain either a canonical proof term or the
exact CNF and SAT/DRUP certificate bytes.

Foundation objects retain the canonical bytes already governed and validated
by their producing contracts. This boundary rechecks canonical JSON syntax,
root schema tags, contract identities, plugin identity/version, the complete
dependency graph, and every content digest; it does not duplicate the large
semantic validators for ProblemIR or the other P2 formats inside the trusted
kernel. Mathematical authority depends only on the fresh small-checker replay.

## Replay and authority

`replay_provenance_bundle(manifest, objects)` ignores stored verdicts as
authority. It allowlists only:

- `mathhead.kernel.checker.v2`, using canonical MH-031 proof terms; and
- `mathhead.kernel.sat-replay.v1`, using exact canonical CNF and certificate
  bytes.

The selected checker runs again and its complete canonical result bytes must
equal the recorded `checker_result` object. Only an identical fresh
`verified` result preserves `checker_attestation`. Exact `refuted`, `invalid`,
`unsupported`, and `exhausted` checker outcomes remain non-authoritative.
Structural mismatch is a provenance `invalid` result, never a weaker success.

Canonical result parsing requires the original manifest and objects and repeats
the full replay. Results are immutable, constructor-closed, non-pickleable, and
content-addressed.

## Atomic store

`mathhead.provenance_store` is deliberately outside the trusted kernel. It
writes only structurally complete bundles and stores objects at:

```text
objects/<first-two-hex>/<remaining-62-hex>
bundles/<first-two-hex>/<remaining-62-hex>/manifest.json
```

Objects are written and synced before the manifest, which is the sole commit
marker. Existing identical objects are reused. Loads reject traversal-shaped
identities, symlinks, multiple hard links, writable or non-regular files,
short reads, mutation, size/hash drift, unexpected bundle-directory state, and
missing objects, then perform a fresh pure replay. Persistence never creates or
upgrades mathematical authority.

The legacy discovery `proof_hash()` remains 16 hexadecimal characters only for
compatibility. `proof_sha256()` supplies the complete canonical MH-031 term
identity; neither is a substitute for a complete replay bundle.

## Validation

```bash
python tools/validate_provenance_replay.py
python -m unittest discover -s tests/provenance_replay -v
python tools/contract_artifacts.py verify \
  --contract MH-C-PROVENANCE-REPLAY-001 --require-bound
```

The pure replay closure contains eight internal modules and eight approved
standard-library roots. It imports no filesystem, process, network, solver,
CAS, clock, randomness, dynamic-import, discovery, MCP, or CLI surface. The
filesystem adapter is separately classified as a non-authoritative effect
boundary.
