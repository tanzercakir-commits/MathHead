"""Non-authoritative atomic filesystem adapter for provenance bundles."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile

from mathhead.kernel.provenance import (
    MAX_MANIFEST_BYTES,
    MAX_OBJECT_BYTES,
    ProvenanceReplayResult,
    replay_provenance_bundle,
)


class ProvenanceStoreError(RuntimeError):
    """A classified refusal by the content-addressed filesystem adapter."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


def _fail(kind: str, detail: str) -> None:
    raise ProvenanceStoreError(kind, detail)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _valid_digest(value: object) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        _fail("identity", "bundle identity must be one lowercase SHA-256")
    return value


def _is_link_like(info: os.stat_result) -> bool:
    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & reparse_point
    )


def _ensure_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o755)
    except FileExistsError:
        pass
    except OSError as exc:
        _fail("io", f"cannot create store directory: {exc.__class__.__name__}")
    try:
        info = path.lstat()
    except OSError as exc:
        _fail("io", f"cannot inspect store directory: {exc.__class__.__name__}")
    if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
        _fail("path", "store component is not a real directory")


def _validate_directory_chain(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            info = current.lstat()
        except OSError as exc:
            _fail("io", f"cannot inspect store path: {exc.__class__.__name__}")
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "store path contains a link or non-directory component")


def _prepare_root(root: Path, *, create: bool) -> Path:
    if not isinstance(root, Path):
        _fail("type", "store root must be a pathlib.Path")
    if not root.is_absolute() or root == Path(root.anchor):
        _fail("path", "store root must be a non-root absolute path")
    if root != Path(os.path.normpath(str(root))):
        _fail("path", "store root must not contain parent traversal")
    if not create and not root.exists():
        _fail("missing", "store root does not exist")
    missing: list[Path] = []
    current = root
    while not current.exists():
        missing.append(current)
        if current.parent == current:
            _fail("path", "store root has no existing parent")
        current = current.parent
    try:
        info = current.lstat()
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "existing store ancestor is not a real directory")
    except OSError as exc:
        _fail("io", f"cannot inspect store ancestor: {exc.__class__.__name__}")
    if missing and not create:
        _fail("missing", "store root does not exist")
    for path in reversed(missing):
        _ensure_directory(path)
    if create:
        _ensure_directory(root)
    _validate_directory_chain(root)
    return root


def _child_directory(parent: Path, name: str, *, create: bool) -> Path:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        _fail("path", "unsafe derived directory component")
    path = parent / name
    if create:
        _ensure_directory(path)
    else:
        try:
            info = path.lstat()
        except OSError as exc:
            _fail("missing", f"store directory is absent: {exc.__class__.__name__}")
        if _is_link_like(info) or not stat.S_ISDIR(info.st_mode):
            _fail("path", "store component is not a real directory")
    return path


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


def _read_exact_file(path: Path, expected_digest: str, maximum: int) -> bytes:
    try:
        linked = path.lstat()
    except OSError as exc:
        _fail("io", f"cannot inspect content object: {exc.__class__.__name__}")
    if _is_link_like(linked) or not stat.S_ISREG(linked.st_mode):
        _fail("link", "content object path must name a regular file directly")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        _fail("io", f"cannot open content object: {exc.__class__.__name__}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            _fail("link", "content object must be a single-link regular file")
        if (linked.st_dev, linked.st_ino) != (before.st_dev, before.st_ino):
            _fail("mutation", "content object changed while it was opened")
        if before.st_size < 1 or before.st_size > maximum:
            _fail("budget", "content object size is outside bounds")
        if hasattr(os, "getuid") and before.st_uid != os.getuid():
            _fail("ownership", "content object has another owner")
        if before.st_mode & 0o222:
            _fail("mutation", "content object is writable")
        chunks: list[bytes] = []
        remaining = before.st_size
        while remaining:
            chunk = os.read(descriptor, min(1_048_576, remaining))
            if not chunk:
                _fail("truncated", "content object ended before its recorded size")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            _fail("mutation", "content object grew during reading")
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
        ):
            _fail("mutation", "content object changed during reading")
    finally:
        os.close(descriptor)
    data = b"".join(chunks)
    if _digest(data) != expected_digest:
        _fail("identity", "content object SHA-256 differs from its path")
    return data


def _atomic_immutable_write(path: Path, data: bytes) -> None:
    expected = _digest(data)
    if path.exists() or path.is_symlink():
        existing = _read_exact_file(path, expected, max(len(data), 1))
        if existing != data:
            _fail("collision", "existing content-addressed file has different bytes")
        return
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=".mathhead-tmp-", dir=path.parent)
    except OSError as exc:
        _fail("io", f"cannot create temporary content object: {exc.__class__.__name__}")
    temporary = Path(temporary_name)
    installed = False
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
            installed = True
        except FileExistsError:
            existing = _read_exact_file(path, expected, max(len(data), 1))
            if existing != data:
                _fail("collision", "concurrent content write differs")
        except OSError as exc:
            _fail("io", f"cannot commit content object: {exc.__class__.__name__}")
        if installed:
            try:
                temporary.unlink()
                os.chmod(path, 0o444)
            except OSError as exc:
                _fail("io", f"cannot seal content object: {exc.__class__.__name__}")
        _fsync_directory(path.parent)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            if not installed:
                _fail("io", "cannot clean uncommitted temporary object")


def _object_path(root: Path, digest: str, *, create: bool) -> Path:
    objects = _child_directory(root, "objects", create=create)
    fanout = _child_directory(objects, digest[:2], create=create)
    return fanout / digest[2:]


def _bundle_directory(root: Path, digest: str, *, create: bool) -> Path:
    bundles = _child_directory(root, "bundles", create=create)
    fanout = _child_directory(bundles, digest[:2], create=create)
    return _child_directory(fanout, digest[2:], create=create)


def persist_replay_bundle(root: Path, manifest: bytes, objects: tuple[bytes, ...]) -> str:
    """Persist one structurally complete replay bundle; never grant authority."""
    result = replay_provenance_bundle(manifest, objects)
    if not result.bundle_complete or result.verdict in {"invalid", "exhausted"}:
        _fail("ineligible", f"bundle is not structurally persistable: {result.reason_code}")
    assert result.bundle_sha256 is not None
    store = _prepare_root(root, create=True)
    for data in objects:
        digest = _digest(data)
        _atomic_immutable_write(_object_path(store, digest, create=True), data)
    bundle = _bundle_directory(store, result.bundle_sha256, create=True)
    _atomic_immutable_write(bundle / "manifest.json", manifest)
    entries = sorted(path.name for path in bundle.iterdir())
    if entries != ["manifest.json"]:
        _fail("partial", "bundle directory contains unexpected state")
    return result.bundle_sha256


def load_replay_bundle(root: Path, manifest_sha256: str) -> ProvenanceReplayResult:
    """Load exact stored bytes and perform a fresh independent replay."""
    digest = _valid_digest(manifest_sha256)
    store = _prepare_root(root, create=False)
    bundle = _bundle_directory(store, digest, create=False)
    entries = sorted(path.name for path in bundle.iterdir())
    if entries != ["manifest.json"]:
        _fail("partial", "bundle directory is missing its sole commit marker")
    manifest = _read_exact_file(bundle / "manifest.json", digest, MAX_MANIFEST_BYTES)
    try:
        value = json.loads(manifest.decode("utf-8"))
        records = value["objects"]
        object_digests = [record["sha256"] for record in records]
    except (UnicodeError, ValueError, KeyError, TypeError, RecursionError) as exc:
        _fail("manifest", f"stored manifest cannot enumerate objects: {type(exc).__name__}")
    if type(object_digests) is not list or not all(type(item) is str for item in object_digests):
        _fail("manifest", "stored manifest object inventory is invalid")
    objects = tuple(
        _read_exact_file(
            _object_path(store, _valid_digest(item), create=False), item, MAX_OBJECT_BYTES
        )
        for item in object_digests
    )
    result = replay_provenance_bundle(manifest, objects)
    if not result.bundle_complete or result.bundle_sha256 != digest:
        _fail("replay", f"stored bundle failed fresh replay: {result.reason_code}")
    return result
