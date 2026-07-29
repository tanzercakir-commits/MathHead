# MathHead — Discovery Run Report

_MathHead 1.0.1 · seed 42 · graphs n≤6 · memoized generation + fixed seed -> same report every run_
_kernel v1.0 · axioms: CRT, POLY_IDENTITY, RESIDUE(m=2), RESIDUE(m=3), RESIDUE(m=5), RESIDUE(m=7), RESIDUE(m=8), SUM_INDUCTION_
_negative knowledge: 4 dead end(s) recorded_
_knowledge graph: 62 nodes · 129 edges (axiom×8, conjecture×20, counterexample×4, law×13, theorem×17)_
_impact: most load-bearing axiom `POLY_IDENTITY` supports 6 theorems_
_solidity (AA3): DISCOVERED_HEURISTIC=0 · EMPIRICALLY_VALIDATED=36 · FORMALLY_SPECIFIED=7 · FORMALLY_PROVED=17_

## MOST INTERESTING (heuristic ranking — Track W1, not a learned measure)
- 0.615 · `(n*(n+1)*(n+2)) % 6 == 0`
- 0.615 · `(n*(n+1)*(n+2)*(n+3)) % 24 == 0`
- 0.615 · `(n**3 - n) % 6 == 0`
- 0.615 · `(n**5 - n) % 30 == 0`
- 0.615 · `(n**7 - n) % 42 == 0`

## PROVED (formal — by the judge) (17)
- `(n*(n+1)) % 2 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [0b5a07c36f79d3bf]
- `(n*(n+1)*(n+2)) % 6 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [aed58ab78a2d4eb9]
- `(n*(n+1)*(n+2)*(n+3)) % 24 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [eb68f40b22e38e78]
- `(n**2 - n) % 2 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [da63adb00914de51]
- `(n**3 - n) % 6 == 0` — formal_proof  ✓ independently verified  ⊢ kernel-verified [7b24fe07c5c0df35]
- `(n**5 - n) % 30 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [750d8a0199ccf762]
- `(n**7 - n) % 42 == 0` — exhaustive_residue_proof  ✓ independently verified  ⊢ kernel-verified [fdbd4814cabf3555]
- `n**2 - 1 = (n - 1)*(n + 1)` — kernel_identity  ⊢ kernel-verified [f03b6c34f7b518de]
- `n**2 - n = n*(n - 1)` — kernel_identity  ⊢ kernel-verified [80852b88f572d75b]
- `n**3 - n = n*(n - 1)*(n + 1)` — kernel_identity  ⊢ kernel-verified [dc3be4bb398acc5d]
- `n**3 - n**2 = n**2*(n - 1)` — kernel_identity  ⊢ kernel-verified [5b09e7084d283282]
- `n**2 - 4 = (n - 2)*(n + 2)` — kernel_identity  ⊢ kernel-verified [47e9628f0c366714]
- `n*(n+1)*(n+2) = n*(n + 1)*(n + 2)` — kernel_identity  ⊢ kernel-verified [7ba4b4b25fc89b37]
- `sum_(i=1..n) i = n*(n + 1)/2` — solver_verified  ✓ independently verified  ⊢ kernel-verified [e33a456111de3dc1]
- `sum_(i=1..n) i**2 = n*(2*n**2 + 3*n + 1)/6` — solver_verified  ✓ independently verified  ⊢ kernel-verified [f94c5eb5111fd398]
- `sum_(i=1..n) i**3 = n**2*(n**2 + 2*n + 1)/4` — solver_verified  ✓ independently verified  ⊢ kernel-verified [7ccd1ca6fe63e8f0]
- `sum_(i=1..n) 2*i - 1 = n**2` — solver_verified  ✓ independently verified  ⊢ kernel-verified [58f94e06710a1abd]

## REFUTED (killed, with a minimal counterexample) (4)
- `num_triangles <= num_edges` — counterexample: {'num_triangles': 16, 'num_edges': 14, 'n': 6, 'edges': [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 3), (2, 4), (2, 5), (3, 4), (3, 5), (4, 5)]}
- `chromatic_number <= max_degree` — counterexample: {'n': 1, 'edges': [], 'lhs': 1, 'rhs': 0}
- `(connected and n>=3) => Hamiltonian` — counterexample: {'n': 3, 'edges': [(0, 2), (1, 2)]}
- `sum_(i=1..n) 2**i = n**7/1260 - n**6/60 + 31*n**5/180 - 11*n**4/12 + 281*n**3/90 - 76*n**2/15 + 704*n/105 - 2` — counterexample: {'note': 'not a polynomial identity'}

## DISCOVERED (empirical — holds on the sample, NOT proven) (13)
- `2*num_edges = sum_degrees` — all graphs n<=6 (support 209)
- `trees: num_triangles = 0` — trees (support 14)
- `trees: num_vertices = num_edges + 1` — trees (support 14)
- `trees: num_vertices = num_edges + num_components` — trees (support 14)
- `forests: num_triangles = 0` — forests (support 43)
- `forests: num_vertices = num_edges + num_components` — forests (support 43)
- `|S_n| = n!` — permutations S_n (n≤6) (support None)
- `sum_(π in S_n) fix(π) = n!` — permutations S_n (n≤6) (support None)
- `sum_(π in S_n) inv(π) = n! · C(n,2) / 2` — permutations S_n (n≤6) (support None)
- `inv and maj are equidistributed over S_n  (Mahonian)` — permutations S_n (n≤7), distribution-level (support None)
- `# permutations of [n] with k descents = Eulerian A(n,k)  (OEIS A008292)` — permutations S_n (n≤7), distribution-level (support None)
- `#{partitions of n into DISTINCT parts} = #{partitions into ODD parts}  (Euler)` — partitions of n (n≤15) (support None)
- `#{partitions of n, largest part = k} = #{partitions of n, exactly k parts}  (conjugation)` — partitions of n (n≤15) (support None)

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

## EXPLANATIONS (structure explaining a result — kernel-verified factorization) (13)
- `n**2 - n = n*(n - 1)` explains `2 | n**2 - n` — product of 2 consecutive integers ⇒ divisible by 2! = 2
- `n**3 - n = n*(n - 1)*(n + 1)` explains `6 | n**3 - n` — product of 3 consecutive integers ⇒ divisible by 3! = 6
- `n*(n+1)*(n+2) = n*(n + 1)*(n + 2)` explains `6 | n*(n+1)*(n+2)` — product of 3 consecutive integers ⇒ divisible by 3! = 6
- `2·|E| = Σ deg(v)` explains `the Handshake Lemma` — double counting the incidences {(v,e): v ∈ e}: summing by vertex gives Σ deg(v), summing by edge gives 2·|E| (each edge has two endpoints) — so they are equal; verified on 208 graphs
- `ω ≤ χ` explains `why a clique lower-bounds the chromatic number` — the ω pairwise-adjacent vertices of a maximum clique must receive ω DISTINCT colors in any proper coloring, so at least ω colors are needed: χ ≥ ω; verified on the sample
- `Hamiltonian ⟹ min_degree ≥ 2` explains `a necessary condition for a Hamiltonian cycle` — a Hamiltonian cycle enters and leaves every vertex by two DISTINCT edges, so each vertex has degree ≥ 2; verified on 60 Hamiltonian graphs
- `|S_n| = n!` explains `over all permutations of [n]` — there are n choices for the first image, n−1 for the next, …, so n! permutations
- `sum_(π in S_n) fix(π) = n!` explains `over all permutations of [n]` — each of the n positions is fixed in exactly (n−1)! permutations, so the total is n·(n−1)! = n!
- `sum_(π in S_n) inv(π) = n! · C(n,2) / 2` explains `over all permutations of [n]` — each of the C(n,2) pairs is inverted in exactly half of S_n (π ↔ its reversal pairs inv(π) with C(n,2)−inv(π)), so the total is C(n,2)·n!/2
- `inv and maj are equidistributed over S_n  (Mahonian)` explains `the distribution over S_n` — MacMahon's theorem: inv and maj are equidistributed permutation statistics (a bijective proof exists). The engine confirms identical distributions on the sample.
- `# permutations of [n] with k descents = Eulerian A(n,k)  (OEIS A008292)` explains `the distribution over S_n` — the descent distribution satisfies the Eulerian recurrence A(n,k) = (k+1)·A(n−1,k) + (n−k)·A(n−1,k−1); computed independently and matched.
- `#{partitions of n into DISTINCT parts} = #{partitions into ODD parts}  (Euler)` explains `over partitions of n` — Euler's theorem: the generating functions ∏(1+x^k) and ∏1/(1−x^{2k−1}) are equal (a bijective proof exists). The engine confirms the two counts agree for every n.
- `#{partitions of n, largest part = k} = #{partitions of n, exactly k parts}  (conjugation)` explains `over partitions of n` — conjugating a partition (transpose its Young diagram) swaps 'largest part' with 'number of parts', giving a bijection between the two families.

## HONEST SCORECARD (Track AF — is any of this NEW?)
- 46 findings · 17 verified · 46 attributable to KNOWN mathematics · **0 novel-to-literature established**
- _the engine correctly REDISCOVERS known mathematics; novelty vs. the literature is not established (needs corpus ingestion, X1/W2 — not built)_

