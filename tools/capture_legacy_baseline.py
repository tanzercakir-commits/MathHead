#!/usr/bin/env python3
"""Capture and offline-replay the immutable MathHead legacy baseline."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 in the governed core profile.
    import tomli as tomllib
from typing import Any


SCHEMA = "mathhead.legacy-baseline.v1"
OBSERVATION_SCHEMA = "mathhead.legacy-observations.v1"
CONTRACT_ID = "MH-C-BASELINE-001"
CONTRACT_SHA256 = "3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2"
RESULT_STATES = ("failed", "not_run", "passed", "timed_out", "unsupported")
HEX_40_OR_64 = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
HEX_64 = re.compile(r"[0-9a-f]{64}")
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
TOP_LEVEL_KEYS = {"contract", "observations", "provenance", "schema", "source"}
OBSERVATION_KEYS = {
    "benchmarks",
    "ci_runs",
    "failure_categories",
    "performance_hotspots",
    "platform_failures",
    "profile_results",
    "result_counts",
}


class BaselineError(RuntimeError):
    """A stable, expected capture or replay failure."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SourceFile:
    path: str
    mode: str
    object_id: str
    content: bytes

    def inventory_record(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "object_id": self.object_id,
            "path": self.path,
            "sha256": hashlib.sha256(self.content).hexdigest(),
            "size": len(self.content),
        }


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _relative_path(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise BaselineError("invalid-path", f"{label} must be a nonempty POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or WINDOWS_ABSOLUTE.match(value) or ".." in path.parts:
        raise BaselineError("invalid-path", f"{label} must stay inside the repository")
    normal = path.as_posix()
    if normal in {"", "."} or normal != value:
        raise BaselineError("invalid-path", f"{label} is not canonical: {value}")
    return normal


def _exact_existing_file(root: Path, relative: str, *, label: str) -> Path:
    relative = _relative_path(relative, label=label)
    current = root
    for part in PurePosixPath(relative).parts:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            raise BaselineError("path-inspection-failed", f"cannot inspect {label}: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise BaselineError(
                    "path-case-mismatch", f"{label} expected {part!r}, found {aliases[0]!r}"
                )
            raise BaselineError("path-missing", f"{label} does not exist: {relative}")
        current /= part
    if not current.is_file():
        raise BaselineError("path-not-file", f"{label} is not a file: {relative}")
    return current


def _new_output_path(root: Path, relative: str) -> Path:
    relative = _relative_path(relative, label="destination")
    parts = PurePosixPath(relative).parts
    current = root
    for part in parts[:-1]:
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            raise BaselineError("path-inspection-failed", f"cannot inspect destination: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise BaselineError(
                    "path-case-mismatch", f"destination expected {part!r}, found {aliases[0]!r}"
                )
            raise BaselineError("destination-parent-missing", f"destination parent is absent: {part}")
        current /= part
        if not current.is_dir():
            raise BaselineError("destination-parent-invalid", f"destination parent is not a directory: {part}")
    destination = current / parts[-1]
    if destination.exists():
        raise BaselineError("destination-exists", f"destination already exists: {relative}")
    return destination


def _run_git(root: Path, args: Sequence[str], *, timeout: int = 60) -> bytes:
    command = ["git", *args]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise BaselineError("git-unavailable", "git executable is unavailable") from exc
    except subprocess.TimeoutExpired as exc:
        raise BaselineError("git-timeout", f"git command exceeded {timeout} seconds") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise BaselineError("git-failed", f"git {' '.join(args)} failed{suffix}")
    return result.stdout


def _resolve_source(root: Path, source_ref: str) -> tuple[str, str]:
    if not source_ref or source_ref.startswith("-"):
        raise BaselineError("invalid-source-ref", "source reference is empty or option-like")
    raw_commit = _run_git(root, ["rev-parse", "--verify", f"{source_ref}^{{commit}}"])
    commit = raw_commit.decode("ascii", errors="strict").strip()
    if not HEX_40_OR_64.fullmatch(commit):
        raise BaselineError("invalid-source-identity", "resolved commit identity is malformed")
    try:
        _run_git(root, ["merge-base", "--is-ancestor", commit, "HEAD"])
    except BaselineError as exc:
        raise BaselineError(
            "source-not-ancestor", "source commit must be an ancestor of the capture commit"
        ) from exc
    tree = _run_git(root, ["rev-parse", f"{commit}^{{tree}}"]).decode("ascii").strip()
    if not HEX_40_OR_64.fullmatch(tree):
        raise BaselineError("invalid-tree-identity", "resolved tree identity is malformed")
    return commit, tree


def _source_files(root: Path, commit: str) -> list[SourceFile]:
    raw_tree = _run_git(root, ["ls-tree", "-r", "-z", "--full-tree", commit])
    metadata: dict[str, tuple[str, str]] = {}
    for raw in raw_tree.split(b"\0"):
        if not raw:
            continue
        try:
            head, path_bytes = raw.split(b"\t", 1)
            mode, kind, object_id = head.decode("ascii").split(" ")
            path = path_bytes.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise BaselineError("git-tree-malformed", "git tree output is malformed") from exc
        _relative_path(path, label="tracked path")
        if kind != "blob":
            raise BaselineError("unsupported-tree-entry", f"tracked entry is not a blob: {path}")
        metadata[path] = (mode, object_id)

    archive = _run_git(root, ["archive", "--format=tar", commit], timeout=120)
    contents: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as handle:
            for member in handle.getmembers():
                if member.isdir():
                    continue
                path = PurePosixPath(member.name).as_posix().removesuffix("/")
                if member.issym():
                    contents[path] = member.linkname.encode("utf-8")
                elif member.isfile():
                    stream = handle.extractfile(member)
                    if stream is None:
                        raise BaselineError("archive-read-failed", f"cannot read archived path: {path}")
                    contents[path] = stream.read()
                else:
                    raise BaselineError("unsupported-archive-entry", f"unsupported archived path: {path}")
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise BaselineError("archive-read-failed", f"cannot inspect source archive: {exc}") from exc
    if set(metadata) != set(contents):
        missing = sorted(set(metadata) ^ set(contents))
        raise BaselineError("archive-tree-mismatch", f"archive/tree mismatch: {missing[:3]}")
    return [
        SourceFile(path, metadata[path][0], metadata[path][1], contents[path])
        for path in sorted(metadata)
    ]


def _decode_utf8(source: SourceFile) -> str:
    try:
        return source.content.decode("utf-8")
    except UnicodeError as exc:
        raise BaselineError("source-not-utf8", f"required source is not UTF-8: {source.path}") from exc


def _package_metadata(files: dict[str, SourceFile]) -> dict[str, Any]:
    try:
        pyproject_source = files["pyproject.toml"]
    except KeyError as exc:
        raise BaselineError("package-metadata-missing", "source tree has no pyproject.toml") from exc
    try:
        document = tomllib.loads(_decode_utf8(pyproject_source))
        project = document["project"]
        build = document["build-system"]
    except (KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise BaselineError("package-metadata-invalid", f"cannot parse package metadata: {exc}") from exc
    selected = {
        "build_system": {
            "backend": build.get("build-backend"),
            "requires": build.get("requires", []),
        },
        "dependencies": project.get("dependencies", []),
        "description": project.get("description"),
        "name": project.get("name"),
        "optional_dependencies": project.get("optional-dependencies", {}),
        "requires_python": project.get("requires-python"),
        "scripts": project.get("scripts", {}),
        "version": project.get("version"),
        "wheel_packages": document.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages", []),
    }
    if not all(isinstance(selected[key], str) and selected[key] for key in ("name", "version", "requires_python")):
        raise BaselineError("package-metadata-invalid", "required project metadata is absent")
    return selected


def _static_test_collection(files: dict[str, SourceFile]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path, source in sorted(files.items()):
        pure = PurePosixPath(path)
        if not path.startswith("tests/") or not pure.name.startswith("test") or pure.suffix != ".py":
            continue
        try:
            tree = ast.parse(_decode_utf8(source), filename=path)
        except SyntaxError as exc:
            raise BaselineError("test-source-invalid", f"cannot parse {path}: line {exc.lineno}") from exc
        digest = hashlib.sha256(source.content).hexdigest()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                items.append(
                    {"line": node.lineno, "nodeid": f"{path}::{node.name}", "source_sha256": digest}
                )
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test"):
                        items.append(
                            {
                                "line": child.lineno,
                                "nodeid": f"{path}::{node.name}::{child.name}",
                                "source_sha256": digest,
                            }
                        )
    items.sort(key=lambda item: item["nodeid"])
    nodeids = [item["nodeid"] for item in items]
    if len(nodeids) != len(set(nodeids)):
        raise BaselineError("duplicate-test-identity", "static test identities are not unique")
    return {"collector": "python-ast-static-v1", "count": len(items), "items": items}


class _FunctionCollector(ast.NodeVisitor):
    def __init__(self, path: str, digest: str):
        self.path = path
        self.digest = digest
        self.scope: list[str] = []
        self.items: list[dict[str, Any]] = []

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        end = getattr(node, "end_lineno", None) or node.lineno
        qualname = ".".join([*self.scope, node.name])
        self.items.append(
            {
                "end_line": end,
                "line_span": end - node.lineno + 1,
                "path": self.path,
                "qualname": qualname,
                "source_sha256": self.digest,
                "start_line": node.lineno,
            }
        )
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()


def _static_hotspots(files: dict[str, SourceFile]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for path, source in sorted(files.items()):
        if not path.endswith(".py") or not (path.startswith("src/") or path.startswith("tools/")):
            continue
        try:
            tree = ast.parse(_decode_utf8(source), filename=path)
        except SyntaxError as exc:
            raise BaselineError("python-source-invalid", f"cannot parse {path}: line {exc.lineno}") from exc
        collector = _FunctionCollector(path, hashlib.sha256(source.content).hexdigest())
        collector.visit(tree)
        items.extend(collector.items)
    items.sort(key=lambda item: (-item["line_span"], item["path"], item["qualname"]))
    return {"metric": "function-line-span", "limit": 25, "items": items[:25]}


def _dispatcher(files: dict[str, SourceFile]) -> dict[str, Any]:
    try:
        source = files["tools/dev_profiles.json"]
        document = json.loads(_decode_utf8(source))
        profiles = document["profiles"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise BaselineError("dispatcher-manifest-invalid", f"cannot parse dispatcher manifest: {exc}") from exc
    if not isinstance(profiles, dict) or not profiles:
        raise BaselineError("dispatcher-manifest-invalid", "dispatcher declares no profiles")
    result = []
    for name, profile in sorted(profiles.items()):
        if not isinstance(name, str) or not isinstance(profile, dict):
            raise BaselineError("dispatcher-manifest-invalid", "dispatcher profile is malformed")
        result.append(
            {
                "commands": sorted(
                    command.get("id")
                    for command in profile.get("commands", [])
                    if isinstance(command, dict) and isinstance(command.get("id"), str)
                ),
                "name": name,
                "supported_platforms": sorted(profile.get("platforms", [])),
            }
        )
    return {
        "manifest_sha256": hashlib.sha256(source.content).hexdigest(),
        "profiles": result,
    }


def _source_section(root: Path, source_ref: str) -> tuple[dict[str, Any], dict[str, SourceFile]]:
    commit, tree = _resolve_source(root, source_ref)
    sources = _source_files(root, commit)
    by_path = {source.path: source for source in sources}
    return (
        {
            "commit": commit,
            "dispatcher": _dispatcher(by_path),
            "inventory": {
                "count": len(sources),
                "files": [source.inventory_record() for source in sources],
            },
            "package": _package_metadata(by_path),
            "static_hotspots": _static_hotspots(by_path),
            "test_collection": _static_test_collection(by_path),
            "tree": tree,
        },
        by_path,
    )


def _is_absolute_checkout_string(value: str) -> bool:
    return value.startswith("/") or bool(WINDOWS_ABSOLUTE.match(value))


def _validate_result(record: dict[str, Any], *, label: str, profiles: set[str]) -> None:
    required = {
        "command",
        "exit_code",
        "id",
        "interpreter",
        "output_identity",
        "platform",
        "profile",
        "provenance",
        "status",
        "test_counts",
    }
    if set(record) != required:
        raise BaselineError("observation-schema", f"{label} has missing or unknown fields")
    for key in ("command", "id", "interpreter", "output_identity", "platform", "profile"):
        if not isinstance(record[key], str) or not record[key]:
            raise BaselineError("observation-schema", f"{label}.{key} must be nonempty text")
    if record["profile"] not in profiles:
        raise BaselineError("unknown-profile", f"{label} names unknown profile {record['profile']}")
    status = record["status"]
    exit_code = record["exit_code"]
    if status not in RESULT_STATES:
        raise BaselineError("invalid-result-state", f"{label} has invalid status {status!r}")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        raise BaselineError("observation-schema", f"{label}.exit_code must be integer or null")
    if status == "passed" and exit_code != 0:
        raise BaselineError("result-inconsistent", f"{label} passed without exit code 0")
    if status in {"failed", "unsupported"} and (exit_code is None or exit_code == 0):
        raise BaselineError("result-inconsistent", f"{label} {status} without nonzero exit code")
    if status == "not_run" and exit_code is not None:
        raise BaselineError("result-inconsistent", f"{label} not_run must have null exit code")
    counts = record["test_counts"]
    if set(counts) != {"failed", "passed", "skipped", "total"} or not all(
        isinstance(value, int) and not isinstance(value, bool) and value >= 0
        for value in counts.values()
    ):
        raise BaselineError("observation-schema", f"{label}.test_counts is malformed")
    if counts["total"] != counts["failed"] + counts["passed"] + counts["skipped"]:
        raise BaselineError("test-count-mismatch", f"{label}.test_counts do not sum to total")
    provenance = record["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"kind", "locator"}:
        raise BaselineError("observation-schema", f"{label}.provenance is malformed")
    if provenance["kind"] not in {"github-job", "github-run", "local-file"}:
        raise BaselineError("observation-schema", f"{label}.provenance kind is unsupported")
    if not isinstance(provenance["locator"], str) or not provenance["locator"]:
        raise BaselineError("observation-schema", f"{label}.provenance locator is missing")
    for value in record.values():
        if isinstance(value, str) and _is_absolute_checkout_string(value):
            raise BaselineError("absolute-path-leak", f"{label} contains an absolute checkout path")


def _validate_local_evidence(
    record: dict[str, Any], *, label: str, source_files: dict[str, SourceFile]
) -> None:
    required = {
        "command",
        "exit_code",
        "id",
        "interpreter",
        "metrics",
        "output_identity",
        "platform",
        "profile",
        "source_path",
        "source_sha256",
        "status",
    }
    if set(record) != required:
        raise BaselineError("observation-schema", f"{label} has missing or unknown fields")
    path = _relative_path(record["source_path"], label=f"{label}.source_path")
    digest = record["source_sha256"]
    if path not in source_files or not isinstance(digest, str) or not HEX_64.fullmatch(digest):
        raise BaselineError("local-evidence-missing", f"{label} has no source-tree evidence")
    actual = hashlib.sha256(source_files[path].content).hexdigest()
    if actual != digest:
        raise BaselineError("local-evidence-drift", f"{label} source SHA-256 mismatch")
    if record["output_identity"] != f"sha256:{digest}":
        raise BaselineError("local-output-identity", f"{label} output identity is not its SHA-256")
    if not isinstance(record["metrics"], dict):
        raise BaselineError("observation-schema", f"{label}.metrics must be an object")
    synthetic = dict(record)
    synthetic.pop("metrics")
    synthetic.pop("source_path")
    synthetic.pop("source_sha256")
    synthetic["provenance"] = {"kind": "local-file", "locator": path}
    synthetic["test_counts"] = {"failed": 0, "passed": 0, "skipped": 0, "total": 0}
    _validate_result(synthetic, label=label, profiles={record["profile"]})


def _sorted_unique(items: list[dict[str, Any]], key: str, *, label: str) -> None:
    values = [item.get(key) for item in items]
    if not all(isinstance(value, (str, int)) for value in values):
        raise BaselineError("observation-schema", f"{label} has an invalid {key}")
    if values != sorted(values) or len(values) != len(set(values)):
        raise BaselineError("observation-order", f"{label} must be uniquely sorted by {key}")


def _validate_observations(
    document: Any, *, source_commit: str, source_files: dict[str, SourceFile]
) -> dict[str, Any]:
    required = {
        "benchmarks",
        "ci_runs",
        "failure_categories",
        "performance_hotspots",
        "platform_failures",
        "profile_results",
        "schema",
        "source_commit",
    }
    if not isinstance(document, dict) or set(document) != required:
        raise BaselineError("observation-schema", "observation document has missing or unknown fields")
    if document["schema"] != OBSERVATION_SCHEMA or document["source_commit"] != source_commit:
        raise BaselineError("observation-source-mismatch", "observation schema or source commit mismatch")
    for name in required - {"schema", "source_commit"}:
        if not isinstance(document[name], list):
            raise BaselineError("observation-schema", f"observation section {name} must be a list")

    dispatcher = json.loads(_decode_utf8(source_files["tools/dev_profiles.json"]))
    profiles = set(dispatcher["profiles"])
    profile_results = document["profile_results"]
    _sorted_unique(profile_results, "id", label="profile_results")
    for index, record in enumerate(profile_results):
        if not isinstance(record, dict):
            raise BaselineError("observation-schema", f"profile_results[{index}] must be an object")
        _validate_result(record, label=f"profile_results[{index}]", profiles=profiles)
    recorded_profiles = {record["profile"] for record in profile_results}
    if recorded_profiles != profiles:
        missing = sorted(profiles - recorded_profiles)
        raise BaselineError("profile-evidence-incomplete", f"profiles have no explicit result: {missing}")

    benchmarks = document["benchmarks"]
    _sorted_unique(benchmarks, "id", label="benchmarks")
    for index, record in enumerate(benchmarks):
        if not isinstance(record, dict):
            raise BaselineError("observation-schema", f"benchmarks[{index}] must be an object")
        _validate_local_evidence(record, label=f"benchmarks[{index}]", source_files=source_files)

    ci_runs = document["ci_runs"]
    _sorted_unique(ci_runs, "run_id", label="ci_runs")
    run_keys = {"conclusion", "head_sha", "name", "run_id", "status", "url", "workflow"}
    for index, record in enumerate(ci_runs):
        if not isinstance(record, dict) or set(record) != run_keys:
            raise BaselineError("observation-schema", f"ci_runs[{index}] is malformed")
        if record["status"] not in RESULT_STATES or record["conclusion"] not in {
            "failure", "success"
        }:
            raise BaselineError("invalid-result-state", f"ci_runs[{index}] has invalid result")
        if record["head_sha"] != source_commit or not isinstance(record["run_id"], int):
            raise BaselineError("observation-source-mismatch", f"ci_runs[{index}] source mismatch")
        expected = f"https://github.com/tanzercakir-commits/MathHead/actions/runs/{record['run_id']}"
        if record["url"] != expected:
            raise BaselineError("unstable-ci-locator", f"ci_runs[{index}] URL is not immutable")

    simple_sections = {
        "failure_categories": {
            "category", "evidence_locators", "id", "profiles", "status", "summary"
        },
        "platform_failures": {
            "category", "evidence_locator", "id", "interpreter", "platform", "status", "summary"
        },
        "performance_hotspots": {
            "category", "evidence_locator", "id", "path", "status", "summary", "symbol"
        },
    }
    for section, keys in simple_sections.items():
        records = document[section]
        _sorted_unique(records, "id", label=section)
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != keys:
                raise BaselineError("observation-schema", f"{section}[{index}] is malformed")
            if record["status"] not in RESULT_STATES:
                raise BaselineError("invalid-result-state", f"{section}[{index}] has invalid status")
            if not all(isinstance(value, str) and value for key, value in record.items() if key not in {"evidence_locators", "profiles"}):
                raise BaselineError("observation-schema", f"{section}[{index}] has empty evidence")
            if "evidence_locators" in record and (
                not isinstance(record["evidence_locators"], list)
                or not record["evidence_locators"]
                or record["evidence_locators"] != sorted(set(record["evidence_locators"]))
            ):
                raise BaselineError("observation-order", f"{section}[{index}] locators are invalid")
            if "profiles" in record and (
                not isinstance(record["profiles"], list)
                or record["profiles"] != sorted(set(record["profiles"]))
                or not set(record["profiles"]).issubset(profiles)
            ):
                raise BaselineError("observation-order", f"{section}[{index}] profiles are invalid")

    if not document["failure_categories"] or not document["platform_failures"]:
        raise BaselineError("failure-evidence-missing", "known failures and platform failures are required")
    if not document["performance_hotspots"]:
        raise BaselineError("hotspot-evidence-missing", "performance hot spots are required")
    counts = Counter(record["status"] for record in [*profile_results, *benchmarks])
    result_counts = {state: counts.get(state, 0) for state in RESULT_STATES}
    return {
        "benchmarks": benchmarks,
        "ci_runs": ci_runs,
        "failure_categories": document["failure_categories"],
        "performance_hotspots": document["performance_hotspots"],
        "platform_failures": document["platform_failures"],
        "profile_results": profile_results,
        "result_counts": result_counts,
    }


def _accepted_contract(root: Path) -> None:
    accepted = _exact_existing_file(
        root, "docs/contracts/MH-C-BASELINE-001.json", label="accepted baseline contract"
    )
    proposal = _exact_existing_file(
        root,
        "docs/contracts/proposed/MH-C-BASELINE-001.json",
        label="baseline contract proposal",
    )
    for path in (accepted, proposal):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != CONTRACT_SHA256:
            raise BaselineError("contract-hash-mismatch", f"contract SHA-256 drift: {path.name}")


def capture(root: Path, source_ref: str, observations_path: str, output_path: str) -> dict[str, Any]:
    _accepted_contract(root)
    destination = _new_output_path(root, output_path)
    observations_file = _exact_existing_file(root, observations_path, label="observations")
    source, source_files = _source_section(root, source_ref)
    try:
        raw_observations = observations_file.read_bytes()
        observation_document = json.loads(raw_observations.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BaselineError("observation-read-failed", f"cannot read observations: {exc}") from exc
    observations = _validate_observations(
        observation_document, source_commit=source["commit"], source_files=source_files
    )
    artifact = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "observations": observations,
        "provenance": {
            "epistemic_classes": [
                "not_run",
                "observed",
                "replayed",
                "reported_external",
                "source_derived",
            ],
            "observations_path": observations_path,
            "observations_sha256": hashlib.sha256(raw_observations).hexdigest(),
        },
        "schema": SCHEMA,
        "source": source,
    }
    try:
        destination.write_bytes(_canonical_bytes(artifact))
    except OSError as exc:
        raise BaselineError("destination-write-failed", f"cannot create baseline artifact: {exc}") from exc
    return artifact


def _validate_artifact_shape(artifact: Any) -> None:
    if not isinstance(artifact, dict) or set(artifact) != TOP_LEVEL_KEYS:
        raise BaselineError("artifact-schema", "artifact has missing or unknown top-level fields")
    if artifact["schema"] != SCHEMA:
        raise BaselineError("artifact-schema", "artifact schema identifier mismatch")
    if artifact["contract"] != {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256}:
        raise BaselineError("artifact-contract", "artifact contract binding mismatch")
    source = artifact["source"]
    source_keys = {
        "commit", "dispatcher", "inventory", "package", "static_hotspots", "test_collection", "tree"
    }
    if not isinstance(source, dict) or set(source) != source_keys:
        raise BaselineError("artifact-schema", "source section has missing or unknown fields")
    inventory = source["inventory"]
    if not isinstance(inventory, dict) or set(inventory) != {"count", "files"}:
        raise BaselineError("artifact-schema", "inventory section is malformed")
    files = inventory["files"]
    if inventory["count"] != len(files):
        raise BaselineError("inventory-count-mismatch", "inventory count does not match file records")
    paths = [record.get("path") for record in files]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise BaselineError("inventory-order", "inventory paths are not unique and sorted")
    for index, record in enumerate(files):
        if set(record) != {"mode", "object_id", "path", "sha256", "size"}:
            raise BaselineError("artifact-schema", f"inventory record {index} is malformed")
        _relative_path(record["path"], label=f"inventory[{index}].path")
        if not HEX_64.fullmatch(record["sha256"]):
            raise BaselineError("artifact-schema", f"inventory record {index} has invalid SHA-256")
    tests = source["test_collection"]
    if not isinstance(tests, dict) or set(tests) != {"collector", "count", "items"}:
        raise BaselineError("artifact-schema", "test collection is malformed")
    if tests["count"] != len(tests["items"]):
        raise BaselineError("test-count-mismatch", "test collection count does not match identities")
    nodeids = [record.get("nodeid") for record in tests["items"]]
    if nodeids != sorted(nodeids) or len(nodeids) != len(set(nodeids)):
        raise BaselineError("test-order", "test identities are not unique and sorted")
    observations = artifact["observations"]
    if not isinstance(observations, dict) or set(observations) != OBSERVATION_KEYS:
        raise BaselineError("artifact-schema", "observations section has missing or unknown fields")
    counts = Counter(
        record.get("status")
        for record in [*observations["profile_results"], *observations["benchmarks"]]
    )
    expected_counts = {state: counts.get(state, 0) for state in RESULT_STATES}
    if observations["result_counts"] != expected_counts:
        raise BaselineError("result-count-mismatch", "observation result counts do not match records")
    provenance = artifact["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {
        "epistemic_classes", "observations_path", "observations_sha256"
    }:
        raise BaselineError("artifact-schema", "provenance section is malformed")
    _relative_path(provenance["observations_path"], label="provenance.observations_path")
    if not HEX_64.fullmatch(provenance["observations_sha256"]):
        raise BaselineError("artifact-schema", "observations provenance SHA-256 is malformed")


def replay(root: Path, artifact_path: str) -> dict[str, Any]:
    _accepted_contract(root)
    path = _exact_existing_file(root, artifact_path, label="baseline artifact")
    try:
        raw = path.read_bytes()
        artifact = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BaselineError("artifact-read-failed", f"cannot read baseline artifact: {exc}") from exc
    if raw != _canonical_bytes(artifact):
        raise BaselineError("artifact-not-canonical", "artifact bytes are not canonical JSON")
    _validate_artifact_shape(artifact)
    source, source_files = _source_section(root, artifact["source"]["commit"])
    if artifact["source"] != source:
        raise BaselineError("source-replay-mismatch", "source-derived fields changed during replay")
    observation_path = artifact["provenance"]["observations_path"]
    current_observations = _exact_existing_file(root, observation_path, label="observations")
    raw_observations = current_observations.read_bytes()
    if hashlib.sha256(raw_observations).hexdigest() != artifact["provenance"]["observations_sha256"]:
        raise BaselineError("observation-hash-mismatch", "observation input SHA-256 changed")
    try:
        observation_document = json.loads(raw_observations.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise BaselineError("observation-read-failed", f"cannot decode observations: {exc}") from exc
    observations = _validate_observations(
        observation_document, source_commit=source["commit"], source_files=source_files
    )
    if artifact["observations"] != observations:
        raise BaselineError("observation-replay-mismatch", "embedded observations changed")
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--debug", action="store_true")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    capture_parser = subparsers.add_parser("capture", help="create one new canonical baseline")
    capture_parser.add_argument("--source-ref", required=True)
    capture_parser.add_argument("--observations", required=True)
    capture_parser.add_argument("--output", required=True)
    replay_parser = subparsers.add_parser("replay", help="recompute source-derived baseline fields")
    replay_parser.add_argument("--artifact", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.operation == "capture":
            artifact = capture(root, args.source_ref, args.observations, args.output)
            digest = hashlib.sha256(_canonical_bytes(artifact)).hexdigest()
            print(
                "legacy-baseline: CAPTURED "
                f"source={artifact['source']['commit']} files={artifact['source']['inventory']['count']} "
                f"tests={artifact['source']['test_collection']['count']} sha256={digest}"
            )
        else:
            artifact = replay(root, args.artifact)
            print(
                "legacy-baseline: REPLAYED "
                f"source={artifact['source']['commit']} files={artifact['source']['inventory']['count']} "
                f"tests={artifact['source']['test_collection']['count']}"
            )
    except KeyboardInterrupt:
        print("legacy-baseline: FAIL [interrupted]: operation interrupted", file=sys.stderr)
        return 130
    except BaselineError as exc:
        print(f"legacy-baseline: FAIL [{exc.code}]: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # Expected failures above never leak tracebacks.
        if args.debug:
            raise
        print(f"legacy-baseline: FAIL [internal-error]: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
