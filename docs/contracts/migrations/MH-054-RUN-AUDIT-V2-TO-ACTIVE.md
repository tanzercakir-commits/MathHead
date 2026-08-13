# MH-054 run-audit v2 to active migration

## Status

This migration activates `MH-C-AUDITED-RUN-004`,
`MH-C-RUN-AUDIT-REPLAY-004`, and `MH-C-RUN-AUDIT-STORE-005`. Accepted v2 and
v3 contracts, the accepted intermediate store contract `004`, their schemas,
and their frozen reports remain immutable historical evidence.

## Reason

The v2 worker-observation closure repaired the missing worker-result preimage,
but qualification found three further boundary requirements that could not be
backported into accepted contracts:

1. audit object order, the prelaunch-invalid final ledger, and invalid-output
   metadata needed independent reconstruction rather than producer-authored
   ordering or retained content identities;
2. the durable store needed a pinned descriptor-relative root so replacement
   of a lexical ancestor could not redirect a later effect;
3. unsupported directory synchronization and the exact store object-count
   boundary had to remain closed non-success outcomes.

Audit/replay v3 and store v3 repaired the semantic audit graph, then accepted
store v4 introduced the pinned store while still binding the v3 audit/replay
owners. Because accepted artifacts are immutable, the final coherent graph
requires audit v4, replay v4, and store v5.

## Active graph

- `MH-C-AUDITED-RUN-004`:
  `9079e68799fe032d982be87034ecb42cbc4b9a8486f370f01ace12a21d2ac4c4`
- `MH-C-RUN-AUDIT-REPLAY-004`:
  `04f484fc85486bcf8b17519128cd74336ff1834e76ab8d5e2713022d91c02c3b`
- `MH-C-RUN-AUDIT-STORE-005`:
  `399bcb9d97217d249d9200697281a25052476f67f8435740fa32d6c7ed2c272b`
- replay-result v4:
  `ae6f6f60f936a40926cd7942e00088a8f409836182d089b2f9c3cec5b007269d`
- store-result v5:
  `bf906f5c01fee05524b4c11cb80a526b5ca72214e8b417d44a3d4191077c11d4`

The active audit graph otherwise retains the content-addressed object v2,
event v2, manifest v3, logical-report v2, worker-observation v3, and store-record
v2 leaves named by the accepted contracts.

## Compatibility boundary

- No historical accepted contract, schema, report, bundle, or run record is
  edited or relabelled.
- Current capture emits only audit v4 bundles; current replay returns only the
  v4 replay result; current persistence accepts only the audit v4/replay v4
  graph and returns only the v5 store result.
- Historical bundles may be retained for forensic comparison, but they are not
  current success inputs. Regeneration requires executing the accepted semantic
  inputs through the active audited boundary.
- Unsupported platforms return the closed store result before content creation;
  supported platforms pin every ancestor and perform descendant effects through
  opened no-follow directory descriptors.
- Migration never upgrades mathematical authority. Audit, replay, and store
  results remain explicitly non-authoritative.

## Adoption order

1. Deploy the immutable accepted contract and schema graph.
2. Deploy audit v4 capture and replay v4 together.
3. Deploy store v5 after the active audit/replay graph is present.
4. Regenerate the v4 audit and v5 store frozen validation reports.
5. Retain all earlier material only as immutable migration evidence.
