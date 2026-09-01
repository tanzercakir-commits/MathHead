from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from threading import Event
import tempfile
from typing import Callable

from mathhead.deterministic_planner import (
    RESOURCE_DIMENSIONS,
    plan_strategies,
    planning_result_bytes,
)
from mathhead.proof_search_portfolio import (
    make_portfolio_execution_binding,
    make_proof_search_portfolio_request,
    parse_portfolio_execution_binding,
)
from mathhead.run_audit import RunAuditBundle, execute_audited_run
from tests.capability_registry.fixtures import plugin_bytes
from tests.deterministic_planner.fixtures import PlannerFixture
from tests.proof_search_portfolio.fixtures import (
    PortfolioFixture,
    emit_script,
    nonproduced_evidence_bytes,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ID = "MH-C-EXECUTION-DISPOSITION-001"
CONTRACT_PATH = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
CONTRACT_SHA256 = hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()
RESERVED_EXTENSION = "org.mathhead.execution-disposition"

INVOCATION_FIELDS = (
    "schema",
    "invocation_id",
    "planning_request_sha256",
    "route_result_sha256",
    "planning_result_sha256",
    "base_parent_budget_sha256",
    "descriptor_sha256s",
    "binding_sha256s",
    "artifact_bindings",
    "cancellation_armed",
    "mathematical_authority",
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


def invocation_projection(request: dict[str, object]) -> dict[str, object]:
    value = {name: copy.deepcopy(request[name]) for name in INVOCATION_FIELDS}
    value["schema"] = "mathhead.execution-disposition-invocation.v1"
    return value


def repair_request(
    value: dict[str, object],
    *,
    repair_invocation: bool = True,
    repair_intent: bool = True,
    repair_request_identity: bool = True,
) -> bytes:
    """Repair selected identities without repairing any other semantic relation."""
    if repair_invocation:
        value["invocation_sha256"] = sha(canonical(invocation_projection(value)))
    intent = value.get("cancellation_intent")
    if type(intent) is dict and repair_intent:
        intent["invocation_sha256"] = value["invocation_sha256"]
        self_hash(intent, "intent_sha256")
    if repair_request_identity:
        self_hash(value, "request_sha256")
    return canonical(value)


def changed_request(
    raw: bytes,
    mutate: Callable[[dict[str, object]], None],
    *,
    repair_invocation: bool = True,
    repair_intent: bool = True,
    repair_request_identity: bool = True,
) -> bytes:
    value = json.loads(raw)
    mutate(value)
    return repair_request(
        value,
        repair_invocation=repair_invocation,
        repair_intent=repair_intent,
        repair_request_identity=repair_request_identity,
    )


def anchored_budget(base_parent_budget: bytes, request_sha256: str) -> bytes:
    value = json.loads(base_parent_budget)
    extensions = value["extensions"]
    if type(extensions) is not dict or RESERVED_EXTENSION in extensions:
        raise AssertionError("fixture base budget does not have a free extension slot")
    extensions[RESERVED_EXTENSION] = {
        "disposition_request_sha256": request_sha256,
    }
    return canonical(value)


def strip_anchor(raw: bytes) -> bytes:
    value = json.loads(raw)
    del value["extensions"][RESERVED_EXTENSION]
    return canonical(value)


def make_disposition_request(
    *,
    planning_request: bytes,
    route_result: bytes,
    planning_result: bytes,
    base_parent_budget: bytes | None,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[tuple[str, bytes], ...],
    invocation_id: str = "invocation_execution_disposition_fixture",
    origin_source: str | None = None,
    reason_code: str = "requested",
) -> tuple[bytes, dict[str, object]]:
    armed = origin_source is not None
    request: dict[str, object] = {
        "schema": "mathhead.execution-disposition-request.v1",
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "invocation_id": invocation_id,
        "planning_request_sha256": sha(planning_request),
        "route_result_sha256": sha(route_result),
        "planning_result_sha256": sha(planning_result),
        "base_parent_budget_sha256": (
            None if base_parent_budget is None else sha(base_parent_budget)
        ),
        "descriptor_sha256s": sorted({sha(raw) for raw in descriptors}),
        "binding_sha256s": [sha(raw) for raw in bindings],
        "artifact_bindings": [
            {"role": role, "sha256": sha(raw), "byte_count": len(raw)}
            for role, raw in artifacts
        ],
        "cancellation_armed": armed,
        "cancellation_intent": None,
        "invocation_sha256": None,
        "request_sha256": None,
        "mathematical_authority": False,
    }
    request["invocation_sha256"] = sha(canonical(invocation_projection(request)))
    if armed:
        if base_parent_budget is None:
            raise AssertionError("an armed fixture requires a base parent budget")
        intent: dict[str, object] = {
            "schema": "mathhead.cancellation-intent.v1",
            "intent_id": f"intent_{invocation_id}",
            "origin_source": origin_source,
            "reason_code": reason_code,
            "invocation_id": invocation_id,
            "invocation_sha256": request["invocation_sha256"],
            "base_parent_budget_sha256": request["base_parent_budget_sha256"],
            "policy_contract_id": CONTRACT_ID,
            "policy_contract_sha256": CONTRACT_SHA256,
            "intent_sha256": None,
            "mathematical_authority": False,
        }
        self_hash(intent, "intent_sha256")
        request["cancellation_intent"] = intent
    self_hash(request, "request_sha256")
    return canonical(request), request


@dataclass(frozen=True)
class DispositionInputs:
    request: bytes
    request_value: dict[str, object]
    planning_request: bytes
    route_result: bytes
    planning_result: bytes
    base_parent_budget: bytes | None
    descriptors: tuple[bytes, ...]
    bindings: tuple[bytes, ...]
    artifacts: tuple[tuple[str, bytes], ...]
    executable_paths: tuple[tuple[str, str], ...]
    workspace_root: str | None
    cancel_event: Event | None

    @property
    def call_arguments(self) -> tuple[object, ...]:
        return (
            self.request,
            self.planning_request,
            self.route_result,
            self.planning_result,
            self.base_parent_budget,
            self.descriptors,
            self.bindings,
            self.artifacts,
            self.executable_paths,
            self.workspace_root,
            self.cancel_event,
        )


class EarlyFixture:
    """A fresh governed route/planner outcome that must not execute work."""

    def __init__(self, kind: str = "unsupported_environment") -> None:
        base = PlannerFixture()
        if kind == "unsupported_environment":
            descriptors: tuple[bytes, ...] = ()
            inputs = base.planning_inputs(descriptors)
        elif kind == "unsupported_input":
            descriptor = plugin_bytes(
                base.fragment,
                suffix="disposition_structural_refusal",
                mutation=lambda value: value["capabilities"][0]["fragment"].update(
                    domains=["real"]
                ),
            )
            descriptors = (descriptor,)
            inputs = base.planning_inputs(descriptors)
        elif kind == "planning_exhausted":
            descriptors = (base.descriptor,)
            inputs = base.planning_inputs(
                descriptors,
                limits={name: 0 for name in RESOURCE_DIMENSIONS},
            )
        else:
            raise ValueError(f"unknown early fixture kind: {kind}")
        planning_request, route_result, selected, artifact_bytes = inputs
        plan = plan_strategies(*inputs)
        planning_result = planning_result_bytes(plan)
        artifacts = tuple(
            (f"input_{index}", raw) for index, raw in enumerate(artifact_bytes)
        )
        request, request_value = make_disposition_request(
            planning_request=planning_request,
            route_result=route_result,
            planning_result=planning_result,
            base_parent_budget=None,
            descriptors=selected,
            bindings=(),
            artifacts=artifacts,
            invocation_id=f"invocation_{kind}",
        )
        self.kind = kind
        self.route_status = json.loads(route_result)["status"]
        self.planning_status = plan.status
        self.inputs = DispositionInputs(
            request=request,
            request_value=request_value,
            planning_request=planning_request,
            route_result=route_result,
            planning_result=planning_result,
            base_parent_budget=None,
            descriptors=selected,
            bindings=(),
            artifacts=artifacts,
            executable_paths=(),
            workspace_root=None,
            cancel_event=None,
        )


class PlannedFixture:
    """One fully bound planned invocation suitable for mocked audited execution."""

    def __init__(
        self,
        *,
        claim: str = "proved",
        agreement: bool = True,
        certificate_status: str = "verified",
        evidence_status: str | None = None,
        malformed_evidence: bool = False,
        producer_exit: int | None = None,
        origin_source: str | None = None,
        event_set: bool = False,
    ) -> None:
        source = PortfolioFixture(
            claim=claim,
            agreement=agreement,
            certificate_status=certificate_status,
        )
        planning_request, route_result, descriptors, artifact_bytes = (
            source.base.planning_inputs(
                (source.descriptor,),
                availability_changes={"allowed_effects": ("process",)},
            )
        )
        if descriptors != (source.descriptor,) or artifact_bytes != source.base.artifacts:
            raise AssertionError("neighboring planner fixture is not deterministic")
        artifacts = source.input_pairs
        binding = source.binding
        producer_overrides = sum(
            item is not None and item is not False
            for item in (evidence_status, malformed_evidence, producer_exit)
        )
        if producer_overrides > 1:
            raise ValueError("select only one producer outcome override")
        if producer_overrides:
            parsed = parse_portfolio_execution_binding(binding)
            if evidence_status is not None:
                producer_payload = nonproduced_evidence_bytes(
                    source.strategy,
                    source.descriptor,
                    evidence_status,
                )
                producer_arguments = ("-I", "-S", "-c", emit_script(producer_payload))
            elif malformed_evidence:
                producer_arguments = (
                    "-I",
                    "-S",
                    "-c",
                    emit_script(b"not-canonical-evidence"),
                )
            else:
                producer_arguments = (
                    "-I",
                    "-S",
                    "-c",
                    f"raise SystemExit({producer_exit})",
                )
            binding = make_portfolio_execution_binding(
                plan_order=parsed.plan_order,
                strategy_sha256=parsed.strategy_sha256,
                descriptor_sha256=parsed.descriptor_sha256,
                producer_component_id=parsed.producer_component_id,
                checker_component_id=parsed.checker_component_id,
                producer_family=parsed.producer_family,
                checker_family=parsed.checker_family,
                producer_executable=source.executable_bytes,
                checker_executable=source.executable_bytes,
                producer_arguments=producer_arguments,
                checker_arguments=parsed.checker_arguments,
                input_artifacts=artifacts,
            )
        cancel_event = Event() if origin_source is not None else None
        if cancel_event is not None and event_set:
            cancel_event.set()
        request, request_value = make_disposition_request(
            planning_request=planning_request,
            route_result=route_result,
            planning_result=source.plan_bytes,
            base_parent_budget=source.parent,
            descriptors=descriptors,
            bindings=(binding,),
            artifacts=artifacts,
            invocation_id=(
                "invocation_planned_unarmed"
                if origin_source is None
                else f"invocation_planned_{origin_source}"
            ),
            origin_source=origin_source,
        )
        self.source = source
        self.binding = binding
        self.expected_anchor = anchored_budget(
            source.parent, str(request_value["request_sha256"])
        )
        self.inputs = DispositionInputs(
            request=request,
            request_value=request_value,
            planning_request=planning_request,
            route_result=route_result,
            planning_result=source.plan_bytes,
            base_parent_budget=source.parent,
            descriptors=descriptors,
            bindings=(binding,),
            artifacts=artifacts,
            executable_paths=source.executable_paths,
            workspace_root=str(ROOT),
            cancel_event=cancel_event,
        )

    def portfolio_request(self) -> bytes:
        return make_proof_search_portfolio_request(
            planning_result=self.inputs.planning_result,
            parent_budget=self.expected_anchor,
            descriptors=self.inputs.descriptors,
            bindings=self.inputs.bindings,
            artifacts=self.inputs.artifacts,
        )

    def audited_bundle(self) -> RunAuditBundle:
        """Produce exact governed evidence once for tests that mock the outer call."""
        with tempfile.TemporaryDirectory(
            prefix="mathhead-execution-disposition-fixture-",
            dir=ROOT,
        ) as workspace:
            return execute_audited_run(
                self.inputs.planning_request,
                self.inputs.route_result,
                self.portfolio_request(),
                self.inputs.planning_result,
                self.expected_anchor,
                self.inputs.descriptors,
                self.inputs.bindings,
                tuple(raw for _, raw in self.inputs.artifacts),
                self.inputs.executable_paths,
                workspace,
                self.inputs.cancel_event,
            )
