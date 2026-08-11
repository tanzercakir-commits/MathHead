# Trusted computing base inventory

MH-030 turns MathHead's trust claims into a checked repository artifact instead
of leaving them distributed across module docstrings and result labels. The
normative inventory is `trust-base-v1.json`; its closed Draft 2020-12 schema is
`trust-base-v1.schema.json`, and `reports/trust-base-v1.json` is the frozen
static analysis result.

The inventory is governed by accepted contract `MH-C-TRUST-BASE-001` at
SHA-256
`2d2c23da4d3b167c5220c7548602f11403af7634031c438a8f61ac8e3e191456`.
Its self-identity is
`32cfc97dcb545bdfa48f3d4b883e8e0195fc645f4963440a28fd5b6ee5a33064`.

## Current result

The static boundary contains 123 Python modules, 32 non-`mathhead` import
roots, 24 classified trust surfaces, and nine supported entry points. Every
source module and import edge is represented in the deterministic report. A
new source file, import edge, import root, dynamic import call, effect owner,
entry-point closure, or trust classification changes the report and therefore
fails the checked repository state until it is deliberately reviewed.

The important current distinctions are:

| Boundary | Current authority | P3 disposition |
|---|---|---|
| Z3 and SymPy | solver verdict | producer-side; independent promotion requires evidence replay |
| PySAT and nauty | producer report | retain outside the checker and bind exact encodings or output |
| `certificate.py` | legacy mixed exact and approximate checking; cannot issue the new immutable attestation | separate remaining numerical evidence in MH-033 |
| `kernel/sat.py` | immutable checker attestation for canonical SAT assignments and RUP-only DRUP | one versioned boundary; DRAT/RAT is explicitly unsupported |
| `drat.py` and `discovery/rup_check.py` | legacy result shapes only | non-authoritative adapters to `kernel/sat.py` |
| `discovery/kernel.py` | legacy checker attestation under a Python LCF-style guard | compatibility only; its forgeable `Theorem` cannot cross the new boundary |
| `kernel/proof_terms.py` | structural validity only, no mathematical authority | constructor-controlled closed values and canonical parsing implemented in MH-031 for MH-032 replay |
| `kernel/checkers.py` | immutable checker attestation after exact independent replay | active MH-032 authority boundary; five internal modules and seven stdlib roots |
| SHA-256 and canonical JSON | identity only | centralize full content and replay identities in MH-035 |
| Lean export | no current authority | grant authority only after pinned external replay in MH-036 |
| MCP, CLI, workers, filesystem, clock, random, dynamic import | none | keep outside the checker and red-team transitions in MH-037 |

The report also preserves two current import cycles rather than hiding them:
the `profiles`/`router`/MCP cycle and the discovery
`__init__`/`formalize`/`product` cycle. Inventory validity describes these
facts; it does not certify the Python runtime, arithmetic, solver, checker, or
proof-assistant implementation as sound.

## Minimal checker target

The MH-032 target is capped at 12 modules and nine standard-library roots. The
proof-term checker closure uses five modules and seven standard-library roots;
the SAT replay checker uses one module and five standard-library roots. It
permits only declared exact value, rational, digest, canonical JSON, Unicode,
and integer-combinatorial primitives. Third-party packages, dynamic imports,
filesystem and process effects, environment reads, network transport, clocks,
randomness, and floating-point or solver authority are all explicitly denied.

The accepted proof-term and SAT replay contracts and result schemas are bound
into the inventory. Legacy SAT adapters import the checker but cannot construct
its immutable result or grant authority independently. MH-031 through MH-037
own every migration in an acyclic order.

## Commands

Check the frozen report and focused adversarial tests:

```bash
python tools/validate_trust_base.py
python -m unittest discover -s tests/trust_base -v
```

After a deliberate trust-boundary review, regenerate the report and then
re-run the same checks:

```bash
python tools/validate_trust_base.py \
  --write-report docs/trust/reports/trust-base-v1.json
python tools/validate_trust_base.py
```

Report generation statically parses Python source. It does not import
`mathhead`, Z3, SymPy, PySAT, mpmath, MCP, or Lean and does not execute a
solver, subprocess, worker, or network request. Dependency-minimal and
full-`jsonschema` profiles produce identical report bytes, including in a
relocated checkout.
