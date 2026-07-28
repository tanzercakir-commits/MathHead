"""
CANLI MCP entegrasyon testi (ROADMAP Aşama 11 [S]) — sunucuyu GERÇEK bir alt
süreç olarak stdio üzerinden başlatır, MCP istemcisiyle el sıkışır, araçları
listeler ve birkaçını çağırıp JSON yanıtını doğrular.

Aşama 8'deki `test_mcp_layer` in-process (fonksiyonu doğrudan çağırır); bu ise
tam yığını (subprocess + JSON-RPC + FastMCP + router + Z3/SymPy) uçtan uca
sınar — "canlı `stdio` bağlantısı" sözleşmesinin fiilen çalıştığını kanıtlar.
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

# (araç, argümanlar, doğrulanacak (anahtar, beklenen)) — her katmandan birer temsil
_PROBES = [
    ("entailment", {"premises": ["p", "implies(p,q)"], "conclusion": "q"}, ("status", "valid")),
    ("simplify", {"expression": "sin(x)**2 + cos(x)**2"}, ("result", "1")),
    ("factorize", {"n": "360"}, ("status", "ok")),
    ("prove_inequality", {"goal": "x**2 + y**2 >= 2*x*y"}, ("status", "valid")),
    ("subset_sum", {"numbers": [3, 4, 2], "target": 9}, ("status", "sat")),
]


def _payload(call_result) -> dict:
    """CallToolResult -> araç dönüş sözlüğü (structuredContent ya da metin JSON)."""
    structured = getattr(call_result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP dict dönüşünü bazen {"result": {...}} sarar
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
    # Sunucu tüm araçları canlı yayımlıyor
    assert len(names) >= 59
    for tool, _, (key, expected) in _PROBES:
        assert results[tool].get(key) == expected, \
            f"{tool}: {key} beklenen {expected!r}, gelen {results[tool].get(key)!r}"
