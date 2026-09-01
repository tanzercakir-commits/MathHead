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

from tools import validate_resource_budget_contract as budget  # noqa: E402


class ResourceBudgetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema, cls.schema_raw = budget.load_json(ROOT / budget.SCHEMA_PATH)

    def valid(self) -> dict[str, object]:
        return copy.deepcopy(budget.minimal_resource_budget())

    def event(self, value: dict[str, object], kind: str) -> dict[str, object]:
        return next(event for event in value["events"] if event["kind"] == kind)

    def resequence(self, value: dict[str, object]) -> None:
        for sequence, event in enumerate(value["events"]):
            event["sequence"] = sequence

    def assert_invalid(self, value: dict[str, object], kind: str) -> None:
        with self.assertRaises(budget.ResourceBudgetValidationError) as caught:
            budget.validate_resource_budget(value, self.schema)
        self.assertEqual(caught.exception.kind, kind)

    def cancelled(self) -> dict[str, object]:
        value = self.valid()
        value["events"] = value["events"][:2]
        value["events"].append(
            {
                "event_id": "event_cancel",
                "sequence": 2,
                "kind": "cancel",
                "cancellation_id": "cancellation_user",
                "source": "user",
                "observed_wall_time_us": 1_000,
                "reason": "request withdrawn",
                "extensions": {},
            }
        )
        value["outcome"] = {
            "status": "cancelled",
            "cancellation_id": "cancellation_user",
        }
        return value

    def exhausted(self) -> dict[str, object]:
        value = self.valid()
        value["limits"]["wall_time_us"] = 100
        sample = copy.deepcopy(self.event(value, "sample"))
        sample["event_id"] = "event_sample_overrun"
        sample["sequence"] = 0
        sample["observation"]["wall_time_us"] = 101
        request = budget.zero_limit_vector()
        request["wall_time_us"] = 1
        value["events"] = [
            sample,
            {
                "event_id": "event_exhaust",
                "sequence": 1,
                "kind": "exhaust",
                "exhaustion_id": "exhaustion_wall",
                "dimensions": ["wall_time_us"],
                "requested": request,
                "reason": "deadline reached",
                "extensions": {},
            },
        ]
        value["outcome"] = {
            "status": "exhausted",
            "exhaustion_id": "exhaustion_wall",
        }
        return value

    def truncated(self) -> dict[str, object]:
        value = self.valid()
        value["events"].append(
            {
                "event_id": "event_truncate",
                "sequence": 5,
                "kind": "truncate",
                "truncation_id": "truncation_output",
                "dimension": "output_bytes",
                "subject_id": "result_example",
                "strategy": "prefix",
                "original": 70,
                "retained": 20,
                "omitted": 50,
                "retained_sha256": "2" * 64,
                "extensions": {},
            }
        )
        value["outcome"] = {
            "status": "truncated",
            "truncation_ids": ["truncation_output"],
        }
        return value

    def test_normative_schema_identity_closed_root_and_canonical_roundtrip(self) -> None:
        self.assertEqual(hashlib.sha256(self.schema_raw).hexdigest(), budget.EXPECTED_SCHEMA_SHA256)
        self.assertEqual(set(self.schema["required"]), budget.ROOT_FIELDS)
        self.assertFalse(self.schema["additionalProperties"])
        value = self.valid()
        budget.validate_resource_budget(value, self.schema)
        self.assertEqual(json.loads(budget.canonical_bytes(value)), value)
        self.assertEqual(
            budget.canonical_sha256(value),
            hashlib.sha256(budget.canonical_bytes(value)).hexdigest(),
        )

    def test_unknown_missing_and_malformed_tagged_union_fail(self) -> None:
        unknown = self.valid()
        unknown["unknown"] = True
        self.assert_invalid(unknown, "schema")

        missing = self.valid()
        missing.pop("policy")
        self.assert_invalid(missing, "schema")

        malformed = self.valid()
        self.event(malformed, "charge")["kind"] = "unknown"
        self.assert_invalid(malformed, "schema")

    def test_duplicate_keys_and_noncanonical_file_bytes_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"schema":1,"schema":2}\n', encoding="utf-8")
            with self.assertRaises(budget.ResourceBudgetValidationError) as caught:
                budget.load_json(duplicate)
            self.assertEqual(caught.exception.kind, "schema")

            pretty = Path(directory) / "pretty.json"
            pretty.write_text(json.dumps(self.valid(), indent=2) + "\n", encoding="utf-8")
            with self.assertRaises(budget.ResourceBudgetValidationError) as caught:
                budget.load_json(pretty, require_canonical=True)
            self.assertEqual(caught.exception.kind, "canonical")

            canonical = Path(directory) / "canonical.json"
            canonical.write_bytes(budget.canonical_bytes(self.valid()))
            loaded, raw = budget.load_json(canonical, require_canonical=True)
            self.assertEqual(raw, budget.canonical_bytes(loaded))

    def test_unicode_nul_float_integer_key_and_nesting_budgets_fail(self) -> None:
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
        integer["extensions"] = {"org.mathhead.test": {"count": budget.MAX_JSON_INTEGER + 1}}
        self.assert_invalid(integer, "budget")

        long_key = self.valid()
        long_key["extensions"] = {
            "org.mathhead.test": {"a" * (budget.MAX_STRING_CODEPOINTS + 1): None}
        }
        self.assert_invalid(long_key, "budget")

        nested: object = None
        for _ in range(budget.MAX_CANONICAL_NESTING + 1):
            nested = [nested]
        deep = self.valid()
        deep["extensions"] = {"org.mathhead.test": nested}
        self.assert_invalid(deep, "budget")

        with mock.patch.object(budget, "MAX_CANONICAL_NODES", 1):
            self.assert_invalid(self.valid(), "budget")

        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "oversized.json"
            oversized.write_bytes(b"{}\n")
            with mock.patch.object(budget, "MAX_INPUT_BYTES", 1):
                with self.assertRaises(budget.ResourceBudgetValidationError) as caught:
                    budget.load_json(oversized)
            self.assertEqual(caught.exception.kind, "budget")

    def test_event_sequence_and_global_identity_fail_closed(self) -> None:
        sequence = self.valid()
        sequence["events"][1]["sequence"] = 0
        self.assert_invalid(sequence, "canonical")

        collision = self.valid()
        self.event(collision, "reserve")["lease_id"] = "event_charge"
        self.assert_invalid(collision, "identity")

    def test_child_lineage_binds_parent_allocation_identity(self) -> None:
        value = self.valid()
        value["lineage"] = {
            "kind": "child",
            "parent_budget_id": "budget_parent",
            "parent_lease_id": "lease_parent",
            "allocation_sha256": budget.canonical_sha256(value["limits"]),
        }
        budget.validate_resource_budget(value, self.schema)

        wrong = copy.deepcopy(value)
        wrong["lineage"]["allocation_sha256"] = "0" * 64
        self.assert_invalid(wrong, "lineage")

        self_parent = copy.deepcopy(value)
        self_parent["lineage"]["parent_budget_id"] = value["budget_id"]
        self.assert_invalid(self_parent, "lineage")

    def test_charge_must_be_positive_and_respect_reserved_capacity(self) -> None:
        empty = self.valid()
        self.event(empty, "charge")["delta"] = budget.zero_cumulative_vector()
        self.assert_invalid(empty, "accounting")

        exceeded = self.valid()
        exceeded["limits"]["cpu_time_us"] = 99
        self.assert_invalid(exceeded, "exhaustion")

    def test_samples_are_monotonic_and_observations_are_consistent(self) -> None:
        decreased = self.valid()
        decreased["events"][3]["observation"]["wall_time_us"] = 999
        self.assert_invalid(decreased, "monotonic")

        retained = self.valid()
        retained["events"][3]["observation"]["memory_retained_bytes"] = 501
        self.assert_invalid(retained, "accounting")

        nesting = self.valid()
        nesting["events"][3]["observation"]["nesting_current"] = 4
        self.assert_invalid(nesting, "accounting")

    def test_reservations_bind_identity_availability_and_active_ceiling(self) -> None:
        identity = self.valid()
        self.event(identity, "reserve")["allocation_sha256"] = "0" * 64
        self.assert_invalid(identity, "identity")

        unavailable = self.valid()
        reserve = self.event(unavailable, "reserve")
        reserve["allocation"]["wall_time_us"] = unavailable["limits"]["wall_time_us"]
        reserve["allocation_sha256"] = budget.canonical_sha256(reserve["allocation"])
        self.assert_invalid(unavailable, "lease")

        with mock.patch.object(budget, "MAX_ACTIVE_LEASES", 0):
            self.assert_invalid(self.valid(), "budget")

    def test_reconciliation_requires_exact_conservation(self) -> None:
        value = self.valid()
        self.event(value, "reconcile")["refund"]["cpu_time_us"] += 1
        self.assert_invalid(value, "conservation")

        both = self.valid()
        reconcile = self.event(both, "reconcile")
        reconcile["refund"]["cpu_time_us"] += 1
        reconcile["overrun"]["cpu_time_us"] = 1
        self.assert_invalid(both, "conservation")

    def test_child_overrun_requires_exhausted_child_outcome(self) -> None:
        value = self.valid()
        reconcile = self.event(value, "reconcile")
        allocation = self.event(value, "reserve")["allocation"]
        reconcile["child_usage"]["cpu_time_us"] = allocation["cpu_time_us"] + 1
        reconcile["refund"]["cpu_time_us"] = 0
        reconcile["overrun"]["cpu_time_us"] = 1
        self.assert_invalid(value, "outcome")

        reconcile["child_outcome"] = "exhausted"
        budget.validate_resource_budget(value, self.schema)

    def test_parent_observations_cover_child_wall_memory_and_nesting(self) -> None:
        wall = self.valid()
        wall["events"][3]["observation"]["wall_time_us"] = 3_999
        self.assert_invalid(wall, "observation")

        memory = self.valid()
        memory["events"][3]["observation"]["memory_peak_bytes"] = 299
        self.assert_invalid(memory, "observation")

        nesting = self.valid()
        nesting["events"][3]["observation"]["nesting_peak"] = 2
        self.assert_invalid(nesting, "observation")

    def test_lease_cannot_be_reconciled_or_refunded_twice(self) -> None:
        value = self.valid()
        duplicate = copy.deepcopy(self.event(value, "reconcile"))
        duplicate["event_id"] = "event_reconcile_again"
        duplicate["sequence"] = 5
        value["events"].append(duplicate)
        self.assert_invalid(value, "lease")

    def test_cancellation_binds_latest_sample_and_is_terminal(self) -> None:
        value = self.cancelled()
        budget.validate_resource_budget(value, self.schema)

        stale = self.cancelled()
        self.event(stale, "cancel")["observed_wall_time_us"] = 999
        self.assert_invalid(stale, "cancellation")

        active = self.valid()
        active["events"] = active["events"][:3] + [copy.deepcopy(value["events"][-1])]
        self.resequence(active)
        active["outcome"] = copy.deepcopy(value["outcome"])
        self.assert_invalid(active, "cancellation")

        trailing = self.cancelled()
        extra = copy.deepcopy(trailing["events"][0])
        extra["event_id"] = "event_after_cancel"
        trailing["events"].append(extra)
        self.resequence(trailing)
        self.assert_invalid(trailing, "outcome")

    def test_exhaustion_dimensions_match_exact_unavailable_set(self) -> None:
        value = self.exhausted()
        budget.validate_resource_budget(value, self.schema)

        missing = self.exhausted()
        self.event(missing, "exhaust")["dimensions"] = ["cpu_time_us"]
        self.assert_invalid(missing, "exhaustion")

        zero = self.exhausted()
        self.event(zero, "exhaust")["requested"] = budget.zero_limit_vector()
        self.assert_invalid(zero, "exhaustion")

    def test_observed_overrun_requires_immediate_exhaustion(self) -> None:
        value = self.exhausted()
        value["events"].insert(1, copy.deepcopy(value["events"][0]))
        value["events"][1]["event_id"] = "event_too_late"
        self.resequence(value)
        self.assert_invalid(value, "exhaustion")

    def test_truncation_conserves_counts_binds_hash_and_is_not_success(self) -> None:
        value = self.truncated()
        budget.validate_resource_budget(value, self.schema)

        count = self.truncated()
        self.event(count, "truncate")["original"] = 71
        self.assert_invalid(count, "conservation")

        uncharged = self.truncated()
        truncate = self.event(uncharged, "truncate")
        truncate.update({"original": 1_050, "retained": 1_000, "omitted": 50})
        self.assert_invalid(uncharged, "truncation")

        hidden = self.truncated()
        hidden["outcome"] = {"status": "completed"}
        self.assert_invalid(hidden, "outcome")

    def test_refusal_and_terminal_outcome_references_fail_closed(self) -> None:
        refused = self.truncated()
        event = self.event(refused, "truncate")
        event.update({"strategy": "refuse", "retained": 0, "omitted": 70})
        event["retained_sha256"] = None
        budget.validate_resource_budget(refused, self.schema)

        malformed = self.truncated()
        event = self.event(malformed, "truncate")
        event["strategy"] = "refuse"
        self.assert_invalid(malformed, "truncation")

        reference = self.cancelled()
        reference["outcome"]["cancellation_id"] = "cancellation_other"
        self.assert_invalid(reference, "outcome")


if __name__ == "__main__":
    unittest.main()
