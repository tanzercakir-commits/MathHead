from __future__ import annotations

import ast
import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools import validate_trust_transitions as validator  # noqa: E402
from mathhead.kernel.trust_transitions import (  # noqa: E402
    MAX_ATTEMPT_BYTES,
    TransitionAuditResult,
    TrustTransitionValidationError,
    audit_trust_transition,
    parse_transition_audit_result,
    transition_audit_result_to_bytes,
    validate_trust_transition_catalogue,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


class TrustTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogue, cls.controls = validator.build_catalogue()
        cls.catalogue_value = json.loads(cls.catalogue)

    def test_repository_catalogue_report_and_contract_are_current(self) -> None:
        totals = validator.validate_repository()
        self.assertEqual(totals["transitions"], 11)
        self.assertEqual(totals["positive_controls"], 11)
        self.assertEqual(totals["mutants"], 45)
        self.assertEqual(totals["mutants_killed"], 45)
        self.assertEqual(totals["mutants_survived"], 0)
        self.assertEqual(totals["surfaces"], 11)
        self.assertEqual(totals["issuer_sites"], 5)

    def test_every_permitted_edge_passes_and_results_round_trip(self) -> None:
        for transition_id, (_attempt, attempt_raw, artifacts) in self.controls.items():
            result = audit_trust_transition(attempt_raw, artifacts, self.catalogue)
            self.assertEqual(result.decision, "allowed", transition_id)
            self.assertEqual(result.reason, "ALLOWED", transition_id)
            self.assertFalse(result.mathematical_authority, transition_id)
            encoded = transition_audit_result_to_bytes(result)
            self.assertEqual(parse_transition_audit_result(encoded), result)
            self.assertEqual(
                hashlib.sha256(attempt_raw).hexdigest(), result.attempt_sha256
            )

    def test_catalogue_is_canonical_closed_and_cross_linked(self) -> None:
        validate_trust_transition_catalogue(self.catalogue)
        self.assertEqual(_canonical(self.catalogue_value), self.catalogue)
        transition_ids = [
            item["transition_id"] for item in self.catalogue_value["transitions"]
        ]
        mutation_ids = [item["mutation_id"] for item in self.catalogue_value["mutations"]]
        self.assertEqual(transition_ids, sorted(set(transition_ids)))
        self.assertEqual(mutation_ids, sorted(set(mutation_ids)))
        self.assertGreaterEqual(len(mutation_ids), 24)
        for transition in self.catalogue_value["transitions"]:
            self.assertTrue(transition["positive_control_ids"])
            self.assertTrue(transition["mutation_ids"])
            self.assertEqual(
                transition["required_binding_roles"],
                sorted(set(transition["required_binding_roles"])),
            )
        broken = copy.deepcopy(self.catalogue_value)
        mutation_id = broken["transitions"][0]["mutation_ids"][0]
        broken["transitions"][0]["mutation_ids"].remove(mutation_id)
        with self.assertRaises(TrustTransitionValidationError):
            validate_trust_transition_catalogue(_canonical(broken))

    def test_all_normative_mutants_have_exact_killed_results(self) -> None:
        report = json.loads(validator.build_report(self.catalogue))
        expected = {
            item["mutation_id"]: item for item in self.catalogue_value["mutations"]
        }
        self.assertEqual(
            [item["mutation_id"] for item in report["mutation_results"]],
            sorted(expected),
        )
        for result in report["mutation_results"]:
            mutation = expected[result["mutation_id"]]
            self.assertEqual(result["outcome"], "killed")
            self.assertEqual(result["decision"], mutation["expected_decision"])
            self.assertEqual(result["effective_tier"], mutation["expected_tier"])
            self.assertEqual(result["reason"], mutation["expected_reason"])
        self.assertTrue(report["g3_passed"])

    def test_malformed_attempts_are_total_and_non_authoritative(self) -> None:
        _attempt, raw, artifacts = next(iter(self.controls.values()))
        malformed = (
            b"",
            b"{}\n",
            b" " + raw,
            raw[:-1],
            raw[:-2] + b',"schema":"mathhead.trust-transition-attempt.v1"}\n',
            b"[" * 1_100 + b"]" * 1_100 + b"\n",
            b'{"value":' + b"9" * 5_000 + b"}\n",
            b"x" * (MAX_ATTEMPT_BYTES + 1),
        )
        for value in malformed:
            result = audit_trust_transition(value, artifacts, self.catalogue)
            self.assertEqual((result.decision, result.reason), ("rejected", "MALFORMED_ATTEMPT"))
            self.assertEqual(result.effective_tier, "none")
            self.assertFalse(result.mathematical_authority)
        oversized = audit_trust_transition(
            b"x" * (MAX_ATTEMPT_BYTES + 1), artifacts, self.catalogue
        )
        self.assertEqual(oversized.attempt_sha256, hashlib.sha256(b"").hexdigest())
        wrong_type = audit_trust_transition(bytearray(raw), artifacts, self.catalogue)  # type: ignore[arg-type]
        self.assertEqual(wrong_type.reason, "MALFORMED_ATTEMPT")

    def test_unknown_duplicate_nul_unicode_and_noncanonical_fields_fail(self) -> None:
        attempt, _raw, _artifacts = next(iter(self.controls.values()))
        cases = []
        unknown = copy.deepcopy(attempt)
        unknown["unknown"] = None
        cases.append(_canonical(unknown))
        nul = copy.deepcopy(attempt)
        nul["issuer"]["component_id"] = "mathhead.\x00attacker"
        cases.append(_canonical(nul))
        non_nfc = copy.deepcopy(attempt)
        non_nfc["issuer"]["component_id"] = "mathhead.e\u0301"
        cases.append(_canonical(non_nfc))
        duplicate = _canonical(attempt)
        cases.append(duplicate[:-2] + b',"status":"verified"}\n')
        for raw in cases:
            result = audit_trust_transition(raw, (), self.catalogue)
            self.assertEqual(result.reason, "MALFORMED_ATTEMPT")

    def test_artifact_inventory_rejects_aliases_extras_reordering_and_wrong_types(self) -> None:
        _attempt, raw, artifacts = self.controls[
            "transition.none.proof-checker.issue"
        ]
        cases = (
            artifacts[:-1],
            (*artifacts, b"extra"),
            (*artifacts, artifacts[0]),
            tuple(reversed(artifacts)),
            (*artifacts[:-1], bytearray(artifacts[-1])),
        )
        for values in cases:
            result = audit_trust_transition(raw, values, self.catalogue)  # type: ignore[arg-type]
            if values == tuple(reversed(artifacts)):
                self.assertEqual(result.decision, "allowed")
            else:
                self.assertNotEqual(result.decision, "allowed")
                self.assertFalse(result.mathematical_authority)
        list_result = audit_trust_transition(raw, list(artifacts), self.catalogue)  # type: ignore[arg-type]
        self.assertEqual(list_result.reason, "ARTIFACT_MISMATCH")

    def test_result_objects_are_closed_frozen_copy_safe_and_not_pickle_authority(self) -> None:
        _attempt, raw, artifacts = next(iter(self.controls.values()))
        result = audit_trust_transition(raw, artifacts, self.catalogue)
        with self.assertRaises(PermissionError):
            TransitionAuditResult()  # type: ignore[call-arg]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.mathematical_authority = True  # type: ignore[misc]
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        with self.assertRaises(TypeError):

            class Forged(TransitionAuditResult):
                pass

        forged = object.__new__(TransitionAuditResult)
        for field in result.__slots__:
            object.__setattr__(forged, field, getattr(result, field))
        object.__setattr__(forged, "mathematical_authority", True)
        with self.assertRaises(TrustTransitionValidationError):
            transition_audit_result_to_bytes(forged)

    def test_result_parser_recomputes_closed_combinations(self) -> None:
        _attempt, raw, artifacts = next(iter(self.controls.values()))
        encoded = transition_audit_result_to_bytes(
            audit_trust_transition(raw, artifacts, self.catalogue)
        )
        value = json.loads(encoded)
        mutations = []
        for field, replacement in (
            ("mathematical_authority", True),
            ("reason", "STATUS_FORBIDDEN"),
            ("decision", "rejected"),
            ("bindings_satisfied", False),
        ):
            changed = copy.deepcopy(value)
            changed[field] = replacement
            mutations.append(_canonical(changed))
        mutations.extend((b" " + encoded, encoded[:-1]))
        for mutation in mutations:
            with self.assertRaises(TrustTransitionValidationError):
                parse_transition_audit_result(mutation)

    def test_catalogue_corruption_unknown_edges_and_wrong_claims_fail_closed(self) -> None:
        attempt, raw, artifacts = self.controls[
            "transition.none.proof-checker.issue"
        ]
        corrupt = audit_trust_transition(raw, artifacts, b" " + self.catalogue)
        self.assertEqual((corrupt.decision, corrupt.reason), ("rejected", "CATALOGUE_INVALID"))
        substituted = copy.deepcopy(self.catalogue_value)
        substituted["transitions"][0]["allowed_statuses"] = ["completed"]
        changed = audit_trust_transition(raw, artifacts, _canonical(substituted))
        self.assertEqual(
            (changed.decision, changed.reason), ("rejected", "CATALOGUE_INVALID")
        )
        unknown = copy.deepcopy(attempt)
        unknown["transition_id"] = "transition.unknown.attack"
        result = audit_trust_transition(_canonical(unknown), artifacts, self.catalogue)
        self.assertEqual((result.decision, result.reason), ("rejected", "TRANSITION_UNKNOWN"))
        wrong = copy.deepcopy(attempt)
        wrong["claimed_authority"] = "external_proof_assistant"
        result = audit_trust_transition(_canonical(wrong), artifacts, self.catalogue)
        self.assertEqual((result.decision, result.reason), ("downgraded", "TIER_CLAIM_MISMATCH"))
        self.assertEqual(result.effective_tier, "none")

    def test_effect_surfaces_have_no_unclassified_authority_route(self) -> None:
        results = validator._effect_results(self.catalogue_value)
        self.assertEqual(
            [item["surface_id"] for item in results], list(validator.EFFECT_SURFACES)
        )
        for result in results:
            self.assertEqual(result["authority_sites"], 0, result["surface_id"])
            self.assertEqual(result["violations"], [], result["surface_id"])
        effects = {item["surface_id"]: item for item in self.catalogue_value["effects"]}
        for surface_id, item in effects.items():
            self.assertFalse(item["authority_issuer"], surface_id)
            if surface_id in {"solver.sympy", "solver.z3"}:
                self.assertEqual(item["maximum_tier"], "producer_report")

    def test_static_issuer_and_tier_literal_inventory_is_exact(self) -> None:
        self.assertEqual(
            validator._authority_literals(), validator.AUTHORITY_LITERAL_COUNTS
        )
        sites = validator._issuer_site_report()
        self.assertEqual(len(sites), 5)
        self.assertEqual(
            {item["tier"] for item in sites},
            {"checker_attestation", "external_proof_assistant"},
        )

    def test_pure_auditor_closure_has_no_effect_or_third_party_roots(self) -> None:
        path = ROOT / "src/mathhead/kernel/trust_transitions.py"
        tree = ast.parse(path.read_bytes())
        roots = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        roots.update(
            node.module.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertLessEqual(
            roots,
            {
                "__future__",
                "dataclasses",
                "hashlib",
                "json",
                "re",
                "typing",
                "unicodedata",
            },
        )
        self.assertFalse(
            roots
            & {
                "importlib",
                "mcp",
                "mpmath",
                "multiprocessing",
                "os",
                "pathlib",
                "pysat",
                "random",
                "shutil",
                "subprocess",
                "sympy",
                "time",
                "z3",
            }
        )

    def test_catalogue_and_report_are_identical_across_processes(self) -> None:
        script = (
            "import hashlib; "
            "from tools import validate_trust_transitions as v; "
            "c,_=v.build_catalogue(); r=v.build_report(c); "
            "print(hashlib.sha256(c).hexdigest(),hashlib.sha256(r).hexdigest())"
        )
        first = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        second = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.assertEqual(first, second)

    def test_dependency_minimal_and_jsonschema_profiles_match(self) -> None:
        full = validator.build_report(self.catalogue)
        saved = validator.Draft202012Validator
        try:
            validator.Draft202012Validator = None
            minimal = validator.build_report(self.catalogue)
        finally:
            validator.Draft202012Validator = saved
        self.assertEqual(minimal, full)

    def test_write_modes_are_deterministic_and_do_not_change_repository_targets(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            catalogue = Path(directory) / "catalogue.json"
            report = Path(directory) / "report.json"
            validator.validate_repository(
                write_catalogue=catalogue,
                write_report=report,
            )
            self.assertEqual(catalogue.read_bytes(), self.catalogue)
            self.assertEqual(report.read_bytes(), validator.build_report(self.catalogue))

    def test_report_writer_rejects_escape_symlink_and_hardlink_targets(self) -> None:
        with self.assertRaises(validator.TrustTransitionReportError):
            validator._safe_output_path(ROOT.parent / "trust-transition-escape.json")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            real = root / "real.json"
            real.write_bytes(b"old\n")
            symlink = root / "symlink.json"
            try:
                symlink.symlink_to(real)
            except OSError:
                pass
            else:
                with self.assertRaises(validator.TrustTransitionReportError):
                    validator._safe_output_path(symlink)
            hardlink = root / "hardlink.json"
            try:
                os.link(real, hardlink)
            except OSError:
                pass
            else:
                with self.assertRaises(validator.TrustTransitionReportError):
                    validator._safe_output_path(hardlink)


if __name__ == "__main__":
    unittest.main()
