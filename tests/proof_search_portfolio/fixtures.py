from __future__ import annotations

import copy
import base64
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
import zlib

from mathhead.deterministic_planner import PlanningStrategy, plan_strategies, planning_result_bytes
from mathhead.proof_search_portfolio import (
    make_portfolio_execution_binding,
    make_proof_search_portfolio_request,
)
from tests.capability_registry.fixtures import plugin_bytes
from tests.deterministic_planner.fixtures import PlannerFixture, canonical, self_hash
from tests.isolated_worker.test_isolated_worker import parent_budget
from tools.validate_evidence_certificate_contracts import (
    certificate_replay_basis_sha256,
    evidence_generation_basis_sha256,
    minimal_certificate,
    minimal_evidence,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def emit_script(data: bytes) -> str:
    payload = base64.b85encode(zlib.compress(data, 9)).decode("ascii")
    return (
        "import base64,zlib,sys;"
        f"sys.stdout.buffer.write(zlib.decompress(base64.b85decode({payload!r})))"
    )


def process_descriptor(
    fixture: PlannerFixture,
    *,
    suffix: str = "portfolio",
    base_cost: int = 1_000_000,
) -> bytes:
    def mutate(value: dict[str, Any]) -> None:
        value["effects"][3].update(
            mode="declared",
            policy_id="org.mathhead.process-policy",
            reason="proof search portfolio fixture",
        )
        value["operations"][1]["effect_kinds"] = ["process"]
        value["lifecycle"].update(
            isolation="subprocess_required",
            shutdown_timeout_us=30_000_000,
        )

    return plugin_bytes(
        fixture.fragment,
        suffix=suffix,
        base_cost=base_cost,
        mutation=mutate,
    )


def evidence_bytes(strategy: PlanningStrategy, descriptor: bytes, claim: str) -> bytes:
    plugin = json.loads(descriptor)
    value = copy.deepcopy(minimal_evidence())
    value["evidence_id"] = f"evidence_{strategy.plan_order}"
    value["subject"].update(
        kind="obligation",
        subject_id=f"obligation_{strategy.plan_order}",
        statement_sha256=strategy.obligation_semantic_sha256,
        obligation_sha256s=[strategy.obligation_semantic_sha256],
    )
    expected = dict(strategy.evidence_expectation.evidence_format.entries)
    value["format"].update(
        format_id=expected["format_id"],
        major=expected["major"],
        minor=expected["minor"],
        version=f"{expected['major']}.{expected['minor']}.0",
        features=list(expected["required_features"]),
        kind="proof" if claim == "proved" else "counterexample",
    )
    producer = plugin["components"]["producer"]
    value["producer"] = {
        **producer,
        "environment_contract_sha256": plugin["implementation"]["environment_contract_sha256"],
    }
    value["generation"].update(
        configuration_sha256=producer["configuration_sha256"],
        input_sha256=sha(canonical(value["subject"])),
    )
    value["extensions"] = {"org.mathhead.portfolio.claim": claim}
    value["generation"]["basis_sha256"] = evidence_generation_basis_sha256(value)
    return canonical(value)


def nonproduced_evidence_bytes(
    strategy: PlanningStrategy,
    descriptor: bytes,
    status: str,
) -> bytes:
    value = json.loads(evidence_bytes(strategy, descriptor, "proved"))
    value["extensions"] = {}
    diagnostic_id = "diagnostic_producer"
    value["diagnostics"] = [
        {
            "diagnostic_id": diagnostic_id,
            "severity": "error" if status == "error" else "warning",
            "code": "org.mathhead.producer-outcome",
            "message": f"producer returned {status}",
            "related_payload_ids": [],
            "details": {},
        }
    ]
    common = {"status": status, "diagnostic_ids": [diagnostic_id]}
    value["outcome"] = {
        "unsupported": {
            **common,
            "unsupported_features": ["org.mathhead.unsupported-feature"],
            "reason": "producer does not support the obligation",
        },
        "incomplete": {**common, "reason": "producer is inconclusive"},
        "cancelled": {
            **common,
            "cancellation_id": "cancel_producer",
            "reason": "producer was cancelled",
        },
        "exhausted": {
            **common,
            "dimensions": ["wall_time_us"],
            "reason": "producer budget exhausted",
        },
        "truncated": {
            **common,
            "truncation_ids": ["truncation_producer"],
            "retained_payload_ids": ["payload_proof"],
            "reason": "producer output truncated",
        },
        "error": {
            **common,
            "error_code": "org.mathhead.producer-error",
            "reason": "producer failed",
        },
    }[status]
    value["budget"]["outcome"] = status if status in {"cancelled", "exhausted", "truncated"} else "completed"
    return canonical(value)


def checker_envelope(
    strategy: PlanningStrategy,
    descriptor: bytes,
    evidence: bytes,
    claim: str,
    *,
    agreement: bool = True,
    certificate_status: str = "verified",
) -> bytes:
    plugin = json.loads(descriptor)
    evidence_value = json.loads(evidence)
    certificate = copy.deepcopy(minimal_certificate(evidence_value))
    checker = plugin["components"]["checker"]
    certificate["certificate_id"] = f"certificate_{strategy.plan_order}"
    certificate["checker"] = {
        **checker,
        "environment_contract_sha256": plugin["implementation"]["environment_contract_sha256"],
    }
    for artifact in certificate["verification_artifacts"]:
        artifact["producer_component_id"] = checker["component_id"]
    certificate_format = plugin["capabilities"][0]["certificate_formats"][0]
    certificate["format"].update(
        format_id=certificate_format["format_id"],
        major=certificate_format["major"],
        minor=certificate_format["minor_minimum"],
        version=f"{certificate_format['major']}.{certificate_format['minor_minimum']}.0",
        features=list(certificate_format["required_features"]),
    )
    certificate["replay"].update(
        attempt_id=f"checker_attempt_{strategy.plan_order}",
        configuration_sha256=checker["configuration_sha256"],
    )
    trust = {
        "checker_contract": (checker["contract_id"], checker["contract_sha256"]),
        "checker_implementation": (checker["component_id"], checker["implementation_sha256"]),
        "checker_configuration": (checker["component_id"], checker["configuration_sha256"]),
        "environment_contract": (
            "MH-C-ENV-002",
            plugin["implementation"]["environment_contract_sha256"],
        ),
        "problem_ir": ("ProblemIR", certificate["subject"]["problem_ir_sha256"]),
        "theory_context": ("TheoryContext", certificate["subject"]["theory_context_sha256"]),
        "evidence": (evidence_value["evidence_id"], sha(evidence)),
    }
    certificate["trust_dependencies"] = [
        {"kind": kind, "identifier": identifier, "sha256": digest}
        for kind, (identifier, digest) in sorted(trust.items())
    ]
    if certificate_status != "verified":
        diagnostic = {
            "diagnostic_id": "diagnostic_checker",
            "severity": "error" if certificate_status in {"verifier_failed", "disagreement"} else "warning",
            "code": "org.mathhead.checker-outcome",
            "message": f"checker returned {certificate_status}",
            "related_artifact_ids": ["artifact_checker_result"],
            "details": {},
        }
        certificate["diagnostics"] = [diagnostic]
        common = {"status": certificate_status, "diagnostic_ids": ["diagnostic_checker"]}
        certificate["verdict"] = {
            "invalid": {
                **common,
                "reason_code": "semantic_failure",
                "checker_result_artifact_id": "artifact_checker_result",
                "reason": "candidate is invalid",
            },
            "unsupported": {
                **common,
                "unsupported_features": ["org.mathhead.unsupported-feature"],
                "reason": "checker format is unsupported",
            },
            "inconclusive": {**common, "reason": "checker could not decide"},
            "cancelled": {
                **common,
                "cancellation_id": "cancel_checker",
                "reason": "checker was cancelled",
            },
            "exhausted": {
                **common,
                "dimensions": ["wall_time_us"],
                "reason": "checker budget exhausted",
            },
            "truncated": {
                **common,
                "truncation_ids": ["truncation_checker"],
                "reason": "checker output truncated",
            },
            "verifier_failed": {
                **common,
                "error_code": "org.mathhead.verifier-failed",
                "reason": "checker failed",
            },
            "disagreement": {
                **common,
                "conflicting_artifact_ids": ["artifact_checker_result", "artifact_replay_log"],
                "reason": "checker artifacts disagree",
            },
        }[certificate_status]
        certificate["budget"]["outcome"] = (
            certificate_status
            if certificate_status in {"cancelled", "exhausted", "truncated"}
            else "completed"
        )
    certificate["replay"]["basis_sha256"] = certificate_replay_basis_sha256(certificate)
    certificate_raw = canonical(certificate)
    decision: dict[str, object] = {
        "schema": "mathhead.portfolio-checker-decision.v1",
        "strategy_sha256": strategy.strategy_sha256,
        "producer_component_id": strategy.producer_component_id,
        "checker_component_id": strategy.checker_component_id,
        "subject_sha256": sha(canonical(evidence_value["subject"])),
        "claim": claim,
        "evidence_sha256": sha(evidence),
        "evidence_bytes": len(evidence),
        "certificate_sha256": sha(certificate_raw),
        "certificate_bytes": len(certificate_raw),
        "certificate_verdict": "invalid" if certificate_status == "disagreement" else certificate_status,
        "certificate_authority": "checker_attested" if certificate_status == "verified" else "none",
        "agreement": agreement if certificate_status == "verified" else False,
        "reason_code": (
            "CHECKER_AGREED"
            if certificate_status == "verified" and agreement
            else "CHECKER_DISAGREED"
            if certificate_status in {"verified", "disagreement"}
            else "CHECKER_REJECTED"
            if certificate_status == "invalid"
            else "CERTIFICATE_INVALID"
            if certificate_status == "verifier_failed"
            else "CHECKER_INCONCLUSIVE"
        ),
        "decision_sha256": None,
        "mathematical_authority": False,
    }
    self_hash(decision, "decision_sha256")
    return canonical({"certificate": certificate, "decision": decision})


class PortfolioFixture:
    def __init__(
        self,
        *,
        claim: str = "proved",
        agreement: bool = True,
        certificate_status: str = "verified",
    ) -> None:
        self.base = PlannerFixture()
        self.descriptor = process_descriptor(self.base)
        inputs = self.base.planning_inputs(
            (self.descriptor,),
            availability_changes={"allowed_effects": ("process",)},
        )
        self.plan = plan_strategies(*inputs)
        if self.plan.status != "planned":
            raise AssertionError(self.plan)
        self.plan_bytes = planning_result_bytes(self.plan)
        self.strategy = self.plan.strategies[0]
        self.evidence = evidence_bytes(self.strategy, self.descriptor, claim)
        self.envelope = checker_envelope(
            self.strategy,
            self.descriptor,
            self.evidence,
            claim,
            agreement=agreement,
            certificate_status=certificate_status,
        )
        self.executable = Path(sys.executable).resolve(strict=True)
        self.executable_bytes = self.executable.read_bytes()
        self.input_pairs = tuple(
            (f"input_{index}", raw) for index, raw in enumerate(self.base.artifacts)
        )
        self.binding = make_portfolio_execution_binding(
            plan_order=0,
            strategy_sha256=self.strategy.strategy_sha256,
            descriptor_sha256=self.strategy.descriptor_sha256,
            producer_component_id=self.strategy.producer_component_id,
            checker_component_id=self.strategy.checker_component_id,
            producer_family="external",
            checker_family="external",
            producer_executable=self.executable_bytes,
            checker_executable=self.executable_bytes,
            producer_arguments=(
                "-I", "-S", "-c",
                emit_script(self.evidence),
            ),
            checker_arguments=(
                "-I", "-S", "-c",
                emit_script(self.envelope),
            ),
            input_artifacts=self.input_pairs,
        )
        limits = {
            name: getattr(self.strategy.resource_request.requested, name)
            for name in (
                "wall_time_us", "cpu_time_us", "memory_bytes", "solver_calls",
                "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes",
                "diagnostic_bytes", "nesting_depth",
            )
        }
        self.parent = parent_budget(limits, scale=4)
        self.request = make_proof_search_portfolio_request(
            planning_result=self.plan_bytes,
            parent_budget=self.parent,
            descriptors=(self.descriptor,),
            bindings=(self.binding,),
            artifacts=self.input_pairs,
        )

    @property
    def executable_paths(self) -> tuple[tuple[str, str], ...]:
        return ((sha(self.executable_bytes), str(self.executable)),)


class FallbackPortfolioFixture:
    def __init__(self, *, first_claim: str | None = None) -> None:
        self.base = PlannerFixture()
        descriptors = (
            process_descriptor(self.base, suffix="portfolio_first", base_cost=1_000_000),
            process_descriptor(self.base, suffix="portfolio_second", base_cost=1_000_000),
        )
        inputs = self.base.planning_inputs(
            descriptors,
            availability_changes={"allowed_effects": ("process",)},
        )
        self.plan = plan_strategies(*inputs)
        if self.plan.status != "planned" or len(self.plan.strategies) != 2:
            raise AssertionError(self.plan)
        self.plan_bytes = planning_result_bytes(self.plan)
        by_digest = {sha(item): item for item in descriptors}
        self.descriptors = tuple(by_digest[item.descriptor_sha256] for item in self.plan.strategies)
        self.executable = Path(sys.executable).resolve(strict=True)
        self.executable_bytes = self.executable.read_bytes()
        self.input_pairs = tuple(
            (f"input_{index}", raw) for index, raw in enumerate(self.base.artifacts)
        )
        bindings: list[bytes] = []
        for index, strategy in enumerate(self.plan.strategies):
            descriptor = by_digest[strategy.descriptor_sha256]
            claim = first_claim if index == 0 and first_claim is not None else "refuted"
            evidence = evidence_bytes(strategy, descriptor, claim)
            envelope = checker_envelope(strategy, descriptor, evidence, claim)
            producer_payload = b"not-canonical-evidence" if index == 0 and first_claim is None else evidence
            bindings.append(
                make_portfolio_execution_binding(
                    plan_order=index,
                    strategy_sha256=strategy.strategy_sha256,
                    descriptor_sha256=strategy.descriptor_sha256,
                    producer_component_id=strategy.producer_component_id,
                    checker_component_id=strategy.checker_component_id,
                    producer_family="external",
                    checker_family="external",
                    producer_executable=self.executable_bytes,
                    checker_executable=self.executable_bytes,
                    producer_arguments=("-I", "-S", "-c", emit_script(producer_payload)),
                    checker_arguments=("-I", "-S", "-c", emit_script(envelope)),
                    input_artifacts=self.input_pairs,
                )
            )
        self.bindings = tuple(bindings)
        peak_limits = {
            name: max(getattr(strategy.resource_request.requested, name) for strategy in self.plan.strategies)
            for name in (
                "wall_time_us", "cpu_time_us", "memory_bytes", "solver_calls",
                "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes",
                "diagnostic_bytes", "nesting_depth",
            )
        }
        self.parent = parent_budget(peak_limits, scale=8)
        self.request = make_proof_search_portfolio_request(
            planning_result=self.plan_bytes,
            parent_budget=self.parent,
            descriptors=self.descriptors,
            bindings=self.bindings,
            artifacts=self.input_pairs,
        )

    @property
    def executable_paths(self) -> tuple[tuple[str, str], ...]:
        return ((sha(self.executable_bytes), str(self.executable)),)
