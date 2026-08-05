# Worked Examples

Eight real sessions — outputs are verbatim engine output, locked by CI (`tests/test_docs_examples.py`).

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
n=14: UNSAT  [independently_verified_unsat_proof_of_strengthened_formula]  → R(3,5) <= 14
R(3,5) = 14
```
The UNSAT side carries the solver's DRUP refutation, re-checked by the engine's own pure-Python RUP
checker — and its tier says, verbatim, that the proof refutes the *strengthened* formula: the two
derived degree lemmas (one of which cites the engine's *own* R(3,4)=9 bracket) are listed on the
verdict. Self-referential, and labelled.

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

## 6 · Polynomial congruences (v4F1)

`p(n) ≡ q(n) (mod m)` reduces to `m | (p − q)` — the same kernel door, the same tiers:

```console
$ mathhead-discover check "n^5 ≡ n (mod 30)"
VERDICT: proved   [kernel_verified]
  statement : n^5 ≡ n (mod 30)
  checked   : all integers n (universal proof)
  proof     : kernel hash 750d8a0199ccf762
  note      : reduced to 30 | (p − q), then proved by residue exhaustion/CRT in the LCF-style kernel
```

```console
$ mathhead-discover check "n^2 ≡ n (mod 3)"
VERDICT: refuted   [exact_integer_certificate]
  statement : n^2 ≡ n (mod 3)
  witness   : {'n': 2, 'lhs_mod_m': 1, 'rhs_mod_m': 2, 'difference_mod_m': 2}
  checked   : decided exactly (finite residue table)
  note      : residue n≡2 (mod 3): the two sides differ mod 3 — the claim is false
```
The ASCII spelling `"n^2 = n mod 2"` is accepted too. Non-integer coefficients (`n/2 ≡ 0 (mod 2)`)
are an honest `unsupported`, never a silent truncation.

## 7 · Graph equalities: a theorem the scan will NOT call proved (v4F1)

```console
$ mathhead-discover check "sum_degrees == 2*num_edges" --max-n 6
VERDICT: open   [no_counterexample_within_bound]
  statement : sum_degrees == 2*num_edges
  checked   : ALL 142 connected graphs with 2 <= n <= 6
  note      : universal claim not proved; holds for all connected graphs up to n=6 — a finite scan NEVER proves an equality
```
The handshake lemma is true for every graph — but the engine only *scanned*, so it says exactly
that. A false equality is convicted in either direction, smallest witness first:

```console
$ mathhead-discover check "num_vertices == num_edges"
VERDICT: refuted   [exact_integer_certificate]
  statement : num_vertices == num_edges
  witness   : {'n': 2, 'edges': [(0, 1)], 'num_vertices': 2, 'num_edges': 1}
  checked   : first counterexample among connected graphs, n=2
  note      : smallest-order witness; values computed exactly (equality broken — either direction convicts)
```
The mirrored `>=` direction works the same way (`"num_edges >= num_triangles"` is refuted by the
same n=6 graph as the `<=` classic).

## 8 · Comparative sum inequalities: a two-instrument proof chain (v4F1)

```console
$ mathhead-discover check "sum_(i=1..n) i <= n^2"
VERDICT: proved   [solver_verified]
  statement : sum_(i=1..n) i <= n^2
  checked   : all integers n >= 1 (closed form + real-relaxation proof)
  note      : closed form kernel_verified; inequality step z3 — chain: sum = n**2/2 + n/2 (kernel hash e33a456111de3dc1); then (n**2/2 - n/2) >= 0 for all REAL n >= 1 (z3 NRA), which covers the integers
```
The tier is the WEAKEST link of the chain (`solver_verified`, not `kernel_verified`) — the kernel
hash covers only the closed-form step, and the note says so. And the relaxation is used in the
sound direction only: a real counterexample is never a refutation by itself — it is a HINT. When
the hint lands on an integer, the engine re-verifies it by exact arithmetic with no solver in the
loop, and only then convicts:

```console
$ mathhead-discover check "sum_(i=1..n) i <= n^2/2 + 100"
VERDICT: refuted   [exact_integer_certificate]
  statement : sum_(i=1..n) i <= n^2/2 + 100
  witness   : {'n': 201, 'lhs_sum': '20301', 'rhs': '40601/2', 'exact': 'direct exact summation'}
  checked   : violation at n=201 verified exactly; no violation among n <= 40
  note      : z3 proposed the integer point; the violation was re-verified by exact arithmetic with no solver in the loop (not necessarily the smallest witness)
```
(The claim first fails at the integer n=201 — outside the n ≤ 40 exact scan. z3 found it; the
exact summation 1+2+⋯+201 = 20301 > 20300.5 convicts it — the solver only pointed.) A hint that
does NOT land on an integer upgrades nothing: `"sum_(i=1..n) (2*i-1) <= n^2 + (n-1)*(n-2)/2"`
holds at every integer but fails between 1 and 2 over the reals — the engine keeps it honestly
`open [no_counterexample_within_bound]`.
