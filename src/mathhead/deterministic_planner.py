"""Pure deterministic strategy planning over accepted capability routes."""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping, NoReturn, Final

from mathhead.capability_registry import (
    capability_route_result_bytes,
    parse_capability_route_result,
    parse_capability_route_request,
    route_capabilities,
)


CONTRACT_ID: Final = "MH-C-DETERMINISTIC-PLANNER-001"
CONTRACT_SHA256: Final = "72e3c39ea40c599cd709fff590a72bfd096450adbb80689ce934342c3aaaa124"
CAPABILITY_REGISTRY_CONTRACT_SHA256: Final = (
    "52cc70945a4e83115c756e5b0a72724676f0e52a89e56c06a0fa8bd42c0e0413"
)
RESOURCE_BUDGET_CONTRACT_SHA256: Final = (
    "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045"
)
ENGINE_RESULT_CONTRACT_SHA256: Final = (
    "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370"
)
EVIDENCE_CONTRACT_SHA256: Final = (
    "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3"
)
CERTIFICATE_CONTRACT_SHA256: Final = (
    "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740"
)
THEORY_PLUGIN_CONTRACT_SHA256: Final = (
    "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8"
)

POLICY_SCHEMA: Final = "mathhead.planning-policy.v1"
REQUEST_SCHEMA: Final = "mathhead.planning-request.v1"
PREREQUISITE_SCHEMA: Final = "mathhead.planning-prerequisite.v1"
EXPECTATION_SCHEMA: Final = "mathhead.planning-evidence-expectation.v1"
RESOURCE_REQUEST_SCHEMA: Final = "mathhead.planning-resource-request.v1"
TRANSITION_SCHEMA: Final = "mathhead.planning-transition.v1"
STRATEGY_SCHEMA: Final = "mathhead.planning-strategy.v1"
RESULT_SCHEMA: Final = "mathhead.planning-result.v1"

SCHEMA_SHA256S: Final = {
    POLICY_SCHEMA: "fa0855768cb0445ab1f8ae67fe55a3851a500603a5757a9da099fe06a653b8f5",
    REQUEST_SCHEMA: "2d8dff59cec10037f59506102c26f41eca21c0b963c968bcf2366b8dfcbff15a",
    PREREQUISITE_SCHEMA: "54dd128e23ed57fcf3996fae61c221dd918dfee72c9bb0f160927bf62c5a0499",
    EXPECTATION_SCHEMA: "126c85466c7c0bcda1bf7b10f4a9cdeeacfd8597e1e04b24a08f4c2f39ed34ae",
    RESOURCE_REQUEST_SCHEMA: "8f5833b632b99ddf626a7d1fdef03986310636466b34d2cd0633501ca8d94c91",
    TRANSITION_SCHEMA: "2f63a40d420c823e5de9eb7fd4af4385dda801af296524ea0063a111a5dbb3f9",
    STRATEGY_SCHEMA: "ca712e4c5f17b58d476537d4658c35c558841378cf7a084ac53cff026a15e1c8",
    RESULT_SCHEMA: "f2e916f669f028eafca56551897e66371114a01f9aa2502e929d0aae90ff30be",
}

INTEGER_MAXIMUM: Final = 9_007_199_254_740_991
MAX_REQUEST_BYTES: Final = 67_108_864
MAX_ROUTE_BYTES: Final = 1_073_741_824
MAX_DESCRIPTOR_BYTES: Final = 67_108_864
MAX_AGGREGATE_DESCRIPTOR_BYTES: Final = 1_073_741_824
MAX_AGGREGATE_ARTIFACT_BYTES: Final = 1_073_741_824
MAX_DESCRIPTORS: Final = 10_000
MAX_ARTIFACTS: Final = 100_000
MAX_STRATEGIES: Final = 100_000
MAX_DEPENDENCIES: Final = 10_000
MAX_DIAGNOSTIC_CODEPOINTS: Final = 1_024
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_JSON_DEPTH: Final = 128
MAX_JSON_NODES: Final = 8_000_000

RESOURCE_DIMENSIONS: Final = (
    "wall_time_us",
    "cpu_time_us",
    "memory_bytes",
    "solver_calls",
    "generated_objects",
    "proof_bytes",
    "evidence_bytes",
    "output_bytes",
    "diagnostic_bytes",
    "nesting_depth",
)
OUTCOMES: Final = (
    "success",
    "unsupported",
    "exhausted",
    "cancelled",
    "producer_error",
    "ambiguous",
    "truncated",
    "checker_inconclusive",
    "checker_disagreement",
    "verifier_failure",
    "invalid_evidence",
)
RETRY_TERMINALS: Final = {
    "unsupported": "unsupported",
    "producer_error": "failed",
    "ambiguous": "ambiguous",
    "truncated": "truncated",
    "checker_inconclusive": "inconclusive",
    "checker_disagreement": "disagreement",
    "invalid_evidence": "invalid_evidence",
}
STOP_TERMINALS: Final = {
    "success": ("succeed", "succeeded"),
    "exhausted": ("stop", "exhausted"),
    "cancelled": ("stop", "cancelled"),
    "verifier_failure": ("stop", "verifier_failed"),
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_CONTRACT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]*$")
_NAMESPACED = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")


class DeterministicPlannerValidationError(ValueError):
    """Raised by requested strict planner validation boundaries."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        self.kind = kind
        self.path = path
        self.detail = detail
        super().__init__(f"{kind} at {path}: {detail}")


class _Invalid(ValueError):
    pass


class _Exhausted(ValueError):
    pass


class _DuplicateKey(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _FrozenMap:
    entries: tuple[tuple[str, object], ...]


_PUBLIC_VALUES_FINAL = False


class _PlannerValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_VALUES_FINAL:
            raise TypeError("deterministic planner value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class PlanningResourceVector(_PlannerValue):
    wall_time_us: int
    cpu_time_us: int
    memory_bytes: int
    solver_calls: int
    generated_objects: int
    proof_bytes: int
    evidence_bytes: int
    output_bytes: int
    diagnostic_bytes: int
    nesting_depth: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning resource vectors are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class PlanningPolicy(_PlannerValue):
    schema: str
    mode: str
    maximum_strategies: int
    policy_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning policies are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class PlanningRequest(_PlannerValue):
    schema: str
    route_request: bytes
    route_result_sha256: str
    resource_budget_contract_sha256: str
    resource_limits: PlanningResourceVector
    policy: PlanningPolicy
    request_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning requests are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class PlanningPrerequisite(_PlannerValue):
    schema: str
    kind: str
    object_sha256: str
    contract_id: str | None
    artifact_schema: str | None
    prerequisite_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning prerequisites are created only by planning")


@dataclass(frozen=True, slots=True, init=False)
class PlanningEvidenceExpectation(_PlannerValue):
    schema: str
    operation_authority: str
    producer_component_id: str
    checker_component_id: str
    evidence_contract_sha256: str
    certificate_contract_sha256: str
    evidence_format: object | None
    certificate_format: object | None
    independent_check_required: bool
    expectation_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("evidence expectations are created only by planning")


@dataclass(frozen=True, slots=True, init=False)
class PlanningResourceRequest(_PlannerValue):
    schema: str
    estimated_cost: int
    requested: PlanningResourceVector
    saturated_dimensions: tuple[str, ...]
    fits_parent: bool
    resource_request_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("resource requests are created only by planning")


@dataclass(frozen=True, slots=True, init=False)
class PlanningTransition(_PlannerValue):
    schema: str
    outcome: str
    action: str
    target_strategy_sha256: str | None
    terminal_state: str | None
    transition_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning transitions are created only by planning")


@dataclass(frozen=True, slots=True, init=False)
class PlanningStrategy(_PlannerValue):
    schema: str
    plan_order: int
    route_order: int
    candidate_sha256: str
    descriptor_sha256: str
    plugin_id: str
    plugin_version: str
    capability_id: str
    capability_kind: str
    operation: str
    component_id: str
    producer_component_id: str
    checker_component_id: str
    session_head_sha256: str
    session_context_sha256: str
    normalization_result_sha256: str
    obligation_semantic_sha256: str
    fragment_sha256: str
    dependency_descriptor_sha256s: tuple[str, ...]
    effect_kinds: tuple[str, ...]
    replay_mode: str
    priority: int
    estimated_cost: int
    cost_sha256: str
    prerequisites: tuple[PlanningPrerequisite, ...]
    evidence_expectation: PlanningEvidenceExpectation
    resource_request: PlanningResourceRequest
    transitions: tuple[PlanningTransition, ...]
    strategy_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning strategies are created only by planning")


@dataclass(frozen=True, slots=True, init=False)
class PlanningResult(_PlannerValue):
    schema: str
    contract_id: str
    contract_sha256: str
    capability_registry_contract_sha256: str
    resource_budget_contract_sha256: str
    engine_result_contract_sha256: str
    evidence_contract_sha256: str
    certificate_contract_sha256: str
    theory_plugin_contract_sha256: str
    status: str
    reason_code: str
    diagnostic: str
    planning_request_sha256: str | None
    route_result_sha256: str | None
    policy_sha256: str | None
    entry_strategy_sha256: str | None
    strategies: tuple[PlanningStrategy, ...]
    result_sha256: str | None
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("planning results are created only by planning")


_PUBLIC_VALUES_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    instance = object.__new__(cls)
    for item in fields(cls):
        object.__setattr__(instance, item.name, values[item.name])
    return instance


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise DeterministicPlannerValidationError(kind, path, detail)


def _invalid(path: str, detail: str) -> NoReturn:
    raise _Invalid(f"{path}: {detail}")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _validate_tree(value: object) -> None:
    stack: list[tuple[object, int, str]] = [(value, 1, "$")]
    nodes = 0
    while stack:
        item, depth, path = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise _Exhausted("JSON node ceiling exceeded")
        if depth > MAX_JSON_DEPTH:
            raise _Exhausted("JSON nesting ceiling exceeded")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if item < -INTEGER_MAXIMUM or item > INTEGER_MAXIMUM:
                _invalid(path, "integer outside portable range")
            continue
        if type(item) is str:
            if len(item) > MAX_STRING_CODEPOINTS or "\x00" in item:
                _invalid(path, "invalid or oversized string")
            if unicodedata.normalize("NFC", item) != item:
                _invalid(path, "string is not NFC")
            continue
        if type(item) is list:
            for index in range(len(item) - 1, -1, -1):
                stack.append((item[index], depth + 1, f"{path}[{index}]"))
            continue
        if type(item) is dict:
            for key, child in reversed(tuple(item.items())):
                if type(key) is not str:
                    _invalid(path, "mapping key is not text")
                stack.append((child, depth + 1, f"{path}.{key}"))
            continue
        _invalid(path, f"unsupported JSON type {type(item).__name__}")


def _canonical_bytes(value: object, *, maximum: int = MAX_ROUTE_BYTES) -> bytes:
    _validate_tree(value)
    try:
        data = (
            json.dumps(
                value,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        _invalid("$", f"canonical encoding failed: {exc}")
    if len(data) > maximum:
        raise _Exhausted("canonical byte ceiling exceeded")
    return data


def _parse_json(data: bytes, path: str, maximum: int) -> dict[str, object]:
    if type(data) is not bytes:
        _invalid(path, "must be exact bytes")
    if len(data) > maximum:
        raise _Exhausted(f"{path} byte ceiling exceeded")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(_Invalid("floats are forbidden")),
            parse_constant=lambda _value: (_ for _ in ()).throw(_Invalid("constants are forbidden")),
        )
    except _DuplicateKey as exc:
        _invalid(path, f"duplicate key {exc}")
    except (UnicodeError, json.JSONDecodeError) as exc:
        _invalid(path, f"invalid JSON: {exc}")
    if type(value) is not dict:
        _invalid(path, "root must be an object")
    _validate_tree(value)
    if _canonical_bytes(value, maximum=maximum) != data:
        _invalid(path, "bytes are not canonical")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict[str, object]:
    if type(value) is not dict:
        _invalid(path, "expected object")
    keys = set(value)
    if keys != expected:
        _invalid(path, f"fields differ missing={sorted(expected - keys)} unknown={sorted(keys - expected)}")
    return value


def _text(
    value: object,
    path: str,
    *,
    pattern: re.Pattern[str] | None = None,
    maximum: int = 255,
) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        _invalid(path, "invalid text")
    if "\x00" in value or unicodedata.normalize("NFC", value) != value:
        _invalid(path, "text must be NUL-free NFC")
    if pattern is not None and pattern.fullmatch(value) is None:
        _invalid(path, "text does not match the closed grammar")
    return value


def _sha(value: object, path: str) -> str:
    return _text(value, path, pattern=_SHA256, maximum=64)


def _integer(value: object, path: str, *, minimum: int = 0, maximum: int = INTEGER_MAXIMUM) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        _invalid(path, "invalid integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _invalid(path, "expected boolean")
    return value


def _choice(value: object, choices: tuple[str, ...] | set[str], path: str) -> str:
    if type(value) is not str or value not in choices:
        _invalid(path, "unknown closed value")
    return value


def _self_hash(mapping: dict[str, object], field: str) -> str:
    payload = dict(mapping)
    payload[field] = None
    return _digest(_canonical_bytes(payload))


def _freeze(value: object) -> object:
    if type(value) is dict:
        return _FrozenMap(tuple((key, _freeze(item)) for key, item in value.items()))
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if type(value) is _FrozenMap:
        return {key: _thaw(item) for key, item in value.entries}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _resource_vector_from_mapping(value: object, path: str) -> PlanningResourceVector:
    item = _keys(value, set(RESOURCE_DIMENSIONS), path)
    return _make(
        PlanningResourceVector,
        **{name: _integer(item[name], f"{path}.{name}") for name in RESOURCE_DIMENSIONS},
    )


def _resource_vector_mapping(value: PlanningResourceVector) -> dict[str, object]:
    return {name: getattr(value, name) for name in RESOURCE_DIMENSIONS}


def _policy_mapping(value: PlanningPolicy, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "mode": value.mode,
        "maximum_strategies": value.maximum_strategies,
        "policy_sha256": value.policy_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _policy_from_mapping(value: object, path: str = "$") -> PlanningPolicy:
    item = _keys(
        value,
        {"schema", "mode", "maximum_strategies", "policy_sha256", "mathematical_authority"},
        path,
    )
    if item["schema"] != POLICY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "policy schema or authority mismatch")
    mode = _choice(item["mode"], ("registry_order", "deterministic_first"), f"{path}.mode")
    maximum = _integer(item["maximum_strategies"], f"{path}.maximum_strategies", minimum=1, maximum=MAX_STRATEGIES)
    identity = _sha(item["policy_sha256"], f"{path}.policy_sha256")
    if identity != _self_hash(item, "policy_sha256"):
        _invalid(path, "policy identity mismatch")
    return _make(PlanningPolicy, schema=POLICY_SCHEMA, mode=mode, maximum_strategies=maximum, policy_sha256=identity, mathematical_authority=False)


def make_planning_policy(*, mode: str = "registry_order", maximum_strategies: int = MAX_STRATEGIES) -> PlanningPolicy:
    value: dict[str, object] = {
        "schema": POLICY_SCHEMA,
        "mode": mode,
        "maximum_strategies": maximum_strategies,
        "policy_sha256": None,
        "mathematical_authority": False,
    }
    value["policy_sha256"] = _self_hash(value, "policy_sha256")
    try:
        return _policy_from_mapping(value)
    except (_Invalid, _Exhausted) as exc:
        _fail("schema", "$", str(exc))


def planning_policy_bytes(value: PlanningPolicy) -> bytes:
    if type(value) is not PlanningPolicy:
        _fail("type", "$", "expected exact PlanningPolicy")
    try:
        parsed = _policy_from_mapping(_policy_mapping(value))
        if parsed != value:
            _invalid("$", "policy differs from strict reconstruction")
        return _canonical_bytes(_policy_mapping(value), maximum=MAX_REQUEST_BYTES)
    except (_Invalid, _Exhausted, AttributeError, TypeError) as exc:
        _fail("result", "$", str(exc))


def _request_mapping(value: PlanningRequest, *, own_hash: bool = True) -> dict[str, object]:
    route_request = _parse_json(value.route_request, "$.route_request", MAX_REQUEST_BYTES)
    return {
        "schema": value.schema,
        "route_request": route_request,
        "route_result_sha256": value.route_result_sha256,
        "resource_budget_contract_sha256": value.resource_budget_contract_sha256,
        "resource_limits": _resource_vector_mapping(value.resource_limits),
        "policy": _policy_mapping(value.policy),
        "request_sha256": value.request_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _request_from_mapping(value: object, path: str = "$") -> PlanningRequest:
    item = _keys(
        value,
        {"schema", "route_request", "route_result_sha256", "resource_budget_contract_sha256", "resource_limits", "policy", "request_sha256", "mathematical_authority"},
        path,
    )
    if item["schema"] != REQUEST_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "request schema or authority mismatch")
    route_request_bytes = _canonical_bytes(item["route_request"], maximum=MAX_REQUEST_BYTES)
    try:
        parse_capability_route_request(route_request_bytes)
    except Exception as exc:
        if isinstance(exc, (MemoryError, KeyboardInterrupt, SystemExit)):
            raise
        _invalid(f"{path}.route_request", f"invalid capability request: {exc}")
    route_digest = _sha(item["route_result_sha256"], f"{path}.route_result_sha256")
    budget_contract = _sha(item["resource_budget_contract_sha256"], f"{path}.resource_budget_contract_sha256")
    if budget_contract != RESOURCE_BUDGET_CONTRACT_SHA256:
        _invalid(path, "resource budget contract mismatch")
    limits = _resource_vector_from_mapping(item["resource_limits"], f"{path}.resource_limits")
    policy = _policy_from_mapping(item["policy"], f"{path}.policy")
    identity = _sha(item["request_sha256"], f"{path}.request_sha256")
    if identity != _self_hash(item, "request_sha256"):
        _invalid(path, "request identity mismatch")
    return _make(PlanningRequest, schema=REQUEST_SCHEMA, route_request=route_request_bytes, route_result_sha256=route_digest, resource_budget_contract_sha256=budget_contract, resource_limits=limits, policy=policy, request_sha256=identity, mathematical_authority=False)


def make_planning_request(
    *,
    route_request: bytes,
    route_result: bytes,
    resource_limits: Mapping[str, int],
    policy: PlanningPolicy,
) -> bytes:
    if type(route_request) is not bytes or type(route_result) is not bytes:
        _fail("type", "$", "route request and result must be exact bytes")
    if type(policy) is not PlanningPolicy or not isinstance(resource_limits, Mapping):
        _fail("type", "$", "invalid policy or resource limits")
    try:
        parse_capability_route_request(route_request)
        parse_capability_route_result(route_result)
        route_mapping = _parse_json(route_request, "route_request", MAX_REQUEST_BYTES)
        policy_value = _policy_from_mapping(_policy_mapping(policy))
        limits = {name: resource_limits[name] for name in RESOURCE_DIMENSIONS}
        if set(resource_limits) != set(RESOURCE_DIMENSIONS):
            _invalid("resource_limits", "resource dimensions differ")
        value: dict[str, object] = {
            "schema": REQUEST_SCHEMA,
            "route_request": route_mapping,
            "route_result_sha256": _digest(route_result),
            "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256,
            "resource_limits": limits,
            "policy": _policy_mapping(policy_value),
            "request_sha256": None,
            "mathematical_authority": False,
        }
        value["request_sha256"] = _self_hash(value, "request_sha256")
        request_value = _request_from_mapping(value)
        return _canonical_bytes(_request_mapping(request_value), maximum=MAX_REQUEST_BYTES)
    except (KeyError, _Invalid, _Exhausted, ValueError, TypeError, UnicodeError) as exc:
        _fail("request", "$", str(exc))


def parse_planning_request(data: bytes) -> PlanningRequest:
    try:
        return _request_from_mapping(_parse_json(data, "$", MAX_REQUEST_BYTES))
    except (_Invalid, _Exhausted, AttributeError, KeyError, TypeError) as exc:
        _fail("request", "$", str(exc))


def _prerequisite_mapping(value: PlanningPrerequisite, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "kind": value.kind,
        "object_sha256": value.object_sha256,
        "contract_id": value.contract_id,
        "artifact_schema": value.artifact_schema,
        "prerequisite_sha256": value.prerequisite_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _prerequisite_from_mapping(value: object, path: str) -> PlanningPrerequisite:
    item = _keys(value, {"schema", "kind", "object_sha256", "contract_id", "artifact_schema", "prerequisite_sha256", "mathematical_authority"}, path)
    if item["schema"] != PREREQUISITE_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "prerequisite schema or authority mismatch")
    kind = _choice(item["kind"], ("route", "session_head", "context", "normalization", "obligation", "contract", "descriptor_dependency"), f"{path}.kind")
    object_sha = _sha(item["object_sha256"], f"{path}.object_sha256")
    contract_id = None if item["contract_id"] is None else _text(item["contract_id"], f"{path}.contract_id", pattern=_CONTRACT_ID, maximum=128)
    artifact_schema = None if item["artifact_schema"] is None else _text(item["artifact_schema"], f"{path}.artifact_schema", pattern=_NAMESPACED, maximum=255)
    identity = _sha(item["prerequisite_sha256"], f"{path}.prerequisite_sha256")
    if identity != _self_hash(item, "prerequisite_sha256"):
        _invalid(path, "prerequisite identity mismatch")
    if (kind == "contract") != (contract_id is not None):
        _invalid(path, "contract identity presence differs from kind")
    return _make(PlanningPrerequisite, schema=PREREQUISITE_SCHEMA, kind=kind, object_sha256=object_sha, contract_id=contract_id, artifact_schema=artifact_schema, prerequisite_sha256=identity, mathematical_authority=False)


def _make_prerequisite(kind: str, object_sha256: str, *, contract_id: str | None = None, artifact_schema: str | None = None) -> PlanningPrerequisite:
    value: dict[str, object] = {"schema": PREREQUISITE_SCHEMA, "kind": kind, "object_sha256": object_sha256, "contract_id": contract_id, "artifact_schema": artifact_schema, "prerequisite_sha256": None, "mathematical_authority": False}
    value["prerequisite_sha256"] = _self_hash(value, "prerequisite_sha256")
    return _prerequisite_from_mapping(value, "prerequisite")


def _format(value: object, path: str) -> object | None:
    if value is None:
        return None
    item = _keys(value, {"format_id", "major", "minor", "required_features"}, path)
    format_id = _text(item["format_id"], f"{path}.format_id", pattern=_NAMESPACED)
    major = _integer(item["major"], f"{path}.major")
    minor = _integer(item["minor"], f"{path}.minor")
    raw_features = item["required_features"]
    if type(raw_features) is not list or len(raw_features) > 100_000:
        _invalid(path, "invalid format feature set")
    features = tuple(_text(entry, f"{path}.required_features[{index}]", pattern=_NAMESPACED) for index, entry in enumerate(raw_features))
    if features != tuple(sorted(set(features))):
        _invalid(path, "format features are not sorted unique")
    return _freeze({"format_id": format_id, "major": major, "minor": minor, "required_features": list(features)})


def _expectation_mapping(value: PlanningEvidenceExpectation, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "operation_authority": value.operation_authority, "producer_component_id": value.producer_component_id, "checker_component_id": value.checker_component_id, "evidence_contract_sha256": value.evidence_contract_sha256, "certificate_contract_sha256": value.certificate_contract_sha256, "evidence_format": _thaw(value.evidence_format), "certificate_format": _thaw(value.certificate_format), "independent_check_required": value.independent_check_required, "expectation_sha256": value.expectation_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _expectation_from_mapping(value: object, path: str) -> PlanningEvidenceExpectation:
    item = _keys(value, {"schema", "operation_authority", "producer_component_id", "checker_component_id", "evidence_contract_sha256", "certificate_contract_sha256", "evidence_format", "certificate_format", "independent_check_required", "expectation_sha256", "mathematical_authority"}, path)
    if item["schema"] != EXPECTATION_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "expectation schema or authority mismatch")
    authority = _choice(item["operation_authority"], ("none", "producer_report", "checker_attestation"), f"{path}.operation_authority")
    producer = _text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64)
    checker = _text(item["checker_component_id"], f"{path}.checker_component_id", pattern=_ID, maximum=64)
    if producer == checker:
        _invalid(path, "producer and checker must be distinct")
    evidence_contract = _sha(item["evidence_contract_sha256"], f"{path}.evidence_contract_sha256")
    certificate_contract = _sha(item["certificate_contract_sha256"], f"{path}.certificate_contract_sha256")
    if evidence_contract != EVIDENCE_CONTRACT_SHA256 or certificate_contract != CERTIFICATE_CONTRACT_SHA256:
        _invalid(path, "evidence contract identity mismatch")
    evidence_format = _format(item["evidence_format"], f"{path}.evidence_format")
    certificate_format = _format(item["certificate_format"], f"{path}.certificate_format")
    independent = _boolean(item["independent_check_required"], f"{path}.independent_check_required")
    if independent != (authority == "producer_report"):
        _invalid(path, "independent check requirement differs from operation authority")
    identity = _sha(item["expectation_sha256"], f"{path}.expectation_sha256")
    if identity != _self_hash(item, "expectation_sha256"):
        _invalid(path, "expectation identity mismatch")
    return _make(PlanningEvidenceExpectation, schema=EXPECTATION_SCHEMA, operation_authority=authority, producer_component_id=producer, checker_component_id=checker, evidence_contract_sha256=evidence_contract, certificate_contract_sha256=certificate_contract, evidence_format=evidence_format, certificate_format=certificate_format, independent_check_required=independent, expectation_sha256=identity, mathematical_authority=False)


def _resource_request_mapping(value: PlanningResourceRequest, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "estimated_cost": value.estimated_cost, "requested": _resource_vector_mapping(value.requested), "saturated_dimensions": list(value.saturated_dimensions), "fits_parent": value.fits_parent, "resource_request_sha256": value.resource_request_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _resource_request_from_mapping(value: object, path: str) -> PlanningResourceRequest:
    item = _keys(value, {"schema", "estimated_cost", "requested", "saturated_dimensions", "fits_parent", "resource_request_sha256", "mathematical_authority"}, path)
    if item["schema"] != RESOURCE_REQUEST_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "resource request schema or authority mismatch")
    cost = _integer(item["estimated_cost"], f"{path}.estimated_cost")
    requested = _resource_vector_from_mapping(item["requested"], f"{path}.requested")
    raw_saturated = item["saturated_dimensions"]
    if type(raw_saturated) is not list or len(raw_saturated) > len(RESOURCE_DIMENSIONS):
        _invalid(path, "invalid saturated dimension set")
    saturated = tuple(_choice(entry, RESOURCE_DIMENSIONS, f"{path}.saturated_dimensions[{index}]") for index, entry in enumerate(raw_saturated))
    if saturated != tuple(name for name in RESOURCE_DIMENSIONS if name in set(saturated)) or len(saturated) != len(set(saturated)):
        _invalid(path, "saturated dimensions are not in canonical order")
    fits = _boolean(item["fits_parent"], f"{path}.fits_parent")
    identity = _sha(item["resource_request_sha256"], f"{path}.resource_request_sha256")
    if identity != _self_hash(item, "resource_request_sha256"):
        _invalid(path, "resource request identity mismatch")
    return _make(PlanningResourceRequest, schema=RESOURCE_REQUEST_SCHEMA, estimated_cost=cost, requested=requested, saturated_dimensions=saturated, fits_parent=fits, resource_request_sha256=identity, mathematical_authority=False)


def _sat_mul(value: int, factor: int) -> tuple[int, bool]:
    if value > INTEGER_MAXIMUM // factor:
        return INTEGER_MAXIMUM, True
    return value * factor, False


def _sat_add(value: int, increment: int) -> tuple[int, bool]:
    if value > INTEGER_MAXIMUM - increment:
        return INTEGER_MAXIMUM, True
    return value + increment, False


def _expected_resource_terms(cost: int, effects: tuple[str, ...]) -> dict[str, int]:
    c_plus_one, _ = _sat_add(cost, 1)
    wall, _ = _sat_mul(cost, 1_000)
    cpu, _ = _sat_mul(cost, 1_000)
    memory, _ = _sat_mul(c_plus_one, 1_024)
    proof, _ = _sat_mul(cost, 16)
    evidence, _ = _sat_mul(cost, 16)
    output, _ = _sat_mul(cost, 16)
    diagnostic, _ = _sat_mul(cost, 4)
    return {
        "wall_time_us": wall,
        "cpu_time_us": cpu,
        "memory_bytes": memory,
        "solver_calls": 1 if "solver" in effects else 0,
        "generated_objects": cost,
        "proof_bytes": proof,
        "evidence_bytes": evidence,
        "output_bytes": output,
        "diagnostic_bytes": min(diagnostic, 4_096),
        "nesting_depth": 1,
    }


def _make_resource_request(cost: int, fragment: dict[str, object], effects: tuple[str, ...], parent: PlanningResourceVector) -> PlanningResourceRequest:
    c_plus_one, add_sat = _sat_add(cost, 1)
    wall, wall_sat = _sat_mul(cost, 1_000)
    cpu, cpu_sat = _sat_mul(cost, 1_000)
    memory, memory_mul_sat = _sat_mul(c_plus_one, 1_024)
    proof, proof_sat = _sat_mul(cost, 16)
    evidence, evidence_sat = _sat_mul(cost, 16)
    output, output_sat = _sat_mul(cost, 16)
    diagnostic_raw, diagnostic_sat = _sat_mul(cost, 4)
    nesting, nesting_sat = _sat_add(_integer(fragment["quantifier_depth"], "fragment.quantifier_depth"), 1)
    values = {"wall_time_us": wall, "cpu_time_us": cpu, "memory_bytes": memory, "solver_calls": 1 if "solver" in effects else 0, "generated_objects": cost, "proof_bytes": proof, "evidence_bytes": evidence, "output_bytes": output, "diagnostic_bytes": min(diagnostic_raw, 4_096), "nesting_depth": nesting}
    saturation_flags = {"wall_time_us": wall_sat, "cpu_time_us": cpu_sat, "memory_bytes": add_sat or memory_mul_sat, "solver_calls": False, "generated_objects": False, "proof_bytes": proof_sat, "evidence_bytes": evidence_sat, "output_bytes": output_sat, "diagnostic_bytes": diagnostic_sat, "nesting_depth": nesting_sat}
    saturated = tuple(name for name in RESOURCE_DIMENSIONS if saturation_flags[name])
    vector = _resource_vector_from_mapping(values, "resource_request.requested")
    fits = all(getattr(vector, name) <= getattr(parent, name) for name in RESOURCE_DIMENSIONS)
    mapping: dict[str, object] = {"schema": RESOURCE_REQUEST_SCHEMA, "estimated_cost": cost, "requested": values, "saturated_dimensions": list(saturated), "fits_parent": fits, "resource_request_sha256": None, "mathematical_authority": False}
    mapping["resource_request_sha256"] = _self_hash(mapping, "resource_request_sha256")
    return _resource_request_from_mapping(mapping, "resource_request")


def _transition_mapping(value: PlanningTransition, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "outcome": value.outcome, "action": value.action, "target_strategy_sha256": value.target_strategy_sha256, "terminal_state": value.terminal_state, "transition_sha256": value.transition_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _transition_from_mapping(value: object, path: str) -> PlanningTransition:
    item = _keys(value, {"schema", "outcome", "action", "target_strategy_sha256", "terminal_state", "transition_sha256", "mathematical_authority"}, path)
    if item["schema"] != TRANSITION_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "transition schema or authority mismatch")
    outcome = _choice(item["outcome"], OUTCOMES, f"{path}.outcome")
    action = _choice(item["action"], ("succeed", "fallback", "stop"), f"{path}.action")
    target = None if item["target_strategy_sha256"] is None else _sha(item["target_strategy_sha256"], f"{path}.target_strategy_sha256")
    terminals = ("succeeded", "unsupported", "exhausted", "cancelled", "failed", "ambiguous", "truncated", "inconclusive", "disagreement", "verifier_failed", "invalid_evidence")
    terminal = None if item["terminal_state"] is None else _choice(item["terminal_state"], terminals, f"{path}.terminal_state")
    if action == "fallback":
        if target is None or terminal is not None or outcome not in RETRY_TERMINALS:
            _invalid(path, "invalid fallback transition")
    else:
        if target is not None or terminal is None:
            _invalid(path, "invalid terminal transition")
        expected = STOP_TERMINALS.get(outcome)
        if expected is not None and (action, terminal) != expected:
            _invalid(path, "fixed terminal transition mismatch")
        if outcome in RETRY_TERMINALS and (action != "stop" or terminal != RETRY_TERMINALS[outcome]):
            _invalid(path, "retry terminal mismatch")
    identity = _sha(item["transition_sha256"], f"{path}.transition_sha256")
    if identity != _self_hash(item, "transition_sha256"):
        _invalid(path, "transition identity mismatch")
    return _make(PlanningTransition, schema=TRANSITION_SCHEMA, outcome=outcome, action=action, target_strategy_sha256=target, terminal_state=terminal, transition_sha256=identity, mathematical_authority=False)


def _make_transitions(next_strategy_sha256: str | None) -> tuple[PlanningTransition, ...]:
    result: list[PlanningTransition] = []
    for outcome in OUTCOMES:
        if outcome in STOP_TERMINALS:
            action, terminal = STOP_TERMINALS[outcome]
            target = None
        elif next_strategy_sha256 is not None:
            action, terminal, target = "fallback", None, next_strategy_sha256
        else:
            action, terminal, target = "stop", RETRY_TERMINALS[outcome], None
        mapping: dict[str, object] = {"schema": TRANSITION_SCHEMA, "outcome": outcome, "action": action, "target_strategy_sha256": target, "terminal_state": terminal, "transition_sha256": None, "mathematical_authority": False}
        mapping["transition_sha256"] = _self_hash(mapping, "transition_sha256")
        result.append(_transition_from_mapping(mapping, f"transition.{outcome}"))
    return tuple(result)


def _strategy_mapping(value: PlanningStrategy, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "plan_order": value.plan_order, "route_order": value.route_order, "candidate_sha256": value.candidate_sha256, "descriptor_sha256": value.descriptor_sha256, "plugin_id": value.plugin_id, "plugin_version": value.plugin_version, "capability_id": value.capability_id, "capability_kind": value.capability_kind, "operation": value.operation, "component_id": value.component_id, "producer_component_id": value.producer_component_id, "checker_component_id": value.checker_component_id, "session_head_sha256": value.session_head_sha256, "session_context_sha256": value.session_context_sha256, "normalization_result_sha256": value.normalization_result_sha256, "obligation_semantic_sha256": value.obligation_semantic_sha256, "fragment_sha256": value.fragment_sha256, "dependency_descriptor_sha256s": list(value.dependency_descriptor_sha256s), "effect_kinds": list(value.effect_kinds), "replay_mode": value.replay_mode, "priority": value.priority, "estimated_cost": value.estimated_cost, "cost_sha256": value.cost_sha256, "prerequisites": [_prerequisite_mapping(item) for item in value.prerequisites], "evidence_expectation": _expectation_mapping(value.evidence_expectation), "resource_request": _resource_request_mapping(value.resource_request), "transitions": [_transition_mapping(item) for item in value.transitions], "strategy_sha256": value.strategy_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _string_tuple(value: object, path: str, *, choices: tuple[str, ...] | None = None, maximum: int = 100_000) -> tuple[str, ...]:
    if type(value) is not list or len(value) > maximum:
        _invalid(path, "invalid string array")
    result = tuple(_text(item, f"{path}[{index}]", maximum=255) for index, item in enumerate(value))
    if result != tuple(sorted(set(result))):
        _invalid(path, "array is not sorted unique")
    if choices is not None and any(item not in choices for item in result):
        _invalid(path, "array contains unknown value")
    return result


def _strategy_from_mapping(value: object, path: str) -> PlanningStrategy:
    expected = {"schema", "plan_order", "route_order", "candidate_sha256", "descriptor_sha256", "plugin_id", "plugin_version", "capability_id", "capability_kind", "operation", "component_id", "producer_component_id", "checker_component_id", "session_head_sha256", "session_context_sha256", "normalization_result_sha256", "obligation_semantic_sha256", "fragment_sha256", "dependency_descriptor_sha256s", "effect_kinds", "replay_mode", "priority", "estimated_cost", "cost_sha256", "prerequisites", "evidence_expectation", "resource_request", "transitions", "strategy_sha256", "mathematical_authority"}
    item = _keys(value, expected, path)
    if item["schema"] != STRATEGY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "strategy schema or authority mismatch")
    raw_prerequisites = item["prerequisites"]
    raw_transitions = item["transitions"]
    if type(raw_prerequisites) is not list or not 6 <= len(raw_prerequisites) <= 100_020:
        _invalid(path, "invalid prerequisite array")
    if type(raw_transitions) is not list or len(raw_transitions) != len(OUTCOMES):
        _invalid(path, "invalid transition array")
    prerequisites = tuple(_prerequisite_from_mapping(entry, f"{path}.prerequisites[{index}]") for index, entry in enumerate(raw_prerequisites))
    transitions = tuple(_transition_from_mapping(entry, f"{path}.transitions[{index}]") for index, entry in enumerate(raw_transitions))
    if tuple(entry.outcome for entry in transitions) != OUTCOMES:
        _invalid(path, "transition outcomes are not complete and ordered")
    identity = _sha(item["strategy_sha256"], f"{path}.strategy_sha256")
    if identity != _self_hash(item, "strategy_sha256"):
        _invalid(path, "strategy identity mismatch")
    dependencies = _string_tuple(item["dependency_descriptor_sha256s"], f"{path}.dependency_descriptor_sha256s", maximum=MAX_DEPENDENCIES)
    if any(_SHA256.fullmatch(entry) is None for entry in dependencies):
        _invalid(path, "invalid dependency digest")
    effects = _string_tuple(item["effect_kinds"], f"{path}.effect_kinds", choices=("environment", "filesystem", "network", "process", "solver"), maximum=5)
    values = {
        "schema": STRATEGY_SCHEMA,
        "plan_order": _integer(item["plan_order"], f"{path}.plan_order", maximum=MAX_STRATEGIES - 1),
        "route_order": _integer(item["route_order"], f"{path}.route_order", maximum=999_999),
        "candidate_sha256": _sha(item["candidate_sha256"], f"{path}.candidate_sha256"),
        "descriptor_sha256": _sha(item["descriptor_sha256"], f"{path}.descriptor_sha256"),
        "plugin_id": _text(item["plugin_id"], f"{path}.plugin_id", pattern=_NAMESPACED),
        "plugin_version": _text(item["plugin_version"], f"{path}.plugin_version", pattern=_SEMVER, maximum=64),
        "capability_id": _text(item["capability_id"], f"{path}.capability_id", pattern=_ID, maximum=64),
        "capability_kind": _choice(item["capability_kind"], ("construction", "decision", "explanation", "verification"), f"{path}.capability_kind"),
        "operation": _choice(item["operation"], ("plan_cost", "solve", "check", "explain"), f"{path}.operation"),
        "component_id": _text(item["component_id"], f"{path}.component_id", pattern=_ID, maximum=64),
        "producer_component_id": _text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64),
        "checker_component_id": _text(item["checker_component_id"], f"{path}.checker_component_id", pattern=_ID, maximum=64),
        "session_head_sha256": _sha(item["session_head_sha256"], f"{path}.session_head_sha256"),
        "session_context_sha256": _sha(item["session_context_sha256"], f"{path}.session_context_sha256"),
        "normalization_result_sha256": _sha(item["normalization_result_sha256"], f"{path}.normalization_result_sha256"),
        "obligation_semantic_sha256": _sha(item["obligation_semantic_sha256"], f"{path}.obligation_semantic_sha256"),
        "fragment_sha256": _sha(item["fragment_sha256"], f"{path}.fragment_sha256"),
        "dependency_descriptor_sha256s": dependencies,
        "effect_kinds": effects,
        "replay_mode": _choice(item["replay_mode"], ("deterministic", "seeded", "recorded"), f"{path}.replay_mode"),
        "priority": _integer(item["priority"], f"{path}.priority"),
        "estimated_cost": _integer(item["estimated_cost"], f"{path}.estimated_cost"),
        "cost_sha256": _sha(item["cost_sha256"], f"{path}.cost_sha256"),
        "prerequisites": prerequisites,
        "evidence_expectation": _expectation_from_mapping(item["evidence_expectation"], f"{path}.evidence_expectation"),
        "resource_request": _resource_request_from_mapping(item["resource_request"], f"{path}.resource_request"),
        "transitions": transitions,
        "strategy_sha256": identity,
        "mathematical_authority": False,
    }
    if values["estimated_cost"] != values["resource_request"].estimated_cost or not values["resource_request"].fits_parent:
        _invalid(path, "strategy resource request mismatch")
    if (
        values["evidence_expectation"].producer_component_id
        != values["producer_component_id"]
        or values["evidence_expectation"].checker_component_id
        != values["checker_component_id"]
    ):
        _invalid(path, "evidence expectation component binding mismatch")
    expected_resource = _expected_resource_terms(
        values["estimated_cost"], values["effect_kinds"]
    )
    for name, expected_value in expected_resource.items():
        if name != "nesting_depth" and (
            getattr(values["resource_request"].requested, name) != expected_value
        ):
            _invalid(path, f"resource term {name} mismatch")
    if values["resource_request"].requested.nesting_depth < 1:
        _invalid(path, "resource nesting depth is zero")
    prerequisite_kinds = tuple(item.kind for item in prerequisites)
    if prerequisite_kinds[:5] != (
        "route",
        "session_head",
        "context",
        "normalization",
        "obligation",
    ):
        _invalid(path, "base prerequisite order mismatch")
    contract_prerequisites = tuple(
        item for item in prerequisites[5:] if item.kind == "contract"
    )
    dependency_prerequisites = tuple(
        item for item in prerequisites[5:] if item.kind == "descriptor_dependency"
    )
    if len(contract_prerequisites) + len(dependency_prerequisites) != len(prerequisites) - 5:
        _invalid(path, "unknown prerequisite suffix kind")
    contract_order = tuple(
        (item.contract_id, item.object_sha256, item.artifact_schema)
        for item in contract_prerequisites
    )
    if contract_order != tuple(
        sorted(
            contract_order,
            key=lambda item: (item[0] or "", item[1], item[2] or ""),
        )
    ):
        _invalid(path, "contract prerequisites are not canonically ordered")
    if tuple(item.object_sha256 for item in dependency_prerequisites) != dependencies:
        _invalid(path, "dependency prerequisites differ from candidate closure")
    if (
        prerequisites[1].object_sha256 != values["session_head_sha256"]
        or prerequisites[2].object_sha256 != values["session_context_sha256"]
        or prerequisites[3].object_sha256 != values["normalization_result_sha256"]
    ):
        _invalid(path, "session prerequisite binding mismatch")
    return _make(PlanningStrategy, **values)


def _result_mapping(value: PlanningResult, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "contract_id": value.contract_id, "contract_sha256": value.contract_sha256, "capability_registry_contract_sha256": value.capability_registry_contract_sha256, "resource_budget_contract_sha256": value.resource_budget_contract_sha256, "engine_result_contract_sha256": value.engine_result_contract_sha256, "evidence_contract_sha256": value.evidence_contract_sha256, "certificate_contract_sha256": value.certificate_contract_sha256, "theory_plugin_contract_sha256": value.theory_plugin_contract_sha256, "status": value.status, "reason_code": value.reason_code, "diagnostic": value.diagnostic, "planning_request_sha256": value.planning_request_sha256, "route_result_sha256": value.route_result_sha256, "policy_sha256": value.policy_sha256, "entry_strategy_sha256": value.entry_strategy_sha256, "strategies": [_strategy_mapping(item) for item in value.strategies], "result_sha256": value.result_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _validate_graph(strategies: tuple[PlanningStrategy, ...], entry: str | None) -> None:
    if not strategies:
        if entry is not None:
            _invalid("$.entry_strategy_sha256", "empty graph has an entry")
        return
    if entry != strategies[0].strategy_sha256:
        _invalid("$.entry_strategy_sha256", "entry is not the first strategy")
    identities = tuple(item.strategy_sha256 for item in strategies)
    if len(identities) != len(set(identities)):
        _invalid("$.strategies", "duplicate strategy identity")
    candidates = tuple(item.candidate_sha256 for item in strategies)
    if len(candidates) != len(set(candidates)):
        _invalid("$.strategies", "duplicate candidate use")
    for index, strategy in enumerate(strategies):
        if strategy.plan_order != index:
            _invalid(f"$.strategies[{index}]", "plan order mismatch")
        expected_target = identities[index + 1] if index + 1 < len(strategies) else None
        for transition in strategy.transitions:
            if transition.outcome in RETRY_TERMINALS:
                if expected_target is None:
                    if transition.action != "stop" or transition.terminal_state != RETRY_TERMINALS[transition.outcome]:
                        _invalid(f"$.strategies[{index}]", "final retry transition mismatch")
                elif transition.action != "fallback" or transition.target_strategy_sha256 != expected_target:
                    _invalid(f"$.strategies[{index}]", "fallback does not target exact next strategy")
            elif (transition.action, transition.terminal_state) != STOP_TERMINALS[transition.outcome]:
                _invalid(f"$.strategies[{index}]", "nonretry transition mismatch")


def _result_from_mapping(value: object) -> PlanningResult:
    expected = {"schema", "contract_id", "contract_sha256", "capability_registry_contract_sha256", "resource_budget_contract_sha256", "engine_result_contract_sha256", "evidence_contract_sha256", "certificate_contract_sha256", "theory_plugin_contract_sha256", "status", "reason_code", "diagnostic", "planning_request_sha256", "route_result_sha256", "policy_sha256", "entry_strategy_sha256", "strategies", "result_sha256", "mathematical_authority"}
    item = _keys(value, expected, "$")
    constants = {"schema": RESULT_SCHEMA, "contract_id": CONTRACT_ID, "contract_sha256": CONTRACT_SHA256, "capability_registry_contract_sha256": CAPABILITY_REGISTRY_CONTRACT_SHA256, "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256, "engine_result_contract_sha256": ENGINE_RESULT_CONTRACT_SHA256, "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256, "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256, "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256, "mathematical_authority": False}
    if any(item[name] != expected_value for name, expected_value in constants.items()):
        _invalid("$", "result contract, schema, or authority mismatch")
    status = _choice(item["status"], ("planned", "unsupported", "ambiguous", "invalid", "exhausted"), "$.status")
    reason = _text(item["reason_code"], "$.reason_code", pattern=_REASON, maximum=64)
    diagnostic = item["diagnostic"]
    if type(diagnostic) is not str or len(diagnostic) > MAX_DIAGNOSTIC_CODEPOINTS or "\x00" in diagnostic or unicodedata.normalize("NFC", diagnostic) != diagnostic:
        _invalid("$.diagnostic", "invalid diagnostic")
    request_sha = None if item["planning_request_sha256"] is None else _sha(item["planning_request_sha256"], "$.planning_request_sha256")
    route_sha = None if item["route_result_sha256"] is None else _sha(item["route_result_sha256"], "$.route_result_sha256")
    policy_sha = None if item["policy_sha256"] is None else _sha(item["policy_sha256"], "$.policy_sha256")
    entry = None if item["entry_strategy_sha256"] is None else _sha(item["entry_strategy_sha256"], "$.entry_strategy_sha256")
    raw_strategies = item["strategies"]
    if type(raw_strategies) is not list or len(raw_strategies) > MAX_STRATEGIES:
        _invalid("$.strategies", "invalid strategy array")
    strategies = tuple(_strategy_from_mapping(strategy, f"$.strategies[{index}]") for index, strategy in enumerate(raw_strategies))
    identity = None if item["result_sha256"] is None else _sha(item["result_sha256"], "$.result_sha256")
    if status == "planned":
        if None in (request_sha, route_sha, policy_sha, entry, identity) or not strategies:
            _invalid("$", "planned result is incomplete")
    elif status in {"unsupported", "ambiguous"}:
        if None in (request_sha, route_sha, policy_sha, identity) or entry is not None or strategies:
            _invalid("$", "nonplanned routed result shape mismatch")
    elif any(value is not None for value in (request_sha, route_sha, policy_sha, entry, identity)) or strategies:
        _invalid("$", "invalid or exhausted result leaked partial state")
    if identity is not None and identity != _self_hash(item, "result_sha256"):
        _invalid("$", "result identity mismatch")
    _validate_graph(strategies, entry)
    if route_sha is not None:
        for index, strategy in enumerate(strategies):
            if strategy.prerequisites[0].object_sha256 != route_sha:
                _invalid(
                    f"$.strategies[{index}]", "route prerequisite binding mismatch"
                )
    return _make(PlanningResult, **constants, status=status, reason_code=reason, diagnostic=diagnostic, planning_request_sha256=request_sha, route_result_sha256=route_sha, policy_sha256=policy_sha, entry_strategy_sha256=entry, strategies=strategies, result_sha256=identity)


def _make_result(*, status: str, reason_code: str, diagnostic: str = "", request: PlanningRequest | None = None, strategies: tuple[PlanningStrategy, ...] = ()) -> PlanningResult:
    diagnostic = unicodedata.normalize("NFC", diagnostic.replace("\x00", "\ufffd"))[:MAX_DIAGNOSTIC_CODEPOINTS]
    bound = status in {"planned", "unsupported", "ambiguous"} and request is not None
    base: dict[str, object] = {"schema": RESULT_SCHEMA, "contract_id": CONTRACT_ID, "contract_sha256": CONTRACT_SHA256, "capability_registry_contract_sha256": CAPABILITY_REGISTRY_CONTRACT_SHA256, "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256, "engine_result_contract_sha256": ENGINE_RESULT_CONTRACT_SHA256, "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256, "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256, "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256, "status": status, "reason_code": reason_code, "diagnostic": diagnostic, "planning_request_sha256": request.request_sha256 if bound else None, "route_result_sha256": request.route_result_sha256 if bound else None, "policy_sha256": request.policy.policy_sha256 if bound else None, "entry_strategy_sha256": strategies[0].strategy_sha256 if status == "planned" and strategies else None, "strategies": strategies if status == "planned" else (), "result_sha256": None, "mathematical_authority": False}
    provisional = _make(PlanningResult, **base)
    if bound:
        base["result_sha256"] = _digest(_canonical_bytes(_result_mapping(provisional, own_hash=False)))
    result = _make(PlanningResult, **base)
    _result_from_mapping(_result_mapping(result))
    return result


def _descriptor_inputs(descriptors: tuple[bytes, ...]) -> dict[str, dict[str, object]]:
    if type(descriptors) is not tuple or len(descriptors) > MAX_DESCRIPTORS:
        _invalid("descriptors", "invalid descriptor tuple")
    total = 0
    result: dict[str, dict[str, object]] = {}
    for index, data in enumerate(descriptors):
        if type(data) is not bytes:
            _invalid(f"descriptors[{index}]", "must be exact bytes")
        total += len(data)
        if len(data) > MAX_DESCRIPTOR_BYTES or total > MAX_AGGREGATE_DESCRIPTOR_BYTES:
            raise _Exhausted("descriptor byte ceiling exceeded")
        mapping = _parse_json(data, f"descriptors[{index}]", MAX_DESCRIPTOR_BYTES)
        digest = _digest(data)
        if digest in result and result[digest] != mapping:
            _invalid("descriptors", "descriptor digest collision")
        result[digest] = mapping
    return result


def _check_artifact_tuple(artifacts: tuple[bytes, ...]) -> None:
    if type(artifacts) is not tuple or len(artifacts) > MAX_ARTIFACTS:
        _invalid("artifacts", "invalid artifact tuple")
    total = 0
    for index, data in enumerate(artifacts):
        if type(data) is not bytes:
            _invalid(f"artifacts[{index}]", "must be exact bytes")
        total += len(data)
        if total > MAX_AGGREGATE_ARTIFACT_BYTES:
            raise _Exhausted("artifact byte ceiling exceeded")


def _find_descriptor_parts(descriptor: dict[str, object], candidate: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, object], dict[str, object]]:
    capabilities = descriptor.get("capabilities")
    operations = descriptor.get("operations")
    components = descriptor.get("components")
    compatibility = descriptor.get("compatibility")
    if type(capabilities) is not list or type(operations) is not list or type(components) is not dict or type(compatibility) is not dict:
        _invalid("descriptor", "required descriptor sections missing")
    matching_capabilities = [entry for entry in capabilities if type(entry) is dict and entry.get("capability_id") == candidate["capability_id"]]
    matching_operations = [entry for entry in operations if type(entry) is dict and entry.get("operation") == candidate["operation"]]
    if len(matching_capabilities) != 1 or len(matching_operations) != 1:
        _invalid("descriptor", "candidate capability or operation is not unique")
    return matching_capabilities[0], matching_operations[0], components, compatibility


def _candidate_prerequisites(candidate: dict[str, object], descriptor: dict[str, object], operation: dict[str, object], components: dict[str, object], compatibility: dict[str, object], request_mapping: dict[str, object], route_digest: str) -> tuple[PlanningPrerequisite, ...]:
    result = [
        _make_prerequisite("route", route_digest),
        _make_prerequisite("session_head", _sha(candidate["session_head_sha256"], "candidate.session_head_sha256")),
        _make_prerequisite("context", _sha(candidate["session_context_sha256"], "candidate.session_context_sha256"), artifact_schema="mathhead.theory-context.v1"),
        _make_prerequisite("normalization", _sha(candidate["normalization_result_sha256"], "candidate.normalization_result_sha256"), artifact_schema="mathhead.canonical-normalization-result.v1"),
        _make_prerequisite("obligation", _sha(request_mapping["obligation_artifact_sha256"], "route_request.obligation_artifact_sha256"), artifact_schema="mathhead.canonical-obligation.v1"),
    ]
    raw_contracts = compatibility.get("contracts")
    if type(raw_contracts) is not list:
        _invalid("descriptor.compatibility.contracts", "missing contract array")
    contracts: dict[str, tuple[str, str | None]] = {}
    for entry in raw_contracts:
        if type(entry) is not dict:
            _invalid("descriptor.compatibility.contracts", "invalid contract reference")
        contract_id = _text(entry.get("contract_id"), "contract.contract_id", pattern=_CONTRACT_ID, maximum=128)
        contracts[contract_id] = (_sha(entry.get("sha256"), "contract.sha256"), _text(entry.get("schema"), "contract.schema", pattern=_NAMESPACED))
    required_ids: set[str] = set()
    for field_name in ("request_contract_ids", "response_contract_ids"):
        raw = operation.get(field_name)
        if type(raw) is not list:
            _invalid(f"operation.{field_name}", "invalid contract ID set")
        required_ids.update(_text(entry, f"operation.{field_name}", pattern=_CONTRACT_ID, maximum=128) for entry in raw)
    component_refs: list[tuple[str, str, str | None]] = []
    for role in ("producer", "checker"):
        component = components.get(role)
        if type(component) is not dict:
            _invalid(f"components.{role}", "missing component")
        component_refs.append((_text(component.get("contract_id"), f"components.{role}.contract_id", pattern=_CONTRACT_ID, maximum=128), _sha(component.get("contract_sha256"), f"components.{role}.contract_sha256"), None))
    contract_refs: set[tuple[str, str, str | None]] = set(component_refs)
    for contract_id in required_ids:
        if contract_id not in contracts:
            _invalid("operation", f"required contract {contract_id} is absent")
        digest, schema = contracts[contract_id]
        contract_refs.add((contract_id, digest, schema))
    for contract_id, digest, schema in sorted(contract_refs):
        result.append(_make_prerequisite("contract", digest, contract_id=contract_id, artifact_schema=schema))
    raw_dependencies = candidate["dependency_descriptor_sha256s"]
    if type(raw_dependencies) is not list:
        _invalid("candidate.dependencies", "invalid dependency array")
    for digest in sorted(_sha(entry, "candidate.dependency") for entry in raw_dependencies):
        result.append(_make_prerequisite("descriptor_dependency", digest, artifact_schema="mathhead.theory-plugin.v1"))
    if len(result) > 100_020:
        raise _Exhausted("prerequisite ceiling exceeded")
    return tuple(result)


def _make_expectation(candidate: dict[str, object], operation: dict[str, object]) -> PlanningEvidenceExpectation:
    authority = _choice(operation.get("authority"), ("none", "producer_report", "checker_attestation"), "operation.authority")
    mapping: dict[str, object] = {"schema": EXPECTATION_SCHEMA, "operation_authority": authority, "producer_component_id": candidate["producer_component_id"], "checker_component_id": candidate["checker_component_id"], "evidence_contract_sha256": EVIDENCE_CONTRACT_SHA256, "certificate_contract_sha256": CERTIFICATE_CONTRACT_SHA256, "evidence_format": candidate["evidence_format"], "certificate_format": candidate["certificate_format"], "independent_check_required": authority == "producer_report", "expectation_sha256": None, "mathematical_authority": False}
    mapping["expectation_sha256"] = _self_hash(mapping, "expectation_sha256")
    return _expectation_from_mapping(mapping, "expectation")


def _make_strategy(*, plan_order: int, route_order: int, candidate: dict[str, object], descriptor: dict[str, object], fragment: dict[str, object], request_mapping: dict[str, object], route_digest: str, parent: PlanningResourceVector, next_strategy_sha256: str | None) -> PlanningStrategy:
    _capability, operation, components, compatibility = _find_descriptor_parts(descriptor, candidate)
    dependencies = _string_tuple(candidate["dependency_descriptor_sha256s"], "candidate.dependencies", maximum=MAX_DEPENDENCIES)
    effects = _string_tuple(candidate["effect_kinds"], "candidate.effects", choices=("environment", "filesystem", "network", "process", "solver"), maximum=5)
    cost = _keys(candidate["cost"], {"schema", "base", "variable_term", "expression_node_term", "quantifier_term", "goal_term", "ambiguity_term", "unsaturated_total", "maximum", "estimated_cost", "saturated", "confidence_ppm", "cost_sha256", "mathematical_authority"}, "candidate.cost")
    estimated_cost = _integer(cost["estimated_cost"], "candidate.cost.estimated_cost")
    prerequisites = _candidate_prerequisites(candidate, descriptor, operation, components, compatibility, request_mapping, route_digest)
    expectation = _make_expectation(candidate, operation)
    resource = _make_resource_request(estimated_cost, fragment, effects, parent)
    if not resource.fits_parent:
        raise _Exhausted("strategy resource request exceeds declared parent limits")
    transitions = _make_transitions(next_strategy_sha256)
    mapping: dict[str, object] = {"schema": STRATEGY_SCHEMA, "plan_order": plan_order, "route_order": route_order, "candidate_sha256": candidate["candidate_sha256"], "descriptor_sha256": candidate["descriptor_sha256"], "plugin_id": candidate["plugin_id"], "plugin_version": candidate["plugin_version"], "capability_id": candidate["capability_id"], "capability_kind": candidate["capability_kind"], "operation": candidate["operation"], "component_id": candidate["component_id"], "producer_component_id": candidate["producer_component_id"], "checker_component_id": candidate["checker_component_id"], "session_head_sha256": candidate["session_head_sha256"], "session_context_sha256": candidate["session_context_sha256"], "normalization_result_sha256": candidate["normalization_result_sha256"], "obligation_semantic_sha256": candidate["obligation_semantic_sha256"], "fragment_sha256": candidate["fragment_sha256"], "dependency_descriptor_sha256s": list(dependencies), "effect_kinds": list(effects), "replay_mode": candidate["replay_mode"], "priority": candidate["priority"], "estimated_cost": estimated_cost, "cost_sha256": cost["cost_sha256"], "prerequisites": [_prerequisite_mapping(item) for item in prerequisites], "evidence_expectation": _expectation_mapping(expectation), "resource_request": _resource_request_mapping(resource), "transitions": [_transition_mapping(item) for item in transitions], "strategy_sha256": None, "mathematical_authority": False}
    mapping["strategy_sha256"] = _self_hash(mapping, "strategy_sha256")
    return _strategy_from_mapping(mapping, f"strategy[{plan_order}]")


def plan_strategies(request: bytes, route_result: bytes, descriptors: tuple[bytes, ...], artifacts: tuple[bytes, ...]) -> PlanningResult:
    """Produce a pure content-addressed strategy DAG for one fresh exact route."""
    try:
        if type(request) is not bytes or type(route_result) is not bytes:
            _invalid("$", "request and route result must be exact bytes")
        request_value = _request_from_mapping(_parse_json(request, "request", MAX_REQUEST_BYTES), "request")
        if len(route_result) > MAX_ROUTE_BYTES:
            raise _Exhausted("route result byte ceiling exceeded")
        supplied_route = parse_capability_route_result(route_result)
        if _digest(route_result) != request_value.route_result_sha256:
            _invalid("route_result", "exact byte digest differs from planning request")
        descriptors_by_sha = _descriptor_inputs(descriptors)
        _check_artifact_tuple(artifacts)
        fresh_route = route_capabilities(request_value.route_request, descriptors, artifacts)
        fresh_bytes = capability_route_result_bytes(fresh_route)
        if fresh_bytes != route_result or fresh_route != supplied_route:
            _invalid("route_result", "fresh route recomputation is not byte-identical")
        if fresh_route.status == "unsupported":
            return _make_result(status="unsupported", reason_code="ROUTE_UNSUPPORTED", request=request_value)
        if fresh_route.status == "ambiguous":
            return _make_result(status="ambiguous", reason_code="ROUTE_AMBIGUOUS", request=request_value)
        if fresh_route.status == "exhausted":
            return _make_result(status="exhausted", reason_code="ROUTE_EXHAUSTED")
        if fresh_route.status != "routed":
            _invalid("route_result", "route is not planned from an invalid status")
        route_mapping = _parse_json(route_result, "route_result", MAX_ROUTE_BYTES)
        raw_candidates = route_mapping["candidates"]
        fragment = route_mapping["fragment"]
        request_mapping = _parse_json(request_value.route_request, "route_request", MAX_REQUEST_BYTES)
        if type(raw_candidates) is not list or not raw_candidates or type(fragment) is not dict:
            _invalid("route_result", "routed result lacks candidates or fragment")
        if len(raw_candidates) > request_value.policy.maximum_strategies:
            raise _Exhausted("candidate count exceeds policy maximum_strategies")
        indexed = list(enumerate(raw_candidates))
        if request_value.policy.mode == "deterministic_first":
            replay_rank = {"deterministic": 0, "seeded": 1, "recorded": 2}
            indexed.sort(key=lambda pair: (replay_rank.get(pair[1].get("replay_mode"), 3) if type(pair[1]) is dict else 3, pair[0]))
        planned: list[PlanningStrategy] = []
        next_identity: str | None = None
        route_digest = _digest(route_result)
        for plan_order in range(len(indexed) - 1, -1, -1):
            route_order, candidate = indexed[plan_order]
            if type(candidate) is not dict:
                _invalid(f"route_result.candidates[{route_order}]", "candidate is not an object")
            descriptor_sha = _sha(candidate.get("descriptor_sha256"), "candidate.descriptor_sha256")
            descriptor = descriptors_by_sha.get(descriptor_sha)
            if descriptor is None:
                _invalid("candidate", "descriptor bytes missing")
            strategy = _make_strategy(plan_order=plan_order, route_order=route_order, candidate=candidate, descriptor=descriptor, fragment=fragment, request_mapping=request_mapping, route_digest=route_digest, parent=request_value.resource_limits, next_strategy_sha256=next_identity)
            planned.insert(0, strategy)
            next_identity = strategy.strategy_sha256
        result = _make_result(status="planned", reason_code="PLANNED", request=request_value, strategies=tuple(planned))
        _canonical_bytes(_result_mapping(result), maximum=MAX_ROUTE_BYTES)
        return result
    except _Exhausted as exc:
        return _make_result(status="exhausted", reason_code="PLANNING_EXHAUSTED", diagnostic=str(exc))
    except _Invalid as exc:
        return _make_result(status="invalid", reason_code="INVALID_INPUT", diagnostic=str(exc))
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError, KeyError, AttributeError) as exc:
        return _make_result(status="invalid", reason_code="INVALID_INPUT", diagnostic=str(exc))


def planning_result_bytes(value: PlanningResult) -> bytes:
    if type(value) is not PlanningResult:
        _fail("type", "$", "expected exact PlanningResult")
    validate_planning_result(value)
    return _canonical_bytes(_result_mapping(value), maximum=MAX_ROUTE_BYTES)


def validate_planning_result(value: PlanningResult) -> None:
    if type(value) is not PlanningResult:
        _fail("type", "$", "expected exact PlanningResult")
    try:
        parsed = _result_from_mapping(_result_mapping(value))
        if parsed != value:
            _invalid("$", "in-memory result differs from strict reconstruction")
    except (_Invalid, _Exhausted, AttributeError, KeyError, TypeError) as exc:
        _fail("result", "$", str(exc))


def parse_planning_result(data: bytes) -> PlanningResult:
    """Strictly parse and recompute a serialized planner result."""
    try:
        return _result_from_mapping(_parse_json(data, "$", MAX_ROUTE_BYTES))
    except (_Invalid, _Exhausted, AttributeError, KeyError, TypeError) as exc:
        _fail("result", "$", str(exc))


__all__ = [
    "CONTRACT_ID",
    "CONTRACT_SHA256",
    "SCHEMA_SHA256S",
    "RESOURCE_DIMENSIONS",
    "OUTCOMES",
    "PlanningResourceVector",
    "PlanningPolicy",
    "PlanningRequest",
    "PlanningPrerequisite",
    "PlanningEvidenceExpectation",
    "PlanningResourceRequest",
    "PlanningTransition",
    "PlanningStrategy",
    "PlanningResult",
    "DeterministicPlannerValidationError",
    "make_planning_policy",
    "planning_policy_bytes",
    "make_planning_request",
    "parse_planning_request",
    "plan_strategies",
    "planning_result_bytes",
    "validate_planning_result",
    "parse_planning_result",
]
