"""Content-addressed, dependency-minimal provenance bundle replay.

The manifest and all constituent objects are untrusted bytes.  This module
validates their complete identity graph and then invokes an allowlisted kernel
checker from exact inputs.  Stored verdicts never attest themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, NoReturn
import unicodedata

from mathhead.kernel.checkers import (
    KERNEL_CHECKER_CONTRACT_ID,
    KERNEL_CHECKER_CONTRACT_SHA256,
    KERNEL_CHECKER_ID,
    check_proof_term,
    checker_result_to_bytes,
)
from mathhead.kernel.proof_terms import (
    PROOF_TERM_CONTRACT_ID,
    PROOF_TERM_CONTRACT_SHA256,
    ProofTermValidationError,
    parse_proof_term,
)
from mathhead.kernel.sat import (
    SAT_REPLAY_CHECKER_ID,
    SAT_REPLAY_CONTRACT_ID,
    SAT_REPLAY_CONTRACT_SHA256,
    check_sat_certificate,
    sat_replay_result_to_bytes,
)


PROVENANCE_REPLAY_CONTRACT_ID = "MH-C-PROVENANCE-REPLAY-001"
PROVENANCE_REPLAY_CONTRACT_SHA256 = (
    "31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67"
)
PROVENANCE_MANIFEST_SCHEMA = "mathhead.provenance-manifest.v1"
PROVENANCE_REPLAY_RESULT_SCHEMA = "mathhead.provenance-replay-result.v1"

MAX_MANIFEST_BYTES = 4_194_304
MAX_OBJECT_BYTES = 67_108_864
MAX_AGGREGATE_OBJECT_BYTES = 536_870_912
MAX_OBJECTS = 13
MAX_JSON_NESTING = 64
MAX_JSON_NODES = 4_000_000
MAX_STRING_CODEPOINTS = 1_048_576
MAX_DEPENDENCY_EDGES = 169
MAX_RESULT_BYTES = 65_536

_HEX = frozenset("0123456789abcdef")
_COMMON_ROLES = frozenset(
    {
        "certificate",
        "checker_configuration",
        "checker_contract",
        "checker_implementation",
        "checker_result",
        "engine_result",
        "evidence",
        "problem_ir",
        "resource_budget",
        "theory_context",
        "theory_plugin",
    }
)
_PROOF_ROLES = _COMMON_ROLES | {"proof_term"}
_SAT_ROLES = _COMMON_ROLES | {"cnf", "sat_certificate"}

_FOUNDATION = {
    "certificate": (
        "application/json",
        "mathhead.certificate.v1",
        "MH-C-CERTIFICATE-001",
        "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
    ),
    "engine_result": (
        "application/json",
        "mathhead.engine-result.v1",
        "MH-C-ENGINE-RESULT-001",
        "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
    ),
    "evidence": (
        "application/json",
        "mathhead.evidence.v1",
        "MH-C-EVIDENCE-001",
        "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
    ),
    "problem_ir": (
        "application/json",
        "mathhead.problem-ir.v1",
        "MH-C-PROBLEM-IR-002",
        "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
    ),
    "resource_budget": (
        "application/json",
        "mathhead.resource-budget.v1",
        "MH-C-RESOURCE-BUDGET-001",
        "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
    ),
    "theory_context": (
        "application/json",
        "mathhead.theory-context.v1",
        "MH-C-THEORY-CONTEXT-001",
        "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
    ),
    "theory_plugin": (
        "application/json",
        "mathhead.theory-plugin.v1",
        "MH-C-THEORY-PLUGIN-001",
        "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
    ),
}

_CHECKERS = {
    KERNEL_CHECKER_ID: {
        "contract_id": KERNEL_CHECKER_CONTRACT_ID,
        "contract_sha256": KERNEL_CHECKER_CONTRACT_SHA256,
        "implementation_sha256": (
            "ea553033f81e670bbb5fb3b7826a912c2aa47980ada86e18287508698dff73b4"
        ),
        "result_schema": "mathhead.kernel-checker-result.v2",
        "roles": _PROOF_ROLES,
    },
    SAT_REPLAY_CHECKER_ID: {
        "contract_id": SAT_REPLAY_CONTRACT_ID,
        "contract_sha256": SAT_REPLAY_CONTRACT_SHA256,
        "implementation_sha256": (
            "1c53dc24f8dd36bca730b5c2ceaa50627dfe5ef889ebabc958ff9ed31b331f39"
        ),
        "result_schema": "mathhead.sat-replay-result.v1",
        "roles": _SAT_ROLES,
    },
}


class ProvenanceReplayValidationError(ValueError):
    """A classified failure at an explicitly requested result boundary."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _ReplayValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("provenance replay values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("provenance replay values cannot be pickled")

    def __copy__(self) -> _ReplayValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _ReplayValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class ProvenanceReplayResult(_ReplayValue):
    verdict: str
    reason_code: str
    diagnostic: str
    authority: str
    exact: bool
    bundle_complete: bool
    manifest_sha256: str | None
    bundle_sha256: str | None
    object_count: int
    total_object_bytes: int
    checker_id: str | None
    checker_contract_id: str | None
    checker_contract_sha256: str | None
    checker_verdict: str | None
    checker_authority: str | None
    replayed_result_sha256: str | None
    manifest: bytes | None
    objects: tuple[bytes, ...] | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("provenance results are created only by replay")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ProvenanceReplayResult is final")


class _DuplicateKey(ValueError):
    pass


class _Invalid(ValueError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        self.reason_code = reason_code
        self.diagnostic = diagnostic
        super().__init__(diagnostic)


class _Exhausted(ValueError):
    pass


def _fail(kind: str, detail: str) -> NoReturn:
    raise ProvenanceReplayValidationError(kind, detail)


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    raise ValueError(f"non-integer JSON number is forbidden: {value[:32]}")


def _canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        _fail("canonical", f"canonical JSON encoding failed: {type(exc).__name__}")
    return (text + "\n").encode("ascii")


def _walk_json(root: object) -> None:
    stack: list[tuple[object, int]] = [(root, 1)]
    nodes = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise _Exhausted("JSON node budget exceeded")
        if depth > MAX_JSON_NESTING:
            raise _Exhausted("JSON nesting budget exceeded")
        if isinstance(value, str):
            if len(value) > MAX_STRING_CODEPOINTS:
                raise _Exhausted("JSON string budget exceeded")
            if "\x00" in value or unicodedata.normalize("NFC", value) != value:
                raise _Invalid("JSON_INVALID", "JSON strings must be NFC without NUL")
        elif type(value) is dict:
            for key, item in value.items():
                if type(key) is not str:
                    raise _Invalid("JSON_INVALID", "JSON object keys must be strings")
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
        elif type(value) is list:
            for item in value:
                stack.append((item, depth + 1))
        elif value is not None and type(value) not in {bool, int}:
            raise _Invalid("JSON_INVALID", "JSON values must not contain floats")


def _parse_canonical_json(data: bytes, label: str) -> dict[str, Any]:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise _Invalid("ENCODING_INVALID", f"{label} has invalid UTF-8 at byte {exc.start}")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except (_DuplicateKey, ValueError, json.JSONDecodeError, RecursionError) as exc:
        raise _Invalid("JSON_INVALID", f"{label} JSON is invalid: {type(exc).__name__}")
    if type(value) is not dict:
        raise _Invalid("SCHEMA_INVALID", f"{label} must be a JSON object")
    _walk_json(value)
    if data != _canonical_json_bytes(value):
        raise _Invalid("NONCANONICAL", f"{label} bytes are not canonical JSON")
    return value


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _lower_digest(value: object, label: str) -> str:
    if type(value) is not str or len(value) != 64 or any(ch not in _HEX for ch in value):
        raise _Invalid("SCHEMA_INVALID", f"{label} must be a lowercase SHA-256")
    return value


def checker_configuration_bytes(checker_id: str) -> bytes:
    """Return the canonical, non-authoritative configuration identity object."""
    if type(checker_id) is not str or checker_id not in _CHECKERS:
        _fail("identity", "checker_id is not allowlisted")
    checker = _CHECKERS[checker_id]
    return _canonical_json_bytes(
        {
            "checker_contract_id": checker["contract_id"],
            "checker_contract_sha256": checker["contract_sha256"],
            "checker_id": checker_id,
            "implementation_sha256": checker["implementation_sha256"],
            "schema": "mathhead.checker-configuration.v1",
        }
    )


def canonical_provenance_manifest_bytes(value: object) -> bytes:
    """Encode a prospective manifest canonically without granting authority."""
    encoded = _canonical_json_bytes(value)
    if len(encoded) > MAX_MANIFEST_BYTES:
        _fail("budget", "manifest exceeds its byte budget")
    return encoded


def _new_result(
    verdict: str,
    reason_code: str,
    diagnostic: str,
    *,
    complete: bool,
    manifest_digest: str | None,
    object_count: int,
    total_bytes: int,
    checker_id: str | None,
    checker_contract_id: str | None,
    checker_contract_sha256: str | None,
    checker_verdict: str | None,
    checker_authority: str | None,
    replayed_result_sha256: str | None,
    manifest: bytes | None,
    objects: tuple[bytes, ...] | None,
) -> ProvenanceReplayResult:
    result = object.__new__(ProvenanceReplayResult)
    fields: dict[str, object] = {
        "authority": "checker_attestation" if verdict == "verified" else "none",
        "bundle_complete": complete,
        "bundle_sha256": manifest_digest if complete else None,
        "checker_authority": checker_authority,
        "checker_contract_id": checker_contract_id,
        "checker_contract_sha256": checker_contract_sha256,
        "checker_id": checker_id,
        "checker_verdict": checker_verdict,
        "diagnostic": diagnostic[:512],
        "exact": True,
        "manifest": manifest,
        "manifest_sha256": manifest_digest,
        "object_count": object_count,
        "objects": objects,
        "reason_code": reason_code,
        "replayed_result_sha256": replayed_result_sha256,
        "total_object_bytes": total_bytes,
        "verdict": verdict,
    }
    for name, value in fields.items():
        object.__setattr__(result, name, value)
    return result


def _invalid_result(
    reason: str,
    diagnostic: str,
    *,
    manifest: bytes | None,
    objects: tuple[bytes, ...] | None,
    manifest_digest: str | None,
    object_count: int,
    total_bytes: int,
    checker_id: str | None = None,
    checker_contract_id: str | None = None,
    checker_contract_sha256: str | None = None,
    exhausted: bool = False,
) -> ProvenanceReplayResult:
    return _new_result(
        "exhausted" if exhausted else "invalid",
        reason,
        diagnostic,
        complete=False,
        manifest_digest=manifest_digest,
        object_count=object_count,
        total_bytes=total_bytes,
        checker_id=checker_id,
        checker_contract_id=checker_contract_id,
        checker_contract_sha256=checker_contract_sha256,
        checker_verdict=None,
        checker_authority=None,
        replayed_result_sha256=None,
        manifest=manifest,
        objects=objects,
    )


def _record_spec(role: str, checker_id: str) -> tuple[str, str | None, str, str]:
    if role in _FOUNDATION:
        return _FOUNDATION[role]
    checker = _CHECKERS[checker_id]
    contract_id = str(checker["contract_id"])
    contract_sha = str(checker["contract_sha256"])
    if role == "checker_contract":
        return "application/json", "mathhead.function-contract.v1", contract_id, contract_sha
    if role == "checker_implementation":
        return "text/x-python", None, contract_id, contract_sha
    if role == "checker_configuration":
        return "application/json", "mathhead.checker-configuration.v1", contract_id, contract_sha
    if role == "checker_result":
        return "application/json", str(checker["result_schema"]), contract_id, contract_sha
    if role == "proof_term":
        return (
            "application/json",
            "mathhead.proof-term.v1",
            PROOF_TERM_CONTRACT_ID,
            PROOF_TERM_CONTRACT_SHA256,
        )
    if role == "cnf":
        return "application/octet-stream", "mathhead.cnf.v1", contract_id, contract_sha
    if role == "sat_certificate":
        return "application/octet-stream", "mathhead.sat-certificate.v1", contract_id, contract_sha
    raise _Invalid("ROLE_INVALID", f"unknown object role: {role}")


def _expected_dependencies(role: str, by_role: dict[str, dict[str, Any]]) -> list[str]:
    def digest(name: str) -> str:
        return by_role[name]["sha256"]

    foundation = ["problem_ir", "resource_budget", "theory_context", "theory_plugin"]
    inputs = [name for name in ("proof_term", "cnf", "sat_certificate") if name in by_role]
    if role in {"problem_ir", "resource_budget", "theory_plugin", "checker_contract"}:
        names: list[str] = []
    elif role == "theory_context":
        names = ["problem_ir"]
    elif role in {"proof_term", "cnf"}:
        names = ["problem_ir", "theory_context"]
    elif role == "sat_certificate":
        names = ["cnf"]
    elif role == "evidence":
        names = foundation
    elif role == "certificate":
        names = [*foundation, "evidence", *inputs]
    elif role == "engine_result":
        names = [*foundation, "evidence", "certificate"]
    elif role == "checker_implementation":
        names = ["checker_contract"]
    elif role == "checker_configuration":
        names = ["checker_contract", "checker_implementation"]
    elif role == "checker_result":
        names = [name for name in by_role if name != "checker_result"]
    else:
        raise _Invalid("ROLE_INVALID", f"unknown dependency role: {role}")
    return sorted(digest(name) for name in names)


def _validate_manifest_shape(value: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    if set(value) != {"objects", "plugin", "replay", "schema"}:
        raise _Invalid("SCHEMA_INVALID", "manifest fields differ")
    if value["schema"] != PROVENANCE_MANIFEST_SCHEMA:
        raise _Invalid("SCHEMA_INVALID", "manifest schema differs")
    plugin = value["plugin"]
    if type(plugin) is not dict or set(plugin) != {"plugin_id", "plugin_version"}:
        raise _Invalid("SCHEMA_INVALID", "plugin identity fields differ")
    if not all(type(plugin[name]) is str and plugin[name] for name in plugin):
        raise _Invalid("SCHEMA_INVALID", "plugin identity must contain exact strings")
    replay = value["replay"]
    replay_fields = {
        "checker_configuration_sha256",
        "checker_contract_id",
        "checker_contract_sha256",
        "checker_id",
        "checker_implementation_sha256",
        "recorded_result_sha256",
    }
    if type(replay) is not dict or set(replay) != replay_fields:
        raise _Invalid("SCHEMA_INVALID", "replay fields differ")
    checker_id = replay["checker_id"]
    if type(checker_id) is not str or checker_id not in _CHECKERS:
        raise _Invalid("DISPATCH_UNSUPPORTED", "checker dispatch is not allowlisted")
    checker = _CHECKERS[checker_id]
    expected_replay = {
        "checker_contract_id": checker["contract_id"],
        "checker_contract_sha256": checker["contract_sha256"],
        "checker_id": checker_id,
        "checker_implementation_sha256": checker["implementation_sha256"],
    }
    for name, expected in expected_replay.items():
        if replay[name] != expected:
            raise _Invalid("CHECKER_IDENTITY_MISMATCH", f"replay.{name} differs")
    for name in (
        "checker_configuration_sha256",
        "checker_contract_sha256",
        "checker_implementation_sha256",
        "recorded_result_sha256",
    ):
        _lower_digest(replay[name], f"replay.{name}")
    records = value["objects"]
    if type(records) is not list:
        raise _Invalid("SCHEMA_INVALID", "objects must be an array")
    roles = checker["roles"]
    if len(records) != len(roles):
        raise _Invalid("INVENTORY_MISMATCH", "object count differs from dispatch")
    by_role: dict[str, dict[str, Any]] = {}
    prior = ""
    digests: set[str] = set()
    edges = 0
    fields = {
        "byte_count",
        "contract_id",
        "contract_sha256",
        "depends_on_sha256",
        "media_type",
        "role",
        "schema",
        "sha256",
    }
    for number, record in enumerate(records):
        if type(record) is not dict or set(record) != fields:
            raise _Invalid("SCHEMA_INVALID", f"object record {number} fields differ")
        role = record["role"]
        if type(role) is not str or role not in roles or role <= prior or role in by_role:
            raise _Invalid("ROLE_INVALID", "object roles must be unique and sorted")
        prior = role
        digest = _lower_digest(record["sha256"], f"objects[{number}].sha256")
        if digest in digests:
            raise _Invalid("DUPLICATE_OBJECT", "one digest cannot fill multiple roles")
        digests.add(digest)
        if type(record["byte_count"]) is not int or type(record["byte_count"]) is bool:
            raise _Invalid("SCHEMA_INVALID", f"{role} byte_count is not an integer")
        if not 1 <= record["byte_count"] <= MAX_OBJECT_BYTES:
            raise _Invalid("SCHEMA_INVALID", f"{role} byte_count is outside bounds")
        dependencies = record["depends_on_sha256"]
        if (
            type(dependencies) is not list
            or dependencies != sorted(set(dependencies))
            or not all(type(item) is str for item in dependencies)
        ):
            raise _Invalid("DEPENDENCY_INVALID", f"{role} dependencies are not sorted unique")
        for dependency in dependencies:
            _lower_digest(dependency, f"{role} dependency")
        edges += len(dependencies)
        if edges > MAX_DEPENDENCY_EDGES:
            raise _Exhausted("dependency edge budget exceeded")
        media, schema, contract_id, contract_sha = _record_spec(role, checker_id)
        expected = (media, schema, contract_id, contract_sha)
        actual = (
            record["media_type"],
            record["schema"],
            record["contract_id"],
            record["contract_sha256"],
        )
        if actual != expected:
            raise _Invalid("ROLE_BINDING_MISMATCH", f"{role} contract or format differs")
        by_role[role] = record
    if frozenset(by_role) != roles:
        raise _Invalid("INVENTORY_MISMATCH", "required role set differs")
    for role, record in by_role.items():
        expected = _expected_dependencies(role, by_role)
        if record["depends_on_sha256"] != expected:
            raise _Invalid("DEPENDENCY_MISMATCH", f"{role} dependency graph differs")
    return checker_id, by_role


def _validate_object_bytes(
    manifest_value: dict[str, Any],
    checker_id: str,
    by_role: dict[str, dict[str, Any]],
    objects: tuple[bytes, ...],
) -> dict[str, bytes]:
    records = manifest_value["objects"]
    if len(objects) != len(records):
        raise _Invalid("INVENTORY_MISMATCH", "supplied object count differs")
    values: dict[str, bytes] = {}
    supplied_digests: set[str] = set()
    for number, (record, data) in enumerate(zip(records, objects)):
        if type(data) is not bytes:
            raise _Invalid("TYPE_INVALID", f"object {number} must be exact bytes")
        digest = _digest(data)
        if digest in supplied_digests:
            raise _Invalid("DUPLICATE_OBJECT", "supplied object identity is duplicated")
        supplied_digests.add(digest)
        role = record["role"]
        if len(data) != record["byte_count"] or digest != record["sha256"]:
            raise _Invalid("OBJECT_MISMATCH", f"{role} size or SHA-256 differs")
        values[role] = data
        if record["media_type"] == "application/json":
            parsed = _parse_canonical_json(data, role)
            if parsed.get("schema") != record["schema"]:
                raise _Invalid("SCHEMA_INVALID", f"{role} root schema differs")
    plugin = _parse_canonical_json(values["theory_plugin"], "theory_plugin")
    if (
        plugin.get("plugin_id") != manifest_value["plugin"]["plugin_id"]
        or plugin.get("plugin_version") != manifest_value["plugin"]["plugin_version"]
    ):
        raise _Invalid("PLUGIN_MISMATCH", "plugin identifier or version differs")
    checker = _CHECKERS[checker_id]
    contract = _parse_canonical_json(values["checker_contract"], "checker_contract")
    if contract.get("contract_id") != checker["contract_id"]:
        raise _Invalid(
            "CHECKER_IDENTITY_MISMATCH", "checker contract bytes identify another contract"
        )
    if values["checker_configuration"] != checker_configuration_bytes(checker_id):
        raise _Invalid("CHECKER_IDENTITY_MISMATCH", "checker configuration bytes differ")
    replay = manifest_value["replay"]
    role_hashes = {
        "checker_configuration_sha256": "checker_configuration",
        "checker_contract_sha256": "checker_contract",
        "checker_implementation_sha256": "checker_implementation",
        "recorded_result_sha256": "checker_result",
    }
    for field, role in role_hashes.items():
        if replay[field] != by_role[role]["sha256"]:
            raise _Invalid("CHECKER_IDENTITY_MISMATCH", f"replay.{field} object differs")
    return values


def _run_checker(checker_id: str, values: dict[str, bytes]) -> tuple[str, str, bytes]:
    if checker_id == KERNEL_CHECKER_ID:
        try:
            term = parse_proof_term(values["proof_term"])
        except ProofTermValidationError as exc:
            raise _Invalid("CHECKER_INPUT_INVALID", f"proof term is invalid: {exc.kind}")
        result = check_proof_term(term)
        return result.verdict, result.authority, checker_result_to_bytes(result)
    if checker_id == SAT_REPLAY_CHECKER_ID:
        result = check_sat_certificate(values["cnf"], values["sat_certificate"])
        return result.verdict, result.authority, sat_replay_result_to_bytes(result)
    raise _Invalid("DISPATCH_UNSUPPORTED", "checker dispatch is not allowlisted")


def replay_provenance_bundle(manifest: bytes, objects: tuple[bytes, ...]) -> ProvenanceReplayResult:
    """Recompute one complete provenance bundle and preserve only fresh authority."""
    if type(manifest) is not bytes or type(objects) is not tuple:
        return _invalid_result(
            "TYPE_INVALID",
            "manifest must be exact bytes and objects must be an exact tuple of exact bytes",
            manifest=None,
            objects=None,
            manifest_digest=None,
            object_count=0,
            total_bytes=0,
        )
    if any(type(item) is not bytes for item in objects):
        return _invalid_result(
            "TYPE_INVALID",
            "manifest must be exact bytes and objects must be an exact tuple of exact bytes",
            manifest=None,
            objects=None,
            manifest_digest=None,
            object_count=0,
            total_bytes=0,
        )
    manifest_digest = _digest(manifest)
    total_bytes = 0
    try:
        if len(manifest) > MAX_MANIFEST_BYTES:
            raise _Exhausted("manifest byte budget exceeded")
        if len(objects) > MAX_OBJECTS:
            raise _Exhausted("object count budget exceeded")
        for item in objects:
            if len(item) > MAX_OBJECT_BYTES:
                raise _Exhausted("object byte budget exceeded")
            if len(item) > MAX_AGGREGATE_OBJECT_BYTES - total_bytes:
                raise _Exhausted("aggregate object byte budget exceeded")
            total_bytes += len(item)
        manifest_value = _parse_canonical_json(manifest, "manifest")
        checker_id, by_role = _validate_manifest_shape(manifest_value)
        values = _validate_object_bytes(manifest_value, checker_id, by_role, objects)
        checker_verdict, checker_authority, fresh_bytes = _run_checker(checker_id, values)
        fresh_digest = _digest(fresh_bytes)
        if fresh_bytes != values["checker_result"]:
            raise _Invalid("CHECKER_RESULT_MISMATCH", "fresh checker result bytes differ")
        verdict = checker_verdict
        if verdict not in {"verified", "refuted", "invalid", "unsupported", "exhausted"}:
            raise _Invalid("CHECKER_RESULT_INVALID", "checker emitted an unknown verdict")
        if verdict == "verified" and checker_authority != "checker_attestation":
            raise _Invalid("AUTHORITY_MISMATCH", "verified checker result lacks attestation")
        if verdict != "verified" and checker_authority != "none":
            raise _Invalid("AUTHORITY_MISMATCH", "non-verified checker result retains authority")
        reason = {
            "verified": "REPLAY_VERIFIED",
            "refuted": "CHECKER_REFUTED",
            "invalid": "CHECKER_INVALID",
            "unsupported": "CHECKER_UNSUPPORTED",
            "exhausted": "CHECKER_EXHAUSTED",
        }[verdict]
        return _new_result(
            verdict,
            reason,
            "complete bundle and fresh checker result are byte-identical",
            complete=True,
            manifest_digest=manifest_digest,
            object_count=len(objects),
            total_bytes=total_bytes,
            checker_id=checker_id,
            checker_contract_id=str(_CHECKERS[checker_id]["contract_id"]),
            checker_contract_sha256=str(_CHECKERS[checker_id]["contract_sha256"]),
            checker_verdict=checker_verdict,
            checker_authority=checker_authority,
            replayed_result_sha256=fresh_digest,
            manifest=manifest,
            objects=objects,
        )
    except _Exhausted as exc:
        return _invalid_result(
            "BUDGET_EXHAUSTED",
            str(exc),
            manifest=manifest,
            objects=objects,
            manifest_digest=manifest_digest,
            object_count=len(objects),
            total_bytes=total_bytes,
            exhausted=True,
        )
    except _Invalid as exc:
        return _invalid_result(
            exc.reason_code,
            exc.diagnostic,
            manifest=manifest,
            objects=objects,
            manifest_digest=manifest_digest,
            object_count=len(objects),
            total_bytes=total_bytes,
        )


def _result_object(result: ProvenanceReplayResult) -> dict[str, object]:
    return {
        "authority": result.authority,
        "bundle_complete": result.bundle_complete,
        "bundle_sha256": result.bundle_sha256,
        "checker_authority": result.checker_authority,
        "checker_contract_id": result.checker_contract_id,
        "checker_contract_sha256": result.checker_contract_sha256,
        "checker_id": result.checker_id,
        "checker_verdict": result.checker_verdict,
        "diagnostic": result.diagnostic,
        "exact": result.exact,
        "manifest_sha256": result.manifest_sha256,
        "object_count": result.object_count,
        "reason_code": result.reason_code,
        "replayed_result_sha256": result.replayed_result_sha256,
        "schema": PROVENANCE_REPLAY_RESULT_SCHEMA,
        "total_object_bytes": result.total_object_bytes,
        "verdict": result.verdict,
    }


def validate_provenance_replay_result(
    result: ProvenanceReplayResult,
) -> ProvenanceReplayResult:
    """Recompute an in-memory provenance result from its retained exact inputs."""
    if type(result) is not ProvenanceReplayResult:
        _fail("type", "result must be an exact ProvenanceReplayResult")
    expected = replay_provenance_bundle(result.manifest, result.objects)  # type: ignore[arg-type]
    if result != expected:
        _fail("result", "provenance result differs from independent recomputation")
    return result


def provenance_replay_result_to_bytes(result: ProvenanceReplayResult) -> bytes:
    """Serialize one independently recomputed result."""
    validate_provenance_replay_result(result)
    encoded = _canonical_json_bytes(_result_object(result))
    if len(encoded) > MAX_RESULT_BYTES:
        _fail("budget", "provenance result exceeds its byte budget")
    return encoded


def provenance_replay_result_sha256(result: ProvenanceReplayResult) -> str:
    """Return the complete digest of one recomputed canonical result."""
    return _digest(provenance_replay_result_to_bytes(result))


def parse_provenance_replay_result(
    data: bytes, manifest: bytes, objects: tuple[bytes, ...]
) -> ProvenanceReplayResult:
    """Parse result bytes only by comparing them with a fresh full replay."""
    if type(data) is not bytes:
        _fail("type", "result input must be exact bytes")
    if len(data) > MAX_RESULT_BYTES:
        _fail("budget", "result input exceeds its byte budget")
    parsed = _parse_canonical_json(data, "result")
    expected = replay_provenance_bundle(manifest, objects)
    if parsed != _result_object(expected):
        _fail("result", "serialized provenance result differs from fresh replay")
    return expected
