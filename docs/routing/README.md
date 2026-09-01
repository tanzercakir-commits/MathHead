# Typed capability routing

MH-050 replaces prose and keyword similarity with a pure, content-addressed
eligibility boundary. The accepted contract is
`MH-C-CAPABILITY-REGISTRY-001`; its public implementation is
`mathhead.capability_registry:route_capabilities`.

The caller supplies only canonical bytes: one exact route request, a tuple of
complete TheoryPlugin descriptors, and the complete event/artifact inventory
needed to replay the named problem-session revision. The boundary validates the
descriptors without importing their entry points, replays the session, proves
the obligation and context current, derives the fragment from normalization
bytes, and emits deterministic candidate and incompatibility records.

Eligibility covers theory, domain, quantifier, expression and relation kinds,
size limits, exact arithmetic, features, operation, Evidence and Certificate
formats, platform, Python version, extensions, effects, replay mode,
dependencies, and explicit availability. Eligible candidates order by integer
cost ascending, priority descending, capability ID, plugin ID, and semantic
version. The selected record is permission for later planning only: it never
executes a plugin or claims that the problem is solvable or true.

`recommend_tool` remains available solely as a legacy exact-name lookup. It
does not tokenize prose, score descriptions, or participate in typed routing.
Use `list_capabilities` to browse that legacy catalogue.

Frozen independent evidence lives in
`reports/capability-registry-v1.json`. Regenerate it only after reviewing the
contract, schemas, production source, tests, and independent validator:

```bash
python tools/validate_capability_registry.py \
  --write-report docs/routing/reports/capability-registry-v1.json
python tools/validate_capability_registry.py
python -m unittest discover -s tests/capability_registry -v
```

The result status vocabulary is `routed`, `unsupported`, `ambiguous`,
`invalid`, and `exhausted`. Every status and nested record carries
`mathematical_authority: false`.
