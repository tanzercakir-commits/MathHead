"""
mathhead.guardrails — Çit (guardrails).

Kullanıcının çalışma prensiplerindeki "Mimari güvenlik önlemleri: çitin dışına
çıkmamalı" maddesinin kod karşılığı. Motor buradaki sınırların DIŞINA çıkamaz.

Üç tür çit:
    1) Girdi doğrulama  -> validate_input(): sayı/uzunluk/derinlik sınırları,
       sözdizimi kontrolü. (duvar #2: fazla varsayımı engelle, belirsizi reddet.)
    2) Kaynak sınırı    -> solver_config(): zaman aşımı (timeout). Çözücü
       sonsuza kadar çalışamaz (undecidability'e karşı).
    3) Determinizm      -> solver_config(): sabit tohum (seed), böylece
       "aynı girdi -> aynı çıktı". (duvar #3: non-determinizmi bastır.)
"""
from __future__ import annotations

import ast

MAX_STATEMENTS: int = 256          # tek istekte en fazla ifade sayısı
MAX_EXPRESSION_CHARS: int = 4_000  # tek ifade uzunluk sınırı
MAX_AST_DEPTH: int = 64            # iç içe geçme (nesting) sınırı


class GuardrailError(ValueError):
    """Bir çit ihlal edildi. İstek reddedilir; motor içeri girmez."""


def _depth(node: ast.AST, level: int = 0) -> int:
    children = list(ast.iter_child_nodes(node))
    if not children:
        return level
    return max(_depth(c, level + 1) for c in children)


def validate_input(statements: list[str]) -> None:
    """Girdiyi çitlere göre denetler; ihlalde `GuardrailError` fırlatır.

    Sessizce kırpmaz/düzeltmez — net reddeder (dürüstlük + öngörülebilirlik).
    """
    if not isinstance(statements, list):
        raise GuardrailError("ifadeler bir liste olmalı")
    if len(statements) == 0:
        raise GuardrailError("en az bir ifade gerekli")
    if len(statements) > MAX_STATEMENTS:
        raise GuardrailError(
            f"en fazla {MAX_STATEMENTS} ifade işlenir (gelen: {len(statements)})"
        )
    for i, s in enumerate(statements):
        if not isinstance(s, str) or not s.strip():
            raise GuardrailError(f"[{i}] boş veya geçersiz ifade")
        if len(s) > MAX_EXPRESSION_CHARS:
            raise GuardrailError(
                f"[{i}] ifade çok uzun (>{MAX_EXPRESSION_CHARS} karakter)"
            )
        try:
            tree = ast.parse(s, mode="eval")
        except SyntaxError as exc:
            raise GuardrailError(f"[{i}] sözdizimi hatası: {exc.msg}") from exc
        if _depth(tree) > MAX_AST_DEPTH:
            raise GuardrailError(f"[{i}] ifade çok derin (>{MAX_AST_DEPTH} seviye)")


def solver_config(timeout_ms: int, seed: int = 42):
    """Deterministik + zaman-sınırlı bir `z3.Solver` üretir.

    Sabit tohum -> reproducibility; timeout -> worst-case sınırı. Böylece aynı
    girdi her seferinde aynı sonucu verir ve motor asla asılı kalmaz.
    """
    import z3

    # Global tohumlar (sürümler arası anahtar adları değişebilir -> güvenli dene).
    for key in ("smt.random_seed", "sat.random_seed"):
        try:
            z3.set_param(key, seed)
        except Exception:  # noqa: BLE001 - determinizm ayarı best-effort
            pass

    solver = z3.Solver()
    solver.set("timeout", int(timeout_ms))
    try:
        solver.set("random_seed", seed)
    except Exception:  # noqa: BLE001
        pass
    return solver
