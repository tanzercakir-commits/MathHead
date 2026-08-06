"""v3P4 — the docs gallery is EXECUTABLE: every claim in the manual runs in CI (docs cannot rot)."""
from pathlib import Path

from mathhead.discovery import check
from mathhead.discovery.cli import main

_MANUAL = Path(__file__).parent.parent / "docs" / "manual"


def test_manual_pages_exist():
    for page in ("index.md", "quickstart.md", "honesty.md", "examples.md", "api.md",
                 "whitepaper.md"):
        assert (_MANUAL / page).exists()


def test_quickstart_trio_runs_exactly_as_documented(capsys):
    assert main(["check", "6 | n^3 - n"]) == 0
    assert "proved   [kernel_verified]" in capsys.readouterr().out
    assert main(["check", "num_triangles <= num_edges", "--max-n", "6"]) == 0
    assert "refuted   [exact_integer_certificate]" in capsys.readouterr().out
    assert main(["check", "clique_number <= chromatic_number", "--max-n", "6"]) == 0
    assert "open   [no_counterexample_within_bound]" in capsys.readouterr().out


def test_example_1_modular_proof():
    r = check("30 | n^5 - n")
    assert r.verdict == "proved" and r.tier == "kernel_verified" and r.proof_hash


def test_example_2_refutation_witness():
    r = check("num_triangles <= num_edges", max_n=6)
    assert r.witness["num_triangles"] == 16 and r.witness["num_edges"] == 14


def test_quickstart_wave1_runs_exactly_as_documented(capsys):     # v4F1
    assert main(["check", "n^2 = n mod 2"]) == 0
    assert "proved   [kernel_verified]" in capsys.readouterr().out
    assert main(["check", "sum_degrees == 2*num_edges", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    assert "open   [no_counterexample_within_bound]" in out
    assert "universal claim not proved; holds for all connected graphs up to n=6" in out
    assert main(["check", "sum_(i=1..n) i <= n^2"]) == 0
    assert "proved   [solver_verified]" in capsys.readouterr().out


def test_example_6_congruence_both_ways():                        # v4F1
    good = check("n^5 ≡ n (mod 30)")
    assert (good.verdict, good.tier) == ("proved", "kernel_verified") and good.proof_hash
    bad = check("n^2 ≡ n (mod 3)")
    assert (bad.verdict, bad.tier) == ("refuted", "exact_integer_certificate")
    assert bad.witness == {"n": 2, "lhs_mod_m": 1, "rhs_mod_m": 2, "difference_mod_m": 2}
    assert check("n/2 ≡ 0 (mod 2)").verdict == "unsupported"      # honest, never truncated


def test_example_7_graph_equality_never_proved(capsys):           # v4F1
    r = check("sum_degrees == 2*num_edges", max_n=6)              # the handshake lemma
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "ALL 142 connected graphs" in r.checked_up_to
    bad = check("num_vertices == num_edges")
    assert bad.verdict == "refuted" and bad.witness["n"] == 2 and bad.witness["edges"] == [(0, 1)]
    mirror = check("num_edges >= num_triangles", max_n=6)
    assert mirror.verdict == "refuted" and mirror.witness["n"] == 6


def test_example_8_sum_inequality_chain_and_the_sound_direction():  # v4F1
    r = check("sum_(i=1..n) i <= n^2")
    assert (r.verdict, r.tier) == ("proved", "solver_verified")
    assert "closed form kernel_verified; inequality step z3" in r.notes
    assert "n**2/2 + n/2" in r.notes                              # the chain is spelled out
    hint = check("sum_(i=1..n) i <= n^2/2 + 100")                 # z3 points at n=201; exact math convicts
    assert (hint.verdict, hint.tier) == ("refuted", "exact_integer_certificate")
    assert hint.witness == {"n": 201, "lhs_sum": "20301", "rhs": "40601/2",
                            "exact": "direct exact summation"}
    o = check("sum_(i=1..n) (2*i-1) <= n^2 + (n-1)*(n-2)/2")      # non-integer hint upgrades nothing
    assert (o.verdict, o.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT an integer witness" in o.notes
    assert "no counterexample among n <= 40" in o.checked_up_to


def test_example_9_permutation_bounds(capsys):                    # v4F2
    r = check("all perms of n: inversions <= n*(n-1)/2")          # a true theorem — still OPEN
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert r.checked_up_to == "ALL 5913 permutations over every n <= 7"
    assert "a finite scan never proves the universal claim" in r.notes
    assert main(["check", "all perms of n: descents <= fixed_points"]) == 0
    out = capsys.readouterr().out
    assert "refuted   [exact_integer_certificate]" in out
    assert "{'n': 2, 'perm': [1, 0], 'descents': 1, 'fixed_points': 0}" in out
    perm = check("all perms of n: descents <= fixed_points").witness["perm"]
    assert sum(1 for i in range(len(perm) - 1) if perm[i] > perm[i + 1]) == 1     # independent
    assert sum(1 for i, v in enumerate(perm) if i == v) == 0


def test_example_10_partition_identity(capsys):                   # v4F2
    r = check("partitions(n, odd) == partitions(n, distinct)")    # Euler's theorem — still OPEN
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "constructive bijection (Glaisher) verified for every n <= 20" in r.notes
    assert "universal step not machine-checked here" in r.notes
    assert main(["check", "partitions(n, all) == partitions(n, distinct)"]) == 0
    out = capsys.readouterr().out
    assert "refuted   [exact_integer_certificate]" in out
    assert "{'n': 2, 'count_all': 2, 'count_distinct': 1}" in out


def test_example_11_composition_identity(capsys):                 # v4F2
    r = check("compositions(n) == 2^(n-1)")
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "constructive bijection (cut-point) verified for every n <= 12" in r.notes
    bad = check("compositions(n) == n^2")
    assert (bad.verdict, bad.tier) == ("refuted", "exact_integer_certificate")
    assert bad.witness == {"n": 2, "compositions_count": 2, "rhs": "4"}
    assert check("set_partitions(n) == bell(n)").verdict == "unsupported"   # docs say NOT covered


def test_quickstart_three_readings_runs_exactly_as_documented(capsys):   # readings feature
    # block 1 — the connectivity assumption is load-bearing: A open / B refuted / C refuted
    assert main(["check", "num_vertices <= num_edges + 1", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    assert "VERDICT: open   [no_counterexample_within_bound]" in out
    assert "quantifier ambiguity: the verdict CHANGES with the reading "\
           "(A: open, B: refuted, C: refuted)" in out
    assert "  readings  : the same text under 3 candidate quantifier readings —" in out
    assert "[A] open       [no_counterexample_within_bound]  "\
           "check()'s own reading (baseline)" in out
    assert "[B] refuted    [exact_integer_certificate]  vs A: drops [connected]" in out
    assert "[C] refuted    [exact_integer_certificate]  vs A: drops [connected, "\
           "2 <= n <= 6 (bounded scan)]; adds [n == 6 (complete finite domain)]" in out
    # block 2 — the fixed-order reading is a genuine decision: A open / B open / C PROVED
    assert main(["check", "sum_degrees == 2*num_edges", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    assert "[B] open       [no_counterexample_within_bound]  vs A: drops [connected]" in out
    assert "[C] proved     [finite_domain_exhaustion]" in out
    assert "(A: open, B: open, C: proved)" in out


def test_example_7_readings_blocks_run_exactly_as_documented(capsys):    # readings feature
    assert main(["check", "num_vertices == num_edges"]) == 0             # default max_n=7
    out = capsys.readouterr().out
    assert "quantifier ambiguity: 3 readings evaluated — all agree (refuted); see readings" in out
    assert "[C] refuted    [exact_integer_certificate]  vs A: drops [connected, "\
           "2 <= n <= 7 (bounded scan)]; adds [n == 7 (complete finite domain)]" in out


def test_example_3_bracket_r33(capsys):
    assert main(["bracket", "3", "3", "--lo", "5", "--hi", "6"]) == 0
    assert "R(3,3) = 6" in capsys.readouterr().out


def test_honesty_page_lists_every_tier_the_engine_emits():
    text = (_MANUAL / "honesty.md").read_text()
    for tier in ("kernel_verified", "formal_proof", "exact_integer_certificate",
                 "finite_domain_exhaustion",
                 "independently_verified_witness",
                 "independently_verified_unsat_proof",
                 "independently_verified_unsat_proof_of_strengthened_formula",
                 "solver_verified_unsat_by_symmetry_case_split_with_rup_checked_cases",
                 "solver_verified_unsat_by_symmetry_case_split",
                 "solver_verified_with_derived_lemmas", "no_counterexample_within_bound",
                 "numerical_conjecture", "empirical"):
        assert tier in text
    assert "0 novel-to-literature" in text                     # the scorecard truth, stated in docs
    assert "ambiguity is surfaced, not resolved silently" in text     # the readings rule
    assert "no new tiers were invented" in text
