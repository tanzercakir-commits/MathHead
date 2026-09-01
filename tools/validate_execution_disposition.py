#!/usr/bin/env python3
"""Independently validate the frozen MH-056 schemas and budget-anchor rule."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urldefrag, urljoin
try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CONTRACT_ID = "MH-C-EXECUTION-DISPOSITION-001"
CONTRACT_SHA256 = (
    "64a7950b13449ee942d003d4e56b482b104769db15cd3080a1011a2a45eb4f96"
)
SCHEMAS = {
    "cancellation-intent-v1.schema.json": (
        "a088044c3a3aeaa0724ece3cdf0ca629475485a12fe73d9c8b79afcdbf946b21"
    ),
    "execution-disposition-request-v1.schema.json": (
        "0e4cb91a1c2a8da79f62b08b4f81234cecd0770c5730dcc859aeb78fcf00f767"
    ),
    "execution-disposition-classification-v1.schema.json": (
        "0f430feba19c7c08cea45a0b2ebc31a47e1cf7d40c9a773f4daf31ef272b7762"
    ),
    "execution-disposition-diagnostic-v1.schema.json": (
        "4908803868cc1260e92dbbc7711571b661869d9b213bcc67cf2b31dc297b180b"
    ),
    "execution-disposition-result-v1.schema.json": (
        "ceb05ed2f6bef7e276c5b84aad61e56991ceb9a09a027e12c6a8e265ed0872b9"
    ),
}
RESOURCE_DIMENSIONS = (
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
)
RESERVED_EXTENSION = "org.mathhead.execution-disposition"
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_KEYWORDS = frozenset(
    {
        "$defs", "$id", "$ref", "$schema", "additionalProperties", "allOf",
        "const", "else", "enum", "if", "items", "maxItems", "maxLength",
        "maximum", "minItems", "minLength", "minimum", "not", "oneOf",
        "pattern", "properties", "required", "then", "title", "type",
        "uniqueItems",
    }
)
INVOCATION_FIELDS = frozenset(
    {
        "schema", "invocation_id", "planning_request_sha256",
        "route_result_sha256", "planning_result_sha256",
        "base_parent_budget_sha256", "descriptor_sha256s", "binding_sha256s",
        "artifact_bindings", "cancellation_armed", "mathematical_authority",
    }
)
REQUEST_FIELDS = frozenset(
    {
        "schema", "contract_id", "contract_sha256", "invocation_id",
        "planning_request_sha256", "route_result_sha256",
        "planning_result_sha256", "base_parent_budget_sha256",
        "descriptor_sha256s", "binding_sha256s", "artifact_bindings",
        "cancellation_armed", "cancellation_intent", "invocation_sha256",
        "request_sha256", "mathematical_authority",
    }
)
CANCELLATION_INTENT_FIELDS = frozenset(
    {
        "schema", "intent_id", "origin_source", "reason_code",
        "invocation_id", "invocation_sha256", "base_parent_budget_sha256",
        "policy_contract_id", "policy_contract_sha256", "intent_sha256",
        "mathematical_authority",
    }
)
RESULT_REQUEST_PROJECTION_FIELDS = frozenset(
    {
        "disposition_request_sha256", "invocation_sha256",
        "cancellation_armed", "cancellation_intent_sha256",
    }
)
RESULT_FIELDS = frozenset(
    {
        "schema", "contract_id", "contract_sha256", "request_input_sha256",
        "disposition_request_sha256", "invocation_sha256",
        "cancellation_armed", "cancellation_intent_sha256",
        "base_parent_budget_sha256", "anchored_parent_budget_sha256",
        "planning_result_sha256", "portfolio_request_sha256",
        "audit_manifest_sha256", "logical_report_sha256",
        "replay_result_sha256", "portfolio_result_sha256",
        "execution_provenance_sha256", "execution_state",
        "portfolio_relation", "portfolio_outcome_kind", "route_status",
        "route_reason_code", "planning_status", "planning_reason_code",
        "portfolio_status", "portfolio_reason_code", "replay_status",
        "replay_reason_code", "classification", "diagnostics",
        "selected_strategy_sha256", "selected_evidence_sha256",
        "selected_certificate_sha256", "selected_checker_decision_sha256",
        "linked_authority_tier", "authority_ceiling", "result_sha256",
        "mathematical_authority",
    }
)


class ExecutionDispositionValidationFailure(RuntimeError):
    """Raised when an independently reconstructed MH-056 invariant drifts."""


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExecutionDispositionValidationFailure(
                f"duplicate JSON key in schema: {key}"
            )
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionDispositionValidationFailure(
            f"invalid JSON document: {path.name}"
        ) from exc
    if type(value) is not dict:
        raise ExecutionDispositionValidationFailure(
            f"JSON root is not an object: {path.name}"
        )
    return value


def _pointer(document: dict[str, Any], fragment: str) -> dict[str, Any]:
    current: object = document
    if fragment:
        if not fragment.startswith("/"):
            raise ExecutionDispositionValidationFailure(
                "only JSON Pointer schema fragments are accepted"
            )
        for raw in fragment[1:].split("/"):
            part = raw.replace("~1", "/").replace("~0", "~")
            if type(current) is not dict or part not in current:
                raise ExecutionDispositionValidationFailure(
                    f"schema reference target is absent: {fragment}"
                )
            current = current[part]
    if type(current) is not dict:
        raise ExecutionDispositionValidationFailure(
            f"schema reference target is not an object: {fragment}"
        )
    return current


def _walk_schema(
    node: object,
    *,
    path: str,
    resource: dict[str, Any],
    base_uri: str,
    registry: dict[str, dict[str, Any]],
) -> None:
    if type(node) is not dict:
        raise ExecutionDispositionValidationFailure(f"schema node is not an object: {path}")
    schema = node
    unknown = set(schema).difference(SCHEMA_KEYWORDS)
    if unknown:
        raise ExecutionDispositionValidationFailure(
            f"unsupported schema keywords at {path}: {sorted(unknown)!r}"
        )
    if "$schema" in schema and schema["$schema"] != SCHEMA_DIALECT:
        raise ExecutionDispositionValidationFailure(f"schema dialect drift at {path}")
    if "$ref" in schema:
        reference = schema["$ref"]
        if type(reference) is not str:
            raise ExecutionDispositionValidationFailure(f"non-string $ref at {path}")
        joined = urljoin(base_uri, reference)
        identity, fragment = urldefrag(joined)
        target_resource = resource if identity == base_uri else registry.get(identity)
        if target_resource is None:
            raise ExecutionDispositionValidationFailure(
                f"unresolved schema resource at {path}: {identity}"
            )
        _pointer(target_resource, fragment)
    for keyword in ("properties", "$defs"):
        members = schema.get(keyword)
        if members is None:
            continue
        if type(members) is not dict:
            raise ExecutionDispositionValidationFailure(
                f"{keyword} is not an object at {path}"
            )
        for name, child in members.items():
            _walk_schema(
                child,
                path=f"{path}.{keyword}.{name}",
                resource=resource,
                base_uri=base_uri,
                registry=registry,
            )
    for keyword in ("items", "if", "then", "else", "not"):
        if keyword in schema:
            _walk_schema(
                schema[keyword],
                path=f"{path}.{keyword}",
                resource=resource,
                base_uri=base_uri,
                registry=registry,
            )
    additional = schema.get("additionalProperties")
    if type(additional) is dict:
        _walk_schema(
            additional,
            path=f"{path}.additionalProperties",
            resource=resource,
            base_uri=base_uri,
            registry=registry,
        )
    elif additional is not None and type(additional) is not bool:
        raise ExecutionDispositionValidationFailure(
            f"additionalProperties has invalid type at {path}"
        )
    for keyword in ("allOf", "oneOf"):
        if keyword not in schema:
            continue
        branches = schema[keyword]
        if type(branches) is not list or not branches:
            raise ExecutionDispositionValidationFailure(
                f"{keyword} is not a nonempty array at {path}"
            )
        for index, child in enumerate(branches):
            _walk_schema(
                child,
                path=f"{path}.{keyword}[{index}]",
                resource=resource,
                base_uri=base_uri,
                registry=registry,
            )
    required = schema.get("required")
    if required is not None and (
        type(required) is not list
        or any(type(item) is not str for item in required)
        or len(required) != len(set(required))
    ):
        raise ExecutionDispositionValidationFailure(f"invalid required array at {path}")
    for keyword in ("minItems", "maxItems", "minLength", "maxLength"):
        if keyword in schema and (type(schema[keyword]) is not int or schema[keyword] < 0):
            raise ExecutionDispositionValidationFailure(f"invalid {keyword} at {path}")
    if "pattern" in schema:
        try:
            re.compile(schema["pattern"])
        except (TypeError, re.error) as exc:
            raise ExecutionDispositionValidationFailure(
                f"invalid pattern at {path}"
            ) from exc


def _schema_graph_check(schemas: dict[str, dict[str, Any]]) -> None:
    registry: dict[str, dict[str, Any]] = {}
    for name, schema in schemas.items():
        identity = schema.get("$id")
        if type(identity) is not str or not identity:
            raise ExecutionDispositionValidationFailure(
                f"schema has no exact resource identity: {name}"
            )
        if identity in registry:
            raise ExecutionDispositionValidationFailure(
                f"duplicate schema resource identity: {identity}"
            )
        registry[identity] = schema
    for name, schema in schemas.items():
        identity = schema["$id"]
        _walk_schema(
            schema,
            path=name,
            resource=schema,
            base_uri=identity,
            registry=registry,
        )


def _values(constraint: object, *, label: str) -> tuple[object, ...]:
    if type(constraint) is not dict:
        raise ExecutionDispositionValidationFailure(f"missing constraint: {label}")
    if "const" in constraint:
        return (constraint["const"],)
    choices = constraint.get("enum")
    if type(choices) is not list or not choices:
        raise ExecutionDispositionValidationFailure(f"constraint is not closed: {label}")
    return tuple(choices)


def _classification_schema_check(schema: dict[str, Any]) -> None:
    cause_catalogue = tuple(schema["properties"]["cause"]["enum"])
    expected_causes = (
        "checked_proof", "checked_refutation", "ambiguity", "user_cancellation",
        "parent_cancellation", "supervisor_cancellation",
        "cancellation_origin_unproven", "budget_exhaustion", "unsupported_input",
        "unsupported_execution_environment", "producer_refusal",
        "verifier_refusal", "truncation", "inconclusive_execution",
        "checker_disagreement", "invalid_evidence", "producer_failure",
        "verifier_failure", "invalid_request", "internal_error",
    )
    if cause_catalogue != expected_causes:
        raise ExecutionDispositionValidationFailure("classification cause catalogue drift")
    if tuple(schema["$defs"]["resource_dimension"]["enum"]) != RESOURCE_DIMENSIONS:
        raise ExecutionDispositionValidationFailure("resource dimension catalogue drift")

    expected: set[tuple[object, ...]] = set()

    def add(
        causes: tuple[str, ...],
        disposition: str,
        row: str,
        rank: int,
        phases: tuple[str, ...],
        minimum: int = 0,
        maximum: int = 0,
    ) -> None:
        for cause in causes:
            expected.add((cause, disposition, row, rank, phases, minimum, maximum))

    add(("checked_proof", "checked_refutation"), "completed", "30_checked_terminal", 30, ("completed",))
    add(("ambiguity",), "inconclusive", "20_early_route_planner", 20, ("routing",))
    add(("ambiguity",), "inconclusive", "80_semantic_terminal", 80, ("producer",))
    add(("user_cancellation", "parent_cancellation", "supervisor_cancellation", "cancellation_origin_unproven"), "cancelled", "40_observed_cancellation", 40, ("producer", "checker"))
    add(("budget_exhaustion",), "exhausted", "20_early_route_planner", 20, ("routing", "planning"))
    add(("budget_exhaustion",), "exhausted", "50_ledger_exhaustion", 50, ("producer", "checker"), 1, 10)
    add(("unsupported_input",), "refused", "20_early_route_planner", 20, ("routing",))
    add(("unsupported_execution_environment",), "refused", "20_early_route_planner", 20, ("routing",))
    add(("unsupported_execution_environment",), "refused", "60_environment_refusal", 60, ("producer", "checker"))
    add(("producer_refusal",), "refused", "70_component_refusal", 70, ("producer",))
    add(("verifier_refusal",), "refused", "70_component_refusal", 70, ("checker",))
    add(("truncation",), "inconclusive", "80_semantic_terminal", 80, ("producer", "checker"))
    add(("inconclusive_execution",), "inconclusive", "80_semantic_terminal", 80, ("checker",))
    add(("checker_disagreement",), "inconclusive", "80_semantic_terminal", 80, ("checker",))
    add(("invalid_evidence",), "inconclusive", "80_semantic_terminal", 80, ("producer", "checker"))
    add(("producer_failure",), "failed", "90_phase_failure", 90, ("producer",))
    add(("verifier_failure",), "failed", "90_phase_failure", 90, ("checker",))
    add(("invalid_request",), "invalid", "10_prelaunch_invalid", 10, ("request", "routing", "planning", "coordinator"))
    add(("internal_error",), "failed", "00_internal_invariant", 0, ("cleanup", "audit", "replay", "coordinator"))

    branches = schema["allOf"][0]["oneOf"]
    observed: set[tuple[object, ...]] = set()
    cancellation_origins = {
        "user_cancellation": "user",
        "parent_cancellation": "parent",
        "supervisor_cancellation": "supervisor",
        "cancellation_origin_unproven": None,
    }
    for branch in branches:
        properties = branch.get("properties", {})
        causes = _values(properties.get("cause"), label="classification cause")
        disposition = _values(
            properties.get("disposition"), label="classification disposition"
        )
        row = _values(properties.get("precedence_row"), label="precedence row")
        rank = _values(properties.get("precedence_rank"), label="precedence rank")
        phases = _values(properties.get("phase"), label="classification phase")
        resources = properties.get("resource_dimensions", {})
        minimum = resources.get("minItems", 0)
        maximum = resources.get("maxItems", 10)
        if len(disposition) != 1 or len(row) != 1 or len(rank) != 1:
            raise ExecutionDispositionValidationFailure(
                "classification row is not singly paired"
            )
        for cause in causes:
            observed.add(
                (
                    cause, disposition[0], row[0], rank[0], phases, minimum, maximum,
                )
            )
            if cause in cancellation_origins:
                expected_origin = cancellation_origins[cause]
                origin = properties.get("origin_source", {})
                if expected_origin is None:
                    origin_ok = origin.get("type") == "null"
                else:
                    origin_ok = origin.get("const") == expected_origin
                if not origin_ok or (
                    properties.get("observer_source", {}).get("const") != "supervisor"
                    or properties.get("observer_cancellation_id", {}).get("type")
                    != "null"
                    or properties.get("observer_basis", {}).get("const")
                    != "replayed_worker_status_plus_accepted_contract"
                ):
                    raise ExecutionDispositionValidationFailure(
                        f"cancellation observer relation drift: {cause}"
                    )
    if observed != expected:
        raise ExecutionDispositionValidationFailure("classification matrix drift")

    cancellation_guard = schema["allOf"][1]
    guarded = tuple(
        cancellation_guard["if"]["properties"]["cause"]["enum"]
    )
    if guarded != tuple(cancellation_origins):
        raise ExecutionDispositionValidationFailure("cancellation guard drift")
    null_fields = cancellation_guard["else"]["properties"]
    for name in (
        "origin_source", "observer_source", "observer_cancellation_id",
        "observer_basis",
    ):
        if null_fields.get(name, {}).get("type") != "null":
            raise ExecutionDispositionValidationFailure(
                f"non-cancellation observer field is not null: {name}"
            )


def _diagnostic_schema_check(schema: dict[str, Any]) -> None:
    expected = {
        "REQUEST_INVALID": ("request",),
        "INTENT_EVENT_MISMATCH": ("request",),
        "RESERVED_EXTENSION_COLLISION": ("coordinator",),
        "ROUTE_INPUT_INVALID": ("routing",),
        "PLANNING_INPUT_INVALID": ("planning",),
        "BINDING_INPUT_INVALID": ("request", "planning"),
        "ARTIFACT_INPUT_INVALID": ("request", "planning"),
        "EXECUTION_INPUT_INVALID": ("coordinator",),
        "BUDGET_ANCHOR_INVALID": ("coordinator",),
        "PORTFOLIO_REQUEST_INVALID": ("coordinator",),
        "AUDITED_EXECUTION_INVALID": ("audit",),
        "AUDIT_REPLAY_INVALID": ("replay",),
        "AUDIT_REPLAY_EXHAUSTED": ("replay",),
        "AUDIT_RELATION_INVALID": ("audit",),
        "CLEANUP_INVARIANT": ("cleanup",),
        "SUPERVISOR_INVARIANT": ("coordinator",),
        "WORKER_REQUEST_INVARIANT": ("coordinator",),
        "WORKER_PLAN_INVARIANT": ("coordinator",),
        "WORKER_STRATEGY_INVARIANT": ("coordinator",),
        "WORKER_BUDGET_INVARIANT": ("coordinator",),
        "WORKER_EXECUTABLE_INVARIANT": ("coordinator",),
        "PORTFOLIO_INPUT_INVARIANT": ("coordinator",),
        "PORTFOLIO_EXECUTION_INVARIANT": ("coordinator",),
        "COORDINATOR_LIMIT_EXHAUSTED": ("coordinator",),
    }
    if schema["properties"]["severity"].get("const") != "error":
        raise ExecutionDispositionValidationFailure("diagnostic severity drift")
    if tuple(schema["properties"]["code"]["enum"]) != tuple(expected):
        raise ExecutionDispositionValidationFailure("diagnostic code catalogue drift")
    if (
        schema["properties"]["subject_sha256"].get("type") != "null"
        or schema["properties"]["related_sha256s"].get("maxItems") != 0
    ):
        raise ExecutionDispositionValidationFailure(
            "diagnostic context is not the exact empty v1 projection"
        )
    observed: dict[str, list[str]] = {}
    for branch in schema["allOf"][0]["oneOf"]:
        properties = branch["properties"]
        codes = _values(properties.get("code"), label="diagnostic code")
        phases = _values(properties.get("phase"), label="diagnostic phase")
        if len(codes) != 1 or len(phases) != 1:
            raise ExecutionDispositionValidationFailure("diagnostic code branch drift")
        code = str(codes[0])
        phase = str(phases[0])
        diagnostic_id = properties.get("diagnostic_id", {}).get("const")
        diagnostic_sha256 = properties.get("diagnostic_sha256", {}).get("const")
        expected_id = f"execution_disposition.{phase}.{code.lower()}"
        preimage = {
            "schema": "mathhead.execution-disposition-diagnostic.v1",
            "diagnostic_id": expected_id,
            "severity": "error",
            "code": code,
            "phase": phase,
            "subject_sha256": None,
            "related_sha256s": [],
            "diagnostic_sha256": None,
            "mathematical_authority": False,
        }
        if (
            diagnostic_id != expected_id
            or diagnostic_sha256 != _sha(_canonical(preimage))
            or phase in observed.setdefault(code, [])
        ):
            raise ExecutionDispositionValidationFailure(
                f"diagnostic identity projection drift: {code}/{phase}"
            )
        observed[code].append(phase)
    if {code: tuple(phases) for code, phases in observed.items()} != expected:
        raise ExecutionDispositionValidationFailure("diagnostic code-phase matrix drift")


def _request_schema_check(schema: dict[str, Any]) -> None:
    branches = schema["allOf"][0]["oneOf"]
    if len(branches) != 2:
        raise ExecutionDispositionValidationFailure("request intent pairing drift")
    by_armed = {
        branch["properties"]["cancellation_armed"]["const"]: branch["properties"]
        for branch in branches
    }
    if set(by_armed) != {False, True}:
        raise ExecutionDispositionValidationFailure("request armed catalogue drift")
    if by_armed[False]["cancellation_intent"].get("type") != "null":
        raise ExecutionDispositionValidationFailure("unarmed request permits intent")
    armed = by_armed[True]
    if (
        armed["cancellation_intent"].get("$ref")
        != "cancellation-intent-v1.schema.json"
        or armed.get("base_parent_budget_sha256", {}).get("$ref")
        != "#/$defs/sha256"
    ):
        raise ExecutionDispositionValidationFailure(
            "armed request does not require intent and parent budget"
        )


def _find_constraints(node: object, name: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if type(node) is dict:
        properties = node.get("properties")
        if type(properties) is dict and type(properties.get(name)) is dict:
            found.append(properties[name])
        for value in node.values():
            found.extend(_find_constraints(value, name))
    elif type(node) is list:
        for value in node:
            found.extend(_find_constraints(value, name))
    return found


def _flatten_values(node: object, name: str) -> set[object]:
    result: set[object] = set()
    for constraint in _find_constraints(node, name):
        if "const" in constraint:
            value = constraint["const"]
            if type(value) in (str, int, bool) or value is None:
                result.add(value)
        elif type(constraint.get("enum")) is list:
            result.update(constraint["enum"])
    return result


def _branch_reference(branch: dict[str, Any]) -> str | None:
    references: list[str] = []

    def visit(node: object) -> None:
        if type(node) is dict:
            reference = node.get("$ref")
            if type(reference) is str and reference.startswith("#/$defs/"):
                references.append(reference.rsplit("/", 1)[-1])
            for value in node.values():
                visit(value)
        elif type(node) is list:
            for value in node:
                visit(value)

    visit(branch)
    for expected in ("early_normal_result", "audited_normal_result"):
        if expected in references:
            return expected
    return None


def _definition_references(node: object) -> set[str]:
    references: set[str] = set()
    if type(node) is dict:
        reference = node.get("$ref")
        if type(reference) is str and reference.startswith("#/$defs/"):
            references.add(reference.rsplit("/", 1)[-1])
        for value in node.values():
            references.update(_definition_references(value))
    elif type(node) is list:
        for value in node:
            references.update(_definition_references(value))
    return references


def _result_schema_check(schema: dict[str, Any]) -> None:
    if len(schema.get("allOf", ())) != 5:
        raise ExecutionDispositionValidationFailure("result relation layer drift")
    state_branches = schema["allOf"][0]["oneOf"]
    states = {
        branch["properties"]["execution_state"]["const"]: branch
        for branch in state_branches
    }
    if set(states) != {
        "not_started", "attempted_no_bundle", "bundle_replay_failed",
        "replayed_complete",
    }:
        raise ExecutionDispositionValidationFailure("result execution-state matrix drift")
    null = {"type": "null"}
    expected_not_started = {
        "execution_state": {"const": "not_started"},
        "portfolio_relation": {"const": "not_available"},
        "audit_manifest_sha256": null,
        "logical_report_sha256": null,
        "replay_result_sha256": null,
        "portfolio_result_sha256": null,
        "execution_provenance_sha256": null,
        "portfolio_status": null,
        "portfolio_reason_code": null,
        "replay_status": null,
        "replay_reason_code": null,
    }
    if states["not_started"].get("properties") != expected_not_started:
        raise ExecutionDispositionValidationFailure(
            "not-started evidence profile drift"
        )
    for state in ("attempted_no_bundle", "bundle_replay_failed", "replayed_complete"):
        properties = states[state]["properties"]
        required_sha_fields = (
            "disposition_request_sha256", "invocation_sha256",
            "base_parent_budget_sha256", "anchored_parent_budget_sha256",
            "planning_result_sha256", "portfolio_request_sha256",
        )
        if any(properties.get(name, {}).get("$ref") != "#/$defs/sha256" for name in required_sha_fields):
            raise ExecutionDispositionValidationFailure(
                f"started state lacks a validated identity: {state}"
            )
        expected_status = {
            "route_status": "routed", "route_reason_code": "ROUTED",
            "planning_status": "planned", "planning_reason_code": "PLANNED",
        }
        if any(properties.get(name, {}).get("const") != value for name, value in expected_status.items()):
            raise ExecutionDispositionValidationFailure(
                f"started state lacks routed/planned relation: {state}"
            )
    if (
        states["attempted_no_bundle"]["properties"]["portfolio_relation"].get("const")
        != "not_available"
        or states["bundle_replay_failed"]["properties"]["portfolio_relation"].get("const")
        != "not_available"
        or tuple(
            states["replayed_complete"]["properties"]["portfolio_relation"].get(
                "enum", ()
            )
        )
        != ("exact", "invalid")
    ):
        raise ExecutionDispositionValidationFailure(
            "execution-state portfolio relation drift"
        )
    replay_pairs = {
        (
            branch["properties"]["replay_status"]["const"],
            branch["properties"]["replay_reason_code"]["const"],
        )
        for branch in states["bundle_replay_failed"]["oneOf"]
    }
    if replay_pairs != {
        ("invalid", "REPLAY_INVALID"),
        ("exhausted", "REPLAY_BUDGET_EXHAUSTED"),
    }:
        raise ExecutionDispositionValidationFailure("replay status-reason matrix drift")

    definitions = schema["$defs"]
    sha = {"$ref": "#/$defs/sha256"}
    valid_request_properties = {
        "disposition_request_sha256": sha,
        "invocation_sha256": sha,
        "cancellation_armed": {"type": "boolean"},
    }
    if definitions["valid_request_result"].get("properties") != valid_request_properties:
        raise ExecutionDispositionValidationFailure(
            "validated result request identity profile drift"
        )
    empty_properties = {
        "disposition_request_sha256": null,
        "invocation_sha256": null,
        "cancellation_armed": null,
        "cancellation_intent_sha256": null,
        "base_parent_budget_sha256": null,
        "anchored_parent_budget_sha256": null,
        "planning_result_sha256": null,
        "portfolio_request_sha256": null,
        "route_status": null,
        "route_reason_code": null,
        "planning_status": null,
        "planning_reason_code": null,
    }
    if definitions["empty_preflight_result"].get("properties") != empty_properties:
        raise ExecutionDispositionValidationFailure("empty preflight profile drift")

    common_null_budget = {
        "base_parent_budget_sha256": null,
        "anchored_parent_budget_sha256": null,
        "portfolio_request_sha256": null,
    }
    planned_status = {
        "route_status": {"const": "routed"},
        "route_reason_code": {"const": "ROUTED"},
        "planning_status": {"const": "planned"},
        "planning_reason_code": {"const": "PLANNED"},
    }
    expected_profiles = {
        "validated_pre_route_result": {
            **common_null_budget,
            "planning_result_sha256": null,
            "route_status": null,
            "route_reason_code": null,
            "planning_status": null,
            "planning_reason_code": null,
        },
        "invalid_route_result": {
            **common_null_budget,
            "planning_result_sha256": null,
            "route_status": {"const": "invalid"},
            "route_reason_code": {"const": "INVALID_INPUT"},
            "planning_status": null,
            "planning_reason_code": null,
        },
        "invalid_planning_result": {
            **common_null_budget,
            "planning_result_sha256": sha,
            "route_status": {"const": "routed"},
            "route_reason_code": {"const": "ROUTED"},
            "planning_status": {"const": "invalid"},
            "planning_reason_code": {"const": "INVALID_INPUT"},
        },
        "planned_no_budget_result": {
            **common_null_budget,
            "planning_result_sha256": sha,
            **planned_status,
        },
        "planned_unanchored_result": {
            "base_parent_budget_sha256": sha,
            "anchored_parent_budget_sha256": null,
            "planning_result_sha256": sha,
            "portfolio_request_sha256": null,
            **planned_status,
        },
        "planned_anchored_result": {
            "base_parent_budget_sha256": sha,
            "anchored_parent_budget_sha256": sha,
            "planning_result_sha256": sha,
            "portfolio_request_sha256": null,
            **planned_status,
        },
        "planned_portfolio_ready_result": {
            "base_parent_budget_sha256": sha,
            "anchored_parent_budget_sha256": sha,
            "planning_result_sha256": sha,
            "portfolio_request_sha256": sha,
            **planned_status,
        },
    }
    for name, properties in expected_profiles.items():
        profile = definitions[name]
        if (
            profile.get("type") != "object"
            or profile.get("allOf")
            != [{"$ref": "#/$defs/valid_request_result"}]
            or profile.get("properties") != properties
        ):
            raise ExecutionDispositionValidationFailure(
                f"prelaunch milestone profile drift: {name}"
            )
    early_profile = definitions["reached_early_result"]
    if (
        early_profile.get("allOf")
        != [{"$ref": "#/$defs/valid_request_result"}]
        or early_profile.get("properties")
        != {
            **common_null_budget,
            "planning_result_sha256": sha,
            "cancellation_armed": {"const": False},
            "cancellation_intent_sha256": null,
        }
    ):
        raise ExecutionDispositionValidationFailure("early milestone profile drift")
    early_pairs = {
        (
            tuple(sorted(str(value) for value in _flatten_values(branch, "route_status"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "route_reason_code"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "planning_status"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "planning_reason_code"))),
        )
        for branch in early_profile.get("oneOf", ())
    }
    if early_pairs != {
        (("ambiguous",), ("NON_UNIQUE_SELECTION", "READING_AMBIGUOUS"), ("ambiguous",), ("ROUTE_AMBIGUOUS",)),
        (("exhausted",), ("BUDGET_EXHAUSTED",), ("exhausted",), ("ROUTE_EXHAUSTED",)),
        (("unsupported",), ("NO_COMPATIBLE_CAPABILITY",), ("unsupported",), ("ROUTE_UNSUPPORTED",)),
        (("routed",), ("ROUTED",), ("exhausted",), ("PLANNING_EXHAUSTED",)),
    }:
        raise ExecutionDispositionValidationFailure("early milestone matrix drift")
    if (
        schema["properties"]["diagnostics"].get("uniqueItems") is not True
        or schema["properties"]["diagnostics"].get("maxItems") != 1
    ):
        raise ExecutionDispositionValidationFailure(
            "result diagnostics are not an exact zero-or-one tuple"
        )

    expected_portfolio_reasons = {
        "succeeded": {"CHECKED_PROOF", "CHECKED_REFUTATION"},
        "unsupported": {"ISOLATION_UNSUPPORTED", "EVIDENCE_UNSUPPORTED"},
        "exhausted": {
            "BUDGET_INSUFFICIENT", "WALL_TIME_EXHAUSTED",
            "CPU_TIME_EXHAUSTED", "MEMORY_EXHAUSTED",
            "OUTPUT_EXHAUSTED", "DIAGNOSTIC_EXHAUSTED",
            "EVIDENCE_EXHAUSTED", "CHECKER_EXHAUSTED",
        },
        "cancelled": {"CANCELLED", "EVIDENCE_CANCELLED", "CHECKER_CANCELLED"},
        "failed": {
            "REQUEST_INVALID", "PLAN_INVALID", "STRATEGY_MISMATCH",
            "BUDGET_INVALID", "EXECUTABLE_INVALID", "LAUNCH_FAILED",
            "EXIT_FAILED", "PROTOCOL_FAILED", "TREE_CLEANUP_FAILED",
            "SUPERVISOR_FAILED", "EVIDENCE_ERROR",
        },
        "ambiguous": {"EVIDENCE_INCOMPLETE"},
        "truncated": {"EVIDENCE_TRUNCATED", "CHECKER_TRUNCATED"},
        "inconclusive": {"ISOLATION_UNSUPPORTED", "CHECKER_INCONCLUSIVE"},
        "disagreement": {"CHECKER_REJECTED", "CHECKER_DISAGREED"},
        "verifier_failed": {
            "REQUEST_INVALID", "PLAN_INVALID", "STRATEGY_MISMATCH",
            "BUDGET_INVALID", "EXECUTABLE_INVALID", "LAUNCH_FAILED",
            "EXIT_FAILED", "PROTOCOL_FAILED", "TREE_CLEANUP_FAILED",
            "SUPERVISOR_FAILED", "CERTIFICATE_INVALID",
        },
        "invalid_evidence": {
            "EVIDENCE_INVALID", "EVIDENCE_PROTOCOL_LIMIT", "CERTIFICATE_INVALID",
        },
        "invalid": {"PORTFOLIO_INPUT_INVALID", "PORTFOLIO_EXECUTION_INVALID"},
    }
    observed_portfolio_reasons: dict[str, set[str]] = {}
    for branch in definitions["portfolio_pair"].get("oneOf", ()):
        statuses = _flatten_values(branch, "portfolio_status")
        reasons = _flatten_values(branch, "portfolio_reason_code")
        if len(statuses) != 1 or not reasons:
            raise ExecutionDispositionValidationFailure(
                "portfolio pair row is not exact"
            )
        status = str(next(iter(statuses)))
        if status in observed_portfolio_reasons:
            raise ExecutionDispositionValidationFailure(
                f"duplicate portfolio status row: {status}"
            )
        observed_portfolio_reasons[status] = {str(reason) for reason in reasons}
    if (
        observed_portfolio_reasons != expected_portfolio_reasons
        or sum(len(reasons) for reasons in observed_portfolio_reasons.values()) != 49
    ):
        raise ExecutionDispositionValidationFailure(
            "accepted 49-pair portfolio matrix drift"
        )

    request_gate = schema["allOf"][1]["oneOf"]
    expected_request_gate = [
        {
            "disposition_request_sha256": null,
            "invocation_sha256": null,
            "cancellation_armed": null,
            "cancellation_intent_sha256": null,
        },
        {
            "disposition_request_sha256": sha,
            "invocation_sha256": sha,
            "cancellation_armed": {"const": False},
            "cancellation_intent_sha256": null,
        },
        {
            "disposition_request_sha256": sha,
            "invocation_sha256": sha,
            "cancellation_armed": {"const": True},
            "cancellation_intent_sha256": sha,
        },
    ]
    if [branch.get("properties") for branch in request_gate] != expected_request_gate:
        raise ExecutionDispositionValidationFailure(
            "result request/armed/intent identity gate drift"
        )

    outcome_gate = schema["allOf"][2]["oneOf"]
    if len(outcome_gate) != 4:
        raise ExecutionDispositionValidationFailure(
            "portfolio outcome discriminator gate drift"
        )
    outcome_variants = {
        (
            tuple(sorted(str(value) for value in _flatten_values(branch, "portfolio_status"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "portfolio_reason_code"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "portfolio_outcome_kind"))),
        )
        for branch in outcome_gate[:3]
        if _flatten_values(branch, "portfolio_relation") == {"exact"}
    }
    if outcome_variants != {
        (("failed", "verifier_failed"), ("LAUNCH_FAILED",), ("launch_refused",)),
        (
            ("failed", "verifier_failed"),
            ("EXECUTABLE_INVALID",),
            ("executable_invalid", "executable_refused"),
        ),
        (
            ("inconclusive",),
            ("CHECKER_INCONCLUSIVE",),
            ("certificate_inconclusive", "certificate_unsupported"),
        ),
    }:
        raise ExecutionDispositionValidationFailure(
            "portfolio outcome discriminator matrix drift"
        )
    outcome_default = outcome_gate[3]
    if (
        outcome_default.get("properties", {})
        .get("portfolio_outcome_kind", {})
        .get("type")
        != "null"
        or len(outcome_default.get("allOf", ())) != 3
    ):
        raise ExecutionDispositionValidationFailure(
            "portfolio outcome discriminator default is open"
        )

    selection = schema["allOf"][3]
    checked = set(
        selection["if"]["properties"]["classification"]["properties"]["cause"]["enum"]
    )
    if checked != {"checked_proof", "checked_refutation"}:
        raise ExecutionDispositionValidationFailure("checked selection guard drift")
    selected_names = (
        "selected_strategy_sha256", "selected_evidence_sha256",
        "selected_certificate_sha256", "selected_checker_decision_sha256",
    )
    then_properties = selection["then"]["properties"]
    else_properties = selection["else"]["properties"]
    if any(then_properties.get(name, {}).get("$ref") != "#/$defs/sha256" for name in selected_names):
        raise ExecutionDispositionValidationFailure("checked identity retention drift")
    if any(else_properties.get(name, {}).get("type") != "null" for name in selected_names):
        raise ExecutionDispositionValidationFailure("non-checked identity retention drift")
    if schema["properties"]["authority_ceiling"].get("const") != "none":
        raise ExecutionDispositionValidationFailure("result authority ceiling drift")

    cause_branches = schema["allOf"][4]["oneOf"]
    expected_counts = {
        "checked_proof": 1, "checked_refutation": 1,
        "user_cancellation": 1, "parent_cancellation": 1,
        "supervisor_cancellation": 1, "ambiguity": 2,
        "budget_exhaustion": 3, "unsupported_input": 1,
        "unsupported_execution_environment": 2, "producer_refusal": 1,
        "verifier_refusal": 1, "truncation": 1,
        "inconclusive_execution": 1, "checker_disagreement": 1,
        "invalid_evidence": 1, "producer_failure": 1,
        "verifier_failure": 1, "invalid_request": 1, "internal_error": 1,
    }
    observed_counts = {name: 0 for name in expected_counts}
    indexed: dict[str, list[dict[str, Any]]] = {name: [] for name in expected_counts}
    reason_owners: dict[str, set[str]] = {}
    for branch in cause_branches:
        causes = _flatten_values(branch, "cause")
        if not causes:
            raise ExecutionDispositionValidationFailure("result cause branch is open")
        for cause_value in causes:
            cause = str(cause_value)
            if cause not in observed_counts:
                raise ExecutionDispositionValidationFailure(
                    f"result emits reserved or unknown cause: {cause}"
                )
            observed_counts[cause] += 1
            indexed[cause].append(branch)
            for reason in _flatten_values(branch, "portfolio_reason_code"):
                reason_owners.setdefault(str(reason), set()).add(cause)
    if observed_counts != expected_counts:
        raise ExecutionDispositionValidationFailure("result cause branch matrix drift")

    ambiguity_variants = {
        (_branch_reference(branch), tuple(sorted(_flatten_values(branch, "precedence_row"))), tuple(sorted(_flatten_values(branch, "phase"))))
        for branch in indexed["ambiguity"]
    }
    if ambiguity_variants != {
        ("early_normal_result", ("20_early_route_planner",), ("routing",)),
        ("audited_normal_result", ("80_semantic_terminal",), ("producer",)),
    }:
        raise ExecutionDispositionValidationFailure("ambiguity variant relation drift")
    budget_variants = {
        (_branch_reference(branch), tuple(sorted(_flatten_values(branch, "precedence_row"))), tuple(sorted(_flatten_values(branch, "phase"))))
        for branch in indexed["budget_exhaustion"]
    }
    if budget_variants != {
        ("early_normal_result", ("20_early_route_planner",), ("routing",)),
        ("early_normal_result", ("20_early_route_planner",), ("planning",)),
        ("audited_normal_result", ("50_ledger_exhaustion",), ()),
    }:
        raise ExecutionDispositionValidationFailure("budget variant relation drift")
    audited_budget = next(
        branch
        for branch in indexed["budget_exhaustion"]
        if _branch_reference(branch) == "audited_normal_result"
    )
    budget_detail = audited_budget["allOf"][1]["oneOf"]
    dimension_by_reason: dict[str, tuple[object, ...]] = {}
    for branch in budget_detail:
        reasons = _flatten_values(branch, "portfolio_reason_code")
        if len(reasons) != 1:
            raise ExecutionDispositionValidationFailure(
                "budget reason branch is not exact"
            )
        reason = str(next(iter(reasons)))
        dimensions = _find_constraints(branch, "resource_dimensions")
        dimension_by_reason[reason] = (
            tuple(dimensions[0]["const"])
            if len(dimensions) == 1 and type(dimensions[0].get("const")) is list
            else ()
        )
    if dimension_by_reason != {
        "BUDGET_INSUFFICIENT": (),
        "WALL_TIME_EXHAUSTED": ("wall_time_us",),
        "CPU_TIME_EXHAUSTED": ("cpu_time_us",),
        "MEMORY_EXHAUSTED": ("memory_bytes",),
        "OUTPUT_EXHAUSTED": ("output_bytes",),
        "DIAGNOSTIC_EXHAUSTED": ("diagnostic_bytes",),
    }:
        raise ExecutionDispositionValidationFailure(
            "budget reason-dimension matrix drift"
        )
    environment_variants = {
        (_branch_reference(branch), tuple(sorted(_flatten_values(branch, "precedence_row"))))
        for branch in indexed["unsupported_execution_environment"]
    }
    if environment_variants != {
        ("early_normal_result", ("20_early_route_planner",)),
        ("audited_normal_result", ("60_environment_refusal",)),
    }:
        raise ExecutionDispositionValidationFailure("environment variant relation drift")

    exact_owners = {
        "CANCELLED": {"user_cancellation", "parent_cancellation", "supervisor_cancellation"},
        "EVIDENCE_CANCELLED": {"producer_refusal"},
        "EVIDENCE_EXHAUSTED": {"producer_refusal"},
        "CHECKER_CANCELLED": {"verifier_refusal"},
        "CHECKER_EXHAUSTED": {"verifier_refusal"},
        "WALL_TIME_EXHAUSTED": {"budget_exhaustion"},
        "CPU_TIME_EXHAUSTED": {"budget_exhaustion"},
        "MEMORY_EXHAUSTED": {"budget_exhaustion"},
        "OUTPUT_EXHAUSTED": {"budget_exhaustion"},
        "DIAGNOSTIC_EXHAUSTED": {"budget_exhaustion"},
        "EXIT_FAILED": {"producer_failure", "verifier_failure"},
        "PROTOCOL_FAILED": {"producer_failure", "verifier_failure"},
        "LAUNCH_FAILED": {"producer_failure", "verifier_failure"},
        "CHECKER_INCONCLUSIVE": {
            "verifier_refusal", "inconclusive_execution",
        },
        "EXECUTABLE_INVALID": {
            "producer_refusal", "verifier_refusal", "internal_error",
        },
        "REQUEST_INVALID": {"internal_error"},
        "PLAN_INVALID": {"internal_error"},
        "STRATEGY_MISMATCH": {"internal_error"},
        "BUDGET_INVALID": {"internal_error"},
        "TREE_CLEANUP_FAILED": {"internal_error"},
        "SUPERVISOR_FAILED": {"internal_error"},
        "PORTFOLIO_INPUT_INVALID": {"internal_error"},
        "PORTFOLIO_EXECUTION_INVALID": {"internal_error"},
    }
    for reason, owners in exact_owners.items():
        if reason_owners.get(reason) != owners:
            raise ExecutionDispositionValidationFailure(
                f"result reason ownership drift: {reason}"
            )
    invalid_codes = _flatten_values(indexed["invalid_request"][0], "code")
    internal = indexed["internal_error"][0]
    internal_codes = _flatten_values(internal, "code")
    if invalid_codes != {
        "REQUEST_INVALID", "INTENT_EVENT_MISMATCH",
        "RESERVED_EXTENSION_COLLISION", "ROUTE_INPUT_INVALID",
        "PLANNING_INPUT_INVALID", "BINDING_INPUT_INVALID",
        "ARTIFACT_INPUT_INVALID", "EXECUTION_INPUT_INVALID",
    }:
        raise ExecutionDispositionValidationFailure(
            "invalid-request diagnostic ownership drift"
        )
    invalid_variants = {
        (
            tuple(sorted(_definition_references(branch))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "code"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "phase"))),
        )
        for branch in indexed["invalid_request"][0]["oneOf"]
    }
    if invalid_variants != {
        (("empty_preflight_result",), ("REQUEST_INVALID",), ("request",)),
        (
            ("validated_pre_route_result",),
            ("ARTIFACT_INPUT_INVALID", "BINDING_INPUT_INVALID", "INTENT_EVENT_MISMATCH"),
            ("request",),
        ),
        (("validated_pre_route_result",), ("ROUTE_INPUT_INVALID",), ("routing",)),
        (("invalid_route_result",), ("ROUTE_INPUT_INVALID",), ("routing",)),
        (
            ("invalid_planning_result",),
            ("ARTIFACT_INPUT_INVALID", "PLANNING_INPUT_INVALID"),
            ("planning",),
        ),
        (("planned_no_budget_result",), ("BINDING_INPUT_INVALID",), ("planning",)),
        (("planned_no_budget_result",), ("EXECUTION_INPUT_INVALID",), ("coordinator",)),
        (("planned_unanchored_result",), ("RESERVED_EXTENSION_COLLISION",), ("coordinator",)),
    }:
        raise ExecutionDispositionValidationFailure(
            "invalid-request reached-evidence matrix drift"
        )
    if internal_codes != {
        "BUDGET_ANCHOR_INVALID", "PORTFOLIO_REQUEST_INVALID",
        "AUDITED_EXECUTION_INVALID", "AUDIT_REPLAY_INVALID",
        "AUDIT_REPLAY_EXHAUSTED", "AUDIT_RELATION_INVALID",
        "CLEANUP_INVARIANT", "SUPERVISOR_INVARIANT",
        "WORKER_REQUEST_INVARIANT", "WORKER_PLAN_INVARIANT",
        "WORKER_STRATEGY_INVARIANT", "WORKER_BUDGET_INVARIANT",
        "WORKER_EXECUTABLE_INVARIANT", "PORTFOLIO_INPUT_INVARIANT",
        "PORTFOLIO_EXECUTION_INVARIANT", "COORDINATOR_LIMIT_EXHAUSTED",
    }:
        raise ExecutionDispositionValidationFailure(
            "internal-error diagnostic ownership drift"
        )
    internal_by_phase = {
        branch["properties"]["classification"]["properties"]["phase"]["const"]:
        branch
        for branch in internal["oneOf"]
    }
    if set(internal_by_phase) != {"cleanup", "audit", "replay", "coordinator"}:
        raise ExecutionDispositionValidationFailure("internal phase matrix drift")
    cleanup_state = internal_by_phase["cleanup"]["properties"]["execution_state"]
    audit_states = internal_by_phase["audit"]["properties"]["execution_state"]
    replay_states = internal_by_phase["replay"]["properties"]["execution_state"]
    if (
        cleanup_state.get("const") != "replayed_complete"
        or tuple(audit_states.get("enum", ()))
        != ("attempted_no_bundle", "replayed_complete")
        or replay_states.get("const") != "bundle_replay_failed"
    ):
        raise ExecutionDispositionValidationFailure(
            "internal execution-state/phase relation drift"
        )
    cleanup = internal_by_phase["cleanup"]
    if (
        _flatten_values(cleanup, "portfolio_relation") != {"exact"}
        or _flatten_values(cleanup, "portfolio_status")
        != {"failed", "verifier_failed"}
        or _flatten_values(cleanup, "portfolio_reason_code")
        != {"TREE_CLEANUP_FAILED"}
        or _flatten_values(cleanup, "code") != {"CLEANUP_INVARIANT"}
    ):
        raise ExecutionDispositionValidationFailure(
            "cleanup invariant ownership drift"
        )
    audit = internal_by_phase["audit"]
    audit_by_code = {
        str(next(iter(codes))): branch
        for branch in audit["oneOf"]
        if len(codes := _flatten_values(branch, "code")) == 1
    }
    if set(audit_by_code) != {
        "AUDITED_EXECUTION_INVALID", "AUDIT_RELATION_INVALID"
    }:
        raise ExecutionDispositionValidationFailure("audit diagnostic ownership drift")
    relation_branch = audit_by_code["AUDIT_RELATION_INVALID"]
    if (
        _definition_references(relation_branch) != {"portfolio_pair"}
        or _flatten_values(relation_branch, "execution_state")
        != {"replayed_complete"}
        or _flatten_values(relation_branch, "portfolio_relation") != {"invalid"}
    ):
        raise ExecutionDispositionValidationFailure(
            "audit relation-invalid evidence profile drift"
        )
    replay = internal_by_phase["replay"]
    replay_by_code = {
        str(next(iter(codes))): branch
        for branch in replay["oneOf"]
        if len(codes := _flatten_values(branch, "code")) == 1
    }
    if set(replay_by_code) != {
        "AUDIT_REPLAY_INVALID", "AUDIT_REPLAY_EXHAUSTED"
    }:
        raise ExecutionDispositionValidationFailure("replay diagnostic ownership drift")
    coordinator = internal_by_phase["coordinator"]
    coordinator_branches = coordinator["oneOf"]
    coordinator_by_code = {
        str(next(iter(codes))): branch
        for branch in coordinator_branches
        if len(codes := _flatten_values(branch, "code")) == 1
    }
    if set(coordinator_by_code) != {
        "BUDGET_ANCHOR_INVALID",
        "PORTFOLIO_REQUEST_INVALID",
        "SUPERVISOR_INVARIANT",
        "WORKER_REQUEST_INVARIANT",
        "WORKER_PLAN_INVARIANT",
        "WORKER_STRATEGY_INVARIANT",
        "WORKER_BUDGET_INVARIANT",
        "WORKER_EXECUTABLE_INVARIANT",
        "PORTFOLIO_INPUT_INVARIANT",
        "PORTFOLIO_EXECUTION_INVARIANT",
        "COORDINATOR_LIMIT_EXHAUSTED",
    }:
        raise ExecutionDispositionValidationFailure(
            "coordinator diagnostic branch matrix drift"
        )
    expected_prelaunch = {
        "BUDGET_ANCHOR_INVALID": "planned_unanchored_result",
        "PORTFOLIO_REQUEST_INVALID": "planned_anchored_result",
    }
    for code, reference in expected_prelaunch.items():
        branch = coordinator_by_code[code]
        if (
            _definition_references(branch) != {reference}
            or _flatten_values(branch, "execution_state") != {"not_started"}
        ):
            raise ExecutionDispositionValidationFailure(
                f"prelaunch coordinator milestone drift: {code}"
            )
    limit_branch = coordinator_by_code["COORDINATOR_LIMIT_EXHAUSTED"]
    if (
        _definition_references(limit_branch) != {"empty_preflight_result"}
        or _flatten_values(limit_branch, "execution_state") != {"not_started"}
    ):
        raise ExecutionDispositionValidationFailure(
            "coordinator limit preflight profile drift"
        )
    exact_coordinator_pairs = {
        "WORKER_REQUEST_INVARIANT": (
            {"failed", "verifier_failed"}, {"REQUEST_INVALID"}, {"exact"}, set()
        ),
        "WORKER_PLAN_INVARIANT": (
            {"failed", "verifier_failed"}, {"PLAN_INVALID"}, {"exact"}, set()
        ),
        "WORKER_STRATEGY_INVARIANT": (
            {"failed", "verifier_failed"}, {"STRATEGY_MISMATCH"}, {"exact"}, set()
        ),
        "WORKER_BUDGET_INVARIANT": (
            {"failed", "verifier_failed"}, {"BUDGET_INVALID"}, {"exact"}, set()
        ),
        "WORKER_EXECUTABLE_INVARIANT": (
            {"failed", "verifier_failed"},
            {"EXECUTABLE_INVALID"},
            {"exact"},
            {"executable_invalid"},
        ),
        "SUPERVISOR_INVARIANT": (
            {"failed", "verifier_failed"}, {"SUPERVISOR_FAILED"}, {"exact"}, set()
        ),
        "PORTFOLIO_INPUT_INVARIANT": (
            {"invalid"}, {"PORTFOLIO_INPUT_INVALID"}, {"exact"}, set()
        ),
        "PORTFOLIO_EXECUTION_INVARIANT": (
            {"invalid"}, {"PORTFOLIO_EXECUTION_INVALID"}, {"exact"}, set()
        ),
    }
    for code, (statuses, reasons, relations, outcome_kinds) in exact_coordinator_pairs.items():
        branch = coordinator_by_code[code]
        if (
            _flatten_values(branch, "execution_state") != {"replayed_complete"}
            or _flatten_values(branch, "portfolio_status") != statuses
            or _flatten_values(branch, "portfolio_reason_code") != reasons
            or _flatten_values(branch, "portfolio_relation") != relations
            or _flatten_values(branch, "portfolio_outcome_kind") != outcome_kinds
        ):
            raise ExecutionDispositionValidationFailure(
                f"coordinator terminal invariant mapping drift: {code}"
            )


def _schema_checks() -> dict[str, str]:
    observed: dict[str, str] = {}
    schemas: dict[str, dict[str, Any]] = {}
    for name, expected_sha256 in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        raw = path.read_bytes()
        value = _load_json(path)
        if (
            _sha(raw) != expected_sha256
            or value.get("$schema")
            != SCHEMA_DIALECT
            or value.get("type") != "object"
            or value.get("additionalProperties") is not False
            or set(value.get("required", ())) != set(value.get("properties", {}))
        ):
            raise ExecutionDispositionValidationFailure(
                f"closed schema binding drift: {name}"
            )
        observed[name] = expected_sha256
        schemas[name] = value
    _schema_graph_check(schemas)
    _classification_schema_check(
        schemas["execution-disposition-classification-v1.schema.json"]
    )
    _diagnostic_schema_check(
        schemas["execution-disposition-diagnostic-v1.schema.json"]
    )
    _request_schema_check(schemas["execution-disposition-request-v1.schema.json"])
    _result_schema_check(schemas["execution-disposition-result-v1.schema.json"])
    return observed


def _contract_registration_check() -> dict[str, str] | None:
    accepted = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
    proposed = ROOT / "docs/contracts/proposed" / f"{CONTRACT_ID}.json"
    if not proposed.exists():
        return None
    proposal_raw = proposed.read_bytes()
    if proposal_raw != _canonical(json.loads(proposal_raw)):
        raise ExecutionDispositionValidationFailure("proposal is not canonical")
    if _sha(proposal_raw) != CONTRACT_SHA256:
        raise ExecutionDispositionValidationFailure(
            "compiled execution-disposition contract identity drift"
        )
    manifest = tomllib.loads(
        (ROOT / "docs/contracts/manifest.toml").read_text(encoding="utf-8")
    )
    entries = [
        item
        for item in manifest.get("contracts", ())
        if item.get("id") == CONTRACT_ID
    ]
    if len(entries) != 1 or entries[0].get("sha256") != CONTRACT_SHA256:
        raise ExecutionDispositionValidationFailure("contract manifest binding drift")
    state = str(entries[0].get("state"))
    if state == "accepted":
        if not accepted.exists() or accepted.read_bytes() != proposal_raw:
            raise ExecutionDispositionValidationFailure(
                "accepted artifact differs from its proposal"
            )
    elif state != "proposed":
        raise ExecutionDispositionValidationFailure("unexpected contract state")
    return {"sha256": _sha(proposal_raw), "state": state}


def _base_budget() -> bytes:
    return _canonical(
        {
            "schema": "mathhead.resource-budget.v1",
            "budget_id": "budget_disposition_anchor_vector",
            "lineage": {"kind": "root"},
            "policy": {
                "wall_clock": "monotonic_elapsed_us",
                "deadline": "relative_to_start",
                "cpu_accounting": "exclusive_budget_scope_us",
                "memory_accounting": "inclusive_active_process_tree_bytes",
                "integer_rounding": "ceil",
                "reservation": "conservative_all_dimensions",
            },
            "limits": {name: 1 for name in RESOURCE_DIMENSIONS},
            "events": [],
            "outcome": {"status": "open"},
            "extensions": {"org.mathhead.fixture": {"preserved": True}},
        }
    )


def _derive_anchor(base: bytes, disposition_request_sha256: str) -> bytes:
    from mathhead.isolated_worker import _parse_parent_budget

    if (
        type(disposition_request_sha256) is not str
        or re.fullmatch(r"[0-9a-f]{64}", disposition_request_sha256) is None
    ):
        raise ExecutionDispositionValidationFailure(
            "disposition request identity is not a lowercase SHA-256"
        )
    _parse_parent_budget(base)
    mapping = json.loads(base)
    extensions = mapping["extensions"]
    if type(extensions) is not dict or RESERVED_EXTENSION in extensions:
        raise ExecutionDispositionValidationFailure("reserved anchor collision")
    extensions[RESERVED_EXTENSION] = {
        "disposition_request_sha256": disposition_request_sha256
    }
    anchored = _canonical(mapping)
    _parse_parent_budget(anchored)
    return anchored


def _anchor_check() -> dict[str, str]:
    request_sha256 = "a" * 64
    base = _base_budget()
    anchored = _derive_anchor(base, request_sha256)
    if anchored == base or _sha(anchored) == _sha(base):
        raise ExecutionDispositionValidationFailure("anchor did not change identity")
    stripped = json.loads(anchored)
    stripped_extensions = stripped["extensions"]
    if type(stripped_extensions) is not dict:
        raise ExecutionDispositionValidationFailure("invalid anchored extensions")
    del stripped_extensions[RESERVED_EXTENSION]
    if _canonical(stripped) != base:
        raise ExecutionDispositionValidationFailure("strip-only round trip differs")
    if stripped_extensions != {"org.mathhead.fixture": {"preserved": True}}:
        raise ExecutionDispositionValidationFailure("unowned extension changed")
    collision = json.loads(base)
    collision["extensions"][RESERVED_EXTENSION] = {
        "disposition_request_sha256": request_sha256
    }
    try:
        _derive_anchor(_canonical(collision), request_sha256)
    except ExecutionDispositionValidationFailure:
        pass
    else:
        raise ExecutionDispositionValidationFailure("reserved collision was accepted")
    for invalid_digest in ("A" * 64, "a" * 63):
        try:
            _derive_anchor(base, invalid_digest)
        except ExecutionDispositionValidationFailure:
            pass
        else:
            raise ExecutionDispositionValidationFailure("invalid anchor digest accepted")
    return {
        "base_parent_budget_sha256": _sha(base),
        "anchored_parent_budget_sha256": _sha(anchored),
        "disposition_request_sha256": request_sha256,
    }


def _identity_projection_check() -> dict[str, str]:
    digest_a = "a" * 64
    digest_b = "b" * 64
    artifact_bindings = [
        {"role": "problem", "sha256": digest_b, "byte_count": 7}
    ]
    projection: dict[str, object] = {
        "schema": "mathhead.execution-disposition-invocation.v1",
        "invocation_id": "invocation_fixture",
        "planning_request_sha256": digest_a,
        "route_result_sha256": digest_b,
        "planning_result_sha256": "c" * 64,
        "base_parent_budget_sha256": "d" * 64,
        "descriptor_sha256s": [digest_a],
        "binding_sha256s": [digest_b],
        "artifact_bindings": artifact_bindings,
        "cancellation_armed": True,
        "mathematical_authority": False,
    }
    if set(projection) != INVOCATION_FIELDS:
        raise ExecutionDispositionValidationFailure("invocation projection field drift")
    invocation_sha256 = _sha(_canonical(projection))
    intent: dict[str, object] = {
        "schema": "mathhead.cancellation-intent.v1",
        "intent_id": "intent_fixture",
        "origin_source": "user",
        "reason_code": "requested",
        "invocation_id": "invocation_fixture",
        "invocation_sha256": invocation_sha256,
        "base_parent_budget_sha256": "d" * 64,
        "policy_contract_id": CONTRACT_ID,
        "policy_contract_sha256": CONTRACT_SHA256,
        "intent_sha256": None,
        "mathematical_authority": False,
    }
    intent_sha256 = _sha(_canonical(intent))
    intent["intent_sha256"] = intent_sha256
    request: dict[str, object] = {
        "schema": "mathhead.execution-disposition-request.v1",
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "invocation_id": "invocation_fixture",
        "planning_request_sha256": digest_a,
        "route_result_sha256": digest_b,
        "planning_result_sha256": "c" * 64,
        "base_parent_budget_sha256": "d" * 64,
        "descriptor_sha256s": [digest_a],
        "binding_sha256s": [digest_b],
        "artifact_bindings": artifact_bindings,
        "cancellation_armed": True,
        "cancellation_intent": intent,
        "invocation_sha256": invocation_sha256,
        "request_sha256": None,
        "mathematical_authority": False,
    }
    request_sha256 = _sha(_canonical(request))
    request["request_sha256"] = request_sha256
    raw_request_sha256 = _sha(_canonical(request))
    if raw_request_sha256 == request_sha256:
        raise ExecutionDispositionValidationFailure(
            "raw request identity collapsed into request self-identity"
        )
    changed = dict(projection)
    changed["planning_result_sha256"] = "f" * 64
    if _sha(_canonical(changed)) == invocation_sha256:
        raise ExecutionDispositionValidationFailure(
            "invocation projection does not bind semantic inputs"
        )
    result_projection = {
        "disposition_request_sha256": request_sha256,
        "invocation_sha256": invocation_sha256,
        "cancellation_armed": True,
        "cancellation_intent_sha256": intent_sha256,
    }
    _validate_result_request_projection(request, result_projection)
    request_input = _canonical(request)
    full_result = {name: None for name in RESULT_FIELDS}
    full_result.update(
        {
            "schema": "mathhead.execution-disposition-result.v1",
            "contract_id": CONTRACT_ID,
            "contract_sha256": CONTRACT_SHA256,
            "request_input_sha256": _sha(request_input),
            **result_projection,
            "diagnostics": [],
            "authority_ceiling": "none",
            "result_sha256": None,
            "mathematical_authority": False,
        }
    )
    full_result["result_sha256"] = _sha(_canonical(full_result))
    _validate_result_request_projection(
        request, full_result, request_input=request_input
    )
    for field, replacement in (
        ("contract_sha256", "f" * 64),
        ("request_input_sha256", "f" * 64),
    ):
        forged_full_result = dict(full_result)
        forged_full_result[field] = replacement
        forged_full_result["result_sha256"] = None
        forged_full_result["result_sha256"] = _sha(_canonical(forged_full_result))
        try:
            _validate_result_request_projection(
                request, forged_full_result, request_input=request_input
            )
        except ExecutionDispositionValidationFailure:
            pass
        else:
            raise ExecutionDispositionValidationFailure(
                f"forged full result identity accepted: {field}"
            )
    transplanted_request_input = b"{}\n"
    transplanted_full_result = dict(full_result)
    transplanted_full_result["request_input_sha256"] = _sha(
        transplanted_request_input
    )
    transplanted_full_result["result_sha256"] = None
    transplanted_full_result["result_sha256"] = _sha(
        _canonical(transplanted_full_result)
    )
    try:
        _validate_result_request_projection(
            request,
            transplanted_full_result,
            request_input=transplanted_request_input,
        )
    except ExecutionDispositionValidationFailure:
        pass
    else:
        raise ExecutionDispositionValidationFailure(
            "retained request accepted against a rehashed raw-byte transplant"
        )
    forged_full_result = dict(full_result)
    forged_full_result["result_sha256"] = "f" * 64
    try:
        _validate_result_request_projection(
            request, forged_full_result, request_input=request_input
        )
    except ExecutionDispositionValidationFailure:
        pass
    else:
        raise ExecutionDispositionValidationFailure(
            "forged full result self-identity accepted"
        )
    invalid_request_input = b'{"malformed":\n'
    invalid_full_result = {name: None for name in RESULT_FIELDS}
    invalid_full_result.update(
        {
            "schema": "mathhead.execution-disposition-result.v1",
            "contract_id": CONTRACT_ID,
            "contract_sha256": CONTRACT_SHA256,
            "request_input_sha256": _sha(invalid_request_input),
            "diagnostics": [],
            "authority_ceiling": "none",
            "result_sha256": None,
            "mathematical_authority": False,
        }
    )
    invalid_full_result["result_sha256"] = _sha(_canonical(invalid_full_result))
    _validate_result_request_projection(
        None, invalid_full_result, request_input=invalid_request_input
    )
    try:
        _validate_result_request_projection(
            None, invalid_full_result, request_input=b'{"different":\n'
        )
    except ExecutionDispositionValidationFailure:
        pass
    else:
        raise ExecutionDispositionValidationFailure(
            "invalid-request result accepted against different raw bytes"
        )
    for field, replacement in (
        ("disposition_request_sha256", "f" * 64),
        ("invocation_sha256", "f" * 64),
        ("cancellation_armed", False),
        ("cancellation_armed", 1),
        ("cancellation_intent_sha256", "f" * 64),
        ("cancellation_intent_sha256", None),
    ):
        forged = dict(result_projection)
        forged[field] = replacement
        try:
            _validate_result_request_projection(request, forged)
        except ExecutionDispositionValidationFailure:
            pass
        else:
            raise ExecutionDispositionValidationFailure(
                f"forged result request projection accepted: {field}"
            )

    def require_rejected(
        label: str,
        forged_request: dict[str, object],
        forged_result: dict[str, object],
    ) -> None:
        try:
            _validate_result_request_projection(forged_request, forged_result)
        except ExecutionDispositionValidationFailure:
            return
        raise ExecutionDispositionValidationFailure(
            f"forged retained request accepted: {label}"
        )

    def different_digest(value: str) -> str:
        return ("0" if value[0] != "0" else "1") + value[1:]

    forged_intent = dict(intent)
    forged_intent_sha256 = different_digest(intent_sha256)
    forged_intent["intent_sha256"] = forged_intent_sha256
    forged_intent_request = dict(request)
    forged_intent_request["cancellation_intent"] = forged_intent
    forged_intent_request["request_sha256"] = None
    forged_intent_request_sha256 = _sha(_canonical(forged_intent_request))
    forged_intent_request["request_sha256"] = forged_intent_request_sha256
    require_rejected(
        "intent digest plus matching result",
        forged_intent_request,
        {
            "disposition_request_sha256": forged_intent_request_sha256,
            "invocation_sha256": invocation_sha256,
            "cancellation_armed": True,
            "cancellation_intent_sha256": forged_intent_sha256,
        },
    )

    forged_request = dict(request)
    forged_request_sha256 = different_digest(request_sha256)
    forged_request["request_sha256"] = forged_request_sha256
    require_rejected(
        "request digest plus matching result",
        forged_request,
        {
            **result_projection,
            "disposition_request_sha256": forged_request_sha256,
        },
    )

    forged_policy_request = json.loads(json.dumps(request))
    forged_policy_intent = forged_policy_request["cancellation_intent"]
    forged_policy_intent["policy_contract_sha256"] = "f" * 64
    forged_policy_intent["intent_sha256"] = None
    forged_policy_intent_sha256 = _sha(_canonical(forged_policy_intent))
    forged_policy_intent["intent_sha256"] = forged_policy_intent_sha256
    forged_policy_request["contract_sha256"] = "f" * 64
    forged_policy_request["request_sha256"] = None
    forged_policy_request_sha256 = _sha(_canonical(forged_policy_request))
    forged_policy_request["request_sha256"] = forged_policy_request_sha256
    require_rejected(
        "contract and policy identities plus matching inner and outer hashes",
        forged_policy_request,
        {
            "disposition_request_sha256": forged_policy_request_sha256,
            "invocation_sha256": invocation_sha256,
            "cancellation_armed": True,
            "cancellation_intent_sha256": forged_policy_intent_sha256,
        },
    )

    forged_intent_policy_request = json.loads(json.dumps(request))
    forged_intent_policy = forged_intent_policy_request["cancellation_intent"]
    forged_intent_policy["policy_contract_sha256"] = "f" * 64
    forged_intent_policy["intent_sha256"] = None
    forged_intent_policy_sha256 = _sha(_canonical(forged_intent_policy))
    forged_intent_policy["intent_sha256"] = forged_intent_policy_sha256
    forged_intent_policy_request["request_sha256"] = None
    forged_intent_policy_request_sha256 = _sha(
        _canonical(forged_intent_policy_request)
    )
    forged_intent_policy_request["request_sha256"] = (
        forged_intent_policy_request_sha256
    )
    require_rejected(
        "intent policy identity plus matching inner and outer hashes",
        forged_intent_policy_request,
        {
            "disposition_request_sha256": forged_intent_policy_request_sha256,
            "invocation_sha256": invocation_sha256,
            "cancellation_armed": True,
            "cancellation_intent_sha256": forged_intent_policy_sha256,
        },
    )

    unarmed_request = dict(request)
    unarmed_request["cancellation_armed"] = False
    unarmed_projection = {
        name: unarmed_request[name] for name in INVOCATION_FIELDS
    }
    unarmed_projection["schema"] = "mathhead.execution-disposition-invocation.v1"
    unarmed_invocation_sha256 = _sha(_canonical(unarmed_projection))
    unarmed_request["invocation_sha256"] = unarmed_invocation_sha256
    unarmed_intent = dict(intent)
    unarmed_intent["invocation_sha256"] = unarmed_invocation_sha256
    unarmed_intent["intent_sha256"] = None
    unarmed_intent_sha256 = _sha(_canonical(unarmed_intent))
    unarmed_intent["intent_sha256"] = unarmed_intent_sha256
    unarmed_request["cancellation_intent"] = unarmed_intent
    unarmed_request["request_sha256"] = None
    unarmed_request_sha256 = _sha(_canonical(unarmed_request))
    unarmed_request["request_sha256"] = unarmed_request_sha256
    require_rejected(
        "unarmed request retaining intent",
        unarmed_request,
        {
            "disposition_request_sha256": unarmed_request_sha256,
            "invocation_sha256": unarmed_invocation_sha256,
            "cancellation_armed": False,
            "cancellation_intent_sha256": None,
        },
    )
    valid_unarmed_request = dict(unarmed_request)
    valid_unarmed_request["cancellation_intent"] = None
    valid_unarmed_request["request_sha256"] = None
    valid_unarmed_request_sha256 = _sha(_canonical(valid_unarmed_request))
    valid_unarmed_request["request_sha256"] = valid_unarmed_request_sha256
    valid_unarmed_result = {
        "disposition_request_sha256": valid_unarmed_request_sha256,
        "invocation_sha256": unarmed_invocation_sha256,
        "cancellation_armed": False,
        "cancellation_intent_sha256": None,
    }
    _validate_result_request_projection(valid_unarmed_request, valid_unarmed_result)
    require_rejected(
        "integer zero substituted for false armed flag",
        valid_unarmed_request,
        {**valid_unarmed_result, "cancellation_armed": 0},
    )
    _validate_result_request_projection(
        None,
        {
            "disposition_request_sha256": None,
            "invocation_sha256": None,
            "cancellation_armed": None,
            "cancellation_intent_sha256": None,
        },
    )
    return {
        "invocation_sha256": invocation_sha256,
        "intent_sha256": intent_sha256,
        "request_sha256": request_sha256,
        "request_input_sha256": raw_request_sha256,
        "request_result_relation": "passed",
    }


def _validate_result_request_projection(
    request: dict[str, object] | None,
    result: dict[str, object],
    *,
    request_input: bytes | None = None,
) -> None:
    result_fields = set(result) if type(result) is dict else set()
    if (
        type(result) is not dict
        or any(type(name) is not str for name in result)
        or result_fields not in {RESULT_REQUEST_PROJECTION_FIELDS, RESULT_FIELDS}
    ):
        raise ExecutionDispositionValidationFailure(
            "result request projection fields are not closed"
        )
    full_result = result_fields == RESULT_FIELDS
    if full_result:
        if (
            type(request_input) is not bytes
            or type(result["schema"]) is not str
            or result["schema"] != "mathhead.execution-disposition-result.v1"
            or type(result["contract_id"]) is not str
            or result["contract_id"] != CONTRACT_ID
            or type(result["contract_sha256"]) is not str
            or result["contract_sha256"] != CONTRACT_SHA256
            or type(result["request_input_sha256"]) is not str
            or result["request_input_sha256"] != _sha(request_input)
            or result["mathematical_authority"] is not False
        ):
            raise ExecutionDispositionValidationFailure(
                "full result contract or raw-request identity is invalid"
            )
        if request is not None and request_input != _canonical(request):
            raise ExecutionDispositionValidationFailure(
                "retained request differs from the exact raw request bytes"
            )
        result_sha256 = result["result_sha256"]
        if (
            type(result_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", result_sha256) is None
        ):
            raise ExecutionDispositionValidationFailure(
                "full result self-identity is malformed"
            )
        result_preimage = dict(result)
        result_preimage["result_sha256"] = None
        if _sha(_canonical(result_preimage)) != result_sha256:
            raise ExecutionDispositionValidationFailure(
                "full result self-identity is invalid"
            )
    elif request_input is not None:
        raise ExecutionDispositionValidationFailure(
            "raw request bytes require a full result"
        )
    if request is None:
        expected: tuple[object, object, object, object] = (None, None, None, None)
    else:
        if (
            type(request) is not dict
            or any(type(name) is not str for name in request)
            or set(request) != REQUEST_FIELDS
        ):
            raise ExecutionDispositionValidationFailure(
                "retained request does not have the closed schema fields"
            )
        if (
            type(request["schema"]) is not str
            or request["schema"] != "mathhead.execution-disposition-request.v1"
            or type(request["contract_id"]) is not str
            or request["contract_id"] != CONTRACT_ID
            or request["mathematical_authority"] is not False
        ):
            raise ExecutionDispositionValidationFailure(
                "retained request schema identity is invalid"
            )

        def require_sha256(value: object, *, label: str) -> str:
            if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
                raise ExecutionDispositionValidationFailure(
                    f"retained request has invalid {label}"
                )
            return value

        def require_id(value: object, *, label: str) -> str:
            if (
                type(value) is not str
                or re.fullmatch(r"[a-z][a-z0-9_.-]{0,254}", value) is None
            ):
                raise ExecutionDispositionValidationFailure(
                    f"retained request has invalid {label}"
                )
            return value

        request_sha256 = require_sha256(
            request["request_sha256"], label="request self-identity"
        )
        invocation_sha256 = require_sha256(
            request["invocation_sha256"], label="invocation identity"
        )
        contract_sha256 = require_sha256(
            request["contract_sha256"], label="contract identity"
        )
        if contract_sha256 != CONTRACT_SHA256:
            raise ExecutionDispositionValidationFailure(
                "retained request contract identity is not accepted"
            )
        require_id(request["invocation_id"], label="invocation ID")
        for name in (
            "planning_request_sha256", "route_result_sha256",
            "planning_result_sha256",
        ):
            require_sha256(request[name], label=name)
        base_parent_budget_sha256 = request["base_parent_budget_sha256"]
        if base_parent_budget_sha256 is not None:
            require_sha256(base_parent_budget_sha256, label="base budget identity")

        descriptor_sha256s = request["descriptor_sha256s"]
        binding_sha256s = request["binding_sha256s"]
        artifact_bindings = request["artifact_bindings"]
        if (
            type(descriptor_sha256s) is not list
            or len(descriptor_sha256s) > 10_000
            or any(
                type(value) is not str
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in descriptor_sha256s
            )
            or descriptor_sha256s != sorted(set(descriptor_sha256s))
            or type(binding_sha256s) is not list
            or len(binding_sha256s) > 100_000
            or any(
                type(value) is not str
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in binding_sha256s
            )
            or len(binding_sha256s) != len(set(binding_sha256s))
            or type(artifact_bindings) is not list
            or len(artifact_bindings) > 200_000
        ):
            raise ExecutionDispositionValidationFailure(
                "retained request inventory is not canonical and schema-valid"
            )
        artifact_roles: set[str] = set()
        for binding in artifact_bindings:
            if (
                type(binding) is not dict
                or any(type(name) is not str for name in binding)
                or set(binding) != {"role", "sha256", "byte_count"}
            ):
                raise ExecutionDispositionValidationFailure(
                    "retained request artifact binding is not closed"
                )
            role = binding["role"]
            byte_count = binding["byte_count"]
            if (
                type(role) is not str
                or re.fullmatch(r"[a-z][a-z0-9_.-]{0,254}", role) is None
                or role in artifact_roles
                or type(byte_count) is not int
                or not 0 <= byte_count <= 1_073_741_824
            ):
                raise ExecutionDispositionValidationFailure(
                    "retained request artifact binding is invalid"
                )
            require_sha256(binding["sha256"], label="artifact identity")
            artifact_roles.add(role)

        armed = request["cancellation_armed"]
        intent = request["cancellation_intent"]
        if type(armed) is not bool or (not armed and intent is not None):
            raise ExecutionDispositionValidationFailure(
                "request cancellation projection is malformed"
            )
        if armed:
            if (
                type(intent) is not dict
                or any(type(name) is not str for name in intent)
                or set(intent) != CANCELLATION_INTENT_FIELDS
                or type(intent["schema"]) is not str
                or intent["schema"] != "mathhead.cancellation-intent.v1"
                or type(intent["policy_contract_id"]) is not str
                or intent["policy_contract_id"] != CONTRACT_ID
                or intent["mathematical_authority"] is not False
                or type(intent["origin_source"]) is not str
                or intent["origin_source"] not in {"user", "parent", "supervisor"}
                or type(intent["reason_code"]) is not str
                or intent["reason_code"]
                not in {"requested", "superseded", "shutdown", "policy_stop"}
            ):
                raise ExecutionDispositionValidationFailure(
                    "retained cancellation intent is not schema-valid"
                )
            require_id(intent["intent_id"], label="intent ID")
            require_id(intent["invocation_id"], label="intent invocation ID")
            for name in (
                "invocation_sha256", "base_parent_budget_sha256",
                "policy_contract_sha256", "intent_sha256",
            ):
                require_sha256(intent[name], label=f"intent {name}")
            if intent["policy_contract_sha256"] != CONTRACT_SHA256:
                raise ExecutionDispositionValidationFailure(
                    "retained cancellation intent policy identity is not accepted"
                )
            intent_preimage = dict(intent)
            intent_preimage["intent_sha256"] = None
            intent_sha256 = _sha(_canonical(intent_preimage))
            if intent["intent_sha256"] != intent_sha256:
                raise ExecutionDispositionValidationFailure(
                    "retained cancellation intent self-identity is invalid"
                )
        else:
            intent_sha256 = None

        invocation_projection = {
            name: request[name] for name in INVOCATION_FIELDS
        }
        invocation_projection["schema"] = (
            "mathhead.execution-disposition-invocation.v1"
        )
        if (
            set(invocation_projection) != INVOCATION_FIELDS
            or _sha(_canonical(invocation_projection)) != invocation_sha256
        ):
            raise ExecutionDispositionValidationFailure(
                "retained request invocation projection identity is invalid"
            )
        if armed and (
            intent["invocation_id"] != request["invocation_id"]
            or intent["invocation_sha256"] != invocation_sha256
            or intent["base_parent_budget_sha256"] != base_parent_budget_sha256
            or intent["policy_contract_sha256"] != request["contract_sha256"]
        ):
            raise ExecutionDispositionValidationFailure(
                "retained cancellation intent relation is invalid"
            )
        request_preimage = dict(request)
        request_preimage["request_sha256"] = None
        if _sha(_canonical(request_preimage)) != request_sha256:
            raise ExecutionDispositionValidationFailure(
                "retained request self-identity is invalid"
            )
        expected = (
            request_sha256,
            invocation_sha256,
            armed,
            intent_sha256,
        )
    observed = (
        result.get("disposition_request_sha256"),
        result.get("invocation_sha256"),
        result.get("cancellation_armed"),
        result.get("cancellation_intent_sha256"),
    )
    if request is None:
        exact_projection_types = all(value is None for value in observed)
    else:
        exact_projection_types = (
            type(observed[0]) is str
            and type(observed[1]) is str
            and type(observed[2]) is bool
            and (
                type(observed[3]) is str
                if armed
                else observed[3] is None
            )
        )
    if not exact_projection_types or observed != expected:
        raise ExecutionDispositionValidationFailure(
            "result request/armed/intent projection differs"
        )


def main() -> int:
    report = {
        "schema": "mathhead.execution-disposition-validation-bootstrap.v1",
        "contract": _contract_registration_check(),
        "schemas": _schema_checks(),
        "identity_projection": _identity_projection_check(),
        "anchor": _anchor_check(),
        "production_binding": "deferred_until_contract_acceptance",
        "status": "passed",
    }
    print(_canonical(report).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
