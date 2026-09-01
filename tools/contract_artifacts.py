#!/usr/bin/env python3
"""Transactional contract artifact workflow for MH-C-WORKFLOW-001."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
from typing import Any, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 compatibility in the status profile.
    import tomli as tomllib


WORKFLOW_ID = "MH-C-WORKFLOW-001"
WORKFLOW_SHA256 = "99cfdf17371938af65c4203c02cbaac0bf73470e9fab59f7a6d62360fc0b7cca"
CONTRACT_ARTIFACTS_CONTRACT_ID = "MH-C-CONTRACT-ARTIFACTS-002"
CONTRACT_ARTIFACTS_CONTRACT_SHA256 = \
    "602845fedb167d06ce3999f6c245d590a43f184b3f271180cae1b8154fe7b750"
SCHEMA = "mathhead.function-contract.v1"
REPORT_SCHEMA = "mathhead.contract-report.v1"
MANIFEST_PATH = Path("docs/contracts/manifest.toml")
TRANSACTION_DIR = Path("docs/contracts/.contract-transaction")
CONTRACT_ID = re.compile(r"^MH-C-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}$")
TARGET = re.compile(
    r"^(?P<module>[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*):"
    r"(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)$"
)
SIGNATURE = re.compile(r"^(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)\(.*\) -> .+$")
MAP_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
FIELDS = {
    "schema",
    "contract_id",
    "target",
    "signature",
    "requires",
    "ensures",
    "raises",
    "effects",
    "determinism",
    "budget",
    "epistemics",
    "invariants",
    "validators",
    "supersedes",
}
CLAUSE_FIELDS = ("requires", "ensures", "raises", "invariants", "validators")
MAP_FIELDS = ("effects", "determinism", "budget", "epistemics")
MANIFEST_FIELDS = {"id", "path", "sha256", "state"}
SHELL_TOKENS = {"|", "||", "&&", ";", ">", ">>", "<", "<<"}
LOCAL_PREFIXES = ("docs/", "scripts/", "src/", "tests/", "tools/")
GRANDFATHERED_HASHES = {
    "3af2573324b7c485b8b3612cacde764e36bad341ce9ab4f83ebd819b39e7d794",
    "3d1313a252711960afb65e5973cc95839a248224a03313dc3a715a60ccb93fa2",
    "3d43a67a5d7732eca8aab19e4326abed42e12c4836942d2301e24e4ae2f65143",
    "53a9e09b58738ccdbb596ec28fa15d989d4cba66cecd46c5c97ca8d1da1f9412",
    "63be92413da8c377b20fb4aa0f86e59900cc058d186f621862b9c007146aee87",
    "69884d482ed38e34ea0b1cd1c6d3349d2dca389704ddbd385d8e493b30886965",
    "701a5f99a41f3f2226859fac98c5a8050915d88fb83111a53e5172a2b2760aad",
    "aa0fbda6f0ba42c8f154ffc21a6a35eb7386f53e47be40326e5d49e3bc5be223",
    "aa5f459b40359c446c5f6853e7a7739e91b42964fbbe97b81d5884e5c7af354d",
    "b47e07c259a8357000d57cde4238b61ea11a872113d713165515dc86a54cf210",
    "247534720fe49f89a9961196701cc12a954f5e95e12bd7b8b8c5a07318b3bf7b",
}


class ContractArtifactError(RuntimeError):
    """A classified, user-facing workflow failure."""

    def __init__(self, kind: str, detail: str, exit_code: int = 1) -> None:
        super().__init__(detail)
        self.kind = kind
        self.exit_code = exit_code


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ContractArtifactError("schema", f"value is not canonical JSON: {exc}") from exc
    return (rendered + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractArtifactError("schema", f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    except ContractArtifactError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractArtifactError("schema", f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractArtifactError("schema", f"JSON root is not an object: {path}")
    return value, raw


def _load_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ContractArtifactError("manifest", f"invalid manifest: {exc}") from exc


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ContractArtifactError("path", f"path escapes repository: {path}") from exc


def _exact_path(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ContractArtifactError("path", f"unsafe repository path: {relative}")
    current = root.resolve()
    for index, part in enumerate(candidate.parts):
        if not current.exists():
            if must_exist:
                raise ContractArtifactError("path", f"path does not exist: {relative}")
            current /= Path(*candidate.parts[index:])
            break
        try:
            names = {entry.name for entry in current.iterdir()}
        except OSError as exc:
            raise ContractArtifactError("path", f"cannot inspect path: {relative}") from exc
        if part not in names:
            aliases = sorted(name for name in names if name.casefold() == part.casefold())
            if aliases:
                raise ContractArtifactError(
                    "path", f"exact-case mismatch: {relative}; found {aliases[0]}"
                )
            if must_exist:
                raise ContractArtifactError("path", f"path does not exist: {relative}")
            current /= Path(*candidate.parts[index:])
            break
        current /= part
    try:
        current.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ContractArtifactError("path", f"path escapes repository: {relative}") from exc
    if must_exist and not current.is_file() and not current.is_dir():
        raise ContractArtifactError("path", f"path is not a file or directory: {relative}")
    return current


def _validate_scalar_map(contract_id: str, name: str, value: Any) -> None:
    if not isinstance(value, dict) or not value:
        raise ContractArtifactError("schema", f"{contract_id}: {name} must be a nonempty object")
    for key, item in value.items():
        if not isinstance(key, str) or not MAP_KEY.fullmatch(key):
            raise ContractArtifactError("schema", f"{contract_id}: invalid {name} key: {key!r}")
        if isinstance(item, bool) or not isinstance(item, (str, int, float)):
            raise ContractArtifactError("schema", f"{contract_id}: invalid {name}.{key} value")
        if isinstance(item, str) and not item.strip():
            raise ContractArtifactError("schema", f"{contract_id}: empty {name}.{key} value")
        if isinstance(item, (int, float)) and (not math.isfinite(float(item)) or item < 0):
            raise ContractArtifactError("schema", f"{contract_id}: invalid {name}.{key} number")


def validate_contract(data: dict[str, Any], *, expected_id: str | None = None) -> None:
    contract_id = data.get("contract_id")
    if set(data) != FIELDS:
        missing = sorted(FIELDS - set(data))
        unknown = sorted(set(data) - FIELDS)
        raise ContractArtifactError(
            "schema", f"contract fields differ: missing={missing}, unknown={unknown}"
        )
    if data["schema"] != SCHEMA:
        raise ContractArtifactError("schema", f"unsupported schema: {data['schema']!r}")
    if not isinstance(contract_id, str) or not CONTRACT_ID.fullmatch(contract_id):
        raise ContractArtifactError("schema", f"invalid contract ID: {contract_id!r}")
    if expected_id is not None and contract_id != expected_id:
        raise ContractArtifactError("schema", f"contract ID mismatch: {contract_id} != {expected_id}")
    target = data["target"]
    signature = data["signature"]
    target_match = TARGET.fullmatch(target) if isinstance(target, str) else None
    signature_match = SIGNATURE.fullmatch(signature) if isinstance(signature, str) else None
    if target_match is None or signature_match is None:
        raise ContractArtifactError("schema", f"{contract_id}: invalid target or signature")
    if target_match.group("symbol") != signature_match.group("symbol"):
        raise ContractArtifactError("schema", f"{contract_id}: target/signature symbol mismatch")
    for name in CLAUSE_FIELDS:
        value = data[name]
        if not isinstance(value, list) or not value:
            raise ContractArtifactError("schema", f"{contract_id}: {name} must be nonempty")
        if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in value):
            raise ContractArtifactError("schema", f"{contract_id}: invalid {name} clause")
        if len(value) != len(set(value)):
            raise ContractArtifactError("schema", f"{contract_id}: duplicate {name} clause")
    for name in MAP_FIELDS:
        _validate_scalar_map(contract_id, name, data[name])
    supersedes = data["supersedes"]
    if supersedes is not None and (
        not isinstance(supersedes, str)
        or not CONTRACT_ID.fullmatch(supersedes)
        or supersedes == contract_id
    ):
        raise ContractArtifactError("schema", f"{contract_id}: invalid supersedes identity")


def _assert_decidable_consistency(data: dict[str, Any]) -> None:
    for name in ("requires", "ensures", "invariants"):
        clauses = set(data[name])
        for clause in clauses:
            if clause.startswith("NOT: ") and clause[5:] in clauses:
                raise ContractArtifactError(
                    "unsatisfiable", f"{data['contract_id']}: contradiction in {name}: {clause[5:]}"
                )


def _validator_references(root: Path, command: str) -> list[str]:
    if any(token in command for token in ("\n", "\r", "|", "&", ";", "<", ">", "`", "$(")):
        raise ContractArtifactError("validator", f"validator command contains shell syntax: {command}")
    try:
        argv = shlex.split(command, posix=True)
    except ValueError as exc:
        raise ContractArtifactError("validator", f"validator command cannot be parsed: {command}") from exc
    if not argv or argv[0] != "python" or any(token in SHELL_TOKENS for token in argv):
        raise ContractArtifactError("validator", f"validator command is not direct Python: {command}")
    references: list[str] = []
    for token in argv[1:]:
        candidate = token.split("::", 1)[0]
        if candidate.startswith(LOCAL_PREFIXES):
            _exact_path(root, candidate)
            references.append(candidate)
    return sorted(set(references))


def _manifest(root: Path) -> tuple[list[dict[str, Any]], bytes]:
    path = root / MANIFEST_PATH
    raw = path.read_bytes()
    data = _load_toml(path)
    records = data.get("contracts")
    if set(data) != {"schema", "contracts"} or data.get("schema") != 1 or not isinstance(records, list):
        raise ContractArtifactError("manifest", "manifest must contain schema 1 and contracts")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != MANIFEST_FIELDS:
            raise ContractArtifactError("manifest", "manifest record fields drift")
        contract_id = record["id"]
        relative = record["path"]
        digest = record["sha256"]
        state = record["state"]
        if not isinstance(contract_id, str) or not re.fullmatch(r"^MH-C-[A-Z0-9-]+$", contract_id):
            raise ContractArtifactError("manifest", f"invalid manifest ID: {contract_id!r}")
        if not isinstance(relative, str) or not relative:
            raise ContractArtifactError("manifest", f"invalid manifest path: {contract_id}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ContractArtifactError("manifest", f"invalid manifest hash: {contract_id}")
        if contract_id in seen_ids or relative in seen_paths:
            raise ContractArtifactError("manifest", f"duplicate manifest identity: {contract_id}")
        if state not in {"proposed", "accepted"}:
            raise ContractArtifactError("manifest", f"invalid state: {contract_id}")
        if (state == "proposed") != ("/proposed/" in f"/{relative}"):
            raise ContractArtifactError("manifest", f"state/path disagreement: {contract_id}")
        artifact = _exact_path(root, relative)
        if not artifact.is_file() or _sha(artifact.read_bytes()) != digest:
            raise ContractArtifactError("manifest", f"artifact hash drift: {contract_id}")
        seen_ids.add(contract_id)
        seen_paths.add(relative)
    return records, raw


def _render_manifest(records: list[dict[str, Any]]) -> bytes:
    lines = ["schema = 1", ""]
    for record in records:
        lines.extend(
            [
                "[[contracts]]",
                f'id = {json.dumps(record["id"])}',
                f'path = {json.dumps(record["path"])}',
                f'sha256 = {json.dumps(record["sha256"])}',
                f'state = {json.dumps(record["state"])}',
                "",
            ]
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _report(body: dict[str, Any]) -> dict[str, Any]:
    if "report_sha256" in body:
        raise ContractArtifactError("report", "report body already has an identity")
    identity = _sha(_canonical_bytes(body))
    return {**body, "report_sha256": identity}


def _validate_report(data: dict[str, Any]) -> None:
    identity = data.get("report_sha256")
    if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{64}", identity):
        raise ContractArtifactError("report", "report identity missing")
    body = {key: value for key, value in data.items() if key != "report_sha256"}
    if _sha(_canonical_bytes(body)) != identity:
        raise ContractArtifactError("report", "report identity drift")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp, 0o644)
        except OSError:
            pass
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def _cleanup_transaction(directory: Path, journal: dict[str, Any]) -> None:
    for item in journal["files"]:
        (directory / item["backup"]).unlink(missing_ok=True)
        (directory / item["next"]).unlink(missing_ok=True)
    (directory / "journal.json").unlink(missing_ok=True)
    try:
        directory.rmdir()
    except OSError as exc:
        raise ContractArtifactError("transaction", "transaction directory cleanup failed", 6) from exc


def recover(root: Path) -> bool:
    directory = root / TRANSACTION_DIR
    if not directory.exists():
        return False
    journal_path = directory / "journal.json"
    data, raw = _load_json(journal_path)
    if raw != _canonical_bytes(data) or set(data) != {"schema", "phase", "files"}:
        raise ContractArtifactError("transaction", "transaction journal is invalid", 6)
    if data["schema"] != 1 or data["phase"] not in {"prepared", "committed"}:
        raise ContractArtifactError("transaction", "transaction journal state is invalid", 6)
    if data["phase"] == "prepared":
        for item in reversed(data["files"]):
            target = _exact_path(root, item["target"], must_exist=False)
            backup = directory / item["backup"]
            if item["existed"]:
                if not backup.is_file() or _sha(backup.read_bytes()) != item["before_sha256"]:
                    raise ContractArtifactError("transaction", "transaction backup drift", 6)
                os.replace(backup, target)
            else:
                target.unlink(missing_ok=True)
    _cleanup_transaction(directory, data)
    return True


def _transaction(root: Path, writes: dict[Path, bytes]) -> None:
    recover(root)
    directory = root / TRANSACTION_DIR
    try:
        directory.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        raise ContractArtifactError("transaction", "cannot create transaction directory", 6) from exc
    files: list[dict[str, Any]] = []
    try:
        for index, (target, payload) in enumerate(writes.items()):
            relative = _relative(root, target)
            target.parent.mkdir(parents=True, exist_ok=True)
            backup_name = f"backup-{index}"
            next_name = f"next-{index}"
            existed = target.is_file()
            before = target.read_bytes() if existed else b""
            if existed:
                (directory / backup_name).write_bytes(before)
            (directory / next_name).write_bytes(payload)
            files.append(
                {
                    "target": relative,
                    "existed": existed,
                    "before_sha256": _sha(before) if existed else None,
                    "after_sha256": _sha(payload),
                    "backup": backup_name,
                    "next": next_name,
                }
            )
        journal = {"schema": 1, "phase": "prepared", "files": files}
        _atomic_write(directory / "journal.json", _canonical_bytes(journal))
        for item in files:
            target = _exact_path(root, item["target"], must_exist=False)
            os.replace(directory / item["next"], target)
        committed = {**journal, "phase": "committed"}
        _atomic_write(directory / "journal.json", _canonical_bytes(committed))
        _cleanup_transaction(directory, committed)
    except BaseException:
        if (directory / "journal.json").exists():
            recover(root)
        else:
            for path in directory.iterdir():
                path.unlink(missing_ok=True)
            directory.rmdir()
        raise


def _emit_or_compare(
    report: dict[str, Any], *, report_path: Path | None, check_path: Path | None
) -> None:
    payload = _canonical_bytes(report)
    if report_path is not None:
        _atomic_write(report_path, payload)
        print(f"contract-artifacts: report updated: {report_path}")
    elif check_path is not None:
        try:
            current = check_path.read_bytes()
        except OSError as exc:
            raise ContractArtifactError("report", f"report missing: {check_path}") from exc
        if current != payload:
            raise ContractArtifactError("report", f"deterministic report drift: {check_path}")
        print(f"contract-artifacts: report current: {check_path}")
    else:
        sys.stdout.buffer.write(payload)


def _find_record(records: list[dict[str, Any]], contract_id: str) -> dict[str, Any]:
    matches = [record for record in records if record["id"] == contract_id]
    if len(matches) != 1:
        raise ContractArtifactError("manifest", f"contract manifest binding missing: {contract_id}")
    return matches[0]


def propose(root: Path, input_path: Path) -> dict[str, Any]:
    input_path = _exact_path(root, _relative(root, input_path))
    data, _raw = _load_json(input_path)
    validate_contract(data)
    _assert_decidable_consistency(data)
    records, _manifest_raw = _manifest(root)
    contract_id = data["contract_id"]
    if any(record["id"] == contract_id for record in records):
        raise ContractArtifactError("proposal", f"contract ID already registered: {contract_id}")
    payload = _canonical_bytes(data)
    relative = f"docs/contracts/proposed/{contract_id}.json"
    target = _exact_path(root, relative, must_exist=False)
    if target.exists():
        raise ContractArtifactError("proposal", f"proposal path already exists: {relative}")
    record = {
        "id": contract_id,
        "path": relative,
        "sha256": _sha(payload),
        "state": "proposed",
    }
    next_records = [*records, record]
    _transaction(root, {target: payload, root / MANIFEST_PATH: _render_manifest(next_records)})
    return _report(
        {
            "schema": REPORT_SCHEMA,
            "workflow": {"id": WORKFLOW_ID, "sha256": WORKFLOW_SHA256},
            "operation": "propose",
            "status": "proposed",
            "contract": {"id": contract_id, "sha256": record["sha256"]},
            "artifact": relative,
        }
    )


def _supersession_check(data: dict[str, Any], records: list[dict[str, Any]], root: Path) -> None:
    old_id = data["supersedes"]
    if old_id is None:
        return
    old = _find_record(records, old_id)
    if old["state"] != "accepted":
        raise ContractArtifactError("supersession", f"superseded contract is not accepted: {old_id}")
    old_data, _raw = _load_json(root / old["path"])
    validate_contract(old_data, expected_id=old_id)
    new_family, new_version = data["contract_id"].rsplit("-", 1)
    old_family, old_version = old_id.rsplit("-", 1)
    if new_family != old_family or int(new_version) <= int(old_version):
        raise ContractArtifactError("supersession", "contract version does not advance its family")
    if old_data["target"] != data["target"]:
        raise ContractArtifactError("supersession", "superseding contract target drift")


def _active_target_check(data: dict[str, Any], records: list[dict[str, Any]], root: Path) -> None:
    superseded = {
        accepted["supersedes"]
        for record in records
        if record["state"] == "accepted" and record["path"].endswith(".json")
        for accepted, _raw in [_load_json(root / record["path"])]
        if accepted.get("supersedes") is not None
    }
    conflicts: list[str] = []
    for record in records:
        if (
            record["state"] != "accepted"
            or not record["path"].endswith(".json")
            or record["id"] in superseded
        ):
            continue
        accepted, _raw = _load_json(root / record["path"])
        validate_contract(accepted, expected_id=record["id"])
        if accepted["target"] == data["target"] and record["id"] != data["supersedes"]:
            conflicts.append(record["id"])
    if conflicts:
        raise ContractArtifactError(
            "supersession",
            f"active target already governed by {', '.join(sorted(conflicts))}",
        )


def prescreen(root: Path, proposal_path: Path) -> dict[str, Any]:
    proposal_path = _exact_path(root, _relative(root, proposal_path))
    data, raw = _load_json(proposal_path)
    validate_contract(data)
    if raw != _canonical_bytes(data):
        raise ContractArtifactError("canonical", "proposal was not created by canonical tooling")
    _assert_decidable_consistency(data)
    records, _manifest_raw = _manifest(root)
    record = _find_record(records, data["contract_id"])
    relative = _relative(root, proposal_path)
    if record != {
        "id": data["contract_id"],
        "path": relative,
        "sha256": _sha(raw),
        "state": "proposed",
    }:
        raise ContractArtifactError("proposal", "proposal manifest binding drift")
    _supersession_check(data, records, root)
    _active_target_check(data, records, root)
    validator_checks = []
    for command in data["validators"]:
        references = _validator_references(root, command)
        validator_checks.append(
            {"command": command, "references": references, "status": "present"}
        )
    return _report(
        {
            "schema": REPORT_SCHEMA,
            "workflow": {"id": WORKFLOW_ID, "sha256": WORKFLOW_SHA256},
            "operation": "prescreen",
            "status": "passed",
            "contract": {
                "id": data["contract_id"],
                "sha256": _sha(raw),
                "semantic_sha256": _sha(_canonical_bytes(data)),
            },
            "proposal": relative,
            "checks": [
                {"id": "strict-schema", "status": "passed"},
                {"id": "canonical-json", "status": "passed"},
                {"id": "manifest-binding", "status": "passed"},
                {"id": "decidable-consistency", "status": "passed"},
                {"id": "supersession", "status": "passed"},
                {"id": "validator-references", "status": "passed"},
            ],
            "validators": validator_checks,
            "acceptance": "not_granted",
        }
    )


def accept(
    root: Path,
    proposal_path: Path,
    prescreen_path: Path,
    expected_sha256: str,
    authority: str,
    acceptance_path: Path | None = None,
) -> dict[str, Any]:
    proposal_path = _exact_path(root, _relative(root, proposal_path))
    prescreen_path = _exact_path(root, _relative(root, prescreen_path))
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ContractArtifactError("acceptance", "expected SHA-256 is invalid")
    if not authority.strip() or authority != authority.strip() or len(authority) > 128:
        raise ContractArtifactError("acceptance", "acceptance authority is invalid")
    data, raw = _load_json(proposal_path)
    validate_contract(data)
    if raw != _canonical_bytes(data) or _sha(raw) != expected_sha256:
        raise ContractArtifactError("acceptance", "proposal bytes do not match expected SHA-256")
    screen, screen_raw = _load_json(prescreen_path)
    _validate_report(screen)
    if screen_raw != _canonical_bytes(screen):
        raise ContractArtifactError("acceptance", "pre-screen report is not canonical")
    current_screen = prescreen(root, proposal_path)
    if screen_raw != _canonical_bytes(current_screen):
        raise ContractArtifactError("acceptance", "pre-screen report is stale or tampered")
    if screen.get("operation") != "prescreen" or screen.get("status") != "passed":
        raise ContractArtifactError("acceptance", "pre-screen report did not pass")
    if screen.get("acceptance") != "not_granted" or screen.get("contract", {}).get("sha256") != expected_sha256:
        raise ContractArtifactError("acceptance", "pre-screen report binding drift")
    records, manifest_raw = _manifest(root)
    record = _find_record(records, data["contract_id"])
    relative_proposal = _relative(root, proposal_path)
    if record != {
        "id": data["contract_id"],
        "path": relative_proposal,
        "sha256": expected_sha256,
        "state": "proposed",
    }:
        raise ContractArtifactError("acceptance", "proposal is not in the proposed state")
    _supersession_check(data, records, root)
    _active_target_check(data, records, root)
    accepted_relative = f"docs/contracts/{data['contract_id']}.json"
    accepted_target = _exact_path(root, accepted_relative, must_exist=False)
    if accepted_target.exists():
        raise ContractArtifactError("acceptance", "accepted artifact already exists")
    next_records = [
        {
            **item,
            "path": accepted_relative,
            "state": "accepted",
        } if item["id"] == data["contract_id"] else item
        for item in records
    ]
    next_manifest = _render_manifest(next_records)
    report_target = acceptance_path or root / (
        f"docs/contracts/reports/{data['contract_id']}.acceptance.json"
    )
    acceptance = _report(
        {
            "schema": REPORT_SCHEMA,
            "workflow": {"id": WORKFLOW_ID, "sha256": WORKFLOW_SHA256},
            "operation": "accept",
            "status": "accepted",
            "contract": {"id": data["contract_id"], "sha256": expected_sha256},
            "proposal": relative_proposal,
            "accepted_artifact": accepted_relative,
            "prescreen_report": {
                "path": _relative(root, prescreen_path),
                "sha256": _sha(screen_raw),
                "report_sha256": screen["report_sha256"],
            },
            "authority": authority,
            "manifest_transition": {
                "before_sha256": _sha(manifest_raw),
                "after_sha256": _sha(next_manifest),
            },
        }
    )
    _transaction(
        root,
        {
            accepted_target: raw,
            report_target: _canonical_bytes(acceptance),
            root / MANIFEST_PATH: next_manifest,
        },
    )
    return acceptance


def _module_path(root: Path, module: str) -> Path | None:
    parts = module.split(".")
    bases = [root / "src", root]
    for base in bases:
        file_path = base.joinpath(*parts).with_suffix(".py")
        package_path = base.joinpath(*parts, "__init__.py")
        if file_path.is_file():
            return file_path
        if package_path.is_file():
            return package_path
    return None


def _render_argument(argument: ast.arg, default: ast.expr | None) -> str:
    text = argument.arg
    if argument.annotation is not None:
        text += f": {ast.unparse(argument.annotation)}"
    if default is not None:
        text += f" = {ast.unparse(default)}"
    return text


def _render_signature(node: ast.FunctionDef | ast.AsyncFunctionDef, *, name: str | None = None) -> str:
    arguments = node.args
    positional = [*arguments.posonlyargs, *arguments.args]
    defaults: list[ast.expr | None] = [None] * (len(positional) - len(arguments.defaults))
    defaults.extend(arguments.defaults)
    parts = [_render_argument(argument, default) for argument, default in zip(positional, defaults)]
    if arguments.posonlyargs:
        parts.insert(len(arguments.posonlyargs), "/")
    if arguments.vararg is not None:
        parts.append("*" + _render_argument(arguments.vararg, None))
    elif arguments.kwonlyargs:
        parts.append("*")
    parts.extend(
        _render_argument(argument, default)
        for argument, default in zip(arguments.kwonlyargs, arguments.kw_defaults)
    )
    if arguments.kwarg is not None:
        parts.append("**" + _render_argument(arguments.kwarg, None))
    returns = f" -> {ast.unparse(node.returns)}" if node.returns is not None else ""
    return f"{name or node.name}({', '.join(parts)}){returns}"


def _binding(root: Path, data: dict[str, Any], digest: str, *, required: bool) -> dict[str, Any]:
    match = TARGET.fullmatch(data["target"])
    assert match is not None
    source = _module_path(root, match.group("module"))
    if source is None:
        if required:
            raise ContractArtifactError("binding", f"implementation module missing: {data['target']}", 3)
        return {"status": "not_implemented", "target": data["target"]}
    try:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ContractArtifactError("binding", f"implementation source invalid: {source}", 3) from exc
    symbol = match.group("symbol")
    functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == symbol
    ]
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == symbol]
    if len(functions) + len(classes) == 0:
        if required:
            raise ContractArtifactError("binding", f"implementation symbol missing: {data['target']}", 3)
        return {"status": "not_implemented", "target": data["target"], "source": _relative(root, source)}
    if len(functions) + len(classes) != 1:
        raise ContractArtifactError("binding", f"implementation symbol ambiguous: {data['target']}", 3)
    if functions:
        actual_signature = _render_signature(functions[0])
    else:
        constructors = [
            node for node in classes[0].body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "__init__"
        ]
        if len(constructors) != 1:
            if required:
                raise ContractArtifactError("binding", f"class constructor missing: {data['target']}", 3)
            return {"status": "not_implemented", "target": data["target"], "source": _relative(root, source)}
        constructor = constructors[0]
        arguments = constructor.args
        positional = [*arguments.posonlyargs, *arguments.args]
        if not positional or positional[0].arg not in {"self", "cls"}:
            raise ContractArtifactError(
                "binding", f"class constructor receiver invalid: {data['target']}", 3
            )
        posonlyargs = list(arguments.posonlyargs)
        regular_args = list(arguments.args)
        if posonlyargs:
            posonlyargs = posonlyargs[1:]
        else:
            regular_args = regular_args[1:]
        copied = ast.FunctionDef(
            name=constructor.name,
            args=ast.arguments(
                posonlyargs=posonlyargs,
                args=regular_args,
                vararg=arguments.vararg,
                kwonlyargs=list(arguments.kwonlyargs),
                kw_defaults=list(arguments.kw_defaults),
                kwarg=arguments.kwarg,
                defaults=list(arguments.defaults),
            ),
            body=[],
            decorator_list=[],
            returns=constructor.returns,
            type_comment=None,
        )
        actual_signature = _render_signature(copied, name=symbol)
    if actual_signature != data["signature"]:
        raise ContractArtifactError(
            "binding", f"signature drift: {data['contract_id']}: {actual_signature}", 3
        )
    metadata: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            if not isinstance(value, str):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    if target.id in metadata:
                        raise ContractArtifactError(
                            "binding", f"implementation metadata ambiguous: {target.id}", 3
                        )
                    metadata[target.id] = value
    bindings = [
        name
        for name, value in metadata.items()
        if name.endswith("CONTRACT_ID")
        and value == data["contract_id"]
        and metadata.get(name[:-2] + "SHA256") == digest
    ]
    if len(bindings) != 1:
        raise ContractArtifactError("binding", f"implementation hash binding missing: {data['contract_id']}", 3)
    return {
        "status": "passed",
        "target": data["target"],
        "signature": actual_signature,
        "source": _relative(root, source),
    }


def _run_validators(root: Path, data: dict[str, Any]) -> list[dict[str, Any]]:
    configured = data["validators"]
    budget = data["budget"].get("total_seconds", 300)
    total_seconds = float(budget) if isinstance(budget, (int, float)) else 300.0
    total_seconds = min(max(total_seconds, 1.0), 1200.0)
    started = time.monotonic()
    results: list[dict[str, Any]] = []
    for command in configured:
        references = _validator_references(root, command)
        argv = shlex.split(command, posix=True)
        if len(argv) > 1 and argv[1] in {
            "tools/project_status.py",
            "tools/contract_artifacts.py",
        }:
            results.append(
                {"command": command, "references": references, "execution": "delegated_recursive"}
            )
            continue
        remaining = total_seconds - (time.monotonic() - started)
        if remaining <= 0:
            raise ContractArtifactError("validator-timeout", f"validator budget exhausted: {command}", 5)
        argv[0] = sys.executable
        try:
            process = subprocess.Popen(
                argv,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.communicate(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            process.terminate()
            try:
                process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            raise ContractArtifactError("validator-timeout", f"validator timed out: {command}", 5) from exc
        except OSError as exc:
            raise ContractArtifactError("validator", f"validator could not start: {command}", 4) from exc
        result = {
            "command": command,
            "references": references,
            "execution": "passed" if process.returncode == 0 else "failed",
            "exit_code": process.returncode,
        }
        results.append(result)
        if process.returncode != 0:
            raise ContractArtifactError("validator", f"validator failed: {command}", 4)
    return results


def verify(
    root: Path,
    *,
    contract_id: str | None,
    run_validators: bool,
    require_bound: bool,
) -> dict[str, Any]:
    workflow_path = root / "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md"
    if _sha(workflow_path.read_bytes()) != WORKFLOW_SHA256:
        raise ContractArtifactError("workflow", "accepted workflow contract hash drift")
    records, manifest_raw = _manifest(root)
    selected = records if contract_id is None else [_find_record(records, contract_id)]
    accepted_data: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["state"] != "accepted" or not record["path"].endswith(".json"):
            continue
        data, _raw = _load_json(root / record["path"])
        validate_contract(data, expected_id=record["id"])
        accepted_data[record["id"]] = data
    superseded_by: dict[str, str] = {}
    for data in accepted_data.values():
        old = data["supersedes"]
        if old is not None:
            if old not in accepted_data or old in superseded_by:
                raise ContractArtifactError("supersession", f"supersession graph invalid: {old}")
            superseded_by[old] = data["contract_id"]
    active_targets: dict[str, str] = {}
    for accepted_id, data in accepted_data.items():
        if accepted_id in superseded_by:
            continue
        target = data["target"]
        if target in active_targets:
            raise ContractArtifactError(
                "supersession", f"multiple active contracts target {target}: {active_targets[target]}"
            )
        active_targets[target] = accepted_id
    outputs: list[dict[str, Any]] = []
    for record in selected:
        path = root / record["path"]
        entry: dict[str, Any] = {
            "id": record["id"],
            "state": record["state"],
            "path": record["path"],
            "artifact_sha256": record["sha256"],
        }
        if path.suffix != ".json":
            entry.update({"kind": "document", "binding": {"status": "not_applicable"}})
            outputs.append(entry)
            continue
        data, raw = _load_json(path)
        validate_contract(data, expected_id=record["id"])
        entry["kind"] = "function"
        entry["semantic_sha256"] = _sha(_canonical_bytes(data))
        entry["canonical"] = raw == _canonical_bytes(data)
        entry["grandfathered"] = record["sha256"] in GRANDFATHERED_HASHES
        if not entry["canonical"] and not entry["grandfathered"]:
            raise ContractArtifactError(
                "canonical", f"accepted artifact is not canonical: {record['id']}"
            )
        if record["state"] == "proposed":
            if not entry["canonical"]:
                raise ContractArtifactError("canonical", f"active proposal is not canonical: {record['id']}")
            entry["binding"] = {"status": "not_applicable"}
        elif record["id"] in superseded_by:
            entry["superseded_by"] = superseded_by[record["id"]]
            entry["binding"] = {"status": "superseded"}
        else:
            entry["binding"] = _binding(root, data, record["sha256"], required=require_bound)
        if record["state"] == "accepted":
            proposal = root / f"docs/contracts/proposed/{record['id']}.json"
            if not proposal.is_file() or proposal.read_bytes() != raw:
                raise ContractArtifactError(
                    "proposal", f"accepted/proposed byte separation drift: {record['id']}"
                )
        if run_validators and record["id"] in superseded_by:
            entry["validators"] = [
                {
                    "command": command,
                    "references": _validator_references(root, command),
                    "execution": "superseded_not_run",
                }
                for command in data["validators"]
            ]
        elif run_validators:
            entry["validators"] = _run_validators(root, data)
        else:
            entry["validators"] = [
                {
                    "command": command,
                    "references": _validator_references(root, command),
                    "execution": "not_run",
                }
                for command in data["validators"]
            ]
        outputs.append(entry)
    return _report(
        {
            "schema": REPORT_SCHEMA,
            "workflow": {"id": WORKFLOW_ID, "sha256": WORKFLOW_SHA256},
            "operation": "verify",
            "status": "passed",
            "manifest_sha256": _sha(manifest_raw),
            "selection": contract_id or "all",
            "validator_execution": "run" if run_validators else "not_run",
            "require_bound": require_bound,
            "contracts": outputs,
        }
    )


def _root(value: Path) -> Path:
    root = value.resolve()
    if not (root / MANIFEST_PATH).is_file():
        raise argparse.ArgumentTypeError(f"not a MathHead contract root: {root}")
    return root


def _argument_path(root: Path, value: Path, *, must_exist: bool) -> Path:
    candidate = value if value.is_absolute() else root / value
    return _exact_path(root, _relative(root, candidate), must_exist=must_exist)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    subparsers = parser.add_subparsers(dest="command", required=True)

    proposal = subparsers.add_parser("propose")
    proposal.add_argument("--input", type=Path, required=True)

    screen = subparsers.add_parser("prescreen")
    screen.add_argument("--proposal", type=Path, required=True)
    screen_output = screen.add_mutually_exclusive_group()
    screen_output.add_argument("--report", type=Path)
    screen_output.add_argument("--check-report", type=Path)

    acceptance = subparsers.add_parser("accept")
    acceptance.add_argument("--proposal", type=Path, required=True)
    acceptance.add_argument("--prescreen-report", type=Path, required=True)
    acceptance.add_argument("--expected-sha256", required=True)
    acceptance.add_argument("--authority", required=True)
    acceptance.add_argument("--acceptance-report", type=Path)

    verification = subparsers.add_parser("verify")
    selection = verification.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--contract")
    verification.add_argument("--run-validators", action="store_true")
    verification.add_argument("--require-bound", action="store_true")
    verify_output = verification.add_mutually_exclusive_group()
    verify_output.add_argument("--report", type=Path)
    verify_output.add_argument("--check-report", type=Path)

    subparsers.add_parser("recover")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        if not (root / MANIFEST_PATH).is_file():
            raise ContractArtifactError("path", f"contract repository root is invalid: {root}")
        if args.command == "recover":
            changed = recover(root)
            print(f"contract-artifacts recover: {'recovered' if changed else 'clean'}")
            return 0
        if (root / TRANSACTION_DIR).exists():
            raise ContractArtifactError("transaction", "unfinished transaction requires recover", 6)
        if args.command == "propose":
            result = propose(root, _argument_path(root, args.input, must_exist=True))
            sys.stdout.buffer.write(_canonical_bytes(result))
        elif args.command == "prescreen":
            result = prescreen(root, _argument_path(root, args.proposal, must_exist=True))
            _emit_or_compare(
                result,
                report_path=(
                    _argument_path(root, args.report, must_exist=False) if args.report else None
                ),
                check_path=(
                    _argument_path(root, args.check_report, must_exist=True)
                    if args.check_report
                    else None
                ),
            )
        elif args.command == "accept":
            result = accept(
                root,
                _argument_path(root, args.proposal, must_exist=True),
                _argument_path(root, args.prescreen_report, must_exist=True),
                args.expected_sha256,
                args.authority,
                (
                    _argument_path(root, args.acceptance_report, must_exist=False)
                    if args.acceptance_report
                    else None
                ),
            )
            sys.stdout.buffer.write(_canonical_bytes(result))
        else:
            result = verify(
                root,
                contract_id=None if args.all else args.contract,
                run_validators=args.run_validators,
                require_bound=args.require_bound,
            )
            _emit_or_compare(
                result,
                report_path=(
                    _argument_path(root, args.report, must_exist=False) if args.report else None
                ),
                check_path=(
                    _argument_path(root, args.check_report, must_exist=True)
                    if args.check_report
                    else None
                ),
            )
        return 0
    except ContractArtifactError as exc:
        print(f"contract-artifacts: {exc.kind}: {exc}", file=sys.stderr)
        return exc.exit_code
    except Exception as exc:
        print(f"contract-artifacts: internal: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
