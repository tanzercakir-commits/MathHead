"""
mathhead.discovery.portfolio — resource-bounded portfolio EXECUTOR + budget manager (roadmap S2).

S0 is the strategy registry, S1 the classifier that PICKS a portfolio; S2 RUNS several strategies under
one shared budget and accounts for the resource each consumes. For a modular claim `m | p(n)` the kernel
offers two proof strategies with very different costs:

  * direct-residue     — one residue sweep at m: cost ≈ m residues checked;
  * crt-prime-powers   — a sweep at each prime power pᵢ^{eᵢ} + a CRT combine: cost ≈ Σ pᵢ^{eᵢ} + #parts,
    much cheaper than m when m is composite (30 → 2+3+5+3 = 13 vs 30).

The executor models an idealized PARALLEL race under a shared step-budget, deterministically (no OS
threads, no wall-clock — reproducibility first): it launches the affordable strategies cheapest-first
while their cumulative cost fits the budget, runs each (kernel-checked), and declares the WINNER to be
the lowest-cost strategy that actually proves the claim — the one that would finish first in a real
race. It reports a full ledger: cost per strategy, which were launched vs skipped (unaffordable), total
`spent`, the winner, and an honest `status`:

  * solved     — a launched strategy proved it (winner named);
  * unsolved   — strategies ran but none proved it (e.g. the claim is FALSE → refuted), NOT hidden;
  * exhausted  — the budget was too small to launch any strategy at all.

Honest by construction: it never reports a proof it did not kernel-check, and it never conceals that a
budget was too tight — it says `exhausted` and names the costs it could not afford.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .kernel import CRT, KernelError, Residue, _factor_prime_powers, check


def _residue_cost(m: int) -> int:
    return m                                          # sweep residues 0..m−1


def _crt_cost(m: int) -> int:
    pks = _factor_prime_powers(m)
    return sum(pks) + len(pks)                        # a sweep per prime power + a CRT combine step


def _run_residue(m: int, poly: tuple) -> str:
    try:
        check(Residue(m, poly))
        return "proved"
    except KernelError:
        return "refuted"


def _run_crt(m: int, poly: tuple) -> str:
    pks = _factor_prime_powers(m)
    try:
        check(CRT(tuple(Residue(pk, poly) for pk in pks)))
        return "proved"
    except KernelError:
        return "refuted"


def _strategies(m: int) -> list:
    """(name, cost, run) for every strategy applicable to modulus m, unsorted."""
    strat = [("direct-residue", _residue_cost(m), _run_residue)]
    if len(_factor_prime_powers(m)) > 1:              # CRT only helps for a composite modulus
        strat.append(("crt-prime-powers", _crt_cost(m), _run_crt))
    return strat


@dataclass
class StrategyOutcome:
    name: str
    cost: int                # deterministic step-cost estimate
    launched: bool           # did it fit within the shared budget?
    outcome: str             # "proved" | "refuted" | "skipped"


@dataclass
class PortfolioRun:
    modulus: int
    budget: int
    spent: int                       # total cost of the launched (concurrent) set
    winner: str | None               # lowest-cost strategy that proved it (first to finish)
    status: str                      # "solved" | "unsolved" | "exhausted"
    outcomes: list = field(default_factory=list)


def run_portfolio(m: int, poly: tuple, budget: int) -> PortfolioRun:
    """Run the modular-proof portfolio for `m | p(n)` under a shared step-`budget`, cheapest-first.
    A negative budget is a caller error (the ledger invariant `spent ≤ budget` must hold even when
    nothing launches) — rejected explicitly, never silently clamped."""
    if budget < 0:
        raise ValueError(f"budget must be ≥ 0, got {budget}")
    strategies = sorted(_strategies(m), key=lambda s: (s[1], s[0]))   # cheapest first, then by name
    launched, spent = [], 0
    for name, cost, _run in strategies:
        if spent + cost <= budget:                   # affordable alongside the already-launched set
            launched.append(name)
            spent += cost
    outcomes, winner = [], None
    for name, cost, run in strategies:
        if name in launched:
            out = run(m, poly)
            outcomes.append(StrategyOutcome(name, cost, True, out))
            if out == "proved" and winner is None:   # cheapest-first ⇒ first proof is the race winner
                winner = name
        else:
            outcomes.append(StrategyOutcome(name, cost, False, "skipped"))
    if winner is not None:
        status = "solved"
    elif launched:
        status = "unsolved"                          # ran, but nothing proved it (false claim, etc.)
    else:
        status = "exhausted"                         # budget too small to launch any strategy
    return PortfolioRun(m, budget, spent, winner, status, outcomes)
