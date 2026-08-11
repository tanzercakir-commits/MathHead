#!/usr/bin/env python3
"""Validate MH-C-ENV-001 acceptance, binding, profiles, docs, and CI ownership."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import hashlib
import inspect
import json
from pathlib import Path
import re
import sys
from typing import get_args, get_origin, get_type_hints

ROOT_HINT = Path(__file__).resolve().parents[1]
if str(ROOT_HINT) not in sys.path:
    sys.path.insert(0, str(ROOT_HINT))

from tools import dev  # noqa: E402


EXPECTED_HASH = "63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87"


class DevEnvironmentValidationError(RuntimeError):
    """Raised when the accepted environment boundary is incomplete or has drifted."""


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise DevEnvironmentValidationError(f"cannot read {path}: {exc}") from exc


def _validate_signature() -> None:
    signature = inspect.signature(dev.main)
    if tuple(signature.parameters) != ("argv",):
        raise DevEnvironmentValidationError("tools.dev:main parameter drift")
    parameter = signature.parameters["argv"]
    if parameter.default is not None:
        raise DevEnvironmentValidationError("tools.dev:main default drift")
    hints = get_type_hints(dev.main)
    annotation = hints.get("argv")
    options = set(get_args(annotation))
    sequence_option = next((item for item in options if get_origin(item) is Sequence), None)
    if sequence_option is None or get_args(sequence_option) != (str,) or type(None) not in options:
        raise DevEnvironmentValidationError("tools.dev:main argv annotation drift")
    if hints.get("return") is not int:
        raise DevEnvironmentValidationError("tools.dev:main return annotation drift")


def _validate_pins(root: Path, manifest: dict) -> None:
    constraints = (root / manifest["constraints"]).read_text(encoding="utf-8")
    required = {
        "z3-solver", "sympy", "mcp", "pytest", "pytest-timeout", "pytest-cov",
        "hypothesis", "ruff", "python-sat", "mkdocs", "mkdocs-material", "build",
        "twine", "hatchling", "pip", "tomli",
    }
    pinned = {
        match.group(1).casefold()
        for match in re.finditer(r"(?m)^([A-Za-z0-9_.-]+)==[^\s;]+", constraints)
    }
    missing = sorted(required - pinned)
    if missing:
        raise DevEnvironmentValidationError(
            "constraints lack required exact pin(s): " + ", ".join(missing)
        )


def validate(root: Path) -> int:
    accepted = root / "docs" / "contracts" / "MH-C-ENV-001.json"
    proposal = root / "docs" / "contracts" / "proposed" / "MH-C-ENV-001.json"
    for path in (accepted, proposal):
        if _sha256(path) != EXPECTED_HASH:
            raise DevEnvironmentValidationError(f"accepted contract hash drift: {path}")
    try:
        contract = json.loads(accepted.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DevEnvironmentValidationError(f"accepted contract is invalid JSON: {exc}") from exc
    if contract.get("target") != "tools.dev:main":
        raise DevEnvironmentValidationError("accepted target drift")
    if contract.get("signature") != "main(argv: Sequence[str] | None = None) -> int":
        raise DevEnvironmentValidationError("accepted signature drift")
    if dev.CONTRACT_ID != contract.get("contract_id") or dev.CONTRACT_SHA256 != EXPECTED_HASH:
        raise DevEnvironmentValidationError("implementation contract binding drift")
    _validate_signature()
    manifest = dev._load_manifest(root)
    _validate_pins(root, manifest)
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml"))
    if not workflows:
        raise DevEnvironmentValidationError("CI workflows missing")
    forbidden = ("pip install", "pytest ", "ruff check", "python -m build", "twine check")
    for workflow in workflows:
        try:
            workflow_text = workflow.read_text(encoding="utf-8")
        except OSError as exc:
            raise DevEnvironmentValidationError(f"cannot read CI workflow: {exc}") from exc
        if "tools/dev.py" not in workflow_text:
            raise DevEnvironmentValidationError(
                f"CI workflow bypasses the dispatcher: {workflow.name}"
            )
        duplicated = next((item for item in forbidden if item in workflow_text), None)
        if duplicated is not None:
            raise DevEnvironmentValidationError(
                f"CI workflow duplicates profile semantics: {workflow.name}: {duplicated}"
            )
    readme = (root / "README.md").read_text(encoding="utf-8")
    if "python tools/dev.py bootstrap --profile core" not in readme:
        raise DevEnvironmentValidationError("README lacks the governed bootstrap command")
    return len(manifest["profiles"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        count = validate(args.root.resolve())
    except DevEnvironmentValidationError as exc:
        print(f"dev-environment: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"dev-environment: PASS ({count} profiles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
