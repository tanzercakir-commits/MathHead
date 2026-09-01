#!/usr/bin/env python3
"""Validate MH-036's written export and pinned external Lean boundary."""

from __future__ import annotations

import argparse
import ast
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
EXPORT_SOURCE = SOURCE_ROOT / "mathhead/proof_assistant/export.py"
RUNNER_SOURCE = SOURCE_ROOT / "mathhead/proof_assistant/lean.py"
PROVENANCE_SOURCE = SOURCE_ROOT / "mathhead/proof_assistant/provenance.py"
LEGACY_SOURCE = SOURCE_ROOT / "mathhead/discovery/lean_export.py"
CONTRACT = ROOT / "docs/contracts/MH-C-LEAN-VERIFICATION-001.json"
PROPOSAL = ROOT / "docs/contracts/proposed/MH-C-LEAN-VERIFICATION-001.json"
REQUEST_SCHEMA = ROOT / "docs/contracts/schemas/lean-verification-request-v1.schema.json"
RESULT_SCHEMA = ROOT / "docs/contracts/schemas/lean-verification-result-v1.schema.json"
TRUST = ROOT / "docs/trust/trust-base-v1.json"

CONTRACT_ID = "MH-C-LEAN-VERIFICATION-001"
CONTRACT_SHA256 = "b5c8bd2b3f93698d404042e7785d6dc503968481de13a77aee71769079a4b60a"
REQUEST_SCHEMA_SHA256 = (
    "696962e42cd29d08a7b38e6e0c8728244c4a3a58ef39a7cc2effe47f8a6ce58d"
)
RESULT_SCHEMA_SHA256 = (
    "109e7e71b71ccce3daea88ea0cfb9f4b112fb1eeecf49a732705892f1bfa9965"
)
DEPENDENCIES = {
    "Cli": "6130a47896ce867c6a4a55373441e59e565bad0f",
    "LeanSearchClient": "5f4d51b81cbd3f6b32b156bfad9056621a040404",
    "Qq": "92c15be17b7caf78c2ad767ec40f89052d908d81",
    "aesop": "3448c0bcc5ce01b2d1546e483ec3620e32df3d0e",
    "batteries": "4488d40d070b9700d4d5a6aa342f0d40c31b2a2d",
    "importGraph": "16f02aa7642864af59f1ff0e384a015994db9118",
    "mathlib": "db584cd6d46c92f209a44c0f1c829460d327499d",
    "plausible": "b7eb3304aeae834b12dda98993a37f6a41f6f0bb",
    "proofwidgets": "4be2e3d5087eeb272cf5a8853b8f9dd025ef5957",
}
PURE_ALLOWED_ROOTS = {
    "__future__",
    "dataclasses",
    "fractions",
    "hashlib",
    "json",
    "mathhead",
    "typing",
}
PURE_DENIED_ROOTS = {
    "importlib",
    "multiprocessing",
    "os",
    "pathlib",
    "random",
    "shutil",
    "socket",
    "subprocess",
    "sys",
    "tempfile",
    "time",
    "urllib",
}


class LeanVerificationContractError(ValueError):
    pass


def _fail(detail: str) -> NoReturn:
    raise LeanVerificationContractError(detail)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot load {path.relative_to(ROOT)}: {type(exc).__name__}")
    if type(value) is not dict:
        _fail(f"{path.relative_to(ROOT)} must contain an object")
    return value


def _import_roots(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        _fail(f"cannot parse {path.relative_to(ROOT)}: {type(exc).__name__}")
    roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    return roots


def _verify_artifacts() -> None:
    required = (
        CONTRACT,
        PROPOSAL,
        REQUEST_SCHEMA,
        RESULT_SCHEMA,
        EXPORT_SOURCE,
        RUNNER_SOURCE,
        PROVENANCE_SOURCE,
        LEGACY_SOURCE,
        TRUST,
    )
    for path in required:
        if not path.is_file():
            _fail(f"required artifact is missing: {path.relative_to(ROOT)}")
    if CONTRACT.read_bytes() != PROPOSAL.read_bytes():
        _fail("accepted Lean contract differs from its proposal")
    expected_hashes = {
        CONTRACT: CONTRACT_SHA256,
        REQUEST_SCHEMA: REQUEST_SCHEMA_SHA256,
        RESULT_SCHEMA: RESULT_SCHEMA_SHA256,
    }
    for path, expected in expected_hashes.items():
        if _sha(path) != expected:
            _fail(f"{path.relative_to(ROOT)} hash differs")
    contract = _load(CONTRACT)
    if contract.get("contract_id") != CONTRACT_ID:
        _fail("Lean contract ID differs")
    if contract.get("target") != "mathhead.proof_assistant.lean:verify_with_lean":
        _fail("Lean contract target differs")
    if contract.get("signature") != (
        "verify_with_lean(request: bytes, artifacts: tuple[bytes, ...], "
        "project_root: str) -> LeanVerificationResult"
    ):
        _fail("Lean contract signature differs")
    for schema in (_load(REQUEST_SCHEMA), _load(RESULT_SCHEMA)):
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            _fail("Lean schema is not Draft 2020-12")
        if schema.get("additionalProperties") is not False:
            _fail("Lean schema root is open")


def _verify_source_boundary() -> None:
    export_roots = _import_roots(EXPORT_SOURCE)
    if export_roots & PURE_DENIED_ROOTS or not export_roots <= PURE_ALLOWED_ROOTS:
        _fail(f"pure exporter imports effect roots: {sorted(export_roots)}")
    runner_roots = _import_roots(RUNNER_SOURCE)
    if not {"os", "pathlib", "stat", "subprocess", "sys"} <= runner_roots:
        _fail("external runner does not own the complete declared effect boundary")
    export_text = EXPORT_SOURCE.read_text(encoding="utf-8")
    runner_text = RUNNER_SOURCE.read_text(encoding="utf-8")
    if "mathhead.proof_assistant.lean" in export_text:
        _fail("pure exporter imports its effectful runner")
    bindings = (
        f'LEAN_VERIFICATION_CONTRACT_ID = "{CONTRACT_ID}"',
        'LEAN_VERIFICATION_CONTRACT_SHA256 = (\n    "' + CONTRACT_SHA256 + '"\n)',
    )
    for binding in bindings:
        if export_text.count(binding) != 1:
            _fail("exporter does not carry one exact contract binding")
    required_functions = {
        "execution_artifacts",
        "lean_verification_result_to_bytes",
        "parse_lean_verification_result",
        "prepare_lean_project",
        "validate_lean_verification_result",
        "verify_with_lean",
    }
    tree = ast.parse(runner_text)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not required_functions <= functions:
        _fail(f"Lean runner functions are missing: {sorted(required_functions - functions)}")
    provenance_text = PROVENANCE_SOURCE.read_text(encoding="utf-8")
    if "replay_provenance_bundle" not in provenance_text or "verify_with_lean" not in provenance_text:
        _fail("external Lean provenance dispatch is incomplete")
    legacy_text = LEGACY_SOURCE.read_text(encoding="utf-8")
    if "from mathhead.proof_assistant.export import build_lean_export" not in legacy_text:
        _fail("legacy Lean API is not an adapter over the canonical exporter")


def _verify_trust_inventory() -> None:
    inventory = _load(TRUST)
    surfaces = {
        item["surface_id"]: item
        for item in inventory.get("surfaces", [])
        if type(item) is dict and type(item.get("surface_id")) is str
    }
    surface = surfaces.get("proof-assistant.lean")
    if (
        type(surface) is not dict
        or surface.get("current_authority") != "external_proof_assistant"
        or surface.get("state") != "current_required"
    ):
        _fail("trust inventory does not activate the pinned Lean surface")
    expected_sources = {
        "src/mathhead/discovery/lean_export.py",
        "src/mathhead/proof_assistant/__init__.py",
        "src/mathhead/proof_assistant/export.py",
        "src/mathhead/proof_assistant/lean.py",
        "src/mathhead/proof_assistant/provenance.py",
    }
    if set(surface.get("source_paths", [])) != expected_sources:
        _fail("trust inventory Lean source ownership differs")
    entries = {
        item.get("target")
        for item in inventory.get("entry_points", [])
        if type(item) is dict
    }
    if not {
        "mathhead.proof_assistant.lean:verify_with_lean",
        "mathhead.proof_assistant.provenance:replay_lean_provenance",
    } <= entries:
        _fail("trust inventory lacks the external Lean entry points")


def _fixtures() -> tuple[object, ...]:
    from mathhead.kernel.proof_terms import crt, polynomial_identity, residue, sum_induction

    polynomial = (0, -1, 0, 1)
    return (
        residue(2, polynomial),
        crt((residue(2, polynomial), residue(3, polynomial))),
        sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
        polynomial_identity(polynomial, polynomial),
    )


def _verify_runtime_structure(project_root: Path) -> tuple[tuple[object, ...], int]:
    from mathhead.kernel.checkers import check_proof_term
    from mathhead.proof_assistant.export import (
        ACQUISITION_LAKEFILE_BYTES,
        ACQUISITION_MANIFEST_BYTES,
        LAKEFILE_BYTES,
        LAKE_MANIFEST_BYTES,
        LEAN_TOOLCHAIN_BYTES,
        TOOLCHAIN_LOCK_BYTES,
        build_lean_export,
        parse_lean_export,
    )
    from mathhead.proof_assistant.lean import (
        export_written_result,
        lean_verification_result_to_bytes,
        parse_lean_verification_result,
    )

    fixed = {
        "acquisition-lake-manifest.json": ACQUISITION_MANIFEST_BYTES,
        "acquisition-lakefile.toml": ACQUISITION_LAKEFILE_BYTES,
        "lake-manifest.json": LAKE_MANIFEST_BYTES,
        "lakefile.toml": LAKEFILE_BYTES,
        "lean-toolchain": LEAN_TOOLCHAIN_BYTES,
        "mathhead-lean-lock.json": TOOLCHAIN_LOCK_BYTES,
    }
    for relative, expected in fixed.items():
        path = project_root / relative
        if not path.is_file() or path.read_bytes() != expected:
            _fail(f"fixed Lean project bytes differ: {relative}")
    acquisition_manifest = json.loads(ACQUISITION_MANIFEST_BYTES)
    revisions = {
        item["name"]: item["rev"] for item in acquisition_manifest["packages"]
    }
    if revisions != DEPENDENCIES:
        _fail("complete transitive Lean dependency lock differs")
    runtime_manifest = json.loads(LAKE_MANIFEST_BYTES)
    runtime_paths = {
        item["name"]: item.get("dir") for item in runtime_manifest["packages"]
    }
    expected_paths = {name: f".lake/packages/{name}" for name in DEPENDENCIES}
    if runtime_paths != expected_paths or any(
        item.get("type") != "path" for item in runtime_manifest["packages"]
    ):
        _fail("hermetic runtime dependencies are not exact local paths")
    lock = json.loads(TOOLCHAIN_LOCK_BYTES)
    if lock.get("lake_manifest_sha256") != hashlib.sha256(LAKE_MANIFEST_BYTES).hexdigest():
        _fail("toolchain lock does not bind the full Lake manifest")
    if lock.get("acquisition_manifest_sha256") != hashlib.sha256(
        ACQUISITION_MANIFEST_BYTES
    ).hexdigest():
        _fail("toolchain lock does not bind the acquisition manifest")
    if lock.get("acquisition_lakefile_sha256") != hashlib.sha256(
        ACQUISITION_LAKEFILE_BYTES
    ).hexdigest():
        _fail("toolchain lock does not bind the acquisition lakefile")
    if lock.get("dependency_commits") != DEPENDENCIES:
        _fail("toolchain lock does not bind every dependency commit")

    exports = []
    total_source_bytes = 0
    for term in _fixtures():
        export = build_lean_export(term, check_proof_term(term))
        if parse_lean_export(export.request, export.artifacts) != export:
            _fail("canonical Lean export replay differs")
        pending = export_written_result(export)
        encoded = lean_verification_result_to_bytes(pending)
        if parse_lean_verification_result(encoded) != pending:
            _fail("written-only Lean result replay differs")
        exports.append(export)
        total_source_bytes += len(export.artifacts[1])
    if [item.statement_kind for item in exports] != [
        "divides",
        "divides",
        "sum_identity",
        "polynomial_identity",
    ]:
        _fail("Lean fixture coverage differs")
    signature = inspect.signature(__import__(
        "mathhead.proof_assistant.lean", fromlist=["verify_with_lean"]
    ).verify_with_lean)
    if list(signature.parameters) != ["request", "artifacts", "project_root"]:
        _fail("Lean runner parameter list differs")
    return tuple(exports), total_source_bytes


def _run_git(package: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(package), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        _fail(f"cannot inspect dependency {package.name}: {type(exc).__name__}")
    if completed.returncode != 0 or completed.stderr:
        _fail(f"cannot prove dependency identity: {package.name}")
    try:
        return completed.stdout.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError:
        _fail(f"dependency identity output is not ASCII: {package.name}")


def _verify_dependency_checkout(project_root: Path) -> None:
    packages = project_root / ".lake/packages"
    for name, revision in DEPENDENCIES.items():
        package = packages / name
        if not package.is_dir():
            _fail(f"locked dependency checkout is missing: {name}")
        if _run_git(package, "rev-parse", "HEAD") != revision:
            _fail(f"locked dependency revision differs: {name}")
        if _run_git(package, "status", "--porcelain", "--untracked-files=no"):
            _fail(f"locked dependency tracked files are dirty: {name}")


def _verify_live(project_root: Path, exports: tuple[object, ...]) -> int:
    from mathhead.proof_assistant.lean import (
        execution_artifacts,
        lean_verification_result_to_bytes,
        parse_lean_verification_result,
        prepare_lean_project,
        validate_lean_verification_result,
        verify_with_lean,
    )
    from mathhead.proof_assistant.provenance import replay_lean_provenance

    sys.path.insert(0, str(ROOT / "tests/provenance_replay"))
    from test_provenance_replay import _bundle

    _verify_dependency_checkout(project_root)
    provenance_manifest, provenance_objects = _bundle()
    result_schema = _load(RESULT_SCHEMA)
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        Draft202012Validator = None  # type: ignore[assignment,misc]
    verified = 0
    for index, export in enumerate(exports):
        if index == 0:
            result = replay_lean_provenance(
                provenance_manifest,
                provenance_objects,
                export.request,
                export.artifacts,
                str(project_root),
            )
        else:
            prepare_lean_project(export, str(project_root))
            result = verify_with_lean(export.request, export.artifacts, str(project_root))
        if result.status != "externally_verified" or result.authority != "external_proof_assistant":
            stdout = getattr(result, "_stdout", None) or b""
            stderr = getattr(result, "_stderr", None) or b""
            detail = (stdout + b"\n" + stderr).decode("utf-8", errors="replace")[-2000:]
            _fail(f"pinned Lean rejected {export.statement_kind}: {result.reason_code}: {detail}")
        validate_lean_verification_result(result, require_fresh=True)
        stdout, stderr, compiled = execution_artifacts(result)
        if hashlib.sha256(stdout).hexdigest() != result.stdout_sha256:
            _fail("fresh Lean stdout identity differs")
        if hashlib.sha256(stderr).hexdigest() != result.stderr_sha256:
            _fail("fresh Lean stderr identity differs")
        if hashlib.sha256(compiled).hexdigest() != result.compiled_artifact_sha256:
            _fail("fresh Lean compiled artifact identity differs")
        encoded = lean_verification_result_to_bytes(result)
        historical = parse_lean_verification_result(encoded)
        try:
            validate_lean_verification_result(historical, require_fresh=True)
        except ValueError:
            pass
        else:
            _fail("historical Lean result refreshed authority without execution")
        if Draft202012Validator is not None:
            Draft202012Validator(result_schema).validate(json.loads(encoded))
        verified += 1
    return verified


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=ROOT / "lean",
        help="prepared pinned Lean project root",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="require fresh external checks for all four proof rules",
    )
    return parser.parse_args()


def main() -> int:
    arguments = _arguments()
    project_root = arguments.project_root.resolve()
    sys.path.insert(0, str(SOURCE_ROOT))
    try:
        _verify_artifacts()
        _verify_source_boundary()
        _verify_trust_inventory()
        exports, source_bytes = _verify_runtime_structure(project_root)
        live = _verify_live(project_root, exports) if arguments.require_live else 0
    except (LeanVerificationContractError, OSError, UnicodeError, ValueError) as exc:
        print(f"lean-verification: FAIL: {exc}", file=sys.stderr)
        return 1
    live_label = str(live) if arguments.require_live else "not-requested"
    print(
        "lean-verification: PASS "
        f"(contract={CONTRACT_SHA256[:12]}, dependencies={len(DEPENDENCIES)}, "
        f"fixtures={len(exports)}, source_bytes={source_bytes}, live={live_label})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
