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

## Isolated worker enforcement

MH-052 consumes one exact planned strategy and reserves its complete ten-
dimension request from an open accepted `ResourceBudget` before launching any
producer. The boundary is governed by `MH-C-ISOLATED-WORKER-001` at SHA-256
`c578d5a75f7a670f55e660147c335dc29709e71b82af8b37eb0033891b81a49b`.

`supervise_worker` never imports a producer or accepts a callable. It executes
one content-bound absolute executable with a direct argument vector, closed
stdin, bounded binary stdout/stderr sinks, a private working directory, and a
minimal environment. Linux and macOS use fresh POSIX sessions, inherited CPU,
address-space, file-size and descriptor limits, plus complete process-group
termination. Windows starts the process suspended, assigns a kill-on-close Job
Object with job CPU and memory limits, and resumes only after containment.

Wall timeout, cancellation, output exhaustion, nonzero exit, malformed input,
and cleanup failure are distinct terminal results. All ordinary launched paths
close a child budget and reconcile its lease exactly once. `completed` means
only that bounded producer bytes were returned and the complete containment
unit was cleaned; it never validates `Evidence`, a `Certificate`, a proof, a
refutation, or any mathematical claim.

The exact checks are:

```bash
python -m unittest discover -s tests/isolated_worker -v
python tools/validate_isolated_worker.py
python tools/contract_artifacts.py verify \
  --contract MH-C-ISOLATED-WORKER-001 --require-bound
```

The independent validator does not import the production supervisor. It
rebinds the accepted contract and six closed schemas, reconstructs request and
artifact identities and lease conservation, audits both platform adapters and
their forbidden shell surface, and freezes the result in
`reports/isolated-worker-v1.json`.

## Proof/search portfolio execution

MH-053 consumes the exact MH-051 graph and sends every visited producer and
checker through the MH-052 supervisor. The boundary is governed by
`MH-C-PROOF-SEARCH-PORTFOLIO-001` at SHA-256
`b59384b54d10665528540e470a3e5b6f7eae8bdcce198d6814a7459c073e0144`.
The request binds the complete sorted descriptor inventory, plan-order
execution bindings, open parent ledger, and ordered artifact inventory.
Executable paths remain explicit effect inputs and never enter canonical
result identity.

Execution begins at the plan entry and is sequential. Each producer and its
separate checker receive unique deterministic child leases; the exact
reconciled parent ledger from one invocation becomes the next invocation's
input. The accepted transition for the classified outcome is the only way to
continue or stop. Unsupported work, producer failure, malformed Evidence,
checker inconclusive or disagreement, and truncation can fall forward;
exhaustion, cancellation, and verifier failure stop. There are no retries,
speculative launches, hidden budget, or timing-selected edges.

A completed producer remains non-authoritative. Promotion requires canonical
produced Evidence for the exact planned obligation, an explicit `proved` or
`refuted` claim, a separately executed exact planned checker, a canonical
Certificate with complete trust closure and matching replay, and a closed
checker decision that agrees with the same claim and bytes. The portfolio
result itself always has `mathematical_authority: false`; only the selected
Certificate carries checker or external proof-assistant authority.

Accepted v1 capability descriptors expose no sound counterexample-path
declaration, so the recorded policy is
`planner_order_no_sound_witness_declaration`. The portfolio never reorders a
strategy by its name, payload, prior result, or folklore. Checked refutations
remain refutations, but no absence-of-witness or exhausted search becomes a
proof.

Validate the six closed schemas, real producer/checker isolation, ledger
arithmetic, exact fallbacks, adversarial promotion boundaries, and independent
fresh-process reconstruction with:

```bash
python -m unittest discover -s tests/proof_search_portfolio -v
python tools/validate_proof_search_portfolio.py
python tools/contract_artifacts.py verify \
  --contract MH-C-PROOF-SEARCH-PORTFOLIO-001 --require-bound
```

The frozen independent report is
`reports/proof-search-portfolio-v1.json`. MH-053 retains no audit log, cache,
replay bundle, public cancellation surface, or interface adapter; those remain
owned by later tasks.
