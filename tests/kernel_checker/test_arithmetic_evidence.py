from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.checkers import (  # noqa: E402
    CRTEvidence,
    CheckerResultValidationError,
    PolynomialIdentityEvidence,
    ResidueEvidence,
    SumInductionEvidence,
    check_proof_term,
    checker_result_to_bytes,
    parse_checker_result,
    validate_checker_result,
)
from mathhead.kernel.proof_terms import (  # noqa: E402
    crt,
    polynomial_identity,
    residue,
    sum_induction,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _rehash(value: dict[str, object]) -> bytes:
    result = value["result"]
    assert isinstance(result, dict)
    evidence = result["evidence"]
    if evidence is not None:
        result["evidence_sha256"] = hashlib.sha256(_canonical(evidence)).hexdigest()
    value["result_sha256"] = hashlib.sha256(_canonical(result)).hexdigest()
    return _canonical(value)


class ArithmeticEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.polynomial = (0, -1, 0, 1)

    def test_residue_evidence_binds_every_exact_division(self) -> None:
        result = check_proof_term(residue(6, self.polynomial))
        self.assertIs(type(result.evidence), ResidueEvidence)
        evidence = result.evidence
        assert isinstance(evidence, ResidueEvidence)
        self.assertEqual(evidence.modulus, 6)
        self.assertEqual(evidence.polynomial, self.polynomial)
        self.assertEqual(
            tuple((row.residue, row.value, row.quotient, row.remainder) for row in evidence.evaluations),
            (
                (0, 0, 0, 0),
                (1, 0, 0, 0),
                (2, 6, 1, 0),
                (3, 24, 4, 0),
                (4, 60, 10, 0),
                (5, 120, 20, 0),
            ),
        )

    def test_crt_evidence_binds_premises_bezout_and_product(self) -> None:
        result = check_proof_term(
            crt((residue(2, self.polynomial), residue(3, self.polynomial)))
        )
        self.assertIs(type(result.evidence), CRTEvidence)
        evidence = result.evidence
        assert isinstance(evidence, CRTEvidence)
        self.assertEqual(tuple(type(item) for item in evidence.premises), (ResidueEvidence,) * 2)
        witness = evidence.bezout_witnesses[0]
        self.assertEqual(witness.gcd, 1)
        self.assertEqual(
            witness.left_coefficient * witness.left_modulus
            + witness.right_coefficient * witness.right_modulus,
            1,
        )
        self.assertEqual(
            tuple((item.prior_product, item.factor, item.product) for item in evidence.product_steps),
            ((1, 2, 2), (2, 3, 6)),
        )
        self.assertEqual((evidence.modulus, evidence.polynomial), (6, self.polynomial))

    def test_sum_evidence_exposes_base_shift_and_both_differences(self) -> None:
        result = check_proof_term(
            sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2)))
        )
        self.assertIs(type(result.evidence), SumInductionEvidence)
        evidence = result.evidence
        assert isinstance(evidence, SumInductionEvidence)
        self.assertEqual(evidence.summand_at_one, 1)
        self.assertEqual(evidence.closed_form_at_one, 1)
        self.assertEqual(evidence.shifted_closed_form, (0, Fraction(-1, 2), Fraction(1, 2)))
        self.assertEqual(evidence.first_difference, (0, 1))
        self.assertEqual(evidence.step_difference, (0,))

    def test_polynomial_identity_exposes_normalized_zero_difference(self) -> None:
        rational = tuple(Fraction(value) for value in self.polynomial)
        result = check_proof_term(polynomial_identity(rational, rational))
        self.assertIs(type(result.evidence), PolynomialIdentityEvidence)
        evidence = result.evidence
        assert isinstance(evidence, PolynomialIdentityEvidence)
        self.assertEqual((evidence.lhs, evidence.rhs), (rational, rational))
        self.assertEqual(evidence.difference, (Fraction(0),))

    def test_no_failed_or_exhausted_result_retains_partial_evidence(self) -> None:
        oversized_coefficient = 11 * ((1 << 4092) - 1)
        polynomial = (0,) * 4095 + (oversized_coefficient,)
        results = (
            check_proof_term(residue(2, (1,))),
            check_proof_term(residue(11, polynomial)),
            check_proof_term(object()),
        )
        self.assertEqual(tuple(item.verdict for item in results), ("invalid", "exhausted", "invalid"))
        for result in results:
            self.assertEqual(result.authority, "none")
            self.assertIsNone(result.statement)
            self.assertIsNone(result.evidence)
            self.assertIsNone(result.evidence_sha256)

    def test_in_memory_row_tamper_and_wrong_variant_fail_recomputation(self) -> None:
        result = check_proof_term(residue(3, self.polynomial))
        evidence = result.evidence
        assert isinstance(evidence, ResidueEvidence)
        object.__setattr__(evidence.evaluations[2], "quotient", 999)
        with self.assertRaisesRegex(CheckerResultValidationError, "recomputation"):
            validate_checker_result(result)

        result = check_proof_term(residue(3, self.polynomial))
        other = check_proof_term(polynomial_identity(self.polynomial, self.polynomial))
        object.__setattr__(result, "evidence", other.evidence)
        with self.assertRaisesRegex(CheckerResultValidationError, "recomputation"):
            validate_checker_result(result)

    def test_missing_and_forged_evidence_fail_closed(self) -> None:
        result = check_proof_term(residue(2, self.polynomial))
        object.__setattr__(result, "evidence", None)
        object.__setattr__(result, "evidence_sha256", None)
        with self.assertRaisesRegex(CheckerResultValidationError, "lacks complete"):
            validate_checker_result(result)

        result = check_proof_term(residue(2, self.polynomial))
        forged = object.__new__(ResidueEvidence)
        object.__setattr__(result, "evidence", forged)
        with self.assertRaises(CheckerResultValidationError):
            validate_checker_result(result)

    def test_serialized_evidence_tampering_fails_even_after_hash_repair(self) -> None:
        encoded = checker_result_to_bytes(check_proof_term(residue(3, self.polynomial)))
        base = json.loads(encoded)
        mutations = (
            lambda evidence: evidence["evaluations"][2].update(quotient=999),
            lambda evidence: evidence["evaluations"].reverse(),
            lambda evidence: evidence["evaluations"].pop(),
            lambda evidence: evidence["evaluations"].append(
                copy.deepcopy(evidence["evaluations"][-1])
            ),
            lambda evidence: evidence.update(extra="producer-asserted"),
        )
        for mutate in mutations:
            value = copy.deepcopy(base)
            evidence = value["result"]["evidence"]
            mutate(evidence)
            with self.assertRaisesRegex(CheckerResultValidationError, "recomputation"):
                parse_checker_result(_rehash(value))

    def test_evidence_identity_is_complete_and_deterministic(self) -> None:
        first = check_proof_term(residue(6, self.polynomial))
        second = check_proof_term(residue(6, self.polynomial))
        self.assertEqual(first, second)
        envelope = json.loads(checker_result_to_bytes(first))
        evidence = envelope["result"]["evidence"]
        self.assertEqual(
            envelope["result"]["evidence_sha256"],
            hashlib.sha256(_canonical(evidence)).hexdigest(),
        )

    def test_v1_result_schema_is_explicitly_refused(self) -> None:
        value = json.loads(checker_result_to_bytes(check_proof_term(residue(2, self.polynomial))))
        value["schema"] = "mathhead.kernel-checker-result.v1"
        with self.assertRaisesRegex(CheckerResultValidationError, "unsupported checker-result schema"):
            parse_checker_result(_canonical(value))


if __name__ == "__main__":
    unittest.main()
