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
REPORT = ROOT / "docs/planning/reports/run-audit-store-v1.json"
CONTRACT_ID = "MH-C-RUN-AUDIT-STORE-001"
CONTRACT_SHA256 = "a28a5f7f0a9f592a2addf0c0a653483fd3198adec112507705567479c17cbc12"
AUDIT_SHA256 = "6032b9efac0c1ffa93cc2ee738318f45d8331c8ee25f4d97b51b55ba8aff8c0a"
REPLAY_SHA256 = "ed130e9099a4308ed2c911e9ad63d2450783d9bff9700ad6ac0e2dd22ede9bc5"
SCHEMAS = {
    "run-audit-store-record-v1.schema.json": "de9127034133d21d23e5d2376a18247da89842b6de65da8555e1ddfc5ec60c05",
    "run-audit-store-result-v1.schema.json": "9245bc736376bbb812234d5e0562a8b541e14ad3cbfbe901cd56bbd82e9544d0",
}
REPORT_SCHEMA = "mathhead.run-audit-store-validation-report.v1"
RECORD_SCHEMA = "mathhead.run-audit-store-record.v1"
RESULT_SCHEMA = "mathhead.run-audit-store-result.v1"
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
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("constant")
            ),
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
        or bindings.get("MH-C-AUDITED-RUN-001") != AUDIT_SHA256
        or bindings.get("MH-C-RUN-AUDIT-REPLAY-001") != REPLAY_SHA256
    ):
        _fail("accepted store/audit/replay contract binding drift")
    schema_report: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        schema = _parse(path.read_bytes(), name, canonical=False)
        if (
            _sha(path.read_bytes()) != digest
            or schema.get("$schema")
            != "https://json-schema.org/draft/2020-12/schema"
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
    return {
        "path": "src/mathhead/run_audit_store.py",
        "sha256": _sha(SOURCE.read_bytes()),
        "public_functions": sorted(required),
    }


_CHILD = r'''import base64, json, os, sys
from pathlib import Path
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
    second = persist_run_audit(root, bundle)
    listed = list_run_audits(root)
    loaded = load_run_audit(root, run_audit_bundle_sha256(bundle))
    print(json.dumps({
        "first": enc(run_audit_store_result_bytes(first)),
        "second": enc(run_audit_store_result_bytes(second)),
        "listed": list(listed),
        "loaded_manifest": enc(loaded.manifest),
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
'''


def _child(root: Path, action: str, manifest: str | None = None) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["MH054_STORE_ROOT"] = str(root)
    environment["MH054_STORE_ACTION"] = action
    if manifest is not None:
        environment["MH054_MANIFEST_SHA256"] = manifest
    roots = (str(ROOT / "src"), str(ROOT))
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        (*roots, inherited) if inherited else roots
    )
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
            f"store child {action} failed: "
            + completed.stderr.decode("utf-8", "replace").strip()
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
    _digest(value["manifest_sha256"], "result.manifest_sha256")
    _digest(value["record_sha256"], "result.record_sha256")
    return value


def _inspect_store(root: Path, written: dict[str, Any]) -> dict[str, object]:
    first = _check_result(_decode(written.get("first"), "first"), "stored")
    second = _check_result(_decode(written.get("second"), "second"), "existing")
    manifest_identity = _digest(first["manifest_sha256"], "manifest identity")
    if (
        second["manifest_sha256"] != manifest_identity
        or first["record_sha256"] != second["record_sha256"]
        or written.get("listed") != [manifest_identity]
        or _sha(_decode(written.get("loaded_manifest"), "loaded manifest"))
        != manifest_identity
    ):
        _fail("stored/existing/load/list identities differ")
    for directory in (root, root / "objects", root / "runs"):
        _check_private_directory(directory)
    object_files: dict[str, bytes] = {}
    for bucket in sorted((root / "objects").iterdir()):
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
    for bucket in sorted((root / "runs").iterdir()):
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
        or manifest.get("logical_report_sha256")
        != record["logical_report_sha256"]
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
        base = Path(parent)
        store = base / "original"
        written = _child(store, "write")
        fixture = _inspect_store(store, written)
        manifest = str(_parse(_decode(written["first"], "first"), "first")["manifest_sha256"])

        relocated = base / "relocated"
        shutil.copytree(store, relocated)
        relocated_result = _child(relocated, "load", manifest)
        relocation_ok = (
            relocated_result.get("manifest_sha256") == manifest
            and relocated_result.get("listed") == [manifest]
        )
        if not relocation_ok:
            _fail("relocated exact store did not preserve load/list identity")

        orphan = relocated / "objects" / ("f" * 2) / ("f" * 64)
        orphan.parent.mkdir(mode=0o700, exist_ok=True)
        orphan.write_bytes(b"orphan\n")
        orphan.chmod(0o600)
        orphan_result = _child(relocated, "load", manifest)
        orphan_ignored = orphan_result.get("manifest_sha256") == manifest
        if not orphan_ignored:
            _fail("unreachable orphan content changed committed run loading")

        corrupt = base / "corrupt"
        shutil.copytree(store, corrupt)
        run_path = corrupt / "runs" / manifest[:2] / manifest
        record = _parse(run_path.read_bytes(), "corrupt source record")
        object_identity = next(
            item
            for item in record["object_sha256s"]
            if item not in {manifest, record["logical_report_sha256"]}
        )
        content = corrupt / "objects" / object_identity[:2] / object_identity
        content.write_bytes(content.read_bytes() + b"corrupt")
        content.chmod(0o600)
        rejected = _child(corrupt, "reject", manifest)
        corruption_rejected = rejected.get("rejected") is True
        if not corruption_rejected:
            _fail("corrupted content did not fail closed")
    return {
        "fixture": fixture,
        "relocation_preserved": relocation_ok,
        "orphan_content_ignored": orphan_ignored,
        "corruption_rejected": corruption_rejected,
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
            "non-authoritative-store-results",
        ],
        "mathematical_authority": False,
        "report_sha256": None,
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def main() -> int:
    try:
        report = _report()
        rendered = _canonical(report)
        if "--write-report" in sys.argv:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_bytes(rendered)
        elif not REPORT.is_file() or REPORT.read_bytes() != rendered:
            _fail(f"frozen report drift or missing: {REPORT.relative_to(ROOT)}")
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
        "run-audit-store: PASS "
        "(append-only commit, exact dedupe, relocation, corruption rejection)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
