# Foundation reference fixtures

`foundation-v1/` is the canonical MH-028 cross-layer boundary for the accepted
P2 foundation contracts. It contains eight exact scenarios: proof, refutation,
unresolved ambiguity, unsupported input, wall-time exhaustion, backend
disagreement, semantic certificate invalidity, and replay mismatch.

The bundle manifest has the stable identity
`4132b29b69600f8ff48477515853f66bb748c7337735c00db8e634987f70ddca`.
Its basis is the canonical manifest with only `bundle_sha256` replaced by 64
zeroes. The manifest binds the nine governing workflow and function contracts,
the MH-027 conformance report, every artifact and attachment byte count and
SHA-256, the dependency DAG, routing decision, expected outcome, and explicit
presence state.

## Layout

- `foundation-v1/manifest.schema.json` is a closed Draft 2020-12 schema.
- `foundation-v1/manifest.json` is the canonical ordered bundle manifest.
- `foundation-v1/objects/<sha256>.json` is the deduplicated object store. A
  filename is the SHA-256 of its canonical JSON bytes.
- Scenario artifact roles are always ordered as ProblemIR, TheoryContext,
  ResourceBudget, TheoryPlugin, Evidence, Certificate, and EngineResult.
- Payloads, checker results, replay logs, and disagreement inputs are real
  content-addressed attachment bytes rather than placeholder hashes.

An absent artifact is a closed `state: absent` variant with a reason. A present
artifact must resolve to non-empty canonical bytes; an empty present artifact
is invalid. This distinction prevents ambiguity, refusal, and timeout from
silently becoming empty evidence.

## Commands

Regenerate and validate the bundle:

```bash
python tools/validate_reference_fixtures.py --write
python tools/validate_reference_fixtures.py
python -m unittest discover -s tests/reference_fixtures -v
```

The generator is source-location independent. Its isolated-root and relocated
subprocess tests rebuild the same manifest and object bytes. Validation works
with the dependency-minimal repository interpreter; when `jsonschema` is
installed, the standard Draft 2020-12 meta-validator and instance validator run
in addition to the repository's fail-closed checks.

## Authority boundary

Only proof and refutation carry `checker_attested` authority, and only when the
independently loaded Certificate is `verified`. Unsupported, ambiguous,
exhausted, disagreement, invalid-certificate, and replay-mismatch scenarios
cannot expose a proved or refuted mathematical verdict. These fixtures define
wire compatibility and failure semantics for later implementations; they do
not implement a parser, solver, checker, worker, kernel, planner, or plugin.
