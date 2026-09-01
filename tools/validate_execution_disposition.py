#!/usr/bin/env python3
"""Independently validate the accepted MH-056 production boundary."""

from __future__ import annotations

import argparse
import ast
import copy
from contextlib import ExitStack
from dataclasses import fields, replace
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, NoReturn, Sequence
import unicodedata
from unittest import mock
from urllib.parse import urldefrag, urljoin

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 compatibility
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SOURCE_PATH = ROOT / "src/mathhead/execution_disposition.py"
REPORT_PATH = ROOT / "docs/planning/reports/execution-disposition-v1.json"
REPORT_SCHEMA = "mathhead.execution-disposition-validation-report.v1"
TEST_DIRECTORY = ROOT / "tests/execution_disposition"
TEST_FIXTURE_PATH = TEST_DIRECTORY / "fixtures.py"
CONTRACT_ID = "MH-C-EXECUTION-DISPOSITION-001"
CONTRACT_SHA256 = "64a7950b13449ee942d003d4e56b482b104769db15cd3080a1011a2a45eb4f96"
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
EXPECTED_BUDGET = {
    "additional_fresh_replays": 1,
    "aggregate_artifact_bytes": 1_073_741_824,
    "aggregate_audit_bytes": 2_147_483_648,
    "aggregate_descriptor_bytes": 1_073_741_824,
    "aggregate_input_bytes": 5_368_709_120,
    "artifact_bytes": 1_073_741_824,
    "artifacts": 200_000,
    "attempts": 100_000,
    "audit_events": 1_000_000,
    "audit_objects": 200_000,
    "audited_calls": 1,
    "bindings": 100_000,
    "cancellation_intents": 1,
    "descriptors": 10_000,
    "diagnostics": 1,
    "input_bytes": 1_073_741_824,
    "integer_maximum": 9_007_199_254_740_991,
    "json_nesting": 128,
    "json_nodes": 12_000_000,
    "live_events": 1,
    "replay_operations": 1_000_000_000,
    "strategies": 100_000,
    "string_codepoints": 1_048_576,
}
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_KEYWORDS = frozenset(
    {
        "$defs",
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "const",
        "else",
        "enum",
        "if",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "not",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "then",
        "title",
        "type",
        "uniqueItems",
    }
)
INVOCATION_FIELDS = frozenset(
    {
        "schema",
        "invocation_id",
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "base_parent_budget_sha256",
        "descriptor_sha256s",
        "binding_sha256s",
        "artifact_bindings",
        "cancellation_armed",
        "mathematical_authority",
    }
)
REQUEST_FIELDS = frozenset(
    {
        "schema",
        "contract_id",
        "contract_sha256",
        "invocation_id",
        "planning_request_sha256",
        "route_result_sha256",
        "planning_result_sha256",
        "base_parent_budget_sha256",
        "descriptor_sha256s",
        "binding_sha256s",
        "artifact_bindings",
        "cancellation_armed",
        "cancellation_intent",
        "invocation_sha256",
        "request_sha256",
        "mathematical_authority",
    }
)
CANCELLATION_INTENT_FIELDS = frozenset(
    {
        "schema",
        "intent_id",
        "origin_source",
        "reason_code",
        "invocation_id",
        "invocation_sha256",
        "base_parent_budget_sha256",
        "policy_contract_id",
        "policy_contract_sha256",
        "intent_sha256",
        "mathematical_authority",
    }
)
RESULT_REQUEST_PROJECTION_FIELDS = frozenset(
    {
        "disposition_request_sha256",
        "invocation_sha256",
        "cancellation_armed",
        "cancellation_intent_sha256",
    }
)
RESULT_FIELDS = frozenset(
    {
        "schema",
        "contract_id",
        "contract_sha256",
        "request_input_sha256",
        "disposition_request_sha256",
        "invocation_sha256",
        "cancellation_armed",
        "cancellation_intent_sha256",
        "base_parent_budget_sha256",
        "anchored_parent_budget_sha256",
        "planning_result_sha256",
        "portfolio_request_sha256",
        "audit_manifest_sha256",
        "logical_report_sha256",
        "replay_result_sha256",
        "portfolio_result_sha256",
        "execution_provenance_sha256",
        "execution_state",
        "portfolio_relation",
        "portfolio_outcome_kind",
        "route_status",
        "route_reason_code",
        "planning_status",
        "planning_reason_code",
        "portfolio_status",
        "portfolio_reason_code",
        "replay_status",
        "replay_reason_code",
        "classification",
        "diagnostics",
        "selected_strategy_sha256",
        "selected_evidence_sha256",
        "selected_certificate_sha256",
        "selected_checker_decision_sha256",
        "linked_authority_tier",
        "authority_ceiling",
        "result_sha256",
        "mathematical_authority",
    }
)


class ExecutionDispositionValidationFailure(RuntimeError):
    """Raised when an independently reconstructed MH-056 invariant drifts."""


class _IndependentReplayExhausted(RuntimeError):
    """Raised when the validator's independent replay oracle crosses a ceiling."""


class _IndependentReplayInvalid(ValueError):
    """Raised for a value that production must exclude from replay node charging."""


def _fail(detail: str) -> NoReturn:
    raise ExecutionDispositionValidationFailure(detail)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("ascii")


def _self_hash(value: dict[str, object], field: str) -> str:
    basis = copy.deepcopy(value)
    basis[field] = None
    return _sha(_canonical(basis))


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExecutionDispositionValidationFailure(f"duplicate JSON key in schema: {key}")
        result[key] = value
    return result


def _independent_replay_nodes(
    value: object,
    *,
    maximum_nodes: int = EXPECTED_BUDGET["json_nodes"],
    maximum_depth: int = EXPECTED_BUDGET["json_nesting"],
) -> int:
    """Count canonical JSON nodes without calling the production implementation."""

    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > maximum_nodes or depth > maximum_depth:
            raise _IndependentReplayExhausted("independent replay JSON budget exceeded")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > EXPECTED_BUDGET["integer_maximum"]:
                raise _IndependentReplayInvalid("integer outside canonical range")
            continue
        if type(item) is str:
            if (
                len(item) > EXPECTED_BUDGET["string_codepoints"]
                or "\x00" in item
                or unicodedata.normalize("NFC", item) != item
            ):
                raise _IndependentReplayInvalid("string outside canonical form")
            continue
        if type(item) is list:
            stack.extend((nested, depth + 1) for nested in reversed(item))
            continue
        if type(item) is dict:
            for key, nested in reversed(tuple(item.items())):
                if type(key) is not str:
                    raise _IndependentReplayInvalid("object key is not exact text")
                stack.append((nested, depth + 1))
                stack.append((key, depth + 1))
            continue
        raise _IndependentReplayInvalid("unsupported JSON value")
    return nodes


def _independent_replay_mapping(
    raw: bytes,
    *,
    maximum_nodes: int = EXPECTED_BUDGET["json_nodes"],
) -> tuple[dict[str, object], int] | None:
    """Independently parse one canonical replay object and return its node cost."""

    try:
        value = json.loads(
            raw,
            object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(
                _IndependentReplayInvalid("floats forbidden")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                _IndependentReplayInvalid("non-finite numbers forbidden")
            ),
        )
        nodes = _independent_replay_nodes(value, maximum_nodes=maximum_nodes)
        if type(value) is not dict or _canonical(value) != raw:
            raise _IndependentReplayInvalid("not a canonical object")
    except _IndependentReplayExhausted:
        raise
    except (
        ExecutionDispositionValidationFailure,
        _IndependentReplayInvalid,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        return None
    return value, nodes


def _independent_normalization_replay_visits(
    value: dict[str, object],
    *,
    maximum_operations: int = EXPECTED_BUDGET["replay_operations"],
) -> int:
    """Recompute expanded semantic replay bytes without production helpers."""

    if (
        value.get("schema") != "mathhead.canonical-normalization-result.v1"
        or value.get("status") != "normalized"
    ):
        return 0
    proof = value.get("proof_obligation_result")
    domain = proof.get("domain_assumption_result") if type(proof) is dict else None
    readings = domain.get("readings_result") if type(domain) is dict else None
    candidates = readings.get("candidates") if type(readings) is dict else None
    if type(candidates) is not list:
        return 0

    visit_limit = maximum_operations // 256 + 1

    def saturated_sum(*amounts: int) -> int:
        total = 0
        for amount in amounts:
            if amount >= visit_limit - total:
                return visit_limit
            total += amount
        return total

    registry_names = (
        "domains",
        "variables",
        "expressions",
        "relations",
        "statements",
        "definitions",
        "assumptions",
        "goals",
    )
    inventories: list[dict[str, dict[str, object]]] = []
    every_identity: set[str] = set()
    for candidate in candidates:
        projection = candidate.get("projection") if type(candidate) is dict else None
        entities = projection.get("entities") if type(projection) is dict else None
        if type(entities) is not dict:
            continue
        records: dict[str, dict[str, object]] = {}
        structurally_usable = True
        for registry_name in registry_names:
            rows = entities.get(registry_name, [])
            if type(rows) is not list:
                structurally_usable = False
                break
            for row in rows:
                if type(row) is not dict:
                    structurally_usable = False
                    break
                identity = row.get("id")
                if type(identity) is not str or identity in records:
                    return visit_limit
                records[identity] = row
            if not structurally_usable:
                break
        if structurally_usable and records:
            inventories.append(records)
            every_identity.update(records)

    if not inventories:
        return 0

    occurrences = {identity: 0 for identity in every_identity}
    stack: list[object] = [proof]
    while stack:
        item = stack.pop()
        if type(item) is str:
            if item in occurrences:
                occurrences[item] += 1
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is dict:
            stack.extend(item.values())

    total = 0
    for records in inventories:
        identities = set(records)
        references: dict[str, tuple[str, ...]] = {}
        encoded_sizes: dict[str, int] = {}
        for identity, row in records.items():
            outgoing: list[str] = []
            pending = [item for name, item in row.items() if name != "id"]
            while pending:
                item = pending.pop()
                if type(item) is str:
                    if item in identities:
                        outgoing.append(item)
                elif type(item) is list:
                    pending.extend(item)
                elif type(item) is dict:
                    pending.extend(item.values())
            references[identity] = tuple(outgoing)
            encoded_sizes[identity] = len(_canonical(row))

        memo: dict[str, int] = {}
        active: set[str] = set()

        def expanded_size(identity: str) -> int:
            known = memo.get(identity)
            if known is not None:
                return known
            if identity in active or len(active) >= EXPECTED_BUDGET["json_nesting"]:
                return visit_limit
            active.add(identity)
            result = saturated_sum(
                encoded_sizes[identity],
                *(expanded_size(child) for child in references[identity]),
            )
            active.remove(identity)
            memo[identity] = result
            return result

        for identity in records:
            roots = max(1, occurrences.get(identity, 0))
            size = expanded_size(identity)
            if roots > visit_limit // size:
                return visit_limit
            total = saturated_sum(total, roots * size)
    return total


def _independent_replay_operation_charge(
    manifest_bytes: bytes,
    objects: tuple[bytes, ...],
    *,
    maximum_operations: int = EXPECTED_BUDGET["replay_operations"],
    maximum_nodes: int = EXPECTED_BUDGET["json_nodes"],
) -> tuple[int, int, int, int, int, dict[str, object] | None]:
    """Recompute the accepted replay charge from bytes, independently of production."""

    operations = 0

    def charge(amount: int) -> None:
        nonlocal operations
        if amount < 0 or amount > maximum_operations - operations:
            raise _IndependentReplayExhausted("independent replay operation budget exceeded")
        operations += amount

    byte_count = len(manifest_bytes) + sum(len(raw) for raw in objects)
    charge(byte_count * 256)
    parsed_manifest = _independent_replay_mapping(manifest_bytes, maximum_nodes=maximum_nodes)
    manifest = None if parsed_manifest is None else parsed_manifest[0]
    nodes = 0 if parsed_manifest is None else parsed_manifest[1]
    normalization_visits = 0
    normalization_visit_limit = maximum_operations // 256 + 1
    for raw in objects:
        remaining_nodes = maximum_nodes - nodes
        if remaining_nodes < 0:
            raise _IndependentReplayExhausted("aggregate replay JSON budget exceeded")
        parsed = _independent_replay_mapping(raw, maximum_nodes=remaining_nodes)
        if parsed is None:
            continue
        nodes += parsed[1]
        if nodes > maximum_nodes:
            raise _IndependentReplayExhausted("aggregate replay JSON budget exceeded")
        normalization_visits = min(
            normalization_visit_limit,
            normalization_visits
            + _independent_normalization_replay_visits(
                parsed[0], maximum_operations=maximum_operations
            ),
        )
    charge(nodes * nodes * 8)
    charge(normalization_visits * 256)
    relation_items = len(objects)
    if manifest is not None:
        records = manifest.get("objects")
        events = manifest.get("events")
        relation_items += len(records) if type(records) is list else 0
        relation_items += len(events) if type(events) is list else 0
    charge(relation_items * 64)
    return operations, byte_count, nodes, relation_items, normalization_visits, manifest


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionDispositionValidationFailure(f"invalid JSON document: {path.name}") from exc
    if type(value) is not dict:
        raise ExecutionDispositionValidationFailure(f"JSON root is not an object: {path.name}")
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
            raise ExecutionDispositionValidationFailure(f"{keyword} is not an object at {path}")
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
            raise ExecutionDispositionValidationFailure(f"invalid pattern at {path}") from exc


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
        "checked_proof",
        "checked_refutation",
        "ambiguity",
        "user_cancellation",
        "parent_cancellation",
        "supervisor_cancellation",
        "cancellation_origin_unproven",
        "budget_exhaustion",
        "unsupported_input",
        "unsupported_execution_environment",
        "producer_refusal",
        "verifier_refusal",
        "truncation",
        "inconclusive_execution",
        "checker_disagreement",
        "invalid_evidence",
        "producer_failure",
        "verifier_failure",
        "invalid_request",
        "internal_error",
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

    add(
        ("checked_proof", "checked_refutation"),
        "completed",
        "30_checked_terminal",
        30,
        ("completed",),
    )
    add(("ambiguity",), "inconclusive", "20_early_route_planner", 20, ("routing",))
    add(("ambiguity",), "inconclusive", "80_semantic_terminal", 80, ("producer",))
    add(
        (
            "user_cancellation",
            "parent_cancellation",
            "supervisor_cancellation",
            "cancellation_origin_unproven",
        ),
        "cancelled",
        "40_observed_cancellation",
        40,
        ("producer", "checker"),
    )
    add(("budget_exhaustion",), "exhausted", "20_early_route_planner", 20, ("routing", "planning"))
    add(
        ("budget_exhaustion",),
        "exhausted",
        "50_ledger_exhaustion",
        50,
        ("producer", "checker"),
        1,
        10,
    )
    add(("unsupported_input",), "refused", "20_early_route_planner", 20, ("routing",))
    add(
        ("unsupported_execution_environment",),
        "refused",
        "20_early_route_planner",
        20,
        ("routing",),
    )
    add(
        ("unsupported_execution_environment",),
        "refused",
        "60_environment_refusal",
        60,
        ("producer", "checker"),
    )
    add(("producer_refusal",), "refused", "70_component_refusal", 70, ("producer",))
    add(("verifier_refusal",), "refused", "70_component_refusal", 70, ("checker",))
    add(("truncation",), "inconclusive", "80_semantic_terminal", 80, ("producer", "checker"))
    add(("inconclusive_execution",), "inconclusive", "80_semantic_terminal", 80, ("checker",))
    add(("checker_disagreement",), "inconclusive", "80_semantic_terminal", 80, ("checker",))
    add(("invalid_evidence",), "inconclusive", "80_semantic_terminal", 80, ("producer", "checker"))
    add(("producer_failure",), "failed", "90_phase_failure", 90, ("producer",))
    add(("verifier_failure",), "failed", "90_phase_failure", 90, ("checker",))
    add(
        ("invalid_request",),
        "invalid",
        "10_prelaunch_invalid",
        10,
        ("request", "routing", "planning", "coordinator"),
    )
    add(
        ("internal_error",),
        "failed",
        "00_internal_invariant",
        0,
        ("cleanup", "audit", "replay", "coordinator"),
    )

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
        disposition = _values(properties.get("disposition"), label="classification disposition")
        row = _values(properties.get("precedence_row"), label="precedence row")
        rank = _values(properties.get("precedence_rank"), label="precedence rank")
        phases = _values(properties.get("phase"), label="classification phase")
        resources = properties.get("resource_dimensions", {})
        minimum = resources.get("minItems", 0)
        maximum = resources.get("maxItems", 10)
        if len(disposition) != 1 or len(row) != 1 or len(rank) != 1:
            raise ExecutionDispositionValidationFailure("classification row is not singly paired")
        for cause in causes:
            observed.add(
                (
                    cause,
                    disposition[0],
                    row[0],
                    rank[0],
                    phases,
                    minimum,
                    maximum,
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
                    or properties.get("observer_cancellation_id", {}).get("type") != "null"
                    or properties.get("observer_basis", {}).get("const")
                    != "replayed_worker_status_plus_accepted_contract"
                ):
                    raise ExecutionDispositionValidationFailure(
                        f"cancellation observer relation drift: {cause}"
                    )
    if observed != expected:
        raise ExecutionDispositionValidationFailure("classification matrix drift")

    cancellation_guard = schema["allOf"][1]
    guarded = tuple(cancellation_guard["if"]["properties"]["cause"]["enum"])
    if guarded != tuple(cancellation_origins):
        raise ExecutionDispositionValidationFailure("cancellation guard drift")
    null_fields = cancellation_guard["else"]["properties"]
    for name in (
        "origin_source",
        "observer_source",
        "observer_cancellation_id",
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
        armed["cancellation_intent"].get("$ref") != "cancellation-intent-v1.schema.json"
        or armed.get("base_parent_budget_sha256", {}).get("$ref") != "#/$defs/sha256"
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
    states = {branch["properties"]["execution_state"]["const"]: branch for branch in state_branches}
    if set(states) != {
        "not_started",
        "attempted_no_bundle",
        "bundle_replay_failed",
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
        raise ExecutionDispositionValidationFailure("not-started evidence profile drift")
    for state in ("attempted_no_bundle", "bundle_replay_failed", "replayed_complete"):
        properties = states[state]["properties"]
        required_sha_fields = (
            "disposition_request_sha256",
            "invocation_sha256",
            "base_parent_budget_sha256",
            "anchored_parent_budget_sha256",
            "planning_result_sha256",
            "portfolio_request_sha256",
        )
        if any(
            properties.get(name, {}).get("$ref") != "#/$defs/sha256" for name in required_sha_fields
        ):
            raise ExecutionDispositionValidationFailure(
                f"started state lacks a validated identity: {state}"
            )
        expected_status = {
            "route_status": "routed",
            "route_reason_code": "ROUTED",
            "planning_status": "planned",
            "planning_reason_code": "PLANNED",
        }
        if any(
            properties.get(name, {}).get("const") != value
            for name, value in expected_status.items()
        ):
            raise ExecutionDispositionValidationFailure(
                f"started state lacks routed/planned relation: {state}"
            )
    if (
        states["attempted_no_bundle"]["properties"]["portfolio_relation"].get("const")
        != "not_available"
        or states["bundle_replay_failed"]["properties"]["portfolio_relation"].get("const")
        != "not_available"
        or tuple(states["replayed_complete"]["properties"]["portfolio_relation"].get("enum", ()))
        != ("exact", "invalid")
    ):
        raise ExecutionDispositionValidationFailure("execution-state portfolio relation drift")
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
            or profile.get("allOf") != [{"$ref": "#/$defs/valid_request_result"}]
            or profile.get("properties") != properties
        ):
            raise ExecutionDispositionValidationFailure(
                f"prelaunch milestone profile drift: {name}"
            )
    early_profile = definitions["reached_early_result"]
    if early_profile.get("allOf") != [
        {"$ref": "#/$defs/valid_request_result"}
    ] or early_profile.get("properties") != {
        **common_null_budget,
        "planning_result_sha256": sha,
        "cancellation_armed": {"const": False},
        "cancellation_intent_sha256": null,
    }:
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
        (
            ("ambiguous",),
            ("NON_UNIQUE_SELECTION", "READING_AMBIGUOUS"),
            ("ambiguous",),
            ("ROUTE_AMBIGUOUS",),
        ),
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
            "BUDGET_INSUFFICIENT",
            "WALL_TIME_EXHAUSTED",
            "CPU_TIME_EXHAUSTED",
            "MEMORY_EXHAUSTED",
            "OUTPUT_EXHAUSTED",
            "DIAGNOSTIC_EXHAUSTED",
            "EVIDENCE_EXHAUSTED",
            "CHECKER_EXHAUSTED",
        },
        "cancelled": {"CANCELLED", "EVIDENCE_CANCELLED", "CHECKER_CANCELLED"},
        "failed": {
            "REQUEST_INVALID",
            "PLAN_INVALID",
            "STRATEGY_MISMATCH",
            "BUDGET_INVALID",
            "EXECUTABLE_INVALID",
            "LAUNCH_FAILED",
            "EXIT_FAILED",
            "PROTOCOL_FAILED",
            "TREE_CLEANUP_FAILED",
            "SUPERVISOR_FAILED",
            "EVIDENCE_ERROR",
        },
        "ambiguous": {"EVIDENCE_INCOMPLETE"},
        "truncated": {"EVIDENCE_TRUNCATED", "CHECKER_TRUNCATED"},
        "inconclusive": {"ISOLATION_UNSUPPORTED", "CHECKER_INCONCLUSIVE"},
        "disagreement": {"CHECKER_REJECTED", "CHECKER_DISAGREED"},
        "verifier_failed": {
            "REQUEST_INVALID",
            "PLAN_INVALID",
            "STRATEGY_MISMATCH",
            "BUDGET_INVALID",
            "EXECUTABLE_INVALID",
            "LAUNCH_FAILED",
            "EXIT_FAILED",
            "PROTOCOL_FAILED",
            "TREE_CLEANUP_FAILED",
            "SUPERVISOR_FAILED",
            "CERTIFICATE_INVALID",
        },
        "invalid_evidence": {
            "EVIDENCE_INVALID",
            "EVIDENCE_PROTOCOL_LIMIT",
            "CERTIFICATE_INVALID",
        },
        "invalid": {"PORTFOLIO_INPUT_INVALID", "PORTFOLIO_EXECUTION_INVALID"},
    }
    observed_portfolio_reasons: dict[str, set[str]] = {}
    for branch in definitions["portfolio_pair"].get("oneOf", ()):
        statuses = _flatten_values(branch, "portfolio_status")
        reasons = _flatten_values(branch, "portfolio_reason_code")
        if len(statuses) != 1 or not reasons:
            raise ExecutionDispositionValidationFailure("portfolio pair row is not exact")
        status = str(next(iter(statuses)))
        if status in observed_portfolio_reasons:
            raise ExecutionDispositionValidationFailure(f"duplicate portfolio status row: {status}")
        observed_portfolio_reasons[status] = {str(reason) for reason in reasons}
    if (
        observed_portfolio_reasons != expected_portfolio_reasons
        or sum(len(reasons) for reasons in observed_portfolio_reasons.values()) != 49
    ):
        raise ExecutionDispositionValidationFailure("accepted 49-pair portfolio matrix drift")

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
        raise ExecutionDispositionValidationFailure("portfolio outcome discriminator gate drift")
    outcome_variants = {
        (
            tuple(sorted(str(value) for value in _flatten_values(branch, "portfolio_status"))),
            tuple(sorted(str(value) for value in _flatten_values(branch, "portfolio_reason_code"))),
            tuple(
                sorted(str(value) for value in _flatten_values(branch, "portfolio_outcome_kind"))
            ),
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
        raise ExecutionDispositionValidationFailure("portfolio outcome discriminator matrix drift")
    outcome_default = outcome_gate[3]
    if (
        outcome_default.get("properties", {}).get("portfolio_outcome_kind", {}).get("type")
        != "null"
        or len(outcome_default.get("allOf", ())) != 3
    ):
        raise ExecutionDispositionValidationFailure(
            "portfolio outcome discriminator default is open"
        )

    selection = schema["allOf"][3]
    checked = set(selection["if"]["properties"]["classification"]["properties"]["cause"]["enum"])
    if checked != {"checked_proof", "checked_refutation"}:
        raise ExecutionDispositionValidationFailure("checked selection guard drift")
    selected_names = (
        "selected_strategy_sha256",
        "selected_evidence_sha256",
        "selected_certificate_sha256",
        "selected_checker_decision_sha256",
    )
    then_properties = selection["then"]["properties"]
    else_properties = selection["else"]["properties"]
    if any(
        then_properties.get(name, {}).get("$ref") != "#/$defs/sha256" for name in selected_names
    ):
        raise ExecutionDispositionValidationFailure("checked identity retention drift")
    if any(else_properties.get(name, {}).get("type") != "null" for name in selected_names):
        raise ExecutionDispositionValidationFailure("non-checked identity retention drift")
    if schema["properties"]["authority_ceiling"].get("const") != "none":
        raise ExecutionDispositionValidationFailure("result authority ceiling drift")

    cause_branches = schema["allOf"][4]["oneOf"]
    expected_counts = {
        "checked_proof": 1,
        "checked_refutation": 1,
        "user_cancellation": 1,
        "parent_cancellation": 1,
        "supervisor_cancellation": 1,
        "ambiguity": 2,
        "budget_exhaustion": 3,
        "unsupported_input": 1,
        "unsupported_execution_environment": 2,
        "producer_refusal": 1,
        "verifier_refusal": 1,
        "truncation": 1,
        "inconclusive_execution": 1,
        "checker_disagreement": 1,
        "invalid_evidence": 1,
        "producer_failure": 1,
        "verifier_failure": 1,
        "invalid_request": 1,
        "internal_error": 1,
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
        (
            _branch_reference(branch),
            tuple(sorted(_flatten_values(branch, "precedence_row"))),
            tuple(sorted(_flatten_values(branch, "phase"))),
        )
        for branch in indexed["ambiguity"]
    }
    if ambiguity_variants != {
        ("early_normal_result", ("20_early_route_planner",), ("routing",)),
        ("audited_normal_result", ("80_semantic_terminal",), ("producer",)),
    }:
        raise ExecutionDispositionValidationFailure("ambiguity variant relation drift")
    budget_variants = {
        (
            _branch_reference(branch),
            tuple(sorted(_flatten_values(branch, "precedence_row"))),
            tuple(sorted(_flatten_values(branch, "phase"))),
        )
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
            raise ExecutionDispositionValidationFailure("budget reason branch is not exact")
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
        raise ExecutionDispositionValidationFailure("budget reason-dimension matrix drift")
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
            "verifier_refusal",
            "inconclusive_execution",
        },
        "EXECUTABLE_INVALID": {
            "producer_refusal",
            "verifier_refusal",
            "internal_error",
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
            raise ExecutionDispositionValidationFailure(f"result reason ownership drift: {reason}")
    invalid_codes = _flatten_values(indexed["invalid_request"][0], "code")
    internal = indexed["internal_error"][0]
    internal_codes = _flatten_values(internal, "code")
    if invalid_codes != {
        "REQUEST_INVALID",
        "INTENT_EVENT_MISMATCH",
        "RESERVED_EXTENSION_COLLISION",
        "ROUTE_INPUT_INVALID",
        "PLANNING_INPUT_INVALID",
        "BINDING_INPUT_INVALID",
        "ARTIFACT_INPUT_INVALID",
        "EXECUTION_INPUT_INVALID",
    }:
        raise ExecutionDispositionValidationFailure("invalid-request diagnostic ownership drift")
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
        raise ExecutionDispositionValidationFailure("invalid-request reached-evidence matrix drift")
    if internal_codes != {
        "BUDGET_ANCHOR_INVALID",
        "PORTFOLIO_REQUEST_INVALID",
        "AUDITED_EXECUTION_INVALID",
        "AUDIT_REPLAY_INVALID",
        "AUDIT_REPLAY_EXHAUSTED",
        "AUDIT_RELATION_INVALID",
        "CLEANUP_INVARIANT",
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
        raise ExecutionDispositionValidationFailure("internal-error diagnostic ownership drift")
    internal_by_phase = {
        branch["properties"]["classification"]["properties"]["phase"]["const"]: branch
        for branch in internal["oneOf"]
    }
    if set(internal_by_phase) != {"cleanup", "audit", "replay", "coordinator"}:
        raise ExecutionDispositionValidationFailure("internal phase matrix drift")
    cleanup_state = internal_by_phase["cleanup"]["properties"]["execution_state"]
    audit_states = internal_by_phase["audit"]["properties"]["execution_state"]
    replay_states = internal_by_phase["replay"]["properties"]["execution_state"]
    if (
        cleanup_state.get("const") != "replayed_complete"
        or tuple(audit_states.get("enum", ())) != ("attempted_no_bundle", "replayed_complete")
        or replay_states.get("const") != "bundle_replay_failed"
    ):
        raise ExecutionDispositionValidationFailure("internal execution-state/phase relation drift")
    cleanup = internal_by_phase["cleanup"]
    if (
        _flatten_values(cleanup, "portfolio_relation") != {"exact"}
        or _flatten_values(cleanup, "portfolio_status") != {"failed", "verifier_failed"}
        or _flatten_values(cleanup, "portfolio_reason_code") != {"TREE_CLEANUP_FAILED"}
        or _flatten_values(cleanup, "code") != {"CLEANUP_INVARIANT"}
    ):
        raise ExecutionDispositionValidationFailure("cleanup invariant ownership drift")
    audit = internal_by_phase["audit"]
    audit_by_code = {
        str(next(iter(codes))): branch
        for branch in audit["oneOf"]
        if len(codes := _flatten_values(branch, "code")) == 1
    }
    if set(audit_by_code) != {"AUDITED_EXECUTION_INVALID", "AUDIT_RELATION_INVALID"}:
        raise ExecutionDispositionValidationFailure("audit diagnostic ownership drift")
    relation_branch = audit_by_code["AUDIT_RELATION_INVALID"]
    if (
        _definition_references(relation_branch) != {"portfolio_pair"}
        or _flatten_values(relation_branch, "execution_state") != {"replayed_complete"}
        or _flatten_values(relation_branch, "portfolio_relation") != {"invalid"}
    ):
        raise ExecutionDispositionValidationFailure("audit relation-invalid evidence profile drift")
    replay = internal_by_phase["replay"]
    replay_by_code = {
        str(next(iter(codes))): branch
        for branch in replay["oneOf"]
        if len(codes := _flatten_values(branch, "code")) == 1
    }
    if set(replay_by_code) != {"AUDIT_REPLAY_INVALID", "AUDIT_REPLAY_EXHAUSTED"}:
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
        raise ExecutionDispositionValidationFailure("coordinator diagnostic branch matrix drift")
    expected_prelaunch = {
        "BUDGET_ANCHOR_INVALID": "planned_unanchored_result",
        "PORTFOLIO_REQUEST_INVALID": "planned_anchored_result",
    }
    for code, reference in expected_prelaunch.items():
        branch = coordinator_by_code[code]
        if _definition_references(branch) != {reference} or _flatten_values(
            branch, "execution_state"
        ) != {"not_started"}:
            raise ExecutionDispositionValidationFailure(
                f"prelaunch coordinator milestone drift: {code}"
            )
    limit_branch = coordinator_by_code["COORDINATOR_LIMIT_EXHAUSTED"]
    if _definition_references(limit_branch) != {"empty_preflight_result"} or _flatten_values(
        limit_branch, "execution_state"
    ) != {"not_started"}:
        raise ExecutionDispositionValidationFailure("coordinator limit preflight profile drift")
    exact_coordinator_pairs = {
        "WORKER_REQUEST_INVARIANT": (
            {"failed", "verifier_failed"},
            {"REQUEST_INVALID"},
            {"exact"},
            set(),
        ),
        "WORKER_PLAN_INVARIANT": (
            {"failed", "verifier_failed"},
            {"PLAN_INVALID"},
            {"exact"},
            set(),
        ),
        "WORKER_STRATEGY_INVARIANT": (
            {"failed", "verifier_failed"},
            {"STRATEGY_MISMATCH"},
            {"exact"},
            set(),
        ),
        "WORKER_BUDGET_INVARIANT": (
            {"failed", "verifier_failed"},
            {"BUDGET_INVALID"},
            {"exact"},
            set(),
        ),
        "WORKER_EXECUTABLE_INVARIANT": (
            {"failed", "verifier_failed"},
            {"EXECUTABLE_INVALID"},
            {"exact"},
            {"executable_invalid"},
        ),
        "SUPERVISOR_INVARIANT": (
            {"failed", "verifier_failed"},
            {"SUPERVISOR_FAILED"},
            {"exact"},
            set(),
        ),
        "PORTFOLIO_INPUT_INVARIANT": ({"invalid"}, {"PORTFOLIO_INPUT_INVALID"}, {"exact"}, set()),
        "PORTFOLIO_EXECUTION_INVARIANT": (
            {"invalid"},
            {"PORTFOLIO_EXECUTION_INVALID"},
            {"exact"},
            set(),
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
            or value.get("$schema") != SCHEMA_DIALECT
            or value.get("type") != "object"
            or value.get("additionalProperties") is not False
            or set(value.get("required", ())) != set(value.get("properties", {}))
        ):
            raise ExecutionDispositionValidationFailure(f"closed schema binding drift: {name}")
        observed[name] = expected_sha256
        schemas[name] = value
    _schema_graph_check(schemas)
    _classification_schema_check(schemas["execution-disposition-classification-v1.schema.json"])
    _diagnostic_schema_check(schemas["execution-disposition-diagnostic-v1.schema.json"])
    _request_schema_check(schemas["execution-disposition-request-v1.schema.json"])
    _result_schema_check(schemas["execution-disposition-result-v1.schema.json"])
    return observed


def _contract_registration_check() -> dict[str, object]:
    accepted = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
    proposed = ROOT / "docs/contracts/proposed" / f"{CONTRACT_ID}.json"
    if not accepted.is_file() or not proposed.is_file():
        raise ExecutionDispositionValidationFailure(
            "accepted/proposed execution-disposition artifacts are incomplete"
        )
    proposal_raw = proposed.read_bytes()
    if proposal_raw != _canonical(json.loads(proposal_raw)):
        raise ExecutionDispositionValidationFailure("proposal is not canonical")
    if _sha(proposal_raw) != CONTRACT_SHA256:
        raise ExecutionDispositionValidationFailure(
            "compiled execution-disposition contract identity drift"
        )
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text(encoding="utf-8"))
    entries = [item for item in manifest.get("contracts", ()) if item.get("id") == CONTRACT_ID]
    if len(entries) != 1 or entries[0].get("sha256") != CONTRACT_SHA256:
        raise ExecutionDispositionValidationFailure("contract manifest binding drift")
    state = str(entries[0].get("state"))
    accepted_raw = accepted.read_bytes()
    if (
        state != "accepted"
        or accepted_raw != proposal_raw
        or accepted_raw != _canonical(json.loads(accepted_raw))
    ):
        raise ExecutionDispositionValidationFailure(
            "accepted artifact differs from its proposal or manifest state"
        )
    return {
        "accepted_equals_proposed": True,
        "id": CONTRACT_ID,
        "sha256": _sha(accepted_raw),
        "state": state,
    }


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
    extensions[RESERVED_EXTENSION] = {"disposition_request_sha256": disposition_request_sha256}
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
    collision["extensions"][RESERVED_EXTENSION] = {"disposition_request_sha256": request_sha256}
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
    artifact_bindings = [{"role": "problem", "sha256": digest_b, "byte_count": 7}]
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
    _validate_result_request_projection(request, full_result, request_input=request_input)
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
    transplanted_full_result["request_input_sha256"] = _sha(transplanted_request_input)
    transplanted_full_result["result_sha256"] = None
    transplanted_full_result["result_sha256"] = _sha(_canonical(transplanted_full_result))
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
        raise ExecutionDispositionValidationFailure("forged full result self-identity accepted")
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
        raise ExecutionDispositionValidationFailure(f"forged retained request accepted: {label}")

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
    forged_intent_policy_request_sha256 = _sha(_canonical(forged_intent_policy_request))
    forged_intent_policy_request["request_sha256"] = forged_intent_policy_request_sha256
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
    unarmed_projection = {name: unarmed_request[name] for name in INVOCATION_FIELDS}
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
        if type(result_sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", result_sha256) is None:
            raise ExecutionDispositionValidationFailure("full result self-identity is malformed")
        result_preimage = dict(result)
        result_preimage["result_sha256"] = None
        if _sha(_canonical(result_preimage)) != result_sha256:
            raise ExecutionDispositionValidationFailure("full result self-identity is invalid")
    elif request_input is not None:
        raise ExecutionDispositionValidationFailure("raw request bytes require a full result")
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
                raise ExecutionDispositionValidationFailure(f"retained request has invalid {label}")
            return value

        def require_id(value: object, *, label: str) -> str:
            if type(value) is not str or re.fullmatch(r"[a-z][a-z0-9_.-]{0,254}", value) is None:
                raise ExecutionDispositionValidationFailure(f"retained request has invalid {label}")
            return value

        request_sha256 = require_sha256(request["request_sha256"], label="request self-identity")
        invocation_sha256 = require_sha256(
            request["invocation_sha256"], label="invocation identity"
        )
        contract_sha256 = require_sha256(request["contract_sha256"], label="contract identity")
        if contract_sha256 != CONTRACT_SHA256:
            raise ExecutionDispositionValidationFailure(
                "retained request contract identity is not accepted"
            )
        require_id(request["invocation_id"], label="invocation ID")
        for name in (
            "planning_request_sha256",
            "route_result_sha256",
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
                type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
                for value in descriptor_sha256s
            )
            or descriptor_sha256s != sorted(set(descriptor_sha256s))
            or type(binding_sha256s) is not list
            or len(binding_sha256s) > 100_000
            or any(
                type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
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
                "invocation_sha256",
                "base_parent_budget_sha256",
                "policy_contract_sha256",
                "intent_sha256",
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

        invocation_projection = {name: request[name] for name in INVOCATION_FIELDS}
        invocation_projection["schema"] = "mathhead.execution-disposition-invocation.v1"
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
            raise ExecutionDispositionValidationFailure("retained request self-identity is invalid")
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
            and (type(observed[3]) is str if armed else observed[3] is None)
        )
    if not exact_projection_types or observed != expected:
        raise ExecutionDispositionValidationFailure(
            "result request/armed/intent projection differs"
        )


def _schema_bindings() -> dict[str, str]:
    result: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        schema = _load_json(ROOT / "docs/contracts/schemas" / name)
        identity = schema.get("properties", {}).get("schema", {}).get("const")
        if type(identity) is not str or identity in result:
            _fail(f"schema semantic identity is absent or duplicated: {name}")
        result[identity] = digest
    return result


def _production_binding_check(production: Any) -> dict[str, object]:
    from mathhead import deterministic_planner, proof_search_portfolio, run_audit

    expected_bindings = _schema_bindings()
    production_budget = {
        "additional_fresh_replays": getattr(
            production, "MAX_ADDITIONAL_FRESH_REPLAYS", None
        ),
        "aggregate_artifact_bytes": getattr(
            production, "MAX_AGGREGATE_ARTIFACT_BYTES", None
        ),
        "aggregate_audit_bytes": getattr(
            production, "MAX_AGGREGATE_AUDIT_BYTES", None
        ),
        "aggregate_descriptor_bytes": getattr(
            production, "MAX_AGGREGATE_DESCRIPTOR_BYTES", None
        ),
        "aggregate_input_bytes": getattr(production, "MAX_AGGREGATE_INPUT_BYTES", None),
        "artifact_bytes": getattr(production, "MAX_ARTIFACT_BYTES", None),
        "artifacts": getattr(production, "MAX_ARTIFACTS", None),
        "attempts": getattr(production, "MAX_ATTEMPTS", None),
        "audit_events": getattr(production, "MAX_AUDIT_EVENTS", None),
        "audit_objects": getattr(production, "MAX_AUDIT_OBJECTS", None),
        "audited_calls": getattr(production, "MAX_AUDITED_CALLS", None),
        "bindings": getattr(production, "MAX_BINDINGS", None),
        "cancellation_intents": getattr(
            production, "MAX_CANCELLATION_INTENTS", None
        ),
        "descriptors": getattr(production, "MAX_DESCRIPTORS", None),
        "diagnostics": getattr(production, "MAX_DIAGNOSTICS", None),
        "input_bytes": getattr(production, "MAX_INPUT_BYTES", None),
        "integer_maximum": getattr(production, "INTEGER_MAXIMUM", None),
        "json_nesting": getattr(production, "MAX_JSON_DEPTH", None),
        "json_nodes": getattr(production, "MAX_JSON_NODES", None),
        "live_events": getattr(production, "MAX_LIVE_EVENTS", None),
        "replay_operations": getattr(production, "MAX_REPLAY_OPERATIONS", None),
        "strategies": getattr(production, "MAX_STRATEGIES", None),
        "string_codepoints": getattr(production, "MAX_STRING", None),
    }
    contract = _load_json(ROOT / "docs/contracts" / f"{CONTRACT_ID}.json")
    target = getattr(production, "execute_with_disposition", None)
    if (
        getattr(production, "CONTRACT_ID", None) != CONTRACT_ID
        or getattr(production, "CONTRACT_SHA256", None) != CONTRACT_SHA256
        or dict(getattr(production, "SCHEMA_SHA256S", {})) != expected_bindings
        or getattr(production, "RESERVED_EXTENSION", None) != RESERVED_EXTENSION
        or contract.get("budget") != EXPECTED_BUDGET
        or production_budget != EXPECTED_BUDGET
        or getattr(production, "MAX_EXECUTABLE_PATHS", None)
        != EXPECTED_BUDGET["bindings"] * 2
        or getattr(production, "REPLAY_NORMALIZATION_VISIT_OPERATIONS", None) != 256
        or production.MAX_AUDIT_OBJECTS != run_audit.MAX_OBJECTS
        or production.MAX_AUDIT_EVENTS != run_audit.MAX_EVENTS
        or production.MAX_AUDIT_BYTES != run_audit.MAX_OBJECT_BYTES
        or production.MAX_AGGREGATE_AUDIT_BYTES != run_audit.MAX_AGGREGATE_BYTES
        or production.MAX_ATTEMPTS != proof_search_portfolio.MAX_ITEMS
        or production.MAX_STRATEGIES != deterministic_planner.MAX_STRATEGIES
        or contract.get("target") != "mathhead.execution_disposition:execute_with_disposition"
        or contract.get("signature")
        != (
            "execute_with_disposition(disposition_request: bytes, planning_request: "
            "bytes, route_result: bytes, planning_result: bytes, "
            "base_parent_budget: bytes | None, descriptors: tuple[bytes, ...], "
            "bindings: tuple[bytes, ...], artifacts: tuple[tuple[str, bytes], ...], "
            "executable_paths: tuple[tuple[str, str], ...], workspace_root: str | "
            "None, cancel_event: Event | None = None) -> "
            "ExecutionDispositionBundle"
        )
        or not callable(target)
        or getattr(target, "__module__", None) != "mathhead.execution_disposition"
        or getattr(target, "__name__", None) != "execute_with_disposition"
        or Path(getattr(production, "__file__", "")).resolve() != SOURCE_PATH.resolve()
    ):
        _fail("accepted production contract, schema, module, or target binding drift")
    required_public = {
        "CancellationIntent",
        "ExecutionDispositionRequest",
        "ExecutionDispositionClassification",
        "ExecutionDispositionDiagnostic",
        "ExecutionDispositionResult",
        "ExecutionDispositionBundle",
        "ExecutionDispositionValidationError",
        "parse_cancellation_intent",
        "validate_cancellation_intent",
        "cancellation_intent_bytes",
        "parse_execution_disposition_request",
        "validate_execution_disposition_request",
        "execution_disposition_request_bytes",
        "parse_execution_disposition_classification",
        "validate_execution_disposition_classification",
        "execution_disposition_classification_bytes",
        "parse_execution_disposition_diagnostic",
        "validate_execution_disposition_diagnostic",
        "execution_disposition_diagnostic_bytes",
        "parse_execution_disposition_result",
        "validate_execution_disposition_result",
        "execution_disposition_result_bytes",
        "validate_execution_disposition_bundle",
        "derive_anchored_parent_budget",
        "execute_with_disposition",
    }
    exported = set(getattr(production, "__all__", ()))
    if not required_public <= exported:
        _fail("production public execution-disposition surface is incomplete")
    return {
        "budget_bindings": production_budget,
        "budget_key_count": len(production_budget),
        "contract_bound": True,
        "module": "mathhead.execution_disposition",
        "replay_normalization_visit_operations": 256,
        "schema_bindings": expected_bindings,
        "target": "mathhead.execution_disposition:execute_with_disposition",
    }


def _annotation_text(node: ast.expr | None) -> str:
    if node is None:
        return ""
    return "".join(ast.unparse(node).split())


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _source_checks() -> dict[str, object]:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE_PATH))
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    target = functions.get("execute_with_disposition")
    if not isinstance(target, ast.FunctionDef):
        _fail("production execute_with_disposition function is absent")
    expected_arguments = (
        "disposition_request",
        "planning_request",
        "route_result",
        "planning_result",
        "base_parent_budget",
        "descriptors",
        "bindings",
        "artifacts",
        "executable_paths",
        "workspace_root",
        "cancel_event",
    )
    arguments = tuple(item.arg for item in target.args.args)
    expected_annotations = {
        "disposition_request": "bytes",
        "planning_request": "bytes",
        "route_result": "bytes",
        "planning_result": "bytes",
        "base_parent_budget": "bytes|None",
        "descriptors": "tuple[bytes,...]",
        "bindings": "tuple[bytes,...]",
        "artifacts": "tuple[tuple[str,bytes],...]",
        "executable_paths": "tuple[tuple[str,str],...]",
        "workspace_root": "str|None",
        "cancel_event": "Event|None",
    }
    observed_annotations = {
        item.arg: _annotation_text(item.annotation) for item in target.args.args
    }
    if (
        arguments != expected_arguments
        or observed_annotations != expected_annotations
        or target.args.posonlyargs
        or target.args.kwonlyargs
        or target.args.vararg is not None
        or target.args.kwarg is not None
        or len(target.args.defaults) != 1
        or not isinstance(target.args.defaults[0], ast.Constant)
        or target.args.defaults[0].value is not None
        or _annotation_text(target.returns) != "ExecutionDispositionBundle"
    ):
        _fail("production execute_with_disposition signature drift")

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    forbidden_imports = {
        "asyncio",
        "importlib",
        "multiprocessing",
        "os",
        "pathlib",
        "random",
        "secrets",
        "signal",
        "socket",
        "subprocess",
        "tempfile",
        "time",
    }
    if imports & forbidden_imports:
        _fail(
            f"production gained a forbidden effect import: {sorted(imports & forbidden_imports)!r}"
        )

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    call_names = [_call_name(node) for node in calls]
    target_calls = [node for node in ast.walk(target) if isinstance(node, ast.Call)]
    target_call_names = [_call_name(node) for node in target_calls]
    exact_calls = (
        "route_capabilities",
        "plan_strategies",
        "make_proof_search_portfolio_request",
        "execute_audited_run",
        "replay_run_audit",
    )
    counts = {name: call_names.count(name) for name in exact_calls}
    target_counts = {name: target_call_names.count(name) for name in exact_calls}
    if any(count != 1 for count in counts.values()) or target_counts != counts:
        _fail(f"production exact-call boundary drift: {counts!r}")
    line_by_call = {
        name: next(node.lineno for node in calls if _call_name(node) == name)
        for name in exact_calls
    }
    if tuple(line_by_call[name] for name in exact_calls) != tuple(sorted(line_by_call.values())):
        _fail("production route/plan/derive/execute/replay call order drift")

    collection_calls = [
        node for node in target_calls if _call_name(node) == "_validate_input_collections"
    ]
    request_validation_calls = [
        node for node in target_calls if _call_name(node) == "_request_from_mapping"
    ]
    if len(collection_calls) != 1 or len(request_validation_calls) != 1:
        _fail("production input preflight or request validation boundary drift")
    collection_call = collection_calls[0]
    collection_arguments = tuple(ast.unparse(item) for item in collection_call.args)
    if (
        collection_call.keywords
        or collection_call.lineno >= request_validation_calls[0].lineno
        or collection_arguments
        != (
            "(disposition_request, planning_request, route_result, planning_result, "
            "*((base_parent_budget,) if base_parent_budget is not None else ()))",
            "descriptors",
            "bindings",
            "artifacts",
        )
    ):
        _fail("production byte preflight no longer precedes retention or binds every input")

    execute_calls = [node for node in calls if _call_name(node) == "execute_audited_run"]
    execution_call = execute_calls[0]
    execution_arguments = tuple(
        item.id if isinstance(item, ast.Name) else "" for item in execution_call.args
    )
    if execution_call.keywords or execution_arguments != (
        "planning_request",
        "route_result",
        "portfolio_request",
        "planning_result",
        "anchored",
        "descriptors",
        "bindings",
        "artifact_bytes",
        "executable_paths",
        "workspace_root",
        "cancel_event",
    ):
        _fail("sole audited call no longer forwards the exact governed inputs")

    replay_call = next(node for node in calls if _call_name(node) == "replay_run_audit")
    replay_arguments = tuple(ast.unparse(item) for item in replay_call.args)
    if replay_call.keywords or replay_arguments != ("audit.manifest", "audit.objects"):
        _fail("fresh replay no longer consumes the exact returned audit bundle")

    shallow_audit = functions.get("_shallow_audit_bundle")
    replay_preflight = functions.get("_replay_operation_preflight")
    normalization_preflight = functions.get("_normalization_replay_expansion_visits")
    if not isinstance(shallow_audit, ast.FunctionDef) or not isinstance(
        replay_preflight, ast.FunctionDef
    ) or not isinstance(normalization_preflight, ast.FunctionDef):
        _fail("audit output or replay-operation preflight is absent")
    preflight_calls = [
        node
        for node in ast.walk(shallow_audit)
        if isinstance(node, ast.Call) and _call_name(node) == "_replay_operation_preflight"
    ]
    if (
        len(preflight_calls) != 1
        or tuple(ast.unparse(item) for item in preflight_calls[0].args)
        != ("manifest", "value.manifest", "value.objects")
        or preflight_calls[0].keywords
        or not any(
            isinstance(node, ast.Name) and node.id == "MAX_REPLAY_OPERATIONS"
            for node in ast.walk(replay_preflight)
        )
    ):
        _fail("fresh replay operation budget is not bound before replay")
    replay_charge_calls = sorted(
        (
            node
            for node in ast.walk(replay_preflight)
            if isinstance(node, ast.Call) and _call_name(node) == "charge"
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    if tuple(ast.unparse(node.args[0]) for node in replay_charge_calls if len(node.args) == 1) != (
        "byte_count * 256",
        "nodes * nodes * 8",
        "normalization_visits * REPLAY_NORMALIZATION_VISIT_OPERATIONS",
        "relation_items * 64",
    ) or any(len(node.args) != 1 or node.keywords for node in replay_charge_calls):
        _fail("fresh replay byte, quadratic-node, or relation charge drift")
    replay_tests = {
        ast.unparse(node.test) for node in ast.walk(replay_preflight) if isinstance(node, ast.If)
    }
    if (
        "amount < 0 or amount > MAX_REPLAY_OPERATIONS - operations" not in replay_tests
        or "nodes > MAX_JSON_NODES" not in replay_tests
    ):
        _fail("fresh replay saturating operation or aggregate node ceiling drift")
    normalization_calls = [
        node
        for node in ast.walk(replay_preflight)
        if isinstance(node, ast.Call)
        and _call_name(node) == "_normalization_replay_expansion_visits"
    ]
    if (
        len(normalization_calls) != 1
        or tuple(ast.unparse(item) for item in normalization_calls[0].args) != ("parsed",)
        or normalization_calls[0].keywords
    ):
        _fail("canonical-normalization replay expansion is not charged from each parsed object")

    portfolio_call = next(
        node for node in calls if _call_name(node) == "make_proof_search_portfolio_request"
    )
    portfolio_keywords = {item.arg: ast.unparse(item.value) for item in portfolio_call.keywords}
    if portfolio_call.args or portfolio_keywords != {
        "planning_result": "planning_result",
        "parent_budget": "anchored",
        "descriptors": "descriptors",
        "bindings": "bindings",
        "artifacts": "artifacts",
    }:
        _fail("derived portfolio request no longer binds the exact anchored inputs")

    forbidden_calls = {
        "__import__",
        "eval",
        "exec",
        "getenv",
        "open",
        "popen",
        "run_portfolio",
        "supervise_worker",
        "system",
    }
    forbidden_event_methods = {"clear", "is_set", "set", "wait"}
    ambient_calls = {
        _call_name(node)
        for node in calls
        if _call_name(node) in forbidden_calls
        or (isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_event_methods)
        or "cache" in _call_name(node).lower()
        or "audit_store" in _call_name(node).lower()
    }
    if ambient_calls:
        _fail(
            f"production gained a forbidden ambient/direct effect call: {sorted(ambient_calls)!r}"
        )
    return {
        "exact_call_sites": counts,
        "forbidden_effect_calls": "absent",
        "forbidden_effect_imports": "absent",
        "input_preflight_before_request_retention": True,
        "replay_operation_preflight": True,
        "imports": sorted(imports),
        "path": "src/mathhead/execution_disposition.py",
        "sha256": _sha(SOURCE_PATH.read_bytes()),
        "signature": list(expected_arguments),
    }


def _require_result_identity(mapping: dict[str, object], label: str) -> None:
    if (
        set(mapping) != RESULT_FIELDS
        or mapping.get("schema") != "mathhead.execution-disposition-result.v1"
        or mapping.get("contract_id") != CONTRACT_ID
        or mapping.get("contract_sha256") != CONTRACT_SHA256
        or mapping.get("mathematical_authority") is not False
        or mapping.get("authority_ceiling") != "none"
        or mapping.get("result_sha256") != _self_hash(mapping, "result_sha256")
    ):
        _fail(f"runtime result identity or authority drift: {label}")


def _runtime_early_checks(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture

    expected = {
        "unsupported_environment": (
            "unsupported_execution_environment",
            "routing",
            "unsupported",
            "unsupported",
        ),
        "unsupported_input": (
            "unsupported_input",
            "routing",
            "unsupported",
            "unsupported",
        ),
        "planning_exhausted": (
            "budget_exhaustion",
            "planning",
            "routed",
            "exhausted",
        ),
    }
    observed: dict[str, str] = {}
    for kind, (cause, phase, route_status, planning_status) in expected.items():
        fixture = EarlyFixture(kind)
        with (
            mock.patch.object(production, "execute_audited_run") as audited,
            mock.patch.object(production, "replay_run_audit") as replay,
        ):
            bundle = production.execute_with_disposition(*fixture.inputs.call_arguments)
            production.validate_execution_disposition_bundle(bundle)
            raw = production.execution_disposition_result_bytes(bundle.result)
        if audited.call_count or replay.call_count:
            _fail(f"early governed outcome launched work or replayed: {kind}")
        mapping = json.loads(raw)
        _require_result_identity(mapping, kind)
        classification = mapping.get("classification")
        if type(classification) is not dict:
            _fail(f"early classification is not an object: {kind}")
        if (
            mapping.get("request_input_sha256") != _sha(fixture.inputs.request)
            or mapping.get("disposition_request_sha256")
            != fixture.inputs.request_value["request_sha256"]
            or mapping.get("execution_state") != "not_started"
            or mapping.get("portfolio_relation") != "not_available"
            or mapping.get("route_status") != route_status
            or mapping.get("planning_status") != planning_status
            or mapping.get("diagnostics") != []
            or classification.get("cause") != cause
            or classification.get("phase") != phase
            or classification.get("mathematical_authority") is not False
            or classification.get("classification_sha256")
            != _self_hash(classification, "classification_sha256")
            or bundle.audit is not None
            or bundle.replay is not None
        ):
            _fail(f"early governed outcome drift: {kind}")
        observed[kind] = cause
    return {
        "audited_calls": 0,
        "causes": observed,
        "fresh_replays": 0,
    }


def _runtime_unsupported_multi_group_check(production: Any) -> dict[str, object]:
    from mathhead.deterministic_planner import (
        plan_strategies,
        planning_result_bytes,
    )
    from tests.capability_registry.fixtures import plugin_bytes
    from tests.deterministic_planner.fixtures import PlannerFixture
    from tests.execution_disposition.fixtures import make_disposition_request

    fixture = PlannerFixture()
    availability_only = plugin_bytes(
        fixture.fragment,
        suffix="disposition_platform_unavailable",
        mutation=lambda value: value["compatibility"].update(platforms=["macos"]),
    )
    structural_only = plugin_bytes(
        fixture.fragment,
        suffix="disposition_domain_mismatch",
        mutation=lambda value: value["capabilities"][0]["fragment"].update(domains=["real"]),
    )
    descriptors = (availability_only, structural_only)
    planning_request, route_result, selected, artifact_bytes = fixture.planning_inputs(descriptors)
    plan = plan_strategies(planning_request, route_result, selected, artifact_bytes)
    planning_result = planning_result_bytes(plan)
    artifacts = tuple((f"input_{index}", raw) for index, raw in enumerate(artifact_bytes))
    request, request_value = make_disposition_request(
        planning_request=planning_request,
        route_result=route_result,
        planning_result=planning_result,
        base_parent_budget=None,
        descriptors=selected,
        bindings=(),
        artifacts=artifacts,
        invocation_id="invocation_unsupported_mixed_groups",
    )
    arguments = (
        request,
        planning_request,
        route_result,
        planning_result,
        None,
        selected,
        (),
        artifacts,
        (),
        None,
        None,
    )
    route_mapping = json.loads(route_result)
    reason_groups = {
        frozenset(item["reason_codes"]) for item in route_mapping.get("incompatibilities", [])
    }
    expected_groups = {
        frozenset({"PLATFORM_UNAVAILABLE"}),
        frozenset({"DOMAIN_MISMATCH"}),
    }
    with (
        mock.patch.object(production, "execute_audited_run") as audited,
        mock.patch.object(production, "replay_run_audit") as replay,
    ):
        bundle = production.execute_with_disposition(*arguments)
        raw = production.execution_disposition_result_bytes(bundle.result)
    mapping = json.loads(raw)
    _require_result_identity(mapping, "unsupported-mixed-groups")
    if (
        selected != descriptors
        or route_mapping.get("status") != "unsupported"
        or route_mapping.get("reason_code") != "NO_COMPATIBLE_CAPABILITY"
        or reason_groups != expected_groups
        or plan.status != "unsupported"
        or audited.call_count
        or replay.call_count
        or mapping.get("classification", {}).get("cause") != "unsupported_execution_environment"
        or mapping.get("classification", {}).get("phase") != "routing"
        or mapping.get("disposition_request_sha256") != request_value["request_sha256"]
    ):
        _fail("mixed structural/availability unsupported groups were misclassified")
    return {
        "availability_group": ["PLATFORM_UNAVAILABLE"],
        "audited_calls": 0,
        "classification": "unsupported_execution_environment",
        "structural_group": ["DOMAIN_MISMATCH"],
    }


def _runtime_invalid_request_check(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture

    fixture = EarlyFixture("unsupported_input")
    malformed = b'{"secret-never-retained":\n'
    arguments = list(fixture.inputs.call_arguments)
    arguments[0] = malformed
    with (
        mock.patch.object(production, "execute_audited_run") as audited,
        mock.patch.object(production, "replay_run_audit") as replay,
    ):
        bundle = production.execute_with_disposition(*arguments)
        raw = production.execution_disposition_result_bytes(bundle.result)
    mapping = json.loads(raw)
    _require_result_identity(mapping, "malformed-request")
    diagnostics = mapping.get("diagnostics")
    diagnostic = diagnostics[0] if type(diagnostics) is list and len(diagnostics) == 1 else None
    null_fields = (
        "disposition_request_sha256",
        "invocation_sha256",
        "cancellation_armed",
        "cancellation_intent_sha256",
        "base_parent_budget_sha256",
        "anchored_parent_budget_sha256",
        "planning_result_sha256",
        "portfolio_request_sha256",
        "audit_manifest_sha256",
        "logical_report_sha256",
        "replay_result_sha256",
        "portfolio_result_sha256",
        "execution_provenance_sha256",
        "route_status",
        "route_reason_code",
        "planning_status",
        "planning_reason_code",
        "portfolio_status",
        "portfolio_reason_code",
        "replay_status",
        "replay_reason_code",
    )
    if (
        audited.call_count
        or replay.call_count
        or bundle.request is not None
        or bundle.audit is not None
        or bundle.replay is not None
        or mapping.get("request_input_sha256") != _sha(malformed)
        or any(mapping.get(name) is not None for name in null_fields)
        or type(diagnostic) is not dict
        or diagnostic.get("code") != "REQUEST_INVALID"
        or diagnostic.get("phase") != "request"
        or diagnostic.get("diagnostic_id") != "execution_disposition.request.request_invalid"
        or diagnostic.get("diagnostic_sha256") != _self_hash(diagnostic, "diagnostic_sha256")
        or getattr(bundle.result, "_request_input", object()) is not None
        or malformed in raw
        or b"secret-never-retained" in raw
    ):
        _fail("malformed raw request retention or diagnostic profile drift")
    return {
        "diagnostic": "REQUEST_INVALID",
        "raw_bytes_retained": False,
        "request_input_sha256_bound": True,
    }


def _different_digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        return "f" * 64
    return ("0" if value[0] != "0" else "1") + value[1:]


def _runtime_projection_mutations(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture

    fixture = EarlyFixture("unsupported_input")
    bundle = production.execute_with_disposition(*fixture.inputs.call_arguments)
    request = production.parse_execution_disposition_request(fixture.inputs.request)
    raw = production.execution_disposition_result_bytes(bundle.result)
    original = json.loads(raw)
    mutations = (
        ("disposition_request_sha256", _different_digest(original["disposition_request_sha256"])),
        ("invocation_sha256", _different_digest(original["invocation_sha256"])),
        ("cancellation_armed", True),
        ("cancellation_intent_sha256", "f" * 64),
    )
    rejected: list[str] = []
    for field, replacement in mutations:
        forged = copy.deepcopy(original)
        forged[field] = replacement
        forged["result_sha256"] = _self_hash(forged, "result_sha256")
        try:
            production.parse_execution_disposition_result(
                _canonical(forged),
                request_input=fixture.inputs.request,
                request=request,
            )
        except production.ExecutionDispositionValidationError:
            rejected.append(field)
        else:
            _fail(f"repaired result request projection mutation was accepted: {field}")
    return {"rejected_fields": rejected, "repaired_outer_hashes": len(rejected)}


def _runtime_bundle_presence_check(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture

    fixture = EarlyFixture("unsupported_input")
    genuine = production.execute_with_disposition(*fixture.inputs.call_arguments)
    parsed = production.parse_execution_disposition_result(
        production.execution_disposition_result_bytes(genuine.result)
    )
    if parsed.disposition_request_sha256 is None:
        _fail("bundle presence attack lacks a validated result request identity")
    forged = object.__new__(production.ExecutionDispositionBundle)
    for name, value in (
        ("request", None),
        ("result", parsed),
        ("audit", None),
        ("replay", None),
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    try:
        production.validate_execution_disposition_bundle(forged)
    except production.ExecutionDispositionValidationError:
        rejected = True
    else:
        _fail("bundle erased a validated result request")
    return {
        "request_presence_equivalence": True,
        "standalone_result_transplant_rejected": rejected,
    }


def _input_bytes(arguments: Sequence[object], *, skip: int | None = None) -> list[bytes]:
    raw: list[bytes] = []
    for index in range(5):
        value = arguments[index]
        if index != skip and type(value) is bytes:
            raw.append(value)
    for value in arguments[5]:
        if type(value) is bytes:
            raw.append(value)
    for value in arguments[6]:
        if type(value) is bytes:
            raw.append(value)
    for pair in arguments[7]:
        if type(pair) is tuple and len(pair) == 2 and type(pair[1]) is bytes:
            raw.append(pair[1])
    return raw


def _require_limit_result(
    production: Any,
    arguments: Sequence[object],
    patches: dict[str, int],
    label: str,
) -> None:
    with ExitStack() as stack:
        for name, value in patches.items():
            stack.enter_context(mock.patch.object(production, name, value))
        audited = stack.enter_context(mock.patch.object(production, "execute_audited_run"))
        replayed = stack.enter_context(mock.patch.object(production, "replay_run_audit"))
        bundle = production.execute_with_disposition(*arguments)
        mapping = json.loads(production.execution_disposition_result_bytes(bundle.result))
    diagnostics = mapping.get("diagnostics")
    if (
        audited.call_count
        or replayed.call_count
        or bundle.request is not None
        or bundle.audit is not None
        or bundle.replay is not None
        or mapping.get("classification", {}).get("cause") != "internal_error"
        or mapping.get("classification", {}).get("phase") != "coordinator"
        or type(diagnostics) is not list
        or len(diagnostics) != 1
        or diagnostics[0].get("code") != "COORDINATOR_LIMIT_EXHAUSTED"
    ):
        _fail(f"input byte ceiling did not precede retention and effects: {label}")


def _runtime_input_limit_checks(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture, PlannedFixture

    early = EarlyFixture("unsupported_input")
    individual: list[str] = []
    names = (
        "disposition_request",
        "planning_request",
        "route_result",
        "planning_result",
        "base_parent_budget",
    )
    for index, name in enumerate(names):
        arguments = list(early.inputs.call_arguments)
        ceiling = max(len(raw) for raw in _input_bytes(arguments, skip=index))
        arguments[index] = b"x" * (ceiling + 1)
        _require_limit_result(
            production,
            arguments,
            {"MAX_INPUT_BYTES": ceiling},
            f"individual-{name}",
        )
        individual.append(name)

    empty_artifacts = replace(early.inputs, artifacts=())
    planned = PlannedFixture()
    base_arguments = list(early.inputs.call_arguments)
    aggregate_without_base = sum(len(raw) for raw in _input_bytes(base_arguments, skip=4))
    base_arguments[4] = b"x"
    aggregate_cases = (
        (
            "all-inputs-without-artifacts",
            empty_artifacts.call_arguments,
            {
                "MAX_AGGREGATE_INPUT_BYTES": sum(
                    len(raw) for raw in _input_bytes(empty_artifacts.call_arguments)
                )
                - 1
            },
        ),
        (
            "base-input-in-overall-aggregate",
            tuple(base_arguments),
            {"MAX_AGGREGATE_INPUT_BYTES": aggregate_without_base},
        ),
        (
            "descriptors",
            planned.inputs.call_arguments,
            {
                "MAX_AGGREGATE_DESCRIPTOR_BYTES": sum(
                    len(raw) for raw in planned.inputs.descriptors
                )
                - 1
            },
        ),
        (
            "artifacts",
            planned.inputs.call_arguments,
            {
                "MAX_AGGREGATE_ARTIFACT_BYTES": sum(len(raw) for _, raw in planned.inputs.artifacts)
                - 1
            },
        ),
    )
    aggregate: list[str] = []
    for label, arguments, patches in aggregate_cases:
        _require_limit_result(production, arguments, patches, label)
        aggregate.append(label)

    largest_semantic = max(
        len(raw) for raw in _input_bytes(planned.inputs.call_arguments)[:5]
    )
    descriptor_arguments = list(planned.inputs.call_arguments)
    descriptor_arguments[5] = (b"x" * (largest_semantic + 1),)
    binding_arguments = list(planned.inputs.call_arguments)
    binding_arguments[6] = (b"x" * (largest_semantic + 1),)
    individual_inventory_cases = (
        (
            "descriptor",
            descriptor_arguments,
            {"MAX_INPUT_BYTES": largest_semantic},
        ),
        (
            "binding",
            binding_arguments,
            {"MAX_INPUT_BYTES": largest_semantic},
        ),
        (
            "artifact",
            planned.inputs.call_arguments,
            {
                "MAX_ARTIFACT_BYTES": max(
                    len(raw) for _, raw in planned.inputs.artifacts
                )
                - 1
            },
        ),
    )
    for label, arguments, patches in individual_inventory_cases:
        _require_limit_result(production, arguments, patches, f"individual-{label}")
        individual.append(label)

    collection_cases = (
        ("descriptors", "MAX_DESCRIPTORS"),
        ("bindings", "MAX_BINDINGS"),
        ("artifacts", "MAX_ARTIFACTS"),
    )
    collections: list[str] = []
    for label, constant in collection_cases:
        _require_limit_result(
            production,
            planned.inputs.call_arguments,
            {constant: 0},
            f"{label}-count",
        )
        collections.append(label)

    string_ceiling = 4_096
    oversized = "x" * (string_ceiling + 1)
    workspace_arguments = list(planned.inputs.call_arguments)
    workspace_arguments[9] = oversized
    path_arguments = list(planned.inputs.call_arguments)
    executable_paths = list(path_arguments[8])
    executable_paths[0] = (executable_paths[0][0], oversized)
    path_arguments[8] = tuple(executable_paths)
    effect_strings: list[str] = []
    for label, arguments in (
        ("workspace_root", workspace_arguments),
        ("executable_path", path_arguments),
    ):
        _require_limit_result(
            production,
            arguments,
            {"MAX_STRING": string_ceiling},
            label,
        )
        effect_strings.append(label)

    path_count_arguments = list(early.inputs.call_arguments)
    path_count_arguments[8] = tuple(
        (_sha(str(index).encode("ascii")), f"path_{index}") for index in range(3)
    )
    _require_limit_result(
        production,
        path_count_arguments,
        {"MAX_EXECUTABLE_PATHS": 2},
        "executable-path-count",
    )
    scalar_boundaries: list[str] = []
    for label, constant in (
        ("json_nodes", "MAX_JSON_NODES"),
        ("json_depth", "MAX_JSON_DEPTH"),
        ("integer", "INTEGER_MAXIMUM"),
        ("json_string", "MAX_STRING"),
    ):
        with mock.patch.object(production, constant, 0):
            try:
                production.parse_execution_disposition_request(early.inputs.request)
            except production.ExecutionDispositionValidationError:
                pass
            else:
                _fail(f"scalar canonical ceiling was not enforced: {label}")
        scalar_boundaries.append(label)
    return {
        "aggregate_boundaries": aggregate,
        "checks_before_retention_and_effects": (
            len(individual) + len(aggregate) + len(effect_strings) + len(collections) + 1
        ),
        "count_and_json_boundaries": collections,
        "effect_only_collections": ["executable_paths"],
        "effect_only_strings": effect_strings,
        "individual_inputs": individual,
        "scalar_canonical_boundaries": scalar_boundaries,
    }


def _runtime_audit_output_limit_checks(production: Any) -> dict[str, object]:
    from mathhead.run_audit import RunAuditBundle, replay_run_audit
    from tests.execution_disposition.fixtures import PlannedFixture

    fixture = PlannedFixture()
    audit = fixture.audited_bundle()
    manifest = json.loads(audit.manifest)
    cases = (
        ("physical_objects", {"MAX_AUDIT_OBJECTS": len(audit.objects) - 1}),
        ("manifest_records", {"MAX_AUDIT_OBJECTS": len(audit.objects)}),
        ("events", {"MAX_AUDIT_EVENTS": len(manifest["events"]) - 1}),
        ("manifest_bytes", {"MAX_AUDIT_BYTES": len(audit.manifest) - 1}),
        (
            "object_bytes",
            {"MAX_AUDIT_BYTES": max(len(raw) for raw in audit.objects) - 1},
        ),
        (
            "aggregate_objects",
            {"MAX_AGGREGATE_AUDIT_BYTES": sum(map(len, audit.objects)) - 1},
        ),
        ("replay_operations", {"MAX_REPLAY_OPERATIONS": 1}),
    )
    rejected: list[str] = []
    for label, patches in cases:
        with ExitStack() as stack:
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(production, name, value))
            audited = stack.enter_context(
                mock.patch.object(production, "execute_audited_run", return_value=audit)
            )
            replayed = stack.enter_context(mock.patch.object(production, "replay_run_audit"))
            bundle = production.execute_with_disposition(*fixture.inputs.call_arguments)
            mapping = json.loads(production.execution_disposition_result_bytes(bundle.result))
        diagnostics = mapping.get("diagnostics")
        if (
            audited.call_count != 1
            or replayed.call_count
            or mapping.get("execution_state") != "attempted_no_bundle"
            or mapping.get("classification", {}).get("cause") != "internal_error"
            or mapping.get("classification", {}).get("phase") != "audit"
            or type(diagnostics) is not list
            or len(diagnostics) != 1
            or diagnostics[0].get("code") != "AUDITED_EXECUTION_INVALID"
            or bundle.audit is not None
            or bundle.replay is not None
        ):
            _fail(f"audit output ceiling crossed replay or retention: {label}")
        rejected.append(label)

    secret = b"credential=mh056-validator-path-env-stderr"
    forged = object.__new__(RunAuditBundle)
    for name, value in (
        ("manifest", audit.manifest),
        ("objects", tuple(sorted((*audit.objects, secret), key=_sha))),
        ("logical_report", audit.logical_report),
        ("manifest_sha256", audit.manifest_sha256),
        ("logical_report_sha256", audit.logical_report_sha256),
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    with (
        mock.patch.object(production, "execute_audited_run", return_value=forged),
        mock.patch.object(production, "replay_run_audit", wraps=replay_run_audit) as replayed,
    ):
        detached = production.execute_with_disposition(*fixture.inputs.call_arguments)
        detached_raw = production.execution_disposition_result_bytes(detached.result)
    if (
        replayed.call_count != 1
        or replayed.call_args.args != (forged.manifest, forged.objects)
        or detached.result.execution_state != "bundle_replay_failed"
        or detached.result.replay_status != "invalid"
        or detached.audit is not None
        or detached.replay is not None
        or secret in detached_raw
        or secret.decode("ascii") in repr(detached)
    ):
        _fail("replay-invalid hostile audit bytes survived in the returned graph")
    return {
        "checks_before_replay": rejected,
        "hostile_failed_replay_sidecars": "discarded",
        "replay_operation_model": "bounded_before_replay",
    }


def _runtime_replay_operation_model_check(production: Any) -> dict[str, object]:
    """Bind production to an independent exact and adversarial replay-cost oracle."""

    from tests.execution_disposition.fixtures import PlannedFixture

    helper = getattr(production, "_replay_operation_preflight", None)
    exhausted_type = getattr(production, "_Exhausted", None)
    if not callable(helper) or not isinstance(exhausted_type, type):
        _fail("production replay-operation preflight is not independently callable")

    def observe_exact(
        label: str, manifest_raw: bytes, objects: tuple[bytes, ...]
    ) -> tuple[int, int, int, int, int]:
        (
            expected,
            byte_count,
            nodes,
            relations,
            normalization_visits,
            manifest,
        ) = _independent_replay_operation_charge(manifest_raw, objects)
        observed = helper(copy.deepcopy(manifest), manifest_raw, objects)
        if observed != expected:
            _fail(f"production replay-operation charge differs from independent oracle: {label}")
        return expected, byte_count, nodes, relations, normalization_visits

    def expect_production_exhausted(
        label: str,
        manifest: dict[str, object] | None,
        manifest_raw: bytes,
        objects: tuple[bytes, ...],
    ) -> None:
        try:
            helper(copy.deepcopy(manifest), manifest_raw, objects)
        except exhausted_type:
            return
        _fail(f"production replay-operation ceiling did not reject: {label}")

    audit = PlannedFixture().audited_bundle()
    genuine = observe_exact("genuine", audit.manifest, audit.objects)
    genuine_mapping = _independent_replay_mapping(audit.manifest)
    if genuine_mapping is None:
        _fail("genuine audit manifest is not independently canonical")
    with mock.patch.object(production, "MAX_REPLAY_OPERATIONS", genuine[0]):
        boundary = helper(copy.deepcopy(genuine_mapping[0]), audit.manifest, audit.objects)
    if boundary != genuine[0]:
        _fail("exact replay-operation boundary did not remain inclusive")
    with mock.patch.object(production, "MAX_REPLAY_OPERATIONS", genuine[0] - 1):
        expect_production_exhausted(
            "one below exact charge", genuine_mapping[0], audit.manifest, audit.objects
        )
    try:
        _independent_replay_operation_charge(
            audit.manifest,
            audit.objects,
            maximum_operations=genuine[0] - 1,
        )
    except _IndependentReplayExhausted:
        pass
    else:
        _fail("independent replay oracle lost saturating limit semantics")

    width = 12
    hostile_manifest = {
        "events": [
            {
                "event": index,
                "subjects": [f"{subject:064x}" for subject in range(width)],
            }
            for index in range(width)
        ],
        "objects": [
            {"role": f"hostile_{index}", "sha256": f"{index:064x}"} for index in range(width)
        ],
    }
    hostile_manifest_raw = _canonical(hostile_manifest)
    hostile_objects = tuple(
        _canonical(
            {
                "bucket": bucket,
                "rows": [{"left": bucket, "right": item} for item in range(width)],
            }
        )
        for bucket in range(width)
    )
    hostile = observe_exact("superlinear hostile", hostile_manifest_raw, hostile_objects)
    hostile_mapping = _independent_replay_mapping(hostile_manifest_raw)
    if hostile_mapping is None or hostile[2] <= 1:
        _fail("superlinear hostile replay fixture is not independently valid")
    linear_charge = hostile[1] * 256 + hostile[3] * 64
    expected_quadratic_charge = hostile[2] * hostile[2] * 8
    if hostile[0] - linear_charge != expected_quadratic_charge:
        _fail("independent replay oracle did not isolate the quadratic node charge")
    weakened_linear_node_limit = linear_charge + hostile[2] * 8
    with mock.patch.object(production, "MAX_REPLAY_OPERATIONS", weakened_linear_node_limit):
        expect_production_exhausted(
            "superlinear hostile fixture",
            hostile_mapping[0],
            hostile_manifest_raw,
            hostile_objects,
        )
    with mock.patch.object(production, "MAX_JSON_NODES", hostile[2] - 1):
        expect_production_exhausted(
            "aggregate JSON node cap",
            hostile_mapping[0],
            hostile_manifest_raw,
            hostile_objects,
        )
    try:
        _independent_replay_operation_charge(
            hostile_manifest_raw,
            hostile_objects,
            maximum_nodes=hostile[2] - 1,
        )
    except _IndependentReplayExhausted:
        pass
    else:
        _fail("independent replay oracle lost the aggregate JSON node cap")

    def normalization_dag(depth: int) -> bytes:
        expressions: list[dict[str, object]] = [
            {
                "id": "expression_0",
                "kind": "literal",
                "domain_id": "domain_integer",
                "literal_type": "integer",
                "value": "0",
                "span_ids": [],
            }
        ]
        for index in range(1, depth + 1):
            expressions.append(
                {
                    "id": f"expression_{index}",
                    "kind": "apply",
                    "domain_id": "domain_integer",
                    "operator": "org.mathhead.validator.ordered",
                    "argument_expr_ids": [
                        f"expression_{index - 1}",
                        f"expression_{index - 1}",
                    ],
                    "attributes": {},
                    "span_ids": [],
                }
            )
        entities = {
            "domains": [
                {
                    "id": "domain_integer",
                    "kind": "builtin",
                    "name": "integer",
                    "span_ids": [],
                }
            ],
            "variables": [],
            "expressions": expressions,
            "relations": [],
            "statements": [],
            "definitions": [],
            "assumptions": [],
            "goals": [],
        }
        return _canonical(
            {
                "schema": "mathhead.canonical-normalization-result.v1",
                "status": "normalized",
                "proof_obligation_result": {
                    "domain_assumption_result": {
                        "readings_result": {
                            "candidates": [{"projection": {"entities": entities}}]
                        }
                    }
                },
            }
        )

    empty_manifest_raw = _canonical({})
    empty_manifest = _independent_replay_mapping(empty_manifest_raw)
    if empty_manifest is None:
        _fail("independent empty replay manifest is not canonical")
    bounded_normalization = observe_exact(
        "bounded normalization DAG", empty_manifest_raw, (normalization_dag(8),)
    )
    if bounded_normalization[4] <= 0:
        _fail("normalization DAG did not receive an expansion surcharge")
    excessive_normalization_raw = normalization_dag(12)
    try:
        _independent_replay_operation_charge(
            empty_manifest_raw, (excessive_normalization_raw,)
        )
    except _IndependentReplayExhausted:
        pass
    else:
        _fail("independent normalization DAG expansion did not exhaust")
    expect_production_exhausted(
        "normalization DAG expansion",
        empty_manifest[0],
        empty_manifest_raw,
        (excessive_normalization_raw,),
    )

    return {
        "exact_boundary_inclusive": True,
        "genuine_charge": genuine[0],
        "normalization_dag_bounded_charge": bounded_normalization[0],
        "normalization_dag_excessive_rejected": True,
        "node_cap_bound": True,
        "one_below_rejected": True,
        "superlinear_hostile_charge": hostile[0],
        "superlinear_hostile_nodes": hostile[2],
    }


def _runtime_fatal_codec_checks(production: Any) -> dict[str, object]:
    from tests.execution_disposition.fixtures import EarlyFixture, PlannedFixture

    request = production.parse_execution_disposition_request(
        PlannedFixture(origin_source="user").inputs.request
    )
    invalid_fixture = EarlyFixture()
    invalid_fixture.inputs = replace(invalid_fixture.inputs, request=b'{"malformed":\n')
    invalid = production.execute_with_disposition(*invalid_fixture.inputs.call_arguments)
    parser_cases = (
        production.parse_cancellation_intent,
        production.parse_execution_disposition_request,
        production.parse_execution_disposition_classification,
        production.parse_execution_disposition_diagnostic,
        production.parse_execution_disposition_result,
    )
    validator_cases = (
        (production.validate_cancellation_intent, request.cancellation_intent, "_intent_mapping"),
        (production.validate_execution_disposition_request, request, "_request_mapping"),
        (
            production.validate_execution_disposition_classification,
            invalid.result.classification,
            "_classification_mapping",
        ),
        (
            production.validate_execution_disposition_diagnostic,
            invalid.result.diagnostics[0],
            "_diagnostic_mapping",
        ),
        (production.validate_execution_disposition_result, invalid.result, "_result_mapping"),
    )
    propagated: list[str] = []
    for parser in parser_cases:
        for fatal_type in (MemoryError, KeyboardInterrupt, SystemExit):
            with mock.patch.object(production, "_parse", side_effect=fatal_type()):
                try:
                    parser(b"{}\n")
                except BaseException as caught:
                    if type(caught) is not fatal_type:
                        _fail(f"codec fatal changed type: {parser.__name__}/{fatal_type.__name__}")
                else:
                    _fail(f"codec fatal was serialized: {parser.__name__}/{fatal_type.__name__}")
            propagated.append(f"{parser.__name__}:{fatal_type.__name__}")
    for validator, value, dependency in validator_cases:
        for fatal_type in (MemoryError, KeyboardInterrupt, SystemExit):
            with mock.patch.object(production, dependency, side_effect=fatal_type()):
                try:
                    validator(value)
                except BaseException as caught:
                    if type(caught) is not fatal_type:
                        _fail(
                            f"validator fatal changed type: "
                            f"{validator.__name__}/{fatal_type.__name__}"
                        )
                else:
                    _fail(
                        f"validator fatal was serialized: "
                        f"{validator.__name__}/{fatal_type.__name__}"
                    )
            propagated.append(f"{validator.__name__}:{fatal_type.__name__}")
    return {"propagated_cases": len(propagated), "surfaces": propagated}


def _runtime_failed_replay_binding_check(production: Any) -> dict[str, object]:
    from mathhead.run_audit import replay_run_audit
    from tests.execution_disposition.fixtures import PlannedFixture

    fixture = PlannedFixture()
    audit = fixture.audited_bundle()
    stale = replay_run_audit(b"{}\n", ())
    with (
        mock.patch.object(production, "execute_audited_run", return_value=audit),
        mock.patch.object(production, "replay_run_audit", return_value=stale),
    ):
        rejected = production.execute_with_disposition(*fixture.inputs.call_arguments)
    rejected_mapping = json.loads(production.execution_disposition_result_bytes(rejected.result))
    if (
        rejected_mapping.get("execution_state") != "attempted_no_bundle"
        or rejected_mapping.get("classification", {}).get("cause") != "internal_error"
        or rejected.audit is not None
        or rejected.replay is not None
    ):
        _fail("failed replay from stale inputs was retained")

    current = object.__new__(type(stale))
    for value_field in fields(type(stale)):
        object.__setattr__(current, value_field.name, getattr(stale, value_field.name))
    object.__setattr__(current, "_input_manifest", audit.manifest)
    object.__setattr__(current, "_input_objects", audit.objects)
    object.__setattr__(current, "object_count", len(audit.objects))
    current_mapping = {
        value_field.name: getattr(current, value_field.name)
        for value_field in fields(type(current))
        if not value_field.name.startswith("_")
    }
    object.__setattr__(
        current,
        "replay_result_sha256",
        _self_hash(current_mapping, "replay_result_sha256"),
    )
    with (
        mock.patch.object(production, "execute_audited_run", return_value=audit),
        mock.patch.object(production, "replay_run_audit", return_value=current),
    ):
        retained = production.execute_with_disposition(*fixture.inputs.call_arguments)
    retained_mapping = json.loads(production.execution_disposition_result_bytes(retained.result))
    retained_diagnostics = retained_mapping.get("diagnostics")
    if (
        retained_mapping.get("execution_state") != "bundle_replay_failed"
        or retained_mapping.get("classification", {}).get("cause") != "internal_error"
        or retained_mapping.get("audit_manifest_sha256") != audit.manifest_sha256
        or retained_mapping.get("replay_result_sha256")
        != current.replay_result_sha256
        or retained_mapping.get("replay_status") != "invalid"
        or retained_mapping.get("replay_reason_code") != "REPLAY_INVALID"
        or type(retained_diagnostics) is not list
        or len(retained_diagnostics) != 1
        or retained_diagnostics[0].get("code") != "AUDIT_REPLAY_INVALID"
        or retained.audit is not None
        or retained.replay is not None
    ):
        _fail("failed replay bound to current audit lost its truthful evidence state")
    anchored = production.execution_disposition_anchored_budget_bytes(retained)
    portfolio_request = production.execution_disposition_portfolio_request_bytes(retained)
    parsed = production.parse_execution_disposition_result(
        production.execution_disposition_result_bytes(retained.result),
        request_input=fixture.inputs.request,
        request=retained.request,
        anchored_parent_budget=anchored,
        portfolio_request=portfolio_request,
    )
    if production.execution_disposition_result_bytes(parsed) != production.execution_disposition_result_bytes(
        retained.result
    ):
        _fail("detached failed replay did not round-trip from scalar evidence")
    try:
        production.parse_execution_disposition_result(
            production.execution_disposition_result_bytes(retained.result),
            request_input=fixture.inputs.request,
            request=retained.request,
            anchored_parent_budget=anchored,
            portfolio_request=portfolio_request,
            audit=audit,
            replay=current,
        )
    except production.ExecutionDispositionValidationError:
        hostile_sidecars_rejected = True
    else:
        _fail("failed replay accepted unvalidated raw audit sidecars")
    return {
        "current_failed_replay_scalar_evidence": True,
        "hostile_sidecars_rejected": hostile_sidecars_rejected,
        "stale_failed_replay_rejected": True,
    }


def _drop_portfolio_input_identity(audit: object, field: str) -> object:
    from mathhead.run_audit import RunAuditBundle, validate_run_audit_bundle

    if type(audit) is not RunAuditBundle:
        _fail("portfolio identity attack requires one exact RunAuditBundle")
    manifest = json.loads(audit.manifest)
    physical = {_sha(raw): raw for raw in audit.objects}
    records = {item["role_id"]: item for item in manifest["objects"]}
    portfolio_record = records["portfolio_result"]
    old_portfolio = portfolio_record["sha256"]
    portfolio = json.loads(physical.pop(old_portfolio))
    portfolio[field] = None
    portfolio["result_sha256"] = _self_hash(portfolio, "result_sha256")
    portfolio_raw = _canonical(portfolio)
    new_portfolio = _sha(portfolio_raw)
    physical[new_portfolio] = portfolio_raw
    portfolio_record["sha256"] = new_portfolio
    portfolio_record["byte_count"] = len(portfolio_raw)
    portfolio_record["record_sha256"] = _self_hash(portfolio_record, "record_sha256")
    manifest["portfolio_result_sha256"] = new_portfolio
    closed = manifest["events"][-1]
    if closed.get("kind") != "run_closed" or old_portfolio not in closed.get("subject_sha256s", []):
        _fail("portfolio identity attack lacks its terminal manifest relation")
    closed["subject_sha256s"] = sorted(
        new_portfolio if item == old_portfolio else item for item in closed["subject_sha256s"]
    )
    closed["event_sha256"] = _self_hash(closed, "event_sha256")
    manifest["manifest_sha256"] = _self_hash(manifest, "manifest_sha256")
    manifest_raw = _canonical(manifest)
    objects = tuple(physical[identity] for identity in sorted(physical))
    forged = object.__new__(RunAuditBundle)
    for name, value in (
        ("manifest", manifest_raw),
        ("objects", objects),
        ("logical_report", audit.logical_report),
        ("manifest_sha256", _sha(manifest_raw)),
        ("logical_report_sha256", _sha(audit.logical_report)),
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    validate_run_audit_bundle(forged)
    return forged


def _runtime_portfolio_input_binding_check(production: Any) -> dict[str, object]:
    from mathhead.run_audit import replay_run_audit
    from tests.execution_disposition.fixtures import PlannedFixture

    fixture = PlannedFixture()
    rejected: list[str] = []
    for field in ("request_sha256", "planning_result_sha256"):
        forged = _drop_portfolio_input_identity(fixture.audited_bundle(), field)
        independent = replay_run_audit(forged.manifest, forged.objects)
        if independent.status != "complete":
            _fail(f"portfolio identity attack is not replay-complete: {field}")
        with (
            mock.patch.object(production, "execute_audited_run", return_value=forged) as audited,
            mock.patch.object(production, "replay_run_audit", wraps=replay_run_audit) as replayed,
        ):
            bundle = production.execute_with_disposition(*fixture.inputs.call_arguments)
        mapping = json.loads(production.execution_disposition_result_bytes(bundle.result))
        diagnostics = mapping.get("diagnostics")
        if (
            audited.call_count != 1
            or replayed.call_count != 1
            or replayed.call_args.args != (forged.manifest, forged.objects)
            or mapping.get("classification", {}).get("cause") != "internal_error"
            or mapping.get("portfolio_relation") != "invalid"
            or type(diagnostics) is not list
            or len(diagnostics) != 1
            or diagnostics[0].get("code") != "AUDIT_RELATION_INVALID"
        ):
            _fail(f"terminal portfolio omitted its current input identity: {field}")
        rejected.append(field)
    return {"replay_complete_null_identities_rejected": rejected}


def _rehashed_outer_pair_audit(audit: object) -> object:
    from mathhead.run_audit import (
        RunAuditBundle,
        replay_run_audit,
        validate_run_audit_bundle,
    )

    if type(audit) is not RunAuditBundle:
        _fail("outer-pair attack requires one exact RunAuditBundle")
    manifest = json.loads(audit.manifest)
    physical = {_sha(raw): raw for raw in audit.objects}
    records = {item["role_id"]: item for item in manifest["objects"]}

    portfolio_record = records["portfolio_result"]
    old_portfolio = portfolio_record["sha256"]
    portfolio = json.loads(physical.pop(old_portfolio))
    if (portfolio.get("status"), portfolio.get("reason_code")) != (
        "inconclusive",
        "CHECKER_INCONCLUSIVE",
    ):
        _fail("outer-pair attack source is not checker-inconclusive")
    portfolio.update(status="ambiguous", reason_code="EVIDENCE_INCOMPLETE")
    portfolio["result_sha256"] = _self_hash(portfolio, "result_sha256")
    portfolio_raw = _canonical(portfolio)
    new_portfolio = _sha(portfolio_raw)
    physical[new_portfolio] = portfolio_raw

    report_record = records["logical_report"]
    old_report = report_record["sha256"]
    report = json.loads(physical.pop(old_report))
    if (report.get("status"), report.get("reason_code")) != (
        "inconclusive",
        "CHECKER_INCONCLUSIVE",
    ):
        _fail("outer-pair logical report source is not checker-inconclusive")
    report.update(status="ambiguous", reason_code="EVIDENCE_INCOMPLETE")
    report["report_sha256"] = _self_hash(report, "report_sha256")
    report_raw = _canonical(report)
    new_report = _sha(report_raw)
    physical[new_report] = report_raw

    for record, raw, identity in (
        (portfolio_record, portfolio_raw, new_portfolio),
        (report_record, report_raw, new_report),
    ):
        record["sha256"] = identity
        record["byte_count"] = len(raw)
        record["record_sha256"] = _self_hash(record, "record_sha256")

    replacements = {
        old_portfolio: new_portfolio,
        old_report: new_report,
    }
    previous: str | None = None
    for event in manifest["events"]:
        event["subject_sha256s"] = sorted(
            replacements.get(item, item) for item in event["subject_sha256s"]
        )
        if event["kind"] == "run_closed":
            event["reason_code"] = "EVIDENCE_INCOMPLETE"
        event["previous_event_sha256"] = previous
        event["event_sha256"] = _self_hash(event, "event_sha256")
        previous = event["event_sha256"]
    manifest["portfolio_result_sha256"] = new_portfolio
    manifest["logical_report_sha256"] = new_report
    manifest["manifest_sha256"] = _self_hash(manifest, "manifest_sha256")
    manifest_raw = _canonical(manifest)
    objects = tuple(physical[identity] for identity in sorted(physical))
    replay = replay_run_audit(manifest_raw, objects)
    if (
        replay.status != "complete"
        or replay.reason_code != "REPLAY_COMPLETE"
        or replay.portfolio_status != "ambiguous"
        or replay.logical_report_sha256 != new_report
    ):
        _fail("rehashed outer pair attack did not remain replay-complete")

    forged = object.__new__(RunAuditBundle)
    for name, value in (
        ("manifest", manifest_raw),
        ("objects", objects),
        ("logical_report", report_raw),
        ("manifest_sha256", _sha(manifest_raw)),
        ("logical_report_sha256", new_report),
        ("mathematical_authority", False),
    ):
        object.__setattr__(forged, name, value)
    validate_run_audit_bundle(forged)
    return forged


def _runtime_planned_checks(production: Any) -> dict[str, object]:
    from mathhead.run_audit import replay_run_audit
    from tests.execution_disposition.fixtures import PlannedFixture

    fixture = PlannedFixture(origin_source="user")
    audit = fixture.audited_bundle()
    event = fixture.inputs.cancel_event
    if event is None:
        _fail("planned cancellation fixture lacks its exact Event")
    event.set()
    order: list[str] = []
    observed_arguments: tuple[object, ...] | None = None

    def audited_boundary(*arguments: object) -> object:
        nonlocal observed_arguments
        observed_arguments = arguments
        order.append("execute_audited_run")
        return audit

    def replay_boundary(*arguments: object) -> object:
        order.append("replay_run_audit")
        return replay_run_audit(*arguments)

    with (
        mock.patch.object(
            production, "execute_audited_run", side_effect=audited_boundary
        ) as audited,
        mock.patch.object(production, "replay_run_audit", side_effect=replay_boundary) as replay,
    ):
        bundle = production.execute_with_disposition(*fixture.inputs.call_arguments)
        production.validate_execution_disposition_bundle(bundle)
        raw = production.execution_disposition_result_bytes(bundle.result)
    if observed_arguments is None:
        _fail("planned execution did not reach the audited boundary")
    expected_arguments = (
        fixture.inputs.planning_request,
        fixture.inputs.route_result,
        fixture.portfolio_request(),
        fixture.inputs.planning_result,
        fixture.expected_anchor,
        fixture.inputs.descriptors,
        fixture.inputs.bindings,
        tuple(raw for _, raw in fixture.inputs.artifacts),
        fixture.inputs.executable_paths,
        fixture.inputs.workspace_root,
        event,
    )
    mapping = json.loads(raw)
    _require_result_identity(mapping, "planned-checked-proof")
    classification = mapping.get("classification")
    independently_anchored = _derive_anchor(
        fixture.inputs.base_parent_budget,
        str(fixture.inputs.request_value["request_sha256"]),
    )
    if (
        audited.call_count != 1
        or replay.call_count != 1
        or order != ["execute_audited_run", "replay_run_audit"]
        or observed_arguments != expected_arguments
        or observed_arguments[-1] is not event
        or observed_arguments[4] != independently_anchored
        or observed_arguments[2] != fixture.portfolio_request()
        or type(classification) is not dict
        or classification.get("cause") != "checked_proof"
        or classification.get("phase") != "completed"
        or mapping.get("execution_state") != "replayed_complete"
        or mapping.get("portfolio_relation") != "exact"
        or mapping.get("portfolio_status") != "succeeded"
        or mapping.get("portfolio_reason_code") != "CHECKED_PROOF"
        or any(
            mapping.get(name) is None
            for name in (
                "selected_strategy_sha256",
                "selected_evidence_sha256",
                "selected_certificate_sha256",
                "selected_checker_decision_sha256",
            )
        )
        or bundle.audit is not audit
        or bundle.replay is None
    ):
        _fail("planned exact-once, fresh-replay, anchor, or checked relation drift")

    forged_pair = copy.deepcopy(mapping)
    forged_classification = forged_pair["classification"]
    if type(forged_classification) is not dict:
        _fail("planned classification is not available for pair mutation")
    forged_pair.update(
        portfolio_status="ambiguous",
        portfolio_reason_code="EVIDENCE_INCOMPLETE",
        selected_strategy_sha256=None,
        selected_evidence_sha256=None,
        selected_certificate_sha256=None,
        selected_checker_decision_sha256=None,
        linked_authority_tier="none",
    )
    forged_classification.update(
        disposition="inconclusive",
        cause="ambiguity",
        precedence_row="80_semantic_terminal",
        precedence_rank=80,
        phase="producer",
        origin_source=None,
        observer_source=None,
        observer_cancellation_id=None,
        observer_basis=None,
        resource_dimensions=[],
        classification_sha256=None,
        mathematical_authority=False,
    )
    forged_classification["classification_sha256"] = _self_hash(
        forged_classification, "classification_sha256"
    )
    forged_pair["result_sha256"] = _self_hash(forged_pair, "result_sha256")
    if bundle.request is None or bundle.replay is None:
        _fail("planned bundle lacks retained values for pair relation mutation")
    try:
        production.parse_execution_disposition_result(
            _canonical(forged_pair),
            request_input=fixture.inputs.request,
            request=bundle.request,
            anchored_parent_budget=independently_anchored,
            portfolio_request=fixture.portfolio_request(),
            audit=audit,
            replay=bundle.replay,
        )
    except production.ExecutionDispositionValidationError:
        pair_relation_rejected = True
    else:
        _fail("repaired accepted pair/cause transplant crossed the retained audit")

    substitution_fixture = PlannedFixture(certificate_status="unsupported")
    genuine_inconclusive = substitution_fixture.audited_bundle()
    altered_audit = _rehashed_outer_pair_audit(genuine_inconclusive)
    with (
        mock.patch.object(
            production, "execute_audited_run", return_value=altered_audit
        ) as substituted_audit,
        mock.patch.object(
            production, "replay_run_audit", wraps=replay_run_audit
        ) as substituted_replay,
    ):
        substituted = production.execute_with_disposition(
            *substitution_fixture.inputs.call_arguments
        )
        production.validate_execution_disposition_bundle(substituted)
        substituted_raw = production.execution_disposition_result_bytes(substituted.result)
    substituted_mapping = json.loads(substituted_raw)
    substituted_diagnostics = substituted_mapping.get("diagnostics")
    if (
        substituted_audit.call_count != 1
        or substituted_replay.call_count != 1
        or substituted_replay.call_args.args != (altered_audit.manifest, altered_audit.objects)
        or substituted_mapping.get("execution_state") != "replayed_complete"
        or substituted_mapping.get("portfolio_relation") != "invalid"
        or substituted_mapping.get("portfolio_status") != "ambiguous"
        or substituted_mapping.get("portfolio_reason_code") != "EVIDENCE_INCOMPLETE"
        or substituted_mapping.get("classification", {}).get("cause") != "internal_error"
        or substituted_mapping.get("classification", {}).get("phase") != "audit"
        or type(substituted_diagnostics) is not list
        or len(substituted_diagnostics) != 1
        or substituted_diagnostics[0].get("code") != "AUDIT_RELATION_INVALID"
        or substituted.audit is not altered_audit
        or substituted.replay is None
        or substituted.replay.status != "complete"
    ):
        _fail("replay-complete rehashed outer pair was normalized as ordinary")

    secret = "mh056-validator-secret-must-not-survive"
    with (
        mock.patch.object(
            production, "execute_audited_run", side_effect=ValueError(secret)
        ) as failed_audit,
        mock.patch.object(production, "replay_run_audit") as failed_replay,
    ):
        failure = production.execute_with_disposition(*fixture.inputs.call_arguments)
        failure_raw = production.execution_disposition_result_bytes(failure.result)
    failure_mapping = json.loads(failure_raw)
    failure_diagnostics = failure_mapping.get("diagnostics")
    if (
        failed_audit.call_count != 1
        or failed_replay.call_count
        or secret.encode("ascii") in failure_raw
        or failure_mapping.get("execution_state") != "attempted_no_bundle"
        or failure_mapping.get("classification", {}).get("cause") != "internal_error"
        or failure_mapping.get("classification", {}).get("phase") != "audit"
        or type(failure_diagnostics) is not list
        or len(failure_diagnostics) != 1
        or failure_diagnostics[0].get("code") != "AUDITED_EXECUTION_INVALID"
    ):
        _fail("ordinary audited exception was retried, leaked, or misclassified")

    propagated: list[str] = []
    for fatal in (MemoryError(), KeyboardInterrupt(), SystemExit(7)):
        with (
            mock.patch.object(production, "execute_audited_run", side_effect=fatal) as fatal_audit,
            mock.patch.object(production, "replay_run_audit") as fatal_replay,
        ):
            try:
                production.execute_with_disposition(*fixture.inputs.call_arguments)
            except BaseException as caught:
                if type(caught) is not type(fatal):
                    _fail(f"fatal control changed type: {type(fatal).__name__}")
            else:
                _fail(f"fatal control was serialized: {type(fatal).__name__}")
        if fatal_audit.call_count != 1 or fatal_replay.call_count:
            _fail(f"fatal control was retried or replayed: {type(fatal).__name__}")
        propagated.append(type(fatal).__name__)
    return {
        "audited_calls": 1,
        "classification": "checked_proof",
        "event_identity_forwarded": True,
        "final_event_state_ignored": True,
        "fresh_replays": 1,
        "ordinary_exception_static": True,
        "repaired_result_pair_projection_rejected": pair_relation_rejected,
        "replayed_outer_pair_substitution": "internal_error",
        "propagated_fatal_controls": propagated,
    }


def _fresh_process_check() -> dict[str, object]:
    code = """
from mathhead.execution_disposition import execute_with_disposition, execution_disposition_result_bytes
from tests.execution_disposition.fixtures import EarlyFixture
fixture = EarlyFixture('unsupported_input')
bundle = execute_with_disposition(*fixture.inputs.call_arguments)
print(execution_disposition_result_bytes(bundle.result).hex())
"""
    fingerprints: list[str] = []
    for seed in ("1", "8675309"):
        environment = dict(os.environ)
        python_path = [str(ROOT / "src"), str(ROOT)]
        inherited = environment.get("PYTHONPATH")
        if inherited:
            python_path.append(inherited)
        environment["PYTHONPATH"] = os.pathsep.join(python_path)
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            _fail(
                f"fresh-process disposition fixture failed for seed {seed}: "
                f"{completed.stderr.strip()}"
            )
        fingerprint = completed.stdout.strip()
        try:
            raw = bytes.fromhex(fingerprint)
        except ValueError as exc:
            raise ExecutionDispositionValidationFailure(
                "fresh-process fixture did not emit exact result bytes"
            ) from exc
        fingerprints.append(_sha(raw))
    if len(set(fingerprints)) != 1:
        _fail("fresh-process result bytes differ across hash seeds")
    return {"hash_seeds": 2, "result_bytes_sha256": fingerprints[0]}


def _test_bindings() -> dict[str, object]:
    bindings: dict[str, str] = {}
    cases = 0
    cases_by_module: dict[str, int] = {}
    paths = (TEST_FIXTURE_PATH, *sorted(TEST_DIRECTORY.glob("test_*.py")))
    if len(paths) < 3:
        _fail("execution-disposition security test modules are incomplete")
    for path in paths:
        if not path.is_file():
            _fail(f"required execution-disposition test artifact is absent: {path.name}")
        relative = path.relative_to(ROOT).as_posix()
        bindings[relative] = _sha(path.read_bytes())
        if path.name.startswith("test_"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            module_cases = sum(
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
                for node in ast.walk(tree)
            )
            if module_cases == 0:
                _fail(f"execution-disposition test module has no test cases: {relative}")
            cases += module_cases
            cases_by_module[relative] = module_cases
    if cases < 30:
        _fail("execution-disposition executable test inventory is incomplete")
    return {
        "cases": cases,
        "cases_by_module": cases_by_module,
        "sha256s": bindings,
    }


def _report() -> dict[str, object]:
    from mathhead import execution_disposition as production

    report: dict[str, object] = {
        "anchor": _anchor_check(),
        "contract": _contract_registration_check(),
        "identity_projection": _identity_projection_check(),
        "mathematical_authority": False,
        "production_binding": _production_binding_check(production),
        "report_sha256": None,
        "runtime": {
            "audit_output_limits": _runtime_audit_output_limit_checks(production),
            "bundle_request_presence": _runtime_bundle_presence_check(production),
            "early_outcomes": _runtime_early_checks(production),
            "fatal_codecs": _runtime_fatal_codec_checks(production),
            "failed_replay_binding": _runtime_failed_replay_binding_check(production),
            "fresh_process": _fresh_process_check(),
            "input_byte_limits": _runtime_input_limit_checks(production),
            "invalid_request": _runtime_invalid_request_check(production),
            "planned_exact_once": _runtime_planned_checks(production),
            "portfolio_input_binding": _runtime_portfolio_input_binding_check(production),
            "replay_operation_model": _runtime_replay_operation_model_check(production),
            "request_result_projection": _runtime_projection_mutations(production),
            "unsupported_multi_group": _runtime_unsupported_multi_group_check(production),
        },
        "schema": REPORT_SCHEMA,
        "schemas": _schema_checks(),
        "source": _source_checks(),
        "status": "passed",
        "tests": _test_bindings(),
        "validator_sha256": _sha(Path(__file__).read_bytes()),
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    rendered = _canonical(report)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(rendered)
        print(f"execution-disposition: report updated: {path}")
        return
    if not path.is_file() or path.read_bytes() != rendered:
        _fail(f"frozen report drift or missing: {path.relative_to(ROOT)}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write-report", action="store_true")
    group.add_argument("--check-report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = _report()
        path = REPORT_PATH if args.check_report is None else ROOT / args.check_report
        _write_or_check(report, path, write=args.write_report)
    except (
        ExecutionDispositionValidationFailure,
        OSError,
        SyntaxError,
        UnicodeError,
        ValueError,
        subprocess.SubprocessError,
        tomllib.TOMLDecodeError,
    ) as exc:
        print(f"execution-disposition: FAIL: {exc}", file=sys.stderr)
        return 1
    runtime = report["runtime"]
    if type(runtime) is not dict:
        _fail("runtime report is not an object")
    print(
        "execution-disposition: PASS "
        "(accepted binding, closed schemas, exact-once audit, fresh replay)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
