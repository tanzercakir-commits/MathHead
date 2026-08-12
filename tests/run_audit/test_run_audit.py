from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
from threading import Event
import unittest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.run_audit.fixtures import (  # noqa: E402
    fallback_bundle,
    single_bundle,
    success_bundle,
)


SCHEMAS = (
    "run-audit-object-v1.schema.json",
    "run-audit-event-v1.schema.json",
    "run-audit-manifest-v1.schema.json",
    "run-logical-report-v1.schema.json",
    "run-audit-replay-result-v1.schema.json",
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def self_hash(value: dict[str, object], field: str) -> None:
    value[field] = None
    value[field] = sha(canonical(value))


class RunAuditContractTests(unittest.TestCase):
    def test_accepted_contracts_and_schema_hashes_are_exact(self) -> None:
        from mathhead import run_audit

        self.assertEqual(
            run_audit.AUDITED_RUN_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-AUDITED-RUN-001.json").read_bytes()),
        )
        self.assertEqual(
            run_audit.REPLAY_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-RUN-AUDIT-REPLAY-001.json").read_bytes()),
        )
        for name in SCHEMAS:
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            schema = json.loads(raw)
            self.assertFalse(schema["additionalProperties"], name)
            self.assertEqual(run_audit.SCHEMA_SHA256S[schema["properties"]["schema"]["const"]], sha(raw))

    def test_contract_bindings_are_implementation_bound(self) -> None:
        for contract in ("MH-C-AUDITED-RUN-001", "MH-C-RUN-AUDIT-REPLAY-001"):
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/contract_artifacts.py",
                    "verify",
                    "--contract",
                    contract,
                    "--require-bound",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


class RunAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = success_bundle()
        cls.fallback = fallback_bundle()

    def test_success_bundle_replays_complete_and_round_trips(self) -> None:
        from mathhead.run_audit import (
            parse_run_audit_replay_result,
            replay_run_audit,
            run_audit_replay_result_bytes,
        )

        bundle = self.fixture.bundle
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        self.assertEqual((replay.status, replay.reason_code), ("complete", "REPLAY_COMPLETE"))
        self.assertEqual((replay.portfolio_status, replay.mathematical_verdict), ("succeeded", "proved"))
        self.assertGreaterEqual(replay.object_count, 18)
        self.assertGreaterEqual(replay.event_count, 10)
        raw = run_audit_replay_result_bytes(replay)
        self.assertEqual(
            parse_run_audit_replay_result(raw, bundle.manifest, bundle.objects),
            replay,
        )

    def test_fallback_is_exactly_ordered_and_replays_refutation(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = self.fallback.bundle
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        report = json.loads(bundle.logical_report)
        manifest = json.loads(bundle.manifest)
        self.assertEqual((replay.status, replay.mathematical_verdict), ("complete", "refuted"))
        self.assertEqual([item["attempt_order"] for item in report["attempts"]], [0, 1])
        transitions = [item for item in manifest["events"] if item["kind"] == "transition_selected"]
        self.assertEqual([item["attempt_order"] for item in transitions], [0, 1])
        self.assertEqual([item["outcome"] for item in transitions], ["invalid_evidence", "success"])

    def test_every_terminal_producer_and_checker_path_is_replayable(self) -> None:
        from mathhead.run_audit import replay_run_audit

        evidence_cases = {
            "unsupported": ("unsupported", "unsupported"),
            "incomplete": ("ambiguous", "ambiguous"),
            "cancelled": ("cancelled", "cancelled"),
            "exhausted": ("exhausted", "exhausted"),
            "truncated": ("truncated", "truncated"),
            "error": ("failed", "producer_error"),
        }
        for evidence_status, (terminal, outcome) in evidence_cases.items():
            with self.subTest(evidence_status=evidence_status):
                bundle = single_bundle(evidence_status=evidence_status).bundle
                replay = replay_run_audit(bundle.manifest, bundle.objects)
                report = json.loads(bundle.logical_report)
                self.assertEqual((replay.status, replay.portfolio_status), ("complete", terminal))
                self.assertEqual(report["attempts"][0]["outcome"], outcome)
                self.assertIsNone(report["selected_evidence_sha256"])
                self.assertFalse(replay.mathematical_authority)

        checker_cases = {
            "invalid": ("disagreement", "checker_disagreement"),
            "unsupported": ("inconclusive", "checker_inconclusive"),
            "inconclusive": ("inconclusive", "checker_inconclusive"),
            "cancelled": ("cancelled", "cancelled"),
            "exhausted": ("exhausted", "exhausted"),
            "truncated": ("truncated", "truncated"),
            "verifier_failed": ("verifier_failed", "verifier_failure"),
            "disagreement": ("disagreement", "checker_disagreement"),
        }
        for checker_status, (terminal, outcome) in checker_cases.items():
            with self.subTest(checker_status=checker_status):
                bundle = single_bundle(certificate_status=checker_status).bundle
                replay = replay_run_audit(bundle.manifest, bundle.objects)
                report = json.loads(bundle.logical_report)
                self.assertEqual((replay.status, replay.portfolio_status), ("complete", terminal))
                self.assertEqual(report["attempts"][0]["outcome"], outcome)
                self.assertIsNone(report["selected_certificate_sha256"])
                self.assertEqual(replay.authority_tier, "none")

        cancelled = Event()
        cancelled.set()
        exceptional_cases = (
            (single_bundle(malformed_evidence=True), "invalid_evidence"),
            (single_bundle(producer_exit=7), "producer_error"),
            (single_bundle(cancel_event=cancelled), "cancelled"),
            (single_bundle(agreement=False), "checker_disagreement"),
        )
        for audited, outcome in exceptional_cases:
            with self.subTest(outcome=outcome):
                replay = replay_run_audit(audited.bundle.manifest, audited.bundle.objects)
                report = json.loads(audited.bundle.logical_report)
                self.assertEqual(replay.status, "complete")
                self.assertEqual(report["attempts"][0]["outcome"], outcome)
                self.assertFalse(audited.bundle.mathematical_authority)

    def test_event_chain_is_contiguous_content_addressed_and_clock_free(self) -> None:
        manifest = json.loads(self.fixture.bundle.manifest)
        previous = None
        for index, event in enumerate(manifest["events"]):
            self.assertEqual(event["event_order"], index)
            self.assertEqual(event["previous_event_sha256"], previous)
            candidate = copy.deepcopy(event)
            identity = candidate["event_sha256"]
            self_hash(candidate, "event_sha256")
            self.assertEqual(candidate["event_sha256"], identity)
            previous = identity
        encoded = self.fixture.bundle.manifest + self.fixture.bundle.logical_report
        for forbidden in (
            b"/tmp",
            b"workspace_root",
            b"executable_path",
            b"environment",
            b"password",
            b"token",
            b"pid",
            b"timestamp",
            b"monotonic",
        ):
            self.assertNotIn(forbidden, encoded.lower())

    def test_normalized_input_plan_plugin_budget_and_checker_are_present(self) -> None:
        manifest = json.loads(self.fixture.bundle.manifest)
        report = json.loads(self.fixture.bundle.logical_report)
        roles = {item["role_id"]: item for item in manifest["objects"]}
        self.assertEqual(roles["normalized_input"]["sha256"], manifest["normalized_input_sha256"])
        self.assertIn("planning_result", roles)
        self.assertIn("initial_parent_budget", roles)
        self.assertIn("final_parent_budget", roles)
        self.assertTrue(any(name.startswith("checker_decision_") for name in roles))
        self.assertEqual(len(report["plugins"]), 1)
        self.assertEqual(report["plugins"][0]["strategy_sha256"], report["selected_strategy_sha256"])
        self.assertEqual(report["authority_tier"], "checker_attestation")

    def test_object_tuple_is_digest_sorted_unique_and_closed(self) -> None:
        bundle = self.fixture.bundle
        physical = [sha(raw) for raw in bundle.objects]
        self.assertEqual(physical, sorted(set(physical)))
        manifest = json.loads(bundle.manifest)
        self.assertEqual(set(physical), {item["sha256"] for item in manifest["objects"]})
        self.assertIn(bundle.logical_report_sha256, physical)

    def test_missing_surplus_duplicate_reordered_and_corrupt_objects_fail(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = self.fixture.bundle
        cases = (
            bundle.objects[:-1],
            (*bundle.objects, canonical({"schema": "mathhead.surplus.v1"})),
            (*bundle.objects, bundle.objects[0]),
            tuple(reversed(bundle.objects)),
            (bundle.objects[0] + b" ", *bundle.objects[1:]),
        )
        for objects in cases:
            with self.subTest(count=len(objects)):
                self.assertNotEqual(replay_run_audit(bundle.manifest, objects).status, "complete")

    def test_duplicate_unknown_noncanonical_and_repaired_manifest_fail(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = self.fixture.bundle
        duplicate = bundle.manifest.replace(b'{"audited_run_contract_sha256"', b'{"schema":"duplicate","audited_run_contract_sha256"', 1)
        value = json.loads(bundle.manifest)
        value["unknown"] = False
        unknown = canonical(value)
        value = json.loads(bundle.manifest)
        value["normalized_input_sha256"] = "0" * 64
        self_hash(value, "manifest_sha256")
        repaired = canonical(value)
        for raw in (duplicate, unknown, bundle.manifest + b" ", repaired):
            with self.subTest(size=len(raw)):
                self.assertEqual(replay_run_audit(raw, bundle.objects).status, "invalid")

    def test_repaired_event_order_still_fails_independent_derivation(self) -> None:
        from mathhead.run_audit import replay_run_audit

        value = json.loads(self.fixture.bundle.manifest)
        value["events"][3], value["events"][4] = value["events"][4], value["events"][3]
        previous = None
        for index, event in enumerate(value["events"]):
            event["event_order"] = index
            event["previous_event_sha256"] = previous
            self_hash(event, "event_sha256")
            previous = event["event_sha256"]
        self_hash(value, "manifest_sha256")
        self.assertEqual(
            replay_run_audit(canonical(value), self.fixture.bundle.objects).status,
            "invalid",
        )

    def test_repaired_logical_report_cannot_replace_fresh_projection(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = self.fixture.bundle
        manifest = json.loads(bundle.manifest)
        report = json.loads(bundle.logical_report)
        report["reason_code"] = "FORGED_REPORT"
        self_hash(report, "report_sha256")
        forged = canonical(report)
        old = bundle.logical_report_sha256
        new = sha(forged)
        for record in manifest["objects"]:
            if record["role_id"] == "logical_report":
                record["sha256"] = new
                record["byte_count"] = len(forged)
                self_hash(record, "record_sha256")
        manifest["logical_report_sha256"] = new
        self_hash(manifest, "manifest_sha256")
        objects = tuple(sorted((forged if sha(raw) == old else raw for raw in bundle.objects), key=sha))
        self.assertEqual(replay_run_audit(canonical(manifest), objects).status, "invalid")

    def test_wrong_exact_types_are_total_and_non_authoritative(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = self.fixture.bundle
        cases = (
            (bytearray(bundle.manifest), bundle.objects),
            (bundle.manifest, list(bundle.objects)),
            (bundle.manifest, (*bundle.objects[:-1], bytearray(bundle.objects[-1]))),
        )
        for manifest, objects in cases:
            result = replay_run_audit(manifest, objects)  # type: ignore[arg-type]
            self.assertIn(result.status, {"invalid", "exhausted"})
            self.assertFalse(result.mathematical_authority)
            self.assertIsNone(result.bundle_sha256)

    def test_values_are_closed_final_immutable_and_not_pickle_authority(self) -> None:
        from mathhead.run_audit import RunAuditBundle, RunAuditReplayResult, replay_run_audit

        bundle = self.fixture.bundle
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        with self.assertRaises(PermissionError):
            RunAuditBundle()
        with self.assertRaises(PermissionError):
            RunAuditReplayResult()
        with self.assertRaises(TypeError):
            class ForgedBundle(RunAuditBundle):
                pass
        for value in (bundle, replay):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(value)
            with self.assertRaises((AttributeError, TypeError)):
                value.mathematical_authority = True  # type: ignore[misc]

    def test_logical_report_is_byte_stable_across_fresh_runs(self) -> None:
        second = success_bundle()
        self.assertEqual(self.fixture.bundle.logical_report, second.bundle.logical_report)


if __name__ == "__main__":
    unittest.main()
