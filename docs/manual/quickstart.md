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
