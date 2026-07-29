# MathHead — Discovery Run Report

_MathHead 1.0.1 · seed 42 · graphs n≤6 · memoized generation + fixed seed -> same report every run_
_kernel v1.0 · axioms: CRT, RESIDUE(m=2), RESIDUE(m=3), RESIDUE(m=5), RESIDUE(m=7), RESIDUE(m=8), SUM_INDUCTION_
_negative knowledge: 4 dead end(s) recorded_
_knowledge graph: 48 nodes · 123 edges (axiom×7, conjecture×20, counterexample×4, law×6, theorem×11)_

## MOST INTERESTING (heuristic ranking — Track W1, not a learned measure)
- 0.615 · `(n*(n+1)*(n+2)) % 6 == 0`
- 0.615 · `(n*(n+1)*(n+2)*(n+3)) % 24 == 0`
- 0.615 · `(n**3 - n) % 6 == 0`
- 0.615 · `(n**5 - n) % 30 == 0`
- 0.615 · `(n**7 - n) % 42 == 0`

## PROVED (formal — by the judge) (11)
- `(n*(n+1)) % 2 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [0b5a07c36f79d3bf]
- `(n*(n+1)*(n+2)) % 6 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [aed58ab78a2d4eb9]
- `(n*(n+1)*(n+2)*(n+3)) % 24 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [eb68f40b22e38e78]
- `(n**2 - n) % 2 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [da63adb00914de51]
- `(n**3 - n) % 6 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [7b24fe07c5c0df35]
- `(n**5 - n) % 30 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [750d8a0199ccf762]
- `(n**7 - n) % 42 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [fdbd4814cabf3555]
- `sum_(i=1..n) i = n*(n + 1)/2` — solver_verified  ✓ independently verified  ⊢ kernel-verified [e33a456111de3dc1]
- `sum_(i=1..n) i**2 = n*(2*n**2 + 3*n + 1)/6` — solver_verified  ✓ independently verified  ⊢ kernel-verified [f94c5eb5111fd398]
- `sum_(i=1..n) i**3 = n**2*(n**2 + 2*n + 1)/4` — solver_verified  ✓ independently verified  ⊢ kernel-verified [7ccd1ca6fe63e8f0]
- `sum_(i=1..n) 2*i - 1 = n**2` — solver_verified  ✓ independently verified  ⊢ kernel-verified [58f94e06710a1abd]

## REFUTED (killed, with a minimal counterexample) (4)
- `num_triangles <= num_edges` — counterexample: {'num_triangles': 16, 'num_edges': 14, 'n': 6, 'edges': [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5), (4, 5)]}
- `chromatic_number <= max_degree` — counterexample: {'n': 1, 'edges': [], 'lhs': 1, 'rhs': 0}
- `(connected and n>=3) => Hamiltonian` — counterexample: {'n': 3, 'edges': [(0, 2), (1, 2)]}
- `sum_(i=1..n) 2**i = n**7/1260 - n**6/60 + 31*n**5/180 - 11*n**4/12 + 281*n**3/90 - 76*n**2/15 + 704*n/105 - 2` — counterexample: {'note': 'not a polynomial identity'}

## DISCOVERED (empirical — holds on the sample, NOT proven) (6)
- `2*num_edges = sum_degrees` — all graphs n<=6 (support 209)
- `trees: num_triangles = 0` — trees (support 14)
- `trees: num_vertices = num_edges + 1` — trees (support 14)
- `trees: num_vertices = num_edges + num_components` — trees (support 14)
- `forests: num_triangles = 0` — forests (support 43)
- `forests: num_vertices = num_edges + num_components` — forests (support 43)

## OPEN (survived the attack; unproven — no_counterexample_within_bound) (16)
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
- `clique_number <= chromatic_number` — frontier · bounded_check · constructively certified over the sample (constructive_bounded)
- `chromatic_number <= max_degree + 1` — frontier · bounded_check · constructively certified over the sample (constructive_bounded)
- `chromatic_number <= num_vertices` — frontier · bounded_check · constructively certified over the sample (constructive_bounded)
- `Hamiltonian => connected` — frontier · bounded_check
- `Hamiltonian => min_degree >= 2` — frontier · bounded_check
- `(n>=3 and min_degree >= n/2) => Hamiltonian [Dirac]` — frontier · bounded_check

## FRONTIER (NP-hard invariant VALUES — independently confirmed by MathHead's solver) (4)
- chromatic_number(K4) = 4 — ✓ confirmed (solver_verified; MathHead graph_coloring: sat@χ ∧ unsat@χ−1)
- chromatic_number(K3) = 3 — ✓ confirmed (solver_verified; MathHead graph_coloring: sat@χ ∧ unsat@χ−1)
- is_hamiltonian(C5) = True — ✓ confirmed (solver_verified; MathHead hamiltonian_path(cycle=True))
- is_hamiltonian(P4) = False — ✓ confirmed (solver_verified; MathHead hamiltonian_path(cycle=True))

