from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ATTRIBUTES = ROOT / ".gitattributes"
HOOK = ROOT / ".githooks" / "pre-commit"
WORKFLOW = ROOT / ".github" / "workflows" / "project-status.yml"


class StatusIntegrationTests(unittest.TestCase):
    def make_hook_fixture(self, staged_path: str) -> Path:
        self.assertIsNotNone(shutil.which("git"), "git executable is required")
        self.assertIsNotNone(shutil.which("sh"), "POSIX sh is required by the hook")
        root = Path(self.temporary.name)
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
        (root / ".project-status.toml").write_text(
            'progress = "PROGRESS.md"\n', encoding="utf-8"
        )
        (root / "PROGRESS.md").write_text("progress\n", encoding="utf-8")
        (root / "source.py").write_text("source\n", encoding="utf-8")
        tools = root / "tools"
        tools.mkdir()
        (tools / "project_status.py").write_text(
            "raise SystemExit(9)\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", staged_path], cwd=root, check=True)
        return root

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_substantive_change_cannot_bypass_failing_status_tool(self) -> None:
        root = self.make_hook_fixture("source.py")

        result = subprocess.run(
            ["sh", str(HOOK)], cwd=root, text=True, capture_output=True
        )

        self.assertEqual(result.returncode, 9, result.stderr)

    def test_progress_only_record_does_not_recurse_into_status_tool(self) -> None:
        root = self.make_hook_fixture("PROGRESS.md")

        result = subprocess.run(
            ["sh", str(HOOK)], cwd=root, text=True, capture_output=True
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_workflow_is_cross_platform_and_not_product_health(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("ubuntu-latest", text)
        self.assertIn("windows-latest", text)
        self.assertIn("PROJECT_STATUS_BASE", text)
        self.assertIn("not product health", text)
        self.assertIn("fetch-depth: 0", text)

    def test_repository_text_evidence_is_lf_on_every_platform(self) -> None:
        text = ATTRIBUTES.read_text(encoding="utf-8")
        self.assertIn("* text=auto eol=lf", text)
        self.assertIn("*.md text eol=lf whitespace=-trailing-space", text)


if __name__ == "__main__":
    unittest.main()
