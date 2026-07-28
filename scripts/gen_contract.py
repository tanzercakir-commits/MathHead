#!/usr/bin/env python3
"""
MathHead — machine-readable MCP contract generator (ROADMAP L2).

Emits `docs/mcp-contract.json`: for every registered MCP tool, its description, input
schema, and **stability tier**; plus the shared output envelope, the `certainty`
(epistemic-strength) vocabulary, and the stability tiers. This is the single
machine-readable artifact an external client can consume (the external review's #6).
`tests/test_contract_artifact.py` enforces that the committed file matches (code = docs).

Usage:
    python scripts/gen_contract.py            # write the file
    python scripts/gen_contract.py --check    # is it up to date (0/1)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mathhead.certainty import stability_of
from mathhead.server.mcp_server import mcp

_OUT = Path(__file__).parent.parent / "docs" / "mcp-contract.json"
# MCP tool name -> router task name (they differ for a few tools).
_TASK = {"model": "find_model", "enumerate_models": "enumerate", "max_satisfy": "maxsat"}

_CERTAINTY_LEVELS = [
    "formal_proof", "independent_certificate", "solver_verified", "bounded_check",
    "symbolic_result", "numerical_check", "unknown", "error", "not_applicable",
]
_STABILITY_TIERS = ["stable", "provisional", "experimental", "internal"]


def generate() -> str:
    tools = asyncio.run(mcp.list_tools())
    tool_map = {}
    for t in sorted(tools, key=lambda x: x.name):
        desc = (t.description or "").strip().splitlines()
        tool_map[t.name] = {
            "description": desc[0].strip() if desc else "",
            "stability": stability_of(_TASK.get(t.name, t.name)),
            "input_schema": t.inputSchema,
        }
    contract = {
        "contract_version": 1,
        "grammar_version": "1.2",
        "tool_count": len(tools),
        "output_envelope": {
            "description": "Every tool returns an object with at least these keys.",
            "required": ["status", "reason_code", "explanation", "meta"],
            "meta_keys": ["elapsed_ms", "certainty", "stability"],
        },
        "certainty_levels": _CERTAINTY_LEVELS,
        "stability_tiers": _STABILITY_TIERS,
        "tools": tool_map,
    }
    return json.dumps(contract, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="MathHead MCP contract generator")
    ap.add_argument("--check", action="store_true", help="only check if up to date")
    args = ap.parse_args()
    content = generate()
    if args.check:
        current = _OUT.read_text(encoding="utf-8") if _OUT.exists() else ""
        if current != content:
            print("mcp-contract.json OUT OF DATE — run `python scripts/gen_contract.py`")
            return 1
        print("mcp-contract.json up to date.")
        return 0
    _OUT.write_text(content, encoding="utf-8")
    print(f"written: {_OUT}  ({len(json.loads(content)['tools'])} tools)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
