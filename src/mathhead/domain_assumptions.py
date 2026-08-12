"""Deterministic, non-authoritative domain and assumption normalization.

This MH-042 boundary consumes only canonical successful MH-041 result bytes.
It inventories already-declared structure independently for every reading; it
does not infer a domain, rewrite mathematics, select a reading, solve, prove,
or issue mathematical authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, Mapping, NoReturn
import unicodedata

from mathhead.problem_intake import (
    CONTRACT_ID as INTAKE_CONTRACT_ID,
    CONTRACT_SHA256 as INTAKE_CONTRACT_SHA256,
    PROBLEM_IR_CONTRACT_SHA256,
)
from mathhead.problem_readings import (
    CONTRACT_ID as READING_ANALYSIS_CONTRACT_ID,
    CONTRACT_SHA256 as READING_ANALYSIS_CONTRACT_SHA256,
    ReadingAnalysisValidationError,
    parse_reading_analysis_result,
    reading_analysis_result_bytes,
)


CONTRACT_ID: Final = "MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001"
CONTRACT_SHA256: Final = \
    "609bc3a0773016f73d4bcee21d6aef034c74bb8edb36fddd9b6df1a4f4ba219a"
RESULT_SCHEMA: Final = "mathhead.domain-assumption-result.v1"
CONTEXT_SCHEMA: Final = "mathhead.normalized-domain-context.v1"
FACT_SCHEMA: Final = "mathhead.domain-assumption-fact.v1"
RULE_CATALOGUE_SHA256: Final = \
    "4d2a14589c7ae8a4a217987f5f7ddfdfc14d7fcf170049a2c8a6c2eb90a7b0b9"

MAX_INPUT_BYTES: Final = 201_326_592
MAX_OUTPUT_BYTES: Final = 268_435_456
MAX_CANDIDATES: Final = 100_000
MAX_DOMAINS: Final = 100_000
MAX_VARIABLES: Final = 100_000
MAX_ASSUMPTIONS: Final = 100_000
MAX_FACTS: Final = 400_000
MAX_DEPENDENCIES: Final = 1_200_000
MAX_DEPTH: Final = 512
MAX_STEPS: Final = 16_000_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 16_777_216
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_DIAGNOSTIC_CODEPOINTS: Final = 512

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PATH = re.compile(r"^\$(?:\.[a-z][a-z0-9_]*|\[[0-9]+\])*$")
_RESULT_TOKEN: Final = object()

_ENTITY_REGISTRIES: Final = (
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
)
_SEMANTIC_REGISTRIES: Final = frozenset(_ENTITY_REGISTRIES[2:])

_DOMAIN_RULES: Final = {
    "builtin": ("mh.normalize.domain.builtin", "builtin_domain"),
    "finite": ("mh.normalize.domain.finite", "finite_domain"),
    "interval": ("mh.normalize.domain.interval", "interval_domain"),
    "modular": ("mh.normalize.domain.modular", "modular_domain"),
    "collection": ("mh.normalize.domain.collection", "collection_domain"),
    "product": ("mh.normalize.domain.product", "product_domain"),
    "function": ("mh.normalize.domain.function", "function_domain"),
    "structure": ("mh.normalize.domain.structure", "structure_domain"),
}
_RELATION_RULES: Final = {
    "equal": ("mh.normalize.assumption.equal", "equality_assumption"),
    "not_equal": ("mh.normalize.assumption.not-equal", "disequality_assumption"),
    "less": ("mh.normalize.assumption.bound", "bound_assumption"),
    "less_equal": ("mh.normalize.assumption.bound", "bound_assumption"),
    "greater": ("mh.normalize.assumption.bound", "bound_assumption"),
    "greater_equal": ("mh.normalize.assumption.bound", "bound_assumption"),
    "member": ("mh.normalize.assumption.member", "membership_assumption"),
    "not_member": (
        "mh.normalize.assumption.not-member",
        "nonmembership_assumption",
    ),
    "divides": ("mh.normalize.assumption.divides", "divisibility_assumption"),
    "congruent": ("mh.normalize.assumption.congruent", "congruence_assumption"),
}
_PREDICATE_RULES: Final = {
    ("org.mathhead.property.nonzero", 1): (
        "mh.normalize.predicate.nonzero",
        "nonzero_assumption",
    ),
    ("org.mathhead.property.finite", 1): (
        "mh.normalize.predicate.finite",
        "finiteness_assumption",
    ),
    ("org.mathhead.property.cardinality", 2): (
        "mh.normalize.predicate.cardinality",
        "cardinality_assumption",
    ),
    ("org.mathhead.property.dimension", 2): (
        "mh.normalize.predicate.dimension",
        "dimension_assumption",
    ),
    ("org.mathhead.graph.class", 2): (
        "mh.normalize.predicate.graph-class",
        "graph_class_assumption",
    ),
    ("org.mathhead.analysis.regularity", 2): (
        "mh.normalize.predicate.regularity",
        "regularity_assumption",
    ),
}


class DomainAssumptionValidationError(ValueError):
    """A strict normalization-result codec invariant failed."""

    __slots__ = ("kind", "path")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path


class _NormalizationError(ValueError):
    __slots__ = ("kind", "path", "detail")

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path
        self.detail = detail


@dataclass(frozen=True, slots=True)
class _FrozenMap(Mapping[str, object]):
    """Small immutable mapping used to keep public payloads alias-free."""

    entries: tuple[tuple[str, object], ...]

    def __getitem__(self, key: str) -> object:
        for item_key, value in self.entries:
            if item_key == key:
                return value
        raise KeyError(key)

    def __iter__(self):
        return (key for key, _value in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclass(frozen=True, slots=True)
class DomainAssumptionDiagnostic:
    code: str
    path: str
    message: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("DomainAssumptionDiagnostic cannot be pickled")


@dataclass(frozen=True, slots=True)
class DomainAssumptionFact:
    fact_sha256: str
    ordinal: int
    reading_id: str
    rule_id: str
    kind: str
    assumption_role: str | None
    origin_registry: str
    origin_id: str
    statement_id: str | None
    relation_id: str | None
    subject_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    span_ids: tuple[str, ...]
    fragment_sha256: str
    payload: object
    supported: bool
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("DomainAssumptionFact cannot be pickled")


@dataclass(frozen=True, slots=True)
class NormalizedDomainContext:
    reading_id: str
    projection_sha256: str
    rule_catalogue_sha256: str
    domain_ids: tuple[str, ...]
    variable_ids: tuple[str, ...]
    assumption_ids: tuple[str, ...]
    facts: tuple[DomainAssumptionFact, ...]
    fact_sha256s: tuple[str, ...]
    unsupported_fact_sha256s: tuple[str, ...]
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("NormalizedDomainContext cannot be pickled")


@dataclass(frozen=True, slots=True)
class DomainAssumptionCandidate:
    reading_id: str
    projection_sha256: str
    context_sha256: str
    context: NormalizedDomainContext

    def __reduce__(self) -> NoReturn:
        raise TypeError("DomainAssumptionCandidate cannot be pickled")


@dataclass(frozen=True, slots=True, init=False)
class DomainAssumptionNormalizationResult:
    schema: str
    contract_id: str
    contract_sha256: str
    reading_analysis_contract_id: str
    reading_analysis_contract_sha256: str
    problem_intake_contract_id: str
    problem_intake_contract_sha256: str
    problem_ir_contract_id: str
    problem_ir_contract_sha256: str
    rule_catalogue_sha256: str
    status: str
    reason_code: str
    input_result_sha256: str | None
    readings_result_bytes: bytes | None
    ambiguity_status: str | None
    selected_reading_id: str | None
    candidates: tuple[DomainAssumptionCandidate, ...]
    diagnostics: tuple[DomainAssumptionDiagnostic, ...]
    mathematical_authority: bool

    def __init__(
        self,
        *,
        schema: str = RESULT_SCHEMA,
        contract_id: str = CONTRACT_ID,
        contract_sha256: str = CONTRACT_SHA256,
        reading_analysis_contract_id: str = READING_ANALYSIS_CONTRACT_ID,
        reading_analysis_contract_sha256: str = READING_ANALYSIS_CONTRACT_SHA256,
        problem_intake_contract_id: str = INTAKE_CONTRACT_ID,
        problem_intake_contract_sha256: str = INTAKE_CONTRACT_SHA256,
        problem_ir_contract_id: str = "MH-C-PROBLEM-IR-002",
        problem_ir_contract_sha256: str = PROBLEM_IR_CONTRACT_SHA256,
        rule_catalogue_sha256: str = RULE_CATALOGUE_SHA256,
        status: str = "invalid",
        reason_code: str = "INVALID_TYPE",
        input_result_sha256: str | None = None,
        readings_result_bytes: bytes | None = None,
        ambiguity_status: str | None = None,
        selected_reading_id: str | None = None,
        candidates: tuple[DomainAssumptionCandidate, ...] = (),
        diagnostics: tuple[DomainAssumptionDiagnostic, ...] = (),
        mathematical_authority: bool = False,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError(
                "DomainAssumptionNormalizationResult is constructed by "
                "normalize_domain_assumptions"
            )
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("DomainAssumptionNormalizationResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("DomainAssumptionNormalizationResult cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("DomainAssumptionNormalizationResult cannot be pickled")

    def __copy__(self) -> DomainAssumptionNormalizationResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> DomainAssumptionNormalizationResult:
        del memo
        return self


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _NormalizationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _step(steps: list[int], path: str, count: int = 1) -> None:
    steps[0] += count
    if steps[0] > MAX_STEPS:
        _fail("budget", path, "validation step budget exceeded")


def _freeze(value: object) -> object:
    if type(value) is dict:
        return _FrozenMap(tuple((key, _freeze(item)) for key, item in value.items()))
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _canonical_bytes(value: object, *, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    value = _thaw(value)
    aggregate_strings = 0
    stack: list[tuple[object, int, str]] = [(value, 0, "$")]
    while stack:
        item, depth, path = stack.pop()
        if depth > MAX_DEPTH:
            _fail("budget", path, "canonical value nesting exceeds 512")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > MAX_INTEGER:
                _fail("canonical", path, "integer exceeds the portable exact range")
            continue
        if type(item) is str:
            if (
                len(item) > MAX_STRING_CODEPOINTS
                or "\x00" in item
                or unicodedata.normalize("NFC", item) != item
            ):
                _fail("canonical", path, "string is oversized, NUL-bearing, or non-NFC")
            aggregate_strings += len(item)
            if aggregate_strings > MAX_AGGREGATE_STRING_CODEPOINTS:
                _fail("budget", path, "aggregate string budget exceeded")
            continue
        if type(item) is list:
            stack.extend(
                (child, depth + 1, f"{path}[{index}]")
                for index, child in enumerate(item)
            )
            continue
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    _fail("canonical", path, "object key is not an exact string")
                stack.append((key, depth + 1, path + ".<key>"))
                stack.append((child, depth + 1, path + "." + key))
            continue
        _fail("canonical", path, "floats, subclasses, and non-JSON values are forbidden")
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
    if len(payload) > maximum:
        _fail("budget", "$", "canonical output byte budget exceeded")
    return payload


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DomainAssumptionValidationError(
                "schema", "$", f"duplicate JSON key {key!r}"
            )
        value[key] = item
    return value


def _json_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except DomainAssumptionValidationError:
        raise
    except RecursionError as exc:
        raise DomainAssumptionValidationError(
            "budget", path, "JSON nesting budget exceeded"
        ) from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise DomainAssumptionValidationError("schema", path, "invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise DomainAssumptionValidationError("schema", path, "expected a JSON object")
    return value


def _indexes(projection: dict[str, Any]) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    entities = projection["entities"]
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    owners: dict[str, str] = {}
    for registry in _ENTITY_REGISTRIES:
        records = entities[registry]
        index = {record["id"]: record for record in records}
        indexes[registry] = index
        for entity_id in index:
            if entity_id in owners:
                _fail("fact", f"$.entities.{registry}", "duplicate cross-registry identity")
            owners[entity_id] = registry
    return indexes, owners


def _dependencies(registry: str, record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []

    def add(owner: str, value: str | None) -> None:
        if value is not None:
            result.append((owner, value))

    def extend(owner: str, values: list[str]) -> None:
        result.extend((owner, value) for value in values)

    if registry != "source_documents":
        extend("source_spans", record.get("span_ids", []))
    if registry == "source_spans":
        add("source_documents", record["source_id"])
    elif registry == "domains":
        kind = record["kind"]
        if kind == "finite":
            add("domains", record["element_domain_id"])
            extend("expressions", record["element_expr_ids"])
        elif kind == "interval":
            add("expressions", record["lower_expr_id"])
            add("expressions", record["upper_expr_id"])
        elif kind == "modular":
            add("expressions", record["modulus_expr_id"])
        elif kind == "collection":
            add("domains", record["element_domain_id"])
        elif kind == "product":
            extend("domains", record["factor_domain_ids"])
        elif kind == "function":
            extend("domains", record["parameter_domain_ids"])
            add("domains", record["result_domain_id"])
        elif kind == "structure":
            extend("domains", record["parameter_domain_ids"])
            extend("expressions", record["parameter_expr_ids"])
    elif registry == "variables":
        add("domains", record["domain_id"])
    elif registry == "expressions":
        add("domains", record["domain_id"])
        kind = record["kind"]
        if kind == "variable":
            add("variables", record["variable_id"])
        elif kind == "apply":
            extend("expressions", record["argument_expr_ids"])
        elif kind in {"tuple", "collection"}:
            extend("expressions", record["element_expr_ids"])
        elif kind == "conditional":
            add("statements", record["condition_statement_id"])
            add("expressions", record["then_expr_id"])
            add("expressions", record["else_expr_id"])
    elif registry == "relations":
        extend("expressions", record["operand_expr_ids"])
    elif registry == "statements":
        kind = record["kind"]
        if kind == "relation":
            add("relations", record["relation_id"])
        elif kind == "logical":
            extend("statements", record["operand_statement_ids"])
        elif kind == "quantified":
            extend("variables", record["variable_ids"])
            add("statements", record["body_statement_id"])
    elif registry == "definitions":
        extend("variables", record["parameter_variable_ids"])
        add("domains", record["result_domain_id"])
        body = record["body"]
        add(
            "expressions" if body["kind"] == "expression" else "statements",
            body.get("expression_id" if body["kind"] == "expression" else "statement_id"),
        )
    elif registry in {"assumptions", "goals"}:
        add("statements", record["statement_id"])
    return tuple(result)


def _closure(
    origin_registry: str,
    origin_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    origin = indexes[origin_registry][origin_id]
    seen: set[tuple[str, str]] = {(origin_registry, origin_id)}
    pending = [(registry, entity_id, 1) for registry, entity_id in _dependencies(origin_registry, origin)]
    while pending:
        registry, entity_id, depth = pending.pop()
        _step(steps, f"$.entities.{registry}.{entity_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$", "fact dependency depth exceeds 512")
        key = (registry, entity_id)
        if key in seen:
            continue
        record = indexes.get(registry, {}).get(entity_id)
        if record is None:
            _fail("fact", f"$.entities.{registry}", f"missing dependency {entity_id!r}")
        seen.add(key)
        if len(seen) > MAX_DEPENDENCIES:
            _fail("budget", "$", "fact dependency budget exceeded")
        pending.extend(
            (owner, child, depth + 1) for owner, child in _dependencies(registry, record)
        )

    semantic = sorted(
        (registry, entity_id)
        for registry, entity_id in seen
        if registry in _SEMANTIC_REGISTRIES and (registry, entity_id) != (origin_registry, origin_id)
    )
    span_ids = tuple(sorted(entity_id for registry, entity_id in seen if registry == "source_spans"))
    source_ids = tuple(sorted(entity_id for registry, entity_id in seen if registry == "source_documents"))
    dependency_ids = tuple(sorted(entity_id for _registry, entity_id in semantic))
    fragment = {
        "origin": {"registry": origin_registry, "record": origin},
        "dependencies": [
            {"registry": registry, "record": indexes[registry][entity_id]}
            for registry, entity_id in semantic
        ],
        "source_spans": [indexes["source_spans"][item] for item in span_ids],
        "source_documents": [indexes["source_documents"][item] for item in source_ids],
    }
    return dependency_ids, span_ids, fragment


def _fact_mapping(fact: DomainAssumptionFact, *, include_digest: bool = True) -> dict[str, Any]:
    value = {
        "schema": FACT_SCHEMA,
        "ordinal": fact.ordinal,
        "reading_id": fact.reading_id,
        "rule_id": fact.rule_id,
        "kind": fact.kind,
        "assumption_role": fact.assumption_role,
        "origin_registry": fact.origin_registry,
        "origin_id": fact.origin_id,
        "statement_id": fact.statement_id,
        "relation_id": fact.relation_id,
        "subject_ids": list(fact.subject_ids),
        "dependency_ids": list(fact.dependency_ids),
        "span_ids": list(fact.span_ids),
        "fragment_sha256": fact.fragment_sha256,
        "payload": _thaw(fact.payload),
        "supported": fact.supported,
        "mathematical_authority": fact.mathematical_authority,
    }
    if include_digest:
        value["fact_sha256"] = fact.fact_sha256
    return value


def _new_fact(**values: object) -> DomainAssumptionFact:
    payload = _freeze(values.pop("payload"))
    provisional = DomainAssumptionFact(fact_sha256="0" * 64, payload=payload, **values)  # type: ignore[arg-type]
    digest = _sha(_canonical_bytes(_fact_mapping(provisional, include_digest=False)))
    return DomainAssumptionFact(fact_sha256=digest, payload=payload, **values)  # type: ignore[arg-type]


def _domain_fact(
    reading_id: str,
    ordinal: int,
    domain_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> DomainAssumptionFact:
    record = indexes["domains"][domain_id]
    rule = _DOMAIN_RULES.get(record["kind"])
    if rule is None:
        _fail("rule", f"$.entities.domains.{domain_id}.kind", "unknown domain rule")
    dependencies, spans, fragment = _closure("domains", domain_id, indexes, steps)
    direct_subjects = sorted({item for owner, item in _dependencies("domains", record) if owner in _SEMANTIC_REGISTRIES})
    return _new_fact(
        ordinal=ordinal,
        reading_id=reading_id,
        rule_id=rule[0],
        kind=rule[1],
        assumption_role=None,
        origin_registry="domains",
        origin_id=domain_id,
        statement_id=None,
        relation_id=None,
        subject_ids=tuple(direct_subjects),
        dependency_ids=dependencies,
        span_ids=spans,
        fragment_sha256=_sha(_canonical_bytes(fragment)),
        payload={"domain": record},
        supported=True,
        mathematical_authority=False,
    )


def _variable_fact(
    reading_id: str,
    ordinal: int,
    variable_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> DomainAssumptionFact:
    record = indexes["variables"][variable_id]
    dependencies, spans, fragment = _closure("variables", variable_id, indexes, steps)
    return _new_fact(
        ordinal=ordinal,
        reading_id=reading_id,
        rule_id="mh.normalize.variable.domain",
        kind="variable_domain",
        assumption_role=None,
        origin_registry="variables",
        origin_id=variable_id,
        statement_id=None,
        relation_id=None,
        subject_ids=(variable_id,),
        dependency_ids=dependencies,
        span_ids=spans,
        fragment_sha256=_sha(_canonical_bytes(fragment)),
        payload={"variable": record},
        supported=True,
        mathematical_authority=False,
    )


def _assumption_rule(
    statement: dict[str, Any],
    relation: dict[str, Any] | None,
) -> tuple[str, str, bool]:
    kind = statement["kind"]
    if kind == "truth":
        return "mh.normalize.assumption.truth", "truth_assumption", True
    if kind == "logical":
        return "mh.normalize.assumption.logical", "logical_assumption", False
    if kind == "quantified":
        return "mh.normalize.assumption.quantified", "quantified_assumption", False
    assert relation is not None
    if relation["kind"] == "predicate":
        match = _PREDICATE_RULES.get((relation["predicate"], len(relation["operand_expr_ids"])))
        if match is None:
            return (
                "mh.normalize.assumption.opaque-predicate",
                "opaque_predicate_assumption",
                False,
            )
        return match[0], match[1], True
    match = _RELATION_RULES.get(relation["kind"])
    if match is None:
        return (
            "mh.normalize.assumption.opaque-relation",
            "opaque_relation_assumption",
            False,
        )
    return match[0], match[1], True


def _subject_ids(statement: dict[str, Any], relation: dict[str, Any] | None) -> tuple[str, ...]:
    if relation is not None:
        return tuple(sorted(set(relation["operand_expr_ids"])))
    if statement["kind"] == "logical":
        return tuple(sorted(set(statement["operand_statement_ids"])))
    if statement["kind"] == "quantified":
        return tuple(sorted({*statement["variable_ids"], statement["body_statement_id"]}))
    return (statement["id"],)


def _zero_operand(
    relation: dict[str, Any], indexes: dict[str, dict[str, dict[str, Any]]]
) -> tuple[int, str] | None:
    if relation["kind"] != "not_equal" or len(relation["operand_expr_ids"]) != 2:
        return None
    matches: list[tuple[int, str]] = []
    for index, expression_id in enumerate(relation["operand_expr_ids"]):
        expression = indexes["expressions"][expression_id]
        if expression["kind"] != "literal":
            continue
        literal_type = expression["literal_type"]
        value = expression["value"]
        is_zero = literal_type == "integer" and value == "0"
        is_zero = is_zero or (
            literal_type == "rational" and value.split("/", 1)[0] == "0"
        )
        if is_zero:
            matches.append((index, expression_id))
    if len(matches) != 1:
        return None
    zero_index, _zero_id = matches[0]
    subject_id = relation["operand_expr_ids"][1 - zero_index]
    return zero_index, subject_id


def _assumption_facts(
    reading_id: str,
    ordinal: int,
    assumption_id: str,
    indexes: dict[str, dict[str, dict[str, Any]]],
    steps: list[int],
) -> tuple[DomainAssumptionFact, ...]:
    assumption = indexes["assumptions"][assumption_id]
    statement = indexes["statements"][assumption["statement_id"]]
    relation = (
        indexes["relations"][statement["relation_id"]]
        if statement["kind"] == "relation"
        else None
    )
    rule_id, fact_kind, supported = _assumption_rule(statement, relation)
    dependencies, spans, fragment = _closure("assumptions", assumption_id, indexes, steps)
    payload = {
        "assumption": assumption,
        "statement": statement,
        "relation": relation,
    }
    base = _new_fact(
        ordinal=ordinal,
        reading_id=reading_id,
        rule_id=rule_id,
        kind=fact_kind,
        assumption_role=assumption["role"],
        origin_registry="assumptions",
        origin_id=assumption_id,
        statement_id=statement["id"],
        relation_id=None if relation is None else relation["id"],
        subject_ids=_subject_ids(statement, relation),
        dependency_ids=dependencies,
        span_ids=spans,
        fragment_sha256=_sha(_canonical_bytes(fragment)),
        payload=payload,
        supported=supported,
        mathematical_authority=False,
    )
    if relation is None:
        return (base,)
    nonzero = _zero_operand(relation, indexes)
    if nonzero is None:
        return (base,)
    zero_index, subject_id = nonzero
    derived = _new_fact(
        ordinal=ordinal + 1,
        reading_id=reading_id,
        rule_id="mh.normalize.assumption.nonzero-relation",
        kind="nonzero_assumption",
        assumption_role=assumption["role"],
        origin_registry="assumptions",
        origin_id=assumption_id,
        statement_id=statement["id"],
        relation_id=relation["id"],
        subject_ids=(subject_id,),
        dependency_ids=dependencies,
        span_ids=spans,
        fragment_sha256=_sha(_canonical_bytes(fragment)),
        payload={**payload, "zero_operand_index": zero_index, "subject_expr_id": subject_id},
        supported=True,
        mathematical_authority=False,
    )
    return base, derived


def _context_mapping(context: NormalizedDomainContext) -> dict[str, Any]:
    return {
        "schema": CONTEXT_SCHEMA,
        "reading_id": context.reading_id,
        "projection_sha256": context.projection_sha256,
        "rule_catalogue_sha256": context.rule_catalogue_sha256,
        "domain_ids": list(context.domain_ids),
        "variable_ids": list(context.variable_ids),
        "assumption_ids": list(context.assumption_ids),
        "facts": [_fact_mapping(item) for item in context.facts],
        "fact_sha256s": list(context.fact_sha256s),
        "unsupported_fact_sha256s": list(context.unsupported_fact_sha256s),
        "mathematical_authority": context.mathematical_authority,
    }


def _normalize_candidate(candidate: object, steps: list[int]) -> DomainAssumptionCandidate:
    projection_bytes = getattr(candidate, "projection_bytes")
    projection_sha256 = getattr(candidate, "projection_sha256")
    reading_id = getattr(candidate, "reading_id")
    try:
        projection = json.loads(projection_bytes.decode("utf-8"), object_pairs_hook=_pairs)
    except DomainAssumptionValidationError as exc:
        _fail(exc.kind, exc.path, str(exc))
    if type(projection) is not dict:
        _fail("fact", "$", "projection root is not an object")
    indexes, _owners = _indexes(projection)
    domain_ids = tuple(sorted(indexes["domains"]))
    variable_ids = tuple(sorted(indexes["variables"]))
    assumption_ids = tuple(projection["assumption_ids"])
    if len(domain_ids) > MAX_DOMAINS or len(variable_ids) > MAX_VARIABLES:
        _fail("budget", "$", "domain or variable budget exceeded")
    if len(assumption_ids) > MAX_ASSUMPTIONS:
        _fail("budget", "$", "assumption budget exceeded")
    facts: list[DomainAssumptionFact] = []
    for domain_id in domain_ids:
        facts.append(_domain_fact(reading_id, len(facts), domain_id, indexes, steps))
    for variable_id in variable_ids:
        facts.append(_variable_fact(reading_id, len(facts), variable_id, indexes, steps))
    for assumption_id in assumption_ids:
        facts.extend(
            _assumption_facts(reading_id, len(facts), assumption_id, indexes, steps)
        )
        if len(facts) > MAX_FACTS:
            _fail("budget", "$", "fact budget exceeded")
    context = NormalizedDomainContext(
        reading_id=reading_id,
        projection_sha256=projection_sha256,
        rule_catalogue_sha256=RULE_CATALOGUE_SHA256,
        domain_ids=domain_ids,
        variable_ids=variable_ids,
        assumption_ids=assumption_ids,
        facts=tuple(facts),
        fact_sha256s=tuple(item.fact_sha256 for item in facts),
        unsupported_fact_sha256s=tuple(
            item.fact_sha256 for item in facts if not item.supported
        ),
    )
    context_sha256 = _sha(_canonical_bytes(_context_mapping(context)))
    return DomainAssumptionCandidate(
        reading_id=reading_id,
        projection_sha256=projection_sha256,
        context_sha256=context_sha256,
        context=context,
    )


def _diagnostic(error: _NormalizationError) -> DomainAssumptionDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "fact": "INVALID_FACT",
        "reading": "INVALID_READING_ANALYSIS",
        "rule": "INVALID_RULE_CATALOGUE",
        "type": "INVALID_TYPE",
    }.get(error.kind, "INVALID_FACT")
    path = error.path if _PATH.fullmatch(error.path) is not None else "$"
    message = error.detail[:MAX_DIAGNOSTIC_CODEPOINTS] or "invalid normalization"
    return DomainAssumptionDiagnostic(code=code, path=path, message=message)


def _new_result(**values: object) -> DomainAssumptionNormalizationResult:
    result = DomainAssumptionNormalizationResult(_token=_RESULT_TOKEN, **values)
    _validate_result_shape(result)
    return result


def normalize_domain_assumptions(
    readings_result: bytes,
) -> DomainAssumptionNormalizationResult:
    """Inventory declared domains and assumptions in every MH-041 reading."""
    try:
        if type(readings_result) is not bytes:
            _fail("type", "$", "readings_result must be exact bytes")
        if len(readings_result) > MAX_INPUT_BYTES:
            _fail("budget", "$", "reading-analysis result byte budget exceeded")
        try:
            parsed = parse_reading_analysis_result(readings_result)
        except ReadingAnalysisValidationError as exc:
            _fail("budget" if exc.kind == "budget" else "reading", exc.path, str(exc))
        if parsed.status != "analyzed":
            _fail("reading", "$.status", "only an analyzed MH-041 result can be normalized")
        if reading_analysis_result_bytes(parsed) != readings_result:
            _fail("reading", "$", "reading-analysis result round-trip drift")
        if len(parsed.candidates) > MAX_CANDIDATES:
            _fail("budget", "$.candidates", "candidate budget exceeded")
        steps = [0]
        candidates = tuple(_normalize_candidate(item, steps) for item in parsed.candidates)
        result = _new_result(
            status="normalized",
            reason_code="NORMALIZED",
            input_result_sha256=_sha(readings_result),
            readings_result_bytes=readings_result,
            ambiguity_status=parsed.ambiguity_status,
            selected_reading_id=parsed.selected_reading_id,
            candidates=candidates,
            diagnostics=(),
        )
        if len(_result_bytes_unchecked(result)) > MAX_OUTPUT_BYTES:
            _fail("budget", "$", "normalization result byte budget exceeded")
        return result
    except _NormalizationError as error:
        diagnostic = _diagnostic(error)
        return _new_result(
            status="exhausted" if error.kind == "budget" else "invalid",
            reason_code=diagnostic.code,
            diagnostics=(diagnostic,),
        )
    except RecursionError:
        return _new_result(
            status="exhausted",
            reason_code="BUDGET_EXHAUSTED",
            diagnostics=(
                DomainAssumptionDiagnostic(
                    code="BUDGET_EXHAUSTED",
                    path="$",
                    message="recursive normalization exceeded the structural budget",
                ),
            ),
        )


def _result_mapping(result: DomainAssumptionNormalizationResult) -> dict[str, Any]:
    readings = (
        None
        if result.readings_result_bytes is None
        else _json_object(result.readings_result_bytes, "$.readings_result")
    )
    return {
        "schema": result.schema,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "reading_analysis_contract_id": result.reading_analysis_contract_id,
        "reading_analysis_contract_sha256": result.reading_analysis_contract_sha256,
        "problem_intake_contract_id": result.problem_intake_contract_id,
        "problem_intake_contract_sha256": result.problem_intake_contract_sha256,
        "problem_ir_contract_id": result.problem_ir_contract_id,
        "problem_ir_contract_sha256": result.problem_ir_contract_sha256,
        "rule_catalogue_sha256": result.rule_catalogue_sha256,
        "status": result.status,
        "reason_code": result.reason_code,
        "input_result_sha256": result.input_result_sha256,
        "readings_result": readings,
        "ambiguity_status": result.ambiguity_status,
        "selected_reading_id": result.selected_reading_id,
        "candidates": [
            {
                "reading_id": item.reading_id,
                "projection_sha256": item.projection_sha256,
                "context_sha256": item.context_sha256,
                "context": _context_mapping(item.context),
            }
            for item in result.candidates
        ],
        "diagnostics": [
            {"code": item.code, "path": item.path, "message": item.message}
            for item in result.diagnostics
        ],
        "mathematical_authority": result.mathematical_authority,
    }


def _result_bytes_unchecked(result: DomainAssumptionNormalizationResult) -> bytes:
    return _canonical_bytes(_result_mapping(result))


def _validate_fact(fact: object, ordinal: int, reading_id: str) -> None:
    if type(fact) is not DomainAssumptionFact:
        raise DomainAssumptionValidationError("type", "$.facts", "invalid fact type")
    if fact.ordinal != ordinal or fact.reading_id != reading_id:
        raise DomainAssumptionValidationError("result", "$.facts", "fact position drift")
    if fact.mathematical_authority is not False:
        raise DomainAssumptionValidationError("result", "$.facts", "fact authority drift")
    expected = _sha(_canonical_bytes(_fact_mapping(fact, include_digest=False)))
    if fact.fact_sha256 != expected:
        raise DomainAssumptionValidationError("identity", "$.facts", "fact digest drift")


def _validate_result_shape(result: object) -> None:
    if type(result) is not DomainAssumptionNormalizationResult:
        raise DomainAssumptionValidationError(
            "type", "$", "expected exact DomainAssumptionNormalizationResult"
        )
    constants = {
        "schema": RESULT_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "reading_analysis_contract_id": READING_ANALYSIS_CONTRACT_ID,
        "reading_analysis_contract_sha256": READING_ANALYSIS_CONTRACT_SHA256,
        "problem_intake_contract_id": INTAKE_CONTRACT_ID,
        "problem_intake_contract_sha256": INTAKE_CONTRACT_SHA256,
        "problem_ir_contract_id": "MH-C-PROBLEM-IR-002",
        "problem_ir_contract_sha256": PROBLEM_IR_CONTRACT_SHA256,
        "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
        "mathematical_authority": False,
    }
    for field, expected in constants.items():
        actual = getattr(result, field, None)
        if type(actual) is not type(expected) or actual != expected:
            raise DomainAssumptionValidationError("result", f"$.{field}", "binding drift")
    if result.status not in {"normalized", "invalid", "exhausted"}:
        raise DomainAssumptionValidationError("result", "$.status", "unknown status")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > 32:
        raise DomainAssumptionValidationError("result", "$.diagnostics", "invalid diagnostics")
    for index, diagnostic in enumerate(result.diagnostics):
        path = f"$.diagnostics[{index}]"
        if type(diagnostic) is not DomainAssumptionDiagnostic:
            raise DomainAssumptionValidationError("type", path, "invalid diagnostic")
        if diagnostic.code not in {
            "BUDGET_EXHAUSTED",
            "INVALID_FACT",
            "INVALID_READING_ANALYSIS",
            "INVALID_RULE_CATALOGUE",
            "INVALID_TYPE",
        }:
            raise DomainAssumptionValidationError("result", path, "unknown diagnostic")
        if (
            type(diagnostic.path) is not str
            or _PATH.fullmatch(diagnostic.path) is None
            or type(diagnostic.message) is not str
            or not diagnostic.message
            or len(diagnostic.message) > MAX_DIAGNOSTIC_CODEPOINTS
        ):
            raise DomainAssumptionValidationError("result", path, "invalid diagnostic shape")
    if result.status != "normalized":
        empty = (
            result.input_result_sha256 is None
            and result.readings_result_bytes is None
            and result.ambiguity_status is None
            and result.selected_reading_id is None
            and result.candidates == ()
        )
        if not empty or not result.diagnostics or result.reason_code != result.diagnostics[0].code:
            raise DomainAssumptionValidationError("result", "$", "failed combination drift")
        if result.status == "exhausted" and result.reason_code != "BUDGET_EXHAUSTED":
            raise DomainAssumptionValidationError("result", "$", "exhausted reason drift")
        if result.status == "invalid" and result.reason_code == "BUDGET_EXHAUSTED":
            raise DomainAssumptionValidationError("result", "$", "invalid reason drift")
        return
    if result.reason_code != "NORMALIZED" or result.diagnostics:
        raise DomainAssumptionValidationError("result", "$", "normalized combination drift")
    if (
        type(result.readings_result_bytes) is not bytes
        or type(result.input_result_sha256) is not str
        or _sha(result.readings_result_bytes) != result.input_result_sha256
    ):
        raise DomainAssumptionValidationError("identity", "$", "input identity drift")
    if result.ambiguity_status not in {"unambiguous", "unresolved", "resolved"}:
        raise DomainAssumptionValidationError("result", "$.ambiguity_status", "state drift")
    if type(result.candidates) is not tuple or not result.candidates:
        raise DomainAssumptionValidationError("result", "$.candidates", "missing candidates")
    if any(type(item) is not DomainAssumptionCandidate for item in result.candidates):
        raise DomainAssumptionValidationError("type", "$.candidates", "invalid candidate")
    ids = tuple(item.reading_id for item in result.candidates)
    if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
        raise DomainAssumptionValidationError("result", "$.candidates", "candidate order drift")
    for candidate in result.candidates:
        context = candidate.context
        if type(context) is not NormalizedDomainContext:
            raise DomainAssumptionValidationError("type", "$.context", "invalid context")
        if (
            candidate.reading_id != context.reading_id
            or candidate.projection_sha256 != context.projection_sha256
            or candidate.context_sha256 != _sha(_canonical_bytes(_context_mapping(context)))
        ):
            raise DomainAssumptionValidationError("identity", "$.context", "context drift")
        if context.domain_ids != tuple(sorted(context.domain_ids)):
            raise DomainAssumptionValidationError("result", "$.context.domain_ids", "order drift")
        if context.variable_ids != tuple(sorted(context.variable_ids)):
            raise DomainAssumptionValidationError("result", "$.context.variable_ids", "order drift")
        for ordinal, fact in enumerate(context.facts):
            _validate_fact(fact, ordinal, candidate.reading_id)
        digests = tuple(item.fact_sha256 for item in context.facts)
        unsupported = tuple(item.fact_sha256 for item in context.facts if not item.supported)
        if digests != context.fact_sha256s or unsupported != context.unsupported_fact_sha256s:
            raise DomainAssumptionValidationError("identity", "$.context", "fact index drift")


def validate_domain_assumption_result(result: object) -> None:
    """Recompute a closed result before it is consumed."""
    _validate_result_shape(result)
    assert type(result) is DomainAssumptionNormalizationResult
    if result.status == "normalized":
        assert result.readings_result_bytes is not None
        expected = normalize_domain_assumptions(result.readings_result_bytes)
        if expected != result:
            raise DomainAssumptionValidationError("result", "$", "normalization replay drift")


def domain_assumption_fact_bytes(fact: DomainAssumptionFact) -> bytes:
    """Return canonical bytes for one validated fact."""
    if type(fact) is not DomainAssumptionFact:
        raise DomainAssumptionValidationError("type", "$", "expected exact fact")
    expected = _sha(_canonical_bytes(_fact_mapping(fact, include_digest=False)))
    if fact.fact_sha256 != expected:
        raise DomainAssumptionValidationError("identity", "$", "fact digest drift")
    return _canonical_bytes(_fact_mapping(fact))


def normalized_domain_context_bytes(context: NormalizedDomainContext) -> bytes:
    """Return canonical bytes for one structurally closed context."""
    if type(context) is not NormalizedDomainContext:
        raise DomainAssumptionValidationError("type", "$", "expected exact context")
    for ordinal, fact in enumerate(context.facts):
        _validate_fact(fact, ordinal, context.reading_id)
    return _canonical_bytes(_context_mapping(context))


def domain_assumption_result_bytes(result: DomainAssumptionNormalizationResult) -> bytes:
    """Serialize one closed result to canonical replayable JSON bytes."""
    validate_domain_assumption_result(result)
    try:
        return _result_bytes_unchecked(result)
    except _NormalizationError as exc:
        raise DomainAssumptionValidationError(exc.kind, exc.path, exc.detail) from exc


def domain_assumption_result_sha256(result: DomainAssumptionNormalizationResult) -> str:
    """Return the full SHA-256 identity of canonical normalization bytes."""
    return _sha(domain_assumption_result_bytes(result))


def parse_domain_assumption_result(data: bytes) -> DomainAssumptionNormalizationResult:
    """Parse canonical result bytes and replay every successful fact and context."""
    if type(data) is not bytes:
        raise DomainAssumptionValidationError("type", "$", "result must be exact bytes")
    if len(data) > MAX_OUTPUT_BYTES:
        raise DomainAssumptionValidationError("budget", "$", "result byte budget exceeded")
    value = _json_object(data, "$")
    try:
        if _canonical_bytes(value) != data:
            raise DomainAssumptionValidationError("canonical", "$", "result is noncanonical")
    except _NormalizationError as exc:
        raise DomainAssumptionValidationError(exc.kind, exc.path, exc.detail) from exc
    fields = {
        "schema", "contract_id", "contract_sha256", "reading_analysis_contract_id",
        "reading_analysis_contract_sha256", "problem_intake_contract_id",
        "problem_intake_contract_sha256", "problem_ir_contract_id",
        "problem_ir_contract_sha256", "rule_catalogue_sha256", "status",
        "reason_code", "input_result_sha256", "readings_result", "ambiguity_status",
        "selected_reading_id", "candidates", "diagnostics", "mathematical_authority",
    }
    if set(value) != fields:
        raise DomainAssumptionValidationError("schema", "$", "result field set drift")
    if value["status"] == "normalized":
        if type(value["readings_result"]) is not dict:
            raise DomainAssumptionValidationError("schema", "$.readings_result", "missing input")
        try:
            input_bytes = _canonical_bytes(value["readings_result"], maximum=MAX_INPUT_BYTES)
        except _NormalizationError as exc:
            raise DomainAssumptionValidationError(exc.kind, exc.path, exc.detail) from exc
        expected = normalize_domain_assumptions(input_bytes)
        if expected.status != "normalized" or _result_mapping(expected) != value:
            raise DomainAssumptionValidationError("result", "$", "historical replay drift")
        if _result_bytes_unchecked(expected) != data:
            raise DomainAssumptionValidationError("canonical", "$", "result round-trip drift")
        return expected
    raw_diagnostics = value["diagnostics"]
    if type(raw_diagnostics) is not list:
        raise DomainAssumptionValidationError("schema", "$.diagnostics", "expected array")
    diagnostics: list[DomainAssumptionDiagnostic] = []
    for index, raw in enumerate(raw_diagnostics):
        if type(raw) is not dict or set(raw) != {"code", "path", "message"}:
            raise DomainAssumptionValidationError(
                "schema", f"$.diagnostics[{index}]", "diagnostic field drift"
            )
        diagnostics.append(DomainAssumptionDiagnostic(**raw))
    result = DomainAssumptionNormalizationResult(
        schema=value["schema"],
        contract_id=value["contract_id"],
        contract_sha256=value["contract_sha256"],
        reading_analysis_contract_id=value["reading_analysis_contract_id"],
        reading_analysis_contract_sha256=value["reading_analysis_contract_sha256"],
        problem_intake_contract_id=value["problem_intake_contract_id"],
        problem_intake_contract_sha256=value["problem_intake_contract_sha256"],
        problem_ir_contract_id=value["problem_ir_contract_id"],
        problem_ir_contract_sha256=value["problem_ir_contract_sha256"],
        rule_catalogue_sha256=value["rule_catalogue_sha256"],
        status=value["status"],
        reason_code=value["reason_code"],
        input_result_sha256=value["input_result_sha256"],
        readings_result_bytes=None,
        ambiguity_status=value["ambiguity_status"],
        selected_reading_id=value["selected_reading_id"],
        candidates=(),
        diagnostics=tuple(diagnostics),
        mathematical_authority=value["mathematical_authority"],
        _token=_RESULT_TOKEN,
    )
    _validate_result_shape(result)
    if _result_bytes_unchecked(result) != data:
        raise DomainAssumptionValidationError("canonical", "$", "failed result round-trip drift")
    return result
