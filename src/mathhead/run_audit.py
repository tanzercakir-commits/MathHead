"""Content-addressed audited portfolio execution and pure logical replay.

Only validated mathematical/governance objects enter the bundle.  Effect-only
paths, ambient state, raw invalid process output, clocks, and diagnostics are
excluded from the canonical boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from threading import Event
import unicodedata
from typing import Any, Final, NoReturn

from .capability_registry import (
    CONTRACT_SHA256 as CAPABILITY_REGISTRY_CONTRACT_SHA256,
    capability_route_result_bytes,
    parse_capability_route_request,
    parse_capability_route_result,
    route_capabilities,
)
from .deterministic_planner import (
    CERTIFICATE_CONTRACT_SHA256,
    CONTRACT_SHA256 as DETERMINISTIC_PLANNER_CONTRACT_SHA256,
    EVIDENCE_CONTRACT_SHA256,
    RESOURCE_BUDGET_CONTRACT_SHA256,
    THEORY_PLUGIN_CONTRACT_SHA256,
    parse_planning_request,
    parse_planning_result,
    plan_strategies,
    planning_result_bytes,
)
from .isolated_worker import ISOLATED_WORKER_CONTRACT_SHA256
from .problem_sessions import PROBLEM_SESSION_CONTRACT_SHA256
from .proof_search_portfolio import (
    PORTFOLIO_CONTRACT_SHA256,
    ProofSearchPortfolioResult,
    _PortfolioAuditAttempt,
    _run_portfolio_audited,
    parse_portfolio_checker_decision,
    parse_portfolio_execution_binding,
    parse_proof_search_portfolio_request,
    parse_proof_search_portfolio_result,
    proof_search_portfolio_budget_bytes,
    proof_search_portfolio_result_bytes,
)


AUDITED_RUN_CONTRACT_ID: Final = "MH-C-AUDITED-RUN-001"
AUDITED_RUN_CONTRACT_SHA256: Final = (
    "6032b9efac0c1ffa93cc2ee738318f45d8331c8ee25f4d97b51b55ba8aff8c0a"
)
REPLAY_CONTRACT_ID: Final = "MH-C-RUN-AUDIT-REPLAY-001"
REPLAY_CONTRACT_SHA256: Final = (
    "ed130e9099a4308ed2c911e9ad63d2450783d9bff9700ad6ac0e2dd22ede9bc5"
)

OBJECT_SCHEMA: Final = "mathhead.run-audit-object.v1"
EVENT_SCHEMA: Final = "mathhead.run-audit-event.v1"
MANIFEST_SCHEMA: Final = "mathhead.run-audit-manifest.v1"
LOGICAL_REPORT_SCHEMA: Final = "mathhead.run-logical-report.v1"
REPLAY_RESULT_SCHEMA: Final = "mathhead.run-audit-replay-result.v1"

SCHEMA_SHA256S: Final = {
    OBJECT_SCHEMA: "03797f8c040c27286fb9bff2a988a7106e3fc6956e9203c90a81714cf8e98f60",
    EVENT_SCHEMA: "6c1ef20c692220b9c1970620eac220e3a8a1ff3c23148a60a05e9d76b4045ecb",
    MANIFEST_SCHEMA: "53c4f799ca8a523e01a518069aa1c27483bd9c2f95132281ebdb93fa0c7bd950",
    LOGICAL_REPORT_SCHEMA: "2db8b0e75d274817201314e853bfe10ed5a6910bf8b6fa74549c1bb30eccbc76",
    REPLAY_RESULT_SCHEMA: "c60e67b31da35441692ea88caeb09780755be092946d1aa4486dcbd748aad500",
}

MAX_OBJECTS: Final = 200_000
MAX_EVENTS: Final = 1_000_000
MAX_OBJECT_BYTES: Final = 1_073_741_824
MAX_AGGREGATE_BYTES: Final = 2_147_483_648
MAX_JSON_NODES: Final = 12_000_000
MAX_JSON_DEPTH: Final = 128
MAX_STRING: Final = 1_048_576
INTEGER_MAXIMUM: Final = 9_007_199_254_740_991

_DIGEST = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[a-z][a-z0-9_]{0,127}")
_NAMESPACED = re.compile(r"[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+")
_REASON = re.compile(r"[A-Z][A-Z0-9_]{0,63}")

_OBJECT_ROLES = {
    "planning_request",
    "capability_route_result",
    "planning_result",
    "portfolio_request",
    "portfolio_result",
    "initial_parent_budget",
    "reconciled_parent_budget",
    "session_event",
    "normalized_input",
    "session_context",
    "session_obligation",
    "session_artifact",
    "plugin_descriptor",
    "execution_binding",
    "validated_evidence",
    "checker_certificate",
    "checker_decision",
    "logical_report",
}
_EVENT_KINDS = {
    "run_opened",
    "input_bound",
    "plan_bound",
    "strategy_started",
    "producer_completed",
    "evidence_classified",
    "checker_completed",
    "checker_decided",
    "transition_selected",
    "run_closed",
}
_EVENT_PHASES = {"run", "input", "plan", "producer", "checker", "transition"}
_EVENT_OUTCOMES = {
    "opened",
    "bound",
    "completed",
    "not_started",
    "success",
    "unsupported",
    "producer_error",
    "ambiguous",
    "cancelled",
    "exhausted",
    "truncated",
    "invalid_evidence",
    "checker_inconclusive",
    "checker_disagreement",
    "verifier_failure",
    "failed",
    "invalid",
    "closed",
}
_PORTFOLIO_STATUSES = {
    "succeeded",
    "unsupported",
    "exhausted",
    "cancelled",
    "failed",
    "ambiguous",
    "truncated",
    "inconclusive",
    "disagreement",
    "verifier_failed",
    "invalid_evidence",
    "invalid",
}
_VERDICTS = {"proved", "refuted", "inconclusive", "none"}
_AUTHORITY_TIERS = {"none", "checker_attestation", "external_proof_assistant"}


class RunAuditValidationError(ValueError):
    """Strict audited-run boundary validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        self.kind = kind
        self.path = path
        self.detail = detail
        super().__init__(f"{kind}:{path}: {detail}")


class _Invalid(ValueError):
    pass


class _Exhausted(ValueError):
    pass


class _DuplicateKey(ValueError):
    pass


_PUBLIC_FINAL = False


class _AuditValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_FINAL:
            raise TypeError("run-audit value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class RunAuditBundle(_AuditValue):
    manifest: bytes
    objects: tuple[bytes, ...]
    logical_report: bytes
    manifest_sha256: str
    logical_report_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("run-audit bundles are builder-owned")


@dataclass(frozen=True, slots=True, init=False)
class RunAuditReplayResult(_AuditValue):
    schema: str
    contract_id: str
    contract_sha256: str
    status: str
    reason_code: str
    manifest_sha256: str | None
    bundle_sha256: str | None
    logical_report_sha256: str | None
    object_count: int
    event_count: int
    portfolio_status: str | None
    mathematical_verdict: str | None
    authority_tier: str | None
    replay_result_sha256: str
    mathematical_authority: bool
    _input_manifest: bytes | None
    _input_objects: tuple[bytes, ...] | None
    _logical_report: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("run-audit replay results are replay-owned")


_PUBLIC_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    value = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(value, field.name, values[field.name])
    return value


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise RunAuditValidationError(kind, path, detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _walk(value: object, *, depth: int = 0, nodes: list[int] | None = None) -> None:
    count = [0] if nodes is None else nodes
    count[0] += 1
    if count[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise _Exhausted("JSON work budget exceeded")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if value < -INTEGER_MAXIMUM or value > INTEGER_MAXIMUM:
            raise _Invalid("integer outside canonical range")
        return
    if type(value) is str:
        if len(value) > MAX_STRING:
            raise _Exhausted("string budget exceeded")
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            raise _Invalid("string is NUL-bearing or non-NFC")
        return
    if type(value) is list:
        for item in value:
            _walk(item, depth=depth + 1, nodes=count)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _Invalid("object key is not an exact string")
            _walk(key, depth=depth + 1, nodes=count)
            _walk(item, depth=depth + 1, nodes=count)
        return
    raise _Invalid("forbidden canonical value type")


def _canonical(value: object, *, maximum: int = MAX_OBJECT_BYTES) -> bytes:
    _walk(value)
    try:
        raw = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise _Invalid(f"canonical encoding failed: {type(exc).__name__}") from exc
    if len(raw) > maximum:
        raise _Exhausted("canonical bytes exceed budget")
    return raw


def _parse(data: bytes, path: str, *, maximum: int = MAX_OBJECT_BYTES) -> dict[str, object]:
    if type(data) is not bytes:
        raise _Invalid(f"{path} must be exact bytes")
    if not data or len(data) > maximum:
        raise _Exhausted(f"{path} bytes outside budget")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda value: (_ for _ in ()).throw(_Invalid("floats forbidden")),
            parse_constant=lambda value: (_ for _ in ()).throw(_Invalid("constants forbidden")),
        )
    except _DuplicateKey as exc:
        raise _Invalid(f"{path} duplicate key {exc.args[0]!r}") from exc
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, (_Invalid, _Exhausted)):
            raise
        raise _Invalid(f"{path} invalid JSON: {type(exc).__name__}") from exc
    if type(value) is not dict:
        raise _Invalid(f"{path} root must be an object")
    _walk(value)
    if _canonical(value, maximum=maximum) != data:
        raise _Invalid(f"{path} is not canonical")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        raise _Invalid(f"{path} field set differs")
    return value


def _digest(value: object, path: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise _Invalid(f"{path} is not one full lowercase SHA-256")
    return value


def _nullable_digest(value: object, path: str) -> str | None:
    return None if value is None else _digest(value, path)


def _identifier(value: object, path: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise _Invalid(f"{path} is not a canonical identifier")
    return value


def _namespaced(value: object, path: str) -> str:
    if type(value) is not str or _NAMESPACED.fullmatch(value) is None:
        raise _Invalid(f"{path} is not a namespaced schema identifier")
    return value


def _quantity(value: object, path: str, maximum: int = INTEGER_MAXIMUM) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise _Invalid(f"{path} is not a bounded exact integer")
    return value


def _reason(value: object, path: str) -> str:
    if type(value) is not str or _REASON.fullmatch(value) is None:
        raise _Invalid(f"{path} is not a closed reason code")
    return value


def _self_hash(value: dict[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _schema_of(raw: bytes, path: str) -> tuple[str, dict[str, object]]:
    value = _parse(raw, path)
    return _namespaced(value.get("schema"), f"{path}.schema"), value


def _record(
    ordinal: int,
    role: str,
    role_id: str,
    raw: bytes,
    *,
    binding_role: str | None = None,
) -> dict[str, object]:
    if role not in _OBJECT_ROLES:
        raise _Invalid("unknown audit object role")
    schema, _value = _schema_of(raw, role_id)
    value: dict[str, object] = {
        "schema": OBJECT_SCHEMA,
        "ordinal": ordinal,
        "role": role,
        "role_id": _identifier(role_id, "record.role_id"),
        "binding_role": None
        if binding_role is None
        else _identifier(binding_role, "record.binding_role"),
        "artifact_schema": schema,
        "sha256": _sha(raw),
        "byte_count": len(raw),
        "record_sha256": None,
        "mathematical_authority": False,
    }
    value["record_sha256"] = _self_hash(value, "record_sha256")
    return value


def _parse_record(value: object, ordinal: int) -> dict[str, object]:
    item = _keys(
        value,
        {
            "schema",
            "ordinal",
            "role",
            "role_id",
            "binding_role",
            "artifact_schema",
            "sha256",
            "byte_count",
            "record_sha256",
            "mathematical_authority",
        },
        f"objects[{ordinal}]",
    )
    if item["schema"] != OBJECT_SCHEMA or item["mathematical_authority"] is not False:
        raise _Invalid("audit object schema or authority drift")
    if _quantity(item["ordinal"], "object.ordinal", MAX_OBJECTS) != ordinal:
        raise _Invalid("audit object ordinal is not contiguous")
    if item["role"] not in _OBJECT_ROLES:
        raise _Invalid("audit object role is unknown")
    _identifier(item["role_id"], "object.role_id")
    if item["binding_role"] is not None:
        _identifier(item["binding_role"], "object.binding_role")
    _namespaced(item["artifact_schema"], "object.artifact_schema")
    _digest(item["sha256"], "object.sha256")
    _quantity(item["byte_count"], "object.byte_count", MAX_OBJECT_BYTES)
    identity = _digest(item["record_sha256"], "object.record_sha256")
    if identity != _self_hash(item, "record_sha256"):
        raise _Invalid("audit object record identity differs")
    return item


def _worker_event_outcome(status: str) -> str:
    return {
        "completed": "completed",
        "cancelled": "cancelled",
        "exhausted": "exhausted",
        "unsupported": "unsupported",
        "invalid": "invalid",
        "refused": "failed",
        "failed": "failed",
    }.get(status, "failed")


def _event(
    events: list[dict[str, object]],
    *,
    kind: str,
    attempt_order: int | None,
    strategy_sha256: str | None,
    phase: str,
    outcome: str,
    reason_code: str,
    subjects: tuple[str, ...],
    parent_before: str | None = None,
    parent_after: str | None = None,
) -> None:
    if kind not in _EVENT_KINDS or phase not in _EVENT_PHASES or outcome not in _EVENT_OUTCOMES:
        raise _Invalid("event classification is outside the closed set")
    ordered_subjects = tuple(sorted(set(subjects)))
    if len(ordered_subjects) > 32 or any(_DIGEST.fullmatch(item) is None for item in ordered_subjects):
        raise _Invalid("event subject inventory is invalid")
    value: dict[str, object] = {
        "schema": EVENT_SCHEMA,
        "event_order": len(events),
        "kind": kind,
        "attempt_order": attempt_order,
        "strategy_sha256": strategy_sha256,
        "phase": phase,
        "outcome": outcome,
        "reason_code": _reason(reason_code, "event.reason_code"),
        "subject_sha256s": list(ordered_subjects),
        "parent_budget_before_sha256": parent_before,
        "parent_budget_after_sha256": parent_after,
        "previous_event_sha256": None if not events else events[-1]["event_sha256"],
        "event_sha256": None,
        "mathematical_authority": False,
    }
    value["event_sha256"] = _self_hash(value, "event_sha256")
    events.append(value)


def _parse_event(value: object, ordinal: int, previous: str | None) -> dict[str, object]:
    item = _keys(
        value,
        {
            "schema",
            "event_order",
            "kind",
            "attempt_order",
            "strategy_sha256",
            "phase",
            "outcome",
            "reason_code",
            "subject_sha256s",
            "parent_budget_before_sha256",
            "parent_budget_after_sha256",
            "previous_event_sha256",
            "event_sha256",
            "mathematical_authority",
        },
        f"events[{ordinal}]",
    )
    if item["schema"] != EVENT_SCHEMA or item["mathematical_authority"] is not False:
        raise _Invalid("event schema or authority differs")
    if _quantity(item["event_order"], "event.event_order", MAX_EVENTS) != ordinal:
        raise _Invalid("event order is not contiguous")
    if item["kind"] not in _EVENT_KINDS or item["phase"] not in _EVENT_PHASES or item["outcome"] not in _EVENT_OUTCOMES:
        raise _Invalid("event classification differs")
    if item["attempt_order"] is not None:
        _quantity(item["attempt_order"], "event.attempt_order", 100_000)
    _nullable_digest(item["strategy_sha256"], "event.strategy_sha256")
    _reason(item["reason_code"], "event.reason_code")
    raw_subjects = item["subject_sha256s"]
    if type(raw_subjects) is not list or len(raw_subjects) > 32:
        raise _Invalid("event subject inventory is invalid")
    subjects = tuple(_digest(entry, "event.subject") for entry in raw_subjects)
    if subjects != tuple(sorted(set(subjects))):
        raise _Invalid("event subjects are not sorted unique")
    _nullable_digest(item["parent_budget_before_sha256"], "event.parent_before")
    _nullable_digest(item["parent_budget_after_sha256"], "event.parent_after")
    if item["previous_event_sha256"] != previous:
        raise _Invalid("event previous link differs")
    identity = _digest(item["event_sha256"], "event.event_sha256")
    if identity != _self_hash(item, "event_sha256"):
        raise _Invalid("event identity differs")
    return item


def _record_inventory_digest(records: list[dict[str, object]], roles: set[str]) -> str:
    identities = [record["record_sha256"] for record in records if record["role"] in roles]
    return _sha(_canonical(identities))


def _report_mapping(
    *,
    planning_request: bytes,
    route_result: bytes,
    planning_result: bytes,
    portfolio_request: bytes,
    normalized_input_sha256: str,
    initial_parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    records: list[dict[str, object]],
    portfolio: ProofSearchPortfolioResult,
) -> dict[str, object]:
    plan = parse_planning_result(planning_result)
    descriptor_values = {_sha(raw): _parse(raw, "descriptor") for raw in descriptors}
    plugins: list[dict[str, object]] = []
    for strategy in plan.strategies:
        descriptor = descriptor_values.get(strategy.descriptor_sha256)
        if descriptor is None:
            raise _Invalid("plan descriptor is absent")
        components = descriptor.get("components")
        if type(components) is not dict or type(components.get("producer")) is not dict or type(components.get("checker")) is not dict:
            raise _Invalid("descriptor components are malformed")
        producer = components["producer"]
        checker = components["checker"]
        plugins.append(
            {
                "plan_order": strategy.plan_order,
                "strategy_sha256": strategy.strategy_sha256,
                "descriptor_sha256": strategy.descriptor_sha256,
                "plugin_id": descriptor.get("plugin_id"),
                "plugin_version": descriptor.get("plugin_version"),
                "producer_component_id": producer.get("component_id"),
                "checker_component_id": checker.get("component_id"),
            }
        )
    budget = _parse(initial_parent_budget, "initial_parent_budget")
    limits = budget.get("limits")
    if type(limits) is not dict:
        raise _Invalid("initial parent budget has no limits")
    artifact_roles = {
        "session_event",
        "normalized_input",
        "session_context",
        "session_obligation",
        "session_artifact",
        "plugin_descriptor",
        "execution_binding",
        "validated_evidence",
        "checker_certificate",
        "checker_decision",
    }
    artifacts = [
        {
            "role_id": item["role_id"],
            "sha256": item["sha256"],
            "byte_count": item["byte_count"],
        }
        for item in records
        if item["role"] in artifact_roles
    ]
    attempts = [
        {
            "attempt_order": attempt.attempt_order,
            "strategy_sha256": attempt.strategy_sha256,
            "producer_worker_result_sha256": attempt.producer_worker_result_sha256,
            "producer_status": attempt.producer_status,
            "producer_reason_code": attempt.producer_reason_code,
            "evidence_sha256": attempt.evidence_sha256,
            "checker_worker_result_sha256": attempt.checker_worker_result_sha256,
            "checker_status": attempt.checker_status,
            "checker_reason_code": attempt.checker_reason_code,
            "checker_decision_sha256": attempt.checker_decision_sha256,
            "outcome": attempt.outcome,
            "transition_sha256": attempt.transition_sha256,
        }
        for attempt in portfolio.attempts
    ]
    value: dict[str, object] = {
        "schema": LOGICAL_REPORT_SCHEMA,
        "audited_run_contract_sha256": AUDITED_RUN_CONTRACT_SHA256,
        "normalized_input_sha256": normalized_input_sha256,
        "planning_request_sha256": _sha(planning_request),
        "route_result_sha256": _sha(route_result),
        "planning_result_sha256": _sha(planning_result),
        "portfolio_request_sha256": _sha(portfolio_request),
        "declared_budget_limits_sha256": _sha(_canonical(limits)),
        "plugins": plugins,
        "artifacts": artifacts,
        "attempts": attempts,
        "status": portfolio.status,
        "mathematical_verdict": portfolio.mathematical_verdict,
        "reason_code": portfolio.reason_code,
        "selected_strategy_sha256": portfolio.selected_strategy_sha256,
        "selected_evidence_sha256": portfolio.selected_evidence_sha256,
        "selected_certificate_sha256": portfolio.selected_certificate_sha256,
        "selected_checker_decision_sha256": portfolio.selected_checker_decision_sha256,
        "authority_tier": portfolio.authority_tier,
        "report_sha256": None,
        "mathematical_authority": False,
    }
    value["report_sha256"] = _self_hash(value, "report_sha256")
    return value


def _validate_report(value: object) -> dict[str, object]:
    item = _keys(
        value,
        {
            "schema",
            "audited_run_contract_sha256",
            "normalized_input_sha256",
            "planning_request_sha256",
            "route_result_sha256",
            "planning_result_sha256",
            "portfolio_request_sha256",
            "declared_budget_limits_sha256",
            "plugins",
            "artifacts",
            "attempts",
            "status",
            "mathematical_verdict",
            "reason_code",
            "selected_strategy_sha256",
            "selected_evidence_sha256",
            "selected_certificate_sha256",
            "selected_checker_decision_sha256",
            "authority_tier",
            "report_sha256",
            "mathematical_authority",
        },
        "logical_report",
    )
    if item["schema"] != LOGICAL_REPORT_SCHEMA or item["audited_run_contract_sha256"] != AUDITED_RUN_CONTRACT_SHA256 or item["mathematical_authority"] is not False:
        raise _Invalid("logical report contract binding differs")
    for name in (
        "normalized_input_sha256",
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "portfolio_request_sha256",
        "declared_budget_limits_sha256",
    ):
        _digest(item[name], f"logical_report.{name}")
    if type(item["plugins"]) is not list or len(item["plugins"]) > 100_000:
        raise _Exhausted("logical report plugin inventory exceeds budget")
    if type(item["artifacts"]) is not list or len(item["artifacts"]) > MAX_OBJECTS:
        raise _Exhausted("logical report artifact inventory exceeds budget")
    if type(item["attempts"]) is not list or len(item["attempts"]) > 100_000:
        raise _Exhausted("logical report attempt inventory exceeds budget")
    if item["status"] not in _PORTFOLIO_STATUSES or item["mathematical_verdict"] not in _VERDICTS or item["authority_tier"] not in _AUTHORITY_TIERS:
        raise _Invalid("logical report classification differs")
    _reason(item["reason_code"], "logical_report.reason_code")
    for name in (
        "selected_strategy_sha256",
        "selected_evidence_sha256",
        "selected_certificate_sha256",
        "selected_checker_decision_sha256",
    ):
        _nullable_digest(item[name], f"logical_report.{name}")
    identity = _digest(item["report_sha256"], "logical_report.report_sha256")
    if identity != _self_hash(item, "report_sha256"):
        raise _Invalid("logical report identity differs")
    return item


def _events_from_records(
    records: list[dict[str, object]],
    by_role_id: dict[str, dict[str, object]],
    portfolio: ProofSearchPortfolioResult,
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    planning = by_role_id["planning_request"]["sha256"]
    route = by_role_id["capability_route_result"]["sha256"]
    plan = by_role_id["planning_result"]["sha256"]
    request = by_role_id["portfolio_request"]["sha256"]
    initial = by_role_id["initial_parent_budget"]["sha256"]
    final = by_role_id["final_parent_budget"]["sha256"]
    logical = by_role_id["logical_report"]["sha256"]
    portfolio_raw = by_role_id["portfolio_result"]["sha256"]
    _event(
        events,
        kind="run_opened",
        attempt_order=None,
        strategy_sha256=None,
        phase="run",
        outcome="opened",
        reason_code="RUN_OPENED",
        subjects=(planning, route, plan, request, initial),
        parent_before=initial,
        parent_after=initial,
    )
    input_inventory = _record_inventory_digest(
        records,
        {"session_event", "normalized_input", "session_context", "session_obligation", "session_artifact"},
    )
    _event(
        events,
        kind="input_bound",
        attempt_order=None,
        strategy_sha256=None,
        phase="input",
        outcome="bound",
        reason_code="INPUT_BOUND",
        subjects=(by_role_id["normalized_input"]["sha256"], input_inventory),
    )
    plan_inventory = _record_inventory_digest(records, {"plugin_descriptor", "execution_binding"})
    _event(
        events,
        kind="plan_bound",
        attempt_order=None,
        strategy_sha256=None,
        phase="plan",
        outcome="bound",
        reason_code="PLAN_BOUND",
        subjects=(plan, plan_inventory),
    )
    ledger_records = [
        record
        for record in records
        if record["role"] == "reconciled_parent_budget"
        and str(record["role_id"]).startswith("reconciled_parent_budget_")
    ]
    ledger_index = 0
    current_parent = str(initial)
    for attempt in portfolio.attempts:
        order = attempt.attempt_order
        strategy = attempt.strategy_sha256
        _event(
            events,
            kind="strategy_started",
            attempt_order=order,
            strategy_sha256=strategy,
            phase="plan",
            outcome="opened",
            reason_code="STRATEGY_STARTED",
            subjects=(strategy,),
            parent_before=current_parent,
            parent_after=current_parent,
        )
        if ledger_index >= len(ledger_records):
            raise _Invalid("producer reconciled ledger is absent")
        producer_after = str(ledger_records[ledger_index]["sha256"])
        ledger_index += 1
        if attempt.parent_budget_before_sha256 != current_parent:
            raise _Invalid("attempt parent-before ledger differs")
        if attempt.producer_worker_result_sha256 is None:
            raise _Invalid("attempt has no producer result identity")
        _event(
            events,
            kind="producer_completed",
            attempt_order=order,
            strategy_sha256=strategy,
            phase="producer",
            outcome=_worker_event_outcome(attempt.producer_status),
            reason_code=attempt.producer_reason_code,
            subjects=(strategy, attempt.producer_worker_result_sha256),
            parent_before=current_parent,
            parent_after=producer_after,
        )
        evidence_record = by_role_id.get(f"validated_evidence_{order:06d}")
        if (evidence_record is None) != (attempt.evidence_sha256 is None):
            raise _Invalid("attempt Evidence presence differs from audit records")
        checker_started = attempt.checker_worker_result_sha256 is not None
        if evidence_record is not None:
            if evidence_record["sha256"] != attempt.evidence_sha256:
                raise _Invalid("attempt Evidence identity differs")
            evidence_outcome = "success" if checker_started else attempt.outcome
            evidence_reason = "EVIDENCE_VALIDATED" if checker_started else {
                "unsupported": "EVIDENCE_UNSUPPORTED",
                "ambiguous": "EVIDENCE_INCOMPLETE",
                "cancelled": "EVIDENCE_CANCELLED",
                "exhausted": "EVIDENCE_EXHAUSTED",
                "truncated": "EVIDENCE_TRUNCATED",
                "producer_error": "EVIDENCE_ERROR",
                "invalid_evidence": "EVIDENCE_INVALID",
            }.get(attempt.outcome, "EVIDENCE_CLASSIFIED")
            _event(
                events,
                kind="evidence_classified",
                attempt_order=order,
                strategy_sha256=strategy,
                phase="producer",
                outcome=evidence_outcome,
                reason_code=evidence_reason,
                subjects=(strategy, str(evidence_record["sha256"])),
                parent_before=producer_after,
                parent_after=producer_after,
            )
        elif attempt.producer_status == "completed":
            _event(
                events,
                kind="evidence_classified",
                attempt_order=order,
                strategy_sha256=strategy,
                phase="producer",
                outcome=attempt.outcome,
                reason_code="EVIDENCE_NOT_RETAINED",
                subjects=(strategy, attempt.producer_worker_result_sha256),
                parent_before=producer_after,
                parent_after=producer_after,
            )
        attempt_after = producer_after
        if checker_started:
            if ledger_index >= len(ledger_records):
                raise _Invalid("checker reconciled ledger is absent")
            checker_after = str(ledger_records[ledger_index]["sha256"])
            ledger_index += 1
            _event(
                events,
                kind="checker_completed",
                attempt_order=order,
                strategy_sha256=strategy,
                phase="checker",
                outcome=_worker_event_outcome(attempt.checker_status),
                reason_code=attempt.checker_reason_code,
                subjects=(strategy, str(attempt.checker_worker_result_sha256)),
                parent_before=producer_after,
                parent_after=checker_after,
            )
            attempt_after = checker_after
            decision_record = by_role_id.get(f"checker_decision_{order:06d}")
            certificate_record = by_role_id.get(f"checker_certificate_{order:06d}")
            if (decision_record is None) != (attempt.checker_decision_sha256 is None):
                raise _Invalid("checker decision presence differs")
            if decision_record is not None:
                if certificate_record is None:
                    raise _Invalid("checker decision Certificate is absent")
                _event(
                    events,
                    kind="checker_decided",
                    attempt_order=order,
                    strategy_sha256=strategy,
                    phase="checker",
                    outcome="success" if attempt.outcome == "success" else attempt.outcome,
                    reason_code="CHECKER_DECIDED",
                    subjects=(strategy, str(decision_record["sha256"]), str(certificate_record["sha256"])),
                    parent_before=checker_after,
                    parent_after=checker_after,
                )
            elif certificate_record is not None:
                raise _Invalid("Certificate exists without a checker decision")
        if attempt.parent_budget_after_sha256 != attempt_after:
            raise _Invalid("attempt parent-after ledger differs")
        _event(
            events,
            kind="transition_selected",
            attempt_order=order,
            strategy_sha256=strategy,
            phase="transition",
            outcome=attempt.outcome,
            reason_code="TRANSITION_SELECTED",
            subjects=(strategy, attempt.transition_sha256),
            parent_before=attempt_after,
            parent_after=attempt_after,
        )
        current_parent = attempt_after
    if ledger_index != len(ledger_records) or current_parent != final:
        raise _Invalid("reconciled ledger inventory or final identity differs")
    _event(
        events,
        kind="run_closed",
        attempt_order=None,
        strategy_sha256=portfolio.selected_strategy_sha256,
        phase="run",
        outcome="closed",
        reason_code=portfolio.reason_code,
        subjects=(portfolio_raw, logical, final),
        parent_before=final,
        parent_after=final,
    )
    return events


def _validate_capture(
    captures: tuple[_PortfolioAuditAttempt, ...],
    result: ProofSearchPortfolioResult,
) -> None:
    if type(captures) is not tuple or len(captures) != len(result.attempts):
        raise _Invalid("captured attempt inventory differs")
    for capture, attempt in zip(captures, result.attempts):
        if type(capture) is not _PortfolioAuditAttempt:
            raise _Invalid("captured attempt type differs")
        decision_identity = None
        if capture.checker_decision is not None:
            if capture.certificate is None:
                raise _Invalid("captured checker decision has no Certificate")
            decision_identity = parse_portfolio_checker_decision(
                capture.checker_decision, capture.certificate
            ).decision_sha256
        if (
            capture.attempt_order != attempt.attempt_order
            or capture.strategy_sha256 != attempt.strategy_sha256
            or capture.producer_result_sha256 != attempt.producer_worker_result_sha256
            or capture.producer_status != attempt.producer_status
            or capture.producer_reason_code != attempt.producer_reason_code
            or capture.checker_result_sha256 != attempt.checker_worker_result_sha256
            or capture.checker_status != attempt.checker_status
            or capture.checker_reason_code != attempt.checker_reason_code
            or capture.outcome != attempt.outcome
            or capture.transition_sha256 != attempt.transition_sha256
            or _sha(capture.producer_parent_before) != attempt.parent_budget_before_sha256
            or _sha(capture.checker_parent_after if capture.checker_parent_after is not None else capture.producer_parent_after)
            != attempt.parent_budget_after_sha256
            or (None if capture.evidence is None else _sha(capture.evidence)) != attempt.evidence_sha256
            or decision_identity != attempt.checker_decision_sha256
        ):
            raise _Invalid("captured attempt differs from portfolio result")
        if (capture.checker_result_sha256 is None) != (capture.checker_parent_before is None) or (capture.checker_result_sha256 is None) != (capture.checker_parent_after is None):
            raise _Invalid("checker ledger presence differs")
        if capture.checker_parent_before is not None and capture.checker_parent_before != capture.producer_parent_after:
            raise _Invalid("producer/checker ledger handoff differs")
        for raw in (
            capture.producer_parent_before,
            capture.producer_parent_after,
            capture.checker_parent_before,
            capture.checker_parent_after,
            capture.evidence,
            capture.checker_decision,
            capture.certificate,
        ):
            if raw is not None and type(raw) is not bytes:
                raise _Invalid("captured bytes have a non-exact type")


def _build_bundle(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    result: ProofSearchPortfolioResult,
    captures: tuple[_PortfolioAuditAttempt, ...],
) -> RunAuditBundle:
    _validate_capture(captures, result)
    planning = parse_planning_request(planning_request)
    route_request = parse_capability_route_request(planning.route_request)
    request = parse_proof_search_portfolio_request(portfolio_request)
    final_parent = proof_search_portfolio_budget_bytes(result)
    result_raw = proof_search_portfolio_result_bytes(result)
    records: list[dict[str, object]] = []
    physical: dict[str, bytes] = {}

    def add(role: str, role_id: str, raw: bytes, binding_role: str | None = None) -> None:
        record = _record(len(records), role, role_id, raw, binding_role=binding_role)
        if any(item["role_id"] == role_id for item in records):
            raise _Invalid("duplicate audit semantic role")
        digest = str(record["sha256"])
        previous = physical.get(digest)
        if previous is not None and previous != raw:
            raise _Invalid("content digest collision")
        physical[digest] = raw
        records.append(record)

    add("planning_request", "planning_request", planning_request)
    add("capability_route_result", "capability_route_result", route_result)
    add("planning_result", "planning_result", planning_result)
    add("portfolio_request", "portfolio_request", portfolio_request)
    add("portfolio_result", "portfolio_result", result_raw)
    add("initial_parent_budget", "initial_parent_budget", parent_budget)

    artifact_bindings = request.artifact_bindings
    if len(artifact_bindings) != len(artifacts):
        raise _Invalid("portfolio artifact binding length differs")
    event_set = set(route_request.event_sha256s)
    session_set = set(route_request.session_artifact_sha256s)
    seen_event_ids: set[str] = set()
    seen_session_digests: set[str] = set()
    seen_raw_digests: set[str] = set()
    for index, (binding, raw) in enumerate(zip(artifact_bindings, artifacts)):
        digest = _sha(raw)
        if digest != binding.sha256 or len(raw) != binding.bytes:
            raise _Invalid("portfolio artifact bytes differ")
        if digest in seen_raw_digests:
            raise _Invalid("duplicate route artifact bytes")
        seen_raw_digests.add(digest)
        schema, parsed_artifact = _schema_of(raw, f"artifact_{index:06d}")
        event_identity = parsed_artifact.get("event_sha256")
        if schema == "mathhead.problem-session-event.v1" and event_identity in event_set:
            role = "session_event"
            role_id = f"session_event_{route_request.event_sha256s.index(str(event_identity)):06d}"
            seen_event_ids.add(str(event_identity))
        elif digest == route_request.normalization_result_sha256:
            role = "normalized_input"
            role_id = "normalized_input"
            seen_session_digests.add(digest)
        elif digest == route_request.session_context_sha256:
            role = "session_context"
            role_id = "session_context"
            seen_session_digests.add(digest)
        elif digest == route_request.obligation_artifact_sha256:
            role = "session_obligation"
            role_id = "session_obligation"
            seen_session_digests.add(digest)
        elif digest in session_set:
            role = "session_artifact"
            role_id = f"session_artifact_{route_request.session_artifact_sha256s.index(digest):06d}"
            seen_session_digests.add(digest)
        else:
            raise _Invalid("portfolio artifact is outside the current session closure")
        add(role, role_id, raw, binding.role)
    if seen_event_ids != event_set or seen_session_digests != session_set:
        raise _Invalid("current session artifact closure differs")

    descriptor_map = {_sha(raw): raw for raw in descriptors}
    if len(descriptor_map) != len(descriptors) or set(descriptor_map) != set(request.descriptor_sha256s):
        raise _Invalid("descriptor closure differs")
    for index, digest in enumerate(sorted(descriptor_map)):
        add("plugin_descriptor", f"plugin_descriptor_{index:06d}", descriptor_map[digest])

    binding_values = [parse_portfolio_execution_binding(raw) for raw in bindings]
    if tuple(_sha(raw) for raw in bindings) != request.binding_sha256s:
        raise _Invalid("execution binding closure differs")
    for item, raw in zip(binding_values, bindings):
        add("execution_binding", f"execution_binding_{item.plan_order:06d}", raw)

    ledger_order = 0
    for capture in captures:
        add(
            "reconciled_parent_budget",
            f"reconciled_parent_budget_{ledger_order:06d}",
            capture.producer_parent_after,
        )
        ledger_order += 1
        if capture.evidence is not None:
            add("validated_evidence", f"validated_evidence_{capture.attempt_order:06d}", capture.evidence)
        if capture.checker_parent_after is not None:
            add(
                "reconciled_parent_budget",
                f"reconciled_parent_budget_{ledger_order:06d}",
                capture.checker_parent_after,
            )
            ledger_order += 1
        if capture.certificate is not None:
            add("checker_certificate", f"checker_certificate_{capture.attempt_order:06d}", capture.certificate)
        if capture.checker_decision is not None:
            add("checker_decision", f"checker_decision_{capture.attempt_order:06d}", capture.checker_decision)
    add("reconciled_parent_budget", "final_parent_budget", final_parent)

    report_value = _report_mapping(
        planning_request=planning_request,
        route_result=route_result,
        planning_result=planning_result,
        portfolio_request=portfolio_request,
        normalized_input_sha256=route_request.normalization_result_sha256,
        initial_parent_budget=parent_budget,
        descriptors=descriptors,
        records=records,
        portfolio=result,
    )
    report_raw = _canonical(report_value)
    add("logical_report", "logical_report", report_raw)
    by_role_id = {str(record["role_id"]): record for record in records}
    events = _events_from_records(records, by_role_id, result)
    manifest_value: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "audited_run_contract_sha256": AUDITED_RUN_CONTRACT_SHA256,
        "replay_contract_sha256": REPLAY_CONTRACT_SHA256,
        "capability_registry_contract_sha256": CAPABILITY_REGISTRY_CONTRACT_SHA256,
        "deterministic_planner_contract_sha256": DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        "isolated_worker_contract_sha256": ISOLATED_WORKER_CONTRACT_SHA256,
        "proof_search_portfolio_contract_sha256": PORTFOLIO_CONTRACT_SHA256,
        "problem_session_contract_sha256": PROBLEM_SESSION_CONTRACT_SHA256,
        "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256,
        "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256,
        "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256,
        "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256,
        "normalized_input_sha256": route_request.normalization_result_sha256,
        "planning_request_sha256": _sha(planning_request),
        "route_result_sha256": _sha(route_result),
        "planning_result_sha256": _sha(planning_result),
        "portfolio_request_sha256": _sha(portfolio_request),
        "portfolio_result_sha256": _sha(result_raw),
        "initial_parent_budget_sha256": _sha(parent_budget),
        "final_parent_budget_sha256": _sha(final_parent),
        "logical_report_sha256": _sha(report_raw),
        "objects": records,
        "events": events,
        "manifest_sha256": None,
        "mathematical_authority": False,
    }
    manifest_value["manifest_sha256"] = _self_hash(manifest_value, "manifest_sha256")
    manifest_raw = _canonical(manifest_value)
    objects = tuple(physical[digest] for digest in sorted(physical))
    return _make(
        RunAuditBundle,
        manifest=manifest_raw,
        objects=objects,
        logical_report=report_raw,
        manifest_sha256=_sha(manifest_raw),
        logical_report_sha256=_sha(report_raw),
        mathematical_authority=False,
    )


def _fresh_inputs(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> None:
    if any(type(item) is not bytes for item in (planning_request, route_result, portfolio_request, planning_result, parent_budget)):
        raise _Invalid("audited byte inputs must be exact bytes")
    if any(type(value) is not tuple for value in (descriptors, bindings, artifacts)) or any(type(raw) is not bytes for raw in (*descriptors, *bindings, *artifacts)):
        raise _Invalid("audited inventories must be exact tuples of exact bytes")
    planning = parse_planning_request(planning_request)
    parse_capability_route_request(planning.route_request)
    supplied_route = parse_capability_route_result(route_result)
    fresh_route = route_capabilities(planning.route_request, descriptors, artifacts)
    if capability_route_result_bytes(fresh_route) != route_result or fresh_route != supplied_route:
        raise _Invalid("fresh capability route differs")
    fresh_plan = plan_strategies(planning_request, route_result, descriptors, artifacts)
    supplied_plan = parse_planning_result(planning_result)
    if planning_result_bytes(fresh_plan) != planning_result or fresh_plan != supplied_plan or fresh_plan.status != "planned":
        raise _Invalid("fresh deterministic plan differs or is not planned")
    request = parse_proof_search_portfolio_request(portfolio_request)
    if request.planning_result_sha256 != _sha(planning_result) or request.parent_budget_sha256 != _sha(parent_budget):
        raise _Invalid("portfolio request planning or parent identity differs")


def execute_audited_run(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    executable_paths: tuple[tuple[str, str], ...],
    workspace_root: str,
    cancel_event: Event | None = None,
) -> RunAuditBundle:
    """Execute one exact portfolio run and return its safe replayable bundle."""
    try:
        _fresh_inputs(
            planning_request,
            route_result,
            portfolio_request,
            planning_result,
            parent_budget,
            descriptors,
            bindings,
            artifacts,
        )
        result, captures = _run_portfolio_audited(
            portfolio_request,
            planning_result,
            parent_budget,
            descriptors,
            bindings,
            artifacts,
            executable_paths,
            workspace_root,
            cancel_event,
        )
        bundle = _build_bundle(
            planning_request,
            route_result,
            portfolio_request,
            planning_result,
            parent_budget,
            descriptors,
            bindings,
            artifacts,
            result,
            captures,
        )
        replay = replay_run_audit(bundle.manifest, bundle.objects)
        if replay.status != "complete" or replay.logical_report_sha256 != bundle.logical_report_sha256:
            raise _Invalid("freshly built audit does not replay complete")
        return bundle
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except RunAuditValidationError:
        raise
    except _Exhausted as exc:
        _fail("limit", "$", str(exc))
    except Exception as exc:
        _fail("result", "$", str(exc))


def _manifest(
    manifest: bytes,
    objects: tuple[bytes, ...],
) -> tuple[
    dict[str, object],
    list[dict[str, object]],
    dict[str, dict[str, object]],
    dict[str, bytes],
]:
    value = _parse(manifest, "manifest")
    fields_expected = {
        "schema",
        "audited_run_contract_sha256",
        "replay_contract_sha256",
        "capability_registry_contract_sha256",
        "deterministic_planner_contract_sha256",
        "isolated_worker_contract_sha256",
        "proof_search_portfolio_contract_sha256",
        "problem_session_contract_sha256",
        "resource_budget_contract_sha256",
        "evidence_contract_sha256",
        "certificate_contract_sha256",
        "theory_plugin_contract_sha256",
        "normalized_input_sha256",
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "portfolio_request_sha256",
        "portfolio_result_sha256",
        "initial_parent_budget_sha256",
        "final_parent_budget_sha256",
        "logical_report_sha256",
        "objects",
        "events",
        "manifest_sha256",
        "mathematical_authority",
    }
    _keys(value, fields_expected, "manifest")
    constants = {
        "schema": MANIFEST_SCHEMA,
        "audited_run_contract_sha256": AUDITED_RUN_CONTRACT_SHA256,
        "replay_contract_sha256": REPLAY_CONTRACT_SHA256,
        "capability_registry_contract_sha256": CAPABILITY_REGISTRY_CONTRACT_SHA256,
        "deterministic_planner_contract_sha256": DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        "isolated_worker_contract_sha256": ISOLATED_WORKER_CONTRACT_SHA256,
        "proof_search_portfolio_contract_sha256": PORTFOLIO_CONTRACT_SHA256,
        "problem_session_contract_sha256": PROBLEM_SESSION_CONTRACT_SHA256,
        "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256,
        "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256,
        "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256,
        "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256,
        "mathematical_authority": False,
    }
    if any(value[name] != expected for name, expected in constants.items()):
        raise _Invalid("manifest contract bindings differ")
    for name in (
        "normalized_input_sha256",
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "portfolio_request_sha256",
        "portfolio_result_sha256",
        "initial_parent_budget_sha256",
        "final_parent_budget_sha256",
        "logical_report_sha256",
    ):
        _digest(value[name], f"manifest.{name}")
    if _digest(value["manifest_sha256"], "manifest.manifest_sha256") != _self_hash(value, "manifest_sha256"):
        raise _Invalid("manifest self identity differs")
    raw_records = value["objects"]
    raw_events = value["events"]
    if type(raw_records) is not list or len(raw_records) < 8 or len(raw_records) > MAX_OBJECTS:
        raise _Exhausted("manifest object record budget exceeded")
    if type(raw_events) is not list or len(raw_events) < 4 or len(raw_events) > MAX_EVENTS:
        raise _Exhausted("manifest event budget exceeded")
    records = [_parse_record(item, index) for index, item in enumerate(raw_records)]
    role_ids = tuple(str(item["role_id"]) for item in records)
    if len(set(role_ids)) != len(role_ids):
        raise _Invalid("audit role IDs are not unique")
    by_role_id = {str(item["role_id"]): item for item in records}
    required = {
        "planning_request",
        "capability_route_result",
        "planning_result",
        "portfolio_request",
        "portfolio_result",
        "initial_parent_budget",
        "final_parent_budget",
        "normalized_input",
        "session_context",
        "session_obligation",
        "logical_report",
    }
    if not required <= set(by_role_id):
        raise _Invalid("required audit roles are absent")
    if type(objects) is not tuple or len(objects) > MAX_OBJECTS or any(type(raw) is not bytes for raw in objects):
        raise _Invalid("physical object tuple type or count differs")
    total = 0
    physical: dict[str, bytes] = {}
    order: list[str] = []
    for raw in objects:
        if not raw or len(raw) > MAX_OBJECT_BYTES:
            raise _Exhausted("physical object byte budget exceeded")
        total += len(raw)
        if total > MAX_AGGREGATE_BYTES:
            raise _Exhausted("aggregate object byte budget exceeded")
        digest = _sha(raw)
        if digest in physical:
            raise _Invalid("physical object tuple contains duplicate digest")
        physical[digest] = raw
        order.append(digest)
    if order != sorted(order):
        raise _Invalid("physical objects are not digest-sorted")
    record_digests = {str(item["sha256"]) for item in records}
    if set(physical) != record_digests:
        raise _Invalid("physical and semantic object closures differ")
    for record in records:
        raw = physical[str(record["sha256"])]
        if len(raw) != record["byte_count"]:
            raise _Invalid("physical object length differs")
        schema, _parsed = _schema_of(raw, str(record["role_id"]))
        if schema != record["artifact_schema"]:
            raise _Invalid("physical object schema differs")
    previous = None
    parsed_events: list[dict[str, object]] = []
    for index, item in enumerate(raw_events):
        event = _parse_event(item, index, previous)
        parsed_events.append(event)
        previous = str(event["event_sha256"])
    value["events"] = parsed_events
    value["objects"] = records
    return value, records, by_role_id, physical


def _complete_replay(
    manifest: bytes,
    objects: tuple[bytes, ...],
) -> tuple[dict[str, object], bytes, ProofSearchPortfolioResult]:
    manifest_value, records, by_role_id, physical = _manifest(manifest, objects)

    def raw(role_id: str) -> bytes:
        return physical[str(by_role_id[role_id]["sha256"])]

    planning_request = raw("planning_request")
    route_result = raw("capability_route_result")
    planning_result = raw("planning_result")
    portfolio_request = raw("portfolio_request")
    portfolio_result = raw("portfolio_result")
    initial_parent = raw("initial_parent_budget")
    final_parent = raw("final_parent_budget")
    logical_report = raw("logical_report")
    if (
        _sha(planning_request) != manifest_value["planning_request_sha256"]
        or _sha(route_result) != manifest_value["route_result_sha256"]
        or _sha(planning_result) != manifest_value["planning_result_sha256"]
        or _sha(portfolio_request) != manifest_value["portfolio_request_sha256"]
        or _sha(portfolio_result) != manifest_value["portfolio_result_sha256"]
        or _sha(initial_parent) != manifest_value["initial_parent_budget_sha256"]
        or _sha(final_parent) != manifest_value["final_parent_budget_sha256"]
        or _sha(logical_report) != manifest_value["logical_report_sha256"]
    ):
        raise _Invalid("manifest singleton object identities differ")
    planning = parse_planning_request(planning_request)
    route_request = parse_capability_route_request(planning.route_request)
    if route_request.normalization_result_sha256 != manifest_value["normalized_input_sha256"] or by_role_id["normalized_input"]["sha256"] != route_request.normalization_result_sha256:
        raise _Invalid("normalized input identity differs")
    request = parse_proof_search_portfolio_request(portfolio_request)
    descriptor_records = [item for item in records if item["role"] == "plugin_descriptor"]
    descriptor_map = {str(item["sha256"]): physical[str(item["sha256"])] for item in descriptor_records}
    if set(descriptor_map) != set(request.descriptor_sha256s):
        raise _Invalid("descriptor object closure differs")
    descriptors = tuple(descriptor_map[digest] for digest in request.descriptor_sha256s)
    binding_records = [item for item in records if item["role"] == "execution_binding"]
    binding_map: dict[str, bytes] = {}
    for item in binding_records:
        binding_raw = physical[str(item["sha256"])]
        parse_portfolio_execution_binding(binding_raw)
        binding_map[_sha(binding_raw)] = binding_raw
    if set(binding_map) != set(request.binding_sha256s):
        raise _Invalid("execution binding object closure differs")
    artifact_map: dict[str, bytes] = {}
    for item in records:
        binding_role = item["binding_role"]
        if binding_role is not None:
            if binding_role in artifact_map:
                raise _Invalid("duplicate portfolio artifact binding role")
            artifact_map[str(binding_role)] = physical[str(item["sha256"])]
    expected_roles = tuple(binding.role for binding in request.artifact_bindings)
    if set(artifact_map) != set(expected_roles) or len(artifact_map) != len(expected_roles):
        raise _Invalid("portfolio artifact binding closure differs")
    artifacts = tuple(artifact_map[role] for role in expected_roles)
    fresh_route = route_capabilities(planning.route_request, descriptors, artifacts)
    if capability_route_result_bytes(fresh_route) != route_result:
        raise _Invalid("fresh route differs")
    fresh_plan = plan_strategies(planning_request, route_result, descriptors, artifacts)
    if planning_result_bytes(fresh_plan) != planning_result:
        raise _Invalid("fresh plan differs")
    if request.planning_result_sha256 != _sha(planning_result) or request.parent_budget_sha256 != _sha(initial_parent):
        raise _Invalid("portfolio request input identities differ")
    selected_evidence_record = None
    selected_certificate_record = None
    portfolio_value = _parse(portfolio_result, "portfolio_result")
    selected_evidence_sha = portfolio_value.get("selected_evidence_sha256")
    selected_certificate_sha = portfolio_value.get("selected_certificate_sha256")
    if selected_evidence_sha is not None:
        selected_evidence_record = next(
            (item for item in records if item["role"] == "validated_evidence" and item["sha256"] == selected_evidence_sha),
            None,
        )
    if selected_certificate_sha is not None:
        selected_certificate_record = next(
            (item for item in records if item["role"] == "checker_certificate" and item["sha256"] == selected_certificate_sha),
            None,
        )
    selected_evidence = None if selected_evidence_record is None else physical[str(selected_evidence_record["sha256"])]
    selected_certificate = None if selected_certificate_record is None else physical[str(selected_certificate_record["sha256"])]
    portfolio = parse_proof_search_portfolio_result(
        portfolio_result,
        final_parent,
        selected_evidence,
        selected_certificate,
    )
    if portfolio.initial_parent_budget_sha256 != _sha(initial_parent) or portfolio.final_parent_budget_sha256 != _sha(final_parent):
        raise _Invalid("portfolio ledger endpoints differ")
    for attempt in portfolio.attempts:
        decision_record = by_role_id.get(
            f"checker_decision_{attempt.attempt_order:06d}"
        )
        certificate_record = by_role_id.get(
            f"checker_certificate_{attempt.attempt_order:06d}"
        )
        if (decision_record is None) != (attempt.checker_decision_sha256 is None):
            raise _Invalid("checker decision object presence differs")
        if decision_record is not None:
            if certificate_record is None:
                raise _Invalid("checker decision has no Certificate object")
            decision = parse_portfolio_checker_decision(
                physical[str(decision_record["sha256"])],
                physical[str(certificate_record["sha256"])],
            )
            if decision.decision_sha256 != attempt.checker_decision_sha256:
                raise _Invalid("checker decision semantic identity differs")
        elif certificate_record is not None:
            raise _Invalid("Certificate object exists without checker decision")
    if portfolio.status == "succeeded":
        if selected_evidence is None or selected_certificate is None:
            raise _Invalid("selected Evidence or Certificate is absent")
        decision_record = by_role_id.get(
            f"checker_decision_{portfolio.attempts[-1].attempt_order:06d}"
        )
        if decision_record is None:
            raise _Invalid("selected checker decision is absent")
        decision = parse_portfolio_checker_decision(
            physical[str(decision_record["sha256"])], selected_certificate
        )
        if (
            not decision.agreement
            or decision.decision_sha256
            != portfolio.selected_checker_decision_sha256
            or decision.evidence_sha256 != _sha(selected_evidence)
        ):
            raise _Invalid("selected checker decision does not agree")
    report_value = _report_mapping(
        planning_request=planning_request,
        route_result=route_result,
        planning_result=planning_result,
        portfolio_request=portfolio_request,
        normalized_input_sha256=route_request.normalization_result_sha256,
        initial_parent_budget=initial_parent,
        descriptors=descriptors,
        records=[item for item in records if item["role"] != "logical_report"],
        portfolio=portfolio,
    )
    _validate_report(_parse(logical_report, "logical_report"))
    if _canonical(report_value) != logical_report:
        raise _Invalid("logical report differs from independent reconstruction")
    expected_events = _events_from_records(records, by_role_id, portfolio)
    if expected_events != manifest_value["events"]:
        raise _Invalid("event transcript differs from independent reconstruction")
    return manifest_value, logical_report, portfolio


def _replay_mapping(value: RunAuditReplayResult, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "contract_id": value.contract_id,
        "contract_sha256": value.contract_sha256,
        "status": value.status,
        "reason_code": value.reason_code,
        "manifest_sha256": value.manifest_sha256,
        "bundle_sha256": value.bundle_sha256,
        "logical_report_sha256": value.logical_report_sha256,
        "object_count": value.object_count,
        "event_count": value.event_count,
        "portfolio_status": value.portfolio_status,
        "mathematical_verdict": value.mathematical_verdict,
        "authority_tier": value.authority_tier,
        "replay_result_sha256": value.replay_result_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _new_replay(
    *,
    status: str,
    reason_code: str,
    manifest: bytes | None,
    objects: tuple[bytes, ...] | None,
    logical_report: bytes | None = None,
    event_count: int = 0,
    portfolio: ProofSearchPortfolioResult | None = None,
) -> RunAuditReplayResult:
    complete = status == "complete"
    mapping: dict[str, object] = {
        "schema": REPLAY_RESULT_SCHEMA,
        "contract_id": REPLAY_CONTRACT_ID,
        "contract_sha256": REPLAY_CONTRACT_SHA256,
        "status": status,
        "reason_code": reason_code,
        "manifest_sha256": _sha(manifest) if complete and manifest is not None else None,
        "bundle_sha256": _sha(manifest) if complete and manifest is not None else None,
        "logical_report_sha256": _sha(logical_report) if complete and logical_report is not None else None,
        "object_count": 0 if objects is None else len(objects),
        "event_count": event_count if complete else 0,
        "portfolio_status": None if portfolio is None or not complete else portfolio.status,
        "mathematical_verdict": None if portfolio is None or not complete else portfolio.mathematical_verdict,
        "authority_tier": None if portfolio is None or not complete else portfolio.authority_tier,
        "replay_result_sha256": None,
        "mathematical_authority": False,
    }
    mapping["replay_result_sha256"] = _self_hash(mapping, "replay_result_sha256")
    return _make(
        RunAuditReplayResult,
        **mapping,
        _input_manifest=manifest,
        _input_objects=objects,
        _logical_report=logical_report,
    )


def replay_run_audit(manifest: bytes, objects: tuple[bytes, ...]) -> RunAuditReplayResult:
    """Independently replay hostile audit bytes without executing producers."""
    retained_manifest = manifest if type(manifest) is bytes else None
    retained_objects = objects if type(objects) is tuple and all(type(item) is bytes for item in objects) else None
    try:
        if retained_manifest is None or retained_objects is None:
            raise _Invalid("replay inputs must be exact bytes and exact tuple bytes")
        manifest_value, logical_report, portfolio = _complete_replay(
            retained_manifest, retained_objects
        )
        return _new_replay(
            status="complete",
            reason_code="REPLAY_COMPLETE",
            manifest=retained_manifest,
            objects=retained_objects,
            logical_report=logical_report,
            event_count=len(manifest_value["events"]),
            portfolio=portfolio,
        )
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except _Exhausted:
        return _new_replay(
            status="exhausted",
            reason_code="REPLAY_BUDGET_EXHAUSTED",
            manifest=retained_manifest,
            objects=retained_objects,
        )
    except Exception:
        return _new_replay(
            status="invalid",
            reason_code="REPLAY_INVALID",
            manifest=retained_manifest,
            objects=retained_objects,
        )


def validate_run_audit_bundle(value: RunAuditBundle) -> None:
    if type(value) is not RunAuditBundle:
        _fail("type", "$", "expected exact RunAuditBundle")
    if (
        type(value.manifest) is not bytes
        or type(value.objects) is not tuple
        or any(type(raw) is not bytes for raw in value.objects)
        or type(value.logical_report) is not bytes
        or value.manifest_sha256 != _sha(value.manifest)
        or value.logical_report_sha256 != _sha(value.logical_report)
        or value.mathematical_authority is not False
    ):
        _fail("result", "$", "bundle fields or identities differ")
    replay = replay_run_audit(value.manifest, value.objects)
    if replay.status != "complete" or replay.logical_report_sha256 != value.logical_report_sha256:
        _fail("result", "$", "bundle does not freshly replay complete")
    logical = next((raw for raw in value.objects if _sha(raw) == value.logical_report_sha256), None)
    if logical != value.logical_report:
        _fail("result", "$.logical_report", "retained logical report differs")


def _bundle_from_replayed_bytes(
    manifest: bytes, objects: tuple[bytes, ...]
) -> RunAuditBundle:
    replay = replay_run_audit(manifest, objects)
    if replay.status != "complete" or replay.logical_report_sha256 is None:
        _fail("result", "$", "bundle bytes do not replay complete")
    logical = next(
        (raw for raw in objects if _sha(raw) == replay.logical_report_sha256), None
    )
    if logical is None:
        _fail("result", "$.logical_report", "logical report object is absent")
    return _make(
        RunAuditBundle,
        manifest=manifest,
        objects=objects,
        logical_report=logical,
        manifest_sha256=_sha(manifest),
        logical_report_sha256=_sha(logical),
        mathematical_authority=False,
    )


def run_audit_manifest_bytes(value: RunAuditBundle) -> bytes:
    validate_run_audit_bundle(value)
    return value.manifest


def run_audit_object_bytes(value: RunAuditBundle) -> tuple[bytes, ...]:
    validate_run_audit_bundle(value)
    return value.objects


def run_audit_logical_report_bytes(value: RunAuditBundle) -> bytes:
    validate_run_audit_bundle(value)
    return value.logical_report


def run_audit_bundle_sha256(value: RunAuditBundle) -> str:
    validate_run_audit_bundle(value)
    return value.manifest_sha256


def validate_run_audit_replay_result(value: RunAuditReplayResult) -> None:
    if type(value) is not RunAuditReplayResult:
        _fail("type", "$", "expected exact RunAuditReplayResult")
    mapping = _replay_mapping(value)
    if (
        value.schema != REPLAY_RESULT_SCHEMA
        or value.contract_id != REPLAY_CONTRACT_ID
        or value.contract_sha256 != REPLAY_CONTRACT_SHA256
        or value.mathematical_authority is not False
        or value.status not in {"complete", "invalid", "exhausted"}
        or value.replay_result_sha256 != _self_hash(mapping, "replay_result_sha256")
    ):
        _fail("result", "$", "replay result binding differs")
    if value._input_manifest is None or value._input_objects is None:
        expected = _new_replay(
            status=value.status,
            reason_code=value.reason_code,
            manifest=None,
            objects=None,
        )
    else:
        expected = replay_run_audit(value._input_manifest, value._input_objects)
    if _replay_mapping(expected) != mapping:
        _fail("result", "$", "replay result differs from fresh replay")


def run_audit_replay_result_bytes(value: RunAuditReplayResult) -> bytes:
    validate_run_audit_replay_result(value)
    return _canonical(_replay_mapping(value))


def parse_run_audit_replay_result(
    data: bytes,
    manifest: bytes,
    objects: tuple[bytes, ...],
) -> RunAuditReplayResult:
    parsed = _parse(data, "replay_result")
    expected = replay_run_audit(manifest, objects)
    if _canonical(_replay_mapping(expected)) != data or parsed != _replay_mapping(expected):
        _fail("result", "$", "serialized replay result differs from fresh replay")
    return expected


__all__ = [
    "AUDITED_RUN_CONTRACT_ID",
    "AUDITED_RUN_CONTRACT_SHA256",
    "EVENT_SCHEMA",
    "LOGICAL_REPORT_SCHEMA",
    "MANIFEST_SCHEMA",
    "OBJECT_SCHEMA",
    "REPLAY_CONTRACT_ID",
    "REPLAY_CONTRACT_SHA256",
    "REPLAY_RESULT_SCHEMA",
    "RunAuditBundle",
    "RunAuditReplayResult",
    "RunAuditValidationError",
    "SCHEMA_SHA256S",
    "execute_audited_run",
    "parse_run_audit_replay_result",
    "replay_run_audit",
    "run_audit_bundle_sha256",
    "run_audit_logical_report_bytes",
    "run_audit_manifest_bytes",
    "run_audit_object_bytes",
    "run_audit_replay_result_bytes",
    "validate_run_audit_bundle",
    "validate_run_audit_replay_result",
]
