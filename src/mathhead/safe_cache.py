"""Pure content-addressed reuse decisions for governed audited runs."""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from types import MappingProxyType
import unicodedata
from typing import Any, Final, NoReturn

from .capability_registry import parse_capability_route_request
from .deterministic_planner import parse_planning_request, parse_planning_result
from .execution_provenance import (
    EXECUTION_CONFIGURATION_BINDINGS,
    EXECUTION_CONTRACT_BINDINGS,
    EXECUTION_IMPLEMENTATION_BINDINGS,
    EXECUTION_SCHEMA_BINDINGS,
    PROVENANCE_SCHEMA,
    TRUST_POLICY_SHA256 as EXECUTION_TRUST_POLICY_SHA256,
    ExecutionProvenanceError,
    parse_execution_provenance,
)
from .isolated_worker import _parse_parent_budget
from .proof_search_portfolio import (
    make_proof_search_portfolio_request,
    parse_portfolio_checker_decision,
    parse_portfolio_execution_binding,
    parse_proof_search_portfolio_request,
    parse_proof_search_portfolio_result,
)
from .run_audit import RunAuditBundle, _fresh_inputs, replay_run_audit


CONTRACT_ID: Final = "MH-C-SAFE-CACHE-002"
CONTRACT_SHA256: Final = (
    "35cd004a1ed91f2c3969a6b295722b8099ee9fc36f3fc15170d5d1082d2bfab4"
)
REQUEST_SCHEMA: Final = "mathhead.safe-cache-request.v2"
ENTRY_SCHEMA: Final = "mathhead.safe-cache-entry.v2"
DECISION_SCHEMA: Final = "mathhead.safe-cache-decision-result.v2"
SCHEMA_SHA256S: Final = MappingProxyType({
    REQUEST_SCHEMA: "3ad6e7111ceb0c6336315a0bbbe6950e60abd2331e9ce0c9dbb52e60f285a18a",
    ENTRY_SCHEMA: "ce1100b9326d04a07c4f22286f28814f1a3bcef9091ca7b13f6ee9ebd57f9234",
    DECISION_SCHEMA: "30df479781c7f022da8ffaee8686118fa7613b6e49f522da88362db46f48965d",
})

MAX_INPUT_EACH: Final = 1_073_741_824
MAX_AGGREGATE_INPUT: Final = 5_368_709_120
MAX_OBJECTS: Final = 200_000
MAX_JSON_NODES: Final = 12_000_000
MAX_JSON_DEPTH: Final = 128
MAX_STRING: Final = 1_048_576
MAX_VALUE_BYTES: Final = 67_108_864
INTEGER_MAXIMUM: Final = 9_007_199_254_740_991

_DIGEST = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[a-z][a-z0-9_.-]{0,254}")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?")

CONTRACT_BINDINGS: Final = EXECUTION_CONTRACT_BINDINGS
SCHEMA_BINDINGS: Final = EXECUTION_SCHEMA_BINDINGS
IMPLEMENTATION_BINDINGS: Final = EXECUTION_IMPLEMENTATION_BINDINGS
CONFIGURATION_BINDINGS: Final = EXECUTION_CONFIGURATION_BINDINGS
TRUST_POLICY_SHA256: Final = EXECUTION_TRUST_POLICY_SHA256


class SafeCacheValidationError(ValueError):
    """Strict safe-cache codec or relation failure."""

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


class _CacheValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_FINAL:
            raise TypeError("safe-cache value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class SafeCacheEntry(_CacheValue):
    schema: str
    safe_cache_contract_sha256: str
    lookup_key_sha256: str
    execution_provenance_sha256: str
    audit_manifest_sha256: str
    logical_report_sha256: str
    portfolio_result_sha256: str
    selected_strategy_sha256: str
    selected_descriptor_sha256: str
    plugin_id: str
    plugin_version: str
    producer_component_id: str
    checker_component_id: str
    selected_evidence_sha256: str
    selected_certificate_sha256: str
    selected_checker_decision_sha256: str
    evidence_format_sha256: str
    certificate_format_sha256: str
    historical_authority_tier: str
    eligibility: str
    entry_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("safe-cache entries are decision-owned")


@dataclass(frozen=True, slots=True, init=False)
class SafeCacheDecision(_CacheValue):
    schema: str
    contract_id: str
    contract_sha256: str
    status: str
    reason_code: str
    lookup_key_sha256: str | None
    entry: SafeCacheEntry | None
    entry_sha256: str | None
    audit_manifest_sha256: str | None
    logical_report_sha256: str | None
    portfolio_result_sha256: str | None
    selected_evidence_sha256: str | None
    selected_certificate_sha256: str | None
    selected_checker_decision_sha256: str | None
    historical_authority_tier: str | None
    decision_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("safe-cache decisions are boundary-owned")


_PUBLIC_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(values: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _walk(value: object, depth: int = 0, nodes: list[int] | None = None) -> None:
    counter = [0] if nodes is None else nodes
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise _Exhausted("JSON work budget exceeded")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > INTEGER_MAXIMUM:
            raise _Invalid("integer outside canonical range")
        return
    if type(value) is str:
        if len(value) > MAX_STRING or "\x00" in value or unicodedata.normalize("NFC", value) != value:
            raise _Invalid("string outside canonical form")
        return
    if type(value) is list:
        for item in value:
            _walk(item, depth + 1, counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _Invalid("object key is not text")
            _walk(key, depth + 1, counter)
            _walk(item, depth + 1, counter)
        return
    raise _Invalid("unsupported JSON value")


def _canonical(value: object, maximum: int = MAX_VALUE_BYTES) -> bytes:
    _walk(value)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    if len(raw) > maximum:
        raise _Exhausted("canonical byte budget exceeded")
    return raw


def _parse(data: bytes, path: str = "$", maximum: int = MAX_VALUE_BYTES) -> dict[str, object]:
    if type(data) is not bytes:
        raise _Invalid(f"{path} must be exact bytes")
    if len(data) > maximum:
        raise _Exhausted(f"{path} byte budget exceeded")
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_float=lambda _: (_ for _ in ()).throw(_Invalid("floats forbidden")))
    except _DuplicateKey as exc:
        raise _Invalid(f"{path} duplicate key {exc}") from exc
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _Invalid(f"{path} invalid JSON") from exc
    _walk(value)
    if type(value) is not dict or _canonical(value, maximum) != data:
        raise _Invalid(f"{path} is not canonical object bytes")
    return value


def _digest(value: object, path: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise _Invalid(f"{path} must be a full digest")
    return value


def _text(value: object, path: str, pattern: re.Pattern[str] = _ID) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise _Invalid(f"{path} is invalid text")
    return value


def _thaw(value: object) -> object:
    entries = getattr(value, "entries", None)
    if type(entries) is tuple:
        return {key: _thaw(item) for key, item in entries}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _format_sha(value: object | None) -> str | None:
    return None if value is None else _sha(_canonical(_thaw(value)))


def _entry_mapping(value: SafeCacheEntry, own_hash: bool = True) -> dict[str, object]:
    return {
        field.name: (None if field.name == "entry_sha256" and not own_hash else getattr(value, field.name))
        for field in fields(SafeCacheEntry)
    }


def _entry_from_mapping(value: object) -> SafeCacheEntry:
    expected = {field.name for field in fields(SafeCacheEntry)}
    if type(value) is not dict or set(value) != expected:
        raise _Invalid("entry fields differ")
    if value["schema"] != ENTRY_SCHEMA or value["safe_cache_contract_sha256"] != CONTRACT_SHA256:
        raise _Invalid("entry constants differ")
    digests = expected - {
        "schema", "plugin_id", "plugin_version", "producer_component_id",
        "checker_component_id", "historical_authority_tier", "eligibility",
        "mathematical_authority",
    }
    for name in digests:
        _digest(value[name], f"entry.{name}")
    _text(value["plugin_id"], "entry.plugin_id")
    _text(value["producer_component_id"], "entry.producer_component_id")
    _text(value["checker_component_id"], "entry.checker_component_id")
    _text(value["plugin_version"], "entry.plugin_version", _SEMVER)
    if value["historical_authority_tier"] not in {"checker_attestation", "external_proof_assistant"}:
        raise _Invalid("entry authority tier differs")
    if value["eligibility"] != "eligible_checked" or value["mathematical_authority"] is not False:
        raise _Invalid("entry eligibility or authority differs")
    result = _make(SafeCacheEntry, **value)
    if result.entry_sha256 != _sha(_canonical(_entry_mapping(result, False))):
        raise _Invalid("entry identity differs")
    return result


def safe_cache_entry_bytes(value: SafeCacheEntry) -> bytes:
    validate_safe_cache_entry(value)
    return _canonical(_entry_mapping(value))


def parse_safe_cache_entry(data: bytes) -> SafeCacheEntry:
    try:
        return _entry_from_mapping(_parse(data))
    except (_Invalid, _Exhausted) as exc:
        raise SafeCacheValidationError("entry", "$", str(exc)) from exc


def validate_safe_cache_entry(value: SafeCacheEntry) -> None:
    if type(value) is not SafeCacheEntry:
        raise SafeCacheValidationError("type", "$", "expected exact SafeCacheEntry")
    try:
        if _entry_from_mapping(_entry_mapping(value)) != value:
            raise _Invalid("entry reconstruction differs")
    except (_Invalid, _Exhausted, AttributeError) as exc:
        raise SafeCacheValidationError("entry", "$", str(exc)) from exc


def _decision_mapping(value: SafeCacheDecision, own_hash: bool = True) -> dict[str, object]:
    result = {
        field.name: (None if field.name == "decision_sha256" and not own_hash else getattr(value, field.name))
        for field in fields(SafeCacheDecision)
    }
    result["entry"] = None if value.entry is None else _entry_mapping(value.entry)
    return result


def _decision_shape(value: dict[str, object]) -> None:
    status = value["status"]
    reason = value["reason_code"]
    history = (
        "audit_manifest_sha256", "logical_report_sha256", "portfolio_result_sha256",
        "selected_evidence_sha256", "selected_certificate_sha256",
        "selected_checker_decision_sha256", "historical_authority_tier",
    )
    null_history = all(value[name] is None for name in history)
    no_entry = value["entry"] is None and value["entry_sha256"] is None
    if status == "hit":
        if reason != "CACHE_HIT" or value["lookup_key_sha256"] is None or no_entry or any(value[name] is None for name in history):
            raise _Invalid("hit shape differs")
    elif status == "miss":
        if reason != "CACHE_CANDIDATE_ABSENT" or value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("miss shape differs")
    elif status == "ineligible" and reason == "CACHE_OUTCOME_INELIGIBLE":
        if value["lookup_key_sha256"] is None or not no_entry or any(value[name] is None for name in history[:3]) or any(value[name] is not None for name in history[3:]):
            raise _Invalid("outcome-ineligible shape differs")
    elif status == "ineligible" and reason == "CACHE_AUTHORITY_INELIGIBLE":
        if value["lookup_key_sha256"] is None or not no_entry or any(value[name] is None for name in history[:6]) or value["historical_authority_tier"] is not None:
            raise _Invalid("authority-ineligible shape differs")
    elif status == "invalid" and reason == "CACHE_CURRENT_REQUEST_INVALID":
        if value["lookup_key_sha256"] is not None or not no_entry or not null_history:
            raise _Invalid("request-invalid shape differs")
    elif status == "invalid" and reason in {
        "CACHE_CONTEXT_MISMATCH", "CACHE_CONTRACT_MISMATCH",
        "CACHE_IMPLEMENTATION_MISMATCH", "CACHE_CONFIGURATION_MISMATCH",
        "CACHE_ARTIFACT_MISMATCH", "CACHE_BUDGET_MISMATCH",
        "CACHE_TRUST_POLICY_MISMATCH", "CACHE_REPLAY_INVALID",
    }:
        if value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("candidate-invalid shape differs")
    elif status == "exhausted" and reason == "CACHE_DECISION_BUDGET_EXHAUSTED":
        if value["lookup_key_sha256"] is not None or not no_entry or not null_history:
            raise _Invalid("decision-exhausted shape differs")
    elif status == "exhausted" and reason == "CACHE_REPLAY_EXHAUSTED":
        if value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("replay-exhausted shape differs")
    else:
        raise _Invalid("status/reason pair differs")


def _decision_from_mapping(value: object) -> SafeCacheDecision:
    expected = {field.name for field in fields(SafeCacheDecision)}
    if type(value) is not dict or set(value) != expected:
        raise _Invalid("decision fields differ")
    if value["schema"] != DECISION_SCHEMA or value["contract_id"] != CONTRACT_ID or value["contract_sha256"] != CONTRACT_SHA256 or value["mathematical_authority"] is not False:
        raise _Invalid("decision constants differ")
    for name in (
        "lookup_key_sha256", "entry_sha256", "audit_manifest_sha256",
        "logical_report_sha256", "portfolio_result_sha256", "selected_evidence_sha256",
        "selected_certificate_sha256", "selected_checker_decision_sha256",
        "historical_authority_tier",
    ):
        if value[name] is not None and name != "historical_authority_tier":
            _digest(value[name], f"decision.{name}")
    if value["historical_authority_tier"] not in {
        None, "checker_attestation", "external_proof_assistant"
    }:
        raise _Invalid("decision authority tier differs")
    _digest(value["decision_sha256"], "decision.decision_sha256")
    entry = None if value["entry"] is None else _entry_from_mapping(value["entry"])
    normalized = dict(value)
    normalized["entry"] = entry
    _decision_shape(normalized)
    if entry is not None:
        relations = {
            "lookup_key_sha256": entry.lookup_key_sha256,
            "entry_sha256": entry.entry_sha256,
            "audit_manifest_sha256": entry.audit_manifest_sha256,
            "logical_report_sha256": entry.logical_report_sha256,
            "portfolio_result_sha256": entry.portfolio_result_sha256,
            "selected_evidence_sha256": entry.selected_evidence_sha256,
            "selected_certificate_sha256": entry.selected_certificate_sha256,
            "selected_checker_decision_sha256": entry.selected_checker_decision_sha256,
            "historical_authority_tier": entry.historical_authority_tier,
        }
        if any(value[name] != expected for name, expected in relations.items()):
            raise _Invalid("decision entry relation differs")
    result = _make(SafeCacheDecision, **normalized)
    if result.decision_sha256 != _sha(_canonical(_decision_mapping(result, False))):
        raise _Invalid("decision identity differs")
    return result


def safe_cache_decision_bytes(value: SafeCacheDecision) -> bytes:
    validate_safe_cache_decision(value)
    return _canonical(_decision_mapping(value))


def parse_safe_cache_decision(data: bytes) -> SafeCacheDecision:
    try:
        return _decision_from_mapping(_parse(data))
    except (_Invalid, _Exhausted) as exc:
        raise SafeCacheValidationError("decision", "$", str(exc)) from exc


def validate_safe_cache_decision(value: SafeCacheDecision) -> None:
    if type(value) is not SafeCacheDecision:
        raise SafeCacheValidationError("type", "$", "expected exact SafeCacheDecision")
    try:
        if _decision_from_mapping(_decision_mapping(value)) != value:
            raise _Invalid("decision reconstruction differs")
    except (_Invalid, _Exhausted, AttributeError) as exc:
        raise SafeCacheValidationError("decision", "$", str(exc)) from exc


def _new_decision(
    status: str,
    reason: str,
    lookup_key: str | None,
    *,
    entry: SafeCacheEntry | None = None,
    manifest: str | None = None,
    report: str | None = None,
    portfolio: str | None = None,
    evidence: str | None = None,
    certificate: str | None = None,
    checker: str | None = None,
    tier: str | None = None,
) -> SafeCacheDecision:
    mapping: dict[str, object] = {
        "schema": DECISION_SCHEMA, "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256, "status": status,
        "reason_code": reason, "lookup_key_sha256": lookup_key,
        "entry": None if entry is None else _entry_mapping(entry),
        "entry_sha256": None if entry is None else entry.entry_sha256,
        "audit_manifest_sha256": manifest, "logical_report_sha256": report,
        "portfolio_result_sha256": portfolio, "selected_evidence_sha256": evidence,
        "selected_certificate_sha256": certificate,
        "selected_checker_decision_sha256": checker,
        "historical_authority_tier": tier, "decision_sha256": None,
        "mathematical_authority": False,
    }
    mapping["decision_sha256"] = _sha(_canonical(mapping))
    return _decision_from_mapping(mapping)


def _expected_execution_provenance_sha256() -> str:
    preimage: dict[str, object] = {
        "schema": PROVENANCE_SCHEMA,
        "dependency_contracts": dict(CONTRACT_BINDINGS),
        "dependency_schemas": dict(SCHEMA_BINDINGS),
        "implementation_bindings": dict(IMPLEMENTATION_BINDINGS),
        "configuration_bindings": dict(CONFIGURATION_BINDINGS),
        "trust_policy_sha256": TRUST_POLICY_SHA256,
        "provenance_sha256": None,
        "mathematical_authority": False,
    }
    return _sha(_canonical(preimage))


def _current_request(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> dict[str, object]:
    singles = (planning_request, route_result, portfolio_request, planning_result, parent_budget)
    if any(type(raw) is not bytes or len(raw) > MAX_INPUT_EACH for raw in singles):
        raise _Invalid("current byte inputs differ")
    if any(type(values) is not tuple for values in (descriptors, bindings, artifacts)):
        raise _Invalid("current inventories must be exact tuples")
    all_inventory = (*descriptors, *bindings, *artifacts)
    if any(type(raw) is not bytes or len(raw) > MAX_INPUT_EACH for raw in all_inventory):
        raise _Invalid("current inventory bytes differ")
    if len(descriptors) > 10_000 or len(bindings) > 100_000 or len(artifacts) > MAX_OBJECTS:
        raise _Exhausted("current inventory count exceeded")
    if sum(map(len, singles + all_inventory)) > MAX_AGGREGATE_INPUT:
        raise _Exhausted("aggregate input bytes exceeded")
    _fresh_inputs(planning_request, route_result, portfolio_request, planning_result, parent_budget, descriptors, bindings, artifacts)
    planning = parse_planning_request(planning_request)
    route = parse_capability_route_request(planning.route_request)
    plan = parse_planning_result(planning_result)
    request = parse_proof_search_portfolio_request(portfolio_request)
    parent = _parse_parent_budget(parent_budget)
    if tuple(_sha(raw) for raw in bindings) != request.binding_sha256s or tuple(sorted(_sha(raw) for raw in descriptors)) != request.descriptor_sha256s:
        raise _Invalid("portfolio descriptor or binding closure differs")
    parsed_bindings = tuple(parse_portfolio_execution_binding(raw) for raw in bindings)
    by_digest: dict[str, bytes] = {}
    for raw in artifacts:
        digest = _sha(raw)
        if digest in by_digest:
            raise _Invalid("duplicate input artifact bytes")
        by_digest[digest] = raw
    pairs: list[tuple[str, bytes]] = []
    artifact_map: dict[str, object] = {}
    for binding in request.artifact_bindings:
        raw = by_digest.get(binding.sha256)
        if raw is None or len(raw) != binding.bytes or binding.role in artifact_map:
            raise _Invalid("artifact role closure differs")
        pairs.append((binding.role, raw))
        artifact_map[binding.role] = {"sha256": binding.sha256, "bytes": binding.bytes}
    if len(pairs) != len(artifacts):
        raise _Invalid("surplus input artifacts")
    rebuilt = make_proof_search_portfolio_request(
        planning_result=planning_result, parent_budget=parent_budget,
        descriptors=descriptors, bindings=bindings, artifacts=tuple(pairs),
    )
    if rebuilt != portfolio_request or len(plan.strategies) != len(bindings):
        raise _Invalid("portfolio request reconstruction differs")
    for strategy, binding in zip(plan.strategies, parsed_bindings):
        if (
            binding.plan_order != strategy.plan_order
            or binding.strategy_sha256 != strategy.strategy_sha256
            or binding.descriptor_sha256 != strategy.descriptor_sha256
            or binding.producer_component_id != strategy.producer_component_id
            or binding.checker_component_id != strategy.checker_component_id
        ):
            raise _Invalid("strategy execution binding differs")
    limits = parent.value.get("limits")
    if type(limits) is not dict:
        raise _Invalid("parent limits absent")
    descriptor_values = {_sha(raw): _parse(raw, "descriptor") for raw in descriptors}
    strategy_formats: dict[str, tuple[str | None, str | None]] = {}
    for item in plan.strategies:
        descriptor = descriptor_values.get(item.descriptor_sha256)
        capabilities = None if descriptor is None else descriptor.get("capabilities")
        if type(capabilities) is not list:
            raise _Invalid("descriptor capabilities absent")
        matches = [
            capability for capability in capabilities
            if type(capability) is dict and capability.get("capability_id") == item.capability_id
        ]
        if len(matches) != 1:
            raise _Invalid("strategy capability descriptor differs")
        capability = matches[0]
        evidence_formats = capability.get("evidence_formats")
        certificate_formats = capability.get("certificate_formats")
        if type(evidence_formats) is not list or len(evidence_formats) != 1:
            raise _Invalid("evidence format selection is not exact")
        if type(certificate_formats) is not list or len(certificate_formats) != 1:
            raise _Invalid("certificate format selection is not exact")
        evidence_format = _format_sha(item.evidence_expectation.evidence_format)
        certificate_format = _format_sha(item.evidence_expectation.certificate_format)
        strategy_formats[item.strategy_sha256] = (
            evidence_format or _sha(_canonical(evidence_formats[0])),
            certificate_format or _sha(_canonical(certificate_formats[0])),
        )
    entry_formats = strategy_formats.get(str(plan.entry_strategy_sha256))
    if entry_formats is None:
        raise _Invalid("entry strategy formats absent")
    value: dict[str, object] = {
        "schema": REQUEST_SCHEMA,
        "safe_cache_contract_sha256": CONTRACT_SHA256,
        "dependency_contracts": dict(CONTRACT_BINDINGS),
        "dependency_schemas": dict(SCHEMA_BINDINGS),
        "implementation_bindings": dict(IMPLEMENTATION_BINDINGS),
        "configuration_bindings": dict(CONFIGURATION_BINDINGS),
        "expected_execution_provenance_sha256": (
            _expected_execution_provenance_sha256()
        ),
        "planning_request_sha256": _sha(planning_request),
        "route_result_sha256": _sha(route_result),
        "planning_result_sha256": _sha(planning_result),
        "portfolio_request_sha256": _sha(portfolio_request),
        "initial_parent_budget_sha256": _sha(parent_budget),
        "session_id": route.session_id,
        "session_head_sha256": route.session_head_sha256,
        "event_sha256s": list(route.event_sha256s),
        "session_artifact_sha256s": list(route.session_artifact_sha256s),
        "reading_id": route.reading_id,
        "session_context_sha256": route.session_context_sha256,
        "normalization_result_sha256": route.normalization_result_sha256,
        "normalized_input_sha256": route.normalization_result_sha256,
        "obligation_record_id": route.session_obligation_record_id,
        "obligation_artifact_sha256": route.obligation_artifact_sha256,
        "obligation_semantic_sha256": route.obligation_semantic_sha256,
        "local_context_semantic_sha256": route.local_context_semantic_sha256,
        "capability_kind": route.capability_kind, "operation": route.operation,
        "availability_sha256": route.availability.availability_sha256,
        "platform": route.availability.platform,
        "python_version": route.availability.python_version,
        "replay_mode": route.replay_mode,
        "evidence_format_sha256": _format_sha(route.evidence_format) or entry_formats[0],
        "certificate_format_sha256": _format_sha(route.certificate_format) or entry_formats[1],
        "descriptor_sha256s": list(request.descriptor_sha256s),
        "strategy_sha256s": [item.strategy_sha256 for item in plan.strategies],
        "execution_binding_sha256s": list(request.binding_sha256s),
        "input_artifacts": artifact_map,
        "initial_parent_limits_sha256": _sha(_canonical(limits)),
        "child_resource_request_sha256s": [
            item.resource_request.resource_request_sha256 for item in plan.strategies
        ],
        "trust_policy_sha256": TRUST_POLICY_SHA256,
        "lookup_key_sha256": None,
        "mathematical_authority": False,
    }
    value["lookup_key_sha256"] = _sha(_canonical(value))
    value["_strategy_formats"] = strategy_formats
    return value


def _relation_reason(
    manifest: dict[str, object],
    provenance: dict[str, object],
    request: dict[str, object],
) -> str | None:
    for field, reason in (
        ("dependency_contracts", "CACHE_CONTRACT_MISMATCH"),
        ("dependency_schemas", "CACHE_CONTRACT_MISMATCH"),
        ("implementation_bindings", "CACHE_IMPLEMENTATION_MISMATCH"),
        ("configuration_bindings", "CACHE_CONFIGURATION_MISMATCH"),
        ("trust_policy_sha256", "CACHE_TRUST_POLICY_MISMATCH"),
    ):
        if provenance.get(field) != request[field]:
            return reason
    if provenance.get("provenance_sha256") != request[
        "expected_execution_provenance_sha256"
    ]:
        return "CACHE_REPLAY_INVALID"
    for field in (
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "normalized_input_sha256",
    ):
        if manifest.get(field) != request[field]:
            return "CACHE_CONTEXT_MISMATCH"
    if manifest.get("portfolio_request_sha256") != request["portfolio_request_sha256"]:
        return "CACHE_ARTIFACT_MISMATCH"
    if manifest.get("initial_parent_budget_sha256") != request[
        "initial_parent_budget_sha256"
    ]:
        return "CACHE_BUDGET_MISMATCH"
    return None


def _record(records: list[object], role: str) -> dict[str, object]:
    matches = [item for item in records if type(item) is dict and item.get("role") == role]
    if len(matches) != 1:
        raise _Invalid(f"exact {role} record absent")
    return matches[0]


def _candidate_view(
    candidate: RunAuditBundle,
    request: dict[str, object],
) -> tuple[
    dict[str, object],
    dict[str, object],
    dict[str, object],
    dict[str, bytes],
]:
    if (
        type(candidate) is not RunAuditBundle
        or type(candidate.manifest) is not bytes
        or type(candidate.objects) is not tuple
        or any(type(raw) is not bytes for raw in candidate.objects)
        or type(candidate.logical_report) is not bytes
        or candidate.manifest_sha256 != _sha(candidate.manifest)
        or candidate.logical_report_sha256 != _sha(candidate.logical_report)
        or candidate.mathematical_authority is not False
    ):
        raise _Invalid("candidate outer fields differ")
    replay = replay_run_audit(candidate.manifest, candidate.objects)
    if replay.status == "exhausted":
        raise _Exhausted("candidate replay budget exhausted")
    if replay.status != "complete" or replay.logical_report_sha256 != candidate.logical_report_sha256:
        raise _Invalid("candidate replay invalid")
    manifest = _parse(candidate.manifest, "manifest", MAX_VALUE_BYTES)
    report = _parse(candidate.logical_report, "logical_report", MAX_VALUE_BYTES)
    objects = {_sha(raw): raw for raw in candidate.objects}
    if len(objects) != len(candidate.objects) or objects.get(candidate.logical_report_sha256) != candidate.logical_report:
        raise _Invalid("candidate object closure differs")
    records = manifest.get("objects")
    if type(records) is not list:
        raise _Invalid("CACHE_REPLAY_INVALID")
    provenance_record = _record(records, "execution_provenance")
    provenance_raw = objects.get(str(provenance_record.get("sha256")))
    if provenance_raw is None:
        raise _Invalid("CACHE_REPLAY_INVALID")
    try:
        provenance = parse_execution_provenance(provenance_raw)
    except ExecutionProvenanceError as exc:
        raise _Invalid("CACHE_REPLAY_INVALID") from exc
    provenance_sha256 = provenance.get("provenance_sha256")
    if (
        provenance_sha256 != manifest.get("execution_provenance_sha256")
        or provenance_sha256 != report.get("execution_provenance_sha256")
        or provenance_sha256 != replay.execution_provenance_sha256
    ):
        raise _Invalid("CACHE_REPLAY_INVALID")
    reason = _relation_reason(manifest, provenance, request)
    if reason is not None:
        raise _Invalid(reason)
    return manifest, report, provenance, objects


def _make_entry(
    request: dict[str, object], candidate: RunAuditBundle,
    manifest: dict[str, object], report: dict[str, object],
    provenance: dict[str, object], objects: dict[str, bytes],
) -> SafeCacheEntry:
    records = manifest.get("objects")
    if type(records) is not list:
        raise _Invalid("manifest records absent")
    portfolio_record = _record(records, "portfolio_result")
    final_record = next(
        (item for item in records if type(item) is dict and item.get("role_id") == "final_parent_budget"),
        None,
    )
    if type(final_record) is not dict:
        raise _Invalid("final parent record absent")
    evidence_sha = report.get("selected_evidence_sha256")
    certificate_sha = report.get("selected_certificate_sha256")
    checker_identity = report.get("selected_checker_decision_sha256")
    strategy_sha = report.get("selected_strategy_sha256")
    if any(type(item) is not str for item in (evidence_sha, certificate_sha, checker_identity, strategy_sha)):
        raise _Invalid("selected chain absent")
    evidence = objects.get(str(evidence_sha))
    certificate = objects.get(str(certificate_sha))
    checker_records = [
        item for item in records
        if type(item) is dict and item.get("role") == "checker_decision"
    ]
    checker_raw = None
    checker = None
    for record in checker_records:
        raw = objects.get(str(record.get("sha256")))
        if raw is None:
            continue
        parsed = parse_portfolio_checker_decision(raw, certificate)
        if parsed.decision_sha256 == checker_identity:
            checker_raw, checker = raw, parsed
            break
    final_parent = objects.get(str(final_record.get("sha256")))
    portfolio_raw = objects.get(str(portfolio_record.get("sha256")))
    if None in {evidence, certificate, checker_raw, final_parent, portfolio_raw} or checker is None:
        raise _Invalid("selected object chain absent")
    portfolio = parse_proof_search_portfolio_result(
        portfolio_raw, final_parent, evidence, certificate
    )
    if (
        portfolio.status != "succeeded"
        or portfolio.mathematical_verdict not in {"proved", "refuted"}
        or portfolio.authority_tier not in {"checker_attestation", "external_proof_assistant"}
        or portfolio.selected_strategy_sha256 != strategy_sha
        or portfolio.selected_evidence_sha256 != evidence_sha
        or portfolio.selected_certificate_sha256 != certificate_sha
        or portfolio.selected_checker_decision_sha256 != checker_identity
        or checker.agreement is not True
    ):
        raise _Invalid("selected checked outcome differs")
    plugins = report.get("plugins")
    if type(plugins) is not list:
        raise _Invalid("plugin inventory absent")
    selected = [item for item in plugins if type(item) is dict and item.get("strategy_sha256") == strategy_sha]
    if len(selected) != 1:
        raise _Invalid("selected plugin differs")
    plugin = selected[0]
    strategy_formats = request.get("_strategy_formats")
    formats = strategy_formats.get(str(strategy_sha)) if type(strategy_formats) is dict else None
    if type(formats) is not tuple or len(formats) != 2:
        raise _Invalid("selected format inventory absent")
    evidence_format, certificate_format = formats
    if type(evidence_format) is not str or type(certificate_format) is not str:
        raise _Invalid("selected formats are not cacheable")
    mapping: dict[str, object] = {
        "schema": ENTRY_SCHEMA, "safe_cache_contract_sha256": CONTRACT_SHA256,
        "lookup_key_sha256": request["lookup_key_sha256"],
        "execution_provenance_sha256": provenance["provenance_sha256"],
        "audit_manifest_sha256": candidate.manifest_sha256,
        "logical_report_sha256": candidate.logical_report_sha256,
        "portfolio_result_sha256": portfolio_record["sha256"],
        "selected_strategy_sha256": strategy_sha,
        "selected_descriptor_sha256": plugin.get("descriptor_sha256"),
        "plugin_id": plugin.get("plugin_id"), "plugin_version": plugin.get("plugin_version"),
        "producer_component_id": plugin.get("producer_component_id"),
        "checker_component_id": plugin.get("checker_component_id"),
        "selected_evidence_sha256": evidence_sha,
        "selected_certificate_sha256": certificate_sha,
        "selected_checker_decision_sha256": checker_identity,
        "evidence_format_sha256": evidence_format,
        "certificate_format_sha256": certificate_format,
        "historical_authority_tier": portfolio.authority_tier,
        "eligibility": "eligible_checked", "entry_sha256": None,
        "mathematical_authority": False,
    }
    mapping["entry_sha256"] = _sha(_canonical(mapping))
    return _entry_from_mapping(mapping)


def decide_safe_cache(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    candidate: RunAuditBundle | None,
) -> SafeCacheDecision:
    """Return a pure zero-authority reuse decision for one explicit candidate."""
    try:
        current = _current_request(
            planning_request, route_result, portfolio_request, planning_result,
            parent_budget, descriptors, bindings, artifacts,
        )
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except _Exhausted:
        return _new_decision("exhausted", "CACHE_DECISION_BUDGET_EXHAUSTED", None)
    except Exception:
        return _new_decision("invalid", "CACHE_CURRENT_REQUEST_INVALID", None)
    lookup = str(current["lookup_key_sha256"])
    if candidate is None:
        return _new_decision("miss", "CACHE_CANDIDATE_ABSENT", lookup)
    try:
        manifest, report, provenance, objects = _candidate_view(candidate, current)
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except _Exhausted:
        return _new_decision("exhausted", "CACHE_REPLAY_EXHAUSTED", lookup)
    except _Invalid as exc:
        reason = str(exc)
        if reason not in {
            "CACHE_CONTEXT_MISMATCH", "CACHE_CONTRACT_MISMATCH",
            "CACHE_IMPLEMENTATION_MISMATCH", "CACHE_CONFIGURATION_MISMATCH",
            "CACHE_ARTIFACT_MISMATCH", "CACHE_BUDGET_MISMATCH",
            "CACHE_TRUST_POLICY_MISMATCH",
        }:
            reason = "CACHE_REPLAY_INVALID"
        return _new_decision("invalid", reason, lookup)
    portfolio_sha = manifest.get("portfolio_result_sha256")
    if (
        report.get("status") != "succeeded"
        or report.get("mathematical_verdict") not in {"proved", "refuted"}
    ):
        return _new_decision(
            "ineligible", "CACHE_OUTCOME_INELIGIBLE", lookup,
            manifest=candidate.manifest_sha256, report=candidate.logical_report_sha256,
            portfolio=str(portfolio_sha),
        )
    try:
        entry = _make_entry(
            current,
            candidate,
            manifest,
            report,
            provenance,
            objects,
        )
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        evidence = report.get("selected_evidence_sha256")
        certificate = report.get("selected_certificate_sha256")
        checker = report.get("selected_checker_decision_sha256")
        if all(type(item) is str for item in (evidence, certificate, checker)):
            return _new_decision(
                "ineligible", "CACHE_AUTHORITY_INELIGIBLE", lookup,
                manifest=candidate.manifest_sha256, report=candidate.logical_report_sha256,
                portfolio=str(portfolio_sha), evidence=str(evidence),
                certificate=str(certificate), checker=str(checker),
            )
        return _new_decision("invalid", "CACHE_REPLAY_INVALID", lookup)
    return _new_decision(
        "hit", "CACHE_HIT", lookup, entry=entry,
        manifest=entry.audit_manifest_sha256, report=entry.logical_report_sha256,
        portfolio=entry.portfolio_result_sha256,
        evidence=entry.selected_evidence_sha256,
        certificate=entry.selected_certificate_sha256,
        checker=entry.selected_checker_decision_sha256,
        tier=entry.historical_authority_tier,
    )


__all__ = [
    "CONTRACT_ID", "CONTRACT_SHA256", "SCHEMA_SHA256S",
    "SafeCacheEntry", "SafeCacheDecision", "SafeCacheValidationError",
    "decide_safe_cache", "safe_cache_entry_bytes", "parse_safe_cache_entry",
    "validate_safe_cache_entry", "safe_cache_decision_bytes",
    "parse_safe_cache_decision", "validate_safe_cache_decision",
]
