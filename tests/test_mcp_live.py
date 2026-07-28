"""
LIVE MCP integration test — starts the server as a REAL subprocess over stdio,
handshakes with the MCP client, lists the tools and calls a few (Phase 11 [S]).

Now profile-aware (ROADMAP L3): it checks BOTH the `full` profile (every layer works
end to end) AND the curated default `core` profile (the verification surface is
exposed, the compute catalog is hidden, and the triage tools are always present so an
AI can discover and enable more).
"""
import asyncio
import json
import os
import sys

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


def _params(profile: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable, args=["-m", "mathhead.server.mcp_server"],
        env={**os.environ, "MATHHEAD_PROFILE": profile},
    )


# one representative tool from each layer (exercised under the `full` profile)
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
        return structured.get("result", structured) if "status" not in structured else structured
    return json.loads(call_result.content[0].text)


async def _run(profile: str, probes):
    async with stdio_client(_params(profile)) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        names = {t.name for t in (await session.list_tools()).tools}
        results = {t: _payload(await session.call_tool(t, a)) for t, a, _ in probes}
        return names, results


@pytest.mark.timeout(60)
def test_live_full_profile_exercises_every_layer():
    names, results = asyncio.run(_run("full", _PROBES))
    assert len(names) >= 160                                   # the full surface
    for tool, _, (key, expected) in _PROBES:
        assert results[tool].get(key) == expected, \
            f"{tool}: {key} expected {expected!r}, got {results[tool].get(key)!r}"


@pytest.mark.timeout(60)
def test_live_core_profile_is_curated_but_discoverable():
    probes = [
        ("entailment", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}, ("status", "valid")),
        ("list_capabilities", {}, ("status", "ok")),
    ]
    names, results = asyncio.run(_run("core", probes))
    assert 10 <= len(names) <= 45                              # curated default, not the full 171
    # the verification core + the always-on triage tools are exposed
    assert {"entailment", "verify_equality", "cross_check", "prove_unsat",
            "list_capabilities", "describe_tool", "recommend_tool"} <= names
    assert "simplify" not in names                            # the compute catalog is hidden by default
    assert results["entailment"]["status"] == "valid"
    assert results["list_capabilities"]["status"] == "ok"     # discovery still works
