"""Discovery S3 — record proof-strategy failures into the failure memory + diagnostics."""
from mathhead.discovery.failure_memory import FailureMemory
from mathhead.discovery.kernel import poly_from_sympy
from mathhead.discovery.portfolio import run_portfolio
from mathhead.discovery.strategy_log import (
    diagnose_portfolio,
    log_and_diagnose,
    log_portfolio_run,
)

_N3 = poly_from_sympy("n**3 - n")
_N5 = poly_from_sympy("n**5 - n")

_SOLVED = run_portfolio(6, _N3, 100)          # direct-residue wins
_EXHAUSTED = run_portfolio(30, _N5, 5)        # budget too small
_UNSOLVED = run_portfolio(5, _N3, 100)        # 5 ∤ n³−n → refuted, nothing proves it


def test_exhausted_and_unsolved_are_recorded_solved_is_not():
    mem = FailureMemory()
    assert log_portfolio_run(mem, _SOLVED, "6|n3-n") is None          # success ⇒ nothing to learn
    assert log_portfolio_run(mem, _EXHAUSTED, "30|n5-n@5") is not None
    assert log_portfolio_run(mem, _UNSOLVED, "5|n3-n") is not None
    assert mem.summary() == {"timeout": 1, "dead_end": 1}             # exhausted→timeout, unsolved→dead_end


def test_recorded_failure_carries_the_strategy_ledger():
    mem = FailureMemory()
    log_portfolio_run(mem, _EXHAUSTED, "30|n5-n@5")
    rec = mem.records("timeout")[0]
    assert rec.detail["status"] == "exhausted" and rec.detail["skipped"]   # names the unaffordable strategies


def test_logging_is_idempotent():
    mem = FailureMemory()
    log_portfolio_run(mem, _UNSOLVED, "5|n3-n")
    log_portfolio_run(mem, _UNSOLVED, "5|n3-n")                       # same failure again
    assert len(mem.records()) == 1                                    # deduped by fingerprint


def test_diagnostics_count_outcomes_and_strategy_usage():
    d = diagnose_portfolio([_SOLVED, _EXHAUSTED, _UNSOLVED])
    assert d.runs == 3 and d.solved == 1 and d.exhausted == 1 and d.unsolved == 1
    assert d.launched.get("direct-residue", 0) >= 1


def test_bottleneck_is_the_most_skipped_strategy():
    # at a tight budget on a composite modulus, direct-residue (cost m) is skipped while CRT fits
    runs = [run_portfolio(30, _N5, 15), run_portfolio(30, _N5, 15)]
    d = diagnose_portfolio(runs)
    assert d.skipped.get("direct-residue", 0) == 2 and d.bottleneck == "direct-residue"


def test_log_and_diagnose_runs_the_full_pass():
    mem = FailureMemory()
    d = log_and_diagnose(mem, [_SOLVED, _EXHAUSTED, _UNSOLVED], ["a", "b", "c"])
    assert d.runs == 3 and len(mem.records()) == 2                    # 2 failures logged, solved skipped


def test_diagnostics_are_deterministic():
    assert diagnose_portfolio([_SOLVED, _EXHAUSTED]) == diagnose_portfolio([_SOLVED, _EXHAUSTED])
