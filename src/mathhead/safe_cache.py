"""Pure content-addressed reuse decisions for governed audited runs."""

from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import re
from types import MappingProxyType
import unicodedata
from typing import Any, Final, NoReturn

from .capability_registry import parse_capability_route_request
from .deterministic_planner import parse_planning_request, parse_planning_result
from .isolated_worker import _parse_parent_budget
from .proof_search_portfolio import (
    make_proof_search_portfolio_request,
    parse_portfolio_checker_decision,
    parse_portfolio_execution_binding,
    parse_proof_search_portfolio_request,
    parse_proof_search_portfolio_result,
)
from .run_audit import RunAuditBundle, _fresh_inputs, replay_run_audit


CONTRACT_ID: Final = "MH-C-SAFE-CACHE-001"
CONTRACT_SHA256: Final = (
    "ec1c056023d8d966ed3a143a12e8c1726849d491800b175a3e807ca9a260cbb9"
)
REQUEST_SCHEMA: Final = "mathhead.safe-cache-request.v1"
ENTRY_SCHEMA: Final = "mathhead.safe-cache-entry.v1"
DECISION_SCHEMA: Final = "mathhead.safe-cache-decision-result.v1"
SCHEMA_SHA256S: Final = MappingProxyType({
    REQUEST_SCHEMA: "d99738d351f5d17292953cf45021bdbd61d65544a3f18f65ba7acaee64032cb8",
    ENTRY_SCHEMA: "36d770882c274962f6a168177d804e3f28b461bd9d2cef1a8c1907c505d9e093",
    DECISION_SCHEMA: "9888e1e8d7ecea9e5a21b6b60b0a26f3f573305484344d4827fec6a37bd69ed2",
})

MAX_INPUT_EACH: Final = 1_073_741_824
MAX_AGGREGATE_INPUT: Final = 5_368_709_120
MAX_OBJECTS: Final = 200_000
MAX_JSON_NODES: Final = 12_000_000
MAX_JSON_DEPTH: Final = 128
MAX_STRING: Final = 1_048_576
MAX_VALUE_BYTES: Final = 67_108_864
INTEGER_MAXIMUM: Final = 9_007_199_254_740_991

_DIGEST = re.compile(r"[0-9a-f]{64}")
_ID = re.compile(r"[a-z][a-z0-9_.-]{0,254}")
_SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?")

CONTRACT_BINDINGS: Final = MappingProxyType({
    "MH-C-AUDITED-RUN-004": "9079e68799fe032d982be87034ecb42cbc4b9a8486f370f01ace12a21d2ac4c4",
    "MH-C-CANONICAL-NORMALIZATION-001": "ad2a58afc455fed01310b125f3ae7e0597642e849fd10b86149c31a13b9249c8",
    "MH-C-CAPABILITY-REGISTRY-001": "52cc70945a4e83115c756e5b0a72724676f0e52a89e56c06a0fa8bd42c0e0413",
    "MH-C-CERTIFICATE-001": "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
    "MH-C-DETERMINISTIC-PLANNER-001": "72e3c39ea40c599cd709fff590a72bfd096450adbb80689ce934342c3aaaa124",
    "MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001": "609bc3a0773016f73d4bcee21d6aef034c74bb8edb36fddd9b6df1a4f4ba219a",
    "MH-C-ENGINE-RESULT-001": "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
    "MH-C-EVIDENCE-001": "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
    "MH-C-ISOLATED-WORKER-001": "c578d5a75f7a670f55e660147c335dc29709e71b82af8b37eb0033891b81a49b",
    "MH-C-PROBLEM-INTAKE-001": "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc",
    "MH-C-PROBLEM-SESSION-001": "822f72c9f41f583e4e0535e83b9dbb10954202acc820192e52eab48a5c2d9c0a",
    "MH-C-PROOF-OBLIGATION-DECOMPOSITION-001": "ea5d0664611b57da3074e20fce90623318ce04280d38ecce548025a91a7b19ff",
    "MH-C-PROOF-SEARCH-PORTFOLIO-001": "b59384b54d10665528540e470a3e5b6f7eae8bdcce198d6814a7459c073e0144",
    "MH-C-READING-ANALYSIS-002": "0a3e2b077c2593af780c11adca12854bc82336911d852d99f251f56602df3d70",
    "MH-C-RESOURCE-BUDGET-001": "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
    "MH-C-RUN-AUDIT-REPLAY-004": "04f484fc85486bcf8b17519128cd74336ff1834e76ab8d5e2713022d91c02c3b",
    "MH-C-RUN-AUDIT-STORE-005": "399bcb9d97217d249d9200697281a25052476f67f8435740fa32d6c7ed2c272b",
    "MH-C-THEORY-CONTEXT-001": "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
    "MH-C-THEORY-PLUGIN-001": "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
    "MH-C-TRUST-TRANSITION-001": "7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796",
    "MH-C-WORKFLOW-001": "99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca",
})

SCHEMA_BINDINGS: Final = MappingProxyType({
    "mathhead.canonical-context.v1": "e43588f34e29eb980efcc2f42600036803d7fb17dad8039aa18d7b1e6f6bf860",
    "mathhead.canonical-normal-form.v1": "d6dc45e60c9d494a70859631403ee7cf6e454f71d7b78dbffb528ae7550d5e9c",
    "mathhead.canonical-normalization-result.v1": "37ef5d35dcba90f32b53559719a08ebca12d8ffa9a0075ea99f6ac18efe18952",
    "mathhead.canonical-obligation.v1": "c6fade940f24fb23f4d16dcb324d3aff5bb35a923748d30b2f93fb302b436d58",
    "mathhead.canonical-occurrence-trace.v1": "01622e476a2fb3b72a9306cd656db6e7525604b1c6f4e680395e9b12cde74fec",
    "mathhead.capability-availability.v1": "aea788ecdee20497bb485c371b07a220707dabf1548bdc930e8b6c66877b52e1",
    "mathhead.capability-candidate.v1": "cc5c231bc11021e155b6390b2682ee63c4c6b2a3d30807f24a9c5d4ae31a75ed",
    "mathhead.capability-registry-entry.v1": "a20d3bcc4dd5bd5988eac60b6000ea8e92299f2aa13275f77a2306fb68dd8b3c",
    "mathhead.capability-registry.v1": "37e03e97fcd736b3c75e0c8c33f3d82c735dc57c4463ead8af9d331704761fbc",
    "mathhead.capability-route-request.v1": "cdf7dd11d0f1048c018c3472f7f0237ac3713db5edbbd1851761ab7388c4cc82",
    "mathhead.capability-route-result.v1": "11c23f4822be4e531e28bf66f47940fdeb389222305f04162c67ced66e2e49ec",
    "mathhead.certificate.v1": "cbc8f68469593e1d2b34588b49eaa16e37d597c863457945dd5b9ce5ae138760",
    "mathhead.domain-assumption-fact.v1": "4d32547bc93a5bb8ddee5424eae9ce4d39c99c0f9df689db317b41dfa5e0f023",
    "mathhead.domain-assumption-result.v1": "2f391074cfc3eae63933bcf91bb04688fddccf2b67eca6d5904edc635e9643ee",
    "mathhead.engine-result.v1": "4cd26ad69c6528a7553a429d06f224c79ae6b01b7d9cc0fa41ccb7c4d20cc948",
    "mathhead.evidence.v1": "4f1d0a4438812bdd7b204d0d0fe0098ff06cc274eb2e4ed7fa66a3f3a76b426f",
    "mathhead.isolated-worker-request.v1": "5f3f12dcf71bcceb7ca539df90c93887a4048366c5ea05be41b70b6532197a97",
    "mathhead.isolated-worker-result.v1": "b6172ad7c33908b65ecb74fc39340664b8a4ca8f55d1b69c1e23eacaf281f7df",
    "mathhead.normalized-domain-context.v1": "066657d0b81e3589c201e1351eeb0e763f0720087864869419f5cd3317fea67e",
    "mathhead.planning-evidence-expectation.v1": "126c85466c7c0bcda1bf7b10f4a9cdeeacfd8597e1e04b24a08f4c2f39ed34ae",
    "mathhead.planning-policy.v1": "fa0855768cb0445ab1f8ae67fe55a3851a500603a5757a9da099fe06a653b8f5",
    "mathhead.planning-prerequisite.v1": "54dd128e23ed57fcf3996fae61c221dd918dfee72c9bb0f160927bf62c5a0499",
    "mathhead.planning-request.v1": "2d8dff59cec10037f59506102c26f41eca21c0b963c968bcf2366b8dfcbff15a",
    "mathhead.planning-resource-request.v1": "8f5833b632b99ddf626a7d1fdef03986310636466b34d2cd0633501ca8d94c91",
    "mathhead.planning-result.v1": "f2e916f669f028eafca56551897e66371114a01f9aa2502e929d0aae90ff30be",
    "mathhead.planning-strategy.v1": "ca712e4c5f17b58d476537d4658c35c558841378cf7a084ac53cff026a15e1c8",
    "mathhead.planning-transition.v1": "2f63a40d420c823e5de9eb7fd4af4385dda801af296524ea0063a111a5dbb3f9",
    "mathhead.portfolio-attempt.v1": "fc12eb424c86d938282fed47ae814f03b9970b32642ccaee3c7226086abf0158",
    "mathhead.portfolio-checker-decision.v1": "88ab41ac83589290879d390bf4c711583b0366297b2435b73d0208a7ce09f15c",
    "mathhead.portfolio-execution-binding.v1": "ab39704148ac4de4489dc68b08b726a696a7794db4543b891ad311ec5b594e65",
    "mathhead.portfolio-inconclusive.v1": "4a2a98d58dfb4182b96b4bcafc01fd95292a1da9e7e8cb29eaa8d36cb784b8c1",
    "mathhead.problem-intake-result.v1": "0ea174a09391dd7f690bba9df7dfd08d8f1253032c472ca60d45eaf9f47101d3",
    "mathhead.problem-intake.v1": "e109d5a664849b8122eed13eeb87d73bc47e2d2989b3298e06a697989fb51c04",
    "mathhead.problem-readings-result.v2": "b05b16d280260ac7854477274852f0273e0a6cb011d740ae827ca172dad72894",
    "mathhead.problem-session-artifact-link.v1": "562faa38159bc98c4a1fb37c107afc20b933244b7f1cd3257b63c80f849a4133",
    "mathhead.problem-session-attempt.v1": "e14f6d0a9d1711bca56bfd195430eb081a58a5718c8c987bc7823df5beeeeb4b",
    "mathhead.problem-session-command.v1": "f395dfd35e14d88b5fd8a8b92613b1fcc355f8d72332483425774e2a8feceac1",
    "mathhead.problem-session-definition.v1": "d00d200ce97494b08ed7fc1b6b7d32f805f4a6c8ec4bd20d942fa426d586bb46",
    "mathhead.problem-session-event.v1": "983be63a2ee1096b8e9f550f0c3d3a1fe49fdaab64565927b6fd66e4b2247582",
    "mathhead.problem-session-invalidation.v1": "fd8dccac3d9437dafdba236d7d40619779661bd32eebbc204da8b08500b6700b",
    "mathhead.problem-session-lemma.v1": "79a446b77cb45f80eded2af13fda66daccc7445bf817161b2eaa6ab1debd6095",
    "mathhead.problem-session-obligation-state.v1": "150c0dfb2649fceb7057cd607e17bf8910ba13ffd97c7a1449995d30847c742e",
    "mathhead.problem-session-result.v1": "4d06b76fb9cca2e646c0a7b95a49d6926b83bf70b54246a40417d9667ba9cd53",
    "mathhead.problem-session-revision.v1": "02b89fd663f6506a6d993900635acb5ac0cd2c283b2f9d0994378e2d35882311",
    "mathhead.proof-obligation-graph.v1": "7244ad195f7a55732babda563b7b6d7d7b9b56f37d41874fe137f8b2e1349da3",
    "mathhead.proof-obligation-local-context.v1": "7ace8271f6ab2839b109208fd0b9686f9a6d3ac1c75c7df60e6febb37a7bd3e5",
    "mathhead.proof-obligation-result.v1": "449f6bb90edf609532410f6df133cb92e7cae925f0b57d1c527b7e5d453cb9ce",
    "mathhead.proof-obligation.v1": "55ff62bac3515763773645577c0ba163adbdda726a277a98945002ea82103db4",
    "mathhead.proof-search-portfolio-request.v1": "61d8d774612de377715e881806a3de8c57a03ee631c50c24400d322ff15a32bd",
    "mathhead.proof-search-portfolio-result.v1": "336d3b09259e119cd37fa3ffcf2405a6806827adc59edecab4c3dc29030fb99c",
    "mathhead.reading-projection.v2": "99ce60e50472e4c9d8026e9af361e4d7b11c776e577aa57de46794998fb26241",
    "mathhead.resource-budget.v1": "e735dee47394bf50c10ac571dfc8923fd1da851e258b1d9f42e1a66bb9d85e78",
    "mathhead.run-audit-event.v2": "eeb0f4ec975dc8417841f6677100f276d85cd356c3d0f376efa800e2ebbc0239",
    "mathhead.run-audit-manifest.v3": "784184e21eccd7043e188b776ec5154328860e99015fe87102cc776bd050eabd",
    "mathhead.run-audit-object.v2": "b81596770c10bac4e192155cd24aea721da2c8dc8b8d8b5f73a3b11570cdd92c",
    "mathhead.run-audit-replay-result.v4": "ae6f6f60f936a40926cd7942e00088a8f409836182d089b2f9c3cec5b007269d",
    "mathhead.run-audit-store-record.v2": "614083f9de220b6a780ff35e7ab6cd3c07f1c3371255112e433213ea556ade8f",
    "mathhead.run-audit-store-result.v5": "bf906f5c01fee05524b4c11cb80a526b5ca72214e8b417d44a3d4191077c11d4",
    "mathhead.run-audit-worker-observation.v3": "6abfae6c0f1be7811e8e8f3cc3e5de895274226e6834201da8018bc4df685a61",
    "mathhead.run-logical-report.v2": "d4a2a23426122d0ba64d3fc8a8135bde13c80794d221eaca9d6a49e7b134d2a2",
    "mathhead.theory-context.v1": "6a6e40070ba0a3209f5bfcfa0cc912d1ec08359a178611a40d61ffadda5819ec",
    "mathhead.theory-plugin.v1": "c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142",
    "mathhead.trust-transition-attempt.v1": "570ff6ed9905b9b3c39b45f51693e3f2b157d3f9ce93a12ce7a4cc3a8e4ca29a",
    "mathhead.trust-transition-audit-result.v1": "8b8b48110d7a2c429b18eec52427e9878bd7c8dde05fb8c9b29dac1a061b89bf",
    "mathhead.trust-transition-catalogue.v1": "205dfc544f130203ef092dbda050c763b93cbd92b9d2d4606fe95516843f2e1e",
    "mathhead.trust-transition-report.v1": "e043d8f6c3425f9806512ced28daaa3a66da080388c0e6a37e6f649eaf74d2f3",
})

IMPLEMENTATION_BINDINGS: Final = MappingProxyType({
    "capability_registry": "ac40c800f94b98875320e9d2e7a2f9164a7b5efb4d9b3c4064193f9af9dfd350",
    "deterministic_planner": "c1e269bc7dc9f347ab2ed23df016acd77084026bb0850218372fce3c0041ee45",
    "isolated_worker": "804a70023bbcb867a269e888eb5540a9c4af7b5987ab6d07613c2726c84d7048",
    "proof_search_portfolio": "f43b5a547449688f38617c975f2db54f196b8bbbe7a03d603660f9af293581bd",
    "run_audit": "fb1f78940b4881971adaf78c628de83627ce788402e36439d94b6e621636ffeb",
    "run_audit_store": "d1a44f1bdaecb2c43827499231d159afe23e247740d8e63bed2578921578a48f",
    "trust_transition": "74b54f54109cb8b837d368c92e777371aa6b4c8c218ef983ffb95586aadd9ea2",
})

CONFIGURATION_BINDINGS: Final = MappingProxyType({
    "capability_registry_report": "dd968cb215317e9c201e8a2776d1615dfe64f1902caa88b2cb4b539abf45a125",
    "deterministic_planner_report": "db38fdfe9592612656c8ff4ceed678039ed2d991b6c4552bc422ef1afc46ea44",
    "isolated_worker_report": "d390ff2dbbb26ba038dd9bed7257e408a75cd2953f2d6c0e7a39d63758b20be4",
    "proof_search_portfolio_report": "08c85ccdbfc1cebaabdec370b2985a306340b260c462e24f7186e1df6b958425",
    "run_audit_report": "dc354eb1196b996efa1e34e4837032bf9802038fdd85dbfd07b5820c0709c1b4",
    "run_audit_store_report": "f1a4cad5550832977f178a49e319accc73276216b494da97fa2107731427cc9a",
    "trust_transition_policy": "1a26d41f546f4a9334442fc7ef7d83eccffef56ed1f7a46d4209c748fb1c4b93",
})
TRUST_POLICY_SHA256: Final = CONFIGURATION_BINDINGS["trust_transition_policy"]


class SafeCacheValidationError(ValueError):
    """Strict safe-cache codec or relation failure."""

    def __init__(self, kind: str, path: str, detail: str) -> None:
        self.kind = kind
        self.path = path
        self.detail = detail
        super().__init__(f"{kind}:{path}: {detail}")


class _Invalid(ValueError):
    pass


class _Exhausted(ValueError):
    pass


class _DuplicateKey(ValueError):
    pass


_PUBLIC_FINAL = False


class _CacheValue:
    def __reduce__(self) -> NoReturn:
        raise TypeError(f"{type(self).__name__} cannot be pickled")

    def __init_subclass__(cls, **kwargs: object) -> None:
        if _PUBLIC_FINAL:
            raise TypeError("safe-cache value classes are final")
        super().__init_subclass__(**kwargs)


@dataclass(frozen=True, slots=True, init=False)
class SafeCacheEntry(_CacheValue):
    schema: str
    safe_cache_contract_sha256: str
    lookup_key_sha256: str
    audit_manifest_sha256: str
    logical_report_sha256: str
    portfolio_result_sha256: str
    selected_strategy_sha256: str
    selected_descriptor_sha256: str
    plugin_id: str
    plugin_version: str
    producer_component_id: str
    checker_component_id: str
    selected_evidence_sha256: str
    selected_certificate_sha256: str
    selected_checker_decision_sha256: str
    evidence_format_sha256: str
    certificate_format_sha256: str
    historical_authority_tier: str
    eligibility: str
    entry_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("safe-cache entries are decision-owned")


@dataclass(frozen=True, slots=True, init=False)
class SafeCacheDecision(_CacheValue):
    schema: str
    contract_id: str
    contract_sha256: str
    status: str
    reason_code: str
    lookup_key_sha256: str | None
    entry: SafeCacheEntry | None
    entry_sha256: str | None
    audit_manifest_sha256: str | None
    logical_report_sha256: str | None
    portfolio_result_sha256: str | None
    selected_evidence_sha256: str | None
    selected_certificate_sha256: str | None
    selected_checker_decision_sha256: str | None
    historical_authority_tier: str | None
    decision_sha256: str
    mathematical_authority: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("safe-cache decisions are boundary-owned")


_PUBLIC_FINAL = True


def _make(cls: type[Any], **values: object) -> Any:
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(values: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in values:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _walk(value: object, depth: int = 0, nodes: list[int] | None = None) -> None:
    counter = [0] if nodes is None else nodes
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
        raise _Exhausted("JSON work budget exceeded")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > INTEGER_MAXIMUM:
            raise _Invalid("integer outside canonical range")
        return
    if type(value) is str:
        if len(value) > MAX_STRING or "\x00" in value or unicodedata.normalize("NFC", value) != value:
            raise _Invalid("string outside canonical form")
        return
    if type(value) is list:
        for item in value:
            _walk(item, depth + 1, counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _Invalid("object key is not text")
            _walk(key, depth + 1, counter)
            _walk(item, depth + 1, counter)
        return
    raise _Invalid("unsupported JSON value")


def _canonical(value: object, maximum: int = MAX_VALUE_BYTES) -> bytes:
    _walk(value)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")
    if len(raw) > maximum:
        raise _Exhausted("canonical byte budget exceeded")
    return raw


def _parse(data: bytes, path: str = "$", maximum: int = MAX_VALUE_BYTES) -> dict[str, object]:
    if type(data) is not bytes:
        raise _Invalid(f"{path} must be exact bytes")
    if len(data) > maximum:
        raise _Exhausted(f"{path} byte budget exceeded")
    try:
        value = json.loads(data, object_pairs_hook=_pairs, parse_float=lambda _: (_ for _ in ()).throw(_Invalid("floats forbidden")))
    except _DuplicateKey as exc:
        raise _Invalid(f"{path} duplicate key {exc}") from exc
    except (UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise _Invalid(f"{path} invalid JSON") from exc
    _walk(value)
    if type(value) is not dict or _canonical(value, maximum) != data:
        raise _Invalid(f"{path} is not canonical object bytes")
    return value


def _digest(value: object, path: str) -> str:
    if type(value) is not str or _DIGEST.fullmatch(value) is None:
        raise _Invalid(f"{path} must be a full digest")
    return value


def _text(value: object, path: str, pattern: re.Pattern[str] = _ID) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise _Invalid(f"{path} is invalid text")
    return value


def _thaw(value: object) -> object:
    entries = getattr(value, "entries", None)
    if type(entries) is tuple:
        return {key: _thaw(item) for key, item in entries}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


def _format_sha(value: object | None) -> str | None:
    return None if value is None else _sha(_canonical(_thaw(value)))


def _entry_mapping(value: SafeCacheEntry, own_hash: bool = True) -> dict[str, object]:
    return {
        field.name: (None if field.name == "entry_sha256" and not own_hash else getattr(value, field.name))
        for field in fields(SafeCacheEntry)
    }


def _entry_from_mapping(value: object) -> SafeCacheEntry:
    expected = {field.name for field in fields(SafeCacheEntry)}
    if type(value) is not dict or set(value) != expected:
        raise _Invalid("entry fields differ")
    if value["schema"] != ENTRY_SCHEMA or value["safe_cache_contract_sha256"] != CONTRACT_SHA256:
        raise _Invalid("entry constants differ")
    digests = expected - {
        "schema", "plugin_id", "plugin_version", "producer_component_id",
        "checker_component_id", "historical_authority_tier", "eligibility",
        "mathematical_authority",
    }
    for name in digests:
        _digest(value[name], f"entry.{name}")
    _text(value["plugin_id"], "entry.plugin_id")
    _text(value["producer_component_id"], "entry.producer_component_id")
    _text(value["checker_component_id"], "entry.checker_component_id")
    _text(value["plugin_version"], "entry.plugin_version", _SEMVER)
    if value["historical_authority_tier"] not in {"checker_attestation", "external_proof_assistant"}:
        raise _Invalid("entry authority tier differs")
    if value["eligibility"] != "eligible_checked" or value["mathematical_authority"] is not False:
        raise _Invalid("entry eligibility or authority differs")
    result = _make(SafeCacheEntry, **value)
    if result.entry_sha256 != _sha(_canonical(_entry_mapping(result, False))):
        raise _Invalid("entry identity differs")
    return result


def safe_cache_entry_bytes(value: SafeCacheEntry) -> bytes:
    validate_safe_cache_entry(value)
    return _canonical(_entry_mapping(value))


def parse_safe_cache_entry(data: bytes) -> SafeCacheEntry:
    try:
        return _entry_from_mapping(_parse(data))
    except (_Invalid, _Exhausted) as exc:
        raise SafeCacheValidationError("entry", "$", str(exc)) from exc


def validate_safe_cache_entry(value: SafeCacheEntry) -> None:
    if type(value) is not SafeCacheEntry:
        raise SafeCacheValidationError("type", "$", "expected exact SafeCacheEntry")
    try:
        if _entry_from_mapping(_entry_mapping(value)) != value:
            raise _Invalid("entry reconstruction differs")
    except (_Invalid, _Exhausted, AttributeError) as exc:
        raise SafeCacheValidationError("entry", "$", str(exc)) from exc


def _decision_mapping(value: SafeCacheDecision, own_hash: bool = True) -> dict[str, object]:
    result = {
        field.name: (None if field.name == "decision_sha256" and not own_hash else getattr(value, field.name))
        for field in fields(SafeCacheDecision)
    }
    result["entry"] = None if value.entry is None else _entry_mapping(value.entry)
    return result


def _decision_shape(value: dict[str, object]) -> None:
    status = value["status"]
    reason = value["reason_code"]
    history = (
        "audit_manifest_sha256", "logical_report_sha256", "portfolio_result_sha256",
        "selected_evidence_sha256", "selected_certificate_sha256",
        "selected_checker_decision_sha256", "historical_authority_tier",
    )
    null_history = all(value[name] is None for name in history)
    no_entry = value["entry"] is None and value["entry_sha256"] is None
    if status == "hit":
        if reason != "CACHE_HIT" or value["lookup_key_sha256"] is None or no_entry or any(value[name] is None for name in history):
            raise _Invalid("hit shape differs")
    elif status == "miss":
        if reason != "CACHE_CANDIDATE_ABSENT" or value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("miss shape differs")
    elif status == "ineligible" and reason == "CACHE_OUTCOME_INELIGIBLE":
        if value["lookup_key_sha256"] is None or not no_entry or any(value[name] is None for name in history[:3]) or any(value[name] is not None for name in history[3:]):
            raise _Invalid("outcome-ineligible shape differs")
    elif status == "ineligible" and reason == "CACHE_AUTHORITY_INELIGIBLE":
        if value["lookup_key_sha256"] is None or not no_entry or any(value[name] is None for name in history[:6]) or value["historical_authority_tier"] is not None:
            raise _Invalid("authority-ineligible shape differs")
    elif status == "invalid" and reason == "CACHE_CURRENT_REQUEST_INVALID":
        if value["lookup_key_sha256"] is not None or not no_entry or not null_history:
            raise _Invalid("request-invalid shape differs")
    elif status == "invalid" and reason in {
        "CACHE_CONTEXT_MISMATCH", "CACHE_CONTRACT_MISMATCH",
        "CACHE_IMPLEMENTATION_MISMATCH", "CACHE_CONFIGURATION_MISMATCH",
        "CACHE_ARTIFACT_MISMATCH", "CACHE_BUDGET_MISMATCH",
        "CACHE_TRUST_POLICY_MISMATCH", "CACHE_REPLAY_INVALID",
    }:
        if value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("candidate-invalid shape differs")
    elif status == "exhausted" and reason == "CACHE_DECISION_BUDGET_EXHAUSTED":
        if value["lookup_key_sha256"] is not None or not no_entry or not null_history:
            raise _Invalid("decision-exhausted shape differs")
    elif status == "exhausted" and reason == "CACHE_REPLAY_EXHAUSTED":
        if value["lookup_key_sha256"] is None or not no_entry or not null_history:
            raise _Invalid("replay-exhausted shape differs")
    else:
        raise _Invalid("status/reason pair differs")


def _decision_from_mapping(value: object) -> SafeCacheDecision:
    expected = {field.name for field in fields(SafeCacheDecision)}
    if type(value) is not dict or set(value) != expected:
        raise _Invalid("decision fields differ")
    if value["schema"] != DECISION_SCHEMA or value["contract_id"] != CONTRACT_ID or value["contract_sha256"] != CONTRACT_SHA256 or value["mathematical_authority"] is not False:
        raise _Invalid("decision constants differ")
    for name in (
        "lookup_key_sha256", "entry_sha256", "audit_manifest_sha256",
        "logical_report_sha256", "portfolio_result_sha256", "selected_evidence_sha256",
        "selected_certificate_sha256", "selected_checker_decision_sha256",
        "historical_authority_tier",
    ):
        if value[name] is not None and name != "historical_authority_tier":
            _digest(value[name], f"decision.{name}")
    if value["historical_authority_tier"] not in {
        None, "checker_attestation", "external_proof_assistant"
    }:
        raise _Invalid("decision authority tier differs")
    _digest(value["decision_sha256"], "decision.decision_sha256")
    entry = None if value["entry"] is None else _entry_from_mapping(value["entry"])
    normalized = dict(value)
    normalized["entry"] = entry
    _decision_shape(normalized)
    if entry is not None:
        relations = {
            "lookup_key_sha256": entry.lookup_key_sha256,
            "entry_sha256": entry.entry_sha256,
            "audit_manifest_sha256": entry.audit_manifest_sha256,
            "logical_report_sha256": entry.logical_report_sha256,
            "portfolio_result_sha256": entry.portfolio_result_sha256,
            "selected_evidence_sha256": entry.selected_evidence_sha256,
            "selected_certificate_sha256": entry.selected_certificate_sha256,
            "selected_checker_decision_sha256": entry.selected_checker_decision_sha256,
            "historical_authority_tier": entry.historical_authority_tier,
        }
        if any(value[name] != expected for name, expected in relations.items()):
            raise _Invalid("decision entry relation differs")
    result = _make(SafeCacheDecision, **normalized)
    if result.decision_sha256 != _sha(_canonical(_decision_mapping(result, False))):
        raise _Invalid("decision identity differs")
    return result


def safe_cache_decision_bytes(value: SafeCacheDecision) -> bytes:
    validate_safe_cache_decision(value)
    return _canonical(_decision_mapping(value))


def parse_safe_cache_decision(data: bytes) -> SafeCacheDecision:
    try:
        return _decision_from_mapping(_parse(data))
    except (_Invalid, _Exhausted) as exc:
        raise SafeCacheValidationError("decision", "$", str(exc)) from exc


def validate_safe_cache_decision(value: SafeCacheDecision) -> None:
    if type(value) is not SafeCacheDecision:
        raise SafeCacheValidationError("type", "$", "expected exact SafeCacheDecision")
    try:
        if _decision_from_mapping(_decision_mapping(value)) != value:
            raise _Invalid("decision reconstruction differs")
    except (_Invalid, _Exhausted, AttributeError) as exc:
        raise SafeCacheValidationError("decision", "$", str(exc)) from exc


def _new_decision(
    status: str,
    reason: str,
    lookup_key: str | None,
    *,
    entry: SafeCacheEntry | None = None,
    manifest: str | None = None,
    report: str | None = None,
    portfolio: str | None = None,
    evidence: str | None = None,
    certificate: str | None = None,
    checker: str | None = None,
    tier: str | None = None,
) -> SafeCacheDecision:
    mapping: dict[str, object] = {
        "schema": DECISION_SCHEMA, "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256, "status": status,
        "reason_code": reason, "lookup_key_sha256": lookup_key,
        "entry": None if entry is None else _entry_mapping(entry),
        "entry_sha256": None if entry is None else entry.entry_sha256,
        "audit_manifest_sha256": manifest, "logical_report_sha256": report,
        "portfolio_result_sha256": portfolio, "selected_evidence_sha256": evidence,
        "selected_certificate_sha256": certificate,
        "selected_checker_decision_sha256": checker,
        "historical_authority_tier": tier, "decision_sha256": None,
        "mathematical_authority": False,
    }
    mapping["decision_sha256"] = _sha(_canonical(mapping))
    return _decision_from_mapping(mapping)


def _current_request(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
) -> dict[str, object]:
    singles = (planning_request, route_result, portfolio_request, planning_result, parent_budget)
    if any(type(raw) is not bytes or len(raw) > MAX_INPUT_EACH for raw in singles):
        raise _Invalid("current byte inputs differ")
    if any(type(values) is not tuple for values in (descriptors, bindings, artifacts)):
        raise _Invalid("current inventories must be exact tuples")
    all_inventory = (*descriptors, *bindings, *artifacts)
    if any(type(raw) is not bytes or len(raw) > MAX_INPUT_EACH for raw in all_inventory):
        raise _Invalid("current inventory bytes differ")
    if len(descriptors) > 10_000 or len(bindings) > 100_000 or len(artifacts) > MAX_OBJECTS:
        raise _Exhausted("current inventory count exceeded")
    if sum(map(len, singles + all_inventory)) > MAX_AGGREGATE_INPUT:
        raise _Exhausted("aggregate input bytes exceeded")
    _fresh_inputs(planning_request, route_result, portfolio_request, planning_result, parent_budget, descriptors, bindings, artifacts)
    planning = parse_planning_request(planning_request)
    route = parse_capability_route_request(planning.route_request)
    plan = parse_planning_result(planning_result)
    request = parse_proof_search_portfolio_request(portfolio_request)
    parent = _parse_parent_budget(parent_budget)
    if tuple(_sha(raw) for raw in bindings) != request.binding_sha256s or tuple(sorted(_sha(raw) for raw in descriptors)) != request.descriptor_sha256s:
        raise _Invalid("portfolio descriptor or binding closure differs")
    parsed_bindings = tuple(parse_portfolio_execution_binding(raw) for raw in bindings)
    by_digest: dict[str, bytes] = {}
    for raw in artifacts:
        digest = _sha(raw)
        if digest in by_digest:
            raise _Invalid("duplicate input artifact bytes")
        by_digest[digest] = raw
    pairs: list[tuple[str, bytes]] = []
    artifact_map: dict[str, object] = {}
    for binding in request.artifact_bindings:
        raw = by_digest.get(binding.sha256)
        if raw is None or len(raw) != binding.bytes or binding.role in artifact_map:
            raise _Invalid("artifact role closure differs")
        pairs.append((binding.role, raw))
        artifact_map[binding.role] = {"sha256": binding.sha256, "bytes": binding.bytes}
    if len(pairs) != len(artifacts):
        raise _Invalid("surplus input artifacts")
    rebuilt = make_proof_search_portfolio_request(
        planning_result=planning_result, parent_budget=parent_budget,
        descriptors=descriptors, bindings=bindings, artifacts=tuple(pairs),
    )
    if rebuilt != portfolio_request or len(plan.strategies) != len(bindings):
        raise _Invalid("portfolio request reconstruction differs")
    for strategy, binding in zip(plan.strategies, parsed_bindings):
        if (
            binding.plan_order != strategy.plan_order
            or binding.strategy_sha256 != strategy.strategy_sha256
            or binding.descriptor_sha256 != strategy.descriptor_sha256
            or binding.producer_component_id != strategy.producer_component_id
            or binding.checker_component_id != strategy.checker_component_id
        ):
            raise _Invalid("strategy execution binding differs")
    limits = parent.value.get("limits")
    if type(limits) is not dict:
        raise _Invalid("parent limits absent")
    descriptor_values = {_sha(raw): _parse(raw, "descriptor") for raw in descriptors}
    strategy_formats: dict[str, tuple[str | None, str | None]] = {}
    for item in plan.strategies:
        descriptor = descriptor_values.get(item.descriptor_sha256)
        capabilities = None if descriptor is None else descriptor.get("capabilities")
        if type(capabilities) is not list:
            raise _Invalid("descriptor capabilities absent")
        matches = [
            capability for capability in capabilities
            if type(capability) is dict and capability.get("capability_id") == item.capability_id
        ]
        if len(matches) != 1:
            raise _Invalid("strategy capability descriptor differs")
        capability = matches[0]
        evidence_formats = capability.get("evidence_formats")
        certificate_formats = capability.get("certificate_formats")
        if type(evidence_formats) is not list or len(evidence_formats) != 1:
            raise _Invalid("evidence format selection is not exact")
        if type(certificate_formats) is not list or len(certificate_formats) != 1:
            raise _Invalid("certificate format selection is not exact")
        evidence_format = _format_sha(item.evidence_expectation.evidence_format)
        certificate_format = _format_sha(item.evidence_expectation.certificate_format)
        strategy_formats[item.strategy_sha256] = (
            evidence_format or _sha(_canonical(evidence_formats[0])),
            certificate_format or _sha(_canonical(certificate_formats[0])),
        )
    entry_formats = strategy_formats.get(str(plan.entry_strategy_sha256))
    if entry_formats is None:
        raise _Invalid("entry strategy formats absent")
    value: dict[str, object] = {
        "schema": REQUEST_SCHEMA,
        "safe_cache_contract_sha256": CONTRACT_SHA256,
        "dependency_contracts": dict(CONTRACT_BINDINGS),
        "dependency_schemas": dict(SCHEMA_BINDINGS),
        "implementation_bindings": dict(IMPLEMENTATION_BINDINGS),
        "configuration_bindings": dict(CONFIGURATION_BINDINGS),
        "planning_request_sha256": _sha(planning_request),
        "route_result_sha256": _sha(route_result),
        "planning_result_sha256": _sha(planning_result),
        "portfolio_request_sha256": _sha(portfolio_request),
        "initial_parent_budget_sha256": _sha(parent_budget),
        "session_id": route.session_id,
        "session_head_sha256": route.session_head_sha256,
        "event_sha256s": list(route.event_sha256s),
        "session_artifact_sha256s": list(route.session_artifact_sha256s),
        "reading_id": route.reading_id,
        "session_context_sha256": route.session_context_sha256,
        "normalization_result_sha256": route.normalization_result_sha256,
        "normalized_input_sha256": route.normalization_result_sha256,
        "obligation_record_id": route.session_obligation_record_id,
        "obligation_artifact_sha256": route.obligation_artifact_sha256,
        "obligation_semantic_sha256": route.obligation_semantic_sha256,
        "local_context_semantic_sha256": route.local_context_semantic_sha256,
        "capability_kind": route.capability_kind, "operation": route.operation,
        "availability_sha256": route.availability.availability_sha256,
        "platform": route.availability.platform,
        "python_version": route.availability.python_version,
        "replay_mode": route.replay_mode,
        "evidence_format_sha256": _format_sha(route.evidence_format) or entry_formats[0],
        "certificate_format_sha256": _format_sha(route.certificate_format) or entry_formats[1],
        "descriptor_sha256s": list(request.descriptor_sha256s),
        "strategy_sha256s": [item.strategy_sha256 for item in plan.strategies],
        "execution_binding_sha256s": list(request.binding_sha256s),
        "input_artifacts": artifact_map,
        "initial_parent_limits_sha256": _sha(_canonical(limits)),
        "child_resource_request_sha256s": [
            item.resource_request.resource_request_sha256 for item in plan.strategies
        ],
        "trust_policy_sha256": TRUST_POLICY_SHA256,
        "lookup_key_sha256": None,
        "mathematical_authority": False,
    }
    value["lookup_key_sha256"] = _sha(_canonical(value))
    value["_strategy_formats"] = strategy_formats
    return value


def _relation_reason(manifest: dict[str, object], request: dict[str, object]) -> str | None:
    if manifest.get("initial_parent_budget_sha256") != request["initial_parent_budget_sha256"]:
        return "CACHE_BUDGET_MISMATCH"
    pairs = {
        "planning_request_sha256": "CACHE_CONTEXT_MISMATCH",
        "route_result_sha256": "CACHE_CONTEXT_MISMATCH",
        "planning_result_sha256": "CACHE_CONTEXT_MISMATCH",
        "portfolio_request_sha256": "CACHE_ARTIFACT_MISMATCH",
        "normalized_input_sha256": "CACHE_CONTEXT_MISMATCH",
    }
    for field, reason in pairs.items():
        if manifest.get(field) != request[field]:
            return reason
    return None


def _record(records: list[object], role: str) -> dict[str, object]:
    matches = [item for item in records if type(item) is dict and item.get("role") == role]
    if len(matches) != 1:
        raise _Invalid(f"exact {role} record absent")
    return matches[0]


def _candidate_view(candidate: RunAuditBundle, request: dict[str, object]) -> tuple[dict[str, object], dict[str, object], dict[str, bytes]]:
    if (
        type(candidate) is not RunAuditBundle
        or type(candidate.manifest) is not bytes
        or type(candidate.objects) is not tuple
        or any(type(raw) is not bytes for raw in candidate.objects)
        or type(candidate.logical_report) is not bytes
        or candidate.manifest_sha256 != _sha(candidate.manifest)
        or candidate.logical_report_sha256 != _sha(candidate.logical_report)
        or candidate.mathematical_authority is not False
    ):
        raise _Invalid("candidate outer fields differ")
    replay = replay_run_audit(candidate.manifest, candidate.objects)
    if replay.status == "exhausted":
        raise _Exhausted("candidate replay budget exhausted")
    if replay.status != "complete" or replay.logical_report_sha256 != candidate.logical_report_sha256:
        raise _Invalid("candidate replay invalid")
    manifest = _parse(candidate.manifest, "manifest", MAX_VALUE_BYTES)
    report = _parse(candidate.logical_report, "logical_report", MAX_VALUE_BYTES)
    objects = {_sha(raw): raw for raw in candidate.objects}
    if len(objects) != len(candidate.objects) or objects.get(candidate.logical_report_sha256) != candidate.logical_report:
        raise _Invalid("candidate object closure differs")
    reason = _relation_reason(manifest, request)
    if reason is not None:
        raise _Invalid(reason)
    return manifest, report, objects


def _make_entry(
    request: dict[str, object], candidate: RunAuditBundle,
    manifest: dict[str, object], report: dict[str, object], objects: dict[str, bytes],
) -> SafeCacheEntry:
    records = manifest.get("objects")
    if type(records) is not list:
        raise _Invalid("manifest records absent")
    portfolio_record = _record(records, "portfolio_result")
    final_record = next(
        (item for item in records if type(item) is dict and item.get("role_id") == "final_parent_budget"),
        None,
    )
    if type(final_record) is not dict:
        raise _Invalid("final parent record absent")
    evidence_sha = report.get("selected_evidence_sha256")
    certificate_sha = report.get("selected_certificate_sha256")
    checker_identity = report.get("selected_checker_decision_sha256")
    strategy_sha = report.get("selected_strategy_sha256")
    if any(type(item) is not str for item in (evidence_sha, certificate_sha, checker_identity, strategy_sha)):
        raise _Invalid("selected chain absent")
    evidence = objects.get(str(evidence_sha))
    certificate = objects.get(str(certificate_sha))
    checker_records = [
        item for item in records
        if type(item) is dict and item.get("role") == "checker_decision"
    ]
    checker_raw = None
    checker = None
    for record in checker_records:
        raw = objects.get(str(record.get("sha256")))
        if raw is None:
            continue
        parsed = parse_portfolio_checker_decision(raw, certificate)
        if parsed.decision_sha256 == checker_identity:
            checker_raw, checker = raw, parsed
            break
    final_parent = objects.get(str(final_record.get("sha256")))
    portfolio_raw = objects.get(str(portfolio_record.get("sha256")))
    if None in {evidence, certificate, checker_raw, final_parent, portfolio_raw} or checker is None:
        raise _Invalid("selected object chain absent")
    portfolio = parse_proof_search_portfolio_result(
        portfolio_raw, final_parent, evidence, certificate
    )
    if (
        portfolio.status != "succeeded"
        or portfolio.mathematical_verdict not in {"proved", "refuted"}
        or portfolio.authority_tier not in {"checker_attestation", "external_proof_assistant"}
        or portfolio.selected_strategy_sha256 != strategy_sha
        or portfolio.selected_evidence_sha256 != evidence_sha
        or portfolio.selected_certificate_sha256 != certificate_sha
        or portfolio.selected_checker_decision_sha256 != checker_identity
        or checker.agreement is not True
    ):
        raise _Invalid("selected checked outcome differs")
    plugins = report.get("plugins")
    if type(plugins) is not list:
        raise _Invalid("plugin inventory absent")
    selected = [item for item in plugins if type(item) is dict and item.get("strategy_sha256") == strategy_sha]
    if len(selected) != 1:
        raise _Invalid("selected plugin differs")
    plugin = selected[0]
    strategy_formats = request.get("_strategy_formats")
    formats = strategy_formats.get(str(strategy_sha)) if type(strategy_formats) is dict else None
    if type(formats) is not tuple or len(formats) != 2:
        raise _Invalid("selected format inventory absent")
    evidence_format, certificate_format = formats
    if type(evidence_format) is not str or type(certificate_format) is not str:
        raise _Invalid("selected formats are not cacheable")
    mapping: dict[str, object] = {
        "schema": ENTRY_SCHEMA, "safe_cache_contract_sha256": CONTRACT_SHA256,
        "lookup_key_sha256": request["lookup_key_sha256"],
        "audit_manifest_sha256": candidate.manifest_sha256,
        "logical_report_sha256": candidate.logical_report_sha256,
        "portfolio_result_sha256": portfolio_record["sha256"],
        "selected_strategy_sha256": strategy_sha,
        "selected_descriptor_sha256": plugin.get("descriptor_sha256"),
        "plugin_id": plugin.get("plugin_id"), "plugin_version": plugin.get("plugin_version"),
        "producer_component_id": plugin.get("producer_component_id"),
        "checker_component_id": plugin.get("checker_component_id"),
        "selected_evidence_sha256": evidence_sha,
        "selected_certificate_sha256": certificate_sha,
        "selected_checker_decision_sha256": checker_identity,
        "evidence_format_sha256": evidence_format,
        "certificate_format_sha256": certificate_format,
        "historical_authority_tier": portfolio.authority_tier,
        "eligibility": "eligible_checked", "entry_sha256": None,
        "mathematical_authority": False,
    }
    mapping["entry_sha256"] = _sha(_canonical(mapping))
    return _entry_from_mapping(mapping)


def decide_safe_cache(
    planning_request: bytes,
    route_result: bytes,
    portfolio_request: bytes,
    planning_result: bytes,
    parent_budget: bytes,
    descriptors: tuple[bytes, ...],
    bindings: tuple[bytes, ...],
    artifacts: tuple[bytes, ...],
    candidate: RunAuditBundle | None,
) -> SafeCacheDecision:
    """Return a pure zero-authority reuse decision for one explicit candidate."""
    try:
        current = _current_request(
            planning_request, route_result, portfolio_request, planning_result,
            parent_budget, descriptors, bindings, artifacts,
        )
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except _Exhausted:
        return _new_decision("exhausted", "CACHE_DECISION_BUDGET_EXHAUSTED", None)
    except Exception:
        return _new_decision("invalid", "CACHE_CURRENT_REQUEST_INVALID", None)
    lookup = str(current["lookup_key_sha256"])
    if candidate is None:
        return _new_decision("miss", "CACHE_CANDIDATE_ABSENT", lookup)
    try:
        manifest, report, objects = _candidate_view(candidate, current)
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except _Exhausted:
        return _new_decision("exhausted", "CACHE_REPLAY_EXHAUSTED", lookup)
    except _Invalid as exc:
        reason = str(exc)
        if reason not in {
            "CACHE_CONTEXT_MISMATCH", "CACHE_CONTRACT_MISMATCH",
            "CACHE_IMPLEMENTATION_MISMATCH", "CACHE_CONFIGURATION_MISMATCH",
            "CACHE_ARTIFACT_MISMATCH", "CACHE_BUDGET_MISMATCH",
            "CACHE_TRUST_POLICY_MISMATCH",
        }:
            reason = "CACHE_REPLAY_INVALID"
        return _new_decision("invalid", reason, lookup)
    portfolio_sha = manifest.get("portfolio_result_sha256")
    if (
        report.get("status") != "succeeded"
        or report.get("mathematical_verdict") not in {"proved", "refuted"}
    ):
        return _new_decision(
            "ineligible", "CACHE_OUTCOME_INELIGIBLE", lookup,
            manifest=candidate.manifest_sha256, report=candidate.logical_report_sha256,
            portfolio=str(portfolio_sha),
        )
    try:
        entry = _make_entry(current, candidate, manifest, report, objects)
    except (MemoryError, KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        evidence = report.get("selected_evidence_sha256")
        certificate = report.get("selected_certificate_sha256")
        checker = report.get("selected_checker_decision_sha256")
        if all(type(item) is str for item in (evidence, certificate, checker)):
            return _new_decision(
                "ineligible", "CACHE_AUTHORITY_INELIGIBLE", lookup,
                manifest=candidate.manifest_sha256, report=candidate.logical_report_sha256,
                portfolio=str(portfolio_sha), evidence=str(evidence),
                certificate=str(certificate), checker=str(checker),
            )
        return _new_decision("invalid", "CACHE_REPLAY_INVALID", lookup)
    return _new_decision(
        "hit", "CACHE_HIT", lookup, entry=entry,
        manifest=entry.audit_manifest_sha256, report=entry.logical_report_sha256,
        portfolio=entry.portfolio_result_sha256,
        evidence=entry.selected_evidence_sha256,
        certificate=entry.selected_certificate_sha256,
        checker=entry.selected_checker_decision_sha256,
        tier=entry.historical_authority_tier,
    )


__all__ = [
    "CONTRACT_ID", "CONTRACT_SHA256", "SCHEMA_SHA256S",
    "SafeCacheEntry", "SafeCacheDecision", "SafeCacheValidationError",
    "decide_safe_cache", "safe_cache_entry_bytes", "parse_safe_cache_entry",
    "validate_safe_cache_entry", "safe_cache_decision_bytes",
    "parse_safe_cache_decision", "validate_safe_cache_decision",
]
