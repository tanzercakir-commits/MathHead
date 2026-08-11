from __future__ import annotations

from pathlib import Path
import unittest
from unittest import mock

from tools import dev
from tools import validate_optional_dependencies as optional


ROOT = Path(__file__).resolve().parents[2]


class OptionalDependencyContractTests(unittest.TestCase):
    def test_repository_core_boundary_is_complete(self) -> None:
        sources, markers = optional.validate(ROOT, "core")
        self.assertGreater(sources, 100)
        self.assertEqual(markers, 10)

    def test_executable_alternatives_accept_either_packaging_name(self) -> None:
        profile = {"platforms": ["linux"], "python": [dev._python_version()],
                   "required_executables": ["nauty-geng|geng"]}
        with mock.patch.object(dev, "_platform_name", return_value="linux"):
            with mock.patch.object(dev.shutil, "which", side_effect=lambda name: "/bin/geng" if name == "geng" else None):
                self.assertEqual(dev._profile_support(profile), (True, "supported"))
            with mock.patch.object(dev.shutil, "which", side_effect=lambda name: "/bin/nauty-geng" if name == "nauty-geng" else None):
                self.assertEqual(dev._profile_support(profile), (True, "supported"))

    def test_missing_executable_alternatives_are_explicit(self) -> None:
        profile = {"platforms": ["linux"], "python": [dev._python_version()],
                   "required_executables": ["nauty-geng|geng"]}
        with mock.patch.object(dev, "_platform_name", return_value="linux"):
            with mock.patch.object(dev.shutil, "which", return_value=None):
                supported, reason = dev._profile_support(profile)
        self.assertFalse(supported)
        self.assertEqual(reason, "missing-system-executable:nauty-geng|geng")

    def test_solver_preflight_requires_python_and_system_capabilities(self) -> None:
        with mock.patch.object(optional, "_module_available", return_value=False):
            with self.assertRaisesRegex(optional.OptionalDependencyError, "pysat.solvers"):
                optional.validate(ROOT, "solver")
        with mock.patch.object(optional, "_module_available", return_value=True):
            with mock.patch.object(optional, "_which_any", return_value=None):
                with self.assertRaisesRegex(optional.OptionalDependencyError, "executable"):
                    optional.validate(ROOT, "solver")
        with mock.patch.object(optional, "_module_available", return_value=True):
            with mock.patch.object(optional, "_which_any", return_value="/usr/bin/nauty-geng"):
                sources, markers = optional.validate(ROOT, "solver")
        self.assertGreater(sources, 100)
        self.assertEqual(markers, 10)


if __name__ == "__main__":
    unittest.main()
