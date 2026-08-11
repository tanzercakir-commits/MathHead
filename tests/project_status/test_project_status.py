#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Black-box contract tests for the vendored project-status CLI."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "project_status.py"


class ProjectStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(self, *args: str, tool: Path = TOOL) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(tool), "--root", str(self.root), *args],
            text=True,
            capture_output=True,
            encoding="utf-8",
        )

    def write_records(self, todo: str | None = None, progress: str | None = None) -> None:
        (self.root / "PLAN.md").write_text(
            "# Plan\n\n#### MH-001 - work\n", encoding="utf-8"
        )
        (self.root / "TODO.md").write_text(
            todo
            or (
                "# TODO\n\n## Now\n\n### MH-001 - work\n\n"
                "**Contracts:** `MH-C-TEST-001`.\n\n"
                "## Next\n\n## Later\n\n## Blocked\n"
            ),
            encoding="utf-8",
        )
        (self.root / "PROGRESS.md").write_text(
            progress or "# Progress\n\n---\n\n## 2026-01-01 - old\n\nKept.\n",
            encoding="utf-8",
        )

    def write_config(self, max_items: int = 3, checks: list[tuple[str, str]] | None = None) -> None:
        import hashlib

        contracts = self.root / "contracts"
        contracts.mkdir(exist_ok=True)
        artifact = contracts / "test.md"
        artifact.write_text("accepted test contract\n", encoding="utf-8")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        (contracts / "manifest.toml").write_text(
            "schema = 1\n\n[[contracts]]\n"
            "id = \"MH-C-TEST-001\"\n"
            "path = \"contracts/test.md\"\n"
            f"sha256 = \"{digest}\"\n"
            "state = \"accepted\"\n",
            encoding="utf-8",
        )
        if checks is None:
            (self.root / "status_pass.py").write_text(
                "raise SystemExit(0)\n", encoding="utf-8"
            )
            python = Path(sys.executable).as_posix()
            checks = [("status-pass", f'"{python}" status_pass.py')]
        body = (
            "schema = 1\n"
            "tool_version = \"2.0.0\"\n"
            "plan = \"PLAN.md\"\n"
            "progress = \"PROGRESS.md\"\n"
            "todo = \"TODO.md\"\n"
            "contract_manifest = \"contracts/manifest.toml\"\n"
            "todo_mode = \"managed\"\n"
            f"max_todo_items = {max_items}\n"
        )
        for name, command in checks:
            body += (
                f"\n[[checks]]\nname = \"{name}\"\ncommand = '{command}'\n"
                "profiles = [\"status\"]\n"
                "tasks = [\"MH-001\"]\n"
                "timeout_seconds = 10\n"
            )
        (self.root / ".project-status.toml").write_text(body, encoding="utf-8")

    def test_adopt_dry_run_is_read_only_and_infers_nested_records(self) -> None:
        docs = self.root / "docs"
        docs.mkdir()
        for name in ("PLAN.md", "PROGRESS.md", "TODO.md"):
            (docs / name).write_text(name, encoding="utf-8")
        before = {path.relative_to(self.root): path.read_bytes()
                  for path in self.root.rglob("*") if path.is_file()}

        result = self.run_tool("adopt", "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PLAN     -> docs/PLAN.md", result.stdout)
        self.assertIn("filesystem unchanged", result.stdout)
        after = {path.relative_to(self.root): path.read_bytes()
                 for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_check_fails_when_now_exceeds_configured_limit(self) -> None:
        self.write_records(
            "# TODO\n\n## Now\n\n### T-001 - one\n\n### T-002 - two\n"
        )
        self.write_config(max_items=1)

        result = self.run_tool("check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("maximum is 1", result.stderr)

    def test_check_fails_closed_on_configured_command(self) -> None:
        self.write_records()
        (self.root / "guard.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        python = Path(sys.executable).as_posix()
        self.write_config(checks=[("failing", f'"{python}" guard.py')])

        result = self.run_tool("check")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failing (failed, exit 7)", result.stderr)

    def test_record_partial_prepends_and_preserves_todo(self) -> None:
        todo = (
            "# TODO\n\n## Now\n\n### MH-001 - work `[now]`\n\n"
            "**Contracts:** `MH-C-TEST-001`.\n\n**Done when:** it runs\n"
        )
        progress = "# Progress\n\n---\n\n## 2026-01-01 - old\n\nKept.\n"
        self.write_records(todo, progress)
        self.write_config()

        result = self.run_tool(
            "record-partial", "--task", "MH-001", "--title", "half",
            "--changed", "Measured half.", "--learned", "The edge is real.",
            "--profile", "status", "--evidence", "PLAN.md",
            "--limitations", "The remaining half is open.",
            "--next", "Finish the remaining half.", "--date", "2026-08-09",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        current_progress = (self.root / "PROGRESS.md").read_text(encoding="utf-8")
        self.assertIn("## 2026-08-09 - half", current_progress)
        self.assertTrue(current_progress.endswith(progress.split("---\n", 1)[1]))
        self.assertEqual((self.root / "TODO.md").read_text(encoding="utf-8"), todo)

    def test_record_done_consumes_task_when_checks_pass(self) -> None:
        self.write_records(
            "# TODO\n\n## Now\n\n### MH-001 - work `[now]`\n\n"
            "**Contracts:** `MH-C-TEST-001`.\n\n"
            "**Done when:** it runs\n\n## Next\n\n## Later\n\n## Blocked\n"
        )
        self.write_config()

        before_plan = (self.root / "PLAN.md").read_bytes()
        result = self.run_tool(
            "record-done", "--task", "MH-001", "--title", "finished",
            "--changed", "Finished it.", "--learned", "It was bounded.",
            "--profile", "status", "--evidence", "PLAN.md",
            "--limitations", "No known limitations.",
            "--next", "Start the next item.", "--date", "2026-08-09",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        current_todo = (self.root / "TODO.md").read_text(encoding="utf-8")
        self.assertNotIn("### MH-001", current_todo)
        self.assertIn("## Now\n\n## Next", current_todo)
        self.assertIn("MH-001 (`done`)", (self.root / "PROGRESS.md").read_text(encoding="utf-8"))
        self.assertEqual((self.root / "PLAN.md").read_bytes(), before_plan)

    def test_record_done_rolls_back_both_files_when_check_fails(self) -> None:
        todo = (
            "# TODO\n\n## Now\n\n### MH-001 - work `[now]`\n\n"
            "**Contracts:** `MH-C-TEST-001`.\n\n**Done when:** it runs\n"
        )
        progress = "# Progress\n\n---\n\n## 2026-01-01 - old\n\nKept.\n"
        self.write_records(todo, progress)
        (self.root / "guard.py").write_text(
            "from pathlib import Path\n"
            "raise SystemExit(0 if 'MH-001' in Path('TODO.md').read_text() else 9)\n",
            encoding="utf-8",
        )
        python = Path(sys.executable).as_posix()
        self.write_config(checks=[("task-remains", f'"{python}" guard.py')])
        before_todo = (self.root / "TODO.md").read_bytes()
        before_progress = (self.root / "PROGRESS.md").read_bytes()

        result = self.run_tool(
            "record-done", "--task", "MH-001", "--title", "finished",
            "--changed", "Finished it.", "--learned", "The guard disagreed.",
            "--profile", "status", "--evidence", "PLAN.md",
            "--limitations", "The guard still disagrees.",
            "--next", "Resolve the guard.", "--date", "2026-08-09",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("records restored", result.stderr)
        self.assertEqual((self.root / "TODO.md").read_bytes(), before_todo)
        self.assertEqual((self.root / "PROGRESS.md").read_bytes(), before_progress)

    def test_upgrade_replaces_only_with_newer_valid_source(self) -> None:
        target = self.root / "tools" / "project_status.py"
        target.parent.mkdir()
        target.write_bytes(TOOL.read_bytes())
        source = self.root / "newer.py"
        source.write_bytes(TOOL.read_bytes().replace(
            b'TOOL_VERSION = "2.0.0"', b'TOOL_VERSION = "2.1.0"', 1
        ))

        result = self.run_tool("upgrade", "--source", str(source), tool=target)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'TOOL_VERSION = "2.1.0"', target.read_bytes())

    def test_init_writes_history_aware_ci_and_literal_hook(self) -> None:
        result = self.run_tool("init")

        self.assertEqual(result.returncode, 0, result.stderr)
        workflow = (self.root / ".github" / "workflows" / "project-status.yml")
        hook = self.root / ".githooks" / "pre-commit"
        self.assertIn("fetch-depth: 0", workflow.read_text(encoding="utf-8"))
        self.assertIn("printf '%s\\n'", hook.read_text(encoding="utf-8"))

    def test_cli_is_clean_with_python_warnings_as_errors(self) -> None:
        result = subprocess.run(
            [sys.executable, "-W", "error", str(TOOL), "--version"],
            text=True,
            capture_output=True,
            encoding="utf-8",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2.0.0")

    def test_init_refuses_existing_records(self) -> None:
        (self.root / "PLAN.md").write_text("owner content\n", encoding="utf-8")

        result = self.run_tool("init")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("require adopt", result.stderr)
        self.assertEqual((self.root / "PLAN.md").read_text(), "owner content\n")


if __name__ == "__main__":
    unittest.main()
