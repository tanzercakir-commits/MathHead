"""CLI davranış testleri — `cli.main` doğrudan çağrılır (çıktı + çıkış kodu)."""
import json

from mathhead import cli


def test_entail_valid(capsys):
    code = cli.main(["entail", "-p", "p", "-p", "implies(p, q)", "-c", "q"])
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_syllogism_via_cli(capsys):
    code = cli.main([
        "entail",
        "-p", "forall(x, implies(Man(x), Mortal(x)))",
        "-p", "Man(socrates)",
        "-c", "Mortal(socrates)",
    ])
    assert code == 0
    assert "valid" in capsys.readouterr().out


def test_solve_json_output(capsys):
    code = cli.main(["--json", "solve", "x**2 == 4", "x"])
    data = json.loads(capsys.readouterr().out)
    assert code == 0
    assert set(data["result"]) == {"-2", "2"}


def test_error_exit_code(capsys):
    code = cli.main(["consistent", "("])
    assert code == 1
    assert "error" in capsys.readouterr().out


def test_pigeonhole_via_cli(capsys):
    code = cli.main(["pigeonhole", "4"])
    assert code == 0
    assert "unsat" in capsys.readouterr().out
