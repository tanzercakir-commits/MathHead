# Pinned Lean verification v1

MH-036 closes MathHead's first external proof-assistant loop. The accepted
boundary is `MH-C-LEAN-VERIFICATION-001` at SHA-256
`b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a`.
Writing Lean source is still non-authoritative. Only a fresh successful run of
the exact runner may return `external_proof_assistant` authority.

## Exact stack

- Lean selector: `leanprover/lean4:v4.33.0`
- Lean commit: `d8b18978322de05a8f3dba51ef03cf5461676c17`
- Linux x86_64 release archive SHA-256:
  `4b3fb03c29a1e0a253fb1d11f9bae3725f19a0dc6fc09b3ea16d2c9df3349e2c`
- mathlib commit: `db584cd6d46c92f209a44c0f1c829460d327499d`
- Transitive dependencies: nine exact Git commits in
  `lean/acquisition-lake-manifest.json`

The acquisition manifest is used only before verification. The runtime
`lakefile.toml` and `lake-manifest.json` contain local path dependencies, so
`lake env lean` cannot silently fetch or update a dependency during an
authority-bearing run. The committed lock binds both manifests, all dependency
commits, the release archive, and exact `lake` and `lean` executable digests.

## Boundary sequence

1. `build_lean_export` revalidates a fresh `MH-C-KERNEL-CHECKER-002`
   attestation and emits one canonical request plus seven content-addressed
   artifacts. Its status is `export_written` and its authority is `none`.
2. The generated source contains exactly one theorem for residue, CRT,
   finite-sum induction, or polynomial identity. It has a fixed import and no
   `sorry`, `admit`, `axiom`, `unsafe`, native oracle, foreign declaration, or
   caller-controlled identifier.
3. `verify_with_lean` independently rebuilds the request, validates fixed
   project and executable bytes, sanitizes the environment, removes only a
   safely validated stale output, and invokes the exact shell-free command.
4. `externally_verified` is issued only for exit code zero and a new, nonempty,
   bounded, single-link `.olean` artifact. Output and artifact bytes are
   retained and hashed.
5. `replay_lean_provenance` first freshly replays the complete MH-035 bundle,
   then requires byte-identical proof-term and checker-result objects before
   invoking Lean again. Stored result bytes are not an input and cannot refresh
   authority.

Historical result parsing is intentionally structural. A parsed successful
result can be audited, but `validate_lean_verification_result(...,
require_fresh=True)` rejects it because it did not arise from the current
process execution.

## Status algebra

| Status | Meaning | Authority |
| --- | --- | --- |
| `export_written` | Canonical source and request exist; Lean was not run | `none` |
| `check_unavailable` | Exact supported platform, project, or toolchain is absent | `none` |
| `check_failed` | Request, provenance, version, process, or theorem check failed | `none` |
| `check_exhausted` | Time or output ceiling was reached | `none` |
| `externally_verified` | Fresh exact Lean execution accepted the theorem | `external_proof_assistant` |

The legacy `mathhead.discovery.lean_export` functions now delegate theorem
eligibility and source generation to the canonical exporter. Their combined
file remains a compatibility view with
`export_written_pending_external_check` status and cannot be imported as
evidence.

## Validation

The ordinary structural suite does not install Lean:

```bash
python -m unittest discover -s tests/lean_verification -v
python tools/validate_lean_verification.py
python tools/contract_artifacts.py verify \
  --contract MH-C-LEAN-VERIFICATION-001 --require-bound
```

After preparing the exact toolchain and dependency cache, the Linux job runs:

```bash
python tools/validate_lean_verification.py --require-live
```

That command checks all nine dependency checkouts, compiles all four supported
proof rules, imports one result through fresh content-addressed provenance
dispatch, validates exact process artifacts, and proves that serialized
historical evidence cannot regain fresh authority. The repository-owned
`pinned Lean 4.33 external verification` GitHub Actions job performs the full
acquisition and live sequence on every pull request and `main` push.
