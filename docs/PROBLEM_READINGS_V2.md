# Deterministic alternative-reading analysis v2

MH-041 introduces the non-authoritative interpretation-analysis boundary under
accepted contract `MH-C-READING-ANALYSIS-002` at SHA-256
`0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70`.
It supersedes `MH-C-READING-ANALYSIS-001`, whose result did not embed the
accepted intake object and therefore could not support self-contained
historical replay. Both versions remain immutable contract evidence; only v2
is active.

The implementation is `mathhead.problem_readings`. Its projection and result
schemas are `docs/contracts/schemas/reading-projection-v2.schema.json` and
`problem-readings-result-v2.schema.json`.

## Boundary and authority

```python
from mathhead.problem_readings import (
    analyze_problem_readings,
    reading_analysis_result_bytes,
    reading_analysis_result_sha256,
)

analysis = analyze_problem_readings(accepted_intake_result_bytes)
if analysis.status == "analyzed":
    canonical_bytes = reading_analysis_result_bytes(analysis)
    identity = reading_analysis_result_sha256(analysis)
```

`analyze_problem_readings(intake_result: bytes) -> ReadingAnalysisResult`
accepts only canonical bytes for an accepted
`mathhead.problem-intake-result.v1`. It reparses and revalidates that artifact,
then reads only the already-declared ProblemIR candidates. It never parses
prose, Markdown, LaTeX, MathML, Python expressions, or legacy discovery output;
never creates a candidate; and never selects one for the caller.

Every result has `mathematical_authority == False`. An analyzed result proves
only that the declared representations and their structural differences were
reproduced deterministically. It is not a semantic-equivalence claim, domain
normalization, solver result, proof, refutation, or checker attestation.

## Projection and delta model

There is exactly one base reading. Every alternative must point directly to
that base. Candidate wrappers sort by reading ID, while semantic orders such as
goals, binders, operands, arguments, tuple elements, and definition parameters
remain unchanged.

Each `mathhead.reading-projection.v2` object contains the exact reading label,
definition and assumption roots, ordered goal roots, reading spans, global
extensions, and complete typed dependency closure through goals, assumptions,
definitions, statements, relations, expressions, variables, domains, source
spans, and source documents. Its canonical bytes and full SHA-256 are retained
together.

An alternative has one delta for every declared ProblemIR difference. The
analyzer independently recomputes:

- removed, added, and retained affected IDs;
- typed structural paths and source spans;
- canonical before/after fragment identities;
- quantifier, domain, scope, notation, parse, reference, or other structural
  evidence; and
- the exact partition of every changed reachable ID.

Labels and summaries are descriptive only. Empty, false, surplus, overlapping,
omitted, chained, or misclassified differences fail closed. Quantifier order
and goal order cannot be normalized away. Notation and parse differences need
an actual change in accepted source-span provenance.

## Choice and failure algebra

The accepted ProblemIR ambiguity state is copied without reinterpretation:

- `unambiguous` has one selected base and no required choice;
- `unresolved` retains all candidates, has no selection, and copies the exact
  required-choice prompt; and
- `resolved` retains all candidates and only the selection already declared by
  the caller.

The result status is `analyzed`, `invalid`, or `exhausted`. Failed results have
one bounded diagnostic and contain no intake object, ProblemIR identity,
candidate, projection, delta, selection, or partial digest. Stable reasons are
`ANALYZED`, `BUDGET_EXHAUSTED`, `INVALID_DIFFERENCE`, `INVALID_INTAKE`,
`INVALID_READING_GRAPH`, and `INVALID_TYPE`.

Analyzed v2 results embed the complete accepted intake object. Strict parsing
reconstructs its exact canonical bytes, reruns the analysis, and requires a
byte-identical result. Forged projections, repaired outer hashes, stale deltas,
unknown fields, duplicate keys, floats, bool-as-int values, noncanonical JSON,
NUL or non-NFC strings, and over-budget structures cannot become analyzed.

Fixed ceilings include 64 MiB input, 192 MiB output, 100,000 candidates and
entities, 400,000 deltas and paths, depth 512, 12,000,000 graph-validation
steps, 1,048,576 code points per string, 16,777,216 aggregate string code
points, and exact integers no larger than `2**53 - 1` in magnitude.

## Legacy boundary

The legacy discovery representation and statement-parsing modules may help a
caller author ProblemIR, but they remain non-authoritative adapters. Their
labels, inferred forms, solver objects, and text envelopes are not accepted by
this function. A caller must pass them through the explicit MH-040 structured
intake boundary before MH-041 can compare the declared readings.

## Validation

```bash
python -m unittest discover -s tests/problem_readings -v
python tools/validate_problem_readings.py
python tools/contract_artifacts.py verify \
  --contract MH-C-READING-ANALYSIS-002 --require-bound
python tools/validate_trust_base.py
```

The independent validator reconstructs every projection closure, canonical
byte sequence, projection and result SHA-256, structural path, affected-ID
partition, and before/after fragment identity without using production helper
functions. Unit and CI coverage includes all ProblemIR domain variants,
quantifier variants and binder order, definition/assumption/goal root changes,
source-backed notation and parse differences, failed intake, adversarial delta
metadata, strict replay, hash-seed reproducibility, supported Python versions,
and clean-wheel imports.
