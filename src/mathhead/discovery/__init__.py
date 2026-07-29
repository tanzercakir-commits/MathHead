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
  * arithmetic — the loop CLOSED end to end (generate → refute → PROVE) in a domain where
                 MathHead is the native judge: discovers modular laws and proves them by induction
  * report     — one honest run report across both domains (AC2): proved / discovered / refuted /
                 open, each with an honest status; deterministic
  * spectral   — the graph domain's first bridge to MathHead: eigenvalues via MathHead, the
                 spectral identities (Σλ²=2|E|, Σλ³=6·#triangles) discovered from data
  * sequences  — 2nd arithmetic generator: discover a SUM's closed form from data and prove it by
                 induction via MathHead (Σi=n(n+1)/2, Σi³=…); refuses to force a non-polynomial fit
  * coloring   — bridge to the SAT/UNSAT FRONTIER: χ(g) computed by backtracking, then confirmed by
                 MathHead's graph_coloring (sat at χ, unsat at χ−1); mines ω ≤ χ ≤ Δ+1, refutes χ ≤ Δ
  * hamiltonicity — 2nd frontier bridge: is_hamiltonian by backtracking, confirmed by MathHead's
                 hamiltonian_path(cycle); rediscovers Dirac's theorem, refutes connected⟹Hamiltonian
  * graph_proofs — CONSTRUCTIVE certificates for the surviving coloring laws (χ≤Δ+1 via greedy,
                 ω≤χ via a solver-double-confirmed clique); independently re-checked; honestly
                 `constructive_bounded` (witnessed over the sample, NOT a universal ∀G proof yet)
  * kernel     — minimal LCF-style PROOF KERNEL (M1/M2): a Theorem exists only if a proof TERM
                 (RESIDUE / CRT rules) is kernel-checked; forge-guarded; rejects false claims

The judge (MathHead: verify / counterexample / certificate) enters at the refutation and proof
tracks (Q/R) — it is intentionally NOT coupled to this object+invariant layer yet.

Placement note: `discovery` currently lives as a subpackage of `mathhead` purely to reuse the
same tooling (tests, CI, ruff) with zero packaging friction. Architecturally it is the layer
that USES the judge, not a part subordinate to it; it may be promoted to a sibling package
later (see docs/discovery/DECISIONS.md, ADR-D0001).
"""
from .arithmetic import (
    ArithmeticFinding,
    discover_and_prove,
    discovered_modulus,
    first_counterexample,
    run_arithmetic_discovery,
)
from .canonical import canonical_graph, canonical_key, is_isomorphic
from .checker import check_proof, independently_verify
from .coloring import (
    ColoringBoundFinding,
    ColoringVerification,
    coloring_bounds,
    verify_chromatic_number,
)
from .conjectures import Conjecture, bound_conjectures, subclass_laws
from .generate import count_non_isomorphic, generate_graphs
from .graph_proofs import (
    Certificate,
    certify_frontier_laws,
    check_certificate,
    greedy_coloring,
    max_clique,
)
from .hamiltonicity import (
    HamiltonicityVerification,
    ImplicationFinding,
    hamiltonicity_laws,
    verify_hamiltonicity,
)
from .kernel import CRT, KernelError, Residue, Theorem, check, prove_divides
from .invariants import (
    INVARIANTS,
    NUMERIC_INVARIANTS,
    chromatic_number,
    clique_number,
    evaluate,
    invariant_vector,
    is_forest,
    is_hamiltonian,
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
from .novelty import is_subclass_specific, novel_subclass_laws
from .objects import Graph, MathObject
from .proof_tree import ProofNode, proof_tree, render_tree
from .refute import RefutationResult, refute
from .report import DiscoveryReport, render, run_report
from .relations import DiscoveredLaw, discover_constants, discover_linear_laws
from .sequences import (
    SumIdentityFinding,
    discover_closed_form,
    run_sequence_discovery,
)
from .spectral_bounds import SpectralBoundFinding, run_spectral_bounds, spectral_radius
from .spectral import (
    discover_spectral_laws,
    num_distinct_eigenvalues,
    spectrum,
    spectrum_confirms_moments,
)
from .strategy import (
    factor_prime_powers,
    prove_by_residues,
    prove_modular_divisibility,
)

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
    "is_hamiltonian",
    "chromatic_number",
    "clique_number",
    "ColoringVerification",
    "verify_chromatic_number",
    "ColoringBoundFinding",
    "coloring_bounds",
    "HamiltonicityVerification",
    "verify_hamiltonicity",
    "ImplicationFinding",
    "hamiltonicity_laws",
    "Certificate",
    "certify_frontier_laws",
    "check_certificate",
    "greedy_coloring",
    "max_clique",
    "Theorem",
    "Residue",
    "CRT",
    "KernelError",
    "check",
    "prove_divides",
    "DiscoveredLaw",
    "discover_linear_laws",
    "discover_constants",
    "Conjecture",
    "subclass_laws",
    "bound_conjectures",
    "novel_subclass_laws",
    "is_subclass_specific",
    "RefutationResult",
    "refute",
    "ProofNode",
    "proof_tree",
    "render_tree",
    "check_proof",
    "independently_verify",
    "Verdict",
    "judge",
    "judge_task",
    "judge_induction",
    "judge_inequality",
    "judge_identity",
    "ArithmeticFinding",
    "run_arithmetic_discovery",
    "discover_and_prove",
    "discovered_modulus",
    "first_counterexample",
    "DiscoveryReport",
    "run_report",
    "render",
    "spectrum",
    "num_distinct_eigenvalues",
    "spectrum_confirms_moments",
    "discover_spectral_laws",
    "spectral_radius",
    "run_spectral_bounds",
    "SpectralBoundFinding",
    "SumIdentityFinding",
    "run_sequence_discovery",
    "discover_closed_form",
    "prove_modular_divisibility",
    "prove_by_residues",
    "factor_prime_powers",
]
