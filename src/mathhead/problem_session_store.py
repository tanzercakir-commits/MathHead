"""Atomic, non-authoritative filesystem adapter for problem sessions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, NoReturn
import unicodedata

from mathhead.problem_sessions import (
    ProblemSessionResult,
    REVISION_SCHEMA,
    parse_problem_session_command,
    session_component_to_bytes,
    transition_problem_session,
)


PROBLEM_SESSION_STORE_CONTRACT_ID = "MH-C-PROBLEM-SESSION-STORE-001"
PROBLEM_SESSION_STORE_CONTRACT_SHA256 = (
    "7637e5178767b661e6e361305090a9f7fb50d50bd5d316035283d73f970a9b82"
)
STORE_HEAD_SCHEMA = "mathhead.problem-session-store-head.v1"
STORE_HEAD_SCHEMA_SHA256 = (
    "a5bed15dda9e8c229687f1a89ba1ca9770e17d72314d16b5de63417472f3f683"
)

MAX_HEAD_BYTES = 67_108_864
MAX_OBJECT_BYTES = 67_108_864
MAX_AGGREGATE_BYTES = 1_073_741_824
MAX_EVENTS = 100_000
MAX_ARTIFACTS = 1_000_000
MAX_PATH_COMPONENTS = 256
MAX_TEMPORARIES = 4096
MAX_JSON_NESTING = 128
MAX_JSON_NODES = 8_000_000
MAX_STRING_CODEPOINTS = 1_048_576
MAX_INTEGER = 9_007_199_254_740_991
_WINDOWS = os.name == "nt"

_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_HEAD_FIELDS = {
    "artifact_sha256s",
    "event_sha256s",
    "head_event_sha256",
    "head_sha256",
    "mathematical_authority",
    "revision",
    "revision_sha256",
    "schema",
    "session_id",
    "session_key_sha256",
    "store_contract_id",
    "store_contract_sha256",
}


class ProblemSessionStoreError(RuntimeError):
    """A classified refusal by the problem-session filesystem adapter."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _DuplicateKey(ValueError):
    pass


def _fail(kind: str, detail: str) -> NoReturn:
    raise ProblemSessionStoreError(kind, detail)


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
        _fail("head", f"canonical head encoding failed: {type(exc).__name__}")
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


def _walk(value: object, depth: int, nodes: list[int]) -> None:
    if depth > MAX_JSON_NESTING:
        _fail("budget", "head JSON nesting exceeds budget")
    nodes[0] += 1
    if nodes[0] > MAX_JSON_NODES:
        _fail("budget", "head JSON nodes exceed budget")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > MAX_INTEGER:
            _fail("budget", "head integer exceeds exact range")
        return
    if type(value) is str:
        if len(value) > MAX_STRING_CODEPOINTS:
            _fail("budget", "head string exceeds budget")
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            _fail("head", "head strings must be NUL-free NFC")
        return
    if type(value) is list:
        for item in value:
            _walk(item, depth + 1, nodes)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail("head", "head keys must be exact strings")
            _walk(key, depth + 1, nodes)
            _walk(item, depth + 1, nodes)
        return
    _fail("head", "head contains a forbidden value type")


def _parse_json(data: bytes) -> dict[str, Any]:
    if type(data) is not bytes or not data or len(data) > MAX_HEAD_BYTES:
        _fail("budget", "head bytes are outside bounds")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=_reject_float,
            parse_constant=_reject_float,
        )
    except _DuplicateKey as exc:
        _fail("head", f"duplicate head key {exc.args[0]!r}")
    except (UnicodeError, ValueError, RecursionError) as exc:
        _fail("head", f"invalid head JSON: {type(exc).__name__}")
    if type(value) is not dict:
        _fail("head", "head root must be an object")
    _walk(value, 0, [0])
    if _canonical_bytes(value) != data:
        _fail("head", "head bytes are not canonical")
    return value


def _valid_id(value: object) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        _fail("head", "session ID is invalid")
    return value


def _valid_digest(value: object) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        _fail("head", "expected one lowercase full SHA-256")
    return value


def _digest_list(value: object, maximum: int, *, ordered: bool) -> tuple[str, ...]:
    if type(value) is not list or len(value) > maximum:
        _fail("head", "head inventory is not a bounded array")
    result = tuple(_valid_digest(item) for item in value)
    if len(set(result)) != len(result):
        _fail("head", "head inventory contains duplicate identities")
    if not ordered and result != tuple(sorted(result)):
        _fail("head", "head inventory is not sorted")
    return result


def _head_preimage(value: dict[str, object]) -> bytes:
    preimage = dict(value)
    preimage["head_sha256"] = None
    return _canonical_bytes(preimage)


def _parse_head(data: bytes, expected_session_id: str) -> dict[str, object]:
    value = _parse_json(data)
    if set(value) != _HEAD_FIELDS:
        _fail("head", "head field set drift")
    if value["schema"] != STORE_HEAD_SCHEMA:
        _fail("head", "store-head schema drift")
    if value["store_contract_id"] != PROBLEM_SESSION_STORE_CONTRACT_ID:
        _fail("head", "store contract ID drift")
    if value["store_contract_sha256"] != PROBLEM_SESSION_STORE_CONTRACT_SHA256:
        _fail("head", "store contract hash drift")
    session_id = _valid_id(value["session_id"])
    if session_id != expected_session_id:
        _fail("head", "head names another session")
    session_key = _valid_digest(value["session_key_sha256"])
    if session_key != _digest(session_id.encode("utf-8")):
        _fail("head", "session key drift")
    revision = value["revision"]
    if type(revision) is not int or revision < 0 or revision > MAX_INTEGER:
        _fail("head", "revision is invalid")
    head_event = _valid_digest(value["head_event_sha256"])
    revision_sha = _valid_digest(value["revision_sha256"])
    event_objects = _digest_list(value["event_sha256s"], MAX_EVENTS, ordered=True)
    artifacts = _digest_list(value["artifact_sha256s"], MAX_ARTIFACTS, ordered=False)
    if len(event_objects) != revision + 1:
        _fail("head", "event inventory does not match revision")
    head_sha = _valid_digest(value["head_sha256"])
    if _digest(_head_preimage(value)) != head_sha:
        _fail("head", "store-head identity drift")
    if value["mathematical_authority"] is not False:
        _fail("head", "store head cannot carry mathematical authority")
    return {
        "value": value,
        "session_id": session_id,
        "session_key": session_key,
        "revision": revision,
        "head_event": head_event,
        "revision_sha": revision_sha,
        "event_objects": event_objects,
        "artifacts": artifacts,
        "head_sha": head_sha,
    }


def _is_link_like(info: os.stat_result) -> bool:
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & reparse
    )


def _ensure_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    except OSError as exc:
        _fail("io", f"cannot create store directory: {type(exc).__name__}")
    try:
        info = path.lstat()
    except OSError as exc:
        _fail("io", f"cannot inspect store directory: {type(exc).__name__}")
    if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
        _fail("path", "store component is not a real directory")


def _validate_chain(path: Path) -> None:
    if len(path.parts) > MAX_PATH_COMPONENTS:
        _fail("budget", "store root is too deep")
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except OSError as exc:
            _fail("io", f"cannot inspect store path: {type(exc).__name__}")
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "store path contains a link or non-directory")


def _validate_existing_prefix(path: Path) -> None:
    """Inspect the caller's lexical path without resolving any existing link."""
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except FileNotFoundError:
            return
        except OSError as exc:
            _fail("io", f"cannot inspect store ancestor: {type(exc).__name__}")
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "store path contains a link or non-directory")


def _prepare_root(root: Path, *, create: bool) -> Path:
    if not isinstance(root, Path):
        _fail("type", "store root must be a pathlib.Path")
    if not root.is_absolute() or root == Path(root.anchor):
        _fail("path", "store root must be a non-root absolute path")
    if root != Path(os.path.normpath(str(root))):
        _fail("path", "store root must not contain parent traversal")
    if len(root.parts) > MAX_PATH_COMPONENTS:
        _fail("budget", "store root is too deep")
    _validate_existing_prefix(root)
    try:
        resolved = root.resolve(strict=False)
    except OSError as exc:
        _fail("io", f"cannot resolve store root: {type(exc).__name__}")
    missing: list[Path] = []
    current = resolved
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            _fail("path", "store root has no existing parent")
        current = current.parent
    if missing and not create:
        _fail("missing", "store root does not exist")
    for item in reversed(missing):
        _ensure_directory(item)
    if create:
        _ensure_directory(resolved)
    _validate_chain(resolved)
    return resolved


def _child(parent: Path, name: str, *, create: bool) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        _fail("path", "unsafe derived path component")
    path = parent / name
    if create:
        _ensure_directory(path)
    else:
        try:
            info = path.lstat()
        except FileNotFoundError:
            _fail("missing", "required store directory is absent")
        except OSError as exc:
            _fail("io", f"cannot inspect store directory: {type(exc).__name__}")
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "store component is not a real directory")
    return path


def _object_path(root: Path, digest: str, *, create: bool) -> Path:
    objects = _child(root, "objects", create=create)
    fanout = _child(objects, digest[:2], create=create)
    return fanout / digest[2:]


def _session_directory(root: Path, session_id: str, *, create: bool) -> Path:
    key = _digest(session_id.encode("utf-8"))
    sessions = _child(root, "sessions", create=create)
    fanout = _child(sessions, key[:2], create=create)
    return _child(fanout, key[2:], create=create)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _read_exact(path: Path, expected_digest: str, maximum: int) -> bytes:
    try:
        linked = path.lstat()
    except FileNotFoundError:
        _fail("missing", "content object is absent")
    except OSError as exc:
        _fail("io", f"cannot inspect content object: {type(exc).__name__}")
    if _is_link_like(linked) or not stat.S_ISREG(linked.st_mode):
        _fail("link", "content object is not a direct regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        _fail("io", f"cannot open content object: {type(exc).__name__}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("link", "content object must be a single-link regular file")
        if (linked.st_dev, linked.st_ino) != (before.st_dev, before.st_ino):
            _fail("mutation", "content object changed while opening")
        if before.st_size < 1 or before.st_size > maximum:
            _fail("budget", "content object size is outside bounds")
        if hasattr(os, "getuid") and before.st_uid != os.getuid():
            _fail("ownership", "content object has another owner")
        if before.st_mode & 0o222:
            _fail("mode", "content object is writable")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1_048_576, remaining))
            if not chunk:
                _fail("partial", "content object ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("mutation", "content object grew during reading")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev, after.st_ino, after.st_size
        ):
            _fail("mutation", "content object changed during reading")
    except OSError as exc:
        _fail("io", f"cannot read content object: {type(exc).__name__}")
    finally:
        os.close(descriptor)
    data = b"".join(chunks)
    if _digest(data) != expected_digest:
        _fail("collision", "content object differs from its path digest")
    return data


def _atomic_immutable_write(path: Path, data: bytes) -> str:
    if type(data) is not bytes or not data or len(data) > MAX_OBJECT_BYTES:
        _fail("budget", "content bytes are outside bounds")
    expected = _digest(data)
    if path.exists() or path.is_symlink():
        if _read_exact(path, expected, len(data)) != data:
            _fail("collision", "existing content object differs")
        return expected
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".mathhead-tmp-", dir=path.parent)
    except OSError as exc:
        _fail("io", f"cannot create content temporary: {type(exc).__name__}")
    temporary = Path(temporary_name)
    installed = False
    try:
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            _fail("io", f"cannot write content temporary: {type(exc).__name__}")
        try:
            os.link(temporary, path)
            installed = True
        except FileExistsError:
            if _read_exact(path, expected, len(data)) != data:
                _fail("collision", "concurrent content object differs")
        except OSError as exc:
            _fail("io", f"cannot install content object: {type(exc).__name__}")
        if installed:
            try:
                temporary.unlink()
                os.chmod(path, 0o444)
            except OSError as exc:
                _fail("io", f"cannot seal content object: {type(exc).__name__}")
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            if not installed:
                _fail("io", "cannot clean uncommitted content temporary")
    return expected


def _write_object(root: Path, data: bytes) -> str:
    identity = _digest(data)
    path = _object_path(root, identity, create=True)
    return _atomic_immutable_write(path, data)


def _acquire_lock(session: Path, name: str) -> Path:
    path = session / name
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail("lock", "session store is busy or has an abandoned lock")
    except OSError as exc:
        _fail("io", f"cannot acquire session lock: {type(exc).__name__}")
    try:
        try:
            os.write(descriptor, b"mathhead problem-session lock\n")
            os.fsync(descriptor)
        except OSError as exc:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            _fail("io", f"cannot persist session lock: {type(exc).__name__}")
    finally:
        os.close(descriptor)
    _fsync_directory(session)
    return path


def _release_lock(path: Path) -> None:
    try:
        info = path.lstat()
        if _is_link_like(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("link", "session lock was replaced")
        path.unlink()
        _fsync_directory(path.parent)
    except FileNotFoundError:
        _fail("lock", "session lock disappeared")
    except ProblemSessionStoreError:
        raise
    except OSError as exc:
        _fail("io", f"cannot release session lock: {type(exc).__name__}")


def _read_head_file(session: Path, session_id: str) -> tuple[dict[str, object], bytes]:
    path = session / "HEAD"
    try:
        linked = path.lstat()
    except FileNotFoundError:
        _fail("missing", "session HEAD does not exist")
    except OSError as exc:
        _fail("io", f"cannot inspect session HEAD: {type(exc).__name__}")
    if _is_link_like(linked) or not stat.S_ISREG(linked.st_mode) or linked.st_nlink != 1:
        _fail("link", "session HEAD must be a single-link regular file")
    if linked.st_mode & 0o222:
        _fail("mode", "session HEAD must be read-only between commits")
    if hasattr(os, "getuid") and linked.st_uid != os.getuid():
        _fail("ownership", "session HEAD has another owner")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        _fail("io", f"cannot open session HEAD: {type(exc).__name__}")
    try:
        before = os.fstat(descriptor)
        if before.st_size < 1 or before.st_size > MAX_HEAD_BYTES:
            _fail("budget", "session HEAD size is outside bounds")
        data = b""
        while len(data) < before.st_size:
            chunk = os.read(descriptor, min(1_048_576, before.st_size - len(data)))
            if not chunk:
                _fail("partial", "session HEAD ended early")
            data += chunk
        if os.read(descriptor, 1):
            _fail("mutation", "session HEAD grew while reading")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev, after.st_ino, after.st_size
        ):
            _fail("mutation", "session HEAD changed while reading")
    except OSError as exc:
        _fail("io", f"cannot read session HEAD: {type(exc).__name__}")
    finally:
        os.close(descriptor)
    return _parse_head(data, session_id), data


def _load_from_head(
    root: Path, session_id: str, head: dict[str, object]
) -> ProblemSessionResult:
    event_objects = head["event_objects"]
    artifact_digests = head["artifacts"]
    assert type(event_objects) is tuple and type(artifact_digests) is tuple
    total = 0
    events: list[bytes] = []
    for identity in event_objects:
        data = _read_exact(
            _object_path(root, identity, create=False), identity, MAX_OBJECT_BYTES
        )
        total += len(data)
        if total > MAX_AGGREGATE_BYTES:
            _fail("budget", "stored event bytes exceed aggregate budget")
        events.append(data)
    artifacts: list[bytes] = []
    for identity in artifact_digests:
        data = _read_exact(
            _object_path(root, identity, create=False), identity, MAX_OBJECT_BYTES
        )
        total += len(data)
        if total > MAX_AGGREGATE_BYTES:
            _fail("budget", "stored bytes exceed aggregate budget")
        artifacts.append(data)
    result = transition_problem_session(None, tuple(events), tuple(artifacts))
    if result.status != "unchanged" or result.revision_value is None:
        _fail("replay", f"stored session failed pure replay: {result.reason_code}")
    if (
        result.session_id != session_id
        or result.revision != head["revision"]
        or result.head_sha256 != head["head_event"]
        or result.revision_value.revision_sha256 != head["revision_sha"]
    ):
        _fail("replay", "stored head differs from pure replay")
    if tuple(_digest(item) for item in result.events or ()) != event_objects:
        _fail("replay", "stored event object inventory drift")
    if tuple(_digest(item) for item in result.artifacts or ()) != artifact_digests:
        _fail("replay", "stored artifact inventory drift")
    return result


def _load_existing(
    root: Path, session_id: str
) -> tuple[dict[str, object], bytes, ProblemSessionResult]:
    session = _session_directory(root, session_id, create=False)
    head, head_bytes = _read_head_file(session, session_id)
    return head, head_bytes, _load_from_head(root, session_id, head)


def _build_head(result: ProblemSessionResult) -> tuple[dict[str, object], bytes]:
    if result.status != "updated" or result.revision_value is None:
        _fail("replay", "only an updated core result can build a new store head")
    assert result.session_id is not None and result.head_sha256 is not None
    assert result.events is not None and result.artifacts is not None
    value: dict[str, object] = {
        "artifact_sha256s": [_digest(item) for item in result.artifacts],
        "event_sha256s": [_digest(item) for item in result.events],
        "head_event_sha256": result.head_sha256,
        "head_sha256": None,
        "mathematical_authority": False,
        "revision": result.revision,
        "revision_sha256": result.revision_value.revision_sha256,
        "schema": STORE_HEAD_SCHEMA,
        "session_id": result.session_id,
        "session_key_sha256": _digest(result.session_id.encode("utf-8")),
        "store_contract_id": PROBLEM_SESSION_STORE_CONTRACT_ID,
        "store_contract_sha256": PROBLEM_SESSION_STORE_CONTRACT_SHA256,
    }
    value["head_sha256"] = _digest(_head_preimage(value))
    data = _canonical_bytes(value)
    parsed = _parse_head(data, result.session_id)
    return parsed, data


def _atomic_replace_head(session: Path, data: bytes) -> None:
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".mathhead-head-", dir=session)
    except OSError as exc:
        _fail("io", f"cannot create HEAD temporary: {type(exc).__name__}")
    temporary = Path(temporary_name)
    head = session / "HEAD"
    replaced = False
    prior_head_unsealed = False
    try:
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o444)
        except OSError as exc:
            _fail("io", f"cannot seal HEAD temporary: {type(exc).__name__}")
        if _WINDOWS and (head.exists() or head.is_symlink()):
            try:
                info = head.lstat()
                if (
                    _is_link_like(info)
                    or not stat.S_ISREG(info.st_mode)
                    or info.st_nlink != 1
                ):
                    _fail("link", "session HEAD changed before replacement")
                os.chmod(head, 0o644)
                prior_head_unsealed = True
            except ProblemSessionStoreError:
                raise
            except OSError as exc:
                _fail("io", f"cannot prepare HEAD replacement: {type(exc).__name__}")
        try:
            os.replace(temporary, head)
            replaced = True
        except OSError as exc:
            if prior_head_unsealed:
                try:
                    os.chmod(head, 0o444)
                except OSError as restore_exc:
                    _fail(
                        "io",
                        f"cannot restore prior HEAD mode: {type(restore_exc).__name__}",
                    )
            _fail("io", f"cannot atomically replace HEAD: {type(exc).__name__}")
        _fsync_directory(session)
    finally:
        if not replaced:
            try:
                if _WINDOWS and temporary.exists():
                    os.chmod(temporary, 0o600)
                temporary.unlink(missing_ok=True)
            except OSError:
                _fail("io", "cannot clean uncommitted HEAD temporary")


def load_problem_session(root: Path, session_id: str) -> ProblemSessionResult:
    """Load exact committed bytes and freshly replay one session."""
    session_id = _valid_id(session_id)
    store = _prepare_root(root, create=False)
    _, _, result = _load_existing(store, session_id)
    return result


def persist_problem_session(
    root: Path,
    command: bytes,
    artifacts: tuple[bytes, ...],
) -> ProblemSessionResult:
    """Apply and atomically persist one exact session command."""
    if type(command) is not bytes:
        _fail("type", "command must be exact bytes")
    if type(artifacts) is not tuple or any(type(item) is not bytes for item in artifacts):
        _fail("type", "artifacts must be an exact tuple of exact bytes")
    command_value = parse_problem_session_command(command)
    session_id = _valid_id(command_value["session_id"])
    store = _prepare_root(root, create=True)
    session = _session_directory(store, session_id, create=True)
    lock = _acquire_lock(session, ".writer-lock")
    try:
        head_path = session / "HEAD"
        if head_path.exists() or head_path.is_symlink():
            old_head, old_head_bytes, previous = _load_existing(store, session_id)
            assert previous.events is not None and previous.artifacts is not None
            merged: dict[str, bytes] = {_digest(item): item for item in previous.artifacts}
            for item in artifacts:
                identity = _digest(item)
                existing = merged.get(identity)
                if existing is not None and existing != item:
                    _fail("collision", "caller artifact collides with stored content")
                merged.setdefault(identity, item)
            complete_artifacts = tuple(merged[key] for key in sorted(merged))
            result = transition_problem_session(command, previous.events, complete_artifacts)
            if result.status == "unchanged":
                current_head, current_bytes = _read_head_file(session, session_id)
                if current_bytes != old_head_bytes or current_head["head_sha"] != old_head["head_sha"]:
                    _fail("mutation", "HEAD changed during idempotent retry")
                return result
            if command_value["expected_head_sha256"] != old_head["head_event"]:
                if result.status != "conflict":
                    _fail("conflict", "stale expected head was not refused by core")
                return result
        else:
            if command_value["kind"] != "create_session":
                _fail("missing", "non-create command has no committed session")
            complete_artifacts = tuple(
                item for _, item in sorted((_digest(item), item) for item in artifacts)
            )
            result = transition_problem_session(command, (), complete_artifacts)
        if result.status != "updated":
            return result
        assert result.events is not None and result.artifacts is not None
        for item in result.artifacts:
            _write_object(store, item)
        for item in result.events:
            _write_object(store, item)
        _write_object(store, command)
        assert result.revision_value is not None
        revision_bytes = session_component_to_bytes(result.revision_value)
        if _parse_json(revision_bytes).get("schema") != REVISION_SCHEMA:
            _fail("replay", "serialized revision schema drift")
        _write_object(store, revision_bytes)
        _, head_bytes = _build_head(result)
        _write_object(store, head_bytes)
        _atomic_replace_head(session, head_bytes)
        head, committed_bytes = _read_head_file(session, session_id)
        if committed_bytes != head_bytes:
            _fail("mutation", "committed HEAD bytes differ")
        loaded = _load_from_head(store, session_id, head)
        if (
            loaded.head_sha256 != result.head_sha256
            or loaded.revision_value != result.revision_value
        ):
            _fail("replay", "post-commit replay differs from updated result")
        return result
    finally:
        _release_lock(lock)


def recover_problem_session_store(root: Path, session_id: str) -> ProblemSessionResult:
    """Remove only abandoned adapter temporaries, then replay the last HEAD."""
    session_id = _valid_id(session_id)
    store = _prepare_root(root, create=False)
    session = _session_directory(store, session_id, create=False)
    recovery = _acquire_lock(session, ".recovery-lock")
    try:
        try:
            entries = list(session.iterdir())
        except OSError as exc:
            _fail("io", f"cannot enumerate recovery directory: {type(exc).__name__}")
        if len(entries) > MAX_TEMPORARIES + 4:
            _fail("budget", "session directory entry count exceeds recovery budget")
        for path in entries:
            if path.name == ".writer-lock" or path.name.startswith(".mathhead-head-"):
                try:
                    info = path.lstat()
                    if _is_link_like(info) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                        _fail("link", "recovery target is not a direct single-link regular file")
                    if _WINDOWS and not info.st_mode & 0o200:
                        os.chmod(path, 0o600)
                    path.unlink()
                except FileNotFoundError:
                    pass
                except ProblemSessionStoreError:
                    raise
                except OSError as exc:
                    _fail("io", f"cannot clean recovery target: {type(exc).__name__}")
        _fsync_directory(session)
        head, _ = _read_head_file(session, session_id)
        return _load_from_head(store, session_id, head)
    finally:
        _release_lock(recovery)


__all__ = [
    "PROBLEM_SESSION_STORE_CONTRACT_ID",
    "PROBLEM_SESSION_STORE_CONTRACT_SHA256",
    "ProblemSessionStoreError",
    "STORE_HEAD_SCHEMA",
    "STORE_HEAD_SCHEMA_SHA256",
    "load_problem_session",
    "persist_problem_session",
    "recover_problem_session_store",
]
