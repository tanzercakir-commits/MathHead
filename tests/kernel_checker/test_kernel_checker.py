from __future__ import annotations

import ast
import copy
import dataclasses
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import pickle
import sys
import unittest

from _legacy_fixture import load_legacy_kernel


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.checkers import (  # noqa: E402
    BezoutWitness,
    CRTEvidence,
    CheckerResult,
    CheckerResultValidationError,
    DividesStatement,
    KERNEL_CHECKER_CONTRACT_ID,
    KERNEL_CHECKER_CONTRACT_SHA256,
    MAX_RESIDUE_CLASSES,
    MAX_RESULT_INPUT_BYTES,
    PolynomialIdentityEvidence,
    PolynomialIdentityStatement,
    ProductStep,
    ResidueEvaluation,
    ResidueEvidence,
    SumInductionEvidence,
    SumIdentityStatement,
    check_proof_term,
    checker_result_sha256,
    checker_result_to_bytes,
    parse_checker_result,
    validate_checker_result,
)


Theorem = load_legacy_kernel(ROOT).Theorem
from mathhead.kernel.proof_terms import (  # noqa: E402
    ResidueTerm,
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


def _with_result_digest(value: dict[str, object]) -> bytes:
    result = value["result"]
    value["result_sha256"] = hashlib.sha256(_canonical(result)).hexdigest()
    return _canonical(value)


class KernelCheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.poly = (0, -1, 0, 1)

    def test_all_four_rules_issue_exact_typed_attestations(self) -> None:
        terms_and_types = (
            (residue(2, self.poly), DividesStatement),
            (crt((residue(2, self.poly), residue(3, self.poly))), DividesStatement),
            (
                sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
                SumIdentityStatement,
            ),
            (polynomial_identity((0, -1, 0, 1), self.poly), PolynomialIdentityStatement),
        )
        for term, statement_type in terms_and_types:
            result = check_proof_term(term)
            self.assertEqual(result.verdict, "verified")
            self.assertEqual(result.reason_code, "CHECKER_VALID")
            self.assertEqual(result.authority, "checker_attestation")
            self.assertTrue(result.exact)
            self.assertIs(type(result.statement), statement_type)
            self.assertIsNotNone(result.evidence)
            self.assertEqual(len(result.evidence_sha256 or ""), 64)
            self.assertEqual(parse_checker_result(checker_result_to_bytes(result)), result)

    def test_crt_derives_product_and_requires_one_polynomial(self) -> None:
        verified = check_proof_term(crt((residue(2, self.poly), residue(3, self.poly))))
        self.assertIs(type(verified.statement), DividesStatement)
        self.assertEqual(verified.statement.modulus, 6)
        self.assertEqual(verified.statement.polynomial, self.poly)

        mismatch = check_proof_term(crt((residue(2, self.poly), residue(3, (0,)))))
        self.assertEqual(
            (mismatch.verdict, mismatch.reason_code), ("invalid", "CRT_POLYNOMIAL_MISMATCH")
        )
        self.assertEqual(mismatch.authority, "none")
        self.assertIsNone(mismatch.statement)

    def test_crt_rejects_non_coprime_and_failed_premises(self) -> None:
        non_coprime = check_proof_term(crt((residue(2, (0, 4)), residue(4, (0, 4)))))
        self.assertEqual(non_coprime.reason_code, "CRT_NON_COPRIME")
        failed = check_proof_term(crt((residue(2, self.poly), residue(3, (1,)))))
        self.assertEqual(failed.reason_code, "CRT_PREMISE_INVALID")
        for result in (non_coprime, failed):
            self.assertEqual(result.verdict, "invalid")
            self.assertEqual(result.authority, "none")
            self.assertIsNone(result.statement)

    def test_false_residue_identity_and_sum_rules_do_not_promote(self) -> None:
        results = (
            (check_proof_term(residue(4, (1, 0, 1))), "RESIDUE_COUNTEREXAMPLE"),
            (check_proof_term(polynomial_identity((0, 1), (1, 1))), "POLYNOMIAL_MISMATCH"),
            (check_proof_term(sum_induction((0, 1), (1, 0, 1))), "SUM_BASE_MISMATCH"),
            (check_proof_term(sum_induction((0, 1), (0, 0, 1))), "SUM_STEP_MISMATCH"),
        )
        for result, reason in results:
            self.assertEqual((result.verdict, result.reason_code), ("invalid", reason))
            self.assertEqual(result.authority, "none")
            self.assertIsNone(result.statement)
            self.assertIsNone(result.evidence)
            self.assertIsNone(result.evidence_sha256)
            self.assertIsNotNone(result.proof_term_sha256)

    def test_deterministic_budget_refuses_before_large_residue_loop(self) -> None:
        term = residue(MAX_RESIDUE_CLASSES + 1, (0,))
        result = check_proof_term(term)
        self.assertEqual((result.verdict, result.reason_code), ("exhausted", "BUDGET_EXHAUSTED"))
        self.assertEqual(result.steps, 0)
        self.assertEqual(result.authority, "none")
        self.assertIsNone(result.statement)
        self.assertEqual(check_proof_term(term), result)

    def test_structurally_forged_and_unknown_objects_fail_without_authority(self) -> None:
        forged = object.__new__(ResidueTerm)
        object.__setattr__(forged, "modulus", True)
        object.__setattr__(forged, "polynomial", self.poly)
        invalid = check_proof_term(forged)
        unsupported = check_proof_term(object())
        self.assertEqual(invalid.reason_code, "TERM_INVALID")
        self.assertEqual(unsupported.reason_code, "UNSUPPORTED_TERM")
        for result in (invalid, unsupported):
            self.assertEqual(result.verdict, "invalid")
            self.assertEqual(result.authority, "none")
            self.assertIsNone(result.proof_term)
            self.assertIsNone(result.statement)
            self.assertIsNone(result.evidence)

    def test_legacy_theorem_cannot_cross_new_checker_boundary(self) -> None:
        forged = object.__new__(Theorem)
        object.__setattr__(forged, "kind", "Divides")
        object.__setattr__(forged, "payload", (2, self.poly))
        result = check_proof_term(forged)
        self.assertEqual((result.verdict, result.reason_code), ("invalid", "UNSUPPORTED_TERM"))
        self.assertEqual(result.authority, "none")

    def test_result_and_statement_constructors_pickle_and_subclasses_are_closed(self) -> None:
        for cls in (
            CheckerResult,
            DividesStatement,
            SumIdentityStatement,
            PolynomialIdentityStatement,
            ResidueEvaluation,
            ResidueEvidence,
            BezoutWitness,
            ProductStep,
            CRTEvidence,
            SumInductionEvidence,
            PolynomialIdentityEvidence,
        ):
            with self.assertRaises(PermissionError):
                cls()  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                type(f"Forged{cls.__name__}", (cls,), {})
        result = check_proof_term(residue(2, self.poly))
        with self.assertRaises(PermissionError):
            dataclasses.replace(result, authority="none")
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)

    def test_object_new_and_field_tampering_are_recomputed(self) -> None:
        empty = object.__new__(CheckerResult)
        with self.assertRaises(CheckerResultValidationError):
            validate_checker_result(empty)
        result = check_proof_term(residue(2, self.poly))
        object.__setattr__(result, "authority", "none")
        with self.assertRaisesRegex(CheckerResultValidationError, "evidence|recomputation"):
            validate_checker_result(result)

    def test_statement_injection_cannot_survive_result_validation(self) -> None:
        result = check_proof_term(residue(2, self.poly))
        forged = object.__new__(DividesStatement)
        object.__setattr__(forged, "modulus", 3)
        object.__setattr__(forged, "polynomial", self.poly)
        object.__setattr__(result, "statement", forged)
        with self.assertRaisesRegex(CheckerResultValidationError, "recomputation"):
            checker_result_to_bytes(result)

    def test_every_verdict_round_trips_canonically(self) -> None:
        results = (
            check_proof_term(residue(2, self.poly)),
            check_proof_term(residue(2, (1,))),
            check_proof_term(residue(MAX_RESIDUE_CLASSES + 1, (0,))),
            check_proof_term(object()),
        )
        for result in results:
            encoded = checker_result_to_bytes(result)
            self.assertEqual(parse_checker_result(encoded), result)
            self.assertEqual(checker_result_to_bytes(parse_checker_result(encoded)), encoded)
            self.assertEqual(len(checker_result_sha256(result)), 64)

    def test_parse_rejects_duplicate_unknown_missing_and_float_fields(self) -> None:
        encoded = checker_result_to_bytes(check_proof_term(residue(2, self.poly)))
        value = json.loads(encoded)
        mutations = (
            lambda item: item.update(extra=True),
            lambda item: item.pop("schema"),
            lambda item: item["result"].update(extra=True),
            lambda item: item["result"].update(steps=1.5),
        )
        for mutate in mutations:
            item = copy.deepcopy(value)
            mutate(item)
            with self.assertRaises(CheckerResultValidationError):
                parse_checker_result(_canonical(item))
        duplicate = encoded.replace(b'{"result":', b'{"result":null,"result":', 1)
        with self.assertRaisesRegex(CheckerResultValidationError, "duplicate"):
            parse_checker_result(duplicate)

    def test_parse_rejects_noncanonical_stale_and_substituted_results(self) -> None:
        encoded = checker_result_to_bytes(check_proof_term(residue(2, self.poly)))
        with self.assertRaisesRegex(CheckerResultValidationError, "canonical"):
            parse_checker_result(encoded[:-1])
        value = json.loads(encoded)
        value["result_sha256"] = "0" * 64
        with self.assertRaisesRegex(CheckerResultValidationError, "identity"):
            parse_checker_result(_canonical(value))
        value = json.loads(encoded)
        value["result"]["authority"] = "none"
        with self.assertRaisesRegex(CheckerResultValidationError, "recomputation"):
            parse_checker_result(_with_result_digest(value))

    def test_parse_rejects_contract_term_and_checker_identity_drift(self) -> None:
        encoded = checker_result_to_bytes(check_proof_term(residue(2, self.poly)))
        for path in ("checker", "proof_term_contract"):
            value = json.loads(encoded)
            value["result"][path]["contract_sha256"] = "0" * 64
            with self.assertRaisesRegex(CheckerResultValidationError, "identity"):
                parse_checker_result(_with_result_digest(value))
        value = json.loads(encoded)
        value["result"]["proof_term_hex"] = "00"
        with self.assertRaisesRegex(CheckerResultValidationError, "embedded proof term"):
            parse_checker_result(_with_result_digest(value))

    def test_result_input_type_encoding_and_byte_budget_fail_closed(self) -> None:
        for bad in ("{}\n", bytearray(b"{}\n"), memoryview(b"{}\n")):
            with self.assertRaises(CheckerResultValidationError):
                parse_checker_result(bad)  # type: ignore[arg-type]
        with self.assertRaisesRegex(CheckerResultValidationError, "encoding"):
            parse_checker_result(b"\xff\n")
        with self.assertRaisesRegex(CheckerResultValidationError, "budget"):
            parse_checker_result(b" " * (MAX_RESULT_INPUT_BYTES + 1))

    def test_contract_and_proof_term_identities_are_exact(self) -> None:
        result = check_proof_term(residue(2, self.poly))
        self.assertEqual(KERNEL_CHECKER_CONTRACT_ID, "MH-C-KERNEL-CHECKER-002")
        self.assertEqual(
            KERNEL_CHECKER_CONTRACT_SHA256,
            "1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e",
        )
        self.assertEqual(result.checker_contract_sha256, KERNEL_CHECKER_CONTRACT_SHA256)
        self.assertEqual(
            result.proof_term_contract_sha256,
            "20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac",
        )

    def test_schema_is_closed_and_accepts_all_canonical_verdicts(self) -> None:
        schema = json.loads(
            (ROOT / "docs/contracts/schemas/kernel-checker-result-v2.schema.json").read_text()
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["result"]["properties"]["steps"]["maximum"], 1_000_000
        )
        try:
            import jsonschema
        except ImportError:
            return
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        for result in (
            check_proof_term(residue(2, self.poly)),
            check_proof_term(residue(2, (1,))),
            check_proof_term(residue(MAX_RESIDUE_CLASSES + 1, (0,))),
            check_proof_term(object()),
        ):
            validator.validate(json.loads(checker_result_to_bytes(result)))

    def test_source_import_boundary_is_dependency_minimal(self) -> None:
        source = ROOT / "src/mathhead/kernel/checkers.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        roots.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertLessEqual(
            roots,
            {
                "__future__",
                "dataclasses",
                "fractions",
                "hashlib",
                "json",
                "math",
                "mathhead",
                "typing",
            },
        )
        self.assertFalse(
            roots
            & {
                "importlib",
                "mcp",
                "mpmath",
                "multiprocessing",
                "os",
                "pathlib",
                "pysat",
                "random",
                "shutil",
                "subprocess",
                "sympy",
                "sys",
                "time",
                "z3",
            }
        )


if __name__ == "__main__":
    unittest.main()
