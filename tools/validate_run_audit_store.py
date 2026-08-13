#!/usr/bin/env python3
"""Independently validate the MH-054 append-only run-audit store.

Production audit/store modules run only in isolated child processes.  This
validator inspects the resulting filesystem and canonical bytes independently,
then exercises fresh load, relocation, idempotent persistence, orphan handling,
and corrupt-state rejection.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
from typing import Any, NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/run_audit_store.py"
REPORT = ROOT / "docs/planning/reports/run-audit-store-v6.json"
CONTRACT_ID = "MH-C-RUN-AUDIT-STORE-006"
CONTRACT_SHA256 = "327f5d55b86433b803f22ba019b8adf5fe3a4bf8bc0dbdf4b1472c276bedff5e"
AUDIT_SHA256 = "42e6cfcb704bc1b40b8c0a9143c4bfdaa34b0228a85621d9464e28c8481a39a7"
REPLAY_SHA256 = "cc1170556ddba8bf4232fff5dc14f1bdb95d7d558540d5066fb4379b9c1c2cde"
SCHEMAS = {
    "run-audit-store-record-v3.schema.json": "0d405720427b8128c36088faffa78a5e8b4967dcafd7883503f7b02302cc3156",
    "run-audit-store-result-v6.schema.json": "e59f14e6c98fb2986a80555c1c6e6315f56a8cef4da50499ab4e1cc796098216",
}
REPORT_SCHEMA = "mathhead.run-audit-store-validation-report.v6"
RECORD_SCHEMA = "mathhead.run-audit-store-record.v3"
RESULT_SCHEMA = "mathhead.run-audit-store-result.v6"
STORE_NAMESPACE = ".mathhead-run-audit-store-v6"
DIGEST = re.compile(r"[0-9a-f]{64}")


class StoreValidationError(RuntimeError):
    """An independent store identity, layout, or negative check failed."""


class _DuplicateKey(ValueError):
    pass


def _fail(detail: str) -> NoReturn:
    raise StoreValidationError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _parse(raw: bytes, label: str, *, canonical: bool = True) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        _fail(f"{label} is not strict JSON: {type(exc).__name__}")
    if type(value) is not dict or (canonical and raw != _canonical(value)):
        _fail(f"{label} is not one canonical object")
    return value


def _digest(value: object, label: str) -> str:
    if type(value) is not str or DIGEST.fullmatch(value) is None:
        _fail(f"{label} is not a full lowercase SHA-256")
    return value


def _self_hash(value: dict[str, Any], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _contract_checks() -> dict[str, object]:
    accepted = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
    proposed = ROOT / "docs/contracts/proposed" / f"{CONTRACT_ID}.json"
    raw = accepted.read_bytes()
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text())
    bindings = {
        str(item["id"]): str(item["sha256"])
        for item in manifest.get("contracts", [])
        if item.get("state") == "accepted"
    }
    if (
        _sha(raw) != CONTRACT_SHA256
        or raw != proposed.read_bytes()
        or raw != _canonical(json.loads(raw))
        or bindings.get(CONTRACT_ID) != CONTRACT_SHA256
        or bindings.get("MH-C-AUDITED-RUN-005") != AUDIT_SHA256
        or bindings.get("MH-C-RUN-AUDIT-REPLAY-005") != REPLAY_SHA256
    ):
        _fail("accepted store/audit/replay contract binding drift")
    schema_report: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        schema = _parse(path.read_bytes(), name, canonical=False)
        if (
            _sha(path.read_bytes()) != digest
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or set(schema.get("required", [])) != set(schema.get("properties", {}))
        ):
            _fail(f"closed store schema binding drift: {name}")
        schema_report[name] = digest
    return {"contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256}, "schemas": schema_report}


def _source_checks() -> dict[str, object]:
    source = SOURCE.read_text()
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    required = {
        "persist_run_audit": ["root", "bundle"],
        "load_run_audit": ["root", "manifest_sha256"],
        "list_run_audits": ["root"],
        "run_audit_store_result_bytes": ["value"],
    }
    for name, parameters in required.items():
        node = functions.get(name)
        if node is None or [item.arg for item in node.args.args] != parameters:
            _fail(f"public store signature drift: {name}")
    attribute_calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    if attribute_calls & {"rmdir", "rmtree", "rename", "replace", "remove"}:
        _fail("store source gained a committed-state deletion or overwrite call")
    name_calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if name_calls & {"eval", "exec", "__import__"}:
        _fail("store source gained dynamic execution")
    descriptor_helpers = {
        "_open_root",
        "_validate_root_path",
        "_guard_root",
        "_open_child_directory",
        "_record_bytes_from_validated",
        "_read_bounded",
        "_write_immutable_locked",
        "_quarantine_uncommitted",
        "_fsync_directory",
    }
    if not descriptor_helpers <= set(functions):
        _fail("store source lost a pinned descriptor helper")
    for owner in ("_open_root", "persist_run_audit"):
        helper_calls = {
            node.func.id: node.lineno
            for node in ast.walk(functions[owner])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"_validate_root_path", "_descriptor_store_supported"}
        }
        if (
            set(helper_calls) != {"_validate_root_path", "_descriptor_store_supported"}
            or helper_calls["_validate_root_path"]
            >= helper_calls["_descriptor_store_supported"]
        ):
            _fail(f"store path validation no longer precedes capability classification: {owner}")
    validated_record_callers = {
        owner
        for owner, function in functions.items()
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_record_bytes_from_validated"
            for node in ast.walk(function)
        )
    }
    if validated_record_callers != {"_record_bytes", "persist_run_audit"}:
        _fail("validated record projection gained an unchecked caller")
    for owner in validated_record_callers:
        ordered_calls = {
            node.func.id: node.lineno
            for node in ast.walk(functions[owner])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"validate_run_audit_bundle", "_record_bytes_from_validated"}
        }
        if (
            set(ordered_calls) != {
                "validate_run_audit_bundle",
                "_record_bytes_from_validated",
            }
            or ordered_calls["validate_run_audit_bundle"]
            >= ordered_calls["_record_bytes_from_validated"]
        ):
            _fail(f"validated record projection lost its validation guard: {owner}")
    dir_fd_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and any(keyword.arg == "dir_fd" for keyword in node.keywords)
    ]
    if len(dir_fd_calls) < 8 or "follow_symlinks=False" not in source:
        _fail("store source no longer owns descriptor-relative no-follow effects")
    return {
        "path": "src/mathhead/run_audit_store.py",
        "sha256": _sha(SOURCE.read_bytes()),
        "public_functions": sorted(required),
        "descriptor_helpers": sorted(descriptor_helpers),
        "descriptor_relative_calls": len(dir_fd_calls),
    }


_CHILD = r"""import base64, errno, json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock
from mathhead import run_audit_store as store_module
from mathhead.run_audit import run_audit_bundle_sha256
from mathhead.run_audit_store import (
    RunAuditStoreError, list_run_audits, load_run_audit, persist_run_audit,
    run_audit_store_result_bytes,
)
from tests.run_audit.fixtures import success_bundle

def enc(value):
    return base64.b64encode(value).decode("ascii")

root = Path(os.environ["MH054_STORE_ROOT"])
action = os.environ["MH054_STORE_ACTION"]
if action == "write":
    bundle = success_bundle().bundle
    first = persist_run_audit(root, bundle)
    if first.status == "unsupported":
        print(json.dumps({
            "supported": False,
            "first": enc(run_audit_store_result_bytes(first)),
            "root_exists": root.exists(),
        }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
        raise SystemExit(0)
    second = persist_run_audit(root, bundle)
    listed = list_run_audits(root)
    loaded = load_run_audit(root, run_audit_bundle_sha256(bundle))
    print(json.dumps({
        "supported": True,
        "first": enc(run_audit_store_result_bytes(first)),
        "second": enc(run_audit_store_result_bytes(second)),
        "listed": list(listed),
        "loaded_manifest": enc(loaded.manifest),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "different":
    bundles = (success_bundle().bundle, success_bundle(claim="refuted").bundle)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda bundle: persist_run_audit(root, bundle), bundles))
    print(json.dumps({
        "statuses": sorted(item.status for item in results),
        "manifests": sorted(item.manifest_sha256 for item in results),
        "listed": list(list_run_audits(root)),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "fsync_unsupported":
    bundle = success_bundle().bundle
    with mock.patch.object(
        store_module.os, "fsync", side_effect=OSError(errno.EINVAL, "unsupported")
    ):
        result = persist_run_audit(root, bundle)
    files = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()) if root.exists() else []
    print(json.dumps({
        "result": enc(run_audit_store_result_bytes(result)),
        "files": files,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "late_fsync_unsupported":
    bundle = success_bundle().bundle
    real_sync = os.fsync
    directory_calls = 0
    def reject_late_directory(descriptor):
        global directory_calls
        import stat
        if stat.S_ISDIR(os.fstat(descriptor).st_mode):
            directory_calls += 1
            if directory_calls == 8:
                raise OSError(errno.EINVAL, "unsupported")
        real_sync(descriptor)
    with mock.patch.object(store_module.os, "fsync", side_effect=reject_late_directory):
        result = persist_run_audit(root, bundle)
    files = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file()) if root.exists() else []
    print(json.dumps({
        "result": enc(run_audit_store_result_bytes(result)),
        "directory_calls": directory_calls,
        "files": files,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "post_probe_fsync_error":
    bundle = success_bundle().bundle
    real_directory_sync = store_module._fsync_directory
    failed = False
    def reject_first_operational(pinned, descriptor, *, capability_probe=False):
        global failed
        if not capability_probe and not failed:
            failed = True
            with mock.patch.object(
                store_module.os,
                "fsync",
                side_effect=OSError(errno.EINVAL, "late operation"),
            ):
                return real_directory_sync(
                    pinned, descriptor, capability_probe=capability_probe
                )
        return real_directory_sync(
            pinned, descriptor, capability_probe=capability_probe
        )
    with mock.patch.object(
        store_module, "_fsync_directory", side_effect=reject_first_operational
    ):
        result = persist_run_audit(root, bundle)
    print(json.dumps({
        "status": result.status,
        "reason": result.reason_code,
        "failed": failed,
        "listed": list(list_run_audits(root)),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "record_cleanup_failure":
    bundle = success_bundle().bundle
    identity = run_audit_bundle_sha256(bundle)
    real_unlink = os.unlink
    matching_temporaries = 0
    def reject_record_temporary(path, *, dir_fd=None):
        global matching_temporaries
        if path.startswith("." + identity + ".") and path.endswith(".tmp"):
            matching_temporaries += 1
            if matching_temporaries == 2:
                raise OSError(errno.EACCES, "permission")
        real_unlink(path, dir_fd=dir_fd)
    with (
        mock.patch.object(store_module, "_descriptor_store_supported", return_value=True),
        mock.patch.object(store_module.os, "unlink", side_effect=reject_record_temporary),
    ):
        result = persist_run_audit(root, bundle)
    print(json.dumps({
        "status": result.status,
        "reason": result.reason_code,
        "listed": list(list_run_audits(root)),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "record_cleanup_cascade":
    bundle = success_bundle().bundle
    identity = run_audit_bundle_sha256(bundle)
    real_unlink = os.unlink
    matching_temporaries = 0
    def reject_record_cleanup(path, *, dir_fd=None):
        global matching_temporaries
        if path.startswith("." + identity + ".") and path.endswith(".tmp"):
            matching_temporaries += 1
            if matching_temporaries < 2:
                real_unlink(path, dir_fd=dir_fd)
                return
            raise OSError(errno.EACCES, "permission")
        if path == identity and matching_temporaries >= 2:
            raise OSError(errno.EACCES, "permission")
        real_unlink(path, dir_fd=dir_fd)
    with (
        mock.patch.object(store_module, "_descriptor_store_supported", return_value=True),
        mock.patch.object(store_module.os, "unlink", side_effect=reject_record_cleanup),
    ):
        result = persist_run_audit(root, bundle)
    try:
        list_run_audits(root)
    except RunAuditStoreError as exc:
        before_kind = exc.kind
    else:
        before_kind = None
    pending = next((root / ".mathhead-run-audit-store-v6" / "runs" / identity[:2]).glob(".*.tmp"))
    real_unlink(pending)
    try:
        list_run_audits(root)
    except RunAuditStoreError as exc:
        after_kind = exc.kind
    else:
        after_kind = None
    print(json.dumps({
        "persist_status": result.status,
        "persist_reason": result.reason_code,
        "before_kind": before_kind,
        "after_kind": after_kind,
        "matching_temporaries": matching_temporaries,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "temporary_link":
    bundle = success_bundle().bundle
    result = persist_run_audit(root, bundle)
    identity = run_audit_bundle_sha256(bundle)
    bucket = root / ".mathhead-run-audit-store-v6" / "runs" / identity[:2]
    os.symlink(bucket / identity, bucket / ".attacker.tmp")
    try:
        list_run_audits(root)
    except RunAuditStoreError as exc:
        rejected = True
        kind = exc.kind
    else:
        rejected = False
        kind = None
    print(json.dumps({
        "stored": result.status,
        "rejected": rejected,
        "kind": kind,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "ancestor":
    bundle = success_bundle().bundle
    base = root.parent.parent
    replacement = base / "replacement"
    replacement.mkdir(mode=0o700)
    original = base / "anchor-original"
    real_sync = store_module._fsync_directory
    changed = False
    def replace_after_probe(pinned, descriptor, *, capability_probe=False):
        global changed
        real_sync(pinned, descriptor, capability_probe=capability_probe)
        if not changed:
            changed = True
            os.rename(base / "anchor", original)
            os.symlink(replacement, base / "anchor", target_is_directory=True)
    try:
        with mock.patch.object(store_module, "_fsync_directory", side_effect=replace_after_probe):
            persist_run_audit(root, bundle)
    except RunAuditStoreError as exc:
        rejected = True
        kind = exc.kind
    else:
        rejected = False
        kind = None
    replacement_entries = sorted(str(path.relative_to(replacement)) for path in replacement.rglob("*"))
    print(json.dumps({
        "rejected": rejected,
        "kind": kind,
        "replacement_entries": replacement_entries,
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "load":
    identity = os.environ["MH054_MANIFEST_SHA256"]
    loaded = load_run_audit(root, identity)
    print(json.dumps({
        "manifest_sha256": run_audit_bundle_sha256(loaded),
        "listed": list(list_run_audits(root)),
    }, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
elif action == "reject":
    identity = os.environ["MH054_MANIFEST_SHA256"]
    try:
        load_run_audit(root, identity)
    except RunAuditStoreError as exc:
        print(json.dumps({"rejected": True, "kind": exc.kind}, sort_keys=True))
    else:
        print(json.dumps({"rejected": False}, sort_keys=True))
        sys.exit(3)
else:
    raise SystemExit("unknown action")
"""


def _child(root: Path, action: str, manifest: str | None = None) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["MH054_STORE_ROOT"] = str(root)
    environment["MH054_STORE_ACTION"] = action
    if manifest is not None:
        environment["MH054_MANIFEST_SHA256"] = manifest
    roots = (str(ROOT / "src"), str(ROOT))
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join((*roots, inherited) if inherited else roots)
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=90,
    )
    if completed.returncode:
        _fail(
            f"store child {action} failed: " + completed.stderr.decode("utf-8", "replace").strip()
        )
    try:
        value = json.loads(completed.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"store child output is invalid: {type(exc).__name__}")
    if type(value) is not dict:
        _fail("store child output is not an object")
    return value


def _decode(value: object, label: str) -> bytes:
    if type(value) is not str:
        _fail(f"{label} is not base64 text")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeError, ValueError) as exc:
        _fail(f"{label} is not strict base64: {type(exc).__name__}")


def _check_private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or path.is_symlink():
        _fail(f"store component is not a real directory: {path.name}")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        _fail(f"store directory is not private: {path.name}")


def _check_private_file(path: Path) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink() or info.st_nlink != 1:
        _fail(f"store component is linked or not a regular file: {path.name}")
    if os.name == "posix" and stat.S_IMODE(info.st_mode) & 0o077:
        _fail(f"store file is not private: {path.name}")
    return path.read_bytes()


def _check_result(raw: bytes, status: str) -> dict[str, Any]:
    value = _parse(raw, f"{status} result")
    expected = {
        "schema",
        "contract_id",
        "contract_sha256",
        "status",
        "reason_code",
        "manifest_sha256",
        "record_sha256",
        "object_count",
        "result_sha256",
        "mathematical_authority",
    }
    if (
        set(value) != expected
        or value["schema"] != RESULT_SCHEMA
        or value["contract_id"] != CONTRACT_ID
        or value["contract_sha256"] != CONTRACT_SHA256
        or value["status"] != status
        or value["mathematical_authority"] is not False
        or value["result_sha256"] != _self_hash(value, "result_sha256")
    ):
        _fail(f"{status} store result binding differs")
    if status in {"stored", "existing", "loaded"}:
        _digest(value["manifest_sha256"], "result.manifest_sha256")
        _digest(value["record_sha256"], "result.record_sha256")
    elif (
        value["manifest_sha256"] is not None
        or value["record_sha256"] is not None
        or value["object_count"] != 0
    ):
        _fail(f"{status} store result retained a committed identity")
    return value


def _inspect_store(root: Path, written: dict[str, Any]) -> dict[str, object]:
    first = _check_result(_decode(written.get("first"), "first"), "stored")
    second = _check_result(_decode(written.get("second"), "second"), "existing")
    manifest_identity = _digest(first["manifest_sha256"], "manifest identity")
    if (
        second["manifest_sha256"] != manifest_identity
        or first["record_sha256"] != second["record_sha256"]
        or written.get("listed") != [manifest_identity]
        or _sha(_decode(written.get("loaded_manifest"), "loaded manifest")) != manifest_identity
    ):
        _fail("stored/existing/load/list identities differ")
    current = root / STORE_NAMESPACE
    for directory in (current, current / "objects", current / "runs"):
        _check_private_directory(directory)
    object_files: dict[str, bytes] = {}
    for bucket in sorted((current / "objects").iterdir()):
        _check_private_directory(bucket)
        if re.fullmatch(r"[0-9a-f]{2}", bucket.name) is None:
            _fail("object bucket name differs")
        for entry in sorted(bucket.iterdir()):
            if entry.name.startswith(".") or entry.name[:2] != bucket.name:
                _fail("temporary or misplaced content became visible")
            _digest(entry.name, "object filename")
            raw = _check_private_file(entry)
            if _sha(raw) != entry.name:
                _fail("object filename/content identity differs")
            object_files[entry.name] = raw
    run_files: list[Path] = []
    for bucket in sorted((current / "runs").iterdir()):
        _check_private_directory(bucket)
        if re.fullmatch(r"[0-9a-f]{2}", bucket.name) is None:
            _fail("run bucket name differs")
        for entry in sorted(bucket.iterdir()):
            if entry.name.startswith(".") or entry.name[:2] != bucket.name:
                _fail("temporary or misplaced run became visible")
            _digest(entry.name, "run filename")
            run_files.append(entry)
    if len(run_files) != 1 or run_files[0].name != manifest_identity:
        _fail("visible run inventory differs")
    record = _parse(_check_private_file(run_files[0]), "run record")
    expected_record = {
        "schema",
        "store_contract_sha256",
        "manifest_sha256",
        "logical_report_sha256",
        "execution_provenance_sha256",
        "object_sha256s",
        "record_sha256",
        "mathematical_authority",
    }
    inventory = record.get("object_sha256s")
    if (
        set(record) != expected_record
        or record["schema"] != RECORD_SCHEMA
        or record["store_contract_sha256"] != CONTRACT_SHA256
        or record["manifest_sha256"] != manifest_identity
        or record["mathematical_authority"] is not False
        or record["record_sha256"] != _self_hash(record, "record_sha256")
        or type(inventory) is not list
        or inventory != sorted(set(inventory))
        or set(inventory) != set(object_files)
        or record["logical_report_sha256"] not in inventory
        or manifest_identity not in inventory
    ):
        _fail("run record binding, identity, or object closure differs")
    manifest = _parse(object_files[manifest_identity], "stored manifest")
    if (
        manifest.get("audited_run_contract_sha256") != AUDIT_SHA256
        or manifest.get("replay_contract_sha256") != REPLAY_SHA256
        or manifest.get("mathematical_authority") is not False
        or manifest.get("logical_report_sha256") != record["logical_report_sha256"]
        or manifest.get("execution_provenance_sha256")
        != record["execution_provenance_sha256"]
    ):
        _fail("stored manifest audit/replay binding differs")
    manifest_objects = manifest.get("objects")
    if type(manifest_objects) is not list:
        _fail("stored manifest object inventory differs")
    expected_inventory = {manifest_identity} | {
        _digest(item.get("sha256"), "manifest object digest")
        for item in manifest_objects
        if type(item) is dict
    }
    if expected_inventory != set(inventory):
        _fail("run record has missing or surplus content")
    return {
        "visible_runs": 1,
        "content_objects": len(object_files),
        "manifest_records": len(manifest_objects),
        "events": len(manifest.get("events", [])),
        "first_status": first["status"],
        "repeat_status": second["status"],
        "private_layout": True,
        "append_only_commit_record": True,
    }


def _runtime_checks() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="mathhead-audit-store-validator-") as parent:
        base = Path(parent).resolve()
        store = base / "original"
        written = _child(store, "write")
        if written.get("supported") is False:
            unsupported = _check_result(
                _decode(written.get("first"), "unsupported first"),
                "unsupported",
            )
            if (
                unsupported.get("reason_code") != "STORE_UNSUPPORTED"
                or written.get("root_exists") is not False
            ):
                _fail("unsupported platform created state or returned the wrong result")
            return {
                "platform_supported": False,
                "unsupported_effect_free": True,
                "fixture": {
                    "store_verified": True,
                    "first_write_verified": False,
                    "repeat_write_verified": False,
                },
            }
        if written.get("supported") is not True:
            _fail("store child omitted its platform capability classification")
        fixture = _inspect_store(store, written)
        manifest = str(_parse(_decode(written["first"], "first"), "first")["manifest_sha256"])

        different = _child(base / "different", "different")
        different_manifests = different.get("manifests")
        if (
            different.get("statuses") != ["stored", "stored"]
            or type(different_manifests) is not list
            or len(different_manifests) != 2
            or len(set(different_manifests)) != 2
            or different.get("listed") != sorted(different_manifests)
        ):
            _fail("concurrent different-run writers did not remain independent")

        unsupported_sync = _child(base / "unsupported-sync", "fsync_unsupported")
        unsupported_result = _check_result(
            _decode(unsupported_sync.get("result"), "unsupported sync result"),
            "unsupported",
        )
        if (
            unsupported_result.get("reason_code") != "STORE_UNSUPPORTED"
            or unsupported_sync.get("files") != []
        ):
            _fail("unsupported directory synchronization installed content")

        late_unsupported_sync = _child(base / "late-unsupported-sync", "late_fsync_unsupported")
        late_unsupported_result = _check_result(
            _decode(late_unsupported_sync.get("result"), "late unsupported sync result"),
            "unsupported",
        )
        if (
            late_unsupported_result.get("reason_code") != "STORE_UNSUPPORTED"
            or late_unsupported_sync.get("directory_calls") != 8
            or late_unsupported_sync.get("files") != []
        ):
            _fail("late unsupported directory synchronization installed content")

        post_probe_sync = _child(base / "post-probe-sync", "post_probe_fsync_error")
        if (
            post_probe_sync.get("status") != "io_error"
            or post_probe_sync.get("reason") != "STORE_IO_ERROR"
            or post_probe_sync.get("failed") is not True
            or post_probe_sync.get("listed") != []
        ):
            _fail("post-probe synchronization error exposed a visible run")

        cleanup_failure = _child(base / "record-cleanup-failure", "record_cleanup_failure")
        if (
            cleanup_failure.get("status") != "io_error"
            or cleanup_failure.get("reason") != "STORE_IO_ERROR"
            or cleanup_failure.get("listed") != []
        ):
            _fail("record temporary cleanup failure exposed a visible run")

        cleanup_cascade = _child(base / "record-cleanup-cascade", "record_cleanup_cascade")
        if cleanup_cascade != {
            "persist_status": "io_error",
            "persist_reason": "STORE_IO_ERROR",
            "before_kind": "link",
            "after_kind": "mode",
            "matching_temporaries": 2,
        }:
            _fail("cascading record cleanup failure became an accepted run")

        temporary_link = _child(base / "temporary-link", "temporary_link")
        if (
            temporary_link.get("stored") != "stored"
            or temporary_link.get("rejected") is not True
            or temporary_link.get("kind") != "link"
        ):
            _fail("linked run temporary was ignored")

        ancestor = _child(base / "anchor" / "audit", "ancestor")
        if (
            ancestor.get("rejected") is not True
            or ancestor.get("kind") != "link"
            or ancestor.get("replacement_entries") != []
        ):
            _fail("ancestor replacement redirected one store effect")

        relocated = base / "relocated"
        shutil.copytree(store, relocated)
        relocated_result = _child(relocated, "load", manifest)
        relocation_ok = relocated_result.get(
            "manifest_sha256"
        ) == manifest and relocated_result.get("listed") == [manifest]
        if not relocation_ok:
            _fail("relocated exact store did not preserve load/list identity")

        relocated_current = relocated / STORE_NAMESPACE
        orphan = relocated_current / "objects" / ("f" * 2) / ("f" * 64)
        orphan.parent.mkdir(mode=0o700, exist_ok=True)
        orphan.write_bytes(b"orphan\n")
        orphan.chmod(0o600)
        orphan_result = _child(relocated, "load", manifest)
        orphan_ignored = orphan_result.get("manifest_sha256") == manifest
        if not orphan_ignored:
            _fail("unreachable orphan content changed committed run loading")

        corrupt = base / "corrupt"
        shutil.copytree(store, corrupt)
        corrupt_current = corrupt / STORE_NAMESPACE
        run_path = corrupt_current / "runs" / manifest[:2] / manifest
        record = _parse(run_path.read_bytes(), "corrupt source record")
        object_identity = next(
            item
            for item in record["object_sha256s"]
            if item not in {manifest, record["logical_report_sha256"]}
        )
        content = corrupt_current / "objects" / object_identity[:2] / object_identity
        content.write_bytes(content.read_bytes() + b"corrupt")
        content.chmod(0o600)
        rejected = _child(corrupt, "reject", manifest)
        corruption_rejected = rejected.get("rejected") is True
        if not corruption_rejected:
            _fail("corrupted content did not fail closed")

        hardlinked = base / "hardlinked"
        shutil.copytree(store, hardlinked)
        hardlinked_current = hardlinked / STORE_NAMESPACE
        hardlinked_run = hardlinked_current / "runs" / manifest[:2] / manifest
        hardlinked_record = _parse(hardlinked_run.read_bytes(), "hardlinked record")
        hardlinked_identity = next(
            item
            for item in hardlinked_record["object_sha256s"]
            if item not in {manifest, hardlinked_record["logical_report_sha256"]}
        )
        hardlinked_content = hardlinked_current / "objects" / hardlinked_identity[:2] / hardlinked_identity
        os.link(hardlinked_content, base / "external-hardlink")
        hardlink_result = _child(hardlinked, "reject", manifest)
        hardlink_rejected = hardlink_result.get("rejected") is True
        if not hardlink_rejected:
            _fail("hardlinked content did not fail closed")
    return {
        "platform_supported": True,
        "fixture": {
            "store_verified": True,
            "first_write_verified": fixture["first_status"] == "stored",
            "repeat_write_verified": fixture["repeat_status"] == "existing",
        },
        "different_run_concurrency_verified": True,
        "unsupported_sync_effect_free": True,
        "late_unsupported_sync_effect_free": True,
        "post_probe_sync_failure_nonvisible": True,
        "record_cleanup_failure_nonvisible": True,
        "cascading_cleanup_failure_nonvisible": True,
        "linked_temporary_rejected": True,
        "ancestor_replacement_effect_free": True,
        "relocation_preserved": relocation_ok,
        "orphan_content_ignored": orphan_ignored,
        "corruption_rejected": corruption_rejected,
        "hardlinked_content_rejected": hardlink_rejected,
    }


def _report() -> dict[str, object]:
    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "binding": _contract_checks(),
        "source": _source_checks(),
        "runtime": _runtime_checks(),
        "checks": [
            "accepted-contract-and-closed-schema-binding",
            "private-real-directory-and-file-layout",
            "content-addressed-object-closure",
            "immutable-run-record-commit-point",
            "idempotent-existing-result",
            "fresh-load-and-sorted-listing",
            "relocation-stability",
            "orphan-content-nonvisibility",
            "corrupt-content-fail-closed",
            "different-run-concurrency",
            "unsupported-sync-no-install",
            "late-unsupported-sync-no-install",
            "post-probe-sync-failure-nonvisibility",
            "record-cleanup-failure-nonvisibility",
            "cascading-cleanup-failure-nonvisibility",
            "linked-temporary-rejection",
            "ancestor-replacement-no-redirect",
            "hardlinked-content-rejection",
            "non-authoritative-store-results",
        ],
        "mathematical_authority": False,
        "report_sha256": None,
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def _verify_frozen_report(report: dict[str, object], rendered: bytes) -> None:
    if not REPORT.is_file():
        _fail(f"frozen report missing: {REPORT.relative_to(ROOT)}")
    frozen_raw = REPORT.read_bytes()
    frozen = _parse(frozen_raw, "frozen store report")
    if frozen.get("report_sha256") != _self_hash(frozen, "report_sha256"):
        _fail("frozen store report self identity differs")
    runtime = report.get("runtime")
    if type(runtime) is not dict or type(runtime.get("platform_supported")) is not bool:
        _fail("live store report omitted its platform classification")
    if runtime["platform_supported"]:
        if frozen_raw != rendered:
            _fail(f"frozen report drift: {REPORT.relative_to(ROOT)}")
        return
    stable_fields = (
        "schema",
        "status",
        "binding",
        "source",
        "checks",
        "mathematical_authority",
    )
    frozen_runtime = frozen.get("runtime")
    if (
        any(frozen.get(field) != report.get(field) for field in stable_fields)
        or type(frozen_runtime) is not dict
        or frozen_runtime.get("platform_supported") is not True
    ):
        _fail("frozen supported-platform evidence is stale or incomplete")


def main() -> int:
    try:
        report = _report()
        rendered = _canonical(report)
        if "--write-report" in sys.argv:
            runtime = report.get("runtime")
            if type(runtime) is not dict or runtime.get("platform_supported") is not True:
                _fail("frozen store evidence can be written only on a supported platform")
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_bytes(rendered)
        else:
            _verify_frozen_report(report, rendered)
    except (
        StoreValidationError,
        OSError,
        UnicodeError,
        ValueError,
        SyntaxError,
        tomllib.TOMLDecodeError,
    ) as exc:
        print(f"run-audit-store: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "run-audit-store: PASS (append-only commit, exact dedupe, relocation, corruption rejection)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
