"""
mathhead.guardrails — Çit (guardrails).

Kullanıcının çalışma prensiplerindeki "Mimari güvenlik önlemleri: çitin dışına
çıkmamalı" maddesinin kod karşılığı. Motor buradaki sınırların DIŞINA çıkamaz.

Üç tür çit:
    1) Girdi doğrulama  -> validate_input(): boyut/derinlik/karakter sınırları,
       bilinmeyen sembol reddi. (duvar #2: fazla varsayımı engelle.)
    2) Kaynak sınırı    -> solver_config(): zaman aşımı (timeout) ve bellek/
       rlimit. Çözücü sonsuza kadar çalışamaz (undecidability'e karşı).
    3) Determinizm      -> solver_config(): sabit tohum (seed) + tek iş parçacığı,
       böylece "aynı girdi -> aynı çıktı". (duvar #3: non-determinizmi bastır.)

İSKELET: imzalar nihai, gövdeler v1'de doldurulacak (Todo.md > T1).
"""
from __future__ import annotations

from typing import Any

MAX_STATEMENTS: int = 256        # tek istekte en fazla ifade sayısı
MAX_EXPRESSION_CHARS: int = 4_000  # tek ifade uzunluk sınırı
MAX_AST_DEPTH: int = 64          # iç içe geçme (nesting) sınırı


class GuardrailError(ValueError):
    """Bir çit ihlal edildi. İstek reddedilir; motor içeri girmez."""


def validate_input(statements: list[str]) -> None:
    """Girdiyi çitlere göre denetler; ihlalde `GuardrailError` fırlatır.

    Sessizce kırpmaz/düzeltmez — net reddeder (dürüstlük + öngörülebilirlik).
    """
    raise NotImplementedError("v1: Todo.md > T1")  # scaffold


def solver_config(timeout_ms: int, seed: int = 42) -> dict[str, Any]:
    """Deterministik + sınırlı bir Z3 yapılandırması (parametre sözlüğü) üretir.

    Döndürülen ayarlar Z3 çözücüsüne uygulanır: `timeout`, `random_seed`,
    tek-iş-parçacığı vb. Amaç: reproducibility ve worst-case sınırı.
    """
    raise NotImplementedError("v1: Todo.md > T1")  # scaffold
