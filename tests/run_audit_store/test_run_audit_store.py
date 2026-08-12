from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import pickle
import shutil
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


class RunAuditStoreContractTests(unittest.TestCase):
    def test_contract_and_closed_schema_hashes_are_exact(self) -> None:
        from mathhead import run_audit_store as store

        self.assertEqual(
            store.STORE_CONTRACT_SHA256,
            sha((ROOT / "docs/contracts/MH-C-RUN-AUDIT-STORE-001.json").read_bytes()),
        )
        for name in ("run-audit-store-record-v1.schema.json", "run-audit-store-result-v1.schema.json"):
            raw = (ROOT / "docs/contracts/schemas" / name).read_bytes()
            value = json.loads(raw)
            self.assertFalse(value["additionalProperties"])
            self.assertEqual(store.SCHEMA_SHA256S[value["properties"]["schema"]["const"]], sha(raw))


class RunAuditStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = success_bundle().bundle
        cls.other_bundle = success_bundle(claim="refuted").bundle

    def test_store_load_list_and_exact_dedupe(self) -> None:
        from mathhead.run_audit_store import list_run_audits, load_run_audit, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            first = persist_run_audit(root, self.bundle)
            second = persist_run_audit(root, self.bundle)
            self.assertEqual((first.status, second.status), ("stored", "existing"))
            self.assertEqual(list_run_audits(root), (self.bundle.manifest_sha256,))
            loaded = load_run_audit(root, self.bundle.manifest_sha256)
            self.assertEqual((loaded.manifest, loaded.objects), (self.bundle.manifest, self.bundle.objects))

    def test_multiple_runs_list_by_digest_not_write_order(self) -> None:
        from mathhead.run_audit_store import list_run_audits, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            persist_run_audit(root, self.other_bundle)
            persist_run_audit(root, self.bundle)
            self.assertEqual(
                list_run_audits(root),
                tuple(sorted((self.bundle.manifest_sha256, self.other_bundle.manifest_sha256))),
            )

    def test_relocated_store_preserves_exact_bundle_identity(self) -> None:
        from mathhead.run_audit_store import load_run_audit, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source = base / "source"
            target = base / "target"
            persist_run_audit(source, self.bundle)
            shutil.copytree(source, target)
            loaded = load_run_audit(target, self.bundle.manifest_sha256)
            self.assertEqual(loaded.manifest_sha256, self.bundle.manifest_sha256)
            self.assertEqual(loaded.logical_report, self.bundle.logical_report)

    def test_same_run_concurrent_writers_converge(self) -> None:
        from mathhead.run_audit_store import list_run_audits, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: persist_run_audit(root, self.bundle), range(4)))
            self.assertEqual({item.status for item in results}, {"stored", "existing"})
            self.assertEqual(list_run_audits(root), (self.bundle.manifest_sha256,))

    def test_interruption_before_run_record_never_commits(self) -> None:
        from mathhead import run_audit_store as store

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            original = store._write_immutable

            def fail_record(path: Path, data: bytes, *, name_digest: str | None = None) -> bool:
                if "runs" in path.parts:
                    raise store.RunAuditStoreError("io", "injected interruption")
                return original(path, data, name_digest=name_digest)

            with mock.patch.object(store, "_write_immutable", side_effect=fail_record):
                with self.assertRaises(store.RunAuditStoreError):
                    store.persist_run_audit(root, self.bundle)
            self.assertEqual(store.list_run_audits(root), ())
            self.assertEqual(store.persist_run_audit(root, self.bundle).status, "stored")

    def test_orphan_content_is_not_a_visible_run(self) -> None:
        from mathhead.run_audit_store import list_run_audits, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            persist_run_audit(root, self.bundle)
            orphan = b'{"schema":"mathhead.orphan.v1"}\n'
            digest = sha(orphan)
            bucket = root / "objects" / digest[:2]
            bucket.mkdir(mode=0o700, exist_ok=True)
            path = bucket / digest
            path.write_bytes(orphan)
            path.chmod(0o600)
            self.assertEqual(list_run_audits(root), (self.bundle.manifest_sha256,))

    def test_corrupt_object_and_record_fail_closed(self) -> None:
        from mathhead.run_audit_store import RunAuditStoreError, load_run_audit, persist_run_audit

        for corrupt_record in (False, True):
            with self.subTest(record=corrupt_record), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "audit"
                persist_run_audit(root, self.bundle)
                if corrupt_record:
                    target = root / "runs" / self.bundle.manifest_sha256[:2] / self.bundle.manifest_sha256
                else:
                    object_digest = sha(self.bundle.objects[0])
                    target = root / "objects" / object_digest[:2] / object_digest
                target.write_bytes(target.read_bytes() + b"x")
                target.chmod(0o600)
                with self.assertRaises(RunAuditStoreError):
                    load_run_audit(root, self.bundle.manifest_sha256)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlinked_root_and_content_are_rejected(self) -> None:
        from mathhead.run_audit_store import RunAuditStoreError, load_run_audit, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            real = base / "real"
            link = base / "link"
            persist_run_audit(real, self.bundle)
            os.symlink(real, link, target_is_directory=True)
            with self.assertRaises(RunAuditStoreError):
                persist_run_audit(link, self.bundle)
            digest = sha(self.bundle.objects[0])
            target = real / "objects" / digest[:2] / digest
            saved = target.read_bytes()
            target.unlink()
            decoy = base / "decoy"
            decoy.write_bytes(saved)
            os.symlink(decoy, target)
            with self.assertRaises(RunAuditStoreError):
                load_run_audit(real, self.bundle.manifest_sha256)

    @unittest.skipUnless(hasattr(os, "link"), "hardlinks unavailable")
    def test_hardlinked_run_record_is_rejected(self) -> None:
        from mathhead.run_audit_store import RunAuditStoreError, load_run_audit, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "audit"
            persist_run_audit(root, self.bundle)
            record = root / "runs" / self.bundle.manifest_sha256[:2] / self.bundle.manifest_sha256
            os.link(record, Path(temporary) / "second-link")
            with self.assertRaises(RunAuditStoreError):
                load_run_audit(root, self.bundle.manifest_sha256)

    def test_relative_root_and_wrong_bundle_type_fail(self) -> None:
        from mathhead.run_audit_store import RunAuditStoreError, persist_run_audit

        with self.assertRaises(RunAuditStoreError):
            persist_run_audit(Path("relative"), self.bundle)
        with tempfile.TemporaryDirectory() as temporary:
            result = persist_run_audit(Path(temporary) / "audit", object())  # type: ignore[arg-type]
            self.assertEqual(result.status, "invalid")
            self.assertFalse(result.mathematical_authority)

    def test_store_results_are_closed_immutable_and_not_pickle_authority(self) -> None:
        from mathhead.run_audit_store import RunAuditStoreResult, persist_run_audit

        with tempfile.TemporaryDirectory() as temporary:
            result = persist_run_audit(Path(temporary) / "audit", self.bundle)
            with self.assertRaises(PermissionError):
                RunAuditStoreResult()
            with self.assertRaises(TypeError):
                class ForgedResult(RunAuditStoreResult):
                    pass
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(result)
            with self.assertRaises((AttributeError, TypeError)):
                result.status = "loaded"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
