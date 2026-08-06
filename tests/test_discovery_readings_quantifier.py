"""Readings wave 2 — the ∀/∃ quantifier ambiguity of modular/congruence statements, surfaced.

A mathematician who writes "5 | n^3 - n" may mean EVERY n (false — n=2 convicts) or SOME n
(true — exactly the classes n ≡ 0, ±1 (mod 5)). The engine no longer picks silently: the
envelope now carries both readings, each with its own honest verdict, in the SAME schema the
wave-1 graph readings established. Backward compatible by construction — the main envelope IS
the ∀ reading (reused, never recomputed); the ∃ reading is DECIDED from the same finite residue
table the route already stands on, so it has no 'open' path. No new tiers: an ∃-proof is a
self-verifying witness (exact_integer_certificate), an ∃-refutation is the full m-entry table
(finite decision, exact integer arithmetic — the same tier the ∀-refutation already carries).
"""
import json

from mathhead.discovery.cli import main
from mathhead.discovery.nt_chain import walk_divisibility_chain
from mathhead.discovery.product import check

_KEYS = {"label", "statement_formal", "assumption_delta", "verdict", "tier", "witness_summary"}


# ------------------------------------------------------------- the flagship split: ∀ vs ∃ ------


def test_flagship_split_forall_refuted_exists_proved():
    """'5 | n^3 - n' — the SAME text, two honest answers: ∀ refuted (n=2), ∃ proved (n≡0,±1)."""
    r = check("5 | n^3 - n")
    # the main envelope is byte-identical to the pre-readings behaviour (backward-compat pin)
    assert (r.structure, r.verdict, r.tier) == \
        ("modular_divisibility", "refuted", "exact_integer_certificate")
    assert r.witness == {"n": 2, "value_mod_m": 1}
    assert r.checked_up_to == "decided exactly (finite residue table)"
    assert r.notes.startswith("residue n≡2 (mod 5) gives a nonzero value — the claim is false")
    # the two readings, ∀ first — ∀ IS the main envelope
    assert [e["label"] for e in r.readings] == ["∀", "∃"]
    fa, ex = r.readings
    assert (fa["verdict"], fa["tier"]) == (r.verdict, r.tier)
    assert fa["assumption_delta"] == "check()'s own reading (baseline)"
    assert fa["witness_summary"] == "counterexample: n=2, value_mod_m=1"
    assert (ex["verdict"], ex["tier"]) == ("proved", "exact_integer_certificate")
    assert "witness n=0" in ex["witness_summary"]
    assert "n ≡ 0, ±1 (mod 5)" in ex["witness_summary"]
    assert "3 of 5 residue classes" in ex["witness_summary"]
    # independent conviction, no engine in the loop: the class list is EXACTLY the solution set
    assert [r_ for r_ in range(5) if (r_**3 - r_) % 5 == 0] == [0, 1, 4]     # 4 ≡ −1 (mod 5)
    assert (2**3 - 2) % 5 == 1 != 0                                          # and ∀ really fails
    assert ("quantifier ambiguity: the verdict CHANGES with the reading "
            "(∀: refuted, ∃: proved)") in r.notes and "see readings" in r.notes


def test_agreement_both_proved_kernel_forall_witnessed_exists():
    r = check("6 | n^3 - n")
    assert (r.verdict, r.tier) == ("proved", "kernel_verified") and r.proof_hash
    fa, ex = r.readings
    assert (fa["verdict"], fa["tier"]) == ("proved", "kernel_verified")
    assert fa["witness_summary"] == "all integers n (universal proof)"
    # ∃ follows from ∀ but is NOT tier-inflated to kernel_verified: its certificate is the
    # witness n=0, re-verified by direct evaluation — exact_integer_certificate, honestly
    assert (ex["verdict"], ex["tier"]) == ("proved", "exact_integer_certificate")
    assert "witness n=0" in ex["witness_summary"]
    assert "every residue class — all 6 of 6 vanish" in ex["witness_summary"]
    assert "quantifier ambiguity: 2 readings evaluated — both agree (proved)" in r.notes
    assert "verdict CHANGES" not in r.notes


def test_agreement_both_refuted_no_residue_class_ever_works():
    """'2 | 2n + 1' — an odd number is never even: ∀ refuted AND ∃ refuted (no residue works)."""
    r = check("2 | 2*n + 1")
    assert (r.verdict, r.tier) == ("refuted", "exact_integer_certificate")
    fa, ex = r.readings
    assert (fa["verdict"], ex["verdict"]) == ("refuted", "refuted")
    assert ex["tier"] == "exact_integer_certificate"
    assert "all 2 residue classes scanned" in ex["witness_summary"]
    assert "finite decision" in ex["witness_summary"]
    assert all((2 * k + 1) % 2 != 0 for k in range(2))          # independent: both residues fail
    assert "2 readings evaluated — both agree (refuted)" in r.notes


# ------------------------------------------------------ congruences inherit the same readings --


def test_congruence_split_inherits_through_the_p_minus_q_reduction():
    """'n^2 ≡ n (mod 3)' — ∀ refuted (n=2: 1 ≢ 2), ∃ proved (n ≡ 0, 1 work)."""
    r = check("n^2 ≡ n (mod 3)")
    assert (r.structure, r.verdict) == ("polynomial_congruence", "refuted")
    assert r.witness == {"n": 2, "lhs_mod_m": 1, "rhs_mod_m": 2, "difference_mod_m": 2}   # pin
    fa, ex = r.readings
    assert fa["witness_summary"] == "counterexample: n=2, lhs_mod_m=1, rhs_mod_m=2, " \
                                    "difference_mod_m=2"
    assert (ex["verdict"], ex["tier"]) == ("proved", "exact_integer_certificate")
    assert "the two sides agree (mod 3)" in ex["witness_summary"]
    assert "n ≡ 0, 1 (mod 3)" in ex["witness_summary"] and "2 of 3" in ex["witness_summary"]
    assert [k for k in range(3) if (k * k - k) % 3 == 0] == [0, 1]           # independent
    assert "(∀: refuted, ∃: proved)" in r.notes


def test_congruence_exists_refuted_no_residue_ever_agrees():
    """'n^2 ≡ 2 (mod 3)' — 2 is not a quadratic residue mod 3: both readings refuted."""
    r = check("n^2 ≡ 2 (mod 3)")
    fa, ex = r.readings
    assert (fa["verdict"], ex["verdict"]) == ("refuted", "refuted")
    assert "the two sides never agree (mod 3)" in ex["witness_summary"]
    assert all(k * k % 3 != 2 for k in range(3))                             # independent
    assert "both agree (refuted)" in r.notes


def test_congruence_both_proved_and_the_reduction_hash_pin_survives():
    r = check("n^2 + n ≡ 0 (mod 2)")
    assert (r.verdict, r.tier) == ("proved", "kernel_verified")
    assert [e["verdict"] for e in r.readings] == ["proved", "proved"]
    assert "the two sides agree (mod 2)" in r.readings[1]["witness_summary"]
    # the v4F1 reduction pin is untouched: same kernel term, same hash as the modular twin
    assert check("n^3 ≡ n (mod 6)").proof_hash == check("6 | n^3 - n").proof_hash


# --------------------------------------------------------- the residue-class list, ± notation --


def test_residue_class_list_self_negative_class_stands_alone():
    ex = check("8 | n^2").readings[1]                       # n² ≡ 0 (mod 8) ⇔ n ≡ 0 or 4 (mod 8)
    assert "n ≡ 0, 4 (mod 8)" in ex["witness_summary"]      # 4 = 8/2 is its own negative: no ±
    assert "2 of 8 residue classes" in ex["witness_summary"]
    assert [r_ for r_ in range(8) if r_ * r_ % 8 == 0] == [0, 4]             # independent


def test_residue_class_list_truncates_with_the_exact_count_stated():
    ex = check("625 | 25*n").readings[1]                    # solutions: n ≡ 0 (mod 25) — 25 classes
    assert ex["verdict"] == "proved"
    assert "n ≡ 0, ±25, ±50" in ex["witness_summary"]       # the list starts exactly
    assert ", … (mod 625)" in ex["witness_summary"]         # 13 ±-terms > 12 → honest ellipsis
    assert "25 of 625 residue classes" in ex["witness_summary"]              # the count is exact
    assert sum(1 for r_ in range(625) if 25 * r_ % 625 == 0) == 25           # independent


# ------------------------------------------------- the ∃ reading agrees with the U1 nt_chain ---


def test_readings_agree_with_the_nt_chain_exists_walk():
    """One source of truth: the ∃ verdict must equal walk_divisibility_chain(..., 'exists')."""
    for stmt, m, poly in (("5 | n^3 - n", 5, (0, -1, 0, 1)),
                          ("6 | n^3 - n", 6, (0, -1, 0, 1)),
                          ("2 | 2*n + 1", 2, (1, 2)),
                          ("4 | n^2 + 1", 4, (1, 0, 1))):
        ex = check(stmt).readings[1]
        walk = walk_divisibility_chain(m, poly, "exists")
        assert ex["verdict"] == ("proved" if walk.holds else "refuted"), stmt


# ---------------------------------------------------------------- honesty + backward compat ----


def test_wall_and_refusals_carry_no_readings():
    # the 10^6 modulus wall guards the ∃ scan too: above it the WHOLE envelope is an honest
    # refusal, readings stay empty and the note says why
    for s in ("1000001 | n", "n ≡ 0 (mod 1000001)"):
        r = check(s)
        assert (r.verdict, r.readings) == ("unsupported", ()) and "bound = 10^6" in r.notes, s
    # every other modular/congruence refusal path stays readings-free as well
    for s in ("0 | n", "2 | n/2", "x^2 ≡ x (mod 2)", "6 | x^3 - x"):
        r = check(s)
        assert (r.verdict, r.readings) == ("unsupported", ()), s
        assert "quantifier ambiguity" not in r.notes, s


def test_constant_polynomial_statements_are_exempt_no_fake_ambiguity():
    """deg(p) = 0 after the reduction: there is no free n for a quantifier to bind, so the two
    readings coincide trivially — the engine attaches NO readings and the note says why."""
    for s, verdict in (("5 | 10", "proved"),                # constant, divisible
                       ("5 | 7", "refuted"),                # constant, not divisible
                       ("n + 1 ≡ n (mod 2)", "refuted")):   # n cancels in p − q: constant 1
        r = check(s)
        assert (r.verdict, r.readings) == (verdict, ()), s
        assert "constant polynomial" in r.notes, s
        assert "coincide trivially" in r.notes, s
        assert "quantifier ambiguity" not in r.notes, s


def test_readings_schema_tiers_and_determinism():
    a, b = check("5 | n^3 - n"), check("5 | n^3 - n")
    assert a == b and a.readings == b.readings and len(a.readings) == 2      # deterministic
    honest = {"kernel_verified", "exact_integer_certificate"}
    for e in a.readings:
        assert set(e) == _KEYS                              # the wave-1 schema, field for field
        assert e["tier"] in honest                          # existing tiers only — none invented
        assert e["statement_formal"].endswith("5 | n^3 - n")
    assert a.readings[0]["statement_formal"].startswith("for all integers n: ")
    assert a.readings[1]["statement_formal"].startswith("there exists an integer n: ")
    assert a.readings[1]["assumption_delta"] == \
        "vs ∀: 'for every integer n' weakened to 'for at least one integer n'"


def test_wave1_graph_readings_are_untouched_by_wave2():
    """The graph surface still carries exactly formalize's THREE readings, A/B/C, verbatim."""
    r = check("num_vertices <= num_edges + 1", max_n=6)
    assert [e["label"] for e in r.readings] == ["A", "B", "C"]
    assert [e["verdict"] for e in r.readings] == ["open", "refuted", "refuted"]
    assert "quantifier ambiguity: the verdict CHANGES with the reading " \
           "(A: open, B: refuted, C: refuted)" in r.notes


# ----------------------------------------------------------------------------- CLI surface -----


def test_cli_prints_the_two_readings_after_the_unchanged_envelope(capsys):
    assert main(["check", "5 | n^3 - n"]) == 0              # an answered verdict still exits 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "VERDICT: refuted   [exact_integer_certificate]"      # envelope unchanged
    assert "  readings  : the same text under 2 candidate quantifier readings —" in lines
    assert any(ln.startswith("    [∀] refuted") and "exact_integer_certificate" in ln
               and "check()'s own reading (baseline)" in ln for ln in lines)
    assert any(ln.startswith("    [∃] proved") and "exact_integer_certificate" in ln
               and "weakened to 'for at least one integer n'" in ln for ln in lines)


def test_cli_graph_bounds_still_print_three_readings(capsys):
    # the header counts readings dynamically — the wave-1 output remains byte-compatible
    assert main(["check", "num_vertices <= num_edges + 1", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    assert "  readings  : the same text under 3 candidate quantifier readings —" in out


def test_cli_json_carries_both_readings_with_the_schema(capsys):
    assert main(["--json", "check", "5 | n^3 - n"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "refuted" and len(data["readings"]) == 2
    assert [e["label"] for e in data["readings"]] == ["∀", "∃"]
    assert [e["verdict"] for e in data["readings"]] == ["refuted", "proved"]
    assert all(set(e) == _KEYS for e in data["readings"])
    assert main(["--json", "check", "6 | n^3 - n"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "proved" and \
        [e["verdict"] for e in data["readings"]] == ["proved", "proved"]
