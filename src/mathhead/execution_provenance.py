"""Closed compiled identities for audited execution provenance."""

from __future__ import annotations

import hashlib
import json
from types import MappingProxyType
from typing import Final, cast


PROVENANCE_SCHEMA: Final = "mathhead.run-execution-provenance.v1"
PROVENANCE_SCHEMA_SHA256: Final = (
    "4f3bcb68f4c83a49f7be230d04346b7ab4bbe6cfff7fccc6d419ea9d233f643e"
)

EXECUTION_CONTRACT_BINDINGS: Final = MappingProxyType({
    "MH-C-AUDITED-RUN-005": "42e6cfcb704bc1b40b8c0a9143c4bfdaa34b0228a85621d9464e28c8481a39a7",
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
    "MH-C-RUN-AUDIT-REPLAY-005": "cc1170556ddba8bf4232fff5dc14f1bdb95d7d558540d5066fb4379b9c1c2cde",
    "MH-C-THEORY-CONTEXT-001": "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
    "MH-C-THEORY-PLUGIN-001": "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
    "MH-C-TRUST-TRANSITION-001": "7b32e2db85c8aa8c98b9a9c5404d562a909f9ae2435310a79dad04b6c6ed4796",
    "MH-C-WORKFLOW-001": "99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca",
})

EXECUTION_SCHEMA_BINDINGS: Final = MappingProxyType({
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
    "mathhead.run-audit-manifest.v4": "b777dfc8778470071b363cd0592384441887827a112c4e9605cf2e523d97a96f",
    "mathhead.run-audit-object.v3": "71a727409a664064b86c22f01356e77967a03e2fc4ebc330c03b4fcefdf6551e",
    "mathhead.run-audit-replay-result.v5": "50bf3daa5ed566dc6911dae1af345486880e2e37eb63ba29d6784f9d13ba1058",
    "mathhead.run-audit-worker-observation.v3": "6abfae6c0f1be7811e8e8f3cc3e5de895274226e6834201da8018bc4df685a61",
    "mathhead.run-execution-provenance.v1": "4f3bcb68f4c83a49f7be230d04346b7ab4bbe6cfff7fccc6d419ea9d233f643e",
    "mathhead.run-logical-report.v3": "f0ca700129d72a132878bd5deba92af7c86eab3c34c9592409afb80822e5fee8",
    "mathhead.theory-context.v1": "6a6e40070ba0a3209f5bfcfa0cc912d1ec08359a178611a40d61ffadda5819ec",
    "mathhead.theory-plugin.v1": "c3d234f725e2c3f0e6fa02507be83190bde71f8ddae6f5a08cd6395065d77142",
    "mathhead.trust-transition-attempt.v1": "570ff6ed9905b9b3c39b45f51693e3f2b157d3f9ce93a12ce7a4cc3a8e4ca29a",
    "mathhead.trust-transition-audit-result.v1": "8b8b48110d7a2c429b18eec52427e9878bd7c8dde05fb8c9b29dac1a061b89bf",
    "mathhead.trust-transition-catalogue.v1": "205dfc544f130203ef092dbda050c763b93cbd92b9d2d4606fe95516843f2e1e",
    "mathhead.trust-transition-report.v1": "e043d8f6c3425f9806512ced28daaa3a66da080388c0e6a37e6f649eaf74d2f3",
})

EXECUTION_IMPLEMENTATION_BINDINGS: Final = MappingProxyType({
    "capability_registry": "ac40c800f94b98875320e9d2e7a2f9164a7b5efb4d9b3c4064193f9af9dfd350",
    "deterministic_planner": "c1e269bc7dc9f347ab2ed23df016acd77084026bb0850218372fce3c0041ee45",
    "isolated_worker": "804a70023bbcb867a269e888eb5540a9c4af7b5987ab6d07613c2726c84d7048",
    "proof_search_portfolio": "f43b5a547449688f38617c975f2db54f196b8bbbe7a03d603660f9af293581bd",
    "trust_transition": "74b54f54109cb8b837d368c92e777371aa6b4c8c218ef983ffb95586aadd9ea2",
})

EXECUTION_CONFIGURATION_BINDINGS: Final = MappingProxyType({
    "capability_registry_report": "dd968cb215317e9c201e8a2776d1615dfe64f1902caa88b2cb4b539abf45a125",
    "deterministic_planner_report": "db38fdfe9592612656c8ff4ceed678039ed2d991b6c4552bc422ef1afc46ea44",
    "isolated_worker_report": "d390ff2dbbb26ba038dd9bed7257e408a75cd2953f2d6c0e7a39d63758b20be4",
    "proof_search_portfolio_report": "08c85ccdbfc1cebaabdec370b2985a306340b260c462e24f7186e1df6b958425",
    "trust_transition_policy": "1a26d41f546f4a9334442fc7ef7d83eccffef56ed1f7a46d4209c748fb1c4b93",
})

TRUST_POLICY_SHA256: Final = EXECUTION_CONFIGURATION_BINDINGS[
    "trust_transition_policy"
]

_PROVENANCE_KEYS: Final = {
    "schema",
    "dependency_contracts",
    "dependency_schemas",
    "implementation_bindings",
    "configuration_bindings",
    "trust_policy_sha256",
    "provenance_sha256",
    "mathematical_authority",
}
_MAX_PROVENANCE_BYTES: Final = 67_108_864


class ExecutionProvenanceError(ValueError):
    """Exact execution-provenance validation failure."""


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ExecutionProvenanceError("duplicate provenance key")
        value[key] = item
    return value


def _canonical(value: object) -> bytes:
    try:
        raw = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ExecutionProvenanceError("provenance is not canonical JSON") from exc
    if len(raw) > _MAX_PROVENANCE_BYTES:
        raise ExecutionProvenanceError("provenance exceeds the byte budget")
    return raw


def _mapping(*, own_digest: str | None) -> dict[str, object]:
    return {
        "schema": PROVENANCE_SCHEMA,
        "dependency_contracts": dict(EXECUTION_CONTRACT_BINDINGS),
        "dependency_schemas": dict(EXECUTION_SCHEMA_BINDINGS),
        "implementation_bindings": dict(EXECUTION_IMPLEMENTATION_BINDINGS),
        "configuration_bindings": dict(EXECUTION_CONFIGURATION_BINDINGS),
        "trust_policy_sha256": TRUST_POLICY_SHA256,
        "provenance_sha256": own_digest,
        "mathematical_authority": False,
    }


def build_execution_provenance() -> tuple[bytes, str]:
    """Return the canonical current provenance object and its exact identity."""

    identity = hashlib.sha256(_canonical(_mapping(own_digest=None))).hexdigest()
    return _canonical(_mapping(own_digest=identity)), identity


def parse_execution_provenance(raw: bytes) -> dict[str, object]:
    """Strictly validate one canonical current execution-provenance object."""

    if type(raw) is not bytes or not raw or len(raw) > _MAX_PROVENANCE_BYTES:
        raise ExecutionProvenanceError("provenance bytes are outside the budget")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(
                ExecutionProvenanceError("provenance floats are forbidden")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ExecutionProvenanceError("provenance constants are forbidden")
            ),
        )
    except ExecutionProvenanceError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ExecutionProvenanceError("provenance JSON is invalid") from exc
    if type(value) is not dict or set(value) != _PROVENANCE_KEYS:
        raise ExecutionProvenanceError("provenance field set differs")
    typed = cast(dict[str, object], value)
    if _canonical(typed) != raw:
        raise ExecutionProvenanceError("provenance bytes are not canonical")
    identity = typed["provenance_sha256"]
    if type(identity) is not str or len(identity) != 64:
        raise ExecutionProvenanceError("provenance identity is malformed")
    try:
        int(identity, 16)
    except ValueError as exc:
        raise ExecutionProvenanceError("provenance identity is malformed") from exc
    expected = _mapping(own_digest=identity)
    if typed != expected:
        raise ExecutionProvenanceError("provenance inventory differs")
    if identity != hashlib.sha256(_canonical(_mapping(own_digest=None))).hexdigest():
        raise ExecutionProvenanceError("provenance identity differs")
    return typed

if tuple(
    len(value)
    for value in (
        EXECUTION_CONTRACT_BINDINGS,
        EXECUTION_SCHEMA_BINDINGS,
        EXECUTION_IMPLEMENTATION_BINDINGS,
        EXECUTION_CONFIGURATION_BINDINGS,
    )
) != (20, 65, 5, 5):
    raise RuntimeError("execution provenance inventory count differs")


__all__ = [
    "ExecutionProvenanceError",
    "EXECUTION_CONFIGURATION_BINDINGS",
    "EXECUTION_CONTRACT_BINDINGS",
    "EXECUTION_IMPLEMENTATION_BINDINGS",
    "EXECUTION_SCHEMA_BINDINGS",
    "PROVENANCE_SCHEMA",
    "PROVENANCE_SCHEMA_SHA256",
    "TRUST_POLICY_SHA256",
    "build_execution_provenance",
    "parse_execution_provenance",
]
