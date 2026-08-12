# Domain and assumption normalization v1

MH-042 introduces a deterministic, non-authoritative structural normalization
boundary under accepted contract
`MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001` at SHA-256
`609bc3a0773016f73d4bcee21d6aef034c74bb8edb36fddd9b6df1a4f4ba219a`.
The implementation is `mathhead.domain_assumptions`. Its closed fact, context,
rule-catalogue, and result schemas live under `docs/contracts/schemas/`; the
frozen rule catalogue is
`docs/normalization/domain-assumption-rules-v1.json`.

## Boundary and authority

```python
from mathhead.domain_assumptions import (
    domain_assumption_result_bytes,
    domain_assumption_result_sha256,
    normalize_domain_assumptions,
)

normalization = normalize_domain_assumptions(successful_mh041_result_bytes)
if normalization.status == "normalized":
    canonical_bytes = domain_assumption_result_bytes(normalization)
    identity = domain_assumption_result_sha256(normalization)
```

`normalize_domain_assumptions(readings_result: bytes)` accepts only complete,
canonical, successful MH-041 result bytes. It strictly replays their embedded
MH-040 intake and ProblemIR chain before use. Failed, exhausted, malformed,
noncanonical, stale, forged, subclassed, or over-budget inputs return one
closed failure result without a partial context or input identity.

Every output has `mathematical_authority == False`. A normalized result says
only that the already-declared structures were inventoried reproducibly under
the frozen exact-match rules. It is not a semantic-equivalence claim,
satisfiability result, implication, proof obligation, solver verdict, proof,
refutation, certificate, or checker attestation.

## Per-reading contexts

Each MH-041 candidate receives exactly one context. Candidate wrappers sort by
stable reading ID, but contexts never combine candidates or transfer a fact
between readings. Unresolved alternatives therefore remain independent and no
selection is synthesized.

A context contains:

- every reachable domain ID and variable ID in stable registry order;
- the reading's exact declared assumption order;
- one fact for each domain and variable-domain binding;
- at least one fact for every declared assumption;
- full fact and context SHA-256 identities; and
- the ordered identities of facts that remain explicitly unsupported.

Every fact binds its reading, origin registry and ID, assumption role,
statement and relation where present, stable subjects, complete typed semantic
dependency closure, complete reachable source spans, an exact fragment
SHA-256, the canonical origin payload, a reviewed rule ID, support state, and
`mathematical_authority: false`.

## Frozen structural rules

The catalogue covers all eight ProblemIR domain variants: builtin, finite,
interval, modular, collection, product, function, and theory structure. The
six builtin carriers—boolean, natural, integer, rational, real, and complex—are
retained exactly; no widening, embedding, or default-domain inference occurs.
Finite enumerations, interval endpoints and closure flags, modular carriers,
collection kind and finiteness, ordered product factors, nullary or higher-arity
function spaces, totality, and structure parameters remain literal data.

Exact relation kinds retain equality, disequality, ordered bounds, membership,
nonmembership, divisibility, and congruence. Exact catalogued predicate IDs
cover nonzero, finiteness, cardinality, dimension, graph class, and regularity
only at their frozen arities. An exact binary disequality with one exact zero
literal additionally emits a nonzero structural fact immediately after the
disequality. Unknown predicates and unrecognized relation, logical, or
quantified structures remain source-backed opaque facts with `supported:
false`; they are never dropped or treated as false.

No rule performs alpha-renaming, commutative or algebraic rewriting,
assumption sorting, simplification, semantic strengthening or weakening,
equivalence, satisfiability, implication, contradiction conversion, obligation
decomposition, solving, or proof checking. Those are later, separately
contracted boundaries.

## Canonical replay and ceilings

Facts, contexts, and results use NFC strings, sorted JSON object keys, compact
separators, ASCII escapes, no floats, and one trailing LF. Identities are full
lowercase SHA-256 values over complete canonical bytes. Strict result parsing
reconstructs the embedded MH-041 bytes, reruns the complete normalization, and
requires byte-identical output, so repaired outer hashes cannot legitimize an
omitted, reordered, surplus, or cross-reading fact.

The fixed policy includes 192 MiB input, 256 MiB output, 100,000 readings,
domains, variables, and assumptions, 400,000 facts, 1,200,000 dependencies,
nesting 512, 16,000,000 deterministic validation steps, bounded strings and
diagnostics, exact portable integers, and a 1.5 GiB memory policy. Wall-clock
cancellation remains caller-owned and never enters canonical identity.

## Validation

```bash
python -m unittest discover -s tests/domain_assumptions -v
python tools/validate_domain_assumptions.py
python tools/contract_artifacts.py verify \
  --contract MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001 --require-bound
python tools/validate_trust_base.py
python tools/project_status.py check
```

The independent validator reads the accepted artifacts and frozen catalogue,
audits the production import and effect closure, independently recomputes every
fixture dependency closure, origin fragment, rule choice, fact digest,
unsupported index, context identity, and top-level identity, checks the closed
schemas, exercises negative controls, and verifies strict replay. Unit and CI
coverage includes all domain variants and builtin carriers, interval and
collection variants, nested products, total and partial function spaces,
theory structures, all assumption roles, catalogued and opaque predicates,
nonzero extraction, unresolved readings, forgery resistance, supported Python
versions, hash seeds, clean-wheel installation, and Linux, macOS, and Windows.
