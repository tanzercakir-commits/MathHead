from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
from types import MappingProxyType
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # dependency-minimal contract profile
    jsonschema = None  # type: ignore[assignment]
    Registry = Resource = None  # type: ignore[assignment,misc]

import mathhead.safe_cache as cache  # noqa: E402
from mathhead.run_audit import RunAuditBundle  # noqa: E402
from mathhead.safe_cache import (  # noqa: E402
    SafeCacheDecision,
    SafeCacheEntry,
    SafeCacheValidationError,
    decide_safe_cache,
    parse_safe_cache_decision,
    parse_safe_cache_entry,
    safe_cache_decision_bytes,
    safe_cache_entry_bytes,
)
from tests.run_audit.fixtures import single_bundle, success_bundle  # noqa: E402


SCHEMAS = ROOT / "docs" / "contracts" / "schemas"


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

    portfolio_request = json.loads(one("portfolio_request"))
    artifacts = tuple(objects[item["sha256"]] for item in portfolio_request["artifact_bindings"])
    descriptors = tuple(objects[item["sha256"]] for item in by_role["plugin_descriptor"])
    bindings = tuple(objects[item["sha256"]] for item in by_role["execution_binding"])
    return (
        one("planning_request"),
        one("capability_route_result"),
        one("portfolio_request"),
        one("planning_result"),
        one("initial_parent_budget"),
        descriptors,
        bindings,
        artifacts,
    )


def validators() -> tuple[object, ...]:
    entry_schema = json.loads((SCHEMAS / "safe-cache-entry-v2.schema.json").read_text())
    decision_schema = json.loads((SCHEMAS / "safe-cache-decision-result-v2.schema.json").read_text())
    request_schema = json.loads((SCHEMAS / "safe-cache-request-v2.schema.json").read_text())
    if jsonschema is None or Registry is None or Resource is None:
        return ()
    registry = Registry().with_resource(
        "https://mathhead.dev/schemas/safe-cache-entry-v2.schema.json",
        Resource.from_contents(entry_schema),
    ).with_resource(
        "safe-cache-entry-v2.schema.json", Resource.from_contents(entry_schema)
    )
    return (
        jsonschema.Draft202012Validator(request_schema, registry=registry),
        jsonschema.Draft202012Validator(entry_schema, registry=registry),
        jsonschema.Draft202012Validator(decision_schema, registry=registry),
    )


class SafeCacheContractTests(unittest.TestCase):
    def test_accepted_contract_schema_hashes_and_signature_are_exact(self) -> None:
        self.assertEqual(
            sha((ROOT / "docs/contracts/MH-C-SAFE-CACHE-002.json").read_bytes()),
            cache.CONTRACT_SHA256,
        )
        expected = {
            "mathhead.safe-cache-request.v2": "safe-cache-request-v2.schema.json",
            "mathhead.safe-cache-entry.v2": "safe-cache-entry-v2.schema.json",
            "mathhead.safe-cache-decision-result.v2": "safe-cache-decision-result-v2.schema.json",
        }
        self.assertEqual(
            {schema: sha((SCHEMAS / name).read_bytes()) for schema, name in expected.items()},
            cache.SCHEMA_SHA256S,
        )
        self.assertEqual(
            str(inspect.signature(decide_safe_cache)),
            "(planning_request: 'bytes', route_result: 'bytes', portfolio_request: 'bytes', planning_result: 'bytes', parent_budget: 'bytes', descriptors: 'tuple[bytes, ...]', bindings: 'tuple[bytes, ...]', artifacts: 'tuple[bytes, ...]', candidate: 'RunAuditBundle | None') -> 'SafeCacheDecision'",
        )
        for validator in validators():
            validator.check_schema(validator.schema)


class SafeCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proved = success_bundle(claim="proved")
        cls.refuted = success_bundle(claim="refuted")
        cls.proved_inputs = cache_inputs(cls.proved)
        cls.refuted_inputs = cache_inputs(cls.refuted)

    def test_absent_candidate_is_one_canonical_miss(self) -> None:
        with mock.patch.object(cache, "replay_run_audit", wraps=cache.replay_run_audit) as replay:
            result = decide_safe_cache(*self.proved_inputs, None)
        self.assertEqual((result.status, result.reason_code), ("miss", "CACHE_CANDIDATE_ABSENT"))
        self.assertIsNotNone(result.lookup_key_sha256)
        self.assertIsNone(result.entry)
        self.assertEqual(replay.call_count, 0)
        self.assertFalse(result.mathematical_authority)
        self.assertEqual(parse_safe_cache_decision(safe_cache_decision_bytes(result)), result)

    def test_proved_and_refuted_runs_are_fresh_single_replay_hits(self) -> None:
        schema_validators = validators()
        for audited, current in ((self.proved, self.proved_inputs), (self.refuted, self.refuted_inputs)):
            miss = decide_safe_cache(*current, None)
            with mock.patch.object(cache, "replay_run_audit", wraps=cache.replay_run_audit) as replay:
                hit = decide_safe_cache(*current, audited.bundle)
            self.assertEqual((hit.status, hit.reason_code), ("hit", "CACHE_HIT"))
            self.assertEqual(replay.call_count, 1)
            self.assertEqual(hit.lookup_key_sha256, miss.lookup_key_sha256)
            self.assertIsNotNone(hit.entry)
            assert hit.entry is not None
            self.assertEqual(parse_safe_cache_entry(safe_cache_entry_bytes(hit.entry)), hit.entry)
            request = cache._current_request(*current)
            request.pop("_strategy_formats")
            if schema_validators:
                request_validator, entry_validator, decision_validator = schema_validators
                request_validator.validate(request)
                entry_validator.validate(json.loads(safe_cache_entry_bytes(hit.entry)))
                decision_validator.validate(json.loads(safe_cache_decision_bytes(hit)))
            self.assertEqual(hit.entry.audit_manifest_sha256, audited.bundle.manifest_sha256)
            manifest = json.loads(audited.bundle.manifest)
            self.assertEqual(
                hit.entry.execution_provenance_sha256,
                manifest["execution_provenance_sha256"],
            )
            self.assertEqual(
                request["expected_execution_provenance_sha256"],
                manifest["execution_provenance_sha256"],
            )
            self.assertFalse(hit.entry.mathematical_authority)

    def test_current_request_is_validated_before_candidate_replay(self) -> None:
        broken = (b"{}\n", *self.proved_inputs[1:])
        with mock.patch.object(cache, "replay_run_audit", wraps=cache.replay_run_audit) as replay:
            result = decide_safe_cache(*broken, self.proved.bundle)
        self.assertEqual(
            (result.status, result.reason_code, result.lookup_key_sha256),
            ("invalid", "CACHE_CURRENT_REQUEST_INVALID", None),
        )
        self.assertEqual(replay.call_count, 0)

    def test_replay_invalid_and_context_mismatch_never_hit(self) -> None:
        forged = object.__new__(RunAuditBundle)
        for name in (
            "manifest", "objects", "logical_report", "manifest_sha256",
            "logical_report_sha256", "mathematical_authority",
        ):
            object.__setattr__(forged, name, getattr(self.proved.bundle, name))
        damaged = self.proved.bundle.manifest[:-2] + b" \n"
        object.__setattr__(forged, "manifest", damaged)
        object.__setattr__(forged, "manifest_sha256", sha(damaged))
        invalid = decide_safe_cache(*self.proved_inputs, forged)
        mismatch = decide_safe_cache(*self.proved_inputs, self.refuted.bundle)
        self.assertEqual((invalid.status, invalid.reason_code), ("invalid", "CACHE_REPLAY_INVALID"))
        self.assertEqual(mismatch.status, "invalid")
        self.assertIn(mismatch.reason_code, {"CACHE_CONTEXT_MISMATCH", "CACHE_ARTIFACT_MISMATCH"})

    def test_closed_non_success_outcomes_are_ineligible(self) -> None:
        for audited in (
            single_bundle(evidence_status="unsupported"),
            success_bundle(agreement=False),
        ):
            result = decide_safe_cache(*cache_inputs(audited), audited.bundle)
            self.assertEqual(
                (result.status, result.reason_code),
                ("ineligible", "CACHE_OUTCOME_INELIGIBLE"),
            )
            self.assertIsNotNone(result.audit_manifest_sha256)
            self.assertIsNone(result.selected_evidence_sha256)

    def test_entry_and_decision_values_are_final_immutable_and_codec_owned(self) -> None:
        hit = decide_safe_cache(*self.proved_inputs, self.proved.bundle)
        assert hit.entry is not None
        for cls in (SafeCacheEntry, SafeCacheDecision):
            with self.assertRaises(PermissionError):
                cls()  # type: ignore[call-arg]
            with self.assertRaises(TypeError):
                type("Derived", (cls,), {})
        with self.assertRaises(FrozenInstanceError):
            hit.status = "miss"  # type: ignore[misc]
        with self.assertRaises((TypeError, PermissionError)):
            replace(hit, status="miss")
        with self.assertRaises(TypeError):
            pickle.dumps(hit)
        for operation in (copy.copy, copy.deepcopy):
            try:
                self.assertIs(operation(hit), hit)
            except TypeError:
                pass

    def test_result_codecs_reject_noncanonical_unknown_duplicate_and_repaired_data(self) -> None:
        hit = decide_safe_cache(*self.proved_inputs, self.proved.bundle)
        raw = safe_cache_decision_bytes(hit)
        value = json.loads(raw)
        value["status"] = "miss"
        value["reason_code"] = "CACHE_CANDIDATE_ABSENT"
        value["decision_sha256"] = None
        value["decision_sha256"] = sha(cache._canonical(value))
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(cache._canonical(value))
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(raw[:-1])
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(raw.replace(b'"schema":', b'"schema":"x","schema2":', 1))
        duplicate = raw.replace(b'"schema":', b'"schema":"x","schema":', 1)
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(duplicate)
        repaired = json.loads(raw)
        repaired["historical_authority_tier"] = "caller_forged_tier"
        repaired["decision_sha256"] = None
        repaired["decision_sha256"] = sha(cache._canonical(repaired))
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(cache._canonical(repaired))
        mismatched = json.loads(raw)
        mismatched["historical_authority_tier"] = (
            "external_proof_assistant"
            if mismatched["historical_authority_tier"] == "checker_attestation"
            else "checker_attestation"
        )
        mismatched["decision_sha256"] = None
        mismatched["decision_sha256"] = sha(cache._canonical(mismatched))
        with self.assertRaises(SafeCacheValidationError):
            parse_safe_cache_decision(cache._canonical(mismatched))

    def test_compiled_identity_inventories_are_closed(self) -> None:
        self.assertEqual((len(cache.CONTRACT_BINDINGS), len(cache.SCHEMA_BINDINGS)), (20, 65))
        self.assertEqual((len(cache.IMPLEMENTATION_BINDINGS), len(cache.CONFIGURATION_BINDINGS)), (5, 5))
        self.assertEqual(cache.TRUST_POLICY_SHA256, cache.CONFIGURATION_BINDINGS["trust_transition_policy"])
        for inventory in (
            cache.SCHEMA_SHA256S,
            cache.CONTRACT_BINDINGS,
            cache.SCHEMA_BINDINGS,
            cache.IMPLEMENTATION_BINDINGS,
            cache.CONFIGURATION_BINDINGS,
        ):
            self.assertTrue(all(type(key) is str and _is_digest(value) for key, value in inventory.items()))
            with self.assertRaises(TypeError):
                inventory[next(iter(inventory))] = "f" * 64  # type: ignore[index]

    def test_every_explicit_input_and_compiled_identity_change_is_non_reusable(self) -> None:
        baseline = decide_safe_cache(*self.proved_inputs, None)
        assert baseline.lookup_key_sha256 is not None
        for index, current in enumerate(self.proved_inputs):
            changed = list(self.proved_inputs)
            changed[index] = () if type(current) is tuple else b"{}\n"
            result = decide_safe_cache(*changed, None)
            self.assertNotEqual(result.status, "hit")
            self.assertTrue(
                result.lookup_key_sha256 is None
                or result.lookup_key_sha256 != baseline.lookup_key_sha256
            )
        for name in (
            "CONTRACT_BINDINGS", "SCHEMA_BINDINGS",
            "IMPLEMENTATION_BINDINGS", "CONFIGURATION_BINDINGS",
        ):
            original = getattr(cache, name)
            changed = dict(original)
            first = next(iter(changed))
            changed[first] = "f" * 64 if changed[first] != "f" * 64 else "e" * 64
            with mock.patch.object(cache, name, MappingProxyType(changed)):
                result = decide_safe_cache(*self.proved_inputs, None)
            self.assertEqual(result.status, "miss")
            self.assertNotEqual(result.lookup_key_sha256, baseline.lookup_key_sha256)

    def test_valid_historical_candidate_cannot_cross_current_identity_change(self) -> None:
        baseline = decide_safe_cache(*self.proved_inputs, self.proved.bundle)
        self.assertEqual(baseline.status, "hit")
        cases = (
            ("CONTRACT_BINDINGS", "CACHE_CONTRACT_MISMATCH"),
            ("SCHEMA_BINDINGS", "CACHE_CONTRACT_MISMATCH"),
            ("IMPLEMENTATION_BINDINGS", "CACHE_IMPLEMENTATION_MISMATCH"),
            ("CONFIGURATION_BINDINGS", "CACHE_CONFIGURATION_MISMATCH"),
        )
        for name, reason in cases:
            original = getattr(cache, name)
            changed = dict(original)
            first = next(iter(changed))
            changed[first] = "f" * 64 if changed[first] != "f" * 64 else "e" * 64
            with self.subTest(inventory=name), mock.patch.object(
                cache,
                name,
                MappingProxyType(changed),
            ):
                result = decide_safe_cache(*self.proved_inputs, self.proved.bundle)
            self.assertEqual((result.status, result.reason_code), ("invalid", reason))
            self.assertNotEqual(result.lookup_key_sha256, baseline.lookup_key_sha256)

    def test_candidate_mismatch_precedence_is_exact(self) -> None:
        contracts = dict(cache.CONTRACT_BINDINGS)
        implementations = dict(cache.IMPLEMENTATION_BINDINGS)
        contracts[next(iter(contracts))] = "f" * 64
        implementations[next(iter(implementations))] = "e" * 64
        with (
            mock.patch.object(cache, "CONTRACT_BINDINGS", MappingProxyType(contracts)),
            mock.patch.object(
                cache,
                "IMPLEMENTATION_BINDINGS",
                MappingProxyType(implementations),
            ),
        ):
            result = decide_safe_cache(*self.proved_inputs, self.refuted.bundle)
        self.assertEqual(
            (result.status, result.reason_code),
            ("invalid", "CACHE_CONTRACT_MISMATCH"),
        )

    def test_lookup_key_is_fresh_process_and_hash_seed_stable(self) -> None:
        outputs: list[dict[str, str]] = []
        for seed in ("1", "4294967295"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            environment["PYTHONPATH"] = os.pathsep.join(
                (str(ROOT / "src"), str(ROOT))
            )
            completed = subprocess.run(
                [sys.executable, str(ROOT / "tests/safe_cache/fresh_process_probe.py")],
                cwd=ROOT, env=environment, check=True, capture_output=True,
                text=True, timeout=30,
            )
            outputs.append(json.loads(completed.stdout))
        self.assertEqual(outputs[0], outputs[1])
        self.assertNotEqual(outputs[0]["proved"], outputs[0]["refuted"])


def _is_digest(value: object) -> bool:
    return type(value) is str and len(value) == 64 and set(value) <= set("0123456789abcdef")


if __name__ == "__main__":
    unittest.main()
