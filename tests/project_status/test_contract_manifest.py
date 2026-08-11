from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tools" / "validate_contract_manifest.py"


class ContractManifestTests(unittest.TestCase):
    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--root", str(root)],
            text=True,
            capture_output=True,
            encoding="utf-8",
        )

    def write_fixture(self, root: Path) -> tuple[Path, Path]:
        contracts = root / "docs" / "contracts"
        proposed = contracts / "proposed"
        proposed.mkdir(parents=True)
        accepted_path = contracts / "accepted.md"
        accepted_path.write_text("accepted\n", encoding="utf-8")
        proposed_path = proposed / "proposal.json"
        proposal = {
            "schema": "mathhead.function-contract.v1",
            "contract_id": "MH-C-PROPOSED-001",
            "target": "example:main",
            "signature": "main() -> int",
            "requires": ["input is valid"],
            "ensures": ["result is explicit"],
            "raises": ["no expected exception crosses the boundary"],
            "effects": {"filesystem": "none"},
            "determinism": {"output": "stable"},
            "budget": {"seconds": 1},
            "epistemics": {"passed": "all checks pass"},
            "invariants": ["fail closed"],
            "validators": ["python validator.py"],
            "supersedes": None,
        }
        proposed_path.write_text(
            json.dumps(proposal, indent=2) + "\n", encoding="utf-8"
        )
        accepted_hash = hashlib.sha256(accepted_path.read_bytes()).hexdigest()
        proposed_hash = hashlib.sha256(proposed_path.read_bytes()).hexdigest()
        (contracts / "manifest.toml").write_text(
            "schema = 1\n\n"
            "[[contracts]]\n"
            "id = \"MH-C-ACCEPTED-001\"\n"
            "path = \"docs/contracts/accepted.md\"\n"
            f"sha256 = \"{accepted_hash}\"\n"
            "state = \"accepted\"\n\n"
            "[[contracts]]\n"
            "id = \"MH-C-PROPOSED-001\"\n"
            "path = \"docs/contracts/proposed/proposal.json\"\n"
            f"sha256 = \"{proposed_hash}\"\n"
            "state = \"proposed\"\n",
            encoding="utf-8",
        )
        (root / "docs" / "TODO.md").write_text(
            "`MH-C-ACCEPTED-001` and `MH-C-PROPOSED-001`\n", encoding="utf-8"
        )
        return accepted_path, proposed_path

    def test_repository_manifest_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3 contracts", result.stdout)

    def test_hash_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            accepted, _ = self.write_fixture(root)
            accepted.write_text("changed\n", encoding="utf-8")
            result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_unknown_proposal_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, proposed = self.write_fixture(root)
            data = json.loads(proposed.read_text(encoding="utf-8"))
            data["invented"] = True
            proposed.write_text(json.dumps(data) + "\n", encoding="utf-8")
            manifest = root / "docs" / "contracts" / "manifest.toml"
            text = manifest.read_text(encoding="utf-8")
            old_hash = re.search(
                r'sha256 = "([0-9a-f]{64})"\nstate = "proposed"', text
            )
            self.assertIsNotNone(old_hash)
            digest = hashlib.sha256(proposed.read_bytes()).hexdigest()
            manifest.write_text(
                text.replace(old_hash.group(1), digest), encoding="utf-8"
            )
            result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown=['invented']", result.stderr)

    def test_unregistered_todo_contract_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_fixture(root)
            (root / "docs" / "TODO.md").write_text(
                "`MH-C-MISSING-001`\n", encoding="utf-8"
            )
            result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("absent from manifest", result.stderr)


if __name__ == "__main__":
    unittest.main()
