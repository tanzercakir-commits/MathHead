from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import errno
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import shutil
import stat
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
except ImportError:  # dependency-minimal contract profile
    jsonschema = None  # type: ignore[assignment]

from mathhead.run_audit import RunAuditValidationError  # noqa: E402
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

    def test_codec_record_and_result_failure_matrix_is_closed(self) -> None:
        with self.assertRaises(store._DuplicateKey):
            store._pairs([("duplicate", 1), ("duplicate", 2)])
        for value, maximum, kind in (
            ({"value": object()}, store.MAX_RECORD_BYTES, "record"),
            ({"value": "too large"}, 1, "budget"),
        ):
            with self.subTest(kind=kind), self.assertRaises(SafeCacheStoreError) as caught:
                store._canonical(value, maximum)
            self.assertEqual(caught.exception.kind, kind)
        for raw, kind in (
            (b"", "budget"),
            (b'{"value":1,"value":2}\n', "record"),
            (b'{"value":1.5}\n', "record"),
            (b'{"value":1}', "record"),
        ):
            with self.subTest(raw=raw), self.assertRaises(SafeCacheStoreError) as caught:
                store._parse(raw)
            self.assertEqual(caught.exception.kind, kind)
        with self.assertRaises(SafeCacheStoreError):
            store._digest("A" * 64, "digest")

        decision = store.decide_safe_cache(*self.current, self.audited.bundle)
        assert decision.entry is not None
        record_raw, _record_identity, _entry_object = store._record_bytes(decision.entry)
        record = json.loads(record_raw)
        mutations = (
            lambda value: value.pop("entry_sha256"),
            lambda value: value.__setitem__("schema", "mathhead.wrong"),
            lambda value: value.__setitem__("record_sha256", "a" * 64),
        )
        for index, mutate in enumerate(mutations):
            value = dict(record)
            mutate(value)
            if index == 1:
                value["record_sha256"] = None
                value["record_sha256"] = store._self_hash(value, "record_sha256")
            with self.subTest(record_mutation=index), self.assertRaises(SafeCacheStoreError):
                store._parse_record(store._canonical(value), decision.entry.lookup_key_sha256)

        with self.assertRaises(SafeCacheStoreError):
            store.validate_safe_cache_store_result(object())  # type: ignore[arg-type]
        miss = store._new_result("lookup", "miss", "CACHE_KEY_ABSENT", lookup="a" * 64)
        mapping = store._result_mapping(miss)
        forged = dict(mapping)
        forged["contract_sha256"] = "b" * 64
        forged["result_sha256"] = store._self_hash(forged, "result_sha256")
        with self.assertRaises(SafeCacheStoreError):
            store.validate_safe_cache_store_result(
                store._make(SafeCacheStoreResult, **forged)
            )
        hit = store._new_result(
            "lookup", "hit", "CACHE_HIT", lookup="a" * 64,
            entry="b" * 64, manifest="c" * 64, record="d" * 64,
            tier="checker_attestation",
        )
        forged_tier = store._result_mapping(hit)
        forged_tier["historical_authority_tier"] = "caller_forged_tier"
        forged_tier["result_sha256"] = store._self_hash(
            forged_tier, "result_sha256"
        )
        with self.assertRaises(SafeCacheStoreError):
            store.validate_safe_cache_store_result(
                store._make(SafeCacheStoreResult, **forged_tier)
            )
        with self.assertRaises(SafeCacheStoreError):
            store._result_from_mapping({})
        with self.assertRaises(SafeCacheStoreError):
            store._shape({"operation": "lookup", "status": "hit", "reason_code": "NOPE"})
        wrong_nullability = store._result_mapping(miss)
        wrong_nullability["entry_sha256"] = "b" * 64
        with self.assertRaises(SafeCacheStoreError):
            store._shape(wrong_nullability)

    def test_metadata_path_and_low_level_io_fail_closed(self) -> None:
        uid = os.geteuid() if hasattr(os, "geteuid") else 0
        directory = SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o700, st_uid=uid, st_dev=1, st_ino=2
        )
        regular = SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600, st_uid=uid, st_dev=1, st_ino=2,
            st_nlink=1,
        )
        store._directory_info(directory, private=True)
        store._file_info(regular)
        directory_cases = [
            SimpleNamespace(st_mode=stat.S_IFREG | 0o700, st_uid=uid),
            SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_uid=uid),
        ]
        file_cases = [
            SimpleNamespace(st_mode=stat.S_IFDIR | 0o600, st_uid=uid, st_nlink=1),
            SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_uid=uid, st_nlink=2),
            SimpleNamespace(st_mode=stat.S_IFREG | 0o644, st_uid=uid, st_nlink=1),
        ]
        if hasattr(os, "geteuid"):
            directory_cases.append(
                SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=uid + 1)
            )
            file_cases.append(
                SimpleNamespace(
                    st_mode=stat.S_IFREG | 0o600,
                    st_uid=uid + 1,
                    st_nlink=1,
                )
            )
        for info in directory_cases:
            with self.subTest(directory=info.st_mode), self.assertRaises(SafeCacheStoreError):
                store._directory_info(info, private=True)
        for info in file_cases:
            with self.subTest(file=info.st_mode), self.assertRaises(SafeCacheStoreError):
                store._file_info(info)
        for code, kind in ((errno.ENOTSUP, "unsupported"), (errno.EIO, "io")):
            with self.subTest(code=code), self.assertRaises(SafeCacheStoreError) as caught:
                store._classify_io(OSError(code, "probe"), "probe")
            self.assertEqual(caught.exception.kind, kind)

        for root in ("not-a-path", Path("relative"), Path(Path().anchor)):
            with self.subTest(root=root), self.assertRaises(SafeCacheStoreError):
                store._validate_root_path(root)  # type: ignore[arg-type]
        absolute = ROOT / "same-root"
        with self.assertRaises(SafeCacheStoreError):
            store._validate_roots(absolute, absolute)
        with mock.patch.object(store.os.path, "commonpath", side_effect=ValueError):
            store._validate_roots(ROOT / "cache-a", ROOT / "audit-a")
        with (
            mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._validate_roots(ROOT / "cache-c", ROOT / "audit-c")
        self.assertEqual(caught.exception.kind, "io")
        same = SimpleNamespace(st_dev=7, st_ino=11)
        with mock.patch.object(store.os, "stat", side_effect=(same, same)):
            with self.assertRaises(SafeCacheStoreError):
                store._validate_roots(ROOT / "cache-b", ROOT / "audit-b")

        identity = store._DirectoryIdentity(ROOT, 1, 2)
        pinned = store._PinnedRoot(ROOT, -1, (identity,))
        with mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")):
            with self.assertRaises(SafeCacheStoreError):
                store._guard_root(pinned)
        changed = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_dev=1, st_ino=3)
        with mock.patch.object(store.os, "stat", return_value=changed):
            with self.assertRaises(SafeCacheStoreError):
                store._guard_root(pinned)

        with mock.patch.object(store.os, "write", side_effect=OSError(errno.EIO, "write")):
            with self.assertRaises(SafeCacheStoreError):
                store._write_all(-1, b"data")
        with mock.patch.object(store.os, "write", return_value=0):
            with self.assertRaises(SafeCacheStoreError):
                store._write_all(-1, b"data")
        with mock.patch.object(store, "_read_bounded", return_value=b"different"):
            with self.assertRaises(SafeCacheStoreError):
                store._read_existing(pinned, -1, "a" * 64, b"expected")
        transient = SafeCacheStoreError("link", "transient")
        if hasattr(store.os, "sched_yield"):
            with (
                mock.patch.object(
                    store,
                    "_read_bounded",
                    side_effect=(transient, b"expected"),
                ),
                mock.patch.object(store.os, "sched_yield") as yielded,
            ):
                store._read_existing(pinned, -1, "a" * 64, b"expected")
            yielded.assert_called_once_with()
        else:
            with (
                mock.patch.object(store, "_read_bounded", side_effect=transient),
                self.assertRaises(SafeCacheStoreError),
            ):
                store._read_existing(pinned, -1, "a" * 64, b"expected")

    def test_descriptor_reads_and_immutable_install_fail_closed(self) -> None:
        uid = os.geteuid() if hasattr(os, "geteuid") else 0
        root = store._PinnedRoot(ROOT / store.STORE_NAMESPACE, 11, ())
        directory = SimpleNamespace(
            st_mode=stat.S_IFDIR | 0o700,
            st_uid=uid,
            st_dev=1,
            st_ino=2,
        )
        linked = SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600,
            st_uid=uid,
            st_dev=1,
            st_ino=2,
            st_nlink=1,
            st_size=4,
        )

        if not store._descriptor_store_supported():
            with self.assertRaises(SafeCacheStoreError) as caught:
                store._open_root(ROOT / "cache", create=False)
            self.assertEqual(caught.exception.kind, "unsupported")
            return

        for probe, expected in ((False, "io"), (True, "unsupported")):
            with (
                self.subTest(fsync_probe=probe),
                mock.patch.object(store.os, "fstat", return_value=directory),
                mock.patch.object(
                    store.os,
                    "fsync",
                    side_effect=OSError(errno.ENOTSUP, "probe"),
                ),
                self.assertRaises(SafeCacheStoreError) as caught,
            ):
                store._fsync_directory(root, 11, probe=probe)
            self.assertEqual(caught.exception.kind, expected)

        for name in ("", ".", "..", "a/b", "a\\b"):
            with self.subTest(child=name), self.assertRaises(SafeCacheStoreError):
                store._open_child(root, 11, name, create=False)
        with (
            mock.patch.object(store.os, "stat", side_effect=FileNotFoundError),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=False)
        self.assertEqual(caught.exception.kind, "missing")
        with (
            mock.patch.object(store, "_descriptor_store_supported", return_value=False),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_root(ROOT / "cache", create=False)
        self.assertEqual(caught.exception.kind, "unsupported")
        with (
            mock.patch.object(store.os, "stat", side_effect=FileNotFoundError),
            mock.patch.object(store.os, "mkdir", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=True)
        self.assertEqual(caught.exception.kind, "io")
        with (
            mock.patch.object(
                store.os,
                "stat",
                side_effect=(FileNotFoundError, OSError(errno.EIO, "probe")),
            ),
            mock.patch.object(store.os, "mkdir"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=True)
        self.assertEqual(caught.exception.kind, "io")
        with (
            mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=False)
        self.assertEqual(caught.exception.kind, "io")
        with (
            mock.patch.object(store.os, "stat", return_value=directory),
            mock.patch.object(store.os, "open", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=False)
        self.assertEqual(caught.exception.kind, "io")
        changed = SimpleNamespace(**{**directory.__dict__, "st_ino": 3})
        with (
            mock.patch.object(store.os, "stat", return_value=directory),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fstat", return_value=changed),
            mock.patch.object(store.os, "close"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._open_child(root, 11, "child", create=False)
        self.assertEqual(caught.exception.kind, "link")
        with (
            mock.patch.object(
                store,
                "_guard_root",
                side_effect=(None, SafeCacheStoreError("link", "probe")),
            ),
            mock.patch.object(store.os, "stat", return_value=directory),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fstat", return_value=directory),
            mock.patch.object(store.os, "close") as closed,
            self.assertRaises(SafeCacheStoreError),
        ):
            store._open_child(root, 11, "child", create=False)
        closed.assert_called_once_with(12)

        with (
            mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._read_bounded(root, 11, "entry", 8)
        self.assertEqual(caught.exception.kind, "io")
        changed_file = SimpleNamespace(**{**linked.__dict__, "st_ino": 3})
        with (
            mock.patch.object(store.os, "stat", return_value=linked),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fstat", return_value=changed_file),
            mock.patch.object(store.os, "close"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._read_bounded(root, 11, "entry", 8)
        self.assertEqual(caught.exception.kind, "link")
        empty = SimpleNamespace(**{**linked.__dict__, "st_size": 0})
        with (
            mock.patch.object(store.os, "stat", return_value=empty),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fstat", return_value=empty),
            mock.patch.object(store.os, "close"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._read_bounded(root, 11, "entry", 8)
        self.assertEqual(caught.exception.kind, "budget")
        for read_effect, fstats, expected in (
            (OSError(errno.EIO, "probe"), (linked,), "io"),
            ((b"",), (linked,), "partial"),
            ((b"data", b"x"), (linked,), "corrupt"),
            ((b"data", OSError(errno.EIO, "probe")), (linked,), "io"),
            ((b"data", b""), (linked, changed_file), "corrupt"),
        ):
            with (
                self.subTest(read=expected),
                mock.patch.object(store.os, "stat", return_value=linked),
                mock.patch.object(store.os, "open", return_value=12),
                mock.patch.object(store.os, "fstat", side_effect=fstats),
                mock.patch.object(store.os, "read", side_effect=read_effect),
                mock.patch.object(store.os, "close"),
                self.assertRaises(SafeCacheStoreError) as caught,
            ):
                store._read_bounded(root, 11, "entry", 8)
            self.assertEqual(caught.exception.kind, expected)

        with (
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fstat", return_value=directory),
            mock.patch.object(store.os, "close"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._quarantine(root, 11, target="entry")
        self.assertEqual(caught.exception.kind, "link")
        with (
            mock.patch.object(store.os, "open", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._quarantine(root, 11, target="entry")
        self.assertEqual(caught.exception.kind, "io")

        target = sha(b"data")
        with self.assertRaises(SafeCacheStoreError):
            store._write_immutable_locked(root, 11, "a" * 64, b"data")
        with (
            mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._write_immutable_locked(root, 11, target, b"data")
        self.assertEqual(caught.exception.kind, "io")

        with (
            mock.patch.object(store.os, "stat", side_effect=FileNotFoundError),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fchmod"),
            mock.patch.object(store, "_write_all"),
            mock.patch.object(store.os, "fsync"),
            mock.patch.object(store.os, "close"),
            mock.patch.object(store, "_read_existing"),
            mock.patch.object(store, "_fsync_directory"),
            mock.patch.object(store.os, "link", side_effect=FileExistsError),
            mock.patch.object(store.os, "unlink"),
        ):
            self.assertFalse(store._write_immutable_locked(root, 11, target, b"data"))
        with (
            mock.patch.object(store.os, "stat", side_effect=FileNotFoundError),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fchmod"),
            mock.patch.object(store, "_write_all"),
            mock.patch.object(store.os, "fsync"),
            mock.patch.object(store.os, "close"),
            mock.patch.object(store, "_read_existing"),
            mock.patch.object(store, "_fsync_directory"),
            mock.patch.object(store.os, "link", side_effect=OSError(errno.EIO, "probe")),
            mock.patch.object(store.os, "unlink"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._write_immutable_locked(root, 11, target, b"data")
        self.assertEqual(caught.exception.kind, "io")

        with (
            mock.patch.object(store.os, "stat", side_effect=FileNotFoundError),
            mock.patch.object(store.os, "open", return_value=12),
            mock.patch.object(store.os, "fchmod"),
            mock.patch.object(store, "_write_all"),
            mock.patch.object(store.os, "fsync"),
            mock.patch.object(store.os, "close"),
            mock.patch.object(store.os, "link"),
            mock.patch.object(
                store.os,
                "unlink",
                side_effect=(OSError(errno.EIO, "cleanup"), None, None),
            ),
            mock.patch.object(store, "_quarantine"),
            mock.patch.object(store, "_fsync_directory"),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._write_immutable_locked(root, 11, target, b"data")
        self.assertEqual(caught.exception.kind, "io")

        with mock.patch.object(store.os, "stat", side_effect=FileNotFoundError):
            self.assertFalse(store._target_present(root, 11, target))
        with mock.patch.object(store.os, "stat", return_value=linked):
            self.assertTrue(store._target_present(root, 11, target))
        with (
            mock.patch.object(store.os, "stat", side_effect=OSError(errno.EIO, "probe")),
            self.assertRaises(SafeCacheStoreError) as caught,
        ):
            store._target_present(root, 11, target)
        self.assertEqual(caught.exception.kind, "io")

    def test_decision_audit_and_post_lookup_projection_matrix_is_exact(self) -> None:
        exhausted = store._decision_failure(
            "lookup", SimpleNamespace(status="exhausted")
        )
        invalid = store._decision_failure("persist", SimpleNamespace(status="invalid"))
        self.assertEqual(exhausted.reason_code, "CACHE_CURRENT_BUDGET_EXHAUSTED")
        self.assertEqual(invalid.reason_code, "CACHE_REQUEST_INVALID")

        candidate_rows = (
            ("persist", "exhausted", "CACHE_REPLAY_EXHAUSTED", "CACHE_AUDIT_REPLAY_EXHAUSTED"),
            ("persist", "ineligible", "CACHE_OUTCOME_INELIGIBLE", "CACHE_RUN_INELIGIBLE"),
            ("lookup", "ineligible", "CACHE_AUTHORITY_INELIGIBLE", "CACHE_ENTRY_STALE"),
            ("persist", "invalid", "CACHE_REPLAY_INVALID", "CACHE_AUDIT_REPLAY_INVALID"),
            ("lookup", "invalid", "CACHE_REPLAY_INVALID", "CACHE_AUDIT_REPLAY_INVALID"),
            ("persist", "invalid", "CACHE_IMPLEMENTATION_MISMATCH", "CACHE_CANDIDATE_MISMATCH"),
            ("lookup", "invalid", "CACHE_TRUST_POLICY_MISMATCH", "CACHE_ENTRY_STALE"),
        )
        for operation, status, reason, expected in candidate_rows:
            with self.subTest(operation=operation, reason=reason):
                result = store._candidate_failure(
                    operation, SimpleNamespace(status=status, reason_code=reason),
                    "a" * 64, "b" * 64,
                )
                self.assertEqual(result.reason_code, expected)
        with self.assertRaises(SafeCacheStoreError):
            store._candidate_failure(
                "lookup", SimpleNamespace(status="invalid", reason_code="CALLER_REASON"),
                "a" * 64, "b" * 64,
            )

        post_rows = (
            ("CACHE_ENTRY_STALE", "invalid", "CACHE_CANDIDATE_MISMATCH"),
            ("CACHE_AUDIT_RUN_MISSING", "invalid", "CACHE_AUDIT_RUN_MISSING"),
            ("CACHE_AUDIT_REPLAY_INVALID", "invalid", "CACHE_AUDIT_REPLAY_INVALID"),
            ("CACHE_AUDIT_REPLAY_EXHAUSTED", "exhausted", "CACHE_AUDIT_REPLAY_EXHAUSTED"),
            ("CACHE_STORE_BUDGET_EXHAUSTED", "exhausted", "CACHE_STORE_BUDGET_EXHAUSTED"),
            ("CACHE_STORE_UNSUPPORTED", "unsupported", "CACHE_STORE_UNSUPPORTED"),
            ("CACHE_AUDIT_STORE_UNSUPPORTED", "unsupported", "CACHE_AUDIT_STORE_UNSUPPORTED"),
            ("CACHE_AUDIT_STORE_IO_ERROR", "io_error", "CACHE_AUDIT_STORE_IO_ERROR"),
            ("UNKNOWN_INTERNAL_REASON", "io_error", "CACHE_STORE_IO_ERROR"),
        )
        for reason, status, expected in post_rows:
            with self.subTest(post=reason):
                result = store._post_lookup_failure(
                    SimpleNamespace(reason_code=reason), "a" * 64, "b" * 64
                )
                self.assertEqual((result.status, result.reason_code), (status, expected))

        audit_rows = (
            ("persist", "missing", "invalid", "CACHE_AUDIT_RUN_MISSING"),
            ("lookup", "missing", "corrupt", "CACHE_AUDIT_RUN_MISSING"),
            ("lookup", "unsupported", "unsupported", "CACHE_AUDIT_STORE_UNSUPPORTED"),
            ("persist", "budget", "invalid", "CACHE_AUDIT_REPLAY_INVALID"),
            ("lookup", "owner", "corrupt", "CACHE_AUDIT_REPLAY_INVALID"),
            ("lookup", "io", "io_error", "CACHE_AUDIT_STORE_IO_ERROR"),
        )
        for operation, kind, status, reason in audit_rows:
            with self.subTest(audit=kind, operation=operation):
                result = store._map_audit_error(
                    operation, RunAuditStoreError(kind, "probe"), "a" * 64, "b" * 64
                )
                self.assertEqual((result.status, result.reason_code), (status, reason))
        self.assertEqual(
            store._map_audit_validation_error(
                "lookup", "a" * 64, "b" * 64
            ).status,
            "corrupt",
        )

    def test_public_lookup_and_persist_failure_projection_is_closed(self) -> None:
        key = "a" * 64
        manifest = self.audited.bundle.manifest_sha256
        current = SimpleNamespace(status="miss", lookup_key_sha256=key)
        decision = store.decide_safe_cache(*self.current, self.audited.bundle)
        assert decision.entry is not None
        record = {"record_sha256": "b" * 64}

        for kind, expected in (
            ("unsupported", ("unsupported", "CACHE_STORE_UNSUPPORTED")),
            ("budget", ("exhausted", "CACHE_STORE_BUDGET_EXHAUSTED")),
            ("io", ("io_error", "CACHE_STORE_IO_ERROR")),
        ):
            with (
                self.subTest(lookup_open=kind),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_current_decision", return_value=current),
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(
                    store,
                    "_open_root",
                    side_effect=SafeCacheStoreError(kind, "probe"),
                ),
            ):
                result = lookup_safe_cache(ROOT / "cache", ROOT / "audit", *self.current)
            self.assertEqual((result.status, result.reason_code), expected)

        for kind, expected in (
            ("budget", ("exhausted", "CACHE_STORE_BUDGET_EXHAUSTED")),
            ("io", ("io_error", "CACHE_STORE_IO_ERROR")),
        ):
            pinned = SimpleNamespace(descriptor=11, close=mock.Mock())
            with (
                self.subTest(lookup_entry=kind),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_current_decision", return_value=current),
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(store, "_open_root", return_value=pinned),
                mock.patch.object(store, "_fsync_directory"),
                mock.patch.object(
                    store,
                    "_load_entry",
                    side_effect=SafeCacheStoreError(kind, "probe"),
                ),
            ):
                result = lookup_safe_cache(ROOT / "cache", ROOT / "audit", *self.current)
            self.assertEqual((result.status, result.reason_code), expected)
            pinned.close.assert_called_once_with()

        pinned = SimpleNamespace(descriptor=11, chain=(), close=mock.Mock())
        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_current_decision", return_value=current),
            mock.patch.object(store, "_descriptor_store_supported", return_value=True),
            mock.patch.object(store, "_open_root", return_value=pinned),
            mock.patch.object(store, "_fsync_directory"),
            mock.patch.object(store, "_load_entry", return_value=(record, decision.entry)),
            mock.patch.object(
                store,
                "load_run_audit",
                side_effect=RunAuditValidationError("invalid", "$", "probe"),
            ),
        ):
            invalid_audit = lookup_safe_cache(
                ROOT / "cache", ROOT / "audit", *self.current
            )
        self.assertEqual(
            (invalid_audit.status, invalid_audit.reason_code),
            ("corrupt", "CACHE_AUDIT_REPLAY_INVALID"),
        )

        pinned = SimpleNamespace(descriptor=11, close=mock.Mock())
        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_current_decision", return_value=current),
            mock.patch.object(store, "_descriptor_store_supported", return_value=True),
            mock.patch.object(store, "_open_root", return_value=pinned),
            mock.patch.object(store, "_fsync_directory"),
            mock.patch.object(store, "_load_entry", return_value=(record, decision.entry)),
            mock.patch.object(store, "load_run_audit", return_value=self.audited.bundle),
            mock.patch.object(
                store,
                "decide_safe_cache",
                return_value=SimpleNamespace(
                    status="invalid",
                    reason_code="CACHE_IMPLEMENTATION_MISMATCH",
                    entry=None,
                ),
            ),
        ):
            stale = lookup_safe_cache(ROOT / "cache", ROOT / "audit", *self.current)
        self.assertEqual((stale.status, stale.reason_code), ("stale", "CACHE_ENTRY_STALE"))

        for current_status, expected in (
            ("invalid", ("invalid", "CACHE_REQUEST_INVALID")),
            ("exhausted", ("exhausted", "CACHE_CURRENT_BUDGET_EXHAUSTED")),
        ):
            with (
                self.subTest(persist_current=current_status),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(
                    store,
                    "_current_decision",
                    return_value=SimpleNamespace(
                        status=current_status,
                        lookup_key_sha256=None,
                    ),
                ),
            ):
                result = persist_safe_cache(
                    ROOT / "cache", ROOT / "audit", *self.current, manifest
                )
            self.assertEqual((result.status, result.reason_code), expected)

        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_current_decision", return_value=current),
        ):
            invalid_request = persist_safe_cache(
                ROOT / "cache", ROOT / "audit", *self.current, "not-a-digest"
            )
        self.assertEqual(invalid_request.reason_code, "CACHE_REQUEST_INVALID")

        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_current_decision", return_value=current),
            mock.patch.object(
                store,
                "load_run_audit",
                side_effect=RunAuditValidationError("invalid", "$", "probe"),
            ),
        ):
            invalid_audit = persist_safe_cache(
                ROOT / "cache", ROOT / "audit", *self.current, manifest
            )
        self.assertEqual(invalid_audit.reason_code, "CACHE_AUDIT_REPLAY_INVALID")

        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_current_decision", return_value=current),
            mock.patch.object(store, "load_run_audit", return_value=self.audited.bundle),
            mock.patch.object(store, "decide_safe_cache", return_value=decision),
            mock.patch.object(store, "_descriptor_store_supported", return_value=True),
            mock.patch.object(
                store,
                "_record_bytes",
                side_effect=SafeCacheStoreError("budget", "probe"),
            ),
        ):
            exhausted = persist_safe_cache(
                ROOT / "cache", ROOT / "audit", *self.current, manifest
            )
        self.assertEqual(exhausted.reason_code, "CACHE_STORE_BUDGET_EXHAUSTED")

        for kind, expected in (
            ("conflict", ("conflict", "CACHE_KEY_CONFLICT")),
            ("unsupported", ("unsupported", "CACHE_STORE_UNSUPPORTED")),
            ("budget", ("exhausted", "CACHE_STORE_BUDGET_EXHAUSTED")),
            ("io", ("io_error", "CACHE_STORE_IO_ERROR")),
        ):
            with (
                self.subTest(persist_open=kind),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_current_decision", return_value=current),
                mock.patch.object(store, "load_run_audit", return_value=self.audited.bundle),
                mock.patch.object(store, "decide_safe_cache", return_value=decision),
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(
                    store,
                    "_record_bytes",
                    return_value=(b"record", "b" * 64, "c" * 64),
                ),
                mock.patch.object(store, "safe_cache_entry_bytes", return_value=b"entry"),
                mock.patch.object(
                    store,
                    "_open_root",
                    side_effect=SafeCacheStoreError(kind, "probe"),
                ),
            ):
                result = persist_safe_cache(
                    ROOT / "cache", ROOT / "audit", *self.current, manifest
                )
            self.assertEqual((result.status, result.reason_code), expected)

    def test_public_listing_rejects_structural_and_historical_failures(self) -> None:
        cache_root, audit_root = ROOT / "cache", ROOT / "audit"
        key = "a" * 64

        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(
                store,
                "_open_root",
                side_effect=SafeCacheStoreError("missing", "probe"),
            ),
        ):
            self.assertEqual(list_safe_cache(cache_root, audit_root), ())
        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(
                store,
                "_open_root",
                side_effect=SafeCacheStoreError("io", "probe"),
            ),
        ):
            with self.assertRaises(SafeCacheStoreError):
                list_safe_cache(cache_root, audit_root)

        pinned = SimpleNamespace(descriptor=11, chain=(), close=mock.Mock())
        with (
            mock.patch.object(store, "_validate_roots"),
            mock.patch.object(store, "_open_root", return_value=pinned),
            mock.patch.object(store, "_fsync_directory"),
            mock.patch.object(
                store,
                "_open_child",
                side_effect=SafeCacheStoreError("missing", "probe"),
            ),
        ):
            self.assertEqual(list_safe_cache(cache_root, audit_root), ())

        for listing, expected_kind in (
            (("wrong-bucket",), "corrupt"),
            (("aa",), "io"),
        ):
            pinned = SimpleNamespace(descriptor=11, close=mock.Mock())
            list_effect = (listing, OSError(errno.EIO, "probe"))
            with (
                self.subTest(listing=listing),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_open_root", return_value=pinned),
                mock.patch.object(store, "_fsync_directory"),
                mock.patch.object(store, "_open_child", return_value=12),
                mock.patch.object(store.os, "listdir", side_effect=list_effect),
                mock.patch.object(store.os, "close"),
            ):
                with self.assertRaises(SafeCacheStoreError) as caught:
                    list_safe_cache(cache_root, audit_root)
            self.assertEqual(caught.exception.kind, expected_kind)

        file_info = SimpleNamespace(
            st_mode=stat.S_IFREG | 0o600,
            st_uid=os.geteuid() if hasattr(os, "geteuid") else 0,
            st_nlink=1,
            st_size=1,
        )
        temporary = f".{key}.0000000000000001.tmp"
        for entries, maximum, expected_kind in (
            ((temporary,), store.MAX_KEYS, None),
            ((".bad.tmp",), store.MAX_KEYS, "corrupt"),
            (("wrong-entry",), store.MAX_KEYS, "corrupt"),
            ((key,), 0, "budget"),
        ):
            pinned = SimpleNamespace(descriptor=11, chain=(), close=mock.Mock())
            with (
                self.subTest(entries=entries),
                mock.patch.object(store, "MAX_KEYS", maximum),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_open_root", return_value=pinned),
                mock.patch.object(store, "_fsync_directory"),
                mock.patch.object(store, "_open_child", return_value=12),
                mock.patch.object(store.os, "listdir", side_effect=(("aa",), entries)),
                mock.patch.object(store.os, "stat", return_value=file_info),
                mock.patch.object(store.os, "close"),
            ):
                if expected_kind is None:
                    self.assertEqual(list_safe_cache(cache_root, audit_root), ())
                else:
                    with self.assertRaises(SafeCacheStoreError) as caught:
                        list_safe_cache(cache_root, audit_root)
                    self.assertEqual(caught.exception.kind, expected_kind)

        decision = store.decide_safe_cache(*self.current, self.audited.bundle)
        assert decision.entry is not None
        for load_effect, expected_kind in (
            (RunAuditStoreError("missing", "probe"), "corrupt"),
            (RunAuditValidationError("invalid", "$", "probe"), "corrupt"),
            (
                SimpleNamespace(
                    manifest_sha256="b" * 64,
                    manifest=self.audited.bundle.manifest,
                ),
                "corrupt",
            ),
        ):
            pinned = SimpleNamespace(descriptor=11, close=mock.Mock())
            with (
                self.subTest(history=type(load_effect).__name__),
                mock.patch.object(store, "_validate_roots"),
                mock.patch.object(store, "_open_root", return_value=pinned),
                mock.patch.object(store, "_fsync_directory"),
                mock.patch.object(store, "_open_child", return_value=12),
                mock.patch.object(store.os, "listdir", side_effect=(("aa",), (key,))),
                mock.patch.object(store.os, "close"),
                mock.patch.object(
                    store,
                    "_load_entry",
                    return_value=({"record_sha256": "b" * 64}, decision.entry),
                ),
                mock.patch.object(
                    store,
                    "load_run_audit",
                    side_effect=load_effect
                    if isinstance(load_effect, BaseException)
                    else None,
                    return_value=None
                    if isinstance(load_effect, BaseException)
                    else load_effect,
                ),
            ):
                with self.assertRaises(SafeCacheStoreError) as caught:
                    list_safe_cache(cache_root, audit_root)
            self.assertEqual(caught.exception.kind, expected_kind)

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
            ready = Barrier(2)

            def write(_: int) -> object:
                ready.wait()
                return persist_safe_cache(
                    cache_root, audit_root, *self.current, audited.bundle.manifest_sha256
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = tuple(pool.map(write, range(2)))
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
