#!/usr/bin/env python3
"""Validate the accepted MH-034 dependency-minimal SAT replay boundary."""

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
SOURCE = PACKAGE_ROOT / "kernel/sat.py"
CONTRACT = ROOT / "docs/contracts/MH-C-SAT-REPLAY-001.json"
PROPOSAL = ROOT / "docs/contracts/proposed/MH-C-SAT-REPLAY-001.json"
SCHEMA = ROOT / "docs/contracts/schemas/sat-replay-result-v1.schema.json"
TRUST = ROOT / "docs/trust/trust-base-v1.json"

CONTRACT_ID = "MH-C-SAT-REPLAY-001"
CONTRACT_SHA256 = "0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50"
SCHEMA_SHA256 = "e7bccaba76958f185a94d7570b5c65972a855dd99888c04269074491506ef242"
ALLOWED_ROOTS = {"__future__", "dataclasses", "hashlib", "json", "typing"}
DENIED_ROOTS = {
    "importlib", "mcp", "mpmath", "multiprocessing", "os", "pathlib", "pysat",
    "random", "shutil", "subprocess", "sympy", "sys", "time", "z3",
}


class SATReplayContractError(ValueError):
    pass


def _fail(detail: str) -> NoReturn:
    raise SATReplayContractError(detail)


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
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError) as exc:
            _fail(f"cannot parse {path.relative_to(ROOT)}: {type(exc).__name__}")
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_from(path, node)
                if resolved:
                    modules.append(resolved)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {
                "__import__", "eval", "exec", "open",
            }:
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
    for path in (SOURCE, CONTRACT, PROPOSAL, SCHEMA, TRUST):
        if not path.is_file():
            _fail(f"required artifact is missing: {path.relative_to(ROOT)}")
    if CONTRACT.read_bytes() != PROPOSAL.read_bytes():
        _fail("accepted SAT replay contract differs from its proposal")
    if _sha(CONTRACT) != CONTRACT_SHA256:
        _fail("accepted SAT replay contract hash differs")
    if _sha(SCHEMA) != SCHEMA_SHA256:
        _fail("SAT replay result schema hash differs")
    contract = _load(CONTRACT)
    if contract.get("contract_id") != CONTRACT_ID:
        _fail("SAT replay contract ID differs")
    if contract.get("target") != "mathhead.kernel.sat:check_sat_certificate":
        _fail("SAT replay target differs")
    if contract.get("signature") != "check_sat_certificate(cnf: bytes, certificate: bytes) -> SATReplayResult":
        _fail("SAT replay signature differs")
    schema = _load(SCHEMA)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        _fail("SAT replay result schema is not Draft 2020-12")
    if schema.get("additionalProperties") is not False:
        _fail("SAT replay result schema root is open")


def _verify_source() -> tuple[int, int]:
    files, roots = _closure(SOURCE)
    if len(files) > 12:
        _fail(f"SAT replay closure exceeds twelve internal modules: {len(files)}")
    if len(roots) > 9 or not roots <= ALLOWED_ROOTS or roots & DENIED_ROOTS:
        _fail(f"SAT replay import closure is not dependency-minimal: {sorted(roots)}")
    text = SOURCE.read_text(encoding="utf-8")
    if text.count(f'SAT_REPLAY_CONTRACT_ID = "{CONTRACT_ID}"') != 1:
        _fail("SAT replay source does not carry exactly one contract ID binding")
    if text.count(f'SAT_REPLAY_CONTRACT_SHA256 = "{CONTRACT_SHA256}"') != 1:
        _fail("SAT replay source does not carry exactly one contract SHA-256 binding")
    required = {
        "check_sat_certificate", "canonical_cnf_bytes", "canonical_drup_bytes",
        "canonical_sat_assignment_bytes", "validate_sat_replay_result",
        "sat_replay_result_to_bytes", "parse_sat_replay_result",
    }
    tree = ast.parse(text)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not required <= functions:
        _fail(f"SAT replay source functions are missing: {sorted(required - functions)}")
    for legacy in (ROOT / "src/mathhead/drat.py", ROOT / "src/mathhead/discovery/rup_check.py"):
        legacy_text = legacy.read_text(encoding="utf-8")
        if "from mathhead.kernel.sat import" not in legacy_text:
            _fail(f"legacy checker is not an adapter: {legacy.relative_to(ROOT)}")
        legacy_tree = ast.parse(legacy_text)
        forbidden = {"_propagate", "_Formula"}
        definitions = {
            node.name for node in legacy_tree.body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef))
        }
        if definitions & forbidden:
            _fail(f"duplicate legacy replay implementation remains in {legacy.relative_to(ROOT)}")
    return len(files), len(roots)


def _verify_trust() -> None:
    inventory = _load(TRUST)
    entries = inventory.get("entry_points")
    if type(entries) is not list:
        _fail("trust inventory entry_points is malformed")
    matches = [item for item in entries if type(item) is dict and item.get("target") ==
               "mathhead.kernel.sat:check_sat_certificate"]
    if len(matches) != 1 or matches[0].get("kind") != "public_checker":
        _fail("trust inventory lacks the unique SAT replay public checker")
    kernel = inventory.get("kernel_target")
    if type(kernel) is not dict or kernel.get("task_id") != "MH-032":
        _fail("trust inventory no longer carries the accepted MH-030 kernel target")


def _verify_runtime() -> int:
    sys.path.insert(0, str(SOURCE_ROOT))
    from mathhead.kernel.sat import (
        SATReplayResult,
        SAT_REPLAY_CONTRACT_ID,
        SAT_REPLAY_CONTRACT_SHA256,
        canonical_cnf_bytes,
        canonical_drup_bytes,
        canonical_sat_assignment_bytes,
        check_sat_certificate,
        parse_sat_replay_result,
        sat_replay_result_to_bytes,
    )

    if SAT_REPLAY_CONTRACT_ID != CONTRACT_ID or SAT_REPLAY_CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("runtime SAT replay contract binding differs")
    signature = inspect.signature(check_sat_certificate)
    if list(signature.parameters) != ["cnf", "certificate"]:
        _fail("runtime SAT replay parameters differ")
    if str(signature) != "(cnf: 'bytes', certificate: 'bytes') -> 'SATReplayResult'":
        _fail(f"runtime SAT replay signature differs: {signature}")
    cnf = canonical_cnf_bytes([[1], [-1]])
    unsat_certificate = canonical_drup_bytes(cnf, [])
    unsat = check_sat_certificate(cnf, unsat_certificate)
    if type(unsat) is not SATReplayResult or not unsat.ok or unsat.reason_code != "UNSAT_VERIFIED":
        _fail("direct UNSAT replay did not verify")
    encoded = sat_replay_result_to_bytes(unsat)
    if parse_sat_replay_result(encoded, cnf, unsat_certificate) != unsat:
        _fail("SAT replay result round trip differs")
    sat_cnf = canonical_cnf_bytes([[1, 2], [-1, 2]])
    sat_result = check_sat_certificate(sat_cnf, canonical_sat_assignment_bytes(sat_cnf, [1, 2]))
    false_result = check_sat_certificate(sat_cnf, canonical_sat_assignment_bytes(sat_cnf, [1, -2]))
    if not sat_result.ok or false_result.authority != "none" or false_result.verdict != "refuted":
        _fail("SAT assignment positive or negative replay differs")
    drat = f"p mathhead-drat 1 {hashlib.sha256(cnf).hexdigest()}\n".encode("ascii")
    refused = check_sat_certificate(cnf, drat)
    if refused.verdict != "unsupported" or refused.authority != "none":
        _fail("DRAT/RAT input was not refused without authority")
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        Draft202012Validator = None  # type: ignore[assignment,misc]
    if Draft202012Validator is not None:
        validator = Draft202012Validator(_load(SCHEMA))
        for result in (unsat, sat_result, false_result, refused):
            validator.validate(json.loads(sat_replay_result_to_bytes(result)))
    return len(encoded)


def main() -> int:
    try:
        _verify_artifacts()
        modules, roots = _verify_source()
        _verify_trust()
        result_bytes = _verify_runtime()
    except (SATReplayContractError, OSError, UnicodeError, SyntaxError) as exc:
        print(f"sat-replay: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "sat-replay: PASS "
        f"(contract={CONTRACT_SHA256[:12]}, schema={SCHEMA_SHA256[:12]}, "
        f"modules={modules}, roots={roots}, sample_result_bytes={result_bytes})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
