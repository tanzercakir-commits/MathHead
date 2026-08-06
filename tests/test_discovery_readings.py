"""v1 readings feature — check() carries formalize's 3 quantifier readings on graph bounds.

The product answer to an ambiguous graph-bound text is no longer ONE silently-picked reading:
the envelope now carries all three candidates (A connected / B all graphs / C fixed order
n = max_n), each with its own honest verdict and tier. Backward compatible by construction —
the main verdict/tier/witness ARE reading A; `readings` is additional information.
"""
import json

from mathhead.discovery.cli import main
from mathhead.discovery.product import check

_KEYS = {"label", "statement_formal", "assumption_delta", "verdict", "tier", "witness_summary"}


# ------------------------------------------------------------------ the three verdicts, pinned --


def test_verdict_splitting_example_connectivity_is_load_bearing():
    """A open / B refuted / C refuted — the SAME text, three honest answers."""
    r = check("num_vertices <= num_edges + 1", max_n=6)
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")   # reading A = main
    assert [e["label"] for e in r.readings] == ["A", "B", "C"]
    a, b, c = r.readings
    assert (a["verdict"], a["tier"]) == ("open", "no_counterexample_within_bound")
    assert (b["verdict"], b["tier"]) == ("refuted", "exact_integer_certificate")
    assert (c["verdict"], c["tier"]) == ("refuted", "exact_integer_certificate")
    # the B witness is real: two isolated vertices — 2 <= 0 + 1 is false, recomputed here
    assert "num_vertices=2" in b["witness_summary"] and "num_edges=0" in b["witness_summary"]
    assert not (2 <= 0 + 1)
    # the assumption delta is machine-derived from formalize's differences(), not prose
    assert b["assumption_delta"] == "vs A: drops [connected]"
    assert "adds [n == 6 (complete finite domain)]" in c["assumption_delta"]
    assert "verdict CHANGES with the reading" in r.notes and "A: open, B: refuted" in r.notes


def test_handshake_fixed_order_reading_is_genuinely_decided():
    """A open / B open / C PROVED — the theorem a finite scan can never prove under the
    unbounded readings becomes decided under the complete finite domain of reading C."""
    r = check("sum_degrees == 2*num_edges", max_n=6)
    assert (r.verdict, r.tier) == ("open", "no_counterexample_within_bound")   # main unchanged
    a, b, c = r.readings
    assert (a["verdict"], b["verdict"]) == ("open", "open")
    assert (c["verdict"], c["tier"]) == ("proved", "finite_domain_exhaustion")
    assert "ALL 156 isomorphism classes of order n=6" in c["witness_summary"]
    # independent recomputation with the PURE-PYTHON generator (no geng in the loop): the C
    # domain is complete (OEIS A000088: 156 classes at n=6) and the equality holds on all of it
    from mathhead.discovery.generate import generate_graphs
    from mathhead.discovery.invariants import evaluate
    order6 = generate_graphs(6)
    assert len(order6) == 156
    assert all(evaluate(g, "sum_degrees") == 2 * evaluate(g, "num_edges") for g in order6)
    assert "A: open, B: open, C: proved" in r.notes


def test_all_readings_agreeing_get_the_short_note():
    r = check("num_triangles <= num_edges", max_n=6)
    assert [e["verdict"] for e in r.readings] == ["refuted", "refuted", "refuted"]
    assert "3 readings evaluated — all agree (refuted)" in r.notes
    assert "verdict CHANGES" not in r.notes


# ---------------------------------------------------------------- backward-compat: A = envelope --


def test_main_envelope_is_reading_a_and_is_unchanged():
    """The pre-readings pins, re-asserted verbatim: verdict, tier, witness, checked_up_to and
    the old notes sentences all survive — readings is ADDITIONAL, never a replacement."""
    r = check("num_triangles <= num_edges", max_n=6)
    assert (r.structure, r.verdict, r.tier) == \
        ("graph_inequality", "refuted", "exact_integer_certificate")
    assert r.witness["n"] == 6 and r.witness["num_triangles"] == 16 and r.witness["num_edges"] == 14
    assert r.checked_up_to == "first counterexample among connected graphs, n=6"
    assert r.notes.startswith("smallest-order witness; values computed exactly")
    assert (r.readings[0]["verdict"], r.readings[0]["tier"]) == (r.verdict, r.tier)
    assert r.readings[0]["assumption_delta"] == "check()'s own reading (baseline)"

    o = check("clique_number <= chromatic_number", max_n=5)
    assert (o.verdict, o.tier) == ("open", "no_counterexample_within_bound")
    assert "NOT proved" in o.notes and "ALL" in o.checked_up_to

    e = check("sum_degrees == 2*num_edges", max_n=5)
    assert "universal claim not proved; holds for all connected graphs up to n=5" in e.notes


def test_readings_only_on_graph_bounds_every_other_structure_stays_empty():
    for s in ("6 | n^3 - n",                                    # modular, proved
              "5 | n^3 - n",                                    # modular, refuted
              "n^2 ≡ n (mod 2)",                                # congruence
              "sum_(i=1..n) i = n*(n+1)/2",                     # sum identity
              "sum_(i=1..n) i <= n^2",                          # sum inequality
              "all perms of n: descents <= fixed_points",       # permutation
              "partitions(n, odd) == partitions(n, distinct)",  # partitions
              "compositions(n) == 2^(n-1)",                     # compositions
              "the weather tomorrow"):                          # unsupported
        r = check(s)
        assert r.readings == (), s
        assert "quantifier ambiguity" not in r.notes, s


def test_outside_the_formalization_wall_readings_absent_and_the_note_says_why():
    r = check("num_vertices <= num_edges + 1", max_n=1)
    assert r.readings == ()
    assert "quantifier readings not evaluated: max_n=1" in r.notes
    assert "2 <= max_n <= 7" in r.notes


def test_readings_shape_tiers_and_determinism():
    a = check("num_vertices <= num_edges + 1", max_n=5)
    b = check("num_vertices <= num_edges + 1", max_n=5)
    assert a.readings == b.readings and len(a.readings) == 3          # deterministic
    honest = {"kernel_verified", "exact_integer_certificate", "finite_domain_exhaustion",
              "no_counterexample_within_bound"}
    for e in a.readings:
        assert set(e) == _KEYS
        assert e["tier"] in honest                                    # formalize's tiers, no invention
        assert e["statement_formal"].endswith("num_vertices <= num_edges + 1")
    # C's fixed order is check()'s max_n — consistent with formalize's fixed_n semantics
    assert "n = 5 (complete finite domain)" in a.readings[2]["statement_formal"]


def test_disconnected_sentinel_refutations_are_marked_definitional():
    """diameter/radius = -1 on disconnected graphs is a DOCUMENTED sentinel (rich_invariants) —
    a B/C refutation riding it is an artifact of the convention, and the reading says so."""
    r = check("diameter <= 2*radius", max_n=6)
    a, b, c = r.readings
    assert (a["verdict"], b["verdict"], c["verdict"]) == ("open", "refuted", "refuted")
    assert "diameter=-1" in b["witness_summary"] and "radius=-1" in b["witness_summary"]
    for e in (b, c):
        assert ("disconnected sentinel: the refutation is definitional "
                "(invariant = -1 on a disconnected graph), not graph-theoretic"
                ) in e["witness_summary"]
    # a normal, genuinely graph-theoretic witness carries NO sentinel marker
    n = check("num_vertices <= num_edges + 1", max_n=6)
    assert all("sentinel" not in e["witness_summary"] for e in n.readings)


def test_readings_verdicts_match_formalize_own_verdicts():
    """The envelope's readings must agree, verdict by verdict and tier by tier, with what the
    formalize surface itself says for the same bounds — one source of truth, surfaced twice."""
    from mathhead.discovery.formalize import formalize
    r = check("num_vertices <= num_edges + 1", max_n=5)
    f = formalize("num_vertices <= num_edges + 1", max_n=5, fixed_n=5)
    for e in r.readings:
        v = f["verdicts"][e["label"]]
        assert (e["verdict"], e["tier"]) == (v.verdict, v.tier)


# ----------------------------------------------------------------------------------- CLI surface --


def test_cli_prints_compact_readings_after_the_unchanged_envelope(capsys):
    assert main(["check", "num_vertices <= num_edges + 1", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0] == "VERDICT: open   [no_counterexample_within_bound]"     # envelope unchanged
    assert "  readings  : the same text under 3 candidate quantifier readings —" in lines
    assert any(ln.startswith("    [A] open") and "no_counterexample_within_bound" in ln
               for ln in lines)
    assert any(ln.startswith("    [B] refuted") and "drops [connected]" in ln for ln in lines)
    assert any(ln.startswith("    [C] refuted") and "complete finite domain" in ln for ln in lines)


def test_cli_json_carries_readings_and_the_exit_code_contract_is_untouched(capsys):
    assert main(["--json", "check", "sum_degrees == 2*num_edges", "--max-n", "6"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "open" and len(data["readings"]) == 3
    assert [e["verdict"] for e in data["readings"]] == ["open", "open", "proved"]
    assert set(data["readings"][2]) == _KEYS
    # honest refusals still exit 3, with readings present-and-empty in the JSON envelope
    assert main(["--json", "check", "the weather tomorrow"]) == 3
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "unsupported" and data["readings"] == []


def test_cli_non_graph_output_has_no_readings_block(capsys):
    assert main(["check", "6 | n^3 - n"]) == 0
    assert "readings" not in capsys.readouterr().out
