#!/usr/bin/env python3
"""Validate the accepted MH-035 provenance replay boundary."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "src"
PACKAGE_ROOT = SOURCE_ROOT / "mathhead"
SOURCE = PACKAGE_ROOT / "kernel/provenance.py"
STORE = PACKAGE_ROOT / "provenance_store.py"
LEGACY = PACKAGE_ROOT / "discovery/provenance.py"
CONTRACT = ROOT / "docs/contracts/MH-C-PROVENANCE-REPLAY-001.json"
PROPOSAL = ROOT / "docs/contracts/proposed/MH-C-PROVENANCE-REPLAY-001.json"
MANIFEST_SCHEMA = ROOT / "docs/contracts/schemas/provenance-manifest-v1.schema.json"
RESULT_SCHEMA = ROOT / "docs/contracts/schemas/provenance-replay-result-v1.schema.json"
TRUST = ROOT / "docs/trust/trust-base-v1.json"

CONTRACT_ID = "MH-C-PROVENANCE-REPLAY-001"
CONTRACT_SHA256 = "31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67"
MANIFEST_SCHEMA_SHA256 = "1c8be7ef43a42abf255e4799d60f2cccc8df05dfc82706f6de613fbf4f03776c"
RESULT_SCHEMA_SHA256 = "a40ac65f5d3560cb78be15ba121ba2d7e56c29c8d9f8abc2d10e4e8d07dcc4b0"
ALLOWED_ROOTS = {
    "__future__",
    "dataclasses",
    "fractions",
    "hashlib",
    "json",
    "math",
    "typing",
    "unicodedata",
}
DENIED_ROOTS = {
    "importlib",
    "mcp",
    "mpmath",
    "multiprocessing",
    "os",
    "pathlib",
    "pysat",
    "random",
    "shutil",
    "subprocess",
    "sympy",
    "sys",
    "tempfile",
    "time",
    "z3",
}


class ProvenanceContractError(ValueError):
    pass


def _fail(detail: str) -> NoReturn:
    raise ProvenanceContractError(detail)


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


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _module_path(module: str) -> Path | None:
    if module != "mathhead" and not module.startswith("mathhead."):
        return None
    relative = Path(*module.split("."))
    direct = SOURCE_ROOT / relative.with_suffix(".py")
    package = SOURCE_ROOT / relative / "__init__.py"
    if direct.is_file():
        return direct
    if package.is_file():
        return package
    _fail(f"unresolved internal import: {module}")


def _package_initializers(path: Path) -> set[Path]:
    result: set[Path] = set()
    parent = path.parent
    while parent == PACKAGE_ROOT or PACKAGE_ROOT in parent.parents:
        candidate = parent / "__init__.py"
        if candidate.is_file():
            result.add(candidate)
        if parent == PACKAGE_ROOT:
            break
        parent = parent.parent
    return result


def _resolve_from(path: Path, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    module = _module_name(path)
    base = module.split(".") if path.name == "__init__.py" else module.split(".")[:-1]
    remove = node.level - 1
    if remove > len(base):
        _fail(f"relative import escapes package: {path.relative_to(ROOT)}")
    base = base[: len(base) - remove]
    if node.module:
        base.extend(node.module.split("."))
    return ".".join(base)


def _closure(entry: Path) -> tuple[set[Path], set[str]]:
    pending = [entry]
    files: set[Path] = set()
    roots: set[str] = set()
    while pending:
        path = pending.pop()
        if path in files:
            continue
        files.add(path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_from(path, node)
                if resolved:
                    modules.append(resolved)
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id
                in {
                    "__import__",
                    "eval",
                    "exec",
                    "open",
                }
            ):
                _fail(f"dynamic or effect call {node.func.id} in {path.relative_to(ROOT)}")
            for module in modules:
                imported = _module_path(module)
                if imported is None:
                    roots.add(module.split(".", 1)[0])
                else:
                    pending.extend(_package_initializers(imported))
                    pending.append(imported)
    return files, roots


def _verify_artifacts() -> None:
    for path in (SOURCE, STORE, LEGACY, CONTRACT, PROPOSAL, MANIFEST_SCHEMA, RESULT_SCHEMA, TRUST):
        if not path.is_file():
            _fail(f"required artifact is missing: {path.relative_to(ROOT)}")
    if CONTRACT.read_bytes() != PROPOSAL.read_bytes():
        _fail("accepted provenance contract differs from its proposal")
    if _sha(CONTRACT) != CONTRACT_SHA256:
        _fail("accepted provenance contract hash differs")
    if _sha(MANIFEST_SCHEMA) != MANIFEST_SCHEMA_SHA256:
        _fail("provenance manifest schema hash differs")
    if _sha(RESULT_SCHEMA) != RESULT_SCHEMA_SHA256:
        _fail("provenance result schema hash differs")
    contract = _load(CONTRACT)
    if contract.get("contract_id") != CONTRACT_ID:
        _fail("provenance contract ID differs")
    if contract.get("target") != "mathhead.kernel.provenance:replay_provenance_bundle":
        _fail("provenance target differs")
    if contract.get("signature") != (
        "replay_provenance_bundle(manifest: bytes, objects: tuple[bytes, ...]) "
        "-> ProvenanceReplayResult"
    ):
        _fail("provenance signature differs")
    for schema in (_load(MANIFEST_SCHEMA), _load(RESULT_SCHEMA)):
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            _fail("provenance schema is not Draft 2020-12")
        if schema.get("additionalProperties") is not False:
            _fail("provenance schema root is open")


def _verify_source() -> tuple[int, int]:
    files, roots = _closure(SOURCE)
    if len(files) > 12:
        _fail(f"provenance closure exceeds twelve internal modules: {len(files)}")
    if len(roots) > 9 or not roots <= ALLOWED_ROOTS or roots & DENIED_ROOTS:
        _fail(f"provenance import closure is not dependency-minimal: {sorted(roots)}")
    text = SOURCE.read_text(encoding="utf-8")
    if text.count(f'PROVENANCE_REPLAY_CONTRACT_ID = "{CONTRACT_ID}"') != 1:
        _fail("provenance source does not carry exactly one contract ID binding")
    binding = 'PROVENANCE_REPLAY_CONTRACT_SHA256 = (\n    "' + CONTRACT_SHA256 + '"\n)'
    if text.count(binding) != 1:
        _fail("provenance source does not carry exactly one contract SHA-256 binding")
    required = {
        "replay_provenance_bundle",
        "canonical_provenance_manifest_bytes",
        "checker_configuration_bytes",
        "validate_provenance_replay_result",
        "provenance_replay_result_to_bytes",
        "parse_provenance_replay_result",
    }
    tree = ast.parse(text)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not required <= functions:
        _fail(f"provenance functions are missing: {sorted(required - functions)}")
    imported = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    if "mathhead.provenance_store" in imported:
        _fail("pure provenance kernel imports its filesystem adapter")
    store_imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(ast.parse(STORE.read_text(encoding="utf-8")))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    if not {"os", "tempfile"} <= store_imports:
        _fail("filesystem effects are not isolated in provenance_store")
    legacy = LEGACY.read_text(encoding="utf-8")
    if "def proof_sha256(" not in legacy or "legacy 16-hex compatibility identifier" not in legacy:
        _fail("legacy provenance does not distinguish its shortened hash")
    return len(files), len(roots)


def _verify_trust() -> None:
    inventory = _load(TRUST)
    entries = inventory.get("entry_points")
    if type(entries) is not list:
        _fail("trust inventory entry_points is malformed")
    target = "mathhead.kernel.provenance:replay_provenance_bundle"
    matches = [item for item in entries if type(item) is dict and item.get("target") == target]
    if len(matches) != 1 or matches[0].get("kind") != "public_checker":
        _fail("trust inventory lacks the unique provenance replay public checker")
    kernel = inventory.get("kernel_target")
    if type(kernel) is not dict or kernel.get("task_id") != "MH-032":
        _fail("trust inventory no longer carries the accepted kernel target")


def _verify_runtime() -> tuple[int, int]:
    sys.path.insert(0, str(SOURCE_ROOT))
    sys.path.insert(0, str(ROOT / "tests/provenance_replay"))
    from mathhead.kernel.provenance import (
        PROVENANCE_REPLAY_CONTRACT_ID,
        PROVENANCE_REPLAY_CONTRACT_SHA256,
        ProvenanceReplayResult,
        parse_provenance_replay_result,
        provenance_replay_result_to_bytes,
        replay_provenance_bundle,
    )
    from test_provenance_replay import _bundle

    if (
        PROVENANCE_REPLAY_CONTRACT_ID != CONTRACT_ID
        or PROVENANCE_REPLAY_CONTRACT_SHA256 != CONTRACT_SHA256
    ):
        _fail("runtime provenance contract binding differs")
    signature = inspect.signature(replay_provenance_bundle)
    if list(signature.parameters) != ["manifest", "objects"]:
        _fail("runtime provenance parameters differ")
    if str(signature) != (
        "(manifest: 'bytes', objects: 'tuple[bytes, ...]') -> 'ProvenanceReplayResult'"
    ):
        _fail(f"runtime provenance signature differs: {signature}")
    for checker_id in ("mathhead.kernel.checker.v2", "mathhead.kernel.sat-replay.v1"):
        manifest, objects = _bundle(checker_id)
        result = replay_provenance_bundle(manifest, objects)
        if type(result) is not ProvenanceReplayResult or result.verdict != "verified":
            _fail(f"{checker_id} provenance replay did not verify")
        encoded = provenance_replay_result_to_bytes(result)
        if parse_provenance_replay_result(encoded, manifest, objects) != result:
            _fail(f"{checker_id} provenance round trip differs")
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            Draft202012Validator = None  # type: ignore[assignment,misc]
        if Draft202012Validator is not None:
            Draft202012Validator(_load(MANIFEST_SCHEMA)).validate(json.loads(manifest))
            Draft202012Validator(_load(RESULT_SCHEMA)).validate(json.loads(encoded))
    return len(manifest), len(encoded)


def main() -> int:
    try:
        _verify_artifacts()
        modules, roots = _verify_source()
        _verify_trust()
        manifest_bytes, result_bytes = _verify_runtime()
    except (ProvenanceContractError, OSError, UnicodeError, SyntaxError) as exc:
        print(f"provenance-replay: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "provenance-replay: PASS "
        f"(contract={CONTRACT_SHA256[:12]}, manifest={MANIFEST_SCHEMA_SHA256[:12]}, "
        f"result={RESULT_SCHEMA_SHA256[:12]}, modules={modules}, roots={roots}, "
        f"sample_manifest_bytes={manifest_bytes}, sample_result_bytes={result_bytes})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
