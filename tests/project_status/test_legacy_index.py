from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tools" / "validate_legacy_index.py"


class LegacyIndexTests(unittest.TestCase):
    def run_validator(
        self, root: Path, index: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATOR), "--root", str(root)]
        if index is not None:
            command.extend(("--index", str(index)))
        return subprocess.run(
            command, text=True, capture_output=True, encoding="utf-8"
        )

    def write_fixture(self, root: Path, *, duplicate: bool = False, bad_hash: bool = False) -> Path:
        docs = root / "docs"
        docs.mkdir()
        for name in ("PLAN.md", "TODO.md", "PROGRESS.md"):
            (docs / name).write_text(name + "\n", encoding="utf-8")
        legacy = root / "Plan.md"
        legacy.write_text("legacy\n", encoding="utf-8")
        digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
        if bad_hash:
            digest = "0" * 64
        entries = [
            ("docs/PLAN.md", "authoritative-plan", "current", False, ""),
            ("docs/TODO.md", "authoritative-todo", "current", False, ""),
            ("docs/PROGRESS.md", "authoritative-progress", "current", False, ""),
            ("Plan.md", "historical-plan", "historical", True, digest),
        ]
        if duplicate:
            entries.append(entries[-1])
        body = "schema = 1\nprogramme = \"test\"\n"
        for path, role, status, immutable, sha256 in entries:
            body += (
                "\n[[records]]\n"
                f"path = \"{path}\"\n"
                f"role = \"{role}\"\n"
                f"claim_status = \"{status}\"\n"
                "phase = \"P0\"\n"
                f"immutable = {str(immutable).lower()}\n"
                + (f"sha256 = \"{sha256}\"\n" if immutable else "")
                + "note = \"fixture\"\n"
            )
        index = root / "index.toml"
        index.write_text(body, encoding="utf-8")
        return index

    def test_repository_index_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("14 records", result.stdout)

    def test_duplicate_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_validator(root, self.write_fixture(root, duplicate=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", result.stderr)

    def test_immutable_hash_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_validator(root, self.write_fixture(root, bad_hash=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)


if __name__ == "__main__":
    unittest.main()
