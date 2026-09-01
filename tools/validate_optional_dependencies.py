#!/usr/bin/env python3
"""Validate the core/solver capability boundary owned by MH-010."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
import shutil
import sys
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 in the governed core profile.
    import tomli as tomllib
from typing import Any


MODULE_MARKERS = (
    "tests/test_discovery_nauty_scale.py",
    "tests/test_discovery_ramsey_sat.py",
    "tests/test_discovery_rup_check.py",
)
FUNCTION_MARKERS = {
    "tests/test_discovery_cli.py": {
        "test_bracket_command",
    },
    "tests/test_discovery_closure_sweep_d.py": {
        "test_ag1_parallel_ramsey_decisions_merge_deterministically",
    },
    "tests/test_docs_examples.py": {
        "test_example_3_bracket_r33",
    },
    "tests/test_hpsolver.py": {
        "test_pysat_bad_solver_name_rejected",
        "test_pysat_bounded_search_is_unknown_not_a_hang",
        "test_pysat_sat_model_independently_verified",
        "test_pysat_scale_sat_verified",
        "test_pysat_unsat",
    },
    "tests/test_j_track_hardening.py": {
        "test_stdlib_dpll_and_cadical_agree",
    },
}


class OptionalDependencyError(RuntimeError):
    """Raised when an optional capability leaks or is selected ambiguously."""


def _distribution_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    if match is None:
        raise OptionalDependencyError(f"invalid requirement: {requirement!r}")
    return match.group(0).replace("_", "-").casefold()


def _load(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
        profiles = json.loads((root / "tools" / "dev_profiles.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
        raise OptionalDependencyError(f"cannot read dependency metadata: {exc}") from exc
    return project, profiles


def _module_scope_imports(tree: ast.Module, module: str) -> list[int]:
    lines: list[int] = []

    def visit(node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(node, ast.Import):
            if any(alias.name == module or alias.name.startswith(module + ".") for alias in node.names):
                lines.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.module == module or (node.module or "").startswith(module + "."):
                lines.append(node.lineno)
        for child in ast.iter_child_nodes(node):
            visit(child)

    for statement in tree.body:
        visit(statement)
    return lines


def _decorator_name(node: ast.expr) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _validate_test_markers(root: Path) -> int:
    marker = "pytest.mark.requires_solver"
    for relative in MODULE_MARKERS:
        try:
            text = (root / relative).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OptionalDependencyError(f"cannot read capability test {relative}: {exc}") from exc
        if marker not in text:
            raise OptionalDependencyError(f"solver test module lacks capability marker: {relative}")
    count = len(MODULE_MARKERS)
    for relative, expected in FUNCTION_MARKERS.items():
        try:
            tree = ast.parse((root / relative).read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise OptionalDependencyError(f"cannot parse capability test {relative}: {exc}") from exc
        marked = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and marker in {_decorator_name(decorator) for decorator in node.decorator_list}
        }
        missing = sorted(expected - marked)
        if missing:
            raise OptionalDependencyError(
                f"solver tests lack capability marker in {relative}: {', '.join(missing)}"
            )
        count += len(expected)
    return count


def _validate_source_import_boundary(root: Path) -> int:
    checked = 0
    for path in sorted((root / "src" / "mathhead").rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except (OSError, UnicodeError, SyntaxError) as exc:
            raise OptionalDependencyError(f"cannot parse product source {relative}: {exc}") from exc
        lines = _module_scope_imports(tree, "pysat")
        if lines:
            raise OptionalDependencyError(
                f"core import would load optional pysat at {relative}:{lines[0]}"
            )
        checked += 1
    return checked


def _module_available(name: str) -> bool:
    try:
        return __import__(name) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def _which_any(requirement: str) -> str | None:
    return next((path for name in requirement.split("|") if (path := shutil.which(name))), None)


def validate(root: Path, profile: str) -> tuple[int, int]:
    project, manifest = _load(root)
    try:
        extras = project["project"]["optional-dependencies"]
        profiles = manifest["profiles"]
        dev_requirements = {_distribution_name(item) for item in extras["dev"]}
        solver_requirements = {_distribution_name(item) for item in extras["solvers"]}
    except (KeyError, TypeError) as exc:
        raise OptionalDependencyError(f"dependency profile metadata is incomplete: {exc}") from exc
    if "python-sat" in dev_requirements:
        raise OptionalDependencyError("dev extra imports the optional python-sat capability")
    if solver_requirements != {"python-sat"}:
        raise OptionalDependencyError("solvers extra must explicitly own python-sat")
    if profiles["core"]["install"] != [".[dev]"]:
        raise OptionalDependencyError("core profile dependency set drift")
    if profiles["solver"]["install"] != [".[dev,solvers]"]:
        raise OptionalDependencyError("solver profile dependency set drift")
    executable_requirements = profiles["solver"]["required_executables"]
    if executable_requirements != ["nauty-geng|geng"]:
        raise OptionalDependencyError("solver executable alternatives are incomplete")
    source_count = _validate_source_import_boundary(root)
    marker_count = _validate_test_markers(root)
    markers = project.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])
    if not any(isinstance(item, str) and item.startswith("requires_solver:") for item in markers):
        raise OptionalDependencyError("pytest capability marker is not registered")
    if profile == "solver":
        if not _module_available("pysat.solvers"):
            raise OptionalDependencyError("solver profile lacks importable pysat.solvers")
        missing = [item for item in executable_requirements if _which_any(item) is None]
        if missing:
            raise OptionalDependencyError("solver profile lacks executable: " + ",".join(missing))
    return source_count, marker_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--profile", choices=("core", "solver"), required=True)
    args = parser.parse_args(argv)
    try:
        sources, markers = validate(args.root.resolve(), args.profile)
    except OptionalDependencyError as exc:
        print(f"optional-dependencies: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        f"optional-dependencies: PASS (profile={args.profile}, sources={sources}, "
        f"capability-markers={markers})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
