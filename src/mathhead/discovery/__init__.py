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
  * conjectures— conjecture generation (P0/P1): subclass laws + inequality bounds
  * refute     — counterexample-first refutation (Q0): minimal counterexample or an honest
                 'no_counterexample_within_bound'
  * judge      — the judge bridge (R): hands algebraically-expressible survivors to MathHead for
                 a real verdict (proved by induction / solver-verified / refuted-with-witness)

The judge (MathHead: verify / counterexample / certificate) enters at the refutation and proof
tracks (Q/R) — it is intentionally NOT coupled to this object+invariant layer yet.

Placement note: `discovery` currently lives as a subpackage of `mathhead` purely to reuse the
same tooling (tests, CI, ruff) with zero packaging friction. Architecturally it is the layer
that USES the judge, not a part subordinate to it; it may be promoted to a sibling package
later (see docs/discovery/DECISIONS.md, ADR-D0001).
"""
from .canonical import canonical_graph, canonical_key, is_isomorphic
from .conjectures import Conjecture, bound_conjectures, subclass_laws
from .generate import count_non_isomorphic, generate_graphs
from .invariants import (
    INVARIANTS,
    NUMERIC_INVARIANTS,
    evaluate,
    invariant_vector,
    is_forest,
    is_tree,
)
from .judge import (
    Verdict,
    judge,
    judge_identity,
    judge_induction,
    judge_inequality,
    judge_task,
)
from .objects import Graph, MathObject
from .refute import RefutationResult, refute
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
    "is_forest",
    "is_tree",
    "DiscoveredLaw",
    "discover_linear_laws",
    "discover_constants",
    "Conjecture",
    "subclass_laws",
    "bound_conjectures",
    "RefutationResult",
    "refute",
    "Verdict",
    "judge",
    "judge_task",
    "judge_induction",
    "judge_inequality",
    "judge_identity",
]
