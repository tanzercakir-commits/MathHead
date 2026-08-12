from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
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

import mathhead.proof_obligations as obligation_module  # noqa: E402
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
    CONTRACT_SHA256,
    DECOMPOSITION_CATALOGUE_SHA256,
    STRATEGY_CATALOGUE_SHA256,
    ProofObligationDecompositionResult,
    ProofObligationValidationError,
    decompose_proof_obligations,
    parse_proof_obligation_result,
    proof_obligation_bytes,
    proof_obligation_graph_bytes,
    proof_obligation_local_context_bytes,
    proof_obligation_result_bytes,
    proof_obligation_result_sha256,
    validate_proof_obligation_result,
)
from tools.validate_problem_ir_contract import minimal_problem_ir  # noqa: E402


REGISTRIES = (
    "source_documents", "source_spans", "domains", "variables", "expressions",
    "relations", "statements", "definitions", "assumptions", "goals", "readings",
)


def _sort(problem: dict[str, object]) -> None:
    for registry in REGISTRIES:
        problem[registry].sort(key=lambda item: item["id"])  # type: ignore[union-attr,index]


def _domain_bytes(problem: dict[str, object] | None = None) -> bytes:
    value = problem if problem is not None else minimal_problem_ir()
    _sort(value)
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": value})
    if intake.status != "accepted":
        raise AssertionError((intake.status, intake.reason_code, intake.diagnostics))
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    if readings.status != "analyzed":
        raise AssertionError((readings.status, readings.reason_code, readings.diagnostics))
    normalized = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    if normalized.status != "normalized":
        raise AssertionError((normalized.status, normalized.reason_code, normalized.diagnostics))
    return domain_assumption_result_bytes(normalized)


def _result(problem: dict[str, object] | None = None):
    result = decompose_proof_obligations(_domain_bytes(problem))
    if result.status != "decomposed":
        raise AssertionError((result.status, result.reason_code, result.diagnostics))
    return result


def _forge(result, **changes):
    forged = object.__new__(ProofObligationDecompositionResult)
    for field in ProofObligationDecompositionResult.__slots__:
        object.__setattr__(forged, field, changes.get(field, getattr(result, field)))
    return forged


def _logic_problem() -> dict[str, object]:
    problem = minimal_problem_ir()
    statements = problem["statements"]  # type: ignore[assignment]
    statements.extend(
        [
            {"id": "statement_true", "kind": "truth", "value": True, "span_ids": []},
            {"id": "statement_false", "kind": "truth", "value": False, "span_ids": []},
            {"id": "statement_not", "kind": "logical", "operator": "not", "operand_statement_ids": ["statement_false"], "span_ids": []},
            {"id": "statement_and", "kind": "logical", "operator": "and", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
            {"id": "statement_or", "kind": "logical", "operator": "or", "operand_statement_ids": ["statement_false", "statement_true"], "span_ids": []},
            {"id": "statement_implies", "kind": "logical", "operator": "implies", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
            {"id": "statement_iff", "kind": "logical", "operator": "iff", "operand_statement_ids": ["statement_true", "statement_false"], "span_ids": []},
            {"id": "statement_exists", "kind": "quantified", "quantifier": "exists", "variable_ids": ["variable_exists"], "body_statement_id": "statement_true", "span_ids": []},
            {"id": "statement_unique", "kind": "quantified", "quantifier": "exists_unique", "variable_ids": ["variable_unique"], "body_statement_id": "statement_true", "span_ids": []},
        ]
    )
    problem["variables"].extend(  # type: ignore[union-attr]
        [
            {"id": "variable_exists", "name": "e", "domain_id": "domain_integer", "role": "bound", "span_ids": []},
            {"id": "variable_unique", "name": "u", "domain_id": "domain_integer", "role": "bound", "span_ids": []},
        ]
    )
    problem["definitions"].append(  # type: ignore[union-attr]
        {"id": "definition_true", "name": "T", "parameter_variable_ids": [], "result_domain_id": None, "body": {"kind": "statement", "statement_id": "statement_true"}, "recursive": False, "span_ids": []}
    )
    problem["assumptions"].append(  # type: ignore[union-attr]
        {"id": "assumption_true", "statement_id": "statement_true", "role": "given", "span_ids": []}
    )
    goal_specs = [
        ("goal_truth", "statement_true", "prove"),
        ("goal_not", "statement_not", "prove"),
        ("goal_and", "statement_and", "prove"),
        ("goal_or", "statement_or", "prove"),
        ("goal_implies", "statement_implies", "prove"),
        ("goal_iff", "statement_iff", "prove"),
        ("goal_forall", "statement_forall", "prove"),
        ("goal_exists", "statement_exists", "prove"),
        ("goal_unique", "statement_unique", "prove"),
        ("goal_refute", "statement_true", "refute"),
        ("goal_witness", "statement_true", "find_witness"),
        ("goal_compute", "statement_true", "compute"),
        ("goal_classify", "statement_true", "classify"),
        ("goal_optimize", "statement_true", "optimize"),
    ]
    problem["goals"] = [
        {"id": goal_id, "statement_id": statement_id, "mode": mode, "span_ids": []}
        for goal_id, statement_id, mode in goal_specs
    ]
    reading = problem["readings"][0]  # type: ignore[index]
    reading["definition_ids"] = ["definition_true"]
    reading["assumption_ids"] = ["assumption_true"]
    reading["goal_ids"] = [item[0] for item in goal_specs]
    return problem


class ProofObligationTests(unittest.TestCase):
    def test_minimal_graph_is_canonical_replayable_and_non_authoritative(self) -> None:
        result = _result()
        self.assertEqual(result.contract_sha256, CONTRACT_SHA256)
        self.assertEqual(result.decomposition_catalogue_sha256, DECOMPOSITION_CATALOGUE_SHA256)
        self.assertEqual(result.strategy_catalogue_sha256, STRATEGY_CATALOGUE_SHA256)
        self.assertIs(result.mathematical_authority, False)
        graph = result.candidates[0].graph
        self.assertEqual([item.kind for item in graph.obligations], ["universal", "relation"])
        self.assertEqual([item.status for item in graph.obligations], ["waiting", "ready"])
        self.assertEqual(parse_proof_obligation_result(proof_obligation_result_bytes(result)), result)
        self.assertEqual(len(proof_obligation_result_sha256(result)), 64)

    def test_all_logical_quantified_and_goal_mode_branches_are_explicit(self) -> None:
        graph = _result(_logic_problem()).candidates[0].graph
        kinds = [item.kind for item in graph.obligations]
        for expected in (
            "truth", "negation", "conjunction", "disjunction", "implication",
            "biconditional", "universal", "existential", "unique_existence",
            "witness_construction", "witness_verification", "uniqueness",
            "refutation", "witness_search", "computation", "classification",
            "optimization",
        ):
            self.assertIn(expected, kinds)
        disjunction = next(item for item in graph.obligations if item.kind == "disjunction")
        self.assertEqual(disjunction.status, "choice_required")
        alternatives = [
            item for item in graph.obligations
            if item.alternative_group_id == f"alternative_{disjunction.obligation_id}"
        ]
        self.assertEqual([item.alternative_index for item in alternatives], [0, 1])
        self.assertEqual(graph.choice_required_obligation_ids, (disjunction.obligation_id,))

    def test_local_contexts_preserve_definitions_facts_binders_and_hypotheses(self) -> None:
        graph = _result(_logic_problem()).candidates[0].graph
        contexts = {digest: context for digest, context in graph.local_contexts}
        implication = next(item for item in graph.obligations if item.root_goal_id == "goal_implies" and item.kind == "implication")
        child = next(item for item in graph.obligations if item.parent_obligation_id == implication.obligation_id)
        child_context = contexts[child.local_context_sha256]
        self.assertEqual(child_context.definition_ids, ("definition_true",))
        self.assertTrue(child_context.assumption_fact_sha256s)
        self.assertEqual(child_context.local_hypothesis_statement_ids, ("statement_true",))
        universal_child = next(item for item in graph.obligations if item.root_goal_id == "goal_forall" and item.kind == "relation")
        self.assertEqual(contexts[universal_child.local_context_sha256].bound_variable_ids, ("variable_x",))

    def test_witness_placeholders_are_symbolic_ordered_and_prerequisite_bound(self) -> None:
        graph = _result(_logic_problem()).candidates[0].graph
        construction = next(item for item in graph.obligations if item.root_goal_id == "goal_exists" and item.kind == "witness_construction")
        verification = next(item for item in graph.obligations if item.root_goal_id == "goal_exists" and item.kind == "witness_verification")
        self.assertEqual(
            construction.witness_placeholder_ids,
            (f"witness_{construction.parent_obligation_id}_variable_exists",),
        )
        self.assertEqual(verification.prerequisite_obligation_ids, (construction.obligation_id,))
        self.assertEqual(verification.status, "waiting")
        uniqueness = next(item for item in graph.obligations if item.kind == "uniqueness")
        self.assertTrue(uniqueness.witness_placeholder_ids)
        self.assertTrue(uniqueness.prerequisite_obligation_ids)

    def test_strategy_matches_are_exact_ordered_and_never_guarantee_success(self) -> None:
        graph = _result().candidates[0].graph
        relation = next(item for item in graph.obligations if item.kind == "relation")
        identifiers = [item.strategy_id for item in relation.admissible_strategies]
        self.assertIn("mh.strategy.equality", identifiers)
        self.assertIn("mh.strategy.numeric-domain", identifiers)
        for item in relation.admissible_strategies:
            self.assertIs(item.guarantees_success, False)
            self.assertIs(item.mathematical_authority, False)

    def test_edges_contexts_obligations_and_graphs_have_closed_codecs(self) -> None:
        graph = _result(_logic_problem()).candidates[0].graph
        ids = {item.obligation_id for item in graph.obligations}
        for edge in graph.edges:
            self.assertIn(edge.from_obligation_id, ids)
            self.assertIn(edge.to_obligation_id, ids)
        self.assertTrue(proof_obligation_bytes(graph.obligations[0]).endswith(b"\n"))
        self.assertTrue(proof_obligation_local_context_bytes(graph.local_contexts[0][1]).endswith(b"\n"))
        self.assertTrue(proof_obligation_graph_bytes(graph).endswith(b"\n"))

    def test_invalid_failed_and_budget_inputs_return_no_partial_artifacts(self) -> None:
        for value in (None, bytearray(), memoryview(b"{}"), b"{}"):
            result = decompose_proof_obligations(value)  # type: ignore[arg-type]
            self.assertIn(result.status, {"invalid", "exhausted"})
            self.assertIsNone(result.input_result_sha256)
            self.assertIsNone(result.domain_result_bytes)
            self.assertEqual(result.candidates, ())
        with mock.patch.object(obligation_module, "MAX_INPUT_BYTES", 1):
            exhausted = decompose_proof_obligations(_domain_bytes())
        self.assertEqual(exhausted.status, "exhausted")
        self.assertEqual(exhausted.candidates, ())

    def test_strict_parser_rejects_noncanonical_and_fabricated_graphs(self) -> None:
        raw = proof_obligation_result_bytes(_result())
        value = json.loads(raw)
        value["candidates"][0]["graph"]["obligations"][0]["status"] = "ready"
        forged = (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaises(ProofObligationValidationError):
            parse_proof_obligation_result(forged)
        with self.assertRaises(ProofObligationValidationError):
            parse_proof_obligation_result(raw.rstrip(b"\n"))

    def test_result_is_closed_immutable_copy_safe_and_not_pickle_authority(self) -> None:
        result = _result()
        with self.assertRaises(PermissionError):
            ProofObligationDecompositionResult()
        with self.assertRaises(TypeError):
            class Forged(ProofObligationDecompositionResult):
                pass
        with self.assertRaises(FrozenInstanceError):
            result.status = "invalid"  # type: ignore[misc]
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):
            pickle.dumps(result)

    def test_public_validator_rejects_forged_closed_values(self) -> None:
        result = _result()
        forged = _forge(result, reason_code="NORMALIZED")
        with self.assertRaises(ProofObligationValidationError):
            validate_proof_obligation_result(forged)
        candidate = result.candidates[0]
        graph = replace(candidate.graph, decomposition_catalogue_sha256="0" * 64)
        forged_graph_result = _forge(
            result,
            candidates=(replace(candidate, graph=graph),),
        )
        with self.assertRaises(ProofObligationValidationError):
            validate_proof_obligation_result(forged_graph_result)

    def test_repeated_processes_and_hash_seeds_are_byte_identical(self) -> None:
        script = """
import sys
sys.path[:0]=['src','.']
from tools.validate_problem_ir_contract import minimal_problem_ir
from mathhead.problem_intake import intake_problem,problem_intake_result_bytes
from mathhead.problem_readings import analyze_problem_readings,reading_analysis_result_bytes
from mathhead.domain_assumptions import normalize_domain_assumptions,domain_assumption_result_bytes
from mathhead.proof_obligations import decompose_proof_obligations,proof_obligation_result_sha256
p=minimal_problem_ir(); i=intake_problem({'schema':'mathhead.problem-intake.v1','problem':p})
a=analyze_problem_readings(problem_intake_result_bytes(i)); n=normalize_domain_assumptions(reading_analysis_result_bytes(a))
print(proof_obligation_result_sha256(decompose_proof_obligations(domain_assumption_result_bytes(n))))
"""
        outputs = []
        for seed in ("1", "19", "random"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            outputs.append(
                subprocess.check_output(
                    [sys.executable, "-c", script], cwd=ROOT, env=environment, text=True
                ).strip()
            )
        self.assertEqual(len(set(outputs)), 1)


if __name__ == "__main__":
    unittest.main()
