# MathHead — Plan

> **This file's job:** to preserve the project's *target architecture* and *roadmap*.
> It is change-resistant; not updated often. Immediate work is in `Todo.md`, what we've done
> in `Progress.md`, the rationale of decisions in `DECISIONS.md`.
> (The Plan ≠ Todo distinction comes from your working principles.)

---

## 0. In one sentence

A system where AI delegates its mathematical **reasoning and proof**, instead of doing it
in its own head (non-deterministic, assumption-prone), to a **deterministic** engine
(SMT solver **Z3** + symbolic compute **SymPy**) over **MCP**.

---

## 1. Why does it exist? (the real problem it solves)

LLMs are strong at language work but unreliable at rigorous logic/proof: they take an invalid
inference step, make numeric/algebraic errors, look "sure" and get it wrong. The 3 walls you
hit with AI are the root cause of this. MathHead **offloads math to a real engine**, giving an
architectural answer to all three walls at once:

| Wall | MathHead's answer |
|---|---|
| **#1 Context loss** | The `Plan/Todo/Progress/DECISIONS` discipline + traceable `meta` on every response (which solver, which version, how long it took). Decisions aren't lost in `DECISIONS.md`. |
| **#2 Over-assumption** | The engine only accepts input permitted by the **explicit grammar**; it *rejects* the ambiguous, doesn't guess. The "no silent assumptions" rule. |
| **#3 Non-determinism** | The core is deterministic (fixed seed + timeout). **Same input → same verdict** (definite result); the witness is an example (ADR-0019). AI's volatile part stays outside the engine. |

---

## 2. Goal — two tracks (Track A + Track B)

Your request is clear: the engine should be reliable **and also** genuinely attack hard problems
that are "currently unsolvable or most in need of solving". We don't squeeze this into a single
goal; we build it as **two parallel tracks**:

**Track A — Solid foundation (near term, v1–v2).**
Making AI's math *deterministic and verifiable*. This is exactly what LLMs can't do
today; this track is the source of trust.

**Track B — North Star: attacking genuinely hard/open problems (v3+).**
And being honest here does *not* mean saying "we can't" — quite the opposite. There's a track
record of SMT/SAT solvers **actually solving decades-old open problems**:

- **Boolean Pythagorean Triples** (2016) — a long-open question, solved with a SAT
  solver (Heule et al.); a ~200 TB machine-generated proof.
- **Keller conjecture, dimension 7** (2020, CMU) — a ~90-year-old geometry problem, closed with
  SAT.
- **Schur number 5** (2017) — again determined with a SAT solver (~2 PB proof).
- Even giant problems like the **Collatz conjecture** have ongoing *active attack* attempts via
  SAT / rewriting.

MathHead's Z3 core comes from exactly this lineage. Track B's target class:
open questions **reducible to a large finite/combinatorial "satisfiability" problem** — plus
*formal verification* of human/AI proofs (a Lean / AlphaProof-style frontier). The critical
point: a solver saying "I solved it" is only valuable if it produces an **independently verifiable
certificate/proof**; that's why Track B is built *on top of* Track A (the verifiable core) —
**trust first, conquest second.**

---

## 3. Scope contract: broad vision, narrow v1

Your two preferences ("forward-looking/ambitious" **and** "v1 narrow & solid") don't conflict;
they're resolved precisely by your `Plan ≠ Todo` principle:

```
Plan.md  ─▶ BIG vision (frontier): a verifiable proof engine for AI
Todo.md  ─▶ SMALL slice (v1): a single, end-to-end working "Reasoning Checker"
```

We deliberately keep v1 a **vertical slice**: a narrow topic, but *working end to end and
well-tested* from MCP down to the core. Once the solid ground is laid, expanding is cheap;
expanding on rotten ground is expensive.

---

## 4. Architecture — layered hybrid

We're not writing a single "FOL engine". Each layer has one responsibility; the outside world
touches the engine **only** through the MCP layer.

```
                ┌──────────────────────────────────────────────┐
   AI / Claude ─┤  server/   MCP interface (contract/protocol) │
                └───────────────┬──────────────────────────────┘
                                │  clear API (docs/mcp-api.md)
                ┌───────────────▼──────────────┐
                │  guardrails/  FENCE          │  ← input validation, timeout,
                │  (every request passes here) │     determinism setup
                └───────────────┬──────────────┘
                ┌───────────────▼──────────────┐
                │  router/   routing           │  ← which solver + which primitive?
                └──────┬────────────────┬───────┘
          ┌────────────▼───┐     ┌──────▼─────────────┐
          │ core/  (Z3)    │     │ compute/ (SymPy)   │
          │ LOGIC  [v1]    │     │ COMPUTE  [v2+]     │
          │ entailment,    │     │ solve, simplify,   │
          │ consistency,   │     │ derivative/integral│
          │ find_model     │     │                    │
          └────────────────┘     └────────────────────┘
```

Details of layer responsibilities: `docs/architecture.md`. Why Z3 + SymPy were chosen:
`DECISIONS.md` ADR-0001/0002.

---

## 5. The v1 slice — "Reasoning Checker"

AI produces an inference/claim; MathHead checks it **deterministically**. Three primitives:

1. **`entailment(premises, conclusion)`** — Do the premises logically entail the conclusion?
   Method: valid if `(⋀ premises) ∧ ¬conclusion` is **UNSAT**; if **SAT** it returns a
   *counterexample*.
2. **`consistency(statements)`** — Can these statements all be true at once?
   `SAT` → a model, `UNSAT` → the conflicting subset (unsat core).
3. **`model(statements)`** — A concrete example assignment satisfying the statements.

**v1 input fragment:** propositional logic (and/or/not/implies/iff) +
linear arithmetic (`+ - * < <= = >= >` over Int/Real). Quantifiers
(∀/∃) are a v1.1 target. The full grammar: `docs/mcp-api.md`.

**Shared output contract:** each primitive returns a `ReasoningResult` —
`status ∈ {valid, invalid, sat, unsat, unknown, error}`, `witness` (model/
counterexample), `explanation`, `reason_code`, `meta`. `unknown` and `error` are **first-class**;
the engine never fabricates a result.

---

## 6. Roadmap

```
v0  SKELETON (this session) .... structure, contracts, design files, stubs
v1  Reasoning Checker .......... 3 primitives work; propositions + linear arithmetic;
                                 end-to-end MCP; best/worst tests green
v1.1 Quantifiers ............... ∀/∃ and a richer FOL fragment
v2  Compute layer (SymPy) ...... solve/simplify/derivative/integral; router grows
v3  Track B begins ............. proof generation/verification; reduce an open
                                 problem to satisfiability and solve it with the solver
                                 [SEED ADDED: frontier/ — Pythagorean + PHP]
v4+ "Engine family" ........... Physics/Chemistry engines on the same skeleton
```

Note: Physics/Chemistry engines are your long-term idea. We design the skeleton (guardrails +
router + MCP contract) to be *engine-independent* so it doesn't have to be rewritten at v4.
But it is **not included** in the v1 scope.

---

## 7. Guardrails (the counterpart to your 4 protective clauses)

1. **Automated tests (best/worst case)** → `tests/` : known-correct scenarios are
   coded as specs; `unknown`/timeout honesty is tested too.
2. **Architectural safety (the fence)** → `guardrails/` : input size/depth limits,
   rejection of unknown symbols, solver timeout, deterministic configuration.
3. **Explicit project principles** → `PRINCIPLES.md`.
4. **A clear protocol / API** → `docs/mcp-api.md` (+ `server/mcp_server.py` with the exact
   same signatures). The API was **frozen early**; even if the core changes, the external contract is fixed.

---

## 8. Success criterion — the definition of "v1 done"

- [ ] The three primitives work with real Z3.
- [ ] The best/worst scenarios in `tests/test_logic.py` are **green** (xfail removed).
- [ ] Malformed input is cleanly rejected (no silent assumptions).
- [ ] Same input 100 times → 100 times the same output (proof of determinism).
- [ ] At least 3 real questions solved end to end from an MCP client (e.g. Claude).
- [ ] Every decision recorded in `DECISIONS.md`, every step in `Progress.md`.

---

## 9. Risks & honest limits

- **Undecidability:** General FOL is semi-decidable; on rich fragments the engine
  may return `unknown`. We don't *hide* this, we report it.
- **Input-language tension:** the narrower the grammar → the safer but less capable;
  the broader → the more powerful but riskier. v1 deliberately starts narrow.
- **"Is math easier than physics/chemistry?"** The honest answer: *it depends on scope.*
  Verification/logic (v1) is tractable; open theorem proving (v3+) is a hard front. We don't
  lean on an assumption of easiness; we lower the risk with a narrow slice.
- **Determinism limit:** Z3 is stable on most queries; still, we transparently record
  version/timeout-related deviations via `meta`.
- **Track B's limit (honest):** We don't promise to solve famous conjectures (Riemann, etc.)
  *by magic*. The realistic front: problems reducible to finite/combinatorial satisfiability
  + proof verification/formalization. Track B doesn't start before Track A matures, and every
  "solution" requires an independently verifiable certificate.
