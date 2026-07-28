# MathHead

![CI](https://github.com/tanzercakir-commits/MathHead/actions/workflows/ci.yml/badge.svg)

A **deterministic**, first-order-logic-based math reasoning and proof engine that
AI (e.g. Claude) can invoke over **MCP**.

> **Idea:** LLMs are unreliable at rigorous logic/proof (non-deterministic,
> assumption-prone). MathHead offloads this work to a real engine (SMT solver
> **Z3** + symbolic compute **SymPy**), shrinking the room for "making things up".

## Status

**v1.0 — API frozen and stable.** The logic core (Z3) + compute/calculus/linear
algebra/number theory/combinatorics/probability (SymPy) + the **verification layer**
(audits AI reasoning) + **logic & proof depth** (induction, SMT theories — bit-vectors/
arrays/strings/EUF, quantifier elimination, modal logic) + the **frontier** (SAT
reductions, a verifiable **UNSAT certificate**, a high-performance CaDiCaL backend) +
holistic performance/observability: **168 MCP tools**, a CLI, and **1236 tests green**.
Every result is deterministic in verdict and honest about its walls. The full history is
in `CHANGELOG.md`, the phased plan in `ROADMAP.md` (Tracks A–K complete).

## Quick start

Once on PyPI: `pip install mathhead` (see `RELEASING.md`). For now, from source:

```bash
git clone https://github.com/tanzercakir-commits/MathHead && cd MathHead
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

mathhead-server        # start the MCP server over stdio
pytest -q              # all tests green
```

## Usage (v1)

From Python:

```python
from mathhead.core import check_entailment, check_consistency, find_model

check_entailment(["p", "implies(p, q)"], "q")   # -> status="valid"
check_entailment(["x > 0"], "x > 5")             # -> "invalid", witness={"x": 1}
check_consistency(["p", "not(p)"])               # -> "unsat" + unsat core
find_model(["x > 2", "x < 5"])                    # -> "sat", witness={"x": 3}

from mathhead.core.inequality import prove_inequality   # v2+ (Z3 NRA, nonlinear)
prove_inequality("x**2 + y**2 >= 2*x*y")          # -> "valid"  (AM-GM, proof)
prove_inequality("x**2 >= x")                     # -> "invalid", witness={"x": 0.5}

from mathhead.core.verify import verify_equality, verify_solution  # VERIFICATION (AI auditor)
verify_equality("(x**2-1)/(x-1)", "x+1")          # -> valid, BUT domain warning (x=1 undefined!)
verify_solution("x**2==4", "x", ["2"])            # -> invalid: INCOMPLETE (-2 missed)
verify_solution("x**2==4", "x", ["2","-2"])       # -> valid: correct + complete

from mathhead.core.crosscheck import cross_check  # CROSS-CHECK (Z3 ⋈ SymPy)
cross_check("(x+1)**2", "x**2 + 2*x + 1")         # -> CONSENSUS_EQUAL (both engines agree)
cross_check("(x**2-1)/(x-1)", "x+1")              # -> ENGINES_DISAGREE (domain-trap flag!)

from mathhead.core.verify import verify_derivative, verify_integral, verify_limit  # AI claim auditing
verify_derivative("x**3", "x", "3*x**2")          # -> valid (derivative correct)
verify_integral("2*x", "x", "x**2 + 5")           # -> valid (+C constant difference tolerated)
verify_limit("sin(x)/x", "x", "0", "1")           # -> valid (limit correct)

from mathhead.core.nl import interpret            # NATURAL LANGUAGE → formal (recognize-or-reject)
interpret("x**3 ifadesinin x e göre türevi")      # -> UNDERSTOOD + "what I understood" (confirm-then-trust)
interpret("anlamsız cümle")                       # -> UNRECOGNIZED (NO GUESSING)

from mathhead.certificate import check_certificate  # INDEPENDENT checker (NO z3/sympy)
check_certificate({"kind":"subset_sum","numbers":[3,4,2],"target":9,"indices":[0,1,2]})  # verified
check_certificate({"kind":"solution","expression":"x**2 - 4","symbol":"x","value":"3"})  # refuted

from mathhead.compute import solve, differentiate, integrate   # v2 (SymPy)
solve("x**2 == 4", "x")                           # -> ["-2", "2"]
differentiate("x**3 + 2*x", "x")                  # -> "3*x**2 + 2"
integrate("2*x", "x")                             # -> "x**2"

from mathhead.compute import limit, series, solve_system       # v2+ (calculus)
limit("sin(x)/x", "x", "0")                       # -> "1"
limit("1/x", "x", "oo")                           # -> "0"
series("exp(x)", "x", "0", 5)                     # -> "x**4/24 + x**3/6 + x**2/2 + x + 1"
solve_system(["x + y == 10", "x - y == 2"], ["x", "y"])   # -> [{"x": "6", "y": "4"}]

from mathhead.compute import determinant, matrix_inverse, eigenvalues   # v2+ (linear algebra)
determinant([["a", "b"], ["c", "d"]])             # -> "a*d - b*c" (symbolic)
matrix_inverse([["1", "2"], ["3", "4"]])          # -> [["-2","1"],["3/2","-1/2"]]
matrix_inverse([["1", "2"], ["2", "4"]])          # -> error: not invertible (honest)
eigenvalues([["2", "0"], ["0", "3"]])             # -> [{"value":"2",...},{"value":"3",...}]

from mathhead.compute import matrix_multiply, matrix_solve, nullspace   # v2+ (linear algebra II)
matrix_multiply([["1","2"],["3","4"]], [["5","6"],["7","8"]])  # -> [["19","22"],["43","50"]]
matrix_solve([["1","1"],["1","-1"]], ["10","2"]) # -> [{"x0":"6","x1":"4"}]  (Ax=b)
matrix_solve([["1","1"],["1","1"]], ["1","2"])   # -> []  (inconsistent → no solution, honest)
nullspace([["1","2"],["2","4"]])                  # -> [["-2","1"]]  (null space basis)

from mathhead.compute import gcd, factorize, modular_inverse, chinese_remainder  # v2+ (number theory)
gcd(48, 36)                                       # -> 12
factorize(360)                                    # -> 2^3 · 3^2 · 5
modular_inverse(3, 11)                            # -> 4  (3·4 ≡ 1 mod 11)
modular_inverse(4, 8)                             # -> error: no inverse (gcd≠1, honest)
chinese_remainder([3,5,7], [2,3,2])               # -> {"x": 23, "modulus": 105}

from mathhead.compute import combinations, factorial, solve_recurrence  # v2+ (combinatorics)
combinations(49, 6)                               # -> 13983816  (lottery)
factorial(10)                                     # -> 3628800
solve_recurrence("y(n) = y(n-1) + y(n-2)",        # -> Fibonacci closed form (Binet)
                 "y", "n", {"0": "0", "1": "1"})

from mathhead.compute import gradient, summation, solve_ode  # v2+ (multivariable analysis)
gradient("x**2*y + sin(y)", ["x", "y"])           # -> ["2*x*y", "x**2 + cos(y)"]
summation("i", "i", "1", "n")                     # -> "n**2/2 + n/2"  (closed form)
solve_ode("y'' + y = 0")                          # -> Eq(y(x), C1*sin(x) + C2*cos(x))

from mathhead.compute import mean, distribution   # v2+ (probability & statistics)
mean(["2", "4", "4", "5", "5"])                   # -> "4"
distribution("binomial", ["10", "1/2"], at="3")   # -> {mean:5, variance:5/2, cdf_at:11/64, ...}
distribution("normal", ["mu", "sigma"])           # -> {mean:"mu", variance:"sigma**2", ...}
```

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

## Structure

```
mathhead/
├── README.md            · this file
├── Plan.md              · target architecture + roadmap (change-resistant)
├── Todo.md              · current work + priorities (changes often)
├── Progress.md          · what we did / when (append-only log)
├── PRINCIPLES.md        · immutable project rules (fence philosophy)
├── DECISIONS.md         · decision log (ADR) — so decisions aren't lost
├── pyproject.toml       · dependencies (z3-solver, sympy, mcp[cli])
├── docs/
│   ├── architecture.md  · layer diagram (Mermaid) + request lifecycle
│   ├── mcp-api.md        · precise MCP protocol & tool definitions + grammar
│   ├── api-reference.md  · auto reference for ALL tools (code=docs)
│   ├── error-taxonomy.md · canonical list of every status/reason_code
│   └── glossary.md       · terms (FOL, SMT, CAS, entailment...)
├── src/mathhead/
│   ├── core/            · logic (Z3) + verification (verify/crosscheck/inequality)
│   ├── certificate.py  · INDEPENDENT certificate checker (stdlib only, NO z3/sympy)
│   ├── compute/         · symbolic compute (SymPy)                       [v2+]
│   ├── router/          · routing
│   ├── guardrails/      · fence: validation, timeout, determinism
│   └── server/          · MCP server (FastMCP, 168 tools)
├── scripts/             · benchmark.py + gen_api_reference.py
├── benchmarks/          · LLM-trap set + harness (100% catch, Track C4)
└── tests/               · comprehensive test suite + fixtures/golden.json (regression fence)
```

## Where should I start reading?

`Plan.md` (big picture) → `docs/architecture.md` (layers) →
`docs/mcp-api.md` (contract) → `Todo.md` (next work item).

## License

Apache-2.0 — see `LICENSE`.
