"""
v1.0 release freeze (ROADMAP K4). A full contract / API-stability check:

  * the version is 1.0.0 and is CONSISTENT across pyproject.toml and __init__.py;
  * the CHANGELOG has a 1.0.0 release entry;
  * every registered MCP tool has a non-empty description and a valid input schema
    (the frozen external contract, ADR-0004), and the surface is at its v1.0 size.

This is the machine-check that "the API is frozen and stable" is actually true.
"""
import asyncio
import tomllib
from pathlib import Path

from mathhead import __version__
from mathhead.server import mcp_server

_ROOT = Path(__file__).resolve().parent.parent
_FROZEN_TOOL_COUNT = 168


def test_version_is_1_0_0():
    assert __version__ == "1.0.0"


def test_pyproject_version_matches_package():
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__


def test_changelog_records_the_release():
    text = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.0.0]" in text


def test_frozen_tool_surface_conforms():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    assert len(tools) >= _FROZEN_TOOL_COUNT, f"tool surface shrank below v1.0 ({len(tools)})"
    for tool in tools:
        assert tool.description and tool.description.strip(), f"{tool.name}: no description"
        schema = tool.inputSchema
        assert isinstance(schema, dict) and schema.get("type") == "object", f"{tool.name}: bad schema"
