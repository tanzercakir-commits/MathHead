# MathHead — LLM-Trap Benchmark Results

> **What it measures:** the rate at which MathHead correctly **adjudicates**
> (catches) the classic math-error patterns that LLMs frequently FALL INTO.
> Source data: `benchmarks/llm_traps.json`; harness: `benchmarks/run.py`;
> regression guardrail: `tests/test_benchmark_traps.py`.
>
> **HONEST framing (important):** This is a **reproducible demonstration** — does
> MathHead return the correct corrective verdict for every trap? This is **NOT a
> live LLM A/B test.** Measuring how much a real model, raw, actually falls into
> these traps (raw-LLM vs MathHead-assisted accuracy) is work the user would run
> against a real model. The claim here is modest and honest: *MathHead reliably
> catches these error classes.*

## Result

**Catch rate: 14/14 = 100%** (all categories).

Critical: the "true_positive" check passes too — MathHead does not mistakenly flag
a CORRECT identity (`sin²+cos² = 1`). So we not only catch the error, we also do
not break what is correct (no false positives).

## Trap categories (the LLM falls in → MathHead catches)

| Category | LLM error | MathHead verdict | Tool |
|---|---|---|---|
| incomplete_solution | `x²=4 → {2}` (−2 missed) | `SOLUTION_INCOMPLETE` | `verify_solution` |
| wrong_solution | `x²=4 → {2,3}` | `SOLUTION_INCORRECT` | `verify_solution` |
| false_identity | `(x+1)² = x²+1` | `CONSENSUS_NOT_EQUAL` | `cross_check` |
| domain_trap | `(x²−1)/(x−1) = x+1` | `EQUAL_ON_COMMON_DOMAIN` / `ENGINES_DISAGREE` | `verify_equality` / `cross_check` |
| false_inequality | `x² ≥ x` (∀x) | `invalid` + counterexample `x=0.5` | `prove_inequality` |
| root_branch | `√(x²) = x` | `NOT_EQUAL` (`x=−1`) | `verify_equality` |
| bad_step | `2(x+3) = 2x+3` | `STEP_INVALID` | `verify_steps` |
| primality | `91 is prime` | `result: false` | `is_prime` |
| arithmetic | `2¹⁰ = 1000` | `NOT_EQUAL` (1024) | `verify_equality` |
| modular | `4⁻¹ mod 8` fabricated | `COMPUTE_FAILED` | `modular_inverse` |
| integer_solution | `2x+4y=5` integer | `[]` (no solution) | `linear_diophantine` |

## Reproduce

```bash
python benchmarks/run.py            # prints the table and the rate
pytest tests/test_benchmark_traps.py -q   # regression guardrail (every trap must be caught)
```

Adding a new trap: add an entry to `benchmarks/llm_traps.json` (task + payload +
expected corrective verdict). The guardrail covers it automatically.
