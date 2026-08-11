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
