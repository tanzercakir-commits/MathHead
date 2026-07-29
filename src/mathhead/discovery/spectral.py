"""
mathhead.discovery.spectral — the graph domain's first bridge to MathHead (roadmap O1 spectral).

Two things live here:

  * the fast, exact spectral MOMENTS (Σ λ² , Σ λ³ = trace(A²), trace(A³)) are ordinary invariants
    (in `invariants.py`); the O2 miner over them rediscovers the spectral identities
    `Σ λ² = 2·|E|` and `Σ λ³ = 6·(#triangles)` from data.
  * the actual SPECTRUM — the eigenvalues themselves — is computed by **MathHead** (its
    `eigenvalues` tool, exact/symbolic). This is the first time the graph domain flows through
    MathHead's compute/judge spine. We use it for genuinely spectral invariants
    (`num_distinct_eigenvalues`) and, on-thesis, as an INDEPENDENT AUTHORITY that confirms the
    discovered moment identities: MathHead's Σ λ^k equals the matmul trace(A^k).

The spectrum is memoized per graph (a MathHead call per distinct graph is ~tens of ms).
"""
from __future__ import annotations

import sympy

from mathhead.router import route

from .invariants import NUMERIC_INVARIANTS, spectral_moment_2, spectral_moment_3
from .objects import Graph
from .relations import discover_linear_laws

SPECTRAL_NUMERIC = ["spectral_moment_2", "spectral_moment_3"]

_SPECTRUM_CACHE: dict = {}


def adjacency_matrix(g: Graph) -> list:
    """Adjacency matrix as a list of "0"/"1" rows (MathHead's matrix input form)."""
    a = [["0"] * g.n for _ in range(g.n)]
    for (u, v) in g.edges:
        a[u][v] = "1"
        a[v][u] = "1"
    return a


def spectrum(g: Graph) -> list:
    """The adjacency spectrum via MathHead's `eigenvalues` tool: [(eigenvalue, multiplicity), …]
    with exact (possibly irrational) values. Memoized per graph."""
    if g not in _SPECTRUM_CACHE:
        if g.n == 0:
            _SPECTRUM_CACHE[g] = []
        else:
            r = route("eigenvalues", {"matrix": adjacency_matrix(g)})
            _SPECTRUM_CACHE[g] = [
                (sympy.sympify(e["value"]), e["multiplicity"]) for e in (r.result or [])
            ]
    return list(_SPECTRUM_CACHE[g])


def num_distinct_eigenvalues(g: Graph) -> int:
    """Number of distinct adjacency eigenvalues (genuinely needs the spectrum)."""
    return len({v for v, _ in spectrum(g)})


def eigen_power_sum(g: Graph, k: int) -> int:
    """Σ λ^k from MathHead's spectrum. The value is provably an integer (it equals trace(A^k)), so
    we evaluate the eigenvalue power-sum to high precision and round — exact for these small
    integers, and far faster than symbolic simplification of irrational cubes."""
    spec = spectrum(g)
    if not spec:
        return 0
    s = sum(v**k * m for v, m in spec)
    # symmetric adjacency -> real spectrum; take Re() to drop any numerical noise, then round.
    return int(round(float(sympy.re(sympy.N(s, 40)))))


def spectrum_confirms_moments(g: Graph) -> bool:
    """MathHead as INDEPENDENT authority: its eigenvalues reproduce the (matmul) moments.
    Σ λ² == trace(A²) and Σ λ³ == trace(A³)."""
    return (eigen_power_sum(g, 2) == spectral_moment_2(g)
            and eigen_power_sum(g, 3) == spectral_moment_3(g))


def discover_spectral_laws(graphs) -> list:
    """Mine linear laws over the numeric invariants PLUS the spectral moments — the engine
    rediscovers `Σ λ² = 2·num_edges` and `Σ λ³ = 6·num_triangles`."""
    return discover_linear_laws(list(graphs), invariant_names=NUMERIC_INVARIANTS + SPECTRAL_NUMERIC)
