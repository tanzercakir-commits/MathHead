# Deterministic planning

MH-051 turns one exact, current `mathhead.capability-route-result.v1` into a
finite content-addressed strategy DAG. The boundary is governed by accepted
contract `MH-C-DETERMINISTIC-PLANNER-001` at SHA-256
`72e3c39ea40c599cd709fff590a72bfd096450adbb80689ce934342c3aaaa124`.

The public function is:

```python
plan_strategies(
    request: bytes,
    route_result: bytes,
    descriptors: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> PlanningResult
```

The planning request embeds the original canonical capability-route request,
the exact route-result byte digest, a complete ResourceBudget limit vector,
and one accepted closed policy. The planner reruns capability routing over the
same descriptor and artifact bytes and requires byte-identical output before
it constructs a strategy. A copied result hash therefore cannot conceal a
changed session head, TheoryContext, normalized reading, obligation,
descriptor, availability declaration, cost, or candidate order.

## Policies and graph

`registry_order` preserves MH-050's cost, negative-priority, capability,
plugin, and version order. `deterministic_first` applies the frozen replay-mode
rank and then the original route index. It does not infer semantics from names,
descriptions, histories, or plugin order. Counterexample-first planning is not
available in v1 because the accepted plugin and obligation contracts do not
yet expose a sound-witness-path declaration.

Every candidate occurs exactly once. Nodes are built from last to first so a
fallback can contain the already known SHA-256 of only the next node. The
eleven outcomes are explicit and ordered. Success alone reaches `succeeded`;
exhaustion, cancellation, and verifier failure stop; unsupported, producer
error, ambiguity, truncation, checker inconclusive/disagreement, and invalid
evidence fall forward or terminate at the final node. Strict parsing
recomputes node identities, forward edges, uniqueness, order, and complete
reachability.

## Resource intent

Resource requests use only the accepted integer candidate cost, fragment
quantifier depth, and declared solver effect. All ten ResourceBudget
dimensions are explicit and use portable saturating integer arithmetic. If
one strategy does not fit the declared parent limits, or the complete
candidate count exceeds the policy ceiling, the whole operation returns
`exhausted` without a partial plan.

Planning does not create or reserve a live budget, load a plugin, start a
worker, call a model, solver or checker, produce Evidence or Certificate, or
grant mathematical authority. MH-052 owns isolation and enforcement; MH-053
owns execution.

## Verification

The independent validator reconstructs the accepted route binding, candidate
order, every prerequisite, evidence expectation, resource term, transition,
node hash, forward edge, entry, and final result hash without using production
planner helpers:

```bash
python -m unittest discover -s tests/deterministic_planner -v
python tools/validate_deterministic_planner.py
python tools/contract_artifacts.py verify \
  --contract MH-C-DETERMINISTIC-PLANNER-001 --require-bound
```

The frozen report is
`reports/deterministic-planner-v1.json`. Identical explicit bytes are tested
across fresh processes and different Python hash seeds. CI supplies the
Python 3.10 through 3.14 and Linux/macOS/Windows qualification matrix.
