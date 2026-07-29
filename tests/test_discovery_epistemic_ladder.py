"""Discovery Track AA3 — the 4-rung epistemic ladder that classifies every finding by solidity."""
from mathhead.discovery import run_report
from mathhead.discovery.epistemic_ladder import (
    LEVELS,
    classify,
    ladder_summary,
    rung_of,
)


def test_levels_are_the_four_document_rungs():
    assert LEVELS == ("DISCOVERED_HEURISTIC", "EMPIRICALLY_VALIDATED",
                      "FORMALLY_SPECIFIED", "FORMALLY_PROVED")


def test_kernel_verified_arithmetic_is_formally_proved():
    r = run_report(max_n=5)
    assert rung_of("(n**3 - n) % 6 == 0", r) == "FORMALLY_PROVED"       # kernel + independently verified


def test_solver_confirmed_values_are_formally_specified():
    r = run_report(max_n=5)
    assert rung_of("chromatic_number(K4)=4", r) == "FORMALLY_SPECIFIED"  # solver-confirmed instance


def test_mined_law_is_empirically_validated():
    r = run_report(max_n=5)
    # the handshake lemma holds on the whole sample but isn't universally proven here
    assert rung_of("2*num_edges = sum_degrees", r) == "EMPIRICALLY_VALIDATED"


def test_every_non_refuted_finding_gets_a_rung():
    r = run_report(max_n=5)
    c = classify(r)
    classified = sum(len(v) for v in c.values())
    non_refuted = (len(r.proved) + len(r.empirical_laws) + len(r.open_bounded)
                   + sum(1 for f in r.frontier if f.get("confirmed"))
                   + sum(1 for e in r.explanations
                         if e.get("status") in ("structural_argument", "constructive_bijection")))
    assert classified == non_refuted


def test_ladder_summary_counts_match_classify():
    r = run_report(max_n=5)
    s = ladder_summary(r)
    c = classify(r)
    assert all(s[lvl] == len(c[lvl]) for lvl in LEVELS)
    assert s["FORMALLY_PROVED"] >= 11                          # 7 modular + 4 sums at least


def test_refuted_items_are_off_the_ladder():
    r = run_report(max_n=5)
    c = classify(r)
    on_ladder = {stmt for v in c.values() for stmt in v}
    for x in r.refuted:
        assert x["statement"] not in on_ladder                # refutations are negative knowledge, not rungs
