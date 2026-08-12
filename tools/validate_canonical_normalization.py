#!/usr/bin/env python3
"""Independently validate the MH-044 canonical-normalization boundary."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, Sequence

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
except ModuleNotFoundError:  # Governed dependency-minimal status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    Registry = Resource = None  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import canonical_normalization as production  # noqa: E402
from mathhead.domain_assumptions import (  # noqa: E402
    domain_assumption_result_bytes,
    normalize_domain_assumptions,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from mathhead.proof_obligations import (  # noqa: E402
    decompose_proof_obligations,
    proof_obligation_result_bytes,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


CONTRACT_ID = "MH-C-CANONICAL-NORMALIZATION-001"
CONTRACT_SHA256 = "ad2a58afc455fed01310b125f3ae7e0597642e849fd10b86149c31a13b9249c8"
RULE_CATALOGUE_SHA256 = "6f73efb9455198422a193424411dcad09328c1ae2c38b3997840b97b04f79eb4"
SOURCE = Path("src/mathhead/canonical_normalization.py")
DEFAULT_REPORT = Path("docs/normalization/reports/canonical-normalization-v1.json")
REPORT_SCHEMA = "mathhead.canonical-normalization-validation-report.v1"
ARTIFACTS = {
    Path("docs/contracts/schemas/canonical-normal-form-v1.schema.json"): "d6dc45e60c9d494a70859631403ee7cf6e454f71d7b78dbffb528ae7550d5e9c",
    Path("docs/contracts/schemas/canonical-occurrence-trace-v1.schema.json"): "01622e476a2fb3b72a9306cd656db6e7525604b1c6f4e680395e9b12cde74fec",
    Path("docs/contracts/schemas/canonical-context-v1.schema.json"): "e43588f34e29eb980efcc2f42600036803d7fb17dad8039aa18d7b1e6f6bf860",
    Path("docs/contracts/schemas/canonical-obligation-v1.schema.json"): "c6fade940f24fb23f4d16dcb324d3aff5bb35a923748d30b2f93fb302b436d58",
    Path("docs/contracts/schemas/canonical-normalization-rules-v1.schema.json"): "845843f01d2b7dfcb0530f028e53b161d283489cc10292c3376af39809609ff7",
    Path("docs/contracts/schemas/canonical-normalization-result-v1.schema.json"): "37ef5d35dcba90f32b53559719a08ebca12d8ffa9a0075ea99f6ac18efe18952",
    Path("docs/normalization/canonical-normalization-rules-v1.json"): RULE_CATALOGUE_SHA256,
}
REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals", "readings",
)
ALLOWED_IMPORT_ROOTS = {
    "__future__", "collections", "dataclasses", "hashlib", "json", "mathhead",
    "re", "typing", "unicodedata",
}
FORBIDDEN_CALLS = {
    "Path", "eval", "exec", "getenv", "import_module", "open", "perf_counter",
    "run", "system", "time",
}
COMMUTATIVE_RULES = {
    "mh.canonical.commutative.logical-and",
    "mh.canonical.commutative.logical-or",
    "mh.canonical.commutative.logical-iff",
    "mh.canonical.commutative.relation-equal",
    "mh.canonical.commutative.relation-not-equal",
}


class CanonicalNormalizationReportError(RuntimeError):
    """A contract, source, semantic, trace, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise CanonicalNormalizationReportError(detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sort(problem: dict[str, Any]) -> None:
    for registry in REGISTRIES:
        problem[registry].sort(key=lambda item: item["id"])


def _proof_bytes(problem: dict[str, Any]) -> bytes:
    _sort(problem)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
    if intake.status != "accepted":
        _fail(f"fixture intake failed: {intake.reason_code}: {intake.diagnostics}")
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    if readings.status != "analyzed":
        _fail(f"fixture reading analysis failed: {readings.reason_code}")
    domain = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    if domain.status != "normalized":
        _fail(f"fixture domain normalization failed: {domain.reason_code}")
    proof = decompose_proof_obligations(domain_assumption_result_bytes(domain))
    if proof.status != "decomposed":
        _fail(f"fixture decomposition failed: {proof.reason_code}")
    return proof_obligation_result_bytes(proof)


def _identity_checks() -> dict[str, object]:
    expected = {
        **ARTIFACTS,
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
    if (
        production.CONTRACT_SHA256 != CONTRACT_SHA256
        or production.RULE_CATALOGUE_SHA256 != RULE_CATALOGUE_SHA256
    ):
        _fail("production contract or catalogue binding drift")

    all_schemas = []
    for path in sorted((ROOT / "docs/contracts/schemas").glob("*.schema.json")):
        schema = json.loads(path.read_bytes())
        if "$id" in schema:
            all_schemas.append(schema)
    selected_names = {
        path.name for path in ARTIFACTS if path.name.endswith(".schema.json")
    }
    selected = {
        schema["$id"].rsplit("/", 1)[-1]: schema
        for schema in all_schemas
        if schema["$id"].rsplit("/", 1)[-1] in selected_names
    }
    if set(selected) != selected_names:
        _fail("canonical-normalization schema identifier drift")
    for schema in selected.values():
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail("closed Draft 2020-12 schema root drift")
    catalogue = json.loads(
        (ROOT / "docs/normalization/canonical-normalization-rules-v1.json").read_bytes()
    )
    rule_ids = [item["rule_id"] for item in catalogue["rules"]]
    if len(rule_ids) != len(set(rule_ids)) or set(rule_ids) - {
        item["rule_id"] for item in catalogue["rules"]
    }:
        _fail("catalogue rule uniqueness drift")
    actual_commutative = {
        item["rule_id"] for item in catalogue["rules"]
        if item["rule_kind"] == "commutative"
    }
    if actual_commutative != COMMUTATIVE_RULES:
        _fail("exact commutative allowlist drift")
    if any(item["mathematical_authority"] is not False for item in catalogue["rules"]):
        _fail("catalogue mathematical authority drift")

    validators: dict[str, Any] = {}
    if Draft202012Validator is not None and Registry is not None and Resource is not None:
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in all_schemas
        )
        validators = {
            name: Draft202012Validator(schema, registry=registry)
            for name, schema in selected.items()
        }
        for validator in validators.values():
            validator.check_schema(validator.schema)
        validators["canonical-normalization-rules-v1.schema.json"].validate(catalogue)
    return {
        "rule_count": len(rule_ids),
        "schema_count": len(selected),
        "validators": validators,
    }


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
    problem["statements"] = [problem["statements"][0]]
    problem["goals"][0]["statement_id"] = "statement_goal"
    problem["variables"].extend([
        {
            "id": "variable_y", "name": "y", "domain_id": "domain_integer",
            "role": "free", "span_ids": [],
        },
        {
            "id": "variable_q", "name": "q", "domain_id": "domain_integer",
            "role": "bound", "span_ids": [],
        },
        {
            "id": "variable_p", "name": "p", "domain_id": "domain_integer",
            "role": "parameter", "span_ids": [],
        },
    ])
    problem["expressions"].extend([
        {
            "id": "expression_y", "kind": "variable", "variable_id": "variable_y",
            "domain_id": "domain_integer", "span_ids": [],
        },
        {
            "id": "expression_q", "kind": "variable", "variable_id": "variable_q",
            "domain_id": "domain_integer", "span_ids": [],
        },
        {
            "id": "expression_p", "kind": "variable", "variable_id": "variable_p",
            "domain_id": "domain_integer", "span_ids": [],
        },
        {
            "id": "expression_apply", "kind": "apply", "domain_id": "domain_integer",
            "operator": "org.mathhead.fixture.ordered", "argument_expr_ids": [
                "expression_x", "expression_y",
            ], "attributes": {}, "span_ids": [],
        },
    ])
    problem["relations"].extend([
        {
            "id": "relation_equal", "kind": "equal",
            "operand_expr_ids": ["expression_y", "expression_x"], "span_ids": [],
        },
        {
            "id": "relation_less", "kind": "less",
            "operand_expr_ids": ["expression_x", "expression_y"], "span_ids": [],
        },
        {
            "id": "relation_quantified", "kind": "equal",
            "operand_expr_ids": ["expression_q", "expression_q"], "span_ids": [],
        },
        {
            "id": "relation_apply", "kind": "equal",
            "operand_expr_ids": ["expression_apply", "expression_apply"], "span_ids": [],
        },
    ])
    problem["statements"].extend([
        {
            "id": "statement_equal", "kind": "relation",
            "relation_id": "relation_equal", "span_ids": [],
        },
        {
            "id": "statement_less", "kind": "relation",
            "relation_id": "relation_less", "span_ids": [],
        },
        {
            "id": "statement_quantified_body", "kind": "relation",
            "relation_id": "relation_quantified", "span_ids": [],
        },
        {
            "id": "statement_quantified", "kind": "quantified", "quantifier": "forall",
            "variable_ids": ["variable_q"],
            "body_statement_id": "statement_quantified_body", "span_ids": [],
        },
        {
            "id": "statement_apply", "kind": "relation",
            "relation_id": "relation_apply", "span_ids": [],
        },
        {
            "id": "statement_goal", "kind": "logical", "operator": "and",
            "operand_statement_ids": [
                "statement_less", "statement_equal", "statement_quantified",
                "statement_apply",
            ], "span_ids": [],
        },
        {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
    ])
    problem["definitions"].append({
        "id": "definition_identity", "name": "identity",
        "parameter_variable_ids": ["variable_p"], "result_domain_id": "domain_integer",
        "body": {"kind": "expression", "expression_id": "expression_p"},
        "recursive": False, "span_ids": [],
    })
    problem["assumptions"].extend([
        {
            "id": "assumption_true", "statement_id": "statement_true",
            "role": "given", "span_ids": [],
        },
        {
            "id": "assumption_false", "statement_id": "statement_false",
            "role": "side_condition", "span_ids": [],
        },
    ])
    reading = problem["readings"][0]
    reading["definition_ids"] = ["definition_identity"]
    reading["assumption_ids"] = ["assumption_false", "assumption_true"]
    reading["goal_ids"] = ["goal_reflexive"]
    return problem


def _index_projection(raw_proof: dict[str, Any], reading_id: str) -> dict[str, dict[str, Any]]:
    domain = raw_proof["domain_assumption_result"]
    readings = domain["readings_result"]
    wrapper = next(item for item in readings["candidates"] if item["reading_id"] == reading_id)
    return {
        registry: {item["id"]: item for item in wrapper["projection"]["entities"][registry]}
        for registry in (
            "domains", "variables", "expressions", "relations", "statements",
            "definitions", "assumptions", "goals",
        )
    }


def _independent_semantics(
    raw_proof: dict[str, Any], candidate: dict[str, Any],
) -> dict[tuple[str, str], set[bytes]]:
    indexes = _index_projection(raw_proof, candidate["reading_id"])
    cache: dict[tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]], Any] = {}

    def domain(domain_id: str, stack: tuple[tuple[str, tuple[str, ...]], ...]) -> Any:
        key = ("domains", domain_id, stack)
        if key in cache:
            return cache[key]
        record = indexes["domains"][domain_id]
        kind = record["kind"]
        if kind == "builtin":
            value = {"kind": kind, "name": record["name"]}
        elif kind == "finite":
            value = {
                "kind": kind, "element_domain": domain(record["element_domain_id"], stack),
                "elements": [expression(item, stack) for item in record["element_expr_ids"]],
                "cardinality": record["cardinality"],
            }
        elif kind == "interval":
            value = {
                "kind": kind, "base": record["base"],
                "lower": None if record["lower_expr_id"] is None else expression(record["lower_expr_id"], stack),
                "lower_closed": record["lower_closed"],
                "upper": None if record["upper_expr_id"] is None else expression(record["upper_expr_id"], stack),
                "upper_closed": record["upper_closed"],
            }
        elif kind == "modular":
            value = {"kind": kind, "modulus": expression(record["modulus_expr_id"], stack)}
        elif kind == "collection":
            value = {
                "kind": kind, "collection": record["collection"],
                "element_domain": domain(record["element_domain_id"], stack),
                "finiteness": record["finiteness"],
            }
        elif kind == "product":
            value = {"kind": kind, "factors": [domain(item, stack) for item in record["factor_domain_ids"]]}
        elif kind == "function":
            value = {
                "kind": kind,
                "parameters": [domain(item, stack) for item in record["parameter_domain_ids"]],
                "result": domain(record["result_domain_id"], stack), "total": record["total"],
            }
        elif kind == "structure":
            value = {
                "kind": kind, "theory_id": record["theory_id"],
                "parameter_domains": [domain(item, stack) for item in record["parameter_domain_ids"]],
                "parameter_expressions": [expression(item, stack) for item in record["parameter_expr_ids"]],
            }
        else:
            value = {"kind": "opaque", "source": record}
        cache[key] = value
        return value

    owners: dict[str, tuple[str, str, int]] = {}
    for definition_record in indexes["definitions"].values():
        for position, variable_id in enumerate(definition_record["parameter_variable_ids"]):
            owners[variable_id] = ("parameter", definition_record["id"], position)
    for statement_record in indexes["statements"].values():
        if statement_record["kind"] == "quantified":
            for position, variable_id in enumerate(statement_record["variable_ids"]):
                owners[variable_id] = ("quantified", statement_record["id"], position)

    def variable(variable_id: str, stack: tuple[tuple[str, tuple[str, ...]], ...]) -> Any:
        record = indexes["variables"][variable_id]
        for depth, frame in enumerate(reversed(stack)):
            if variable_id in frame[1]:
                return {
                    "binding_kind": frame[0], "depth": depth,
                    "position": frame[1].index(variable_id),
                    "domain": domain(record["domain_id"], stack), "role": record["role"],
                }
        owner = owners.get(variable_id)
        if owner is not None:
            return {
                "binding_kind": owner[0], "position": owner[2],
                "domain": domain(record["domain_id"], stack), "role": record["role"],
            }
        return {
            "binding_kind": "free", "variable_id": variable_id, "name": record["name"],
            "domain": domain(record["domain_id"], stack), "role": record["role"],
        }

    def expression(expression_id: str, stack: tuple[tuple[str, tuple[str, ...]], ...]) -> Any:
        key = ("expressions", expression_id, stack)
        if key in cache:
            return cache[key]
        record = indexes["expressions"][expression_id]
        base = domain(record["domain_id"], stack)
        kind = record["kind"]
        if kind == "literal":
            value = {"kind": kind, "domain": base, "literal_type": record["literal_type"], "value": record["value"]}
        elif kind == "variable":
            value = {"kind": kind, "domain": base, "variable": variable(record["variable_id"], stack)}
        elif kind == "apply":
            value = {
                "kind": kind, "domain": base, "operator": record["operator"],
                "arguments": [expression(item, stack) for item in record["argument_expr_ids"]],
                "attributes": record["attributes"],
            }
        elif kind in {"tuple", "collection"}:
            value = {"kind": kind, "domain": base, "elements": [expression(item, stack) for item in record["element_expr_ids"]]}
        elif kind == "conditional":
            value = {
                "kind": kind, "domain": base,
                "condition": statement(record["condition_statement_id"], stack),
                "then": expression(record["then_expr_id"], stack),
                "else": expression(record["else_expr_id"], stack),
            }
        else:
            value = {"kind": "opaque", "domain": base, "source": record}
        cache[key] = value
        return value

    def relation(relation_id: str, stack: tuple[tuple[str, tuple[str, ...]], ...]) -> Any:
        key = ("relations", relation_id, stack)
        if key in cache:
            return cache[key]
        record = indexes["relations"][relation_id]
        operands = [expression(item, stack) for item in record["operand_expr_ids"]]
        if record["kind"] in {"equal", "not_equal"} and len(operands) == 2:
            operands = [item[1] for item in sorted(enumerate(operands), key=lambda item: (_canonical(item[1]), item[0]))]
        value = {"kind": record["kind"], "operands": operands}
        if record["kind"] == "predicate":
            value["predicate"] = record["predicate"]
        cache[key] = value
        return value

    def statement(statement_id: str, stack: tuple[tuple[str, tuple[str, ...]], ...]) -> Any:
        key = ("statements", statement_id, stack)
        if key in cache:
            return cache[key]
        record = indexes["statements"][statement_id]
        kind = record["kind"]
        if kind == "truth":
            value = {"kind": kind, "value": record["value"]}
        elif kind == "relation":
            value = {"kind": kind, "relation": relation(record["relation_id"], stack)}
        elif kind == "logical":
            operands = [statement(item, stack) for item in record["operand_statement_ids"]]
            if record["operator"] in {"and", "or"} or (
                record["operator"] == "iff" and len(operands) == 2
            ):
                operands = [item[1] for item in sorted(enumerate(operands), key=lambda item: (_canonical(item[1]), item[0]))]
            value = {"kind": kind, "operator": record["operator"], "operands": operands}
        elif kind == "quantified":
            variable_ids = tuple(record["variable_ids"])
            next_stack = (*stack, ("quantified", variable_ids))
            value = {
                "kind": kind, "quantifier": record["quantifier"],
                "variables": [variable(item, next_stack) for item in variable_ids],
                "body": statement(record["body_statement_id"], next_stack),
            }
        else:
            value = {"kind": "opaque", "source": record}
        cache[key] = value
        return value

    expected: dict[tuple[str, str], bytes] = {}
    for registry, records in indexes.items():
        if registry == "domains":
            expected.update(((registry, key), _canonical(domain(key, ()))) for key in records)
        elif registry == "variables":
            expected.update(((registry, key), _canonical(variable(key, ()))) for key in records)
        elif registry == "expressions":
            expected.update(((registry, key), _canonical(expression(key, ()))) for key in records)
        elif registry == "relations":
            expected.update(((registry, key), _canonical(relation(key, ()))) for key in records)
        elif registry == "statements":
            expected.update(((registry, key), _canonical(statement(key, ()))) for key in records)
        elif registry == "definitions":
            for definition_id, record in records.items():
                variable_ids = tuple(record["parameter_variable_ids"])
                stack = (("parameter", variable_ids),)
                body = record["body"]
                value = {
                    "kind": "definition", "name": record["name"],
                    "parameters": [variable(item, stack) for item in variable_ids],
                    "result_domain": None if record["result_domain_id"] is None else domain(record["result_domain_id"], stack),
                    "body_kind": body["kind"],
                    "body": expression(body["expression_id"], stack) if body["kind"] == "expression" else statement(body["statement_id"], stack),
                    "recursive": record["recursive"],
                }
                expected[(registry, definition_id)] = _canonical(value)
    # Shared nodes may be reached inside a lexical owner before their source
    # inventory record is visited.  Production deliberately retains that first
    # capture-safe form, so independently retain every lexical value computed
    # for the same source and accept only an exact member of this closed set.
    options = {key: {value} for key, value in expected.items()}
    for (registry, source_ref, _stack), value in cache.items():
        if registry in {"domains", "expressions", "relations", "statements"}:
            options.setdefault((registry, source_ref), set()).add(_canonical(value))
    return options


def _obligation_ordinal(source_id: str | None) -> int | None:
    if source_id is None:
        return None
    prefix = "obligation_"
    if not source_id.startswith(prefix) or len(source_id) != len(prefix) + 6:
        _fail(f"invalid source obligation identity: {source_id}")
    try:
        return int(source_id[len(prefix):])
    except ValueError:
        _fail(f"invalid source obligation ordinal: {source_id}")


def _verify_source_projection(
    raw_proof: dict[str, Any], candidate: dict[str, Any],
) -> dict[str, Any]:
    reading_id = candidate["reading_id"]
    source_wrapper = next(
        item for item in raw_proof["candidates"] if item["reading_id"] == reading_id
    )
    graph = source_wrapper["graph"]
    if candidate["source_graph_sha256"] != source_wrapper["graph_sha256"]:
        _fail("source graph identity drift")
    if candidate["goal_ids"] != graph["goal_ids"]:
        _fail("goal order or membership drift")
    expected_roots = [_obligation_ordinal(item) for item in graph["root_obligation_ids"]]
    if candidate["root_ordinals"] != expected_roots:
        _fail("root obligation topology drift")

    raw_contexts = {
        item["local_context_sha256"]: item["context"]
        for item in graph["local_contexts"]
    }
    actual_contexts = {
        item["source_local_context_sha256"]: item
        for item in candidate["contexts"]
    }
    if set(actual_contexts) != set(raw_contexts):
        _fail("local-context membership drift")
    occurrence_fields = (
        ("definition_occurrences", "definition_ids"),
        ("assumption_occurrences", "assumption_fact_sha256s"),
        ("bound_variable_occurrences", "bound_variable_ids"),
        ("hypothesis_occurrences", "local_hypothesis_statement_ids"),
        ("witness_occurrences", "witness_placeholder_ids"),
    )
    for digest, source in raw_contexts.items():
        actual = actual_contexts[digest]
        if (
            actual["reading_id"] != reading_id
            or actual["source_span_ids"] != source["source_span_ids"]
            or actual["mathematical_authority"] is not False
        ):
            _fail("context source metadata drift")
        for output_field, source_field in occurrence_fields:
            occurrences = sorted(
                actual[output_field], key=lambda item: item["source_index"]
            )
            if [item["source_ref"] for item in occurrences] != source[source_field]:
                _fail(f"context occurrence source drift: {output_field}")
            expected_indexes = set(range(len(occurrences)))
            if (
                {item["source_index"] for item in occurrences} != expected_indexes
                or {item["canonical_index"] for item in occurrences} != expected_indexes
            ):
                _fail(f"context occurrence permutation drift: {output_field}")
        expected_context_value = {
            "reading_id": reading_id,
            "definitions": [
                item["semantic_sha256"] for item in actual["definition_occurrences"]
            ],
            "assumptions": [
                {"role": item["role"], "semantic_sha256": item["semantic_sha256"]}
                for item in actual["assumption_occurrences"]
            ],
            "bound_variables": [
                item["semantic_sha256"] for item in actual["bound_variable_occurrences"]
            ],
            "hypotheses": [
                item["semantic_sha256"] for item in actual["hypothesis_occurrences"]
            ],
            "witnesses": [
                item["semantic_sha256"] for item in actual["witness_occurrences"]
            ],
            "dependencies": actual["dependency_semantic_sha256s"],
        }
        if actual["semantic_value"] != expected_context_value:
            _fail("independent context semantic-value drift")
        if actual["semantic_sha256"] != _sha(_canonical(expected_context_value)):
            _fail("independent context semantic identity drift")

    raw_obligations = graph["obligations"]
    if len(candidate["obligations"]) != len(raw_obligations):
        _fail("obligation membership drift")
    goal_positions = {item: index for index, item in enumerate(graph["goal_ids"])}
    for ordinal, (source, actual) in enumerate(
        zip(raw_obligations, candidate["obligations"], strict=True)
    ):
        expected_children = [_obligation_ordinal(item) for item in source["child_obligation_ids"]]
        expected_prerequisites = [
            _obligation_ordinal(item) for item in source["prerequisite_obligation_ids"]
        ]
        alternative = source["alternative_group_id"]
        expected_alternative = None
        if alternative is not None:
            if not alternative.startswith("alternative_"):
                _fail("alternative group source identity drift")
            expected_alternative = _obligation_ordinal(alternative[len("alternative_"):])
        exact_fields = {
            "reading_id": source["reading_id"],
            "source_obligation_id": source["obligation_id"],
            "source_obligation_sha256": source["obligation_sha256"],
            "ordinal": ordinal,
            "root_goal_id": source["root_goal_id"],
            "parent_ordinal": _obligation_ordinal(source["parent_obligation_id"]),
            "rule_id": source["rule_id"],
            "kind": source["kind"],
            "goal_mode": source["goal_mode"],
            "status": source["status"],
            "source_statement_id": source["statement_id"],
            "source_relation_id": source["relation_id"],
            "child_ordinals": expected_children,
            "prerequisite_ordinals": expected_prerequisites,
            "alternative_group_ordinal": expected_alternative,
            "alternative_index": source["alternative_index"],
            "strategy_ids": [
                item["strategy_id"] for item in source["admissible_strategies"]
            ],
            "source_span_ids": source["source_span_ids"],
            "supported": source["supported"],
            "mathematical_authority": False,
        }
        for field, expected in exact_fields.items():
            if actual[field] != expected:
                _fail(f"obligation source projection drift: {ordinal}:{field}")
        expected_strategies = []
        for strategy in source["admissible_strategies"]:
            expected_strategy = {
                "strategy_id": strategy["strategy_id"],
                "match_rule_id": strategy["match_rule_id"],
                "reason_code": strategy["reason_code"],
                "matched_value": strategy["matched_value"],
                "prerequisite_ordinals": [
                    _obligation_ordinal(item)
                    for item in strategy["prerequisite_obligation_ids"]
                ],
                "guarantees_success": strategy["guarantees_success"],
                "mathematical_authority": strategy["mathematical_authority"],
            }
            expected_strategies.append(expected_strategy)
        if actual["strategy_record_sha256s"] != [
            _sha(_canonical(item)) for item in expected_strategies
        ]:
            _fail("strategy record semantic identity drift")
        expected_semantic = {
            "reading_id": reading_id,
            "ordinal": ordinal,
            "root_goal_position": goal_positions[source["root_goal_id"]],
            "parent_ordinal": exact_fields["parent_ordinal"],
            "rule_id": source["rule_id"],
            "kind": source["kind"],
            "goal_mode": source["goal_mode"],
            "status": source["status"],
            "statement": actual["statement_normal_form"],
            "local_context_semantic_sha256": actual["local_context_semantic_sha256"],
            "child_ordinals": expected_children,
            "prerequisite_ordinals": expected_prerequisites,
            "alternative_group_ordinal": expected_alternative,
            "alternative_index": source["alternative_index"],
            "witness_slots": actual["witness_slots"],
            "strategies": expected_strategies,
            "dependencies": actual["dependency_semantic_sha256s"],
            "supported": source["supported"],
        }
        if actual["semantic_value"] != expected_semantic:
            _fail("independent obligation semantic-value drift")
        if actual["semantic_sha256"] != _sha(_canonical(expected_semantic)):
            _fail("independent obligation semantic identity drift")
        if actual["statement_semantic_sha256"] != _sha(
            _canonical(actual["statement_normal_form"])
        ):
            _fail("independent obligation statement identity drift")
    return graph


def _semantic_graph_digest(candidate: dict[str, Any]) -> str:
    obligations = candidate["obligations"]
    source_values = [item["semantic_value"] for item in obligations]
    positional_fields = {
        "ordinal", "root_goal_position", "parent_ordinal", "child_ordinals",
        "prerequisite_ordinals", "alternative_group_ordinal", "alternative_index",
    }
    base_values = []
    for value in source_values:
        base = {key: item for key, item in value.items() if key not in positional_fields}
        base["strategies"] = [
            {key: item for key, item in strategy.items() if key != "prerequisite_ordinals"}
            for strategy in value["strategies"]
        ]
        base_values.append(base)
    semantic_order = sorted(
        range(len(obligations)),
        key=lambda ordinal: (_canonical(base_values[ordinal]), ordinal),
    )
    semantic_ordinal = {
        source_ordinal: canonical
        for canonical, source_ordinal in enumerate(semantic_order)
    }
    graph_obligations = []
    commutative_owners = {
        "mh.obligation.logical.and", "mh.obligation.logical.or",
        "mh.obligation.logical.iff",
    }
    for source_ordinal in semantic_order:
        obligation = obligations[source_ordinal]
        source_value = source_values[source_ordinal]
        value = dict(base_values[source_ordinal])
        children = [semantic_ordinal[item] for item in obligation["child_ordinals"]]
        if obligation["rule_id"] in commutative_owners:
            children.sort()
        strategies = []
        for strategy in source_value["strategies"]:
            normalized = dict(strategy)
            normalized["prerequisite_ordinals"] = [
                semantic_ordinal[item] for item in strategy["prerequisite_ordinals"]
            ]
            strategies.append(normalized)
        alternative_index = obligation["alternative_index"]
        alternative_owner_ordinal = obligation["alternative_group_ordinal"]
        if alternative_owner_ordinal is not None:
            owner = obligations[alternative_owner_ordinal]
            if owner["rule_id"] in commutative_owners:
                alternatives = sorted(
                    semantic_ordinal[item] for item in owner["child_ordinals"]
                )
                alternative_index = alternatives.index(semantic_ordinal[source_ordinal])
        value.update({
            "semantic_ordinal": semantic_ordinal[source_ordinal],
            "root_goal_position": source_value["root_goal_position"],
            "parent_semantic_ordinal": None
            if obligation["parent_ordinal"] is None
            else semantic_ordinal[obligation["parent_ordinal"]],
            "child_semantic_ordinals": children,
            "prerequisite_semantic_ordinals": [
                semantic_ordinal[item] for item in obligation["prerequisite_ordinals"]
            ],
            "alternative_group_semantic_ordinal": None
            if alternative_owner_ordinal is None
            else semantic_ordinal[alternative_owner_ordinal],
            "alternative_index": alternative_index,
            "strategies": strategies,
        })
        graph_obligations.append(value)
    forms = [
        {
            "form_kind": item["form_kind"],
            "semantic_sha256": item["semantic_sha256"],
            "value": item["value"],
            "supported": item["supported"],
        }
        for item in candidate["normal_forms"]
        if item["source_registry"] not in {"local_contexts", "obligations"}
    ]
    graph_value = {
        "contract_sha256": CONTRACT_SHA256,
        "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
        "reading_id": candidate["reading_id"],
        "goal_count": len(candidate["goal_ids"]),
        "root_semantic_ordinals": [
            semantic_ordinal[item] for item in candidate["root_ordinals"]
        ],
        "forms": sorted(forms, key=_canonical),
        "contexts": sorted(item["semantic_sha256"] for item in candidate["contexts"]),
        "obligations": graph_obligations,
        "traces": sorted(
            ({
                "kind": item["kind"],
                "canonical_index": item["canonical_index"],
                "semantic_sha256": item["semantic_sha256"],
                "rule_id": item["rule_id"],
            } for item in candidate["traces"]),
            key=_canonical,
        ),
        "unsupported": candidate["unsupported_semantic_sha256s"],
    }
    return _sha(_canonical(graph_value))


def _verify_result(validators: dict[str, Any]) -> dict[str, object]:
    problem = _fixture_problem()
    proof = _proof_bytes(problem)
    result = production.normalize_canonical_obligations(proof)
    if result.status != "normalized" or result.mathematical_authority is not False:
        _fail(f"production fixture normalization failed: {result.reason_code}")
    raw_bytes = production.canonical_normalization_result_bytes(result)
    raw = json.loads(raw_bytes)
    result_validator = validators.get("canonical-normalization-result-v1.schema.json")
    if result_validator is not None:
        result_validator.validate(raw)
    if production.parse_canonical_normalization_result(raw_bytes) != result:
        _fail("strict normalized result replay drift")
    if result.result_sha256 != _sha(_canonical({
        key: value for key, value in raw.items() if key != "result_sha256"
    })):
        _fail("independent top-level result digest drift")
    raw_proof = json.loads(proof)
    form_count = context_count = obligation_count = trace_count = 0
    for typed, raw_candidate in zip(result.candidates, raw["candidates"], strict=True):
        _verify_source_projection(raw_proof, raw_candidate)
        expected = _independent_semantics(raw_proof, raw_candidate)
        actual_forms = {
            (item["source_registry"], item["source_ref"]): item
            for item in raw_candidate["normal_forms"]
        }
        for key, expected_options in expected.items():
            item = actual_forms.get(key)
            if item is None:
                _fail(f"missing independently expected normal form: {key}")
            actual_bytes = _canonical(item["value"])
            if (
                actual_bytes not in expected_options
                or item["semantic_sha256"] != _sha(actual_bytes)
            ):
                _fail(f"independent semantic form drift: {key}")
        if typed.semantic_graph_sha256 != raw_candidate["semantic_graph_sha256"]:
            _fail("typed/raw semantic graph identity drift")
        if raw_candidate["semantic_graph_sha256"] != _semantic_graph_digest(raw_candidate):
            _fail("independent semantic graph identity drift")
        trace_ids = [item["trace_id"] for item in raw_candidate["traces"]]
        if trace_ids != [f"trace_{index:08d}" for index in range(len(trace_ids))]:
            _fail("trace identity sequence drift")
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for trace in raw_candidate["traces"]:
            groups.setdefault(
                (trace["owner_kind"], trace["owner_ref"], trace["kind"]), []
            ).append(trace)
        for key, traces in groups.items():
            expected_indexes = set(range(len(traces)))
            if (
                {item["source_index"] for item in traces} != expected_indexes
                or {item["canonical_index"] for item in traces} != expected_indexes
            ):
                _fail(f"non-bidirectional trace group: {key}")
        all_trace_ids = set(trace_ids)
        for context in raw_candidate["contexts"]:
            if not set(context["trace_ids"]) <= all_trace_ids:
                _fail("context trace closure drift")
            if context["semantic_sha256"] != _sha(_canonical(context["semantic_value"])):
                _fail("context semantic digest drift")
        for obligation in raw_candidate["obligations"]:
            if not set(obligation["trace_ids"]) <= all_trace_ids:
                _fail("obligation trace closure drift")
            if obligation["semantic_sha256"] != _sha(_canonical(obligation["semantic_value"])):
                _fail("obligation semantic digest drift")
            if obligation["statement_semantic_sha256"] != _sha(_canonical(obligation["statement_normal_form"])):
                _fail("obligation statement digest drift")
        form_count += len(raw_candidate["normal_forms"])
        context_count += len(raw_candidate["contexts"])
        obligation_count += len(raw_candidate["obligations"])
        trace_count += len(raw_candidate["traces"])
    return {
        "candidates": len(result.candidates),
        "contexts": context_count,
        "normal_forms": form_count,
        "obligations": obligation_count,
        "result_sha256": result.result_sha256,
        "traces": trace_count,
    }


def _metamorphic_checks() -> dict[str, bool]:
    alpha_left = minimal_problem_ir()
    alpha_right = copy.deepcopy(alpha_left)
    alpha_right["variables"][0]["id"] = "variable_z"
    alpha_right["variables"][0]["name"] = "z"
    alpha_right["expressions"][0]["variable_id"] = "variable_z"
    alpha_right["statements"][1]["variable_ids"] = ["variable_z"]

    def graph_digest(problem: dict[str, Any]) -> str:
        result = production.normalize_canonical_obligations(_proof_bytes(problem))
        if result.status != "normalized":
            _fail(f"metamorphic fixture failed: {result.reason_code}")
        return result.candidates[0].semantic_graph_sha256

    alpha = graph_digest(alpha_left) == graph_digest(alpha_right)
    if not alpha:
        _fail("alpha-renaming invariance failed")

    def binary(kind: str, swapped: bool) -> dict[str, Any]:
        problem = minimal_problem_ir()
        problem["variables"][0]["role"] = "free"
        problem["variables"].append({
            "id": "variable_y", "name": "y", "domain_id": "domain_integer",
            "role": "free", "span_ids": [],
        })
        problem["expressions"].append({
            "id": "expression_y", "kind": "variable", "variable_id": "variable_y",
            "domain_id": "domain_integer", "span_ids": [],
        })
        problem["relations"][0]["kind"] = kind
        operands = ["expression_x", "expression_y"]
        problem["relations"][0]["operand_expr_ids"] = list(reversed(operands)) if swapped else operands
        problem["statements"] = [problem["statements"][0]]
        problem["goals"][0]["statement_id"] = "statement_body"
        return problem

    commutative = all(
        graph_digest(binary(kind, False)) == graph_digest(binary(kind, True))
        for kind in ("equal", "not_equal")
    )
    ordered = graph_digest(binary("less", False)) != graph_digest(binary("less", True))
    def logical(operator: str, swapped: bool) -> dict[str, Any]:
        problem = minimal_problem_ir()
        problem["statements"].extend([
            {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
            {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        ])
        operands = ["statement_true", "statement_false"]
        problem["statements"].append({
            "id": "statement_logical", "kind": "logical", "operator": operator,
            "operand_statement_ids": list(reversed(operands)) if swapped else operands,
            "span_ids": [],
        })
        problem["goals"][0]["statement_id"] = "statement_logical"
        return problem

    logical_commutative = all(
        graph_digest(logical(operator, False))
        == graph_digest(logical(operator, True))
        for operator in ("and", "or", "iff")
    )
    implication_ordered = (
        graph_digest(logical("implies", False))
        != graph_digest(logical("implies", True))
    )

    assumptions_left = minimal_problem_ir()
    assumptions_left["statements"].extend([
        {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
        {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
    ])
    assumptions_left["assumptions"].extend([
        {
            "id": "assumption_true", "statement_id": "statement_true",
            "role": "given", "span_ids": [],
        },
        {
            "id": "assumption_false", "statement_id": "statement_false",
            "role": "side_condition", "span_ids": [],
        },
    ])
    assumptions_left["readings"][0]["assumption_ids"] = [
        "assumption_true", "assumption_false",
    ]
    assumptions_right = copy.deepcopy(assumptions_left)
    assumptions_right["readings"][0]["assumption_ids"].reverse()
    assumption_order = (
        graph_digest(assumptions_left) == graph_digest(assumptions_right)
    )
    if not all(
        (
            commutative, ordered, logical_commutative, implication_ordered,
            assumption_order,
        )
    ):
        _fail("exact commutative or ordered-relation boundary failed")
    return {
        "alpha_invariant": alpha,
        "assumption_order_invariant": assumption_order,
        "authorized_commutative_invariant": commutative,
        "logical_commutative_invariant": logical_commutative,
        "implication_order_distinguishable": implication_ordered,
        "ordered_relation_distinguishable": ordered,
    }


def _negative_checks(validators: dict[str, Any]) -> int:
    controls = 0
    invalids = (None, bytearray(), memoryview(b"{}"), b"{}")
    for value in invalids:
        result = production.normalize_canonical_obligations(value)  # type: ignore[arg-type]
        if not (
            result.status in {"invalid", "exhausted"}
            and result.input_result_sha256 is None
            and result.proof_result_bytes is None
            and result.candidates == ()
            and result.result_sha256 is None
        ):
            _fail("invalid input returned a partial canonical artifact")
        controls += 1
    normalized = production.normalize_canonical_obligations(_proof_bytes(_fixture_problem()))
    raw = production.canonical_normalization_result_bytes(normalized)
    try:
        production.parse_canonical_normalization_result(raw.rstrip(b"\n"))
    except production.CanonicalNormalizationValidationError:
        controls += 1
    else:
        _fail("strict parser accepted noncanonical framing")
    forged = json.loads(raw)
    forged["candidates"][0]["obligations"][0]["status"] = "ready"
    repaired = dict(forged)
    repaired.pop("result_sha256")
    forged["result_sha256"] = _sha(_canonical(repaired))
    try:
        production.parse_canonical_normalization_result(_canonical(forged))
    except production.CanonicalNormalizationValidationError:
        controls += 1
    else:
        _fail("strict parser accepted repaired outer digest forgery")
    result_validator = validators.get("canonical-normalization-result-v1.schema.json")
    if result_validator is not None:
        surplus = json.loads(raw)
        surplus["unexpected"] = True
        if not list(result_validator.iter_errors(surplus)):
            _fail("closed result schema accepted unknown field")
    else:
        # The governed dependency-minimal profile performs the equivalent
        # closed-root control directly so report bytes do not depend on whether
        # the optional Draft 2020-12 engine is installed.
        schema = json.loads(
            (
                ROOT
                / "docs/contracts/schemas/canonical-normalization-result-v1.schema.json"
            ).read_bytes()
        )
        if schema.get("additionalProperties") is not False:
            _fail("dependency-minimal closed result schema control failed")
    controls += 1
    return controls


def _report() -> dict[str, object]:
    identities = _identity_checks()
    validators = identities.pop("validators")
    assert isinstance(validators, dict)
    fixture = _verify_result(validators)
    metamorphic = _metamorphic_checks()
    test_paths = sorted((ROOT / "tests/canonical_normalization").glob("test_*.py"))
    report: dict[str, object] = {
        "artifacts": {
            path.as_posix(): digest for path, digest in ARTIFACTS.items()
        },
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "identity_checks": identities,
        "metamorphic": metamorphic,
        "negative_controls": _negative_checks(validators),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "source": _source_closure(),
        "summary": {
            "candidates": fixture["candidates"],
            "contexts": fixture["contexts"],
            "mathematical_authority": False,
            "normal_forms": fixture["normal_forms"],
            "obligations": fixture["obligations"],
            "status": "passed",
            "traces": fixture["traces"],
        },
        "tests": {
            path.relative_to(ROOT).as_posix(): _sha(path.read_bytes())
            for path in test_paths
        },
        "validator_sha256": _sha(
            (ROOT / "tools/validate_canonical_normalization.py").read_bytes()
        ),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"canonical-normalization: report updated: {target}")
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
        OSError, UnicodeError, json.JSONDecodeError,
        CanonicalNormalizationReportError,
    ) as exc:
        print(f"canonical-normalization: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "canonical-normalization: PASS "
        f"(candidates={summary['candidates']}, forms={summary['normal_forms']}, "
        f"contexts={summary['contexts']}, obligations={summary['obligations']}, "
        f"traces={summary['traces']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
