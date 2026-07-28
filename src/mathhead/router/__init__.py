"""
mathhead.router — Yönlendirme katmanı.

Görev: gelen bir görevi DOĞRU çözücü + ilkele yönlendirmek. Karar açık ve kurallı
(rule-based); "model sezgisiyle" değil. Bu, duvar #3'e (non-determinizm) karşı
mimari güvenliğin parçasıdır.

v1: mantık (Z3) — entailment / consistency / find_model.
v2: hesap (SymPy) — simplify / solve / differentiate / integrate.
Dış sözleşme (ADR-0004) sabit; yeni yetenekler yalnızca yeni görev adları ekler.
"""
from __future__ import annotations

from typing import Any

from mathhead import compute, frontier
from mathhead.compute import ComputeResult
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


def route(task: str, payload: dict[str, Any]) -> ReasoningResult | ComputeResult:
    """Bir görevi uygun çözücü + ilkele yönlendirir.

    Mantık görevleri (Z3): entailment, consistency, find_model.
    Hesap görevleri (SymPy): simplify, solve, differentiate, integrate.
    """
    # --- Mantık çekirdeği (Z3) ---
    if task == "entailment":
        return check_entailment(payload["premises"], payload["conclusion"], **_opts(payload))
    if task == "consistency":
        return check_consistency(payload["statements"], **_opts(payload))
    if task == "find_model":
        return find_model(payload["statements"], **_opts(payload))

    # --- Hesap katmanı (SymPy) ---
    if task == "simplify":
        return compute.simplify(payload["expression"])
    if task == "solve":
        return compute.solve(payload["equation"], payload["symbol"])
    if task == "differentiate":
        return compute.differentiate(payload["expression"], payload["symbol"], payload.get("order", 1))
    if task == "integrate":
        return compute.integrate(payload["expression"], payload["symbol"])

    # --- Frontier / Track B (programatik indirgeme -> Z3) ---
    if task == "pythagorean_coloring":
        return frontier.boolean_pythagorean_coloring(payload["n"], **_opts(payload))
    if task == "pigeonhole":
        return frontier.pigeonhole(payload["n"], **_opts(payload))

    raise ValueError(f"bilinmeyen görev: {task!r}")
