"""
mathhead.discovery.nauty_scale — scale generation via nauty/geng (v2A4, Real Discovery Program).

The pure-Python generator is honest-bounded at n ≤ 7 (1044 graphs). Real radar work needs more terms and
bigger haystacks. nauty's `geng` (McKay & Piperno) generates non-isomorphic graphs directly — the
standard instrument of computational graph theory. This module wraps it with the project's verification
culture:

  * CROSS-VALIDATION, not blind trust — for every n ≤ 6 the geng-generated graphs are compared to the
    pure-Python generator CLASS BY CLASS (equal sets of canonical keys), and counts must agree through
    n=7. Two fully independent generators agreeing on 1044 isomorphism classes is the warrant for
    trusting geng where the Python generator cannot follow.
  * graph6 decoding is implemented here and round-trip-tested against our own adjacency encoding.
  * honest bounds — full enumeration is used to n ≈ 8-9 (12 346 / 274 668 graphs); beyond that only
    COUNTS (`geng -u`), never silently-truncated object lists.

Filtered generation (`connected=`, `triangle_free=`, `bipartite=`) extends the OEIS radar's refined
family sequences by several terms — more evidence for the human's external lookup.
"""
from __future__ import annotations

import shutil
import subprocess

from .objects import Graph

_GENG = shutil.which("nauty-geng") or shutil.which("geng")


def geng_available() -> bool:
    return _GENG is not None


def _flags(connected: bool, triangle_free: bool, bipartite: bool) -> list:
    out = []
    if connected:
        out.append("-c")
    if triangle_free:
        out.append("-t")
    if bipartite:
        out.append("-b")
    return out


def geng_count(n: int, *, connected: bool = False, triangle_free: bool = False,
               bipartite: bool = False) -> int:
    """Count of non-isomorphic graphs on n vertices in the given class (geng -u; no object cost)."""
    if n == 0:
        return 1                                          # the empty graph — geng starts at n=1
    proc = subprocess.run([_GENG, "-u", *_flags(connected, triangle_free, bipartite), str(n)],
                          capture_output=True, text=True, check=True)
    for tok in proc.stderr.split():
        if tok.isdigit():
            return int(tok)
    raise RuntimeError(f"could not parse geng -u output: {proc.stderr!r}")


def decode_graph6(line: str) -> Graph:
    """Decode one graph6 line (n ≤ 62) into a Graph — upper triangle, column-major bit order."""
    data = [ord(c) - 63 for c in line.strip()]
    n = data[0]
    bits = []
    for byte in data[1:]:
        bits.extend((byte >> shift) & 1 for shift in range(5, -1, -1))
    edges, k = set(), 0
    for j in range(1, n):
        for i in range(j):
            if bits[k]:
                edges.add((i, j))
            k += 1
    return Graph(n, frozenset(edges))


def geng_graphs(n: int, *, connected: bool = False, triangle_free: bool = False,
                bipartite: bool = False, hard_cap: int = 300_000) -> list:
    """All non-isomorphic graphs on n vertices in the class, via geng, decoded to Graph objects.
    Refuses (rather than silently truncates) when the class exceeds `hard_cap`."""
    if n == 0:
        return [Graph(0, frozenset())]
    count = geng_count(n, connected=connected, triangle_free=triangle_free, bipartite=bipartite)
    if count > hard_cap:
        raise ValueError(f"class has {count} graphs > hard_cap={hard_cap}; use geng_count "
                         f"(we refuse to silently truncate)")
    proc = subprocess.run([_GENG, "-q", *_flags(connected, triangle_free, bipartite), str(n)],
                          capture_output=True, text=True, check=True)
    graphs = [decode_graph6(line) for line in proc.stdout.splitlines() if line.strip()]
    if len(graphs) != count:
        raise RuntimeError(f"geng enumeration ({len(graphs)}) disagrees with geng -u count ({count})")
    return graphs


def cross_validate(n_max: int = 5) -> bool:
    """The warrant for trusting geng: for every n ≤ n_max the geng output and the pure-Python generator
    contain EXACTLY the same isomorphism classes (equal canonical-key sets), and counts agree at
    n_max+1. (Defaults stay within the pure generator's fast range — that boundedness is exactly WHY
    geng is being adopted.) Returns True iff everything matches."""
    from .canonical import canonical_key
    from .generate import generate_graphs
    for n in range(n_max + 1):
        ours = {canonical_key(g) for g in generate_graphs(n)}
        theirs = {canonical_key(g) for g in geng_graphs(n)}
        if ours != theirs:
            return False
    return geng_count(n_max + 1) == len(generate_graphs(n_max + 1))


def extended_radar_sequences(n_max: int = 8) -> dict:
    """Longer prefixes for the radar's refined families, from geng counts (cheap even past
    enumeration range): {name: terms}. More terms = a sharper external OEIS lookup for the human."""
    rng = range(n_max + 1)
    return {
        "graphs": tuple(geng_count(n) for n in rng),
        "connected_graphs": tuple(geng_count(n, connected=True) for n in rng),
        "triangle_free_graphs": tuple(geng_count(n, triangle_free=True) for n in rng),
        "bipartite_graphs": tuple(geng_count(n, bipartite=True) for n in rng),
    }
