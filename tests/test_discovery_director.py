"""Discovery Track AC — the research director: cross-cycle state + rule-based strategy selection."""
from mathhead.discovery.director import CycleResult, ResearchDirector


def test_single_cycle_produces_a_result_and_next_goal():
    d = ResearchDirector()
    res = d.run_cycle(max_n=3)
    assert isinstance(res, CycleResult)
    assert res.cycle == 1 and res.max_n == 3
    assert res.ladder["FORMALLY_PROVED"] >= 11          # kernel-verified arithmetic + identities
    assert res.next_goal                                # a strategy was chosen


def test_dead_ends_accumulate_deduped_across_cycles():
    d = ResearchDirector()
    d.run_cycle(max_n=3)
    total_after_1 = len(d.memory.records())
    d.run_cycle(max_n=3)                                # same bound → same refutations
    total_after_2 = len(d.memory.records())
    assert total_after_2 == total_after_1               # nothing new: fingerprints dedup across cycles


def test_new_findings_taper_as_the_sample_repeats():
    d = ResearchDirector()
    first = d.run_cycle(max_n=3).new_findings
    second = d.run_cycle(max_n=3).new_findings
    assert first > 0 and second == 0                    # everything from a repeated bound is already seen


def test_strategy_targets_the_open_frontier():
    d = ResearchDirector()
    res = d.run_cycle(max_n=4)
    if res.open_frontier:
        assert res.next_goal.startswith("settle open conjecture:")
        assert res.open_frontier[0]["statement"] in res.next_goal


def test_session_summary_reports_progression():
    d = ResearchDirector()
    summary = d.run_session(n_cycles=2, start_n=3)
    assert summary["cycles_run"] == 2
    assert len(summary["ladder_progression"]) == 2
    assert summary["total_dead_ends_learned"] >= 3
    assert summary["next_goal"]


def test_director_follows_its_own_recommendation():
    d = ResearchDirector()
    d.run_session(n_cycles=2, start_n=3)
    # cycle 2's goal is whatever cycle 1 recommended
    assert d.cycles[1].goal == d.cycles[0].next_goal
