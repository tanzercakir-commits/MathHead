from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import mathhead.problem_intake as problem_intake_module  # noqa: E402
from mathhead.problem_intake import (  # noqa: E402
    CONTRACT_SHA256,
    ProblemIntakeResult,
    ProblemIntakeValidationError,
    canonical_problem_ir_bytes,
    intake_problem,
    parse_problem_intake_result,
    problem_intake_result_bytes,
    problem_intake_result_sha256,
    validate_problem_intake_result,
)
from tools import validate_problem_ir_contract as independent  # noqa: E402


SCHEMA_ROOT = ROOT / "docs/contracts/schemas"


def specification(problem: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "schema": "mathhead.problem-intake.v1",
        "problem": problem if problem is not None else independent.minimal_problem_ir(),
    }


def all_variants_problem() -> dict[str, object]:
    value = independent.minimal_problem_ir()
    value["domains"].extend(
        [
            {"id": "domain_boolean", "kind": "builtin", "name": "boolean", "span_ids": []},
            {
                "id": "domain_collection",
                "kind": "collection",
                "collection": "set",
                "element_domain_id": "domain_integer",
                "finiteness": "finite",
                "span_ids": [],
            },
            {
                "id": "domain_function",
                "kind": "function",
                "parameter_domain_ids": ["domain_integer"],
                "result_domain_id": "domain_integer",
                "total": True,
                "span_ids": [],
            },
            {"id": "domain_natural", "kind": "builtin", "name": "natural", "span_ids": []},
            {
                "id": "domain_product",
                "kind": "product",
                "factor_domain_ids": ["domain_integer", "domain_boolean"],
                "span_ids": [],
            },
            {"id": "domain_rational", "kind": "builtin", "name": "rational", "span_ids": []},
            {"id": "domain_real", "kind": "builtin", "name": "real", "span_ids": []},
            {
                "id": "domain_structure",
                "kind": "structure",
                "theory_id": "org.mathhead.test.structure",
                "parameter_domain_ids": ["domain_integer"],
                "parameter_expr_ids": ["expression_one"],
                "span_ids": [],
            },
        ]
    )
    value["variables"].extend(
        [
            {
                "id": "variable_exists",
                "name": "z",
                "domain_id": "domain_integer",
                "role": "bound",
                "span_ids": [],
            },
            {
                "id": "variable_free",
                "name": "y",
                "domain_id": "domain_integer",
                "role": "free",
                "span_ids": [],
            },
            {
                "id": "variable_parameter",
                "name": "p",
                "domain_id": "domain_integer",
                "role": "parameter",
                "span_ids": [],
            },
        ]
    )
    value["expressions"].extend(
        [
            {
                "id": "expression_apply",
                "kind": "apply",
                "domain_id": "domain_integer",
                "operator": "org.mathhead.test.successor",
                "argument_expr_ids": ["expression_one"],
                "attributes": {"mode": "exact"},
                "span_ids": [],
            },
            {
                "id": "expression_boolean",
                "kind": "literal",
                "domain_id": "domain_boolean",
                "literal_type": "boolean",
                "value": "true",
                "span_ids": [],
            },
            {
                "id": "expression_collection",
                "kind": "collection",
                "domain_id": "domain_collection",
                "element_expr_ids": ["expression_one", "expression_two"],
                "span_ids": [],
            },
            {
                "id": "expression_one",
                "kind": "literal",
                "domain_id": "domain_integer",
                "literal_type": "integer",
                "value": "1",
                "span_ids": [],
            },
            {
                "id": "expression_parameter",
                "kind": "variable",
                "domain_id": "domain_integer",
                "variable_id": "variable_parameter",
                "span_ids": [],
            },
            {
                "id": "expression_rational",
                "kind": "literal",
                "domain_id": "domain_rational",
                "literal_type": "rational",
                "value": "1/2",
                "span_ids": [],
            },
            {
                "id": "expression_real_lower",
                "kind": "literal",
                "domain_id": "domain_real",
                "literal_type": "integer",
                "value": "0",
                "span_ids": [],
            },
            {
                "id": "expression_real_upper",
                "kind": "literal",
                "domain_id": "domain_real",
                "literal_type": "integer",
                "value": "2",
                "span_ids": [],
            },
            {
                "id": "expression_string",
                "kind": "literal",
                "domain_id": "domain_structure",
                "literal_type": "string",
                "value": "symbol",
                "span_ids": [],
            },
            {
                "id": "expression_tuple",
                "kind": "tuple",
                "domain_id": "domain_product",
                "element_expr_ids": ["expression_one", "expression_boolean"],
                "span_ids": [],
            },
            {
                "id": "expression_two",
                "kind": "literal",
                "domain_id": "domain_integer",
                "literal_type": "integer",
                "value": "2",
                "span_ids": [],
            },
        ]
    )
    value["domains"].extend(
        [
            {
                "id": "domain_finite",
                "kind": "finite",
                "element_domain_id": "domain_integer",
                "element_expr_ids": ["expression_two", "expression_one"],
                "cardinality": 2,
                "span_ids": [],
            },
            {
                "id": "domain_interval",
                "kind": "interval",
                "base": "real",
                "lower_expr_id": "expression_real_lower",
                "lower_closed": True,
                "upper_expr_id": "expression_real_upper",
                "upper_closed": False,
                "span_ids": [],
            },
            {
                "id": "domain_modular",
                "kind": "modular",
                "modulus_expr_id": "expression_two",
                "span_ids": [],
            },
        ]
    )
    value["statements"].append(
        {"id": "statement_truth", "kind": "truth", "value": True, "span_ids": []}
    )
    value["expressions"].append(
        {
            "id": "expression_conditional",
            "kind": "conditional",
            "domain_id": "domain_integer",
            "condition_statement_id": "statement_truth",
            "then_expr_id": "expression_one",
            "else_expr_id": "expression_two",
            "span_ids": [],
        }
    )
    value["relations"].extend(
        [
            {
                "id": "relation_congruent",
                "kind": "congruent",
                "operand_expr_ids": ["expression_one", "expression_one", "expression_two"],
                "span_ids": [],
            },
            {
                "id": "relation_divides",
                "kind": "divides",
                "operand_expr_ids": ["expression_one", "expression_two"],
                "span_ids": [],
            },
            {
                "id": "relation_less",
                "kind": "less",
                "operand_expr_ids": ["expression_one", "expression_two"],
                "span_ids": [],
            },
            {
                "id": "relation_member",
                "kind": "member",
                "operand_expr_ids": ["expression_one", "expression_collection"],
                "span_ids": [],
            },
            {
                "id": "relation_predicate",
                "kind": "predicate",
                "predicate": "org.mathhead.test.predicate",
                "operand_expr_ids": ["expression_apply"],
                "span_ids": [],
            },
        ]
    )
    for relation_id in (
        "relation_congruent",
        "relation_divides",
        "relation_less",
        "relation_member",
        "relation_predicate",
    ):
        value["statements"].append(
            {
                "id": "statement_" + relation_id.removeprefix("relation_"),
                "kind": "relation",
                "relation_id": relation_id,
                "span_ids": [],
            }
        )
    value["statements"].extend(
        [
            {
                "id": "statement_and",
                "kind": "logical",
                "operator": "and",
                "operand_statement_ids": ["statement_truth", "statement_less"],
                "span_ids": [],
            },
            {
                "id": "statement_exists",
                "kind": "quantified",
                "quantifier": "exists",
                "variable_ids": ["variable_exists"],
                "body_statement_id": "statement_body",
                "span_ids": [],
            },
        ]
    )
    value["definitions"].extend(
        [
            {
                "id": "definition_expression",
                "name": "identity",
                "parameter_variable_ids": ["variable_parameter"],
                "result_domain_id": "domain_integer",
                "body": {"kind": "expression", "expression_id": "expression_parameter"},
                "recursive": False,
                "span_ids": [],
            },
            {
                "id": "definition_statement",
                "name": "truth",
                "parameter_variable_ids": [],
                "result_domain_id": None,
                "body": {"kind": "statement", "statement_id": "statement_truth"},
                "recursive": False,
                "span_ids": [],
            },
        ]
    )
    value["assumptions"].append(
        {
            "id": "assumption_truth",
            "statement_id": "statement_truth",
            "role": "given",
            "span_ids": [],
        }
    )
    value["goals"].append(
        {
            "id": "goal_secondary",
            "statement_id": "statement_and",
            "mode": "refute",
            "span_ids": [],
        }
    )
    reading = value["readings"][0]
    reading["definition_ids"] = ["definition_statement", "definition_expression"]
    reading["assumption_ids"] = ["assumption_truth"]
    reading["goal_ids"] = ["goal_secondary", "goal_reflexive"]
    value["extensions"] = {"org.mathhead.test": {"exact": True, "labels": ["a", "b"]}}
    return value


class ProblemIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.problem_schema, _ = independent.load_json(
            ROOT / "docs/contracts/schemas/problem-ir-v1.schema.json"
        )

    def assert_accepted(self, spec: dict[str, object]):
        result = intake_problem(spec)
        self.assertEqual((result.status, result.reason_code), ("accepted", "ACCEPTED"))
        problem = json.loads(canonical_problem_ir_bytes(result))
        independent.validate_problem_ir(problem, self.problem_schema)
        self.assertEqual(result.problem_ir_sha256, hashlib.sha256(result.problem_ir_bytes).hexdigest())
        self.assertFalse(result.mathematical_authority)
        return result

    def assert_failed(self, spec: object, reason: str):
        result = intake_problem(spec)  # type: ignore[arg-type]
        self.assertIn(result.status, {"invalid", "exhausted"})
        self.assertEqual(result.reason_code, reason)
        self.assertIsNone(result.problem_ir_bytes)
        self.assertIsNone(result.problem_ir_sha256)
        self.assertFalse(result.mathematical_authority)
        return result

    def test_minimal_and_all_tagged_variants_are_independently_valid(self) -> None:
        self.assert_accepted(specification())
        self.assert_accepted(specification(all_variants_problem()))

    def test_all_eight_foundation_scenarios_reach_stable_problem_ir(self) -> None:
        manifest = json.loads((ROOT / "docs/fixtures/foundation-v1/manifest.json").read_text())
        for scenario in manifest["scenarios"]:
            artifact = next(item for item in scenario["artifacts"] if item["role"] == "problem_ir")
            problem = json.loads(
                (ROOT / f"docs/fixtures/foundation-v1/objects/{artifact['sha256']}.json").read_text()
            )
            with self.subTest(scenario=scenario["scenario_id"]):
                result = self.assert_accepted(specification(problem))
                self.assertEqual(result.problem_ir_sha256, artifact["sha256"])

    def test_registry_and_set_order_normalize_but_goal_order_is_preserved(self) -> None:
        problem = all_variants_problem()
        ordered_goals = list(problem["readings"][0]["goal_ids"])
        baseline = self.assert_accepted(specification(copy.deepcopy(problem)))
        for registry in (
            "domains",
            "variables",
            "expressions",
            "relations",
            "statements",
            "definitions",
            "assumptions",
            "goals",
        ):
            problem[registry].reverse()
        problem["readings"][0]["definition_ids"].reverse()
        normalized = self.assert_accepted(specification(problem))
        self.assertEqual(normalized.problem_ir_bytes, baseline.problem_ir_bytes)
        value = json.loads(normalized.problem_ir_bytes)
        self.assertEqual(value["readings"][0]["goal_ids"], ordered_goals)

    def test_input_is_owned_and_caller_mutation_cannot_change_result(self) -> None:
        spec = specification()
        result = self.assert_accepted(spec)
        encoded = problem_intake_result_bytes(result)
        spec["problem"]["readings"][0]["label"] = "mutated"
        spec["problem"]["domains"].clear()
        self.assertEqual(problem_intake_result_bytes(result), encoded)

    def test_exact_type_boundary_rejects_subclasses_floats_bytes_and_bool_ints(self) -> None:
        class EvilDict(dict):
            pass

        self.assert_failed(EvilDict(specification()), "INVALID_TYPE")
        floating = specification()
        floating["problem"]["extensions"] = {"org.mathhead.test": {"score": 0.5}}
        self.assert_failed(floating, "INVALID_TYPE")
        binary = specification()
        binary["problem"]["extensions"] = {"org.mathhead.test": {"payload": b"x"}}
        self.assert_failed(binary, "INVALID_TYPE")
        boolean = specification()
        boolean["problem"]["source_documents"] = [
            {
                "id": "source_input",
                "media_type": "text/plain",
                "language": "en",
                "sha256": "0" * 64,
                "byte_length": True,
            }
        ]
        self.assert_failed(boolean, "INVALID_SCHEMA")

    def test_text_latex_ast_sympy_and_custom_sequences_are_not_adapters(self) -> None:
        for value in ("x = x", b"x=x", ["x=x"], ("x=x",)):
            with self.subTest(value=type(value).__name__):
                self.assert_failed(value, "INVALID_TYPE")

        class Sequence:
            def __iter__(self):
                yield independent.minimal_problem_ir()

        custom = specification()
        custom["problem"]["domains"] = Sequence()
        self.assert_failed(custom, "INVALID_TYPE")

    def test_unknown_missing_dangling_type_cycle_and_scope_fail_closed(self) -> None:
        unknown = specification()
        unknown["problem"]["unknown"] = True
        self.assert_failed(unknown, "INVALID_SCHEMA")
        missing = specification()
        missing["problem"].pop("readings")
        self.assert_failed(missing, "INVALID_SCHEMA")
        dangling = specification()
        dangling["problem"]["goals"][0]["statement_id"] = "statement_missing"
        self.assert_failed(dangling, "INVALID_REFERENCE")
        typed = specification()
        typed["problem"]["expressions"][0]["domain_id"] = "domain_missing"
        self.assert_failed(typed, "INVALID_REFERENCE")
        cycle = specification()
        cycle["problem"]["statements"].append(
            {
                "id": "statement_cycle",
                "kind": "logical",
                "operator": "not",
                "operand_statement_ids": ["statement_cycle"],
                "span_ids": [],
            }
        )
        self.assert_failed(cycle, "INVALID_SEMANTICS")
        escape = specification()
        escape["problem"]["goals"][0]["statement_id"] = "statement_body"
        self.assert_failed(escape, "INVALID_SEMANTICS")

    def test_unicode_is_nfc_normalized_and_nul_is_rejected(self) -> None:
        decomposed = specification()
        decomposed["problem"]["readings"][0]["label"] = "es\u0327it"
        result = self.assert_accepted(decomposed)
        self.assertEqual(json.loads(result.problem_ir_bytes)["readings"][0]["label"], "eşit")
        nul = specification()
        nul["problem"]["readings"][0]["label"] = "bad\x00label"
        self.assert_failed(nul, "INVALID_CANONICAL_VALUE")

    def test_budget_exhaustion_returns_no_partial_identity(self) -> None:
        oversized = specification()
        oversized["problem"]["readings"][0]["label"] = "x" * 1_048_577
        result = self.assert_failed(oversized, "BUDGET_EXHAUSTED")
        self.assertEqual(result.status, "exhausted")
        huge_integer = specification()
        huge_integer["problem"]["extensions"] = {"org.mathhead.test": {"count": 2**53}}
        self.assert_failed(huge_integer, "BUDGET_EXHAUSTED")
        with mock.patch.object(problem_intake_module, "MAX_VALIDATION_STEPS", 10):
            self.assert_failed(specification(), "BUDGET_EXHAUSTED")

    def test_result_round_trip_schema_and_identity_are_closed(self) -> None:
        result = self.assert_accepted(specification())
        encoded = problem_intake_result_bytes(result)
        parsed = parse_problem_intake_result(encoded)
        self.assertEqual(parsed, result)
        self.assertEqual(problem_intake_result_sha256(result), hashlib.sha256(encoded).hexdigest())

        wire = json.loads(encoded)
        self.assertEqual(
            set(wire),
            {
                "contract_id",
                "contract_sha256",
                "diagnostics",
                "mathematical_authority",
                "problem_ir",
                "problem_ir_contract_sha256",
                "problem_ir_schema_sha256",
                "problem_ir_sha256",
                "reason_code",
                "schema",
                "status",
            },
        )
        independent.validate_problem_ir(wire["problem_ir"], self.problem_schema)

    def test_result_parser_rejects_unknown_duplicate_noncanonical_and_tampered_bytes(self) -> None:
        result = self.assert_accepted(specification())
        value = json.loads(problem_intake_result_bytes(result))
        value["unknown"] = True
        unknown = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ProblemIntakeValidationError):
            parse_problem_intake_result(unknown)
        with self.assertRaises(ProblemIntakeValidationError):
            parse_problem_intake_result(b'{"schema":1,"schema":2}\n')
        with self.assertRaises(ProblemIntakeValidationError):
            parse_problem_intake_result(json.dumps(json.loads(problem_intake_result_bytes(result))).encode())
        value.pop("unknown")
        value["problem_ir_sha256"] = "0" * 64
        tampered = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ProblemIntakeValidationError):
            parse_problem_intake_result(tampered)
        value = json.loads(problem_intake_result_bytes(result))
        value["problem_ir"]["readings"][0]["label"] = "es\u0327it"
        problem_bytes = (
            json.dumps(value["problem_ir"], sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
        value["problem_ir_sha256"] = hashlib.sha256(problem_bytes).hexdigest()
        non_nfc = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ProblemIntakeValidationError):
            parse_problem_intake_result(non_nfc)

    def test_result_values_cannot_be_forged_subclassed_or_pickled(self) -> None:
        with self.assertRaises(PermissionError):
            ProblemIntakeResult()
        with self.assertRaises(TypeError):
            class Forged(ProblemIntakeResult):
                pass

        result = self.assert_accepted(specification())
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        forged = object.__new__(ProblemIntakeResult)
        with self.assertRaises(ProblemIntakeValidationError):
            validate_problem_intake_result(forged)

    def test_cross_process_and_hash_seed_determinism(self) -> None:
        script = """
import json
from tools.validate_problem_ir_contract import minimal_problem_ir
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes
r = intake_problem({'schema':'mathhead.problem-intake.v1','problem':minimal_problem_ir()})
print(problem_intake_result_bytes(r).hex())
"""
        outputs = []
        for seed in ("1", "777"):
            completed = subprocess.run(
                [sys.executable, "-c", script],
                cwd=ROOT,
                env={"PYTHONHASHSEED": seed, "PYTHONPATH": str(SRC)},
                check=True,
                capture_output=True,
                text=True,
            )
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_contract_and_schema_identities_are_exact(self) -> None:
        self.assertEqual(CONTRACT_SHA256, "855375a8fb788ff65728d860c16f0ccfa32fe9d058b3fe93534ef11f147794dc")
        for name, expected in {
            "problem-intake-v1.schema.json": "e109d5a664849b8122eed13eeb87d73bc47e2d2989b3298e06a697989fb51c04",
            "problem-intake-result-v1.schema.json": "0ea174a09391dd7f690bba9df7dfd08d8f1253032c472ca60d45eaf9f47101d3",
        }.items():
            self.assertEqual(hashlib.sha256((SCHEMA_ROOT / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
