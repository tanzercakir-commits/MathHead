from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import contract_artifacts as artifacts  # noqa: E402


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class ContractArtifactTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        workflow_source = ROOT / "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md"
        workflow_target = self.root / "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md"
        workflow_target.parent.mkdir(parents=True)
        workflow_target.write_bytes(workflow_source.read_bytes())
        records = [
            {
                "id": artifacts.WORKFLOW_ID,
                "path": "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md",
                "sha256": artifacts.WORKFLOW_SHA256,
                "state": "accepted",
            }
        ]
        (self.root / artifacts.MANIFEST_PATH).write_bytes(artifacts._render_manifest(records))
        (self.root / "tools").mkdir()
        (self.root / "tools/validator.py").write_text("raise SystemExit(0)\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def contract(
        self,
        contract_id: str = "MH-C-SAMPLE-001",
        *,
        target: str = "tools.sample:run",
        signature: str = "run(value: int) -> int",
        supersedes: str | None = None,
        validators: list[str] | None = None,
        budget: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return {
            "schema": artifacts.SCHEMA,
            "contract_id": contract_id,
            "target": target,
            "signature": signature,
            "requires": ["value is an integer"],
            "ensures": ["result is an integer"],
            "raises": ["ContractArtifactError on invalid input"],
            "effects": {"filesystem": "none", "mutation": "none"},
            "determinism": {"output": "canonical"},
            "budget": budget or {"total_seconds": 5},
            "epistemics": {"success": "validator evidence"},
            "invariants": ["accepted bytes remain immutable"],
            "validators": validators or ["python tools/validator.py"],
            "supersedes": supersedes,
        }

    def input_path(self, data: dict[str, object], name: str = "input.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def propose(self, data: dict[str, object], name: str = "input.json") -> Path:
        artifacts.propose(self.root, self.input_path(data, name))
        return self.root / f"docs/contracts/proposed/{data['contract_id']}.json"

    def screen(self, proposal: Path, name: str = "screen.json") -> Path:
        report = artifacts.prescreen(self.root, proposal)
        path = self.root / name
        path.write_bytes(artifacts._canonical_bytes(report))
        return path

    def accept(self, data: dict[str, object], name: str = "input.json") -> tuple[Path, str]:
        proposal = self.propose(data, name)
        screen = self.screen(proposal, f"{data['contract_id']}.screen.json")
        digest = _sha(proposal.read_bytes())
        artifacts.accept(self.root, proposal, screen, digest, "test-owner")
        return self.root / f"docs/contracts/{data['contract_id']}.json", digest

    def implement(
        self,
        data: dict[str, object],
        digest: str,
        *,
        definition: str = "def run(value: int) -> int:\n    return value\n",
    ) -> Path:
        module = str(data["target"]).split(":", 1)[0]
        path = self.root / (module.replace(".", "/") + ".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'CONTRACT_ID = "{data["contract_id"]}"\n'
            f'CONTRACT_SHA256 = "{digest}"\n\n{definition}',
            encoding="utf-8",
        )
        return path

    def test_schema_rejects_missing_unknown_wrong_type_and_duplicate_json_key(self) -> None:
        base = self.contract()
        cases: list[dict[str, object]] = []
        missing = copy.deepcopy(base)
        missing.pop("ensures")
        cases.append(missing)
        unknown = copy.deepcopy(base)
        unknown["surprise"] = True
        cases.append(unknown)
        wrong_type = copy.deepcopy(base)
        wrong_type["requires"] = "not-a-list"
        cases.append(wrong_type)
        for candidate in cases:
            with self.subTest(candidate=set(candidate)):
                with self.assertRaises(artifacts.ContractArtifactError) as caught:
                    artifacts.validate_contract(candidate)
                self.assertEqual(caught.exception.kind, "schema")

        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts._load_json(duplicate)
        self.assertEqual(caught.exception.kind, "schema")

    def test_zero_argument_signature_is_valid(self) -> None:
        data = self.contract(signature="run() -> int")
        artifacts.validate_contract(data)

    def test_propose_is_canonical_content_addressed_and_immutable(self) -> None:
        data = self.contract()
        proposal = self.propose(data)
        raw = proposal.read_bytes()
        self.assertEqual(raw, artifacts._canonical_bytes(data))
        records, _raw = artifacts._manifest(self.root)
        record = next(item for item in records if item["id"] == data["contract_id"])
        self.assertEqual(record["sha256"], _sha(raw))
        self.assertEqual(record["state"], "proposed")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.propose(self.root, self.input_path(data, "again.json"))
        self.assertEqual(caught.exception.kind, "proposal")
        self.assertEqual(proposal.read_bytes(), raw)

    def test_repository_paths_cannot_escape_root(self) -> None:
        outside = Path(self.temporary.name).with_suffix(".outside-contract.json")
        outside.write_bytes(artifacts._canonical_bytes(self.contract()))
        try:
            with self.assertRaises(artifacts.ContractArtifactError) as caught:
                artifacts.propose(self.root, outside)
            self.assertEqual(caught.exception.kind, "path")
            with self.assertRaises(artifacts.ContractArtifactError) as caught:
                artifacts._argument_path(self.root, Path("../report.json"), must_exist=False)
            self.assertEqual(caught.exception.kind, "path")
        finally:
            outside.unlink(missing_ok=True)

    def test_prescreen_is_deterministic_and_never_accepts(self) -> None:
        data = self.contract()
        proposal = self.propose(data)
        first = artifacts.prescreen(self.root, proposal)
        second = artifacts.prescreen(self.root, proposal)
        self.assertEqual(first, second)
        self.assertEqual(first["acceptance"], "not_granted")
        artifacts._validate_report(first)
        records, _raw = artifacts._manifest(self.root)
        record = next(item for item in records if item["id"] == data["contract_id"])
        self.assertEqual(record["state"], "proposed")
        self.assertFalse((self.root / f"docs/contracts/{data['contract_id']}.json").exists())

    def test_prescreen_rejects_missing_validator_shell_syntax_and_contradiction(self) -> None:
        missing = self.contract(validators=["python tools/missing.py"])
        proposal = self.propose(missing)
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.prescreen(self.root, proposal)
        self.assertEqual(caught.exception.kind, "path")

        shell = self.contract("MH-C-SHELL-001", validators=["python -c pass; touch marker"])
        proposal = self.propose(shell, "shell.json")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.prescreen(self.root, proposal)
        self.assertEqual(caught.exception.kind, "validator")

        contradiction = self.contract("MH-C-CONTRADICTION-001")
        contradiction["requires"] = ["value is positive", "NOT: value is positive"]
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.propose(self.root, self.input_path(contradiction, "contradiction.json"))
        self.assertEqual(caught.exception.kind, "unsatisfiable")

    def test_accept_copies_exact_bytes_and_rejects_forged_or_stale_screen(self) -> None:
        data = self.contract()
        proposal = self.propose(data)
        screen = self.screen(proposal)
        original_screen = screen.read_bytes()
        digest = _sha(proposal.read_bytes())

        forged, _raw = artifacts._load_json(screen)
        forged["forged"] = True
        forged = artifacts._report({key: value for key, value in forged.items() if key != "report_sha256"})
        screen.write_bytes(artifacts._canonical_bytes(forged))
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.accept(self.root, proposal, screen, digest, "test-owner")
        self.assertEqual(caught.exception.kind, "acceptance")

        screen.write_bytes(original_screen)
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.accept(self.root, proposal, screen, "0" * 64, "test-owner")
        self.assertEqual(caught.exception.kind, "acceptance")

        result = artifacts.accept(self.root, proposal, screen, digest, "test-owner")
        accepted = self.root / f"docs/contracts/{data['contract_id']}.json"
        self.assertEqual(accepted.read_bytes(), proposal.read_bytes())
        self.assertEqual(result["status"], "accepted")
        artifacts._validate_report(result)

    def test_acceptance_rolls_back_when_second_or_third_replace_fails(self) -> None:
        real_replace = artifacts.os.replace
        for failure_at in (2, 3):
            with self.subTest(failure_at=failure_at):
                self.tearDown()
                self.setUp()
                data = self.contract()
                proposal = self.propose(data)
                screen = self.screen(proposal)
                digest = _sha(proposal.read_bytes())
                manifest_before = (self.root / artifacts.MANIFEST_PATH).read_bytes()
                calls = 0

                def flaky_replace(source: object, target: object) -> None:
                    nonlocal calls
                    calls += 1
                    if calls == failure_at:
                        raise OSError("injected replace failure")
                    real_replace(source, target)

                with mock.patch.object(artifacts.os, "replace", side_effect=flaky_replace):
                    with self.assertRaises(OSError):
                        artifacts.accept(self.root, proposal, screen, digest, "test-owner")
                self.assertEqual((self.root / artifacts.MANIFEST_PATH).read_bytes(), manifest_before)
                self.assertFalse((self.root / f"docs/contracts/{data['contract_id']}.json").exists())
                self.assertFalse((self.root / artifacts.TRANSACTION_DIR).exists())

    def test_process_control_exception_is_re_raised_after_rollback(self) -> None:
        real_replace = artifacts.os.replace
        data = self.contract()
        proposal = self.propose(data)
        screen = self.screen(proposal)
        digest = _sha(proposal.read_bytes())
        manifest_before = (self.root / artifacts.MANIFEST_PATH).read_bytes()
        calls = 0

        def interrupt_once(source: object, target: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt
            real_replace(source, target)

        with mock.patch.object(artifacts.os, "replace", side_effect=interrupt_once):
            with self.assertRaises(KeyboardInterrupt):
                artifacts.accept(self.root, proposal, screen, digest, "test-owner")
        self.assertEqual((self.root / artifacts.MANIFEST_PATH).read_bytes(), manifest_before)
        self.assertFalse((self.root / artifacts.TRANSACTION_DIR).exists())

    def test_verify_binds_callable_signature_and_hash(self) -> None:
        data = self.contract()
        _accepted, digest = self.accept(data)
        source = self.implement(data, digest)
        report = artifacts.verify(
            self.root, contract_id=str(data["contract_id"]), run_validators=False, require_bound=True
        )
        self.assertEqual(report["contracts"][0]["binding"]["status"], "passed")
        artifacts._validate_report(report)

        source.write_text(
            source.read_text(encoding="utf-8").replace("value: int", "value: str"),
            encoding="utf-8",
        )
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(
                self.root,
                contract_id=str(data["contract_id"]),
                run_validators=False,
                require_bound=True,
            )
        self.assertEqual(caught.exception.kind, "binding")

    def test_verify_rejects_missing_hash_and_ambiguous_symbol(self) -> None:
        data = self.contract()
        _accepted, digest = self.accept(data)
        source = self.implement(data, digest)
        source.write_text("def run(value: int) -> int:\n    return value\n", encoding="utf-8")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(
                self.root,
                contract_id=str(data["contract_id"]),
                run_validators=False,
                require_bound=True,
            )
        self.assertEqual(caught.exception.kind, "binding")

        self.implement(
            data,
            digest,
            definition=(
                "def run(value: int) -> int:\n    return value\n\n"
                "def run(value: int) -> int:\n    return value + 1\n"
            ),
        )
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(
                self.root,
                contract_id=str(data["contract_id"]),
                run_validators=False,
                require_bound=True,
            )
        self.assertEqual(caught.exception.kind, "binding")

    def test_verify_distinguishes_future_implementation_from_required_binding(self) -> None:
        data = self.contract(target="tools.future:run")
        self.accept(data)
        report = artifacts.verify(
            self.root, contract_id=str(data["contract_id"]), run_validators=False, require_bound=False
        )
        self.assertEqual(report["contracts"][0]["binding"]["status"], "not_implemented")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(
                self.root,
                contract_id=str(data["contract_id"]),
                run_validators=False,
                require_bound=True,
            )
        self.assertEqual(caught.exception.kind, "binding")

    def test_supersession_requires_newer_same_family_same_target(self) -> None:
        old = self.contract()
        self.accept(old)

        valid = self.contract("MH-C-SAMPLE-002", supersedes="MH-C-SAMPLE-001")
        valid_proposal = self.propose(valid, "valid.json")
        self.assertEqual(artifacts.prescreen(self.root, valid_proposal)["status"], "passed")
        valid_screen = self.screen(valid_proposal, "valid-screen.json")
        artifacts.accept(
            self.root,
            valid_proposal,
            valid_screen,
            _sha(valid_proposal.read_bytes()),
            "test-owner",
        )
        report = artifacts.verify(
            self.root, contract_id=None, run_validators=True, require_bound=False
        )
        entries = {entry["id"]: entry for entry in report["contracts"]}
        self.assertEqual(
            entries["MH-C-SAMPLE-001"]["validators"][0]["execution"],
            "superseded_not_run",
        )

        no_link = self.contract("MH-C-SAMPLE-003")
        no_link_proposal = self.propose(no_link, "no-link.json")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.prescreen(self.root, no_link_proposal)
        self.assertEqual(caught.exception.kind, "supersession")

        wrong_family = self.contract("MH-C-OTHER-002", supersedes="MH-C-SAMPLE-001")
        wrong_family_proposal = self.propose(wrong_family, "wrong-family.json")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.prescreen(self.root, wrong_family_proposal)
        self.assertEqual(caught.exception.kind, "supersession")

        wrong_target = self.contract(
            "MH-C-SAMPLE-004", target="tools.other:run", supersedes="MH-C-SAMPLE-001"
        )
        wrong_target_proposal = self.propose(wrong_target, "wrong-target.json")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.prescreen(self.root, wrong_target_proposal)
        self.assertEqual(caught.exception.kind, "supersession")

    def test_verify_rejects_noncanonical_acceptance_and_proposal_byte_drift(self) -> None:
        data = self.contract()
        accepted, digest = self.accept(data)
        self.implement(data, digest)
        records, _raw = artifacts._manifest(self.root)
        accepted.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        for record in records:
            if record["id"] == data["contract_id"]:
                record["sha256"] = _sha(accepted.read_bytes())
        (self.root / artifacts.MANIFEST_PATH).write_bytes(artifacts._render_manifest(records))
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(self.root, contract_id=None, run_validators=False, require_bound=False)
        self.assertEqual(caught.exception.kind, "canonical")

        accepted.write_bytes(artifacts._canonical_bytes(data))
        for record in records:
            if record["id"] == data["contract_id"]:
                record["sha256"] = digest
        (self.root / artifacts.MANIFEST_PATH).write_bytes(artifacts._render_manifest(records))
        proposal = self.root / f"docs/contracts/proposed/{data['contract_id']}.json"
        proposal.write_bytes(b"{}\n")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts.verify(self.root, contract_id=None, run_validators=False, require_bound=False)
        self.assertEqual(caught.exception.kind, "proposal")

    def test_validator_execution_records_pass_fail_and_timeout(self) -> None:
        passing = self.contract()
        passed = artifacts._run_validators(self.root, passing)
        self.assertEqual(passed[0]["execution"], "passed")
        self.assertEqual(passed[0]["exit_code"], 0)

        (self.root / "tools/fail.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        failing = self.contract(validators=["python tools/fail.py"])
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts._run_validators(self.root, failing)
        self.assertEqual(caught.exception.kind, "validator")

        (self.root / "tools/slow.py").write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
        slow = self.contract(
            validators=["python tools/slow.py"], budget={"total_seconds": 1}
        )
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts._run_validators(self.root, slow)
        self.assertEqual(caught.exception.kind, "validator-timeout")

    def test_report_comparison_fails_closed_on_drift(self) -> None:
        report = artifacts.verify(
            self.root, contract_id=None, run_validators=False, require_bound=False
        )
        path = self.root / "report.json"
        artifacts._emit_or_compare(report, report_path=path, check_path=None)
        artifacts._emit_or_compare(report, report_path=None, check_path=path)
        path.write_bytes(b"{}\n")
        with self.assertRaises(artifacts.ContractArtifactError) as caught:
            artifacts._emit_or_compare(report, report_path=None, check_path=path)
        self.assertEqual(caught.exception.kind, "report")


if __name__ == "__main__":
    unittest.main()
