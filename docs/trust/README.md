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
`d93d09a044430ec2ae97ca915ee9d592814c025e9277b91ac927f60d9d83ace7`.

## Current result

The static boundary contains 117 Python modules, 32 non-`mathhead` import
roots, 24 classified trust surfaces, and seven supported entry points. Every
source module and import edge is represented in the deterministic report. A
new source file, import edge, import root, dynamic import call, effect owner,
entry-point closure, or trust classification changes the report and therefore
fails the checked repository state until it is deliberately reviewed.

The important current distinctions are:

| Boundary | Current authority | P3 disposition |
|---|---|---|
| Z3 and SymPy | solver verdict | producer-side; independent promotion requires evidence replay |
| PySAT and nauty | producer report | retain outside the checker and bind exact encodings or output |
| `certificate.py` | checker attestation, with a visible approximate legacy branch | split exact typed certificates from numerical checks in MH-032/MH-033 |
| `drat.py` and `discovery/rup_check.py` | two checker-attested RUP/DRUP boundaries | unify and harden one versioned streaming checker in MH-034 |
| `discovery/kernel.py` | checker attestation under a Python LCF-style guard | replace forgeable theorem objects and expose derived evidence in MH-031/MH-033 |
| SHA-256 and canonical JSON | identity only | centralize full content and replay identities in MH-035 |
| Lean export | no current authority | grant authority only after pinned external replay in MH-036 |
| MCP, CLI, workers, filesystem, clock, random, dynamic import | none | keep outside the checker and red-team transitions in MH-037 |

The report also preserves two current import cycles rather than hiding them:
the `profiles`/`router`/MCP cycle and the discovery
`__init__`/`formalize`/`product` cycle. Inventory validity describes these
facts; it does not certify the Python runtime, arithmetic, solver, checker, or
proof-assistant implementation as sound.

## Minimal checker target

The MH-032 target is capped at 12 modules and nine standard-library roots. It
permits only declared exact value, rational, digest, canonical JSON, Unicode,
and integer-combinatorial primitives. Third-party packages, dynamic imports,
filesystem and process effects, environment reads, network transport, clocks,
randomness, and floating-point or solver authority are all explicitly denied.

That target is a budget and allowlist, not a claim that the new kernel already
exists. MH-031 through MH-037 own every migration in an acyclic order.

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
