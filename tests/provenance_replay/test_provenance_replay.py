from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from mathhead.kernel.checkers import check_proof_term, checker_result_to_bytes  # noqa: E402
from mathhead.kernel.proof_terms import proof_term_to_bytes, residue  # noqa: E402
from mathhead.kernel.provenance import (  # noqa: E402
    MAX_MANIFEST_BYTES,
    PROVENANCE_REPLAY_CONTRACT_SHA256,
    ProvenanceReplayResult,
    canonical_provenance_manifest_bytes,
    checker_configuration_bytes,
    parse_provenance_replay_result,
    provenance_replay_result_sha256,
    provenance_replay_result_to_bytes,
    replay_provenance_bundle,
)
from mathhead.kernel.sat import (  # noqa: E402
    canonical_cnf_bytes,
    canonical_sat_assignment_bytes,
    check_sat_certificate,
    sat_replay_result_to_bytes,
)
from mathhead.provenance_store import (  # noqa: E402
    ProvenanceStoreError,
    load_replay_bundle,
    persist_replay_bundle,
)


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("ascii")


FOUNDATION = {
    "certificate": (
        "mathhead.certificate.v1",
        "MH-C-CERTIFICATE-001",
        "0a21aca8058fb5fc9900decb6dcd14e179c7a5171f7653ea965b5d34edd59740",
    ),
    "engine_result": (
        "mathhead.engine-result.v1",
        "MH-C-ENGINE-RESULT-001",
        "6c57ba36c78a2e15b27d3e464342b890f71b2d298f6395c7f4b0cd5aa5a09370",
    ),
    "evidence": (
        "mathhead.evidence.v1",
        "MH-C-EVIDENCE-001",
        "c68c20ca599cfdd7aabe9b85f2817c6c3f1a121289334136ff048768ee20c3b3",
    ),
    "problem_ir": (
        "mathhead.problem-ir.v1",
        "MH-C-PROBLEM-IR-002",
        "6d657195869a5746c5a41492c334b32ee5edd2ca84eb7facfade44f53334c286",
    ),
    "resource_budget": (
        "mathhead.resource-budget.v1",
        "MH-C-RESOURCE-BUDGET-001",
        "eef46d8e6d37ada50fb9af1ab6a1db5665070896f83c5d9155fc6ee2777f5045",
    ),
    "theory_context": (
        "mathhead.theory-context.v1",
        "MH-C-THEORY-CONTEXT-001",
        "d2cb0e61c33327a6c2d5887872278179b5e11e42b6358b1661b60386e60e888d",
    ),
    "theory_plugin": (
        "mathhead.theory-plugin.v1",
        "MH-C-THEORY-PLUGIN-001",
        "2226973b172a3b2ce489aae3baae7820c3b7b57ab76cff089927f68a2759a8e8",
    ),
}
CHECKERS = {
    "mathhead.kernel.checker.v2": {
        "contract_id": "MH-C-KERNEL-CHECKER-002",
        "contract_sha256": "1baf3b44734369fdb298609ad0230062686697a7198401d6fc53f161c70a678e",
        "implementation": ROOT / "src/mathhead/kernel/checkers.py",
        "result_schema": "mathhead.kernel-checker-result.v2",
    },
    "mathhead.kernel.sat-replay.v1": {
        "contract_id": "MH-C-SAT-REPLAY-001",
        "contract_sha256": "0bf4edbba9285070ef525ae584124ae4fab2762ce83a42f2434c18c8db6f2b50",
        "implementation": ROOT / "src/mathhead/kernel/sat.py",
        "result_schema": "mathhead.sat-replay-result.v1",
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dependencies(role: str, roles: set[str]) -> list[str]:
    foundation = ["problem_ir", "resource_budget", "theory_context", "theory_plugin"]
    inputs = [name for name in ("proof_term", "cnf", "sat_certificate") if name in roles]
    if role in {"problem_ir", "resource_budget", "theory_plugin", "checker_contract"}:
        return []
    if role == "theory_context":
        return ["problem_ir"]
    if role in {"proof_term", "cnf"}:
        return ["problem_ir", "theory_context"]
    if role == "sat_certificate":
        return ["cnf"]
    if role == "evidence":
        return foundation
    if role == "certificate":
        return [*foundation, "evidence", *inputs]
    if role == "engine_result":
        return [*foundation, "evidence", "certificate"]
    if role == "checker_implementation":
        return ["checker_contract"]
    if role == "checker_configuration":
        return ["checker_contract", "checker_implementation"]
    if role == "checker_result":
        return sorted(roles - {"checker_result"})
    raise AssertionError(role)


def _bundle(
    checker_id: str = "mathhead.kernel.checker.v2",
    *,
    sat_outcome: str = "verified",
    evidence_padding: int = 0,
) -> tuple[bytes, tuple[bytes, ...]]:
    checker = CHECKERS[checker_id]
    values = {
        role: _canonical({"schema": schema})
        for role, (schema, _contract, _sha256) in FOUNDATION.items()
    }
    values["theory_plugin"] = _canonical(
        {
            "plugin_id": "org.mathhead.test-plugin",
            "plugin_version": "1.2.3",
            "schema": "mathhead.theory-plugin.v1",
        }
    )
    if evidence_padding:
        padding = {
            f"padding_{index:03d}": "x" * min(1_000_000, evidence_padding - index * 1_000_000)
            for index in range((evidence_padding + 999_999) // 1_000_000)
        }
        values["evidence"] = _canonical({"extensions": padding, "schema": "mathhead.evidence.v1"})
    contract_id = checker["contract_id"]
    contract_sha = checker["contract_sha256"]
    values["checker_contract"] = (ROOT / f"docs/contracts/{contract_id}.json").read_bytes()
    values["checker_implementation"] = checker["implementation"].read_bytes()
    values["checker_configuration"] = checker_configuration_bytes(checker_id)
    if checker_id == "mathhead.kernel.checker.v2":
        term = residue(2, (0, -1, 0, 1))
        values["proof_term"] = proof_term_to_bytes(term)
        values["checker_result"] = checker_result_to_bytes(check_proof_term(term))
    else:
        cnf = canonical_cnf_bytes(((1,),))
        if sat_outcome == "verified":
            certificate = canonical_sat_assignment_bytes(cnf, (1,))
        elif sat_outcome == "refuted":
            certificate = canonical_sat_assignment_bytes(cnf, (-1,))
        elif sat_outcome == "unsupported":
            certificate = f"p mathhead-drat 1 {_sha(cnf)}\n".encode("ascii")
        else:
            raise AssertionError(sat_outcome)
        values["cnf"] = cnf
        values["sat_certificate"] = certificate
        values["checker_result"] = sat_replay_result_to_bytes(
            check_sat_certificate(cnf, certificate)
        )
    roles = set(values)
    records = []
    for role in sorted(roles):
        data = values[role]
        if role in FOUNDATION:
            schema, role_contract, role_contract_sha = FOUNDATION[role]
            media = "application/json"
        elif role == "checker_contract":
            schema, role_contract, role_contract_sha = (
                "mathhead.function-contract.v1",
                contract_id,
                contract_sha,
            )
            media = "application/json"
        elif role == "checker_implementation":
            schema, role_contract, role_contract_sha = None, contract_id, contract_sha
            media = "text/x-python"
        elif role == "checker_configuration":
            schema, role_contract, role_contract_sha = (
                "mathhead.checker-configuration.v1",
                contract_id,
                contract_sha,
            )
            media = "application/json"
        elif role == "checker_result":
            schema, role_contract, role_contract_sha = (
                checker["result_schema"],
                contract_id,
                contract_sha,
            )
            media = "application/json"
        elif role == "proof_term":
            schema, role_contract, role_contract_sha = (
                "mathhead.proof-term.v1",
                "MH-C-PROOF-TERM-001",
                "20c501b77e370c4258523a291e83b15a99ed6308e002d9a54d0abc3bb18199ac",
            )
            media = "application/json"
        elif role == "cnf":
            schema, role_contract, role_contract_sha = "mathhead.cnf.v1", contract_id, contract_sha
            media = "application/octet-stream"
        else:
            schema, role_contract, role_contract_sha = (
                "mathhead.sat-certificate.v1",
                contract_id,
                contract_sha,
            )
            media = "application/octet-stream"
        records.append(
            {
                "byte_count": len(data),
                "contract_id": role_contract,
                "contract_sha256": role_contract_sha,
                "depends_on_sha256": sorted(
                    _sha(values[name]) for name in _dependencies(role, roles)
                ),
                "media_type": media,
                "role": role,
                "schema": schema,
                "sha256": _sha(data),
            }
        )
    manifest = canonical_provenance_manifest_bytes(
        {
            "objects": records,
            "plugin": {
                "plugin_id": "org.mathhead.test-plugin",
                "plugin_version": "1.2.3",
            },
            "replay": {
                "checker_configuration_sha256": _sha(values["checker_configuration"]),
                "checker_contract_id": contract_id,
                "checker_contract_sha256": contract_sha,
                "checker_id": checker_id,
                "checker_implementation_sha256": _sha(values["checker_implementation"]),
                "recorded_result_sha256": _sha(values["checker_result"]),
            },
            "schema": "mathhead.provenance-manifest.v1",
        }
    )
    return manifest, tuple(values[record["role"]] for record in records)


def _replace_object(
    manifest: bytes,
    objects: tuple[bytes, ...],
    role: str,
    replacement: bytes,
) -> tuple[bytes, tuple[bytes, ...]]:
    value = json.loads(manifest)
    index = next(index for index, record in enumerate(value["objects"]) if record["role"] == role)
    previous = value["objects"][index]["sha256"]
    current = _sha(replacement)
    value["objects"][index]["sha256"] = current
    value["objects"][index]["byte_count"] = len(replacement)
    for record in value["objects"]:
        record["depends_on_sha256"] = sorted(
            current if dependency == previous else dependency
            for dependency in record["depends_on_sha256"]
        )
    replay_field = {
        "checker_configuration": "checker_configuration_sha256",
        "checker_contract": "checker_contract_sha256",
        "checker_implementation": "checker_implementation_sha256",
        "checker_result": "recorded_result_sha256",
    }.get(role)
    if replay_field is not None:
        value["replay"][replay_field] = current
    changed = list(objects)
    changed[index] = replacement
    return _canonical(value), tuple(changed)


class ProvenanceReplayTests(unittest.TestCase):
    def test_proof_bundle_replays_and_round_trips_exactly(self) -> None:
        manifest, objects = _bundle()
        result = replay_provenance_bundle(manifest, objects)
        self.assertEqual(result.verdict, "verified")
        self.assertEqual(result.authority, "checker_attestation")
        self.assertTrue(result.bundle_complete)
        self.assertEqual(result.bundle_sha256, _sha(manifest))
        encoded = provenance_replay_result_to_bytes(result)
        self.assertEqual(parse_provenance_replay_result(encoded, manifest, objects), result)
        self.assertEqual(provenance_replay_result_sha256(result), _sha(encoded))
        self.assertEqual(
            PROVENANCE_REPLAY_CONTRACT_SHA256,
            "31a664252096b47a10dfe14d999a5fe7bf278612fdebd003c3982123a0bcdb67",
        )

    def test_sat_bundle_uses_the_same_complete_boundary(self) -> None:
        manifest, objects = _bundle("mathhead.kernel.sat-replay.v1")
        result = replay_provenance_bundle(manifest, objects)
        self.assertEqual((result.verdict, result.authority), ("verified", "checker_attestation"))
        self.assertEqual(result.object_count, 13)

    def test_non_authoritative_checker_outcomes_remain_complete_but_never_promote(self) -> None:
        for outcome in ("refuted", "unsupported"):
            manifest, objects = _bundle("mathhead.kernel.sat-replay.v1", sat_outcome=outcome)
            result = replay_provenance_bundle(manifest, objects)
            self.assertEqual(result.verdict, outcome)
            self.assertEqual(result.checker_verdict, outcome)
            self.assertTrue(result.bundle_complete)
            self.assertEqual(result.authority, "none")

    def test_wrong_types_noncanonical_and_budget_fail_closed(self) -> None:
        manifest, objects = _bundle()
        self.assertEqual(
            replay_provenance_bundle(bytearray(manifest), objects).reason_code, "TYPE_INVALID"
        )  # type: ignore[arg-type]
        self.assertEqual(
            replay_provenance_bundle(manifest, list(objects)).reason_code, "TYPE_INVALID"
        )  # type: ignore[arg-type]
        noncanonical = json.dumps(json.loads(manifest), indent=2).encode()
        self.assertEqual(
            replay_provenance_bundle(noncanonical, objects).reason_code, "NONCANONICAL"
        )
        huge = b"{" + b" " * MAX_MANIFEST_BYTES + b"}"
        self.assertEqual(replay_provenance_bundle(huge, objects).verdict, "exhausted")
        bad_item = replay_provenance_bundle(manifest, (*objects[:-1], bytearray(objects[-1])))  # type: ignore[arg-type]
        self.assertEqual(bad_item.reason_code, "TYPE_INVALID")
        self.assertEqual(
            parse_provenance_replay_result(provenance_replay_result_to_bytes(bad_item), None, None),  # type: ignore[arg-type]
            bad_item,
        )

    def test_duplicate_keys_numbers_unicode_and_unknown_fields_fail_closed(self) -> None:
        manifest, objects = _bundle()
        value = json.loads(manifest)
        cases = [
            manifest[:-2] + b',"schema":"mathhead.provenance-manifest.v1"}\n',
            manifest.replace(b'"plugin_version":"1.2.3"', b'"plugin_version":1.2'),
            _canonical({**value, "unknown": None}),
        ]
        nul = copy.deepcopy(value)
        nul["plugin"]["plugin_id"] = "org.mathhead.\x00plugin"
        cases.append(_canonical(nul))
        non_nfc = copy.deepcopy(value)
        non_nfc["plugin"]["plugin_id"] = "org.mathhead.e\u0301"
        cases.append(_canonical(non_nfc))
        for data in cases:
            result = replay_provenance_bundle(data, objects)
            self.assertEqual(result.authority, "none")
            self.assertIn(result.verdict, {"invalid", "exhausted"})

    def test_every_object_and_record_identity_is_necessary(self) -> None:
        manifest, objects = _bundle()
        for index in range(len(objects)):
            mutated = list(objects)
            mutated[index] = mutated[index][:-1] + bytes([mutated[index][-1] ^ 1])
            result = replay_provenance_bundle(manifest, tuple(mutated))
            self.assertEqual(result.verdict, "invalid", index)
            self.assertEqual(result.authority, "none", index)
        self.assertEqual(
            replay_provenance_bundle(manifest, objects[:-1]).reason_code, "INVENTORY_MISMATCH"
        )
        self.assertEqual(
            replay_provenance_bundle(manifest, (*objects, b"extra")).verdict, "invalid"
        )

    def test_manifest_role_dependency_plugin_and_replay_drift_fail(self) -> None:
        manifest, objects = _bundle()
        base = json.loads(manifest)
        mutations = []
        wrong_plugin = copy.deepcopy(base)
        wrong_plugin["plugin"]["plugin_version"] = "1.2.4"
        mutations.append(wrong_plugin)
        wrong_dependency = copy.deepcopy(base)
        next(
            record for record in wrong_dependency["objects"] if record["role"] == "checker_result"
        )["depends_on_sha256"] = []
        mutations.append(wrong_dependency)
        wrong_result = copy.deepcopy(base)
        wrong_result["replay"]["recorded_result_sha256"] = "0" * 64
        mutations.append(wrong_result)
        reversed_records = copy.deepcopy(base)
        reversed_records["objects"] = list(reversed(reversed_records["objects"]))
        mutations.append(reversed_records)
        for value in mutations:
            result = replay_provenance_bundle(_canonical(value), objects)
            self.assertEqual(result.verdict, "invalid")
            self.assertEqual(result.authority, "none")

    def test_recorded_checker_result_cannot_self_attest(self) -> None:
        manifest, objects = _bundle()
        value = json.loads(manifest)
        result_index = next(
            index
            for index, record in enumerate(value["objects"])
            if record["role"] == "checker_result"
        )
        forged_objects = list(objects)
        forged = json.loads(forged_objects[result_index])
        forged["result"]["diagnostic"] = "stored verdict says true"
        forged_objects[result_index] = _canonical(forged)
        record = value["objects"][result_index]
        record["byte_count"] = len(forged_objects[result_index])
        record["sha256"] = _sha(forged_objects[result_index])
        value["replay"]["recorded_result_sha256"] = record["sha256"]
        checker_result_digest = record["sha256"]
        for item in value["objects"]:
            if item["role"] != "checker_result":
                item["depends_on_sha256"] = [
                    checker_result_digest if digest == _sha(objects[result_index]) else digest
                    for digest in item["depends_on_sha256"]
                ]
                item["depends_on_sha256"].sort()
        result = replay_provenance_bundle(_canonical(value), tuple(forged_objects))
        self.assertEqual(result.reason_code, "CHECKER_RESULT_MISMATCH")
        self.assertEqual(result.authority, "none")

    def test_repaired_hashes_cannot_swap_checker_contract_source_or_configuration(self) -> None:
        manifest, objects = _bundle()
        replacements = {
            "checker_contract": _canonical(
                {
                    "contract_id": "MH-C-KERNEL-CHECKER-002",
                    "schema": "mathhead.function-contract.v1",
                }
            ),
            "checker_implementation": b"# forged checker implementation\n",
            "checker_configuration": _canonical(
                {
                    "checker_contract_id": "MH-C-KERNEL-CHECKER-002",
                    "checker_contract_sha256": CHECKERS["mathhead.kernel.checker.v2"][
                        "contract_sha256"
                    ],
                    "checker_id": "mathhead.kernel.checker.v2",
                    "implementation_sha256": "0" * 64,
                    "schema": "mathhead.checker-configuration.v1",
                }
            ),
        }
        for role, replacement in replacements.items():
            changed_manifest, changed_objects = _replace_object(
                manifest, objects, role, replacement
            )
            result = replay_provenance_bundle(changed_manifest, changed_objects)
            self.assertEqual(result.verdict, "invalid", role)
            self.assertEqual(result.authority, "none", role)

    def test_results_are_closed_immutable_and_not_pickle_authority(self) -> None:
        manifest, objects = _bundle()
        result = replay_provenance_bundle(manifest, objects)
        with self.assertRaises(PermissionError):
            ProvenanceReplayResult()  # type: ignore[call-arg]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.authority = "none"  # type: ignore[misc]
        with self.assertRaises(TypeError):
            pickle.dumps(result)
        self.assertIs(copy.copy(result), result)
        self.assertIs(copy.deepcopy(result), result)
        with self.assertRaises(TypeError):

            class Forged(ProvenanceReplayResult):
                pass

    def test_store_is_atomic_immutable_and_freshly_replayed(self) -> None:
        manifest, objects = _bundle()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "store"
            identity = persist_replay_bundle(root, manifest, objects)
            self.assertEqual(identity, _sha(manifest))
            self.assertEqual(persist_replay_bundle(root, manifest, objects), identity)
            loaded = load_replay_bundle(root, identity)
            self.assertEqual(loaded, replay_provenance_bundle(manifest, objects))
            manifest_path = root / "bundles" / identity[:2] / identity[2:] / "manifest.json"
            self.assertEqual(stat_mode(manifest_path), 0o444)
            object_digest = _sha(objects[0])
            object_path = root / "objects" / object_digest[:2] / object_digest[2:]
            os.chmod(object_path, 0o644)
            with self.assertRaises(ProvenanceStoreError):
                load_replay_bundle(root, identity)

    def test_store_handles_large_streamed_objects_and_refuses_partial_commit(self) -> None:
        manifest, objects = _bundle(evidence_padding=2_000_000)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "store"
            identity = persist_replay_bundle(root, manifest, objects)
            self.assertEqual(load_replay_bundle(root, identity).verdict, "verified")
            missing = "0" * 64
            before = sorted(path.relative_to(root) for path in root.rglob("*"))
            with self.assertRaises(ProvenanceStoreError):
                load_replay_bundle(root, missing)
            after = sorted(path.relative_to(root) for path in root.rglob("*"))
            self.assertEqual(after, before)

    def test_store_preserves_complete_refutation_without_upgrading_it(self) -> None:
        manifest, objects = _bundle("mathhead.kernel.sat-replay.v1", sat_outcome="refuted")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "store"
            identity = persist_replay_bundle(root, manifest, objects)
            result = load_replay_bundle(root, identity)
            self.assertEqual((result.verdict, result.authority), ("refuted", "none"))

    def test_store_rejects_symlink_and_hardlink_state(self) -> None:
        manifest, objects = _bundle()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "target"
            target.mkdir()
            link = base / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                pass  # The host filesystem does not grant symlink creation.
            else:
                with self.assertRaises(ProvenanceStoreError):
                    persist_replay_bundle(link, manifest, objects)
                nested_identity = persist_replay_bundle(link / "store", manifest, objects)
                self.assertEqual(nested_identity, _sha(manifest))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "store"
            identity = persist_replay_bundle(root, manifest, objects)
            digest = _sha(objects[0])
            object_path = root / "objects" / digest[:2] / digest[2:]
            os.link(object_path, root / "duplicate-link")
            with self.assertRaises(ProvenanceStoreError):
                load_replay_bundle(root, identity)


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


if __name__ == "__main__":
    unittest.main()
