"""Pure, non-authoritative proof-obligation decomposition for MH-043."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, NoReturn
import unicodedata

from mathhead.domain_assumptions import (
    CONTRACT_ID as DOMAIN_ASSUMPTION_CONTRACT_ID,
    CONTRACT_SHA256 as DOMAIN_ASSUMPTION_CONTRACT_SHA256,
    DomainAssumptionValidationError,
    domain_assumption_result_bytes,
    parse_domain_assumption_result,
)


CONTRACT_ID: Final = "MH-C-PROOF-OBLIGATION-DECOMPOSITION-001"
CONTRACT_SHA256: Final = \
    "ea5d0664611b57da3074e20fce90623318ce04280d38ecce548025a91a7b19ff"
RESULT_SCHEMA: Final = "mathhead.proof-obligation-result.v1"
DECOMPOSITION_CATALOGUE_SHA256: Final = \
    "d59c480c6ee19471051632407deb611d8df6be4987cf23154d56aa4d3326a524"
STRATEGY_CATALOGUE_SHA256: Final = \
    "28b815267fb5a2637d4a673218d1720c9ddcab0ea3f6bf3a8f6d05a3125fa1c8"
READING_ANALYSIS_CONTRACT_ID: Final = "MH-C-READING-ANALYSIS-002"
READING_ANALYSIS_CONTRACT_SHA256: Final = \
    "0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70"
PROBLEM_INTAKE_CONTRACT_ID: Final = "MH-C-PROBLEM-INTAKE-001"
PROBLEM_INTAKE_CONTRACT_SHA256: Final = \
    "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc"
PROBLEM_IR_CONTRACT_ID: Final = "MH-C-PROBLEM-IR-002"
PROBLEM_IR_CONTRACT_SHA256: Final = \
    "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286"

MAX_INPUT_BYTES: Final = 268_435_456
MAX_OUTPUT_BYTES: Final = 536_870_912
MAX_READINGS: Final = 100_000
MAX_GOALS: Final = 100_000
MAX_OBLIGATIONS: Final = 800_000
MAX_EDGES: Final = 1_600_000
MAX_CONTEXTS: Final = 800_000
MAX_STRATEGIES: Final = 128
MAX_DEPENDENCIES: Final = 2_400_000
MAX_DEPTH: Final = 512
MAX_STEPS: Final = 32_000_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 33_554_432
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_DIAGNOSTIC_CODEPOINTS: Final = 512

_RESULT_TOKEN = object()
_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_OBLIGATION_ID = re.compile(r"^obligation_[0-9]{6}$")
_PATH = re.compile(r"^\$(?:\.[A-Za-z_][A-Za-z0-9_]*|\[[0-9]+\])*$")
_ENTITY_REGISTRIES: Final = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals",
)
_SEMANTIC_REGISTRIES: Final = frozenset(_ENTITY_REGISTRIES[2:])

_PROVE_RULES: Final = {
    ("truth", None): ("mh.obligation.statement.truth", "truth", True),
    ("relation", None): ("mh.obligation.statement.relation", "relation", True),
    ("logical", "not"): ("mh.obligation.logical.not", "negation", True),
    ("logical", "and"): ("mh.obligation.logical.and", "conjunction", True),
    ("logical", "or"): ("mh.obligation.logical.or", "disjunction", True),
    ("logical", "implies"): ("mh.obligation.logical.implies", "implication", True),
    ("logical", "iff"): ("mh.obligation.logical.iff", "biconditional", True),
    ("quantified", "forall"): ("mh.obligation.quantified.forall", "universal", True),
    ("quantified", "exists"): ("mh.obligation.quantified.exists", "existential", True),
    ("quantified", "exists_unique"): (
        "mh.obligation.quantified.exists-unique", "unique_existence", True
    ),
}
_MODE_RULES: Final = {
    "refute": ("mh.obligation.goal.refute", "refutation"),
    "find_witness": ("mh.obligation.goal.find-witness", "witness_search"),
    "compute": ("mh.obligation.goal.compute", "computation"),
    "classify": ("mh.obligation.goal.classify", "classification"),
    "optimize": ("mh.obligation.goal.optimize", "optimization"),
}

_RULE_SHAPES: Final = {
    **{
        rule_id: (kind, "prove")
        for rule_id, kind, _supported in _PROVE_RULES.values()
    },
    **{
        rule_id: (kind, mode)
        for mode, (rule_id, kind) in _MODE_RULES.items()
    },
    "mh.obligation.component.witness-construction": (
        "witness_construction", "prove"
    ),
    "mh.obligation.component.witness-verification": (
        "witness_verification", "prove"
    ),
    "mh.obligation.component.uniqueness": ("uniqueness", "prove"),
    "mh.obligation.unsupported": ("unsupported", None),
}

_STRATEGIES: Final = (
    ("mh.strategy.truth-constant", "mh.strategy-match.kind.truth", "obligation_kind", ("truth",), "EXACT_TRUTH_KIND"),
    ("mh.strategy.equality", "mh.strategy-match.relation.equal", "relation_kind", ("equal",), "EXACT_EQUAL_RELATION"),
    ("mh.strategy.disequality", "mh.strategy-match.relation.not-equal", "relation_kind", ("not_equal",), "EXACT_NOT_EQUAL_RELATION"),
    ("mh.strategy.ordered-relation", "mh.strategy-match.relation.order", "relation_kind", ("greater", "greater_equal", "less", "less_equal"), "EXACT_ORDER_RELATION"),
    ("mh.strategy.membership", "mh.strategy-match.relation.membership", "relation_kind", ("member", "not_member"), "EXACT_MEMBERSHIP_RELATION"),
    ("mh.strategy.divisibility", "mh.strategy-match.relation.divides", "relation_kind", ("divides",), "EXACT_DIVIDES_RELATION"),
    ("mh.strategy.congruence", "mh.strategy-match.relation.congruent", "relation_kind", ("congruent",), "EXACT_CONGRUENT_RELATION"),
    ("mh.strategy.named-predicate", "mh.strategy-match.relation.predicate", "relation_kind", ("predicate",), "EXACT_PREDICATE_RELATION"),
    ("mh.strategy.structural-composition", "mh.strategy-match.kind.structural", "obligation_kind", ("biconditional", "conjunction", "implication", "universal"), "EXACT_STRUCTURAL_KIND"),
    ("mh.strategy.case-choice", "mh.strategy-match.kind.case-choice", "obligation_kind", ("disjunction",), "EXACT_DISJUNCTION_KIND"),
    ("mh.strategy.witness-construction", "mh.strategy-match.kind.witness", "obligation_kind", ("existential", "unique_existence", "witness_construction", "witness_search"), "EXACT_WITNESS_KIND"),
    ("mh.strategy.uniqueness", "mh.strategy-match.kind.uniqueness", "obligation_kind", ("uniqueness",), "EXACT_UNIQUENESS_KIND"),
    ("mh.strategy.counterexample-search", "mh.strategy-match.mode.refute", "goal_mode", ("refute",), "EXACT_REFUTE_MODE"),
    ("mh.strategy.exact-computation", "mh.strategy-match.mode.compute", "goal_mode", ("compute",), "EXACT_COMPUTE_MODE"),
    ("mh.strategy.classification", "mh.strategy-match.mode.classify", "goal_mode", ("classify",), "EXACT_CLASSIFY_MODE"),
    ("mh.strategy.optimization", "mh.strategy-match.mode.optimize", "goal_mode", ("optimize",), "EXACT_OPTIMIZE_MODE"),
    ("mh.strategy.finite-enumeration", "mh.strategy-match.domain.finite", "domain_kind", ("finite",), "EXACT_FINITE_DOMAIN_DEPENDENCY"),
    ("mh.strategy.modular-domain", "mh.strategy-match.domain.modular", "domain_kind", ("modular",), "EXACT_MODULAR_DOMAIN_DEPENDENCY"),
    ("mh.strategy.numeric-domain", "mh.strategy-match.carrier.numeric", "builtin_carrier", ("complex", "integer", "natural", "rational", "real"), "EXACT_NUMERIC_CARRIER_DEPENDENCY"),
)


class ProofObligationValidationError(ValueError):
    """Strict proof-obligation validation failed."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{kind} at {path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


class _DecompositionError(ValueError):
    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind
        self.path = path
        self.detail = detail


@dataclass(frozen=True, slots=True)
class _FrozenMap(Mapping[str, object]):
    entries: tuple[tuple[str, object], ...]

    def __getitem__(self, key: str) -> object:
        for candidate, value in self.entries:
            if candidate == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _value in self.entries)

    def __len__(self) -> int:
        return len(self.entries)


@dataclass(frozen=True, slots=True)
class ProofObligationDiagnostic:
    code: str
    path: str
    message: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationDiagnostic cannot be pickled")


@dataclass(frozen=True, slots=True)
class StrategyAdmissibility:
    strategy_id: str
    match_rule_id: str
    reason_code: str
    matched_value: str
    prerequisite_obligation_ids: tuple[str, ...]
    guarantees_success: bool = False
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("StrategyAdmissibility cannot be pickled")


@dataclass(frozen=True, slots=True)
class ProofObligationLocalContext:
    reading_id: str
    normalized_context_sha256: str
    definition_ids: tuple[str, ...]
    assumption_fact_sha256s: tuple[str, ...]
    bound_variable_ids: tuple[str, ...]
    local_hypothesis_statement_ids: tuple[str, ...]
    witness_placeholder_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    source_span_ids: tuple[str, ...]
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationLocalContext cannot be pickled")


@dataclass(frozen=True, slots=True)
class ProofObligation:
    obligation_sha256: str
    obligation_id: str
    ordinal: int
    reading_id: str
    root_goal_id: str
    parent_obligation_id: str | None
    rule_id: str
    kind: str
    goal_mode: str
    status: str
    statement_id: str | None
    relation_id: str | None
    statement_fragment_sha256: str
    source_span_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    local_context_sha256: str
    child_obligation_ids: tuple[str, ...]
    prerequisite_obligation_ids: tuple[str, ...]
    alternative_group_id: str | None
    alternative_index: int | None
    witness_placeholder_ids: tuple[str, ...]
    admissible_strategies: tuple[StrategyAdmissibility, ...]
    payload: object
    supported: bool
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligation cannot be pickled")


@dataclass(frozen=True, slots=True)
class ProofObligationEdge:
    ordinal: int
    from_obligation_id: str
    to_obligation_id: str
    kind: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationEdge cannot be pickled")


@dataclass(frozen=True, slots=True)
class ProofObligationGraph:
    reading_id: str
    projection_sha256: str
    normalized_context_sha256: str
    decomposition_catalogue_sha256: str
    strategy_catalogue_sha256: str
    goal_ids: tuple[str, ...]
    root_obligation_ids: tuple[str, ...]
    obligations: tuple[ProofObligation, ...]
    obligation_sha256s: tuple[str, ...]
    local_contexts: tuple[tuple[str, ProofObligationLocalContext], ...]
    edges: tuple[ProofObligationEdge, ...]
    unsupported_obligation_ids: tuple[str, ...]
    choice_required_obligation_ids: tuple[str, ...]
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationGraph cannot be pickled")


@dataclass(frozen=True, slots=True)
class ProofObligationCandidate:
    reading_id: str
    projection_sha256: str
    normalized_context_sha256: str
    graph_sha256: str
    graph: ProofObligationGraph

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationCandidate cannot be pickled")


@dataclass(frozen=True, slots=True, init=False)
class ProofObligationDecompositionResult:
    schema: str
    contract_id: str
    contract_sha256: str
    domain_assumption_contract_id: str
    domain_assumption_contract_sha256: str
    reading_analysis_contract_id: str
    reading_analysis_contract_sha256: str
    problem_intake_contract_id: str
    problem_intake_contract_sha256: str
    problem_ir_contract_id: str
    problem_ir_contract_sha256: str
    decomposition_catalogue_sha256: str
    strategy_catalogue_sha256: str
    status: str
    reason_code: str
    input_result_sha256: str | None
    domain_result_bytes: bytes | None
    ambiguity_status: str | None
    selected_reading_id: str | None
    candidates: tuple[ProofObligationCandidate, ...]
    diagnostics: tuple[ProofObligationDiagnostic, ...]
    mathematical_authority: bool

    def __init__(
        self,
        *,
        schema: str = RESULT_SCHEMA,
        contract_id: str = CONTRACT_ID,
        contract_sha256: str = CONTRACT_SHA256,
        domain_assumption_contract_id: str = DOMAIN_ASSUMPTION_CONTRACT_ID,
        domain_assumption_contract_sha256: str = DOMAIN_ASSUMPTION_CONTRACT_SHA256,
        reading_analysis_contract_id: str = READING_ANALYSIS_CONTRACT_ID,
        reading_analysis_contract_sha256: str = READING_ANALYSIS_CONTRACT_SHA256,
        problem_intake_contract_id: str = PROBLEM_INTAKE_CONTRACT_ID,
        problem_intake_contract_sha256: str = PROBLEM_INTAKE_CONTRACT_SHA256,
        problem_ir_contract_id: str = PROBLEM_IR_CONTRACT_ID,
        problem_ir_contract_sha256: str = PROBLEM_IR_CONTRACT_SHA256,
        decomposition_catalogue_sha256: str = DECOMPOSITION_CATALOGUE_SHA256,
        strategy_catalogue_sha256: str = STRATEGY_CATALOGUE_SHA256,
        status: str = "invalid",
        reason_code: str = "INVALID_TYPE",
        input_result_sha256: str | None = None,
        domain_result_bytes: bytes | None = None,
        ambiguity_status: str | None = None,
        selected_reading_id: str | None = None,
        candidates: tuple[ProofObligationCandidate, ...] = (),
        diagnostics: tuple[ProofObligationDiagnostic, ...] = (),
        mathematical_authority: bool = False,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError(
                "ProofObligationDecompositionResult is constructed by "
                "decompose_proof_obligations"
            )
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ProofObligationDecompositionResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("ProofObligationDecompositionResult cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("ProofObligationDecompositionResult cannot be pickled")

    def __copy__(self) -> ProofObligationDecompositionResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> ProofObligationDecompositionResult:
        del memo
        return self


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _DecompositionError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _step(steps: list[int], path: str) -> None:
    steps[0] += 1
    if steps[0] > MAX_STEPS:
        _fail("budget", path, "validation-step budget exceeded")


def _freeze(value: object) -> object:
    if type(value) is dict:
        return _FrozenMap(tuple((key, _freeze(item)) for key, item in sorted(value.items())))
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if type(value) is _FrozenMap:
        return {key: _thaw(item) for key, item in value.entries}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _canonical_bytes(value: object, *, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    aggregate = 0
    stack = [(value, 0, "$")]
    while stack:
        item, depth, path = stack.pop()
        if depth > MAX_DEPTH:
            _fail("budget", path, "canonical nesting budget exceeded")
        if item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > MAX_INTEGER:
                _fail("canonical", path, "integer exceeds portable exact range")
            continue
        if type(item) is str:
            if (
                len(item) > MAX_STRING_CODEPOINTS
                or "\x00" in item
                or unicodedata.normalize("NFC", item) != item
            ):
                _fail("canonical", path, "string is oversized, NUL-bearing, or non-NFC")
            aggregate += len(item)
            if aggregate > MAX_AGGREGATE_STRING_CODEPOINTS:
                _fail("budget", path, "aggregate string budget exceeded")
            continue
        if type(item) is tuple or type(item) is list:
            stack.extend((child, depth + 1, f"{path}[{index}]") for index, child in enumerate(item))
            continue
        if type(item) is _FrozenMap:
            item = {key: child for key, child in item.entries}
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
            _thaw(value), ensure_ascii=True, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
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
            raise ProofObligationValidationError("schema", "$", f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def _json_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except ProofObligationValidationError:
        raise
    except RecursionError as exc:
        raise ProofObligationValidationError("budget", path, "JSON nesting budget exceeded") from exc
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ProofObligationValidationError("schema", path, "invalid UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ProofObligationValidationError("schema", path, "expected a JSON object")
    return value


def _indexes(
    projection: dict[str, Any],
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, str]]:
    entities = projection.get("entities")
    if type(entities) is not dict:
        _fail("graph", "$.projection.entities", "missing entity registries")
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    owners: dict[str, str] = {}
    for registry in _ENTITY_REGISTRIES:
        records = entities.get(registry)
        if type(records) is not list:
            _fail("graph", f"$.projection.entities.{registry}", "invalid registry")
        index: dict[str, dict[str, Any]] = {}
        for record in records:
            if type(record) is not dict or type(record.get("id")) is not str:
                _fail("graph", f"$.projection.entities.{registry}", "invalid record")
            entity_id = record["id"]
            if entity_id in index or entity_id in owners:
                _fail("graph", f"$.projection.entities.{registry}", "duplicate identity")
            index[entity_id] = record
            owners[entity_id] = registry
        indexes[registry] = index
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
    origin = indexes.get(origin_registry, {}).get(origin_id)
    if origin is None:
        _fail("graph", f"$.entities.{origin_registry}", f"missing origin {origin_id!r}")
    seen: set[tuple[str, str]] = {(origin_registry, origin_id)}
    pending = [
        (registry, entity_id, 1)
        for registry, entity_id in _dependencies(origin_registry, origin)
    ]
    while pending:
        registry, entity_id, depth = pending.pop()
        _step(steps, f"$.entities.{registry}.{entity_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$", "semantic dependency depth exceeded")
        key = (registry, entity_id)
        if key in seen:
            continue
        record = indexes.get(registry, {}).get(entity_id)
        if record is None:
            _fail("graph", f"$.entities.{registry}", f"missing dependency {entity_id!r}")
        seen.add(key)
        if len(seen) > MAX_DEPENDENCIES:
            _fail("budget", "$", "semantic dependency budget exceeded")
        pending.extend(
            (owner, child, depth + 1)
            for owner, child in _dependencies(registry, record)
        )
    semantic = sorted(
        (registry, entity_id)
        for registry, entity_id in seen
        if registry in _SEMANTIC_REGISTRIES
        and (registry, entity_id) != (origin_registry, origin_id)
    )
    span_ids = tuple(
        sorted(entity_id for registry, entity_id in seen if registry == "source_spans")
    )
    source_ids = tuple(
        sorted(entity_id for registry, entity_id in seen if registry == "source_documents")
    )
    fragment = {
        "origin": {"registry": origin_registry, "record": origin},
        "dependencies": [
            {"registry": registry, "record": indexes[registry][entity_id]}
            for registry, entity_id in semantic
        ],
        "source_spans": [indexes["source_spans"][item] for item in span_ids],
        "source_documents": [indexes["source_documents"][item] for item in source_ids],
    }
    return tuple(entity_id for _registry, entity_id in semantic), span_ids, fragment


def _ordered_unique(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def _context_mapping(context: ProofObligationLocalContext) -> dict[str, Any]:
    return {
        "reading_id": context.reading_id,
        "normalized_context_sha256": context.normalized_context_sha256,
        "definition_ids": list(context.definition_ids),
        "assumption_fact_sha256s": list(context.assumption_fact_sha256s),
        "bound_variable_ids": list(context.bound_variable_ids),
        "local_hypothesis_statement_ids": list(context.local_hypothesis_statement_ids),
        "witness_placeholder_ids": list(context.witness_placeholder_ids),
        "dependency_ids": list(context.dependency_ids),
        "source_span_ids": list(context.source_span_ids),
        "mathematical_authority": context.mathematical_authority,
    }


def _admissibility_mapping(item: StrategyAdmissibility) -> dict[str, Any]:
    return {
        "strategy_id": item.strategy_id,
        "match_rule_id": item.match_rule_id,
        "reason_code": item.reason_code,
        "matched_value": item.matched_value,
        "prerequisite_obligation_ids": list(item.prerequisite_obligation_ids),
        "guarantees_success": item.guarantees_success,
        "mathematical_authority": item.mathematical_authority,
    }


def _obligation_mapping(
    obligation: ProofObligation, *, include_digest: bool = True,
) -> dict[str, Any]:
    value = {
        "obligation_id": obligation.obligation_id,
        "ordinal": obligation.ordinal,
        "reading_id": obligation.reading_id,
        "root_goal_id": obligation.root_goal_id,
        "parent_obligation_id": obligation.parent_obligation_id,
        "rule_id": obligation.rule_id,
        "kind": obligation.kind,
        "goal_mode": obligation.goal_mode,
        "status": obligation.status,
        "statement_id": obligation.statement_id,
        "relation_id": obligation.relation_id,
        "statement_fragment_sha256": obligation.statement_fragment_sha256,
        "source_span_ids": list(obligation.source_span_ids),
        "dependency_ids": list(obligation.dependency_ids),
        "local_context_sha256": obligation.local_context_sha256,
        "child_obligation_ids": list(obligation.child_obligation_ids),
        "prerequisite_obligation_ids": list(obligation.prerequisite_obligation_ids),
        "alternative_group_id": obligation.alternative_group_id,
        "alternative_index": obligation.alternative_index,
        "witness_placeholder_ids": list(obligation.witness_placeholder_ids),
        "admissible_strategies": [
            _admissibility_mapping(item) for item in obligation.admissible_strategies
        ],
        "payload": _thaw(obligation.payload),
        "supported": obligation.supported,
        "mathematical_authority": obligation.mathematical_authority,
    }
    if include_digest:
        value["obligation_sha256"] = obligation.obligation_sha256
    return value


def _graph_mapping(graph: ProofObligationGraph) -> dict[str, Any]:
    return {
        "reading_id": graph.reading_id,
        "projection_sha256": graph.projection_sha256,
        "normalized_context_sha256": graph.normalized_context_sha256,
        "decomposition_catalogue_sha256": graph.decomposition_catalogue_sha256,
        "strategy_catalogue_sha256": graph.strategy_catalogue_sha256,
        "goal_ids": list(graph.goal_ids),
        "root_obligation_ids": list(graph.root_obligation_ids),
        "obligations": [_obligation_mapping(item) for item in graph.obligations],
        "obligation_sha256s": list(graph.obligation_sha256s),
        "local_contexts": [
            {"local_context_sha256": digest, "context": _context_mapping(context)}
            for digest, context in graph.local_contexts
        ],
        "edges": [
            {
                "ordinal": edge.ordinal,
                "from_obligation_id": edge.from_obligation_id,
                "to_obligation_id": edge.to_obligation_id,
                "kind": edge.kind,
            }
            for edge in graph.edges
        ],
        "unsupported_obligation_ids": list(graph.unsupported_obligation_ids),
        "choice_required_obligation_ids": list(graph.choice_required_obligation_ids),
        "mathematical_authority": graph.mathematical_authority,
    }


@dataclass(slots=True)
class _PendingObligation:
    obligation_id: str
    ordinal: int
    reading_id: str
    root_goal_id: str
    parent_obligation_id: str | None
    rule_id: str
    kind: str
    goal_mode: str
    statement_id: str | None
    relation_id: str | None
    statement_fragment_sha256: str
    source_span_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    local_context_sha256: str
    child_obligation_ids: list[str]
    prerequisite_obligation_ids: tuple[str, ...]
    alternative_group_id: str | None
    alternative_index: int | None
    witness_placeholder_ids: tuple[str, ...]
    payload: object
    supported: bool


class _GraphBuilder:
    def __init__(
        self,
        *,
        reading_id: str,
        projection_sha256: str,
        normalized_context_sha256: str,
        projection: dict[str, Any],
        normalized_context: object,
        steps: list[int],
    ) -> None:
        self.reading_id = reading_id
        self.projection_sha256 = projection_sha256
        self.normalized_context_sha256 = normalized_context_sha256
        self.projection = projection
        self.normalized_context = normalized_context
        self.steps = steps
        self.indexes, self.owners = _indexes(projection)
        self.nodes: list[_PendingObligation] = []
        self.contexts: list[tuple[str, ProofObligationLocalContext]] = []
        self.context_index: dict[bytes, str] = {}

    def _context(
        self,
        bound_variables: tuple[str, ...],
        hypotheses: tuple[str, ...],
        witnesses: tuple[str, ...],
    ) -> str:
        bound_variables = _ordered_unique(bound_variables)
        hypotheses = _ordered_unique(hypotheses)
        witnesses = _ordered_unique(witnesses)
        dependencies: set[str] = set()
        spans: set[str] = set()
        definition_ids = tuple(self.projection["definition_ids"])
        for registry, identifiers in (
            ("definitions", definition_ids),
            ("variables", bound_variables),
            ("statements", hypotheses),
        ):
            for entity_id in identifiers:
                child_dependencies, child_spans, _fragment = _closure(
                    registry, entity_id, self.indexes, self.steps
                )
                dependencies.add(entity_id)
                dependencies.update(child_dependencies)
                spans.update(child_spans)
        facts = getattr(self.normalized_context, "facts")
        for fact in facts:
            dependencies.add(fact.origin_id)
            dependencies.update(fact.dependency_ids)
            spans.update(fact.span_ids)
        dependencies.intersection_update(self.owners)
        context = ProofObligationLocalContext(
            reading_id=self.reading_id,
            normalized_context_sha256=self.normalized_context_sha256,
            definition_ids=definition_ids,
            assumption_fact_sha256s=tuple(fact.fact_sha256 for fact in facts),
            bound_variable_ids=bound_variables,
            local_hypothesis_statement_ids=hypotheses,
            witness_placeholder_ids=witnesses,
            dependency_ids=tuple(sorted(dependencies)),
            source_span_ids=tuple(sorted(spans)),
        )
        raw = _canonical_bytes(_context_mapping(context))
        digest = _sha(raw)
        existing = self.context_index.get(raw)
        if existing is not None:
            return existing
        if len(self.contexts) >= MAX_CONTEXTS:
            _fail("budget", "$", "local-context budget exceeded")
        self.context_index[raw] = digest
        self.contexts.append((digest, context))
        return digest

    def _fragment(
        self, statement_id: str, component: dict[str, Any] | None = None,
    ) -> tuple[tuple[str, ...], tuple[str, ...], str]:
        dependencies, spans, fragment = _closure(
            "statements", statement_id, self.indexes, self.steps
        )
        if component is not None:
            fragment = {"statement_fragment": fragment, "component": component}
        return dependencies, spans, _sha(_canonical_bytes(fragment))

    def _reserve(
        self,
        *,
        root_goal_id: str,
        parent_id: str | None,
        rule_id: str,
        kind: str,
        goal_mode: str,
        statement_id: str,
        bound_variables: tuple[str, ...],
        hypotheses: tuple[str, ...],
        witnesses: tuple[str, ...],
        node_witnesses: tuple[str, ...] | None = None,
        prerequisites: tuple[str, ...] = (),
        alternative_group_id: str | None = None,
        alternative_index: int | None = None,
        component: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        supported: bool = True,
    ) -> _PendingObligation:
        if len(self.nodes) >= MAX_OBLIGATIONS:
            _fail("budget", "$", "obligation budget exceeded")
        ordinal = len(self.nodes)
        obligation_id = f"obligation_{ordinal:06d}"
        dependencies, spans, fragment_sha256 = self._fragment(statement_id, component)
        statement = self.indexes["statements"][statement_id]
        relation_id = statement.get("relation_id") if statement["kind"] == "relation" else None
        context_sha256 = self._context(bound_variables, hypotheses, witnesses)
        node = _PendingObligation(
            obligation_id=obligation_id,
            ordinal=ordinal,
            reading_id=self.reading_id,
            root_goal_id=root_goal_id,
            parent_obligation_id=parent_id,
            rule_id=rule_id,
            kind=kind,
            goal_mode=goal_mode,
            statement_id=statement_id,
            relation_id=relation_id,
            statement_fragment_sha256=fragment_sha256,
            source_span_ids=spans,
            dependency_ids=dependencies,
            local_context_sha256=context_sha256,
            child_obligation_ids=[],
            prerequisite_obligation_ids=prerequisites,
            alternative_group_id=alternative_group_id,
            alternative_index=alternative_index,
            witness_placeholder_ids=witnesses if node_witnesses is None else node_witnesses,
            payload=_freeze(payload if payload is not None else {"statement": statement}),
            supported=supported,
        )
        self.nodes.append(node)
        return node

    def _build_statement(
        self,
        *,
        statement_id: str,
        goal_mode: str,
        root_goal_id: str,
        parent_id: str | None,
        bound_variables: tuple[str, ...],
        hypotheses: tuple[str, ...],
        witnesses: tuple[str, ...],
        depth: int,
        alternative_group_id: str | None = None,
        alternative_index: int | None = None,
        root_goal: dict[str, Any] | None = None,
    ) -> str:
        _step(self.steps, f"$.statements.{statement_id}")
        if depth > MAX_DEPTH:
            _fail("budget", "$", "obligation decomposition depth exceeded")
        statement = self.indexes["statements"].get(statement_id)
        if statement is None:
            _fail("graph", "$.statements", f"missing statement {statement_id!r}")
        component = None if root_goal is None else {"root_goal": root_goal}
        payload = {"statement": statement}
        if root_goal is not None:
            payload["root_goal"] = root_goal

        if goal_mode != "prove":
            rule = _MODE_RULES.get(goal_mode)
            if rule is None:
                rule_id, kind, supported = (
                    "mh.obligation.unsupported", "unsupported", False
                )
            else:
                rule_id, kind = rule
                supported = True
            node = self._reserve(
                root_goal_id=root_goal_id,
                parent_id=parent_id,
                rule_id=rule_id,
                kind=kind,
                goal_mode=goal_mode,
                statement_id=statement_id,
                bound_variables=bound_variables,
                hypotheses=hypotheses,
                witnesses=witnesses,
                alternative_group_id=alternative_group_id,
                alternative_index=alternative_index,
                component=component,
                payload=payload,
                supported=supported,
            )
            return node.obligation_id

        match_name = (
            statement.get("operator")
            if statement["kind"] == "logical"
            else statement.get("quantifier")
            if statement["kind"] == "quantified"
            else None
        )
        selected = _PROVE_RULES.get((statement["kind"], match_name))
        if selected is None:
            rule_id, kind, supported = "mh.obligation.unsupported", "unsupported", False
        else:
            rule_id, kind, supported = selected
        node = self._reserve(
            root_goal_id=root_goal_id,
            parent_id=parent_id,
            rule_id=rule_id,
            kind=kind,
            goal_mode=goal_mode,
            statement_id=statement_id,
            bound_variables=bound_variables,
            hypotheses=hypotheses,
            witnesses=witnesses,
            alternative_group_id=alternative_group_id,
            alternative_index=alternative_index,
            component=component,
            payload=payload,
            supported=supported,
        )
        if not supported or statement["kind"] in {"truth", "relation"}:
            return node.obligation_id
        if statement["kind"] == "logical":
            operator = statement["operator"]
            operands = tuple(statement["operand_statement_ids"])
            if operator == "not":
                return node.obligation_id
            if operator in {"and", "or"}:
                group = (
                    f"alternative_{node.obligation_id}"
                    if operator == "or"
                    else None
                )
                for index, child_statement_id in enumerate(operands):
                    child = self._build_statement(
                        statement_id=child_statement_id,
                        goal_mode=goal_mode,
                        root_goal_id=root_goal_id,
                        parent_id=node.obligation_id,
                        bound_variables=bound_variables,
                        hypotheses=hypotheses,
                        witnesses=witnesses,
                        depth=depth + 1,
                        alternative_group_id=group,
                        alternative_index=index if group is not None else None,
                    )
                    node.child_obligation_ids.append(child)
                return node.obligation_id
            if operator == "implies":
                antecedent, consequent = operands
                child = self._build_statement(
                    statement_id=consequent,
                    goal_mode=goal_mode,
                    root_goal_id=root_goal_id,
                    parent_id=node.obligation_id,
                    bound_variables=bound_variables,
                    hypotheses=(*hypotheses, antecedent),
                    witnesses=witnesses,
                    depth=depth + 1,
                )
                node.child_obligation_ids.append(child)
                return node.obligation_id
            if operator == "iff":
                left, right = operands
                for direction, (antecedent, consequent) in enumerate(
                    ((left, right), (right, left))
                ):
                    direction_context = (*hypotheses, antecedent)
                    wrapper = self._reserve(
                        root_goal_id=root_goal_id,
                        parent_id=node.obligation_id,
                        rule_id="mh.obligation.logical.implies",
                        kind="implication",
                        goal_mode=goal_mode,
                        statement_id=consequent,
                        bound_variables=bound_variables,
                        hypotheses=direction_context,
                        witnesses=witnesses,
                        component={
                            "biconditional_statement_id": statement_id,
                            "direction": direction,
                            "antecedent_statement_id": antecedent,
                            "consequent_statement_id": consequent,
                        },
                        payload={
                            "direction": direction,
                            "antecedent_statement_id": antecedent,
                            "consequent_statement_id": consequent,
                        },
                    )
                    child = self._build_statement(
                        statement_id=consequent,
                        goal_mode=goal_mode,
                        root_goal_id=root_goal_id,
                        parent_id=wrapper.obligation_id,
                        bound_variables=bound_variables,
                        hypotheses=direction_context,
                        witnesses=witnesses,
                        depth=depth + 1,
                    )
                    wrapper.child_obligation_ids.append(child)
                    node.child_obligation_ids.append(wrapper.obligation_id)
                return node.obligation_id
        if statement["kind"] == "quantified":
            variables = tuple(statement["variable_ids"])
            body = statement["body_statement_id"]
            if statement["quantifier"] == "forall":
                child = self._build_statement(
                    statement_id=body,
                    goal_mode=goal_mode,
                    root_goal_id=root_goal_id,
                    parent_id=node.obligation_id,
                    bound_variables=(*bound_variables, *variables),
                    hypotheses=hypotheses,
                    witnesses=witnesses,
                    depth=depth + 1,
                )
                node.child_obligation_ids.append(child)
                return node.obligation_id
            placeholders = tuple(
                f"witness_{node.obligation_id}_{variable_id}" for variable_id in variables
            )
            node.witness_placeholder_ids = placeholders
            construction = self._reserve(
                root_goal_id=root_goal_id,
                parent_id=node.obligation_id,
                rule_id="mh.obligation.component.witness-construction",
                kind="witness_construction",
                goal_mode=goal_mode,
                statement_id=statement_id,
                bound_variables=bound_variables,
                hypotheses=hypotheses,
                witnesses=witnesses,
                node_witnesses=placeholders,
                component={"component": "witness_construction", "variable_ids": list(variables)},
                payload={"variable_ids": list(variables), "placeholder_ids": list(placeholders)},
            )
            witness_context = (*witnesses, *placeholders)
            verification = self._reserve(
                root_goal_id=root_goal_id,
                parent_id=node.obligation_id,
                rule_id="mh.obligation.component.witness-verification",
                kind="witness_verification",
                goal_mode=goal_mode,
                statement_id=body,
                bound_variables=(*bound_variables, *variables),
                hypotheses=hypotheses,
                witnesses=witness_context,
                prerequisites=(construction.obligation_id,),
                component={
                    "component": "witness_verification",
                    "quantified_statement_id": statement_id,
                    "placeholder_ids": list(placeholders),
                },
                payload={
                    "body_statement_id": body,
                    "placeholder_ids": list(placeholders),
                },
            )
            body_child = self._build_statement(
                statement_id=body,
                goal_mode=goal_mode,
                root_goal_id=root_goal_id,
                parent_id=verification.obligation_id,
                bound_variables=(*bound_variables, *variables),
                hypotheses=hypotheses,
                witnesses=witness_context,
                depth=depth + 1,
            )
            verification.child_obligation_ids.append(body_child)
            node.child_obligation_ids.extend(
                (construction.obligation_id, verification.obligation_id)
            )
            if statement["quantifier"] == "exists_unique":
                uniqueness = self._reserve(
                    root_goal_id=root_goal_id,
                    parent_id=node.obligation_id,
                    rule_id="mh.obligation.component.uniqueness",
                    kind="uniqueness",
                    goal_mode=goal_mode,
                    statement_id=statement_id,
                    bound_variables=(*bound_variables, *variables),
                    hypotheses=hypotheses,
                    witnesses=witness_context,
                    prerequisites=(construction.obligation_id,),
                    component={
                        "component": "uniqueness",
                        "placeholder_ids": list(placeholders),
                    },
                    payload={
                        "original_statement_id": statement_id,
                        "placeholder_ids": list(placeholders),
                    },
                )
                node.child_obligation_ids.append(uniqueness.obligation_id)
            return node.obligation_id
        return node.obligation_id

    def _strategy_values(self, node: _PendingObligation) -> dict[str, tuple[str, ...]]:
        relation_kind: tuple[str, ...] = ()
        if node.relation_id is not None:
            relation = self.indexes["relations"].get(node.relation_id)
            if relation is not None:
                relation_kind = (relation["kind"],)
        domains: list[str] = []
        carriers: list[str] = []
        for entity_id in node.dependency_ids:
            domain = self.indexes["domains"].get(entity_id)
            if domain is None:
                continue
            domains.append(domain["kind"])
            if domain["kind"] == "builtin":
                carriers.append(domain["name"])
        return {
            "obligation_kind": (node.kind,),
            "goal_mode": (node.goal_mode,),
            "relation_kind": relation_kind,
            "domain_kind": tuple(sorted(set(domains))),
            "builtin_carrier": tuple(sorted(set(carriers))),
        }

    def _strategies(self, node: _PendingObligation) -> tuple[StrategyAdmissibility, ...]:
        available = self._strategy_values(node)
        result: list[StrategyAdmissibility] = []
        for strategy_id, match_rule_id, axis, values, reason in _STRATEGIES:
            matched = next(
                (value for value in values if value in available[axis]), None
            )
            if matched is None:
                continue
            result.append(
                StrategyAdmissibility(
                    strategy_id=strategy_id,
                    match_rule_id=match_rule_id,
                    reason_code=reason,
                    matched_value=matched,
                    prerequisite_obligation_ids=node.prerequisite_obligation_ids,
                )
            )
        if len(result) > MAX_STRATEGIES:
            _fail("budget", "$", "strategy admissibility budget exceeded")
        return tuple(result)

    def build(self) -> ProofObligationGraph:
        goal_ids = tuple(self.projection["goal_ids"])
        if len(goal_ids) > MAX_GOALS:
            _fail("budget", "$", "goal budget exceeded")
        root_ids: list[str] = []
        for goal_id in goal_ids:
            goal = self.indexes["goals"].get(goal_id)
            if goal is None:
                _fail("graph", "$.goals", f"missing goal {goal_id!r}")
            root_ids.append(
                self._build_statement(
                    statement_id=goal["statement_id"],
                    goal_mode=goal["mode"],
                    root_goal_id=goal_id,
                    parent_id=None,
                    bound_variables=(),
                    hypotheses=(),
                    witnesses=(),
                    depth=0,
                    root_goal=goal,
                )
            )
        obligations: list[ProofObligation] = []
        edges: list[ProofObligationEdge] = []
        for pending in self.nodes:
            status = (
                "unsupported"
                if not pending.supported
                else "choice_required"
                if pending.kind == "disjunction"
                else "waiting"
                if pending.child_obligation_ids or pending.prerequisite_obligation_ids
                else "ready"
            )
            provisional = ProofObligation(
                obligation_sha256="0" * 64,
                obligation_id=pending.obligation_id,
                ordinal=pending.ordinal,
                reading_id=pending.reading_id,
                root_goal_id=pending.root_goal_id,
                parent_obligation_id=pending.parent_obligation_id,
                rule_id=pending.rule_id,
                kind=pending.kind,
                goal_mode=pending.goal_mode,
                status=status,
                statement_id=pending.statement_id,
                relation_id=pending.relation_id,
                statement_fragment_sha256=pending.statement_fragment_sha256,
                source_span_ids=pending.source_span_ids,
                dependency_ids=pending.dependency_ids,
                local_context_sha256=pending.local_context_sha256,
                child_obligation_ids=tuple(pending.child_obligation_ids),
                prerequisite_obligation_ids=pending.prerequisite_obligation_ids,
                alternative_group_id=pending.alternative_group_id,
                alternative_index=pending.alternative_index,
                witness_placeholder_ids=pending.witness_placeholder_ids,
                admissible_strategies=self._strategies(pending),
                payload=pending.payload,
                supported=pending.supported,
            )
            digest = _sha(_canonical_bytes(_obligation_mapping(provisional, include_digest=False)))
            obligation = ProofObligation(
                **{
                    field: digest if field == "obligation_sha256" else getattr(provisional, field)
                    for field in ProofObligation.__slots__
                }
            )
            obligations.append(obligation)
            for child in obligation.child_obligation_ids:
                edges.append(
                    ProofObligationEdge(len(edges), obligation.obligation_id, child, "child")
                )
            for prerequisite in obligation.prerequisite_obligation_ids:
                edges.append(
                    ProofObligationEdge(
                        len(edges), obligation.obligation_id, prerequisite, "prerequisite"
                    )
                )
            if len(edges) > MAX_EDGES:
                _fail("budget", "$", "obligation edge budget exceeded")
        return ProofObligationGraph(
            reading_id=self.reading_id,
            projection_sha256=self.projection_sha256,
            normalized_context_sha256=self.normalized_context_sha256,
            decomposition_catalogue_sha256=DECOMPOSITION_CATALOGUE_SHA256,
            strategy_catalogue_sha256=STRATEGY_CATALOGUE_SHA256,
            goal_ids=goal_ids,
            root_obligation_ids=tuple(root_ids),
            obligations=tuple(obligations),
            obligation_sha256s=tuple(item.obligation_sha256 for item in obligations),
            local_contexts=tuple(self.contexts),
            edges=tuple(edges),
            unsupported_obligation_ids=tuple(
                item.obligation_id for item in obligations if not item.supported
            ),
            choice_required_obligation_ids=tuple(
                item.obligation_id for item in obligations if item.status == "choice_required"
            ),
        )


def _diagnostic(error: _DecompositionError) -> ProofObligationDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "context": "INVALID_LOCAL_CONTEXT",
        "domain": "INVALID_DOMAIN_ASSUMPTIONS",
        "graph": "INVALID_OBLIGATION_GRAPH",
        "rule": "INVALID_DECOMPOSITION_CATALOGUE",
        "strategy": "INVALID_STRATEGY_CATALOGUE",
        "type": "INVALID_TYPE",
    }.get(error.kind, "INVALID_OBLIGATION_GRAPH")
    path = error.path if _PATH.fullmatch(error.path) is not None else "$"
    return ProofObligationDiagnostic(
        code=code,
        path=path,
        message=(error.detail[:MAX_DIAGNOSTIC_CODEPOINTS] or "invalid decomposition"),
    )


def _new_result(**values: object) -> ProofObligationDecompositionResult:
    result = ProofObligationDecompositionResult(_token=_RESULT_TOKEN, **values)
    _validate_result_shape(result)
    return result


def _candidate_graph(
    candidate: object,
    projection: dict[str, Any],
    steps: list[int],
) -> ProofObligationCandidate:
    reading_id = getattr(candidate, "reading_id")
    projection_sha256 = getattr(candidate, "projection_sha256")
    normalized_context_sha256 = getattr(candidate, "context_sha256")
    if projection.get("reading_id") != reading_id:
        _fail("graph", "$.candidates", "projection reading identity drift")
    if _sha(_canonical_bytes(projection)) != projection_sha256:
        _fail("graph", "$.candidates", "projection digest drift")
    builder = _GraphBuilder(
        reading_id=reading_id,
        projection_sha256=projection_sha256,
        normalized_context_sha256=normalized_context_sha256,
        projection=projection,
        normalized_context=getattr(candidate, "context"),
        steps=steps,
    )
    graph = builder.build()
    return ProofObligationCandidate(
        reading_id=reading_id,
        projection_sha256=projection_sha256,
        normalized_context_sha256=normalized_context_sha256,
        graph_sha256=_sha(_canonical_bytes(_graph_mapping(graph))),
        graph=graph,
    )


def decompose_proof_obligations(
    domain_result: bytes,
) -> ProofObligationDecompositionResult:
    """Build finite, source-backed obligation graphs without solving them."""
    try:
        if type(domain_result) is not bytes:
            _fail("type", "$", "domain_result must be exact bytes")
        if len(domain_result) > MAX_INPUT_BYTES:
            _fail("budget", "$", "domain-assumption result byte budget exceeded")
        try:
            parsed = parse_domain_assumption_result(domain_result)
        except DomainAssumptionValidationError as exc:
            _fail("budget" if exc.kind == "budget" else "domain", exc.path, str(exc))
        if parsed.status != "normalized":
            _fail("domain", "$.status", "only a normalized MH-042 result can be decomposed")
        if domain_assumption_result_bytes(parsed) != domain_result:
            _fail("domain", "$", "domain-assumption result round-trip drift")
        if len(parsed.candidates) > MAX_READINGS:
            _fail("budget", "$.candidates", "reading budget exceeded")
        raw = _json_object(domain_result, "$")
        readings_result = raw.get("readings_result")
        if type(readings_result) is not dict:
            _fail("domain", "$.readings_result", "missing embedded readings result")
        raw_candidates = readings_result.get("candidates")
        if type(raw_candidates) is not list:
            _fail("domain", "$.readings_result.candidates", "missing projections")
        projections: dict[str, dict[str, Any]] = {}
        for item in raw_candidates:
            if type(item) is not dict or type(item.get("projection")) is not dict:
                _fail("domain", "$.readings_result.candidates", "invalid projection wrapper")
            reading_id = item.get("reading_id")
            if type(reading_id) is not str or reading_id in projections:
                _fail("domain", "$.readings_result.candidates", "duplicate projection")
            projections[reading_id] = item["projection"]
        expected_ids = tuple(candidate.reading_id for candidate in parsed.candidates)
        if set(projections) != set(expected_ids):
            _fail("domain", "$.readings_result.candidates", "projection membership drift")
        steps = [0]
        candidates = tuple(
            _candidate_graph(candidate, projections[candidate.reading_id], steps)
            for candidate in parsed.candidates
        )
        result = _new_result(
            status="decomposed",
            reason_code="DECOMPOSED",
            input_result_sha256=_sha(domain_result),
            domain_result_bytes=domain_result,
            ambiguity_status=parsed.ambiguity_status,
            selected_reading_id=parsed.selected_reading_id,
            candidates=candidates,
            diagnostics=(),
        )
        if len(_result_bytes_unchecked(result)) > MAX_OUTPUT_BYTES:
            _fail("budget", "$", "decomposition result byte budget exceeded")
        return result
    except _DecompositionError as error:
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
                ProofObligationDiagnostic(
                    code="BUDGET_EXHAUSTED",
                    path="$",
                    message="recursive decomposition exceeded the structural budget",
                ),
            ),
        )


def _result_mapping(result: ProofObligationDecompositionResult) -> dict[str, Any]:
    domain_result = (
        None
        if result.domain_result_bytes is None
        else _json_object(result.domain_result_bytes, "$.domain_assumption_result")
    )
    return {
        "schema": result.schema,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "domain_assumption_contract_id": result.domain_assumption_contract_id,
        "domain_assumption_contract_sha256": result.domain_assumption_contract_sha256,
        "reading_analysis_contract_id": result.reading_analysis_contract_id,
        "reading_analysis_contract_sha256": result.reading_analysis_contract_sha256,
        "problem_intake_contract_id": result.problem_intake_contract_id,
        "problem_intake_contract_sha256": result.problem_intake_contract_sha256,
        "problem_ir_contract_id": result.problem_ir_contract_id,
        "problem_ir_contract_sha256": result.problem_ir_contract_sha256,
        "decomposition_catalogue_sha256": result.decomposition_catalogue_sha256,
        "strategy_catalogue_sha256": result.strategy_catalogue_sha256,
        "status": result.status,
        "reason_code": result.reason_code,
        "input_result_sha256": result.input_result_sha256,
        "domain_assumption_result": domain_result,
        "ambiguity_status": result.ambiguity_status,
        "selected_reading_id": result.selected_reading_id,
        "candidates": [
            {
                "reading_id": item.reading_id,
                "projection_sha256": item.projection_sha256,
                "normalized_context_sha256": item.normalized_context_sha256,
                "graph_sha256": item.graph_sha256,
                "graph": _graph_mapping(item.graph),
            }
            for item in result.candidates
        ],
        "diagnostics": [
            {"code": item.code, "path": item.path, "message": item.message}
            for item in result.diagnostics
        ],
        "mathematical_authority": result.mathematical_authority,
    }


def _result_bytes_unchecked(result: ProofObligationDecompositionResult) -> bytes:
    return _canonical_bytes(_result_mapping(result))


def _validate_context(context: object, digest: str, reading_id: str) -> None:
    if type(context) is not ProofObligationLocalContext:
        raise ProofObligationValidationError("type", "$.local_contexts", "invalid context")
    if (
        context.reading_id != reading_id
        or context.mathematical_authority is not False
        or any(
            type(value) is not tuple
            for value in (
                context.definition_ids,
                context.assumption_fact_sha256s,
                context.bound_variable_ids,
                context.local_hypothesis_statement_ids,
                context.witness_placeholder_ids,
                context.dependency_ids,
                context.source_span_ids,
            )
        )
        or context.dependency_ids != tuple(sorted(set(context.dependency_ids)))
        or context.source_span_ids != tuple(sorted(set(context.source_span_ids)))
        or any(
            len(value) != len(set(value))
            for value in (
                context.definition_ids,
                context.assumption_fact_sha256s,
                context.bound_variable_ids,
                context.local_hypothesis_statement_ids,
                context.witness_placeholder_ids,
            )
        )
    ):
        raise ProofObligationValidationError("context", "$.local_contexts", "context drift")
    if digest != _sha(_canonical_bytes(_context_mapping(context))):
        raise ProofObligationValidationError("identity", "$.local_contexts", "context digest drift")


def _validate_obligation(obligation: object, ordinal: int, reading_id: str) -> None:
    if type(obligation) is not ProofObligation:
        raise ProofObligationValidationError("type", "$.obligations", "invalid obligation")
    if (
        obligation.ordinal != ordinal
        or obligation.obligation_id != f"obligation_{ordinal:06d}"
        or obligation.reading_id != reading_id
        or obligation.mathematical_authority is not False
    ):
        raise ProofObligationValidationError("graph", "$.obligations", "obligation position drift")
    shape = _RULE_SHAPES.get(obligation.rule_id)
    if (
        shape is None
        or obligation.kind != shape[0]
        or (shape[1] is not None and obligation.goal_mode != shape[1])
        or obligation.supported is (obligation.rule_id == "mh.obligation.unsupported")
    ):
        raise ProofObligationValidationError("rule", "$.obligations", "rule shape drift")
    expected_status = (
        "unsupported"
        if not obligation.supported
        else "choice_required"
        if obligation.kind == "disjunction"
        else "waiting"
        if obligation.child_obligation_ids or obligation.prerequisite_obligation_ids
        else "ready"
    )
    if obligation.status != expected_status:
        raise ProofObligationValidationError("graph", "$.obligations", "status drift")
    sequence_fields = (
        obligation.source_span_ids,
        obligation.dependency_ids,
        obligation.child_obligation_ids,
        obligation.prerequisite_obligation_ids,
        obligation.witness_placeholder_ids,
        obligation.admissible_strategies,
    )
    if any(type(value) is not tuple for value in sequence_fields):
        raise ProofObligationValidationError("type", "$.obligations", "sequence type drift")
    if (
        obligation.source_span_ids != tuple(sorted(set(obligation.source_span_ids)))
        or obligation.dependency_ids != tuple(sorted(set(obligation.dependency_ids)))
        or any(
            len(value) != len(set(value))
            for value in (
                obligation.child_obligation_ids,
                obligation.prerequisite_obligation_ids,
                obligation.witness_placeholder_ids,
            )
        )
    ):
        raise ProofObligationValidationError("graph", "$.obligations", "sequence drift")
    expected = _sha(_canonical_bytes(_obligation_mapping(obligation, include_digest=False)))
    if obligation.obligation_sha256 != expected:
        raise ProofObligationValidationError("identity", "$.obligations", "obligation digest drift")
    strategy_records = {
        strategy_id: (match_rule_id, frozenset(values), reason)
        for strategy_id, match_rule_id, _axis, values, reason in _STRATEGIES
    }
    seen_strategies: set[str] = set()
    catalogue_positions = {item[0]: index for index, item in enumerate(_STRATEGIES)}
    positions: list[int] = []
    for strategy in obligation.admissible_strategies:
        expected_strategy = (
            strategy_records.get(strategy.strategy_id)
            if type(strategy) is StrategyAdmissibility
            else None
        )
        if (
            type(strategy) is not StrategyAdmissibility
            or expected_strategy is None
            or strategy.strategy_id in seen_strategies
            or strategy.match_rule_id != expected_strategy[0]
            or strategy.matched_value not in expected_strategy[1]
            or strategy.reason_code != expected_strategy[2]
            or strategy.prerequisite_obligation_ids
            != obligation.prerequisite_obligation_ids
            or strategy.guarantees_success is not False
            or strategy.mathematical_authority is not False
        ):
            raise ProofObligationValidationError("strategy", "$.obligations", "strategy drift")
        seen_strategies.add(strategy.strategy_id)
        positions.append(catalogue_positions[strategy.strategy_id])
    if positions != sorted(positions):
        raise ProofObligationValidationError("strategy", "$.obligations", "strategy order drift")


def _validate_graph(graph: object) -> None:
    if type(graph) is not ProofObligationGraph:
        raise ProofObligationValidationError("type", "$.graph", "invalid graph")
    if (
        graph.decomposition_catalogue_sha256 != DECOMPOSITION_CATALOGUE_SHA256
        or graph.strategy_catalogue_sha256 != STRATEGY_CATALOGUE_SHA256
        or graph.mathematical_authority is not False
    ):
        raise ProofObligationValidationError("graph", "$.graph", "graph binding drift")
    if (
        type(graph.goal_ids) is not tuple
        or type(graph.root_obligation_ids) is not tuple
        or type(graph.obligations) is not tuple
        or type(graph.obligation_sha256s) is not tuple
        or type(graph.local_contexts) is not tuple
        or type(graph.edges) is not tuple
        or type(graph.unsupported_obligation_ids) is not tuple
        or type(graph.choice_required_obligation_ids) is not tuple
        or not graph.obligations
    ):
        raise ProofObligationValidationError("graph", "$.graph", "missing obligations")
    for ordinal, obligation in enumerate(graph.obligations):
        _validate_obligation(obligation, ordinal, graph.reading_id)
    ids = tuple(item.obligation_id for item in graph.obligations)
    by_id = {item.obligation_id: item for item in graph.obligations}
    if (
        len(graph.goal_ids) != len(set(graph.goal_ids))
        or len(graph.root_obligation_ids) != len(graph.goal_ids)
        or len(graph.root_obligation_ids) != len(set(graph.root_obligation_ids))
    ):
        raise ProofObligationValidationError("graph", "$.graph", "root index drift")
    if graph.obligation_sha256s != tuple(item.obligation_sha256 for item in graph.obligations):
        raise ProofObligationValidationError("identity", "$.graph", "obligation index drift")
    if any(root not in ids for root in graph.root_obligation_ids):
        raise ProofObligationValidationError("graph", "$.graph", "missing root")
    contexts = {digest for digest, _context in graph.local_contexts}
    if len(contexts) != len(graph.local_contexts):
        raise ProofObligationValidationError("context", "$.graph", "duplicate contexts")
    for digest, context in graph.local_contexts:
        _validate_context(context, digest, graph.reading_id)
        if context.normalized_context_sha256 != graph.normalized_context_sha256:
            raise ProofObligationValidationError(
                "context", "$.graph", "normalized context binding drift"
            )
    expected_edges: list[tuple[str, str, str]] = []
    child_owners: dict[str, str] = {}
    for obligation in graph.obligations:
        if obligation.root_goal_id not in graph.goal_ids:
            raise ProofObligationValidationError("graph", "$.graph", "unknown root goal")
        if obligation.local_context_sha256 not in contexts:
            raise ProofObligationValidationError("context", "$.graph", "missing local context")
        for child in obligation.child_obligation_ids:
            child_node = by_id.get(child)
            if (
                child_node is None
                or child == obligation.obligation_id
                or child_node.ordinal <= obligation.ordinal
                or child_node.parent_obligation_id != obligation.obligation_id
                or child_node.root_goal_id != obligation.root_goal_id
                or child in child_owners
            ):
                raise ProofObligationValidationError("graph", "$.graph", "child ownership drift")
            child_owners[child] = obligation.obligation_id
            expected_edges.append((obligation.obligation_id, child, "child"))
        for prerequisite in obligation.prerequisite_obligation_ids:
            prerequisite_node = by_id.get(prerequisite)
            if (
                prerequisite_node is None
                or prerequisite == obligation.obligation_id
                or prerequisite_node.ordinal >= obligation.ordinal
                or prerequisite_node.root_goal_id != obligation.root_goal_id
            ):
                raise ProofObligationValidationError("graph", "$.graph", "prerequisite drift")
            expected_edges.append((obligation.obligation_id, prerequisite, "prerequisite"))
    for goal_id, root_id in zip(graph.goal_ids, graph.root_obligation_ids, strict=True):
        root = by_id.get(root_id)
        if (
            root is None
            or root.parent_obligation_id is not None
            or root.root_goal_id != goal_id
            or root_id in child_owners
        ):
            raise ProofObligationValidationError("graph", "$.graph", "root ownership drift")
    root_set = set(graph.root_obligation_ids)
    for obligation in graph.obligations:
        if obligation.obligation_id not in root_set and (
            obligation.parent_obligation_id is None
            or child_owners.get(obligation.obligation_id)
            != obligation.parent_obligation_id
        ):
            raise ProofObligationValidationError("graph", "$.graph", "unreachable obligation")
        if obligation.alternative_group_id is None:
            if obligation.alternative_index is not None:
                raise ProofObligationValidationError("graph", "$.graph", "alternative drift")
        else:
            parent = by_id.get(obligation.parent_obligation_id or "")
            if (
                parent is None
                or parent.kind != "disjunction"
                or obligation.alternative_group_id
                != f"alternative_{parent.obligation_id}"
                or obligation.alternative_index is None
            ):
                raise ProofObligationValidationError("graph", "$.graph", "alternative drift")
    for obligation in graph.obligations:
        if obligation.kind == "disjunction":
            alternatives = [by_id[item] for item in obligation.child_obligation_ids]
            if (
                [item.alternative_index for item in alternatives]
                != list(range(len(alternatives)))
                or any(
                    item.alternative_group_id
                    != f"alternative_{obligation.obligation_id}"
                    for item in alternatives
                )
            ):
                raise ProofObligationValidationError("graph", "$.graph", "choice drift")
    actual_edges: list[tuple[str, str, str]] = []
    for ordinal, edge in enumerate(graph.edges):
        if type(edge) is not ProofObligationEdge or edge.ordinal != ordinal:
            raise ProofObligationValidationError("graph", "$.edges", "edge position drift")
        if edge.from_obligation_id not in ids or edge.to_obligation_id not in ids:
            raise ProofObligationValidationError("graph", "$.edges", "dangling edge")
        actual_edges.append((edge.from_obligation_id, edge.to_obligation_id, edge.kind))
    if actual_edges != expected_edges:
        raise ProofObligationValidationError("graph", "$.edges", "edge index drift")
    if graph.unsupported_obligation_ids != tuple(
        item.obligation_id for item in graph.obligations if not item.supported
    ):
        raise ProofObligationValidationError("graph", "$.graph", "unsupported index drift")
    if graph.choice_required_obligation_ids != tuple(
        item.obligation_id for item in graph.obligations if item.status == "choice_required"
    ):
        raise ProofObligationValidationError("graph", "$.graph", "choice index drift")


def _validate_result_shape(result: object) -> None:
    if type(result) is not ProofObligationDecompositionResult:
        raise ProofObligationValidationError(
            "type", "$", "expected exact ProofObligationDecompositionResult"
        )
    constants = {
        "schema": RESULT_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "domain_assumption_contract_id": DOMAIN_ASSUMPTION_CONTRACT_ID,
        "domain_assumption_contract_sha256": DOMAIN_ASSUMPTION_CONTRACT_SHA256,
        "reading_analysis_contract_id": READING_ANALYSIS_CONTRACT_ID,
        "reading_analysis_contract_sha256": READING_ANALYSIS_CONTRACT_SHA256,
        "problem_intake_contract_id": PROBLEM_INTAKE_CONTRACT_ID,
        "problem_intake_contract_sha256": PROBLEM_INTAKE_CONTRACT_SHA256,
        "problem_ir_contract_id": PROBLEM_IR_CONTRACT_ID,
        "problem_ir_contract_sha256": PROBLEM_IR_CONTRACT_SHA256,
        "decomposition_catalogue_sha256": DECOMPOSITION_CATALOGUE_SHA256,
        "strategy_catalogue_sha256": STRATEGY_CATALOGUE_SHA256,
        "mathematical_authority": False,
    }
    for field, expected in constants.items():
        actual = getattr(result, field, None)
        if type(actual) is not type(expected) or actual != expected:
            raise ProofObligationValidationError("result", f"$.{field}", "binding drift")
    if result.status not in {"decomposed", "invalid", "exhausted"}:
        raise ProofObligationValidationError("result", "$.status", "unknown status")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > 32:
        raise ProofObligationValidationError("result", "$.diagnostics", "invalid diagnostics")
    for diagnostic in result.diagnostics:
        if (
            type(diagnostic) is not ProofObligationDiagnostic
            or type(diagnostic.code) is not str
            or type(diagnostic.path) is not str
            or _PATH.fullmatch(diagnostic.path) is None
            or type(diagnostic.message) is not str
            or not diagnostic.message
            or len(diagnostic.message) > MAX_DIAGNOSTIC_CODEPOINTS
        ):
            raise ProofObligationValidationError("result", "$.diagnostics", "diagnostic drift")
    if result.status != "decomposed":
        empty = (
            result.input_result_sha256 is None
            and result.domain_result_bytes is None
            and result.ambiguity_status is None
            and result.selected_reading_id is None
            and result.candidates == ()
        )
        if not empty or not result.diagnostics or result.reason_code != result.diagnostics[0].code:
            raise ProofObligationValidationError("result", "$", "failed combination drift")
        if result.status == "exhausted" and result.reason_code != "BUDGET_EXHAUSTED":
            raise ProofObligationValidationError("result", "$", "exhausted reason drift")
        if result.status == "invalid" and result.reason_code == "BUDGET_EXHAUSTED":
            raise ProofObligationValidationError("result", "$", "invalid reason drift")
        return
    if result.reason_code != "DECOMPOSED" or result.diagnostics:
        raise ProofObligationValidationError("result", "$", "decomposed combination drift")
    if (
        type(result.domain_result_bytes) is not bytes
        or type(result.input_result_sha256) is not str
        or _sha(result.domain_result_bytes) != result.input_result_sha256
    ):
        raise ProofObligationValidationError("identity", "$", "input identity drift")
    if result.ambiguity_status not in {"unambiguous", "unresolved", "resolved"}:
        raise ProofObligationValidationError("result", "$.ambiguity_status", "state drift")
    if type(result.candidates) is not tuple or not result.candidates:
        raise ProofObligationValidationError("result", "$.candidates", "missing candidates")
    ids = tuple(item.reading_id for item in result.candidates if type(item) is ProofObligationCandidate)
    if len(ids) != len(result.candidates) or ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
        raise ProofObligationValidationError("result", "$.candidates", "candidate drift")
    for candidate in result.candidates:
        _validate_graph(candidate.graph)
        if (
            candidate.reading_id != candidate.graph.reading_id
            or candidate.projection_sha256 != candidate.graph.projection_sha256
            or candidate.normalized_context_sha256 != candidate.graph.normalized_context_sha256
            or candidate.graph_sha256 != _sha(_canonical_bytes(_graph_mapping(candidate.graph)))
        ):
            raise ProofObligationValidationError("identity", "$.candidates", "graph digest drift")


def validate_proof_obligation_result(result: object) -> None:
    """Recompute a closed decomposition result before it is consumed."""
    _validate_result_shape(result)
    assert type(result) is ProofObligationDecompositionResult
    if result.status == "decomposed":
        assert result.domain_result_bytes is not None
        expected = decompose_proof_obligations(result.domain_result_bytes)
        if expected != result:
            raise ProofObligationValidationError("result", "$", "decomposition replay drift")


def proof_obligation_bytes(obligation: ProofObligation) -> bytes:
    """Return canonical bytes for one validated obligation."""
    _validate_obligation(obligation, obligation.ordinal, obligation.reading_id)
    return _canonical_bytes(_obligation_mapping(obligation))


def proof_obligation_local_context_bytes(context: ProofObligationLocalContext) -> bytes:
    """Return canonical bytes for one local context."""
    if type(context) is not ProofObligationLocalContext:
        raise ProofObligationValidationError("type", "$", "expected exact local context")
    try:
        digest = _sha(_canonical_bytes(_context_mapping(context)))
    except _DecompositionError as exc:
        raise ProofObligationValidationError(exc.kind, exc.path, exc.detail) from exc
    _validate_context(context, digest, context.reading_id)
    return _canonical_bytes(_context_mapping(context))


def proof_obligation_graph_bytes(graph: ProofObligationGraph) -> bytes:
    """Return canonical bytes for one validated graph."""
    _validate_graph(graph)
    return _canonical_bytes(_graph_mapping(graph))


def proof_obligation_result_bytes(result: ProofObligationDecompositionResult) -> bytes:
    """Serialize one closed result to canonical replayable JSON bytes."""
    validate_proof_obligation_result(result)
    try:
        return _result_bytes_unchecked(result)
    except _DecompositionError as exc:
        raise ProofObligationValidationError(exc.kind, exc.path, exc.detail) from exc


def proof_obligation_result_sha256(result: ProofObligationDecompositionResult) -> str:
    """Return the full SHA-256 identity of canonical decomposition bytes."""
    return _sha(proof_obligation_result_bytes(result))


def parse_proof_obligation_result(data: bytes) -> ProofObligationDecompositionResult:
    """Parse canonical bytes and replay every successful graph."""
    if type(data) is not bytes:
        raise ProofObligationValidationError("type", "$", "result must be exact bytes")
    if len(data) > MAX_OUTPUT_BYTES:
        raise ProofObligationValidationError("budget", "$", "result byte budget exceeded")
    value = _json_object(data, "$")
    try:
        if _canonical_bytes(value) != data:
            raise ProofObligationValidationError("canonical", "$", "result is noncanonical")
    except _DecompositionError as exc:
        raise ProofObligationValidationError(exc.kind, exc.path, exc.detail) from exc
    fields = {
        "schema", "contract_id", "contract_sha256", "domain_assumption_contract_id",
        "domain_assumption_contract_sha256", "reading_analysis_contract_id",
        "reading_analysis_contract_sha256", "problem_intake_contract_id",
        "problem_intake_contract_sha256", "problem_ir_contract_id",
        "problem_ir_contract_sha256", "decomposition_catalogue_sha256",
        "strategy_catalogue_sha256", "status", "reason_code", "input_result_sha256",
        "domain_assumption_result", "ambiguity_status", "selected_reading_id",
        "candidates", "diagnostics", "mathematical_authority",
    }
    if set(value) != fields:
        raise ProofObligationValidationError("schema", "$", "result field set drift")
    if value["status"] == "decomposed":
        embedded = value["domain_assumption_result"]
        if type(embedded) is not dict:
            raise ProofObligationValidationError("schema", "$.domain_assumption_result", "missing input")
        try:
            input_bytes = _canonical_bytes(embedded, maximum=MAX_INPUT_BYTES)
        except _DecompositionError as exc:
            raise ProofObligationValidationError(exc.kind, exc.path, exc.detail) from exc
        expected = decompose_proof_obligations(input_bytes)
        if expected.status != "decomposed" or _result_mapping(expected) != value:
            raise ProofObligationValidationError("result", "$", "historical replay drift")
        if _result_bytes_unchecked(expected) != data:
            raise ProofObligationValidationError("canonical", "$", "result round-trip drift")
        return expected
    raw_diagnostics = value["diagnostics"]
    if type(raw_diagnostics) is not list:
        raise ProofObligationValidationError("schema", "$.diagnostics", "expected array")
    diagnostics: list[ProofObligationDiagnostic] = []
    for index, raw in enumerate(raw_diagnostics):
        if type(raw) is not dict or set(raw) != {"code", "path", "message"}:
            raise ProofObligationValidationError(
                "schema", f"$.diagnostics[{index}]", "diagnostic field drift"
            )
        diagnostics.append(ProofObligationDiagnostic(**raw))
    result = ProofObligationDecompositionResult(
        schema=value["schema"],
        contract_id=value["contract_id"],
        contract_sha256=value["contract_sha256"],
        domain_assumption_contract_id=value["domain_assumption_contract_id"],
        domain_assumption_contract_sha256=value["domain_assumption_contract_sha256"],
        reading_analysis_contract_id=value["reading_analysis_contract_id"],
        reading_analysis_contract_sha256=value["reading_analysis_contract_sha256"],
        problem_intake_contract_id=value["problem_intake_contract_id"],
        problem_intake_contract_sha256=value["problem_intake_contract_sha256"],
        problem_ir_contract_id=value["problem_ir_contract_id"],
        problem_ir_contract_sha256=value["problem_ir_contract_sha256"],
        decomposition_catalogue_sha256=value["decomposition_catalogue_sha256"],
        strategy_catalogue_sha256=value["strategy_catalogue_sha256"],
        status=value["status"],
        reason_code=value["reason_code"],
        input_result_sha256=value["input_result_sha256"],
        domain_result_bytes=None,
        ambiguity_status=value["ambiguity_status"],
        selected_reading_id=value["selected_reading_id"],
        candidates=(),
        diagnostics=tuple(diagnostics),
        mathematical_authority=value["mathematical_authority"],
        _token=_RESULT_TOKEN,
    )
    _validate_result_shape(result)
    if _result_bytes_unchecked(result) != data:
        raise ProofObligationValidationError("canonical", "$", "failed result round-trip drift")
    return result
