from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
from threading import Event
from typing import Any, Callable
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
    "run-audit-object-v2.schema.json",
    "run-audit-event-v2.schema.json",
    "run-audit-manifest-v3.schema.json",
    "run-logical-report-v2.schema.json",
    "run-audit-replay-result-v4.schema.json",
    "run-audit-worker-observation-v3.schema.json",
)


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def self_hash(value: dict[str, object], field: str) -> None:
    value[field] = None
    value[field] = sha(canonical(value))


def reidentify_portfolio_worker(bundle: Any) -> tuple[bytes, tuple[bytes, ...]]:
    manifest = json.loads(bundle.manifest)
    physical = {sha(raw): raw for raw in bundle.objects}
    records = {item["role_id"]: item for item in manifest["objects"]}
    portfolio_record = records["portfolio_result"]
    old_portfolio = portfolio_record["sha256"]
    portfolio = json.loads(physical.pop(old_portfolio))
    old_worker = portfolio["attempts"][0]["producer_worker_result_sha256"]
    replacement = "0" * 64
    portfolio["attempts"][0]["producer_worker_result_sha256"] = replacement
    self_hash(portfolio["attempts"][0], "attempt_sha256")
    self_hash(portfolio, "result_sha256")
    portfolio_raw = canonical(portfolio)
    new_portfolio = sha(portfolio_raw)
    physical[new_portfolio] = portfolio_raw

    report_record = records["logical_report"]
    old_report = report_record["sha256"]
    report = json.loads(physical.pop(old_report))
    report["attempts"][0]["producer_worker_result_sha256"] = replacement
    self_hash(report, "report_sha256")
    report_raw = canonical(report)
    new_report = sha(report_raw)
    physical[new_report] = report_raw
    for record, raw, identity in (
        (portfolio_record, portfolio_raw, new_portfolio),
        (report_record, report_raw, new_report),
    ):
        record["sha256"] = identity
        record["byte_count"] = len(raw)
        self_hash(record, "record_sha256")

    replacements = {
        old_worker: replacement,
        old_portfolio: new_portfolio,
        old_report: new_report,
    }
    previous = None
    for event in manifest["events"]:
        event["subject_sha256s"] = sorted(
            {replacements.get(item, item) for item in event["subject_sha256s"]}
        )
        event["previous_event_sha256"] = previous
        self_hash(event, "event_sha256")
        previous = event["event_sha256"]
    manifest["portfolio_result_sha256"] = new_portfolio
    manifest["logical_report_sha256"] = new_report
    self_hash(manifest, "manifest_sha256")
    return canonical(manifest), tuple(physical[item] for item in sorted(physical))


def changed_worker_observation(
    bundle: Any,
    mutate: Callable[[dict[str, Any]], None],
    *,
    repair_result: bool = True,
    repair_observation: bool = True,
) -> tuple[bytes, tuple[bytes, ...]]:
    manifest = json.loads(bundle.manifest)
    physical = {sha(raw): raw for raw in bundle.objects}
    record = next(
        item
        for item in manifest["objects"]
        if item["role_id"] == "producer_worker_observation_000000"
    )
    old = record["sha256"]
    observation = json.loads(physical.pop(old))
    mutate(observation)
    if repair_result:
        observation["result_identity_sha256"] = sha(canonical(observation["result"]))
    if repair_observation:
        self_hash(observation, "observation_sha256")
    raw = canonical(observation)
    identity = sha(raw)
    physical[identity] = raw
    record["sha256"] = identity
    record["byte_count"] = len(raw)
    self_hash(record, "record_sha256")
    self_hash(manifest, "manifest_sha256")
    return canonical(manifest), tuple(physical[item] for item in sorted(physical))


def changed_manifest_records(
    bundle: Any,
    mutate: Callable[[list[dict[str, Any]]], None],
) -> tuple[bytes, tuple[bytes, ...]]:
    manifest = json.loads(bundle.manifest)
    physical = {sha(raw): raw for raw in bundle.objects}
    mutate(manifest["objects"])
    for ordinal, record in enumerate(manifest["objects"]):
        record["ordinal"] = ordinal
        self_hash(record, "record_sha256")
    retained = {record["sha256"] for record in manifest["objects"]}
    physical = {identity: raw for identity, raw in physical.items() if identity in retained}
    self_hash(manifest, "manifest_sha256")
    return canonical(manifest), tuple(physical[item] for item in sorted(physical))


class RunAuditContractTests(unittest.TestCase):
    def test_accepted_contracts_and_schema_hashes_are_exact(self) -> None:
        from mathhead import run_audit

        self.assertEqual(
            run_audit.AUDITED_RUN_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-AUDITED-RUN-004.json").read_bytes()),
        )
        self.assertEqual(
            run_audit.REPLAY_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-RUN-AUDIT-REPLAY-004.json").read_bytes()),
        )
        for name in SCHEMAS:
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            schema = json.loads(raw)
            self.assertFalse(schema["additionalProperties"], name)
            self.assertEqual(
                run_audit.SCHEMA_SHA256S[schema["properties"]["schema"]["const"]], sha(raw)
            )

    def test_contract_bindings_are_implementation_bound(self) -> None:
        for contract in ("MH-C-AUDITED-RUN-004", "MH-C-RUN-AUDIT-REPLAY-004"):
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

    def test_emitted_values_validate_against_the_resolved_schema_graph(self) -> None:
        from mathhead.run_audit import replay_run_audit, run_audit_replay_result_bytes
        from tools.audit_schema_validation import validate_schema_instance

        schema_root = ROOT / "docs/contracts/schemas"
        schemas: dict[str, dict[str, Any]] = {}
        for name in SCHEMAS:
            path = schema_root / name
            value = json.loads(path.read_bytes())
            schemas[path.name] = value
        fixture = success_bundle()
        manifest = json.loads(fixture.bundle.manifest)
        physical = {sha(raw): raw for raw in fixture.bundle.objects}

        def validate(name: str, value: object) -> None:
            validate_schema_instance(schemas[name], value, schemas, label=name)

        validate("run-audit-manifest-v3.schema.json", manifest)
        for record in manifest["objects"]:
            validate("run-audit-object-v2.schema.json", record)
            if record["role"] == "worker_observation":
                validate(
                    "run-audit-worker-observation-v3.schema.json",
                    json.loads(physical[record["sha256"]]),
                )
        for event in manifest["events"]:
            validate("run-audit-event-v2.schema.json", event)
        validate(
            "run-logical-report-v2.schema.json",
            json.loads(fixture.bundle.logical_report),
        )
        replay = replay_run_audit(fixture.bundle.manifest, fixture.bundle.objects)
        validate(
            "run-audit-replay-result-v4.schema.json",
            json.loads(run_audit_replay_result_bytes(replay)),
        )


class RunAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = success_bundle()
        cls.fallback = fallback_bundle()
        cls.isolation_supported = (
            json.loads(cls.fixture.bundle.logical_report)["status"] == "succeeded"
        )

    def require_supported_isolation(self) -> bool:
        if self.isolation_supported:
            return True
        from mathhead.run_audit import replay_run_audit

        replay = replay_run_audit(
            self.fixture.bundle.manifest,
            self.fixture.bundle.objects,
        )
        self.assertEqual(replay.status, "complete")
        self.assertIn(replay.portfolio_status, {"unsupported", "invalid"})
        self.assertFalse(replay.mathematical_authority)
        return False

    def test_success_bundle_replays_complete_and_round_trips(self) -> None:
        from mathhead.run_audit import (
            parse_run_audit_replay_result,
            replay_run_audit,
            run_audit_replay_result_bytes,
        )

        if not self.require_supported_isolation():
            return
        bundle = self.fixture.bundle
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        self.assertEqual((replay.status, replay.reason_code), ("complete", "REPLAY_COMPLETE"))
        self.assertEqual(
            (replay.portfolio_status, replay.mathematical_verdict), ("succeeded", "proved")
        )
        self.assertGreaterEqual(replay.object_count, 18)
        self.assertGreaterEqual(replay.event_count, 10)
        raw = run_audit_replay_result_bytes(replay)
        self.assertEqual(
            parse_run_audit_replay_result(raw, bundle.manifest, bundle.objects),
            replay,
        )

    def test_fallback_is_exactly_ordered_and_replays_refutation(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if not self.require_supported_isolation():
            return
        bundle = self.fallback.bundle
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        report = json.loads(bundle.logical_report)
        manifest = json.loads(bundle.manifest)
        self.assertEqual((replay.status, replay.mathematical_verdict), ("complete", "refuted"))
        self.assertEqual([item["attempt_order"] for item in report["attempts"]], [0, 1])
        transitions = [item for item in manifest["events"] if item["kind"] == "transition_selected"]
        self.assertEqual([item["attempt_order"] for item in transitions], [0, 1])
        self.assertEqual([item["outcome"] for item in transitions], ["invalid_evidence", "success"])

    def test_terminal_evidence_paths_are_replayable(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if not self.require_supported_isolation():
            return
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

    def test_terminal_checker_paths_are_replayable(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if not self.require_supported_isolation():
            return
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

    def test_exceptional_portfolio_paths_are_replayable(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if not self.require_supported_isolation():
            return
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

    def test_prelaunch_invalid_path_is_a_complete_unchanged_ledger_audit(self) -> None:
        from mathhead.run_audit import execute_audited_run, replay_run_audit

        fixture = self.fixture.source
        _planning, _route, _descriptors, artifacts = fixture.base.planning_inputs(
            (fixture.descriptor,),
            availability_changes={"allowed_effects": ("process",)},
        )
        bundle = execute_audited_run(
            self.fixture.planning_request,
            self.fixture.route_result,
            fixture.request,
            fixture.plan_bytes,
            fixture.parent,
            (fixture.descriptor,),
            (fixture.binding,),
            artifacts,
            (),
            str(ROOT),
        )
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        manifest = json.loads(bundle.manifest)
        report = json.loads(bundle.logical_report)
        self.assertEqual(
            (replay.status, replay.portfolio_status, report["status"]),
            ("complete", "invalid", "invalid"),
        )
        self.assertEqual(
            manifest["initial_parent_budget_sha256"],
            manifest["final_parent_budget_sha256"],
        )
        self.assertEqual(report["attempts"], [])
        self.assertFalse(
            {
                "worker_observation",
                "validated_evidence",
                "checker_certificate",
                "checker_decision",
            }
            & {item["role"] for item in manifest["objects"]}
        )

    def test_unavailable_isolation_still_has_a_complete_non_authoritative_audit(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if self.isolation_supported:
            self.assertEqual(
                json.loads(self.fixture.bundle.logical_report)["status"],
                "succeeded",
            )
            return
        replay = replay_run_audit(
            self.fixture.bundle.manifest,
            self.fixture.bundle.objects,
        )
        self.assertEqual(replay.status, "complete")
        self.assertIn(replay.portfolio_status, {"unsupported", "invalid"})
        self.assertFalse(replay.mathematical_authority)

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
        if not self.require_supported_isolation():
            return
        manifest = json.loads(self.fixture.bundle.manifest)
        report = json.loads(self.fixture.bundle.logical_report)
        roles = {item["role_id"]: item for item in manifest["objects"]}
        self.assertEqual(roles["normalized_input"]["sha256"], manifest["normalized_input_sha256"])
        self.assertIn("planning_result", roles)
        self.assertIn("initial_parent_budget", roles)
        self.assertIn("final_parent_budget", roles)
        self.assertTrue(any(name.startswith("checker_decision_") for name in roles))
        self.assertEqual(len(report["plugins"]), 1)
        self.assertEqual(
            report["plugins"][0]["strategy_sha256"], report["selected_strategy_sha256"]
        )
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
        duplicate = bundle.manifest.replace(
            b'{"audited_run_contract_sha256"',
            b'{"schema":"duplicate","audited_run_contract_sha256"',
            1,
        )
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

    def test_repaired_semantic_record_order_is_rejected(self) -> None:
        from mathhead.run_audit import replay_run_audit

        if not self.require_supported_isolation():
            return

        def swap_observations(records: list[dict[str, Any]]) -> None:
            producer = next(
                index
                for index, item in enumerate(records)
                if item["role_id"] == "producer_worker_observation_000000"
            )
            checker = next(
                index
                for index, item in enumerate(records)
                if item["role_id"] == "checker_worker_observation_000000"
            )
            records[producer], records[checker] = records[checker], records[producer]

        manifest, objects = changed_manifest_records(
            self.fixture.bundle,
            swap_observations,
        )
        replay = replay_run_audit(manifest, objects)
        self.assertEqual((replay.status, replay.reason_code), ("invalid", "REPLAY_INVALID"))

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
        objects = tuple(
            sorted((forged if sha(raw) == old else raw for raw in bundle.objects), key=sha)
        )
        self.assertEqual(replay_run_audit(canonical(manifest), objects).status, "invalid")

    def test_reidentified_worker_is_rejected_after_outer_reidentification(self) -> None:
        from mathhead.run_audit import replay_run_audit

        manifest, objects = reidentify_portfolio_worker(self.fixture.bundle)
        self.assertEqual(replay_run_audit(manifest, objects).status, "invalid")

    def test_worker_observation_field_relations_fail_independently(self) -> None:
        from mathhead.run_audit import replay_run_audit

        def artifact(value: dict[str, Any]) -> dict[str, Any]:
            return value["result"]["artifacts"][0]

        def artifact_role(value: dict[str, Any]) -> None:
            item = artifact(value)
            item["role"] = "stderr"
            self_hash(item, "artifact_sha256")

        def artifact_conservation(value: dict[str, Any]) -> None:
            item = artifact(value)
            item["original_bytes"] += 1
            self_hash(item, "artifact_sha256")

        def artifact_retained_identity(value: dict[str, Any]) -> None:
            item = artifact(value)
            item["retained_sha256"] = None
            self_hash(item, "artifact_sha256")

        def artifact_self_identity(value: dict[str, Any]) -> None:
            artifact(value)["artifact_sha256"] = "0" * 64

        cases = (
            ("attempt", lambda value: value.__setitem__("attempt_order", 1), True, True),
            ("phase", lambda value: value.__setitem__("phase", "checker"), True, True),
            ("request", lambda value: value.__setitem__("request_sha256", "0" * 64), True, True),
            ("status", lambda value: value["result"].__setitem__("status", "failed"), True, True),
            (
                "reason",
                lambda value: value["result"].__setitem__("reason_code", "CHANGED"),
                True,
                True,
            ),
            (
                "plan",
                lambda value: value["result"].__setitem__("planning_result_sha256", "0" * 64),
                True,
                True,
            ),
            (
                "strategy",
                lambda value: value["result"].__setitem__("strategy_sha256", "0" * 64),
                True,
                True,
            ),
            ("capability", lambda value: value["result"].__setitem__("capability", {}), True, True),
            (
                "diagnostics",
                lambda value: value["result"].__setitem__("diagnostics", ["changed"]),
                True,
                True,
            ),
            (
                "empty-artifacts",
                lambda value: value["result"].__setitem__("artifacts", []),
                True,
                True,
            ),
            ("artifact-role", artifact_role, True, True),
            ("artifact-conservation", artifact_conservation, True, True),
            ("artifact-retained-identity", artifact_retained_identity, True, True),
            ("artifact-self-identity", artifact_self_identity, True, True),
            (
                "result-identity",
                lambda value: value["result"].__setitem__("status", "failed"),
                False,
                True,
            ),
            (
                "observation-identity",
                lambda value: value.__setitem__("request_sha256", "0" * 64),
                True,
                False,
            ),
            ("unknown-field", lambda value: value.__setitem__("unknown", False), True, True),
        )
        for label, mutate, repair_result, repair_observation in cases:
            with self.subTest(label=label):
                manifest, objects = changed_worker_observation(
                    self.fixture.bundle,
                    mutate,
                    repair_result=repair_result,
                    repair_observation=repair_observation,
                )
                self.assertEqual(replay_run_audit(manifest, objects).status, "invalid")

    def test_worker_observation_inventory_and_ledger_are_exact(self) -> None:
        from mathhead.run_audit import replay_run_audit

        def remove_producer(records: list[dict[str, Any]]) -> None:
            records[:] = [
                item for item in records if item["role_id"] != "producer_worker_observation_000000"
            ]

        def remove_first_ledger(records: list[dict[str, Any]]) -> None:
            records[:] = [
                item for item in records if item["role_id"] != "reconciled_parent_budget_000000"
            ]

        def add_surplus(records: list[dict[str, Any]]) -> None:
            source = next(
                item for item in records if item["role_id"] == "producer_worker_observation_000000"
            )
            extra = copy.deepcopy(source)
            extra["role_id"] = "producer_worker_observation_999999"
            records.append(extra)

        for label, mutate in (
            ("missing-observation", remove_producer),
            ("missing-ledger", remove_first_ledger),
            ("surplus-observation", add_surplus),
        ):
            with self.subTest(label=label):
                manifest, objects = changed_manifest_records(
                    self.fixture.bundle,
                    mutate,
                )
                self.assertEqual(replay_run_audit(manifest, objects).status, "invalid")

    def test_unvalidated_worker_output_has_no_canonical_content_digest(self) -> None:
        from mathhead.run_audit import replay_run_audit

        bundle = single_bundle(malformed_evidence=True).bundle
        manifest = json.loads(bundle.manifest)
        physical = {sha(raw): raw for raw in bundle.objects}
        producer = next(
            item
            for item in manifest["objects"]
            if item["role_id"] == "producer_worker_observation_000000"
        )
        observation = json.loads(physical[producer["sha256"]])
        self.assertEqual(observation["result"]["artifacts"], [])
        self.assertEqual(
            replay_run_audit(bundle.manifest, bundle.objects).status,
            "complete",
        )

    def test_audit_codec_and_observation_helpers_reject_invalid_relations(self) -> None:
        from mathhead import run_audit

        codec_cases = (
            lambda: run_audit._walk(1, nodes=[run_audit.MAX_JSON_NODES]),
            lambda: run_audit._walk(run_audit.INTEGER_MAXIMUM + 1),
            lambda: run_audit._walk("x", nodes=[run_audit.MAX_JSON_NODES]),
            lambda: run_audit._walk("nul\x00"),
            lambda: run_audit._walk({1: False}),
            lambda: run_audit._walk(object()),
            lambda: run_audit._canonical({"schema": "mathhead.test.v1"}, maximum=1),
            lambda: run_audit._parse(bytearray(b"{}\n"), "value"),
            lambda: run_audit._parse(b"", "value"),
            lambda: run_audit._parse(b"\xff", "value"),
            lambda: run_audit._parse(b"[]\n", "value"),
            lambda: run_audit._parse(b"{}\n ", "value"),
            lambda: run_audit._keys({}, {"required"}, "value"),
            lambda: run_audit._digest(None, "value"),
            lambda: run_audit._identifier("Changed", "value"),
            lambda: run_audit._namespaced("changed", "value"),
            lambda: run_audit._quantity(True, "value"),
            lambda: run_audit._reason("changed", "value"),
            lambda: run_audit._record(0, "unknown", "value", b"{}\n"),
        )
        for index, operation in enumerate(codec_cases):
            with self.subTest(index=index), self.assertRaises(ValueError):
                operation()

        manifest = json.loads(self.fixture.bundle.manifest)
        physical = {sha(raw): raw for raw in self.fixture.bundle.objects}
        record = next(
            item
            for item in manifest["objects"]
            if item["role_id"] == "producer_worker_observation_000000"
        )
        observation = json.loads(physical[record["sha256"]])
        preimage = canonical(observation["result"])
        with self.assertRaises(ValueError):
            run_audit._worker_observation(
                attempt_order=0,
                phase="changed",
                request_sha256=observation["request_sha256"],
                result_identity_sha256=observation["result_identity_sha256"],
                result_preimage=preimage,
            )
        with self.assertRaises(ValueError):
            run_audit._worker_observation(
                attempt_order=0,
                phase="producer",
                request_sha256=observation["request_sha256"],
                result_identity_sha256="0" * 64,
                result_preimage=preimage,
            )
        with self.assertRaises(ValueError):
            run_audit._observation_artifact_link({"artifacts": []}, b"retained", "value")
        with self.assertRaises(ValueError):
            run_audit._observation_artifact_link(
                {
                    "artifacts": [
                        {
                            "role": "stdout",
                            "retained_bytes": 1,
                            "retained_sha256": "0" * 64,
                        }
                    ]
                },
                b"retained",
                "value",
            )
        with self.assertRaises(ValueError):
            run_audit._event(
                [],
                kind="changed",
                attempt_order=None,
                strategy_sha256=None,
                phase="run",
                outcome="opened",
                reason_code="CHANGED",
                subjects=(),
            )
        with self.assertRaises(ValueError):
            run_audit._event(
                [],
                kind="run_opened",
                attempt_order=None,
                strategy_sha256=None,
                phase="run",
                outcome="opened",
                reason_code="CHANGED",
                subjects=("changed",),
            )

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
