#!/usr/bin/env python3
"""Independently validate the accepted TheoryPlugin v1 descriptor contract."""

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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_evidence_certificate_contracts as common  # noqa: E402


CONTRACT_ID = "MH-C-THEORY-PLUGIN-001"
EXPECTED_CONTRACT_SHA256 = "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8"
SCHEMA_PATH = Path("docs/contracts/schemas/theory-plugin-v1.schema.json")
EXPECTED_SCHEMA_SHA256 = "c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142"
ROOT_FIELDS = {
    "schema",
    "plugin_id",
    "display_name",
    "plugin_version",
    "api",
    "implementation",
    "components",
    "compatibility",
    "capabilities",
    "operations",
    "lifecycle",
    "effects",
    "replay",
    "limits",
    "extensions",
}
EXPECTED_CONTRACTS = {
    "MH-C-CERTIFICATE-001": (
        "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
        "mathhead.certificate.v1",
    ),
    "MH-C-ENGINE-RESULT-001": (
        "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
        "mathhead.engine-result.v1",
    ),
    "MH-C-EVIDENCE-001": (
        "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
        "mathhead.evidence.v1",
    ),
    "MH-C-PROBLEM-IR-002": (
        "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
        "mathhead.problem-ir.v1",
    ),
    "MH-C-RESOURCE-BUDGET-001": (
        "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
        "mathhead.resource-budget.v1",
    ),
    "MH-C-THEORY-CONTEXT-001": (
        "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
        "mathhead.theory-context.v1",
    ),
}
OPERATION_ORDER = ["plan_cost", "solve", "check", "explain"]
EFFECT_KINDS = ["environment", "filesystem", "network", "process", "solver"]
MAX_VALIDATION_SECONDS = 30.0
MAX_INPUT_BYTES = 67_108_864
MAX_CANONICAL_NODES = 4_000_000
MAX_CANONICAL_NESTING = 64
MAX_STRING_CODEPOINTS = 1_048_576
MAX_JSON_INTEGER = 9_007_199_254_740_991
MAX_ENTITIES = 100_000
EXPECTED_LIMITS = {
    "input_bytes": MAX_INPUT_BYTES,
    "canonical_nodes": MAX_CANONICAL_NODES,
    "canonical_nesting": MAX_CANONICAL_NESTING,
    "entities": MAX_ENTITIES,
    "items_per_array": 100_000,
    "string_codepoints": MAX_STRING_CODEPOINTS,
    "validation_seconds": 30,
    "memory_mb": 512,
}


class TheoryPluginValidationError(RuntimeError):
    """A classified descriptor, compatibility, routing, or replay failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise TheoryPluginValidationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _example_sha(label: str) -> str:
    return _sha(label.encode("utf-8"))


def canonical_bytes(value: Any) -> bytes:
    try:
        return common.canonical_bytes(value)
    except common.EvidenceCertificateValidationError as exc:
        _fail(exc.kind, exc.path, exc.detail)


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
    except TheoryPluginValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical TheoryPlugin JSON")
    return value, raw


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


def _schema_validate(value: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        common._schema_validate(value, schema, schema)  # noqa: SLF001
    except common.EvidenceCertificateValidationError as exc:
        _fail(exc.kind, exc.path, exc.detail)


def _require_sorted_unique(values: list[str], path: str) -> None:
    if values != sorted(values) or len(values) != len(set(values)):
        _fail("canonical", path, "values must be sorted and unique")


def _semver(value: str, path: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", value)
    if match is None:
        _fail("compatibility", path, "version is not semantic")
    return tuple(int(item) for item in match.groups())


def descriptor_basis_sha256(value: dict[str, Any]) -> str:
    replay = {
        key: item
        for key, item in value["replay"].items()
        if key != "descriptor_basis_sha256"
    }
    basis = {key: item for key, item in value.items() if key != "replay"}
    basis["replay"] = replay
    return canonical_sha256(basis)


def _validate_api_and_implementation(value: dict[str, Any]) -> None:
    api = value["api"]
    major, minor, _ = _semver(api["version"], "$.api.version")
    if major != api["major"] or minor != api["minor"] or major != 1:
        _fail("compatibility", "$.api", "API semantic and numeric versions disagree")
    if api["reader_minimum_minor"] > minor:
        _fail("compatibility", "$.api.reader_minimum_minor", "reader minimum exceeds minor")
    if api["contract_sha256"] != EXPECTED_CONTRACT_SHA256:
        _fail("contract", "$.api.contract_sha256", "TheoryPlugin contract identity mismatch")
    implementation = value["implementation"]
    if implementation["package_version"] != value["plugin_version"]:
        _fail("compatibility", "$.implementation.package_version", "plugin version mismatch")
    if value["replay"]["configuration_sha256"] != implementation["configuration_sha256"]:
        _fail("replay", "$.replay.configuration_sha256", "implementation configuration mismatch")


def _validate_components(value: dict[str, Any]) -> None:
    producer = value["components"]["producer"]
    checker = value["components"]["checker"]
    if producer["role"] != "producer" or checker["role"] != "checker":
        _fail("epistemic", "$.components", "producer and checker roles are exact")
    if producer["component_id"] == checker["component_id"]:
        _fail("epistemic", "$.components", "producer and checker IDs must differ")
    if (
        producer["contract_sha256"] == checker["contract_sha256"]
        and producer["implementation_sha256"] == checker["implementation_sha256"]
    ):
        _fail("epistemic", "$.components", "checker cannot alias producer implementation")
    if producer["implementation_sha256"] != value["implementation"]["implementation_sha256"]:
        _fail("provenance", "$.components.producer", "root implementation is not producer")
    if producer["configuration_sha256"] != value["implementation"]["configuration_sha256"]:
        _fail("provenance", "$.components.producer", "root configuration is not producer")
    if producer["version"] != value["plugin_version"] or checker["version"] != value[
        "plugin_version"
    ]:
        _fail("compatibility", "$.components", "component versions must equal plugin version")


def _validate_compatibility(value: dict[str, Any]) -> None:
    compatibility = value["compatibility"]
    contracts = compatibility["contracts"]
    identifiers = [item["contract_id"] for item in contracts]
    _require_sorted_unique(identifiers, "$.compatibility.contracts")
    if set(identifiers) != set(EXPECTED_CONTRACTS):
        _fail("compatibility", "$.compatibility.contracts", "foundational contract set is incomplete")
    for index, item in enumerate(contracts):
        expected_sha, expected_schema = EXPECTED_CONTRACTS[item["contract_id"]]
        if item["sha256"] != expected_sha or item["schema"] != expected_schema:
            _fail("compatibility", f"$.compatibility.contracts[{index}]", "contract binding drift")
    _require_sorted_unique(compatibility["python_versions"], "$.compatibility.python_versions")
    _require_sorted_unique(compatibility["platforms"], "$.compatibility.platforms")
    required = compatibility["required_extensions"]
    optional = compatibility["optional_extensions"]
    _require_sorted_unique(required, "$.compatibility.required_extensions")
    _require_sorted_unique(optional, "$.compatibility.optional_extensions")
    if set(required) & set(optional):
        _fail("compatibility", "$.compatibility", "required and optional extensions overlap")
    dependencies = compatibility["plugin_dependencies"]
    dependency_ids = [item["plugin_id"] for item in dependencies]
    _require_sorted_unique(dependency_ids, "$.compatibility.plugin_dependencies")
    if value["plugin_id"] in dependency_ids:
        _fail("dependency", "$.compatibility.plugin_dependencies", "plugin depends on itself")
    for index, item in enumerate(dependencies):
        minimum = _semver(item["version_minimum"], f"$.compatibility.plugin_dependencies[{index}]")
        maximum = _semver(
            item["version_maximum_exclusive"],
            f"$.compatibility.plugin_dependencies[{index}]",
        )
        if minimum >= maximum:
            _fail("compatibility", f"$.compatibility.plugin_dependencies[{index}]", "empty range")


def _validate_format_support(items: list[dict[str, Any]], path: str) -> None:
    identifiers = [item["format_id"] for item in items]
    _require_sorted_unique(identifiers, path)
    for index, item in enumerate(items):
        if item["minor_minimum"] > item["minor_maximum"]:
            _fail("compatibility", f"{path}[{index}]", "format minor range is empty")
        _require_sorted_unique(item["required_features"], f"{path}[{index}].required_features")


def _validate_capabilities(value: dict[str, Any]) -> None:
    capabilities = value["capabilities"]
    identifiers = [item["capability_id"] for item in capabilities]
    _require_sorted_unique(identifiers, "$.capabilities")
    for index, capability in enumerate(capabilities):
        path = f"$.capabilities[{index}]"
        _require_sorted_unique(capability["theories"], f"{path}.theories")
        if not capability["theories"]:
            _fail("capability", f"{path}.theories", "capability must name a theory")
        fragment = capability["fragment"]
        for field in (
            "domains",
            "quantifiers",
            "expression_kinds",
            "relation_kinds",
            "required_theory_features",
            "forbidden_theory_features",
        ):
            _require_sorted_unique(fragment[field], f"{path}.fragment.{field}")
        if set(fragment["required_theory_features"]) & set(
            fragment["forbidden_theory_features"]
        ):
            _fail("capability", f"{path}.fragment", "required and forbidden features overlap")
        _validate_format_support(capability["evidence_formats"], f"{path}.evidence_formats")
        _validate_format_support(capability["certificate_formats"], f"{path}.certificate_formats")
        if capability["kind"] in {"decision", "construction"} and not capability[
            "evidence_formats"
        ]:
            _fail("capability", path, "producer capability needs an Evidence format")
        if capability["kind"] == "verification" and not capability["certificate_formats"]:
            _fail("capability", path, "verification capability needs a Certificate format")
        cost = capability["cost_model"]
        if cost["maximum"] < cost["base"] or cost["confidence_ppm"] == 0:
            _fail("cost", f"{path}.cost_model", "cost maximum or confidence is invalid")


def _operation_expectations(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    producer_id = value["components"]["producer"]["component_id"]
    checker_id = value["components"]["checker"]["component_id"]
    base_request = [
        "MH-C-PROBLEM-IR-002",
        "MH-C-RESOURCE-BUDGET-001",
        "MH-C-THEORY-CONTEXT-001",
    ]
    return {
        "plan_cost": {
            "component_id": producer_id,
            "request_contract_ids": base_request,
            "response_contract_ids": [],
            "response_schema": "mathhead.plugin-cost.v1",
            "budget_policy": "none",
            "cancellation": "not_applicable",
            "replay_modes": ["deterministic"],
            "effect_kinds": [],
            "authority": "none",
            "outcomes": ["completed", "error", "unsupported"],
        },
        "solve": {
            "component_id": producer_id,
            "request_contract_ids": base_request,
            "response_contract_ids": ["MH-C-ENGINE-RESULT-001", "MH-C-EVIDENCE-001"],
            "response_schema": "mathhead.plugin-solve.v1",
            "budget_policy": "child_lease_required",
            "cancellation": "cooperative_required",
            "replay_modes": value["replay"]["supported_modes"],
            "effect_kinds": None,
            "authority": "producer_report",
            "outcomes": [
                "ambiguous",
                "cancelled",
                "completed",
                "error",
                "exhausted",
                "truncated",
                "unsupported",
            ],
        },
        "check": {
            "component_id": checker_id,
            "request_contract_ids": [
                "MH-C-EVIDENCE-001",
                *base_request,
            ],
            "response_contract_ids": ["MH-C-CERTIFICATE-001"],
            "response_schema": "mathhead.plugin-check.v1",
            "budget_policy": "child_lease_required",
            "cancellation": "cooperative_required",
            "replay_modes": value["replay"]["supported_modes"],
            "effect_kinds": None,
            "authority": "checker_attestation",
            "outcomes": [
                "cancelled",
                "disagreement",
                "exhausted",
                "inconclusive",
                "invalid",
                "truncated",
                "unsupported",
                "verified",
                "verifier_failed",
            ],
        },
        "explain": {
            "component_id": producer_id,
            "request_contract_ids": [
                "MH-C-CERTIFICATE-001",
                "MH-C-ENGINE-RESULT-001",
                "MH-C-EVIDENCE-001",
                *base_request,
            ],
            "response_contract_ids": [],
            "response_schema": "mathhead.plugin-explanation.v1",
            "budget_policy": "child_lease_required",
            "cancellation": "cooperative_required",
            "replay_modes": value["replay"]["supported_modes"],
            "effect_kinds": None,
            "authority": "none",
            "outcomes": [
                "cancelled",
                "completed",
                "error",
                "exhausted",
                "truncated",
                "unsupported",
            ],
        },
    }


def _validate_effects_and_operations(value: dict[str, Any]) -> None:
    effects = value["effects"]
    if [item["kind"] for item in effects] != EFFECT_KINDS:
        _fail("effect", "$.effects", "effect registry must be complete and ordered")
    declared: set[str] = set()
    for index, effect in enumerate(effects):
        if effect["mode"] == "none":
            if effect["policy_id"] is not None or effect["reason"] is not None:
                _fail("effect", f"$.effects[{index}]", "none effect has policy or reason")
        else:
            if effect["policy_id"] is None or effect["reason"] is None:
                _fail("effect", f"$.effects[{index}]", "declared effect lacks policy or reason")
            declared.add(effect["kind"])
    operations = value["operations"]
    if [item["operation"] for item in operations] != OPERATION_ORDER:
        _fail("operation", "$.operations", "operation ABI order is fixed")
    expectations = _operation_expectations(value)
    for index, operation in enumerate(operations):
        path = f"$.operations[{index}]"
        name = operation["operation"]
        for field in (
            "request_contract_ids",
            "response_contract_ids",
            "replay_modes",
            "effect_kinds",
            "outcomes",
        ):
            _require_sorted_unique(operation[field], f"{path}.{field}")
        if not set(operation["effect_kinds"]) <= declared:
            _fail("effect", f"{path}.effect_kinds", "operation uses an undeclared effect")
        expected = expectations[name]
        for field, expected_value in expected.items():
            if field == "effect_kinds" and expected_value is None:
                continue
            if operation[field] != expected_value:
                _fail("operation", f"{path}.{field}", f"{name} binding drift")
    if value["lifecycle"]["isolation"] != "subprocess_required" and declared & {
        "filesystem",
        "network",
        "process",
        "solver",
    }:
        _fail("effect", "$.lifecycle.isolation", "declared external effects require isolation")


def _validate_lifecycle_replay_limits(value: dict[str, Any]) -> None:
    lifecycle = value["lifecycle"]
    if (not lifecycle["reentrant"] or not lifecycle["thread_safe"]) and lifecycle[
        "maximum_concurrency"
    ] != 1:
        _fail("lifecycle", "$.lifecycle.maximum_concurrency", "unsafe plugin must be serial")
    if lifecycle["scope"] == "invocation" and lifecycle["state_persistence"] != "none":
        _fail("lifecycle", "$.lifecycle.state_persistence", "invocation state cannot persist")
    if lifecycle["isolation"] == "subprocess_required" and lifecycle["shutdown_timeout_us"] == 0:
        _fail("lifecycle", "$.lifecycle.shutdown_timeout_us", "subprocess needs shutdown budget")
    replay = value["replay"]
    _require_sorted_unique(replay["supported_modes"], "$.replay.supported_modes")
    has_seeded = "seeded" in replay["supported_modes"]
    expected_policy = "explicit_required_when_seeded" if has_seeded else "forbidden"
    if replay["seed_policy"] != expected_policy:
        _fail("replay", "$.replay.seed_policy", "seed policy and modes disagree")
    if lifecycle["initialization"] == "seeded" and not has_seeded:
        _fail("replay", "$.lifecycle.initialization", "seeded initialization is unsupported")
    if replay["descriptor_basis_sha256"] != descriptor_basis_sha256(value):
        _fail("replay", "$.replay.descriptor_basis_sha256", "descriptor basis mismatch")
    if value["limits"] != EXPECTED_LIMITS:
        _fail("budget", "$.limits", "descriptor hard-limit declaration drift")


def validate_theory_plugin(value: dict[str, Any], schema: dict[str, Any]) -> None:
    started = time.monotonic()
    _shape_budget(value, started)
    _schema_validate(value, schema)
    if set(value) != ROOT_FIELDS:
        _fail("schema", "$", "root field set drift")
    for path, text in _walk_strings(value):
        if "\x00" in text:
            _fail("canonical", path, "NUL is forbidden")
        if unicodedata.normalize("NFC", text) != text:
            _fail("canonical", path, "string is not Unicode NFC")
    entity_count = (
        len(value["compatibility"]["contracts"])
        + len(value["compatibility"]["plugin_dependencies"])
        + len(value["capabilities"])
        + len(value["operations"])
        + len(value["effects"])
    )
    if entity_count > MAX_ENTITIES:
        _fail("budget", "$", "descriptor entities exceed 100000")
    _validate_api_and_implementation(value)
    _validate_components(value)
    _validate_compatibility(value)
    _validate_capabilities(value)
    _validate_effects_and_operations(value)
    _validate_lifecycle_replay_limits(value)
    identities = [
        value["components"]["producer"]["component_id"],
        value["components"]["checker"]["component_id"],
        *(item["capability_id"] for item in value["capabilities"]),
    ]
    if len(identities) != len(set(identities)):
        _fail("identity", "$", "component and capability IDs collide")


def _require_fragment_summary(fragment: dict[str, Any]) -> None:
    expected = {
        "theories",
        "domains",
        "quantifiers",
        "expression_kinds",
        "relation_kinds",
        "polynomial_degree",
        "quantifier_count",
        "quantifier_depth",
        "variables",
        "expression_nodes",
        "goals",
        "ambiguous",
        "exact_arithmetic",
        "theory_features",
    }
    if set(fragment) != expected:
        _fail("routing", "fragment", "fragment summary field set drift")
    for field in (
        "theories",
        "domains",
        "quantifiers",
        "expression_kinds",
        "relation_kinds",
        "theory_features",
    ):
        values = fragment[field]
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            _fail("routing", f"fragment.{field}", "fragment set is malformed")
        _require_sorted_unique(values, f"fragment.{field}")
    for field in (
        "polynomial_degree",
        "quantifier_count",
        "quantifier_depth",
        "variables",
        "expression_nodes",
        "goals",
    ):
        amount = fragment[field]
        if not isinstance(amount, int) or isinstance(amount, bool) or not 0 <= amount <= MAX_JSON_INTEGER:
            _fail("routing", f"fragment.{field}", "fragment quantity is invalid")
    if not isinstance(fragment["ambiguous"], bool) or not isinstance(
        fragment["exact_arithmetic"], bool
    ):
        _fail("routing", "fragment", "fragment flags are malformed")


def capability_supports(capability: dict[str, Any], fragment: dict[str, Any]) -> bool:
    _require_fragment_summary(fragment)
    supported = capability["fragment"]
    if not set(fragment["theories"]) <= set(capability["theories"]):
        return False
    if not set(fragment["domains"]) <= set(supported["domains"]):
        return False
    if not set(fragment["quantifiers"]) <= set(supported["quantifiers"]):
        return False
    if not set(fragment["expression_kinds"]) <= set(supported["expression_kinds"]):
        return False
    if not set(fragment["relation_kinds"]) <= set(supported["relation_kinds"]):
        return False
    if fragment["polynomial_degree"] > supported["maximum_polynomial_degree"]:
        return False
    if fragment["quantifier_depth"] > supported["maximum_quantifier_depth"]:
        return False
    if fragment["variables"] > supported["maximum_variables"]:
        return False
    if fragment["ambiguous"] and not supported["supports_ambiguity"]:
        return False
    if supported["requires_exact_arithmetic"] and not fragment["exact_arithmetic"]:
        return False
    features = set(fragment["theory_features"])
    if not set(supported["required_theory_features"]) <= features:
        return False
    return not bool(set(supported["forbidden_theory_features"]) & features)


def estimate_cost(capability: dict[str, Any], fragment: dict[str, Any]) -> int:
    _require_fragment_summary(fragment)
    model = capability["cost_model"]
    terms = [
        model["base"],
        model["per_variable"] * fragment["variables"],
        model["per_expression_node"] * fragment["expression_nodes"],
        model["per_quantifier"] * fragment["quantifier_count"],
        model["per_goal"] * fragment["goals"],
        model["ambiguity_surcharge"] if fragment["ambiguous"] else 0,
    ]
    total = sum(terms)
    if total > MAX_JSON_INTEGER:
        _fail("cost", "fragment", "planning cost exceeds portable exact range")
    return min(total, model["maximum"])


def route_fragment(
    value: dict[str, Any], fragment: dict[str, Any], *, kind: str
) -> dict[str, Any]:
    if kind not in {"decision", "construction", "verification", "explanation"}:
        _fail("routing", "kind", "unknown capability kind")
    candidates = []
    for capability in value["capabilities"]:
        if capability["kind"] == kind and capability_supports(capability, fragment):
            candidates.append(
                (
                    estimate_cost(capability, fragment),
                    -capability["priority"],
                    capability["capability_id"],
                )
            )
    if not candidates:
        return {"status": "unsupported", "capability_id": None, "cost": None}
    cost, _, capability_id = min(candidates)
    return {"status": "supported", "capability_id": capability_id, "cost": cost}


def minimal_fragment() -> dict[str, Any]:
    return {
        "theories": ["org.mathhead.theory.arithmetic"],
        "domains": ["integer"],
        "quantifiers": ["none"],
        "expression_kinds": ["org.mathhead.expression.add"],
        "relation_kinds": ["org.mathhead.relation.equal"],
        "polynomial_degree": 2,
        "quantifier_count": 0,
        "quantifier_depth": 0,
        "variables": 2,
        "expression_nodes": 5,
        "goals": 1,
        "ambiguous": False,
        "exact_arithmetic": True,
        "theory_features": ["org.mathhead.theory.arithmetic"],
    }


def _operation(
    name: str,
    component_id: str,
    request: list[str],
    response: list[str],
    response_schema: str,
    budget_policy: str,
    cancellation: str,
    replay_modes: list[str],
    authority: str,
    outcomes: list[str],
) -> dict[str, Any]:
    return {
        "operation": name,
        "component_id": component_id,
        "request_contract_ids": request,
        "response_contract_ids": response,
        "response_schema": response_schema,
        "budget_policy": budget_policy,
        "cancellation": cancellation,
        "replay_modes": replay_modes,
        "effect_kinds": [],
        "authority": authority,
        "outcomes": outcomes,
    }


def minimal_theory_plugin() -> dict[str, Any]:
    producer_id = "component_producer"
    checker_id = "component_checker"
    configuration_sha256 = _example_sha("plugin-configuration")
    implementation_sha256 = _example_sha("plugin-implementation")
    replay_modes = ["deterministic", "seeded"]
    base_request = [
        "MH-C-PROBLEM-IR-002",
        "MH-C-RESOURCE-BUDGET-001",
        "MH-C-THEORY-CONTEXT-001",
    ]
    value: dict[str, Any] = {
        "schema": "mathhead.theory-plugin.v1",
        "plugin_id": "org.mathhead.example-plugin",
        "display_name": "Example arithmetic plugin",
        "plugin_version": "1.0.0",
        "api": {
            "contract_id": CONTRACT_ID,
            "contract_sha256": EXPECTED_CONTRACT_SHA256,
            "version": "1.0.0",
            "major": 1,
            "minor": 0,
            "reader_minimum_minor": 0,
        },
        "implementation": {
            "package": "mathhead_example",
            "package_version": "1.0.0",
            "entry_point": "mathhead_example.plugin:ExamplePlugin",
            "implementation_sha256": implementation_sha256,
            "configuration_sha256": configuration_sha256,
            "environment_contract_sha256": _example_sha("environment-contract"),
        },
        "components": {
            "producer": {
                "component_id": producer_id,
                "role": "producer",
                "name": "org.mathhead.example-producer",
                "version": "1.0.0",
                "contract_id": "MH-C-EXAMPLE-PRODUCER-001",
                "contract_sha256": _example_sha("producer-contract"),
                "implementation_sha256": implementation_sha256,
                "configuration_sha256": configuration_sha256,
            },
            "checker": {
                "component_id": checker_id,
                "role": "checker",
                "name": "org.mathhead.example-checker",
                "version": "1.0.0",
                "contract_id": "MH-C-EXAMPLE-CHECKER-001",
                "contract_sha256": _example_sha("checker-contract"),
                "implementation_sha256": _example_sha("checker-implementation"),
                "configuration_sha256": _example_sha("checker-configuration"),
            },
        },
        "compatibility": {
            "contracts": [
                {"contract_id": identifier, "sha256": sha256, "schema": schema}
                for identifier, (sha256, schema) in sorted(EXPECTED_CONTRACTS.items())
            ],
            "python_versions": ["3.10", "3.11", "3.12", "3.13", "3.14"],
            "platforms": ["linux", "macos", "windows"],
            "required_extensions": [],
            "optional_extensions": [],
            "plugin_dependencies": [],
        },
        "capabilities": [
            {
                "capability_id": "capability_arithmetic",
                "kind": "decision",
                "theories": ["org.mathhead.theory.arithmetic"],
                "priority": 100,
                "fragment": {
                    "domains": ["integer", "rational"],
                    "quantifiers": ["exists", "none"],
                    "expression_kinds": ["org.mathhead.expression.add"],
                    "relation_kinds": ["org.mathhead.relation.equal"],
                    "maximum_polynomial_degree": 3,
                    "maximum_quantifier_depth": 2,
                    "maximum_variables": 32,
                    "supports_ambiguity": False,
                    "requires_exact_arithmetic": True,
                    "required_theory_features": ["org.mathhead.theory.arithmetic"],
                    "forbidden_theory_features": [],
                },
                "evidence_formats": [
                    {
                        "format_id": "org.mathhead.proof",
                        "major": 1,
                        "minor_minimum": 0,
                        "minor_maximum": 0,
                        "required_features": [],
                    }
                ],
                "certificate_formats": [
                    {
                        "format_id": "org.mathhead.certificate",
                        "major": 1,
                        "minor_minimum": 0,
                        "minor_maximum": 0,
                        "required_features": [],
                    }
                ],
                "cost_model": {
                    "base": 10,
                    "per_variable": 3,
                    "per_expression_node": 2,
                    "per_quantifier": 5,
                    "per_goal": 7,
                    "ambiguity_surcharge": 20,
                    "maximum": 1000000,
                    "confidence_ppm": 900000,
                },
            }
        ],
        "operations": [
            _operation(
                "plan_cost",
                producer_id,
                base_request,
                [],
                "mathhead.plugin-cost.v1",
                "none",
                "not_applicable",
                ["deterministic"],
                "none",
                ["completed", "error", "unsupported"],
            ),
            _operation(
                "solve",
                producer_id,
                base_request,
                ["MH-C-ENGINE-RESULT-001", "MH-C-EVIDENCE-001"],
                "mathhead.plugin-solve.v1",
                "child_lease_required",
                "cooperative_required",
                replay_modes,
                "producer_report",
                [
                    "ambiguous",
                    "cancelled",
                    "completed",
                    "error",
                    "exhausted",
                    "truncated",
                    "unsupported",
                ],
            ),
            _operation(
                "check",
                checker_id,
                ["MH-C-EVIDENCE-001", *base_request],
                ["MH-C-CERTIFICATE-001"],
                "mathhead.plugin-check.v1",
                "child_lease_required",
                "cooperative_required",
                replay_modes,
                "checker_attestation",
                [
                    "cancelled",
                    "disagreement",
                    "exhausted",
                    "inconclusive",
                    "invalid",
                    "truncated",
                    "unsupported",
                    "verified",
                    "verifier_failed",
                ],
            ),
            _operation(
                "explain",
                producer_id,
                [
                    "MH-C-CERTIFICATE-001",
                    "MH-C-ENGINE-RESULT-001",
                    "MH-C-EVIDENCE-001",
                    *base_request,
                ],
                [],
                "mathhead.plugin-explanation.v1",
                "child_lease_required",
                "cooperative_required",
                replay_modes,
                "none",
                [
                    "cancelled",
                    "completed",
                    "error",
                    "exhausted",
                    "truncated",
                    "unsupported",
                ],
            ),
        ],
        "lifecycle": {
            "scope": "invocation",
            "reentrant": False,
            "thread_safe": False,
            "maximum_concurrency": 1,
            "state_persistence": "none",
            "isolation": "in_process",
            "initialization": "deterministic",
            "shutdown_timeout_us": 0,
        },
        "effects": [
            {"kind": kind, "mode": "none", "policy_id": None, "reason": None}
            for kind in EFFECT_KINDS
        ],
        "replay": {
            "supported_modes": replay_modes,
            "seed_policy": "explicit_required_when_seeded",
            "configuration_sha256": configuration_sha256,
            "descriptor_basis_sha256": "0" * 64,
        },
        "limits": copy.deepcopy(EXPECTED_LIMITS),
        "extensions": {},
    }
    value["replay"]["descriptor_basis_sha256"] = descriptor_basis_sha256(value)
    return value


def _verify_contract_artifact() -> None:
    accepted_path = ROOT / f"docs/contracts/{CONTRACT_ID}.json"
    proposed_path = ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json"
    accepted, accepted_raw = load_json(accepted_path, require_canonical=True)
    proposed, proposed_raw = load_json(proposed_path, require_canonical=True)
    if accepted["contract_id"] != CONTRACT_ID or proposed["contract_id"] != CONTRACT_ID:
        _fail("contract", str(accepted_path), "contract logical identity mismatch")
    if accepted_raw != proposed_raw or _sha(accepted_raw) != EXPECTED_CONTRACT_SHA256:
        _fail("contract", str(accepted_path), "accepted/proposed contract binding mismatch")
    schema_clause = f"{SCHEMA_PATH.as_posix()}={EXPECTED_SCHEMA_SHA256}"
    if not any(schema_clause in clause for clause in accepted["invariants"]):
        _fail("contract", f"{CONTRACT_ID}.invariants", "normative schema identity is not bound")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("descriptor", nargs="?", type=Path)
    args = parser.parse_args(argv)
    try:
        _verify_contract_artifact()
        schema, raw = load_json(ROOT / SCHEMA_PATH)
        if _sha(raw) != EXPECTED_SCHEMA_SHA256:
            _fail("schema-document", str(SCHEMA_PATH), "schema hash mismatch")
        value = minimal_theory_plugin()
        if args.descriptor:
            value, _ = load_json(args.descriptor, require_canonical=True)
        validate_theory_plugin(value, schema)
        decision = route_fragment(value, minimal_fragment(), kind="decision")
        if decision["status"] != "supported":
            _fail("routing", "$", "minimal supported fragment was refused")
    except TheoryPluginValidationError as exc:
        print(f"theory-plugin-contract: FAIL [{exc.kind}] {exc}", file=sys.stderr)
        return 1
    print(
        "theory-plugin-contract: PASS "
        f"(schema={EXPECTED_SCHEMA_SHA256[:12]}, descriptor={canonical_sha256(value)[:12]}, "
        f"cost={decision['cost']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
