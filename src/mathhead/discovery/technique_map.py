"""
mathhead.discovery.technique_map — notation synonyms + problem-structure → technique map (v1 X2).

S1's portfolio selector needs to know WHICH instruments apply to WHAT. This is that map, kept honest by
construction: every technique entry names a REAL engine module.function, and a test imports each one —
the map cannot drift from the codebase without the suite failing. Plus the notation-synonym table the
track asks for (λ₁ = spectral radius; μ = ν = matching number; …), used by the statement classifier.
"""
from __future__ import annotations

SYNONYMS: dict = {
    "spectral radius": ("lambda1", "largest adjacency eigenvalue", "perron root"),
    "matching number": ("mu", "nu", "maximum matching size"),
    "independence number": ("alpha", "stability number"),
    "domination number": ("gamma",),
    "chromatic number": ("chi",),
    "clique number": ("omega",),
    "union-closed": ("frankl",),
}

# structure → [(technique, engine pointer "module.attr", verdict tier)]
TECHNIQUES: dict = {
    "modular_divisibility": [
        ("residue exhaustion (kernel)", "kernel.prove_divides", "kernel_verified"),
        ("CRT modulus-factoring", "strategy.prove_modular_divisibility", "formal_proof"),
        ("budgeted portfolio", "portfolio.run_portfolio", "kernel_verified"),
    ],
    "sum_identity": [
        ("SumInduction (kernel)", "kernel.prove_sum_identity", "kernel_verified"),
        ("closed-form fit + proof", "sequences.run_sequence_discovery", "kernel_verified"),
        ("program evolution + kernel", "program_search.conjecture_and_prove", "kernel_verified"),
    ],
    "graph_inequality": [
        ("counterexample-first scan", "refute.refute", "refuted_or_open"),
        ("adaptive SA hunt", "adaptive_search.hunt", "exact_certificate_or_honest_fail"),
        ("constructive certificate", "graph_proofs.certify_frontier_laws", "constructive_bounded"),
    ],
    "spectral_bound": [
        ("integer Sylvester certificate", "spectral_cert.certify_lambda1_plus_mu_below",
         "exact_integer_certificate"),
        ("interval enclosure", "interval_check.double_star_slack_interval", "interval_certified"),
        ("power iteration (steering only)", "conjecture_db.lambda1_power", "heuristic_float"),
    ],
    "finite_coloring_ramsey": [
        ("SAT encode + witness recheck", "ramsey_sat.ramsey_decide", "independently_verified_witness"),
    ],
    "set_family": [
        ("generator evolution + integer certificate", "frankl.hunt_frankl",
         "exact_certificate_or_honest_fail"),
    ],
    "constant_relation": [
        ("PSLQ two-precision", "pslq_hunt.find_relation", "numerical_conjecture"),
    ],
}

_KEYWORDS = {
    "modular_divisibility": ("divisible", "| n", "mod ", "divides"),
    "sum_identity": ("sum_", "sum of", "Σ", "partial sum"),
    "spectral_bound": ("lambda1", "spectral radius", "eigenvalue"),
    "finite_coloring_ramsey": ("ramsey", "colouring", "coloring of K_", "monochromatic"),
    "set_family": ("union-closed", "family of sets"),
    "constant_relation": ("zeta", "pi^", "constant relation"),
    "graph_inequality": ("<=", "graph",),          # the generic fallback — checked LAST
}


def classify_statement(text: str) -> str:
    """Deterministic keyword classifier → problem structure ('unknown' when nothing matches)."""
    low = text.lower()
    for structure, keys in _KEYWORDS.items():
        if any(k.lower() in low for k in keys):
            return structure
    return "unknown"


def suggest_techniques(text: str) -> list:
    """The S1 feed: classify, then list (technique, engine pointer, verdict tier) — strongest first."""
    return TECHNIQUES.get(classify_statement(text), [])
