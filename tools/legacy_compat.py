#!/usr/bin/env python3
"""Capture and replay the MH-017 legacy compatibility corpus."""

from __future__ import annotations

import argparse
from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "docs/reconstruction/legacy-compat-v1.json"
CONTRACT_ID = "MH-C-LEGACY-COMPAT-001"
CONTRACT_SHA256 = "53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412"
SOURCE_COMMIT = "8bb02b5634d4aedf469cb82a83b9d14c185eb158"
BASELINE_CONTRACT_SHA256 = "3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2"
BASELINE_ARTIFACT_SHA256 = "b93f71ce676380574235ca422e8a23a8f4871ee45b2973195575ea397cefe19a"
ADR_SHA256 = "da4295023849d330bb627ab75717dec5f1e5e68448ad536d2be61c567906d0e3"
CASE_SECONDS = 10
SUPPORTED_PYTHONS = {(3, minor) for minor in range(10, 15)}
SUPPORTED_PLATFORMS = {"linux", "windows", "darwin"}
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

# These inputs are deliberately duplicated in the committed corpus. Replay first
# checks that the data artifact still matches this executable case definition.
CASE_SPECS: tuple[dict[str, Any], ...] = (
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
            "payload": {
                "premises": ["p", "implies(p, q)"],
                "conclusion": "q",
            },
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
        "invocation": {
            "surface": "discovery",
            "statement": "1000001 | n",
            "max_n": 6,
        },
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


class LegacyCompatError(RuntimeError):
    """A classified capture or replay failure."""

    def __init__(self, kind: str, detail: str, exit_code: int = 2) -> None:
        super().__init__(detail)
        self.kind = kind
        self.exit_code = exit_code


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
        raise LegacyCompatError("invalid", f"non-canonical JSON value: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_path(path: Path) -> str:
    try:
        return _sha_bytes(path.read_bytes())
    except OSError as exc:
        raise LegacyCompatError("invalid", f"unreadable file: {path.relative_to(ROOT)}") from exc


def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LegacyCompatError("invalid", f"git invocation failed: {' '.join(args)}") from exc
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", "backslashreplace").strip()
        raise LegacyCompatError("invalid", f"git {' '.join(args)} failed: {detail}")
    return result


def _source_tree_sha256(revision: str) -> str:
    listing = _git("ls-tree", "-r", "-z", revision, "--", "src/mathhead").stdout
    if not listing:
        raise LegacyCompatError("invalid", f"source tree absent at {revision}")
    return _sha_bytes(listing)


def _assert_capture_source() -> None:
    resolved = _git("rev-parse", f"{SOURCE_COMMIT}^{{commit}}").stdout.decode().strip()
    if resolved != SOURCE_COMMIT:
        raise LegacyCompatError("invalid", "capture source commit identity drift")
    if _git("diff", "--quiet", SOURCE_COMMIT, "--", "src/mathhead", check=False).returncode != 0:
        raise LegacyCompatError("invalid", "MathHead source differs from the MH-016 source commit")
    status = _git(
        "status", "--porcelain", "--untracked-files=all", "--", "src/mathhead"
    ).stdout
    if status:
        raise LegacyCompatError("invalid", "MathHead source tree is dirty during capture")


def _host_supported() -> None:
    python_key = (sys.version_info.major, sys.version_info.minor)
    platform_key = "windows" if sys.platform == "win32" else platform.system().lower()
    if python_key not in SUPPORTED_PYTHONS or platform_key not in SUPPORTED_PLATFORMS:
        raise LegacyCompatError(
            "unsupported-host",
            f"unsupported host: Python {python_key[0]}.{python_key[1]} on {platform_key}",
            6,
        )


def _invoke(spec: dict[str, Any]) -> dict[str, Any]:
    invocation = spec["invocation"]
    if invocation["surface"] == "router":
        from mathhead.router import route

        result = route(invocation["task"], invocation["payload"])
    elif invocation["surface"] == "discovery":
        from mathhead.discovery.product import check

        result = check(invocation["statement"], invocation["max_n"])
    else:
        raise LegacyCompatError("invalid", f"unsupported surface: {invocation['surface']}")
    if is_dataclass(result) and not isinstance(result, type):
        payload = asdict(result)
    elif isinstance(result, dict):
        payload = result
    else:
        raise LegacyCompatError("invocation", f"case returned {type(result).__name__}", 3)
    _canonical_bytes(payload)
    return payload


def _child_main() -> int:
    try:
        spec = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        result = _invoke(spec)
        sys.stdout.buffer.write(_canonical_bytes(result))
        return 0
    except LegacyCompatError as exc:
        print(f"legacy-compat-child: {exc.kind}: {exc}", file=sys.stderr)
        return exc.exit_code
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"legacy-compat-child: invocation: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3


def _run_case(spec: dict[str, Any]) -> dict[str, Any]:
    command = [sys.executable, str(Path(__file__).resolve()), "--_run-case"]
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise LegacyCompatError("invocation", f"could not start case {spec['id']}", 3) from exc
    try:
        stdout, stderr = process.communicate(input=_canonical_bytes(spec), timeout=CASE_SECONDS)
    except subprocess.TimeoutExpired as exc:
        process.terminate()
        try:
            process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
        raise LegacyCompatError("watchdog-timeout", f"case {spec['id']} exceeded watchdog", 4) from exc
    if process.returncode != 0:
        detail = stderr.decode("utf-8", "backslashreplace").strip()
        raise LegacyCompatError("invocation", f"case {spec['id']} failed: {detail}", 3)
    try:
        result = json.loads(stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LegacyCompatError("invocation", f"case {spec['id']} emitted invalid JSON", 3) from exc
    if not isinstance(result, dict):
        raise LegacyCompatError("invocation", f"case {spec['id']} emitted a non-object", 3)
    return result


def _path_value(result: dict[str, Any], path: str) -> Any:
    value: Any = result
    for component in path.split("."):
        if not isinstance(value, dict) or component not in value:
            raise LegacyCompatError("invalid", f"normalization path missing: {path}")
        value = value[component]
    return value


def _normalized_paths(result: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for path in sorted(NORMALIZATION_SENTINELS):
        value: Any = result
        present = True
        for component in path.split("."):
            if not isinstance(value, dict) or component not in value:
                present = False
                break
            value = value[component]
        if present:
            paths.append(path)
    return paths


def _normalize(result: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    if paths != sorted(set(paths)) or any(path not in NORMALIZATION_SENTINELS for path in paths):
        raise LegacyCompatError("invalid", "normalization paths are not the exact sorted allowlist subset")
    normalized = json.loads(_canonical_bytes(result))
    for path in paths:
        value = _path_value(normalized, path)
        expected_type = NORMALIZATION_TYPES[path]
        if expected_type == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
            valid = valid and math.isfinite(float(value)) and float(value) >= 0
        else:
            valid = isinstance(value, str) and bool(value)
        if not valid:
            raise LegacyCompatError("drifted", f"normalization type drift: {path}", 5)
        target: Any = normalized
        components = path.split(".")
        for component in components[:-1]:
            target = target[component]
        target[components[-1]] = NORMALIZATION_SENTINELS[path]
    return normalized


def _assert_normalized_expected(result: dict[str, Any], paths: list[str]) -> None:
    if paths != sorted(set(paths)) or any(path not in NORMALIZATION_SENTINELS for path in paths):
        raise LegacyCompatError("invalid", "normalization paths are not the exact sorted allowlist subset")
    for path in paths:
        if _path_value(result, path) != NORMALIZATION_SENTINELS[path]:
            raise LegacyCompatError("invalid", f"normalized sentinel drift: {path}")
    for path, sentinel in NORMALIZATION_SENTINELS.items():
        if path in paths:
            continue
        try:
            value = _path_value(result, path)
        except LegacyCompatError:
            continue
        if value == sentinel:
            raise LegacyCompatError("invalid", f"undeclared normalized sentinel: {path}")


def _assert_outcome(category: str, result: dict[str, Any], case_id: str) -> None:
    status = result.get("status")
    verdict = result.get("verdict")
    reason = result.get("reason_code")
    valid = {
        "success": verdict == "proved" or status in {"ok", "valid", "sat", "unsat", "verified"},
        "refuted": verdict == "refuted" or status in {"invalid", "refuted", "not_equivalent"},
        "unsupported": verdict == "unsupported" or status == "unsupported",
        "timeout": status in {"unknown", "timed_out"} and reason == "SOLVER_TIMEOUT",
        "error": verdict == "error" or status == "error",
    }.get(category, False)
    if not valid:
        raise LegacyCompatError(
            "drifted",
            f"case {case_id} no longer has {category} semantics",
            5,
        )


def _provenance() -> dict[str, Any]:
    return {
        "source_commit": SOURCE_COMMIT,
        "source_tree": {
            "algorithm": "sha256(git-ls-tree-r-z:src/mathhead)",
            "sha256": _source_tree_sha256(SOURCE_COMMIT),
        },
        "baseline": {
            "contract_id": "MH-C-BASELINE-001",
            "contract_sha256": BASELINE_CONTRACT_SHA256,
            "path": "docs/reconstruction/legacy-baseline-v1.json",
            "sha256": BASELINE_ARTIFACT_SHA256,
        },
        "compatibility_adr": {
            "path": "docs/reconstruction/adrs/0004-compatibility-and-deprecation.md",
            "sha256": ADR_SHA256,
        },
    }


def _validate_contract_binding() -> None:
    accepted = ROOT / f"docs/contracts/{CONTRACT_ID}.json"
    proposed = ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json"
    if _sha_path(accepted) != CONTRACT_SHA256 or _sha_path(proposed) != CONTRACT_SHA256:
        raise LegacyCompatError("invalid", "legacy compatibility contract hash drift")
    if accepted.read_bytes() != proposed.read_bytes():
        raise LegacyCompatError("invalid", "accepted contract differs from proposal")


def _build_corpus() -> dict[str, Any]:
    _host_supported()
    _validate_contract_binding()
    _assert_capture_source()
    records: list[dict[str, Any]] = []
    for spec in CASE_SPECS:
        result = _run_case(spec)
        _assert_outcome(spec["category"], result, spec["id"])
        paths = _normalized_paths(result)
        expected = _normalize(result, paths)
        records.append(
            {
                **spec,
                "normalized_paths": paths,
                "expected": expected,
                "expected_sha256": _sha_bytes(_canonical_bytes(expected)),
            }
        )
    return {
        "schema": "mathhead.legacy-compat.v1",
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "provenance": _provenance(),
        "normalization": {
            "allowlist": sorted(NORMALIZATION_SENTINELS),
            "sentinels": NORMALIZATION_SENTINELS,
            "types": NORMALIZATION_TYPES,
        },
        "cases": records,
    }


def _load_corpus(path: Path = CORPUS_PATH) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise LegacyCompatError("invalid", f"corpus unreadable: {exc}") from exc
    if not isinstance(data, dict) or raw != _canonical_bytes(data):
        raise LegacyCompatError("invalid", "corpus is not canonical JSON")
    return data, raw


def validate_corpus_structure(data: dict[str, Any]) -> None:
    if set(data) != {"schema", "contract", "provenance", "normalization", "cases"}:
        raise LegacyCompatError("invalid", "corpus top-level fields drift")
    if data["schema"] != "mathhead.legacy-compat.v1":
        raise LegacyCompatError("invalid", "corpus schema drift")
    if data["contract"] != {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256}:
        raise LegacyCompatError("invalid", "corpus contract binding drift")
    if data["provenance"] != _provenance():
        raise LegacyCompatError("invalid", "corpus provenance drift")
    expected_normalization = {
        "allowlist": sorted(NORMALIZATION_SENTINELS),
        "sentinels": NORMALIZATION_SENTINELS,
        "types": NORMALIZATION_TYPES,
    }
    if data["normalization"] != expected_normalization:
        raise LegacyCompatError("invalid", "normalization policy drift")
    cases = data["cases"]
    if not isinstance(cases, list) or len(cases) < 10:
        raise LegacyCompatError("invalid", "compatibility case minimum not met")
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or ids != sorted(set(ids)):
        raise LegacyCompatError("invalid", "case IDs are invalid, duplicate, or unsorted")
    if {case.get("category") for case in cases} != {
        "success", "refuted", "unsupported", "timeout", "error"
    }:
        raise LegacyCompatError("invalid", "required outcome category coverage drift")
    if {case.get("invocation", {}).get("surface") for case in cases} != {"router", "discovery"}:
        raise LegacyCompatError("invalid", "required invocation surface coverage drift")
    if len(cases) != len(CASE_SPECS):
        raise LegacyCompatError("invalid", "executable case definition count drift")
    for case, spec in zip(cases, CASE_SPECS, strict=True):
        if not isinstance(case, dict) or set(case) != {
            "id", "category", "invocation", "normalized_paths", "expected", "expected_sha256"
        }:
            raise LegacyCompatError("invalid", "case record fields drift")
        if {key: case[key] for key in ("id", "category", "invocation")} != spec:
            raise LegacyCompatError("invalid", f"case input drift: {spec['id']}")
        expected = case["expected"]
        if not isinstance(expected, dict):
            raise LegacyCompatError("invalid", f"case expected output invalid: {spec['id']}")
        if case["expected_sha256"] != _sha_bytes(_canonical_bytes(expected)):
            raise LegacyCompatError("invalid", f"case output identity drift: {spec['id']}")
        _assert_normalized_expected(expected, case["normalized_paths"])
        _assert_outcome(spec["category"], expected, spec["id"])


def _capture() -> None:
    corpus = _build_corpus()
    payload = _canonical_bytes(corpus)
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=".legacy-compat-", dir=CORPUS_PATH.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, CORPUS_PATH)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise
    print(f"legacy-compat capture: PASS ({len(corpus['cases'])} cases)")


def _check() -> None:
    _host_supported()
    _validate_contract_binding()
    corpus, _raw = _load_corpus()
    validate_corpus_structure(corpus)
    for case in corpus["cases"]:
        actual = _run_case(
            {key: case[key] for key in ("id", "category", "invocation")}
        )
        _assert_outcome(case["category"], actual, case["id"])
        normalized = _normalize(actual, case["normalized_paths"])
        actual_sha = _sha_bytes(_canonical_bytes(normalized))
        if actual_sha != case["expected_sha256"] or normalized != case["expected"]:
            raise LegacyCompatError("drifted", f"semantic drift: {case['id']}", 5)
    print(f"legacy-compat replay: PASS ({len(corpus['cases'])} cases)")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--capture", action="store_true", help="replace the governed corpus")
    mode.add_argument("--check", action="store_true", help="replay the governed corpus")
    mode.add_argument("--_run-case", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--debug", action="store_true", help="show programmer tracebacks")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args._run_case:
        return _child_main()
    try:
        if args.capture:
            _capture()
        else:
            _check()
        return 0
    except LegacyCompatError as exc:
        print(f"legacy-compat: {exc.kind}: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        if args.debug:
            raise
        print(f"legacy-compat: internal: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
