#!/usr/bin/env python3
"""Independently validate the accepted EngineResult v1 schema and semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from typing import Any, NoReturn, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 core profile.
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "MH-C-ENGINE-RESULT-001"
EXPECTED_CONTRACT_SHA256 = "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370"
SCHEMA_PATH = Path("docs/contracts/schemas/engine-result-v1.schema.json")
EXPECTED_SCHEMA_SHA256 = "4cd26ad69c6528a7553a429d06f224c79ae6b01b7d9cc0fa41ccb7c4d20cc948"
ROOT_FIELDS = {
    "schema",
    "result_id",
    "request",
    "replay",
    "provenance",
    "artifacts",
    "assessments",
    "execution",
    "budget",
    "diagnostics",
    "extensions",
}
TRUSTED_TIERS = {"checker_attested", "external_verified"}
TERMINAL_RESOURCE_OUTCOMES = {"cancelled", "exhausted", "truncated"}
RESOURCE_DIMENSIONS = {
    "wall_time_us",
    "cpu_time_us",
    "memory_bytes",
    "solver_calls",
    "generated_objects",
    "proof_bytes",
    "evidence_bytes",
    "output_bytes",
    "diagnostic_bytes",
    "nesting_depth",
}
SUPPORT_KINDS = {
    "value",
    "witness",
    "counterexample",
    "proof",
    "certificate",
    "evidence",
    "checker_result",
    "producer_result",
}
EVIDENCE_KINDS = {"proof", "certificate", "evidence"}
MAX_VALIDATION_SECONDS = 30.0
MAX_INPUT_BYTES = 67_108_864
MAX_CANONICAL_NODES = 4_000_000
MAX_CANONICAL_NESTING = 64
MAX_STRING_CODEPOINTS = 1_048_576
MAX_JSON_INTEGER = 9_007_199_254_740_991
MAX_ENTITIES = 100_000


class EngineResultValidationError(RuntimeError):
    """A classified schema, identity, reference, or trust validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise EngineResultValidationError(kind, path, detail)


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


def replay_basis_sha256(value: dict[str, Any]) -> str:
    replay = {key: item for key, item in value["replay"].items() if key != "basis_sha256"}
    basis = {
        "request": value["request"],
        "replay": replay,
        "provenance": value["provenance"],
    }
    return canonical_sha256(basis)


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
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            _fail("budget", str(path), "JSON input exceeds 67108864 bytes")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs(path))
    except EngineResultValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical EngineResult JSON")
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
    if "allOf" in schema:
        for candidate in schema["allOf"]:
            _schema_validate(value, candidate, root_schema, path)
    if "oneOf" in schema:
        matches = 0
        for candidate in schema["oneOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except EngineResultValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail("schema", path, f"must match exactly one tagged variant, matched {matches}")
        return
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except EngineResultValidationError:
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
        missing = sorted(set(schema.get("required", [])) - set(value))
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


def _shape_budget(value: Any, started: float) -> None:
    stack = [(value, 0, "$")]
    visited = 0
    while stack:
        item, depth, path = stack.pop()
        visited += 1
        if visited > MAX_CANONICAL_NODES:
            _fail("budget", path, "canonical value exceeds 4000000 nodes")
        if visited % 1024 == 0 and time.monotonic() - started > MAX_VALIDATION_SECONDS:
            _fail("budget", path, "validation exceeded 30 seconds")
        if depth > MAX_CANONICAL_NESTING:
            _fail("budget", path, "canonical value nesting exceeds 64")
        if isinstance(item, str) and len(item) > MAX_STRING_CODEPOINTS:
            _fail("budget", path, "string exceeds 1048576 code points")
        if isinstance(item, int) and not isinstance(item, bool) and abs(item) > MAX_JSON_INTEGER:
            _fail("budget", path, "JSON integer exceeds the portable exact range")
        if isinstance(item, list):
            stack.extend((child, depth + 1, f"{path}[{index}]") for index, child in enumerate(item))
        elif isinstance(item, dict):
            for key, child in item.items():
                if len(key) > MAX_STRING_CODEPOINTS:
                    _fail("budget", f"{path}.<key>", "string exceeds 1048576 code points")
                stack.append((child, depth + 1, f"{path}.{key}"))


def _require_sorted_unique(values: list[str], path: str) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        _fail("canonical", path, "values must be sorted and unique")


def _claim(identifier: str, owners: dict[str, str], owner: str, path: str) -> None:
    if identifier in owners:
        _fail("identity", path, f"ID already belongs to {owners[identifier]}")
    owners[identifier] = owner


def _validate_request_replay(value: dict[str, Any]) -> None:
    request = value["request"]
    _require_sorted_unique(request["candidate_reading_ids"], "$.request.candidate_reading_ids")
    if len(request["goal_ids"]) != len(set(request["goal_ids"])):
        _fail("canonical", "$.request.goal_ids", "goal order must not repeat an ID")
    selected = request["selected_reading_id"]
    status = value["execution"]["status"]
    if status == "ambiguous":
        if selected is not None:
            _fail("reading", "$.request.selected_reading_id", "ambiguous result selects a reading")
        if value["execution"]["reading_ids"] != request["candidate_reading_ids"]:
            _fail("reading", "$.execution.reading_ids", "ambiguity must preserve all candidates")
    elif selected is None or selected not in request["candidate_reading_ids"]:
        _fail("reading", "$.request.selected_reading_id", "execution requires a selected candidate")
    replay = value["replay"]
    if (replay["mode"] == "deterministic") != (replay["seed"] is None):
        _fail("replay", "$.replay.seed", "deterministic has no seed; seeded requires one")
    if replay["basis_sha256"] != replay_basis_sha256(value):
        _fail("replay", "$.replay.basis_sha256", "replay basis identity mismatch")


def _validate_provenance(
    value: dict[str, Any], owners: dict[str, str]
) -> dict[str, dict[str, Any]]:
    provenance = value["provenance"]
    producer = provenance["producer"]
    if producer["role"] != "producer":
        _fail("provenance", "$.provenance.producer.role", "root producer role is required")
    _claim(producer["component_id"], owners, "component", "$.provenance.producer.component_id")
    components = provenance["components"]
    ids = [component["component_id"] for component in components]
    _require_sorted_unique(ids, "$.provenance.components")
    registry = {producer["component_id"]: producer}
    for index, component in enumerate(components):
        path = f"$.provenance.components[{index}]"
        if component["role"] == "producer":
            _fail("provenance", f"{path}.role", "only the root component is producer")
        _claim(component["component_id"], owners, "component", f"{path}.component_id")
        registry[component["component_id"]] = component
    return registry


def _validate_artifacts(
    value: dict[str, Any],
    components: dict[str, dict[str, Any]],
    owners: dict[str, str],
) -> dict[str, dict[str, Any]]:
    artifacts = value["artifacts"]
    ids = [artifact["artifact_id"] for artifact in artifacts]
    _require_sorted_unique(ids, "$.artifacts")
    identities: set[tuple[str, str]] = set()
    registry: dict[str, dict[str, Any]] = {}
    for index, artifact in enumerate(artifacts):
        path = f"$.artifacts[{index}]"
        identifier = artifact["artifact_id"]
        _claim(identifier, owners, "artifact", f"{path}.artifact_id")
        producer_id = artifact["producer_component_id"]
        if producer_id not in components:
            _fail("reference", f"{path}.producer_component_id", "unknown producer component")
        identity = (artifact["kind"], artifact["sha256"])
        if identity in identities:
            _fail("identity", path, "duplicate kind and content identity")
        identities.add(identity)
        registry[identifier] = artifact
    return registry


def _require_artifacts(
    identifiers: list[str],
    artifacts: dict[str, dict[str, Any]],
    path: str,
    kinds: set[str] | None = None,
) -> list[dict[str, Any]]:
    _require_sorted_unique(identifiers, path)
    result = []
    for identifier in identifiers:
        artifact = artifacts.get(identifier)
        if artifact is None:
            _fail("reference", path, f"unknown artifact {identifier}")
        if kinds is not None and artifact["kind"] not in kinds:
            _fail("artifact", path, f"artifact {identifier} has incompatible kind")
        result.append(artifact)
    return result


def _validate_verification(
    verification: dict[str, Any],
    *,
    tier: str,
    support_ids: list[str],
    artifacts: dict[str, dict[str, Any]],
    components: dict[str, dict[str, Any]],
    producer_id: str,
    request: dict[str, Any],
    path: str,
) -> None:
    checker_id = verification["checker_component_id"]
    checker = components.get(checker_id)
    if checker is None:
        _fail("reference", f"{path}.checker_component_id", "unknown checker component")
    expected_role = "checker" if tier == "checker_attested" else "external"
    if checker["role"] != expected_role:
        _fail("epistemic", path, f"{tier} requires {expected_role} component")
    if checker_id == producer_id:
        _fail("epistemic", path, "producer cannot attest its own mathematical verdict")
    if (
        verification["checker_contract_id"] != checker["contract_id"]
        or verification["checker_contract_sha256"] != checker["contract_sha256"]
    ):
        _fail("epistemic", path, "checker contract does not match provenance")
    result_id = verification["checker_result_artifact_id"]
    result = artifacts.get(result_id)
    if result is None or result["kind"] != "checker_result":
        _fail("artifact", f"{path}.checker_result_artifact_id", "checker result kind is required")
    if result["producer_component_id"] != checker_id:
        _fail("epistemic", path, "checker result was not produced by the named checker")
    evidence_ids = verification["evidence_artifact_ids"]
    _require_artifacts(evidence_ids, artifacts, f"{path}.evidence_artifact_ids", EVIDENCE_KINDS)
    dependencies = verification["trust_dependency_sha256"]
    _require_sorted_unique(dependencies, f"{path}.trust_dependency_sha256")
    required = {
        checker["contract_sha256"],
        checker["implementation_sha256"],
        request["problem_ir_sha256"],
        request["theory_context_sha256"],
    }
    if not required <= set(dependencies):
        _fail("epistemic", path, "verification omits a required trust dependency")
    if not {result_id, *evidence_ids} <= set(support_ids):
        _fail("epistemic", path, "verification artifacts are absent from verdict support")


def _validate_verdict(
    verdict: dict[str, Any],
    *,
    artifacts: dict[str, dict[str, Any]],
    components: dict[str, dict[str, Any]],
    producer_id: str,
    request: dict[str, Any],
    path: str,
) -> None:
    status = verdict["status"]
    if status == "unsupported":
        _require_sorted_unique(verdict["feature_codes"], f"{path}.feature_codes")
        return
    support_ids = verdict["support_artifact_ids"]
    _require_artifacts(support_ids, artifacts, f"{path}.support_artifact_ids", SUPPORT_KINDS)
    if status == "unknown":
        return
    tier = verdict["epistemic_tier"]
    verification = verdict["verification"]
    if status == "bounded":
        directions = [bound["direction"] for bound in verdict["bounds"]]
        expected = sorted(directions, key={"lower": 0, "upper": 1}.get)
        if directions != expected or len(directions) != len(set(directions)):
            _fail("bound", f"{path}.bounds", "bounds must be lower then upper without duplicates")
        for index, bound in enumerate(verdict["bounds"]):
            artifact = artifacts.get(bound["value_artifact_id"])
            if artifact is None or artifact["kind"] != "value":
                _fail("artifact", f"{path}.bounds[{index}]", "bound requires a value artifact")
            if bound["value_artifact_id"] not in support_ids:
                _fail("artifact", f"{path}.bounds[{index}]", "bound value is absent from support")
        if verdict["exact"]:
            if len(verdict["bounds"]) != 2:
                _fail("bound", path, "exact bound requires both lower and upper")
            lower, upper = verdict["bounds"]
            if (
                not lower["inclusive"]
                or not upper["inclusive"]
                or lower["value_artifact_id"] != upper["value_artifact_id"]
            ):
                _fail("bound", path, "exact bounds require the same inclusive value")
            if tier not in TRUSTED_TIERS or verification is None:
                _fail("epistemic", path, "exactness requires independent verification")
        if tier == "producer_reported":
            if verification is not None:
                _fail(
                    "epistemic", path, "producer-reported bound cannot carry trusted verification"
                )
            return
        if verification is None:
            _fail("epistemic", path, "trusted bound requires verification")
    if tier not in TRUSTED_TIERS or verification is None:
        _fail("epistemic", path, "proof or refutation requires independent verification")
    if status == "proved" and not any(
        artifacts[identifier]["kind"] in {"proof", "certificate", "witness"}
        for identifier in support_ids
    ):
        _fail("artifact", path, "proved verdict requires proof, certificate, or witness support")
    if status == "refuted":
        counterexamples = verdict["counterexample_artifact_ids"]
        _require_artifacts(
            counterexamples,
            artifacts,
            f"{path}.counterexample_artifact_ids",
            {"counterexample"},
        )
        if not set(counterexamples) <= set(support_ids):
            _fail("artifact", path, "counterexample is absent from verdict support")
        if not counterexamples and not any(
            artifacts[identifier]["kind"] in {"proof", "certificate"} for identifier in support_ids
        ):
            _fail("artifact", path, "refutation requires a counterexample or proof of negation")
    _validate_verification(
        verification,
        tier=tier,
        support_ids=support_ids,
        artifacts=artifacts,
        components=components,
        producer_id=producer_id,
        request=request,
        path=f"{path}.verification",
    )


def _validate_assessments(
    value: dict[str, Any],
    *,
    artifacts: dict[str, dict[str, Any]],
    components: dict[str, dict[str, Any]],
    owners: dict[str, str],
) -> None:
    request = value["request"]
    selected = request["selected_reading_id"]
    assessments = value["assessments"]
    assessment_goals = [assessment["goal_id"] for assessment in assessments]
    positions = {goal_id: index for index, goal_id in enumerate(request["goal_ids"])}
    if any(goal_id not in positions for goal_id in assessment_goals):
        _fail("reference", "$.assessments", "assessment names an unrequested goal")
    if len(assessment_goals) != len(set(assessment_goals)):
        _fail("identity", "$.assessments", "goal is assessed more than once")
    if assessment_goals != sorted(assessment_goals, key=positions.get):
        _fail("canonical", "$.assessments", "assessments must follow requested goal order")
    execution_status = value["execution"]["status"]
    if execution_status == "completed" and assessment_goals != request["goal_ids"]:
        _fail("outcome", "$.assessments", "completed execution must assess every requested goal")
    if execution_status in {"ambiguous", "error"} and assessments:
        _fail("outcome", "$.assessments", f"{execution_status} execution cannot expose assessments")
    producer_id = value["provenance"]["producer"]["component_id"]
    for index, assessment in enumerate(assessments):
        path = f"$.assessments[{index}]"
        _claim(assessment["assessment_id"], owners, "assessment", f"{path}.assessment_id")
        if assessment["reading_id"] != selected:
            _fail("reading", f"{path}.reading_id", "assessment does not use selected reading")
        assumptions = assessment["assumption_refs"]
        assumption_ids = [item["declaration_id"] for item in assumptions]
        _require_sorted_unique(assumption_ids, f"{path}.assumption_refs")
        obligations = assessment["discharged_obligations"]
        obligation_ids = [item["obligation_id"] for item in obligations]
        _require_sorted_unique(obligation_ids, f"{path}.discharged_obligations")
        for offset, obligation in enumerate(obligations):
            _require_artifacts(
                obligation["evidence_artifact_ids"],
                artifacts,
                f"{path}.discharged_obligations[{offset}].evidence_artifact_ids",
                EVIDENCE_KINDS,
            )
        verdict = assessment["verdict"]
        _validate_verdict(
            verdict,
            artifacts=artifacts,
            components=components,
            producer_id=producer_id,
            request=request,
            path=f"{path}.verdict",
        )
        verdict_status = verdict["status"]
        if execution_status == "unsupported" and verdict_status != "unsupported":
            _fail("outcome", path, "unsupported execution can expose only unsupported verdicts")
        if execution_status == "unknown" and verdict_status != "unknown":
            _fail("outcome", path, "unknown execution can expose only unknown verdicts")
        if execution_status == "unknown" and verdict["reason"] != value["execution"]["reason_code"]:
            _fail("outcome", path, "unknown execution and verdict reasons disagree")
        if execution_status == "disagreement" and (
            verdict_status != "unknown" or verdict.get("reason") != "backend_disagreement"
        ):
            _fail("outcome", path, "disagreement can expose only disagreement-unknown verdicts")
        if execution_status == "verifier_failed" and (
            verdict_status != "unknown" or verdict.get("reason") != "verifier_failure"
        ):
            _fail("outcome", path, "verifier failure can expose only verifier-failure unknowns")


def _validate_diagnostics(
    value: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    owners: dict[str, str],
) -> None:
    diagnostics = value["diagnostics"]
    ids = [diagnostic["diagnostic_id"] for diagnostic in diagnostics]
    _require_sorted_unique(ids, "$.diagnostics")
    for index, diagnostic in enumerate(diagnostics):
        path = f"$.diagnostics[{index}]"
        _claim(diagnostic["diagnostic_id"], owners, "diagnostic", f"{path}.diagnostic_id")
        _require_artifacts(
            diagnostic["related_artifact_ids"],
            artifacts,
            f"{path}.related_artifact_ids",
        )
    execution = value["execution"]
    _require_sorted_unique(execution["diagnostic_ids"], "$.execution.diagnostic_ids")
    if execution["diagnostic_ids"] != ids:
        _fail("diagnostic", "$.execution.diagnostic_ids", "execution must bind every diagnostic")
    if execution["status"] == "completed" and any(
        diagnostic["severity"] == "error" for diagnostic in diagnostics
    ):
        _fail("outcome", "$.diagnostics", "completed execution cannot hide an error diagnostic")
    if (
        execution["status"]
        in {
            "unsupported",
            "ambiguous",
            "unknown",
            "disagreement",
            "verifier_failed",
            "error",
        }
        and not diagnostics
    ):
        _fail("diagnostic", "$.diagnostics", "non-success execution requires a diagnostic")
    if execution["status"] in {"disagreement", "verifier_failed", "error"} and not any(
        diagnostic["severity"] == "error" for diagnostic in diagnostics
    ):
        _fail("diagnostic", "$.diagnostics", "failure execution requires an error diagnostic")


def _validate_execution_artifacts(
    value: dict[str, Any], artifacts: dict[str, dict[str, Any]]
) -> None:
    execution = value["execution"]
    status = execution["status"]
    if status == "unsupported":
        _require_sorted_unique(execution["feature_codes"], "$.execution.feature_codes")
        assessment_features = sorted(
            {
                feature
                for assessment in value["assessments"]
                for feature in assessment["verdict"]["feature_codes"]
            }
        )
        if assessment_features and assessment_features != execution["feature_codes"]:
            _fail("outcome", "$.execution.feature_codes", "unsupported features disagree")
    elif status == "exhausted":
        _require_sorted_unique(execution["dimensions"], "$.execution.dimensions")
        if not set(execution["dimensions"]) <= RESOURCE_DIMENSIONS:
            _fail("schema", "$.execution.dimensions", "unknown resource dimension")
    elif status == "truncated":
        _require_sorted_unique(execution["truncation_ids"], "$.execution.truncation_ids")
    elif status == "disagreement":
        items = _require_artifacts(
            execution["backend_artifact_ids"],
            artifacts,
            "$.execution.backend_artifact_ids",
            {"disagreement_input"},
        )
        producers = {item["producer_component_id"] for item in items}
        if len(producers) < 2:
            _fail("outcome", "$.execution.backend_artifact_ids", "disagreement needs two producers")
    elif status == "verifier_failed":
        _require_artifacts(
            execution["checker_result_artifact_ids"],
            artifacts,
            "$.execution.checker_result_artifact_ids",
            {"checker_result"},
        )


def _validate_budget_outcome(value: dict[str, Any]) -> None:
    request = value["request"]
    snapshot = value["budget"]
    execution_status = value["execution"]["status"]
    if snapshot["initial_budget_sha256"] != request["initial_budget_sha256"]:
        _fail("budget", "$.budget.initial_budget_sha256", "initial budget identity mismatch")
    usage = snapshot["usage"]
    if usage["memory_retained_bytes"] > usage["memory_peak_bytes"]:
        _fail("budget", "$.budget.usage", "retained memory exceeds peak")
    if execution_status in TERMINAL_RESOURCE_OUTCOMES:
        if snapshot["outcome"] != execution_status:
            _fail("outcome", "$.budget.outcome", "resource outcome is hidden or mismatched")
    elif snapshot["outcome"] != "completed":
        _fail("outcome", "$.budget.outcome", "execution hides a terminal resource outcome")


def validate_engine_result(value: dict[str, Any], schema: dict[str, Any]) -> None:
    started = time.monotonic()
    _shape_budget(value, started)
    _schema_validate(value, schema, schema)
    if set(value) != ROOT_FIELDS:
        _fail("schema", "$", "root field set drift")
    for path, text in _walk_strings(value):
        if "\x00" in text:
            _fail("canonical", path, "NUL is forbidden")
        if unicodedata.normalize("NFC", text) != text:
            _fail("canonical", path, "string is not Unicode NFC")
    total_entities = (
        4
        + len(value["provenance"]["components"])
        + len(value["artifacts"])
        + len(value["assessments"])
        + len(value["diagnostics"])
    )
    if total_entities > MAX_ENTITIES:
        _fail("budget", "$", "result entities exceed 100000")
    owners = {
        value["result_id"]: "result",
        value["request"]["request_id"]: "request",
        value["replay"]["replay_id"]: "replay",
        value["budget"]["budget_id"]: "budget",
    }
    if len(owners) != 4:
        _fail("identity", "$", "root identities collide")
    components = _validate_provenance(value, owners)
    artifacts = _validate_artifacts(value, components, owners)
    _validate_request_replay(value)
    _validate_assessments(
        value,
        artifacts=artifacts,
        components=components,
        owners=owners,
    )
    _validate_diagnostics(value, artifacts, owners)
    _validate_execution_artifacts(value, artifacts)
    _validate_budget_outcome(value)
    canonical_bytes(value)
    if time.monotonic() - started > MAX_VALIDATION_SECONDS:
        _fail("budget", "$", "validation exceeded 30 seconds")


def _usage(**updates: int) -> dict[str, int]:
    value = {
        "wall_time_us": 5_000,
        "cpu_time_us": 4_000,
        "memory_peak_bytes": 500,
        "memory_retained_bytes": 50,
        "solver_calls": 1,
        "generated_objects": 5,
        "proof_bytes": 100,
        "evidence_bytes": 200,
        "output_bytes": 80,
        "diagnostic_bytes": 0,
        "nesting_peak": 3,
    }
    value.update(updates)
    return value


def minimal_engine_result() -> dict[str, Any]:
    producer = {
        "component_id": "component_engine",
        "role": "producer",
        "name": "org.mathhead.engine",
        "version": "1.0.0",
        "contract_id": "contract_engine",
        "contract_sha256": "3" * 64,
        "implementation_sha256": "4" * 64,
        "configuration_sha256": "5" * 64,
    }
    checker = {
        "component_id": "component_checker",
        "role": "checker",
        "name": "org.mathhead.checker",
        "version": "1.0.0",
        "contract_id": "contract_checker",
        "contract_sha256": "6" * 64,
        "implementation_sha256": "7" * 64,
        "configuration_sha256": "8" * 64,
    }
    request = {
        "request_id": "request_example",
        "problem_ir_sha256": "1" * 64,
        "theory_context_sha256": "2" * 64,
        "initial_budget_sha256": "9" * 64,
        "candidate_reading_ids": ["reading_primary"],
        "selected_reading_id": "reading_primary",
        "goal_ids": ["goal_main"],
    }
    artifacts = [
        {
            "artifact_id": "artifact_checker_result",
            "kind": "checker_result",
            "schema": "org.mathhead.checker-result",
            "sha256": "a" * 64,
            "byte_count": 120,
            "producer_component_id": "component_checker",
            "extensions": {},
        },
        {
            "artifact_id": "artifact_evidence",
            "kind": "evidence",
            "schema": "org.mathhead.evidence",
            "sha256": "b" * 64,
            "byte_count": 200,
            "producer_component_id": "component_checker",
            "extensions": {},
        },
        {
            "artifact_id": "artifact_proof",
            "kind": "proof",
            "schema": "org.mathhead.proof",
            "sha256": "c" * 64,
            "byte_count": 100,
            "producer_component_id": "component_engine",
            "extensions": {},
        },
    ]
    verification = {
        "checker_component_id": "component_checker",
        "checker_contract_id": "contract_checker",
        "checker_contract_sha256": "6" * 64,
        "checker_result_artifact_id": "artifact_checker_result",
        "evidence_artifact_ids": ["artifact_evidence"],
        "trust_dependency_sha256": sorted(["1" * 64, "2" * 64, "6" * 64, "7" * 64]),
    }
    value: dict[str, Any] = {
        "schema": "mathhead.engine-result.v1",
        "result_id": "result_example",
        "request": request,
        "replay": {
            "replay_id": "replay_example",
            "mode": "deterministic",
            "seed": None,
            "algorithm_id": "org.mathhead.solve",
            "configuration_sha256": "d" * 64,
            "plan_sha256": "e" * 64,
            "parent_result_sha256": None,
            "basis_sha256": "0" * 64,
        },
        "provenance": {
            "producer": producer,
            "components": [checker],
            "environment_contract_sha256": "f" * 64,
        },
        "artifacts": artifacts,
        "assessments": [
            {
                "assessment_id": "assessment_main",
                "goal_id": "goal_main",
                "reading_id": "reading_primary",
                "verdict": {
                    "status": "proved",
                    "epistemic_tier": "checker_attested",
                    "support_artifact_ids": [
                        "artifact_checker_result",
                        "artifact_evidence",
                        "artifact_proof",
                    ],
                    "verification": verification,
                },
                "assumption_refs": [
                    {
                        "declaration_id": "declaration_axiom",
                        "declaration_kind": "axiom",
                        "declaration_sha256": "0" * 64,
                    }
                ],
                "discharged_obligations": [
                    {
                        "obligation_id": "obligation_domain",
                        "evidence_artifact_ids": ["artifact_evidence"],
                    }
                ],
                "extensions": {},
            }
        ],
        "execution": {"status": "completed", "diagnostic_ids": []},
        "budget": {
            "budget_id": "budget_example",
            "initial_budget_sha256": "9" * 64,
            "final_budget_sha256": "a" * 64,
            "outcome": "completed",
            "usage": _usage(),
        },
        "diagnostics": [],
        "extensions": {},
    }
    value["replay"]["basis_sha256"] = replay_basis_sha256(value)
    return value


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
    try:
        accepted_value = json.loads(accepted_raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail("identity", "contract", f"accepted contract is invalid JSON: {exc}")
    if (
        accepted_raw != proposed_raw
        or _sha(accepted_raw) != EXPECTED_CONTRACT_SHA256
        or accepted_raw != canonical_bytes(accepted_value)
    ):
        _fail("identity", "contract", "accepted/proposed contract identity drift")
    manifest = tomllib.loads((root / "docs/contracts/manifest.toml").read_text(encoding="utf-8"))
    records = [
        record for record in manifest.get("contracts", []) if record.get("id") == CONTRACT_ID
    ]
    expected = {
        "id": CONTRACT_ID,
        "path": f"docs/contracts/{CONTRACT_ID}.json",
        "sha256": EXPECTED_CONTRACT_SHA256,
        "state": "accepted",
    }
    if records != [expected]:
        _fail("identity", "manifest", "accepted contract manifest binding drift")
    schema_clause = f"{SCHEMA_PATH.as_posix()}={EXPECTED_SCHEMA_SHA256}"
    if not any(schema_clause in clause for clause in accepted_value.get("invariants", [])):
        _fail("identity", "contract.invariants", "normative schema identity is not bound")


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
            value = minimal_engine_result()
        else:
            path = args.instance if args.instance.is_absolute() else root / args.instance
            value, _raw = load_json(path, require_canonical=True)
        validate_engine_result(value, schema)
    except (EngineResultValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"engine-result-contract: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "engine-result-contract: PASS "
        f"(schema={EXPECTED_SCHEMA_SHA256[:12]}, identity={canonical_sha256(value)[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
