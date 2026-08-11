#!/usr/bin/env python3
"""Fail-closed static validation for MH-C-PROJECT-FACTS-001."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad"
CONTRACT_ID = "MH-C-PROJECT-FACTS-001"
DIRECTIVE = re.compile(
    r"^<!-- mathhead-(example|non-executable): ([a-z0-9][a-z0-9-]*)(?: \| (.+))? -->$"
)
FENCE = re.compile(r"^```([A-Za-z0-9_-]*)\s*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class ProjectMetadataError(RuntimeError):
    """Raised when generated metadata ownership or inputs drift."""


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise ProjectMetadataError(f"invalid TOML {label}: {exc}") from exc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_contract() -> None:
    accepted = ROOT / f"docs/contracts/{CONTRACT_ID}.json"
    proposed = ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json"
    for path in (accepted, proposed):
        if _sha(path) != EXPECTED_SHA256:
            raise ProjectMetadataError(f"contract hash drift: {path.relative_to(ROOT)}")
    if accepted.read_bytes() != proposed.read_bytes():
        raise ProjectMetadataError("accepted contract differs from reviewed proposal")
    manifest = _load_toml(ROOT / "docs/contracts/manifest.toml")
    records = [item for item in manifest.get("contracts", []) if item.get("id") == CONTRACT_ID]
    if len(records) != 1 or records[0].get("sha256") != EXPECTED_SHA256:
        raise ProjectMetadataError("accepted contract manifest binding missing or ambiguous")


def _validate_version() -> str:
    pyproject = _load_toml(ROOT / "pyproject.toml")
    project = pyproject.get("project", {})
    if "version" in project or project.get("dynamic", []).count("version") != 1:
        raise ProjectMetadataError("pyproject version is not uniquely dynamic")
    hatch_path = pyproject.get("tool", {}).get("hatch", {}).get("version", {}).get("path")
    if hatch_path != "src/mathhead/_version.py":
        raise ProjectMetadataError("Hatch version path drift")
    version_path = ROOT / hatch_path
    tree = ast.parse(version_path.read_text(encoding="utf-8"), filename=str(version_path))
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Constant):
        raise ProjectMetadataError("version source must contain one literal assignment")
    version = assignments[0].value.value
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ProjectMetadataError("version source is not SemVer")
    init_tree = ast.parse((ROOT / "src/mathhead/__init__.py").read_text(encoding="utf-8"))
    imports = [
        node for node in init_tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "_version"
        and any(alias.name == "__version__" for alias in node.names)
    ]
    if len(imports) != 1:
        raise ProjectMetadataError("package does not import its version from _version")
    return version


def _pytest_function_exists(root: Path, nodeid: str) -> bool:
    match = re.fullmatch(r"(tests/[A-Za-z0-9_./-]+\.py)::([A-Za-z_][A-Za-z0-9_]*)", nodeid)
    if not match:
        return False
    path = root / match.group(1)
    if not path.is_file():
        return False
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError):
        return False
    return any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == match.group(2)
        for node in tree.body
    )


def _validator_profile(nodeid: str) -> str:
    path, function = nodeid.split("::", 1)
    if path == "tests/test_discovery_ramsey_sat.py":
        return "slow"
    if path == "tests/test_docs_examples.py" and function == "test_example_3_bracket_r33":
        return "solver"
    if path == "tests/test_docs_examples.py" or path.startswith("tests/project_metadata/"):
        return "docs"
    if Path(path).name.startswith("test_discovery_") or "/graph_budget/" in path:
        return "discovery"
    return "core"


def _source_directives(root: Path, sources: list[str]) -> dict[str, dict[str, str]]:
    found: dict[str, dict[str, str]] = {}
    for relative in sources:
        path = root / relative
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise ProjectMetadataError(f"example source unreadable: {relative}: {exc}") from exc
        open_fence = False
        for number, line in enumerate(lines):
            fence = FENCE.fullmatch(line)
            if not fence:
                continue
            if open_fence:
                open_fence = False
                continue
            open_fence = True
            if number == 0:
                raise ProjectMetadataError(f"unclassified fence: {relative}:{number + 1}")
            directive = DIRECTIVE.fullmatch(lines[number - 1])
            if not directive:
                raise ProjectMetadataError(f"unclassified fence: {relative}:{number + 1}")
            kind, example_id, reason = directive.groups()
            if example_id in found:
                raise ProjectMetadataError(f"duplicate source example ID: {example_id}")
            found[example_id] = {
                "source": relative,
                "language": fence.group(1),
                "mode": "executable" if kind == "example" else "non-executable",
                "reason": reason or "",
            }
        if open_fence:
            raise ProjectMetadataError(f"unclosed fence: {relative}")
    return found


def validate_examples(root: Path = ROOT, manifest_path: Path | None = None) -> None:
    path = manifest_path or root / "docs/examples.toml"
    data = _load_toml(path)
    if set(data) != {"schema", "contract_id", "sources", "examples"}:
        raise ProjectMetadataError("example manifest top-level fields invalid")
    if data["schema"] != 1 or data["contract_id"] != CONTRACT_ID:
        raise ProjectMetadataError("example manifest contract binding invalid")
    sources = data["sources"]
    entries = data["examples"]
    if not isinstance(sources, list) or not sources or len(sources) != len(set(sources)):
        raise ProjectMetadataError("example source list invalid")
    if not isinstance(entries, list) or not entries:
        raise ProjectMetadataError("example entries missing")
    directives = _source_directives(root, sources)
    profiles = set(json.loads((root / "tools/dev_profiles.json").read_text(encoding="utf-8"))["profiles"])
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ProjectMetadataError("example entry is not a table")
        example_id = entry.get("id")
        if not isinstance(example_id, str) or example_id in seen:
            raise ProjectMetadataError(f"invalid or duplicate example ID: {example_id}")
        seen.add(example_id)
        source = directives.get(example_id)
        if source is None:
            raise ProjectMetadataError(f"orphan manifest example: {example_id}")
        common = {"id", "source", "language", "mode"}
        if any(entry.get(key) != source[key] for key in ("source", "language", "mode")):
            raise ProjectMetadataError(f"example locator drift: {example_id}")
        if entry["mode"] == "executable":
            if set(entry) != common | {"profile", "validators"}:
                raise ProjectMetadataError(f"executable example fields invalid: {example_id}")
            if entry["profile"] not in profiles:
                raise ProjectMetadataError(f"unsupported example profile: {example_id}")
            validators = entry["validators"]
            if not isinstance(validators, list) or not validators or any(
                not isinstance(item, str) or not _pytest_function_exists(root, item)
                for item in validators
            ):
                raise ProjectMetadataError(f"missing exact validator node ID: {example_id}")
            if any(_validator_profile(item) != entry["profile"] for item in validators):
                raise ProjectMetadataError(f"validator profile ownership drift: {example_id}")
        elif entry["mode"] == "non-executable":
            if set(entry) != common | {"reason"} or entry.get("reason") != source["reason"]:
                raise ProjectMetadataError(f"non-executable reason drift: {example_id}")
            if not entry["reason"].strip():
                raise ProjectMetadataError(f"non-executable reason missing: {example_id}")
        else:
            raise ProjectMetadataError(f"unknown example mode: {example_id}")
    if seen != set(directives):
        raise ProjectMetadataError("source and manifest example sets differ")


def _validate_generated(version: str) -> None:
    try:
        facts = json.loads((ROOT / "docs/project-facts.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectMetadataError(f"generated facts invalid: {exc}") from exc
    if facts.get("schema") != "mathhead.project-facts.v1":
        raise ProjectMetadataError("generated facts schema invalid")
    if facts.get("contract") != {"id": CONTRACT_ID, "sha256": EXPECTED_SHA256}:
        raise ProjectMetadataError("generated facts contract binding drift")
    if facts.get("package") != {"version": version}:
        raise ProjectMetadataError("generated package version drift")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    begin = "<!-- BEGIN MATHHEAD PROJECT FACTS -->"
    end = "<!-- END MATHHEAD PROJECT FACTS -->"
    if readme.count(begin) != 1 or readme.count(end) != 1:
        raise ProjectMetadataError("README generated region invalid")
    before, rest = readme.split(begin, 1)
    region, after = rest.split(end, 1)
    outside = before + after
    stale_patterns = (
        r"\b\d+ MCP tools\b",
        r"\b\d+ tests green\b",
        r"Package \(SemVer\) \| `\d+\.\d+(?:\.\d+|\.x)`",
    )
    if any(re.search(pattern, outside) for pattern in stale_patterns):
        raise ProjectMetadataError("README current numeric claim escaped generator ownership")
    expected_claims = (
        f"Package `{version}`",
        f"{facts['mcp_tools']['count']} MCP tools",
        f"{facts['pytest']['count']} collected tests",
    )
    if any(claim not in region for claim in expected_claims):
        raise ProjectMetadataError("README generated facts disagree with JSON")


def validate() -> None:
    _validate_contract()
    version = _validate_version()
    validate_examples()
    _validate_generated(version)
    source = (ROOT / "tools/project_facts.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(main_nodes) != 1:
        raise ProjectMetadataError("project_facts main signature drift")
    main_node = main_nodes[0]
    signature_valid = (
        len(main_node.args.args) == 1
        and main_node.args.args[0].arg == "argv"
        and ast.unparse(main_node.args.args[0].annotation) == "Sequence[str] | None"
        and len(main_node.args.defaults) == 1
        and isinstance(main_node.args.defaults[0], ast.Constant)
        and main_node.args.defaults[0].value is None
        and ast.unparse(main_node.returns) == "int"
    )
    if not signature_valid:
        raise ProjectMetadataError("project_facts main signature drift")
    if f'CONTRACT_ID = "{CONTRACT_ID}"' not in source or f'CONTRACT_SHA256 = "{EXPECTED_SHA256}"' not in source:
        raise ProjectMetadataError("project_facts contract constants drift")


def main() -> int:
    try:
        validate()
    except (ProjectMetadataError, OSError, UnicodeError, SyntaxError, ValueError, KeyError) as exc:
        print(f"project-metadata: FAIL: {exc}", file=sys.stderr)
        return 1
    print("project-metadata: PASS (version/facts/examples/README)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
