"""
mathhead.discovery.interestingness — a transparent interestingness score (roadmap Track W1).

Ranks findings by the document's interestingness components —
novelty · generality · surprise · usefulness · compression · connectivity − triviality —
each a NAMED, documented, deterministic proxy computed from the finding itself and its peers. The
weighted sum gives a single score in [0, 1] with a per-component breakdown, so a human can see WHY
something ranked where it did.

HONESTY — say it plainly. This is a HEURISTIC, not a learned or ground-truth measure. The components
are defensible proxies (e.g. "compression = support explained per symbol"), not the real thing; a
truly learned interestingness model with human feedback is Track W3, and is explicitly OPEN (the
source document itself concedes full automation isn't solved). This module ranks and explains; it
never decides what is true.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# component weights (documented, hand-set — NOT learned; that is W3, open)
WEIGHTS = {
    "novelty": 0.20,
    "generality": 0.20,
    "surprise": 0.20,
    "usefulness": 0.15,
    "compression": 0.15,
    "connectivity": 0.10,
}

_KNOWN_INVARIANTS = {
    "num_vertices", "num_edges", "sum_degrees", "num_triangles", "max_degree", "min_degree",
    "num_components", "chromatic_number", "clique_number", "is_hamiltonian", "degree_sequence",
}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def _tokens(statement: str) -> set:
    """Identifier-like tokens in a statement — used for connectivity and compression."""
    return set(re.findall(r"[A-Za-z_][A-Za-z_0-9]+", str(statement)))


def _support(item: dict) -> int:
    s = item.get("support")
    return int(s) if isinstance(s, (int, float)) else 0


def novelty(item: dict) -> float:
    """Heuristic: non-trivial, non-tautological statements are more novel. A tautology (same token on
    both sides of ≤/=) or a known-trivial bound scores low."""
    stmt = str(item.get("statement", ""))
    parts = re.split(r"<=|==|=|>=|<|>", stmt)
    if len(parts) == 2 and _tokens(parts[0]) == _tokens(parts[1]) and _tokens(parts[0]):
        return 0.1                                           # tautology-shaped
    if "chromatic_number <= num_vertices" in stmt:           # the textbook-trivial bound
        return 0.2
    return 0.7


def generality(item: dict) -> float:
    """Heuristic: broad scope scores higher. Universal (proved-for-all-n) > all-graphs > subclass."""
    status = item.get("status", "")
    scope = str(item.get("scope", "")).lower()
    if status == "proved":
        return 1.0                                           # holds for all n (a real universal)
    if "all graphs" in scope or "all graphs" in str(item.get("statement", "")):
        return 0.8
    if any(w in scope for w in ("tree", "forest", "subclass")):
        return 0.5
    return 0.45


def surprise(item: dict) -> float:
    """Heuristic: a plausible-looking claim that turned out FALSE is surprising; a proved fact with a
    composite modulus (stronger than the naive single-prime guess) is mildly surprising."""
    if item.get("status") == "refuted":
        return 0.9
    mod = item.get("modulus")
    if isinstance(mod, int) and mod > 1 and len(_prime_factors(mod)) > 1:
        return 0.7                                           # e.g. n³−n mod 6, stronger than mod 3
    return 0.3


def usefulness(item: dict) -> float:
    """Heuristic: a kernel-verified proof is the most useful (reusable, trustworthy); a refutation is
    useful negative knowledge; open/empirical are weaker."""
    if item.get("kernel_verified"):
        return 0.9
    status = item.get("status", "")
    return {"proved": 0.75, "refuted": 0.6, "empirical": 0.5}.get(status, 0.4)


def compression(item: dict) -> float:
    """Heuristic (MDL flavor): support explained per symbol. A short law covering much data compresses
    well. Normalized by a soft cap."""
    ntokens = max(1, len(_tokens(item.get("statement", ""))))
    return _clamp(_support(item) / (ntokens * 12.0))


def connectivity(item: dict, context: list) -> float:
    """Heuristic: fraction of OTHER findings that share an invariant token — how wired-in it is."""
    others = [c for c in context if c is not item]
    if not others:
        return 0.0
    toks = _tokens(item.get("statement", "")) & _KNOWN_INVARIANTS
    if not toks:
        return 0.0
    shared = sum(1 for c in others if toks & _tokens(c.get("statement", "")))
    return _clamp(shared / len(others))


def triviality(item: dict) -> float:
    """Penalty (subtracted): degenerate counterexample (n≤1), tautology-shaped, or near-zero support."""
    pen = 0.0
    ce = item.get("counterexample") or {}
    if isinstance(ce, dict) and isinstance(ce.get("n"), int) and ce["n"] <= 1:
        pen += 0.3                                           # a degenerate single-vertex witness
    if novelty(item) <= 0.2:
        pen += 0.3
    return _clamp(pen)


@dataclass
class Interestingness:
    statement: str
    total: float
    components: dict = field(default_factory=dict)
    penalty: float = 0.0


def score(item: dict, context: list | None = None) -> Interestingness:
    """Weighted interestingness of one finding (with its peers as context). Transparent: the returned
    object carries every component so the ranking is explainable."""
    ctx = context or [item]
    comps = {
        "novelty": novelty(item),
        "generality": generality(item),
        "surprise": surprise(item),
        "usefulness": usefulness(item),
        "compression": compression(item),
        "connectivity": connectivity(item, ctx),
    }
    pen = triviality(item)
    total = _clamp(sum(WEIGHTS[k] * v for k, v in comps.items()) - pen)
    return Interestingness(str(item.get("statement", "")), round(total, 4),
                           {k: round(v, 4) for k, v in comps.items()}, round(pen, 4))


def rank(items: list) -> list:
    """Score every finding against the whole set and return them most-interesting first
    (deterministic — ties broken by statement)."""
    scored = [(score(it, items), it) for it in items]
    scored.sort(key=lambda si: (-si[0].total, si[0].statement))
    return scored


def _prime_factors(m: int) -> set:
    out, d, x = set(), 2, int(m)
    while d * d <= x:
        while x % d == 0:
            out.add(d)
            x //= d
        d += 1
    if x > 1:
        out.add(x)
    return out
