#!/usr/bin/env python3
"""Generate deterministic project claims from live repository sources."""

from __future__ import annotations

import argparse
import asyncio
import ast
from collections.abc import Sequence
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import traceback
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from mathhead.output import safe_print as print  # noqa: E402


CONTRACT_ID = "MH-C-PROJECT-FACTS-001"
CONTRACT_SHA256 = "701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad"
FACTS_PATH = Path("docs/project-facts.json")
EXAMPLES_PATH = Path("docs/examples.toml")
README_PATH = Path("README.md")
README_BEGIN = "<!-- BEGIN MATHHEAD PROJECT FACTS -->"
README_END = "<!-- END MATHHEAD PROJECT FACTS -->"


class ProjectFactsError(RuntimeError):
    """Expected metadata failure that must not cross the command boundary."""


class ProjectFactsTimeout(ProjectFactsError):
    """A bounded child operation exceeded its accepted budget."""


def _sha_lines(values: list[str]) -> str:
    payload = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _version() -> str:
    path = ROOT / "src/mathhead/_version.py"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ProjectFactsError(f"version-source-invalid:{exc}") from exc
    assignments = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    if len(assignments) != 1 or not isinstance(assignments[0].value.value, str):
        raise ProjectFactsError("version-source-missing")
    return assignments[0].value.value


def _terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _collect_tests() -> list[str]:
    kwargs: dict[str, Any] = {
        "cwd": ROOT,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"], **kwargs
    )
    try:
        stdout, stderr = process.communicate(timeout=90)
    except subprocess.TimeoutExpired as exc:
        _terminate(process)
        raise ProjectFactsTimeout("pytest-collection-timed-out") from exc
    except KeyboardInterrupt:
        _terminate(process)
        raise
    if process.returncode != 0:
        detail = (stderr or stdout).strip().splitlines()
        raise ProjectFactsError(
            "pytest-collection-failed:" + (detail[-1] if detail else str(process.returncode))
        )
    nodeids = sorted(
        line.strip()
        for line in stdout.splitlines()
        if line.startswith("tests/") and "::" in line
    )
    if not nodeids or len(nodeids) != len(set(nodeids)):
        raise ProjectFactsError("pytest-collection-empty-or-duplicate")
    return nodeids


async def _enumerate_tools() -> list[str]:
    from mathhead.server import mcp_server

    try:
        tools = await asyncio.wait_for(mcp_server.mcp.list_tools(), timeout=30)
    except asyncio.TimeoutError as exc:
        raise ProjectFactsTimeout("mcp-enumeration-timed-out") from exc
    names = sorted(tool.name for tool in tools)
    if not names or len(names) != len(set(names)):
        raise ProjectFactsError("mcp-enumeration-empty-or-duplicate")
    return names


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ProjectFactsError(f"toml-invalid:{path.relative_to(ROOT)}:{exc}") from exc


def build_facts() -> dict[str, Any]:
    from validate_project_metadata import ProjectMetadataError, validate_examples

    try:
        validate_examples()
    except ProjectMetadataError as exc:
        raise ProjectFactsError(f"example-ownership-invalid:{exc}") from exc
    profile_data = json.loads((ROOT / "tools/dev_profiles.json").read_text(encoding="utf-8"))
    profiles = list(profile_data["profiles"])
    runtime_python = profile_data["profiles"]["runtime"]["python"]
    example_data = _load_toml(ROOT / EXAMPLES_PATH)
    example_ids = sorted(item["id"] for item in example_data.get("examples", []))
    nodeids = _collect_tests()
    tool_names = asyncio.run(_enumerate_tools())
    return {
        "schema": "mathhead.project-facts.v1",
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "package": {"version": _version()},
        "mcp_tools": {"count": len(tool_names), "names_sha256": _sha_lines(tool_names)},
        "pytest": {"count": len(nodeids), "nodeids_sha256": _sha_lines(nodeids)},
        "profiles": {"names": profiles, "product_python": runtime_python},
        "examples": {"count": len(example_ids), "ids_sha256": _sha_lines(example_ids)},
    }


def _json_text(facts: dict[str, Any]) -> str:
    return json.dumps(facts, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _readme_region(facts: dict[str, Any]) -> str:
    version = facts["package"]["version"]
    tools = facts["mcp_tools"]["count"]
    tests = facts["pytest"]["count"]
    profiles = ", ".join(f"`{item}`" for item in facts["profiles"]["names"])
    python = ", ".join(facts["profiles"]["product_python"])
    return (
        f"{README_BEGIN}\n"
        f"**Package `{version}` · {tools} MCP tools · {tests} collected tests.**  \n"
        f"Governed profiles: {profiles}.  \n"
        f"Product Python matrix: {python}.\n"
        f"{README_END}"
    )


def _render_readme(facts: dict[str, Any]) -> str:
    try:
        current = (ROOT / README_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ProjectFactsError(f"readme-unreadable:{exc}") from exc
    if current.count(README_BEGIN) != 1 or current.count(README_END) != 1:
        raise ProjectFactsError("readme-generator-region-invalid")
    before, remainder = current.split(README_BEGIN, 1)
    _, after = remainder.split(README_END, 1)
    return before + _readme_region(facts) + after


def _replace(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _check_or_update(facts: dict[str, Any], *, update: bool) -> None:
    outputs = {
        ROOT / FACTS_PATH: _json_text(facts),
        ROOT / README_PATH: _render_readme(facts),
    }
    stale: list[str] = []
    for path, expected in outputs.items():
        try:
            current = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            current = ""
        if current != expected:
            stale.append(path.relative_to(ROOT).as_posix())
            if update:
                _replace(path, expected)
    if stale and not update:
        raise ProjectFactsError("generated-output-stale:" + ",".join(stale))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail if generated outputs drift")
    mode.add_argument("--update", action="store_true", help="replace only declared outputs")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)
    try:
        facts = build_facts()
        _check_or_update(facts, update=args.update)
    except ProjectFactsTimeout as exc:
        print(f"project-facts: TIMED_OUT: {exc}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 4
    except Exception as exc:
        print(f"project-facts: FAIL: {exc}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1
    except KeyboardInterrupt:
        print("project-facts: INTERRUPTED", file=sys.stderr)
        return 130
    action = "updated" if args.update else "current"
    print(
        f"project-facts: PASS ({action}; version={facts['package']['version']}; "
        f"tools={facts['mcp_tools']['count']}; tests={facts['pytest']['count']}; "
        f"examples={facts['examples']['count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
