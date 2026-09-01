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

from tools import validate_engine_result_contract as result  # noqa: E402


class EngineResultContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema, cls.schema_raw = result.load_json(ROOT / result.SCHEMA_PATH)

    def valid(self) -> dict[str, object]:
        return copy.deepcopy(result.minimal_engine_result())

    def rebind(self, value: dict[str, object]) -> None:
        value["replay"]["basis_sha256"] = result.replay_basis_sha256(value)

    def assert_invalid(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(result.EngineResultValidationError) as caught:
            result.validate_engine_result(value, self.schema)
        self.assertEqual(caught.exception.kind, kind)

    def add_artifact(
        self,
        value: dict[str, object],
        identifier: str,
        kind: str,
        *,
        producer: str = "component_engine",
        sha: str | None = None,
    ) -> None:
        value["artifacts"].append(
            {
                "artifact_id": identifier,
                "kind": kind,
                "schema": f"org.mathhead.{kind.replace('_', '-')}",
                "sha256": sha or hashlib.sha256(identifier.encode()).hexdigest(),
                "byte_count": 10,
                "producer_component_id": producer,
                "extensions": {},
            }
        )
        value["artifacts"].sort(key=lambda item: item["artifact_id"])

    def add_diagnostic(
        self,
        value: dict[str, object],
        *,
        severity: str = "warning",
        identifier: str = "diagnostic_result",
    ) -> None:
        value["diagnostics"] = [
            {
                "diagnostic_id": identifier,
                "severity": severity,
                "code": "org.mathhead.result",
                "message": "result did not complete normally",
                "related_artifact_ids": [],
                "details": {},
            }
        ]
        value["execution"]["diagnostic_ids"] = [identifier]

    def unknown(self, reason: str = "search_incomplete") -> dict[str, object]:
        value = self.valid()
        value["assessments"][0]["verdict"] = {
            "status": "unknown",
            "epistemic_tier": "producer_reported",
            "reason": reason,
            "support_artifact_ids": [],
        }
        value["execution"] = {
            "status": "unknown",
            "reason_code": "search_incomplete",
            "reason": "bounded search ended without a verdict",
            "diagnostic_ids": [],
        }
        self.add_diagnostic(value)
        return value

    def ambiguous(self) -> dict[str, object]:
        value = self.valid()
        value["request"]["candidate_reading_ids"] = ["reading_alternative", "reading_primary"]
        value["request"]["selected_reading_id"] = None
        value["assessments"] = []
        value["execution"] = {
            "status": "ambiguous",
            "reading_ids": ["reading_alternative", "reading_primary"],
            "reason": "multiple readings require an explicit choice",
            "diagnostic_ids": [],
        }
        self.add_diagnostic(value)
        self.rebind(value)
        return value

    def test_normative_schema_identity_closed_root_and_canonical_roundtrip(self) -> None:
        self.assertEqual(hashlib.sha256(self.schema_raw).hexdigest(), result.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(set(self.schema["required"]), result.ROOT_FIELDS)
        self.assertFalse(self.schema["additionalProperties"])
        value = self.valid()
        result.validate_engine_result(value, self.schema)
        self.assertEqual(json.loads(result.canonical_bytes(value)), value)
        self.assertEqual(
            result.canonical_sha256(value),
            hashlib.sha256(result.canonical_bytes(value)).hexdigest(),
        )

    def test_unknown_missing_and_malformed_tagged_union_fail(self) -> None:
        unknown = self.valid()
        unknown["unknown"] = True
        self.assert_invalid(unknown, "schema")

        missing = self.valid()
        missing.pop("budget")
        self.assert_invalid(missing, "schema")

        malformed = self.valid()
        malformed["execution"]["status"] = "successful"
        self.assert_invalid(malformed, "schema")

    def test_duplicate_keys_and_noncanonical_file_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(result.EngineResultValidationError) as caught:
                result.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")

            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.valid(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(result.EngineResultValidationError) as caught:
                result.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")

            canonical = Path(directory) / "canonical.json"
            canonical.write_bytes(result.canonical_bytes(self.valid()))
            loaded, raw = result.load_json(canonical, require_canonical=True)
            self.assertEqual(raw, result.canonical_bytes(loaded))

    def test_unicode_nul_float_integer_nesting_node_and_input_budgets_fail(self) -> None:
        decomposed = self.valid()
        decomposed["extensions"] = {"org.mathhead.test": "es\u0327it"}
        self.assert_invalid(decomposed, "canonical")

        nul = self.valid()
        nul["extensions"] = {"org.mathhead.test": "bad\x00value"}
        self.assert_invalid(nul, "canonical")

        floating = self.valid()
        floating["extensions"] = {"org.mathhead.test": {"ratio": 0.5}}
        self.assert_invalid(floating, "schema")

        integer = self.valid()
        integer["extensions"] = {"org.mathhead.test": {"count": result.MAX_JSON_INTEGER + 1}}
        self.assert_invalid(integer, "budget")

        nested: object = None
        for _ in range(result.MAX_CANONICAL_NESTING + 1):
            nested = [nested]
        deep = self.valid()
        deep["extensions"] = {"org.mathhead.test": nested}
        self.assert_invalid(deep, "budget")

        with mock.patch.object(result, "MAX_CANONICAL_NODES", 1):
            self.assert_invalid(self.valid(), "budget")
        with mock.patch.object(result, "MAX_ENTITIES", 1):
            self.assert_invalid(self.valid(), "budget")

        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b"{}\n")
            with mock.patch.object(result, "MAX_INPUT_BYTES", 1):
                with self.assertRaises(result.EngineResultValidationError) as caught:
                    result.load_json(oversized)
            self.assertEqual(caught.exception.kind, "budget")

    def test_replay_seed_policy_and_basis_identity_fail_closed(self) -> None:
        seeded = self.valid()
        seeded["replay"]["mode"] = "seeded"
        seeded["replay"]["seed"] = 7
        self.rebind(seeded)
        result.validate_engine_result(seeded, self.schema)

        missing = self.valid()
        missing["replay"]["mode"] = "seeded"
        self.assert_invalid(missing, "replay")

        drift = self.valid()
        drift["provenance"]["producer"]["version"] = "1.0.1"
        self.assert_invalid(drift, "replay")

    def test_reading_selection_ambiguity_and_goal_identity_rules(self) -> None:
        value = self.ambiguous()
        result.validate_engine_result(value, self.schema)

        selected = self.ambiguous()
        selected["request"]["selected_reading_id"] = "reading_primary"
        self.assert_invalid(selected, "reading")

        omitted = self.ambiguous()
        omitted["execution"]["reading_ids"] = ["reading_primary", "reading_other"]
        self.assert_invalid(omitted, "reading")

        duplicate = self.valid()
        duplicate["request"]["goal_ids"] = ["goal_main", "goal_main"]
        self.assert_invalid(duplicate, "schema")

    def test_provenance_order_role_and_global_identity_fail(self) -> None:
        unordered = self.valid()
        checker = copy.deepcopy(unordered["provenance"]["components"][0])
        checker.update(
            {
                "component_id": "component_analyzer",
                "role": "heuristic",
                "name": "org.mathhead.analyzer",
            }
        )
        unordered["provenance"]["components"].append(checker)
        self.rebind(unordered)
        self.assert_invalid(unordered, "canonical")

        role = self.valid()
        role["provenance"]["producer"]["role"] = "solver"
        self.assert_invalid(role, "provenance")

        collision = self.valid()
        collision["provenance"]["components"][0]["component_id"] = "result_example"
        self.assert_invalid(collision, "identity")

    def test_artifact_order_producer_reference_and_content_identity_fail(self) -> None:
        order = self.valid()
        order["artifacts"].reverse()
        self.assert_invalid(order, "canonical")

        producer = self.valid()
        producer["artifacts"][0]["producer_component_id"] = "component_missing"
        self.assert_invalid(producer, "reference")

        duplicate = self.valid()
        artifact = copy.deepcopy(duplicate["artifacts"][-1])
        artifact["artifact_id"] = "artifact_proof_alias"
        duplicate["artifacts"].append(artifact)
        duplicate["artifacts"].sort(key=lambda item: item["artifact_id"])
        self.assert_invalid(duplicate, "identity")

    def test_assessments_cover_completed_goals_in_request_order(self) -> None:
        missing = self.valid()
        missing["assessments"] = []
        self.assert_invalid(missing, "outcome")

        order = self.valid()
        second = copy.deepcopy(order["assessments"][0])
        second.update({"assessment_id": "assessment_other", "goal_id": "goal_other"})
        order["request"]["goal_ids"] = ["goal_main", "goal_other"]
        order["assessments"] = [second, order["assessments"][0]]
        self.rebind(order)
        self.assert_invalid(order, "canonical")

        reading = self.valid()
        reading["assessments"][0]["reading_id"] = "reading_other"
        self.assert_invalid(reading, "reading")

    def test_assumptions_and_obligations_are_canonical_and_typed(self) -> None:
        assumptions = self.valid()
        other = copy.deepcopy(assumptions["assessments"][0]["assumption_refs"][0])
        other["declaration_id"] = "declaration_another"
        assumptions["assessments"][0]["assumption_refs"].append(other)
        self.assert_invalid(assumptions, "canonical")

        obligation = self.valid()
        obligation["assessments"][0]["discharged_obligations"][0]["evidence_artifact_ids"] = [
            "artifact_checker_result"
        ]
        self.assert_invalid(obligation, "artifact")

    def test_proof_requires_independent_checker_and_bound_trust_dependencies(self) -> None:
        witness = self.valid()
        witness["artifacts"][-1]["kind"] = "witness"
        result.validate_engine_result(witness, self.schema)

        external = self.valid()
        external["provenance"]["components"][0]["role"] = "external"
        external["assessments"][0]["verdict"]["epistemic_tier"] = "external_verified"
        self.rebind(external)
        result.validate_engine_result(external, self.schema)

        role = self.valid()
        role["provenance"]["components"][0]["role"] = "solver"
        self.rebind(role)
        self.assert_invalid(role, "epistemic")

        contract = self.valid()
        contract["assessments"][0]["verdict"]["verification"]["checker_contract_sha256"] = "0" * 64
        self.assert_invalid(contract, "epistemic")

        dependency = self.valid()
        dependencies = dependency["assessments"][0]["verdict"]["verification"][
            "trust_dependency_sha256"
        ]
        dependencies.remove("1" * 64)
        self.assert_invalid(dependency, "epistemic")

    def test_verification_artifacts_must_match_checker_and_support(self) -> None:
        producer = self.valid()
        producer["artifacts"][0]["producer_component_id"] = "component_engine"
        self.assert_invalid(producer, "epistemic")

        kind = self.valid()
        kind["artifacts"][1]["kind"] = "witness"
        self.assert_invalid(kind, "artifact")

        support = self.valid()
        support["assessments"][0]["verdict"]["support_artifact_ids"].remove("artifact_evidence")
        self.assert_invalid(support, "epistemic")

    def test_refutation_requires_counterexample_support(self) -> None:
        value = self.valid()
        self.add_artifact(value, "artifact_counterexample", "counterexample")
        verdict = value["assessments"][0]["verdict"]
        verdict["status"] = "refuted"
        verdict["counterexample_artifact_ids"] = ["artifact_counterexample"]
        verdict["support_artifact_ids"].append("artifact_counterexample")
        verdict["support_artifact_ids"].sort()
        result.validate_engine_result(value, self.schema)

        missing = copy.deepcopy(value)
        missing["assessments"][0]["verdict"]["counterexample_artifact_ids"] = []
        missing["assessments"][0]["verdict"]["support_artifact_ids"].remove(
            "artifact_counterexample"
        )
        result.validate_engine_result(missing, self.schema)

        unsupported = copy.deepcopy(value)
        unsupported["assessments"][0]["verdict"]["counterexample_artifact_ids"] = []
        unsupported["assessments"][0]["verdict"]["support_artifact_ids"] = [
            "artifact_checker_result",
            "artifact_evidence",
        ]
        self.assert_invalid(unsupported, "artifact")

    def test_bounds_distinguish_reported_one_sided_and_verified_exact(self) -> None:
        reported = self.valid()
        self.add_artifact(reported, "artifact_value_lower", "value")
        reported["assessments"][0]["verdict"] = {
            "status": "bounded",
            "epistemic_tier": "producer_reported",
            "bounds": [
                {
                    "direction": "lower",
                    "inclusive": True,
                    "value_artifact_id": "artifact_value_lower",
                }
            ],
            "exact": False,
            "support_artifact_ids": ["artifact_value_lower"],
            "verification": None,
        }
        result.validate_engine_result(reported, self.schema)

        exact = self.valid()
        self.add_artifact(exact, "artifact_value_exact", "value")
        verification = copy.deepcopy(exact["assessments"][0]["verdict"]["verification"])
        support = copy.deepcopy(exact["assessments"][0]["verdict"]["support_artifact_ids"])
        support.append("artifact_value_exact")
        support.sort()
        exact["assessments"][0]["verdict"] = {
            "status": "bounded",
            "epistemic_tier": "checker_attested",
            "bounds": [
                {
                    "direction": "lower",
                    "inclusive": True,
                    "value_artifact_id": "artifact_value_exact",
                },
                {
                    "direction": "upper",
                    "inclusive": True,
                    "value_artifact_id": "artifact_value_exact",
                },
            ],
            "exact": True,
            "support_artifact_ids": support,
            "verification": verification,
        }
        result.validate_engine_result(exact, self.schema)

        unverified = copy.deepcopy(exact)
        unverified["assessments"][0]["verdict"]["epistemic_tier"] = "producer_reported"
        unverified["assessments"][0]["verdict"]["verification"] = None
        self.assert_invalid(unverified, "epistemic")

        absent = copy.deepcopy(reported)
        absent["assessments"][0]["verdict"]["support_artifact_ids"] = []
        self.assert_invalid(absent, "artifact")

    def test_execution_and_verdict_states_cannot_contradict(self) -> None:
        unknown = self.unknown()
        result.validate_engine_result(unknown, self.schema)

        contradiction = self.unknown()
        contradiction["assessments"][0]["verdict"] = copy.deepcopy(
            self.valid()["assessments"][0]["verdict"]
        )
        self.assert_invalid(contradiction, "outcome")

        unsupported = self.valid()
        unsupported["assessments"][0]["verdict"] = {
            "status": "unsupported",
            "epistemic_tier": "producer_reported",
            "feature_codes": ["org.mathhead.transcendental"],
        }
        unsupported["execution"] = {
            "status": "unsupported",
            "feature_codes": ["org.mathhead.transcendental"],
            "reason": "input feature is outside the supported fragment",
            "diagnostic_ids": [],
        }
        self.add_diagnostic(unsupported)
        result.validate_engine_result(unsupported, self.schema)

        mismatched = copy.deepcopy(unsupported)
        mismatched["execution"]["feature_codes"] = ["org.mathhead.polynomial"]
        self.assert_invalid(mismatched, "outcome")

        reason = self.unknown()
        reason["assessments"][0]["verdict"]["reason"] = "insufficient_evidence"
        self.assert_invalid(reason, "outcome")

    def test_budget_snapshot_cannot_hide_resource_outcomes(self) -> None:
        retained = self.valid()
        retained["budget"]["usage"]["memory_retained_bytes"] = 501
        self.assert_invalid(retained, "budget")

        hidden = self.valid()
        hidden["budget"]["outcome"] = "exhausted"
        self.assert_invalid(hidden, "outcome")

        cancelled = self.valid()
        cancelled["execution"] = {
            "status": "cancelled",
            "cancellation_id": "cancellation_user",
            "reason": "user cancelled",
            "diagnostic_ids": [],
        }
        cancelled["budget"]["outcome"] = "cancelled"
        result.validate_engine_result(cancelled, self.schema)

        mismatch = copy.deepcopy(cancelled)
        mismatch["budget"]["outcome"] = "completed"
        self.assert_invalid(mismatch, "outcome")

    def test_diagnostics_are_complete_and_completion_hides_no_error(self) -> None:
        missing = self.unknown()
        missing["execution"]["diagnostic_ids"] = []
        self.assert_invalid(missing, "diagnostic")

        silent = self.unknown()
        silent["diagnostics"] = []
        silent["execution"]["diagnostic_ids"] = []
        self.assert_invalid(silent, "diagnostic")

        hidden = self.valid()
        self.add_diagnostic(hidden, severity="error")
        self.assert_invalid(hidden, "outcome")

    def test_exhaustion_truncation_and_ambiguity_remain_explicit(self) -> None:
        exhausted = self.valid()
        exhausted["execution"] = {
            "status": "exhausted",
            "exhaustion_id": "exhaustion_wall",
            "dimensions": ["wall_time_us"],
            "reason": "deadline reached",
            "diagnostic_ids": [],
        }
        exhausted["budget"]["outcome"] = "exhausted"
        result.validate_engine_result(exhausted, self.schema)

        truncated = self.valid()
        truncated["execution"] = {
            "status": "truncated",
            "truncation_ids": ["truncation_output"],
            "reason": "output limit reached",
            "diagnostic_ids": [],
        }
        truncated["budget"]["outcome"] = "truncated"
        result.validate_engine_result(truncated, self.schema)

        result.validate_engine_result(self.ambiguous(), self.schema)

        hidden = copy.deepcopy(exhausted)
        hidden["execution"] = {"status": "completed", "diagnostic_ids": []}
        self.assert_invalid(hidden, "outcome")

    def test_disagreement_and_verifier_failure_bind_typed_artifacts(self) -> None:
        disagreement = self.unknown("backend_disagreement")
        self.add_artifact(disagreement, "artifact_disagreement_engine", "disagreement_input")
        self.add_artifact(
            disagreement,
            "artifact_disagreement_checker",
            "disagreement_input",
            producer="component_checker",
        )
        disagreement["execution"] = {
            "status": "disagreement",
            "backend_artifact_ids": [
                "artifact_disagreement_checker",
                "artifact_disagreement_engine",
            ],
            "reason": "backends returned incompatible claims",
            "diagnostic_ids": [],
        }
        self.add_diagnostic(disagreement, severity="error")
        result.validate_engine_result(disagreement, self.schema)

        same = copy.deepcopy(disagreement)
        for artifact in same["artifacts"]:
            if artifact["artifact_id"] == "artifact_disagreement_checker":
                artifact["producer_component_id"] = "component_engine"
        self.assert_invalid(same, "outcome")

        verifier = self.unknown("verifier_failure")
        verifier["execution"] = {
            "status": "verifier_failed",
            "checker_result_artifact_ids": ["artifact_checker_result"],
            "reason": "checker rejected the producer artifact",
            "diagnostic_ids": [],
        }
        self.add_diagnostic(verifier, severity="error")
        result.validate_engine_result(verifier, self.schema)


if __name__ == "__main__":
    unittest.main()
