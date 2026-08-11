"""Real nauty/geng evidence for the accepted graph-budget fast path."""

from itertools import islice

import pytest

from mathhead.discovery import nauty_scale, product


pytestmark = [
    pytest.mark.requires_solver,
    pytest.mark.skipif(not nauty_scale.geng_available(), reason="nauty/geng not installed"),
]


def test_fast_plan_uses_real_geng_within_accepted_budget():
    plan = product.graph_search_plan(8, fast_backend_available=True)
    assert (plan.backend, plan.safe_max_n, plan.max_objects, plan.supported) == (
        "nauty", 8, 20_000, True
    )
    graphs = list(islice(product._iter_planned_graphs(plan, connected=True), 3))
    assert graphs and all(graph.n >= 2 for graph in graphs)


def test_real_geng_connected_order_eight_stays_under_object_budget():
    assert nauty_scale.geng_count(8, connected=True, timeout_seconds=30) == 11_117


def test_real_geng_order_six_generation_is_complete_and_bounded():
    graphs = nauty_scale.geng_graphs(
        6, connected=True, hard_cap=20_000, timeout_seconds=30
    )
    assert len(graphs) == 112
