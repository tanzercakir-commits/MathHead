# Contributing to MathHead

Thanks for wanting to help. MathHead is a **verification engine**, so the bar is a little
unusual: correctness and *honesty about limits* matter more than breadth. A tool that returns a
clean `unknown` is better than one that guesses. Please read `PRINCIPLES.md` (the immutable
project rules) once before a first change — everything below is downstream of it.

## Development setup

```bash
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"        # z3, sympy, mcp, pytest, ruff, hypothesis
# optional, Linux-only: the SAT backends behind the [solvers] extra
pip install -e ".[dev,solvers]"
```

Python 3.10–3.12 are supported. `pytest -q` should be fully green on a clean checkout before you
start; if it isn't, that's a bug — please report it.

## The one hard rule: test-gated, then docs = code

Every change lands as a self-contained unit that is **green before it is committed**, and the
generated docs are regenerated in the *same* commit so they never drift:

```bash
ruff check .                       # style/lint gate (must be clean)
pytest -q                          # the whole suite (must be green)
python scripts/gen_api_reference.py   # regenerate docs/api-reference.md from the code
python scripts/gen_contract.py        # regenerate docs/mcp-contract.json (--check verifies)
```

`docs/api-reference.md` and `docs/mcp-contract.json` are **generated artifacts** — never edit
them by hand. A test enforces that they match the code (`code = docs`); if you add or change a
tool and forget to regenerate, CI fails.

## Adding or changing a tool

A tool touches a few layers in a fixed order — keep them consistent:

1. **Implement** the function in the right layer (`core/` for logic/Z3, `compute/` for
   SymPy/CAS, `frontier/` for SAT reductions, `certificate.py` for an independent re-checker).
   Return the layer's frozen result dataclass — `status` / `reason_code` / `explanation` /
   `meta`. **Do not** change that envelope (ADR-0004: it is frozen).
2. **Route** it in `router/__init__.py` (`_dispatch`). The public `route` wrapper then annotates
   `meta.certainty` and `meta.stability` for you — set the tool's tier in `certainty.py` if it is
   not the default.
3. **Expose** it as an `@mcp.tool()` in `server/mcp_server.py` with a docstring that states the
   grammar and the honest failure modes. Put it in the right capability pack — that is derived
   automatically in `profiles.py` from its stability tier + category, so usually you only set the
   tier.
4. **Parse safely.** If the tool takes an expression string, route it through the existing AST
   allowlist (`compute/_to_sympy` or the logic kernel's parser). **Never** call `sympify`,
   `eval`, or `exec` — see `docs/threat-model.md` for why this is non-negotiable.
5. **Test** it: a golden/regression case, the honest-wall case (what does it return when it
   *can't* decide?), and — for anything solver- or property-shaped — a Hypothesis property.
6. **Document the decision, not just the code.** If you made a real design choice, add an ADR to
   `DECISIONS.md` (next `ADR-XXXX`, with Context/Decision/Consequences). This is the antidote to
   context loss and it is expected, not optional.

## Honesty requirements (the ones reviewers will hold firm on)

- **No fabricated verdicts.** Undecidable / timed-out / out-of-fragment inputs return
  `unknown` / `bounded` / `error` with a truthful `reason_code`. Never return `valid` on a guess.
- **No metric gaming.** If coverage or a benchmark number falls short, report the real number and
  explain the gap — do not add a vacuous test to move it.
- **No silent caps.** If a code path bounds its work (top-N, sampling, a variable limit), that
  bound is surfaced in `meta` and in `resource_limits`, not hidden.
- **Determinism.** Same input → same *verdict* (a witness may vary; ADR-0019). Keep the fixed
  seed; don't introduce wall-clock- or `random`-dependent behavior into a verdict.

## Commits and pull requests

Conventional-commit style with the track tag we use in the log, e.g.
`feat(L4): document the timeout model honestly`. Reference the ADR if you added one. In the PR
description, say what you verified (which tests, which honest-wall cases) — "green on my machine"
plus the command you ran is enough. Small, single-purpose PRs review fastest.

## Reporting bugs

A soundness bug (a wrong verdict) is the highest priority — include the exact tool call and the
correct answer. For a *security* bug, follow `SECURITY.md` (report privately), don't open a
public issue.
