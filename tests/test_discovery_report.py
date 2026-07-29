"""Discovery AC2 — one honest run report across both domains."""
from mathhead.discovery import DiscoveryReport, render, run_report


def test_report_has_all_four_honest_sections():
    r = run_report(max_n=6)
    assert isinstance(r, DiscoveryReport)
    assert r.proved and r.empirical_laws and r.refuted and r.open_bounded  # all populated


def test_key_findings_land_in_the_right_section():
    r = run_report(max_n=6)
    proved = " ".join(x["statement"] for x in r.proved)
    empirical = " ".join(x["statement"] for x in r.empirical_laws)
    refuted = " ".join(x["statement"] for x in r.refuted)
    assert "% 2 == 0" in proved                               # arithmetic parity, formally proved
    assert "sum_(i=1..n) 2*i - 1" in proved                   # a sum identity, proved via MathHead
    assert "2*num_edges = sum_degrees" in empirical           # handshake, empirical
    assert "num_triangles <= num_edges" in refuted            # the artifact bound, killed


def test_refuted_items_carry_a_counterexample():
    r = run_report(max_n=6)
    assert all("counterexample" in x or x.get("status") == "refuted" for x in r.refuted)
    tri = next(x for x in r.refuted if x["statement"] == "num_triangles <= num_edges")
    assert tri["counterexample"]["num_triangles"] == 16 and tri["counterexample"]["num_edges"] == 14


def test_report_is_deterministic():
    a, b = run_report(max_n=5), run_report(max_n=5)
    assert [x["statement"] for x in a.proved] == [x["statement"] for x in b.proved]
    assert [x["statement"] for x in a.refuted] == [x["statement"] for x in b.refuted]


def test_render_produces_readable_markdown():
    text = render(run_report(max_n=5))
    assert text.startswith("# MathHead — Discovery Run Report")
    for header in ("PROVED", "REFUTED", "DISCOVERED", "OPEN"):
        assert header in text
