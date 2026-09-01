"""Non-authoritative migration from legacy discovery proof terms.

This adapter preserves candidate evidence only.  It never imports the new
checker and therefore cannot issue a checker attestation.  Callers must pass
the returned MH-031 proof term to ``mathhead.kernel.checkers.check_proof_term``
before treating any statement as verified.
"""

from __future__ import annotations

from typing import NoReturn

from mathhead.kernel.proof_terms import (
    MAX_DEPTH,
    MAX_NODES,
    ProofTerm,
    ProofTermValidationError,
    crt,
    polynomial_identity,
    residue,
    sum_induction,
)


_LEGACY_MODULE = "mathhead.discovery.kernel"
_LEGACY_TERM_NAMES = {"CRT", "Identity", "Residue", "SumInduction", "Theorem"}


class LegacyProofAdapterError(ValueError):
    """A classified, non-promoting legacy migration failure."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


def _fail(kind: str, detail: str) -> NoReturn:
    raise LegacyProofAdapterError(kind, detail)


def adapt_legacy_proof_term(term: object) -> ProofTerm:
    """Convert one exact legacy proof-term graph into candidate evidence.

    The guarded-but-forgeable legacy ``Theorem`` representation is rejected;
    it is a result value, not replayable evidence.  Exact legacy term classes
    are copied through the closed MH-031 factories under the same graph and
    scalar budgets.  The output remains non-authoritative until MH-032 checks
    it independently.
    """

    active: set[int] = set()
    node_count = 0

    def walk(value: object, depth: int) -> ProofTerm:
        nonlocal node_count
        if depth > MAX_DEPTH:
            _fail("budget", f"legacy proof-term depth exceeds {MAX_DEPTH}")
        node_count += 1
        if node_count > MAX_NODES:
            _fail("budget", f"legacy proof-term graph exceeds {MAX_NODES} nodes")

        identity = id(value)
        if identity in active:
            _fail("cycle", "legacy proof-term graph contains an active object cycle")
        active.add(identity)
        try:
            value_type = type(value)
            legacy_name = value_type.__name__
            if value_type.__module__ != _LEGACY_MODULE or legacy_name not in _LEGACY_TERM_NAMES:
                _fail("unsupported", f"unsupported legacy input type: {legacy_name}")
            if legacy_name == "Residue":
                try:
                    return residue(value.modulus, value.poly)
                except AttributeError:
                    _fail("malformed", "legacy Residue has missing fields")
            if legacy_name == "CRT":
                try:
                    parts = value.parts
                except AttributeError:
                    _fail("malformed", "legacy CRT has missing fields")
                if type(parts) is not tuple:
                    _fail("malformed", "legacy CRT parts must be an owned tuple")
                return crt(tuple(walk(child, depth + 1) for child in parts))
            if legacy_name == "SumInduction":
                try:
                    return sum_induction(value.f_poly, value.g_poly)
                except AttributeError:
                    _fail("malformed", "legacy SumInduction has missing fields")
            if legacy_name == "Identity":
                try:
                    return polynomial_identity(value.lhs, value.rhs)
                except AttributeError:
                    _fail("malformed", "legacy Identity has missing fields")
            if legacy_name == "Theorem":
                _fail("authority", "legacy Theorem values are not replayable proof evidence")
            _fail("unsupported", f"unsupported legacy input type: {legacy_name}")
        except LegacyProofAdapterError:
            raise
        except ProofTermValidationError as exc:
            _fail(exc.kind, exc.detail)
        except (TypeError, ValueError, OverflowError, ArithmeticError) as exc:
            _fail("malformed", f"legacy term conversion failed: {type(exc).__name__}")
        finally:
            active.remove(identity)

    return walk(term, 1)


__all__ = ["LegacyProofAdapterError", "adapt_legacy_proof_term"]
