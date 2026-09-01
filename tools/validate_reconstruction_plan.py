#!/usr/bin/env python3
"""Validate the structural contract of the MathHead reconstruction records."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


TASK_ID = r"MH-[0-9]{3}"
PLAN_TASK = re.compile(rf"^####\s+({TASK_ID})\s+-\s+(.+?)\s*$", re.MULTILINE)
TODO_TASK = re.compile(rf"^###\s+({TASK_ID})\s+-\s+(.+?)\s*$", re.MULTILINE)
PROGRESS_TASK = re.compile(rf"\*\*Task\.\*\*\s+({TASK_ID})\b")
REQUIRED_QUEUES = ("Now", "Next", "Later", "Blocked")


class PlanValidationError(RuntimeError):
    """Raised when reconstruction status records violate their frozen contract."""


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise PlanValidationError(f"cannot read {path}: {exc}") from exc


def _unique(matches: list[tuple[str, str]], label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for task, title in matches:
        if task in result:
            raise PlanValidationError(f"duplicate {label} task: {task}")
        result[task] = title.strip()
    return result


def _section(text: str, name: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(name)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise PlanValidationError(f"TODO is missing queue: {name}")
    return match.group("body")


def validate(root: Path) -> tuple[int, int, int]:
    plan_path = root / "docs" / "PLAN.md"
    todo_path = root / "docs" / "TODO.md"
    progress_path = root / "docs" / "PROGRESS.md"
    status_contract = root / "docs" / "contracts" / "PROJECT_STATUS_CONTRACT_V1.md"
    workflow_contract = root / "docs" / "contracts" / "PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md"

    plan = _read(plan_path)
    todo = _read(todo_path)
    progress = _read(progress_path)
    status_text = _read(status_contract)
    workflow_text = _read(workflow_contract)

    if "**Status:** FROZEN" not in status_text:
        raise PlanValidationError("project-status contract is not frozen")
    if "**Status:** FROZEN" not in workflow_text:
        raise PlanValidationError("Python contract workflow is not frozen")

    plan_tasks = _unique(PLAN_TASK.findall(plan), "PLAN")
    if not plan_tasks:
        raise PlanValidationError("PLAN declares no MH tasks")
    todo_tasks = _unique(TODO_TASK.findall(todo), "TODO")
    unknown_todo = sorted(set(todo_tasks) - set(plan_tasks))
    if unknown_todo:
        raise PlanValidationError(
            "TODO references task(s) absent from PLAN: " + ", ".join(unknown_todo)
        )

    queue_bodies = {name: _section(todo, name) for name in REQUIRED_QUEUES}
    now_count = len(TODO_TASK.findall(queue_bodies["Now"]))
    if now_count > 5:
        raise PlanValidationError(f"TODO Now has {now_count} tasks; maximum is 5")

    if "\n---\n" not in progress.replace("\r\n", "\n"):
        raise PlanValidationError("PROGRESS has no append-only divider")
    progress_ids = PROGRESS_TASK.findall(progress)
    unknown_progress = sorted(set(progress_ids) - set(plan_tasks))
    if unknown_progress:
        raise PlanValidationError(
            "PROGRESS references task(s) absent from PLAN: "
            + ", ".join(unknown_progress)
        )

    config_path = root / ".project-status.toml"
    if config_path.exists():
        config = _read(config_path)
        required = (
            'plan = "docs/PLAN.md"',
            'todo = "docs/TODO.md"',
            'progress = "docs/PROGRESS.md"',
        )
        missing = [line for line in required if line not in config]
        if missing:
            raise PlanValidationError(
                "project-status config lacks exact-case path(s): " + ", ".join(missing)
            )

    return len(plan_tasks), len(todo_tasks), now_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        plan_count, todo_count, now_count = validate(root)
    except PlanValidationError as exc:
        print(f"reconstruction-plan: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "reconstruction-plan: PASS "
        f"(plan={plan_count}, todo={todo_count}, now={now_count}/5)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
