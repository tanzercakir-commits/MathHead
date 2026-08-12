#!/usr/bin/env python3
"""Independently validate the MH-045 unsupported-explanation boundary."""

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
    from referencing import Registry, Resource
except ModuleNotFoundError:  # Governed dependency-minimal status profile.
    Draft202012Validator = None  # type: ignore[assignment,misc]
    Registry = Resource = None  # type: ignore[assignment,misc]


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import unsupported_explanations as production  # noqa: E402
from mathhead.canonical_normalization import (  # noqa: E402
    canonical_normalization_result_bytes,
    normalize_canonical_obligations,
)
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


CONTRACT_ID = "MH-C-UNSUPPORTED-EXPLANATION-001"
CONTRACT_SHA256 = "35248c92eea2253c153b4cc0d1be2cffead624c417c74ca5562696e8d07786f9"
CATALOGUE_SHA256 = "902c5ed06273b8372794e20f2309861d70002455b7b3389a0054e3627681848e"
SOURCE = Path("src/mathhead/unsupported_explanations.py")
DEFAULT_REPORT = Path("docs/explanations/reports/unsupported-explanations-v1.json")
REPORT_SCHEMA = "mathhead.unsupported-explanation-validation-report.v1"
ARTIFACTS = {
    Path("docs/contracts/schemas/unsupported-target-v1.schema.json"): "3650aa309cab01e6dc63c4cc5cc3aa07f92caa3a7cef879fc2a70e0082c68cfc",
    Path("docs/contracts/schemas/owned-fragment-v1.schema.json"): "6c678c9cf115fc99de34f1f38c45b5bc6d7e8c6ef957d29f811659423687d3e9",
    Path("docs/contracts/schemas/formalization-step-v1.schema.json"): "142e609977e9cdb0d6fe37a26831ea34c146ad0c07e7245467df667a4f0bd601",
    Path("docs/contracts/schemas/unsupported-explanation-v1.schema.json"): "17c6fe18e2b0c545c922d049e330e8ad18e0a94876a7b5613a7001bfaa4e6973",
    Path("docs/contracts/schemas/unsupported-explanation-catalogue-v1.schema.json"): "6131d3e5c9d0244ba79422fba80549a0d473651f46e9e7a8448e6b52455d234e",
    Path("docs/contracts/schemas/unsupported-explanation-result-v1.schema.json"): "b2e490c657737519d57b6e9bca30a095790c167e50feb36d9c79a03335ce8051",
    Path("docs/explanations/unsupported-explanation-catalogue-v1.json"): CATALOGUE_SHA256,
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


class UnsupportedExplanationReportError(RuntimeError):
    """An independent identity, inventory, source, or report check failed."""


def _fail(detail: str) -> NoReturn:
    raise UnsupportedExplanationReportError(detail)


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


def _fixture_problem() -> dict[str, Any]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"
    problem["goals"][0]["statement_id"] = "statement_body"
    problem["statements"] = [problem["statements"][0]]
    problem["variables"].append({
        "id": "variable_q", "name": "q", "domain_id": "domain_integer",
        "role": "bound", "span_ids": [],
    })
    problem["expressions"].append({
        "id": "expression_q", "kind": "variable", "domain_id": "domain_integer",
        "variable_id": "variable_q", "span_ids": [],
    })
    problem["relations"].extend([
        {
            "id": "relation_opaque", "kind": "predicate",
            "predicate": "org.example.unknown.property",
            "operand_expr_ids": ["expression_x"], "span_ids": [],
        },
        {
            "id": "relation_q", "kind": "equal",
            "operand_expr_ids": ["expression_q", "expression_q"], "span_ids": [],
        },
    ])
    problem["statements"].extend([
        {
            "id": "statement_opaque", "kind": "relation",
            "relation_id": "relation_opaque", "span_ids": [],
        },
        {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        {
            "id": "statement_logical", "kind": "logical", "operator": "and",
            "operand_statement_ids": ["statement_body", "statement_true"],
            "span_ids": [],
        },
        {
            "id": "statement_q", "kind": "relation",
            "relation_id": "relation_q", "span_ids": [],
        },
        {
            "id": "statement_quantified", "kind": "quantified",
            "quantifier": "exists", "variable_ids": ["variable_q"],
            "body_statement_id": "statement_q", "span_ids": [],
        },
    ])
    problem["assumptions"] = [
        {
            "id": "assumption_logical", "statement_id": "statement_logical",
            "role": "given", "span_ids": [],
        },
        {
            "id": "assumption_opaque", "statement_id": "statement_opaque",
            "role": "side_condition", "span_ids": [],
        },
        {
            "id": "assumption_quantified", "statement_id": "statement_quantified",
            "role": "domain_constraint", "span_ids": [],
        },
    ]
    problem["readings"][0]["assumption_ids"] = [
        "assumption_logical", "assumption_opaque", "assumption_quantified",
    ]
    return problem


def _normalization_bytes(problem: dict[str, Any]) -> bytes:
    _sort(problem)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": problem})
    if intake.status != "accepted":
        _fail(f"fixture intake failed: {intake.reason_code}")
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    domain = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    proof = decompose_proof_obligations(domain_assumption_result_bytes(domain))
    normalized = normalize_canonical_obligations(proof_obligation_result_bytes(proof))
    if normalized.status != "normalized":
        _fail(f"fixture normalization failed: {normalized.reason_code}")
    return canonical_normalization_result_bytes(normalized)


def _identity_checks() -> dict[str, Any]:
    expected = {
        **ARTIFACTS,
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
    }
    for relative, digest in expected.items():
        if _sha((ROOT / relative).read_bytes()) != digest:
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
        or production.CATALOGUE_SHA256 != CATALOGUE_SHA256
    ):
        _fail("production contract or catalogue binding drift")

    schemas = []
    for path in sorted((ROOT / "docs/contracts/schemas").glob("*.schema.json")):
        schema = json.loads(path.read_bytes())
        if "$id" in schema:
            schemas.append(schema)
    selected_names = {
        path.name for path in ARTIFACTS if path.name.endswith(".schema.json")
    }
    selected = {
        schema["$id"].rsplit("/", 1)[-1]: schema
        for schema in schemas
        if schema["$id"].rsplit("/", 1)[-1] in selected_names
    }
    if set(selected) != selected_names:
        _fail("unsupported-explanation schema identifier drift")
    for schema in selected.values():
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail("closed Draft 2020-12 schema root drift")

    catalogue = json.loads(
        (ROOT / "docs/explanations/unsupported-explanation-catalogue-v1.json").read_bytes()
    )
    entries = catalogue["entries"]
    priorities = [item["priority"] for item in entries]
    rule_ids = [item["rule_id"] for item in entries]
    if priorities != sorted(set(priorities)) or len(rule_ids) != len(set(rule_ids)):
        _fail("catalogue priority or identity uniqueness drift")
    if (
        sum(item["generic_fallback"] for item in entries) != 1
        or not entries[-1]["generic_fallback"]
        or entries[-1]["owner_boundary"] != "none"
        or catalogue["mathematical_authority"] is not False
    ):
        _fail("catalogue fallback or authority drift")
    for entry in entries:
        if entry["parameter_names"] != sorted(entry["parameter_names"]):
            _fail("catalogue parameter order drift")
        for name in entry["parameter_names"]:
            placeholder = "{" + name + "}"
            counts = (
                entry["summary_template"].count(placeholder),
                entry["detail_template"].count(placeholder),
            )
            if max(counts) > 1 or sum(counts) < 1:
                _fail("catalogue placeholder drift")

    validators: dict[str, Any] = {}
    if Draft202012Validator is not None and Registry is not None and Resource is not None:
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in schemas
        )
        validators = {
            name: Draft202012Validator(schema, registry=registry)
            for name, schema in selected.items()
        }
        for validator in validators.values():
            validator.check_schema(validator.schema)
        validators["unsupported-explanation-catalogue-v1.schema.json"].validate(
            catalogue
        )
    return {
        "catalogue": catalogue,
        "rule_count": len(entries),
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


def _independent_parameters(
    source: dict[str, Any], rule: dict[str, Any],
) -> dict[str, object]:
    value = source["value"] if source["surface"] == "normal_form" else source["semantic_value"]
    rule_id = rule["rule_id"]
    if rule_id.endswith("opaque-predicate-assumption"):
        return {
            "arity": len(value["relation"]["operands"]),
            "predicate_id": value["relation"]["predicate"],
        }
    if rule_id.endswith("opaque-relation-assumption"):
        return {"relation_kind": value["relation"]["kind"]}
    if rule_id.endswith("logical-assumption"):
        return {"operator": value["statement"]["operator"]}
    if rule_id.endswith("quantified-assumption"):
        return {
            "binder_count": len(value["statement"]["variables"]),
            "quantifier": value["statement"]["quantifier"],
        }
    if rule_id.endswith("unsupported-obligation"):
        return {"goal_mode": source["goal_mode"], "obligation_id": source["source_ref"]}
    return {"source_ref": source["source_ref"]}


def _select_rule(source: dict[str, Any], catalogue: dict[str, Any]) -> dict[str, Any]:
    fact_kind = source.get("value", {}).get("kind")
    matches = []
    for rule in catalogue["entries"]:
        if rule["generic_fallback"]:
            continue
        if rule["match_surface"] != source["surface"]:
            continue
        if rule["match_form_kind"] is not None and rule["match_form_kind"] != source.get("form_kind"):
            continue
        if rule["match_fact_kind"] is not None and rule["match_fact_kind"] != fact_kind:
            continue
        if rule["match_obligation_kind"] is not None and rule["match_obligation_kind"] != source.get("kind"):
            continue
        matches.append(rule)
    if len(matches) > 1:
        _fail("independent catalogue selection was ambiguous")
    return matches[0] if matches else catalogue["entries"][-1]


def _render(template: str, parameters: dict[str, object]) -> str:
    value = template
    for name, parameter in sorted(parameters.items()):
        value = value.replace("{" + name + "}", str(parameter))
    if "{" in value or "}" in value:
        _fail("independent rendering left a placeholder")
    return value


def _verify_result(
    validators: dict[str, Any], catalogue: dict[str, Any],
) -> dict[str, int]:
    normalization_bytes = _normalization_bytes(_fixture_problem())
    normalization = json.loads(normalization_bytes)
    result = production.explain_unsupported_constructs(normalization_bytes)
    raw_bytes = production.unsupported_explanation_result_bytes(result)
    raw = json.loads(raw_bytes)
    result_validator = validators.get("unsupported-explanation-result-v1.schema.json")
    if result_validator is not None:
        result_validator.validate(raw)
    if (
        raw["status"] != "explained"
        or raw["reason_code"] != "EXPLAINED"
        or raw["input_result_sha256"] != _sha(normalization_bytes)
        or raw["normalization_result"] != normalization
        or raw["ambiguity_status"] != normalization["ambiguity_status"]
        or raw["selected_reading_id"] != normalization["selected_reading_id"]
        or raw["diagnostics"]
        or raw["mathematical_authority"] is not False
    ):
        _fail("top-level exact preservation drift")
    if production.parse_unsupported_explanation_result(raw_bytes) != result:
        _fail("strict production replay drift")

    target_count = 0
    exact_count = 0
    fallback_count = 0
    for source_candidate, candidate in zip(
        normalization["candidates"], raw["candidates"], strict=True
    ):
        sources = []
        for form in source_candidate["normal_forms"]:
            if not form["supported"]:
                sources.append({**form, "surface": "normal_form"})
        for obligation in source_candidate["obligations"]:
            if not obligation["supported"]:
                sources.append({
                    **obligation,
                    "surface": "obligation",
                    "source_ref": obligation["source_obligation_id"],
                })
        if len(sources) != len(candidate["targets"]) or len(sources) != len(candidate["explanations"]):
            _fail("unsupported occurrence cardinality drift")
        if (
            candidate["reading_id"] != source_candidate["reading_id"]
            or candidate["source_graph_sha256"] != source_candidate["source_graph_sha256"]
            or candidate["semantic_graph_sha256"] != source_candidate["semantic_graph_sha256"]
            or candidate["unsupported_semantic_sha256s"] != source_candidate["unsupported_semantic_sha256s"]
        ):
            _fail("candidate identity preservation drift")
        for ordinal, (source, target, explanation) in enumerate(
            zip(sources, candidate["targets"], candidate["explanations"], strict=True)
        ):
            rule = _select_rule(source, catalogue)
            parameters = _independent_parameters(source, rule)
            source_sha = source["semantic_sha256"]
            cause_sha = _sha(_canonical({
                "reading_id": candidate["reading_id"],
                "construct_code": rule["construct_code"],
                "construct_parameters": parameters,
                "source_semantic_sha256": source_sha,
            }))
            if (
                target["target_id"] != f"target_{ordinal:08d}"
                or target["ordinal"] != ordinal
                or target["reading_id"] != candidate["reading_id"]
                or target["surface"] != source["surface"]
                or target["source_semantic_sha256"] != source_sha
                or target["construct_code"] != rule["construct_code"]
                or target["construct_parameters"] != parameters
                or target["cause_sha256"] != cause_sha
                or target["mathematical_authority"] is not False
            ):
                _fail(f"independent target projection drift at {ordinal}")
            summary = _render(rule["summary_template"], parameters)
            detail = _render(rule["detail_template"], parameters)
            if (
                explanation["explanation_id"] != f"explanation_{ordinal:08d}"
                or explanation["target_id"] != target["target_id"]
                or explanation["cause_sha256"] != cause_sha
                or explanation["catalogue_rule_id"] != rule["rule_id"]
                or explanation["summary"] != summary
                or explanation["detail"] != detail
                or explanation["formalization_step"]["automatic"] is not False
                or explanation["formalization_step"]["requires_user_confirmation"] is not True
                or explanation["mathematical_authority"] is not False
            ):
                _fail(f"independent explanation projection drift at {ordinal}")
            explanation_preimage = dict(explanation)
            explanation_preimage["explanation_sha256"] = None
            if explanation["explanation_sha256"] != _sha(_canonical(explanation_preimage)):
                _fail("independent explanation identity drift")
            target_count += 1
            if rule["generic_fallback"]:
                fallback_count += 1
            else:
                exact_count += 1
        candidate_preimage = dict(candidate)
        candidate_preimage["explanation_set_sha256"] = None
        if candidate["explanation_set_sha256"] != _sha(_canonical(candidate_preimage)):
            _fail("independent explanation-set identity drift")
    result_preimage = dict(raw)
    result_preimage["result_sha256"] = None
    if raw["result_sha256"] != _sha(_canonical(result_preimage)):
        _fail("independent result identity drift")
    return {
        "candidates": len(raw["candidates"]),
        "exact_matches": exact_count,
        "fallback_matches": fallback_count,
        "targets": target_count,
    }


def _negative_checks(validators: dict[str, Any]) -> int:
    controls = 0
    for value in (None, bytearray(), memoryview(b"{}"), b"{}", b"{}\n"):
        result = production.explain_unsupported_constructs(value)  # type: ignore[arg-type]
        if not (
            result.status in {"invalid", "exhausted"}
            and result.input_result_sha256 is None
            and result.normalization_result_bytes is None
            and result.candidates == ()
            and result.result_sha256 is None
        ):
            _fail("invalid input returned a partial explanation artifact")
        controls += 1
    result = production.explain_unsupported_constructs(
        _normalization_bytes(_fixture_problem())
    )
    raw = production.unsupported_explanation_result_bytes(result)
    try:
        production.parse_unsupported_explanation_result(raw.rstrip(b"\n"))
    except production.UnsupportedExplanationValidationError:
        controls += 1
    else:
        _fail("strict parser accepted noncanonical framing")
    forged = json.loads(raw)
    forged["candidates"][0]["explanations"][0]["summary"] = "forged"
    forged["result_sha256"] = _sha(_canonical({**forged, "result_sha256": None}))
    try:
        production.parse_unsupported_explanation_result(_canonical(forged))
    except production.UnsupportedExplanationValidationError:
        controls += 1
    else:
        _fail("strict parser accepted repaired outer digest forgery")
    validator = validators.get("unsupported-explanation-result-v1.schema.json")
    if validator is not None:
        surplus = json.loads(raw)
        surplus["unexpected"] = True
        if not list(validator.iter_errors(surplus)):
            _fail("closed result schema accepted an unknown field")
    else:
        schema = json.loads(
            (ROOT / "docs/contracts/schemas/unsupported-explanation-result-v1.schema.json").read_bytes()
        )
        if schema.get("additionalProperties") is not False:
            _fail("dependency-minimal closed result schema control failed")
    return controls + 1


def _report() -> dict[str, object]:
    identities = _identity_checks()
    validators = identities.pop("validators")
    catalogue = identities.pop("catalogue")
    assert isinstance(validators, dict) and isinstance(catalogue, dict)
    fixture = _verify_result(validators, catalogue)
    test_paths = sorted((ROOT / "tests/unsupported_explanations").glob("test_*.py"))
    report: dict[str, object] = {
        "artifacts": {path.as_posix(): digest for path, digest in ARTIFACTS.items()},
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "identity_checks": identities,
        "negative_controls": _negative_checks(validators),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "source": _source_closure(),
        "summary": {
            **fixture,
            "mathematical_authority": False,
            "status": "passed",
        },
        "tests": {
            path.relative_to(ROOT).as_posix(): _sha(path.read_bytes())
            for path in test_paths
        },
        "validator_sha256": _sha(
            (ROOT / "tools/validate_unsupported_explanations.py").read_bytes()
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
        print(f"unsupported-explanations: report updated: {target}")
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
        UnsupportedExplanationReportError,
    ) as exc:
        print(f"unsupported-explanations: FAIL: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(
        "unsupported-explanations: PASS "
        f"(candidates={summary['candidates']}, targets={summary['targets']}, "
        f"exact={summary['exact_matches']}, fallback={summary['fallback_matches']}, "
        f"negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
