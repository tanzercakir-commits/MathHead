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


@mcp.tool()
def prove(premises: list[str], conclusion: str) -> dict[str, Any]:
    """Öncüller sonucu gerektiriyorsa NEDEN gösterir — minimal çekirdek + adım adım türetim.

    valid: `used_premises` (gerekli öncüller) + `proof_steps` (önerme/yüklem/evrensel
    parçası için kurulur; kurulamazsa Z3 kararı korunur). invalid: `witness` karşıörnek.
    """
    return asdict(route("prove", {"premises": premises, "conclusion": conclusion}))


@mcp.tool()
def enumerate_models(statements: list[str], limit: int = 10) -> dict[str, Any]:
    """İfadeleri sağlayan FARKLI modelleri (en fazla `limit`) numaralandırır.

    Dönüş: `models` (liste), `count`, `exhaustive` (True = tüm modeller bulundu;
    False = sınıra ulaşıldı, sonsuz alanda daha fazlası olabilir).
    """
    return asdict(route("enumerate", {"statements": statements, "limit": limit}))


@mcp.tool()
def optimize(constraints: list[str], objective: str, sense: str = "max") -> dict[str, Any]:
    """Kısıtları sağlayıp sayısal `objective`'i en büyük/küçük (`sense`) yapan çözümü bul.

    Dönüş: status ∈ {optimal, unbounded, unsat, unknown, error}; optimal ise
    `objective_value` + `witness` (optimumu sağlayan atama). (Z3 Optimize çekirdeği.)
    """
    return asdict(route("optimize", {"constraints": constraints, "objective": objective, "sense": sense}))


# --------------------------- Hesap (SymPy) -------------------------------- #
@mcp.tool()
def simplify(expression: str) -> dict[str, Any]:
    """Bir cebirsel ifadeyi sadeleştirir (ör. 'sin(x)**2 + cos(x)**2' -> '1')."""
    return asdict(route("simplify", {"expression": expression}))


@mcp.tool()
def solve(equation: str, symbol: str) -> dict[str, Any]:
    """Bir denklemi bir değişken için çözer (ör. 'x**2 == 4', symbol='x')."""
    return asdict(route("solve", {"equation": equation, "symbol": symbol}))


@mcp.tool()
def differentiate(expression: str, symbol: str, order: int = 1) -> dict[str, Any]:
    """İfadenin `symbol`'e göre `order`. mertebeden türevini alır."""
    return asdict(route("differentiate", {"expression": expression, "symbol": symbol, "order": order}))


@mcp.tool()
def integrate(expression: str, symbol: str) -> dict[str, Any]:
    """İfadenin `symbol`'e göre belirsiz integralini alır (+C)."""
    return asdict(route("integrate", {"expression": expression, "symbol": symbol}))


# ------------------- Frontier / Track B (SAT indirgeme) ------------------- #
@mcp.tool()
def pythagorean_coloring(n: int) -> dict[str, Any]:
    """{1..n}'i 2 renge, tek renkli Pythagoras üçlüsü olmadan boyamayı dener.

    Track B gösterimi: sat -> boyama bulundu; unsat -> imkânsızlık ispatı.
    (2016'da n=7825'i çözen ~200 TB'lık ispatın aynı kodlaması; küçük ölçek.)
    """
    return asdict(route("pythagorean_coloring", {"n": n}))


@mcp.tool()
def pigeonhole(n: int) -> dict[str, Any]:
    """`n+1` güvercinin `n` kutuya sığamayacağını ispatlar (güvercin yuvası ilkesi)."""
    return asdict(route("pigeonhole", {"n": n}))


@mcp.tool()
def van_der_waerden(n: int, k: int, colors: int = 2) -> dict[str, Any]:
    """{1..n}'i `colors` renge, tek renkli k-terimli aritmetik dizi olmadan boyamayı dener.

    van der Waerden sayısı W(colors,k) hesabının çekirdeği: `unsat` -> n ≥ W (ispat).
    Bilinen W değerleri bu yöntemle hesaplandı; büyük/açık değerler `unknown` döner.
    """
    return asdict(route("van_der_waerden", {"n": n, "k": k, "colors": colors}))


@mcp.tool()
def schur_number(n: int, colors: int) -> dict[str, Any]:
    """{1..n}'i `colors` sum-free renge bölmeyi dener (Schur sayısı S(colors) çekirdeği).

    `unsat` -> n > S(colors) (ispat). Bilinen: S(2)=4, S(3)=13, S(4)=44, S(5)=160;
    S(6) açık.
    """
    return asdict(route("schur_number", {"n": n, "colors": colors}))


def main() -> None:
    """Sunucuyu stdio üzerinden başlatır (yerel MCP istemcileri için)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
