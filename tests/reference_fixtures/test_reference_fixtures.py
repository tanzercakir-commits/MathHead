from __future__ import annotations

import builtins
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_reference_fixtures as fixtures  # noqa: E402


class ReferenceFixtureTests(unittest.TestCase):
    def fixture_root(self) -> tempfile.TemporaryDirectory[str]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        shutil.copytree(ROOT / "docs/fixtures", root / "docs/fixtures")
        shutil.copytree(ROOT / "docs/contracts", root / "docs/contracts")
        return temporary

    def manifest(self, root: Path = ROOT) -> dict[str, object]:
        return copy.deepcopy(fixtures.load_json(root / fixtures.MANIFEST_PATH)[0])

    def write_manifest(self, root: Path, manifest: dict[str, object]) -> None:
        manifest["bundle_sha256"] = fixtures.bundle_basis_sha256(manifest)
        (root / fixtures.MANIFEST_PATH).write_bytes(fixtures.canonical_bytes(manifest))

    def scenario(self, manifest: dict[str, object], scenario_id: str) -> dict[str, object]:
        return next(
            scenario for scenario in manifest["scenarios"] if scenario["scenario_id"] == scenario_id
        )

    def binding(
        self, manifest: dict[str, object], scenario_id: str, role: str
    ) -> dict[str, object]:
        scenario = self.scenario(manifest, scenario_id)
        return next(item for item in scenario["artifacts"] if item["role"] == role)

    def replace_object(
        self,
        root: Path,
        manifest: dict[str, object],
        old_digest: str,
        value: dict[str, object],
    ) -> str:
        raw = fixtures.canonical_bytes(value)
        new_digest = fixtures._sha(raw)  # noqa: SLF001
        old_path = root / fixtures.OBJECT_DIR / f"{old_digest}.json"
        new_path = root / fixtures.OBJECT_DIR / f"{new_digest}.json"
        old_path.unlink()
        new_path.write_bytes(raw)
        record = next(item for item in manifest["objects"] if item["sha256"] == old_digest)
        record.update(
            {
                "sha256": new_digest,
                "path": f"{fixtures.OBJECT_DIR.as_posix()}/{new_digest}.json",
                "byte_count": len(raw),
            }
        )
        manifest["objects"].sort(key=lambda item: item["sha256"])
        return new_digest

    def assert_invalid(self, root: Path, kind: str, *, alternatives: tuple[str, ...] = ()) -> None:
        with self.assertRaises(fixtures.ReferenceFixtureError) as caught:
            fixtures.validate_bundle(root)
        self.assertIn(caught.exception.kind, (kind, *alternatives))

    def test_repository_bundle_is_valid_and_has_stable_identity(self) -> None:
        report = fixtures.validate_bundle(ROOT)
        self.assertEqual(report["scenario_count"], 8)
        self.assertEqual(report["contract_count"], 9)
        self.assertEqual(report["object_count"], 43)
        self.assertEqual(report["attachment_count"], 18)
        self.assertEqual(
            report["bundle_sha256"],
            "4132b29b69600f8ff48477515853f66bb748c7337735c00db8e634987f70ddca",
        )

    def test_manifest_and_schema_are_canonical_closed_draft_202012(self) -> None:
        manifest, manifest_raw = fixtures.load_json(ROOT / fixtures.MANIFEST_PATH, canonical=True)
        schema, schema_raw = fixtures.load_json(ROOT / fixtures.SCHEMA_PATH, canonical=True)
        self.assertEqual(manifest_raw, fixtures.canonical_bytes(manifest))
        self.assertEqual(schema_raw, fixtures.canonical_bytes(schema))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(fixtures._sha(schema_raw), manifest["manifest_schema_sha256"])  # noqa: SLF001

    def test_scenario_order_presence_and_non_promotion_are_exact(self) -> None:
        manifest = self.manifest()
        self.assertEqual(manifest["scenario_order"], list(fixtures.SCENARIO_ORDER))
        expected_absent = {"ambiguity", "unsupported", "timeout"}
        for scenario_id in fixtures.SCENARIO_ORDER:
            with self.subTest(scenario=scenario_id):
                scenario = self.scenario(manifest, scenario_id)
                self.assertEqual(
                    [item["role"] for item in scenario["artifacts"]],
                    list(fixtures.ROLE_ORDER),
                )
                evidence = self.binding(manifest, scenario_id, "evidence")
                certificate = self.binding(manifest, scenario_id, "certificate")
                state = "absent" if scenario_id in expected_absent else "present"
                self.assertEqual(evidence["state"], state)
                self.assertEqual(certificate["state"], state)
                if scenario["expected"]["authority"] == "none":
                    self.assertNotIn(
                        scenario["expected"]["mathematical_status"],
                        {"proved", "refuted"},
                    )

    def test_object_store_is_content_addressed_deduplicated_and_complete(self) -> None:
        manifest = self.manifest()
        hashes = [item["sha256"] for item in manifest["objects"]]
        self.assertEqual(hashes, sorted(set(hashes)))
        self.assertLess(len(hashes), 8 * 7 + 18)
        for record in manifest["objects"]:
            raw = (ROOT / record["path"]).read_bytes()
            self.assertEqual(fixtures._sha(raw), record["sha256"])  # noqa: SLF001
            self.assertEqual(len(raw), record["byte_count"])

    def test_generation_is_byte_identical_in_an_isolated_root(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            generated = fixtures.write_bundle(root)
            self.assertEqual(
                fixtures.canonical_bytes(generated), (ROOT / fixtures.MANIFEST_PATH).read_bytes()
            )
            fixtures.validate_bundle(root)
            source_objects = {
                path.name: path.read_bytes() for path in (ROOT / fixtures.OBJECT_DIR).glob("*.json")
            }
            moved_objects = {
                path.name: path.read_bytes() for path in (root / fixtures.OBJECT_DIR).glob("*.json")
            }
            self.assertEqual(moved_objects, source_objects)

    def test_relocated_subprocess_regenerates_the_same_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "relocated"
            shutil.copytree(ROOT / "tools", root / "tools")
            shutil.copytree(ROOT / "docs/contracts", root / "docs/contracts")
            schema_target = root / fixtures.SCHEMA_PATH
            schema_target.parent.mkdir(parents=True)
            shutil.copy2(ROOT / fixtures.SCHEMA_PATH, schema_target)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(root / "tools/validate_reference_fixtures.py"),
                    "--root",
                    str(root),
                    "--write",
                ],
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(
                (root / fixtures.MANIFEST_PATH).read_bytes(),
                (ROOT / fixtures.MANIFEST_PATH).read_bytes(),
            )

    def test_dependency_minimal_validation_matches_full_profile(self) -> None:
        real_import = builtins.__import__

        def without_jsonschema(name: str, *args: object, **kwargs: object) -> object:
            if name == "jsonschema":
                raise ImportError("simulated dependency-minimal profile")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=without_jsonschema):
            report = fixtures.validate_bundle(ROOT)
        self.assertEqual(report["bundle_sha256"], self.manifest()["bundle_sha256"])

    def test_duplicate_manifest_key_fails_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            path = root / fixtures.MANIFEST_PATH
            path.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            self.assert_invalid(root, "duplicate-key")

    def test_noncanonical_manifest_bytes_fail_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            path = root / fixtures.MANIFEST_PATH
            path.write_text(json.dumps(self.manifest(), indent=2) + "\n", encoding="utf-8")
            self.assert_invalid(root, "canonical")

    def test_scenario_reorder_fails_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            manifest["scenarios"][0], manifest["scenarios"][1] = (
                manifest["scenarios"][1],
                manifest["scenarios"][0],
            )
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "scenario-order")

    def test_absent_is_not_an_empty_present_artifact(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            binding = self.binding(manifest, "timeout", "evidence")
            binding.clear()
            binding.update(
                {
                    "role": "evidence",
                    "state": "present",
                    "contract_id": fixtures.ROLE_CONTRACTS["evidence"][0],
                    "contract_sha256": fixtures.ROLE_CONTRACTS["evidence"][1],
                    "schema": fixtures.ROLE_CONTRACTS["evidence"][2],
                    "sha256": "0" * 64,
                    "byte_count": 0,
                    "depends_on_sha256": [],
                }
            )
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "reference", alternatives=("empty", "shape"))

    def test_corrupt_object_bytes_fail_hash_check(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            digest = self.binding(manifest, "proof", "engine_result")["sha256"]
            path = root / fixtures.OBJECT_DIR / f"{digest}.json"
            path.write_bytes(path.read_bytes().replace(b'"completed"', b'"completeD"', 1))
            self.assert_invalid(root, "object-hash")

    def test_missing_and_stale_objects_fail_inventory(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            digest = self.binding(manifest, "proof", "engine_result")["sha256"]
            (root / fixtures.OBJECT_DIR / f"{digest}.json").unlink()
            self.assert_invalid(root, "json")
        with self.fixture_root() as directory:
            root = Path(directory)
            (root / fixtures.OBJECT_DIR / f"{'f' * 64}.json").write_text("{}\n", encoding="utf-8")
            self.assert_invalid(root, "object-inventory")

    def test_contract_and_schema_hash_drift_fail_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            manifest["contracts"][0]["sha256"] = "f" * 64
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "contract")
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            manifest["manifest_schema_sha256"] = "f" * 64
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "schema-hash")
        with self.fixture_root() as directory:
            root = Path(directory)
            path = root / "docs/contracts/MH-C-PROBLEM-IR-002.json"
            path.write_bytes(path.read_bytes() + b"\n")
            self.assert_invalid(root, "contract")

    def test_conformance_report_drift_fails_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            path = root / fixtures.CONFORMANCE_REPORT_PATH
            path.write_bytes(path.read_bytes() + b"\n")
            self.assert_invalid(root, "conformance")

    def test_missing_dependency_and_cycle_fail_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            context = self.binding(manifest, "proof", "theory_context")
            context["depends_on_sha256"] = []
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "regeneration")
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            result = self.binding(manifest, "proof", "engine_result")
            result["depends_on_sha256"] = [result["sha256"]]
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "dependency-cycle")

    def test_route_and_expected_outcome_drift_fail_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            self.scenario(manifest, "proof")["routing"]["cost"] += 1
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "routing")
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            self.scenario(manifest, "invalid-certificate")["expected"]["authority"] = (
                "checker_attested"
            )
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "expectation")

    def test_engine_schema_and_cross_link_mutations_fail_closed(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            binding = self.binding(manifest, "proof", "engine_result")
            old_digest = binding["sha256"]
            value = fixtures.load_json(root / fixtures.OBJECT_DIR / f"{old_digest}.json")[0]
            value["unexpected"] = True
            new_digest = self.replace_object(root, manifest, old_digest, value)
            binding["sha256"] = new_digest
            binding["byte_count"] = len(fixtures.canonical_bytes(value))
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "artifact-schema")
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            binding = self.binding(manifest, "proof", "engine_result")
            old_digest = binding["sha256"]
            value = fixtures.load_json(root / fixtures.OBJECT_DIR / f"{old_digest}.json")[0]
            value["request"]["problem_ir_sha256"] = "f" * 64
            value["replay"]["basis_sha256"] = fixtures.engine_result.replay_basis_sha256(value)
            new_digest = self.replace_object(root, manifest, old_digest, value)
            binding["sha256"] = new_digest
            binding["byte_count"] = len(fixtures.canonical_bytes(value))
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "cross-link", alternatives=("artifact-epistemic",))

    def test_failure_result_cannot_be_replaced_by_a_proof(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            timeout = self.binding(manifest, "timeout", "engine_result")
            proof = self.binding(manifest, "proof", "engine_result")
            timeout["sha256"] = proof["sha256"]
            timeout["byte_count"] = proof["byte_count"]
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "dependency", alternatives=("cross-link", "budget"))

    def test_replay_mismatch_cannot_be_promoted_to_verified(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            binding = self.binding(manifest, "replay-mismatch", "certificate")
            old_digest = binding["sha256"]
            value = fixtures.load_json(root / fixtures.OBJECT_DIR / f"{old_digest}.json")[0]
            value["verdict"] = {
                "status": "verified",
                "authority": "checker_attested",
                "checker_result_artifact_id": "artifact_checker_result",
                "supporting_artifact_ids": [
                    "artifact_checker_result",
                    "artifact_replay_log",
                ],
                "diagnostic_ids": [],
            }
            value["diagnostics"] = []
            value["replay"]["basis_sha256"] = (
                fixtures.evidence_certificate.certificate_replay_basis_sha256(value)
            )
            new_digest = self.replace_object(root, manifest, old_digest, value)
            binding["sha256"] = new_digest
            binding["byte_count"] = len(fixtures.canonical_bytes(value))
            engine_binding = self.binding(manifest, "replay-mismatch", "engine_result")
            engine_binding["depends_on_sha256"] = [
                new_digest if item == old_digest else item
                for item in engine_binding["depends_on_sha256"]
            ]
            engine_binding["depends_on_sha256"].sort()
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "artifact-replay")

    def test_disagreement_requires_distinct_producers(self) -> None:
        with self.fixture_root() as directory:
            root = Path(directory)
            manifest = self.manifest(root)
            binding = self.binding(manifest, "backend-disagreement", "engine_result")
            old_digest = binding["sha256"]
            value = fixtures.load_json(root / fixtures.OBJECT_DIR / f"{old_digest}.json")[0]
            backend_ids = value["execution"]["backend_artifact_ids"]
            artifacts = {item["artifact_id"]: item for item in value["artifacts"]}
            artifacts[backend_ids[0]]["producer_component_id"] = artifacts[backend_ids[1]][
                "producer_component_id"
            ]
            new_digest = self.replace_object(root, manifest, old_digest, value)
            binding["sha256"] = new_digest
            binding["byte_count"] = len(fixtures.canonical_bytes(value))
            self.write_manifest(root, manifest)
            self.assert_invalid(root, "artifact-outcome")


if __name__ == "__main__":
    unittest.main()
