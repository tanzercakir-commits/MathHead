from __future__ import annotations

import inspect
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# Import this compatibility leaf without executing discovery's optional,
# heavyweight package facade. The full discovery profile exercises that facade.
import mathhead as _mathhead  # noqa: E402

discovery_package = types.ModuleType("mathhead.discovery")
discovery_package.__path__ = [str(SRC / "mathhead/discovery")]
sys.modules.setdefault("mathhead.discovery", discovery_package)
_mathhead.discovery = discovery_package

from mathhead.discovery.lean_export import (  # noqa: E402
    LeanExport,
    _lean_poly,
    export_divides,
    export_identity,
    export_kernel_theorems,
)


class LegacyLeanAdapterTests(unittest.TestCase):
    """Keep the historical writer honest while authority lives in proof_assistant."""

    def test_polynomial_rendering_is_compatible(self) -> None:
        self.assertEqual(_lean_poly((0, -1, 0, 1)), "(-n) + n^3")
        self.assertEqual(_lean_poly((0, 2, 3, 1)), "(2) * n + (3) * n^2 + n^3")

    def test_divides_export_comes_from_the_canonical_residue_exporter(self) -> None:
        source = export_divides("legacy_t1", 6, (0, -1, 0, 1))
        self.assertIn("theorem legacy_t1", source)
        self.assertIn("∀ n : ℤ, (6 : ℤ) ∣", source)
        self.assertIn("∀ x : ZMod 6", source)
        self.assertIn("by decide", source)
        self.assertIn("ZMod.intCast_zmod_eq_zero_iff_dvd", source)

    def test_identity_export_requires_a_canonical_checker_result(self) -> None:
        source = export_identity("legacy_t2", "n^2 - 1", "(n - 1) * (n + 1)")
        self.assertTrue(source.strip().endswith("by intro n; ring"))
        with self.assertRaises(ValueError):
            export_identity("false_identity", "n", "n + 1")

    def test_legacy_text_cannot_inject_names_or_expression_comments(self) -> None:
        for name in ("bad name", "bad\naxiom injected", "theorem", "λ"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                export_identity(name, "n", "n")
        source = export_identity("safe_name", "n # ignored Python comment", "n")
        self.assertNotIn("#", source)
        self.assertEqual(source.count("theorem safe_name"), 1)

    def test_file_writer_is_explicitly_non_authoritative(self) -> None:
        result = LeanExport("not-written.lean", 0)
        self.assertEqual(result.status, "export_written_pending_external_check")
        self.assertIn("No theorem is claimed Lean-verified", result.note)
        source = inspect.getsource(export_kernel_theorems)
        self.assertIn("build_lean_export", source)
        self.assertNotIn("verify_with_lean", source)
        self.assertNotIn("externally_verified", source)


if __name__ == "__main__":
    unittest.main()
