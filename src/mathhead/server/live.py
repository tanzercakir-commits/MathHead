"""Fail-closed capability semantics for live MCP stdio integration tests."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import math
import subprocess
import sys
from typing import Literal


LIVE_MCP_CONTRACT_ID = "MH-C-LIVE-MCP-001"
LIVE_MCP_CONTRACT_SHA256 = \
    "3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143"

_STDIN_SENTINEL = b"mathhead-stdio-probe\n"
_STDOUT_SENTINEL = b"stdout:mathhead-stdio-probe\n"
_STDERR_SENTINEL = b"stderr:mathhead-stdio-probe\n"
_PROBE_PROGRAM = (
    "import sys; "
    "data=sys.stdin.buffer.readline(); "
    "sys.stdout.buffer.write(b'stdout:'+data); sys.stdout.buffer.flush(); "
    "sys.stderr.buffer.write(b'stderr:'+data); sys.stderr.buffer.flush()"
)
_TERMINATE_GRACE_SECONDS = 2.0
_KILL_GRACE_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class StdioCapability:
    """Evidence from the independent fixed-child stdio capability probe."""

    status: Literal["supported", "unsupported", "timed_out", "failed"]
    reason: str


def _denial_reason(exc: OSError) -> str | None:
    permission_errnos = {errno.EACCES, errno.EPERM}
    unsupported_errnos = {
        value
        for value in (
            getattr(errno, "ENOSYS", None),
            getattr(errno, "ENOTSUP", None),
            getattr(errno, "EOPNOTSUPP", None),
        )
        if value is not None
    }
    if exc.errno in permission_errnos or getattr(exc, "winerror", None) == 5:
        return "pipe-permission-denied"
    if exc.errno in unsupported_errnos or getattr(exc, "winerror", None) == 50:
        return "pipe-operation-not-supported"
    return None


def _close_streams(process: subprocess.Popen[bytes]) -> bool:
    clean = True
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is None or stream.closed:
            continue
        try:
            stream.close()
        except OSError:
            clean = False
    return clean


def _reap(process: subprocess.Popen[bytes]) -> bool:
    clean = True
    try:
        if process.poll() is None:
            try:
                process.terminate()
            except OSError:
                clean = False
            try:
                process.wait(timeout=_TERMINATE_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except OSError:
                    clean = False
                try:
                    process.wait(timeout=_KILL_GRACE_SECONDS)
                except (OSError, subprocess.TimeoutExpired):
                    clean = False
            except OSError:
                clean = False
        if process.poll() is None:
            clean = False
    finally:
        clean = _close_streams(process) and clean
    return clean


def probe_stdio_capability(timeout_seconds: float = 5.0) -> StdioCapability:
    """Prove fixed-child stdio support or return a fail-closed classification."""
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise TypeError("timeout_seconds must be a finite positive number")
    timeout = float(timeout_seconds)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout_seconds must be a finite positive number")

    process: subprocess.Popen[bytes] | None = None
    result: StdioCapability | None = None
    propagate: BaseException | None = None
    try:
        try:
            process = subprocess.Popen(
                [sys.executable, "-c", _PROBE_PROGRAM],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            reason = _denial_reason(exc)
            return StdioCapability(
                "unsupported" if reason is not None else "failed",
                reason or "probe-start-failed",
            )

        try:
            stdout, stderr = process.communicate(input=_STDIN_SENTINEL, timeout=timeout)
        except subprocess.TimeoutExpired:
            result = StdioCapability("timed_out", "probe-timeout")
        except OSError as exc:
            reason = _denial_reason(exc)
            result = StdioCapability(
                "unsupported" if reason is not None else "failed",
                reason or "probe-io-failed",
            )
        except Exception:
            result = StdioCapability("failed", "probe-io-failed")
        else:
            if process.returncode != 0:
                result = StdioCapability("failed", "probe-nonzero-exit")
            elif stdout != _STDOUT_SENTINEL or stderr != _STDERR_SENTINEL:
                result = StdioCapability("failed", "probe-output-mismatch")
            else:
                result = StdioCapability("supported", "stdio-pipes-supported")
    except (KeyboardInterrupt, SystemExit) as exc:
        propagate = exc
    except Exception:
        result = StdioCapability("failed", "probe-internal-failure")
    finally:
        clean = process is None or _reap(process)

    if propagate is not None:
        raise propagate
    if not clean:
        return StdioCapability("failed", "probe-cleanup-failed")
    return result or StdioCapability("failed", "probe-internal-failure")
