from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_theory_plugin_contract as plugin  # noqa: E402


class TheoryPluginContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema, cls.schema_raw = plugin.load_json(ROOT / plugin.SCHEMA_PATH)

    def valid(self) -> dict[str, object]:
        return copy.deepcopy(plugin.minimal_theory_plugin())

    def fragment(self) -> dict[str, object]:
        return copy.deepcopy(plugin.minimal_fragment())

    def rebind(self, value: dict[str, object]) -> None:
        value["replay"]["descriptor_basis_sha256"] = plugin.descriptor_basis_sha256(value)

    def assert_invalid(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
            plugin.validate_theory_plugin(value, self.schema)
        self.assertEqual(caught.exception.kind, kind)

    def test_schema_identity_closed_root_and_canonical_roundtrip(self) -> None:
        self.assertEqual(hashlib.sha256(self.schema_raw).hexdigest(), plugin.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(set(self.schema["required"]), plugin.ROOT_FIELDS)
        self.assertFalse(self.schema["additionalProperties"])
        value = self.valid()
        plugin.validate_theory_plugin(value, self.schema)
        self.assertEqual(json.loads(plugin.canonical_bytes(value)), value)
        self.assertEqual(plugin.canonical_sha256(value), hashlib.sha256(plugin.canonical_bytes(value)).hexdigest())

    def test_standard_draft_202012_metaschema_and_instance(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is optional outside the test profile")
        jsonschema.Draft202012Validator.check_schema(self.schema)
        jsonschema.Draft202012Validator(self.schema).validate(self.valid())

    def test_unknown_missing_and_malformed_fields_fail(self) -> None:
        unknown = self.valid()
        unknown["trusted"] = True
        self.assert_invalid(unknown, "schema")
        missing = self.valid()
        missing.pop("operations")
        self.assert_invalid(missing, "schema")
        malformed = self.valid()
        malformed["lifecycle"]["scope"] = "global"
        self.assert_invalid(malformed, "schema")

    def test_duplicate_keys_and_noncanonical_file_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
                plugin.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")
            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.valid(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
                plugin.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")
            canonical = Path(directory) / "canonical.json"
            canonical.write_bytes(plugin.canonical_bytes(self.valid()))
            loaded, raw = plugin.load_json(canonical, require_canonical=True)
            self.assertEqual(raw, plugin.canonical_bytes(loaded))

    def test_unicode_scalar_nesting_node_entity_and_input_budgets_fail(self) -> None:
        decomposed = self.valid()
        decomposed["extensions"] = {"org.mathhead.test": "es\u0327it"}
        self.assert_invalid(decomposed, "canonical")
        nul = self.valid()
        nul["extensions"] = {"org.mathhead.test": "bad\x00value"}
        self.assert_invalid(nul, "canonical")
        floating = self.valid()
        floating["extensions"] = {"org.mathhead.test": {"ratio": 0.5}}
        self.assert_invalid(floating, "schema")
        integer = self.valid()
        integer["extensions"] = {"org.mathhead.test": {"count": plugin.MAX_JSON_INTEGER + 1}}
        self.assert_invalid(integer, "budget")
        nested: object = None
        for _ in range(plugin.MAX_CANONICAL_NESTING + 1):
            nested = [nested]
        deep = self.valid()
        deep["extensions"] = {"org.mathhead.test": nested}
        self.assert_invalid(deep, "budget")
        with mock.patch.object(plugin, "MAX_CANONICAL_NODES", 1):
            self.assert_invalid(self.valid(), "budget")
        with mock.patch.object(plugin, "MAX_ENTITIES", 1):
            self.assert_invalid(self.valid(), "budget")
        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b"{}\n")
            with mock.patch.object(plugin, "MAX_INPUT_BYTES", 1):
                with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
                    plugin.load_json(oversized)
            self.assertEqual(caught.exception.kind, "budget")

    def test_api_version_contract_and_reader_compatibility(self) -> None:
        value = self.valid()
        value["api"]["version"] = "1.2.0"
        value["api"]["minor"] = 2
        value["api"]["reader_minimum_minor"] = 1
        self.rebind(value)
        plugin.validate_theory_plugin(value, self.schema)
        confused = self.valid()
        confused["api"]["version"] = "1.2.0"
        self.rebind(confused)
        self.assert_invalid(confused, "compatibility")
        future = self.valid()
        future["api"]["version"] = "2.0.0"
        future["api"]["major"] = 2
        self.rebind(future)
        self.assert_invalid(future, "schema")
        drift = self.valid()
        drift["api"]["contract_sha256"] = "f" * 64
        self.rebind(drift)
        self.assert_invalid(drift, "contract")

    def test_implementation_and_component_provenance_bindings(self) -> None:
        version = self.valid()
        version["implementation"]["package_version"] = "1.0.1"
        self.rebind(version)
        self.assert_invalid(version, "compatibility")
        implementation = self.valid()
        implementation["components"]["producer"]["implementation_sha256"] = "f" * 64
        self.rebind(implementation)
        self.assert_invalid(implementation, "provenance")
        configuration = self.valid()
        configuration["components"]["producer"]["configuration_sha256"] = "f" * 64
        self.rebind(configuration)
        self.assert_invalid(configuration, "provenance")
        replay = self.valid()
        replay["replay"]["configuration_sha256"] = "f" * 64
        self.rebind(replay)
        self.assert_invalid(replay, "replay")

    def test_producer_checker_roles_and_self_attestation_fail(self) -> None:
        role = self.valid()
        role["components"]["checker"]["role"] = "producer"
        self.rebind(role)
        self.assert_invalid(role, "epistemic")
        identity = self.valid()
        identity["components"]["checker"]["component_id"] = "component_producer"
        identity["operations"][2]["component_id"] = "component_producer"
        self.rebind(identity)
        self.assert_invalid(identity, "epistemic")
        alias = self.valid()
        alias["components"]["checker"]["contract_sha256"] = alias["components"]["producer"]["contract_sha256"]
        alias["components"]["checker"]["implementation_sha256"] = alias["components"]["producer"]["implementation_sha256"]
        self.rebind(alias)
        self.assert_invalid(alias, "epistemic")

    def test_foundational_contract_set_order_hash_and_schema_are_exact(self) -> None:
        missing = self.valid()
        missing["compatibility"]["contracts"].pop()
        self.rebind(missing)
        self.assert_invalid(missing, "schema")
        unordered = self.valid()
        unordered["compatibility"]["contracts"].reverse()
        self.rebind(unordered)
        self.assert_invalid(unordered, "canonical")
        drift = self.valid()
        drift["compatibility"]["contracts"][0]["sha256"] = "f" * 64
        self.rebind(drift)
        self.assert_invalid(drift, "compatibility")
        schema = self.valid()
        schema["compatibility"]["contracts"][0]["schema"] = "org.mathhead.wrong"
        self.rebind(schema)
        self.assert_invalid(schema, "compatibility")

    def test_platform_extension_and_plugin_dependency_compatibility(self) -> None:
        unordered = self.valid()
        unordered["compatibility"]["python_versions"].reverse()
        self.rebind(unordered)
        self.assert_invalid(unordered, "canonical")
        overlap = self.valid()
        overlap["compatibility"]["required_extensions"] = ["org.mathhead.extension"]
        overlap["compatibility"]["optional_extensions"] = ["org.mathhead.extension"]
        self.rebind(overlap)
        self.assert_invalid(overlap, "compatibility")
        self_dependency = self.valid()
        self_dependency["compatibility"]["plugin_dependencies"] = [
            {
                "plugin_id": self_dependency["plugin_id"],
                "version_minimum": "1.0.0",
                "version_maximum_exclusive": "2.0.0",
                "descriptor_sha256": "a" * 64,
            }
        ]
        self.rebind(self_dependency)
        self.assert_invalid(self_dependency, "dependency")
        empty_range = self.valid()
        empty_range["compatibility"]["plugin_dependencies"] = [
            {
                "plugin_id": "org.example.other",
                "version_minimum": "2.0.0",
                "version_maximum_exclusive": "1.0.0",
                "descriptor_sha256": "a" * 64,
            }
        ]
        self.rebind(empty_range)
        self.assert_invalid(empty_range, "compatibility")

    def test_capability_order_fragment_sets_and_feature_conflicts(self) -> None:
        unordered = self.valid()
        second = copy.deepcopy(unordered["capabilities"][0])
        second["capability_id"] = "capability_alpha"
        unordered["capabilities"].append(second)
        self.rebind(unordered)
        self.assert_invalid(unordered, "canonical")
        domains = self.valid()
        domains["capabilities"][0]["fragment"]["domains"] = ["rational", "integer"]
        self.rebind(domains)
        self.assert_invalid(domains, "canonical")
        conflict = self.valid()
        conflict["capabilities"][0]["fragment"]["forbidden_theory_features"] = [
            "org.mathhead.theory.arithmetic"
        ]
        self.rebind(conflict)
        self.assert_invalid(conflict, "capability")

    def test_format_ranges_and_capability_output_requirements(self) -> None:
        empty_range = self.valid()
        item = empty_range["capabilities"][0]["evidence_formats"][0]
        item["minor_minimum"] = 2
        item["minor_maximum"] = 1
        self.rebind(empty_range)
        self.assert_invalid(empty_range, "compatibility")
        no_evidence = self.valid()
        no_evidence["capabilities"][0]["evidence_formats"] = []
        self.rebind(no_evidence)
        self.assert_invalid(no_evidence, "capability")
        verify = self.valid()
        verify["capabilities"][0]["kind"] = "verification"
        verify["capabilities"][0]["certificate_formats"] = []
        self.rebind(verify)
        self.assert_invalid(verify, "capability")

    def test_cost_formula_saturation_and_overflow_are_deterministic(self) -> None:
        value = self.valid()
        capability = value["capabilities"][0]
        fragment = self.fragment()
        self.assertEqual(plugin.estimate_cost(capability, fragment), 33)
        fragment["quantifier_count"] = 2
        self.assertEqual(plugin.estimate_cost(capability, fragment), 43)
        capability["cost_model"]["maximum"] = 20
        self.assertEqual(plugin.estimate_cost(capability, fragment), 20)
        overflow = self.fragment()
        overflow["variables"] = plugin.MAX_JSON_INTEGER
        capability["cost_model"]["per_variable"] = 2
        with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
            plugin.estimate_cost(capability, overflow)
        self.assertEqual(caught.exception.kind, "cost")
        invalid = self.valid()
        invalid["capabilities"][0]["cost_model"]["confidence_ppm"] = 0
        self.rebind(invalid)
        self.assert_invalid(invalid, "cost")

    def test_routing_supported_and_every_fragment_boundary_refuses(self) -> None:
        value = self.valid()
        supported = plugin.route_fragment(value, self.fragment(), kind="decision")
        self.assertEqual(supported, {"status": "supported", "capability_id": "capability_arithmetic", "cost": 33})
        mutations = {
            "theories": ["org.mathhead.theory.graph"],
            "domains": ["real"],
            "quantifiers": ["forall"],
            "expression_kinds": ["org.mathhead.expression.multiply"],
            "relation_kinds": ["org.mathhead.relation.less"],
            "polynomial_degree": 4,
            "quantifier_depth": 3,
            "variables": 33,
            "ambiguous": True,
            "exact_arithmetic": False,
            "theory_features": [],
        }
        for field, replacement in mutations.items():
            with self.subTest(field=field):
                fragment = self.fragment()
                fragment[field] = replacement
                self.assertEqual(plugin.route_fragment(value, fragment, kind="decision")["status"], "unsupported")

    def test_routing_tie_breaks_by_cost_priority_then_stable_id(self) -> None:
        value = self.valid()
        second = copy.deepcopy(value["capabilities"][0])
        second["capability_id"] = "capability_beta"
        second["cost_model"]["base"] = 5
        value["capabilities"].append(second)
        self.rebind(value)
        plugin.validate_theory_plugin(value, self.schema)
        self.assertEqual(plugin.route_fragment(value, self.fragment(), kind="decision")["capability_id"], "capability_beta")
        second["cost_model"]["base"] = 10
        second["priority"] = 101
        self.rebind(value)
        self.assertEqual(plugin.route_fragment(value, self.fragment(), kind="decision")["capability_id"], "capability_beta")
        second["priority"] = 100
        self.rebind(value)
        self.assertEqual(plugin.route_fragment(value, self.fragment(), kind="decision")["capability_id"], "capability_arithmetic")

    def test_operation_order_components_contracts_and_authorities_are_exact(self) -> None:
        order = self.valid()
        order["operations"][0], order["operations"][1] = order["operations"][1], order["operations"][0]
        self.rebind(order)
        self.assert_invalid(order, "operation")
        producer = self.valid()
        producer["operations"][2]["component_id"] = "component_producer"
        self.rebind(producer)
        self.assert_invalid(producer, "operation")
        authority = self.valid()
        authority["operations"][1]["authority"] = "checker_attestation"
        self.rebind(authority)
        self.assert_invalid(authority, "operation")
        explain = self.valid()
        explain["operations"][3]["authority"] = "producer_report"
        self.rebind(explain)
        self.assert_invalid(explain, "operation")
        response = self.valid()
        response["operations"][1]["response_contract_ids"] = ["MH-C-ENGINE-RESULT-001"]
        self.rebind(response)
        self.assert_invalid(response, "operation")

    def test_plan_cost_is_pure_unbudgeted_uncancellable_and_deterministic(self) -> None:
        for field, replacement in (
            ("budget_policy", "child_lease_required"),
            ("cancellation", "cooperative_required"),
            ("replay_modes", ["deterministic", "seeded"]),
            ("effect_kinds", ["solver"]),
            ("authority", "producer_report"),
        ):
            with self.subTest(field=field):
                value = self.valid()
                value["operations"][0][field] = replacement
                self.rebind(value)
                expected = "effect" if field == "effect_kinds" else "operation"
                self.assert_invalid(value, expected)

    def test_effect_declarations_require_policy_and_process_isolation(self) -> None:
        malformed = self.valid()
        malformed["effects"][4]["mode"] = "declared"
        self.rebind(malformed)
        self.assert_invalid(malformed, "effect")
        isolated = self.valid()
        isolated["effects"][4] = {
            "kind": "solver",
            "mode": "declared",
            "policy_id": "org.mathhead.solver-policy",
            "reason": "bounded solver execution",
        }
        isolated["operations"][1]["effect_kinds"] = ["solver"]
        isolated["lifecycle"]["isolation"] = "subprocess_required"
        isolated["lifecycle"]["shutdown_timeout_us"] = 1000000
        self.rebind(isolated)
        plugin.validate_theory_plugin(isolated, self.schema)
        in_process = copy.deepcopy(isolated)
        in_process["lifecycle"]["isolation"] = "in_process"
        in_process["lifecycle"]["shutdown_timeout_us"] = 0
        self.rebind(in_process)
        self.assert_invalid(in_process, "effect")

    def test_lifecycle_replay_seed_policy_basis_and_limits_fail_closed(self) -> None:
        concurrency = self.valid()
        concurrency["lifecycle"]["maximum_concurrency"] = 2
        self.rebind(concurrency)
        self.assert_invalid(concurrency, "lifecycle")
        persistence = self.valid()
        persistence["lifecycle"]["state_persistence"] = "content_addressed"
        self.rebind(persistence)
        self.assert_invalid(persistence, "lifecycle")
        seed = self.valid()
        seed["replay"]["seed_policy"] = "forbidden"
        self.rebind(seed)
        self.assert_invalid(seed, "replay")
        basis = self.valid()
        basis["display_name"] = "Changed without replay rebind"
        self.assert_invalid(basis, "replay")
        limits = self.valid()
        limits["limits"]["entities"] -= 1
        self.rebind(limits)
        self.assert_invalid(limits, "budget")

    def test_global_identity_collision_and_fragment_shape_fail(self) -> None:
        collision = self.valid()
        collision["capabilities"][0]["capability_id"] = "component_checker"
        self.rebind(collision)
        self.assert_invalid(collision, "identity")
        fragment = self.fragment()
        fragment["unknown"] = 1
        with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
            plugin.route_fragment(self.valid(), fragment, kind="decision")
        self.assertEqual(caught.exception.kind, "routing")
        with self.assertRaises(plugin.TheoryPluginValidationError) as caught:
            plugin.route_fragment(self.valid(), self.fragment(), kind="unknown")
        self.assertEqual(caught.exception.kind, "routing")

    def test_contract_constants_and_cli_minimal_descriptor(self) -> None:
        self.assertEqual(plugin.CONTRACT_ID, "MH-C-THEORY-PLUGIN-001")
        self.assertEqual(plugin.main([]), 0)


if __name__ == "__main__":
    unittest.main()
