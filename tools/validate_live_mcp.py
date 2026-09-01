#!/usr/bin/env python3
"""Validate accepted MH-C-LIVE-MCP-001 binding and fail-closed selection."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import inspect
import math
from pathlib import Path
import sys
from typing import get_type_hints


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mathhead.server import live  # noqa: E402


EXPECTED_CONTRACT_SHA256 = \
    "3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143"
FROZEN_BASELINE_SHA256 = \
    "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
FROZEN_OBSERVATIONS_SHA256 = \
    "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"


class LiveMcpValidationError(RuntimeError):
    """Raised when the live-MCP capability boundary drifts."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_signature() -> None:
    signature = inspect.signature(live.probe_stdio_capability)
    if tuple(signature.parameters) != ("timeout_seconds",):
        raise LiveMcpValidationError("probe signature parameter drift")
    parameter = signature.parameters["timeout_seconds"]
    if parameter.default != 5.0 or parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD:
        raise LiveMcpValidationError("probe timeout default or kind drift")
    hints = get_type_hints(live.probe_stdio_capability)
    if hints.get("timeout_seconds") is not float or hints.get("return") is not live.StdioCapability:
        raise LiveMcpValidationError("probe type annotation drift")


def validate() -> None:
    accepted = ROOT / "docs/contracts/MH-C-LIVE-MCP-001.json"
    proposed = ROOT / "docs/contracts/proposed/MH-C-LIVE-MCP-001.json"
    for path in (accepted, proposed):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise LiveMcpValidationError(f"contract hash drift: {path.relative_to(ROOT)}")
    if accepted.read_bytes() != proposed.read_bytes():
        raise LiveMcpValidationError("accepted contract differs from reviewed proposal")
    if _sha256(ROOT / "docs/reconstruction/legacy-baseline-v1.json") != \
            FROZEN_BASELINE_SHA256:
        raise LiveMcpValidationError("immutable baseline artifact drift")
    if _sha256(ROOT / "docs/reconstruction/legacy-observations-v1.json") != \
            FROZEN_OBSERVATIONS_SHA256:
        raise LiveMcpValidationError("immutable observation artifact drift")
    if live.LIVE_MCP_CONTRACT_ID != "MH-C-LIVE-MCP-001" or \
            live.LIVE_MCP_CONTRACT_SHA256 != EXPECTED_CONTRACT_SHA256:
        raise LiveMcpValidationError("implementation contract metadata drift")
    _validate_signature()

    value = live.StdioCapability("supported", "stdio-pipes-supported")
    try:
        value.status = "failed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise LiveMcpValidationError("StdioCapability is not frozen")

    for invalid in (True, "5", None, 0, -1, math.inf, -math.inf, math.nan):
        try:
            live.probe_stdio_capability(invalid)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        raise LiveMcpValidationError(f"invalid timeout accepted: {invalid!r}")

    probe = live.probe_stdio_capability()
    if probe.status not in {"supported", "unsupported", "timed_out", "failed"}:
        raise LiveMcpValidationError("probe emitted an unknown status")
    if probe.status == "unsupported" and probe.reason not in {
        "pipe-permission-denied", "pipe-operation-not-supported"
    }:
        raise LiveMcpValidationError("unsupported emitted a non-allowlisted reason")

    test_text = (ROOT / "tests/test_mcp_live.py").read_text(encoding="utf-8")
    required = (
        "pytestmark = pytest.mark.live_mcp",
        "capability = probe_stdio_capability()",
        'if capability.status == "unsupported":',
        'if capability.status != "supported":',
        "proc.terminate()",
        "proc.kill()",
        "proc.wait(timeout=2)",
    )
    missing = [item for item in required if item not in test_text]
    if missing:
        raise LiveMcpValidationError("live MCP fail-closed test semantics drift: " + missing[0])
    forbidden = ("skipif(sys.platform", "skipif(os.name", "except Exception:\n        pytest.skip")
    if any(item in test_text for item in forbidden):
        raise LiveMcpValidationError("broad live MCP skip returned")


def main() -> int:
    try:
        validate()
    except (LiveMcpValidationError, OSError, SyntaxError) as exc:
        print(f"live-mcp: FAIL: {exc}", file=sys.stderr)
        return 1
    print("live-mcp: PASS (independent-probe, strict-skip, deterministic-cleanup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
