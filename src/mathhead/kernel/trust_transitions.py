"""Pure, non-authoritative audit of MathHead trust-tier transitions.

This module is policy machinery, not a mathematical checker.  An ``allowed``
result says that exact supplied bytes satisfy the frozen transition catalogue;
it never establishes the truth of the subject or recreates another boundary's
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Final, Mapping
import unicodedata


CONTRACT_ID: Final = "MH-C-TRUST-TRANSITION-001"
CONTRACT_SHA256: Final = \
    "7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796"
CATALOGUE_SHA256: Final = \
    "1a26d41f546f4a9334442fc7ef7d83eccffef56ed1f7a46d4209c748fb1c4b93"
ATTEMPT_SCHEMA: Final = "mathhead.trust-transition-attempt.v1"
RESULT_SCHEMA: Final = "mathhead.trust-transition-audit-result.v1"
CATALOGUE_SCHEMA: Final = "mathhead.trust-transition-catalogue.v1"

TIERS: Final = (
    "none",
    "producer_report",
    "solver_verdict",
    "checker_attestation",
    "external_proof_assistant",
)
OPERATIONS: Final = ("downgrade", "issue", "preserve")
STATUSES: Final = (
    "completed",
    "disagreement",
    "error",
    "exhausted",
    "invalid",
    "unsupported",
    "verified",
)
ROLES: Final = (
    "canonicalizer",
    "checker",
    "effect_boundary",
    "orchestrator",
    "parser",
    "producer",
    "proof_assistant",
    "transport",
)
DECISIONS: Final = ("allowed", "downgraded", "rejected")
REASONS: Final = (
    "ALLOWED",
    "ARTIFACT_MISMATCH",
    "BUDGET_INCOMPLETE",
    "CATALOGUE_INVALID",
    "DOWNGRADED",
    "EVIDENCE_INCOMPLETE",
    "FRESHNESS_REQUIRED",
    "INDEPENDENCE_REQUIRED",
    "ISSUER_FORBIDDEN",
    "MALFORMED_ATTEMPT",
    "STATUS_FORBIDDEN",
    "TIER_CLAIM_MISMATCH",
    "TRANSITION_FORBIDDEN",
    "TRANSITION_UNKNOWN",
)
EFFECT_SURFACES: Final = (
    "arithmetic.approximate",
    "process.dynamic-import",
    "process.external-nauty",
    "process.subprocess",
    "process.workers",
    "runtime.clock",
    "runtime.nondeterminism",
    "solver.sympy",
    "solver.z3",
    "transport.cli",
    "transport.mcp",
)

MAX_ATTEMPT_BYTES: Final = 4_194_304
MAX_CATALOGUE_BYTES: Final = 16_777_216
MAX_ARTIFACT_BYTES: Final = 67_108_864
MAX_AGGREGATE_BYTES: Final = 268_435_456
MAX_ARTIFACTS: Final = 64
MAX_JSON_NODES: Final = 500_000
MAX_JSON_NESTING: Final = 64
MAX_STRING_CODEPOINTS: Final = 1_048_576
MAX_INTEGER: Final = 9_007_199_254_740_991
MAX_TRANSITIONS: Final = 32
MAX_MUTATIONS: Final = 2_048
MAX_DIAGNOSTICS: Final = 32

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_ROLE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SCHEMA_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_TRANSITION_ID = re.compile(r"^transition\.[a-z][a-z0-9_.-]{0,95}$")
_CONTRACT_ID = re.compile(r"^MH-C-[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}$")
_MEDIA_TYPE = re.compile(
    r"^[a-z0-9][a-z0-9.+-]{0,31}/[a-z0-9][a-z0-9.+-]{0,63}$"
)
_DIAGNOSTIC = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_MUTATION_CLASSES: Final = (
    "artifact",
    "authority",
    "budget",
    "canonical",
    "effect",
    "freshness",
    "identity",
    "independence",
    "provenance",
    "semantic",
    "status",
    "structure",
)
_EFFECT_ROLES: Final = ("effect_boundary", "producer", "transport")
_EMPTY_SHA256: Final = hashlib.sha256(b"").hexdigest()
_RESULT_TOKEN: Final = object()


class TrustTransitionValidationError(ValueError):
    """A strict codec or catalogue invariant failed."""

    __slots__ = ("kind",)

    def __init__(self, kind: str, detail: str) -> None:
        super().__init__(detail)
        self.kind = kind


@dataclass(frozen=True, slots=True, init=False)
class TransitionAuditResult:
    """Closed policy result carrying explicitly no mathematical authority."""

    attempt_sha256: str
    bindings_satisfied: bool
    decision: str
    diagnostics: tuple[str, ...]
    edge_allowed: bool
    effective_tier: str
    freshness_satisfied: bool
    independence_satisfied: bool
    issuer_allowed: bool
    mathematical_authority: bool
    reason: str
    schema: str
    status_satisfied: bool
    transition_id: str

    def __init__(
        self,
        *,
        attempt_sha256: str = "",
        bindings_satisfied: bool = False,
        decision: str = "rejected",
        diagnostics: tuple[str, ...] = (),
        edge_allowed: bool = False,
        effective_tier: str = "none",
        freshness_satisfied: bool = False,
        independence_satisfied: bool = False,
        issuer_allowed: bool = False,
        mathematical_authority: bool = False,
        reason: str = "MALFORMED_ATTEMPT",
        schema: str = RESULT_SCHEMA,
        status_satisfied: bool = False,
        transition_id: str = "transition.invalid",
        _token: object | None = None,
    ) -> None:
        if _token is not _RESULT_TOKEN:
            raise PermissionError("TransitionAuditResult is constructed by the auditor")
        values = locals()
        for field in self.__slots__:
            object.__setattr__(self, field, values[field])

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("TransitionAuditResult is final")

    def __reduce__(self) -> object:
        raise TypeError("TransitionAuditResult cannot be pickled")

    def __copy__(self) -> TransitionAuditResult:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> TransitionAuditResult:
        return self


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustTransitionValidationError("duplicate", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _canonical_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TrustTransitionValidationError("canonical", str(exc)) from exc
    return (rendered + "\n").encode("utf-8")


def _walk_json(value: object, *, depth: int = 0, counter: list[int] | None = None) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise TrustTransitionValidationError("budget", "JSON node budget exceeded")
    if depth > MAX_JSON_NESTING:
        raise TrustTransitionValidationError("budget", "JSON nesting budget exceeded")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > MAX_INTEGER:
            raise TrustTransitionValidationError("budget", "integer exceeds portable range")
        return
    if type(value) is str:
        if len(value) > MAX_STRING_CODEPOINTS:
            raise TrustTransitionValidationError("budget", "string budget exceeded")
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            raise TrustTransitionValidationError("canonical", "string is not canonical NFC")
        return
    if type(value) is list:
        if len(value) > MAX_MUTATIONS:
            raise TrustTransitionValidationError("budget", "array budget exceeded")
        for item in value:
            _walk_json(item, depth=depth + 1, counter=counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TrustTransitionValidationError("schema", "JSON key must be a string")
            _walk_json(key, depth=depth + 1, counter=counter)
            _walk_json(item, depth=depth + 1, counter=counter)
        return
    raise TrustTransitionValidationError("schema", "floats and non-JSON values are forbidden")


def _load_canonical(data: object, *, label: str, maximum: int) -> dict[str, Any]:
    if type(data) is not bytes:
        raise TrustTransitionValidationError("type", f"{label} must be exact bytes")
    if not data or len(data) > maximum:
        raise TrustTransitionValidationError("budget", f"{label} byte budget violated")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs)
    except TrustTransitionValidationError:
        raise
    except UnicodeError as exc:
        raise TrustTransitionValidationError("encoding", f"{label} is not UTF-8") from exc
    except RecursionError as exc:
        raise TrustTransitionValidationError("budget", f"{label} nesting budget exceeded") from exc
    except ValueError as exc:
        raise TrustTransitionValidationError("json", f"invalid {label} JSON") from exc
    if type(value) is not dict:
        raise TrustTransitionValidationError("schema", f"{label} root must be an object")
    _walk_json(value)
    if _canonical_bytes(value) != data:
        raise TrustTransitionValidationError("canonical", f"{label} bytes are noncanonical")
    return value


def _exact_fields(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise TrustTransitionValidationError("schema", f"{label} fields differ")
    return value


def _string(value: object, pattern: re.Pattern[str], label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise TrustTransitionValidationError("schema", f"invalid {label}")
    return value


def _boolean(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise TrustTransitionValidationError("schema", f"invalid {label}")
    return value


def _enum(value: object, allowed: tuple[str, ...], label: str) -> str:
    if type(value) is not str or value not in allowed:
        raise TrustTransitionValidationError("schema", f"invalid {label}")
    return value


def _bounded_int(value: object, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or value < minimum or value > maximum:
        raise TrustTransitionValidationError("schema", f"invalid {label}")
    return value


def _sorted_unique_strings(
    value: object,
    *,
    minimum: int,
    maximum: int,
    pattern: re.Pattern[str],
    label: str,
) -> tuple[str, ...]:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise TrustTransitionValidationError("schema", f"invalid {label}")
    items = tuple(_string(item, pattern, label) for item in value)
    if tuple(sorted(items)) != items or len(set(items)) != len(items):
        raise TrustTransitionValidationError("canonical", f"{label} must sort and deduplicate")
    return items


def _validate_artifact(value: object, label: str) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {"bytes", "media_type", "role", "schema", "sha256"},
        label,
    )
    _bounded_int(result["bytes"], 1, MAX_ARTIFACT_BYTES, f"{label}.bytes")
    _string(result["media_type"], _MEDIA_TYPE, f"{label}.media_type")
    _string(result["role"], _ROLE, f"{label}.role")
    _string(result["schema"], _SCHEMA_ID, f"{label}.schema")
    _string(result["sha256"], _DIGEST, f"{label}.sha256")
    return result


def _validate_component(value: object) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {
            "component_id",
            "configuration_sha256",
            "contract_id",
            "contract_sha256",
            "entry_point",
            "fresh",
            "implementation_sha256",
            "independent",
            "role",
        },
        "issuer",
    )
    _string(result["component_id"], _ID, "issuer.component_id")
    _string(result["configuration_sha256"], _DIGEST, "issuer.configuration_sha256")
    _string(result["contract_id"], _CONTRACT_ID, "issuer.contract_id")
    _string(result["contract_sha256"], _DIGEST, "issuer.contract_sha256")
    _string(result["entry_point"], _ID, "issuer.entry_point")
    _boolean(result["fresh"], "issuer.fresh")
    _string(result["implementation_sha256"], _DIGEST, "issuer.implementation_sha256")
    _boolean(result["independent"], "issuer.independent")
    _enum(result["role"], ROLES, "issuer.role")
    return result


def trust_transition_issuer_key(issuer: Mapping[str, object]) -> str:
    """Return the catalogue key binding every exact issuer policy field."""

    if type(issuer) is not dict:
        raise TrustTransitionValidationError("type", "issuer must be an exact dict")
    checked = _validate_component(issuer)
    return f"issuer.{_sha(_canonical_bytes(checked))}"


def _validate_contract_ref(value: object, label: str) -> dict[str, Any]:
    result = _exact_fields(value, {"contract_id", "sha256"}, label)
    _string(result["contract_id"], _CONTRACT_ID, f"{label}.contract_id")
    _string(result["sha256"], _DIGEST, f"{label}.sha256")
    return result


def _validate_attempt(value: dict[str, Any]) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {
            "bindings",
            "budget_complete",
            "claimed_authority",
            "evidence_complete",
            "issuer",
            "operation",
            "schema",
            "source_tier",
            "status",
            "subject",
            "target_tier",
            "transition_id",
        },
        "attempt",
    )
    if result["schema"] != ATTEMPT_SCHEMA:
        raise TrustTransitionValidationError("schema", "attempt schema differs")
    _string(result["transition_id"], _TRANSITION_ID, "attempt.transition_id")
    _enum(result["source_tier"], TIERS, "attempt.source_tier")
    _enum(result["target_tier"], TIERS, "attempt.target_tier")
    _enum(result["claimed_authority"], TIERS, "attempt.claimed_authority")
    _enum(result["operation"], OPERATIONS, "attempt.operation")
    _enum(result["status"], STATUSES, "attempt.status")
    _boolean(result["evidence_complete"], "attempt.evidence_complete")
    _boolean(result["budget_complete"], "attempt.budget_complete")
    _validate_component(result["issuer"])
    subject = _validate_artifact(result["subject"], "attempt.subject")
    bindings = result["bindings"]
    if type(bindings) is not list or not 1 <= len(bindings) <= MAX_ARTIFACTS:
        raise TrustTransitionValidationError("schema", "attempt bindings count differs")
    checked = tuple(_validate_artifact(item, "attempt.binding") for item in bindings)
    roles = tuple(item["role"] for item in checked)
    if tuple(sorted(roles)) != roles or len(set(roles)) != len(roles):
        raise TrustTransitionValidationError("canonical", "binding roles must sort and deduplicate")
    matching_subjects = [item for item in checked if item["role"] == subject["role"]]
    if matching_subjects != [subject]:
        raise TrustTransitionValidationError("identity", "subject is not one exact binding")
    return result


def _validate_transition(value: object) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {
            "allowed_issuers",
            "allowed_statuses",
            "mutation_ids",
            "on_failure_tier",
            "operation",
            "positive_control_ids",
            "required_binding_roles",
            "required_contracts",
            "requires_fresh",
            "requires_independent",
            "source_tier",
            "target_tier",
            "transition_id",
        },
        "transition",
    )
    _string(result["transition_id"], _TRANSITION_ID, "transition.transition_id")
    _enum(result["source_tier"], TIERS, "transition.source_tier")
    _enum(result["target_tier"], TIERS, "transition.target_tier")
    _enum(result["on_failure_tier"], TIERS, "transition.on_failure_tier")
    _enum(result["operation"], OPERATIONS, "transition.operation")
    if TIERS.index(result["on_failure_tier"]) > TIERS.index(result["source_tier"]):
        raise TrustTransitionValidationError("catalogue", "failure tier exceeds source")
    _boolean(result["requires_fresh"], "transition.requires_fresh")
    _boolean(result["requires_independent"], "transition.requires_independent")
    _sorted_unique_strings(
        result["allowed_issuers"],
        minimum=1,
        maximum=16,
        pattern=_ID,
        label="transition.allowed_issuers",
    )
    statuses = _sorted_unique_strings(
        result["allowed_statuses"],
        minimum=1,
        maximum=len(STATUSES),
        pattern=_ID,
        label="transition.allowed_statuses",
    )
    if any(status not in STATUSES for status in statuses):
        raise TrustTransitionValidationError("catalogue", "transition status is unknown")
    _sorted_unique_strings(
        result["required_binding_roles"],
        minimum=1,
        maximum=MAX_ARTIFACTS,
        pattern=_ROLE,
        label="transition.required_binding_roles",
    )
    _sorted_unique_strings(
        result["positive_control_ids"],
        minimum=1,
        maximum=32,
        pattern=_ID,
        label="transition.positive_control_ids",
    )
    _sorted_unique_strings(
        result["mutation_ids"],
        minimum=1,
        maximum=256,
        pattern=_ID,
        label="transition.mutation_ids",
    )
    contracts = result["required_contracts"]
    if type(contracts) is not list or not 1 <= len(contracts) <= 16:
        raise TrustTransitionValidationError("catalogue", "required contracts count differs")
    checked_contracts = tuple(
        _validate_contract_ref(item, "transition.required_contract") for item in contracts
    )
    contract_ids = tuple(item["contract_id"] for item in checked_contracts)
    if tuple(sorted(contract_ids)) != contract_ids or len(set(contract_ids)) != len(contract_ids):
        raise TrustTransitionValidationError("canonical", "required contracts must sort")
    return result


def _validate_mutation(value: object) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {
            "description",
            "expected_decision",
            "expected_reason",
            "expected_tier",
            "mutation_class",
            "mutation_id",
            "transition_ids",
        },
        "mutation",
    )
    description = result["description"]
    if type(description) is not str or not 1 <= len(description) <= 512:
        raise TrustTransitionValidationError("catalogue", "mutation description differs")
    _string(result["mutation_id"], _ID, "mutation.mutation_id")
    _enum(result["mutation_class"], _MUTATION_CLASSES, "mutation.mutation_class")
    _enum(result["expected_decision"], ("downgraded", "rejected"), "mutation decision")
    _string(result["expected_reason"], _DIAGNOSTIC, "mutation.expected_reason")
    _enum(result["expected_tier"], TIERS, "mutation.expected_tier")
    _sorted_unique_strings(
        result["transition_ids"],
        minimum=1,
        maximum=MAX_TRANSITIONS,
        pattern=_TRANSITION_ID,
        label="mutation.transition_ids",
    )
    return result


def _validate_effect(value: object) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {"authority_issuer", "maximum_tier", "mutation_ids", "role", "surface_id"},
        "effect",
    )
    if result["authority_issuer"] is not False:
        raise TrustTransitionValidationError("authority", "effect is an authority issuer")
    _enum(result["maximum_tier"], TIERS, "effect.maximum_tier")
    _enum(result["role"], _EFFECT_ROLES, "effect.role")
    _string(result["surface_id"], _ID, "effect.surface_id")
    _sorted_unique_strings(
        result["mutation_ids"],
        minimum=1,
        maximum=64,
        pattern=_ID,
        label="effect.mutation_ids",
    )
    return result


def _validate_catalogue(value: dict[str, Any]) -> dict[str, Any]:
    result = _exact_fields(
        value,
        {"contract", "effects", "mutations", "schema", "tiers", "transitions"},
        "catalogue",
    )
    if result["schema"] != CATALOGUE_SCHEMA or result["tiers"] != list(TIERS):
        raise TrustTransitionValidationError("catalogue", "catalogue schema or tiers differ")
    contract = _validate_contract_ref(result["contract"], "catalogue.contract")
    if contract != {"contract_id": CONTRACT_ID, "sha256": CONTRACT_SHA256}:
        raise TrustTransitionValidationError("contract", "catalogue contract differs")

    transitions = result["transitions"]
    if type(transitions) is not list or not 6 <= len(transitions) <= MAX_TRANSITIONS:
        raise TrustTransitionValidationError("catalogue", "transition count differs")
    checked_transitions = tuple(_validate_transition(item) for item in transitions)
    transition_ids = tuple(item["transition_id"] for item in checked_transitions)
    if tuple(sorted(transition_ids)) != transition_ids or len(set(transition_ids)) != len(
        transition_ids
    ):
        raise TrustTransitionValidationError("canonical", "transitions must sort and deduplicate")

    mutations = result["mutations"]
    if type(mutations) is not list or not 24 <= len(mutations) <= MAX_MUTATIONS:
        raise TrustTransitionValidationError("catalogue", "mutation count differs")
    checked_mutations = tuple(_validate_mutation(item) for item in mutations)
    mutation_ids = tuple(item["mutation_id"] for item in checked_mutations)
    if tuple(sorted(mutation_ids)) != mutation_ids or len(set(mutation_ids)) != len(mutation_ids):
        raise TrustTransitionValidationError("canonical", "mutations must sort and deduplicate")

    effects = result["effects"]
    if type(effects) is not list or not 11 <= len(effects) <= 64:
        raise TrustTransitionValidationError("catalogue", "effect count differs")
    checked_effects = tuple(_validate_effect(item) for item in effects)
    surface_ids = tuple(item["surface_id"] for item in checked_effects)
    if tuple(sorted(surface_ids)) != surface_ids or len(set(surface_ids)) != len(surface_ids):
        raise TrustTransitionValidationError("canonical", "effects must sort and deduplicate")
    if tuple(surface for surface in EFFECT_SURFACES if surface not in surface_ids):
        raise TrustTransitionValidationError("catalogue", "required effect surface is absent")

    transition_set = set(transition_ids)
    mutation_set = set(mutation_ids)
    for mutation in checked_mutations:
        if not set(mutation["transition_ids"]) <= transition_set:
            raise TrustTransitionValidationError("catalogue", "mutation transition is dangling")
    for transition in checked_transitions:
        if not set(transition["mutation_ids"]) <= mutation_set:
            raise TrustTransitionValidationError("catalogue", "transition mutation is dangling")
        for mutation_id in transition["mutation_ids"]:
            mutation = checked_mutations[mutation_ids.index(mutation_id)]
            if transition["transition_id"] not in mutation["transition_ids"]:
                raise TrustTransitionValidationError("catalogue", "mutation cross-link differs")
    transitions_by_id = {
        transition["transition_id"]: transition for transition in checked_transitions
    }
    for mutation in checked_mutations:
        for transition_id in mutation["transition_ids"]:
            if mutation["mutation_id"] not in transitions_by_id[transition_id]["mutation_ids"]:
                raise TrustTransitionValidationError("catalogue", "reverse mutation cross-link differs")
    for effect in checked_effects:
        if not set(effect["mutation_ids"]) <= mutation_set:
            raise TrustTransitionValidationError("catalogue", "effect mutation is dangling")
    return result


def validate_trust_transition_catalogue(catalogue: bytes) -> None:
    """Strictly validate canonical catalogue bytes and all cross-links."""

    _validate_catalogue(
        _load_canonical(catalogue, label="catalogue", maximum=MAX_CATALOGUE_BYTES)
    )


def _result(
    *,
    attempt_sha256: str,
    bindings_satisfied: bool,
    decision: str,
    diagnostics: tuple[str, ...],
    edge_allowed: bool,
    effective_tier: str,
    freshness_satisfied: bool,
    independence_satisfied: bool,
    issuer_allowed: bool,
    reason: str,
    status_satisfied: bool,
    transition_id: str,
) -> TransitionAuditResult:
    value = TransitionAuditResult(
        attempt_sha256=attempt_sha256,
        bindings_satisfied=bindings_satisfied,
        decision=decision,
        diagnostics=diagnostics,
        edge_allowed=edge_allowed,
        effective_tier=effective_tier,
        freshness_satisfied=freshness_satisfied,
        independence_satisfied=independence_satisfied,
        issuer_allowed=issuer_allowed,
        mathematical_authority=False,
        reason=reason,
        schema=RESULT_SCHEMA,
        status_satisfied=status_satisfied,
        transition_id=transition_id,
        _token=_RESULT_TOKEN,
    )
    _validate_result(value)
    return value


def _invalid_result(reason: str, attempt: object, transition_id: str) -> TransitionAuditResult:
    attempt_sha = (
        _sha(attempt)
        if type(attempt) is bytes and 0 < len(attempt) <= MAX_ATTEMPT_BYTES
        else _EMPTY_SHA256
    )
    safe_transition = transition_id if _TRANSITION_ID.fullmatch(transition_id) else \
        "transition.invalid"
    return _result(
        attempt_sha256=attempt_sha,
        bindings_satisfied=False,
        decision="rejected",
        diagnostics=(reason,),
        edge_allowed=False,
        effective_tier="none",
        freshness_satisfied=False,
        independence_satisfied=False,
        issuer_allowed=False,
        reason=reason,
        status_satisfied=False,
        transition_id=safe_transition,
    )


def _artifact_inventory(
    attempt: dict[str, Any], artifacts: object
) -> tuple[bool, tuple[dict[str, Any], ...]]:
    if type(artifacts) is not tuple or not 1 <= len(artifacts) <= MAX_ARTIFACTS:
        return False, ()
    if any(type(item) is not bytes or not item or len(item) > MAX_ARTIFACT_BYTES for item in artifacts):
        return False, ()
    if sum(len(item) for item in artifacts) > MAX_AGGREGATE_BYTES:
        return False, ()
    supplied = tuple((_sha(item), len(item)) for item in artifacts)
    if len(set(supplied)) != len(supplied):
        return False, ()
    records = tuple(attempt["bindings"])
    expected = tuple((item["sha256"], item["bytes"]) for item in records)
    return sorted(supplied) == sorted(expected), records


def _contracts_satisfied(
    transition: dict[str, Any], issuer: dict[str, Any], bindings: tuple[dict[str, Any], ...]
) -> bool:
    required = tuple(transition["required_contracts"])
    if not any(
        item["contract_id"] == issuer["contract_id"]
        and item["sha256"] == issuer["contract_sha256"]
        for item in required
    ):
        return False
    available_hashes = {item["sha256"] for item in bindings}
    return all(item["sha256"] in available_hashes for item in required)


def _identity_bindings_satisfied(
    issuer: dict[str, Any], bindings: tuple[dict[str, Any], ...]
) -> bool:
    by_role = {item["role"]: item for item in bindings}
    implementation = by_role.get("issuer_implementation")
    configuration = by_role.get("issuer_configuration")
    return (
        implementation is not None
        and configuration is not None
        and implementation["sha256"] == issuer["implementation_sha256"]
        and configuration["sha256"] == issuer["configuration_sha256"]
    )


def audit_trust_transition(
    attempt: bytes,
    artifacts: tuple[bytes, ...],
    catalogue: bytes,
) -> TransitionAuditResult:
    """Audit exact transition policy without granting mathematical authority."""

    try:
        attempt_value = _validate_attempt(
            _load_canonical(attempt, label="attempt", maximum=MAX_ATTEMPT_BYTES)
        )
    except TrustTransitionValidationError:
        return _invalid_result("MALFORMED_ATTEMPT", attempt, "transition.invalid")
    transition_id = attempt_value["transition_id"]
    if (
        type(catalogue) is not bytes
        or not 0 < len(catalogue) <= MAX_CATALOGUE_BYTES
        or _sha(catalogue) != CATALOGUE_SHA256
    ):
        return _invalid_result("CATALOGUE_INVALID", attempt, transition_id)
    try:
        catalogue_value = _validate_catalogue(
            _load_canonical(catalogue, label="catalogue", maximum=MAX_CATALOGUE_BYTES)
        )
    except TrustTransitionValidationError:
        return _invalid_result("CATALOGUE_INVALID", attempt, transition_id)

    transitions = {
        item["transition_id"]: item for item in catalogue_value["transitions"]
    }
    transition = transitions.get(transition_id)
    if transition is None:
        return _invalid_result("TRANSITION_UNKNOWN", attempt, transition_id)

    issuer = attempt_value["issuer"]
    inventory_ok, bindings = _artifact_inventory(attempt_value, artifacts)
    roles = tuple(item["role"] for item in bindings)
    required_roles = tuple(transition["required_binding_roles"])
    bindings_satisfied = (
        inventory_ok
        and roles == required_roles
        and _contracts_satisfied(transition, issuer, bindings)
        and _identity_bindings_satisfied(issuer, bindings)
    )
    edge_allowed = (
        attempt_value["source_tier"] == transition["source_tier"]
        and attempt_value["target_tier"] == transition["target_tier"]
        and attempt_value["operation"] == transition["operation"]
    )
    issuer_allowed = trust_transition_issuer_key(issuer) in transition["allowed_issuers"]
    status_satisfied = attempt_value["status"] in transition["allowed_statuses"]
    freshness_satisfied = not transition["requires_fresh"] or issuer["fresh"] is True
    independence_satisfied = not transition["requires_independent"] or issuer[
        "independent"
    ] is True
    claim_satisfied = attempt_value["claimed_authority"] == transition["target_tier"]
    evidence_satisfied = attempt_value["evidence_complete"] is True
    budget_satisfied = attempt_value["budget_complete"] is True

    failures: list[str] = []
    for passed, diagnostic in (
        (edge_allowed, "TRANSITION_FORBIDDEN"),
        (issuer_allowed, "ISSUER_FORBIDDEN"),
        (claim_satisfied, "TIER_CLAIM_MISMATCH"),
        (bindings_satisfied, "ARTIFACT_MISMATCH"),
        (evidence_satisfied, "EVIDENCE_INCOMPLETE"),
        (budget_satisfied, "BUDGET_INCOMPLETE"),
        (freshness_satisfied, "FRESHNESS_REQUIRED"),
        (independence_satisfied, "INDEPENDENCE_REQUIRED"),
        (status_satisfied, "STATUS_FORBIDDEN"),
    ):
        if not passed:
            failures.append(diagnostic)

    if not failures:
        return _result(
            attempt_sha256=_sha(attempt),
            bindings_satisfied=True,
            decision="allowed",
            diagnostics=(),
            edge_allowed=True,
            effective_tier=transition["target_tier"],
            freshness_satisfied=True,
            independence_satisfied=True,
            issuer_allowed=True,
            reason="ALLOWED",
            status_satisfied=True,
            transition_id=transition_id,
        )
    return _result(
        attempt_sha256=_sha(attempt),
        bindings_satisfied=bindings_satisfied,
        decision="downgraded",
        diagnostics=tuple(failures[:MAX_DIAGNOSTICS]),
        edge_allowed=edge_allowed,
        effective_tier=transition["on_failure_tier"],
        freshness_satisfied=freshness_satisfied,
        independence_satisfied=independence_satisfied,
        issuer_allowed=issuer_allowed,
        reason=failures[0],
        status_satisfied=status_satisfied,
        transition_id=transition_id,
    )


def _result_value(result: TransitionAuditResult) -> dict[str, object]:
    return {
        "attempt_sha256": result.attempt_sha256,
        "bindings_satisfied": result.bindings_satisfied,
        "decision": result.decision,
        "diagnostics": list(result.diagnostics),
        "edge_allowed": result.edge_allowed,
        "effective_tier": result.effective_tier,
        "freshness_satisfied": result.freshness_satisfied,
        "independence_satisfied": result.independence_satisfied,
        "issuer_allowed": result.issuer_allowed,
        "mathematical_authority": result.mathematical_authority,
        "reason": result.reason,
        "schema": result.schema,
        "status_satisfied": result.status_satisfied,
        "transition_id": result.transition_id,
    }


def _validate_result(result: object) -> TransitionAuditResult:
    if type(result) is not TransitionAuditResult:
        raise TrustTransitionValidationError("type", "result type differs")
    _string(result.attempt_sha256, _DIGEST, "result.attempt_sha256")
    for name in (
        "bindings_satisfied",
        "edge_allowed",
        "freshness_satisfied",
        "independence_satisfied",
        "issuer_allowed",
        "mathematical_authority",
        "status_satisfied",
    ):
        _boolean(getattr(result, name), f"result.{name}")
    if result.mathematical_authority is not False:
        raise TrustTransitionValidationError("authority", "audit result gained authority")
    _enum(result.decision, DECISIONS, "result.decision")
    _enum(result.effective_tier, TIERS, "result.effective_tier")
    _enum(result.reason, REASONS, "result.reason")
    if result.schema != RESULT_SCHEMA:
        raise TrustTransitionValidationError("schema", "result schema differs")
    _string(result.transition_id, _TRANSITION_ID, "result.transition_id")
    if type(result.diagnostics) is not tuple or len(result.diagnostics) > MAX_DIAGNOSTICS:
        raise TrustTransitionValidationError("result", "result diagnostics differ")
    if any(type(item) is not str or _DIAGNOSTIC.fullmatch(item) is None for item in result.diagnostics):
        raise TrustTransitionValidationError("result", "result diagnostic is invalid")
    if len(set(result.diagnostics)) != len(result.diagnostics):
        raise TrustTransitionValidationError("result", "result diagnostics duplicate")
    if result.decision == "allowed":
        if result.reason != "ALLOWED" or result.diagnostics or not all(
            (
                result.bindings_satisfied,
                result.edge_allowed,
                result.freshness_satisfied,
                result.independence_satisfied,
                result.issuer_allowed,
                result.status_satisfied,
            )
        ):
            raise TrustTransitionValidationError("result", "allowed result is incomplete")
    elif result.reason == "ALLOWED" or not result.diagnostics:
        raise TrustTransitionValidationError("result", "closed result lacks failure evidence")
    return result


def transition_audit_result_to_bytes(result: TransitionAuditResult) -> bytes:
    """Serialize one validated, non-authoritative result canonically."""

    return _canonical_bytes(_result_value(_validate_result(result)))


def parse_transition_audit_result(data: bytes) -> TransitionAuditResult:
    """Parse historical policy evidence without granting mathematical authority."""

    value = _load_canonical(data, label="result", maximum=MAX_ATTEMPT_BYTES)
    _exact_fields(
        value,
        {
            "attempt_sha256",
            "bindings_satisfied",
            "decision",
            "diagnostics",
            "edge_allowed",
            "effective_tier",
            "freshness_satisfied",
            "independence_satisfied",
            "issuer_allowed",
            "mathematical_authority",
            "reason",
            "schema",
            "status_satisfied",
            "transition_id",
        },
        "result",
    )
    diagnostics = value["diagnostics"]
    if type(diagnostics) is not list:
        raise TrustTransitionValidationError("schema", "result diagnostics must be an array")
    result = TransitionAuditResult(
        attempt_sha256=value["attempt_sha256"],
        bindings_satisfied=value["bindings_satisfied"],
        decision=value["decision"],
        diagnostics=tuple(diagnostics),
        edge_allowed=value["edge_allowed"],
        effective_tier=value["effective_tier"],
        freshness_satisfied=value["freshness_satisfied"],
        independence_satisfied=value["independence_satisfied"],
        issuer_allowed=value["issuer_allowed"],
        mathematical_authority=value["mathematical_authority"],
        reason=value["reason"],
        schema=value["schema"],
        status_satisfied=value["status_satisfied"],
        transition_id=value["transition_id"],
        _token=_RESULT_TOKEN,
    )
    _validate_result(result)
    if transition_audit_result_to_bytes(result) != data:
        raise TrustTransitionValidationError("canonical", "result bytes differ")
    return result


def trust_transition_attempt_to_bytes(value: Mapping[str, object]) -> bytes:
    """Canonicalize one prospective attempt after complete structural validation."""

    if type(value) is not dict:
        raise TrustTransitionValidationError("type", "attempt must be an exact dict")
    _validate_attempt(value)
    return _canonical_bytes(value)
