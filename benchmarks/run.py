#!/usr/bin/env python3
"""
MathHead — LLM-tuzak benchmark harness (ROADMAP Track C4).

`benchmarks/llm_traps.json` içindeki her tuzağı MathHead'in ilgili aracıyla
adjuke eder ve **yakalama oranını** (catch-rate) raporlar. Bir tuzak, MathHead
`expect`'teki düzeltici verdict'i döndürürse "YAKALANDI" sayılır.

DÜRÜST çerçeve: bu, MathHead'in bilinen LLM hata desenlerini doğru adjuke
ettiğinin **yeniden-üretilebilir gösterimidir** — canlı bir LLM ile A/B testi
DEĞİL (o, gerçek bir modelle kullanıcının koşacağı iş). Amaç: değer önerisini
("AI'ın işini denetler") ölçülebilir + regresyona karşı korunur kılmak.

Kullanım:
    python benchmarks/run.py           # rapor
    python benchmarks/run.py --json    # ham JSON
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
    """Her tuzağı çalıştırır; {id, category, caught, got} listesi döndürür."""
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
    ap = argparse.ArgumentParser(description="MathHead LLM-tuzak benchmark")
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
    print("  MathHead — LLM-tuzak benchmark (yeniden-üretilebilir gösterim)")
    print("=" * 72)
    for r in rows:
        mark = "✓ yakaladı" if r["caught"] else "✗ KAÇIRDI"
        print(f"  [{mark}] {r['id']:30} — {r['llm_error']}")
        if not r["caught"]:
            print(f"       beklenen {r['expect']}  ·  gelen {r['got']}")
    print("-" * 72)
    print("  Kategori bazında:")
    for cat, vals in sorted(by_cat.items()):
        print(f"    {cat:22} {sum(vals)}/{len(vals)}")
    print("-" * 72)
    print(f"  YAKALAMA ORANI: {caught}/{total} = %{round(100 * caught / total, 1)}")
    print("  (Not: MathHead'in bilinen hata desenlerini doğru adjuke etme oranı;")
    print("   canlı LLM A/B değil — o kullanıcının gerçek modelle koşacağı iş.)")
    print("=" * 72)


if __name__ == "__main__":
    main()
