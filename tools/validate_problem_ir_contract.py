#!/usr/bin/env python3
"""Independently validate the accepted ProblemIR v1 schema and semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, NoReturn, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 core profile.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "MH-C-PROBLEM-IR-001"
EXPECTED_CONTRACT_SHA256 = "d705d82fcb6b7ac3b2f411f5a6d2cf01f80e4e8ebe71116ea8db9b91b639287b"
SCHEMA_PATH = Path("docs/contracts/schemas/problem-ir-v1.schema.json")
EXPECTED_SCHEMA_SHA256 = "dcf871f15ebbae06b0eca285a115f2545defc00cb0befc23e3cc574d8523df2c"
ROOT_FIELDS = {
    "schema",
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
    "readings",
    "ambiguity",
    "extensions",
}
REGISTRIES = (
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
    "readings",
)


class ProblemIRValidationError(RuntimeError):
    """A classified schema, identity, or semantic validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ProblemIRValidationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        _fail("canonical", "$", f"not canonical JSON: {exc}")
    return (rendered + "\n").encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return _sha(canonical_bytes(value))


def _pairs(path: Path):
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _fail("schema", str(path), f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    return reject_duplicates


def load_json(path: Path, *, require_canonical: bool = False) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs(path))
    except ProblemIRValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical ProblemIR JSON")
    return value, raw


def _resolve_ref(root_schema: dict[str, Any], reference: str, path: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        _fail("schema-document", path, f"non-local schema reference {reference!r}")
    value: Any = root_schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            _fail("schema-document", path, f"unresolved schema reference {reference!r}")
        value = value[token]
    if not isinstance(value, dict):
        _fail("schema-document", path, f"schema reference is not an object: {reference!r}")
    return value


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "null": value is None,
        "boolean": isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "string": isinstance(value, str),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(expected, False)


def _schema_validate(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    path: str = "$",
) -> None:
    if "$ref" in schema:
        _schema_validate(value, _resolve_ref(root_schema, schema["$ref"], path), root_schema, path)
        return
    if "oneOf" in schema:
        matches = 0
        for candidate in schema["oneOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except ProblemIRValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail("schema", path, f"must match exactly one tagged variant, matched {matches}")
        return
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except ProblemIRValidationError:
                continue
            return
        _fail("schema", path, "does not match any allowed variant")
    expected = schema.get("type")
    if expected is not None:
        allowed = [expected] if isinstance(expected, str) else expected
        if not isinstance(allowed, list) or not any(
            isinstance(item, str) and _type_matches(value, item) for item in allowed
        ):
            _fail("schema", path, f"expected type {allowed!r}")
    if "const" in schema and value != schema["const"]:
        _fail("schema", path, f"expected constant {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        _fail("schema", path, f"value is outside enum {schema['enum']!r}")
    if isinstance(value, str):
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            _fail("schema", path, f"does not match {schema['pattern']!r}")
        if len(value) < schema.get("minLength", 0):
            _fail("schema", path, "string is too short")
        if len(value) > schema.get("maxLength", sys.maxsize):
            _fail("schema", path, "string is too long")
    if isinstance(value, int) and not isinstance(value, bool):
        if value < schema.get("minimum", value):
            _fail("schema", path, "number is below minimum")
        if value > schema.get("maximum", value):
            _fail("schema", path, "number is above maximum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            _fail("schema", path, "array is too short")
        if len(value) > schema.get("maxItems", sys.maxsize):
            _fail("schema", path, "array is too long")
        if schema.get("uniqueItems"):
            identities = [canonical_bytes(item) for item in value]
            if len(identities) != len(set(identities)):
                _fail("schema", path, "array items must be unique")
        if "items" in schema:
            for index, item in enumerate(value):
                _schema_validate(item, schema["items"], root_schema, f"{path}[{index}]")
    if isinstance(value, dict):
        required = schema.get("required", [])
        missing = sorted(set(required) - set(value))
        if missing:
            _fail("schema", path, f"missing fields {missing}")
        properties = schema.get("properties", {})
        unknown = sorted(set(value) - set(properties))
        additional = schema.get("additionalProperties", True)
        if unknown and additional is False:
            _fail("schema", path, f"unknown fields {unknown}")
        for key, item in value.items():
            if key in properties:
                _schema_validate(item, properties[key], root_schema, f"{path}.{key}")
            elif isinstance(additional, dict):
                _schema_validate(item, additional, root_schema, f"{path}.{key}")
        if "propertyNames" in schema:
            for key in value:
                _schema_validate(key, schema["propertyNames"], root_schema, f"{path}.<key>")


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(key, f"{path}.<key>")
            yield from _walk_strings(item, f"{path}.{key}")


def _index_registries(value: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    indexes: dict[str, dict[str, Any]] = {}
    global_owner: dict[str, str] = {}
    total = 0
    for registry in REGISTRIES:
        entries = value[registry]
        ids = [entry["id"] for entry in entries]
        if ids != sorted(ids):
            _fail("canonical", f"$.{registry}", "registry must be sorted by id")
        if len(ids) != len(set(ids)):
            _fail("identity", f"$.{registry}", "duplicate entity id")
        for entity_id in ids:
            if entity_id in global_owner:
                _fail(
                    "identity",
                    f"$.{registry}",
                    f"id {entity_id!r} already belongs to {global_owner[entity_id]}",
                )
            global_owner[entity_id] = registry
        indexes[registry] = {entry["id"]: entry for entry in entries}
        total += len(entries)
    if total > 100000:
        _fail("budget", "$", "combined entity count exceeds 100000")
    return indexes, global_owner


def _require_ref(index: dict[str, Any], reference: str | None, path: str) -> None:
    if reference is not None and reference not in index:
        _fail("reference", path, f"unknown reference {reference!r}")


def _require_refs(index: dict[str, Any], references: list[str], path: str) -> None:
    for position, reference in enumerate(references):
        _require_ref(index, reference, f"{path}[{position}]")


def _sorted_unique(references: list[str], path: str) -> None:
    if references != sorted(set(references)):
        _fail("canonical", path, "set-valued references must be sorted and unique")


def _references(value: dict[str, Any], indexes: dict[str, dict[str, Any]], owners: dict[str, str]) -> None:
    sources = indexes["source_documents"]
    spans = indexes["source_spans"]
    domains = indexes["domains"]
    variables = indexes["variables"]
    expressions = indexes["expressions"]
    relations = indexes["relations"]
    statements = indexes["statements"]
    definitions = indexes["definitions"]
    assumptions = indexes["assumptions"]
    goals = indexes["goals"]
    readings = indexes["readings"]

    for registry in REGISTRIES[2:]:
        for entity in value[registry]:
            span_ids = entity.get("span_ids", [])
            _sorted_unique(span_ids, f"$.{registry}.{entity['id']}.span_ids")
            _require_refs(spans, span_ids, f"$.{registry}.{entity['id']}.span_ids")
    for span in value["source_spans"]:
        source = sources.get(span["source_id"])
        if source is None:
            _fail("reference", f"$.source_spans.{span['id']}.source_id", "unknown source")
        if span["start_byte"] > span["end_byte"] or span["end_byte"] > source["byte_length"]:
            _fail("span", f"$.source_spans.{span['id']}", "span lies outside source bytes")
    for domain in value["domains"]:
        path = f"$.domains.{domain['id']}"
        kind = domain["kind"]
        if kind == "finite":
            _require_ref(domains, domain["element_domain_id"], path + ".element_domain_id")
            _require_refs(expressions, domain["element_expr_ids"], path + ".element_expr_ids")
            if domain["cardinality"] != len(domain["element_expr_ids"]):
                _fail("domain", path, "finite cardinality must equal the element count")
            if any(
                expressions[item]["domain_id"] != domain["element_domain_id"]
                for item in domain["element_expr_ids"]
            ):
                _fail("domain", path, "finite elements must use the declared element domain")
        elif kind == "interval":
            _require_ref(expressions, domain["lower_expr_id"], path + ".lower_expr_id")
            _require_ref(expressions, domain["upper_expr_id"], path + ".upper_expr_id")
            if domain["lower_expr_id"] is None and domain["upper_expr_id"] is None:
                _fail("domain", path, "an unbounded interval must use the builtin domain")
            if domain["lower_expr_id"] is None and domain["lower_closed"]:
                _fail("domain", path, "an absent lower bound cannot be closed")
            if domain["upper_expr_id"] is None and domain["upper_closed"]:
                _fail("domain", path, "an absent upper bound cannot be closed")
            for bound in (domain["lower_expr_id"], domain["upper_expr_id"]):
                if bound is None:
                    continue
                bound_domain = domains[expressions[bound]["domain_id"]]
                if bound_domain.get("kind") != "builtin" or bound_domain.get("name") != domain["base"]:
                    _fail("domain", path, "interval bounds must use its builtin base domain")
        elif kind == "modular":
            _require_ref(expressions, domain["modulus_expr_id"], path + ".modulus_expr_id")
            modulus = expressions[domain["modulus_expr_id"]]
            modulus_domain = domains[modulus["domain_id"]]
            if modulus_domain.get("kind") != "builtin" or modulus_domain.get("name") not in {
                "natural",
                "integer",
            }:
                _fail("domain", path, "modulus must have a natural or integer domain")
            if (
                modulus["kind"] == "literal"
                and modulus["literal_type"] == "integer"
                and int(modulus["value"]) <= 1
            ):
                _fail("domain", path, "literal modulus must exceed one")
        elif kind == "collection":
            _require_ref(domains, domain["element_domain_id"], path + ".element_domain_id")
        elif kind == "product":
            _require_refs(domains, domain["factor_domain_ids"], path + ".factor_domain_ids")
        elif kind == "function":
            _require_refs(domains, domain["parameter_domain_ids"], path + ".parameter_domain_ids")
            _require_ref(domains, domain["result_domain_id"], path + ".result_domain_id")
        elif kind == "structure":
            _require_refs(domains, domain["parameter_domain_ids"], path + ".parameter_domain_ids")
            _require_refs(expressions, domain["parameter_expr_ids"], path + ".parameter_expr_ids")
    for variable in value["variables"]:
        _require_ref(domains, variable["domain_id"], f"$.variables.{variable['id']}.domain_id")
    for expression in value["expressions"]:
        path = f"$.expressions.{expression['id']}"
        _require_ref(domains, expression["domain_id"], path + ".domain_id")
        kind = expression["kind"]
        if kind == "variable":
            _require_ref(variables, expression["variable_id"], path + ".variable_id")
            if expression["domain_id"] != variables[expression["variable_id"]]["domain_id"]:
                _fail("expression", path, "variable expression domain drift")
        elif kind == "apply":
            _require_refs(expressions, expression["argument_expr_ids"], path + ".argument_expr_ids")
            if not isinstance(expression["attributes"], dict):
                _fail("expression", path + ".attributes", "operator attributes must be an object")
        elif kind in {"tuple", "collection"}:
            _require_refs(expressions, expression["element_expr_ids"], path + ".element_expr_ids")
            expression_domain = domains[expression["domain_id"]]
            if kind == "tuple":
                if expression_domain.get("kind") != "product" or [
                    expressions[item]["domain_id"] for item in expression["element_expr_ids"]
                ] != expression_domain.get("factor_domain_ids"):
                    _fail("expression", path, "tuple elements do not match its product domain")
            elif expression_domain.get("kind") != "collection" or any(
                expressions[item]["domain_id"] != expression_domain.get("element_domain_id")
                for item in expression["element_expr_ids"]
            ):
                _fail("expression", path, "collection elements do not match its domain")
        elif kind == "conditional":
            _require_ref(statements, expression["condition_statement_id"], path + ".condition_statement_id")
            _require_ref(expressions, expression["then_expr_id"], path + ".then_expr_id")
            _require_ref(expressions, expression["else_expr_id"], path + ".else_expr_id")
            if any(
                expressions[item]["domain_id"] != expression["domain_id"]
                for item in (expression["then_expr_id"], expression["else_expr_id"])
            ):
                _fail("expression", path, "conditional branch domain drift")
        elif kind == "literal":
            _literal(expression, domains, path)
    for relation in value["relations"]:
        path = f"$.relations.{relation['id']}"
        operands = relation["operand_expr_ids"]
        _require_refs(expressions, operands, path + ".operand_expr_ids")
        expected = 3 if relation["kind"] == "congruent" else 2
        if relation["kind"] != "predicate" and len(operands) != expected:
            _fail("relation", path, f"{relation['kind']} requires exactly {expected} operands")
        operand_domains = [domains[expressions[item]["domain_id"]] for item in operands]
        operand_domain_ids = [expressions[item]["domain_id"] for item in operands]
        if relation["kind"] in {"equal", "not_equal"} and len(set(operand_domain_ids)) != 1:
            _fail("relation", path, "equality operands must have one exact domain")
        if relation["kind"] in {"less", "less_equal", "greater", "greater_equal"} and any(
            domain.get("kind") != "builtin"
            or domain.get("name") not in {"natural", "integer", "rational", "real"}
            for domain in operand_domains
        ):
            _fail("relation", path, "ordered comparison requires ordered numeric domains")
        if relation["kind"] in {"divides", "congruent"} and any(
            domain.get("kind") != "builtin" or domain.get("name") not in {"natural", "integer"}
            for domain in operand_domains
        ):
            _fail("relation", path, "arithmetic relation requires integral operands")
        if relation["kind"] in {"member", "not_member"}:
            container = operand_domains[1]
            if (
                container.get("kind") != "collection"
                or operand_domain_ids[0] != container.get("element_domain_id")
            ):
                _fail("relation", path, "membership operands do not match a collection domain")
    for statement in value["statements"]:
        path = f"$.statements.{statement['id']}"
        if statement["kind"] == "relation":
            _require_ref(relations, statement["relation_id"], path + ".relation_id")
        elif statement["kind"] == "logical":
            operands = statement["operand_statement_ids"]
            _require_refs(statements, operands, path + ".operand_statement_ids")
            expected = {"not": 1, "implies": 2, "iff": 2}.get(statement["operator"])
            if expected is not None and len(operands) != expected:
                _fail("statement", path, f"{statement['operator']} requires {expected} operands")
            if statement["operator"] in {"and", "or"} and len(operands) < 2:
                _fail("statement", path, f"{statement['operator']} requires at least 2 operands")
        elif statement["kind"] == "quantified":
            _require_refs(variables, statement["variable_ids"], path + ".variable_ids")
            _require_ref(statements, statement["body_statement_id"], path + ".body_statement_id")
    for definition in value["definitions"]:
        path = f"$.definitions.{definition['id']}"
        _require_refs(variables, definition["parameter_variable_ids"], path + ".parameter_variable_ids")
        _require_ref(domains, definition["result_domain_id"], path + ".result_domain_id")
        body = definition["body"]
        if body["kind"] == "expression":
            _require_ref(expressions, body["expression_id"], path + ".body.expression_id")
            if (
                definition["result_domain_id"] is None
                or expressions[body["expression_id"]]["domain_id"]
                != definition["result_domain_id"]
            ):
                _fail("definition", path, "expression definition result domain drift")
        else:
            _require_ref(statements, body["statement_id"], path + ".body.statement_id")
            if definition["result_domain_id"] is not None:
                _fail("definition", path, "statement definition cannot declare a result domain")
    for assumption in value["assumptions"]:
        _require_ref(
            statements,
            assumption["statement_id"],
            f"$.assumptions.{assumption['id']}.statement_id",
        )
    for goal in value["goals"]:
        _require_ref(statements, goal["statement_id"], f"$.goals.{goal['id']}.statement_id")
    for reading in value["readings"]:
        path = f"$.readings.{reading['id']}"
        _sorted_unique(reading["definition_ids"], path + ".definition_ids")
        _sorted_unique(reading["assumption_ids"], path + ".assumption_ids")
        _require_refs(definitions, reading["definition_ids"], path + ".definition_ids")
        _require_refs(assumptions, reading["assumption_ids"], path + ".assumption_ids")
        _require_refs(goals, reading["goal_ids"], path + ".goal_ids")
        _require_ref(readings, reading["difference_from"], path + ".difference_from")
        if reading["difference_from"] == reading["id"]:
            _fail("ambiguity", path, "reading cannot differ from itself")
        if reading["difference_from"] is None and reading["differences"]:
            _fail("ambiguity", path, "base reading cannot declare relative differences")
        if reading["difference_from"] is not None and not reading["differences"]:
            _fail("ambiguity", path, "alternative reading must explain its differences")
        for number, difference in enumerate(reading["differences"]):
            _sorted_unique(difference["affected_ids"], f"{path}.differences[{number}].affected_ids")
            for affected in difference["affected_ids"]:
                if affected not in owners:
                    _fail("reference", path, f"difference names unknown entity {affected!r}")
            _sorted_unique(difference["span_ids"], f"{path}.differences[{number}].span_ids")
            _require_refs(spans, difference["span_ids"], f"{path}.differences[{number}].span_ids")


def _literal(expression: dict[str, Any], domains: dict[str, dict[str, Any]], path: str) -> None:
    kind = expression["literal_type"]
    value = expression["value"]
    domain = domains[expression["domain_id"]]
    builtin = domain.get("name") if domain.get("kind") == "builtin" else None
    compatible = {
        "boolean": {"boolean"},
        "integer": {"natural", "integer", "rational", "real", "complex"},
        "rational": {"rational", "real", "complex"},
        "string": set(),
    }
    if kind != "string" and builtin not in compatible[kind]:
        _fail("literal", path, "literal type is incompatible with its domain")
    if kind == "string" and domain.get("kind") != "structure":
        _fail("literal", path, "string literal requires a named structure domain")
    if kind == "boolean" and value not in {"true", "false"}:
        _fail("literal", path, "boolean literal must be true or false")
    if kind == "integer" and re.fullmatch(r"0|-?[1-9][0-9]*", value) is None:
        _fail("literal", path, "integer literal is not canonical")
    if kind == "integer" and builtin == "natural" and int(value) < 0:
        _fail("literal", path, "natural literal cannot be negative")
    if kind == "rational":
        match = re.fullmatch(r"(-?)(0|[1-9][0-9]*)/([1-9][0-9]*)", value)
        if match is None:
            _fail("literal", path, "rational literal is not canonical")
        numerator = int(("-" if match.group(1) else "") + match.group(2))
        denominator = int(match.group(3))
        if numerator == 0 or denominator == 1 or math.gcd(abs(numerator), denominator) != 1:
            _fail("literal", path, "rational literal must be non-integral and reduced")


def _acyclic(value: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> None:
    graph: dict[str, list[str]] = {}
    for domain in value["domains"]:
        node = "domain:" + domain["id"]
        kind = domain["kind"]
        dependencies: list[str] = []
        if kind == "finite":
            dependencies = ["domain:" + domain["element_domain_id"]]
            dependencies.extend("expr:" + item for item in domain["element_expr_ids"])
        elif kind == "interval":
            dependencies = [
                "expr:" + item
                for item in (domain["lower_expr_id"], domain["upper_expr_id"])
                if item is not None
            ]
        elif kind == "modular":
            dependencies = ["expr:" + domain["modulus_expr_id"]]
        elif kind == "collection":
            dependencies = ["domain:" + domain["element_domain_id"]]
        elif kind == "product":
            dependencies = ["domain:" + item for item in domain["factor_domain_ids"]]
        elif kind == "function":
            dependencies = ["domain:" + item for item in domain["parameter_domain_ids"]]
            dependencies.append("domain:" + domain["result_domain_id"])
        elif kind == "structure":
            dependencies = ["domain:" + item for item in domain["parameter_domain_ids"]]
            dependencies.extend("expr:" + item for item in domain["parameter_expr_ids"])
        graph[node] = dependencies
    for expression in value["expressions"]:
        node = "expr:" + expression["id"]
        dependencies = ["domain:" + expression["domain_id"]]
        if expression["kind"] == "apply":
            dependencies.extend("expr:" + item for item in expression["argument_expr_ids"])
        elif expression["kind"] in {"tuple", "collection"}:
            dependencies.extend("expr:" + item for item in expression["element_expr_ids"])
        elif expression["kind"] == "conditional":
            dependencies.extend(
                [
                    "stmt:" + expression["condition_statement_id"],
                    "expr:" + expression["then_expr_id"],
                    "expr:" + expression["else_expr_id"],
                ]
            )
        graph[node] = dependencies
    for relation in value["relations"]:
        graph["rel:" + relation["id"]] = [
            "expr:" + item for item in relation["operand_expr_ids"]
        ]
    for statement in value["statements"]:
        node = "stmt:" + statement["id"]
        if statement["kind"] == "relation":
            graph[node] = ["rel:" + statement["relation_id"]]
        elif statement["kind"] == "logical":
            graph[node] = ["stmt:" + item for item in statement["operand_statement_ids"]]
        elif statement["kind"] == "quantified":
            graph[node] = ["stmt:" + statement["body_statement_id"]]
        else:
            graph[node] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            _fail("cycle", "$", f"cyclic ProblemIR graph at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _scope(value: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> None:
    variables = indexes["variables"]
    expressions = indexes["expressions"]
    relations = indexes["relations"]
    statements = indexes["statements"]
    binder_owner: dict[str, str] = {}
    for statement in value["statements"]:
        if statement["kind"] != "quantified":
            continue
        for variable_id in statement["variable_ids"]:
            variable = variables[variable_id]
            if variable["role"] != "bound":
                _fail("scope", f"$.statements.{statement['id']}", "binder variable is not bound")
            if variable_id in binder_owner:
                _fail("scope", f"$.statements.{statement['id']}", "bound variable has two owners")
            binder_owner[variable_id] = statement["id"]
    parameter_owner: dict[str, str] = {}
    for definition in value["definitions"]:
        for variable_id in definition["parameter_variable_ids"]:
            variable = variables[variable_id]
            if variable["role"] != "parameter":
                _fail("scope", f"$.definitions.{definition['id']}", "parameter role mismatch")
            if variable_id in parameter_owner:
                _fail("scope", f"$.definitions.{definition['id']}", "parameter has two owners")
            parameter_owner[variable_id] = definition["id"]
    for variable in value["variables"]:
        if variable["role"] == "bound" and variable["id"] not in binder_owner:
            _fail("scope", f"$.variables.{variable['id']}", "bound variable has no binder")
        if variable["role"] == "parameter" and variable["id"] not in parameter_owner:
            _fail("scope", f"$.variables.{variable['id']}", "parameter has no definition")

    def expression_scope(expression_id: str, allowed: frozenset[str], trail: frozenset[str]) -> None:
        if expression_id in trail:
            return
        expression = expressions[expression_id]
        kind = expression["kind"]
        if kind == "variable":
            variable = variables[expression["variable_id"]]
            if variable["role"] in {"bound", "parameter"} and variable["id"] not in allowed:
                _fail("scope", f"$.expressions.{expression_id}", "variable escapes its scope")
        elif kind == "apply":
            for child in expression["argument_expr_ids"]:
                expression_scope(child, allowed, trail | {expression_id})
        elif kind in {"tuple", "collection"}:
            for child in expression["element_expr_ids"]:
                expression_scope(child, allowed, trail | {expression_id})
        elif kind == "conditional":
            statement_scope(expression["condition_statement_id"], allowed, frozenset())
            expression_scope(expression["then_expr_id"], allowed, trail | {expression_id})
            expression_scope(expression["else_expr_id"], allowed, trail | {expression_id})

    def statement_scope(statement_id: str, allowed: frozenset[str], trail: frozenset[str]) -> None:
        if statement_id in trail:
            return
        statement = statements[statement_id]
        kind = statement["kind"]
        if kind == "relation":
            for expression_id in relations[statement["relation_id"]]["operand_expr_ids"]:
                expression_scope(expression_id, allowed, frozenset())
        elif kind == "logical":
            for child in statement["operand_statement_ids"]:
                statement_scope(child, allowed, trail | {statement_id})
        elif kind == "quantified":
            statement_scope(
                statement["body_statement_id"],
                allowed | frozenset(statement["variable_ids"]),
                trail | {statement_id},
            )

    for assumption in value["assumptions"]:
        statement_scope(assumption["statement_id"], frozenset(), frozenset())
    for goal in value["goals"]:
        statement_scope(goal["statement_id"], frozenset(), frozenset())
    for definition in value["definitions"]:
        allowed = frozenset(definition["parameter_variable_ids"])
        if definition["body"]["kind"] == "expression":
            expression_scope(definition["body"]["expression_id"], allowed, frozenset())
        else:
            statement_scope(definition["body"]["statement_id"], allowed, frozenset())


def _ambiguity(value: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> None:
    readings = indexes["readings"]
    ambiguity = value["ambiguity"]
    candidates = ambiguity["candidate_reading_ids"]
    _sorted_unique(candidates, "$.ambiguity.candidate_reading_ids")
    if candidates != sorted(readings):
        _fail("ambiguity", "$.ambiguity", "candidate list must name every reading exactly once")
    status = ambiguity["status"]
    selected = ambiguity["selected_reading_id"]
    choice = ambiguity["required_choice"]
    if status == "unambiguous":
        if len(candidates) != 1 or selected != candidates[0] or choice is not None:
            _fail("ambiguity", "$.ambiguity", "unambiguous state must select its sole reading")
        reading = readings[candidates[0]]
        if reading["difference_from"] is not None or reading["differences"]:
            _fail("ambiguity", "$.ambiguity", "unambiguous reading cannot carry alternatives")
    elif status == "unresolved":
        if len(candidates) < 2 or selected is not None or not isinstance(choice, str) or not choice:
            _fail("ambiguity", "$.ambiguity", "unresolved ambiguity needs alternatives and a choice")
    elif len(candidates) < 2 or selected not in readings or choice is not None:
        _fail("ambiguity", "$.ambiguity", "resolved ambiguity must select one candidate")
    if len(candidates) > 1:
        bases = [reading for reading in value["readings"] if reading["difference_from"] is None]
        alternatives = [reading for reading in value["readings"] if reading["difference_from"] is not None]
        if len(bases) != 1 or not alternatives:
            _fail("ambiguity", "$.readings", "ambiguous IR needs one base and explained alternatives")


def validate_problem_ir(value: dict[str, Any], schema: dict[str, Any]) -> None:
    _schema_validate(value, schema, schema)
    if set(value) != ROOT_FIELDS:
        _fail("schema", "$", "root field set drift")
    for path, text in _walk_strings(value):
        if unicodedata.normalize("NFC", text) != text:
            _fail("canonical", path, "string is not Unicode NFC")
        if "\x00" in text:
            _fail("canonical", path, "NUL is forbidden")
    indexes, owners = _index_registries(value)
    _references(value, indexes, owners)
    _acyclic(value, indexes)
    _scope(value, indexes)
    _ambiguity(value, indexes)
    canonical_bytes(value)


def minimal_problem_ir() -> dict[str, Any]:
    return {
        "schema": "mathhead.problem-ir.v1",
        "source_documents": [],
        "source_spans": [],
        "domains": [
            {"id": "domain_integer", "kind": "builtin", "name": "integer", "span_ids": []}
        ],
        "variables": [
            {
                "id": "variable_x",
                "name": "x",
                "domain_id": "domain_integer",
                "role": "bound",
                "span_ids": [],
            }
        ],
        "expressions": [
            {
                "id": "expression_x",
                "kind": "variable",
                "domain_id": "domain_integer",
                "variable_id": "variable_x",
                "span_ids": [],
            }
        ],
        "relations": [
            {
                "id": "relation_reflexive",
                "kind": "equal",
                "operand_expr_ids": ["expression_x", "expression_x"],
                "span_ids": [],
            }
        ],
        "statements": [
            {
                "id": "statement_body",
                "kind": "relation",
                "relation_id": "relation_reflexive",
                "span_ids": [],
            },
            {
                "id": "statement_forall",
                "kind": "quantified",
                "quantifier": "forall",
                "variable_ids": ["variable_x"],
                "body_statement_id": "statement_body",
                "span_ids": [],
            },
        ],
        "definitions": [],
        "assumptions": [],
        "goals": [
            {
                "id": "goal_reflexive",
                "statement_id": "statement_forall",
                "mode": "prove",
                "span_ids": [],
            }
        ],
        "readings": [
            {
                "id": "reading_only",
                "label": "For every integer x, x equals itself.",
                "definition_ids": [],
                "assumption_ids": [],
                "goal_ids": ["goal_reflexive"],
                "difference_from": None,
                "differences": [],
                "span_ids": [],
            }
        ],
        "ambiguity": {
            "status": "unambiguous",
            "candidate_reading_ids": ["reading_only"],
            "selected_reading_id": "reading_only",
            "required_choice": None,
        },
        "extensions": {},
    }


def _repository_contract(root: Path, schema_raw: bytes) -> None:
    if _sha(schema_raw) != EXPECTED_SCHEMA_SHA256:
        _fail("identity", str(SCHEMA_PATH), "normative schema hash drift")
    if not re.fullmatch(r"[0-9a-f]{64}", EXPECTED_CONTRACT_SHA256):
        _fail("identity", "validator", "accepted contract hash is not configured")
    accepted = root / f"docs/contracts/{CONTRACT_ID}.json"
    proposed = root / f"docs/contracts/proposed/{CONTRACT_ID}.json"
    try:
        accepted_raw = accepted.read_bytes()
        proposed_raw = proposed.read_bytes()
    except OSError as exc:
        _fail("identity", "contract", f"accepted/proposed contract missing: {exc}")
    if (
        accepted_raw != proposed_raw
        or _sha(accepted_raw) != EXPECTED_CONTRACT_SHA256
        or accepted_raw != canonical_bytes(json.loads(accepted_raw))
    ):
        _fail("identity", "contract", "accepted/proposed contract identity drift")
    manifest = tomllib.loads((root / "docs/contracts/manifest.toml").read_text(encoding="utf-8"))
    records = [record for record in manifest.get("contracts", []) if record.get("id") == CONTRACT_ID]
    expected = {
        "id": CONTRACT_ID,
        "path": f"docs/contracts/{CONTRACT_ID}.json",
        "sha256": EXPECTED_CONTRACT_SHA256,
        "state": "accepted",
    }
    if records != [expected]:
        _fail("identity", "manifest", "accepted contract manifest binding drift")
    contract = json.loads(accepted_raw)
    schema_clause = f"{SCHEMA_PATH.as_posix()}={EXPECTED_SCHEMA_SHA256}"
    if not any(schema_clause in clause for clause in contract.get("invariants", [])):
        _fail("identity", "contract.invariants", "normative schema identity is not bound")


def validate_repository(root: Path) -> None:
    schema, schema_raw = load_json(root / SCHEMA_PATH)
    _repository_contract(root, schema_raw)
    minimal = minimal_problem_ir()
    validate_problem_ir(minimal, schema)
    if canonical_sha256(minimal) != canonical_sha256(json.loads(canonical_bytes(minimal))):
        _fail("canonical", "$", "canonical round trip changed identity")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--instance", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        schema, schema_raw = load_json(root / SCHEMA_PATH)
        _repository_contract(root, schema_raw)
        if args.instance is None:
            value = minimal_problem_ir()
        else:
            path = args.instance if args.instance.is_absolute() else root / args.instance
            value, _raw = load_json(path, require_canonical=True)
        validate_problem_ir(value, schema)
    except (ProblemIRValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"problem-ir-contract: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "problem-ir-contract: PASS "
        f"(schema={EXPECTED_SCHEMA_SHA256[:12]}, identity={canonical_sha256(value)[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
