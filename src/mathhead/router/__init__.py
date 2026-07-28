"""
mathhead.router — Yönlendirme katmanı.

Görev: MCP'den gelen bir problemi, DOĞRU çözücüye (core/Z3 mi, compute/SymPy mi)
ve doğru ilkele (entailment / consistency / find_model) yönlendirmek.

Neden ayrı katman? Determinizm ve izlenebilirlik. Yönlendirme kararı açık,
kurallı (rule-based) ve loglanabilir olmalı; "model sezgisiyle" değil. Bu,
duvar #3'e (non-determinizm) karşı mimari güvenliğin parçasıdır.

v1'de yönlendirme basittir (tek çözücü: Z3). Katman yine de var ki v2'de
compute/ eklendiğinde sözleşme değişmesin (API'yi erken dondur prensibi).

İSKELET: gövde v1'de doldurulacak (Todo.md > T6).
"""
from __future__ import annotations

from mathhead.core.logic import ReasoningResult


def route(task: str, payload: dict) -> ReasoningResult:
    """Bir görevi uygun ilkele yönlendirir.

    Args:
        task: "entailment" | "consistency" | "find_model" (v1). v2: "solve",
            "simplify", "derivative"...
        payload: göreve özgü argümanlar (premises, conclusion, statements...).
    """
    raise NotImplementedError("v1: Todo.md > T6")  # scaffold
