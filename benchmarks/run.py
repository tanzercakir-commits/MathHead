#!/usr/bin/env python3
"""
MathHead — LLM-trap benchmark harness (ROADMAP Track C4).

Adjudicates every trap in `benchmarks/llm_traps.json` with MathHead's relevant
tool and reports the **catch-rate**. A trap counts as "CAUGHT" if MathHead
returns the corrective verdict in `expect`.

HONEST framing: this is a **reproducible demonstration** that MathHead correctly
adjudicates known LLM error patterns — NOT an A/B test against a live LLM
(that's the work the user runs with a real model). Goal: make the value proposition
("audits the AI's work") measurable + protected against regression.

Usage:
    python benchmarks/run.py           # report
    python benchmarks/run.py --json    # raw JSON
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

from mathhead.router import route

_TRAPS = Path(__file__).parent / "llm_traps.json"


def run() -> list[dict]:
    """Runs each trap; returns a list of {id, category, caught, got}."""
    traps = json.loads(_TRAPS.read_text(encoding="utf-8"))["traps"]
    out = []
    for t in traps:
        result = asdict(route(t["task"], t["payload"]))
        caught = all(result.get(k) == v for k, v in t["expect"].items())
        out.append({
            "id": t["id"], "category": t["category"], "caught": caught,
            "llm_error": t["llm_error"],
            "got": {k: result.get(k) for k in t["expect"]},
            "expect": t["expect"],
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="MathHead LLM-trap benchmark")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = run()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    caught = sum(r["caught"] for r in rows)
    total = len(rows)
    by_cat: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r["caught"])

    print("=" * 72)
    print("  MathHead — LLM-trap benchmark (reproducible demonstration)")
    print("=" * 72)
    for r in rows:
        mark = "✓ caught" if r["caught"] else "✗ MISSED"
        print(f"  [{mark}] {r['id']:30} — {r['llm_error']}")
        if not r["caught"]:
            print(f"       expected {r['expect']}  ·  got {r['got']}")
    print("-" * 72)
    print("  By category:")
    for cat, vals in sorted(by_cat.items()):
        print(f"    {cat:22} {sum(vals)}/{len(vals)}")
    print("-" * 72)
    print(f"  CATCH RATE: {caught}/{total} = %{round(100 * caught / total, 1)}")
    print("  (Note: the rate at which MathHead correctly adjudicates known error patterns;")
    print("   not a live LLM A/B — that's the work the user runs with a real model.)")
    print("=" * 72)


if __name__ == "__main__":
    main()
