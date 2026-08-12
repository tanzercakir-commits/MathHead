"""Pure typed capability registration and routing for MH-050.

The boundary consumes explicit canonical bytes only.  It never imports a plugin,
inspects the host, executes a producer/checker, or grants mathematical authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from typing import Any, Final, Mapping, NoReturn
import unicodedata

from mathhead.canonical_normalization import (
    CONTRACT_SHA256 as CANONICAL_NORMALIZATION_CONTRACT_SHA256,
    canonical_normal_form_bytes,
    canonical_obligation_bytes,
    parse_canonical_normalization_result,
)
from mathhead.problem_sessions import (
    PROBLEM_SESSION_CONTRACT_SHA256,
    transition_problem_session,
)


CONTRACT_ID: Final = "MH-C-CAPABILITY-REGISTRY-001"
CONTRACT_SHA256: Final = "52cc70945a4e83115c756e5b0a72724676f0e52a89e56c06a0fa8bd42c0e0413"
THEORY_PLUGIN_CONTRACT_SHA256: Final = (
    "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8"
)
THEORY_PLUGIN_SCHEMA_SHA256: Final = (
    "c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142"
)
SCHEMA_SHA256S: Final = {
    "capability-availability-v1.schema.json": "aea788ecdee20497bb485c371b07a220707dabf1548bdc930e8b6c66877b52e1",
    "capability-candidate-v1.schema.json": "cc5c231bc11021e155b6390b2682ee63c4c6b2a3d30807f24a9c5d4ae31a75ed",
    "capability-cost-derivation-v1.schema.json": "f4de59ae5cff8d9e096e42f0bc4d044f611997be5df5ae95f5a47f40d7e9d915",
    "capability-incompatibility-v1.schema.json": "53780cc2e9d3e2fec418c6d04ad417d6920f3d4e12cf953b2bafca864d5054f2",
    "capability-registry-entry-v1.schema.json": "a20d3bcc4dd5bd5988eac60b6000ea8e92299f2aa13275f77a2306fb68dd8b3c",
    "capability-registry-v1.schema.json": "37e03e97fcd736b3c75e0c8c33f3d82c735dc57c4463ead8af9d331704761fbc",
    "capability-route-request-v1.schema.json": "cdf7dd11d0f1048c018c3472f7f0237ac3713db5edbbd1851761ab7388c4cc82",
    "capability-route-result-v1.schema.json": "11c23f4822be4e531e28bf66f47940fdeb389222305f04162c67ced66e2e49ec",
}

AVAILABILITY_SCHEMA: Final = "mathhead.capability-availability.v1"
ENTRY_SCHEMA: Final = "mathhead.capability-registry-entry.v1"
REGISTRY_SCHEMA: Final = "mathhead.capability-registry.v1"
REQUEST_SCHEMA: Final = "mathhead.capability-route-request.v1"
FRAGMENT_SCHEMA: Final = "mathhead.capability-fragment.v1"
COST_SCHEMA: Final = "mathhead.capability-cost-derivation.v1"
CANDIDATE_SCHEMA: Final = "mathhead.capability-candidate.v1"
INCOMPATIBILITY_SCHEMA: Final = "mathhead.capability-incompatibility.v1"
RESULT_SCHEMA: Final = "mathhead.capability-route-result.v1"

MAX_REQUEST_BYTES: Final = 4_194_304
MAX_DESCRIPTOR_BYTES: Final = 67_108_864
MAX_AGGREGATE_DESCRIPTOR_BYTES: Final = 1_073_741_824
MAX_DESCRIPTORS: Final = 10_000
MAX_ARTIFACT_BYTES: Final = 67_108_864
MAX_AGGREGATE_ARTIFACT_BYTES: Final = 1_073_741_824
MAX_ARTIFACTS: Final = 100_000
MAX_CAPABILITIES: Final = 1_000_000
MAX_DEPENDENCIES: Final = 1_000_000
MAX_JSON_NESTING: Final = 128
MAX_JSON_NODES: Final = 8_000_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_DIAGNOSTIC_CODEPOINTS: Final = 1_024
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_OUTPUT_BYTES: Final = 1_073_741_824

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_NAMESPACED = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_CONTRACT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9._:-]*$")
_PACKAGE = re.compile(r"^[a-z][a-z0-9_-]*$")
_ENTRY_POINT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*$")
_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?$")
_PLATFORMS = ("linux", "macos", "windows")
_PYTHON_VERSIONS = ("3.10", "3.11", "3.12", "3.13", "3.14")
_EFFECTS = ("environment", "filesystem", "network", "process", "solver")
_REPLAY_MODES = ("deterministic", "recorded", "seeded")
_KINDS = ("construction", "decision", "explanation", "verification")
_OPERATIONS = ("plan_cost", "solve", "check", "explain")
_OPERATION_KINDS: Final = {
    "plan_cost": frozenset(_KINDS),
    "solve": frozenset(("construction", "decision")),
    "check": frozenset(("verification",)),
    "explain": frozenset(("explanation",)),
}
_REASON_CODES = (
    "AMBIGUITY_UNSUPPORTED", "ARITHMETIC_MISMATCH", "CAPABILITY_KIND_MISMATCH",
    "CERTIFICATE_FORMAT_MISMATCH", "DEPENDENCY_UNAVAILABLE", "DOMAIN_MISMATCH",
    "EFFECT_FORBIDDEN", "EVIDENCE_FORMAT_MISMATCH", "EXPRESSION_KIND_MISMATCH",
    "EXTENSION_UNAVAILABLE", "FEATURE_FORBIDDEN", "FEATURE_REQUIRED", "LIMIT_EXCEEDED",
    "LIFECYCLE_UNAVAILABLE", "OPERATION_MISMATCH", "PLATFORM_UNAVAILABLE",
    "PYTHON_VERSION_UNAVAILABLE", "QUANTIFIER_MISMATCH", "RELATION_KIND_MISMATCH",
    "REPLAY_MODE_UNAVAILABLE", "THEORY_MISMATCH",
)
_EXACT_DOMAINS = frozenset(("boolean", "integer", "modular", "polynomial", "rational", "set"))
_DOMAIN_THEORIES: Final = {
    "boolean": "org.mathhead.theory.logic",
    "complex": "org.mathhead.theory.analysis",
    "graph": "org.mathhead.theory.graph",
    "integer": "org.mathhead.theory.arithmetic",
    "modular": "org.mathhead.theory.arithmetic",
    "polynomial": "org.mathhead.theory.algebra",
    "rational": "org.mathhead.theory.arithmetic",
    "real": "org.mathhead.theory.analysis",
    "set": "org.mathhead.theory.set",
}
_EXPECTED_FOUNDATION_CONTRACTS: Final = {
    "MH-C-CERTIFICATE-001": ("0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740", "mathhead.certificate.v1"),
    "MH-C-ENGINE-RESULT-001": ("6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370", "mathhead.engine-result.v1"),
    "MH-C-EVIDENCE-001": ("c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3", "mathhead.evidence.v1"),
    "MH-C-PROBLEM-IR-002": ("6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286", "mathhead.problem-ir.v1"),
    "MH-C-RESOURCE-BUDGET-001": ("eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045", "mathhead.resource-budget.v1"),
    "MH-C-THEORY-CONTEXT-001": ("d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d", "mathhead.theory-context.v1"),
}
_EXPECTED_PLUGIN_LIMITS: Final = {
    "canonical_nesting": 64,
    "canonical_nodes": 4_000_000,
    "entities": 100_000,
    "input_bytes": 67_108_864,
    "items_per_array": 100_000,
    "memory_mb": 512,
    "string_codepoints": 1_048_576,
    "validation_seconds": 30,
}
_BASE_OPERATION_REQUESTS: Final = (
    "MH-C-PROBLEM-IR-002",
    "MH-C-RESOURCE-BUDGET-001",
    "MH-C-THEORY-CONTEXT-001",
)
_OPERATION_OUTCOMES: Final = {
    "plan_cost": ("completed", "error", "unsupported"),
    "solve": ("ambiguous", "cancelled", "completed", "error", "exhausted", "truncated", "unsupported"),
    "check": ("cancelled", "disagreement", "exhausted", "inconclusive", "invalid", "truncated", "unsupported", "verified", "verifier_failed"),
    "explain": ("cancelled", "completed", "error", "exhausted", "truncated", "unsupported"),
}


class CapabilityRegistryValidationError(ValueError):
    """Raised by strict component and result validation boundaries."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        self.kind = kind
        self.path = path
        self.detail = detail
        super().__init__(f"{kind} at {path}: {detail}")


class _Invalid(ValueError):
    pass


class _Ambiguous(ValueError):
    pass


class _Exhausted(ValueError):
    pass


class _DuplicateKey(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class _FrozenMap:
    entries: tuple[tuple[str, object], ...]


_PUBLIC_VALUES_FINAL = False


class _RegistryValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_VALUES_FINAL:
            raise TypeError("capability registry value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class CapabilityAvailability(_RegistryValue):
    schema: str
    platform: str
    python_version: str
    extension_ids: tuple[str, ...]
    available_descriptor_sha256s: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    replay_modes: tuple[str, ...]
    availability_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("capability availability is created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityRegistryEntry(_RegistryValue):
    schema: str
    descriptor_sha256: str
    plugin_id: str
    plugin_version: str
    implementation_sha256: str
    producer_component_id: str
    checker_component_id: str
    capability_ids: tuple[str, ...]
    dependency_descriptor_sha256s: tuple[str, ...]
    entry_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("registry entries are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityRegistry(_RegistryValue):
    schema: str
    descriptor_sha256s: tuple[str, ...]
    entries: tuple[CapabilityRegistryEntry, ...]
    dependency_order_sha256s: tuple[str, ...]
    registry_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("registries are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityRouteRequest(_RegistryValue):
    schema: str
    session_id: str
    session_head_sha256: str
    session_context_sha256: str
    event_sha256s: tuple[str, ...]
    session_artifact_sha256s: tuple[str, ...]
    normalization_result_sha256: str
    reading_id: str
    session_obligation_record_id: str
    obligation_artifact_sha256: str
    obligation_semantic_sha256: str
    local_context_semantic_sha256: str
    capability_kind: str
    operation: str
    evidence_format: object | None
    certificate_format: object | None
    availability: CapabilityAvailability
    replay_mode: str
    request_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("route requests are created only by validation")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityFragment(_RegistryValue):
    schema: str
    theories: tuple[str, ...]
    domains: tuple[str, ...]
    quantifiers: tuple[str, ...]
    expression_kinds: tuple[str, ...]
    relation_kinds: tuple[str, ...]
    polynomial_degree: int
    quantifier_count: int
    quantifier_depth: int
    variables: int
    expression_nodes: int
    goals: int
    ambiguous: bool
    exact_arithmetic: bool
    theory_features: tuple[str, ...]
    fragment_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("capability fragments are derived only from accepted artifacts")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityCostDerivation(_RegistryValue):
    schema: str
    base: int
    variable_term: int
    expression_node_term: int
    quantifier_term: int
    goal_term: int
    ambiguity_term: int
    unsaturated_total: int
    maximum: int
    estimated_cost: int
    saturated: bool
    confidence_ppm: int
    cost_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("cost derivations are created only by routing")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityCandidate(_RegistryValue):
    schema: str
    registry_sha256: str
    request_sha256: str
    availability_sha256: str
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
    evidence_format: object | None
    certificate_format: object | None
    effect_kinds: tuple[str, ...]
    replay_mode: str
    priority: int
    cost: CapabilityCostDerivation
    candidate_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("candidates are created only by routing")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityIncompatibility(_RegistryValue):
    schema: str
    descriptor_sha256: str
    plugin_id: str
    plugin_version: str
    capability_id: str
    capability_kind: str
    operation: str
    reason_codes: tuple[str, ...]
    incompatibility_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("incompatibilities are created only by routing")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityRouteResult(_RegistryValue):
    schema: str
    contract_id: str
    contract_sha256: str
    theory_plugin_contract_sha256: str
    canonical_normalization_contract_sha256: str
    problem_session_contract_sha256: str
    status: str
    reason_code: str
    diagnostic: str
    request_sha256: str | None
    registry: CapabilityRegistry | None
    fragment: CapabilityFragment | None
    candidates: tuple[CapabilityCandidate, ...]
    incompatibilities: tuple[CapabilityIncompatibility, ...]
    selected_candidate_sha256: str | None
    result_sha256: str | None
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("route results are created only by routing")


_PUBLIC_VALUES_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    instance = object.__new__(cls)
    for item in fields(cls):
        object.__setattr__(instance, item.name, values[item.name])
    return instance


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise CapabilityRegistryValidationError(kind, path, detail)


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


def _check_canonical_value(value: object, path: str = "$") -> None:
    stack: list[tuple[object, int, str]] = [(value, 0, path)]
    visited = 0
    while stack:
        item, depth, current = stack.pop()
        visited += 1
        if visited > MAX_JSON_NODES or depth > MAX_JSON_NESTING:
            raise _Exhausted(f"{current}: canonical value budget exceeded")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > MAX_INTEGER:
                _invalid(current, "integer exceeds portable exact range")
            continue
        if type(item) is str:
            if len(item) > MAX_STRING_CODEPOINTS:
                raise _Exhausted(f"{current}: string budget exceeded")
            if "\x00" in item or unicodedata.normalize("NFC", item) != item:
                _invalid(current, "text must be NFC and contain no NUL")
            continue
        if type(item) is list:
            stack.extend((child, depth + 1, f"{current}[{index}]") for index, child in enumerate(item))
            continue
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    _invalid(current, "mapping keys must be exact strings")
                stack.append((child, depth + 1, f"{current}.{key}"))
            continue
        _invalid(current, "non-canonical JSON value")


def _canonical_bytes(value: object, *, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    _check_canonical_value(value)
    try:
        data = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        _invalid("$", f"cannot serialize canonical value: {exc}")
    if len(data) > maximum:
        raise _Exhausted("$: canonical output budget exceeded")
    return data


def _parse_json(data: bytes, path: str, maximum: int) -> dict[str, object]:
    if type(data) is not bytes:
        _invalid(path, "must be exact bytes")
    if not data or len(data) > maximum:
        raise _Exhausted(f"{path}: byte budget exceeded")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except _DuplicateKey as exc:
        _invalid(path, f"duplicate JSON key {exc}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _invalid(path, f"invalid UTF-8 JSON: {exc}")
    if type(value) is not dict:
        _invalid(path, "root must be an object")
    _check_canonical_value(value, path)
    if data != _canonical_bytes(value, maximum=maximum):
        _invalid(path, "bytes are not canonical JSON")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != expected:
        _invalid(path, "field set drift")
    return value


def _text(value: object, path: str, *, pattern: re.Pattern[str] | None = None, maximum: int = 4096) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        _invalid(path, "invalid string")
    if "\x00" in value or unicodedata.normalize("NFC", value) != value:
        _invalid(path, "text must be NFC and contain no NUL")
    if pattern is not None and pattern.fullmatch(value) is None:
        _invalid(path, "string pattern mismatch")
    return value


def _optional_text(value: object, path: str, *, maximum: int = 4096) -> str | None:
    if value is None:
        return None
    return _text(value, path, maximum=maximum)


def _integer(value: object, path: str, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        _invalid(path, "invalid nonnegative integer")
    return value


def _boolean(value: object, path: str) -> bool:
    if type(value) is not bool:
        _invalid(path, "invalid boolean")
    return value


def _string_tuple(
    value: object,
    path: str,
    *,
    pattern: re.Pattern[str] | None = None,
    maximum: int = 100_000,
    choices: tuple[str, ...] | None = None,
    require_nonempty: bool = False,
    preserve_order: bool = False,
) -> tuple[str, ...]:
    if type(value) is not list or len(value) > maximum or (require_nonempty and not value):
        _invalid(path, "invalid array")
    result = tuple(_text(item, f"{path}[{index}]", pattern=pattern, maximum=255) for index, item in enumerate(value))
    if len(result) != len(set(result)):
        _invalid(path, "values must be unique")
    if not preserve_order and result != tuple(sorted(result)):
        _invalid(path, "values must be sorted")
    if choices is not None and any(item not in choices for item in result):
        _invalid(path, "unknown value")
    return result


def _sha(value: object, path: str) -> str:
    return _text(value, path, pattern=_DIGEST, maximum=64)


def _self_hash(value: Mapping[str, object], field: str) -> str:
    basis = dict(value)
    basis[field] = None
    return _digest(_canonical_bytes(basis))


def _mapping_from_format(value: object, path: str) -> dict[str, object] | None:
    if value is None:
        return None
    item = _keys(value, {"format_id", "major", "minor", "required_features"}, path)
    result = {
        "format_id": _text(item["format_id"], f"{path}.format_id", pattern=_NAMESPACED, maximum=255),
        "major": _integer(item["major"], f"{path}.major"),
        "minor": _integer(item["minor"], f"{path}.minor"),
        "required_features": list(_string_tuple(item["required_features"], f"{path}.required_features", pattern=_NAMESPACED)),
    }
    return result


def _freeze_json(value: object) -> object:
    if type(value) is dict:
        return _FrozenMap(
            tuple((key, _freeze_json(item)) for key, item in sorted(value.items()))
        )
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if type(value) is _FrozenMap:
        return {key: _thaw_json(item) for key, item in value.entries}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _availability_mapping(value: CapabilityAvailability, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "platform": value.platform,
        "python_version": value.python_version,
        "extension_ids": list(value.extension_ids),
        "available_descriptor_sha256s": list(value.available_descriptor_sha256s),
        "allowed_effects": list(value.allowed_effects),
        "replay_modes": list(value.replay_modes),
        "availability_sha256": value.availability_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _availability_from_mapping(value: object, path: str = "$.availability") -> CapabilityAvailability:
    item = _keys(value, {"schema", "platform", "python_version", "extension_ids", "available_descriptor_sha256s", "allowed_effects", "replay_modes", "availability_sha256", "mathematical_authority"}, path)
    if item["schema"] != AVAILABILITY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "availability schema or authority drift")
    platform = _text(item["platform"], f"{path}.platform")
    python_version = _text(item["python_version"], f"{path}.python_version")
    if platform not in _PLATFORMS or python_version not in _PYTHON_VERSIONS:
        _invalid(path, "unknown platform or Python version")
    extensions = _string_tuple(item["extension_ids"], f"{path}.extension_ids", pattern=_NAMESPACED)
    descriptors = _string_tuple(item["available_descriptor_sha256s"], f"{path}.available_descriptor_sha256s", pattern=_DIGEST, maximum=MAX_DESCRIPTORS)
    effects = _string_tuple(item["allowed_effects"], f"{path}.allowed_effects", choices=_EFFECTS, maximum=5)
    replay = _string_tuple(item["replay_modes"], f"{path}.replay_modes", choices=_REPLAY_MODES, maximum=3, require_nonempty=True)
    identity = _sha(item["availability_sha256"], f"{path}.availability_sha256")
    if identity != _self_hash(item, "availability_sha256"):
        _invalid(f"{path}.availability_sha256", "availability identity mismatch")
    return _make(CapabilityAvailability, schema=AVAILABILITY_SCHEMA, platform=platform, python_version=python_version, extension_ids=extensions, available_descriptor_sha256s=descriptors, allowed_effects=effects, replay_modes=replay, availability_sha256=identity, mathematical_authority=False)


def make_capability_availability(
    *,
    platform: str,
    python_version: str,
    extension_ids: tuple[str, ...] = (),
    available_descriptor_sha256s: tuple[str, ...] = (),
    allowed_effects: tuple[str, ...] = (),
    replay_modes: tuple[str, ...] = ("deterministic",),
) -> CapabilityAvailability:
    value: dict[str, object] = {
        "schema": AVAILABILITY_SCHEMA,
        "platform": platform,
        "python_version": python_version,
        "extension_ids": list(extension_ids),
        "available_descriptor_sha256s": list(available_descriptor_sha256s),
        "allowed_effects": list(allowed_effects),
        "replay_modes": list(replay_modes),
        "availability_sha256": None,
        "mathematical_authority": False,
    }
    value["availability_sha256"] = _self_hash(value, "availability_sha256")
    return _availability_from_mapping(value)


def capability_availability_bytes(value: CapabilityAvailability) -> bytes:
    if type(value) is not CapabilityAvailability:
        _fail("type", "$", "expected CapabilityAvailability")
    parsed = _availability_from_mapping(_availability_mapping(value))
    if parsed != value:
        _fail("identity", "$", "availability value drift")
    return _canonical_bytes(_availability_mapping(value))


def _request_mapping(value: CapabilityRouteRequest, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "session_id": value.session_id,
        "session_head_sha256": value.session_head_sha256,
        "session_context_sha256": value.session_context_sha256,
        "event_sha256s": list(value.event_sha256s),
        "session_artifact_sha256s": list(value.session_artifact_sha256s),
        "normalization_result_sha256": value.normalization_result_sha256,
        "reading_id": value.reading_id,
        "session_obligation_record_id": value.session_obligation_record_id,
        "obligation_artifact_sha256": value.obligation_artifact_sha256,
        "obligation_semantic_sha256": value.obligation_semantic_sha256,
        "local_context_semantic_sha256": value.local_context_semantic_sha256,
        "capability_kind": value.capability_kind,
        "operation": value.operation,
        "evidence_format": _thaw_json(value.evidence_format),
        "certificate_format": _thaw_json(value.certificate_format),
        "availability": _availability_mapping(value.availability),
        "replay_mode": value.replay_mode,
        "request_sha256": value.request_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _request_from_mapping(value: object, path: str = "$") -> CapabilityRouteRequest:
    expected = {"schema", "session_id", "session_head_sha256", "session_context_sha256", "event_sha256s", "session_artifact_sha256s", "normalization_result_sha256", "reading_id", "session_obligation_record_id", "obligation_artifact_sha256", "obligation_semantic_sha256", "local_context_semantic_sha256", "capability_kind", "operation", "evidence_format", "certificate_format", "availability", "replay_mode", "request_sha256", "mathematical_authority"}
    item = _keys(value, expected, path)
    if item["schema"] != REQUEST_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "request schema or authority drift")
    kind = _text(item["capability_kind"], f"{path}.capability_kind")
    operation = _text(item["operation"], f"{path}.operation")
    replay_mode = _text(item["replay_mode"], f"{path}.replay_mode")
    if kind not in _KINDS or operation not in _OPERATIONS or replay_mode not in _REPLAY_MODES:
        _invalid(path, "unknown kind, operation, or replay mode")
    if kind not in _OPERATION_KINDS[operation]:
        _invalid(path, "capability kind and operation disagree")
    evidence = _mapping_from_format(item["evidence_format"], f"{path}.evidence_format")
    certificate = _mapping_from_format(item["certificate_format"], f"{path}.certificate_format")
    if operation in {"solve", "check"} and evidence is None:
        _invalid(path, "solve/check require an Evidence format")
    if operation == "check" and certificate is None:
        _invalid(path, "check requires a Certificate format")
    availability = _availability_from_mapping(item["availability"], f"{path}.availability")
    if replay_mode not in availability.replay_modes:
        _invalid(path, "request replay mode is unavailable")
    identity = _sha(item["request_sha256"], f"{path}.request_sha256")
    if identity != _self_hash(item, "request_sha256"):
        _invalid(f"{path}.request_sha256", "request identity mismatch")
    return _make(
        CapabilityRouteRequest,
        schema=REQUEST_SCHEMA,
        session_id=_text(item["session_id"], f"{path}.session_id", pattern=_ID, maximum=128),
        session_head_sha256=_sha(item["session_head_sha256"], f"{path}.session_head_sha256"),
        session_context_sha256=_sha(item["session_context_sha256"], f"{path}.session_context_sha256"),
        event_sha256s=_string_tuple(item["event_sha256s"], f"{path}.event_sha256s", pattern=_DIGEST, maximum=MAX_ARTIFACTS, require_nonempty=True, preserve_order=True),
        session_artifact_sha256s=_string_tuple(item["session_artifact_sha256s"], f"{path}.session_artifact_sha256s", pattern=_DIGEST, maximum=MAX_ARTIFACTS, require_nonempty=True),
        normalization_result_sha256=_sha(item["normalization_result_sha256"], f"{path}.normalization_result_sha256"),
        reading_id=_text(item["reading_id"], f"{path}.reading_id", pattern=_ID, maximum=128),
        session_obligation_record_id=_text(item["session_obligation_record_id"], f"{path}.session_obligation_record_id", pattern=_ID, maximum=128),
        obligation_artifact_sha256=_sha(item["obligation_artifact_sha256"], f"{path}.obligation_artifact_sha256"),
        obligation_semantic_sha256=_sha(item["obligation_semantic_sha256"], f"{path}.obligation_semantic_sha256"),
        local_context_semantic_sha256=_sha(item["local_context_semantic_sha256"], f"{path}.local_context_semantic_sha256"),
        capability_kind=kind,
        operation=operation,
        evidence_format=_freeze_json(evidence),
        certificate_format=_freeze_json(certificate),
        availability=availability,
        replay_mode=replay_mode,
        request_sha256=identity,
        mathematical_authority=False,
    )


def make_capability_route_request(
    *,
    session_id: str,
    session_head_sha256: str,
    session_context_sha256: str,
    event_sha256s: tuple[str, ...],
    session_artifact_sha256s: tuple[str, ...],
    normalization_result_sha256: str,
    reading_id: str,
    session_obligation_record_id: str,
    obligation_artifact_sha256: str,
    obligation_semantic_sha256: str,
    local_context_semantic_sha256: str,
    capability_kind: str,
    operation: str,
    availability: CapabilityAvailability,
    replay_mode: str = "deterministic",
    evidence_format: Mapping[str, object] | None = None,
    certificate_format: Mapping[str, object] | None = None,
) -> bytes:
    if type(availability) is not CapabilityAvailability:
        _fail("type", "availability", "expected CapabilityAvailability")
    value: dict[str, object] = {
        "schema": REQUEST_SCHEMA,
        "session_id": session_id,
        "session_head_sha256": session_head_sha256,
        "session_context_sha256": session_context_sha256,
        "event_sha256s": list(event_sha256s),
        "session_artifact_sha256s": list(session_artifact_sha256s),
        "normalization_result_sha256": normalization_result_sha256,
        "reading_id": reading_id,
        "session_obligation_record_id": session_obligation_record_id,
        "obligation_artifact_sha256": obligation_artifact_sha256,
        "obligation_semantic_sha256": obligation_semantic_sha256,
        "local_context_semantic_sha256": local_context_semantic_sha256,
        "capability_kind": capability_kind,
        "operation": operation,
        "evidence_format": dict(evidence_format) if evidence_format is not None else None,
        "certificate_format": dict(certificate_format) if certificate_format is not None else None,
        "availability": _availability_mapping(availability),
        "replay_mode": replay_mode,
        "request_sha256": None,
        "mathematical_authority": False,
    }
    value["request_sha256"] = _self_hash(value, "request_sha256")
    request = _request_from_mapping(value)
    return _canonical_bytes(_request_mapping(request), maximum=MAX_REQUEST_BYTES)


def parse_capability_route_request(data: bytes) -> CapabilityRouteRequest:
    try:
        return _request_from_mapping(_parse_json(data, "$", MAX_REQUEST_BYTES))
    except (_Invalid, _Exhausted) as exc:
        _fail("schema", "$", str(exc))


def _semver(value: object, path: str) -> tuple[int, int, int, str]:
    text = _text(value, path, maximum=64)
    match = _SEMVER.fullmatch(text)
    if match is None:
        _invalid(path, "invalid semantic version")
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), text


def _semver_rank(value: str, path: str) -> tuple[object, ...]:
    major, minor, patch, text = _semver(value, path)
    if "-" not in text:
        return major, minor, patch, 1, ()
    prerelease = text.split("-", 1)[1]
    tokens = tuple(
        (0, int(token)) if token.isdigit() else (1, token)
        for token in prerelease.split(".")
    )
    return major, minor, patch, 0, tokens


def _plugin_sorted_strings(value: object, path: str, *, choices: tuple[str, ...] | None = None, nonempty: bool = False) -> tuple[str, ...]:
    return _string_tuple(value, path, maximum=100_000, choices=choices, require_nonempty=nonempty)


def _validate_plugin_format(value: object, path: str) -> dict[str, object]:
    item = _keys(value, {"format_id", "major", "minor_minimum", "minor_maximum", "required_features"}, path)
    result = {
        "format_id": _text(item["format_id"], f"{path}.format_id", pattern=_NAMESPACED, maximum=255),
        "major": _integer(item["major"], f"{path}.major"),
        "minor_minimum": _integer(item["minor_minimum"], f"{path}.minor_minimum"),
        "minor_maximum": _integer(item["minor_maximum"], f"{path}.minor_maximum"),
        "required_features": list(
            _string_tuple(
                item["required_features"],
                f"{path}.required_features",
                pattern=_NAMESPACED,
            )
        ),
    }
    if result["minor_minimum"] > result["minor_maximum"]:
        _invalid(path, "empty format interval")
    return result


def _descriptor_basis(value: dict[str, object]) -> str:
    replay = dict(value["replay"])
    replay.pop("descriptor_basis_sha256", None)
    basis = dict(value)
    basis["replay"] = replay
    return _digest(_canonical_bytes(basis, maximum=MAX_DESCRIPTOR_BYTES))


def _validate_descriptor(data: bytes, path: str) -> dict[str, object]:
    value = _parse_json(data, path, MAX_DESCRIPTOR_BYTES)
    root_fields = {"schema", "plugin_id", "display_name", "plugin_version", "api", "implementation", "components", "compatibility", "capabilities", "operations", "lifecycle", "effects", "replay", "limits", "extensions"}
    _keys(value, root_fields, path)
    if value["schema"] != "mathhead.theory-plugin.v1":
        _invalid(path, "TheoryPlugin schema mismatch")
    plugin_id = _text(value["plugin_id"], f"{path}.plugin_id", pattern=_NAMESPACED, maximum=255)
    version = _semver(value["plugin_version"], f"{path}.plugin_version")
    _text(value["display_name"], f"{path}.display_name", maximum=128)

    api = _keys(value["api"], {"contract_id", "contract_sha256", "version", "major", "minor", "reader_minimum_minor"}, f"{path}.api")
    api_version = _semver(api["version"], f"{path}.api.version")
    if api["contract_id"] != "MH-C-THEORY-PLUGIN-001" or api["contract_sha256"] != THEORY_PLUGIN_CONTRACT_SHA256 or api_version[0] != 1 or api_version[:2] != (_integer(api["major"], f"{path}.api.major"), _integer(api["minor"], f"{path}.api.minor")) or _integer(api["reader_minimum_minor"], f"{path}.api.reader_minimum_minor") > api_version[1]:
        _invalid(f"{path}.api", "TheoryPlugin API compatibility drift")

    implementation = _keys(value["implementation"], {"package", "package_version", "entry_point", "implementation_sha256", "configuration_sha256", "environment_contract_sha256"}, f"{path}.implementation")
    _text(implementation["package"], f"{path}.implementation.package", pattern=_PACKAGE, maximum=128)
    if _semver(implementation["package_version"], f"{path}.implementation.package_version")[3] != version[3]:
        _invalid(f"{path}.implementation.package_version", "plugin version mismatch")
    _text(implementation["entry_point"], f"{path}.implementation.entry_point", pattern=_ENTRY_POINT, maximum=255)
    for field in ("implementation_sha256", "configuration_sha256", "environment_contract_sha256"):
        _sha(implementation[field], f"{path}.implementation.{field}")

    components = _keys(value["components"], {"producer", "checker"}, f"{path}.components")
    component_values: dict[str, dict[str, object]] = {}
    for role in ("producer", "checker"):
        component = _keys(components[role], {"component_id", "role", "name", "version", "contract_id", "contract_sha256", "implementation_sha256", "configuration_sha256"}, f"{path}.components.{role}")
        if component["role"] != role or _semver(component["version"], f"{path}.components.{role}.version")[3] != version[3]:
            _invalid(f"{path}.components.{role}", "component role/version drift")
        _text(component["component_id"], f"{path}.components.{role}.component_id", pattern=_ID, maximum=64)
        _text(component["name"], f"{path}.components.{role}.name", pattern=_NAMESPACED, maximum=255)
        _text(component["contract_id"], f"{path}.components.{role}.contract_id", pattern=_CONTRACT_ID, maximum=128)
        for field in ("contract_sha256", "implementation_sha256", "configuration_sha256"):
            _sha(component[field], f"{path}.components.{role}.{field}")
        component_values[role] = component
    producer = component_values["producer"]
    checker = component_values["checker"]
    if producer["component_id"] == checker["component_id"] or (producer["contract_sha256"], producer["implementation_sha256"]) == (checker["contract_sha256"], checker["implementation_sha256"]):
        _invalid(f"{path}.components", "producer and checker must be distinct")
    if producer["implementation_sha256"] != implementation["implementation_sha256"] or producer["configuration_sha256"] != implementation["configuration_sha256"]:
        _invalid(f"{path}.components.producer", "root implementation provenance mismatch")

    compatibility = _keys(value["compatibility"], {"contracts", "python_versions", "platforms", "required_extensions", "optional_extensions", "plugin_dependencies"}, f"{path}.compatibility")
    contracts = compatibility["contracts"]
    if type(contracts) is not list or len(contracts) != len(_EXPECTED_FOUNDATION_CONTRACTS):
        _invalid(f"{path}.compatibility.contracts", "foundation contract count mismatch")
    contract_ids: list[str] = []
    for index, raw in enumerate(contracts):
        item = _keys(raw, {"contract_id", "sha256", "schema"}, f"{path}.compatibility.contracts[{index}]")
        identifier = _text(item["contract_id"], f"{path}.compatibility.contracts[{index}].contract_id", maximum=128)
        contract_ids.append(identifier)
        if identifier not in _EXPECTED_FOUNDATION_CONTRACTS or (item["sha256"], item["schema"]) != _EXPECTED_FOUNDATION_CONTRACTS[identifier]:
            _invalid(f"{path}.compatibility.contracts[{index}]", "foundation binding drift")
    if contract_ids != sorted(set(contract_ids)):
        _invalid(f"{path}.compatibility.contracts", "contracts must sort and deduplicate")
    python_versions = _plugin_sorted_strings(compatibility["python_versions"], f"{path}.compatibility.python_versions", choices=_PYTHON_VERSIONS, nonempty=True)
    platforms = _plugin_sorted_strings(compatibility["platforms"], f"{path}.compatibility.platforms", choices=_PLATFORMS, nonempty=True)
    required_extensions = _string_tuple(compatibility["required_extensions"], f"{path}.compatibility.required_extensions", pattern=_NAMESPACED)
    optional_extensions = _string_tuple(compatibility["optional_extensions"], f"{path}.compatibility.optional_extensions", pattern=_NAMESPACED)
    if set(required_extensions) & set(optional_extensions):
        _invalid(f"{path}.compatibility", "extension classes overlap")
    raw_dependencies = compatibility["plugin_dependencies"]
    if type(raw_dependencies) is not list or len(raw_dependencies) > 10_000:
        raise _Exhausted(f"{path}.compatibility.plugin_dependencies: dependency budget")
    dependency_ids: list[str] = []
    dependencies: list[dict[str, object]] = []
    for index, raw in enumerate(raw_dependencies):
        item = _keys(raw, {"plugin_id", "version_minimum", "version_maximum_exclusive", "descriptor_sha256"}, f"{path}.compatibility.plugin_dependencies[{index}]")
        dep_id = _text(item["plugin_id"], f"{path}.compatibility.plugin_dependencies[{index}].plugin_id", pattern=_NAMESPACED, maximum=255)
        minimum = _semver(item["version_minimum"], f"{path}.compatibility.plugin_dependencies[{index}].version_minimum")
        maximum = _semver(item["version_maximum_exclusive"], f"{path}.compatibility.plugin_dependencies[{index}].version_maximum_exclusive")
        digest = _sha(item["descriptor_sha256"], f"{path}.compatibility.plugin_dependencies[{index}].descriptor_sha256")
        if dep_id == plugin_id or minimum[:3] >= maximum[:3]:
            _invalid(f"{path}.compatibility.plugin_dependencies[{index}]", "invalid dependency")
        dependency_ids.append(dep_id)
        dependencies.append({"plugin_id": dep_id, "version_minimum": minimum[3], "version_maximum_exclusive": maximum[3], "descriptor_sha256": digest})
    if dependency_ids != sorted(set(dependency_ids)):
        _invalid(f"{path}.compatibility.plugin_dependencies", "dependencies must sort/deduplicate")

    raw_capabilities = value["capabilities"]
    if type(raw_capabilities) is not list or not raw_capabilities or len(raw_capabilities) > 10_000:
        raise _Exhausted(f"{path}.capabilities: capability budget")
    capabilities: list[dict[str, object]] = []
    capability_ids: list[str] = []
    for index, raw in enumerate(raw_capabilities):
        cap_path = f"{path}.capabilities[{index}]"
        cap = _keys(raw, {"capability_id", "kind", "theories", "priority", "fragment", "evidence_formats", "certificate_formats", "cost_model"}, cap_path)
        cap_id = _text(cap["capability_id"], f"{cap_path}.capability_id", pattern=_ID, maximum=64)
        kind = _text(cap["kind"], f"{cap_path}.kind")
        if kind not in _KINDS:
            _invalid(f"{cap_path}.kind", "unknown capability kind")
        theories = _string_tuple(cap["theories"], f"{cap_path}.theories", pattern=_NAMESPACED, require_nonempty=True)
        priority = _integer(cap["priority"], f"{cap_path}.priority", 1_000_000)
        fragment = _keys(cap["fragment"], {"domains", "quantifiers", "expression_kinds", "relation_kinds", "maximum_polynomial_degree", "maximum_quantifier_depth", "maximum_variables", "supports_ambiguity", "requires_exact_arithmetic", "required_theory_features", "forbidden_theory_features"}, f"{cap_path}.fragment")
        domains = _plugin_sorted_strings(
            fragment["domains"],
            f"{cap_path}.fragment.domains",
            choices=("boolean", "complex", "graph", "integer", "polynomial", "rational", "real", "set"),
            nonempty=True,
        )
        if len(domains) > 8:
            _invalid(f"{cap_path}.fragment.domains", "domain count exceeds descriptor schema")
        quantifiers = _plugin_sorted_strings(
            fragment["quantifiers"],
            f"{cap_path}.fragment.quantifiers",
            choices=("exists", "forall", "mixed", "none"),
            nonempty=True,
        )
        if len(quantifiers) > 4:
            _invalid(f"{cap_path}.fragment.quantifiers", "quantifier count exceeds descriptor schema")
        expression_kinds = _string_tuple(fragment["expression_kinds"], f"{cap_path}.fragment.expression_kinds", pattern=_NAMESPACED)
        relation_kinds = _string_tuple(fragment["relation_kinds"], f"{cap_path}.fragment.relation_kinds", pattern=_NAMESPACED)
        required_features = _string_tuple(fragment["required_theory_features"], f"{cap_path}.fragment.required_theory_features", pattern=_NAMESPACED)
        forbidden_features = _string_tuple(fragment["forbidden_theory_features"], f"{cap_path}.fragment.forbidden_theory_features", pattern=_NAMESPACED)
        if set(required_features) & set(forbidden_features):
            _invalid(f"{cap_path}.fragment", "required/forbidden feature overlap")
        fragment_value = {"domains": domains, "quantifiers": quantifiers, "expression_kinds": expression_kinds, "relation_kinds": relation_kinds, "maximum_polynomial_degree": _integer(fragment["maximum_polynomial_degree"], f"{cap_path}.fragment.maximum_polynomial_degree"), "maximum_quantifier_depth": _integer(fragment["maximum_quantifier_depth"], f"{cap_path}.fragment.maximum_quantifier_depth"), "maximum_variables": _integer(fragment["maximum_variables"], f"{cap_path}.fragment.maximum_variables"), "supports_ambiguity": _boolean(fragment["supports_ambiguity"], f"{cap_path}.fragment.supports_ambiguity"), "requires_exact_arithmetic": _boolean(fragment["requires_exact_arithmetic"], f"{cap_path}.fragment.requires_exact_arithmetic"), "required_theory_features": required_features, "forbidden_theory_features": forbidden_features}
        formats: dict[str, tuple[dict[str, object], ...]] = {}
        for field in ("evidence_formats", "certificate_formats"):
            raw_formats = cap[field]
            if type(raw_formats) is not list or len(raw_formats) > 1000:
                _invalid(f"{cap_path}.{field}", "invalid formats")
            parsed = tuple(_validate_plugin_format(item, f"{cap_path}.{field}[{position}]") for position, item in enumerate(raw_formats))
            ids = [item["format_id"] for item in parsed]
            if ids != sorted(set(ids)):
                _invalid(f"{cap_path}.{field}", "formats must sort/deduplicate")
            formats[field] = parsed
        if kind in {"decision", "construction"} and not formats["evidence_formats"]:
            _invalid(cap_path, "producer capability requires Evidence format")
        if kind == "verification" and not formats["certificate_formats"]:
            _invalid(cap_path, "verification capability requires Certificate format")
        cost = _keys(cap["cost_model"], {"base", "per_variable", "per_expression_node", "per_quantifier", "per_goal", "ambiguity_surcharge", "maximum", "confidence_ppm"}, f"{cap_path}.cost_model")
        cost_value = {field: _integer(cost[field], f"{cap_path}.cost_model.{field}", 1_000_000 if field == "confidence_ppm" else MAX_INTEGER) for field in cost}
        if cost_value["maximum"] < cost_value["base"] or cost_value["confidence_ppm"] == 0:
            _invalid(f"{cap_path}.cost_model", "invalid maximum or confidence")
        capability_ids.append(cap_id)
        capabilities.append({"capability_id": cap_id, "kind": kind, "theories": theories, "priority": priority, "fragment": fragment_value, "evidence_formats": formats["evidence_formats"], "certificate_formats": formats["certificate_formats"], "cost_model": cost_value})
    if capability_ids != sorted(set(capability_ids)):
        _invalid(f"{path}.capabilities", "capabilities must sort/deduplicate")

    raw_effects = value["effects"]
    if type(raw_effects) is not list or len(raw_effects) != 5:
        _invalid(f"{path}.effects", "effect registry must be complete")
    declared_effects: set[str] = set()
    effect_kinds: list[str] = []
    for index, raw in enumerate(raw_effects):
        item = _keys(raw, {"kind", "mode", "policy_id", "reason"}, f"{path}.effects[{index}]")
        effect = _text(item["kind"], f"{path}.effects[{index}].kind")
        mode = _text(item["mode"], f"{path}.effects[{index}].mode")
        if effect not in _EFFECTS or mode not in {"none", "declared"}:
            _invalid(f"{path}.effects[{index}]", "unknown effect")
        if (mode == "none") != (item["policy_id"] is None and item["reason"] is None):
            _invalid(f"{path}.effects[{index}]", "effect policy mismatch")
        if mode == "declared":
            _text(item["policy_id"], f"{path}.effects[{index}].policy_id", pattern=_NAMESPACED, maximum=255)
            _text(item["reason"], f"{path}.effects[{index}].reason", maximum=4096)
            declared_effects.add(effect)
        effect_kinds.append(effect)
    if effect_kinds != list(_EFFECTS):
        _invalid(f"{path}.effects", "effect order drift")

    replay = _keys(value["replay"], {"supported_modes", "seed_policy", "configuration_sha256", "descriptor_basis_sha256"}, f"{path}.replay")
    supported_replay = _plugin_sorted_strings(
        replay["supported_modes"],
        f"{path}.replay.supported_modes",
        choices=_REPLAY_MODES,
        nonempty=True,
    )
    if len(supported_replay) > 2:
        _invalid(f"{path}.replay.supported_modes", "replay mode count exceeds descriptor schema")

    raw_operations = value["operations"]
    if type(raw_operations) is not list or len(raw_operations) != 4:
        _invalid(f"{path}.operations", "operation ABI count drift")
    operations: dict[str, dict[str, object]] = {}
    operation_order: list[str] = []
    for index, raw in enumerate(raw_operations):
        op_path = f"{path}.operations[{index}]"
        item = _keys(raw, {"operation", "component_id", "request_contract_ids", "response_contract_ids", "response_schema", "budget_policy", "cancellation", "replay_modes", "effect_kinds", "authority", "outcomes"}, op_path)
        name = _text(item["operation"], f"{op_path}.operation")
        if name not in _OPERATIONS:
            _invalid(op_path, "unknown operation")
        component_id = _text(item["component_id"], f"{op_path}.component_id", pattern=_ID, maximum=64)
        replay_modes = _plugin_sorted_strings(
            item["replay_modes"],
            f"{op_path}.replay_modes",
            choices=_REPLAY_MODES,
            nonempty=True,
        )
        effects = _plugin_sorted_strings(
            item["effect_kinds"],
            f"{op_path}.effect_kinds",
            choices=_EFFECTS,
        )
        if not set(effects) <= declared_effects:
            _invalid(op_path, "operation uses undeclared effect")
        request_contracts = _string_tuple(
            item["request_contract_ids"],
            f"{op_path}.request_contract_ids",
            pattern=_CONTRACT_ID,
        )
        response_contracts = _string_tuple(
            item["response_contract_ids"],
            f"{op_path}.response_contract_ids",
            pattern=_CONTRACT_ID,
        )
        outcomes = _plugin_sorted_strings(
            item["outcomes"],
            f"{op_path}.outcomes",
            nonempty=True,
        )
        if len(outcomes) > 20:
            _invalid(f"{op_path}.outcomes", "outcome count exceeds descriptor schema")
        response_schema = _text(item["response_schema"], f"{op_path}.response_schema", pattern=_NAMESPACED, maximum=255)
        budget_policy = _text(item["budget_policy"], f"{op_path}.budget_policy")
        cancellation = _text(item["cancellation"], f"{op_path}.cancellation")
        authority = _text(item["authority"], f"{op_path}.authority")
        expected_component = checker["component_id"] if name == "check" else producer["component_id"]
        expected_requests = (
            ("MH-C-EVIDENCE-001", *_BASE_OPERATION_REQUESTS)
            if name == "check"
            else ("MH-C-CERTIFICATE-001", "MH-C-ENGINE-RESULT-001", "MH-C-EVIDENCE-001", *_BASE_OPERATION_REQUESTS)
            if name == "explain"
            else _BASE_OPERATION_REQUESTS
        )
        expected_responses = {
            "plan_cost": (),
            "solve": ("MH-C-ENGINE-RESULT-001", "MH-C-EVIDENCE-001"),
            "check": ("MH-C-CERTIFICATE-001",),
            "explain": (),
        }[name]
        expected_schema = {
            "plan_cost": "mathhead.plugin-cost.v1",
            "solve": "mathhead.plugin-solve.v1",
            "check": "mathhead.plugin-check.v1",
            "explain": "mathhead.plugin-explanation.v1",
        }[name]
        if (
            component_id != expected_component
            or request_contracts != expected_requests
            or response_contracts != expected_responses
            or response_schema != expected_schema
            or budget_policy != ("none" if name == "plan_cost" else "child_lease_required")
            or cancellation != ("not_applicable" if name == "plan_cost" else "cooperative_required")
            or replay_modes != (("deterministic",) if name == "plan_cost" else supported_replay)
            or authority != ("producer_report" if name == "solve" else "checker_attestation" if name == "check" else "none")
            or outcomes != _OPERATION_OUTCOMES[name]
            or (name in {"plan_cost", "explain"} and effects)
        ):
            _invalid(op_path, "operation ABI binding drift")
        operations[name] = {"component_id": component_id, "replay_modes": replay_modes, "effect_kinds": effects}
        operation_order.append(name)
    if operation_order != list(_OPERATIONS):
        _invalid(f"{path}.operations", "operation ABI order drift")

    lifecycle = _keys(value["lifecycle"], {"scope", "reentrant", "thread_safe", "maximum_concurrency", "state_persistence", "isolation", "initialization", "shutdown_timeout_us"}, f"{path}.lifecycle")
    reentrant = _boolean(lifecycle["reentrant"], f"{path}.lifecycle.reentrant")
    thread_safe = _boolean(lifecycle["thread_safe"], f"{path}.lifecycle.thread_safe")
    concurrency = _integer(lifecycle["maximum_concurrency"], f"{path}.lifecycle.maximum_concurrency", 10_000)
    if concurrency == 0 or ((not reentrant or not thread_safe) and concurrency != 1):
        _invalid(f"{path}.lifecycle.maximum_concurrency", "unsafe plugin concurrency drift")
    isolation = _text(lifecycle["isolation"], f"{path}.lifecycle.isolation")
    scope = _text(lifecycle["scope"], f"{path}.lifecycle.scope")
    state_persistence = _text(lifecycle["state_persistence"], f"{path}.lifecycle.state_persistence")
    initialization = _text(lifecycle["initialization"], f"{path}.lifecycle.initialization")
    shutdown_timeout = _integer(lifecycle["shutdown_timeout_us"], f"{path}.lifecycle.shutdown_timeout_us")
    if scope not in {"invocation", "session", "process"} or state_persistence not in {"none", "content_addressed"} or isolation not in {"in_process", "subprocess_required"} or initialization not in {"deterministic", "seeded"}:
        _invalid(f"{path}.lifecycle", "unknown lifecycle value")
    if scope == "invocation" and state_persistence != "none":
        _invalid(f"{path}.lifecycle.state_persistence", "invocation state cannot persist")
    if isolation == "subprocess_required" and shutdown_timeout == 0:
        _invalid(f"{path}.lifecycle.shutdown_timeout_us", "subprocess requires shutdown budget")
    if initialization == "seeded" and "seeded" not in supported_replay:
        _invalid(f"{path}.lifecycle.initialization", "seeded initialization is unavailable")
    if declared_effects & {"filesystem", "network", "process", "solver"} and isolation != "subprocess_required":
        _invalid(f"{path}.lifecycle.isolation", "external effects require isolation")

    seed_policy = _text(replay["seed_policy"], f"{path}.replay.seed_policy")
    expected_seed_policy = "explicit_required_when_seeded" if "seeded" in supported_replay else "forbidden"
    if seed_policy != expected_seed_policy:
        _invalid(f"{path}.replay.seed_policy", "seed policy and replay modes disagree")
    if replay["configuration_sha256"] != implementation["configuration_sha256"] or _sha(replay["descriptor_basis_sha256"], f"{path}.replay.descriptor_basis_sha256") != _descriptor_basis(value):
        _invalid(f"{path}.replay", "replay identity mismatch")
    if value["limits"] != _EXPECTED_PLUGIN_LIMITS:
        _invalid(f"{path}.limits", "plugin hard limits drift")
    if type(value["extensions"]) is not dict:
        _invalid(f"{path}.extensions", "extensions must be an object")
    identities = [producer["component_id"], checker["component_id"], *capability_ids]
    if len(identities) != len(set(identities)):
        _invalid(path, "component and capability IDs collide")
    return {
        "raw": value,
        "descriptor_sha256": _digest(data),
        "plugin_id": plugin_id,
        "plugin_version": version[3],
        "version_tuple": version[:3],
        "implementation_sha256": implementation["implementation_sha256"],
        "producer_component_id": producer["component_id"],
        "checker_component_id": checker["component_id"],
        "python_versions": python_versions,
        "platforms": platforms,
        "required_extensions": required_extensions,
        "optional_extensions": optional_extensions,
        "dependencies": tuple(dependencies),
        "capabilities": tuple(capabilities),
        "operations": operations,
        "declared_effects": tuple(sorted(declared_effects)),
        "supported_replay": supported_replay,
        "lifecycle_isolation": isolation,
    }


def _entry_mapping(value: CapabilityRegistryEntry, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "descriptor_sha256": value.descriptor_sha256, "plugin_id": value.plugin_id, "plugin_version": value.plugin_version, "implementation_sha256": value.implementation_sha256, "producer_component_id": value.producer_component_id, "checker_component_id": value.checker_component_id, "capability_ids": list(value.capability_ids), "dependency_descriptor_sha256s": list(value.dependency_descriptor_sha256s), "entry_sha256": value.entry_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _make_entry(plugin: dict[str, object]) -> CapabilityRegistryEntry:
    value: dict[str, object] = {"schema": ENTRY_SCHEMA, "descriptor_sha256": plugin["descriptor_sha256"], "plugin_id": plugin["plugin_id"], "plugin_version": plugin["plugin_version"], "implementation_sha256": plugin["implementation_sha256"], "producer_component_id": plugin["producer_component_id"], "checker_component_id": plugin["checker_component_id"], "capability_ids": [item["capability_id"] for item in plugin["capabilities"]], "dependency_descriptor_sha256s": sorted(item["descriptor_sha256"] for item in plugin["dependencies"]), "entry_sha256": None, "mathematical_authority": False}
    value["entry_sha256"] = _self_hash(value, "entry_sha256")
    return _make(CapabilityRegistryEntry, schema=ENTRY_SCHEMA, descriptor_sha256=value["descriptor_sha256"], plugin_id=value["plugin_id"], plugin_version=value["plugin_version"], implementation_sha256=value["implementation_sha256"], producer_component_id=value["producer_component_id"], checker_component_id=value["checker_component_id"], capability_ids=tuple(value["capability_ids"]), dependency_descriptor_sha256s=tuple(value["dependency_descriptor_sha256s"]), entry_sha256=value["entry_sha256"], mathematical_authority=False)


def _registry_mapping(value: CapabilityRegistry, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "descriptor_sha256s": list(value.descriptor_sha256s), "entries": [_entry_mapping(item) for item in value.entries], "dependency_order_sha256s": list(value.dependency_order_sha256s), "registry_sha256": value.registry_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _build_registry(descriptors: tuple[bytes, ...]) -> tuple[CapabilityRegistry, dict[str, dict[str, object]]]:
    if type(descriptors) is not tuple or len(descriptors) > MAX_DESCRIPTORS:
        raise _Exhausted("descriptors: descriptor count budget exceeded")
    total = 0
    unique: dict[str, bytes] = {}
    for index, data in enumerate(descriptors):
        if type(data) is not bytes or not data or len(data) > MAX_DESCRIPTOR_BYTES:
            _invalid(f"descriptors[{index}]", "invalid descriptor bytes")
        total += len(data)
        if total > MAX_AGGREGATE_DESCRIPTOR_BYTES:
            raise _Exhausted("descriptors: aggregate byte budget exceeded")
        unique.setdefault(_digest(data), data)
    plugins = {digest: _validate_descriptor(unique[digest], f"descriptors[{digest}]") for digest in sorted(unique)}
    logical_ids: dict[tuple[str, str], str] = {}
    component_ids: dict[str, str] = {}
    capability_ids: dict[str, str] = {}
    format_specs: dict[str, tuple[object, ...]] = {}
    for digest, plugin in plugins.items():
        logical = (plugin["plugin_id"], plugin["plugin_version"])
        if logical in logical_ids and logical_ids[logical] != digest:
            _invalid("descriptors", "plugin ID/version collision")
        logical_ids[logical] = digest
        for identifier in (plugin["producer_component_id"], plugin["checker_component_id"]):
            if identifier in component_ids and component_ids[identifier] != digest:
                _invalid("descriptors", "component identity collision")
            component_ids[identifier] = digest
        for capability in plugin["capabilities"]:
            identifier = capability["capability_id"]
            if identifier in capability_ids and capability_ids[identifier] != digest:
                _invalid("descriptors", "capability identity collision")
            capability_ids[identifier] = digest
            for field in ("evidence_formats", "certificate_formats"):
                for format_item in capability[field]:
                    spec = (format_item["major"], format_item["minor_minimum"], format_item["minor_maximum"], tuple(format_item["required_features"]))
                    format_id = format_item["format_id"]
                    if format_id in format_specs and format_specs[format_id] != spec:
                        _invalid("descriptors", "format identity collision")
                    format_specs[format_id] = spec
    graph: dict[str, tuple[str, ...]] = {}
    for digest, plugin in plugins.items():
        deps: list[str] = []
        for dependency in plugin["dependencies"]:
            target_digest = dependency["descriptor_sha256"]
            target = plugins.get(target_digest)
            if target is None or target["plugin_id"] != dependency["plugin_id"]:
                _invalid("descriptors", "required dependency is missing or substituted")
            minimum = _semver(dependency["version_minimum"], "dependency.minimum")[:3]
            maximum = _semver(dependency["version_maximum_exclusive"], "dependency.maximum")[:3]
            if not minimum <= target["version_tuple"] < maximum:
                _invalid("descriptors", "dependency version interval mismatch")
            deps.append(target_digest)
        graph[digest] = tuple(sorted(deps))
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []
    def visit(node: str) -> None:
        if node in visiting:
            _invalid("descriptors", "dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in graph[node]:
            visit(child)
        visiting.remove(node)
        visited.add(node)
        order.append(node)
    for digest in sorted(graph):
        visit(digest)
    entries = tuple(_make_entry(plugins[digest]) for digest in sorted(plugins))
    value: dict[str, object] = {"schema": REGISTRY_SCHEMA, "descriptor_sha256s": sorted(plugins), "entries": [_entry_mapping(item) for item in entries], "dependency_order_sha256s": order, "registry_sha256": None, "mathematical_authority": False}
    value["registry_sha256"] = _self_hash(value, "registry_sha256")
    registry = _make(CapabilityRegistry, schema=REGISTRY_SCHEMA, descriptor_sha256s=tuple(value["descriptor_sha256s"]), entries=entries, dependency_order_sha256s=tuple(order), registry_sha256=value["registry_sha256"], mathematical_authority=False)
    return registry, plugins


def _artifact_inventory(
    artifacts: tuple[bytes, ...],
    event_sha256s: tuple[str, ...],
    payload_sha256s: tuple[str, ...],
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    if type(artifacts) is not tuple or len(artifacts) > MAX_ARTIFACTS:
        raise _Exhausted("artifacts: artifact count budget exceeded")
    expected_events = set(event_sha256s)
    expected_payloads = set(payload_sha256s)
    if expected_events & expected_payloads:
        _invalid("artifacts", "event and payload identities overlap")
    events: dict[str, bytes] = {}
    payloads: dict[str, bytes] = {}
    raw_identities: set[str] = set()
    total = 0
    for index, data in enumerate(artifacts):
        if type(data) is not bytes or not data or len(data) > MAX_ARTIFACT_BYTES:
            _invalid(f"artifacts[{index}]", "invalid artifact bytes")
        total += len(data)
        if total > MAX_AGGREGATE_ARTIFACT_BYTES:
            raise _Exhausted("artifacts: aggregate byte budget exceeded")
        digest = _digest(data)
        if digest in raw_identities:
            _invalid(f"artifacts[{index}]", "duplicate artifact content")
        raw_identities.add(digest)
        if digest in expected_payloads:
            payloads[digest] = data
            continue
        event = _parse_json(data, f"artifacts[{index}]", MAX_ARTIFACT_BYTES)
        if event.get("schema") != "mathhead.problem-session-event.v1":
            _invalid(f"artifacts[{index}]", "surplus or unclassified artifact")
        event_sha256 = _sha(event.get("event_sha256"), f"artifacts[{index}].event_sha256")
        if event_sha256 != _self_hash(event, "event_sha256"):
            _invalid(f"artifacts[{index}].event_sha256", "session event identity mismatch")
        if event_sha256 not in expected_events or event_sha256 in events:
            _invalid(f"artifacts[{index}]", "surplus or duplicate session event")
        events[event_sha256] = data
    if set(events) != expected_events or set(payloads) != expected_payloads:
        _invalid("artifacts", "artifact inventory is incomplete")
    return events, payloads


def _load_current_obligation(request: CapabilityRouteRequest, artifacts: tuple[bytes, ...]) -> tuple[object, object]:
    event_inventory, payload_inventory = _artifact_inventory(
        artifacts,
        request.event_sha256s,
        request.session_artifact_sha256s,
    )
    events = tuple(event_inventory[digest] for digest in request.event_sha256s)
    payloads = tuple(payload_inventory[digest] for digest in request.session_artifact_sha256s)
    replay = transition_problem_session(None, events, payloads)
    if replay.status != "unchanged" or replay.revision_value is None:
        _invalid("artifacts", "problem session does not replay to one current head")
    revision = replay.revision_value
    if replay.session_id != request.session_id or replay.head_sha256 != request.session_head_sha256 or revision.context_sha256 != request.session_context_sha256:
        _invalid("request", "session/head/context binding mismatch")
    if request.normalization_result_sha256 not in revision.analysis_artifact_sha256s:
        _invalid("request.normalization_result_sha256", "normalization artifact is not current analysis")
    normalization_bytes = payload_inventory.get(request.normalization_result_sha256)
    obligation_bytes = payload_inventory.get(request.obligation_artifact_sha256)
    if normalization_bytes is None or obligation_bytes is None:
        _invalid("artifacts", "normalization or obligation artifact missing")
    try:
        normalization = parse_canonical_normalization_result(normalization_bytes)
    except (ValueError, TypeError) as exc:
        _invalid("normalization", f"invalid canonical-normalization result: {exc}")
    if normalization.status != "normalized":
        _invalid("normalization", "upstream result is not successful")
    if normalization.ambiguity_status != "unambiguous" or normalization.selected_reading_id is None:
        raise _Ambiguous("normalization reading is unresolved")
    if normalization.selected_reading_id != request.reading_id:
        _invalid("request.reading_id", "selected reading mismatch")
    candidate = next((item for item in normalization.candidates if item.reading_id == request.reading_id), None)
    if candidate is None:
        _invalid("request.reading_id", "candidate reading missing")
    obligation = next((item for item in candidate.obligations if item.semantic_sha256 == request.obligation_semantic_sha256), None)
    if obligation is None or obligation.reading_id != request.reading_id or obligation.local_context_semantic_sha256 != request.local_context_semantic_sha256:
        _invalid("request.obligation_semantic_sha256", "obligation/context binding mismatch")
    if _digest(canonical_obligation_bytes(obligation)) != request.obligation_artifact_sha256 or canonical_obligation_bytes(obligation) != obligation_bytes:
        _invalid("request.obligation_artifact_sha256", "canonical obligation bytes mismatch")
    session_obligation = next((item for item in revision.obligations if item.record_id == request.session_obligation_record_id), None)
    if session_obligation is None or session_obligation.obligation_sha256 != request.obligation_artifact_sha256 or session_obligation.context_sha256 != request.session_context_sha256 or session_obligation.reading_id != request.reading_id:
        _invalid("request.session_obligation_record_id", "session obligation is not exact/current")
    if session_obligation.state not in {"open", "reopened"}:
        _invalid("request.session_obligation_record_id", "session obligation is not routable")
    return candidate, _parse_json(
        obligation_bytes,
        "obligation",
        MAX_ARTIFACT_BYTES,
    )


def _namespaced_kind(prefix: str, kind: str) -> str:
    return f"org.mathhead.{prefix}.{kind.replace('_', '-')}"


def _domain_name(value: object) -> str | None:
    if type(value) is not dict:
        return None
    kind = value.get("kind")
    if kind == "builtin" and type(value.get("name")) is str:
        return value["name"]
    if kind == "modular":
        return "integer"
    if kind in {"collection", "set"}:
        return "set"
    if kind == "structure" and value.get("name") == "graph":
        return "graph"
    return None


def _walk_structural(value: object) -> tuple[set[str], set[str], set[str], int, int, int]:
    domains: set[str] = set()
    expressions: set[str] = set()
    relations: set[str] = set()
    quantifier_count = 0
    quantifier_depth = 0
    expression_nodes = 0
    stack: list[tuple[object, int]] = [(value, 0)]
    while stack:
        item, qdepth = stack.pop()
        if type(item) is list:
            stack.extend((child, qdepth) for child in reversed(item))
            continue
        if type(item) is not dict:
            continue
        domain = item.get("domain")
        named_domain = _domain_name(domain)
        if named_domain is not None:
            domains.add(named_domain)
        kind = item.get("kind")
        if kind == "quantified":
            quantifier_count += 1
            qdepth += 1
            quantifier_depth = max(quantifier_depth, qdepth)
        if kind == "relation" and type(item.get("relation")) is dict:
            relation_kind = item["relation"].get("kind")
            if type(relation_kind) is str:
                relations.add(_namespaced_kind("relation", relation_kind))
        elif type(kind) is str and ("operands" in item or kind in {"equal", "not_equal", "less", "less_equal", "greater", "greater_equal", "member", "not_member", "divides", "congruent"}):
            relations.add(_namespaced_kind("relation", kind))
        elif type(kind) is str and ("variable" in item or "arguments" in item or "operands" in item or kind in {"literal", "variable", "apply", "add", "multiply", "power", "negate"}):
            expressions.add(_namespaced_kind("expression", kind))
            expression_nodes += 1
        stack.extend((child, qdepth) for child in reversed(tuple(item.values())))
    return domains, expressions, relations, quantifier_count, quantifier_depth, expression_nodes


def _polynomial_degree(value: object) -> int:
    if type(value) is not dict:
        return 0
    kind = value.get("kind")
    if kind == "variable":
        return 1
    if kind in {"literal", "integer", "rational"}:
        return 0
    if kind in {"add", "subtract", "negate"}:
        children = value.get("operands", value.get("arguments", []))
        return max((_polynomial_degree(item) for item in children), default=0) if type(children) is list else 0
    if kind in {"multiply", "product"}:
        children = value.get("operands", value.get("arguments", []))
        if type(children) is list:
            total = sum(_polynomial_degree(item) for item in children)
            return min(total, MAX_INTEGER)
    if kind == "power":
        base = value.get("base")
        exponent = value.get("exponent")
        if type(exponent) is int and not isinstance(exponent, bool) and exponent >= 0:
            return min(_polynomial_degree(base) * exponent, MAX_INTEGER)
    degrees = [_polynomial_degree(item) for item in value.values()]
    return max(degrees, default=0)


def _fragment_mapping(value: CapabilityFragment, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "theories": list(value.theories), "domains": list(value.domains), "quantifiers": list(value.quantifiers), "expression_kinds": list(value.expression_kinds), "relation_kinds": list(value.relation_kinds), "polynomial_degree": value.polynomial_degree, "quantifier_count": value.quantifier_count, "quantifier_depth": value.quantifier_depth, "variables": value.variables, "expression_nodes": value.expression_nodes, "goals": value.goals, "ambiguous": value.ambiguous, "exact_arithmetic": value.exact_arithmetic, "theory_features": list(value.theory_features), "fragment_sha256": value.fragment_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _derive_fragment(candidate: object, obligation: object) -> CapabilityFragment:
    if type(obligation) is not dict:
        _invalid("obligation", "canonical obligation projection is not an object")
    dependencies = set(obligation["dependency_semantic_sha256s"]) | {
        obligation["statement_semantic_sha256"],
        obligation["local_context_semantic_sha256"],
    }
    forms = [item for item in candidate.normal_forms if item.semantic_sha256 in dependencies]
    domains: set[str] = set()
    expressions: set[str] = set()
    relations: set[str] = set()
    quantifiers: set[str] = set()
    variables: set[str] = set()
    quantifier_count = 0
    quantifier_depth = 0
    expression_nodes = 0
    polynomial_degree = 0
    for form in forms:
        form_mapping = _parse_json(
            canonical_normal_form_bytes(form),
            "normalization.normal_form",
            MAX_ARTIFACT_BYTES,
        )
        form_value = form_mapping["value"]
        found_domains, found_expressions, found_relations, count, depth, nodes = _walk_structural(form_value)
        domains.update(found_domains)
        expressions.update(found_expressions)
        relations.update(found_relations)
        quantifier_count = max(quantifier_count, count)
        quantifier_depth = max(quantifier_depth, depth)
        expression_nodes += nodes if form.form_kind == "expression" else 0
        if form.form_kind == "variable":
            variables.add(form.semantic_sha256)
        if form.form_kind == "expression":
            polynomial_degree = max(polynomial_degree, _polynomial_degree(form_value))
        if type(form_value) is dict and form_value.get("kind") == "quantified" and type(form_value.get("quantifier")) is str:
            quantifiers.add(form_value["quantifier"])
    statement_normal_form = obligation["statement_normal_form"]
    statement_domains, statement_expressions, statement_relations, count, depth, nodes = _walk_structural(statement_normal_form)
    domains.update(statement_domains)
    expressions.update(statement_expressions)
    relations.update(statement_relations)
    quantifier_count = max(quantifier_count, count)
    quantifier_depth = max(quantifier_depth, depth)
    expression_nodes = max(expression_nodes, nodes)
    polynomial_degree = max(polynomial_degree, _polynomial_degree(statement_normal_form))
    if not quantifiers:
        stack = [statement_normal_form]
        while stack:
            item = stack.pop()
            if type(item) is dict:
                if item.get("kind") == "quantified" and type(item.get("quantifier")) is str:
                    quantifiers.add(item["quantifier"])
                stack.extend(item.values())
            elif type(item) is list:
                stack.extend(item)
    if not quantifiers:
        quantifiers.add("none")
    theories = {_DOMAIN_THEORIES.get(item, f"org.mathhead.theory.{item.replace('_', '-')}") for item in domains}
    if not theories:
        theories.add("org.mathhead.theory.logic")
    features = set(theories)
    exact = bool(domains) and domains <= _EXACT_DOMAINS
    if exact:
        features.add("org.mathhead.feature.exact-arithmetic")
    if obligation["supported"] is not True:
        features.add("org.mathhead.feature.unsupported")
    value: dict[str, object] = {"schema": FRAGMENT_SCHEMA, "theories": sorted(theories), "domains": sorted(domains), "quantifiers": sorted(quantifiers), "expression_kinds": sorted(expressions), "relation_kinds": sorted(relations), "polynomial_degree": polynomial_degree, "quantifier_count": quantifier_count, "quantifier_depth": quantifier_depth, "variables": len(variables), "expression_nodes": expression_nodes, "goals": 1, "ambiguous": False, "exact_arithmetic": exact, "theory_features": sorted(features), "fragment_sha256": None, "mathematical_authority": False}
    value["fragment_sha256"] = _self_hash(value, "fragment_sha256")
    return _make(CapabilityFragment, schema=FRAGMENT_SCHEMA, theories=tuple(value["theories"]), domains=tuple(value["domains"]), quantifiers=tuple(value["quantifiers"]), expression_kinds=tuple(value["expression_kinds"]), relation_kinds=tuple(value["relation_kinds"]), polynomial_degree=polynomial_degree, quantifier_count=quantifier_count, quantifier_depth=quantifier_depth, variables=len(variables), expression_nodes=expression_nodes, goals=1, ambiguous=False, exact_arithmetic=exact, theory_features=tuple(value["theory_features"]), fragment_sha256=value["fragment_sha256"], mathematical_authority=False)


def _format_matches(supported: tuple[dict[str, object], ...], requested: object | None) -> bool:
    if requested is None:
        return True
    request = _thaw_json(requested)
    assert type(request) is dict
    for item in supported:
        if item["format_id"] == request["format_id"] and item["major"] == request["major"] and item["minor_minimum"] <= request["minor"] <= item["minor_maximum"] and set(item["required_features"]) <= set(request["required_features"]):
            return True
    return False


def _incompatibility_reasons(plugin: dict[str, object], capability: dict[str, object], request: CapabilityRouteRequest, fragment: CapabilityFragment) -> tuple[str, ...]:
    reasons: set[str] = set()
    supported = capability["fragment"]
    if "org.mathhead.feature.unsupported" in fragment.theory_features:
        reasons.add("FEATURE_FORBIDDEN")
    if capability["kind"] != request.capability_kind:
        reasons.add("CAPABILITY_KIND_MISMATCH")
    if request.capability_kind not in _OPERATION_KINDS[request.operation] or request.operation not in plugin["operations"]:
        reasons.add("OPERATION_MISMATCH")
    if not set(fragment.theories) <= set(capability["theories"]):
        reasons.add("THEORY_MISMATCH")
    if not set(fragment.domains) <= set(supported["domains"]):
        reasons.add("DOMAIN_MISMATCH")
    if not set(fragment.quantifiers) <= set(supported["quantifiers"]):
        reasons.add("QUANTIFIER_MISMATCH")
    if not set(fragment.expression_kinds) <= set(supported["expression_kinds"]):
        reasons.add("EXPRESSION_KIND_MISMATCH")
    if not set(fragment.relation_kinds) <= set(supported["relation_kinds"]):
        reasons.add("RELATION_KIND_MISMATCH")
    if fragment.polynomial_degree > supported["maximum_polynomial_degree"] or fragment.quantifier_depth > supported["maximum_quantifier_depth"] or fragment.variables > supported["maximum_variables"]:
        reasons.add("LIMIT_EXCEEDED")
    if fragment.ambiguous and not supported["supports_ambiguity"]:
        reasons.add("AMBIGUITY_UNSUPPORTED")
    if supported["requires_exact_arithmetic"] and not fragment.exact_arithmetic:
        reasons.add("ARITHMETIC_MISMATCH")
    if not set(supported["required_theory_features"]) <= set(fragment.theory_features):
        reasons.add("FEATURE_REQUIRED")
    if set(supported["forbidden_theory_features"]) & set(fragment.theory_features):
        reasons.add("FEATURE_FORBIDDEN")
    if not _format_matches(capability["evidence_formats"], request.evidence_format):
        reasons.add("EVIDENCE_FORMAT_MISMATCH")
    if not _format_matches(capability["certificate_formats"], request.certificate_format):
        reasons.add("CERTIFICATE_FORMAT_MISMATCH")
    availability = request.availability
    if plugin["descriptor_sha256"] not in availability.available_descriptor_sha256s:
        reasons.add("LIFECYCLE_UNAVAILABLE")
    if availability.platform not in plugin["platforms"]:
        reasons.add("PLATFORM_UNAVAILABLE")
    if availability.python_version not in plugin["python_versions"]:
        reasons.add("PYTHON_VERSION_UNAVAILABLE")
    if not set(plugin["required_extensions"]) <= set(availability.extension_ids):
        reasons.add("EXTENSION_UNAVAILABLE")
    operation = plugin["operations"].get(request.operation)
    if operation is not None:
        if not set(operation["effect_kinds"]) <= set(availability.allowed_effects):
            reasons.add("EFFECT_FORBIDDEN")
        if request.replay_mode not in operation["replay_modes"] or request.replay_mode not in plugin["supported_replay"] or request.replay_mode not in availability.replay_modes:
            reasons.add("REPLAY_MODE_UNAVAILABLE")
    dependency_hashes = {item["descriptor_sha256"] for item in plugin["dependencies"]}
    if not dependency_hashes <= set(availability.available_descriptor_sha256s):
        reasons.add("DEPENDENCY_UNAVAILABLE")
    return tuple(code for code in _REASON_CODES if code in reasons)


def _cost_mapping(value: CapabilityCostDerivation, *, own_hash: bool = True) -> dict[str, object]:
    return {item.name: (getattr(value, item.name) if item.name != "cost_sha256" or own_hash else None) for item in fields(value)}


def _derive_cost(model: dict[str, int], fragment: CapabilityFragment) -> CapabilityCostDerivation:
    terms = {"base": model["base"], "variable_term": model["per_variable"] * fragment.variables, "expression_node_term": model["per_expression_node"] * fragment.expression_nodes, "quantifier_term": model["per_quantifier"] * fragment.quantifier_count, "goal_term": model["per_goal"] * fragment.goals, "ambiguity_term": model["ambiguity_surcharge"] if fragment.ambiguous else 0}
    if any(value > MAX_INTEGER for value in terms.values()):
        _invalid("cost", "cost term exceeds portable range")
    total = sum(terms.values())
    if total > MAX_INTEGER:
        _invalid("cost", "cost total exceeds portable range")
    value: dict[str, object] = {"schema": COST_SCHEMA, **terms, "unsaturated_total": total, "maximum": model["maximum"], "estimated_cost": min(total, model["maximum"]), "saturated": total > model["maximum"], "confidence_ppm": model["confidence_ppm"], "cost_sha256": None, "mathematical_authority": False}
    value["cost_sha256"] = _self_hash(value, "cost_sha256")
    return _make(CapabilityCostDerivation, **value)


def _candidate_mapping(value: CapabilityCandidate, *, own_hash: bool = True) -> dict[str, object]:
    result = {item.name: getattr(value, item.name) for item in fields(value)}
    result["dependency_descriptor_sha256s"] = list(value.dependency_descriptor_sha256s)
    result["evidence_format"] = _thaw_json(value.evidence_format)
    result["certificate_format"] = _thaw_json(value.certificate_format)
    result["effect_kinds"] = list(value.effect_kinds)
    result["cost"] = _cost_mapping(value.cost)
    if not own_hash:
        result["candidate_sha256"] = None
    return result


def _make_candidate(plugin: dict[str, object], capability: dict[str, object], operation: dict[str, object], request: CapabilityRouteRequest, registry: CapabilityRegistry, fragment: CapabilityFragment) -> CapabilityCandidate:
    cost = _derive_cost(capability["cost_model"], fragment)
    value: dict[str, object] = {"schema": CANDIDATE_SCHEMA, "registry_sha256": registry.registry_sha256, "request_sha256": request.request_sha256, "availability_sha256": request.availability.availability_sha256, "descriptor_sha256": plugin["descriptor_sha256"], "plugin_id": plugin["plugin_id"], "plugin_version": plugin["plugin_version"], "capability_id": capability["capability_id"], "capability_kind": capability["kind"], "operation": request.operation, "component_id": operation["component_id"], "producer_component_id": plugin["producer_component_id"], "checker_component_id": plugin["checker_component_id"], "session_head_sha256": request.session_head_sha256, "session_context_sha256": request.session_context_sha256, "normalization_result_sha256": request.normalization_result_sha256, "obligation_semantic_sha256": request.obligation_semantic_sha256, "fragment_sha256": fragment.fragment_sha256, "dependency_descriptor_sha256s": sorted(item["descriptor_sha256"] for item in plugin["dependencies"]), "evidence_format": _thaw_json(request.evidence_format), "certificate_format": _thaw_json(request.certificate_format), "effect_kinds": list(operation["effect_kinds"]), "replay_mode": request.replay_mode, "priority": capability["priority"], "cost": _cost_mapping(cost), "candidate_sha256": None, "mathematical_authority": False}
    value["candidate_sha256"] = _self_hash(value, "candidate_sha256")
    return _make(CapabilityCandidate, schema=CANDIDATE_SCHEMA, registry_sha256=registry.registry_sha256, request_sha256=request.request_sha256, availability_sha256=request.availability.availability_sha256, descriptor_sha256=plugin["descriptor_sha256"], plugin_id=plugin["plugin_id"], plugin_version=plugin["plugin_version"], capability_id=capability["capability_id"], capability_kind=capability["kind"], operation=request.operation, component_id=operation["component_id"], producer_component_id=plugin["producer_component_id"], checker_component_id=plugin["checker_component_id"], session_head_sha256=request.session_head_sha256, session_context_sha256=request.session_context_sha256, normalization_result_sha256=request.normalization_result_sha256, obligation_semantic_sha256=request.obligation_semantic_sha256, fragment_sha256=fragment.fragment_sha256, dependency_descriptor_sha256s=tuple(value["dependency_descriptor_sha256s"]), evidence_format=_freeze_json(value["evidence_format"]), certificate_format=_freeze_json(value["certificate_format"]), effect_kinds=tuple(value["effect_kinds"]), replay_mode=request.replay_mode, priority=capability["priority"], cost=cost, candidate_sha256=value["candidate_sha256"], mathematical_authority=False)


def _incompatibility_mapping(value: CapabilityIncompatibility, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "descriptor_sha256": value.descriptor_sha256, "plugin_id": value.plugin_id, "plugin_version": value.plugin_version, "capability_id": value.capability_id, "capability_kind": value.capability_kind, "operation": value.operation, "reason_codes": list(value.reason_codes), "incompatibility_sha256": value.incompatibility_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _make_incompatibility(plugin: dict[str, object], capability: dict[str, object], request: CapabilityRouteRequest, reasons: tuple[str, ...]) -> CapabilityIncompatibility:
    value: dict[str, object] = {"schema": INCOMPATIBILITY_SCHEMA, "descriptor_sha256": plugin["descriptor_sha256"], "plugin_id": plugin["plugin_id"], "plugin_version": plugin["plugin_version"], "capability_id": capability["capability_id"], "capability_kind": capability["kind"], "operation": request.operation, "reason_codes": list(reasons), "incompatibility_sha256": None, "mathematical_authority": False}
    value["incompatibility_sha256"] = _self_hash(value, "incompatibility_sha256")
    return _make(CapabilityIncompatibility, schema=INCOMPATIBILITY_SCHEMA, descriptor_sha256=plugin["descriptor_sha256"], plugin_id=plugin["plugin_id"], plugin_version=plugin["plugin_version"], capability_id=capability["capability_id"], capability_kind=capability["kind"], operation=request.operation, reason_codes=reasons, incompatibility_sha256=value["incompatibility_sha256"], mathematical_authority=False)


def _result_mapping(value: CapabilityRouteResult, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "contract_id": value.contract_id, "contract_sha256": value.contract_sha256, "theory_plugin_contract_sha256": value.theory_plugin_contract_sha256, "canonical_normalization_contract_sha256": value.canonical_normalization_contract_sha256, "problem_session_contract_sha256": value.problem_session_contract_sha256, "status": value.status, "reason_code": value.reason_code, "diagnostic": value.diagnostic, "request_sha256": value.request_sha256, "registry": _registry_mapping(value.registry) if value.registry is not None else None, "fragment": _fragment_mapping(value.fragment) if value.fragment is not None else None, "candidates": [_candidate_mapping(item) for item in value.candidates], "incompatibilities": [_incompatibility_mapping(item) for item in value.incompatibilities], "selected_candidate_sha256": value.selected_candidate_sha256, "result_sha256": value.result_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _entry_from_mapping(value: object, path: str) -> CapabilityRegistryEntry:
    item = _keys(value, {"schema", "descriptor_sha256", "plugin_id", "plugin_version", "implementation_sha256", "producer_component_id", "checker_component_id", "capability_ids", "dependency_descriptor_sha256s", "entry_sha256", "mathematical_authority"}, path)
    if item["schema"] != ENTRY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "registry entry schema or authority drift")
    capability_ids = _string_tuple(item["capability_ids"], f"{path}.capability_ids", pattern=_ID, maximum=10_000, require_nonempty=True)
    dependencies = _string_tuple(item["dependency_descriptor_sha256s"], f"{path}.dependency_descriptor_sha256s", pattern=_DIGEST, maximum=MAX_DESCRIPTORS)
    identity = _sha(item["entry_sha256"], f"{path}.entry_sha256")
    if identity != _self_hash(item, "entry_sha256"):
        _invalid(f"{path}.entry_sha256", "registry entry identity mismatch")
    return _make(CapabilityRegistryEntry, schema=ENTRY_SCHEMA, descriptor_sha256=_sha(item["descriptor_sha256"], f"{path}.descriptor_sha256"), plugin_id=_text(item["plugin_id"], f"{path}.plugin_id", pattern=_NAMESPACED, maximum=255), plugin_version=_semver(item["plugin_version"], f"{path}.plugin_version")[3], implementation_sha256=_sha(item["implementation_sha256"], f"{path}.implementation_sha256"), producer_component_id=_text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64), checker_component_id=_text(item["checker_component_id"], f"{path}.checker_component_id", pattern=_ID, maximum=64), capability_ids=capability_ids, dependency_descriptor_sha256s=dependencies, entry_sha256=identity, mathematical_authority=False)


def _registry_from_mapping(value: object, path: str) -> CapabilityRegistry:
    item = _keys(value, {"schema", "descriptor_sha256s", "entries", "dependency_order_sha256s", "registry_sha256", "mathematical_authority"}, path)
    if item["schema"] != REGISTRY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "registry schema or authority drift")
    descriptors = _string_tuple(item["descriptor_sha256s"], f"{path}.descriptor_sha256s", pattern=_DIGEST, maximum=MAX_DESCRIPTORS)
    raw_entries = item["entries"]
    if type(raw_entries) is not list or len(raw_entries) > MAX_DESCRIPTORS:
        _invalid(f"{path}.entries", "invalid registry entries")
    entries = tuple(_entry_from_mapping(entry, f"{path}.entries[{index}]") for index, entry in enumerate(raw_entries))
    if tuple(entry.descriptor_sha256 for entry in entries) != descriptors:
        _invalid(path, "registry entries do not exactly project descriptors")
    dependency_order = _string_tuple(item["dependency_order_sha256s"], f"{path}.dependency_order_sha256s", pattern=_DIGEST, maximum=MAX_DESCRIPTORS, preserve_order=True)
    if set(dependency_order) != set(descriptors):
        _invalid(f"{path}.dependency_order_sha256s", "dependency order is not a descriptor permutation")
    positions = {digest: index for index, digest in enumerate(dependency_order)}
    for entry in entries:
        if any(dependency not in positions or positions[dependency] >= positions[entry.descriptor_sha256] for dependency in entry.dependency_descriptor_sha256s):
            _invalid(f"{path}.dependency_order_sha256s", "dependency order violates closure")
    identity = _sha(item["registry_sha256"], f"{path}.registry_sha256")
    if identity != _self_hash(item, "registry_sha256"):
        _invalid(f"{path}.registry_sha256", "registry identity mismatch")
    return _make(CapabilityRegistry, schema=REGISTRY_SCHEMA, descriptor_sha256s=descriptors, entries=entries, dependency_order_sha256s=dependency_order, registry_sha256=identity, mathematical_authority=False)


def _fragment_from_mapping(value: object, path: str) -> CapabilityFragment:
    item = _keys(value, {"schema", "theories", "domains", "quantifiers", "expression_kinds", "relation_kinds", "polynomial_degree", "quantifier_count", "quantifier_depth", "variables", "expression_nodes", "goals", "ambiguous", "exact_arithmetic", "theory_features", "fragment_sha256", "mathematical_authority"}, path)
    if item["schema"] != FRAGMENT_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "fragment schema or authority drift")
    theories = _string_tuple(item["theories"], f"{path}.theories", pattern=_NAMESPACED, require_nonempty=True)
    domains = _string_tuple(item["domains"], f"{path}.domains", choices=tuple(sorted(_DOMAIN_THEORIES)))
    quantifiers = _string_tuple(item["quantifiers"], f"{path}.quantifiers", choices=("exists", "forall", "mixed", "none"), require_nonempty=True)
    expressions = _string_tuple(item["expression_kinds"], f"{path}.expression_kinds", pattern=_NAMESPACED)
    relations = _string_tuple(item["relation_kinds"], f"{path}.relation_kinds", pattern=_NAMESPACED)
    features = _string_tuple(item["theory_features"], f"{path}.theory_features", pattern=_NAMESPACED)
    quantities = {field: _integer(item[field], f"{path}.{field}") for field in ("polynomial_degree", "quantifier_count", "quantifier_depth", "variables", "expression_nodes", "goals")}
    if quantities["goals"] == 0:
        _invalid(f"{path}.goals", "fragment must contain a goal")
    ambiguous = _boolean(item["ambiguous"], f"{path}.ambiguous")
    exact = _boolean(item["exact_arithmetic"], f"{path}.exact_arithmetic")
    identity = _sha(item["fragment_sha256"], f"{path}.fragment_sha256")
    if identity != _self_hash(item, "fragment_sha256"):
        _invalid(f"{path}.fragment_sha256", "fragment identity mismatch")
    return _make(CapabilityFragment, schema=FRAGMENT_SCHEMA, theories=theories, domains=domains, quantifiers=quantifiers, expression_kinds=expressions, relation_kinds=relations, polynomial_degree=quantities["polynomial_degree"], quantifier_count=quantities["quantifier_count"], quantifier_depth=quantities["quantifier_depth"], variables=quantities["variables"], expression_nodes=quantities["expression_nodes"], goals=quantities["goals"], ambiguous=ambiguous, exact_arithmetic=exact, theory_features=features, fragment_sha256=identity, mathematical_authority=False)


def _cost_from_mapping(value: object, path: str) -> CapabilityCostDerivation:
    item = _keys(value, {"schema", "base", "variable_term", "expression_node_term", "quantifier_term", "goal_term", "ambiguity_term", "unsaturated_total", "maximum", "estimated_cost", "saturated", "confidence_ppm", "cost_sha256", "mathematical_authority"}, path)
    if item["schema"] != COST_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "cost schema or authority drift")
    quantity_names = ("base", "variable_term", "expression_node_term", "quantifier_term", "goal_term", "ambiguity_term", "unsaturated_total", "maximum", "estimated_cost")
    quantities = {field: _integer(item[field], f"{path}.{field}") for field in quantity_names}
    total = sum(quantities[field] for field in ("base", "variable_term", "expression_node_term", "quantifier_term", "goal_term", "ambiguity_term"))
    if total > MAX_INTEGER or quantities["unsaturated_total"] != total or quantities["estimated_cost"] != min(total, quantities["maximum"]):
        _invalid(path, "cost arithmetic drift")
    saturated = _boolean(item["saturated"], f"{path}.saturated")
    if saturated != (total > quantities["maximum"]):
        _invalid(f"{path}.saturated", "cost saturation drift")
    confidence = _integer(item["confidence_ppm"], f"{path}.confidence_ppm", 1_000_000)
    if confidence == 0:
        _invalid(f"{path}.confidence_ppm", "confidence must be positive")
    identity = _sha(item["cost_sha256"], f"{path}.cost_sha256")
    if identity != _self_hash(item, "cost_sha256"):
        _invalid(f"{path}.cost_sha256", "cost identity mismatch")
    return _make(CapabilityCostDerivation, schema=COST_SCHEMA, **quantities, saturated=saturated, confidence_ppm=confidence, cost_sha256=identity, mathematical_authority=False)


def _candidate_from_mapping(value: object, path: str) -> CapabilityCandidate:
    expected = {item.name for item in fields(CapabilityCandidate)}
    item = _keys(value, expected, path)
    if item["schema"] != CANDIDATE_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "candidate schema or authority drift")
    kind = _text(item["capability_kind"], f"{path}.capability_kind")
    operation = _text(item["operation"], f"{path}.operation")
    replay_mode = _text(item["replay_mode"], f"{path}.replay_mode")
    if kind not in _KINDS or operation not in _OPERATIONS or kind not in _OPERATION_KINDS[operation] or replay_mode not in _REPLAY_MODES:
        _invalid(path, "candidate kind, operation, or replay drift")
    dependencies = _string_tuple(item["dependency_descriptor_sha256s"], f"{path}.dependency_descriptor_sha256s", pattern=_DIGEST, maximum=MAX_DESCRIPTORS)
    effects = _string_tuple(item["effect_kinds"], f"{path}.effect_kinds", choices=_EFFECTS, maximum=5)
    evidence = _mapping_from_format(item["evidence_format"], f"{path}.evidence_format")
    certificate = _mapping_from_format(item["certificate_format"], f"{path}.certificate_format")
    cost = _cost_from_mapping(item["cost"], f"{path}.cost")
    identity = _sha(item["candidate_sha256"], f"{path}.candidate_sha256")
    if identity != _self_hash(item, "candidate_sha256"):
        _invalid(f"{path}.candidate_sha256", "candidate identity mismatch")
    return _make(CapabilityCandidate, schema=CANDIDATE_SCHEMA, registry_sha256=_sha(item["registry_sha256"], f"{path}.registry_sha256"), request_sha256=_sha(item["request_sha256"], f"{path}.request_sha256"), availability_sha256=_sha(item["availability_sha256"], f"{path}.availability_sha256"), descriptor_sha256=_sha(item["descriptor_sha256"], f"{path}.descriptor_sha256"), plugin_id=_text(item["plugin_id"], f"{path}.plugin_id", pattern=_NAMESPACED, maximum=255), plugin_version=_semver(item["plugin_version"], f"{path}.plugin_version")[3], capability_id=_text(item["capability_id"], f"{path}.capability_id", pattern=_ID, maximum=64), capability_kind=kind, operation=operation, component_id=_text(item["component_id"], f"{path}.component_id", pattern=_ID, maximum=64), producer_component_id=_text(item["producer_component_id"], f"{path}.producer_component_id", pattern=_ID, maximum=64), checker_component_id=_text(item["checker_component_id"], f"{path}.checker_component_id", pattern=_ID, maximum=64), session_head_sha256=_sha(item["session_head_sha256"], f"{path}.session_head_sha256"), session_context_sha256=_sha(item["session_context_sha256"], f"{path}.session_context_sha256"), normalization_result_sha256=_sha(item["normalization_result_sha256"], f"{path}.normalization_result_sha256"), obligation_semantic_sha256=_sha(item["obligation_semantic_sha256"], f"{path}.obligation_semantic_sha256"), fragment_sha256=_sha(item["fragment_sha256"], f"{path}.fragment_sha256"), dependency_descriptor_sha256s=dependencies, evidence_format=_freeze_json(evidence), certificate_format=_freeze_json(certificate), effect_kinds=effects, replay_mode=replay_mode, priority=_integer(item["priority"], f"{path}.priority"), cost=cost, candidate_sha256=identity, mathematical_authority=False)


def _incompatibility_from_mapping(value: object, path: str) -> CapabilityIncompatibility:
    item = _keys(value, {"schema", "descriptor_sha256", "plugin_id", "plugin_version", "capability_id", "capability_kind", "operation", "reason_codes", "incompatibility_sha256", "mathematical_authority"}, path)
    if item["schema"] != INCOMPATIBILITY_SCHEMA or item["mathematical_authority"] is not False:
        _invalid(path, "incompatibility schema or authority drift")
    kind = _text(item["capability_kind"], f"{path}.capability_kind")
    operation = _text(item["operation"], f"{path}.operation")
    if kind not in _KINDS or operation not in _OPERATIONS:
        _invalid(path, "incompatibility kind or operation drift")
    reasons = _string_tuple(item["reason_codes"], f"{path}.reason_codes", choices=_REASON_CODES, maximum=len(_REASON_CODES), require_nonempty=True)
    identity = _sha(item["incompatibility_sha256"], f"{path}.incompatibility_sha256")
    if identity != _self_hash(item, "incompatibility_sha256"):
        _invalid(f"{path}.incompatibility_sha256", "incompatibility identity mismatch")
    return _make(CapabilityIncompatibility, schema=INCOMPATIBILITY_SCHEMA, descriptor_sha256=_sha(item["descriptor_sha256"], f"{path}.descriptor_sha256"), plugin_id=_text(item["plugin_id"], f"{path}.plugin_id", pattern=_NAMESPACED, maximum=255), plugin_version=_semver(item["plugin_version"], f"{path}.plugin_version")[3], capability_id=_text(item["capability_id"], f"{path}.capability_id", pattern=_ID, maximum=64), capability_kind=kind, operation=operation, reason_codes=reasons, incompatibility_sha256=identity, mathematical_authority=False)


def _validate_result_structure(value: CapabilityRouteResult) -> None:
    if value.status in {"invalid", "exhausted"}:
        if any((value.request_sha256, value.registry, value.fragment, value.candidates, value.incompatibilities, value.selected_candidate_sha256, value.result_sha256)):
            _invalid("$", "failure result contains partial state")
        return
    if value.result_sha256 != _digest(_canonical_bytes(_result_mapping(value, own_hash=False))):
        _invalid("$.result_sha256", "result identity mismatch")
    if value.registry is None:
        if value.status != "ambiguous" or any((value.request_sha256, value.fragment, value.candidates, value.incompatibilities, value.selected_candidate_sha256)):
            _invalid("$.registry", "structural result lacks registry")
        return
    if value.request_sha256 is None or value.fragment is None:
        _invalid("$", "retained registry lacks request or fragment")
    entry_by_descriptor = {entry.descriptor_sha256: entry for entry in value.registry.entries}
    projected_ids: list[str] = []
    for candidate in value.candidates:
        entry = entry_by_descriptor.get(candidate.descriptor_sha256)
        if entry is None or candidate.capability_id not in entry.capability_ids or candidate.registry_sha256 != value.registry.registry_sha256 or candidate.request_sha256 != value.request_sha256 or candidate.fragment_sha256 != value.fragment.fragment_sha256 or candidate.producer_component_id != entry.producer_component_id or candidate.checker_component_id != entry.checker_component_id or candidate.dependency_descriptor_sha256s != entry.dependency_descriptor_sha256s:
            _invalid("$.candidates", "candidate registry/request/fragment projection drift")
        projected_ids.append(candidate.capability_id)
    for incompatibility in value.incompatibilities:
        entry = entry_by_descriptor.get(incompatibility.descriptor_sha256)
        if entry is None or incompatibility.capability_id not in entry.capability_ids:
            _invalid("$.incompatibilities", "incompatibility registry projection drift")
        projected_ids.append(incompatibility.capability_id)
    expected_ids = sorted(identifier for entry in value.registry.entries for identifier in entry.capability_ids)
    if sorted(projected_ids) != expected_ids or len(projected_ids) != len(set(projected_ids)):
        _invalid("$", "candidate and incompatibility projections are incomplete or overlapping")
    ordering = tuple(sorted(value.candidates, key=lambda item: (item.cost.estimated_cost, -item.priority, item.capability_id, item.plugin_id, _semver_rank(item.plugin_version, "candidate.plugin_version"))))
    if value.candidates != ordering:
        _invalid("$.candidates", "candidate order drift")
    incompatibility_order = tuple(sorted(value.incompatibilities, key=lambda item: (item.descriptor_sha256, item.capability_id, item.reason_codes)))
    if value.incompatibilities != incompatibility_order:
        _invalid("$.incompatibilities", "incompatibility order drift")
    if value.status == "routed":
        if value.reason_code != "ROUTED" or not value.candidates or value.selected_candidate_sha256 != value.candidates[0].candidate_sha256:
            _invalid("$", "routed selection mismatch")
    elif value.status == "unsupported":
        if value.reason_code != "NO_COMPATIBLE_CAPABILITY" or value.candidates or value.selected_candidate_sha256 is not None:
            _invalid("$", "unsupported result drift")
    elif value.status == "ambiguous":
        if value.reason_code != "NON_UNIQUE_SELECTION" or value.selected_candidate_sha256 is not None or len(value.candidates) < 2:
            _invalid("$", "selection ambiguity drift")
    else:
        _invalid("$.status", "unknown retained result status")


def _result_from_mapping(item: dict[str, object]) -> CapabilityRouteResult:
    expected = {item.name for item in fields(CapabilityRouteResult)}
    _keys(item, expected, "$")
    if item["schema"] != RESULT_SCHEMA or item["contract_id"] != CONTRACT_ID or item["contract_sha256"] != CONTRACT_SHA256 or item["theory_plugin_contract_sha256"] != THEORY_PLUGIN_CONTRACT_SHA256 or item["canonical_normalization_contract_sha256"] != CANONICAL_NORMALIZATION_CONTRACT_SHA256 or item["problem_session_contract_sha256"] != PROBLEM_SESSION_CONTRACT_SHA256 or item["mathematical_authority"] is not False:
        _invalid("$", "result contract binding drift")
    status = _text(item["status"], "$.status")
    if status not in {"routed", "unsupported", "ambiguous", "invalid", "exhausted"}:
        _invalid("$.status", "unknown result status")
    reason = _text(item["reason_code"], "$.reason_code", pattern=re.compile(r"^[A-Z][A-Z0-9_]*$"), maximum=64)
    diagnostic = item["diagnostic"]
    if type(diagnostic) is not str or len(diagnostic) > MAX_DIAGNOSTIC_CODEPOINTS or "\x00" in diagnostic or unicodedata.normalize("NFC", diagnostic) != diagnostic:
        _invalid("$.diagnostic", "invalid diagnostic")
    request_sha256 = None if item["request_sha256"] is None else _sha(item["request_sha256"], "$.request_sha256")
    registry = None if item["registry"] is None else _registry_from_mapping(item["registry"], "$.registry")
    fragment = None if item["fragment"] is None else _fragment_from_mapping(item["fragment"], "$.fragment")
    raw_candidates = item["candidates"]
    raw_incompatibilities = item["incompatibilities"]
    if type(raw_candidates) is not list or len(raw_candidates) > MAX_CAPABILITIES or type(raw_incompatibilities) is not list or len(raw_incompatibilities) > MAX_CAPABILITIES:
        _invalid("$", "invalid candidate or incompatibility arrays")
    candidates = tuple(_candidate_from_mapping(candidate, f"$.candidates[{index}]") for index, candidate in enumerate(raw_candidates))
    incompatibilities = tuple(_incompatibility_from_mapping(incompatibility, f"$.incompatibilities[{index}]") for index, incompatibility in enumerate(raw_incompatibilities))
    selected = None if item["selected_candidate_sha256"] is None else _sha(item["selected_candidate_sha256"], "$.selected_candidate_sha256")
    identity = None if item["result_sha256"] is None else _sha(item["result_sha256"], "$.result_sha256")
    result = _make(CapabilityRouteResult, schema=RESULT_SCHEMA, contract_id=CONTRACT_ID, contract_sha256=CONTRACT_SHA256, theory_plugin_contract_sha256=THEORY_PLUGIN_CONTRACT_SHA256, canonical_normalization_contract_sha256=CANONICAL_NORMALIZATION_CONTRACT_SHA256, problem_session_contract_sha256=PROBLEM_SESSION_CONTRACT_SHA256, status=status, reason_code=reason, diagnostic=diagnostic, request_sha256=request_sha256, registry=registry, fragment=fragment, candidates=candidates, incompatibilities=incompatibilities, selected_candidate_sha256=selected, result_sha256=identity, mathematical_authority=False)
    _validate_result_structure(result)
    return result


def _make_result(*, status: str, reason_code: str, diagnostic: str = "", request: CapabilityRouteRequest | None = None, registry: CapabilityRegistry | None = None, fragment: CapabilityFragment | None = None, candidates: tuple[CapabilityCandidate, ...] = (), incompatibilities: tuple[CapabilityIncompatibility, ...] = (), selected: str | None = None) -> CapabilityRouteResult:
    diagnostic = unicodedata.normalize("NFC", diagnostic.replace("\x00", "\ufffd"))
    if len(diagnostic) > MAX_DIAGNOSTIC_CODEPOINTS:
        diagnostic = diagnostic[:MAX_DIAGNOSTIC_CODEPOINTS]
    base = {"schema": RESULT_SCHEMA, "contract_id": CONTRACT_ID, "contract_sha256": CONTRACT_SHA256, "theory_plugin_contract_sha256": THEORY_PLUGIN_CONTRACT_SHA256, "canonical_normalization_contract_sha256": CANONICAL_NORMALIZATION_CONTRACT_SHA256, "problem_session_contract_sha256": PROBLEM_SESSION_CONTRACT_SHA256, "status": status, "reason_code": reason_code, "diagnostic": diagnostic, "request_sha256": request.request_sha256 if request is not None else None, "registry": registry, "fragment": fragment, "candidates": candidates, "incompatibilities": incompatibilities, "selected_candidate_sha256": selected, "result_sha256": None, "mathematical_authority": False}
    provisional = _make(CapabilityRouteResult, **base)
    identity = None if status in {"invalid", "exhausted"} else _digest(_canonical_bytes(_result_mapping(provisional, own_hash=False)))
    base["result_sha256"] = identity
    return _make(CapabilityRouteResult, **base)


def route_capabilities(request: bytes, descriptors: tuple[bytes, ...], artifacts: tuple[bytes, ...]) -> CapabilityRouteResult:
    """Build a pure registry and route one exact current canonical obligation."""
    try:
        if type(request) is not bytes:
            _invalid("request", "must be exact bytes")
        request_value = _request_from_mapping(_parse_json(request, "request", MAX_REQUEST_BYTES), "request")
        registry, plugins = _build_registry(descriptors)
        candidate_value, obligation = _load_current_obligation(request_value, artifacts)
        fragment = _derive_fragment(candidate_value, obligation)
        candidates: list[CapabilityCandidate] = []
        incompatibilities: list[CapabilityIncompatibility] = []
        for digest in sorted(plugins):
            plugin = plugins[digest]
            for capability in plugin["capabilities"]:
                reasons = _incompatibility_reasons(plugin, capability, request_value, fragment)
                if reasons:
                    incompatibilities.append(_make_incompatibility(plugin, capability, request_value, reasons))
                else:
                    candidates.append(_make_candidate(plugin, capability, plugin["operations"][request_value.operation], request_value, registry, fragment))
        candidates.sort(key=lambda item: (item.cost.estimated_cost, -item.priority, item.capability_id, item.plugin_id, _semver_rank(item.plugin_version, "candidate.plugin_version")))
        incompatibilities.sort(key=lambda item: (item.descriptor_sha256, item.capability_id, item.reason_codes))
        candidate_tuple = tuple(candidates)
        incompatibility_tuple = tuple(incompatibilities)
        if not candidate_tuple:
            return _make_result(status="unsupported", reason_code="NO_COMPATIBLE_CAPABILITY", request=request_value, registry=registry, fragment=fragment, incompatibilities=incompatibility_tuple)
        first_key = (candidate_tuple[0].cost.estimated_cost, candidate_tuple[0].priority, candidate_tuple[0].capability_id, candidate_tuple[0].plugin_id, _semver_rank(candidate_tuple[0].plugin_version, "candidate.plugin_version"))
        if len(candidate_tuple) > 1:
            second = candidate_tuple[1]
            second_key = (second.cost.estimated_cost, second.priority, second.capability_id, second.plugin_id, _semver_rank(second.plugin_version, "candidate.plugin_version"))
            if first_key == second_key:
                return _make_result(status="ambiguous", reason_code="NON_UNIQUE_SELECTION", request=request_value, registry=registry, fragment=fragment, candidates=candidate_tuple, incompatibilities=incompatibility_tuple)
        return _make_result(status="routed", reason_code="ROUTED", request=request_value, registry=registry, fragment=fragment, candidates=candidate_tuple, incompatibilities=incompatibility_tuple, selected=candidate_tuple[0].candidate_sha256)
    except _Ambiguous as exc:
        return _make_result(status="ambiguous", reason_code="READING_AMBIGUOUS", diagnostic=str(exc))
    except _Exhausted as exc:
        return _make_result(status="exhausted", reason_code="BUDGET_EXHAUSTED", diagnostic=str(exc))
    except _Invalid as exc:
        return _make_result(status="invalid", reason_code="INVALID_INPUT", diagnostic=str(exc))
    except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
        return _make_result(status="invalid", reason_code="INVALID_INPUT", diagnostic=str(exc))


def capability_route_result_bytes(value: CapabilityRouteResult) -> bytes:
    if type(value) is not CapabilityRouteResult:
        _fail("type", "$", "expected CapabilityRouteResult")
    validate_capability_route_result(value)
    return _canonical_bytes(_result_mapping(value))


def validate_capability_route_result(value: CapabilityRouteResult) -> None:
    if type(value) is not CapabilityRouteResult:
        _fail("type", "$", "expected exact CapabilityRouteResult")
    try:
        parsed = _result_from_mapping(_result_mapping(value))
        if parsed != value:
            _invalid("$", "in-memory result differs from strict reconstruction")
    except (_Invalid, _Exhausted, AttributeError, KeyError, TypeError) as exc:
        _fail("result", "$", str(exc))


def parse_capability_route_result(data: bytes) -> CapabilityRouteResult:
    """Strictly parse and recompute a serialized result's nested identities."""
    try:
        return _result_from_mapping(_parse_json(data, "$", MAX_OUTPUT_BYTES))
    except (_Invalid, _Exhausted, AttributeError, KeyError, TypeError) as exc:
        _fail("result", "$", str(exc))


__all__ = [
    "CONTRACT_ID", "CONTRACT_SHA256", "SCHEMA_SHA256S",
    "CapabilityAvailability", "CapabilityRegistry", "CapabilityRegistryEntry",
    "CapabilityRouteRequest", "CapabilityFragment", "CapabilityCostDerivation",
    "CapabilityCandidate", "CapabilityIncompatibility", "CapabilityRouteResult",
    "CapabilityRegistryValidationError", "make_capability_availability",
    "capability_availability_bytes", "make_capability_route_request",
    "parse_capability_route_request", "route_capabilities",
    "capability_route_result_bytes", "validate_capability_route_result",
    "parse_capability_route_result",
]
