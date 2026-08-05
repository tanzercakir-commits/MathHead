"""v3P4 — the docs gallery is EXECUTABLE: every claim in the manual runs in CI (docs cannot rot)."""
from pathlib import Path

from mathhead.discovery import check
from mathhead.discovery.cli import main

_MANUAL = Path(__file__).parent.parent / "docs" / "manual"


def test_manual_pages_exist():
    for page in ("index.md", "quickstart.md", "honesty.md", "examples.md", "api.md"):
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


def test_example_3_bracket_r33(capsys):
    assert main(["bracket", "3", "3", "--lo", "5", "--hi", "6"]) == 0
    assert "R(3,3) = 6" in capsys.readouterr().out


def test_honesty_page_lists_every_tier_the_engine_emits():
    text = (_MANUAL / "honesty.md").read_text()
    for tier in ("kernel_verified", "exact_integer_certificate", "independently_verified_witness",
                 "solver_verified_with_derived_lemmas", "no_counterexample_within_bound",
                 "numerical_conjecture", "empirical"):
        assert tier in text
    assert "0 novel-to-literature" in text                     # the scorecard truth, stated in docs
