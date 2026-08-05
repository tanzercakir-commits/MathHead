# Worked Examples

Five real sessions — outputs are verbatim engine output, locked by CI (`tests/test_docs_examples.py`).

## 1 · A modular proof, universally

```python
from mathhead.discovery import check
r = check("30 | n^5 - n")
# r.verdict == "proved", r.tier == "kernel_verified", r.proof_hash != ""
```
The kernel proves it by residue exhaustion — and residue exhaustion itself is a *theorem* in the
kernel (derived from the factor theorem), not an axiom.

## 2 · A refutation with the witness in hand

```python
r = check("num_triangles <= num_edges", max_n=6)
# r.verdict == "refuted"; r.witness carries the n=6 graph with 16 triangles and 14 edges
```

## 3 · Bracketing R(3,5)

```console
$ mathhead-discover bracket 3 5 --lo 13 --hi 14 --strengthen
n=13: SAT  [independently_verified_witness]  → R(3,5) > 13
n=14: UNSAT  [solver_verified_with_derived_lemmas]  → R(3,5) <= 14
R(3,5) = 14
```
The UNSAT side lists its two derived degree lemmas — one of which cites the engine's *own* R(3,4)=9
bracket. Self-referential, and labelled.

## 4 · A live hunt that honestly fails

```console
$ mathhead-discover hunt frankl --universe 8 --steps 2000
STATUS: not_found_within_budget  best_score=1
```
`best_score=1` is one step above the equality wall — exactly where a 45-year-old conjecture should
hold the line. The engine reports the measurement, not a wish.

## 5 · The full deterministic report

```console
$ mathhead-discover report --max-n 5
```
One markdown artifact: PROVED / REFUTED / DISCOVERED / OPEN, the kernel axiom manifest, the trust
base, the knowledge graph, the honest scorecard. Same input → byte-identical output.
