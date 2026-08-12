"""Pinned external Lean execution boundary for MH-036.

The exporter is deliberately pure and non-authoritative.  This module owns the
filesystem and process effects required to ask the separately pinned Lean
kernel to check one exact generated theorem.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any, NoReturn

from mathhead.proof_assistant.export import (
    LAKEFILE_BYTES,
    LAKE_EXECUTABLE_SHA256,
    LAKE_MANIFEST_BYTES,
    LEAN_COMMIT,
    LEAN_EXECUTABLE_SHA256,
    LEAN_PLATFORM,
    LEAN_TOOLCHAIN,
    LEAN_TOOLCHAIN_BYTES,
    LeanExport,
    LeanVerificationValidationError,
    MATHLIB_COMMIT,
    MAX_OUTPUT_BYTES,
    MAX_TOTAL_SECONDS,
    TOOLCHAIN_LOCK_BYTES,
    parse_lean_export,
    validate_lean_export,
)


LEAN_VERIFICATION_CONTRACT_ID = "MH-C-LEAN-VERIFICATION-001"
LEAN_VERIFICATION_CONTRACT_SHA256 = (
    "b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a"
)
LEAN_RESULT_SCHEMA = "mathhead.lean-verification-result.v1"
_FRESH_AUTHORITY = object()
_PROJECT_FILES = {
    "lake-manifest.json": LAKE_MANIFEST_BYTES,
    "lakefile.toml": LAKEFILE_BYTES,
    "lean-toolchain": LEAN_TOOLCHAIN_BYTES,
    "mathhead-lean-lock.json": TOOLCHAIN_LOCK_BYTES,
}
_SOURCE_PATH = Path("MathHead") / "Generated.lean"
_OUTPUT_PATH = Path(".lake") / "build" / "lib" / "lean" / "MathHead" / "Generated.olean"
_COMMAND = (
    "env",
    "lean",
    "-o",
    str(_OUTPUT_PATH).replace(os.sep, "/"),
    str(_SOURCE_PATH).replace(os.sep, "/"),
)
_LEAN_VERSION_BYTES = (
    b"Lean (version 4.33.0, x86_64-unknown-linux-gnu, commit "
    + LEAN_COMMIT.encode("ascii")
    + b", Release)\n"
)
_DEPENDENCY_NAMES = (
    "Cli",
    "LeanSearchClient",
    "Qq",
    "aesop",
    "batteries",
    "importGraph",
    "mathlib",
    "plausible",
    "proofwidgets",
)
_MAX_EXECUTABLE_BYTES = 16_777_216
_MAX_COMPILED_BYTES = 67_108_864


@dataclass(frozen=True, slots=True, init=False)
class LeanVerificationResult:
    authority: str
    checker_result_sha256: str | None
    compiled_artifact_sha256: str | None
    contract_id: str
    contract_sha256: str
    diagnostic: str
    exact: bool
    exit_code: int | None
    lake_executable_sha256: str | None
    lean_executable_sha256: str | None
    lean_version_sha256: str | None
    project_sha256: str | None
    proof_term_sha256: str | None
    reason_code: str
    request_sha256: str | None
    source_sha256: str | None
    status: str
    stderr_bytes: int
    stderr_sha256: str | None
    stdout_bytes: int
    stdout_sha256: str | None
    toolchain: tuple[str, str, str, str]
    verdict: str
    _fresh_authority: object | None
    _stdout: bytes | None
    _stderr: bytes | None
    _compiled_artifact: bytes | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("Lean verification results are runner-owned")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("LeanVerificationResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("Lean verification results cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Lean verification results cannot be pickled")

    def __copy__(self) -> LeanVerificationResult:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> LeanVerificationResult:
        del memo
        return self


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: object) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, ValueError, OverflowError) as exc:
        raise LeanVerificationValidationError(
            "canonical", f"canonical JSON encoding failed: {type(exc).__name__}"
        ) from exc
    return encoded + b"\n"


def _toolchain_tuple() -> tuple[str, str, str, str]:
    return (LEAN_COMMIT, LEAN_TOOLCHAIN, MATHLIB_COMMIT, LEAN_PLATFORM)


def _new_result(
    export: LeanExport | None,
    *,
    status: str,
    reason_code: str,
    diagnostic: str,
    verdict: str,
    exit_code: int | None = None,
    lake_digest: str | None = None,
    lean_digest: str | None = None,
    version_digest: str | None = None,
    stdout: bytes | None = None,
    stderr: bytes | None = None,
    compiled: bytes | None = None,
    fresh: bool = False,
) -> LeanVerificationResult:
    value = object.__new__(LeanVerificationResult)
    authority = "external_proof_assistant" if status == "externally_verified" else "none"
    fields: dict[str, object] = {
        "_compiled_artifact": compiled,
        "_fresh_authority": _FRESH_AUTHORITY if fresh else None,
        "_stderr": stderr,
        "_stdout": stdout,
        "authority": authority,
        "checker_result_sha256": None if export is None else export.checker_result_sha256,
        "compiled_artifact_sha256": None if compiled is None else _sha256(compiled),
        "contract_id": LEAN_VERIFICATION_CONTRACT_ID,
        "contract_sha256": LEAN_VERIFICATION_CONTRACT_SHA256,
        "diagnostic": diagnostic,
        "exact": True,
        "exit_code": exit_code,
        "lake_executable_sha256": lake_digest,
        "lean_executable_sha256": lean_digest,
        "lean_version_sha256": version_digest,
        "project_sha256": None if export is None else export.project_sha256,
        "proof_term_sha256": None if export is None else export.proof_term_sha256,
        "reason_code": reason_code,
        "request_sha256": None if export is None else export.request_sha256,
        "source_sha256": None if export is None else export.source_sha256,
        "status": status,
        "stderr_bytes": 0 if stderr is None else len(stderr),
        "stderr_sha256": None if stderr is None else _sha256(stderr),
        "stdout_bytes": 0 if stdout is None else len(stdout),
        "stdout_sha256": None if stdout is None else _sha256(stdout),
        "toolchain": _toolchain_tuple(),
        "verdict": verdict,
    }
    for name, field in fields.items():
        object.__setattr__(value, name, field)
    validate_lean_verification_result(value, require_fresh=fresh)
    return value


def export_written_result(export: LeanExport) -> LeanVerificationResult:
    """Record that canonical source exists without claiming an external check."""
    validate_lean_export(export)
    return _new_result(
        export,
        status="export_written",
        reason_code="EXPORT_WRITTEN",
        diagnostic="canonical Lean export written; external check not run",
        verdict="unsupported",
    )


def _rejected_export_result(export: LeanExport, diagnostic: str) -> LeanVerificationResult:
    """Return a closed non-authoritative failure for an internal dispatch guard."""
    validate_lean_export(export)
    return _new_result(
        export,
        status="check_failed",
        reason_code="CHECK_FAILED",
        diagnostic=diagnostic[:512],
        verdict="invalid",
    )


def _regular_file_bytes(
    path: Path,
    expected: bytes | None,
    label: str,
    *,
    max_bytes: int = _MAX_COMPILED_BYTES,
) -> bytes:
    try:
        before = path.lstat()
    except OSError as exc:
        raise LeanVerificationValidationError("path", f"{label} is unavailable") from exc
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise LeanVerificationValidationError("path", f"{label} is not one regular file")
    limit = len(expected) if expected is not None else max_bytes
    if before.st_size > limit or (expected is not None and before.st_size != limit):
        raise LeanVerificationValidationError("budget", f"{label} length differs or exceeds its limit")
    try:
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            data = handle.read(limit + 1)
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise LeanVerificationValidationError("path", f"{label} cannot be read") from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        or (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        or len(data) != after.st_size
        or len(data) > limit
    ):
        raise LeanVerificationValidationError("path", f"{label} changed while opened")
    if expected is not None and data != expected:
        raise LeanVerificationValidationError("identity", f"{label} bytes differ")
    return data


def _real_directory(root: Path, relative: Path, label: str, *, create: bool) -> Path:
    """Resolve one root-owned directory chain without following links."""
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise LeanVerificationValidationError("path", f"{label} path is invalid")
    current = root
    for component in relative.parts:
        current = current / component
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if not create:
                raise LeanVerificationValidationError("path", f"{label} is unavailable") from None
            try:
                current.mkdir(mode=0o700)
                metadata = current.lstat()
            except OSError as exc:
                raise LeanVerificationValidationError(
                    "path", f"{label} cannot be created"
                ) from exc
        except OSError as exc:
            raise LeanVerificationValidationError("path", f"{label} is unavailable") from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise LeanVerificationValidationError(
                "path", f"{label} contains a non-directory or link"
            )
    try:
        current.relative_to(root)
    except ValueError as exc:  # pragma: no cover - guarded by lexical construction above
        raise LeanVerificationValidationError("path", f"{label} escapes the project root") from exc
    return current


def _empty_runtime_directory(root: Path, relative: Path, label: str) -> Path:
    directory = _real_directory(root, relative, label, create=True)
    try:
        with os.scandir(directory) as entries:
            if next(entries, None) is not None:
                raise LeanVerificationValidationError(
                    "path", f"{label} must be empty before execution"
                )
    except OSError as exc:
        raise LeanVerificationValidationError("path", f"{label} cannot be inspected") from exc
    return directory


def _validated_root(project_root: str) -> Path:
    if type(project_root) is not str or not project_root or "\x00" in project_root:
        raise LeanVerificationValidationError("type", "project_root must be one exact path string")
    root = Path(project_root)
    if not root.is_absolute():
        raise LeanVerificationValidationError("path", "project_root must be absolute")
    try:
        metadata = root.lstat()
    except OSError as exc:
        raise LeanVerificationValidationError("path", "project_root is unavailable") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise LeanVerificationValidationError("path", "project_root must be a real directory")
    return root.resolve(strict=True)


def _safe_output_path(root: Path) -> Path:
    _real_directory(
        root,
        Path(*_OUTPUT_PATH.parts[:-1]),
        "compiled artifact parent",
        create=True,
    )
    output = root / _OUTPUT_PATH
    try:
        metadata = output.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as exc:
        raise LeanVerificationValidationError(
            "path", "compiled artifact path cannot be inspected"
        ) from exc
    if metadata is not None:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LeanVerificationValidationError(
                "path", "preexisting compiled artifact is unsafe"
            )
        try:
            output.unlink()
        except OSError as exc:
            raise LeanVerificationValidationError(
                "path", "preexisting compiled artifact cannot be removed"
            ) from exc
    return output


def prepare_lean_project(export: LeanExport, project_root: str) -> Path:
    """Write only the generated source after validating fixed project files."""
    validate_lean_export(export)
    root = _validated_root(project_root)
    for relative, expected in _PROJECT_FILES.items():
        _regular_file_bytes(root / relative, expected, relative)
    source_parent = _real_directory(
        root, _SOURCE_PATH.parent, "generated source parent", create=True
    )
    source = root / _SOURCE_PATH
    if source.parent != source_parent:
        raise LeanVerificationValidationError("path", "generated source parent differs")
    try:
        metadata = source.lstat()
    except FileNotFoundError:
        metadata = None
    except OSError as exc:
        raise LeanVerificationValidationError("path", "generated source cannot be inspected") from exc
    if metadata is not None:
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LeanVerificationValidationError("path", "generated source path is unsafe")
    source_bytes = export.artifacts[1]
    temporary = source.with_name(".Generated.lean.tmp")
    if temporary.exists():
        metadata = temporary.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise LeanVerificationValidationError("path", "temporary source path is unsafe")
        temporary.unlink()
    try:
        with temporary.open("xb") as handle:
            handle.write(source_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, source)
        source.chmod(0o444)
    finally:
        if temporary.exists():
            temporary.unlink()
    _regular_file_bytes(source, source_bytes, "generated source")
    _safe_output_path(root)
    return source


def _process_environment(root: Path, toolchain_bin: Path) -> dict[str, str]:
    home = _empty_runtime_directory(root, Path(".hermetic-home"), "hermetic HOME")
    lake_home = _empty_runtime_directory(
        root, Path(".hermetic-lake-home"), "hermetic Lake home"
    )
    return {
        "HOME": str(home),
        "LAKE_HOME": str(lake_home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": str(toolchain_bin),
    }


@dataclass(frozen=True, slots=True)
class _ProcessObservation:
    returncode: int
    stdout: bytes
    stderr: bytes
    output_exhausted: bool
    timed_out: bool


def _run(
    command: list[str], root: Path, environment: dict[str, str], timeout: int
) -> _ProcessObservation:
    """Run without a shell while bounding retained output and in-memory use."""
    with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(
        mode="w+b"
    ) as stderr_file:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            close_fds=True,
            shell=False,
        )
        deadline = time.monotonic() + timeout
        output_exhausted = False
        timed_out = False
        try:
            while process.poll() is None:
                stdout_size = os.fstat(stdout_file.fileno()).st_size
                stderr_size = os.fstat(stderr_file.fileno()).st_size
                if stdout_size > MAX_OUTPUT_BYTES or stderr_size > MAX_OUTPUT_BYTES:
                    output_exhausted = True
                    process.kill()
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    process.kill()
                    break
                time.sleep(0.01)
            returncode = process.wait(timeout=30)
        except BaseException:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=30)
            except (OSError, subprocess.SubprocessError):
                pass
            raise
        stdout_size = os.fstat(stdout_file.fileno()).st_size
        stderr_size = os.fstat(stderr_file.fileno()).st_size
        output_exhausted = output_exhausted or stdout_size > MAX_OUTPUT_BYTES
        output_exhausted = output_exhausted or stderr_size > MAX_OUTPUT_BYTES
        stdout_file.seek(0)
        stderr_file.seek(0)
        return _ProcessObservation(
            returncode=returncode,
            stdout=stdout_file.read(MAX_OUTPUT_BYTES),
            stderr=stderr_file.read(MAX_OUTPUT_BYTES),
            output_exhausted=output_exhausted,
            timed_out=timed_out,
        )


def verify_with_lean(
    request: bytes, artifacts: tuple[bytes, ...], project_root: str
) -> LeanVerificationResult:
    """Run the exact prepared export through the exact pinned Lean boundary."""
    try:
        export = parse_lean_export(request, artifacts)
    except (LeanVerificationValidationError, TypeError, ValueError, RecursionError):
        return _new_result(
            None,
            status="check_failed",
            reason_code="REQUEST_INVALID",
            diagnostic="Lean verification request is invalid",
            verdict="invalid",
        )
    if not sys.platform.startswith("linux") or not hasattr(os, "uname"):
        return _new_result(
            export,
            status="check_unavailable",
            reason_code="CHECK_UNAVAILABLE",
            diagnostic="exact Linux Lean verification profile is unavailable",
            verdict="unsupported",
        )
    if os.uname().machine not in {"x86_64", "amd64"}:
        return _new_result(
            export,
            status="check_unavailable",
            reason_code="CHECK_UNAVAILABLE",
            diagnostic="exact Linux x86_64 Lean verification profile is unavailable",
            verdict="unsupported",
        )
    try:
        root = _validated_root(project_root)
        for relative, expected in _PROJECT_FILES.items():
            _regular_file_bytes(root / relative, expected, relative)
        _real_directory(root, _SOURCE_PATH.parent, "generated source parent", create=False)
        _regular_file_bytes(root / _SOURCE_PATH, artifacts[1], "generated source")
        output = _safe_output_path(root)
        toolchain_bin = _real_directory(
            root, Path(".toolchain/bin"), "toolchain bin", create=False
        )
        for dependency in _DEPENDENCY_NAMES:
            _real_directory(
                root,
                Path(".lake/packages") / dependency,
                f"dependency {dependency}",
                create=False,
            )
        lake = toolchain_bin / "lake"
        lean = toolchain_bin / "lean"
        lake_bytes = _regular_file_bytes(
            lake, None, "lake executable", max_bytes=_MAX_EXECUTABLE_BYTES
        )
        lean_bytes = _regular_file_bytes(
            lean, None, "Lean executable", max_bytes=_MAX_EXECUTABLE_BYTES
        )
        for path in (lake, lean):
            metadata = path.lstat()
            if metadata.st_mode & 0o222:
                raise LeanVerificationValidationError(
                    "toolchain", "toolchain executable is writable"
                )
        lake_digest = _sha256(lake_bytes)
        lean_digest = _sha256(lean_bytes)
        if (
            lake_digest != LAKE_EXECUTABLE_SHA256
            or lean_digest != LEAN_EXECUTABLE_SHA256
        ):
            raise LeanVerificationValidationError(
                "toolchain", "toolchain executable digest differs from the lock"
            )
        environment = _process_environment(root, toolchain_bin)
    except LeanVerificationValidationError:
        return _new_result(
            export,
            status="check_unavailable",
            reason_code="CHECK_UNAVAILABLE",
            diagnostic="exact pinned Lean toolchain or project is unavailable",
            verdict="unsupported",
        )
    try:
        version = _run([str(lean), "--version"], root, environment, 30)
    except (OSError, subprocess.SubprocessError):
        return _new_result(
            export,
            status="check_failed",
            reason_code="CHECK_FAILED",
            diagnostic="Lean version probe failed",
            verdict="invalid",
            lake_digest=lake_digest,
            lean_digest=lean_digest,
        )
    if version.timed_out or version.output_exhausted:
        return _new_result(
            export,
            status="check_exhausted",
            reason_code="CHECK_EXHAUSTED",
            diagnostic=(
                "Lean version time budget exhausted"
                if version.timed_out
                else "Lean version output budget exhausted"
            ),
            verdict="exhausted",
            exit_code=version.returncode if 0 <= version.returncode <= 255 else None,
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            stdout=version.stdout[:MAX_OUTPUT_BYTES],
            stderr=version.stderr[:MAX_OUTPUT_BYTES],
        )
    if (
        version.returncode != 0
        or version.stderr
        or version.stdout != _LEAN_VERSION_BYTES
    ):
        return _new_result(
            export,
            status="check_failed",
            reason_code="CHECK_FAILED",
            diagnostic="Lean version identity differs from the lock",
            verdict="invalid",
            exit_code=version.returncode if 0 <= version.returncode <= 255 else None,
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            version_digest=_sha256(version.stdout),
            stdout=version.stdout,
            stderr=version.stderr,
        )
    version_digest = _sha256(version.stdout)
    try:
        completed = _run(
            [str(lake), *_COMMAND], root, environment, MAX_TOTAL_SECONDS
        )
    except (OSError, subprocess.SubprocessError):
        return _new_result(
            export,
            status="check_failed",
            reason_code="CHECK_FAILED",
            diagnostic="Lean verification process failed",
            verdict="invalid",
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            version_digest=version_digest,
        )
    if completed.timed_out or completed.output_exhausted:
        return _new_result(
            export,
            status="check_exhausted",
            reason_code="CHECK_EXHAUSTED",
            diagnostic=(
                "Lean verification time budget exhausted"
                if completed.timed_out
                else "Lean verification output budget exhausted"
            ),
            verdict="exhausted",
            exit_code=completed.returncode if 0 <= completed.returncode <= 255 else None,
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            version_digest=version_digest,
            stdout=completed.stdout[:MAX_OUTPUT_BYTES],
            stderr=completed.stderr[:MAX_OUTPUT_BYTES],
        )
    if completed.returncode != 0:
        return _new_result(
            export,
            status="check_failed",
            reason_code="CHECK_FAILED",
            diagnostic="Lean kernel rejected the generated theorem",
            verdict="invalid",
            exit_code=completed.returncode if 0 <= completed.returncode <= 255 else None,
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            version_digest=version_digest,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    try:
        compiled = _regular_file_bytes(
            output, None, "compiled Lean artifact", max_bytes=_MAX_COMPILED_BYTES
        )
        if not compiled:
            raise LeanVerificationValidationError(
                "budget", "compiled Lean artifact length is outside the contract"
            )
        if _sha256(
            _regular_file_bytes(
                lake, None, "lake executable", max_bytes=_MAX_EXECUTABLE_BYTES
            )
        ) != lake_digest:
            raise LeanVerificationValidationError("toolchain", "lake changed during execution")
        if _sha256(
            _regular_file_bytes(
                lean, None, "Lean executable", max_bytes=_MAX_EXECUTABLE_BYTES
            )
        ) != lean_digest:
            raise LeanVerificationValidationError("toolchain", "Lean changed during execution")
        for relative, expected in _PROJECT_FILES.items():
            _regular_file_bytes(root / relative, expected, relative)
        _regular_file_bytes(root / _SOURCE_PATH, artifacts[1], "generated source")
    except LeanVerificationValidationError:
        return _new_result(
            export,
            status="check_failed",
            reason_code="CHECK_FAILED",
            diagnostic="compiled artifact or toolchain postcondition failed",
            verdict="invalid",
            exit_code=0,
            lake_digest=lake_digest,
            lean_digest=lean_digest,
            version_digest=version_digest,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
    return _new_result(
        export,
        status="externally_verified",
        reason_code="EXTERNALLY_VERIFIED",
        diagnostic="exact generated theorem accepted by the pinned Lean kernel",
        verdict="verified",
        exit_code=0,
        lake_digest=lake_digest,
        lean_digest=lean_digest,
        version_digest=version_digest,
        stdout=completed.stdout,
        stderr=completed.stderr,
        compiled=compiled,
        fresh=True,
    )


_STATUS_RULES = {
    "check_exhausted": ("CHECK_EXHAUSTED", "exhausted", "none"),
    "check_failed": (None, "invalid", "none"),
    "check_unavailable": ("CHECK_UNAVAILABLE", "unsupported", "none"),
    "export_written": ("EXPORT_WRITTEN", "unsupported", "none"),
    "externally_verified": (
        "EXTERNALLY_VERIFIED",
        "verified",
        "external_proof_assistant",
    ),
}


def _is_digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_lean_verification_result(
    result: object, *, require_fresh: bool = False
) -> None:
    """Validate one result; authority consumers must request fresh execution."""
    if type(result) is not LeanVerificationResult:
        raise LeanVerificationValidationError(
            "result", f"unknown Lean result type: {type(result).__name__}"
        )
    if (
        result.contract_id != LEAN_VERIFICATION_CONTRACT_ID
        or result.contract_sha256 != LEAN_VERIFICATION_CONTRACT_SHA256
        or result.toolchain != _toolchain_tuple()
        or type(result.exact) is not bool
        or not result.exact
    ):
        raise LeanVerificationValidationError("identity", "Lean result identity differs")
    if result.status not in _STATUS_RULES:
        raise LeanVerificationValidationError("result", "unknown Lean result status")
    expected_reason, expected_verdict, expected_authority = _STATUS_RULES[result.status]
    if expected_reason is not None and result.reason_code != expected_reason:
        raise LeanVerificationValidationError("result", "Lean status and reason differ")
    if result.status == "check_failed" and result.reason_code not in {
        "CHECK_FAILED",
        "REQUEST_INVALID",
    }:
        raise LeanVerificationValidationError("result", "unknown failed-check reason")
    if result.verdict != expected_verdict or result.authority != expected_authority:
        raise LeanVerificationValidationError("result", "Lean status authority differs")
    if type(result.diagnostic) is not str or not 0 < len(result.diagnostic) <= 512:
        raise LeanVerificationValidationError("result", "Lean diagnostic is invalid")
    digest_fields = (
        result.checker_result_sha256,
        result.compiled_artifact_sha256,
        result.lake_executable_sha256,
        result.lean_executable_sha256,
        result.lean_version_sha256,
        result.project_sha256,
        result.proof_term_sha256,
        result.request_sha256,
        result.source_sha256,
        result.stderr_sha256,
        result.stdout_sha256,
    )
    if any(value is not None and not _is_digest(value) for value in digest_fields):
        raise LeanVerificationValidationError("identity", "Lean result digest is invalid")
    if type(result.stdout_bytes) is not int or type(result.stderr_bytes) is not int:
        raise LeanVerificationValidationError("result", "Lean output lengths are invalid")
    if not 0 <= result.stdout_bytes <= MAX_OUTPUT_BYTES or not 0 <= result.stderr_bytes <= MAX_OUTPUT_BYTES:
        raise LeanVerificationValidationError("budget", "Lean output lengths exceed the contract")
    if result.exit_code is not None and (
        type(result.exit_code) is not int or type(result.exit_code) is bool or not 0 <= result.exit_code <= 255
    ):
        raise LeanVerificationValidationError("result", "Lean exit code is invalid")
    if result._stdout is not None:
        if len(result._stdout) != result.stdout_bytes or _sha256(result._stdout) != result.stdout_sha256:
            raise LeanVerificationValidationError("identity", "retained stdout differs")
    if result._stderr is not None:
        if len(result._stderr) != result.stderr_bytes or _sha256(result._stderr) != result.stderr_sha256:
            raise LeanVerificationValidationError("identity", "retained stderr differs")
    if result._compiled_artifact is not None and (
        _sha256(result._compiled_artifact) != result.compiled_artifact_sha256
        or not result._compiled_artifact
    ):
        raise LeanVerificationValidationError("identity", "retained olean differs")
    if result.status == "externally_verified":
        required = (
            result.checker_result_sha256,
            result.compiled_artifact_sha256,
            result.lake_executable_sha256,
            result.lean_executable_sha256,
            result.lean_version_sha256,
            result.project_sha256,
            result.proof_term_sha256,
            result.request_sha256,
            result.source_sha256,
            result.stderr_sha256,
            result.stdout_sha256,
        )
        if not all(_is_digest(value) for value in required) or result.exit_code != 0:
            raise LeanVerificationValidationError("result", "verified Lean result is incomplete")
        if require_fresh and result._fresh_authority is not _FRESH_AUTHORITY:
            raise LeanVerificationValidationError("result", "Lean authority is not freshly replayed")
    elif result._fresh_authority is not None:
        raise LeanVerificationValidationError("result", "non-verified result retains fresh authority")


def _result_object(result: LeanVerificationResult) -> dict[str, object]:
    lean_commit, lean_toolchain, mathlib_commit, target = result.toolchain
    return {
        "authority": result.authority,
        "checker_result_sha256": result.checker_result_sha256,
        "compiled_artifact_sha256": result.compiled_artifact_sha256,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "diagnostic": result.diagnostic,
        "exact": result.exact,
        "exit_code": result.exit_code,
        "lake_executable_sha256": result.lake_executable_sha256,
        "lean_executable_sha256": result.lean_executable_sha256,
        "lean_version_sha256": result.lean_version_sha256,
        "project_sha256": result.project_sha256,
        "proof_term_sha256": result.proof_term_sha256,
        "reason_code": result.reason_code,
        "request_sha256": result.request_sha256,
        "schema": LEAN_RESULT_SCHEMA,
        "source_sha256": result.source_sha256,
        "status": result.status,
        "stderr_bytes": result.stderr_bytes,
        "stderr_sha256": result.stderr_sha256,
        "stdout_bytes": result.stdout_bytes,
        "stdout_sha256": result.stdout_sha256,
        "toolchain": {
            "lean_commit": lean_commit,
            "lean_toolchain": lean_toolchain,
            "mathlib_commit": mathlib_commit,
            "platform": target,
        },
        "verdict": result.verdict,
    }


def lean_verification_result_to_bytes(result: LeanVerificationResult) -> bytes:
    """Serialize a structurally complete fresh or historical result."""
    validate_lean_verification_result(result)
    return _canonical_json(_result_object(result))


def lean_verification_result_sha256(result: LeanVerificationResult) -> str:
    """Return the full canonical identity of one Lean result."""
    return _sha256(lean_verification_result_to_bytes(result))


class _DuplicateKey(ValueError):
    pass


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    del value
    raise ValueError("floating-point JSON numbers are forbidden")


def parse_lean_verification_result(data: bytes) -> LeanVerificationResult:
    """Parse historical evidence without refreshing its external authority."""
    if type(data) is not bytes or len(data) > MAX_OUTPUT_BYTES:
        raise LeanVerificationValidationError("type", "Lean result input is invalid")
    try:
        raw = json.loads(
            data.decode("utf-8", errors="strict"),
            object_pairs_hook=_pairs_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except UnicodeDecodeError as exc:
        raise LeanVerificationValidationError(
            "encoding", f"invalid UTF-8 at byte {exc.start}"
        ) from exc
    except _DuplicateKey as exc:
        raise LeanVerificationValidationError(
            "duplicate", f"duplicate JSON key: {exc.args[0]}"
        ) from exc
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise LeanVerificationValidationError(
            "json", f"invalid Lean result JSON: {type(exc).__name__}"
        ) from exc
    if type(raw) is not dict or data != _canonical_json(raw):
        raise LeanVerificationValidationError("canonical", "Lean result is not canonical")
    expected = {
        "authority",
        "checker_result_sha256",
        "compiled_artifact_sha256",
        "contract_id",
        "contract_sha256",
        "diagnostic",
        "exact",
        "exit_code",
        "lake_executable_sha256",
        "lean_executable_sha256",
        "lean_version_sha256",
        "project_sha256",
        "proof_term_sha256",
        "reason_code",
        "request_sha256",
        "schema",
        "source_sha256",
        "status",
        "stderr_bytes",
        "stderr_sha256",
        "stdout_bytes",
        "stdout_sha256",
        "toolchain",
        "verdict",
    }
    if set(raw) != expected or raw.get("schema") != LEAN_RESULT_SCHEMA:
        raise LeanVerificationValidationError("schema", "Lean result fields differ")
    toolchain = raw["toolchain"]
    if type(toolchain) is not dict or set(toolchain) != {
        "lean_commit",
        "lean_toolchain",
        "mathlib_commit",
        "platform",
    }:
        raise LeanVerificationValidationError("schema", "Lean toolchain fields differ")
    value = object.__new__(LeanVerificationResult)
    fields = {key: raw[key] for key in expected if key not in {"schema", "toolchain"}}
    fields.update(
        {
            "_compiled_artifact": None,
            "_fresh_authority": None,
            "_stderr": None,
            "_stdout": None,
            "toolchain": (
                toolchain["lean_commit"],
                toolchain["lean_toolchain"],
                toolchain["mathlib_commit"],
                toolchain["platform"],
            ),
        }
    )
    for name, field in fields.items():
        object.__setattr__(value, name, field)
    validate_lean_verification_result(value)
    return value


def execution_artifacts(result: LeanVerificationResult) -> tuple[bytes, bytes, bytes]:
    """Return retained stdout, stderr, and olean only for a fresh verified result."""
    validate_lean_verification_result(result, require_fresh=True)
    if (
        result._stdout is None
        or result._stderr is None
        or result._compiled_artifact is None
    ):
        raise LeanVerificationValidationError("result", "fresh execution bytes are absent")
    return result._stdout, result._stderr, result._compiled_artifact


__all__ = [
    "LEAN_RESULT_SCHEMA",
    "LeanVerificationResult",
    "execution_artifacts",
    "export_written_result",
    "lean_verification_result_sha256",
    "lean_verification_result_to_bytes",
    "parse_lean_verification_result",
    "prepare_lean_project",
    "validate_lean_verification_result",
    "verify_with_lean",
]
