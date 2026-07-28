# MathHead — Project Principles

> **This file's job:** the immutable rules everyone developing the engine (human or AI)
> must follow. If a piece of code/decision conflicts with one of these principles, the
> principle wins, not the decision. This is the concrete form of your "explicitly defined
> project principles" and "don't step outside the fence" clauses.

---

## Core principles

1. **Determinism comes first.** Same input → same **verdict** (definite result: valid/
   invalid/sat/unsat). The witness is a valid *example*; when there are multiple solutions
   which one is returned can vary, but the verdict is always the same (ADR-0019). Volatility
   stays *outside* the engine. *(Wall #3)*

2. **No silent assumptions.** If the input is ambiguous, incomplete, or outside the grammar,
   the engine **rejects** it — it does *not* guess "they probably meant this". The reason for
   rejection is clear. *(Wall #2)*

3. **`unknown` and `error` are first-class output.** If the engine doesn't know a result,
   it says so explicitly; it never **fabricates** a fake `valid/sat`. Honesty > looking good.

4. **The fence is hard (hard guardrail).** Size, depth, time, and symbol limits
   cannot be exceeded. The solver can't run forever; a timeout is a *feature*, not a
   bug.

5. **Freeze the external API early, fill in the internals later.** The `ReasoningResult` contract
   and the MCP tool signatures are fixed. Even if the core changes, the outside world is unaffected.
   *(Wall #1: prevents contract drift.)*

6. **Narrow & solid > broad & shallow.** Every release adds a vertical slice that *works*
   end to end. "Small but complete" is preferred over "half-done but broad".

7. **Every decision is written down.** Every choice affecting the architecture goes to
   `DECISIONS.md` (as an ADR), every work step to `Progress.md`. Small decisions are
   *not lost*. *(Wall #1)*

8. **Test = specification.** A new capability is first defined with a best-case **and** worst-case
   test. `unknown`/timeout behavior is tested too.

9. **Traceability is mandatory.** Every response carries `meta`: which solver, which version,
   how long it took, which seed. A result must always be *reproducible*.

10. **The external contract is independent of the engine.** Z3 today, another solver tomorrow —
    the MCP/`ReasoningResult` layer doesn't change. This preserves the ground for future engines (v4:
    Physics/Chemistry).

---

## Checklist before making a change

- [ ] Which principle is this change aligned with / in conflict with?
- [ ] Does it change the external API contract (signature/output)? If so, **stop**
      and write an ADR first.
- [ ] Is there a best-case *and* worst-case test?
- [ ] Does it break determinism? (new randomness / order dependence?)
- [ ] Was `Progress.md` updated, and a new ADR opened if needed?
