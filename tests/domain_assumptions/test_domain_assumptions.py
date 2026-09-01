from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
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

import mathhead.domain_assumptions as normalization_module  # noqa: E402
from mathhead.domain_assumptions import (  # noqa: E402
    CONTRACT_SHA256,
    RULE_CATALOGUE_SHA256,
    DomainAssumptionNormalizationResult,
    DomainAssumptionValidationError,
    domain_assumption_fact_bytes,
    domain_assumption_result_bytes,
    domain_assumption_result_sha256,
    normalize_domain_assumptions,
    normalized_domain_context_bytes,
    parse_domain_assumption_result,
    validate_domain_assumption_result,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


def _sort(problem: dict[str, object]) -> None:
    for registry in (
        "source_documents",
        "source_spans",
        "domains",
        "variables",
        "expressions",
        "relations",
        "statements",
        "definitions",
        "assumptions",
        "goals",
        "readings",
    ):
        problem[registry].sort(key=lambda item: item["id"])  # type: ignore[union-attr,index]


def _analysis_bytes(problem: dict[str, object] | None = None) -> bytes:
    value = problem if problem is not None else minimal_problem_ir()
    _sort(value)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": value})
    if intake.status != "accepted":
        raise AssertionError((intake.status, intake.reason_code, intake.diagnostics))
    analysis = analyze_problem_readings(problem_intake_result_bytes(intake))
    if analysis.status != "analyzed":
        raise AssertionError((analysis.status, analysis.reason_code, analysis.diagnostics))
    return reading_analysis_result_bytes(analysis)


def _normalized(problem: dict[str, object] | None = None):
    result = normalize_domain_assumptions(_analysis_bytes(problem))
    if result.status != "normalized":
        raise AssertionError((result.status, result.reason_code, result.diagnostics))
    return result


def _forge_result(result, **changes):
    forged = object.__new__(DomainAssumptionNormalizationResult)
    for field in DomainAssumptionNormalizationResult.__slots__:
        object.__setattr__(forged, field, changes.get(field, getattr(result, field)))
    return forged


def _candidate_with_context(candidate, context):
    digest = hashlib.sha256(
        normalization_module._canonical_bytes(  # noqa: SLF001
            normalization_module._context_mapping(context)  # noqa: SLF001
        )
    ).hexdigest()
    return replace(candidate, context=context, context_sha256=digest)


def _all_domains_problem() -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["domains"].extend(  # type: ignore[union-attr]
        {"id": f"domain_{name}", "kind": "builtin", "name": name, "span_ids": []}
        for name in ("boolean", "natural", "rational", "real", "complex")
    )
    problem["expressions"].extend(  # type: ignore[union-attr]
        [
            {"id": "expression_boolean", "kind": "literal", "domain_id": "domain_boolean", "literal_type": "boolean", "value": "true", "span_ids": []},
            {"id": "expression_natural_one", "kind": "literal", "domain_id": "domain_natural", "literal_type": "integer", "value": "1", "span_ids": []},
            {"id": "expression_integer_zero", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "0", "span_ids": []},
            {"id": "expression_integer_two", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "2", "span_ids": []},
            {"id": "expression_rational_half", "kind": "literal", "domain_id": "domain_rational", "literal_type": "rational", "value": "1/2", "span_ids": []},
            {"id": "expression_real_one", "kind": "literal", "domain_id": "domain_real", "literal_type": "integer", "value": "1", "span_ids": []},
            {"id": "expression_complex_one", "kind": "literal", "domain_id": "domain_complex", "literal_type": "integer", "value": "1", "span_ids": []},
        ]
    )
    problem["domains"].extend(  # type: ignore[union-attr]
        [
            {"id": "domain_finite", "kind": "finite", "element_domain_id": "domain_integer", "element_expr_ids": ["expression_integer_two", "expression_integer_zero"], "cardinality": 2, "span_ids": []},
            {"id": "domain_interval_closed", "kind": "interval", "base": "integer", "lower_expr_id": "expression_integer_zero", "lower_closed": True, "upper_expr_id": "expression_integer_two", "upper_closed": True, "span_ids": []},
            {"id": "domain_interval_half_open", "kind": "interval", "base": "rational", "lower_expr_id": "expression_rational_half", "lower_closed": False, "upper_expr_id": None, "upper_closed": False, "span_ids": []},
            {"id": "domain_interval_unbounded_lower", "kind": "interval", "base": "real", "lower_expr_id": None, "lower_closed": False, "upper_expr_id": "expression_real_one", "upper_closed": True, "span_ids": []},
            {"id": "domain_modular", "kind": "modular", "modulus_expr_id": "expression_integer_two", "span_ids": []},
            {"id": "domain_set_finite", "kind": "collection", "collection": "set", "element_domain_id": "domain_integer", "finiteness": "finite", "span_ids": []},
            {"id": "domain_sequence_infinite", "kind": "collection", "collection": "sequence", "element_domain_id": "domain_real", "finiteness": "infinite", "span_ids": []},
            {"id": "domain_multiset_unknown", "kind": "collection", "collection": "multiset", "element_domain_id": "domain_rational", "finiteness": "unknown", "span_ids": []},
            {"id": "domain_product", "kind": "product", "factor_domain_ids": ["domain_integer", "domain_real"], "span_ids": []},
            {"id": "domain_nested_product", "kind": "product", "factor_domain_ids": ["domain_product", "domain_boolean"], "span_ids": []},
            {"id": "domain_nullary_total_function", "kind": "function", "parameter_domain_ids": [], "result_domain_id": "domain_boolean", "total": True, "span_ids": []},
            {"id": "domain_partial_function", "kind": "function", "parameter_domain_ids": ["domain_integer", "domain_real"], "result_domain_id": "domain_complex", "total": False, "span_ids": []},
            {"id": "domain_structure", "kind": "structure", "theory_id": "org.mathhead.algebra.group", "parameter_domain_ids": ["domain_integer"], "parameter_expr_ids": ["expression_integer_two"], "span_ids": []},
        ]
    )
    domain_ids = sorted(item["id"] for item in problem["domains"])  # type: ignore[index]
    extra_variables = []
    extra_expressions = []
    for index, domain_id in enumerate(domain_ids):
        variable_id = f"variable_domain_{index:02d}"
        expression_id = f"expression_domain_{index:02d}"
        extra_variables.append(
            {"id": variable_id, "name": f"v{index}", "domain_id": domain_id, "role": "bound", "span_ids": []}
        )
        extra_expressions.append(
            {"id": expression_id, "kind": "variable", "domain_id": domain_id, "variable_id": variable_id, "span_ids": []}
        )
    problem["variables"].extend(extra_variables)  # type: ignore[union-attr]
    problem["expressions"].extend(extra_expressions)  # type: ignore[union-attr]
    variable_ids = sorted(item["id"] for item in problem["variables"])  # type: ignore[index]
    statement_forall = next(  # type: ignore[index]
        item for item in problem["statements"] if item["id"] == "statement_forall"
    )
    statement_forall["variable_ids"] = variable_ids
    return problem


def _assumptions_problem() -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"  # type: ignore[index]
    problem["statements"] = [  # type: ignore[index]
        item for item in problem["statements"] if item["id"] != "statement_forall"
    ]
    problem["goals"][0]["statement_id"] = "statement_body"  # type: ignore[index]
    problem["domains"].append(  # type: ignore[union-attr]
        {"id": "domain_integer_set", "kind": "collection", "collection": "set", "element_domain_id": "domain_integer", "finiteness": "unknown", "span_ids": []}
    )
    problem["expressions"].extend(  # type: ignore[union-attr]
        [
            {"id": "expression_zero", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "0", "span_ids": []},
            {"id": "expression_one", "kind": "literal", "domain_id": "domain_integer", "literal_type": "integer", "value": "1", "span_ids": []},
            {"id": "expression_set", "kind": "collection", "domain_id": "domain_integer_set", "element_expr_ids": ["expression_x"], "span_ids": []},
            {"id": "expression_assumption_bound", "kind": "variable", "domain_id": "domain_integer", "variable_id": "variable_assumption_bound", "span_ids": []},
        ]
    )
    problem["variables"].append(  # type: ignore[union-attr]
        {"id": "variable_assumption_bound", "name": "q", "domain_id": "domain_integer", "role": "bound", "span_ids": []}
    )
    relations = [
        {"id": "relation_not_equal_zero", "kind": "not_equal", "operand_expr_ids": ["expression_x", "expression_zero"], "span_ids": []},
        {"id": "relation_lower", "kind": "greater_equal", "operand_expr_ids": ["expression_x", "expression_zero"], "span_ids": []},
        {"id": "relation_member", "kind": "member", "operand_expr_ids": ["expression_x", "expression_set"], "span_ids": []},
        {"id": "relation_not_member", "kind": "not_member", "operand_expr_ids": ["expression_x", "expression_set"], "span_ids": []},
        {"id": "relation_divides", "kind": "divides", "operand_expr_ids": ["expression_one", "expression_x"], "span_ids": []},
        {"id": "relation_congruent", "kind": "congruent", "operand_expr_ids": ["expression_x", "expression_one", "expression_one"], "span_ids": []},
        {"id": "relation_assumption_bound", "kind": "equal", "operand_expr_ids": ["expression_assumption_bound", "expression_assumption_bound"], "span_ids": []},
    ]
    predicate_specs = [
        ("nonzero", "org.mathhead.property.nonzero", ["expression_x"]),
        ("finite", "org.mathhead.property.finite", ["expression_set"]),
        ("cardinality", "org.mathhead.property.cardinality", ["expression_set", "expression_one"]),
        ("dimension", "org.mathhead.property.dimension", ["expression_x", "expression_one"]),
        ("graph_class", "org.mathhead.graph.class", ["expression_x", "expression_one"]),
        ("regularity", "org.mathhead.analysis.regularity", ["expression_x", "expression_one"]),
        ("opaque", "org.example.unknown.property", ["expression_x"]),
    ]
    relations.extend(
        {"id": f"relation_{suffix}", "kind": "predicate", "predicate": predicate, "operand_expr_ids": operands, "span_ids": []}
        for suffix, predicate, operands in predicate_specs
    )
    problem["relations"].extend(relations)  # type: ignore[union-attr]
    relation_ids = [item["id"] for item in relations]
    problem["statements"].extend(  # type: ignore[union-attr]
        {"id": f"statement_{relation_id.removeprefix('relation_')}", "kind": "relation", "relation_id": relation_id, "span_ids": []}
        for relation_id in relation_ids
    )
    problem["statements"].extend(  # type: ignore[union-attr]
        [
            {"id": "statement_truth", "kind": "truth", "value": True, "span_ids": []},
            {"id": "statement_logical", "kind": "logical", "operator": "and", "operand_statement_ids": ["statement_lower", "statement_truth"], "span_ids": []},
            {"id": "statement_quantified", "kind": "quantified", "quantifier": "exists", "variable_ids": ["variable_assumption_bound"], "body_statement_id": "statement_assumption_bound", "span_ids": []},
        ]
    )
    statement_ids = [
        f"statement_{item.removeprefix('relation_')}"
        for item in relation_ids
        if item != "relation_assumption_bound"
    ]
    statement_ids.extend(["statement_truth", "statement_logical", "statement_quantified"])
    roles = ("given", "domain_constraint", "side_condition")
    assumptions = [
        {"id": f"assumption_{index:02d}", "statement_id": statement_id, "role": roles[index % 3], "span_ids": []}
        for index, statement_id in enumerate(statement_ids)
    ]
    problem["assumptions"].extend(assumptions)  # type: ignore[union-attr]
    problem["readings"][0]["assumption_ids"] = sorted(item["id"] for item in assumptions)  # type: ignore[index]
    return problem


def _unresolved_problem() -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["variables"].append(  # type: ignore[union-attr]
        {"id": "variable_y", "name": "y", "domain_id": "domain_integer", "role": "bound", "span_ids": []}
    )
    problem["expressions"].append(  # type: ignore[union-attr]
        {"id": "expression_y", "kind": "variable", "domain_id": "domain_integer", "variable_id": "variable_y", "span_ids": []}
    )
    problem["relations"].append(  # type: ignore[union-attr]
        {"id": "relation_reflexive_y", "kind": "equal", "operand_expr_ids": ["expression_y", "expression_y"], "span_ids": []}
    )
    problem["statements"].extend(  # type: ignore[union-attr]
        [
            {"id": "statement_body_y", "kind": "relation", "relation_id": "relation_reflexive_y", "span_ids": []},
            {"id": "statement_exists", "kind": "quantified", "quantifier": "exists", "variable_ids": ["variable_y"], "body_statement_id": "statement_body_y", "span_ids": []},
        ]
    )
    problem["goals"].append(  # type: ignore[union-attr]
        {"id": "goal_exists", "statement_id": "statement_exists", "mode": "prove", "span_ids": []}
    )
    changed = sorted(
        {
            "variable_x", "expression_x", "relation_reflexive", "statement_body",
            "statement_forall", "goal_reflexive", "variable_y", "expression_y",
            "relation_reflexive_y", "statement_body_y", "statement_exists", "goal_exists",
        }
    )
    problem["readings"].append(  # type: ignore[union-attr]
        {
            "id": "reading_alternative",
            "label": "There exists an integer y equal to itself.",
            "definition_ids": [],
            "assumption_ids": [],
            "goal_ids": ["goal_exists"],
            "difference_from": "reading_only",
            "differences": [{"kind": "quantifier", "summary": "The declared binder differs.", "affected_ids": changed, "span_ids": []}],
            "span_ids": [],
        }
    )
    problem["ambiguity"] = {
        "status": "unresolved",
        "candidate_reading_ids": ["reading_alternative", "reading_only"],
        "selected_reading_id": None,
        "required_choice": "Choose the intended quantified reading.",
    }
    return problem


class DomainAssumptionTests(unittest.TestCase):
    def test_minimal_result_is_canonical_replayable_and_non_authoritative(self) -> None:
        first = _normalized()
        second = _normalized()
        self.assertEqual(first, second)
        self.assertFalse(first.mathematical_authority)
        self.assertEqual(first.status, "normalized")
        self.assertEqual(first.candidates[0].context.domain_ids, ("domain_integer",))
        self.assertEqual(first.candidates[0].context.variable_ids, ("variable_x",))
        self.assertEqual(
            [item.kind for item in first.candidates[0].context.facts],
            ["builtin_domain", "variable_domain"],
        )
        payload = domain_assumption_result_bytes(first)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(parse_domain_assumption_result(payload), first)
        self.assertEqual(domain_assumption_result_sha256(first), hashlib.sha256(payload).hexdigest())

    def test_every_domain_variant_and_builtin_carrier_remains_exact(self) -> None:
        result = _normalized(_all_domains_problem())
        context = result.candidates[0].context
        domain_facts = [item for item in context.facts if item.origin_registry == "domains"]
        self.assertEqual({item.origin_id for item in domain_facts}, set(context.domain_ids))
        self.assertEqual(
            {item.kind for item in domain_facts},
            {
                "builtin_domain", "finite_domain", "interval_domain", "modular_domain",
                "collection_domain", "product_domain", "function_domain", "structure_domain",
            },
        )
        builtin_names = {
            item.payload["domain"]["name"]  # type: ignore[index]
            for item in domain_facts
            if item.kind == "builtin_domain"
        }
        self.assertEqual(builtin_names, {"boolean", "natural", "integer", "rational", "real", "complex"})
        functions = [item.payload["domain"] for item in domain_facts if item.kind == "function_domain"]  # type: ignore[index]
        self.assertEqual({item["total"] for item in functions}, {False, True})
        self.assertIn([], [list(item["parameter_domain_ids"]) for item in functions])

    def test_assumption_roles_specialized_rules_opaque_visibility_and_nonzero(self) -> None:
        result = _normalized(_assumptions_problem())
        context = result.candidates[0].context
        facts = [item for item in context.facts if item.origin_registry == "assumptions"]
        kinds = {item.kind for item in facts}
        self.assertTrue(
            {
                "truth_assumption", "disequality_assumption", "bound_assumption",
                "membership_assumption", "nonmembership_assumption", "divisibility_assumption",
                "congruence_assumption", "nonzero_assumption", "finiteness_assumption",
                "cardinality_assumption", "dimension_assumption", "graph_class_assumption",
                "regularity_assumption", "opaque_predicate_assumption", "logical_assumption",
                "quantified_assumption",
            }.issubset(kinds)
        )
        self.assertEqual({item.assumption_role for item in facts}, {"given", "domain_constraint", "side_condition"})
        unsupported = [item for item in facts if not item.supported]
        self.assertEqual(
            tuple(item.fact_sha256 for item in unsupported),
            context.unsupported_fact_sha256s,
        )
        disequality_index = next(index for index, item in enumerate(facts) if item.kind == "disequality_assumption")
        self.assertEqual(facts[disequality_index + 1].kind, "nonzero_assumption")
        self.assertEqual(facts[disequality_index + 1].subject_ids, ("expression_x",))

    def test_fact_origins_dependency_closures_and_hashes_are_complete(self) -> None:
        result = _normalized(_assumptions_problem())
        context = result.candidates[0].context
        for ordinal, fact in enumerate(context.facts):
            self.assertEqual(fact.ordinal, ordinal)
            self.assertEqual(fact.reading_id, context.reading_id)
            self.assertRegex(fact.fact_sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(fact.fragment_sha256, r"^[0-9a-f]{64}$")
            self.assertFalse(fact.mathematical_authority)
            self.assertTrue(domain_assumption_fact_bytes(fact).endswith(b"\n"))
        self.assertEqual(context.fact_sha256s, tuple(item.fact_sha256 for item in context.facts))
        self.assertEqual(
            hashlib.sha256(normalized_domain_context_bytes(context)).hexdigest(),
            result.candidates[0].context_sha256,
        )
        nonzero = next(item for item in context.facts if item.kind == "nonzero_assumption" and item.origin_registry == "assumptions")
        self.assertIn("expression_zero", nonzero.dependency_ids)
        self.assertIn("domain_integer", nonzero.dependency_ids)

    def test_unresolved_readings_stay_separate_without_selection_or_leakage(self) -> None:
        result = _normalized(_unresolved_problem())
        self.assertEqual(result.ambiguity_status, "unresolved")
        self.assertIsNone(result.selected_reading_id)
        self.assertEqual(
            tuple(item.reading_id for item in result.candidates),
            ("reading_alternative", "reading_only"),
        )
        contexts = {item.reading_id: item.context for item in result.candidates}
        self.assertEqual(contexts["reading_alternative"].variable_ids, ("variable_y",))
        self.assertEqual(contexts["reading_only"].variable_ids, ("variable_x",))
        self.assertNotEqual(
            contexts["reading_alternative"].fact_sha256s,
            contexts["reading_only"].fact_sha256s,
        )

    def test_invalid_and_failed_upstream_results_fail_without_partial_artifacts(self) -> None:
        invalid = normalize_domain_assumptions(b"{}\n")
        self.assertEqual(invalid.status, "invalid")
        self.assertEqual(invalid.candidates, ())
        self.assertIsNone(invalid.input_result_sha256)
        failed_analysis = analyze_problem_readings(b"{}\n")
        failed = normalize_domain_assumptions(reading_analysis_result_bytes(failed_analysis))
        self.assertEqual(failed.status, "invalid")
        self.assertEqual(failed.candidates, ())
        self.assertIsNone(failed.readings_result_bytes)

    def test_exact_bytes_type_and_budget_fail_closed(self) -> None:
        wrong = normalize_domain_assumptions(bytearray(b"{}\n"))  # type: ignore[arg-type]
        self.assertEqual((wrong.status, wrong.reason_code), ("invalid", "INVALID_TYPE"))
        oversized = normalize_domain_assumptions(b" " * (201_326_592 + 1))
        self.assertEqual((oversized.status, oversized.reason_code), ("exhausted", "BUDGET_EXHAUSTED"))
        self.assertIsNone(oversized.input_result_sha256)

    def test_strict_parser_rejects_noncanonical_and_fabricated_contexts(self) -> None:
        payload = domain_assumption_result_bytes(_normalized())
        with self.assertRaises(DomainAssumptionValidationError):
            parse_domain_assumption_result(payload.rstrip(b"\n") + b" \n")
        value = json.loads(payload)
        value["candidates"][0]["context"]["facts"][0]["supported"] = False
        forged = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(DomainAssumptionValidationError):
            parse_domain_assumption_result(forged)

    def test_closed_result_blocks_direct_construction_subclass_mutation_and_pickle(self) -> None:
        result = _normalized()
        with self.assertRaises(PermissionError):
            DomainAssumptionNormalizationResult()
        with self.assertRaises(TypeError):
            class Forged(DomainAssumptionNormalizationResult):
                pass
        with self.assertRaises(FrozenInstanceError):
            result.status = "invalid"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        failed_diagnostic = normalize_domain_assumptions(b"{}\n").diagnostics[0]
        with self.assertRaises(TypeError):
            pickle.dumps(failed_diagnostic)
        candidate = result.candidates[0]
        with self.assertRaises(TypeError):
            pickle.dumps(candidate)
        with self.assertRaises(TypeError):
            pickle.dumps(candidate.context)
        with self.assertRaises(TypeError):
            pickle.dumps(candidate.context.facts[0])
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        validate_domain_assumption_result(result)

    def test_public_validators_reject_forged_closed_values(self) -> None:
        result = _normalized(_assumptions_problem())
        candidate = result.candidates[0]
        context = candidate.context
        fact = context.facts[0]
        with self.assertRaises(DomainAssumptionValidationError):
            validate_domain_assumption_result(object())
        for forged in (
            _forge_result(result, contract_sha256="0" * 64),
            _forge_result(result, status="mystery"),
            _forge_result(result, reason_code="INVALID_FACT"),
            _forge_result(result, input_result_sha256="0" * 64),
            _forge_result(result, ambiguity_status="mystery"),
            _forge_result(result, candidates=()),
            _forge_result(result, candidates=(candidate, candidate)),
            _forge_result(result, candidates=(object(),)),
        ):
            with self.assertRaises(DomainAssumptionValidationError):
                validate_domain_assumption_result(forged)
        bad_context_candidate = replace(candidate, context=object())
        with self.assertRaises(DomainAssumptionValidationError):
            validate_domain_assumption_result(
                _forge_result(result, candidates=(bad_context_candidate,))
            )
        mismatched = replace(candidate, projection_sha256="0" * 64)
        with self.assertRaises(DomainAssumptionValidationError):
            validate_domain_assumption_result(_forge_result(result, candidates=(mismatched,)))

        reversed_domains = replace(context, domain_ids=tuple(reversed(context.domain_ids)))
        reversed_variables = replace(context, variable_ids=tuple(reversed(context.variable_ids)))
        stale_indexes = replace(context, fact_sha256s=())
        for bad_context in (reversed_domains, reversed_variables, stale_indexes):
            with self.assertRaises(DomainAssumptionValidationError):
                validate_domain_assumption_result(
                    _forge_result(
                        result,
                        candidates=(_candidate_with_context(candidate, bad_context),),
                    )
                )

        for bad_fact in (
            object(),
            replace(fact, ordinal=99),
            replace(fact, mathematical_authority=True),
            replace(fact, fact_sha256="0" * 64),
        ):
            bad_context = replace(context, facts=(bad_fact,))
            with self.assertRaises(DomainAssumptionValidationError):
                normalized_domain_context_bytes(bad_context)
        with self.assertRaises(DomainAssumptionValidationError):
            domain_assumption_fact_bytes(object())  # type: ignore[arg-type]
        with self.assertRaises(DomainAssumptionValidationError):
            domain_assumption_fact_bytes(replace(fact, fact_sha256="0" * 64))
        with self.assertRaises(DomainAssumptionValidationError):
            normalized_domain_context_bytes(object())  # type: ignore[arg-type]

        failed = normalize_domain_assumptions(b"{}\n")
        bad_diagnostic = replace(failed.diagnostics[0], code="UNKNOWN")
        bad_shape = replace(failed.diagnostics[0], path="not-a-path")
        for forged in (
            _forge_result(failed, diagnostics=[]),
            _forge_result(failed, diagnostics=(object(),)),
            _forge_result(failed, diagnostics=(bad_diagnostic,)),
            _forge_result(failed, diagnostics=(bad_shape,)),
            _forge_result(failed, input_result_sha256="0" * 64),
            _forge_result(failed, status="exhausted"),
            _forge_result(failed, reason_code="BUDGET_EXHAUSTED"),
        ):
            with self.assertRaises(DomainAssumptionValidationError):
                validate_domain_assumption_result(forged)

    def test_codec_canonical_budget_and_failed_result_guards(self) -> None:
        failed = normalize_domain_assumptions(b"{}\n")
        failed_bytes = domain_assumption_result_bytes(failed)
        self.assertEqual(parse_domain_assumption_result(failed_bytes), failed)
        for value in (bytearray(failed_bytes), "invalid"):
            with self.assertRaises(DomainAssumptionValidationError):
                parse_domain_assumption_result(value)  # type: ignore[arg-type]
        for payload in (
            b'{"x":1,"x":2}\n',
            b"[]\n",
            b"\xff\n",
        ):
            with self.assertRaises(DomainAssumptionValidationError):
                parse_domain_assumption_result(payload)
        with mock.patch.object(normalization_module, "MAX_OUTPUT_BYTES", 1):
            with self.assertRaises(DomainAssumptionValidationError):
                parse_domain_assumption_result(failed_bytes)

        value = json.loads(failed_bytes)
        mutations = []
        missing = dict(value)
        missing.pop("status")
        mutations.append(missing)
        nonarray = dict(value)
        nonarray["diagnostics"] = {}
        mutations.append(nonarray)
        extra_diagnostic = copy.deepcopy(value)
        extra_diagnostic["diagnostics"][0]["extra"] = True
        mutations.append(extra_diagnostic)
        binding = dict(value)
        binding["contract_sha256"] = "0" * 64
        mutations.append(binding)
        for mutation in mutations:
            payload = (
                json.dumps(mutation, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
                + "\n"
            ).encode()
            with self.assertRaises(DomainAssumptionValidationError):
                parse_domain_assumption_result(payload)

        frozen_payload = _normalized().candidates[0].context.facts[0].payload
        self.assertGreater(len(frozen_payload), 0)  # type: ignore[arg-type]
        with self.assertRaises(KeyError):
            frozen_payload["missing"]  # type: ignore[index]
        for invalid in (
            1.5,
            {1: "bad-key"},
            {"value": 9_007_199_254_740_992},
            {"value": "nul\x00"},
        ):
            with self.assertRaises(normalization_module._NormalizationError):  # noqa: SLF001
                normalization_module._canonical_bytes(invalid)  # noqa: SLF001
        with mock.patch.object(normalization_module, "MAX_DEPTH", 0):
            with self.assertRaises(normalization_module._NormalizationError):  # noqa: SLF001
                normalization_module._canonical_bytes([1])  # noqa: SLF001
        with mock.patch.object(normalization_module, "MAX_AGGREGATE_STRING_CODEPOINTS", 0):
            with self.assertRaises(normalization_module._NormalizationError):  # noqa: SLF001
                normalization_module._canonical_bytes("x")  # noqa: SLF001
        with self.assertRaises(normalization_module._NormalizationError):  # noqa: SLF001
            normalization_module._canonical_bytes({"value": "x"}, maximum=1)  # noqa: SLF001

        valid_input = _analysis_bytes()
        with mock.patch.object(normalization_module, "MAX_CANDIDATES", 0):
            self.assertEqual(
                normalize_domain_assumptions(valid_input).reason_code,
                "BUDGET_EXHAUSTED",
            )
        with mock.patch.object(normalization_module, "MAX_STEPS", 0):
            self.assertEqual(
                normalize_domain_assumptions(valid_input).reason_code,
                "BUDGET_EXHAUSTED",
            )
        with mock.patch.object(
            normalization_module,
            "reading_analysis_result_bytes",
            return_value=b"drift\n",
        ):
            self.assertEqual(
                normalize_domain_assumptions(valid_input).reason_code,
                "INVALID_READING_ANALYSIS",
            )
        with mock.patch.object(
            normalization_module,
            "_normalize_candidate",
            side_effect=RecursionError,
        ):
            self.assertEqual(
                normalize_domain_assumptions(valid_input).reason_code,
                "BUDGET_EXHAUSTED",
            )

    def test_rule_catalogue_and_contract_bindings_are_exact(self) -> None:
        self.assertEqual(
            hashlib.sha256((ROOT / "docs/normalization/domain-assumption-rules-v1.json").read_bytes()).hexdigest(),
            RULE_CATALOGUE_SHA256,
        )
        self.assertEqual(
            hashlib.sha256((ROOT / "docs/contracts/MH-C-DOMAIN-ASSUMPTION-NORMALIZATION-001.json").read_bytes()).hexdigest(),
            CONTRACT_SHA256,
        )

    def test_repeated_processes_and_hash_seeds_are_byte_identical(self) -> None:
        script = (
            "import sys;sys.path[:0]=['src','.'];"
            "from tools.validate_problem_ir_contract import minimal_problem_ir;"
            "from mathhead.problem_intake import intake_problem,problem_intake_result_bytes;"
            "from mathhead.problem_readings import analyze_problem_readings,reading_analysis_result_bytes;"
            "from mathhead.domain_assumptions import normalize_domain_assumptions,domain_assumption_result_sha256;"
            "p=minimal_problem_ir();i=intake_problem({'schema':'mathhead.problem-intake.v1','problem':p});"
            "a=analyze_problem_readings(problem_intake_result_bytes(i));"
            "print(domain_assumption_result_sha256(normalize_domain_assumptions(reading_analysis_result_bytes(a))))"
        )
        outputs = []
        for seed in ("1", "929"):
            environment = os.environ.copy()
            environment["PYTHONHASHSEED"] = seed
            outputs.append(
                subprocess.check_output([sys.executable, "-c", script], cwd=ROOT, env=environment, text=True).strip()
            )
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
