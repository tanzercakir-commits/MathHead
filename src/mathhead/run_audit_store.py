"""Append-only content-addressed persistence for MH-054 audit bundles."""

from __future__ import annotations

from dataclasses import dataclass, fields
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from threading import Lock
from typing import Any, Final, NoReturn

from .run_audit import (
    RunAuditBundle,
    RunAuditValidationError,
    _bundle_from_replayed_bytes,
    run_audit_bundle_sha256,
    run_audit_logical_report_bytes,
    run_audit_manifest_bytes,
    run_audit_object_bytes,
    validate_run_audit_bundle,
)


STORE_CONTRACT_ID: Final = "MH-C-RUN-AUDIT-STORE-001"
STORE_CONTRACT_SHA256: Final = (
    "a28a5f7f0a9f592a2addf0c0a653483fd3198adec112507705567479c17cbc12"
)
STORE_RECORD_SCHEMA: Final = "mathhead.run-audit-store-record.v1"
STORE_RESULT_SCHEMA: Final = "mathhead.run-audit-store-result.v1"
SCHEMA_SHA256S: Final = {
    STORE_RECORD_SCHEMA: "de9127034133d21d23e5d2376a18247da89842b6de65da8555e1ddfc5ec60c05",
    STORE_RESULT_SCHEMA: "9245bc736376bbb812234d5e0562a8b541e14ad3cbfbe901cd56bbd82e9544d0",
}

MAX_OBJECT_BYTES: Final = 1_073_741_824
MAX_AGGREGATE_BYTES: Final = 2_147_483_648
MAX_OBJECTS: Final = 200_000
MAX_RUNS: Final = 1_000_000
MAX_RECORD_BYTES: Final = 67_108_864
MAX_PATH_COMPONENTS: Final = 128
MAX_PATH_CODEPOINTS: Final = 32_768
INTEGER_MAXIMUM: Final = 9_007_199_254_740_991

_DIGEST = re.compile(r"[0-9a-f]{64}")
_REASON = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_RESULT_STATUSES = {"stored", "existing", "loaded", "invalid", "unsupported", "io_error"}
_INSTALL_LOCK = Lock()


class RunAuditStoreError(RuntimeError):
    """Strict audit-store path, state, or I/O failure."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _DuplicateKey(ValueError):
    pass


_PUBLIC_FINAL = False


class _StoreValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_FINAL:
            raise TypeError("run-audit store value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class RunAuditStoreResult(_StoreValue):
    schema: str
    contract_id: str
    contract_sha256: str
    status: str
    reason_code: str
    manifest_sha256: str | None
    record_sha256: str | None
    object_count: int
    result_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("run-audit store results are store-owned")


_PUBLIC_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


def _fail(kind: str, detail: str) -> NoReturn:
    raise RunAuditStoreError(kind, detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _canonical(value: object) -> bytes:
    try:
        raw = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        _fail("record", f"canonical encoding failed: {type(exc).__name__}")
    if len(raw) > MAX_RECORD_BYTES:
        _fail("budget", "store record exceeds byte budget")
    return raw


def _parse(data: bytes) -> dict[str, object]:
    if type(data) is not bytes or not data or len(data) > MAX_RECORD_BYTES:
        _fail("budget", "store record bytes are outside bounds")
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda value: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except _DuplicateKey as exc:
        _fail("record", f"duplicate store record key {exc.args[0]!r}")
    except (UnicodeError, ValueError, RecursionError) as exc:
        _fail("record", f"invalid store record JSON: {type(exc).__name__}")
    if type(value) is not dict or _canonical(value) != data:
        _fail("record", "store record is not one canonical object")
    return value


def _digest(value: object, label: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        _fail("record", f"{label} is not one full lowercase SHA-256")
    return value


def _quantity(value: object, label: str, maximum: int) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        _fail("record", f"{label} is not one bounded exact integer")
    return value


def _self_hash(value: dict[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _record_bytes(bundle: RunAuditBundle) -> tuple[bytes, str]:
    manifest = run_audit_manifest_bytes(bundle)
    object_digests = sorted(
        {_sha(raw) for raw in (*run_audit_object_bytes(bundle), manifest)}
    )
    logical = run_audit_logical_report_bytes(bundle)
    value: dict[str, object] = {
        "schema": STORE_RECORD_SCHEMA,
        "store_contract_sha256": STORE_CONTRACT_SHA256,
        "manifest_sha256": _sha(manifest),
        "logical_report_sha256": _sha(logical),
        "object_sha256s": object_digests,
        "record_sha256": None,
        "mathematical_authority": False,
    }
    value["record_sha256"] = _self_hash(value, "record_sha256")
    raw = _canonical(value)
    return raw, str(value["record_sha256"])


def _parse_record(data: bytes, expected_manifest: str) -> dict[str, object]:
    value = _parse(data)
    expected = {
        "schema",
        "store_contract_sha256",
        "manifest_sha256",
        "logical_report_sha256",
        "object_sha256s",
        "record_sha256",
        "mathematical_authority",
    }
    if set(value) != expected:
        _fail("record", "store record field set differs")
    if (
        value["schema"] != STORE_RECORD_SCHEMA
        or value["store_contract_sha256"] != STORE_CONTRACT_SHA256
        or value["mathematical_authority"] is not False
    ):
        _fail("record", "store record contract binding differs")
    manifest = _digest(value["manifest_sha256"], "manifest_sha256")
    if manifest != expected_manifest:
        _fail("record", "store record names another manifest")
    logical = _digest(value["logical_report_sha256"], "logical_report_sha256")
    raw_objects = value["object_sha256s"]
    if type(raw_objects) is not list or not raw_objects or len(raw_objects) > MAX_OBJECTS + 1:
        _fail("budget", "store object inventory is outside bounds")
    objects = tuple(_digest(item, "object_sha256") for item in raw_objects)
    if objects != tuple(sorted(set(objects))) or manifest not in objects or logical not in objects:
        _fail("record", "store object inventory is not closed sorted unique")
    identity = _digest(value["record_sha256"], "record_sha256")
    if identity != _self_hash(value, "record_sha256"):
        _fail("record", "store record identity differs")
    return value


def _is_link_like(info: os.stat_result) -> bool:
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & reparse
    )


def _inspect_directory(path: Path, *, private: bool) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        _fail("io", f"cannot inspect store directory: {type(exc).__name__}")
    if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
        _fail("link", "store component is not a real directory")
    if private and os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        _fail("mode", "store directory is not private")


def _validate_existing_prefix(path: Path) -> None:
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
            _fail("link", "store path contains a link or non-directory")


def _root(root: Path, *, create: bool) -> Path:
    if not isinstance(root, Path):
        _fail("type", "store root must be an exact pathlib.Path")
    if (
        not root.is_absolute()
        or root == Path(root.anchor)
        or len(root.parts) > MAX_PATH_COMPONENTS
        or len(str(root)) > MAX_PATH_CODEPOINTS
        or root != Path(os.path.normpath(str(root)))
    ):
        _fail("path", "store root is relative, root, non-normalized, or over budget")
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
        try:
            item.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            _fail("io", f"cannot create store directory: {type(exc).__name__}")
        _inspect_directory(item, private=True)
    _inspect_directory(resolved, private=True)
    return resolved


def _directory(parent: Path, name: str, *, create: bool) -> Path:
    child = parent / name
    if create:
        try:
            child.mkdir(mode=0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            _fail("io", f"cannot create store component: {type(exc).__name__}")
    elif not child.exists():
        _fail("missing", "store component is absent")
    _inspect_directory(child, private=True)
    return child


def _content_path(root: Path, digest: str, *, create: bool) -> Path:
    objects = _directory(root, "objects", create=create)
    bucket = _directory(objects, digest[:2], create=create)
    return bucket / digest


def _run_path(root: Path, digest: str, *, create: bool) -> Path:
    runs = _directory(root, "runs", create=create)
    bucket = _directory(runs, digest[:2], create=create)
    return bucket / digest


def _inspect_file(path: Path) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        _fail("io", f"cannot inspect store file: {type(exc).__name__}")
    if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
        _fail("link", "store file is not a real regular file")
    if info.st_nlink != 1:
        _fail("link", "store file has an unsafe hardlink count")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        _fail("mode", "store file is not private")
    return info


def _read_bounded(path: Path, maximum: int) -> bytes:
    info = _inspect_file(path)
    if info.st_size < 1 or info.st_size > maximum:
        _fail("budget", "store file size is outside bounds")
    try:
        with path.open("rb") as handle:
            data = handle.read(maximum + 1)
    except OSError as exc:
        _fail("io", f"cannot read store file: {type(exc).__name__}")
    after = _inspect_file(path)
    if (
        len(data) != info.st_size
        or after.st_size != info.st_size
        or getattr(after, "st_ino", None) != getattr(info, "st_ino", None)
    ):
        _fail("corrupt", "store file changed while it was read")
    return data


def _read_exact(path: Path, digest: str, maximum: int) -> bytes:
    data = _read_bounded(path, maximum)
    if _sha(data) != digest:
        _fail("corrupt", "store file content digest differs")
    return data


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
            _fail("io", f"cannot fsync store directory: {type(exc).__name__}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        try:
            count = os.write(descriptor, view[written:])
        except OSError as exc:
            _fail("io", f"cannot write store file: {type(exc).__name__}")
        if count <= 0:
            _fail("io", "store write made no progress")
        written += count


def _read_existing_exact(path: Path, data: bytes) -> None:
    for _attempt in range(10_000):
        try:
            if _read_bounded(path, max(len(data), MAX_RECORD_BYTES)) != data:
                _fail("conflict", "existing immutable content differs")
            return
        except RunAuditStoreError as exc:
            if exc.kind != "link" or not hasattr(os, "sched_yield"):
                raise
            os.sched_yield()
    _fail("link", "immutable target retained an unsafe hardlink count")


def _write_immutable_locked(
    path: Path, data: bytes, *, name_digest: str | None = None
) -> bool:
    content_digest = _sha(data)
    target_identity = content_digest if name_digest is None else _digest(
        name_digest, "target identity"
    )
    if path.name != target_identity:
        _fail("path", "immutable target name differs")
    try:
        existing = path.exists()
    except OSError as exc:
        _fail("io", f"cannot inspect content target: {type(exc).__name__}")
    if existing:
        _read_existing_exact(path, data)
        return False
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{target_identity}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(name)
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        try:
            os.link(temporary, path, follow_symlinks=False)
            created = True
        except FileExistsError:
            created = False
        except OSError as exc:
            _fail("io", f"cannot install immutable content: {type(exc).__name__}")
        temporary.unlink()
        temporary = None
        _read_existing_exact(path, data)
        _fsync_directory(path.parent)
        return created
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _write_immutable(
    path: Path, data: bytes, *, name_digest: str | None = None
) -> bool:
    with _INSTALL_LOCK:
        return _write_immutable_locked(path, data, name_digest=name_digest)


def _result_mapping(value: RunAuditStoreResult, *, own_hash: bool = True) -> dict[str, object]:
    return {
        "schema": value.schema,
        "contract_id": value.contract_id,
        "contract_sha256": value.contract_sha256,
        "status": value.status,
        "reason_code": value.reason_code,
        "manifest_sha256": value.manifest_sha256,
        "record_sha256": value.record_sha256,
        "object_count": value.object_count,
        "result_sha256": value.result_sha256 if own_hash else None,
        "mathematical_authority": value.mathematical_authority,
    }


def _new_result(
    status: str,
    reason: str,
    *,
    manifest_sha256: str | None,
    record_sha256: str | None,
    object_count: int,
) -> RunAuditStoreResult:
    if status not in _RESULT_STATUSES or _REASON.fullmatch(reason) is None:
        _fail("result", "store result classification is outside the closed set")
    value: dict[str, object] = {
        "schema": STORE_RESULT_SCHEMA,
        "contract_id": STORE_CONTRACT_ID,
        "contract_sha256": STORE_CONTRACT_SHA256,
        "status": status,
        "reason_code": reason,
        "manifest_sha256": manifest_sha256,
        "record_sha256": record_sha256,
        "object_count": object_count,
        "result_sha256": None,
        "mathematical_authority": False,
    }
    value["result_sha256"] = _self_hash(value, "result_sha256")
    return _make(RunAuditStoreResult, **value)


def persist_run_audit(root: Path, bundle: RunAuditBundle) -> RunAuditStoreResult:
    """Freshly replay and atomically append one immutable audit run."""
    if not isinstance(root, Path):
        _fail("type", "store root must be an exact pathlib.Path")
    if type(bundle) is not RunAuditBundle:
        return _new_result(
            "invalid",
            "BUNDLE_INVALID",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    try:
        validate_run_audit_bundle(bundle)
    except RunAuditValidationError:
        return _new_result(
            "invalid",
            "BUNDLE_INVALID",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    store = _root(root, create=True)
    manifest = run_audit_manifest_bytes(bundle)
    manifest_digest = run_audit_bundle_sha256(bundle)
    object_values = {
        _sha(raw): raw for raw in (*run_audit_object_bytes(bundle), manifest)
    }
    if len(object_values) > MAX_OBJECTS + 1 or sum(len(raw) for raw in object_values.values()) > MAX_AGGREGATE_BYTES:
        return _new_result(
            "invalid",
            "STORE_BUDGET_EXCEEDED",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    record, record_identity = _record_bytes(bundle)
    try:
        for digest in sorted(object_values):
            target = _content_path(store, digest, create=True)
            _write_immutable(target, object_values[digest])
        run_target = _run_path(store, manifest_digest, create=True)
        created = _write_immutable(
            run_target, record, name_digest=manifest_digest
        )
        _fsync_directory(run_target.parent)
        loaded = load_run_audit(store, manifest_digest)
        if run_audit_bundle_sha256(loaded) != manifest_digest:
            _fail("corrupt", "freshly loaded run identity differs")
        return _new_result(
            "stored" if created else "existing",
            "RUN_STORED" if created else "RUN_ALREADY_EXISTS",
            manifest_sha256=manifest_digest,
            record_sha256=record_identity,
            object_count=len(object_values),
        )
    except RunAuditStoreError:
        raise
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except OSError:
        return _new_result(
            "io_error",
            "STORE_IO_ERROR",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )


def load_run_audit(root: Path, manifest_sha256: str) -> RunAuditBundle:
    """Load one visible immutable run and freshly replay its exact bytes."""
    digest = _digest(manifest_sha256, "manifest_sha256")
    store = _root(root, create=False)
    run_path = _run_path(store, digest, create=False)
    record_raw = _read_bounded(run_path, MAX_RECORD_BYTES)
    record = _parse_record(record_raw, digest)
    object_digests = tuple(str(item) for item in record["object_sha256s"])
    values: dict[str, bytes] = {}
    total = 0
    for object_digest in object_digests:
        raw = _read_exact(
            _content_path(store, object_digest, create=False),
            object_digest,
            MAX_OBJECT_BYTES,
        )
        total += len(raw)
        if total > MAX_AGGREGATE_BYTES:
            _fail("budget", "stored run aggregate exceeds budget")
        values[object_digest] = raw
    manifest = values[digest]
    objects = tuple(values[item] for item in object_digests if item != digest)
    bundle = _bundle_from_replayed_bytes(manifest, objects)
    if bundle.logical_report_sha256 != record["logical_report_sha256"]:
        _fail("corrupt", "stored logical report identity differs")
    return bundle


def list_run_audits(root: Path) -> tuple[str, ...]:
    """Return digest-sorted visible runs only after fresh complete replay."""
    store = _root(root, create=False)
    runs = _directory(store, "runs", create=False)
    identities: list[str] = []
    try:
        buckets = sorted(runs.iterdir(), key=lambda item: item.name)
    except OSError as exc:
        _fail("io", f"cannot enumerate run store: {type(exc).__name__}")
    for bucket in buckets:
        if re.fullmatch(r"[0-9a-f]{2}", bucket.name) is None:
            _fail("corrupt", "run bucket name differs")
        _inspect_directory(bucket, private=True)
        try:
            entries = sorted(bucket.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            _fail("io", f"cannot enumerate run bucket: {type(exc).__name__}")
        for entry in entries:
            if entry.name.startswith(".") and entry.name.endswith(".tmp"):
                continue
            if _DIGEST.fullmatch(entry.name) is None or entry.name[:2] != bucket.name:
                _fail("corrupt", "run record filename differs")
            identities.append(entry.name)
            if len(identities) > MAX_RUNS:
                _fail("budget", "run listing exceeds budget")
    result = tuple(sorted(identities))
    if len(set(result)) != len(result):
        _fail("corrupt", "duplicate visible run identity")
    for digest in result:
        load_run_audit(store, digest)
    return result


def validate_run_audit_store_result(value: RunAuditStoreResult) -> None:
    if type(value) is not RunAuditStoreResult:
        _fail("type", "expected exact RunAuditStoreResult")
    mapping = _result_mapping(value)
    if (
        value.schema != STORE_RESULT_SCHEMA
        or value.contract_id != STORE_CONTRACT_ID
        or value.contract_sha256 != STORE_CONTRACT_SHA256
        or value.status not in _RESULT_STATUSES
        or _REASON.fullmatch(value.reason_code) is None
        or value.mathematical_authority is not False
        or value.result_sha256 != _self_hash(mapping, "result_sha256")
        or type(value.object_count) is not int
        or value.object_count < 0
        or value.object_count > MAX_OBJECTS + 1
    ):
        _fail("result", "store result fields or identity differ")
    if value.status in {"stored", "existing", "loaded"}:
        _digest(value.manifest_sha256, "result.manifest_sha256")
        _digest(value.record_sha256, "result.record_sha256")
    elif value.manifest_sha256 is not None or value.record_sha256 is not None or value.object_count != 0:
        _fail("result", "failed store result retains committed identity")


def run_audit_store_result_bytes(value: RunAuditStoreResult) -> bytes:
    validate_run_audit_store_result(value)
    return _canonical(_result_mapping(value))


__all__ = [
    "RunAuditStoreError",
    "RunAuditStoreResult",
    "SCHEMA_SHA256S",
    "STORE_CONTRACT_ID",
    "STORE_CONTRACT_SHA256",
    "STORE_RECORD_SCHEMA",
    "STORE_RESULT_SCHEMA",
    "list_run_audits",
    "load_run_audit",
    "persist_run_audit",
    "run_audit_store_result_bytes",
    "validate_run_audit_store_result",
]
