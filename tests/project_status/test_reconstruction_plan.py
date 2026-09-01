from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tools" / "validate_reconstruction_plan.py"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--root", str(root)],
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def _write_fixture(root: Path, todo_task: str = "MH-000") -> None:
    contracts = root / "docs" / "contracts"
    contracts.mkdir(parents=True)
    (contracts / "PROJECT_STATUS_CONTRACT_V1.md").write_text(
        "**Status:** FROZEN\n", encoding="utf-8"
    )
    (contracts / "PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md").write_text(
        "**Status:** FROZEN\n", encoding="utf-8"
    )
    (root / "docs" / "PLAN.md").write_text(
        "# Plan\n\n#### MH-000 - Start\n", encoding="utf-8"
    )
    (root / "docs" / "TODO.md").write_text(
        "# TODO\n\n"
        f"## Now\n\n### {todo_task} - Start\n\n"
        "## Next\n\n## Later\n\n## Blocked\n",
        encoding="utf-8",
    )
    (root / "docs" / "PROGRESS.md").write_text(
        "# Progress\n\n---\n", encoding="utf-8"
    )


class ReconstructionPlanTests(unittest.TestCase):
    def test_repository_reconstruction_plan_is_valid(self) -> None:
        result = _run(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reconstruction-plan: PASS", result.stdout)

    def test_unknown_todo_task_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_fixture(root, todo_task="MH-999")
            result = _run(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("absent from PLAN", result.stderr)

    def test_duplicate_plan_task_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_fixture(root)
            plan = root / "docs" / "PLAN.md"
            plan.write_text(
                plan.read_text(encoding="utf-8") + "\n#### MH-000 - Again\n",
                encoding="utf-8",
            )
            result = _run(root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("duplicate PLAN task", result.stderr)


if __name__ == "__main__":
    unittest.main()
