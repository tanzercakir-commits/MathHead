from __future__ import annotations

import ast
import copy
import dataclasses
from fractions import Fraction
import json
from pathlib import Path
import pickle
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.proof_terms import (  # noqa: E402
    CRTTerm,
    MAX_COEFFICIENTS,
    MAX_CRT_PARTS,
    MAX_DEPTH,
    MAX_INPUT_BYTES,
    MAX_INTEGER_BITS,
    PolynomialIdentityTerm,
    ProofTermValidationError,
    ResidueTerm,
    SumInductionTerm,
    crt,
    parse_proof_term,
    polynomial_identity,
    proof_term_sha256,
    proof_term_to_bytes,
    residue,
    sum_induction,
    validate_proof_term,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


class ProofTermTests(unittest.TestCase):
    def setUp(self) -> None:
        self.poly = (0, -1, 0, 1)
        self.leaf = residue(2, self.poly)

    def test_all_four_rules_round_trip_canonically(self) -> None:
        terms = (
            self.leaf,
            crt((residue(3, self.poly), self.leaf)),
            sum_induction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
            polynomial_identity((0, -1, 0, 1), (0, -1, 0, 1, 0)),
        )
        self.assertEqual(
            [type(term) for term in terms],
            [ResidueTerm, CRTTerm, SumInductionTerm, PolynomialIdentityTerm],
        )
        for term in terms:
            encoded = proof_term_to_bytes(term)
            self.assertEqual(parse_proof_term(encoded), term)
            self.assertEqual(proof_term_to_bytes(parse_proof_term(encoded)), encoded)
            self.assertEqual(len(proof_term_sha256(term)), 64)

    def test_crt_parts_have_one_canonical_order(self) -> None:
        left = crt((residue(3, self.poly), residue(2, self.poly)))
        right = crt((residue(2, self.poly), residue(3, self.poly)))
        self.assertEqual(left, right)
        self.assertEqual(proof_term_to_bytes(left), proof_term_to_bytes(right))

    def test_polynomials_are_exact_normalized_and_deeply_immutable(self) -> None:
        source = [0, -1, 0, 1, 0]
        term = residue(2, source)
        source[0] = 99
        self.assertEqual(term.polynomial, self.poly)
        summed = sum_induction([0, 1], [0, Fraction(2, 4), Fraction(1, 2), 0])
        self.assertEqual(summed.closed_form, (Fraction(0), Fraction(1, 2), Fraction(1, 2)))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            term.modulus = 3  # type: ignore[misc]

    def test_direct_constructors_are_closed(self) -> None:
        for cls in (ResidueTerm, CRTTerm, SumInductionTerm, PolynomialIdentityTerm):
            with self.assertRaises(PermissionError):
                cls()  # type: ignore[call-arg]

    def test_replace_pickle_and_subclass_paths_cannot_forge(self) -> None:
        with self.assertRaises(PermissionError):
            dataclasses.replace(self.leaf, modulus=3)
        with self.assertRaises(TypeError):
            pickle.dumps(self.leaf)
        self.assertIs(copy.copy(self.leaf), self.leaf)
        self.assertIs(copy.deepcopy(self.leaf), self.leaf)
        with self.assertRaises(TypeError):

            class ForgedResidue(ResidueTerm):
                pass

    def test_object_new_bypass_is_revalidated_and_fails_closed(self) -> None:
        empty = object.__new__(ResidueTerm)
        with self.assertRaises(ProofTermValidationError):
            validate_proof_term(empty)
        forged = object.__new__(ResidueTerm)
        object.__setattr__(forged, "modulus", True)
        object.__setattr__(forged, "polynomial", self.poly)
        with self.assertRaises(ProofTermValidationError):
            proof_term_to_bytes(forged)

    def test_forged_cycle_fails_closed(self) -> None:
        forged = object.__new__(CRTTerm)
        object.__setattr__(forged, "parts", (forged,))
        with self.assertRaisesRegex(ProofTermValidationError, "cycle"):
            validate_proof_term(forged)

    def test_unknown_duplicate_and_missing_json_fields_fail_closed(self) -> None:
        valid = json.loads(proof_term_to_bytes(self.leaf))
        for mutate in (
            lambda item: item.update(extra=True),
            lambda item: item.pop("schema"),
            lambda item: item["term"].update(rule="future_rule"),
            lambda item: item["term"].update(extra=True),
        ):
            item = copy.deepcopy(valid)
            mutate(item)
            with self.assertRaises(ProofTermValidationError):
                parse_proof_term(_canonical(item))
        duplicate = proof_term_to_bytes(self.leaf).replace(
            b'{"schema":', b'{"schema":"mathhead.proof-term.v1","schema":', 1
        )
        with self.assertRaisesRegex(ProofTermValidationError, "duplicate"):
            parse_proof_term(duplicate)

    def test_noncanonical_bytes_and_stale_identity_fail_closed(self) -> None:
        encoded = proof_term_to_bytes(self.leaf)
        with self.assertRaisesRegex(ProofTermValidationError, "canonical"):
            parse_proof_term(encoded[:-1])
        with self.assertRaisesRegex(ProofTermValidationError, "canonical"):
            parse_proof_term(encoded.replace(b'":', b'": ', 1))
        item = json.loads(encoded)
        item["term_sha256"] = "0" * 64
        with self.assertRaisesRegex(ProofTermValidationError, "identity"):
            parse_proof_term(_canonical(item))

    def test_input_type_encoding_float_and_root_shape_fail_closed(self) -> None:
        for bad in ("{}\n", bytearray(b"{}\n"), memoryview(b"{}\n")):
            with self.assertRaises(ProofTermValidationError):
                parse_proof_term(bad)  # type: ignore[arg-type]
        for bad in (b"\xff\n", b"NaN\n", b"1.5\n", b"[]\n"):
            with self.assertRaises(ProofTermValidationError):
                parse_proof_term(bad)

    def test_strict_integer_and_polynomial_boundaries(self) -> None:
        for modulus in (True, 0, -1, "2", Fraction(2, 1)):
            with self.assertRaises(ProofTermValidationError):
                residue(modulus, self.poly)  # type: ignore[arg-type]
        for polynomial in ((), (True,), (1.0,), ("1",)):
            with self.assertRaises(ProofTermValidationError):
                residue(2, polynomial)  # type: ignore[arg-type]
        with self.assertRaises(ProofTermValidationError):
            residue(1 << MAX_INTEGER_BITS, (0,))
        with self.assertRaises(ProofTermValidationError):
            residue(2, (0,) * (MAX_COEFFICIENTS + 1))

    def test_rational_boundaries_are_exact(self) -> None:
        for bad in ((0.5,), (True,), ("1/2",)):
            with self.assertRaises(ProofTermValidationError):
                sum_induction(bad, (0,))  # type: ignore[arg-type]
        huge = Fraction(1 << MAX_INTEGER_BITS, 1)
        with self.assertRaises(ProofTermValidationError):
            sum_induction((huge,), (0,))

    def test_crt_size_depth_and_type_budgets(self) -> None:
        with self.assertRaises(ProofTermValidationError):
            crt(())
        with self.assertRaises(ProofTermValidationError):
            crt((self.leaf,) * (MAX_CRT_PARTS + 1))
        with self.assertRaises(ProofTermValidationError):
            crt((self.leaf, object()))  # type: ignore[arg-type]
        nested = self.leaf
        for _ in range(MAX_DEPTH - 1):
            nested = crt((nested,))
        with self.assertRaises(ProofTermValidationError):
            crt((nested,))

    def test_input_byte_budget_precedes_json_work(self) -> None:
        with self.assertRaisesRegex(ProofTermValidationError, "budget"):
            parse_proof_term(b" " * (MAX_INPUT_BYTES + 1))

    def test_values_have_stable_equality_hash_and_no_authority_field(self) -> None:
        same = residue(2, self.poly)
        self.assertEqual(self.leaf, same)
        self.assertEqual(hash(self.leaf), hash(same))
        self.assertFalse(hasattr(self.leaf, "authority"))
        self.assertFalse(hasattr(self.leaf, "verified"))

    def test_error_taxonomy_is_stable(self) -> None:
        try:
            residue(True, self.poly)  # type: ignore[arg-type]
        except ProofTermValidationError as exc:
            self.assertEqual(exc.kind, "term")
            self.assertIn("boolean", str(exc))
        else:
            self.fail("invalid value unexpectedly accepted")

    def test_schema_is_closed_and_standard_valid(self) -> None:
        schema = json.loads((ROOT / "docs/contracts/schemas/proof-term-v1.schema.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(len(schema["$defs"]["term"]["oneOf"]), 4)
        try:
            import jsonschema
        except ImportError:
            return
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(json.loads(proof_term_to_bytes(self.leaf)))

    def test_source_import_boundary_is_dependency_minimal(self) -> None:
        source = ROOT / "src/mathhead/kernel/proof_terms.py"
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
            {"__future__", "dataclasses", "fractions", "hashlib", "json", "typing"},
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
