"""Discovery S2 — resource-bounded proof-strategy portfolio with a budget manager."""
from mathhead.discovery.kernel import poly_from_sympy
from mathhead.discovery.portfolio import run_portfolio

_N3 = poly_from_sympy("n**3 - n")     # 6 | n³−n
_N5 = poly_from_sympy("n**5 - n")     # 30 | n⁵−n


def test_ample_budget_solves_and_the_cheapest_proof_wins():
    r = run_portfolio(6, _N3, 100)
    assert r.status == "solved" and r.winner == "direct-residue"     # cost 6 < CRT cost 7
    launched = [o for o in r.outcomes if o.launched]
    assert r.spent == sum(o.cost for o in launched)


def test_tight_budget_launches_only_the_affordable_strategy():
    # CRT (2+3+5+3 = 13) fits; direct-residue (30) does not
    r = run_portfolio(30, _N5, 15)
    assert r.status == "solved" and r.winner == "crt-prime-powers"
    skipped = {o.name for o in r.outcomes if not o.launched}
    assert skipped == {"direct-residue"}


def test_budget_too_small_is_reported_as_exhausted_not_a_proof():
    r = run_portfolio(30, _N5, 5)
    assert r.status == "exhausted" and r.winner is None and r.spent == 0
    assert all(not o.launched and o.outcome == "skipped" for o in r.outcomes)


def test_false_claim_runs_and_is_refuted_not_hidden():
    # 5 ∤ n³−n (n=2 → 6); a strategy runs and refutes it — status is unsolved, never "solved"
    r = run_portfolio(5, _N3, 100)
    assert r.status == "unsolved" and r.winner is None
    assert any(o.launched and o.outcome == "refuted" for o in r.outcomes)


def test_prime_modulus_offers_only_the_direct_strategy():
    r = run_portfolio(2, poly_from_sympy("n**2 - n"), 100)
    assert [o.name for o in r.outcomes] == ["direct-residue"]
    assert r.status == "solved"


def test_winner_is_always_a_kernel_checked_proof():
    # invariant: the winner (if any) must have a "proved" outcome in the ledger — never fabricated
    for m, poly, budget in [(6, _N3, 100), (30, _N5, 15), (5, _N3, 100), (30, _N5, 5)]:
        r = run_portfolio(m, poly, budget)
        if r.winner is not None:
            won = next(o for o in r.outcomes if o.name == r.winner)
            assert won.launched and won.outcome == "proved"


def test_portfolio_run_is_deterministic():
    assert run_portfolio(30, _N5, 15) == run_portfolio(30, _N5, 15)
