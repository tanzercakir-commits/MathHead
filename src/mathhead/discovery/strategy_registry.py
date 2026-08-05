"""
mathhead.discovery.strategy_registry — the strategy LEDGER (roadmap S0).

S0 asks for a *kayıt defteri* (registry) of proof/refutation strategies. This module IS that ledger:
every strategy the engine actually ships is registered with its taxonomy kind and a dotted reference
to the callable that implements it. The references are RESOLVABLE (`resolve` imports them), so the
ledger cannot rot silently — a renamed function fails `validate()` in CI.

HONEST COVERAGE — the ledger records what is MISSING too. The classical strategies the roadmap
enumerates but the engine does not implement (MCTS, resolution, superposition, term rewriting,
quantifier elimination, Gröbner bases, ILP, learned best-first guidance) are listed with
`implemented=False`. The registry never inflates: an entry is `implemented=True` only if its
callable exists and is importable today.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class StrategyEntry:
    name: str            # unique ledger name
    kind: str            # taxonomy: induction / case-split / compositional / SAT / stochastic / …
    ref: str | None      # "module:callable" for implemented strategies, None otherwise
    implemented: bool
    note: str            # one honest line: what it does / why it is absent


REGISTRY: tuple = (
    # --- implemented, callable-referenced (the engine's real arsenal) --------------------------
    StrategyEntry("induction", "induction",
                  "mathhead.discovery.judge:judge_induction", True,
                  "Z3-backed induction on n for modular claims"),
    StrategyEntry("residue-exhaustion", "exhaustive case-split",
                  "mathhead.discovery.strategy:prove_by_residues", True,
                  "complete finite case-split on n mod m"),
    StrategyEntry("crt-factoring", "compositional (divide & conquer)",
                  "mathhead.discovery.strategy:prove_modular_divisibility", True,
                  "factor the modulus, prove prime-power parts, CRT-combine"),
    StrategyEntry("kernel-proof-term", "LCF kernel",
                  "mathhead.discovery.kernel:prove_divides", True,
                  "emit a RESIDUE/CRT proof term, kernel mints the Theorem"),
    StrategyEntry("sum-induction", "induction",
                  "mathhead.discovery.kernel:prove_sum_identity", True,
                  "base case + kernel-checked telescoping step for Σf(i)=g(n)"),
    StrategyEntry("counterexample-scan", "exhaustive search (refutation)",
                  "mathhead.discovery.refute:refute", True,
                  "counterexample-first bounded scan over small objects"),
    StrategyEntry("sat-encoding", "SAT",
                  "mathhead.discovery.ramsey_sat:ramsey_decide", True,
                  "CNF encoding + solver, witnesses independently re-verified"),
    StrategyEntry("rup-unsat-check", "SAT (proof checking)",
                  "mathhead.discovery.rup_check:check_drup_proof", True,
                  "independent RUP/DRUP check of solver UNSAT proofs"),
    StrategyEntry("simulated-annealing", "stochastic local search",
                  "mathhead.discovery.adaptive_search:hunt", True,
                  "seeded SA over graph spaces; integer certificates decide"),
    StrategyEntry("evolutionary-program-search", "evolutionary",
                  "mathhead.discovery.program_search:evolve", True,
                  "mutation-only elitist evolution over an expression DSL"),
    StrategyEntry("generator-evolution", "evolutionary",
                  "mathhead.discovery.frankl:hunt_frankl", True,
                  "generator evolution over union-closed set families"),
    StrategyEntry("interval-arithmetic", "interval / numerical enclosure",
                  "mathhead.discovery.interval_check:double_star_slack_interval", True,
                  "directed-rounding certified enclosures (three-valued verdicts)"),
    StrategyEntry("constructive-certificate", "constructive witness",
                  "mathhead.discovery.graph_proofs:certify_chi_le_delta_plus_1", True,
                  "greedy-coloring / clique witnesses, independently checkable"),
    StrategyEntry("portfolio-race", "portfolio orchestration",
                  "mathhead.discovery.portfolio:run_portfolio", True,
                  "budgeted cheapest-first race among applicable strategies (S2)"),
    # --- honestly absent (enumerated by the roadmap, not implemented) --------------------------
    StrategyEntry("mcts", "search guidance", None, False,
                  "Monte-Carlo tree search — not implemented"),
    StrategyEntry("resolution", "saturation", None, False,
                  "first-order resolution — not implemented"),
    StrategyEntry("superposition", "saturation", None, False,
                  "superposition calculus — not implemented"),
    StrategyEntry("term-rewriting", "rewriting", None, False,
                  "completion / rewriting engine — not implemented"),
    StrategyEntry("quantifier-elimination", "QE", None, False,
                  "real/Presburger QE — not implemented"),
    StrategyEntry("groebner-basis", "algebraic", None, False,
                  "Gröbner-basis reasoning — not implemented"),
    StrategyEntry("ilp", "optimization", None, False,
                  "integer linear programming attack — not implemented"),
    StrategyEntry("learned-guidance", "learned best-first", None, False,
                  "RL/learned proof guidance — open research (S4 🔴)"),
)


def implemented() -> list:
    return [e for e in REGISTRY if e.implemented]


def missing() -> list:
    return [e for e in REGISTRY if not e.implemented]


def resolve(entry: StrategyEntry):
    """Import and return the callable behind an implemented entry (raises if the ref rotted)."""
    if not entry.implemented or entry.ref is None:
        raise ValueError(f"strategy '{entry.name}' is not implemented — nothing to resolve")
    mod_name, fn_name = entry.ref.split(":")
    fn = getattr(import_module(mod_name), fn_name)
    if not callable(fn):
        raise TypeError(f"strategy '{entry.name}' ref {entry.ref} is not callable")
    return fn


def validate() -> dict:
    """Ledger integrity: unique names; every implemented ref resolves to a callable. Returns the
    honest coverage summary {implemented: n, missing: m}."""
    names = [e.name for e in REGISTRY]
    if len(names) != len(set(names)):
        raise ValueError("duplicate strategy names in the registry")
    for e in implemented():
        resolve(e)
    return {"implemented": len(implemented()), "missing": len(missing())}
