#!/usr/bin/env python3
"""Independently validate the MH-054 audited-run and replay boundaries.

The validator process deliberately never imports :mod:`mathhead.run_audit`.
Fresh bundles are produced in isolated child processes, then this process
reconstructs their canonical identities, object closure, event chain, stable
logical projection, and hostile-input rejection from bytes alone.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any, NoReturn
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/run_audit.py"
REPORT = ROOT / "docs/planning/reports/run-audit-v1.json"
AUDIT_CONTRACT = "MH-C-AUDITED-RUN-001"
AUDIT_SHA256 = "6032b9efac0c1ffa93cc2ee738318f45d8331c8ee25f4d97b51b55ba8aff8c0a"
REPLAY_CONTRACT = "MH-C-RUN-AUDIT-REPLAY-001"
REPLAY_SHA256 = "ed130e9099a4308ed2c911e9ad63d2450783d9bff9700ad6ac0e2dd22ede9bc5"
SCHEMAS = {
    "run-audit-object-v1.schema.json": "03797f8c040c27286fb9bff2a988a7106e3fc6956e9203c90a81714cf8e98f60",
    "run-audit-event-v1.schema.json": "6c1ef20c692220b9c1970620eac220e3a8a1ff3c23148a60a05e9d76b4045ecb",
    "run-audit-manifest-v1.schema.json": "53c4f799ca8a523e01a518069aa1c27483bd9c2f95132281ebdb93fa0c7bd950",
    "run-logical-report-v1.schema.json": "2db8b0e75d274817201314e853bfe10ed5a6910bf8b6fa74549c1bb30eccbc76",
    "run-audit-replay-result-v1.schema.json": "c60e67b31da35441692ea88caeb09780755be092946d1aa4486dcbd748aad500",
}
REPORT_SCHEMA = "mathhead.run-audit-validation-report.v1"
MANIFEST_SCHEMA = "mathhead.run-audit-manifest.v1"
OBJECT_SCHEMA = "mathhead.run-audit-object.v1"
EVENT_SCHEMA = "mathhead.run-audit-event.v1"
LOGICAL_SCHEMA = "mathhead.run-logical-report.v1"
DIGEST = re.compile(r"[0-9a-f]{64}")
REASON = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
MAX_OBJECTS = 200_000
MAX_EVENTS = 1_000_000
FORBIDDEN_MARKERS = (
    b"MH054_ENV_SECRET_DO_NOT_RECORD",
    b"mh054-machine-path-do-not-record",
    b"workspace_root",
    b"executable_paths",
    b"PYTHONHASHSEED",
)


class AuditValidationError(RuntimeError):
    """An independent contract, identity, closure, or replay check failed."""


class _DuplicateKey(ValueError):
    pass


def _fail(detail: str) -> NoReturn:
    raise AuditValidationError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("ascii")


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _walk(value: object, *, depth: int = 0) -> None:
    if depth > 128:
        _fail("canonical value nesting exceeds the accepted bound")
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > 9_007_199_254_740_991:
            _fail("canonical integer exceeds the accepted bound")
        return
    if type(value) is str:
        if "\x00" in value or unicodedata.normalize("NFC", value) != value:
            _fail("canonical string is NUL-bearing or non-NFC")
        return
    if type(value) is list:
        for item in value:
            _walk(item, depth=depth + 1)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                _fail("canonical object key is not an exact string")
            _walk(key, depth=depth + 1)
            _walk(item, depth=depth + 1)
        return
    _fail("canonical value has a forbidden type")


def _parse(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_float=lambda _value: (_ for _ in ()).throw(ValueError("float")),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                ValueError("constant")
            ),
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        _fail(f"{label} is not strict JSON: {type(exc).__name__}")
    if type(value) is not dict:
        _fail(f"{label} root is not an object")
    _walk(value)
    if raw != _canonical(value):
        _fail(f"{label} is not canonical")
    return value


def _digest(value: object, label: str) -> str:
    if type(value) is not str or DIGEST.fullmatch(value) is None:
        _fail(f"{label} is not a full lowercase SHA-256")
    return value


def _self_hash(value: dict[str, Any], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _exact_fields(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        _fail(f"{label} field set differs")


def _contract_checks() -> dict[str, object]:
    accepted: dict[str, str] = {}
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text())
    for entry in manifest.get("contracts", []):
        if entry.get("state") == "accepted":
            accepted[str(entry["id"])] = str(entry["sha256"])
    for contract_id, digest in (
        (AUDIT_CONTRACT, AUDIT_SHA256),
        (REPLAY_CONTRACT, REPLAY_SHA256),
    ):
        path = ROOT / "docs/contracts" / f"{contract_id}.json"
        proposed = ROOT / "docs/contracts/proposed" / f"{contract_id}.json"
        raw = path.read_bytes()
        if (
            _sha(raw) != digest
            or raw != proposed.read_bytes()
            or raw != _canonical(json.loads(raw))
            or accepted.get(contract_id) != digest
        ):
            _fail(f"accepted contract binding drift: {contract_id}")
    schema_report: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        raw = path.read_bytes()
        try:
            schema = json.loads(raw, object_pairs_hook=_pairs)
        except (UnicodeError, ValueError, RecursionError) as exc:
            _fail(f"schema is not strict JSON: {name}: {type(exc).__name__}")
        if (
            _sha(raw) != digest
            or type(schema) is not dict
            or schema.get("$schema")
            != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or set(schema.get("required", [])) != set(schema.get("properties", {}))
        ):
            _fail(f"closed schema binding drift: {name}")
        schema_report[name] = digest
    return {
        "accepted_contracts": [AUDIT_CONTRACT, REPLAY_CONTRACT],
        "schemas": schema_report,
    }


def _source_checks() -> dict[str, object]:
    source = SOURCE.read_text()
    tree = ast.parse(source)
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    signatures = {
        "execute_audited_run": [
            "planning_request",
            "route_result",
            "portfolio_request",
            "planning_result",
            "parent_budget",
            "descriptors",
            "bindings",
            "artifacts",
            "executable_paths",
            "workspace_root",
            "cancel_event",
        ],
        "replay_run_audit": ["manifest", "objects"],
    }
    for name, parameters in signatures.items():
        node = functions.get(name)
        if node is None or [item.arg for item in node.args.args] != parameters:
            _fail(f"public signature drift: {name}")
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    if imports & {"os", "pathlib", "subprocess", "time", "random", "secrets"}:
        _fail("audit module gained an ambient path, process, clock, or entropy import")
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if calls & {"open", "eval", "exec", "__import__", "getenv"}:
        _fail("audit module gained a forbidden ambient or dynamic call")
    replay_node = functions["replay_run_audit"]
    replay_calls = {
        node.func.id
        for node in ast.walk(replay_node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if replay_calls & {"_run_portfolio_audited", "supervise_worker", "Popen", "run"}:
        _fail("logical replay gained an execution call")
    return {
        "path": "src/mathhead/run_audit.py",
        "sha256": _sha(SOURCE.read_bytes()),
        "imports": sorted(imports),
    }


_CHILD = r'''import base64, json, os, tempfile
from pathlib import Path
from mathhead.proof_search_portfolio import make_proof_search_portfolio_request
from mathhead.run_audit import execute_audited_run, replay_run_audit, run_audit_replay_result_bytes
from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture, PortfolioFixture

def enc(value):
    return base64.b64encode(value).decode("ascii")

def execute(fixture, fallback=False):
    descriptors = fixture.descriptors if fallback else (fixture.descriptor,)
    bindings = fixture.bindings if fallback else (fixture.binding,)
    planning_request, route_result, _, artifacts = fixture.base.planning_inputs(
        descriptors, availability_changes={"allowed_effects": ("process",)}
    )
    portfolio_request = fixture.request
    if fallback:
        portfolio_request = make_proof_search_portfolio_request(
            planning_result=fixture.plan_bytes,
            parent_budget=fixture.parent,
            descriptors=descriptors,
            bindings=bindings,
            artifacts=fixture.input_pairs,
        )
    with tempfile.TemporaryDirectory(prefix="mh054-machine-path-do-not-record-") as workspace:
        bundle = execute_audited_run(
            planning_request, route_result, portfolio_request, fixture.plan_bytes,
            fixture.parent, descriptors, bindings, artifacts,
            fixture.executable_paths, workspace,
        )
    replay = replay_run_audit(bundle.manifest, bundle.objects)
    return {
        "manifest": enc(bundle.manifest),
        "objects": [enc(item) for item in bundle.objects],
        "logical_report": enc(bundle.logical_report),
        "replay": enc(run_audit_replay_result_bytes(replay)),
    }

os.environ["MATHHEAD_AUDIT_SENTINEL"] = "MH054_ENV_SECRET_DO_NOT_RECORD"
print(json.dumps({
    "success": execute(PortfolioFixture()),
    "fallback": execute(FallbackPortfolioFixture(), True),
}, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
'''


def _runtime_sample(seed: str) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    roots = (str(ROOT / "src"), str(ROOT))
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        (*roots, inherited) if inherited else roots
    )
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=90,
    )
    if completed.returncode:
        _fail(
            "audit fixture child failed: "
            + completed.stderr.decode("utf-8", "replace").strip()
        )
    try:
        value = json.loads(completed.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        _fail(f"audit fixture child output is invalid: {type(exc).__name__}")
    if type(value) is not dict:
        _fail("audit fixture child output is not an object")
    return value


def _decode(value: object, label: str) -> bytes:
    if type(value) is not str:
        _fail(f"{label} is not base64 text")
    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (UnicodeError, ValueError) as exc:
        _fail(f"{label} is not strict base64: {type(exc).__name__}")


_RECORD_FIELDS = {
    "schema",
    "ordinal",
    "role",
    "role_id",
    "binding_role",
    "artifact_schema",
    "sha256",
    "byte_count",
    "record_sha256",
    "mathematical_authority",
}
_EVENT_FIELDS = {
    "schema",
    "event_order",
    "kind",
    "attempt_order",
    "strategy_sha256",
    "phase",
    "outcome",
    "reason_code",
    "subject_sha256s",
    "parent_budget_before_sha256",
    "parent_budget_after_sha256",
    "previous_event_sha256",
    "event_sha256",
    "mathematical_authority",
}
_MANIFEST_FIELDS = {
    "schema",
    "audited_run_contract_sha256",
    "replay_contract_sha256",
    "capability_registry_contract_sha256",
    "deterministic_planner_contract_sha256",
    "isolated_worker_contract_sha256",
    "proof_search_portfolio_contract_sha256",
    "problem_session_contract_sha256",
    "resource_budget_contract_sha256",
    "evidence_contract_sha256",
    "certificate_contract_sha256",
    "theory_plugin_contract_sha256",
    "normalized_input_sha256",
    "planning_request_sha256",
    "route_result_sha256",
    "planning_result_sha256",
    "portfolio_request_sha256",
    "portfolio_result_sha256",
    "initial_parent_budget_sha256",
    "final_parent_budget_sha256",
    "logical_report_sha256",
    "objects",
    "events",
    "manifest_sha256",
    "mathematical_authority",
}
_REPORT_FIELDS = {
    "schema",
    "audited_run_contract_sha256",
    "normalized_input_sha256",
    "planning_request_sha256",
    "route_result_sha256",
    "planning_result_sha256",
    "portfolio_request_sha256",
    "declared_budget_limits_sha256",
    "plugins",
    "artifacts",
    "attempts",
    "status",
    "mathematical_verdict",
    "reason_code",
    "selected_strategy_sha256",
    "selected_evidence_sha256",
    "selected_certificate_sha256",
    "selected_checker_decision_sha256",
    "authority_tier",
    "report_sha256",
    "mathematical_authority",
}


def _object_by_role(
    role_id: str,
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
) -> dict[str, Any]:
    record = next((item for item in records if item["role_id"] == role_id), None)
    if record is None:
        _fail(f"required audit role is absent: {role_id}")
    return _parse(physical[record["sha256"]], role_id)


def _verify_projection(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
    report: dict[str, Any],
) -> None:
    links = {
        "planning_request_sha256": "planning_request",
        "route_result_sha256": "capability_route_result",
        "planning_result_sha256": "planning_result",
        "portfolio_request_sha256": "portfolio_request",
    }
    by_role = {item["role_id"]: item for item in records}
    for field, role_id in links.items():
        if report[field] != by_role[role_id]["sha256"] or manifest[field] != report[field]:
            _fail(f"logical report singleton link differs: {field}")
    if (
        report["normalized_input_sha256"] != by_role["normalized_input"]["sha256"]
        or manifest["normalized_input_sha256"] != report["normalized_input_sha256"]
    ):
        _fail("logical report normalized input link differs")
    initial = _object_by_role("initial_parent_budget", records, physical)
    if report["declared_budget_limits_sha256"] != _sha(
        _canonical(initial.get("limits"))
    ):
        _fail("logical report declared budget projection differs")
    planning = _object_by_role("planning_result", records, physical)
    descriptors = {
        item["sha256"]: _parse(physical[item["sha256"]], item["role_id"])
        for item in records
        if item["role"] == "plugin_descriptor"
    }
    expected_plugins = []
    for strategy in planning.get("strategies", []):
        descriptor = descriptors.get(strategy.get("descriptor_sha256"))
        if descriptor is None:
            _fail("planned descriptor is absent from audit closure")
        components = descriptor.get("components", {})
        expected_plugins.append(
            {
                "plan_order": strategy.get("plan_order"),
                "strategy_sha256": strategy.get("strategy_sha256"),
                "descriptor_sha256": strategy.get("descriptor_sha256"),
                "plugin_id": descriptor.get("plugin_id"),
                "plugin_version": descriptor.get("plugin_version"),
                "producer_component_id": components.get("producer", {}).get(
                    "component_id"
                ),
                "checker_component_id": components.get("checker", {}).get(
                    "component_id"
                ),
            }
        )
    if report["plugins"] != expected_plugins:
        _fail("logical report plugin projection differs")
    portfolio = _object_by_role("portfolio_result", records, physical)
    scalar_links = {
        "status": "status",
        "mathematical_verdict": "mathematical_verdict",
        "reason_code": "reason_code",
        "selected_strategy_sha256": "selected_strategy_sha256",
        "selected_evidence_sha256": "selected_evidence_sha256",
        "selected_certificate_sha256": "selected_certificate_sha256",
        "selected_checker_decision_sha256": "selected_checker_decision_sha256",
        "authority_tier": "authority_tier",
    }
    if any(report[left] != portfolio[right] for left, right in scalar_links.items()):
        _fail("logical report portfolio classification differs")
    attempts = []
    for attempt in portfolio.get("attempts", []):
        attempts.append(
            {
                key: attempt.get(key)
                for key in (
                    "attempt_order",
                    "strategy_sha256",
                    "producer_worker_result_sha256",
                    "producer_status",
                    "producer_reason_code",
                    "evidence_sha256",
                    "checker_worker_result_sha256",
                    "checker_status",
                    "checker_reason_code",
                    "checker_decision_sha256",
                    "outcome",
                    "transition_sha256",
                )
            }
        )
    if report["attempts"] != attempts:
        _fail("logical report attempt projection differs")
    artifact_roles = {
        "session_event",
        "normalized_input",
        "session_context",
        "session_obligation",
        "session_artifact",
        "plugin_descriptor",
        "execution_binding",
        "validated_evidence",
        "checker_certificate",
        "checker_decision",
    }
    expected_artifacts = [
        {
            "role_id": item["role_id"],
            "sha256": item["sha256"],
            "byte_count": item["byte_count"],
        }
        for item in records
        if item["role"] in artifact_roles
    ]
    if report["artifacts"] != expected_artifacts:
        _fail("logical report artifact projection differs")


def _verify_bundle(sample: dict[str, Any], label: str) -> dict[str, object]:
    manifest_raw = _decode(sample.get("manifest"), f"{label}.manifest")
    object_values = sample.get("objects")
    if type(object_values) is not list:
        _fail(f"{label}.objects is not an array")
    objects = tuple(
        _decode(item, f"{label}.objects[{index}]")
        for index, item in enumerate(object_values)
    )
    logical_raw = _decode(sample.get("logical_report"), f"{label}.logical_report")
    replay = _parse(_decode(sample.get("replay"), f"{label}.replay"), "replay")
    combined = b"".join((manifest_raw, logical_raw, *objects))
    if any(marker in combined for marker in FORBIDDEN_MARKERS):
        _fail(f"{label} retained an ambient path, environment, or secret marker")
    manifest = _parse(manifest_raw, f"{label}.manifest")
    _exact_fields(manifest, _MANIFEST_FIELDS, f"{label}.manifest")
    if (
        manifest["schema"] != MANIFEST_SCHEMA
        or manifest["audited_run_contract_sha256"] != AUDIT_SHA256
        or manifest["replay_contract_sha256"] != REPLAY_SHA256
        or manifest["mathematical_authority"] is not False
        or manifest["manifest_sha256"]
        != _self_hash(manifest, "manifest_sha256")
    ):
        _fail(f"{label} manifest binding or identity differs")
    raw_records = manifest["objects"]
    raw_events = manifest["events"]
    if (
        type(raw_records) is not list
        or not 8 <= len(raw_records) <= MAX_OBJECTS
        or type(raw_events) is not list
        or not 4 <= len(raw_events) <= MAX_EVENTS
    ):
        _fail(f"{label} manifest inventories are outside bounds")
    physical: dict[str, bytes] = {}
    physical_order: list[str] = []
    for raw in objects:
        digest = _sha(raw)
        if digest in physical:
            _fail(f"{label} physical object digest is duplicated")
        physical[digest] = raw
        physical_order.append(digest)
    if physical_order != sorted(physical_order):
        _fail(f"{label} physical objects are not digest sorted")
    records: list[dict[str, Any]] = []
    role_ids: set[str] = set()
    for ordinal, raw_record in enumerate(raw_records):
        if type(raw_record) is not dict:
            _fail(f"{label} object record is not an object")
        record = raw_record
        _exact_fields(record, _RECORD_FIELDS, f"{label}.objects[{ordinal}]")
        digest = _digest(record["sha256"], "object.sha256")
        if (
            record["schema"] != OBJECT_SCHEMA
            or record["ordinal"] != ordinal
            or record["mathematical_authority"] is not False
            or record["record_sha256"] != _self_hash(record, "record_sha256")
            or type(record["role_id"]) is not str
            or record["role_id"] in role_ids
            or digest not in physical
            or record["byte_count"] != len(physical[digest])
        ):
            _fail(f"{label} object record identity or content differs at {ordinal}")
        artifact = _parse(physical[digest], str(record["role_id"]))
        if artifact.get("schema") != record["artifact_schema"]:
            _fail(f"{label} object schema binding differs at {ordinal}")
        role_ids.add(record["role_id"])
        records.append(record)
    if set(physical) != {item["sha256"] for item in records}:
        _fail(f"{label} semantic and physical object closure differs")
    previous = None
    for ordinal, event in enumerate(raw_events):
        if type(event) is not dict:
            _fail(f"{label} event is not an object")
        _exact_fields(event, _EVENT_FIELDS, f"{label}.events[{ordinal}]")
        subjects = event["subject_sha256s"]
        if (
            event["schema"] != EVENT_SCHEMA
            or event["event_order"] != ordinal
            or event["previous_event_sha256"] != previous
            or event["event_sha256"] != _self_hash(event, "event_sha256")
            or event["mathematical_authority"] is not False
            or type(subjects) is not list
            or subjects != sorted(set(subjects))
            or any(DIGEST.fullmatch(str(item)) is None for item in subjects)
            or REASON.fullmatch(str(event["reason_code"])) is None
        ):
            _fail(f"{label} event chain differs at {ordinal}")
        previous = event["event_sha256"]
    by_role = {item["role_id"]: item for item in records}
    singleton_links = {
        "planning_request_sha256": "planning_request",
        "route_result_sha256": "capability_route_result",
        "planning_result_sha256": "planning_result",
        "portfolio_request_sha256": "portfolio_request",
        "portfolio_result_sha256": "portfolio_result",
        "initial_parent_budget_sha256": "initial_parent_budget",
        "final_parent_budget_sha256": "final_parent_budget",
        "logical_report_sha256": "logical_report",
    }
    if any(
        manifest[field] != by_role[role_id]["sha256"]
        for field, role_id in singleton_links.items()
    ):
        _fail(f"{label} manifest singleton links differ")
    if _sha(logical_raw) != manifest["logical_report_sha256"]:
        _fail(f"{label} retained logical report differs")
    report = _parse(logical_raw, f"{label}.logical_report")
    _exact_fields(report, _REPORT_FIELDS, f"{label}.logical_report")
    if (
        report["schema"] != LOGICAL_SCHEMA
        or report["audited_run_contract_sha256"] != AUDIT_SHA256
        or report["mathematical_authority"] is not False
        or report["report_sha256"] != _self_hash(report, "report_sha256")
    ):
        _fail(f"{label} logical report binding or identity differs")
    _verify_projection(manifest, records, physical, report)
    if (
        replay.get("schema") != "mathhead.run-audit-replay-result.v1"
        or replay.get("contract_id") != REPLAY_CONTRACT
        or replay.get("contract_sha256") != REPLAY_SHA256
        or replay.get("status") != "complete"
        or replay.get("reason_code") != "REPLAY_COMPLETE"
        or replay.get("manifest_sha256") != _sha(manifest_raw)
        or replay.get("logical_report_sha256") != _sha(logical_raw)
        or replay.get("object_count") != len(objects)
        or replay.get("event_count") != len(raw_events)
        or replay.get("mathematical_authority") is not False
        or replay.get("replay_result_sha256")
        != _self_hash(replay, "replay_result_sha256")
    ):
        _fail(f"{label} replay result differs")
    return {
        "logical_report_sha256": _sha(logical_raw),
        "objects": len(objects),
        "records": len(records),
        "events": len(raw_events),
        "attempts": len(report["attempts"]),
        "plugins": len(report["plugins"]),
        "status": report["status"],
        "verdict": report["mathematical_verdict"],
    }


def _negative_checks(sample: dict[str, Any]) -> dict[str, bool]:
    manifest_raw = _decode(sample["manifest"], "negative.manifest")
    objects = [_decode(item, "negative.object") for item in sample["objects"]]

    def rejected(manifest_bytes: bytes, values: list[bytes]) -> bool:
        candidate = {
            "manifest": base64.b64encode(manifest_bytes).decode("ascii"),
            "objects": [base64.b64encode(item).decode("ascii") for item in values],
            "logical_report": sample["logical_report"],
            "replay": sample["replay"],
        }
        try:
            _verify_bundle(candidate, "negative")
        except AuditValidationError:
            return True
        return False

    manifest = _parse(manifest_raw, "negative.manifest")
    unknown = dict(manifest)
    unknown["host_path"] = "/forbidden"
    repaired_event = json.loads(manifest_raw)
    repaired_event["events"][0]["reason_code"] = "CALLER_REPAIRED"
    repaired_event["events"][0]["event_sha256"] = _self_hash(
        repaired_event["events"][0], "event_sha256"
    )
    for index in range(1, len(repaired_event["events"])):
        repaired_event["events"][index]["previous_event_sha256"] = repaired_event[
            "events"
        ][index - 1]["event_sha256"]
        repaired_event["events"][index]["event_sha256"] = _self_hash(
            repaired_event["events"][index], "event_sha256"
        )
    repaired_event["manifest_sha256"] = _self_hash(
        repaired_event, "manifest_sha256"
    )
    checks = {
        "missing_object": rejected(manifest_raw, objects[:-1]),
        "surplus_object": rejected(manifest_raw, [*objects, b"{}\n"]),
        "reordered_objects": rejected(manifest_raw, list(reversed(objects))),
        "unknown_manifest_field": rejected(_canonical(unknown), objects),
        "repaired_event_chain": rejected(_canonical(repaired_event), objects),
    }
    if not all(checks.values()):
        _fail("one or more independent negative controls did not fail closed")
    return checks


def _report() -> dict[str, object]:
    contracts = _contract_checks()
    source = _source_checks()
    first = _runtime_sample("1")
    second = _runtime_sample("8675309")
    success = _verify_bundle(first["success"], "success")
    fallback = _verify_bundle(first["fallback"], "fallback")
    second_success = _verify_bundle(second["success"], "success_second")
    second_fallback = _verify_bundle(second["fallback"], "fallback_second")
    if (
        success["logical_report_sha256"]
        != second_success["logical_report_sha256"]
        or fallback["logical_report_sha256"]
        != second_fallback["logical_report_sha256"]
    ):
        _fail("fresh-process logical report differs across hash seeds")
    if success["status"] != "succeeded" or fallback["attempts"] != 2:
        _fail("runtime fixtures did not exercise success and fallback paths")
    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "contracts": contracts,
        "source": source,
        "fixtures": {"success": success, "fallback": fallback},
        "negative_controls": _negative_checks(first["success"]),
        "checks": [
            "accepted-contract-and-schema-binding",
            "ambient-effect-exclusion",
            "canonical-content-closure",
            "record-and-event-self-identities",
            "contiguous-event-chain",
            "normalized-input-plan-plugin-budget-projection",
            "portfolio-attempt-and-checker-projection",
            "fresh-process-determinism",
            "hostile-input-fail-closed",
            "non-authoritative-replay-result",
        ],
        "mathematical_authority": False,
        "report_sha256": None,
    }
    report["report_sha256"] = _self_hash(report, "report_sha256")
    return report


def main() -> int:
    try:
        report = _report()
        rendered = _canonical(report)
        if "--write-report" in sys.argv:
            REPORT.parent.mkdir(parents=True, exist_ok=True)
            REPORT.write_bytes(rendered)
        elif not REPORT.is_file() or REPORT.read_bytes() != rendered:
            _fail(f"frozen report drift or missing: {REPORT.relative_to(ROOT)}")
    except (
        AuditValidationError,
        OSError,
        UnicodeError,
        ValueError,
        SyntaxError,
        tomllib.TOMLDecodeError,
    ) as exc:
        print(f"run-audit: FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "run-audit: PASS "
        "(closed objects, deterministic events, stable replay, ambient data excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
