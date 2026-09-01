from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mathhead.capability_registry as registry_module  # noqa: E402
from mathhead.capability_registry import (  # noqa: E402
    CONTRACT_SHA256,
    SCHEMA_SHA256S,
    CapabilityAvailability,
    CapabilityRegistryValidationError,
    CapabilityRouteResult,
    capability_availability_bytes,
    capability_route_result_bytes,
    make_capability_availability,
    make_capability_route_request,
    parse_capability_route_request,
    parse_capability_route_result,
    route_capabilities,
    validate_capability_route_result,
)
from tests.capability_registry.fixtures import (  # noqa: E402
    RouteFixture,
    canonical,
    plugin_bytes,
    sha,
)

def self_hash(value: dict[str, object], field: str) -> None:
    value[field] = None
    value[field] = sha(canonical(value))


class CapabilityRegistryContractTests(unittest.TestCase):
    def test_accepted_contract_and_closed_schemas_are_exact(self) -> None:
        accepted = ROOT / "docs/contracts/MH-C-CAPABILITY-REGISTRY-001.json"
        proposal = ROOT / "docs/contracts/proposed/MH-C-CAPABILITY-REGISTRY-001.json"
        self.assertEqual(accepted.read_bytes(), proposal.read_bytes())
        self.assertEqual(sha(accepted.read_bytes()), CONTRACT_SHA256)
        self.assertEqual(set(SCHEMA_SHA256S), {
            "capability-availability-v1.schema.json",
            "capability-candidate-v1.schema.json",
            "capability-cost-derivation-v1.schema.json",
            "capability-incompatibility-v1.schema.json",
            "capability-registry-entry-v1.schema.json",
            "capability-registry-v1.schema.json",
            "capability-route-request-v1.schema.json",
            "capability-route-result-v1.schema.json",
        })
        for name, expected in SCHEMA_SHA256S.items():
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            self.assertTrue(raw.endswith(b"\n"), name)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, name)
            self.assertEqual(json.loads(raw)["additionalProperties"], False, name)


class CapabilityRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = RouteFixture()
        availability = make_capability_availability(platform="linux", python_version="3.12")
        request = make_capability_route_request(
            **cls.fixture.request_fields,
            availability=availability,
        )
        empty = route_capabilities(request, (), cls.fixture.artifacts)
        if empty.status != "unsupported" or empty.fragment is None:
            raise AssertionError(empty)
        cls.fragment = empty.fragment
        cls.descriptor = plugin_bytes(cls.fragment)

    def availability(self, descriptors: tuple[bytes, ...], **changes: object):
        values: dict[str, object] = {
            "platform": "linux",
            "python_version": "3.12",
            "available_descriptor_sha256s": tuple(sorted({sha(item) for item in descriptors})),
        }
        values.update(changes)
        return make_capability_availability(**values)

    def request(
        self,
        descriptors: tuple[bytes, ...],
        *,
        availability_changes: dict[str, object] | None = None,
        request_changes: dict[str, object] | None = None,
    ) -> bytes:
        fields = dict(self.fixture.request_fields)
        if request_changes:
            fields.update(request_changes)
        availability = self.availability(descriptors, **(availability_changes or {}))
        return make_capability_route_request(**fields, availability=availability)

    def route(
        self,
        descriptors: tuple[bytes, ...] | None = None,
        *,
        availability_changes: dict[str, object] | None = None,
        request_changes: dict[str, object] | None = None,
        artifacts: tuple[bytes, ...] | None = None,
    ) -> CapabilityRouteResult:
        selected = (self.descriptor,) if descriptors is None else descriptors
        request = self.request(
            selected,
            availability_changes=availability_changes,
            request_changes=request_changes,
        )
        return route_capabilities(
            request,
            selected,
            self.fixture.artifacts if artifacts is None else artifacts,
        )

    def test_availability_and_request_are_canonical_and_strict(self) -> None:
        availability = self.availability((self.descriptor,))
        raw = capability_availability_bytes(availability)
        self.assertTrue(raw.endswith(b"\n"))
        request = self.request((self.descriptor,))
        self.assertEqual(parse_capability_route_request(request).availability, availability)
        with self.assertRaises(PermissionError):
            CapabilityAvailability()  # type: ignore[call-arg]
        with self.assertRaises(CapabilityRegistryValidationError):
            parse_capability_route_request(request.rstrip(b"\n"))

    def test_exact_route_binds_every_layer_and_round_trips(self) -> None:
        result = self.route()
        self.assertEqual((result.status, result.reason_code), ("routed", "ROUTED"))
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.selected_candidate_sha256, result.candidates[0].candidate_sha256)
        self.assertEqual(result.fragment, self.fragment)
        candidate = result.candidates[0]
        self.assertEqual(candidate.request_sha256, result.request_sha256)
        self.assertEqual(candidate.registry_sha256, result.registry.registry_sha256)
        self.assertEqual(candidate.fragment_sha256, result.fragment.fragment_sha256)
        self.assertEqual(candidate.cost.estimated_cost, 24)
        self.assertFalse(result.mathematical_authority)
        validate_capability_route_result(result)
        raw = capability_route_result_bytes(result)
        self.assertEqual(parse_capability_route_result(raw), result)

    def test_empty_registry_is_unsupported_and_duplicate_bytes_are_idempotent(self) -> None:
        empty = self.route(())
        self.assertEqual(empty.status, "unsupported")
        self.assertEqual(empty.candidates, ())
        duplicate = self.route((self.descriptor, self.descriptor))
        single = self.route((self.descriptor,))
        self.assertEqual(capability_route_result_bytes(duplicate), capability_route_result_bytes(single))
        self.assertEqual(len(duplicate.registry.entries), 1)

    def test_cost_priority_and_lexical_order_are_deterministic(self) -> None:
        high_cost = plugin_bytes(self.fragment, suffix="zulu", base_cost=30, priority=999)
        low_priority = plugin_bytes(self.fragment, suffix="bravo", base_cost=5, priority=10)
        high_priority = plugin_bytes(self.fragment, suffix="charlie", base_cost=5, priority=20)
        descriptors = (high_cost, low_priority, high_priority)
        forward = self.route(descriptors)
        reverse = self.route(tuple(reversed(descriptors)))
        self.assertEqual(
            [item.capability_id for item in forward.candidates],
            ["capability_charlie", "capability_bravo", "capability_zulu"],
        )
        self.assertEqual(capability_route_result_bytes(forward), capability_route_result_bytes(reverse))

    def test_every_capability_is_candidate_or_explicit_incompatibility(self) -> None:
        def incompatible(value: dict[str, object]) -> None:
            capability = value["capabilities"][0]  # type: ignore[index]
            capability["fragment"]["domains"] = ["real"]  # type: ignore[index]
            capability["fragment"]["required_theory_features"] = [  # type: ignore[index]
                "org.mathhead.feature.missing"
            ]

        rejected = plugin_bytes(self.fragment, suffix="reject", mutation=incompatible)
        result = self.route((self.descriptor, rejected))
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(len(result.incompatibilities), 1)
        self.assertEqual(
            result.incompatibilities[0].reason_codes,
            ("DOMAIN_MISMATCH", "FEATURE_REQUIRED"),
        )

    def test_fragment_format_platform_extension_effect_and_replay_mismatches_close(self) -> None:
        mutations = {
            "THEORY_MISMATCH": lambda p: p["capabilities"][0].update(
                theories=["org.mathhead.theory.analysis"]
            ),
            "QUANTIFIER_MISMATCH": lambda p: p["capabilities"][0]["fragment"].update(
                quantifiers=["forall"]
            ),
            "EXPRESSION_KIND_MISMATCH": lambda p: p["capabilities"][0]["fragment"].update(
                expression_kinds=["org.mathhead.expression.add"]
            ),
            "RELATION_KIND_MISMATCH": lambda p: p["capabilities"][0]["fragment"].update(
                relation_kinds=["org.mathhead.relation.less"]
            ),
            "LIMIT_EXCEEDED": lambda p: p["capabilities"][0]["fragment"].update(
                maximum_variables=0
            ),
            "FEATURE_FORBIDDEN": lambda p: p["capabilities"][0]["fragment"].update(
                forbidden_theory_features=["org.mathhead.theory.arithmetic"],
                required_theory_features=["org.mathhead.feature.exact-arithmetic"],
            ),
            "EVIDENCE_FORMAT_MISMATCH": lambda p: p["capabilities"][0]["evidence_formats"][0].update(
                minor_minimum=1, minor_maximum=1
            ),
            "PLATFORM_UNAVAILABLE": lambda p: p["compatibility"].update(platforms=["macos"]),
            "PYTHON_VERSION_UNAVAILABLE": lambda p: p["compatibility"].update(
                python_versions=["3.14"]
            ),
            "EXTENSION_UNAVAILABLE": lambda p: p["compatibility"].update(
                required_extensions=["org.mathhead.extension.fixture"]
            ),
            "REPLAY_MODE_UNAVAILABLE": lambda p: (
                next(
                    item for item in p["operations"] if item["operation"] == "solve"
                ).update(replay_modes=["seeded"]),
                next(
                    item for item in p["operations"] if item["operation"] == "check"
                ).update(replay_modes=["seeded"]),
                next(
                    item for item in p["operations"] if item["operation"] == "explain"
                ).update(replay_modes=["seeded"]),
                p["replay"].update(supported_modes=["seeded"]),
            ),
        }
        for reason, mutation in mutations.items():
            with self.subTest(reason=reason):
                descriptor = plugin_bytes(self.fragment, suffix=reason.lower(), mutation=mutation)
                result = self.route((descriptor,))
                self.assertEqual(result.status, "unsupported", result.diagnostic)
                self.assertIn(reason, result.incompatibilities[0].reason_codes)

        def network_effect(value: dict[str, object]) -> None:
            value["effects"][2].update(  # type: ignore[index]
                mode="declared", policy_id="org.mathhead.policy.network", reason="fixture"
            )
            value["lifecycle"]["isolation"] = "subprocess_required"  # type: ignore[index]
            value["lifecycle"]["shutdown_timeout_us"] = 1  # type: ignore[index]
            next(
                item for item in value["operations"] if item["operation"] == "solve"  # type: ignore[index]
            )["effect_kinds"] = ["network"]

        effect_descriptor = plugin_bytes(self.fragment, suffix="effect", mutation=network_effect)
        effect_result = self.route((effect_descriptor,))
        self.assertIn("EFFECT_FORBIDDEN", effect_result.incompatibilities[0].reason_codes)

    def test_decision_construction_verification_and_explanation_operations(self) -> None:
        cases = (
            ("decision", "solve", self.fixture.request_fields["evidence_format"], None),
            ("construction", "solve", self.fixture.request_fields["evidence_format"], None),
            (
                "verification",
                "check",
                self.fixture.request_fields["evidence_format"],
                {"format_id": "org.mathhead.certificate", "major": 1, "minor": 0, "required_features": []},
            ),
            ("explanation", "explain", None, None),
        )
        for kind, operation, evidence, certificate in cases:
            with self.subTest(kind=kind):
                descriptor = plugin_bytes(
                    self.fragment,
                    suffix=kind,
                    mutation=lambda value, kind=kind: value["capabilities"][0].update(kind=kind),
                )
                result = self.route(
                    (descriptor,),
                    request_changes={
                        "capability_kind": kind,
                        "operation": operation,
                        "evidence_format": evidence,
                        "certificate_format": certificate,
                    },
                )
                self.assertEqual(result.status, "routed", result.diagnostic)

    def test_registry_collisions_and_missing_dependencies_fail_closed(self) -> None:
        collision = plugin_bytes(
            self.fragment,
            suffix="collision",
            mutation=lambda value: value["capabilities"][0].update(
                capability_id="capability_arithmetic"
            ),
        )
        result = self.route((self.descriptor, collision))
        self.assertEqual(result.status, "invalid")
        self.assertIsNone(result.registry)

        missing_digest = "f" * 64
        dependent = plugin_bytes(
            self.fragment,
            suffix="dependent",
            mutation=lambda value: value["compatibility"].update(
                plugin_dependencies=[{
                    "plugin_id": "org.mathhead.missing-plugin",
                    "version_minimum": "1.0.0",
                    "version_maximum_exclusive": "2.0.0",
                    "descriptor_sha256": missing_digest,
                }]
            ),
        )
        missing = self.route((dependent,))
        self.assertEqual(missing.status, "invalid")
        self.assertIsNone(missing.registry)

        forged_abi = plugin_bytes(
            self.fragment,
            suffix="forged_abi",
            mutation=lambda value: next(
                item for item in value["operations"] if item["operation"] == "solve"
            ).update(response_schema="mathhead.plugin-forged.v1"),
        )
        forged = self.route((forged_abi,))
        self.assertEqual(forged.status, "invalid")
        self.assertIsNone(forged.registry)

    def test_dependency_chain_requires_exact_registry_and_availability_closure(self) -> None:
        foundation = plugin_bytes(self.fragment, suffix="foundation")

        def depend(value: dict[str, object]) -> None:
            value["compatibility"]["plugin_dependencies"] = [{  # type: ignore[index]
                "plugin_id": "org.mathhead.fixture-foundation",
                "version_minimum": "1.0.0",
                "version_maximum_exclusive": "2.0.0",
                "descriptor_sha256": sha(foundation),
            }]

        dependent = plugin_bytes(self.fragment, suffix="dependent_ok", mutation=depend)
        result = self.route((dependent, foundation))
        self.assertEqual(result.status, "routed", result.diagnostic)
        self.assertEqual(
            result.registry.dependency_order_sha256s,
            (sha(foundation), sha(dependent)),
        )
        dependent_candidate = next(
            item for item in result.candidates if item.capability_id == "capability_dependent_ok"
        )
        self.assertEqual(dependent_candidate.dependency_descriptor_sha256s, (sha(foundation),))

        unavailable = self.route(
            (dependent, foundation),
            availability_changes={"available_descriptor_sha256s": (sha(dependent),)},
        )
        rejected = next(
            item for item in unavailable.incompatibilities
            if item.capability_id == "capability_dependent_ok"
        )
        self.assertIn("DEPENDENCY_UNAVAILABLE", rejected.reason_codes)

    def test_stale_session_and_artifact_inventory_never_route(self) -> None:
        stale = self.route(request_changes={"session_head_sha256": "0" * 64})
        self.assertEqual(stale.status, "invalid")
        self.assertIsNone(stale.result_sha256)
        duplicate_artifact = self.route(artifacts=(*self.fixture.artifacts, self.fixture.artifacts[-1]))
        self.assertEqual(duplicate_artifact.status, "invalid")
        missing_artifact = self.route(artifacts=self.fixture.artifacts[:-1])
        self.assertEqual(missing_artifact.status, "invalid")

    def test_results_reject_mutation_subclass_pickle_and_repaired_forgery(self) -> None:
        result = self.route()
        with self.assertRaises(FrozenInstanceError):
            result.status = "unsupported"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            type("ForgedRouteResult", (CapabilityRouteResult,), {})
        with self.assertRaises(TypeError):
            pickle.dumps(result)

        value = json.loads(capability_route_result_bytes(result))
        value["candidates"][0]["cost"]["estimated_cost"] += 1
        self_hash(value["candidates"][0]["cost"], "cost_sha256")
        self_hash(value["candidates"][0], "candidate_sha256")
        self_hash(value, "result_sha256")
        with self.assertRaises(CapabilityRegistryValidationError):
            parse_capability_route_result(canonical(value))

    def test_noncanonical_unknown_duplicate_and_float_inputs_are_invalid(self) -> None:
        request = self.request((self.descriptor,))
        malformed = (
            request.rstrip(b"\n"),
            request.replace(b'{"availability"', b'{"unknown":null,"availability"'),
            request.replace(b'{"availability"', b'{"schema":"duplicate","availability"'),
            request.replace(b'"mathematical_authority":false', b'"mathematical_authority":0.0'),
        )
        for data in malformed:
            with self.subTest(data=data[:40]):
                result = route_capabilities(data, (self.descriptor,), self.fixture.artifacts)
                self.assertEqual(result.status, "invalid")
                self.assertIsNone(result.registry)

    def test_memory_and_process_control_exceptions_propagate(self) -> None:
        request = self.request((self.descriptor,))
        for exception in (MemoryError(), KeyboardInterrupt(), SystemExit()):
            with self.subTest(exception=type(exception).__name__):
                with mock.patch.object(registry_module, "_build_registry", side_effect=exception):
                    with self.assertRaises(type(exception)):
                        route_capabilities(request, (self.descriptor,), self.fixture.artifacts)

    def test_descriptor_semantic_invariants_fail_closed_independently(self) -> None:
        def set_dependency(value: dict[str, object], *, self_reference: bool) -> None:
            value["compatibility"]["plugin_dependencies"] = [{  # type: ignore[index]
                "plugin_id": (
                    value["plugin_id"] if self_reference else "org.mathhead.fixture-dependency"
                ),
                "version_minimum": "1.0.0",
                "version_maximum_exclusive": "1.0.0" if not self_reference else "2.0.0",
                "descriptor_sha256": "f" * 64,
            }]

        def overlap_extensions(value: dict[str, object]) -> None:
            compatibility = value["compatibility"]  # type: ignore[assignment]
            compatibility["required_extensions"] = ["org.mathhead.extension.same"]
            compatibility["optional_extensions"] = ["org.mathhead.extension.same"]

        def duplicate_format(value: dict[str, object]) -> None:
            formats = value["capabilities"][0]["evidence_formats"]  # type: ignore[index]
            formats.append(dict(formats[0]))

        def declare_network_without_isolation(value: dict[str, object]) -> None:
            value["effects"][2].update(  # type: ignore[index]
                mode="declared",
                policy_id="org.mathhead.policy.network",
                reason="fixture",
            )
            next(
                item for item in value["operations"]  # type: ignore[index]
                if item["operation"] == "solve"
            )["effect_kinds"] = ["network"]

        def seeded_initialization_without_seeded_replay(value: dict[str, object]) -> None:
            value["replay"].update(  # type: ignore[index]
                supported_modes=["deterministic"],
                seed_policy="forbidden",
            )
            for operation in value["operations"]:  # type: ignore[index]
                if operation["operation"] != "plan_cost":
                    operation["replay_modes"] = ["deterministic"]
            value["lifecycle"]["initialization"] = "seeded"  # type: ignore[index]

        def collide_component_and_capability(value: dict[str, object]) -> None:
            value["capabilities"][0]["capability_id"] = value["components"]["producer"][  # type: ignore[index]
                "component_id"
            ]

        cases = {
            "root-schema": lambda value: value.update(schema="mathhead.theory-plugin.v2"),
            "plugin-semver": lambda value: value.update(plugin_version="not-semver"),
            "api-binding": lambda value: value["api"].update(contract_sha256="0" * 64),  # type: ignore[index]
            "package-version": lambda value: value["implementation"].update(package_version="2.0.0"),  # type: ignore[index]
            "component-role": lambda value: value["components"]["producer"].update(role="checker"),  # type: ignore[index]
            "component-alias": lambda value: value["components"]["checker"].update(component_id=value["components"]["producer"]["component_id"]),  # type: ignore[index]
            "producer-provenance": lambda value: value["components"]["producer"].update(implementation_sha256="0" * 64),  # type: ignore[index]
            "foundation-count": lambda value: value["compatibility"]["contracts"].pop(),  # type: ignore[index]
            "foundation-binding": lambda value: value["compatibility"]["contracts"][0].update(sha256="0" * 64),  # type: ignore[index]
            "foundation-order": lambda value: value["compatibility"]["contracts"].reverse(),  # type: ignore[index]
            "extension-overlap": overlap_extensions,
            "self-dependency": lambda value: set_dependency(value, self_reference=True),
            "empty-dependency-range": lambda value: set_dependency(value, self_reference=False),
            "capability-kind": lambda value: value["capabilities"][0].update(kind="unknown"),  # type: ignore[index]
            "empty-theories": lambda value: value["capabilities"][0].update(theories=[]),  # type: ignore[index]
            "feature-overlap": lambda value: value["capabilities"][0]["fragment"].update(forbidden_theory_features=list(value["capabilities"][0]["fragment"]["required_theory_features"])),  # type: ignore[index]
            "format-interval": lambda value: value["capabilities"][0]["evidence_formats"][0].update(minor_minimum=2, minor_maximum=1),  # type: ignore[index]
            "format-duplicate": duplicate_format,
            "missing-producer-format": lambda value: value["capabilities"][0].update(evidence_formats=[]),  # type: ignore[index]
            "missing-verifier-format": lambda value: value["capabilities"][0].update(kind="verification", certificate_formats=[]),  # type: ignore[index]
            "cost-maximum": lambda value: value["capabilities"][0]["cost_model"].update(maximum=0),  # type: ignore[index]
            "effect-count": lambda value: value["effects"].pop(),  # type: ignore[index]
            "unknown-effect": lambda value: value["effects"][0].update(kind="unknown"),  # type: ignore[index]
            "effect-policy": lambda value: value["effects"][0].update(policy_id="org.mathhead.policy.bad"),  # type: ignore[index]
            "effect-order": lambda value: value["effects"].reverse(),  # type: ignore[index]
            "replay-count": lambda value: value["replay"].update(supported_modes=["deterministic", "recorded", "seeded"]),  # type: ignore[index]
            "operation-count": lambda value: value["operations"].pop(),  # type: ignore[index]
            "unknown-operation": lambda value: value["operations"][0].update(operation="unknown"),  # type: ignore[index]
            "undeclared-operation-effect": lambda value: next(item for item in value["operations"] if item["operation"] == "solve").update(effect_kinds=["network"]),  # type: ignore[index]
            "outcome-count": lambda value: value["operations"][0].update(outcomes=[f"outcome-{index:02d}" for index in range(21)]),  # type: ignore[index]
            "operation-abi": lambda value: value["operations"][0].update(component_id="component_checker"),  # type: ignore[index]
            "operation-order": lambda value: value["operations"].reverse(),  # type: ignore[index]
            "zero-concurrency": lambda value: value["lifecycle"].update(maximum_concurrency=0),  # type: ignore[index]
            "invocation-persistence": lambda value: value["lifecycle"].update(state_persistence="content_addressed"),  # type: ignore[index]
            "subprocess-timeout": lambda value: value["lifecycle"].update(isolation="subprocess_required"),  # type: ignore[index]
            "seeded-initialization": seeded_initialization_without_seeded_replay,
            "external-effect-isolation": declare_network_without_isolation,
            "seed-policy": lambda value: value["replay"].update(seed_policy="forbidden"),  # type: ignore[index]
            "configuration-binding": lambda value: value["replay"].update(configuration_sha256="0" * 64),  # type: ignore[index]
            "hard-limits": lambda value: value["limits"].update(entities=99),  # type: ignore[index]
            "extensions-shape": lambda value: value.update(extensions=[]),
            "cross-class-identity": collide_component_and_capability,
        }
        for name, mutation in cases.items():
            with self.subTest(name=name):
                descriptor = plugin_bytes(
                    self.fragment,
                    suffix=f"invalid_{name.replace('-', '_')}",
                    mutation=mutation,
                )
                result = self.route((descriptor,))
                self.assertEqual(result.status, "invalid", result.diagnostic)
                self.assertIsNone(result.registry)

    def test_canonical_budget_and_public_type_boundaries_fail_closed(self) -> None:
        invalid_values = (
            9_007_199_254_740_992,
            "not-nfc-e\u0301",
            "contains\x00nul",
            {1: "non-string-key"},
            1.5,
        )
        for value in invalid_values:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ValueError):
                    registry_module._check_canonical_value(value)

        with mock.patch.object(registry_module, "MAX_JSON_NODES", 0):
            with self.assertRaises(ValueError):
                registry_module._check_canonical_value({})
        with mock.patch.object(registry_module, "MAX_JSON_NESTING", 0):
            with self.assertRaises(ValueError):
                registry_module._check_canonical_value({"nested": {}})
        with mock.patch.object(registry_module, "MAX_STRING_CODEPOINTS", 1):
            with self.assertRaises(ValueError):
                registry_module._check_canonical_value("too long")
        with self.assertRaises(ValueError):
            registry_module._canonical_bytes({"value": "large"}, maximum=1)

        malformed_json = (b"", b"not-json", b"[]", b'{"b":1,"a":2}\n')
        for raw in malformed_json:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    registry_module._parse_json(raw, "$", 64)
        with self.assertRaises(ValueError):
            registry_module._parse_json("not-bytes", "$", 64)

        availability = self.availability((self.descriptor,))
        public_type_calls = (
            lambda: capability_availability_bytes(object()),
            lambda: make_capability_route_request(
                **self.fixture.request_fields,
                availability=object(),
            ),
            lambda: capability_route_result_bytes(object()),
            lambda: validate_capability_route_result(object()),
        )
        for call in public_type_calls:
            with self.subTest(call=call):
                with self.assertRaises(CapabilityRegistryValidationError):
                    call()
        self.assertIsInstance(capability_availability_bytes(availability), bytes)

        for cls in (
            registry_module.CapabilityRegistryEntry,
            registry_module.CapabilityRegistry,
            registry_module.CapabilityRouteRequest,
            registry_module.CapabilityFragment,
            registry_module.CapabilityCostDerivation,
            registry_module.CapabilityCandidate,
            registry_module.CapabilityIncompatibility,
            CapabilityRouteResult,
        ):
            with self.subTest(cls=cls.__name__):
                with self.assertRaises(PermissionError):
                    cls()

    def test_structural_helpers_cover_all_supported_projection_kinds(self) -> None:
        domain_cases = (
            (None, None),
            ({"kind": "builtin", "name": "integer"}, "integer"),
            ({"kind": "modular"}, "integer"),
            ({"kind": "collection"}, "set"),
            ({"kind": "set"}, "set"),
            ({"kind": "structure", "name": "graph"}, "graph"),
            ({"kind": "unknown"}, None),
        )
        for value, expected in domain_cases:
            with self.subTest(domain=value):
                self.assertEqual(registry_module._domain_name(value), expected)

        structural = [{
            "kind": "quantified",
            "quantifier": "forall",
            "domain": {"kind": "builtin", "name": "integer"},
            "body": {
                "kind": "relation",
                "relation": {"kind": "equal"},
                "arguments": [
                    {"kind": "variable", "variable": "x"},
                    {"kind": "add", "operands": [{"kind": "literal"}]},
                ],
            },
        }]
        domains, expressions, relations, count, depth, nodes = registry_module._walk_structural(
            structural
        )
        self.assertEqual(domains, {"integer"})
        self.assertIn("org.mathhead.expression.variable", expressions)
        self.assertIn("org.mathhead.relation.equal", relations)
        self.assertEqual((count, depth), (1, 1))
        self.assertGreaterEqual(nodes, 2)

        degrees = (
            ({"kind": "variable"}, 1),
            ({"kind": "literal"}, 0),
            ({"kind": "add", "operands": [{"kind": "variable"}, {"kind": "literal"}]}, 1),
            ({"kind": "add", "operands": "invalid"}, 0),
            ({"kind": "multiply", "operands": [{"kind": "variable"}, {"kind": "variable"}]}, 2),
            ({"kind": "multiply", "operands": "invalid"}, 0),
            ({"kind": "power", "base": {"kind": "variable"}, "exponent": 3}, 3),
            ({"kind": "power", "base": {"kind": "variable"}, "exponent": True}, 1),
            ({"kind": "wrapper", "child": {"kind": "variable"}}, 1),
            (None, 0),
        )
        for value, expected in degrees:
            with self.subTest(polynomial=value):
                self.assertEqual(registry_module._polynomial_degree(value), expected)

        self.assertGreater(
            registry_module._semver_rank("1.0.0", "version"),
            registry_module._semver_rank("1.0.0-alpha.1", "version"),
        )
        supported = ({
            "format_id": "org.mathhead.proof",
            "major": 1,
            "minor_minimum": 0,
            "minor_maximum": 1,
            "required_features": (),
        },)
        self.assertTrue(registry_module._format_matches(supported, None))
        self.assertTrue(
            registry_module._format_matches(
                supported,
                registry_module._freeze_json({
                    "format_id": "org.mathhead.proof",
                    "major": 1,
                    "minor": 1,
                    "required_features": [],
                }),
            )
        )
        self.assertFalse(
            registry_module._format_matches(
                supported,
                registry_module._freeze_json({
                    "format_id": "org.mathhead.other",
                    "major": 1,
                    "minor": 0,
                    "required_features": [],
                }),
            )
        )

    def test_saturated_cost_and_remaining_public_incompatibility_reasons(self) -> None:
        saturated = plugin_bytes(
            self.fragment,
            suffix="saturated",
            mutation=lambda value: value["capabilities"][0]["cost_model"].update(  # type: ignore[index]
                base=10,
                maximum=10,
            ),
        )
        saturated_result = self.route((saturated,))
        self.assertTrue(saturated_result.candidates[0].cost.saturated)
        self.assertEqual(saturated_result.candidates[0].cost.estimated_cost, 10)

        unavailable = self.route(
            (self.descriptor,),
            availability_changes={"available_descriptor_sha256s": ()},
        )
        self.assertIn("LIFECYCLE_UNAVAILABLE", unavailable.incompatibilities[0].reason_codes)

        wrong_kind = plugin_bytes(
            self.fragment,
            suffix="wrong_kind",
            mutation=lambda value: value["capabilities"][0].update(kind="verification"),  # type: ignore[index]
        )
        kind_result = self.route((wrong_kind,))
        self.assertIn("CAPABILITY_KIND_MISMATCH", kind_result.incompatibilities[0].reason_codes)

        verification = plugin_bytes(
            self.fragment,
            suffix="certificate_mismatch",
            mutation=lambda value: value["capabilities"][0].update(kind="verification"),  # type: ignore[index]
        )
        certificate_result = self.route(
            (verification,),
            request_changes={
                "capability_kind": "verification",
                "operation": "check",
                "certificate_format": {
                    "format_id": "org.mathhead.other-certificate",
                    "major": 1,
                    "minor": 0,
                    "required_features": [],
                },
            },
        )
        self.assertIn(
            "CERTIFICATE_FORMAT_MISMATCH",
            certificate_result.incompatibilities[0].reason_codes,
        )

    def test_serialized_results_reject_nested_and_structural_drift(self) -> None:
        routed = json.loads(capability_route_result_bytes(self.route()))

        def rejected(value: dict[str, object]) -> None:
            with self.assertRaises(CapabilityRegistryValidationError):
                parse_capability_route_result(canonical(value))

        direct_mutations = {
            "contract": lambda value: value.update(contract_id="MH-C-FORGED-001"),
            "status": lambda value: value.update(status="unknown"),
            "diagnostic": lambda value: value.update(diagnostic="x" * 1025),
            "candidate-array": lambda value: value.update(candidates={}),
            "entry-schema": lambda value: value["registry"]["entries"][0].update(schema="forged"),  # type: ignore[index]
            "entry-identity": lambda value: value["registry"]["entries"][0].update(entry_sha256="0" * 64),  # type: ignore[index]
            "registry-schema": lambda value: value["registry"].update(schema="forged"),  # type: ignore[index]
            "registry-entries": lambda value: value["registry"].update(entries={}),  # type: ignore[index]
            "fragment-schema": lambda value: value["fragment"].update(schema="forged"),  # type: ignore[index]
            "fragment-goals": lambda value: value["fragment"].update(goals=0),  # type: ignore[index]
            "fragment-identity": lambda value: value["fragment"].update(fragment_sha256="0" * 64),  # type: ignore[index]
            "cost-schema": lambda value: value["candidates"][0]["cost"].update(schema="forged"),  # type: ignore[index]
            "cost-arithmetic": lambda value: value["candidates"][0]["cost"].update(unsaturated_total=999),  # type: ignore[index]
            "cost-saturation": lambda value: value["candidates"][0]["cost"].update(saturated=True),  # type: ignore[index]
            "cost-confidence": lambda value: value["candidates"][0]["cost"].update(confidence_ppm=0),  # type: ignore[index]
            "cost-identity": lambda value: value["candidates"][0]["cost"].update(cost_sha256="0" * 64),  # type: ignore[index]
            "candidate-schema": lambda value: value["candidates"][0].update(schema="forged"),  # type: ignore[index]
            "candidate-operation": lambda value: value["candidates"][0].update(operation="check"),  # type: ignore[index]
            "candidate-identity": lambda value: value["candidates"][0].update(candidate_sha256="0" * 64),  # type: ignore[index]
        }
        for name, mutation in direct_mutations.items():
            with self.subTest(name=name):
                value = json.loads(canonical(routed))
                mutation(value)
                rejected(value)

        identity_drift = json.loads(canonical(routed))
        identity_drift["diagnostic"] = "changed without identity repair"
        rejected(identity_drift)

        registry_absent = json.loads(canonical(routed))
        registry_absent.update(
            request_sha256=None,
            registry=None,
            fragment=None,
            candidates=[],
            incompatibilities=[],
            selected_candidate_sha256=None,
        )
        self_hash(registry_absent, "result_sha256")
        rejected(registry_absent)

        fragment_absent = json.loads(canonical(routed))
        fragment_absent["fragment"] = None
        self_hash(fragment_absent, "result_sha256")
        rejected(fragment_absent)

        missing_projection = json.loads(canonical(routed))
        missing_projection.update(
            status="unsupported",
            reason_code="NO_COMPATIBLE_CAPABILITY",
            candidates=[],
            selected_candidate_sha256=None,
        )
        self_hash(missing_projection, "result_sha256")
        rejected(missing_projection)

        selection_drift = json.loads(canonical(routed))
        selection_drift["selected_candidate_sha256"] = None
        self_hash(selection_drift, "result_sha256")
        rejected(selection_drift)

        ambiguity_drift = json.loads(canonical(routed))
        ambiguity_drift.update(
            status="ambiguous",
            reason_code="NON_UNIQUE_SELECTION",
            selected_candidate_sha256=None,
        )
        self_hash(ambiguity_drift, "result_sha256")
        rejected(ambiguity_drift)

        expensive = plugin_bytes(self.fragment, suffix="ordering_expensive", base_cost=20)
        cheap = plugin_bytes(self.fragment, suffix="ordering_cheap", base_cost=5)
        ordering = json.loads(capability_route_result_bytes(self.route((expensive, cheap))))
        ordering["candidates"].reverse()
        self_hash(ordering, "result_sha256")
        rejected(ordering)

        def reject_domain(value: dict[str, object]) -> None:
            value["capabilities"][0]["fragment"]["domains"] = ["real"]  # type: ignore[index]

        rejected_a = plugin_bytes(self.fragment, suffix="incompat_a", mutation=reject_domain)
        rejected_b = plugin_bytes(self.fragment, suffix="incompat_b", mutation=reject_domain)
        incompatibility_order = json.loads(
            capability_route_result_bytes(self.route((rejected_a, rejected_b)))
        )
        incompatibility_order["incompatibilities"].reverse()
        self_hash(incompatibility_order, "result_sha256")
        rejected(incompatibility_order)

        invalid = json.loads(
            capability_route_result_bytes(
                route_capabilities(b"not-json", (), ()),
            )
        )
        invalid["request_sha256"] = "0" * 64
        rejected(invalid)


if __name__ == "__main__":
    unittest.main()
