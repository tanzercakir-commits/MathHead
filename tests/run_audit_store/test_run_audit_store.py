from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import fields
import errno
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tests.run_audit.fixtures import success_bundle  # noqa: E402


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def committed_run_files(root: Path) -> tuple[Path, ...]:
    runs = root / "runs"
    if not runs.exists():
        return ()
    return tuple(
        path
        for path in runs.rglob("*")
        if path.is_file() and len(path.name) == 64 and not path.name.startswith(".")
    )


class RunAuditStoreContractTests(unittest.TestCase):
    def test_contract_and_closed_schema_hashes_are_exact(self) -> None:
        from mathhead import run_audit_store as store

        self.assertEqual(
            store.STORE_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-RUN-AUDIT-STORE-005.json").read_bytes()),
        )
        for name in (
            "run-audit-store-record-v2.schema.json",
            "run-audit-store-result-v5.schema.json",
        ):
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            value = json.loads(raw)
            self.assertFalse(value["additionalProperties"])
            self.assertEqual(
                store.SCHEMA_SHA256S[value["properties"]["schema"]["const"]],
                sha(raw),
            )

    def test_contract_bindings_are_implementation_bound(self) -> None:
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "tools/contract_artifacts.py",
                "verify",
                "--contract",
                "MH-C-RUN-AUDIT-STORE-005",
                "--require-bound",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class RunAuditStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = success_bundle().bundle
        cls.other_bundle = success_bundle(claim="refuted").bundle

    def unsupported_was_closed(self, root: Path) -> bool:
        from mathhead import run_audit_store as store

        if store._descriptor_store_supported():
            return False
        result = store.persist_run_audit(root, self.bundle)
        self.assertEqual(
            (result.status, result.reason_code, result.object_count),
            ("unsupported", "STORE_UNSUPPORTED", 0),
        )
        self.assertFalse(root.exists())
        for accessor, arguments in (
            (store.load_run_audit, (root, self.bundle.manifest_sha256)),
            (store.list_run_audits, (root,)),
        ):
            with self.assertRaises(store.RunAuditStoreError) as caught:
                accessor(*arguments)
            self.assertEqual(caught.exception.kind, "unsupported")
        return True

    def test_store_load_list_and_exact_dedupe(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            first = store.persist_run_audit(root, self.bundle)
            second = store.persist_run_audit(root, self.bundle)
            self.assertEqual((first.status, second.status), ("stored", "existing"))
            self.assertEqual(store.list_run_audits(root), (self.bundle.manifest_sha256,))
            loaded = store.load_run_audit(root, self.bundle.manifest_sha256)
            self.assertEqual(
                (loaded.manifest, loaded.objects),
                (self.bundle.manifest, self.bundle.objects),
            )
            schema = json.loads(
                (ROOT / "docs/contracts/schemas/run-audit-store-result-v5.schema.json").read_bytes()
            )
            from tools.audit_schema_validation import validate_schema_instance

            validate_schema_instance(
                schema,
                json.loads(store.run_audit_store_result_bytes(first)),
                {"run-audit-store-result-v5.schema.json": schema},
            )

    def test_multiple_and_different_run_concurrent_writers_are_independent(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            work = (self.other_bundle, self.bundle, self.other_bundle, self.bundle)
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda bundle: store.persist_run_audit(root, bundle), work))
            self.assertEqual({item.status for item in results}, {"stored", "existing"})
            self.assertEqual(
                store.list_run_audits(root),
                tuple(sorted((self.bundle.manifest_sha256, self.other_bundle.manifest_sha256))),
            )

    def test_relocated_store_preserves_exact_bundle_identity(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            source = base / "source"
            if self.unsupported_was_closed(source):
                return
            target = base / "target"
            store.persist_run_audit(source, self.bundle)
            shutil.copytree(source, target)
            loaded = store.load_run_audit(target, self.bundle.manifest_sha256)
            self.assertEqual(loaded.manifest_sha256, self.bundle.manifest_sha256)
            self.assertEqual(loaded.logical_report, self.bundle.logical_report)

    def test_same_run_concurrent_writers_converge(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(
                    pool.map(lambda _: store.persist_run_audit(root, self.bundle), range(4))
                )
            self.assertEqual({item.status for item in results}, {"stored", "existing"})
            self.assertEqual(store.list_run_audits(root), (self.bundle.manifest_sha256,))

    def test_interruption_before_run_record_never_commits(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            original = store._write_immutable

            def fail_record(
                pinned: object,
                parent: int,
                target: str,
                data: bytes,
                *,
                name_digest: str | None = None,
            ) -> bool:
                if name_digest is not None:
                    raise store.RunAuditStoreError("io", "injected interruption")
                return original(
                    pinned,
                    parent,
                    target,
                    data,
                    name_digest=name_digest,
                )

            with mock.patch.object(store, "_write_immutable", side_effect=fail_record):
                with self.assertRaises(store.RunAuditStoreError):
                    store.persist_run_audit(root, self.bundle)
            self.assertEqual(committed_run_files(root), ())
            self.assertEqual(store.list_run_audits(root), ())
            self.assertEqual(store.persist_run_audit(root, self.bundle).status, "stored")

    def test_write_install_and_sync_interruption_matrix_has_no_visible_run(self) -> None:
        from mathhead import run_audit_store as store

        stages = {
            "write": (store, "_write_all", store.RunAuditStoreError("io", "write")),
            "immutable-install": (store.os, "link", OSError(errno.ENOSPC, "capacity")),
            "file-sync": (store.os, "fsync", OSError(errno.EIO, "file sync")),
        }
        for label, (owner, attribute, failure) in stages.items():
            with self.subTest(stage=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / "audit"
                if self.unsupported_was_closed(root):
                    return
                if label == "file-sync":
                    real_fsync = os.fsync

                    def fail_regular(descriptor: int) -> None:
                        if stat.S_ISREG(os.fstat(descriptor).st_mode):
                            raise failure
                        real_fsync(descriptor)

                    effect: object = fail_regular
                else:
                    effect = failure
                with (
                    mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                    mock.patch.object(owner, attribute, side_effect=effect),
                ):
                    with self.assertRaises(store.RunAuditStoreError):
                        store.persist_run_audit(root, self.bundle)
                self.assertEqual(committed_run_files(root), ())
                self.assertFalse(tuple(root.rglob("*.tmp")))

    def test_unsupported_directory_sync_returns_before_content_installation(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            with mock.patch.object(
                store.os,
                "fsync",
                side_effect=OSError(errno.EINVAL, "unsupported"),
            ):
                result = store.persist_run_audit(root, self.bundle)
            self.assertEqual(
                (result.status, result.reason_code), ("unsupported", "STORE_UNSUPPORTED")
            )
            self.assertEqual(committed_run_files(root), ())
            self.assertFalse(any(path.is_file() for path in root.rglob("*")))

    def test_late_unsupported_directory_sync_is_probed_before_content_installation(
        self,
    ) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            real_fsync = os.fsync
            directory_calls = 0

            def reject_eighth_directory(descriptor: int) -> None:
                nonlocal directory_calls
                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    directory_calls += 1
                    if directory_calls == 8:
                        raise OSError(errno.EINVAL, "unsupported")
                real_fsync(descriptor)

            with mock.patch.object(store.os, "fsync", side_effect=reject_eighth_directory):
                result = store.persist_run_audit(root, self.bundle)
            self.assertEqual(result.status, "unsupported")
            self.assertEqual(committed_run_files(root), ())
            self.assertFalse(any(path.is_file() for path in root.rglob("*")))

    def test_run_record_temporary_cleanup_failure_rolls_back_visibility(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            real_unlink = os.unlink
            manifest = self.bundle.manifest_sha256
            matching_temporaries = 0

            def reject_record_temporary(path: str, *, dir_fd: int | None = None) -> None:
                nonlocal matching_temporaries
                if path.startswith(f".{manifest}.") and path.endswith(".tmp"):
                    matching_temporaries += 1
                    if matching_temporaries == 2:
                        raise OSError(errno.EACCES, "permission")
                real_unlink(path, dir_fd=dir_fd)

            with (
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(store.os, "unlink", side_effect=reject_record_temporary),
                self.assertRaises(store.RunAuditStoreError),
            ):
                store.persist_run_audit(root, self.bundle)
            self.assertEqual(committed_run_files(root), ())
            self.assertEqual(store.list_run_audits(root), ())

    def test_cascading_cleanup_failure_leaves_no_accepted_run(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            real_unlink = os.unlink
            manifest = self.bundle.manifest_sha256
            matching_temporaries = 0

            def reject_record_cleanup(path: str, *, dir_fd: int | None = None) -> None:
                nonlocal matching_temporaries
                if path.startswith(f".{manifest}.") and path.endswith(".tmp"):
                    matching_temporaries += 1
                    if matching_temporaries < 2:
                        real_unlink(path, dir_fd=dir_fd)
                        return
                    raise OSError(errno.EACCES, "permission")
                if path == manifest and matching_temporaries >= 2:
                    raise OSError(errno.EACCES, "permission")
                real_unlink(path, dir_fd=dir_fd)

            with (
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(store.os, "unlink", side_effect=reject_record_cleanup),
                self.assertRaises(store.RunAuditStoreError),
            ):
                store.persist_run_audit(root, self.bundle)
            with self.assertRaises(store.RunAuditStoreError) as listed:
                store.list_run_audits(root)
            self.assertEqual(listed.exception.kind, "link")
            with self.assertRaises(store.RunAuditStoreError) as loaded:
                store.load_run_audit(root, manifest)
            self.assertEqual(loaded.exception.kind, "link")
            pending = next((root / "runs" / manifest[:2]).glob(".*.tmp"))
            os.unlink(pending)
            with self.assertRaises(store.RunAuditStoreError) as listed:
                store.list_run_audits(root)
            self.assertEqual(listed.exception.kind, "mode")
            with self.assertRaises(store.RunAuditStoreError) as loaded:
                store.load_run_audit(root, manifest)
            self.assertEqual(loaded.exception.kind, "mode")

    def test_final_record_sync_and_rollback_failure_quarantines_visibility(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            real_link = os.link
            real_unlink = os.unlink
            real_fsync = os.fsync
            manifest = self.bundle.manifest_sha256
            identity_links = 0
            record_linked = False
            sync_failed = False

            def note_link(source: str, target: str, **kwargs: object) -> None:
                nonlocal identity_links, record_linked
                real_link(source, target, **kwargs)
                if target == manifest:
                    identity_links += 1
                    record_linked = identity_links == 2

            def reject_final_run_sync(descriptor: int) -> None:
                nonlocal sync_failed
                run_bucket = root / "runs" / manifest[:2]
                descriptor_info = os.fstat(descriptor)
                bucket_info = run_bucket.stat() if run_bucket.exists() else None
                if (
                    record_linked
                    and not sync_failed
                    and bucket_info is not None
                    and (descriptor_info.st_dev, descriptor_info.st_ino)
                    == (bucket_info.st_dev, bucket_info.st_ino)
                ):
                    sync_failed = True
                    raise OSError(errno.EIO, "final run sync")
                real_fsync(descriptor)

            def reject_record_rollback(path: str, *, dir_fd: int | None = None) -> None:
                if sync_failed and path == manifest:
                    raise OSError(errno.EACCES, "record rollback")
                real_unlink(path, dir_fd=dir_fd)

            with (
                mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                mock.patch.object(store.os, "link", side_effect=note_link),
                mock.patch.object(store.os, "fsync", side_effect=reject_final_run_sync),
                mock.patch.object(store.os, "unlink", side_effect=reject_record_rollback),
                self.assertRaises(store.RunAuditStoreError) as persisted,
            ):
                store.persist_run_audit(root, self.bundle)
            self.assertEqual(persisted.exception.kind, "io")
            target = root / "runs" / manifest[:2] / manifest
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o000)
            for accessor, arguments in (
                (store.list_run_audits, (root,)),
                (store.load_run_audit, (root, manifest)),
            ):
                with self.assertRaises(store.RunAuditStoreError) as rejected:
                    accessor(*arguments)
                self.assertEqual(rejected.exception.kind, "mode")

    def test_orphan_content_is_not_a_visible_run(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            store.persist_run_audit(root, self.bundle)
            orphan = b'{"schema":"mathhead.orphan.v1"}\n'
            digest = sha(orphan)
            bucket = root / "objects" / digest[:2]
            bucket.mkdir(mode=0o700, exist_ok=True)
            path = bucket / digest
            path.write_bytes(orphan)
            path.chmod(0o600)
            self.assertEqual(store.list_run_audits(root), (self.bundle.manifest_sha256,))

    def test_corrupt_object_record_and_load_time_replay_fail_closed(self) -> None:
        from mathhead import run_audit_store as store

        for corrupt_record in (False, True):
            with self.subTest(record=corrupt_record), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / "audit"
                if self.unsupported_was_closed(root):
                    return
                store.persist_run_audit(root, self.bundle)
                if corrupt_record:
                    target = (
                        root
                        / "runs"
                        / self.bundle.manifest_sha256[:2]
                        / self.bundle.manifest_sha256
                    )
                else:
                    object_digest = sha(self.bundle.objects[0])
                    target = root / "objects" / object_digest[:2] / object_digest
                target.write_bytes(target.read_bytes() + b"x")
                target.chmod(0o600)
                with self.assertRaises(store.RunAuditStoreError):
                    store.load_run_audit(root, self.bundle.manifest_sha256)
                with self.assertRaises(store.RunAuditStoreError):
                    store.list_run_audits(root)

    def test_symlinked_root_and_content_are_rejected(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            real = base / "real"
            if self.unsupported_was_closed(real):
                return
            link = base / "link"
            store.persist_run_audit(real, self.bundle)
            os.symlink(real, link, target_is_directory=True)
            with self.assertRaises(store.RunAuditStoreError):
                store.persist_run_audit(link, self.bundle)
            digest = sha(self.bundle.objects[0])
            target = real / "objects" / digest[:2] / digest
            saved = target.read_bytes()
            target.unlink()
            decoy = base / "decoy"
            decoy.write_bytes(saved)
            os.symlink(decoy, target)
            with self.assertRaises(store.RunAuditStoreError):
                store.load_run_audit(real, self.bundle.manifest_sha256)

    def test_hardlinked_run_record_and_content_are_rejected(self) -> None:
        from mathhead import run_audit_store as store

        for content in (False, True):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / "audit"
                if self.unsupported_was_closed(root):
                    return
                store.persist_run_audit(root, self.bundle)
                if content:
                    digest = sha(self.bundle.objects[0])
                    target = root / "objects" / digest[:2] / digest
                else:
                    target = (
                        root
                        / "runs"
                        / self.bundle.manifest_sha256[:2]
                        / self.bundle.manifest_sha256
                    )
                os.link(target, Path(temporary).resolve() / "second-link")
                with self.assertRaises(store.RunAuditStoreError):
                    store.load_run_audit(root, self.bundle.manifest_sha256)

    def test_ancestor_replacement_cannot_redirect_writes(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            root = base / "anchor" / "audit"
            if self.unsupported_was_closed(root):
                return
            replacement = base / "replacement"
            replacement.mkdir(mode=0o700)
            original = base / "original"
            real_sync = store._fsync_directory
            changed = False

            def replace_after_probe(
                pinned: object, descriptor: int, *, capability_probe: bool = False
            ) -> None:
                nonlocal changed
                real_sync(pinned, descriptor, capability_probe=capability_probe)
                if not changed:
                    changed = True
                    os.rename(base / "anchor", original)
                    os.symlink(replacement, base / "anchor", target_is_directory=True)

            with mock.patch.object(store, "_fsync_directory", side_effect=replace_after_probe):
                with self.assertRaises(store.RunAuditStoreError) as caught:
                    store.persist_run_audit(root, self.bundle)
            self.assertEqual(caught.exception.kind, "link")
            self.assertEqual(tuple(replacement.iterdir()), ())
            self.assertEqual(committed_run_files(replacement), ())

    def test_post_probe_sync_capability_errno_is_closed_io(self) -> None:
        from mathhead import run_audit_store as store

        if not store._descriptor_store_supported():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            pinned = store._open_root(root, create=True)
            try:
                with (
                    mock.patch.object(
                        store.os,
                        "fsync",
                        side_effect=OSError(errno.EINVAL, "late operation"),
                    ),
                    self.assertRaises(store.RunAuditStoreError) as caught,
                ):
                    store._fsync_directory(pinned, pinned.descriptor, capability_probe=False)
                self.assertEqual(caught.exception.kind, "io")
            finally:
                pinned.close()

    def test_root_relative_and_traversal_shaped_paths_are_rejected(self) -> None:
        from mathhead import run_audit_store as store

        candidates = (Path(os.path.sep), Path("relative"))
        for candidate in candidates:
            with self.subTest(path=candidate), self.assertRaises(store.RunAuditStoreError):
                store.persist_run_audit(candidate, self.bundle)
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            traversal = base / "parent" / ".." / "audit"
            with self.assertRaises(store.RunAuditStoreError):
                store.persist_run_audit(traversal, self.bundle)
            result = store.persist_run_audit(base / "typed", object())  # type: ignore[arg-type]
            self.assertEqual(result.status, "invalid")
            self.assertFalse(result.mathematical_authority)

    def test_platform_capability_absence_is_explicit_and_effect_free(self) -> None:
        from mathhead import run_audit_store as store

        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch.object(store, "_descriptor_store_supported", return_value=False),
        ):
            root = Path(temporary).resolve() / "audit"
            result = store.persist_run_audit(root, self.bundle)
            self.assertEqual(
                (result.status, result.reason_code, result.object_count),
                ("unsupported", "STORE_UNSUPPORTED", 0),
            )
            self.assertFalse(root.exists())
            for accessor, arguments in (
                (store.load_run_audit, (root, self.bundle.manifest_sha256)),
                (store.list_run_audits, (root,)),
            ):
                with self.assertRaises(store.RunAuditStoreError) as caught:
                    accessor(*arguments)
                self.assertEqual(caught.exception.kind, "unsupported")

    def test_store_results_are_closed_immutable_and_not_pickle_authority(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            result = store.persist_run_audit(Path(temporary).resolve() / "audit", self.bundle)
            with self.assertRaises(PermissionError):
                store.RunAuditStoreResult()
            with self.assertRaises(TypeError):

                class ForgedResult(store.RunAuditStoreResult):
                    pass

            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(result)
            with self.assertRaises((AttributeError, TypeError)):
                result.status = "loaded"  # type: ignore[misc]

    def test_store_codec_and_record_controls_fail_closed(self) -> None:
        from mathhead import run_audit_store as store

        record_raw, _identity = store._record_bytes(self.bundle)
        record = json.loads(record_raw)

        def encoded(value: dict[str, object], *, repair: bool = True) -> bytes:
            if repair:
                value["record_sha256"] = store._self_hash(value, "record_sha256")
            return store._canonical(value)

        with self.assertRaises(store.RunAuditStoreError):
            store._canonical(object())
        for raw in (
            b"",
            b'{"schema":"one","schema":"two"}\n',
            b"\xff",
            b"[]\n",
            record_raw + b" ",
        ):
            with self.subTest(raw=raw[:16]), self.assertRaises(store.RunAuditStoreError):
                store._parse(raw)
        for value, label in ((None, "digest"), (True, "quantity"), (-1, "quantity")):
            with self.subTest(label=label), self.assertRaises(store.RunAuditStoreError):
                if label == "digest":
                    store._digest(value, label)
                else:
                    store._quantity(value, label, 1)

        cases: list[tuple[dict[str, object], bool, str]] = []
        changed = copy.deepcopy(record)
        changed["unknown"] = False
        cases.append((changed, True, self.bundle.manifest_sha256))
        changed = copy.deepcopy(record)
        changed["schema"] = "mathhead.changed.v1"
        cases.append((changed, True, self.bundle.manifest_sha256))
        changed = copy.deepcopy(record)
        changed["manifest_sha256"] = "0" * 64
        cases.append((changed, True, self.bundle.manifest_sha256))
        changed = copy.deepcopy(record)
        changed["object_sha256s"] = []
        cases.append((changed, True, self.bundle.manifest_sha256))
        changed = copy.deepcopy(record)
        changed["object_sha256s"] = list(reversed(changed["object_sha256s"]))
        cases.append((changed, True, self.bundle.manifest_sha256))
        changed = copy.deepcopy(record)
        changed["record_sha256"] = "0" * 64
        cases.append((changed, False, self.bundle.manifest_sha256))
        for value, repair, expected in cases:
            with self.assertRaises(store.RunAuditStoreError):
                store._parse_record(encoded(value, repair=repair), expected)

        with self.assertRaises(store.RunAuditStoreError):
            store._new_result(
                "changed",
                "CHANGED",
                manifest_sha256=None,
                record_sha256=None,
                object_count=0,
            )
        with self.assertRaises(store.RunAuditStoreError):
            store.validate_run_audit_store_result(object())  # type: ignore[arg-type]
        retained = store._new_result(
            "invalid",
            "BUNDLE_INVALID",
            manifest_sha256="0" * 64,
            record_sha256="1" * 64,
            object_count=1,
        )
        with self.assertRaises(store.RunAuditStoreError):
            store.validate_run_audit_store_result(retained)

    def test_descriptor_helpers_reject_types_modes_links_and_conflicts(self) -> None:
        from mathhead import run_audit_store as store

        if not store._descriptor_store_supported():
            with tempfile.TemporaryDirectory() as temporary:
                self.unsupported_was_closed(Path(temporary).resolve() / "audit")
            return
        with self.assertRaises(store.RunAuditStoreError):
            store._open_root("not-a-path", create=False)  # type: ignore[arg-type]
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            private = base / "private"
            private.mkdir(mode=0o700)
            pinned = store._open_root(private, create=False)
            try:
                with self.assertRaises(store.RunAuditStoreError):
                    store._open_child_directory(pinned, pinned.descriptor, "absent", create=False)
                empty = private / "empty"
                empty.write_bytes(b"")
                empty.chmod(0o600)
                with self.assertRaises(store.RunAuditStoreError):
                    store._read_bounded(pinned, pinned.descriptor, "empty", 10)
                with self.assertRaises(store.RunAuditStoreError):
                    store._write_immutable_locked(
                        pinned, pinned.descriptor, sha(b"expected"), b"different"
                    )
                existing_name = sha(b"actual")
                existing = private / existing_name
                existing.write_bytes(b"other")
                existing.chmod(0o600)
                with self.assertRaises(store.RunAuditStoreError):
                    store._read_existing_exact(pinned, pinned.descriptor, existing_name, b"actual")
            finally:
                pinned.close()

            regular = base / "regular"
            regular.write_bytes(b"data")
            regular.chmod(0o600)
            with self.assertRaises(store.RunAuditStoreError):
                store._directory_info(os.lstat(regular), private=True)
            public_directory = base / "public-directory"
            public_directory.mkdir(mode=0o755)
            public_directory.chmod(0o755)
            with self.assertRaises(store.RunAuditStoreError):
                store._directory_info(os.lstat(public_directory), private=True)
            public_file = base / "public-file"
            public_file.write_bytes(b"data")
            public_file.chmod(0o644)
            with self.assertRaises(store.RunAuditStoreError):
                store._file_info(os.lstat(public_file))

    def test_listing_rejects_bad_names_and_ignores_only_private_temporaries(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "listing"
            if self.unsupported_was_closed(root):
                return
            runs = root / "runs"
            runs.mkdir(parents=True, mode=0o700)
            root.chmod(0o700)
            runs.chmod(0o700)
            bad_bucket = runs / "zz"
            bad_bucket.mkdir(mode=0o700)
            with self.assertRaises(store.RunAuditStoreError):
                store.list_run_audits(root)
            bad_bucket.rmdir()
            bucket = runs / "00"
            bucket.mkdir(mode=0o700)
            pending = bucket / f".{('0' * 64)}.{('0' * 16)}.tmp"
            pending.write_bytes(b"temporary")
            pending.chmod(0o600)
            self.assertEqual(store.list_run_audits(root), ())
            pending.unlink()

            linked = bucket / ".attacker.tmp"
            os.symlink(bucket / self.bundle.manifest_sha256, linked)
            with self.assertRaises(store.RunAuditStoreError) as caught:
                store.list_run_audits(root)
            self.assertEqual(caught.exception.kind, "link")
            linked.unlink()

            for label, sequence in (
                ("hardlink", "1" * 16),
                ("directory", "2" * 16),
                ("public", "3" * 16),
            ):
                with self.subTest(temporary=label):
                    candidate = bucket / f".{('0' * 64)}.{sequence}.tmp"
                    external = Path(temporary).resolve() / f"external-{label}"
                    if label == "hardlink":
                        external.write_bytes(b"temporary")
                        external.chmod(0o600)
                        os.link(external, candidate)
                    elif label == "directory":
                        candidate.mkdir(mode=0o700)
                    else:
                        candidate.write_bytes(b"temporary")
                        candidate.chmod(0o644)
                    with self.assertRaises(store.RunAuditStoreError):
                        store.list_run_audits(root)
                    if candidate.is_dir():
                        candidate.rmdir()
                    else:
                        candidate.unlink()
                    if external.exists():
                        external.unlink()
            bad_name = bucket / "changed"
            bad_name.write_bytes(b"changed")
            bad_name.chmod(0o600)
            with self.assertRaises(store.RunAuditStoreError):
                store.list_run_audits(root)

    def test_object_count_boundary_is_exact(self) -> None:
        from mathhead import run_audit_store as store

        count = len(
            {
                sha(raw)
                for raw in (
                    *self.bundle.objects,
                    self.bundle.manifest,
                )
            }
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            if self.unsupported_was_closed(base / "probe"):
                return
            with mock.patch.object(store, "MAX_OBJECTS", count):
                exact = store.persist_run_audit(base / "exact", self.bundle)
            self.assertEqual(exact.status, "stored")
            with mock.patch.object(store, "MAX_OBJECTS", count - 1):
                exceeded = store.persist_run_audit(base / "exceeded", self.bundle)
            self.assertEqual(
                (exceeded.status, exceeded.reason_code, exceeded.object_count),
                ("invalid", "STORE_BUDGET_EXCEEDED", 0),
            )

    def test_record_byte_budget_and_empty_store_are_closed(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            root = base / "audit"
            if self.unsupported_was_closed(root):
                return
            root.mkdir(mode=0o700)
            root.chmod(0o700)
            self.assertEqual(store.list_run_audits(root), ())
            runs = root / "runs"
            runs.mkdir(mode=0o700)
            runs.chmod(0o700)
            with (
                mock.patch.object(store.os, "listdir", side_effect=OSError(errno.EIO, "list")),
                self.assertRaises(store.RunAuditStoreError) as unreadable,
            ):
                store.list_run_audits(root)
            self.assertEqual(unreadable.exception.kind, "io")
            with self.assertRaises(store.RunAuditStoreError) as missing:
                store.load_run_audit(base / "missing", self.bundle.manifest_sha256)
            self.assertEqual(missing.exception.kind, "missing")
            with mock.patch.object(store, "MAX_RECORD_BYTES", 500):
                exceeded = store.persist_run_audit(root, self.bundle)
            self.assertEqual(
                (exceeded.status, exceeded.reason_code, exceeded.object_count),
                ("invalid", "STORE_BUDGET_EXCEEDED", 0),
            )

    def test_derived_store_components_reject_unsafe_names(self) -> None:
        from mathhead import run_audit_store as store

        with self.assertRaises(store.RunAuditStoreError) as wrong_root:
            store.persist_run_audit("audit", self.bundle)  # type: ignore[arg-type]
        self.assertEqual(wrong_root.exception.kind, "type")
        self.assertEqual(store._quantity(1, "quantity", 1), 1)
        with (
            mock.patch.object(store, "MAX_OBJECTS", 0),
            self.assertRaises(store.RunAuditStoreError) as inventory,
        ):
            store._record_bytes(self.bundle)
        self.assertEqual(inventory.exception.kind, "budget")
        if not store._descriptor_store_supported():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            root.mkdir(mode=0o700)
            pinned = store._open_root(root, create=False)
            try:
                for name in ("", ".", "..", "a/b", "a\\b"):
                    with self.subTest(name=name), self.assertRaises(
                        store.RunAuditStoreError
                    ) as caught:
                        store._open_child_directory(
                            pinned,
                            pinned.descriptor,
                            name,
                            create=False,
                        )
                    self.assertEqual(caught.exception.kind, "path")
            finally:
                pinned.close()

    def test_permission_capacity_stat_read_and_write_failures_are_closed(self) -> None:
        from mathhead import run_audit_store as store

        failures = {
            "capacity-write": (store.os, "write", OSError(errno.ENOSPC, "full")),
            "permission-link": (store.os, "link", OSError(errno.EACCES, "denied")),
            "stat": (store.os, "stat", OSError(errno.EIO, "stat")),
        }
        for label, (owner, attribute, failure) in failures.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve() / "audit"
                if self.unsupported_was_closed(root):
                    return
                with (
                    mock.patch.object(store, "_descriptor_store_supported", return_value=True),
                    mock.patch.object(owner, attribute, side_effect=failure),
                ):
                    with self.assertRaises(store.RunAuditStoreError):
                        store.persist_run_audit(root, self.bundle)
                self.assertEqual(committed_run_files(root), ())

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / "audit"
            if self.unsupported_was_closed(root):
                return
            store.persist_run_audit(root, self.bundle)
            with mock.patch.object(store.os, "read", side_effect=OSError(errno.EIO, "read")):
                with self.assertRaises(store.RunAuditStoreError):
                    store.load_run_audit(root, self.bundle.manifest_sha256)

    def test_control_flow_exceptions_propagate_and_temporary_is_removed(self) -> None:
        from mathhead import run_audit_store as store

        for failure in (MemoryError(), KeyboardInterrupt(), SystemExit()):
            with (
                self.subTest(failure=type(failure).__name__),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary).resolve() / "audit"
                if self.unsupported_was_closed(root):
                    return
                with mock.patch.object(store, "_write_all", side_effect=failure):
                    with self.assertRaises(type(failure)):
                        store.persist_run_audit(root, self.bundle)
                self.assertEqual(committed_run_files(root), ())
                self.assertFalse(tuple(root.rglob("*.tmp")))

    def test_defensive_result_and_io_classification_is_explicit(self) -> None:
        from mathhead import run_audit_store as store

        with (
            mock.patch.object(store, "MAX_RECORD_BYTES", 8),
            self.assertRaises(store.RunAuditStoreError),
        ):
            store._canonical({"long": "value"})
        with self.assertRaises(store.RunAuditStoreError):
            store._quantity(2, "quantity", 1)
        for effect in (OSError("write"), 0):
            with (
                self.subTest(effect=effect),
                mock.patch.object(
                    store.os,
                    "write",
                    side_effect=effect if isinstance(effect, BaseException) else None,
                    return_value=None if isinstance(effect, BaseException) else effect,
                ),
                self.assertRaises(store.RunAuditStoreError),
            ):
                store._write_all(1, b"x")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            forged = object.__new__(type(self.bundle))
            for field in fields(self.bundle):
                object.__setattr__(forged, field.name, getattr(self.bundle, field.name))
            object.__setattr__(forged, "manifest", b"invalid\n")
            self.assertEqual(store.persist_run_audit(base / "forged", forged).status, "invalid")
            with mock.patch.object(store, "MAX_OBJECTS", 0):
                self.assertEqual(
                    store.persist_run_audit(base / "budget", self.bundle).reason_code,
                    "STORE_BUDGET_EXCEEDED",
                )
            if not store._descriptor_store_supported():
                return
            with mock.patch.object(store, "_write_immutable", side_effect=OSError("io")):
                result = store.persist_run_audit(base / "io", self.bundle)
            self.assertEqual(result.status, "io_error")


if __name__ == "__main__":
    unittest.main()
