from __future__ import annotations

import inspect
import importlib
import io
from pathlib import Path
import sys
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mathhead.discovery.objects import Graph  # noqa: E402

cli = importlib.import_module("mathhead.discovery.cli")
formalize = importlib.import_module("mathhead.discovery.formalize")
generate = importlib.import_module("mathhead.discovery.generate")
nauty_scale = importlib.import_module("mathhead.discovery.nauty_scale")
product = importlib.import_module("mathhead.discovery.product")


EXPECTED_HASH = "3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794"


class GraphBudgetContractTests(unittest.TestCase):
    def test_contract_binding_and_signature(self) -> None:
        signature = inspect.signature(product.graph_search_plan)
        self.assertEqual(list(signature.parameters), ["max_n", "fast_backend_available"])
        self.assertEqual(signature.parameters["max_n"].kind, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        self.assertEqual(signature.parameters["fast_backend_available"].kind,
                         inspect.Parameter.KEYWORD_ONLY)
        self.assertIs(signature.parameters["fast_backend_available"].default,
                      inspect.Parameter.empty)
        plan = product.graph_search_plan(6, fast_backend_available=False)
        self.assertEqual(plan.contract_id, "MH-C-GRAPH-BUDGET-001")
        self.assertEqual(plan.contract_sha256, EXPECTED_HASH)
        self.assertEqual(product.GRAPH_BUDGET_CONTRACT_SHA256, EXPECTED_HASH)

    def test_pure_and_fast_plans_have_exact_limits(self) -> None:
        pure = product.graph_search_plan(6, fast_backend_available=False)
        self.assertEqual(
            (pure.backend, pure.safe_max_n, pure.max_objects, pure.supported, pure.reason),
            ("pure_python", 6, 2_000, True, "pure-backend-within-budget"),
        )
        fast = product.graph_search_plan(8, fast_backend_available=True)
        self.assertEqual(
            (fast.backend, fast.safe_max_n, fast.max_objects, fast.supported, fast.reason),
            ("nauty", 8, 20_000, True, "fast-backend-within-budget"),
        )

    def test_requests_outside_budget_are_refused_not_clamped(self) -> None:
        pure = product.graph_search_plan(7, fast_backend_available=False)
        fast = product.graph_search_plan(9, fast_backend_available=True)
        low = product.graph_search_plan(1, fast_backend_available=False)
        self.assertEqual((pure.supported, pure.requested_max_n, pure.reason),
                         (False, 7, "fast-backend-required"))
        self.assertEqual((fast.supported, fast.requested_max_n, fast.reason),
                         (False, 9, "fast-order-limit-exceeded"))
        self.assertEqual((low.supported, low.reason), (False, "order-below-minimum"))

    def test_invalid_argument_types_fail_before_planning(self) -> None:
        for bad in (True, 6.0, "6", None):
            with self.subTest(max_n=bad), self.assertRaises(TypeError):
                product.graph_search_plan(bad, fast_backend_available=False)
        for bad in (1, None, "yes"):
            with self.subTest(fast=bad), self.assertRaises(TypeError):
                product.graph_search_plan(6, fast_backend_available=bad)

    def test_refusal_occurs_before_any_graph_is_generated(self) -> None:
        with mock.patch.object(nauty_scale, "geng_available", return_value=False), \
                mock.patch.object(product, "_iter_planned_graphs",
                                  side_effect=AssertionError("enumeration started")):
            result = product.check("sum_degrees == 2*num_edges", max_n=7)
        self.assertEqual((result.verdict, result.tier), ("unsupported", "none"))
        self.assertIn("reason=fast-backend-required", result.notes)
        self.assertIn("requested max_n=7", result.notes)
        self.assertIn("safe max_n=6", result.notes)
        self.assertIn("no graph was checked or silently clamped", result.notes)

    def test_counterexample_stops_the_incremental_scan_immediately(self) -> None:
        first = Graph.from_edges(2, [(0, 1)])

        def graphs(*_args, **_kwargs):
            yield first
            raise AssertionError("scan continued after first counterexample")

        with mock.patch.object(nauty_scale, "geng_available", return_value=False), \
                mock.patch.object(product, "_iter_planned_graphs", side_effect=graphs):
            result = product._graph_bound_verdict("num_vertices == num_edges", 6)
        self.assertEqual(result.verdict, "refuted")
        self.assertEqual(result.witness["n"], 2)

    def test_generated_object_budget_fails_closed(self) -> None:
        graph = Graph.from_edges(2, [])
        plan = product.GraphSearchPlan(2, "pure_python", 6, 1, True,
                                       "pure-backend-within-budget")
        with mock.patch.object(generate, "generate_graphs", return_value=[graph, graph]):
            with self.assertRaisesRegex(RuntimeError, "object-budget-exceeded"):
                list(product._iter_planned_graphs(plan, connected=False))

    def test_backend_failure_is_error_without_path_or_completion_claim(self) -> None:
        with mock.patch.object(nauty_scale, "geng_available", return_value=False), \
                mock.patch.object(generate, "generate_graphs",
                                  side_effect=OSError("/secret/checkout/geng")):
            result = product._graph_bound_verdict("sum_degrees == 2*num_edges", 6)
        self.assertEqual((result.verdict, result.tier), ("error", "none"))
        self.assertIn("reason=backend-unavailable", result.notes)
        self.assertNotIn("/secret", result.notes)
        self.assertNotIn("ALL ", result.checked_up_to)

    def test_default_core_graph_check_finishes_inside_test_budget(self) -> None:
        with mock.patch.object(nauty_scale, "geng_available", return_value=False):
            started = time.monotonic()
            result = product.check("sum_degrees == 2*num_edges")
            elapsed = time.monotonic() - started
        self.assertEqual(inspect.signature(product.check).parameters["max_n"].default, 6)
        self.assertEqual((result.verdict, result.tier),
                         ("open", "no_counterexample_within_bound"))
        self.assertIn("ALL 142 connected graphs with 2 <= n <= 6", result.checked_up_to)
        self.assertLess(elapsed, 30)

    def test_discovery_cli_passes_safe_default(self) -> None:
        result = product.CheckResult("x", "unknown", "unsupported", "none")
        with mock.patch.object(product, "check", return_value=result) as check_mock, \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            code = cli.main(["check", "x"])
        self.assertEqual(code, 3)
        check_mock.assert_called_once()
        self.assertEqual(check_mock.call_args.kwargs["max_n"], 6)

    def test_formalization_refuses_order_seven_without_fast_backend(self) -> None:
        candidate = formalize.candidate_formalizations(
            "sum_degrees == 2*num_edges", max_n=7, fixed_n=6
        )[1]
        with mock.patch.object(nauty_scale, "geng_available", return_value=False), \
                mock.patch.object(generate, "generate_graphs",
                                  side_effect=AssertionError("enumeration started")):
            result = formalize.evaluate_candidate(candidate)
        self.assertEqual(result.verdict, "unsupported")
        self.assertIn("reason=fast-backend-required", result.notes)


if __name__ == "__main__":
    unittest.main()
