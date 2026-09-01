#!/usr/bin/env python3
"""Independently validate the accepted TheoryContext v1 schema and semantics."""

from __future__ import annotations

import argparse
from collections import deque
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
CONTRACT_ID = "MH-C-THEORY-CONTEXT-001"
EXPECTED_CONTRACT_SHA256 = "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d"
SCHEMA_PATH = Path("docs/contracts/schemas/theory-context-v1.schema.json")
EXPECTED_SCHEMA_SHA256 = "6a6e40070ba0a3209f5bfcfa0cc912d1ec08359a178611a40d61ffadda5819ec"
ROOT_FIELDS = {
    "schema",
    "context_id",
    "namespace",
    "revision",
    "scope",
    "artifacts",
    "imports",
    "direct_import_ids",
    "declarations",
    "consistency",
    "extensions",
}
REGISTRIES = ("artifacts", "imports", "declarations")
MAX_VALIDATION_SECONDS = 30.0
MAX_CANONICAL_NESTING = 64
MAX_GRAPH_NESTING = 512
MAX_STRING_CODEPOINTS = 1_048_576
MAX_JSON_INTEGER = 9_007_199_254_740_991
MAX_ENTITIES = 100_000


class TheoryContextValidationError(RuntimeError):
    """A classified schema, identity, or semantic validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise TheoryContextValidationError(kind, path, detail)


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


def declaration_sha256(value: dict[str, Any]) -> str:
    """Return the stable fingerprint of one closed declaration object."""
    return canonical_sha256(value)


def consistency_basis_sha256(value: dict[str, Any]) -> str:
    """Bind consistency evidence to every core semantic input, excluding annotations."""
    basis = {
        "schema": value["schema"],
        "context_id": value["context_id"],
        "namespace": value["namespace"],
        "revision": value["revision"],
        "artifacts": value["artifacts"],
        "declarations": value["declarations"],
        "direct_import_ids": value["direct_import_ids"],
        "imports": value["imports"],
        "scope": value["scope"],
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
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs(path))
    except TheoryContextValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _fail("schema", str(path), f"invalid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        _fail("schema", str(path), "root must be an object")
    if require_canonical and raw != canonical_bytes(value):
        _fail("canonical", str(path), "bytes are not canonical TheoryContext JSON")
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
            except TheoryContextValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail("schema", path, f"must match exactly one tagged variant, matched {matches}")
        return
    if "anyOf" in schema:
        for candidate in schema["anyOf"]:
            try:
                _schema_validate(value, candidate, root_schema, path)
            except TheoryContextValidationError:
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


def _shape_budget(value: Any, started: float) -> None:
    stack = [(value, 0, "$")]
    visited = 0
    while stack:
        item, depth, path = stack.pop()
        visited += 1
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


def _ref_key(reference: dict[str, Any]) -> str:
    if reference["kind"] == "local":
        return f"local:{reference['declaration_id']}"
    return (
        f"imported:{reference['import_id']}:{reference['declaration_id']}:"
        f"{reference['declaration_sha256']}"
    )


def _require_sorted_refs(references: list[dict[str, Any]], path: str) -> None:
    keys = [_ref_key(reference) for reference in references]
    _require_sorted_unique(keys, path)


def _index_registries(
    value: dict[str, Any],
) -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, str],
]:
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    global_owner: dict[str, str] = {}
    total = 0
    for registry in REGISTRIES:
        entries = value[registry]
        ids = [entry["id"] for entry in entries]
        if ids != sorted(ids):
            _fail("canonical", f"$.{registry}", "registry IDs must be sorted")
        index: dict[str, dict[str, Any]] = {}
        for position, entry in enumerate(entries):
            identifier = entry["id"]
            if identifier in index:
                _fail("identity", f"$.{registry}[{position}].id", "duplicate registry ID")
            if identifier in global_owner:
                _fail(
                    "identity",
                    f"$.{registry}[{position}].id",
                    f"ID already belongs to {global_owner[identifier]}",
                )
            index[identifier] = entry
            global_owner[identifier] = registry
        indexes[registry] = index
        total += len(entries)
    parent = value["revision"]["parent"]
    if parent is not None:
        total += len(parent["declaration_fingerprints"])
    if total > MAX_ENTITIES:
        _fail("budget", "$", "combined entity count exceeds 100000")
    return indexes, global_owner


def _validate_reference(
    reference: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
    path: str,
) -> None:
    if reference["kind"] == "local":
        if reference["declaration_id"] not in indexes["declarations"]:
            _fail("reference", path, "unknown local declaration")
    elif reference["import_id"] not in indexes["imports"]:
        _fail("reference", path, "unknown imported context")


def _validate_checker_fields(
    record: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    path: str,
) -> None:
    evidence_id = record["evidence_artifact_id"]
    result_id = record["checker_result_artifact_id"]
    if evidence_id not in artifacts or artifacts[evidence_id]["kind"] != "evidence":
        _fail("epistemic", f"{path}.evidence_artifact_id", "must reference evidence")
    if result_id not in artifacts or artifacts[result_id]["kind"] != "checker_result":
        _fail(
            "epistemic",
            f"{path}.checker_result_artifact_id",
            "must reference a checker result",
        )
    _require_sorted_unique(
        record["trust_dependency_sha256s"],
        f"{path}.trust_dependency_sha256s",
    )


def _validate_artifacts(artifacts: dict[str, dict[str, Any]]) -> None:
    identities: set[tuple[str, str, str]] = set()
    for identifier, artifact in artifacts.items():
        path = f"$.artifacts.{identifier}"
        identity = (artifact["kind"], artifact["schema"], artifact["sha256"])
        if identity in identities:
            _fail("identity", path, "duplicate content-addressed artifact")
        identities.add(identity)
        if artifact["kind"] == "problem_ir":
            if artifact["schema"] != "mathhead.problem-ir.v1":
                _fail("artifact", path, "ProblemIR artifact must use mathhead.problem-ir.v1")
        elif artifact["schema"] == "mathhead.problem-ir.v1":
            _fail("artifact", path, "ProblemIR schema requires problem_ir artifact kind")


def _bounded_dag(
    graph: dict[str, list[str]],
    *,
    kind: str,
    path: str,
) -> None:
    unresolved = {node: len(set(dependencies)) for node, dependencies in graph.items()}
    dependents: dict[str, list[str]] = {node: [] for node in graph}
    depth = {node: 0 for node in graph}
    for node, dependencies in graph.items():
        for dependency in dependencies:
            dependents[dependency].append(node)
    ready = deque(sorted(node for node, count in unresolved.items() if count == 0))
    completed = 0
    while ready:
        node = ready.popleft()
        completed += 1
        for dependent in dependents[node]:
            depth[dependent] = max(depth[dependent], depth[node] + 1)
            if depth[dependent] > MAX_GRAPH_NESTING:
                _fail("budget", path, f"{kind} dependency nesting exceeds 512")
            unresolved[dependent] -= 1
            if unresolved[dependent] == 0:
                ready.append(dependent)
    if completed != len(graph):
        _fail("cycle", path, f"cyclic {kind} dependency graph")


def _validate_imports(
    value: dict[str, Any],
    imports: dict[str, dict[str, Any]],
) -> None:
    direct = value["direct_import_ids"]
    _require_sorted_unique(direct, "$.direct_import_ids")
    for identifier in direct:
        if identifier not in imports:
            _fail("reference", "$.direct_import_ids", f"unknown import {identifier}")
    aliases: set[str] = set()
    namespaces: set[str] = set()
    contexts: set[tuple[str, int, str]] = set()
    graph: dict[str, list[str]] = {}
    current_sha = canonical_sha256(value)
    for identifier, imported in imports.items():
        path = f"$.imports.{identifier}"
        is_direct = identifier in direct
        if is_direct != (imported["alias"] is not None):
            _fail("import", f"{path}.alias", "alias must exist exactly for direct imports")
        if imported["alias"] is not None:
            if imported["alias"] in aliases:
                _fail("import", f"{path}.alias", "duplicate direct-import alias")
            aliases.add(imported["alias"])
        if imported["namespace"] == value["namespace"]:
            _fail("import", path, "an imported namespace cannot equal the local namespace")
        if imported["namespace"] in namespaces:
            _fail("import", path, "multiple imported contexts claim one namespace")
        namespaces.add(imported["namespace"])
        if imported["context_id"] == value["context_id"]:
            _fail("import", path, "logical self-import is forbidden")
        if imported["context_sha256"] == current_sha:
            _fail("import", path, "content-addressed self-import is forbidden")
        context_key = (
            imported["context_id"],
            imported["revision"],
            imported["context_sha256"],
        )
        if context_key in contexts:
            _fail("import", path, "duplicate imported context identity")
        contexts.add(context_key)
        dependencies = imported["dependency_import_ids"]
        _require_sorted_unique(dependencies, f"{path}.dependency_import_ids")
        for dependency in dependencies:
            if dependency not in imports:
                _fail("reference", path, f"unknown transitive import {dependency}")
            if dependency == identifier:
                _fail("cycle", path, "import cannot depend on itself")
        graph[identifier] = dependencies
    _bounded_dag(graph, kind="import", path="$.imports")
    reachable: set[str] = set()
    stack = list(reversed(direct))
    while stack:
        identifier = stack.pop()
        if identifier in reachable:
            continue
        reachable.add(identifier)
        stack.extend(reversed(graph[identifier]))
    if reachable != set(imports):
        _fail("import", "$.imports", "every import must be reachable from a direct import")


def _validate_revision(
    value: dict[str, Any],
    declarations: dict[str, dict[str, Any]],
) -> None:
    revision = value["revision"]
    parent = revision["parent"]
    retired = revision["retired_declaration_ids"]
    _require_sorted_unique(retired, "$.revision.retired_declaration_ids")
    if revision["mode"] == "root":
        if revision["number"] != 0 or parent is not None or retired:
            _fail("revision", "$.revision", "root revision must be number zero without parent")
        return
    if parent is None:
        _fail("revision", "$.revision.parent", "derived revision requires a parent")
    if revision["number"] != parent["revision"] + 1:
        _fail("revision", "$.revision.number", "revision must advance parent by exactly one")
    if parent["context_id"] != value["context_id"]:
        _fail("revision", "$.revision.parent.context_id", "parent context ID drift")
    if parent["context_sha256"] == canonical_sha256(value):
        _fail("revision", "$.revision.parent.context_sha256", "parent cannot be current context")
    fingerprints = parent["declaration_fingerprints"]
    fingerprint_ids = [item["id"] for item in fingerprints]
    if fingerprint_ids != sorted(fingerprint_ids) or len(fingerprint_ids) != len(
        set(fingerprint_ids)
    ):
        _fail("canonical", "$.revision.parent.declaration_fingerprints", "must sort by ID")
    fingerprint_map = {item["id"]: item["sha256"] for item in fingerprints}
    if not set(retired) <= set(fingerprint_map):
        _fail("revision", "$.revision.retired_declaration_ids", "retired ID is not in parent")
    if revision["mode"] == "extension" and retired:
        _fail("revision", "$.revision", "extension cannot retire declarations")
    for identifier, expected_sha in fingerprint_map.items():
        if identifier in retired:
            if identifier in declarations:
                _fail("revision", "$.declarations", "retired declaration remains present")
            continue
        if identifier not in declarations:
            _fail("revision", "$.declarations", "parent declaration disappeared silently")
        if declaration_sha256(declarations[identifier]) != expected_sha:
            _fail("revision", "$.declarations", "parent declaration changed under stable ID")
    added = set(declarations) - set(fingerprint_map)
    if not added and not retired:
        _fail("revision", "$.revision", "derived revision must make an explicit change")


def _validate_declarations(
    value: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> None:
    artifacts = indexes["artifacts"]
    imports = indexes["imports"]
    declarations = indexes["declarations"]
    qualified_names: set[str] = set()
    graph: dict[str, list[str]] = {}
    scope = value["scope"]
    for identifier, declaration in declarations.items():
        path = f"$.declarations.{identifier}"
        namespace = declaration["namespace"]
        if namespace != value["namespace"] and not namespace.startswith(value["namespace"] + "."):
            _fail("namespace", f"{path}.namespace", "declaration escapes context namespace")
        expected_qualified = f"{namespace}.{declaration['name']}"
        if declaration["qualified_name"] != expected_qualified:
            _fail("namespace", f"{path}.qualified_name", "qualified name is not exact")
        if expected_qualified in qualified_names:
            _fail("namespace", f"{path}.qualified_name", "duplicate qualified name")
        qualified_names.add(expected_qualified)
        content = declaration["content"]
        artifact_id = content["artifact_id"]
        if artifact_id not in artifacts or artifacts[artifact_id]["kind"] != "problem_ir":
            _fail("artifact", f"{path}.content.artifact_id", "must reference ProblemIR")
        kind = declaration["kind"]
        entity_kind = content["entity_kind"]
        epistemic = declaration["epistemic"]
        status = epistemic["status"]
        origin = declaration["origin"]
        if kind == "definition":
            if entity_kind != "definition" or status != "definitional" or origin is not None:
                _fail("epistemic", path, "definition must be definitional and locally sourced")
        else:
            if entity_kind != "statement":
                _fail("artifact", f"{path}.content.entity_kind", "claim must be a statement")
        if kind == "axiom":
            if status != "assumed" or origin is not None:
                _fail("epistemic", path, "axiom must be an explicit local assumption")
        elif kind == "hypothesis":
            if status != "assumed_local" or origin is not None:
                _fail("epistemic", path, "hypothesis must be an explicit local assumption")
        elif kind == "lemma":
            if status not in {"unchecked", "checker_attested"} or origin is not None:
                _fail("epistemic", path, "local lemma has invalid authority state")
        elif kind == "imported_lemma":
            if status not in {"unchecked", "checker_attested"} or origin is None:
                _fail("epistemic", path, "imported lemma must retain its imported origin")
        if status == "checker_attested":
            _validate_checker_fields(epistemic, artifacts, f"{path}.epistemic")
        if origin is not None:
            _validate_reference(origin, indexes, f"{path}.origin")
        declaration_scope = declaration["scope_id"]
        if scope["kind"] == "theory":
            if declaration_scope is not None or kind == "hypothesis":
                _fail("scope", path, "theory scope cannot contain local declarations")
        else:
            if declaration_scope not in {None, scope["id"]}:
                _fail("scope", f"{path}.scope_id", "declaration belongs to another scope")
            if kind == "hypothesis" and declaration_scope != scope["id"]:
                _fail("scope", path, "hypothesis must name the active local scope")
            if kind in {"axiom", "imported_lemma"} and declaration_scope is not None:
                _fail("scope", path, "axioms and imported lemmas cannot become local claims")
            if declaration_scope is not None and declaration["visibility"] != "private":
                _fail("scope", path, "local declarations cannot be public")
        if status == "assumed_local":
            if scope["kind"] != "local" or epistemic["scope_id"] != scope["id"]:
                _fail("scope", f"{path}.epistemic", "local authority scope mismatch")
        references = declaration["dependency_refs"]
        _require_sorted_refs(references, f"{path}.dependency_refs")
        local_dependencies: list[str] = []
        for position, reference in enumerate(references):
            _validate_reference(reference, indexes, f"{path}.dependency_refs[{position}]")
            if reference["kind"] == "local":
                dependency = reference["declaration_id"]
                if dependency == identifier:
                    _fail("cycle", path, "declaration cannot depend on itself")
                if declaration_scope is None and declarations[dependency]["scope_id"] is not None:
                    _fail("scope", path, "unscoped declaration depends on a local declaration")
                local_dependencies.append(dependency)
        if kind == "imported_lemma" and _ref_key(origin) not in {
            _ref_key(reference) for reference in references
        }:
            _fail("reference", path, "imported lemma origin must be a dependency")
        graph[identifier] = local_dependencies
    _bounded_dag(graph, kind="declaration", path="$.declarations")
    if scope["kind"] == "local":
        parent_sha = scope["parent_theory_sha256"]
        if not any(
            imported["context_sha256"] == parent_sha
            for identifier, imported in imports.items()
            if identifier in value["direct_import_ids"]
        ):
            _fail("scope", "$.scope.parent_theory_sha256", "local parent theory is not imported")


def _consistency_references(consistency: dict[str, Any]) -> list[dict[str, Any]]:
    status = consistency["status"]
    if status in {"unknown", "fragment_consistent"}:
        return consistency["covered_declaration_refs"]
    if status == "inconsistent":
        return consistency["conflict_declaration_refs"]
    return []


def _validate_consistency(
    value: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> None:
    consistency = value["consistency"]
    if consistency["basis_sha256"] != consistency_basis_sha256(value):
        _fail("consistency", "$.consistency.basis_sha256", "context basis hash mismatch")
    references = _consistency_references(consistency)
    _require_sorted_refs(references, "$.consistency.declaration_refs")
    for position, reference in enumerate(references):
        _validate_reference(reference, indexes, f"$.consistency.declaration_refs[{position}]")
    status = consistency["status"]
    artifacts = indexes["artifacts"]
    if status in {"fragment_consistent", "inconsistent"}:
        _validate_checker_fields(consistency, artifacts, "$.consistency")
    elif status == "unknown" and consistency["checker_result_artifact_id"] is not None:
        identifier = consistency["checker_result_artifact_id"]
        if identifier not in artifacts or artifacts[identifier]["kind"] != "checker_result":
            _fail(
                "consistency",
                "$.consistency.checker_result_artifact_id",
                "must reference a checker result",
            )


def validate_theory_context(value: dict[str, Any], schema: dict[str, Any]) -> None:
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
    indexes, _global_owner = _index_registries(value)
    _validate_artifacts(indexes["artifacts"])
    _validate_imports(value, indexes["imports"])
    _validate_declarations(value, indexes)
    _validate_revision(value, indexes["declarations"])
    _validate_consistency(value, indexes)
    canonical_bytes(value)
    if time.monotonic() - started > MAX_VALIDATION_SECONDS:
        _fail("budget", "$", "validation exceeded 30 seconds")


def minimal_theory_context() -> dict[str, Any]:
    imported_origin = {
        "kind": "imported",
        "import_id": "import_base",
        "declaration_id": "declaration_base_lemma",
        "declaration_sha256": "4" * 64,
    }
    value: dict[str, Any] = {
        "schema": "mathhead.theory-context.v1",
        "context_id": "context_example",
        "namespace": "org.mathhead.example",
        "revision": {
            "number": 0,
            "mode": "root",
            "parent": None,
            "retired_declaration_ids": [],
        },
        "scope": {"kind": "theory", "id": None, "parent_theory_sha256": None},
        "artifacts": [
            {
                "id": "artifact_checker",
                "kind": "checker_result",
                "schema": "mathhead.checker-result.v1",
                "sha256": "1" * 64,
            },
            {
                "id": "artifact_evidence",
                "kind": "evidence",
                "schema": "mathhead.evidence.v1",
                "sha256": "2" * 64,
            },
            {
                "id": "artifact_problem",
                "kind": "problem_ir",
                "schema": "mathhead.problem-ir.v1",
                "sha256": "3" * 64,
            },
        ],
        "imports": [
            {
                "id": "import_base",
                "alias": "base",
                "context_id": "context_base",
                "namespace": "org.mathhead.base",
                "revision": 2,
                "context_sha256": "5" * 64,
                "exports_sha256": "6" * 64,
                "dependency_import_ids": [],
            }
        ],
        "direct_import_ids": ["import_base"],
        "declarations": [
            {
                "id": "declaration_axiom",
                "kind": "axiom",
                "namespace": "org.mathhead.example",
                "name": "IdentityAxiom",
                "qualified_name": "org.mathhead.example.IdentityAxiom",
                "visibility": "public",
                "content": {
                    "artifact_id": "artifact_problem",
                    "entity_kind": "statement",
                    "entity_id": "statement_identity_axiom",
                },
                "dependency_refs": [],
                "epistemic": {
                    "status": "assumed",
                    "authority_id": "org.mathhead.owner",
                    "rationale": "Declared as an explicit axiom of the example theory.",
                },
                "origin": None,
                "scope_id": None,
                "extensions": {},
            },
            {
                "id": "declaration_definition",
                "kind": "definition",
                "namespace": "org.mathhead.example",
                "name": "Identity",
                "qualified_name": "org.mathhead.example.Identity",
                "visibility": "public",
                "content": {
                    "artifact_id": "artifact_problem",
                    "entity_kind": "definition",
                    "entity_id": "definition_identity",
                },
                "dependency_refs": [],
                "epistemic": {"status": "definitional"},
                "origin": None,
                "scope_id": None,
                "extensions": {},
            },
            {
                "id": "declaration_imported",
                "kind": "imported_lemma",
                "namespace": "org.mathhead.example",
                "name": "ImportedIdentity",
                "qualified_name": "org.mathhead.example.ImportedIdentity",
                "visibility": "public",
                "content": {
                    "artifact_id": "artifact_problem",
                    "entity_kind": "statement",
                    "entity_id": "statement_imported_identity",
                },
                "dependency_refs": [imported_origin.copy()],
                "epistemic": {
                    "status": "unchecked",
                    "reason": "The imported claim is pinned but has no local checker verdict.",
                },
                "origin": imported_origin.copy(),
                "scope_id": None,
                "extensions": {},
            },
            {
                "id": "declaration_lemma",
                "kind": "lemma",
                "namespace": "org.mathhead.example",
                "name": "IdentityLemma",
                "qualified_name": "org.mathhead.example.IdentityLemma",
                "visibility": "public",
                "content": {
                    "artifact_id": "artifact_problem",
                    "entity_kind": "statement",
                    "entity_id": "statement_identity_lemma",
                },
                "dependency_refs": [
                    {"kind": "local", "declaration_id": "declaration_axiom"},
                    {"kind": "local", "declaration_id": "declaration_definition"},
                ],
                "epistemic": {
                    "status": "checker_attested",
                    "evidence_artifact_id": "artifact_evidence",
                    "checker_result_artifact_id": "artifact_checker",
                    "checker_contract_id": "MH-C-CHECKER-001",
                    "checker_contract_sha256": "7" * 64,
                    "trust_dependency_sha256s": ["8" * 64],
                },
                "origin": None,
                "scope_id": None,
                "extensions": {},
            },
        ],
        "consistency": {
            "status": "unchecked",
            "basis_sha256": "0" * 64,
            "reason": "No bounded consistency checker has been run.",
        },
        "extensions": {},
    }
    value["consistency"]["basis_sha256"] = consistency_basis_sha256(value)
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
            value = minimal_theory_context()
        else:
            path = args.instance if args.instance.is_absolute() else root / args.instance
            value, _raw = load_json(path, require_canonical=True)
        validate_theory_context(value, schema)
    except (TheoryContextValidationError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"theory-context-contract: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "theory-context-contract: PASS "
        f"(schema={EXPECTED_SCHEMA_SHA256[:12]}, identity={canonical_sha256(value)[:12]})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
