from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tools" / "validate_reconstruction_adrs.py"
TOPICS = (
    "preserve-rebuild-boundary",
    "package-ownership",
    "migration-strategy",
    "compatibility-policy",
    "trust-terminology",
)


class ReconstructionAdrTests(unittest.TestCase):
    def run_validator(
        self, root: Path, index: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(VALIDATOR), "--root", str(root)]
        if index is not None:
            command.extend(("--index", str(index)))
        return subprocess.run(
            command, text=True, capture_output=True, encoding="utf-8"
        )

    def write_fixture(
        self,
        root: Path,
        *,
        bad_hash: bool = False,
        duplicate_topic: bool = False,
        unknown_field: bool = False,
    ) -> Path:
        directory = root / "docs" / "reconstruction" / "adrs"
        directory.mkdir(parents=True)
        records: list[tuple[str, str, str, str]] = []
        for number, topic in enumerate(TOPICS, 1):
            adr_id = f"MH-ADR-{number:04d}"
            title = f"Decision {number}"
            relative = f"docs/reconstruction/adrs/{number:04d}-decision.md"
            document = root / relative
            document.write_text(
                f"# {adr_id}: {title}\n\n**Status:** Accepted\n",
                encoding="utf-8",
            )
            digest = hashlib.sha256(document.read_bytes()).hexdigest()
            records.append((adr_id, title, relative, digest))
        if bad_hash:
            adr_id, title, relative, _ = records[-1]
            records[-1] = (adr_id, title, relative, "0" * 64)

        body = (
            "schema = 1\n"
            'programme = "fixture"\n'
            'authority = "accepted-reconstruction-decisions"\n'
            "append_only = true\n"
            'supersession_policy = "new-adr-required"\n'
            "required_topics = ["
            + ", ".join(f'"{topic}"' for topic in TOPICS)
            + "]\n"
        )
        for number, (adr_id, title, relative, digest) in enumerate(records):
            topic = TOPICS[0] if duplicate_topic and number == 1 else TOPICS[number]
            body += (
                "\n[[adrs]]\n"
                f'id = "{adr_id}"\n'
                f'title = "{title}"\n'
                f'path = "{relative}"\n'
                'status = "accepted"\n'
                'accepted_on = "2026-08-11"\n'
                f'topics = ["{topic}"]\n'
                f'sha256 = "{digest}"\n'
                "supersedes = []\n"
                + ("unexpected = true\n" if unknown_field and number == 0 else "")
            )
        index = directory / "INDEX.toml"
        index.write_text(body, encoding="utf-8")
        return index

    def test_repository_adr_index_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("5 accepted decisions", result.stdout)

    def test_accepted_adr_hash_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_validator(root, self.write_fixture(root, bad_hash=True))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_duplicate_topic_owner_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_validator(
                root, self.write_fixture(root, duplicate_topic=True)
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("owned by both", result.stderr)

    def test_unknown_index_field_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.run_validator(
                root, self.write_fixture(root, unknown_field=True)
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or unknown fields", result.stderr)


if __name__ == "__main__":
    unittest.main()
