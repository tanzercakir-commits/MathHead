# Structured unsupported explanations v1

MH-045 adds a pure support-boundary diagnostic over complete, replay-valid
MH-044 canonical-normalization bytes. It names structures that MH-042 through
MH-044 already marked unsupported. It does not interpret prose, change the
problem, choose a reading, discover a plugin, invoke a solver or planner, or
claim mathematical authority.

The public entry point is:

```python
explain_unsupported_constructs(
    normalization_result: bytes,
) -> UnsupportedExplanationResult
```

Only canonical `mathhead.canonical-normalization-result.v1` bytes with status
`normalized` are accepted. The complete embedded MH-040 through MH-044 chain is
strictly reparsed and replayed before a target is emitted. Ordinary invalid and
budget-exhausted inputs return a closed diagnostic result with no embedded
input, target, explanation, candidate, or result identity.

## Exact target inventory

For each reading, unsupported normal forms remain in their MH-044 order and are
followed by unsupported canonical obligations in source ordinal order. Every
such occurrence receives one candidate-local `target_NNNNNNNN` and exactly one
positionally aligned `explanation_NNNNNNNN`. Supported records receive none. A
fully supported reading still receives a valid, content-addressed empty
explanation set.

Targets preserve the reading, source registry and reference, source semantic
identity, available context and obligation ownership, dependency identities,
source spans, trace identities, and occurrence multiplicity. The sorted unique
target semantic identities must exactly equal the upstream unsupported index;
that set check never erases separate occurrences.

Cause identities cover the reading, exact construct code and parameters, and
the complete source semantic identity. They are comparison identities for this
contract only, not proof of mathematical equivalence.

## Frozen catalogue and safe steps

The only matching rules are frozen in
`explanations/unsupported-explanation-catalogue-v1.json` and bound by SHA-256
in `MH-C-UNSUPPORTED-EXPLANATION-001`. Matching uses exact surface, form kind,
fact kind, and obligation kind fields. It never uses names, prose, substring
similarity, edit distance, runtime capability discovery, model output, or
backend behavior.

The catalogue currently owns exact records for:

- opaque named-predicate assumptions;
- opaque typed-relation assumptions;
- logical assumptions retained as one atomic fact;
- quantified assumptions retained without instantiation; and
- structurally unsupported proof obligations.

One final generic fallback owns no executable fragment and asks the caller to
retain the construct for a separately reviewed capability contract.

Every explanation contains one nearest-owned-fragment record and one structured
formalization step. Steps are always `automatic: false`,
`requires_user_confirmation: true`, and `mathematical_authority: false`. They
may request exact missing declarations or an explicit reformulation, but they
never mutate source bytes or claim that a proposed replacement is equivalent.
English summary and detail strings are deterministic renderings of the frozen
codes and validated scalar parameters; the structured fields remain the
machine-readable surface.

## Canonical replay and validation

Targets, fragments, steps, explanations, candidates, diagnostics, and results
are immutable closed values. Their codecs emit sorted-key, compact,
ASCII-escaped JSON with one trailing LF. Explanation, explanation-set, and
result identities use SHA-256 preimages with only their own identity field set
to null. The strict result parser reconstructs the embedded MH-044 bytes,
replays the complete function, and requires byte-identical output, so repairing
an outer digest cannot legitimize an altered target or message.

The independent validator is `tools/validate_unsupported_explanations.py`. It
binds the accepted contract, six closed schemas, and catalogue; audits the
production import/effect closure; independently recomputes target inventory,
construct descriptors, exact rule matches, template rendering, and all digest
layers; validates the frozen report at
`explanations/reports/unsupported-explanations-v1.json`; and exercises invalid,
noncanonical, partial, and repaired-forgery controls.

Run the focused gates with:

```bash
python -m unittest discover -s tests/unsupported_explanations -v
python tools/validate_unsupported_explanations.py
python tools/contract_artifacts.py verify \
  --contract MH-C-UNSUPPORTED-EXPLANATION-001 --require-bound
```

An `explained` result means only that every already-declared unsupported
occurrence received deterministic structural guidance. It does not mean the
construct is false, impossible, permanently unavailable, solvable, proved,
refuted, verified, or equivalent to the suggested formalization.
