# API & CLI

## The single door

```python
from mathhead.discovery import check
check(statement: str, max_n: int = 7) -> CheckResult
```
`CheckResult`: `verdict` (proved/refuted/open/unsupported) · `tier` · `witness` · `checked_up_to` ·
`proof_hash` · `instruments` · `notes`.

Supported statement forms: `"m | poly(n)"` · `"sum_(i=1..n) f(i) = g(n)"` ·
`"invA <= [k*]invB [+ c]"` (rich + classic graph invariants, connected graphs).

## CLI

```text
mathhead-discover check STATEMENT [--max-n N] [--json]
mathhead-discover bracket S T --lo N --hi M [--strengthen]
mathhead-discover hunt frankl [--universe M] [--steps K] [--seed S]
mathhead-discover report [--max-n N]
```

## The instrument map

Problem structure → instruments (each pointer is import-tested against the codebase):

```python
from mathhead.discovery import suggest_techniques
suggest_techniques("6 divides n^3 - n")
# [("residue exhaustion (kernel)", "kernel.prove_divides", "kernel_verified"), ...]
```

Deeper surfaces (all public in `mathhead.discovery`): the kernel (`prove_divides`,
`prove_sum_identity`, `prove_identity`), the hunters (`hunt`, `tree_hunt`, `hunt_frankl`),
Ramsey (`ramsey_decide`, `bracket_ramsey`), exact certificates (`certify_lambda1_plus_mu_below`,
`lambda1_below`), scale (`geng_graphs`, `geng_count`), the OEIS radar (`radar`), PSLQ
(`find_relation`, `find_algebraic`), and the Lean export (`export_kernel_theorems`).
