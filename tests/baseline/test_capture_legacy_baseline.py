from __future__ import annotations

import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import capture_legacy_baseline as baseline  # noqa: E402
from tools import validate_legacy_baseline as validator  # noqa: E402


ARTIFACT = ROOT / "docs" / "reconstruction" / "legacy-baseline-v1.json"
OBSERVATIONS = ROOT / "docs" / "reconstruction" / "legacy-observations-v1.json"


class LegacyBaselineTests(unittest.TestCase):
    def test_accepted_binding_and_frozen_artifacts(self) -> None:
        files, tests = validator.validate(ROOT)
        self.assertEqual(files, 379)
        self.assertEqual(tests, 1546)

    def test_public_signature_matches_accepted_contract(self) -> None:
        signature = inspect.signature(baseline.main)
        self.assertEqual(tuple(signature.parameters), ("argv",))
        self.assertIsNone(signature.parameters["argv"].default)
        self.assertEqual(signature.return_annotation, "int")

    def test_offline_replay_recomputes_source_fields(self) -> None:
        artifact = baseline.replay(ROOT, "docs/reconstruction/legacy-baseline-v1.json")
        self.assertEqual(artifact["source"]["commit"], "3fc1d00efbecad4f18a401db28e350f2b495c6a5")
        self.assertEqual(artifact["source"]["tree"], "84cd477c1ef8049ca555ceabe0d29a0eb421d74b")

    def test_every_result_state_is_preserved(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        counts = artifact["observations"]["result_counts"]
        self.assertEqual(set(counts), set(baseline.RESULT_STATES))
        self.assertTrue(all(counts[state] > 0 for state in baseline.RESULT_STATES))

    def test_inventory_and_test_identities_are_sorted_and_unique(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        paths = [item["path"] for item in artifact["source"]["inventory"]["files"]]
        nodeids = [item["nodeid"] for item in artifact["source"]["test_collection"]["items"]]
        self.assertEqual(paths, sorted(set(paths)))
        self.assertEqual(nodeids, sorted(set(nodeids)))

    def test_capture_refuses_existing_destination_before_other_work(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "tools/capture_legacy_baseline.py",
                "capture",
                "--source-ref",
                "missing-ref",
                "--observations",
                "missing-observations.json",
                "--output",
                "docs/reconstruction/legacy-baseline-v1.json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("[destination-exists]", result.stderr)

    def test_capture_refuses_absolute_destination(self) -> None:
        with self.assertRaisesRegex(baseline.BaselineError, "inside the repository") as raised:
            baseline.capture(ROOT, "HEAD", "missing.json", "/tmp/baseline.json")
        self.assertEqual(raised.exception.code, "invalid-path")

    def test_replay_refuses_noncanonical_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="baseline-test-", dir=ROOT) as temporary:
            target = Path(temporary) / "noncanonical.json"
            target.write_bytes(ARTIFACT.read_bytes() + b"\n")
            relative = target.relative_to(ROOT).as_posix()
            with self.assertRaises(baseline.BaselineError) as raised:
                baseline.replay(ROOT, relative)
            self.assertEqual(raised.exception.code, "artifact-not-canonical")

    def test_replay_detects_source_derived_tampering(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        artifact["source"]["package"]["version"] = "0.0-tampered"
        with tempfile.TemporaryDirectory(prefix="baseline-test-", dir=ROOT) as temporary:
            target = Path(temporary) / "tampered.json"
            target.write_bytes(baseline._canonical_bytes(artifact))
            relative = target.relative_to(ROOT).as_posix()
            with self.assertRaises(baseline.BaselineError) as raised:
                baseline.replay(ROOT, relative)
            self.assertEqual(raised.exception.code, "source-replay-mismatch")

    def test_capture_rejects_omitted_failure_evidence_without_output(self) -> None:
        document = json.loads(OBSERVATIONS.read_text(encoding="utf-8"))
        document["failure_categories"] = []
        with tempfile.TemporaryDirectory(prefix="baseline-test-", dir=ROOT) as temporary:
            directory = Path(temporary)
            observations = directory / "observations.json"
            output = directory / "output.json"
            observations.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(baseline.BaselineError) as raised:
                baseline.capture(
                    ROOT,
                    "3fc1d00efbecad4f18a401db28e350f2b495c6a5",
                    observations.relative_to(ROOT).as_posix(),
                    output.relative_to(ROOT).as_posix(),
                )
            self.assertEqual(raised.exception.code, "failure-evidence-missing")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
