from __future__ import annotations

from dataclasses import FrozenInstanceError
import copy
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import mathhead.deterministic_planner as planner_module  # noqa: E402
from mathhead.deterministic_planner import (  # noqa: E402
    CONTRACT_SHA256,
    OUTCOMES,
    RESOURCE_DIMENSIONS,
    SCHEMA_SHA256S,
    DeterministicPlannerValidationError,
    PlanningEvidenceExpectation,
    PlanningPolicy,
    PlanningPrerequisite,
    PlanningRequest,
    PlanningResourceRequest,
    PlanningResourceVector,
    PlanningResult,
    PlanningStrategy,
    PlanningTransition,
    make_planning_policy,
    parse_planning_request,
    parse_planning_result,
    plan_strategies,
    planning_policy_bytes,
    planning_result_bytes,
    validate_planning_result,
)
from tests.capability_registry.fixtures import plugin_bytes, sha  # noqa: E402
from tests.deterministic_planner.fixtures import (  # noqa: E402
    PlannerFixture,
    canonical,
    self_hash,
)


class DeterministicPlannerContractTests(unittest.TestCase):
    def test_accepted_contract_and_closed_schemas_are_exact(self) -> None:
        accepted = ROOT / "docs/contracts/MH-C-DETERMINISTIC-PLANNER-001.json"
        proposal = ROOT / "docs/contracts/proposed/MH-C-DETERMINISTIC-PLANNER-001.json"
        self.assertEqual(accepted.read_bytes(), proposal.read_bytes())
        self.assertEqual(sha(accepted.read_bytes()), CONTRACT_SHA256)
        self.assertEqual(len(SCHEMA_SHA256S), 8)
        for schema, expected in SCHEMA_SHA256S.items():
            name = schema.removeprefix("mathhead.").replace(".", "-") + ".schema.json"
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, name)
            parsed = json.loads(raw)
            self.assertEqual(parsed["additionalProperties"], False, name)


class DeterministicPlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PlannerFixture()

    def plan(self, *args: object, **kwargs: object):
        inputs = self.fixture.planning_inputs(*args, **kwargs)
        return plan_strategies(*inputs), inputs

    def test_exact_plan_binds_every_layer_and_round_trips(self) -> None:
        result, _inputs = self.plan()
        self.assertEqual((result.status, result.reason_code), ("planned", "PLANNED"))
        self.assertEqual(len(result.strategies), 1)
        strategy = result.strategies[0]
        self.assertEqual(result.entry_strategy_sha256, strategy.strategy_sha256)
        self.assertEqual(tuple(item.outcome for item in strategy.transitions), OUTCOMES)
        self.assertEqual(len(strategy.transitions), 11)
        self.assertGreaterEqual(len(strategy.prerequisites), 6)
        self.assertEqual(strategy.prerequisites[0].kind, "route")
        self.assertEqual(strategy.evidence_expectation.operation_authority, "producer_report")
        self.assertTrue(strategy.evidence_expectation.independent_check_required)
        self.assertFalse(result.mathematical_authority)
        validate_planning_result(result)
        raw = planning_result_bytes(result)
        self.assertEqual(parse_planning_result(raw), result)

    def test_many_candidates_form_one_forward_reachable_dag(self) -> None:
        descriptors = self.fixture.descriptors(3)
        result, _inputs = self.plan(descriptors)
        self.assertEqual(result.status, "planned", result.diagnostic)
        self.assertEqual(len(result.strategies), 3)
        self.assertEqual([item.plan_order for item in result.strategies], [0, 1, 2])
        self.assertEqual(len({item.candidate_sha256 for item in result.strategies}), 3)
        for index, strategy in enumerate(result.strategies):
            retryable = [item for item in strategy.transitions if item.outcome in planner_module.RETRY_TERMINALS]
            if index + 1 < len(result.strategies):
                self.assertEqual({item.action for item in retryable}, {"fallback"})
                self.assertEqual(
                    {item.target_strategy_sha256 for item in retryable},
                    {result.strategies[index + 1].strategy_sha256},
                )
            else:
                self.assertEqual({item.action for item in retryable}, {"stop"})

    def test_registry_and_deterministic_first_policies_are_explicit(self) -> None:
        descriptors = self.fixture.descriptors(3)
        default, _ = self.plan(descriptors)
        alternate, _ = self.plan(descriptors, policy_mode="deterministic_first")
        self.assertEqual(
            [item.candidate_sha256 for item in default.strategies],
            [item.candidate_sha256 for item in alternate.strategies],
        )
        self.assertNotEqual(default.policy_sha256, alternate.policy_sha256)
        self.assertNotEqual(default.result_sha256, alternate.result_sha256)

    def test_resource_arithmetic_is_exact_and_solver_sensitive(self) -> None:
        result, _ = self.plan()
        strategy = result.strategies[0]
        cost = strategy.estimated_cost
        requested = strategy.resource_request.requested
        self.assertEqual(requested.wall_time_us, cost * 1_000)
        self.assertEqual(requested.cpu_time_us, cost * 1_000)
        self.assertEqual(requested.memory_bytes, (cost + 1) * 1_024)
        self.assertEqual(requested.solver_calls, 0)
        self.assertEqual(requested.generated_objects, cost)
        self.assertEqual(requested.proof_bytes, cost * 16)
        self.assertEqual(requested.diagnostic_bytes, min(cost * 4, 4_096))
        self.assertEqual(requested.nesting_depth, 1)

        def solver_effect(value: dict[str, object]) -> None:
            value["effects"][4].update(  # type: ignore[index]
                mode="declared",
                policy_id="org.mathhead.solver-policy",
                reason="bounded solver fixture",
            )
            value["operations"][1]["effect_kinds"] = ["solver"]  # type: ignore[index]
            value["lifecycle"]["isolation"] = "subprocess_required"  # type: ignore[index]
            value["lifecycle"]["shutdown_timeout_us"] = 1_000_000  # type: ignore[index]

        descriptor = plugin_bytes(
            self.fixture.fragment,
            suffix="solver_resource",
            mutation=solver_effect,
        )
        solver, _ = self.plan(
            (descriptor,),
            availability_changes={"allowed_effects": ("solver",)},
        )
        self.assertEqual(solver.status, "planned", solver.diagnostic)
        self.assertEqual(solver.strategies[0].resource_request.requested.solver_calls, 1)

    def test_parent_limit_or_strategy_ceiling_exhausts_without_partial_plan(self) -> None:
        limits = {name: 0 for name in RESOURCE_DIMENSIONS}
        exhausted, _ = self.plan(limits=limits)
        self.assertEqual(exhausted.status, "exhausted")
        self.assertEqual(exhausted.strategies, ())
        self.assertIsNone(exhausted.result_sha256)

        descriptors = self.fixture.descriptors(2)
        capped, _ = self.plan(descriptors, maximum_strategies=1)
        self.assertEqual(capped.status, "exhausted")
        self.assertEqual(capped.strategies, ())

    def test_unsupported_route_has_no_strategy_and_preserves_binding(self) -> None:
        result, _ = self.plan(())
        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.strategies, ())
        self.assertIsNotNone(result.planning_request_sha256)
        self.assertIsNotNone(result.route_result_sha256)
        self.assertIsNotNone(result.result_sha256)

    def test_stale_route_descriptor_or_artifact_never_plans(self) -> None:
        result, inputs = self.plan()
        self.assertEqual(result.status, "planned")
        request, route_bytes, descriptors, artifacts = inputs
        changed_descriptor = plugin_bytes(self.fixture.fragment, suffix="changed")
        stale = plan_strategies(request, route_bytes, (changed_descriptor,), artifacts)
        self.assertEqual(stale.status, "invalid")
        self.assertEqual(stale.strategies, ())
        missing = plan_strategies(request, route_bytes, descriptors, artifacts[:-1])
        self.assertEqual(missing.status, "invalid")

    def test_request_route_digest_and_exact_bytes_are_recomputed(self) -> None:
        _result, inputs = self.plan()
        request, route_bytes, descriptors, artifacts = inputs
        request_value = json.loads(request)
        request_value["route_result_sha256"] = "0" * 64
        self_hash(request_value, "request_sha256")
        mismatch = plan_strategies(canonical(request_value), route_bytes, descriptors, artifacts)
        self.assertEqual(mismatch.status, "invalid")
        noncanonical = plan_strategies(request.rstrip(b"\n"), route_bytes, descriptors, artifacts)
        self.assertEqual(noncanonical.status, "invalid")

    def test_dependency_and_contract_prerequisites_are_complete(self) -> None:
        foundation = plugin_bytes(self.fixture.fragment, suffix="foundation")

        def depend(value: dict[str, object]) -> None:
            value["compatibility"]["plugin_dependencies"] = [{  # type: ignore[index]
                "plugin_id": "org.mathhead.fixture-foundation",
                "version_minimum": "1.0.0",
                "version_maximum_exclusive": "2.0.0",
                "descriptor_sha256": sha(foundation),
            }]

        dependent = plugin_bytes(self.fixture.fragment, suffix="dependent_plan", mutation=depend)
        result, _ = self.plan((dependent, foundation))
        self.assertEqual(result.status, "planned", result.diagnostic)
        strategy = next(item for item in result.strategies if item.capability_id == "capability_dependent_plan")
        dependency = [item for item in strategy.prerequisites if item.kind == "descriptor_dependency"]
        self.assertEqual([item.object_sha256 for item in dependency], [sha(foundation)])
        contracts = [item.contract_id for item in strategy.prerequisites if item.kind == "contract"]
        self.assertIn("MH-C-EVIDENCE-001", contracts)
        self.assertIn("MH-C-RESOURCE-BUDGET-001", contracts)
        self.assertIn("MH-C-EXAMPLE-PRODUCER-001", contracts)
        self.assertIn("MH-C-EXAMPLE-CHECKER-001", contracts)

    def test_operation_and_capability_kinds_remain_data_only(self) -> None:
        cases = (
            ("construction", "solve"),
            ("decision", "plan_cost"),
            ("explanation", "explain"),
            ("verification", "check"),
        )
        for kind, operation in cases:
            with self.subTest(kind=kind, operation=operation):
                def mutate(value: dict[str, object]) -> None:
                    value["capabilities"][0]["kind"] = kind  # type: ignore[index]

                descriptor = plugin_bytes(
                    self.fixture.fragment,
                    suffix=f"{kind}_{operation}",
                    mutation=mutate,
                )
                changes: dict[str, object] = {
                    "capability_kind": kind,
                    "operation": operation,
                }
                if operation == "check":
                    changes["certificate_format"] = {
                        "format_id": "org.mathhead.certificate",
                        "major": 1,
                        "minor": 0,
                        "required_features": [],
                    }
                result, _ = self.plan(
                    (descriptor,),
                    request_changes=changes,
                )
                self.assertEqual(result.status, "planned", result.diagnostic)
                self.assertEqual(result.strategies[0].capability_kind, kind)
                self.assertEqual(result.strategies[0].operation, operation)
                self.assertFalse(result.strategies[0].mathematical_authority)

    def test_policy_request_and_result_reject_noncanonical_or_repaired_data(self) -> None:
        policy = make_planning_policy(mode="registry_order", maximum_strategies=7)
        self.assertTrue(planning_policy_bytes(policy).endswith(b"\n"))
        with self.assertRaises(DeterministicPlannerValidationError):
            make_planning_policy(mode="unknown")
        _result, inputs = self.plan()
        request = inputs[0]
        self.assertEqual(parse_planning_request(request).policy.mode, "registry_order")
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_request(request.rstrip(b"\n"))

        raw = json.loads(planning_result_bytes(plan_strategies(*inputs)))
        raw["strategies"][0]["transitions"][1]["target_strategy_sha256"] = "f" * 64
        self_hash(raw["strategies"][0]["transitions"][1], "transition_sha256")
        self_hash(raw["strategies"][0], "strategy_sha256")
        raw["entry_strategy_sha256"] = raw["strategies"][0]["strategy_sha256"]
        self_hash(raw, "result_sha256")
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(raw))

    def test_values_are_immutable_final_and_not_pickle_authority(self) -> None:
        result, _ = self.plan()
        with self.assertRaises(FrozenInstanceError):
            result.status = "unsupported"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            type("ForgedPlanningResult", (PlanningResult,), {})
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        with self.assertRaises(PermissionError):
            PlanningPolicy()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            copy.copy(result)

    def test_public_constructor_and_exact_type_boundaries(self) -> None:
        guarded = (
            PlanningResourceVector,
            PlanningPolicy,
            PlanningRequest,
            PlanningPrerequisite,
            PlanningEvidenceExpectation,
            PlanningResourceRequest,
            PlanningTransition,
            PlanningStrategy,
            PlanningResult,
        )
        for value_type in guarded:
            with self.subTest(value_type=value_type.__name__):
                with self.assertRaises(PermissionError):
                    value_type()  # type: ignore[call-arg]
        with self.assertRaises(DeterministicPlannerValidationError):
            planning_policy_bytes(object())  # type: ignore[arg-type]
        with self.assertRaises(DeterministicPlannerValidationError):
            planning_result_bytes(object())  # type: ignore[arg-type]
        with self.assertRaises(DeterministicPlannerValidationError):
            validate_planning_result(object())  # type: ignore[arg-type]

        _result, inputs = self.plan()
        request, route, descriptors, artifacts = inputs
        invalid_calls = (
            (bytearray(request), route, descriptors, artifacts),
            (request, bytearray(route), descriptors, artifacts),
            (request, route, list(descriptors), artifacts),
            (request, route, descriptors, list(artifacts)),
            (request, route, (object(),), artifacts),
            (request, route, descriptors, (*artifacts[:-1], object())),
        )
        for arguments in invalid_calls:
            with self.subTest(types=tuple(type(item).__name__ for item in arguments)):
                invalid = plan_strategies(*arguments)  # type: ignore[arg-type]
                self.assertEqual(invalid.status, "invalid")
                self.assertEqual(invalid.strategies, ())

    def test_request_codec_rejects_schema_identity_and_json_attacks(self) -> None:
        _result, inputs = self.plan()
        request = inputs[0]
        base = json.loads(request)

        def rejected(mutator) -> None:
            value = copy.deepcopy(base)
            mutator(value)
            if "request_sha256" in value:
                self_hash(value, "request_sha256")
            with self.assertRaises(DeterministicPlannerValidationError):
                parse_planning_request(canonical(value))

        rejected(lambda value: value.update(schema="mathhead.planning-request.v2"))
        rejected(lambda value: value.update(mathematical_authority=True))
        rejected(lambda value: value.update(resource_budget_contract_sha256="0" * 64))
        rejected(lambda value: value["resource_limits"].update(wall_time_us=True))
        rejected(lambda value: value["policy"].update(mode="unknown"))
        rejected(lambda value: value["policy"].update(policy_sha256="0" * 64))
        rejected(lambda value: value["route_request"].update(schema="mathhead.bad.v1"))
        rejected(lambda value: value.update(unknown=None))
        rejected(
            lambda value: value["resource_limits"].update(
                wall_time_us=planner_module.INTEGER_MAXIMUM + 1
            )
        )
        rejected(lambda value: value.update(route_result_sha256=""))
        rejected(lambda value: value.update(route_result_sha256="e\u0301"))
        rejected(lambda value: value.update(route_result_sha256="bad\x00digest"))

        malformed = (
            b"[]\n",
            b'{"duplicate":null,"duplicate":null}\n',
            b'{"float":1.5}\n',
            b'{"constant":NaN}\n',
            b"{not-json}\n",
            b"\xff",
        )
        for raw in malformed:
            with self.subTest(raw=raw):
                with self.assertRaises(DeterministicPlannerValidationError):
                    parse_planning_request(raw)

        with mock.patch.object(planner_module, "MAX_JSON_DEPTH", 1):
            with self.assertRaises(DeterministicPlannerValidationError):
                parse_planning_request(request)
        with mock.patch.object(planner_module, "MAX_JSON_NODES", 1):
            with self.assertRaises(DeterministicPlannerValidationError):
                parse_planning_request(request)
        with mock.patch.object(planner_module, "MAX_REQUEST_BYTES", 1):
            with self.assertRaises(DeterministicPlannerValidationError):
                parse_planning_request(request)
        with mock.patch.object(planner_module, "MAX_REQUEST_BYTES", 1):
            with self.assertRaises(DeterministicPlannerValidationError):
                planning_policy_bytes(make_planning_policy())

    def test_result_codec_rejects_repaired_structural_forgery(self) -> None:
        result, _inputs = self.plan(self.fixture.descriptors(2))
        base = json.loads(planning_result_bytes(result))

        def rehash_strategy(value: dict[str, object], index: int) -> None:
            self_hash(value["strategies"][index], "strategy_sha256")  # type: ignore[index]
            if index == 1:
                first = value["strategies"][0]  # type: ignore[index]
                for transition in first["transitions"]:  # type: ignore[index]
                    if transition["action"] == "fallback":
                        transition["target_strategy_sha256"] = value["strategies"][1][  # type: ignore[index]
                            "strategy_sha256"
                        ]
                        self_hash(transition, "transition_sha256")
                self_hash(first, "strategy_sha256")
                value["entry_strategy_sha256"] = first["strategy_sha256"]
            elif index == 0:
                value["entry_strategy_sha256"] = value["strategies"][0][  # type: ignore[index]
                    "strategy_sha256"
                ]
            self_hash(value, "result_sha256")

        for field in (
            "contract_sha256",
            "capability_registry_contract_sha256",
            "mathematical_authority",
        ):
            value = copy.deepcopy(base)
            value[field] = True if field == "mathematical_authority" else "0" * 64
            self_hash(value, "result_sha256")
            with self.subTest(field=field):
                with self.assertRaises(DeterministicPlannerValidationError):
                    parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        value["entry_strategy_sha256"] = "f" * 64
        self_hash(value, "result_sha256")
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        value["strategies"][1]["candidate_sha256"] = value["strategies"][0][  # type: ignore[index]
            "candidate_sha256"
        ]
        rehash_strategy(value, 1)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        resource = value["strategies"][0]["resource_request"]  # type: ignore[index]
        resource["requested"]["wall_time_us"] += 1  # type: ignore[index]
        self_hash(resource, "resource_request_sha256")
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        expectation = value["strategies"][0]["evidence_expectation"]  # type: ignore[index]
        expectation["producer_component_id"] = "forged_producer"
        self_hash(expectation, "expectation_sha256")
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        prerequisites = value["strategies"][0]["prerequisites"]  # type: ignore[index]
        prerequisites[0]["object_sha256"] = "e" * 64  # type: ignore[index]
        self_hash(prerequisites[0], "prerequisite_sha256")  # type: ignore[arg-type]
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        value["status"] = "unsupported"
        self_hash(value, "result_sha256")
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        value["status"] = "invalid"
        value["result_sha256"] = None
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        expectation = value["strategies"][0]["evidence_expectation"]  # type: ignore[index]
        expectation["independent_check_required"] = False
        self_hash(expectation, "expectation_sha256")
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        contracts = [
            item
            for item in value["strategies"][0]["prerequisites"]  # type: ignore[index]
            if item["kind"] == "contract"
        ]
        contracts[0]["contract_id"], contracts[-1]["contract_id"] = (
            contracts[-1]["contract_id"],
            contracts[0]["contract_id"],
        )
        self_hash(contracts[0], "prerequisite_sha256")
        self_hash(contracts[-1], "prerequisite_sha256")
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

        value = copy.deepcopy(base)
        transition = value["strategies"][0]["transitions"][1]  # type: ignore[index]
        transition["action"] = "stop"
        transition["target_strategy_sha256"] = None
        transition["terminal_state"] = "unsupported"
        self_hash(transition, "transition_sha256")
        rehash_strategy(value, 0)
        with self.assertRaises(DeterministicPlannerValidationError):
            parse_planning_result(canonical(value))

    def test_hash_seed_and_process_output_are_byte_identical(self) -> None:
        code = """
from tests.deterministic_planner.fixtures import PlannerFixture
from mathhead.deterministic_planner import plan_strategies, planning_result_bytes
fixture = PlannerFixture()
inputs = fixture.planning_inputs(fixture.descriptors(3))
print(planning_result_bytes(plan_strategies(*inputs)).hex())
"""
        outputs = []
        for seed in ("1", "987654"):
            environment = dict(**planner_module.__dict__.get("_TEST_ENV", {}))
            environment.update(
                PYTHONHASHSEED=seed,
                PYTHONPATH=os.pathsep.join((str(SRC), str(ROOT))),
            )
            completed = subprocess.run(
                [sys.executable, "-c", code],
                cwd=ROOT,
                env={**os.environ, **environment},
                check=True,
                capture_output=True,
                text=True,
            )
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_memory_and_process_control_exceptions_propagate(self) -> None:
        _result, inputs = self.plan()
        for exception in (MemoryError(), KeyboardInterrupt(), SystemExit()):
            with self.subTest(exception=type(exception).__name__):
                with mock.patch.object(planner_module, "route_capabilities", side_effect=exception):
                    with self.assertRaises(type(exception)):
                        plan_strategies(*inputs)


if __name__ == "__main__":
    unittest.main()
