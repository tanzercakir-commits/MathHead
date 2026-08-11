#!/usr/bin/env python3
"""Repository-owned development, validation, and clean-smoke dispatcher."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any
import venv

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))
from mathhead.output import safe_print as print  # noqa: E402


CONTRACT_ID = "MH-C-ENV-001"
CONTRACT_SHA256 = "63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87"
PROFILE_NAMES = ("status", "runtime", "core", "solver", "docs", "release")
MANIFEST_NAME = "dev_profiles.json"
RESULT_EXIT_CODES = {
    "passed": 0,
    "unsupported": 2,
    "failed": 3,
    "timed_out": 4,
    "missing": 5,
    "interrupted": 130,
}


class DevEnvironmentError(RuntimeError):
    """Expected dispatcher failure that must not cross the CLI boundary."""


@dataclass(frozen=True)
class CommandResult:
    command: str
    status: str
    exit_code: int | None
    output_sha256: str
    elapsed_seconds: float


def _root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if not (root / "pyproject.toml").is_file():
        raise DevEnvironmentError("repository-root-not-found")
    return root


def _platform_name() -> str:
    value = platform.system().casefold()
    return {"windows": "windows", "darwin": "darwin", "linux": "linux"}.get(
        value, value or "unknown"
    )


def _python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def _load_manifest(root: Path) -> dict[str, Any]:
    path = root / "tools" / MANIFEST_NAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DevEnvironmentError(f"profile-manifest-invalid:{exc}") from exc
    if not isinstance(data, dict):
        raise DevEnvironmentError("profile-manifest-not-object")
    if set(data) != {
        "schema", "contract_id", "contract_sha256", "constraints", "bootstrap_pip", "profiles"
    }:
        raise DevEnvironmentError("profile-manifest-fields-invalid")
    if data["schema"] != 1:
        raise DevEnvironmentError("profile-manifest-schema-unsupported")
    if data["contract_id"] != CONTRACT_ID or data["contract_sha256"] != CONTRACT_SHA256:
        raise DevEnvironmentError("profile-manifest-contract-binding-mismatch")
    profiles = data["profiles"]
    if not isinstance(profiles, dict) or tuple(profiles) != PROFILE_NAMES:
        raise DevEnvironmentError("profile-set-or-order-invalid")
    for name, profile in profiles.items():
        _validate_profile(name, profile)
    constraints = root / data["constraints"]
    if not constraints.is_file():
        raise DevEnvironmentError("constraints-file-missing")
    if not isinstance(data["bootstrap_pip"], str) or "==" not in data["bootstrap_pip"]:
        raise DevEnvironmentError("bootstrap-pip-not-pinned")
    return data


def _validate_profile(name: str, profile: Any) -> None:
    fields = {
        "purpose", "python", "platforms", "timeout_seconds", "install",
        "required_executables", "commands",
    }
    if not isinstance(profile, dict) or set(profile) != fields:
        raise DevEnvironmentError(f"profile-fields-invalid:{name}")
    if not isinstance(profile["purpose"], str) or not profile["purpose"].strip():
        raise DevEnvironmentError(f"profile-purpose-invalid:{name}")
    for field in ("python", "platforms", "install", "required_executables", "commands"):
        if not isinstance(profile[field], list):
            raise DevEnvironmentError(f"profile-list-invalid:{name}:{field}")
    if not profile["python"] or not all(
        isinstance(item, str) and item for item in profile["python"]
    ):
        raise DevEnvironmentError(f"profile-python-invalid:{name}")
    if not profile["platforms"] or not all(
        item in {"linux", "windows", "darwin"} for item in profile["platforms"]
    ):
        raise DevEnvironmentError(f"profile-platform-invalid:{name}")
    if not isinstance(profile["timeout_seconds"], int) or profile["timeout_seconds"] <= 0:
        raise DevEnvironmentError(f"profile-timeout-invalid:{name}")
    if not all(isinstance(item, str) and item for item in profile["install"]):
        raise DevEnvironmentError(f"profile-install-invalid:{name}")
    for requirement in profile["required_executables"]:
        if not isinstance(requirement, str) or not requirement:
            raise DevEnvironmentError(f"profile-executable-invalid:{name}")
        alternatives = requirement.split("|")
        if any(not item or not re.fullmatch(r"[A-Za-z0-9_.+-]+", item) for item in alternatives):
            raise DevEnvironmentError(f"profile-executable-invalid:{name}")
        if len(alternatives) != len(set(alternatives)):
            raise DevEnvironmentError(f"profile-executable-invalid:{name}")
    if not profile["commands"]:
        raise DevEnvironmentError(f"profile-command-set-empty:{name}")
    seen: set[str] = set()
    for command in profile["commands"]:
        if not isinstance(command, dict) or set(command) != {
            "id", "required", "timeout_seconds", "argv"
        }:
            raise DevEnvironmentError(f"profile-command-fields-invalid:{name}")
        command_id = command["id"]
        if not isinstance(command_id, str) or not command_id or command_id in seen:
            raise DevEnvironmentError(f"profile-command-id-invalid:{name}")
        if not isinstance(command["required"], bool):
            raise DevEnvironmentError(f"profile-command-required-invalid:{name}:{command_id}")
        timeout = command["timeout_seconds"]
        if not isinstance(timeout, int) or timeout <= 0 or timeout > profile["timeout_seconds"]:
            raise DevEnvironmentError(f"profile-command-timeout-invalid:{name}:{command_id}")
        argv = command["argv"]
        if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item for item in argv
        ):
            raise DevEnvironmentError(f"profile-command-argv-invalid:{name}:{command_id}")
        seen.add(command_id)


def _profile_support(profile: dict[str, Any]) -> tuple[bool, str]:
    current_platform = _platform_name()
    current_python = _python_version()
    if current_platform not in profile["platforms"]:
        return False, f"unsupported-platform:{current_platform}"
    if current_python not in profile["python"]:
        return False, f"unsupported-python:{current_python}"
    missing = [
        requirement
        for requirement in profile["required_executables"]
        if not any(shutil.which(item) is not None for item in requirement.split("|"))
    ]
    if missing:
        return False, "missing-system-executable:" + ",".join(missing)
    return True, "supported"


def _venv_python(directory: Path) -> Path:
    return directory / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _expand_argv(
    argv: list[str], *, python: Path, root: Path, temp: Path
) -> list[str]:
    values = {"python": str(python), "root": str(root), "temp": str(temp)}
    return [item.format_map(values) for item in argv]


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _run_command(
    command_id: str,
    argv: list[str],
    *,
    root: Path,
    timeout_seconds: float,
) -> tuple[CommandResult, str, str]:
    started = time.monotonic()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    popen_kwargs: dict[str, Any] = {
        "cwd": root,
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(argv, **popen_kwargs)
    except FileNotFoundError as exc:
        payload = ("\0" + str(exc)).encode("utf-8")
        result = CommandResult(
            command_id,
            "missing",
            None,
            hashlib.sha256(payload).hexdigest(),
            time.monotonic() - started,
        )
        return result, "", str(exc)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        status = "passed" if process.returncode == 0 else "failed"
        payload = (stdout + "\0" + stderr).encode("utf-8")
        result = CommandResult(
            command_id,
            status,
            process.returncode,
            hashlib.sha256(payload).hexdigest(),
            time.monotonic() - started,
        )
        return result, stdout, stderr
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        before_out = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        before_err = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stdout = before_out + (stdout or "")
        stderr = before_err + (stderr or "")
        payload = (stdout + "\0" + stderr).encode("utf-8")
        result = CommandResult(
            command_id,
            "timed_out",
            None,
            hashlib.sha256(payload).hexdigest(),
            time.monotonic() - started,
        )
        return result, stdout, stderr
    except KeyboardInterrupt:
        _terminate_process_tree(process)
        stdout, stderr = process.communicate()
        payload = ((stdout or "") + "\0" + (stderr or "")).encode("utf-8")
        result = CommandResult(
            command_id,
            "interrupted",
            130,
            hashlib.sha256(payload).hexdigest(),
            time.monotonic() - started,
        )
        return result, stdout or "", stderr or ""


def _overall_status(results: list[CommandResult]) -> str:
    for status in ("interrupted", "timed_out", "missing", "failed"):
        if any(item.status == status for item in results):
            return status
    return "passed"


def _summary(
    profile_name: str,
    status: str,
    results: list[CommandResult],
    *,
    reason: str,
) -> dict[str, Any]:
    return {
        "schema": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "profile": profile_name,
        "status": status,
        "reason": reason,
        "platform": _platform_name(),
        "interpreter": f"CPython {platform.python_version()}",
        "commands": [
            {
                "id": item.command,
                "status": item.status,
                "exit_code": item.exit_code,
                "output_sha256": item.output_sha256,
            }
            for item in results
        ],
    }


def _emit(summary: dict[str, Any], *, json_output: bool, diagnostics: list[str]) -> None:
    if json_output:
        print(json.dumps(summary, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        return
    print(
        f"dev: profile={summary['profile']} status={summary['status']} "
        f"reason={summary['reason']} platform={summary['platform']} "
        f"interpreter={summary['interpreter']}"
    )
    for result in summary["commands"]:
        suffix = "" if result["exit_code"] is None else f" exit={result['exit_code']}"
        print(f"  {result['id']}: {result['status']}{suffix}")
    for diagnostic in diagnostics:
        if diagnostic:
            print(diagnostic, end="" if diagnostic.endswith("\n") else "\n", file=sys.stderr)


def _check(
    manifest: dict[str, Any],
    profile_name: str,
    *,
    command_id: str | None,
    json_output: bool,
) -> int:
    root = _root()
    profile = manifest["profiles"][profile_name]
    supported, reason = _profile_support(profile)
    if not supported:
        summary = _summary(profile_name, "unsupported", [], reason=reason)
        _emit(summary, json_output=json_output, diagnostics=[])
        return RESULT_EXIT_CODES["unsupported"]
    commands = profile["commands"]
    if command_id is None:
        commands = [item for item in commands if item["required"]]
    else:
        commands = [item for item in commands if item["id"] == command_id]
        if not commands:
            raise DevEnvironmentError(f"unknown-profile-command:{profile_name}:{command_id}")
    results: list[CommandResult] = []
    diagnostics: list[str] = []
    profile_started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"mathhead-{profile_name}-") as temp_name:
        temp = Path(temp_name)
        for command in commands:
            remaining = profile["timeout_seconds"] - (time.monotonic() - profile_started)
            if remaining <= 0:
                result = CommandResult(command["id"], "timed_out", None, hashlib.sha256(b"\0").hexdigest(), 0.0)
                results.append(result)
                break
            argv = _expand_argv(command["argv"], python=Path(sys.executable), root=root, temp=temp)
            result, stdout, stderr = _run_command(
                command["id"],
                argv,
                root=root,
                timeout_seconds=min(command["timeout_seconds"], remaining),
            )
            results.append(result)
            if not json_output:
                if stdout:
                    diagnostics.append(stdout)
                if stderr:
                    diagnostics.append(stderr)
            if result.status != "passed":
                break
    status = _overall_status(results)
    summary = _summary(profile_name, status, results, reason=f"commands-{status}")
    _emit(summary, json_output=json_output, diagnostics=diagnostics)
    return RESULT_EXIT_CODES[status]


def _bootstrap_python(
    manifest: dict[str, Any],
    profile_name: str,
    *,
    current: bool,
    venv_path: Path | None,
    json_output: bool,
) -> int:
    root = _root()
    profile = manifest["profiles"][profile_name]
    supported, reason = _profile_support(profile)
    if not supported:
        summary = _summary(profile_name, "unsupported", [], reason=reason)
        _emit(summary, json_output=json_output, diagnostics=[])
        return RESULT_EXIT_CODES["unsupported"]
    if current and venv_path is not None:
        raise DevEnvironmentError("bootstrap-target-ambiguous")
    if current:
        target_python = Path(sys.executable)
    else:
        directory = (venv_path or root / ".venv").resolve()
        if not directory.exists():
            venv.EnvBuilder(with_pip=True, clear=False).create(directory)
        target_python = _venv_python(directory)
        if not target_python.is_file():
            raise DevEnvironmentError("selected-environment-invalid")
    if profile_name == "status":
        summary = _summary(profile_name, "passed", [], reason="stdlib-profile-no-install")
        _emit(summary, json_output=json_output, diagnostics=[])
        return 0
    install_argv = [
        str(target_python), "-m", "pip", "install", "--constraint",
        str(root / manifest["constraints"]),
    ]
    if len(profile["install"]) == 1 and profile["install"][0].startswith("."):
        install_argv.extend(("--editable", profile["install"][0]))
    else:
        install_argv.extend(profile["install"])
    commands = [
        ("bootstrap-pip", [str(target_python), "-m", "pip", "install", manifest["bootstrap_pip"]]),
        ("bootstrap-profile", install_argv),
    ]
    results: list[CommandResult] = []
    diagnostics: list[str] = []
    started = time.monotonic()
    for command_id, argv in commands:
        remaining = profile["timeout_seconds"] - (time.monotonic() - started)
        if remaining <= 0:
            results.append(CommandResult(command_id, "timed_out", None, hashlib.sha256(b"\0").hexdigest(), 0.0))
            break
        result, stdout, stderr = _run_command(
            command_id, argv, root=root, timeout_seconds=remaining
        )
        results.append(result)
        if not json_output:
            diagnostics.extend(item for item in (stdout, stderr) if item)
        if result.status != "passed":
            break
    status = _overall_status(results)
    summary = _summary(profile_name, status, results, reason=f"bootstrap-{status}")
    _emit(summary, json_output=json_output, diagnostics=diagnostics)
    return RESULT_EXIT_CODES[status]


def _install_into_clean_environment(
    manifest: dict[str, Any],
    *,
    root: Path,
    environment: Path,
    install_target: str,
    timeout_seconds: float,
) -> tuple[list[CommandResult], list[str]]:
    venv.EnvBuilder(with_pip=True, clear=True).create(environment)
    python = _venv_python(environment)
    commands = [
        ("clean-pip", [str(python), "-m", "pip", "install", manifest["bootstrap_pip"]]),
        (
            "clean-install",
            [
                str(python), "-m", "pip", "install", "--constraint",
                str(root / manifest["constraints"]), install_target,
            ],
        ),
    ]
    results: list[CommandResult] = []
    diagnostics: list[str] = []
    started = time.monotonic()
    for command_id, argv in commands:
        remaining = timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            results.append(CommandResult(command_id, "timed_out", None, hashlib.sha256(b"\0").hexdigest(), 0.0))
            break
        result, stdout, stderr = _run_command(
            command_id, argv, root=root, timeout_seconds=remaining
        )
        results.append(result)
        diagnostics.extend(item for item in (stdout, stderr) if item)
        if result.status != "passed":
            break
    return results, diagnostics


def _runtime_smokes(
    python: Path, *, root: Path, remaining: float
) -> tuple[list[CommandResult], list[str]]:
    commands = [
        ("smoke-version", [str(python), "-c", "import mathhead; print(mathhead.__version__)"]),
        (
            "smoke-entail",
            [
                str(python), "-m", "mathhead.cli", "entail", "-p", "p",
                "-p", "implies(p, q)", "-c", "q",
            ],
        ),
        (
            "smoke-mcp",
            [
                str(python), "-c",
                "import asyncio; from mathhead.server.mcp_server import mcp; "
                "n=len(asyncio.run(mcp.list_tools())); print(n); assert n >= 160",
            ],
        ),
    ]
    results: list[CommandResult] = []
    diagnostics: list[str] = []
    started = time.monotonic()
    for command_id, argv in commands:
        budget = remaining - (time.monotonic() - started)
        if budget <= 0:
            results.append(CommandResult(command_id, "timed_out", None, hashlib.sha256(b"\0").hexdigest(), 0.0))
            break
        result, stdout, stderr = _run_command(command_id, argv, root=root, timeout_seconds=budget)
        results.append(result)
        diagnostics.extend(item for item in (stdout, stderr) if item)
        if result.status != "passed":
            break
    return results, diagnostics


def _export_release_artifacts(
    *, root: Path, source: Path, requested: Path, elapsed_seconds: float
) -> CommandResult:
    destination = requested if requested.is_absolute() else root / requested
    destination = destination.resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise DevEnvironmentError("artifact-directory-outside-repository") from exc
    if destination.exists():
        raise DevEnvironmentError("artifact-directory-already-exists")
    artifacts = sorted(path for path in source.iterdir() if path.is_file())
    if not artifacts:
        raise DevEnvironmentError("release-artifacts-missing")
    try:
        destination.mkdir(parents=True)
        for artifact in artifacts:
            shutil.copy2(artifact, destination / artifact.name)
        digest = hashlib.sha256()
        for artifact in sorted(destination.iterdir()):
            digest.update(artifact.name.encode("utf-8"))
            digest.update(hashlib.sha256(artifact.read_bytes()).digest())
    except OSError as exc:
        raise DevEnvironmentError(f"artifact-export-failed:{exc}") from exc
    return CommandResult(
        "release-export", "passed", 0, digest.hexdigest(), round(elapsed_seconds, 3)
    )


def _clean_smoke(
    manifest: dict[str, Any],
    profile_name: str,
    *,
    json_output: bool,
    artifact_dir: Path | None,
) -> int:
    if profile_name not in {"runtime", "release"}:
        raise DevEnvironmentError("clean-smoke-profile-must-be-runtime-or-release")
    if artifact_dir is not None and profile_name != "release":
        raise DevEnvironmentError("artifact-export-requires-release-profile")
    root = _root()
    profile = manifest["profiles"][profile_name]
    supported, reason = _profile_support(profile)
    if not supported:
        summary = _summary(profile_name, "unsupported", [], reason=reason)
        _emit(summary, json_output=json_output, diagnostics=[])
        return RESULT_EXIT_CODES["unsupported"]
    started = time.monotonic()
    results: list[CommandResult] = []
    diagnostics: list[str] = []
    with tempfile.TemporaryDirectory(prefix=f"mathhead-{profile_name}-smoke-") as temp_name:
        temp = Path(temp_name)
        install_target = str(root)
        if profile_name == "release":
            build_env = temp / "build-env"
            build_results, build_diagnostics = _install_into_clean_environment(
                manifest,
                root=root,
                environment=build_env,
                install_target=str(root) + "[release]",
                timeout_seconds=profile["timeout_seconds"],
            )
            results.extend(build_results)
            diagnostics.extend(build_diagnostics)
            if _overall_status(results) == "passed":
                dist = temp / "dist"
                dist.mkdir()
                build_python = _venv_python(build_env)
                build_result, stdout, stderr = _run_command(
                    "release-build",
                    [str(build_python), "-m", "build", "--outdir", str(dist), str(root)],
                    root=root,
                    timeout_seconds=max(1, profile["timeout_seconds"] - (time.monotonic() - started)),
                )
                results.append(build_result)
                diagnostics.extend(item for item in (stdout, stderr) if item)
            if _overall_status(results) == "passed":
                artifacts = sorted(temp.joinpath("dist").glob("*"))
                twine_result, stdout, stderr = _run_command(
                    "release-twine-check",
                    [str(_venv_python(build_env)), "-m", "twine", "check", *map(str, artifacts)],
                    root=root,
                    timeout_seconds=max(1, profile["timeout_seconds"] - (time.monotonic() - started)),
                )
                results.append(twine_result)
                diagnostics.extend(item for item in (stdout, stderr) if item)
                wheels = sorted(temp.joinpath("dist").glob("*.whl"))
                if not wheels:
                    raise DevEnvironmentError("release-wheel-missing")
                install_target = str(wheels[0])
        if _overall_status(results) == "passed":
            runtime_env = temp / "runtime-env"
            install_results, install_diagnostics = _install_into_clean_environment(
                manifest,
                root=root,
                environment=runtime_env,
                install_target=install_target,
                timeout_seconds=max(1, profile["timeout_seconds"] - (time.monotonic() - started)),
            )
            results.extend(install_results)
            diagnostics.extend(install_diagnostics)
        if _overall_status(results) == "passed":
            smoke_results, smoke_diagnostics = _runtime_smokes(
                _venv_python(temp / "runtime-env"),
                root=root,
                remaining=max(1, profile["timeout_seconds"] - (time.monotonic() - started)),
            )
            results.extend(smoke_results)
            diagnostics.extend(smoke_diagnostics)
        if _overall_status(results) == "passed" and artifact_dir is not None:
            results.append(
                _export_release_artifacts(
                    root=root,
                    source=temp / "dist",
                    requested=artifact_dir,
                    elapsed_seconds=time.monotonic() - started,
                )
            )
    status = _overall_status(results)
    summary = _summary(profile_name, status, results, reason=f"clean-smoke-{status}")
    _emit(summary, json_output=json_output, diagnostics=[] if json_output else diagnostics)
    return RESULT_EXIT_CODES[status]


def _describe(manifest: dict[str, Any], profile_name: str, *, json_output: bool) -> int:
    profile = manifest["profiles"][profile_name]
    supported, reason = _profile_support(profile)
    payload = {
        "schema": 1,
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "profile": profile_name,
        "status": "not_run",
        "support": "supported" if supported else "unsupported",
        "reason": reason,
        "platform": _platform_name(),
        "interpreter": f"CPython {platform.python_version()}",
        "definition": profile,
    }
    if json_output:
        print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
    else:
        print(
            f"dev: profile={profile_name} status=not_run support={payload['support']} "
            f"reason={reason}"
        )
        print(profile["purpose"])
        for command in profile["commands"]:
            kind = "required" if command["required"] else "explicit-auxiliary"
            print(f"  {command['id']}: {kind}, timeout={command['timeout_seconds']}s")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true", help=argparse.SUPPRESS)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for action in ("describe", "check", "run"):
        child = subparsers.add_parser(action)
        child.add_argument("--profile", required=True, choices=PROFILE_NAMES)
        child.add_argument("--json", action="store_true")
        if action == "run":
            child.add_argument("--command", required=True)
    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--profile", required=True, choices=PROFILE_NAMES)
    bootstrap.add_argument("--json", action="store_true")
    target = bootstrap.add_mutually_exclusive_group()
    target.add_argument("--current", action="store_true")
    target.add_argument("--venv", type=Path)
    smoke = subparsers.add_parser("clean-smoke")
    smoke.add_argument("--profile", required=True, choices=("runtime", "release"))
    smoke.add_argument("--json", action="store_true")
    smoke.add_argument("--artifact-dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the accepted MH-C-ENV-001 command boundary."""
    parser = _parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        manifest = _load_manifest(_root())
        if args.action == "describe":
            return _describe(manifest, args.profile, json_output=args.json)
        if args.action == "check":
            return _check(manifest, args.profile, command_id=None, json_output=args.json)
        if args.action == "run":
            return _check(manifest, args.profile, command_id=args.command, json_output=args.json)
        if args.action == "bootstrap":
            return _bootstrap_python(
                manifest,
                args.profile,
                current=args.current,
                venv_path=args.venv,
                json_output=args.json,
            )
        if args.action == "clean-smoke":
            return _clean_smoke(
                manifest,
                args.profile,
                json_output=args.json,
                artifact_dir=args.artifact_dir,
            )
        raise DevEnvironmentError("unknown-action")
    except DevEnvironmentError as exc:
        print(f"dev: status=failed reason={exc}", file=sys.stderr)
        return RESULT_EXIT_CODES["failed"]
    except KeyboardInterrupt:
        print("dev: status=interrupted reason=user-interrupt", file=sys.stderr)
        return RESULT_EXIT_CODES["interrupted"]
    except Exception:
        if args.debug:
            traceback.print_exc()
        else:
            print("dev: status=failed reason=internal-error", file=sys.stderr)
        return RESULT_EXIT_CODES["failed"]


if __name__ == "__main__":
    raise SystemExit(main())
