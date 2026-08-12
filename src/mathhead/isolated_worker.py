"""Fail-closed isolated producer supervision for MH-052.

The process boundary is deliberately non-authoritative.  It turns one exact
planner strategy and one exact ResourceBudget lease into bounded process
observations and opaque stdout/stderr artifacts.  Mathematical interpretation
belongs to later checker boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from threading import Event
import time
import unicodedata
from typing import Any, Final, NoReturn

from mathhead.deterministic_planner import (
    CONTRACT_SHA256 as DETERMINISTIC_PLANNER_CONTRACT_SHA256,
    RESOURCE_DIMENSIONS,
    DeterministicPlannerValidationError,
    PlanningResult,
    PlanningStrategy,
    parse_planning_result,
)


ISOLATED_WORKER_CONTRACT_ID: Final = "MH-C-ISOLATED-WORKER-001"
ISOLATED_WORKER_CONTRACT_SHA256: Final = (
    "c578d5a75f7a670f55e660147c335dc29709e71b82af8b37eb0033891b81a49b"
)
RESOURCE_BUDGET_CONTRACT_SHA256: Final = (
    "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045"
)
REQUEST_SCHEMA: Final = "mathhead.isolated-worker-request.v1"
CAPABILITY_SCHEMA: Final = "mathhead.isolation-capability.v1"
USAGE_SCHEMA: Final = "mathhead.worker-resource-usage.v1"
ARTIFACT_SCHEMA: Final = "mathhead.worker-artifact.v1"
DIAGNOSTIC_SCHEMA: Final = "mathhead.worker-diagnostic.v1"
RESULT_SCHEMA: Final = "mathhead.isolated-worker-result.v1"
SCHEMA_SHA256S: Final = {
    REQUEST_SCHEMA: "5f3f12dcf71bcceb7ca539df90c93887a4048366c5ea05be41b70b6532197a97",
    CAPABILITY_SCHEMA: "63b1800180724b51dcfa3289fec3e990ecad131f6422203319562178e7296098",
    USAGE_SCHEMA: "0daa1bb755a8005d53824ee8bcfebd0be1174e16cbcd7e2c5fd80ee2467b1e44",
    ARTIFACT_SCHEMA: "d4df223c84841325f99e1a7285a9e0f9773522ed37f8cb550f4b55efedc9700a",
    DIAGNOSTIC_SCHEMA: "e076d807d7e6c7d5e040792f928e592640f7615b6dc041855769b6a8a7f75673",
    RESULT_SCHEMA: "b6172ad7c33908b65ecb74fc39340664b8a4ca8f55d1b69c1e23eacaf281f7df",
}

INTEGER_MAXIMUM: Final = 9_007_199_254_740_991
MAX_INPUT_BYTES: Final = 1_073_741_824
MAX_EXECUTABLE_BYTES: Final = 1_073_741_824
MAX_ARGUMENTS: Final = 128
MAX_ARGUMENT_CODEPOINTS: Final = 4_096
MAX_ARTIFACTS: Final = 1_024
MAX_DIAGNOSTICS: Final = 32
MAX_DIAGNOSTIC_CODEPOINTS: Final = 1_024
MAX_JSON_DEPTH: Final = 128
MAX_JSON_NODES: Final = 8_000_000
RESOURCE_BUDGET_MAX_BYTES: Final = 67_108_864
RESOURCE_BUDGET_MAX_DEPTH: Final = 64
RESOURCE_BUDGET_MAX_NODES: Final = 4_000_000
RESOURCE_BUDGET_MAX_EVENTS: Final = 100_000
RESOURCE_BUDGET_MAX_ACTIVE_LEASES: Final = 10_000
POLL_SECONDS: Final = 0.01
GRACE_SECONDS: Final = 0.25
FORCE_SECONDS: Final = 30.0
_CREATE_SUSPENDED: Final = 0x00000004
_FAMILIES: Final = {"sympy", "python_enumeration", "smt", "external_process"}
_STATUSES: Final = {"completed", "refused", "unsupported", "exhausted", "cancelled", "failed", "invalid"}
_REASONS: Final = {
    "COMPLETED", "REQUEST_INVALID", "PLAN_INVALID", "STRATEGY_MISMATCH",
    "BUDGET_INVALID", "BUDGET_INSUFFICIENT", "ISOLATION_UNSUPPORTED",
    "EXECUTABLE_INVALID", "LAUNCH_FAILED", "WALL_TIME_EXHAUSTED",
    "CPU_TIME_EXHAUSTED", "MEMORY_EXHAUSTED", "OUTPUT_EXHAUSTED",
    "DIAGNOSTIC_EXHAUSTED", "CANCELLED", "EXIT_FAILED", "PROTOCOL_FAILED",
    "TREE_CLEANUP_FAILED", "SUPERVISOR_FAILED",
}
_STATUS_REASONS: Final = {
    "completed": {"COMPLETED"},
    "refused": {"BUDGET_INSUFFICIENT", "EXECUTABLE_INVALID", "LAUNCH_FAILED"},
    "unsupported": {"ISOLATION_UNSUPPORTED"},
    "exhausted": {
        "WALL_TIME_EXHAUSTED", "CPU_TIME_EXHAUSTED", "MEMORY_EXHAUSTED",
        "OUTPUT_EXHAUSTED", "DIAGNOSTIC_EXHAUSTED",
    },
    "cancelled": {"CANCELLED"},
    "failed": {
        "LAUNCH_FAILED", "EXIT_FAILED", "PROTOCOL_FAILED",
        "TREE_CLEANUP_FAILED", "SUPERVISOR_FAILED",
    },
    "invalid": {
        "REQUEST_INVALID", "PLAN_INVALID", "STRATEGY_MISMATCH",
        "BUDGET_INVALID", "EXECUTABLE_INVALID",
    },
}
_POLICY: Final = {
    "wall_clock": "monotonic_elapsed_us",
    "deadline": "relative_to_start",
    "cpu_accounting": "exclusive_budget_scope_us",
    "memory_accounting": "inclusive_active_process_tree_bytes",
    "integer_rounding": "ceil",
    "reservation": "conservative_all_dimensions",
}
_CUMULATIVE: Final = (
    "cpu_time_us", "solver_calls", "generated_objects", "proof_bytes",
    "evidence_bytes", "output_bytes", "diagnostic_bytes",
)
_TRUNCATABLE: Final = {
    "diagnostic_bytes", "evidence_bytes", "generated_objects",
    "output_bytes", "proof_bytes",
}
_NAMESPACED = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class IsolatedWorkerValidationError(ValueError):
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


class _WorkerValue:
    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__module__ != __name__:
            raise TypeError("isolated-worker values are final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("isolated-worker values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("isolated-worker values cannot be pickled")

    def __copy__(self) -> NoReturn:
        raise TypeError("isolated-worker values cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        del memo
        raise TypeError("isolated-worker values cannot be copied")


@dataclass(frozen=True, slots=True, init=False)
class WorkerResourceVector(_WorkerValue):
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
        raise PermissionError("resource vectors are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class WorkerArtifactBinding(_WorkerValue):
    role: str
    sha256: str
    bytes: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("artifact bindings are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class IsolatedWorkerRequest(_WorkerValue):
    schema: str
    planning_result_sha256: str
    strategy_sha256: str
    descriptor_sha256: str
    family: str
    protocol: str
    executable_sha256: str
    arguments: tuple[str, ...]
    artifact_bindings: tuple[WorkerArtifactBinding, ...]
    parent_budget_sha256: str
    lease_id: str
    child_budget_id: str
    resource_limits: WorkerResourceVector
    request_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("worker requests are codec-owned")


@dataclass(frozen=True, slots=True, init=False)
class IsolationCapability(_WorkerValue):
    schema: str
    platform: str
    containment: str
    wall_limit: str
    cpu_limit: str
    memory_limit: str
    tree_termination: str
    supported: bool
    reason_code: str
    capability_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("capabilities are supervisor-owned")


@dataclass(frozen=True, slots=True, init=False)
class WorkerResourceUsage(_WorkerValue):
    schema: str
    wall_time_us: int
    cpu_time_us: int
    memory_peak_bytes: int
    solver_calls: int
    generated_objects: int
    proof_bytes: int
    evidence_bytes: int
    output_bytes: int
    diagnostic_bytes: int
    nesting_peak: int
    exit_code: int | None
    termination_signal: int | None
    usage_complete: bool
    usage_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("usage values are supervisor-owned")


@dataclass(frozen=True, slots=True, init=False)
class WorkerArtifact(_WorkerValue):
    schema: str
    role: str
    media_type: str
    original_bytes: int
    retained_bytes: int
    omitted_bytes: int
    retained_sha256: str | None
    artifact_sha256: str
    mathematical_authority: bool
    _retained: bytes

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("worker artifacts are supervisor-owned")


@dataclass(frozen=True, slots=True, init=False)
class WorkerDiagnostic(_WorkerValue):
    schema: str
    code: str
    message: str
    diagnostic_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("worker diagnostics are supervisor-owned")


@dataclass(frozen=True, slots=True, init=False)
class IsolatedWorkerResult(_WorkerValue):
    schema: str
    contract_id: str
    contract_sha256: str
    resource_budget_contract_sha256: str
    deterministic_planner_contract_sha256: str
    status: str
    reason_code: str
    request_sha256: str | None
    planning_result_sha256: str | None
    strategy_sha256: str | None
    capability: IsolationCapability | None
    usage: WorkerResourceUsage | None
    artifacts: tuple[WorkerArtifact, ...]
    diagnostics: tuple[WorkerDiagnostic, ...]
    child_budget_sha256: str | None
    parent_budget_sha256: str | None
    tree_terminated: bool
    lease_reconciled: bool
    semantic_sha256: str | None
    result_sha256: str | None
    mathematical_authority: bool
    _child_budget: bytes | None
    _parent_budget: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("worker results are supervisor-owned")


def _make(cls: type[Any], **values: object) -> Any:
    value = object.__new__(cls)
    for name, item in values.items():
        object.__setattr__(value, name, item)
    return value


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise IsolatedWorkerValidationError(kind, path, detail)


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
    stack: list[tuple[object, int]] = [(value, 1)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        if count > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            _fail("limit", "$", "JSON tree exceeds its finite ceiling")
        if type(item) is str:
            if "\x00" in item or unicodedata.normalize("NFC", item) != item:
                _fail("canonical", "$", "text must be NFC without NUL")
            if len(item) > 1_048_576:
                _fail("limit", "$", "text exceeds its finite ceiling")
        elif type(item) is int:
            if abs(item) > INTEGER_MAXIMUM:
                _fail("limit", "$", "integer exceeds portable exact range")
        elif type(item) is float:
            _fail("schema", "$", "floats are forbidden")
        elif type(item) is list:
            stack.extend((nested, depth + 1) for nested in reversed(item))
        elif type(item) is dict:
            stack.extend((key, depth + 1) for key in item)
            stack.extend((nested, depth + 1) for nested in item.values())
        elif item is not None and type(item) is not bool:
            _fail("schema", "$", "unsupported JSON value")


def _canonical(value: object, *, maximum: int = MAX_INPUT_BYTES) -> bytes:
    _walk(value)
    try:
        raw = (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        _fail("canonical", "$", f"encoding failed: {type(exc).__name__}")
    if len(raw) > maximum:
        _fail("limit", "$", "canonical bytes exceed their finite ceiling")
    return raw


def _parse(data: bytes, path: str, *, maximum: int = MAX_INPUT_BYTES) -> dict[str, object]:
    if type(data) is not bytes:
        _fail("type", path, "expected exact bytes")
    if not data or len(data) > maximum:
        _fail("limit", path, "input byte length is invalid")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except _DuplicateKey as exc:
        _fail("duplicate", path, f"duplicate key {exc}")
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        _fail("json", path, f"invalid JSON: {type(exc).__name__}")
    if type(value) is not dict:
        _fail("schema", path, "root must be an object")
    _walk(value)
    if _canonical(value, maximum=maximum) != data:
        _fail("canonical", path, "bytes are not canonical")
    return value


def _keys(value: object, expected: set[str], path: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail("schema", path, "expected object")
    item = value
    if set(item) != expected:
        _fail("schema", path, "object field set differs")
    return item


def _text(value: object, path: str, *, maximum: int = 1_048_576) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        _fail("schema", path, "invalid text")
    if "\x00" in value or unicodedata.normalize("NFC", value) != value:
        _fail("canonical", path, "text must be NFC without NUL")
    return value


def _identifier(value: object, path: str) -> str:
    text = _text(value, path, maximum=64)
    if _SNAKE.fullmatch(text) is None:
        _fail("schema", path, "invalid stable identifier")
    return text


def _digest(value: object, path: str) -> str:
    text = _text(value, path, maximum=64)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        _fail("identity", path, "invalid SHA-256")
    return text


def _quantity(value: object, path: str) -> int:
    if type(value) is not int or not 0 <= value <= INTEGER_MAXIMUM:
        _fail("schema", path, "invalid exact quantity")
    return value


def _self_hash(mapping: dict[str, object], field: str) -> str:
    preimage = dict(mapping)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _vector_from_mapping(value: object, path: str) -> WorkerResourceVector:
    item = _keys(value, set(RESOURCE_DIMENSIONS), path)
    values = {name: _quantity(item[name], f"{path}.{name}") for name in RESOURCE_DIMENSIONS}
    return _make(WorkerResourceVector, **values)


def _vector_mapping(value: WorkerResourceVector) -> dict[str, int]:
    if type(value) is not WorkerResourceVector:
        _fail("type", "$", "expected exact WorkerResourceVector")
    return {name: getattr(value, name) for name in RESOURCE_DIMENSIONS}


def _binding_from_mapping(value: object, path: str) -> WorkerArtifactBinding:
    item = _keys(value, {"role", "sha256", "bytes"}, path)
    return _make(WorkerArtifactBinding, role=_identifier(item["role"], f"{path}.role"), sha256=_digest(item["sha256"], f"{path}.sha256"), bytes=_quantity(item["bytes"], f"{path}.bytes"))


def _request_mapping(value: IsolatedWorkerRequest, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "planning_result_sha256": value.planning_result_sha256,
        "strategy_sha256": value.strategy_sha256, "descriptor_sha256": value.descriptor_sha256,
        "family": value.family, "protocol": value.protocol,
        "executable_sha256": value.executable_sha256, "arguments": list(value.arguments),
        "artifact_bindings": [{"role": item.role, "sha256": item.sha256, "bytes": item.bytes} for item in value.artifact_bindings],
        "parent_budget_sha256": value.parent_budget_sha256, "lease_id": value.lease_id,
        "child_budget_id": value.child_budget_id, "resource_limits": _vector_mapping(value.resource_limits),
        "request_sha256": value.request_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _request_from_mapping(value: object) -> IsolatedWorkerRequest:
    fields = {"schema", "planning_result_sha256", "strategy_sha256", "descriptor_sha256", "family", "protocol", "executable_sha256", "arguments", "artifact_bindings", "parent_budget_sha256", "lease_id", "child_budget_id", "resource_limits", "request_sha256", "mathematical_authority"}
    item = _keys(value, fields, "$")
    if item["schema"] != REQUEST_SCHEMA or item["protocol"] != "raw_stdout_v1" or item["mathematical_authority"] is not False:
        _fail("schema", "$", "request constants differ")
    family = _text(item["family"], "$.family", maximum=32)
    if family not in _FAMILIES:
        _fail("schema", "$.family", "unsupported worker family")
    arguments_value = item["arguments"]
    if type(arguments_value) is not list or len(arguments_value) > MAX_ARGUMENTS:
        _fail("limit", "$.arguments", "argument list exceeds its ceiling")
    arguments = tuple(_text(argument, f"$.arguments[{index}]", maximum=MAX_ARGUMENT_CODEPOINTS) for index, argument in enumerate(arguments_value))
    bindings_value = item["artifact_bindings"]
    if type(bindings_value) is not list or len(bindings_value) > MAX_ARTIFACTS:
        _fail("limit", "$.artifact_bindings", "artifact list exceeds its ceiling")
    bindings = tuple(_binding_from_mapping(binding, f"$.artifact_bindings[{index}]") for index, binding in enumerate(bindings_value))
    if len({binding.role for binding in bindings}) != len(bindings):
        _fail("artifact", "$.artifact_bindings", "artifact roles must be unique")
    request = _make(
        IsolatedWorkerRequest, schema=REQUEST_SCHEMA,
        planning_result_sha256=_digest(item["planning_result_sha256"], "$.planning_result_sha256"),
        strategy_sha256=_digest(item["strategy_sha256"], "$.strategy_sha256"),
        descriptor_sha256=_digest(item["descriptor_sha256"], "$.descriptor_sha256"),
        family=family, protocol="raw_stdout_v1",
        executable_sha256=_digest(item["executable_sha256"], "$.executable_sha256"), arguments=arguments,
        artifact_bindings=bindings, parent_budget_sha256=_digest(item["parent_budget_sha256"], "$.parent_budget_sha256"),
        lease_id=_identifier(item["lease_id"], "$.lease_id"), child_budget_id=_identifier(item["child_budget_id"], "$.child_budget_id"),
        resource_limits=_vector_from_mapping(item["resource_limits"], "$.resource_limits"),
        request_sha256=_digest(item["request_sha256"], "$.request_sha256"), mathematical_authority=False,
    )
    if request.request_sha256 != _self_hash(_request_mapping(request), "request_sha256"):
        _fail("identity", "$.request_sha256", "request identity mismatch")
    return request


def make_isolated_worker_request(*, planning_result: bytes, strategy_sha256: str, descriptor_sha256: str, family: str, executable: bytes, arguments: tuple[str, ...], artifacts: tuple[tuple[str, bytes], ...], parent_budget: bytes, lease_id: str, child_budget_id: str, resource_limits: dict[str, int]) -> bytes:
    """Create canonical request bytes without reading paths or host state."""
    if any(type(value) is not bytes for value in (planning_result, executable, parent_budget)) or type(arguments) is not tuple or type(artifacts) is not tuple:
        _fail("type", "$", "request constructor requires exact immutable values")
    bindings: list[dict[str, object]] = []
    for index, pair in enumerate(artifacts):
        if type(pair) is not tuple or len(pair) != 2 or type(pair[1]) is not bytes:
            _fail("type", f"artifacts[{index}]", "expected role and exact bytes")
        bindings.append({"role": pair[0], "sha256": _sha(pair[1]), "bytes": len(pair[1])})
    mapping: dict[str, object] = {
        "schema": REQUEST_SCHEMA, "planning_result_sha256": _sha(planning_result),
        "strategy_sha256": strategy_sha256, "descriptor_sha256": descriptor_sha256,
        "family": family, "protocol": "raw_stdout_v1", "executable_sha256": _sha(executable),
        "arguments": list(arguments), "artifact_bindings": bindings,
        "parent_budget_sha256": _sha(parent_budget), "lease_id": lease_id,
        "child_budget_id": child_budget_id, "resource_limits": resource_limits,
        "request_sha256": None, "mathematical_authority": False,
    }
    mapping["request_sha256"] = _sha(_canonical(mapping))
    request = _request_from_mapping(mapping)
    return _canonical(_request_mapping(request))


def parse_isolated_worker_request(data: bytes) -> IsolatedWorkerRequest:
    return _request_from_mapping(_parse(data, "$"))


def _capability_mapping(value: IsolationCapability, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "platform": value.platform, "containment": value.containment,
        "wall_limit": value.wall_limit, "cpu_limit": value.cpu_limit,
        "memory_limit": value.memory_limit, "tree_termination": value.tree_termination,
        "supported": value.supported, "reason_code": value.reason_code,
        "capability_sha256": value.capability_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _capability_from_mapping(value: object, path: str = "$") -> IsolationCapability:
    fields = {"schema", "platform", "containment", "wall_limit", "cpu_limit", "memory_limit", "tree_termination", "supported", "reason_code", "capability_sha256", "mathematical_authority"}
    item = _keys(value, fields, path)
    platforms = {"linux", "darwin", "windows", "unsupported"}
    containments = {"posix_session", "windows_job", "none"}
    wall = {"supervisor_monotonic", "none"}
    cpu = {"posix_rlimit_inherited", "windows_job", "none"}
    memory = {"posix_address_space_inherited", "windows_job_tree", "none"}
    trees = {"process_group", "job_close", "none"}
    platform = _text(item["platform"], f"{path}.platform", maximum=16)
    containment = _text(item["containment"], f"{path}.containment", maximum=32)
    wall_limit = _text(item["wall_limit"], f"{path}.wall_limit", maximum=32)
    cpu_limit = _text(item["cpu_limit"], f"{path}.cpu_limit", maximum=32)
    memory_limit = _text(item["memory_limit"], f"{path}.memory_limit", maximum=40)
    tree = _text(item["tree_termination"], f"{path}.tree_termination", maximum=32)
    reason = _text(item["reason_code"], f"{path}.reason_code", maximum=32)
    supported = item["supported"]
    if platform not in platforms or containment not in containments or wall_limit not in wall or cpu_limit not in cpu or memory_limit not in memory or tree not in trees or type(supported) is not bool or reason not in {"SUPPORTED", "PLATFORM_UNSUPPORTED", "PRIMITIVE_UNAVAILABLE"} or item["schema"] != CAPABILITY_SCHEMA or item["mathematical_authority"] is not False:
        _fail("schema", path, "capability fields are invalid")
    if supported != (reason == "SUPPORTED"):
        _fail("platform", path, "support and reason disagree")
    if supported and (containment == "none" or wall_limit == "none" or cpu_limit == "none" or memory_limit == "none" or tree == "none"):
        _fail("platform", path, "supported capability omits an enforcement primitive")
    if not supported and any(part != "none" for part in (containment, wall_limit, cpu_limit, memory_limit, tree)):
        _fail("platform", path, "unsupported capability claims a primitive")
    result = _make(IsolationCapability, schema=CAPABILITY_SCHEMA, platform=platform, containment=containment, wall_limit=wall_limit, cpu_limit=cpu_limit, memory_limit=memory_limit, tree_termination=tree, supported=supported, reason_code=reason, capability_sha256=_digest(item["capability_sha256"], f"{path}.capability_sha256"), mathematical_authority=False)
    if result.capability_sha256 != _self_hash(_capability_mapping(result), "capability_sha256"):
        _fail("identity", f"{path}.capability_sha256", "capability identity mismatch")
    return result


def isolation_capability() -> IsolationCapability:
    """Return the exact currently usable host containment capability."""
    platform = sys.platform
    if platform.startswith("linux") or platform == "darwin":
        try:
            import resource  # noqa: PLC0415
            required = (resource.RLIMIT_CPU, resource.RLIMIT_AS, resource.RLIMIT_FSIZE, resource.RLIMIT_NOFILE)
            del required
            supported = hasattr(os, "killpg") and hasattr(os, "setsid")
        except (ImportError, AttributeError):
            supported = False
        mapping: dict[str, object] = {
            "schema": CAPABILITY_SCHEMA, "platform": "linux" if platform.startswith("linux") else "darwin",
            "containment": "posix_session" if supported else "none",
            "wall_limit": "supervisor_monotonic" if supported else "none",
            "cpu_limit": "posix_rlimit_inherited" if supported else "none",
            "memory_limit": "posix_address_space_inherited" if supported else "none",
            "tree_termination": "process_group" if supported else "none",
            "supported": supported, "reason_code": "SUPPORTED" if supported else "PRIMITIVE_UNAVAILABLE",
            "capability_sha256": None, "mathematical_authority": False,
        }
    elif platform == "win32":
        try:
            import ctypes  # noqa: PLC0415
            supported = hasattr(ctypes, "windll") and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP")
        except (ImportError, AttributeError):
            supported = False
        mapping = {
            "schema": CAPABILITY_SCHEMA, "platform": "windows",
            "containment": "windows_job" if supported else "none",
            "wall_limit": "supervisor_monotonic" if supported else "none",
            "cpu_limit": "windows_job" if supported else "none",
            "memory_limit": "windows_job_tree" if supported else "none",
            "tree_termination": "job_close" if supported else "none",
            "supported": supported, "reason_code": "SUPPORTED" if supported else "PRIMITIVE_UNAVAILABLE",
            "capability_sha256": None, "mathematical_authority": False,
        }
    else:
        mapping = {
            "schema": CAPABILITY_SCHEMA, "platform": "unsupported", "containment": "none",
            "wall_limit": "none", "cpu_limit": "none", "memory_limit": "none",
            "tree_termination": "none", "supported": False, "reason_code": "PLATFORM_UNSUPPORTED",
            "capability_sha256": None, "mathematical_authority": False,
        }
    mapping["capability_sha256"] = _sha(_canonical(mapping))
    return _capability_from_mapping(mapping)


def _usage_mapping(value: WorkerResourceUsage, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "wall_time_us": value.wall_time_us,
        "cpu_time_us": value.cpu_time_us, "memory_peak_bytes": value.memory_peak_bytes,
        "solver_calls": value.solver_calls, "generated_objects": value.generated_objects,
        "proof_bytes": value.proof_bytes, "evidence_bytes": value.evidence_bytes,
        "output_bytes": value.output_bytes, "diagnostic_bytes": value.diagnostic_bytes,
        "nesting_peak": value.nesting_peak, "exit_code": value.exit_code,
        "termination_signal": value.termination_signal, "usage_complete": value.usage_complete,
        "usage_sha256": value.usage_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _usage_from_mapping(value: object, path: str = "$") -> WorkerResourceUsage:
    fields = {"schema", "wall_time_us", "cpu_time_us", "memory_peak_bytes", "solver_calls", "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes", "diagnostic_bytes", "nesting_peak", "exit_code", "termination_signal", "usage_complete", "usage_sha256", "mathematical_authority"}
    item = _keys(value, fields, path)
    if item["schema"] != USAGE_SCHEMA or item["mathematical_authority"] is not False or type(item["usage_complete"]) is not bool:
        _fail("schema", path, "usage constants differ")
    exit_code = item["exit_code"]
    termination_signal = item["termination_signal"]
    if exit_code is not None and (type(exit_code) is not int or not -(2**31) <= exit_code < 2**31):
        _fail("schema", f"{path}.exit_code", "invalid exit code")
    if termination_signal is not None and (type(termination_signal) is not int or not 1 <= termination_signal <= 255):
        _fail("schema", f"{path}.termination_signal", "invalid signal")
    result = _make(
        WorkerResourceUsage, schema=USAGE_SCHEMA,
        wall_time_us=_quantity(item["wall_time_us"], f"{path}.wall_time_us"),
        cpu_time_us=_quantity(item["cpu_time_us"], f"{path}.cpu_time_us"),
        memory_peak_bytes=_quantity(item["memory_peak_bytes"], f"{path}.memory_peak_bytes"),
        solver_calls=_quantity(item["solver_calls"], f"{path}.solver_calls"),
        generated_objects=_quantity(item["generated_objects"], f"{path}.generated_objects"),
        proof_bytes=_quantity(item["proof_bytes"], f"{path}.proof_bytes"),
        evidence_bytes=_quantity(item["evidence_bytes"], f"{path}.evidence_bytes"),
        output_bytes=_quantity(item["output_bytes"], f"{path}.output_bytes"),
        diagnostic_bytes=_quantity(item["diagnostic_bytes"], f"{path}.diagnostic_bytes"),
        nesting_peak=_quantity(item["nesting_peak"], f"{path}.nesting_peak"),
        exit_code=exit_code, termination_signal=termination_signal,
        usage_complete=item["usage_complete"], usage_sha256=_digest(item["usage_sha256"], f"{path}.usage_sha256"), mathematical_authority=False,
    )
    if result.usage_sha256 != _self_hash(_usage_mapping(result), "usage_sha256"):
        _fail("identity", f"{path}.usage_sha256", "usage identity mismatch")
    return result


def _make_usage(*, wall: int, cpu: int, memory: int, solver_calls: int, output: int, diagnostic: int, exit_code: int | None, termination_signal: int | None, complete: bool) -> WorkerResourceUsage:
    mapping: dict[str, object] = {
        "schema": USAGE_SCHEMA, "wall_time_us": max(0, min(wall, INTEGER_MAXIMUM)),
        "cpu_time_us": max(0, min(cpu, INTEGER_MAXIMUM)), "memory_peak_bytes": max(0, min(memory, INTEGER_MAXIMUM)),
        "solver_calls": solver_calls, "generated_objects": 0, "proof_bytes": 0,
        "evidence_bytes": 0, "output_bytes": output, "diagnostic_bytes": diagnostic,
        "nesting_peak": 0, "exit_code": exit_code, "termination_signal": termination_signal,
        "usage_complete": complete, "usage_sha256": None, "mathematical_authority": False,
    }
    mapping["usage_sha256"] = _sha(_canonical(mapping))
    return _usage_from_mapping(mapping)


def _artifact_mapping(value: WorkerArtifact, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "role": value.role, "media_type": value.media_type,
        "original_bytes": value.original_bytes, "retained_bytes": value.retained_bytes,
        "omitted_bytes": value.omitted_bytes, "retained_sha256": value.retained_sha256,
        "artifact_sha256": value.artifact_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _artifact_from_mapping(value: object, retained: bytes, path: str = "$") -> WorkerArtifact:
    fields = {"schema", "role", "media_type", "original_bytes", "retained_bytes", "omitted_bytes", "retained_sha256", "artifact_sha256", "mathematical_authority"}
    item = _keys(value, fields, path)
    role = item["role"]
    if item["schema"] != ARTIFACT_SCHEMA or role not in {"stdout", "stderr"} or item["media_type"] != "application/octet-stream" or item["mathematical_authority"] is not False or type(retained) is not bytes:
        _fail("schema", path, "artifact constants differ")
    original = _quantity(item["original_bytes"], f"{path}.original_bytes")
    retained_count = _quantity(item["retained_bytes"], f"{path}.retained_bytes")
    omitted = _quantity(item["omitted_bytes"], f"{path}.omitted_bytes")
    retained_sha = item["retained_sha256"]
    if original != retained_count + omitted or retained_count != len(retained) or retained_sha != (_sha(retained) if retained else None):
        _fail("artifact", path, "artifact byte conservation or digest differs")
    result = _make(WorkerArtifact, schema=ARTIFACT_SCHEMA, role=role, media_type="application/octet-stream", original_bytes=original, retained_bytes=retained_count, omitted_bytes=omitted, retained_sha256=retained_sha, artifact_sha256=_digest(item["artifact_sha256"], f"{path}.artifact_sha256"), mathematical_authority=False, _retained=retained)
    if result.artifact_sha256 != _self_hash(_artifact_mapping(result), "artifact_sha256"):
        _fail("identity", f"{path}.artifact_sha256", "artifact identity mismatch")
    return result


def _make_artifact(role: str, retained: bytes, original: int) -> WorkerArtifact:
    mapping: dict[str, object] = {
        "schema": ARTIFACT_SCHEMA, "role": role, "media_type": "application/octet-stream",
        "original_bytes": original, "retained_bytes": len(retained), "omitted_bytes": original - len(retained),
        "retained_sha256": _sha(retained) if retained else None, "artifact_sha256": None,
        "mathematical_authority": False,
    }
    mapping["artifact_sha256"] = _sha(_canonical(mapping))
    return _artifact_from_mapping(mapping, retained)


def worker_artifact_bytes(value: WorkerArtifact) -> bytes:
    if type(value) is not WorkerArtifact:
        _fail("type", "$", "expected exact WorkerArtifact")
    _artifact_from_mapping(_artifact_mapping(value), value._retained)
    return value._retained


def _diagnostic_mapping(value: WorkerDiagnostic, *, own_hash: bool = True) -> dict[str, object]:
    return {"schema": value.schema, "code": value.code, "message": value.message, "diagnostic_sha256": value.diagnostic_sha256 if own_hash else None, "mathematical_authority": value.mathematical_authority}


def _diagnostic_from_mapping(value: object, path: str = "$") -> WorkerDiagnostic:
    item = _keys(value, {"schema", "code", "message", "diagnostic_sha256", "mathematical_authority"}, path)
    code = _text(item["code"], f"{path}.code", maximum=64)
    if not code[0].isupper() or not all(character.isupper() or character.isdigit() or character == "_" for character in code) or item["schema"] != DIAGNOSTIC_SCHEMA or item["mathematical_authority"] is not False:
        _fail("schema", path, "diagnostic constants differ")
    result = _make(WorkerDiagnostic, schema=DIAGNOSTIC_SCHEMA, code=code, message=_text(item["message"], f"{path}.message", maximum=MAX_DIAGNOSTIC_CODEPOINTS), diagnostic_sha256=_digest(item["diagnostic_sha256"], f"{path}.diagnostic_sha256"), mathematical_authority=False)
    if result.diagnostic_sha256 != _self_hash(_diagnostic_mapping(result), "diagnostic_sha256"):
        _fail("identity", f"{path}.diagnostic_sha256", "diagnostic identity mismatch")
    return result


def _make_diagnostic(code: str, message: str) -> WorkerDiagnostic:
    clean = unicodedata.normalize("NFC", message.replace("\x00", ""))[:MAX_DIAGNOSTIC_CODEPOINTS] or code.lower()
    mapping: dict[str, object] = {"schema": DIAGNOSTIC_SCHEMA, "code": code, "message": clean, "diagnostic_sha256": None, "mathematical_authority": False}
    mapping["diagnostic_sha256"] = _sha(_canonical(mapping))
    return _diagnostic_from_mapping(mapping)


@dataclass(slots=True)
class _BudgetState:
    value: dict[str, object]
    cumulative: dict[str, int]
    observation: dict[str, int]
    active: dict[str, dict[str, object]]
    owners: set[str]
    reconciliations: dict[str, dict[str, object]]


def _zero_limit() -> dict[str, int]:
    return {name: 0 for name in RESOURCE_DIMENSIONS}


def _zero_usage() -> dict[str, int]:
    return {
        "wall_time_us": 0, "cpu_time_us": 0, "memory_peak_bytes": 0,
        "memory_retained_bytes": 0, "solver_calls": 0, "generated_objects": 0,
        "proof_bytes": 0, "evidence_bytes": 0, "output_bytes": 0,
        "diagnostic_bytes": 0, "nesting_peak": 0,
    }


def _zero_observation() -> dict[str, int]:
    return {"wall_time_us": 0, "memory_peak_bytes": 0, "memory_retained_bytes": 0, "nesting_current": 0, "nesting_peak": 0}


def _budget_vector(value: object, path: str) -> dict[str, int]:
    item = _keys(value, set(RESOURCE_DIMENSIONS), path)
    return {name: _quantity(item[name], f"{path}.{name}") for name in RESOURCE_DIMENSIONS}


def _usage_as_limit(value: dict[str, int]) -> dict[str, int]:
    return {
        "wall_time_us": value["wall_time_us"], "cpu_time_us": value["cpu_time_us"],
        "memory_bytes": value["memory_peak_bytes"], "solver_calls": value["solver_calls"],
        "generated_objects": value["generated_objects"], "proof_bytes": value["proof_bytes"],
        "evidence_bytes": value["evidence_bytes"], "output_bytes": value["output_bytes"],
        "diagnostic_bytes": value["diagnostic_bytes"], "nesting_depth": value["nesting_peak"],
    }


def _parse_usage_mapping(value: object, path: str) -> dict[str, int]:
    expected = {"wall_time_us", "cpu_time_us", "memory_peak_bytes", "memory_retained_bytes", "solver_calls", "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes", "diagnostic_bytes", "nesting_peak"}
    item = _keys(value, expected, path)
    result = {name: _quantity(item[name], f"{path}.{name}") for name in expected}
    if result["memory_retained_bytes"] > result["memory_peak_bytes"]:
        _fail("accounting", path, "retained memory exceeds peak")
    return result


def _active_totals(active: dict[str, dict[str, object]]) -> dict[str, int]:
    totals = _zero_limit()
    for lease in active.values():
        allocation = lease["allocation"]
        assert isinstance(allocation, dict)
        for name in RESOURCE_DIMENSIONS:
            totals[name] += allocation[name]
            if totals[name] > INTEGER_MAXIMUM:
                _fail("budget", "$", "active allocation sum exceeds exact range")
    return totals


def _event_identifier(item: dict[str, object], name: str, path: str, owners: set[str]) -> str:
    if name not in item:
        _fail("schema", f"{path}.{name}", "missing identity")
    identifier = _identifier(item[name], f"{path}.{name}")
    if identifier in owners:
        _fail("budget", f"{path}.{name}", "budget identity is reused")
    owners.add(identifier)
    return identifier


def _budget_shape(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > RESOURCE_BUDGET_MAX_NODES or depth > RESOURCE_BUDGET_MAX_DEPTH:
            _fail("budget", "resource_budget", "canonical resource budget exceeds its shape ceiling")
        if type(item) is list:
            stack.extend((nested, depth + 1) for nested in item)
        elif type(item) is dict:
            stack.extend((key, depth + 1) for key in item)
            stack.extend((nested, depth + 1) for nested in item.values())


def _extension_payload(value: object, path: str) -> None:
    stack: list[tuple[object, str]] = [(value, path)]
    while stack:
        item, current = stack.pop()
        if type(item) is list:
            if len(item) > RESOURCE_BUDGET_MAX_EVENTS:
                _fail("budget", current, "extension array exceeds its ceiling")
            stack.extend((nested, f"{current}[{index}]") for index, nested in enumerate(item))
        elif type(item) is dict:
            for key, nested in item.items():
                if len(key) > 128 or _SNAKE.fullmatch(key) is None:
                    _fail("schema", f"{current}.<key>", "invalid extension payload key")
                stack.append((nested, f"{current}.{key}"))


def _extensions(value: object, path: str) -> None:
    if type(value) is not dict:
        _fail("schema", path, "extensions must be an object")
    for key, payload in value.items():
        if len(key) > 255 or _NAMESPACED.fullmatch(key) is None:
            _fail("schema", f"{path}.<key>", "extension key is not reverse-DNS namespaced")
        _extension_payload(payload, f"{path}.{key}")


def _reason(value: object, path: str) -> str:
    return _text(value, path, maximum=4_096)


def _observed_overruns(limits: dict[str, int], observation: dict[str, int]) -> set[str]:
    result: set[str] = set()
    if observation["wall_time_us"] > limits["wall_time_us"]:
        result.add("wall_time_us")
    if observation["memory_peak_bytes"] > limits["memory_bytes"] or observation["memory_retained_bytes"] > limits["memory_bytes"]:
        result.add("memory_bytes")
    if observation["nesting_peak"] > limits["nesting_depth"] or observation["nesting_current"] > limits["nesting_depth"]:
        result.add("nesting_depth")
    return result


def _parse_budget_outcome(value: object) -> dict[str, object]:
    if type(value) is not dict:
        _fail("schema", "resource_budget.outcome", "outcome must be an object")
    status = value.get("status")
    if status in {"open", "completed"}:
        return _keys(value, {"status"}, "resource_budget.outcome")
    if status == "cancelled":
        item = _keys(value, {"status", "cancellation_id"}, "resource_budget.outcome")
        _identifier(item["cancellation_id"], "resource_budget.outcome.cancellation_id")
        return item
    if status == "exhausted":
        item = _keys(value, {"status", "exhaustion_id"}, "resource_budget.outcome")
        _identifier(item["exhaustion_id"], "resource_budget.outcome.exhaustion_id")
        return item
    if status == "truncated":
        item = _keys(value, {"status", "truncation_ids"}, "resource_budget.outcome")
        identifiers = item["truncation_ids"]
        if type(identifiers) is not list or not identifiers or len(identifiers) > RESOURCE_BUDGET_MAX_EVENTS:
            _fail("schema", "resource_budget.outcome.truncation_ids", "invalid truncation inventory")
        parsed = [_identifier(identifier, f"resource_budget.outcome.truncation_ids[{index}]") for index, identifier in enumerate(identifiers)]
        if parsed != sorted(parsed) or len(parsed) != len(set(parsed)):
            _fail("canonical", "resource_budget.outcome.truncation_ids", "truncation identities must be sorted and unique")
        return item
    _fail("schema", "resource_budget.outcome", "unknown outcome")


def _parse_resource_budget(data: bytes, *, require_open: bool | None = None) -> _BudgetState:
    value = _parse(data, "resource_budget", maximum=RESOURCE_BUDGET_MAX_BYTES)
    _budget_shape(value)
    expected = {"schema", "budget_id", "lineage", "policy", "limits", "events", "outcome", "extensions"}
    _keys(value, expected, "resource_budget")
    if value["schema"] != "mathhead.resource-budget.v1" or value["policy"] != _POLICY:
        _fail("budget", "resource_budget", "schema or policy differs")
    budget_id = _identifier(value["budget_id"], "resource_budget.budget_id")
    lineage = value["lineage"]
    if type(lineage) is not dict:
        _fail("budget", "resource_budget.lineage", "invalid lineage")
    if lineage.get("kind") == "root":
        _keys(lineage, {"kind"}, "resource_budget.lineage")
    elif lineage.get("kind") == "child":
        _keys(lineage, {"kind", "parent_budget_id", "parent_lease_id", "allocation_sha256"}, "resource_budget.lineage")
        parent_id = _identifier(lineage["parent_budget_id"], "resource_budget.lineage.parent_budget_id")
        _identifier(lineage["parent_lease_id"], "resource_budget.lineage.parent_lease_id")
        if parent_id == budget_id:
            _fail("lineage", "resource_budget.lineage.parent_budget_id", "child cannot name itself as parent")
        _digest(lineage["allocation_sha256"], "resource_budget.lineage.allocation_sha256")
    else:
        _fail("budget", "resource_budget.lineage", "invalid lineage")
    limits = _budget_vector(value["limits"], "resource_budget.limits")
    if lineage["kind"] == "child" and lineage["allocation_sha256"] != _sha(_canonical(limits)):
        _fail("lineage", "resource_budget.lineage.allocation_sha256", "child limits do not match allocation")
    outcome = _parse_budget_outcome(value["outcome"])
    if require_open is True and outcome["status"] != "open":
        _fail("budget", "resource_budget.outcome", "budget must be open")
    if require_open is False and outcome["status"] == "open":
        _fail("budget", "resource_budget.outcome", "budget must be terminal")
    _extensions(value["extensions"], "resource_budget.extensions")
    events = value["events"]
    if type(events) is not list or len(events) > RESOURCE_BUDGET_MAX_EVENTS:
        _fail("budget", "resource_budget.events", "event ledger is invalid")
    cumulative = {name: 0 for name in _CUMULATIVE}
    observation = _zero_observation()
    active: dict[str, dict[str, object]] = {}
    owners = {budget_id}
    child_ids: set[str] = set()
    closed: set[str] = set()
    cancellations: dict[str, dict[str, object]] = {}
    exhaustions: dict[str, dict[str, object]] = {}
    truncations: dict[str, dict[str, object]] = {}
    truncation_retained = {dimension: 0 for dimension in _TRUNCATABLE}
    must_exhaust: set[str] = set()
    terminal_sequence: int | None = None
    reconciliations: dict[str, dict[str, object]] = {}
    for sequence, raw_event in enumerate(events):
        path = f"resource_budget.events[{sequence}]"
        if type(raw_event) is not dict:
            _fail("budget", path, "event must be an object")
        event = raw_event
        if event.get("sequence") != sequence:
            _fail("budget", path, "event sequence differs")
        if terminal_sequence is not None:
            _fail("outcome", path, "event follows terminal event")
        _extensions(event.get("extensions"), f"{path}.extensions")
        _event_identifier(event, "event_id", path, owners)
        kind = event.get("kind")
        if must_exhaust and kind != "exhaust":
            _fail("exhaustion", path, "observed overrun requires immediate exhaustion")
        if kind == "charge":
            if set(event) != {"event_id", "sequence", "kind", "delta", "extensions"}:
                _fail("budget", path, "charge fields differ")
            delta_item = _keys(event["delta"], set(_CUMULATIVE), f"{path}.delta")
            delta = {name: _quantity(delta_item[name], f"{path}.delta.{name}") for name in _CUMULATIVE}
            if not any(delta.values()):
                _fail("budget", path, "charge is empty")
            reserved = _active_totals(active)
            for name in _CUMULATIVE:
                cumulative[name] += delta[name]
                if cumulative[name] > INTEGER_MAXIMUM:
                    _fail("budget", path, "charge aggregate exceeds exact range")
                if cumulative[name] + reserved[name] > limits[name]:
                    _fail("budget", path, "charge exceeds a limit")
        elif kind == "sample":
            if set(event) != {"event_id", "sequence", "kind", "observation", "extensions"}:
                _fail("budget", path, "sample fields differ")
            sample_item = _keys(event["observation"], set(observation), f"{path}.observation")
            sample = {name: _quantity(sample_item[name], f"{path}.observation.{name}") for name in observation}
            if sample["wall_time_us"] < observation["wall_time_us"] or sample["memory_peak_bytes"] < observation["memory_peak_bytes"] or sample["nesting_peak"] < observation["nesting_peak"] or sample["memory_retained_bytes"] > sample["memory_peak_bytes"] or sample["nesting_current"] > sample["nesting_peak"]:
                _fail("budget", path, "observation is not valid and monotonic")
            observation = sample
            must_exhaust.update(_observed_overruns(limits, observation))
        elif kind == "reserve":
            expected_reserve = {"event_id", "sequence", "kind", "lease_id", "child_budget_id", "allocation", "allocation_sha256", "extensions"}
            if set(event) != expected_reserve:
                _fail("budget", path, "reserve fields differ")
            lease = _event_identifier(event, "lease_id", path, owners)
            child = _event_identifier(event, "child_budget_id", path, owners)
            if lease in active or lease in closed or child in child_ids:
                _fail("budget", path, "lease or child is reused")
            allocation = _budget_vector(event["allocation"], f"{path}.allocation")
            if not any(allocation.values()) or event["allocation_sha256"] != _sha(_canonical(allocation)):
                _fail("budget", path, "allocation identity differs")
            if len(active) >= RESOURCE_BUDGET_MAX_ACTIVE_LEASES:
                _fail("budget", path, "active child lease count exceeds its ceiling")
            reserved = _active_totals(active)
            effective = {**cumulative, "wall_time_us": observation["wall_time_us"], "memory_bytes": observation["memory_retained_bytes"], "nesting_depth": observation["nesting_current"]}
            if any(effective[name] + reserved[name] + allocation[name] > limits[name] for name in RESOURCE_DIMENSIONS):
                _fail("budget", path, "reservation exceeds available capacity")
            active[lease] = {"allocation": allocation, "child_budget_id": child, "wall_start": observation["wall_time_us"], "memory_current_start": observation["memory_retained_bytes"], "nesting_current_start": observation["nesting_current"]}
            child_ids.add(child)
        elif kind == "reconcile":
            expected_reconcile = {"event_id", "sequence", "kind", "lease_id", "child_budget_sha256", "child_outcome", "child_usage", "refund", "overrun", "extensions"}
            if set(event) != expected_reconcile:
                _fail("budget", path, "reconcile fields differ")
            lease = _identifier(event["lease_id"], f"{path}.lease_id")
            if lease not in active:
                _fail("budget", path, "reconciliation has no active lease")
            _digest(event["child_budget_sha256"], f"{path}.child_budget_sha256")
            if event["child_outcome"] not in {"completed", "cancelled", "exhausted", "truncated"}:
                _fail("budget", path, "child outcome differs")
            usage = _parse_usage_mapping(event["child_usage"], f"{path}.child_usage")
            refund = _budget_vector(event["refund"], f"{path}.refund")
            overrun = _budget_vector(event["overrun"], f"{path}.overrun")
            allocation = active[lease]["allocation"]
            assert isinstance(allocation, dict)
            mapped = _usage_as_limit(usage)
            has_overrun = False
            for name in RESOURCE_DIMENSIONS:
                if allocation[name] + overrun[name] != mapped[name] + refund[name] or (overrun[name] and refund[name]):
                    _fail("budget", path, "reconciliation does not conserve allocation")
                has_overrun = has_overrun or overrun[name] > 0
            if has_overrun and event["child_outcome"] != "exhausted":
                _fail("outcome", path, "child overrun requires exhausted outcome")
            lease_value = active[lease]
            if observation["wall_time_us"] < lease_value["wall_start"] + usage["wall_time_us"] or observation["memory_peak_bytes"] < usage["memory_peak_bytes"] or observation["nesting_peak"] < lease_value["nesting_current_start"] + usage["nesting_peak"]:
                _fail("observation", path, "parent observation does not cover child usage")
            for name in _CUMULATIVE:
                cumulative[name] += usage[name]
                if cumulative[name] > INTEGER_MAXIMUM:
                    _fail("budget", path, "reconciled aggregate exceeds exact range")
                if cumulative[name] > limits[name]:
                    must_exhaust.add(name)
            reconciliations[lease] = {"event": event, "lease": lease_value}
            del active[lease]
            closed.add(lease)
        elif kind == "cancel":
            required = {"event_id", "sequence", "kind", "cancellation_id", "source", "observed_wall_time_us", "reason", "extensions"}
            if set(event) != required or event["source"] not in {"user", "parent", "supervisor"}:
                _fail("budget", path, "cancellation fields differ")
            if active or cancellations or exhaustions:
                _fail("cancellation", path, "cancellation has active children or prior terminal state")
            identifier = _event_identifier(event, "cancellation_id", path, owners)
            if _quantity(event["observed_wall_time_us"], f"{path}.observed_wall_time_us") != observation["wall_time_us"]:
                _fail("cancellation", path, "cancellation wall time is not the latest sample")
            _reason(event["reason"], f"{path}.reason")
            cancellations[identifier] = event
            terminal_sequence = sequence
        elif kind == "exhaust":
            required = {"event_id", "sequence", "kind", "exhaustion_id", "dimensions", "requested", "reason", "extensions"}
            if set(event) != required or active or cancellations or exhaustions:
                _fail("exhaustion", path, "exhaustion fields or terminal state differ")
            identifier = _event_identifier(event, "exhaustion_id", path, owners)
            dimensions_value = event["dimensions"]
            if type(dimensions_value) is not list or not dimensions_value or len(dimensions_value) > len(RESOURCE_DIMENSIONS):
                _fail("exhaustion", f"{path}.dimensions", "invalid exhausted dimensions")
            dimensions = [_text(name, f"{path}.dimensions[{index}]", maximum=32) for index, name in enumerate(dimensions_value)]
            if any(name not in RESOURCE_DIMENSIONS for name in dimensions) or dimensions != sorted(dimensions) or len(dimensions) != len(set(dimensions)):
                _fail("exhaustion", f"{path}.dimensions", "dimensions must be sorted, unique, and closed")
            requested = _budget_vector(event["requested"], f"{path}.requested")
            if not any(requested.values()):
                _fail("exhaustion", f"{path}.requested", "exhaustion request must be positive")
            reserved = _active_totals(active)
            effective = {**cumulative, "wall_time_us": observation["wall_time_us"], "memory_bytes": observation["memory_retained_bytes"], "nesting_depth": observation["nesting_current"]}
            unavailable = set(must_exhaust)
            for name in RESOURCE_DIMENSIONS:
                if effective[name] + reserved[name] + requested[name] > limits[name]:
                    unavailable.add(name)
            if set(dimensions) != unavailable:
                _fail("exhaustion", path, "dimensions do not match unavailable resources")
            _reason(event["reason"], f"{path}.reason")
            exhaustions[identifier] = event
            terminal_sequence = sequence
        elif kind == "truncate":
            required = {"event_id", "sequence", "kind", "truncation_id", "dimension", "subject_id", "strategy", "original", "retained", "omitted", "retained_sha256", "extensions"}
            if set(event) != required:
                _fail("budget", path, "truncation fields differ")
            identifier = _event_identifier(event, "truncation_id", path, owners)
            dimension = _text(event["dimension"], f"{path}.dimension", maximum=32)
            _identifier(event["subject_id"], f"{path}.subject_id")
            strategy = _text(event["strategy"], f"{path}.strategy", maximum=16)
            original = _quantity(event["original"], f"{path}.original")
            retained = _quantity(event["retained"], f"{path}.retained")
            omitted = _quantity(event["omitted"], f"{path}.omitted")
            retained_sha = event["retained_sha256"]
            if dimension not in _TRUNCATABLE or strategy not in {"prefix", "suffix", "sample", "refuse"}:
                _fail("truncation", path, "truncation enum differs")
            if original != retained + omitted or omitted == 0 or retained > limits[dimension]:
                _fail("truncation", path, "truncation conservation or limit differs")
            refused = strategy == "refuse"
            if refused != (retained == 0 and retained_sha is None):
                _fail("truncation", path, "refusal state differs")
            if not refused and (retained == 0 or retained_sha is None):
                _fail("truncation", path, "retained truncation requires bytes and identity")
            if retained_sha is not None:
                _digest(retained_sha, f"{path}.retained_sha256")
            truncations[identifier] = event
            truncation_retained[dimension] += retained
            if truncation_retained[dimension] > INTEGER_MAXIMUM:
                _fail("budget", path, "retained truncation aggregate exceeds exact range")
        else:
            _fail("budget", path, "unknown event kind")
    for dimension, retained in truncation_retained.items():
        if retained > cumulative[dimension]:
            _fail("truncation", "resource_budget.events", "retained truncation was not charged")
    status = outcome["status"]
    if status != "open" and active:
        _fail("outcome", "resource_budget.outcome", "terminal budget has active child leases")
    if status == "open":
        if cancellations or exhaustions or must_exhaust:
            _fail("outcome", "resource_budget.outcome", "open budget hides terminal resource state")
    elif status == "completed":
        if cancellations or exhaustions or truncations or must_exhaust:
            _fail("outcome", "resource_budget.outcome", "completion hides a non-success state")
    elif status == "cancelled":
        if set(cancellations) != {outcome["cancellation_id"]} or exhaustions or must_exhaust:
            _fail("outcome", "resource_budget.outcome", "cancelled outcome does not bind its event")
    elif status == "exhausted":
        if set(exhaustions) != {outcome["exhaustion_id"]} or cancellations:
            _fail("outcome", "resource_budget.outcome", "exhausted outcome does not bind its event")
        dimensions = set(exhaustions[outcome["exhaustion_id"]]["dimensions"])
        if not must_exhaust <= dimensions:
            _fail("outcome", "resource_budget.outcome", "exhaustion omits an observed overrun")
    elif status == "truncated":
        if outcome["truncation_ids"] != sorted(truncations) or cancellations or exhaustions or must_exhaust:
            _fail("outcome", "resource_budget.outcome", "truncated outcome does not bind all truncations")
    return _BudgetState(value=value, cumulative=cumulative, observation=observation, active=active, owners=owners, reconciliations=reconciliations)


def _parse_parent_budget(data: bytes) -> _BudgetState:
    return _parse_resource_budget(data, require_open=True)


def _derived_budget_usage(state: _BudgetState) -> dict[str, int]:
    return {
        **state.cumulative,
        "wall_time_us": state.observation["wall_time_us"],
        "memory_peak_bytes": state.observation["memory_peak_bytes"],
        "memory_retained_bytes": state.observation["memory_retained_bytes"],
        "nesting_peak": state.observation["nesting_peak"],
    }


def _validate_result_budgets(
    child_budget: bytes,
    parent_budget: bytes,
    usage: WorkerResourceUsage | None,
    status: str,
) -> None:
    child = _parse_resource_budget(child_budget, require_open=False)
    parent = _parse_resource_budget(parent_budget, require_open=True)
    lineage = child.value["lineage"]
    assert isinstance(lineage, dict)
    if lineage["kind"] != "child" or lineage["parent_budget_id"] != parent.value["budget_id"]:
        _fail("lineage", "child_budget.lineage", "child does not name the returned parent")
    lease_id = lineage["parent_lease_id"]
    reconciliation = parent.reconciliations.get(lease_id)
    if reconciliation is None:
        _fail("accounting", "parent_budget.events", "parent does not reconcile the child lease")
    event = reconciliation["event"]
    lease = reconciliation["lease"]
    assert isinstance(event, dict) and isinstance(lease, dict)
    if event["child_budget_sha256"] != _sha(child_budget):
        _fail("identity", "parent_budget.events", "reconciliation does not bind child bytes")
    if lease["child_budget_id"] != child.value["budget_id"] or lease["allocation"] != child.value["limits"]:
        _fail("lineage", "parent_budget.events", "reservation and child lineage differ")
    child_outcome = child.value["outcome"]
    assert isinstance(child_outcome, dict)
    if event["child_outcome"] != child_outcome["status"] or event["child_usage"] != _derived_budget_usage(child):
        _fail("accounting", "parent_budget.events", "reconciliation does not replay child outcome and usage")
    expected_outcome = "cancelled" if status == "cancelled" else "exhausted" if status == "exhausted" else "completed"
    if child_outcome["status"] != expected_outcome:
        _fail("outcome", "child_budget.outcome", "worker status and child budget outcome differ")
    if usage is None:
        _fail("accounting", "$.usage", "reconciled result requires resource usage")
    limits = child.value["limits"]
    assert isinstance(limits, dict)
    expected_usage = {
        "wall_time_us": min(usage.wall_time_us, limits["wall_time_us"]),
        "cpu_time_us": min(usage.cpu_time_us, limits["cpu_time_us"]),
        "memory_peak_bytes": min(usage.memory_peak_bytes, limits["memory_bytes"]),
        "memory_retained_bytes": 0,
        "solver_calls": min(usage.solver_calls, limits["solver_calls"]),
        "generated_objects": min(usage.generated_objects, limits["generated_objects"]),
        "proof_bytes": min(usage.proof_bytes, limits["proof_bytes"]),
        "evidence_bytes": min(usage.evidence_bytes, limits["evidence_bytes"]),
        "output_bytes": min(usage.output_bytes, limits["output_bytes"]),
        "diagnostic_bytes": min(usage.diagnostic_bytes, limits["diagnostic_bytes"]),
        "nesting_peak": min(usage.nesting_peak, limits["nesting_depth"]),
    }
    if expected_usage != _derived_budget_usage(child):
        _fail("accounting", "child_budget.events", "child ledger does not bind result usage")


def _reserve_budget(state: _BudgetState, request: IsolatedWorkerRequest) -> None:
    if request.lease_id in state.owners or request.child_budget_id in state.owners:
        raise _OrdinaryFailure("invalid", "BUDGET_INVALID", "lease or child identity is already used")
    limits = state.value["limits"]
    assert isinstance(limits, dict)
    requested = _vector_mapping(request.resource_limits)
    reserved = _active_totals(state.active)
    effective = {**state.cumulative, "wall_time_us": state.observation["wall_time_us"], "memory_bytes": state.observation["memory_retained_bytes"], "nesting_depth": state.observation["nesting_current"]}
    if not any(requested.values()) or any(effective[name] + reserved[name] + requested[name] > limits[name] for name in RESOURCE_DIMENSIONS):
        raise _OrdinaryFailure("refused", "BUDGET_INSUFFICIENT", "child allocation does not fit the parent")
    token = request.request_sha256[:20]
    event_id = f"reserve_{token}"
    if event_id in state.owners:
        raise _OrdinaryFailure("invalid", "BUDGET_INVALID", "derived reserve identity collides")
    event = {"event_id": event_id, "sequence": len(state.value["events"]), "kind": "reserve", "lease_id": request.lease_id, "child_budget_id": request.child_budget_id, "allocation": requested, "allocation_sha256": _sha(_canonical(requested)), "extensions": {}}
    state.value["events"].append(event)
    state.owners.update({event_id, request.lease_id, request.child_budget_id})
    state.active[request.lease_id] = {"allocation": requested, "child_budget_id": request.child_budget_id, "wall_start": state.observation["wall_time_us"], "memory_current_start": state.observation["memory_retained_bytes"], "nesting_current_start": state.observation["nesting_current"]}


def _child_budget(request: IsolatedWorkerRequest, usage: WorkerResourceUsage, resource_reason: str | None, *, cancelled: bool = False) -> tuple[dict[str, object], str]:
    limits = _vector_mapping(request.resource_limits)
    mapped_usage = {
        "wall_time_us": min(usage.wall_time_us, limits["wall_time_us"]),
        "cpu_time_us": min(usage.cpu_time_us, limits["cpu_time_us"]),
        "memory_peak_bytes": min(usage.memory_peak_bytes, limits["memory_bytes"]),
        "memory_retained_bytes": 0,
        "solver_calls": min(usage.solver_calls, limits["solver_calls"]),
        "generated_objects": min(usage.generated_objects, limits["generated_objects"]),
        "proof_bytes": min(usage.proof_bytes, limits["proof_bytes"]),
        "evidence_bytes": min(usage.evidence_bytes, limits["evidence_bytes"]),
        "output_bytes": min(usage.output_bytes, limits["output_bytes"]),
        "diagnostic_bytes": min(usage.diagnostic_bytes, limits["diagnostic_bytes"]),
        "nesting_peak": min(usage.nesting_peak, limits["nesting_depth"]),
    }
    events: list[dict[str, object]] = []
    cumulative = {name: mapped_usage[name] for name in _CUMULATIVE}
    if any(cumulative.values()):
        events.append({"event_id": "worker_charge", "sequence": len(events), "kind": "charge", "delta": cumulative, "extensions": {}})
    observation = {"wall_time_us": mapped_usage["wall_time_us"], "memory_peak_bytes": mapped_usage["memory_peak_bytes"], "memory_retained_bytes": 0, "nesting_current": 0, "nesting_peak": mapped_usage["nesting_peak"]}
    if any(observation.values()):
        events.append({"event_id": "worker_sample", "sequence": len(events), "kind": "sample", "observation": observation, "extensions": {}})
    if resource_reason is not None:
        dimension_by_reason = {"WALL_TIME_EXHAUSTED": "wall_time_us", "CPU_TIME_EXHAUSTED": "cpu_time_us", "MEMORY_EXHAUSTED": "memory_bytes", "OUTPUT_EXHAUSTED": "output_bytes", "DIAGNOSTIC_EXHAUSTED": "diagnostic_bytes"}
        dimension = dimension_by_reason[resource_reason]
        requested = _zero_limit()
        requested[dimension] = 1
        events.append({"event_id": "worker_exhaust", "sequence": len(events), "kind": "exhaust", "exhaustion_id": "worker_exhaustion", "dimensions": [dimension], "requested": requested, "reason": resource_reason.lower(), "extensions": {}})
        outcome: dict[str, object] = {"status": "exhausted", "exhaustion_id": "worker_exhaustion"}
        child_outcome = "exhausted"
    elif cancelled:
        events.append({"event_id": "worker_cancel", "sequence": len(events), "kind": "cancel", "cancellation_id": "worker_cancellation", "source": "supervisor", "observed_wall_time_us": observation["wall_time_us"], "reason": "worker cancellation observed", "extensions": {}})
        outcome = {"status": "cancelled", "cancellation_id": "worker_cancellation"}
        child_outcome = "cancelled"
    else:
        outcome = {"status": "completed"}
        child_outcome = "completed"
    child = {"schema": "mathhead.resource-budget.v1", "budget_id": request.child_budget_id, "lineage": {"kind": "child", "parent_budget_id": "placeholder", "parent_lease_id": request.lease_id, "allocation_sha256": _sha(_canonical(limits))}, "policy": dict(_POLICY), "limits": limits, "events": events, "outcome": outcome, "extensions": {}}
    return child, child_outcome


def _reconcile_budget(state: _BudgetState, request: IsolatedWorkerRequest, child: dict[str, object], child_outcome: str, usage: WorkerResourceUsage) -> bytes:
    child["lineage"]["parent_budget_id"] = state.value["budget_id"]
    child_raw = _canonical(child)
    limits = _vector_mapping(request.resource_limits)
    used = _parse_usage_mapping({
        "wall_time_us": min(usage.wall_time_us, limits["wall_time_us"]),
        "cpu_time_us": min(usage.cpu_time_us, limits["cpu_time_us"]),
        "memory_peak_bytes": min(usage.memory_peak_bytes, limits["memory_bytes"]),
        "memory_retained_bytes": 0,
        "solver_calls": min(usage.solver_calls, limits["solver_calls"]),
        "generated_objects": min(usage.generated_objects, limits["generated_objects"]),
        "proof_bytes": min(usage.proof_bytes, limits["proof_bytes"]),
        "evidence_bytes": min(usage.evidence_bytes, limits["evidence_bytes"]),
        "output_bytes": min(usage.output_bytes, limits["output_bytes"]),
        "diagnostic_bytes": min(usage.diagnostic_bytes, limits["diagnostic_bytes"]),
        "nesting_peak": min(usage.nesting_peak, limits["nesting_depth"]),
    }, "child_usage")
    observation = {
        "wall_time_us": state.observation["wall_time_us"] + used["wall_time_us"],
        "memory_peak_bytes": max(state.observation["memory_peak_bytes"], used["memory_peak_bytes"]),
        "memory_retained_bytes": state.observation["memory_retained_bytes"],
        "nesting_current": state.observation["nesting_current"],
        "nesting_peak": max(state.observation["nesting_peak"], state.observation["nesting_current"] + used["nesting_peak"]),
    }
    token = request.request_sha256[:20]
    sample_id = f"sample_{token}"
    reconcile_id = f"reconcile_{token}"
    if sample_id in state.owners or reconcile_id in state.owners:
        _fail("accounting", "$", "derived reconciliation identity collides")
    events = state.value["events"]
    assert isinstance(events, list)
    events.append({"event_id": sample_id, "sequence": len(events), "kind": "sample", "observation": observation, "extensions": {}})
    mapped = _usage_as_limit(used)
    refund = {name: limits[name] - mapped[name] for name in RESOURCE_DIMENSIONS}
    events.append({"event_id": reconcile_id, "sequence": len(events), "kind": "reconcile", "lease_id": request.lease_id, "child_budget_sha256": _sha(child_raw), "child_outcome": child_outcome, "child_usage": used, "refund": refund, "overrun": _zero_limit(), "extensions": {}})
    del state.active[request.lease_id]
    return child_raw


@dataclass(slots=True)
class _ProcessObservation:
    exit_code: int | None
    termination_signal: int | None
    wall_time_us: int
    cpu_time_us: int
    memory_peak_bytes: int
    stdout: bytes
    stdout_size: int
    stderr: bytes
    stderr_size: int
    reason: str
    tree_terminated: bool
    usage_complete: bool


def _validated_root(workspace_root: str) -> Path:
    if type(workspace_root) is not str or not workspace_root or "\x00" in workspace_root:
        raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "workspace root is invalid")
    path = Path(workspace_root)
    if not path.is_absolute() or path == Path(path.anchor):
        raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "workspace root must be a non-root absolute path")
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise _OrdinaryFailure("refused", "LAUNCH_FAILED", "workspace root is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode) or resolved != path:
        raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "workspace root must be a real exact directory")
    return path


def _validated_executable(executable_path: str, expected_sha256: str) -> Path:
    if type(executable_path) is not str or not executable_path or "\x00" in executable_path:
        raise _OrdinaryFailure("invalid", "EXECUTABLE_INVALID", "executable path is invalid")
    path = Path(executable_path)
    if not path.is_absolute():
        raise _OrdinaryFailure("invalid", "EXECUTABLE_INVALID", "executable path must be absolute")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_EXECUTABLE_BYTES:
            raise _OrdinaryFailure("invalid", "EXECUTABLE_INVALID", "executable is not one bounded regular file")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = handle.read(1_048_576)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_EXECUTABLE_BYTES:
                    raise _OrdinaryFailure("invalid", "EXECUTABLE_INVALID", "executable exceeds its byte ceiling")
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except _OrdinaryFailure:
        raise
    except OSError as exc:
        raise _OrdinaryFailure("refused", "EXECUTABLE_INVALID", "executable cannot be read") from exc
    identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    if identity != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) or identity != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) or digest.hexdigest() != expected_sha256:
        raise _OrdinaryFailure("invalid", "EXECUTABLE_INVALID", "executable bytes or identity differ")
    if os.name != "nt" and not os.access(path, os.X_OK):
        raise _OrdinaryFailure("refused", "EXECUTABLE_INVALID", "executable permission is absent")
    return path


def _environment(root: Path) -> dict[str, str]:
    home = root / "home"
    temporary = root / "tmp"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    result = {
        "HOME": str(home), "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0", "PYTHONNOUSERSITE": "1", "TMPDIR": str(temporary),
        "TEMP": str(temporary), "TMP": str(temporary),
    }
    if os.name == "nt":
        for name in ("SystemRoot", "WINDIR", "ComSpec", "PATHEXT"):
            value = os.environ.get(name)
            if value:
                result[name] = value
    return result


def _posix_limits(limits: WorkerResourceVector):
    def apply() -> None:
        import resource  # noqa: PLC0415
        cpu_seconds = max(1, math.ceil(limits.cpu_time_us / 1_000_000))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
        file_limit = min(INTEGER_MAXIMUM, max(limits.output_bytes, limits.diagnostic_bytes) + 1)
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        descriptor_limit = min(64, resource.getrlimit(resource.RLIMIT_NOFILE)[1])
        resource.setrlimit(resource.RLIMIT_NOFILE, (descriptor_limit, descriptor_limit))
    return apply


def _posix_group_alive(pid: int) -> bool:
    try:
        os.killpg(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _terminate_posix_group(pid: int) -> bool:
    if not _posix_group_alive(pid):
        return True
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + GRACE_SECONDS
    while time.monotonic() < deadline and _posix_group_alive(pid):
        time.sleep(POLL_SECONDS)
    if _posix_group_alive(pid):
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            return True
    # The root may remain as a zombie until the caller's following wait4.  A
    # successful group-wide SIGKILL establishes termination; liveness is
    # checked again by tree tests after the root has been reaped.
    return True


def _read_bounded(handle: Any, limit: int) -> tuple[bytes, int]:
    size = os.fstat(handle.fileno()).st_size
    handle.seek(0)
    return handle.read(min(size, limit)), size


def _run_posix(command: list[str], root: Path, environment: dict[str, str], limits: WorkerResourceVector, cancel_event: Event | None) -> _ProcessObservation:
    with tempfile.TemporaryFile(mode="w+b", dir=root) as stdout_file, tempfile.TemporaryFile(mode="w+b", dir=root) as stderr_file:
        try:
            process = subprocess.Popen(
                command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                stdout=stdout_file, stderr=stderr_file, close_fds=True, shell=False,
                start_new_session=True, preexec_fn=_posix_limits(limits),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise _OrdinaryFailure("failed", "LAUNCH_FAILED", f"worker launch failed: {type(exc).__name__}") from exc
        started = time.monotonic_ns()
        deadline = started + limits.wall_time_us * 1_000
        reason = "COMPLETED"
        status_value: int | None = None
        rusage: Any = None
        try:
            while status_value is None:
                try:
                    waited_pid, wait_status, current_usage = os.wait4(process.pid, os.WNOHANG)
                except ChildProcessError:
                    waited_pid, wait_status, current_usage = process.pid, 0, None
                if waited_pid == process.pid:
                    status_value = wait_status
                    rusage = current_usage
                    process.returncode = os.waitstatus_to_exitcode(wait_status)
                    break
                stdout_size = os.fstat(stdout_file.fileno()).st_size
                stderr_size = os.fstat(stderr_file.fileno()).st_size
                if cancel_event is not None and cancel_event.is_set():
                    reason = "CANCELLED"
                    break
                if stdout_size > limits.output_bytes:
                    reason = "OUTPUT_EXHAUSTED"
                    break
                if stderr_size > limits.diagnostic_bytes:
                    reason = "DIAGNOSTIC_EXHAUSTED"
                    break
                if time.monotonic_ns() >= deadline:
                    reason = "WALL_TIME_EXHAUSTED"
                    break
                time.sleep(POLL_SECONDS)
        except BaseException:
            _terminate_posix_group(process.pid)
            if process.returncode is None:
                try:
                    waited_pid, wait_status, _usage = os.wait4(process.pid, 0)
                    if waited_pid == process.pid:
                        process.returncode = os.waitstatus_to_exitcode(wait_status)
                except (ChildProcessError, OSError):
                    pass
            raise
        tree_terminated = _terminate_posix_group(process.pid)
        if status_value is None:
            try:
                waited_pid, wait_status, current_usage = os.wait4(process.pid, 0)
                if waited_pid == process.pid:
                    status_value = wait_status
                    rusage = current_usage
                    process.returncode = os.waitstatus_to_exitcode(wait_status)
            except (ChildProcessError, OSError):
                pass
        wall = max(0, (time.monotonic_ns() - started) // 1_000)
        stdout, stdout_size = _read_bounded(stdout_file, limits.output_bytes)
        stderr, stderr_size = _read_bounded(stderr_file, limits.diagnostic_bytes)
        returncode = process.returncode
        termination_signal = -returncode if returncode is not None and returncode < 0 else None
        exit_code = returncode if returncode is not None and returncode >= 0 else None
        cpu = 0 if rusage is None else max(0, int((rusage.ru_utime + rusage.ru_stime) * 1_000_000))
        memory = 0 if rusage is None else max(0, int(rusage.ru_maxrss * (1 if sys.platform == "darwin" else 1024)))
        if reason == "COMPLETED" and not tree_terminated:
            reason = "TREE_CLEANUP_FAILED"
        elif reason == "COMPLETED" and returncode != 0:
            if termination_signal == getattr(signal, "SIGXCPU", -1) or cpu >= (limits.cpu_time_us * 9) // 10:
                reason = "CPU_TIME_EXHAUSTED"
            elif termination_signal in {getattr(signal, "SIGKILL", -1), getattr(signal, "SIGSEGV", -1)}:
                reason = "MEMORY_EXHAUSTED"
            else:
                reason = "EXIT_FAILED"
        return _ProcessObservation(exit_code=exit_code, termination_signal=termination_signal, wall_time_us=wall, cpu_time_us=cpu, memory_peak_bytes=memory, stdout=stdout, stdout_size=stdout_size, stderr=stderr, stderr_size=stderr_size, reason=reason, tree_terminated=tree_terminated, usage_complete=rusage is not None)


def _run_windows(command: list[str], root: Path, environment: dict[str, str], limits: WorkerResourceVector, cancel_event: Event | None) -> _ProcessObservation:
    """Launch suspended, assign a kill-on-close Job Object, then resume."""
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415

    ULONG_PTR = ctypes.c_size_t

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ULONG_PTR), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD),
        ]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION), ("IoInfo", IO_COUNTERS), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t), ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
        _fields_ = [("TotalUserTime", ctypes.c_longlong), ("TotalKernelTime", ctypes.c_longlong), ("ThisPeriodTotalUserTime", ctypes.c_longlong), ("ThisPeriodTotalKernelTime", ctypes.c_longlong), ("TotalPageFaultCount", wintypes.DWORD), ("TotalProcesses", wintypes.DWORD), ("ActiveProcesses", wintypes.DWORD), ("TotalTerminatedProcesses", wintypes.DWORD)]

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ThreadID", wintypes.DWORD), ("th32OwnerProcessID", wintypes.DWORD), ("tpBasePri", wintypes.LONG), ("tpDeltaPri", wintypes.LONG), ("dwFlags", wintypes.DWORD)]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise _OrdinaryFailure("unsupported", "ISOLATION_UNSUPPORTED", "Windows Job Object creation failed")
    process: subprocess.Popen[bytes] | None = None
    with tempfile.TemporaryFile(mode="w+b", dir=root) as stdout_file, tempfile.TemporaryFile(mode="w+b", dir=root) as stderr_file:
        try:
            extended = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            extended.BasicLimitInformation.LimitFlags = 0x00002000 | 0x00000004 | 0x00000200
            extended.BasicLimitInformation.PerJobUserTimeLimit = max(1, limits.cpu_time_us * 10)
            extended.JobMemoryLimit = limits.memory_bytes
            if not kernel32.SetInformationJobObject(job, 9, ctypes.byref(extended), ctypes.sizeof(extended)):
                raise _OrdinaryFailure("unsupported", "ISOLATION_UNSUPPORTED", "Windows Job Object limits are unavailable")
            process = subprocess.Popen(
                command, cwd=root, env=environment, stdin=subprocess.DEVNULL,
                stdout=stdout_file, stderr=stderr_file, close_fds=True, shell=False,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_SUSPENDED,
            )
            process_handle = wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]
            if not kernel32.AssignProcessToJobObject(job, process_handle):
                raise _OrdinaryFailure("unsupported", "ISOLATION_UNSUPPORTED", "worker cannot be assigned before resumption")
            snapshot = kernel32.CreateToolhelp32Snapshot(0x00000004, 0)
            resumed = False
            if snapshot and snapshot != wintypes.HANDLE(-1).value:
                entry = THREADENTRY32()
                entry.dwSize = ctypes.sizeof(entry)
                present = kernel32.Thread32First(snapshot, ctypes.byref(entry))
                while present:
                    if entry.th32OwnerProcessID == process.pid:
                        thread = kernel32.OpenThread(0x0002, False, entry.th32ThreadID)
                        if thread:
                            if kernel32.ResumeThread(thread) != 0xFFFFFFFF:
                                resumed = True
                            kernel32.CloseHandle(thread)
                    present = kernel32.Thread32Next(snapshot, ctypes.byref(entry))
                kernel32.CloseHandle(snapshot)
            if not resumed:
                raise _OrdinaryFailure("failed", "LAUNCH_FAILED", "suspended worker thread cannot be resumed")
            started = time.monotonic_ns()
            deadline = started + limits.wall_time_us * 1_000
            reason = "COMPLETED"
            while process.poll() is None:
                stdout_size = os.fstat(stdout_file.fileno()).st_size
                stderr_size = os.fstat(stderr_file.fileno()).st_size
                if cancel_event is not None and cancel_event.is_set():
                    reason = "CANCELLED"
                    break
                if stdout_size > limits.output_bytes:
                    reason = "OUTPUT_EXHAUSTED"
                    break
                if stderr_size > limits.diagnostic_bytes:
                    reason = "DIAGNOSTIC_EXHAUSTED"
                    break
                if time.monotonic_ns() >= deadline:
                    reason = "WALL_TIME_EXHAUSTED"
                    break
                time.sleep(POLL_SECONDS)
            accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
            queried_accounting = bool(kernel32.QueryInformationJobObject(job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None))
            queried_extended = bool(kernel32.QueryInformationJobObject(job, 9, ctypes.byref(extended), ctypes.sizeof(extended), None))
            terminated = bool(kernel32.TerminateJobObject(job, 1))
            try:
                process.wait(timeout=FORCE_SECONDS)
            except subprocess.TimeoutExpired:
                terminated = False
            wall = max(0, (time.monotonic_ns() - started) // 1_000)
            stdout, stdout_size = _read_bounded(stdout_file, limits.output_bytes)
            stderr, stderr_size = _read_bounded(stderr_file, limits.diagnostic_bytes)
            returncode = process.returncode
            cpu = 0 if not queried_accounting else max(0, (accounting.TotalUserTime + accounting.TotalKernelTime) // 10)
            memory = 0 if not queried_extended else max(0, int(extended.PeakJobMemoryUsed))
            if reason == "COMPLETED" and not terminated:
                reason = "TREE_CLEANUP_FAILED"
            elif reason == "COMPLETED" and returncode != 0:
                if cpu >= limits.cpu_time_us:
                    reason = "CPU_TIME_EXHAUSTED"
                elif memory >= limits.memory_bytes:
                    reason = "MEMORY_EXHAUSTED"
                else:
                    reason = "EXIT_FAILED"
            return _ProcessObservation(exit_code=returncode, termination_signal=None, wall_time_us=wall, cpu_time_us=cpu, memory_peak_bytes=memory, stdout=stdout, stdout_size=stdout_size, stderr=stderr, stderr_size=stderr_size, reason=reason, tree_terminated=terminated, usage_complete=queried_accounting and queried_extended)
        except BaseException:
            if process is not None:
                kernel32.TerminateJobObject(job, 1)
                try:
                    process.wait(timeout=FORCE_SECONDS)
                except (OSError, subprocess.SubprocessError):
                    pass
            raise
        finally:
            kernel32.CloseHandle(job)


def _result_mapping(value: IsolatedWorkerResult, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema, "contract_id": value.contract_id,
        "contract_sha256": value.contract_sha256,
        "resource_budget_contract_sha256": value.resource_budget_contract_sha256,
        "deterministic_planner_contract_sha256": value.deterministic_planner_contract_sha256,
        "status": value.status, "reason_code": value.reason_code,
        "request_sha256": value.request_sha256,
        "planning_result_sha256": value.planning_result_sha256,
        "strategy_sha256": value.strategy_sha256,
        "capability": None if value.capability is None else _capability_mapping(value.capability),
        "usage": None if value.usage is None else _usage_mapping(value.usage),
        "artifacts": [_artifact_mapping(item) for item in value.artifacts],
        "diagnostics": [_diagnostic_mapping(item) for item in value.diagnostics],
        "child_budget_sha256": value.child_budget_sha256,
        "parent_budget_sha256": value.parent_budget_sha256,
        "tree_terminated": value.tree_terminated, "lease_reconciled": value.lease_reconciled,
        "semantic_sha256": value.semantic_sha256,
        "result_sha256": value.result_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _semantic_preimage(mapping: dict[str, object]) -> dict[str, object]:
    return {
        "schema": mapping["schema"], "contract_id": mapping["contract_id"],
        "contract_sha256": mapping["contract_sha256"], "status": mapping["status"],
        "reason_code": mapping["reason_code"], "request_sha256": mapping["request_sha256"],
        "planning_result_sha256": mapping["planning_result_sha256"], "strategy_sha256": mapping["strategy_sha256"],
        "capability": mapping["capability"], "artifacts": mapping["artifacts"],
        "diagnostics": mapping["diagnostics"], "tree_terminated": mapping["tree_terminated"],
        "lease_reconciled": mapping["lease_reconciled"], "mathematical_authority": False,
    }


def _result_from_mapping(value: object, *, artifact_payloads: tuple[bytes, ...] = (), child_budget: bytes | None = None, parent_budget: bytes | None = None) -> IsolatedWorkerResult:
    fields = {"schema", "contract_id", "contract_sha256", "resource_budget_contract_sha256", "deterministic_planner_contract_sha256", "status", "reason_code", "request_sha256", "planning_result_sha256", "strategy_sha256", "capability", "usage", "artifacts", "diagnostics", "child_budget_sha256", "parent_budget_sha256", "tree_terminated", "lease_reconciled", "semantic_sha256", "result_sha256", "mathematical_authority"}
    item = _keys(value, fields, "$")
    constants = (item["schema"] == RESULT_SCHEMA and item["contract_id"] == ISOLATED_WORKER_CONTRACT_ID and item["contract_sha256"] == ISOLATED_WORKER_CONTRACT_SHA256 and item["resource_budget_contract_sha256"] == RESOURCE_BUDGET_CONTRACT_SHA256 and item["deterministic_planner_contract_sha256"] == DETERMINISTIC_PLANNER_CONTRACT_SHA256 and item["mathematical_authority"] is False)
    if not constants:
        _fail("contract", "$", "result contract constants differ")
    status_value = _text(item["status"], "$.status", maximum=16)
    reason = _text(item["reason_code"], "$.reason_code", maximum=32)
    if status_value not in _STATUSES or reason not in _REASONS or reason not in _STATUS_REASONS[status_value] or type(item["tree_terminated"]) is not bool or type(item["lease_reconciled"]) is not bool:
        _fail("result", "$", "result status fields differ")
    def optional_digest(name: str) -> str | None:
        raw = item[name]
        return None if raw is None else _digest(raw, f"$.{name}")
    capability = None if item["capability"] is None else _capability_from_mapping(item["capability"], "$.capability")
    usage = None if item["usage"] is None else _usage_from_mapping(item["usage"], "$.usage")
    artifact_values = item["artifacts"]
    if type(artifact_values) is not list or len(artifact_values) > 2 or type(artifact_payloads) is not tuple:
        _fail("artifact", "$.artifacts", "artifact inventory is invalid")
    if artifact_values and len(artifact_payloads) != len(artifact_values):
        _fail("artifact", "$.artifacts", "exact retained artifact bytes are required")
    artifacts = tuple(_artifact_from_mapping(raw, artifact_payloads[index], f"$.artifacts[{index}]") for index, raw in enumerate(artifact_values))
    if tuple(artifact.role for artifact in artifacts) not in {(), ("stdout",), ("stdout", "stderr")}:
        _fail("artifact", "$.artifacts", "artifact roles or order differ")
    diagnostics_value = item["diagnostics"]
    if type(diagnostics_value) is not list or len(diagnostics_value) > MAX_DIAGNOSTICS:
        _fail("result", "$.diagnostics", "diagnostic inventory is invalid")
    diagnostics = tuple(_diagnostic_from_mapping(raw, f"$.diagnostics[{index}]") for index, raw in enumerate(diagnostics_value))
    if status_value == "completed" and diagnostics or status_value != "completed" and (len(diagnostics) != 1 or diagnostics[0].code != reason):
        _fail("result", "$.diagnostics", "diagnostic inventory does not bind terminal reason")
    child_sha = optional_digest("child_budget_sha256")
    parent_sha = optional_digest("parent_budget_sha256")
    if (child_budget is None) != (child_sha is None) or (parent_budget is None) != (parent_sha is None):
        _fail("accounting", "$", "budget bytes and identities disagree")
    if child_budget is not None and (type(child_budget) is not bytes or _sha(child_budget) != child_sha):
        _fail("accounting", "$.child_budget_sha256", "child budget bytes differ")
    if parent_budget is not None and (type(parent_budget) is not bytes or _sha(parent_budget) != parent_sha):
        _fail("accounting", "$.parent_budget_sha256", "parent budget bytes differ")
    if child_budget is not None and parent_budget is not None:
        _validate_result_budgets(child_budget, parent_budget, usage, status_value)
    result = _make(
        IsolatedWorkerResult, schema=RESULT_SCHEMA, contract_id=ISOLATED_WORKER_CONTRACT_ID,
        contract_sha256=ISOLATED_WORKER_CONTRACT_SHA256,
        resource_budget_contract_sha256=RESOURCE_BUDGET_CONTRACT_SHA256,
        deterministic_planner_contract_sha256=DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        status=status_value, reason_code=reason, request_sha256=optional_digest("request_sha256"),
        planning_result_sha256=optional_digest("planning_result_sha256"), strategy_sha256=optional_digest("strategy_sha256"),
        capability=capability, usage=usage, artifacts=artifacts, diagnostics=diagnostics,
        child_budget_sha256=child_sha, parent_budget_sha256=parent_sha,
        tree_terminated=item["tree_terminated"], lease_reconciled=item["lease_reconciled"],
        semantic_sha256=optional_digest("semantic_sha256"), result_sha256=optional_digest("result_sha256"),
        mathematical_authority=False, _child_budget=child_budget, _parent_budget=parent_budget,
    )
    mapping = _result_mapping(result)
    bound_fields = (result.request_sha256, result.planning_result_sha256, result.strategy_sha256)
    if any(field is None for field in bound_fields) != all(field is None for field in bound_fields):
        _fail("identity", "$", "request, plan, and strategy identities must be jointly present")
    if result.result_sha256 is None:
        if result.semantic_sha256 is not None or result.request_sha256 is not None or result.status != "invalid":
            _fail("identity", "$", "only unbound invalid results may omit identities")
    else:
        if result.semantic_sha256 != _sha(_canonical(_semantic_preimage(mapping))):
            _fail("identity", "$.semantic_sha256", "semantic identity mismatch")
        if result.result_sha256 != _self_hash(mapping, "result_sha256"):
            _fail("identity", "$.result_sha256", "result identity mismatch")
    if result.status == "completed":
        if result.reason_code != "COMPLETED" or result.usage is None or not result.usage.usage_complete or result.usage.exit_code != 0 or result.usage.termination_signal is not None or not result.tree_terminated or not result.lease_reconciled or not result.artifacts or result.artifacts[0].role != "stdout" or any(artifact.omitted_bytes for artifact in result.artifacts):
            _fail("result", "$", "completed result invariants differ")
    elif result.status in {"exhausted", "cancelled"}:
        if result.usage is None or result.capability is None or not result.capability.supported or not result.artifacts or not result.tree_terminated or not result.lease_reconciled:
            _fail("result", "$", "launched terminal result inventory differs")
    elif result.status in {"invalid", "refused", "unsupported"}:
        if result.usage is not None or result.artifacts or result.tree_terminated or result.lease_reconciled:
            _fail("result", "$", "non-launched result contains execution state")
        if result.status == "unsupported" and (result.capability is None or result.capability.supported):
            _fail("result", "$", "unsupported result lacks an unsupported capability")
        if result.status != "unsupported" and result.capability is not None:
            _fail("result", "$", "pre-launch result unexpectedly contains capability state")
    elif result.status == "failed":
        launched = result.usage is not None or bool(result.artifacts) or result.lease_reconciled or result.tree_terminated
        if launched and (result.usage is None or result.capability is None or not result.capability.supported or not result.artifacts or not result.lease_reconciled):
            _fail("result", "$", "launched failure inventory differs")
        if not launched and (result.capability is not None or result.usage is not None or result.artifacts or result.lease_reconciled or result.tree_terminated):
            _fail("result", "$", "pre-launch failure contains execution state")
    if result.lease_reconciled != (child_sha is not None and parent_sha is not None):
        _fail("accounting", "$", "lease state and budget inventory disagree")
    return result


def _make_result(*, status: str, reason: str, request: IsolatedWorkerRequest | None = None, capability: IsolationCapability | None = None, usage: WorkerResourceUsage | None = None, artifacts: tuple[WorkerArtifact, ...] = (), diagnostics: tuple[WorkerDiagnostic, ...] = (), child_budget: bytes | None = None, parent_budget: bytes | None = None, tree_terminated: bool = False, lease_reconciled: bool = False) -> IsolatedWorkerResult:
    bound = request is not None
    mapping: dict[str, object] = {
        "schema": RESULT_SCHEMA, "contract_id": ISOLATED_WORKER_CONTRACT_ID,
        "contract_sha256": ISOLATED_WORKER_CONTRACT_SHA256,
        "resource_budget_contract_sha256": RESOURCE_BUDGET_CONTRACT_SHA256,
        "deterministic_planner_contract_sha256": DETERMINISTIC_PLANNER_CONTRACT_SHA256,
        "status": status, "reason_code": reason,
        "request_sha256": request.request_sha256 if bound else None,
        "planning_result_sha256": request.planning_result_sha256 if bound else None,
        "strategy_sha256": request.strategy_sha256 if bound else None,
        "capability": None if capability is None else _capability_mapping(capability),
        "usage": None if usage is None else _usage_mapping(usage),
        "artifacts": [_artifact_mapping(item) for item in artifacts],
        "diagnostics": [_diagnostic_mapping(item) for item in diagnostics],
        "child_budget_sha256": None if child_budget is None else _sha(child_budget),
        "parent_budget_sha256": None if parent_budget is None else _sha(parent_budget),
        "tree_terminated": tree_terminated, "lease_reconciled": lease_reconciled,
        "semantic_sha256": None, "result_sha256": None, "mathematical_authority": False,
    }
    if bound:
        mapping["semantic_sha256"] = _sha(_canonical(_semantic_preimage(mapping)))
        mapping["result_sha256"] = _self_hash(mapping, "result_sha256")
    payloads = tuple(worker_artifact_bytes(item) for item in artifacts)
    return _result_from_mapping(mapping, artifact_payloads=payloads, child_budget=child_budget, parent_budget=parent_budget)


def isolated_worker_result_bytes(value: IsolatedWorkerResult) -> bytes:
    if type(value) is not IsolatedWorkerResult:
        _fail("type", "$", "expected exact IsolatedWorkerResult")
    validate_isolated_worker_result(value)
    return _canonical(_result_mapping(value))


def parse_isolated_worker_result(data: bytes, artifact_payloads: tuple[bytes, ...] = (), child_budget: bytes | None = None, parent_budget: bytes | None = None) -> IsolatedWorkerResult:
    return _result_from_mapping(_parse(data, "$"), artifact_payloads=artifact_payloads, child_budget=child_budget, parent_budget=parent_budget)


def validate_isolated_worker_result(value: IsolatedWorkerResult) -> None:
    if type(value) is not IsolatedWorkerResult:
        _fail("type", "$", "expected exact IsolatedWorkerResult")
    rebuilt = _result_from_mapping(_result_mapping(value), artifact_payloads=tuple(worker_artifact_bytes(item) for item in value.artifacts), child_budget=value._child_budget, parent_budget=value._parent_budget)
    if rebuilt != value:
        _fail("result", "$", "in-memory result differs from strict reconstruction")


def isolated_worker_budget_bytes(value: IsolatedWorkerResult, kind: str) -> bytes:
    if type(value) is not IsolatedWorkerResult or kind not in {"child", "parent"}:
        _fail("type", "$", "expected exact result and child or parent selector")
    data = value._child_budget if kind == "child" else value._parent_budget
    if data is None:
        _fail("accounting", "$", "result has no reconciled budget bytes")
    return data


def _match_strategy(plan: PlanningResult, request: IsolatedWorkerRequest) -> PlanningStrategy:
    if plan.status != "planned":
        raise _OrdinaryFailure("invalid", "PLAN_INVALID", "planning result is not the exact planned subject")
    matches = [strategy for strategy in plan.strategies if strategy.strategy_sha256 == request.strategy_sha256]
    if len(matches) != 1:
        raise _OrdinaryFailure("invalid", "STRATEGY_MISMATCH", "selected strategy is absent or ambiguous")
    strategy = matches[0]
    if strategy.descriptor_sha256 != request.descriptor_sha256 or _vector_mapping(request.resource_limits) != {name: getattr(strategy.resource_request.requested, name) for name in RESOURCE_DIMENSIONS}:
        raise _OrdinaryFailure("invalid", "STRATEGY_MISMATCH", "descriptor or resource request differs from the plan")
    return strategy


def supervise_worker(request: bytes, planning_result: bytes, parent_budget: bytes, artifacts: tuple[bytes, ...], executable_path: str, workspace_root: str, cancel_event: Event | None = None) -> IsolatedWorkerResult:
    """Execute one exact planned producer under one isolated child budget."""
    request_value: IsolatedWorkerRequest | None = None
    reserved = False
    state: _BudgetState | None = None
    try:
        if type(artifacts) is not tuple or any(type(item) is not bytes for item in artifacts) or (cancel_event is not None and type(cancel_event) is not Event):
            raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "boundary values must have exact immutable types")
        request_value = parse_isolated_worker_request(request)
        if _sha(planning_result) != request_value.planning_result_sha256 or _sha(parent_budget) != request_value.parent_budget_sha256:
            raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "bound input byte identity differs")
        if len(artifacts) != len(request_value.artifact_bindings):
            raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "artifact inventory length differs")
        for binding, payload in zip(request_value.artifact_bindings, artifacts):
            if len(payload) != binding.bytes or _sha(payload) != binding.sha256:
                raise _OrdinaryFailure("invalid", "REQUEST_INVALID", "artifact bytes differ from their binding")
        try:
            plan = parse_planning_result(planning_result)
        except DeterministicPlannerValidationError as exc:
            raise _OrdinaryFailure("invalid", "PLAN_INVALID", "planning result is invalid") from exc
        strategy = _match_strategy(plan, request_value)
        del strategy
        state = _parse_parent_budget(parent_budget)
        capability = isolation_capability()
        if not capability.supported:
            return _make_result(status="unsupported", reason="ISOLATION_UNSUPPORTED", request=request_value, capability=capability, diagnostics=(_make_diagnostic("ISOLATION_UNSUPPORTED", "contracted process containment is unavailable"),))
        executable = _validated_executable(executable_path, request_value.executable_sha256)
        root = _validated_root(workspace_root)
        _reserve_budget(state, request_value)
        reserved = True
        private = Path(tempfile.mkdtemp(prefix="mathhead-worker-", dir=root))
        cleanup_ok = True
        try:
            command = [str(executable), *request_value.arguments]
            environment = _environment(private)
            if capability.platform in {"linux", "darwin"}:
                observation = _run_posix(command, private, environment, request_value.resource_limits, cancel_event)
            elif capability.platform == "windows":
                observation = _run_windows(command, private, environment, request_value.resource_limits, cancel_event)
            else:
                raise _OrdinaryFailure("unsupported", "ISOLATION_UNSUPPORTED", "no platform adapter exists")
        finally:
            try:
                shutil.rmtree(private)
            except OSError:
                cleanup_ok = False
        if not cleanup_ok:
            observation.reason = "SUPERVISOR_FAILED"
            observation.tree_terminated = False
        if observation.reason == "COMPLETED":
            if observation.stdout_size > request_value.resource_limits.output_bytes:
                observation.reason = "OUTPUT_EXHAUSTED"
            elif observation.stderr_size > request_value.resource_limits.diagnostic_bytes:
                observation.reason = "DIAGNOSTIC_EXHAUSTED"
            elif observation.wall_time_us > request_value.resource_limits.wall_time_us:
                observation.reason = "WALL_TIME_EXHAUSTED"
            elif observation.cpu_time_us > request_value.resource_limits.cpu_time_us:
                observation.reason = "CPU_TIME_EXHAUSTED"
            elif observation.memory_peak_bytes > request_value.resource_limits.memory_bytes:
                observation.reason = "MEMORY_EXHAUSTED"
        resource_reasons = {"WALL_TIME_EXHAUSTED", "CPU_TIME_EXHAUSTED", "MEMORY_EXHAUSTED", "OUTPUT_EXHAUSTED", "DIAGNOSTIC_EXHAUSTED"}
        if observation.reason == "COMPLETED":
            status_value = "completed"
        elif observation.reason == "CANCELLED":
            status_value = "cancelled"
        elif observation.reason in resource_reasons:
            status_value = "exhausted"
        else:
            status_value = "failed"
        # The accepted plan, not the caller-selected family label, owns the
        # solver-call allocation.  This prevents relabelling a solver process
        # as enumeration to evade accounting.
        solver_calls = 1 if request_value.resource_limits.solver_calls else 0
        usage = _make_usage(
            wall=observation.wall_time_us, cpu=observation.cpu_time_us,
            memory=observation.memory_peak_bytes, solver_calls=solver_calls,
            output=observation.stdout_size, diagnostic=observation.stderr_size,
            exit_code=observation.exit_code, termination_signal=observation.termination_signal,
            complete=observation.usage_complete and observation.tree_terminated,
        )
        output = _make_artifact("stdout", observation.stdout, observation.stdout_size)
        produced: tuple[WorkerArtifact, ...] = (output,)
        if observation.stderr_size:
            produced = (*produced, _make_artifact("stderr", observation.stderr, observation.stderr_size))
        child, child_outcome = _child_budget(request_value, usage, observation.reason if observation.reason in resource_reasons else None, cancelled=observation.reason == "CANCELLED")
        assert state is not None
        child_raw = _reconcile_budget(state, request_value, child, child_outcome, usage)
        parent_raw = _canonical(state.value)
        _parse_parent_budget(parent_raw)
        reserved = False
        diagnostic_values: tuple[WorkerDiagnostic, ...] = () if status_value == "completed" else (_make_diagnostic(observation.reason, "isolated worker did not produce a bounded completed result"),)
        return _make_result(status=status_value, reason=observation.reason, request=request_value, capability=capability, usage=usage, artifacts=produced, diagnostics=diagnostic_values, child_budget=child_raw, parent_budget=parent_raw, tree_terminated=observation.tree_terminated, lease_reconciled=True)
    except _OrdinaryFailure as exc:
        return _make_result(status=exc.status, reason=exc.reason, request=request_value, diagnostics=(_make_diagnostic(exc.reason, str(exc)),))
    except IsolatedWorkerValidationError:
        return _make_result(status="invalid", reason="REQUEST_INVALID", request=request_value, diagnostics=(_make_diagnostic("REQUEST_INVALID", "isolated worker input validation failed"),))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, UnicodeError, json.JSONDecodeError, KeyError, AttributeError) as exc:
        return _make_result(status="failed" if request_value is not None else "invalid", reason="SUPERVISOR_FAILED" if request_value is not None else "REQUEST_INVALID", request=request_value, diagnostics=(_make_diagnostic("SUPERVISOR_FAILED" if request_value is not None else "REQUEST_INVALID", f"isolated worker boundary failed: {type(exc).__name__}"),))
    finally:
        if reserved and state is not None and request_value is not None:
            state.active.pop(request_value.lease_id, None)


__all__ = [
    "ISOLATED_WORKER_CONTRACT_ID", "ISOLATED_WORKER_CONTRACT_SHA256", "SCHEMA_SHA256S",
    "WorkerResourceVector", "WorkerArtifactBinding", "IsolatedWorkerRequest",
    "IsolationCapability", "WorkerResourceUsage", "WorkerArtifact", "WorkerDiagnostic",
    "IsolatedWorkerResult", "IsolatedWorkerValidationError", "make_isolated_worker_request",
    "parse_isolated_worker_request", "isolation_capability", "worker_artifact_bytes",
    "isolated_worker_result_bytes", "parse_isolated_worker_result",
    "validate_isolated_worker_result", "isolated_worker_budget_bytes", "supervise_worker",
]
