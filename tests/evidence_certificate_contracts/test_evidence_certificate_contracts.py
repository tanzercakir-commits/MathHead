from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import validate_evidence_certificate_contracts as contracts  # noqa: E402


class EvidenceCertificateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence_schema, cls.evidence_raw = contracts.load_json(
            ROOT / contracts.EVIDENCE_SCHEMA_PATH
        )
        cls.certificate_schema, cls.certificate_raw = contracts.load_json(
            ROOT / contracts.CERTIFICATE_SCHEMA_PATH
        )

    def evidence(self) -> dict[str, object]:
        return copy.deepcopy(contracts.minimal_evidence())

    def certificate(self, evidence: dict[str, object]) -> dict[str, object]:
        return copy.deepcopy(contracts.minimal_certificate(evidence))

    def rebind_evidence(self, value: dict[str, object]) -> None:
        value["generation"]["basis_sha256"] = contracts.evidence_generation_basis_sha256(value)

    def rebind_certificate(self, value: dict[str, object]) -> None:
        value["replay"]["basis_sha256"] = contracts.certificate_replay_basis_sha256(value)

    def assert_bad_evidence(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(contracts.EvidenceCertificateValidationError) as caught:
            contracts.validate_evidence(value, self.evidence_schema)
        self.assertEqual(caught.exception.kind, kind)

    def assert_bad_certificate(
        self,
        value: dict[str, object],
        evidence: dict[str, object] | None,
        kind: str,
    ) -> None:
        with self.assertRaises(contracts.EvidenceCertificateValidationError) as caught:
            contracts.validate_certificate(
                value,
                self.certificate_schema,
                evidence=evidence,
                evidence_schema=self.evidence_schema if evidence is not None else None,
            )
        self.assertEqual(caught.exception.kind, kind)

    def add_evidence_diagnostic(
        self,
        value: dict[str, object],
        *,
        severity: str = "warning",
        identifier: str = "diagnostic_evidence",
    ) -> None:
        value["diagnostics"] = [
            {
                "diagnostic_id": identifier,
                "severity": severity,
                "code": "org.mathhead.evidence",
                "message": "evidence generation did not complete normally",
                "related_payload_ids": [],
                "details": {},
            }
        ]
        value["outcome"]["diagnostic_ids"] = [identifier]

    def set_certificate_verdict(
        self,
        value: dict[str, object],
        verdict: dict[str, object],
        *,
        severity: str = "warning",
    ) -> None:
        verdict["diagnostic_ids"] = ["diagnostic_certificate"]
        value["verdict"] = verdict
        value["diagnostics"] = [
            {
                "diagnostic_id": "diagnostic_certificate",
                "severity": severity,
                "code": "org.mathhead.certificate",
                "message": "certificate replay did not verify",
                "related_artifact_ids": [],
                "details": {},
            }
        ]

    def test_schema_hashes_closed_roots_and_canonical_roundtrip(self) -> None:
        self.assertEqual(
            hashlib.sha256(self.evidence_raw).hexdigest(), contracts.EVIDENCE_SCHEMA_SHA256
        )
        self.assertEqual(
            hashlib.sha256(self.certificate_raw).hexdigest(),
            contracts.CERTIFICATE_SCHEMA_SHA256,
        )
        self.assertFalse(self.evidence_schema["additionalProperties"])
        self.assertFalse(self.certificate_schema["additionalProperties"])
        self.assertEqual(set(self.evidence_schema["required"]), contracts.EVIDENCE_ROOT_FIELDS)
        self.assertEqual(
            set(self.certificate_schema["required"]), contracts.CERTIFICATE_ROOT_FIELDS
        )
        evidence = self.evidence()
        certificate = self.certificate(evidence)
        contracts.validate_evidence(evidence, self.evidence_schema)
        contracts.validate_certificate(
            certificate,
            self.certificate_schema,
            evidence=evidence,
            evidence_schema=self.evidence_schema,
        )
        self.assertEqual(json.loads(contracts.canonical_bytes(evidence)), evidence)

    def test_standard_draft_202012_metaschema_and_instances(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema is optional outside the test profile")
        jsonschema.Draft202012Validator.check_schema(self.evidence_schema)
        jsonschema.Draft202012Validator.check_schema(self.certificate_schema)
        jsonschema.Draft202012Validator(self.evidence_schema).validate(self.evidence())
        evidence = self.evidence()
        jsonschema.Draft202012Validator(self.certificate_schema).validate(
            self.certificate(evidence)
        )

    def test_unknown_missing_and_malformed_tagged_variants_fail(self) -> None:
        unknown = self.evidence()
        unknown["verified"] = True
        self.assert_bad_evidence(unknown, "schema")
        missing = self.evidence()
        missing.pop("producer")
        self.assert_bad_evidence(missing, "schema")
        malformed = self.evidence()
        malformed["outcome"]["status"] = "verified"
        self.assert_bad_evidence(malformed, "schema")

        evidence = self.evidence()
        certificate = self.certificate(evidence)
        certificate["producer_verdict"] = "verified"
        self.assert_bad_certificate(certificate, evidence, "schema")

    def test_duplicate_keys_and_noncanonical_files_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(contracts.EvidenceCertificateValidationError) as caught:
                contracts.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")

            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.evidence(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(contracts.EvidenceCertificateValidationError) as caught:
                contracts.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")

            canonical = Path(directory) / "canonical.json"
            canonical.write_bytes(contracts.canonical_bytes(self.evidence()))
            loaded, raw = contracts.load_json(canonical, require_canonical=True)
            self.assertEqual(raw, contracts.canonical_bytes(loaded))

    def test_unicode_scalar_shape_and_input_budgets_fail(self) -> None:
        decomposed = self.evidence()
        decomposed["extensions"] = {"org.mathhead.test": "es\u0327it"}
        self.assert_bad_evidence(decomposed, "canonical")
        nul = self.evidence()
        nul["extensions"] = {"org.mathhead.test": "bad\x00value"}
        self.assert_bad_evidence(nul, "canonical")
        floating = self.evidence()
        floating["extensions"] = {"org.mathhead.test": {"ratio": 0.5}}
        self.assert_bad_evidence(floating, "schema")
        integer = self.evidence()
        integer["extensions"] = {
            "org.mathhead.test": {"count": contracts.MAX_JSON_INTEGER + 1}
        }
        self.assert_bad_evidence(integer, "budget")

        nested: object = None
        for _ in range(contracts.MAX_CANONICAL_NESTING + 1):
            nested = [nested]
        deep = self.evidence()
        deep["extensions"] = {"org.mathhead.test": nested}
        self.assert_bad_evidence(deep, "budget")
        with mock.patch.object(contracts, "MAX_CANONICAL_NODES", 1):
            self.assert_bad_evidence(self.evidence(), "budget")
        with mock.patch.object(contracts, "MAX_ENTITIES", 0):
            self.assert_bad_evidence(self.evidence(), "budget")

        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b"{}\n")
            with mock.patch.object(contracts, "MAX_INPUT_BYTES", 1):
                with self.assertRaises(contracts.EvidenceCertificateValidationError) as caught:
                    contracts.load_json(oversized)
            self.assertEqual(caught.exception.kind, "budget")

    def test_evidence_format_compatibility_and_generation_replay(self) -> None:
        evidence = self.evidence()
        evidence["format"]["version"] = "1.2.0"
        evidence["format"]["minor"] = 2
        evidence["format"]["reader_minimum_minor"] = 1
        evidence["generation"]["mode"] = "seeded"
        evidence["generation"]["seed"] = 7
        self.rebind_evidence(evidence)
        contracts.validate_evidence(evidence, self.evidence_schema)

        confused = self.evidence()
        confused["format"]["version"] = "1.2.0"
        self.rebind_evidence(confused)
        self.assert_bad_evidence(confused, "compatibility")
        future = self.evidence()
        future["format"]["version"] = "2.0.0"
        future["format"]["major"] = 2
        self.rebind_evidence(future)
        self.assert_bad_evidence(future, "schema")
        unordered = self.evidence()
        unordered["format"]["features"] = ["org.mathhead.zeta", "org.mathhead.alpha"]
        self.rebind_evidence(unordered)
        self.assert_bad_evidence(unordered, "canonical")
        seed = self.evidence()
        seed["generation"]["seed"] = 1
        self.rebind_evidence(seed)
        self.assert_bad_evidence(seed, "replay")
        drift = self.evidence()
        drift["subject"]["statement_sha256"] = "f" * 64
        self.assert_bad_evidence(drift, "replay")

    def test_payload_primary_order_identity_and_outcome_binding(self) -> None:
        unordered = self.evidence()
        unordered["payloads"].insert(
            0,
            {
                "payload_id": "payload_zeta",
                "role": "auxiliary",
                "media_type": "application/json",
                "sha256": "a" * 64,
                "byte_count": 1,
                "encoding": "utf-8",
                "compression": "none",
                "extensions": {},
            },
        )
        unordered["outcome"]["payload_ids"] = ["payload_proof", "payload_zeta"]
        self.assert_bad_evidence(unordered, "canonical")

        absent = self.evidence()
        absent["primary_payload_id"] = None
        self.assert_bad_evidence(absent, "reference")
        empty = self.evidence()
        empty["payloads"][0]["byte_count"] = 0
        self.assert_bad_evidence(empty, "reference")
        omitted = self.evidence()
        omitted["outcome"]["payload_ids"] = []
        self.assert_bad_evidence(omitted, "outcome")

    def test_dependency_closure_order_resolution_and_cycles(self) -> None:
        evidence = self.evidence()
        evidence["dependencies"] = [
            {
                "evidence_id": "evidence_a",
                "evidence_sha256": "a" * 64,
                "relation": "premise",
                "depends_on_evidence_ids": [],
            },
            {
                "evidence_id": "evidence_b",
                "evidence_sha256": "b" * 64,
                "relation": "derivation",
                "depends_on_evidence_ids": ["evidence_a"],
            },
        ]
        self.rebind_evidence(evidence)
        contracts.validate_evidence(evidence, self.evidence_schema)

        unresolved = copy.deepcopy(evidence)
        unresolved["dependencies"][1]["depends_on_evidence_ids"] = ["evidence_missing"]
        self.rebind_evidence(unresolved)
        self.assert_bad_evidence(unresolved, "dependency")
        cycle = copy.deepcopy(evidence)
        cycle["dependencies"][0]["depends_on_evidence_ids"] = ["evidence_b"]
        self.rebind_evidence(cycle)
        self.assert_bad_evidence(cycle, "dependency")
        duplicate_hash = copy.deepcopy(evidence)
        duplicate_hash["dependencies"][1]["evidence_sha256"] = "a" * 64
        self.rebind_evidence(duplicate_hash)
        self.assert_bad_evidence(duplicate_hash, "dependency")
        self_ref = self.evidence()
        self_ref["dependencies"] = [
            {
                "evidence_id": "evidence_example",
                "evidence_sha256": "c" * 64,
                "relation": "input",
                "depends_on_evidence_ids": [],
            }
        ]
        self.rebind_evidence(self_ref)
        self.assert_bad_evidence(self_ref, "dependency")

    def test_evidence_outcomes_never_express_checker_authority(self) -> None:
        variants = [
            (
                {"status": "unsupported", "unsupported_features": ["org.mathhead.foo"], "reason": "unsupported", "diagnostic_ids": []},
                "completed",
                "warning",
            ),
            ({"status": "incomplete", "reason": "partial", "diagnostic_ids": []}, "completed", "warning"),
            ({"status": "cancelled", "cancellation_id": "cancel_user", "reason": "cancelled", "diagnostic_ids": []}, "cancelled", "warning"),
            ({"status": "exhausted", "dimensions": ["wall_time_us"], "reason": "budget", "diagnostic_ids": []}, "exhausted", "warning"),
            ({"status": "truncated", "truncation_ids": ["truncate_output"], "retained_payload_ids": ["payload_proof"], "reason": "limit", "diagnostic_ids": []}, "truncated", "warning"),
            ({"status": "error", "error_code": "org.mathhead.error", "reason": "failure", "diagnostic_ids": []}, "completed", "error"),
        ]
        for outcome, budget, severity in variants:
            with self.subTest(status=outcome["status"]):
                evidence = self.evidence()
                evidence["outcome"] = outcome
                evidence["budget"]["outcome"] = budget
                self.add_evidence_diagnostic(evidence, severity=severity)
                contracts.validate_evidence(evidence, self.evidence_schema)

        hidden = self.evidence()
        hidden["budget"]["outcome"] = "truncated"
        self.assert_bad_evidence(hidden, "outcome")

    def test_evidence_diagnostic_and_global_identity_rules(self) -> None:
        missing = self.evidence()
        missing["outcome"] = {
            "status": "incomplete",
            "reason": "partial",
            "diagnostic_ids": [],
        }
        self.assert_bad_evidence(missing, "diagnostic")
        dangling = self.evidence()
        dangling["diagnostics"] = [
            {
                "diagnostic_id": "diagnostic_evidence",
                "severity": "warning",
                "code": "org.mathhead.evidence",
                "message": "warning",
                "related_payload_ids": ["payload_missing"],
                "details": {},
            }
        ]
        dangling["outcome"]["diagnostic_ids"] = ["diagnostic_evidence"]
        self.assert_bad_evidence(dangling, "reference")
        collision = self.evidence()
        collision["evidence_id"] = "payload_proof"
        self.rebind_evidence(collision)
        self.assert_bad_evidence(collision, "identity")

    def test_verified_certificate_requires_loaded_valid_evidence_bytes(self) -> None:
        evidence = self.evidence()
        certificate = self.certificate(evidence)
        self.assert_bad_certificate(certificate, None, "reference")

        mutated = copy.deepcopy(evidence)
        mutated["payloads"][0]["byte_count"] += 1
        self.assert_bad_certificate(certificate, mutated, "reference")

        invalid = copy.deepcopy(evidence)
        invalid["payloads"][0]["byte_count"] = 0
        rebound = self.certificate(invalid)
        self.assert_bad_certificate(rebound, invalid, "reference")

    def test_certificate_header_subject_and_dependency_bindings(self) -> None:
        evidence = self.evidence()
        certificate = self.certificate(evidence)
        certificate["evidence"]["primary_payload_sha256"] = "f" * 64
        certificate["replay"]["expected_payload_sha256"] = "f" * 64
        self.rebind_certificate(certificate)
        self.assert_bad_certificate(certificate, evidence, "reference")

        certificate = self.certificate(evidence)
        certificate["subject"]["statement_sha256"] = "f" * 64
        self.rebind_certificate(certificate)
        self.assert_bad_certificate(certificate, evidence, "reference")

    def test_checker_role_and_independence_are_fail_closed(self) -> None:
        evidence = self.evidence()
        certificate = self.certificate(evidence)
        certificate["checker"]["role"] = "solver"
        self.rebind_certificate(certificate)
        self.assert_bad_certificate(certificate, evidence, "schema")

        same_id = self.certificate(evidence)
        same_id["checker"]["component_id"] = evidence["producer"]["component_id"]
        for artifact in same_id["verification_artifacts"]:
            artifact["producer_component_id"] = same_id["checker"]["component_id"]
        self.rebind_certificate(same_id)
        self.assert_bad_certificate(same_id, evidence, "epistemic")

        same_code = self.certificate(evidence)
        same_code["checker"]["contract_sha256"] = evidence["producer"]["contract_sha256"]
        same_code["checker"]["implementation_sha256"] = evidence["producer"][
            "implementation_sha256"
        ]
        self.rebind_certificate(same_code)
        self.assert_bad_certificate(same_code, evidence, "epistemic")

    def test_certificate_format_seed_and_replay_basis_rules(self) -> None:
        evidence = self.evidence()
        seeded = self.certificate(evidence)
        seeded["replay"]["mode"] = "seeded"
        seeded["replay"]["seed"] = 11
        self.rebind_certificate(seeded)
        contracts.validate_certificate(
            seeded,
            self.certificate_schema,
            evidence=evidence,
            evidence_schema=self.evidence_schema,
        )

        seed = self.certificate(evidence)
        seed["replay"]["seed"] = 2
        self.rebind_certificate(seed)
        self.assert_bad_certificate(seed, evidence, "replay")
        basis = self.certificate(evidence)
        basis["checker"]["version"] = "1.0.1"
        self.assert_bad_certificate(basis, evidence, "replay")
        version = self.certificate(evidence)
        version["format"]["version"] = "1.1.0"
        self.rebind_certificate(version)
        self.assert_bad_certificate(version, evidence, "compatibility")

    def test_verification_artifact_producer_order_and_support_rules(self) -> None:
        evidence = self.evidence()
        unordered = self.certificate(evidence)
        unordered["verification_artifacts"].reverse()
        self.assert_bad_certificate(unordered, evidence, "canonical")
        producer = self.certificate(evidence)
        producer["verification_artifacts"][0]["producer_component_id"] = evidence["producer"][
            "component_id"
        ]
        self.assert_bad_certificate(producer, evidence, "epistemic")
        absent = self.certificate(evidence)
        absent["verdict"]["supporting_artifact_ids"] = ["artifact_checker_result"]
        self.assert_bad_certificate(absent, evidence, "artifact")
        missing = self.certificate(evidence)
        missing["verdict"]["checker_result_artifact_id"] = "artifact_replay_log"
        self.assert_bad_certificate(missing, evidence, "artifact")

    def test_verified_trust_closure_order_hashes_and_authority(self) -> None:
        evidence = self.evidence()
        missing = self.certificate(evidence)
        missing["trust_dependencies"].pop()
        self.assert_bad_certificate(missing, evidence, "epistemic")
        unordered = self.certificate(evidence)
        unordered["trust_dependencies"].reverse()
        self.assert_bad_certificate(unordered, evidence, "canonical")
        drift = self.certificate(evidence)
        drift["trust_dependencies"][0]["sha256"] = "f" * 64
        self.assert_bad_certificate(drift, evidence, "epistemic")
        authority = self.certificate(evidence)
        authority["verdict"]["authority"] = "external_verified"
        self.assert_bad_certificate(authority, evidence, "epistemic")

        external = self.certificate(evidence)
        external["checker"]["role"] = "external"
        external["verdict"]["authority"] = "external_verified"
        self.rebind_certificate(external)
        contracts.validate_certificate(
            external,
            self.certificate_schema,
            evidence=evidence,
            evidence_schema=self.evidence_schema,
        )

    def test_replay_mismatch_is_invalid_not_verified(self) -> None:
        evidence = self.evidence()
        verified = self.certificate(evidence)
        verified["replay"]["observed_payload_sha256"] = "f" * 64
        self.rebind_certificate(verified)
        self.assert_bad_certificate(verified, evidence, "replay")

        invalid = self.certificate(evidence)
        invalid["replay"]["observed_payload_sha256"] = "f" * 64
        self.set_certificate_verdict(
            invalid,
            {
                "status": "invalid",
                "reason_code": "replay_mismatch",
                "checker_result_artifact_id": "artifact_checker_result",
                "reason": "replayed payload differs",
            },
        )
        self.rebind_certificate(invalid)
        contracts.validate_certificate(
            invalid,
            self.certificate_schema,
            evidence=evidence,
            evidence_schema=self.evidence_schema,
        )

    def test_certificate_non_success_and_terminal_resource_states(self) -> None:
        variants = [
            ({"status": "unsupported", "unsupported_features": ["org.mathhead.foo"], "reason": "unsupported"}, "completed", "warning"),
            ({"status": "inconclusive", "reason": "no decision"}, "completed", "warning"),
            ({"status": "cancelled", "cancellation_id": "cancel_user", "reason": "cancelled"}, "cancelled", "warning"),
            ({"status": "exhausted", "dimensions": ["wall_time_us"], "reason": "budget"}, "exhausted", "warning"),
            ({"status": "truncated", "truncation_ids": ["truncate_log"], "reason": "limit"}, "truncated", "warning"),
            ({"status": "verifier_failed", "error_code": "org.mathhead.failure", "reason": "checker crashed"}, "completed", "error"),
        ]
        evidence = self.evidence()
        for verdict, budget, severity in variants:
            with self.subTest(status=verdict["status"]):
                certificate = self.certificate(evidence)
                self.set_certificate_verdict(certificate, verdict, severity=severity)
                certificate["budget"]["outcome"] = budget
                contracts.validate_certificate(
                    certificate,
                    self.certificate_schema,
                    evidence=evidence,
                    evidence_schema=self.evidence_schema,
                )
        hidden = self.certificate(evidence)
        hidden["budget"]["outcome"] = "exhausted"
        self.assert_bad_certificate(hidden, evidence, "outcome")

    def test_disagreement_diagnostics_references_and_id_collisions(self) -> None:
        evidence = self.evidence()
        disagreement = self.certificate(evidence)
        self.set_certificate_verdict(
            disagreement,
            {
                "status": "disagreement",
                "conflicting_artifact_ids": [
                    "artifact_checker_result",
                    "artifact_replay_log",
                ],
                "reason": "checker observations conflict",
            },
            severity="error",
        )
        contracts.validate_certificate(
            disagreement,
            self.certificate_schema,
            evidence=evidence,
            evidence_schema=self.evidence_schema,
        )

        dangling = copy.deepcopy(disagreement)
        dangling["diagnostics"][0]["related_artifact_ids"] = ["artifact_missing"]
        self.assert_bad_certificate(dangling, evidence, "reference")
        collision = self.certificate(evidence)
        collision["certificate_id"] = "attempt_checker"
        self.rebind_certificate(collision)
        self.assert_bad_certificate(collision, evidence, "identity")

    def test_contract_constants_and_cli_minimal_examples(self) -> None:
        self.assertEqual(contracts.EVIDENCE_CONTRACT_ID, "MH-C-EVIDENCE-001")
        self.assertEqual(contracts.CERTIFICATE_CONTRACT_ID, "MH-C-CERTIFICATE-001")
        self.assertEqual(contracts.main([]), 0)


if __name__ == "__main__":
    unittest.main()
