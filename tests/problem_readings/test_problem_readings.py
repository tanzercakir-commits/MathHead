from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
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

import mathhead.problem_readings as readings_module  # noqa: E402
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    CONTRACT_SHA256,
    ReadingAnalysisResult,
    ReadingAnalysisValidationError,
    analyze_problem_readings,
    parse_reading_analysis_result,
    reading_analysis_result_bytes,
    reading_analysis_result_sha256,
    reading_projection_bytes,
    validate_reading_analysis_result,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


def _accepted_bytes(problem: dict[str, object] | None = None) -> bytes:
    result = intake_problem(
        {
            "schema": "mathhead.problem-intake.v1",
            "problem": problem if problem is not None else minimal_problem_ir(),
        }
    )
    if result.status != "accepted":
        raise AssertionError((result.status, result.reason_code, result.diagnostics))
    return problem_intake_result_bytes(result)


def _quantifier_problem(*, status: str = "unresolved", quantifier: str = "exists"):
    problem = minimal_problem_ir()
    problem["variables"].append(
        {
            "id": "variable_y",
            "name": "y",
            "domain_id": "domain_integer",
            "role": "bound",
            "span_ids": [],
        }
    )
    problem["expressions"].append(
        {
            "id": "expression_y",
            "kind": "variable",
            "domain_id": "domain_integer",
            "variable_id": "variable_y",
            "span_ids": [],
        }
    )
    problem["relations"].append(
        {
            "id": "relation_reflexive_y",
            "kind": "equal",
            "operand_expr_ids": ["expression_y", "expression_y"],
            "span_ids": [],
        }
    )
    problem["statements"].extend(
        [
            {
                "id": "statement_body_y",
                "kind": "relation",
                "relation_id": "relation_reflexive_y",
                "span_ids": [],
            },
            {
                "id": "statement_exists",
                "kind": "quantified",
                "quantifier": quantifier,
                "variable_ids": ["variable_y"],
                "body_statement_id": "statement_body_y",
                "span_ids": [],
            },
        ]
    )
    problem["goals"].append(
        {
            "id": "goal_exists",
            "statement_id": "statement_exists",
            "mode": "prove",
            "span_ids": [],
        }
    )
    changed = sorted(
        {
            "variable_x",
            "expression_x",
            "relation_reflexive",
            "statement_body",
            "statement_forall",
            "goal_reflexive",
            "variable_y",
            "expression_y",
            "relation_reflexive_y",
            "statement_body_y",
            "statement_exists",
            "goal_exists",
        }
    )
    problem["readings"].append(
        {
            "id": "reading_alternative",
            "label": f"There {quantifier} an integer y such that y equals itself.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_exists"],
            "difference_from": "reading_only",
            "differences": [
                {
                    "kind": "quantifier",
                    "summary": "The declared binder and quantified goal differ.",
                    "affected_ids": changed,
                    "span_ids": [],
                }
            ],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": status,
        "candidate_reading_ids": ["reading_alternative", "reading_only"],
        "selected_reading_id": "reading_alternative" if status == "resolved" else None,
        "required_choice": "Choose the intended quantified reading."
        if status == "unresolved"
        else None,
    }
    return problem


def _goal_order_problem():
    problem = minimal_problem_ir()
    problem["goals"].append(
        {
            "id": "goal_second",
            "statement_id": "statement_forall",
            "mode": "compute",
            "span_ids": [],
        }
    )
    problem["readings"][0]["goal_ids"] = ["goal_reflexive", "goal_second"]
    problem["readings"].append(
        {
            "id": "reading_reordered",
            "label": "The same goals in the other declared order.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_second", "goal_reflexive"],
            "difference_from": "reading_only",
            "differences": [
                {
                    "kind": "reference",
                    "summary": "The ordered goal roots differ.",
                    "affected_ids": ["goal_reflexive", "goal_second"],
                    "span_ids": [],
                }
            ],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_only", "reading_reordered"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended goal order.",
    }
    return problem


def _notation_problem():
    problem = minimal_problem_ir()
    problem["source_documents"] = [
        {
            "id": "source_problem",
            "media_type": "text/plain",
            "language": "en",
            "sha256": hashlib.sha256(b"x equals x").hexdigest(),
            "byte_length": 10,
        }
    ]
    problem["source_spans"] = [
        {"id": "span_words", "source_id": "source_problem", "start_byte": 0, "end_byte": 10},
        {"id": "span_symbol", "source_id": "source_problem", "start_byte": 0, "end_byte": 1},
    ]
    problem["readings"][0]["span_ids"] = ["span_symbol"]
    problem["readings"].append(
        {
            "id": "reading_words",
            "label": "The source-backed word form.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_reflexive"],
            "difference_from": "reading_only",
            "differences": [
                {
                    "kind": "notation",
                    "summary": "The declared source notation span differs.",
                    "affected_ids": ["goal_reflexive"],
                    "span_ids": ["span_symbol", "span_words"],
                }
            ],
            "span_ids": ["span_words"],
        }
    )
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_only", "reading_words"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended notation.",
    }
    return problem


def _domain_problem(kind: str):
    problem = minimal_problem_ir()
    dependencies: list[str] = []
    if kind == "builtin":
        domain = {"id": "domain_alt", "kind": "builtin", "name": "real", "span_ids": []}
    elif kind == "finite":
        problem["expressions"].append(
            {"id": "expression_one", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "1", "span_ids": []}
        )
        dependencies.append("expression_one")
        domain = {"id": "domain_alt", "kind": "finite", "element_domain_id": "domain_integer", "element_expr_ids": ["expression_one"], "cardinality": 1, "span_ids": []}
    elif kind == "interval":
        problem["domains"].append(
            {"id": "domain_real", "kind": "builtin", "name": "real", "span_ids": []}
        )
        problem["expressions"].extend(
            [
                {"id": "expression_lower", "kind": "literal", "domain_id": "domain_real", "literal_type": "integer", "value": "0", "span_ids": []},
                {"id": "expression_upper", "kind": "literal", "domain_id": "domain_real", "literal_type": "integer", "value": "1", "span_ids": []},
            ]
        )
        dependencies.extend(("domain_real", "expression_lower", "expression_upper"))
        domain = {"id": "domain_alt", "kind": "interval", "base": "real", "lower_expr_id": "expression_lower", "lower_closed": True, "upper_expr_id": "expression_upper", "upper_closed": False, "span_ids": []}
    elif kind == "modular":
        problem["expressions"].append(
            {"id": "expression_modulus", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "2", "span_ids": []}
        )
        dependencies.append("expression_modulus")
        domain = {"id": "domain_alt", "kind": "modular", "modulus_expr_id": "expression_modulus", "span_ids": []}
    elif kind == "collection":
        domain = {"id": "domain_alt", "kind": "collection", "collection": "set", "element_domain_id": "domain_integer", "finiteness": "unknown", "span_ids": []}
    elif kind == "product":
        domain = {"id": "domain_alt", "kind": "product", "factor_domain_ids": ["domain_integer", "domain_integer"], "span_ids": []}
    elif kind == "function":
        domain = {"id": "domain_alt", "kind": "function", "parameter_domain_ids": ["domain_integer"], "result_domain_id": "domain_integer", "total": True, "span_ids": []}
    elif kind == "structure":
        problem["expressions"].append(
            {"id": "expression_parameter", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "1", "span_ids": []}
        )
        dependencies.append("expression_parameter")
        domain = {"id": "domain_alt", "kind": "structure", "theory_id": "org.mathhead.test", "parameter_domain_ids": ["domain_integer"], "parameter_expr_ids": ["expression_parameter"], "span_ids": []}
    else:
        raise AssertionError(kind)
    problem["domains"].append(domain)
    problem["variables"].append(
        {"id": "variable_alt", "name": "y", "domain_id": "domain_alt", "role": "bound", "span_ids": []}
    )
    problem["expressions"].append(
        {"id": "expression_alt", "kind": "variable", "domain_id": "domain_alt", "variable_id": "variable_alt", "span_ids": []}
    )
    problem["relations"].append(
        {"id": "relation_alt", "kind": "equal", "operand_expr_ids": ["expression_alt", "expression_alt"], "span_ids": []}
    )
    problem["statements"].extend(
        [
            {"id": "statement_alt_body", "kind": "relation", "relation_id": "relation_alt", "span_ids": []},
            {"id": "statement_alt_forall", "kind": "quantified", "quantifier": "forall", "variable_ids": ["variable_alt"], "body_statement_id": "statement_alt_body", "span_ids": []},
        ]
    )
    problem["goals"].append(
        {"id": "goal_alt", "statement_id": "statement_alt_forall", "mode": "prove", "span_ids": []}
    )
    base_ids = {
        "domain_integer", "variable_x", "expression_x", "relation_reflexive",
        "statement_body", "statement_forall", "goal_reflexive",
    }
    alt_ids = {
        "domain_alt", "variable_alt", "expression_alt", "relation_alt",
        "statement_alt_body", "statement_alt_forall", "goal_alt", *dependencies,
    }
    if kind in {"finite", "modular", "collection", "product", "function", "structure"}:
        alt_ids.add("domain_integer")
    changed = sorted(base_ids ^ alt_ids)
    problem["readings"].append(
        {
            "id": "reading_domain",
            "label": f"The declared {kind} domain reading.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_alt"],
            "difference_from": "reading_only",
            "differences": [{"kind": "domain", "summary": "The declared domain graph differs.", "affected_ids": changed, "span_ids": []}],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_domain", "reading_only"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended domain.",
    }
    return problem


def _root_set_problem():
    problem = minimal_problem_ir()
    problem["statements"].append(
        {"id": "statement_truth", "kind": "truth", "value": True, "span_ids": []}
    )
    problem["definitions"].append(
        {
            "id": "definition_truth",
            "name": "truth",
            "parameter_variable_ids": [],
            "result_domain_id": None,
            "body": {"kind": "statement", "statement_id": "statement_truth"},
            "recursive": False,
            "span_ids": [],
        }
    )
    problem["assumptions"].append(
        {"id": "assumption_truth", "statement_id": "statement_truth", "role": "given", "span_ids": []}
    )
    problem["readings"].append(
        {
            "id": "reading_roots",
            "label": "The declared reading with an assumption and definition.",
            "definition_ids": ["definition_truth"],
            "assumption_ids": ["assumption_truth"],
            "goal_ids": ["goal_reflexive"],
            "difference_from": "reading_only",
            "differences": [
                {"kind": "scope", "summary": "The definition root is present.", "affected_ids": ["definition_truth"], "span_ids": []},
                {"kind": "reference", "summary": "The assumption graph is present.", "affected_ids": ["assumption_truth", "statement_truth"], "span_ids": []},
            ],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_only", "reading_roots"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended root set.",
    }
    return problem


class ProblemReadingsTests(unittest.TestCase):
    def test_unambiguous_projection_is_complete_stable_and_non_authoritative(self) -> None:
        intake = _accepted_bytes()
        first = analyze_problem_readings(intake)
        second = analyze_problem_readings(intake)
        self.assertEqual(first, second)
        self.assertEqual((first.status, first.reason_code), ("analyzed", "ANALYZED"))
        self.assertEqual(first.ambiguity_status, "unambiguous")
        self.assertEqual(first.selected_reading_id, "reading_only")
        self.assertIsNone(first.required_choice)
        self.assertFalse(first.mathematical_authority)
        self.assertEqual(len(first.candidates), 1)
        projection = json.loads(reading_projection_bytes(first.candidates[0]))
        self.assertEqual(projection["goal_ids"], ["goal_reflexive"])
        self.assertEqual(
            projection["entity_ids"],
            sorted(
                [
                    "domain_integer",
                    "expression_x",
                    "goal_reflexive",
                    "relation_reflexive",
                    "statement_body",
                    "statement_forall",
                    "variable_x",
                ]
            ),
        )
        self.assertEqual(
            first.candidates[0].projection_sha256,
            hashlib.sha256(first.candidates[0].projection_bytes).hexdigest(),
        )

    def test_unresolved_and_resolved_quantifier_alternatives_preserve_choice(self) -> None:
        unresolved = analyze_problem_readings(_accepted_bytes(_quantifier_problem()))
        self.assertEqual(unresolved.status, "analyzed")
        self.assertIsNone(unresolved.selected_reading_id)
        self.assertEqual(
            unresolved.required_choice.candidate_reading_ids,
            ("reading_alternative", "reading_only"),
        )
        alternative = unresolved.candidates[0]
        self.assertEqual(alternative.difference_from, "reading_only")
        self.assertEqual(alternative.deltas[0].kind, "quantifier")
        self.assertTrue(alternative.deltas[0].added_ids)
        self.assertTrue(alternative.deltas[0].removed_ids)
        self.assertNotEqual(
            alternative.deltas[0].before_sha256,
            alternative.deltas[0].after_sha256,
        )

        resolved = analyze_problem_readings(
            _accepted_bytes(_quantifier_problem(status="resolved"))
        )
        self.assertEqual(resolved.status, "analyzed")
        self.assertEqual(resolved.selected_reading_id, "reading_alternative")
        self.assertIsNone(resolved.required_choice)
        self.assertEqual(len(resolved.candidates), 2)

        unique = analyze_problem_readings(
            _accepted_bytes(_quantifier_problem(quantifier="exists_unique"))
        )
        self.assertEqual(unique.status, "analyzed")
        projection = json.loads(unique.candidates[0].projection_bytes)
        quantified = next(
            item for item in projection["entities"]["statements"]
            if item["id"] == "statement_exists"
        )
        self.assertEqual(quantified["quantifier"], "exists_unique")

    def test_every_domain_variant_remains_explicit_in_the_projection_and_delta(self) -> None:
        for kind in (
            "builtin", "finite", "interval", "modular", "collection", "product",
            "function", "structure",
        ):
            with self.subTest(kind=kind):
                result = analyze_problem_readings(_accepted_bytes(_domain_problem(kind)))
                self.assertEqual(result.status, "analyzed", result.diagnostics)
                candidate = next(
                    item for item in result.candidates if item.reading_id == "reading_domain"
                )
                self.assertEqual(candidate.deltas[0].kind, "domain")
                projection = json.loads(candidate.projection_bytes)
                domain = next(
                    item for item in projection["entities"]["domains"]
                    if item["id"] == "domain_alt"
                )
                self.assertEqual(domain["kind"], kind)

    def test_combined_domain_quantifier_and_scope_changes_are_partitioned(self) -> None:
        problem = _domain_problem("builtin")
        all_affected = set(problem["readings"][1]["differences"][0]["affected_ids"])
        scope_ids = {"variable_alt", "variable_x"}
        quantifier_ids = {"statement_alt_forall", "statement_forall"}
        domain_ids = all_affected - scope_ids - quantifier_ids
        problem["readings"][1]["differences"] = [
            {"kind": "domain", "summary": "The domain graph differs.", "affected_ids": sorted(domain_ids), "span_ids": []},
            {"kind": "quantifier", "summary": "The quantified owners differ.", "affected_ids": sorted(quantifier_ids), "span_ids": []},
            {"kind": "scope", "summary": "The bound variable ownership differs.", "affected_ids": sorted(scope_ids), "span_ids": []},
        ]
        result = analyze_problem_readings(_accepted_bytes(problem))
        self.assertEqual(result.status, "analyzed", result.diagnostics)
        candidate = next(item for item in result.candidates if item.reading_id == "reading_domain")
        self.assertEqual(tuple(item.kind for item in candidate.deltas), ("domain", "quantifier", "scope"))
        self.assertEqual(
            set().union(*(set(item.affected_ids) for item in candidate.deltas)),
            all_affected,
        )

    def test_nested_binder_order_is_preserved_and_changes_identity(self) -> None:
        first = _quantifier_problem()
        first["variables"].append(
            {"id": "variable_z", "name": "z", "domain_id": "domain_integer", "role": "bound", "span_ids": []}
        )
        quantified = next(item for item in first["statements"] if item["id"] == "statement_exists")
        quantified["variable_ids"] = ["variable_y", "variable_z"]
        affected = first["readings"][1]["differences"][0]["affected_ids"]
        affected.append("variable_z")
        affected.sort()
        second = copy.deepcopy(first)
        next(item for item in second["statements"] if item["id"] == "statement_exists")[
            "variable_ids"
        ] = ["variable_z", "variable_y"]
        one = analyze_problem_readings(_accepted_bytes(first))
        two = analyze_problem_readings(_accepted_bytes(second))
        self.assertEqual((one.status, two.status), ("analyzed", "analyzed"))
        one_projection = json.loads(one.candidates[0].projection_bytes)
        two_projection = json.loads(two.candidates[0].projection_bytes)
        one_statement = next(
            item for item in one_projection["entities"]["statements"]
            if item["id"] == "statement_exists"
        )
        two_statement = next(
            item for item in two_projection["entities"]["statements"]
            if item["id"] == "statement_exists"
        )
        self.assertEqual(one_statement["variable_ids"], ["variable_y", "variable_z"])
        self.assertEqual(two_statement["variable_ids"], ["variable_z", "variable_y"])
        self.assertNotEqual(
            reading_analysis_result_sha256(one),
            reading_analysis_result_sha256(two),
        )

    def test_goal_order_is_semantic_and_cannot_be_erased(self) -> None:
        result = analyze_problem_readings(_accepted_bytes(_goal_order_problem()))
        self.assertEqual(result.status, "analyzed")
        reordered = next(item for item in result.candidates if item.reading_id == "reading_reordered")
        delta = reordered.deltas[0]
        self.assertEqual(delta.retained_ids, ("goal_reflexive", "goal_second"))
        self.assertEqual(
            delta.paths,
            ("$.goal_ids.goal_reflexive", "$.goal_ids.goal_second"),
        )
        projection = json.loads(reordered.projection_bytes)
        self.assertEqual(projection["goal_ids"], ["goal_second", "goal_reflexive"])

    def test_alternate_definition_and_assumption_roots_are_complete(self) -> None:
        result = analyze_problem_readings(_accepted_bytes(_root_set_problem()))
        self.assertEqual(result.status, "analyzed", result.diagnostics)
        candidate = next(item for item in result.candidates if item.reading_id == "reading_roots")
        self.assertEqual(tuple(delta.kind for delta in candidate.deltas), ("scope", "reference"))
        projection = json.loads(candidate.projection_bytes)
        self.assertEqual(projection["definition_ids"], ["definition_truth"])
        self.assertEqual(projection["assumption_ids"], ["assumption_truth"])
        self.assertIn("definition_truth", projection["entity_ids"])
        self.assertIn("assumption_truth", projection["entity_ids"])
        self.assertIn("statement_truth", projection["entity_ids"])

    def test_notation_requires_and_retains_source_backing(self) -> None:
        result = analyze_problem_readings(_accepted_bytes(_notation_problem()))
        self.assertEqual(result.status, "analyzed")
        words = next(item for item in result.candidates if item.reading_id == "reading_words")
        delta = words.deltas[0]
        self.assertEqual(delta.kind, "notation")
        self.assertEqual(delta.span_ids, ("span_symbol", "span_words"))
        self.assertEqual(delta.retained_ids, ("goal_reflexive",))
        self.assertNotEqual(delta.before_sha256, delta.after_sha256)
        projection = json.loads(words.projection_bytes)
        self.assertEqual(projection["reading_span_ids"], ["span_words"])
        self.assertEqual(projection["source_span_ids"], ["span_words"])

        parse_problem = _notation_problem()
        parse_problem["readings"][1]["differences"][0]["kind"] = "parse"
        parsed = analyze_problem_readings(_accepted_bytes(parse_problem))
        self.assertEqual(parsed.status, "analyzed")
        parse_candidate = next(
            item for item in parsed.candidates if item.reading_id == "reading_words"
        )
        self.assertEqual(parse_candidate.deltas[0].kind, "parse")

    def test_false_omitted_surplus_duplicate_and_wrong_kind_differences_fail_closed(self) -> None:
        false = _goal_order_problem()
        false["readings"][1]["goal_ids"] = list(false["readings"][0]["goal_ids"])
        self.assertEqual(analyze_problem_readings(_accepted_bytes(false)).reason_code, "INVALID_DIFFERENCE")

        omitted = _quantifier_problem()
        omitted["readings"][1]["differences"][0]["affected_ids"].pop()
        self.assertEqual(
            analyze_problem_readings(_accepted_bytes(omitted)).reason_code,
            "INVALID_DIFFERENCE",
        )

        surplus = _goal_order_problem()
        surplus["readings"][1]["differences"][0]["affected_ids"].append("domain_integer")
        surplus["readings"][1]["differences"][0]["affected_ids"].sort()
        self.assertEqual(
            analyze_problem_readings(_accepted_bytes(surplus)).reason_code,
            "INVALID_DIFFERENCE",
        )

        duplicate = _goal_order_problem()
        original = duplicate["readings"][1]["differences"][0]
        original["affected_ids"] = ["goal_reflexive"]
        duplicate["readings"][1]["differences"].append(
            {**copy.deepcopy(original), "affected_ids": ["goal_reflexive", "goal_second"]}
        )
        self.assertEqual(
            analyze_problem_readings(_accepted_bytes(duplicate)).reason_code,
            "INVALID_DIFFERENCE",
        )

        for kind in ("notation", "reference", "scope", "other"):
            with self.subTest(wrong_kind=kind):
                wrong_kind = _quantifier_problem()
                wrong_kind["readings"][1]["differences"][0]["kind"] = kind
                self.assertEqual(
                    analyze_problem_readings(_accepted_bytes(wrong_kind)).reason_code,
                    "INVALID_DIFFERENCE",
                )

    def test_chained_alternative_is_rejected_after_accepted_intake(self) -> None:
        problem = _quantifier_problem()
        chained = copy.deepcopy(problem["readings"][1])
        chained["id"] = "reading_chained"
        chained["difference_from"] = "reading_alternative"
        problem["readings"].append(chained)
        problem["ambiguity"]["candidate_reading_ids"] = [
            "reading_alternative",
            "reading_chained",
            "reading_only",
        ]
        result = analyze_problem_readings(_accepted_bytes(problem))
        self.assertEqual((result.status, result.reason_code), ("invalid", "INVALID_READING_GRAPH"))
        self.assertEqual(result.candidates, ())

    def test_invalid_exhausted_and_wrong_exact_type_inputs_have_no_partial_artifact(self) -> None:
        for value in (b"{}\n", bytearray(b"{}\n")):
            with self.subTest(kind=type(value).__name__):
                result = analyze_problem_readings(value)  # type: ignore[arg-type]
                self.assertEqual(result.status, "invalid")
                self.assertEqual(result.candidates, ())
                self.assertIsNone(result.problem_ir_sha256)
        invalid_intake = intake_problem(None)  # type: ignore[arg-type]
        invalid_result = analyze_problem_readings(problem_intake_result_bytes(invalid_intake))
        self.assertEqual((invalid_result.status, invalid_result.reason_code), ("invalid", "INVALID_INTAKE"))
        self.assertEqual(invalid_result.candidates, ())
        with mock.patch.object(readings_module, "MAX_STEPS", 0):
            exhausted = analyze_problem_readings(_accepted_bytes())
        self.assertEqual((exhausted.status, exhausted.reason_code), ("exhausted", "BUDGET_EXHAUSTED"))
        self.assertEqual(exhausted.candidates, ())

    def test_result_codec_replays_embedded_intake_and_rejects_tampering(self) -> None:
        result = analyze_problem_readings(_accepted_bytes(_quantifier_problem()))
        encoded = reading_analysis_result_bytes(result)
        self.assertEqual(parse_reading_analysis_result(encoded), result)
        self.assertEqual(reading_analysis_result_sha256(result), hashlib.sha256(encoded).hexdigest())
        value = json.loads(encoded)
        value["candidates"][0]["projection_sha256"] = "0" * 64
        forged = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ReadingAnalysisValidationError):
            parse_reading_analysis_result(forged)
        with self.assertRaises(ReadingAnalysisValidationError):
            parse_reading_analysis_result(encoded.rstrip(b"\n"))

    def test_failed_results_round_trip_without_partial_state(self) -> None:
        invalid = analyze_problem_readings(b"{}\n")
        invalid_bytes = reading_analysis_result_bytes(invalid)
        self.assertEqual(parse_reading_analysis_result(invalid_bytes), invalid)
        self.assertIsNone(json.loads(invalid_bytes)["intake_result"])
        with mock.patch.object(readings_module, "MAX_STEPS", 0):
            exhausted = analyze_problem_readings(_accepted_bytes())
        exhausted_bytes = reading_analysis_result_bytes(exhausted)
        self.assertEqual(parse_reading_analysis_result(exhausted_bytes), exhausted)
        self.assertEqual(json.loads(exhausted_bytes)["candidates"], [])

    def test_strict_codecs_reject_malformed_types_shapes_and_budgets(self) -> None:
        result = analyze_problem_readings(_accepted_bytes())
        candidate = result.candidates[0]
        with self.assertRaises(ReadingAnalysisValidationError):
            reading_projection_bytes(object())  # type: ignore[arg-type]
        forged_candidate = type(candidate)(
            candidate.reading_id,
            candidate.difference_from,
            candidate.projection_bytes,
            "0" * 64,
            candidate.deltas,
        )
        with self.assertRaises(ReadingAnalysisValidationError):
            reading_projection_bytes(forged_candidate)
        noncanonical_projection = candidate.projection_bytes.rstrip(b"\n") + b" \n"
        noncanonical_candidate = type(candidate)(
            candidate.reading_id,
            candidate.difference_from,
            noncanonical_projection,
            hashlib.sha256(noncanonical_projection).hexdigest(),
            candidate.deltas,
        )
        with self.assertRaises(ReadingAnalysisValidationError):
            reading_projection_bytes(noncanonical_candidate)
        with mock.patch.object(readings_module, "MAX_AGGREGATE_STRING_CODEPOINTS", 1):
            with self.assertRaises(ReadingAnalysisValidationError):
                reading_projection_bytes(candidate)

        for malformed in (bytearray(b"{}\n"), b"[]\n", b"\xff", b'{"schema":1,"schema":2}\n'):
            with self.subTest(malformed=repr(malformed)):
                with self.assertRaises(ReadingAnalysisValidationError):
                    parse_reading_analysis_result(malformed)  # type: ignore[arg-type]
        with mock.patch.object(readings_module, "MAX_OUTPUT_BYTES", 1):
            with self.assertRaises(ReadingAnalysisValidationError):
                parse_reading_analysis_result(b"{}\n")

        encoded = reading_analysis_result_bytes(result)
        unknown = json.loads(encoded)
        unknown["unknown"] = True
        with self.assertRaises(ReadingAnalysisValidationError):
            parse_reading_analysis_result(
                (json.dumps(unknown, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
        floating = json.loads(encoded)
        floating["mathematical_authority"] = 0.0
        with self.assertRaises(ReadingAnalysisValidationError):
            parse_reading_analysis_result(
                (json.dumps(floating, sort_keys=True, separators=(",", ":")) + "\n").encode()
            )
        nested: object = None
        for _ in range(514):
            nested = [nested]
        deeply_nested = (json.dumps({"unknown": nested}, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ReadingAnalysisValidationError):
            parse_reading_analysis_result(deeply_nested)

        invalid = analyze_problem_readings(b"{}\n")
        with mock.patch.object(readings_module, "MAX_AGGREGATE_STRING_CODEPOINTS", 1):
            with self.assertRaises(ReadingAnalysisValidationError):
                reading_analysis_result_bytes(invalid)

    def test_closed_result_surface_blocks_construction_subclass_pickle_and_mutation(self) -> None:
        result = analyze_problem_readings(_accepted_bytes())
        with self.assertRaises(PermissionError):
            ReadingAnalysisResult()
        with self.assertRaises(TypeError):
            class Forged(ReadingAnalysisResult):
                pass
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        invalid = analyze_problem_readings(b"{}\n")
        diagnostic = invalid.diagnostics[0]
        self.assertIs(copy.copy(diagnostic), diagnostic)
        self.assertIs(copy.deepcopy(diagnostic), diagnostic)
        for value in (
            diagnostic,
            result.candidates[0],
            analyze_problem_readings(_accepted_bytes(_quantifier_problem())).candidates[0].deltas[0],
            analyze_problem_readings(_accepted_bytes(_quantifier_problem())).required_choice,
        ):
            with self.subTest(pickle_type=type(value).__name__):
                with self.assertRaises(TypeError):
                    pickle.dumps(value)
        with self.assertRaises(FrozenInstanceError):
            result.status = "invalid"  # type: ignore[misc]
        object.__setattr__(result, "status", "invalid")
        with self.assertRaises(ReadingAnalysisValidationError):
            validate_reading_analysis_result(result)

    def test_cross_process_hash_seed_reproducibility(self) -> None:
        code = (
            "from mathhead.problem_intake import intake_problem,problem_intake_result_bytes;"
            "from mathhead.problem_readings import analyze_problem_readings,reading_analysis_result_sha256;"
            "from tools.validate_problem_ir_contract import minimal_problem_ir;"
            "r=intake_problem({'schema':'mathhead.problem-intake.v1','problem':minimal_problem_ir()});"
            "print(reading_analysis_result_sha256(analyze_problem_readings(problem_intake_result_bytes(r))))"
        )
        outputs = []
        for seed in ("1", "777"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            environment["PYTHONPATH"] = os.pathsep.join((str(SRC), str(ROOT)))
            outputs.append(
                subprocess.check_output([sys.executable, "-c", code], cwd=ROOT, env=environment, text=True)
            )
        self.assertEqual(outputs[0], outputs[1])

    def test_contract_binding_is_frozen(self) -> None:
        contract = (ROOT / "docs/contracts/MH-C-READING-ANALYSIS-002.json").read_bytes()
        self.assertEqual(hashlib.sha256(contract).hexdigest(), CONTRACT_SHA256)


if __name__ == "__main__":
    unittest.main()
