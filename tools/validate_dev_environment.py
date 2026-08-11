#!/usr/bin/env python3
"""Validate MH-C-ENV-002 acceptance, profile ownership, budgets, docs, and CI routing."""

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

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 uses the pinned compatibility package.
    import tomli as tomllib

ROOT_HINT = Path(__file__).resolve().parents[1]
if str(ROOT_HINT) not in sys.path:
    sys.path.insert(0, str(ROOT_HINT))

from tools import dev  # noqa: E402


EXPECTED_HASH = "aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d"
LEGACY_HASH = "63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87"
EXPECTED_PROFILES = (
    "status", "runtime", "core", "solver", "discovery", "docs", "live-mcp",
    "slow", "release",
)
EXPECTED_BUDGETS = {
    "status": 180,
    "runtime": 180,
    "core": 600,
    "solver": 600,
    "discovery": 600,
    "docs": 300,
    "live-mcp": 180,
    "slow": 1200,
    "release": 900,
}


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


def _commands(manifest: dict, profile: str) -> dict[str, dict]:
    return {command["id"]: command for command in manifest["profiles"][profile]["commands"]}


def _validate_profile_ownership(root: Path, manifest: dict) -> None:
    profiles = manifest["profiles"]
    if tuple(profiles) != EXPECTED_PROFILES or dev.PROFILE_NAMES != EXPECTED_PROFILES:
        raise DevEnvironmentValidationError("profile name or order drift")
    budgets = {name: profile["timeout_seconds"] for name, profile in profiles.items()}
    if budgets != EXPECTED_BUDGETS:
        raise DevEnvironmentValidationError("profile budget drift")
    installs = {
        "status": [],
        "runtime": ["."],
        "core": [".[dev]"],
        "solver": [".[dev,solvers]"],
        "discovery": [".[dev]"],
        "docs": [".[dev,docs]"],
        "live-mcp": [".[dev]"],
        "slow": [".[dev,solvers]"],
        "release": [".[release]"],
    }
    if {name: profile["install"] for name, profile in profiles.items()} != installs:
        raise DevEnvironmentValidationError("profile dependency boundary drift")
    if profiles["solver"]["platforms"] != ["linux"]:
        raise DevEnvironmentValidationError("solver platform boundary drift")
    if profiles["slow"]["platforms"] != ["linux"]:
        raise DevEnvironmentValidationError("slow platform boundary drift")
    if profiles["live-mcp"]["python"] != ["3.10", "3.11", "3.12"]:
        raise DevEnvironmentValidationError("live-MCP Python support drift")

    expected_selectors = {
        ("core", "core-tests"):
            "not requires_solver and not discovery and not docs and not live_mcp and not slow",
        ("solver", "solver-tests"): "requires_solver and not slow",
        ("discovery", "discovery-tests"):
            "discovery and not requires_solver and not slow",
        ("docs", "docs-examples"): "docs and not requires_solver and not slow",
        ("live-mcp", "live-mcp-tests"):
            "live_mcp and not requires_solver and not slow",
        ("slow", "slow-tests"): "slow",
    }
    for (profile, command_id), selector in expected_selectors.items():
        argv = _commands(manifest, profile).get(command_id, {}).get("argv", [])
        if not argv or argv[-1] != selector:
            raise DevEnvironmentValidationError(
                f"profile marker selector drift: {profile}:{command_id}"
            )
    all_command_ids = {
        command["id"]
        for profile in profiles.values()
        for command in profile["commands"]
    }
    if {"legacy-full", "solver-full-coverage"} & all_command_ids:
        raise DevEnvironmentValidationError("monolithic legacy command retained")

    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    registered = "\n".join(pyproject["tool"]["pytest"]["ini_options"]["markers"])
    for marker in ("requires_solver", "discovery", "docs", "live_mcp", "slow"):
        if not re.search(rf"(?m)^{re.escape(marker)}:", registered):
            raise DevEnvironmentValidationError(f"pytest marker not registered: {marker}")
    coverage_floor = pyproject["tool"]["coverage"]["report"]["fail_under"]
    if not isinstance(coverage_floor, int) or coverage_floor < 85:
        raise DevEnvironmentValidationError("coverage floor is below 85")
    coverage = _commands(manifest, "slow").get("coverage-gate")
    if coverage is None or coverage["required"] or coverage["timeout_seconds"] != 900:
        raise DevEnvironmentValidationError("separate coverage command drift")
    if "--cov=mathhead" not in coverage["argv"] or "--cov-fail-under=85" not in coverage["argv"]:
        raise DevEnvironmentValidationError("coverage command is missing the bound floor")

    conftest = (root / "tests" / "conftest.py").read_text(encoding="utf-8")
    if "pytest.mark.slow" in conftest:
        raise DevEnvironmentValidationError("slow ownership inferred by collection hook")
    slow_sources = (
        "tests/test_discovery_nauty_scale.py",
        "tests/test_discovery_ramsey_sat.py",
        "tests/test_discovery_rup_check.py",
    )
    for relative in slow_sources:
        if "pytest.mark.slow" not in (root / relative).read_text(encoding="utf-8"):
            raise DevEnvironmentValidationError(f"explicit slow marker missing: {relative}")


def _validate_checkout_history(workflow_text: str, workflow_name: str) -> None:
    chunks = workflow_text.split("uses: actions/checkout@v7")
    if len(chunks) == 1:
        return
    for index, chunk in enumerate(chunks[1:], start=1):
        step = chunk.split("- name:", 1)[0].split("- uses:", 1)[0]
        if "fetch-depth: 0" not in step:
            raise DevEnvironmentValidationError(
                f"shallow checkout may break baseline replay: {workflow_name}:{index}"
            )


def _validate_ci(root: Path) -> None:
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
        _validate_checkout_history(workflow_text, workflow.name)

    ci = (workflow_dir / "ci.yml").read_text(encoding="utf-8")
    for profile in ("core", "solver", "discovery", "docs", "live-mcp", "slow"):
        if f"check --profile {profile}" not in ci:
            raise DevEnvironmentValidationError(f"CI profile gate missing: {profile}")
    if "run --profile slow --command coverage-gate" not in ci:
        raise DevEnvironmentValidationError("required CI coverage gate missing")
    if "legacy-full" in ci or "continue-on-error" in ci:
        raise DevEnvironmentValidationError("CI contains a bypassed required gate")
    if "os: [ubuntu-latest, macos-latest, windows-latest]" not in ci:
        raise DevEnvironmentValidationError("portable three-OS matrix drift")
    if 'python: ["3.10", "3.11", "3.12"]' not in ci:
        raise DevEnvironmentValidationError("portable product Python matrix drift")


def validate(root: Path) -> int:
    accepted = root / "docs" / "contracts" / "MH-C-ENV-002.json"
    proposal = root / "docs" / "contracts" / "proposed" / "MH-C-ENV-002.json"
    for path in (accepted, proposal):
        if _sha256(path) != EXPECTED_HASH:
            raise DevEnvironmentValidationError(f"accepted contract hash drift: {path}")
    legacy_paths = (
        root / "docs" / "contracts" / "MH-C-ENV-001.json",
        root / "docs" / "contracts" / "proposed" / "MH-C-ENV-001.json",
    )
    for path in legacy_paths:
        if _sha256(path) != LEGACY_HASH:
            raise DevEnvironmentValidationError(f"superseded contract hash drift: {path}")
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
    _validate_profile_ownership(root, manifest)
    _validate_ci(root)
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
