# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

**A deterministic verification & counterexample engine for AI-generated mathematics** —
callable by an AI (e.g. Claude) over **MCP**.

> **The problem it solves.** An LLM confidently tells you `(x²−1)/(x−1) = x+1`, or that
> `x²=4 ⟹ x=2`. Often *almost* right — and the "almost" is where trust dies. MathHead is the
> **independent checker**: hand it the claim, it verifies it deterministically with Z3 + SymPy,
> hands back a **counterexample** or an **independently-checkable certificate** when it can, and
> an honest **`unknown`** when it can't. It never bluffs.

## Status

**v1.0.x — the MCP contract is frozen; maturity is Beta.** MathHead is a **deterministic
verification engine for AI-generated mathematics**: given a claim an AI produced, it checks
it deterministically and returns a *counterexample* or an *independently-checkable
certificate* when it can — and an honest `unknown` when it can't.

- **Stable core** — the verification surface: `verify_*`, `cross_check`, `check_certificate`,
  entailment / consistency / model, and `prove_unsat` / `check_unsat_proof`.
- **Experimental extended** — the broad compute/CAS catalog, the frontier reductions, and
  observability. Useful and tested, but the surface may still change (per-tool stability is
  being made explicit).

**171 MCP tools** (curated down to a ~20-tool `core` profile by default — see *Tool profiles*),
a CLI, **1261 tests green** — deterministic verdicts, honest walls. Not yet published to PyPI;
install from source (below). Full history in `CHANGELOG.md`, plan in `ROADMAP.md`.

### Version vocabulary (separate on purpose)

| What | Version |
|---|---|
| Package (SemVer) | `1.0.x` |
| MCP contract (the supported surface) | `1` |
| Input grammar (logic kernel) | `1.2` |
| Extended tool packs | experimental |

The **MCP layer is the supported contract**. The `from mathhead.…` Python imports shown below
are convenience/internal — not covered by the package's SemVer promise (see
`docs/architecture.md`).

## Quick start

Once on PyPI: `pip install mathhead` (see `RELEASING.md`). For now, from source:

```bash
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

mathhead-server        # start the MCP server over stdio
pytest -q              # all tests green
```

## Three scenarios — why it exists

These are the cases where an AI's answer is *almost* right and MathHead catches the gap.
Shown via the Python convenience API for readability; the same checks are the MCP tools
`verify_equality`, `verify_solution`, `cross_check`, and `check_certificate`.

**1. The domain trap — "simplify" that quietly changes the function.**

```python
from mathhead.core.verify import verify_equality
verify_equality("(x**2-1)/(x-1)", "x+1")
# -> valid AS POLYNOMIALS, but flagged: x=1 is a hole (LHS undefined, RHS = 2).
#    The "obvious" cancellation an LLM does silently loses a point of the domain.
```

**2. The incomplete solution — a right answer that isn't the whole answer.**

```python
from mathhead.core.verify import verify_solution
verify_solution("x**2==4", "x", ["2"])          # -> invalid: INCOMPLETE (root -2 is missing)
verify_solution("x**2==4", "x", ["2", "-2"])    # -> valid: correct AND complete
```

**3. The independent certificate — a checker with no Z3 and no SymPy.**

```python
from mathhead.certificate import check_certificate   # stdlib only — a second, disjoint witness
check_certificate({"kind": "subset_sum", "numbers": [3,4,2], "target": 9, "indices": [0,1,2]})  # verified
check_certificate({"kind": "solution", "expression": "x**2 - 4", "symbol": "x", "value": "3"})  # refuted
```

When Z3 and SymPy might share a blind spot, `cross_check` runs both and reports
`ENGINES_DISAGREE` instead of picking a winner — and `check_certificate` re-derives the
result from scratch in plain Python, so the proof doesn't depend on the same libraries that
produced it.

**Everything else** — the full CAS (algebra, calculus, linear algebra, number theory,
combinatorics, statistics), the numerical methods, and the frontier SAT reductions — is
catalogued with signatures and examples in **`docs/api-reference.md`** (auto-generated from
the code, so it never drifts). Those tools live in the *experimental extended* surface and
are hidden behind the default profile; see below.

To connect it to an MCP client (e.g. Claude Code):

```bash
claude mcp add mathhead -- mathhead-server
```

Input language (grammar) and tool contract: `docs/mcp-api.md`.

From the terminal (CLI):

```bash
mathhead entail -p "p" -p "implies(p, q)" -c "q"          # -> valid
mathhead entail -p "forall(x, implies(Man(x), Mortal(x)))" \
                -p "Man(socrates)" -c "Mortal(socrates)"  # syllogism -> valid
mathhead prove -p "forall(x, implies(Man(x), Mortal(x)))" \
               -p "Man(socrates)" -c "Mortal(socrates)"   # + step-by-step proof
mathhead solve "x**2 == 4" x                              # -> ['-2', '2']
mathhead limit "sin(x)/x" x --point 0                     # -> 1
mathhead solve-system --eq "x + y == 10" --eq "x - y == 2" \
                      --sym x --sym y                     # -> [{'x':'6','y':'4'}]
mathhead det "1,2;3,4"                                    # -> -2
mathhead eigenvals "2,0;0,3"                              # -> eigenvalues + multiplicity
mathhead pigeonhole 4                                     # -> unsat (proof)
mathhead graph-coloring --edge 1,2 --edge 2,3 --edge 1,3 --colors 3   # -> sat (verified)
mathhead subset-sum 3 34 4 12 5 2 --target 9              # -> sat: {3,4,2}
mathhead --json consistent "x > 2" "x < 5"                # raw JSON
```

## Tool profiles — a small default, not a wall of 171

171 tools is too many for an AI to choose from well, so the server exposes a **profile** set
by the `MATHHEAD_PROFILE` environment variable. The default is **`core`**: the ~20-tool
verification surface, plus three always-present *triage* tools so an AI can still discover and
enable the rest.

| `MATHHEAD_PROFILE` | Exposes |
|---|---|
| *(unset)* / `core` | Verification core: `verify_*`, `cross_check`, entailment/consistency/model, `prove_unsat`/`check_unsat_proof`, certificates — **the default**. |
| `full` / `all` | Every one of the 171 tools. |
| e.g. `core,symbolic` | The core plus named packs: `logic`, `symbolic`, `numerical`, `frontier`, `observability`. |

```bash
MATHHEAD_PROFILE=full mathhead-server        # expose the whole catalog
```

The three triage tools are exposed under **every** profile, so discovery is never hidden:

- `list_capabilities` — the packs, each with a tool count and a sample.
- `describe_tool(name)` — full metadata for any tool (even one the current profile hides), so an AI knows what to turn on.
- `recommend_tool(query)` — a keyword match from a task description to candidate tools.

## Certainty & limits — where *not* to trust it

Every result carries two honesty signals in `meta` so a caller never has to guess how much
weight a verdict bears:

- `meta.certainty` — the epistemic strength of *this* answer: `formal_proof` ·
  `independent_certificate` · `solver_verified` · `bounded_check` · `symbolic_result` ·
  `numerical_check` · `unknown` · `error` · `not_applicable`. A `bounded_check` "valid" is a
  much weaker claim than an `independent_certificate` one, and it says so.
- `meta.stability` — how settled the *tool* is: `stable` (the frozen verification core) ·
  `provisional` · `experimental` · `internal`.

Honest limits, stated plainly:

- **Determinism is about the verdict, not the witness** (ADR-0019). The same input always
  yields the same *status*; a counterexample is *an* example and may differ between runs.
- **`unknown` is a real answer.** Undecidable fragments, solver timeouts, and out-of-fragment
  inputs return `unknown`/`bounded`/`error` — never a guessed `valid`. A wall is reported as a
  wall.
- **`numerical_check` results are sampled**, not proven; treat them as strong evidence, not a
  formal proof.
- **The extended surface may still change.** Only the `stable`-tier core is under the frozen
  MCP contract (`1`); experimental tools are useful and tested but not yet contract-frozen.

## Structure

```
mathhead/
├── README.md            · this file
├── Plan.md              · target architecture + roadmap (change-resistant)
├── Todo.md              · current work + priorities (changes often)
├── Progress.md          · what we did / when (append-only log)
├── PRINCIPLES.md        · immutable project rules (fence philosophy)
├── DECISIONS.md         · decision log (ADR) — so decisions aren't lost
├── SECURITY.md          · security policy + reporting + honest limits
├── CONTRIBUTING.md      · dev setup, test-gated/code=docs discipline, add-a-tool checklist
├── pyproject.toml       · dependencies (z3-solver, sympy, mcp[cli])
├── docs/
│   ├── architecture.md  · layer diagram (Mermaid) + request lifecycle
│   ├── mcp-api.md        · precise MCP protocol & tool definitions + grammar
│   ├── api-reference.md  · auto reference for ALL tools (code=docs)
│   ├── threat-model.md  · trust boundaries, threat table, the timeout model
│   ├── error-taxonomy.md · canonical list of every status/reason_code
│   └── glossary.md       · terms (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · logic (Z3) + verification (verify/crosscheck/inequality)
│   ├── certificate.py  · INDEPENDENT certificate checker (stdlib only, NO z3/sympy)
│   ├── compute/         · symbolic compute (SymPy)                
│   ├── router/          · routing
│   ├── guardrails/      · fence: validation, timeout, determinism
│   ├── profiles.py     · capability packs + triage (MATHHEAD_PROFILE)
│   └── server/          · MCP server (FastMCP, 171 tools; default `core` profile)
├── scripts/             · benchmark.py + gen_api_reference.py
├── benchmarks/          · LLM-trap set + harness (100% catch, Track C4)
└── tests/               · comprehensive test suite + fixtures/golden.json (regression fence)
```

## Where should I start reading?

`Plan.md` (big picture) → `docs/architecture.md` (layers) →
`docs/mcp-api.md` (contract) → `Todo.md` (next work item).

## License

Apache-2.0 — see `LICENSE`.
