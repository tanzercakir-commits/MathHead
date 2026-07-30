"""Discovery Track P4 — cross-domain analogy detection (same technique across domains)."""
from mathhead.discovery import run_report
from mathhead.discovery.analogy import find_analogies


def test_analogies_span_multiple_domains():
    analogies = find_analogies(run_report(max_n=5))
    assert analogies
    for a in analogies:
        assert len(a.domains) >= 2                      # by definition an analogy crosses domains
        assert len(set(a.domains)) == len(a.domains)    # distinct domains


def test_constructive_bijection_analogy_is_found():
    by_tech = {a.technique: a for a in find_analogies(run_report(max_n=5))}
    assert "constructive bijection" in by_tech
    # the bijection technique proves facts in both permutations and integer partitions
    doms = by_tech["constructive bijection"].domains
    assert "permutations" in doms and "integer partitions" in doms


def test_report_carries_analogies():
    r = run_report(max_n=5)
    assert r.meta["analogies"]
    from mathhead.discovery import render
    assert "CROSS-DOMAIN ANALOGIES" in render(r)


def test_analogies_are_deterministic():
    a = [(x.technique, x.domains) for x in find_analogies(run_report(max_n=4))]
    b = [(x.technique, x.domains) for x in find_analogies(run_report(max_n=4))]
    assert a == b
