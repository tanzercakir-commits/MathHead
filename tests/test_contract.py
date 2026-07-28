"""
Contract check (ROADMAP Phase 11 [S]) — verifies that EVERY tool conforms to the
common output contract: `status` + `reason_code` + `explanation` + `meta` (with
elapsed_ms). This is the machine-check of the "clean protocol & API" principle;
if a tool breaks the contract (e.g. returns without meta), the test fails.

The covered tool set comes from `test_mcp_layer.ARGS` (single source) — so when a
new tool is added, both callability and contract are enforced together.
"""
from dataclasses import asdict

import pytest

from mathhead.router import route
from tests.test_mcp_layer import ARGS

# route() task names diverge from MCP tool names in a few places (enumerate_models
# -> enumerate, model -> find_model, etc.). MCP name -> router task mapping:
_TASK = {
    "model": "find_model",
    "enumerate_models": "enumerate",
    "max_satisfy": "maxsat",
    "van_der_waerden": "van_der_waerden",
}


@pytest.mark.parametrize("tool", sorted(ARGS), ids=sorted(ARGS))
def test_tool_output_contract(tool):
    task = _TASK.get(tool, tool)
    result = asdict(route(task, ARGS[tool]))
    # Universal contract: four fields always present
    for key in ("status", "reason_code", "explanation", "meta"):
        assert key in result, f"{tool}: contract violation — '{key}' missing"
    assert isinstance(result["status"], str) and result["status"]
    assert isinstance(result["explanation"], str)
    assert isinstance(result["meta"], dict)
    # meta must carry a measurement (every layer)
    assert "elapsed_ms" in result["meta"], f"{tool}: meta.elapsed_ms missing"
    assert isinstance(result["meta"]["elapsed_ms"], (int, float))
