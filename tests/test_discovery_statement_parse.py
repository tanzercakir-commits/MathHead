"""Discovery M0 + V1 — judge-surface pin and statement decomposition."""
from mathhead.discovery.conjecture_db import AH_SPECTRAL_MATCHING, CONJECTURES
from mathhead.discovery.judge import Verdict, judge_induction
from mathhead.discovery.statement_parse import parse_statement


def test_m0_judge_envelope_is_pinned():
    # the judge SURFACE contract (M0): Verdict carries exactly these envelope fields
    import dataclasses
    assert [f.name for f in dataclasses.fields(Verdict)] == [
        "status", "certainty", "reason_code", "detail", "source_status", "engine"]
    a = judge_induction("(n*(n+1)) % 2 == 0", "n", 0, 1500)
    b = judge_induction("(n*(n+1)) % 2 == 0", "n", 0, 1500)
    assert (a.status, a.certainty, a.reason_code) == (b.status, b.certainty, b.reason_code)
    assert a.status == "proved"


def test_v1_parses_the_ah_statement():
    p = parse_statement(AH_SPECTRAL_MATCHING.statement)
    assert p.quantifier == "universal" and "connected graph" in p.domain
    assert p.n_min == 3 and p.relation == ">="
    assert "spectral radius" in p.invariants and "matching number" in p.invariants


def test_v1_parsed_domain_agrees_with_db_entries():
    for c in CONJECTURES.values():
        p = parse_statement(c.statement)
        assert p.quantifier == "universal"
        if "connected" in c.domain:
            assert "connected" in p.domain                 # the parse must match the recorded domain


def test_v1_unrecognized_is_reported_not_guessed():
    p = parse_statement("the weather tomorrow")
    assert p.unrecognized == ("the weather tomorrow",) and p.quantifier == "unknown"


def test_v1_is_deterministic():
    s = AH_SPECTRAL_MATCHING.statement
    assert parse_statement(s) == parse_statement(s)
