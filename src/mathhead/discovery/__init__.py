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
  * kernel     — minimal LCF-style PROOF KERNEL (M1/M2): a Theorem exists only if a proof TERM is
                 kernel-checked; three judgments — Divides (RESIDUE/CRT), SumIdentity (SumInduction),
                 PolyIdentity (Identity); rational polys; forge-guarded; rejects false claims
  * congruence — DERIVE RESIDUE from the factor theorem (M-floor): shrinks the trusted base — residue
                 -exhaustion becomes a theorem about PolyIdentity, not a black-box axiom
  * cross_check — multi-path invariant consistency (O4): |E| four ways, #triangles three ways
                 (count / Handshake / trace / MathHead spectrum); catches any measurement bug
  * analogy    — cross-domain analogy detection (P4): the same proof technique (double counting,
                 bijection, recurrence) recurring across two+ domains
  * identities — factorization discovery, kernel-verified (PolyIdentity), that EXPLAINS the modular
                 divisibilities: n³−n = n(n−1)(n+1) ⇒ 3 consecutive ints ⇒ divisible by 3!=6
  * structural_explanations — WHY the graph laws hold: double counting (handshake), the clique bound
                 (ω≤χ), the cycle-degree argument (Hamiltonian⟹δ≥2); conclusion checked on the sample
  * epistemic_ladder — one 4-rung solidity axis (AA3): DISCOVERED → EMPIRICALLY_VALIDATED →
                 FORMALLY_SPECIFIED → FORMALLY_PROVED; classifies every finding, honestly
  * permutations — a THIRD object domain (proves the model generalizes): generate S_n, invariants
                 (inversions/descents/fixed points/cycles), discovered+explained laws (|S_n|=n!, …)
  * partitions  — a FOURTH object domain (number-theoretic): p(n) counts (A000041), rediscovers
                 Euler's distinct=odd theorem (A000009) and conjugation symmetry
  * set_partitions — a FIFTH object domain: Bell numbers (A000110), Stirling 2nd kind (A008277),
                 rediscovers B(n)=Σ_k S(n,k) with an independent Stirling-recurrence cross-check
  * bijections  — CONSTRUCTIVE bijections proving the equidistributions: Glaisher (Euler distinct=odd),
                 conjugation, and Foata's Φ (Mahonian inv~maj); verified on the sample (constructive_bijection)
  * director    — the research director (AC): goal-driven multi-cycle loop with cross-cycle memory;
                 accumulates dead ends, tracks ladder progress, picks the next goal from the frontier
  * evaluation  — the honest scorecard (AF): correctness + attribution to KNOWN results; states
                 plainly that novelty-vs-literature is 0 established (rediscovery, not discovery)
  * known_results — a structured, cited catalog of the KNOWN mathematics the engine touches (X1/W2);
                 the auditable basis for attribution and the honest 0-novel verdict
  * adversarial — red-team the verifier: a systematic battery of false claims (600+) the kernel and
                 checker must all reject, plus positive controls; proves soundness on the sweep
  * provenance — proof-artifact hash + axiom list + deterministic replay (M4/M5)
  * failure_memory — negative knowledge (Y): fingerprint dead ends so they're not re-walked;
                 distill reusable lessons (which witness refutes the most conjectures)
  * families    — parametric object families (N4): K_n, C_n, P_n, star, wheel, K_{a,b} at any size +
                 stratified sampling; invariants match known closed forms (a cross-check oracle)
  * adversarial_objects — random/adversarial/extreme generators (N5): degenerate + K_n/K_n−e +
                 seeded-random stress set; invariants survive it with 0 crashes
  * serialize   — generic object serialization + content-hash + reproducible ordering (N3), one
                 canonicaliser across all five object types (dedup, stable storage keys)
  * object_store — queryable store indexed by invariant (N6): add (dedup) → query(χ=3, triangles=0);
                 the substrate for targeted discovery / feature tables
  * interestingness — transparent heuristic ranking (W1): novelty/generality/surprise/usefulness/
                 compression/connectivity − triviality, with a per-component breakdown (not learned)
  * knowledge_graph — typed semantic graph of findings + relations (X0): theorem/law/conjecture/
                 counterexample/axiom nodes; depends_on/refuted_by/related_to edges; Mermaid export
  * impact       — structural impact analysis over the graph (X3): load-bearing axioms, hubs, and the
                 open frontier (most-entangled unresolved conjectures)

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
from .adversarial import RobustnessReport, robustness_report
from .adversarial_objects import (
    degenerate_graphs,
    extreme_graphs,
    random_graphs,
    stress_set,
)
from .analogy import Analogy, find_analogies
from .bijections import (
    BijectionCertificate,
    certify_mahonian_bijection,
    certify_partition_bijections,
    foata,
    glaisher_distinct_to_odd,
    glaisher_odd_to_distinct,
)
from .canonical import canonical_graph, canonical_key, is_isomorphic
from .checker import check_proof, independently_verify
from .coloring import (
    ColoringBoundFinding,
    ColoringVerification,
    coloring_bounds,
    verify_chromatic_number,
)
from .congruence import (
    ResidueDerivation,
    check_residue_derivation,
    crt_chain_is_derivable,
    derive_crt,
    derive_residue,
    residue_is_derivable,
)
from .conjectures import Conjecture, bound_conjectures, subclass_laws
from .cross_check import CrossCheck, all_consistent, cross_check, disagreements
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
from .identities import IdentityFinding, discover_factorization, run_identity_discovery
from .impact import impact_summary, load_bearing_axioms
from .interestingness import Interestingness
from .interestingness import rank as rank_interestingness
from .interestingness import score as score_interestingness
from .kernel import (
    CRT,
    Identity,
    KernelError,
    Residue,
    SumInduction,
    Theorem,
    check,
    prove_divides,
    prove_identity,
    prove_sum_identity,
)
from .knowledge_graph import (
    Edge,
    KnowledgeGraph,
    Node,
)
from .knowledge_graph import from_report as knowledge_graph_from_report
from .known_results import CATALOG, KnownResult, attributed_findings, catalog_size
from .director import CycleResult, ResearchDirector
from .epistemic_ladder import LEVELS, classify, ladder_summary, rung_of
from .evaluation import Scorecard, attribute, render_scorecard
from .evaluation import evaluate as evaluate_report
from .failure_memory import (
    AttemptRecord,
    FailureMemory,
    fingerprint,
    populate_from_refutations,
)
from .families import (
    FAMILIES,
    complete,
    complete_bipartite,
    cycle,
    path,
    star,
    stratified_sample,
    wheel,
)
from .provenance import KERNEL_VERSION, axioms_used, proof_hash, replay
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
from .object_store import ObjectStore
from .objects import Graph, MathObject
from .proof_tree import ProofNode, proof_tree, render_tree
from .refute import RefutationResult, refute
from .report import DiscoveryReport, render, run_report
from .partitions import (
    Partition,
    conjugate,
    count_partitions,
    discover_partition_laws,
    generate_partitions,
)
from .permutations import (
    Permutation,
    count_permutations,
    discover_distribution_laws,
    discover_permutation_laws,
    eulerian_number,
    generate_permutations,
    statistic_distribution,
)
from .relations import DiscoveredLaw, discover_constants, discover_linear_laws
from .serialize import content_hash, deduplicate, reproducible_sort, serialize
from .set_partitions import (
    SetPartition,
    count_set_partitions,
    discover_set_partition_laws,
    generate_set_partitions,
    stirling2,
)
from .structural_explanations import structural_explanations
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
    "SumInduction",
    "Identity",
    "KernelError",
    "check",
    "prove_divides",
    "prove_sum_identity",
    "prove_identity",
    "derive_residue",
    "check_residue_derivation",
    "residue_is_derivable",
    "ResidueDerivation",
    "derive_crt",
    "crt_chain_is_derivable",
    "cross_check",
    "all_consistent",
    "CrossCheck",
    "disagreements",
    "IdentityFinding",
    "discover_factorization",
    "run_identity_discovery",
    "axioms_used",
    "proof_hash",
    "replay",
    "KERNEL_VERSION",
    "FailureMemory",
    "AttemptRecord",
    "fingerprint",
    "populate_from_refutations",
    "FAMILIES",
    "complete",
    "cycle",
    "path",
    "star",
    "wheel",
    "complete_bipartite",
    "stratified_sample",
    "stress_set",
    "extreme_graphs",
    "degenerate_graphs",
    "random_graphs",
    "serialize",
    "content_hash",
    "reproducible_sort",
    "deduplicate",
    "ObjectStore",
    "Interestingness",
    "score_interestingness",
    "rank_interestingness",
    "KnowledgeGraph",
    "Node",
    "Edge",
    "knowledge_graph_from_report",
    "impact_summary",
    "load_bearing_axioms",
    "structural_explanations",
    "Permutation",
    "generate_permutations",
    "count_permutations",
    "discover_permutation_laws",
    "discover_distribution_laws",
    "statistic_distribution",
    "eulerian_number",
    "Partition",
    "generate_partitions",
    "count_partitions",
    "discover_partition_laws",
    "conjugate",
    "SetPartition",
    "generate_set_partitions",
    "count_set_partitions",
    "discover_set_partition_laws",
    "stirling2",
    "LEVELS",
    "classify",
    "ladder_summary",
    "rung_of",
    "ResearchDirector",
    "CycleResult",
    "Scorecard",
    "evaluate_report",
    "attribute",
    "render_scorecard",
    "CATALOG",
    "KnownResult",
    "attributed_findings",
    "catalog_size",
    "RobustnessReport",
    "robustness_report",
    "Analogy",
    "find_analogies",
    "BijectionCertificate",
    "certify_partition_bijections",
    "certify_mahonian_bijection",
    "foata",
    "glaisher_odd_to_distinct",
    "glaisher_distinct_to_odd",
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
