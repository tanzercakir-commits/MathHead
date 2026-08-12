"""Pure, replayable problem-session state transitions.

Session history is untrusted input.  Every event is rebuilt from its embedded
command and exact artifact bytes before the current view is exposed.  The
module records provenance and retained epistemic labels but never grants
mathematical authority.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from typing import Any, Mapping, NoReturn
import unicodedata


PROBLEM_SESSION_CONTRACT_ID = "MH-C-PROBLEM-SESSION-001"
PROBLEM_SESSION_CONTRACT_SHA256 = (
    "822f72c9f41f583e4e0535e83b9dbb10954202acc820192e52eab48a5c2d9c0a"
)
ARTIFACT_LINK_SCHEMA = "mathhead.problem-session-artifact-link.v1"
DEFINITION_SCHEMA = "mathhead.problem-session-definition.v1"
LEMMA_SCHEMA = "mathhead.problem-session-lemma.v1"
ATTEMPT_SCHEMA = "mathhead.problem-session-attempt.v1"
OBLIGATION_SCHEMA = "mathhead.problem-session-obligation-state.v1"
INVALIDATION_SCHEMA = "mathhead.problem-session-invalidation.v1"
COMMAND_SCHEMA = "mathhead.problem-session-command.v1"
EVENT_SCHEMA = "mathhead.problem-session-event.v1"
REVISION_SCHEMA = "mathhead.problem-session-revision.v1"
RESULT_SCHEMA = "mathhead.problem-session-result.v1"

SCHEMA_SHA256S = {
    ARTIFACT_LINK_SCHEMA: "562faa38159bc98c4a1fb37c107afc20b933244b7f1cd3257b63c80f849a4133",
    ATTEMPT_SCHEMA: "e14f6d0a9d1711bca56bfd195430eb081a58a5718c8c987bc7823df5beeeeb4b",
    COMMAND_SCHEMA: "f395dfd35e14d88b5fd8a8b92613b1fcc355f8d72332483425774e2a8feceac1",
    DEFINITION_SCHEMA: "d00d200ce97494b08ed7fc1b6b7d32f805f4a6c8ec4bd20d942fa426d586bb46",
    EVENT_SCHEMA: "983be63a2ee1096b8e9f550f0c3d3a1fe49fdaab64565927b6fd66e4b2247582",
    INVALIDATION_SCHEMA: "fd8dccac3d9437dafdba236d7d40619779661bd32eebbc204da8b08500b6700b",
    LEMMA_SCHEMA: "79a446b77cb45f80eded2af13fda66daccc7445bf817161b2eaa6ab1debd6095",
    OBLIGATION_SCHEMA: "150c0dfb2649fceb7057cd607e17bf8910ba13ffd97c7a1449995d30847c742e",
    RESULT_SCHEMA: "4d06b76fb9cca2e646c0a7b95a49d6926b83bf70b54246a40417d9667ba9cd53",
    REVISION_SCHEMA: "02b89fd663f6506a6d993900635acb5ac0cd2c283b2f9d0994378e2d35882311",
    "mathhead.problem-session-store-head.v1": (
        "a5bed15dda9e8c229687f1a89ba1ca9770e17d72314d16b5de63417472f3f683"
    ),
}

MAX_COMMAND_BYTES = 4_194_304
MAX_ARTIFACT_BYTES = 67_108_864
MAX_AGGREGATE_ARTIFACT_BYTES = 1_073_741_824
MAX_AGGREGATE_EVENT_BYTES = 1_073_741_824
MAX_EVENTS = 100_000
MAX_ARTIFACTS = 1_000_000
MAX_RECORDS = 2_000_000
MAX_DEPENDENCY_EDGES = 4_000_000
MAX_INVALIDATIONS = 1_000_000
MAX_JSON_NESTING = 128
MAX_JSON_NODES = 8_000_000
MAX_STRING_CODEPOINTS = 1_048_576
MAX_DIAGNOSTIC_CODEPOINTS = 512
MAX_INTEGER = 9_007_199_254_740_991
MAX_REPLAY_STEPS = 1_000_000_000

_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MEDIA = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,31}/[a-z0-9][a-z0-9.+-]{0,63}$")
_SCHEMA = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")

_ROLES = frozenset(
    {
        "certificate",
        "context",
        "definition_payload",
        "diagnostic_attachment",
        "engine_result",
        "evidence",
        "lemma_statement",
        "obligation",
        "problem_analysis",
        "provenance_replay",
        "resource_outcome",
        "unsupported_explanation",
        "attempt_input",
        "attempt_observation",
    }
)
_TIERS = frozenset(
    {
        "none",
        "assumed",
        "definitional",
        "unchecked",
        "producer_report",
        "solver_verdict",
        "checker_attestation",
        "external_proof_assistant",
    }
)
_RECORD_KINDS = ("definition", "lemma", "attempt", "obligation")
_PUT_KIND = {
    "put_definition": "definition",
    "put_lemma": "lemma",
    "put_attempt": "attempt",
    "put_obligation": "obligation",
}
_COMMAND_KINDS = frozenset(
    {"create_session", "replace_context", "retire_record", *_PUT_KIND}
)
_ATTEMPT_OUTCOMES = frozenset(
    {"succeeded", "failed", "cancelled", "timed_out", "exhausted"}
)
_OBLIGATION_STATES = frozenset(
    {"open", "blocked", "discharged", "reopened", "superseded"}
)


class ProblemSessionValidationError(ValueError):
    """A classified strict-boundary validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        self.kind = kind
        self.path = path
        self.detail = detail
        super().__init__(f"{kind}: {path}: {detail}")


class _Invalid(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(detail)


class _Conflict(ValueError):
    def __init__(self, reason_code: str, detail: str) -> None:
        self.reason_code = reason_code
        self.detail = detail
        super().__init__(detail)


class _Exhausted(ValueError):
    pass


class _DuplicateKey(ValueError):
    pass


class _SessionValue:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs

    def __reduce__(self) -> NoReturn:
        raise TypeError("problem-session values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("problem-session values cannot be pickled")

    def __copy__(self) -> _SessionValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _SessionValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class SessionArtifactLink(_SessionValue):
    schema: str
    role: str
    media_type: str
    artifact_schema: str | None
    sha256: str
    bytes: int
    context_sha256: str | None
    reading_id: str | None
    depends_on_sha256s: tuple[str, ...]
    retained_tier: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session artifact links are created only by validation")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionArtifactLink is final")


@dataclass(frozen=True, slots=True, init=False)
class SessionDefinition(_SessionValue):
    schema: str
    record_id: str
    generation: int
    definition_id: str
    primary_artifact_sha256: str
    problem_ir_sha256: str
    theory_context_sha256: str
    declaration_sha256: str
    depends_on_record_sha256s: tuple[str, ...]
    record_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session definitions are created only by validation")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionDefinition is final")


@dataclass(frozen=True, slots=True, init=False)
class SessionLemma(_SessionValue):
    schema: str
    record_id: str
    generation: int
    lemma_id: str
    statement_sha256: str
    primary_artifact_sha256: str
    context_sha256: str
    reading_id: str | None
    evidence_sha256: str | None
    certificate_sha256: str | None
    provenance_sha256: str | None
    retained_tier: str
    depends_on_record_sha256s: tuple[str, ...]
    record_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session lemmas are created only by validation")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionLemma is final")


@dataclass(frozen=True, slots=True, init=False)
class SessionAttempt(_SessionValue):
    schema: str
    record_id: str
    generation: int
    attempt_id: str
    strategy_id: str
    outcome: str
    context_sha256: str
    reading_id: str | None
    obligation_record_sha256s: tuple[str, ...]
    input_artifact_sha256s: tuple[str, ...]
    observation_artifact_sha256s: tuple[str, ...]
    produced_artifact_sha256s: tuple[str, ...]
    resource_outcome_sha256: str | None
    diagnostic_codes: tuple[str, ...]
    depends_on_record_sha256s: tuple[str, ...]
    record_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session attempts are created only by validation")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionAttempt is final")


@dataclass(frozen=True, slots=True, init=False)
class SessionObligation(_SessionValue):
    schema: str
    record_id: str
    generation: int
    obligation_id: str
    obligation_sha256: str
    context_sha256: str
    reading_id: str
    state: str
    evidence_sha256s: tuple[str, ...]
    depends_on_record_sha256s: tuple[str, ...]
    record_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session obligations are created only by validation")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionObligation is final")


SessionRecord = SessionDefinition | SessionLemma | SessionAttempt | SessionObligation


@dataclass(frozen=True, slots=True, init=False)
class SessionInvalidation(_SessionValue):
    schema: str
    ordinal: int
    target_record_sha256: str
    trigger_record_sha256: str | None
    old_context_sha256: str | None
    new_context_sha256: str | None
    reason: str
    invalidation_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session invalidations are created only by transition")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionInvalidation is final")


@dataclass(frozen=True, slots=True, init=False)
class SessionRevision(_SessionValue):
    schema: str
    session_id: str
    revision: int
    parent_event_sha256: str | None
    head_event_sha256: str
    context_sha256: str
    analysis_artifact_sha256s: tuple[str, ...]
    definitions: tuple[SessionDefinition, ...]
    lemmas: tuple[SessionLemma, ...]
    attempts: tuple[SessionAttempt, ...]
    obligations: tuple[SessionObligation, ...]
    stale_record_sha256s: tuple[str, ...]
    retired_record_sha256s: tuple[str, ...]
    invalidation_sha256s: tuple[str, ...]
    event_sha256s: tuple[str, ...]
    artifact_sha256s: tuple[str, ...]
    view_sha256: str
    revision_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("session revisions are created only by replay")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SessionRevision is final")


@dataclass(frozen=True, slots=True, init=False)
class ProblemSessionResult(_SessionValue):
    schema: str
    contract_id: str
    contract_sha256: str
    status: str
    reason_code: str
    diagnostic: str
    session_id: str | None
    revision: int | None
    head_sha256: str | None
    view_sha256: str | None
    event_count: int
    artifact_count: int
    stale_record_count: int
    revision_value: SessionRevision | None
    result_sha256: str | None
    mathematical_authority: bool
    events: tuple[bytes, ...] | None
    artifacts: tuple[bytes, ...] | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("problem-session results are created only by transition")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ProblemSessionResult is final")


def _make(cls: type[Any], **values: object) -> Any:
    instance = object.__new__(cls)
    for item in fields(cls):
        object.__setattr__(instance, item.name, values[item.name])
    return instance


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ProblemSessionValidationError(kind, path, detail)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        _fail("canonical", "$", f"canonical JSON encoding failed: {type(exc).__name__}")
    return (rendered + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_float(value: str) -> NoReturn:
    raise ValueError(f"non-integer JSON number is forbidden: {value[:32]}")


def _walk_canonical(value: object, path: str, depth: int, counter: list[int]) -> None:
    if depth > MAX_JSON_NESTING:
        _fail("budget", path, "JSON nesting exceeds the fixed ceiling")
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        _fail("budget", path, "JSON node count exceeds the fixed ceiling")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > MAX_INTEGER:
            _fail("budget", path, "integer exceeds the portable exact range")
        return
    if type(value) is str:
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            _fail("canonical", path, "strings must be NUL-free NFC")
        if len(value) > MAX_STRING_CODEPOINTS:
            _fail("budget", path, "string exceeds the code-point ceiling")
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _walk_canonical(item, f"{path}[{index}]", depth + 1, counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail("schema", path, "object key must be an exact string")
            _walk_canonical(key, f"{path}.<key>", depth + 1, counter)
            _walk_canonical(item, f"{path}.{key}", depth + 1, counter)
        return
    _fail("schema", path, f"forbidden JSON value type {type(value).__name__}")


def _parse_json(data: bytes, path: str, maximum: int) -> dict[str, Any]:
    if type(data) is not bytes:
        _fail("type", path, "input must be exact bytes")
    if len(data) < 3 or len(data) > maximum:
        _fail("budget", path, "input byte count is outside bounds")
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except _DuplicateKey as exc:
        _fail("duplicate", path, f"duplicate JSON key {exc.args[0]!r}")
    except UnicodeError as exc:
        _fail("encoding", path, f"invalid UTF-8: {type(exc).__name__}")
    except (ValueError, RecursionError) as exc:
        _fail("json", path, f"invalid JSON: {type(exc).__name__}")
    if type(value) is not dict:
        _fail("schema", path, "root must be an exact JSON object")
    _walk_canonical(value, path, 0, [0])
    if _canonical_bytes(value) != data:
        _fail("canonical", path, "bytes are not the unique canonical encoding")
    return value


def _closed(value: Mapping[str, object], expected: set[str], path: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        _fail("schema", path, f"field set drift; missing={missing}, extra={extra}")


def _string(value: object, path: str, *, pattern: re.Pattern[str] | None = None) -> str:
    if type(value) is not str:
        _fail("schema", path, "expected exact string")
    if not value or len(value) > MAX_STRING_CODEPOINTS:
        _fail("budget", path, "string length is outside bounds")
    if "\x00" in value or unicodedata.normalize("NFC", value) != value:
        _fail("canonical", path, "string must be NUL-free NFC")
    if pattern is not None and pattern.fullmatch(value) is None:
        _fail("schema", path, "string does not match the closed vocabulary")
    return value


def _optional_string(
    value: object, path: str, *, pattern: re.Pattern[str] | None = None
) -> str | None:
    if value is None:
        return None
    return _string(value, path, pattern=pattern)


def _integer(value: object, path: str, maximum: int = MAX_INTEGER) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        _fail("schema", path, "expected bounded nonnegative exact integer")
    return value


def _false(value: object, path: str) -> bool:
    if value is not False:
        _fail("epistemic", path, "mathematical authority must be exact false")
    return False


def _digest_value(value: object, path: str) -> str:
    return _string(value, path, pattern=_DIGEST)


def _optional_digest(value: object, path: str) -> str | None:
    return _optional_string(value, path, pattern=_DIGEST)


def _tuple_strings(
    value: object,
    path: str,
    *,
    maximum: int,
    pattern: re.Pattern[str],
    sorted_unique: bool = True,
) -> tuple[str, ...]:
    if type(value) is not list or len(value) > maximum:
        _fail("schema", path, "expected bounded array")
    result = tuple(_string(item, f"{path}[{i}]", pattern=pattern) for i, item in enumerate(value))
    if sorted_unique and tuple(sorted(set(result))) != result:
        _fail("canonical", path, "array must be sorted and unique")
    return result


def _self_digest(value: Mapping[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _digest(_canonical_bytes(preimage))


def _link_value(link: SessionArtifactLink) -> dict[str, object]:
    return {
        "artifact_schema": link.artifact_schema,
        "bytes": link.bytes,
        "context_sha256": link.context_sha256,
        "depends_on_sha256s": list(link.depends_on_sha256s),
        "mathematical_authority": link.mathematical_authority,
        "media_type": link.media_type,
        "reading_id": link.reading_id,
        "retained_tier": link.retained_tier,
        "role": link.role,
        "schema": link.schema,
        "sha256": link.sha256,
    }


def _parse_link(value: object, path: str) -> SessionArtifactLink:
    if type(value) is not dict:
        _fail("schema", path, "artifact link must be an exact object")
    expected = {
        "artifact_schema",
        "bytes",
        "context_sha256",
        "depends_on_sha256s",
        "mathematical_authority",
        "media_type",
        "reading_id",
        "retained_tier",
        "role",
        "schema",
        "sha256",
    }
    _closed(value, expected, path)
    if value["schema"] != ARTIFACT_LINK_SCHEMA:
        _fail("schema", f"{path}.schema", "artifact-link schema drift")
    role = _string(value["role"], f"{path}.role")
    if role not in _ROLES:
        _fail("schema", f"{path}.role", "unknown artifact role")
    media_type = _string(value["media_type"], f"{path}.media_type", pattern=_MEDIA)
    artifact_schema = _optional_string(
        value["artifact_schema"], f"{path}.artifact_schema", pattern=_SCHEMA
    )
    if (artifact_schema is None) == (media_type == "application/json"):
        _fail("schema", path, "JSON media requires a schema and binary media forbids one")
    tier = _string(value["retained_tier"], f"{path}.retained_tier")
    if tier not in _TIERS:
        _fail("epistemic", f"{path}.retained_tier", "unknown retained tier")
    result = _make(
        SessionArtifactLink,
        schema=ARTIFACT_LINK_SCHEMA,
        role=role,
        media_type=media_type,
        artifact_schema=artifact_schema,
        sha256=_digest_value(value["sha256"], f"{path}.sha256"),
        bytes=_integer(value["bytes"], f"{path}.bytes", MAX_ARTIFACT_BYTES),
        context_sha256=_optional_digest(value["context_sha256"], f"{path}.context_sha256"),
        reading_id=_optional_string(value["reading_id"], f"{path}.reading_id", pattern=_ID),
        depends_on_sha256s=_tuple_strings(
            value["depends_on_sha256s"],
            f"{path}.depends_on_sha256s",
            maximum=4096,
            pattern=_DIGEST,
        ),
        retained_tier=tier,
        mathematical_authority=_false(
            value["mathematical_authority"], f"{path}.mathematical_authority"
        ),
    )
    if _link_value(result) != value:
        _fail("canonical", path, "artifact-link projection drift")
    return result


def make_session_artifact_link(
    data: bytes,
    *,
    role: str,
    media_type: str = "application/json",
    artifact_schema: str | None = None,
    context_sha256: str | None = None,
    reading_id: str | None = None,
    depends_on_sha256s: tuple[str, ...] = (),
    retained_tier: str = "none",
) -> SessionArtifactLink:
    """Create one non-authoritative exact artifact link from payload bytes."""
    if type(data) is not bytes or not data or len(data) > MAX_ARTIFACT_BYTES:
        _fail("type", "data", "artifact data must be nonempty bounded exact bytes")
    value = {
        "artifact_schema": artifact_schema,
        "bytes": len(data),
        "context_sha256": context_sha256,
        "depends_on_sha256s": list(depends_on_sha256s),
        "mathematical_authority": False,
        "media_type": media_type,
        "reading_id": reading_id,
        "retained_tier": retained_tier,
        "role": role,
        "schema": ARTIFACT_LINK_SCHEMA,
        "sha256": _digest(data),
    }
    link = _parse_link(value, "artifact_link")
    _validate_link_payload(link, data, "data")
    return link


def _definition_value(record: SessionDefinition) -> dict[str, object]:
    return {
        "declaration_sha256": record.declaration_sha256,
        "definition_id": record.definition_id,
        "depends_on_record_sha256s": list(record.depends_on_record_sha256s),
        "generation": record.generation,
        "mathematical_authority": record.mathematical_authority,
        "primary_artifact_sha256": record.primary_artifact_sha256,
        "problem_ir_sha256": record.problem_ir_sha256,
        "record_id": record.record_id,
        "record_sha256": record.record_sha256,
        "schema": record.schema,
        "theory_context_sha256": record.theory_context_sha256,
    }


def _lemma_value(record: SessionLemma) -> dict[str, object]:
    return {
        "certificate_sha256": record.certificate_sha256,
        "context_sha256": record.context_sha256,
        "depends_on_record_sha256s": list(record.depends_on_record_sha256s),
        "evidence_sha256": record.evidence_sha256,
        "generation": record.generation,
        "lemma_id": record.lemma_id,
        "mathematical_authority": record.mathematical_authority,
        "primary_artifact_sha256": record.primary_artifact_sha256,
        "provenance_sha256": record.provenance_sha256,
        "reading_id": record.reading_id,
        "record_id": record.record_id,
        "record_sha256": record.record_sha256,
        "retained_tier": record.retained_tier,
        "schema": record.schema,
        "statement_sha256": record.statement_sha256,
    }


def _attempt_value(record: SessionAttempt) -> dict[str, object]:
    return {
        "attempt_id": record.attempt_id,
        "context_sha256": record.context_sha256,
        "depends_on_record_sha256s": list(record.depends_on_record_sha256s),
        "diagnostic_codes": list(record.diagnostic_codes),
        "generation": record.generation,
        "input_artifact_sha256s": list(record.input_artifact_sha256s),
        "mathematical_authority": record.mathematical_authority,
        "obligation_record_sha256s": list(record.obligation_record_sha256s),
        "observation_artifact_sha256s": list(record.observation_artifact_sha256s),
        "outcome": record.outcome,
        "produced_artifact_sha256s": list(record.produced_artifact_sha256s),
        "reading_id": record.reading_id,
        "record_id": record.record_id,
        "record_sha256": record.record_sha256,
        "resource_outcome_sha256": record.resource_outcome_sha256,
        "schema": record.schema,
        "strategy_id": record.strategy_id,
    }


def _obligation_value(record: SessionObligation) -> dict[str, object]:
    return {
        "context_sha256": record.context_sha256,
        "depends_on_record_sha256s": list(record.depends_on_record_sha256s),
        "evidence_sha256s": list(record.evidence_sha256s),
        "generation": record.generation,
        "mathematical_authority": record.mathematical_authority,
        "obligation_id": record.obligation_id,
        "obligation_sha256": record.obligation_sha256,
        "reading_id": record.reading_id,
        "record_id": record.record_id,
        "record_sha256": record.record_sha256,
        "schema": record.schema,
        "state": record.state,
    }


def _record_value(record: SessionRecord) -> dict[str, object]:
    if type(record) is SessionDefinition:
        return _definition_value(record)
    if type(record) is SessionLemma:
        return _lemma_value(record)
    if type(record) is SessionAttempt:
        return _attempt_value(record)
    if type(record) is SessionObligation:
        return _obligation_value(record)
    _fail("type", "record", "unknown session record type")


def _base_record(
    value: Mapping[str, object], path: str, schema: str, expected: set[str]
) -> tuple[str, int, tuple[str, ...], str, bool]:
    _closed(value, expected, path)
    if value["schema"] != schema:
        _fail("schema", f"{path}.schema", "record schema drift")
    record_id = _string(value["record_id"], f"{path}.record_id", pattern=_ID)
    generation = _integer(value["generation"], f"{path}.generation")
    dependencies = _tuple_strings(
        value["depends_on_record_sha256s"],
        f"{path}.depends_on_record_sha256s",
        maximum=4096,
        pattern=_DIGEST,
    )
    record_sha256 = _digest_value(value["record_sha256"], f"{path}.record_sha256")
    if _self_digest(value, "record_sha256") != record_sha256:
        _fail("identity", f"{path}.record_sha256", "record identity drift")
    authority = _false(value["mathematical_authority"], f"{path}.mathematical_authority")
    return record_id, generation, dependencies, record_sha256, authority


def _parse_definition(value: object, path: str) -> SessionDefinition:
    if type(value) is not dict:
        _fail("schema", path, "definition must be an exact object")
    expected = {
        "declaration_sha256", "definition_id", "depends_on_record_sha256s",
        "generation", "mathematical_authority", "primary_artifact_sha256",
        "problem_ir_sha256", "record_id", "record_sha256", "schema",
        "theory_context_sha256",
    }
    record_id, generation, dependencies, record_sha256, authority = _base_record(
        value, path, DEFINITION_SCHEMA, expected
    )
    result = _make(
        SessionDefinition,
        schema=DEFINITION_SCHEMA,
        record_id=record_id,
        generation=generation,
        definition_id=_string(value["definition_id"], f"{path}.definition_id", pattern=_ID),
        primary_artifact_sha256=_digest_value(
            value["primary_artifact_sha256"], f"{path}.primary_artifact_sha256"
        ),
        problem_ir_sha256=_digest_value(value["problem_ir_sha256"], f"{path}.problem_ir_sha256"),
        theory_context_sha256=_digest_value(
            value["theory_context_sha256"], f"{path}.theory_context_sha256"
        ),
        declaration_sha256=_digest_value(
            value["declaration_sha256"], f"{path}.declaration_sha256"
        ),
        depends_on_record_sha256s=dependencies,
        record_sha256=record_sha256,
        mathematical_authority=authority,
    )
    if _definition_value(result) != value:
        _fail("canonical", path, "definition projection drift")
    return result


def _parse_lemma(value: object, path: str) -> SessionLemma:
    if type(value) is not dict:
        _fail("schema", path, "lemma must be an exact object")
    expected = {
        "certificate_sha256", "context_sha256", "depends_on_record_sha256s",
        "evidence_sha256", "generation", "lemma_id", "mathematical_authority",
        "primary_artifact_sha256", "provenance_sha256", "reading_id", "record_id",
        "record_sha256", "retained_tier", "schema", "statement_sha256",
    }
    record_id, generation, dependencies, record_sha256, authority = _base_record(
        value, path, LEMMA_SCHEMA, expected
    )
    tier = _string(value["retained_tier"], f"{path}.retained_tier")
    if tier not in {"unchecked", "checker_attestation", "external_proof_assistant"}:
        _fail("epistemic", f"{path}.retained_tier", "invalid lemma tier")
    evidence = _optional_digest(value["evidence_sha256"], f"{path}.evidence_sha256")
    certificate = _optional_digest(
        value["certificate_sha256"], f"{path}.certificate_sha256"
    )
    provenance = _optional_digest(
        value["provenance_sha256"], f"{path}.provenance_sha256"
    )
    if tier == "unchecked" and any(item is not None for item in (evidence, certificate, provenance)):
        _fail("epistemic", path, "unchecked lemma must not carry attestation links")
    if tier != "unchecked" and any(item is None for item in (evidence, certificate, provenance)):
        _fail("epistemic", path, "attested lemma requires evidence, certificate, and provenance")
    result = _make(
        SessionLemma,
        schema=LEMMA_SCHEMA,
        record_id=record_id,
        generation=generation,
        lemma_id=_string(value["lemma_id"], f"{path}.lemma_id", pattern=_ID),
        statement_sha256=_digest_value(value["statement_sha256"], f"{path}.statement_sha256"),
        primary_artifact_sha256=_digest_value(
            value["primary_artifact_sha256"], f"{path}.primary_artifact_sha256"
        ),
        context_sha256=_digest_value(value["context_sha256"], f"{path}.context_sha256"),
        reading_id=_optional_string(value["reading_id"], f"{path}.reading_id", pattern=_ID),
        evidence_sha256=evidence,
        certificate_sha256=certificate,
        provenance_sha256=provenance,
        retained_tier=tier,
        depends_on_record_sha256s=dependencies,
        record_sha256=record_sha256,
        mathematical_authority=authority,
    )
    if _lemma_value(result) != value:
        _fail("canonical", path, "lemma projection drift")
    return result


def _parse_attempt(value: object, path: str) -> SessionAttempt:
    if type(value) is not dict:
        _fail("schema", path, "attempt must be an exact object")
    expected = {
        "attempt_id", "context_sha256", "depends_on_record_sha256s",
        "diagnostic_codes", "generation", "input_artifact_sha256s",
        "mathematical_authority", "obligation_record_sha256s",
        "observation_artifact_sha256s", "outcome", "produced_artifact_sha256s",
        "reading_id", "record_id", "record_sha256", "resource_outcome_sha256",
        "schema", "strategy_id",
    }
    record_id, generation, dependencies, record_sha256, authority = _base_record(
        value, path, ATTEMPT_SCHEMA, expected
    )
    outcome = _string(value["outcome"], f"{path}.outcome")
    if outcome not in _ATTEMPT_OUTCOMES:
        _fail("lifecycle", f"{path}.outcome", "unknown attempt outcome")
    diagnostic_codes = _tuple_strings(
        value["diagnostic_codes"],
        f"{path}.diagnostic_codes",
        maximum=64,
        pattern=_CODE,
    )
    result = _make(
        SessionAttempt,
        schema=ATTEMPT_SCHEMA,
        record_id=record_id,
        generation=generation,
        attempt_id=_string(value["attempt_id"], f"{path}.attempt_id", pattern=_ID),
        strategy_id=_string(value["strategy_id"], f"{path}.strategy_id", pattern=_ID),
        outcome=outcome,
        context_sha256=_digest_value(value["context_sha256"], f"{path}.context_sha256"),
        reading_id=_optional_string(value["reading_id"], f"{path}.reading_id", pattern=_ID),
        obligation_record_sha256s=_tuple_strings(
            value["obligation_record_sha256s"],
            f"{path}.obligation_record_sha256s",
            maximum=4096,
            pattern=_DIGEST,
        ),
        input_artifact_sha256s=_tuple_strings(
            value["input_artifact_sha256s"],
            f"{path}.input_artifact_sha256s",
            maximum=4096,
            pattern=_DIGEST,
        ),
        observation_artifact_sha256s=_tuple_strings(
            value["observation_artifact_sha256s"],
            f"{path}.observation_artifact_sha256s",
            maximum=4096,
            pattern=_DIGEST,
        ),
        produced_artifact_sha256s=_tuple_strings(
            value["produced_artifact_sha256s"],
            f"{path}.produced_artifact_sha256s",
            maximum=4096,
            pattern=_DIGEST,
        ),
        resource_outcome_sha256=_optional_digest(
            value["resource_outcome_sha256"], f"{path}.resource_outcome_sha256"
        ),
        diagnostic_codes=diagnostic_codes,
        depends_on_record_sha256s=dependencies,
        record_sha256=record_sha256,
        mathematical_authority=authority,
    )
    if _attempt_value(result) != value:
        _fail("canonical", path, "attempt projection drift")
    return result


def _parse_obligation(value: object, path: str) -> SessionObligation:
    if type(value) is not dict:
        _fail("schema", path, "obligation must be an exact object")
    expected = {
        "context_sha256", "depends_on_record_sha256s", "evidence_sha256s",
        "generation", "mathematical_authority", "obligation_id",
        "obligation_sha256", "reading_id", "record_id", "record_sha256",
        "schema", "state",
    }
    record_id, generation, dependencies, record_sha256, authority = _base_record(
        value, path, OBLIGATION_SCHEMA, expected
    )
    state = _string(value["state"], f"{path}.state")
    if state not in _OBLIGATION_STATES:
        _fail("lifecycle", f"{path}.state", "unknown obligation state")
    evidence = _tuple_strings(
        value["evidence_sha256s"],
        f"{path}.evidence_sha256s",
        maximum=4096,
        pattern=_DIGEST,
    )
    if state == "discharged" and not evidence:
        _fail("epistemic", path, "discharged obligation requires retained evidence")
    if state != "discharged" and evidence:
        _fail("epistemic", path, "only discharged obligation may retain evidence")
    result = _make(
        SessionObligation,
        schema=OBLIGATION_SCHEMA,
        record_id=record_id,
        generation=generation,
        obligation_id=_string(value["obligation_id"], f"{path}.obligation_id", pattern=_ID),
        obligation_sha256=_digest_value(
            value["obligation_sha256"], f"{path}.obligation_sha256"
        ),
        context_sha256=_digest_value(value["context_sha256"], f"{path}.context_sha256"),
        reading_id=_string(value["reading_id"], f"{path}.reading_id", pattern=_ID),
        state=state,
        evidence_sha256s=evidence,
        depends_on_record_sha256s=dependencies,
        record_sha256=record_sha256,
        mathematical_authority=authority,
    )
    if _obligation_value(result) != value:
        _fail("canonical", path, "obligation projection drift")
    return result


def _parse_record(value: object, path: str) -> tuple[str, SessionRecord]:
    if type(value) is not dict or type(value.get("schema")) is not str:
        _fail("schema", path, "record must have one exact schema")
    schema = value["schema"]
    if schema == DEFINITION_SCHEMA:
        return "definition", _parse_definition(value, path)
    if schema == LEMMA_SCHEMA:
        return "lemma", _parse_lemma(value, path)
    if schema == ATTEMPT_SCHEMA:
        return "attempt", _parse_attempt(value, path)
    if schema == OBLIGATION_SCHEMA:
        return "obligation", _parse_obligation(value, path)
    _fail("schema", f"{path}.schema", "unknown session record schema")


def _record_context(record: SessionRecord) -> str:
    if type(record) is SessionDefinition:
        return record.theory_context_sha256
    return record.context_sha256


def _record_artifact_refs(record: SessionRecord) -> tuple[tuple[str, str | None], ...]:
    if type(record) is SessionDefinition:
        return (
            (record.primary_artifact_sha256, "definition_payload"),
            (record.problem_ir_sha256, None),
            (record.theory_context_sha256, "context"),
        )
    if type(record) is SessionLemma:
        values: list[tuple[str, str | None]] = [
            (record.primary_artifact_sha256, "lemma_statement"),
            (record.statement_sha256, None),
            (record.context_sha256, "context"),
        ]
        if record.evidence_sha256 is not None:
            values.append((record.evidence_sha256, "evidence"))
        if record.certificate_sha256 is not None:
            values.append((record.certificate_sha256, "certificate"))
        if record.provenance_sha256 is not None:
            values.append((record.provenance_sha256, "provenance_replay"))
        return tuple(values)
    if type(record) is SessionAttempt:
        values = [(record.context_sha256, "context")]
        values.extend((item, "attempt_input") for item in record.input_artifact_sha256s)
        values.extend(
            (item, "attempt_observation") for item in record.observation_artifact_sha256s
        )
        values.extend((item, None) for item in record.produced_artifact_sha256s)
        if record.resource_outcome_sha256 is not None:
            values.append((record.resource_outcome_sha256, "resource_outcome"))
        return tuple(values)
    values = [
        (record.obligation_sha256, "obligation"),
        (record.context_sha256, "context"),
    ]
    values.extend((item, None) for item in record.evidence_sha256s)
    return tuple(values)


def _record_factory(schema: str, values: dict[str, object]) -> SessionRecord:
    values["schema"] = schema
    values["mathematical_authority"] = False
    values["record_sha256"] = None
    values["record_sha256"] = _self_digest(values, "record_sha256")
    return _parse_record(values, "record")[1]


def make_session_definition(
    *, record_id: str, generation: int, definition_id: str,
    primary_artifact_sha256: str, problem_ir_sha256: str,
    theory_context_sha256: str, declaration_sha256: str,
    depends_on_record_sha256s: tuple[str, ...] = (),
) -> SessionDefinition:
    return _record_factory(
        DEFINITION_SCHEMA,
        {
            "record_id": record_id,
            "generation": generation,
            "definition_id": definition_id,
            "primary_artifact_sha256": primary_artifact_sha256,
            "problem_ir_sha256": problem_ir_sha256,
            "theory_context_sha256": theory_context_sha256,
            "declaration_sha256": declaration_sha256,
            "depends_on_record_sha256s": list(depends_on_record_sha256s),
        },
    )  # type: ignore[return-value]


def make_session_lemma(
    *, record_id: str, generation: int, lemma_id: str, statement_sha256: str,
    primary_artifact_sha256: str, context_sha256: str, reading_id: str | None = None,
    evidence_sha256: str | None = None, certificate_sha256: str | None = None,
    provenance_sha256: str | None = None, retained_tier: str = "unchecked",
    depends_on_record_sha256s: tuple[str, ...] = (),
) -> SessionLemma:
    return _record_factory(
        LEMMA_SCHEMA,
        {
            "record_id": record_id, "generation": generation, "lemma_id": lemma_id,
            "statement_sha256": statement_sha256,
            "primary_artifact_sha256": primary_artifact_sha256,
            "context_sha256": context_sha256, "reading_id": reading_id,
            "evidence_sha256": evidence_sha256, "certificate_sha256": certificate_sha256,
            "provenance_sha256": provenance_sha256, "retained_tier": retained_tier,
            "depends_on_record_sha256s": list(depends_on_record_sha256s),
        },
    )  # type: ignore[return-value]


def make_session_attempt(
    *, record_id: str, generation: int, attempt_id: str, strategy_id: str,
    outcome: str, context_sha256: str, reading_id: str | None = None,
    obligation_record_sha256s: tuple[str, ...] = (),
    input_artifact_sha256s: tuple[str, ...] = (),
    observation_artifact_sha256s: tuple[str, ...] = (),
    produced_artifact_sha256s: tuple[str, ...] = (),
    resource_outcome_sha256: str | None = None,
    diagnostic_codes: tuple[str, ...] = (),
    depends_on_record_sha256s: tuple[str, ...] = (),
) -> SessionAttempt:
    return _record_factory(
        ATTEMPT_SCHEMA,
        {
            "record_id": record_id, "generation": generation, "attempt_id": attempt_id,
            "strategy_id": strategy_id, "outcome": outcome,
            "context_sha256": context_sha256, "reading_id": reading_id,
            "obligation_record_sha256s": list(obligation_record_sha256s),
            "input_artifact_sha256s": list(input_artifact_sha256s),
            "observation_artifact_sha256s": list(observation_artifact_sha256s),
            "produced_artifact_sha256s": list(produced_artifact_sha256s),
            "resource_outcome_sha256": resource_outcome_sha256,
            "diagnostic_codes": list(diagnostic_codes),
            "depends_on_record_sha256s": list(depends_on_record_sha256s),
        },
    )  # type: ignore[return-value]


def make_session_obligation(
    *, record_id: str, generation: int, obligation_id: str,
    obligation_sha256: str, context_sha256: str, reading_id: str,
    state: str = "open", evidence_sha256s: tuple[str, ...] = (),
    depends_on_record_sha256s: tuple[str, ...] = (),
) -> SessionObligation:
    return _record_factory(
        OBLIGATION_SCHEMA,
        {
            "record_id": record_id, "generation": generation,
            "obligation_id": obligation_id, "obligation_sha256": obligation_sha256,
            "context_sha256": context_sha256, "reading_id": reading_id, "state": state,
            "evidence_sha256s": list(evidence_sha256s),
            "depends_on_record_sha256s": list(depends_on_record_sha256s),
        },
    )  # type: ignore[return-value]


def session_component_to_bytes(
    value: SessionArtifactLink | SessionRecord | SessionInvalidation | SessionRevision,
) -> bytes:
    """Serialize one strictly revalidated session component."""
    if type(value) is SessionArtifactLink:
        parsed: object = _parse_link(_link_value(value), "component")
        return _canonical_bytes(_link_value(parsed))  # type: ignore[arg-type]
    if type(value) in {SessionDefinition, SessionLemma, SessionAttempt, SessionObligation}:
        record_value = _record_value(value)  # type: ignore[arg-type]
        _parse_record(record_value, "component")
        return _canonical_bytes(record_value)
    if type(value) is SessionInvalidation:
        invalidation_value = _invalidation_value(value)
        _parse_invalidation(invalidation_value, "component")
        return _canonical_bytes(invalidation_value)
    if type(value) is SessionRevision:
        revision_value = _revision_value(value)
        _parse_revision(revision_value, "component")
        return _canonical_bytes(revision_value)
    _fail("type", "component", "unknown problem-session component")


_COMMAND_FIELDS = {
    "analysis_artifact_sha256s",
    "command_id",
    "command_sha256",
    "context_sha256",
    "expected_head_sha256",
    "introduced_artifacts",
    "kind",
    "reason_code",
    "record",
    "schema",
    "session_id",
    "target_record_id",
    "target_record_kind",
}


def _parse_command_value(value: object, path: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail("schema", path, "command must be an exact object")
    _closed(value, _COMMAND_FIELDS, path)
    if value["schema"] != COMMAND_SCHEMA:
        _fail("schema", f"{path}.schema", "command schema drift")
    kind = _string(value["kind"], f"{path}.kind")
    if kind not in _COMMAND_KINDS:
        _fail("command", f"{path}.kind", "unknown command kind")
    command_id = _string(value["command_id"], f"{path}.command_id", pattern=_ID)
    session_id = _string(value["session_id"], f"{path}.session_id", pattern=_ID)
    expected_head = _optional_digest(
        value["expected_head_sha256"], f"{path}.expected_head_sha256"
    )
    context = _optional_digest(value["context_sha256"], f"{path}.context_sha256")
    analysis = _tuple_strings(
        value["analysis_artifact_sha256s"],
        f"{path}.analysis_artifact_sha256s",
        maximum=4096,
        pattern=_DIGEST,
    )
    links_raw = value["introduced_artifacts"]
    if type(links_raw) is not list or len(links_raw) > 4096:
        _fail("schema", f"{path}.introduced_artifacts", "expected bounded array")
    links = tuple(
        _parse_link(item, f"{path}.introduced_artifacts[{index}]")
        for index, item in enumerate(links_raw)
    )
    if tuple(sorted(link.sha256 for link in links)) != tuple(link.sha256 for link in links):
        _fail("canonical", f"{path}.introduced_artifacts", "links must sort by digest")
    if len({link.sha256 for link in links}) != len(links):
        _fail("reference", f"{path}.introduced_artifacts", "duplicate artifact identity")
    record: SessionRecord | None
    record_kind: str | None
    if value["record"] is None:
        record = None
        record_kind = None
    else:
        record_kind, record = _parse_record(value["record"], f"{path}.record")
    target_kind = value["target_record_kind"]
    if target_kind is not None:
        target_kind = _string(target_kind, f"{path}.target_record_kind")
        if target_kind not in _RECORD_KINDS:
            _fail("command", f"{path}.target_record_kind", "unknown record kind")
    target_id = _optional_string(
        value["target_record_id"], f"{path}.target_record_id", pattern=_ID
    )
    reason = _optional_string(value["reason_code"], f"{path}.reason_code", pattern=_CODE)
    command_sha = _digest_value(value["command_sha256"], f"{path}.command_sha256")
    if _self_digest(value, "command_sha256") != command_sha:
        _fail("identity", f"{path}.command_sha256", "command identity drift")
    if kind == "create_session":
        if expected_head is not None or context is None or not analysis:
            _fail("command", path, "create requires null head, context, and analysis")
        if record is not None or target_kind is not None or target_id is not None or reason is not None:
            _fail("command", path, "create carries forbidden record fields")
    elif kind == "replace_context":
        if expected_head is None or context is None or not analysis:
            _fail("command", path, "context replacement requires head, context, and analysis")
        if record is not None or target_kind is not None or target_id is not None or reason is not None:
            _fail("command", path, "context replacement carries forbidden record fields")
    elif kind in _PUT_KIND:
        if expected_head is None or context is not None or analysis:
            _fail("command", path, "record command has invalid head or context fields")
        if record is None or record_kind != _PUT_KIND[kind]:
            _fail("command", path, "record schema does not match command kind")
        if target_kind is not None or target_id is not None or reason is not None:
            _fail("command", path, "record command carries retirement fields")
    else:
        if expected_head is None or context is not None or analysis or links or record is not None:
            _fail("command", path, "retirement has invalid state fields")
        if target_kind is None or target_id is None or reason is None:
            _fail("command", path, "retirement requires target and reason")
    return {
        "value": value,
        "kind": kind,
        "command_id": command_id,
        "session_id": session_id,
        "expected_head": expected_head,
        "context": context,
        "analysis": analysis,
        "links": links,
        "record": record,
        "record_kind": record_kind,
        "target_kind": target_kind,
        "target_id": target_id,
        "reason": reason,
        "sha256": command_sha,
    }


def parse_problem_session_command(data: bytes) -> dict[str, object]:
    """Strictly parse canonical command bytes and return an owned projection."""
    parsed = _parse_command_value(_parse_json(data, "command", MAX_COMMAND_BYTES), "command")
    return dict(parsed["value"])  # type: ignore[arg-type]


def make_problem_session_command(
    *,
    command_id: str,
    kind: str,
    session_id: str,
    expected_head_sha256: str | None = None,
    context_sha256: str | None = None,
    analysis_artifact_sha256s: tuple[str, ...] = (),
    introduced_artifacts: tuple[SessionArtifactLink, ...] = (),
    record: SessionRecord | None = None,
    target_record_kind: str | None = None,
    target_record_id: str | None = None,
    reason_code: str | None = None,
) -> bytes:
    """Build one canonical self-addressed command without applying it."""
    links = tuple(_parse_link(_link_value(item), "introduced_artifacts") for item in introduced_artifacts)
    value: dict[str, object] = {
        "analysis_artifact_sha256s": list(analysis_artifact_sha256s),
        "command_id": command_id,
        "command_sha256": None,
        "context_sha256": context_sha256,
        "expected_head_sha256": expected_head_sha256,
        "introduced_artifacts": [_link_value(item) for item in links],
        "kind": kind,
        "reason_code": reason_code,
        "record": None if record is None else _record_value(record),
        "schema": COMMAND_SCHEMA,
        "session_id": session_id,
        "target_record_id": target_record_id,
        "target_record_kind": target_record_kind,
    }
    value["command_sha256"] = _self_digest(value, "command_sha256")
    _parse_command_value(value, "command")
    return _canonical_bytes(value)


def _invalidation_value(item: SessionInvalidation) -> dict[str, object]:
    return {
        "invalidation_sha256": item.invalidation_sha256,
        "mathematical_authority": item.mathematical_authority,
        "new_context_sha256": item.new_context_sha256,
        "old_context_sha256": item.old_context_sha256,
        "ordinal": item.ordinal,
        "reason": item.reason,
        "schema": item.schema,
        "target_record_sha256": item.target_record_sha256,
        "trigger_record_sha256": item.trigger_record_sha256,
    }


def _parse_invalidation(value: object, path: str) -> SessionInvalidation:
    if type(value) is not dict:
        _fail("schema", path, "invalidation must be an exact object")
    expected = {
        "invalidation_sha256", "mathematical_authority", "new_context_sha256",
        "old_context_sha256", "ordinal", "reason", "schema",
        "target_record_sha256", "trigger_record_sha256",
    }
    _closed(value, expected, path)
    if value["schema"] != INVALIDATION_SCHEMA:
        _fail("schema", f"{path}.schema", "invalidation schema drift")
    reason = _string(value["reason"], f"{path}.reason")
    if reason not in {
        "context_revised", "dependency_replaced", "dependency_retired",
        "superseded", "retired",
    }:
        _fail("lifecycle", f"{path}.reason", "unknown invalidation reason")
    identity = _digest_value(value["invalidation_sha256"], f"{path}.invalidation_sha256")
    if _self_digest(value, "invalidation_sha256") != identity:
        _fail("identity", f"{path}.invalidation_sha256", "invalidation identity drift")
    result = _make(
        SessionInvalidation,
        schema=INVALIDATION_SCHEMA,
        ordinal=_integer(value["ordinal"], f"{path}.ordinal", MAX_INVALIDATIONS - 1),
        target_record_sha256=_digest_value(
            value["target_record_sha256"], f"{path}.target_record_sha256"
        ),
        trigger_record_sha256=_optional_digest(
            value["trigger_record_sha256"], f"{path}.trigger_record_sha256"
        ),
        old_context_sha256=_optional_digest(
            value["old_context_sha256"], f"{path}.old_context_sha256"
        ),
        new_context_sha256=_optional_digest(
            value["new_context_sha256"], f"{path}.new_context_sha256"
        ),
        reason=reason,
        invalidation_sha256=identity,
        mathematical_authority=_false(
            value["mathematical_authority"], f"{path}.mathematical_authority"
        ),
    )
    if _invalidation_value(result) != value:
        _fail("canonical", path, "invalidation projection drift")
    return result


def _new_invalidation(
    *, ordinal: int, target: str, trigger: str | None,
    old_context: str | None, new_context: str | None, reason: str,
) -> SessionInvalidation:
    value: dict[str, object] = {
        "invalidation_sha256": None,
        "mathematical_authority": False,
        "new_context_sha256": new_context,
        "old_context_sha256": old_context,
        "ordinal": ordinal,
        "reason": reason,
        "schema": INVALIDATION_SCHEMA,
        "target_record_sha256": target,
        "trigger_record_sha256": trigger,
    }
    value["invalidation_sha256"] = _self_digest(value, "invalidation_sha256")
    return _parse_invalidation(value, "invalidation")


@dataclass(slots=True)
class _State:
    session_id: str | None
    revision: int
    head: str | None
    context: str | None
    analysis: tuple[str, ...]
    current: dict[str, dict[str, SessionRecord]]
    stale: list[str]
    retired: list[str]
    invalidations: list[str]
    event_sha256s: list[str]
    artifact_links: dict[str, SessionArtifactLink]
    command_ids: dict[str, str]
    last_command_bytes: bytes | None


def _empty_state() -> _State:
    return _State(
        session_id=None,
        revision=-1,
        head=None,
        context=None,
        analysis=(),
        current={kind: {} for kind in _RECORD_KINDS},
        stale=[],
        retired=[],
        invalidations=[],
        event_sha256s=[],
        artifact_links={},
        command_ids={},
        last_command_bytes=None,
    )


def _all_current(state: _State) -> dict[str, tuple[str, SessionRecord]]:
    result: dict[str, tuple[str, SessionRecord]] = {}
    for kind in _RECORD_KINDS:
        for record_id, record in state.current[kind].items():
            result[record.record_sha256] = (kind, record)
            if record_id != record.record_id:
                raise AssertionError("internal record index drift")
    return result


def _validate_link_payload(link: SessionArtifactLink, data: bytes, path: str) -> None:
    if type(data) is not bytes or not data or len(data) > MAX_ARTIFACT_BYTES:
        _fail("type", path, "artifact payload must be nonempty bounded exact bytes")
    if len(data) != link.bytes or _digest(data) != link.sha256:
        _fail("identity", path, "artifact bytes differ from their link")
    if link.artifact_schema is not None:
        value = _parse_json(data, path, MAX_ARTIFACT_BYTES)
        if value.get("schema") != link.artifact_schema:
            _fail("schema", path, "artifact root schema differs from its link")


def _artifact_map(artifacts: tuple[bytes, ...]) -> dict[str, bytes]:
    if type(artifacts) is not tuple:
        _fail("type", "artifacts", "artifacts must be an exact tuple")
    if len(artifacts) > MAX_ARTIFACTS:
        raise _Exhausted("artifact count exceeds budget")
    result: dict[str, bytes] = {}
    total = 0
    order: list[str] = []
    for index, data in enumerate(artifacts):
        if type(data) is not bytes:
            _fail("type", f"artifacts[{index}]", "artifact must be exact bytes")
        if not data or len(data) > MAX_ARTIFACT_BYTES:
            raise _Exhausted("artifact byte count exceeds budget")
        total += len(data)
        if total > MAX_AGGREGATE_ARTIFACT_BYTES:
            raise _Exhausted("aggregate artifact bytes exceed budget")
        identity = _digest(data)
        if identity in result:
            _fail("reference", f"artifacts[{index}]", "duplicate artifact content identity")
        result[identity] = data
        order.append(identity)
    if order != sorted(order):
        _fail("canonical", "artifacts", "artifact tuple must sort by full SHA-256")
    return result


def _install_links(
    state: _State,
    links: tuple[SessionArtifactLink, ...],
    artifacts: Mapping[str, bytes],
    *,
    replay: bool,
) -> None:
    for link in links:
        existing = state.artifact_links.get(link.sha256)
        if existing is not None:
            if replay:
                _fail("reference", "event.command.introduced_artifacts", "artifact reintroduced")
            _fail("reference", "command.introduced_artifacts", "artifact already exists in session")
        payload = artifacts.get(link.sha256)
        if payload is None:
            _fail("reference", "introduced_artifacts", "linked artifact bytes are missing")
        _validate_link_payload(link, payload, f"artifacts[{link.sha256}]")
        state.artifact_links[link.sha256] = link


def _require_artifact(
    state: _State, identity: str, path: str, role: str | None = None
) -> SessionArtifactLink:
    link = state.artifact_links.get(identity)
    if link is None:
        _fail("reference", path, "artifact identity is not linked in the session")
    if role is not None and link.role != role:
        _fail("reference", path, f"artifact role must be {role}")
    return link


def _validate_record_references(
    state: _State, record: SessionRecord, kind: str
) -> None:
    assert state.context is not None
    if _record_context(record) != state.context:
        _fail("session", "command.record", "record context is not the current context")
    current = _all_current(state)
    dependencies = record.depends_on_record_sha256s
    for index, dependency in enumerate(dependencies):
        if dependency not in current:
            _fail("dependency", f"command.record.depends_on_record_sha256s[{index}]", "dependency is not current")
        dependent = current[dependency][1]
        reading = getattr(record, "reading_id", None)
        parent_reading = getattr(dependent, "reading_id", None)
        if reading is not None and parent_reading is not None and reading != parent_reading:
            _fail("dependency", "command.record", "dependency crosses reading boundary")
    existing = state.current[kind].get(record.record_id)
    expected_generation = 0 if existing is None else existing.generation + 1
    if record.generation != expected_generation:
        raise _Conflict("GENERATION_MISMATCH", "record generation is not the exact next value")
    for identity, role in _record_artifact_refs(record):
        _require_artifact(state, identity, "command.record", role)
    if type(record) is SessionAttempt:
        for identity in record.obligation_record_sha256s:
            current_entry = current.get(identity)
            if current_entry is None or current_entry[0] != "obligation":
                _fail("reference", "command.record.obligation_record_sha256s", "attempt obligation is not current")
        for identity in record.produced_artifact_sha256s:
            _require_artifact(state, identity, "command.record.produced_artifact_sha256s")
    if type(record) is SessionObligation:
        for identity in record.evidence_sha256s:
            link = _require_artifact(state, identity, "command.record.evidence_sha256s")
            if link.role not in {"evidence", "certificate", "provenance_replay", "engine_result"}:
                _fail("epistemic", "command.record.evidence_sha256s", "ineligible evidence role")
            if link.context_sha256 not in {None, state.context}:
                _fail("epistemic", "command.record.evidence_sha256s", "evidence context is stale")


def _dependency_closure(
    state: _State,
    seeds: list[tuple[str, str | None, str]],
    *,
    old_context: str | None,
    new_context: str | None,
) -> tuple[SessionInvalidation, ...]:
    current = _all_current(state)
    chosen: dict[str, tuple[int, str | None, str]] = {}
    frontier: list[tuple[str, str | None, str]] = sorted(seeds, key=lambda item: item[0])
    for target, trigger, reason in frontier:
        if target in current and target not in chosen:
            chosen[target] = (0, trigger, reason)
    depth = 0
    while frontier:
        triggers = {item[0] for item in frontier}
        next_items: dict[str, tuple[str, str]] = {}
        for identity, (_, record) in sorted(current.items()):
            if identity in chosen:
                continue
            matches = sorted(set(record.depends_on_record_sha256s) & triggers)
            if matches:
                root_reasons = {chosen[item][2] for item in matches}
                reason = (
                    "dependency_retired" if root_reasons & {"retired", "dependency_retired"}
                    else "dependency_replaced"
                )
                next_items[identity] = (matches[0], reason)
        depth += 1
        frontier = []
        for identity in sorted(next_items):
            trigger, reason = next_items[identity]
            chosen[identity] = (depth, trigger, reason)
            frontier.append((identity, trigger, reason))
        if len(chosen) > MAX_INVALIDATIONS:
            raise _Exhausted("invalidation count exceeds budget")
    ordered = sorted(chosen.items(), key=lambda item: (item[1][0], item[0]))
    return tuple(
        _new_invalidation(
            ordinal=index,
            target=identity,
            trigger=metadata[1],
            old_context=old_context,
            new_context=new_context,
            reason=metadata[2],
        )
        for index, (identity, metadata) in enumerate(ordered)
    )


def _remove_invalidated(state: _State, invalidations: tuple[SessionInvalidation, ...]) -> None:
    by_sha = {item.target_record_sha256: item for item in invalidations}
    for kind in _RECORD_KINDS:
        retained: dict[str, SessionRecord] = {}
        for record_id, record in state.current[kind].items():
            item = by_sha.get(record.record_sha256)
            if item is None:
                retained[record_id] = record
            elif item.reason == "retired":
                state.retired.append(record.record_sha256)
            else:
                state.stale.append(record.record_sha256)
        state.current[kind] = retained
    state.invalidations.extend(item.invalidation_sha256 for item in invalidations)


def _current_records(state: _State, kind: str) -> tuple[SessionRecord, ...]:
    return tuple(state.current[kind][key] for key in sorted(state.current[kind]))


def _view_value(state: _State) -> dict[str, object]:
    return {
        "analysis_artifact_sha256s": list(state.analysis),
        "artifact_sha256s": sorted(state.artifact_links),
        "attempts": [_record_value(item) for item in _current_records(state, "attempt")],
        "context_sha256": state.context,
        "definitions": [_record_value(item) for item in _current_records(state, "definition")],
        "invalidation_sha256s": list(state.invalidations),
        "lemmas": [_record_value(item) for item in _current_records(state, "lemma")],
        "obligations": [_record_value(item) for item in _current_records(state, "obligation")],
        "retired_record_sha256s": list(state.retired),
        "revision": state.revision,
        "session_id": state.session_id,
        "stale_record_sha256s": list(state.stale),
    }


def _view_sha256(state: _State) -> str:
    return _digest(_canonical_bytes(_view_value(state)))


def _validate_artifact_graph(state: _State) -> None:
    for identity, link in state.artifact_links.items():
        if identity in link.depends_on_sha256s:
            _fail("dependency", "artifact_links", "artifact dependency self-cycle")
        for dependency in link.depends_on_sha256s:
            if dependency not in state.artifact_links:
                _fail("reference", "artifact_links", "artifact dependency is missing")
    marks: dict[str, int] = {}

    def visit(identity: str, depth: int) -> None:
        if depth > MAX_JSON_NESTING:
            raise _Exhausted("artifact dependency depth exceeds budget")
        mark = marks.get(identity, 0)
        if mark == 1:
            _fail("dependency", "artifact_links", "artifact dependency cycle")
        if mark == 2:
            return
        marks[identity] = 1
        for dependency in state.artifact_links[identity].depends_on_sha256s:
            visit(dependency, depth + 1)
        marks[identity] = 2

    edges = sum(len(item.depends_on_sha256s) for item in state.artifact_links.values())
    if edges > MAX_DEPENDENCY_EDGES:
        raise _Exhausted("artifact dependency edges exceed budget")
    for identity in sorted(state.artifact_links):
        visit(identity, 0)


def _validate_context_selection(
    state: _State, context: str, analysis: tuple[str, ...]
) -> None:
    context_link = _require_artifact(state, context, "command.context_sha256", "context")
    if context_link.context_sha256 not in {None, context}:
        _fail("reference", "command.context_sha256", "context link binds another context")
    for identity in analysis:
        link = _require_artifact(state, identity, "command.analysis_artifact_sha256s")
        if link.role not in {"problem_analysis", "unsupported_explanation"}:
            _fail("reference", "command.analysis_artifact_sha256s", "invalid analysis role")
        if link.context_sha256 not in {None, context}:
            _fail("reference", "command.analysis_artifact_sha256s", "analysis binds another context")


def _validate_new_links_context(
    links: tuple[SessionArtifactLink, ...], allowed_context: str
) -> None:
    for link in links:
        if link.context_sha256 not in {None, allowed_context}:
            _fail("reference", "command.introduced_artifacts", "new artifact binds stale context")


def _apply_command(
    state: _State,
    command: dict[str, object],
    artifacts: Mapping[str, bytes],
    command_bytes: bytes,
) -> tuple[tuple[SessionInvalidation, ...], str | None]:
    kind = command["kind"]
    session_id = command["session_id"]
    expected_head = command["expected_head"]
    command_id = command["command_id"]
    command_sha = command["sha256"]
    assert type(kind) is str and type(session_id) is str
    assert type(command_id) is str and type(command_sha) is str
    if state.session_id is None:
        if kind != "create_session":
            _fail("session", "command.kind", "first command must create the session")
    else:
        if session_id != state.session_id:
            raise _Conflict("SESSION_MISMATCH", "command names another session")
        previous = state.command_ids.get(command_id)
        if previous is not None:
            if previous == command_sha and state.last_command_bytes == command_bytes:
                return (), "retry"
            raise _Conflict("COMMAND_ID_REUSED", "command ID was already used")
        if expected_head != state.head:
            raise _Conflict("HEAD_MISMATCH", "expected head is not current")
    links = command["links"]
    assert type(links) is tuple
    _install_links(state, links, artifacts, replay=False)
    _validate_artifact_graph(state)
    invalidations: tuple[SessionInvalidation, ...] = ()
    if kind == "create_session":
        if state.session_id is not None or state.event_sha256s:
            raise _Conflict("SESSION_EXISTS", "session already has history")
        context = command["context"]
        analysis = command["analysis"]
        assert type(context) is str and type(analysis) is tuple
        _validate_new_links_context(links, context)
        _validate_context_selection(state, context, analysis)
        state.session_id = session_id
        state.context = context
        state.analysis = analysis
        state.revision = 0
    elif kind == "replace_context":
        context = command["context"]
        analysis = command["analysis"]
        assert type(context) is str and type(analysis) is tuple
        assert state.context is not None
        if context == state.context:
            raise _Conflict("CONTEXT_UNCHANGED", "replacement context equals current context")
        _validate_new_links_context(links, context)
        _validate_context_selection(state, context, analysis)
        seeds = [
            (identity, None, "context_revised")
            for identity, (_, record) in _all_current(state).items()
            if _record_context(record) != context
        ]
        invalidations = _dependency_closure(
            state, seeds, old_context=state.context, new_context=context
        )
        _remove_invalidated(state, invalidations)
        state.context = context
        state.analysis = analysis
        state.revision += 1
    elif kind in _PUT_KIND:
        assert state.context is not None
        _validate_new_links_context(links, state.context)
        record = command["record"]
        record_kind = command["record_kind"]
        assert type(record_kind) is str
        assert type(record) in {SessionDefinition, SessionLemma, SessionAttempt, SessionObligation}
        _validate_record_references(state, record, record_kind)
        existing = state.current[record_kind].get(record.record_id)
        if existing is not None:
            invalidations = _dependency_closure(
                state,
                [(existing.record_sha256, existing.record_sha256, "superseded")],
                old_context=state.context,
                new_context=state.context,
            )
            _remove_invalidated(state, invalidations)
        # Dependencies are checked before removal; replacing a dependency cannot
        # make the new record depend on the superseded generation.
        if any(item not in _all_current(state) for item in record.depends_on_record_sha256s):
            _fail("dependency", "command.record", "replacement invalidated a new dependency")
        state.current[record_kind][record.record_id] = record
        state.revision += 1
    else:
        assert state.context is not None
        target_kind = command["target_kind"]
        target_id = command["target_id"]
        assert type(target_kind) is str and type(target_id) is str
        existing = state.current[target_kind].get(target_id)
        if existing is None:
            raise _Conflict("RECORD_NOT_CURRENT", "retirement target is not current")
        invalidations = _dependency_closure(
            state,
            [(existing.record_sha256, existing.record_sha256, "retired")],
            old_context=state.context,
            new_context=state.context,
        )
        _remove_invalidated(state, invalidations)
        state.revision += 1
    state.command_ids[command_id] = command_sha
    state.last_command_bytes = command_bytes
    if sum(len(item.depends_on_record_sha256s) for _, item in _all_current(state).values()) > MAX_DEPENDENCY_EDGES:
        raise _Exhausted("record dependency edges exceed budget")
    if len(_all_current(state)) + len(state.stale) + len(state.retired) > MAX_RECORDS:
        raise _Exhausted("record count exceeds budget")
    return invalidations, None


_EVENT_FIELDS = {
    "command",
    "command_sha256",
    "event_sha256",
    "introduced_artifact_sha256s",
    "invalidations",
    "mathematical_authority",
    "parent_event_sha256",
    "revision",
    "schema",
    "session_id",
    "view_sha256",
}


def _event_from_command(
    state: _State,
    command: dict[str, object],
    command_bytes: bytes,
    artifacts: Mapping[str, bytes],
) -> tuple[bytes | None, str | None]:
    parent = state.head
    before_revision = state.revision
    invalidations, retry = _apply_command(state, command, artifacts, command_bytes)
    if retry == "retry":
        return None, "retry"
    if state.revision != before_revision + 1:
        if not (before_revision == -1 and state.revision == 0):
            raise AssertionError("internal revision step drift")
    view_sha = _view_sha256(state)
    links = command["links"]
    assert type(links) is tuple
    value: dict[str, object] = {
        "command": command["value"],
        "command_sha256": command["sha256"],
        "event_sha256": None,
        "introduced_artifact_sha256s": [item.sha256 for item in links],
        "invalidations": [_invalidation_value(item) for item in invalidations],
        "mathematical_authority": False,
        "parent_event_sha256": parent,
        "revision": state.revision,
        "schema": EVENT_SCHEMA,
        "session_id": state.session_id,
        "view_sha256": view_sha,
    }
    value["event_sha256"] = _self_digest(value, "event_sha256")
    event_bytes = _canonical_bytes(value)
    state.head = value["event_sha256"]  # type: ignore[assignment]
    state.event_sha256s.append(state.head)
    return event_bytes, None


def _parse_event_value(value: object, path: str) -> dict[str, object]:
    if type(value) is not dict:
        _fail("schema", path, "event must be an exact object")
    _closed(value, _EVENT_FIELDS, path)
    if value["schema"] != EVENT_SCHEMA:
        _fail("schema", f"{path}.schema", "event schema drift")
    session_id = _string(value["session_id"], f"{path}.session_id", pattern=_ID)
    revision = _integer(value["revision"], f"{path}.revision")
    parent = _optional_digest(value["parent_event_sha256"], f"{path}.parent_event_sha256")
    command = _parse_command_value(value["command"], f"{path}.command")
    command_sha = _digest_value(value["command_sha256"], f"{path}.command_sha256")
    if command_sha != command["sha256"]:
        _fail("identity", f"{path}.command_sha256", "event command digest drift")
    introduced = _tuple_strings(
        value["introduced_artifact_sha256s"],
        f"{path}.introduced_artifact_sha256s",
        maximum=4096,
        pattern=_DIGEST,
    )
    raw_invalidations = value["invalidations"]
    if type(raw_invalidations) is not list or len(raw_invalidations) > MAX_INVALIDATIONS:
        _fail("schema", f"{path}.invalidations", "expected bounded invalidation array")
    invalidations = tuple(
        _parse_invalidation(item, f"{path}.invalidations[{index}]")
        for index, item in enumerate(raw_invalidations)
    )
    if tuple(item.ordinal for item in invalidations) != tuple(range(len(invalidations))):
        _fail("canonical", f"{path}.invalidations", "invalidation ordinals are not contiguous")
    view_sha = _digest_value(value["view_sha256"], f"{path}.view_sha256")
    event_sha = _digest_value(value["event_sha256"], f"{path}.event_sha256")
    if _self_digest(value, "event_sha256") != event_sha:
        _fail("identity", f"{path}.event_sha256", "event identity drift")
    _false(value["mathematical_authority"], f"{path}.mathematical_authority")
    return {
        "value": value,
        "session_id": session_id,
        "revision": revision,
        "parent": parent,
        "command": command,
        "introduced": introduced,
        "invalidations": invalidations,
        "view_sha256": view_sha,
        "sha256": event_sha,
    }


def _revision_value(revision: SessionRevision) -> dict[str, object]:
    return {
        "analysis_artifact_sha256s": list(revision.analysis_artifact_sha256s),
        "artifact_sha256s": list(revision.artifact_sha256s),
        "attempts": [_attempt_value(item) for item in revision.attempts],
        "context_sha256": revision.context_sha256,
        "definitions": [_definition_value(item) for item in revision.definitions],
        "event_sha256s": list(revision.event_sha256s),
        "head_event_sha256": revision.head_event_sha256,
        "invalidation_sha256s": list(revision.invalidation_sha256s),
        "lemmas": [_lemma_value(item) for item in revision.lemmas],
        "mathematical_authority": revision.mathematical_authority,
        "obligations": [_obligation_value(item) for item in revision.obligations],
        "parent_event_sha256": revision.parent_event_sha256,
        "retired_record_sha256s": list(revision.retired_record_sha256s),
        "revision": revision.revision,
        "revision_sha256": revision.revision_sha256,
        "schema": revision.schema,
        "session_id": revision.session_id,
        "stale_record_sha256s": list(revision.stale_record_sha256s),
        "view_sha256": revision.view_sha256,
    }


def _build_revision(state: _State) -> SessionRevision:
    assert state.session_id is not None and state.head is not None and state.context is not None
    parent = None if len(state.event_sha256s) == 1 else state.event_sha256s[-2]
    value: dict[str, object] = {
        "analysis_artifact_sha256s": list(state.analysis),
        "artifact_sha256s": sorted(state.artifact_links),
        "attempts": [_record_value(item) for item in _current_records(state, "attempt")],
        "context_sha256": state.context,
        "definitions": [_record_value(item) for item in _current_records(state, "definition")],
        "event_sha256s": list(state.event_sha256s),
        "head_event_sha256": state.head,
        "invalidation_sha256s": list(state.invalidations),
        "lemmas": [_record_value(item) for item in _current_records(state, "lemma")],
        "mathematical_authority": False,
        "obligations": [_record_value(item) for item in _current_records(state, "obligation")],
        "parent_event_sha256": parent,
        "retired_record_sha256s": list(state.retired),
        "revision": state.revision,
        "revision_sha256": None,
        "schema": REVISION_SCHEMA,
        "session_id": state.session_id,
        "stale_record_sha256s": list(state.stale),
        "view_sha256": _view_sha256(state),
    }
    value["revision_sha256"] = _self_digest(value, "revision_sha256")
    return _parse_revision(value, "revision")


def _parse_record_array(
    value: object, path: str, expected_kind: str, maximum: int
) -> tuple[SessionRecord, ...]:
    if type(value) is not list or len(value) > maximum:
        _fail("schema", path, "expected bounded record array")
    records: list[SessionRecord] = []
    ids: list[str] = []
    for index, item in enumerate(value):
        kind, record = _parse_record(item, f"{path}[{index}]")
        if kind != expected_kind:
            _fail("schema", f"{path}[{index}]", "record kind differs from registry")
        records.append(record)
        ids.append(record.record_id)
    if ids != sorted(set(ids)):
        _fail("canonical", path, "record registry must sort by unique stable ID")
    return tuple(records)


def _parse_revision(value: object, path: str) -> SessionRevision:
    if type(value) is not dict:
        _fail("schema", path, "revision must be an exact object")
    expected = {
        "analysis_artifact_sha256s", "artifact_sha256s", "attempts",
        "context_sha256", "definitions", "event_sha256s", "head_event_sha256",
        "invalidation_sha256s", "lemmas", "mathematical_authority", "obligations",
        "parent_event_sha256", "retired_record_sha256s", "revision",
        "revision_sha256", "schema", "session_id", "stale_record_sha256s",
        "view_sha256",
    }
    _closed(value, expected, path)
    if value["schema"] != REVISION_SCHEMA:
        _fail("schema", f"{path}.schema", "revision schema drift")
    session_id = _string(value["session_id"], f"{path}.session_id", pattern=_ID)
    number = _integer(value["revision"], f"{path}.revision")
    parent = _optional_digest(value["parent_event_sha256"], f"{path}.parent_event_sha256")
    head = _digest_value(value["head_event_sha256"], f"{path}.head_event_sha256")
    context = _digest_value(value["context_sha256"], f"{path}.context_sha256")
    analysis = _tuple_strings(
        value["analysis_artifact_sha256s"], f"{path}.analysis_artifact_sha256s",
        maximum=4096, pattern=_DIGEST,
    )
    definitions = _parse_record_array(value["definitions"], f"{path}.definitions", "definition", 100_000)
    lemmas = _parse_record_array(value["lemmas"], f"{path}.lemmas", "lemma", 100_000)
    attempts = _parse_record_array(value["attempts"], f"{path}.attempts", "attempt", 1_000_000)
    obligations = _parse_record_array(value["obligations"], f"{path}.obligations", "obligation", 1_000_000)
    stale = _tuple_strings(
        value["stale_record_sha256s"], f"{path}.stale_record_sha256s",
        maximum=MAX_INVALIDATIONS, pattern=_DIGEST, sorted_unique=False,
    )
    retired = _tuple_strings(
        value["retired_record_sha256s"], f"{path}.retired_record_sha256s",
        maximum=MAX_INVALIDATIONS, pattern=_DIGEST, sorted_unique=False,
    )
    if len(set(stale)) != len(stale) or len(set(retired)) != len(retired):
        _fail("canonical", path, "stale and retired histories must be unique")
    invalidations = _tuple_strings(
        value["invalidation_sha256s"], f"{path}.invalidation_sha256s",
        maximum=MAX_INVALIDATIONS, pattern=_DIGEST, sorted_unique=False,
    )
    if len(set(invalidations)) != len(invalidations):
        _fail("canonical", path, "invalidation history must be unique")
    event_sha256s = _tuple_strings(
        value["event_sha256s"], f"{path}.event_sha256s",
        maximum=MAX_EVENTS, pattern=_DIGEST, sorted_unique=False,
    )
    if len(set(event_sha256s)) != len(event_sha256s):
        _fail("canonical", path, "event history must be unique")
    artifacts = _tuple_strings(
        value["artifact_sha256s"], f"{path}.artifact_sha256s",
        maximum=MAX_ARTIFACTS, pattern=_DIGEST,
    )
    if not event_sha256s or event_sha256s[-1] != head or len(event_sha256s) != number + 1:
        _fail("revision", path, "event inventory does not match revision and head")
    expected_parent = None if number == 0 else event_sha256s[-2]
    if parent != expected_parent:
        _fail("revision", f"{path}.parent_event_sha256", "parent event drift")
    current_records = (*definitions, *lemmas, *attempts, *obligations)
    current_shas = {item.record_sha256 for item in current_records}
    if len(current_shas) != len(current_records):
        _fail("reference", path, "duplicate current record identity")
    if current_shas & (set(stale) | set(retired)) or set(stale) & set(retired):
        _fail("lifecycle", path, "current, stale, and retired record sets overlap")
    view_sha = _digest_value(value["view_sha256"], f"{path}.view_sha256")
    temp = _empty_state()
    temp.session_id = session_id
    temp.revision = number
    temp.context = context
    temp.analysis = analysis
    temp.current = {
        "definition": {item.record_id: item for item in definitions},
        "lemma": {item.record_id: item for item in lemmas},
        "attempt": {item.record_id: item for item in attempts},
        "obligation": {item.record_id: item for item in obligations},
    }
    temp.stale = list(stale)
    temp.retired = list(retired)
    temp.invalidations = list(invalidations)
    temp.artifact_links = {identity: None for identity in artifacts}  # type: ignore[dict-item]
    if _view_sha256(temp) != view_sha:
        _fail("identity", f"{path}.view_sha256", "revision view identity drift")
    identity = _digest_value(value["revision_sha256"], f"{path}.revision_sha256")
    if _self_digest(value, "revision_sha256") != identity:
        _fail("identity", f"{path}.revision_sha256", "revision identity drift")
    result = _make(
        SessionRevision,
        schema=REVISION_SCHEMA,
        session_id=session_id,
        revision=number,
        parent_event_sha256=parent,
        head_event_sha256=head,
        context_sha256=context,
        analysis_artifact_sha256s=analysis,
        definitions=definitions,
        lemmas=lemmas,
        attempts=attempts,
        obligations=obligations,
        stale_record_sha256s=stale,
        retired_record_sha256s=retired,
        invalidation_sha256s=invalidations,
        event_sha256s=event_sha256s,
        artifact_sha256s=artifacts,
        view_sha256=view_sha,
        revision_sha256=identity,
        mathematical_authority=_false(
            value["mathematical_authority"], f"{path}.mathematical_authority"
        ),
    )
    if _revision_value(result) != value:
        _fail("canonical", path, "revision projection drift")
    return result


def _replay_history(
    events: tuple[bytes, ...], artifacts: Mapping[str, bytes]
) -> _State:
    if type(events) is not tuple:
        _fail("type", "events", "events must be an exact tuple")
    if len(events) > MAX_EVENTS:
        raise _Exhausted("event count exceeds budget")
    total = 0
    state = _empty_state()
    for index, event_bytes in enumerate(events):
        if type(event_bytes) is not bytes:
            _fail("type", f"events[{index}]", "event must be exact bytes")
        total += len(event_bytes)
        if total > MAX_AGGREGATE_EVENT_BYTES:
            raise _Exhausted("aggregate event bytes exceed budget")
        value = _parse_json(event_bytes, f"events[{index}]", MAX_COMMAND_BYTES * 4)
        parsed = _parse_event_value(value, f"events[{index}]")
        if parsed["revision"] != index:
            _fail("revision", f"events[{index}].revision", "event revision is not contiguous")
        if parsed["parent"] != state.head:
            _fail("revision", f"events[{index}].parent_event_sha256", "event parent drift")
        command = parsed["command"]
        assert type(command) is dict
        command_bytes = _canonical_bytes(command["value"])
        rebuilt, retry = _event_from_command(state, command, command_bytes, artifacts)
        if retry is not None or rebuilt != event_bytes:
            _fail("result", f"events[{index}]", "event differs from deterministic replay")
        if parsed["sha256"] != state.head or parsed["view_sha256"] != _view_sha256(state):
            _fail("identity", f"events[{index}]", "event replay identity drift")
    return state


def _result_value(result: ProblemSessionResult) -> dict[str, object]:
    return {
        "artifact_count": result.artifact_count,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "diagnostic": result.diagnostic,
        "event_count": result.event_count,
        "head_sha256": result.head_sha256,
        "mathematical_authority": result.mathematical_authority,
        "reason_code": result.reason_code,
        "result_sha256": result.result_sha256,
        "revision": result.revision,
        "revision_value": (
            None if result.revision_value is None else _revision_value(result.revision_value)
        ),
        "schema": result.schema,
        "session_id": result.session_id,
        "stale_record_count": result.stale_record_count,
        "status": result.status,
        "view_sha256": result.view_sha256,
    }


def _success_result(
    status: str,
    reason_code: str,
    state: _State,
    events: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> ProblemSessionResult:
    revision = _build_revision(state)
    values: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "contract_id": PROBLEM_SESSION_CONTRACT_ID,
        "contract_sha256": PROBLEM_SESSION_CONTRACT_SHA256,
        "status": status,
        "reason_code": reason_code,
        "diagnostic": "",
        "session_id": revision.session_id,
        "revision": revision.revision,
        "head_sha256": revision.head_event_sha256,
        "view_sha256": revision.view_sha256,
        "event_count": len(events),
        "artifact_count": len(artifacts),
        "stale_record_count": len(revision.stale_record_sha256s),
        "revision_value": revision,
        "result_sha256": None,
        "mathematical_authority": False,
        "events": events,
        "artifacts": artifacts,
    }
    projected = {
        key: (None if key == "revision_value" else value)
        for key, value in values.items()
        if key not in {"events", "artifacts"}
    }
    projected["revision_value"] = _revision_value(revision)
    values["result_sha256"] = _self_digest(projected, "result_sha256")
    return _make(ProblemSessionResult, **values)


def _failure_result(status: str, reason_code: str, diagnostic: str) -> ProblemSessionResult:
    diagnostic = unicodedata.normalize("NFC", diagnostic.replace("\x00", ""))
    if len(diagnostic) > MAX_DIAGNOSTIC_CODEPOINTS:
        diagnostic = diagnostic[:MAX_DIAGNOSTIC_CODEPOINTS]
    return _make(
        ProblemSessionResult,
        schema=RESULT_SCHEMA,
        contract_id=PROBLEM_SESSION_CONTRACT_ID,
        contract_sha256=PROBLEM_SESSION_CONTRACT_SHA256,
        status=status,
        reason_code=reason_code,
        diagnostic=diagnostic,
        session_id=None,
        revision=None,
        head_sha256=None,
        view_sha256=None,
        event_count=0,
        artifact_count=0,
        stale_record_count=0,
        revision_value=None,
        result_sha256=None,
        mathematical_authority=False,
        events=None,
        artifacts=None,
    )


def transition_problem_session(
    command: bytes | None,
    events: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> ProblemSessionResult:
    """Replay exact history and optionally derive one non-authoritative revision."""
    try:
        artifact_map = _artifact_map(artifacts)
        state = _replay_history(events, artifact_map)
        if command is None:
            if not events:
                raise _Invalid("EMPTY_HISTORY", "replay requires a committed root event")
            if set(state.artifact_links) != set(artifact_map):
                raise _Invalid("ARTIFACT_INVENTORY", "artifact inventory differs from history")
            return _success_result("unchanged", "REPLAYED", state, events, artifacts)
        if type(command) is not bytes:
            raise _Invalid("COMMAND_TYPE", "command must be exact bytes or None")
        command_value = _parse_json(command, "command", MAX_COMMAND_BYTES)
        parsed_command = _parse_command_value(command_value, "command")
        event_bytes, retry = _event_from_command(state, parsed_command, command, artifact_map)
        if retry == "retry":
            if set(state.artifact_links) != set(artifact_map):
                raise _Invalid("ARTIFACT_INVENTORY", "retry artifact inventory differs")
            return _success_result("unchanged", "IDEMPOTENT_RETRY", state, events, artifacts)
        assert event_bytes is not None
        if set(state.artifact_links) != set(artifact_map):
            raise _Invalid("ARTIFACT_INVENTORY", "artifact inventory is missing or surplus")
        updated_events = (*events, event_bytes)
        return _success_result("updated", "UPDATED", state, updated_events, artifacts)
    except _Conflict as exc:
        return _failure_result("conflict", exc.reason_code, exc.detail)
    except _Exhausted as exc:
        return _failure_result("exhausted", "BUDGET_EXHAUSTED", str(exc))
    except _Invalid as exc:
        return _failure_result("invalid", exc.reason_code, exc.detail)
    except ProblemSessionValidationError as exc:
        reason = f"INVALID_{exc.kind.upper()}"
        if not _CODE.fullmatch(reason):
            reason = "INVALID_INPUT"
        return _failure_result("invalid", reason, f"{exc.path}: {exc.detail}")


_RESULT_FIELDS = {
    "artifact_count", "contract_id", "contract_sha256", "diagnostic",
    "event_count", "head_sha256", "mathematical_authority", "reason_code",
    "result_sha256", "revision", "revision_value", "schema", "session_id",
    "stale_record_count", "status", "view_sha256",
}


def _parse_result_value(
    value: object,
    path: str,
    events: tuple[bytes, ...] | None,
    artifacts: tuple[bytes, ...] | None,
) -> ProblemSessionResult:
    if type(value) is not dict:
        _fail("schema", path, "result must be an exact object")
    _closed(value, _RESULT_FIELDS, path)
    if value["schema"] != RESULT_SCHEMA:
        _fail("schema", f"{path}.schema", "result schema drift")
    if value["contract_id"] != PROBLEM_SESSION_CONTRACT_ID:
        _fail("identity", f"{path}.contract_id", "contract ID drift")
    if value["contract_sha256"] != PROBLEM_SESSION_CONTRACT_SHA256:
        _fail("identity", f"{path}.contract_sha256", "contract hash drift")
    status = _string(value["status"], f"{path}.status")
    if status not in {"updated", "unchanged", "conflict", "invalid", "exhausted"}:
        _fail("schema", f"{path}.status", "unknown result status")
    reason = _string(value["reason_code"], f"{path}.reason_code", pattern=_CODE)
    diagnostic = value["diagnostic"]
    if type(diagnostic) is not str or len(diagnostic) > MAX_DIAGNOSTIC_CODEPOINTS:
        _fail("budget", f"{path}.diagnostic", "invalid diagnostic")
    _string(diagnostic or "x", f"{path}.diagnostic")
    authority = _false(value["mathematical_authority"], f"{path}.mathematical_authority")
    if status in {"updated", "unchanged"}:
        session_id = _string(value["session_id"], f"{path}.session_id", pattern=_ID)
        revision_number = _integer(value["revision"], f"{path}.revision")
        head = _digest_value(value["head_sha256"], f"{path}.head_sha256")
        view = _digest_value(value["view_sha256"], f"{path}.view_sha256")
        event_count = _integer(value["event_count"], f"{path}.event_count", MAX_EVENTS)
        artifact_count = _integer(
            value["artifact_count"], f"{path}.artifact_count", MAX_ARTIFACTS
        )
        stale_count = _integer(
            value["stale_record_count"], f"{path}.stale_record_count", MAX_INVALIDATIONS
        )
        revision = _parse_revision(value["revision_value"], f"{path}.revision_value")
        result_sha = _digest_value(value["result_sha256"], f"{path}.result_sha256")
        if _self_digest(value, "result_sha256") != result_sha:
            _fail("identity", f"{path}.result_sha256", "result identity drift")
        if (
            session_id != revision.session_id
            or revision_number != revision.revision
            or head != revision.head_event_sha256
            or view != revision.view_sha256
            or stale_count != len(revision.stale_record_sha256s)
        ):
            _fail("result", path, "result summary differs from revision")
        if events is None or artifacts is None:
            _fail("result", path, "successful result requires exact replay inputs")
        if event_count != len(events) or artifact_count != len(artifacts):
            _fail("result", path, "result counts differ from replay inputs")
    else:
        if any(value[key] is not None for key in (
            "session_id", "revision", "head_sha256", "view_sha256",
            "revision_value", "result_sha256",
        )):
            _fail("result", path, "failure result contains partial state")
        if any(value[key] != 0 for key in ("event_count", "artifact_count", "stale_record_count")):
            _fail("result", path, "failure result contains partial counts")
        session_id = None
        revision_number = None
        head = None
        view = None
        event_count = 0
        artifact_count = 0
        stale_count = 0
        revision = None
        result_sha = None
        if events is not None or artifacts is not None:
            _fail("result", path, "failure result must not retain replay inputs")
    return _make(
        ProblemSessionResult,
        schema=RESULT_SCHEMA,
        contract_id=PROBLEM_SESSION_CONTRACT_ID,
        contract_sha256=PROBLEM_SESSION_CONTRACT_SHA256,
        status=status,
        reason_code=reason,
        diagnostic=diagnostic,
        session_id=session_id,
        revision=revision_number,
        head_sha256=head,
        view_sha256=view,
        event_count=event_count,
        artifact_count=artifact_count,
        stale_record_count=stale_count,
        revision_value=revision,
        result_sha256=result_sha,
        mathematical_authority=authority,
        events=events,
        artifacts=artifacts,
    )


def validate_problem_session_result(result: object) -> None:
    """Recompute a closed result and its complete retained successful history."""
    if type(result) is not ProblemSessionResult:
        _fail("type", "result", "result must be an exact ProblemSessionResult")
    parsed = _parse_result_value(
        _result_value(result), "result", result.events, result.artifacts
    )
    if parsed != result:
        _fail("result", "result", "in-memory result projection drift")
    if result.status in {"updated", "unchanged"}:
        assert result.events is not None and result.artifacts is not None
        replayed = transition_problem_session(None, result.events, result.artifacts)
        if replayed.status != "unchanged":
            _fail("result", "result", "retained inputs fail complete replay")
        for name in (
            "session_id", "revision", "head_sha256", "view_sha256", "event_count",
            "artifact_count", "stale_record_count", "revision_value",
        ):
            if getattr(replayed, name) != getattr(result, name):
                _fail("result", f"result.{name}", "retained replay differs")


def problem_session_result_to_bytes(result: ProblemSessionResult) -> bytes:
    """Serialize one strictly replayed session result."""
    validate_problem_session_result(result)
    return _canonical_bytes(_result_value(result))


def problem_session_result_sha256(result: ProblemSessionResult) -> str:
    """Return the full digest of one canonical validated result envelope."""
    return _digest(problem_session_result_to_bytes(result))


def parse_problem_session_result(
    data: bytes,
    events: tuple[bytes, ...] | None = None,
    artifacts: tuple[bytes, ...] | None = None,
) -> ProblemSessionResult:
    """Parse result bytes only with exact retained inputs for successful state."""
    value = _parse_json(data, "result", MAX_AGGREGATE_EVENT_BYTES)
    result = _parse_result_value(value, "result", events, artifacts)
    validate_problem_session_result(result)
    return result


__all__ = [
    "ARTIFACT_LINK_SCHEMA",
    "ATTEMPT_SCHEMA",
    "COMMAND_SCHEMA",
    "DEFINITION_SCHEMA",
    "EVENT_SCHEMA",
    "INVALIDATION_SCHEMA",
    "LEMMA_SCHEMA",
    "OBLIGATION_SCHEMA",
    "PROBLEM_SESSION_CONTRACT_ID",
    "PROBLEM_SESSION_CONTRACT_SHA256",
    "ProblemSessionResult",
    "ProblemSessionValidationError",
    "REVISION_SCHEMA",
    "RESULT_SCHEMA",
    "SCHEMA_SHA256S",
    "SessionArtifactLink",
    "SessionAttempt",
    "SessionDefinition",
    "SessionInvalidation",
    "SessionLemma",
    "SessionObligation",
    "SessionRevision",
    "make_problem_session_command",
    "make_session_artifact_link",
    "make_session_attempt",
    "make_session_definition",
    "make_session_lemma",
    "make_session_obligation",
    "parse_problem_session_command",
    "parse_problem_session_result",
    "problem_session_result_sha256",
    "problem_session_result_to_bytes",
    "session_component_to_bytes",
    "transition_problem_session",
    "validate_problem_session_result",
]
