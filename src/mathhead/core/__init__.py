"""Mantık çekirdeği (reasoning core) — Z3 tabanlı deterministik ilkeller."""

from mathhead.core.logic import (
    ReasoningResult,
    check_consistency,
    check_entailment,
    find_model,
)

__all__ = [
    "ReasoningResult",
    "check_consistency",
    "check_entailment",
    "find_model",
]
