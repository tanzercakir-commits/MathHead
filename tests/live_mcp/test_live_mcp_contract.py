from __future__ import annotations

from dataclasses import FrozenInstanceError
import errno
import hashlib
import inspect
import math
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from mathhead.server import live


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_HASH = "3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143"


class _Stream:
    def __init__(self, *, close_error: bool = False) -> None:
        self.closed = False
        self.close_error = close_error

    def close(self) -> None:
        self.closed = True
        if self.close_error:
            raise OSError(errno.EIO, "synthetic close failure")


class _Process:
    def __init__(
        self,
        *,
        stdout: bytes = live._STDOUT_SENTINEL,
        stderr: bytes = live._STDERR_SENTINEL,
        returncode: int | None = 0,
        communicate_error: BaseException | None = None,
        survive_terminate: bool = False,
        close_error: bool = False,
    ) -> None:
        self.stdin = _Stream(close_error=close_error)
        self.stdout = _Stream(close_error=close_error)
        self.stderr = _Stream(close_error=close_error)
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._communicate_error = communicate_error
        self._survive_terminate = survive_terminate
        self.terminated = False
        self.killed = False
        self.waited = 0

    def communicate(self, *, input: bytes, timeout: float) -> tuple[bytes, bytes]:
        assert input == live._STDIN_SENTINEL
        assert timeout > 0
        if self._communicate_error is not None:
            raise self._communicate_error
        return self._stdout, self._stderr

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        if not self._survive_terminate:
            self.returncode = -15

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9

    def wait(self, *, timeout: float) -> int:
        self.waited += 1
        if self._survive_terminate and not self.killed:
            raise subprocess.TimeoutExpired("probe", timeout)
        assert self.returncode is not None
        return self.returncode


class LiveMcpContractTests(unittest.TestCase):
    def test_contract_binding_hash_and_signature(self) -> None:
        accepted = ROOT / "docs/contracts/MH-C-LIVE-MCP-001.json"
        proposed = ROOT / "docs/contracts/proposed/MH-C-LIVE-MCP-001.json"
        self.assertEqual(accepted.read_bytes(), proposed.read_bytes())
        self.assertEqual(hashlib.sha256(accepted.read_bytes()).hexdigest(), EXPECTED_HASH)
        self.assertEqual(live.LIVE_MCP_CONTRACT_ID, "MH-C-LIVE-MCP-001")
        self.assertEqual(live.LIVE_MCP_CONTRACT_SHA256, EXPECTED_HASH)
        self.assertEqual(
            str(inspect.signature(live.probe_stdio_capability)),
            "(timeout_seconds: 'float' = 5.0) -> 'StdioCapability'",
        )

    def test_capability_value_is_frozen(self) -> None:
        value = live.StdioCapability("supported", "stdio-pipes-supported")
        with self.assertRaises(FrozenInstanceError):
            value.status = "failed"  # type: ignore[misc]

    def test_real_fixed_child_proves_stdio_support(self) -> None:
        self.assertEqual(
            live.probe_stdio_capability(),
            live.StdioCapability("supported", "stdio-pipes-supported"),
        )

    def test_invalid_timeout_fails_before_spawn(self) -> None:
        invalid = (True, "5", None, 0, -1, math.inf, -math.inf, math.nan)
        with mock.patch.object(live.subprocess, "Popen") as popen:
            for value in invalid:
                with self.subTest(value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        live.probe_stdio_capability(value)  # type: ignore[arg-type]
            popen.assert_not_called()

    def test_only_allowlisted_os_denials_are_unsupported(self) -> None:
        with mock.patch.object(
            live.subprocess,
            "Popen",
            side_effect=PermissionError(errno.EPERM, "synthetic"),
        ):
            self.assertEqual(
                live.probe_stdio_capability(),
                live.StdioCapability("unsupported", "pipe-permission-denied"),
            )
        with mock.patch.object(
            live.subprocess,
            "Popen",
            side_effect=FileNotFoundError(errno.ENOENT, "synthetic"),
        ):
            self.assertEqual(
                live.probe_stdio_capability(),
                live.StdioCapability("failed", "probe-start-failed"),
            )

    def test_output_and_exit_mismatch_fail_closed(self) -> None:
        cases = (
            (_Process(returncode=7), "probe-nonzero-exit"),
            (_Process(stdout=b"wrong"), "probe-output-mismatch"),
            (_Process(stderr=b"wrong"), "probe-output-mismatch"),
        )
        for process, reason in cases:
            with self.subTest(reason=reason), mock.patch.object(
                live.subprocess, "Popen", return_value=process
            ):
                result = live.probe_stdio_capability()
                self.assertEqual(result, live.StdioCapability("failed", reason))
                self.assertTrue(process.stdin.closed)
                self.assertTrue(process.stdout.closed)
                self.assertTrue(process.stderr.closed)

    def test_timeout_terminates_kills_waits_and_closes(self) -> None:
        process = _Process(
            returncode=None,
            communicate_error=subprocess.TimeoutExpired("probe", 0.01),
            survive_terminate=True,
        )
        with mock.patch.object(live.subprocess, "Popen", return_value=process):
            result = live.probe_stdio_capability(0.01)
        self.assertEqual(result, live.StdioCapability("timed_out", "probe-timeout"))
        self.assertTrue(process.terminated)
        self.assertTrue(process.killed)
        self.assertEqual(process.waited, 2)
        self.assertTrue(process.stdin.closed)
        self.assertTrue(process.stdout.closed)
        self.assertTrue(process.stderr.closed)

    def test_cleanup_failure_overrides_success(self) -> None:
        process = _Process(close_error=True)
        with mock.patch.object(live.subprocess, "Popen", return_value=process):
            result = live.probe_stdio_capability()
        self.assertEqual(result, live.StdioCapability("failed", "probe-cleanup-failed"))

    def test_interrupt_propagates_after_cleanup(self) -> None:
        process = _Process(returncode=None, communicate_error=KeyboardInterrupt())
        with mock.patch.object(live.subprocess, "Popen", return_value=process):
            with self.assertRaises(KeyboardInterrupt):
                live.probe_stdio_capability()
        self.assertTrue(process.terminated)
        self.assertTrue(process.stdin.closed)


if __name__ == "__main__":
    unittest.main()
