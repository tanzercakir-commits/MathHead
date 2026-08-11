# Reconstruction architecture decisions

This directory is the accepted decision authority for
`MH-RECONSTRUCTION-V1`. The root `DECISIONS.md` and
`docs/discovery/DECISIONS.md` remain immutable legacy evidence; they do not
override these reconstruction decisions.

`INDEX.toml` is the machine-readable index. An accepted ADR is immutable at
its recorded SHA-256. A changed decision requires a new ADR that explicitly
supersedes the old one; history is never rewritten.

The initial decision set is:

- `MH-ADR-0001`: preserve, rebuild, or quarantine boundaries;
- `MH-ADR-0002`: target package ownership and dependency direction;
- `MH-ADR-0003`: verified vertical-slice migration;
- `MH-ADR-0004`: compatibility and deprecation policy;
- `MH-ADR-0005`: trust-base and evidence terminology.

Validate the set with:

```text
python tools/validate_reconstruction_adrs.py
```
