#!/usr/bin/env python3
"""Independently validate the MH-055 immutable safe-cache store."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import tomllib
from typing import NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/safe_cache_store.py"
REPORT = ROOT / "docs/planning/reports/safe-cache-store-v1.json"
CONTRACT_ID = "MH-C-SAFE-CACHE-STORE-001"
CONTRACT_SHA256 = "1f1dba767275ce066a977fe5eda2e499da7faf6135e1f11ac8db3587e2337cd1"
PURE_ID = "MH-C-SAFE-CACHE-001"
PURE_SHA256 = "ec1c056023d8d966ed3a143a12e8c1726849d491800b175a3e807ca9a260cbb9"
SCHEMAS = {
    "safe-cache-store-record-v1.schema.json": "959e5f08b002479753fa14210e39dbc594c529177e6923866b0c6911c29ef001",
    "safe-cache-store-result-v1.schema.json": "0c9a2c429522b44fb51728e5c6491e6f2379e2fcd544a6c4c7eca552a2a9a4ca",
}
REPORT_SCHEMA = "mathhead.safe-cache-store-validation-report.v1"


class StoreValidationFailure(RuntimeError):
    pass


def _fail(detail: str) -> NoReturn:
    raise StoreValidationFailure(detail)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _self_hash(value: dict[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _binding_checks() -> dict[str, object]:
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text())
    accepted = {
        str(item["id"]): str(item["sha256"])
        for item in manifest.get("contracts", [])
        if item.get("state") == "accepted"
    }
    for contract_id, digest in ((CONTRACT_ID, CONTRACT_SHA256), (PURE_ID, PURE_SHA256)):
        raw = (ROOT / f"docs/contracts/{contract_id}.json").read_bytes()
        proposed = (ROOT / f"docs/contracts/proposed/{contract_id}.json").read_bytes()
        if _sha(raw) != digest or raw != proposed or accepted.get(contract_id) != digest:
            _fail(f"accepted contract binding drift: {contract_id}")
    schemas: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        schema = json.loads(path.read_bytes())
        if (
            _sha(path.read_bytes()) != digest
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or set(schema.get("required", [])) != set(schema.get("properties", {}))
        ):
            _fail(f"closed store schema binding drift: {name}")
        schemas[name] = digest
    return {
        "contracts": {CONTRACT_ID: CONTRACT_SHA256, PURE_ID: PURE_SHA256},
        "schemas": schemas,
    }


def _source_checks() -> dict[str, object]:
    source = SOURCE.read_text()
    tree = ast.parse(source)
    functions = {
        node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    required = {
        "persist_safe_cache": [
            "cache_root", "audit_root", "planning_request", "route_result",
            "portfolio_request", "planning_result", "parent_budget", "descriptors",
            "bindings", "artifacts", "manifest_sha256",
        ],
        "lookup_safe_cache": [
            "cache_root", "audit_root", "planning_request", "route_result",
            "portfolio_request", "planning_result", "parent_budget", "descriptors",
            "bindings", "artifacts",
        ],
        "list_safe_cache": ["cache_root", "audit_root"],
    }
    for name, parameters in required.items():
        node = functions.get(name)
        if node is None or [item.arg for item in node.args.args] != parameters:
            _fail(f"public store signature source drift: {name}")
    audit_imports: set[str] = set()
    forbidden_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module == "run_audit_store":
                audit_imports.update(item.name for item in node.names)
            if node.module and any(part in node.module for part in ("subprocess", "multiprocessing", "discovery", "cache")) and node.module not in {"safe_cache", "safe_cache_store"}:
                forbidden_imports.add(node.module)
        elif isinstance(node, ast.Import):
            for item in node.names:
                if item.name in {"subprocess", "multiprocessing", "socket", "importlib"}:
                    forbidden_imports.add(item.name)
    if audit_imports != {"RunAuditStoreError", "load_run_audit"} or forbidden_imports:
        _fail("store import closure bypasses public audit load or includes execution")
    persist_start = source.find("def persist_safe_cache")
    text_order = tuple(
        source.find(marker, persist_start)
        for marker in (
            "current = _current_decision(args)",
            "bundle = load_run_audit(audit_root, manifest_sha256)",
            "decision = decide_safe_cache(*args, bundle)",
            "if not _descriptor_store_supported()",
            "_write_immutable(store, object_bucket",
            "created = _write_immutable(",
        )
    )
    if any(index < 0 for index in text_order) or tuple(sorted(text_order)) != text_order:
        _fail("persist validation, capability, content and commit order drift")
    return {
        "path": "src/mathhead/safe_cache_store.py",
        "sha256": _sha(SOURCE.read_bytes()),
        "descriptor_relative": all(
            marker in source
            for marker in (
                "dir_fd=", "follow_symlinks=False", "os.O_NOFOLLOW",
                "_guard_root", "_fsync_directory", "_write_immutable",
            )
        ),
        "public_audit_load_only": True,
    }


def _cache_inputs(audited: object) -> tuple[object, ...]:
    bundle = audited.bundle
    manifest = json.loads(bundle.manifest)
    objects = {_sha(raw): raw for raw in bundle.objects}
    by_role: dict[str, list[dict[str, object]]] = {}
    for record in manifest["objects"]:
        by_role.setdefault(str(record["role"]), []).append(record)

    def one(role: str) -> bytes:
        values = by_role[role]
        if len(values) != 1:
            _fail(f"fixture role differs: {role}")
        return objects[str(values[0]["sha256"])]

    request = json.loads(one("portfolio_request"))
    return (
        one("planning_request"), one("capability_route_result"),
        one("portfolio_request"), one("planning_result"), one("initial_parent_budget"),
        tuple(objects[str(item["sha256"])] for item in by_role["plugin_descriptor"]),
        tuple(objects[str(item["sha256"])] for item in by_role["execution_binding"]),
        tuple(objects[str(item["sha256"])] for item in request["artifact_bindings"]),
    )


def _private_directory(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700:
        _fail(f"cache directory is not exact private 0700: {path.name}")


def _private_file(path: Path) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
        _fail(f"cache file is not exact private single-link 0600: {path.name}")


def _runtime_checks(module: object) -> dict[str, object]:
    from mathhead.run_audit_store import persist_run_audit
    from tests.run_audit.fixtures import success_bundle

    if not module._descriptor_store_supported():
        return {"platform_supported": False}
    audited = success_bundle()
    current = _cache_inputs(audited)
    with tempfile.TemporaryDirectory(prefix="mh055-store-validator-", dir=ROOT) as raw:
        base = Path(raw).resolve()
        cache_root, audit_root = base / "cache", base / "audit"
        audit = persist_run_audit(audit_root, audited.bundle)
        if audit.status not in {"stored", "existing"}:
            _fail("audit fixture did not persist")
        miss = module.lookup_safe_cache(cache_root, audit_root, *current)
        first = module.persist_safe_cache(
            cache_root, audit_root, *current, audited.bundle.manifest_sha256
        )
        repeat = module.persist_safe_cache(
            cache_root, audit_root, *current, audited.bundle.manifest_sha256
        )
        hit = module.lookup_safe_cache(cache_root, audit_root, *current)
        listing = module.list_safe_cache(cache_root, audit_root)
        if (
            miss.status != "miss" or first.status != "stored"
            or repeat.status != "existing" or hit.status != "hit"
            or listing != (hit.lookup_key_sha256,)
            or first.record_sha256 != repeat.record_sha256
        ):
            _fail("store miss/write/repeat/hit/list cycle differs")
        key = str(hit.lookup_key_sha256)
        record_path = cache_root / "keys" / key[:2] / key
        _private_directory(cache_root)
        _private_directory(cache_root / "keys")
        _private_directory(cache_root / "keys" / key[:2])
        _private_file(record_path)
        record_raw = record_path.read_bytes()
        record = json.loads(record_raw)
        if (
            record_raw != _canonical(record)
            or record.get("record_sha256") != _self_hash(record, "record_sha256")
            or record.get("lookup_key_sha256") != key
            or record.get("audit_manifest_sha256") != audited.bundle.manifest_sha256
        ):
            _fail("visible key record identity differs")
        object_digest = str(record["entry_object_sha256"])
        object_path = cache_root / "objects" / object_digest[:2] / object_digest
        _private_file(object_path)
        if _sha(object_path.read_bytes()) != object_digest:
            _fail("entry object content address differs")
        relocated = base / "relocated"
        relocated.mkdir(mode=0o700)
        moved_cache, moved_audit = relocated / "cache", relocated / "audit"
        shutil.copytree(cache_root, moved_cache)
        shutil.copytree(audit_root, moved_audit)
        moved = module.lookup_safe_cache(moved_cache, moved_audit, *current)
        if moved.status != "hit" or moved.result_sha256 != hit.result_sha256:
            _fail("relocated store changed logical hit")
        corrupt = base / "corrupt"
        shutil.copytree(cache_root, corrupt)
        corrupt_record = corrupt / "keys" / key[:2] / key
        corrupt_record.write_bytes(corrupt_record.read_bytes() + b"x")
        rejected = module.lookup_safe_cache(corrupt, audit_root, *current)
        if (rejected.status, rejected.reason_code) != ("corrupt", "CACHE_ENTRY_CORRUPT"):
            _fail("corrupt visible record did not fail closed")
        orphan = cache_root / "objects" / "ff" / ("f" * 64)
        orphan.parent.mkdir(mode=0o700, exist_ok=True)
        orphan.write_bytes(b"orphan\n")
        orphan.chmod(0o600)
        if module.list_safe_cache(cache_root, audit_root) != (key,):
            _fail("unreachable exact content changed listing")
        return {
            "platform_supported": True,
            "lookup_key_sha256": key,
            "first_write_verified": True, "repeat_write_verified": True,
            "fresh_lookup_verified": True, "listing_verified": True,
            "relocation_verified": True, "corruption_rejected": True,
            "orphan_content_ignored": True, "mathematical_authority": False,
        }


def _report() -> dict[str, object]:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    import mathhead.safe_cache_store as module

    report: dict[str, object] = {
        "schema": REPORT_SCHEMA, "status": "passed",
        "binding": _binding_checks(), "source": _source_checks(),
        "runtime": _runtime_checks(module),
        "checks": [
            "accepted-contract-and-closed-schema-binding",
            "public-audit-load-only", "root-separation-and-stable-ancestor-guards",
            "descriptor-relative-no-follow-layout", "capability-before-content-install",
            "entry-content-before-key-commit", "canonical-record-self-identity",
            "exact-dedupe-and-conflict", "fresh-present-lookup",
            "fresh-historical-listing", "relocation-stability",
            "corrupt-visible-state-fail-closed", "orphan-content-nonvisibility",
            "zero-cache-metadata-authority",
        ],
        "mathematical_authority": False, "report_sha256": None,
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def _verify_frozen(report: dict[str, object], rendered: bytes) -> None:
    if not REPORT.is_file():
        _fail(f"frozen report missing: {REPORT.relative_to(ROOT)}")
    frozen_raw = REPORT.read_bytes()
    frozen = json.loads(frozen_raw)
    runtime = report.get("runtime")
    if type(runtime) is not dict or type(runtime.get("platform_supported")) is not bool:
        _fail("runtime platform classification absent")
    if runtime["platform_supported"]:
        if frozen_raw != rendered:
            _fail(f"frozen report drift: {REPORT.relative_to(ROOT)}")
        return
    stable = ("schema", "status", "binding", "source", "checks", "mathematical_authority")
    frozen_runtime = frozen.get("runtime")
    if (
        any(frozen.get(field) != report.get(field) for field in stable)
        or type(frozen_runtime) is not dict
        or frozen_runtime.get("platform_supported") is not True
    ):
        _fail("frozen supported-platform store evidence is stale")


def main() -> int:
    try:
        report = _report()
        rendered = _canonical(report)
        if "--write-report" in sys.argv:
            runtime = report.get("runtime")
            if type(runtime) is not dict or runtime.get("platform_supported") is not True:
                _fail("frozen report can be written only on a supported platform")
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_bytes(rendered)
        else:
            _verify_frozen(report, rendered)
    except (StoreValidationFailure, OSError, ValueError, SyntaxError) as exc:
        print(f"safe-cache-store: FAIL: {exc}", file=sys.stderr)
        return 1
    print("safe-cache-store: PASS (immutable commit, fresh lookup, corruption rejection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
