"""Immutable explicit arithmetic evidence for the dependency-minimal kernel.

These values carry no authority on their own.  Only the checker may construct
them during exact replay, and every result boundary compares them with a fresh
derivation from the retained proof term.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, NoReturn


class _EvidenceValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("arithmetic evidence cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("arithmetic evidence cannot be pickled")

    def __copy__(self) -> _EvidenceValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _EvidenceValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class ResidueEvaluation(_EvidenceValue):
    residue: int
    value: int
    quotient: int
    remainder: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("residue evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ResidueEvaluation is final")


@dataclass(frozen=True, slots=True, init=False)
class ResidueEvidence(_EvidenceValue):
    modulus: int
    polynomial: tuple[int, ...]
    evaluations: tuple[ResidueEvaluation, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("residue evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ResidueEvidence is final")


@dataclass(frozen=True, slots=True, init=False)
class BezoutWitness(_EvidenceValue):
    left_modulus: int
    right_modulus: int
    gcd: int
    left_coefficient: int
    right_coefficient: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("Bezout evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("BezoutWitness is final")


@dataclass(frozen=True, slots=True, init=False)
class ProductStep(_EvidenceValue):
    prior_product: int
    factor: int
    product: int

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("product evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ProductStep is final")


@dataclass(frozen=True, slots=True, init=False)
class CRTEvidence(_EvidenceValue):
    premises: tuple[ResidueEvidence | CRTEvidence, ...]
    bezout_witnesses: tuple[BezoutWitness, ...]
    product_steps: tuple[ProductStep, ...]
    modulus: int
    polynomial: tuple[int, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("CRT evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("CRTEvidence is final")


@dataclass(frozen=True, slots=True, init=False)
class SumInductionEvidence(_EvidenceValue):
    summand: tuple[Fraction, ...]
    closed_form: tuple[Fraction, ...]
    summand_at_one: Fraction
    closed_form_at_one: Fraction
    shifted_closed_form: tuple[Fraction, ...]
    first_difference: tuple[Fraction, ...]
    step_difference: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("sum evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SumInductionEvidence is final")


@dataclass(frozen=True, slots=True, init=False)
class PolynomialIdentityEvidence(_EvidenceValue):
    lhs: tuple[Fraction, ...]
    rhs: tuple[Fraction, ...]
    difference: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("identity evidence is derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PolynomialIdentityEvidence is final")


DivisibilityEvidence = ResidueEvidence | CRTEvidence
ArithmeticEvidence = (
    ResidueEvidence | CRTEvidence | SumInductionEvidence | PolynomialIdentityEvidence
)


def _new_residue_evaluation(
    residue: int, value: int, quotient: int, remainder: int
) -> ResidueEvaluation:
    result = object.__new__(ResidueEvaluation)
    object.__setattr__(result, "residue", residue)
    object.__setattr__(result, "value", value)
    object.__setattr__(result, "quotient", quotient)
    object.__setattr__(result, "remainder", remainder)
    return result


def _new_residue_evidence(
    modulus: int,
    polynomial: tuple[int, ...],
    evaluations: tuple[ResidueEvaluation, ...],
) -> ResidueEvidence:
    result = object.__new__(ResidueEvidence)
    object.__setattr__(result, "modulus", modulus)
    object.__setattr__(result, "polynomial", polynomial)
    object.__setattr__(result, "evaluations", evaluations)
    return result


def _new_bezout_witness(
    left_modulus: int,
    right_modulus: int,
    gcd_value: int,
    left_coefficient: int,
    right_coefficient: int,
) -> BezoutWitness:
    result = object.__new__(BezoutWitness)
    object.__setattr__(result, "left_modulus", left_modulus)
    object.__setattr__(result, "right_modulus", right_modulus)
    object.__setattr__(result, "gcd", gcd_value)
    object.__setattr__(result, "left_coefficient", left_coefficient)
    object.__setattr__(result, "right_coefficient", right_coefficient)
    return result


def _new_product_step(prior_product: int, factor: int, product: int) -> ProductStep:
    result = object.__new__(ProductStep)
    object.__setattr__(result, "prior_product", prior_product)
    object.__setattr__(result, "factor", factor)
    object.__setattr__(result, "product", product)
    return result


def _new_crt_evidence(
    premises: tuple[DivisibilityEvidence, ...],
    bezout_witnesses: tuple[BezoutWitness, ...],
    product_steps: tuple[ProductStep, ...],
    modulus: int,
    polynomial: tuple[int, ...],
) -> CRTEvidence:
    result = object.__new__(CRTEvidence)
    object.__setattr__(result, "premises", premises)
    object.__setattr__(result, "bezout_witnesses", bezout_witnesses)
    object.__setattr__(result, "product_steps", product_steps)
    object.__setattr__(result, "modulus", modulus)
    object.__setattr__(result, "polynomial", polynomial)
    return result


def _new_sum_evidence(
    summand: tuple[Fraction, ...],
    closed_form: tuple[Fraction, ...],
    summand_at_one: Fraction,
    closed_form_at_one: Fraction,
    shifted_closed_form: tuple[Fraction, ...],
    first_difference: tuple[Fraction, ...],
    step_difference: tuple[Fraction, ...],
) -> SumInductionEvidence:
    result = object.__new__(SumInductionEvidence)
    object.__setattr__(result, "summand", summand)
    object.__setattr__(result, "closed_form", closed_form)
    object.__setattr__(result, "summand_at_one", summand_at_one)
    object.__setattr__(result, "closed_form_at_one", closed_form_at_one)
    object.__setattr__(result, "shifted_closed_form", shifted_closed_form)
    object.__setattr__(result, "first_difference", first_difference)
    object.__setattr__(result, "step_difference", step_difference)
    return result


def _new_polynomial_identity_evidence(
    lhs: tuple[Fraction, ...],
    rhs: tuple[Fraction, ...],
    difference: tuple[Fraction, ...],
) -> PolynomialIdentityEvidence:
    result = object.__new__(PolynomialIdentityEvidence)
    object.__setattr__(result, "lhs", lhs)
    object.__setattr__(result, "rhs", rhs)
    object.__setattr__(result, "difference", difference)
    return result


__all__ = [
    "ArithmeticEvidence",
    "BezoutWitness",
    "CRTEvidence",
    "DivisibilityEvidence",
    "PolynomialIdentityEvidence",
    "ProductStep",
    "ResidueEvaluation",
    "ResidueEvidence",
    "SumInductionEvidence",
]
