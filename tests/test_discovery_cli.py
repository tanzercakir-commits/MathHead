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
