"""Deterministic pytest ownership markers for MH-C-ENV-002 profiles."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Assign path-owned surfaces; slow ownership is always explicit in test source."""
    for item in items:
        path = Path(str(item.path))
        name = path.name
        parts = path.parts
        if name.startswith("test_discovery_") or "graph_budget" in parts:
            item.add_marker(pytest.mark.discovery)
        if name in {"test_api_reference.py", "test_docs_examples.py"} or \
                "project_metadata" in parts:
            item.add_marker(pytest.mark.docs)
        if name == "test_mcp_live.py" or "live_mcp" in parts:
            item.add_marker(pytest.mark.live_mcp)
        surface_markers = {
            marker
            for marker in ("discovery", "docs", "live_mcp")
            if item.get_closest_marker(marker) is not None
        }
        if len(surface_markers) > 1:
            joined = ",".join(sorted(surface_markers))
            raise pytest.UsageError(f"profile-surface-overlap:{item.nodeid}:{joined}")
