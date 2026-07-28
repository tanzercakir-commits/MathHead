"""
mathhead.core.translate
========================

Girdi ifadesi -> Z3 nesnesi çevirimi (parsing + translation).

Sınır (guardrail): dış dünyadan gelen metin DOĞRUDAN çözücüye verilmez. Önce
kısıtlı, açıkça tanımlı bir gramere (bkz. docs/mcp-api.md) göre ayrıştırılır.
Bu, "gereğinden fazla varsayım" (duvar #2) ve enjeksiyon riskine karşı çittir:
motor yalnızca gramerin izin verdiği ifadeleri kabul eder, gerisini reddeder.

v1 desteklenen parça (fragment):
    * Önermeler mantığı: and, or, not, implies, iff  (Boolean değişkenler)
    * Doğrusal aritmetik: +, -, *, <, <=, =, >=, >   (Int / Real değişkenler)
    * Nicelik belirteçleri (forall/exists): v1.1 hedefi (bkz. Plan.md yol haritası)

İSKELET: imza nihai, gövde v1'de doldurulacak (Todo.md > T2).
"""
from __future__ import annotations

from typing import Any


class ParseError(ValueError):
    """Girdi grameri ihlal edildi. Guardrail: net hata, sessiz varsayım YOK."""


def parse(expression: str) -> Any:
    """Tek bir ifadeyi ayrıştırıp soyut sözdizim ağacı (AST) döndürür.

    Hata durumunda `ParseError` fırlatır (asla 'tahmin edip düzeltmez').
    """
    raise NotImplementedError("v1: Todo.md > T2")  # scaffold


def to_z3(expression: str, symbols: dict[str, Any] | None = None) -> Any:
    """Bir ifadeyi Z3 mantık nesnesine çevirir.

    Args:
        expression: gramere uygun mantık ifadesi.
        symbols: paylaşılan sembol tablosu (aynı isim -> aynı Z3 sabiti);
            birden çok ifade arasında tutarlılık için router tarafından beslenir.
    """
    raise NotImplementedError("v1: Todo.md > T2")  # scaffold
