"""Reasoning core — Z3-based deterministic primitives."""

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
