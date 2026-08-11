"""Dependency-minimal exact checker for the MH-031 proof-term algebra.

Proof terms are untrusted structural values. This module is the only new
boundary that may issue ``checker_attestation`` for the supported fragment,
and every serialization boundary replays the decision instead of trusting an
object's constructor history.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from math import comb, gcd
from typing import Any, NoReturn

from mathhead.kernel.proof_terms import (
    CRTTerm,
    PROOF_TERM_CONTRACT_ID,
    PROOF_TERM_CONTRACT_SHA256,
    PolynomialIdentityTerm,
    ProofTerm,
    ProofTermValidationError,
    ResidueTerm,
    SumInductionTerm,
    parse_proof_term,
    proof_term_sha256,
    proof_term_to_bytes,
    validate_proof_term,
)


KERNEL_CHECKER_CONTRACT_ID = "MH-C-KERNEL-CHECKER-001"
KERNEL_CHECKER_CONTRACT_SHA256 = "78293c5a2e8845377e8bd704398c7a0058afcea74017dffbc2a18daac97ecff7"
KERNEL_CHECKER_ID = "mathhead.kernel.checker.v1"
KERNEL_CHECKER_RESULT_SCHEMA = "mathhead.kernel-checker-result.v1"

MAX_RESULT_INPUT_BYTES = 2_200_000
MAX_CHECK_STEPS = 1_000_000
MAX_DERIVED_INTEGER_BITS = 16_384


class CheckerResultValidationError(ValueError):
    """A classified, fail-closed checker-result boundary error."""

    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(f"{kind}: {detail}")


class _CheckerValue:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        raise TypeError("checker values cannot be pickled")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("checker values cannot be pickled")

    def __copy__(self) -> _CheckerValue:
        return self

    def __deepcopy__(self, memo: dict[int, Any]) -> _CheckerValue:
        del memo
        return self


@dataclass(frozen=True, slots=True, init=False)
class DividesStatement(_CheckerValue):
    modulus: int
    polynomial: tuple[int, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("statements are derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("DividesStatement is final")


@dataclass(frozen=True, slots=True, init=False)
class SumIdentityStatement(_CheckerValue):
    summand: tuple[Fraction, ...]
    closed_form: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("statements are derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("SumIdentityStatement is final")


@dataclass(frozen=True, slots=True, init=False)
class PolynomialIdentityStatement(_CheckerValue):
    lhs: tuple[Fraction, ...]
    rhs: tuple[Fraction, ...]

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("statements are derived only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("PolynomialIdentityStatement is final")


Statement = DividesStatement | SumIdentityStatement | PolynomialIdentityStatement


@dataclass(frozen=True, slots=True, init=False)
class CheckerResult(_CheckerValue):
    verdict: str
    reason_code: str
    diagnostic: str
    authority: str
    exact: bool
    proof_term: ProofTerm | None
    proof_term_sha256: str | None
    statement: Statement | None
    steps: int
    checker_id: str
    checker_contract_id: str
    checker_contract_sha256: str
    proof_term_contract_id: str
    proof_term_contract_sha256: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise PermissionError("checker results are created only by check_proof_term()")

    def __init_subclass__(cls, **kwargs: object) -> NoReturn:
        del cls, kwargs
        raise TypeError("CheckerResult is final")


class _InvalidProof(ValueError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        self.reason_code = reason_code
        self.diagnostic = diagnostic
        super().__init__(reason_code)


class _BudgetExhausted(ValueError):
    pass


@dataclass(slots=True)
class _WorkBudget:
    used: int = 0

    def consume(self, amount: int = 1) -> None:
        if type(amount) is not int or amount < 0:
            raise AssertionError("checker step charge must be a nonnegative exact integer")
        if amount > MAX_CHECK_STEPS - self.used:
            raise _BudgetExhausted
        self.used += amount


def _fail(kind: str, detail: str) -> NoReturn:
    raise CheckerResultValidationError(kind, detail)


def _new_divides(modulus: int, polynomial: tuple[int, ...]) -> DividesStatement:
    value = object.__new__(DividesStatement)
    object.__setattr__(value, "modulus", modulus)
    object.__setattr__(value, "polynomial", polynomial)
    return value


def _new_sum(
    summand: tuple[Fraction, ...], closed_form: tuple[Fraction, ...]
) -> SumIdentityStatement:
    value = object.__new__(SumIdentityStatement)
    object.__setattr__(value, "summand", summand)
    object.__setattr__(value, "closed_form", closed_form)
    return value


def _new_identity(
    lhs: tuple[Fraction, ...], rhs: tuple[Fraction, ...]
) -> PolynomialIdentityStatement:
    value = object.__new__(PolynomialIdentityStatement)
    object.__setattr__(value, "lhs", lhs)
    object.__setattr__(value, "rhs", rhs)
    return value


def _new_result(
    verdict: str,
    reason_code: str,
    diagnostic: str,
    *,
    proof_term: ProofTerm | None,
    proof_term_digest: str | None,
    statement: Statement | None,
    steps: int,
) -> CheckerResult:
    value = object.__new__(CheckerResult)
    fields: dict[str, object] = {
        "authority": "checker_attestation" if verdict == "verified" else "none",
        "checker_contract_id": KERNEL_CHECKER_CONTRACT_ID,
        "checker_contract_sha256": KERNEL_CHECKER_CONTRACT_SHA256,
        "checker_id": KERNEL_CHECKER_ID,
        "diagnostic": diagnostic,
        "exact": True,
        "proof_term": proof_term,
        "proof_term_contract_id": PROOF_TERM_CONTRACT_ID,
        "proof_term_contract_sha256": PROOF_TERM_CONTRACT_SHA256,
        "proof_term_sha256": proof_term_digest,
        "reason_code": reason_code,
        "statement": statement,
        "steps": steps,
        "verdict": verdict,
    }
    for name, field_value in fields.items():
        object.__setattr__(value, name, field_value)
    return value


def _bounded_fraction(value: Fraction) -> Fraction:
    if (
        value.numerator.bit_length() > MAX_DERIVED_INTEGER_BITS
        or value.denominator.bit_length() > MAX_DERIVED_INTEGER_BITS
    ):
        raise _BudgetExhausted
    return value


def _trim_fraction_polynomial(values: list[Fraction]) -> tuple[Fraction, ...]:
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    return tuple(values)


def _evaluate_at_one(polynomial: tuple[Fraction, ...], budget: _WorkBudget) -> Fraction:
    budget.consume(len(polynomial))
    total = Fraction(0)
    for coefficient in polynomial:
        total = _bounded_fraction(total + coefficient)
    return total


def _subtract_polynomials(
    left: tuple[Fraction, ...], right: tuple[Fraction, ...], budget: _WorkBudget
) -> tuple[Fraction, ...]:
    size = max(len(left), len(right))
    budget.consume(size)
    result: list[Fraction] = []
    for index in range(size):
        left_value = left[index] if index < len(left) else Fraction(0)
        right_value = right[index] if index < len(right) else Fraction(0)
        result.append(_bounded_fraction(left_value - right_value))
    return _trim_fraction_polynomial(result)


def _shift_back(polynomial: tuple[Fraction, ...], budget: _WorkBudget) -> tuple[Fraction, ...]:
    pair_count = len(polynomial) * (len(polynomial) + 1) // 2
    budget.consume(pair_count * 2)
    result = [Fraction(0)] * len(polynomial)
    for degree, coefficient in enumerate(polynomial):
        for power in range(degree + 1):
            signed_binomial = comb(degree, power) * (-1 if (degree - power) % 2 else 1)
            contribution = _bounded_fraction(coefficient * signed_binomial)
            result[power] = _bounded_fraction(result[power] + contribution)
    return _trim_fraction_polynomial(result)


def _check_supported(term: ProofTerm, budget: _WorkBudget) -> Statement:
    if type(term) is ResidueTerm:
        required = term.modulus * len(term.polynomial)
        budget.consume(required)
        for residue_value in range(term.modulus):
            value = 0
            for coefficient in reversed(term.polynomial):
                value = (value * residue_value + coefficient) % term.modulus
            if value != 0:
                raise _InvalidProof(
                    "RESIDUE_COUNTEREXAMPLE", "residue sweep found a counterexample"
                )
        return _new_divides(term.modulus, term.polynomial)

    if type(term) is CRTTerm:
        premises: list[DividesStatement] = []
        for part in term.parts:
            try:
                statement = _check_supported(part, budget)
            except _InvalidProof as exc:
                raise _InvalidProof("CRT_PREMISE_INVALID", "a CRT premise did not verify") from exc
            if type(statement) is not DividesStatement:
                raise _InvalidProof("CRT_PREMISE_INVALID", "a CRT premise did not verify")
            premises.append(statement)
        polynomial = premises[0].polynomial
        for premise in premises[1:]:
            budget.consume()
            if premise.polynomial != polynomial:
                raise _InvalidProof(
                    "CRT_POLYNOMIAL_MISMATCH", "CRT premises prove different polynomials"
                )
        for left_index, left in enumerate(premises):
            for right in premises[left_index + 1 :]:
                budget.consume()
                if gcd(left.modulus, right.modulus) != 1:
                    raise _InvalidProof("CRT_NON_COPRIME", "CRT moduli are not pairwise coprime")
        modulus = 1
        for premise in premises:
            budget.consume()
            modulus *= premise.modulus
            if modulus.bit_length() > MAX_DERIVED_INTEGER_BITS:
                raise _BudgetExhausted
        return _new_divides(modulus, polynomial)

    if type(term) is SumInductionTerm:
        if _evaluate_at_one(term.closed_form, budget) != _evaluate_at_one(term.summand, budget):
            raise _InvalidProof("SUM_BASE_MISMATCH", "sum induction base case differs")
        shifted = _shift_back(term.closed_form, budget)
        difference = _subtract_polynomials(term.closed_form, shifted, budget)
        step = _subtract_polynomials(difference, term.summand, budget)
        if step != (Fraction(0),):
            raise _InvalidProof("SUM_STEP_MISMATCH", "sum induction step polynomial is nonzero")
        return _new_sum(term.summand, term.closed_form)

    if type(term) is PolynomialIdentityTerm:
        difference = _subtract_polynomials(term.lhs, term.rhs, budget)
        if difference != (Fraction(0),):
            raise _InvalidProof("POLYNOMIAL_MISMATCH", "polynomial coefficients differ")
        return _new_identity(term.lhs, term.rhs)

    raise _InvalidProof("UNSUPPORTED_TERM", "proof-term rule is unsupported")


def check_proof_term(term: object) -> CheckerResult:
    """Independently check one untrusted proof term inside deterministic budgets."""
    supported_types = (ResidueTerm, CRTTerm, SumInductionTerm, PolynomialIdentityTerm)
    if type(term) not in supported_types:
        return _new_result(
            "invalid",
            "UNSUPPORTED_TERM",
            "proof-term rule is unsupported",
            proof_term=None,
            proof_term_digest=None,
            statement=None,
            steps=0,
        )
    try:
        validate_proof_term(term)
        digest = proof_term_sha256(term)
    except ProofTermValidationError:
        return _new_result(
            "invalid",
            "TERM_INVALID",
            "proof term is structurally invalid",
            proof_term=None,
            proof_term_digest=None,
            statement=None,
            steps=0,
        )
    budget = _WorkBudget()
    try:
        statement = _check_supported(term, budget)
    except _BudgetExhausted:
        return _new_result(
            "exhausted",
            "BUDGET_EXHAUSTED",
            "deterministic checker work budget exhausted",
            proof_term=term,
            proof_term_digest=digest,
            statement=None,
            steps=budget.used,
        )
    except _InvalidProof as exc:
        return _new_result(
            "invalid",
            exc.reason_code,
            exc.diagnostic,
            proof_term=term,
            proof_term_digest=digest,
            statement=None,
            steps=budget.used,
        )
    return _new_result(
        "verified",
        "CHECKER_VALID",
        "proof term checked exactly",
        proof_term=term,
        proof_term_digest=digest,
        statement=statement,
        steps=budget.used,
    )


_REASON_DIAGNOSTIC = {
    "BUDGET_EXHAUSTED": "deterministic checker work budget exhausted",
    "CHECKER_VALID": "proof term checked exactly",
    "CRT_NON_COPRIME": "CRT moduli are not pairwise coprime",
    "CRT_POLYNOMIAL_MISMATCH": "CRT premises prove different polynomials",
    "CRT_PREMISE_INVALID": "a CRT premise did not verify",
    "POLYNOMIAL_MISMATCH": "polynomial coefficients differ",
    "RESIDUE_COUNTEREXAMPLE": "residue sweep found a counterexample",
    "SUM_BASE_MISMATCH": "sum induction base case differs",
    "SUM_STEP_MISMATCH": "sum induction step polynomial is nonzero",
    "TERM_INVALID": "proof term is structurally invalid",
    "UNSUPPORTED_TERM": "proof-term rule is unsupported",
}


def validate_checker_result(result: object) -> None:
    """Recompute a complete result without trusting its constructor history."""
    if type(result) is not CheckerResult:
        _fail("result", f"unknown checker-result type: {type(result).__name__}")
    try:
        fields = (
            result.verdict,
            result.reason_code,
            result.diagnostic,
            result.authority,
            result.exact,
            result.proof_term,
            result.proof_term_sha256,
            result.statement,
            result.steps,
            result.checker_id,
            result.checker_contract_id,
            result.checker_contract_sha256,
            result.proof_term_contract_id,
            result.proof_term_contract_sha256,
        )
    except AttributeError:
        _fail("result", "CheckerResult has missing fields")
    del fields
    if (
        result.checker_id != KERNEL_CHECKER_ID
        or result.checker_contract_id != KERNEL_CHECKER_CONTRACT_ID
        or result.checker_contract_sha256 != KERNEL_CHECKER_CONTRACT_SHA256
        or result.proof_term_contract_id != PROOF_TERM_CONTRACT_ID
        or result.proof_term_contract_sha256 != PROOF_TERM_CONTRACT_SHA256
    ):
        _fail("identity", "checker or proof-term contract identity differs")
    string_fields = {
        "authority": result.authority,
        "checker_contract_id": result.checker_contract_id,
        "checker_contract_sha256": result.checker_contract_sha256,
        "checker_id": result.checker_id,
        "diagnostic": result.diagnostic,
        "proof_term_contract_id": result.proof_term_contract_id,
        "proof_term_contract_sha256": result.proof_term_contract_sha256,
        "reason_code": result.reason_code,
        "verdict": result.verdict,
    }
    for label, value in string_fields.items():
        if type(value) is not str:
            _fail("result", f"{label} must be an exact string")
    if type(result.exact) is not bool or not result.exact:
        _fail("result", "checker exactness must be true")
    if type(result.steps) is not int or type(result.steps) is bool:
        _fail("result", "checker steps must be an exact integer")
    if not 0 <= result.steps <= MAX_CHECK_STEPS:
        _fail("budget", f"checker steps must be between zero and {MAX_CHECK_STEPS}")
    if result.reason_code not in _REASON_DIAGNOSTIC:
        _fail("result", "unknown checker reason code")
    if result.diagnostic != _REASON_DIAGNOSTIC[result.reason_code]:
        _fail("result", "checker reason and diagnostic differ")
    if result.proof_term is None:
        if (
            result.verdict != "invalid"
            or result.reason_code not in {"TERM_INVALID", "UNSUPPORTED_TERM"}
            or result.authority != "none"
            or result.proof_term_sha256 is not None
            or result.statement is not None
            or result.steps != 0
        ):
            _fail("result", "term-less checker result is not a canonical invalid result")
        return
    if result.statement is not None and type(result.statement) not in {
        DividesStatement,
        SumIdentityStatement,
        PolynomialIdentityStatement,
    }:
        _fail("result", "unknown checker statement type")
    if result.proof_term_sha256 is not None:
        _lower_sha256(result.proof_term_sha256, "proof_term_sha256")
    try:
        validate_proof_term(result.proof_term)
        digest = proof_term_sha256(result.proof_term)
    except ProofTermValidationError as exc:
        _fail("result", f"retained proof term is invalid: {exc.kind}")
    if result.proof_term_sha256 != digest:
        _fail("identity", "retained proof-term identity differs")
    expected = check_proof_term(result.proof_term)
    if result != expected:
        _fail("result", "checker result differs from independent recomputation")


def _fraction_object(value: Fraction) -> dict[str, int]:
    return {"denominator": value.denominator, "numerator": value.numerator}


def _statement_object(statement: Statement | None) -> dict[str, Any] | None:
    if statement is None:
        return None
    if type(statement) is DividesStatement:
        return {
            "kind": "divides",
            "modulus": statement.modulus,
            "polynomial": list(statement.polynomial),
        }
    if type(statement) is SumIdentityStatement:
        return {
            "closed_form": [_fraction_object(value) for value in statement.closed_form],
            "kind": "sum_identity",
            "summand": [_fraction_object(value) for value in statement.summand],
        }
    if type(statement) is PolynomialIdentityStatement:
        return {
            "kind": "polynomial_identity",
            "lhs": [_fraction_object(value) for value in statement.lhs],
            "rhs": [_fraction_object(value) for value in statement.rhs],
        }
    _fail("result", f"unknown checker statement type: {type(statement).__name__}")


def _result_object(result: CheckerResult) -> dict[str, Any]:
    term_hex = None
    if result.proof_term is not None:
        term_hex = proof_term_to_bytes(result.proof_term).hex()
    return {
        "authority": result.authority,
        "checker": {
            "checker_id": result.checker_id,
            "contract_id": result.checker_contract_id,
            "contract_sha256": result.checker_contract_sha256,
        },
        "diagnostic": result.diagnostic,
        "exact": result.exact,
        "proof_term_contract": {
            "contract_id": result.proof_term_contract_id,
            "contract_sha256": result.proof_term_contract_sha256,
        },
        "proof_term_hex": term_hex,
        "proof_term_sha256": result.proof_term_sha256,
        "reason_code": result.reason_code,
        "statement": _statement_object(result.statement),
        "steps": result.steps,
        "verdict": result.verdict,
    }


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


def _canonical_result_bytes(result: CheckerResult) -> bytes:
    return _canonical_json_bytes(_result_object(result))


def checker_result_sha256(result: CheckerResult) -> str:
    """Return the full identity of one replayed canonical result object."""
    validate_checker_result(result)
    return hashlib.sha256(_canonical_result_bytes(result)).hexdigest()


def checker_result_to_bytes(result: CheckerResult) -> bytes:
    """Serialize a result only after independently recomputing its decision."""
    validate_checker_result(result)
    envelope = {
        "result": _result_object(result),
        "result_sha256": checker_result_sha256(result),
        "schema": KERNEL_CHECKER_RESULT_SCHEMA,
    }
    encoded = _canonical_json_bytes(envelope)
    if len(encoded) > MAX_RESULT_INPUT_BYTES:
        _fail("budget", f"checker-result output exceeds {MAX_RESULT_INPUT_BYTES} bytes")
    return encoded


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


def _lower_sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail("schema", f"{label} must be 64 lowercase hexadecimal characters")
    return value


def _decode_term_hex(value: object) -> ProofTerm | None:
    if value is None:
        return None
    if type(value) is not str or not value or len(value) % 2:
        _fail("schema", "proof_term_hex must be nonempty lowercase byte hex or null")
    if len(value) > 2_097_152 or any(character not in "0123456789abcdef" for character in value):
        _fail("budget", "proof_term_hex exceeds its budget or is not lowercase byte hex")
    try:
        term_bytes = bytes.fromhex(value)
        return parse_proof_term(term_bytes)
    except (ValueError, ProofTermValidationError) as exc:
        _fail("result", f"embedded proof term is invalid: {type(exc).__name__}")


def _expected_without_term(item: dict[str, Any]) -> CheckerResult:
    reason = item["reason_code"]
    if type(reason) is not str or reason not in {"TERM_INVALID", "UNSUPPORTED_TERM"}:
        _fail("result", "term-less result must classify invalid or unsupported structure")
    return _new_result(
        "invalid",
        reason,
        _REASON_DIAGNOSTIC[reason],
        proof_term=None,
        proof_term_digest=None,
        statement=None,
        steps=0,
    )


def parse_checker_result(data: bytes) -> CheckerResult:
    """Parse canonical result bytes and independently replay their decision."""
    if type(data) is not bytes:
        _fail("type", "checker-result input must be exact bytes")
    if len(data) > MAX_RESULT_INPUT_BYTES:
        _fail("budget", f"checker-result input exceeds {MAX_RESULT_INPUT_BYTES} bytes")
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
        _fail("json", f"invalid checker-result JSON: {type(exc).__name__}")
    except RecursionError:
        _fail("budget", "JSON nesting exceeds the parser depth budget")
    envelope = _exact_keys(raw, {"result", "result_sha256", "schema"}, "result envelope")
    if envelope["schema"] != KERNEL_CHECKER_RESULT_SCHEMA:
        _fail("schema", f"unsupported checker-result schema: {envelope['schema']!r}")
    digest = _lower_sha256(envelope["result_sha256"], "result_sha256")
    item = _exact_keys(
        envelope["result"],
        {
            "authority",
            "checker",
            "diagnostic",
            "exact",
            "proof_term_contract",
            "proof_term_hex",
            "proof_term_sha256",
            "reason_code",
            "statement",
            "steps",
            "verdict",
        },
        "result",
    )
    checker = _exact_keys(
        item["checker"], {"checker_id", "contract_id", "contract_sha256"}, "checker"
    )
    proof_contract = _exact_keys(
        item["proof_term_contract"],
        {"contract_id", "contract_sha256"},
        "proof_term_contract",
    )
    if checker != {
        "checker_id": KERNEL_CHECKER_ID,
        "contract_id": KERNEL_CHECKER_CONTRACT_ID,
        "contract_sha256": KERNEL_CHECKER_CONTRACT_SHA256,
    }:
        _fail("identity", "checker identity differs")
    if proof_contract != {
        "contract_id": PROOF_TERM_CONTRACT_ID,
        "contract_sha256": PROOF_TERM_CONTRACT_SHA256,
    }:
        _fail("identity", "proof-term contract identity differs")
    term = _decode_term_hex(item["proof_term_hex"])
    if term is None:
        expected = _expected_without_term(item)
    else:
        expected = check_proof_term(term)
    expected_object = _result_object(expected)
    if item != expected_object:
        _fail("result", "serialized checker result differs from independent recomputation")
    actual_digest = hashlib.sha256(_canonical_json_bytes(expected_object)).hexdigest()
    if digest != actual_digest:
        _fail("identity", f"result_sha256 mismatch: expected {actual_digest}, got {digest}")
    expected_bytes = checker_result_to_bytes(expected)
    if data != expected_bytes:
        _fail("canonical", "checker-result envelope bytes are not canonical")
    return expected


__all__ = [
    "CheckerResult",
    "CheckerResultValidationError",
    "DividesStatement",
    "KERNEL_CHECKER_CONTRACT_ID",
    "KERNEL_CHECKER_CONTRACT_SHA256",
    "KERNEL_CHECKER_ID",
    "KERNEL_CHECKER_RESULT_SCHEMA",
    "MAX_CHECK_STEPS",
    "MAX_DERIVED_INTEGER_BITS",
    "MAX_RESULT_INPUT_BYTES",
    "PolynomialIdentityStatement",
    "Statement",
    "SumIdentityStatement",
    "check_proof_term",
    "checker_result_sha256",
    "checker_result_to_bytes",
    "parse_checker_result",
    "validate_checker_result",
]
