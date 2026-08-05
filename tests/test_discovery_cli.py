"""v3P1 — the mathhead-discover CLI (product surface, CI-locked)."""
import json

from mathhead.discovery.cli import main


def test_check_command(capsys):
    assert main(["check", "6 | n^3 - n"]) == 0
    out = capsys.readouterr().out
    assert "proved" in out and "kernel_verified" in out and "kernel hash" in out


def test_check_refutation_with_witness(capsys):
    assert main(["check", "num_triangles <= num_edges", "--max-n", "6"]) == 0
    out = capsys.readouterr().out
    assert "refuted" in out and "exact_integer_certificate" in out and "'n': 6" in out


def test_bracket_command(capsys):
    assert main(["bracket", "3", "3", "--lo", "5", "--hi", "6"]) == 0
    out = capsys.readouterr().out
    assert "R(3,3) = 6" in out and "independently_verified_witness" in out


def test_hunt_command_reports_honestly(capsys):
    assert main(["hunt", "frankl", "--universe", "6", "--steps", "300"]) == 0
    out = capsys.readouterr().out
    assert "STATUS:" in out and ("not_found_within_budget" in out or "certified" in out)


def test_json_output_is_machine_readable(capsys):
    assert main(["--json", "check", "5 | n^3 - n"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "refuted" and data["witness"]["n"] == 2


def test_check_congruence_command(capsys):                        # v4F1
    assert main(["check", "n^2 = n mod 2"]) == 0
    out = capsys.readouterr().out
    assert "proved   [kernel_verified]" in out and "kernel hash" in out


def test_check_graph_equality_command_is_honestly_open(capsys):   # v4F1
    assert main(["check", "sum_degrees == 2*num_edges", "--max-n", "5"]) == 0
    out = capsys.readouterr().out
    assert "open   [no_counterexample_within_bound]" in out
    assert "universal claim not proved" in out


def test_check_sum_inequality_command_json(capsys):               # v4F1
    assert main(["--json", "check", "sum_(i=1..n) i <= n^2"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "proved" and data["tier"] == "solver_verified"
    assert "closed form kernel_verified; inequality step z3" in data["notes"]
