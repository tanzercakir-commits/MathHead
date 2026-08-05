"""v4F1 — check() coverage wave 1: polynomial congruences p(n) ≡ q(n) (mod m), the mirrored '>='
and equality claims on graph invariants, and comparative sum inequalities — all through the single
door, every verdict honestly tiered. Tier inflation is the highest-priority bug class: the tests
below pin the CEILING of each path (an equality scan is NEVER 'proved'; a z3 real counterexample is
NEVER a refutation)."""
from mathhead.discovery.product import check

# ---------------------------------------------------------------- polynomial congruence -------


def test_congruence_proved_unicode():
    r = check("n^2 + n ≡ 0 (mod 2)")
    assert (r.structure, r.verdict, r.tier) == ("polynomial_congruence", "proved", "kernel_verified")
    assert r.proof_hash and "reduced to 2 | (p − q)" in r.notes


def test_congruence_proved_ascii_variant():
    r = check("n^2 = n mod 2")
    assert (r.verdict, r.tier) == ("proved", "kernel_verified") and r.proof_hash


def test_congruence_reduction_matches_the_direct_modular_form():
    # p ≡ q (mod m) reduces to m | (p−q): the SAME kernel term, hence the SAME proof hash.
    assert check("n^3 ≡ n (mod 6)").proof_hash == check("6 | n^3 - n").proof_hash


def test_congruence_refuted_with_self_verifying_residue_witness():
    r = check("n^2 ≡ n (mod 3)")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    n = r.witness["n"]
    assert (n * n - n) % 3 != 0                                  # independent conviction
    assert r.witness["lhs_mod_m"] != r.witness["rhs_mod_m"]


def test_congruence_non_integer_coefficients_are_honestly_unsupported():
    r = check("n/2 ≡ 0 (mod 2)")
    assert (r.verdict, r.tier) == ("unsupported", "none") and "integer-coefficient" in r.notes


def test_congruence_foreign_symbol_is_honestly_unsupported():
    r = check("x^2 ≡ x (mod 2)")
    assert r.verdict == "unsupported" and "refuses to guess" in r.notes


# ------------------------------------------------- v4F1 honesty fixes on the modular door -----


def test_modular_rational_coefficients_no_longer_fake_a_proof():
    # BEFORE v4F1: poly_from_sympy int()-truncated n/2 → (0,) → "2 | n/2" was a FALSE kernel proof.
    r = check("2 | n/2")
    assert (r.verdict, r.tier) == ("unsupported", "none") and r.proof_hash == ""


def test_modular_foreign_symbol_no_longer_crashes_the_single_door():
    r = check("6 | x^3 - x")                                      # used to raise TypeError
    assert r.verdict == "unsupported" and "refuses to guess" in r.notes


def test_modular_zero_modulus_is_refused_not_proved():
    # BEFORE v4F1: "0 | n" came back proved/kernel_verified (mod-1 collapse in prime-power split).
    r = check("0 | n")
    assert (r.verdict, r.tier) == ("unsupported", "none")


def test_huge_modulus_is_an_honest_refusal_not_a_hang():
    r = check("1000001 | n")
    assert (r.verdict, r.tier) == ("unsupported", "none")
    assert "infeasible; bound = 10^6" in r.notes
    c = check("n ≡ 0 (mod 1000001)")
    assert c.verdict == "unsupported" and "infeasible; bound = 10^6" in c.notes


# ------------------------------------------------------- graph '>=' mirror + '==' equality ----


def test_graph_ge_mirror_refuted_with_the_same_witness_as_le():
    r = check("num_edges >= num_triangles", max_n=6)
    assert (r.structure, r.verdict) == ("graph_inequality", "refuted")
    assert r.witness["n"] == 6 and r.witness["num_triangles"] > r.witness["num_edges"]


def test_graph_ge_refuted_smallest_order():
    r = check("min_degree >= max_degree", max_n=5)
    assert r.verdict == "refuted" and r.witness["n"] == 3        # the path P3 already convicts


def test_graph_ge_survivor_is_honestly_open():
    r = check("chromatic_number >= clique_number", max_n=5)
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT proved" in r.notes


def test_graph_equality_handshake_is_open_never_proved():
    r = check("sum_degrees == 2*num_edges", max_n=5)              # a THEOREM — the scan cannot know
    assert (r.structure, r.verdict, r.tier) == ("graph_equality", "open",
                                                "no_counterexample_within_bound")
    assert "universal claim not proved; holds for all connected graphs up to n=5" in r.notes


def test_graph_equality_single_equals_variant():
    r = check("sum_degrees = 2*num_edges", max_n=4)
    assert (r.structure, r.verdict) == ("graph_equality", "open")


def test_graph_equality_refuted_in_either_direction():
    r = check("num_vertices == num_edges", max_n=4)
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness["n"] == 2 and r.witness["num_vertices"] != r.witness["num_edges"]


def test_graph_equality_with_offset_refuted():
    r = check("independence_number = matching_number + 1", max_n=4)
    assert r.verdict == "refuted"
    assert r.witness["independence_number"] != r.witness["matching_number"] + 1


def test_graph_le_behavior_is_unchanged():                        # backward-compat pin
    r = check("num_triangles <= num_edges", max_n=6)
    assert (r.structure, r.verdict) == ("graph_inequality", "refuted") and r.witness["n"] == 6


# ------------------------------------------------------------- comparative sum inequality -----


def test_sum_le_proved_via_kernel_closed_form_plus_z3():
    r = check("sum_(i=1..n) i <= n^2")
    assert (r.structure, r.verdict, r.tier) == ("sum_inequality", "proved", "solver_verified")
    assert "closed form kernel_verified; inequality step z3" in r.notes
    assert r.proof_hash == ""     # the hash field is reserved for kernel proofs of the STATEMENT


def test_sum_ge_proved_via_kernel_closed_form_plus_z3():
    r = check("sum_(i=1..n) i^2 >= n^2")
    assert (r.verdict, r.tier) == ("proved", "solver_verified")


def test_sum_ge_refuted_smallest_witness():
    r = check("sum_(i=1..n) i >= n^2")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness == {"n": 2, "lhs_sum": "3", "rhs": "4"}      # 1+2 = 3 < 4 = 2², exactly


def test_sum_le_refuted_smallest_witness():
    r = check("sum_(i=1..n) i^2 <= n^2")
    assert r.verdict == "refuted" and r.witness["n"] == 2         # 5 > 4, exactly


def test_sum_z3_integer_hint_is_upgraded_only_after_exact_reverification():
    # Σi = n²/2 + n/2 <= n²/2 + 100 fails first at n=201 — beyond the exact scan. z3's real model
    # lands on the integer 201; the engine re-verifies by DIRECT exact summation (no solver in the
    # loop) and only then refutes.
    r = check("sum_(i=1..n) i <= n^2/2 + 100")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness["n"] == 201 and r.witness["exact"] == "direct exact summation"
    assert r.witness["lhs_sum"] == "20301" and r.witness["rhs"] == "40601/2"   # 20301 > 20300.5
    assert sum(range(1, 202)) == 20301                            # independent conviction
    assert "not necessarily the smallest witness" in r.notes


def test_sum_non_integer_real_counterexample_stays_open():
    # Σ(2i−1) = n² <= n² + (n−1)(n−2)/2 holds at EVERY integer n >= 1 but fails on (1,2) over the
    # reals — z3's non-integer model must upgrade NOTHING.
    r = check("sum_(i=1..n) (2*i-1) <= n^2 + (n-1)*(n-2)/2")
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT an integer witness" in r.notes and r.witness == {}


def test_sum_grammar_rejection_is_named_not_conflated_with_solver_unknown():
    r = check("sum_(i=1..n) i <= 2^n")                            # 2^n is outside the z3 grammar
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "grammar/parse" in r.notes and "parse error" in r.notes


def test_sum_open_when_no_polynomial_closed_form_exists():
    r = check("sum_(i=1..n) 2^i <= 2^(n+1)")                      # true, but no poly proof route
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "no kernel-verified polynomial closed form" in r.notes


def test_sum_inequality_with_stray_symbols_is_honestly_unsupported():
    r = check("sum_(i=1..n) i <= weather")
    assert (r.verdict, r.tier) == ("unsupported", "none") and "refuses to guess" in r.notes


# ------------------------------------------------------------------------- the single door ----


def test_unsupported_message_knows_the_new_surface():
    r = check("the weather tomorrow")
    assert r.verdict == "unsupported"
    for phrase in ("congruences", "sum inequalities", "== [k*]invB", "refuses to guess"):
        assert phrase in r.notes


def test_new_forms_are_deterministic():
    for s in ("n^2 ≡ n (mod 3)", "sum_(i=1..n) i <= n^2", "num_vertices == num_edges"):
        a, b = check(s, max_n=4), check(s, max_n=4)
        assert (a.verdict, a.tier, a.witness) == (b.verdict, b.tier, b.witness)
