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
    assert "2*num_edges = sum_degrees" in empirical           # handshake (universal), empirical
    assert "trees: num_vertices = num_edges + 1" in empirical  # a NOVEL tree law, kept
    assert "trees: 2*num_edges = sum_degrees" not in empirical  # restricted-universal, filtered (W0)
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


def test_proved_arithmetic_facts_are_independently_verified():
    r = run_report(max_n=5)
    modular = [x for x in r.proved if "% " in x["statement"]]
    assert modular and all(x.get("independently_verified") for x in modular)
    assert "independently verified" in render(r)          # surfaced in the report


def test_proved_arithmetic_facts_are_kernel_verified():
    r = run_report(max_n=5)
    modular = [x for x in r.proved if "% " in x["statement"]]
    assert modular and all(x.get("kernel_verified") for x in modular)
    assert "kernel-verified" in render(r)                 # surfaced in the report


def test_frontier_invariant_values_are_solver_confirmed():
    r = run_report(max_n=5)
    assert r.frontier and all(x["confirmed"] and x["certainty"] == "solver_verified"
                              for x in r.frontier)
    chi_k4 = next(x for x in r.frontier if x["invariant"] == "chromatic_number"
                  and x["graph"] == "K4")
    assert chi_k4["value"] == 4                           # χ(K4)=4, confirmed sat@4 ∧ unsat@3
    assert "FRONTIER" in render(r) and "solver_verified" in render(r)


def test_frontier_laws_land_in_open_and_refuted():
    r = run_report(max_n=5)
    open_stmts = " ".join(x["statement"] for x in r.open_bounded)
    refuted_stmts = " ".join(x["statement"] for x in r.refuted)
    assert "Dirac" in open_stmts                          # Dirac survived -> OPEN (unproven)
    assert "clique_number <= chromatic_number" in open_stmts   # ω ≤ χ survived
    assert "(connected and n>=3) => Hamiltonian" in refuted_stmts   # refuted by P3
    assert "chromatic_number <= max_degree" in refuted_stmts        # refuted (χ≤Δ)


def test_report_records_negative_knowledge_from_refutations():
    r = run_report(max_n=5)
    # every refuted finding becomes a recorded dead end (Track Y)
    assert r.meta["dead_ends"] == len(r.refuted) and r.meta["dead_ends"] >= 3
    assert "negative knowledge" in render(r)


def test_certified_coloring_laws_are_annotated_but_stay_open():
    r = run_report(max_n=5)
    by_stmt = {x["statement"]: x for x in r.open_bounded}
    # the 3 constructively-certified coloring laws carry the annotation...
    for law in ("chromatic_number <= max_degree + 1", "chromatic_number <= num_vertices",
                "clique_number <= chromatic_number"):
        assert by_stmt[law].get("certified") is True
        assert "constructive_bounded" in by_stmt[law]["note"]
    # ...but a Hamiltonicity implication (no certificate) is NOT marked certified
    assert by_stmt["Hamiltonian => connected"].get("certified") is False
    # and certified still means OPEN, never PROVED (honesty)
    assert all("constructive" not in x.get("certainty", "") for x in r.proved)
