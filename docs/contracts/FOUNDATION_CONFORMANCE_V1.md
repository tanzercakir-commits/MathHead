# P2 foundation conformance v1

This check proves structural compatibility across the active contract-first
foundation. It does not prove mathematical truth, solver correctness, checker
honesty, or runtime isolation.

## Active closure

The inventory is deliberately exact:

| Contract | Target | Normative schema |
| --- | --- | --- |
| `MH-C-CONTRACT-ARTIFACTS-002` | `tools.contract_artifacts:main` | function-contract workflow |
| `MH-C-PROBLEM-IR-002` | `mathhead.ir:ProblemIR` | `problem-ir-v1.schema.json` |
| `MH-C-THEORY-CONTEXT-001` | `mathhead.context:TheoryContext` | `theory-context-v1.schema.json` |
| `MH-C-RESOURCE-BUDGET-001` | `mathhead.budget:ResourceBudget` | `resource-budget-v1.schema.json` |
| `MH-C-ENGINE-RESULT-001` | `mathhead.results:EngineResult` | `engine-result-v1.schema.json` |
| `MH-C-EVIDENCE-001` | `mathhead.evidence:Evidence` | `evidence-v1.schema.json` |
| `MH-C-CERTIFICATE-001` | `mathhead.certificates:Certificate` | `certificate-v1.schema.json` |
| `MH-C-THEORY-PLUGIN-001` | `mathhead.plugins:TheoryPlugin` | `theory-plugin-v1.schema.json` |

The checker binds every item to its accepted manifest record, canonical
accepted and proposal bytes, proposal hash, pre-screen and acceptance report,
target, supersession, validator references, schema bytes, and explicit
cross-contract dependencies. Every schema passes a dependency-minimal,
fail-closed Draft 2020-12 keyword and structure check; when `jsonschema` is
installed, the standard Draft 2020-12 meta-validator runs as an additional
check. Every schema must also accept its representative minimal instance and
reject unknown and missing root fields. The optional standard check does not
alter report bytes, so dependency-free status and full environments reach the
same deterministic identity.

## Negative conformance

Built-in probes demonstrate fail-closed handling for unknown or missing
contract fields, duplicate JSON keys, syntactic contradictions, a missing
primary validator, shell syntax in a validator command, and exact synthetic
implementation binding. The unittest suite additionally mutates isolated
copies of the repository closure to exercise manifest hashes,
accepted/proposed byte separation, schema hashes, acceptance-report identity,
dependency hashes, targets, supersession, contract hashes, signatures, and
implementation source.

Accepted contract, proposal, schema, and report bytes are never changed by a
negative probe.

## Future implementation binding

An unimplemented foundation target is reported as `not_implemented`, never as
passed or failed implementation conformance. Once its module and symbol exist,
the existing contract workflow requires the exact accepted signature and one
matching `*_CONTRACT_ID` plus `*_CONTRACT_SHA256` pair.

The cross-contract gate additionally requires exactly one canonical line of
this form in new foundation implementation source:

```python
COMPONENT_IMPLEMENTATION_SHA256 = "<64 lowercase hexadecimal characters>"
```

Its value is SHA-256 over the complete source bytes after replacing only those
64 characters with zeroes. Consequently, comments, annotations, defaults,
metadata, and executable code are all source-bound without a circular hash.
Signature drift, accepted-contract hash drift, source drift, duplicate
markers, and missing markers fail independently.

The already implemented and independently accepted contract-artifact tool is
not retrofitted with this marker; its immutable contract and existing static
binding remain authoritative.

## Deterministic report

`docs/contracts/reports/foundation-conformance-v1.json` records the exact
closure, schema probes, negative probes, implementation state, primary
validator executions, workflow and manifest identity, and a content-derived
report hash. Refreshing and checking use the same command:

```bash
python tools/validate_contract_conformance.py \
  --report docs/contracts/reports/foundation-conformance-v1.json
python tools/validate_contract_conformance.py \
  --check-report docs/contracts/reports/foundation-conformance-v1.json
```

`--skip-validator-execution` exists only for focused mutation tests and emits
a visibly different report whose validators are `not_run`; it cannot satisfy
the repository's checked report.
