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

import mathhead.canonical_normalization as normalization_module  # noqa: E402
from mathhead.canonical_normalization import (  # noqa: E402
    CONTRACT_SHA256,
    RULE_CATALOGUE_SHA256,
    CanonicalNormalizationResult,
    CanonicalNormalizationValidationError,
    canonical_context_bytes,
    canonical_normal_form_bytes,
    canonical_normalization_result_bytes,
    canonical_normalization_result_sha256,
    canonical_obligation_bytes,
    canonical_occurrence_trace_bytes,
    normalize_canonical_obligations,
    parse_canonical_normalization_result,
    validate_canonical_normalization_result,
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
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402
from tools.validate_proof_obligations import _rich_problem  # noqa: E402


REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals", "readings",
)


def _sort(problem: dict[str, object]) -> None:
    for registry in REGISTRIES:
        problem[registry].sort(key=lambda item: item["id"])  # type: ignore[union-attr,index]


def _proof_bytes(problem: dict[str, object] | None = None) -> bytes:
    value = minimal_problem_ir() if problem is None else problem
    _sort(value)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": value})
    if intake.status != "accepted":
        raise AssertionError((intake.status, intake.reason_code, intake.diagnostics))
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    if readings.status != "analyzed":
        raise AssertionError((readings.status, readings.reason_code, readings.diagnostics))
    domain = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    if domain.status != "normalized":
        raise AssertionError((domain.status, domain.reason_code, domain.diagnostics))
    proof = decompose_proof_obligations(domain_assumption_result_bytes(domain))
    if proof.status != "decomposed":
        raise AssertionError((proof.status, proof.reason_code, proof.diagnostics))
    return proof_obligation_result_bytes(proof)


def _result(problem: dict[str, object] | None = None):
    result = normalize_canonical_obligations(_proof_bytes(problem))
    if result.status != "normalized":
        raise AssertionError((result.status, result.reason_code, result.diagnostics))
    return result


def _free_binary_problem(kind: str, *, swapped: bool = False) -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["variables"][0]["role"] = "free"  # type: ignore[index]
    problem["variables"].append(  # type: ignore[union-attr]
        {
            "id": "variable_y", "name": "y", "domain_id": "domain_integer",
            "role": "free", "span_ids": [],
        }
    )
    problem["expressions"].append(  # type: ignore[union-attr]
        {
            "id": "expression_y", "kind": "variable", "variable_id": "variable_y",
            "domain_id": "domain_integer", "span_ids": [],
        }
    )
    problem["relations"][0]["kind"] = kind  # type: ignore[index]
    operands = ["expression_x", "expression_y"]
    problem["relations"][0]["operand_expr_ids"] = (  # type: ignore[index]
        list(reversed(operands)) if swapped else operands
    )
    problem["statements"] = problem["statements"][:1]  # type: ignore[index]
    problem["goals"][0]["statement_id"] = "statement_body"  # type: ignore[index]
    return problem


def _assumption_problem(*, swapped: bool = False) -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["statements"].extend(  # type: ignore[union-attr]
        [
            {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
            {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        ]
    )
    problem["assumptions"] = [
        {
            "id": "assumption_a", "statement_id": "statement_true",
            "role": "given", "span_ids": [],
        },
        {
            "id": "assumption_b", "statement_id": "statement_false",
            "role": "side_condition", "span_ids": [],
        },
    ]
    order = ["assumption_a", "assumption_b"]
    problem["readings"][0]["assumption_ids"] = (  # type: ignore[index]
        list(reversed(order)) if swapped else order
    )
    return problem


def _logical_problem(operator: str, *, swapped: bool = False) -> dict[str, object]:
    problem = minimal_problem_ir()
    problem["statements"].extend(  # type: ignore[union-attr]
        [
            {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
            {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
        ]
    )
    operands = ["statement_true", "statement_false"]
    problem["statements"].append(  # type: ignore[union-attr]
        {
            "id": "statement_logical", "kind": "logical", "operator": operator,
            "operand_statement_ids": list(reversed(operands)) if swapped else operands,
            "span_ids": [],
        }
    )
    problem["goals"][0]["statement_id"] = "statement_logical"  # type: ignore[index]
    problem["readings"][0]["goal_ids"] = ["goal_reflexive"]  # type: ignore[index]
    return problem


def _apply_problem(*, swapped: bool = False) -> dict[str, object]:
    problem = _free_binary_problem("equal")
    arguments = ["expression_x", "expression_y"]
    problem["expressions"].append(  # type: ignore[union-attr]
        {
            "id": "expression_apply", "kind": "apply", "domain_id": "domain_integer",
            "operator": "org.mathhead.fixture.ordered",
            "argument_expr_ids": list(reversed(arguments)) if swapped else arguments,
            "attributes": {"mode": "exact"}, "span_ids": [],
        }
    )
    problem["relations"][0]["operand_expr_ids"] = [  # type: ignore[index]
        "expression_apply", "expression_apply",
    ]
    return problem


def _nested_binder_problem(*, renamed: bool = False) -> dict[str, object]:
    outer = "variable_alpha" if renamed else "variable_outer"
    inner = "variable_beta" if renamed else "variable_inner"
    problem = minimal_problem_ir()
    problem["variables"] = [
        {
            "id": outer, "name": "free_name" if renamed else "outer",
            "domain_id": "domain_integer", "role": "bound", "span_ids": [],
        },
        {
            "id": inner, "name": "inner_renamed" if renamed else "inner",
            "domain_id": "domain_integer", "role": "bound", "span_ids": [],
        },
        {
            "id": "variable_free", "name": "free_name",
            "domain_id": "domain_integer", "role": "free", "span_ids": [],
        },
    ]
    problem["expressions"] = [
        {
            "id": "expression_outer", "kind": "variable", "variable_id": outer,
            "domain_id": "domain_integer", "span_ids": [],
        },
        {
            "id": "expression_inner", "kind": "variable", "variable_id": inner,
            "domain_id": "domain_integer", "span_ids": [],
        },
        {
            "id": "expression_free", "kind": "variable",
            "variable_id": "variable_free", "domain_id": "domain_integer",
            "span_ids": [],
        },
    ]
    problem["relations"] = [
        {
            "id": "relation_bound", "kind": "equal",
            "operand_expr_ids": ["expression_outer", "expression_inner"],
            "span_ids": [],
        },
        {
            "id": "relation_free", "kind": "equal",
            "operand_expr_ids": ["expression_free", "expression_inner"],
            "span_ids": [],
        },
    ]
    problem["statements"] = [
        {
            "id": "statement_bound", "kind": "relation",
            "relation_id": "relation_bound", "span_ids": [],
        },
        {
            "id": "statement_free", "kind": "relation",
            "relation_id": "relation_free", "span_ids": [],
        },
        {
            "id": "statement_body", "kind": "logical", "operator": "and",
            "operand_statement_ids": ["statement_bound", "statement_free"],
            "span_ids": [],
        },
        {
            "id": "statement_inner", "kind": "quantified", "quantifier": "exists",
            "variable_ids": [inner], "body_statement_id": "statement_body",
            "span_ids": [],
        },
        {
            "id": "statement_outer", "kind": "quantified", "quantifier": "forall",
            "variable_ids": [outer], "body_statement_id": "statement_inner",
            "span_ids": [],
        },
    ]
    problem["goals"][0]["statement_id"] = "statement_outer"  # type: ignore[index]
    return problem


def _forge(result, **changes):
    forged = object.__new__(CanonicalNormalizationResult)
    for field in CanonicalNormalizationResult.__slots__:
        object.__setattr__(forged, field, changes.get(field, getattr(result, field)))
    return forged


class CanonicalNormalizationTests(unittest.TestCase):
    def test_minimal_result_is_canonical_replayable_and_non_authoritative(self) -> None:
        result = _result()
        self.assertEqual(result.contract_sha256, CONTRACT_SHA256)
        self.assertEqual(result.rule_catalogue_sha256, RULE_CATALOGUE_SHA256)
        self.assertFalse(result.mathematical_authority)
        self.assertTrue(result.candidates)
        self.assertTrue(result.candidates[0].normal_forms)
        self.assertTrue(result.candidates[0].contexts)
        self.assertTrue(result.candidates[0].obligations)
        raw = canonical_normalization_result_bytes(result)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertEqual(parse_canonical_normalization_result(raw), result)
        self.assertEqual(canonical_normalization_result_sha256(result), result.result_sha256)

    def test_bound_alpha_renaming_preserves_semantic_graph_identity(self) -> None:
        first = minimal_problem_ir()
        second = copy.deepcopy(first)
        second["variables"][0]["id"] = "variable_z"  # type: ignore[index]
        second["variables"][0]["name"] = "z"  # type: ignore[index]
        second["expressions"][0]["variable_id"] = "variable_z"  # type: ignore[index]
        second["statements"][1]["variable_ids"] = ["variable_z"]  # type: ignore[index]
        left = _result(first).candidates[0]
        right = _result(second).candidates[0]
        self.assertNotEqual(left.source_graph_sha256, right.source_graph_sha256)
        self.assertEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)

    def test_binary_equal_and_not_equal_are_exactly_commutative(self) -> None:
        for kind in ("equal", "not_equal"):
            with self.subTest(kind=kind):
                left = _result(_free_binary_problem(kind)).candidates[0]
                right = _result(_free_binary_problem(kind, swapped=True)).candidates[0]
                self.assertNotEqual(left.source_graph_sha256, right.source_graph_sha256)
                self.assertEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)
                traces = [
                    item for item in right.traces
                    if item.kind == "commutative_operand"
                    and item.owner_ref == "relation_reflexive"
                ]
                self.assertEqual({item.canonical_index for item in traces}, {0, 1})

    def test_ordered_relation_change_remains_distinguishable(self) -> None:
        for kind in ("less", "less_equal", "greater", "greater_equal"):
            with self.subTest(kind=kind):
                left = _result(_free_binary_problem(kind)).candidates[0]
                right = _result(_free_binary_problem(kind, swapped=True)).candidates[0]
                self.assertNotEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)

    def test_logical_allowlist_is_commutative_but_implication_is_ordered(self) -> None:
        for operator in ("and", "or", "iff"):
            with self.subTest(operator=operator):
                left = _result(_logical_problem(operator)).candidates[0]
                right = _result(_logical_problem(operator, swapped=True)).candidates[0]
                self.assertEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)
        implication = _result(_logical_problem("implies")).candidates[0]
        reversed_implication = _result(
            _logical_problem("implies", swapped=True)
        ).candidates[0]
        self.assertNotEqual(
            implication.semantic_graph_sha256,
            reversed_implication.semantic_graph_sha256,
        )

    def test_namespaced_application_never_infers_commutativity(self) -> None:
        left = _result(_apply_problem()).candidates[0]
        right = _result(_apply_problem(swapped=True)).candidates[0]
        self.assertNotEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)
        apply_form = next(
            item for item in left.normal_forms if item.source_ref == "expression_apply"
        )
        self.assertEqual(apply_form.rule_ids, ("mh.canonical.preserve.ordered",))

    def test_definition_parameter_alpha_renaming_is_owner_scoped(self) -> None:
        first = minimal_problem_ir()
        first["variables"].append(  # type: ignore[union-attr]
            {
                "id": "variable_parameter", "name": "p",
                "domain_id": "domain_integer", "role": "parameter", "span_ids": [],
            }
        )
        first["expressions"].append(  # type: ignore[union-attr]
            {
                "id": "expression_parameter", "kind": "variable",
                "variable_id": "variable_parameter", "domain_id": "domain_integer",
                "span_ids": [],
            }
        )
        first["definitions"].append(  # type: ignore[union-attr]
            {
                "id": "definition_identity", "name": "identity",
                "parameter_variable_ids": ["variable_parameter"],
                "result_domain_id": "domain_integer",
                "body": {"kind": "expression", "expression_id": "expression_parameter"},
                "recursive": False, "span_ids": [],
            }
        )
        first["readings"][0]["definition_ids"] = ["definition_identity"]  # type: ignore[index]
        second = copy.deepcopy(first)
        parameter = next(item for item in second["variables"] if item["id"] == "variable_parameter")  # type: ignore[union-attr]
        parameter["id"] = "variable_argument"
        parameter["name"] = "argument"
        expression = next(item for item in second["expressions"] if item["id"] == "expression_parameter")  # type: ignore[union-attr]
        expression["variable_id"] = "variable_argument"
        second["definitions"][0]["parameter_variable_ids"] = ["variable_argument"]  # type: ignore[index]
        self.assertEqual(
            _result(first).candidates[0].semantic_graph_sha256,
            _result(second).candidates[0].semantic_graph_sha256,
        )

    def test_nested_alpha_scope_is_capture_safe_and_free_identity_is_preserved(self) -> None:
        left = _result(_nested_binder_problem()).candidates[0]
        right = _result(_nested_binder_problem(renamed=True)).candidates[0]
        self.assertEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)
        changed_free = _nested_binder_problem(renamed=True)
        free = next(item for item in changed_free["variables"] if item["id"] == "variable_free")  # type: ignore[union-attr]
        free["id"] = "variable_other_free"
        free["name"] = "other_free"
        expression = next(item for item in changed_free["expressions"] if item["id"] == "expression_free")  # type: ignore[union-attr]
        expression["variable_id"] = "variable_other_free"
        self.assertNotEqual(
            left.semantic_graph_sha256,
            _result(changed_free).candidates[0].semantic_graph_sha256,
        )

    def test_binder_order_remains_semantic_for_ordered_body(self) -> None:
        first = minimal_problem_ir()
        first["variables"] = [  # type: ignore[assignment]
            {
                "id": "variable_a", "name": "a", "domain_id": "domain_integer",
                "role": "bound", "span_ids": [],
            },
            {
                "id": "variable_b", "name": "b", "domain_id": "domain_integer",
                "role": "bound", "span_ids": [],
            },
        ]
        first["expressions"] = [  # type: ignore[assignment]
            {
                "id": "expression_a", "kind": "variable", "variable_id": "variable_a",
                "domain_id": "domain_integer", "span_ids": [],
            },
            {
                "id": "expression_b", "kind": "variable", "variable_id": "variable_b",
                "domain_id": "domain_integer", "span_ids": [],
            },
        ]
        first["relations"] = [  # type: ignore[assignment]
            {
                "id": "relation_ordered", "kind": "less",
                "operand_expr_ids": ["expression_a", "expression_b"], "span_ids": [],
            }
        ]
        first["statements"] = [  # type: ignore[assignment]
            {
                "id": "statement_body", "kind": "relation",
                "relation_id": "relation_ordered", "span_ids": [],
            },
            {
                "id": "statement_forall", "kind": "quantified", "quantifier": "forall",
                "variable_ids": ["variable_a", "variable_b"],
                "body_statement_id": "statement_body", "span_ids": [],
            },
        ]
        second = copy.deepcopy(first)
        second["statements"][1]["variable_ids"].reverse()  # type: ignore[index,union-attr]
        self.assertNotEqual(
            _result(first).candidates[0].semantic_graph_sha256,
            _result(second).candidates[0].semantic_graph_sha256,
        )

    def test_all_domain_variants_and_unresolved_readings_remain_separate(self) -> None:
        result = _result(_rich_problem())
        self.assertEqual(result.ambiguity_status, "unresolved")
        self.assertIsNone(result.selected_reading_id)
        self.assertEqual(
            [item.reading_id for item in result.candidates],
            ["reading_only", "reading_secondary"],
        )
        expected_domain_kinds = {
            "builtin", "finite", "interval", "modular", "collection",
            "product", "function", "structure",
        }
        for candidate in result.candidates:
            domain_forms = {
                item.value["kind"] for item in candidate.normal_forms
                if item.form_kind == "domain"
            }
            self.assertEqual(domain_forms, expected_domain_kinds)
            self.assertEqual(candidate.goal_ids, tuple(_rich_problem()["readings"][0]["goal_ids"]))

    def test_assumption_source_order_is_canonical_but_roles_and_content_remain(self) -> None:
        left = _result(_assumption_problem()).candidates[0]
        right = _result(_assumption_problem(swapped=True)).candidates[0]
        self.assertEqual(left.semantic_graph_sha256, right.semantic_graph_sha256)
        occurrences = left.contexts[0].assumption_occurrences
        self.assertEqual(
            [item.role for item in occurrences],
            ["domain_fact", "variable_fact", "given", "side_condition"],
        )
        self.assertEqual({item.source_index for item in occurrences}, set(range(4)))
        self.assertEqual({item.canonical_index for item in occurrences}, set(range(4)))

    def test_trace_groups_are_complete_reversible_permutations(self) -> None:
        candidate = _result(_assumption_problem(swapped=True)).candidates[0]
        groups: dict[tuple[str, str, str], list[object]] = {}
        for trace in candidate.traces:
            canonical_occurrence_trace_bytes(trace)
            groups.setdefault((trace.owner_kind, trace.owner_ref, trace.kind), []).append(trace)
        for traces in groups.values():
            self.assertEqual(
                {item.source_index for item in traces}, set(range(len(traces)))
            )
            self.assertEqual(
                {item.canonical_index for item in traces}, set(range(len(traces)))
            )

    def test_every_public_component_codec_recomputes_its_identity(self) -> None:
        candidate = _result().candidates[0]
        for form in candidate.normal_forms:
            self.assertTrue(canonical_normal_form_bytes(form).endswith(b"\n"))
        for context in candidate.contexts:
            self.assertTrue(canonical_context_bytes(context).endswith(b"\n"))
        for obligation in candidate.obligations:
            self.assertTrue(canonical_obligation_bytes(obligation).endswith(b"\n"))
        for trace in candidate.traces:
            self.assertTrue(canonical_occurrence_trace_bytes(trace).endswith(b"\n"))

    def test_invalid_and_exhausted_inputs_return_no_partial_artifacts(self) -> None:
        for value in (None, bytearray(), memoryview(b"{}"), b"{}"):
            result = normalize_canonical_obligations(value)  # type: ignore[arg-type]
            self.assertIn(result.status, {"invalid", "exhausted"})
            self.assertIsNone(result.input_result_sha256)
            self.assertIsNone(result.proof_result_bytes)
            self.assertIsNone(result.result_sha256)
            self.assertEqual(result.candidates, ())
        with mock.patch.object(normalization_module, "MAX_INPUT_BYTES", 1):
            exhausted = normalize_canonical_obligations(_proof_bytes())
        self.assertEqual(exhausted.status, "exhausted")
        self.assertEqual(exhausted.reason_code, "BUDGET_EXHAUSTED")
        self.assertEqual(exhausted.candidates, ())
        with mock.patch.object(normalization_module, "MAX_STEPS", 0):
            work_exhausted = normalize_canonical_obligations(_proof_bytes())
        self.assertEqual(work_exhausted.status, "exhausted")
        self.assertIsNone(work_exhausted.result_sha256)

    def test_failed_upstream_exact_subclasses_and_fatal_exceptions_fail_safely(self) -> None:
        failed_upstream = decompose_proof_obligations(b"{}")
        normalized = normalize_canonical_obligations(
            proof_obligation_result_bytes(failed_upstream)
        )
        self.assertEqual(normalized.status, "invalid")
        self.assertEqual(normalized.candidates, ())

        class EvilBytes(bytes):
            pass

        subclassed = normalize_canonical_obligations(EvilBytes(_proof_bytes()))
        self.assertEqual(subclassed.status, "invalid")
        with mock.patch.object(
            normalization_module,
            "parse_proof_obligation_result",
            side_effect=MemoryError("fatal"),
        ):
            with self.assertRaises(MemoryError):
                normalize_canonical_obligations(_proof_bytes())

    def test_strict_parser_rejects_noncanonical_and_repaired_outer_forgery(self) -> None:
        raw = canonical_normalization_result_bytes(_result())
        with self.assertRaises(CanonicalNormalizationValidationError):
            parse_canonical_normalization_result(raw.rstrip(b"\n"))
        value = json.loads(raw)
        value["candidates"][0]["obligations"][0]["status"] = "ready"
        without_digest = dict(value)
        without_digest.pop("result_sha256")
        value["result_sha256"] = hashlib.sha256(
            (json.dumps(without_digest, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        ).hexdigest()
        forged = (
            json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()
        with self.assertRaises(CanonicalNormalizationValidationError):
            parse_canonical_normalization_result(forged)

    def test_result_is_final_immutable_copy_safe_and_not_pickle_authority(self) -> None:
        result = _result()
        with self.assertRaises(PermissionError):
            CanonicalNormalizationResult()
        with self.assertRaises(TypeError):
            class Forged(CanonicalNormalizationResult):
                pass
        with self.assertRaises(FrozenInstanceError):
            result.status = "invalid"  # type: ignore[misc]
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):
            pickle.dumps(result)

    def test_public_validator_rejects_forged_nested_and_outer_values(self) -> None:
        result = _result()
        with self.assertRaises(CanonicalNormalizationValidationError):
            validate_canonical_normalization_result(
                _forge(result, reason_code="DECOMPOSED")
            )
        candidate = result.candidates[0]
        obligation = replace(candidate.obligations[0], status="ready")
        forged_candidate = replace(
            candidate, obligations=(obligation, *candidate.obligations[1:])
        )
        with self.assertRaises(CanonicalNormalizationValidationError):
            validate_canonical_normalization_result(
                _forge(result, candidates=(forged_candidate,))
            )

    def test_component_codecs_reject_stale_hashes_indexes_and_authority(self) -> None:
        candidate = _result().candidates[0]
        with self.assertRaises(CanonicalNormalizationValidationError):
            canonical_normal_form_bytes(
                replace(candidate.normal_forms[0], semantic_sha256="0" * 64)
            )
        with self.assertRaises(CanonicalNormalizationValidationError):
            canonical_occurrence_trace_bytes(
                replace(candidate.traces[0], source_index=-1)
            )
        with self.assertRaises(CanonicalNormalizationValidationError):
            canonical_context_bytes(
                replace(candidate.contexts[0], mathematical_authority=True)
            )
        with self.assertRaises(CanonicalNormalizationValidationError):
            canonical_obligation_bytes(
                replace(candidate.obligations[0], semantic_sha256="f" * 64)
            )

    def test_frozen_artifact_hashes_are_exact(self) -> None:
        artifacts = {
            "docs/contracts/schemas/canonical-normal-form-v1.schema.json": "d6dc45e60c9d494a70859631403ee7cf6e454f71d7b78dbffb528ae7550d5e9c",
            "docs/contracts/schemas/canonical-occurrence-trace-v1.schema.json": "01622e476a2fb3b72a9306cd656db6e7525604b1c6f4e680395e9b12cde74fec",
            "docs/contracts/schemas/canonical-context-v1.schema.json": "e43588f34e29eb980efcc2f42600036803d7fb17dad8039aa18d7b1e6f6bf860",
            "docs/contracts/schemas/canonical-obligation-v1.schema.json": "c6fade940f24fb23f4d16dcb324d3aff5bb35a923748d30b2f93fb302b436d58",
            "docs/contracts/schemas/canonical-normalization-rules-v1.schema.json": "845843f01d2b7dfcb0530f028e53b161d283489cc10292c3376af39809609ff7",
            "docs/contracts/schemas/canonical-normalization-result-v1.schema.json": "37ef5d35dcba90f32b53559719a08ebca12d8ffa9a0075ea99f6ac18efe18952",
            "docs/normalization/canonical-normalization-rules-v1.json": RULE_CATALOGUE_SHA256,
        }
        for relative, expected in artifacts.items():
            with self.subTest(relative=relative):
                self.assertEqual(
                    hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(), expected
                )
        catalogue = json.loads(
            (ROOT / "docs/normalization/canonical-normalization-rules-v1.json").read_bytes()
        )
        commutative = {
            item["rule_id"] for item in catalogue["rules"]
            if item["rule_kind"] == "commutative"
        }
        self.assertEqual(
            commutative,
            {
                "mh.canonical.commutative.logical-and",
                "mh.canonical.commutative.logical-or",
                "mh.canonical.commutative.logical-iff",
                "mh.canonical.commutative.relation-equal",
                "mh.canonical.commutative.relation-not-equal",
            },
        )

    def test_repeated_processes_and_hash_seeds_are_byte_identical(self) -> None:
        script = """
import sys
sys.path[:0]=['src','.']
from tools.validate_problem_ir_contract import minimal_problem_ir
from mathhead.problem_intake import intake_problem,problem_intake_result_bytes
from mathhead.problem_readings import analyze_problem_readings,reading_analysis_result_bytes
from mathhead.domain_assumptions import normalize_domain_assumptions,domain_assumption_result_bytes
from mathhead.proof_obligations import decompose_proof_obligations,proof_obligation_result_bytes
from mathhead.canonical_normalization import normalize_canonical_obligations,canonical_normalization_result_sha256
p=minimal_problem_ir();i=intake_problem({'schema':'mathhead.problem-intake.v1','problem':p})
a=analyze_problem_readings(problem_intake_result_bytes(i));d=normalize_domain_assumptions(reading_analysis_result_bytes(a))
o=decompose_proof_obligations(domain_assumption_result_bytes(d));n=normalize_canonical_obligations(proof_obligation_result_bytes(o))
print(canonical_normalization_result_sha256(n))
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
