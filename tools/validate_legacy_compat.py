#!/usr/bin/env python3
"""Dependency-free, fail-closed validator for MH-C-LEGACY-COMPAT-001."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = ROOT / "docs/reconstruction/legacy-compat-v1.json"
CONTRACT_ID = "MH-C-LEGACY-COMPAT-001"
CONTRACT_SHA256 = "53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412"
SOURCE_COMMIT = "8bb02b5634d4aedf469cb82a83b9d14c185eb158"
BASELINE_SHA256 = "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
ADR_SHA256 = "da4295023849d330bb627ab75717dec5f1e5e68448ad536d2be61c567906d0e3"
NORMALIZATION_SENTINELS = {
    "meta.elapsed_ms": "<normalized:number>",
    "meta.sympy_version": "<normalized:string>",
    "meta.z3_version": "<normalized:string>",
}
NORMALIZATION_TYPES = {
    "meta.elapsed_ms": "number",
    "meta.sympy_version": "string",
    "meta.z3_version": "string",
}
EXPECTED_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "error-malicious-simplify",
        "category": "error",
        "invocation": {
            "surface": "router",
            "task": "simplify",
            "payload": {"expression": "__import__('os').system('echo nope')"},
        },
    },
    {
        "id": "error-singular-matrix",
        "category": "error",
        "invocation": {
            "surface": "router",
            "task": "matrix_inverse",
            "payload": {"matrix": [["1", "2"], ["2", "4"]]},
        },
    },
    {
        "id": "refuted-discovery-composition",
        "category": "refuted",
        "invocation": {
            "surface": "discovery",
            "statement": "compositions(n) == 2**n",
            "max_n": 6,
        },
    },
    {
        "id": "refuted-verify-equality",
        "category": "refuted",
        "invocation": {
            "surface": "router",
            "task": "verify_equality",
            "payload": {"left": "x + 1", "right": "x + 2"},
        },
    },
    {
        "id": "success-discovery-divisibility",
        "category": "success",
        "invocation": {
            "surface": "discovery",
            "statement": "24 | n*(n+1)*(n+2)*(n+3)",
            "max_n": 6,
        },
    },
    {
        "id": "success-entailment",
        "category": "success",
        "invocation": {
            "surface": "router",
            "task": "entailment",
            "payload": {"premises": ["p", "implies(p, q)"], "conclusion": "q"},
        },
    },
    {
        "id": "success-symbolic-simplify",
        "category": "success",
        "invocation": {
            "surface": "router",
            "task": "simplify",
            "payload": {"expression": "(x + 1)**2 - (x**2 + 2*x + 1)"},
        },
    },
    {
        "id": "timeout-pythagorean-colouring",
        "category": "timeout",
        "invocation": {
            "surface": "router",
            "task": "pythagorean_coloring",
            "payload": {"n": 3000, "seed": 42, "timeout_ms": 1},
        },
    },
    {
        "id": "unsupported-discovery-bound",
        "category": "unsupported",
        "invocation": {"surface": "discovery", "statement": "1000001 | n", "max_n": 6},
    },
    {
        "id": "unsupported-discovery-language",
        "category": "unsupported",
        "invocation": {
            "surface": "discovery",
            "statement": "the weather tomorrow",
            "max_n": 6,
        },
    },
)
EXPECTED_OUTPUT_SHA256 = {
    "error-malicious-simplify": "49a290e881b1786e726eca9e28ca447f5b6ea12d7f40d9650dfc83cedfe19e12",
    "error-singular-matrix": "cc58cad7a26170c653db52291a92142454fb5ba8e1092c192c9a64aa0ff8ec4d",
    "refuted-discovery-composition": "c4aeb46c7c7cdb8b717669efcbfc0b866e6ee7ff97c8cbbfe061de175192c648",
    "refuted-verify-equality": "f844b46032dc2c610ebf88c21af986c366a5ea3d4069cfb45328bf7cd244c528",
    "success-discovery-divisibility": "f2fef98706593c1a7f02d97c958a6b9f38620f1f18aefa3933a6552824e1c3e2",
    "success-entailment": "f89b08ee08f6825b4997287456cfb0bafee02fc47a97d6c942242eedd784e09f",
    "success-symbolic-simplify": "9d53ac01e2812892540c0a6a7e2bdcc052db42897fbca23c3b3a718fe8e7cb44",
    "timeout-pythagorean-colouring": "234fb51aca52c9ee03d631222f4389031ade6af8313f6d5dca476cdfbdac29a6",
    "unsupported-discovery-bound": "406cb31df5d10e559bffb04217c9fe85067903d60aa5dac6f3cccea6840a2c5c",
    "unsupported-discovery-language": "4210fa3c4243313e3a6a6239d80ca65c5dcd45d1fbb2f066a0dbbe6171035ede",
}


class CompatibilityValidationError(RuntimeError):
    """Raised when the accepted contract or corpus drifts."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CompatibilityValidationError(f"non-canonical JSON value: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise CompatibilityValidationError(f"unreadable file: {path}") from exc


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise CompatibilityValidationError(f"invalid TOML: {path}") from exc


def _source_tree_sha256() -> str:
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "-z", SOURCE_COMMIT, "--", "src/mathhead"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CompatibilityValidationError("source provenance Git lookup failed") from exc
    if result.returncode != 0 or not result.stdout:
        raise CompatibilityValidationError("source provenance commit unavailable")
    return _sha(result.stdout)


def _path_value(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            raise CompatibilityValidationError(f"normalization path missing: {path}")
        current = current[component]
    return current


def _outcome_matches(category: str, result: dict[str, Any]) -> bool:
    status = result.get("status")
    verdict = result.get("verdict")
    reason = result.get("reason_code")
    return {
        "success": verdict == "proved" or status in {"ok", "valid", "sat", "unsat", "verified"},
        "refuted": verdict == "refuted" or status in {"invalid", "refuted", "not_equivalent"},
        "unsupported": verdict == "unsupported" or status == "unsupported",
        "timeout": status in {"unknown", "timed_out"} and reason == "SOLVER_TIMEOUT",
        "error": verdict == "error" or status == "error",
    }.get(category, False)


def _validate_contract() -> None:
    accepted = _read(ROOT / f"docs/contracts/{CONTRACT_ID}.json")
    proposed = _read(ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json")
    if _sha(accepted) != CONTRACT_SHA256 or _sha(proposed) != CONTRACT_SHA256:
        raise CompatibilityValidationError("contract hash drift")
    if accepted != proposed:
        raise CompatibilityValidationError("accepted contract differs from proposal")
    manifest = _load_toml(ROOT / "docs/contracts/manifest.toml")
    records = [item for item in manifest.get("contracts", []) if item.get("id") == CONTRACT_ID]
    expected = {
        "id": CONTRACT_ID,
        "path": f"docs/contracts/{CONTRACT_ID}.json",
        "sha256": CONTRACT_SHA256,
        "state": "accepted",
    }
    if records != [expected]:
        raise CompatibilityValidationError("accepted manifest binding drift")


def _validate_tool_binding() -> None:
    path = ROOT / "tools/legacy_compat.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise CompatibilityValidationError("legacy compatibility tool is invalid") from exc
    constants: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    if constants.get("CONTRACT_ID") != CONTRACT_ID or constants.get("CONTRACT_SHA256") != CONTRACT_SHA256:
        raise CompatibilityValidationError("tool contract binding drift")
    if constants.get("SOURCE_COMMIT") != SOURCE_COMMIT:
        raise CompatibilityValidationError("tool source commit binding drift")
    mains = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"]
    if len(mains) != 1 or [arg.arg for arg in mains[0].args.args] != ["argv"]:
        raise CompatibilityValidationError("tool main signature drift")


def _validate_configuration() -> None:
    status = _load_toml(ROOT / ".project-status.toml")
    checks = [item for item in status.get("checks", []) if item.get("name") == "legacy-compat-contract"]
    if checks != [{
        "name": "legacy-compat-contract",
        "command": "python tools/validate_legacy_compat.py",
        "profiles": ["status", "fast"],
        "tasks": ["MH-017"],
        "timeout_seconds": 60,
    }]:
        raise CompatibilityValidationError("project-status ownership drift")
    profiles = json.loads((ROOT / "tools/dev_profiles.json").read_text(encoding="utf-8"))
    core = profiles.get("profiles", {}).get("core", {})
    commands = [item for item in core.get("commands", []) if item.get("id") == "legacy-compat-replay"]
    if commands != [{
        "id": "legacy-compat-replay",
        "required": True,
        "timeout_seconds": 90,
        "argv": ["{python}", "tools/legacy_compat.py", "--check"],
    }]:
        raise CompatibilityValidationError("core replay ownership drift")


def validate_corpus(path: Path = DEFAULT_CORPUS) -> None:
    raw = _read(path)
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityValidationError("corpus is invalid JSON") from exc
    if not isinstance(data, dict) or raw != _canonical_bytes(data):
        raise CompatibilityValidationError("corpus is not canonical JSON")
    if set(data) != {"schema", "contract", "provenance", "normalization", "cases"}:
        raise CompatibilityValidationError("corpus top-level fields drift")
    if data["schema"] != "mathhead.legacy-compat.v1":
        raise CompatibilityValidationError("corpus schema drift")
    if data["contract"] != {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256}:
        raise CompatibilityValidationError("corpus contract binding drift")
    provenance = data["provenance"]
    expected_provenance = {
        "source_commit": SOURCE_COMMIT,
        "source_tree": {
            "algorithm": "sha256(git-ls-tree-r-z:src/mathhead)",
            "sha256": _source_tree_sha256(),
        },
        "baseline": {
            "contract_id": "MH-C-BASELINE-001",
            "contract_sha256": "3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2",
            "path": "docs/reconstruction/legacy-baseline-v1.json",
            "sha256": BASELINE_SHA256,
        },
        "compatibility_adr": {
            "path": "docs/reconstruction/adrs/0004-compatibility-and-deprecation.md",
            "sha256": ADR_SHA256,
        },
    }
    if provenance != expected_provenance:
        raise CompatibilityValidationError("corpus provenance drift")
    if _sha(_read(ROOT / provenance["baseline"]["path"])) != BASELINE_SHA256:
        raise CompatibilityValidationError("legacy baseline artifact drift")
    if _sha(_read(ROOT / provenance["compatibility_adr"]["path"])) != ADR_SHA256:
        raise CompatibilityValidationError("compatibility ADR drift")
    expected_normalization = {
        "allowlist": sorted(NORMALIZATION_SENTINELS),
        "sentinels": NORMALIZATION_SENTINELS,
        "types": NORMALIZATION_TYPES,
    }
    if data["normalization"] != expected_normalization:
        raise CompatibilityValidationError("normalization policy drift")
    cases = data["cases"]
    if not isinstance(cases, list) or len(cases) < 10 or len(cases) != len(EXPECTED_CASES):
        raise CompatibilityValidationError("case count drift")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or ids != sorted(set(ids)):
        raise CompatibilityValidationError("case IDs are invalid, duplicate, or unsorted")
    if {case.get("category") for case in cases} != {
        "success", "refuted", "unsupported", "timeout", "error"
    }:
        raise CompatibilityValidationError("outcome category coverage drift")
    if {case.get("invocation", {}).get("surface") for case in cases} != {"router", "discovery"}:
        raise CompatibilityValidationError("invocation surface coverage drift")
    for case, spec in zip(cases, EXPECTED_CASES, strict=True):
        if set(case) != {
            "id", "category", "invocation", "normalized_paths", "expected", "expected_sha256"
        }:
            raise CompatibilityValidationError(f"case fields drift: {spec['id']}")
        if {key: case[key] for key in ("id", "category", "invocation")} != spec:
            raise CompatibilityValidationError(f"case input drift: {spec['id']}")
        paths = case["normalized_paths"]
        if not isinstance(paths, list) or paths != sorted(set(paths)):
            raise CompatibilityValidationError(f"normalization paths invalid: {spec['id']}")
        if any(path not in NORMALIZATION_SENTINELS for path in paths):
            raise CompatibilityValidationError(f"normalization path not allowlisted: {spec['id']}")
        expected = case["expected"]
        if not isinstance(expected, dict) or not _outcome_matches(spec["category"], expected):
            raise CompatibilityValidationError(f"outcome semantics drift: {spec['id']}")
        for normalized_path in paths:
            if _path_value(expected, normalized_path) != NORMALIZATION_SENTINELS[normalized_path]:
                raise CompatibilityValidationError(f"normalization sentinel drift: {spec['id']}")
        if case["expected_sha256"] != _sha(_canonical_bytes(expected)):
            raise CompatibilityValidationError(f"output identity drift: {spec['id']}")
        if case["expected_sha256"] != EXPECTED_OUTPUT_SHA256[spec["id"]]:
            raise CompatibilityValidationError(f"accepted output identity drift: {spec['id']}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _validate_contract()
        _validate_tool_binding()
        _validate_configuration()
        validate_corpus(args.corpus)
    except (CompatibilityValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"legacy-compat-validator: FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"legacy-compat-validator: PASS (cases={len(EXPECTED_CASES)}, source={SOURCE_COMMIT[:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
