"""Immutable, canonical, non-authoritative proof-term values for MH-031.

The values in this module are candidate evidence.  Construction and parsing
establish only the closed structural invariants below; mathematical authority
belongs to the independent checker introduced by MH-032.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from typing import Any, NoReturn


PROOF_TERM_CONTRACT_ID = "MH-C-PROOF-TERM-001"
PROOF_TERM_CONTRACT_SHA256 = "20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac"

PROOF_TERM_SCHEMA = "mathhead.proof-term.v1"
MAX_INPUT_BYTES = 1_048_576
MAX_DEPTH = 64
MAX_NODES = 4_096
MAX_COEFFICIENTS = 4_096
MAX_CRT_PARTS = 1_024
MAX_INTEGER_BITS = 4_096


class ProofTermValidationError(ValueError):
    """A classified, fail-closed proof-term boundary error."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _ProofValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("proof terms cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("proof terms cannot be pickled")

    def __copy__(self) -> _ProofValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _ProofValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class ResidueTerm(_ProofValue):
    modulus: int
    polynomial: tuple[int, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("use residue() or parse_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("ResidueTerm is final")


@dataclass(frozen=True, slots=True, init=False)
class CRTTerm(_ProofValue):
    parts: tuple[ProofTerm, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("use crt() or parse_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("CRTTerm is final")


@dataclass(frozen=True, slots=True, init=False)
class SumInductionTerm(_ProofValue):
    summand: tuple[Fraction, ...]
    closed_form: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("use sum_induction() or parse_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SumInductionTerm is final")


@dataclass(frozen=True, slots=True, init=False)
class PolynomialIdentityTerm(_ProofValue):
    lhs: tuple[Fraction, ...]
    rhs: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("use polynomial_identity() or parse_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PolynomialIdentityTerm is final")


ProofTerm = ResidueTerm | CRTTerm | SumInductionTerm | PolynomialIdentityTerm


def _fail(kind: str, detail: str) -> NoReturn:
    raise ProofTermValidationError(kind, detail)


def _bounded_integer(value: object, label: str) -> int:
    if type(value) is bool:
        _fail("term", f"{label} rejects boolean integers")
    if type(value) is not int:
        _fail("term", f"{label} must be an exact integer")
    integer = value
    if integer.bit_length() > MAX_INTEGER_BITS:
        _fail("budget", f"{label} exceeds {MAX_INTEGER_BITS} bits")
    return integer


def _sequence(value: object, label: str, maximum: int) -> tuple[object, ...]:
    if type(value) not in {list, tuple}:
        _fail("term", f"{label} must be a list or tuple")
    if not value:
        _fail("term", f"{label} must not be empty")
    if len(value) > maximum:
        _fail("budget", f"{label} exceeds {maximum} items")
    return tuple(value)


def _integer_polynomial(value: object, label: str) -> tuple[int, ...]:
    raw = _sequence(value, label, MAX_COEFFICIENTS)
    result = [_bounded_integer(coefficient, f"{label} coefficient") for coefficient in raw]
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


def _rational(value: object, label: str) -> Fraction:
    if type(value) is bool or type(value) not in {int, Fraction}:
        _fail("term", f"{label} must be an exact integer or Fraction")
    fraction = Fraction(value)
    _bounded_integer(fraction.numerator, f"{label} numerator")
    _bounded_integer(fraction.denominator, f"{label} denominator")
    return fraction


def _rational_polynomial(value: object, label: str) -> tuple[Fraction, ...]:
    raw = _sequence(value, label, MAX_COEFFICIENTS)
    result = [_rational(coefficient, f"{label} coefficient") for coefficient in raw]
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


def _new_residue(modulus: int, polynomial: tuple[int, ...]) -> ResidueTerm:
    value = object.__new__(ResidueTerm)
    object.__setattr__(value, "modulus", modulus)
    object.__setattr__(value, "polynomial", polynomial)
    return value


def _new_crt(parts: tuple[ProofTerm, ...]) -> CRTTerm:
    value = object.__new__(CRTTerm)
    object.__setattr__(value, "parts", parts)
    return value


def _new_sum(summand: tuple[Fraction, ...], closed_form: tuple[Fraction, ...]) -> SumInductionTerm:
    value = object.__new__(SumInductionTerm)
    object.__setattr__(value, "summand", summand)
    object.__setattr__(value, "closed_form", closed_form)
    return value


def _new_identity(lhs: tuple[Fraction, ...], rhs: tuple[Fraction, ...]) -> PolynomialIdentityTerm:
    value = object.__new__(PolynomialIdentityTerm)
    object.__setattr__(value, "lhs", lhs)
    object.__setattr__(value, "rhs", rhs)
    return value


def residue(modulus: int, polynomial: list[int] | tuple[int, ...]) -> ResidueTerm:
    """Create one structurally valid residue-exhaustion candidate term."""
    checked_modulus = _bounded_integer(modulus, "modulus")
    if checked_modulus < 1:
        _fail("term", "modulus must be at least one")
    return _new_residue(checked_modulus, _integer_polynomial(polynomial, "polynomial"))


def crt(parts: list[ProofTerm] | tuple[ProofTerm, ...]) -> CRTTerm:
    """Create one canonical CRT candidate with bytewise-sorted child terms."""
    raw = _sequence(parts, "CRT parts", MAX_CRT_PARTS)
    checked: list[ProofTerm] = []
    for child in raw:
        validate_proof_term(child)
        checked.append(child)
    checked.sort(key=_canonical_term_bytes)
    value = _new_crt(tuple(checked))
    validate_proof_term(value)
    return value


def sum_induction(
    summand: list[int | Fraction] | tuple[int | Fraction, ...],
    closed_form: list[int | Fraction] | tuple[int | Fraction, ...],
) -> SumInductionTerm:
    """Create one exact polynomial finite-sum induction candidate term."""
    return _new_sum(
        _rational_polynomial(summand, "summand"),
        _rational_polynomial(closed_form, "closed form"),
    )


def polynomial_identity(
    lhs: list[int | Fraction] | tuple[int | Fraction, ...],
    rhs: list[int | Fraction] | tuple[int | Fraction, ...],
) -> PolynomialIdentityTerm:
    """Create one exact polynomial-identity candidate term."""
    return _new_identity(
        _rational_polynomial(lhs, "identity lhs"),
        _rational_polynomial(rhs, "identity rhs"),
    )


def validate_proof_term(term: object) -> None:
    """Revalidate a complete in-memory graph without trusting its constructor history."""
    active: set[int] = set()
    node_count = 0

    def walk(value: object, depth: int) -> None:
        nonlocal node_count
        if depth > MAX_DEPTH:
            _fail("budget", f"proof-term depth exceeds {MAX_DEPTH}")
        node_count += 1
        if node_count > MAX_NODES:
            _fail("budget", f"proof-term graph exceeds {MAX_NODES} nodes")
        identity = id(value)
        if identity in active:
            _fail("cycle", "proof-term graph contains an active object cycle")
        active.add(identity)
        try:
            if type(value) is ResidueTerm:
                try:
                    modulus = value.modulus
                    polynomial = value.polynomial
                except AttributeError:
                    _fail("term", "ResidueTerm has missing fields")
                if _bounded_integer(modulus, "modulus") < 1:
                    _fail("term", "modulus must be at least one")
                if type(polynomial) is not tuple:
                    _fail("term", "ResidueTerm polynomial must be an owned tuple")
                if _integer_polynomial(polynomial, "polynomial") != polynomial:
                    _fail("term", "ResidueTerm polynomial is not canonical")
                return
            if type(value) is CRTTerm:
                try:
                    parts = value.parts
                except AttributeError:
                    _fail("term", "CRTTerm has missing fields")
                if type(parts) is not tuple:
                    _fail("term", "CRTTerm parts must be an owned tuple")
                if not parts:
                    _fail("term", "CRTTerm parts must not be empty")
                if len(parts) > MAX_CRT_PARTS:
                    _fail("budget", f"CRT parts exceeds {MAX_CRT_PARTS} items")
                for child in parts:
                    walk(child, depth + 1)
                canonical = tuple(sorted(parts, key=_canonical_term_bytes))
                if parts != canonical:
                    _fail("term", "CRTTerm parts are not in canonical byte order")
                return
            if type(value) is SumInductionTerm:
                try:
                    summand = value.summand
                    closed_form = value.closed_form
                except AttributeError:
                    _fail("term", "SumInductionTerm has missing fields")
                if type(summand) is not tuple or type(closed_form) is not tuple:
                    _fail("term", "SumInductionTerm polynomials must be owned tuples")
                if _rational_polynomial(summand, "summand") != summand:
                    _fail("term", "summand polynomial is not canonical")
                if _rational_polynomial(closed_form, "closed form") != closed_form:
                    _fail("term", "closed-form polynomial is not canonical")
                return
            if type(value) is PolynomialIdentityTerm:
                try:
                    lhs = value.lhs
                    rhs = value.rhs
                except AttributeError:
                    _fail("term", "PolynomialIdentityTerm has missing fields")
                if type(lhs) is not tuple or type(rhs) is not tuple:
                    _fail("term", "identity polynomials must be owned tuples")
                if _rational_polynomial(lhs, "identity lhs") != lhs:
                    _fail("term", "identity lhs is not canonical")
                if _rational_polynomial(rhs, "identity rhs") != rhs:
                    _fail("term", "identity rhs is not canonical")
                return
            _fail("term", f"unknown proof-term type: {type(value).__name__}")
        finally:
            active.discard(identity)

    walk(term, 1)


def _fraction_object(value: Fraction) -> dict[str, int]:
    return {"denominator": value.denominator, "numerator": value.numerator}


def _term_object(term: ProofTerm) -> dict[str, Any]:
    if type(term) is ResidueTerm:
        return {
            "modulus": term.modulus,
            "polynomial": list(term.polynomial),
            "rule": "residue",
        }
    if type(term) is CRTTerm:
        return {"parts": [_term_object(child) for child in term.parts], "rule": "crt"}
    if type(term) is SumInductionTerm:
        return {
            "closed_form": [_fraction_object(value) for value in term.closed_form],
            "rule": "sum_induction",
            "summand": [_fraction_object(value) for value in term.summand],
        }
    if type(term) is PolynomialIdentityTerm:
        return {
            "lhs": [_fraction_object(value) for value in term.lhs],
            "rhs": [_fraction_object(value) for value in term.rhs],
            "rule": "polynomial_identity",
        }
    _fail("term", f"unknown proof-term type: {type(term).__name__}")


def _canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError, OverflowError) as exc:
        _fail("canonical", f"canonical JSON encoding failed: {type(exc).__name__}")
    return (text + "\n").encode("utf-8")


def _canonical_term_bytes(term: ProofTerm) -> bytes:
    return _canonical_json_bytes(_term_object(term))


def proof_term_sha256(term: ProofTerm) -> str:
    """Return the full identity of one revalidated canonical term object."""
    validate_proof_term(term)
    return hashlib.sha256(_canonical_term_bytes(term)).hexdigest()


def proof_term_to_bytes(term: ProofTerm) -> bytes:
    """Serialize one revalidated term into its closed canonical envelope."""
    validate_proof_term(term)
    envelope = {
        "schema": PROOF_TERM_SCHEMA,
        "term": _term_object(term),
        "term_sha256": proof_term_sha256(term),
    }
    return _canonical_json_bytes(envelope)


class _DuplicateKey(ValueError):
    pass


def _pairs_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _reject_number(value: str) -> NoReturn:
    del value
    raise ValueError("floating-point and non-finite JSON numbers are forbidden")


def _exact_keys(value: object, expected: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail("schema", f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        _fail("schema", f"{label} fields differ; missing={missing}, unknown={unknown}")
    return value


def _decode_rational(value: object, label: str) -> Fraction:
    item = _exact_keys(value, {"denominator", "numerator"}, label)
    numerator = _bounded_integer(item["numerator"], f"{label} numerator")
    denominator = _bounded_integer(item["denominator"], f"{label} denominator")
    if denominator < 1:
        _fail("term", f"{label} denominator must be positive")
    fraction = Fraction(numerator, denominator)
    if fraction.numerator != numerator or fraction.denominator != denominator:
        _fail("canonical", f"{label} is not a normalized Fraction")
    return fraction


def _decode_term(value: object, depth: int, count: list[int]) -> ProofTerm:
    if depth > MAX_DEPTH:
        _fail("budget", f"proof-term depth exceeds {MAX_DEPTH}")
    count[0] += 1
    if count[0] > MAX_NODES:
        _fail("budget", f"proof-term graph exceeds {MAX_NODES} nodes")
    if type(value) is not dict:
        _fail("schema", "term must be an object")
    rule = value.get("rule")
    if rule == "residue":
        item = _exact_keys(value, {"modulus", "polynomial", "rule"}, "residue term")
        return residue(item["modulus"], item["polynomial"])
    if rule == "crt":
        item = _exact_keys(value, {"parts", "rule"}, "CRT term")
        parts = _sequence(item["parts"], "CRT parts", MAX_CRT_PARTS)
        return crt(tuple(_decode_term(child, depth + 1, count) for child in parts))
    if rule == "sum_induction":
        item = _exact_keys(value, {"closed_form", "rule", "summand"}, "sum term")
        summand_raw = _sequence(item["summand"], "summand", MAX_COEFFICIENTS)
        closed_raw = _sequence(item["closed_form"], "closed form", MAX_COEFFICIENTS)
        summand = tuple(
            _decode_rational(coefficient, "summand coefficient") for coefficient in summand_raw
        )
        closed = tuple(
            _decode_rational(coefficient, "closed-form coefficient") for coefficient in closed_raw
        )
        term = sum_induction(summand, closed)
        if term.summand != summand or term.closed_form != closed:
            _fail("canonical", "sum polynomials contain noncanonical trailing zeroes")
        return term
    if rule == "polynomial_identity":
        item = _exact_keys(value, {"lhs", "rhs", "rule"}, "identity term")
        lhs_raw = _sequence(item["lhs"], "identity lhs", MAX_COEFFICIENTS)
        rhs_raw = _sequence(item["rhs"], "identity rhs", MAX_COEFFICIENTS)
        lhs = tuple(_decode_rational(coefficient, "lhs coefficient") for coefficient in lhs_raw)
        rhs = tuple(_decode_rational(coefficient, "rhs coefficient") for coefficient in rhs_raw)
        term = polynomial_identity(lhs, rhs)
        if term.lhs != lhs or term.rhs != rhs:
            _fail("canonical", "identity polynomials contain noncanonical trailing zeroes")
        return term
    _fail("schema", f"unknown proof-term rule: {rule!r}")


def parse_proof_term(data: bytes) -> ProofTerm:
    """Parse exact canonical proof-term bytes and return a non-authoritative value."""
    if type(data) is not bytes:
        _fail("type", "proof-term input must be exact bytes")
    if len(data) > MAX_INPUT_BYTES:
        _fail("budget", f"proof-term input exceeds {MAX_INPUT_BYTES} bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        _fail("encoding", f"invalid UTF-8 at byte {exc.start}")
    try:
        raw = json.loads(
            text,
            object_pairs_hook=_pairs_object,
            parse_float=_reject_number,
            parse_constant=_reject_number,
        )
    except _DuplicateKey as exc:
        _fail("duplicate", f"duplicate JSON key: {exc.args[0]}")
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        _fail("json", f"invalid proof-term JSON: {type(exc).__name__}")
    except RecursionError:
        _fail("budget", "JSON nesting exceeds the parser depth budget")
    envelope = _exact_keys(raw, {"schema", "term", "term_sha256"}, "proof-term envelope")
    if envelope["schema"] != PROOF_TERM_SCHEMA:
        _fail("schema", f"unsupported proof-term schema: {envelope['schema']!r}")
    digest = envelope["term_sha256"]
    if (
        type(digest) is not str
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        _fail("schema", "term_sha256 must be 64 lowercase hexadecimal characters")
    term = _decode_term(envelope["term"], 1, [0])
    actual_digest = proof_term_sha256(term)
    if digest != actual_digest:
        _fail("identity", f"term_sha256 mismatch: expected {actual_digest}, got {digest}")
    expected_bytes = proof_term_to_bytes(term)
    if data != expected_bytes:
        _fail("canonical", "proof-term envelope bytes are not canonical")
    return term


__all__ = [
    "CRTTerm",
    "MAX_COEFFICIENTS",
    "MAX_CRT_PARTS",
    "MAX_DEPTH",
    "MAX_INPUT_BYTES",
    "MAX_INTEGER_BITS",
    "MAX_NODES",
    "PROOF_TERM_CONTRACT_ID",
    "PROOF_TERM_CONTRACT_SHA256",
    "PROOF_TERM_SCHEMA",
    "PolynomialIdentityTerm",
    "ProofTerm",
    "ProofTermValidationError",
    "ResidueTerm",
    "SumInductionTerm",
    "crt",
    "parse_proof_term",
    "polynomial_identity",
    "proof_term_sha256",
    "proof_term_to_bytes",
    "residue",
    "sum_induction",
    "validate_proof_term",
]
