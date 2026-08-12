# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

**Bring your conjecture — MathHead refutes it (with a witness), proves it (with a kernel proof),
or tells you exactly how far it survived.** A deterministic mathematics engine with an honesty
contract: **every verdict carries its epistemic tier.**

<!-- mathhead-non-executable: readme-overview-install | requires network and optional system package installation -->
```console
$ pip install "mathhead[solvers] @ git+https://github.com/tanzercakir-commits/MathHead"
$ # (PyPI release pending — until then, install from git.)  + `apt install nauty` for scale
```

<!-- mathhead-example: readme-overview-divisibility -->
```console
$ mathhead-discover check "6 | n^3 - n"
VERDICT: proved   [kernel_verified]
  proof     : kernel hash 7b24fe07c5c0df35
```

<!-- mathhead-example: readme-overview-graph-refutation -->
```console
$ mathhead-discover check "num_triangles <= num_edges" --max-n 6
VERDICT: refuted   [exact_integer_certificate]
  witness   : n=6 graph with num_triangles=16 > num_edges=14
```

<!-- mathhead-example: readme-overview-r35 -->
```console
$ mathhead-discover bracket 3 5 --lo 13 --hi 14 --strengthen
n=13: SAT   [independently_verified_witness]  → R(3,5) > 13
n=14: UNSAT [independently_verified_unsat_proof_of_strengthened_formula]  → R(3,5) <= 14
R(3,5) = 14
```

**What it can do today** (each claim CI-tested): prove modular facts and sum identities by
replaying immutable proof terms in a dependency-minimal exact checker; refute conjectures
counterexample-first over ALL connected graphs (nauty-scale, exact invariants incl. α, γ, ν,
girth, diameter); certify spectral counterexamples in **pure integer arithmetic** (no floats in
any verdict); bracket Ramsey numbers — R(3,3)=6 · R(3,4)=9 · R(3,5)=14 · R(4,4)=18 — with
independently re-verified SAT witnesses and independently RUP-checked UNSAT proofs; hunt live on open problems (Frankl union-closed) with
honest `not_found_within_budget` outcomes; run PSLQ constant-relation searches with a
two-precision protocol; export kernel theorems to Lean 4 for external cross-sealing.

**The honesty contract** — the tier rides every verdict, strongest first:

| tier | meaning |
|---|---|
| `kernel_verified` | universal machine proof in the LCF-style kernel (+ proof hash) |
| `exact_integer_certificate` | self-verifying witness, pure integer arithmetic |
| `independently_verified_witness` | solver output re-checked by brute force, no solver in the loop |
| `independently_verified_unsat_proof(_of_strengthened_formula)` | DRUP refutation re-checked by a pure-Python RUP checker; the `strengthened` variant says the proof is of base + derived lemmas, not the bare encoding |
| `solver_verified(_with_derived_lemmas)` | solver verdict; any added lemmas are listed on the verdict |
| `constructive_bounded` / `interval_certified` | explicit witness / certified enclosure, sample-bounded |
| `numerical_conjecture` / `empirical` | evidence, **never** presented as proof |
| `no_counterexample_within_bound` | survived exhaustive attack to the stated bound — honestly open |

It never bluffs: unsupported input is refused with suggestions, unfinished hunts say so, and
nothing is ever labelled stronger than what was actually checked.

---

## The verification core (MCP)

**A deterministic verification & counterexample engine for AI-generated mathematics** —
callable by an AI (e.g. Claude) over **MCP**.

> **The problem it solves.** An LLM confidently tells you `(x²−1)/(x−1) = x+1`, or that
> `x²=4 ⟹ x=2`. Often *almost* right — and the "almost" is where trust dies. MathHead is the
> **independent checker**: hand it the claim, it verifies it deterministically with Z3 + SymPy,
> hands back a **counterexample** or an **independently-checkable certificate** when it can, and
> an honest **`unknown`** when it can't. It never bluffs.

## Status

The MCP contract is frozen at compatibility level `1`; package maturity is Beta. MathHead is a **deterministic
verification engine for AI-generated mathematics**: given a claim an AI produced, it checks
it deterministically and returns a *counterexample* or an *independently-checkable
certificate* when it can — and an honest `unknown` when it can't.

- **Stable core** — the verification surface: `verify_*`, `cross_check`, `check_certificate`,
  entailment / consistency / model, and `prove_unsat` / `check_unsat_proof`.
- **Experimental extended** — the broad compute/CAS catalog, the frontier reductions, and
  observability. Useful and tested, but the surface may still change (per-tool stability is
  being made explicit).

<!-- BEGIN MATHHEAD PROJECT FACTS -->
**Package `1.5.0` · 171 MCP tools · 2673 collected tests.**  
Governed profiles: `status`, `runtime`, `core`, `solver`, `discovery`, `docs`, `live-mcp`, `slow`, `release`.  
Product Python matrix: 3.10, 3.11, 3.12, 3.13, 3.14.
<!-- END MATHHEAD PROJECT FACTS -->

The full MCP catalog is curated down to a small `core` profile by default (see *Tool profiles*).
The project also ships a CLI. It is not yet published to PyPI; install from source (below).
Full history is in `CHANGELOG.md`; reconstruction governance is in `docs/PLAN.md`.
The reconstruction target's first structured boundary is the non-authoritative,
syntax-neutral ProblemIR intake API documented in `docs/PROBLEM_INTAKE_V1.md`.
Declared alternatives then pass through the deterministic, non-selecting
reading analysis documented in `docs/PROBLEM_READINGS_V2.md`. Each reading's
declared domains and assumptions then become a separate source-backed fact
inventory under `docs/DOMAIN_ASSUMPTIONS_V1.md`; unsupported structures remain
visible. The exact goals finally become independent typed dependency graphs
under `docs/PROOF_OBLIGATIONS_V1.md`; choices and symbolic witness duties stay
explicit. Those graphs then receive capture-safe, catalogue-limited comparison
identities and reversible occurrence traces under
`docs/CANONICAL_NORMALIZATION_V1.md`. Source topology remains exact, readings
remain separate. Explicitly unsupported occurrences then receive exact,
source-backed owner boundaries and conservative caller-confirmed next steps
under `docs/UNSUPPORTED_EXPLANATIONS_V1.md`. No stage grants mathematical
authority or promises a runtime capability. The complete artifact chain can
then be retained as a content-addressed, replayable revision history with
deterministic dependency invalidation and an atomic non-authoritative store as
documented in `docs/PROBLEM_SESSIONS_V1.md`.

### Version vocabulary (separate on purpose)

| What | Version |
|---|---|
| Package (SemVer) | generated above from the package source |
| MCP contract (the supported surface) | `1` |
| Input grammar (logic kernel) | `1.2` |
| Extended tool packs | experimental |

The **MCP layer is the supported contract**. The `from mathhead.…` Python imports shown below
are convenience/internal — not covered by the package's SemVer promise (see
`docs/architecture.md`).

## Quick start

Once on PyPI: `pip install mathhead` (see `RELEASING.md`). For now, from source:

<!-- mathhead-non-executable: readme-posix-setup | platform-specific setup and long-running server launch -->
```bash
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python tools/dev.py bootstrap --profile core --venv .venv
.venv/bin/python tools/dev.py check --profile core
.venv/bin/mathhead-server        # start the MCP server over stdio
```

On Windows PowerShell, the equivalent governed commands are:

<!-- mathhead-non-executable: readme-windows-setup | platform-specific setup and long-running server launch -->
```powershell
py tools/dev.py bootstrap --profile core --venv .venv
.venv\Scripts\python.exe tools/dev.py check --profile core
.venv\Scripts\mathhead-server.exe
```

`status`, `runtime`, `core`, `solver`, `docs`, and `release` are explicit
profiles in `tools/dev_profiles.json`. `describe` reports a profile without
claiming it passed; `check` is offline; only `bootstrap` and `clean-smoke` may
use the network. The Linux-only `solver` profile refuses unsupported platforms
instead of silently skipping its required backend. Tests that require
`python-sat` or nauty are labeled `requires_solver`; the core profile neither
installs nor imports `python-sat`. Linux distributions may expose nauty's
generator as either `nauty-geng` or `geng`, and the solver profile accepts only
those explicit alternatives.

## Three scenarios — why it exists

These are the cases where an AI's answer is *almost* right and MathHead catches the gap.
Shown via the Python convenience API for readability; the same checks are the MCP tools
`verify_equality`, `verify_solution`, `cross_check`, and `check_certificate`.

**1. The domain trap — "simplify" that quietly changes the function.**

<!-- mathhead-example: readme-domain-trap -->
```python
from mathhead.core.verify import verify_equality
verify_equality("(x**2-1)/(x-1)", "x+1")
# -> valid AS POLYNOMIALS, but flagged: x=1 is a hole (LHS undefined, RHS = 2).
#    The "obvious" cancellation an LLM does silently loses a point of the domain.
```

**2. The incomplete solution — a right answer that isn't the whole answer.**

<!-- mathhead-example: readme-incomplete-solution -->
```python
from mathhead.core.verify import verify_solution
verify_solution("x**2==4", "x", ["2"])          # -> invalid: INCOMPLETE (root -2 is missing)
verify_solution("x**2==4", "x", ["2", "-2"])    # -> valid: correct AND complete
```

**3. The independent certificate — a checker with no Z3 and no SymPy.**

<!-- mathhead-example: readme-independent-certificate -->
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

<!-- mathhead-non-executable: readme-external-client | requires the external Claude client -->
```bash
claude mcp add mathhead -- mathhead-server
```

Input language (grammar) and tool contract: `docs/mcp-api.md`.

From the terminal (CLI):

<!-- mathhead-example: readme-cli-catalog -->
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

## Tool profiles — a small default, not the full catalog

The full catalog is too broad for reliable tool selection, so the server exposes a **profile** set
by the `MATHHEAD_PROFILE` environment variable. The default is **`core`**: the ~20-tool
verification surface, plus three always-present *triage* tools so an AI can still discover and
enable the rest.

| `MATHHEAD_PROFILE` | Exposes |
|---|---|
| *(unset)* / `core` | Verification core: `verify_*`, `cross_check`, entailment/consistency/model, `prove_unsat`/`check_unsat_proof`, certificates — **the default**. |
| `full` / `all` | Every tool in the generated current catalog. |
| e.g. `core,symbolic` | The core plus named packs: `logic`, `symbolic`, `numerical`, `frontier`, `observability`. |

<!-- mathhead-non-executable: readme-server-launch | long-running server process -->
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

<!-- mathhead-non-executable: readme-repository-tree | illustrative repository layout rather than executable code -->
```
mathhead/
├── README.md            · this file
├── docs/PLAN.md         · target architecture + roadmap (change-resistant)
├── docs/TODO.md         · current work + priorities (automated)
├── docs/PROGRESS.md     · append-only execution evidence (automated)
├── PRINCIPLES.md        · immutable project rules (fence philosophy)
├── DECISIONS.md         · decision log (ADR) — so decisions aren't lost
├── SECURITY.md          · security policy + reporting + honest limits
├── CONTRIBUTING.md      · dev setup, test-gated/code=docs discipline, add-a-tool checklist
├── pyproject.toml       · dependencies (z3-solver, sympy, mcp[cli])
├── docs/
│   ├── architecture.md  · layer diagram (Mermaid) + request lifecycle
│   ├── PROOF_TERMS_V1.md · immutable canonical proof terms + authority boundary
│   ├── KERNEL_CHECKER_V1.md · historical exact checker + v1 replay ABI
│   ├── KERNEL_CHECKER_V2.md · explicit arithmetic evidence + current replay ABI
│   ├── SAT_REPLAY_V1.md · canonical SAT witnesses + RUP-only DRUP replay
│   ├── PROVENANCE_REPLAY_V1.md · content-addressed whole-run replay + atomic store
│   ├── DOMAIN_ASSUMPTIONS_V1.md · per-reading declared fact inventory + frozen rules
│   ├── PROOF_OBLIGATIONS_V1.md · typed goal graphs + local contexts + strategy hints
│   ├── mcp-api.md        · precise MCP protocol & tool definitions + grammar
│   ├── api-reference.md  · auto reference for ALL tools (code=docs)
│   ├── threat-model.md  · trust boundaries, threat table, the timeout model
│   ├── trust/           · machine-readable TCB inventory, schema, and frozen import report
│   ├── error-taxonomy.md · canonical list of every status/reason_code
│   └── glossary.md       · terms (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · logic (Z3) + verification (verify/crosscheck/inequality)
│   ├── kernel/          · immutable proof terms + dependency-minimal exact checker
│   ├── legacy_kernel_adapter.py · non-authoritative migration into proof terms
│   ├── certificate.py  · INDEPENDENT certificate checker (stdlib only, NO z3/sympy)
│   ├── compute/         · symbolic compute (SymPy)                
│   ├── router/          · routing
│   ├── guardrails/      · fence: validation, timeout, determinism
│   ├── profiles.py     · capability packs + triage (MATHHEAD_PROFILE)
│   └── server/          · MCP server (FastMCP; generated full count, default `core` profile)
├── scripts/             · gen_api_reference.py + gen_contract.py (code=docs generators)
├── benchmarks/          · LLM-trap catch-rate (23 errors, 100%) + tool-selection accuracy harness
└── tests/               · comprehensive test suite + fixtures/golden.json (regression fence)
```

## Where should I start reading?

`docs/PLAN.md` (big picture) → `docs/architecture.md` (layers) →
`docs/mcp-api.md` (contract) → `docs/TODO.md` (next work item).

## License

Apache-2.0 — see `LICENSE`.
