"""v4F2 — check() coverage wave 2: NEW DOMAINS through the single door — permutation invariant
bounds over ALL of S_n, partition counting identities, and the composition count identity. Tier
inflation stays the highest-priority bug class: a finite S_n scan / a per-n bijection check is
NEVER 'proved' (the ceilings are pinned below), and every witness is INDEPENDENTLY recomputed
here with no engine code in the loop."""
from mathhead.discovery.product import check

# ---- independent re-implementations (deliberately engine-free) --------------------------------


def _inv(perm):
    return sum(1 for i in range(len(perm)) for j in range(i + 1, len(perm)) if perm[i] > perm[j])


def _desc(perm):
    return sum(1 for i in range(len(perm) - 1) if perm[i] > perm[i + 1])


def _maj(perm):
    return sum(i + 1 for i in range(len(perm) - 1) if perm[i] > perm[i + 1])


def _fix(perm):
    return sum(1 for i, v in enumerate(perm) if i == v)


def _partitions(n, mx=None):
    if n == 0:
        yield ()
        return
    mx = n if mx is None else mx
    for first in range(min(n, mx), 0, -1):
        for rest in _partitions(n - first, first):
            yield (first, *rest)


def _count_compositions(n):
    return 1 if n == 0 else sum(_count_compositions(n - k) for k in range(1, n + 1))


# ------------------------------------------------------------------ permutation bounds ---------


def test_perm_true_bound_is_open_never_proved():
    r = check("all perms of n: inversions <= n*(n-1)/2")           # a THEOREM — the scan cannot know
    assert (r.structure, r.verdict, r.tier) == ("permutation_inequality", "open",
                                                "no_counterexample_within_bound")
    assert "a finite scan never proves the universal claim" in r.notes
    assert "ALL 5913 permutations over every n <= 7" in r.checked_up_to    # 1!+2!+...+7! = 5913


def test_perm_le_refuted_with_witness_independently_recomputed():
    r = check("all perms of n: descents <= fixed_points")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    perm = r.witness["perm"]
    assert r.witness["n"] == len(perm) == 2 and sorted(perm) == [0, 1]     # a real permutation
    assert _desc(perm) == r.witness["descents"] and _fix(perm) == r.witness["fixed_points"]
    assert _desc(perm) > _fix(perm)                                        # independent conviction


def test_perm_ge_refuted():
    r = check("all perms of n: fixed_points >= 1")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert _fix(r.witness["perm"]) == 0 < 1                                # independent conviction


def test_perm_equality_refuted_in_either_direction():
    r = check("all perms of n: major_index == inversions")
    assert (r.structure, r.verdict) == ("permutation_equality", "refuted")
    perm = r.witness["perm"]
    assert _maj(perm) != _inv(perm)                                        # independent conviction
    assert _maj(perm) == r.witness["major_index"] and _inv(perm) == r.witness["inversions"]
    assert "either direction convicts" in r.notes


def test_perm_equality_vs_expression_refuted_smallest_first():
    r = check("all perms of n: inversions == n*(n-1)/2")
    assert r.verdict == "refuted" and r.witness["n"] == 2
    assert r.witness["perm"] == [0, 1]                             # identity: 0 inversions != 1
    assert _inv(r.witness["perm"]) == 0 and r.witness["rhs"] == 1


def test_perm_survivor_ge_direction_open():
    r = check("all perms of n: cycles >= 1")
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT proved" in r.notes


def test_perm_max_n_shrinks_and_the_factorial_wall_is_honest():
    small = check("all perms of n: inversions <= n*(n-1)/2", max_n=4)
    assert "ALL 33 permutations over every n <= 4" in small.checked_up_to  # 1!+2!+3!+4! = 33
    big = check("all perms of n: inversions <= n*(n-1)/2", max_n=9)
    assert "n <= 7" in big.checked_up_to                                   # capped, and SAYS so
    assert "scan honestly capped at n=7" in big.checked_up_to


def test_perm_unknown_invariant_is_honestly_unsupported():
    r = check("all perms of n: entropy <= 3")
    assert (r.verdict, r.tier) == ("unsupported", "none")
    for name in ("inversions", "descents", "major_index", "fixed_points", "cycles"):
        assert name in r.notes                                             # the surface is NAMED
    assert "refuses to guess" in r.notes


def test_perm_irrational_rhs_is_honestly_unsupported():
    r = check("all perms of n: inversions <= sqrt(2)")
    assert r.verdict == "unsupported" and "exact rational" in r.notes


def test_perm_foreign_symbol_rhs_is_honestly_unsupported():
    r = check("all perms of n: inversions <= x^2")
    assert r.verdict == "unsupported" and "free symbols other than n" in r.notes


def test_perm_garbled_tail_is_honestly_unsupported():
    r = check("all perms of n dance")
    assert r.verdict == "unsupported" and "could not read" in r.notes


# ------------------------------------------------------------- partition counting identities ---


def test_partition_euler_identity_open_with_glaisher_note_and_exact_tier():
    r = check("partitions(n, odd) == partitions(n, distinct)")     # Euler's THEOREM — still open
    assert (r.structure, r.verdict) == ("partition_count_identity", "open")
    # the tier decision, pinned: per-n bijection verification is NOT independently_verified_witness
    # and NEVER proved — the universal step lives in the literature, not in this machine.
    assert r.tier == "no_counterexample_within_bound"
    assert ("constructive bijection (Glaisher) verified for every n <= 20 — classical theorem, "
            "universal step not machine-checked here") in r.notes
    assert "bijections.certify_euler_bijection" in r.instruments


def test_partition_euler_counts_independently_recomputed():
    # the engine says the counts agree for every n <= 20; recount n <= 10 with local code only
    for n in range(1, 11):
        parts = list(_partitions(n))
        odd = sum(1 for p in parts if all(x % 2 == 1 for x in p))
        distinct = sum(1 for p in parts if len(p) == len(set(p)))
        assert odd == distinct
    assert [sum(1 for p in _partitions(n) if len(p) == len(set(p))) for n in range(1, 9)] \
        == [1, 1, 2, 2, 3, 4, 5, 6]                                # OEIS A000009


def test_partition_identity_refuted_with_both_counts_in_hand():
    r = check("partitions(n, all) == partitions(n, distinct)")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness == {"n": 2, "count_all": 2, "count_distinct": 1}
    parts2 = list(_partitions(2))                                  # independent: (2), (1,1)
    assert len(parts2) == 2 and sum(1 for p in parts2 if len(p) == len(set(p))) == 1


def test_partition_bare_form_means_all():
    r = check("partitions(n) == partitions(n, odd)")
    assert r.verdict == "refuted" and r.witness == {"n": 2, "count_all": 2, "count_odd": 1}


def test_partition_unknown_filter_is_honestly_unsupported():
    r = check("partitions(n, even) == partitions(n, odd)")
    assert (r.verdict, r.tier) == ("unsupported", "none")
    assert "unknown partition filter 'even'" in r.notes
    assert "'parts <= k' filters and closed-form right sides are NOT supported" in r.notes


def test_partition_closed_form_rhs_is_honestly_unsupported():
    r = check("partitions(n, odd) == 2^(n-1)")
    assert r.verdict == "unsupported" and "refuses to guess" in r.notes


# ------------------------------------------------------------------ composition identity -------


def test_composition_identity_open_with_cutpoint_note_and_exact_tier():
    r = check("compositions(n) == 2^(n-1)")
    assert (r.structure, r.verdict) == ("composition_count_identity", "open")
    assert r.tier == "no_counterexample_within_bound"              # per-n bijection ≠ proved
    assert ("constructive bijection (cut-point) verified for every n <= 12 — classical theorem, "
            "universal step not machine-checked here") in r.notes


def test_composition_counts_independently_recomputed():
    for n in range(1, 11):
        assert _count_compositions(n) == 2 ** (n - 1)              # engine-free recount


def test_composition_identity_refuted_with_count_in_hand():
    r = check("compositions(n) == n^2")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    assert r.witness == {"n": 2, "compositions_count": 2, "rhs": "4"}
    assert _count_compositions(2) == 2 != 4                        # independent conviction


def test_composition_equivalent_spelling_of_the_formula_still_gets_the_bijection():
    r = check("compositions(n) == 2^n / 2")                        # symbolically the same formula
    assert r.verdict == "open" and "constructive bijection (cut-point)" in r.notes


def test_composition_foreign_symbol_is_honestly_unsupported():
    r = check("compositions(n) == weather")
    assert (r.verdict, r.tier) == ("unsupported", "none") and "free symbols" in r.notes


def test_composition_filtered_grammar_is_honestly_unsupported():
    r = check("compositions(n, odd) == 2^(n-1)")
    assert r.verdict == "unsupported" and "compositions(n) == g(n)" in r.notes


# ------------------------------------------- the route-wide oversized-constant guard (v4F2) ----


def test_giant_evaluated_constants_are_refused_route_wide_never_crashed():
    # CPython's int↔str conversion raises past ~4300 digits; before this guard, 2^15000 CRASHED
    # the modular, congruence, sum and composition routes with an uncaught ValueError.
    for s in ("compositions(n) == 2^15000",
              "sum_(i=1..n) i <= 2^15000",
              "sum_(i=1..n) i = 2^15000",
              "3 | n + 2^15000",
              "n ≡ 2^15000 (mod 3)",
              "all perms of n: inversions <= 2^15000"):
        r = check(s)
        assert (r.verdict, r.tier) == ("unsupported", "none"), s
        assert "4000 digits" in r.notes and "refused up front" in r.notes


def test_giant_literal_digit_runs_are_refused_at_the_door():
    big = "9" * 5000                                       # int("9"*5000) itself raises ValueError
    for s in (f"{big} | n", f"n ≡ 0 (mod {big})", f"compositions(n) == {big}",
              f"num_triangles <= {big}*num_edges"):
        r = check(s)
        assert (r.verdict, r.tier) == ("unsupported", "none"), s[:40]
        assert "4000 digits" in r.notes


def test_giant_values_created_only_at_evaluation_are_refused_too():
    # small atoms, monstrous values: factorial(10000*n) at n=1 has ~35660 digits
    r = check("compositions(n) == factorial(10000*n)")
    assert r.verdict == "unsupported" and "4000 digits" in r.notes and "n=1" in r.notes
    r = check("all perms of n: inversions <= factorial(10000*n)")
    assert r.verdict == "unsupported" and "4000 digits" in r.notes
    r = check("sum_(i=1..n) factorial(3000*i) >= 1")
    assert r.verdict == "unsupported" and "evaluated value" in r.notes


def test_reasonable_constants_still_flow_through_every_route():   # the guard must not overreach
    assert check("compositions(n) == 2^(n-1)").verdict == "open"
    assert check("3 | n^3 + 2^100 - 1").verdict in ("proved", "refuted")
    assert check("sum_(i=1..n) i <= n^2 + 10^100").verdict in ("proved", "open")


# ------------------------------------------------- closing-round consistency fixes (v4F2) ------


def test_perm_num_cycles_alias_is_accepted_and_documented():
    a, b = check("all perms of n: num_cycles >= 1"), check("all perms of n: cycles >= 1")
    assert (a.verdict, a.tier) == (b.verdict, b.tier) == ("open", "no_counterexample_within_bound")
    assert a.checked_up_to == b.checked_up_to
    refusal = check("all perms of n: entropy <= 3")               # the refusal NAMES the alias
    assert "num_cycles" in refusal.notes


def test_composition_irrational_rhs_is_honestly_unsupported():
    # pi is exactly decidable but NOT integer arithmetic — the tier name promises an integer
    # certificate, so the engine refuses instead of "refuting" with pi in the witness.
    r = check("compositions(n) == pi")
    assert (r.verdict, r.tier) == ("unsupported", "none")
    assert "exact rational" in r.notes


def test_perm_max_n_below_one_is_clamped_and_says_so():
    r = check("all perms of n: cycles >= 1", max_n=0)
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")
    assert "ALL 1 permutations over every n <= 1" in r.checked_up_to
    assert "max_n=0 < 1 clamped to n=1" in r.checked_up_to


# ------------------------------------------------------------------------- the single door ----


def test_unsupported_message_knows_the_wave2_surface():
    r = check("the weather tomorrow")
    assert r.verdict == "unsupported"
    for phrase in ("all perms of n:", "partitions(n, odd|distinct|all)",
                   "compositions(n) == g(n)", "set-partition/Bell counts are NOT yet supported",
                   "refuses to guess"):
        assert phrase in r.notes


def test_wave2_forms_are_deterministic():
    for s in ("all perms of n: descents <= fixed_points",
              "partitions(n, odd) == partitions(n, distinct)",
              "compositions(n) == n^2"):
        a, b = check(s), check(s)
        assert (a.verdict, a.tier, a.witness, a.notes) == (b.verdict, b.tier, b.witness, b.notes)


def test_wave1_and_v3_behaviour_unchanged():                       # backward-compat pin
    assert check("6 | n^3 - n").verdict == "proved"
    assert check("n^2 ≡ n (mod 3)").verdict == "refuted"
    g = check("num_triangles <= num_edges", max_n=6)
    assert g.verdict == "refuted" and g.witness["n"] == 6
    assert check("sum_(i=1..n) i = n*(n+1)/2").verdict == "proved"


def test_cli_reaches_all_three_new_domains(capsys):
    from mathhead.discovery.cli import main
    assert main(["check", "all perms of n: descents <= fixed_points"]) == 0
    out = capsys.readouterr().out
    assert "refuted   [exact_integer_certificate]" in out and "'perm': [1, 0]" in out
    assert main(["check", "partitions(n, odd) == partitions(n, distinct)"]) == 0
    out = capsys.readouterr().out
    assert "open   [no_counterexample_within_bound]" in out and "Glaisher" in out
    assert main(["check", "compositions(n) == 2^(n-1)"]) == 0
    out = capsys.readouterr().out
    assert "open   [no_counterexample_within_bound]" in out and "cut-point" in out
