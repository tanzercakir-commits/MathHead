"""
mathhead.server.mcp_server
==========================

MathHead'in MCP (Model Context Protocol) arayüzü. AI istemcisi (ör. Claude)
motorun yeteneklerine SADECE buradaki araçlar (tools) üzerinden erişir. Bu
katman "net protokol & API tanımı" prensibinin uygulama noktasıdır.

SDK: `mcp` (FastMCP), Python 3.10+. Kurulum: `pip install "mcp[cli]"`.
Çalıştırma (yerel): `mathhead-server`  ya da  `python -m mathhead.server.mcp_server`

Akış: server -> router -> (guardrails + core/Z3). Araç imzaları ve dönüş şekli
docs/mcp-api.md ile birebir aynıdır (ADR-0004: erken donduruldu).
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # guardrail: bağımlılık yoksa net mesaj
    raise SystemExit(
        "MCP SDK bulunamadı. Kurulum: pip install 'mcp[cli]'  (bkz. pyproject.toml)"
    ) from exc

from mathhead.router import route

mcp = FastMCP("MathHead")


@mcp.tool()
def entailment(premises: list[str], conclusion: str) -> dict[str, Any]:
    """Öncüller sonucu MANTIKSAL OLARAK gerektirir mi? (premises ⊨ conclusion)

    Dönüş: ReasoningResult sözlüğü. status ∈ {valid, invalid, unknown, error}.
    invalid ise `witness` bir karşıörnek (counterexample) içerir.
    İfade grameri için: docs/mcp-api.md.
    """
    return asdict(route("entailment", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def consistency(statements: list[str]) -> dict[str, Any]:
    """Bu ifadeler AYNI ANDA doğru olabilir mi? (tutarlılık / satisfiability)

    Dönüş: status ∈ {sat, unsat, unknown, error}. sat ise `witness` örnek bir
    atama (model); unsat ise çelişen alt küme (unsat core) döner.
    """
    return asdict(route("consistency", {"statements": statements}))


@mcp.tool()
def model(statements: list[str]) -> dict[str, Any]:
    """İfadeleri sağlayan SOMUT bir örnek (değişken ataması) döndürür.

    Dönüş: status ∈ {sat, unsat, unknown, error}. sat ise `witness` = model.
    """
    return asdict(route("find_model", {"statements": statements}))


def main() -> None:
    """Sunucuyu stdio üzerinden başlatır (yerel MCP istemcileri için)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
