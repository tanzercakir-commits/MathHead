#!/usr/bin/env python3
"""Independently validate the MH-040 structured problem-intake boundary."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mathhead import problem_intake as production  # noqa: E402
from tools import validate_problem_ir_contract as independent  # noqa: E402


CONTRACT_ID = "MH-C-PROBLEM-INTAKE-001"
CONTRACT_SHA256 = "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc"
INPUT_SCHEMA = Path("docs/contracts/schemas/problem-intake-v1.schema.json")
INPUT_SCHEMA_SHA256 = "e109d5a664849b8122eed13eeb87d73bc47e2d2989b3298e06a697989fb51c04"
RESULT_SCHEMA = Path("docs/contracts/schemas/problem-intake-result-v1.schema.json")
RESULT_SCHEMA_SHA256 = "0ea174a09391dd7f690bba9df7dfd08d8f1253032c472ca60d45eaf9f47101d3"
PROBLEM_SCHEMA = Path("docs/contracts/schemas/problem-ir-v1.schema.json")
PROBLEM_SCHEMA_SHA256 = "dcf871f15ebbae06b0eca285a115f2545defc00cb0befc23e3cc574d8523df2c"
PROBLEM_CONTRACT_SHA256 = "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286"
SOURCE = Path("src/mathhead/problem_intake.py")
TEST_SOURCE = Path("tests/problem_intake/test_problem_intake.py")
DEFAULT_REPORT = Path("docs/intake/reports/problem-intake-v1.json")
REPORT_SCHEMA = "mathhead.problem-intake-validation-report.v1"
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "dataclasses",
    "hashlib",
    "json",
    "math",
    "re",
    "typing",
    "unicodedata",
}
FORBIDDEN_NAMES = {
    "Path",
    "eval",
    "exec",
    "getenv",
    "import_module",
    "open",
    "perf_counter",
    "run",
    "system",
    "time",
}


class ProblemIntakeReportError(RuntimeError):
    """An independent contract, source, output, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise ProblemIntakeReportError(detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _load(relative: Path) -> tuple[Any, bytes]:
    raw = (ROOT / relative).read_bytes()
    try:
        return json.loads(raw), raw
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON at {relative}: {exc}")


def _identity_checks() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected = {
        INPUT_SCHEMA: INPUT_SCHEMA_SHA256,
        RESULT_SCHEMA: RESULT_SCHEMA_SHA256,
        PROBLEM_SCHEMA: PROBLEM_SCHEMA_SHA256,
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
    }
    for relative, digest in expected.items():
        raw = (ROOT / relative).read_bytes()
        if _sha(raw) != digest:
            _fail(f"identity drift: {relative}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed or accepted != _canonical(json.loads(accepted)):
        _fail("accepted and proposed contract bytes must be identical canonical JSON")
    manifest = (ROOT / "docs/contracts/manifest.toml").read_text(encoding="utf-8")
    expected_record = (
        f'id = "{CONTRACT_ID}"\n'
        f'path = "docs/contracts/{CONTRACT_ID}.json"\n'
        f'sha256 = "{CONTRACT_SHA256}"\n'
        'state = "accepted"'
    )
    if manifest.count(expected_record) != 1:
        _fail("accepted contract manifest binding drift")
    input_schema, _ = _load(INPUT_SCHEMA)
    result_schema, _ = _load(RESULT_SCHEMA)
    problem_schema, _ = _load(PROBLEM_SCHEMA)
    expected_schema_ids = {
        "https://mathhead.dev/schemas/problem-intake-v1.schema.json",
        "https://mathhead.dev/schemas/problem-intake-result-v1.schema.json",
        "https://mathhead.dev/schemas/problem-ir-v1.schema.json",
    }
    if {schema.get("$id") for schema in (input_schema, result_schema, problem_schema)} != expected_schema_ids:
        _fail("schema identifiers drift")
    for schema in (input_schema, result_schema, problem_schema):
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail(f"closed Draft 2020-12 schema root drift: {schema.get('$id')}")
    contract = json.loads(accepted)
    bindings = {
        INPUT_SCHEMA.as_posix(): INPUT_SCHEMA_SHA256,
        RESULT_SCHEMA.as_posix(): RESULT_SCHEMA_SHA256,
        PROBLEM_SCHEMA.as_posix(): PROBLEM_SCHEMA_SHA256,
    }
    clauses = [*contract["requires"], *contract["ensures"], *contract["invariants"]]
    for path, digest in bindings.items():
        if not any(f"{path}={digest}" in clause for clause in clauses):
            _fail(f"contract does not bind {path}")
    if production.CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract identity drift")
    return input_schema, result_schema, problem_schema


def _source_closure() -> dict[str, object]:
    source_path = ROOT / SOURCE
    source_raw = source_path.read_bytes()
    tree = ast.parse(source_raw, filename=str(source_path))
    imports: set[str] = set()
    forbidden: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".", 1)[0])
        elif isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in FORBIDDEN_NAMES:
                forbidden.append(f"{name}@{node.lineno}")
    if imports != ALLOWED_IMPORT_ROOTS:
        _fail(f"dependency-minimal import roots drift: {sorted(imports)}")
    if forbidden:
        _fail(f"forbidden effect calls in production source: {forbidden}")
    return {
        "forbidden_calls": 0,
        "import_roots": sorted(imports),
        "source_sha256": _sha(source_raw),
    }


def _validate_result_instance(value: object, problem_schema: dict[str, Any]) -> None:
    fields = {
        "contract_id",
        "contract_sha256",
        "diagnostics",
        "mathematical_authority",
        "problem_ir",
        "problem_ir_contract_sha256",
        "problem_ir_schema_sha256",
        "problem_ir_sha256",
        "reason_code",
        "schema",
        "status",
    }
    if type(value) is not dict or set(value) != fields:
        _fail("result schema field set drift")
    constants = {
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "mathematical_authority": False,
        "problem_ir_contract_sha256": PROBLEM_CONTRACT_SHA256,
        "problem_ir_schema_sha256": PROBLEM_SCHEMA_SHA256,
        "schema": "mathhead.problem-intake-result.v1",
    }
    if any(type(value[key]) is not type(expected) or value[key] != expected for key, expected in constants.items()):
        _fail("result schema constant binding drift")
    if value["status"] not in {"accepted", "exhausted", "invalid"}:
        _fail("result schema status drift")
    diagnostics = value["diagnostics"]
    if type(diagnostics) is not list or len(diagnostics) > 32:
        _fail("result schema diagnostics drift")
    for diagnostic in diagnostics:
        if type(diagnostic) is not dict or set(diagnostic) != {"code", "message", "path"}:
            _fail("result schema diagnostic field drift")
        if not all(type(diagnostic[key]) is str and diagnostic[key] for key in diagnostic):
            _fail("result schema diagnostic type drift")
    if value["status"] == "accepted":
        problem = value["problem_ir"]
        if type(problem) is not dict or type(value["problem_ir_sha256"]) is not str:
            _fail("accepted result schema payload drift")
        independent.validate_problem_ir(problem, problem_schema)
        if independent.canonical_sha256(problem) != value["problem_ir_sha256"]:
            _fail("accepted result schema identity drift")
        if diagnostics or value["reason_code"] != "ACCEPTED":
            _fail("accepted result schema combination drift")
    elif value["problem_ir"] is not None or value["problem_ir_sha256"] is not None or not diagnostics:
        _fail("failed result schema combination drift")


def _validate_one(
    scenario_id: str,
    problem: dict[str, Any],
    expected_sha256: str | None,
    *,
    problem_schema: dict[str, Any],
) -> dict[str, object]:
    result = production.intake_problem(
        {"schema": "mathhead.problem-intake.v1", "problem": problem}
    )
    if result.status != "accepted" or result.problem_ir_bytes is None:
        _fail(f"{scenario_id}: production intake rejected valid ProblemIR: {result.diagnostics}")
    output = json.loads(result.problem_ir_bytes)
    independent.validate_problem_ir(output, problem_schema)
    if independent.canonical_bytes(output) != result.problem_ir_bytes:
        _fail(f"{scenario_id}: independent canonical bytes drift")
    if expected_sha256 is not None and result.problem_ir_sha256 != expected_sha256:
        _fail(f"{scenario_id}: expected fixture identity drift")
    result_bytes = production.problem_intake_result_bytes(result)
    _validate_result_instance(json.loads(result_bytes), problem_schema)
    parsed = production.parse_problem_intake_result(result_bytes)
    if parsed != result or production.problem_intake_result_bytes(parsed) != result_bytes:
        _fail(f"{scenario_id}: result round trip drift")
    return {
        "problem_ir_bytes": len(result.problem_ir_bytes),
        "problem_ir_sha256": result.problem_ir_sha256,
        "result_bytes": len(result_bytes),
        "result_sha256": _sha(result_bytes),
        "scenario_id": scenario_id,
    }


def _fixture_checks(
    result_schema: dict[str, Any], problem_schema: dict[str, Any]
) -> list[dict[str, object]]:
    if result_schema.get("$id") != "https://mathhead.dev/schemas/problem-intake-result-v1.schema.json":
        _fail("result schema identity drift")
    results = [
        _validate_one(
            "minimal",
            independent.minimal_problem_ir(),
            independent.canonical_sha256(independent.minimal_problem_ir()),
            problem_schema=problem_schema,
        )
    ]
    manifest, _ = _load(Path("docs/fixtures/foundation-v1/manifest.json"))
    if manifest["scenario_order"] != [item["scenario_id"] for item in manifest["scenarios"]]:
        _fail("foundation scenario ordering drift")
    for scenario in manifest["scenarios"]:
        artifact = next(item for item in scenario["artifacts"] if item["role"] == "problem_ir")
        path = Path(f"docs/fixtures/foundation-v1/objects/{artifact['sha256']}.json")
        problem, raw = _load(path)
        if _sha(raw) != artifact["sha256"] or len(raw) != artifact["byte_count"]:
            _fail(f"{scenario['scenario_id']}: fixture object identity drift")
        results.append(
            _validate_one(
                scenario["scenario_id"],
                problem,
                artifact["sha256"],
                problem_schema=problem_schema,
            )
        )
    return results


def _negative_checks() -> int:
    controls: list[object] = [None, "x = x", b"x=x", ["x=x"], ("x=x",)]
    for value in controls:
        result = production.intake_problem(value)  # type: ignore[arg-type]
        if result.status == "accepted" or result.problem_ir_bytes is not None:
            _fail(f"non-structured input was accepted: {type(value).__name__}")
    missing = {"schema": "mathhead.problem-intake.v1", "problem": {}}
    result = production.intake_problem(missing)
    if result.status != "invalid" or result.problem_ir_sha256 is not None:
        _fail("partial ProblemIR did not fail closed")
    floating = independent.minimal_problem_ir()
    floating["extensions"] = {"org.mathhead.test": {"value": 0.5}}
    result = production.intake_problem(
        {"schema": "mathhead.problem-intake.v1", "problem": floating}
    )
    if result.reason_code != "INVALID_TYPE":
        _fail("floating input did not fail at exact type boundary")
    return len(controls) + 2


def _report() -> dict[str, object]:
    _input_schema, result_schema, problem_schema = _identity_checks()
    fixtures = _fixture_checks(result_schema, problem_schema)
    source = _source_closure()
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixtures": fixtures,
        "negative_controls": _negative_checks(),
        "problem_ir": {
            "contract_sha256": PROBLEM_CONTRACT_SHA256,
            "schema_sha256": PROBLEM_SCHEMA_SHA256,
        },
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schemas": {
            "input_sha256": INPUT_SCHEMA_SHA256,
            "result_sha256": RESULT_SCHEMA_SHA256,
        },
        "source": source,
        "summary": {
            "foundation_scenarios": len(fixtures) - 1,
            "mathematical_authority": False,
            "outputs_independently_valid": len(fixtures),
            "status": "passed",
            "unique_problem_identities": len({item["problem_ir_sha256"] for item in fixtures}),
        },
        "tests_sha256": _sha((ROOT / TEST_SOURCE).read_bytes()),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"problem-intake: report updated: {target}")
        return
    try:
        current = target.read_bytes()
    except OSError as exc:
        _fail(f"frozen report missing: {path}: {exc}")
    if current != payload:
        _fail(f"frozen report drift: {path}")


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
    except (ProblemIntakeReportError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"problem-intake: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "problem-intake: PASS "
        f"(scenarios={summary['foundation_scenarios']}, "
        f"outputs={summary['outputs_independently_valid']}, "
        f"unique={summary['unique_problem_identities']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
