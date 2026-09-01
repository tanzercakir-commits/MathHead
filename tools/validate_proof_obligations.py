#!/usr/bin/env python3
"""Independently validate the MH-043 proof-obligation boundary and report."""

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
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import proof_obligations as production  # noqa: E402
from mathhead.domain_assumptions import (  # noqa: E402
    domain_assumption_result_bytes,
    normalize_domain_assumptions,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


CONTRACT_ID = "MH-C-PROOF-OBLIGATION-DECOMPOSITION-001"
CONTRACT_SHA256 = "ea5d0664611b57da3074e20fce90623318ce04280d38ecce548025a91a7b19ff"
SOURCE = Path("src/mathhead/proof_obligations.py")
DEFAULT_REPORT = Path("docs/obligations/reports/proof-obligations-v1.json")
REPORT_SCHEMA = "mathhead.proof-obligation-validation-report.v1"
ARTIFACTS = {
    Path("docs/contracts/schemas/proof-obligation-v1.schema.json"): "55ff62bac3515763773645577c0ba163adbdda726a277a98945002ea82103db4",
    Path("docs/contracts/schemas/proof-obligation-local-context-v1.schema.json"): "7ace8271f6ab2839b109208fd0b9686f9a6d3ac1c75c7df60e6febb37a7bd3e5",
    Path("docs/contracts/schemas/proof-obligation-graph-v1.schema.json"): "7244ad195f7a55732babda563b7b6d7d7b9b56f37d41874fe137f8b2e1349da3",
    Path("docs/contracts/schemas/proof-obligation-rules-v1.schema.json"): "4e9dd834724e85b630b57a1fc9b2d92919e85952d202ec0713a812afacc3f739",
    Path("docs/contracts/schemas/proof-strategy-catalogue-v1.schema.json"): "77a9f1de86d6bedc10c2b181c614dee987bea36937ce696be4aa232694d2333e",
    Path("docs/contracts/schemas/proof-obligation-result-v1.schema.json"): "449f6bb90edf609532410f6df133cb92e7cae925f0b57d1c527b7e5d453cb9ce",
    Path("docs/obligations/proof-obligation-rules-v1.json"): "d59c480c6ee19471051632407deb611d8df6be4987cf23154d56aa4d3326a524",
    Path("docs/obligations/proof-strategy-catalogue-v1.json"): "28b815267fb5a2637d4a673218d1720c9ddcab0ea3f6bf3a8f6d05a3125fa1c8",
}
ENTITY_REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals",
)
SEMANTIC_REGISTRIES = frozenset(ENTITY_REGISTRIES[2:])
ALLOWED_IMPORT_ROOTS = {
    "__future__", "collections", "dataclasses", "hashlib", "json", "mathhead",
    "re", "typing", "unicodedata",
}
FORBIDDEN_CALLS = {
    "Path", "eval", "exec", "getenv", "import_module", "open", "perf_counter",
    "run", "system", "time",
}
PROVE_RULES = {
    ("truth", None): ("mh.obligation.statement.truth", "truth", True),
    ("relation", None): ("mh.obligation.statement.relation", "relation", True),
    ("logical", "not"): ("mh.obligation.logical.not", "negation", True),
    ("logical", "and"): ("mh.obligation.logical.and", "conjunction", True),
    ("logical", "or"): ("mh.obligation.logical.or", "disjunction", True),
    ("logical", "implies"): ("mh.obligation.logical.implies", "implication", True),
    ("logical", "iff"): ("mh.obligation.logical.iff", "biconditional", True),
    ("quantified", "forall"): ("mh.obligation.quantified.forall", "universal", True),
    ("quantified", "exists"): ("mh.obligation.quantified.exists", "existential", True),
    ("quantified", "exists_unique"): (
        "mh.obligation.quantified.exists-unique", "unique_existence", True,
    ),
}
MODE_RULES = {
    "refute": ("mh.obligation.goal.refute", "refutation"),
    "find_witness": ("mh.obligation.goal.find-witness", "witness_search"),
    "compute": ("mh.obligation.goal.compute", "computation"),
    "classify": ("mh.obligation.goal.classify", "classification"),
    "optimize": ("mh.obligation.goal.optimize", "optimization"),
}
STRATEGIES = (
    ("mh.strategy.truth-constant", "mh.strategy-match.kind.truth", "obligation_kind", ("truth",), "EXACT_TRUTH_KIND"),
    ("mh.strategy.equality", "mh.strategy-match.relation.equal", "relation_kind", ("equal",), "EXACT_EQUAL_RELATION"),
    ("mh.strategy.disequality", "mh.strategy-match.relation.not-equal", "relation_kind", ("not_equal",), "EXACT_NOT_EQUAL_RELATION"),
    ("mh.strategy.ordered-relation", "mh.strategy-match.relation.order", "relation_kind", ("greater", "greater_equal", "less", "less_equal"), "EXACT_ORDER_RELATION"),
    ("mh.strategy.membership", "mh.strategy-match.relation.membership", "relation_kind", ("member", "not_member"), "EXACT_MEMBERSHIP_RELATION"),
    ("mh.strategy.divisibility", "mh.strategy-match.relation.divides", "relation_kind", ("divides",), "EXACT_DIVIDES_RELATION"),
    ("mh.strategy.congruence", "mh.strategy-match.relation.congruent", "relation_kind", ("congruent",), "EXACT_CONGRUENT_RELATION"),
    ("mh.strategy.named-predicate", "mh.strategy-match.relation.predicate", "relation_kind", ("predicate",), "EXACT_PREDICATE_RELATION"),
    ("mh.strategy.structural-composition", "mh.strategy-match.kind.structural", "obligation_kind", ("biconditional", "conjunction", "implication", "universal"), "EXACT_STRUCTURAL_KIND"),
    ("mh.strategy.case-choice", "mh.strategy-match.kind.case-choice", "obligation_kind", ("disjunction",), "EXACT_DISJUNCTION_KIND"),
    ("mh.strategy.witness-construction", "mh.strategy-match.kind.witness", "obligation_kind", ("existential", "unique_existence", "witness_construction", "witness_search"), "EXACT_WITNESS_KIND"),
    ("mh.strategy.uniqueness", "mh.strategy-match.kind.uniqueness", "obligation_kind", ("uniqueness",), "EXACT_UNIQUENESS_KIND"),
    ("mh.strategy.counterexample-search", "mh.strategy-match.mode.refute", "goal_mode", ("refute",), "EXACT_REFUTE_MODE"),
    ("mh.strategy.exact-computation", "mh.strategy-match.mode.compute", "goal_mode", ("compute",), "EXACT_COMPUTE_MODE"),
    ("mh.strategy.classification", "mh.strategy-match.mode.classify", "goal_mode", ("classify",), "EXACT_CLASSIFY_MODE"),
    ("mh.strategy.optimization", "mh.strategy-match.mode.optimize", "goal_mode", ("optimize",), "EXACT_OPTIMIZE_MODE"),
    ("mh.strategy.finite-enumeration", "mh.strategy-match.domain.finite", "domain_kind", ("finite",), "EXACT_FINITE_DOMAIN_DEPENDENCY"),
    ("mh.strategy.modular-domain", "mh.strategy-match.domain.modular", "domain_kind", ("modular",), "EXACT_MODULAR_DOMAIN_DEPENDENCY"),
    ("mh.strategy.numeric-domain", "mh.strategy-match.carrier.numeric", "builtin_carrier", ("complex", "integer", "natural", "rational", "real"), "EXACT_NUMERIC_CARRIER_DEPENDENCY"),
)


class ProofObligationReportError(RuntimeError):
    """An independent contract, source, output, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise ProofObligationReportError(detail)


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


def _identity_checks() -> dict[str, Any]:
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
    if production.CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract binding drift")
    if (
        production.DECOMPOSITION_CATALOGUE_SHA256
        != ARTIFACTS[Path("docs/obligations/proof-obligation-rules-v1.json")]
        or production.STRATEGY_CATALOGUE_SHA256
        != ARTIFACTS[Path("docs/obligations/proof-strategy-catalogue-v1.json")]
    ):
        _fail("production catalogue binding drift")

    schemas = []
    for path in sorted((ROOT / "docs/contracts/schemas").glob("*.schema.json")):
        schema = json.loads(path.read_bytes())
        if "$id" in schema:
            schemas.append(schema)
    selected_names = {
        "proof-obligation-v1.schema.json",
        "proof-obligation-local-context-v1.schema.json",
        "proof-obligation-graph-v1.schema.json",
        "proof-obligation-rules-v1.schema.json",
        "proof-strategy-catalogue-v1.schema.json",
        "proof-obligation-result-v1.schema.json",
    }
    selected = {
        schema["$id"].rsplit("/", 1)[-1]: schema
        for schema in schemas
        if schema["$id"].rsplit("/", 1)[-1] in selected_names
    }
    if set(selected) != selected_names:
        _fail("proof-obligation schema identifier drift")
    for schema in selected.values():
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail("closed Draft 2020-12 schema root drift")

    rules = json.loads((ROOT / "docs/obligations/proof-obligation-rules-v1.json").read_bytes())
    strategies = json.loads((ROOT / "docs/obligations/proof-strategy-catalogue-v1.json").read_bytes())
    rule_ids = [item["rule_id"] for item in rules["rules"]]
    strategy_ids = [item["strategy_id"] for item in strategies["strategies"]]
    if len(rule_ids) != len(set(rule_ids)) or len(strategy_ids) != len(set(strategy_ids)):
        _fail("catalogue identity uniqueness drift")
    if (
        rules["mathematical_authority"] is not False
        or strategies["guarantees_success"] is not False
        or strategies["mathematical_authority"] is not False
    ):
        _fail("catalogue authority drift")
    if Draft202012Validator is None or Registry is None or Resource is None:
        return {}
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    validators = {
        name: Draft202012Validator(schema, registry=registry)
        for name, schema in selected.items()
    }
    for validator in validators.values():
        validator.check_schema(validator.schema)
    validators["proof-obligation-rules-v1.schema.json"].validate(rules)
    validators["proof-strategy-catalogue-v1.schema.json"].validate(strategies)
    return validators


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


def _rich_problem() -> dict[str, Any]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"
    problem["statements"] = [
        item for item in problem["statements"] if item["id"] != "statement_forall"
    ]
    problem["goals"][0]["statement_id"] = "statement_body"
    source = b"MathHead proof obligation fixture"
    problem["source_documents"] = [{
        "id": "source_fixture", "media_type": "text/plain", "language": "en",
        "sha256": _sha(source), "byte_length": len(source),
    }]
    problem["source_spans"] = [{
        "id": "span_fixture", "source_id": "source_fixture", "start_byte": 0,
        "end_byte": len(source),
    }]
    problem["relations"][0]["span_ids"] = ["span_fixture"]
    problem["domains"].extend([
        {"id": "domain_real", "kind": "builtin", "name": "real", "span_ids": []},
        {"id": "domain_finite", "kind": "finite", "element_domain_id": "domain_integer", "element_expr_ids": ["expression_zero", "expression_one"], "cardinality": 2, "span_ids": []},
        {"id": "domain_interval", "kind": "interval", "base": "integer", "lower_expr_id": "expression_zero", "lower_closed": True, "upper_expr_id": "expression_two", "upper_closed": True, "span_ids": []},
        {"id": "domain_modular", "kind": "modular", "modulus_expr_id": "expression_two", "span_ids": []},
        {"id": "domain_collection", "kind": "collection", "collection": "set", "element_domain_id": "domain_integer", "finiteness": "finite", "span_ids": []},
        {"id": "domain_product", "kind": "product", "factor_domain_ids": ["domain_integer", "domain_integer"], "span_ids": []},
        {"id": "domain_function", "kind": "function", "parameter_domain_ids": ["domain_integer"], "result_domain_id": "domain_integer", "total": True, "span_ids": []},
        {"id": "domain_structure", "kind": "structure", "theory_id": "org.mathhead.algebra.group", "parameter_domain_ids": ["domain_integer"], "parameter_expr_ids": ["expression_two"], "span_ids": []},
    ])
    problem["expressions"].extend([
        {"id": "expression_zero", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "0", "span_ids": []},
        {"id": "expression_one", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "1", "span_ids": []},
        {"id": "expression_two", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "2", "span_ids": []},
        {"id": "expression_set", "kind": "collection", "domain_id": "domain_collection", "element_expr_ids": ["expression_zero", "expression_one"], "span_ids": []},
    ])
    goal_specs: list[tuple[str, str, str]] = [("goal_reflexive", "statement_body", "prove")]
    for suffix, domain_id in (
        ("finite", "domain_finite"), ("interval", "domain_interval"),
        ("modular", "domain_modular"), ("collection", "domain_collection"),
        ("product", "domain_product"), ("function", "domain_function"),
        ("structure", "domain_structure"), ("real", "domain_real"),
    ):
        variable_id = f"variable_{suffix}"
        expression_id = f"expression_{suffix}"
        relation_id = f"relation_domain_{suffix}"
        statement_id = f"statement_domain_{suffix}"
        problem["variables"].append({
            "id": variable_id, "name": f"v_{suffix}", "domain_id": domain_id,
            "role": "free", "span_ids": [],
        })
        problem["expressions"].append({
            "id": expression_id, "kind": "variable", "domain_id": domain_id,
            "variable_id": variable_id, "span_ids": [],
        })
        problem["relations"].append({
            "id": relation_id, "kind": "equal",
            "operand_expr_ids": [expression_id, expression_id], "span_ids": [],
        })
        problem["statements"].append({
            "id": statement_id, "kind": "relation", "relation_id": relation_id,
            "span_ids": [],
        })
        goal_specs.append((f"goal_domain_{suffix}", statement_id, "prove"))
    relation_specs = (
        ("not_equal", "not_equal", ["expression_x", "expression_zero"], None),
        ("less", "less", ["expression_zero", "expression_x"], None),
        ("less_equal", "less_equal", ["expression_zero", "expression_x"], None),
        ("greater", "greater", ["expression_x", "expression_zero"], None),
        ("greater_equal", "greater_equal", ["expression_x", "expression_zero"], None),
        ("member", "member", ["expression_x", "expression_set"], None),
        ("not_member", "not_member", ["expression_x", "expression_set"], None),
        ("divides", "divides", ["expression_one", "expression_x"], None),
        ("congruent", "congruent", ["expression_x", "expression_one", "expression_two"], None),
        ("predicate", "predicate", ["expression_x"], "org.mathhead.fixture.predicate"),
    )
    for suffix, kind, operands, predicate in relation_specs:
        relation = {
            "id": f"relation_{suffix}", "kind": kind,
            "operand_expr_ids": operands, "span_ids": [],
        }
        if predicate is not None:
            relation["predicate"] = predicate
        problem["relations"].append(relation)
        problem["statements"].append({
            "id": f"statement_{suffix}", "kind": "relation",
            "relation_id": f"relation_{suffix}", "span_ids": [],
        })
        goal_specs.append((f"goal_{suffix}", f"statement_{suffix}", "prove"))
    problem["statements"].extend([
        {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
        {"id": "statement_not", "kind": "logical", "operator": "not", "operand_statement_ids": ["statement_false"], "span_ids": []},
        {"id": "statement_and", "kind": "logical", "operator": "and", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
        {"id": "statement_or", "kind": "logical", "operator": "or", "operand_statement_ids": ["statement_false", "statement_true"], "span_ids": []},
        {"id": "statement_implies", "kind": "logical", "operator": "implies", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
        {"id": "statement_iff", "kind": "logical", "operator": "iff", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
    ])
    for suffix in ("true", "not", "and", "or", "implies", "iff"):
        goal_specs.append((f"goal_{suffix}", f"statement_{suffix}", "prove"))
    for suffix, quantifier in (
        ("forall", "forall"), ("exists", "exists"),
        ("unique", "exists_unique"),
    ):
        variable_id = f"variable_{suffix}"
        expression_id = f"expression_{suffix}"
        relation_id = f"relation_{suffix}_body"
        body_id = f"statement_{suffix}_body"
        problem["variables"].append({
            "id": variable_id, "name": f"q_{suffix}",
            "domain_id": "domain_integer", "role": "bound", "span_ids": [],
        })
        problem["expressions"].append({
            "id": expression_id, "kind": "variable", "domain_id": "domain_integer",
            "variable_id": variable_id, "span_ids": [],
        })
        problem["relations"].append({
            "id": relation_id, "kind": "equal",
            "operand_expr_ids": [expression_id, expression_id], "span_ids": [],
        })
        problem["statements"].extend([
            {"id": body_id, "kind": "relation", "relation_id": relation_id, "span_ids": []},
            {"id": f"statement_{suffix}", "kind": "quantified", "quantifier": quantifier, "variable_ids": [variable_id], "body_statement_id": body_id, "span_ids": []},
        ])
    goal_specs.extend([
        ("goal_forall", "statement_forall", "prove"),
        ("goal_exists", "statement_exists", "prove"),
        ("goal_unique", "statement_unique", "prove"),
        ("goal_refute", "statement_true", "refute"),
        ("goal_witness", "statement_true", "find_witness"),
        ("goal_compute", "statement_true", "compute"),
        ("goal_classify", "statement_true", "classify"),
        ("goal_optimize", "statement_true", "optimize"),
    ])
    problem["definitions"].append({
        "id": "definition_truth", "name": "Truth", "parameter_variable_ids": [],
        "result_domain_id": None,
        "body": {"kind": "statement", "statement_id": "statement_true"},
        "recursive": False, "span_ids": [],
    })
    for index, role in enumerate(("given", "domain_constraint", "side_condition")):
        problem["assumptions"].append({
            "id": f"assumption_{index}", "statement_id": "statement_true",
            "role": role, "span_ids": [],
        })
    problem["goals"] = [
        {"id": goal_id, "statement_id": statement_id, "mode": mode, "span_ids": []}
        for goal_id, statement_id, mode in goal_specs
    ]
    primary = problem["readings"][0]
    primary["definition_ids"] = ["definition_truth"]
    primary["assumption_ids"] = ["assumption_0", "assumption_1", "assumption_2"]
    primary["goal_ids"] = [item[0] for item in goal_specs]
    primary["span_ids"] = ["span_fixture"]
    problem["readings"].append({
        "id": "reading_secondary", "label": "Alternate notation for the same goals.",
        "definition_ids": ["definition_truth"],
        "assumption_ids": ["assumption_0", "assumption_1", "assumption_2"],
        "goal_ids": [item[0] for item in goal_specs],
        "difference_from": "reading_only",
        "differences": [{
            "kind": "notation", "summary": "The source notation differs.",
            "affected_ids": ["goal_reflexive"], "span_ids": ["span_fixture"],
        }],
        "span_ids": [],
    })
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_only", "reading_secondary"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended goal scope.",
    }
    for registry in (*ENTITY_REGISTRIES, "readings"):
        problem[registry].sort(key=lambda item: item["id"])
    return problem


def _domain_bytes(problem: dict[str, Any]) -> bytes:
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
    if intake.status != "accepted":
        _fail(f"fixture intake failed: {intake.reason_code}: {intake.diagnostics}")
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    if readings.status != "analyzed":
        _fail(f"fixture analysis failed: {readings.reason_code}: {readings.diagnostics}")
    normalized = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    if normalized.status != "normalized":
        _fail(f"fixture normalization failed: {normalized.reason_code}: {normalized.diagnostics}")
    return domain_assumption_result_bytes(normalized)


def _indexes(projection: dict[str, Any]) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    owners: dict[str, str] = {}
    for registry in ENTITY_REGISTRIES:
        index = {item["id"]: item for item in projection["entities"][registry]}
        indexes[registry] = index
        owners.update((item, registry) for item in index)
    return indexes, owners


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
        add(
            "expressions" if body["kind"] == "expression" else "statements",
            body.get("expression_id" if body["kind"] == "expression" else "statement_id"),
        )
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
        owner, child = pending.pop()
        key = (owner, child)
        if key in seen:
            continue
        if child not in indexes[owner]:
            _fail(f"missing independent closure dependency: {owner}.{child}")
        seen.add(key)
        pending.extend(_dependencies(owner, indexes[owner][child]))
    semantic = sorted(
        (owner, child) for owner, child in seen
        if owner in SEMANTIC_REGISTRIES and (owner, child) != (registry, entity_id)
    )
    spans = sorted(child for owner, child in seen if owner == "source_spans")
    sources = sorted(child for owner, child in seen if owner == "source_documents")
    fragment = {
        "origin": {"registry": registry, "record": origin},
        "dependencies": [
            {"registry": owner, "record": indexes[owner][child]}
            for owner, child in semantic
        ],
        "source_spans": [indexes["source_spans"][item] for item in spans],
        "source_documents": [indexes["source_documents"][item] for item in sources],
    }
    return [child for _owner, child in semantic], spans, fragment


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


class _IndependentGraph:
    def __init__(
        self,
        projection: dict[str, Any],
        projection_sha256: str,
        context: dict[str, Any],
        context_sha256: str,
    ) -> None:
        self.projection = projection
        self.reading_id = projection["reading_id"]
        self.projection_sha256 = projection_sha256
        self.context = context
        self.context_sha256 = context_sha256
        self.indexes, self.owners = _indexes(projection)
        self.nodes: list[dict[str, Any]] = []
        self.contexts: list[tuple[str, dict[str, Any]]] = []
        self.context_index: dict[bytes, str] = {}

    def _context(self, bound: list[str], hypotheses: list[str], witnesses: list[str]) -> str:
        bound = _ordered_unique(bound)
        hypotheses = _ordered_unique(hypotheses)
        witnesses = _ordered_unique(witnesses)
        dependencies: set[str] = set()
        spans: set[str] = set()
        definitions = list(self.projection["definition_ids"])
        for registry, identifiers in (
            ("definitions", definitions), ("variables", bound),
            ("statements", hypotheses),
        ):
            for entity_id in identifiers:
                child_dependencies, child_spans, _fragment = _closure(
                    registry, entity_id, self.indexes
                )
                dependencies.add(entity_id)
                dependencies.update(child_dependencies)
                spans.update(child_spans)
        for fact in self.context["facts"]:
            dependencies.add(fact["origin_id"])
            dependencies.update(fact["dependency_ids"])
            spans.update(fact["span_ids"])
        value = {
            "reading_id": self.reading_id,
            "normalized_context_sha256": self.context_sha256,
            "definition_ids": definitions,
            "assumption_fact_sha256s": [item["fact_sha256"] for item in self.context["facts"]],
            "bound_variable_ids": bound,
            "local_hypothesis_statement_ids": hypotheses,
            "witness_placeholder_ids": witnesses,
            "dependency_ids": sorted(dependencies.intersection(self.owners)),
            "source_span_ids": sorted(spans),
            "mathematical_authority": False,
        }
        raw = _canonical(value)
        if raw in self.context_index:
            return self.context_index[raw]
        digest = _sha(raw)
        self.context_index[raw] = digest
        self.contexts.append((digest, value))
        return digest

    def _reserve(
        self, *, root_goal_id: str, parent_id: str | None, rule_id: str,
        kind: str, goal_mode: str, statement_id: str, bound: list[str],
        hypotheses: list[str], witnesses: list[str], node_witnesses: list[str] | None = None,
        prerequisites: list[str] | None = None, alternative_group_id: str | None = None,
        alternative_index: int | None = None, component: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None, supported: bool = True,
    ) -> dict[str, Any]:
        obligation_id = f"obligation_{len(self.nodes):06d}"
        dependencies, spans, fragment = _closure("statements", statement_id, self.indexes)
        if component is not None:
            fragment = {"statement_fragment": fragment, "component": component}
        statement = self.indexes["statements"][statement_id]
        node = {
            "obligation_id": obligation_id,
            "ordinal": len(self.nodes),
            "reading_id": self.reading_id,
            "root_goal_id": root_goal_id,
            "parent_obligation_id": parent_id,
            "rule_id": rule_id,
            "kind": kind,
            "goal_mode": goal_mode,
            "statement_id": statement_id,
            "relation_id": statement.get("relation_id") if statement["kind"] == "relation" else None,
            "statement_fragment_sha256": _sha(_canonical(fragment)),
            "source_span_ids": spans,
            "dependency_ids": dependencies,
            "local_context_sha256": self._context(bound, hypotheses, witnesses),
            "child_obligation_ids": [],
            "prerequisite_obligation_ids": prerequisites or [],
            "alternative_group_id": alternative_group_id,
            "alternative_index": alternative_index,
            "witness_placeholder_ids": witnesses if node_witnesses is None else node_witnesses,
            "payload": payload if payload is not None else {"statement": statement},
            "supported": supported,
            "mathematical_authority": False,
        }
        self.nodes.append(node)
        return node

    def _statement(
        self, statement_id: str, goal_mode: str, root_goal_id: str,
        parent_id: str | None, bound: list[str], hypotheses: list[str],
        witnesses: list[str], alternative_group_id: str | None = None,
        alternative_index: int | None = None, root_goal: dict[str, Any] | None = None,
    ) -> str:
        statement = self.indexes["statements"][statement_id]
        component = None if root_goal is None else {"root_goal": root_goal}
        payload = {"statement": statement}
        if root_goal is not None:
            payload["root_goal"] = root_goal
        if goal_mode != "prove":
            selected = MODE_RULES.get(goal_mode)
            rule_id, kind, supported = (
                (*selected, True) if selected is not None
                else ("mh.obligation.unsupported", "unsupported", False)
            )
            return self._reserve(
                root_goal_id=root_goal_id, parent_id=parent_id, rule_id=rule_id,
                kind=kind, goal_mode=goal_mode, statement_id=statement_id,
                bound=bound, hypotheses=hypotheses, witnesses=witnesses,
                alternative_group_id=alternative_group_id,
                alternative_index=alternative_index, component=component,
                payload=payload, supported=supported,
            )["obligation_id"]
        match = statement.get("operator") if statement["kind"] == "logical" else (
            statement.get("quantifier") if statement["kind"] == "quantified" else None
        )
        selected = PROVE_RULES.get((statement["kind"], match))
        rule_id, kind, supported = selected or (
            "mh.obligation.unsupported", "unsupported", False,
        )
        node = self._reserve(
            root_goal_id=root_goal_id, parent_id=parent_id, rule_id=rule_id,
            kind=kind, goal_mode=goal_mode, statement_id=statement_id,
            bound=bound, hypotheses=hypotheses, witnesses=witnesses,
            alternative_group_id=alternative_group_id,
            alternative_index=alternative_index, component=component,
            payload=payload, supported=supported,
        )
        if not supported or statement["kind"] in {"truth", "relation"}:
            return node["obligation_id"]
        if statement["kind"] == "logical":
            operator = statement["operator"]
            operands = statement["operand_statement_ids"]
            if operator == "not":
                return node["obligation_id"]
            if operator in {"and", "or"}:
                group = f"alternative_{node['obligation_id']}" if operator == "or" else None
                for index, child_statement in enumerate(operands):
                    child = self._statement(
                        child_statement, goal_mode, root_goal_id, node["obligation_id"],
                        bound, hypotheses, witnesses, group,
                        index if group is not None else None,
                    )
                    node["child_obligation_ids"].append(child)
                return node["obligation_id"]
            if operator == "implies":
                antecedent, consequent = operands
                child = self._statement(
                    consequent, goal_mode, root_goal_id, node["obligation_id"],
                    bound, [*hypotheses, antecedent], witnesses,
                )
                node["child_obligation_ids"].append(child)
                return node["obligation_id"]
            if operator == "iff":
                left, right = operands
                for direction, (antecedent, consequent) in enumerate(((left, right), (right, left))):
                    direction_context = [*hypotheses, antecedent]
                    wrapper = self._reserve(
                        root_goal_id=root_goal_id, parent_id=node["obligation_id"],
                        rule_id="mh.obligation.logical.implies", kind="implication",
                        goal_mode=goal_mode, statement_id=consequent, bound=bound,
                        hypotheses=direction_context, witnesses=witnesses,
                        component={
                            "biconditional_statement_id": statement_id,
                            "direction": direction,
                            "antecedent_statement_id": antecedent,
                            "consequent_statement_id": consequent,
                        },
                        payload={
                            "direction": direction,
                            "antecedent_statement_id": antecedent,
                            "consequent_statement_id": consequent,
                        },
                    )
                    child = self._statement(
                        consequent, goal_mode, root_goal_id, wrapper["obligation_id"],
                        bound, direction_context, witnesses,
                    )
                    wrapper["child_obligation_ids"].append(child)
                    node["child_obligation_ids"].append(wrapper["obligation_id"])
                return node["obligation_id"]
        if statement["kind"] == "quantified":
            variables = statement["variable_ids"]
            body = statement["body_statement_id"]
            if statement["quantifier"] == "forall":
                child = self._statement(
                    body, goal_mode, root_goal_id, node["obligation_id"],
                    [*bound, *variables], hypotheses, witnesses,
                )
                node["child_obligation_ids"].append(child)
                return node["obligation_id"]
            placeholders = [
                f"witness_{node['obligation_id']}_{variable_id}" for variable_id in variables
            ]
            node["witness_placeholder_ids"] = placeholders
            construction = self._reserve(
                root_goal_id=root_goal_id, parent_id=node["obligation_id"],
                rule_id="mh.obligation.component.witness-construction",
                kind="witness_construction", goal_mode=goal_mode,
                statement_id=statement_id, bound=bound, hypotheses=hypotheses,
                witnesses=witnesses, node_witnesses=placeholders,
                component={"component": "witness_construction", "variable_ids": variables},
                payload={"variable_ids": variables, "placeholder_ids": placeholders},
            )
            witness_context = [*witnesses, *placeholders]
            verification = self._reserve(
                root_goal_id=root_goal_id, parent_id=node["obligation_id"],
                rule_id="mh.obligation.component.witness-verification",
                kind="witness_verification", goal_mode=goal_mode,
                statement_id=body, bound=[*bound, *variables], hypotheses=hypotheses,
                witnesses=witness_context, prerequisites=[construction["obligation_id"]],
                component={
                    "component": "witness_verification",
                    "quantified_statement_id": statement_id,
                    "placeholder_ids": placeholders,
                },
                payload={"body_statement_id": body, "placeholder_ids": placeholders},
            )
            child = self._statement(
                body, goal_mode, root_goal_id, verification["obligation_id"],
                [*bound, *variables], hypotheses, witness_context,
            )
            verification["child_obligation_ids"].append(child)
            node["child_obligation_ids"].extend(
                [construction["obligation_id"], verification["obligation_id"]]
            )
            if statement["quantifier"] == "exists_unique":
                uniqueness = self._reserve(
                    root_goal_id=root_goal_id, parent_id=node["obligation_id"],
                    rule_id="mh.obligation.component.uniqueness", kind="uniqueness",
                    goal_mode=goal_mode, statement_id=statement_id,
                    bound=[*bound, *variables], hypotheses=hypotheses,
                    witnesses=witness_context,
                    prerequisites=[construction["obligation_id"]],
                    component={"component": "uniqueness", "placeholder_ids": placeholders},
                    payload={"original_statement_id": statement_id, "placeholder_ids": placeholders},
                )
                node["child_obligation_ids"].append(uniqueness["obligation_id"])
        return node["obligation_id"]

    def _strategies(self, node: dict[str, Any]) -> list[dict[str, Any]]:
        relation_values = []
        if node["relation_id"] is not None:
            relation_values.append(self.indexes["relations"][node["relation_id"]]["kind"])
        domain_kinds: set[str] = set()
        carriers: set[str] = set()
        for entity_id in node["dependency_ids"]:
            domain = self.indexes["domains"].get(entity_id)
            if domain is not None:
                domain_kinds.add(domain["kind"])
                if domain["kind"] == "builtin":
                    carriers.add(domain["name"])
        available = {
            "obligation_kind": [node["kind"]],
            "goal_mode": [node["goal_mode"]],
            "relation_kind": relation_values,
            "domain_kind": sorted(domain_kinds),
            "builtin_carrier": sorted(carriers),
        }
        matches = []
        for strategy_id, match_rule_id, axis, values, reason in STRATEGIES:
            matched = next((item for item in values if item in available[axis]), None)
            if matched is not None:
                matches.append({
                    "strategy_id": strategy_id, "match_rule_id": match_rule_id,
                    "reason_code": reason, "matched_value": matched,
                    "prerequisite_obligation_ids": node["prerequisite_obligation_ids"],
                    "guarantees_success": False, "mathematical_authority": False,
                })
        return matches

    def build(self) -> dict[str, Any]:
        roots = []
        for goal_id in self.projection["goal_ids"]:
            goal = self.indexes["goals"][goal_id]
            roots.append(self._statement(
                goal["statement_id"], goal["mode"], goal_id, None, [], [], [],
                root_goal=goal,
            ))
        obligations = []
        edges = []
        for node in self.nodes:
            value = {
                **node,
                "status": (
                    "unsupported" if not node["supported"]
                    else "choice_required" if node["kind"] == "disjunction"
                    else "waiting" if node["child_obligation_ids"] or node["prerequisite_obligation_ids"]
                    else "ready"
                ),
                "admissible_strategies": self._strategies(node),
            }
            value["obligation_sha256"] = _sha(_canonical(value))
            obligations.append(value)
            for child in value["child_obligation_ids"]:
                edges.append({
                    "ordinal": len(edges), "from_obligation_id": value["obligation_id"],
                    "to_obligation_id": child, "kind": "child",
                })
            for prerequisite in value["prerequisite_obligation_ids"]:
                edges.append({
                    "ordinal": len(edges), "from_obligation_id": value["obligation_id"],
                    "to_obligation_id": prerequisite, "kind": "prerequisite",
                })
        return {
            "reading_id": self.reading_id,
            "projection_sha256": self.projection_sha256,
            "normalized_context_sha256": self.context_sha256,
            "decomposition_catalogue_sha256": ARTIFACTS[Path("docs/obligations/proof-obligation-rules-v1.json")],
            "strategy_catalogue_sha256": ARTIFACTS[Path("docs/obligations/proof-strategy-catalogue-v1.json")],
            "goal_ids": self.projection["goal_ids"],
            "root_obligation_ids": roots,
            "obligations": obligations,
            "obligation_sha256s": [item["obligation_sha256"] for item in obligations],
            "local_contexts": [
                {"local_context_sha256": digest, "context": context}
                for digest, context in self.contexts
            ],
            "edges": edges,
            "unsupported_obligation_ids": [
                item["obligation_id"] for item in obligations if not item["supported"]
            ],
            "choice_required_obligation_ids": [
                item["obligation_id"] for item in obligations
                if item["status"] == "choice_required"
            ],
            "mathematical_authority": False,
        }


def _verify_result(validators: dict[str, Any]) -> dict[str, object]:
    input_bytes = _domain_bytes(_rich_problem())
    result = production.decompose_proof_obligations(input_bytes)
    if result.status != "decomposed":
        _fail(f"production rejected valid fixture: {result.diagnostics}")
    raw = production.proof_obligation_result_bytes(result)
    value = json.loads(raw)
    if validators:
        validators["proof-obligation-result-v1.schema.json"].validate(value)
    if raw != _canonical(value):
        _fail("result bytes are noncanonical")
    if value["input_result_sha256"] != _sha(input_bytes):
        _fail("input result identity drift")
    if _canonical(value["domain_assumption_result"]) != input_bytes:
        _fail("embedded domain result bytes drift")
    domain_value = value["domain_assumption_result"]
    readings_candidates = {
        item["reading_id"]: item
        for item in domain_value["readings_result"]["candidates"]
    }
    context_candidates = {
        item["reading_id"]: item for item in domain_value["candidates"]
    }
    expected_ids = sorted(context_candidates)
    if [item["reading_id"] for item in value["candidates"]] != expected_ids:
        _fail("candidate membership or order drift")
    obligations = 0
    contexts = 0
    strategies = 0
    choices = 0
    witnesses = 0
    for candidate in value["candidates"]:
        reading_id = candidate["reading_id"]
        upstream = readings_candidates[reading_id]
        normalized = context_candidates[reading_id]
        expected = _IndependentGraph(
            upstream["projection"], upstream["projection_sha256"],
            normalized["context"], normalized["context_sha256"],
        ).build()
        if candidate["graph"] != expected:
            _fail(f"{reading_id}: independently recomputed graph drift")
        if candidate["graph_sha256"] != _sha(_canonical(expected)):
            _fail(f"{reading_id}: independently recomputed graph identity drift")
        if validators:
            validators["proof-obligation-graph-v1.schema.json"].validate(expected)
            for item in expected["obligations"]:
                validators["proof-obligation-v1.schema.json"].validate(item)
            for item in expected["local_contexts"]:
                validators["proof-obligation-local-context-v1.schema.json"].validate(item["context"])
        obligations += len(expected["obligations"])
        contexts += len(expected["local_contexts"])
        strategies += sum(len(item["admissible_strategies"]) for item in expected["obligations"])
        choices += len(expected["choice_required_obligation_ids"])
        witnesses += sum(len(item["witness_placeholder_ids"]) for item in expected["obligations"])
    if value["ambiguity_status"] != "unresolved" or value["selected_reading_id"] is not None:
        _fail("unresolved alternatives were selected or erased")
    if value["mathematical_authority"] is not False:
        _fail("mathematical authority drift")
    parsed = production.parse_proof_obligation_result(raw)
    if production.proof_obligation_result_bytes(parsed) != raw:
        _fail("strict replay drift")
    return {
        "candidates": len(value["candidates"]),
        "choices": choices,
        "contexts": contexts,
        "input_sha256": _sha(input_bytes),
        "obligations": obligations,
        "result_bytes": len(raw),
        "result_sha256": _sha(raw),
        "strategies": strategies,
        "witness_placeholders": witnesses,
    }


def _negative_checks(validators: dict[str, Any]) -> int:
    count = 0
    for invalid in (None, "x", bytearray(), memoryview(b"{}"), b"{}"):
        result = production.decompose_proof_obligations(invalid)  # type: ignore[arg-type]
        if result.status not in {"invalid", "exhausted"} or result.candidates:
            _fail(f"invalid input produced graph: {type(invalid).__name__}")
        if result.input_result_sha256 is not None or result.domain_result_bytes is not None:
            _fail("failed result leaked a partial identity")
        count += 1
    input_bytes = _domain_bytes(_rich_problem())
    valid = production.decompose_proof_obligations(input_bytes)
    raw = production.proof_obligation_result_bytes(valid)
    for mutate in (
        lambda value: value["candidates"][0]["graph"]["obligations"][0].update(status="unsupported"),
        lambda value: value["candidates"][0]["graph"]["edges"][0].update(to_obligation_id="obligation_999999"),
        lambda value: value["candidates"][0]["graph"].update(root_obligation_ids=[]),
        lambda value: value["candidates"][0]["graph"]["local_contexts"][0]["context"].update(reading_id="reading_secondary"),
        lambda value: value["candidates"][0]["graph"]["obligations"][0]["admissible_strategies"].append({
            "strategy_id": "mh.strategy.fabricated", "match_rule_id": "mh.strategy-match.fake",
            "reason_code": "FAKE", "matched_value": "fake",
            "prerequisite_obligation_ids": [], "guarantees_success": False,
            "mathematical_authority": False,
        }),
    ):
        forged = json.loads(raw)
        mutate(forged)
        try:
            production.parse_proof_obligation_result(_canonical(forged))
        except production.ProofObligationValidationError:
            count += 1
        else:
            _fail("forged graph passed strict replay")
    noncanonical = (
        json.dumps(json.loads(raw), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    for forged in (raw.rstrip(b"\n"), noncanonical):
        try:
            production.parse_proof_obligation_result(forged)
        except production.ProofObligationValidationError:
            count += 1
        else:
            _fail("noncanonical result passed strict replay")
    duplicate = raw.replace(b'{"ambiguity_status"', b'{"ambiguity_status":null,"ambiguity_status"', 1)
    try:
        production.parse_proof_obligation_result(duplicate)
    except production.ProofObligationValidationError:
        count += 1
    else:
        _fail("duplicate JSON key passed strict replay")
    if validators:
        forged = json.loads(raw)
        forged["unknown"] = None
        try:
            validators["proof-obligation-result-v1.schema.json"].validate(forged)
        except ValidationError:
            count += 1
        else:
            _fail("closed result schema accepted an unknown field")
    else:
        forged = json.loads(raw)
        forged["unknown"] = None
        expected_fields = set(json.loads(raw))
        if set(forged) != expected_fields | {"unknown"}:
            _fail("dependency-minimal closed-field control drift")
        count += 1
    failed_upstream = normalize_domain_assumptions(b"{}\n")
    failed = production.decompose_proof_obligations(domain_assumption_result_bytes(failed_upstream))
    if failed.status != "invalid" or failed.candidates:
        _fail("failed upstream normalization did not fail closed")
    return count + 1


def _report() -> dict[str, object]:
    validators = _identity_checks()
    fixture = _verify_result(validators)
    test_paths = sorted((ROOT / "tests/proof_obligations").glob("test_*.py"))
    report: dict[str, object] = {
        "catalogues": {
            "decomposition_sha256": ARTIFACTS[Path("docs/obligations/proof-obligation-rules-v1.json")],
            "strategy_sha256": ARTIFACTS[Path("docs/obligations/proof-strategy-catalogue-v1.json")],
        },
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "negative_controls": _negative_checks(validators),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schemas": {
            path.name: digest for path, digest in ARTIFACTS.items()
            if path.name.endswith(".schema.json")
        },
        "source": _source_closure(),
        "summary": {
            "candidates": fixture["candidates"],
            "contexts": fixture["contexts"],
            "mathematical_authority": False,
            "obligations": fixture["obligations"],
            "status": "passed",
            "strategies": fixture["strategies"],
        },
        "tests": {
            path.relative_to(ROOT).as_posix(): _sha(path.read_bytes()) for path in test_paths
        },
        "validator_sha256": _sha((ROOT / "tools/validate_proof_obligations.py").read_bytes()),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"proof-obligations: report updated: {target}")
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
        OSError, UnicodeError, json.JSONDecodeError, ValidationError,
        ProofObligationReportError,
    ) as exc:
        print(f"proof-obligations: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "proof-obligations: PASS "
        f"(candidates={summary['candidates']}, obligations={summary['obligations']}, "
        f"contexts={summary['contexts']}, strategies={summary['strategies']}, "
        f"negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
