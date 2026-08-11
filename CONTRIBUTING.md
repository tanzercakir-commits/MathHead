# Contributing

Use the repository-owned profiles for development. Bootstrap once with
`python tools/dev.py bootstrap --profile core --venv .venv`, then run
`.venv/bin/python tools/dev.py check --profile core`. Documentation changes use the `docs`
profile, solver work uses the Linux-only `solver` profile, and
`python tools/project_status.py check` guards PLAN/TODO/PROGRESS transitions.

**The honesty rules are the contribution rules:**
1. Any new verdict path MUST carry an epistemic tier, and the tier must not overstate the evidence.
2. Witnesses must be self-verifying (exact arithmetic or independent re-checking) and tested.
3. If your feature can fail or run out of budget, it reports that honestly — no silent truncation.
4. Published code fences must be declared in `docs/examples.toml`; executable claims need exact
   pytest node IDs under one governed profile, while non-executable snippets need a reason.
