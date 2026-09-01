from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import contract_artifacts as artifacts
from tools import validate_contract_conformance as conformance


ROOT = Path(__file__).resolve().parents[2]


class ContractConformanceTests(unittest.TestCase):
    def copy_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory(prefix="mathhead-conformance-test-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / "docs/contracts", root / "docs/contracts")
        shutil.copytree(ROOT / "tools", root / "tools")
        shutil.copytree(ROOT / "tests", root / "tests")
        return root

    def load_contract(self, contract_id: str) -> dict[str, object]:
        return json.loads((ROOT / f"docs/contracts/{contract_id}.json").read_text())

    def synthetic_root(
        self,
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object], str]:
        temporary = tempfile.TemporaryDirectory(prefix="mathhead-binding-test-")
        root = Path(temporary.name)
        source_path = root / "src/mathhead/synthetic.py"
        source_path.parent.mkdir(parents=True)
        contract = conformance._synthetic_contract()  # noqa: SLF001
        contract_sha256 = hashlib.sha256(conformance.canonical_bytes(contract)).hexdigest()
        source_path.write_bytes(conformance._synthetic_source(contract_sha256))  # noqa: SLF001
        return temporary, root, contract, contract_sha256

    def test_repository_report_is_deterministic_and_complete(self) -> None:
        first = conformance.build_report(ROOT, run_validators=False)
        second = conformance.build_report(ROOT, run_validators=False)
        self.assertEqual(first, second)
        conformance.validate_report(first)
        self.assertEqual(first["status"], "passed")
        self.assertEqual(first["contract_count"], 8)
        self.assertEqual(len(first["schema_probes"]), 7)
        self.assertEqual(len(first["negative_probes"]), 10)
        self.assertEqual(len(first["validators"]), 7)
        self.assertEqual({item["status"] for item in first["validators"]}, {"not_run"})
        self.assertEqual(
            first["manifest"]["sha256"],
            "3921af074b4ebe8ddf483f1e46e7d10ee87c315582f3fe50e736883d62c8579d",
        )

    def test_later_phase_contracts_do_not_rewrite_p2_evidence(self) -> None:
        root = self.copy_root()
        before = conformance.build_report(root, run_validators=False)
        records, _raw = artifacts._manifest(root)  # noqa: SLF001
        later = root / "docs/contracts/MH-C-LATER-PHASE-999.json"
        later.write_bytes(b"{}\n")
        records.append(
            {
                "id": "MH-C-LATER-PHASE-999",
                "path": "docs/contracts/MH-C-LATER-PHASE-999.json",
                "sha256": hashlib.sha256(later.read_bytes()).hexdigest(),
                "state": "accepted",
            }
        )
        (root / conformance.MANIFEST_PATH).write_bytes(
            artifacts._render_manifest(records)  # noqa: SLF001
        )
        after = conformance.build_report(root, run_validators=False)
        self.assertEqual(before, after)

    def test_cli_writes_and_checks_the_same_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mathhead-report-test-") as directory:
            report = Path(directory) / "report.json"
            command = [
                sys.executable,
                str(ROOT / "tools/validate_contract_conformance.py"),
                "--skip-validator-execution",
            ]
            created = subprocess.run(
                [*command, "--report", str(report)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            checked = subprocess.run(
                [*command, "--check-report", str(report)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            value, raw = conformance.load_json(report, canonical=True)
            conformance.validate_report(value)
            self.assertEqual(raw, conformance.canonical_bytes(value))

    def test_active_contract_inventory_targets_and_supersession_are_exact(self) -> None:
        report = conformance.build_report(ROOT, run_validators=False)
        observed = {
            item["contract_id"]: (item["target"], item["supersedes"])
            for item in report["contracts"]
        }
        expected = {
            spec.contract_id: (spec.target, spec.supersedes) for spec in conformance.CONTRACTS
        }
        self.assertEqual(observed, expected)

    def test_manifest_hash_drift_fails(self) -> None:
        root = self.copy_root()
        manifest = root / conformance.MANIFEST_PATH
        raw = manifest.read_text()
        spec = conformance.CONTRACTS[1]
        manifest.write_text(raw.replace(spec.sha256, "0" * 64, 1))
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.build_report(root, run_validators=False)
        self.assertEqual(raised.exception.kind, "manifest")

    def test_accepted_and_proposed_byte_drift_fails(self) -> None:
        root = self.copy_root()
        proposal = root / "docs/contracts/proposed/MH-C-PROBLEM-IR-002.json"
        proposal.write_bytes(proposal.read_bytes() + b" ")
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.build_report(root, run_validators=False)
        self.assertEqual(raised.exception.kind, "canonical")

    def test_schema_hash_drift_fails_before_instance_use(self) -> None:
        root = self.copy_root()
        schema = root / "docs/contracts/schemas/problem-ir-v1.schema.json"
        schema.write_bytes(schema.read_bytes() + b" ")
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.build_report(root, run_validators=False)
        self.assertEqual(raised.exception.kind, "schema-hash")

    def test_dependency_minimal_schema_meta_fallback_is_deterministic(self) -> None:
        with mock.patch.object(conformance, "Draft202012Validator", None):
            fallback = conformance.build_report(ROOT, run_validators=False)
        standard = conformance.build_report(ROOT, run_validators=False)
        self.assertEqual(fallback, standard)

    def test_dependency_minimal_schema_meta_rejects_malformed_keywords(self) -> None:
        with self.assertRaises(conformance.ConformanceError) as invalid_type:
            conformance._validate_schema_keywords({"type": 7}, "$")  # noqa: SLF001
        with self.assertRaises(conformance.ConformanceError) as invalid_range:
            conformance._validate_schema_keywords(  # noqa: SLF001
                {"type": "array", "minItems": 2, "maxItems": 1},
                "$",
            )
        self.assertEqual(invalid_type.exception.kind, "schema-meta")
        self.assertEqual(invalid_range.exception.kind, "schema-meta")

    def test_acceptance_report_identity_drift_fails(self) -> None:
        root = self.copy_root()
        path = root / "docs/contracts/reports/MH-C-PROBLEM-IR-002.acceptance.json"
        value = json.loads(path.read_text())
        value["authority"] = "forged-authority"
        path.write_bytes(conformance.canonical_bytes(value))
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.build_report(root, run_validators=False)
        self.assertEqual(raised.exception.kind, "report")

    def test_contract_unknown_and_missing_fields_fail(self) -> None:
        value = self.load_contract("MH-C-PROBLEM-IR-002")
        unknown = copy.deepcopy(value)
        unknown["unexpected"] = True
        missing = copy.deepcopy(value)
        del missing["ensures"]
        with self.assertRaises(artifacts.ContractArtifactError) as unknown_error:
            artifacts.validate_contract(unknown)
        with self.assertRaises(artifacts.ContractArtifactError) as missing_error:
            artifacts.validate_contract(missing)
        self.assertEqual(unknown_error.exception.kind, "schema")
        self.assertEqual(missing_error.exception.kind, "schema")

    def test_unsatisfiable_requirement_pair_fails(self) -> None:
        value = self.load_contract("MH-C-PROBLEM-IR-002")
        value["requires"].extend(["condition", "NOT: condition"])
        with self.assertRaises(artifacts.ContractArtifactError) as raised:
            artifacts._assert_decidable_consistency(value)  # noqa: SLF001
        self.assertEqual(raised.exception.kind, "unsatisfiable")

    def test_primary_validator_removal_fails(self) -> None:
        spec = conformance.CONTRACT_BY_ID["MH-C-PROBLEM-IR-002"]
        value = self.load_contract(spec.contract_id)
        value["validators"].remove(spec.primary_validator)
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.validate_contract_payload(value, spec, ROOT)
        self.assertEqual(raised.exception.kind, "validator")

    def test_validator_shell_syntax_and_missing_reference_fail(self) -> None:
        spec = conformance.CONTRACT_BY_ID["MH-C-PROBLEM-IR-002"]
        shell = self.load_contract(spec.contract_id)
        shell["validators"][0] = "python tools/validate_problem_ir_contract.py && python -V"
        missing = self.load_contract(spec.contract_id)
        missing["validators"][0] = "python tools/not_present.py"
        for value in (shell, missing):
            with self.assertRaises(conformance.ConformanceError) as raised:
                conformance.validate_contract_payload(value, spec, ROOT)
            self.assertEqual(raised.exception.kind, "validator")

    def test_explicit_dependency_hash_removal_fails(self) -> None:
        spec = conformance.CONTRACT_BY_ID["MH-C-CERTIFICATE-001"]
        value = self.load_contract(spec.contract_id)
        dependency_id, dependency_sha256 = spec.explicit_dependencies[0]
        value["requires"] = [
            clause.replace(f"{dependency_id}={dependency_sha256}", dependency_id)
            for clause in value["requires"]
        ]
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.validate_contract_payload(value, spec, ROOT)
        self.assertEqual(raised.exception.kind, "dependency")

    def test_target_and_supersession_drift_fail(self) -> None:
        spec = conformance.CONTRACT_BY_ID["MH-C-PROBLEM-IR-002"]
        target = self.load_contract(spec.contract_id)
        target["target"] = "mathhead.ir:Other"
        target["signature"] = target["signature"].replace("ProblemIR(", "Other(", 1)
        supersession = self.load_contract(spec.contract_id)
        supersession["supersedes"] = None
        with self.assertRaises(conformance.ConformanceError) as target_error:
            conformance.validate_contract_payload(target, spec, ROOT)
        with self.assertRaises(conformance.ConformanceError) as supersession_error:
            conformance.validate_contract_payload(supersession, spec, ROOT)
        self.assertEqual(target_error.exception.kind, "target")
        self.assertEqual(supersession_error.exception.kind, "supersession")

    def test_every_schema_accepts_positive_and_rejects_root_drift(self) -> None:
        report = conformance.build_report(ROOT, run_validators=False)
        for probe in report["schema_probes"]:
            self.assertEqual(
                {
                    probe["positive_instance"],
                    probe["unknown_field_rejection"],
                    probe["missing_field_rejection"],
                },
                {"passed"},
            )

    def test_duplicate_json_key_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mathhead-json-test-") as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema":1,"schema":2}\n')
            with self.assertRaises(conformance.ConformanceError) as raised:
                conformance.load_json(path)
        self.assertEqual(raised.exception.kind, "duplicate-key")

    def test_exact_synthetic_implementation_binding_passes(self) -> None:
        temporary, root, contract, contract_sha256 = self.synthetic_root()
        self.addCleanup(temporary.cleanup)
        binding = conformance.verify_implementation_binding(
            root,
            contract,
            contract_sha256,
            required=True,
            require_source_hash=True,
        )
        self.assertEqual(binding["status"], "passed")
        self.assertRegex(binding["implementation_basis_sha256"], r"^[0-9a-f]{64}$")

    def test_synthetic_signature_drift_fails(self) -> None:
        temporary, root, contract, contract_sha256 = self.synthetic_root()
        self.addCleanup(temporary.cleanup)
        source = root / "src/mathhead/synthetic.py"
        source.write_bytes(source.read_bytes().replace(b"value: str", b"value: bytes"))
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.verify_implementation_binding(
                root,
                contract,
                contract_sha256,
                required=True,
                require_source_hash=True,
            )
        self.assertEqual(raised.exception.kind, "binding")

    def test_synthetic_contract_hash_drift_fails(self) -> None:
        temporary, root, contract, contract_sha256 = self.synthetic_root()
        self.addCleanup(temporary.cleanup)
        source = root / "src/mathhead/synthetic.py"
        source.write_bytes(source.read_bytes().replace(contract_sha256.encode(), b"f" * 64))
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.verify_implementation_binding(
                root,
                contract,
                contract_sha256,
                required=True,
                require_source_hash=True,
            )
        self.assertEqual(raised.exception.kind, "binding")

    def test_synthetic_source_basis_drift_fails(self) -> None:
        temporary, root, contract, contract_sha256 = self.synthetic_root()
        self.addCleanup(temporary.cleanup)
        source = root / "src/mathhead/synthetic.py"
        source.write_bytes(
            source.read_bytes().replace(b"self.value = value", b"self.value = value.strip()")
        )
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.verify_implementation_binding(
                root,
                contract,
                contract_sha256,
                required=True,
                require_source_hash=True,
            )
        self.assertEqual(raised.exception.kind, "implementation-hash")

    def test_report_identity_tamper_fails(self) -> None:
        report = conformance.build_report(ROOT, run_validators=False)
        report["authority"] = "forged authority"
        with self.assertRaises(conformance.ConformanceError) as raised:
            conformance.validate_report(report)
        self.assertEqual(raised.exception.kind, "report")

    def test_future_targets_are_not_misreported_as_implemented(self) -> None:
        report = conformance.build_report(ROOT, run_validators=False)
        bindings = {item["contract_id"]: item["binding"]["status"] for item in report["contracts"]}
        self.assertEqual(bindings["MH-C-CONTRACT-ARTIFACTS-002"], "passed")
        self.assertEqual(set(bindings.values()), {"passed", "not_implemented"})


if __name__ == "__main__":
    unittest.main()
