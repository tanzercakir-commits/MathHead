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

import mathhead.unsupported_explanations as explanation_module  # noqa: E402
from mathhead.canonical_normalization import (  # noqa: E402
    canonical_normalization_result_bytes,
    normalize_canonical_obligations,
)
from mathhead.domain_assumptions import (  # noqa: E402
    domain_assumption_result_bytes,
    normalize_domain_assumptions,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from mathhead.proof_obligations import (  # noqa: E402
    decompose_proof_obligations,
    proof_obligation_result_bytes,
)
from mathhead.unsupported_explanations import (  # noqa: E402
    CATALOGUE_SHA256,
    CONTRACT_SHA256,
    UnsupportedExplanationResult,
    UnsupportedExplanationValidationError,
    explain_unsupported_constructs,
    formalization_step_bytes,
    owned_fragment_bytes,
    parse_formalization_step,
    parse_owned_fragment,
    parse_unsupported_explanation,
    parse_unsupported_explanation_result,
    parse_unsupported_target,
    unsupported_explanation_bytes,
    unsupported_explanation_result_bytes,
    unsupported_explanation_result_sha256,
    unsupported_target_bytes,
    validate_unsupported_explanation_result,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals", "readings",
)


def _sort(problem: dict[str, object]) -> None:
    for registry in REGISTRIES:
        problem[registry].sort(key=lambda item: item["id"])  # type: ignore[union-attr,index]


def _unsupported_problem(
    *, opaque_arity: int = 1, duplicate_opaque: bool = False,
) -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"  # type: ignore[index]
    problem["goals"][0]["statement_id"] = "statement_body"  # type: ignore[index]
    problem["statements"] = [problem["statements"][0]]  # type: ignore[index]
    problem["variables"].append(  # type: ignore[union-attr]
        {
            "id": "variable_q", "name": "q", "domain_id": "domain_integer",
            "role": "bound", "span_ids": [],
        }
    )
    problem["expressions"].append(  # type: ignore[union-attr]
        {
            "id": "expression_q", "kind": "variable", "domain_id": "domain_integer",
            "variable_id": "variable_q", "span_ids": [],
        }
    )
    opaque_operands = ["expression_x"]
    if opaque_arity == 2:
        problem["variables"].append(  # type: ignore[union-attr]
            {
                "id": "variable_y", "name": "y", "domain_id": "domain_integer",
                "role": "free", "span_ids": [],
            }
        )
        problem["expressions"].append(  # type: ignore[union-attr]
            {
                "id": "expression_y", "kind": "variable",
                "domain_id": "domain_integer", "variable_id": "variable_y",
                "span_ids": [],
            }
        )
        opaque_operands.append("expression_y")
    problem["relations"].extend(  # type: ignore[union-attr]
        [
            {
                "id": "relation_opaque", "kind": "predicate",
                "predicate": "org.example.unknown.property",
                "operand_expr_ids": opaque_operands, "span_ids": [],
            },
            {
                "id": "relation_q", "kind": "equal",
                "operand_expr_ids": ["expression_q", "expression_q"], "span_ids": [],
            },
        ]
    )
    problem["statements"].extend(  # type: ignore[union-attr]
        [
            {
                "id": "statement_opaque", "kind": "relation",
                "relation_id": "relation_opaque", "span_ids": [],
            },
            {
                "id": "statement_true", "kind": "truth", "value": True,
                "span_ids": [],
            },
            {
                "id": "statement_logical", "kind": "logical", "operator": "and",
                "operand_statement_ids": ["statement_body", "statement_true"],
                "span_ids": [],
            },
            {
                "id": "statement_q", "kind": "relation",
                "relation_id": "relation_q", "span_ids": [],
            },
            {
                "id": "statement_quantified", "kind": "quantified",
                "quantifier": "exists", "variable_ids": ["variable_q"],
                "body_statement_id": "statement_q", "span_ids": [],
            },
        ]
    )
    problem["assumptions"] = [
        {
            "id": "assumption_logical", "statement_id": "statement_logical",
            "role": "given", "span_ids": [],
        },
        {
            "id": "assumption_opaque", "statement_id": "statement_opaque",
            "role": "side_condition", "span_ids": [],
        },
        {
            "id": "assumption_quantified", "statement_id": "statement_quantified",
            "role": "domain_constraint", "span_ids": [],
        },
    ]
    if duplicate_opaque:
        problem["assumptions"].append({  # type: ignore[union-attr]
            "id": "assumption_opaque_second", "statement_id": "statement_opaque",
            "role": "given", "span_ids": [],
        })
    problem["readings"][0]["assumption_ids"] = [  # type: ignore[index]
        "assumption_logical", "assumption_opaque", "assumption_quantified"
    ]
    if duplicate_opaque:
        problem["readings"][0]["assumption_ids"].append(  # type: ignore[index,union-attr]
            "assumption_opaque_second"
        )
    return problem


def _normalization_bytes(problem: dict[str, object] | None = None) -> bytes:
    value = minimal_problem_ir() if problem is None else problem
    _sort(value)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": value})
    if intake.status != "accepted":
        raise AssertionError((intake.reason_code, intake.diagnostics))
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    domain = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    proof = decompose_proof_obligations(domain_assumption_result_bytes(domain))
    normalized = normalize_canonical_obligations(proof_obligation_result_bytes(proof))
    if normalized.status != "normalized":
        raise AssertionError((normalized.reason_code, normalized.diagnostics))
    return canonical_normalization_result_bytes(normalized)


def _result(problem: dict[str, object] | None = None):
    result = explain_unsupported_constructs(_normalization_bytes(problem))
    if result.status != "explained":
        raise AssertionError((result.reason_code, result.diagnostics))
    return result


def _forge_result(result, **changes):
    forged = object.__new__(UnsupportedExplanationResult)
    for field in UnsupportedExplanationResult.__slots__:
        object.__setattr__(forged, field, changes.get(field, getattr(result, field)))
    return forged


def _forge_value(value, **changes):
    forged = object.__new__(type(value))
    for field in type(value).__slots__:
        object.__setattr__(forged, field, changes.get(field, getattr(value, field)))
    return forged


class UnsupportedExplanationTests(unittest.TestCase):
    def test_supported_candidate_has_exact_empty_explanation_set(self) -> None:
        result = _result()
        self.assertEqual(result.reason_code, "EXPLAINED")
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertEqual(candidate.targets, ())
        self.assertEqual(candidate.explanations, ())
        self.assertRegex(candidate.explanation_set_sha256, r"^[0-9a-f]{64}$")
        self.assertFalse(result.mathematical_authority)

    def test_every_unsupported_form_is_explained_once_in_source_order(self) -> None:
        result = _result(_unsupported_problem())
        candidate = result.candidates[0]
        self.assertEqual(len(candidate.targets), 3)
        self.assertEqual(
            tuple(item.target_id for item in candidate.targets),
            ("target_00000000", "target_00000001", "target_00000002"),
        )
        self.assertEqual(
            tuple(item.catalogue_rule_id for item in candidate.explanations),
            (
                "mh.unsupported.rule.opaque-predicate-assumption",
                "mh.unsupported.rule.quantified-assumption",
                "mh.unsupported.rule.logical-assumption",
            ),
        )
        self.assertEqual(
            tuple(sorted({item.source_semantic_sha256 for item in candidate.targets})),
            candidate.unsupported_semantic_sha256s,
        )
        for ordinal, (target, explanation) in enumerate(
            zip(candidate.targets, candidate.explanations)
        ):
            self.assertEqual(target.ordinal, ordinal)
            self.assertEqual(explanation.ordinal, ordinal)
            self.assertEqual(explanation.target_id, target.target_id)
            self.assertEqual(explanation.cause_sha256, target.cause_sha256)
            self.assertFalse(target.mathematical_authority)
            self.assertFalse(explanation.mathematical_authority)

    def test_exact_parameters_owner_boundaries_and_safe_actions(self) -> None:
        explanations = _result(_unsupported_problem()).candidates[0].explanations
        by_rule = {item.catalogue_rule_id: item for item in explanations}
        predicate = by_rule["mh.unsupported.rule.opaque-predicate-assumption"]
        self.assertEqual(
            dict(predicate.construct_parameters),
            {"arity": 1, "predicate_id": "org.example.unknown.property"},
        )
        self.assertEqual(predicate.owned_fragment.owner_boundary, "problem_ir")
        logical = by_rule["mh.unsupported.rule.logical-assumption"]
        self.assertEqual(dict(logical.construct_parameters), {"operator": "and"})
        self.assertEqual(logical.owned_fragment.owner_boundary, "domain_assumptions")
        quantified = by_rule["mh.unsupported.rule.quantified-assumption"]
        self.assertEqual(
            dict(quantified.construct_parameters),
            {"binder_count": 1, "quantifier": "exists"},
        )
        for explanation in explanations:
            step = explanation.formalization_step
            self.assertFalse(step.automatic)
            self.assertTrue(step.requires_user_confirmation)
            self.assertIn("USER_CONFIRMATION_REQUIRED", step.safety_condition_codes)
            self.assertFalse(step.mathematical_authority)

    def test_unknown_predicate_arity_is_derived_from_exact_operands(self) -> None:
        explanations = _result(
            _unsupported_problem(opaque_arity=2)
        ).candidates[0].explanations
        predicate = next(
            item for item in explanations
            if item.catalogue_rule_id
            == "mh.unsupported.rule.opaque-predicate-assumption"
        )
        self.assertEqual(
            dict(predicate.construct_parameters),
            {"arity": 2, "predicate_id": "org.example.unknown.property"},
        )
        self.assertIn("arity 2", predicate.summary)

    def test_repeated_opaque_occurrences_are_not_collapsed(self) -> None:
        candidate = _result(
            _unsupported_problem(duplicate_opaque=True)
        ).candidates[0]
        opaque = [
            target for target, explanation in zip(
                candidate.targets, candidate.explanations
            )
            if explanation.catalogue_rule_id
            == "mh.unsupported.rule.opaque-predicate-assumption"
        ]
        self.assertEqual(len(opaque), 2)
        self.assertEqual(len({item.target_id for item in opaque}), 2)
        self.assertEqual(len({item.source_ref for item in opaque}), 2)
        self.assertEqual(len({item.source_semantic_sha256 for item in opaque}), 2)

    def test_catalogue_exact_relation_obligation_and_generic_paths(self) -> None:
        relation = explanation_module._select_rule(  # noqa: SLF001
            surface="normal_form", form_kind="assumption_fact",
            fact_kind="opaque_relation_assumption", obligation_kind=None,
        )
        obligation = explanation_module._select_rule(  # noqa: SLF001
            surface="obligation", form_kind=None, fact_kind=None,
            obligation_kind="unsupported",
        )
        fallback = explanation_module._select_rule(  # noqa: SLF001
            surface="normal_form", form_kind="expression",
            fact_kind="future_exact_kind", obligation_kind=None,
        )
        self.assertEqual(
            relation.action_code, "EXPRESS_WITH_OWNED_RELATION"
        )
        self.assertEqual(
            obligation.action_code, "REFORMALIZE_UNSUPPORTED_OBLIGATION"
        )
        self.assertTrue(fallback.generic_fallback)
        parameters = explanation_module._parameters_for(  # noqa: SLF001
            fallback, semantic_value={"kind": "future_exact_kind"},
            source_ref="future.ref",
        )
        self.assertEqual(dict(parameters), {"source_ref": "future.ref"})
        summary, detail = explanation_module._render(fallback, parameters)  # noqa: SLF001
        self.assertIn("future.ref", summary)
        self.assertNotIn("future.ref", detail)

    def test_provenance_dependencies_and_cause_identities_are_exact(self) -> None:
        candidate = _result(_unsupported_problem()).candidates[0]
        for target in candidate.targets:
            self.assertEqual(target.surface, "normal_form")
            self.assertEqual(target.source_registry, "assumption_facts")
            self.assertEqual(target.form_kind, "assumption_fact")
            self.assertGreater(len(target.dependency_semantic_sha256s), 0)
            self.assertEqual(
                target.dependency_semantic_sha256s,
                tuple(sorted(set(target.dependency_semantic_sha256s))),
            )
            self.assertRegex(target.cause_sha256, r"^[0-9a-f]{64}$")
            self.assertIsNone(target.obligation_ordinal)

    def test_result_and_every_component_round_trip_canonically(self) -> None:
        result = _result(_unsupported_problem())
        payload = unsupported_explanation_result_bytes(result)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(parse_unsupported_explanation_result(payload), result)
        self.assertEqual(unsupported_explanation_result_sha256(result), result.result_sha256)
        for target, explanation in zip(
            result.candidates[0].targets, result.candidates[0].explanations
        ):
            self.assertEqual(
                parse_unsupported_target(unsupported_target_bytes(target)), target
            )
            self.assertEqual(
                parse_owned_fragment(owned_fragment_bytes(explanation.owned_fragment)),
                explanation.owned_fragment,
            )
            self.assertEqual(
                parse_formalization_step(
                    formalization_step_bytes(explanation.formalization_step)
                ),
                explanation.formalization_step,
            )
            self.assertEqual(
                parse_unsupported_explanation(
                    unsupported_explanation_bytes(explanation)
                ),
                explanation,
            )

    def test_invalid_and_exhausted_inputs_have_no_partial_artifacts(self) -> None:
        for value in (None, bytearray(), memoryview(b"{}"), b"{}", b"{}\n"):
            result = explain_unsupported_constructs(value)  # type: ignore[arg-type]
            self.assertIn(result.status, {"invalid", "exhausted"})
            self.assertIsNone(result.input_result_sha256)
            self.assertIsNone(result.normalization_result_bytes)
            self.assertIsNone(result.result_sha256)
            self.assertEqual(result.candidates, ())
            self.assertTrue(result.diagnostics)
        with mock.patch.object(explanation_module, "MAX_INPUT_BYTES", 1):
            exhausted = explain_unsupported_constructs(_normalization_bytes())
        self.assertEqual(exhausted.status, "exhausted")
        with mock.patch.object(explanation_module, "MAX_STEPS", 0):
            work_exhausted = explain_unsupported_constructs(
                _normalization_bytes(_unsupported_problem())
            )
        self.assertEqual(work_exhausted.status, "exhausted")
        self.assertEqual(work_exhausted.candidates, ())

    def test_failed_result_round_trips_but_has_no_identity(self) -> None:
        result = explain_unsupported_constructs(b"{}\n")
        payload = unsupported_explanation_result_bytes(result)
        self.assertEqual(parse_unsupported_explanation_result(payload), result)
        with self.assertRaises(UnsupportedExplanationValidationError):
            unsupported_explanation_result_sha256(result)

    def test_strict_parsers_reject_noncanonical_and_repaired_outer_forgery(self) -> None:
        raw = unsupported_explanation_result_bytes(_result(_unsupported_problem()))
        with self.assertRaises(UnsupportedExplanationValidationError):
            parse_unsupported_explanation_result(raw.rstrip(b"\n"))
        value = json.loads(raw)
        value["candidates"][0]["explanations"][0]["summary"] = "forged"
        value["result_sha256"] = "f" * 64
        forged = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()
        with self.assertRaises(UnsupportedExplanationValidationError):
            parse_unsupported_explanation_result(forged)
        target_raw = unsupported_target_bytes(_result(_unsupported_problem()).candidates[0].targets[0])
        with self.assertRaises(UnsupportedExplanationValidationError):
            parse_unsupported_target(target_raw.replace(b'"ordinal":0', b'"ordinal":1'))

    def test_component_parser_rejects_duplicate_float_and_bool_parameters(self) -> None:
        target = _result(_unsupported_problem()).candidates[0].targets[0]
        raw = unsupported_target_bytes(target)
        duplicate = raw.replace(
            b"{", b'{"target_id":"target_00000000",', 1
        )
        with self.assertRaises(UnsupportedExplanationValidationError):
            parse_unsupported_target(duplicate)
        for replacement in (True, 1.0):
            value = json.loads(raw)
            value["construct_parameters"]["arity"] = replacement
            forged = (
                json.dumps(
                    value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            ).encode()
            with self.assertRaises(UnsupportedExplanationValidationError):
                parse_unsupported_target(forged)

    def test_closed_values_block_construction_subclass_mutation_and_pickle(self) -> None:
        result = _result(_unsupported_problem())
        with self.assertRaises(PermissionError):
            UnsupportedExplanationResult()
        with self.assertRaises(TypeError):
            class Forged(UnsupportedExplanationResult):
                pass
        with self.assertRaises(FrozenInstanceError):
            result.status = "invalid"  # type: ignore[misc]
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        target = result.candidates[0].targets[0]
        self.assertEqual(hash(target), hash(copy.copy(target)))

    def test_public_validator_and_codecs_reject_forged_values(self) -> None:
        result = _result(_unsupported_problem())
        with self.assertRaises(UnsupportedExplanationValidationError):
            validate_unsupported_explanation_result(
                _forge_result(result, reason_code="SUPPORTED")
            )
        candidate = result.candidates[0]
        target = candidate.targets[0]
        with self.assertRaises(UnsupportedExplanationValidationError):
            unsupported_target_bytes(
                _forge_value(target, mathematical_authority=True)
            )
        explanation = candidate.explanations[0]
        with self.assertRaises(UnsupportedExplanationValidationError):
            unsupported_explanation_bytes(
                _forge_value(explanation, explanation_sha256="0" * 64)
            )

    def test_fatal_exceptions_propagate_unchanged(self) -> None:
        with mock.patch.object(
            explanation_module.canonical,
            "parse_canonical_normalization_result",
            side_effect=MemoryError("fatal"),
        ):
            with self.assertRaises(MemoryError):
                explain_unsupported_constructs(_normalization_bytes())
        with mock.patch.object(
            explanation_module.canonical,
            "parse_canonical_normalization_result",
            side_effect=KeyboardInterrupt(),
        ):
            with self.assertRaises(KeyboardInterrupt):
                explain_unsupported_constructs(_normalization_bytes())

    def test_frozen_contract_schema_and_catalogue_hashes_are_exact(self) -> None:
        artifacts = {
            "docs/contracts/MH-C-UNSUPPORTED-EXPLANATION-001.json": CONTRACT_SHA256,
            "docs/contracts/schemas/unsupported-target-v1.schema.json": explanation_module.TARGET_SCHEMA_SHA256,
            "docs/contracts/schemas/owned-fragment-v1.schema.json": explanation_module.OWNED_FRAGMENT_SCHEMA_SHA256,
            "docs/contracts/schemas/formalization-step-v1.schema.json": explanation_module.FORMALIZATION_STEP_SCHEMA_SHA256,
            "docs/contracts/schemas/unsupported-explanation-v1.schema.json": explanation_module.EXPLANATION_SCHEMA_SHA256,
            "docs/contracts/schemas/unsupported-explanation-catalogue-v1.schema.json": explanation_module.CATALOGUE_SCHEMA_SHA256,
            "docs/contracts/schemas/unsupported-explanation-result-v1.schema.json": explanation_module.RESULT_SCHEMA_SHA256,
            "docs/explanations/unsupported-explanation-catalogue-v1.json": CATALOGUE_SHA256,
        }
        for relative, expected in artifacts.items():
            with self.subTest(relative=relative):
                self.assertEqual(
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected
                )

    def test_catalogue_is_exact_unique_and_has_one_final_fallback(self) -> None:
        catalogue = json.loads(
            (ROOT / "docs/explanations/unsupported-explanation-catalogue-v1.json").read_bytes()
        )
        entries = catalogue["entries"]
        self.assertEqual([item["priority"] for item in entries], [0, 1, 2, 3, 4, 127])
        self.assertEqual(len({item["rule_id"] for item in entries}), len(entries))
        self.assertEqual(sum(item["generic_fallback"] for item in entries), 1)
        self.assertTrue(entries[-1]["generic_fallback"])
        self.assertEqual(entries[-1]["owner_boundary"], "none")

    def test_no_runtime_filesystem_process_or_network_effect_is_needed(self) -> None:
        payload = _normalization_bytes(_unsupported_problem())
        with mock.patch("builtins.open", side_effect=AssertionError("filesystem")):
            with mock.patch("subprocess.run", side_effect=AssertionError("process")):
                first = explain_unsupported_constructs(payload)
                second = explain_unsupported_constructs(payload)
        self.assertEqual(first, second)

    def test_repeated_processes_and_hash_seeds_are_byte_identical(self) -> None:
        script = """
import sys
sys.path[:0]=['src','.']
from tools.validate_problem_ir_contract import minimal_problem_ir
from mathhead.problem_intake import intake_problem,problem_intake_result_bytes
from mathhead.problem_readings import analyze_problem_readings,reading_analysis_result_bytes
from mathhead.domain_assumptions import normalize_domain_assumptions,domain_assumption_result_bytes
from mathhead.proof_obligations import decompose_proof_obligations,proof_obligation_result_bytes
from mathhead.canonical_normalization import normalize_canonical_obligations,canonical_normalization_result_bytes
from mathhead.unsupported_explanations import explain_unsupported_constructs,unsupported_explanation_result_sha256
p=minimal_problem_ir();i=intake_problem({'schema':'mathhead.problem-intake.v1','problem':p})
a=analyze_problem_readings(problem_intake_result_bytes(i));d=normalize_domain_assumptions(reading_analysis_result_bytes(a))
o=decompose_proof_obligations(domain_assumption_result_bytes(d));n=normalize_canonical_obligations(proof_obligation_result_bytes(o))
e=explain_unsupported_constructs(canonical_normalization_result_bytes(n));print(unsupported_explanation_result_sha256(e))
"""
        outputs = []
        for seed in ("1", "19", "random"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            outputs.append(
                subprocess.check_output(
                    [sys.executable, "-c", script], cwd=ROOT,
                    env=environment, text=True,
                ).strip()
            )
        self.assertEqual(len(set(outputs)), 1)


if __name__ == "__main__":
    unittest.main()
