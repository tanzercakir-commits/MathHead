#!/usr/bin/env python3
"""Independently validate the MH-042 domain-assumption boundary and report."""

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

from mathhead import domain_assumptions as production  # noqa: E402
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


CONTRACT_ID = "MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001"
CONTRACT_SHA256 = "609bc3a0773016f73d4bcee21d6aef034c74bb8edb36fddd9b6df1a4f4ba219a"
FACT_SCHEMA = Path("docs/contracts/schemas/domain-assumption-fact-v1.schema.json")
FACT_SCHEMA_SHA256 = "4d32547bc93a5bb8ddee5424eae9ce4d39c99c0f9df689db317b41dfa5e0f023"
CONTEXT_SCHEMA = Path("docs/contracts/schemas/normalized-domain-context-v1.schema.json")
CONTEXT_SCHEMA_SHA256 = "066657d0b81e3589c201e1351eeb0e763f0720087864869419f5cd3317fea67e"
RULE_SCHEMA = Path("docs/contracts/schemas/domain-assumption-rules-v1.schema.json")
RULE_SCHEMA_SHA256 = "cc06944ce150dab0f737f21928e62779c63ead9083cedf5de372c3649f6f8d4b"
RESULT_SCHEMA = Path("docs/contracts/schemas/domain-assumption-result-v1.schema.json")
RESULT_SCHEMA_SHA256 = "2f391074cfc3eae63933bcf91bb04688fddccf2b67eca6d5904edc635e9643ee"
RULE_CATALOGUE = Path("docs/normalization/domain-assumption-rules-v1.json")
RULE_CATALOGUE_SHA256 = "4d2a14589c7ae8a4a217987f5f7ddfdfc14d7fcf170049a2c8a6c2eb90a7b0b9"
SOURCE = Path("src/mathhead/domain_assumptions.py")
TEST_SOURCE = Path("tests/domain_assumptions/test_domain_assumptions.py")
DEFAULT_REPORT = Path("docs/normalization/reports/domain-assumption-v1.json")
REPORT_SCHEMA = "mathhead.domain-assumption-validation-report.v1"

ENTITY_REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals",
)
SEMANTIC_REGISTRIES = frozenset(ENTITY_REGISTRIES[2:])
ALLOWED_IMPORT_ROOTS = {
    "__future__", "dataclasses", "hashlib", "json", "mathhead", "re",
    "typing", "unicodedata",
}
FORBIDDEN_CALLS = {
    "Path", "eval", "exec", "getenv", "import_module", "open", "perf_counter",
    "run", "system", "time",
}
DOMAIN_RULES = {
    "builtin": ("mh.normalize.domain.builtin", "builtin_domain"),
    "finite": ("mh.normalize.domain.finite", "finite_domain"),
    "interval": ("mh.normalize.domain.interval", "interval_domain"),
    "modular": ("mh.normalize.domain.modular", "modular_domain"),
    "collection": ("mh.normalize.domain.collection", "collection_domain"),
    "product": ("mh.normalize.domain.product", "product_domain"),
    "function": ("mh.normalize.domain.function", "function_domain"),
    "structure": ("mh.normalize.domain.structure", "structure_domain"),
}
RELATION_RULES = {
    "equal": ("mh.normalize.assumption.equal", "equality_assumption"),
    "not_equal": ("mh.normalize.assumption.not-equal", "disequality_assumption"),
    "less": ("mh.normalize.assumption.bound", "bound_assumption"),
    "less_equal": ("mh.normalize.assumption.bound", "bound_assumption"),
    "greater": ("mh.normalize.assumption.bound", "bound_assumption"),
    "greater_equal": ("mh.normalize.assumption.bound", "bound_assumption"),
    "member": ("mh.normalize.assumption.member", "membership_assumption"),
    "not_member": ("mh.normalize.assumption.not-member", "nonmembership_assumption"),
    "divides": ("mh.normalize.assumption.divides", "divisibility_assumption"),
    "congruent": ("mh.normalize.assumption.congruent", "congruence_assumption"),
}
PREDICATE_RULES = {
    ("org.mathhead.property.nonzero", 1): ("mh.normalize.predicate.nonzero", "nonzero_assumption"),
    ("org.mathhead.property.finite", 1): ("mh.normalize.predicate.finite", "finiteness_assumption"),
    ("org.mathhead.property.cardinality", 2): ("mh.normalize.predicate.cardinality", "cardinality_assumption"),
    ("org.mathhead.property.dimension", 2): ("mh.normalize.predicate.dimension", "dimension_assumption"),
    ("org.mathhead.graph.class", 2): ("mh.normalize.predicate.graph-class", "graph_class_assumption"),
    ("org.mathhead.analysis.regularity", 2): ("mh.normalize.predicate.regularity", "regularity_assumption"),
}


class DomainAssumptionReportError(RuntimeError):
    """An independent contract, source, output, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise DomainAssumptionReportError(detail)


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
        FACT_SCHEMA: FACT_SCHEMA_SHA256,
        CONTEXT_SCHEMA: CONTEXT_SCHEMA_SHA256,
        RULE_SCHEMA: RULE_SCHEMA_SHA256,
        RESULT_SCHEMA: RESULT_SCHEMA_SHA256,
        RULE_CATALOGUE: RULE_CATALOGUE_SHA256,
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
        _fail("accepted/proposed contract canonical binding drift")
    manifest = (ROOT / "docs/contracts/manifest.toml").read_text(encoding="utf-8")
    record = (
        f'id = "{CONTRACT_ID}"\n'
        f'path = "docs/contracts/{CONTRACT_ID}.json"\n'
        f'sha256 = "{CONTRACT_SHA256}"\n'
        'state = "accepted"'
    )
    if manifest.count(record) != 1:
        _fail("accepted contract manifest binding drift")
    if production.CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract binding drift")
    if production.RULE_CATALOGUE_SHA256 != RULE_CATALOGUE_SHA256:
        _fail("production rule-catalogue binding drift")

    schemas: list[dict[str, Any]] = []
    for path in sorted((ROOT / "docs/contracts/schemas").glob("*.schema.json")):
        schema = json.loads(path.read_bytes())
        if "$id" in schema:
            schemas.append(schema)
    selected = {
        schema["$id"]: schema
        for schema in schemas
        if schema["$id"] in {
            "https://mathhead.dev/schemas/domain-assumption-fact-v1.schema.json",
            "https://mathhead.dev/schemas/normalized-domain-context-v1.schema.json",
            "https://mathhead.dev/schemas/domain-assumption-rules-v1.schema.json",
            "https://mathhead.dev/schemas/domain-assumption-result-v1.schema.json",
        }
    }
    if len(selected) != 4:
        _fail("normalization schema identifiers drift")
    for schema in selected.values():
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail("closed Draft 2020-12 schema root drift")
    catalogue = json.loads((ROOT / RULE_CATALOGUE).read_bytes())
    rule_ids = [item["rule_id"] for item in catalogue["rules"]]
    if len(rule_ids) != len(set(rule_ids)) or catalogue["mathematical_authority"] is not False:
        _fail("rule catalogue closure or authority drift")
    expected_rule_ids = {
        rule_id for rule_id, _kind in DOMAIN_RULES.values()
    } | {
        "mh.normalize.variable.domain",
        "mh.normalize.assumption.truth",
        "mh.normalize.assumption.opaque-relation",
        "mh.normalize.assumption.opaque-predicate",
        "mh.normalize.assumption.logical",
        "mh.normalize.assumption.quantified",
        "mh.normalize.assumption.nonzero-relation",
    } | {rule_id for rule_id, _kind in RELATION_RULES.values()} | {
        rule_id for rule_id, _kind in PREDICATE_RULES.values()
    }
    if set(rule_ids) != expected_rule_ids:
        _fail("rule catalogue membership drift")
    if Draft202012Validator is None or Registry is None or Resource is None:
        return None
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    for schema in selected.values():
        Draft202012Validator.check_schema(schema)
    rule_validator = Draft202012Validator(selected[
        "https://mathhead.dev/schemas/domain-assumption-rules-v1.schema.json"
    ], registry=registry)
    rule_validator.validate(catalogue)
    return Draft202012Validator(selected[
        "https://mathhead.dev/schemas/domain-assumption-result-v1.schema.json"
    ], registry=registry)


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


def _fixture_problem() -> dict[str, Any]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"
    problem["statements"] = [item for item in problem["statements"] if item["id"] != "statement_forall"]
    problem["goals"][0]["statement_id"] = "statement_body"
    problem["domains"].append(
        {"id": "domain_integer_set", "kind": "collection", "collection": "set", "element_domain_id": "domain_integer", "finiteness": "unknown", "span_ids": []}
    )
    problem["expressions"].extend(
        [
            {"id": "expression_zero", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "0", "span_ids": []},
            {"id": "expression_set", "kind": "collection", "domain_id": "domain_integer_set", "element_expr_ids": ["expression_x"], "span_ids": []},
        ]
    )
    problem["relations"].extend(
        [
            {"id": "relation_not_equal_zero", "kind": "not_equal", "operand_expr_ids": ["expression_x", "expression_zero"], "span_ids": []},
            {"id": "relation_member", "kind": "member", "operand_expr_ids": ["expression_x", "expression_set"], "span_ids": []},
            {"id": "relation_opaque", "kind": "predicate", "predicate": "org.example.unknown.property", "operand_expr_ids": ["expression_x"], "span_ids": []},
        ]
    )
    problem["statements"].extend(
        [
            {"id": "statement_not_equal_zero", "kind": "relation", "relation_id": "relation_not_equal_zero", "span_ids": []},
            {"id": "statement_member", "kind": "relation", "relation_id": "relation_member", "span_ids": []},
            {"id": "statement_opaque", "kind": "relation", "relation_id": "relation_opaque", "span_ids": []},
            {"id": "statement_truth", "kind": "truth", "value": True, "span_ids": []},
        ]
    )
    problem["assumptions"].extend(
        [
            {"id": "assumption_domain", "statement_id": "statement_not_equal_zero", "role": "domain_constraint", "span_ids": []},
            {"id": "assumption_given", "statement_id": "statement_truth", "role": "given", "span_ids": []},
            {"id": "assumption_member", "statement_id": "statement_member", "role": "side_condition", "span_ids": []},
            {"id": "assumption_opaque", "statement_id": "statement_opaque", "role": "side_condition", "span_ids": []},
        ]
    )
    problem["readings"][0]["assumption_ids"] = [
        "assumption_domain", "assumption_given", "assumption_member", "assumption_opaque"
    ]
    for registry in (
        "domains", "variables", "expressions", "relations", "statements", "assumptions"
    ):
        problem[registry].sort(key=lambda item: item["id"])
    return problem


def _analysis(problem: dict[str, Any]) -> bytes:
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
    if intake.status != "accepted":
        _fail(f"fixture intake failed: {intake.reason_code}: {intake.diagnostics}")
    analyzed = analyze_problem_readings(problem_intake_result_bytes(intake))
    if analyzed.status != "analyzed":
        _fail(f"fixture analysis failed: {analyzed.reason_code}: {analyzed.diagnostics}")
    return reading_analysis_result_bytes(analyzed)


def _indexes(projection: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        registry: {item["id"]: item for item in projection["entities"][registry]}
        for registry in ENTITY_REGISTRIES
    }


def _dependencies(registry: str, record: dict[str, Any]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    def add(owner: str, value: str | None) -> None:
        if value is not None:
            result.append((owner, value))

    def extend(owner: str, values: list[str]) -> None:
        result.extend((owner, item) for item in values)

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


def _closure(
    registry: str,
    entity_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> tuple[list[str], list[str], dict[str, Any]]:
    origin = indexes[registry][entity_id]
    seen = {(registry, entity_id)}
    pending = list(_dependencies(registry, origin))
    while pending:
        owner, dependency_id = pending.pop()
        key = (owner, dependency_id)
        if key in seen:
            continue
        if dependency_id not in indexes[owner]:
            _fail(f"missing independent closure dependency: {owner}.{dependency_id}")
        seen.add(key)
        pending.extend(_dependencies(owner, indexes[owner][dependency_id]))
    semantic = sorted(
        (owner, dependency_id)
        for owner, dependency_id in seen
        if owner in SEMANTIC_REGISTRIES and (owner, dependency_id) != (registry, entity_id)
    )
    spans = sorted(item for owner, item in seen if owner == "source_spans")
    sources = sorted(item for owner, item in seen if owner == "source_documents")
    fragment = {
        "origin": {"registry": registry, "record": origin},
        "dependencies": [
            {"registry": owner, "record": indexes[owner][item]}
            for owner, item in semantic
        ],
        "source_spans": [indexes["source_spans"][item] for item in spans],
        "source_documents": [indexes["source_documents"][item] for item in sources],
    }
    return sorted(item for _owner, item in semantic), spans, fragment


def _finish_fact(value: dict[str, Any]) -> dict[str, Any]:
    value["fact_sha256"] = _sha(_canonical(value))
    return value


def _base_fact(
    ordinal: int,
    reading_id: str,
    registry: str,
    origin_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    record = indexes[registry][origin_id]
    dependencies, spans, fragment = _closure(registry, origin_id, indexes)
    if registry == "domains":
        rule_id, kind = DOMAIN_RULES[record["kind"]]
        subjects = sorted({item for owner, item in _dependencies(registry, record) if owner in SEMANTIC_REGISTRIES})
        payload = {"domain": record}
    else:
        rule_id, kind = "mh.normalize.variable.domain", "variable_domain"
        subjects = [origin_id]
        payload = {"variable": record}
    return _finish_fact({
        "schema": "mathhead.domain-assumption-fact.v1",
        "ordinal": ordinal,
        "reading_id": reading_id,
        "rule_id": rule_id,
        "kind": kind,
        "assumption_role": None,
        "origin_registry": registry,
        "origin_id": origin_id,
        "statement_id": None,
        "relation_id": None,
        "subject_ids": subjects,
        "dependency_ids": dependencies,
        "span_ids": spans,
        "fragment_sha256": _sha(_canonical(fragment)),
        "payload": payload,
        "supported": True,
        "mathematical_authority": False,
    })


def _assumption_rule(statement: dict[str, Any], relation: dict[str, Any] | None) -> tuple[str, str, bool]:
    if statement["kind"] == "truth":
        return "mh.normalize.assumption.truth", "truth_assumption", True
    if statement["kind"] == "logical":
        return "mh.normalize.assumption.logical", "logical_assumption", False
    if statement["kind"] == "quantified":
        return "mh.normalize.assumption.quantified", "quantified_assumption", False
    assert relation is not None
    if relation["kind"] == "predicate":
        match = PREDICATE_RULES.get((relation["predicate"], len(relation["operand_expr_ids"])))
        return (*match, True) if match is not None else (
            "mh.normalize.assumption.opaque-predicate", "opaque_predicate_assumption", False
        )
    match = RELATION_RULES.get(relation["kind"])
    return (*match, True) if match is not None else (
        "mh.normalize.assumption.opaque-relation", "opaque_relation_assumption", False
    )


def _assumption_facts(
    ordinal: int,
    reading_id: str,
    assumption_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    assumption = indexes["assumptions"][assumption_id]
    statement = indexes["statements"][assumption["statement_id"]]
    relation = indexes["relations"][statement["relation_id"]] if statement["kind"] == "relation" else None
    rule_id, kind, supported = _assumption_rule(statement, relation)
    dependencies, spans, fragment = _closure("assumptions", assumption_id, indexes)
    if relation is not None:
        subjects = sorted(set(relation["operand_expr_ids"]))
    elif statement["kind"] == "logical":
        subjects = sorted(set(statement["operand_statement_ids"]))
    elif statement["kind"] == "quantified":
        subjects = sorted({*statement["variable_ids"], statement["body_statement_id"]})
    else:
        subjects = [statement["id"]]
    payload = {"assumption": assumption, "statement": statement, "relation": relation}
    common = {
        "schema": "mathhead.domain-assumption-fact.v1",
        "reading_id": reading_id,
        "assumption_role": assumption["role"],
        "origin_registry": "assumptions",
        "origin_id": assumption_id,
        "statement_id": statement["id"],
        "relation_id": None if relation is None else relation["id"],
        "dependency_ids": dependencies,
        "span_ids": spans,
        "fragment_sha256": _sha(_canonical(fragment)),
        "mathematical_authority": False,
    }
    facts = [_finish_fact({
        **common,
        "ordinal": ordinal,
        "rule_id": rule_id,
        "kind": kind,
        "subject_ids": subjects,
        "payload": payload,
        "supported": supported,
    })]
    if relation is None or relation["kind"] != "not_equal" or len(relation["operand_expr_ids"]) != 2:
        return facts
    zero_matches = []
    for index, expression_id in enumerate(relation["operand_expr_ids"]):
        expression = indexes["expressions"][expression_id]
        if expression["kind"] == "literal" and (
            (expression["literal_type"] == "integer" and expression["value"] == "0")
            or (expression["literal_type"] == "rational" and expression["value"].split("/", 1)[0] == "0")
        ):
            zero_matches.append(index)
    if len(zero_matches) != 1:
        return facts
    zero_index = zero_matches[0]
    subject = relation["operand_expr_ids"][1 - zero_index]
    facts.append(_finish_fact({
        **common,
        "ordinal": ordinal + 1,
        "rule_id": "mh.normalize.assumption.nonzero-relation",
        "kind": "nonzero_assumption",
        "subject_ids": [subject],
        "payload": {**payload, "zero_operand_index": zero_index, "subject_expr_id": subject},
        "supported": True,
    }))
    return facts


def _expected_context(candidate: dict[str, Any]) -> dict[str, Any]:
    projection = candidate["projection"]
    indexes = _indexes(projection)
    reading_id = candidate["reading_id"]
    domain_ids = sorted(indexes["domains"])
    variable_ids = sorted(indexes["variables"])
    assumption_ids = list(projection["assumption_ids"])
    facts: list[dict[str, Any]] = []
    for domain_id in domain_ids:
        facts.append(_base_fact(len(facts), reading_id, "domains", domain_id, indexes))
    for variable_id in variable_ids:
        facts.append(_base_fact(len(facts), reading_id, "variables", variable_id, indexes))
    for assumption_id in assumption_ids:
        facts.extend(_assumption_facts(len(facts), reading_id, assumption_id, indexes))
    return {
        "schema": "mathhead.normalized-domain-context.v1",
        "reading_id": reading_id,
        "projection_sha256": candidate["projection_sha256"],
        "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
        "domain_ids": domain_ids,
        "variable_ids": variable_ids,
        "assumption_ids": assumption_ids,
        "facts": facts,
        "fact_sha256s": [item["fact_sha256"] for item in facts],
        "unsupported_fact_sha256s": [item["fact_sha256"] for item in facts if not item["supported"]],
        "mathematical_authority": False,
    }


def _verify_result(schema_validator: Any) -> dict[str, object]:
    input_bytes = _analysis(_fixture_problem())
    result = production.normalize_domain_assumptions(input_bytes)
    if result.status != "normalized":
        _fail(f"production rejected valid fixture: {result.diagnostics}")
    raw = production.domain_assumption_result_bytes(result)
    value = json.loads(raw)
    if schema_validator is not None:
        schema_validator.validate(value)
    if raw != _canonical(value):
        _fail("result bytes are noncanonical")
    if value["input_result_sha256"] != _sha(input_bytes):
        _fail("input result identity drift")
    if _canonical(value["readings_result"]) != input_bytes:
        _fail("embedded reading-analysis bytes drift")
    upstream = {item["reading_id"]: item for item in value["readings_result"]["candidates"]}
    if [item["reading_id"] for item in value["candidates"]] != sorted(upstream):
        _fail("candidate membership or order drift")
    facts = 0
    unsupported = 0
    for candidate in value["candidates"]:
        expected = _expected_context(upstream[candidate["reading_id"]])
        if candidate["context"] != expected:
            _fail(f"{candidate['reading_id']}: independently recomputed context drift")
        if candidate["context_sha256"] != _sha(_canonical(expected)):
            _fail(f"{candidate['reading_id']}: independently recomputed context identity drift")
        if candidate["projection_sha256"] != upstream[candidate["reading_id"]]["projection_sha256"]:
            _fail(f"{candidate['reading_id']}: projection binding drift")
        facts += len(expected["facts"])
        unsupported += len(expected["unsupported_fact_sha256s"])
    if value["mathematical_authority"] is not False:
        _fail("mathematical authority drift")
    parsed = production.parse_domain_assumption_result(raw)
    if production.domain_assumption_result_bytes(parsed) != raw:
        _fail("strict replay drift")
    return {
        "contexts": len(value["candidates"]),
        "facts": facts,
        "input_sha256": _sha(input_bytes),
        "result_bytes": len(raw),
        "result_sha256": _sha(raw),
        "unsupported_facts": unsupported,
    }


def _negative_checks(schema_validator: Any) -> int:
    count = 0
    for value in (None, "x != 0", bytearray(b"{}\n"), b"{}\n"):
        result = production.normalize_domain_assumptions(value)  # type: ignore[arg-type]
        if result.status == "normalized" or result.candidates or result.input_result_sha256 is not None:
            _fail(f"invalid input produced normalization: {type(value).__name__}")
        if schema_validator is not None:
            schema_validator.validate(json.loads(production.domain_assumption_result_bytes(result)))
        count += 1
    valid = production.normalize_domain_assumptions(_analysis(_fixture_problem()))
    raw = production.domain_assumption_result_bytes(valid)
    forged = json.loads(raw)
    forged["candidates"][0]["context"]["facts"][0]["supported"] = False
    try:
        production.parse_domain_assumption_result(_canonical(forged))
    except production.DomainAssumptionValidationError:
        count += 1
    else:
        _fail("forged fact passed strict replay")
    try:
        production.parse_domain_assumption_result(raw.rstrip(b"\n"))
    except production.DomainAssumptionValidationError:
        count += 1
    else:
        _fail("noncanonical result passed strict replay")
    failed_analysis = analyze_problem_readings(b"{}\n")
    failed = production.normalize_domain_assumptions(reading_analysis_result_bytes(failed_analysis))
    if failed.status != "invalid" or failed.candidates:
        _fail("failed upstream analysis did not fail closed")
    return count + 1


def _report() -> dict[str, object]:
    schema_validator = _identity_checks()
    fixture = _verify_result(schema_validator)
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "negative_controls": _negative_checks(schema_validator),
        "report_sha256": "",
        "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
        "schema": REPORT_SCHEMA,
        "schemas": {
            "context_sha256": CONTEXT_SCHEMA_SHA256,
            "fact_sha256": FACT_SCHEMA_SHA256,
            "result_sha256": RESULT_SCHEMA_SHA256,
            "rules_sha256": RULE_SCHEMA_SHA256,
        },
        "source": _source_closure(),
        "summary": {
            "contexts": fixture["contexts"],
            "facts": fixture["facts"],
            "mathematical_authority": False,
            "status": "passed",
            "unsupported_facts": fixture["unsupported_facts"],
        },
        "tests_sha256": _sha((ROOT / TEST_SOURCE).read_bytes()),
        "validator_sha256": _sha((ROOT / "tools/validate_domain_assumptions.py").read_bytes()),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"domain-assumptions: report updated: {target}")
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
        DomainAssumptionReportError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        ValidationError,
    ) as exc:
        print(f"domain-assumptions: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "domain-assumptions: PASS "
        f"(contexts={summary['contexts']}, facts={summary['facts']}, "
        f"unsupported={summary['unsupported_facts']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
