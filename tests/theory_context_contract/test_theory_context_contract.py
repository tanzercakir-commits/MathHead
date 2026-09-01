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

from tools import validate_theory_context_contract as theory  # noqa: E402


class TheoryContextContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema, cls.schema_raw = theory.load_json(ROOT / theory.SCHEMA_PATH)

    def valid(self) -> dict[str, object]:
        return theory.minimal_theory_context()

    def rebind(self, value: dict[str, object]) -> None:
        value["consistency"]["basis_sha256"] = theory.consistency_basis_sha256(value)

    def assert_invalid(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(theory.TheoryContextValidationError) as caught:
            theory.validate_theory_context(value, self.schema)
        self.assertEqual(caught.exception.kind, kind)

    def add_import(
        self,
        value: dict[str, object],
        identifier: str,
        *,
        alias: str | None = None,
        dependencies: list[str] | None = None,
        namespace: str | None = None,
    ) -> dict[str, object]:
        imported = {
            "id": identifier,
            "alias": alias,
            "context_id": f"context_{identifier}",
            "namespace": namespace or f"org.mathhead.{identifier.replace('_', '-')}",
            "revision": 0,
            "context_sha256": hashlib.sha256(identifier.encode()).hexdigest(),
            "exports_sha256": hashlib.sha256(f"exports:{identifier}".encode()).hexdigest(),
            "dependency_import_ids": dependencies or [],
        }
        value["imports"].append(imported)
        value["imports"].sort(key=lambda item: item["id"])
        return imported

    def add_definition(self, value: dict[str, object], identifier: str) -> None:
        suffix = identifier.removeprefix("declaration_").title().replace("_", "")
        value["declarations"].append(
            {
                "id": identifier,
                "kind": "definition",
                "namespace": value["namespace"],
                "name": suffix,
                "qualified_name": f"{value['namespace']}.{suffix}",
                "visibility": "public",
                "content": {
                    "artifact_id": "artifact_problem",
                    "entity_kind": "definition",
                    "entity_id": f"definition_{identifier}",
                },
                "dependency_refs": [],
                "epistemic": {"status": "definitional"},
                "origin": None,
                "scope_id": None,
                "extensions": {},
            }
        )
        value["declarations"].sort(key=lambda item: item["id"])

    def derive(
        self,
        value: dict[str, object],
        *,
        mode: str = "extension",
        add: bool = True,
        retire: str | None = None,
    ) -> None:
        parent = copy.deepcopy(value)
        fingerprints = [
            {"id": item["id"], "sha256": theory.declaration_sha256(item)}
            for item in parent["declarations"]
        ]
        value["revision"] = {
            "number": 1,
            "mode": mode,
            "parent": {
                "context_id": parent["context_id"],
                "revision": 0,
                "context_sha256": theory.canonical_sha256(parent),
                "declaration_fingerprints": fingerprints,
            },
            "retired_declaration_ids": [] if retire is None else [retire],
        }
        if retire is not None:
            value["declarations"] = [item for item in value["declarations"] if item["id"] != retire]
        if add:
            self.add_definition(value, "declaration_new")
        self.rebind(value)

    def test_normative_schema_identity_closed_root_and_canonical_roundtrip(self) -> None:
        self.assertEqual(hashlib.sha256(self.schema_raw).hexdigest(), theory.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(set(self.schema["required"]), theory.ROOT_FIELDS)
        self.assertFalse(self.schema["additionalProperties"])
        value = self.valid()
        theory.validate_theory_context(value, self.schema)
        self.assertEqual(
            json.loads(theory.canonical_bytes(value)),
            value,
        )
        self.assertEqual(
            theory.canonical_sha256(value),
            hashlib.sha256(theory.canonical_bytes(value)).hexdigest(),
        )

    def test_unknown_missing_and_malformed_tagged_union_fail(self) -> None:
        unknown = self.valid()
        unknown["unknown"] = True
        self.assert_invalid(unknown, "schema")

        missing = self.valid()
        missing.pop("namespace")
        self.assert_invalid(missing, "schema")

        malformed = self.valid()
        malformed["consistency"]["status"] = "consistent"
        self.assert_invalid(malformed, "schema")

    def test_duplicate_keys_and_noncanonical_file_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(theory.TheoryContextValidationError) as caught:
                theory.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")

            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.valid(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(theory.TheoryContextValidationError) as caught:
                theory.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")

            canonical = Path(directory) / "canonical.json"
            canonical.write_bytes(theory.canonical_bytes(self.valid()))
            loaded, raw = theory.load_json(canonical, require_canonical=True)
            self.assertEqual(raw, theory.canonical_bytes(loaded))

    def test_unicode_nul_float_integer_key_and_nesting_budgets_fail(self) -> None:
        decomposed = self.valid()
        decomposed["consistency"]["reason"] = "es\u0327it"
        self.assert_invalid(decomposed, "canonical")

        nul = self.valid()
        nul["consistency"]["reason"] = "bad\x00reason"
        self.assert_invalid(nul, "canonical")

        floating = self.valid()
        floating["extensions"] = {"org.mathhead.test": {"score": 0.5}}
        self.assert_invalid(floating, "schema")

        integer = self.valid()
        integer["extensions"] = {"org.mathhead.test": {"count": theory.MAX_JSON_INTEGER + 1}}
        self.assert_invalid(integer, "budget")

        long_key = self.valid()
        long_key["extensions"] = {
            "org.mathhead.test": {"a" * (theory.MAX_STRING_CODEPOINTS + 1): None}
        }
        self.assert_invalid(long_key, "budget")

        nested: object = None
        for _ in range(theory.MAX_CANONICAL_NESTING + 1):
            nested = [nested]
        deep = self.valid()
        deep["extensions"] = {"org.mathhead.test": nested}
        self.assert_invalid(deep, "budget")

    def test_registry_order_global_identity_and_combined_budget_fail(self) -> None:
        unsorted = self.valid()
        unsorted["declarations"].reverse()
        self.assert_invalid(unsorted, "canonical")

        collision = self.valid()
        collision["declarations"][0]["id"] = "artifact_problem"
        self.assert_invalid(collision, "identity")

        with mock.patch.object(theory, "MAX_ENTITIES", 7):
            self.assert_invalid(self.valid(), "budget")

    def test_artifact_identity_kind_schema_and_content_binding_fail(self) -> None:
        duplicate = self.valid()
        duplicate["artifacts"][1].update(copy.deepcopy(duplicate["artifacts"][0]))
        duplicate["artifacts"][1]["id"] = "artifact_evidence"
        self.assert_invalid(duplicate, "identity")

        wrong_kind = self.valid()
        wrong_kind["artifacts"][2]["kind"] = "other"
        self.assert_invalid(wrong_kind, "artifact")

        wrong_content = self.valid()
        wrong_content["declarations"][0]["content"]["artifact_id"] = "artifact_evidence"
        self.assert_invalid(wrong_content, "artifact")

    def test_import_alias_reference_reachability_and_self_import_rules(self) -> None:
        alias = self.valid()
        alias["imports"][0]["alias"] = None
        self.assert_invalid(alias, "import")

        reference = self.valid()
        reference["imports"][0]["dependency_import_ids"] = ["import_missing"]
        self.assert_invalid(reference, "reference")

        orphan = self.valid()
        self.add_import(orphan, "import_orphan")
        self.assert_invalid(orphan, "import")

        logical_self = self.valid()
        logical_self["imports"][0]["context_id"] = logical_self["context_id"]
        self.assert_invalid(logical_self, "import")

        duplicate_namespace = self.valid()
        self.add_import(
            duplicate_namespace,
            "import_other",
            namespace="org.mathhead.base",
        )
        duplicate_namespace["imports"][0]["dependency_import_ids"] = ["import_other"]
        self.assert_invalid(duplicate_namespace, "import")

    def test_import_cycles_and_dependency_depth_fail_closed(self) -> None:
        cyclic = self.valid()
        self.add_import(cyclic, "import_transitive", dependencies=["import_base"])
        cyclic["imports"][0]["dependency_import_ids"] = ["import_transitive"]
        self.assert_invalid(cyclic, "cycle")

        deep = self.valid()
        self.add_import(deep, "import_middle", dependencies=["import_tail"])
        self.add_import(deep, "import_tail")
        deep["imports"][0]["dependency_import_ids"] = ["import_middle"]
        with mock.patch.object(theory, "MAX_GRAPH_NESTING", 1):
            self.assert_invalid(deep, "budget")

    def test_namespace_qualified_name_and_alias_collisions_fail(self) -> None:
        escaped = self.valid()
        escaped["declarations"][0]["namespace"] = "org.other.example"
        escaped["declarations"][0]["qualified_name"] = "org.other.example.IdentityAxiom"
        self.assert_invalid(escaped, "namespace")

        mismatch = self.valid()
        mismatch["declarations"][0]["qualified_name"] = "org.mathhead.example.Other"
        self.assert_invalid(mismatch, "namespace")

        duplicate = self.valid()
        duplicate["declarations"][1]["namespace"] = duplicate["declarations"][0]["namespace"]
        duplicate["declarations"][1]["name"] = duplicate["declarations"][0]["name"]
        duplicate["declarations"][1]["qualified_name"] = duplicate["declarations"][0][
            "qualified_name"
        ]
        self.assert_invalid(duplicate, "namespace")

        aliases = self.valid()
        self.add_import(aliases, "import_other", alias="base")
        aliases["direct_import_ids"].append("import_other")
        aliases["direct_import_ids"].sort()
        self.assert_invalid(aliases, "import")

    def test_declaration_kind_content_epistemics_and_origins_fail(self) -> None:
        axiom = self.valid()
        axiom["declarations"][0]["epistemic"] = {
            "status": "unchecked",
            "reason": "An axiom cannot be silently downgraded or promoted.",
        }
        self.assert_invalid(axiom, "epistemic")

        definition = self.valid()
        definition["declarations"][1]["content"]["entity_kind"] = "statement"
        self.assert_invalid(definition, "epistemic")

        imported = self.valid()
        imported["declarations"][2]["origin"] = None
        self.assert_invalid(imported, "epistemic")

        origin_dependency = self.valid()
        origin_dependency["declarations"][2]["origin"]["declaration_sha256"] = "9" * 64
        self.assert_invalid(origin_dependency, "reference")

    def test_checker_attestations_bind_evidence_result_contract_and_trust(self) -> None:
        evidence = self.valid()
        evidence["declarations"][3]["epistemic"]["evidence_artifact_id"] = "artifact_checker"
        self.assert_invalid(evidence, "epistemic")

        result = self.valid()
        result["declarations"][3]["epistemic"]["checker_result_artifact_id"] = "artifact_evidence"
        self.assert_invalid(result, "epistemic")

        trust = self.valid()
        trust["declarations"][3]["epistemic"]["trust_dependency_sha256s"] = [
            "9" * 64,
            "8" * 64,
        ]
        self.assert_invalid(trust, "canonical")

        malformed_contract = self.valid()
        malformed_contract["declarations"][3]["epistemic"]["checker_contract_id"] = "checker"
        self.assert_invalid(malformed_contract, "schema")

    def test_declaration_reference_integrity_cycles_and_depth_fail(self) -> None:
        missing = self.valid()
        missing["declarations"][3]["dependency_refs"][0]["declaration_id"] = "declaration_missing"
        self.assert_invalid(missing, "canonical")

        cycle = self.valid()
        cycle["declarations"][0]["dependency_refs"] = [
            {"kind": "local", "declaration_id": "declaration_lemma"}
        ]
        self.assert_invalid(cycle, "cycle")

        deep = self.valid()
        deep["declarations"][0]["dependency_refs"] = [
            {"kind": "local", "declaration_id": "declaration_definition"}
        ]
        with mock.patch.object(theory, "MAX_GRAPH_NESTING", 1):
            self.assert_invalid(deep, "budget")

    def test_theory_and_local_scope_rules_prevent_authority_escape(self) -> None:
        hypothesis_in_theory = self.valid()
        hypothesis_in_theory["declarations"][0].update(
            {
                "kind": "hypothesis",
                "visibility": "private",
                "scope_id": "scope_local",
                "epistemic": {"status": "assumed_local", "scope_id": "scope_local"},
            }
        )
        self.assert_invalid(hypothesis_in_theory, "scope")

        local = self.valid()
        local["scope"] = {
            "kind": "local",
            "id": "scope_local",
            "parent_theory_sha256": "5" * 64,
        }
        local["declarations"][0].update(
            {
                "kind": "hypothesis",
                "visibility": "private",
                "scope_id": "scope_local",
                "epistemic": {"status": "assumed_local", "scope_id": "scope_local"},
            }
        )
        local["declarations"][3]["scope_id"] = "scope_local"
        local["declarations"][3]["visibility"] = "private"
        self.rebind(local)
        theory.validate_theory_context(local, self.schema)

        public_local = copy.deepcopy(local)
        public_local["declarations"][3]["visibility"] = "public"
        self.assert_invalid(public_local, "scope")

        escaping = copy.deepcopy(local)
        escaping["declarations"][3]["scope_id"] = None
        self.assert_invalid(escaping, "scope")

        parent = copy.deepcopy(local)
        parent["scope"]["parent_theory_sha256"] = "9" * 64
        self.assert_invalid(parent, "scope")

    def test_revision_extension_is_additive_and_stable_ids_are_immutable(self) -> None:
        extension = self.valid()
        self.derive(extension)
        theory.validate_theory_context(extension, self.schema)

        no_change = self.valid()
        self.derive(no_change, add=False)
        self.assert_invalid(no_change, "revision")

        retired = self.valid()
        self.derive(
            retired,
            add=False,
            retire="declaration_imported",
        )
        self.assert_invalid(retired, "revision")

        changed = self.valid()
        self.derive(changed)
        changed["declarations"][1]["name"] = "ChangedIdentity"
        changed["declarations"][1]["qualified_name"] = "org.mathhead.example.ChangedIdentity"
        self.rebind(changed)
        self.assert_invalid(changed, "revision")

    def test_revision_mode_can_explicitly_retire_a_parent_declaration(self) -> None:
        revision = self.valid()
        self.derive(
            revision,
            mode="revision",
            add=False,
            retire="declaration_imported",
        )
        theory.validate_theory_context(revision, self.schema)

        missing_parent = self.valid()
        missing_parent["revision"] = {
            "number": 1,
            "mode": "revision",
            "parent": None,
            "retired_declaration_ids": [],
        }
        self.rebind(missing_parent)
        self.assert_invalid(missing_parent, "revision")

        wrong_number = self.valid()
        self.derive(wrong_number)
        wrong_number["revision"]["number"] = 2
        self.rebind(wrong_number)
        self.assert_invalid(wrong_number, "revision")

    def test_consistency_basis_binds_context_revision_and_semantic_inputs(self) -> None:
        value = self.valid()
        value["consistency"]["basis_sha256"] = "9" * 64
        self.assert_invalid(value, "consistency")

        base = self.valid()
        original = base["consistency"]["basis_sha256"]
        base["revision"]["number"] = 1
        self.assertNotEqual(theory.consistency_basis_sha256(base), original)

        annotation = self.valid()
        original = annotation["consistency"]["basis_sha256"]
        annotation["extensions"] = {"org.mathhead.note": "non-semantic annotation"}
        self.assertEqual(theory.consistency_basis_sha256(annotation), original)

    def test_consistency_variants_are_bounded_and_checker_attested(self) -> None:
        local_ref = {"kind": "local", "declaration_id": "declaration_axiom"}

        unknown = self.valid()
        unknown["consistency"] = {
            "status": "unknown",
            "basis_sha256": theory.consistency_basis_sha256(unknown),
            "covered_declaration_refs": [local_ref],
            "checker_result_artifact_id": None,
            "reason": "A bounded attempt returned no verdict.",
        }
        theory.validate_theory_context(unknown, self.schema)

        fragment = self.valid()
        fragment["consistency"] = {
            "status": "fragment_consistent",
            "basis_sha256": theory.consistency_basis_sha256(fragment),
            "fragment_id": "org.mathhead.fragment",
            "covered_declaration_refs": [local_ref],
            "evidence_artifact_id": "artifact_evidence",
            "checker_result_artifact_id": "artifact_checker",
            "checker_contract_id": "MH-C-CHECKER-001",
            "checker_contract_sha256": "7" * 64,
            "trust_dependency_sha256s": ["8" * 64],
        }
        theory.validate_theory_context(fragment, self.schema)

        inconsistent = self.valid()
        inconsistent["consistency"] = {
            "status": "inconsistent",
            "basis_sha256": theory.consistency_basis_sha256(inconsistent),
            "conflict_declaration_refs": [local_ref],
            "evidence_artifact_id": "artifact_evidence",
            "checker_result_artifact_id": "artifact_checker",
            "checker_contract_id": "MH-C-CHECKER-001",
            "checker_contract_sha256": "7" * 64,
            "trust_dependency_sha256s": ["8" * 64],
        }
        theory.validate_theory_context(inconsistent, self.schema)

        wrong_result = copy.deepcopy(fragment)
        wrong_result["consistency"]["checker_result_artifact_id"] = "artifact_evidence"
        self.assert_invalid(wrong_result, "epistemic")

        missing_ref = copy.deepcopy(fragment)
        missing_ref["consistency"]["covered_declaration_refs"] = [
            {"kind": "local", "declaration_id": "declaration_missing"}
        ]
        self.assert_invalid(missing_ref, "reference")


if __name__ == "__main__":
    unittest.main()
