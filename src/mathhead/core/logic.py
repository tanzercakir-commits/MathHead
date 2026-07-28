"""
mathhead.core.logic
====================

Motorun KALBİ: bir SMT çözücü (Z3) üzerine kurulu, deterministik akıl yürütme
ilkelleri (reasoning primitives).

Neden Z3? -> DECISIONS.md ADR-0002. Kısaca: FOL + hazır teoriler (doğrusal
aritmetik, eşitsizlik, eşitlik...) için dünya standardı; deterministik ve
kanıtlanmış. Sıfırdan resolution/unification yazmak yerine bunu kullanıyoruz.

Not: Bu dosya ŞU AN İSKELET (scaffold). Fonksiyon imzaları ve `ReasoningResult`
dönüş sözleşmesi (contract) NİHAİDİR ve değişmemesi hedeflenir; gövdeler v1'de
doldurulacak (bkz. Todo.md > T3-T5). Sözleşmeyi kilitleyip gövdeyi sonra
doldurmak, proje prensibi "API'yi erken dondur"un (guardrail) gereğidir.

Dönüş Sözleşmesi:
    valid / invalid  -> entailment (mantıksal gerektirme) sorusu
    sat   / unsat    -> consistency (tutarlılık) sorusu
    unknown          -> çözücü karar veremedi (undecidability'e DÜRÜST yanıt)
    error            -> girdi/guardrail hatası
    "unknown" ve "error" birinci sınıf çıktılardır; ASLA gizlenmez.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Determinizm/guardrail varsayılanları (bkz. guardrails.solver_config).
DEFAULT_TIMEOUT_MS: int = 5_000   # worst-case: çözücü bu sürede durdurulur
DEFAULT_SEED: int = 42            # aynı girdi -> aynı çıktı (reproducibility)


@dataclass
class ReasoningResult:
    """Tüm akıl yürütme ilkellerinin ortak, makine + insan okunur çıktısı."""

    status: str                              # valid|invalid|sat|unsat|unknown|error
    reason_code: str                         # ENTAILED, COUNTEREXAMPLE_FOUND, SOLVER_TIMEOUT...
    explanation: str                         # insan-okur açıklama
    witness: dict[str, Any] | None = None    # model (sat) / karşıörnek (invalid)
    meta: dict[str, Any] = field(default_factory=dict)  # engine, seed, elapsed_ms, z3_version...

    def is_conclusive(self) -> bool:
        """Sonuç kesin mi? (unknown/error -> False)."""
        return self.status not in ("unknown", "error")


def check_entailment(
    premises: list[str],
    conclusion: str,
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ReasoningResult:
    """`premises ⊨ conclusion` mı? (öncüller sonucu mantıksal gerektirir mi).

    Yöntem (v1): (⋀ premises) ∧ ¬conclusion formülünün UNSAT olup olmadığına bak.
      * UNSAT -> entailment VAR      -> status="valid",   reason_code="ENTAILED"
      * SAT   -> bir KARŞIÖRNEK var  -> status="invalid",  witness=model
      * unknown/timeout -> status="unknown"

    Args:
        premises: mantık ifadeleri (gramer: docs/mcp-api.md).
        conclusion: tek bir mantık ifadesi.
        timeout_ms: guardrail zaman aşımı.
    """
    raise NotImplementedError("v1: Todo.md > T3")  # scaffold


def check_consistency(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ReasoningResult:
    """Bu ifadeler kümesi TUTARLI (aynı anda doğru olabilir) mi?

    Yöntem (v1): ⋀ statements SAT mı?
      * SAT   -> tutarlı   -> status="sat",   witness=model (örnek atama)
      * UNSAT -> çelişkili  -> status="unsat", witness=unsat_core (çelişen alt küme)
      * unknown/timeout -> status="unknown"
    """
    raise NotImplementedError("v1: Todo.md > T4")  # scaffold


def find_model(
    statements: list[str],
    *,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> ReasoningResult:
    """İfadeleri sağlayan somut bir MODEL (değişken ataması) bul.

    check_consistency ile aynı çekirdek; farkı, SAT durumunda modeli her zaman
    okunur biçimde döndürmeye odaklanır (karşıörnek üretimi için de kullanılır).
    """
    raise NotImplementedError("v1: Todo.md > T5")  # scaffold
