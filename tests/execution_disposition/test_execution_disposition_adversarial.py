from __future__ import annotations

import copy
from contextlib import ExitStack
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import sys
from threading import Event
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.capability_registry.fixtures import plugin_bytes  # noqa: E402
from tests.deterministic_planner.fixtures import PlannerFixture  # noqa: E402
from tests.execution_disposition.fixtures import (  # noqa: E402
    EarlyFixture,
    PlannedFixture,
    anchored_budget,
    canonical,
    changed_request,
    make_disposition_request,
    self_hash,
    sha,
)


def execute(fixture: PlannedFixture):
    from mathhead.execution_disposition import execute_with_disposition

    return execute_with_disposition(*fixture.inputs.call_arguments)


def mocked_execution(fixture: PlannedFixture, audit: object):
    from mathhead import execution_disposition as disposition
    from mathhead.run_audit import replay_run_audit

    with (
        mock.patch.object(disposition, "execute_audited_run", return_value=audit) as audited,
        mock.patch.object(disposition, "replay_run_audit", wraps=replay_run_audit) as replay,
    ):
        bundle = execute(fixture)
    return bundle, audited, replay


def _replace_checker_executable(
    fixture: PlannedFixture,
    *,
    checker_bytes: bytes,
    checker_path: str,
    invocation_id: str,
) -> PlannedFixture:
    from mathhead.proof_search_portfolio import (
        make_portfolio_execution_binding,
        parse_portfolio_execution_binding,
    )

    parsed = parse_portfolio_execution_binding(fixture.binding)
    binding = make_portfolio_execution_binding(
        plan_order=parsed.plan_order,
        strategy_sha256=parsed.strategy_sha256,
        descriptor_sha256=parsed.descriptor_sha256,
        producer_component_id=parsed.producer_component_id,
        checker_component_id=parsed.checker_component_id,
        producer_family=parsed.producer_family,
        checker_family=parsed.checker_family,
        producer_executable=fixture.source.executable_bytes,
        checker_executable=checker_bytes,
        producer_arguments=parsed.producer_arguments,
        checker_arguments=parsed.checker_arguments,
        input_artifacts=fixture.inputs.artifacts,
    )
    request, request_value = make_disposition_request(
        planning_request=fixture.inputs.planning_request,
        route_result=fixture.inputs.route_result,
        planning_result=fixture.inputs.planning_result,
        base_parent_budget=fixture.inputs.base_parent_budget,
        descriptors=fixture.inputs.descriptors,
        bindings=(binding,),
        artifacts=fixture.inputs.artifacts,
        invocation_id=invocation_id,
    )
    if fixture.inputs.base_parent_budget is None:
        raise AssertionError("planned fixture unexpectedly lacks a base budget")
    fixture.binding = binding
    fixture.expected_anchor = anchored_budget(
        fixture.inputs.base_parent_budget,
        str(request_value["request_sha256"]),
    )
    fixture.inputs = replace(
        fixture.inputs,
        request=request,
        request_value=request_value,
        bindings=(binding,),
        executable_paths=(
            (
                sha(fixture.source.executable_bytes),
                fixture.inputs.executable_paths[0][1],
            ),
            (sha(checker_bytes), checker_path),
        ),
    )
    return fixture


def _transplant_outer_pair(audit: object):
    """Build a replay-complete audit whose outer pair contradicts its final attempt."""
    from mathhead.run_audit import RunAuditBundle

    manifest = json.loads(audit.manifest)  # type: ignore[attr-defined]
    logical = json.loads(audit.logical_report)  # type: ignore[attr-defined]
    physical = {sha(raw): raw for raw in audit.objects}  # type: ignore[attr-defined]
    records = {item["role_id"]: item for item in manifest["objects"]}

    portfolio_record = records["portfolio_result"]
    old_portfolio_sha = portfolio_record["sha256"]
    portfolio = json.loads(physical[old_portfolio_sha])
    portfolio["status"] = "ambiguous"
    portfolio["reason_code"] = "EVIDENCE_INCOMPLETE"
    self_hash(portfolio, "result_sha256")
    portfolio_raw = canonical(portfolio)
    portfolio_sha = sha(portfolio_raw)
    portfolio_record["sha256"] = portfolio_sha
    portfolio_record["byte_count"] = len(portfolio_raw)
    self_hash(portfolio_record, "record_sha256")

    logical_record = records["logical_report"]
    old_logical_sha = logical_record["sha256"]
    logical["status"] = "ambiguous"
    logical["reason_code"] = "EVIDENCE_INCOMPLETE"
    self_hash(logical, "report_sha256")
    logical_raw = canonical(logical)
    logical_sha = sha(logical_raw)
    logical_record["sha256"] = logical_sha
    logical_record["byte_count"] = len(logical_raw)
    self_hash(logical_record, "record_sha256")

    manifest["portfolio_result_sha256"] = portfolio_sha
    manifest["logical_report_sha256"] = logical_sha
    closed = manifest["events"][-1]
    if closed["kind"] != "run_closed":
        raise AssertionError("fixture audit lacks a final run_closed event")
    closed["reason_code"] = "EVIDENCE_INCOMPLETE"
    closed["subject_sha256s"] = sorted(
        (portfolio_sha, logical_sha, manifest["final_parent_budget_sha256"])
    )
    self_hash(closed, "event_sha256")
    self_hash(manifest, "manifest_sha256")
    manifest_raw = canonical(manifest)

    objects = tuple(
        sorted(
            (
                portfolio_raw
                if sha(raw) == old_portfolio_sha
                else logical_raw
                if sha(raw) == old_logical_sha
                else raw
                for raw in audit.objects  # type: ignore[attr-defined]
            ),
            key=sha,
        )
    )
    forged = object.__new__(RunAuditBundle)
    for name, value in (
        ("manifest", manifest_raw),
        ("objects", objects),
        ("logical_report", logical_raw),
        ("manifest_sha256", sha(manifest_raw)),
        ("logical_report_sha256", logical_sha),
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    return forged


def _drop_portfolio_input_identity(audit: object, field: str):
    """Keep replay complete while deleting one required terminal input link."""
    from mathhead.run_audit import RunAuditBundle

    manifest = json.loads(audit.manifest)  # type: ignore[attr-defined]
    physical = {sha(raw): raw for raw in audit.objects}  # type: ignore[attr-defined]
    records = {item["role_id"]: item for item in manifest["objects"]}
    portfolio_record = records["portfolio_result"]
    old_portfolio_sha = portfolio_record["sha256"]
    portfolio = json.loads(physical[old_portfolio_sha])
    portfolio[field] = None
    self_hash(portfolio, "result_sha256")
    portfolio_raw = canonical(portfolio)
    portfolio_sha = sha(portfolio_raw)
    portfolio_record["sha256"] = portfolio_sha
    portfolio_record["byte_count"] = len(portfolio_raw)
    self_hash(portfolio_record, "record_sha256")

    manifest["portfolio_result_sha256"] = portfolio_sha
    closed = manifest["events"][-1]
    if closed["kind"] != "run_closed" or old_portfolio_sha not in closed["subject_sha256s"]:
        raise AssertionError("fixture audit lacks the terminal portfolio relation")
    closed["subject_sha256s"] = sorted(
        portfolio_sha if item == old_portfolio_sha else item for item in closed["subject_sha256s"]
    )
    self_hash(closed, "event_sha256")
    self_hash(manifest, "manifest_sha256")
    manifest_raw = canonical(manifest)
    objects = tuple(
        sorted(
            (
                portfolio_raw if sha(raw) == old_portfolio_sha else raw
                for raw in audit.objects  # type: ignore[attr-defined]
            ),
            key=sha,
        )
    )
    forged = object.__new__(RunAuditBundle)
    for name, value in (
        ("manifest", manifest_raw),
        ("objects", objects),
        ("logical_report", audit.logical_report),  # type: ignore[attr-defined]
        ("manifest_sha256", sha(manifest_raw)),
        ("logical_report_sha256", sha(audit.logical_report)),  # type: ignore[attr-defined]
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    return forged


class ExactEffectBoundaryTests(unittest.TestCase):
    def test_planned_path_orders_each_outer_effect_once_and_skips_forbidden_boundaries(
        self,
    ) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead import isolated_worker, proof_search_portfolio
        from mathhead import run_audit_store, safe_cache, safe_cache_store
        from mathhead.run_audit import replay_run_audit

        fixture = PlannedFixture()
        audit = fixture.audited_bundle()
        observed: list[str] = []

        def ordered(name: str, target):
            def invoke(*args, **kwargs):
                observed.append(name)
                return target(*args, **kwargs)

            return invoke

        original_route = disposition.route_capabilities
        original_plan = disposition.plan_strategies
        original_portfolio_request = disposition.make_proof_search_portfolio_request

        def audited_once(*_args, **_kwargs):
            observed.append("execute_audited_run")
            return audit

        forbidden = (
            (proof_search_portfolio, "run_portfolio"),
            (isolated_worker, "supervise_worker"),
            (safe_cache, "decide_safe_cache"),
            (safe_cache_store, "lookup_safe_cache"),
            (safe_cache_store, "persist_safe_cache"),
            (run_audit_store, "load_run_audit"),
            (run_audit_store, "persist_run_audit"),
        )
        with ExitStack() as stack:
            forbidden_mocks = [
                stack.enter_context(
                    mock.patch.object(
                        module,
                        name,
                        side_effect=AssertionError(f"forbidden boundary called: {name}"),
                    )
                )
                for module, name in forbidden
            ]
            routed = stack.enter_context(
                mock.patch.object(
                    disposition,
                    "route_capabilities",
                    side_effect=ordered("route_capabilities", original_route),
                )
            )
            planned = stack.enter_context(
                mock.patch.object(
                    disposition,
                    "plan_strategies",
                    side_effect=ordered("plan_strategies", original_plan),
                )
            )
            portfolio_request = stack.enter_context(
                mock.patch.object(
                    disposition,
                    "make_proof_search_portfolio_request",
                    side_effect=ordered(
                        "make_proof_search_portfolio_request",
                        original_portfolio_request,
                    ),
                )
            )
            audited = stack.enter_context(
                mock.patch.object(
                    disposition,
                    "execute_audited_run",
                    side_effect=audited_once,
                )
            )
            replayed = stack.enter_context(
                mock.patch.object(
                    disposition,
                    "replay_run_audit",
                    side_effect=ordered("replay_run_audit", replay_run_audit),
                )
            )
            bundle = execute(fixture)

        self.assertEqual(
            observed,
            [
                "route_capabilities",
                "plan_strategies",
                "make_proof_search_portfolio_request",
                "execute_audited_run",
                "replay_run_audit",
            ],
        )
        routed.assert_called_once()
        planned.assert_called_once()
        portfolio_request.assert_called_once()
        audited.assert_called_once()
        replayed.assert_called_once_with(audit.manifest, audit.objects)
        for boundary in forbidden_mocks:
            boundary.assert_not_called()
        self.assertEqual(bundle.result.classification.cause, "checked_proof")

    def test_all_individual_and_aggregate_input_byte_ceilings_precede_effects(
        self,
    ) -> None:
        from mathhead import execution_disposition as disposition

        early = EarlyFixture("unsupported_input")
        fixed_inputs = (
            early.inputs.request,
            early.inputs.planning_request,
            early.inputs.route_result,
            early.inputs.planning_result,
        )
        empty_artifacts = replace(early.inputs, artifacts=())
        planned = PlannedFixture()
        descriptor_total = sum(len(raw) for raw in planned.inputs.descriptors)
        artifact_total = sum(len(raw) for _, raw in planned.inputs.artifacts)
        cases = (
            (
                "individual_semantic_input",
                empty_artifacts,
                {"MAX_INPUT_BYTES": max(len(raw) for raw in fixed_inputs) - 1},
            ),
            (
                "empty_artifact_aggregate",
                empty_artifacts,
                {"MAX_AGGREGATE_INPUT_BYTES": (sum(len(raw) for raw in fixed_inputs) - 1)},
            ),
            (
                "descriptor_aggregate",
                planned.inputs,
                {"MAX_AGGREGATE_DESCRIPTOR_BYTES": descriptor_total - 1},
            ),
            (
                "artifact_aggregate",
                planned.inputs,
                {"MAX_AGGREGATE_ARTIFACT_BYTES": artifact_total - 1},
            ),
        )
        for label, inputs, ceilings in cases:
            with self.subTest(label=label), ExitStack() as stack:
                for name, value in ceilings.items():
                    stack.enter_context(mock.patch.object(disposition, name, value))
                audited = stack.enter_context(mock.patch.object(disposition, "execute_audited_run"))
                bundle = disposition.execute_with_disposition(*inputs.call_arguments)
            audited.assert_not_called()
            self.assertIsNone(bundle.request)
            self.assertEqual(bundle.result.classification.cause, "internal_error")
            self.assertEqual(bundle.result.classification.phase, "coordinator")
            self.assertEqual(
                [item.code for item in bundle.result.diagnostics],
                ["COORDINATOR_LIMIT_EXHAUSTED"],
            )

    def test_effect_only_string_ceilings_precede_retention_and_effects(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture()
        ceiling = 4_096
        oversized = "x" * (ceiling + 1)
        executable_paths = list(fixture.inputs.executable_paths)
        executable_paths[0] = (executable_paths[0][0], oversized)
        cases = (
            replace(fixture.inputs, workspace_root=oversized),
            replace(fixture.inputs, executable_paths=tuple(executable_paths)),
        )
        for inputs in cases:
            with (
                mock.patch.object(disposition, "MAX_STRING", ceiling),
                mock.patch.object(disposition, "route_capabilities") as routed,
                mock.patch.object(disposition, "plan_strategies") as planned,
                mock.patch.object(disposition, "execute_audited_run") as audited,
                mock.patch.object(disposition, "replay_run_audit") as replayed,
            ):
                bundle = disposition.execute_with_disposition(*inputs.call_arguments)
            routed.assert_not_called()
            planned.assert_not_called()
            audited.assert_not_called()
            replayed.assert_not_called()
            self.assertIsNone(bundle.request)
            self.assertEqual(bundle.result.classification.cause, "internal_error")
            self.assertEqual(bundle.result.classification.phase, "coordinator")
            self.assertEqual(
                [item.code for item in bundle.result.diagnostics],
                ["COORDINATOR_LIMIT_EXHAUSTED"],
            )

    def test_effect_only_path_count_ceiling_precedes_retention_and_effects(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = EarlyFixture("unsupported_input")
        paths = tuple((sha(str(index).encode()), f"path_{index}") for index in range(3))
        inputs = replace(fixture.inputs, executable_paths=paths)
        with (
            mock.patch.object(disposition, "MAX_EXECUTABLE_PATHS", 2),
            mock.patch.object(disposition, "route_capabilities") as routed,
            mock.patch.object(disposition, "plan_strategies") as planned,
            mock.patch.object(disposition, "execute_audited_run") as audited,
            mock.patch.object(disposition, "replay_run_audit") as replayed,
        ):
            bundle = disposition.execute_with_disposition(*inputs.call_arguments)
        routed.assert_not_called()
        planned.assert_not_called()
        audited.assert_not_called()
        replayed.assert_not_called()
        self.assertIsNone(bundle.request)
        self.assertEqual(bundle.result.classification.cause, "internal_error")
        self.assertEqual(bundle.result.classification.phase, "coordinator")
        self.assertEqual(
            [item.code for item in bundle.result.diagnostics],
            ["COORDINATOR_LIMIT_EXHAUSTED"],
        )

    def test_audit_output_and_replay_work_ceilings_precede_fresh_replay(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture()
        audit = fixture.audited_bundle()
        manifest = json.loads(audit.manifest)
        cases = (
            ("physical_objects", {"MAX_AUDIT_OBJECTS": len(audit.objects) - 1}),
            ("manifest_records", {"MAX_AUDIT_OBJECTS": len(audit.objects)}),
            ("events", {"MAX_AUDIT_EVENTS": len(manifest["events"]) - 1}),
            ("manifest_bytes", {"MAX_AUDIT_BYTES": len(audit.manifest) - 1}),
            (
                "object_bytes",
                {"MAX_AUDIT_BYTES": max(len(raw) for raw in audit.objects) - 1},
            ),
            (
                "aggregate_objects",
                {
                    "MAX_AGGREGATE_AUDIT_BYTES": sum(
                        len(raw) for raw in audit.objects
                    )
                    - 1
                },
            ),
            ("replay_operations", {"MAX_REPLAY_OPERATIONS": 1}),
        )
        for label, ceilings in cases:
            with self.subTest(label=label), ExitStack() as stack:
                for name, value in ceilings.items():
                    stack.enter_context(mock.patch.object(disposition, name, value))
                audited = stack.enter_context(
                    mock.patch.object(disposition, "execute_audited_run", return_value=audit)
                )
                replayed = stack.enter_context(
                    mock.patch.object(disposition, "replay_run_audit")
                )
                bundle = execute(fixture)
            audited.assert_called_once()
            replayed.assert_not_called()
            self.assertEqual(bundle.result.execution_state, "attempted_no_bundle")
            self.assertEqual(bundle.result.classification.cause, "internal_error")
            self.assertEqual(bundle.result.classification.phase, "audit")
            self.assertEqual(
                [item.code for item in bundle.result.diagnostics],
                ["AUDITED_EXECUTION_INVALID"],
            )
            self.assertIsNone(bundle.audit)
            self.assertIsNone(bundle.replay)

    def test_normalization_expression_dag_exhausts_before_fresh_replay(self) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.run_audit import RunAuditBundle

        def normalization_dag(depth: int) -> bytes:
            expressions: list[dict[str, object]] = [
                {
                    "id": "expression_0",
                    "kind": "literal",
                    "domain_id": "domain_integer",
                    "literal_type": "integer",
                    "value": "0",
                    "span_ids": [],
                }
            ]
            for index in range(1, depth + 1):
                expressions.append(
                    {
                        "id": f"expression_{index}",
                        "kind": "apply",
                        "domain_id": "domain_integer",
                        "operator": "org.mathhead.fixture.ordered",
                        "argument_expr_ids": [
                            f"expression_{index - 1}",
                            f"expression_{index - 1}",
                        ],
                        "attributes": {},
                        "span_ids": [],
                    }
                )
            return canonical(
                {
                    "schema": "mathhead.canonical-normalization-result.v1",
                    "status": "normalized",
                    "proof_obligation_result": {
                        "domain_assumption_result": {
                            "readings_result": {
                                "candidates": [
                                    {
                                        "projection": {
                                            "entities": {
                                                "domains": [
                                                    {
                                                        "id": "domain_integer",
                                                        "kind": "builtin",
                                                        "name": "integer",
                                                        "span_ids": [],
                                                    }
                                                ],
                                                "variables": [],
                                                "expressions": expressions,
                                                "relations": [],
                                                "statements": [],
                                                "definitions": [],
                                                "assumptions": [],
                                                "goals": [],
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    },
                }
            )

        bounded = normalization_dag(8)
        bounded_charge = disposition._replay_operation_preflight(  # noqa: SLF001
            {}, b"{}\n", (bounded,)
        )
        self.assertLess(bounded_charge, disposition.MAX_REPLAY_OPERATIONS)

        fixture = PlannedFixture()
        audit = fixture.audited_bundle()
        forged = object.__new__(RunAuditBundle)
        for name, value in (
            ("manifest", audit.manifest),
            ("objects", (*audit.objects, normalization_dag(12))),
            ("logical_report", audit.logical_report),
            ("manifest_sha256", audit.manifest_sha256),
            ("logical_report_sha256", audit.logical_report_sha256),
            ("mathematical_authority", False),
        ):
            object.__setattr__(forged, name, value)
        with (
            mock.patch.object(
                disposition, "execute_audited_run", return_value=forged
            ) as audited,
            mock.patch.object(disposition, "replay_run_audit") as replayed,
        ):
            bundle = execute(fixture)
        audited.assert_called_once()
        replayed.assert_not_called()
        self.assertEqual(bundle.result.execution_state, "attempted_no_bundle")
        self.assertEqual(bundle.result.classification.cause, "internal_error")
        self.assertEqual(
            [item.code for item in bundle.result.diagnostics],
            ["AUDITED_EXECUTION_INVALID"],
        )
        self.assertIsNone(bundle.audit)
        self.assertIsNone(bundle.replay)

    def test_replay_invalid_audit_never_retains_hostile_raw_objects(self) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.run_audit import RunAuditBundle, replay_run_audit

        fixture = PlannedFixture()
        audit = fixture.audited_bundle()
        secret = b"credential=mh056-secret-path-env-stderr"
        forged = object.__new__(RunAuditBundle)
        for name, value in (
            ("manifest", audit.manifest),
            ("objects", tuple(sorted((*audit.objects, secret), key=sha))),
            ("logical_report", audit.logical_report),
            ("manifest_sha256", audit.manifest_sha256),
            ("logical_report_sha256", audit.logical_report_sha256),
            ("mathematical_authority", False),
        ):
            object.__setattr__(forged, name, value)
        with (
            mock.patch.object(disposition, "execute_audited_run", return_value=forged),
            mock.patch.object(
                disposition, "replay_run_audit", wraps=replay_run_audit
            ) as replayed,
        ):
            bundle = execute(fixture)
        replayed.assert_called_once_with(forged.manifest, forged.objects)
        self.assertEqual(bundle.result.execution_state, "bundle_replay_failed")
        self.assertEqual(bundle.result.replay_status, "invalid")
        self.assertEqual(bundle.result.replay_reason_code, "REPLAY_INVALID")
        self.assertEqual(bundle.result.audit_manifest_sha256, audit.manifest_sha256)
        self.assertIsNotNone(bundle.result.replay_result_sha256)
        self.assertIsNone(bundle.audit)
        self.assertIsNone(bundle.replay)
        raw = disposition.execution_disposition_result_bytes(bundle.result)
        self.assertNotIn(secret, raw)
        self.assertNotIn(secret.decode("ascii"), repr(bundle))
        disposition.validate_execution_disposition_bundle(bundle)

    def test_ordinary_audited_failure_is_static_internal_and_never_retried(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture()
        secret = "secret-path-and-credential-must-not-survive"
        with (
            mock.patch.object(
                disposition,
                "execute_audited_run",
                side_effect=RuntimeError(secret),
            ) as audited,
            mock.patch.object(disposition, "replay_run_audit") as replay,
        ):
            bundle = execute(fixture)
        audited.assert_called_once()
        replay.assert_not_called()
        self.assertEqual(bundle.result.classification.cause, "internal_error")
        self.assertEqual(bundle.result.classification.phase, "audit")
        self.assertEqual(
            [item.code for item in bundle.result.diagnostics],
            ["AUDITED_EXECUTION_INVALID"],
        )
        self.assertNotIn(secret, repr(bundle.result))


class AntiReplayAndProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PlannedFixture(origin_source="user", event_set=True)
        cls.audit = cls.fixture.audited_bundle()

    def test_stale_cancelled_audit_cannot_authorize_rebound_intent_or_invocation(
        self,
    ) -> None:
        from mathhead import execution_disposition as disposition

        cases = (
            (
                "intent",
                lambda value: value["cancellation_intent"].update(intent_id="intent_retrofitted"),
            ),
            (
                "invocation",
                lambda value: (
                    value.update(invocation_id="invocation_rebound"),
                    value["cancellation_intent"].update(invocation_id="invocation_rebound"),
                ),
            ),
        )
        for label, mutation in cases:
            with self.subTest(label=label):
                request = changed_request(self.fixture.inputs.request, mutation)
                disposition.parse_execution_disposition_request(request)
                current_event = Event()
                current_event.set()
                fixture = copy.copy(self.fixture)
                fixture.inputs = replace(
                    self.fixture.inputs,
                    request=request,
                    request_value=json.loads(request),
                    cancel_event=current_event,
                )
                bundle, audited, replay = mocked_execution(fixture, self.audit)
                audited.assert_called_once()
                replay.assert_called_once_with(self.audit.manifest, self.audit.objects)
                self.assertIs(audited.call_args.args[10], current_event)
                self.assertEqual(
                    audited.call_args.args[4],
                    anchored_budget(
                        fixture.inputs.base_parent_budget,
                        json.loads(request)["request_sha256"],
                    ),
                )
                self.assertEqual(bundle.result.classification.cause, "internal_error")
                self.assertNotEqual(bundle.result.classification.cause, "user_cancellation")
                self.assertEqual(bundle.result.portfolio_relation, "invalid")
                self.assertEqual(
                    [item.code for item in bundle.result.diagnostics],
                    ["AUDIT_RELATION_INVALID"],
                )

    def test_each_result_request_projection_rejects_outer_hash_repair(self) -> None:
        from mathhead import execution_disposition as disposition

        bundle, _audited, _replay = mocked_execution(self.fixture, self.audit)
        self.assertEqual(bundle.result.classification.cause, "user_cancellation")
        raw = disposition.execution_disposition_result_bytes(bundle.result)
        retained = {
            "request_input": self.fixture.inputs.request,
            "request": bundle.request,
            "anchored_parent_budget": (
                disposition.execution_disposition_anchored_budget_bytes(bundle)
            ),
            "portfolio_request": (
                disposition.execution_disposition_portfolio_request_bytes(bundle)
            ),
            "audit": bundle.audit,
            "replay": bundle.replay,
        }
        mutations = (
            ("disposition_request_sha256", "f" * 64),
            ("invocation_sha256", "f" * 64),
            ("cancellation_armed", False),
            ("cancellation_intent_sha256", "f" * 64),
        )
        for field, replacement in mutations:
            with self.subTest(field=field):
                value = json.loads(raw)
                value[field] = replacement
                self_hash(value, "result_sha256")
                with self.assertRaises(disposition.ExecutionDispositionValidationError):
                    disposition.parse_execution_disposition_result(canonical(value), **retained)

    def test_bundle_cannot_erase_a_validated_result_request(self) -> None:
        from mathhead import execution_disposition as disposition

        genuine = execute(EarlyFixture("unsupported_input"))
        parsed = disposition.parse_execution_disposition_result(
            disposition.execution_disposition_result_bytes(genuine.result)
        )
        self.assertIsNone(parsed._request)
        self.assertIsNotNone(parsed.disposition_request_sha256)
        forged = object.__new__(disposition.ExecutionDispositionBundle)
        for name, value in (
            ("request", None),
            ("result", parsed),
            ("audit", None),
            ("replay", None),
            ("mathematical_authority", False),
        ):
            object.__setattr__(forged, name, value)
        with self.assertRaises(disposition.ExecutionDispositionValidationError):
            disposition.validate_execution_disposition_bundle(forged)


class CrossLayerRelationTests(unittest.TestCase):
    def test_terminal_portfolio_must_bind_current_request_and_plan(self) -> None:
        from mathhead.run_audit import replay_run_audit

        fixture = PlannedFixture()
        for field in ("request_sha256", "planning_result_sha256"):
            with self.subTest(field=field):
                forged = _drop_portfolio_input_identity(fixture.audited_bundle(), field)
                replay = replay_run_audit(forged.manifest, forged.objects)
                self.assertEqual(replay.status, "complete")
                bundle, audited, replayed = mocked_execution(fixture, forged)
                audited.assert_called_once()
                replayed.assert_called_once_with(forged.manifest, forged.objects)
                self.assertEqual(bundle.result.classification.cause, "internal_error")
                self.assertEqual(bundle.result.portfolio_relation, "invalid")
                self.assertEqual(
                    [item.code for item in bundle.result.diagnostics],
                    ["AUDIT_RELATION_INVALID"],
                )

    def test_replay_complete_outer_pair_transplant_is_an_audit_relation_error(
        self,
    ) -> None:
        from mathhead.run_audit import replay_run_audit

        fixture = PlannedFixture(certificate_status="inconclusive")
        forged = _transplant_outer_pair(fixture.audited_bundle())
        independent_replay = replay_run_audit(forged.manifest, forged.objects)
        self.assertEqual(
            (
                independent_replay.status,
                independent_replay.portfolio_status,
                independent_replay.mathematical_verdict,
            ),
            ("complete", "ambiguous", "inconclusive"),
        )
        bundle, audited, replay = mocked_execution(fixture, forged)
        audited.assert_called_once()
        replay.assert_called_once_with(forged.manifest, forged.objects)
        self.assertEqual(bundle.result.classification.cause, "internal_error")
        self.assertEqual(bundle.result.classification.phase, "audit")
        self.assertEqual(bundle.result.portfolio_relation, "invalid")
        self.assertEqual(
            [item.code for item in bundle.result.diagnostics],
            ["AUDIT_RELATION_INVALID"],
        )

    def test_one_availability_only_group_outweighs_a_separate_structural_group(
        self,
    ) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.capability_registry import parse_capability_route_result
        from mathhead.deterministic_planner import (
            plan_strategies,
            planning_result_bytes,
        )

        base = PlannerFixture()
        domain = plugin_bytes(
            base.fragment,
            suffix="domain_mismatch",
            mutation=lambda value: value["capabilities"][0]["fragment"].update(domains=["real"]),
        )
        platform = plugin_bytes(
            base.fragment,
            suffix="platform_unavailable",
            mutation=lambda value: value["compatibility"].update(platforms=["macos"]),
        )
        planning_request, route_result, descriptors, artifact_bytes = base.planning_inputs(
            (domain, platform)
        )
        route = parse_capability_route_result(route_result)
        self.assertEqual(
            {item.reason_codes for item in route.incompatibilities},
            {("DOMAIN_MISMATCH",), ("PLATFORM_UNAVAILABLE",)},
        )
        plan = plan_strategies(
            planning_request,
            route_result,
            descriptors,
            artifact_bytes,
        )
        plan_raw = planning_result_bytes(plan)
        artifacts = tuple((f"input_{index}", raw) for index, raw in enumerate(artifact_bytes))
        request, _request_value = make_disposition_request(
            planning_request=planning_request,
            route_result=route_result,
            planning_result=plan_raw,
            base_parent_budget=None,
            descriptors=descriptors,
            bindings=(),
            artifacts=artifacts,
            invocation_id="invocation_mixed_unsupported_groups",
        )
        with (
            mock.patch.object(disposition, "execute_audited_run") as audited,
            mock.patch.object(disposition, "replay_run_audit") as replay,
        ):
            bundle = disposition.execute_with_disposition(
                request,
                planning_request,
                route_result,
                plan_raw,
                None,
                descriptors,
                (),
                artifacts,
                (),
                None,
                None,
            )
        audited.assert_not_called()
        replay.assert_not_called()
        self.assertEqual(
            bundle.result.classification.cause,
            "unsupported_execution_environment",
        )

    def test_request_bound_canonical_malformed_binding_fails_after_plan(self) -> None:
        from mathhead import execution_disposition as disposition

        fixture = PlannedFixture()
        malformed_binding = b"{}\n"
        request, request_value = make_disposition_request(
            planning_request=fixture.inputs.planning_request,
            route_result=fixture.inputs.route_result,
            planning_result=fixture.inputs.planning_result,
            base_parent_budget=fixture.inputs.base_parent_budget,
            descriptors=fixture.inputs.descriptors,
            bindings=(malformed_binding,),
            artifacts=fixture.inputs.artifacts,
            invocation_id="invocation_malformed_bound_binding",
        )
        fixture.inputs = replace(
            fixture.inputs,
            request=request,
            request_value=request_value,
            bindings=(malformed_binding,),
        )
        with mock.patch.object(disposition, "execute_audited_run") as audited:
            bundle = execute(fixture)
        audited.assert_not_called()
        self.assertEqual(bundle.result.classification.cause, "invalid_request")
        self.assertEqual(bundle.result.classification.phase, "planning")
        self.assertEqual(bundle.result.route_status, "routed")
        self.assertEqual(bundle.result.planning_status, "planned")
        self.assertEqual(
            [item.code for item in bundle.result.diagnostics],
            ["BINDING_INPUT_INVALID"],
        )


class SpecialWorkerOutcomeTests(unittest.TestCase):
    def test_producer_launch_refusal_is_exact_component_failure(self) -> None:
        fixture = PlannedFixture()
        with tempfile.TemporaryDirectory(prefix="mh056-launch-refusal-") as root:
            missing = Path(root) / "missing-workspace"
            fixture.inputs = replace(fixture.inputs, workspace_root=str(missing))
            bundle = execute(fixture)
        result = bundle.result
        self.assertEqual(result.classification.cause, "producer_failure")
        self.assertEqual(result.classification.phase, "producer")
        self.assertEqual(
            (result.portfolio_status, result.portfolio_reason_code),
            ("failed", "LAUNCH_FAILED"),
        )
        self.assertEqual(result.portfolio_relation, "exact")
        self.assertEqual(result.portfolio_outcome_kind, "launch_refused")

    def test_checker_launch_refusal_is_exact_component_failure(self) -> None:
        from mathhead import proof_search_portfolio as portfolio

        fixture = PlannedFixture()
        original = portfolio.supervise_worker
        calls = 0
        with tempfile.TemporaryDirectory(prefix="mh056-checker-launch-") as root:
            missing = str(Path(root) / "missing-checker-workspace")
            fixture.inputs = replace(fixture.inputs, workspace_root=root)

            def refuse_second(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    changed = list(args)
                    changed[5] = missing
                    args = tuple(changed)
                return original(*args, **kwargs)

            with mock.patch.object(portfolio, "supervise_worker", side_effect=refuse_second):
                bundle = execute(fixture)
        self.assertEqual(calls, 2)
        result = bundle.result
        self.assertEqual(result.classification.cause, "verifier_failure")
        self.assertEqual(result.classification.phase, "checker")
        self.assertEqual(
            (result.portfolio_status, result.portfolio_reason_code),
            ("verifier_failed", "LAUNCH_FAILED"),
        )
        self.assertEqual(result.portfolio_relation, "exact")
        self.assertEqual(result.portfolio_outcome_kind, "launch_refused")

    def test_producer_executable_invalid_is_internal_not_component_refusal(
        self,
    ) -> None:
        fixture = PlannedFixture()
        expected_sha = fixture.inputs.executable_paths[0][0]
        with tempfile.TemporaryDirectory(prefix="mh056-producer-invalid-") as root:
            wrong = Path(root) / "wrong-executable"
            wrong.write_bytes(b"not the bound executable")
            wrong.chmod(0o700)
            workspace = Path(root) / "workspace"
            workspace.mkdir()
            fixture.inputs = replace(
                fixture.inputs,
                executable_paths=((expected_sha, str(wrong)),),
                workspace_root=str(workspace),
            )
            bundle = execute(fixture)
        result = bundle.result
        self.assertEqual(result.classification.cause, "internal_error")
        self.assertEqual(result.classification.phase, "coordinator")
        self.assertEqual(
            (result.portfolio_status, result.portfolio_reason_code),
            ("failed", "EXECUTABLE_INVALID"),
        )
        self.assertEqual(result.portfolio_relation, "exact")
        self.assertEqual(result.portfolio_outcome_kind, "executable_invalid")
        self.assertEqual(
            [item.code for item in result.diagnostics],
            ["WORKER_EXECUTABLE_INVARIANT"],
        )

    def test_checker_executable_invalid_is_internal_not_component_refusal(
        self,
    ) -> None:
        checker_bytes = b"checker executable identity distinct from producer"
        with tempfile.TemporaryDirectory(prefix="mh056-checker-invalid-") as root:
            wrong = Path(root) / "wrong-checker"
            wrong.write_bytes(b"not the bound checker executable")
            wrong.chmod(0o700)
            workspace = Path(root) / "workspace"
            workspace.mkdir()
            fixture = _replace_checker_executable(
                PlannedFixture(),
                checker_bytes=checker_bytes,
                checker_path=str(wrong),
                invocation_id="invocation_checker_executable_invalid",
            )
            fixture.inputs = replace(fixture.inputs, workspace_root=str(workspace))
            bundle = execute(fixture)
        result = bundle.result
        self.assertEqual(result.classification.cause, "internal_error")
        self.assertEqual(result.classification.phase, "coordinator")
        self.assertEqual(
            (result.portfolio_status, result.portfolio_reason_code),
            ("verifier_failed", "EXECUTABLE_INVALID"),
        )
        self.assertEqual(result.portfolio_relation, "exact")
        self.assertEqual(result.portfolio_outcome_kind, "executable_invalid")
        self.assertEqual(
            [item.code for item in result.diagnostics],
            ["WORKER_EXECUTABLE_INVARIANT"],
        )

    @unittest.skipIf(os.name == "nt", "POSIX executable permission refusal")
    def test_producer_and_checker_executable_permission_refusals_are_component_refusals(
        self,
    ) -> None:
        producer = PlannedFixture()
        with tempfile.TemporaryDirectory(prefix="mh056-executable-refusal-") as root:
            root_path = Path(root)
            producer_copy = root_path / "producer-copy"
            shutil.copyfile(producer.inputs.executable_paths[0][1], producer_copy)
            producer_copy.chmod(0o600)
            producer_workspace = root_path / "producer-workspace"
            producer_workspace.mkdir()
            producer.inputs = replace(
                producer.inputs,
                executable_paths=((producer.inputs.executable_paths[0][0], str(producer_copy)),),
                workspace_root=str(producer_workspace),
            )
            producer_result = execute(producer).result

            checker_bytes = b"checker permission refusal executable"
            checker_copy = root_path / "checker-copy"
            checker_copy.write_bytes(checker_bytes)
            checker_copy.chmod(0o600)
            checker_workspace = root_path / "checker-workspace"
            checker_workspace.mkdir()
            checker = _replace_checker_executable(
                PlannedFixture(),
                checker_bytes=checker_bytes,
                checker_path=str(checker_copy),
                invocation_id="invocation_checker_executable_refused",
            )
            checker.inputs = replace(checker.inputs, workspace_root=str(checker_workspace))
            checker_result = execute(checker).result

        self.assertEqual(
            (
                producer_result.classification.cause,
                producer_result.classification.phase,
                producer_result.portfolio_status,
                producer_result.portfolio_reason_code,
                producer_result.portfolio_relation,
                producer_result.portfolio_outcome_kind,
            ),
            (
                "producer_refusal",
                "producer",
                "failed",
                "EXECUTABLE_INVALID",
                "exact",
                "executable_refused",
            ),
        )
        self.assertEqual(
            (
                checker_result.classification.cause,
                checker_result.classification.phase,
                checker_result.portfolio_status,
                checker_result.portfolio_reason_code,
                checker_result.portfolio_relation,
                checker_result.portfolio_outcome_kind,
            ),
            (
                "verifier_refusal",
                "checker",
                "verifier_failed",
                "EXECUTABLE_INVALID",
                "exact",
                "executable_refused",
            ),
        )


if __name__ == "__main__":
    unittest.main()
