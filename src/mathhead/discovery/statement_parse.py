"""
mathhead.discovery.statement_parse — decompose a statement into formal components (v1 V1 slice).

Track V's goal is safe NL→formal; its first honest, fully-deterministic slice is DECOMPOSITION of the
engine's own statement strings into the components the track names: quantifier, domain restriction,
size precondition, relation, and the invariants mentioned (resolved through X2's synonym table). No
LLM, no guessing — regex + the synonym registry; anything unrecognized is reported as such, honestly.
Used to sanity-check `conjecture_db` entries (the parsed domain must match the recorded one).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .technique_map import SYNONYMS

_RELATIONS = (">=", "<=", "=", "divides", "∣", " | ")


@dataclass
class ParsedStatement:
    text: str
    quantifier: str = "unknown"          # "universal" | "existential" | "unknown"
    domain: str = ""                     # e.g. "connected graph"
    n_min: int | None = None             # size precondition (n >= k)
    relation: str = ""                   # the main relation symbol
    invariants: tuple = ()               # canonical invariant names mentioned
    unrecognized: tuple = ()             # tokens that resolved to nothing — reported, not guessed


def _canonical_invariants(text: str) -> tuple:
    low = text.lower()
    found = []
    for canon, syns in SYNONYMS.items():
        if canon in low or any(s.lower() in re.findall(r"[a-z0-9_^]+", low) for s in syns):
            found.append(canon)
    for name in ("num_edges", "num_triangles", "num_vertices", "max_degree", "min_degree",
                 "girth", "diameter", "radius"):
        if name in low:
            found.append(name)
    return tuple(sorted(set(found)))


def parse_statement(text: str) -> ParsedStatement:
    """Deterministic decomposition; unrecognized parts stay visible in `unrecognized`."""
    p = ParsedStatement(text)
    low = text.lower()
    if low.startswith(("for every", "for all", "every")):
        p.quantifier = "universal"
    elif low.startswith(("there exists", "some", "exists")):
        p.quantifier = "existential"
    m = re.search(r"(?:every|for every|for all)\s+([a-z\- ]*?graph[s]?|[a-z\- ]*?famil\w+)", low)
    if m:
        p.domain = m.group(1).strip()
    m = re.search(r"n\s*>=\s*(\d+)", low)
    if m:
        p.n_min = int(m.group(1))
    for rel in _RELATIONS:
        if rel in low:
            p.relation = rel.strip()
            break
    p.invariants = _canonical_invariants(text)
    if p.quantifier == "unknown" and not p.relation and not p.invariants:
        p.unrecognized = (text,)
    return p
