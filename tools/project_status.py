#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Portable, repository-owned project status automation."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import re
import subprocess
import sys
import tempfile
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility in the pinned core profile.
    import tomli as tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TOOL_VERSION = "2.0.0"
CONFIG_NAME = ".project-status.toml"
TASK_ID = re.compile(r"^[A-Z][A-Z0-9-]*-\d+$")
PROFILE_NAME = re.compile(r"^[a-z][a-z0-9-]*$")
VERSION_LINE = re.compile(
    rb'^TOOL_VERSION\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']\s*$', re.MULTILINE
)


class StatusError(RuntimeError):
    """A user-facing, fail-closed status automation error."""


@dataclass(frozen=True)
class Check:
    name: str
    command: str
    profiles: tuple[str, ...]
    tasks: tuple[str, ...]
    timeout_seconds: int


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    exit_code: int | None
    output_sha256: str


@dataclass(frozen=True)
class ContractEvidence:
    contract_id: str
    path: str
    sha256: str


@dataclass(frozen=True)
class FileEvidence:
    path: str
    sha256: str


@dataclass(frozen=True)
class Config:
    root: Path
    plan: Path
    progress: Path
    todo: Path
    contract_manifest: Path | None
    max_todo_items: int
    todo_mode: str
    checks: tuple[Check, ...]


GENERIC_AGENTS = """# Repository instructions

## Project status

- Read PLAN, TODO, and PROGRESS before substantial development.
- Treat PROGRESS as immutable history; add only a newest session block.
- Use `python tools/project_status.py check` before reporting completion.
- Use the repository status tool for completed or partial task transitions.
- Never bypass a failing configured status check.
"""

GENERIC_PLAN = """# Plan

Record stable goals and acceptance criteria here. Put changing execution state
in TODO and durable session evidence in PROGRESS.
"""

GENERIC_PROGRESS = """# Progress

Append-only history, newest first.

---
"""

GENERIC_TODO = """# TODO

## Now

## Next

## Later

## Blocked
"""

ATTRIBUTES_TEMPLATE = """# Keep repository evidence byte-stable across Linux and Windows checkouts.
* text=auto eol=lf

# Markdown uses two trailing spaces for intentional hard line breaks.
*.md text eol=lf whitespace=-trailing-space
"""

HOOK_TEMPLATE = r"""#!/bin/sh
set -eu

staged="$(git diff --cached --name-only --diff-filter=ACMR)"
[ -n "$staged" ] || exit 0

# A PROGRESS-only record is already append-only evidence. Every other staged
# path, including TODO consumption, is substantive under the status model.
progress_path="$(sed -n 's/^progress = "\([^"]*\)"/\1/p' .project-status.toml | head -n 1)"
if [ -n "$progress_path" ] && ! printf '%s\n' "$staged" | grep -Fqvx "$progress_path"; then
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 tools/project_status.py check
fi
if command -v python >/dev/null 2>&1; then
  exec python tools/project_status.py check
fi

echo "project-status: Python 3 is required" >&2
exit 1
"""

WORKFLOW_TEMPLATE = """name: Project Status (governance only, not product health)

on:
  pull_request:
  push:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  project-status:
    name: project-status only (not product health) - ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    steps:
      - name: Check out repository
        uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Set up Python
        uses: actions/setup-python@v7
        with:
          python-version: "3.11"
      - name: Test project-status tool
        run: python -m unittest discover -s tests/project_status -v
      - name: Validate project status
        env:
          PROJECT_STATUS_BASE: ${{ github.event.pull_request.base.sha || github.event.before }}
        run: python tools/project_status.py check
"""


def _inside(root: Path, relative: str, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise StatusError(f"{label} escapes repository root: {relative}") from exc
    return candidate


def _exact_case_path(root: Path, relative: str, label: str) -> Path:
    """Resolve a repository path while rejecting case-insensitive aliases."""
    candidate = _inside(root, relative, label)
    current = root
    for part in Path(relative).parts:
        if part in {"", "."}:
            continue
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            raise StatusError(f"cannot inspect exact-case {label} path: {exc}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise StatusError(
                    f"{label} has an exact-case mismatch: requested {part!r}, "
                    f"found {aliases[0]!r}"
                )
            raise StatusError(f"{label} path component does not exist: {part}")
        current = current / part
    return candidate


def find_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise StatusError(f"repository root does not exist: {root}")
        return root

    start = Path.cwd().resolve()
    for candidate in (start, *start.parents):
        if (candidate / CONFIG_NAME).is_file():
            return candidate

    script_root = Path(__file__).resolve().parents[1]
    if (script_root / ".git").exists():
        return script_root
    return start


def load_config(root: Path) -> Config:
    path = root / CONFIG_NAME
    if not path.is_file():
        raise StatusError(
            f"{CONFIG_NAME} is missing; run `project_status.py adopt --dry-run`"
        )
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise StatusError(f"cannot read {CONFIG_NAME}: {exc}") from exc

    if data.get("schema") != 1:
        raise StatusError(f"{CONFIG_NAME}: schema must be 1")
    max_items = data.get("max_todo_items", 7)
    if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 1:
        raise StatusError(f"{CONFIG_NAME}: max_todo_items must be a positive integer")
    todo_mode = data.get("todo_mode", "managed")
    if todo_mode not in {"managed"}:
        raise StatusError(f"{CONFIG_NAME}: unsupported todo_mode {todo_mode!r}")

    def required_path(key: str) -> Path:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise StatusError(f"{CONFIG_NAME}: {key} must be a relative path")
        if Path(value).is_absolute():
            raise StatusError(f"{CONFIG_NAME}: {key} must be relative")
        return _exact_case_path(root, value, key)

    def optional_path(key: str) -> Path | None:
        value = data.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise StatusError(f"{CONFIG_NAME}: {key} must be a relative path")
        if Path(value).is_absolute():
            raise StatusError(f"{CONFIG_NAME}: {key} must be relative")
        return _exact_case_path(root, value, key)

    def string_tuple(item: dict[str, object], key: str, index: int) -> tuple[str, ...]:
        value = item.get(key, [])
        if not isinstance(value, list) or not all(
            isinstance(entry, str) and entry.strip() for entry in value
        ):
            raise StatusError(f"{CONFIG_NAME}: checks[{index}].{key} must be strings")
        return tuple(value)

    raw_checks = data.get("checks", [])
    if not isinstance(raw_checks, list):
        raise StatusError(f"{CONFIG_NAME}: checks must be an array of tables")
    checks: list[Check] = []
    names: set[str] = set()
    for index, item in enumerate(raw_checks, 1):
        if not isinstance(item, dict):
            raise StatusError(f"{CONFIG_NAME}: checks[{index}] must be a table")
        name, command = item.get("name"), item.get("command")
        if not isinstance(name, str) or not name.strip():
            raise StatusError(f"{CONFIG_NAME}: checks[{index}].name is required")
        if name in names:
            raise StatusError(f"{CONFIG_NAME}: duplicate check name {name!r}")
        if not isinstance(command, str) or not command.strip():
            raise StatusError(f"{CONFIG_NAME}: checks[{index}].command is required")
        profiles = string_tuple(item, "profiles", index)
        if any(not PROFILE_NAME.fullmatch(profile) for profile in profiles):
            raise StatusError(
                f"{CONFIG_NAME}: checks[{index}].profiles contains an invalid name"
            )
        tasks = string_tuple(item, "tasks", index)
        if any(not TASK_ID.fullmatch(task) for task in tasks):
            raise StatusError(
                f"{CONFIG_NAME}: checks[{index}].tasks contains an invalid task ID"
            )
        timeout = item.get("timeout_seconds", 120)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
            raise StatusError(
                f"{CONFIG_NAME}: checks[{index}].timeout_seconds must be positive"
            )
        names.add(name)
        checks.append(
            Check(
                name=name,
                command=command,
                profiles=profiles,
                tasks=tasks,
                timeout_seconds=timeout,
            )
        )

    return Config(
        root=root,
        plan=required_path("plan"),
        progress=required_path("progress"),
        todo=required_path("todo"),
        contract_manifest=optional_path("contract_manifest"),
        max_todo_items=max_items,
        todo_mode=todo_mode,
        checks=tuple(checks),
    )


def _todo_now_count(text: str) -> int:
    in_now = False
    count = 0
    for line in text.splitlines():
        if line.startswith("## "):
            in_now = line[3:].strip() == "Now"
            continue
        if in_now and re.match(r"^###\s+", line):
            count += 1
    return count


def _git_output(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False
    )


def _progress_parts(raw: bytes, label: str) -> tuple[bytes, bytes]:
    normalized = raw.replace(b"\r\n", b"\n")
    divider = b"\n---\n"
    marker = normalized.find(divider)
    if marker < 0:
        raise StatusError(f"{label} has no front-matter divider")
    split = marker + len(divider)
    return normalized[:split], normalized[split:]


def _validate_progress_append_only(config: Config) -> None:
    if not (config.root / ".git").exists():
        return
    relative = config.progress.relative_to(config.root).as_posix()
    explicit_base = os.environ.get("PROJECT_STATUS_BASE", "").strip()
    if explicit_base:
        base = explicit_base
        if re.fullmatch(r"0{40}|0{64}", base):
            head = _git_output(
                config.root, "rev-list", "--parents", "-n", "1", "HEAD"
            )
            if head.returncode:
                message = head.stderr.decode("utf-8", errors="replace").strip()
                raise StatusError(f"cannot resolve zero PROGRESS baseline: {message}")
            revisions = head.stdout.decode("ascii", errors="strict").split()
            if len(revisions) == 1:
                return
            base = revisions[1]
    else:
        dirty = _git_output(config.root, "diff", "--quiet", "HEAD", "--", relative)
        base = "HEAD" if dirty.returncode else "HEAD^"
    previous = _git_output(config.root, "show", f"{base}:{relative}")
    if previous.returncode:
        if explicit_base:
            valid_base = _git_output(
                config.root, "rev-parse", "--verify", f"{base}^{{commit}}"
            )
            history = _git_output(
                config.root,
                "rev-list",
                "--reverse",
                f"{base}..HEAD",
                "--",
                relative,
            )
            revisions = history.stdout.decode("ascii", errors="strict").split()
            introduced = (
                _git_output(config.root, "show", f"{revisions[0]}:{relative}")
                if valid_base.returncode == 0 and history.returncode == 0 and revisions
                else None
            )
            if introduced is None or introduced.returncode:
                message = previous.stderr.decode("utf-8", errors="replace").strip()
                raise StatusError(f"cannot read PROGRESS baseline {base}: {message}")
            previous = introduced
        else:
            return
    current = config.progress.read_bytes()
    old_header, old_history = _progress_parts(previous.stdout, f"{base}:{relative}")
    new_header, new_history = _progress_parts(current, relative)
    if new_header != old_header:
        raise StatusError("PROGRESS front matter changed; history is append-only")
    if not new_history.endswith(old_history):
        raise StatusError("PROGRESS historical bytes changed; prepend new entries only")


def validate_records(config: Config) -> None:
    missing = [
        path.relative_to(config.root).as_posix()
        for path in (config.plan, config.progress, config.todo)
        if not path.is_file()
    ]
    if missing:
        raise StatusError("missing status record(s): " + ", ".join(missing))

    try:
        todo = config.todo.read_text(encoding="utf-8")
        progress = config.progress.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StatusError(f"cannot read status records: {exc}") from exc
    if "\n---\n" not in progress.replace("\r\n", "\n"):
        raise StatusError(
            f"{config.progress.relative_to(config.root).as_posix()} has no "
            "front-matter divider"
        )
    now_count = _todo_now_count(todo)
    if now_count > config.max_todo_items:
        raise StatusError(
            f"TODO Now has {now_count} items; maximum is {config.max_todo_items}"
        )
    _validate_progress_append_only(config)
    print(
        "project-status records: "
        f"plan={config.plan.relative_to(config.root).as_posix()}  "
        f"todo={config.todo.relative_to(config.root).as_posix()}  "
        f"progress={config.progress.relative_to(config.root).as_posix()}  "
        f"now={now_count}/{config.max_todo_items}"
    )


def _selected_checks(
    config: Config,
    profile: str | None = None,
    task: str | None = None,
    require_task_check: bool = False,
) -> tuple[Check, ...]:
    if profile is None:
        return config.checks
    if not PROFILE_NAME.fullmatch(profile):
        raise StatusError(f"invalid validator profile: {profile!r}")
    profile_checks = [check for check in config.checks if profile in check.profiles]
    if not profile_checks:
        raise StatusError(f"validator profile has no configured checks: {profile}")
    task_checks = [check for check in config.checks if task and task in check.tasks]
    if require_task_check and not task_checks:
        raise StatusError(f"task has no configured task-specific validator: {task}")
    selected: list[Check] = []
    for check in (*profile_checks, *task_checks):
        if check not in selected:
            selected.append(check)
    return tuple(selected)


def _check_status(returncode: int, stderr: str) -> str:
    if returncode == 0:
        return "passed"
    if returncode == 77:
        return "skipped"
    if returncode == 78:
        return "inconclusive"
    lowered = stderr.casefold()
    if returncode in {127, 9009} or "not found" in lowered or "not recognized" in lowered:
        return "missing"
    return "failed"


def execute_checks(checks: Iterable[Check], root: Path) -> tuple[CheckResult, ...]:
    results: list[CheckResult] = []
    for check in checks:
        print(f"project-status check: {check.name} -> {check.command}", flush=True)
        try:
            completed = subprocess.run(
                check.command,
                cwd=root,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=check.timeout_seconds,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            if stdout:
                print(stdout, end="" if stdout.endswith("\n") else "\n")
            if stderr:
                print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
            payload = (stdout + "\0" + stderr).encode("utf-8")
            results.append(
                CheckResult(
                    name=check.name,
                    status=_check_status(completed.returncode, stderr),
                    exit_code=completed.returncode,
                    output_sha256=hashlib.sha256(payload).hexdigest(),
                )
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            payload = (stdout + "\0" + stderr).encode("utf-8")
            results.append(
                CheckResult(
                    name=check.name,
                    status="timed-out",
                    exit_code=None,
                    output_sha256=hashlib.sha256(payload).hexdigest(),
                )
            )
    return tuple(results)


def require_green(results: Iterable[CheckResult]) -> None:
    failures = [result for result in results if result.status != "passed"]
    if failures:
        rendered = ", ".join(
            f"{result.name} ({result.status}"
            + (f", exit {result.exit_code}" if result.exit_code is not None else "")
            + ")"
            for result in failures
        )
        raise StatusError("configured check(s) failed: " + rendered)


def run_checks(
    config: Config,
    profile: str | None = None,
    task: str | None = None,
    require_task_check: bool = False,
) -> tuple[CheckResult, ...]:
    selected = _selected_checks(config, profile, task, require_task_check)
    results = execute_checks(selected, config.root)
    require_green(results)
    return results


def perform_check(root: Path) -> None:
    config = load_config(root)
    validate_records(config)
    run_checks(config)
    print(f"project-status: PASS (tool {TOOL_VERSION}, {len(config.checks)} check(s))")


def render_config(plan: str, progress: str, todo: str, max_items: int = 7) -> str:
    return f'''schema = 1
tool_version = "{TOOL_VERSION}"
plan = "{plan}"
progress = "{progress}"
todo = "{todo}"
todo_mode = "managed"
max_todo_items = {max_items}
'''


def _write_new(path: Path, content: str, dry_run: bool) -> None:
    if path.exists():
        raise StatusError(f"refusing to overwrite existing file: {path}")
    print(f"{'would create' if dry_run else 'create'}: {path}")
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")


def _integration_templates(root: Path) -> tuple[tuple[Path, str], ...]:
    return (
        (root / ".gitattributes", ATTRIBUTES_TEMPLATE),
        (root / "AGENTS.md", GENERIC_AGENTS),
        (root / ".githooks" / "pre-commit", HOOK_TEMPLATE),
        (root / ".github" / "workflows" / "project-status.yml", WORKFLOW_TEMPLATE),
    )


def command_init(root: Path, dry_run: bool) -> None:
    if (root / CONFIG_NAME).exists():
        raise StatusError(f"{CONFIG_NAME} already exists; repository is initialized")
    existing_records = [name for name in ("PLAN.md", "PROGRESS.md", "TODO.md")
                        if (root / name).exists()]
    if existing_records:
        raise StatusError(
            "existing status record(s) require adopt, not init: "
            + ", ".join(existing_records)
        )
    _write_new(root / "PLAN.md", GENERIC_PLAN, dry_run)
    _write_new(root / "PROGRESS.md", GENERIC_PROGRESS, dry_run)
    _write_new(root / "TODO.md", GENERIC_TODO, dry_run)
    _write_new(
        root / CONFIG_NAME,
        render_config("PLAN.md", "PROGRESS.md", "TODO.md"),
        dry_run,
    )
    for path, content in _integration_templates(root):
        _write_new(path, content, dry_run)
    print("project-status init: dry-run complete" if dry_run else "project-status init: complete")


def _first_existing(root: Path, candidates: Iterable[str]) -> str | None:
    return next((item for item in candidates if (root / item).is_file()), None)


def infer_records(root: Path) -> tuple[str, str, str]:
    plan = _first_existing(root, ("docs/PLAN.md", "PLAN.md", "plan.md"))
    progress = _first_existing(root, ("docs/PROGRESS.md", "PROGRESS.md"))
    todo = _first_existing(root, ("docs/TODO.md", "TODO.md"))
    missing = [name for name, value in (("PLAN", plan), ("PROGRESS", progress),
                                         ("TODO", todo)) if value is None]
    if missing:
        raise StatusError("cannot adopt; missing recognizable record(s): " + ", ".join(missing))
    return plan, progress, todo


def command_adopt(root: Path, dry_run: bool) -> None:
    config_path = root / CONFIG_NAME
    if config_path.exists():
        config = load_config(root)
        mapping = (
            config.plan.relative_to(root).as_posix(),
            config.progress.relative_to(root).as_posix(),
            config.todo.relative_to(root).as_posix(),
        )
    else:
        mapping = infer_records(root)

    print("project-status adoption mapping:")
    print(f"  PLAN     -> {mapping[0]}")
    print(f"  PROGRESS -> {mapping[1]}")
    print(f"  TODO     -> {mapping[2]}")

    actions: list[tuple[Path, str]] = []
    if not config_path.exists():
        actions.append((config_path, render_config(*mapping)))
    actions.extend((path, content) for path, content in _integration_templates(root)
                   if not path.exists())

    if actions:
        for path, content in actions:
            _write_new(path, content, dry_run)
    else:
        print("  no file changes required")
    if dry_run:
        print("project-status adopt: dry-run complete; filesystem unchanged")
        return
    perform_check(root)
    print("project-status adopt: complete")


def _normalized_text(raw: bytes, path: Path) -> tuple[str, str]:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeError as exc:
        raise StatusError(f"{path} is not UTF-8: {exc}") from exc
    newline = "\r\n" if b"\r\n" in raw else "\n"
    return decoded.replace("\r\n", "\n"), newline


def _encoded_text(text: str, newline: str) -> bytes:
    return text.replace("\n", newline).encode("utf-8")


def _progress_with_block(progress: str, block: str) -> str:
    divider = "\n---\n"
    marker = progress.find(divider)
    if marker < 0:
        raise StatusError("PROGRESS has no front-matter divider")
    split = marker + len(divider)
    return progress[:split] + "\n" + block.rstrip() + "\n\n---\n" + progress[split:]


def _task_location(todo: str, task: str) -> tuple[str, str]:
    lines = todo.splitlines(keepends=True)
    queue = ""
    for index, line in enumerate(lines):
        queue_match = re.match(r"^##\s+(.+?)\s*$", line)
        if queue_match:
            queue = queue_match.group(1)
            continue
        if re.match(rf"^###\s+{re.escape(task)}\b", line):
            end = len(lines)
            for later in range(index + 1, len(lines)):
                if re.match(r"^#{2,3}\s+", lines[later]):
                    end = later
                    break
            return queue, "".join(lines[index:end])
    raise StatusError(f"TODO item does not exist: {task}")


def _task_contract_ids(block: str) -> tuple[str, ...]:
    match = re.search(
        r"\*\*Contracts:\*\*(.*?)(?=\n\n\*\*|\Z)", block, re.DOTALL
    )
    if match is None:
        raise StatusError("TODO task has no Contracts field")
    identifiers = tuple(dict.fromkeys(re.findall(r"`(MH-C-[A-Z0-9-]+)`", match.group(1))))
    if not identifiers:
        raise StatusError("TODO task has no machine-readable contract ID")
    return identifiers


def _contract_evidence(
    config: Config,
    contract_ids: tuple[str, ...],
    *,
    require_accepted: bool,
) -> tuple[ContractEvidence, ...]:
    if config.contract_manifest is None:
        raise StatusError("contract_manifest is required for status transitions")
    try:
        data = tomllib.loads(config.contract_manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise StatusError(f"cannot read contract manifest: {exc}") from exc
    if data.get("schema") != 1 or not isinstance(data.get("contracts"), list):
        raise StatusError("contract manifest must use schema 1 and [[contracts]] entries")
    entries: dict[str, dict[str, object]] = {}
    for raw in data["contracts"]:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
            raise StatusError("contract manifest contains a malformed entry")
        contract_id = raw["id"]
        if contract_id in entries:
            raise StatusError(f"duplicate contract manifest ID: {contract_id}")
        entries[contract_id] = raw
    evidence: list[ContractEvidence] = []
    for contract_id in contract_ids:
        raw = entries.get(contract_id)
        if raw is None:
            raise StatusError(f"accepted contract is absent from manifest: {contract_id}")
        path_value = raw.get("path")
        expected = raw.get("sha256")
        state = raw.get("state")
        if state not in {"proposed", "accepted"}:
            raise StatusError(f"contract has an invalid manifest state: {contract_id}")
        if require_accepted and state != "accepted":
            raise StatusError(f"contract is not accepted: {contract_id}")
        if not isinstance(path_value, str) or not isinstance(expected, str):
            raise StatusError(f"contract manifest entry is incomplete: {contract_id}")
        path = _exact_case_path(config.root, path_value, f"contract {contract_id}")
        if not path.is_file():
            raise StatusError(f"contract artifact is missing: {path_value}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", expected) or actual != expected:
            raise StatusError(f"accepted contract hash mismatch: {contract_id}")
        evidence.append(ContractEvidence(contract_id, path_value, actual))
    return tuple(evidence)


def _file_evidence(config: Config, values: list[str]) -> tuple[FileEvidence, ...]:
    if not values:
        raise StatusError("at least one --evidence path is required")
    evidence: list[FileEvidence] = []
    for value in dict.fromkeys(values):
        if Path(value).is_absolute():
            raise StatusError(f"evidence path must be repository-relative: {value}")
        path = _exact_case_path(config.root, value, "evidence")
        if not path.is_file():
            raise StatusError(f"evidence path is not a file: {value}")
        evidence.append(FileEvidence(value, hashlib.sha256(path.read_bytes()).hexdigest()))
    return tuple(evidence)


def _consume_task(todo: str, task: str) -> str:
    lines = todo.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines)
                  if re.match(rf"^###\s+{re.escape(task)}\b", line)), None)
    if start is None:
        raise StatusError(f"TODO item does not exist: {task}")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if re.match(r"^(?:#{2,3}\s+|---\s*$)", lines[index]):
            end = index
            break
    del lines[start:end]
    return "".join(lines)


def _record_block(
    args: argparse.Namespace,
    state: str,
    contracts: tuple[ContractEvidence, ...],
    checks: tuple[CheckResult, ...],
    evidence: tuple[FileEvidence, ...],
) -> str:
    date = args.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError as exc:
        raise StatusError("--date must be YYYY-MM-DD") from exc
    contract_text = "; ".join(
        f"{item.contract_id}={item.sha256} ({item.path})" for item in contracts
    )
    check_text = "; ".join(
        f"{item.name}={item.status}"
        + (f"/exit-{item.exit_code}" if item.exit_code is not None else "")
        + f"/output-{item.output_sha256}"
        for item in checks
    )
    evidence_text = "; ".join(f"{item.path}={item.sha256}" for item in evidence)
    return (
        f"## {date} - {args.title}\n\n"
        f"**Task.** {args.task} (`{state}`).\n\n"
        f"**Changed.** {args.changed.strip()}\n\n"
        f"**Learned.** {args.learned.strip()}\n\n"
        f"**Contracts.** {contract_text}\n\n"
        f"**Validator profile.** {args.profile}.\n\n"
        f"**Validators.** {check_text}\n\n"
        f"**Evidence.** {evidence_text}\n\n"
        f"**Limitations.** {args.limitations.strip()}\n\n"
        f"**Next.** {args.next_step.strip()}"
    )


def command_record(root: Path, args: argparse.Namespace, done: bool) -> None:
    if not TASK_ID.fullmatch(args.task):
        raise StatusError("--task must look like T-001 or PROJECT-42")
    config = load_config(root)
    validate_records(config)

    progress_raw = config.progress.read_bytes()
    todo_raw = config.todo.read_bytes()
    progress, progress_newline = _normalized_text(progress_raw, config.progress)
    todo, todo_newline = _normalized_text(todo_raw, config.todo)
    queue, task_block = _task_location(todo, args.task)
    if queue != "Now":
        raise StatusError(f"status transitions require a task in TODO Now, found {queue!r}")
    for label, value in (
        ("--title", args.title),
        ("--changed", args.changed),
        ("--learned", args.learned),
        ("--limitations", args.limitations),
        ("--next", args.next_step),
    ):
        if not value.strip():
            raise StatusError(f"{label} must contain positive evidence text")
    contracts = _contract_evidence(
        config, _task_contract_ids(task_block), require_accepted=done
    )
    evidence = _file_evidence(config, args.evidence)
    selected = _selected_checks(
        config, args.profile, args.task, require_task_check=done
    )
    check_results = execute_checks(selected, config.root)
    if done:
        require_green(check_results)

    state = "done" if done else "partial"
    block = _record_block(args, state, contracts, check_results, evidence)
    new_progress = _progress_with_block(progress, block)
    new_todo = _consume_task(todo, args.task) if done else todo

    if args.dry_run:
        print(block)
        print(f"would prepend PROGRESS block for {args.task}")
        print(f"would {'consume' if done else 'retain'} TODO item {args.task}")
        print("record dry-run complete; filesystem unchanged")
        return

    try:
        config.progress.write_bytes(_encoded_text(new_progress, progress_newline))
        if done:
            config.todo.write_bytes(_encoded_text(new_todo, todo_newline))
        if done:
            perform_check(root)
        else:
            validate_records(config)
    except BaseException:
        config.progress.write_bytes(progress_raw)
        config.todo.write_bytes(todo_raw)
        print("project-status record: validation failed; records restored", file=sys.stderr)
        raise
    print(f"project-status record-{state}: {args.task} recorded")


def _version(raw: bytes, label: str) -> tuple[int, int, int]:
    match = VERSION_LINE.search(raw)
    if not match:
        raise StatusError(f"{label} has no literal TOOL_VERSION = x.y.z")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def command_upgrade(root: Path, source: Path, dry_run: bool) -> None:
    target = root / "tools" / "project_status.py"
    if not target.is_file():
        raise StatusError(f"vendored tool is missing: {target}")
    source = source.expanduser().resolve()
    if not source.is_file():
        raise StatusError(f"upgrade source does not exist: {source}")
    incoming = source.read_bytes()
    current = target.read_bytes()
    incoming_version = _version(incoming, str(source))
    current_version = _version(current, str(target))
    if incoming_version <= current_version:
        print(
            "project-status upgrade: no newer version "
            f"({'.'.join(map(str, current_version))} >= "
            f"{'.'.join(map(str, incoming_version))})"
        )
        return
    try:
        compile(incoming.decode("utf-8"), str(source), "exec")
    except (UnicodeError, SyntaxError) as exc:
        raise StatusError(f"upgrade source is not valid UTF-8 Python: {exc}") from exc
    print(
        "project-status upgrade: "
        f"{'.'.join(map(str, current_version))} -> "
        f"{'.'.join(map(str, incoming_version))}"
    )
    if dry_run:
        print("upgrade dry-run complete; filesystem unchanged")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".project_status.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(incoming)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("project-status upgrade: vendored tool replaced; review in a separate PR")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", help="repository root (default: discover from cwd)")
    result.add_argument("--version", action="version", version=TOOL_VERSION)
    commands = result.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize a new repository")
    init.add_argument("--dry-run", action="store_true")

    adopt = commands.add_parser("adopt", help="adopt existing status records")
    adopt.add_argument("--dry-run", action="store_true")

    commands.add_parser("sync", help="reconcile and validate managed state")
    commands.add_parser("check", help="run intrinsic and configured checks")

    def record(name: str, help_text: str) -> None:
        item = commands.add_parser(name, help=help_text)
        item.add_argument("--task", required=True)
        item.add_argument("--title", required=True)
        item.add_argument("--changed", required=True)
        item.add_argument("--learned", required=True)
        item.add_argument("--profile", required=True)
        item.add_argument("--evidence", action="append", default=[])
        item.add_argument("--limitations", required=True)
        item.add_argument("--next", dest="next_step", required=True)
        item.add_argument("--date")
        item.add_argument("--dry-run", action="store_true")

    record("record-done", "record and consume a completed TODO item")
    record("record-partial", "record partial progress and retain the TODO item")

    upgrade = commands.add_parser("upgrade", help="upgrade from a newer vendored source")
    upgrade.add_argument("--source", required=True, type=Path)
    upgrade.add_argument("--dry-run", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = find_root(args.root)
        if args.command == "init":
            command_init(root, args.dry_run)
        elif args.command == "adopt":
            command_adopt(root, args.dry_run)
        elif args.command == "sync":
            config = load_config(root)
            if config.todo_mode == "managed":
                print("project-status sync: managed TODO mode; validation only")
            perform_check(root)
        elif args.command == "check":
            perform_check(root)
        elif args.command == "record-done":
            command_record(root, args, done=True)
        elif args.command == "record-partial":
            command_record(root, args, done=False)
        elif args.command == "upgrade":
            command_upgrade(root, args.source, args.dry_run)
        else:  # pragma: no cover - argparse owns this branch
            raise StatusError(f"unknown command: {args.command}")
    except StatusError as exc:
        print(f"project-status: FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
