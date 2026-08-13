from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_trust_base as trust  # noqa: E402


class TrustBaseTests(unittest.TestCase):
    maxDiff = None

    def _copy_root(self) -> Path:
        temporary = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temporary, True)
        for relative in (
            "docs/contracts/MH-C-KERNEL-CHECKER-001.json",
            "docs/contracts/MH-C-KERNEL-CHECKER-002.json",
            "docs/contracts/MH-C-LEAN-VERIFICATION-001.json",
            "docs/contracts/MH-C-PROOF-TERM-001.json",
            "docs/contracts/MH-C-SAT-REPLAY-001.json",
            "docs/contracts/MH-C-TRUST-BASE-001.json",
            "docs/contracts/PYTHON_CONTRACT_FIRST_WORKFLOW_V1.md",
            "docs/contracts/reports/foundation-conformance-v1.json",
            "docs/contracts/schemas/kernel-checker-result-v1.schema.json",
            "docs/contracts/schemas/kernel-checker-result-v2.schema.json",
            "docs/contracts/schemas/lean-verification-request-v1.schema.json",
            "docs/contracts/schemas/lean-verification-result-v1.schema.json",
            "docs/contracts/schemas/proof-term-v1.schema.json",
            "docs/contracts/schemas/sat-replay-result-v1.schema.json",
            "docs/fixtures/foundation-v1/manifest.json",
            "docs/trust/trust-base-v1.json",
            "docs/trust/trust-base-v1.schema.json",
            "docs/trust/reports/trust-base-v1.json",
            "pyproject.toml",
            "tools/validate_trust_base.py",
        ):
            source = ROOT / relative
            target = temporary / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        shutil.copytree(ROOT / "src", temporary / "src")
        return temporary

    def _inventory(self, root: Path) -> dict:
        return json.loads((root / trust.INVENTORY_PATH).read_text(encoding="utf-8"))

    def _write_inventory(self, root: Path, value: dict, *, identity: bool = True) -> None:
        candidate = copy.deepcopy(value)
        if identity:
            candidate["inventory_sha256"] = trust.ZERO_SHA256
            candidate["inventory_sha256"] = hashlib.sha256(
                trust.canonical_bytes(candidate)
            ).hexdigest()
        (root / trust.INVENTORY_PATH).write_bytes(trust.canonical_bytes(candidate))

    def _error(self, root: Path, *, report: bool = False) -> trust.TrustBaseValidationError:
        check = root / trust.REPORT_PATH if report else None
        with self.assertRaises(trust.TrustBaseValidationError) as raised:
            trust.validate_trust_base(root, check_report=check)
        return raised.exception

    def test_repository_inventory_and_report_are_current(self) -> None:
        report = trust.validate_trust_base(ROOT, check_report=ROOT / trust.REPORT_PATH)
        self.assertEqual(report["source"]["file_count"], 146)
        self.assertEqual(report["source"]["module_count"], 146)
        self.assertEqual(len(report["import_roots"]), 39)
        self.assertEqual(report["surface_summary"]["count"], 24)
        self.assertEqual(
            report["report_sha256"],
            "47cbb869f1c19aa546a64bc42f9883310eedd7dc865eaa5bcebb3cf668fbda4c",
        )

    def test_dependency_minimal_and_full_schema_profiles_match(self) -> None:
        full = trust.validate_trust_base(ROOT)
        with mock.patch.object(trust, "Draft202012Validator", None):
            minimal = trust.validate_trust_base(ROOT)
        self.assertEqual(trust.canonical_bytes(minimal), trust.canonical_bytes(full))

    def test_relocated_copy_reproduces_exact_report(self) -> None:
        root = self._copy_root()
        report = trust.validate_trust_base(root, check_report=root / trust.REPORT_PATH)
        self.assertEqual(trust.canonical_bytes(report), (ROOT / trust.REPORT_PATH).read_bytes())

    def test_subprocess_never_imports_product_or_backend_modules(self) -> None:
        root = self._copy_root()
        wrapper = (
            "import importlib.abc,runpy,sys;"
            "blocked={'mathhead','z3','sympy','pysat','mpmath','mcp'};"
            "F=type('F',(importlib.abc.MetaPathFinder,),"
            "{'find_spec':lambda self,name,path=None,target=None: "
            "(_ for _ in ()).throw(RuntimeError('blocked import '+name)) "
            "if name.split('.')[0] in blocked else None});"
            "sys.meta_path.insert(0,F());"
            f"sys.argv=['validate_trust_base.py','--root',{str(root)!r}];"
            f"runpy.run_path({str(root / 'tools/validate_trust_base.py')!r},run_name='__main__')"
        )
        completed = subprocess.run(
            [sys.executable, "-I", "-c", wrapper],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("trust-base: PASS", completed.stdout)

    def test_duplicate_json_key_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / trust.INVENTORY_PATH
        raw = path.read_bytes().replace(
            b'{"authority_tiers":',
            b'{"schema":"mathhead.trust-base-inventory.v1","authority_tiers":',
            1,
        )
        path.write_bytes(raw)
        self.assertEqual(self._error(root).kind, "schema")

    def test_noncanonical_inventory_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / trust.INVENTORY_PATH
        value = self._inventory(root)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self._error(root).kind, "schema")

    def test_inventory_identity_tamper_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["inventory_sha256"] = "f" * 64
        self._write_inventory(root, value, identity=False)
        self.assertEqual(self._error(root).kind, "identity")

    def test_unknown_inventory_field_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["undeclared"] = True
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "schema")

    def test_contract_byte_drift_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / trust.TRUST_BASE_CONTRACT_PATH
        path.write_bytes(path.read_bytes() + b"\n")
        self.assertEqual(self._error(root).kind, "contract")

    def test_trusted_byte_drift_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / trust.CONFORMANCE_PATH
        path.write_bytes(path.read_bytes() + b" ")
        self.assertEqual(self._error(root).kind, "primitive")

    def test_undeclared_import_root_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / "src/mathhead/cache.py"
        path.write_text(path.read_text(encoding="utf-8") + "\nimport sqlite3\n", encoding="utf-8")
        error = self._error(root)
        self.assertEqual(error.kind, "import")
        self.assertIn("sqlite3", error.detail)

    def test_stale_import_root_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["import_roots"] = [row for row in value["import_roots"] if row["root"] != "z3"]
        z3_surface = next(row for row in value["surfaces"] if row["surface_id"] == "solver.z3")
        z3_surface["import_roots"] = []
        self._write_inventory(root, value)
        error = self._error(root)
        self.assertEqual(error.kind, "import")
        self.assertIn("z3", error.detail)

    def test_unresolved_internal_import_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / "src/mathhead/cache.py"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nimport mathhead.missing_trust_module\n",
            encoding="utf-8",
        )
        error = self._error(root)
        self.assertEqual(error.kind, "import")
        self.assertIn("unresolved internal import", error.detail)

    def test_new_dynamic_import_call_site_fails_closed(self) -> None:
        root = self._copy_root()
        path = root / "src/mathhead/discovery/serialize.py"
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nfrom importlib import import_module\ndef _rogue(name):\n    return import_module(name)\n",
            encoding="utf-8",
        )
        error = self._error(root)
        self.assertEqual(error.kind, "effect")
        self.assertIn("dynamic import", error.detail)

    def test_existing_root_usage_changes_frozen_report(self) -> None:
        root = self._copy_root()
        path = root / "src/mathhead/cache.py"
        path.write_text(path.read_text(encoding="utf-8") + "\nimport json\n", encoding="utf-8")
        error = self._error(root, report=True)
        self.assertEqual(error.kind, "report")

    def test_console_script_target_drift_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        entry = next(row for row in value["entry_points"] if row["entry_id"] == "console.mathhead")
        entry["target"] = "mathhead.cli:_print"
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "entry-point")

    def test_unknown_surface_reference_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["entry_points"][0]["surface_ids"].append("surface.unknown")
        value["entry_points"][0]["surface_ids"].sort()
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "surface")

    def test_non_authority_role_cannot_promote(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        surface = next(row for row in value["surfaces"] if row["surface_id"] == "parser.python-ast")
        surface["current_authority"] = "checker_attestation"
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "authority")

    def test_migration_cycle_or_forward_dependency_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["migration_order"][0]["depends_on"] = ["MH-037"]
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "migration")

    def test_duplicate_migration_ownership_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["migration_order"][1]["closes"].append("checker.discovery-kernel")
        value["migration_order"][1]["closes"].sort()
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "migration")

    def test_kernel_third_party_allowlist_fails_closed(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["kernel_target"]["deny_import_roots"].remove("z3")
        value["kernel_target"]["allow_import_roots"].append("z3")
        value["kernel_target"]["allow_import_roots"].sort()
        self._write_inventory(root, value)
        self.assertEqual(self._error(root).kind, "primitive")

    def test_kernel_effect_budget_must_be_zero(self) -> None:
        root = self._copy_root()
        value = self._inventory(root)
        value["kernel_target"]["source_budget"]["max_dynamic_imports"] = 1
        self._write_inventory(root, value)
        error = self._error(root)
        self.assertIn(error.kind, {"budget", "schema"})

    def test_report_tamper_fails_byte_exact_comparison(self) -> None:
        root = self._copy_root()
        report = root / trust.REPORT_PATH
        report.write_bytes(report.read_bytes() + b"\n")
        self.assertEqual(self._error(root, report=True).kind, "report")

    def test_current_cycles_are_visible_not_hidden(self) -> None:
        report = trust.validate_trust_base(ROOT)
        self.assertEqual(
            report["source"]["cycles"],
            [
                [
                    "mathhead.discovery",
                    "mathhead.discovery.formalize",
                    "mathhead.discovery.product",
                ],
                ["mathhead.profiles", "mathhead.router", "mathhead.server.mcp_server"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
