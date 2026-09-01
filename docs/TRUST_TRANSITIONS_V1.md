# Trust-tier transitions and the G3 boundary

MH-037 closes P3 with an explicit, fail-closed policy for moving evidence
between MathHead's authority tiers. The accepted contract is
`MH-C-TRUST-TRANSITION-001` at SHA-256
`7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796`.
Its production entry point is
`mathhead.kernel.trust_transitions.audit_trust_transition`.

The auditor answers one narrow question: do the exact attempt, catalogue, and
artifact bytes satisfy the frozen transition policy? Its result always has
`mathematical_authority: false`. It does not prove a statement, validate a SAT
certificate, replay provenance, invoke Lean, refresh stored evidence, or turn a
digest or successful process into authority.

## Frozen lattice and edges

The declared lattice, in order, is `none`, `producer_report`,
`solver_verdict`, `checker_attestation`, and `external_proof_assistant`.
The catalogue deliberately has no current edge that issues `solver_verdict`:
legacy Z3 and SymPy verdict labels are bounded to `producer_report` until an
independently replayable solver contract is introduced.

The eleven permitted policy edges are:

| Source | Operation | Target | Issuer boundary |
|---|---|---|---|
| `none` | issue | `producer_report` | approximate arithmetic |
| `none` | issue | `producer_report` | nauty producer |
| `none` | issue | `producer_report` | SymPy producer |
| `none` | issue | `producer_report` | Z3 producer |
| `none` | issue | `checker_attestation` | proof-term checker |
| `none` | issue | `checker_attestation` | SAT replay checker |
| `producer_report` | issue | `checker_attestation` | SAT replay checker |
| `checker_attestation` | preserve | `checker_attestation` | fresh proof provenance replay |
| `checker_attestation` | preserve | `checker_attestation` | fresh SAT provenance replay |
| `checker_attestation` | issue | `external_proof_assistant` | fresh pinned Lean execution |
| `external_proof_assistant` | preserve | `external_proof_assistant` | fresh provenance plus Lean replay |

Every failed prerequisite falls to `none`. There is no label-based fallback,
implicit transitivity, deserialization promotion, or process-success shortcut.
Each allowed attempt binds the issuer component, entry point, role, accepted
contract, implementation bytes, configuration bytes, subject bytes, required
contract bytes, complete evidence and budget state, allowed status, freshness,
and independence where required.

## Effects cannot issue authority

The catalogue separately freezes eleven effect surfaces. Approximate
arithmetic, nauty, SymPy, and Z3 are capped at `producer_report`; dynamic
imports, subprocesses, workers, clocks, randomness, CLI, and MCP are capped at
`none`. The static audit finds strong-tier literals and the five actual issuer
entry points, then scans every source path owned by those effects for an
unclassified route to an issuer. The clock-bearing legacy DRUP module is
explicitly classified as a non-authoritative adapter to the SAT checker; its
clock and legacy result shape do not mint the checker's closed result.

## Mutation and semantic replay

The normative catalogue contains 45 deterministic attacks. It covers malformed
and noncanonical JSON, duplicate and unknown fields, wrong tier and operation,
issuer/component/contract/source/configuration substitution, stale or aliased
issuers, incomplete evidence and budgets, missing/extra/changed artifacts,
backend disagreement, all eleven effect surfaces, forged proof objects, false
proof claims, false and truncated SAT evidence, trailing certificate data,
corrupted provenance, repaired outer hashes around substituted checker source,
and stale or substituted Lean material.

There are two intentionally separate checks:

- The pure policy auditor kills byte, identity, status, freshness,
  independence, catalogue, and artifact-policy mutations.
- The real proof, SAT, provenance, export, and Lean request boundaries kill
  semantic mutations. A caller that changes a subject and consistently repairs
  every outer hash cannot be detected by hashing alone; independent replay is
  the required control.

## Frozen G3 evidence

The normative catalogue is
`docs/trust/trust-transition-catalogue-v1.json`. The canonical G3 report is
`docs/trust/reports/trust-transition-g3-v1.json`; it binds the accepted
contract and four schemas, complete source snapshot, generator, issuer sites,
all transitions, positive controls, mutations, effects, outcomes, and totals.
`g3_passed` is true only when all eleven controls pass, all 45 mutants are
killed with their exact expected result, every effect is classified, and no
survivor or static violation exists.

Validate or deliberately regenerate the evidence with:

```bash
python tools/validate_trust_transitions.py
python -m unittest discover -s tests/trust_transitions -v
python tools/contract_artifacts.py verify \
  --contract MH-C-TRUST-TRANSITION-001 --require-bound

python tools/validate_trust_transitions.py \
  --write-catalogue docs/trust/trust-transition-catalogue-v1.json \
  --write-report docs/trust/reports/trust-transition-g3-v1.json
```

The ordinary validator is deterministic and performs no live network access.
Pinned live Lean compilation remains a distinct exact-head CI gate governed by
MH-036; the G3 report binds the local transition and adversarial evidence
without pretending that a stored CI status refreshes external authority.
