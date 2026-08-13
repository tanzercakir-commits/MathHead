"""Immutable descriptor-relative persistence for governed safe-cache entries."""

from __future__ import annotations

from dataclasses import dataclass, fields
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock
from types import MappingProxyType
from typing import Any, Final, NoReturn

from .run_audit import RunAuditBundle, RunAuditValidationError
from .run_audit_store import RunAuditStoreError, load_run_audit
from .safe_cache import (
    CONTRACT_SHA256 as SAFE_CACHE_CONTRACT_SHA256,
    SafeCacheDecision,
    SafeCacheEntry,
    decide_safe_cache,
    parse_safe_cache_entry,
    safe_cache_entry_bytes,
)


STORE_CONTRACT_ID: Final = "MH-C-SAFE-CACHE-STORE-001"
STORE_CONTRACT_SHA256: Final = (
    "1f1dba767275ce066a977fe5eda2e499da7faf6135e1f11ac8db3587e2337cd1"
)
STORE_RECORD_SCHEMA: Final = "mathhead.safe-cache-store-record.v1"
STORE_RESULT_SCHEMA: Final = "mathhead.safe-cache-store-result.v1"
SCHEMA_SHA256S: Final = MappingProxyType({
    STORE_RECORD_SCHEMA: "959e5f08b002479753fa14210e39dbc594c529177e6923866b0c6911c29ef001",
    STORE_RESULT_SCHEMA: "0c9a2c429522b44fb51728e5c6491e6f2379e2fcd544a6c4c7eca552a2a9a4ca",
})

MAX_OBJECT_BYTES: Final = 67_108_864
MAX_RECORD_BYTES: Final = 67_108_864
MAX_RESULT_BYTES: Final = 67_108_864
MAX_KEYS: Final = 1_000_000
MAX_PATH_COMPONENTS: Final = 128
MAX_PATH_CODEPOINTS: Final = 32_768

_DIGEST = re.compile(r"[0-9a-f]{64}")
_REASON = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
_INSTALL_LOCK = RLock()
_TEMP_SEQUENCE = 0
_UNSUPPORTED_ERRNOS = {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}


class SafeCacheStoreError(RuntimeError):
    """Strict cache-store path, state, or access failure."""

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
            raise TypeError("safe-cache store values are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class SafeCacheStoreResult(_StoreValue):
    schema: str
    contract_id: str
    contract_sha256: str
    operation: str
    status: str
    reason_code: str
    lookup_key_sha256: str | None
    entry_sha256: str | None
    audit_manifest_sha256: str | None
    record_sha256: str | None
    historical_authority_tier: str | None
    result_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("safe-cache store results are store-owned")


_PUBLIC_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


def _fail(kind: str, detail: str) -> NoReturn:
    raise SafeCacheStoreError(kind, detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(values: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _canonical(value: object, maximum: int = MAX_RECORD_BYTES) -> bytes:
    try:
        raw = (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        _fail("record", f"canonical encoding failed: {type(exc).__name__}")
    if len(raw) > maximum:
        _fail("budget", "canonical store value exceeds byte budget")
    return raw


def _parse(data: bytes) -> dict[str, object]:
    if type(data) is not bytes or not data or len(data) > MAX_RECORD_BYTES:
        _fail("budget", "store record bytes are outside bounds")
    try:
        value = json.loads(
            data.decode("utf-8"), object_pairs_hook=_pairs,
            parse_float=lambda _: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("constant")),
        )
    except _DuplicateKey as exc:
        _fail("record", f"duplicate record key {exc.args[0]!r}")
    except (UnicodeError, ValueError, RecursionError) as exc:
        _fail("record", f"invalid record JSON: {type(exc).__name__}")
    if type(value) is not dict or _canonical(value) != data:
        _fail("record", "record is not one canonical object")
    return value


def _digest(value: object, label: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        _fail("record", f"{label} is not one full lowercase SHA-256")
    return value


def _self_hash(value: dict[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage, MAX_RESULT_BYTES))


def _record_bytes(entry: SafeCacheEntry) -> tuple[bytes, str, str]:
    entry_raw = safe_cache_entry_bytes(entry)
    entry_object = _sha(entry_raw)
    value: dict[str, object] = {
        "schema": STORE_RECORD_SCHEMA,
        "safe_cache_contract_sha256": SAFE_CACHE_CONTRACT_SHA256,
        "safe_cache_store_contract_sha256": STORE_CONTRACT_SHA256,
        "lookup_key_sha256": entry.lookup_key_sha256,
        "entry_sha256": entry.entry_sha256,
        "entry_object_sha256": entry_object,
        "audit_manifest_sha256": entry.audit_manifest_sha256,
        "record_sha256": None,
        "mathematical_authority": False,
    }
    value["record_sha256"] = _self_hash(value, "record_sha256")
    return _canonical(value), str(value["record_sha256"]), entry_object


def _parse_record(data: bytes, expected_key: str) -> dict[str, object]:
    value = _parse(data)
    expected = {
        "schema", "safe_cache_contract_sha256", "safe_cache_store_contract_sha256",
        "lookup_key_sha256", "entry_sha256", "entry_object_sha256",
        "audit_manifest_sha256", "record_sha256", "mathematical_authority",
    }
    if set(value) != expected:
        _fail("record", "record field set differs")
    if (
        value["schema"] != STORE_RECORD_SCHEMA
        or value["safe_cache_contract_sha256"] != SAFE_CACHE_CONTRACT_SHA256
        or value["safe_cache_store_contract_sha256"] != STORE_CONTRACT_SHA256
        or value["mathematical_authority"] is not False
        or _digest(value["lookup_key_sha256"], "lookup_key_sha256") != expected_key
    ):
        _fail("record", "record contract or key binding differs")
    for name in (
        "entry_sha256", "entry_object_sha256", "audit_manifest_sha256", "record_sha256"
    ):
        _digest(value[name], name)
    if value["record_sha256"] != _self_hash(value, "record_sha256"):
        _fail("record", "record identity differs")
    return value


def _result_mapping(value: SafeCacheStoreResult, own_hash: bool = True) -> dict[str, object]:
    return {
        field.name: (None if field.name == "result_sha256" and not own_hash else getattr(value, field.name))
        for field in fields(SafeCacheStoreResult)
    }


def _shape(value: dict[str, object]) -> None:
    operation, status, reason = value["operation"], value["status"], value["reason_code"]
    lookup, entry = value["lookup_key_sha256"], value["entry_sha256"]
    manifest, record, tier = (
        value["audit_manifest_sha256"], value["record_sha256"],
        value["historical_authority_tier"],
    )
    full = all(item is not None for item in (lookup, entry, manifest, record, tier))
    if operation == "persist" and status in {"stored", "existing"}:
        if reason != ("CACHE_ENTRY_STORED" if status == "stored" else "CACHE_ENTRY_ALREADY_EXISTS") or not full:
            _fail("result", "persist success shape differs")
    elif operation == "lookup" and status == "hit":
        if reason != "CACHE_HIT" or not full:
            _fail("result", "lookup hit shape differs")
    elif operation == "lookup" and status == "miss":
        if reason != "CACHE_KEY_ABSENT" or lookup is None or any(item is not None for item in (entry, manifest, record, tier)):
            _fail("result", "lookup miss shape differs")
    elif operation == "persist" and status == "ineligible":
        if reason != "CACHE_RUN_INELIGIBLE" or lookup is None or manifest is None or any(item is not None for item in (entry, record, tier)):
            _fail("result", "persist ineligible shape differs")
    elif operation == "lookup" and status in {"stale", "corrupt"}:
        if lookup is None or any(item is not None for item in (entry, record, tier)):
            _fail("result", "lookup non-hit shape differs")
        if status == "stale" and (reason != "CACHE_ENTRY_STALE" or manifest is not None):
            _fail("result", "lookup stale shape differs")
        if status == "corrupt" and reason == "CACHE_ENTRY_CORRUPT" and manifest is not None:
            _fail("result", "entry corrupt shape differs")
        if status == "corrupt" and reason in {"CACHE_AUDIT_RUN_MISSING", "CACHE_AUDIT_REPLAY_INVALID"} and manifest is None:
            _fail("result", "audit corrupt shape differs")
        if status == "corrupt" and reason not in {
            "CACHE_ENTRY_CORRUPT", "CACHE_AUDIT_RUN_MISSING",
            "CACHE_AUDIT_REPLAY_INVALID",
        }:
            _fail("result", "lookup corrupt reason differs")
    elif operation == "persist" and status == "conflict":
        if reason != "CACHE_KEY_CONFLICT" or lookup is None or any(item is not None for item in (entry, manifest, record, tier)):
            _fail("result", "persist conflict shape differs")
    elif status == "invalid" and reason in {"CACHE_REQUEST_INVALID", "CACHE_PATH_INVALID"}:
        if any(item is not None for item in (lookup, entry, manifest, record, tier)):
            _fail("result", "input invalid shape differs")
    elif operation == "persist" and status == "invalid" and reason in {"CACHE_AUDIT_RUN_MISSING", "CACHE_AUDIT_REPLAY_INVALID"}:
        if lookup is None or manifest is None or any(item is not None for item in (entry, record, tier)):
            _fail("result", "persist audit invalid shape differs")
    elif status == "exhausted":
        if reason == "CACHE_CURRENT_BUDGET_EXHAUSTED":
            if any(item is not None for item in (lookup, entry, manifest, record, tier)):
                _fail("result", "current exhaustion shape differs")
        elif reason == "CACHE_STORE_BUDGET_EXHAUSTED":
            if lookup is None or entry is not None or record is not None or tier is not None or (operation == "persist") != (manifest is not None):
                _fail("result", "store exhaustion shape differs")
        else:
            _fail("result", "unknown exhaustion reason")
    elif status in {"unsupported", "io_error"}:
        expected = {
            ("unsupported", "CACHE_STORE_UNSUPPORTED"),
            ("unsupported", "CACHE_AUDIT_STORE_UNSUPPORTED"),
            ("io_error", "CACHE_STORE_IO_ERROR"),
            ("io_error", "CACHE_AUDIT_STORE_IO_ERROR"),
        }
        if (status, reason) not in expected or lookup is None or any(item is not None for item in (entry, record, tier)):
            _fail("result", "capability or I/O shape differs")
        audit_reason = reason in {
            "CACHE_AUDIT_STORE_UNSUPPORTED", "CACHE_AUDIT_STORE_IO_ERROR"
        }
        needs_manifest = operation == "persist" or audit_reason
        if needs_manifest != (manifest is not None):
            _fail("result", "capability or I/O manifest shape differs")
    else:
        _fail("result", "operation/status/reason pair differs")


def _new_result(
    operation: str, status: str, reason: str, *, lookup: str | None = None,
    entry: str | None = None, manifest: str | None = None, record: str | None = None,
    tier: str | None = None,
) -> SafeCacheStoreResult:
    value: dict[str, object] = {
        "schema": STORE_RESULT_SCHEMA, "contract_id": STORE_CONTRACT_ID,
        "contract_sha256": STORE_CONTRACT_SHA256, "operation": operation,
        "status": status, "reason_code": reason, "lookup_key_sha256": lookup,
        "entry_sha256": entry, "audit_manifest_sha256": manifest,
        "record_sha256": record, "historical_authority_tier": tier,
        "result_sha256": None, "mathematical_authority": False,
    }
    _shape(value)
    value["result_sha256"] = _self_hash(value, "result_sha256")
    return _make(SafeCacheStoreResult, **value)


def validate_safe_cache_store_result(value: SafeCacheStoreResult) -> None:
    if type(value) is not SafeCacheStoreResult:
        _fail("type", "expected exact SafeCacheStoreResult")
    mapping = _result_mapping(value)
    if (
        value.schema != STORE_RESULT_SCHEMA
        or value.contract_id != STORE_CONTRACT_ID
        or value.contract_sha256 != STORE_CONTRACT_SHA256
        or value.operation not in {"persist", "lookup"}
        or type(value.reason_code) is not str
        or _REASON.fullmatch(value.reason_code) is None
        or value.mathematical_authority is not False
        or value.result_sha256 != _self_hash(mapping, "result_sha256")
    ):
        _fail("result", "store result fields or identity differ")
    _digest(value.result_sha256, "result.result_sha256")
    for name in (
        "lookup_key_sha256", "entry_sha256", "audit_manifest_sha256", "record_sha256"
    ):
        item = getattr(value, name)
        if item is not None:
            _digest(item, f"result.{name}")
    if value.historical_authority_tier not in {None, "checker_attestation", "external_proof_assistant"}:
        _fail("result", "historical authority tier differs")
    _shape(mapping)


def _result_from_mapping(value: object) -> SafeCacheStoreResult:
    expected = {field.name for field in fields(SafeCacheStoreResult)}
    if type(value) is not dict or set(value) != expected:
        _fail("result", "store result field set differs")
    result = _make(SafeCacheStoreResult, **value)
    validate_safe_cache_store_result(result)
    return result


def parse_safe_cache_store_result(data: bytes) -> SafeCacheStoreResult:
    """Strictly parse and reconstruct one canonical store result."""
    return _result_from_mapping(_parse(data))


def safe_cache_store_result_bytes(value: SafeCacheStoreResult) -> bytes:
    validate_safe_cache_store_result(value)
    return _canonical(_result_mapping(value), MAX_RESULT_BYTES)


def _is_link_like(info: os.stat_result) -> bool:
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & reparse
    )


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


def _descriptor_store_supported() -> bool:
    required = {os.open, os.mkdir, os.stat, os.link, os.unlink}
    return (
        os.name == "posix" and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW") and hasattr(os, "fchmod")
        and required <= os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and os.link in os.supports_follow_symlinks
    )


def _classify_io(exc: OSError, detail: str) -> NoReturn:
    if exc.errno in _UNSUPPORTED_ERRNOS:
        _fail("unsupported", f"{detail}: {type(exc).__name__}")
    _fail("io", f"{detail}: {type(exc).__name__}")


def _directory_info(info: os.stat_result, *, private: bool) -> None:
    if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
        _fail("link", "cache component is not a real directory")
    if private and stat.S_IMODE(info.st_mode) != 0o700:
        _fail("mode", "cache directory mode is not exact private 0700")
    if private and hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        _fail("owner", "cache directory owner differs")


def _file_info(info: os.stat_result) -> None:
    if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
        _fail("link", "cache file is not a real regular file")
    if info.st_nlink != 1:
        _fail("link", "cache file has an unsafe hardlink count")
    if stat.S_IMODE(info.st_mode) != 0o600:
        _fail("mode", "cache file mode is not exact private 0600")
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        _fail("owner", "cache file owner differs")


def _guard_root(root: _PinnedRoot) -> None:
    for expected in root.chain:
        try:
            info = os.stat(expected.path, follow_symlinks=False)
        except OSError as exc:
            _fail("link", f"cache ancestor identity unavailable: {type(exc).__name__}")
        if (
            _is_link_like(info) or not stat.S_ISDIR(info.st_mode)
            or (info.st_dev, info.st_ino) != (expected.device, expected.inode)
        ):
            _fail("link", "cache ancestor identity changed")


def _validate_root_path(root: Path) -> None:
    if type(root) is not type(Path()):
        _fail("type", "root must be an exact concrete pathlib.Path")
    if (
        not root.is_absolute() or not root.anchor or root == Path(root.anchor)
        or len(root.parts) > MAX_PATH_COMPONENTS or len(str(root)) > MAX_PATH_CODEPOINTS
        or root != Path(os.path.normpath(str(root)))
    ):
        _fail("path", "root is relative, root, non-normalized, or over budget")


def _validate_roots(cache_root: Path, audit_root: Path) -> None:
    _validate_root_path(cache_root)
    _validate_root_path(audit_root)
    try:
        common = Path(os.path.commonpath((str(cache_root), str(audit_root))))
    except ValueError:
        return
    if common in {cache_root, audit_root}:
        _fail("path", "cache and audit roots overlap")


def _open_root(root: Path, *, create: bool) -> _PinnedRoot:
    _validate_root_path(root)
    if not _descriptor_store_supported():
        _fail("unsupported", "descriptor-relative no-follow operations unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = -1
    current = Path(root.anchor)
    chain: list[_DirectoryIdentity] = []
    try:
        descriptor = os.open(current, flags)
        info = os.fstat(descriptor)
        _directory_info(info, private=False)
        chain.append(_DirectoryIdentity(current, info.st_dev, info.st_ino))
        parts = root.parts[1:]
        for index, component in enumerate(parts):
            private = index == len(parts) - 1
            try:
                linked = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                if not create:
                    _fail("missing", "cache root does not exist")
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                except OSError as exc:
                    _classify_io(exc, "cannot create cache root")
                try:
                    linked = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                    os.fsync(descriptor)
                except OSError as exc:
                    _classify_io(exc, "cannot synchronize root creation")
            except OSError as exc:
                _classify_io(exc, "cannot inspect cache ancestor")
            _directory_info(linked, private=private)
            try:
                opened = os.open(component, flags, dir_fd=descriptor)
            except OSError as exc:
                _classify_io(exc, "cannot open cache ancestor")
            opened_info = os.fstat(opened)
            if (linked.st_dev, linked.st_ino) != (opened_info.st_dev, opened_info.st_ino):
                os.close(opened)
                _fail("link", "cache ancestor changed while opening")
            os.close(descriptor)
            descriptor = opened
            current /= component
            chain.append(_DirectoryIdentity(current, opened_info.st_dev, opened_info.st_ino))
        result = _PinnedRoot(root, descriptor, tuple(chain))
        _guard_root(result)
        return result
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise


def _fsync_directory(root: _PinnedRoot, descriptor: int, *, probe: bool = False) -> None:
    _guard_root(root)
    try:
        _directory_info(os.fstat(descriptor), private=True)
        os.fsync(descriptor)
    except OSError as exc:
        if not probe and exc.errno in _UNSUPPORTED_ERRNOS:
            _fail("io", f"directory synchronization failed after probe: {type(exc).__name__}")
        _classify_io(exc, "cannot synchronize cache directory")
    _guard_root(root)


def _open_child(root: _PinnedRoot, parent: int, name: str, *, create: bool) -> int:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        _fail("path", "derived cache component is unsafe")
    _guard_root(root)
    try:
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        if not create:
            _fail("missing", "cache component absent")
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
        except OSError as exc:
            _classify_io(exc, "cannot create cache component")
        try:
            linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
            _fsync_directory(root, parent, probe=True)
        except OSError as exc:
            _classify_io(exc, "cannot synchronize cache component creation")
    except OSError as exc:
        _classify_io(exc, "cannot inspect cache component")
    _directory_info(linked, private=True)
    try:
        descriptor = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
        )
    except OSError as exc:
        _classify_io(exc, "cannot open cache component")
    opened = os.fstat(descriptor)
    if (linked.st_dev, linked.st_ino) != (opened.st_dev, opened.st_ino):
        os.close(descriptor)
        _fail("link", "cache component changed while opening")
    try:
        _guard_root(root)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_bucket(root: _PinnedRoot, category: str, digest: str, *, create: bool) -> int:
    category_fd = _open_child(root, root.descriptor, category, create=create)
    try:
        return _open_child(root, category_fd, digest[:2], create=create)
    finally:
        os.close(category_fd)


def _read_bounded(root: _PinnedRoot, parent: int, name: str, maximum: int) -> bytes:
    _guard_root(root)
    try:
        linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
        _file_info(linked)
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    except FileNotFoundError:
        _fail("missing", "cache file absent")
    except OSError as exc:
        _classify_io(exc, "cannot open cache file")
    try:
        before = os.fstat(descriptor)
        if (linked.st_dev, linked.st_ino) != (before.st_dev, before.st_ino):
            _fail("link", "cache file changed while opening")
        _file_info(before)
        if before.st_size < 1 or before.st_size > maximum:
            _fail("budget", "cache file size outside bounds")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            try:
                chunk = os.read(descriptor, min(1_048_576, remaining))
            except OSError as exc:
                _classify_io(exc, "cannot read cache file")
            if not chunk:
                _fail("partial", "cache file ended early")
            chunks.append(chunk)
            remaining -= len(chunk)
        try:
            if os.read(descriptor, 1):
                _fail("corrupt", "cache file grew while read")
        except OSError as exc:
            _classify_io(exc, "cannot finish cache read")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (after.st_dev, after.st_ino, after.st_size):
            _fail("corrupt", "cache file changed while read")
        _guard_root(root)
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _read_exact(root: _PinnedRoot, parent: int, name: str, digest: str, maximum: int) -> bytes:
    raw = _read_bounded(root, parent, name, maximum)
    if _sha(raw) != digest:
        _fail("corrupt", "cache content digest differs")
    return raw


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    offset = 0
    while offset < len(view):
        try:
            count = os.write(descriptor, view[offset:])
        except OSError as exc:
            _fail("io", f"cannot write cache file: {type(exc).__name__}")
        if count <= 0:
            _fail("io", "cache write made no progress")
        offset += count


def _read_existing(root: _PinnedRoot, parent: int, name: str, data: bytes) -> None:
    for _attempt in range(10_000):
        try:
            if _read_bounded(root, parent, name, max(len(data), MAX_RECORD_BYTES)) != data:
                _fail("conflict", "existing immutable content differs")
            return
        except SafeCacheStoreError as exc:
            if exc.kind != "link" or not hasattr(os, "sched_yield"):
                raise
            os.sched_yield()
    _fail("link", "immutable target retained unsafe link count")


def _quarantine(root: _PinnedRoot, parent: int, target: str) -> None:
    descriptor = -1
    _guard_root(root)
    try:
        descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(descriptor)
        if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
            _fail("link", "uncommitted target is not regular")
        os.fchmod(descriptor, 0o000)
        os.fsync(descriptor)
    except OSError as exc:
        _fail("io", f"cannot quarantine uncommitted target: {type(exc).__name__}")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _guard_root(root)


def _rollback_visible_key(root: _PinnedRoot, key: str) -> None:
    """Make a newly installed key ineligible, then remove it."""
    bucket = _open_bucket(root, "keys", key, create=False)
    try:
        quarantined = False
        try:
            _quarantine(root, bucket, key)
            quarantined = True
        except SafeCacheStoreError:
            pass
        try:
            os.unlink(key, dir_fd=bucket)
        except OSError as exc:
            if not quarantined:
                descriptor = -1
                try:
                    descriptor = os.open(
                        key, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=bucket
                    )
                    info = os.fstat(descriptor)
                    if _is_link_like(info) or not stat.S_ISREG(info.st_mode):
                        _fail("link", "uncommitted key is not regular")
                    os.fchmod(descriptor, 0o000)
                    os.fsync(descriptor)
                    quarantined = True
                except OSError as fallback:
                    _fail(
                        "io",
                        "cannot make uncommitted key ineligible: "
                        f"{type(exc).__name__}/{type(fallback).__name__}",
                    )
                finally:
                    if descriptor >= 0:
                        os.close(descriptor)
            if not quarantined:
                _fail("io", "cannot make uncommitted key ineligible")
        _fsync_directory(root, bucket)
    finally:
        os.close(bucket)


def _write_immutable_locked(
    root: _PinnedRoot, parent: int, target: str, data: bytes,
    *, name_digest: str | None = None,
) -> bool:
    global _TEMP_SEQUENCE
    content_digest = _sha(data)
    identity = content_digest if name_digest is None else _digest(name_digest, "target")
    if target != identity:
        _fail("path", "immutable target name differs")
    _guard_root(root)
    try:
        os.stat(target, dir_fd=parent, follow_symlinks=False)
        existing = True
    except FileNotFoundError:
        existing = False
    except OSError as exc:
        _classify_io(exc, "cannot inspect immutable target")
    if existing:
        _read_existing(root, parent, target, data)
        return False
    descriptor = -1
    temporary: str | None = None
    try:
        for _attempt in range(10_000):
            sequence = _TEMP_SEQUENCE
            _TEMP_SEQUENCE += 1
            candidate = f".{identity}.{sequence:016x}.tmp"
            try:
                descriptor = os.open(
                    candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600, dir_fd=parent,
                )
                temporary = candidate
                break
            except FileExistsError:
                continue
            except OSError as exc:
                _classify_io(exc, "cannot create cache temporary")
        if descriptor < 0 or temporary is None:
            _fail("io", "cannot allocate bounded cache temporary")
        os.fchmod(descriptor, 0o600)
        _write_all(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        _guard_root(root)
        try:
            os.link(
                temporary, target, src_dir_fd=parent, dst_dir_fd=parent,
                follow_symlinks=False,
            )
            created = True
        except FileExistsError:
            created = False
        except OSError as exc:
            _classify_io(exc, "cannot install immutable cache content")
        try:
            os.unlink(temporary, dir_fd=parent)
        except OSError as exc:
            if created:
                try:
                    _quarantine(root, parent, target)
                    os.unlink(target, dir_fd=parent)
                    _fsync_directory(root, parent)
                except (OSError, SafeCacheStoreError):
                    temporary = None
            _classify_io(exc, "cannot clean cache temporary")
        temporary = None
        _read_existing(root, parent, target, data)
        try:
            _fsync_directory(root, parent)
        except SafeCacheStoreError:
            if created:
                try:
                    _quarantine(root, parent, target)
                    os.unlink(target, dir_fd=parent)
                    _fsync_directory(root, parent)
                except (OSError, SafeCacheStoreError):
                    pass
            raise
        return created
    except OSError as exc:
        _classify_io(exc, "cache immutable installation failed")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary, dir_fd=parent)
            except OSError:
                pass


def _write_immutable(
    root: _PinnedRoot, parent: int, target: str, data: bytes,
    *, name_digest: str | None = None,
) -> bool:
    with _INSTALL_LOCK:
        return _write_immutable_locked(
            root, parent, target, data, name_digest=name_digest
        )


def _target_present(root: _PinnedRoot, parent: int, target: str) -> bool:
    _guard_root(root)
    try:
        os.stat(target, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as exc:
        _classify_io(exc, "cannot inspect cache commit target")
    return True


def _current_decision(args: tuple[object, ...]) -> SafeCacheDecision:
    return decide_safe_cache(*args, None)


def _decision_failure(operation: str, decision: SafeCacheDecision) -> SafeCacheStoreResult:
    if decision.status == "exhausted":
        return _new_result(operation, "exhausted", "CACHE_CURRENT_BUDGET_EXHAUSTED")
    return _new_result(operation, "invalid", "CACHE_REQUEST_INVALID")


def _historical_inputs(bundle: RunAuditBundle) -> tuple[object, ...]:
    manifest = json.loads(bundle.manifest)
    objects = {_sha(raw): raw for raw in bundle.objects}
    records = manifest.get("objects")
    if type(records) is not list:
        _fail("corrupt", "audit manifest object records absent")
    by_role: dict[str, list[dict[str, object]]] = {}
    for record in records:
        if type(record) is not dict or type(record.get("role")) is not str:
            _fail("corrupt", "audit object record differs")
        by_role.setdefault(str(record["role"]), []).append(record)

    def one(role: str) -> bytes:
        matches = by_role.get(role, [])
        if len(matches) != 1:
            _fail("corrupt", f"historical {role} closure differs")
        raw = objects.get(str(matches[0].get("sha256")))
        if raw is None:
            _fail("corrupt", f"historical {role} bytes absent")
        return raw

    portfolio_request = json.loads(one("portfolio_request"))
    artifact_bindings = portfolio_request.get("artifact_bindings")
    if type(artifact_bindings) is not list:
        _fail("corrupt", "historical artifact bindings absent")
    artifacts: list[bytes] = []
    for binding in artifact_bindings:
        if type(binding) is not dict:
            _fail("corrupt", "historical artifact binding differs")
        raw = objects.get(str(binding.get("sha256")))
        if raw is None:
            _fail("corrupt", "historical artifact bytes absent")
        artifacts.append(raw)
    descriptors = tuple(
        objects[str(item["sha256"])] for item in by_role.get("plugin_descriptor", [])
    )
    bindings = tuple(
        objects[str(item["sha256"])] for item in by_role.get("execution_binding", [])
    )
    return (
        one("planning_request"), one("capability_route_result"),
        one("portfolio_request"), one("planning_result"),
        one("initial_parent_budget"), descriptors, bindings, tuple(artifacts),
    )


def _load_entry(root: _PinnedRoot, key: str) -> tuple[dict[str, object], SafeCacheEntry]:
    key_bucket = _open_bucket(root, "keys", key, create=False)
    try:
        record_raw = _read_bounded(root, key_bucket, key, MAX_RECORD_BYTES)
    finally:
        os.close(key_bucket)
    record = _parse_record(record_raw, key)
    object_digest = str(record["entry_object_sha256"])
    object_bucket = _open_bucket(root, "objects", object_digest, create=False)
    try:
        entry_raw = _read_exact(
            root, object_bucket, object_digest, object_digest, MAX_OBJECT_BYTES
        )
    finally:
        os.close(object_bucket)
    try:
        entry = parse_safe_cache_entry(entry_raw)
    except ValueError as exc:
        _fail("corrupt", f"stored entry codec rejected bytes: {type(exc).__name__}")
    if (
        entry.lookup_key_sha256 != key
        or entry.entry_sha256 != record["entry_sha256"]
        or entry.audit_manifest_sha256 != record["audit_manifest_sha256"]
    ):
        _fail("corrupt", "record and entry cross-links differ")
    _guard_root(root)
    return record, entry


def _map_audit_error(
    operation: str, exc: RunAuditStoreError, lookup: str, manifest: str,
) -> SafeCacheStoreResult:
    if exc.kind == "missing":
        status = "invalid" if operation == "persist" else "corrupt"
        return _new_result(
            operation, status, "CACHE_AUDIT_RUN_MISSING",
            lookup=lookup, manifest=manifest,
        )
    if exc.kind == "unsupported":
        return _new_result(
            operation, "unsupported", "CACHE_AUDIT_STORE_UNSUPPORTED",
            lookup=lookup, manifest=manifest,
        )
    if exc.kind in {"budget", "corrupt", "record", "partial", "link", "mode", "owner"}:
        status = "invalid" if operation == "persist" else "corrupt"
        return _new_result(
            operation, status, "CACHE_AUDIT_REPLAY_INVALID",
            lookup=lookup, manifest=manifest,
        )
    return _new_result(
        operation, "io_error", "CACHE_AUDIT_STORE_IO_ERROR",
        lookup=lookup, manifest=manifest,
    )


def _map_audit_validation_error(
    operation: str, lookup: str, manifest: str,
) -> SafeCacheStoreResult:
    return _new_result(
        operation, "invalid" if operation == "persist" else "corrupt",
        "CACHE_AUDIT_REPLAY_INVALID", lookup=lookup, manifest=manifest,
    )


def lookup_safe_cache(
    cache_root: Path,
    audit_root: Path,
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> SafeCacheStoreResult:
    """Look up one exact current key and freshly replay its historical run."""
    try:
        _validate_roots(cache_root, audit_root)
    except SafeCacheStoreError:
        return _new_result("lookup", "invalid", "CACHE_PATH_INVALID")
    args: tuple[object, ...] = (
        planning_request, route_result, portfolio_request, planning_result,
        parent_budget, descriptors, bindings, artifacts,
    )
    current = _current_decision(args)
    if current.status != "miss" or current.lookup_key_sha256 is None:
        return _decision_failure("lookup", current)
    key = current.lookup_key_sha256
    if not _descriptor_store_supported():
        return _new_result(
            "lookup", "unsupported", "CACHE_STORE_UNSUPPORTED", lookup=key
        )
    store: _PinnedRoot | None = None
    try:
        try:
            store = _open_root(cache_root, create=False)
        except SafeCacheStoreError as exc:
            if exc.kind == "missing":
                return _new_result("lookup", "miss", "CACHE_KEY_ABSENT", lookup=key)
            raise
        _fsync_directory(store, store.descriptor, probe=True)
        try:
            record, entry = _load_entry(store, key)
        except SafeCacheStoreError as exc:
            if exc.kind == "missing":
                return _new_result("lookup", "miss", "CACHE_KEY_ABSENT", lookup=key)
            if exc.kind in {"record", "corrupt", "partial", "link", "mode"}:
                return _new_result(
                    "lookup", "corrupt", "CACHE_ENTRY_CORRUPT", lookup=key
                )
            if exc.kind == "budget":
                return _new_result(
                    "lookup", "exhausted", "CACHE_STORE_BUDGET_EXHAUSTED",
                    lookup=key,
                )
            raise
        manifest = entry.audit_manifest_sha256
        try:
            bundle = load_run_audit(audit_root, manifest)
        except RunAuditStoreError as exc:
            return _map_audit_error("lookup", exc, key, manifest)
        except RunAuditValidationError:
            return _map_audit_validation_error("lookup", key, manifest)
        decision = decide_safe_cache(*args, bundle)
        if decision.status != "hit" or decision.entry is None:
            return _new_result(
                "lookup", "stale", "CACHE_ENTRY_STALE", lookup=key
            )
        if safe_cache_entry_bytes(decision.entry) != safe_cache_entry_bytes(entry):
            return _new_result(
                "lookup", "stale", "CACHE_ENTRY_STALE", lookup=key
            )
        _guard_root(store)
        return _new_result(
            "lookup", "hit", "CACHE_HIT", lookup=key,
            entry=entry.entry_sha256, manifest=manifest,
            record=str(record["record_sha256"]),
            tier=entry.historical_authority_tier,
        )
    except SafeCacheStoreError as exc:
        if exc.kind == "unsupported":
            return _new_result(
                "lookup", "unsupported", "CACHE_STORE_UNSUPPORTED", lookup=key
            )
        if exc.kind == "budget":
            return _new_result(
                "lookup", "exhausted", "CACHE_STORE_BUDGET_EXHAUSTED", lookup=key
            )
        return _new_result(
            "lookup", "io_error", "CACHE_STORE_IO_ERROR", lookup=key
        )
    finally:
        if store is not None:
            store.close()


def persist_safe_cache(
    cache_root: Path,
    audit_root: Path,
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    manifest_sha256: str,
) -> SafeCacheStoreResult:
    """Persist one eligible audited run under its exact current key."""
    try:
        _validate_roots(cache_root, audit_root)
    except SafeCacheStoreError:
        return _new_result("persist", "invalid", "CACHE_PATH_INVALID")
    args: tuple[object, ...] = (
        planning_request, route_result, portfolio_request, planning_result,
        parent_budget, descriptors, bindings, artifacts,
    )
    current = _current_decision(args)
    if current.status != "miss" or current.lookup_key_sha256 is None:
        return _decision_failure("persist", current)
    key = current.lookup_key_sha256
    if type(manifest_sha256) is not str or _DIGEST.fullmatch(manifest_sha256) is None:
        return _new_result("persist", "invalid", "CACHE_REQUEST_INVALID")
    try:
        bundle = load_run_audit(audit_root, manifest_sha256)
    except RunAuditStoreError as exc:
        return _map_audit_error("persist", exc, key, manifest_sha256)
    except RunAuditValidationError:
        return _map_audit_validation_error("persist", key, manifest_sha256)
    decision = decide_safe_cache(*args, bundle)
    if decision.status == "ineligible":
        return _new_result(
            "persist", "ineligible", "CACHE_RUN_INELIGIBLE",
            lookup=key, manifest=manifest_sha256,
        )
    if decision.status != "hit" or decision.entry is None:
        return _new_result(
            "persist", "invalid", "CACHE_AUDIT_REPLAY_INVALID",
            lookup=key, manifest=manifest_sha256,
        )
    entry = decision.entry
    if not _descriptor_store_supported():
        return _new_result(
            "persist", "unsupported", "CACHE_STORE_UNSUPPORTED",
            lookup=key, manifest=manifest_sha256,
        )
    try:
        record_raw, record_identity, entry_object = _record_bytes(entry)
        entry_raw = safe_cache_entry_bytes(entry)
    except SafeCacheStoreError:
        return _new_result(
            "persist", "exhausted", "CACHE_STORE_BUDGET_EXHAUSTED",
            lookup=key, manifest=manifest_sha256,
        )
    store: _PinnedRoot | None = None
    try:
        store = _open_root(cache_root, create=True)
        _fsync_directory(store, store.descriptor, probe=True)
        for category, identity in (("objects", entry_object), ("keys", key)):
            bucket = _open_bucket(store, category, identity, create=True)
            try:
                _fsync_directory(store, bucket, probe=True)
            finally:
                os.close(bucket)
        object_bucket = _open_bucket(store, "objects", entry_object, create=False)
        try:
            _write_immutable(store, object_bucket, entry_object, entry_raw)
        finally:
            os.close(object_bucket)
        key_bucket = _open_bucket(store, "keys", key, create=False)
        key_preexisting = True
        try:
            try:
                with _INSTALL_LOCK:
                    key_preexisting = _target_present(store, key_bucket, key)
                    created = _write_immutable(
                        store, key_bucket, key, record_raw, name_digest=key
                    )
                    loaded_record, loaded_entry = _load_entry(store, key)
                    if (
                        safe_cache_entry_bytes(loaded_entry) != entry_raw
                        or loaded_record["record_sha256"] != record_identity
                    ):
                        _fail("corrupt", "freshly installed cache entry differs")
                    try:
                        loaded_bundle = load_run_audit(audit_root, manifest_sha256)
                    except RunAuditStoreError as exc:
                        if created:
                            _rollback_visible_key(store, key)
                        return _map_audit_error(
                            "persist", exc, key, manifest_sha256
                        )
                    except RunAuditValidationError:
                        if created:
                            _rollback_visible_key(store, key)
                        return _map_audit_validation_error(
                            "persist", key, manifest_sha256
                        )
                    verified = decide_safe_cache(*args, loaded_bundle)
                    if (
                        verified.status != "hit"
                        or verified.entry is None
                        or safe_cache_entry_bytes(verified.entry) != entry_raw
                    ):
                        _fail("corrupt", "post-install fresh hit differs")
                    _guard_root(store)
                    return _new_result(
                        "persist", "stored" if created else "existing",
                        "CACHE_ENTRY_STORED"
                        if created else "CACHE_ENTRY_ALREADY_EXISTS",
                        lookup=key, entry=entry.entry_sha256,
                        manifest=manifest_sha256, record=record_identity,
                        tier=entry.historical_authority_tier,
                    )
            except BaseException:
                if not key_preexisting:
                    try:
                        _rollback_visible_key(store, key)
                    except SafeCacheStoreError:
                        pass
                raise
        finally:
            os.close(key_bucket)
    except SafeCacheStoreError as exc:
        if exc.kind == "conflict":
            return _new_result(
                "persist", "conflict", "CACHE_KEY_CONFLICT", lookup=key
            )
        if exc.kind == "unsupported":
            return _new_result(
                "persist", "unsupported", "CACHE_STORE_UNSUPPORTED",
                lookup=key, manifest=manifest_sha256,
            )
        if exc.kind == "budget":
            return _new_result(
                "persist", "exhausted", "CACHE_STORE_BUDGET_EXHAUSTED",
                lookup=key, manifest=manifest_sha256,
            )
        return _new_result(
            "persist", "io_error", "CACHE_STORE_IO_ERROR",
            lookup=key, manifest=manifest_sha256,
        )
    finally:
        if store is not None:
            store.close()


def list_safe_cache(cache_root: Path, audit_root: Path) -> tuple[str, ...]:
    """List structurally and historically valid immutable cache keys."""
    _validate_roots(cache_root, audit_root)
    store = _open_root(cache_root, create=False)
    keys_fd = -1
    try:
        _fsync_directory(store, store.descriptor, probe=True)
        try:
            keys_fd = _open_child(store, store.descriptor, "keys", create=False)
        except SafeCacheStoreError as exc:
            if exc.kind != "missing":
                raise
            _guard_root(store)
            return ()
        try:
            buckets = sorted(os.listdir(keys_fd))
        except OSError as exc:
            _classify_io(exc, "cannot enumerate cache keys")
        identities: list[str] = []
        for bucket_name in buckets:
            if re.fullmatch(r"[0-9a-f]{2}", bucket_name) is None:
                _fail("corrupt", "cache key bucket name differs")
            bucket = _open_child(store, keys_fd, bucket_name, create=False)
            try:
                try:
                    entries = sorted(os.listdir(bucket))
                except OSError as exc:
                    _classify_io(exc, "cannot enumerate cache key bucket")
                for entry in entries:
                    if entry.startswith(".") and entry.endswith(".tmp"):
                        info = os.stat(entry, dir_fd=bucket, follow_symlinks=False)
                        _file_info(info)
                        match = re.fullmatch(r"\.([0-9a-f]{64})\.[0-9a-f]{16}\.tmp", entry)
                        if match is None or match.group(1)[:2] != bucket_name or not 1 <= info.st_size <= MAX_RECORD_BYTES:
                            _fail("corrupt", "cache temporary shape differs")
                        continue
                    if _DIGEST.fullmatch(entry) is None or entry[:2] != bucket_name:
                        _fail("corrupt", "cache key filename differs")
                    identities.append(entry)
                    if len(identities) > MAX_KEYS:
                        _fail("budget", "cache listing exceeds key budget")
            finally:
                os.close(bucket)
        result = tuple(sorted(identities))
        if len(set(result)) != len(result):
            _fail("corrupt", "duplicate visible cache key")
        for key in result:
            _record_value, entry = _load_entry(store, key)
            try:
                bundle = load_run_audit(audit_root, entry.audit_manifest_sha256)
            except RunAuditStoreError as exc:
                _fail("corrupt", f"listed audit run rejected: {exc.kind}")
            except RunAuditValidationError:
                _fail("corrupt", "listed audit replay rejected")
            historical = decide_safe_cache(*_historical_inputs(bundle), bundle)
            if historical.status != "hit" or historical.entry is None or safe_cache_entry_bytes(historical.entry) != safe_cache_entry_bytes(entry):
                _fail("corrupt", "listed historical cache relation differs")
        _guard_root(store)
        return result
    finally:
        if keys_fd >= 0:
            os.close(keys_fd)
        store.close()


__all__ = [
    "SCHEMA_SHA256S", "STORE_CONTRACT_ID", "STORE_CONTRACT_SHA256",
    "STORE_RECORD_SCHEMA", "STORE_RESULT_SCHEMA", "SafeCacheStoreError",
    "SafeCacheStoreResult", "persist_safe_cache", "lookup_safe_cache",
    "list_safe_cache", "parse_safe_cache_store_result", "safe_cache_store_result_bytes",
    "validate_safe_cache_store_result",
]
