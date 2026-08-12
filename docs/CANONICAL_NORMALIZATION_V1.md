# Canonical normalization v1

MH-044 adds a pure, deterministic representation boundary over complete,
replay-valid MH-043 proof-obligation bytes. It does not parse prose, simplify
mathematics, choose a reading, solve an obligation, or grant mathematical
authority.

The public entry point is:

```python
normalize_canonical_obligations(proof_result: bytes) -> CanonicalNormalizationResult
```

Only a canonical `mathhead.proof-obligation-result.v1` value with status
`decomposed` is accepted. The complete MH-040 through MH-043 chain is strictly
reparsed and replayed before any normalized artifact is emitted. Invalid and
budget-exhausted inputs return a closed result containing one bounded diagnostic
and no input digest, embedded upstream value, candidate, form, context,
obligation, trace, graph identity, or partial result identity.

## Exact normalization rules

The complete allowlist is frozen in
`normalization/canonical-normalization-rules-v1.json` and bound by SHA-256 in
`MH-C-CANONICAL-NORMALIZATION-001`.

- Quantified variables use lexical depth and declared binder position.
  Definition parameters use owner-local declared position. Their domains,
  roles, order, scope, shadowing, vacuity, and multiplicity remain explicit.
- Free variables retain their declared identity and name. They are never
  alpha-renamed.
- Symbolic witnesses become ordered local-context slots. They are not values or
  discovered witnesses.
- Only logical `and`, logical `or`, binary logical `iff`, binary `equal`, and
  binary `not_equal` use complete normalized-byte commutative ordering.
- Assumption facts use the contracted role rank, complete semantic bytes,
  origin registry, and original occurrence as the duplicate tie-break. Local
  hypotheses use complete semantic bytes and their original occurrence.
- Every other order is preserved, including namespaced applications,
  predicates, implication, ordered relations, tuples, collections,
  conditionals, binders, parameters, goals, graph edges, prerequisites,
  strategies, and witness declarations.

No associativity, flattening, idempotence, identity, inverse, distributivity,
cancellation, evaluation, or operator-name heuristic is applied.

## Two deliberately separate surfaces

Every candidate keeps its exact `source_graph_sha256`, source IDs, source
ordinals, topology, alternative indexes, spans, statuses, strategies, and
reversible occurrence traces. A separate `semantic_graph_sha256` provides a
comparison key under only the frozen rules. For authorized commutative logical
owners, source obligation ordinals are translated to content-derived semantic
ordinals only inside that graph-hash preimage; public obligation topology is
unchanged.

Equal semantic hashes mean byte-equal canonical representation under this exact
contract, catalogue, and schema set. They are not theorem-level equivalence,
truth, satisfiability, proof, or permission to merge readings. Different hashes
do not prove mathematical inequivalence.

## Replay and validation

The result, normal-form, trace, context, and obligation codecs emit sorted-key,
compact, ASCII-escaped canonical JSON with one trailing LF. The strict result
parser reconstructs the embedded MH-043 bytes, reruns the complete
normalization, and requires byte-identical output. Repairing an outer hash
cannot legitimize an altered inner value.

The independent validator is `tools/validate_canonical_normalization.py`. It
binds every accepted artifact, checks the production import/effect closure,
independently recomputes lexical forms, source projections, contexts,
obligations, occurrence permutations, semantic graph and top-level identities,
runs positive and negative metamorphic controls, and checks the frozen report at
`normalization/reports/canonical-normalization-v1.json`.

All normalized records carry `mathematical_authority: false`.
