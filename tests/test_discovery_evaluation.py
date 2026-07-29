"""Discovery Track AF — the honest scorecard: correctness, attribution to known results, novelty."""
from mathhead.discovery import run_report
from mathhead.discovery.evaluation import attribute, evaluate, render_scorecard


def test_known_results_are_attributed():
    assert attribute("2*num_edges = sum_degrees")[0] == "Handshake Lemma"
    assert attribute("inv and maj are equidistributed over S_n  (Mahonian)")[1] == "MacMahon 1913"
    assert attribute("|S_n| = n!")[1] == "OEIS A000142"
    assert attribute("(n**3 - n) % 6 == 0") is not None            # elementary number theory


def test_everything_the_engine_produces_is_attributable():
    r = run_report(max_n=5)
    card = evaluate(r)
    # the honest bottom line: 100% of current findings map to known mathematics
    assert card.attributed_known == card.total
    assert card.unattributed == []


def test_novelty_is_honestly_zero():
    r = run_report(max_n=5)
    card = evaluate(r)
    assert card.novel_candidates == []                              # nothing novel-to-literature
    assert "rediscovers known mathematics" in card.notes
    assert "NOT established" in card.notes                          # honest about the corpus gap


def test_verified_count_is_positive_and_bounded():
    r = run_report(max_n=5)
    card = evaluate(r)
    assert 0 < card.verified <= card.total
    assert card.verified >= 11                                      # kernel-verified arithmetic + sums


def test_scorecard_renders_the_honest_headline():
    r = run_report(max_n=5)
    text = render_scorecard(evaluate(r))
    assert "novel-to-literature: 0 established" in text
    assert "rediscovers known mathematics" in text


def test_report_meta_carries_the_scorecard():
    r = run_report(max_n=5)
    sc = r.meta["scorecard"]
    assert sc["novel_established"] == 0 and sc["attributed_known"] == sc["total"]
