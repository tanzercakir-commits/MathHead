from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "project_status.py"


class TaskAwareStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(
        self, *args: str, project_status_base: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        if project_status_base is not None:
            env["PROJECT_STATUS_BASE"] = project_status_base
        return subprocess.run(
            [sys.executable, str(TOOL), "--root", str(self.root), *args],
            text=True,
            capture_output=True,
            encoding="utf-8",
            env=env,
        )

    def write_fixture(
        self,
        guard_source: str = "raise SystemExit(0)\n",
        *,
        task_specific: bool = True,
        queue: str = "Now",
        timeout_seconds: int = 5,
    ) -> None:
        (self.root / "PLAN.md").write_text(
            "# Plan\n\n#### MH-002 - task-aware status\n", encoding="utf-8"
        )
        sections = {name: "" for name in ("Now", "Next", "Later", "Blocked")}
        sections[queue] = (
            "### MH-002 - task-aware status\n\n"
            "**Contracts:** `MH-C-STATUS-001`.\n\n"
            "**Done when:** validators pass.\n\n"
        )
        todo = "# TODO\n\n" + "".join(
            f"## {name}\n\n{sections[name]}" for name in sections
        )
        (self.root / "TODO.md").write_text(todo, encoding="utf-8")
        (self.root / "PROGRESS.md").write_text(
            "# Progress\n\n---\n\n## 2026-01-01 - old\n\nKept.\n",
            encoding="utf-8",
        )
        contracts = self.root / "contracts"
        contracts.mkdir()
        artifact = contracts / "status.md"
        artifact.write_text("accepted status contract\n", encoding="utf-8")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        (contracts / "manifest.toml").write_text(
            "schema = 1\n\n[[contracts]]\n"
            "id = \"MH-C-STATUS-001\"\n"
            "path = \"contracts/status.md\"\n"
            f"sha256 = \"{digest}\"\n"
            "state = \"accepted\"\n",
            encoding="utf-8",
        )
        (self.root / "guard.py").write_text(guard_source, encoding="utf-8")
        python = Path(sys.executable).as_posix()
        tasks = '["MH-002"]' if task_specific else "[]"
        (self.root / ".project-status.toml").write_text(
            "schema = 1\n"
            "tool_version = \"2.0.0\"\n"
            "plan = \"PLAN.md\"\n"
            "progress = \"PROGRESS.md\"\n"
            "todo = \"TODO.md\"\n"
            "contract_manifest = \"contracts/manifest.toml\"\n"
            "todo_mode = \"managed\"\n"
            "max_todo_items = 5\n\n"
            "[[checks]]\n"
            "name = \"guard\"\n"
            f"command = '\"{python}\" guard.py'\n"
            "profiles = [\"status\"]\n"
            f"tasks = {tasks}\n"
            f"timeout_seconds = {timeout_seconds}\n",
            encoding="utf-8",
        )

    def record_args(self, operation: str = "record-done") -> list[str]:
        return [
            operation,
            "--task",
            "MH-002",
            "--title",
            "status transition",
            "--changed",
            "Implemented the transition.",
            "--learned",
            "Negative evidence is binding.",
            "--profile",
            "status",
            "--evidence",
            "PLAN.md",
            "--limitations",
            "No known limitation in this fixture.",
            "--next",
            "Continue to the next task.",
            "--date",
            "2026-08-11",
        ]

    def assert_records_unchanged(
        self, before_todo: bytes, before_progress: bytes
    ) -> None:
        self.assertEqual((self.root / "TODO.md").read_bytes(), before_todo)
        self.assertEqual((self.root / "PROGRESS.md").read_bytes(), before_progress)

    def test_done_rejects_missing_evidence(self) -> None:
        self.write_fixture()
        before_todo = (self.root / "TODO.md").read_bytes()
        before_progress = (self.root / "PROGRESS.md").read_bytes()
        args = self.record_args()
        evidence_index = args.index("--evidence")
        del args[evidence_index : evidence_index + 2]

        result = self.run_tool(*args)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--evidence", result.stderr)
        self.assert_records_unchanged(before_todo, before_progress)

    def test_done_rejects_task_outside_now(self) -> None:
        self.write_fixture(queue="Next")

        result = self.run_tool(*self.record_args())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TODO Now", result.stderr)

    def test_done_rejects_missing_task_specific_check(self) -> None:
        self.write_fixture(task_specific=False)

        result = self.run_tool(*self.record_args())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task-specific validator", result.stderr)

    def test_done_rejects_contract_hash_drift(self) -> None:
        self.write_fixture()
        (self.root / "contracts" / "status.md").write_text(
            "silently changed\n", encoding="utf-8"
        )

        result = self.run_tool(*self.record_args())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stderr)

    def test_partial_records_proposed_contract_but_done_rejects_it(self) -> None:
        self.write_fixture()
        manifest = self.root / "contracts" / "manifest.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                'state = "accepted"', 'state = "proposed"'
            ),
            encoding="utf-8",
        )

        partial = self.run_tool(*self.record_args("record-partial"))
        done = self.run_tool(*self.record_args())

        self.assertEqual(partial.returncode, 0, partial.stderr)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("not accepted", done.stderr)

    def test_done_rejects_failed_skipped_and_inconclusive_validators(self) -> None:
        for code, expected in ((7, "failed"), (77, "skipped"), (78, "inconclusive")):
            with self.subTest(code=code):
                self.tearDown()
                self.setUp()
                self.write_fixture(f"raise SystemExit({code})\n")
                before_todo = (self.root / "TODO.md").read_bytes()
                before_progress = (self.root / "PROGRESS.md").read_bytes()

                result = self.run_tool(*self.record_args())

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
                self.assert_records_unchanged(before_todo, before_progress)

    def test_done_rejects_missing_validator_command(self) -> None:
        self.write_fixture()
        config = self.root / ".project-status.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                f'"{Path(sys.executable).as_posix()}" guard.py',
                "mathhead-command-that-does-not-exist",
            ),
            encoding="utf-8",
        )

        result = self.run_tool(*self.record_args())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stderr)

    def test_done_rejects_timed_out_validator(self) -> None:
        self.write_fixture("import time\ntime.sleep(2)\n", timeout_seconds=1)

        result = self.run_tool(*self.record_args())

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed-out", result.stderr)

    def test_partial_records_red_evidence_and_retains_todo(self) -> None:
        self.write_fixture("raise SystemExit(7)\n")
        before_todo = (self.root / "TODO.md").read_bytes()

        result = self.run_tool(*self.record_args("record-partial"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "TODO.md").read_bytes(), before_todo)
        progress = (self.root / "PROGRESS.md").read_text(encoding="utf-8")
        self.assertIn("MH-002 (`partial`)", progress)
        self.assertIn("guard=failed/exit-7/output-", progress)

    def test_exact_case_alias_is_rejected(self) -> None:
        self.write_fixture()
        config = self.root / ".project-status.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'plan = "PLAN.md"', 'plan = "plan.md"'
            ),
            encoding="utf-8",
        )

        result = self.run_tool("check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact-case mismatch", result.stderr)

    def test_historical_progress_edit_is_rejected(self) -> None:
        self.write_fixture()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "status@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Status Test"], cwd=self.root, check=True
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "baseline"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        progress = self.root / "PROGRESS.md"
        progress.write_text(
            progress.read_text(encoding="utf-8").replace("Kept.", "Changed."),
            encoding="utf-8",
        )

        result = self.run_tool("check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("historical bytes changed", result.stderr)

    def test_new_progress_block_preserves_committed_history(self) -> None:
        self.write_fixture()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "status@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Status Test"], cwd=self.root, check=True
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "baseline"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        result = self.run_tool(*self.record_args("record-partial"))

        self.assertEqual(result.returncode, 0, result.stderr)
        progress = (self.root / "PROGRESS.md").read_text(encoding="utf-8")
        self.assertTrue(progress.endswith("## 2026-01-01 - old\n\nKept.\n"))

    def test_zero_event_base_accepts_initial_progress_introduction(self) -> None:
        self.write_fixture()
        progress = self.root / "PROGRESS.md"
        progress_bytes = progress.read_bytes()
        progress.unlink()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "status@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Status Test"], cwd=self.root, check=True
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "baseline"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        progress.write_bytes(progress_bytes)
        subprocess.run(["git", "add", "PROGRESS.md"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "introduce progress"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        result = self.run_tool("check", project_status_base="0" * 40)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_zero_event_base_cannot_bypass_existing_progress_history(self) -> None:
        self.write_fixture()
        subprocess.run(["git", "init"], cwd=self.root, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "status@example.invalid"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Status Test"], cwd=self.root, check=True
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "baseline"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        progress = self.root / "PROGRESS.md"
        progress.write_text(
            progress.read_text(encoding="utf-8").replace("Kept.", "Changed."),
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "PROGRESS.md"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "rewrite history"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        result = self.run_tool("check", project_status_base="0" * 40)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("historical bytes changed", result.stderr)


if __name__ == "__main__":
    unittest.main()
