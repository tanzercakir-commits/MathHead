"""Discovery Track AC — the research director: cross-cycle state + rule-based strategy selection."""
from mathhead.discovery.director import CycleResult, ResearchDirector
from mathhead.discovery.knowledge_graph import from_report
from mathhead.discovery.lemma_ranking import rank_lemmas
from mathhead.discovery.report import run_report


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


def test_director_goal_choice_uses_the_t2_lemma_ranking():
    # pin the integration: the director's top_lemma is exactly lemma_ranking's top pick on the same report
    d = ResearchDirector()
    res = d.run_cycle(max_n=4)
    ranked = rank_lemmas(from_report(run_report(max_n=4)))
    if ranked:
        assert res.top_lemma["statement"] == ranked[0].statement
        assert res.top_lemma["priority"] == ranked[0].priority


def test_strategy_targets_the_highest_priority_open_conjecture():
    # AC0 now selects by importance × likelihood (T2), exposed as top_lemma — not raw entanglement
    d = ResearchDirector()
    res = d.run_cycle(max_n=4)
    if res.top_lemma:
        assert res.next_goal.startswith("settle open conjecture:")
        assert res.top_lemma["statement"] in res.next_goal          # the T2 top pick drives the goal
        assert 0.0 <= res.top_lemma["priority"] <= 1.0


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
