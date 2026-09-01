"""Deterministic proof/search portfolio over isolated producer and checker workers.

The orchestrator never imports or trusts a plugin.  It consumes an exact plan,
constructs every worker request itself, conserves the returned parent ledger,
and promotes only a separately checked canonical Evidence/Certificate pair.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from threading import Event
from typing import Any, Final, NoReturn
import unicodedata

from mathhead.capability_registry import _validate_descriptor as _validate_theory_plugin_descriptor
from mathhead.deterministic_planner import (
    CAPABILITY_REGISTRY_CONTRACT_SHA256,
    CERTIFICATE_CONTRACT_SHA256,
    CONTRACT_SHA256 as DETERMINISTIC_PLANNER_CONTRACT_SHA256,
    ENGINE_RESULT_CONTRACT_SHA256,
    EVIDENCE_CONTRACT_SHA256,
    RESOURCE_DIMENSIONS,
    RESOURCE_BUDGET_CONTRACT_SHA256,
    THEORY_PLUGIN_CONTRACT_SHA256,
    DeterministicPlannerValidationError,
    PlanningResult,
    PlanningStrategy,
    parse_planning_result,
)
from mathhead.isolated_worker import (
    ISOLATED_WORKER_CONTRACT_SHA256,
    IsolatedWorkerResult,
    _parse_parent_budget as _validate_parent_budget,
    isolated_worker_budget_bytes,
    isolated_worker_result_bytes,
    parse_isolated_worker_request,
    supervise_worker,
    validate_isolated_worker_result,
    worker_artifact_bytes,
)


PORTFOLIO_CONTRACT_ID: Final = "MH-C-PROOF-SEARCH-PORTFOLIO-001"
PORTFOLIO_CONTRACT_SHA256: Final = (
    "b59384b54d10665528540e470a3e5b6f7eae8bdcce198d6814a7459c073e0144"
)
TRUST_TRANSITION_CONTRACT_SHA256: Final = (
    "7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796"
)

BINDING_SCHEMA: Final = "mathhead.portfolio-execution-binding.v1"
REQUEST_SCHEMA: Final = "mathhead.proof-search-portfolio-request.v1"
DECISION_SCHEMA: Final = "mathhead.portfolio-checker-decision.v1"
ATTEMPT_SCHEMA: Final = "mathhead.portfolio-attempt.v1"
INCONCLUSIVE_SCHEMA: Final = "mathhead.portfolio-inconclusive.v1"
RESULT_SCHEMA: Final = "mathhead.proof-search-portfolio-result.v1"

SCHEMA_SHA256S: Final = {
    BINDING_SCHEMA: "ab39704148ac4de4489dc68b08b726a696a7794db4543b891ad311ec5b594e65",
    REQUEST_SCHEMA: "61d8d774612de377715e881806a3de8c57a03ee631c50c24400d322ff15a32bd",
    DECISION_SCHEMA: "88ab41ac83589290879d390bf4c711583b0366297b2435b73d0208a7ce09f15c",
    ATTEMPT_SCHEMA: "fc12eb424c86d938282fed47ae814f03b9970b32642ccaee3c7226086abf0158",
    INCONCLUSIVE_SCHEMA: "4a2a98d58dfb4182b96b4bcafc01fd95292a1da9e7e8cb29eaa8d36cb784b8c1",
    RESULT_SCHEMA: "336d3b09259e119cd37fa3ffcf2405a6806827adc59edecab4c3dc29030fb99c",
}

PREFERENCE_POLICY: Final = "planner_order_no_sound_witness_declaration"
INTEGER_MAXIMUM: Final = 9_007_199_254_740_991
MAX_INPUT_BYTES: Final = 1_073_741_824
MAX_ARTIFACT_BYTES: Final = 67_108_864
MAX_CHECKER_PAYLOAD_BYTES: Final = 1_048_576
MAX_ITEMS: Final = 100_000
MAX_ARGUMENTS: Final = 128
MAX_WORKER_ARGUMENT_CODEPOINTS: Final = 4096
MAX_STRING: Final = 1_048_576
MAX_DEPTH: Final = 128
MAX_NODES: Final = 8_000_000

_SHA = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")
_NAMESPACED = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_CONTRACT = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]*$")
_SEMVER = re.compile(r"^1\.([0-9]+)\.([0-9]+)(?:-[0-9A-Za-z.-]+)?$")
_FAMILIES: Final = ("sympy", "enumeration", "smt", "external")
_WORKER_STATUSES: Final = (
    "not_started", "completed", "refused", "unsupported", "exhausted",
    "cancelled", "failed", "invalid",
)
_OUTCOMES: Final = (
    "success", "unsupported", "exhausted", "cancelled", "producer_error",
    "ambiguous", "truncated", "checker_inconclusive", "checker_disagreement",
    "verifier_failure", "invalid_evidence",
)
_INCONCLUSIVE_OUTCOMES: Final = (
    "unsupported", "producer_error", "ambiguous", "truncated",
    "checker_inconclusive", "checker_disagreement", "invalid_evidence",
)
_TERMINAL_STATUSES: Final = (
    "succeeded", "unsupported", "exhausted", "cancelled", "failed",
    "ambiguous", "truncated", "inconclusive", "disagreement",
    "verifier_failed", "invalid_evidence", "invalid",
)


class ProofSearchPortfolioValidationError(ValueError):
    """Classified strict-codec or boundary validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{kind}: {path}: {detail}")
        self.kind = kind
        self.path = path


class _OrdinaryFailure(ValueError):
    def __init__(self, status: str, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.reason = reason


class _DuplicateKey(ValueError):
    pass


_PUBLIC_VALUES_FINAL = False


class _PortfolioValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_VALUES_FINAL:
            raise TypeError("proof/search portfolio value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class PortfolioArtifactBinding(_PortfolioValue):
    role: str
    sha256: str
    bytes: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("artifact bindings are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class PortfolioExecutionBinding(_PortfolioValue):
    schema: str
    plan_order: int
    strategy_sha256: str
    descriptor_sha256: str
    producer_component_id: str
    checker_component_id: str
    producer_family: str
    checker_family: str
    producer_executable_sha256: str
    checker_executable_sha256: str
    producer_arguments: tuple[str, ...]
    checker_arguments: tuple[str, ...]
    input_artifacts: tuple[PortfolioArtifactBinding, ...]
    protocol: str
    binding_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("execution bindings are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class ProofSearchPortfolioRequest(_PortfolioValue):
    schema: str
    planning_result_sha256: str
    parent_budget_sha256: str
    descriptor_sha256s: tuple[str, ...]
    binding_sha256s: tuple[str, ...]
    artifact_bindings: tuple[PortfolioArtifactBinding, ...]
    preference_policy: str
    request_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("portfolio requests are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class PortfolioCheckerDecision(_PortfolioValue):
    schema: str
    strategy_sha256: str
    producer_component_id: str
    checker_component_id: str
    subject_sha256: str
    claim: str
    evidence_sha256: str | None
    evidence_bytes: int
    certificate_sha256: str | None
    certificate_bytes: int
    certificate_verdict: str
    certificate_authority: str
    agreement: bool
    reason_code: str
    decision_sha256: str
    mathematical_authority: bool
    _certificate: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("checker decisions are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class PortfolioAttempt(_PortfolioValue):
    schema: str
    attempt_order: int
    strategy_sha256: str
    producer_worker_result_sha256: str | None
    producer_status: str
    producer_reason_code: str
    evidence_sha256: str | None
    evidence_bytes: int
    checker_worker_result_sha256: str | None
    checker_status: str
    checker_reason_code: str
    checker_decision_sha256: str | None
    outcome: str
    transition_sha256: str
    parent_budget_before_sha256: str
    parent_budget_after_sha256: str
    attempt_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("portfolio attempts are orchestrator-owned")


@dataclass(frozen=True, slots=True, init=False)
class PortfolioInconclusive(_PortfolioValue):
    schema: str
    attempt_order: int
    strategy_sha256: str
    outcome: str
    reason_code: str
    producer_worker_result_sha256: str | None
    checker_worker_result_sha256: str | None
    inconclusive_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("inconclusive records are orchestrator-owned")


@dataclass(frozen=True, slots=True, init=False)
class ProofSearchPortfolioResult(_PortfolioValue):
    schema: str
    contract_id: str
    contract_sha256: str
    deterministic_planner_contract_sha256: str
    isolated_worker_contract_sha256: str
    resource_budget_contract_sha256: str
    engine_result_contract_sha256: str
    evidence_contract_sha256: str
    certificate_contract_sha256: str
    theory_plugin_contract_sha256: str
    capability_registry_contract_sha256: str
    trust_transition_contract_sha256: str
    status: str
    mathematical_verdict: str
    reason_code: str
    request_sha256: str | None
    planning_result_sha256: str | None
    initial_parent_budget_sha256: str | None
    final_parent_budget_sha256: str | None
    preference_policy: str
    attempts: tuple[PortfolioAttempt, ...]
    inconclusive_outcomes: tuple[PortfolioInconclusive, ...]
    selected_strategy_sha256: str | None
    selected_evidence_sha256: str | None
    selected_certificate_sha256: str | None
    selected_checker_decision_sha256: str | None
    authority_tier: str
    result_sha256: str | None
    mathematical_authority: bool
    _final_parent_budget: bytes | None
    _selected_evidence: bytes | None
    _selected_certificate: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("portfolio results are orchestrator-owned")


_PUBLIC_VALUES_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    instance = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(instance, field.name, values[field.name])
    return instance


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ProofSearchPortfolioValidationError(kind, path, detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _walk(value: object) -> None:
    stack: list[tuple[object, int, str]] = [(value, 1, "$")]
    nodes = 0
    while stack:
        item, depth, path = stack.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            _fail("limit", path, "JSON structural ceiling exceeded")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if item < -INTEGER_MAXIMUM or item > INTEGER_MAXIMUM:
                _fail("limit", path, "integer outside portable range")
            continue
        if type(item) is float:
            _fail("schema", path, "floats are forbidden")
        if type(item) is str:
            if len(item) > MAX_STRING or "\x00" in item or unicodedata.normalize("NFC", item) != item:
                _fail("canonical", path, "invalid string")
            continue
        if type(item) is list:
            if len(item) > MAX_ITEMS:
                _fail("limit", path, "array ceiling exceeded")
            for index, child in enumerate(reversed(item)):
                stack.append((child, depth + 1, f"{path}[{len(item) - index - 1}]"))
            continue
        if type(item) is dict:
            if len(item) > MAX_ITEMS or any(type(key) is not str for key in item):
                _fail("schema", path, "invalid object")
            for key, child in reversed(tuple(item.items())):
                stack.append((child, depth + 1, f"{path}.{key}"))
            continue
        _fail("schema", path, "non-JSON value")


def _canonical(value: object, *, maximum: int = MAX_INPUT_BYTES) -> bytes:
    _walk(value)
    try:
        raw = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    except (TypeError, ValueError, UnicodeError) as exc:
        _fail("encoding", "$", str(exc))
    if len(raw) > maximum:
        _fail("limit", "$", "canonical byte ceiling exceeded")
    return raw


def _parse(data: bytes, path: str, *, maximum: int = MAX_INPUT_BYTES) -> dict[str, object]:
    if type(data) is not bytes or not data or len(data) > maximum:
        _fail("type", path, "expected bounded exact bytes")
    try:
        value = json.loads(data.decode(), object_pairs_hook=_pairs)
    except _DuplicateKey as exc:
        _fail("duplicate", path, f"duplicate key: {exc}")
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail("json", path, str(exc))
    if type(value) is not dict:
        _fail("schema", path, "root must be an object")
    if _canonical(value, maximum=maximum) != data:
        _fail("canonical", path, "bytes are not canonical")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        _fail("schema", path, "object fields differ")
    return value


def _text(value: object, path: str, *, pattern: re.Pattern[str] | None = None, maximum: int = MAX_STRING) -> str:
    if type(value) is not str or not value or len(value) > maximum or "\x00" in value or unicodedata.normalize("NFC", value) != value or (pattern is not None and not pattern.fullmatch(value)):
        _fail("schema", path, "invalid text")
    return value


def _digest(value: object, path: str) -> str:
    return _text(value, path, pattern=_SHA, maximum=64)


def _nullable_digest(value: object, path: str) -> str | None:
    return None if value is None else _digest(value, path)


def _quantity(value: object, path: str) -> int:
    if type(value) is not int or not 0 <= value <= INTEGER_MAXIMUM:
        _fail("schema", path, "invalid quantity")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail("schema", path, "expected boolean")
    return value


def _choice(value: object, choices: tuple[str, ...], path: str) -> str:
    result = _text(value, path, maximum=64)
    if result not in choices:
        _fail("schema", path, "unknown enum member")
    return result


def _self_hash(mapping: dict[str, object], name: str) -> str:
    value = dict(mapping)
    value[name] = None
    return _sha(_canonical(value))


def _binding_value(value: PortfolioArtifactBinding) -> dict[str, object]:
    return {"role": value.role, "sha256": value.sha256, "bytes": value.bytes}


def _artifact_binding(value: object, path: str) -> PortfolioArtifactBinding:
    item = _keys(value, {"role", "sha256", "bytes"}, path)
    return _make(PortfolioArtifactBinding, role=_text(item["role"], f"{path}.role", pattern=_ID, maximum=64), sha256=_digest(item["sha256"], f"{path}.sha256"), bytes=_quantity(item["bytes"], f"{path}.bytes"))


def _artifact_bindings(value: object, path: str) -> tuple[PortfolioArtifactBinding, ...]:
    if type(value) is not list or len(value) > MAX_ITEMS:
        _fail("limit", path, "artifact binding ceiling exceeded")
    result = tuple(_artifact_binding(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len({item.role for item in result}) != len(result) or len({(item.sha256, item.bytes) for item in result}) != len(result):
        _fail("artifact", path, "artifact roles and content bindings must be unique")
    return result


def _arguments(value: object, path: str) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_ARGUMENTS:
        _fail("limit", path, "argument ceiling exceeded")
    return tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(value))


def _binding_mapping(value: PortfolioExecutionBinding, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "plan_order": value.plan_order,
        "strategy_sha256": value.strategy_sha256, "descriptor_sha256": value.descriptor_sha256,
        "producer_component_id": value.producer_component_id,
        "checker_component_id": value.checker_component_id,
        "producer_family": value.producer_family, "checker_family": value.checker_family,
        "producer_executable_sha256": value.producer_executable_sha256,
        "checker_executable_sha256": value.checker_executable_sha256,
        "producer_arguments": list(value.producer_arguments),
        "checker_arguments": list(value.checker_arguments),
        "input_artifacts": [_binding_value(item) for item in value.input_artifacts],
        "protocol": value.protocol,
        "binding_sha256": value.binding_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _binding_from_mapping(value: object, path: str = "$") -> PortfolioExecutionBinding:
    expected = {"schema", "plan_order", "strategy_sha256", "descriptor_sha256", "producer_component_id", "checker_component_id", "producer_family", "checker_family", "producer_executable_sha256", "checker_executable_sha256", "producer_arguments", "checker_arguments", "input_artifacts", "protocol", "binding_sha256", "mathematical_authority"}
    item = _keys(value, expected, path)
    if item["schema"] != BINDING_SCHEMA or item["protocol"] != "canonical_evidence_certificate_v1" or item["mathematical_authority"] is not False:
        _fail("schema", path, "execution binding constants differ")
    result = _make(
        PortfolioExecutionBinding, schema=BINDING_SCHEMA,
        plan_order=_quantity(item["plan_order"], f"{path}.plan_order"),
        strategy_sha256=_digest(item["strategy_sha256"], f"{path}.strategy_sha256"),
        descriptor_sha256=_digest(item["descriptor_sha256"], f"{path}.descriptor_sha256"),
        producer_component_id=_text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64),
        checker_component_id=_text(item["checker_component_id"], f"{path}.checker_component_id", pattern=_ID, maximum=64),
        producer_family=_choice(item["producer_family"], _FAMILIES, f"{path}.producer_family"),
        checker_family=_choice(item["checker_family"], _FAMILIES, f"{path}.checker_family"),
        producer_executable_sha256=_digest(item["producer_executable_sha256"], f"{path}.producer_executable_sha256"),
        checker_executable_sha256=_digest(item["checker_executable_sha256"], f"{path}.checker_executable_sha256"),
        producer_arguments=_arguments(item["producer_arguments"], f"{path}.producer_arguments"),
        checker_arguments=_arguments(item["checker_arguments"], f"{path}.checker_arguments"),
        input_artifacts=_artifact_bindings(item["input_artifacts"], f"{path}.input_artifacts"),
        protocol="canonical_evidence_certificate_v1",
        binding_sha256=_digest(item["binding_sha256"], f"{path}.binding_sha256"),
        mathematical_authority=False,
    )
    if result.producer_component_id == result.checker_component_id or result.binding_sha256 != _self_hash(_binding_mapping(result), "binding_sha256"):
        _fail("identity", path, "execution binding identity or separation differs")
    return result


def make_portfolio_execution_binding(*, plan_order: int, strategy_sha256: str, descriptor_sha256: str, producer_component_id: str, checker_component_id: str, producer_family: str, checker_family: str, producer_executable: bytes, checker_executable: bytes, producer_arguments: tuple[str, ...], checker_arguments: tuple[str, ...], input_artifacts: tuple[tuple[str, bytes], ...]) -> bytes:
    """Construct one exact closed producer/checker execution binding."""
    if type(producer_executable) is not bytes or type(checker_executable) is not bytes or type(producer_arguments) is not tuple or type(checker_arguments) is not tuple or type(input_artifacts) is not tuple:
        _fail("type", "$", "binding constructor requires exact immutable values")
    artifact_values: list[dict[str, object]] = []
    for index, pair in enumerate(input_artifacts):
        if type(pair) is not tuple or len(pair) != 2 or type(pair[1]) is not bytes:
            _fail("type", f"$.input_artifacts[{index}]", "expected role and exact bytes")
        artifact_values.append({"role": pair[0], "sha256": _sha(pair[1]), "bytes": len(pair[1])})
    mapping: dict[str, object] = {
        "schema": BINDING_SCHEMA, "plan_order": plan_order,
        "strategy_sha256": strategy_sha256, "descriptor_sha256": descriptor_sha256,
        "producer_component_id": producer_component_id, "checker_component_id": checker_component_id,
        "producer_family": producer_family, "checker_family": checker_family,
        "producer_executable_sha256": _sha(producer_executable),
        "checker_executable_sha256": _sha(checker_executable),
        "producer_arguments": list(producer_arguments), "checker_arguments": list(checker_arguments),
        "input_artifacts": artifact_values, "protocol": "canonical_evidence_certificate_v1",
        "binding_sha256": None, "mathematical_authority": False,
    }
    mapping["binding_sha256"] = _self_hash(mapping, "binding_sha256")
    return _canonical(_binding_mapping(_binding_from_mapping(mapping)))


def parse_portfolio_execution_binding(data: bytes) -> PortfolioExecutionBinding:
    return _binding_from_mapping(_parse(data, "$"))


def _request_mapping(value: ProofSearchPortfolioRequest, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "planning_result_sha256": value.planning_result_sha256,
        "parent_budget_sha256": value.parent_budget_sha256,
        "descriptor_sha256s": list(value.descriptor_sha256s),
        "binding_sha256s": list(value.binding_sha256s),
        "artifact_bindings": [_binding_value(item) for item in value.artifact_bindings],
        "preference_policy": value.preference_policy,
        "request_sha256": value.request_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _sha_tuple(value: object, path: str, *, sorted_required: bool = False) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_ITEMS:
        _fail("limit", path, "digest array ceiling exceeded")
    result = tuple(_digest(item, f"{path}[{index}]") for index, item in enumerate(value))
    if len(set(result)) != len(result) or (sorted_required and result != tuple(sorted(result))):
        _fail("identity", path, "digest array order or uniqueness differs")
    return result


def _request_from_mapping(value: object) -> ProofSearchPortfolioRequest:
    expected = {"schema", "planning_result_sha256", "parent_budget_sha256", "descriptor_sha256s", "binding_sha256s", "artifact_bindings", "preference_policy", "request_sha256", "mathematical_authority"}
    item = _keys(value, expected, "$")
    if item["schema"] != REQUEST_SCHEMA or item["preference_policy"] != PREFERENCE_POLICY or item["mathematical_authority"] is not False:
        _fail("schema", "$", "portfolio request constants differ")
    result = _make(
        ProofSearchPortfolioRequest, schema=REQUEST_SCHEMA,
        planning_result_sha256=_digest(item["planning_result_sha256"], "$.planning_result_sha256"),
        parent_budget_sha256=_digest(item["parent_budget_sha256"], "$.parent_budget_sha256"),
        descriptor_sha256s=_sha_tuple(item["descriptor_sha256s"], "$.descriptor_sha256s", sorted_required=True),
        binding_sha256s=_sha_tuple(item["binding_sha256s"], "$.binding_sha256s"),
        artifact_bindings=_artifact_bindings(item["artifact_bindings"], "$.artifact_bindings"),
        preference_policy=PREFERENCE_POLICY,
        request_sha256=_digest(item["request_sha256"], "$.request_sha256"), mathematical_authority=False,
    )
    if result.request_sha256 != _self_hash(_request_mapping(result), "request_sha256"):
        _fail("identity", "$.request_sha256", "portfolio request identity mismatch")
    return result


def make_proof_search_portfolio_request(*, planning_result: bytes, parent_budget: bytes, descriptors: tuple[bytes, ...], bindings: tuple[bytes, ...], artifacts: tuple[tuple[str, bytes], ...]) -> bytes:
    """Construct a request that closes every semantic portfolio input."""
    if type(planning_result) is not bytes or type(parent_budget) is not bytes or type(descriptors) is not tuple or type(bindings) is not tuple or type(artifacts) is not tuple or any(type(item) is not bytes for item in (*descriptors, *bindings)):
        _fail("type", "$", "request constructor requires exact immutable values")
    artifact_values: list[dict[str, object]] = []
    for index, pair in enumerate(artifacts):
        if type(pair) is not tuple or len(pair) != 2 or type(pair[1]) is not bytes:
            _fail("type", f"$.artifacts[{index}]", "expected role and exact bytes")
        artifact_values.append({"role": pair[0], "sha256": _sha(pair[1]), "bytes": len(pair[1])})
    mapping: dict[str, object] = {
        "schema": REQUEST_SCHEMA, "planning_result_sha256": _sha(planning_result),
        "parent_budget_sha256": _sha(parent_budget),
        "descriptor_sha256s": sorted(_sha(item) for item in descriptors),
        "binding_sha256s": [_sha(item) for item in bindings],
        "artifact_bindings": artifact_values, "preference_policy": PREFERENCE_POLICY,
        "request_sha256": None, "mathematical_authority": False,
    }
    mapping["request_sha256"] = _self_hash(mapping, "request_sha256")
    return _canonical(_request_mapping(_request_from_mapping(mapping)))


def parse_proof_search_portfolio_request(data: bytes) -> ProofSearchPortfolioRequest:
    return _request_from_mapping(_parse(data, "$"))


def _array(value: object, path: str, *, maximum: int = MAX_ITEMS) -> list[object]:
    if type(value) is not list or len(value) > maximum:
        _fail("limit", path, "invalid bounded array")
    return value


def _sorted_texts(
    value: object,
    path: str,
    *,
    pattern: re.Pattern[str] | None = None,
    choices: tuple[str, ...] | None = None,
    maximum: int = MAX_ITEMS,
) -> tuple[str, ...]:
    raw = _array(value, path, maximum=maximum)
    result = tuple(
        _text(item, f"{path}[{index}]", pattern=pattern, maximum=255)
        for index, item in enumerate(raw)
    )
    if result != tuple(sorted(set(result))):
        _fail("canonical", path, "array must be sorted and unique")
    if choices is not None and any(item not in choices for item in result):
        _fail("schema", path, "array contains an unknown member")
    return result


def _extensions(value: object, path: str) -> dict[str, object]:
    if type(value) is not dict or len(value) > MAX_ITEMS:
        _fail("schema", path, "invalid extension object")
    for key in value:
        _text(key, f"{path}.{key}", pattern=_NAMESPACED, maximum=255)
    _walk(value)
    return value


def _subject(value: object, path: str) -> dict[str, object]:
    item = _keys(
        value,
        {
            "kind", "subject_id", "statement_sha256", "problem_ir_sha256",
            "theory_context_sha256", "reading_id", "assumption_sha256s",
            "obligation_sha256s",
        },
        path,
    )
    _choice(item["kind"], ("goal", "obligation", "claim", "result"), f"{path}.kind")
    _text(item["subject_id"], f"{path}.subject_id", pattern=_ID, maximum=64)
    _digest(item["statement_sha256"], f"{path}.statement_sha256")
    _digest(item["problem_ir_sha256"], f"{path}.problem_ir_sha256")
    _digest(item["theory_context_sha256"], f"{path}.theory_context_sha256")
    _text(item["reading_id"], f"{path}.reading_id", pattern=_ID, maximum=64)
    _sorted_texts(item["assumption_sha256s"], f"{path}.assumption_sha256s", pattern=_SHA)
    _sorted_texts(item["obligation_sha256s"], f"{path}.obligation_sha256s", pattern=_SHA)
    return item


def _versioned_format(value: object, path: str, *, evidence: bool) -> dict[str, object]:
    expected = {
        "format_id", "version", "major", "minor", "reader_minimum_minor",
        "schema_sha256", "canonicalization", "features",
    }
    if evidence:
        expected.add("kind")
    item = _keys(value, expected, path)
    if evidence:
        _choice(
            item["kind"],
            ("proof", "witness", "counterexample", "derivation", "model", "trace", "bound"),
            f"{path}.kind",
        )
    _text(item["format_id"], f"{path}.format_id", pattern=_NAMESPACED, maximum=255)
    version = _text(item["version"], f"{path}.version", pattern=_SEMVER, maximum=64)
    major = _quantity(item["major"], f"{path}.major")
    minor = _quantity(item["minor"], f"{path}.minor")
    reader = _quantity(item["reader_minimum_minor"], f"{path}.reader_minimum_minor")
    match = _SEMVER.fullmatch(version)
    if match is None or major != 1 or int(match.group(1)) != minor or reader > minor:
        _fail("contract", path, "format version fields disagree")
    _digest(item["schema_sha256"], f"{path}.schema_sha256")
    _text(item["canonicalization"], f"{path}.canonicalization", pattern=_NAMESPACED, maximum=255)
    _sorted_texts(item["features"], f"{path}.features", pattern=_NAMESPACED)
    return item


def _component(value: object, path: str, *, checker: bool) -> dict[str, object]:
    item = _keys(
        value,
        {
            "component_id", "role", "name", "version", "contract_id",
            "contract_sha256", "implementation_sha256", "configuration_sha256",
            "environment_contract_sha256",
        },
        path,
    )
    _text(item["component_id"], f"{path}.component_id", pattern=_ID, maximum=64)
    roles = ("checker", "external") if checker else ("producer", "solver", "heuristic", "external")
    _choice(item["role"], roles, f"{path}.role")
    _text(item["name"], f"{path}.name", pattern=_NAMESPACED, maximum=255)
    _text(item["version"], f"{path}.version", maximum=128)
    _text(item["contract_id"], f"{path}.contract_id", pattern=_CONTRACT, maximum=128)
    for name in ("contract_sha256", "implementation_sha256", "configuration_sha256", "environment_contract_sha256"):
        _digest(item[name], f"{path}.{name}")
    return item


def _budget_reference(value: object, path: str) -> dict[str, object]:
    item = _keys(value, {"initial_sha256", "final_sha256", "outcome"}, path)
    _digest(item["initial_sha256"], f"{path}.initial_sha256")
    _digest(item["final_sha256"], f"{path}.final_sha256")
    _choice(item["outcome"], ("completed", "cancelled", "exhausted", "truncated"), f"{path}.outcome")
    return item


def _diagnostics(
    value: object,
    path: str,
    *,
    relation_name: str,
) -> tuple[dict[str, object], ...]:
    result: list[dict[str, object]] = []
    for index, raw in enumerate(_array(value, path)):
        item_path = f"{path}[{index}]"
        item = _keys(
            raw,
            {"diagnostic_id", "severity", "code", "message", relation_name, "details"},
            item_path,
        )
        _text(item["diagnostic_id"], f"{item_path}.diagnostic_id", pattern=_ID, maximum=64)
        _choice(item["severity"], ("info", "warning", "error"), f"{item_path}.severity")
        _text(item["code"], f"{item_path}.code", pattern=_NAMESPACED, maximum=255)
        _text(item["message"], f"{item_path}.message", maximum=4096)
        _sorted_texts(item[relation_name], f"{item_path}.{relation_name}", pattern=_ID)
        _walk(item["details"])
        result.append(item)
    identifiers = tuple(item["diagnostic_id"] for item in result)
    if identifiers != tuple(sorted(set(identifiers))):
        _fail("identity", path, "diagnostic identifiers must be sorted and unique")
    return tuple(result)


def _generation_basis(value: dict[str, object]) -> str:
    generation = dict(value["generation"])  # type: ignore[arg-type]
    del generation["basis_sha256"]
    return _sha(
        _canonical(
            {
                "evidence_id": value["evidence_id"],
                "subject": value["subject"],
                "format": value["format"],
                "producer": value["producer"],
                "dependencies": value["dependencies"],
                "generation": generation,
            }
        )
    )


def _validate_evidence(
    data: bytes,
    strategy: PlanningStrategy,
    producer: dict[str, object],
    environment_contract_sha256: str,
) -> tuple[dict[str, object], str]:
    value = _parse(data, "evidence", maximum=MAX_CHECKER_PAYLOAD_BYTES)
    expected = {
        "schema", "evidence_id", "subject", "format", "producer", "payloads",
        "primary_payload_id", "dependencies", "generation", "budget", "outcome",
        "diagnostics", "extensions",
    }
    _keys(value, expected, "evidence")
    if value["schema"] != "mathhead.evidence.v1":
        _fail("evidence", "evidence.schema", "Evidence schema differs")
    _text(value["evidence_id"], "evidence.evidence_id", pattern=_ID, maximum=64)
    subject = _subject(value["subject"], "evidence.subject")
    if subject["kind"] != "obligation" or subject["statement_sha256"] != strategy.obligation_semantic_sha256:
        _fail("evidence", "evidence.subject", "Evidence does not bind the planned obligation")
    format_value = _versioned_format(value["format"], "evidence.format", evidence=True)
    expected_format = _thaw_planner_value(strategy.evidence_expectation.evidence_format)
    if type(expected_format) is not dict:
        _fail("evidence", "evidence.format", "plan has no accepted Evidence format")
    if (
        format_value["format_id"] != expected_format.get("format_id")
        or format_value["major"] != expected_format.get("major")
        or format_value["minor"] != expected_format.get("minor")
        or not set(expected_format.get("required_features", ())) <= set(format_value["features"])  # type: ignore[arg-type]
    ):
        _fail("evidence", "evidence.format", "Evidence format differs from the plan")
    producer_value = _component(value["producer"], "evidence.producer", checker=False)
    component_expected = {
        "component_id": producer["component_id"], "role": producer["role"],
        "name": producer["name"], "version": producer["version"],
        "contract_id": producer["contract_id"], "contract_sha256": producer["contract_sha256"],
        "implementation_sha256": producer["implementation_sha256"],
        "configuration_sha256": producer["configuration_sha256"],
        "environment_contract_sha256": environment_contract_sha256,
    }
    if producer_value != component_expected or producer_value["component_id"] != strategy.producer_component_id:
        _fail("evidence", "evidence.producer", "producer identity differs from the descriptor")

    payloads: list[dict[str, object]] = []
    for index, raw in enumerate(_array(value["payloads"], "evidence.payloads")):
        path = f"evidence.payloads[{index}]"
        item = _keys(raw, {"payload_id", "role", "media_type", "sha256", "byte_count", "encoding", "compression", "extensions"}, path)
        _text(item["payload_id"], f"{path}.payload_id", pattern=_ID, maximum=64)
        _choice(item["role"], ("primary", "auxiliary"), f"{path}.role")
        media = _text(item["media_type"], f"{path}.media_type", maximum=255)
        if "/" not in media or media.lower() != media:
            _fail("schema", f"{path}.media_type", "invalid media type")
        _digest(item["sha256"], f"{path}.sha256")
        _quantity(item["byte_count"], f"{path}.byte_count")
        _choice(item["encoding"], ("binary", "utf-8"), f"{path}.encoding")
        _choice(item["compression"], ("none", "gzip", "zstd"), f"{path}.compression")
        _extensions(item["extensions"], f"{path}.extensions")
        payloads.append(item)
    payload_ids = tuple(item["payload_id"] for item in payloads)
    if payload_ids != tuple(sorted(set(payload_ids))) or len({(item["role"], item["sha256"]) for item in payloads}) != len(payloads):
        _fail("evidence", "evidence.payloads", "payload identifiers must be sorted and unique")
    primary = value["primary_payload_id"]
    primary_values = [item for item in payloads if item["role"] == "primary"]
    if primary is None:
        if primary_values:
            _fail("evidence", "evidence.primary_payload_id", "primary payload is not bound")
    else:
        _text(primary, "evidence.primary_payload_id", pattern=_ID, maximum=64)
        if len(primary_values) != 1 or primary_values[0]["payload_id"] != primary or primary_values[0]["byte_count"] == 0:
            _fail("evidence", "evidence.primary_payload_id", "primary payload binding differs")

    dependencies: list[dict[str, object]] = []
    for index, raw in enumerate(_array(value["dependencies"], "evidence.dependencies")):
        path = f"evidence.dependencies[{index}]"
        item = _keys(raw, {"evidence_id", "evidence_sha256", "relation", "depends_on_evidence_ids"}, path)
        _text(item["evidence_id"], f"{path}.evidence_id", pattern=_ID, maximum=64)
        _digest(item["evidence_sha256"], f"{path}.evidence_sha256")
        _choice(item["relation"], ("premise", "derivation", "input", "support"), f"{path}.relation")
        _sorted_texts(item["depends_on_evidence_ids"], f"{path}.depends_on_evidence_ids", pattern=_ID)
        dependencies.append(item)
    dependency_ids = tuple(item["evidence_id"] for item in dependencies)
    if dependency_ids != tuple(sorted(set(dependency_ids))) or value["evidence_id"] in dependency_ids or len({item["evidence_sha256"] for item in dependencies}) != len(dependencies):
        _fail("evidence", "evidence.dependencies", "dependency identities differ")
    known = set(dependency_ids)
    graph = {item["evidence_id"]: tuple(item["depends_on_evidence_ids"]) for item in dependencies}
    if any(not set(edges) <= known or node in edges for node, edges in graph.items()):
        _fail("evidence", "evidence.dependencies", "dependency edge is unresolved")
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting:
            _fail("evidence", "evidence.dependencies", "dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for target in graph[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)
    for node in graph:
        visit(node)

    generation = _keys(value["generation"], {"mode", "seed", "algorithm_id", "configuration_sha256", "input_sha256", "basis_sha256"}, "evidence.generation")
    mode = _choice(generation["mode"], ("deterministic", "seeded"), "evidence.generation.mode")
    seed = generation["seed"]
    if (mode == "deterministic" and seed is not None) or (mode == "seeded" and type(seed) is not int):
        _fail("evidence", "evidence.generation.seed", "generation seed policy differs")
    if seed is not None:
        _quantity(seed, "evidence.generation.seed")
    _text(generation["algorithm_id"], "evidence.generation.algorithm_id", pattern=_NAMESPACED, maximum=255)
    for name in ("configuration_sha256", "input_sha256", "basis_sha256"):
        _digest(generation[name], f"evidence.generation.{name}")
    if generation["configuration_sha256"] != producer_value["configuration_sha256"] or generation["input_sha256"] != _sha(_canonical(subject)) or generation["basis_sha256"] != _generation_basis(value):
        _fail("evidence", "evidence.generation", "generation identity differs")
    budget = _budget_reference(value["budget"], "evidence.budget")
    diagnostics = _diagnostics(value["diagnostics"], "evidence.diagnostics", relation_name="related_payload_ids")
    for diagnostic in diagnostics:
        if not set(diagnostic["related_payload_ids"]) <= set(payload_ids):  # type: ignore[arg-type]
            _fail("evidence", "evidence.diagnostics", "diagnostic references an unknown payload")
    outcome = value["outcome"]
    if type(outcome) is not dict or "status" not in outcome:
        _fail("schema", "evidence.outcome", "invalid Evidence outcome")
    status = _choice(outcome["status"], ("produced", "unsupported", "incomplete", "cancelled", "exhausted", "truncated", "error"), "evidence.outcome.status")
    variant_fields = {
        "produced": {"status", "payload_ids", "diagnostic_ids"},
        "unsupported": {"status", "unsupported_features", "reason", "diagnostic_ids"},
        "incomplete": {"status", "reason", "diagnostic_ids"},
        "cancelled": {"status", "cancellation_id", "reason", "diagnostic_ids"},
        "exhausted": {"status", "dimensions", "reason", "diagnostic_ids"},
        "truncated": {"status", "truncation_ids", "retained_payload_ids", "reason", "diagnostic_ids"},
        "error": {"status", "error_code", "reason", "diagnostic_ids"},
    }
    _keys(outcome, variant_fields[status], "evidence.outcome")
    diagnostic_ids = _sorted_texts(outcome["diagnostic_ids"], "evidence.outcome.diagnostic_ids", pattern=_ID)
    if diagnostic_ids != tuple(item["diagnostic_id"] for item in diagnostics):
        _fail("evidence", "evidence.outcome.diagnostic_ids", "outcome does not bind diagnostics")
    if status == "produced":
        if primary is None or _sorted_texts(outcome["payload_ids"], "evidence.outcome.payload_ids", pattern=_ID) != payload_ids:
            _fail("evidence", "evidence.outcome.payload_ids", "produced outcome omits payloads")
        if any(item["severity"] == "error" for item in diagnostics):
            _fail("evidence", "evidence.diagnostics", "produced Evidence hides an error")
    else:
        if not diagnostics:
            _fail("evidence", "evidence.diagnostics", "non-produced Evidence requires a diagnostic")
        if "reason" in outcome:
            _text(outcome["reason"], "evidence.outcome.reason", maximum=4096)
        if status == "unsupported":
            _sorted_texts(outcome["unsupported_features"], "evidence.outcome.unsupported_features", pattern=_NAMESPACED)
        elif status == "cancelled":
            _text(outcome["cancellation_id"], "evidence.outcome.cancellation_id", pattern=_ID, maximum=64)
        elif status == "exhausted":
            dims = _sorted_texts(outcome["dimensions"], "evidence.outcome.dimensions", choices=RESOURCE_DIMENSIONS, maximum=10)
            if not dims:
                _fail("evidence", "evidence.outcome.dimensions", "exhaustion needs a dimension")
        elif status == "truncated":
            if not _sorted_texts(outcome["truncation_ids"], "evidence.outcome.truncation_ids", pattern=_ID):
                _fail("evidence", "evidence.outcome.truncation_ids", "truncation identity required")
            if not set(_sorted_texts(outcome["retained_payload_ids"], "evidence.outcome.retained_payload_ids", pattern=_ID)) <= set(payload_ids):
                _fail("evidence", "evidence.outcome.retained_payload_ids", "unknown retained payload")
        elif status == "error":
            _text(outcome["error_code"], "evidence.outcome.error_code", pattern=_NAMESPACED, maximum=255)
            if not any(item["severity"] == "error" for item in diagnostics):
                _fail("evidence", "evidence.diagnostics", "error Evidence needs an error diagnostic")
    expected_budget = status if status in {"cancelled", "exhausted", "truncated"} else "completed"
    if budget["outcome"] != expected_budget:
        _fail("evidence", "evidence.budget.outcome", "Evidence hides a resource outcome")
    extensions = _extensions(value["extensions"], "evidence.extensions")
    claim = extensions.get("org.mathhead.portfolio.claim")
    if status == "produced" and claim not in {"proved", "refuted"}:
        _fail("evidence", "evidence.extensions", "produced Evidence lacks a closed portfolio claim")
    owners = {
        value["evidence_id"], producer_value["component_id"], *payload_ids,
        *dependency_ids, *(item["diagnostic_id"] for item in diagnostics),
    }
    expected_owners = 2 + len(payloads) + len(dependencies) + len(diagnostics)
    if len(owners) != expected_owners:
        _fail("evidence", "evidence", "Evidence namespace contains an identity collision")
    if status != "produced":
        return value, status
    return value, str(claim)


def _thaw_planner_value(value: object) -> object:
    if type(value).__name__ == "_FrozenMap" and hasattr(value, "entries"):
        return {key: _thaw_planner_value(item) for key, item in value.entries}  # type: ignore[attr-defined]
    if type(value) is tuple:
        return tuple(_thaw_planner_value(item) for item in value)
    return value


def _replay_basis(value: dict[str, object]) -> str:
    replay = dict(value["replay"])  # type: ignore[arg-type]
    del replay["basis_sha256"]
    return _sha(
        _canonical(
            {
                "certificate_id": value["certificate_id"],
                "subject": value["subject"],
                "format": value["format"],
                "checker": value["checker"],
                "evidence": value["evidence"],
                "replay": replay,
            }
        )
    )


def _validate_certificate(
    data: bytes,
    evidence_data: bytes,
    evidence: dict[str, object],
    strategy: PlanningStrategy,
    checker: dict[str, object],
    environment_contract_sha256: str,
    certificate_formats: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], str, str]:
    value = _parse(data, "certificate", maximum=MAX_CHECKER_PAYLOAD_BYTES)
    _keys(
        value,
        {
            "schema", "certificate_id", "subject", "format", "checker", "evidence",
            "replay", "verification_artifacts", "trust_dependencies", "verdict",
            "budget", "diagnostics", "extensions",
        },
        "certificate",
    )
    if value["schema"] != "mathhead.certificate.v1":
        _fail("certificate", "certificate.schema", "Certificate schema differs")
    _text(value["certificate_id"], "certificate.certificate_id", pattern=_ID, maximum=64)
    subject = _subject(value["subject"], "certificate.subject")
    if subject != evidence["subject"]:
        _fail("certificate", "certificate.subject", "Certificate subject differs from Evidence")
    format_value = _versioned_format(value["format"], "certificate.format", evidence=False)
    compatible_format = any(
        format_value["format_id"] == candidate["format_id"]
        and format_value["major"] == candidate["major"]
        and candidate["minor_minimum"] <= format_value["minor"] <= candidate["minor_maximum"]
        and set(candidate["required_features"]) <= set(format_value["features"])  # type: ignore[arg-type]
        for candidate in certificate_formats
    )
    if not compatible_format:
        _fail("certificate", "certificate.format", "Certificate format is not descriptor-compatible")
    checker_value = _component(value["checker"], "certificate.checker", checker=True)
    checker_expected = {
        "component_id": checker["component_id"], "role": checker["role"],
        "name": checker["name"], "version": checker["version"],
        "contract_id": checker["contract_id"], "contract_sha256": checker["contract_sha256"],
        "implementation_sha256": checker["implementation_sha256"],
        "configuration_sha256": checker["configuration_sha256"],
        "environment_contract_sha256": environment_contract_sha256,
    }
    if checker_value != checker_expected or checker_value["component_id"] != strategy.checker_component_id:
        _fail("certificate", "certificate.checker", "checker identity differs from the descriptor")
    producer_value = evidence["producer"]
    if (
        checker_value["component_id"] == producer_value["component_id"]  # type: ignore[index]
        or (
            checker_value["contract_sha256"] == producer_value["contract_sha256"]  # type: ignore[index]
            and checker_value["implementation_sha256"] == producer_value["implementation_sha256"]  # type: ignore[index]
        )
    ):
        _fail("certificate", "certificate.checker", "checker is not independent")

    reference = _keys(
        value["evidence"],
        {
            "schema", "evidence_id", "evidence_sha256", "primary_payload_sha256",
            "format_id", "format_version", "format_features", "dependency_sha256s", "producer",
        },
        "certificate.evidence",
    )
    producer_ref = _keys(
        reference["producer"],
        {"component_id", "role", "contract_sha256", "implementation_sha256", "configuration_sha256"},
        "certificate.evidence.producer",
    )
    _text(producer_ref["component_id"], "certificate.evidence.producer.component_id", pattern=_ID, maximum=64)
    _choice(producer_ref["role"], ("producer", "solver", "heuristic", "external"), "certificate.evidence.producer.role")
    for name in ("contract_sha256", "implementation_sha256", "configuration_sha256"):
        _digest(producer_ref[name], f"certificate.evidence.producer.{name}")
    payloads = evidence["payloads"]
    primary = next(item for item in payloads if item["payload_id"] == evidence["primary_payload_id"])  # type: ignore[union-attr]
    expected_reference = {
        "schema": "mathhead.evidence.v1",
        "evidence_id": evidence["evidence_id"],
        "evidence_sha256": _sha(evidence_data),
        "primary_payload_sha256": primary["sha256"],
        "format_id": evidence["format"]["format_id"],  # type: ignore[index]
        "format_version": evidence["format"]["version"],  # type: ignore[index]
        "format_features": evidence["format"]["features"],  # type: ignore[index]
        "dependency_sha256s": sorted(item["evidence_sha256"] for item in evidence["dependencies"]),  # type: ignore[union-attr]
        "producer": {
            name: producer_value[name]  # type: ignore[index]
            for name in ("component_id", "role", "contract_sha256", "implementation_sha256", "configuration_sha256")
        },
    }
    if reference != expected_reference:
        _fail("certificate", "certificate.evidence", "Certificate does not bind exact Evidence bytes")

    replay = _keys(
        value["replay"],
        {
            "attempt_id", "mode", "seed", "algorithm_id", "configuration_sha256",
            "input_evidence_sha256", "expected_payload_sha256", "observed_payload_sha256",
            "basis_sha256",
        },
        "certificate.replay",
    )
    _text(replay["attempt_id"], "certificate.replay.attempt_id", pattern=_ID, maximum=64)
    mode = _choice(replay["mode"], ("deterministic", "seeded"), "certificate.replay.mode")
    if (mode == "deterministic" and replay["seed"] is not None) or (mode == "seeded" and type(replay["seed"]) is not int):
        _fail("certificate", "certificate.replay.seed", "replay seed policy differs")
    if replay["seed"] is not None:
        _quantity(replay["seed"], "certificate.replay.seed")
    _text(replay["algorithm_id"], "certificate.replay.algorithm_id", pattern=_NAMESPACED, maximum=255)
    for name in ("configuration_sha256", "input_evidence_sha256", "expected_payload_sha256", "basis_sha256"):
        _digest(replay[name], f"certificate.replay.{name}")
    if replay["observed_payload_sha256"] is not None:
        _digest(replay["observed_payload_sha256"], "certificate.replay.observed_payload_sha256")
    if (
        replay["configuration_sha256"] != checker_value["configuration_sha256"]
        or replay["input_evidence_sha256"] != _sha(evidence_data)
        or replay["expected_payload_sha256"] != primary["sha256"]
        or replay["basis_sha256"] != _replay_basis(value)
    ):
        _fail("certificate", "certificate.replay", "replay identity differs")

    artifacts: list[dict[str, object]] = []
    for index, raw in enumerate(_array(value["verification_artifacts"], "certificate.verification_artifacts")):
        path = f"certificate.verification_artifacts[{index}]"
        item = _keys(raw, {"artifact_id", "kind", "sha256", "byte_count", "producer_component_id", "extensions"}, path)
        _text(item["artifact_id"], f"{path}.artifact_id", pattern=_ID, maximum=64)
        _choice(item["kind"], ("checker_result", "replay_log", "certificate_payload", "diagnostic"), f"{path}.kind")
        _digest(item["sha256"], f"{path}.sha256")
        _quantity(item["byte_count"], f"{path}.byte_count")
        _text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64)
        _extensions(item["extensions"], f"{path}.extensions")
        if item["producer_component_id"] != checker_value["component_id"]:
            _fail("certificate", path, "verification artifact is not checker-produced")
        artifacts.append(item)
    artifact_ids = tuple(item["artifact_id"] for item in artifacts)
    if artifact_ids != tuple(sorted(set(artifact_ids))) or len({(item["kind"], item["sha256"]) for item in artifacts}) != len(artifacts):
        _fail("certificate", "certificate.verification_artifacts", "artifact identity/order differs")
    by_artifact = {item["artifact_id"]: item for item in artifacts}

    trust: list[dict[str, object]] = []
    trust_kinds = (
        "checker_configuration", "checker_contract", "checker_implementation", "environment_contract",
        "evidence", "problem_ir", "theory_context",
    )
    for index, raw in enumerate(_array(value["trust_dependencies"], "certificate.trust_dependencies")):
        path = f"certificate.trust_dependencies[{index}]"
        item = _keys(raw, {"kind", "identifier", "sha256"}, path)
        _choice(item["kind"], trust_kinds, f"{path}.kind")
        _text(item["identifier"], f"{path}.identifier", pattern=_CONTRACT, maximum=128)
        _digest(item["sha256"], f"{path}.sha256")
        trust.append(item)
    order = tuple((item["kind"], item["identifier"]) for item in trust)
    if order != tuple(sorted(set(order))):
        _fail("certificate", "certificate.trust_dependencies", "trust closure is not sorted/unique")
    budget = _budget_reference(value["budget"], "certificate.budget")
    diagnostics = _diagnostics(value["diagnostics"], "certificate.diagnostics", relation_name="related_artifact_ids")
    for diagnostic in diagnostics:
        if not set(diagnostic["related_artifact_ids"]) <= set(artifact_ids):  # type: ignore[arg-type]
            _fail("certificate", "certificate.diagnostics", "diagnostic references an unknown artifact")

    verdict = value["verdict"]
    if type(verdict) is not dict or "status" not in verdict:
        _fail("certificate", "certificate.verdict", "invalid Certificate verdict")
    status = _choice(
        verdict["status"],
        ("verified", "invalid", "unsupported", "inconclusive", "cancelled", "exhausted", "truncated", "verifier_failed", "disagreement"),
        "certificate.verdict.status",
    )
    fields_by_status = {
        "verified": {"status", "authority", "checker_result_artifact_id", "supporting_artifact_ids", "diagnostic_ids"},
        "invalid": {"status", "reason_code", "checker_result_artifact_id", "reason", "diagnostic_ids"},
        "unsupported": {"status", "unsupported_features", "reason", "diagnostic_ids"},
        "inconclusive": {"status", "reason", "diagnostic_ids"},
        "cancelled": {"status", "cancellation_id", "reason", "diagnostic_ids"},
        "exhausted": {"status", "dimensions", "reason", "diagnostic_ids"},
        "truncated": {"status", "truncation_ids", "reason", "diagnostic_ids"},
        "verifier_failed": {"status", "error_code", "reason", "diagnostic_ids"},
        "disagreement": {"status", "conflicting_artifact_ids", "reason", "diagnostic_ids"},
    }
    _keys(verdict, fields_by_status[status], "certificate.verdict")
    diagnostic_ids = _sorted_texts(verdict["diagnostic_ids"], "certificate.verdict.diagnostic_ids", pattern=_ID)
    if diagnostic_ids != tuple(item["diagnostic_id"] for item in diagnostics):
        _fail("certificate", "certificate.verdict.diagnostic_ids", "verdict does not bind diagnostics")
    authority = "none"
    if status == "verified":
        authority = _choice(verdict["authority"], ("checker_attested", "external_verified"), "certificate.verdict.authority")
        expected_authority = "checker_attested" if checker_value["role"] == "checker" else "external_verified"
        result_id = _text(verdict["checker_result_artifact_id"], "certificate.verdict.checker_result_artifact_id", pattern=_ID, maximum=64)
        support = _sorted_texts(verdict["supporting_artifact_ids"], "certificate.verdict.supporting_artifact_ids", pattern=_ID)
        if authority != expected_authority or result_id not in by_artifact or by_artifact[result_id]["kind"] != "checker_result" or result_id not in support or not set(support) <= set(artifact_ids) or not any(by_artifact[item]["kind"] == "replay_log" for item in support) or replay["observed_payload_sha256"] != replay["expected_payload_sha256"] or diagnostics:
            _fail("certificate", "certificate.verdict", "verified Certificate lacks independent replay support")
        by_kind = {item["kind"]: item for item in trust}
        expected_trust = {
            "checker_contract": checker_value["contract_sha256"],
            "checker_implementation": checker_value["implementation_sha256"],
            "checker_configuration": checker_value["configuration_sha256"],
            "environment_contract": checker_value["environment_contract_sha256"],
            "problem_ir": subject["problem_ir_sha256"],
            "theory_context": subject["theory_context_sha256"],
            "evidence": _sha(evidence_data),
        }
        if set(by_kind) != set(expected_trust) or len(trust) != len(expected_trust) or any(by_kind[kind]["sha256"] != digest for kind, digest in expected_trust.items()):
            _fail("certificate", "certificate.trust_dependencies", "verified Certificate lacks exact trust closure")
    else:
        if not diagnostics:
            _fail("certificate", "certificate.diagnostics", "non-verified Certificate requires a diagnostic")
        if status in {"verifier_failed", "disagreement"} and not any(item["severity"] == "error" for item in diagnostics):
            _fail("certificate", "certificate.diagnostics", "checker failure requires an error diagnostic")
        if "reason" in verdict:
            _text(verdict["reason"], "certificate.verdict.reason", maximum=4096)
        if status == "invalid":
            _choice(verdict["reason_code"], ("evidence_mismatch", "replay_mismatch", "semantic_failure", "dependency_failure"), "certificate.verdict.reason_code")
            result_id = _text(verdict["checker_result_artifact_id"], "certificate.verdict.checker_result_artifact_id", pattern=_ID, maximum=64)
            if result_id not in by_artifact or by_artifact[result_id]["kind"] != "checker_result":
                _fail("certificate", "certificate.verdict", "invalid verdict lacks checker result")
        elif status == "unsupported":
            _sorted_texts(verdict["unsupported_features"], "certificate.verdict.unsupported_features", pattern=_NAMESPACED)
        elif status == "cancelled":
            _text(verdict["cancellation_id"], "certificate.verdict.cancellation_id", pattern=_ID, maximum=64)
        elif status == "exhausted":
            if not _sorted_texts(verdict["dimensions"], "certificate.verdict.dimensions", choices=RESOURCE_DIMENSIONS, maximum=10):
                _fail("certificate", "certificate.verdict.dimensions", "exhaustion needs a dimension")
        elif status == "truncated":
            if not _sorted_texts(verdict["truncation_ids"], "certificate.verdict.truncation_ids", pattern=_ID):
                _fail("certificate", "certificate.verdict.truncation_ids", "truncation identity required")
        elif status == "verifier_failed":
            _text(verdict["error_code"], "certificate.verdict.error_code", pattern=_NAMESPACED, maximum=255)
        elif status == "disagreement":
            conflicts = _sorted_texts(verdict["conflicting_artifact_ids"], "certificate.verdict.conflicting_artifact_ids", pattern=_ID)
            if len(conflicts) < 2 or not set(conflicts) <= set(artifact_ids):
                _fail("certificate", "certificate.verdict.conflicting_artifact_ids", "unresolved checker disagreement")
    expected_budget = status if status in {"cancelled", "exhausted", "truncated"} else "completed"
    if budget["outcome"] != expected_budget:
        _fail("certificate", "certificate.budget.outcome", "Certificate hides a resource outcome")
    _extensions(value["extensions"], "certificate.extensions")
    owners = {
        value["certificate_id"], checker_value["component_id"], replay["attempt_id"],
        *artifact_ids, *(item["diagnostic_id"] for item in diagnostics),
    }
    if len(owners) != 3 + len(artifacts) + len(diagnostics):
        _fail("certificate", "certificate", "Certificate namespace collides")
    return value, status, authority


def _decision_mapping(value: PortfolioCheckerDecision, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "strategy_sha256": value.strategy_sha256,
        "producer_component_id": value.producer_component_id,
        "checker_component_id": value.checker_component_id,
        "subject_sha256": value.subject_sha256,
        "claim": value.claim,
        "evidence_sha256": value.evidence_sha256,
        "evidence_bytes": value.evidence_bytes,
        "certificate_sha256": value.certificate_sha256,
        "certificate_bytes": value.certificate_bytes,
        "certificate_verdict": value.certificate_verdict,
        "certificate_authority": value.certificate_authority,
        "agreement": value.agreement,
        "reason_code": value.reason_code,
        "decision_sha256": value.decision_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _decision_from_mapping(value: object, certificate: bytes | None = None) -> PortfolioCheckerDecision:
    item = _keys(
        value,
        {
            "schema", "strategy_sha256", "producer_component_id", "checker_component_id",
            "subject_sha256", "claim", "evidence_sha256", "evidence_bytes",
            "certificate_sha256", "certificate_bytes", "certificate_verdict",
            "certificate_authority", "agreement", "reason_code", "decision_sha256",
            "mathematical_authority",
        },
        "$",
    )
    if item["schema"] != DECISION_SCHEMA or item["mathematical_authority"] is not False:
        _fail("schema", "$", "checker decision constants differ")
    result = _make(
        PortfolioCheckerDecision,
        schema=DECISION_SCHEMA,
        strategy_sha256=_digest(item["strategy_sha256"], "$.strategy_sha256"),
        producer_component_id=_text(item["producer_component_id"], "$.producer_component_id", pattern=_ID, maximum=64),
        checker_component_id=_text(item["checker_component_id"], "$.checker_component_id", pattern=_ID, maximum=64),
        subject_sha256=_digest(item["subject_sha256"], "$.subject_sha256"),
        claim=_choice(item["claim"], ("proved", "refuted", "none"), "$.claim"),
        evidence_sha256=_nullable_digest(item["evidence_sha256"], "$.evidence_sha256"),
        evidence_bytes=_quantity(item["evidence_bytes"], "$.evidence_bytes"),
        certificate_sha256=_nullable_digest(item["certificate_sha256"], "$.certificate_sha256"),
        certificate_bytes=_quantity(item["certificate_bytes"], "$.certificate_bytes"),
        certificate_verdict=_choice(item["certificate_verdict"], ("verified", "invalid", "unsupported", "inconclusive", "cancelled", "exhausted", "truncated", "verifier_failed"), "$.certificate_verdict"),
        certificate_authority=_choice(item["certificate_authority"], ("checker_attested", "external_verified", "none"), "$.certificate_authority"),
        agreement=_boolean(item["agreement"], "$.agreement"),
        reason_code=_choice(item["reason_code"], ("CHECKER_AGREED", "CHECKER_REJECTED", "CHECKER_INCONCLUSIVE", "CHECKER_DISAGREED", "CERTIFICATE_INVALID"), "$.reason_code"),
        decision_sha256=_digest(item["decision_sha256"], "$.decision_sha256"),
        mathematical_authority=False,
        _certificate=certificate,
    )
    if result.producer_component_id == result.checker_component_id or result.decision_sha256 != _self_hash(_decision_mapping(result), "decision_sha256"):
        _fail("identity", "$", "checker decision identity or independence differs")
    if (result.evidence_sha256 is None) != (result.evidence_bytes == 0) or (result.certificate_sha256 is None) != (result.certificate_bytes == 0):
        _fail("checker", "$", "checker decision byte bindings differ")
    if certificate is not None and (type(certificate) is not bytes or _sha(certificate) != result.certificate_sha256 or len(certificate) != result.certificate_bytes):
        _fail("checker", "$.certificate_sha256", "retained Certificate bytes differ")
    agreed = result.certificate_verdict == "verified" and result.certificate_authority != "none" and result.claim in {"proved", "refuted"} and result.agreement
    if agreed != (result.reason_code == "CHECKER_AGREED"):
        _fail("checker", "$", "checker agreement fields differ")
    if result.certificate_verdict != "verified" and (result.certificate_authority != "none" or result.agreement):
        _fail("checker", "$", "non-verified Certificate cannot carry authority or agreement")
    if result.reason_code == "CHECKER_DISAGREED" and (result.certificate_verdict not in {"verified", "invalid"} or result.agreement):
        _fail("checker", "$", "checker disagreement fields differ")
    return result


def parse_portfolio_checker_decision(data: bytes, certificate: bytes | None = None) -> PortfolioCheckerDecision:
    """Strictly parse one closed checker decision and optional bound Certificate bytes."""
    if certificate is not None and type(certificate) is not bytes:
        _fail("type", "certificate", "expected exact Certificate bytes")
    return _decision_from_mapping(_parse(data, "$", maximum=MAX_CHECKER_PAYLOAD_BYTES), certificate)


def _attempt_mapping(value: PortfolioAttempt, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "attempt_order": value.attempt_order,
        "strategy_sha256": value.strategy_sha256,
        "producer_worker_result_sha256": value.producer_worker_result_sha256,
        "producer_status": value.producer_status,
        "producer_reason_code": value.producer_reason_code,
        "evidence_sha256": value.evidence_sha256,
        "evidence_bytes": value.evidence_bytes,
        "checker_worker_result_sha256": value.checker_worker_result_sha256,
        "checker_status": value.checker_status,
        "checker_reason_code": value.checker_reason_code,
        "checker_decision_sha256": value.checker_decision_sha256,
        "outcome": value.outcome,
        "transition_sha256": value.transition_sha256,
        "parent_budget_before_sha256": value.parent_budget_before_sha256,
        "parent_budget_after_sha256": value.parent_budget_after_sha256,
        "attempt_sha256": value.attempt_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _attempt_from_mapping(value: object, path: str) -> PortfolioAttempt:
    item = _keys(
        value,
        {
            "schema", "attempt_order", "strategy_sha256", "producer_worker_result_sha256",
            "producer_status", "producer_reason_code", "evidence_sha256", "evidence_bytes",
            "checker_worker_result_sha256", "checker_status", "checker_reason_code",
            "checker_decision_sha256", "outcome", "transition_sha256",
            "parent_budget_before_sha256", "parent_budget_after_sha256", "attempt_sha256",
            "mathematical_authority",
        },
        path,
    )
    if item["schema"] != ATTEMPT_SCHEMA or item["mathematical_authority"] is not False:
        _fail("schema", path, "attempt constants differ")
    result = _make(
        PortfolioAttempt,
        schema=ATTEMPT_SCHEMA,
        attempt_order=_quantity(item["attempt_order"], f"{path}.attempt_order"),
        strategy_sha256=_digest(item["strategy_sha256"], f"{path}.strategy_sha256"),
        producer_worker_result_sha256=_nullable_digest(item["producer_worker_result_sha256"], f"{path}.producer_worker_result_sha256"),
        producer_status=_choice(item["producer_status"], _WORKER_STATUSES, f"{path}.producer_status"),
        producer_reason_code=_text(item["producer_reason_code"], f"{path}.producer_reason_code", pattern=_REASON, maximum=64),
        evidence_sha256=_nullable_digest(item["evidence_sha256"], f"{path}.evidence_sha256"),
        evidence_bytes=_quantity(item["evidence_bytes"], f"{path}.evidence_bytes"),
        checker_worker_result_sha256=_nullable_digest(item["checker_worker_result_sha256"], f"{path}.checker_worker_result_sha256"),
        checker_status=_choice(item["checker_status"], _WORKER_STATUSES, f"{path}.checker_status"),
        checker_reason_code=_text(item["checker_reason_code"], f"{path}.checker_reason_code", pattern=_REASON, maximum=64),
        checker_decision_sha256=_nullable_digest(item["checker_decision_sha256"], f"{path}.checker_decision_sha256"),
        outcome=_choice(item["outcome"], _OUTCOMES, f"{path}.outcome"),
        transition_sha256=_digest(item["transition_sha256"], f"{path}.transition_sha256"),
        parent_budget_before_sha256=_digest(item["parent_budget_before_sha256"], f"{path}.parent_budget_before_sha256"),
        parent_budget_after_sha256=_digest(item["parent_budget_after_sha256"], f"{path}.parent_budget_after_sha256"),
        attempt_sha256=_digest(item["attempt_sha256"], f"{path}.attempt_sha256"),
        mathematical_authority=False,
    )
    if result.attempt_sha256 != _self_hash(_attempt_mapping(result), "attempt_sha256"):
        _fail("identity", f"{path}.attempt_sha256", "attempt identity mismatch")
    if (result.producer_worker_result_sha256 is None) != (result.producer_status == "not_started"):
        _fail("result", path, "producer worker status and identity differ")
    if (result.evidence_sha256 is None) != (result.evidence_bytes == 0):
        _fail("result", path, "Evidence byte binding differs")
    if (result.checker_worker_result_sha256 is None) != (result.checker_status == "not_started"):
        _fail("result", path, "checker worker status and identity differ")
    if result.checker_status == "not_started" and (result.checker_decision_sha256 is not None or result.checker_reason_code != "NOT_STARTED"):
        _fail("result", path, "unstarted checker contains a decision")
    if result.outcome == "success" and (result.evidence_sha256 is None or result.checker_decision_sha256 is None or result.checker_status != "completed"):
        _fail("result", path, "successful attempt lacks checked Evidence")
    return result


def _make_attempt(
    *,
    attempt_order: int,
    strategy_sha256: str,
    producer_result_sha256: str | None,
    producer_status: str,
    producer_reason_code: str,
    evidence: bytes | None,
    checker_result_sha256: str | None,
    checker_status: str,
    checker_reason_code: str,
    checker_decision_sha256: str | None,
    outcome: str,
    transition_sha256: str,
    parent_before: bytes,
    parent_after: bytes,
) -> PortfolioAttempt:
    mapping: dict[str, object] = {
        "schema": ATTEMPT_SCHEMA,
        "attempt_order": attempt_order,
        "strategy_sha256": strategy_sha256,
        "producer_worker_result_sha256": producer_result_sha256,
        "producer_status": producer_status,
        "producer_reason_code": producer_reason_code,
        "evidence_sha256": None if evidence is None else _sha(evidence),
        "evidence_bytes": 0 if evidence is None else len(evidence),
        "checker_worker_result_sha256": checker_result_sha256,
        "checker_status": checker_status,
        "checker_reason_code": checker_reason_code,
        "checker_decision_sha256": checker_decision_sha256,
        "outcome": outcome,
        "transition_sha256": transition_sha256,
        "parent_budget_before_sha256": _sha(parent_before),
        "parent_budget_after_sha256": _sha(parent_after),
        "attempt_sha256": None,
        "mathematical_authority": False,
    }
    mapping["attempt_sha256"] = _self_hash(mapping, "attempt_sha256")
    return _attempt_from_mapping(mapping, "attempt")


def _inconclusive_mapping(value: PortfolioInconclusive, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "attempt_order": value.attempt_order,
        "strategy_sha256": value.strategy_sha256,
        "outcome": value.outcome,
        "reason_code": value.reason_code,
        "producer_worker_result_sha256": value.producer_worker_result_sha256,
        "checker_worker_result_sha256": value.checker_worker_result_sha256,
        "inconclusive_sha256": value.inconclusive_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _inconclusive_from_mapping(value: object, path: str) -> PortfolioInconclusive:
    item = _keys(
        value,
        {
            "schema", "attempt_order", "strategy_sha256", "outcome", "reason_code",
            "producer_worker_result_sha256", "checker_worker_result_sha256",
            "inconclusive_sha256", "mathematical_authority",
        },
        path,
    )
    if item["schema"] != INCONCLUSIVE_SCHEMA or item["mathematical_authority"] is not False:
        _fail("schema", path, "inconclusive constants differ")
    result = _make(
        PortfolioInconclusive,
        schema=INCONCLUSIVE_SCHEMA,
        attempt_order=_quantity(item["attempt_order"], f"{path}.attempt_order"),
        strategy_sha256=_digest(item["strategy_sha256"], f"{path}.strategy_sha256"),
        outcome=_choice(item["outcome"], _INCONCLUSIVE_OUTCOMES, f"{path}.outcome"),
        reason_code=_text(item["reason_code"], f"{path}.reason_code", pattern=_REASON, maximum=64),
        producer_worker_result_sha256=_nullable_digest(item["producer_worker_result_sha256"], f"{path}.producer_worker_result_sha256"),
        checker_worker_result_sha256=_nullable_digest(item["checker_worker_result_sha256"], f"{path}.checker_worker_result_sha256"),
        inconclusive_sha256=_digest(item["inconclusive_sha256"], f"{path}.inconclusive_sha256"),
        mathematical_authority=False,
    )
    if result.inconclusive_sha256 != _self_hash(_inconclusive_mapping(result), "inconclusive_sha256"):
        _fail("identity", f"{path}.inconclusive_sha256", "inconclusive identity mismatch")
    return result


def _make_inconclusive(attempt: PortfolioAttempt, reason_code: str) -> PortfolioInconclusive:
    mapping: dict[str, object] = {
        "schema": INCONCLUSIVE_SCHEMA,
        "attempt_order": attempt.attempt_order,
        "strategy_sha256": attempt.strategy_sha256,
        "outcome": attempt.outcome,
        "reason_code": reason_code,
        "producer_worker_result_sha256": attempt.producer_worker_result_sha256,
        "checker_worker_result_sha256": attempt.checker_worker_result_sha256,
        "inconclusive_sha256": None,
        "mathematical_authority": False,
    }
    mapping["inconclusive_sha256"] = _self_hash(mapping, "inconclusive_sha256")
    return _inconclusive_from_mapping(mapping, "inconclusive")


def _result_mapping(value: ProofSearchPortfolioResult, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "contract_id": value.contract_id,
        "contract_sha256": value.contract_sha256,
        "deterministic_planner_contract_sha256": value.deterministic_planner_contract_sha256,
        "isolated_worker_contract_sha256": value.isolated_worker_contract_sha256,
        "resource_budget_contract_sha256": value.resource_budget_contract_sha256,
        "engine_result_contract_sha256": value.engine_result_contract_sha256,
        "evidence_contract_sha256": value.evidence_contract_sha256,
        "certificate_contract_sha256": value.certificate_contract_sha256,
        "theory_plugin_contract_sha256": value.theory_plugin_contract_sha256,
        "capability_registry_contract_sha256": value.capability_registry_contract_sha256,
        "trust_transition_contract_sha256": value.trust_transition_contract_sha256,
        "status": value.status,
        "mathematical_verdict": value.mathematical_verdict,
        "reason_code": value.reason_code,
        "request_sha256": value.request_sha256,
        "planning_result_sha256": value.planning_result_sha256,
        "initial_parent_budget_sha256": value.initial_parent_budget_sha256,
        "final_parent_budget_sha256": value.final_parent_budget_sha256,
        "preference_policy": value.preference_policy,
        "attempts": [_attempt_mapping(item) for item in value.attempts],
        "inconclusive_outcomes": [_inconclusive_mapping(item) for item in value.inconclusive_outcomes],
        "selected_strategy_sha256": value.selected_strategy_sha256,
        "selected_evidence_sha256": value.selected_evidence_sha256,
        "selected_certificate_sha256": value.selected_certificate_sha256,
        "selected_checker_decision_sha256": value.selected_checker_decision_sha256,
        "authority_tier": value.authority_tier,
        "result_sha256": value.result_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _result_from_mapping(
    value: object,
    *,
    final_parent_budget: bytes | None = None,
    selected_evidence: bytes | None = None,
    selected_certificate: bytes | None = None,
) -> ProofSearchPortfolioResult:
    item = _keys(
        value,
        {
            "schema", "contract_id", "contract_sha256", "deterministic_planner_contract_sha256",
            "isolated_worker_contract_sha256", "resource_budget_contract_sha256",
            "engine_result_contract_sha256", "evidence_contract_sha256",
            "certificate_contract_sha256", "theory_plugin_contract_sha256",
            "capability_registry_contract_sha256", "trust_transition_contract_sha256",
            "status", "mathematical_verdict", "reason_code", "request_sha256",
            "planning_result_sha256", "initial_parent_budget_sha256",
            "final_parent_budget_sha256", "preference_policy", "attempts",
            "inconclusive_outcomes", "selected_strategy_sha256", "selected_evidence_sha256",
            "selected_certificate_sha256", "selected_checker_decision_sha256",
            "authority_tier", "result_sha256", "mathematical_authority",
        },
        "$",
    )
    constants = (
        item["schema"] == RESULT_SCHEMA
        and item["contract_id"] == PORTFOLIO_CONTRACT_ID
        and item["contract_sha256"] == PORTFOLIO_CONTRACT_SHA256
        and item["deterministic_planner_contract_sha256"] == DETERMINISTIC_PLANNER_CONTRACT_SHA256
        and item["isolated_worker_contract_sha256"] == ISOLATED_WORKER_CONTRACT_SHA256
        and item["resource_budget_contract_sha256"] == RESOURCE_BUDGET_CONTRACT_SHA256
        and item["engine_result_contract_sha256"] == ENGINE_RESULT_CONTRACT_SHA256
        and item["evidence_contract_sha256"] == EVIDENCE_CONTRACT_SHA256
        and item["certificate_contract_sha256"] == CERTIFICATE_CONTRACT_SHA256
        and item["theory_plugin_contract_sha256"] == THEORY_PLUGIN_CONTRACT_SHA256
        and item["capability_registry_contract_sha256"] == CAPABILITY_REGISTRY_CONTRACT_SHA256
        and item["trust_transition_contract_sha256"] == TRUST_TRANSITION_CONTRACT_SHA256
        and item["preference_policy"] == PREFERENCE_POLICY
        and item["mathematical_authority"] is False
    )
    if not constants:
        _fail("contract", "$", "portfolio result contract bindings differ")
    raw_attempts = _array(item["attempts"], "$.attempts")
    attempts = tuple(_attempt_from_mapping(raw, f"$.attempts[{index}]") for index, raw in enumerate(raw_attempts))
    raw_inconclusive = _array(item["inconclusive_outcomes"], "$.inconclusive_outcomes")
    inconclusive = tuple(_inconclusive_from_mapping(raw, f"$.inconclusive_outcomes[{index}]") for index, raw in enumerate(raw_inconclusive))
    result = _make(
        ProofSearchPortfolioResult,
        schema=RESULT_SCHEMA,
        contract_id=PORTFOLIO_CONTRACT_ID,
        contract_sha256=PORTFOLIO_CONTRACT_SHA256,
        deterministic_planner_contract_sha256=DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        isolated_worker_contract_sha256=ISOLATED_WORKER_CONTRACT_SHA256,
        resource_budget_contract_sha256=RESOURCE_BUDGET_CONTRACT_SHA256,
        engine_result_contract_sha256=ENGINE_RESULT_CONTRACT_SHA256,
        evidence_contract_sha256=EVIDENCE_CONTRACT_SHA256,
        certificate_contract_sha256=CERTIFICATE_CONTRACT_SHA256,
        theory_plugin_contract_sha256=THEORY_PLUGIN_CONTRACT_SHA256,
        capability_registry_contract_sha256=CAPABILITY_REGISTRY_CONTRACT_SHA256,
        trust_transition_contract_sha256=TRUST_TRANSITION_CONTRACT_SHA256,
        status=_choice(item["status"], _TERMINAL_STATUSES, "$.status"),
        mathematical_verdict=_choice(item["mathematical_verdict"], ("proved", "refuted", "inconclusive", "none"), "$.mathematical_verdict"),
        reason_code=_text(item["reason_code"], "$.reason_code", pattern=_REASON, maximum=64),
        request_sha256=_nullable_digest(item["request_sha256"], "$.request_sha256"),
        planning_result_sha256=_nullable_digest(item["planning_result_sha256"], "$.planning_result_sha256"),
        initial_parent_budget_sha256=_nullable_digest(item["initial_parent_budget_sha256"], "$.initial_parent_budget_sha256"),
        final_parent_budget_sha256=_nullable_digest(item["final_parent_budget_sha256"], "$.final_parent_budget_sha256"),
        preference_policy=PREFERENCE_POLICY,
        attempts=attempts,
        inconclusive_outcomes=inconclusive,
        selected_strategy_sha256=_nullable_digest(item["selected_strategy_sha256"], "$.selected_strategy_sha256"),
        selected_evidence_sha256=_nullable_digest(item["selected_evidence_sha256"], "$.selected_evidence_sha256"),
        selected_certificate_sha256=_nullable_digest(item["selected_certificate_sha256"], "$.selected_certificate_sha256"),
        selected_checker_decision_sha256=_nullable_digest(item["selected_checker_decision_sha256"], "$.selected_checker_decision_sha256"),
        authority_tier=_choice(item["authority_tier"], ("none", "checker_attestation", "external_proof_assistant"), "$.authority_tier"),
        result_sha256=_nullable_digest(item["result_sha256"], "$.result_sha256"),
        mathematical_authority=False,
        _final_parent_budget=final_parent_budget,
        _selected_evidence=selected_evidence,
        _selected_certificate=selected_certificate,
    )
    if result.result_sha256 is None or result.result_sha256 != _self_hash(_result_mapping(result), "result_sha256"):
        _fail("identity", "$.result_sha256", "portfolio result identity mismatch")
    if tuple(attempt.attempt_order for attempt in attempts) != tuple(range(len(attempts))):
        _fail("result", "$.attempts", "attempt order is not canonical")
    inconclusive_orders = tuple(entry.attempt_order for entry in inconclusive)
    expected_orders = tuple(attempt.attempt_order for attempt in attempts if attempt.outcome in _INCONCLUSIVE_OUTCOMES)
    if inconclusive_orders != expected_orders or any(
        entry.strategy_sha256 != attempts[entry.attempt_order].strategy_sha256
        or entry.outcome != attempts[entry.attempt_order].outcome
        or entry.producer_worker_result_sha256 != attempts[entry.attempt_order].producer_worker_result_sha256
        or entry.checker_worker_result_sha256 != attempts[entry.attempt_order].checker_worker_result_sha256
        for entry in inconclusive
    ):
        _fail("result", "$.inconclusive_outcomes", "inconclusive inventory differs from attempts")
    selected = (
        result.selected_strategy_sha256,
        result.selected_evidence_sha256,
        result.selected_certificate_sha256,
        result.selected_checker_decision_sha256,
    )
    if result.status == "succeeded":
        if any(entry is None for entry in selected) or result.mathematical_verdict not in {"proved", "refuted"} or result.authority_tier == "none" or not attempts or attempts[-1].outcome != "success":
            _fail("result", "$", "successful result lacks one exact checked selection")
        final_attempt = attempts[-1]
        expected_reason = "CHECKED_PROOF" if result.mathematical_verdict == "proved" else "CHECKED_REFUTATION"
        if (
            result.reason_code != expected_reason
            or result.selected_strategy_sha256 != final_attempt.strategy_sha256
            or result.selected_evidence_sha256 != final_attempt.evidence_sha256
            or result.selected_checker_decision_sha256 != final_attempt.checker_decision_sha256
        ):
            _fail("result", "$", "selected checked identities differ from the successful attempt")
    elif any(entry is not None for entry in selected) or result.authority_tier != "none" or result.mathematical_verdict not in {"inconclusive", "none"}:
        _fail("result", "$", "non-success result carries selected authority")
    if (final_parent_budget is None) != (result.final_parent_budget_sha256 is None) or (selected_evidence is None) != (result.selected_evidence_sha256 is None) or (selected_certificate is None) != (result.selected_certificate_sha256 is None):
        _fail("result", "$", "retained bytes and metadata inventory differ")
    for raw, digest, path in (
        (final_parent_budget, result.final_parent_budget_sha256, "$.final_parent_budget_sha256"),
        (selected_evidence, result.selected_evidence_sha256, "$.selected_evidence_sha256"),
        (selected_certificate, result.selected_certificate_sha256, "$.selected_certificate_sha256"),
    ):
        if raw is not None and (type(raw) is not bytes or _sha(raw) != digest):
            _fail("result", path, "retained bytes differ")
    if final_parent_budget is not None:
        _validate_parent_budget(final_parent_budget)
    if result.status == "succeeded" and selected_evidence is not None and selected_certificate is not None:
        evidence_value = _parse(selected_evidence, "selected_evidence", maximum=MAX_CHECKER_PAYLOAD_BYTES)
        certificate_value = _parse(selected_certificate, "selected_certificate", maximum=MAX_CHECKER_PAYLOAD_BYTES)
        if (
            evidence_value.get("schema") != "mathhead.evidence.v1"
            or type(evidence_value.get("outcome")) is not dict
            or evidence_value["outcome"].get("status") != "produced"  # type: ignore[union-attr]
            or evidence_value.get("extensions") != {"org.mathhead.portfolio.claim": result.mathematical_verdict}
            or certificate_value.get("schema") != "mathhead.certificate.v1"
            or certificate_value.get("subject") != evidence_value.get("subject")
            or type(certificate_value.get("evidence")) is not dict
            or certificate_value["evidence"].get("evidence_sha256") != _sha(selected_evidence)  # type: ignore[union-attr]
            or certificate_value["evidence"].get("evidence_id") != evidence_value.get("evidence_id")  # type: ignore[union-attr]
            or type(certificate_value.get("verdict")) is not dict
            or certificate_value["verdict"].get("status") != "verified"  # type: ignore[union-attr]
            or certificate_value["verdict"].get("authority")  # type: ignore[union-attr]
            != ("checker_attested" if result.authority_tier == "checker_attestation" else "external_verified")
            or type(certificate_value.get("checker")) is not dict
            or type(evidence_value.get("producer")) is not dict
            or certificate_value["checker"].get("component_id")  # type: ignore[union-attr]
            == evidence_value["producer"].get("component_id")  # type: ignore[union-attr]
        ):
            _fail("result", "$", "retained checked Evidence and Certificate chain differs")
    if final_parent_budget is not None and attempts and attempts[-1].parent_budget_after_sha256 != _sha(final_parent_budget):
        _fail("result", "$.final_parent_budget_sha256", "final ledger differs from the attempt chain")
    for previous, following in zip(attempts, attempts[1:]):
        if previous.parent_budget_after_sha256 != following.parent_budget_before_sha256:
            _fail("budget", "$.attempts", "parent ledger chain is discontinuous")
    return result


def _make_result(
    *,
    status: str,
    mathematical_verdict: str,
    reason_code: str,
    request_sha256: str | None,
    planning_result_sha256: str | None,
    initial_parent_budget: bytes | None,
    final_parent_budget: bytes | None,
    attempts: tuple[PortfolioAttempt, ...] = (),
    inconclusive: tuple[PortfolioInconclusive, ...] = (),
    selected_strategy_sha256: str | None = None,
    selected_evidence: bytes | None = None,
    selected_certificate: bytes | None = None,
    selected_checker_decision_sha256: str | None = None,
    authority_tier: str = "none",
) -> ProofSearchPortfolioResult:
    mapping: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "contract_id": PORTFOLIO_CONTRACT_ID,
        "contract_sha256": PORTFOLIO_CONTRACT_SHA256,
        "deterministic_planner_contract_sha256": DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        "isolated_worker_contract_sha256": ISOLATED_WORKER_CONTRACT_SHA256,
        "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256,
        "engine_result_contract_sha256": ENGINE_RESULT_CONTRACT_SHA256,
        "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256,
        "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256,
        "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256,
        "capability_registry_contract_sha256": CAPABILITY_REGISTRY_CONTRACT_SHA256,
        "trust_transition_contract_sha256": TRUST_TRANSITION_CONTRACT_SHA256,
        "status": status,
        "mathematical_verdict": mathematical_verdict,
        "reason_code": reason_code,
        "request_sha256": request_sha256,
        "planning_result_sha256": planning_result_sha256,
        "initial_parent_budget_sha256": None if initial_parent_budget is None else _sha(initial_parent_budget),
        "final_parent_budget_sha256": None if final_parent_budget is None else _sha(final_parent_budget),
        "preference_policy": PREFERENCE_POLICY,
        "attempts": [_attempt_mapping(item) for item in attempts],
        "inconclusive_outcomes": [_inconclusive_mapping(item) for item in inconclusive],
        "selected_strategy_sha256": selected_strategy_sha256,
        "selected_evidence_sha256": None if selected_evidence is None else _sha(selected_evidence),
        "selected_certificate_sha256": None if selected_certificate is None else _sha(selected_certificate),
        "selected_checker_decision_sha256": selected_checker_decision_sha256,
        "authority_tier": authority_tier,
        "result_sha256": None,
        "mathematical_authority": False,
    }
    mapping["result_sha256"] = _self_hash(mapping, "result_sha256")
    return _result_from_mapping(
        mapping,
        final_parent_budget=final_parent_budget,
        selected_evidence=selected_evidence,
        selected_certificate=selected_certificate,
    )


def parse_proof_search_portfolio_result(
    data: bytes,
    final_parent_budget: bytes | None = None,
    selected_evidence: bytes | None = None,
    selected_certificate: bytes | None = None,
) -> ProofSearchPortfolioResult:
    """Parse a closed portfolio result and optionally bind retained exact bytes."""
    return _result_from_mapping(
        _parse(data, "$"),
        final_parent_budget=final_parent_budget,
        selected_evidence=selected_evidence,
        selected_certificate=selected_certificate,
    )


def validate_proof_search_portfolio_result(value: ProofSearchPortfolioResult) -> None:
    if type(value) is not ProofSearchPortfolioResult:
        _fail("type", "$", "expected exact ProofSearchPortfolioResult")
    rebuilt = _result_from_mapping(
        _result_mapping(value),
        final_parent_budget=value._final_parent_budget,
        selected_evidence=value._selected_evidence,
        selected_certificate=value._selected_certificate,
    )
    if rebuilt != value:
        _fail("result", "$", "in-memory portfolio result differs from reconstruction")


def proof_search_portfolio_result_bytes(value: ProofSearchPortfolioResult) -> bytes:
    if type(value) is not ProofSearchPortfolioResult:
        _fail("type", "$", "expected exact ProofSearchPortfolioResult")
    validate_proof_search_portfolio_result(value)
    return _canonical(_result_mapping(value))


def proof_search_portfolio_semantic_bytes(value: ProofSearchPortfolioResult) -> bytes:
    """Return the stable classification projection without runtime ledger observations."""
    if type(value) is not ProofSearchPortfolioResult:
        _fail("type", "$", "expected exact ProofSearchPortfolioResult")
    validate_proof_search_portfolio_result(value)
    mapping = _result_mapping(value)
    mapping["final_parent_budget_sha256"] = None
    mapping["result_sha256"] = None
    attempts = mapping["attempts"]
    if type(attempts) is not list:
        _fail("result", "$.attempts", "invalid result projection")
    for attempt in attempts:
        attempt["parent_budget_before_sha256"] = None
        attempt["parent_budget_after_sha256"] = None
        attempt["attempt_sha256"] = None
    return _canonical(mapping)


def proof_search_portfolio_budget_bytes(value: ProofSearchPortfolioResult) -> bytes:
    if type(value) is not ProofSearchPortfolioResult or value._final_parent_budget is None:
        _fail("type", "$", "result has no retained final parent ledger")
    return value._final_parent_budget


def proof_search_portfolio_selected_bytes(value: ProofSearchPortfolioResult, kind: str) -> bytes:
    if type(value) is not ProofSearchPortfolioResult or kind not in {"evidence", "certificate"}:
        _fail("type", "$", "expected exact result and selected byte kind")
    raw = value._selected_evidence if kind == "evidence" else value._selected_certificate
    if raw is None:
        _fail("result", "$", "result has no selected artifact of that kind")
    return raw


@dataclass(frozen=True, slots=True)
class _PreparedPortfolio:
    request: ProofSearchPortfolioRequest
    plan: PlanningResult
    descriptors: dict[str, dict[str, object]]
    bindings: tuple[PortfolioExecutionBinding, ...]
    artifacts_by_role: dict[str, bytes]
    executable_paths: dict[str, str]


@dataclass(frozen=True, slots=True)
class _PortfolioAuditAttempt:
    """Safe, validated execution observations retained only by MH-054."""

    attempt_order: int
    strategy_sha256: str
    producer_request_sha256: str
    producer_result_sha256: str
    producer_result_preimage: bytes
    producer_status: str
    producer_reason_code: str
    producer_parent_before: bytes
    producer_parent_after: bytes
    evidence: bytes | None
    checker_request_sha256: str | None
    checker_result_sha256: str | None
    checker_result_preimage: bytes | None
    checker_status: str
    checker_reason_code: str
    checker_parent_before: bytes | None
    checker_parent_after: bytes | None
    checker_decision: bytes | None
    certificate: bytes | None
    outcome: str
    transition_sha256: str


def _descriptor_inventory(descriptors: tuple[bytes, ...]) -> dict[str, dict[str, object]]:
    if type(descriptors) is not tuple or len(descriptors) > 10_000 or any(type(item) is not bytes for item in descriptors):
        _fail("type", "descriptors", "expected a bounded exact descriptor tuple")
    result: dict[str, dict[str, object]] = {}
    total = 0
    for index, raw in enumerate(descriptors):
        total += len(raw)
        if not raw or len(raw) > MAX_ARTIFACT_BYTES or total > MAX_INPUT_BYTES:
            _fail("limit", f"descriptors[{index}]", "descriptor byte ceiling exceeded")
        digest = _sha(raw)
        if digest in result:
            _fail("descriptor", f"descriptors[{index}]", "duplicate descriptor bytes")
        try:
            result[digest] = _validate_theory_plugin_descriptor(raw, f"descriptors[{index}]")
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            raise ProofSearchPortfolioValidationError("descriptor", f"descriptors[{index}]", "invalid accepted TheoryPlugin descriptor") from exc
    return result


def _descriptor_strategy_parts(
    descriptor: dict[str, object], strategy: PlanningStrategy
) -> tuple[dict[str, object], dict[str, object], str, tuple[dict[str, object], ...]]:
    raw = descriptor["raw"]
    if type(raw) is not dict:
        _fail("descriptor", "descriptor", "normalized descriptor has no raw mapping")
    components = raw["components"]
    implementation = raw["implementation"]
    if type(components) is not dict or type(implementation) is not dict:
        _fail("descriptor", "descriptor", "component provenance is incomplete")
    producer = components["producer"]
    checker = components["checker"]
    if type(producer) is not dict or type(checker) is not dict:
        _fail("descriptor", "descriptor.components", "component mappings differ")
    capabilities = descriptor["capabilities"]
    if type(capabilities) is not tuple:
        _fail("descriptor", "descriptor.capabilities", "capability inventory differs")
    selected = [item for item in capabilities if item["capability_id"] == strategy.capability_id]  # type: ignore[index]
    if len(selected) != 1:
        _fail("descriptor", "descriptor.capabilities", "planned capability is absent or ambiguous")
    capability = selected[0]
    if (
        descriptor["descriptor_sha256"] != strategy.descriptor_sha256
        or descriptor["plugin_id"] != strategy.plugin_id
        or descriptor["plugin_version"] != strategy.plugin_version
        or descriptor["producer_component_id"] != strategy.producer_component_id
        or descriptor["checker_component_id"] != strategy.checker_component_id
        or capability["kind"] != strategy.capability_kind
        or producer["component_id"] != strategy.producer_component_id
        or checker["component_id"] != strategy.checker_component_id
    ):
        _fail("descriptor", "descriptor", "descriptor and planned strategy identities differ")
    operations = descriptor["operations"]
    if type(operations) is not dict or operations.get(strategy.operation, {}).get("component_id") != strategy.component_id or operations.get("check", {}).get("component_id") != strategy.checker_component_id:  # type: ignore[union-attr]
        _fail("descriptor", "descriptor.operations", "planned producer/checker ABI differs")
    formats = capability["certificate_formats"]
    if type(formats) is not tuple or not formats:
        _fail("descriptor", "descriptor.capabilities.certificate_formats", "checker has no accepted Certificate format")
    environment = _digest(implementation["environment_contract_sha256"], "descriptor.implementation.environment_contract_sha256")
    return producer, checker, environment, formats


def _prepare_portfolio(
    request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    executable_paths: tuple[tuple[str, str], ...],
    workspace_root: str,
    cancel_event: Event | None,
) -> _PreparedPortfolio:
    if (
        type(request) is not bytes
        or type(planning_result) is not bytes
        or type(parent_budget) is not bytes
        or type(bindings) is not tuple
        or type(artifacts) is not tuple
        or type(executable_paths) is not tuple
        or type(workspace_root) is not str
        or not workspace_root
        or (cancel_event is not None and type(cancel_event) is not Event)
    ):
        _fail("type", "$", "portfolio boundary requires exact immutable built-in values")
    request_value = parse_proof_search_portfolio_request(request)
    if request_value.planning_result_sha256 != _sha(planning_result) or request_value.parent_budget_sha256 != _sha(parent_budget):
        _fail("request", "$", "request does not bind plan and parent ledger bytes")
    try:
        plan = parse_planning_result(planning_result)
    except DeterministicPlannerValidationError as exc:
        raise ProofSearchPortfolioValidationError("plan", "planning_result", "invalid deterministic plan") from exc
    if plan.status != "planned" or plan.entry_strategy_sha256 is None or not plan.strategies:
        _fail("plan", "planning_result", "portfolio requires one nonempty planned graph")
    _validate_parent_budget(parent_budget)

    descriptor_values = _descriptor_inventory(descriptors)
    if tuple(sorted(descriptor_values)) != request_value.descriptor_sha256s:
        _fail("descriptor", "descriptors", "descriptor inventory differs from the request")
    required_descriptors = {
        digest
        for strategy in plan.strategies
        for digest in (strategy.descriptor_sha256, *strategy.dependency_descriptor_sha256s)
    }
    if set(descriptor_values) != required_descriptors:
        _fail("descriptor", "descriptors", "descriptor inventory is missing or surplus for the plan")

    if len(bindings) != len(plan.strategies) or len(bindings) > MAX_ITEMS or any(type(item) is not bytes for item in bindings):
        _fail("binding", "bindings", "one exact execution binding per strategy is required")
    if tuple(_sha(item) for item in bindings) != request_value.binding_sha256s:
        _fail("binding", "bindings", "binding inventory differs from the request")
    binding_values = tuple(parse_portfolio_execution_binding(item) for item in bindings)

    if len(artifacts) != len(request_value.artifact_bindings) or any(type(item) is not bytes for item in artifacts):
        _fail("artifact", "artifacts", "artifact inventory length or type differs")
    artifact_map: dict[str, bytes] = {}
    total = 0
    for index, (binding, raw) in enumerate(zip(request_value.artifact_bindings, artifacts)):
        total += len(raw)
        if len(raw) != binding.bytes or _sha(raw) != binding.sha256 or len(raw) > MAX_ARTIFACT_BYTES or total > MAX_INPUT_BYTES:
            _fail("artifact", f"artifacts[{index}]", "artifact bytes differ from the request")
        artifact_map[binding.role] = raw
    if "portfolio_evidence" in artifact_map:
        _fail("artifact", "artifacts", "reserved checker Evidence role is caller-supplied")

    for index, (strategy, binding) in enumerate(zip(plan.strategies, binding_values)):
        if (
            strategy.plan_order != index
            or binding.plan_order != index
            or binding.strategy_sha256 != strategy.strategy_sha256
            or binding.descriptor_sha256 != strategy.descriptor_sha256
            or binding.producer_component_id != strategy.producer_component_id
            or binding.checker_component_id != strategy.checker_component_id
            or len(binding.checker_arguments) >= MAX_ARGUMENTS
        ):
            _fail("binding", f"bindings[{index}]", "binding and planned strategy differ")
        for artifact in binding.input_artifacts:
            raw = artifact_map.get(artifact.role)
            if raw is None or _sha(raw) != artifact.sha256 or len(raw) != artifact.bytes:
                _fail("artifact", f"bindings[{index}].input_artifacts", "binding artifact is absent or stale")
        _descriptor_strategy_parts(descriptor_values[strategy.descriptor_sha256], strategy)

    paths: dict[str, str] = {}
    for index, pair in enumerate(executable_paths):
        if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not str or type(pair[1]) is not str or not pair[1]:
            _fail("executable", f"executable_paths[{index}]", "expected digest and explicit path strings")
        digest = _digest(pair[0], f"executable_paths[{index}][0]")
        if digest in paths:
            _fail("executable", "executable_paths", "duplicate executable digest")
        paths[digest] = pair[1]
    expected_paths = {
        digest
        for binding in binding_values
        for digest in (binding.producer_executable_sha256, binding.checker_executable_sha256)
    }
    if set(paths) != expected_paths:
        _fail("executable", "executable_paths", "executable path inventory is missing or surplus")
    return _PreparedPortfolio(
        request=request_value,
        plan=plan,
        descriptors=descriptor_values,
        bindings=binding_values,
        artifacts_by_role=artifact_map,
        executable_paths=paths,
    )


_WORKER_FAMILY: Final = {
    "sympy": "sympy",
    "enumeration": "python_enumeration",
    "smt": "smt",
    "external": "external_process",
}


def _worker_request(
    *,
    plan_bytes: bytes,
    parent_budget: bytes,
    strategy: PlanningStrategy,
    binding: PortfolioExecutionBinding,
    phase: str,
    arguments: tuple[str, ...],
    artifacts: tuple[tuple[str, bytes], ...],
    executable_sha256: str,
) -> bytes:
    family = binding.producer_family if phase == "producer" else binding.checker_family
    identity = strategy.strategy_sha256[:16]
    lease_id = f"lease_portfolio_{strategy.plan_order}_{phase}_{identity}"
    child_budget_id = f"budget_portfolio_{strategy.plan_order}_{phase}_{identity}"
    limits = {name: getattr(strategy.resource_request.requested, name) for name in RESOURCE_DIMENSIONS}
    mapping: dict[str, object] = {
        "schema": "mathhead.isolated-worker-request.v1",
        "planning_result_sha256": _sha(plan_bytes),
        "strategy_sha256": strategy.strategy_sha256,
        "descriptor_sha256": strategy.descriptor_sha256,
        "family": _WORKER_FAMILY[family],
        "protocol": "raw_stdout_v1",
        "executable_sha256": executable_sha256,
        "arguments": list(arguments),
        "artifact_bindings": [
            {"role": role, "sha256": _sha(raw), "bytes": len(raw)}
            for role, raw in artifacts
        ],
        "parent_budget_sha256": _sha(parent_budget),
        "lease_id": lease_id,
        "child_budget_id": child_budget_id,
        "resource_limits": limits,
        "request_sha256": None,
        "mathematical_authority": False,
    }
    mapping["request_sha256"] = _self_hash(mapping, "request_sha256")
    raw = _canonical(mapping)
    parse_isolated_worker_request(raw)
    return raw


def _supervise_exact(
    worker_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    artifacts: tuple[bytes, ...],
    executable_path: str,
    workspace_root: str,
    cancel_event: Event | None,
) -> tuple[IsolatedWorkerResult, bytes]:
    request_value = parse_isolated_worker_request(worker_request)
    result = supervise_worker(
        worker_request,
        planning_result,
        parent_budget,
        artifacts,
        executable_path,
        workspace_root,
        cancel_event,
    )
    if type(result) is not IsolatedWorkerResult:
        _fail("result", "worker", "supervisor returned a caller-authored result type")
    validate_isolated_worker_result(result)
    if (
        result.request_sha256 != request_value.request_sha256
        or result.planning_result_sha256 != request_value.planning_result_sha256
        or result.strategy_sha256 != request_value.strategy_sha256
        or result.semantic_sha256 is None
    ):
        _fail("result", "worker", "worker result does not bind its invocation")
    next_parent = parent_budget
    if result.lease_reconciled:
        next_parent = isolated_worker_budget_bytes(result, "parent")
        _validate_parent_budget(next_parent)
    if result.status not in {"invalid", "refused", "unsupported"} and (
        not result.lease_reconciled or not result.tree_terminated
    ):
        _fail("result", "worker", "worker containment or ledger reconciliation is incomplete")
    return result, next_parent


def _portfolio_worker_preimage(
    result: IsolatedWorkerResult,
    retained_artifact: bytes | None,
) -> bytes:
    mapping = _parse(isolated_worker_result_bytes(result), "worker_result")
    stable = {
        name: mapping[name]
        for name in (
            "schema", "contract_id", "contract_sha256", "status", "reason_code",
            "planning_result_sha256", "strategy_sha256",
            "tree_terminated", "lease_reconciled", "mathematical_authority",
        )
    }
    # Host capability and diagnostic prose are effect observations, not
    # portable portfolio semantics.  Their terminal classification is already
    # represented by status/reason_code; retaining them would make an audited
    # logical identity platform- and message-dependent.
    stable["capability"] = None
    stable["diagnostics"] = []
    stable["artifacts"] = []
    if retained_artifact is not None:
        if type(retained_artifact) is not bytes:
            _fail("type", "worker_result.artifact", "retained artifact must be exact bytes")
        raw_artifacts = mapping["artifacts"]
        if (
            type(raw_artifacts) is not list
            or not raw_artifacts
            or type(raw_artifacts[0]) is not dict
            or raw_artifacts[0].get("role") != "stdout"
            or raw_artifacts[0].get("retained_bytes") != len(retained_artifact)
            or raw_artifacts[0].get("retained_sha256") != _sha(retained_artifact)
        ):
            _fail("result", "worker_result.artifact", "validated artifact link differs")
        stable["artifacts"] = [raw_artifacts[0]]
    return _canonical(stable)


def _worker_stdout(result: IsolatedWorkerResult) -> bytes:
    if result.status != "completed" or not result.artifacts or result.artifacts[0].role != "stdout":
        _fail("result", "worker.artifacts", "completed worker has no exact stdout")
    raw = worker_artifact_bytes(result.artifacts[0])
    if len(raw) > MAX_CHECKER_PAYLOAD_BYTES:
        _fail("limit", "worker.stdout", "checker protocol payload exceeds its ceiling")
    return raw


def _checker_envelope(
    stdout: bytes,
    evidence_data: bytes,
    evidence: dict[str, object],
    claim: str,
    strategy: PlanningStrategy,
    checker: dict[str, object],
    environment_contract_sha256: str,
    certificate_formats: tuple[dict[str, object], ...],
) -> tuple[PortfolioCheckerDecision, bytes, str, str]:
    envelope = _keys(
        _parse(stdout, "checker_output", maximum=MAX_CHECKER_PAYLOAD_BYTES),
        {"certificate", "decision"},
        "checker_output",
    )
    if type(envelope["certificate"]) is not dict or type(envelope["decision"]) is not dict:
        _fail("checker", "checker_output", "checker envelope members must be objects")
    certificate_data = _canonical(envelope["certificate"], maximum=MAX_CHECKER_PAYLOAD_BYTES)
    decision_data = _canonical(envelope["decision"], maximum=MAX_CHECKER_PAYLOAD_BYTES)
    _, verdict, authority = _validate_certificate(
        certificate_data,
        evidence_data,
        evidence,
        strategy,
        checker,
        environment_contract_sha256,
        certificate_formats,
    )
    decision = parse_portfolio_checker_decision(decision_data, certificate_data)
    expected_decision_verdict = "invalid" if verdict == "disagreement" else verdict
    expected_reason = (
        "CHECKER_AGREED"
        if verdict == "verified" and decision.agreement
        else "CHECKER_DISAGREED"
        if verdict in {"verified", "disagreement"}
        else "CHECKER_REJECTED"
        if verdict == "invalid"
        else "CERTIFICATE_INVALID"
        if verdict == "verifier_failed"
        else "CHECKER_INCONCLUSIVE"
    )
    if (
        decision.strategy_sha256 != strategy.strategy_sha256
        or decision.producer_component_id != strategy.producer_component_id
        or decision.checker_component_id != strategy.checker_component_id
        or decision.subject_sha256 != _sha(_canonical(evidence["subject"]))
        or decision.claim != claim
        or decision.evidence_sha256 != _sha(evidence_data)
        or decision.evidence_bytes != len(evidence_data)
        or decision.certificate_verdict != expected_decision_verdict
        or decision.certificate_authority != authority
        or decision.reason_code != expected_reason
    ):
        _fail("checker", "checker_output.decision", "checker decision disagrees with independently reconstructed bytes")
    return decision, certificate_data, verdict, authority


def _worker_outcome(result: IsolatedWorkerResult, *, checker: bool) -> tuple[str, str]:
    if result.status == "completed":
        return "success", result.reason_code
    if result.status == "cancelled":
        return "cancelled", result.reason_code
    if result.status == "exhausted" or (result.status == "refused" and result.reason_code == "BUDGET_INSUFFICIENT"):
        return "exhausted", result.reason_code
    if result.status == "unsupported":
        return ("checker_inconclusive" if checker else "unsupported"), result.reason_code
    return ("verifier_failure" if checker else "producer_error"), result.reason_code


def _evidence_outcome(status: str) -> tuple[str, str]:
    return {
        "unsupported": ("unsupported", "EVIDENCE_UNSUPPORTED"),
        "incomplete": ("ambiguous", "EVIDENCE_INCOMPLETE"),
        "cancelled": ("cancelled", "EVIDENCE_CANCELLED"),
        "exhausted": ("exhausted", "EVIDENCE_EXHAUSTED"),
        "truncated": ("truncated", "EVIDENCE_TRUNCATED"),
        "error": ("producer_error", "EVIDENCE_ERROR"),
    }[status]


def _decision_outcome(decision: PortfolioCheckerDecision) -> tuple[str, str]:
    if decision.reason_code == "CHECKER_AGREED":
        return "success", "CHECKER_AGREED"
    if decision.reason_code in {"CHECKER_REJECTED", "CHECKER_DISAGREED"}:
        return "checker_disagreement", decision.reason_code
    if decision.certificate_verdict == "cancelled":
        return "cancelled", "CHECKER_CANCELLED"
    if decision.certificate_verdict == "exhausted":
        return "exhausted", "CHECKER_EXHAUSTED"
    if decision.certificate_verdict == "truncated":
        return "truncated", "CHECKER_TRUNCATED"
    if decision.certificate_verdict == "verifier_failed" or decision.reason_code == "CERTIFICATE_INVALID":
        return "verifier_failure", "CERTIFICATE_INVALID"
    return "checker_inconclusive", "CHECKER_INCONCLUSIVE"


def _transition(strategy: PlanningStrategy, outcome: str):
    matches = [item for item in strategy.transitions if item.outcome == outcome]
    if len(matches) != 1:
        _fail("transition", "strategy.transitions", "classified outcome has no exact transition")
    return matches[0]


def _terminal_result(
    *,
    transition: object,
    reason_code: str,
    request_sha256: str,
    planning_result_sha256: str,
    initial_parent_budget: bytes,
    final_parent_budget: bytes,
    attempts: tuple[PortfolioAttempt, ...],
    inconclusive: tuple[PortfolioInconclusive, ...],
) -> ProofSearchPortfolioResult:
    terminal_state = transition.terminal_state  # type: ignore[attr-defined]
    if terminal_state is None:
        _fail("transition", "transition", "terminal transition has no terminal state")
    return _make_result(
        status=terminal_state,
        mathematical_verdict="inconclusive",
        reason_code=reason_code,
        request_sha256=request_sha256,
        planning_result_sha256=planning_result_sha256,
        initial_parent_budget=initial_parent_budget,
        final_parent_budget=final_parent_budget,
        attempts=attempts,
        inconclusive=inconclusive,
    )


def _execute_portfolio(
    request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    executable_paths: tuple[tuple[str, str], ...],
    workspace_root: str,
    cancel_event: Event | None,
    audit_attempts: list[_PortfolioAuditAttempt] | None,
) -> ProofSearchPortfolioResult:
    prepared: _PreparedPortfolio | None = None
    initial_parent: bytes | None = None
    current_parent: bytes | None = None
    attempts: list[PortfolioAttempt] = []
    inconclusive: list[PortfolioInconclusive] = []
    try:
        prepared = _prepare_portfolio(
            request,
            planning_result,
            parent_budget,
            descriptors,
            bindings,
            artifacts,
            executable_paths,
            workspace_root,
            cancel_event,
        )
        initial_parent = parent_budget
        current_parent = parent_budget
        by_strategy = {item.strategy_sha256: item for item in prepared.plan.strategies}
        current_sha = prepared.plan.entry_strategy_sha256
        visited: set[str] = set()
        while current_sha is not None:
            if current_sha in visited or current_sha not in by_strategy:
                _fail("transition", "planning_result", "portfolio graph revisits or loses a strategy")
            visited.add(current_sha)
            strategy = by_strategy[current_sha]
            binding = prepared.bindings[strategy.plan_order]
            producer, checker, environment_sha, certificate_formats = _descriptor_strategy_parts(
                prepared.descriptors[strategy.descriptor_sha256], strategy
            )
            parent_before = current_parent
            bound_artifacts = tuple(
                (item.role, prepared.artifacts_by_role[item.role])
                for item in binding.input_artifacts
            )
            producer_request = _worker_request(
                plan_bytes=planning_result,
                parent_budget=current_parent,
                strategy=strategy,
                binding=binding,
                phase="producer",
                arguments=binding.producer_arguments,
                artifacts=bound_artifacts,
                executable_sha256=binding.producer_executable_sha256,
            )
            producer_result, current_parent = _supervise_exact(
                producer_request,
                planning_result,
                current_parent,
                tuple(raw for _, raw in bound_artifacts),
                prepared.executable_paths[binding.producer_executable_sha256],
                workspace_root,
                cancel_event,
            )
            producer_parent_after = current_parent
            outcome, reason_code = _worker_outcome(producer_result, checker=False)
            evidence_data: bytes | None = None
            evidence_value: dict[str, object] | None = None
            claim: str | None = None
            checker_result: IsolatedWorkerResult | None = None
            checker_identity: str | None = None
            decision: PortfolioCheckerDecision | None = None
            certificate_data: bytes | None = None
            checker_request_sha256: str | None = None
            checker_parent_before: bytes | None = None
            checker_parent_after: bytes | None = None
            checker_validated_output: bytes | None = None
            authority = "none"

            if outcome == "success":
                try:
                    candidate = _worker_stdout(producer_result)
                    evidence_value, evidence_status = _validate_evidence(
                        candidate, strategy, producer, environment_sha
                    )
                    evidence_data = candidate
                    if evidence_status in {"proved", "refuted"}:
                        claim = evidence_status
                    else:
                        outcome, reason_code = _evidence_outcome(evidence_status)
                except ProofSearchPortfolioValidationError:
                    outcome, reason_code = "invalid_evidence", "EVIDENCE_INVALID"
                    evidence_data = None
                    evidence_value = None

            if outcome == "success" and evidence_data is not None and evidence_value is not None and claim is not None:
                if len(evidence_data.decode("ascii")) > MAX_WORKER_ARGUMENT_CODEPOINTS:
                    outcome, reason_code = "invalid_evidence", "EVIDENCE_PROTOCOL_LIMIT"

            if outcome == "success" and evidence_data is not None and evidence_value is not None and claim is not None:
                checker_artifacts = (*bound_artifacts, ("portfolio_evidence", evidence_data))
                checker_arguments = (*binding.checker_arguments, evidence_data.decode("ascii"))
                checker_request = _worker_request(
                    plan_bytes=planning_result,
                    parent_budget=current_parent,
                    strategy=strategy,
                    binding=binding,
                    phase="checker",
                    arguments=checker_arguments,
                    artifacts=checker_artifacts,
                    executable_sha256=binding.checker_executable_sha256,
                )
                checker_request_sha256 = parse_isolated_worker_request(
                    checker_request
                ).request_sha256
                checker_parent_before = current_parent
                checker_result, current_parent = _supervise_exact(
                    checker_request,
                    planning_result,
                    current_parent,
                    tuple(raw for _, raw in checker_artifacts),
                    prepared.executable_paths[binding.checker_executable_sha256],
                    workspace_root,
                    cancel_event,
                )
                checker_parent_after = current_parent
                outcome, reason_code = _worker_outcome(checker_result, checker=True)
                if outcome == "success":
                    try:
                        checker_output = _worker_stdout(checker_result)
                        decision, certificate_data, _, authority = _checker_envelope(
                            checker_output,
                            evidence_data,
                            evidence_value,
                            claim,
                            strategy,
                            checker,
                            environment_sha,
                            certificate_formats,
                        )
                        checker_validated_output = checker_output
                        outcome, reason_code = _decision_outcome(decision)
                    except ProofSearchPortfolioValidationError:
                        outcome, reason_code = "invalid_evidence", "CERTIFICATE_INVALID"
                        decision = None
                        certificate_data = None
                        authority = "none"

            producer_preimage = _portfolio_worker_preimage(
                producer_result, evidence_data
            )
            producer_identity = _sha(producer_preimage)
            checker_preimage = (
                None
                if checker_result is None
                else _portfolio_worker_preimage(
                    checker_result, checker_validated_output
                )
            )
            checker_identity = (
                None if checker_preimage is None else _sha(checker_preimage)
            )
            selected_transition = _transition(strategy, outcome)
            attempt = _make_attempt(
                attempt_order=len(attempts),
                strategy_sha256=strategy.strategy_sha256,
                producer_result_sha256=producer_identity,
                producer_status=producer_result.status,
                producer_reason_code=producer_result.reason_code,
                evidence=evidence_data,
                checker_result_sha256=checker_identity,
                checker_status="not_started" if checker_result is None else checker_result.status,
                checker_reason_code="NOT_STARTED" if checker_result is None else checker_result.reason_code,
                checker_decision_sha256=None if decision is None else decision.decision_sha256,
                outcome=outcome,
                transition_sha256=selected_transition.transition_sha256,
                parent_before=parent_before,
                parent_after=current_parent,
            )
            attempts.append(attempt)
            if audit_attempts is not None:
                audit_attempts.append(
                    _PortfolioAuditAttempt(
                        attempt_order=attempt.attempt_order,
                        strategy_sha256=strategy.strategy_sha256,
                        producer_request_sha256=producer_result.request_sha256,
                        producer_result_sha256=producer_identity,
                        producer_result_preimage=producer_preimage,
                        producer_status=producer_result.status,
                        producer_reason_code=producer_result.reason_code,
                        producer_parent_before=parent_before,
                        producer_parent_after=producer_parent_after,
                        evidence=evidence_data,
                        checker_request_sha256=checker_request_sha256,
                        checker_result_sha256=checker_identity,
                        checker_result_preimage=checker_preimage,
                        checker_status="not_started"
                        if checker_result is None
                        else checker_result.status,
                        checker_reason_code="NOT_STARTED"
                        if checker_result is None
                        else checker_result.reason_code,
                        checker_parent_before=checker_parent_before,
                        checker_parent_after=checker_parent_after,
                        checker_decision=None
                        if decision is None
                        else _canonical(_decision_mapping(decision)),
                        certificate=certificate_data,
                        outcome=outcome,
                        transition_sha256=selected_transition.transition_sha256,
                    )
                )
            if outcome in _INCONCLUSIVE_OUTCOMES:
                inconclusive.append(_make_inconclusive(attempt, reason_code))

            if selected_transition.action == "fallback":
                current_sha = selected_transition.target_strategy_sha256
                continue
            if outcome == "success":
                if (
                    claim is None
                    or evidence_data is None
                    or certificate_data is None
                    or decision is None
                    or authority not in {"checker_attested", "external_verified"}
                ):
                    _fail("checker", "selection", "successful transition lacks checked artifacts")
                return _make_result(
                    status="succeeded",
                    mathematical_verdict=claim,
                    reason_code="CHECKED_PROOF" if claim == "proved" else "CHECKED_REFUTATION",
                    request_sha256=prepared.request.request_sha256,
                    planning_result_sha256=_sha(planning_result),
                    initial_parent_budget=initial_parent,
                    final_parent_budget=current_parent,
                    attempts=tuple(attempts),
                    inconclusive=tuple(inconclusive),
                    selected_strategy_sha256=strategy.strategy_sha256,
                    selected_evidence=evidence_data,
                    selected_certificate=certificate_data,
                    selected_checker_decision_sha256=decision.decision_sha256,
                    authority_tier="checker_attestation" if authority == "checker_attested" else "external_proof_assistant",
                )
            return _terminal_result(
                transition=selected_transition,
                reason_code=reason_code,
                request_sha256=prepared.request.request_sha256,
                planning_result_sha256=_sha(planning_result),
                initial_parent_budget=initial_parent,
                final_parent_budget=current_parent,
                attempts=tuple(attempts),
                inconclusive=tuple(inconclusive),
            )
        _fail("transition", "planning_result", "portfolio graph ended without a terminal transition")
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        reason = "PORTFOLIO_INPUT_INVALID" if prepared is None else "PORTFOLIO_EXECUTION_INVALID"
        try:
            return _make_result(
                status="invalid",
                mathematical_verdict="none",
                reason_code=reason,
                request_sha256=None if prepared is None else prepared.request.request_sha256,
                planning_result_sha256=None if prepared is None else _sha(planning_result),
                initial_parent_budget=initial_parent,
                final_parent_budget=current_parent,
                attempts=tuple(attempts),
                inconclusive=tuple(inconclusive),
            )
        except Exception:
            return _make_result(
                status="invalid",
                mathematical_verdict="none",
                reason_code=reason,
                request_sha256=None if prepared is None else prepared.request.request_sha256,
                planning_result_sha256=None if prepared is None else _sha(planning_result),
                initial_parent_budget=initial_parent,
                final_parent_budget=current_parent,
            )


def run_portfolio(
    request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    executable_paths: tuple[tuple[str, str], ...],
    workspace_root: str,
    cancel_event: Event | None = None,
) -> ProofSearchPortfolioResult:
    """Run the exact planned graph through sequential isolated producer/checker leases."""
    return _execute_portfolio(
        request,
        planning_result,
        parent_budget,
        descriptors,
        bindings,
        artifacts,
        executable_paths,
        workspace_root,
        cancel_event,
        None,
    )


def _run_portfolio_audited(
    request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    executable_paths: tuple[tuple[str, str], ...],
    workspace_root: str,
    cancel_event: Event | None = None,
) -> tuple[ProofSearchPortfolioResult, tuple[_PortfolioAuditAttempt, ...]]:
    """Execute once and return only allowlisted validated MH-054 observations."""
    captured: list[_PortfolioAuditAttempt] = []
    result = _execute_portfolio(
        request,
        planning_result,
        parent_budget,
        descriptors,
        bindings,
        artifacts,
        executable_paths,
        workspace_root,
        cancel_event,
        captured,
    )
    return result, tuple(captured)


__all__ = [
    "ATTEMPT_SCHEMA",
    "BINDING_SCHEMA",
    "DECISION_SCHEMA",
    "INCONCLUSIVE_SCHEMA",
    "PORTFOLIO_CONTRACT_ID",
    "PORTFOLIO_CONTRACT_SHA256",
    "PREFERENCE_POLICY",
    "ProofSearchPortfolioRequest",
    "ProofSearchPortfolioResult",
    "ProofSearchPortfolioValidationError",
    "PortfolioArtifactBinding",
    "PortfolioAttempt",
    "PortfolioCheckerDecision",
    "PortfolioExecutionBinding",
    "PortfolioInconclusive",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "SCHEMA_SHA256S",
    "make_portfolio_execution_binding",
    "make_proof_search_portfolio_request",
    "parse_portfolio_checker_decision",
    "parse_portfolio_execution_binding",
    "parse_proof_search_portfolio_request",
    "parse_proof_search_portfolio_result",
    "proof_search_portfolio_budget_bytes",
    "proof_search_portfolio_result_bytes",
    "proof_search_portfolio_semantic_bytes",
    "proof_search_portfolio_selected_bytes",
    "run_portfolio",
    "validate_proof_search_portfolio_result",
]
