"""Discovery X1/W2 — the structured catalog of known results and attribution."""
from mathhead.discovery import run_report
from mathhead.discovery.known_results import (
    CATALOG,
    attribute,
    attributed_findings,
    catalog_size,
    domains,
)


def test_catalog_entries_are_well_formed():
    assert catalog_size() >= 20
    for kr in CATALOG:
        assert kr.name and kr.reference and kr.domain and kr.markers


def test_attribution_carries_name_and_reference():
    assert attribute("2*num_edges = sum_degrees").name == "Handshake Lemma"
    assert attribute("inv and maj are equidistributed over S_n  (Mahonian)").reference == "MacMahon 1913"
    assert attribute("|S_n| = n!").reference == "OEIS A000142"
    assert attribute("something the engine never produced xyz") is None


def test_catalog_spans_all_five_domains():
    assert set(domains()) == {"graphs", "arithmetic", "permutations",
                              "integer partitions", "set partitions"}


def test_every_reported_finding_is_attributed_with_a_citation():
    rows = attributed_findings(run_report(max_n=5))
    assert rows
    assert all(r["known"] is not None for r in rows)          # nothing unattributed
    assert all(r["reference"] != "—" for r in rows)           # every one cited
