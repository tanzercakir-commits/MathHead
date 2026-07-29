#!/usr/bin/env python3
"""
MathHead — tool-selection accuracy harness (ROADMAP L5).

Validates the L3 triage: given a natural-language task, does `recommend_tool`
surface a correct tool in its top-1 / top-3? Reports the accuracy over
`benchmarks/tool_selection.json`.

HONEST framing: `recommend_tool` is a **keyword-overlap heuristic** (see
`mathhead/profiles.py`), not a model. This harness measures how well that
heuristic maps intent→tool. The case set intentionally keeps realistic queries
that MISS, so the reported number reflects reality — when the heuristic misses,
`describe_tool` / `list_capabilities` are the fallbacks an AI uses to navigate.

Usage:
    python benchmarks/run_tool_selection.py           # report
    python benchmarks/run_tool_selection.py --json     # raw JSON
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mathhead.router import route

_CASES = Path(__file__).parent / "tool_selection.json"


def run(k: int = 3) -> list[dict]:
    """Score each case; returns {query, expect, got, hit1, hit3}."""
    cases = json.loads(_CASES.read_text(encoding="utf-8"))["cases"]
    out = []
    for c in cases:
        expect = set(c["expect"])
        r = route("recommend_tool", {"query": c["query"], "limit": k})
        got = [rec["tool"] for rec in getattr(r, "recommendations", [])]
        out.append({
            "query": c["query"],
            "expect": sorted(expect),
            "got": got,
            "hit1": bool(got) and got[0] in expect,
            "hit3": any(g in expect for g in got),
        })
    return out


def summarize(rows: list[dict]) -> dict:
    n = len(rows) or 1
    return {
        "cases": len(rows),
        "top1": sum(r["hit1"] for r in rows),
        "top3": sum(r["hit3"] for r in rows),
        "top1_rate": round(sum(r["hit1"] for r in rows) / n, 3),
        "top3_rate": round(sum(r["hit3"] for r in rows) / n, 3),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="MathHead tool-selection accuracy")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = run()
    s = summarize(rows)
    if args.json:
        print(json.dumps({"summary": s, "rows": rows}, ensure_ascii=False, indent=2))
        return

    print("=" * 72)
    print("  MathHead — tool-selection accuracy (recommend_tool, keyword heuristic)")
    print("=" * 72)
    for r in rows:
        mark = "✓1" if r["hit1"] else ("·3" if r["hit3"] else "✗ MISS")
        print(f"  [{mark:6}] {r['query'][:48]:48} → {r['got']}")
    print("-" * 72)
    print(f"  TOP-1: {s['top1']}/{s['cases']} = %{round(100 * s['top1_rate'], 1)}"
          f"    TOP-3: {s['top3']}/{s['cases']} = %{round(100 * s['top3_rate'], 1)}")
    print("  (recommend_tool is a keyword heuristic; misses fall back to describe_tool /")
    print("   list_capabilities. Not a learned ranker — see profiles.py.)")
    print("=" * 72)


if __name__ == "__main__":
    main()
