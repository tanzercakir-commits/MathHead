from __future__ import annotations

import copy
from dataclasses import fields, replace
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
from threading import Event
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.execution_disposition.fixtures import (  # noqa: E402
    CONTRACT_ID,
    CONTRACT_PATH,
    CONTRACT_SHA256,
    EarlyFixture,
    PlannedFixture,
    anchored_budget,
    canonical,
    changed_request,
    repair_request,
    self_hash,
    sha,
    strip_anchor,
)


SCHEMA_NAMES = (
    "cancellation-intent-v1.schema.json",
    "execution-disposition-request-v1.schema.json",
    "execution-disposition-classification-v1.schema.json",
    "execution-disposition-diagnostic-v1.schema.json",
    "execution-disposition-result-v1.schema.json",
)


def execute(fixture: EarlyFixture | PlannedFixture):
    from mathhead.execution_disposition import execute_with_disposition

    return execute_with_disposition(*fixture.inputs.call_arguments)


def result_mapping(bundle: object) -> dict[str, object]:
    from mathhead.execution_disposition import execution_disposition_result_bytes

    return json.loads(execution_disposition_result_bytes(bundle.result))  # type: ignore[attr-defined]


def portfolio_pairs() -> set[tuple[str, str]]:
    schema = json.loads(
        (ROOT / "docs/contracts/schemas/execution-disposition-result-v1.schema.json").read_bytes()
    )
    rows: set[tuple[str, str]] = set()
    for branch in schema["$defs"]["portfolio_pair"]["oneOf"]:
        properties = branch["properties"]
        statuses = properties["portfolio_status"].get(
            "enum", [properties["portfolio_status"].get("const")]
        )
        reasons = properties["portfolio_reason_code"].get(
            "enum", [properties["portfolio_reason_code"].get("const")]
        )
        rows.update((status, reason) for status in statuses for reason in reasons)
    return rows


class ExecutionDispositionContractTests(unittest.TestCase):
    def test_contract_and_five_schema_identities_are_compiled(self) -> None:
        from mathhead import execution_disposition as disposition

        self.assertEqual(disposition.CONTRACT_ID, CONTRACT_ID)
        self.assertEqual(disposition.CONTRACT_SHA256, CONTRACT_SHA256)
        self.assertEqual(CONTRACT_SHA256, sha(CONTRACT_PATH.read_bytes()))
        observed: dict[str, str] = {}
        for name in SCHEMA_NAMES:
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            value = json.loads(raw)
            self.assertFalse(value["additionalProperties"], name)
            observed[value["properties"]["schema"]["const"]] = sha(raw)
        self.assertEqual(disposition.SCHEMA_SHA256S, observed)

    def test_public_request_codec_is_strict_and_content_addressed(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture(origin_source="user")
        request = disposition.parse_execution_disposition_request(fixture.inputs.request)
        self.assertEqual(
            disposition.execution_disposition_request_bytes(request),
            fixture.inputs.request,
        )
        self.assertEqual(request.request_sha256, fixture.inputs.request_value["request_sha256"])
        self.assertEqual(
            request.cancellation_intent.intent_sha256,
            fixture.inputs.request_value["cancellation_intent"]["intent_sha256"],
        )
        malformed = (
            bytearray(fixture.inputs.request),
            fixture.inputs.request.rstrip(b"\n"),
            b"\xff",
            b"[]\n",
            fixture.inputs.request.replace(
                b'{"artifact_bindings"',
                b'{"schema":"duplicate","artifact_bindings"',
                1,
            ),
        )
        for raw in malformed:
            with self.subTest(raw=repr(raw)[:80]):
                with self.assertRaises(disposition.ExecutionDispositionValidationError):
                    disposition.parse_execution_disposition_request(raw)  # type: ignore[arg-type]

        wrong_contract = changed_request(
            fixture.inputs.request,
            lambda value: value.update(contract_sha256="f" * 64),
        )
        wrong_policy = changed_request(
            fixture.inputs.request,
            lambda value: value["cancellation_intent"].update(policy_contract_sha256="f" * 64),
        )
        unknown = changed_request(
            fixture.inputs.request,
            lambda value: value.update(unknown="closed"),
        )
        for label, raw in (
            ("contract", wrong_contract),
            ("intent_policy", wrong_policy),
            ("unknown", unknown),
        ):
            with self.subTest(repaired_forgery=label):
                with self.assertRaises(disposition.ExecutionDispositionValidationError):
                    disposition.parse_execution_disposition_request(raw)

    def test_public_values_are_final_immutable_and_not_pickle_authority(self) -> None:
        from mathhead import execution_disposition as disposition

        invalid = EarlyFixture()
        bad_inputs = replace(invalid.inputs, request=b'{"malformed":\n')
        invalid.inputs = bad_inputs
        invalid_bundle = execute(invalid)
        armed_request = disposition.parse_execution_disposition_request(
            PlannedFixture(origin_source="parent").inputs.request
        )
        values = (
            armed_request.cancellation_intent,
            armed_request,
            invalid_bundle.result.classification,
            invalid_bundle.result.diagnostics[0],
            invalid_bundle.result,
            invalid_bundle,
        )
        classes = (
            disposition.CancellationIntent,
            disposition.ExecutionDispositionRequest,
            disposition.ExecutionDispositionClassification,
            disposition.ExecutionDispositionDiagnostic,
            disposition.ExecutionDispositionResult,
            disposition.ExecutionDispositionBundle,
        )
        for value_class in classes:
            with self.subTest(constructor=value_class.__name__):
                with self.assertRaises(PermissionError):
                    value_class()
                with self.assertRaises(TypeError):
                    type(f"Forged{value_class.__name__}", (value_class,), {})
        for value in values:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises((AttributeError, TypeError)):
                    value.mathematical_authority = True
                with self.assertRaises((TypeError, pickle.PicklingError)):
                    pickle.dumps(value)

        forged = object.__new__(disposition.ExecutionDispositionResult)
        with self.assertRaises(
            (disposition.ExecutionDispositionValidationError, AttributeError, TypeError)
        ):
            disposition.execution_disposition_result_bytes(forged)

    def test_result_codec_rejects_repaired_structural_and_identity_forgery(self) -> None:
        from mathhead import execution_disposition as disposition

        bundle = execute(EarlyFixture("unsupported_input"))
        raw = disposition.execution_disposition_result_bytes(bundle.result)
        parsed = disposition.parse_execution_disposition_result(raw)
        self.assertEqual(parsed, bundle.result)
        self.assertEqual(disposition.execution_disposition_result_bytes(parsed), raw)

        stale = json.loads(raw)
        stale["result_sha256"] = "f" * 64
        wrong_contract = json.loads(raw)
        wrong_contract["contract_sha256"] = "f" * 64
        self_hash(wrong_contract, "result_sha256")
        crossed = json.loads(raw)
        crossed["classification"]["cause"] = "user_cancellation"
        self_hash(crossed["classification"], "classification_sha256")
        self_hash(crossed, "result_sha256")
        for label, value in (
            ("stale_result_hash", stale),
            ("wrong_contract_repaired", wrong_contract),
            ("crossed_classification_repaired", crossed),
        ):
            with self.subTest(forgery=label):
                with self.assertRaises(disposition.ExecutionDispositionValidationError):
                    disposition.parse_execution_disposition_result(canonical(value))

    def test_public_codecs_and_validators_never_serialize_fatal_control(self) -> None:
        from mathhead import execution_disposition as disposition

        armed_request = disposition.parse_execution_disposition_request(
            PlannedFixture(origin_source="user").inputs.request
        )
        self.assertIsNotNone(armed_request.cancellation_intent)
        invalid = EarlyFixture()
        invalid.inputs = replace(invalid.inputs, request=b'{"malformed":\n')
        invalid_bundle = execute(invalid)
        values = (
            (
                disposition.validate_cancellation_intent,
                armed_request.cancellation_intent,
                "_intent_mapping",
            ),
            (
                disposition.validate_execution_disposition_request,
                armed_request,
                "_request_mapping",
            ),
            (
                disposition.validate_execution_disposition_classification,
                invalid_bundle.result.classification,
                "_classification_mapping",
            ),
            (
                disposition.validate_execution_disposition_diagnostic,
                invalid_bundle.result.diagnostics[0],
                "_diagnostic_mapping",
            ),
            (
                disposition.validate_execution_disposition_result,
                invalid_bundle.result,
                "_result_mapping",
            ),
        )
        parsers = (
            disposition.parse_cancellation_intent,
            disposition.parse_execution_disposition_request,
            disposition.parse_execution_disposition_classification,
            disposition.parse_execution_disposition_diagnostic,
            disposition.parse_execution_disposition_result,
        )
        fatal_types = (MemoryError, KeyboardInterrupt, SystemExit)
        for parser in parsers:
            for fatal_type in fatal_types:
                with self.subTest(parser=parser.__name__, fatal=fatal_type.__name__), mock.patch.object(
                    disposition, "_parse", side_effect=fatal_type()
                ):
                    with self.assertRaises(fatal_type):
                        parser(b"{}\n")
        for validator, value, dependency in values:
            for fatal_type in fatal_types:
                with self.subTest(
                    validator=validator.__name__, fatal=fatal_type.__name__
                ), mock.patch.object(disposition, dependency, side_effect=fatal_type()):
                    with self.assertRaises(fatal_type):
                        validator(value)


class EarlyAndPrelaunchTests(unittest.TestCase):
    def test_three_governed_early_outcomes_never_launch(self) -> None:
        from mathhead import execution_disposition as disposition

        cases = (
            (
                "unsupported_environment",
                "unsupported_execution_environment",
                "routing",
                "unsupported",
                "unsupported",
            ),
            (
                "unsupported_input",
                "unsupported_input",
                "routing",
                "unsupported",
                "unsupported",
            ),
            (
                "planning_exhausted",
                "budget_exhaustion",
                "planning",
                "routed",
                "exhausted",
            ),
        )
        for kind, cause, phase, route_status, planning_status in cases:
            with self.subTest(kind=kind):
                fixture = EarlyFixture(kind)
                with (
                    mock.patch.object(disposition, "execute_audited_run") as audited,
                    mock.patch.object(disposition, "replay_run_audit") as replay,
                ):
                    bundle = execute(fixture)
                audited.assert_not_called()
                replay.assert_not_called()
                disposition.validate_execution_disposition_bundle(bundle)
                result = bundle.result
                self.assertEqual(result.classification.cause, cause)
                self.assertEqual(result.classification.phase, phase)
                self.assertEqual(result.route_status, route_status)
                self.assertEqual(result.planning_status, planning_status)
                self.assertEqual(result.execution_state, "not_started")
                self.assertEqual(result.portfolio_relation, "not_available")
                self.assertEqual(result.diagnostics, ())
                self.assertFalse(result.mathematical_authority)
                self.assertEqual(result.authority_ceiling, "none")
                self.assertEqual(
                    bundle.request.request_sha256,
                    result.disposition_request_sha256,
                )
                self.assertIsNone(bundle.audit)
                self.assertIsNone(bundle.replay)

    def test_malformed_raw_request_has_the_empty_preflight_profile(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = EarlyFixture()
        fixture.inputs = replace(fixture.inputs, request=b'{"malformed":\n')
        with mock.patch.object(disposition, "execute_audited_run") as audited:
            bundle = execute(fixture)
        audited.assert_not_called()
        result = bundle.result
        self.assertIsNone(bundle.request)
        self.assertEqual(result.classification.cause, "invalid_request")
        self.assertEqual(result.classification.phase, "request")
        self.assertEqual([item.code for item in result.diagnostics], ["REQUEST_INVALID"])
        for name in (
            "disposition_request_sha256",
            "invocation_sha256",
            "cancellation_armed",
            "cancellation_intent_sha256",
            "base_parent_budget_sha256",
            "anchored_parent_budget_sha256",
            "planning_result_sha256",
            "portfolio_request_sha256",
            "audit_manifest_sha256",
            "logical_report_sha256",
            "replay_result_sha256",
            "portfolio_result_sha256",
            "execution_provenance_sha256",
            "route_status",
            "planning_status",
            "portfolio_status",
            "replay_status",
        ):
            self.assertIsNone(getattr(result, name), name)

    def test_request_binding_artifact_and_execution_failures_stop_at_reached_milestone(
        self,
    ) -> None:
        from mathhead import execution_disposition as disposition

        planned = PlannedFixture()
        mutations = []

        changed_artifacts = list(planned.inputs.artifacts)
        role, raw = changed_artifacts[0]
        changed_artifacts[0] = (role, raw + b"x")
        mutations.append(
            (
                "ARTIFACT_INPUT_INVALID",
                replace(planned.inputs, artifacts=tuple(changed_artifacts)),
                False,
            )
        )
        mutations.append(
            (
                "BINDING_INPUT_INVALID",
                replace(
                    planned.inputs,
                    bindings=(planned.inputs.bindings[0] + b"x",),
                ),
                False,
            )
        )
        mutations.append(
            (
                "EXECUTION_INPUT_INVALID",
                replace(planned.inputs, workspace_root=None),
                True,
            )
        )
        for code, inputs, planned_reached in mutations:
            with self.subTest(code=code):
                fixture = copy.copy(planned)
                fixture.inputs = inputs
                with mock.patch.object(disposition, "execute_audited_run") as audited:
                    bundle = execute(fixture)
                audited.assert_not_called()
                self.assertEqual(bundle.result.classification.cause, "invalid_request")
                self.assertEqual([item.code for item in bundle.result.diagnostics], [code])
                self.assertIsNotNone(bundle.result.disposition_request_sha256)
                if planned_reached:
                    self.assertEqual(bundle.result.route_status, "routed")
                    self.assertEqual(bundle.result.planning_status, "planned")
                self.assertIsNone(bundle.result.audit_manifest_sha256)
                self.assertIsNone(bundle.result.portfolio_result_sha256)

    def test_reserved_extension_collision_retains_only_the_validated_base_milestone(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture()
        base = json.loads(fixture.inputs.base_parent_budget)
        base["extensions"]["org.mathhead.execution-disposition"] = {
            "disposition_request_sha256": "0" * 64
        }
        collided = canonical(base)
        request_value = json.loads(fixture.inputs.request)
        request_value["base_parent_budget_sha256"] = sha(collided)
        request = repair_request(request_value)
        fixture.inputs = replace(
            fixture.inputs,
            request=request,
            request_value=request_value,
            base_parent_budget=collided,
        )
        with mock.patch.object(disposition, "execute_audited_run") as audited:
            bundle = execute(fixture)
        audited.assert_not_called()
        result = bundle.result
        self.assertEqual(
            [item.code for item in result.diagnostics], ["RESERVED_EXTENSION_COLLISION"]
        )
        self.assertEqual(result.base_parent_budget_sha256, sha(collided))
        self.assertIsNone(result.anchored_parent_budget_sha256)
        self.assertIsNone(result.portfolio_request_sha256)

    def test_exact_builtin_type_boundaries_reject_coercion(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = EarlyFixture()
        cases = (
            replace(fixture.inputs, request=bytearray(fixture.inputs.request)),
            replace(fixture.inputs, descriptors=list(fixture.inputs.descriptors)),
            replace(fixture.inputs, artifacts=list(fixture.inputs.artifacts)),
            replace(fixture.inputs, workspace_root=Path(".")),
        )
        for inputs in cases:
            with self.subTest(
                field_types=tuple(type(item).__name__ for item in inputs.call_arguments)
            ):
                with self.assertRaises(disposition.ExecutionDispositionValidationError):
                    disposition.execute_with_disposition(*inputs.call_arguments)

    def test_intent_and_event_pairing_is_exact_and_effect_free(self) -> None:
        from mathhead import execution_disposition as disposition

        armed = PlannedFixture(origin_source="user")
        unarmed = PlannedFixture()
        cases = (
            replace(armed.inputs, cancel_event=None),
            replace(unarmed.inputs, cancel_event=Event()),
        )
        for inputs in cases:
            fixture = copy.copy(armed)
            fixture.inputs = inputs
            with mock.patch.object(disposition, "execute_audited_run") as audited:
                bundle = execute(fixture)
            audited.assert_not_called()
            self.assertEqual(bundle.result.classification.cause, "invalid_request")
            self.assertEqual(
                [item.code for item in bundle.result.diagnostics],
                ["INTENT_EVENT_MISMATCH"],
            )


class PlannedExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.planned = PlannedFixture()
        cls.audit = cls.planned.audited_bundle()

    def mocked_execution(self, fixture: PlannedFixture, audit: object):
        from mathhead import execution_disposition as disposition
        from mathhead.run_audit import replay_run_audit

        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=audit) as audited,
            mock.patch.object(disposition, "replay_run_audit", wraps=replay_run_audit) as replay,
        ):
            bundle = execute(fixture)
        return bundle, audited, replay

    def test_anchor_roundtrip_and_sole_audit_plus_fresh_replay_calls(self) -> None:
        from mathhead import execution_disposition as disposition

        bundle, audited, replay = self.mocked_execution(self.planned, self.audit)
        audited.assert_called_once()
        replay.assert_called_once_with(self.audit.manifest, self.audit.objects)
        args = audited.call_args.args
        self.assertEqual(args[0], self.planned.inputs.planning_request)
        self.assertEqual(args[1], self.planned.inputs.route_result)
        self.assertEqual(args[2], self.planned.portfolio_request())
        self.assertEqual(args[3], self.planned.inputs.planning_result)
        self.assertEqual(args[4], self.planned.expected_anchor)
        self.assertEqual(args[5], self.planned.inputs.descriptors)
        self.assertEqual(args[6], self.planned.inputs.bindings)
        self.assertEqual(args[7], tuple(raw for _, raw in self.planned.inputs.artifacts))
        self.assertEqual(args[8], self.planned.inputs.executable_paths)
        self.assertEqual(args[9], self.planned.inputs.workspace_root)
        self.assertIs(args[10], self.planned.inputs.cancel_event)
        self.assertEqual(strip_anchor(args[4]), self.planned.inputs.base_parent_budget)
        self.assertEqual(
            args[4],
            anchored_budget(
                self.planned.inputs.base_parent_budget,
                self.planned.inputs.request_value["request_sha256"],
            ),
        )
        self.assertEqual(bundle.result.classification.cause, "checked_proof")
        self.assertEqual(bundle.result.execution_state, "replayed_complete")
        self.assertEqual(bundle.result.portfolio_relation, "exact")
        self.assertIs(bundle.audit, self.audit)
        self.assertIsNotNone(bundle.replay)
        disposition.validate_execution_disposition_bundle(bundle)

    def test_replay_failure_and_replayed_cross_input_relation_are_internal(self) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.run_audit import replay_run_audit

        invalid_replay = replay_run_audit(b"{}\n", ())
        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=self.audit),
            mock.patch.object(disposition, "replay_run_audit", return_value=invalid_replay),
        ):
            stale_replay = execute(self.planned)
        self.assertEqual(stale_replay.result.classification.cause, "internal_error")
        self.assertEqual(stale_replay.result.execution_state, "attempted_no_bundle")
        self.assertEqual(
            [item.code for item in stale_replay.result.diagnostics],
            ["AUDITED_EXECUTION_INVALID"],
        )
        self.assertIsNone(stale_replay.audit)
        self.assertIsNone(stale_replay.replay)

        current_invalid_replay = object.__new__(type(invalid_replay))
        for value_field in fields(type(invalid_replay)):
            object.__setattr__(
                current_invalid_replay,
                value_field.name,
                getattr(invalid_replay, value_field.name),
            )
        object.__setattr__(current_invalid_replay, "_input_manifest", self.audit.manifest)
        object.__setattr__(current_invalid_replay, "_input_objects", self.audit.objects)
        object.__setattr__(current_invalid_replay, "object_count", len(self.audit.objects))
        replay_mapping = {
            value_field.name: getattr(current_invalid_replay, value_field.name)
            for value_field in fields(type(current_invalid_replay))
            if not value_field.name.startswith("_")
        }
        self_hash(replay_mapping, "replay_result_sha256")
        object.__setattr__(
            current_invalid_replay,
            "replay_result_sha256",
            replay_mapping["replay_result_sha256"],
        )
        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=self.audit),
            mock.patch.object(
                disposition,
                "replay_run_audit",
                return_value=current_invalid_replay,
            ),
        ):
            replay_failed = execute(self.planned)
        self.assertEqual(replay_failed.result.classification.cause, "internal_error")
        self.assertEqual(replay_failed.result.execution_state, "bundle_replay_failed")
        self.assertEqual(
            [item.code for item in replay_failed.result.diagnostics],
            ["AUDIT_REPLAY_INVALID"],
        )
        self.assertEqual(
            replay_failed.result.audit_manifest_sha256,
            self.audit.manifest_sha256,
        )
        self.assertEqual(
            replay_failed.result.replay_result_sha256,
            current_invalid_replay.replay_result_sha256,
        )
        self.assertEqual(replay_failed.result.replay_status, "invalid")
        self.assertEqual(replay_failed.result.replay_reason_code, "REPLAY_INVALID")
        self.assertIsNone(replay_failed.audit)
        self.assertIsNone(replay_failed.replay)
        disposition.validate_execution_disposition_bundle(replay_failed)
        replay_failed_raw = disposition.execution_disposition_result_bytes(
            replay_failed.result
        )
        detached = disposition.parse_execution_disposition_result(
            replay_failed_raw,
            request_input=self.planned.inputs.request,
            request=replay_failed.request,
            anchored_parent_budget=disposition.execution_disposition_anchored_budget_bytes(
                replay_failed
            ),
            portfolio_request=disposition.execution_disposition_portfolio_request_bytes(
                replay_failed
            ),
        )
        self.assertEqual(
            disposition.execution_disposition_result_bytes(detached), replay_failed_raw
        )
        with self.assertRaises(disposition.ExecutionDispositionValidationError):
            disposition.parse_execution_disposition_result(
                replay_failed_raw,
                request_input=self.planned.inputs.request,
                request=replay_failed.request,
                anchored_parent_budget=(
                    disposition.execution_disposition_anchored_budget_bytes(replay_failed)
                ),
                portfolio_request=(
                    disposition.execution_disposition_portfolio_request_bytes(replay_failed)
                ),
                audit=self.audit,
                replay=current_invalid_replay,
            )

        current_exhausted_replay = object.__new__(type(current_invalid_replay))
        for value_field in fields(type(current_invalid_replay)):
            object.__setattr__(
                current_exhausted_replay,
                value_field.name,
                getattr(current_invalid_replay, value_field.name),
            )
        object.__setattr__(current_exhausted_replay, "status", "exhausted")
        object.__setattr__(
            current_exhausted_replay,
            "reason_code",
            "REPLAY_BUDGET_EXHAUSTED",
        )
        exhausted_mapping = {
            value_field.name: getattr(current_exhausted_replay, value_field.name)
            for value_field in fields(type(current_exhausted_replay))
            if not value_field.name.startswith("_")
        }
        self_hash(exhausted_mapping, "replay_result_sha256")
        object.__setattr__(
            current_exhausted_replay,
            "replay_result_sha256",
            exhausted_mapping["replay_result_sha256"],
        )
        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=self.audit),
            mock.patch.object(
                disposition,
                "replay_run_audit",
                return_value=current_exhausted_replay,
            ),
        ):
            replay_exhausted = execute(self.planned)
        self.assertEqual(replay_exhausted.result.execution_state, "bundle_replay_failed")
        self.assertEqual(replay_exhausted.result.replay_status, "exhausted")
        self.assertEqual(
            [item.code for item in replay_exhausted.result.diagnostics],
            ["AUDIT_REPLAY_EXHAUSTED"],
        )
        self.assertIsNone(replay_exhausted.audit)
        self.assertIsNone(replay_exhausted.replay)

        changed = copy.copy(self.planned)
        changed_request_raw = changed_request(
            changed.inputs.request,
            lambda value: value.update(invocation_id="invocation_cross_input"),
        )
        changed.inputs = replace(
            changed.inputs,
            request=changed_request_raw,
            request_value=json.loads(changed_request_raw),
        )
        related, _audited, _replay = self.mocked_execution(changed, self.audit)
        self.assertEqual(related.result.classification.cause, "internal_error")
        self.assertEqual(related.result.portfolio_relation, "invalid")
        self.assertEqual(
            [item.code for item in related.result.diagnostics],
            ["AUDIT_RELATION_INVALID"],
        )

    def test_special_checker_discriminators_remain_distinct(self) -> None:
        cases = (
            (
                "unsupported",
                "verifier_refusal",
                "certificate_unsupported",
            ),
            (
                "inconclusive",
                "inconclusive_execution",
                "certificate_inconclusive",
            ),
        )
        for certificate_status, cause, outcome_kind in cases:
            with self.subTest(certificate_status=certificate_status):
                fixture = PlannedFixture(certificate_status=certificate_status)
                audit = fixture.audited_bundle()
                bundle, _audited, _replay = self.mocked_execution(fixture, audit)
                self.assertEqual(bundle.result.classification.cause, cause)
                self.assertEqual(bundle.result.portfolio_outcome_kind, outcome_kind)
                self.assertEqual(bundle.result.portfolio_relation, "exact")

    def test_six_plan_distinctions_have_different_canonical_causes(self) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.run_audit import replay_run_audit

        observed: dict[str, str] = {}
        observed["unsupported_input"] = execute(
            EarlyFixture("unsupported_input")
        ).result.classification.cause
        observed["budget_exhaustion"] = execute(
            EarlyFixture("planning_exhausted")
        ).result.classification.cause

        invalid_replay = replay_run_audit(b"{}\n", ())
        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=self.audit),
            mock.patch.object(disposition, "replay_run_audit", return_value=invalid_replay),
        ):
            observed["internal_error"] = execute(self.planned).result.classification.cause

        cases = (
            (
                "user_cancellation",
                PlannedFixture(origin_source="user", event_set=True),
            ),
            ("producer_failure", PlannedFixture(producer_exit=7)),
            (
                "verifier_failure",
                PlannedFixture(certificate_status="verifier_failed"),
            ),
        )
        for expected, fixture in cases:
            audit = fixture.audited_bundle()
            bundle, _audited, _replay = self.mocked_execution(fixture, audit)
            observed[expected] = bundle.result.classification.cause
        self.assertEqual(
            observed,
            {
                "user_cancellation": "user_cancellation",
                "budget_exhaustion": "budget_exhaustion",
                "unsupported_input": "unsupported_input",
                "internal_error": "internal_error",
                "producer_failure": "producer_failure",
                "verifier_failure": "verifier_failure",
            },
        )
        self.assertEqual(len(set(observed.values())), 6)

    def test_all_emitted_upstream_pairs_belong_to_the_closed_49_pair_table(self) -> None:
        pairs = portfolio_pairs()
        self.assertEqual(len(pairs), 49)
        bundles = [self.mocked_execution(self.planned, self.audit)[0]]
        for status in ("unsupported", "inconclusive", "verifier_failed"):
            fixture = PlannedFixture(certificate_status=status)
            bundles.append(self.mocked_execution(fixture, fixture.audited_bundle())[0])
        for bundle in bundles:
            pair = (
                bundle.result.portfolio_status,
                bundle.result.portfolio_reason_code,
            )
            self.assertIn(pair, pairs)

    def test_event_identity_is_forwarded_but_final_state_is_not_classification(self) -> None:
        fixture = PlannedFixture(origin_source="parent")
        audit = fixture.audited_bundle()
        fixture.inputs.cancel_event.set()
        bundle, audited, _replay = self.mocked_execution(fixture, audit)
        self.assertIs(audited.call_args.args[10], fixture.inputs.cancel_event)
        self.assertEqual(bundle.result.classification.cause, "checked_proof")
        self.assertEqual(bundle.result.classification.origin_source, None)

    def test_fatal_control_exceptions_propagate_without_retry_or_replay(self) -> None:
        from mathhead import execution_disposition as disposition

        for exception in (MemoryError(), KeyboardInterrupt(), SystemExit()):
            with self.subTest(exception=type(exception).__name__):
                with (
                    mock.patch.object(
                        disposition,
                        "execute_audited_run",
                        side_effect=exception,
                    ) as audited,
                    mock.patch.object(disposition, "replay_run_audit") as replay,
                ):
                    with self.assertRaises(type(exception)):
                        execute(self.planned)
                audited.assert_called_once()
                replay.assert_not_called()


class DeterminismTests(unittest.TestCase):
    def test_early_result_bytes_are_equal_across_fresh_hash_seeded_processes(self) -> None:
        code = """
from mathhead.execution_disposition import execute_with_disposition, execution_disposition_result_bytes
from tests.execution_disposition.fixtures import EarlyFixture
fixture = EarlyFixture('unsupported_input')
bundle = execute_with_disposition(*fixture.inputs.call_arguments)
print(execution_disposition_result_bytes(bundle.result).hex())
"""
        outputs = []
        for seed in ("1", "987654"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            env["PYTHONPATH"] = os.pathsep.join((str(SRC), str(ROOT)))
            completed = subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
