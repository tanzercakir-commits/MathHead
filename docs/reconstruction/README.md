# MathHead reconstruction records

This directory contains migration evidence derived from, but separate from,
the immutable legacy trackers and architecture records.

`LEGACY_INDEX.toml` assigns every indexed source one role and one claim status:

- `authoritative-*` means current reconstruction authority;
- `historical-*` and `archive` mean preserved evidence, never live state;
- `generated-output` means reproducible engine output, never project status;
- `decision-ledger` means decisions remain valid until a new ADR supersedes them;
- `reference` means descriptive input whose claims must be revalidated.

An immutable entry carries the SHA-256 of the audited `6927033` source tree.
The validator fails if such a source is edited, removed, duplicated, or reached
through a case-insensitive alias.

Accepted reconstruction decisions live under `adrs/` and are indexed by
`adrs/INDEX.toml`. They supersede conflicting legacy architecture claims only
through an explicit new ADR; the legacy decision ledgers remain unchanged as
historical evidence.

## Immutable legacy baseline

`legacy-baseline-v1.json` is the canonical differential-oracle input captured
from commit `3fc1d00efbecad4f18a401db28e350f2b495c6a5`. It records the complete tracked
file inventory, static test identities, package/build metadata, dispatcher
profiles, immutable CI results, benchmark records, known platform failures, and
source/performance hot spots. Red, unsupported, timed-out, and not-run outcomes
are evidence; they are never rewritten as success.

Replay is offline and never executes the legacy product suite:

```bash
python tools/capture_legacy_baseline.py replay --artifact docs/reconstruction/legacy-baseline-v1.json
python tools/validate_legacy_baseline.py
```

The human-supplied external evidence is frozen separately in
`legacy-observations-v1.json`; both files are content-addressed by the validator.
