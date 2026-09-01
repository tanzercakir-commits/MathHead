from __future__ import annotations

import ast
from fractions import Fraction
from pathlib import Path
import sys
import unittest

from _legacy_fixture import load_legacy_kernel


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.checkers import check_proof_term  # noqa: E402
from mathhead.legacy_kernel_adapter import (  # noqa: E402
    LegacyProofAdapterError,
    adapt_legacy_proof_term,
)


LEGACY = load_legacy_kernel(ROOT)
CRT = LEGACY.CRT
Identity = LEGACY.Identity
KernelError = LEGACY.KernelError
Residue = LEGACY.Residue
SumInduction = LEGACY.SumInduction
Theorem = LEGACY.Theorem
legacy_check = LEGACY.check


class LegacyKernelAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.polynomial = (0, -1, 0, 1)

    def test_all_legacy_rules_preserve_claims_without_preserving_authority(self) -> None:
        terms = (
            Residue(2, self.polynomial),
            CRT((Residue(2, self.polynomial), Residue(3, self.polynomial))),
            SumInduction((0, 1), (0, Fraction(1, 2), Fraction(1, 2))),
            Identity(self.polynomial, self.polynomial),
        )
        for legacy_term in terms:
            old_statement = legacy_check(legacy_term)
            candidate = adapt_legacy_proof_term(legacy_term)
            self.assertFalse(hasattr(candidate, "authority"))
            checked = check_proof_term(candidate)
            self.assertEqual(checked.verdict, "verified")
            self.assertEqual(checked.authority, "checker_attestation")
            if old_statement.kind == "Divides":
                self.assertEqual(
                    (checked.statement.modulus, checked.statement.polynomial),
                    old_statement.payload,
                )
            elif old_statement.kind == "SumIdentity":
                self.assertEqual(
                    (checked.statement.summand, checked.statement.closed_form),
                    old_statement.payload,
                )
            else:
                self.assertEqual(
                    (checked.statement.lhs, checked.statement.rhs),
                    old_statement.payload,
                )

    def test_false_legacy_claims_remain_false_after_migration(self) -> None:
        cases = (
            Residue(2, (1,)),
            SumInduction((0, 1), (0, 0, 1)),
            Identity((0, 1), (1, 1)),
        )
        for legacy_term in cases:
            with self.assertRaises(KernelError):
                legacy_check(legacy_term)
            checked = check_proof_term(adapt_legacy_proof_term(legacy_term))
            self.assertEqual(checked.verdict, "invalid")
            self.assertEqual(checked.authority, "none")

    def test_legacy_theorem_and_unknown_inputs_cannot_be_promoted(self) -> None:
        forged = object.__new__(Theorem)
        object.__setattr__(forged, "kind", "Divides")
        object.__setattr__(forged, "payload", (2, self.polynomial))
        with self.assertRaisesRegex(LegacyProofAdapterError, "not replayable proof evidence"):
            adapt_legacy_proof_term(forged)
        with self.assertRaisesRegex(LegacyProofAdapterError, "unsupported"):
            adapt_legacy_proof_term(object())

    def test_malformed_cycles_and_new_terms_fail_closed(self) -> None:
        cyclic = CRT(())
        object.__setattr__(cyclic, "parts", (cyclic,))
        with self.assertRaisesRegex(LegacyProofAdapterError, "cycle"):
            adapt_legacy_proof_term(cyclic)

        malformed = object.__new__(Residue)
        with self.assertRaisesRegex(LegacyProofAdapterError, "missing fields"):
            adapt_legacy_proof_term(malformed)

        from mathhead.kernel.proof_terms import residue

        with self.assertRaisesRegex(LegacyProofAdapterError, "unsupported"):
            adapt_legacy_proof_term(residue(2, self.polynomial))

    def test_adapter_source_cannot_issue_or_import_checker_authority(self) -> None:
        source = ROOT / "src/mathhead/legacy_kernel_adapter.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        self.assertNotIn("mathhead.kernel.checkers", imported_modules)
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertFalse({"CheckerResult", "check_proof_term"} & names)


if __name__ == "__main__":
    unittest.main()
