# MathHead — Discovery Run Report

_MathHead 1.0.1 · seed 42 · graphs n≤6 · memoized generation + fixed seed -> same report every run_

## PROVED (formal — by the judge) (8)
- `(n*(n+1)) % 2 == 0` — formal_proof
- `(n*(n+1)*(n+2)) % 6 == 0` — formal_proof
- `(n**2 - n) % 2 == 0` — formal_proof
- `(n**3 - n) % 6 == 0` — formal_proof
- `sum_(i=1..n) i = n*(n + 1)/2` — solver_verified
- `sum_(i=1..n) i**2 = n*(2*n**2 + 3*n + 1)/6` — solver_verified
- `sum_(i=1..n) i**3 = n**2*(n**2 + 2*n + 1)/4` — solver_verified
- `sum_(i=1..n) 2*i - 1 = n**2` — solver_verified

## REFUTED (killed, with a minimal counterexample) (2)
- `num_triangles <= num_edges` — counterexample: {'num_triangles': 16, 'num_edges': 14, 'n': 6, 'edges': [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5), (4, 5)]}
- `sum_(i=1..n) 2**i = n**7/1260 - n**6/60 + 31*n**5/180 - 11*n**4/12 + 281*n**3/90 - 76*n**2/15 + 704*n/105 - 2` — counterexample: {'note': 'not a polynomial identity'}

## DISCOVERED (empirical — holds on the sample, NOT proven) (6)
- `2*num_edges = sum_degrees` — all graphs n<=6 (support 209)
- `trees: num_triangles = 0` — trees (support 14)
- `trees: num_vertices = num_edges + 1` — trees (support 14)
- `trees: num_vertices = num_edges + num_components` — trees (support 14)
- `forests: num_triangles = 0` — forests (support 43)
- `forests: num_vertices = num_edges + num_components` — forests (support 43)

## OPEN (survived the attack; unproven — no_counterexample_within_bound) (13)
- `num_edges <= sum_degrees` — no_counterexample_within_bound
- `num_triangles <= sum_degrees` — no_counterexample_within_bound
- `max_degree <= num_vertices` — no_counterexample_within_bound
- `max_degree <= num_edges` — no_counterexample_within_bound
- `max_degree <= sum_degrees` — no_counterexample_within_bound
- `min_degree <= num_vertices` — no_counterexample_within_bound
- `min_degree <= num_edges` — no_counterexample_within_bound
- `min_degree <= sum_degrees` — no_counterexample_within_bound
- `min_degree <= max_degree` — no_counterexample_within_bound
- `num_components <= num_vertices` — no_counterexample_within_bound
- `(n*(n+1)*(n+2)*(n+3)) % 24 == 0` — judge: unknown
- `(n**5 - n) % 30 == 0` — judge: unknown
- `(n**7 - n) % 42 == 0` — judge: unknown
