"""v3P0 — the product's single-door check() API: the quickstart trio, CI-proven."""
from mathhead.discovery.product import check


def test_kernel_proof_path():
    r = check("6 | n^3 - n")
    assert (r.verdict, r.tier) == ("proved", "kernel_verified") and r.proof_hash


def test_modular_refutation_with_exact_witness():
    r = check("5 | n^3 - n")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness["n"] == 2 and r.witness["value_mod_m"] != 0


def test_sum_identity_proof_and_refutation():
    assert check("sum_(i=1..n) i = n*(n+1)/2").verdict == "proved"
    bad = check("sum_(i=1..n) i = n^2")
    assert bad.verdict == "refuted" and bad.witness["n"] == 2


def test_graph_bound_refuted_with_smallest_witness():
    r = check("num_triangles <= num_edges", max_n=6)
    assert r.verdict == "refuted" and r.witness["n"] == 6
    assert r.witness["num_triangles"] > r.witness["num_edges"]     # 16 > 14, exactly


def test_graph_bound_survivor_is_honestly_open():
    r = check("clique_number <= chromatic_number", max_n=6)
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT proved" in r.notes and "ALL" in r.checked_up_to


def test_unsupported_is_refused_never_guessed():
    r = check("the weather tomorrow")
    assert r.verdict == "unsupported" and "refuses to guess" in r.notes


def test_check_is_deterministic():
    a, b = check("num_triangles <= num_edges", max_n=6), check("num_triangles <= num_edges", max_n=6)
    assert (a.verdict, a.witness) == (b.verdict, b.witness)
