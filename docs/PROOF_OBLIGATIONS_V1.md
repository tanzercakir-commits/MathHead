# Proof-obligation decomposition v1

MH-043 introduces a deterministic, non-authoritative proof-obligation boundary
under accepted contract `MH-C-PROOF-OBLIGATION-DECOMPOSITION-001` at SHA-256
`ea5d0664611b57da3074e20fce90623318ce04280d38ecce548025a91a7b19ff`.
The implementation is `mathhead.proof_obligations`. Its closed obligation,
local-context, graph, catalogue, and result schemas live under
`docs/contracts/schemas/`; the frozen syntax-directed rule and strategy
catalogues live under `docs/obligations/`.

## Boundary and authority

```python
from mathhead.proof_obligations import (
    decompose_proof_obligations,
    proof_obligation_result_bytes,
    proof_obligation_result_sha256,
)

decomposition = decompose_proof_obligations(successful_mh042_result_bytes)
if decomposition.status == "decomposed":
    canonical_bytes = proof_obligation_result_bytes(decomposition)
    identity = proof_obligation_result_sha256(decomposition)
```

`decompose_proof_obligations(domain_result: bytes)` accepts only complete,
canonical, successful MH-042 bytes. It strictly replays their embedded MH-041,
MH-040, and ProblemIR chain before use. Malformed, noncanonical, stale, forged,
failed, subclassed, or over-budget inputs return one closed `invalid` or
`exhausted` result with no graph, input identity, or other partial artifact.

Every result, graph, context, obligation, and strategy record has
`mathematical_authority == False`; every strategy also has
`guarantees_success == False`. Decomposition says what structural work is
declared, not whether a goal is true, solvable, proved, refuted, satisfiable, or
likely to yield to a strategy.

## One graph per reading

Each successful MH-042 candidate receives a separate graph. Candidate wrappers
use stable reading-ID order, while each graph preserves the reading's declared
goal order. Every goal has exactly one root. Unresolved alternatives remain
separate: the boundary does not select, rank, merge, compare, or transfer facts
between readings.

Each obligation records:

- a deterministic preorder ordinal, `obligation_NNNNNN` ID, and complete
  SHA-256 identity;
- its reading, root goal, unique parent, reviewed rule, kind, and goal mode;
- its exact statement and relation references, canonical source fragment,
  semantic dependency closure, and source spans;
- its complete local-context identity, ordered children, explicit
  prerequisites, choices, and symbolic witness placeholders;
- exact catalogue-ordered strategy admissibility reasons; and
- a structural `ready`, `waiting`, `choice_required`, or `unsupported` status.

These statuses are workflow metadata. In particular, `ready` does not mean
solved, `waiting` does not mean false, `choice_required` does not choose a
disjunct, and `unsupported` never discards a declared goal.

## Syntax-directed algebra

Truth and relation statements remain atomic. Negation remains exact and is not
pushed inward. Conjunction emits every ordered operand. Disjunction retains
every ordered alternative and a choice-required parent. Implication adds only
the exact antecedent as a local hypothesis for the consequent. Biconditional
emits both ordered implication directions.

Universal statements extend binder scope in declared order. Existential
statements expose separate symbolic witness-construction and body-verification
duties. Unique existence additionally exposes an undecomposed uniqueness duty.
Placeholders are deterministic identifiers, never values or synthesized
witnesses. `refute`, `find_witness`, `compute`, `classify`, and `optimize` goals
remain atomic mode-shaped duties and are never executed here.

Every local context retains the reading's definitions, complete ordered MH-042
fact identities, inherited binders, exact implication hypotheses, symbolic
witness placeholders, full semantic dependencies, reachable source spans, and
the normalized-context identity. Child ownership is unique, roots cover goals
exactly, prerequisites point backward to explicit duties, and repaired cycles,
dangling references, escaped parents, false statuses, or erased alternatives
fail closed.

## Strategy admissibility

The frozen catalogue matches only exact obligation kind, goal mode, relation
kind, reachable domain kind, or builtin carrier. It covers truth constants,
equality and disequality, ordered relations, membership, divisibility,
congruence, named predicates, structural composition, case choice, witness and
uniqueness duties, counterexample search, exact computation, classification,
optimization, finite enumeration, modular domains, and numeric carriers.

Admissibility is neither ranking nor execution. An empty strategy list is
valid. The boundary calls no planner, solver, CAS, producer, checker, proof
assistant, model, filesystem, process, environment, clock, randomness, network,
CLI, or MCP owner.

## Canonical replay and ceilings

Artifacts use NFC strings, sorted JSON object keys, compact separators, ASCII
escapes, no floats, exact portable integers, and exactly one trailing LF.
Identities are full lowercase SHA-256 values over complete canonical bytes.
Strict result parsing reconstructs the embedded MH-042 bytes, reruns the full
decomposition, and requires byte-identical output; repaired outer hashes cannot
legitimize missing, surplus, reordered, cross-reading, cyclic, or fabricated
graph content.

The fixed policy caps input at 256 MiB and output at 512 MiB; readings and goals
at 100,000; obligations and contexts at 800,000; edges at 1,600,000;
dependencies at 2,400,000; strategies at 128 per obligation; nesting at 512;
validation work at 32,000,000 deterministic steps; and strings, integers, and
diagnostics at explicit portable limits. Any ceiling is checked before a
partial graph can escape.

## Validation

```bash
python -m unittest discover -s tests/proof_obligations -v
python tools/validate_proof_obligations.py
python tools/contract_artifacts.py verify \
  --contract MH-C-PROOF-OBLIGATION-DECOMPOSITION-001 --require-bound
python tools/validate_trust_base.py
python tools/project_status.py check
```

The independent validator reads the accepted artifacts and catalogues, audits
the production import and effect closure, constructs two unresolved rich
readings, and independently recomputes all roots, children, fragments,
contexts, dependencies, edges, statuses, choices, placeholders, strategies,
graph identities, and the result identity. Its frozen report currently covers
100 obligations, twelve local contexts, 162 exact strategy records, and fifteen
negative controls. Unit and CI coverage adds every relation and domain kind,
all logical and quantified forms, all goal modes and assumption roles,
forgery/cycle/budget resistance, hash-seed repeatability, clean-wheel
installation, Python 3.10 through 3.14, and Linux, macOS, and Windows.
