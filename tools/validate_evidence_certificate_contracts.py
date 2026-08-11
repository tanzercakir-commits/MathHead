#!/usr/bin/env python3
"""Validate the accepted Evidence v1 and Certificate v1 contracts."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_CONTRACT_ID = "MH-C-EVIDENCE-001"
CERTIFICATE_CONTRACT_ID = "MH-C-CERTIFICATE-001"
EVIDENCE_CONTRACT_SHA256 = "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3"
CERTIFICATE_CONTRACT_SHA256 = "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740"
EVIDENCE_SCHEMA_PATH = Path("docs/contracts/schemas/evidence-v1.schema.json")
CERTIFICATE_SCHEMA_PATH = Path("docs/contracts/schemas/certificate-v1.schema.json")
EVIDENCE_SCHEMA_SHA256 = "4f1d0a4438812bdd7b204d0d0fe0098ff06cc274eb2e4ed7fa66a3f3a76b426f"
CERTIFICATE_SCHEMA_SHA256 = "cbc8f68469593e1d2b34588b49eaa16e37d597c863457945dd5b9ce5ae138760"
EVIDENCE_ROOT_FIELDS = {
    "schema",
    "evidence_id",
    "subject",
    "format",
    "producer",
    "payloads",
    "primary_payload_id",
    "dependencies",
    "generation",
    "budget",
    "outcome",
    "diagnostics",
    "extensions",
}
CERTIFICATE_ROOT_FIELDS = {
    "schema",
    "certificate_id",
    "subject",
    "format",
    "checker",
    "evidence",
    "replay",
    "verification_artifacts",
    "trust_dependencies",
    "verdict",
    "budget",
    "diagnostics",
    "extensions",
}
RESOURCE_OUTCOMES = {"cancelled", "exhausted", "truncated"}
TRUST_KINDS = {
    "checker_contract",
    "checker_implementation",
    "checker_configuration",
    "environment_contract",
    "problem_ir",
    "theory_context",
    "evidence",
}
MAX_VALIDATION_SECONDS = 30.0
MAX_INPUT_BYTES = 67_108_864
MAX_CANONICAL_NODES = 4_000_000
MAX_CANONICAL_NESTING = 64
MAX_STRING_CODEPOINTS = 1_048_576
MAX_JSON_INTEGER = 9_007_199_254_740_991
MAX_ENTITIES = 100_000


class EvidenceCertificateValidationError(RuntimeError):
    """A classified schema, identity, reference, replay, or trust failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise EvidenceCertificateValidationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _example_sha(label: str) -> str:
    return _sha(label.encode("utf-8"))


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
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            _fail("budget", str(path), "JSON input exceeds 67108864 bytes")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs(path))
    except EvidenceCertificateValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical JSON")
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
            except EvidenceCertificateValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail("schema", path, f"must match exactly one tagged variant, matched {matches}")
        return
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except EvidenceCertificateValidationError:
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
            _fail("budget", path, "JSON integer exceeds portable exact range")
        if isinstance(item, list):
            stack.extend((child, depth + 1, f"{path}[{index}]") for index, child in enumerate(item))
        elif isinstance(item, dict):
            stack.extend((child, depth + 1, f"{path}.{key}") for key, child in item.items())


def _canonical_prelude(
    value: dict[str, Any], schema: dict[str, Any], root_fields: set[str]
) -> None:
    started = time.monotonic()
    _shape_budget(value, started)
    _schema_validate(value, schema, schema)
    if set(value) != root_fields:
        _fail("schema", "$", "root field set drift")
    for path, text in _walk_strings(value):
        if "\x00" in text:
            _fail("canonical", path, "NUL is forbidden")
        if unicodedata.normalize("NFC", text) != text:
            _fail("canonical", path, "string is not Unicode NFC")


def _require_sorted_unique(values: list[str], path: str) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        _fail("canonical", path, "values must be sorted and unique")


def _require_unique_ids(items: list[dict[str, Any]], key: str, path: str) -> list[str]:
    identifiers = [item[key] for item in items]
    _require_sorted_unique(identifiers, path)
    return identifiers


def _version_parts(format_value: dict[str, Any], path: str) -> tuple[int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.", format_value["version"])
    if match is None:
        _fail("compatibility", f"{path}.version", "version is not semantic")
    major, minor = int(match.group(1)), int(match.group(2))
    if major != format_value["major"] or minor != format_value["minor"]:
        _fail("compatibility", path, "semantic version and numeric compatibility fields disagree")
    if major != 1 or format_value["reader_minimum_minor"] > minor:
        _fail("compatibility", path, "unsupported major or impossible reader minimum")
    _require_sorted_unique(format_value["features"], f"{path}.features")
    return major, minor


def evidence_generation_basis_sha256(value: dict[str, Any]) -> str:
    generation = {
        key: item for key, item in value["generation"].items() if key != "basis_sha256"
    }
    basis = {
        "evidence_id": value["evidence_id"],
        "subject": value["subject"],
        "format": value["format"],
        "producer": value["producer"],
        "dependencies": value["dependencies"],
        "generation": generation,
    }
    return canonical_sha256(basis)


def certificate_replay_basis_sha256(value: dict[str, Any]) -> str:
    replay = {key: item for key, item in value["replay"].items() if key != "basis_sha256"}
    basis = {
        "certificate_id": value["certificate_id"],
        "subject": value["subject"],
        "format": value["format"],
        "checker": value["checker"],
        "evidence": value["evidence"],
        "replay": replay,
    }
    return canonical_sha256(basis)


def _validate_dependency_graph(value: dict[str, Any]) -> None:
    dependencies = value["dependencies"]
    identifiers = _require_unique_ids(dependencies, "evidence_id", "$.dependencies")
    if value["evidence_id"] in identifiers:
        _fail("dependency", "$.dependencies", "evidence cannot depend on itself")
    hashes = [item["evidence_sha256"] for item in dependencies]
    if len(hashes) != len(set(hashes)):
        _fail("dependency", "$.dependencies", "dependency content identity repeats")
    known = set(identifiers)
    graph: dict[str, list[str]] = {}
    for index, item in enumerate(dependencies):
        path = f"$.dependencies[{index}].depends_on_evidence_ids"
        edges = item["depends_on_evidence_ids"]
        _require_sorted_unique(edges, path)
        if item["evidence_id"] in edges or not set(edges) <= known:
            _fail("dependency", path, "dependency edge is self-referential or unresolved")
        graph[item["evidence_id"]] = edges

    state: dict[str, int] = {}

    def visit(identifier: str) -> None:
        if state.get(identifier) == 1:
            _fail("dependency", "$.dependencies", "dependency graph contains a cycle")
        if state.get(identifier) == 2:
            return
        state[identifier] = 1
        for target in graph[identifier]:
            visit(target)
        state[identifier] = 2

    for identifier in identifiers:
        visit(identifier)


def _validate_evidence_diagnostics(
    value: dict[str, Any], payloads: dict[str, dict[str, Any]]
) -> None:
    diagnostics = value["diagnostics"]
    ids = _require_unique_ids(diagnostics, "diagnostic_id", "$.diagnostics")
    for index, diagnostic in enumerate(diagnostics):
        related = diagnostic["related_payload_ids"]
        _require_sorted_unique(related, f"$.diagnostics[{index}].related_payload_ids")
        if not set(related) <= set(payloads):
            _fail("reference", f"$.diagnostics[{index}]", "unknown related payload")
    outcome = value["outcome"]
    _require_sorted_unique(outcome["diagnostic_ids"], "$.outcome.diagnostic_ids")
    if outcome["diagnostic_ids"] != ids:
        _fail("diagnostic", "$.outcome.diagnostic_ids", "outcome must bind every diagnostic")
    if outcome["status"] != "produced" and not diagnostics:
        _fail("diagnostic", "$.diagnostics", "non-produced outcome requires a diagnostic")
    if outcome["status"] == "error" and not any(
        item["severity"] == "error" for item in diagnostics
    ):
        _fail("diagnostic", "$.diagnostics", "error outcome requires error severity")
    if outcome["status"] == "produced" and any(
        item["severity"] == "error" for item in diagnostics
    ):
        _fail("outcome", "$.diagnostics", "produced evidence cannot hide an error")


def validate_evidence(value: dict[str, Any], schema: dict[str, Any]) -> None:
    _canonical_prelude(value, schema, EVIDENCE_ROOT_FIELDS)
    entity_count = len(value["payloads"]) + len(value["dependencies"]) + len(
        value["diagnostics"]
    )
    if entity_count > MAX_ENTITIES:
        _fail("budget", "$", "evidence entities exceed 100000")
    subject = value["subject"]
    _require_sorted_unique(subject["assumption_sha256s"], "$.subject.assumption_sha256s")
    _require_sorted_unique(subject["obligation_sha256s"], "$.subject.obligation_sha256s")
    _version_parts(value["format"], "$.format")
    generation = value["generation"]
    if (generation["mode"] == "deterministic") != (generation["seed"] is None):
        _fail("replay", "$.generation.seed", "deterministic has no seed; seeded requires one")
    if generation["configuration_sha256"] != value["producer"]["configuration_sha256"]:
        _fail("replay", "$.generation.configuration_sha256", "producer configuration mismatch")
    if generation["input_sha256"] != canonical_sha256(subject):
        _fail("replay", "$.generation.input_sha256", "subject input identity mismatch")
    if generation["basis_sha256"] != evidence_generation_basis_sha256(value):
        _fail("replay", "$.generation.basis_sha256", "generation basis identity mismatch")

    payload_ids = _require_unique_ids(value["payloads"], "payload_id", "$.payloads")
    payloads = {item["payload_id"]: item for item in value["payloads"]}
    content = [(item["role"], item["sha256"]) for item in value["payloads"]]
    if len(content) != len(set(content)):
        _fail("identity", "$.payloads", "payload role and content identity repeats")
    primary = value["primary_payload_id"]
    primary_items = [item for item in value["payloads"] if item["role"] == "primary"]
    if primary is None:
        if primary_items:
            _fail("reference", "$.primary_payload_id", "primary payload is not bound")
    elif (
        primary not in payloads
        or payloads[primary]["role"] != "primary"
        or len(primary_items) != 1
        or payloads[primary]["byte_count"] == 0
    ):
        _fail("reference", "$.primary_payload_id", "one nonempty primary payload is required")
    _validate_dependency_graph(value)

    outcome = value["outcome"]
    status = outcome["status"]
    if status == "produced":
        _require_sorted_unique(outcome["payload_ids"], "$.outcome.payload_ids")
        if outcome["payload_ids"] != payload_ids or primary is None:
            _fail("outcome", "$.outcome.payload_ids", "produced outcome binds every payload")
    elif status == "unsupported":
        _require_sorted_unique(outcome["unsupported_features"], "$.outcome.unsupported_features")
    elif status == "exhausted":
        _require_sorted_unique(outcome["dimensions"], "$.outcome.dimensions")
    elif status == "truncated":
        _require_sorted_unique(outcome["truncation_ids"], "$.outcome.truncation_ids")
        _require_sorted_unique(
            outcome["retained_payload_ids"], "$.outcome.retained_payload_ids"
        )
        if not set(outcome["retained_payload_ids"]) <= set(payloads):
            _fail("reference", "$.outcome.retained_payload_ids", "unknown retained payload")
    budget_outcome = value["budget"]["outcome"]
    if status in RESOURCE_OUTCOMES:
        if budget_outcome != status:
            _fail("outcome", "$.budget.outcome", "terminal resource outcome mismatch")
    elif budget_outcome != "completed":
        _fail("outcome", "$.budget.outcome", "non-resource outcome hides terminal budget")
    _validate_evidence_diagnostics(value, payloads)

    owners = {
        value["evidence_id"],
        value["producer"]["component_id"],
        *payload_ids,
        *(item["evidence_id"] for item in value["dependencies"]),
        *(item["diagnostic_id"] for item in value["diagnostics"]),
    }
    expected = 2 + len(value["payloads"]) + len(value["dependencies"]) + len(
        value["diagnostics"]
    )
    if len(owners) != expected:
        _fail("identity", "$", "evidence namespace contains an ID collision")
def _evidence_primary(value: dict[str, Any]) -> dict[str, Any]:
    primary = value["primary_payload_id"]
    for payload in value["payloads"]:
        if payload["payload_id"] == primary:
            return payload
    _fail("reference", "$.primary_payload_id", "primary payload is unresolved")


def _validate_certificate_evidence(
    value: dict[str, Any], evidence: dict[str, Any] | None
) -> None:
    reference = value["evidence"]
    _require_sorted_unique(reference["format_features"], "$.evidence.format_features")
    _require_sorted_unique(reference["dependency_sha256s"], "$.evidence.dependency_sha256s")
    checker = value["checker"]
    producer = reference["producer"]
    if checker["component_id"] == producer["component_id"]:
        _fail("epistemic", "$.checker", "producer cannot check its own evidence")
    if (
        checker["contract_sha256"] == producer["contract_sha256"]
        and checker["implementation_sha256"] == producer["implementation_sha256"]
    ):
        _fail("epistemic", "$.checker", "checker is not independent from producer")
    if evidence is None:
        if value["verdict"]["status"] == "verified":
            _fail("reference", "$.evidence", "verified verdict requires independently loaded bytes")
        return
    if reference["evidence_sha256"] != canonical_sha256(evidence):
        _fail("reference", "$.evidence.evidence_sha256", "Evidence canonical bytes mismatch")
    if reference["evidence_id"] != evidence["evidence_id"]:
        _fail("reference", "$.evidence.evidence_id", "Evidence logical identity mismatch")
    if value["subject"] != evidence["subject"]:
        _fail("reference", "$.subject", "certificate subject does not equal Evidence subject")
    primary = _evidence_primary(evidence)
    expected = {
        "schema": evidence["schema"],
        "evidence_id": evidence["evidence_id"],
        "evidence_sha256": canonical_sha256(evidence),
        "primary_payload_sha256": primary["sha256"],
        "format_id": evidence["format"]["format_id"],
        "format_version": evidence["format"]["version"],
        "format_features": evidence["format"]["features"],
        "dependency_sha256s": sorted(
            item["evidence_sha256"] for item in evidence["dependencies"]
        ),
        "producer": {
            key: evidence["producer"][key]
            for key in (
                "component_id",
                "role",
                "contract_sha256",
                "implementation_sha256",
                "configuration_sha256",
            )
        },
    }
    if reference != expected:
        _fail("reference", "$.evidence", "Evidence header binding mismatch")


def _validate_trust(value: dict[str, Any]) -> None:
    dependencies = value["trust_dependencies"]
    order = [(item["kind"], item["identifier"]) for item in dependencies]
    if order != sorted(order) or len(order) != len(set(order)):
        _fail("canonical", "$.trust_dependencies", "trust dependencies must sort and deduplicate")
    if value["verdict"]["status"] != "verified":
        return
    by_kind = {item["kind"]: item for item in dependencies}
    if set(by_kind) != TRUST_KINDS or len(dependencies) != len(TRUST_KINDS):
        _fail("epistemic", "$.trust_dependencies", "verified verdict needs exact trust closure")
    checker = value["checker"]
    expected = {
        "checker_contract": checker["contract_sha256"],
        "checker_implementation": checker["implementation_sha256"],
        "checker_configuration": checker["configuration_sha256"],
        "environment_contract": checker["environment_contract_sha256"],
        "problem_ir": value["subject"]["problem_ir_sha256"],
        "theory_context": value["subject"]["theory_context_sha256"],
        "evidence": value["evidence"]["evidence_sha256"],
    }
    for kind, sha256 in expected.items():
        if by_kind[kind]["sha256"] != sha256:
            _fail("epistemic", "$.trust_dependencies", f"{kind} identity mismatch")


def _validate_certificate_diagnostics(
    value: dict[str, Any], artifacts: dict[str, dict[str, Any]]
) -> None:
    diagnostics = value["diagnostics"]
    ids = _require_unique_ids(diagnostics, "diagnostic_id", "$.diagnostics")
    for index, diagnostic in enumerate(diagnostics):
        related = diagnostic["related_artifact_ids"]
        _require_sorted_unique(related, f"$.diagnostics[{index}].related_artifact_ids")
        if not set(related) <= set(artifacts):
            _fail("reference", f"$.diagnostics[{index}]", "unknown related artifact")
    verdict = value["verdict"]
    _require_sorted_unique(verdict["diagnostic_ids"], "$.verdict.diagnostic_ids")
    if verdict["diagnostic_ids"] != ids:
        _fail("diagnostic", "$.verdict.diagnostic_ids", "verdict must bind every diagnostic")
    status = verdict["status"]
    if status != "verified" and not diagnostics:
        _fail("diagnostic", "$.diagnostics", "non-verified verdict requires a diagnostic")
    if status in {"verifier_failed", "disagreement"} and not any(
        item["severity"] == "error" for item in diagnostics
    ):
        _fail("diagnostic", "$.diagnostics", "failure verdict requires error severity")
    if status == "verified" and diagnostics:
        _fail("diagnostic", "$.diagnostics", "verified certificate must be diagnostic-free")


def validate_certificate(
    value: dict[str, Any],
    schema: dict[str, Any],
    *,
    evidence: dict[str, Any] | None = None,
    evidence_schema: dict[str, Any] | None = None,
) -> None:
    _canonical_prelude(value, schema, CERTIFICATE_ROOT_FIELDS)
    entity_count = len(value["verification_artifacts"]) + len(
        value["trust_dependencies"]
    ) + len(value["diagnostics"])
    if entity_count > MAX_ENTITIES:
        _fail("budget", "$", "certificate entities exceed 100000")
    subject = value["subject"]
    _require_sorted_unique(subject["assumption_sha256s"], "$.subject.assumption_sha256s")
    _require_sorted_unique(subject["obligation_sha256s"], "$.subject.obligation_sha256s")
    _version_parts(value["format"], "$.format")
    if evidence is not None:
        if evidence_schema is None:
            _fail("reference", "$.evidence", "Evidence schema is required with loaded bytes")
        validate_evidence(evidence, evidence_schema)
    _validate_certificate_evidence(value, evidence)

    replay = value["replay"]
    if (replay["mode"] == "deterministic") != (replay["seed"] is None):
        _fail("replay", "$.replay.seed", "deterministic has no seed; seeded requires one")
    if replay["configuration_sha256"] != value["checker"]["configuration_sha256"]:
        _fail("replay", "$.replay.configuration_sha256", "checker configuration mismatch")
    if replay["input_evidence_sha256"] != value["evidence"]["evidence_sha256"]:
        _fail("replay", "$.replay.input_evidence_sha256", "Evidence replay input mismatch")
    if replay["expected_payload_sha256"] != value["evidence"]["primary_payload_sha256"]:
        _fail("replay", "$.replay.expected_payload_sha256", "expected payload mismatch")
    if replay["basis_sha256"] != certificate_replay_basis_sha256(value):
        _fail("replay", "$.replay.basis_sha256", "certificate replay basis mismatch")

    artifact_ids = _require_unique_ids(
        value["verification_artifacts"], "artifact_id", "$.verification_artifacts"
    )
    artifacts = {item["artifact_id"]: item for item in value["verification_artifacts"]}
    checker_id = value["checker"]["component_id"]
    identities: set[tuple[str, str]] = set()
    for index, artifact in enumerate(value["verification_artifacts"]):
        if artifact["producer_component_id"] != checker_id:
            _fail("epistemic", f"$.verification_artifacts[{index}]", "checker did not produce artifact")
        identity = (artifact["kind"], artifact["sha256"])
        if identity in identities:
            _fail("identity", "$.verification_artifacts", "artifact kind and content repeat")
        identities.add(identity)

    verdict = value["verdict"]
    status = verdict["status"]
    if status == "verified":
        expected_authority = (
            "checker_attested" if value["checker"]["role"] == "checker" else "external_verified"
        )
        if verdict["authority"] != expected_authority:
            _fail("epistemic", "$.verdict.authority", "authority does not match checker role")
        result_id = verdict["checker_result_artifact_id"]
        if result_id not in artifacts or artifacts[result_id]["kind"] != "checker_result":
            _fail("artifact", "$.verdict.checker_result_artifact_id", "checker result is required")
        support = verdict["supporting_artifact_ids"]
        _require_sorted_unique(support, "$.verdict.supporting_artifact_ids")
        if not set(support) <= set(artifacts) or result_id not in support:
            _fail("artifact", "$.verdict.supporting_artifact_ids", "support is unresolved")
        if not any(artifacts[item]["kind"] == "replay_log" for item in support):
            _fail("artifact", "$.verdict.supporting_artifact_ids", "replay log is required")
        if replay["observed_payload_sha256"] != replay["expected_payload_sha256"]:
            _fail("replay", "$.replay.observed_payload_sha256", "verified replay did not match")
    elif status == "invalid":
        result_id = verdict["checker_result_artifact_id"]
        if result_id not in artifacts or artifacts[result_id]["kind"] != "checker_result":
            _fail("artifact", "$.verdict.checker_result_artifact_id", "invalid verdict needs result")
        if verdict["reason_code"] == "replay_mismatch" and (
            replay["observed_payload_sha256"] is None
            or replay["observed_payload_sha256"] == replay["expected_payload_sha256"]
        ):
            _fail("replay", "$.replay.observed_payload_sha256", "replay mismatch is not observed")
    elif status == "unsupported":
        _require_sorted_unique(verdict["unsupported_features"], "$.verdict.unsupported_features")
    elif status == "exhausted":
        _require_sorted_unique(verdict["dimensions"], "$.verdict.dimensions")
    elif status == "truncated":
        _require_sorted_unique(verdict["truncation_ids"], "$.verdict.truncation_ids")
    elif status == "disagreement":
        conflicts = verdict["conflicting_artifact_ids"]
        _require_sorted_unique(conflicts, "$.verdict.conflicting_artifact_ids")
        if not set(conflicts) <= set(artifacts):
            _fail("reference", "$.verdict.conflicting_artifact_ids", "conflict is unresolved")

    _validate_trust(value)
    budget_outcome = value["budget"]["outcome"]
    if status in RESOURCE_OUTCOMES:
        if budget_outcome != status:
            _fail("outcome", "$.budget.outcome", "terminal resource verdict mismatch")
    elif budget_outcome != "completed":
        _fail("outcome", "$.budget.outcome", "verdict hides terminal resource outcome")
    _validate_certificate_diagnostics(value, artifacts)
    owners = {
        value["certificate_id"],
        value["checker"]["component_id"],
        value["replay"]["attempt_id"],
        *artifact_ids,
        *(item["diagnostic_id"] for item in value["diagnostics"]),
    }
    expected = 3 + len(value["verification_artifacts"]) + len(value["diagnostics"])
    if len(owners) != expected:
        _fail("identity", "$", "certificate namespace contains an ID collision")


def minimal_evidence() -> dict[str, Any]:
    subject = {
        "kind": "goal",
        "subject_id": "goal_main",
        "statement_sha256": _example_sha("statement"),
        "problem_ir_sha256": _example_sha("problem-ir"),
        "theory_context_sha256": _example_sha("theory-context"),
        "reading_id": "reading_primary",
        "assumption_sha256s": [],
        "obligation_sha256s": [],
    }
    value: dict[str, Any] = {
        "schema": "mathhead.evidence.v1",
        "evidence_id": "evidence_example",
        "subject": subject,
        "format": {
            "kind": "proof",
            "format_id": "org.mathhead.proof",
            "version": "1.0.0",
            "major": 1,
            "minor": 0,
            "reader_minimum_minor": 0,
            "schema_sha256": _example_sha("proof-schema"),
            "canonicalization": "org.mathhead.canonical-json",
            "features": [],
        },
        "producer": {
            "component_id": "component_producer",
            "role": "solver",
            "name": "org.mathhead.solver",
            "version": "1.0.0",
            "contract_id": "MH-C-SOLVER-001",
            "contract_sha256": _example_sha("solver-contract"),
            "implementation_sha256": _example_sha("solver-implementation"),
            "configuration_sha256": _example_sha("solver-configuration"),
            "environment_contract_sha256": _example_sha("environment-contract"),
        },
        "payloads": [
            {
                "payload_id": "payload_proof",
                "role": "primary",
                "media_type": "application/json",
                "sha256": _example_sha("proof-payload"),
                "byte_count": 128,
                "encoding": "utf-8",
                "compression": "none",
                "extensions": {},
            }
        ],
        "primary_payload_id": "payload_proof",
        "dependencies": [],
        "generation": {
            "mode": "deterministic",
            "seed": None,
            "algorithm_id": "org.mathhead.generate-proof",
            "configuration_sha256": _example_sha("solver-configuration"),
            "input_sha256": canonical_sha256(subject),
            "basis_sha256": "0" * 64,
        },
        "budget": {
            "initial_sha256": _example_sha("initial-budget"),
            "final_sha256": _example_sha("final-budget"),
            "outcome": "completed",
        },
        "outcome": {
            "status": "produced",
            "payload_ids": ["payload_proof"],
            "diagnostic_ids": [],
        },
        "diagnostics": [],
        "extensions": {},
    }
    value["generation"]["basis_sha256"] = evidence_generation_basis_sha256(value)
    return value


def minimal_certificate(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = copy.deepcopy(evidence or minimal_evidence())
    primary = _evidence_primary(evidence)
    checker = {
        "component_id": "component_checker",
        "role": "checker",
        "name": "org.mathhead.checker",
        "version": "1.0.0",
        "contract_id": "MH-C-CHECKER-001",
        "contract_sha256": _example_sha("checker-contract"),
        "implementation_sha256": _example_sha("checker-implementation"),
        "configuration_sha256": _example_sha("checker-configuration"),
        "environment_contract_sha256": _example_sha("checker-environment"),
    }
    evidence_ref = {
        "schema": evidence["schema"],
        "evidence_id": evidence["evidence_id"],
        "evidence_sha256": canonical_sha256(evidence),
        "primary_payload_sha256": primary["sha256"],
        "format_id": evidence["format"]["format_id"],
        "format_version": evidence["format"]["version"],
        "format_features": evidence["format"]["features"],
        "dependency_sha256s": sorted(
            item["evidence_sha256"] for item in evidence["dependencies"]
        ),
        "producer": {
            key: evidence["producer"][key]
            for key in (
                "component_id",
                "role",
                "contract_sha256",
                "implementation_sha256",
                "configuration_sha256",
            )
        },
    }
    value: dict[str, Any] = {
        "schema": "mathhead.certificate.v1",
        "certificate_id": "certificate_example",
        "subject": copy.deepcopy(evidence["subject"]),
        "format": {
            "format_id": "org.mathhead.certificate",
            "version": "1.0.0",
            "major": 1,
            "minor": 0,
            "reader_minimum_minor": 0,
            "schema_sha256": _example_sha("certificate-schema"),
            "canonicalization": "org.mathhead.canonical-json",
            "features": [],
        },
        "checker": checker,
        "evidence": evidence_ref,
        "replay": {
            "attempt_id": "attempt_checker",
            "mode": "deterministic",
            "seed": None,
            "algorithm_id": "org.mathhead.check-proof",
            "configuration_sha256": checker["configuration_sha256"],
            "input_evidence_sha256": evidence_ref["evidence_sha256"],
            "expected_payload_sha256": evidence_ref["primary_payload_sha256"],
            "observed_payload_sha256": evidence_ref["primary_payload_sha256"],
            "basis_sha256": "0" * 64,
        },
        "verification_artifacts": [
            {
                "artifact_id": "artifact_checker_result",
                "kind": "checker_result",
                "sha256": _example_sha("checker-result"),
                "byte_count": 64,
                "producer_component_id": checker["component_id"],
                "extensions": {},
            },
            {
                "artifact_id": "artifact_replay_log",
                "kind": "replay_log",
                "sha256": _example_sha("replay-log"),
                "byte_count": 64,
                "producer_component_id": checker["component_id"],
                "extensions": {},
            },
        ],
        "trust_dependencies": [],
        "verdict": {
            "status": "verified",
            "authority": "checker_attested",
            "checker_result_artifact_id": "artifact_checker_result",
            "supporting_artifact_ids": ["artifact_checker_result", "artifact_replay_log"],
            "diagnostic_ids": [],
        },
        "budget": {
            "initial_sha256": _example_sha("checker-initial-budget"),
            "final_sha256": _example_sha("checker-final-budget"),
            "outcome": "completed",
        },
        "diagnostics": [],
        "extensions": {},
    }
    trust = {
        "checker_contract": (checker["contract_id"], checker["contract_sha256"]),
        "checker_implementation": (
            checker["component_id"],
            checker["implementation_sha256"],
        ),
        "checker_configuration": (
            checker["component_id"],
            checker["configuration_sha256"],
        ),
        "environment_contract": (
            "MH-C-ENV-002",
            checker["environment_contract_sha256"],
        ),
        "problem_ir": ("ProblemIR", value["subject"]["problem_ir_sha256"]),
        "theory_context": ("TheoryContext", value["subject"]["theory_context_sha256"]),
        "evidence": (evidence["evidence_id"], evidence_ref["evidence_sha256"]),
    }
    value["trust_dependencies"] = [
        {"kind": kind, "identifier": identifier, "sha256": sha256}
        for kind, (identifier, sha256) in sorted(trust.items())
    ]
    value["replay"]["basis_sha256"] = certificate_replay_basis_sha256(value)
    return value


def _load_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    evidence_schema, evidence_raw = load_json(ROOT / EVIDENCE_SCHEMA_PATH)
    certificate_schema, certificate_raw = load_json(ROOT / CERTIFICATE_SCHEMA_PATH)
    if _sha(evidence_raw) != EVIDENCE_SCHEMA_SHA256:
        _fail("schema-document", str(EVIDENCE_SCHEMA_PATH), "Evidence schema hash mismatch")
    if _sha(certificate_raw) != CERTIFICATE_SCHEMA_SHA256:
        _fail("schema-document", str(CERTIFICATE_SCHEMA_PATH), "Certificate schema hash mismatch")
    return evidence_schema, certificate_schema


def _verify_contract_artifacts() -> None:
    expected = {
        EVIDENCE_CONTRACT_ID: EVIDENCE_CONTRACT_SHA256,
        CERTIFICATE_CONTRACT_ID: CERTIFICATE_CONTRACT_SHA256,
    }
    for contract_id, expected_sha256 in expected.items():
        accepted_path = ROOT / f"docs/contracts/{contract_id}.json"
        proposed_path = ROOT / f"docs/contracts/proposed/{contract_id}.json"
        accepted, accepted_raw = load_json(accepted_path, require_canonical=True)
        proposed, proposed_raw = load_json(proposed_path, require_canonical=True)
        if accepted["contract_id"] != contract_id or proposed["contract_id"] != contract_id:
            _fail("contract", str(accepted_path), "contract logical identity mismatch")
        if accepted_raw != proposed_raw or _sha(accepted_raw) != expected_sha256:
            _fail("contract", str(accepted_path), "accepted/proposed contract binding mismatch")
    certificate, _ = load_json(
        ROOT / f"docs/contracts/{CERTIFICATE_CONTRACT_ID}.json", require_canonical=True
    )
    if not any(EVIDENCE_CONTRACT_SHA256 in requirement for requirement in certificate["requires"]):
        _fail("contract", CERTIFICATE_CONTRACT_ID, "Certificate omits accepted Evidence hash")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--certificate", type=Path)
    args = parser.parse_args(argv)
    try:
        _verify_contract_artifacts()
        evidence_schema, certificate_schema = _load_schemas()
        evidence = minimal_evidence()
        if args.evidence:
            evidence, _ = load_json(args.evidence, require_canonical=True)
        validate_evidence(evidence, evidence_schema)
        certificate = minimal_certificate(evidence)
        if args.certificate:
            certificate, _ = load_json(args.certificate, require_canonical=True)
        validate_certificate(
            certificate,
            certificate_schema,
            evidence=evidence,
            evidence_schema=evidence_schema,
        )
    except EvidenceCertificateValidationError as exc:
        print(f"evidence-certificate-contracts: FAIL [{exc.kind}] {exc}", file=sys.stderr)
        return 1
    print(
        "evidence-certificate-contracts: PASS "
        f"(evidence={canonical_sha256(evidence)[:12]}, "
        f"certificate={canonical_sha256(certificate)[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
