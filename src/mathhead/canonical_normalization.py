"""Contract-first canonical normalization of accepted MH-043 obligation graphs.

This MH-044 boundary is deliberately representation-only.  It accepts exact
canonical MH-043 bytes, replay-validates them, and emits immutable canonical
forms and reversible source-occurrence traces.  It never solves, simplifies,
selects a reading, or claims mathematical equivalence or authority.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, NoReturn
import unicodedata

from mathhead.proof_obligations import (
    CONTRACT_ID as PROOF_OBLIGATION_CONTRACT_ID,
    CONTRACT_SHA256 as PROOF_OBLIGATION_CONTRACT_SHA256,
    ProofObligationValidationError,
    parse_proof_obligation_result,
    proof_obligation_result_bytes,
)


CONTRACT_ID: Final = "MH-C-CANONICAL-NORMALIZATION-001"
CONTRACT_SHA256: Final = \
    "ad2a58afc455fed01310b125f3ae7e0597642e849fd10b86149c31a13b9249c8"
RULE_CATALOGUE_SHA256: Final = \
    "6f73efb9455198422a193424411dcad09328c1ae2c38b3997840b97b04f79eb4"
DOMAIN_ASSUMPTION_CONTRACT_ID: Final = \
    "MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001"
DOMAIN_ASSUMPTION_CONTRACT_SHA256: Final = \
    "609bc3a0773016f73d4bcee21d6aef034c74bb8edb36fddd9b6df1a4f4ba219a"
READING_ANALYSIS_CONTRACT_ID: Final = "MH-C-READING-ANALYSIS-002"
READING_ANALYSIS_CONTRACT_SHA256: Final = \
    "0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70"
PROBLEM_INTAKE_CONTRACT_ID: Final = "MH-C-PROBLEM-INTAKE-001"
PROBLEM_INTAKE_CONTRACT_SHA256: Final = \
    "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc"
PROBLEM_IR_CONTRACT_ID: Final = "MH-C-PROBLEM-IR-002"
PROBLEM_IR_CONTRACT_SHA256: Final = \
    "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286"

RESULT_SCHEMA: Final = "mathhead.canonical-normalization-result.v1"
FORM_SCHEMA: Final = "mathhead.canonical-normal-form.v1"
TRACE_SCHEMA: Final = "mathhead.canonical-occurrence-trace.v1"
CONTEXT_SCHEMA: Final = "mathhead.canonical-context.v1"
OBLIGATION_SCHEMA: Final = "mathhead.canonical-obligation.v1"

MAX_INPUT_BYTES: Final = 536_870_912
MAX_OUTPUT_BYTES: Final = 1_073_741_824
MAX_READINGS: Final = 100_000
MAX_GOALS: Final = 100_000
MAX_DOMAINS: Final = 400_000
MAX_VARIABLES: Final = 400_000
MAX_BINDERS: Final = 400_000
MAX_DEFINITIONS: Final = 100_000
MAX_ASSUMPTIONS: Final = 400_000
MAX_FACTS: Final = 400_000
MAX_EXPRESSIONS: Final = 400_000
MAX_RELATIONS: Final = 400_000
MAX_STATEMENTS: Final = 400_000
MAX_OPERANDS: Final = 2_400_000
MAX_OBLIGATIONS: Final = 800_000
MAX_CONTEXTS: Final = 800_000
MAX_FORMS: Final = 2_400_000
MAX_TRACES: Final = 2_400_000
MAX_DEPENDENCIES: Final = 2_400_000
MAX_SOURCE_SPANS: Final = 1_200_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 67_108_864
MAX_NESTING: Final = 512
MAX_STEPS: Final = 64_000_000
MAX_INTEGER: Final = 9_007_199_254_740_991

_SHA_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_ID_RE: Final = re.compile(r"^[a-z][a-z0-9_]*$")
_OBLIGATION_RE: Final = re.compile(r"^obligation_([0-9]{6})$")
_RULE_RE: Final = re.compile(r"^mh[.]canonical[.][a-z0-9_.-]+$")

_REGISTRY_ORDER: Final = {
    "domains": 0,
    "variables": 1,
    "expressions": 2,
    "relations": 3,
    "statements": 4,
    "definitions": 5,
    "assumption_facts": 6,
    "local_contexts": 7,
    "obligations": 8,
}
_FORM_KINDS: Final = {
    "domains": "domain",
    "variables": "variable",
    "expressions": "expression",
    "relations": "relation",
    "statements": "statement",
    "definitions": "definition",
    "assumption_facts": "assumption_fact",
    "local_contexts": "local_context",
    "obligations": "obligation",
}
_ROLE_ORDER: Final = {
    None: 0,
    "domain_fact": 0,
    "variable_fact": 1,
    "domain_constraint": 2,
    "given": 3,
    "side_condition": 4,
    "unsupported": 5,
}
_COMMUTATIVE_STATEMENTS: Final = {
    "and": "mh.canonical.commutative.logical-and",
    "or": "mh.canonical.commutative.logical-or",
    "iff": "mh.canonical.commutative.logical-iff",
}
_COMMUTATIVE_RELATIONS: Final = {
    "equal": "mh.canonical.commutative.relation-equal",
    "not_equal": "mh.canonical.commutative.relation-not-equal",
}
_COMMUTATIVE_OBLIGATION_RULES: Final = {
    "mh.obligation.logical.and",
    "mh.obligation.logical.or",
    "mh.obligation.logical.iff",
}
_PRESERVE_RULE: Final = "mh.canonical.preserve.ordered"
_OPAQUE_RULE: Final = "mh.canonical.preserve.opaque"
_BOUND_RULE: Final = "mh.canonical.alpha.quantified-binder"
_PARAMETER_RULE: Final = "mh.canonical.alpha.definition-parameter"
_WITNESS_RULE: Final = "mh.canonical.alpha.witness-slot"
_ASSUMPTION_RULE: Final = "mh.canonical.order.assumption-facts"
_HYPOTHESIS_RULE: Final = "mh.canonical.order.local-hypotheses"

_RESULT_TOKEN = object()


class CanonicalNormalizationValidationError(ValueError):
    """A classified strict-codec or closed-value validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{kind} at {path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


class _NormalizationError(ValueError):
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
class CanonicalNormalizationDiagnostic:
    code: str
    path: str
    message: str

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalNormalizationDiagnostic cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalNormalForm:
    form_kind: str
    source_registry: str
    source_ref: str
    semantic_sha256: str
    rule_ids: tuple[str, ...]
    value: object
    supported: bool
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalNormalForm cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalOccurrenceTrace:
    trace_id: str
    kind: str
    owner_kind: str
    owner_ref: str
    source_ref: str
    source_index: int
    canonical_index: int
    semantic_sha256: str
    rule_id: str
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalOccurrenceTrace cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalOccurrence:
    source_ref: str
    semantic_sha256: str
    role: str
    source_index: int
    canonical_index: int

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalOccurrence cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalContext:
    reading_id: str
    source_local_context_sha256: str
    semantic_sha256: str
    semantic_value: object
    definition_occurrences: tuple[CanonicalOccurrence, ...]
    assumption_occurrences: tuple[CanonicalOccurrence, ...]
    bound_variable_occurrences: tuple[CanonicalOccurrence, ...]
    hypothesis_occurrences: tuple[CanonicalOccurrence, ...]
    witness_occurrences: tuple[CanonicalOccurrence, ...]
    dependency_semantic_sha256s: tuple[str, ...]
    source_span_ids: tuple[str, ...]
    trace_ids: tuple[str, ...]
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalContext cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalObligation:
    reading_id: str
    source_obligation_id: str
    source_obligation_sha256: str
    ordinal: int
    root_goal_id: str
    parent_ordinal: int | None
    rule_id: str
    kind: str
    goal_mode: str
    status: str
    source_statement_id: str | None
    source_relation_id: str | None
    statement_semantic_sha256: str
    statement_normal_form: object
    local_context_semantic_sha256: str
    child_ordinals: tuple[int, ...]
    prerequisite_ordinals: tuple[int, ...]
    alternative_group_ordinal: int | None
    alternative_index: int | None
    witness_slots: tuple[int, ...]
    strategy_ids: tuple[str, ...]
    strategy_record_sha256s: tuple[str, ...]
    dependency_semantic_sha256s: tuple[str, ...]
    source_span_ids: tuple[str, ...]
    trace_ids: tuple[str, ...]
    semantic_sha256: str
    semantic_value: object
    supported: bool
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalObligation cannot be pickled")


@dataclass(frozen=True, slots=True)
class CanonicalNormalizationCandidate:
    reading_id: str
    source_graph_sha256: str
    semantic_graph_sha256: str
    goal_ids: tuple[str, ...]
    root_ordinals: tuple[int, ...]
    normal_forms: tuple[CanonicalNormalForm, ...]
    contexts: tuple[CanonicalContext, ...]
    obligations: tuple[CanonicalObligation, ...]
    traces: tuple[CanonicalOccurrenceTrace, ...]
    unsupported_semantic_sha256s: tuple[str, ...]
    mathematical_authority: bool = False

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalNormalizationCandidate cannot be pickled")


@dataclass(frozen=True, slots=True, init=False)
class CanonicalNormalizationResult:
    schema: str
    contract_id: str
    contract_sha256: str
    proof_obligation_contract_id: str
    proof_obligation_contract_sha256: str
    domain_assumption_contract_id: str
    domain_assumption_contract_sha256: str
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
    proof_result_bytes: bytes | None
    ambiguity_status: str | None
    selected_reading_id: str | None
    candidates: tuple[CanonicalNormalizationCandidate, ...]
    diagnostics: tuple[CanonicalNormalizationDiagnostic, ...]
    result_sha256: str | None
    mathematical_authority: bool

    def __init__(
        self,
        *,
        schema: str = RESULT_SCHEMA,
        contract_id: str = CONTRACT_ID,
        contract_sha256: str = CONTRACT_SHA256,
        proof_obligation_contract_id: str = PROOF_OBLIGATION_CONTRACT_ID,
        proof_obligation_contract_sha256: str = PROOF_OBLIGATION_CONTRACT_SHA256,
        domain_assumption_contract_id: str = DOMAIN_ASSUMPTION_CONTRACT_ID,
        domain_assumption_contract_sha256: str = DOMAIN_ASSUMPTION_CONTRACT_SHA256,
        reading_analysis_contract_id: str = READING_ANALYSIS_CONTRACT_ID,
        reading_analysis_contract_sha256: str = READING_ANALYSIS_CONTRACT_SHA256,
        problem_intake_contract_id: str = PROBLEM_INTAKE_CONTRACT_ID,
        problem_intake_contract_sha256: str = PROBLEM_INTAKE_CONTRACT_SHA256,
        problem_ir_contract_id: str = PROBLEM_IR_CONTRACT_ID,
        problem_ir_contract_sha256: str = PROBLEM_IR_CONTRACT_SHA256,
        rule_catalogue_sha256: str = RULE_CATALOGUE_SHA256,
        status: str = "invalid",
        reason_code: str = "INVALID_TYPE",
        input_result_sha256: str | None = None,
        proof_result_bytes: bytes | None = None,
        ambiguity_status: str | None = None,
        selected_reading_id: str | None = None,
        candidates: tuple[CanonicalNormalizationCandidate, ...] = (),
        diagnostics: tuple[CanonicalNormalizationDiagnostic, ...] = (),
        result_sha256: str | None = None,
        mathematical_authority: bool = False,
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError(
                "CanonicalNormalizationResult is constructed by "
                "normalize_canonical_obligations"
            )
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("CanonicalNormalizationResult is final")

    def __reduce__(self) -> NoReturn:
        raise TypeError("CanonicalNormalizationResult cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("CanonicalNormalizationResult cannot be pickled")

    def __copy__(self) -> CanonicalNormalizationResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> CanonicalNormalizationResult:
        del memo
        return self


@dataclass(frozen=True, slots=True)
class _Frame:
    kind: str
    variable_ids: tuple[str, ...]


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _NormalizationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _step(steps: list[int], path: str, count: int = 1) -> None:
    steps[0] += count
    if steps[0] > MAX_STEPS:
        _fail("budget", path, "normalization-step budget exceeded")


def _freeze(value: object) -> object:
    if isinstance(value, dict):
        return _FrozenMap(tuple((key, _freeze(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: object) -> object:
    if isinstance(value, _FrozenMap):
        return {key: _thaw(item) for key, item in value.entries}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical_bytes(value: object, *, maximum: int = MAX_OUTPUT_BYTES) -> bytes:
    aggregate = 0
    seen: set[int] = set()

    def check(item: object, path: str, depth: int) -> None:
        nonlocal aggregate
        if depth > MAX_NESTING:
            _fail("budget", path, "canonical nesting budget exceeded")
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            if not -MAX_INTEGER <= item <= MAX_INTEGER:
                _fail("canonical", path, "integer exceeds portable exact range")
            return
        if type(item) is str:
            aggregate += len(item)
            if (
                len(item) > MAX_STRING_CODEPOINTS
                or "\x00" in item
                or unicodedata.normalize("NFC", item) != item
                or aggregate > MAX_AGGREGATE_STRING_CODEPOINTS
            ):
                _fail("canonical", path, "string is oversized, NUL-bearing, or non-NFC")
            return
        if type(item) in (list, tuple) or isinstance(item, _FrozenMap) or type(item) is dict:
            marker = id(item)
            if marker in seen:
                _fail("canonical", path, "cyclic canonical value")
            seen.add(marker)
            try:
                if isinstance(item, _FrozenMap):
                    pairs = item.entries
                    for key, child in pairs:
                        check(key, f"{path}.<key>", depth + 1)
                        check(child, f"{path}.{key}", depth + 1)
                elif type(item) is dict:
                    for key, child in item.items():
                        if type(key) is not str:
                            _fail("canonical", path, "object key is not an exact string")
                        check(key, f"{path}.<key>", depth + 1)
                        check(child, f"{path}.{key}", depth + 1)
                else:
                    for index, child in enumerate(item):
                        check(child, f"{path}[{index}]", depth + 1)
            finally:
                seen.remove(marker)
            return
        _fail("canonical", path, "floats, subclasses, and non-JSON values are forbidden")

    check(value, "$", 0)
    rendered = json.dumps(
        _thaw(value), ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    if len(rendered) > maximum:
        _fail("budget", "$", "canonical output byte budget exceeded")
    return rendered


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("schema", "$", f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _json_object(data: bytes, path: str) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except _NormalizationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("canonical", path, f"value is not strict UTF-8 JSON: {exc}")
    if type(value) is not dict:
        _fail("schema", path, "root must be an exact JSON object")
    return value


def _form_mapping(form: CanonicalNormalForm) -> dict[str, Any]:
    return {
        "schema": FORM_SCHEMA,
        "form_kind": form.form_kind,
        "source_registry": form.source_registry,
        "source_ref": form.source_ref,
        "semantic_sha256": form.semantic_sha256,
        "rule_ids": list(form.rule_ids),
        "value": _thaw(form.value),
        "supported": form.supported,
        "mathematical_authority": form.mathematical_authority,
    }


def _trace_mapping(trace: CanonicalOccurrenceTrace) -> dict[str, Any]:
    return {
        "schema": TRACE_SCHEMA,
        "trace_id": trace.trace_id,
        "kind": trace.kind,
        "owner_kind": trace.owner_kind,
        "owner_ref": trace.owner_ref,
        "source_ref": trace.source_ref,
        "source_index": trace.source_index,
        "canonical_index": trace.canonical_index,
        "semantic_sha256": trace.semantic_sha256,
        "rule_id": trace.rule_id,
        "mathematical_authority": trace.mathematical_authority,
    }


def _occurrence_mapping(item: CanonicalOccurrence) -> dict[str, Any]:
    return {
        "source_ref": item.source_ref,
        "semantic_sha256": item.semantic_sha256,
        "role": item.role,
        "source_index": item.source_index,
        "canonical_index": item.canonical_index,
    }


def _context_mapping(context: CanonicalContext) -> dict[str, Any]:
    return {
        "schema": CONTEXT_SCHEMA,
        "reading_id": context.reading_id,
        "source_local_context_sha256": context.source_local_context_sha256,
        "semantic_sha256": context.semantic_sha256,
        "semantic_value": _thaw(context.semantic_value),
        "definition_occurrences": [
            _occurrence_mapping(item) for item in context.definition_occurrences
        ],
        "assumption_occurrences": [
            _occurrence_mapping(item) for item in context.assumption_occurrences
        ],
        "bound_variable_occurrences": [
            _occurrence_mapping(item) for item in context.bound_variable_occurrences
        ],
        "hypothesis_occurrences": [
            _occurrence_mapping(item) for item in context.hypothesis_occurrences
        ],
        "witness_occurrences": [
            _occurrence_mapping(item) for item in context.witness_occurrences
        ],
        "dependency_semantic_sha256s": list(context.dependency_semantic_sha256s),
        "source_span_ids": list(context.source_span_ids),
        "trace_ids": list(context.trace_ids),
        "mathematical_authority": context.mathematical_authority,
    }


def _obligation_mapping(obligation: CanonicalObligation) -> dict[str, Any]:
    return {
        "schema": OBLIGATION_SCHEMA,
        "reading_id": obligation.reading_id,
        "source_obligation_id": obligation.source_obligation_id,
        "source_obligation_sha256": obligation.source_obligation_sha256,
        "ordinal": obligation.ordinal,
        "root_goal_id": obligation.root_goal_id,
        "parent_ordinal": obligation.parent_ordinal,
        "rule_id": obligation.rule_id,
        "kind": obligation.kind,
        "goal_mode": obligation.goal_mode,
        "status": obligation.status,
        "source_statement_id": obligation.source_statement_id,
        "source_relation_id": obligation.source_relation_id,
        "statement_semantic_sha256": obligation.statement_semantic_sha256,
        "statement_normal_form": _thaw(obligation.statement_normal_form),
        "local_context_semantic_sha256": obligation.local_context_semantic_sha256,
        "child_ordinals": list(obligation.child_ordinals),
        "prerequisite_ordinals": list(obligation.prerequisite_ordinals),
        "alternative_group_ordinal": obligation.alternative_group_ordinal,
        "alternative_index": obligation.alternative_index,
        "witness_slots": list(obligation.witness_slots),
        "strategy_ids": list(obligation.strategy_ids),
        "strategy_record_sha256s": list(obligation.strategy_record_sha256s),
        "dependency_semantic_sha256s": list(obligation.dependency_semantic_sha256s),
        "source_span_ids": list(obligation.source_span_ids),
        "trace_ids": list(obligation.trace_ids),
        "semantic_sha256": obligation.semantic_sha256,
        "semantic_value": _thaw(obligation.semantic_value),
        "supported": obligation.supported,
        "mathematical_authority": obligation.mathematical_authority,
    }


def _candidate_mapping(candidate: CanonicalNormalizationCandidate) -> dict[str, Any]:
    return {
        "reading_id": candidate.reading_id,
        "source_graph_sha256": candidate.source_graph_sha256,
        "semantic_graph_sha256": candidate.semantic_graph_sha256,
        "goal_ids": list(candidate.goal_ids),
        "root_ordinals": list(candidate.root_ordinals),
        "normal_forms": [_form_mapping(item) for item in candidate.normal_forms],
        "contexts": [_context_mapping(item) for item in candidate.contexts],
        "obligations": [_obligation_mapping(item) for item in candidate.obligations],
        "traces": [_trace_mapping(item) for item in candidate.traces],
        "unsupported_semantic_sha256s": list(
            candidate.unsupported_semantic_sha256s
        ),
        "mathematical_authority": candidate.mathematical_authority,
    }


def _result_mapping(
    result: CanonicalNormalizationResult, *, include_digest: bool = True,
) -> dict[str, Any]:
    proof_result = (
        None
        if result.proof_result_bytes is None
        else _json_object(result.proof_result_bytes, "$.proof_obligation_result")
    )
    value = {
        "schema": result.schema,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "proof_obligation_contract_id": result.proof_obligation_contract_id,
        "proof_obligation_contract_sha256": result.proof_obligation_contract_sha256,
        "domain_assumption_contract_id": result.domain_assumption_contract_id,
        "domain_assumption_contract_sha256": result.domain_assumption_contract_sha256,
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
        "proof_obligation_result": proof_result,
        "ambiguity_status": result.ambiguity_status,
        "selected_reading_id": result.selected_reading_id,
        "candidates": [_candidate_mapping(item) for item in result.candidates],
        "diagnostics": [
            {"code": item.code, "path": item.path, "message": item.message}
            for item in result.diagnostics
        ],
        "mathematical_authority": result.mathematical_authority,
    }
    if include_digest:
        value["result_sha256"] = result.result_sha256
    return value


def _result_bytes_unchecked(result: CanonicalNormalizationResult) -> bytes:
    return _canonical_bytes(_result_mapping(result))


def _new_result(**values: object) -> CanonicalNormalizationResult:
    return CanonicalNormalizationResult(_token=_RESULT_TOKEN, **values)  # type: ignore[arg-type]


class _CandidateNormalizer:
    def __init__(
        self,
        *,
        reading_id: str,
        projection: dict[str, Any],
        domain_candidate: dict[str, Any],
        proof_candidate: dict[str, Any],
        steps: list[int],
    ) -> None:
        self.reading_id = reading_id
        self.projection = projection
        self.domain_candidate = domain_candidate
        self.proof_candidate = proof_candidate
        self.graph = proof_candidate["graph"]
        self.steps = steps
        entities = projection.get("entities")
        if type(entities) is not dict:
            _fail("schema", "$.projection.entities", "entities must be an object")
        self.indexes: dict[str, dict[str, dict[str, Any]]] = {}
        self.owners: dict[str, str] = {}
        registry_limits = {
            "source_spans": MAX_SOURCE_SPANS,
            "domains": MAX_DOMAINS,
            "variables": MAX_VARIABLES,
            "expressions": MAX_EXPRESSIONS,
            "relations": MAX_RELATIONS,
            "statements": MAX_STATEMENTS,
            "definitions": MAX_DEFINITIONS,
            "assumptions": MAX_ASSUMPTIONS,
            "goals": MAX_GOALS,
        }
        for registry in (
            "domains", "variables", "expressions", "relations", "statements",
            "definitions", "assumptions", "goals", "source_spans",
        ):
            records = entities.get(registry, [])
            if type(records) is not list:
                _fail("schema", f"$.projection.entities.{registry}", "must be an array")
            maximum = registry_limits[registry]
            if len(records) > maximum:
                _fail(
                    "budget", f"$.projection.entities.{registry}",
                    f"{registry} budget exceeded",
                )
            index: dict[str, dict[str, Any]] = {}
            for record in records:
                if type(record) is not dict or type(record.get("id")) is not str:
                    _fail("schema", f"$.projection.entities.{registry}", "invalid record")
                entity_id = record["id"]
                if entity_id in self.owners:
                    _fail("reference", f"$.projection.entities.{registry}", "duplicate ID")
                self.owners[entity_id] = registry
                index[entity_id] = record
            self.indexes[registry] = index
        context = domain_candidate.get("context")
        if type(context) is not dict or type(context.get("facts")) is not list:
            _fail("schema", "$.domain_candidate.context", "invalid context")
        if len(context["facts"]) > MAX_FACTS:
            _fail("budget", "$.domain_candidate.context.facts", "fact budget exceeded")
        self.facts: dict[str, dict[str, Any]] = {}
        for fact in context["facts"]:
            if type(fact) is not dict or type(fact.get("fact_sha256")) is not str:
                _fail("schema", "$.domain_candidate.context.facts", "invalid fact")
            self.facts[fact["fact_sha256"]] = fact
        self.values: dict[tuple[str, str], dict[str, Any]] = {}
        self.value_contexts: dict[tuple[str, str], tuple[tuple[str, tuple[str, ...]], ...]] = {}
        self.memo: dict[
            tuple[str, str, tuple[tuple[str, tuple[str, ...]], ...]], dict[str, Any]
        ] = {}
        self.forms: dict[tuple[str, str], CanonicalNormalForm] = {}
        self.traces: list[CanonicalOccurrenceTrace] = []
        self.trace_by_owner: dict[str, list[str]] = {}
        self.variable_owners: dict[str, tuple[str, str, int]] = {}
        self._discover_variable_owners()
        if len(self.variable_owners) > MAX_BINDERS:
            _fail("budget", "$.projection.entities.variables", "binder budget exceeded")
        self._check_aggregate_budgets()

    def _check_aggregate_budgets(self) -> None:
        operands = 0
        dependencies = 0
        source_spans = 0
        for registry, records in self.indexes.items():
            for record in records.values():
                source_spans += len(record.get("span_ids", ()))
                if registry == "domains":
                    for field in (
                        "element_expr_ids", "factor_domain_ids",
                        "parameter_domain_ids", "parameter_expr_ids",
                    ):
                        operands += len(record.get(field, ()))
                elif registry == "expressions":
                    operands += len(record.get("argument_expr_ids", ()))
                    operands += len(record.get("element_expr_ids", ()))
                elif registry == "relations":
                    operands += len(record.get("operand_expr_ids", ()))
                elif registry == "statements":
                    operands += len(record.get("operand_statement_ids", ()))
                elif registry == "definitions":
                    operands += len(record.get("parameter_variable_ids", ()))
        for fact in self.facts.values():
            dependencies += len(fact["dependency_ids"])
            source_spans += len(fact["span_ids"])
        graph = self.graph
        for wrapper in graph["local_contexts"]:
            context = wrapper["context"]
            dependencies += len(context["dependency_ids"])
            source_spans += len(context["source_span_ids"])
            operands += sum(
                len(context[field])
                for field in (
                    "definition_ids", "assumption_fact_sha256s",
                    "bound_variable_ids", "local_hypothesis_statement_ids",
                    "witness_placeholder_ids",
                )
            )
        for obligation in graph["obligations"]:
            dependencies += len(obligation["dependency_ids"])
            source_spans += len(obligation["source_span_ids"])
            operands += sum(
                len(obligation[field])
                for field in (
                    "child_obligation_ids", "prerequisite_obligation_ids",
                    "witness_placeholder_ids", "admissible_strategies",
                )
            )
            dependencies += sum(
                len(item["prerequisite_obligation_ids"])
                for item in obligation["admissible_strategies"]
            )
        if operands > MAX_OPERANDS:
            _fail("budget", "$", "aggregate operand budget exceeded")
        if dependencies > MAX_DEPENDENCIES:
            _fail("budget", "$", "aggregate dependency budget exceeded")
        if source_spans > MAX_SOURCE_SPANS:
            _fail("budget", "$", "aggregate source-span budget exceeded")

    def _discover_variable_owners(self) -> None:
        for definition in self.indexes["definitions"].values():
            for position, variable_id in enumerate(definition["parameter_variable_ids"]):
                if variable_id in self.variable_owners:
                    _fail("scope", f"$.variables.{variable_id}", "multiple lexical owners")
                self.variable_owners[variable_id] = ("definition", definition["id"], position)
        for statement in self.indexes["statements"].values():
            if statement["kind"] != "quantified":
                continue
            for position, variable_id in enumerate(statement["variable_ids"]):
                if variable_id in self.variable_owners:
                    _fail("scope", f"$.variables.{variable_id}", "multiple lexical owners")
                self.variable_owners[variable_id] = ("statement", statement["id"], position)

    def _form(
        self,
        registry: str,
        source_ref: str,
        value: dict[str, Any],
        rule_ids: tuple[str, ...],
        *,
        supported: bool = True,
    ) -> CanonicalNormalForm:
        key = (registry, source_ref)
        digest = _sha(_canonical_bytes(value))
        existing = self.forms.get(key)
        if existing is not None:
            # Shared source nodes can occur below different lexical depths.  The
            # first source inventory form stays stable; each contextual use is
            # still represented in its enclosing statement and occurrence trace.
            return existing
        if len(self.forms) >= MAX_FORMS:
            _fail("budget", "$", "normal-form budget exceeded")
        form = CanonicalNormalForm(
            form_kind=_FORM_KINDS[registry],
            source_registry=registry,
            source_ref=source_ref,
            semantic_sha256=digest,
            rule_ids=rule_ids,
            value=_freeze(value),
            supported=supported,
        )
        self.forms[key] = form
        return form

    def _trace(
        self,
        *,
        kind: str,
        owner_kind: str,
        owner_ref: str,
        source_ref: str,
        source_index: int,
        canonical_index: int,
        semantic_sha256: str,
        rule_id: str,
    ) -> str:
        if len(self.traces) >= MAX_TRACES:
            _fail("budget", "$", "occurrence-trace budget exceeded")
        trace_id = f"trace_{len(self.traces):08d}"
        trace = CanonicalOccurrenceTrace(
            trace_id=trace_id,
            kind=kind,
            owner_kind=owner_kind,
            owner_ref=owner_ref,
            source_ref=source_ref,
            source_index=source_index,
            canonical_index=canonical_index,
            semantic_sha256=semantic_sha256,
            rule_id=rule_id,
        )
        self.traces.append(trace)
        self.trace_by_owner.setdefault(owner_ref, []).append(trace_id)
        return trace_id

    @staticmethod
    def _stack_key(stack: tuple[_Frame, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple((frame.kind, frame.variable_ids) for frame in stack)

    def _binding_token(
        self, variable_id: str, stack: tuple[_Frame, ...], *, standalone: bool = False,
    ) -> dict[str, Any]:
        variable = self.indexes["variables"].get(variable_id)
        if variable is None:
            _fail("reference", f"$.variables.{variable_id}", "missing variable")
        domain = self._domain_value(variable["domain_id"], stack)
        if not standalone:
            for depth, frame in enumerate(reversed(stack)):
                if variable_id in frame.variable_ids:
                    return {
                        "binding_kind": frame.kind,
                        "depth": depth,
                        "position": frame.variable_ids.index(variable_id),
                        "domain": domain,
                        "role": variable["role"],
                    }
        owner = self.variable_owners.get(variable_id)
        if owner is not None:
            return {
                "binding_kind": "parameter" if owner[0] == "definition" else "quantified",
                "position": owner[2],
                "domain": domain,
                "role": variable["role"],
            }
        return {
            "binding_kind": "free",
            "variable_id": variable_id,
            "name": variable["name"],
            "domain": domain,
            "role": variable["role"],
        }

    def _record_variable(
        self, variable_id: str, stack: tuple[_Frame, ...], *, standalone: bool = False,
    ) -> dict[str, Any]:
        token = self._binding_token(variable_id, stack, standalone=standalone)
        inventory_token = self._binding_token(variable_id, (), standalone=True)
        rule = (
            (_PARAMETER_RULE,)
            if inventory_token["binding_kind"] == "parameter"
            else (_BOUND_RULE,)
            if inventory_token["binding_kind"] == "quantified"
            else (_PRESERVE_RULE,)
        )
        self._form("variables", variable_id, inventory_token, rule)
        return token

    def _domain_value(
        self, domain_id: str, stack: tuple[_Frame, ...],
    ) -> dict[str, Any]:
        key = ("domains", domain_id, self._stack_key(stack))
        if key in self.memo:
            return self.memo[key]
        _step(self.steps, f"$.domains.{domain_id}")
        record = self.indexes["domains"].get(domain_id)
        if record is None:
            _fail("reference", f"$.domains.{domain_id}", "missing domain")
        kind = record["kind"]
        value: dict[str, Any]
        if kind == "builtin":
            value = {"kind": kind, "name": record["name"]}
        elif kind == "finite":
            value = {
                "kind": kind,
                "element_domain": self._domain_value(record["element_domain_id"], stack),
                "elements": [
                    self._expression_value(item, stack) for item in record["element_expr_ids"]
                ],
                "cardinality": record["cardinality"],
            }
        elif kind == "interval":
            value = {
                "kind": kind,
                "base": record["base"],
                "lower": None
                if record["lower_expr_id"] is None
                else self._expression_value(record["lower_expr_id"], stack),
                "lower_closed": record["lower_closed"],
                "upper": None
                if record["upper_expr_id"] is None
                else self._expression_value(record["upper_expr_id"], stack),
                "upper_closed": record["upper_closed"],
            }
        elif kind == "modular":
            value = {
                "kind": kind,
                "modulus": self._expression_value(record["modulus_expr_id"], stack),
            }
        elif kind == "collection":
            value = {
                "kind": kind,
                "collection": record["collection"],
                "element_domain": self._domain_value(record["element_domain_id"], stack),
                "finiteness": record["finiteness"],
            }
        elif kind == "product":
            value = {
                "kind": kind,
                "factors": [
                    self._domain_value(item, stack) for item in record["factor_domain_ids"]
                ],
            }
        elif kind == "function":
            value = {
                "kind": kind,
                "parameters": [
                    self._domain_value(item, stack)
                    for item in record["parameter_domain_ids"]
                ],
                "result": self._domain_value(record["result_domain_id"], stack),
                "total": record["total"],
            }
        elif kind == "structure":
            value = {
                "kind": kind,
                "theory_id": record["theory_id"],
                "parameter_domains": [
                    self._domain_value(item, stack)
                    for item in record["parameter_domain_ids"]
                ],
                "parameter_expressions": [
                    self._expression_value(item, stack)
                    for item in record["parameter_expr_ids"]
                ],
            }
        else:
            value = {"kind": "opaque", "source": record}
        self.memo[key] = value
        self._form(
            "domains", domain_id, value,
            (_OPAQUE_RULE,) if kind not in {
                "builtin", "finite", "interval", "modular", "collection",
                "product", "function", "structure",
            } else (_PRESERVE_RULE,),
            supported=kind != "opaque",
        )
        return value

    def _ordered_children(
        self,
        *,
        owner_kind: str,
        owner_ref: str,
        source_refs: list[str],
        values: list[dict[str, Any]],
        rule_id: str,
        commutative: bool,
    ) -> list[dict[str, Any]]:
        if len(source_refs) != len(values):
            _fail("trace", f"$.{owner_kind}.{owner_ref}", "occurrence arity drift")
        indexed = list(enumerate(zip(source_refs, values, strict=True)))
        ordered = (
            sorted(indexed, key=lambda row: (_canonical_bytes(row[1][1]), row[0]))
            if commutative
            else indexed
        )
        canonical_by_source = {source_index: canonical for canonical, (source_index, _row)
                               in enumerate(ordered)}
        trace_kind = "commutative_operand" if commutative else "preserved_order"
        for source_index, (source_ref, value) in indexed:
            self._trace(
                kind=trace_kind,
                owner_kind=owner_kind,
                owner_ref=owner_ref,
                source_ref=source_ref,
                source_index=source_index,
                canonical_index=canonical_by_source[source_index],
                semantic_sha256=_sha(_canonical_bytes(value)),
                rule_id=rule_id,
            )
        return [row[1][1] for row in ordered]

    def _expression_value(
        self, expression_id: str, stack: tuple[_Frame, ...],
    ) -> dict[str, Any]:
        key = ("expressions", expression_id, self._stack_key(stack))
        if key in self.memo:
            return self.memo[key]
        _step(self.steps, f"$.expressions.{expression_id}")
        record = self.indexes["expressions"].get(expression_id)
        if record is None:
            _fail("reference", f"$.expressions.{expression_id}", "missing expression")
        kind = record["kind"]
        domain = self._domain_value(record["domain_id"], stack)
        if kind == "literal":
            value = {
                "kind": kind,
                "domain": domain,
                "literal_type": record["literal_type"],
                "value": record["value"],
            }
        elif kind == "variable":
            value = {
                "kind": kind,
                "domain": domain,
                "variable": self._record_variable(record["variable_id"], stack),
            }
        elif kind == "apply":
            refs = list(record["argument_expr_ids"])
            children = [self._expression_value(item, stack) for item in refs]
            value = {
                "kind": kind,
                "domain": domain,
                "operator": record["operator"],
                "arguments": self._ordered_children(
                    # The frozen trace schema has no expression owner kind.
                    # Expression-owned order is therefore grouped under the
                    # closest semantic relation class while owner_ref keeps
                    # the exact expression record that owns the occurrence.
                    owner_kind="relation",
                    owner_ref=expression_id,
                    source_refs=refs,
                    values=children,
                    rule_id=_PRESERVE_RULE,
                    commutative=False,
                ),
                "attributes": record["attributes"],
            }
        elif kind in {"tuple", "collection"}:
            refs = list(record["element_expr_ids"])
            children = [self._expression_value(item, stack) for item in refs]
            value = {
                "kind": kind,
                "domain": domain,
                "elements": self._ordered_children(
                    owner_kind="relation",
                    owner_ref=expression_id,
                    source_refs=refs,
                    values=children,
                    rule_id=_PRESERVE_RULE,
                    commutative=False,
                ),
            }
        elif kind == "conditional":
            refs = [
                record["condition_statement_id"], record["then_expr_id"],
                record["else_expr_id"],
            ]
            children = [
                self._statement_value(refs[0], stack),
                self._expression_value(refs[1], stack),
                self._expression_value(refs[2], stack),
            ]
            value = {
                "kind": kind,
                "domain": domain,
                "condition": children[0],
                "then": children[1],
                "else": children[2],
            }
            self._ordered_children(
                owner_kind="relation",
                owner_ref=expression_id,
                source_refs=refs,
                values=children,
                rule_id=_PRESERVE_RULE,
                commutative=False,
            )
        else:
            value = {"kind": "opaque", "domain": domain, "source": record}
        self.memo[key] = value
        self._form(
            "expressions", expression_id, value,
            (_OPAQUE_RULE,) if kind not in {
                "literal", "variable", "apply", "tuple", "collection", "conditional",
            } else (_PRESERVE_RULE,),
            supported=kind != "opaque",
        )
        return value

    def _relation_value(
        self, relation_id: str, stack: tuple[_Frame, ...],
    ) -> dict[str, Any]:
        key = ("relations", relation_id, self._stack_key(stack))
        if key in self.memo:
            return self.memo[key]
        _step(self.steps, f"$.relations.{relation_id}")
        record = self.indexes["relations"].get(relation_id)
        if record is None:
            _fail("reference", f"$.relations.{relation_id}", "missing relation")
        refs = list(record["operand_expr_ids"])
        children = [self._expression_value(item, stack) for item in refs]
        rule = _COMMUTATIVE_RELATIONS.get(record["kind"])
        commutative = rule is not None and len(refs) == 2
        rule_id = rule if commutative else _PRESERVE_RULE
        operands = self._ordered_children(
            owner_kind="relation",
            owner_ref=relation_id,
            source_refs=refs,
            values=children,
            rule_id=rule_id,
            commutative=commutative,
        )
        value = {
            "kind": record["kind"],
            "operands": operands,
        }
        if record["kind"] == "predicate":
            value["predicate"] = record["predicate"]
        self.memo[key] = value
        self._form("relations", relation_id, value, (rule_id,))
        return value

    def _statement_value(
        self, statement_id: str, stack: tuple[_Frame, ...],
    ) -> dict[str, Any]:
        key = ("statements", statement_id, self._stack_key(stack))
        if key in self.memo:
            return self.memo[key]
        _step(self.steps, f"$.statements.{statement_id}")
        record = self.indexes["statements"].get(statement_id)
        if record is None:
            _fail("reference", f"$.statements.{statement_id}", "missing statement")
        kind = record["kind"]
        rule_id = _PRESERVE_RULE
        if kind == "truth":
            value = {"kind": kind, "value": record["value"]}
        elif kind == "relation":
            value = {
                "kind": kind,
                "relation": self._relation_value(record["relation_id"], stack),
            }
        elif kind == "logical":
            refs = list(record["operand_statement_ids"])
            children = [self._statement_value(item, stack) for item in refs]
            selected = _COMMUTATIVE_STATEMENTS.get(record["operator"])
            commutative = selected is not None and (
                record["operator"] in {"and", "or"} or len(refs) == 2
            )
            rule_id = selected if commutative else _PRESERVE_RULE
            value = {
                "kind": kind,
                "operator": record["operator"],
                "operands": self._ordered_children(
                    owner_kind="statement",
                    owner_ref=statement_id,
                    source_refs=refs,
                    values=children,
                    rule_id=rule_id,
                    commutative=commutative,
                ),
            }
        elif kind == "quantified":
            variable_ids = tuple(record["variable_ids"])
            frame = _Frame("quantified", variable_ids)
            next_stack = (*stack, frame)
            variables = []
            for position, variable_id in enumerate(variable_ids):
                token = self._record_variable(variable_id, next_stack)
                variables.append(token)
                self._trace(
                    kind="quantified_binder",
                    owner_kind="statement",
                    owner_ref=statement_id,
                    source_ref=variable_id,
                    source_index=position,
                    canonical_index=position,
                    semantic_sha256=_sha(_canonical_bytes(token)),
                    rule_id=_BOUND_RULE,
                )
            value = {
                "kind": kind,
                "quantifier": record["quantifier"],
                "variables": variables,
                "body": self._statement_value(record["body_statement_id"], next_stack),
            }
            rule_id = _BOUND_RULE
        else:
            value = {"kind": "opaque", "source": record}
            rule_id = _OPAQUE_RULE
        self.memo[key] = value
        self._form(
            "statements", statement_id, value, (rule_id,), supported=kind != "opaque"
        )
        return value

    def _definition_value(self, definition_id: str) -> dict[str, Any]:
        key = ("definitions", definition_id, ())
        if key in self.memo:
            return self.memo[key]
        _step(self.steps, f"$.definitions.{definition_id}")
        record = self.indexes["definitions"].get(definition_id)
        if record is None:
            _fail("reference", f"$.definitions.{definition_id}", "missing definition")
        variable_ids = tuple(record["parameter_variable_ids"])
        frame = _Frame("parameter", variable_ids)
        stack = (frame,)
        parameters = []
        for position, variable_id in enumerate(variable_ids):
            token = self._record_variable(variable_id, stack)
            parameters.append(token)
            self._trace(
                kind="definition_parameter",
                owner_kind="definition",
                owner_ref=definition_id,
                source_ref=variable_id,
                source_index=position,
                canonical_index=position,
                semantic_sha256=_sha(_canonical_bytes(token)),
                rule_id=_PARAMETER_RULE,
            )
        body = record["body"]
        body_value = (
            self._expression_value(body["expression_id"], stack)
            if body["kind"] == "expression"
            else self._statement_value(body["statement_id"], stack)
        )
        value = {
            "kind": "definition",
            "name": record["name"],
            "parameters": parameters,
            "result_domain": None
            if record["result_domain_id"] is None
            else self._domain_value(record["result_domain_id"], stack),
            "body_kind": body["kind"],
            "body": body_value,
            "recursive": record["recursive"],
        }
        self.memo[key] = value
        self._form(
            "definitions", definition_id, value,
            (_PARAMETER_RULE,) if variable_ids else (_PRESERVE_RULE,),
        )
        return value

    def _entity_value(
        self, entity_id: str, stack: tuple[_Frame, ...] = (),
    ) -> dict[str, Any]:
        registry = self.owners.get(entity_id)
        if registry == "domains":
            return self._domain_value(entity_id, stack)
        if registry == "variables":
            return self._record_variable(entity_id, stack, standalone=not stack)
        if registry == "expressions":
            return self._expression_value(entity_id, stack)
        if registry == "relations":
            return self._relation_value(entity_id, stack)
        if registry == "statements":
            return self._statement_value(entity_id, stack)
        if registry == "definitions":
            return self._definition_value(entity_id)
        if registry == "assumptions":
            assumption = self.indexes["assumptions"][entity_id]
            return {
                "kind": "assumption",
                "role": assumption["role"],
                "statement": self._statement_value(assumption["statement_id"], stack),
            }
        if registry == "goals":
            goal = self.indexes["goals"][entity_id]
            return {
                "kind": "goal",
                "mode": goal["mode"],
                "statement": self._statement_value(goal["statement_id"], stack),
            }
        if registry == "source_spans":
            return {"kind": "source_span", "source_ref": entity_id}
        _fail("reference", "$.dependencies", f"unknown entity {entity_id!r}")

    def _dependency_hash(
        self, entity_id: str, stack: tuple[_Frame, ...] = (),
    ) -> str:
        registry = self.owners.get(entity_id)
        if registry in _FORM_KINDS:
            existing = self.forms.get((registry, entity_id))
            if existing is not None:
                return existing.semantic_sha256
        return _sha(_canonical_bytes(self._entity_value(entity_id, stack)))

    def _fact_value(self, fact_sha256: str) -> dict[str, Any]:
        key = ("assumption_facts", fact_sha256)
        existing = self.forms.get(key)
        if existing is not None:
            value = _thaw(existing.value)
            if type(value) is not dict:
                _fail("schema", f"$.facts.{fact_sha256}", "fact form is not an object")
            return value
        _step(self.steps, f"$.facts.{fact_sha256}")
        fact = self.facts.get(fact_sha256)
        if fact is None:
            _fail("reference", f"$.facts.{fact_sha256}", "missing fact")
        origin_id = fact["origin_id"]
        statement_id = fact["statement_id"]
        relation_id = fact["relation_id"]
        dependencies = [self._dependency_hash(item) for item in fact["dependency_ids"]]
        value = {
            "kind": fact["kind"],
            "assumption_role": fact["assumption_role"],
            "origin_registry": fact["origin_registry"],
            "origin": self._entity_value(origin_id),
            "statement": None
            if statement_id is None
            else self._statement_value(statement_id, ()),
            "relation": None
            if relation_id is None
            else self._relation_value(relation_id, ()),
            "subjects": [self._entity_value(item) for item in fact["subject_ids"]],
            "dependencies": sorted(dependencies),
            "rule_id": fact["rule_id"],
            "supported": fact["supported"],
        }
        self._form(
            "assumption_facts",
            fact_sha256,
            value,
            (_PRESERVE_RULE,) if fact["supported"] else (_OPAQUE_RULE,),
            supported=fact["supported"],
        )
        return value

    def _ensure_source_forms(self) -> None:
        for definition_id in self.projection["definition_ids"]:
            self._definition_value(definition_id)
        for assumption_id in self.projection["assumption_ids"]:
            assumption = self.indexes["assumptions"][assumption_id]
            self._statement_value(assumption["statement_id"], ())
        for goal_id in self.projection["goal_ids"]:
            goal = self.indexes["goals"][goal_id]
            self._statement_value(goal["statement_id"], ())
        for fact_sha256 in self.facts:
            self._fact_value(fact_sha256)
        for registry in (
            "domains", "variables", "expressions", "relations", "statements",
            "definitions",
        ):
            for source_ref in sorted(self.indexes[registry]):
                # The preceding reading-root traversal establishes the lexical
                # context for every reachable source record.  Only genuinely
                # unvisited inventory records need a standalone pass; replaying
                # an already visited relation or statement outside that scope
                # would fabricate a second occurrence trace.
                if (registry, source_ref) not in self.forms:
                    self._entity_value(source_ref)

    @staticmethod
    def _occurrence(
        source_ref: str,
        semantic_sha256: str,
        role: str,
        source_index: int,
        canonical_index: int,
    ) -> CanonicalOccurrence:
        return CanonicalOccurrence(
            source_ref=source_ref,
            semantic_sha256=semantic_sha256,
            role=role,
            source_index=source_index,
            canonical_index=canonical_index,
        )

    def _preserved_occurrences(
        self,
        *,
        owner_ref: str,
        owner_kind: str,
        source_refs: tuple[str, ...],
        roles: tuple[str, ...],
        values: tuple[dict[str, Any], ...],
    ) -> tuple[CanonicalOccurrence, ...]:
        result = []
        for index, (source_ref, role, value) in enumerate(
            zip(source_refs, roles, values, strict=True)
        ):
            digest = _sha(_canonical_bytes(value))
            result.append(self._occurrence(source_ref, digest, role, index, index))
            self._trace(
                kind="preserved_order",
                owner_kind=owner_kind,
                owner_ref=owner_ref,
                source_ref=source_ref,
                source_index=index,
                canonical_index=index,
                semantic_sha256=digest,
                rule_id=_PRESERVE_RULE,
            )
        return tuple(result)

    def _context(self, digest: str, raw: dict[str, Any]) -> CanonicalContext:
        if raw["reading_id"] != self.reading_id:
            _fail("context", f"$.contexts.{digest}", "reading mismatch")
        trace_start = len(self.traces)
        definition_refs = tuple(raw["definition_ids"])
        definition_values = tuple(self._definition_value(item) for item in definition_refs)
        definitions = self._preserved_occurrences(
            owner_ref=f"{digest}:definitions",
            owner_kind="local_context",
            source_refs=definition_refs,
            roles=tuple("definition" for _item in definition_refs),
            values=definition_values,
        )

        fact_refs = tuple(raw["assumption_fact_sha256s"])
        fact_values = [self._fact_value(item) for item in fact_refs]
        fact_rows = []
        for source_index, (source_ref, value) in enumerate(
            zip(fact_refs, fact_values, strict=True)
        ):
            fact = self.facts[source_ref]
            role = fact["assumption_role"]
            if role is None:
                role = "variable_fact" if fact["origin_registry"] == "variables" else "domain_fact"
            fact_rows.append((source_index, source_ref, role, value))
        ordered_facts = sorted(
            fact_rows,
            key=lambda row: (
                _ROLE_ORDER.get(row[2], 99), _canonical_bytes(row[3]),
                self.facts[row[1]]["origin_registry"], row[0],
            ),
        )
        fact_canonical = {row[0]: index for index, row in enumerate(ordered_facts)}
        assumptions = []
        for source_index, source_ref, role, value in fact_rows:
            canonical_index = fact_canonical[source_index]
            semantic_sha256 = _sha(_canonical_bytes(value))
            assumptions.append(
                self._occurrence(
                    source_ref, semantic_sha256, role, source_index, canonical_index
                )
            )
            self._trace(
                kind="assumption_order",
                owner_kind="local_context",
                owner_ref=digest,
                source_ref=source_ref,
                source_index=source_index,
                canonical_index=canonical_index,
                semantic_sha256=semantic_sha256,
                rule_id=_ASSUMPTION_RULE,
            )
        assumptions.sort(key=lambda item: item.canonical_index)

        bound_refs = tuple(raw["bound_variable_ids"])
        bound_values = tuple(
            self._binding_token(item, (), standalone=True) for item in bound_refs
        )
        bounds = self._preserved_occurrences(
            owner_ref=f"{digest}:bound_variables",
            owner_kind="local_context",
            source_refs=bound_refs,
            roles=tuple("bound" for _item in bound_refs),
            values=bound_values,
        )

        hypothesis_refs = tuple(raw["local_hypothesis_statement_ids"])
        context_stack = (_Frame("quantified", bound_refs),) if bound_refs else ()
        hypothesis_values = [
            self._statement_value(item, context_stack) for item in hypothesis_refs
        ]
        hypothesis_rows = list(enumerate(zip(hypothesis_refs, hypothesis_values, strict=True)))
        ordered_hypotheses = sorted(
            hypothesis_rows, key=lambda row: (_canonical_bytes(row[1][1]), row[0])
        )
        hypothesis_canonical = {
            source_index: index
            for index, (source_index, _row) in enumerate(ordered_hypotheses)
        }
        hypotheses = []
        for source_index, (source_ref, value) in hypothesis_rows:
            canonical_index = hypothesis_canonical[source_index]
            semantic_sha256 = _sha(_canonical_bytes(value))
            hypotheses.append(
                self._occurrence(
                    source_ref, semantic_sha256, "hypothesis", source_index,
                    canonical_index,
                )
            )
            self._trace(
                kind="hypothesis_order",
                owner_kind="local_context",
                owner_ref=digest,
                source_ref=source_ref,
                source_index=source_index,
                canonical_index=canonical_index,
                semantic_sha256=semantic_sha256,
                rule_id=_HYPOTHESIS_RULE,
            )
        hypotheses.sort(key=lambda item: item.canonical_index)

        witness_refs = tuple(raw["witness_placeholder_ids"])
        witnesses = []
        for index, source_ref in enumerate(witness_refs):
            value = {"kind": "symbolic_witness", "slot": index}
            semantic_sha256 = _sha(_canonical_bytes(value))
            witnesses.append(
                self._occurrence(source_ref, semantic_sha256, "witness", index, index)
            )
            self._trace(
                kind="witness_slot",
                owner_kind="local_context",
                owner_ref=digest,
                source_ref=source_ref,
                source_index=index,
                canonical_index=index,
                semantic_sha256=semantic_sha256,
                rule_id=_WITNESS_RULE,
            )

        dependency_hashes = tuple(
            sorted(
                self._dependency_hash(item, context_stack)
                for item in raw["dependency_ids"]
            )
        )
        semantic_value = {
            "reading_id": self.reading_id,
            "definitions": [item.semantic_sha256 for item in definitions],
            "assumptions": [
                {"role": item.role, "semantic_sha256": item.semantic_sha256}
                for item in assumptions
            ],
            "bound_variables": [item.semantic_sha256 for item in bounds],
            "hypotheses": [item.semantic_sha256 for item in hypotheses],
            "witnesses": [item.semantic_sha256 for item in witnesses],
            "dependencies": list(dependency_hashes),
        }
        semantic_sha256 = _sha(_canonical_bytes(semantic_value))
        trace_ids = tuple(item.trace_id for item in self.traces[trace_start:])
        context = CanonicalContext(
            reading_id=self.reading_id,
            source_local_context_sha256=digest,
            semantic_sha256=semantic_sha256,
            semantic_value=_freeze(semantic_value),
            definition_occurrences=definitions,
            assumption_occurrences=tuple(assumptions),
            bound_variable_occurrences=bounds,
            hypothesis_occurrences=tuple(hypotheses),
            witness_occurrences=tuple(witnesses),
            dependency_semantic_sha256s=dependency_hashes,
            source_span_ids=tuple(raw["source_span_ids"]),
            trace_ids=trace_ids,
        )
        self._form(
            "local_contexts", digest, semantic_value, (_ASSUMPTION_RULE, _HYPOTHESIS_RULE)
        )
        return context

    @staticmethod
    def _obligation_ordinal(obligation_id: str | None) -> int | None:
        if obligation_id is None:
            return None
        match = _OBLIGATION_RE.fullmatch(obligation_id)
        if match is None:
            _fail("graph", "$.obligations", f"invalid obligation ID {obligation_id!r}")
        return int(match.group(1))

    def _obligation(
        self,
        raw: dict[str, Any],
        contexts: dict[str, CanonicalContext],
        goal_positions: dict[str, int],
        obligation_ids: set[str],
    ) -> CanonicalObligation:
        source_id = raw["obligation_id"]
        ordinal = self._obligation_ordinal(source_id)
        if ordinal is None or ordinal != raw["ordinal"]:
            _fail("graph", f"$.obligations.{source_id}", "ordinal mismatch")
        context = contexts.get(raw["local_context_sha256"])
        if context is None:
            _fail("context", f"$.obligations.{source_id}", "missing local context")
        bound_refs = tuple(
            item.source_ref for item in context.bound_variable_occurrences
        )
        context_stack = (_Frame("quantified", bound_refs),) if bound_refs else ()
        statement_id = raw["statement_id"]
        statement_value = (
            {"kind": "absent"}
            if statement_id is None
            else self._statement_value(statement_id, context_stack)
        )
        statement_sha256 = _sha(_canonical_bytes(statement_value))
        child_ordinals = tuple(
            self._required_ordinal(item, obligation_ids) for item in raw["child_obligation_ids"]
        )
        prerequisite_ordinals = tuple(
            self._required_ordinal(item, obligation_ids)
            for item in raw["prerequisite_obligation_ids"]
        )
        alternative = raw["alternative_group_id"]
        alternative_ordinal = None
        if alternative is not None:
            prefix = "alternative_"
            if not alternative.startswith(prefix):
                _fail("graph", f"$.obligations.{source_id}", "invalid alternative group")
            alternative_source = alternative[len(prefix):]
            alternative_ordinal = self._required_ordinal(alternative_source, obligation_ids)
        witness_index = {
            item.source_ref: item.canonical_index for item in context.witness_occurrences
        }
        witness_slots = []
        for witness in raw["witness_placeholder_ids"]:
            if witness not in witness_index:
                # Construction obligations introduce placeholders before their
                # verification context contains them.  Their declared order is
                # still a stable symbolic slot sequence local to the obligation.
                witness_index[witness] = len(witness_index)
            witness_slots.append(witness_index[witness])
        strategy_values = []
        strategy_ids = []
        strategy_hashes = []
        for strategy in raw["admissible_strategies"]:
            normalized = {
                "strategy_id": strategy["strategy_id"],
                "match_rule_id": strategy["match_rule_id"],
                "reason_code": strategy["reason_code"],
                "matched_value": strategy["matched_value"],
                "prerequisite_ordinals": [
                    self._required_ordinal(item, obligation_ids)
                    for item in strategy["prerequisite_obligation_ids"]
                ],
                "guarantees_success": strategy["guarantees_success"],
                "mathematical_authority": strategy["mathematical_authority"],
            }
            strategy_values.append(normalized)
            strategy_ids.append(strategy["strategy_id"])
            strategy_hashes.append(_sha(_canonical_bytes(normalized)))
        dependency_hashes = tuple(
            sorted(
                self._dependency_hash(item, context_stack)
                for item in raw["dependency_ids"]
            )
        )
        trace_ids: list[str] = list(context.trace_ids)
        for owner_ref in (statement_id, raw["relation_id"], *raw["dependency_ids"]):
            if owner_ref is not None:
                trace_ids.extend(self.trace_by_owner.get(owner_ref, ()))
        trace_ids = list(dict.fromkeys(trace_ids))
        root_position = goal_positions.get(raw["root_goal_id"])
        if root_position is None:
            _fail("graph", f"$.obligations.{source_id}", "unknown root goal")
        semantic_value = {
            "reading_id": self.reading_id,
            "ordinal": ordinal,
            "root_goal_position": root_position,
            "parent_ordinal": self._obligation_ordinal(raw["parent_obligation_id"]),
            "rule_id": raw["rule_id"],
            "kind": raw["kind"],
            "goal_mode": raw["goal_mode"],
            "status": raw["status"],
            "statement": statement_value,
            "local_context_semantic_sha256": context.semantic_sha256,
            "child_ordinals": list(child_ordinals),
            "prerequisite_ordinals": list(prerequisite_ordinals),
            "alternative_group_ordinal": alternative_ordinal,
            "alternative_index": raw["alternative_index"],
            "witness_slots": witness_slots,
            "strategies": strategy_values,
            "dependencies": list(dependency_hashes),
            "supported": raw["supported"],
        }
        semantic_sha256 = _sha(_canonical_bytes(semantic_value))
        if not raw["supported"]:
            trace_ids.append(
                self._trace(
                    kind="opaque",
                    owner_kind="obligation",
                    owner_ref=source_id,
                    source_ref=source_id,
                    source_index=0,
                    canonical_index=0,
                    semantic_sha256=semantic_sha256,
                    rule_id=_OPAQUE_RULE,
                )
            )
        obligation = CanonicalObligation(
            reading_id=self.reading_id,
            source_obligation_id=source_id,
            source_obligation_sha256=raw["obligation_sha256"],
            ordinal=ordinal,
            root_goal_id=raw["root_goal_id"],
            parent_ordinal=self._obligation_ordinal(raw["parent_obligation_id"]),
            rule_id=raw["rule_id"],
            kind=raw["kind"],
            goal_mode=raw["goal_mode"],
            status=raw["status"],
            source_statement_id=statement_id,
            source_relation_id=raw["relation_id"],
            statement_semantic_sha256=statement_sha256,
            statement_normal_form=_freeze(statement_value),
            local_context_semantic_sha256=context.semantic_sha256,
            child_ordinals=child_ordinals,
            prerequisite_ordinals=prerequisite_ordinals,
            alternative_group_ordinal=alternative_ordinal,
            alternative_index=raw["alternative_index"],
            witness_slots=tuple(witness_slots),
            strategy_ids=tuple(strategy_ids),
            strategy_record_sha256s=tuple(strategy_hashes),
            dependency_semantic_sha256s=dependency_hashes,
            source_span_ids=tuple(raw["source_span_ids"]),
            trace_ids=tuple(dict.fromkeys(trace_ids)),
            semantic_sha256=semantic_sha256,
            semantic_value=_freeze(semantic_value),
            supported=raw["supported"],
        )
        self._form(
            "obligations", source_id, semantic_value,
            (_PRESERVE_RULE,) if raw["supported"] else (_OPAQUE_RULE,),
            supported=raw["supported"],
        )
        return obligation

    def _required_ordinal(self, source_id: str, obligation_ids: set[str]) -> int:
        if source_id not in obligation_ids:
            _fail("graph", "$.obligations", f"dangling obligation {source_id!r}")
        ordinal = self._obligation_ordinal(source_id)
        if ordinal is None:
            _fail("graph", "$.obligations", "null obligation reference")
        return ordinal

    def build(self) -> CanonicalNormalizationCandidate:
        self._ensure_source_forms()
        raw_contexts = self.graph["local_contexts"]
        if len(raw_contexts) > MAX_CONTEXTS:
            _fail("budget", "$.graph.local_contexts", "context budget exceeded")
        contexts: list[CanonicalContext] = []
        context_index: dict[str, CanonicalContext] = {}
        for item in raw_contexts:
            digest = item["local_context_sha256"]
            context = self._context(digest, item["context"])
            contexts.append(context)
            context_index[digest] = context

        raw_obligations = self.graph["obligations"]
        if len(raw_obligations) > MAX_OBLIGATIONS:
            _fail("budget", "$.graph.obligations", "obligation budget exceeded")
        obligation_ids = {item["obligation_id"] for item in raw_obligations}
        goal_positions = {
            goal_id: index for index, goal_id in enumerate(self.graph["goal_ids"])
        }
        obligations = tuple(
            self._obligation(item, context_index, goal_positions, obligation_ids)
            for item in raw_obligations
        )
        if tuple(item.ordinal for item in obligations) != tuple(range(len(obligations))):
            _fail("graph", "$.graph.obligations", "obligation preorder is not contiguous")
        root_ordinals = tuple(
            self._required_ordinal(item, obligation_ids)
            for item in self.graph["root_obligation_ids"]
        )
        forms = tuple(
            sorted(
                self.forms.values(),
                key=lambda item: (_REGISTRY_ORDER[item.source_registry], item.source_ref),
            )
        )
        unsupported = tuple(
            sorted({
                item.semantic_sha256 for item in forms if not item.supported
            } | {
                item.semantic_sha256 for item in obligations if not item.supported
            })
        )
        # Source obligation ordinals and alternative indexes are retained on
        # every public CanonicalObligation.  They must not, however, leak the
        # original operand order into the separate comparison identity for an
        # explicitly commutative logical owner.  Establish a semantic ordinal
        # namespace from complete non-positional obligation content, then
        # rewrite graph references only inside the graph-hash preimage.
        source_values = [_thaw(item.semantic_value) for item in obligations]
        base_values: list[dict[str, Any]] = []
        positional_fields = {
            "ordinal", "root_goal_position", "parent_ordinal", "child_ordinals",
            "prerequisite_ordinals", "alternative_group_ordinal",
            "alternative_index",
        }
        for value in source_values:
            if type(value) is not dict:
                _fail("graph", "$.obligations", "semantic obligation is not an object")
            base = {
                key: item for key, item in value.items() if key not in positional_fields
            }
            base["strategies"] = [
                {
                    key: item
                    for key, item in strategy.items()
                    if key != "prerequisite_ordinals"
                }
                for strategy in value["strategies"]
            ]
            base_values.append(base)
        semantic_order = sorted(
            range(len(obligations)),
            key=lambda ordinal: (_canonical_bytes(base_values[ordinal]), ordinal),
        )
        semantic_ordinal = {
            source_ordinal: canonical
            for canonical, source_ordinal in enumerate(semantic_order)
        }
        obligation_graph_values: list[dict[str, Any]] = []
        for source_ordinal in semantic_order:
            obligation = obligations[source_ordinal]
            source_value = source_values[source_ordinal]
            graph_obligation = dict(base_values[source_ordinal])
            children = [semantic_ordinal[item] for item in obligation.child_ordinals]
            if obligation.rule_id in _COMMUTATIVE_OBLIGATION_RULES:
                children.sort()
            prerequisites = [
                semantic_ordinal[item] for item in obligation.prerequisite_ordinals
            ]
            strategies = []
            for strategy in source_value["strategies"]:
                normalized_strategy = dict(strategy)
                normalized_strategy["prerequisite_ordinals"] = [
                    semantic_ordinal[item]
                    for item in strategy["prerequisite_ordinals"]
                ]
                strategies.append(normalized_strategy)
            alternative_index = obligation.alternative_index
            if obligation.alternative_group_ordinal is not None:
                alternative_owner = obligations[obligation.alternative_group_ordinal]
                if alternative_owner.rule_id in _COMMUTATIVE_OBLIGATION_RULES:
                    canonical_alternatives = sorted(
                        semantic_ordinal[item]
                        for item in alternative_owner.child_ordinals
                    )
                    alternative_index = canonical_alternatives.index(
                        semantic_ordinal[source_ordinal]
                    )
            graph_obligation.update({
                "semantic_ordinal": semantic_ordinal[source_ordinal],
                "root_goal_position": source_value["root_goal_position"],
                "parent_semantic_ordinal": None
                if obligation.parent_ordinal is None
                else semantic_ordinal[obligation.parent_ordinal],
                "child_semantic_ordinals": children,
                "prerequisite_semantic_ordinals": prerequisites,
                "alternative_group_semantic_ordinal": None
                if obligation.alternative_group_ordinal is None
                else semantic_ordinal[obligation.alternative_group_ordinal],
                "alternative_index": alternative_index,
                "strategies": strategies,
            })
            obligation_graph_values.append(graph_obligation)
        graph_value = {
            "contract_sha256": CONTRACT_SHA256,
            "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
            "reading_id": self.reading_id,
            "goal_count": len(self.graph["goal_ids"]),
            "root_semantic_ordinals": [
                semantic_ordinal[item] for item in root_ordinals
            ],
            "forms": sorted(
                [
                    {
                        "form_kind": item.form_kind,
                        "semantic_sha256": item.semantic_sha256,
                        "value": _thaw(item.value),
                        "supported": item.supported,
                    }
                    for item in forms
                    if item.source_registry not in {"local_contexts", "obligations"}
                ],
                key=_canonical_bytes,
            ),
            "contexts": sorted(item.semantic_sha256 for item in contexts),
            "obligations": obligation_graph_values,
            # Source indexes and trace emission order belong to the reversible
            # provenance surface, not to the invariant semantic identity.  A
            # canonical-indexed multiset still binds every rule application,
            # duplicate, and ordered position while allowing an authorized
            # source permutation to keep the same graph identity.
            "traces": sorted(
                (
                    {
                        "kind": item.kind,
                        "canonical_index": item.canonical_index,
                        "semantic_sha256": item.semantic_sha256,
                        "rule_id": item.rule_id,
                    }
                    for item in self.traces
                ),
                key=_canonical_bytes,
            ),
            "unsupported": list(unsupported),
        }
        semantic_graph_sha256 = _sha(_canonical_bytes(graph_value))
        return CanonicalNormalizationCandidate(
            reading_id=self.reading_id,
            source_graph_sha256=self.proof_candidate["graph_sha256"],
            semantic_graph_sha256=semantic_graph_sha256,
            goal_ids=tuple(self.graph["goal_ids"]),
            root_ordinals=root_ordinals,
            normal_forms=forms,
            contexts=tuple(contexts),
            obligations=obligations,
            traces=tuple(self.traces),
            unsupported_semantic_sha256s=unsupported,
        )


def _diagnostic(error: _NormalizationError) -> CanonicalNormalizationDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "canonical": "INVALID_CANONICAL_INPUT",
        "context": "INVALID_CANONICAL_CONTEXT",
        "graph": "INVALID_CANONICAL_GRAPH",
        "identity": "INVALID_IDENTITY",
        "reference": "INVALID_REFERENCE",
        "rule": "INVALID_NORMALIZATION_RULE",
        "schema": "INVALID_SCHEMA",
        "scope": "INVALID_SCOPE",
        "trace": "INVALID_OCCURRENCE_TRACE",
        "type": "INVALID_TYPE",
        "upstream": "INVALID_PROOF_OBLIGATIONS",
    }.get(error.kind, "INVALID_CANONICAL_GRAPH")
    path = error.path[:4096] or "$"
    message = error.detail[:512] or "invalid canonical normalization"
    return CanonicalNormalizationDiagnostic(code=code, path=path, message=message)


def _raw_candidates_by_reading(
    raw: object,
    *,
    path: str,
    value_key: str,
) -> dict[str, dict[str, Any]]:
    if type(raw) is not list:
        _fail("schema", path, "candidate wrappers must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, wrapper in enumerate(raw):
        item_path = f"{path}[{index}]"
        if type(wrapper) is not dict:
            _fail("schema", item_path, "candidate wrapper must be an object")
        reading_id = wrapper.get("reading_id")
        value = wrapper.get(value_key)
        if type(reading_id) is not str or _ID_RE.fullmatch(reading_id) is None:
            _fail("schema", item_path, "invalid reading identity")
        if type(value) is not dict:
            _fail("schema", item_path, f"missing {value_key}")
        if reading_id in result:
            _fail("schema", item_path, "duplicate reading candidate")
        result[reading_id] = value
    return result


def normalize_canonical_obligations(
    proof_result: bytes,
) -> CanonicalNormalizationResult:
    """Normalize exact replay-valid MH-043 bytes without solving anything."""
    try:
        if type(proof_result) is not bytes:
            _fail("type", "$", "proof_result must be exact bytes")
        if len(proof_result) > MAX_INPUT_BYTES:
            _fail("budget", "$", "proof-obligation result byte budget exceeded")
        try:
            parsed = parse_proof_obligation_result(proof_result)
        except ProofObligationValidationError as exc:
            _fail(
                "budget" if exc.kind == "budget" else "upstream",
                exc.path,
                str(exc),
            )
        if parsed.status != "decomposed":
            _fail(
                "upstream",
                "$.status",
                "only a decomposed MH-043 result can be normalized",
            )
        if proof_obligation_result_bytes(parsed) != proof_result:
            _fail("upstream", "$", "proof-obligation result round-trip drift")
        if len(parsed.candidates) > MAX_READINGS:
            _fail("budget", "$.candidates", "reading budget exceeded")

        raw = _json_object(proof_result, "$")
        domain_raw = raw.get("domain_assumption_result")
        if type(domain_raw) is not dict:
            _fail("schema", "$.domain_assumption_result", "missing embedded result")
        readings_raw = domain_raw.get("readings_result")
        if type(readings_raw) is not dict:
            _fail("schema", "$.domain_assumption_result.readings_result", "missing result")
        projections = _raw_candidates_by_reading(
            readings_raw.get("candidates"),
            path="$.domain_assumption_result.readings_result.candidates",
            value_key="projection",
        )
        domain_candidates = _raw_candidates_by_reading(
            domain_raw.get("candidates"),
            path="$.domain_assumption_result.candidates",
            value_key="context",
        )
        proof_candidates = _raw_candidates_by_reading(
            raw.get("candidates"), path="$.candidates", value_key="graph",
        )
        expected_ids = tuple(item.reading_id for item in parsed.candidates)
        for membership, path in (
            (projections, "$.domain_assumption_result.readings_result.candidates"),
            (domain_candidates, "$.domain_assumption_result.candidates"),
            (proof_candidates, "$.candidates"),
        ):
            if set(membership) != set(expected_ids):
                _fail("graph", path, "reading membership drift")
        if not expected_ids:
            _fail("graph", "$.candidates", "normalization requires a candidate")

        steps = [0]
        candidates: list[CanonicalNormalizationCandidate] = []
        for reading_id in expected_ids:
            graph = proof_candidates[reading_id]
            if len(graph.get("goal_ids", ())) > MAX_GOALS:
                _fail("budget", f"$.candidates.{reading_id}.graph", "goal budget exceeded")
            candidates.append(
                _CandidateNormalizer(
                    reading_id=reading_id,
                    projection=projections[reading_id],
                    domain_candidate={"context": domain_candidates[reading_id]},
                    proof_candidate={
                        "graph_sha256": next(
                            item.graph_sha256
                            for item in parsed.candidates
                            if item.reading_id == reading_id
                        ),
                        "graph": graph,
                    },
                    steps=steps,
                ).build()
            )
        aggregate_limits = {
            "domains": MAX_DOMAINS,
            "variables": MAX_VARIABLES,
            "expressions": MAX_EXPRESSIONS,
            "relations": MAX_RELATIONS,
            "statements": MAX_STATEMENTS,
            "definitions": MAX_DEFINITIONS,
            "assumption_facts": MAX_FACTS,
        }
        for registry, maximum in aggregate_limits.items():
            count = sum(
                1
                for candidate in candidates
                for form in candidate.normal_forms
                if form.source_registry == registry
            )
            if count > maximum:
                _fail("budget", "$.candidates", f"aggregate {registry} budget exceeded")
        if sum(len(item.normal_forms) for item in candidates) > MAX_FORMS:
            _fail("budget", "$.candidates", "aggregate normal-form budget exceeded")
        if sum(len(item.contexts) for item in candidates) > MAX_CONTEXTS:
            _fail("budget", "$.candidates", "aggregate context budget exceeded")
        if sum(len(item.obligations) for item in candidates) > MAX_OBLIGATIONS:
            _fail("budget", "$.candidates", "aggregate obligation budget exceeded")
        if sum(len(item.traces) for item in candidates) > MAX_TRACES:
            _fail("budget", "$.candidates", "aggregate trace budget exceeded")
        result = _new_result(
            status="normalized",
            reason_code="NORMALIZED",
            input_result_sha256=_sha(proof_result),
            proof_result_bytes=proof_result,
            ambiguity_status=parsed.ambiguity_status,
            selected_reading_id=parsed.selected_reading_id,
            candidates=tuple(candidates),
            diagnostics=(),
        )
        result_sha256 = _sha(
            _canonical_bytes(_result_mapping(result, include_digest=False))
        )
        result = _new_result(
            status=result.status,
            reason_code=result.reason_code,
            input_result_sha256=result.input_result_sha256,
            proof_result_bytes=result.proof_result_bytes,
            ambiguity_status=result.ambiguity_status,
            selected_reading_id=result.selected_reading_id,
            candidates=result.candidates,
            diagnostics=result.diagnostics,
            result_sha256=result_sha256,
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
                CanonicalNormalizationDiagnostic(
                    code="BUDGET_EXHAUSTED",
                    path="$",
                    message="recursive normalization exceeded the structural budget",
                ),
            ),
        )


def _require_exact_tuple(value: object, path: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise CanonicalNormalizationValidationError(
            "type", path, "expected exact immutable tuple"
        )
    return value


def _validate_form(form: object) -> CanonicalNormalForm:
    if type(form) is not CanonicalNormalForm:
        raise CanonicalNormalizationValidationError(
            "type", "$", "expected exact CanonicalNormalForm"
        )
    assert isinstance(form, CanonicalNormalForm)
    if (
        _FORM_KINDS.get(form.source_registry) != form.form_kind
        or type(form.source_ref) is not str
        or not form.source_ref
        or type(form.rule_ids) is not tuple
        or not form.rule_ids
        or len(form.rule_ids) > 128
        or len(set(form.rule_ids)) != len(form.rule_ids)
        or any(type(item) is not str or _RULE_RE.fullmatch(item) is None for item in form.rule_ids)
        or type(form.supported) is not bool
        or form.mathematical_authority is not False
    ):
        raise CanonicalNormalizationValidationError("schema", "$", "normal form drift")
    try:
        expected = _sha(_canonical_bytes(form.value))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc
    if form.semantic_sha256 != expected:
        raise CanonicalNormalizationValidationError(
            "identity", "$.semantic_sha256", "normal form digest drift"
        )
    return form


def _validate_trace(trace: object) -> CanonicalOccurrenceTrace:
    if type(trace) is not CanonicalOccurrenceTrace:
        raise CanonicalNormalizationValidationError(
            "type", "$", "expected exact CanonicalOccurrenceTrace"
        )
    assert isinstance(trace, CanonicalOccurrenceTrace)
    if (
        re.fullmatch(r"trace_[0-9]{8}", trace.trace_id) is None
        or trace.kind not in {
            "quantified_binder", "definition_parameter", "commutative_operand",
            "assumption_order", "hypothesis_order", "witness_slot",
            "preserved_order", "opaque",
        }
        or trace.owner_kind not in {
            "definition", "relation", "statement", "local_context", "obligation"
        }
        or type(trace.owner_ref) is not str
        or not trace.owner_ref
        or type(trace.source_ref) is not str
        or not trace.source_ref
        or type(trace.source_index) is not int
        or type(trace.canonical_index) is not int
        or not 0 <= trace.source_index < 400_000
        or not 0 <= trace.canonical_index < 400_000
        or _SHA_RE.fullmatch(trace.semantic_sha256) is None
        or _RULE_RE.fullmatch(trace.rule_id) is None
        or trace.mathematical_authority is not False
    ):
        raise CanonicalNormalizationValidationError("trace", "$", "occurrence trace drift")
    return trace


def _validate_occurrence(item: object, path: str) -> CanonicalOccurrence:
    if type(item) is not CanonicalOccurrence:
        raise CanonicalNormalizationValidationError("type", path, "invalid occurrence")
    assert isinstance(item, CanonicalOccurrence)
    if (
        type(item.source_ref) is not str
        or not item.source_ref
        or _SHA_RE.fullmatch(item.semantic_sha256) is None
        or type(item.role) is not str
        or not item.role
        or type(item.source_index) is not int
        or type(item.canonical_index) is not int
        or not 0 <= item.source_index < 400_000
        or not 0 <= item.canonical_index < 400_000
    ):
        raise CanonicalNormalizationValidationError("schema", path, "occurrence drift")
    return item


def _validate_context_value(context: object) -> CanonicalContext:
    if type(context) is not CanonicalContext:
        raise CanonicalNormalizationValidationError(
            "type", "$", "expected exact CanonicalContext"
        )
    assert isinstance(context, CanonicalContext)
    occurrence_groups = (
        context.definition_occurrences,
        context.assumption_occurrences,
        context.bound_variable_occurrences,
        context.hypothesis_occurrences,
        context.witness_occurrences,
    )
    for group_index, group in enumerate(occurrence_groups):
        _require_exact_tuple(group, f"$.occurrences[{group_index}]")
        for index, item in enumerate(group):
            _validate_occurrence(item, f"$.occurrences[{group_index}][{index}]")
        if {item.source_index for item in group} != set(range(len(group))):
            raise CanonicalNormalizationValidationError(
                "trace", "$", "source occurrence indexes are not a permutation"
            )
        if {item.canonical_index for item in group} != set(range(len(group))):
            raise CanonicalNormalizationValidationError(
                "trace", "$", "canonical occurrence indexes are not a permutation"
            )
    for path, values in (
        ("$.dependency_semantic_sha256s", context.dependency_semantic_sha256s),
        ("$.source_span_ids", context.source_span_ids),
        ("$.trace_ids", context.trace_ids),
    ):
        _require_exact_tuple(values, path)
        if any(type(item) is not str for item in values):
            raise CanonicalNormalizationValidationError("schema", path, "string tuple drift")
    try:
        expected = _sha(_canonical_bytes(context.semantic_value))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc
    if (
        context.semantic_sha256 != expected
        or _SHA_RE.fullmatch(context.source_local_context_sha256) is None
        or context.mathematical_authority is not False
    ):
        raise CanonicalNormalizationValidationError("identity", "$", "context digest drift")
    return context


def _validate_obligation_value(obligation: object) -> CanonicalObligation:
    if type(obligation) is not CanonicalObligation:
        raise CanonicalNormalizationValidationError(
            "type", "$", "expected exact CanonicalObligation"
        )
    assert isinstance(obligation, CanonicalObligation)
    try:
        statement_digest = _sha(_canonical_bytes(obligation.statement_normal_form))
        semantic_digest = _sha(_canonical_bytes(obligation.semantic_value))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc
    tuple_fields = (
        obligation.child_ordinals,
        obligation.prerequisite_ordinals,
        obligation.witness_slots,
        obligation.strategy_ids,
        obligation.strategy_record_sha256s,
        obligation.dependency_semantic_sha256s,
        obligation.source_span_ids,
        obligation.trace_ids,
    )
    if any(type(item) is not tuple for item in tuple_fields):
        raise CanonicalNormalizationValidationError("type", "$", "obligation tuple drift")
    if (
        statement_digest != obligation.statement_semantic_sha256
        or semantic_digest != obligation.semantic_sha256
        or _SHA_RE.fullmatch(obligation.source_obligation_sha256) is None
        or _SHA_RE.fullmatch(obligation.local_context_semantic_sha256) is None
        or type(obligation.ordinal) is not int
        or obligation.ordinal < 0
        or type(obligation.supported) is not bool
        or obligation.mathematical_authority is not False
    ):
        raise CanonicalNormalizationValidationError("identity", "$", "obligation drift")
    return obligation


def canonical_normal_form_bytes(form: CanonicalNormalForm) -> bytes:
    """Serialize one validated canonical normal form."""
    form = _validate_form(form)
    try:
        return _canonical_bytes(_form_mapping(form))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc


def canonical_occurrence_trace_bytes(trace: CanonicalOccurrenceTrace) -> bytes:
    """Serialize one validated reversible occurrence trace."""
    trace = _validate_trace(trace)
    try:
        return _canonical_bytes(_trace_mapping(trace))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc


def canonical_context_bytes(context: CanonicalContext) -> bytes:
    """Serialize one validated normalized local context."""
    context = _validate_context_value(context)
    try:
        return _canonical_bytes(_context_mapping(context))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc


def canonical_obligation_bytes(obligation: CanonicalObligation) -> bytes:
    """Serialize one validated normalized obligation."""
    obligation = _validate_obligation_value(obligation)
    try:
        return _canonical_bytes(_obligation_mapping(obligation))
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc


def _validate_result_shape(result: object) -> CanonicalNormalizationResult:
    if type(result) is not CanonicalNormalizationResult:
        raise CanonicalNormalizationValidationError(
            "type", "$", "expected exact CanonicalNormalizationResult"
        )
    assert isinstance(result, CanonicalNormalizationResult)
    constants = {
        "schema": RESULT_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "proof_obligation_contract_id": PROOF_OBLIGATION_CONTRACT_ID,
        "proof_obligation_contract_sha256": PROOF_OBLIGATION_CONTRACT_SHA256,
        "domain_assumption_contract_id": DOMAIN_ASSUMPTION_CONTRACT_ID,
        "domain_assumption_contract_sha256": DOMAIN_ASSUMPTION_CONTRACT_SHA256,
        "reading_analysis_contract_id": READING_ANALYSIS_CONTRACT_ID,
        "reading_analysis_contract_sha256": READING_ANALYSIS_CONTRACT_SHA256,
        "problem_intake_contract_id": PROBLEM_INTAKE_CONTRACT_ID,
        "problem_intake_contract_sha256": PROBLEM_INTAKE_CONTRACT_SHA256,
        "problem_ir_contract_id": PROBLEM_IR_CONTRACT_ID,
        "problem_ir_contract_sha256": PROBLEM_IR_CONTRACT_SHA256,
        "rule_catalogue_sha256": RULE_CATALOGUE_SHA256,
        "mathematical_authority": False,
    }
    for field, expected in constants.items():
        actual = getattr(result, field, None)
        if type(actual) is not type(expected) or actual != expected:
            raise CanonicalNormalizationValidationError(
                "result", f"$.{field}", "binding drift"
            )
    if result.status not in {"normalized", "invalid", "exhausted"}:
        raise CanonicalNormalizationValidationError("result", "$.status", "state drift")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > 32:
        raise CanonicalNormalizationValidationError(
            "result", "$.diagnostics", "diagnostic collection drift"
        )
    for item in result.diagnostics:
        if (
            type(item) is not CanonicalNormalizationDiagnostic
            or type(item.code) is not str
            or re.fullmatch(r"[A-Z][A-Z0-9_]*", item.code) is None
            or type(item.path) is not str
            or not item.path
            or len(item.path) > 4096
            or type(item.message) is not str
            or not item.message
            or len(item.message) > 512
        ):
            raise CanonicalNormalizationValidationError(
                "result", "$.diagnostics", "diagnostic drift"
            )
    if result.status != "normalized":
        if not (
            result.input_result_sha256 is None
            and result.proof_result_bytes is None
            and result.ambiguity_status is None
            and result.selected_reading_id is None
            and result.candidates == ()
            and result.result_sha256 is None
            and result.diagnostics
            and result.reason_code == result.diagnostics[0].code
        ):
            raise CanonicalNormalizationValidationError(
                "result", "$", "failed combination drift"
            )
        if (result.status == "exhausted") != (
            result.reason_code == "BUDGET_EXHAUSTED"
        ):
            raise CanonicalNormalizationValidationError(
                "result", "$", "failed reason drift"
            )
        return result
    if (
        result.reason_code != "NORMALIZED"
        or result.diagnostics
        or type(result.proof_result_bytes) is not bytes
        or type(result.input_result_sha256) is not str
        or _sha(result.proof_result_bytes) != result.input_result_sha256
        or result.ambiguity_status not in {"unambiguous", "unresolved", "resolved"}
        or type(result.candidates) is not tuple
        or not result.candidates
        or _SHA_RE.fullmatch(result.result_sha256 or "") is None
    ):
        raise CanonicalNormalizationValidationError(
            "result", "$", "normalized combination drift"
        )
    ids = tuple(item.reading_id for item in result.candidates)
    if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
        raise CanonicalNormalizationValidationError(
            "result", "$.candidates", "candidate order drift"
        )
    return result


def validate_canonical_normalization_result(result: object) -> None:
    """Replay one closed result and reject every forged inner value."""
    result = _validate_result_shape(result)
    if result.status == "normalized":
        assert result.proof_result_bytes is not None
        expected = normalize_canonical_obligations(result.proof_result_bytes)
        if expected != result:
            raise CanonicalNormalizationValidationError(
                "result", "$", "canonical normalization replay drift"
            )
        expected_digest = _sha(
            _canonical_bytes(_result_mapping(result, include_digest=False))
        )
        if result.result_sha256 != expected_digest:
            raise CanonicalNormalizationValidationError(
                "identity", "$.result_sha256", "result digest drift"
            )


def canonical_normalization_result_bytes(
    result: CanonicalNormalizationResult,
) -> bytes:
    """Serialize one closed replay-valid canonical normalization result."""
    validate_canonical_normalization_result(result)
    try:
        return _result_bytes_unchecked(result)
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc


def canonical_normalization_result_sha256(
    result: CanonicalNormalizationResult,
) -> str:
    """Return the identity stored over the result excluding only itself."""
    validate_canonical_normalization_result(result)
    assert result.result_sha256 is not None
    return result.result_sha256


def parse_canonical_normalization_result(data: bytes) -> CanonicalNormalizationResult:
    """Strictly parse canonical bytes and replay every normalized artifact."""
    if type(data) is not bytes:
        raise CanonicalNormalizationValidationError(
            "type", "$", "result must be exact bytes"
        )
    if len(data) > MAX_OUTPUT_BYTES:
        raise CanonicalNormalizationValidationError(
            "budget", "$", "result byte budget exceeded"
        )
    try:
        value = _json_object(data, "$")
        if _canonical_bytes(value) != data:
            raise CanonicalNormalizationValidationError(
                "canonical", "$", "result is noncanonical"
            )
    except _NormalizationError as exc:
        raise CanonicalNormalizationValidationError(exc.kind, exc.path, exc.detail) from exc
    fields = {
        "schema", "contract_id", "contract_sha256",
        "proof_obligation_contract_id", "proof_obligation_contract_sha256",
        "domain_assumption_contract_id", "domain_assumption_contract_sha256",
        "reading_analysis_contract_id", "reading_analysis_contract_sha256",
        "problem_intake_contract_id", "problem_intake_contract_sha256",
        "problem_ir_contract_id", "problem_ir_contract_sha256",
        "rule_catalogue_sha256", "status", "reason_code", "input_result_sha256",
        "proof_obligation_result", "ambiguity_status", "selected_reading_id",
        "candidates", "diagnostics", "result_sha256", "mathematical_authority",
    }
    if set(value) != fields:
        raise CanonicalNormalizationValidationError(
            "schema", "$", "result field set drift"
        )
    if value["status"] == "normalized":
        embedded = value["proof_obligation_result"]
        if type(embedded) is not dict:
            raise CanonicalNormalizationValidationError(
                "schema", "$.proof_obligation_result", "missing input"
            )
        try:
            input_bytes = _canonical_bytes(embedded, maximum=MAX_INPUT_BYTES)
        except _NormalizationError as exc:
            raise CanonicalNormalizationValidationError(
                exc.kind, exc.path, exc.detail
            ) from exc
        expected = normalize_canonical_obligations(input_bytes)
        if expected.status != "normalized" or _result_mapping(expected) != value:
            raise CanonicalNormalizationValidationError(
                "result", "$", "historical replay drift"
            )
        if _result_bytes_unchecked(expected) != data:
            raise CanonicalNormalizationValidationError(
                "canonical", "$", "result round-trip drift"
            )
        return expected
    raw_diagnostics = value["diagnostics"]
    if type(raw_diagnostics) is not list:
        raise CanonicalNormalizationValidationError(
            "schema", "$.diagnostics", "expected diagnostic array"
        )
    diagnostics: list[CanonicalNormalizationDiagnostic] = []
    for index, raw in enumerate(raw_diagnostics):
        if type(raw) is not dict or set(raw) != {"code", "path", "message"}:
            raise CanonicalNormalizationValidationError(
                "schema", f"$.diagnostics[{index}]", "diagnostic field drift"
            )
        diagnostics.append(CanonicalNormalizationDiagnostic(**raw))
    result = _new_result(
        schema=value["schema"],
        contract_id=value["contract_id"],
        contract_sha256=value["contract_sha256"],
        proof_obligation_contract_id=value["proof_obligation_contract_id"],
        proof_obligation_contract_sha256=value["proof_obligation_contract_sha256"],
        domain_assumption_contract_id=value["domain_assumption_contract_id"],
        domain_assumption_contract_sha256=value["domain_assumption_contract_sha256"],
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
        proof_result_bytes=None,
        ambiguity_status=value["ambiguity_status"],
        selected_reading_id=value["selected_reading_id"],
        candidates=(),
        diagnostics=tuple(diagnostics),
        result_sha256=value["result_sha256"],
        mathematical_authority=value["mathematical_authority"],
    )
    validate_canonical_normalization_result(result)
    if _result_bytes_unchecked(result) != data:
        raise CanonicalNormalizationValidationError(
            "canonical", "$", "failed result round-trip drift"
        )
    return result
