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


STORE_CONTRACT_ID: Final = "MH-C-RUN-AUDIT-STORE-005"
STORE_CONTRACT_SHA256: Final = "399bcb9d97217d249d9200697281a25052476f67f8435740fa32d6c7ed2c272b"
STORE_RECORD_SCHEMA: Final = "mathhead.run-audit-store-record.v2"
STORE_RESULT_SCHEMA: Final = "mathhead.run-audit-store-result.v5"
SCHEMA_SHA256S: Final = {
    STORE_RECORD_SCHEMA: "614083f9de220b6a780ff35e7ab6cd3c07f1c3371255112e433213ea556ade8f",
    STORE_RESULT_SCHEMA: "bf906f5c01fee05524b4c11cb80a526b5ca72214e8b417d44a3d4191077c11d4",
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
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
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
    object_digests = sorted({_sha(raw) for raw in (*run_audit_object_bytes(bundle), manifest)})
    if len(object_digests) > MAX_OBJECTS:
        _fail("budget", "store object inventory exceeds the schema bound")
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
    if type(raw_objects) is not list or not raw_objects or len(raw_objects) > MAX_OBJECTS:
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
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & reparse)


@dataclass(frozen=True, slots=True)
class _DirectoryIdentity:
    path: Path
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class _PinnedRoot:
    path: Path
    descriptor: int
    chain: tuple[_DirectoryIdentity, ...]

    def close(self) -> None:
        os.close(self.descriptor)


_UNSUPPORTED_ERRNOS = {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}
_TEMP_SEQUENCE = 0


def _descriptor_store_supported() -> bool:
    required_dir_fd = {os.open, os.mkdir, os.stat, os.link, os.unlink}
    return (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "fchmod")
        and required_dir_fd <= os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and os.link in os.supports_follow_symlinks
    )


def _classify_io(exc: OSError, detail: str) -> NoReturn:
    if exc.errno in _UNSUPPORTED_ERRNOS:
        _fail("unsupported", f"{detail}: {type(exc).__name__}")
    _fail("io", f"{detail}: {type(exc).__name__}")


def _directory_info(info: os.stat_result, *, private: bool) -> None:
    if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
        _fail("link", "store component is not a real directory")
    if private and stat.S_IMODE(info.st_mode) != 0o700:
        _fail("mode", "store directory mode is not exact private 0700")


def _file_info(info: os.stat_result) -> None:
    if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
        _fail("link", "store file is not a real regular file")
    if info.st_nlink != 1:
        _fail("link", "store file has an unsafe hardlink count")
    if stat.S_IMODE(info.st_mode) != 0o600:
        _fail("mode", "store file mode is not exact private 0600")


def _guard_root(root: _PinnedRoot) -> None:
    for expected in root.chain:
        try:
            info = os.stat(expected.path, follow_symlinks=False)
        except OSError as exc:
            _fail("link", f"store ancestor identity is unavailable: {type(exc).__name__}")
        if (
            _is_link_like(info)
            or not stat.S_ISDIR(info.st_mode)
            or (info.st_dev, info.st_ino) != (expected.device, expected.inode)
        ):
            _fail("link", "store ancestor identity changed")


def _open_root(root: Path, *, create: bool) -> _PinnedRoot:
    if type(root) is not type(Path()):
        _fail("type", "store root must be an exact concrete pathlib.Path")
    if (
        not root.is_absolute()
        or root == Path(root.anchor)
        or root.anchor != os.path.sep
        or len(root.parts) > MAX_PATH_COMPONENTS
        or len(str(root)) > MAX_PATH_CODEPOINTS
        or root != Path(os.path.normpath(str(root)))
    ):
        _fail("path", "store root is relative, root, non-normalized, or over budget")
    if not _descriptor_store_supported():
        _fail("unsupported", "descriptor-relative no-follow store operations are unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = -1
    current_path = Path(root.anchor)
    chain: list[_DirectoryIdentity] = []
    try:
        descriptor = os.open(current_path, flags)
        anchor_info = os.fstat(descriptor)
        _directory_info(anchor_info, private=False)
        chain.append(_DirectoryIdentity(current_path, anchor_info.st_dev, anchor_info.st_ino))
        for index, component in enumerate(root.parts[1:]):
            is_root = index == len(root.parts[1:]) - 1
            try:
                linked = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                if not create:
                    _fail("missing", "store root does not exist")
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                except OSError as exc:
                    _classify_io(exc, "cannot create store directory")
                try:
                    linked = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                    os.fsync(descriptor)
                except OSError as exc:
                    _classify_io(exc, "cannot synchronize store ancestor creation")
            except OSError as exc:
                _classify_io(exc, "cannot inspect store ancestor")
            _directory_info(linked, private=is_root)
            try:
                opened = os.open(component, flags, dir_fd=descriptor)
            except OSError as exc:
                _classify_io(exc, "cannot open store ancestor")
            opened_info = os.fstat(opened)
            if (linked.st_dev, linked.st_ino) != (
                opened_info.st_dev,
                opened_info.st_ino,
            ):
                os.close(opened)
                _fail("link", "store ancestor changed while opening")
            os.close(descriptor)
            descriptor = opened
            current_path /= component
            chain.append(_DirectoryIdentity(current_path, opened_info.st_dev, opened_info.st_ino))
        result = _PinnedRoot(root, descriptor, tuple(chain))
        _guard_root(result)
        return result
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _open_child_directory(root: _PinnedRoot, parent: int, name: str, *, create: bool) -> int:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        _fail("path", "derived store component is unsafe")
    _guard_root(root)
    try:
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        if not create:
            _fail("missing", "store component is absent")
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        except OSError as exc:
            _classify_io(exc, "cannot create store component")
        try:
            linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _fsync_directory(root, parent, capability_probe=True)
        except OSError as exc:
            _classify_io(exc, "cannot synchronize store component creation")
    except OSError as exc:
        _classify_io(exc, "cannot inspect store component")
    _directory_info(linked, private=True)
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent,
        )
    except OSError as exc:
        _classify_io(exc, "cannot open store component")
    opened = os.fstat(descriptor)
    if (linked.st_dev, linked.st_ino) != (opened.st_dev, opened.st_ino):
        os.close(descriptor)
        _fail("link", "store component changed while opening")
    try:
        _guard_root(root)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_bucket(root: _PinnedRoot, category: str, digest: str, *, create: bool) -> int:
    category_fd = _open_child_directory(root, root.descriptor, category, create=create)
    try:
        return _open_child_directory(root, category_fd, digest[:2], create=create)
    finally:
        os.close(category_fd)


def _read_bounded(root: _PinnedRoot, parent: int, name: str, maximum: int) -> bytes:
    _guard_root(root)
    try:
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _file_info(linked)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    except OSError as exc:
        _classify_io(exc, "cannot open store file")
    try:
        before = os.fstat(descriptor)
        if (linked.st_dev, linked.st_ino) != (before.st_dev, before.st_ino):
            _fail("link", "store file changed while opening")
        _file_info(before)
        if before.st_size < 1 or before.st_size > maximum:
            _fail("budget", "store file size is outside bounds")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            try:
                chunk = os.read(descriptor, min(1_048_576, remaining))
            except OSError as exc:
                _classify_io(exc, "cannot read store file")
            if not chunk:
                _fail("partial", "store file ended before its recorded size")
            chunks.append(chunk)
            remaining -= len(chunk)
        try:
            if os.read(descriptor, 1):
                _fail("corrupt", "store file grew while it was read")
        except OSError as exc:
            _classify_io(exc, "cannot finish reading store file")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            _fail("corrupt", "store file changed while it was read")
        _guard_root(root)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_exact(root: _PinnedRoot, parent: int, name: str, digest: str, maximum: int) -> bytes:
    data = _read_bounded(root, parent, name, maximum)
    if _sha(data) != digest:
        _fail("corrupt", "store file content digest differs")
    return data


def _fsync_directory(root: _PinnedRoot, descriptor: int, *, capability_probe: bool = False) -> None:
    _guard_root(root)
    try:
        info = os.fstat(descriptor)
        _directory_info(info, private=True)
        os.fsync(descriptor)
    except OSError as exc:
        if not capability_probe and exc.errno in _UNSUPPORTED_ERRNOS:
            _fail(
                "io",
                f"store directory synchronization failed after capability probe: {type(exc).__name__}",
            )
        _classify_io(exc, "cannot synchronize store directory")
    _guard_root(root)


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


def _read_existing_exact(root: _PinnedRoot, parent: int, name: str, data: bytes) -> None:
    for _attempt in range(10_000):
        try:
            if _read_bounded(root, parent, name, max(len(data), MAX_RECORD_BYTES)) != data:
                _fail("conflict", "existing immutable content differs")
            return
        except RunAuditStoreError as exc:
            if exc.kind != "link" or not hasattr(os, "sched_yield"):
                raise
            os.sched_yield()
    _fail("link", "immutable target retained an unsafe hardlink count")


def _quarantine_uncommitted(root: _PinnedRoot, parent: int, target: str) -> None:
    descriptor = -1
    _guard_root(root)
    try:
        descriptor = os.open(
            target,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=parent,
        )
        info = os.fstat(descriptor)
        if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
            _fail("link", "uncommitted target is not a regular file")
        os.fchmod(descriptor, 0o000)
        os.fsync(descriptor)
    except OSError as exc:
        _fail("io", f"cannot quarantine uncommitted target: {type(exc).__name__}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _guard_root(root)


def _write_immutable_locked(
    root: _PinnedRoot,
    parent: int,
    target: str,
    data: bytes,
    *,
    name_digest: str | None = None,
) -> bool:
    global _TEMP_SEQUENCE
    content_digest = _sha(data)
    target_identity = (
        content_digest if name_digest is None else _digest(name_digest, "target identity")
    )
    if target != target_identity:
        _fail("path", "immutable target name differs")
    _guard_root(root)
    try:
        os.stat(target, dir_fd=parent, follow_symlinks=False)
        existing = True
    except FileNotFoundError:
        existing = False
    except OSError as exc:
        _classify_io(exc, "cannot inspect content target")
    if existing:
        _read_existing_exact(root, parent, target, data)
        return False
    descriptor = -1
    temporary: str | None = None
    try:
        for _attempt in range(10_000):
            sequence = _TEMP_SEQUENCE
            _TEMP_SEQUENCE += 1
            candidate = f".{target_identity}.{sequence:016x}.tmp"
            try:
                descriptor = os.open(
                    candidate,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=parent,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
            except OSError as exc:
                _classify_io(exc, "cannot create content temporary")
        if descriptor < 0 or temporary is None:
            _fail("io", "cannot allocate one bounded content temporary")
        try:
            os.fchmod(descriptor, 0o600)
        except OSError as exc:
            _classify_io(exc, "cannot set private content mode")
        _write_all(descriptor, data)
        try:
            os.fsync(descriptor)
        except OSError as exc:
            _classify_io(exc, "cannot synchronize content temporary")
        os.close(descriptor)
        descriptor = -1
        _guard_root(root)
        try:
            os.link(
                temporary,
                target,
                src_dir_fd=parent,
                dst_dir_fd=parent,
                follow_symlinks=False,
            )
            created = True
        except FileExistsError:
            created = False
        except OSError as exc:
            _classify_io(exc, "cannot install immutable content")
        try:
            os.unlink(temporary, dir_fd=parent)
        except OSError as exc:
            if created:
                try:
                    _quarantine_uncommitted(root, parent, target)
                    os.unlink(target, dir_fd=parent)
                    _fsync_directory(root, parent)
                except (OSError, RunAuditStoreError):
                    temporary = None
            _classify_io(exc, "cannot clean content temporary")
        temporary = None
        _read_existing_exact(root, parent, target, data)
        try:
            _fsync_directory(root, parent)
        except RunAuditStoreError:
            if created:
                try:
                    _quarantine_uncommitted(root, parent, target)
                    os.unlink(target, dir_fd=parent)
                    _fsync_directory(root, parent)
                except (OSError, RunAuditStoreError):
                    pass
            raise
        return created
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=parent)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def _write_immutable(
    root: _PinnedRoot,
    parent: int,
    target: str,
    data: bytes,
    *,
    name_digest: str | None = None,
) -> bool:
    with _INSTALL_LOCK:
        return _write_immutable_locked(root, parent, target, data, name_digest=name_digest)


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
    if type(root) is not type(Path()):
        _fail("type", "store root must be an exact concrete pathlib.Path")
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
    if not _descriptor_store_supported():
        return _new_result(
            "unsupported",
            "STORE_UNSUPPORTED",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    manifest = run_audit_manifest_bytes(bundle)
    manifest_digest = run_audit_bundle_sha256(bundle)
    object_values = {_sha(raw): raw for raw in (*run_audit_object_bytes(bundle), manifest)}
    if (
        len(object_values) > MAX_OBJECTS
        or sum(len(raw) for raw in object_values.values()) > MAX_AGGREGATE_BYTES
    ):
        return _new_result(
            "invalid",
            "STORE_BUDGET_EXCEEDED",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    try:
        record, record_identity = _record_bytes(bundle)
    except RunAuditStoreError as exc:
        if exc.kind != "budget":
            raise
        return _new_result(
            "invalid",
            "STORE_BUDGET_EXCEEDED",
            manifest_sha256=None,
            record_sha256=None,
            object_count=0,
        )
    store: _PinnedRoot | None = None
    try:
        store = _open_root(root, create=True)
        _fsync_directory(store, store.descriptor, capability_probe=True)
        required_buckets = sorted(
            {
                *(("objects", digest[:2]) for digest in object_values),
                ("runs", manifest_digest[:2]),
            }
        )
        for category, prefix in required_buckets:
            bucket = _open_bucket(store, category, prefix, create=True)
            try:
                _fsync_directory(store, bucket, capability_probe=True)
            finally:
                os.close(bucket)
        for digest in sorted(object_values):
            bucket = _open_bucket(store, "objects", digest, create=False)
            try:
                _write_immutable(store, bucket, digest, object_values[digest])
            finally:
                os.close(bucket)
        run_bucket = _open_bucket(store, "runs", manifest_digest, create=False)
        try:
            created = _write_immutable(
                store,
                run_bucket,
                manifest_digest,
                record,
                name_digest=manifest_digest,
            )
        finally:
            os.close(run_bucket)
        loaded = _load_from_root(store, manifest_digest)
        if run_audit_bundle_sha256(loaded) != manifest_digest:
            _fail("corrupt", "freshly loaded run identity differs")
        _guard_root(store)
        return _new_result(
            "stored" if created else "existing",
            "RUN_STORED" if created else "RUN_ALREADY_EXISTS",
            manifest_sha256=manifest_digest,
            record_sha256=record_identity,
            object_count=len(object_values),
        )
    except RunAuditStoreError as exc:
        if exc.kind == "unsupported":
            return _new_result(
                "unsupported",
                "STORE_UNSUPPORTED",
                manifest_sha256=None,
                record_sha256=None,
                object_count=0,
            )
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
    finally:
        if store is not None:
            store.close()


def _load_from_root(store: _PinnedRoot, manifest_sha256: str) -> RunAuditBundle:
    digest = _digest(manifest_sha256, "manifest_sha256")
    run_bucket = _open_bucket(store, "runs", digest, create=False)
    try:
        record_raw = _read_bounded(store, run_bucket, digest, MAX_RECORD_BYTES)
    finally:
        os.close(run_bucket)
    record = _parse_record(record_raw, digest)
    object_digests = tuple(str(item) for item in record["object_sha256s"])
    values: dict[str, bytes] = {}
    total = 0
    for object_digest in object_digests:
        bucket = _open_bucket(store, "objects", object_digest, create=False)
        try:
            raw = _read_exact(
                store,
                bucket,
                object_digest,
                object_digest,
                MAX_OBJECT_BYTES,
            )
        finally:
            os.close(bucket)
        total += len(raw)
        if total > MAX_AGGREGATE_BYTES:
            _fail("budget", "stored run aggregate exceeds budget")
        values[object_digest] = raw
    manifest = values[digest]
    objects = tuple(values[item] for item in object_digests if item != digest)
    bundle = _bundle_from_replayed_bytes(manifest, objects)
    if bundle.logical_report_sha256 != record["logical_report_sha256"]:
        _fail("corrupt", "stored logical report identity differs")
    _guard_root(store)
    return bundle


def load_run_audit(root: Path, manifest_sha256: str) -> RunAuditBundle:
    """Load one visible immutable run and freshly replay its exact bytes."""
    store = _open_root(root, create=False)
    try:
        _fsync_directory(store, store.descriptor, capability_probe=True)
        return _load_from_root(store, manifest_sha256)
    finally:
        store.close()


def list_run_audits(root: Path) -> tuple[str, ...]:
    """Return digest-sorted visible runs only after fresh complete replay."""
    store = _open_root(root, create=False)
    runs = -1
    try:
        _fsync_directory(store, store.descriptor, capability_probe=True)
        try:
            runs = _open_child_directory(store, store.descriptor, "runs", create=False)
        except RunAuditStoreError as exc:
            if exc.kind != "missing":
                raise
            _guard_root(store)
            return ()
        _guard_root(store)
        try:
            bucket_names = sorted(os.listdir(runs))
        except OSError as exc:
            _classify_io(exc, "cannot enumerate run store")
        identities: list[str] = []
        for bucket_name in bucket_names:
            if re.fullmatch(r"[0-9a-f]{2}", bucket_name) is None:
                _fail("corrupt", "run bucket name differs")
            bucket = _open_child_directory(store, runs, bucket_name, create=False)
            try:
                try:
                    entries = sorted(os.listdir(bucket))
                except OSError as exc:
                    _classify_io(exc, "cannot enumerate run bucket")
                for entry in entries:
                    if entry.startswith(".") and entry.endswith(".tmp"):
                        try:
                            info = os.stat(entry, dir_fd=bucket, follow_symlinks=False)
                        except OSError as exc:
                            _classify_io(exc, "cannot inspect run temporary")
                        _file_info(info)
                        match = re.fullmatch(r"\.([0-9a-f]{64})\.[0-9a-f]{16}\.tmp", entry)
                        if (
                            match is None
                            or match.group(1)[:2] != bucket_name
                            or info.st_size < 1
                            or info.st_size > MAX_RECORD_BYTES
                        ):
                            _fail("corrupt", "run temporary shape differs")
                        continue
                    if _DIGEST.fullmatch(entry) is None or entry[:2] != bucket_name:
                        _fail("corrupt", "run record filename differs")
                    identities.append(entry)
                    if len(identities) > MAX_RUNS:
                        _fail("budget", "run listing exceeds budget")
            finally:
                os.close(bucket)
        result = tuple(sorted(identities))
        if len(set(result)) != len(result):
            _fail("corrupt", "duplicate visible run identity")
        for digest in result:
            _load_from_root(store, digest)
        _guard_root(store)
        return result
    finally:
        if runs >= 0:
            os.close(runs)
        store.close()


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
        or value.object_count > MAX_OBJECTS
    ):
        _fail("result", "store result fields or identity differ")
    if value.status in {"stored", "existing", "loaded"}:
        _digest(value.manifest_sha256, "result.manifest_sha256")
        _digest(value.record_sha256, "result.record_sha256")
    elif (
        value.manifest_sha256 is not None
        or value.record_sha256 is not None
        or value.object_count != 0
    ):
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
