"""
LIVE MCP integration test (ROADMAP Phase 11 [S]) — starts the server as a REAL
subprocess over stdio, handshakes with the MCP client, lists the tools and
calls a few, verifying the JSON response.

Phase 8's `test_mcp_layer` is in-process (calls the function directly); this one
exercises the full stack (subprocess + JSON-RPC + FastMCP + router + Z3/SymPy)
end-to-end — proving the "live `stdio` connection" contract actually works.
"""
import asyncio
import json
import sys

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

_PARAMS = StdioServerParameters(
    command=sys.executable, args=["-m", "mathhead.server.mcp_server"],
)

# (tool, arguments, (key, expected) to verify) — one representative from each layer
_PROBES = [
    ("entailment", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}, ("status", "valid")),
    ("simplify", {"expression": "sin(x)**2 + cos(x)**2"}, ("result", "1")),
    ("factorize", {"n": "360"}, ("status", "ok")),
    ("prove_inequality", {"goal": "x**2 + y**2 >= 2*x*y"}, ("status", "valid")),
    ("subset_sum", {"numbers": [3, 4, 2], "target": 9}, ("status", "sat")),
]


def _payload(call_result) -> dict:
    """CallToolResult -> tool return dict (structuredContent or text JSON)."""
    structured = getattr(call_result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP sometimes wraps the dict return in {"result": {...}}
        return structured.get("result", structured) if "status" not in structured else structured
    text = call_result.content[0].text
    return json.loads(text)


async def _run():
    async with stdio_client(_PARAMS) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = await session.list_tools()
        names = {t.name for t in listed.tools}
        results = {}
        for tool, args, _ in _PROBES:
            res = await session.call_tool(tool, args)
            results[tool] = _payload(res)
        return names, results


@pytest.mark.timeout(60)
def test_live_mcp_stdio_roundtrip():
    names, results = asyncio.run(_run())
    # Server publishes all tools live
    assert len(names) >= 59
    for tool, _, (key, expected) in _PROBES:
        assert results[tool].get(key) == expected, \
            f"{tool}: {key} beklenen {expected!r}, gelen {results[tool].get(key)!r}"
