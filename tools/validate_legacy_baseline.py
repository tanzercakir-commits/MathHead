#!/usr/bin/env python3
"""Validate MH-C-BASELINE-001 binding, artifact identity, replay, and CI ownership."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import inspect
from pathlib import Path
import sys
from typing import get_args, get_origin, get_type_hints

ROOT_HINT = Path(__file__).resolve().parents[1]
if str(ROOT_HINT) not in sys.path:
    sys.path.insert(0, str(ROOT_HINT))

from tools import capture_legacy_baseline as baseline  # noqa: E402


EXPECTED_CONTRACT_SHA256 = "3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2"
EXPECTED_ARTIFACT_SHA256 = "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
EXPECTED_OBSERVATIONS_SHA256 = "69c90d4e71a9955c4211b5939be75bdde19a2d05457b1d272d900b74b11aa903"


class LegacyBaselineValidationError(RuntimeError):
    """Raised when the accepted baseline implementation or evidence drifts."""


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise LegacyBaselineValidationError(f"cannot read {path}: {exc}") from exc


def _validate_signature() -> None:
    signature = inspect.signature(baseline.main)
    if tuple(signature.parameters) != ("argv",):
        raise LegacyBaselineValidationError("tools.capture_legacy_baseline:main parameter drift")
    parameter = signature.parameters["argv"]
    if parameter.default is not None:
        raise LegacyBaselineValidationError("tools.capture_legacy_baseline:main default drift")
    hints = get_type_hints(baseline.main)
    annotation = hints.get("argv")
    options = set(get_args(annotation))
    sequence = next((item for item in options if get_origin(item) is Sequence), None)
    if sequence is None or get_args(sequence) != (str,) or type(None) not in options:
        raise LegacyBaselineValidationError("tools.capture_legacy_baseline:main argv annotation drift")
    if hints.get("return") is not int:
        raise LegacyBaselineValidationError("tools.capture_legacy_baseline:main return annotation drift")


def validate(root: Path) -> tuple[int, int]:
    accepted = root / "docs" / "contracts" / "MH-C-BASELINE-001.json"
    proposal = root / "docs" / "contracts" / "proposed" / "MH-C-BASELINE-001.json"
    artifact = root / "docs" / "reconstruction" / "legacy-baseline-v1.json"
    observations = root / "docs" / "reconstruction" / "legacy-observations-v1.json"
    for path in (accepted, proposal):
        if _sha256(path) != EXPECTED_CONTRACT_SHA256:
            raise LegacyBaselineValidationError(f"accepted contract hash drift: {path}")
    if baseline.CONTRACT_ID != "MH-C-BASELINE-001" or baseline.CONTRACT_SHA256 != EXPECTED_CONTRACT_SHA256:
        raise LegacyBaselineValidationError("implementation contract binding drift")
    _validate_signature()
    if _sha256(artifact) != EXPECTED_ARTIFACT_SHA256:
        raise LegacyBaselineValidationError("canonical baseline artifact SHA-256 drift")
    if _sha256(observations) != EXPECTED_OBSERVATIONS_SHA256:
        raise LegacyBaselineValidationError("baseline observation input SHA-256 drift")
    try:
        replayed = baseline.replay(root, "docs/reconstruction/legacy-baseline-v1.json")
    except baseline.BaselineError as exc:
        raise LegacyBaselineValidationError(f"offline replay failed [{exc.code}]: {exc}") from exc
    workflow = root / ".github" / "workflows" / "project-status.yml"
    try:
        workflow_text = workflow.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise LegacyBaselineValidationError(f"cannot read independent CI workflow: {exc}") from exc
    if "os: [ubuntu-latest, windows-latest]" not in workflow_text:
        raise LegacyBaselineValidationError("baseline replay lacks Ubuntu/Windows CI ownership")
    if "python tools/dev.py check --profile status" not in workflow_text:
        raise LegacyBaselineValidationError("baseline replay CI bypasses the governed dispatcher")
    config = (root / ".project-status.toml").read_text(encoding="utf-8")
    if 'name = "legacy-baseline"' not in config or 'tasks = ["MH-004"]' not in config:
        raise LegacyBaselineValidationError("legacy baseline is not a task-owned status check")
    return replayed["source"]["inventory"]["count"], replayed["source"]["test_collection"]["count"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        files, tests = validate(args.root.resolve())
    except LegacyBaselineValidationError as exc:
        print(f"legacy-baseline-validator: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"legacy-baseline-validator: PASS (files={files}, tests={tests})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
