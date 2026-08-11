from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_problem_ir_contract as problem_ir  # noqa: E402


class ProblemIRContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema, cls.schema_raw = problem_ir.load_json(ROOT / problem_ir.SCHEMA_PATH)

    def valid(self) -> dict[str, object]:
        return problem_ir.minimal_problem_ir()

    def assert_invalid(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(problem_ir.ProblemIRValidationError) as caught:
            problem_ir.validate_problem_ir(value, self.schema)
        self.assertEqual(caught.exception.kind, kind)

    def test_normative_schema_identity_and_closed_root(self) -> None:
        self.assertEqual(hashlib.sha256(self.schema_raw).hexdigest(), problem_ir.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(set(self.schema["required"]), problem_ir.ROOT_FIELDS)
        self.assertFalse(self.schema["additionalProperties"])
        problem_ir.validate_problem_ir(self.valid(), self.schema)

    def test_unknown_missing_and_malformed_tagged_union_fail(self) -> None:
        unknown = self.valid()
        unknown["unknown"] = True
        self.assert_invalid(unknown, "schema")

        missing = self.valid()
        missing.pop("readings")
        self.assert_invalid(missing, "schema")

        malformed = self.valid()
        malformed["expressions"][0]["operator"] = "mathhead.add"
        self.assert_invalid(malformed, "schema")

    def test_duplicate_keys_and_noncanonical_file_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(problem_ir.ProblemIRValidationError) as caught:
                problem_ir.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")

            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.valid(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(problem_ir.ProblemIRValidationError) as caught:
                problem_ir.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")

    def test_ids_are_unique_globally_and_registries_are_sorted(self) -> None:
        duplicate = self.valid()
        duplicate["goals"][0]["id"] = "domain_integer"
        self.assert_invalid(duplicate, "identity")

        unsorted = self.valid()
        unsorted["domains"].append(
            {"id": "domain_boolean", "kind": "builtin", "name": "boolean", "span_ids": []}
        )
        self.assert_invalid(unsorted, "canonical")

    def test_reference_integrity_and_span_bounds_fail_closed(self) -> None:
        missing = self.valid()
        missing["goals"][0]["statement_id"] = "statement_missing"
        self.assert_invalid(missing, "reference")

        span = self.valid()
        span["source_documents"] = [
            {
                "id": "source_input",
                "media_type": "text/plain",
                "language": "tr",
                "sha256": "0" * 64,
                "byte_length": 3,
            }
        ]
        span["source_spans"] = [
            {
                "id": "span_goal",
                "source_id": "source_input",
                "start_byte": 1,
                "end_byte": 4,
            }
        ]
        self.assert_invalid(span, "span")

    def test_set_valued_references_are_sorted_but_goal_order_is_preserved(self) -> None:
        value = self.valid()
        value["source_documents"] = [
            {
                "id": "source_input",
                "media_type": "text/plain",
                "language": "en",
                "sha256": "0" * 64,
                "byte_length": 2,
            }
        ]
        value["source_spans"] = [
            {"id": "span_a", "source_id": "source_input", "start_byte": 0, "end_byte": 1},
            {"id": "span_b", "source_id": "source_input", "start_byte": 1, "end_byte": 2},
        ]
        value["goals"][0]["span_ids"] = ["span_b", "span_a"]
        self.assert_invalid(value, "canonical")

        ordered = self.valid()
        ordered["goals"].append(
            {
                "id": "goal_second",
                "statement_id": "statement_forall",
                "mode": "refute",
                "span_ids": [],
            }
        )
        ordered["goals"].sort(key=lambda item: item["id"])
        ordered["readings"][0]["goal_ids"] = ["goal_second", "goal_reflexive"]
        problem_ir.validate_problem_ir(ordered, self.schema)

    def test_unicode_nfc_nul_and_float_extensions_fail(self) -> None:
        decomposed = self.valid()
        decomposed["readings"][0]["label"] = "es\u0327it"
        self.assert_invalid(decomposed, "canonical")

        nul = self.valid()
        nul["readings"][0]["label"] = "bad\x00label"
        self.assert_invalid(nul, "canonical")

        floating = self.valid()
        floating["extensions"] = {"org.mathhead.test": {"score": 0.5}}
        self.assert_invalid(floating, "schema")

    def test_exact_literal_canonicalization_rejects_equivalent_spellings(self) -> None:
        integer = self.valid()
        integer["expressions"][0] = {
            "id": "expression_x",
            "kind": "literal",
            "domain_id": "domain_integer",
            "literal_type": "integer",
            "value": "01",
            "span_ids": [],
        }
        self.assert_invalid(integer, "literal")

        rational = self.valid()
        rational["domains"].append(
            {"id": "domain_rational", "kind": "builtin", "name": "rational", "span_ids": []}
        )
        rational["domains"].sort(key=lambda item: item["id"])
        rational["expressions"][0] = {
            "id": "expression_x",
            "kind": "literal",
            "domain_id": "domain_rational",
            "literal_type": "rational",
            "value": "2/4",
            "span_ids": [],
        }
        self.assert_invalid(rational, "literal")

    def test_relation_and_logical_operator_arity_is_exact(self) -> None:
        relation = self.valid()
        relation["relations"][0]["operand_expr_ids"].append("expression_x")
        self.assert_invalid(relation, "relation")

        logical = self.valid()
        logical["statements"].append(
            {
                "id": "statement_not",
                "kind": "logical",
                "operator": "not",
                "operand_statement_ids": ["statement_body", "statement_forall"],
                "span_ids": [],
            }
        )
        logical["statements"].sort(key=lambda item: item["id"])
        self.assert_invalid(logical, "statement")

    def test_expression_relation_and_definition_domains_are_typed(self) -> None:
        variable = self.valid()
        variable["domains"].append(
            {"id": "domain_real", "kind": "builtin", "name": "real", "span_ids": []}
        )
        variable["domains"].sort(key=lambda item: item["id"])
        variable["expressions"][0]["domain_id"] = "domain_real"
        self.assert_invalid(variable, "expression")

        equality = self.valid()
        equality["domains"].append(
            {"id": "domain_real", "kind": "builtin", "name": "real", "span_ids": []}
        )
        equality["domains"].sort(key=lambda item: item["id"])
        equality["expressions"].append(
            {
                "id": "expression_real",
                "kind": "literal",
                "domain_id": "domain_real",
                "literal_type": "integer",
                "value": "1",
                "span_ids": [],
            }
        )
        equality["expressions"].sort(key=lambda item: item["id"])
        equality["relations"][0]["operand_expr_ids"][1] = "expression_real"
        self.assert_invalid(equality, "relation")

        definition = self.valid()
        definition["variables"].append(
            {
                "id": "variable_parameter",
                "name": "p",
                "domain_id": "domain_integer",
                "role": "parameter",
                "span_ids": [],
            }
        )
        definition["variables"].sort(key=lambda item: item["id"])
        definition["expressions"].append(
            {
                "id": "expression_parameter",
                "kind": "variable",
                "domain_id": "domain_integer",
                "variable_id": "variable_parameter",
                "span_ids": [],
            }
        )
        definition["expressions"].sort(key=lambda item: item["id"])
        definition["definitions"] = [
            {
                "id": "definition_bad",
                "name": "bad",
                "parameter_variable_ids": ["variable_parameter"],
                "result_domain_id": None,
                "body": {"kind": "expression", "expression_id": "expression_parameter"},
                "recursive": False,
                "span_ids": [],
            }
        ]
        definition["readings"][0]["definition_ids"] = ["definition_bad"]
        self.assert_invalid(definition, "definition")

    def test_expression_statement_and_domain_cycles_fail(self) -> None:
        statement_cycle = self.valid()
        statement_cycle["statements"].append(
            {
                "id": "statement_cycle",
                "kind": "logical",
                "operator": "not",
                "operand_statement_ids": ["statement_cycle"],
                "span_ids": [],
            }
        )
        statement_cycle["statements"].sort(key=lambda item: item["id"])
        self.assert_invalid(statement_cycle, "cycle")

        domain_cycle = self.valid()
        domain_cycle["domains"] = [
            {
                "id": "domain_integer",
                "kind": "collection",
                "collection": "set",
                "element_domain_id": "domain_integer",
                "finiteness": "unknown",
                "span_ids": [],
            }
        ]
        self.assert_invalid(domain_cycle, "cycle")

    def test_bound_variables_cannot_escape_or_have_two_binders(self) -> None:
        escape = self.valid()
        escape["goals"][0]["statement_id"] = "statement_body"
        self.assert_invalid(escape, "scope")

        duplicate_owner = self.valid()
        duplicate_owner["statements"].append(
            {
                "id": "statement_second_quantifier",
                "kind": "quantified",
                "quantifier": "exists",
                "variable_ids": ["variable_x"],
                "body_statement_id": "statement_body",
                "span_ids": [],
            }
        )
        duplicate_owner["statements"].sort(key=lambda item: item["id"])
        self.assert_invalid(duplicate_owner, "scope")

    def test_definition_parameters_have_one_scope_owner(self) -> None:
        value = self.valid()
        value["variables"].append(
            {
                "id": "variable_parameter",
                "name": "p",
                "domain_id": "domain_integer",
                "role": "parameter",
                "span_ids": [],
            }
        )
        value["variables"].sort(key=lambda item: item["id"])
        value["expressions"].append(
            {
                "id": "expression_parameter",
                "kind": "variable",
                "domain_id": "domain_integer",
                "variable_id": "variable_parameter",
                "span_ids": [],
            }
        )
        value["expressions"].sort(key=lambda item: item["id"])
        value["definitions"] = [
            {
                "id": "definition_identity",
                "name": "identity",
                "parameter_variable_ids": ["variable_parameter"],
                "result_domain_id": "domain_integer",
                "body": {"kind": "expression", "expression_id": "expression_parameter"},
                "recursive": False,
                "span_ids": [],
            }
        ]
        value["readings"][0]["definition_ids"] = ["definition_identity"]
        problem_ir.validate_problem_ir(value, self.schema)

        orphan = copy.deepcopy(value)
        orphan["definitions"] = []
        orphan["readings"][0]["definition_ids"] = []
        self.assert_invalid(orphan, "scope")

    def test_unresolved_ambiguity_preserves_complete_alternative_readings(self) -> None:
        value = self.valid()
        value["goals"].append(
            {
                "id": "goal_alternative",
                "statement_id": "statement_forall",
                "mode": "refute",
                "span_ids": [],
            }
        )
        value["goals"].sort(key=lambda item: item["id"])
        base = value["readings"][0]
        base["id"] = "reading_base"
        base["label"] = "Universal reading"
        alternative = {
            "id": "reading_other",
            "label": "Alternative goal-mode reading",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_alternative"],
            "difference_from": "reading_base",
            "differences": [
                {
                    "kind": "quantifier",
                    "summary": "The intended claim mode remains unresolved.",
                    "affected_ids": ["goal_alternative"],
                    "span_ids": [],
                }
            ],
            "span_ids": [],
        }
        value["readings"] = [base, alternative]
        value["ambiguity"] = {
            "status": "unresolved",
            "candidate_reading_ids": ["reading_base", "reading_other"],
            "selected_reading_id": None,
            "required_choice": "Choose the intended claim mode.",
        }
        problem_ir.validate_problem_ir(value, self.schema)

        silently_selected = copy.deepcopy(value)
        silently_selected["ambiguity"]["selected_reading_id"] = "reading_base"
        self.assert_invalid(silently_selected, "ambiguity")

        unexplained = copy.deepcopy(value)
        unexplained["readings"][1]["differences"] = []
        self.assert_invalid(unexplained, "ambiguity")

    def test_ambiguity_candidates_must_name_every_reading_in_canonical_order(self) -> None:
        value = self.valid()
        value["ambiguity"]["candidate_reading_ids"] = []
        self.assert_invalid(value, "schema")

        value = self.valid()
        value["ambiguity"]["status"] = "unresolved"
        value["ambiguity"]["selected_reading_id"] = None
        value["ambiguity"]["required_choice"] = "Choose."
        self.assert_invalid(value, "ambiguity")

    def test_canonical_round_trip_and_sha256_identity_are_stable(self) -> None:
        value = self.valid()
        payload = problem_ir.canonical_bytes(value)
        restored = json.loads(payload)
        problem_ir.validate_problem_ir(restored, self.schema)
        self.assertEqual(payload, problem_ir.canonical_bytes(restored))
        self.assertEqual(
            problem_ir.canonical_sha256(value),
            "9ee660a1e2793852c9d14071aa2785413e1653c08d14bb27a43bbf82d3e0494c",
        )


if __name__ == "__main__":
    unittest.main()
