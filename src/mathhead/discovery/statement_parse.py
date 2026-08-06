"""
mathhead.discovery.statement_parse — decompose a statement into formal components (v1 V1 slice).

Track V's goal is safe NL→formal; its honest, fully-deterministic slice is DECOMPOSITION of the
engine's own statement strings into the SEVEN components the track names, each a visible field:

  * quantifier  (niceleyici)       — universal / existential / unknown;
  * domain + n_min (önkoşul)       — the explicit domain restriction + size precondition;
  * invariants  (notasyon)         — mentioned invariants, resolved through X2's synonym table
                                     (single-token synonyms like `mu`/`chi` land on canonical names);
  * definitions (tanım)            — each recognized invariant resolved to the CALLABLE that defines
                                     it (`module:attr`, importable — the definition cannot drift);
  * implicit_assumptions (örtük-varsayım) — the background conventions the domain silently carries
                                     (finite / simple / undirected for graphs), made VISIBLE from a
                                     fixed table — never inferred, never guessed;
  * goal        (hedef)            — the claim triple (lhs, relation, rhs), split ONLY where the
                                     split is unambiguous (after the ':' separator, or a bare
                                     relation with no quantifier prefix); () otherwise, honestly;
  * basis       (temel)            — the object theory the statement lives in (fixed classification).

No LLM, no guessing — regex + fixed tables + the synonym registry; anything unrecognized is
reported as such, honestly. Used to sanity-check `conjecture_db` entries (the parsed domain must
match the recorded one).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .technique_map import SYNONYMS

_RELATIONS = (">=", "<=", "=", "divides", "∣", " | ")

# tanım — canonical invariant name → the callable that DEFINES it ("module:attr", importable).
# Names absent here (e.g. "union-closed", a domain marker, not a numeric invariant) simply get no
# definition pointer — visible absence, never a fabricated one.
DEFINITIONS: dict = {
    "spectral radius": "mathhead.discovery.conjecture_db:lambda1_power",
    "matching number": "mathhead.discovery.rich_invariants:matching_number",
    "independence number": "mathhead.discovery.rich_invariants:independence_number",
    "domination number": "mathhead.discovery.rich_invariants:domination_number",
    "chromatic number": "mathhead.discovery.invariants:chromatic_number",
    "clique number": "mathhead.discovery.invariants:clique_number",
    "girth": "mathhead.discovery.rich_invariants:girth",
    "diameter": "mathhead.discovery.rich_invariants:diameter",
    "radius": "mathhead.discovery.rich_invariants:radius",
    "num_vertices": "mathhead.discovery.invariants:num_vertices",
    "num_edges": "mathhead.discovery.invariants:num_edges",
    "num_triangles": "mathhead.discovery.invariants:num_triangles",
    "max_degree": "mathhead.discovery.invariants:max_degree",
    "min_degree": "mathhead.discovery.invariants:min_degree",
}

# örtük-varsayım / temel — fixed convention tables keyed by the recognized domain kind. The point
# is to make the SILENT background explicit; an unrecognized domain honestly gets none.
_GRAPH_ASSUMPTIONS = ("finite", "simple (no loops / multi-edges)", "undirected")
_FAMILY_ASSUMPTIONS = ("finite family of finite sets",)


@dataclass
class ParsedStatement:
    text: str
    quantifier: str = "unknown"          # "universal" | "existential" | "unknown"
    domain: str = ""                     # e.g. "connected graph"
    n_min: int | None = None             # size precondition (n >= k)
    relation: str = ""                   # the main relation symbol
    invariants: tuple = ()               # canonical invariant names mentioned
    unrecognized: tuple = ()             # tokens that resolved to nothing — reported, not guessed
    definitions: tuple = ()              # ((invariant, "module:attr"), …) — resolvable code (tanım)
    implicit_assumptions: tuple = ()     # background conventions made visible (örtük-varsayım)
    goal: tuple = ()                     # (lhs, relation, rhs) claim triple, or () (hedef)
    basis: str = ""                      # the object theory of the statement (temel)


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


def _goal_triple(text: str, quantifier: str) -> tuple:
    """The claim triple (lhs, relation, rhs) — split ONLY where the split point is unambiguous:
    after the last ':' (the engine's canonical statement separator), or over the whole text when
    there is NO quantifier prefix (a bare relation). Anything else → () — no guessing: a relation
    glyph inside a precondition ('n>=3') must never be mistaken for the claim."""
    region = text.rsplit(":", 1)[1] if ":" in text else (text if quantifier == "unknown" else "")
    low = region.lower()
    for rel in _RELATIONS:
        idx = low.find(rel)
        if idx >= 0:
            return (region[:idx].strip(), rel.strip(), region[idx + len(rel):].strip())
    return ()


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
    p.definitions = tuple((inv, DEFINITIONS[inv]) for inv in p.invariants if inv in DEFINITIONS)
    graphy = "graph" in p.domain or any(inv in DEFINITIONS for inv in p.invariants)
    if graphy:
        p.implicit_assumptions, p.basis = _GRAPH_ASSUMPTIONS, "finite graph theory"
    elif "famil" in p.domain:
        p.implicit_assumptions, p.basis = _FAMILY_ASSUMPTIONS, "finite set combinatorics"
    p.goal = _goal_triple(text, p.quantifier)
    if p.quantifier == "unknown" and not p.relation and not p.invariants:
        p.unrecognized = (text,)
    return p
