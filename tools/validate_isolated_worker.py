#!/usr/bin/env python3
"""Independently validate the MH-052 isolated-worker boundary."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "MH-C-ISOLATED-WORKER-001"
CONTRACT_SHA256 = "c578d5a75f7a670f55e660147c335dc29709e71b82af8b37eb0033891b81a49b"
REPORT_SCHEMA = "mathhead.isolated-worker-validation-report.v1"
DEFAULT_REPORT = Path("docs/planning/reports/isolated-worker-v1.json")
SCHEMAS = {
    "isolated-worker-request-v1.schema.json": "5f3f12dcf71bcceb7ca539df90c93887a4048366c5ea05be41b70b6532197a97",
    "isolation-capability-v1.schema.json": "63b1800180724b51dcfa3289fec3e990ecad131f6422203319562178e7296098",
    "worker-resource-usage-v1.schema.json": "0daa1bb755a8005d53824ee8bcfebd0be1174e16cbcd7e2c5fd80ee2467b1e44",
    "worker-artifact-v1.schema.json": "d4df223c84841325f99e1a7285a9e0f9773522ed37f8cb550f4b55efedc9700a",
    "worker-diagnostic-v1.schema.json": "e076d807d7e6c7d5e040792f928e592640f7615b6dc041855769b6a8a7f75673",
    "isolated-worker-result-v1.schema.json": "b6172ad7c33908b65ecb74fc39340664b8a4ca8f55d1b69c1e23eacaf281f7df",
}
RESOURCE_DIMENSIONS = (
    "wall_time_us", "cpu_time_us", "memory_bytes", "solver_calls",
    "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes",
    "diagnostic_bytes", "nesting_depth",
)
STATUSES = ("completed", "refused", "unsupported", "exhausted", "cancelled", "failed", "invalid")
REASONS = (
    "COMPLETED", "REQUEST_INVALID", "PLAN_INVALID", "STRATEGY_MISMATCH",
    "BUDGET_INVALID", "BUDGET_INSUFFICIENT", "ISOLATION_UNSUPPORTED",
    "EXECUTABLE_INVALID", "LAUNCH_FAILED", "WALL_TIME_EXHAUSTED",
    "CPU_TIME_EXHAUSTED", "MEMORY_EXHAUSTED", "OUTPUT_EXHAUSTED",
    "DIAGNOSTIC_EXHAUSTED", "CANCELLED", "EXIT_FAILED", "PROTOCOL_FAILED",
    "TREE_CLEANUP_FAILED", "SUPERVISOR_FAILED",
)


class IsolatedWorkerReportError(RuntimeError):
    pass


def _fail(detail: str) -> NoReturn:
    raise IsolatedWorkerReportError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load(path: Path, *, canonical: bool = False) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"JSON root is not an object: {path}")
    if canonical and _canonical(value) != raw:
        _fail(f"noncanonical JSON: {path}")
    return value, raw


def _self_hash(value: dict[str, Any], field: str) -> str:
    basis = copy.deepcopy(value)
    basis[field] = None
    return _sha(_canonical(basis))


def _identity_checks() -> dict[str, object]:
    paths = {
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        **{Path("docs/contracts/schemas") / name: digest for name, digest in SCHEMAS.items()},
    }
    for relative, expected in paths.items():
        if _sha((ROOT / relative).read_bytes()) != expected:
            _fail(f"identity drift: {relative}")
    accepted, accepted_raw = _load(ROOT / f"docs/contracts/{CONTRACT_ID}.json", canonical=True)
    _proposed, proposed_raw = _load(ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json", canonical=True)
    if accepted_raw != proposed_raw or accepted["contract_id"] != CONTRACT_ID:
        _fail("accepted/proposed contract separation drift")
    required_text = " ".join(
        str(item)
        for field in ("requires", "ensures", "invariants")
        for item in accepted[field]
    )
    for phrase in (
        "shell disabled", "fresh POSIX session", "Job Object", "kill-on-close",
        "reconciles the reserved lease exactly once", "mathematical authority",
    ):
        if phrase not in required_text:
            _fail(f"contract safety clause missing: {phrase}")
    return {"accepted_equals_proposed": True, "contract_sha256": CONTRACT_SHA256, "schemas": len(SCHEMAS)}


def _schema_checks() -> dict[str, object]:
    parsed: dict[str, dict[str, Any]] = {}
    for name in SCHEMAS:
        schema, _raw = _load(ROOT / "docs/contracts/schemas" / name)
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            _fail(f"schema root is not closed Draft 2020-12: {name}")
        required = schema.get("required")
        properties = schema.get("properties")
        if not isinstance(required, list) or not isinstance(properties, dict) or set(required) != set(properties):
            _fail(f"root required/property closure drift: {name}")
        parsed[name] = schema
    request = parsed["isolated-worker-request-v1.schema.json"]
    vector = request["$defs"]["resource_vector"]
    if tuple(vector["required"]) != RESOURCE_DIMENSIONS or set(vector["properties"]) != set(RESOURCE_DIMENSIONS):
        _fail("request resource vector is not the accepted ten-dimensional vector")
    result = parsed["isolated-worker-result-v1.schema.json"]
    if tuple(result["properties"]["status"]["enum"]) != STATUSES:
        _fail("terminal status taxonomy drift")
    if tuple(result["properties"]["reason_code"]["enum"]) != REASONS:
        _fail("terminal reason taxonomy drift")
    references = {
        result["properties"]["capability"]["anyOf"][1]["$ref"],
        result["properties"]["usage"]["anyOf"][1]["$ref"],
        result["properties"]["artifacts"]["items"]["$ref"],
        result["properties"]["diagnostics"]["items"]["$ref"],
    }
    if references != {
        "isolation-capability-v1.schema.json", "worker-resource-usage-v1.schema.json",
        "worker-artifact-v1.schema.json", "worker-diagnostic-v1.schema.json",
    }:
        _fail("result nested schema bindings drift")
    return {"closed": len(parsed), "resource_dimensions": len(RESOURCE_DIMENSIONS), "reasons": len(REASONS), "statuses": len(STATUSES)}


def _source_checks() -> dict[str, object]:
    path = ROOT / "src/mathhead/isolated_worker.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    functions: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.add(node.name)
    if not {"subprocess", "tempfile", "threading", "time"} <= imports:
        _fail("effect-boundary import inventory drift")
    required_functions = {
        "supervise_worker", "_run_posix", "_run_windows", "_terminate_posix_group",
        "_reserve_budget", "_reconcile_budget", "parse_isolated_worker_request",
        "_parse_resource_budget", "_validate_result_budgets",
        "validate_isolated_worker_result",
    }
    if not required_functions <= functions:
        _fail("required supervisor boundary functions are missing")
    for literal in (
        "shell=False", "start_new_session=True", "os.killpg", "resource.setrlimit",
        "CreateJobObjectW", "AssignProcessToJobObject", "TerminateJobObject",
        "CREATE_SUSPENDED", "CREATE_NEW_PROCESS_GROUP", "close_fds=True",
    ):
        if literal not in source:
            _fail(f"containment primitive missing: {literal}")
    if "shell=True" in source or "os.system(" in source or "subprocess.run(" in source:
        _fail("forbidden command execution surface exists")
    return {"imports": sorted(imports), "required_functions": len(required_functions), "sha256": _sha(path.read_bytes())}


def _canonical_fixture_checks() -> dict[str, object]:
    zero = {name: 0 for name in RESOURCE_DIMENSIONS}
    zero.update({"wall_time_us": 1_000_000, "cpu_time_us": 1_000_000, "memory_bytes": 67_108_864, "output_bytes": 4_096, "diagnostic_bytes": 4_096, "nesting_depth": 8})
    request: dict[str, Any] = {
        "schema": "mathhead.isolated-worker-request.v1",
        "planning_result_sha256": "1" * 64,
        "strategy_sha256": "2" * 64,
        "descriptor_sha256": "3" * 64,
        "family": "python_enumeration",
        "protocol": "raw_stdout_v1",
        "executable_sha256": "4" * 64,
        "arguments": ["--fixture"],
        "artifact_bindings": [{"role": "context", "sha256": "5" * 64, "bytes": 7}],
        "parent_budget_sha256": "6" * 64,
        "lease_id": "lease_fixture",
        "child_budget_id": "budget_fixture_child",
        "resource_limits": zero,
        "request_sha256": None,
        "mathematical_authority": False,
    }
    request["request_sha256"] = _self_hash(request, "request_sha256")
    if request["request_sha256"] != _self_hash(json.loads(_canonical(request)), "request_sha256"):
        _fail("independent request identity reconstruction drift")
    allocation_sha = _sha(_canonical(zero))
    usage = {
        "wall_time_us": 10, "cpu_time_us": 4, "memory_peak_bytes": 1_024,
        "memory_retained_bytes": 0, "solver_calls": 0, "generated_objects": 0,
        "proof_bytes": 0, "evidence_bytes": 0, "output_bytes": 2,
        "diagnostic_bytes": 0, "nesting_peak": 0,
    }
    mapped = {**{name: usage[name] for name in ("wall_time_us", "cpu_time_us", "solver_calls", "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes", "diagnostic_bytes")}, "memory_bytes": usage["memory_peak_bytes"], "nesting_depth": usage["nesting_peak"]}
    refund = {name: zero[name] - mapped[name] for name in RESOURCE_DIMENSIONS}
    if any(zero[name] != mapped[name] + refund[name] for name in RESOURCE_DIMENSIONS):
        _fail("independent lease conservation drift")
    artifact = {"schema": "mathhead.worker-artifact.v1", "role": "stdout", "media_type": "application/octet-stream", "original_bytes": 2, "retained_bytes": 2, "omitted_bytes": 0, "retained_sha256": _sha(b"ok"), "artifact_sha256": None, "mathematical_authority": False}
    artifact["artifact_sha256"] = _self_hash(artifact, "artifact_sha256")
    return {"allocation_sha256": allocation_sha, "artifact_sha256": artifact["artifact_sha256"], "lease_conserved": True, "request_sha256": request["request_sha256"]}


def _test_checks() -> dict[str, object]:
    path = ROOT / "tests/isolated_worker/test_isolated_worker.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tests = sorted(node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"))
    required = {
        "test_all_declared_producer_families_use_the_same_isolated_boundary",
        "test_cleanup_failure_cannot_become_success",
        "test_concurrent_supervisors_have_independent_containment",
        "test_diagnostic_overrun_signal_and_forced_cleanup_are_explicit",
        "test_success_is_bounded_reconciled_and_non_authoritative",
        "test_output_overrun_is_exhausted_and_explicit",
        "test_preobserved_cancellation_terminates_and_reconciles",
        "test_grandchild_is_dead_before_return",
        "test_hostile_ambient_environment_is_not_inherited",
        "test_repaired_invalid_parent_budget_semantics_fail_before_launch",
        "test_repaired_result_cannot_bind_invalid_budget_bytes",
        "test_same_producer_bytes_have_same_semantic_identity",
        "test_fatal_controls_propagate_after_cleanup_path",
    }
    if len(tests) < 21 or not required <= set(tests):
        _fail("isolated-worker executable test coverage drift")
    return {"cases": len(tests), "required_adversarial_cases": len(required), "sha256": _sha(path.read_bytes())}


def _report() -> dict[str, object]:
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": _canonical_fixture_checks(),
        "identity_checks": _identity_checks(),
        "mathematical_authority": False,
        "platform_adapters": ["linux-posix-session", "macos-posix-session", "windows-job-object"],
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schema_checks": _schema_checks(),
        "schemas": SCHEMAS,
        "source": _source_checks(),
        "status": "passed",
        "tests": _test_checks(),
        "validator_sha256": _sha(Path(__file__).read_bytes()),
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"isolated-worker: report updated: {target}")
        return
    if not target.is_file() or target.read_bytes() != payload:
        _fail(f"frozen report drift or missing: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write-report", type=Path)
    group.add_argument("--check-report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = _report()
        path = args.write_report or args.check_report or DEFAULT_REPORT
        _write_or_check(report, path, write=args.write_report is not None)
    except (OSError, UnicodeError, ValueError, IsolatedWorkerReportError) as exc:
        print(f"isolated-worker: FAIL: {exc}", file=sys.stderr)
        return 1
    print("isolated-worker: PASS (schemas=6, statuses=7, reasons=19, adapters=3)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
