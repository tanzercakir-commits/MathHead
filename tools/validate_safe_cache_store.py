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
from unittest import mock
from typing import NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/safe_cache_store.py"
REPORT = ROOT / "docs/planning/reports/safe-cache-store-v2.json"
CONTRACT_ID = "MH-C-SAFE-CACHE-STORE-002"
CONTRACT_SHA256 = "4ed580fcb08191bfc7caa8901a4f5b74456cd9fc178f17b8a2530b0599368ed2"
PURE_ID = "MH-C-SAFE-CACHE-002"
PURE_SHA256 = "35cd004a1ed91f2c3969a6b295722b8099ee9fc36f3fc15170d5d1082d2bfab4"
AUDIT_STORE_ID = "MH-C-RUN-AUDIT-STORE-006"
AUDIT_STORE_SHA256 = "327f5d55b86433b803f22ba019b8adf5fe3a4bf8bc0dbdf4b1472c276bedff5e"
SCHEMAS = {
    "safe-cache-store-record-v2.schema.json": "9caba023663c86e8917cb3560ed5d56fd04178fc123bc04cc6da2d0449767dda",
    "safe-cache-store-result-v2.schema.json": "6c00b6c21692bc79b5a355e27c40563524e190ab544f05024330513b427acd75",
}
REPORT_SCHEMA = "mathhead.safe-cache-store-validation-report.v2"
STORE_NAMESPACE = ".mathhead-safe-cache-store-v2"


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
    for contract_id, digest in (
        (CONTRACT_ID, CONTRACT_SHA256), (PURE_ID, PURE_SHA256),
        (AUDIT_STORE_ID, AUDIT_STORE_SHA256),
    ):
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
    result_schema = json.loads(
        (ROOT / "docs/contracts/schemas/safe-cache-store-result-v2.schema.json").read_bytes()
    )
    branches = result_schema.get("allOf", [{}])[0].get("oneOf", [])
    rows = sum(
        len(branch.get("properties", {}).get("reason_code", {}).get("enum", [None]))
        for branch in branches
    )
    if len(branches) != 27 or rows != 31:
        _fail("closed store result operation matrix differs")
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
    if (
        "_historical_inputs" in functions
        or STORE_NAMESPACE not in source
        or "verified = lookup_safe_cache(" not in source[persist_start:]
    ):
        _fail("v2 namespace, public post-lookup, or listing purity drift")
    list_calls = [
        node.func.id
        for node in ast.walk(functions["list_safe_cache"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    if list_calls.count("decide_safe_cache") != 0 or list_calls.count("load_run_audit") != 1:
        _fail("listing decision/load budget drift")
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
    from tests.safe_cache.audited_fixtures import EXPECTED_LOOKUP_KEYS, success_bundle

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
        with (
            mock.patch.object(module, "load_run_audit", wraps=module.load_run_audit) as persist_load,
            mock.patch.object(module, "decide_safe_cache", wraps=module.decide_safe_cache) as persist_decide,
        ):
            first = module.persist_safe_cache(
                cache_root, audit_root, *current, audited.bundle.manifest_sha256
            )
        repeat = module.persist_safe_cache(
            cache_root, audit_root, *current, audited.bundle.manifest_sha256
        )
        with (
            mock.patch.object(module, "load_run_audit", wraps=module.load_run_audit) as lookup_load,
            mock.patch.object(module, "decide_safe_cache", wraps=module.decide_safe_cache) as lookup_decide,
        ):
            hit = module.lookup_safe_cache(cache_root, audit_root, *current)
        with (
            mock.patch.object(module, "load_run_audit", wraps=module.load_run_audit) as list_load,
            mock.patch.object(module, "decide_safe_cache", wraps=module.decide_safe_cache) as list_decide,
        ):
            listing = module.list_safe_cache(cache_root, audit_root)
        if (
            miss.status != "miss" or first.status != "stored"
            or repeat.status != "existing" or hit.status != "hit"
            or listing != (hit.lookup_key_sha256,)
            or first.record_sha256 != repeat.record_sha256
            or (persist_load.call_count, persist_decide.call_count) != (2, 4)
            or (lookup_load.call_count, lookup_decide.call_count) != (1, 2)
            or (list_load.call_count, list_decide.call_count) != (1, 0)
        ):
            _fail("store miss/write/repeat/hit/list cycle differs")
        key = str(hit.lookup_key_sha256)
        if key != EXPECTED_LOOKUP_KEYS["proved"]:
            _fail("cross-platform lookup key differs")
        current_root = cache_root / STORE_NAMESPACE
        record_path = current_root / "keys" / key[:2] / key
        _private_directory(current_root)
        _private_directory(current_root / "keys")
        _private_directory(current_root / "keys" / key[:2])
        _private_file(record_path)
        record_raw = record_path.read_bytes()
        record = json.loads(record_raw)
        if (
            record_raw != _canonical(record)
            or record.get("record_sha256") != _self_hash(record, "record_sha256")
            or record.get("lookup_key_sha256") != key
            or record.get("audit_manifest_sha256") != audited.bundle.manifest_sha256
            or record.get("execution_provenance_sha256") is None
        ):
            _fail("visible key record identity differs")
        object_digest = str(record["entry_object_sha256"])
        object_path = current_root / "objects" / object_digest[:2] / object_digest
        _private_file(object_path)
        object_raw = object_path.read_bytes()
        entry = json.loads(object_raw)
        if (
            _sha(object_raw) != object_digest
            or entry.get("execution_provenance_sha256")
            != record.get("execution_provenance_sha256")
            or entry.get("lookup_key_sha256") != key
            or entry.get("audit_manifest_sha256")
            != audited.bundle.manifest_sha256
        ):
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
        corrupt_record = corrupt / STORE_NAMESPACE / "keys" / key[:2] / key
        corrupt_record.write_bytes(corrupt_record.read_bytes() + b"x")
        rejected = module.lookup_safe_cache(corrupt, audit_root, *current)
        if (rejected.status, rejected.reason_code) != ("corrupt", "CACHE_ENTRY_CORRUPT"):
            _fail("corrupt visible record did not fail closed")
        orphan = current_root / "objects" / "ff" / ("f" * 64)
        orphan.parent.mkdir(mode=0o700, exist_ok=True)
        orphan.write_bytes(b"orphan\n")
        orphan.chmod(0o600)
        if module.list_safe_cache(cache_root, audit_root) != (key,):
            _fail("unreachable exact content changed listing")
        return {
            "platform_supported": True,
            "cross_platform_key_verified": True,
            "first_write_verified": True, "repeat_write_verified": True,
            "fresh_lookup_verified": True, "listing_verified": True,
            "persist_decisions": 4, "persist_audit_loads": 2,
            "lookup_decisions": 2, "lookup_audit_loads": 1,
            "listing_decisions": 0, "listing_audit_loads": 1,
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
