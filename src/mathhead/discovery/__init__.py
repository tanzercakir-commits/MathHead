"""
mathhead.discovery — the math *discovery* engine (see docs/IDEAL-ENGINE-ROADMAP.md).

This package is the "matter + experiment" (and, later, "discovery") layers built on top of
MathHead's verification/judge spine. It starts in the finite-graph domain (roadmap v0.1:
finite combinatorics + graph theory).

Layers so far:
  * objects    — typed object model (N0): Graph
  * canonical  — isomorphism elimination / canonical labeling (N2)
  * generate   — canonical non-isomorphic generation (N1), pinned to OEIS A000088
  * invariants — property & invariant evaluation (O0/O1)
  * relations  — automatic relation discovery (O2): finds empirical linear laws
                 (e.g. rediscovers the Handshake Lemma) + constant invariants

The judge (MathHead: verify / counterexample / certificate) enters at the refutation and proof
tracks (Q/R) — it is intentionally NOT coupled to this object+invariant layer yet.

Placement note: `discovery` currently lives as a subpackage of `mathhead` purely to reuse the
same tooling (tests, CI, ruff) with zero packaging friction. Architecturally it is the layer
that USES the judge, not a part subordinate to it; it may be promoted to a sibling package
later (see docs/discovery/DECISIONS.md, ADR-D0001).
"""
from .canonical import canonical_graph, canonical_key, is_isomorphic
from .generate import count_non_isomorphic, generate_graphs
from .invariants import INVARIANTS, NUMERIC_INVARIANTS, evaluate, invariant_vector
from .objects import Graph, MathObject
from .relations import DiscoveredLaw, discover_constants, discover_linear_laws

__all__ = [
    "Graph",
    "MathObject",
    "canonical_key",
    "is_isomorphic",
    "canonical_graph",
    "generate_graphs",
    "count_non_isomorphic",
    "INVARIANTS",
    "NUMERIC_INVARIANTS",
    "evaluate",
    "invariant_vector",
    "DiscoveredLaw",
    "discover_linear_laws",
    "discover_constants",
]
