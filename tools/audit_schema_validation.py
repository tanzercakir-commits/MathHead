"""Dependency-minimal validation for MathHead's closed audit schemas.

The active audit schemas intentionally use a small, closed Draft 2020-12
keyword set.  This module rejects unknown schema keywords before validating
instances, so running without an optional third-party schema package cannot
silently weaken the repository checks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re
from typing import Any, NoReturn
from urllib.parse import urldefrag, urljoin


_KEYWORDS = frozenset(
    {
        "$defs",
        "$id",
        "$ref",
        "$schema",
        "additionalProperties",
        "allOf",
        "const",
        "enum",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "oneOf",
        "pattern",
        "properties",
        "propertyNames",
        "required",
        "title",
        "type",
        "uniqueItems",
    }
)
_TYPES = frozenset({"array", "boolean", "integer", "null", "number", "object", "string"})
_DIALECT = "https://json-schema.org/draft/2020-12/schema"


class AuditSchemaValidationError(ValueError):
    """A schema graph or instance differs from the supported closed profile."""


def _fail(path: str, detail: str) -> NoReturn:
    raise AuditSchemaValidationError(f"{path}: {detail}")


def _exact_json_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        assert isinstance(left, dict) and isinstance(right, dict)
        return set(left) == set(right) and all(
            _exact_json_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        assert isinstance(left, list) and isinstance(right, list)
        return len(left) == len(right) and all(
            _exact_json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _nonnegative_integer(value: object, path: str) -> int:
    if type(value) is not int or value < 0:
        _fail(path, "must be a non-negative integer")
    return value


def _check_schema(schema: object, path: str) -> None:
    if type(schema) is not dict:
        _fail(path, "schema must be an object")
    assert isinstance(schema, dict)
    unknown = set(schema).difference(_KEYWORDS)
    if unknown:
        _fail(path, f"unsupported schema keywords: {sorted(unknown)!r}")
    for keyword in ("$id", "$ref", "$schema", "title"):
        if keyword in schema and type(schema[keyword]) is not str:
            _fail(f"{path}.{keyword}", "must be a string")
    if "$schema" in schema and schema["$schema"] != _DIALECT:
        _fail(f"{path}.$schema", "must select Draft 2020-12")
    if "type" in schema:
        declared = schema["type"]
        if type(declared) is str:
            types = [declared]
        elif type(declared) is list and declared:
            types = declared
        else:
            _fail(f"{path}.type", "must be a type name or non-empty array")
        if any(type(item) is not str or item not in _TYPES for item in types):
            _fail(f"{path}.type", "contains an unknown JSON type")
        if len(set(types)) != len(types):
            _fail(f"{path}.type", "contains duplicate JSON types")
    for keyword in ("properties", "$defs"):
        if keyword not in schema:
            continue
        members = schema[keyword]
        if type(members) is not dict:
            _fail(f"{path}.{keyword}", "must be an object")
        for name, child in members.items():
            if type(name) is not str:
                _fail(f"{path}.{keyword}", "member name must be a string")
            _check_schema(child, f"{path}.{keyword}.{name}")
    if "required" in schema:
        required = schema["required"]
        if (
            type(required) is not list
            or any(type(item) is not str for item in required)
            or len(set(required)) != len(required)
        ):
            _fail(f"{path}.required", "must be an array of unique strings")
    if "additionalProperties" in schema:
        additional = schema["additionalProperties"]
        if type(additional) is dict:
            _check_schema(additional, f"{path}.additionalProperties")
        elif type(additional) is not bool:
            _fail(f"{path}.additionalProperties", "must be a boolean or schema")
    if "items" in schema:
        _check_schema(schema["items"], f"{path}.items")
    if "propertyNames" in schema:
        _check_schema(schema["propertyNames"], f"{path}.propertyNames")
    for keyword in ("allOf", "oneOf"):
        if keyword not in schema:
            continue
        choices = schema[keyword]
        if type(choices) is not list or not choices:
            _fail(f"{path}.{keyword}", "must be a non-empty array")
        for index, choice in enumerate(choices):
            _check_schema(choice, f"{path}.{keyword}[{index}]")
    for keyword in (
        "minItems",
        "maxItems",
        "minLength",
        "maxLength",
        "minProperties",
        "maxProperties",
    ):
        if keyword in schema:
            _nonnegative_integer(schema[keyword], f"{path}.{keyword}")
    for minimum, maximum in (
        ("minItems", "maxItems"),
        ("minLength", "maxLength"),
        ("minProperties", "maxProperties"),
    ):
        if minimum in schema and maximum in schema and schema[minimum] > schema[maximum]:
            _fail(path, f"{minimum} exceeds {maximum}")
    for keyword in ("minimum", "maximum"):
        if keyword in schema:
            value = schema[keyword]
            if type(value) not in (int, float) or not math.isfinite(value):
                _fail(f"{path}.{keyword}", "must be a finite number")
    if "minimum" in schema and "maximum" in schema and schema["minimum"] > schema["maximum"]:
        _fail(path, "minimum exceeds maximum")
    if "pattern" in schema:
        pattern = schema["pattern"]
        if type(pattern) is not str:
            _fail(f"{path}.pattern", "must be a string")
        try:
            re.compile(pattern)
        except re.error as exc:
            _fail(f"{path}.pattern", f"invalid regular expression: {exc}")
    if "enum" in schema:
        choices = schema["enum"]
        if type(choices) is not list or not choices:
            _fail(f"{path}.enum", "must be a non-empty array")
        for index, choice in enumerate(choices):
            if any(_exact_json_equal(choice, earlier) for earlier in choices[:index]):
                _fail(f"{path}.enum", "contains duplicate JSON values")
    if "uniqueItems" in schema and type(schema["uniqueItems"]) is not bool:
        _fail(f"{path}.uniqueItems", "must be a boolean")


def _resolve_pointer(document: Mapping[str, Any], fragment: str, path: str) -> Mapping[str, Any]:
    current: object = document
    if fragment:
        if not fragment.startswith("/"):
            _fail(path, "only JSON Pointer fragments are supported")
        for raw_part in fragment[1:].split("/"):
            part = raw_part.replace("~1", "/").replace("~0", "~")
            if type(current) is not dict or part not in current:
                _fail(path, "reference target is absent")
            current = current[part]
    if type(current) is not dict:
        _fail(path, "reference target is not a schema object")
    return current


def _resource_registry(
    schemas: Mapping[str, Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    registry: dict[str, Mapping[str, Any]] = {}
    for name, schema in schemas.items():
        _check_schema(schema, name)
        identity = schema.get("$id")
        if type(identity) is not str or not identity:
            _fail(name, "root schema must have a non-empty $id")
        if identity in registry:
            _fail(name, "duplicate schema resource identity")
        registry[identity] = schema
    for identity, schema in registry.items():
        _check_references(schema, schema, identity, registry, identity)
    return registry


def _check_references(
    schema: Mapping[str, Any],
    resource: Mapping[str, Any],
    base_uri: str,
    registry: Mapping[str, Mapping[str, Any]],
    path: str,
) -> None:
    if "$ref" in schema:
        _resolve_reference(str(schema["$ref"]), resource, base_uri, registry, path)
    for keyword in ("properties", "$defs"):
        members = schema.get(keyword, {})
        if isinstance(members, Mapping):
            for name, child in members.items():
                _check_references(child, resource, base_uri, registry, f"{path}.{keyword}.{name}")
    child = schema.get("items")
    if isinstance(child, Mapping):
        _check_references(child, resource, base_uri, registry, f"{path}.items")
    child = schema.get("propertyNames")
    if isinstance(child, Mapping):
        _check_references(
            child, resource, base_uri, registry, f"{path}.propertyNames"
        )
    for keyword in ("allOf", "oneOf"):
        for index, choice in enumerate(schema.get(keyword, ())):
            _check_references(
                choice,
                resource,
                base_uri,
                registry,
                f"{path}.{keyword}[{index}]",
            )
    additional = schema.get("additionalProperties")
    if isinstance(additional, Mapping):
        _check_references(additional, resource, base_uri, registry, f"{path}.additionalProperties")


def _resolve_reference(
    reference: str,
    resource: Mapping[str, Any],
    base_uri: str,
    registry: Mapping[str, Mapping[str, Any]],
    path: str,
) -> tuple[Mapping[str, Any], Mapping[str, Any], str]:
    joined = urljoin(base_uri, reference)
    identity, fragment = urldefrag(joined)
    target_resource = resource if identity == base_uri else registry.get(identity)
    if target_resource is None:
        _fail(path, f"unresolved schema resource: {identity}")
    target = _resolve_pointer(target_resource, fragment, path)
    return target, target_resource, identity


def _is_type(value: object, declared: str) -> bool:
    if declared == "null":
        return value is None
    if declared == "boolean":
        return type(value) is bool
    if declared == "object":
        return type(value) is dict
    if declared == "array":
        return type(value) is list
    if declared == "string":
        return type(value) is str
    if declared == "integer":
        return type(value) is int or (
            type(value) is float and math.isfinite(value) and value.is_integer()
        )
    if declared == "number":
        return type(value) in (int, float) and math.isfinite(value)
    raise AssertionError(declared)


def _validate(
    value: object,
    schema: Mapping[str, Any],
    resource: Mapping[str, Any],
    base_uri: str,
    registry: Mapping[str, Mapping[str, Any]],
    path: str,
) -> None:
    if "$ref" in schema:
        target, target_resource, target_uri = _resolve_reference(
            str(schema["$ref"]), resource, base_uri, registry, path
        )
        _validate(value, target, target_resource, target_uri, registry, path)
    if "type" in schema:
        declared = schema["type"]
        types: Sequence[str] = [declared] if type(declared) is str else declared
        if not any(_is_type(value, item) for item in types):
            _fail(path, f"expected JSON type {list(types)!r}")
    if "const" in schema and not _exact_json_equal(value, schema["const"]):
        _fail(path, "value differs from const")
    if "enum" in schema and not any(_exact_json_equal(value, choice) for choice in schema["enum"]):
        _fail(path, "value is outside enum")
    for choice in schema.get("allOf", ()):
        _validate(value, choice, resource, base_uri, registry, path)
    if "oneOf" in schema:
        matches = 0
        for choice in schema["oneOf"]:
            try:
                _validate(value, choice, resource, base_uri, registry, path)
            except AuditSchemaValidationError:
                continue
            matches += 1
        if matches != 1:
            _fail(path, f"oneOf matched {matches} branches")
    if type(value) is dict:
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            _fail(path, "object is smaller than minProperties")
        if "maxProperties" in schema and len(value) > schema["maxProperties"]:
            _fail(path, "object is larger than maxProperties")
        if "propertyNames" in schema:
            for name in value:
                _validate(
                    name,
                    schema["propertyNames"],
                    resource,
                    base_uri,
                    registry,
                    f"{path}.<propertyName>",
                )
        required = schema.get("required", ())
        missing = [name for name in required if name not in value]
        if missing:
            _fail(path, f"missing required properties: {missing!r}")
        properties = schema.get("properties", {})
        for name, child in properties.items():
            if name in value:
                _validate(value[name], child, resource, base_uri, registry, f"{path}.{name}")
        extras = set(value).difference(properties)
        additional = schema.get("additionalProperties", True)
        if extras and additional is False:
            _fail(path, f"additional properties are closed: {sorted(extras)!r}")
        if type(additional) is dict:
            for name in extras:
                _validate(value[name], additional, resource, base_uri, registry, f"{path}.{name}")
    if type(value) is list:
        if "minItems" in schema and len(value) < schema["minItems"]:
            _fail(path, "array is shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            _fail(path, "array is longer than maxItems")
        if schema.get("uniqueItems"):
            for index, item in enumerate(value):
                if any(_exact_json_equal(item, earlier) for earlier in value[:index]):
                    _fail(f"{path}[{index}]", "array item is not unique")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate(item, schema["items"], resource, base_uri, registry, f"{path}[{index}]")
    if type(value) is str:
        if "minLength" in schema and len(value) < schema["minLength"]:
            _fail(path, "string is shorter than minLength")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            _fail(path, "string is longer than maxLength")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            _fail(path, "string does not match pattern")
    if type(value) in (int, float) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            _fail(path, "number is below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            _fail(path, "number is above maximum")


def validate_schema_instance(
    schema: Mapping[str, Any],
    value: object,
    schemas: Mapping[str, Mapping[str, Any]],
    *,
    label: str = "$",
) -> None:
    """Validate one value after closing and resolving the complete schema graph."""

    registry = _resource_registry(schemas)
    identity = schema.get("$id")
    if type(identity) is not str or registry.get(identity) is not schema:
        _fail(label, "selected schema is not a member of the supplied graph")
    _validate(value, schema, schema, identity, registry, label)


def validate_schema_graph(schemas: Mapping[str, Mapping[str, Any]]) -> None:
    """Validate every schema document and reference in a closed graph."""

    _resource_registry(schemas)
