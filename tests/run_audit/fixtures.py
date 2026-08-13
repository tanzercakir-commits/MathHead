from __future__ import annotations

from dataclasses import dataclass
from threading import Event
import tempfile

from mathhead.proof_search_portfolio import (
    make_portfolio_execution_binding,
    make_proof_search_portfolio_request,
    parse_portfolio_execution_binding,
)
from mathhead.run_audit import RunAuditBundle, execute_audited_run
from tests.proof_search_portfolio.fixtures import (
    FallbackPortfolioFixture,
    PortfolioFixture,
    emit_script,
    nonproduced_evidence_bytes,
)


@dataclass(frozen=True)
class AuditedFixture:
    source: object
    planning_request: bytes
    route_result: bytes
    bundle: RunAuditBundle


def single_bundle(
    *,
    claim: str = "proved",
    agreement: bool = True,
    certificate_status: str = "verified",
    evidence_status: str | None = None,
    malformed_evidence: bool = False,
    producer_exit: int | None = None,
    cancel_event: Event | None = None,
) -> AuditedFixture:
    fixture = PortfolioFixture(
        claim=claim,
        agreement=agreement,
        certificate_status=certificate_status,
    )
    binding = fixture.binding
    request = fixture.request
    if evidence_status is not None or malformed_evidence or producer_exit is not None:
        parsed = parse_portfolio_execution_binding(binding)
        if evidence_status is not None:
            payload = nonproduced_evidence_bytes(
                fixture.strategy,
                fixture.descriptor,
                evidence_status,
            )
            arguments = ("-I", "-S", "-c", emit_script(payload))
        elif malformed_evidence:
            arguments = ("-I", "-S", "-c", emit_script(b"not-canonical-evidence"))
        else:
            arguments = ("-I", "-S", "-c", f"raise SystemExit({producer_exit})")
        binding = make_portfolio_execution_binding(
            plan_order=parsed.plan_order,
            strategy_sha256=parsed.strategy_sha256,
            descriptor_sha256=parsed.descriptor_sha256,
            producer_component_id=parsed.producer_component_id,
            checker_component_id=parsed.checker_component_id,
            producer_family=parsed.producer_family,
            checker_family=parsed.checker_family,
            producer_executable=fixture.executable_bytes,
            checker_executable=fixture.executable_bytes,
            producer_arguments=arguments,
            checker_arguments=parsed.checker_arguments,
            input_artifacts=fixture.input_pairs,
        )
        request = make_proof_search_portfolio_request(
            planning_result=fixture.plan_bytes,
            parent_budget=fixture.parent,
            descriptors=(fixture.descriptor,),
            bindings=(binding,),
            artifacts=fixture.input_pairs,
        )
    planning_request, route_result, _descriptors, artifacts = fixture.base.planning_inputs(
        (fixture.descriptor,), availability_changes={"allowed_effects": ("process",)}
    )
    with tempfile.TemporaryDirectory(prefix="mathhead-run-audit-fixture-") as workspace:
        bundle = execute_audited_run(
            planning_request,
            route_result,
            request,
            fixture.plan_bytes,
            fixture.parent,
            (fixture.descriptor,),
            (binding,),
            artifacts,
            fixture.executable_paths,
            workspace,
            cancel_event,
        )
    return AuditedFixture(fixture, planning_request, route_result, bundle)


def success_bundle(*, claim: str = "proved", agreement: bool = True) -> AuditedFixture:
    return single_bundle(claim=claim, agreement=agreement)


def fallback_bundle() -> AuditedFixture:
    fixture = FallbackPortfolioFixture()
    planning_request, route_result, _descriptors, artifacts = fixture.base.planning_inputs(
        fixture.descriptors, availability_changes={"allowed_effects": ("process",)}
    )
    request = make_proof_search_portfolio_request(
        planning_result=fixture.plan_bytes,
        parent_budget=fixture.parent,
        descriptors=fixture.descriptors,
        bindings=fixture.bindings,
        artifacts=fixture.input_pairs,
    )
    with tempfile.TemporaryDirectory(prefix="mathhead-run-audit-fixture-") as workspace:
        bundle = execute_audited_run(
            planning_request,
            route_result,
            request,
            fixture.plan_bytes,
            fixture.parent,
            fixture.descriptors,
            fixture.bindings,
            artifacts,
            fixture.executable_paths,
            workspace,
        )
    return AuditedFixture(fixture, planning_request, route_result, bundle)
