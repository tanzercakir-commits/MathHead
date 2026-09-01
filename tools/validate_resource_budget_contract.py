#!/usr/bin/env python3
"""Independently validate the accepted ResourceBudget v1 schema and ledger semantics."""

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
CONTRACT_ID = "MH-C-RESOURCE-BUDGET-001"
EXPECTED_CONTRACT_SHA256 = "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045"
SCHEMA_PATH = Path("docs/contracts/schemas/resource-budget-v1.schema.json")
EXPECTED_SCHEMA_SHA256 = "e735dee47394bf50c10ac571dfc8923fd1da851e258b1d9f42e1a66bb9d85e78"
ROOT_FIELDS = {
    "schema",
    "budget_id",
    "lineage",
    "policy",
    "limits",
    "events",
    "outcome",
    "extensions",
}
DIMENSIONS = (
    "cpu_time_us",
    "diagnostic_bytes",
    "evidence_bytes",
    "generated_objects",
    "memory_bytes",
    "nesting_depth",
    "output_bytes",
    "proof_bytes",
    "solver_calls",
    "wall_time_us",
)
CUMULATIVE_DIMENSIONS = (
    "cpu_time_us",
    "diagnostic_bytes",
    "evidence_bytes",
    "generated_objects",
    "output_bytes",
    "proof_bytes",
    "solver_calls",
)
TRUNCATABLE_DIMENSIONS = {
    "diagnostic_bytes",
    "evidence_bytes",
    "generated_objects",
    "output_bytes",
    "proof_bytes",
}
MAX_VALIDATION_SECONDS = 30.0
MAX_INPUT_BYTES = 67_108_864
MAX_CANONICAL_NODES = 4_000_000
MAX_CANONICAL_NESTING = 64
MAX_STRING_CODEPOINTS = 1_048_576
MAX_JSON_INTEGER = 9_007_199_254_740_991
MAX_EVENTS = 100_000
MAX_ACTIVE_LEASES = 10_000


class ResourceBudgetValidationError(RuntimeError):
    """A classified schema, identity, accounting, or outcome validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise ResourceBudgetValidationError(kind, path, detail)


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


def zero_limit_vector() -> dict[str, int]:
    return {dimension: 0 for dimension in DIMENSIONS}


def zero_cumulative_vector() -> dict[str, int]:
    return {dimension: 0 for dimension in CUMULATIVE_DIMENSIONS}


def zero_observation() -> dict[str, int]:
    return {
        "wall_time_us": 0,
        "memory_retained_bytes": 0,
        "memory_peak_bytes": 0,
        "nesting_current": 0,
        "nesting_peak": 0,
    }


def usage_as_limit_vector(usage: dict[str, int]) -> dict[str, int]:
    return {
        "wall_time_us": usage["wall_time_us"],
        "cpu_time_us": usage["cpu_time_us"],
        "memory_bytes": usage["memory_peak_bytes"],
        "solver_calls": usage["solver_calls"],
        "generated_objects": usage["generated_objects"],
        "proof_bytes": usage["proof_bytes"],
        "evidence_bytes": usage["evidence_bytes"],
        "output_bytes": usage["output_bytes"],
        "diagnostic_bytes": usage["diagnostic_bytes"],
        "nesting_depth": usage["nesting_peak"],
    }


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
    except ResourceBudgetValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical ResourceBudget JSON")
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
            except ResourceBudgetValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail("schema", path, f"must match exactly one tagged variant, matched {matches}")
        return
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except ResourceBudgetValidationError:
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


def _positive(vector: dict[str, int]) -> bool:
    return any(value > 0 for value in vector.values())


def _claim(identifier: str, owners: dict[str, str], owner: str, path: str) -> None:
    if identifier in owners:
        _fail("identity", path, f"ID already belongs to {owners[identifier]}")
    owners[identifier] = owner


def _active_totals(active: dict[str, dict[str, Any]]) -> dict[str, int]:
    result = zero_limit_vector()
    for lease in active.values():
        for dimension, amount in lease["allocation"].items():
            result[dimension] += amount
            if result[dimension] > MAX_JSON_INTEGER:
                _fail("budget", "$.events", "active reservation total exceeds exact range")
    return result


def _effective_usage(cumulative: dict[str, int], observation: dict[str, int]) -> dict[str, int]:
    return {
        **cumulative,
        "wall_time_us": observation["wall_time_us"],
        "memory_bytes": observation["memory_retained_bytes"],
        "nesting_depth": observation["nesting_current"],
    }


def _derived_usage(cumulative: dict[str, int], observation: dict[str, int]) -> dict[str, int]:
    return {
        **cumulative,
        "wall_time_us": observation["wall_time_us"],
        "memory_peak_bytes": observation["memory_peak_bytes"],
        "memory_retained_bytes": observation["memory_retained_bytes"],
        "nesting_peak": observation["nesting_peak"],
    }


def _observed_overruns(limits: dict[str, int], observation: dict[str, int]) -> set[str]:
    result: set[str] = set()
    if observation["wall_time_us"] > limits["wall_time_us"]:
        result.add("wall_time_us")
    if (
        observation["memory_peak_bytes"] > limits["memory_bytes"]
        or observation["memory_retained_bytes"] > limits["memory_bytes"]
    ):
        result.add("memory_bytes")
    if (
        observation["nesting_peak"] > limits["nesting_depth"]
        or observation["nesting_current"] > limits["nesting_depth"]
    ):
        result.add("nesting_depth")
    return result


def _validate_lineage(value: dict[str, Any]) -> None:
    lineage = value["lineage"]
    if lineage["kind"] == "root":
        return
    if lineage["parent_budget_id"] == value["budget_id"]:
        _fail("lineage", "$.lineage.parent_budget_id", "child cannot name itself as parent")
    expected = canonical_sha256(value["limits"])
    if lineage["allocation_sha256"] != expected:
        _fail("lineage", "$.lineage.allocation_sha256", "child limits do not match allocation")


def _validate_sample(
    event: dict[str, Any],
    observation: dict[str, int],
    path: str,
) -> None:
    current = event["observation"]
    if current["wall_time_us"] < observation["wall_time_us"]:
        _fail("monotonic", path, "wall time decreased")
    if current["memory_peak_bytes"] < observation["memory_peak_bytes"]:
        _fail("monotonic", path, "memory peak decreased")
    if current["nesting_peak"] < observation["nesting_peak"]:
        _fail("monotonic", path, "nesting peak decreased")
    if current["memory_retained_bytes"] > current["memory_peak_bytes"]:
        _fail("accounting", path, "retained memory exceeds observed peak")
    if current["nesting_current"] > current["nesting_peak"]:
        _fail("accounting", path, "current nesting exceeds observed peak")
    observation.update(current)


def _validate_reserve(
    event: dict[str, Any],
    *,
    limits: dict[str, int],
    cumulative: dict[str, int],
    observation: dict[str, int],
    active: dict[str, dict[str, Any]],
    closed: set[str],
    child_ids: set[str],
    owners: dict[str, str],
    path: str,
) -> None:
    lease_id = event["lease_id"]
    child_id = event["child_budget_id"]
    _claim(lease_id, owners, "lease", f"{path}.lease_id")
    _claim(child_id, owners, "child_budget", f"{path}.child_budget_id")
    if lease_id in active or lease_id in closed:
        _fail("lease", path, "lease ID was already used")
    if child_id in child_ids:
        _fail("lease", path, "child budget ID was already used")
    allocation = event["allocation"]
    if not _positive(allocation):
        _fail("lease", f"{path}.allocation", "child allocation must reserve a resource")
    if event["allocation_sha256"] != canonical_sha256(allocation):
        _fail("identity", f"{path}.allocation_sha256", "allocation identity mismatch")
    if len(active) >= MAX_ACTIVE_LEASES:
        _fail("budget", path, "active child lease count exceeds 10000")
    reserved = _active_totals(active)
    effective = _effective_usage(cumulative, observation)
    unavailable: list[str] = []
    for dimension in DIMENSIONS:
        if effective[dimension] + reserved[dimension] + allocation[dimension] > limits[dimension]:
            unavailable.append(dimension)
    if unavailable:
        _fail("lease", path, f"allocation exceeds available dimensions {unavailable}")
    active[lease_id] = {
        "allocation": allocation,
        "child_budget_id": child_id,
        "wall_start": observation["wall_time_us"],
        "memory_current_start": observation["memory_retained_bytes"],
        "nesting_current_start": observation["nesting_current"],
    }
    child_ids.add(child_id)


def _validate_reconcile(
    event: dict[str, Any],
    *,
    limits: dict[str, int],
    cumulative: dict[str, int],
    observation: dict[str, int],
    active: dict[str, dict[str, Any]],
    closed: set[str],
    must_exhaust: set[str],
    path: str,
) -> None:
    lease_id = event["lease_id"]
    if lease_id not in active:
        _fail("lease", path, "reconciliation names no active lease")
    lease = active[lease_id]
    usage = event["child_usage"]
    if usage["memory_retained_bytes"] > usage["memory_peak_bytes"]:
        _fail("accounting", f"{path}.child_usage", "child retained memory exceeds peak")
    mapped = usage_as_limit_vector(usage)
    allocation = lease["allocation"]
    has_overrun = False
    for dimension in DIMENSIONS:
        allocated = allocation[dimension]
        consumed = mapped[dimension]
        refund = event["refund"][dimension]
        overrun = event["overrun"][dimension]
        if allocated + overrun != consumed + refund:
            _fail("conservation", path, f"{dimension} does not conserve allocation")
        if refund and overrun:
            _fail("conservation", path, f"{dimension} cannot refund and overrun")
        has_overrun = has_overrun or overrun > 0
    if has_overrun and event["child_outcome"] != "exhausted":
        _fail("outcome", path, "child overrun requires exhausted child outcome")
    if event["child_outcome"] == "completed" and has_overrun:
        _fail("outcome", path, "completed child cannot overrun")
    if observation["wall_time_us"] < lease["wall_start"] + usage["wall_time_us"]:
        _fail("observation", path, "parent wall sample does not cover child elapsed time")
    if observation["memory_peak_bytes"] < usage["memory_peak_bytes"]:
        _fail("observation", path, "parent process-tree memory peak omits child peak")
    if observation["nesting_peak"] < lease["nesting_current_start"] + usage["nesting_peak"]:
        _fail("observation", path, "parent nesting peak omits child depth")
    for dimension in CUMULATIVE_DIMENSIONS:
        cumulative[dimension] += usage[dimension]
        if cumulative[dimension] > MAX_JSON_INTEGER:
            _fail("budget", path, f"{dimension} aggregate exceeds exact range")
        if cumulative[dimension] > limits[dimension]:
            must_exhaust.add(dimension)
    del active[lease_id]
    closed.add(lease_id)


def _validate_exhaustion(
    event: dict[str, Any],
    *,
    limits: dict[str, int],
    cumulative: dict[str, int],
    observation: dict[str, int],
    active: dict[str, dict[str, Any]],
    must_exhaust: set[str],
    path: str,
) -> None:
    requested = event["requested"]
    if not _positive(requested):
        _fail("exhaustion", f"{path}.requested", "exhaustion needs a positive request")
    dimensions = event["dimensions"]
    _require_sorted_unique(dimensions, f"{path}.dimensions")
    reserved = _active_totals(active)
    effective = _effective_usage(cumulative, observation)
    unavailable = set(must_exhaust)
    for dimension in DIMENSIONS:
        if effective[dimension] + reserved[dimension] + requested[dimension] > limits[dimension]:
            unavailable.add(dimension)
    if set(dimensions) != unavailable:
        _fail("exhaustion", path, "exhausted dimensions do not match unavailable resources")


def _validate_truncation(event: dict[str, Any], limits: dict[str, int], path: str) -> None:
    dimension = event["dimension"]
    if dimension not in TRUNCATABLE_DIMENSIONS:
        _fail("truncation", f"{path}.dimension", "dimension is not truncatable")
    if event["original"] != event["retained"] + event["omitted"]:
        _fail("conservation", path, "truncation counts do not conserve original size")
    if event["omitted"] == 0:
        _fail("truncation", path, "truncation must omit a positive amount")
    if event["retained"] > limits[dimension]:
        _fail("truncation", path, "retained amount exceeds its declared limit")
    refused = event["strategy"] == "refuse"
    if refused != (event["retained"] == 0 and event["retained_sha256"] is None):
        _fail("truncation", path, "refuse must retain nothing; retained data needs a hash")
    if not refused and (event["retained"] == 0 or event["retained_sha256"] is None):
        _fail("truncation", path, "non-refusal truncation requires retained data and hash")


def _validate_outcome(
    outcome: dict[str, Any],
    *,
    active: dict[str, dict[str, Any]],
    cancellations: dict[str, dict[str, Any]],
    exhaustions: dict[str, dict[str, Any]],
    truncations: dict[str, dict[str, Any]],
    must_exhaust: set[str],
) -> None:
    status = outcome["status"]
    if status != "open" and active:
        _fail("outcome", "$.outcome", "terminal outcome has active child leases")
    if status == "open":
        if cancellations or exhaustions or must_exhaust:
            _fail("outcome", "$.outcome", "open budget has a terminal resource event")
    elif status == "completed":
        if cancellations or exhaustions or truncations or must_exhaust:
            _fail("outcome", "$.outcome", "ordinary completion hides a non-success state")
    elif status == "cancelled":
        if set(cancellations) != {outcome["cancellation_id"]} or exhaustions or must_exhaust:
            _fail("outcome", "$.outcome", "cancelled outcome does not bind its sole event")
    elif status == "exhausted":
        if set(exhaustions) != {outcome["exhaustion_id"]} or cancellations:
            _fail("outcome", "$.outcome", "exhausted outcome does not bind its sole event")
        dimensions = set(exhaustions[outcome["exhaustion_id"]]["dimensions"])
        if not must_exhaust <= dimensions:
            _fail("outcome", "$.outcome", "observed overrun is absent from exhaustion event")
    elif status == "truncated":
        expected = sorted(truncations)
        if outcome["truncation_ids"] != expected or cancellations or exhaustions or must_exhaust:
            _fail("outcome", "$.outcome", "truncated outcome does not bind all truncations")


def _validate_events(value: dict[str, Any]) -> None:
    limits = value["limits"]
    cumulative = zero_cumulative_vector()
    observation = zero_observation()
    active: dict[str, dict[str, Any]] = {}
    closed: set[str] = set()
    child_ids: set[str] = set()
    owners = {value["budget_id"]: "budget"}
    cancellations: dict[str, dict[str, Any]] = {}
    exhaustions: dict[str, dict[str, Any]] = {}
    truncations: dict[str, dict[str, Any]] = {}
    truncation_retained = {dimension: 0 for dimension in TRUNCATABLE_DIMENSIONS}
    must_exhaust: set[str] = set()
    terminal_sequence: int | None = None
    events = value["events"]
    if len(events) > MAX_EVENTS:
        _fail("budget", "$.events", "event count exceeds 100000")
    for sequence, event in enumerate(events):
        path = f"$.events[{sequence}]"
        if event["sequence"] != sequence:
            _fail("canonical", f"{path}.sequence", "event sequence must equal array index")
        if terminal_sequence is not None:
            _fail("outcome", path, f"event follows terminal event {terminal_sequence}")
        _claim(event["event_id"], owners, "event", f"{path}.event_id")
        kind = event["kind"]
        if must_exhaust and kind != "exhaust":
            _fail("exhaustion", path, "observed overrun requires immediate exhaustion")
        if kind == "charge":
            delta = event["delta"]
            if not _positive(delta):
                _fail("accounting", f"{path}.delta", "charge must consume a resource")
            reserved = _active_totals(active)
            for dimension in CUMULATIVE_DIMENSIONS:
                new_value = cumulative[dimension] + delta[dimension]
                if new_value + reserved[dimension] > limits[dimension]:
                    _fail("exhaustion", path, f"charge exceeds available {dimension}")
                cumulative[dimension] = new_value
        elif kind == "sample":
            _validate_sample(event, observation, path)
            must_exhaust.update(_observed_overruns(limits, observation))
        elif kind == "reserve":
            _validate_reserve(
                event,
                limits=limits,
                cumulative=cumulative,
                observation=observation,
                active=active,
                closed=closed,
                child_ids=child_ids,
                owners=owners,
                path=path,
            )
        elif kind == "reconcile":
            _validate_reconcile(
                event,
                limits=limits,
                cumulative=cumulative,
                observation=observation,
                active=active,
                closed=closed,
                must_exhaust=must_exhaust,
                path=path,
            )
        elif kind == "cancel":
            if active:
                _fail("cancellation", path, "children must reconcile before parent cancellation")
            identifier = event["cancellation_id"]
            _claim(identifier, owners, "cancellation", f"{path}.cancellation_id")
            if cancellations or exhaustions:
                _fail("cancellation", path, "budget already has a terminal resource event")
            if event["observed_wall_time_us"] != observation["wall_time_us"]:
                _fail("cancellation", path, "cancellation wall time is not the latest sample")
            cancellations[identifier] = event
            terminal_sequence = sequence
        elif kind == "exhaust":
            if active:
                _fail("exhaustion", path, "children must reconcile before parent exhaustion")
            identifier = event["exhaustion_id"]
            _claim(identifier, owners, "exhaustion", f"{path}.exhaustion_id")
            if cancellations or exhaustions:
                _fail("exhaustion", path, "budget already has a terminal resource event")
            _validate_exhaustion(
                event,
                limits=limits,
                cumulative=cumulative,
                observation=observation,
                active=active,
                must_exhaust=must_exhaust,
                path=path,
            )
            exhaustions[identifier] = event
            terminal_sequence = sequence
        elif kind == "truncate":
            identifier = event["truncation_id"]
            _claim(identifier, owners, "truncation", f"{path}.truncation_id")
            _validate_truncation(event, limits, path)
            truncations[identifier] = event
            dimension = event["dimension"]
            truncation_retained[dimension] += event["retained"]
            if truncation_retained[dimension] > MAX_JSON_INTEGER:
                _fail("budget", path, "retained truncation total exceeds exact range")
        else:  # The closed schema makes this unreachable.
            _fail("schema", path, f"unsupported event kind {kind!r}")
    for dimension, retained in truncation_retained.items():
        if retained > cumulative[dimension]:
            _fail("truncation", "$.events", f"retained {dimension} was not charged")
    _validate_outcome(
        value["outcome"],
        active=active,
        cancellations=cancellations,
        exhaustions=exhaustions,
        truncations=truncations,
        must_exhaust=must_exhaust,
    )


def validate_resource_budget(value: dict[str, Any], schema: dict[str, Any]) -> None:
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
    _validate_lineage(value)
    _validate_events(value)
    canonical_bytes(value)
    if time.monotonic() - started > MAX_VALIDATION_SECONDS:
        _fail("budget", "$", "validation exceeded 30 seconds")


def _limit_vector(**updates: int) -> dict[str, int]:
    value = {
        "wall_time_us": 1_000_000,
        "cpu_time_us": 800_000,
        "memory_bytes": 1_000_000,
        "solver_calls": 4,
        "generated_objects": 100,
        "proof_bytes": 10_000,
        "evidence_bytes": 10_000,
        "output_bytes": 10_000,
        "diagnostic_bytes": 10_000,
        "nesting_depth": 64,
    }
    value.update(updates)
    return value


def _usage(**updates: int) -> dict[str, int]:
    value = {
        "wall_time_us": 3_000,
        "cpu_time_us": 5_000,
        "memory_peak_bytes": 300,
        "memory_retained_bytes": 50,
        "solver_calls": 1,
        "generated_objects": 4,
        "proof_bytes": 20,
        "evidence_bytes": 30,
        "output_bytes": 40,
        "diagnostic_bytes": 10,
        "nesting_peak": 2,
    }
    value.update(updates)
    return value


def minimal_resource_budget() -> dict[str, Any]:
    allocation = _limit_vector(
        wall_time_us=10_000,
        cpu_time_us=10_000,
        memory_bytes=10_000,
        solver_calls=1,
        generated_objects=10,
        proof_bytes=100,
        evidence_bytes=100,
        output_bytes=100,
        diagnostic_bytes=100,
        nesting_depth=4,
    )
    child_usage = _usage()
    mapped = usage_as_limit_vector(child_usage)
    refund = {dimension: allocation[dimension] - mapped[dimension] for dimension in DIMENSIONS}
    value: dict[str, Any] = {
        "schema": "mathhead.resource-budget.v1",
        "budget_id": "budget_example",
        "lineage": {"kind": "root"},
        "policy": {
            "wall_clock": "monotonic_elapsed_us",
            "deadline": "relative_to_start",
            "cpu_accounting": "exclusive_budget_scope_us",
            "memory_accounting": "inclusive_active_process_tree_bytes",
            "integer_rounding": "ceil",
            "reservation": "conservative_all_dimensions",
        },
        "limits": _limit_vector(),
        "events": [
            {
                "event_id": "event_charge",
                "sequence": 0,
                "kind": "charge",
                "delta": {
                    "cpu_time_us": 100,
                    "solver_calls": 1,
                    "generated_objects": 5,
                    "proof_bytes": 0,
                    "evidence_bytes": 0,
                    "output_bytes": 20,
                    "diagnostic_bytes": 10,
                },
                "extensions": {},
            },
            {
                "event_id": "event_sample_before",
                "sequence": 1,
                "kind": "sample",
                "observation": {
                    "wall_time_us": 1_000,
                    "memory_retained_bytes": 100,
                    "memory_peak_bytes": 200,
                    "nesting_current": 1,
                    "nesting_peak": 2,
                },
                "extensions": {},
            },
            {
                "event_id": "event_reserve",
                "sequence": 2,
                "kind": "reserve",
                "lease_id": "lease_child",
                "child_budget_id": "budget_child",
                "allocation": allocation,
                "allocation_sha256": canonical_sha256(allocation),
                "extensions": {},
            },
            {
                "event_id": "event_sample_after",
                "sequence": 3,
                "kind": "sample",
                "observation": {
                    "wall_time_us": 5_000,
                    "memory_retained_bytes": 150,
                    "memory_peak_bytes": 500,
                    "nesting_current": 1,
                    "nesting_peak": 3,
                },
                "extensions": {},
            },
            {
                "event_id": "event_reconcile",
                "sequence": 4,
                "kind": "reconcile",
                "lease_id": "lease_child",
                "child_budget_sha256": "1" * 64,
                "child_outcome": "completed",
                "child_usage": child_usage,
                "refund": refund,
                "overrun": zero_limit_vector(),
                "extensions": {},
            },
        ],
        "outcome": {"status": "completed"},
        "extensions": {},
    }
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
            value = minimal_resource_budget()
        else:
            path = args.instance if args.instance.is_absolute() else root / args.instance
            value, _raw = load_json(path, require_canonical=True)
        validate_resource_budget(value, schema)
    except (ResourceBudgetValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"resource-budget-contract: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "resource-budget-contract: PASS "
        f"(schema={EXPECTED_SCHEMA_SHA256[:12]}, identity={canonical_sha256(value)[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
