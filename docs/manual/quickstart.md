# Quickstart

```bash
pip install "mathhead[solvers] @ git+https://github.com/tanzercakir-commits/MathHead"
# optional, for graph generation at scale:
sudo apt-get install nauty
```

Three checks, three kinds of honest answer.

```console
$ mathhead-discover check "6 | n^3 - n"
VERDICT: proved   [kernel_verified]
```

```console
$ mathhead-discover check "num_triangles <= num_edges" --max-n 6
VERDICT: refuted   [exact_integer_certificate]
```

```console
$ mathhead-discover check "clique_number <= chromatic_number" --max-n 6
VERDICT: open   [no_counterexample_within_bound]
```

Coverage wave 1 (v4F1) — three more forms through the same door:

```console
$ mathhead-discover check "n^2 = n mod 2"
VERDICT: proved   [kernel_verified]
```

```console
$ mathhead-discover check "sum_degrees == 2*num_edges" --max-n 6
VERDICT: open   [no_counterexample_within_bound]
```
The handshake lemma is a *theorem* — but a finite scan cannot know that, so the engine refuses to
say "proved" and tells you exactly how far the equality held.

```console
$ mathhead-discover check "sum_(i=1..n) i <= n^2"
VERDICT: proved   [solver_verified]
```
The chain is spelled out on the verdict: the closed form `n²/2 + n/2` is kernel-verified, then z3
proves the difference nonnegative for all *real* n ≥ 1 — which covers the integers (the sound
direction of the relaxation).

## The three readings

A bare graph-bound text is *ambiguous* about its quantifier domain: connected graphs? all graphs?
one fixed order? The engine no longer picks one silently — every graph-bound verdict also carries
the three candidate readings, each with its own honest answer:

```console
$ mathhead-discover check "num_vertices <= num_edges + 1" --max-n 6
VERDICT: open   [no_counterexample_within_bound]
  statement : num_vertices <= num_edges + 1
  checked   : ALL 142 connected graphs with 2 <= n <= 6
  note      : survived exhaustive small-order attack; NOT proved — honestly open; quantifier ambiguity: the verdict CHANGES with the reading (A: open, B: refuted, C: refuted) — the answer depends on which question the statement is asking; see readings
  readings  : the same text under 3 candidate quantifier readings —
    [A] open       [no_counterexample_within_bound]  check()'s own reading (baseline)
    [B] refuted    [exact_integer_certificate]  vs A: drops [connected]
    [C] refuted    [exact_integer_certificate]  vs A: drops [connected, 2 <= n <= 6 (bounded scan)]; adds [n == 6 (complete finite domain)]
```
On connected graphs `n ≤ m + 1` is a theorem (still honestly `open` — a finite scan proves
nothing); drop connectivity and two isolated vertices refute it instantly. The connectivity
assumption is load-bearing, and the answer *changes with the question* — so the product says so.
The fixed-order reading C can even turn a scan into a **decision**:

```console
$ mathhead-discover check "sum_degrees == 2*num_edges" --max-n 6
VERDICT: open   [no_counterexample_within_bound]
  ...
  readings  : the same text under 3 candidate quantifier readings —
    [A] open       [no_counterexample_within_bound]  check()'s own reading (baseline)
    [B] open       [no_counterexample_within_bound]  vs A: drops [connected]
    [C] proved     [finite_domain_exhaustion]  vs A: drops [connected, 2 <= n <= 6 (bounded scan)]; adds [n == 6 (complete finite domain)]
```
The handshake lemma stays `open` under both unbounded readings — but restricted to the *complete*
finite domain of order 6 it is genuinely decided, and only there may the engine say `proved`.
The main verdict is always reading A (nothing about the classic envelope changed); `readings` is
extra information, also present as a list under `--json`.

## ∀ or ∃?

Divisibility and congruence statements hide the same kind of ambiguity: does `5 | n^3 - n` claim
*every* n, or *some* n? The engine answers **both** questions — the main envelope is the ∀
reading (unchanged), and the ∃ reading is *decided* from the same finite residue table (p(n) mod
m depends only on n mod m, so the m-residue scan settles ∃ completely — it is never `open`):

```console
$ mathhead-discover check "5 | n^3 - n"
VERDICT: refuted   [exact_integer_certificate]
  statement : 5 | n^3 - n
  witness   : {'n': 2, 'value_mod_m': 1}
  checked   : decided exactly (finite residue table)
  note      : residue n≡2 (mod 5) gives a nonzero value — the claim is false; quantifier ambiguity: the verdict CHANGES with the reading (∀: refuted, ∃: proved) — the answer depends on which question the statement is asking; see readings
  readings  : the same text under 2 candidate quantifier readings —
    [∀] refuted    [exact_integer_certificate]  check()'s own reading (baseline)
    [∃] proved     [exact_integer_certificate]  vs ∀: 'for every integer n' weakened to 'for at least one integer n'
```
Under ∀ the claim is false (n=2 gives 6, and 5 ∤ 6); under ∃ it is true — the ∃ reading's
`witness_summary` (in the API and `--json`) carries the witness n=0 *and* the full solution set
as residue classes: `n ≡ 0, ±1 (mod 5)` — 3 of 5 residue classes. When no residue class works at
all (`"2 | 2*n + 1"` — an odd number is never even), the ∃ reading is *refuted* outright: all m
residues were scanned, a finite decision. Congruences `p(n) ≡ q(n) (mod m)` inherit the same two
readings through the `m | (p − q)` reduction.

And a classic, bracketed before your coffee cools:

```console
$ mathhead-discover bracket 3 3 --lo 5 --hi 6
R(3,3) = 6
```

From Python:

```python
from mathhead.discovery import check
r = check("sum_(i=1..n) i = n*(n+1)/2")
assert r.verdict == "proved" and r.tier == "kernel_verified"
```
