#!/usr/bin/env python3
"""Independently validate the MH-041 alternative-reading boundary and report."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, Sequence

try:
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError
    from referencing import Registry, Resource
except ModuleNotFoundError:  # Dependency-minimal governed status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    Registry = Resource = None  # type: ignore[assignment,misc]

    class ValidationError(Exception):
        """Compatibility placeholder when the optional schema engine is absent."""


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mathhead import problem_readings as production  # noqa: E402
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


CONTRACT_ID = "MH-C-READING-ANALYSIS-002"
CONTRACT_SHA256 = "0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70"
PROJECTION_SCHEMA = Path("docs/contracts/schemas/reading-projection-v2.schema.json")
PROJECTION_SCHEMA_SHA256 = "99ce60e50472e4c9d8026e9af361e4d7b11c776e577aa57de46794998fb26241"
RESULT_SCHEMA = Path("docs/contracts/schemas/problem-readings-result-v2.schema.json")
RESULT_SCHEMA_SHA256 = "b05b16d280260ac7854477274852f0273e0a6cb011d740ae827ca172dad72894"
SOURCE = Path("src/mathhead/problem_readings.py")
TEST_SOURCE = Path("tests/problem_readings/test_problem_readings.py")
DEFAULT_REPORT = Path("docs/readings/reports/problem-readings-v2.json")
REPORT_SCHEMA = "mathhead.problem-readings-validation-report.v2"
ENTITY_REGISTRIES = (
    "source_documents",
    "source_spans",
    "domains",
    "variables",
    "expressions",
    "relations",
    "statements",
    "definitions",
    "assumptions",
    "goals",
)
SEMANTIC_REGISTRIES = frozenset(ENTITY_REGISTRIES[2:])
ALLOWED_IMPORT_ROOTS = {
    "__future__",
    "dataclasses",
    "hashlib",
    "json",
    "mathhead",
    "re",
    "typing",
    "unicodedata",
}
FORBIDDEN_CALLS = {
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


class ReadingReportError(RuntimeError):
    """An independent contract, source, output, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise ReadingReportError(detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _identity_checks() -> Any:
    expected = {
        PROJECTION_SCHEMA: PROJECTION_SCHEMA_SHA256,
        RESULT_SCHEMA: RESULT_SCHEMA_SHA256,
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
    }
    for relative, digest in expected.items():
        raw = (ROOT / relative).read_bytes()
        if _sha(raw) != digest:
            _fail(f"identity drift: {relative}")
        if relative.parent.name in {"contracts", "proposed"} and raw != _canonical(json.loads(raw)):
            _fail(f"noncanonical JSON artifact: {relative}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed:
        _fail("accepted and proposed contract bytes differ")
    manifest = (ROOT / "docs/contracts/manifest.toml").read_text(encoding="utf-8")
    record = (
        f'id = "{CONTRACT_ID}"\n'
        f'path = "docs/contracts/{CONTRACT_ID}.json"\n'
        f'sha256 = "{CONTRACT_SHA256}"\n'
        'state = "accepted"'
    )
    if manifest.count(record) != 1:
        _fail("accepted contract manifest binding drift")
    projection_schema = json.loads((ROOT / PROJECTION_SCHEMA).read_bytes())
    result_schema = json.loads((ROOT / RESULT_SCHEMA).read_bytes())
    expected_ids = {
        "https://mathhead.dev/schemas/reading-projection-v2.schema.json",
        "https://mathhead.dev/schemas/problem-readings-result-v2.schema.json",
    }
    if {projection_schema.get("$id"), result_schema.get("$id")} != expected_ids:
        _fail("schema identifier drift")
    for schema in (projection_schema, result_schema):
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail("closed Draft 2020-12 schema root drift")
    if production.CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract binding drift")
    schema_paths = (
        RESULT_SCHEMA,
        PROJECTION_SCHEMA,
        Path("docs/contracts/schemas/problem-intake-result-v1.schema.json"),
        Path("docs/contracts/schemas/problem-ir-v1.schema.json"),
    )
    if Draft202012Validator is None or Registry is None or Resource is None:
        return None
    schemas = [json.loads((ROOT / path).read_bytes()) for path in schema_paths]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    validator = Draft202012Validator(schemas[0], registry=registry)
    validator.check_schema(schemas[0])
    validator.check_schema(schemas[1])
    return validator


def _source_closure() -> dict[str, object]:
    raw = (ROOT / SOURCE).read_bytes()
    tree = ast.parse(raw, filename=str(SOURCE))
    imports: set[str] = set()
    forbidden: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            else:
                name = None
            if name in FORBIDDEN_CALLS:
                forbidden.append(f"{name}@{node.lineno}")
    if imports != ALLOWED_IMPORT_ROOTS:
        _fail(f"dependency-minimal import roots drift: {sorted(imports)}")
    if forbidden:
        _fail(f"forbidden effect calls in production source: {forbidden}")
    return {
        "forbidden_calls": 0,
        "import_roots": sorted(imports),
        "source_sha256": _sha(raw),
    }


def _alternative_problem(*, status: str = "unresolved") -> dict[str, Any]:
    problem = minimal_problem_ir()
    problem["variables"].append(
        {"id": "variable_y", "name": "y", "domain_id": "domain_integer", "role": "bound", "span_ids": []}
    )
    problem["expressions"].append(
        {"id": "expression_y", "kind": "variable", "domain_id": "domain_integer", "variable_id": "variable_y", "span_ids": []}
    )
    problem["relations"].append(
        {"id": "relation_y", "kind": "equal", "operand_expr_ids": ["expression_y", "expression_y"], "span_ids": []}
    )
    problem["statements"].extend(
        [
            {"id": "statement_body_y", "kind": "relation", "relation_id": "relation_y", "span_ids": []},
            {"id": "statement_exists", "kind": "quantified", "quantifier": "exists", "variable_ids": ["variable_y"], "body_statement_id": "statement_body_y", "span_ids": []},
        ]
    )
    problem["goals"].append(
        {"id": "goal_exists", "statement_id": "statement_exists", "mode": "prove", "span_ids": []}
    )
    affected = sorted(
        {
            "variable_x", "expression_x", "relation_reflexive", "statement_body",
            "statement_forall", "goal_reflexive", "variable_y", "expression_y",
            "relation_y", "statement_body_y", "statement_exists", "goal_exists",
        }
    )
    problem["readings"].append(
        {
            "id": "reading_exists",
            "label": "There exists an integer y such that y equals itself.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_exists"],
            "difference_from": "reading_only",
            "differences": [{"kind": "quantifier", "summary": "The quantified goal differs.", "affected_ids": affected, "span_ids": []}],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": status,
        "candidate_reading_ids": ["reading_exists", "reading_only"],
        "selected_reading_id": "reading_exists" if status == "resolved" else None,
        "required_choice": "Choose the intended quantified reading." if status == "unresolved" else None,
    }
    return problem


def _accepted(problem: dict[str, Any]) -> bytes:
    result = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
    if result.status != "accepted":
        _fail(f"fixture intake failed: {result.reason_code}: {result.diagnostics}")
    return problem_intake_result_bytes(result)


def _indexes(problem: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    indexes = {registry: {item["id"]: item for item in problem[registry]} for registry in (*ENTITY_REGISTRIES, "readings")}
    owners = {
        entity_id: registry
        for registry, records in indexes.items()
        for entity_id in records
    }
    return indexes, owners


def _dependencies(registry: str, record: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def add(owner: str, value: str | None) -> None:
        if value is not None:
            result.append((owner, value))

    def extend(owner: str, values: list[str]) -> None:
        result.extend((owner, value) for value in values)

    if registry != "source_documents":
        extend("source_spans", record.get("span_ids", []))
    if registry == "source_spans":
        add("source_documents", record["source_id"])
    elif registry == "domains":
        kind = record["kind"]
        if kind == "finite":
            add("domains", record["element_domain_id"])
            extend("expressions", record["element_expr_ids"])
        elif kind == "interval":
            add("expressions", record["lower_expr_id"])
            add("expressions", record["upper_expr_id"])
        elif kind == "modular":
            add("expressions", record["modulus_expr_id"])
        elif kind == "collection":
            add("domains", record["element_domain_id"])
        elif kind == "product":
            extend("domains", record["factor_domain_ids"])
        elif kind == "function":
            extend("domains", record["parameter_domain_ids"])
            add("domains", record["result_domain_id"])
        elif kind == "structure":
            extend("domains", record["parameter_domain_ids"])
            extend("expressions", record["parameter_expr_ids"])
    elif registry == "variables":
        add("domains", record["domain_id"])
    elif registry == "expressions":
        add("domains", record["domain_id"])
        kind = record["kind"]
        if kind == "variable":
            add("variables", record["variable_id"])
        elif kind == "apply":
            extend("expressions", record["argument_expr_ids"])
        elif kind in {"tuple", "collection"}:
            extend("expressions", record["element_expr_ids"])
        elif kind == "conditional":
            add("statements", record["condition_statement_id"])
            add("expressions", record["then_expr_id"])
            add("expressions", record["else_expr_id"])
    elif registry == "relations":
        extend("expressions", record["operand_expr_ids"])
    elif registry == "statements":
        if record["kind"] == "relation":
            add("relations", record["relation_id"])
        elif record["kind"] == "logical":
            extend("statements", record["operand_statement_ids"])
        elif record["kind"] == "quantified":
            extend("variables", record["variable_ids"])
            add("statements", record["body_statement_id"])
    elif registry == "definitions":
        extend("variables", record["parameter_variable_ids"])
        add("domains", record["result_domain_id"])
        body = record["body"]
        add("expressions" if body["kind"] == "expression" else "statements", body["expression_id"] if body["kind"] == "expression" else body["statement_id"])
    elif registry in {"assumptions", "goals"}:
        add("statements", record["statement_id"])
    return result


def _projection(problem: dict[str, Any], reading: dict[str, Any], base_id: str) -> tuple[dict[str, Any], frozenset[str]]:
    indexes, _owners = _indexes(problem)
    included = {registry: set() for registry in ENTITY_REGISTRIES}
    pending = [*(('definitions', item) for item in reading["definition_ids"]), *(('assumptions', item) for item in reading["assumption_ids"]), *(('goals', item) for item in reading["goal_ids"]), *(('source_spans', item) for item in reading["span_ids"])]
    while pending:
        registry, entity_id = pending.pop()
        if entity_id in included[registry]:
            continue
        included[registry].add(entity_id)
        pending.extend(_dependencies(registry, indexes[registry][entity_id]))
    entity_ids = sorted(entity_id for values in included.values() for entity_id in values)
    value = {
        "schema": "mathhead.reading-projection.v2",
        "problem_ir_sha256": _sha(_canonical(problem)),
        "reading_id": reading["id"],
        "label": reading["label"],
        "base_reading_id": base_id,
        "is_base": reading["id"] == base_id,
        "definition_ids": list(reading["definition_ids"]),
        "assumption_ids": list(reading["assumption_ids"]),
        "goal_ids": list(reading["goal_ids"]),
        "reading_span_ids": list(reading["span_ids"]),
        "source_span_ids": sorted(included["source_spans"]),
        "entity_ids": entity_ids,
        "entities": {
            registry: [item for item in problem[registry] if item["id"] in included[registry]]
            for registry in ENTITY_REGISTRIES
        },
        "extensions": problem["extensions"],
    }
    return value, frozenset(entity_ids)


def _positions(reading: dict[str, Any]) -> dict[str, tuple[str, int]]:
    return {
        entity_id: (field, index)
        for field in ("definition_ids", "assumption_ids", "goal_ids")
        for index, entity_id in enumerate(reading[field])
    }


def _fragment(ids: set[str], closure: frozenset[str], reading: dict[str, Any], indexes: dict[str, dict[str, Any]], owners: dict[str, str]) -> bytes | None:
    values = []
    positions = _positions(reading)
    for entity_id in sorted(ids & set(closure)):
        registry = owners[entity_id]
        item = {"id": entity_id, "registry": registry, "record": indexes[registry][entity_id], "reading_span_ids": list(reading["span_ids"])}
        if entity_id in positions:
            field, index = positions[entity_id]
            item["root"] = {"field": field, "index": index}
        values.append(item)
    return _canonical(values) if values else None


def _verify_deltas(problem: dict[str, Any], base: dict[str, Any], reading: dict[str, Any], base_closure: frozenset[str], closure: frozenset[str], output: list[dict[str, Any]]) -> None:
    indexes, owners = _indexes(problem)
    changed = {item for item in base_closure ^ closure if owners[item] in SEMANTIC_REGISTRIES}
    base_positions = _positions(base)
    positions = _positions(reading)
    changed.update(item for item in set(base_positions) & set(positions) if base_positions[item] != positions[item])
    span_changes = set(base["span_ids"]) ^ set(reading["span_ids"])
    for difference in reading["differences"]:
        if difference["kind"] in {"notation", "parse"} and set(difference["span_ids"]) & span_changes:
            changed.update(item for item in difference["affected_ids"] if item in base_closure and item in closure and owners[item] in SEMANTIC_REGISTRIES)
    if len(output) != len(reading["differences"]):
        _fail(f"{reading['id']}: delta count drift")
    claimed: set[str] = set()
    for ordinal, (declared, actual) in enumerate(zip(reading["differences"], output, strict=True)):
        affected = set(declared["affected_ids"])
        if not affected or not affected <= changed or claimed & affected:
            _fail(f"{reading['id']}: invalid affected partition")
        claimed.update(affected)
        removed = affected & (set(base_closure) - set(closure))
        added = affected & (set(closure) - set(base_closure))
        retained = affected - removed - added
        paths = set()
        source_evidence = bool(set(declared["span_ids"]) & span_changes)
        for entity_id in affected:
            registry = owners[entity_id]
            if entity_id in removed:
                paths.add(f"$.base.entities.{registry}.{entity_id}")
            elif entity_id in added:
                paths.add(f"$.alternative.entities.{registry}.{entity_id}")
            elif base_positions.get(entity_id) != positions.get(entity_id):
                paths.add(f"$.goal_ids.{entity_id}")
            elif declared["kind"] in {"notation", "parse"} and source_evidence:
                paths.add(f"$.reading_span_ids.{entity_id}")
            else:
                _fail(f"{reading['id']}: retained ID lacks evidence")
        before = _fragment(affected, base_closure, base, indexes, owners)
        after = _fragment(affected, closure, reading, indexes, owners)
        expected = {
            "ordinal": ordinal,
            "kind": declared["kind"],
            "summary": declared["summary"],
            "affected_ids": sorted(affected),
            "span_ids": list(declared["span_ids"]),
            "removed_ids": sorted(removed),
            "added_ids": sorted(added),
            "retained_ids": sorted(retained),
            "paths": sorted(paths),
            "before_sha256": _sha(before) if before is not None else None,
            "after_sha256": _sha(after) if after is not None else None,
        }
        if actual != expected:
            _fail(f"{reading['id']}: independently recomputed delta drift")
    if claimed != changed:
        _fail(f"{reading['id']}: omitted structural changes")


def _verify_result(
    scenario_id: str,
    intake: bytes,
    schema_validator: Any,
) -> dict[str, object]:
    result = production.analyze_problem_readings(intake)
    if result.status != "analyzed":
        _fail(f"{scenario_id}: production rejected valid fixture: {result.diagnostics}")
    raw = production.reading_analysis_result_bytes(result)
    value = json.loads(raw)
    if schema_validator is not None:
        schema_validator.validate(value)
    if raw != _canonical(value):
        _fail(f"{scenario_id}: result bytes are noncanonical")
    if _canonical(value["intake_result"]) != intake:
        _fail(f"{scenario_id}: embedded intake bytes drift")
    problem = value["intake_result"]["problem_ir"]
    if value["input_result_sha256"] != _sha(intake) or value["problem_ir_sha256"] != _sha(_canonical(problem)):
        _fail(f"{scenario_id}: top-level input identity drift")
    bases = [item for item in problem["readings"] if item["difference_from"] is None]
    if len(bases) != 1:
        _fail(f"{scenario_id}: base topology drift")
    base = bases[0]
    readings = {item["id"]: item for item in problem["readings"]}
    if [item["reading_id"] for item in value["candidates"]] != sorted(readings):
        _fail(f"{scenario_id}: candidate ordering drift")
    expected_projections = {item["id"]: _projection(problem, item, base["id"]) for item in problem["readings"]}
    base_closure = expected_projections[base["id"]][1]
    for candidate in value["candidates"]:
        reading = readings[candidate["reading_id"]]
        expected_projection, closure = expected_projections[reading["id"]]
        projection_bytes = _canonical(candidate["projection"])
        if candidate["projection"] != expected_projection or candidate["projection_sha256"] != _sha(projection_bytes):
            _fail(f"{scenario_id}: independently recomputed projection drift")
        if reading is base:
            if candidate["difference_from"] is not None or candidate["deltas"]:
                _fail(f"{scenario_id}: base candidate delta drift")
        else:
            if candidate["difference_from"] != base["id"]:
                _fail(f"{scenario_id}: alternative base link drift")
            _verify_deltas(problem, base, reading, base_closure, closure, candidate["deltas"])
    ambiguity = problem["ambiguity"]
    if value["ambiguity_status"] != ambiguity["status"] or value["selected_reading_id"] != ambiguity["selected_reading_id"]:
        _fail(f"{scenario_id}: ambiguity state drift")
    if ambiguity["status"] == "unresolved":
        expected_choice = {"prompt": ambiguity["required_choice"], "candidate_reading_ids": ambiguity["candidate_reading_ids"], "selection_required": True}
        if value["required_choice"] != expected_choice:
            _fail(f"{scenario_id}: required choice drift")
    elif value["required_choice"] is not None:
        _fail(f"{scenario_id}: surplus required choice")
    if value["mathematical_authority"] is not False:
        _fail(f"{scenario_id}: authority drift")
    parsed = production.parse_reading_analysis_result(raw)
    if production.reading_analysis_result_bytes(parsed) != raw:
        _fail(f"{scenario_id}: strict replay drift")
    return {
        "ambiguity_status": value["ambiguity_status"],
        "candidates": len(value["candidates"]),
        "problem_ir_sha256": value["problem_ir_sha256"],
        "result_bytes": len(raw),
        "result_sha256": _sha(raw),
        "scenario_id": scenario_id,
    }


def _negative_checks(schema_validator: Any) -> int:
    count = 0
    for value in (None, "x = x", bytearray(b"{}\n"), b"{}\n"):
        result = production.analyze_problem_readings(value)  # type: ignore[arg-type]
        if result.status == "analyzed" or result.candidates:
            _fail(f"invalid input produced analysis: {type(value).__name__}")
        if schema_validator is not None:
            schema_validator.validate(json.loads(production.reading_analysis_result_bytes(result)))
        count += 1
    false = _alternative_problem()
    false["readings"][1]["goal_ids"] = list(false["readings"][0]["goal_ids"])
    result = production.analyze_problem_readings(_accepted(false))
    if result.reason_code != "INVALID_DIFFERENCE" or result.candidates:
        _fail("false declared difference did not fail closed")
    count += 1
    valid = production.analyze_problem_readings(_accepted(_alternative_problem()))
    raw = production.reading_analysis_result_bytes(valid)
    forged = json.loads(raw)
    forged["candidates"][0]["projection_sha256"] = "0" * 64
    try:
        production.parse_reading_analysis_result(_canonical(forged))
    except production.ReadingAnalysisValidationError:
        count += 1
    else:
        _fail("forged projection digest passed strict replay")
    try:
        production.parse_reading_analysis_result(raw.rstrip(b"\n"))
    except production.ReadingAnalysisValidationError:
        count += 1
    else:
        _fail("noncanonical result bytes passed strict replay")
    return count


def _report() -> dict[str, object]:
    schema_validator = _identity_checks()
    fixtures = [
        _verify_result("minimal-unambiguous", _accepted(minimal_problem_ir()), schema_validator),
        _verify_result("quantifier-unresolved", _accepted(_alternative_problem()), schema_validator),
        _verify_result(
            "quantifier-resolved",
            _accepted(_alternative_problem(status="resolved")),
            schema_validator,
        ),
    ]
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixtures": fixtures,
        "negative_controls": _negative_checks(schema_validator),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schemas": {
            "projection_sha256": PROJECTION_SCHEMA_SHA256,
            "result_sha256": RESULT_SCHEMA_SHA256,
        },
        "source": _source_closure(),
        "summary": {
            "analyzed_outputs": len(fixtures),
            "mathematical_authority": False,
            "status": "passed",
            "unique_result_identities": len({item["result_sha256"] for item in fixtures}),
        },
        "tests_sha256": _sha((ROOT / TEST_SOURCE).read_bytes()),
        "validator_sha256": _sha((ROOT / "tools/validate_problem_readings.py").read_bytes()),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"problem-readings: report updated: {target}")
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
    except (
        ReadingReportError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        print(f"problem-readings: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "problem-readings: PASS "
        f"(outputs={summary['analyzed_outputs']}, "
        f"unique={summary['unique_result_identities']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
