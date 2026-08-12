"""Syntax-neutral, dependency-minimal structured problem intake for MH-040.

The boundary accepts only exact built-in Python data.  It constructs one
canonical ProblemIR representation or a closed failure result.  Representation
validity carries no mathematical authority and performs no solving or parsing
of prose, LaTeX, Python expressions, or legacy adapter payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Final, NoReturn
import unicodedata


CONTRACT_ID: Final = "MH-C-PROBLEM-INTAKE-001"
CONTRACT_SHA256: Final = \
    "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc"
PROBLEM_IR_CONTRACT_SHA256: Final = \
    "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286"
PROBLEM_IR_SCHEMA_SHA256: Final = \
    "dcf871f15ebbae06b0eca285a115f2545defc00cb0befc23e3cc574d8523df2c"
INTAKE_SCHEMA: Final = "mathhead.problem-intake.v1"
PROBLEM_SCHEMA: Final = "mathhead.problem-ir.v1"
RESULT_SCHEMA: Final = "mathhead.problem-intake-result.v1"

MAX_INPUT_BYTES: Final = 67_108_864
MAX_OUTPUT_BYTES: Final = 67_108_864
MAX_NODES: Final = 4_000_000
MAX_DEPTH: Final = 512
MAX_ARRAY_ITEMS: Final = 100_000
MAX_ENTITIES: Final = 100_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 16_777_216
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_NUMERIC_DIGITS: Final = 4_096
MAX_DIAGNOSTICS: Final = 32
MAX_DIAGNOSTIC_CODEPOINTS: Final = 512
MAX_VALIDATION_STEPS: Final = 8_000_000

ROOT_FIELDS: Final = frozenset(
    {
        "ambiguity",
        "assumptions",
        "definitions",
        "domains",
        "expressions",
        "extensions",
        "goals",
        "readings",
        "relations",
        "schema",
        "source_documents",
        "source_spans",
        "statements",
        "variables",
    }
)
REGISTRIES: Final = (
    "source_documents",
    "source_spans",
    "domains",
    "variables",
    "expressions",
    "relations",
    "statements",
    "definitions",
    "assumptions",
    "goals",
    "readings",
)

_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_NAMESPACED = re.compile(r"^[a-z][a-z0-9-]*(?:\.[a-z][a-z0-9-]*)+$")
_EXTENSION_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_PATH = re.compile(r"^\$(?:\.[a-z][a-z0-9_]*|\[[0-9]+\])*$")
_RESULT_TOKEN: Final = object()


class ProblemIntakeValidationError(ValueError):
    """A strict result codec invariant failed."""

    __slots__ = ("kind", "path")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path


class _ProblemError(ValueError):
    __slots__ = ("kind", "path", "detail")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ProblemIntakeDiagnostic:
    """One bounded, immutable intake failure description."""

    code: str
    message: str
    path: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProblemIntakeDiagnostic cannot be pickled")

    def __copy__(self) -> ProblemIntakeDiagnostic:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ProblemIntakeDiagnostic:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class ProblemIntakeResult:
    """Closed structural result with explicitly no mathematical authority."""

    contract_id: str
    contract_sha256: str
    diagnostics: tuple[ProblemIntakeDiagnostic, ...]
    mathematical_authority: bool
    problem_ir_bytes: bytes | None
    problem_ir_contract_sha256: str
    problem_ir_schema_sha256: str
    problem_ir_sha256: str | None
    reason_code: str
    schema: str
    status: str

    def __init__(
        self,
        *,
        contract_id: str = CONTRACT_ID,
        contract_sha256: str = CONTRACT_SHA256,
        diagnostics: tuple[ProblemIntakeDiagnostic, ...] = (),
        mathematical_authority: bool = False,
        problem_ir_bytes: bytes | None = None,
        problem_ir_contract_sha256: str = PROBLEM_IR_CONTRACT_SHA256,
        problem_ir_schema_sha256: str = PROBLEM_IR_SCHEMA_SHA256,
        problem_ir_sha256: str | None = None,
        reason_code: str = "INVALID_PROBLEM",
        schema: str = RESULT_SCHEMA,
        status: str = "invalid",
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError("ProblemIntakeResult is constructed by intake_problem")
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ProblemIntakeResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProblemIntakeResult cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("ProblemIntakeResult cannot be pickled")

    def __copy__(self) -> ProblemIntakeResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ProblemIntakeResult:
        del memo
        return self


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _ProblemError(kind, path, detail)


def _step(steps: list[int], path: str, count: int = 1) -> None:
    steps[0] += count
    if steps[0] > MAX_VALIDATION_STEPS:
        _fail("budget", path, "validation step budget exceeded")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        _fail("canonical", "$", f"value is not canonical JSON: {exc}")
    payload = (rendered + "\n").encode("utf-8")
    if len(payload) > MAX_OUTPUT_BYTES:
        _fail("budget", "$", "canonical output exceeds 67108864 bytes")
    return payload


def _normal_string(value: object, path: str, budget: list[int]) -> str:
    if type(value) is not str:
        _fail("type", path, "expected an exact string")
    if "\x00" in value:
        _fail("canonical", path, "NUL is forbidden")
    normalized = unicodedata.normalize("NFC", value)
    if len(normalized) > MAX_STRING_CODEPOINTS:
        _fail("budget", path, "string exceeds 1048576 code points")
    budget[0] += len(normalized)
    if budget[0] > MAX_AGGREGATE_STRING_CODEPOINTS:
        _fail("budget", path, "aggregate string budget exceeded")
    return normalized


def _normalize_exact(
    value: object,
    *,
    path: str = "$",
    depth: int = 0,
    nodes: list[int] | None = None,
    strings: list[int] | None = None,
    steps: list[int] | None = None,
) -> object:
    if nodes is None:
        nodes = [0]
    if strings is None:
        strings = [0]
    if steps is None:
        steps = [0]
    _step(steps, path)
    nodes[0] += 1
    if nodes[0] > MAX_NODES:
        _fail("budget", path, "node budget exceeded")
    if depth > MAX_DEPTH:
        _fail("budget", path, "nesting exceeds 512")
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_INTEGER:
            _fail("budget", path, "integer exceeds portable exact range")
        return value
    if type(value) is str:
        return _normal_string(value, path, strings)
    if type(value) in {list, tuple}:
        if len(value) > MAX_ARRAY_ITEMS:
            _fail("budget", path, "array exceeds 100000 items")
        return [
            _normalize_exact(
                item,
                path=f"{path}[{index}]",
                depth=depth + 1,
                nodes=nodes,
                strings=strings,
                steps=steps,
            )
            for index, item in enumerate(value)
        ]
    if type(value) is dict:
        if len(value) > MAX_ARRAY_ITEMS:
            _fail("budget", path, "object exceeds 100000 fields")
        result: dict[str, object] = {}
        for key, item in value.items():
            normalized_key = _normal_string(key, f"{path}.<key>", strings)
            if normalized_key in result:
                _fail("canonical", path, "dictionary keys collide after NFC normalization")
            result[normalized_key] = _normalize_exact(
                item,
                path=f"{path}.{normalized_key}",
                depth=depth + 1,
                nodes=nodes,
                strings=strings,
                steps=steps,
            )
        return result
    _fail("type", path, f"unsupported Python type {type(value).__name__}")


def _closed(value: object, fields: set[str] | frozenset[str], path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("schema", path, "expected an object")
    missing = sorted(fields - set(value))
    unknown = sorted(set(value) - fields)
    if missing:
        _fail("schema", path, f"missing fields {missing}")
    if unknown:
        _fail("schema", path, f"unknown fields {unknown}")
    return value


def _array(value: object, path: str, *, minimum: int = 0, unique: bool = False) -> list[Any]:
    if type(value) is not list:
        _fail("schema", path, "expected an array")
    if len(value) < minimum:
        _fail("schema", path, f"array requires at least {minimum} item(s)")
    if len(value) > MAX_ARRAY_ITEMS:
        _fail("budget", path, "array exceeds 100000 items")
    if unique:
        identities = [_canonical_bytes(item) for item in value]
        if len(identities) != len(set(identities)):
            _fail("schema", path, "array items must be unique")
    return value


def _string(
    value: object,
    path: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_STRING_CODEPOINTS,
) -> str:
    if type(value) is not str:
        _fail("schema", path, "expected a string")
    if not minimum <= len(value) <= maximum:
        _fail("schema", path, "string length is outside the allowed range")
    return value


def _identifier(value: object, path: str) -> str:
    text = _string(value, path, minimum=1, maximum=64)
    if _ID.fullmatch(text) is None:
        _fail("schema", path, "invalid stable identifier")
    return text


def _namespace(value: object, path: str) -> str:
    text = _string(value, path, minimum=3, maximum=255)
    if _NAMESPACED.fullmatch(text) is None:
        _fail("schema", path, "invalid namespaced identifier")
    return text


def _enum(value: object, allowed: set[object], path: str) -> object:
    if value not in allowed or type(value) not in {type(item) for item in allowed}:
        _fail("schema", path, f"value is outside enum {sorted(allowed)!r}")
    return value


def _exact_bool(value: object, path: str) -> bool:
    if type(value) is not bool:
        _fail("schema", path, "expected a boolean")
    return value


def _exact_int(value: object, path: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        _fail("schema", path, "expected an exact integer")
    if not minimum <= value <= MAX_INTEGER:
        _fail("schema", path, "integer is outside the allowed range")
    return value


def _ids(value: object, path: str, *, minimum: int = 0, unique: bool = False) -> list[str]:
    values = _array(value, path, minimum=minimum, unique=unique)
    return [_identifier(item, f"{path}[{index}]") for index, item in enumerate(values)]


def _span_ids(record: dict[str, Any], path: str) -> None:
    _ids(record["span_ids"], path + ".span_ids", unique=True)


def _canonical_value(
    value: object,
    path: str,
    *,
    depth: int = 0,
    steps: list[int] | None = None,
) -> None:
    if steps is not None:
        _step(steps, path)
    if depth > 64:
        _fail("budget", path, "canonical extension nesting exceeds 64")
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _canonical_value(item, f"{path}[{index}]", depth=depth + 1, steps=steps)
        return
    if type(value) is dict:
        for key, item in value.items():
            if _EXTENSION_KEY.fullmatch(key) is None:
                _fail("schema", f"{path}.<key>", "invalid canonical mapping key")
            _canonical_value(item, f"{path}.{key}", depth=depth + 1, steps=steps)
        return
    _fail("schema", path, "invalid canonical value")


def _shape_domain(record: object, path: str) -> None:
    if type(record) is not dict:
        _fail("schema", path, "expected a domain object")
    kind = record.get("kind")
    common = {"id", "kind", "span_ids"}
    variants = {
        "builtin": common | {"name"},
        "finite": common | {"cardinality", "element_domain_id", "element_expr_ids"},
        "interval": common
        | {"base", "lower_closed", "lower_expr_id", "upper_closed", "upper_expr_id"},
        "modular": common | {"modulus_expr_id"},
        "collection": common | {"collection", "element_domain_id", "finiteness"},
        "product": common | {"factor_domain_ids"},
        "function": common | {"parameter_domain_ids", "result_domain_id", "total"},
        "structure": common
        | {"parameter_domain_ids", "parameter_expr_ids", "theory_id"},
    }
    if kind not in variants:
        _fail("schema", path + ".kind", "unknown domain variant")
    value = _closed(record, variants[kind], path)
    _identifier(value["id"], path + ".id")
    _span_ids(value, path)
    if kind == "builtin":
        _enum(
            value["name"],
            {"boolean", "complex", "integer", "natural", "rational", "real"},
            path + ".name",
        )
    elif kind == "finite":
        _identifier(value["element_domain_id"], path + ".element_domain_id")
        _ids(value["element_expr_ids"], path + ".element_expr_ids", minimum=1, unique=True)
        cardinality = _exact_int(value["cardinality"], path + ".cardinality", minimum=1)
        if cardinality > MAX_ARRAY_ITEMS:
            _fail("schema", path + ".cardinality", "finite cardinality exceeds 100000")
    elif kind == "interval":
        _enum(value["base"], {"integer", "rational", "real"}, path + ".base")
        for label in ("lower", "upper"):
            bound = value[f"{label}_expr_id"]
            if bound is not None:
                _identifier(bound, f"{path}.{label}_expr_id")
            _exact_bool(value[f"{label}_closed"], f"{path}.{label}_closed")
    elif kind == "modular":
        _identifier(value["modulus_expr_id"], path + ".modulus_expr_id")
    elif kind == "collection":
        _enum(value["collection"], {"multiset", "sequence", "set"}, path + ".collection")
        _identifier(value["element_domain_id"], path + ".element_domain_id")
        _enum(value["finiteness"], {"finite", "infinite", "unknown"}, path + ".finiteness")
    elif kind == "product":
        _ids(value["factor_domain_ids"], path + ".factor_domain_ids", minimum=1)
    elif kind == "function":
        _ids(value["parameter_domain_ids"], path + ".parameter_domain_ids")
        _identifier(value["result_domain_id"], path + ".result_domain_id")
        _exact_bool(value["total"], path + ".total")
    elif kind == "structure":
        _namespace(value["theory_id"], path + ".theory_id")
        _ids(value["parameter_domain_ids"], path + ".parameter_domain_ids")
        _ids(value["parameter_expr_ids"], path + ".parameter_expr_ids")


def _shape_expression(record: object, path: str) -> None:
    if type(record) is not dict:
        _fail("schema", path, "expected an expression object")
    kind = record.get("kind")
    common = {"domain_id", "id", "kind", "span_ids"}
    variants = {
        "literal": common | {"literal_type", "value"},
        "variable": common | {"variable_id"},
        "apply": common | {"argument_expr_ids", "attributes", "operator"},
        "tuple": common | {"element_expr_ids"},
        "collection": common | {"element_expr_ids"},
        "conditional": common
        | {"condition_statement_id", "else_expr_id", "then_expr_id"},
    }
    if kind not in variants:
        _fail("schema", path + ".kind", "unknown expression variant")
    value = _closed(record, variants[kind], path)
    _identifier(value["id"], path + ".id")
    _identifier(value["domain_id"], path + ".domain_id")
    _span_ids(value, path)
    if kind == "literal":
        _enum(
            value["literal_type"],
            {"boolean", "integer", "rational", "string"},
            path + ".literal_type",
        )
        _string(value["value"], path + ".value")
    elif kind == "variable":
        _identifier(value["variable_id"], path + ".variable_id")
    elif kind == "apply":
        _namespace(value["operator"], path + ".operator")
        _ids(value["argument_expr_ids"], path + ".argument_expr_ids")
        if type(value["attributes"]) is not dict:
            _fail("schema", path + ".attributes", "operator attributes must be an object")
        _canonical_value(value["attributes"], path + ".attributes")
    elif kind in {"tuple", "collection"}:
        _ids(value["element_expr_ids"], path + ".element_expr_ids")
    else:
        _identifier(value["condition_statement_id"], path + ".condition_statement_id")
        _identifier(value["then_expr_id"], path + ".then_expr_id")
        _identifier(value["else_expr_id"], path + ".else_expr_id")


def _shape_relation(record: object, path: str) -> None:
    if type(record) is not dict:
        _fail("schema", path, "expected a relation object")
    kind = record.get("kind")
    common = {"id", "kind", "operand_expr_ids", "span_ids"}
    if kind == "predicate":
        value = _closed(record, common | {"predicate"}, path)
        _namespace(value["predicate"], path + ".predicate")
        minimum = 0
    elif kind in {
        "congruent",
        "divides",
        "equal",
        "greater",
        "greater_equal",
        "less",
        "less_equal",
        "member",
        "not_equal",
        "not_member",
    }:
        value = _closed(record, common, path)
        minimum = 2
    else:
        _fail("schema", path + ".kind", "unknown relation variant")
    _identifier(value["id"], path + ".id")
    _ids(value["operand_expr_ids"], path + ".operand_expr_ids", minimum=minimum)
    _span_ids(value, path)


def _shape_statement(record: object, path: str) -> None:
    if type(record) is not dict:
        _fail("schema", path, "expected a statement object")
    kind = record.get("kind")
    common = {"id", "kind", "span_ids"}
    variants = {
        "truth": common | {"value"},
        "relation": common | {"relation_id"},
        "logical": common | {"operand_statement_ids", "operator"},
        "quantified": common | {"body_statement_id", "quantifier", "variable_ids"},
    }
    if kind not in variants:
        _fail("schema", path + ".kind", "unknown statement variant")
    value = _closed(record, variants[kind], path)
    _identifier(value["id"], path + ".id")
    _span_ids(value, path)
    if kind == "truth":
        _exact_bool(value["value"], path + ".value")
    elif kind == "relation":
        _identifier(value["relation_id"], path + ".relation_id")
    elif kind == "logical":
        _enum(value["operator"], {"and", "iff", "implies", "not", "or"}, path + ".operator")
        _ids(value["operand_statement_ids"], path + ".operand_statement_ids", minimum=1)
    else:
        _enum(
            value["quantifier"],
            {"exists", "exists_unique", "forall"},
            path + ".quantifier",
        )
        _ids(value["variable_ids"], path + ".variable_ids", minimum=1, unique=True)
        _identifier(value["body_statement_id"], path + ".body_statement_id")


def _shape_definition(record: object, path: str) -> None:
    value = _closed(
        record,
        {"body", "id", "name", "parameter_variable_ids", "recursive", "result_domain_id", "span_ids"},
        path,
    )
    _identifier(value["id"], path + ".id")
    _string(value["name"], path + ".name", minimum=1, maximum=1024)
    _ids(value["parameter_variable_ids"], path + ".parameter_variable_ids", unique=True)
    if value["result_domain_id"] is not None:
        _identifier(value["result_domain_id"], path + ".result_domain_id")
    if type(value["body"]) is not dict:
        _fail("schema", path + ".body", "expected a definition body")
    body_kind = value["body"].get("kind")
    if body_kind == "expression":
        body = _closed(value["body"], {"expression_id", "kind"}, path + ".body")
        _identifier(body["expression_id"], path + ".body.expression_id")
    elif body_kind == "statement":
        body = _closed(value["body"], {"kind", "statement_id"}, path + ".body")
        _identifier(body["statement_id"], path + ".body.statement_id")
    else:
        _fail("schema", path + ".body.kind", "unknown definition body variant")
    _exact_bool(value["recursive"], path + ".recursive")
    _span_ids(value, path)


def _shape_reading(record: object, path: str) -> None:
    value = _closed(
        record,
        {
            "assumption_ids",
            "definition_ids",
            "difference_from",
            "differences",
            "goal_ids",
            "id",
            "label",
            "span_ids",
        },
        path,
    )
    _identifier(value["id"], path + ".id")
    _string(value["label"], path + ".label", minimum=1, maximum=4096)
    _ids(value["definition_ids"], path + ".definition_ids", unique=True)
    _ids(value["assumption_ids"], path + ".assumption_ids", unique=True)
    _ids(value["goal_ids"], path + ".goal_ids", minimum=1, unique=True)
    if value["difference_from"] is not None:
        _identifier(value["difference_from"], path + ".difference_from")
    for index, item in enumerate(_array(value["differences"], path + ".differences")):
        item_path = f"{path}.differences[{index}]"
        difference = _closed(item, {"affected_ids", "kind", "span_ids", "summary"}, item_path)
        _enum(
            difference["kind"],
            {"domain", "notation", "other", "parse", "quantifier", "reference", "scope"},
            item_path + ".kind",
        )
        _string(difference["summary"], item_path + ".summary", minimum=1, maximum=4096)
        _ids(difference["affected_ids"], item_path + ".affected_ids", minimum=1, unique=True)
        _ids(difference["span_ids"], item_path + ".span_ids", unique=True)
    _span_ids(value, path)


def _shape_problem(value: object, steps: list[int]) -> dict[str, Any]:
    _step(steps, "$.problem")
    problem = _closed(value, ROOT_FIELDS, "$.problem")
    if problem["schema"] != PROBLEM_SCHEMA:
        _fail("schema", "$.problem.schema", f"expected {PROBLEM_SCHEMA}")
    shape_handlers = {
        "domains": _shape_domain,
        "expressions": _shape_expression,
        "relations": _shape_relation,
        "statements": _shape_statement,
        "definitions": _shape_definition,
        "readings": _shape_reading,
    }
    total = 0
    for registry in REGISTRIES:
        entries = _array(problem[registry], f"$.problem.{registry}")
        total += len(entries)
        handler = shape_handlers.get(registry)
        for index, record in enumerate(entries):
            path = f"$.problem.{registry}[{index}]"
            _step(steps, path)
            if handler is not None:
                handler(record, path)
            elif registry == "source_documents":
                item = _closed(record, {"byte_length", "id", "language", "media_type", "sha256"}, path)
                _identifier(item["id"], path + ".id")
                _enum(
                    item["media_type"],
                    {
                        "application/json",
                        "application/mathml+xml",
                        "application/x-latex",
                        "text/markdown",
                        "text/plain",
                    },
                    path + ".media_type",
                )
                _string(item["language"], path + ".language", minimum=1, maximum=128)
                if type(item["sha256"]) is not str or _DIGEST.fullmatch(item["sha256"]) is None:
                    _fail("schema", path + ".sha256", "invalid SHA-256")
                _exact_int(item["byte_length"], path + ".byte_length")
            elif registry == "source_spans":
                item = _closed(record, {"end_byte", "id", "source_id", "start_byte"}, path)
                _identifier(item["id"], path + ".id")
                _identifier(item["source_id"], path + ".source_id")
                _exact_int(item["start_byte"], path + ".start_byte")
                _exact_int(item["end_byte"], path + ".end_byte")
            elif registry == "variables":
                item = _closed(record, {"domain_id", "id", "name", "role", "span_ids"}, path)
                _identifier(item["id"], path + ".id")
                _string(item["name"], path + ".name", minimum=1, maximum=1024)
                _identifier(item["domain_id"], path + ".domain_id")
                _enum(item["role"], {"bound", "free", "index", "parameter", "witness"}, path + ".role")
                _span_ids(item, path)
            elif registry == "assumptions":
                item = _closed(record, {"id", "role", "span_ids", "statement_id"}, path)
                _identifier(item["id"], path + ".id")
                _identifier(item["statement_id"], path + ".statement_id")
                _enum(item["role"], {"domain_constraint", "given", "side_condition"}, path + ".role")
                _span_ids(item, path)
            elif registry == "goals":
                item = _closed(record, {"id", "mode", "span_ids", "statement_id"}, path)
                _identifier(item["id"], path + ".id")
                _identifier(item["statement_id"], path + ".statement_id")
                _enum(
                    item["mode"],
                    {"classify", "compute", "find_witness", "optimize", "prove", "refute"},
                    path + ".mode",
                )
                _span_ids(item, path)
    if total > MAX_ENTITIES:
        _fail("budget", "$.problem", "combined entity count exceeds 100000")
    readings = problem["readings"]
    if not readings:
        _fail("schema", "$.problem.readings", "at least one reading is required")
    ambiguity = _closed(
        problem["ambiguity"],
        {"candidate_reading_ids", "required_choice", "selected_reading_id", "status"},
        "$.problem.ambiguity",
    )
    _enum(ambiguity["status"], {"resolved", "unambiguous", "unresolved"}, "$.problem.ambiguity.status")
    _ids(
        ambiguity["candidate_reading_ids"],
        "$.problem.ambiguity.candidate_reading_ids",
        minimum=1,
        unique=True,
    )
    if ambiguity["selected_reading_id"] is not None:
        _identifier(ambiguity["selected_reading_id"], "$.problem.ambiguity.selected_reading_id")
    if ambiguity["required_choice"] is not None:
        _string(ambiguity["required_choice"], "$.problem.ambiguity.required_choice")
    if type(problem["extensions"]) is not dict:
        _fail("schema", "$.problem.extensions", "extensions must be an object")
    for key, item in problem["extensions"].items():
        _step(steps, "$.problem.extensions")
        _namespace(key, "$.problem.extensions.<key>")
        _canonical_value(item, f"$.problem.extensions.{key}", steps=steps)
    return problem


def _sort_unique_strings(value: object, path: str) -> list[str]:
    if type(value) is not list:
        _fail("schema", path, "expected an array")
    for index, item in enumerate(value):
        if type(item) is not str:
            _fail("schema", f"{path}[{index}]", "expected a string reference")
    return sorted(set(value))


def _prepare_problem(value: object, steps: list[int]) -> dict[str, Any]:
    _step(steps, "$.problem")
    if type(value) is not dict:
        _fail("schema", "$.problem", "expected a problem object")
    if set(value) != ROOT_FIELDS:
        _closed(value, ROOT_FIELDS, "$.problem")
    for registry in REGISTRIES:
        entries = value[registry]
        if type(entries) is not list:
            _fail("schema", f"$.problem.{registry}", "expected an array")
        for index, item in enumerate(entries):
            _step(steps, f"$.problem.{registry}[{index}]")
            if type(item) is not dict or type(item.get("id")) is not str:
                _fail("schema", f"$.problem.{registry}[{index}]", "entity requires a string id")
        entries.sort(key=lambda item: item["id"])
    for registry in REGISTRIES[2:]:
        for item in value[registry]:
            _step(steps, f"$.problem.{registry}")
            if "span_ids" in item:
                item["span_ids"] = _sort_unique_strings(
                    item["span_ids"], f"$.problem.{registry}.{item['id']}.span_ids"
                )
    for domain in value["domains"]:
        _step(steps, "$.problem.domains")
        if domain.get("kind") == "finite" and "element_expr_ids" in domain:
            domain["element_expr_ids"] = _sort_unique_strings(
                domain["element_expr_ids"],
                f"$.problem.domains.{domain['id']}.element_expr_ids",
            )
    for reading in value["readings"]:
        _step(steps, "$.problem.readings")
        for field in ("definition_ids", "assumption_ids"):
            if field in reading:
                reading[field] = _sort_unique_strings(
                    reading[field], f"$.problem.readings.{reading['id']}.{field}"
                )
        differences = reading.get("differences")
        if type(differences) is list:
            for index, difference in enumerate(differences):
                _step(steps, f"$.problem.readings.{reading['id']}.differences[{index}]")
                if type(difference) is not dict:
                    continue
                for field in ("affected_ids", "span_ids"):
                    if field in difference:
                        difference[field] = _sort_unique_strings(
                            difference[field],
                            f"$.problem.readings.{reading['id']}.differences[{index}].{field}",
                        )
    ambiguity = value.get("ambiguity")
    if type(ambiguity) is dict and "candidate_reading_ids" in ambiguity:
        ambiguity["candidate_reading_ids"] = _sort_unique_strings(
            ambiguity["candidate_reading_ids"],
            "$.problem.ambiguity.candidate_reading_ids",
        )
    return value


def _index_registries(
    value: dict[str, Any],
    steps: list[int],
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    owners: dict[str, str] = {}
    for registry in REGISTRIES:
        entries = value[registry]
        _step(steps, f"$.problem.{registry}", len(entries) + 1)
        ids = [entry["id"] for entry in entries]
        if ids != sorted(ids):
            _fail("canonical", f"$.problem.{registry}", "registry must be sorted by id")
        if len(ids) != len(set(ids)):
            _fail("identity", f"$.problem.{registry}", "duplicate entity id")
        for entity_id in ids:
            if entity_id in owners:
                _fail(
                    "identity",
                    f"$.problem.{registry}",
                    f"id {entity_id!r} already belongs to {owners[entity_id]}",
                )
            owners[entity_id] = registry
        indexes[registry] = {entry["id"]: entry for entry in entries}
    return indexes, owners


def _require_ref(index: dict[str, Any], reference: str | None, path: str) -> None:
    if reference is not None and reference not in index:
        _fail("reference", path, f"unknown reference {reference!r}")


def _require_refs(index: dict[str, Any], references: list[str], path: str) -> None:
    for position, reference in enumerate(references):
        _require_ref(index, reference, f"{path}[{position}]")


def _sorted_unique(references: list[str], path: str) -> None:
    if references != sorted(set(references)):
        _fail("canonical", path, "set-valued references must be sorted and unique")


def _literal(expression: dict[str, Any], domains: dict[str, dict[str, Any]], path: str) -> None:
    kind = expression["literal_type"]
    value = expression["value"]
    domain = domains[expression["domain_id"]]
    builtin = domain.get("name") if domain.get("kind") == "builtin" else None
    compatible = {
        "boolean": {"boolean"},
        "integer": {"complex", "integer", "natural", "rational", "real"},
        "rational": {"complex", "rational", "real"},
        "string": set(),
    }
    if kind != "string" and builtin not in compatible[kind]:
        _fail("semantic", path, "literal type is incompatible with its domain")
    if kind == "string" and domain.get("kind") != "structure":
        _fail("semantic", path, "string literal requires a named structure domain")
    if kind in {"integer", "rational"}:
        components = value.removeprefix("-").split("/")
        if any(len(component) > MAX_NUMERIC_DIGITS for component in components):
            _fail("budget", path, "numeric literal component exceeds 4096 digits")
    if kind == "boolean" and value not in {"false", "true"}:
        _fail("semantic", path, "boolean literal must be true or false")
    if kind == "integer" and re.fullmatch(r"0|-?[1-9][0-9]*", value) is None:
        _fail("semantic", path, "integer literal is not canonical")
    if kind == "integer" and builtin == "natural" and int(value) < 0:
        _fail("semantic", path, "natural literal cannot be negative")
    if kind == "rational":
        match = re.fullmatch(r"(-?)(0|[1-9][0-9]*)/([1-9][0-9]*)", value)
        if match is None:
            _fail("semantic", path, "rational literal is not canonical")
        numerator = int(("-" if match.group(1) else "") + match.group(2))
        denominator = int(match.group(3))
        if numerator == 0 or denominator == 1 or math.gcd(abs(numerator), denominator) != 1:
            _fail("semantic", path, "rational literal must be non-integral and reduced")


def _references(
    value: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
    owners: dict[str, str],
    steps: list[int],
) -> None:
    sources = indexes["source_documents"]
    spans = indexes["source_spans"]
    domains = indexes["domains"]
    variables = indexes["variables"]
    expressions = indexes["expressions"]
    relations = indexes["relations"]
    statements = indexes["statements"]
    definitions = indexes["definitions"]
    assumptions = indexes["assumptions"]
    goals = indexes["goals"]
    readings = indexes["readings"]

    for registry in REGISTRIES[2:]:
        for entity in value[registry]:
            path = f"$.problem.{registry}.{entity['id']}.span_ids"
            span_ids = entity.get("span_ids", [])
            _step(steps, path, len(span_ids) + 1)
            _sorted_unique(span_ids, path)
            _require_refs(spans, span_ids, path)
    for span in value["source_spans"]:
        path = f"$.problem.source_spans.{span['id']}"
        _step(steps, path)
        source = sources.get(span["source_id"])
        if source is None:
            _fail("reference", path + ".source_id", "unknown source")
        if span["start_byte"] > span["end_byte"] or span["end_byte"] > source["byte_length"]:
            _fail("semantic", path, "span lies outside source bytes")
    for domain in value["domains"]:
        path = f"$.problem.domains.{domain['id']}"
        _step(steps, path)
        kind = domain["kind"]
        if kind == "finite":
            _require_ref(domains, domain["element_domain_id"], path + ".element_domain_id")
            _require_refs(expressions, domain["element_expr_ids"], path + ".element_expr_ids")
            if domain["cardinality"] != len(domain["element_expr_ids"]):
                _fail("semantic", path, "finite cardinality must equal the element count")
            if any(
                expressions[item]["domain_id"] != domain["element_domain_id"]
                for item in domain["element_expr_ids"]
            ):
                _fail("semantic", path, "finite elements use the wrong domain")
        elif kind == "interval":
            _require_ref(expressions, domain["lower_expr_id"], path + ".lower_expr_id")
            _require_ref(expressions, domain["upper_expr_id"], path + ".upper_expr_id")
            if domain["lower_expr_id"] is None and domain["upper_expr_id"] is None:
                _fail("semantic", path, "fully unbounded interval must use a builtin domain")
            if domain["lower_expr_id"] is None and domain["lower_closed"]:
                _fail("semantic", path, "absent lower bound cannot be closed")
            if domain["upper_expr_id"] is None and domain["upper_closed"]:
                _fail("semantic", path, "absent upper bound cannot be closed")
            for bound in (domain["lower_expr_id"], domain["upper_expr_id"]):
                if bound is None:
                    continue
                bound_domain = domains[expressions[bound]["domain_id"]]
                if bound_domain.get("kind") != "builtin" or bound_domain.get("name") != domain["base"]:
                    _fail("semantic", path, "interval bound domain drift")
        elif kind == "modular":
            _require_ref(expressions, domain["modulus_expr_id"], path + ".modulus_expr_id")
            modulus = expressions[domain["modulus_expr_id"]]
            modulus_domain = domains[modulus["domain_id"]]
            if modulus_domain.get("kind") != "builtin" or modulus_domain.get("name") not in {
                "integer",
                "natural",
            }:
                _fail("semantic", path, "modulus must have an integral domain")
            if (
                modulus["kind"] == "literal"
                and modulus["literal_type"] == "integer"
                and int(modulus["value"]) <= 1
            ):
                _fail("semantic", path, "literal modulus must exceed one")
        elif kind == "collection":
            _require_ref(domains, domain["element_domain_id"], path + ".element_domain_id")
        elif kind == "product":
            _require_refs(domains, domain["factor_domain_ids"], path + ".factor_domain_ids")
        elif kind == "function":
            _require_refs(domains, domain["parameter_domain_ids"], path + ".parameter_domain_ids")
            _require_ref(domains, domain["result_domain_id"], path + ".result_domain_id")
        elif kind == "structure":
            _require_refs(domains, domain["parameter_domain_ids"], path + ".parameter_domain_ids")
            _require_refs(expressions, domain["parameter_expr_ids"], path + ".parameter_expr_ids")
    for variable in value["variables"]:
        _step(steps, f"$.problem.variables.{variable['id']}")
        _require_ref(
            domains,
            variable["domain_id"],
            f"$.problem.variables.{variable['id']}.domain_id",
        )
    for expression in value["expressions"]:
        path = f"$.problem.expressions.{expression['id']}"
        _step(steps, path)
        _require_ref(domains, expression["domain_id"], path + ".domain_id")
        kind = expression["kind"]
        if kind == "literal":
            _literal(expression, domains, path)
        elif kind == "variable":
            _require_ref(variables, expression["variable_id"], path + ".variable_id")
            if expression["domain_id"] != variables[expression["variable_id"]]["domain_id"]:
                _fail("semantic", path, "variable expression domain drift")
        elif kind == "apply":
            _require_refs(expressions, expression["argument_expr_ids"], path + ".argument_expr_ids")
        elif kind in {"collection", "tuple"}:
            _require_refs(expressions, expression["element_expr_ids"], path + ".element_expr_ids")
            expression_domain = domains[expression["domain_id"]]
            if kind == "tuple":
                actual = [expressions[item]["domain_id"] for item in expression["element_expr_ids"]]
                if expression_domain.get("kind") != "product" or actual != expression_domain.get(
                    "factor_domain_ids"
                ):
                    _fail("semantic", path, "tuple elements do not match product domain")
            elif expression_domain.get("kind") != "collection" or any(
                expressions[item]["domain_id"] != expression_domain.get("element_domain_id")
                for item in expression["element_expr_ids"]
            ):
                _fail("semantic", path, "collection elements do not match domain")
        elif kind == "conditional":
            _require_ref(
                statements,
                expression["condition_statement_id"],
                path + ".condition_statement_id",
            )
            _require_ref(expressions, expression["then_expr_id"], path + ".then_expr_id")
            _require_ref(expressions, expression["else_expr_id"], path + ".else_expr_id")
            if any(
                expressions[item]["domain_id"] != expression["domain_id"]
                for item in (expression["then_expr_id"], expression["else_expr_id"])
            ):
                _fail("semantic", path, "conditional branch domain drift")
    for relation in value["relations"]:
        path = f"$.problem.relations.{relation['id']}"
        operands = relation["operand_expr_ids"]
        _step(steps, path, len(operands) + 1)
        _require_refs(expressions, operands, path + ".operand_expr_ids")
        expected = 3 if relation["kind"] == "congruent" else 2
        if relation["kind"] != "predicate" and len(operands) != expected:
            _fail("semantic", path, f"{relation['kind']} requires {expected} operands")
        operand_domains = [domains[expressions[item]["domain_id"]] for item in operands]
        operand_domain_ids = [expressions[item]["domain_id"] for item in operands]
        if relation["kind"] in {"equal", "not_equal"} and len(set(operand_domain_ids)) != 1:
            _fail("semantic", path, "equality operands require one exact domain")
        if relation["kind"] in {"greater", "greater_equal", "less", "less_equal"} and any(
            domain.get("kind") != "builtin"
            or domain.get("name") not in {"integer", "natural", "rational", "real"}
            for domain in operand_domains
        ):
            _fail("semantic", path, "ordered comparison requires ordered numeric domains")
        if relation["kind"] in {"congruent", "divides"} and any(
            domain.get("kind") != "builtin" or domain.get("name") not in {"integer", "natural"}
            for domain in operand_domains
        ):
            _fail("semantic", path, "arithmetic relation requires integral operands")
        if relation["kind"] in {"member", "not_member"}:
            container = operand_domains[1]
            if (
                container.get("kind") != "collection"
                or operand_domain_ids[0] != container.get("element_domain_id")
            ):
                _fail("semantic", path, "membership operands do not match collection domain")
    for statement in value["statements"]:
        path = f"$.problem.statements.{statement['id']}"
        _step(steps, path)
        if statement["kind"] == "relation":
            _require_ref(relations, statement["relation_id"], path + ".relation_id")
        elif statement["kind"] == "logical":
            operands = statement["operand_statement_ids"]
            _require_refs(statements, operands, path + ".operand_statement_ids")
            expected = {"iff": 2, "implies": 2, "not": 1}.get(statement["operator"])
            if expected is not None and len(operands) != expected:
                _fail("semantic", path, f"{statement['operator']} requires {expected} operands")
            if statement["operator"] in {"and", "or"} and len(operands) < 2:
                _fail("semantic", path, f"{statement['operator']} requires at least 2 operands")
        elif statement["kind"] == "quantified":
            _require_refs(variables, statement["variable_ids"], path + ".variable_ids")
            _require_ref(statements, statement["body_statement_id"], path + ".body_statement_id")
    for definition in value["definitions"]:
        path = f"$.problem.definitions.{definition['id']}"
        _step(steps, path)
        _require_refs(
            variables,
            definition["parameter_variable_ids"],
            path + ".parameter_variable_ids",
        )
        _require_ref(domains, definition["result_domain_id"], path + ".result_domain_id")
        body = definition["body"]
        if body["kind"] == "expression":
            _require_ref(expressions, body["expression_id"], path + ".body.expression_id")
            if (
                definition["result_domain_id"] is None
                or expressions[body["expression_id"]]["domain_id"]
                != definition["result_domain_id"]
            ):
                _fail("semantic", path, "expression definition result domain drift")
        else:
            _require_ref(statements, body["statement_id"], path + ".body.statement_id")
            if definition["result_domain_id"] is not None:
                _fail("semantic", path, "statement definition cannot declare a result domain")
    for assumption in value["assumptions"]:
        _step(steps, f"$.problem.assumptions.{assumption['id']}")
        _require_ref(
            statements,
            assumption["statement_id"],
            f"$.problem.assumptions.{assumption['id']}.statement_id",
        )
    for goal in value["goals"]:
        _step(steps, f"$.problem.goals.{goal['id']}")
        _require_ref(
            statements,
            goal["statement_id"],
            f"$.problem.goals.{goal['id']}.statement_id",
        )
    for reading in value["readings"]:
        path = f"$.problem.readings.{reading['id']}"
        _step(
            steps,
            path,
            len(reading["definition_ids"])
            + len(reading["assumption_ids"])
            + len(reading["goal_ids"])
            + 1,
        )
        _sorted_unique(reading["definition_ids"], path + ".definition_ids")
        _sorted_unique(reading["assumption_ids"], path + ".assumption_ids")
        _require_refs(definitions, reading["definition_ids"], path + ".definition_ids")
        _require_refs(assumptions, reading["assumption_ids"], path + ".assumption_ids")
        _require_refs(goals, reading["goal_ids"], path + ".goal_ids")
        _require_ref(readings, reading["difference_from"], path + ".difference_from")
        if reading["difference_from"] == reading["id"]:
            _fail("semantic", path, "reading cannot differ from itself")
        if reading["difference_from"] is None and reading["differences"]:
            _fail("semantic", path, "base reading cannot declare relative differences")
        if reading["difference_from"] is not None and not reading["differences"]:
            _fail("semantic", path, "alternative reading must explain differences")
        for number, difference in enumerate(reading["differences"]):
            _step(
                steps,
                f"{path}.differences[{number}]",
                len(difference["affected_ids"]) + len(difference["span_ids"]) + 1,
            )
            affected_path = f"{path}.differences[{number}].affected_ids"
            _sorted_unique(difference["affected_ids"], affected_path)
            for affected in difference["affected_ids"]:
                if affected not in owners:
                    _fail("reference", affected_path, f"unknown affected id {affected!r}")
            difference_spans = f"{path}.differences[{number}].span_ids"
            _sorted_unique(difference["span_ids"], difference_spans)
            _require_refs(spans, difference["span_ids"], difference_spans)


def _acyclic(value: dict[str, Any], steps: list[int]) -> None:
    graph: dict[str, list[str]] = {}
    for domain in value["domains"]:
        _step(steps, f"$.problem.domains.{domain['id']}")
        node = "domain:" + domain["id"]
        kind = domain["kind"]
        dependencies: list[str] = []
        if kind == "finite":
            dependencies = ["domain:" + domain["element_domain_id"]]
            dependencies.extend("expr:" + item for item in domain["element_expr_ids"])
        elif kind == "interval":
            dependencies = [
                "expr:" + item
                for item in (domain["lower_expr_id"], domain["upper_expr_id"])
                if item is not None
            ]
        elif kind == "modular":
            dependencies = ["expr:" + domain["modulus_expr_id"]]
        elif kind == "collection":
            dependencies = ["domain:" + domain["element_domain_id"]]
        elif kind == "product":
            dependencies = ["domain:" + item for item in domain["factor_domain_ids"]]
        elif kind == "function":
            dependencies = ["domain:" + item for item in domain["parameter_domain_ids"]]
            dependencies.append("domain:" + domain["result_domain_id"])
        elif kind == "structure":
            dependencies = ["domain:" + item for item in domain["parameter_domain_ids"]]
            dependencies.extend("expr:" + item for item in domain["parameter_expr_ids"])
        graph[node] = dependencies
    for expression in value["expressions"]:
        _step(steps, f"$.problem.expressions.{expression['id']}")
        node = "expr:" + expression["id"]
        dependencies = ["domain:" + expression["domain_id"]]
        if expression["kind"] == "apply":
            dependencies.extend("expr:" + item for item in expression["argument_expr_ids"])
        elif expression["kind"] in {"collection", "tuple"}:
            dependencies.extend("expr:" + item for item in expression["element_expr_ids"])
        elif expression["kind"] == "conditional":
            dependencies.extend(
                [
                    "stmt:" + expression["condition_statement_id"],
                    "expr:" + expression["then_expr_id"],
                    "expr:" + expression["else_expr_id"],
                ]
            )
        graph[node] = dependencies
    for relation in value["relations"]:
        _step(steps, f"$.problem.relations.{relation['id']}")
        graph["rel:" + relation["id"]] = [
            "expr:" + item for item in relation["operand_expr_ids"]
        ]
    for statement in value["statements"]:
        _step(steps, f"$.problem.statements.{statement['id']}")
        node = "stmt:" + statement["id"]
        if statement["kind"] == "relation":
            graph[node] = ["rel:" + statement["relation_id"]]
        elif statement["kind"] == "logical":
            graph[node] = ["stmt:" + item for item in statement["operand_statement_ids"]]
        elif statement["kind"] == "quantified":
            graph[node] = ["stmt:" + statement["body_statement_id"]]
        else:
            graph[node] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str, depth: int) -> None:
        _step(steps, "$.problem")
        if depth > MAX_DEPTH:
            _fail("budget", "$.problem", "ProblemIR dependency nesting exceeds 512")
        if node in visiting:
            _fail("semantic", "$.problem", f"cyclic ProblemIR graph at {node}")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            visit(dependency, depth + 1)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node, 0)


def _scope(
    value: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> None:
    variables = indexes["variables"]
    expressions = indexes["expressions"]
    relations = indexes["relations"]
    statements = indexes["statements"]
    binder_owner: dict[str, str] = {}
    for statement in value["statements"]:
        _step(steps, f"$.problem.statements.{statement['id']}")
        if statement["kind"] != "quantified":
            continue
        for variable_id in statement["variable_ids"]:
            _step(steps, f"$.problem.statements.{statement['id']}.variable_ids")
            variable = variables[variable_id]
            if variable["role"] != "bound":
                _fail(
                    "semantic",
                    f"$.problem.statements.{statement['id']}",
                    "binder variable is not bound",
                )
            if variable_id in binder_owner:
                _fail(
                    "semantic",
                    f"$.problem.statements.{statement['id']}",
                    "bound variable has two owners",
                )
            binder_owner[variable_id] = statement["id"]
    parameter_owner: dict[str, str] = {}
    for definition in value["definitions"]:
        _step(steps, f"$.problem.definitions.{definition['id']}")
        for variable_id in definition["parameter_variable_ids"]:
            _step(steps, f"$.problem.definitions.{definition['id']}.parameter_variable_ids")
            variable = variables[variable_id]
            if variable["role"] != "parameter":
                _fail(
                    "semantic",
                    f"$.problem.definitions.{definition['id']}",
                    "parameter role mismatch",
                )
            if variable_id in parameter_owner:
                _fail(
                    "semantic",
                    f"$.problem.definitions.{definition['id']}",
                    "parameter has two owners",
                )
            parameter_owner[variable_id] = definition["id"]
    for variable in value["variables"]:
        _step(steps, f"$.problem.variables.{variable['id']}")
        if variable["role"] == "bound" and variable["id"] not in binder_owner:
            _fail(
                "semantic",
                f"$.problem.variables.{variable['id']}",
                "bound variable has no binder",
            )
        if variable["role"] == "parameter" and variable["id"] not in parameter_owner:
            _fail(
                "semantic",
                f"$.problem.variables.{variable['id']}",
                "parameter has no definition",
            )

    def expression_scope(
        expression_id: str,
        allowed: frozenset[str],
        trail: frozenset[str],
        depth: int,
    ) -> None:
        _step(steps, f"$.problem.expressions.{expression_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$.problem.expressions", "scope nesting exceeds 512")
        if expression_id in trail:
            return
        expression = expressions[expression_id]
        kind = expression["kind"]
        if kind == "variable":
            variable = variables[expression["variable_id"]]
            if variable["role"] in {"bound", "parameter"} and variable["id"] not in allowed:
                _fail(
                    "semantic",
                    f"$.problem.expressions.{expression_id}",
                    "variable escapes its scope",
                )
        elif kind == "apply":
            for child in expression["argument_expr_ids"]:
                expression_scope(child, allowed, trail | {expression_id}, depth + 1)
        elif kind in {"collection", "tuple"}:
            for child in expression["element_expr_ids"]:
                expression_scope(child, allowed, trail | {expression_id}, depth + 1)
        elif kind == "conditional":
            statement_scope(expression["condition_statement_id"], allowed, frozenset(), depth + 1)
            expression_scope(
                expression["then_expr_id"],
                allowed,
                trail | {expression_id},
                depth + 1,
            )
            expression_scope(
                expression["else_expr_id"],
                allowed,
                trail | {expression_id},
                depth + 1,
            )

    def statement_scope(
        statement_id: str,
        allowed: frozenset[str],
        trail: frozenset[str],
        depth: int,
    ) -> None:
        _step(steps, f"$.problem.statements.{statement_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$.problem.statements", "scope nesting exceeds 512")
        if statement_id in trail:
            return
        statement = statements[statement_id]
        kind = statement["kind"]
        if kind == "relation":
            for expression_id in relations[statement["relation_id"]]["operand_expr_ids"]:
                expression_scope(expression_id, allowed, frozenset(), depth + 1)
        elif kind == "logical":
            for child in statement["operand_statement_ids"]:
                statement_scope(child, allowed, trail | {statement_id}, depth + 1)
        elif kind == "quantified":
            statement_scope(
                statement["body_statement_id"],
                allowed | frozenset(statement["variable_ids"]),
                trail | {statement_id},
                depth + 1,
            )

    for assumption in value["assumptions"]:
        _step(steps, f"$.problem.assumptions.{assumption['id']}")
        statement_scope(assumption["statement_id"], frozenset(), frozenset(), 0)
    for goal in value["goals"]:
        _step(steps, f"$.problem.goals.{goal['id']}")
        statement_scope(goal["statement_id"], frozenset(), frozenset(), 0)
    for definition in value["definitions"]:
        _step(steps, f"$.problem.definitions.{definition['id']}")
        allowed = frozenset(definition["parameter_variable_ids"])
        if definition["body"]["kind"] == "expression":
            expression_scope(definition["body"]["expression_id"], allowed, frozenset(), 0)
        else:
            statement_scope(definition["body"]["statement_id"], allowed, frozenset(), 0)


def _ambiguity(
    value: dict[str, Any],
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> None:
    readings = indexes["readings"]
    ambiguity = value["ambiguity"]
    candidates = ambiguity["candidate_reading_ids"]
    _step(steps, "$.problem.ambiguity", len(candidates) + len(readings) + 1)
    _sorted_unique(candidates, "$.problem.ambiguity.candidate_reading_ids")
    if candidates != sorted(readings):
        _fail(
            "semantic",
            "$.problem.ambiguity",
            "candidate list must name every reading exactly once",
        )
    status = ambiguity["status"]
    selected = ambiguity["selected_reading_id"]
    choice = ambiguity["required_choice"]
    if status == "unambiguous":
        if len(candidates) != 1 or selected != candidates[0] or choice is not None:
            _fail(
                "semantic",
                "$.problem.ambiguity",
                "unambiguous state must select its sole reading",
            )
        reading = readings[candidates[0]]
        if reading["difference_from"] is not None or reading["differences"]:
            _fail(
                "semantic",
                "$.problem.ambiguity",
                "unambiguous reading cannot carry alternatives",
            )
    elif status == "unresolved":
        if len(candidates) < 2 or selected is not None or type(choice) is not str or not choice:
            _fail(
                "semantic",
                "$.problem.ambiguity",
                "unresolved ambiguity needs alternatives and a choice",
            )
    elif len(candidates) < 2 or selected not in readings or choice is not None:
        _fail(
            "semantic",
            "$.problem.ambiguity",
            "resolved ambiguity must select one candidate",
        )
    if len(candidates) > 1:
        bases = [reading for reading in value["readings"] if reading["difference_from"] is None]
        alternatives = [
            reading for reading in value["readings"] if reading["difference_from"] is not None
        ]
        if len(bases) != 1 or not alternatives:
            _fail(
                "semantic",
                "$.problem.readings",
                "ambiguous IR needs one base and explained alternatives",
            )


def _validate_problem(value: dict[str, Any], steps: list[int]) -> None:
    indexes, owners = _index_registries(value, steps)
    _references(value, indexes, owners, steps)
    _acyclic(value, steps)
    _scope(value, indexes, steps)
    _ambiguity(value, indexes, steps)


def _diagnostic(error: _ProblemError) -> ProblemIntakeDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "canonical": "INVALID_CANONICAL_VALUE",
        "identity": "INVALID_PROBLEM",
        "reference": "INVALID_REFERENCE",
        "schema": "INVALID_SCHEMA",
        "semantic": "INVALID_SEMANTICS",
        "type": "INVALID_TYPE",
    }.get(error.kind, "INVALID_PROBLEM")
    path = error.path if _PATH.fullmatch(error.path) is not None else "$"
    message = error.detail[:MAX_DIAGNOSTIC_CODEPOINTS] or "invalid structured problem"
    return ProblemIntakeDiagnostic(code=code, message=message, path=path)


def _new_result(
    *,
    status: str,
    reason_code: str,
    diagnostics: tuple[ProblemIntakeDiagnostic, ...],
    problem_ir_bytes: bytes | None,
    problem_ir_sha256: str | None,
) -> ProblemIntakeResult:
    result = ProblemIntakeResult(
        status=status,
        reason_code=reason_code,
        diagnostics=diagnostics,
        problem_ir_bytes=problem_ir_bytes,
        problem_ir_sha256=problem_ir_sha256,
        _token=_RESULT_TOKEN,
    )
    validate_problem_intake_result(result)
    return result


def intake_problem(specification: dict[str, object]) -> ProblemIntakeResult:
    """Convert one exact structured Python envelope into canonical ProblemIR.

    Success establishes representation validity only.  All ordinary input
    failures are returned as closed, non-authoritative results.
    """
    try:
        steps = [0]
        if type(specification) is not dict:
            _fail("type", "$", "specification must be an exact built-in dict")
        normalized = _normalize_exact(specification, steps=steps)
        assert type(normalized) is dict
        if set(normalized) != {"problem", "schema"}:
            _closed(normalized, {"problem", "schema"}, "$")
        if normalized["schema"] != INTAKE_SCHEMA:
            _fail("schema", "$.schema", f"expected {INTAKE_SCHEMA}")
        input_bytes = _canonical_bytes(normalized)
        if len(input_bytes) > MAX_INPUT_BYTES:
            _fail("budget", "$", "canonical input exceeds 67108864 bytes")
        problem = _prepare_problem(normalized["problem"], steps)
        _shape_problem(problem, steps)
        _validate_problem(problem, steps)
        problem_bytes = _canonical_bytes(problem)
        return _new_result(
            status="accepted",
            reason_code="ACCEPTED",
            diagnostics=(),
            problem_ir_bytes=problem_bytes,
            problem_ir_sha256=_sha(problem_bytes),
        )
    except _ProblemError as error:
        diagnostic = _diagnostic(error)
        return _new_result(
            status="exhausted" if error.kind == "budget" else "invalid",
            reason_code=diagnostic.code,
            diagnostics=(diagnostic,),
            problem_ir_bytes=None,
            problem_ir_sha256=None,
        )
    except RecursionError:
        return _new_result(
            status="exhausted",
            reason_code="BUDGET_EXHAUSTED",
            diagnostics=(
                ProblemIntakeDiagnostic(
                    code="BUDGET_EXHAUSTED",
                    message="recursive validation exceeded the structural budget",
                    path="$",
                ),
            ),
            problem_ir_bytes=None,
            problem_ir_sha256=None,
        )


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProblemIntakeValidationError("schema", "$", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _load_canonical_bytes(data: object, *, maximum: int) -> dict[str, Any]:
    if type(data) is not bytes:
        raise ProblemIntakeValidationError("type", "$", "result must be exact bytes")
    if len(data) > maximum:
        raise ProblemIntakeValidationError("budget", "$", "result byte budget exceeded")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except ProblemIntakeValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProblemIntakeValidationError("schema", "$", "invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ProblemIntakeValidationError("schema", "$", "result root must be an object")
    try:
        canonical = _canonical_bytes(value)
    except _ProblemError as exc:
        raise ProblemIntakeValidationError(exc.kind, exc.path, exc.detail) from exc
    if data != canonical:
        raise ProblemIntakeValidationError("canonical", "$", "result bytes are not canonical")
    return value


def _decode_problem_bytes(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except ProblemIntakeValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProblemIntakeValidationError("schema", "$.problem_ir", "invalid ProblemIR") from exc
    if type(value) is not dict:
        raise ProblemIntakeValidationError("schema", "$.problem_ir", "ProblemIR must be an object")
    try:
        steps = [0]
        normalized = _normalize_exact(value, path="$.problem_ir", steps=steps)
        if normalized != value:
            raise ProblemIntakeValidationError(
                "canonical", "$.problem_ir", "ProblemIR strings are not canonical NFC"
            )
        if _canonical_bytes(value) != data:
            raise ProblemIntakeValidationError(
                "canonical", "$.problem_ir", "ProblemIR bytes are not canonical"
            )
        _shape_problem(value, steps)
        _validate_problem(value, steps)
    except _ProblemError as exc:
        raise ProblemIntakeValidationError(exc.kind, exc.path, exc.detail) from exc
    return value


def validate_problem_intake_result(result: object) -> None:
    """Recompute a complete in-memory result before it is consumed."""
    if type(result) is not ProblemIntakeResult:
        raise ProblemIntakeValidationError("type", "$", "expected exact ProblemIntakeResult")
    expected_constants = {
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "mathematical_authority": False,
        "problem_ir_contract_sha256": PROBLEM_IR_CONTRACT_SHA256,
        "problem_ir_schema_sha256": PROBLEM_IR_SCHEMA_SHA256,
        "schema": RESULT_SCHEMA,
    }
    for field, expected in expected_constants.items():
        try:
            actual = getattr(result, field)
        except AttributeError as exc:
            raise ProblemIntakeValidationError("result", "$", f"missing result field {field}") from exc
        if type(actual) is not type(expected) or actual != expected:
            raise ProblemIntakeValidationError("result", f"$.{field}", "result binding drift")
    if result.status not in {"accepted", "exhausted", "invalid"}:
        raise ProblemIntakeValidationError("result", "$.status", "unknown result status")
    reason_codes = {
        "ACCEPTED",
        "BUDGET_EXHAUSTED",
        "INVALID_CANONICAL_VALUE",
        "INVALID_PROBLEM",
        "INVALID_REFERENCE",
        "INVALID_SCHEMA",
        "INVALID_SEMANTICS",
        "INVALID_TYPE",
    }
    if type(result.reason_code) is not str or result.reason_code not in reason_codes:
        raise ProblemIntakeValidationError("result", "$.reason_code", "unknown reason code")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > MAX_DIAGNOSTICS:
        raise ProblemIntakeValidationError("result", "$.diagnostics", "invalid diagnostics tuple")
    for index, diagnostic in enumerate(result.diagnostics):
        path = f"$.diagnostics[{index}]"
        if type(diagnostic) is not ProblemIntakeDiagnostic:
            raise ProblemIntakeValidationError("result", path, "invalid diagnostic value")
        if diagnostic.code not in reason_codes - {"ACCEPTED"}:
            raise ProblemIntakeValidationError("result", path + ".code", "invalid diagnostic code")
        if (
            type(diagnostic.message) is not str
            or not diagnostic.message
            or len(diagnostic.message) > MAX_DIAGNOSTIC_CODEPOINTS
            or "\x00" in diagnostic.message
            or unicodedata.normalize("NFC", diagnostic.message) != diagnostic.message
        ):
            raise ProblemIntakeValidationError("result", path + ".message", "invalid message")
        if type(diagnostic.path) is not str or _PATH.fullmatch(diagnostic.path) is None:
            raise ProblemIntakeValidationError("result", path + ".path", "invalid JSON path")
    if result.status == "accepted":
        if result.reason_code != "ACCEPTED" or result.diagnostics:
            raise ProblemIntakeValidationError("result", "$", "accepted result combination drift")
        if type(result.problem_ir_bytes) is not bytes or len(result.problem_ir_bytes) > MAX_OUTPUT_BYTES:
            raise ProblemIntakeValidationError("result", "$.problem_ir", "missing ProblemIR bytes")
        if type(result.problem_ir_sha256) is not str or _DIGEST.fullmatch(
            result.problem_ir_sha256
        ) is None:
            raise ProblemIntakeValidationError("result", "$.problem_ir_sha256", "invalid digest")
        _decode_problem_bytes(result.problem_ir_bytes)
        if _sha(result.problem_ir_bytes) != result.problem_ir_sha256:
            raise ProblemIntakeValidationError(
                "identity", "$.problem_ir_sha256", "ProblemIR digest drift"
            )
        return
    if result.problem_ir_bytes is not None or result.problem_ir_sha256 is not None:
        raise ProblemIntakeValidationError("result", "$", "failed result contains ProblemIR")
    if not result.diagnostics or result.diagnostics[0].code != result.reason_code:
        raise ProblemIntakeValidationError("result", "$", "failed result diagnostic drift")
    if result.status == "exhausted" and result.reason_code != "BUDGET_EXHAUSTED":
        raise ProblemIntakeValidationError("result", "$", "exhausted reason drift")
    if result.status == "invalid" and result.reason_code in {"ACCEPTED", "BUDGET_EXHAUSTED"}:
        raise ProblemIntakeValidationError("result", "$", "invalid reason drift")


def canonical_problem_ir_bytes(result: ProblemIntakeResult) -> bytes:
    """Return exact accepted ProblemIR bytes after complete revalidation."""
    validate_problem_intake_result(result)
    if result.status != "accepted" or result.problem_ir_bytes is None:
        raise ProblemIntakeValidationError("result", "$", "result has no accepted ProblemIR")
    return result.problem_ir_bytes


def _result_mapping(result: ProblemIntakeResult) -> dict[str, Any]:
    validate_problem_intake_result(result)
    problem = (
        _decode_problem_bytes(result.problem_ir_bytes)
        if result.problem_ir_bytes is not None
        else None
    )
    return {
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "diagnostics": [
            {"code": item.code, "message": item.message, "path": item.path}
            for item in result.diagnostics
        ],
        "mathematical_authority": result.mathematical_authority,
        "problem_ir": problem,
        "problem_ir_contract_sha256": result.problem_ir_contract_sha256,
        "problem_ir_schema_sha256": result.problem_ir_schema_sha256,
        "problem_ir_sha256": result.problem_ir_sha256,
        "reason_code": result.reason_code,
        "schema": result.schema,
        "status": result.status,
    }


def problem_intake_result_bytes(result: ProblemIntakeResult) -> bytes:
    """Serialize one closed result to canonical JSON bytes."""
    try:
        return _canonical_bytes(_result_mapping(result))
    except _ProblemError as exc:
        raise ProblemIntakeValidationError(exc.kind, exc.path, exc.detail) from exc


def problem_intake_result_sha256(result: ProblemIntakeResult) -> str:
    """Return the full SHA-256 identity of canonical result bytes."""
    return _sha(problem_intake_result_bytes(result))


def parse_problem_intake_result(data: bytes) -> ProblemIntakeResult:
    """Parse canonical historical result bytes without adding authority."""
    value = _load_canonical_bytes(data, maximum=MAX_OUTPUT_BYTES)
    fields = {
        "contract_id",
        "contract_sha256",
        "diagnostics",
        "mathematical_authority",
        "problem_ir",
        "problem_ir_contract_sha256",
        "problem_ir_schema_sha256",
        "problem_ir_sha256",
        "reason_code",
        "schema",
        "status",
    }
    if set(value) != fields:
        raise ProblemIntakeValidationError("schema", "$", "result field set drift")
    raw_diagnostics = value["diagnostics"]
    if type(raw_diagnostics) is not list:
        raise ProblemIntakeValidationError("schema", "$.diagnostics", "expected an array")
    diagnostics: list[ProblemIntakeDiagnostic] = []
    for index, raw in enumerate(raw_diagnostics):
        if type(raw) is not dict or set(raw) != {"code", "message", "path"}:
            raise ProblemIntakeValidationError(
                "schema", f"$.diagnostics[{index}]", "diagnostic field drift"
            )
        diagnostics.append(
            ProblemIntakeDiagnostic(code=raw["code"], message=raw["message"], path=raw["path"])
        )
    raw_problem = value["problem_ir"]
    if raw_problem is None:
        problem_bytes = None
    else:
        try:
            problem_bytes = _canonical_bytes(raw_problem)
        except _ProblemError as exc:
            raise ProblemIntakeValidationError(exc.kind, exc.path, exc.detail) from exc
    result = ProblemIntakeResult(
        contract_id=value["contract_id"],
        contract_sha256=value["contract_sha256"],
        diagnostics=tuple(diagnostics),
        mathematical_authority=value["mathematical_authority"],
        problem_ir_bytes=problem_bytes,
        problem_ir_contract_sha256=value["problem_ir_contract_sha256"],
        problem_ir_schema_sha256=value["problem_ir_schema_sha256"],
        problem_ir_sha256=value["problem_ir_sha256"],
        reason_code=value["reason_code"],
        schema=value["schema"],
        status=value["status"],
        _token=_RESULT_TOKEN,
    )
    validate_problem_intake_result(result)
    if problem_intake_result_bytes(result) != data:
        raise ProblemIntakeValidationError("canonical", "$", "result round-trip drift")
    return result
