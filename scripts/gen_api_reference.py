#!/usr/bin/env python3
"""
MathHead — API referansı üreteci (ROADMAP Aşama 8 [S]).

Tek doğruluk kaynağı: MCP sunucusuna KAYITLI araçlar. Bu betik onların adını,
imzasını (parametreler + varsayılanlar) ve açıklamasını okuyup
`docs/api-reference.md`'yi üretir. `tests/test_api_reference.py` üretilenin
işlenmiş dosyayla aynı olmasını zorlar (çürümez).

Kullanım:
    python scripts/gen_api_reference.py            # dosyayı yaz
    python scripts/gen_api_reference.py --check     # güncel mi (0/1)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from mathhead.server.mcp_server import mcp

_OUT = Path(__file__).parent.parent / "docs" / "api-reference.md"


def _signature(name: str, schema: dict) -> str:
    props = (schema or {}).get("properties", {}) or {}
    required = set((schema or {}).get("required", []) or [])
    parts = []
    for pname, spec in props.items():
        if pname in required:
            parts.append(pname)
        else:
            default = spec.get("default", None)
            parts.append(f"{pname}={default!r}" if default is not None else f"{pname}=None")
    return f"{name}({', '.join(parts)})"


def generate() -> str:
    tools = asyncio.run(mcp.list_tools())
    lines = [
        "# MathHead — API Referansı (otomatik üretilmiş)",
        "",
        "> **UYARI:** Bu dosya `scripts/gen_api_reference.py` tarafından, MCP'ye",
        "> kayıtlı araçlardan üretilir. ELLE DÜZENLEME. Güncellemek için:",
        "> `python scripts/gen_api_reference.py`. Sözleşme ayrıntısı: `docs/mcp-api.md`.",
        "",
        f"Toplam **{len(tools)} araç**.",
        "",
    ]
    for t in tools:
        desc = (t.description or "").strip().splitlines()
        first = desc[0].strip() if desc else ""
        lines.append(f"### `{_signature(t.name, t.inputSchema)}`")
        lines.append("")
        lines.append(first)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="MathHead API referansı üreteci")
    ap.add_argument("--check", action="store_true", help="yalnızca güncel mi denetle")
    args = ap.parse_args()
    content = generate()
    if args.check:
        current = _OUT.read_text(encoding="utf-8") if _OUT.exists() else ""
        if current != content:
            print("api-reference.md GÜNCEL DEĞİL — `python scripts/gen_api_reference.py` çalıştır")
            return 1
        print("api-reference.md güncel.")
        return 0
    _OUT.write_text(content, encoding="utf-8")
    print(f"yazıldı: {_OUT}  ({content.count('### ')} araç)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
