from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.execution_disposition.fixtures import (  # noqa: E402
    PlannedFixture,
    anchored_budget,
    canonical,
    make_disposition_request,
    self_hash,
    sha,
)
from tests.proof_search_portfolio.fixtures import (  # noqa: E402
    canonical as portfolio_canonical,
    emit_script,
)


@dataclass(frozen=True)
class ExpectedGraph:
    cause: str
    disposition: str
    phase: str
    precedence_row: str
    precedence_rank: int
    attempt_outcome: str | None
    producer_status: str | None
    producer_reason: str | None
    checker_status: str | None
    checker_reason: str | None
    terminal_state: str
    portfolio_relation: str = "exact"
    outcome_kind: str | None = None
    diagnostic: str | None = None
    dimensions: tuple[str, ...] | None = ()


@dataclass(frozen=True)
class PairRow:
    status: str
    reason: str
    variants: tuple[ExpectedGraph, ...]


def graph(
    cause: str,
    disposition: str,
    phase: str,
    precedence_row: str,
    precedence_rank: int,
    attempt_outcome: str | None,
    producer_status: str | None,
    producer_reason: str | None,
    checker_status: str | None,
    checker_reason: str | None,
    terminal_state: str,
    *,
    outcome_kind: str | None = None,
    diagnostic: str | None = None,
    dimensions: tuple[str, ...] | None = (),
) -> ExpectedGraph:
    return ExpectedGraph(
        cause,
        disposition,
        phase,
        precedence_row,
        precedence_rank,
        attempt_outcome,
        producer_status,
        producer_reason,
        checker_status,
        checker_reason,
        terminal_state,
        outcome_kind=outcome_kind,
        diagnostic=diagnostic,
        dimensions=dimensions,
    )


def row(status: str, reason: str, *variants: ExpectedGraph) -> PairRow:
    return PairRow(status, reason, variants)


def producer_worker(
    cause: str,
    disposition: str,
    precedence_row: str,
    rank: int,
    outcome: str,
    worker_status: str,
    worker_reason: str,
    terminal: str,
    *,
    phase: str = "producer",
    outcome_kind: str | None = None,
    diagnostic: str | None = None,
    dimensions: tuple[str, ...] | None = (),
) -> ExpectedGraph:
    return graph(
        cause,
        disposition,
        phase,
        precedence_row,
        rank,
        outcome,
        worker_status,
        worker_reason,
        "not_started",
        "NOT_STARTED",
        terminal,
        outcome_kind=outcome_kind,
        diagnostic=diagnostic,
        dimensions=dimensions,
    )


def checker_worker(
    cause: str,
    disposition: str,
    precedence_row: str,
    rank: int,
    outcome: str,
    worker_status: str,
    worker_reason: str,
    terminal: str,
    *,
    phase: str = "checker",
    outcome_kind: str | None = None,
    diagnostic: str | None = None,
    dimensions: tuple[str, ...] | None = (),
) -> ExpectedGraph:
    return graph(
        cause,
        disposition,
        phase,
        precedence_row,
        rank,
        outcome,
        "completed",
        "COMPLETED",
        worker_status,
        worker_reason,
        terminal,
        outcome_kind=outcome_kind,
        diagnostic=diagnostic,
        dimensions=dimensions,
    )


CHECKED_PROOF = checker_worker(
    "checked_proof", "completed", "30_checked_terminal", 30,
    "success", "completed", "COMPLETED", "succeeded", phase="completed",
)
CHECKED_REFUTATION = replace(CHECKED_PROOF, cause="checked_refutation")


# This is an independent, literal oracle.  It is deliberately not loaded from a
# JSON schema and does not call an execution-disposition production helper.
PAIR_ORACLE: tuple[PairRow, ...] = (
    row("succeeded", "CHECKED_PROOF", CHECKED_PROOF),
    row("succeeded", "CHECKED_REFUTATION", CHECKED_REFUTATION),
    row(
        "unsupported", "ISOLATION_UNSUPPORTED",
        producer_worker(
            "unsupported_execution_environment", "refused",
            "60_environment_refusal", 60, "unsupported", "unsupported",
            "ISOLATION_UNSUPPORTED", "unsupported",
        ),
    ),
    row(
        "unsupported", "EVIDENCE_UNSUPPORTED",
        producer_worker(
            "producer_refusal", "refused", "70_component_refusal", 70,
            "unsupported", "completed", "COMPLETED", "unsupported",
        ),
    ),
    row(
        "exhausted", "BUDGET_INSUFFICIENT",
        producer_worker(
            "budget_exhaustion", "exhausted", "50_ledger_exhaustion", 50,
            "exhausted", "refused", "BUDGET_INSUFFICIENT", "exhausted",
            dimensions=None,
        ),
        checker_worker(
            "budget_exhaustion", "exhausted", "50_ledger_exhaustion", 50,
            "exhausted", "refused", "BUDGET_INSUFFICIENT", "exhausted",
            dimensions=None,
        ),
    ),
    *tuple(
        row(
            "exhausted", reason,
            producer_worker(
                "budget_exhaustion", "exhausted", "50_ledger_exhaustion", 50,
                "exhausted", "exhausted", reason, "exhausted",
                dimensions=(dimension,),
            ),
            checker_worker(
                "budget_exhaustion", "exhausted", "50_ledger_exhaustion", 50,
                "exhausted", "exhausted", reason, "exhausted",
                dimensions=(dimension,),
            ),
        )
        for reason, dimension in (
            ("WALL_TIME_EXHAUSTED", "wall_time_us"),
            ("CPU_TIME_EXHAUSTED", "cpu_time_us"),
            ("MEMORY_EXHAUSTED", "memory_bytes"),
            ("OUTPUT_EXHAUSTED", "output_bytes"),
            ("DIAGNOSTIC_EXHAUSTED", "diagnostic_bytes"),
        )
    ),
    row(
        "exhausted", "EVIDENCE_EXHAUSTED",
        producer_worker(
            "producer_refusal", "refused", "70_component_refusal", 70,
            "exhausted", "completed", "COMPLETED", "exhausted",
        ),
    ),
    row(
        "exhausted", "CHECKER_EXHAUSTED",
        checker_worker(
            "verifier_refusal", "refused", "70_component_refusal", 70,
            "exhausted", "completed", "COMPLETED", "exhausted",
        ),
    ),
    row(
        "cancelled", "CANCELLED",
        *tuple(
            worker
            for source in ("user", "parent", "supervisor")
            for worker in (
                producer_worker(
                    f"{source}_cancellation", "cancelled",
                    "40_observed_cancellation", 40, "cancelled", "cancelled",
                    "CANCELLED", "cancelled",
                ),
                checker_worker(
                    f"{source}_cancellation", "cancelled",
                    "40_observed_cancellation", 40, "cancelled", "cancelled",
                    "CANCELLED", "cancelled",
                ),
            )
        ),
    ),
    row(
        "cancelled", "EVIDENCE_CANCELLED",
        producer_worker(
            "producer_refusal", "refused", "70_component_refusal", 70,
            "cancelled", "completed", "COMPLETED", "cancelled",
        ),
    ),
    row(
        "cancelled", "CHECKER_CANCELLED",
        checker_worker(
            "verifier_refusal", "refused", "70_component_refusal", 70,
            "cancelled", "completed", "COMPLETED", "cancelled",
        ),
    ),
    *tuple(
        row(
            "failed", reason,
            producer_worker(
                "internal_error", "failed", "00_internal_invariant", 0,
                "producer_error", "invalid", reason, "failed",
                phase="coordinator", diagnostic=diagnostic,
            ),
        )
        for reason, diagnostic in (
            ("REQUEST_INVALID", "WORKER_REQUEST_INVARIANT"),
            ("PLAN_INVALID", "WORKER_PLAN_INVARIANT"),
            ("STRATEGY_MISMATCH", "WORKER_STRATEGY_INVARIANT"),
            ("BUDGET_INVALID", "WORKER_BUDGET_INVARIANT"),
        )
    ),
    row(
        "failed", "EXECUTABLE_INVALID",
        producer_worker(
            "producer_refusal", "refused", "70_component_refusal", 70,
            "producer_error", "refused", "EXECUTABLE_INVALID", "failed",
            outcome_kind="executable_refused",
        ),
        producer_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "producer_error", "invalid", "EXECUTABLE_INVALID", "failed",
            phase="coordinator", outcome_kind="executable_invalid",
            diagnostic="WORKER_EXECUTABLE_INVARIANT",
        ),
    ),
    row(
        "failed", "LAUNCH_FAILED",
        producer_worker(
            "producer_failure", "failed", "90_phase_failure", 90,
            "producer_error", "refused", "LAUNCH_FAILED", "failed",
            outcome_kind="launch_refused",
        ),
    ),
    row(
        "failed", "EXIT_FAILED",
        producer_worker(
            "producer_failure", "failed", "90_phase_failure", 90,
            "producer_error", "failed", "EXIT_FAILED", "failed",
        ),
    ),
    row(
        "failed", "PROTOCOL_FAILED",
        producer_worker(
            "producer_failure", "failed", "90_phase_failure", 90,
            "producer_error", "failed", "PROTOCOL_FAILED", "failed",
        ),
    ),
    row(
        "failed", "TREE_CLEANUP_FAILED",
        producer_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "producer_error", "failed", "TREE_CLEANUP_FAILED", "failed",
            phase="cleanup", diagnostic="CLEANUP_INVARIANT",
        ),
    ),
    row(
        "failed", "SUPERVISOR_FAILED",
        producer_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "producer_error", "failed", "SUPERVISOR_FAILED", "failed",
            phase="coordinator", diagnostic="SUPERVISOR_INVARIANT",
        ),
    ),
    row(
        "failed", "EVIDENCE_ERROR",
        producer_worker(
            "producer_failure", "failed", "90_phase_failure", 90,
            "producer_error", "completed", "COMPLETED", "failed",
        ),
    ),
    row(
        "ambiguous", "EVIDENCE_INCOMPLETE",
        producer_worker(
            "ambiguity", "inconclusive", "80_semantic_terminal", 80,
            "ambiguous", "completed", "COMPLETED", "ambiguous",
        ),
    ),
    row(
        "truncated", "EVIDENCE_TRUNCATED",
        producer_worker(
            "truncation", "inconclusive", "80_semantic_terminal", 80,
            "truncated", "completed", "COMPLETED", "truncated",
        ),
    ),
    row(
        "truncated", "CHECKER_TRUNCATED",
        checker_worker(
            "truncation", "inconclusive", "80_semantic_terminal", 80,
            "truncated", "completed", "COMPLETED", "truncated",
        ),
    ),
    row(
        "inconclusive", "ISOLATION_UNSUPPORTED",
        checker_worker(
            "unsupported_execution_environment", "refused",
            "60_environment_refusal", 60, "checker_inconclusive",
            "unsupported", "ISOLATION_UNSUPPORTED", "inconclusive",
        ),
    ),
    row(
        "inconclusive", "CHECKER_INCONCLUSIVE",
        checker_worker(
            "verifier_refusal", "refused", "70_component_refusal", 70,
            "checker_inconclusive", "completed", "COMPLETED", "inconclusive",
            outcome_kind="certificate_unsupported",
        ),
        checker_worker(
            "inconclusive_execution", "inconclusive", "80_semantic_terminal", 80,
            "checker_inconclusive", "completed", "COMPLETED", "inconclusive",
            outcome_kind="certificate_inconclusive",
        ),
    ),
    row(
        "disagreement", "CHECKER_REJECTED",
        checker_worker(
            "checker_disagreement", "inconclusive", "80_semantic_terminal", 80,
            "checker_disagreement", "completed", "COMPLETED", "disagreement",
        ),
    ),
    row(
        "disagreement", "CHECKER_DISAGREED",
        checker_worker(
            "checker_disagreement", "inconclusive", "80_semantic_terminal", 80,
            "checker_disagreement", "completed", "COMPLETED", "disagreement",
        ),
    ),
    *tuple(
        row(
            "verifier_failed", reason,
            checker_worker(
                "internal_error", "failed", "00_internal_invariant", 0,
                "verifier_failure", "invalid", reason, "verifier_failed",
                phase="coordinator", diagnostic=diagnostic,
            ),
        )
        for reason, diagnostic in (
            ("REQUEST_INVALID", "WORKER_REQUEST_INVARIANT"),
            ("PLAN_INVALID", "WORKER_PLAN_INVARIANT"),
            ("STRATEGY_MISMATCH", "WORKER_STRATEGY_INVARIANT"),
            ("BUDGET_INVALID", "WORKER_BUDGET_INVARIANT"),
        )
    ),
    row(
        "verifier_failed", "EXECUTABLE_INVALID",
        checker_worker(
            "verifier_refusal", "refused", "70_component_refusal", 70,
            "verifier_failure", "refused", "EXECUTABLE_INVALID",
            "verifier_failed", outcome_kind="executable_refused",
        ),
        checker_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "verifier_failure", "invalid", "EXECUTABLE_INVALID",
            "verifier_failed", phase="coordinator",
            outcome_kind="executable_invalid",
            diagnostic="WORKER_EXECUTABLE_INVARIANT",
        ),
    ),
    row(
        "verifier_failed", "LAUNCH_FAILED",
        checker_worker(
            "verifier_failure", "failed", "90_phase_failure", 90,
            "verifier_failure", "refused", "LAUNCH_FAILED", "verifier_failed",
            outcome_kind="launch_refused",
        ),
    ),
    row(
        "verifier_failed", "EXIT_FAILED",
        checker_worker(
            "verifier_failure", "failed", "90_phase_failure", 90,
            "verifier_failure", "failed", "EXIT_FAILED", "verifier_failed",
        ),
    ),
    row(
        "verifier_failed", "PROTOCOL_FAILED",
        checker_worker(
            "verifier_failure", "failed", "90_phase_failure", 90,
            "verifier_failure", "failed", "PROTOCOL_FAILED", "verifier_failed",
        ),
    ),
    row(
        "verifier_failed", "TREE_CLEANUP_FAILED",
        checker_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "verifier_failure", "failed", "TREE_CLEANUP_FAILED",
            "verifier_failed", phase="cleanup", diagnostic="CLEANUP_INVARIANT",
        ),
    ),
    row(
        "verifier_failed", "SUPERVISOR_FAILED",
        checker_worker(
            "internal_error", "failed", "00_internal_invariant", 0,
            "verifier_failure", "failed", "SUPERVISOR_FAILED",
            "verifier_failed", phase="coordinator",
            diagnostic="SUPERVISOR_INVARIANT",
        ),
    ),
    row(
        "verifier_failed", "CERTIFICATE_INVALID",
        checker_worker(
            "verifier_failure", "failed", "90_phase_failure", 90,
            "verifier_failure", "completed", "COMPLETED", "verifier_failed",
        ),
    ),
    row(
        "invalid_evidence", "EVIDENCE_INVALID",
        producer_worker(
            "invalid_evidence", "inconclusive", "80_semantic_terminal", 80,
            "invalid_evidence", "completed", "COMPLETED", "invalid_evidence",
        ),
    ),
    row(
        "invalid_evidence", "EVIDENCE_PROTOCOL_LIMIT",
        producer_worker(
            "invalid_evidence", "inconclusive", "80_semantic_terminal", 80,
            "invalid_evidence", "completed", "COMPLETED", "invalid_evidence",
        ),
    ),
    row(
        "invalid_evidence", "CERTIFICATE_INVALID",
        checker_worker(
            "invalid_evidence", "inconclusive", "80_semantic_terminal", 80,
            "invalid_evidence", "completed", "COMPLETED", "invalid_evidence",
        ),
    ),
    row(
        "invalid", "PORTFOLIO_INPUT_INVALID",
        graph(
            "internal_error", "failed", "coordinator", "00_internal_invariant",
            0, None, None, None, None, None, "invalid",
            diagnostic="PORTFOLIO_INPUT_INVARIANT",
        ),
    ),
    row(
        "invalid", "PORTFOLIO_EXECUTION_INVALID",
        graph(
            "internal_error", "failed", "coordinator", "00_internal_invariant",
            0, None, None, None, None, None, "invalid",
            diagnostic="PORTFOLIO_EXECUTION_INVARIANT",
        ),
    ),
)


ORACLE_BY_PAIR = {(item.status, item.reason): item for item in PAIR_ORACLE}


def execute_with_audit(fixture: PlannedFixture, audit: object):
    from mathhead import execution_disposition as disposition
    from mathhead.run_audit import replay_run_audit

    with (
        mock.patch.object(
            disposition, "execute_audited_run", return_value=audit
        ) as audited,
        mock.patch.object(
            disposition, "replay_run_audit", wraps=replay_run_audit
        ) as replay,
    ):
        bundle = disposition.execute_with_disposition(
            *fixture.inputs.call_arguments
        )
    audited.assert_called_once()
    replay.assert_called_once_with(audit.manifest, audit.objects)
    return bundle


def replace_execution_binding(
    fixture: PlannedFixture,
    *,
    invocation_id: str,
    producer_arguments: tuple[str, ...] | None = None,
    checker_arguments: tuple[str, ...] | None = None,
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
        checker_executable=fixture.source.executable_bytes,
        producer_arguments=(
            parsed.producer_arguments
            if producer_arguments is None
            else producer_arguments
        ),
        checker_arguments=(
            parsed.checker_arguments
            if checker_arguments is None
            else checker_arguments
        ),
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
    fixture.binding = binding
    fixture.inputs = replace(
        fixture.inputs,
        request=request,
        request_value=request_value,
        bindings=(binding,),
    )
    if fixture.inputs.base_parent_budget is None:
        raise AssertionError("replacement binding requires a planned budget")
    fixture.expected_anchor = anchored_budget(
        fixture.inputs.base_parent_budget,
        str(request_value["request_sha256"]),
    )
    return fixture


def protocol_limit_fixture() -> PlannedFixture:
    from tools.validate_evidence_certificate_contracts import (
        evidence_generation_basis_sha256,
    )

    fixture = PlannedFixture()
    evidence = json.loads(fixture.source.evidence)
    evidence["diagnostics"] = [
        {
            "diagnostic_id": "diagnostic_protocol_limit",
            "severity": "info",
            "code": "org.mathhead.protocol-limit",
            "message": "x" * 4096,
            "related_payload_ids": [],
            "details": {},
        }
    ]
    evidence["outcome"]["diagnostic_ids"] = ["diagnostic_protocol_limit"]
    evidence["generation"]["basis_sha256"] = (
        evidence_generation_basis_sha256(evidence)
    )
    raw = portfolio_canonical(evidence)
    if len(raw.decode("ascii")) <= 4096:
        raise AssertionError("protocol-limit fixture is not oversized")
    return replace_execution_binding(
        fixture,
        invocation_id="invocation_pair_matrix_protocol_limit",
        producer_arguments=("-I", "-S", "-c", emit_script(raw)),
    )


def budget_fixture(scale: int) -> PlannedFixture:
    from mathhead.deterministic_planner import RESOURCE_DIMENSIONS
    from tests.isolated_worker.test_isolated_worker import parent_budget

    fixture = PlannedFixture()
    limits = {
        name: getattr(fixture.source.strategy.resource_request.requested, name)
        for name in RESOURCE_DIMENSIONS
    }
    base = parent_budget(limits, scale=scale)
    request, request_value = make_disposition_request(
        planning_request=fixture.inputs.planning_request,
        route_result=fixture.inputs.route_result,
        planning_result=fixture.inputs.planning_result,
        base_parent_budget=base,
        descriptors=fixture.inputs.descriptors,
        bindings=fixture.inputs.bindings,
        artifacts=fixture.inputs.artifacts,
        invocation_id=f"invocation_pair_matrix_budget_{scale}",
    )
    fixture.inputs = replace(
        fixture.inputs,
        request=request,
        request_value=request_value,
        base_parent_budget=base,
    )
    fixture.expected_anchor = anchored_budget(
        base, str(request_value["request_sha256"])
    )
    return fixture


def isolation_audit(fixture: PlannedFixture, phase: str):
    from mathhead import isolated_worker as worker

    supported = worker.isolation_capability()
    if not supported.supported:
        raise unittest.SkipTest(
            "host cannot emit the accepted complete isolated-worker graph"
        )
    with mock.patch.object(worker.sys, "platform", "unsupported-test-platform"):
        unsupported = worker.isolation_capability()
    values = (unsupported,) if phase == "producer" else (supported, unsupported)
    with mock.patch.object(worker, "isolation_capability", side_effect=values):
        return fixture.audited_bundle()


def resource_audit(fixture: PlannedFixture, phase: str, reason: str):
    from mathhead import isolated_worker as worker

    calls = 0

    def observation(
        _command: object,
        _root: object,
        _environment: object,
        limits: object,
        _cancel_event: object,
    ) -> SimpleNamespace:
        nonlocal calls
        calls += 1
        completed_producer = phase == "checker" and calls == 1
        selected_reason = "COMPLETED" if completed_producer else reason
        payload = fixture.source.evidence if completed_producer else b""
        values = {
            "exit_code": 0,
            "termination_signal": None,
            "wall_time_us": 1,
            "cpu_time_us": 1,
            "memory_peak_bytes": 1,
            "stdout": payload,
            "stdout_size": len(payload),
            "stderr": b"",
            "stderr_size": 0,
            "reason": selected_reason,
            "tree_terminated": True,
            "usage_complete": True,
        }
        if selected_reason == "WALL_TIME_EXHAUSTED":
            values["wall_time_us"] = limits.wall_time_us + 1
        elif selected_reason == "CPU_TIME_EXHAUSTED":
            values["cpu_time_us"] = limits.cpu_time_us + 1
        elif selected_reason == "OUTPUT_EXHAUSTED":
            values["stdout_size"] = limits.output_bytes + 1
        elif selected_reason == "DIAGNOSTIC_EXHAUSTED":
            values["stderr_size"] = limits.diagnostic_bytes + 1
        return SimpleNamespace(**values)

    with (
        mock.patch.object(worker, "_run_posix", side_effect=observation),
        mock.patch.object(worker, "_run_windows", side_effect=observation),
    ):
        return fixture.audited_bundle()


_WORKER_SEMANTIC_FIELDS = (
    "schema",
    "contract_id",
    "contract_sha256",
    "status",
    "reason_code",
    "request_sha256",
    "planning_result_sha256",
    "strategy_sha256",
    "capability",
    "artifacts",
    "diagnostics",
    "tree_terminated",
    "lease_reconciled",
    "mathematical_authority",
)


def retag_worker_result(value: object, status: str, reason: str):
    """Build a public-codec-valid fault result without a private constructor."""
    from mathhead import isolated_worker as worker

    mapping = json.loads(worker.isolated_worker_result_bytes(value))
    mapping["status"] = status
    mapping["reason_code"] = reason
    if mapping["diagnostics"]:
        diagnostic = mapping["diagnostics"][0]
        diagnostic["code"] = reason
    else:
        diagnostic = {
            "schema": "mathhead.worker-diagnostic.v1",
            "code": reason,
            "message": "accepted synthetic terminal observation",
            "diagnostic_sha256": None,
            "mathematical_authority": False,
        }
        mapping["diagnostics"] = [diagnostic]
    self_hash(diagnostic, "diagnostic_sha256")
    semantic = {name: mapping[name] for name in _WORKER_SEMANTIC_FIELDS}
    mapping["semantic_sha256"] = sha(canonical(semantic))
    self_hash(mapping, "result_sha256")
    payloads = tuple(worker.worker_artifact_bytes(item) for item in value.artifacts)
    child = None
    parent = None
    if value.lease_reconciled:
        child = worker.isolated_worker_budget_bytes(value, "child")
        parent = worker.isolated_worker_budget_bytes(value, "parent")
    return worker.parse_isolated_worker_result(
        canonical(mapping), payloads, child, parent
    )


def worker_fault_audit(
    fixture: PlannedFixture,
    phase: str,
    status: str,
    reason: str,
    *,
    launched: bool,
):
    from mathhead import isolated_worker as worker
    from mathhead import proof_search_portfolio as portfolio

    calls = 0

    def supervise(
        request: bytes,
        planning_result: bytes,
        parent_budget: bytes,
        artifacts: tuple[bytes, ...],
        executable_path: str,
        workspace_root: str,
        cancel_event: object = None,
    ):
        nonlocal calls
        calls += 1
        targeted = (phase == "producer" and calls == 1) or (
            phase == "checker" and calls == 2
        )
        if not targeted:
            return worker.supervise_worker(
                request,
                planning_result,
                parent_budget,
                artifacts,
                executable_path,
                workspace_root,
                cancel_event,
            )
        root = (
            workspace_root
            if launched
            else str(ROOT / "absent-pair-matrix-workspace")
        )
        baseline = worker.supervise_worker(
            request,
            planning_result,
            parent_budget,
            artifacts,
            executable_path,
            root,
            cancel_event,
        )
        return retag_worker_result(baseline, status, reason)

    with mock.patch.object(portfolio, "supervise_worker", side_effect=supervise):
        return fixture.audited_bundle()


def portfolio_input_invalid_audit(fixture: PlannedFixture):
    from mathhead import proof_search_portfolio as portfolio

    with mock.patch.object(
        portfolio, "_prepare_portfolio", side_effect=ValueError("fault injected")
    ):
        return fixture.audited_bundle()


def audit_inventory(audit: object):
    manifest = json.loads(audit.manifest)
    physical = {sha(raw): raw for raw in audit.objects}
    records = {item["role_id"]: item for item in manifest["objects"]}
    return manifest, physical, records


def portfolio_graph(audit: object):
    from mathhead.proof_search_portfolio import (
        parse_proof_search_portfolio_result,
    )

    _manifest, physical, records = audit_inventory(audit)
    raw = physical[records["portfolio_result"]["sha256"]]
    mapping = json.loads(raw)
    evidence_sha = mapping["selected_evidence_sha256"]
    certificate_sha = mapping["selected_certificate_sha256"]
    final_budget = (
        None
        if (mapping["status"], mapping["reason_code"])
        == ("invalid", "PORTFOLIO_INPUT_INVALID")
        else physical[records["final_parent_budget"]["sha256"]]
    )
    portfolio = parse_proof_search_portfolio_result(
        raw,
        final_budget,
        None if evidence_sha is None else physical[evidence_sha],
        None if certificate_sha is None else physical[certificate_sha],
    )
    observations = {
        role_id: json.loads(physical[record["sha256"]])
        for role_id, record in records.items()
        if role_id.startswith("producer_worker_observation_")
        or role_id.startswith("checker_worker_observation_")
    }
    return portfolio, observations


def transplant_checker_outer_pair(audit: object):
    """Rehash a complete audit while retaining its stale checker attempt graph."""
    from mathhead.run_audit import RunAuditBundle, replay_run_audit

    manifest, physical, records = audit_inventory(audit)
    portfolio_record = records["portfolio_result"]
    old_portfolio = portfolio_record["sha256"]
    portfolio = json.loads(physical.pop(old_portfolio))
    portfolio["status"] = "ambiguous"
    portfolio["reason_code"] = "EVIDENCE_INCOMPLETE"
    self_hash(portfolio, "result_sha256")
    portfolio_raw = canonical(portfolio)
    new_portfolio = sha(portfolio_raw)
    physical[new_portfolio] = portfolio_raw
    portfolio_record["sha256"] = new_portfolio
    portfolio_record["byte_count"] = len(portfolio_raw)
    self_hash(portfolio_record, "record_sha256")

    report_record = records["logical_report"]
    old_report = report_record["sha256"]
    report = json.loads(physical.pop(old_report))
    report["status"] = "ambiguous"
    report["reason_code"] = "EVIDENCE_INCOMPLETE"
    self_hash(report, "report_sha256")
    report_raw = canonical(report)
    new_report = sha(report_raw)
    physical[new_report] = report_raw
    report_record["sha256"] = new_report
    report_record["byte_count"] = len(report_raw)
    self_hash(report_record, "record_sha256")

    replacements = {old_portfolio: new_portfolio, old_report: new_report}
    previous = None
    for event in manifest["events"]:
        event["subject_sha256s"] = sorted(
            {replacements.get(item, item) for item in event["subject_sha256s"]}
        )
        if event["kind"] == "run_closed":
            event["reason_code"] = "EVIDENCE_INCOMPLETE"
        event["previous_event_sha256"] = previous
        self_hash(event, "event_sha256")
        previous = event["event_sha256"]
    manifest["portfolio_result_sha256"] = new_portfolio
    manifest["logical_report_sha256"] = new_report
    self_hash(manifest, "manifest_sha256")
    manifest_raw = canonical(manifest)
    objects = tuple(physical[item] for item in sorted(physical))
    replay = replay_run_audit(manifest_raw, objects)
    if replay.status != "complete":
        raise AssertionError("outer-pair transplant must remain replay-complete")

    forged = object.__new__(RunAuditBundle)
    values = {
        "manifest": manifest_raw,
        "objects": objects,
        "logical_report": report_raw,
        "manifest_sha256": sha(manifest_raw),
        "logical_report_sha256": new_report,
        "mathematical_authority": False,
    }
    for name, value in values.items():
        object.__setattr__(forged, name, value)
    return forged


class ExecutionDispositionPairMatrixTests(unittest.TestCase):
    def assert_bundle_matches(
        self,
        bundle: object,
        fixture: PlannedFixture,
        expected_pair: tuple[str, str],
        expected: ExpectedGraph,
    ) -> None:
        from mathhead import execution_disposition as disposition
        from mathhead.deterministic_planner import parse_planning_result

        disposition.validate_execution_disposition_bundle(bundle)
        result = bundle.result
        classification = result.classification
        self.assertEqual(
            (result.portfolio_status, result.portfolio_reason_code),
            expected_pair,
        )
        self.assertEqual(classification.cause, expected.cause)
        self.assertEqual(classification.disposition, expected.disposition)
        self.assertEqual(classification.phase, expected.phase)
        self.assertEqual(classification.precedence_row, expected.precedence_row)
        self.assertEqual(classification.precedence_rank, expected.precedence_rank)
        self.assertEqual(result.portfolio_relation, expected.portfolio_relation)
        self.assertEqual(result.portfolio_outcome_kind, expected.outcome_kind)
        self.assertEqual(
            tuple(item.code for item in result.diagnostics),
            () if expected.diagnostic is None else (expected.diagnostic,),
        )
        if expected.dimensions is None:
            self.assertTrue(classification.resource_dimensions)
        else:
            self.assertEqual(
                classification.resource_dimensions, expected.dimensions
            )
        self.assertEqual(result.execution_state, "replayed_complete")
        self.assertFalse(result.mathematical_authority)
        self.assertEqual(result.authority_ceiling, "none")

        portfolio, observations = portfolio_graph(bundle.audit)
        self.assertEqual((portfolio.status, portfolio.reason_code), expected_pair)
        if expected.attempt_outcome is None:
            self.assertEqual(portfolio.attempts, ())
            self.assertEqual(observations, {})
            return
        attempt = portfolio.attempts[-1]
        self.assertEqual(attempt.outcome, expected.attempt_outcome)
        self.assertEqual(attempt.producer_status, expected.producer_status)
        self.assertEqual(attempt.producer_reason_code, expected.producer_reason)
        self.assertEqual(attempt.checker_status, expected.checker_status)
        self.assertEqual(attempt.checker_reason_code, expected.checker_reason)
        producer = observations[
            f"producer_worker_observation_{attempt.attempt_order:06d}"
        ]["result"]
        self.assertEqual(
            (producer["status"], producer["reason_code"]),
            (expected.producer_status, expected.producer_reason),
        )
        checker_key = f"checker_worker_observation_{attempt.attempt_order:06d}"
        if expected.checker_status == "not_started":
            self.assertNotIn(checker_key, observations)
        else:
            checker = observations[checker_key]["result"]
            self.assertEqual(
                (checker["status"], checker["reason_code"]),
                (expected.checker_status, expected.checker_reason),
            )
        plan = parse_planning_result(fixture.inputs.planning_result)
        strategy = next(
            item
            for item in plan.strategies
            if item.strategy_sha256 == attempt.strategy_sha256
        )
        transitions = tuple(
            item
            for item in strategy.transitions
            if item.outcome == attempt.outcome
        )
        self.assertEqual(len(transitions), 1)
        transition = transitions[0]
        self.assertEqual(transition.transition_sha256, attempt.transition_sha256)
        self.assertNotEqual(transition.action, "fallback")
        self.assertEqual(transition.terminal_state, expected.terminal_state)
        self.assertEqual(transition.terminal_state, portfolio.status)

    def test_literal_oracle_has_exactly_49_unique_relation_rows(self) -> None:
        self.assertEqual(len(PAIR_ORACLE), 49)
        self.assertEqual(len(ORACLE_BY_PAIR), 49)
        self.assertEqual(
            sum(1 for item in PAIR_ORACLE if not item.variants), 0
        )
        for item in PAIR_ORACLE:
            with self.subTest(pair=(item.status, item.reason)):
                for variant in item.variants:
                    self.assertEqual(variant.terminal_state, item.status)
                    if variant.attempt_outcome is None:
                        self.assertEqual(item.status, "invalid")
                    else:
                        self.assertIsNotNone(variant.producer_status)
                        self.assertIsNotNone(variant.producer_reason)

    def test_real_semantic_fixtures_match_pair_and_terminal_graph_oracle(self) -> None:
        cases = (
            ("proof", PlannedFixture(), ("succeeded", "CHECKED_PROOF"), 0),
            (
                "refutation",
                PlannedFixture(claim="refuted"),
                ("succeeded", "CHECKED_REFUTATION"),
                0,
            ),
            (
                "evidence_unsupported",
                PlannedFixture(evidence_status="unsupported"),
                ("unsupported", "EVIDENCE_UNSUPPORTED"),
                0,
            ),
            (
                "evidence_exhausted",
                PlannedFixture(evidence_status="exhausted"),
                ("exhausted", "EVIDENCE_EXHAUSTED"),
                0,
            ),
            (
                "evidence_cancelled",
                PlannedFixture(evidence_status="cancelled"),
                ("cancelled", "EVIDENCE_CANCELLED"),
                0,
            ),
            (
                "evidence_error",
                PlannedFixture(evidence_status="error"),
                ("failed", "EVIDENCE_ERROR"),
                0,
            ),
            (
                "evidence_incomplete",
                PlannedFixture(evidence_status="incomplete"),
                ("ambiguous", "EVIDENCE_INCOMPLETE"),
                0,
            ),
            (
                "evidence_truncated",
                PlannedFixture(evidence_status="truncated"),
                ("truncated", "EVIDENCE_TRUNCATED"),
                0,
            ),
            (
                "evidence_invalid",
                PlannedFixture(malformed_evidence=True),
                ("invalid_evidence", "EVIDENCE_INVALID"),
                0,
            ),
            (
                "producer_exit",
                PlannedFixture(producer_exit=7),
                ("failed", "EXIT_FAILED"),
                0,
            ),
            (
                "certificate_unsupported",
                PlannedFixture(certificate_status="unsupported"),
                ("inconclusive", "CHECKER_INCONCLUSIVE"),
                0,
            ),
            (
                "certificate_inconclusive",
                PlannedFixture(certificate_status="inconclusive"),
                ("inconclusive", "CHECKER_INCONCLUSIVE"),
                1,
            ),
            (
                "checker_exhausted",
                PlannedFixture(certificate_status="exhausted"),
                ("exhausted", "CHECKER_EXHAUSTED"),
                0,
            ),
            (
                "checker_cancelled",
                PlannedFixture(certificate_status="cancelled"),
                ("cancelled", "CHECKER_CANCELLED"),
                0,
            ),
            (
                "checker_truncated",
                PlannedFixture(certificate_status="truncated"),
                ("truncated", "CHECKER_TRUNCATED"),
                0,
            ),
            (
                "checker_rejected",
                PlannedFixture(certificate_status="invalid"),
                ("disagreement", "CHECKER_REJECTED"),
                0,
            ),
            (
                "checker_disagreed",
                PlannedFixture(agreement=False),
                ("disagreement", "CHECKER_DISAGREED"),
                0,
            ),
            (
                "certificate_verifier_failure",
                PlannedFixture(certificate_status="verifier_failed"),
                ("verifier_failed", "CERTIFICATE_INVALID"),
                0,
            ),
            (
                "producer_cancellation",
                PlannedFixture(
                    origin_source="user", event_set=True
                ),
                ("cancelled", "CANCELLED"),
                0,
            ),
            (
                "protocol_limit",
                protocol_limit_fixture(),
                ("invalid_evidence", "EVIDENCE_PROTOCOL_LIMIT"),
                0,
            ),
            (
                "checker_exit",
                replace_execution_binding(
                    PlannedFixture(),
                    invocation_id="invocation_pair_matrix_checker_exit",
                    checker_arguments=(
                        "-I", "-S", "-c", "raise SystemExit(9)"
                    ),
                ),
                ("verifier_failed", "EXIT_FAILED"),
                0,
            ),
            (
                "certificate_invalid",
                replace_execution_binding(
                    PlannedFixture(),
                    invocation_id="invocation_pair_matrix_bad_certificate",
                    checker_arguments=(
                        "-I",
                        "-S",
                        "-c",
                        emit_script(b'{"certificate":{},"decision":{}}\n'),
                    ),
                ),
                ("invalid_evidence", "CERTIFICATE_INVALID"),
                0,
            ),
        )
        for label, fixture, pair_value, variant in cases:
            with self.subTest(case=label):
                audit = fixture.audited_bundle()
                bundle = execute_with_audit(fixture, audit)
                self.assert_bundle_matches(
                    bundle,
                    fixture,
                    pair_value,
                    ORACLE_BY_PAIR[pair_value].variants[variant],
                )

    def test_role_sensitive_environment_budget_and_cancellation_rows(self) -> None:
        for phase, pair_value, variant in (
            ("producer", ("unsupported", "ISOLATION_UNSUPPORTED"), 0),
            ("checker", ("inconclusive", "ISOLATION_UNSUPPORTED"), 0),
        ):
            with self.subTest(kind="isolation", phase=phase):
                fixture = PlannedFixture()
                audit = isolation_audit(fixture, phase)
                self.assert_bundle_matches(
                    execute_with_audit(fixture, audit),
                    fixture,
                    pair_value,
                    ORACLE_BY_PAIR[pair_value].variants[variant],
                )

        for scale, phase, variant in ((0, "producer", 0), (1, "checker", 1)):
            with self.subTest(kind="budget", phase=phase):
                fixture = budget_fixture(scale)
                audit = fixture.audited_bundle()
                pair_value = ("exhausted", "BUDGET_INSUFFICIENT")
                self.assert_bundle_matches(
                    execute_with_audit(fixture, audit),
                    fixture,
                    pair_value,
                    ORACLE_BY_PAIR[pair_value].variants[variant],
                )

        checker_cancel = PlannedFixture(origin_source="parent")
        from mathhead import isolated_worker as worker
        from mathhead import proof_search_portfolio as portfolio

        calls = 0

        def set_before_checker(*args: object):
            nonlocal calls
            calls += 1
            if calls == 2:
                checker_cancel.inputs.cancel_event.set()
            return worker.supervise_worker(*args)

        with mock.patch.object(
            portfolio, "supervise_worker", side_effect=set_before_checker
        ):
            audit = checker_cancel.audited_bundle()
        pair_value = ("cancelled", "CANCELLED")
        self.assert_bundle_matches(
            execute_with_audit(checker_cancel, audit),
            checker_cancel,
            pair_value,
            ORACLE_BY_PAIR[pair_value].variants[3],
        )

    def test_replayed_worker_fault_rows_match_exact_role_and_diagnostic(self) -> None:
        nonlaunched = (
            ("invalid", "REQUEST_INVALID", False, 0),
            ("invalid", "PLAN_INVALID", False, 0),
            ("invalid", "STRATEGY_MISMATCH", False, 0),
            ("invalid", "BUDGET_INVALID", False, 0),
            ("refused", "EXECUTABLE_INVALID", False, 0),
            ("invalid", "EXECUTABLE_INVALID", False, 1),
            ("refused", "LAUNCH_FAILED", False, 0),
        )
        for phase, outer_status in (
            ("producer", "failed"),
            ("checker", "verifier_failed"),
        ):
            for status, reason, launched, variant in nonlaunched:
                pair_value = (outer_status, reason)
                with self.subTest(phase=phase, pair=pair_value, status=status):
                    fixture = PlannedFixture()
                    audit = worker_fault_audit(
                        fixture, phase, status, reason, launched=launched
                    )
                    self.assert_bundle_matches(
                        execute_with_audit(fixture, audit),
                        fixture,
                        pair_value,
                        ORACLE_BY_PAIR[pair_value].variants[variant],
                    )

        for phase, outer_status in (
            ("producer", "failed"),
            ("checker", "verifier_failed"),
        ):
            for reason in (
                "PROTOCOL_FAILED",
                "TREE_CLEANUP_FAILED",
                "SUPERVISOR_FAILED",
            ):
                pair_value = (outer_status, reason)
                with self.subTest(phase=phase, pair=pair_value):
                    fixture = PlannedFixture()
                    audit = worker_fault_audit(
                        fixture, phase, "failed", reason, launched=True
                    )
                    self.assert_bundle_matches(
                        execute_with_audit(fixture, audit),
                        fixture,
                        pair_value,
                        ORACLE_BY_PAIR[pair_value].variants[0],
                    )

    def test_four_replayable_resource_reasons_bind_both_worker_roles(self) -> None:
        for phase, variant in (("producer", 0), ("checker", 1)):
            for reason in (
                "WALL_TIME_EXHAUSTED",
                "CPU_TIME_EXHAUSTED",
                "OUTPUT_EXHAUSTED",
                "DIAGNOSTIC_EXHAUSTED",
            ):
                pair_value = ("exhausted", reason)
                with self.subTest(phase=phase, reason=reason):
                    fixture = PlannedFixture()
                    audit = resource_audit(fixture, phase, reason)
                    self.assert_bundle_matches(
                        execute_with_audit(fixture, audit),
                        fixture,
                        pair_value,
                        ORACLE_BY_PAIR[pair_value].variants[variant],
                    )

    def test_prelaunch_invalid_portfolio_row_is_a_replayed_internal_invariant(self) -> None:
        fixture = PlannedFixture()
        audit = portfolio_input_invalid_audit(fixture)
        pair_value = ("invalid", "PORTFOLIO_INPUT_INVALID")
        self.assert_bundle_matches(
            execute_with_audit(fixture, audit),
            fixture,
            pair_value,
            ORACLE_BY_PAIR[pair_value].variants[0],
        )

    def test_rehashed_outer_pair_cannot_override_stale_final_checker_graph(self) -> None:
        fixture = PlannedFixture(certificate_status="unsupported")
        genuine = fixture.audited_bundle()
        forged = transplant_checker_outer_pair(genuine)
        bundle = execute_with_audit(fixture, forged)
        self.assertEqual(
            (bundle.result.portfolio_status, bundle.result.portfolio_reason_code),
            ("ambiguous", "EVIDENCE_INCOMPLETE"),
        )
        self.assertEqual(bundle.result.classification.cause, "internal_error")
        self.assertEqual(bundle.result.classification.phase, "audit")
        self.assertEqual(bundle.result.portfolio_relation, "invalid")
        self.assertEqual(
            tuple(item.code for item in bundle.result.diagnostics),
            ("AUDIT_RELATION_INVALID",),
        )

    def test_two_upstream_rows_without_a_genuine_v1_fixture_remain_explicit(self) -> None:
        # The accepted worker currently clamps memory_peak_bytes before forming
        # the child exhaustion ledger, so MEMORY_EXHAUSTED cannot replay with
        # its required unavailable-dimension relation.  Audit v5 likewise
        # rejects the zero-attempt PORTFOLIO_EXECUTION_INVALID prefix.  Keeping
        # these two literal rows visible prevents a smaller emitted subset from
        # being mislabeled as exhaustive executable coverage.
        self.assertEqual(
            {
                ("exhausted", "MEMORY_EXHAUSTED"),
                ("invalid", "PORTFOLIO_EXECUTION_INVALID"),
            },
            {
                pair_value
                for pair_value in ORACLE_BY_PAIR
                if pair_value
                in {
                    ("exhausted", "MEMORY_EXHAUSTED"),
                    ("invalid", "PORTFOLIO_EXECUTION_INVALID"),
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
