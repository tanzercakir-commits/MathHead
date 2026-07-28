"""
mathhead.router — Yönlendirme katmanı.

Görev: gelen bir görevi DOĞRU ilkele yönlendirmek. Karar açık ve kurallı
(rule-based); "model sezgisiyle" değil. Bu, duvar #3'e (non-determinizm) karşı
mimari güvenliğin parçasıdır.

v1'de tek çözücü (Z3) var, o yüzden yönlendirme basittir. Katman yine de var ki
v2'de compute/ (SymPy) eklendiğinde dış sözleşme değişmesin (ADR-0004).
"""
from __future__ import annotations

from typing import Any

from mathhead.core.logic import (
    ReasoningResult,
    check_consistency,
    check_entailment,
    find_model,
)

__all__ = ["route"]


def _opts(payload: dict[str, Any]) -> dict[str, Any]:
    opts: dict[str, Any] = {}
    for key in ("timeout_ms", "seed"):
        if key in payload and payload[key] is not None:
            opts[key] = payload[key]
    return opts


def route(task: str, payload: dict[str, Any]) -> ReasoningResult:
    """Bir görevi uygun ilkele yönlendirir.

    Args:
        task: "entailment" | "consistency" | "find_model" (v1).
        payload: göreve özgü argümanlar (premises, conclusion, statements,
            opsiyonel timeout_ms/seed).
    """
    if task == "entailment":
        return check_entailment(payload["premises"], payload["conclusion"], **_opts(payload))
    if task == "consistency":
        return check_consistency(payload["statements"], **_opts(payload))
    if task == "find_model":
        return find_model(payload["statements"], **_opts(payload))
    raise ValueError(f"bilinmeyen görev: {task!r}")
