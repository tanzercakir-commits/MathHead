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
