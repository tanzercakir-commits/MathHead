from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import mathhead.proof_obligations as production  # noqa: E402
from mathhead.domain_assumptions import (  # noqa: E402
    domain_assumption_result_bytes,
    normalize_domain_assumptions,
)
from mathhead.problem_intake import intake_problem, problem_intake_result_bytes  # noqa: E402
from mathhead.problem_readings import (  # noqa: E402
    analyze_problem_readings,
    reading_analysis_result_bytes,
)
from tools.validate_proof_obligations import _rich_problem  # noqa: E402


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _domain_bytes() -> bytes:
    intake = intake_problem({"schema": "mathhead.problem-intake.v1", "problem": _rich_problem()})
    if intake.status != "accepted":
        raise AssertionError((intake.reason_code, intake.diagnostics))
    readings = analyze_problem_readings(problem_intake_result_bytes(intake))
    if readings.status != "analyzed":
        raise AssertionError((readings.reason_code, readings.diagnostics))
    normalized = normalize_domain_assumptions(reading_analysis_result_bytes(readings))
    if normalized.status != "normalized":
        raise AssertionError((normalized.reason_code, normalized.diagnostics))
    return domain_assumption_result_bytes(normalized)


def _result():
    result = production.decompose_proof_obligations(_domain_bytes())
    if result.status != "decomposed":
        raise AssertionError((result.reason_code, result.diagnostics))
    return result


def _nodes(graph):
    return {item.obligation_id: item for item in graph.obligations}


def _roots(graph):
    nodes = _nodes(graph)
    return {
        goal_id: nodes[root_id]
        for goal_id, root_id in zip(graph.goal_ids, graph.root_obligation_ids, strict=True)
    }


def _rehash(obligation, **changes):
    provisional = replace(obligation, **changes)
    digest = hashlib.sha256(
        production._canonical_bytes(  # noqa: SLF001
            production._obligation_mapping(  # noqa: SLF001
                provisional,
                include_digest=False,
            )
        )
    ).hexdigest()
    return replace(provisional, obligation_sha256=digest)


class ProofObligationAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.input_bytes = _domain_bytes()
        cls.result = production.decompose_proof_obligations(cls.input_bytes)
        if cls.result.status != "decomposed":
            raise AssertionError((cls.result.reason_code, cls.result.diagnostics))

    def test_every_relation_kind_gets_only_exact_catalogue_matches(self) -> None:
        graph = self.result.candidates[0].graph
        roots = _roots(graph)
        expected = {
            "not_equal": "mh.strategy.disequality",
            "less": "mh.strategy.ordered-relation",
            "less_equal": "mh.strategy.ordered-relation",
            "greater": "mh.strategy.ordered-relation",
            "greater_equal": "mh.strategy.ordered-relation",
            "member": "mh.strategy.membership",
            "not_member": "mh.strategy.membership",
            "divides": "mh.strategy.divisibility",
            "congruent": "mh.strategy.congruence",
            "predicate": "mh.strategy.named-predicate",
        }
        for suffix, strategy_id in expected.items():
            with self.subTest(relation=suffix):
                root = roots[f"goal_{suffix}"]
                identifiers = {item.strategy_id for item in root.admissible_strategies}
                self.assertIn(strategy_id, identifiers)
                self.assertTrue(all(not item.guarantees_success for item in root.admissible_strategies))

    def test_all_domain_shapes_remain_reachable_and_exactly_match_hints(self) -> None:
        graph = self.result.candidates[0].graph
        roots = _roots(graph)
        for suffix in (
            "finite", "interval", "modular", "collection", "product",
            "function", "structure", "real",
        ):
            with self.subTest(domain=suffix):
                root = roots[f"goal_domain_{suffix}"]
                self.assertIn(f"domain_{suffix}", root.dependency_ids)
        finite = {item.strategy_id for item in roots["goal_domain_finite"].admissible_strategies}
        modular = {item.strategy_id for item in roots["goal_domain_modular"].admissible_strategies}
        real = {item.strategy_id for item in roots["goal_domain_real"].admissible_strategies}
        self.assertIn("mh.strategy.finite-enumeration", finite)
        self.assertIn("mh.strategy.modular-domain", modular)
        self.assertIn("mh.strategy.numeric-domain", real)

    def test_unresolved_readings_stay_separate_and_preserve_goal_order(self) -> None:
        self.assertEqual(self.result.ambiguity_status, "unresolved")
        self.assertIsNone(self.result.selected_reading_id)
        self.assertEqual(
            [item.reading_id for item in self.result.candidates],
            ["reading_only", "reading_secondary"],
        )
        first, second = (item.graph for item in self.result.candidates)
        self.assertEqual(first.goal_ids, second.goal_ids)
        self.assertNotEqual(first.normalized_context_sha256, second.normalized_context_sha256)
        self.assertTrue(all(item.reading_id == first.reading_id for item in first.obligations))
        self.assertTrue(all(item.reading_id == second.reading_id for item in second.obligations))

    def test_context_retains_definition_all_assumption_roles_and_source_origin(self) -> None:
        raw = json.loads(production.proof_obligation_result_bytes(self.result))
        upstream = raw["domain_assumption_result"]["candidates"][0]["context"]
        roles = {
            item["assumption_role"] for item in upstream["facts"]
            if item["assumption_role"] is not None
        }
        self.assertEqual(roles, {"given", "domain_constraint", "side_condition"})
        graph = self.result.candidates[0].graph
        contexts = {digest: context for digest, context in graph.local_contexts}
        root = _roots(graph)["goal_reflexive"]
        context = contexts[root.local_context_sha256]
        self.assertEqual(context.definition_ids, ("definition_truth",))
        self.assertEqual(
            context.assumption_fact_sha256s,
            tuple(item["fact_sha256"] for item in upstream["facts"]),
        )
        self.assertEqual(root.source_span_ids, ("span_fixture",))
        self.assertEqual(context.source_span_ids, ())

    def test_structural_statuses_choices_modes_and_witnesses_are_not_verdicts(self) -> None:
        graph = self.result.candidates[0].graph
        roots = _roots(graph)
        self.assertEqual(roots["goal_or"].status, "choice_required")
        self.assertEqual(roots["goal_and"].status, "waiting")
        self.assertEqual(roots["goal_true"].status, "ready")
        mode_strategies = {
            "goal_refute": "mh.strategy.counterexample-search",
            "goal_witness": "mh.strategy.witness-construction",
            "goal_compute": "mh.strategy.exact-computation",
            "goal_classify": "mh.strategy.classification",
            "goal_optimize": "mh.strategy.optimization",
        }
        for goal_id, strategy_id in mode_strategies.items():
            identifiers = {item.strategy_id for item in roots[goal_id].admissible_strategies}
            self.assertIn(strategy_id, identifiers)
        exists = roots["goal_exists"]
        nodes = _nodes(graph)
        construction, verification = (nodes[item] for item in exists.child_obligation_ids)
        self.assertEqual(construction.kind, "witness_construction")
        self.assertEqual(verification.kind, "witness_verification")
        self.assertEqual(verification.prerequisite_obligation_ids, (construction.obligation_id,))
        self.assertTrue(construction.witness_placeholder_ids)
        self.assertTrue(all(item.mathematical_authority is False for item in graph.obligations))

    def test_repaired_wrong_status_and_unknown_strategy_fail_graph_boundary(self) -> None:
        graph = self.result.candidates[0].graph
        original = graph.obligations[0]
        wrong_status = _rehash(original, status="unsupported")
        forged = replace(
            graph,
            obligations=(wrong_status, *graph.obligations[1:]),
            obligation_sha256s=(wrong_status.obligation_sha256, *graph.obligation_sha256s[1:]),
        )
        with self.assertRaises(production.ProofObligationValidationError):
            production.proof_obligation_graph_bytes(forged)
        context = graph.local_contexts[0][1]
        forged_context = replace(context, dependency_ids=("variable_x", "domain_integer"))
        with self.assertRaises(production.ProofObligationValidationError):
            production.proof_obligation_local_context_bytes(forged_context)
        strategy = replace(
            original.admissible_strategies[0],
            strategy_id="mh.strategy.fabricated",
        )
        wrong_strategy = _rehash(original, admissible_strategies=(strategy,))
        forged = replace(
            graph,
            obligations=(wrong_strategy, *graph.obligations[1:]),
            obligation_sha256s=(wrong_strategy.obligation_sha256, *graph.obligation_sha256s[1:]),
        )
        with self.assertRaises(production.ProofObligationValidationError):
            production.proof_obligation_graph_bytes(forged)

    def test_repaired_cycle_parent_and_prerequisite_order_fail_graph_boundary(self) -> None:
        graph = self.result.candidates[0].graph
        leaf = graph.obligations[0]
        cycle = _rehash(
            leaf,
            child_obligation_ids=(leaf.obligation_id,),
            status="waiting",
        )
        forged = replace(
            graph,
            obligations=(cycle, *graph.obligations[1:]),
            obligation_sha256s=(cycle.obligation_sha256, *graph.obligation_sha256s[1:]),
        )
        with self.assertRaises(production.ProofObligationValidationError):
            production.proof_obligation_graph_bytes(forged)
        future = graph.obligations[1]
        prerequisite = _rehash(
            leaf,
            prerequisite_obligation_ids=(future.obligation_id,),
            status="waiting",
        )
        forged = replace(
            graph,
            obligations=(prerequisite, *graph.obligations[1:]),
            obligation_sha256s=(prerequisite.obligation_sha256, *graph.obligation_sha256s[1:]),
        )
        with self.assertRaises(production.ProofObligationValidationError):
            production.proof_obligation_graph_bytes(forged)

    def test_unknown_fields_floats_bools_nul_non_nfc_and_duplicates_fail_closed(self) -> None:
        raw_value = json.loads(self.input_bytes)
        mutations = []
        unknown = json.loads(self.input_bytes)
        unknown["unknown"] = None
        mutations.append(_canonical(unknown))
        floating = json.loads(self.input_bytes)
        floating["candidates"][0]["context"]["facts"][0]["ordinal"] = 0.5
        mutations.append(_canonical(floating))
        boolean = json.loads(self.input_bytes)
        boolean["candidates"][0]["context"]["facts"][0]["ordinal"] = False
        mutations.append(_canonical(boolean))
        nul = json.loads(self.input_bytes)
        nul["readings_result"]["candidates"][0]["projection"]["label"] += "\x00"
        mutations.append(_canonical(nul))
        non_nfc = json.loads(self.input_bytes)
        non_nfc["readings_result"]["candidates"][0]["projection"]["label"] += "e\u0301"
        mutations.append(_canonical(non_nfc))
        duplicate = self.input_bytes.replace(
            b'{"ambiguity_status"',
            b'{"ambiguity_status":null,"ambiguity_status"',
            1,
        )
        mutations.append(duplicate)
        self.assertEqual(raw_value["status"], "normalized")
        for payload in mutations:
            with self.subTest(payload=payload[:40]):
                result = production.decompose_proof_obligations(payload)
                self.assertIn(result.status, {"invalid", "exhausted"})
                self.assertEqual(result.candidates, ())
                self.assertIsNone(result.input_result_sha256)

    def test_obligation_graph_and_output_budgets_fail_without_partial_graphs(self) -> None:
        for field, value in (
            ("MAX_STEPS", 0),
            ("MAX_OBLIGATIONS", 1),
            ("MAX_OUTPUT_BYTES", 1),
        ):
            with self.subTest(budget=field), mock.patch.object(production, field, value):
                result = production.decompose_proof_obligations(self.input_bytes)
                self.assertEqual(result.status, "exhausted")
                self.assertEqual(result.reason_code, "BUDGET_EXHAUSTED")
                self.assertEqual(result.candidates, ())
                self.assertIsNone(result.input_result_sha256)

    def test_independent_fixture_is_byte_stable_on_repeated_runs(self) -> None:
        first = production.proof_obligation_result_bytes(self.result)
        second = production.proof_obligation_result_bytes(
            production.decompose_proof_obligations(self.input_bytes)
        )
        self.assertEqual(first, second)
        self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())


if __name__ == "__main__":
    unittest.main()
