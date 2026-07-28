# MathHead — Status & Error Taxonomy

> **What this file does:** the canonical list of ALL `status` and `reason_code`
> values the engine can return. If a new code is added, this file **and**
> `tests/test_taxonomy.py` are updated together (the test enforces this list).
>
> Principle (PRINCIPLES): failure is a first-class output — `unknown`/`error` is
> not hidden. Every result carries `status` (what happened) + `reason_code` (why).

---

## `status` — what happened?

```
Common
  unknown            · solver could not decide (timeout / semi-decidable)
  error              · input/grammar error or compute failed

Logic — entailment / prove
  valid              · premises entail the conclusion (⊨)
  invalid            · do not entail (counterexample exists)

Logic — consistency / find_model / enumerate / Track B
  sat                · satisfiable (model/coloring exists)
  unsat              · unsatisfiable (contradiction / impossibility proof)

Classification — classify
  tautology | contradiction | contingent

Equivalence — equivalent
  equivalent | not_equivalent

Optimization — optimize / maxsat
  optimal            · best solution found
  unbounded          · objective unbounded (optimize)

Compute — compute (SymPy)
  ok                 · compute succeeded

Independent certificate — check_certificate (Track C2, stdlib)
  verified           · certificate passed independent check
  refuted            · certificate does not hold (produced result is WRONG)
```

## `reason_code` — why?

```
SUCCESS (status: ok/valid/sat/optimal/...)
  OK                     · compute complete (compute)
  ENTAILED               · ⊨ verified
  CONSISTENT             · jointly satisfiable
  MODEL_FOUND            · concrete model found
  MODELS_FOUND           · multiple models (limit)  ·  ALL_MODELS_FOUND · all
  TAUTOLOGY / CONTRADICTION / CONTINGENT       · classify result
  EQUIVALENT / NOT_EQUIVALENT                  · equivalence result
  OPTIMAL                · optimum found  ·  UNBOUNDED · unbounded  ·  OPEN_BOUND · open bound
  COLORING_FOUND         · Track B: coloring found (sat)

FAILURE / NEGATIVE (status: invalid/unsat/error/unknown)
  COUNTEREXAMPLE_FOUND   · counterexample (invalid)
  CONTRADICTION          · contradiction (unsat)
  NO_MODEL               · no model
  PROVEN_IMPOSSIBLE      · Track B: impossibility proof (unsat)  ·  NO_COLORING
  INFEASIBLE             · constraints unsatisfiable (optimize)  ·  HARD_INFEASIBLE (maxsat)
  PARSE_ERROR            · input grammar/whitelist violation (compute)
  COMPUTE_FAILED         · compute failed in closed form (compute; e.g. singular matrix)
  GUARDRAIL_VIOLATION    · guardrail violation (logic input: syntax/length/symbol)
  SOLVER_TIMEOUT         · timeout  ·  SOLVER_UNKNOWN · solver 'unknown'
  UNEXPECTED_SAT         · unexpected sat (internal consistency check)

VERIFICATION LAYER (Track C — AI reasoning auditor)
  EQUAL                  · expressions equivalent (valid)
  EQUAL_ON_COMMON_DOMAIN · equivalent on common domain, domains differ (valid + warning)
  NOT_EQUAL              · not equivalent, counterexample exists (invalid)
  SOLUTION_VERIFIED      · solutions correct + COMPLETE (valid)
  SOLUTION_INCORRECT     · at least one claimed value is not a solution (invalid)
  SOLUTION_INCOMPLETE    · values correct but incomplete (missed solution) (invalid)
  COMPLETENESS_UNKNOWN   · values hold but completeness unverified (unknown)
  STEPS_VALID            · all transitions in the step chain are equivalent (valid)
  STEP_INVALID           · first invalid transition found (invalid)
  UNDECIDED              · equivalence/transition could not be decided (unknown)

CROSS-CHECK (Track C3 — Z3 ⋈ SymPy)
  CONSENSUS_EQUAL        · both engines say 'equivalent' (valid, high confidence)
  CONSENSUS_NOT_EQUAL    · both engines say 'not equivalent' (invalid)
  ENGINES_DISAGREE       · engines conflict — subtle case/domain flag (unknown)
  SINGLE_ENGINE          · only one engine decided (valid/invalid, low confidence)
  CROSS_UNDECIDED        · no engine could decide (unknown)

INDEPENDENT CERTIFICATE (Track C2 — stdlib checker)
  CERTIFICATE_VALID      · certificate independently verified (verified)
  CERTIFICATE_INVALID    · certificate refuted (refuted)

NATURAL LANGUAGE → FORMAL (I2 — recognize-or-refuse)
  UNDERSTOOD             · NL translated to a formal task (ok) + round-trip restatement
  AMBIGUOUS              · multiple interpretations, clarify (unknown)
  UNRECOGNIZED           · not recognized, not guessed (error)
```

**Invariant (test_taxonomy):** every tool call returns values only from the
`status` and `reason_code` sets above; in the `error` case no fabricated result
is produced. New code = this document + test updated together.
