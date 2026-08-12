"""Deterministic structural explanations for unsupported MH-044 records.

This boundary explains only support metadata already present in a replay-valid
canonical-normalization result.  It does not parse prose, discover capability,
transform mathematics, or claim mathematical authority.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, fields
import hashlib
import json
import re
from typing import Any, Final, NoReturn, TypeVar
import unicodedata

from mathhead import canonical_normalization as canonical


CONTRACT_ID: Final = "MH-C-UNSUPPORTED-EXPLANATION-001"
CONTRACT_SHA256: Final = \
    "35248c92eea2253c153b4cc0d1be2cffead624c417c74ca5562696e8d07786f9"
CATALOGUE_SHA256: Final = \
    "902c5ed06273b8372794e20f2309861d70002455b7b3389a0054e3627681848e"
_CATALOGUE_CANONICAL_SHA256: Final = \
    "5fecc447071f362fedeb4790f9cfc32495d30f42465a5e7169eb712a368b3723"

CANONICAL_NORMALIZATION_CONTRACT_ID: Final = canonical.CONTRACT_ID
CANONICAL_NORMALIZATION_CONTRACT_SHA256: Final = canonical.CONTRACT_SHA256
PROOF_OBLIGATION_CONTRACT_ID: Final = "MH-C-PROOF-OBLIGATION-DECOMPOSITION-001"
PROOF_OBLIGATION_CONTRACT_SHA256: Final = \
    "ea5d0664611b57da3074e20fce90623318ce04280d38ecce548025a91a7b19ff"
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

TARGET_SCHEMA_SHA256: Final = \
    "3650aa309cab01e6dc63c4cc5cc3aa07f92caa3a7cef879fc2a70e0082c68cfc"
OWNED_FRAGMENT_SCHEMA_SHA256: Final = \
    "6c678c9cf115fc99de34f1f38c45b5bc6d7e8c6ef957d29f811659423687d3e9"
FORMALIZATION_STEP_SCHEMA_SHA256: Final = \
    "142e609977e9cdb0d6fe37a26831ea34c146ad0c07e7245467df667a4f0bd601"
EXPLANATION_SCHEMA_SHA256: Final = \
    "17c6fe18e2b0c545c922d049e330e8ad18e0a94876a7b5613a7001bfaa4e6973"
CATALOGUE_SCHEMA_SHA256: Final = \
    "6131d3e5c9d0244ba79422fba80549a0d473651f46e9e7a8448e6b52455d234e"
RESULT_SCHEMA_SHA256: Final = \
    "b2e490c657737519d57b6e9bca30a095790c167e50feb36d9c79a03335ce8051"

RESULT_SCHEMA: Final = "mathhead.unsupported-explanation-result.v1"
TARGET_SCHEMA: Final = "mathhead.unsupported-target.v1"
FRAGMENT_SCHEMA: Final = "mathhead.owned-fragment.v1"
STEP_SCHEMA: Final = "mathhead.formalization-step.v1"
EXPLANATION_SCHEMA: Final = "mathhead.unsupported-explanation.v1"

MAX_INPUT_BYTES: Final = 1_073_741_824
MAX_OUTPUT_BYTES: Final = 1_073_741_824
MAX_READINGS: Final = 100_000
MAX_TARGETS: Final = 2_400_000
MAX_PARAMETERS: Final = 64
MAX_DIAGNOSTICS: Final = 32
MAX_DEPENDENCIES: Final = 2_400_000
MAX_SOURCE_SPANS: Final = 1_200_000
MAX_TRACES: Final = 2_400_000
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_AGGREGATE_STRING_CODEPOINTS: Final = 67_108_864
MAX_RENDERED_CODEPOINTS: Final = 8_192
MAX_NESTING: Final = 512
MAX_STEPS: Final = 64_000_000
MAX_INTEGER: Final = 9_007_199_254_740_991

_SHA_RE: Final = re.compile(r"^[0-9a-f]{64}$")
_ID_RE: Final = re.compile(r"^[a-z][a-z0-9_]*$")
_REF_RE: Final = re.compile(r"^[A-Za-z0-9_.:-]+$")
_CODE_RE: Final = re.compile(r"^[A-Z][A-Z0-9_]*$")
_TARGET_RE: Final = re.compile(r"^target_([0-9]{8})$")
_EXPLANATION_RE: Final = re.compile(r"^explanation_([0-9]{8})$")
_TRACE_RE: Final = re.compile(r"^trace_[0-9]{8}$")
_CONSTRUCT_RE: Final = re.compile(
    r"^mh[.]unsupported[.]construct[.][a-z0-9_.-]+$"
)

_VALUE_TOKEN = object()


class UnsupportedExplanationValidationError(ValueError):
    """A classified strict-codec or closed-value validation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        super().__init__(f"{kind} at {path}: {detail}")
        self.kind = kind
        self.path = path
        self.detail = detail


class _ExplanationError(ValueError):
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


class _ClosedValue:
    __slots__ = ()

    def __init__(self, *, _token: object | None = None, **values: object) -> None:
        if _token is not _VALUE_TOKEN:
            raise PermissionError("closed explanation values are constructed by MathHead")
        names = tuple(field.name for field in fields(self))
        if set(values) != set(names):
            raise TypeError("closed explanation field set drift")
        for name in names:
            object.__setattr__(self, name, values[name])

    def __reduce__(self) -> NoReturn:
        raise TypeError("closed explanation values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("closed explanation values cannot be pickled")

    def __copy__(self) -> _ClosedValue:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> _ClosedValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class UnsupportedExplanationDiagnostic(_ClosedValue):
    code: str
    path: str
    message: str

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("UnsupportedExplanationDiagnostic is final")


@dataclass(frozen=True, slots=True, init=False)
class UnsupportedTarget(_ClosedValue):
    target_id: str
    ordinal: int
    reading_id: str
    surface: str
    source_registry: str
    source_ref: str
    form_kind: str | None
    source_semantic_sha256: str
    construct_code: str
    construct_parameters: _FrozenMap
    context_semantic_sha256: str | None
    obligation_ordinal: int | None
    dependency_semantic_sha256s: tuple[str, ...]
    source_span_ids: tuple[str, ...]
    trace_ids: tuple[str, ...]
    cause_sha256: str
    mathematical_authority: bool = False

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("UnsupportedTarget is final")


@dataclass(frozen=True, slots=True, init=False)
class OwnedFragment(_ClosedValue):
    fragment_code: str
    owner_boundary: str
    owner_contract_id: str | None
    owner_contract_sha256: str | None
    owner_kind: str
    match_basis: str
    catalogue_rule_id: str
    generic_fallback: bool
    mathematical_authority: bool = False

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("OwnedFragment is final")


@dataclass(frozen=True, slots=True, init=False)
class FormalizationStep(_ClosedValue):
    action_code: str
    summary_template_id: str
    detail_template_id: str
    parameters: _FrozenMap
    required_input_codes: tuple[str, ...]
    safety_condition_codes: tuple[str, ...]
    automatic: bool = False
    requires_user_confirmation: bool = True
    mathematical_authority: bool = False

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("FormalizationStep is final")


@dataclass(frozen=True, slots=True, init=False)
class UnsupportedExplanation(_ClosedValue):
    explanation_id: str
    ordinal: int
    target_id: str
    cause_sha256: str
    construct_code: str
    construct_parameters: _FrozenMap
    catalogue_rule_id: str
    owned_fragment: OwnedFragment
    formalization_step: FormalizationStep
    summary: str
    detail: str
    explanation_sha256: str
    mathematical_authority: bool = False

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("UnsupportedExplanation is final")


@dataclass(frozen=True, slots=True, init=False)
class UnsupportedExplanationCandidate(_ClosedValue):
    reading_id: str
    source_graph_sha256: str
    semantic_graph_sha256: str
    unsupported_semantic_sha256s: tuple[str, ...]
    targets: tuple[UnsupportedTarget, ...]
    explanations: tuple[UnsupportedExplanation, ...]
    explanation_set_sha256: str
    mathematical_authority: bool = False

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("UnsupportedExplanationCandidate is final")


@dataclass(frozen=True, slots=True, init=False)
class UnsupportedExplanationResult(_ClosedValue):
    schema: str
    contract_id: str
    contract_sha256: str
    canonical_normalization_contract_id: str
    canonical_normalization_contract_sha256: str
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
    catalogue_sha256: str
    status: str
    reason_code: str
    input_result_sha256: str | None
    normalization_result_bytes: bytes | None
    ambiguity_status: str | None
    selected_reading_id: str | None
    candidates: tuple[UnsupportedExplanationCandidate, ...]
    diagnostics: tuple[UnsupportedExplanationDiagnostic, ...]
    result_sha256: str | None
    mathematical_authority: bool

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("UnsupportedExplanationResult is final")


_T = TypeVar("_T", bound=_ClosedValue)


def _make(value_type: type[_T], **values: object) -> _T:
    return value_type(_token=_VALUE_TOKEN, **values)  # type: ignore[call-arg]


def _fail(kind: str, path: str, detail: str) -> NoReturn:
    raise _ExplanationError(kind, path, detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _step(steps: list[int], path: str, count: int = 1) -> None:
    steps[0] += count
    if steps[0] > MAX_STEPS:
        _fail("budget", path, "explanation-step budget exceeded")


def _freeze(value: object) -> object:
    if type(value) is dict:
        return _FrozenMap(
            tuple((key, _freeze(item)) for key, item in sorted(value.items()))
        )
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
        if type(item) in (dict, list, tuple, _FrozenMap):
            marker = id(item)
            if marker in seen:
                _fail("canonical", path, "cyclic canonical value")
            seen.add(marker)
            try:
                if type(item) is _FrozenMap:
                    iterator = item.entries
                elif type(item) is dict:
                    iterator = tuple(item.items())
                else:
                    iterator = tuple(enumerate(item))
                for key, child in iterator:
                    if type(item) in (dict, _FrozenMap):
                        if type(key) is not str:
                            _fail("canonical", path, "object key is not an exact string")
                        check(key, f"{path}.<key>", depth + 1)
                        check(child, f"{path}.{key}", depth + 1)
                    else:
                        check(child, f"{path}[{key}]", depth + 1)
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


def _json_object(data: bytes, path: str = "$") -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except _ExplanationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail("canonical", path, f"value is not strict UTF-8 JSON: {exc}")
    if type(value) is not dict:
        _fail("schema", path, "root must be an exact JSON object")
    return value


@dataclass(frozen=True, slots=True)
class _Rule:
    rule_id: str
    priority: int
    match_surface: str
    match_form_kind: str | None
    match_fact_kind: str | None
    match_obligation_kind: str | None
    construct_code: str
    fragment_code: str
    owner_boundary: str
    owner_contract_id: str | None
    owner_contract_sha256: str | None
    owner_kind: str
    match_basis: str
    action_code: str
    summary_template_id: str
    detail_template_id: str
    summary_template: str
    detail_template: str
    parameter_names: tuple[str, ...]
    required_input_codes: tuple[str, ...]
    safety_condition_codes: tuple[str, ...]
    generic_fallback: bool


_RULES: Final = (
    _Rule(
        rule_id="mh.unsupported.rule.opaque-predicate-assumption",
        priority=0,
        match_surface="normal_form",
        match_form_kind="assumption_fact",
        match_fact_kind="opaque_predicate_assumption",
        match_obligation_kind=None,
        construct_code="mh.unsupported.construct.opaque-predicate-assumption",
        fragment_code="mh.fragment.problem-ir.named-predicate",
        owner_boundary="problem_ir",
        owner_contract_id=PROBLEM_IR_CONTRACT_ID,
        owner_contract_sha256=PROBLEM_IR_CONTRACT_SHA256,
        owner_kind="relation.predicate",
        match_basis="exact_fact_kind",
        action_code="DECLARE_EXACT_PREDICATE_DEFINITION",
        summary_template_id="mh.unsupported.template.opaque-predicate.summary",
        detail_template_id="mh.unsupported.template.opaque-predicate.detail",
        summary_template=(
            "Predicate {predicate_id} with arity {arity} is declared but has no "
            "reviewed structural assumption rule."
        ),
        detail_template=(
            "The nearest owned fragment is the exact named-predicate relation. "
            "Declare a typed definition or a separately contracted assumption rule "
            "for {predicate_id}; do not replace it with a different predicate without "
            "confirming semantic equivalence."
        ),
        parameter_names=("arity", "predicate_id"),
        required_input_codes=(
            "EXACT_PREDICATE_ID", "EXPLICIT_PARAMETER_DOMAINS",
            "EXPLICIT_PREDICATE_MEANING",
        ),
        safety_condition_codes=(
            "NO_EQUIVALENCE_ASSUMED", "NO_SOURCE_REWRITE",
            "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=False,
    ),
    _Rule(
        rule_id="mh.unsupported.rule.opaque-relation-assumption",
        priority=1,
        match_surface="normal_form",
        match_form_kind="assumption_fact",
        match_fact_kind="opaque_relation_assumption",
        match_obligation_kind=None,
        construct_code="mh.unsupported.construct.opaque-relation-assumption",
        fragment_code="mh.fragment.problem-ir.typed-relation",
        owner_boundary="problem_ir",
        owner_contract_id=PROBLEM_IR_CONTRACT_ID,
        owner_contract_sha256=PROBLEM_IR_CONTRACT_SHA256,
        owner_kind="relation",
        match_basis="exact_fact_kind",
        action_code="EXPRESS_WITH_OWNED_RELATION",
        summary_template_id="mh.unsupported.template.opaque-relation.summary",
        detail_template_id="mh.unsupported.template.opaque-relation.detail",
        summary_template=(
            "Relation kind {relation_kind} is retained exactly but has no reviewed "
            "structural assumption rule."
        ),
        detail_template=(
            "The nearest owned fragment is a typed ProblemIR relation. Express the "
            "condition with one owned relation only if its meaning is exactly the same, "
            "or retain {relation_kind} for a separately contracted rule."
        ),
        parameter_names=("relation_kind",),
        required_input_codes=(
            "EXACT_RELATION_KIND", "EXPLICIT_OPERAND_DOMAINS",
            "SEMANTIC_EQUIVALENCE_CONFIRMATION",
        ),
        safety_condition_codes=(
            "NO_RELATION_SUBSTITUTION", "NO_SOURCE_REWRITE",
            "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=False,
    ),
    _Rule(
        rule_id="mh.unsupported.rule.logical-assumption",
        priority=2,
        match_surface="normal_form",
        match_form_kind="assumption_fact",
        match_fact_kind="logical_assumption",
        match_obligation_kind=None,
        construct_code="mh.unsupported.construct.logical-assumption",
        fragment_code="mh.fragment.domain-assumptions.atomic-fact",
        owner_boundary="domain_assumptions",
        owner_contract_id=DOMAIN_ASSUMPTION_CONTRACT_ID,
        owner_contract_sha256=DOMAIN_ASSUMPTION_CONTRACT_SHA256,
        owner_kind="assumption.atomic",
        match_basis="exact_fact_kind",
        action_code="SPLIT_LOGICAL_ASSUMPTION_EXPLICITLY",
        summary_template_id="mh.unsupported.template.logical-assumption.summary",
        detail_template_id="mh.unsupported.template.logical-assumption.detail",
        summary_template=(
            "Logical assumption operator {operator} is preserved as one opaque fact "
            "rather than decomposed."
        ),
        detail_template=(
            "The nearest owned fragment is an atomic normalized assumption fact. "
            "Declare the intended component assumptions explicitly only when that "
            "decomposition is logically valid for {operator}; otherwise retain the "
            "logical assumption for a separately contracted rule."
        ),
        parameter_names=("operator",),
        required_input_codes=(
            "EXPLICIT_LOGICAL_OPERATOR", "EXPLICIT_COMPONENT_ASSUMPTIONS",
            "DECOMPOSITION_EQUIVALENCE_CONFIRMATION",
        ),
        safety_condition_codes=(
            "NO_IMPLICATION_INFERENCE", "NO_DUPLICATE_COLLAPSE",
            "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=False,
    ),
    _Rule(
        rule_id="mh.unsupported.rule.quantified-assumption",
        priority=3,
        match_surface="normal_form",
        match_form_kind="assumption_fact",
        match_fact_kind="quantified_assumption",
        match_obligation_kind=None,
        construct_code="mh.unsupported.construct.quantified-assumption",
        fragment_code="mh.fragment.problem-ir.quantified-statement",
        owner_boundary="problem_ir",
        owner_contract_id=PROBLEM_IR_CONTRACT_ID,
        owner_contract_sha256=PROBLEM_IR_CONTRACT_SHA256,
        owner_kind="statement.quantified",
        match_basis="exact_fact_kind",
        action_code="CONTRACT_QUANTIFIED_ASSUMPTION_RULE",
        summary_template_id="mh.unsupported.template.quantified-assumption.summary",
        detail_template_id="mh.unsupported.template.quantified-assumption.detail",
        summary_template=(
            "Quantified assumption {quantifier} with {binder_count} binder occurrences "
            "is represented but not normalized into assumption facts."
        ),
        detail_template=(
            "The nearest owned fragment is the typed quantified statement. Add an "
            "explicit reviewed normalization rule that preserves binder order, scope, "
            "and domains; do not instantiate or drop {quantifier} automatically."
        ),
        parameter_names=("binder_count", "quantifier"),
        required_input_codes=(
            "EXACT_QUANTIFIER", "EXPLICIT_BINDER_DOMAINS", "SCOPE_PRESERVING_RULE",
        ),
        safety_condition_codes=(
            "NO_AUTOMATIC_INSTANTIATION", "NO_BINDER_REORDER",
            "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=False,
    ),
    _Rule(
        rule_id="mh.unsupported.rule.unsupported-obligation",
        priority=4,
        match_surface="obligation",
        match_form_kind=None,
        match_fact_kind=None,
        match_obligation_kind="unsupported",
        construct_code="mh.unsupported.construct.proof-obligation",
        fragment_code="mh.fragment.proof-obligations.typed-duty",
        owner_boundary="proof_obligations",
        owner_contract_id=PROOF_OBLIGATION_CONTRACT_ID,
        owner_contract_sha256=PROOF_OBLIGATION_CONTRACT_SHA256,
        owner_kind="obligation.typed",
        match_basis="exact_obligation_kind",
        action_code="REFORMALIZE_UNSUPPORTED_OBLIGATION",
        summary_template_id="mh.unsupported.template.obligation.summary",
        detail_template_id="mh.unsupported.template.obligation.detail",
        summary_template=(
            "Obligation {obligation_id} for goal mode {goal_mode} has no reviewed "
            "decomposition rule for its exact statement shape."
        ),
        detail_template=(
            "The nearest owned fragment is a typed proof duty with preserved context and "
            "topology. Re-express the statement as supported explicit sub-obligations "
            "only after proving that the reformulation preserves the original goal; "
            "otherwise retain this duty unsupported."
        ),
        parameter_names=("goal_mode", "obligation_id"),
        required_input_codes=(
            "EXACT_ORIGINAL_GOAL", "EXPLICIT_SUB_OBLIGATIONS",
            "REFORMULATION_EQUIVALENCE_CONFIRMATION",
        ),
        safety_condition_codes=(
            "NO_GOAL_WEAKENING", "NO_TOPOLOGY_CHANGE", "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=False,
    ),
    _Rule(
        rule_id="mh.unsupported.rule.generic-fallback",
        priority=127,
        match_surface="any",
        match_form_kind=None,
        match_fact_kind=None,
        match_obligation_kind=None,
        construct_code="mh.unsupported.construct.unclassified",
        fragment_code="mh.fragment.none",
        owner_boundary="none",
        owner_contract_id=None,
        owner_contract_sha256=None,
        owner_kind="unclassified",
        match_basis="generic_fallback",
        action_code="RETAIN_FOR_SEPARATE_CAPABILITY",
        summary_template_id="mh.unsupported.template.generic.summary",
        detail_template_id="mh.unsupported.template.generic.detail",
        summary_template=(
            "Construct {source_ref} is retained exactly but has no registered owned "
            "fragment match."
        ),
        detail_template=(
            "Keep the construct unchanged and define a separately reviewed contract "
            "before attempting to transform or execute it. No equivalence, availability, "
            "solvability, or truth claim is implied."
        ),
        parameter_names=("source_ref",),
        required_input_codes=(
            "EXACT_SOURCE_CONSTRUCT", "SEPARATE_CAPABILITY_CONTRACT",
        ),
        safety_condition_codes=(
            "NO_GUESSING", "NO_SOURCE_REWRITE", "USER_CONFIRMATION_REQUIRED",
        ),
        generic_fallback=True,
    ),
)

_RULE_BY_ID: Final = {rule.rule_id: rule for rule in _RULES}


def _rule_mapping(rule: _Rule) -> dict[str, object]:
    return {
        "rule_id": rule.rule_id,
        "priority": rule.priority,
        "match_surface": rule.match_surface,
        "match_form_kind": rule.match_form_kind,
        "match_fact_kind": rule.match_fact_kind,
        "match_obligation_kind": rule.match_obligation_kind,
        "construct_code": rule.construct_code,
        "fragment_code": rule.fragment_code,
        "owner_boundary": rule.owner_boundary,
        "owner_contract_id": rule.owner_contract_id,
        "owner_contract_sha256": rule.owner_contract_sha256,
        "owner_kind": rule.owner_kind,
        "match_basis": rule.match_basis,
        "action_code": rule.action_code,
        "summary_template_id": rule.summary_template_id,
        "detail_template_id": rule.detail_template_id,
        "summary_template": rule.summary_template,
        "detail_template": rule.detail_template,
        "parameter_names": list(rule.parameter_names),
        "required_input_codes": list(rule.required_input_codes),
        "safety_condition_codes": list(rule.safety_condition_codes),
        "generic_fallback": rule.generic_fallback,
    }


def _catalogue_mapping() -> dict[str, object]:
    return {
        "schema": "mathhead.unsupported-explanation-catalogue.v1",
        "catalogue_id": "mh.unsupported.catalogue.v1",
        "entries": [_rule_mapping(rule) for rule in _RULES],
        "fallback_rule_id": "mh.unsupported.rule.generic-fallback",
        "mathematical_authority": False,
    }


def _validate_catalogue() -> None:
    actual_catalogue_sha256 = _sha(_canonical_bytes(_catalogue_mapping()))
    if actual_catalogue_sha256 != _CATALOGUE_CANONICAL_SHA256:
        _fail(
            "catalogue",
            "$catalogue",
            f"compiled catalogue binding drift: {actual_catalogue_sha256}",
        )
    priorities = tuple(rule.priority for rule in _RULES)
    if priorities != tuple(sorted(set(priorities))):
        _fail("catalogue", "$catalogue", "catalogue priorities are not unique and sorted")
    for rule in _RULES:
        if tuple(sorted(rule.parameter_names)) != rule.parameter_names:
            _fail("catalogue", rule.rule_id, "parameter names are not sorted")
        for parameter in rule.parameter_names:
            placeholder = "{" + parameter + "}"
            counts = (
                rule.summary_template.count(placeholder),
                rule.detail_template.count(placeholder),
            )
            if max(counts) > 1 or sum(counts) < 1:
                _fail("catalogue", rule.rule_id, "template placeholder count drift")
    if sum(rule.generic_fallback for rule in _RULES) != 1 or not _RULES[-1].generic_fallback:
        _fail("catalogue", "$catalogue", "generic fallback drift")


_validate_catalogue()


def _target_mapping(target: UnsupportedTarget) -> dict[str, object]:
    return {
        "schema": TARGET_SCHEMA,
        "target_id": target.target_id,
        "ordinal": target.ordinal,
        "reading_id": target.reading_id,
        "surface": target.surface,
        "source_registry": target.source_registry,
        "source_ref": target.source_ref,
        "form_kind": target.form_kind,
        "source_semantic_sha256": target.source_semantic_sha256,
        "construct_code": target.construct_code,
        "construct_parameters": _thaw(target.construct_parameters),
        "context_semantic_sha256": target.context_semantic_sha256,
        "obligation_ordinal": target.obligation_ordinal,
        "dependency_semantic_sha256s": list(target.dependency_semantic_sha256s),
        "source_span_ids": list(target.source_span_ids),
        "trace_ids": list(target.trace_ids),
        "cause_sha256": target.cause_sha256,
        "mathematical_authority": target.mathematical_authority,
    }


def _fragment_mapping(fragment: OwnedFragment) -> dict[str, object]:
    return {
        "schema": FRAGMENT_SCHEMA,
        "fragment_code": fragment.fragment_code,
        "owner_boundary": fragment.owner_boundary,
        "owner_contract_id": fragment.owner_contract_id,
        "owner_contract_sha256": fragment.owner_contract_sha256,
        "owner_kind": fragment.owner_kind,
        "match_basis": fragment.match_basis,
        "catalogue_rule_id": fragment.catalogue_rule_id,
        "generic_fallback": fragment.generic_fallback,
        "mathematical_authority": fragment.mathematical_authority,
    }


def _step_mapping(step: FormalizationStep) -> dict[str, object]:
    return {
        "schema": STEP_SCHEMA,
        "action_code": step.action_code,
        "summary_template_id": step.summary_template_id,
        "detail_template_id": step.detail_template_id,
        "parameters": _thaw(step.parameters),
        "required_input_codes": list(step.required_input_codes),
        "safety_condition_codes": list(step.safety_condition_codes),
        "automatic": step.automatic,
        "requires_user_confirmation": step.requires_user_confirmation,
        "mathematical_authority": step.mathematical_authority,
    }


def _explanation_mapping(
    explanation: UnsupportedExplanation, *, include_digest: bool = True,
) -> dict[str, object]:
    value = {
        "schema": EXPLANATION_SCHEMA,
        "explanation_id": explanation.explanation_id,
        "ordinal": explanation.ordinal,
        "target_id": explanation.target_id,
        "cause_sha256": explanation.cause_sha256,
        "construct_code": explanation.construct_code,
        "construct_parameters": _thaw(explanation.construct_parameters),
        "catalogue_rule_id": explanation.catalogue_rule_id,
        "owned_fragment": _fragment_mapping(explanation.owned_fragment),
        "formalization_step": _step_mapping(explanation.formalization_step),
        "summary": explanation.summary,
        "detail": explanation.detail,
        "mathematical_authority": explanation.mathematical_authority,
    }
    value["explanation_sha256"] = (
        explanation.explanation_sha256 if include_digest else None
    )
    return value


def _candidate_mapping(
    candidate: UnsupportedExplanationCandidate, *, include_digest: bool = True,
) -> dict[str, object]:
    return {
        "reading_id": candidate.reading_id,
        "source_graph_sha256": candidate.source_graph_sha256,
        "semantic_graph_sha256": candidate.semantic_graph_sha256,
        "unsupported_semantic_sha256s": list(
            candidate.unsupported_semantic_sha256s
        ),
        "targets": [_target_mapping(item) for item in candidate.targets],
        "explanations": [_explanation_mapping(item) for item in candidate.explanations],
        "explanation_set_sha256": (
            candidate.explanation_set_sha256 if include_digest else None
        ),
        "mathematical_authority": candidate.mathematical_authority,
    }


def _result_mapping(
    result: UnsupportedExplanationResult, *, include_digest: bool = True,
) -> dict[str, object]:
    normalization_result = (
        None
        if result.normalization_result_bytes is None
        else _json_object(result.normalization_result_bytes, "$.normalization_result")
    )
    return {
        "schema": result.schema,
        "contract_id": result.contract_id,
        "contract_sha256": result.contract_sha256,
        "canonical_normalization_contract_id": (
            result.canonical_normalization_contract_id
        ),
        "canonical_normalization_contract_sha256": (
            result.canonical_normalization_contract_sha256
        ),
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
        "catalogue_sha256": result.catalogue_sha256,
        "status": result.status,
        "reason_code": result.reason_code,
        "input_result_sha256": result.input_result_sha256,
        "normalization_result": normalization_result,
        "ambiguity_status": result.ambiguity_status,
        "selected_reading_id": result.selected_reading_id,
        "candidates": [_candidate_mapping(item) for item in result.candidates],
        "diagnostics": [
            {"code": item.code, "path": item.path, "message": item.message}
            for item in result.diagnostics
        ],
        "result_sha256": result.result_sha256 if include_digest else None,
        "mathematical_authority": result.mathematical_authority,
    }


def _new_result(**values: object) -> UnsupportedExplanationResult:
    defaults: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "canonical_normalization_contract_id": CANONICAL_NORMALIZATION_CONTRACT_ID,
        "canonical_normalization_contract_sha256": (
            CANONICAL_NORMALIZATION_CONTRACT_SHA256
        ),
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
        "catalogue_sha256": CATALOGUE_SHA256,
        "status": "invalid",
        "reason_code": "INVALID_TYPE",
        "input_result_sha256": None,
        "normalization_result_bytes": None,
        "ambiguity_status": None,
        "selected_reading_id": None,
        "candidates": (),
        "diagnostics": (),
        "result_sha256": None,
        "mathematical_authority": False,
    }
    defaults.update(values)
    return _make(UnsupportedExplanationResult, **defaults)


def _require_object(value: object, path: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("inventory", path, "expected exact object")
    return value


def _require_string(value: object, path: str) -> str:
    if type(value) is not str or not value:
        _fail("inventory", path, "expected non-empty exact string")
    if "\x00" in value or unicodedata.normalize("NFC", value) != value:
        _fail("canonical", path, "string must be NUL-free NFC")
    return value


def _require_sequence(value: object, path: str) -> tuple[object, ...]:
    if type(value) not in (list, tuple):
        _fail("inventory", path, "expected exact sequence")
    return tuple(value)


def _semantic_parameters(value: Mapping[str, object], path: str) -> _FrozenMap:
    if len(value) > MAX_PARAMETERS:
        _fail("budget", path, "parameter budget exceeded")
    normalized: dict[str, object] = {}
    for key, item in sorted(value.items()):
        if type(key) is not str or _ID_RE.fullmatch(key) is None or len(key) > 64:
            _fail("template", path, "invalid parameter name")
        if type(item) is int:
            if type(item) is bool or not -MAX_INTEGER <= item <= MAX_INTEGER:
                _fail("template", f"{path}.{key}", "invalid integer parameter")
        elif type(item) is str:
            if (
                not item
                or len(item) > MAX_STRING_CODEPOINTS
                or any(ord(character) < 32 or ord(character) == 127 for character in item)
                or unicodedata.normalize("NFC", item) != item
            ):
                _fail("template", f"{path}.{key}", "invalid string parameter")
        else:
            _fail("template", f"{path}.{key}", "render parameters must be scalar")
        normalized[key] = item
    frozen = _freeze(normalized)
    assert type(frozen) is _FrozenMap
    return frozen


def _render(rule: _Rule, parameters: _FrozenMap) -> tuple[str, str]:
    values = dict(parameters.entries)
    if tuple(values) != rule.parameter_names:
        _fail("template", rule.rule_id, "complete exact template parameters required")

    def render(template: str, path: str) -> str:
        output = template
        for name in rule.parameter_names:
            placeholder = "{" + name + "}"
            if output.count(placeholder) > 1:
                _fail("template", path, "template placeholder drift")
            output = output.replace(placeholder, str(values[name]))
        if "{" in output or "}" in output:
            _fail("template", path, "unknown template placeholder")
        if (
            not output
            or len(output) > MAX_RENDERED_CODEPOINTS
            or "\x00" in output
            or unicodedata.normalize("NFC", output) != output
        ):
            _fail("template", path, "rendered text budget or normalization drift")
        return output

    return (
        render(rule.summary_template, f"{rule.rule_id}.summary"),
        render(rule.detail_template, f"{rule.rule_id}.detail"),
    )


def _select_rule(
    *, surface: str, form_kind: str | None, fact_kind: str | None,
    obligation_kind: str | None,
) -> _Rule:
    matches = [
        rule
        for rule in _RULES
        if not rule.generic_fallback
        and rule.match_surface == surface
        and (rule.match_form_kind is None or rule.match_form_kind == form_kind)
        and (rule.match_fact_kind is None or rule.match_fact_kind == fact_kind)
        and (
            rule.match_obligation_kind is None
            or rule.match_obligation_kind == obligation_kind
        )
    ]
    if len(matches) > 1:
        _fail("catalogue", "$catalogue", "ambiguous exact rule match")
    return matches[0] if matches else _RULES[-1]


def _parameters_for(
    rule: _Rule, *, semantic_value: dict[str, Any], source_ref: str,
    goal_mode: str | None = None,
) -> _FrozenMap:
    if rule.rule_id == "mh.unsupported.rule.opaque-predicate-assumption":
        relation = _require_object(semantic_value.get("relation"), "$.value.relation")
        predicate = _require_string(relation.get("predicate"), "$.value.relation.predicate")
        operands = _require_sequence(relation.get("operands"), "$.value.relation.operands")
        return _semantic_parameters(
            {"arity": len(operands), "predicate_id": predicate}, "$.parameters"
        )
    if rule.rule_id == "mh.unsupported.rule.opaque-relation-assumption":
        relation = _require_object(semantic_value.get("relation"), "$.value.relation")
        relation_kind = _require_string(relation.get("kind"), "$.value.relation.kind")
        return _semantic_parameters({"relation_kind": relation_kind}, "$.parameters")
    if rule.rule_id == "mh.unsupported.rule.logical-assumption":
        statement = _require_object(semantic_value.get("statement"), "$.value.statement")
        operator = _require_string(statement.get("operator"), "$.value.statement.operator")
        return _semantic_parameters({"operator": operator}, "$.parameters")
    if rule.rule_id == "mh.unsupported.rule.quantified-assumption":
        statement = _require_object(semantic_value.get("statement"), "$.value.statement")
        quantifier = _require_string(
            statement.get("quantifier"), "$.value.statement.quantifier"
        )
        variables = _require_sequence(
            statement.get("variables"), "$.value.statement.variables"
        )
        return _semantic_parameters(
            {"binder_count": len(variables), "quantifier": quantifier}, "$.parameters"
        )
    if rule.rule_id == "mh.unsupported.rule.unsupported-obligation":
        return _semantic_parameters(
            {
                "goal_mode": _require_string(goal_mode, "$.obligation.goal_mode"),
                "obligation_id": source_ref,
            },
            "$.parameters",
        )
    return _semantic_parameters({"source_ref": source_ref}, "$.parameters")


def _cause_sha256(
    *, reading_id: str, construct_code: str, parameters: _FrozenMap,
    source_semantic_sha256: str,
) -> str:
    return _sha(
        _canonical_bytes(
            {
                "reading_id": reading_id,
                "construct_code": construct_code,
                "construct_parameters": _thaw(parameters),
                "source_semantic_sha256": source_semantic_sha256,
            }
        )
    )


def _make_fragment(rule: _Rule) -> OwnedFragment:
    return _make(
        OwnedFragment,
        fragment_code=rule.fragment_code,
        owner_boundary=rule.owner_boundary,
        owner_contract_id=rule.owner_contract_id,
        owner_contract_sha256=rule.owner_contract_sha256,
        owner_kind=rule.owner_kind,
        match_basis=rule.match_basis,
        catalogue_rule_id=rule.rule_id,
        generic_fallback=rule.generic_fallback,
        mathematical_authority=False,
    )


def _make_formalization_step(
    rule: _Rule, parameters: _FrozenMap,
) -> FormalizationStep:
    return _make(
        FormalizationStep,
        action_code=rule.action_code,
        summary_template_id=rule.summary_template_id,
        detail_template_id=rule.detail_template_id,
        parameters=parameters,
        required_input_codes=rule.required_input_codes,
        safety_condition_codes=rule.safety_condition_codes,
        automatic=False,
        requires_user_confirmation=True,
        mathematical_authority=False,
    )


def _make_explanation(
    target: UnsupportedTarget, rule: _Rule,
) -> UnsupportedExplanation:
    summary, detail = _render(rule, target.construct_parameters)
    fragment = _make_fragment(rule)
    step = _make_formalization_step(rule, target.construct_parameters)
    values: dict[str, object] = {
        "explanation_id": f"explanation_{target.ordinal:08d}",
        "ordinal": target.ordinal,
        "target_id": target.target_id,
        "cause_sha256": target.cause_sha256,
        "construct_code": target.construct_code,
        "construct_parameters": target.construct_parameters,
        "catalogue_rule_id": rule.rule_id,
        "owned_fragment": fragment,
        "formalization_step": step,
        "summary": summary,
        "detail": detail,
        "explanation_sha256": "0" * 64,
        "mathematical_authority": False,
    }
    draft = _make(UnsupportedExplanation, **values)
    values["explanation_sha256"] = _sha(
        _canonical_bytes(_explanation_mapping(draft, include_digest=False))
    )
    return _make(UnsupportedExplanation, **values)


def _upstream_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _upstream_thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_upstream_thaw(item) for item in value]
    return value


def _sha_tuple(value: object, path: str, maximum: int) -> tuple[str, ...]:
    sequence = _require_sequence(value, path)
    if len(sequence) > maximum:
        _fail("budget", path, "identity collection budget exceeded")
    result: list[str] = []
    for index, item in enumerate(sequence):
        if type(item) is not str or _SHA_RE.fullmatch(item) is None:
            _fail("inventory", f"{path}[{index}]", "invalid SHA-256 identity")
        result.append(item)
    if result != sorted(set(result)):
        _fail("inventory", path, "identity collection must be sorted and unique")
    return tuple(result)


def _id_tuple(value: object, path: str, maximum: int) -> tuple[str, ...]:
    sequence = _require_sequence(value, path)
    if len(sequence) > maximum:
        _fail("budget", path, "identifier collection budget exceeded")
    result: list[str] = []
    for index, item in enumerate(sequence):
        if type(item) is not str or _ID_RE.fullmatch(item) is None or len(item) > 64:
            _fail("inventory", f"{path}[{index}]", "invalid identifier")
        result.append(item)
    if result != sorted(set(result)):
        _fail("inventory", path, "identifier collection must be sorted and unique")
    return tuple(result)


def _trace_tuple(value: object, path: str) -> tuple[str, ...]:
    sequence = _require_sequence(value, path)
    if len(sequence) > MAX_TRACES:
        _fail("budget", path, "trace collection budget exceeded")
    result = tuple(sequence)
    if any(type(item) is not str or _TRACE_RE.fullmatch(item) is None for item in result):
        _fail("inventory", path, "invalid trace identity")
    if result != tuple(sorted(set(result))):
        _fail("inventory", path, "trace collection must be sorted and unique")
    return result  # type: ignore[return-value]


def _project_sha_set(value: object, path: str) -> tuple[str, ...]:
    sequence = _require_sequence(value, path)
    if len(sequence) > MAX_DEPENDENCIES:
        _fail("budget", path, "dependency collection budget exceeded")
    result: set[str] = set()
    for index, item in enumerate(sequence):
        if type(item) is not str or _SHA_RE.fullmatch(item) is None:
            _fail("inventory", f"{path}[{index}]", "invalid dependency identity")
        result.add(item)
    return tuple(sorted(result))


def _facts_by_reading(raw: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    proof = _require_object(
        raw.get("proof_obligation_result"), "$.proof_obligation_result"
    )
    domain = _require_object(
        proof.get("domain_assumption_result"),
        "$.proof_obligation_result.domain_assumption_result",
    )
    wrappers = _require_sequence(
        domain.get("candidates"),
        "$.proof_obligation_result.domain_assumption_result.candidates",
    )
    if len(wrappers) > MAX_READINGS:
        _fail("budget", "$.candidates", "reading budget exceeded")
    result: dict[str, dict[str, dict[str, Any]]] = {}
    for index, wrapper_value in enumerate(wrappers):
        path = f"$.proof_obligation_result.domain_assumption_result.candidates[{index}]"
        wrapper = _require_object(wrapper_value, path)
        reading_id = _require_string(wrapper.get("reading_id"), f"{path}.reading_id")
        context = _require_object(wrapper.get("context"), f"{path}.context")
        facts = _require_sequence(context.get("facts"), f"{path}.context.facts")
        fact_index: dict[str, dict[str, Any]] = {}
        for fact_index_value, fact_value in enumerate(facts):
            fact_path = f"{path}.context.facts[{fact_index_value}]"
            fact = _require_object(fact_value, fact_path)
            fact_sha256 = _require_string(fact.get("fact_sha256"), f"{fact_path}.fact_sha256")
            if _SHA_RE.fullmatch(fact_sha256) is None or fact_sha256 in fact_index:
                _fail("inventory", fact_path, "invalid or duplicate fact identity")
            fact_index[fact_sha256] = fact
        if reading_id in result:
            _fail("inventory", path, "duplicate reading fact inventory")
        result[reading_id] = fact_index
    return result


def _form_context_sha256(
    candidate: canonical.CanonicalNormalizationCandidate, source_ref: str,
) -> str | None:
    owners: set[str] = set()
    for context in candidate.contexts:
        occurrences = (
            *context.definition_occurrences,
            *context.assumption_occurrences,
            *context.bound_variable_occurrences,
            *context.hypothesis_occurrences,
            *context.witness_occurrences,
        )
        if any(item.source_ref == source_ref for item in occurrences):
            owners.add(context.semantic_sha256)
    return next(iter(owners)) if len(owners) == 1 else None


def _target_for_form(
    *, ordinal: int, candidate: canonical.CanonicalNormalizationCandidate,
    form: canonical.CanonicalNormalForm, fact_index: dict[str, dict[str, Any]],
) -> tuple[UnsupportedTarget, _Rule]:
    value = _upstream_thaw(form.value)
    semantic_value = _require_object(value, "$.normal_form.value")
    fact_kind_value = semantic_value.get("kind")
    fact_kind = fact_kind_value if type(fact_kind_value) is str else None
    rule = _select_rule(
        surface="normal_form",
        form_kind=form.form_kind,
        fact_kind=fact_kind,
        obligation_kind=None,
    )
    parameters = _parameters_for(
        rule, semantic_value=semantic_value, source_ref=form.source_ref
    )
    cause_sha256 = _cause_sha256(
        reading_id=candidate.reading_id,
        construct_code=rule.construct_code,
        parameters=parameters,
        source_semantic_sha256=form.semantic_sha256,
    )
    dependencies_value = semantic_value.get("dependencies", [])
    dependencies = _project_sha_set(
        dependencies_value, "$.normal_form.value.dependencies"
    )
    fact = fact_index.get(form.source_ref)
    spans = ()
    if fact is not None:
        spans = _id_tuple(
            fact.get("span_ids"), "$.domain_assumption_fact.span_ids", MAX_SOURCE_SPANS
        )
    traces = tuple(
        sorted(
            item.trace_id
            for item in candidate.traces
            if item.source_ref == form.source_ref
        )
    )
    target = _make(
        UnsupportedTarget,
        target_id=f"target_{ordinal:08d}",
        ordinal=ordinal,
        reading_id=candidate.reading_id,
        surface="normal_form",
        source_registry=form.source_registry,
        source_ref=form.source_ref,
        form_kind=form.form_kind,
        source_semantic_sha256=form.semantic_sha256,
        construct_code=rule.construct_code,
        construct_parameters=parameters,
        context_semantic_sha256=_form_context_sha256(candidate, form.source_ref),
        obligation_ordinal=None,
        dependency_semantic_sha256s=dependencies,
        source_span_ids=spans,
        trace_ids=traces,
        cause_sha256=cause_sha256,
        mathematical_authority=False,
    )
    return target, rule


def _target_for_obligation(
    *, ordinal: int, candidate: canonical.CanonicalNormalizationCandidate,
    obligation: canonical.CanonicalObligation,
) -> tuple[UnsupportedTarget, _Rule]:
    value = _upstream_thaw(obligation.semantic_value)
    semantic_value = _require_object(value, "$.obligation.semantic_value")
    rule = _select_rule(
        surface="obligation",
        form_kind=None,
        fact_kind=None,
        obligation_kind=obligation.kind,
    )
    parameters = _parameters_for(
        rule,
        semantic_value=semantic_value,
        source_ref=obligation.source_obligation_id,
        goal_mode=obligation.goal_mode,
    )
    cause_sha256 = _cause_sha256(
        reading_id=candidate.reading_id,
        construct_code=rule.construct_code,
        parameters=parameters,
        source_semantic_sha256=obligation.semantic_sha256,
    )
    target = _make(
        UnsupportedTarget,
        target_id=f"target_{ordinal:08d}",
        ordinal=ordinal,
        reading_id=candidate.reading_id,
        surface="obligation",
        source_registry="obligations",
        source_ref=obligation.source_obligation_id,
        form_kind=None,
        source_semantic_sha256=obligation.semantic_sha256,
        construct_code=rule.construct_code,
        construct_parameters=parameters,
        context_semantic_sha256=obligation.local_context_semantic_sha256,
        obligation_ordinal=obligation.ordinal,
        dependency_semantic_sha256s=tuple(
            sorted(set(obligation.dependency_semantic_sha256s))
        ),
        source_span_ids=obligation.source_span_ids,
        trace_ids=obligation.trace_ids,
        cause_sha256=cause_sha256,
        mathematical_authority=False,
    )
    return target, rule


def _build_candidate(
    candidate: canonical.CanonicalNormalizationCandidate,
    fact_index: dict[str, dict[str, Any]],
    steps: list[int],
) -> UnsupportedExplanationCandidate:
    targets: list[UnsupportedTarget] = []
    explanations: list[UnsupportedExplanation] = []
    unsupported_forms = tuple(item for item in candidate.normal_forms if not item.supported)
    unsupported_obligations = tuple(
        item for item in candidate.obligations if not item.supported
    )
    if len(unsupported_forms) + len(unsupported_obligations) > MAX_TARGETS:
        _fail("budget", "$.candidates.targets", "target budget exceeded")
    for form in unsupported_forms:
        _step(steps, "$.candidates.targets")
        target, rule = _target_for_form(
            ordinal=len(targets), candidate=candidate, form=form, fact_index=fact_index
        )
        targets.append(target)
        explanations.append(_make_explanation(target, rule))
    for obligation in unsupported_obligations:
        _step(steps, "$.candidates.targets")
        target, rule = _target_for_obligation(
            ordinal=len(targets), candidate=candidate, obligation=obligation
        )
        targets.append(target)
        explanations.append(_make_explanation(target, rule))
    target_index = tuple(sorted({item.source_semantic_sha256 for item in targets}))
    if target_index != candidate.unsupported_semantic_sha256s:
        _fail(
            "inventory",
            f"$.candidates.{candidate.reading_id}.unsupported_semantic_sha256s",
            "target inventory does not equal the unsupported semantic index",
        )
    values: dict[str, object] = {
        "reading_id": candidate.reading_id,
        "source_graph_sha256": candidate.source_graph_sha256,
        "semantic_graph_sha256": candidate.semantic_graph_sha256,
        "unsupported_semantic_sha256s": candidate.unsupported_semantic_sha256s,
        "targets": tuple(targets),
        "explanations": tuple(explanations),
        "explanation_set_sha256": "0" * 64,
        "mathematical_authority": False,
    }
    draft = _make(UnsupportedExplanationCandidate, **values)
    values["explanation_set_sha256"] = _sha(
        _canonical_bytes(_candidate_mapping(draft, include_digest=False))
    )
    return _make(UnsupportedExplanationCandidate, **values)


def _diagnostic(error: _ExplanationError) -> UnsupportedExplanationDiagnostic:
    code = {
        "budget": "BUDGET_EXHAUSTED",
        "canonical": "INVALID_CANONICAL_INPUT",
        "catalogue": "INVALID_CATALOGUE",
        "identity": "INVALID_IDENTITY",
        "inventory": "INVALID_UNSUPPORTED_INVENTORY",
        "reference": "INVALID_REFERENCE",
        "result": "INVALID_RESULT",
        "schema": "INVALID_SCHEMA",
        "template": "INVALID_TEMPLATE",
        "type": "INVALID_TYPE",
        "upstream": "INVALID_CANONICAL_NORMALIZATION",
    }.get(error.kind, "INVALID_UNSUPPORTED_INVENTORY")
    return _make(
        UnsupportedExplanationDiagnostic,
        code=code,
        path=(error.path[:4096] or "$"),
        message=(error.detail[:512] or "invalid unsupported explanation"),
    )


def explain_unsupported_constructs(
    normalization_result: bytes,
) -> UnsupportedExplanationResult:
    """Explain every already-declared unsupported occurrence without authority."""
    try:
        _validate_catalogue()
        if type(normalization_result) is not bytes:
            _fail("type", "$", "normalization_result must be exact bytes")
        if len(normalization_result) > MAX_INPUT_BYTES:
            _fail("budget", "$", "normalization result byte budget exceeded")
        try:
            parsed = canonical.parse_canonical_normalization_result(normalization_result)
        except canonical.CanonicalNormalizationValidationError as exc:
            _fail("budget" if exc.kind == "budget" else "upstream", exc.path, str(exc))
        if parsed.status != "normalized":
            _fail(
                "upstream", "$.status",
                "only a normalized MH-044 result can be explained",
            )
        if canonical.canonical_normalization_result_bytes(parsed) != normalization_result:
            _fail("upstream", "$", "canonical normalization round-trip drift")
        if len(parsed.candidates) > MAX_READINGS:
            _fail("budget", "$.candidates", "reading budget exceeded")
        raw = _json_object(normalization_result)
        fact_indexes = _facts_by_reading(raw)
        if set(fact_indexes) != {item.reading_id for item in parsed.candidates}:
            _fail("inventory", "$.candidates", "reading fact inventory drift")
        steps = [0]
        candidates = tuple(
            _build_candidate(candidate, fact_indexes[candidate.reading_id], steps)
            for candidate in parsed.candidates
        )
        result = _new_result(
            status="explained",
            reason_code="EXPLAINED",
            input_result_sha256=_sha(normalization_result),
            normalization_result_bytes=normalization_result,
            ambiguity_status=parsed.ambiguity_status,
            selected_reading_id=parsed.selected_reading_id,
            candidates=candidates,
            diagnostics=(),
        )
        result_sha256 = _sha(
            _canonical_bytes(_result_mapping(result, include_digest=False))
        )
        result = _new_result(
            status=result.status,
            reason_code=result.reason_code,
            input_result_sha256=result.input_result_sha256,
            normalization_result_bytes=result.normalization_result_bytes,
            ambiguity_status=result.ambiguity_status,
            selected_reading_id=result.selected_reading_id,
            candidates=result.candidates,
            diagnostics=result.diagnostics,
            result_sha256=result_sha256,
        )
        if len(_canonical_bytes(_result_mapping(result))) > MAX_OUTPUT_BYTES:
            _fail("budget", "$", "explanation result byte budget exceeded")
        return result
    except _ExplanationError as error:
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
                _make(
                    UnsupportedExplanationDiagnostic,
                    code="BUDGET_EXHAUSTED",
                    path="$",
                    message="recursive explanation exceeded the structural budget",
                ),
            ),
        )


def _exact_fields(value: dict[str, Any], expected: set[str], path: str) -> None:
    if set(value) != expected:
        _fail("schema", path, "object field set drift")


def _require_sha(value: object, path: str) -> str:
    if type(value) is not str or _SHA_RE.fullmatch(value) is None:
        _fail("schema", path, "invalid SHA-256 identity")
    return value


def _require_id(value: object, path: str) -> str:
    if (
        type(value) is not str
        or len(value) > 64
        or _ID_RE.fullmatch(value) is None
    ):
        _fail("schema", path, "invalid identifier")
    return value


def _target_from_mapping(value: object, path: str = "$") -> UnsupportedTarget:
    item = _require_object(value, path)
    _exact_fields(
        item,
        {
            "schema", "target_id", "ordinal", "reading_id", "surface",
            "source_registry", "source_ref", "form_kind", "source_semantic_sha256",
            "construct_code", "construct_parameters", "context_semantic_sha256",
            "obligation_ordinal", "dependency_semantic_sha256s", "source_span_ids",
            "trace_ids", "cause_sha256", "mathematical_authority",
        },
        path,
    )
    if item["schema"] != TARGET_SCHEMA or type(item["schema"]) is not str:
        _fail("schema", f"{path}.schema", "target schema drift")
    ordinal = item["ordinal"]
    if type(ordinal) is not int or not 0 <= ordinal < MAX_TARGETS:
        _fail("schema", f"{path}.ordinal", "invalid target ordinal")
    target_id = item["target_id"]
    if type(target_id) is not str or target_id != f"target_{ordinal:08d}":
        _fail("schema", f"{path}.target_id", "target identity drift")
    reading_id = _require_id(item["reading_id"], f"{path}.reading_id")
    surface = item["surface"]
    if type(surface) is not str or surface not in {"normal_form", "obligation"}:
        _fail("schema", f"{path}.surface", "invalid target surface")
    registries = {
        "domains", "variables", "expressions", "relations", "statements",
        "definitions", "assumption_facts", "local_contexts", "obligations",
    }
    source_registry = item["source_registry"]
    if type(source_registry) is not str or source_registry not in registries:
        _fail("schema", f"{path}.source_registry", "invalid source registry")
    source_ref = item["source_ref"]
    if (
        type(source_ref) is not str
        or not 1 <= len(source_ref) <= 256
        or _REF_RE.fullmatch(source_ref) is None
    ):
        _fail("schema", f"{path}.source_ref", "invalid source reference")
    form_kind = item["form_kind"]
    form_kinds = {
        "domain", "variable", "expression", "relation", "statement", "definition",
        "assumption_fact", "local_context", "obligation",
    }
    if form_kind is not None and (
        type(form_kind) is not str or form_kind not in form_kinds
    ):
        _fail("schema", f"{path}.form_kind", "invalid form kind")
    context_sha = item["context_semantic_sha256"]
    if context_sha is not None:
        context_sha = _require_sha(context_sha, f"{path}.context_semantic_sha256")
    obligation_ordinal = item["obligation_ordinal"]
    if obligation_ordinal is not None and (
        type(obligation_ordinal) is not int
        or not 0 <= obligation_ordinal < 800_000
    ):
        _fail("schema", f"{path}.obligation_ordinal", "invalid obligation ordinal")
    if surface == "obligation":
        if (
            source_registry != "obligations"
            or form_kind is not None
            or obligation_ordinal is None
            or context_sha is None
        ):
            _fail("schema", path, "obligation target combination drift")
    elif form_kind is None or obligation_ordinal is not None:
        _fail("schema", path, "normal-form target combination drift")
    construct_code = item["construct_code"]
    if type(construct_code) is not str or _CONSTRUCT_RE.fullmatch(construct_code) is None:
        _fail("schema", f"{path}.construct_code", "invalid construct code")
    parameter_value = _require_object(
        item["construct_parameters"], f"{path}.construct_parameters"
    )
    parameters = _semantic_parameters(parameter_value, f"{path}.construct_parameters")
    source_sha = _require_sha(
        item["source_semantic_sha256"], f"{path}.source_semantic_sha256"
    )
    expected_cause = _cause_sha256(
        reading_id=reading_id,
        construct_code=construct_code,
        parameters=parameters,
        source_semantic_sha256=source_sha,
    )
    cause_sha = _require_sha(item["cause_sha256"], f"{path}.cause_sha256")
    if cause_sha != expected_cause:
        _fail("identity", f"{path}.cause_sha256", "cause digest drift")
    if item["mathematical_authority"] is not False:
        _fail("result", f"{path}.mathematical_authority", "authority drift")
    return _make(
        UnsupportedTarget,
        target_id=target_id,
        ordinal=ordinal,
        reading_id=reading_id,
        surface=surface,
        source_registry=source_registry,
        source_ref=source_ref,
        form_kind=form_kind,
        source_semantic_sha256=source_sha,
        construct_code=construct_code,
        construct_parameters=parameters,
        context_semantic_sha256=context_sha,
        obligation_ordinal=obligation_ordinal,
        dependency_semantic_sha256s=_sha_tuple(
            item["dependency_semantic_sha256s"],
            f"{path}.dependency_semantic_sha256s",
            MAX_DEPENDENCIES,
        ),
        source_span_ids=_id_tuple(
            item["source_span_ids"], f"{path}.source_span_ids", MAX_SOURCE_SPANS
        ),
        trace_ids=_trace_tuple(item["trace_ids"], f"{path}.trace_ids"),
        cause_sha256=cause_sha,
        mathematical_authority=False,
    )


def _fragment_from_mapping(value: object, path: str) -> OwnedFragment:
    item = _require_object(value, path)
    _exact_fields(
        item,
        {
            "schema", "fragment_code", "owner_boundary", "owner_contract_id",
            "owner_contract_sha256", "owner_kind", "match_basis",
            "catalogue_rule_id", "generic_fallback", "mathematical_authority",
        },
        path,
    )
    rule_id = item["catalogue_rule_id"]
    if type(rule_id) is not str or rule_id not in _RULE_BY_ID:
        _fail("catalogue", f"{path}.catalogue_rule_id", "unknown catalogue rule")
    rule = _RULE_BY_ID[rule_id]
    expected = _fragment_mapping(_make_fragment(rule))
    if item != expected:
        _fail("catalogue", path, "owned-fragment catalogue projection drift")
    return _make_fragment(rule)


def _step_from_mapping(
    value: object, path: str, expected_rule: _Rule | None = None,
) -> FormalizationStep:
    item = _require_object(value, path)
    _exact_fields(
        item,
        {
            "schema", "action_code", "summary_template_id", "detail_template_id",
            "parameters", "required_input_codes", "safety_condition_codes",
            "automatic", "requires_user_confirmation", "mathematical_authority",
        },
        path,
    )
    matching = [
        rule
        for rule in _RULES
        if item.get("action_code") == rule.action_code
        and item.get("summary_template_id") == rule.summary_template_id
        and item.get("detail_template_id") == rule.detail_template_id
    ]
    if len(matching) != 1 or (expected_rule is not None and matching[0] != expected_rule):
        _fail("catalogue", path, "formalization-step catalogue projection drift")
    rule = matching[0]
    parameters_value = _require_object(item["parameters"], f"{path}.parameters")
    parameters = _semantic_parameters(parameters_value, f"{path}.parameters")
    expected = _step_mapping(_make_formalization_step(rule, parameters))
    if item != expected:
        _fail("catalogue", path, "formalization-step field drift")
    return _make_formalization_step(rule, parameters)


def _explanation_from_mapping(
    value: object, path: str = "$",
) -> UnsupportedExplanation:
    item = _require_object(value, path)
    _exact_fields(
        item,
        {
            "schema", "explanation_id", "ordinal", "target_id", "cause_sha256",
            "construct_code", "construct_parameters", "catalogue_rule_id",
            "owned_fragment", "formalization_step", "summary", "detail",
            "explanation_sha256", "mathematical_authority",
        },
        path,
    )
    if item["schema"] != EXPLANATION_SCHEMA or type(item["schema"]) is not str:
        _fail("schema", f"{path}.schema", "explanation schema drift")
    ordinal = item["ordinal"]
    if type(ordinal) is not int or not 0 <= ordinal < MAX_TARGETS:
        _fail("schema", f"{path}.ordinal", "invalid explanation ordinal")
    if item["explanation_id"] != f"explanation_{ordinal:08d}":
        _fail("schema", f"{path}.explanation_id", "explanation identity drift")
    if item["target_id"] != f"target_{ordinal:08d}":
        _fail("schema", f"{path}.target_id", "target identity drift")
    rule_id = item["catalogue_rule_id"]
    if type(rule_id) is not str or rule_id not in _RULE_BY_ID:
        _fail("catalogue", f"{path}.catalogue_rule_id", "unknown catalogue rule")
    rule = _RULE_BY_ID[rule_id]
    construct_code = item["construct_code"]
    if construct_code != rule.construct_code:
        _fail("catalogue", f"{path}.construct_code", "construct code drift")
    parameters_value = _require_object(
        item["construct_parameters"], f"{path}.construct_parameters"
    )
    parameters = _semantic_parameters(
        parameters_value, f"{path}.construct_parameters"
    )
    if tuple(parameters) != rule.parameter_names:
        _fail("template", f"{path}.construct_parameters", "parameter set drift")
    fragment = _fragment_from_mapping(item["owned_fragment"], f"{path}.owned_fragment")
    if fragment.catalogue_rule_id != rule_id:
        _fail("catalogue", f"{path}.owned_fragment", "rule association drift")
    step = _step_from_mapping(
        item["formalization_step"], f"{path}.formalization_step", rule
    )
    if step.parameters != parameters:
        _fail("template", f"{path}.formalization_step.parameters", "parameter drift")
    summary, detail = _render(rule, parameters)
    if item["summary"] != summary or item["detail"] != detail:
        _fail("template", path, "rendered explanation drift")
    cause_sha = _require_sha(item["cause_sha256"], f"{path}.cause_sha256")
    explanation_sha = _require_sha(
        item["explanation_sha256"], f"{path}.explanation_sha256"
    )
    values: dict[str, object] = {
        "explanation_id": item["explanation_id"],
        "ordinal": ordinal,
        "target_id": item["target_id"],
        "cause_sha256": cause_sha,
        "construct_code": construct_code,
        "construct_parameters": parameters,
        "catalogue_rule_id": rule_id,
        "owned_fragment": fragment,
        "formalization_step": step,
        "summary": summary,
        "detail": detail,
        "explanation_sha256": explanation_sha,
        "mathematical_authority": False,
    }
    if item["mathematical_authority"] is not False:
        _fail("result", f"{path}.mathematical_authority", "authority drift")
    result = _make(UnsupportedExplanation, **values)
    expected_sha = _sha(
        _canonical_bytes(_explanation_mapping(result, include_digest=False))
    )
    if explanation_sha != expected_sha:
        _fail("identity", f"{path}.explanation_sha256", "explanation digest drift")
    return result


def _component_from_bytes(
    data: bytes, parser: Any, *, maximum: int = MAX_OUTPUT_BYTES,
) -> Any:
    if type(data) is not bytes:
        raise UnsupportedExplanationValidationError(
            "type", "$", "component must be exact bytes"
        )
    if len(data) > maximum:
        raise UnsupportedExplanationValidationError(
            "budget", "$", "component byte budget exceeded"
        )
    try:
        value = _json_object(data)
        if _canonical_bytes(value, maximum=maximum) != data:
            _fail("canonical", "$", "component is noncanonical")
        return parser(value)
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc


def parse_unsupported_target(data: bytes) -> UnsupportedTarget:
    """Strictly parse one canonical unsupported target."""
    return _component_from_bytes(data, _target_from_mapping)


def parse_owned_fragment(data: bytes) -> OwnedFragment:
    """Strictly parse one frozen nearest-owned-fragment record."""
    return _component_from_bytes(data, lambda value: _fragment_from_mapping(value, "$"))


def parse_formalization_step(data: bytes) -> FormalizationStep:
    """Strictly parse one frozen caller-confirmed formalization step."""
    return _component_from_bytes(data, lambda value: _step_from_mapping(value, "$"))


def parse_unsupported_explanation(data: bytes) -> UnsupportedExplanation:
    """Strictly parse one canonical structured unsupported explanation."""
    return _component_from_bytes(data, _explanation_from_mapping)


def _serialize_component(value: object, expected_type: type[object], mapping: Any) -> bytes:
    if type(value) is not expected_type:
        raise UnsupportedExplanationValidationError(
            "type", "$", f"expected exact {expected_type.__name__}"
        )
    try:
        rendered = _canonical_bytes(mapping(value))
        return rendered
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc


def unsupported_target_bytes(target: UnsupportedTarget) -> bytes:
    """Serialize one validated unsupported target."""
    rendered = _serialize_component(target, UnsupportedTarget, _target_mapping)
    if parse_unsupported_target(rendered) != target:
        raise UnsupportedExplanationValidationError("result", "$", "target replay drift")
    return rendered


def owned_fragment_bytes(fragment: OwnedFragment) -> bytes:
    """Serialize one validated nearest-owned-fragment record."""
    rendered = _serialize_component(fragment, OwnedFragment, _fragment_mapping)
    if parse_owned_fragment(rendered) != fragment:
        raise UnsupportedExplanationValidationError("result", "$", "fragment replay drift")
    return rendered


def formalization_step_bytes(step: FormalizationStep) -> bytes:
    """Serialize one validated caller-confirmed formalization step."""
    rendered = _serialize_component(step, FormalizationStep, _step_mapping)
    if parse_formalization_step(rendered) != step:
        raise UnsupportedExplanationValidationError("result", "$", "step replay drift")
    return rendered


def unsupported_explanation_bytes(explanation: UnsupportedExplanation) -> bytes:
    """Serialize one validated structured explanation."""
    rendered = _serialize_component(
        explanation, UnsupportedExplanation, _explanation_mapping
    )
    if parse_unsupported_explanation(rendered) != explanation:
        raise UnsupportedExplanationValidationError(
            "result", "$", "explanation replay drift"
        )
    return rendered


def _candidate_from_mapping(
    value: object, path: str,
) -> UnsupportedExplanationCandidate:
    item = _require_object(value, path)
    _exact_fields(
        item,
        {
            "reading_id", "source_graph_sha256", "semantic_graph_sha256",
            "unsupported_semantic_sha256s", "targets", "explanations",
            "explanation_set_sha256", "mathematical_authority",
        },
        path,
    )
    reading_id = _require_id(item["reading_id"], f"{path}.reading_id")
    unsupported_index = _sha_tuple(
        item["unsupported_semantic_sha256s"],
        f"{path}.unsupported_semantic_sha256s",
        800_000,
    )
    target_values = _require_sequence(item["targets"], f"{path}.targets")
    explanation_values = _require_sequence(
        item["explanations"], f"{path}.explanations"
    )
    if len(target_values) > MAX_TARGETS or len(explanation_values) > MAX_TARGETS:
        _fail("budget", path, "target or explanation budget exceeded")
    if len(target_values) != len(explanation_values):
        _fail("inventory", path, "target and explanation cardinality drift")
    targets = tuple(
        _target_from_mapping(target, f"{path}.targets[{index}]")
        for index, target in enumerate(target_values)
    )
    explanations = tuple(
        _explanation_from_mapping(explanation, f"{path}.explanations[{index}]")
        for index, explanation in enumerate(explanation_values)
    )
    for ordinal, (target, explanation) in enumerate(zip(targets, explanations)):
        if (
            target.ordinal != ordinal
            or explanation.ordinal != ordinal
            or target.reading_id != reading_id
            or explanation.target_id != target.target_id
            or explanation.cause_sha256 != target.cause_sha256
            or explanation.construct_code != target.construct_code
            or explanation.construct_parameters != target.construct_parameters
        ):
            _fail("inventory", f"{path}.targets[{ordinal}]", "one-to-one alignment drift")
    if tuple(sorted({target.source_semantic_sha256 for target in targets})) != unsupported_index:
        _fail("inventory", path, "unsupported semantic index drift")
    if item["mathematical_authority"] is not False:
        _fail("result", f"{path}.mathematical_authority", "authority drift")
    set_sha = _require_sha(
        item["explanation_set_sha256"], f"{path}.explanation_set_sha256"
    )
    values: dict[str, object] = {
        "reading_id": reading_id,
        "source_graph_sha256": _require_sha(
            item["source_graph_sha256"], f"{path}.source_graph_sha256"
        ),
        "semantic_graph_sha256": _require_sha(
            item["semantic_graph_sha256"], f"{path}.semantic_graph_sha256"
        ),
        "unsupported_semantic_sha256s": unsupported_index,
        "targets": targets,
        "explanations": explanations,
        "explanation_set_sha256": set_sha,
        "mathematical_authority": False,
    }
    result = _make(UnsupportedExplanationCandidate, **values)
    expected_sha = _sha(_canonical_bytes(_candidate_mapping(result, include_digest=False)))
    if set_sha != expected_sha:
        _fail("identity", f"{path}.explanation_set_sha256", "explanation-set drift")
    return result


def _diagnostic_from_mapping(
    value: object, path: str,
) -> UnsupportedExplanationDiagnostic:
    item = _require_object(value, path)
    _exact_fields(item, {"code", "path", "message"}, path)
    code = item["code"]
    diagnostic_path = item["path"]
    message = item["message"]
    if (
        type(code) is not str
        or len(code) > 128
        or _CODE_RE.fullmatch(code) is None
        or type(diagnostic_path) is not str
        or not 1 <= len(diagnostic_path) <= 4096
        or type(message) is not str
        or not 1 <= len(message) <= 512
        or "\x00" in diagnostic_path
        or "\x00" in message
        or unicodedata.normalize("NFC", diagnostic_path) != diagnostic_path
        or unicodedata.normalize("NFC", message) != message
    ):
        _fail("schema", path, "diagnostic drift")
    return _make(
        UnsupportedExplanationDiagnostic,
        code=code,
        path=diagnostic_path,
        message=message,
    )


_RESULT_CONSTANTS: Final = {
    "schema": RESULT_SCHEMA,
    "contract_id": CONTRACT_ID,
    "contract_sha256": CONTRACT_SHA256,
    "canonical_normalization_contract_id": CANONICAL_NORMALIZATION_CONTRACT_ID,
    "canonical_normalization_contract_sha256": CANONICAL_NORMALIZATION_CONTRACT_SHA256,
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
    "catalogue_sha256": CATALOGUE_SHA256,
    "mathematical_authority": False,
}

_RESULT_FIELDS: Final = {
    *_RESULT_CONSTANTS,
    "status", "reason_code", "input_result_sha256", "normalization_result",
    "ambiguity_status", "selected_reading_id", "candidates", "diagnostics",
    "result_sha256",
}


def _validate_result_constants(value: Mapping[str, object], path: str = "$") -> None:
    for name, expected in _RESULT_CONSTANTS.items():
        actual = value.get(name)
        if type(actual) is not type(expected) or actual != expected:
            _fail("result", f"{path}.{name}", "frozen binding drift")


def _validate_result_shape(result: object) -> UnsupportedExplanationResult:
    if type(result) is not UnsupportedExplanationResult:
        raise UnsupportedExplanationValidationError(
            "type", "$", "expected exact UnsupportedExplanationResult"
        )
    assert isinstance(result, UnsupportedExplanationResult)
    try:
        _validate_result_constants(
            {
                "schema": result.schema,
                "contract_id": result.contract_id,
                "contract_sha256": result.contract_sha256,
                "canonical_normalization_contract_id": (
                    result.canonical_normalization_contract_id
                ),
                "canonical_normalization_contract_sha256": (
                    result.canonical_normalization_contract_sha256
                ),
                "proof_obligation_contract_id": result.proof_obligation_contract_id,
                "proof_obligation_contract_sha256": (
                    result.proof_obligation_contract_sha256
                ),
                "domain_assumption_contract_id": result.domain_assumption_contract_id,
                "domain_assumption_contract_sha256": (
                    result.domain_assumption_contract_sha256
                ),
                "reading_analysis_contract_id": result.reading_analysis_contract_id,
                "reading_analysis_contract_sha256": (
                    result.reading_analysis_contract_sha256
                ),
                "problem_intake_contract_id": result.problem_intake_contract_id,
                "problem_intake_contract_sha256": result.problem_intake_contract_sha256,
                "problem_ir_contract_id": result.problem_ir_contract_id,
                "problem_ir_contract_sha256": result.problem_ir_contract_sha256,
                "catalogue_sha256": result.catalogue_sha256,
                "mathematical_authority": result.mathematical_authority,
            }
        )
        if result.status not in {"explained", "invalid", "exhausted"}:
            _fail("result", "$.status", "state drift")
        if type(result.diagnostics) is not tuple or len(result.diagnostics) > MAX_DIAGNOSTICS:
            _fail("result", "$.diagnostics", "diagnostic collection drift")
        for index, diagnostic in enumerate(result.diagnostics):
            if type(diagnostic) is not UnsupportedExplanationDiagnostic:
                _fail("result", f"$.diagnostics[{index}]", "diagnostic type drift")
            reparsed = _diagnostic_from_mapping(
                {
                    "code": diagnostic.code,
                    "path": diagnostic.path,
                    "message": diagnostic.message,
                },
                f"$.diagnostics[{index}]",
            )
            if reparsed != diagnostic:
                _fail("result", f"$.diagnostics[{index}]", "diagnostic value drift")
        if result.status != "explained":
            if not (
                result.input_result_sha256 is None
                and result.normalization_result_bytes is None
                and result.ambiguity_status is None
                and result.selected_reading_id is None
                and result.candidates == ()
                and result.result_sha256 is None
                and result.diagnostics
                and result.reason_code == result.diagnostics[0].code
                and (result.status == "exhausted")
                == (result.reason_code == "BUDGET_EXHAUSTED")
            ):
                _fail("result", "$", "failed result combination drift")
            return result
        if (
            result.reason_code != "EXPLAINED"
            or result.diagnostics
            or type(result.normalization_result_bytes) is not bytes
            or type(result.input_result_sha256) is not str
            or _sha(result.normalization_result_bytes) != result.input_result_sha256
            or result.ambiguity_status not in {"unambiguous", "unresolved", "resolved"}
            or type(result.candidates) is not tuple
            or not result.candidates
            or _SHA_RE.fullmatch(result.result_sha256 or "") is None
        ):
            _fail("result", "$", "explained result combination drift")
        ids = tuple(item.reading_id for item in result.candidates)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            _fail("result", "$.candidates", "candidate order drift")
        return result
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc


def validate_unsupported_explanation_result(result: object) -> None:
    """Replay one closed result and reject every forged inner value."""
    result = _validate_result_shape(result)
    if result.status != "explained":
        return
    assert result.normalization_result_bytes is not None
    expected = explain_unsupported_constructs(result.normalization_result_bytes)
    if expected != result:
        raise UnsupportedExplanationValidationError(
            "result", "$", "unsupported explanation replay drift"
        )
    try:
        expected_sha = _sha(
            _canonical_bytes(_result_mapping(result, include_digest=False))
        )
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc
    if result.result_sha256 != expected_sha:
        raise UnsupportedExplanationValidationError(
            "identity", "$.result_sha256", "result digest drift"
        )


def unsupported_explanation_result_bytes(
    result: UnsupportedExplanationResult,
) -> bytes:
    """Serialize one closed replay-valid unsupported-explanation result."""
    validate_unsupported_explanation_result(result)
    try:
        return _canonical_bytes(_result_mapping(result))
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc


def unsupported_explanation_result_sha256(
    result: UnsupportedExplanationResult,
) -> str:
    """Return the stored identity over the result with a null self-reference."""
    validate_unsupported_explanation_result(result)
    if result.result_sha256 is None:
        raise UnsupportedExplanationValidationError(
            "result", "$.result_sha256", "failed results have no result identity"
        )
    return result.result_sha256


def parse_unsupported_explanation_result(
    data: bytes,
) -> UnsupportedExplanationResult:
    """Strictly parse canonical bytes and replay every explained artifact."""
    if type(data) is not bytes:
        raise UnsupportedExplanationValidationError(
            "type", "$", "result must be exact bytes"
        )
    if len(data) > MAX_OUTPUT_BYTES:
        raise UnsupportedExplanationValidationError(
            "budget", "$", "result byte budget exceeded"
        )
    try:
        value = _json_object(data)
        if _canonical_bytes(value) != data:
            _fail("canonical", "$", "result is noncanonical")
        _exact_fields(value, _RESULT_FIELDS, "$")
        _validate_result_constants(value)
        status = value.get("status")
        if status == "explained":
            normalization_value = _require_object(
                value.get("normalization_result"), "$.normalization_result"
            )
            normalization_bytes = _canonical_bytes(
                normalization_value, maximum=MAX_INPUT_BYTES
            )
            expected = explain_unsupported_constructs(normalization_bytes)
            if expected.status != "explained":
                _fail("upstream", "$.normalization_result", "embedded replay failed")
            if _canonical_bytes(_result_mapping(expected)) != data:
                _fail("result", "$", "explained result replay drift")
            return expected
        if status not in {"invalid", "exhausted"}:
            _fail("result", "$.status", "invalid result state")
        diagnostics_value = _require_sequence(value.get("diagnostics"), "$.diagnostics")
        if not 1 <= len(diagnostics_value) <= MAX_DIAGNOSTICS:
            _fail("result", "$.diagnostics", "failed diagnostic cardinality drift")
        diagnostics = tuple(
            _diagnostic_from_mapping(item, f"$.diagnostics[{index}]")
            for index, item in enumerate(diagnostics_value)
        )
        reason_code = value.get("reason_code")
        if type(reason_code) is not str or reason_code != diagnostics[0].code:
            _fail("result", "$.reason_code", "failed reason drift")
        if (status == "exhausted") != (reason_code == "BUDGET_EXHAUSTED"):
            _fail("result", "$.status", "failed exhaustion state drift")
        result = _new_result(
            status=status,
            reason_code=reason_code,
            diagnostics=diagnostics,
        )
        if _canonical_bytes(_result_mapping(result)) != data:
            _fail("result", "$", "failed result combination drift")
        return result
    except _ExplanationError as exc:
        raise UnsupportedExplanationValidationError(exc.kind, exc.path, exc.detail) from exc
