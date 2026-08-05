# API & CLI

## The single door

```python
from mathhead.discovery import check
check(statement: str, max_n: int = 7) -> CheckResult
```
`CheckResult`: `verdict` (proved/refuted/open/unsupported) · `tier` · `witness` · `checked_up_to` ·
`proof_hash` · `instruments` · `notes`.

Supported statement forms: `"m | poly(n)"` · `"p(n) ≡ q(n) (mod m)"` (ASCII: `"p(n) = q(n) mod m"`;
integer coefficients only) · `"sum_(i=1..n) f(i) = g(n)"` · `"sum_(i=1..n) f(i) <= g(n)"` / `">="`
(smallest-n witness first, then kernel closed form + z3 real-relaxation proof; an integer z3
hint is re-verified by exact arithmetic before any refutation) ·
`"invA <= [k*]invB [+ c]"`, the mirrored `">="`, and equalities `"invA == [k*]invB [+ c]"`
(rich + classic graph invariants, connected graphs; a surviving equality stays `open`, never proved) ·
`"all perms of n: invA <= invB"` / `">="` / `"=="` (invariants: `inversions`, `descents`,
`major_index`, `fixed_points`, `cycles` — alias `num_cycles`; the right side may be an
exact-rational `g(n)`; ALL of S_1..S_min(max_n,7) scanned — a survivor stays `open`) ·
`"partitions(n, odd) == partitions(n, distinct)"` (filters `odd`/`distinct`/`all`; both counts exact
for every n ≤ 20; the odd/distinct survivor also gets Glaisher's bijection re-verified per n — and
STILL stays `open`) · `"compositions(n) == g(n)"` (exact count vs formula for every n ≤ 12; for
`2^(n-1)` the cut-point bijection is re-verified per n — same honest `open`). Set-partition/Bell
counts are not yet in the surface — `unsupported` says so. Route-wide guard: any numeric constant
(literal or evaluated) beyond 4000 digits is an honest `unsupported`, never a crash.

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
