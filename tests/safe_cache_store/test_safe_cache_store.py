from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
except ImportError:  # dependency-minimal contract profile
    jsonschema = None  # type: ignore[assignment]

from mathhead.run_audit_store import RunAuditStoreError, persist_run_audit  # noqa: E402
import mathhead.safe_cache_store as store  # noqa: E402
from mathhead.safe_cache_store import (  # noqa: E402
    SafeCacheStoreError,
    SafeCacheStoreResult,
    list_safe_cache,
    lookup_safe_cache,
    parse_safe_cache_store_result,
    persist_safe_cache,
    safe_cache_store_result_bytes,
)
from tests.run_audit.fixtures import single_bundle  # noqa: E402
from tests.safe_cache.audited_fixtures import success_bundle  # noqa: E402


SCHEMAS = ROOT / "docs/contracts/schemas"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def cache_inputs(audited: object) -> tuple[object, ...]:
    bundle = audited.bundle
    manifest = json.loads(bundle.manifest)
    objects = {sha(raw): raw for raw in bundle.objects}
    by_role: dict[str, list[dict[str, object]]] = {}
    for record in manifest["objects"]:
        by_role.setdefault(record["role"], []).append(record)

    def one(role: str) -> bytes:
        records = by_role[role]
        if len(records) != 1:
            raise AssertionError(role)
        return objects[records[0]["sha256"]]

    request = json.loads(one("portfolio_request"))
    return (
        one("planning_request"), one("capability_route_result"),
        one("portfolio_request"), one("planning_result"),
        one("initial_parent_budget"),
        tuple(objects[item["sha256"]] for item in by_role["plugin_descriptor"]),
        tuple(objects[item["sha256"]] for item in by_role["execution_binding"]),
        tuple(objects[item["sha256"]] for item in request["artifact_bindings"]),
    )


class SafeCacheStoreContractTests(unittest.TestCase):
    def test_accepted_contract_schema_hashes_and_signatures_are_exact(self) -> None:
        self.assertEqual(
            sha((ROOT / "docs/contracts/MH-C-SAFE-CACHE-STORE-002.json").read_bytes()),
            store.STORE_CONTRACT_SHA256,
        )
        expected = {
            "mathhead.safe-cache-store-record.v2": "safe-cache-store-record-v2.schema.json",
            "mathhead.safe-cache-store-result.v2": "safe-cache-store-result-v2.schema.json",
        }
        self.assertEqual(
            {schema: sha((SCHEMAS / name).read_bytes()) for schema, name in expected.items()},
            store.SCHEMA_SHA256S,
        )
        with self.assertRaises(TypeError):
            store.SCHEMA_SHA256S[store.STORE_RECORD_SCHEMA] = "f" * 64  # type: ignore[index]
        self.assertEqual(
            str(inspect.signature(persist_safe_cache)),
            "(cache_root: 'Path', audit_root: 'Path', planning_request: 'bytes', route_result: 'bytes', portfolio_request: 'bytes', planning_result: 'bytes', parent_budget: 'bytes', descriptors: 'tuple[bytes, ...]', bindings: 'tuple[bytes, ...]', artifacts: 'tuple[bytes, ...]', manifest_sha256: 'str') -> 'SafeCacheStoreResult'",
        )
        self.assertEqual(
            str(inspect.signature(lookup_safe_cache)),
            "(cache_root: 'Path', audit_root: 'Path', planning_request: 'bytes', route_result: 'bytes', portfolio_request: 'bytes', planning_result: 'bytes', parent_budget: 'bytes', descriptors: 'tuple[bytes, ...]', bindings: 'tuple[bytes, ...]', artifacts: 'tuple[bytes, ...]') -> 'SafeCacheStoreResult'",
        )


class SafeCacheStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audited = success_bundle()
        cls.current = cache_inputs(cls.audited)

    def roots(self, base: Path) -> tuple[Path, Path]:
        return base / "cache", base / "audit"

    def prepare(self, base: Path, audited: object | None = None) -> tuple[Path, Path, object]:
        selected = self.audited if audited is None else audited
        cache_root, audit_root = self.roots(base)
        audit = persist_run_audit(audit_root, selected.bundle)
        if audit.status == "unsupported":
            self.skipTest("host cannot provide the descriptor-relative audit store")
        self.assertIn(audit.status, {"stored", "existing"})
        return cache_root, audit_root, selected

    def test_unsupported_cache_store_is_explicit_and_effect_free(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-unsupported-", dir=ROOT) as raw:
            cache_root, audit_root = self.roots(Path(raw).resolve())
            with (
                mock.patch.object(store, "_descriptor_store_supported", return_value=False),
                mock.patch.object(
                    store, "load_run_audit", return_value=self.audited.bundle
                ) as load,
            ):
                lookup = lookup_safe_cache(cache_root, audit_root, *self.current)
                persisted = persist_safe_cache(
                    cache_root,
                    audit_root,
                    *self.current,
                    self.audited.bundle.manifest_sha256,
                )
            self.assertEqual(
                (lookup.status, lookup.reason_code),
                ("unsupported", "CACHE_STORE_UNSUPPORTED"),
            )
            self.assertEqual(
                (persisted.status, persisted.reason_code),
                ("unsupported", "CACHE_STORE_UNSUPPORTED"),
            )
            self.assertEqual(load.call_count, 1)
            self.assertFalse(cache_root.exists())
            self.assertFalse(audit_root.exists())

    def test_missing_write_repeat_lookup_and_listing_are_exact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-store-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            before = lookup_safe_cache(cache_root, audit_root, *self.current)
            first = persist_safe_cache(
                cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
            )
            repeat = persist_safe_cache(
                cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
            )
            hit = lookup_safe_cache(cache_root, audit_root, *self.current)
            self.assertEqual((before.status, before.reason_code), ("miss", "CACHE_KEY_ABSENT"))
            self.assertEqual((first.status, first.reason_code), ("stored", "CACHE_ENTRY_STORED"))
            self.assertEqual((repeat.status, repeat.reason_code), ("existing", "CACHE_ENTRY_ALREADY_EXISTS"))
            self.assertEqual((hit.status, hit.reason_code), ("hit", "CACHE_HIT"))
            self.assertEqual(first.lookup_key_sha256, repeat.lookup_key_sha256)
            self.assertEqual(first.record_sha256, repeat.record_sha256)
            self.assertEqual(list_safe_cache(cache_root, audit_root), (hit.lookup_key_sha256,))
            self.assertEqual(
                parse_safe_cache_store_result(safe_cache_store_result_bytes(hit)), hit
            )
            if jsonschema is not None:
                schema = json.loads((SCHEMAS / "safe-cache-store-result-v2.schema.json").read_text())
                jsonschema.Draft202012Validator(schema).validate(
                    json.loads(safe_cache_store_result_bytes(hit))
                )

    def test_present_lookup_runs_public_audit_load_and_pure_decision_cycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-cycle-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            persist_safe_cache(
                cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
            )
            with (
                mock.patch.object(store, "load_run_audit", wraps=store.load_run_audit) as load,
                mock.patch.object(store, "decide_safe_cache", wraps=store.decide_safe_cache) as decide,
            ):
                result = lookup_safe_cache(cache_root, audit_root, *self.current)
            self.assertEqual(result.status, "hit")
            self.assertEqual(load.call_count, 1)
            self.assertEqual(decide.call_count, 2)

    def test_successful_persist_runs_exact_pre_and_post_validation_cycles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-persist-cycle-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            with (
                mock.patch.object(store, "load_run_audit", wraps=store.load_run_audit) as load,
                mock.patch.object(store, "decide_safe_cache", wraps=store.decide_safe_cache) as decide,
            ):
                result = persist_safe_cache(
                    cache_root, audit_root, *self.current,
                    audited.bundle.manifest_sha256,
                )
            self.assertEqual(result.status, "stored")
            self.assertEqual(load.call_count, 2)
            self.assertEqual(decide.call_count, 4)

    def test_listing_uses_one_audit_load_and_no_safe_cache_decision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-list-cycle-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            persisted = persist_safe_cache(
                cache_root, audit_root, *self.current,
                audited.bundle.manifest_sha256,
            )
            with (
                mock.patch.object(store, "load_run_audit", wraps=store.load_run_audit) as load,
                mock.patch.object(store, "decide_safe_cache", wraps=store.decide_safe_cache) as decide,
            ):
                listed = list_safe_cache(cache_root, audit_root)
            self.assertEqual(listed, (persisted.lookup_key_sha256,))
            self.assertEqual(load.call_count, 1)
            self.assertEqual(decide.call_count, 0)

    def test_invalid_separated_roots_and_invalid_current_input_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-roots-", dir=ROOT) as raw:
            base = Path(raw).resolve()
            same = lookup_safe_cache(base, base, *self.current)
            nested = persist_safe_cache(
                base, base / "audit", *self.current, self.audited.bundle.manifest_sha256
            )
            broken = lookup_safe_cache(base / "cache", base / "audit", b"{}\n", *self.current[1:])
            self.assertEqual((same.status, same.reason_code), ("invalid", "CACHE_PATH_INVALID"))
            self.assertEqual((nested.status, nested.reason_code), ("invalid", "CACHE_PATH_INVALID"))
            self.assertEqual((broken.status, broken.reason_code), ("invalid", "CACHE_REQUEST_INVALID"))

    def test_ineligible_and_missing_audit_run_are_never_persisted(self) -> None:
        ineligible = single_bundle(evidence_status="unsupported")
        with tempfile.TemporaryDirectory(prefix="mh055-cache-ineligible-", dir=ROOT) as raw:
            base = Path(raw).resolve()
            cache_root, audit_root, _ = self.prepare(base, ineligible)
            current = cache_inputs(ineligible)
            result = persist_safe_cache(
                cache_root, audit_root, *current, ineligible.bundle.manifest_sha256
            )
            missing = persist_safe_cache(
                cache_root, audit_root, *self.current, "f" * 64
            )
            self.assertEqual((result.status, result.reason_code), ("ineligible", "CACHE_RUN_INELIGIBLE"))
            self.assertEqual((missing.status, missing.reason_code), ("invalid", "CACHE_AUDIT_RUN_MISSING"))
            self.assertFalse(cache_root.exists())

    def test_corrupt_record_object_and_hardlink_state_never_hit_or_list(self) -> None:
        for target_kind in ("record", "object", "hardlink"):
            with tempfile.TemporaryDirectory(prefix="mh055-cache-corrupt-", dir=ROOT) as raw:
                base = Path(raw).resolve()
                cache_root, audit_root, audited = self.prepare(base)
                first = persist_safe_cache(
                    cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
                )
                assert first.lookup_key_sha256 is not None
                current_root = cache_root / store.STORE_NAMESPACE
                record_path = current_root / "keys" / first.lookup_key_sha256[:2] / first.lookup_key_sha256
                record = json.loads(record_path.read_bytes())
                object_digest = record["entry_object_sha256"]
                object_path = current_root / "objects" / object_digest[:2] / object_digest
                if target_kind == "record":
                    record_path.write_bytes(record_path.read_bytes() + b"x")
                elif target_kind == "object":
                    object_path.write_bytes(object_path.read_bytes() + b"x")
                else:
                    os.link(object_path, base / "external-link")
                result = lookup_safe_cache(cache_root, audit_root, *self.current)
                self.assertEqual((result.status, result.reason_code), ("corrupt", "CACHE_ENTRY_CORRUPT"))
                with self.assertRaises(SafeCacheStoreError):
                    list_safe_cache(cache_root, audit_root)

    def test_repaired_record_provenance_swap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-provenance-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            result = persist_safe_cache(
                cache_root, audit_root, *self.current,
                audited.bundle.manifest_sha256,
            )
            assert result.lookup_key_sha256 is not None
            record_path = (
                cache_root / store.STORE_NAMESPACE / "keys"
                / result.lookup_key_sha256[:2] / result.lookup_key_sha256
            )
            record = json.loads(record_path.read_bytes())
            record["execution_provenance_sha256"] = "f" * 64
            record["record_sha256"] = None
            record["record_sha256"] = sha(store._canonical(record))
            record_path.write_bytes(store._canonical(record))
            self.assertEqual(
                lookup_safe_cache(cache_root, audit_root, *self.current).reason_code,
                "CACHE_ENTRY_CORRUPT",
            )
            with self.assertRaises(SafeCacheStoreError):
                list_safe_cache(cache_root, audit_root)

    def test_legacy_root_level_v1_layout_is_not_current_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-legacy-", dir=ROOT) as raw:
            base = Path(raw).resolve()
            cache_root, audit_root, _audited = self.prepare(base)
            cache_root.mkdir(mode=0o700)
            (cache_root / "keys").mkdir(mode=0o700)
            (cache_root / "objects").mkdir(mode=0o700)
            self.assertEqual(list_safe_cache(cache_root, audit_root), ())
            result = lookup_safe_cache(cache_root, audit_root, *self.current)
            self.assertEqual((result.status, result.reason_code), ("miss", "CACHE_KEY_ABSENT"))

    def test_same_key_concurrent_writers_converge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-concurrent-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())

            def write(_: int) -> object:
                return persist_safe_cache(
                    cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
                )

            with ThreadPoolExecutor(max_workers=4) as pool:
                results = tuple(pool.map(write, range(4)))
            self.assertEqual(sum(item.status == "stored" for item in results), 1)
            self.assertTrue(all(item.status in {"stored", "existing"} for item in results))
            self.assertEqual(len({item.record_sha256 for item in results}), 1)

    def test_key_commit_failure_leaves_only_unreachable_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-interrupt-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            original = store._write_immutable
            count = 0

            def fail_reference(*args: object, **kwargs: object) -> bool:
                nonlocal count
                count += 1
                if count == 2:
                    raise SafeCacheStoreError("io", "injected key commit failure")
                return original(*args, **kwargs)

            with mock.patch.object(store, "_write_immutable", side_effect=fail_reference):
                result = persist_safe_cache(
                    cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
                )
            self.assertEqual((result.status, result.reason_code), ("io_error", "CACHE_STORE_IO_ERROR"))
            self.assertEqual(
                lookup_safe_cache(cache_root, audit_root, *self.current).status, "miss"
            )

    def test_post_commit_audit_failure_rolls_back_new_visible_key(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-post-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            original = store.load_run_audit
            count = 0

            def fail_second(*args: object, **kwargs: object) -> object:
                nonlocal count
                count += 1
                if count == 2:
                    raise RunAuditStoreError("io", "injected post-commit failure")
                return original(*args, **kwargs)

            with mock.patch.object(store, "load_run_audit", side_effect=fail_second):
                result = persist_safe_cache(
                    cache_root, audit_root, *self.current,
                    audited.bundle.manifest_sha256,
                )
            self.assertEqual(
                (result.status, result.reason_code),
                ("io_error", "CACHE_AUDIT_STORE_IO_ERROR"),
            )
            self.assertEqual(
                lookup_safe_cache(cache_root, audit_root, *self.current).status,
                "miss",
            )

    def test_compound_post_commit_cleanup_failure_cannot_leave_a_hit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-compound-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            original = store.load_run_audit
            count = 0

            def fail_second(*args: object, **kwargs: object) -> object:
                nonlocal count
                count += 1
                if count == 2:
                    raise RunAuditStoreError("io", "injected post-commit failure")
                return original(*args, **kwargs)

            with (
                mock.patch.object(store, "load_run_audit", side_effect=fail_second),
                mock.patch.object(
                    store, "_quarantine",
                    side_effect=SafeCacheStoreError(
                        "io", "injected quarantine failure"
                    ),
                ),
            ):
                result = persist_safe_cache(
                    cache_root, audit_root, *self.current,
                    audited.bundle.manifest_sha256,
                )
            self.assertEqual(result.status, "io_error")
            self.assertEqual(
                lookup_safe_cache(cache_root, audit_root, *self.current).status,
                "miss",
            )

    def test_interruption_at_key_install_return_cannot_leave_a_hit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-key-return-", dir=ROOT) as raw:
            cache_root, audit_root, audited = self.prepare(Path(raw).resolve())
            original = store._write_immutable
            count = 0

            def interrupt_after_install(*args: object, **kwargs: object) -> bool:
                nonlocal count
                count += 1
                created = original(*args, **kwargs)
                if count == 2:
                    raise KeyboardInterrupt
                return created

            with (
                mock.patch.object(
                    store, "_write_immutable", side_effect=interrupt_after_install
                ),
                self.assertRaises(KeyboardInterrupt),
            ):
                persist_safe_cache(
                    cache_root, audit_root, *self.current,
                    audited.bundle.manifest_sha256,
                )
            self.assertEqual(
                lookup_safe_cache(cache_root, audit_root, *self.current).status,
                "miss",
            )

    def test_relocation_preserves_hit_and_logical_listing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-relocate-", dir=ROOT) as raw:
            base = Path(raw).resolve()
            cache_root, audit_root, audited = self.prepare(base / "first")
            first = persist_safe_cache(
                cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
            )
            second = base / "second"
            second.mkdir(mode=0o700)
            moved_cache, moved_audit = second / "cache", second / "audit"
            shutil.copytree(cache_root, moved_cache)
            shutil.copytree(audit_root, moved_audit)
            hit = lookup_safe_cache(moved_cache, moved_audit, *self.current)
            self.assertEqual((hit.status, hit.result_sha256), ("hit", lookup_safe_cache(cache_root, audit_root, *self.current).result_sha256))
            self.assertEqual(list_safe_cache(moved_cache, moved_audit), (first.lookup_key_sha256,))

    def test_result_values_are_final_immutable_and_repaired_shapes_fail(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mh055-cache-values-", dir=ROOT) as raw:
            cache_root, audit_root, _ = self.prepare(Path(raw).resolve())
            value = lookup_safe_cache(cache_root, audit_root, *self.current)
        with self.assertRaises(PermissionError):
            SafeCacheStoreResult()  # type: ignore[call-arg]
        with self.assertRaises(TypeError):
            type("Derived", (SafeCacheStoreResult,), {})
        with self.assertRaises(FrozenInstanceError):
            value.status = "hit"  # type: ignore[misc]
        with self.assertRaises((TypeError, PermissionError)):
            replace(value, status="hit")
        with self.assertRaises(TypeError):
            pickle.dumps(value)
        for operation in (copy.copy, copy.deepcopy):
            try:
                self.assertIs(operation(value), value)
            except TypeError:
                pass
        raw_value = json.loads(safe_cache_store_result_bytes(value))
        raw_value["status"] = "hit"
        raw_value["reason_code"] = "CACHE_HIT"
        raw_value["result_sha256"] = None
        raw_value["result_sha256"] = sha(store._canonical(raw_value))
        with self.assertRaises(SafeCacheStoreError):
            parse_safe_cache_store_result(store._canonical(raw_value))
        forged = json.loads(safe_cache_store_result_bytes(value))
        forged["status"] = "corrupt"
        forged["reason_code"] = "CALLER_FORGED_REASON"
        forged["result_sha256"] = None
        forged["result_sha256"] = sha(store._canonical(forged))
        with self.assertRaises(SafeCacheStoreError):
            parse_safe_cache_store_result(store._canonical(forged))

    def test_result_codec_matches_every_closed_v2_schema_row(self) -> None:
        schema = json.loads(
            (SCHEMAS / "safe-cache-store-result-v2.schema.json").read_text()
        )
        rows = 0
        for branch in schema["allOf"][0]["oneOf"]:
            properties = branch["properties"]
            reason_spec = properties["reason_code"]
            reasons = reason_spec.get("enum")
            if reasons is None:
                reasons = (reason_spec["const"],)
            for reason in reasons:
                kwargs: dict[str, object] = {}
                for field, argument in (
                    ("lookup_key_sha256", "lookup"),
                    ("entry_sha256", "entry"),
                    ("audit_manifest_sha256", "manifest"),
                    ("record_sha256", "record"),
                    ("historical_authority_tier", "tier"),
                ):
                    spec = properties[field]
                    if spec.get("type") != "null":
                        kwargs[argument] = (
                            "checker_attestation"
                            if field == "historical_authority_tier"
                            else "a" * 64
                        )
                value = store._new_result(
                    properties["operation"]["const"],
                    properties["status"]["const"],
                    reason,
                    **kwargs,
                )
                validate = json.loads(safe_cache_store_result_bytes(value))
                if jsonschema is not None:
                    jsonschema.Draft202012Validator(schema).validate(validate)
                rows += 1
        self.assertEqual(rows, 31)


if __name__ == "__main__":
    unittest.main()
