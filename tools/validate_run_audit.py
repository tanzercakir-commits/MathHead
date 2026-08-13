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

from audit_schema_validation import (
    AuditSchemaValidationError,
    validate_schema_graph,
    validate_schema_instance,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/run_audit.py"
REPORT = ROOT / "docs/planning/reports/run-audit-v4.json"
AUDIT_CONTRACT = "MH-C-AUDITED-RUN-004"
AUDIT_SHA256 = "9079e68799fe032d982be87034ecb42cbc4b9a8486f370f01ace12a21d2ac4c4"
REPLAY_CONTRACT = "MH-C-RUN-AUDIT-REPLAY-004"
REPLAY_SHA256 = "04f484fc85486bcf8b17519128cd74336ff1834e76ab8d5e2713022d91c02c3b"
SCHEMAS = {
    "run-audit-object-v2.schema.json": "b81596770c10bac4e192155cd24aea721da2c8dc8b8d8b5f73a3b11570cdd92c",
    "run-audit-event-v2.schema.json": "eeb0f4ec975dc8417841f6677100f276d85cd356c3d0f376efa800e2ebbc0239",
    "run-audit-manifest-v3.schema.json": "784184e21eccd7043e188b776ec5154328860e99015fe87102cc776bd050eabd",
    "run-logical-report-v2.schema.json": "d4a2a23426122d0ba64d3fc8a8135bde13c80794d221eaca9d6a49e7b134d2a2",
    "run-audit-replay-result-v4.schema.json": "ae6f6f60f936a40926cd7942e00088a8f409836182d089b2f9c3cec5b007269d",
    "run-audit-worker-observation-v3.schema.json": "6abfae6c0f1be7811e8e8f3cc3e5de895274226e6834201da8018bc4df685a61",
}
REPORT_SCHEMA = "mathhead.run-audit-validation-report.v4"
MANIFEST_SCHEMA = "mathhead.run-audit-manifest.v3"
OBJECT_SCHEMA = "mathhead.run-audit-object.v2"
EVENT_SCHEMA = "mathhead.run-audit-event.v2"
LOGICAL_SCHEMA = "mathhead.run-logical-report.v2"
WORKER_OBSERVATION_SCHEMA = "mathhead.run-audit-worker-observation.v3"
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
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("constant")),
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
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
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


_CHILD = r"""import base64, json, os, tempfile
from pathlib import Path
from mathhead.isolated_worker import isolation_capability
from mathhead.proof_search_portfolio import make_proof_search_portfolio_request
from mathhead.run_audit import execute_audited_run, replay_run_audit, run_audit_replay_result_bytes
from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture, PortfolioFixture
from tests.run_audit.fixtures import single_bundle

def enc(value):
    return base64.b64encode(value).decode("ascii")

def packed(bundle):
    replay = replay_run_audit(bundle.manifest, bundle.objects)
    return {
        "manifest": enc(bundle.manifest),
        "objects": [enc(item) for item in bundle.objects],
        "logical_report": enc(bundle.logical_report),
        "replay": enc(run_audit_replay_result_bytes(replay)),
    }

def execute(fixture, fallback=False, prelaunch=False):
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
            () if prelaunch else fixture.executable_paths, workspace,
        )
    return packed(bundle)

os.environ["MATHHEAD_AUDIT_SENTINEL"] = "MH054_ENV_SECRET_DO_NOT_RECORD"
print(json.dumps({
    "isolation_supported": isolation_capability().supported,
    "success": execute(PortfolioFixture()),
    "fallback": execute(FallbackPortfolioFixture(), True),
    "prelaunch": execute(PortfolioFixture(), prelaunch=True),
    "invalid_output": packed(single_bundle(malformed_evidence=True).bundle),
}, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
"""


def _runtime_sample(seed: str) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    roots = (str(ROOT / "src"), str(ROOT))
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join((*roots, inherited) if inherited else roots)
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
        _fail("audit fixture child failed: " + completed.stderr.decode("utf-8", "replace").strip())
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


def _expected_record_sequence(
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
) -> list[tuple[str, str, str | None]]:
    planning_request = _object_by_role("planning_request", records, physical)
    route_request = planning_request.get("route_request")
    request = _object_by_role("portfolio_request", records, physical)
    portfolio = _object_by_role("portfolio_result", records, physical)
    if type(route_request) is not dict:
        _fail("planning request route input is not an object")
    expected: list[tuple[str, str, str | None]] = [
        ("planning_request", "planning_request", None),
        ("capability_route_result", "capability_route_result", None),
        ("planning_result", "planning_result", None),
        ("portfolio_request", "portfolio_request", None),
        ("portfolio_result", "portfolio_result", None),
        ("initial_parent_budget", "initial_parent_budget", None),
    ]
    event_ids = route_request.get("event_sha256s")
    session_ids = route_request.get("session_artifact_sha256s")
    bindings = request.get("artifact_bindings")
    if type(event_ids) is not list or type(session_ids) is not list or type(bindings) is not list:
        _fail("canonical session ordering inputs differ")
    event_set = set(event_ids)
    session_set = set(session_ids)
    seen_events: set[str] = set()
    seen_session: set[str] = set()
    artifacts_by_role = {
        item["binding_role"]: physical[item["sha256"]]
        for item in records
        if item["binding_role"] is not None
    }
    for binding in bindings:
        if type(binding) is not dict or type(binding.get("role")) is not str:
            _fail("portfolio artifact binding differs")
        binding_role = binding["role"]
        raw = artifacts_by_role.get(binding_role)
        if raw is None:
            _fail("canonical session artifact is absent")
        parsed = _parse(raw, f"canonical_{binding_role}")
        identity = _sha(raw)
        event_identity = parsed.get("event_sha256")
        if (
            parsed.get("schema") == "mathhead.problem-session-event.v1"
            and event_identity in event_set
        ):
            role = "session_event"
            role_id = f"session_event_{event_ids.index(event_identity):06d}"
            seen_events.add(str(event_identity))
        elif identity == route_request.get("normalization_result_sha256"):
            role, role_id = "normalized_input", "normalized_input"
            seen_session.add(identity)
        elif identity == route_request.get("session_context_sha256"):
            role, role_id = "session_context", "session_context"
            seen_session.add(identity)
        elif identity == route_request.get("obligation_artifact_sha256"):
            role, role_id = "session_obligation", "session_obligation"
            seen_session.add(identity)
        elif identity in session_set:
            role = "session_artifact"
            role_id = f"session_artifact_{session_ids.index(identity):06d}"
            seen_session.add(identity)
        else:
            _fail("canonical artifact is outside the current session")
        expected.append((role, role_id, binding_role))
    if seen_events != event_set or seen_session != session_set:
        _fail("canonical session record closure differs")
    descriptor_ids = request.get("descriptor_sha256s")
    binding_ids = request.get("binding_sha256s")
    if type(descriptor_ids) is not list or type(binding_ids) is not list:
        _fail("portfolio descriptor or execution-binding inventory differs")
    for index, _identity in enumerate(sorted(descriptor_ids)):
        expected.append(("plugin_descriptor", f"plugin_descriptor_{index:06d}", None))
    execution_records = {
        item["sha256"]: _parse(physical[item["sha256"]], str(item["role_id"]))
        for item in records
        if item["role"] == "execution_binding"
    }
    for index, identity in enumerate(binding_ids):
        binding = execution_records.get(identity)
        if binding is None or binding.get("plan_order") != index:
            _fail("canonical execution-binding order differs")
        expected.append(("execution_binding", f"execution_binding_{index:06d}", None))
    attempts = portfolio.get("attempts")
    if type(attempts) is not list:
        _fail("portfolio attempts are not an array")
    for attempt in attempts:
        if type(attempt) is not dict or type(attempt.get("attempt_order")) is not int:
            _fail("portfolio attempt order differs")
        order = attempt["attempt_order"]
        expected.append(("worker_observation", f"producer_worker_observation_{order:06d}", None))
        if attempt.get("checker_worker_result_sha256") is not None:
            expected.append(("worker_observation", f"checker_worker_observation_{order:06d}", None))
    ledger_order = 0
    for attempt in attempts:
        order = attempt["attempt_order"]
        expected.append(
            ("reconciled_parent_budget", f"reconciled_parent_budget_{ledger_order:06d}", None)
        )
        ledger_order += 1
        if attempt.get("evidence_sha256") is not None:
            expected.append(("validated_evidence", f"validated_evidence_{order:06d}", None))
        if attempt.get("checker_worker_result_sha256") is not None:
            expected.append(
                ("reconciled_parent_budget", f"reconciled_parent_budget_{ledger_order:06d}", None)
            )
            ledger_order += 1
        if attempt.get("checker_decision_sha256") is not None:
            expected.extend(
                (
                    ("checker_certificate", f"checker_certificate_{order:06d}", None),
                    ("checker_decision", f"checker_decision_{order:06d}", None),
                )
            )
    expected.extend(
        (
            ("reconciled_parent_budget", "final_parent_budget", None),
            ("logical_report", "logical_report", None),
        )
    )
    return expected


def _is_prelaunch_invalid(portfolio: dict[str, Any]) -> bool:
    return (
        portfolio.get("status") == "invalid"
        and portfolio.get("reason_code") == "PORTFOLIO_INPUT_INVALID"
        and portfolio.get("request_sha256") is None
        and portfolio.get("planning_result_sha256") is None
        and portfolio.get("initial_parent_budget_sha256") is None
        and portfolio.get("final_parent_budget_sha256") is None
        and portfolio.get("attempts") == []
        and portfolio.get("inconclusive_outcomes") == []
        and portfolio.get("selected_strategy_sha256") is None
        and portfolio.get("selected_evidence_sha256") is None
        and portfolio.get("selected_certificate_sha256") is None
        and portfolio.get("selected_checker_decision_sha256") is None
        and portfolio.get("authority_tier") == "none"
        and portfolio.get("mathematical_verdict") == "none"
    )


def _expected_events(
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
) -> list[dict[str, Any]]:
    by_role = {item["role_id"]: item for item in records}
    portfolio = _object_by_role("portfolio_result", records, physical)
    events: list[dict[str, Any]] = []

    def add(
        *,
        kind: str,
        attempt_order: int | None,
        strategy: str | None,
        phase: str,
        outcome: str,
        reason: str,
        subjects: tuple[str, ...],
        parent_before: str | None = None,
        parent_after: str | None = None,
    ) -> None:
        value: dict[str, Any] = {
            "schema": EVENT_SCHEMA,
            "event_order": len(events),
            "kind": kind,
            "attempt_order": attempt_order,
            "strategy_sha256": strategy,
            "phase": phase,
            "outcome": outcome,
            "reason_code": reason,
            "subject_sha256s": sorted(set(subjects)),
            "parent_budget_before_sha256": parent_before,
            "parent_budget_after_sha256": parent_after,
            "previous_event_sha256": None if not events else events[-1]["event_sha256"],
            "event_sha256": None,
            "mathematical_authority": False,
        }
        value["event_sha256"] = _self_hash(value, "event_sha256")
        events.append(value)

    planning = str(by_role["planning_request"]["sha256"])
    route = str(by_role["capability_route_result"]["sha256"])
    plan = str(by_role["planning_result"]["sha256"])
    request = str(by_role["portfolio_request"]["sha256"])
    initial = str(by_role["initial_parent_budget"]["sha256"])
    final = str(by_role["final_parent_budget"]["sha256"])
    logical = str(by_role["logical_report"]["sha256"])
    portfolio_identity = str(by_role["portfolio_result"]["sha256"])
    add(
        kind="run_opened",
        attempt_order=None,
        strategy=None,
        phase="run",
        outcome="opened",
        reason="RUN_OPENED",
        subjects=(planning, route, plan, request, initial),
        parent_before=initial,
        parent_after=initial,
    )
    input_inventory = _sha(
        _canonical(
            [
                item["record_sha256"]
                for item in records
                if item["role"]
                in {
                    "session_event",
                    "normalized_input",
                    "session_context",
                    "session_obligation",
                    "session_artifact",
                }
            ]
        )
    )
    add(
        kind="input_bound",
        attempt_order=None,
        strategy=None,
        phase="input",
        outcome="bound",
        reason="INPUT_BOUND",
        subjects=(str(by_role["normalized_input"]["sha256"]), input_inventory),
    )
    plan_inventory = _sha(
        _canonical(
            [
                item["record_sha256"]
                for item in records
                if item["role"] in {"plugin_descriptor", "execution_binding"}
            ]
        )
    )
    add(
        kind="plan_bound",
        attempt_order=None,
        strategy=None,
        phase="plan",
        outcome="bound",
        reason="PLAN_BOUND",
        subjects=(plan, plan_inventory),
    )
    ledgers = [
        item
        for item in records
        if item["role"] == "reconciled_parent_budget"
        and str(item["role_id"]).startswith("reconciled_parent_budget_")
    ]
    ledger_index = 0
    current_parent = initial
    status_outcomes = {
        "completed": "completed",
        "cancelled": "cancelled",
        "exhausted": "exhausted",
        "unsupported": "unsupported",
        "invalid": "invalid",
        "refused": "failed",
        "failed": "failed",
    }
    for attempt in portfolio["attempts"]:
        order = attempt["attempt_order"]
        strategy = attempt["strategy_sha256"]
        add(
            kind="strategy_started",
            attempt_order=order,
            strategy=strategy,
            phase="plan",
            outcome="opened",
            reason="STRATEGY_STARTED",
            subjects=(strategy,),
            parent_before=current_parent,
            parent_after=current_parent,
        )
        if ledger_index >= len(ledgers):
            _fail("producer reconciled ledger is absent")
        producer_after = str(ledgers[ledger_index]["sha256"])
        ledger_index += 1
        producer_observation = by_role.get(f"producer_worker_observation_{order:06d}")
        if producer_observation is None:
            _fail("producer worker observation is absent")
        add(
            kind="producer_completed",
            attempt_order=order,
            strategy=strategy,
            phase="producer",
            outcome=status_outcomes.get(attempt["producer_status"], "failed"),
            reason=attempt["producer_reason_code"],
            subjects=(
                strategy,
                attempt["producer_worker_result_sha256"],
                str(producer_observation["sha256"]),
            ),
            parent_before=current_parent,
            parent_after=producer_after,
        )
        evidence = by_role.get(f"validated_evidence_{order:06d}")
        checker_started = attempt["checker_worker_result_sha256"] is not None
        if evidence is not None:
            evidence_outcome = "success" if checker_started else attempt["outcome"]
            evidence_reason = (
                "EVIDENCE_VALIDATED"
                if checker_started
                else {
                    "unsupported": "EVIDENCE_UNSUPPORTED",
                    "ambiguous": "EVIDENCE_INCOMPLETE",
                    "cancelled": "EVIDENCE_CANCELLED",
                    "exhausted": "EVIDENCE_EXHAUSTED",
                    "truncated": "EVIDENCE_TRUNCATED",
                    "producer_error": "EVIDENCE_ERROR",
                    "invalid_evidence": "EVIDENCE_INVALID",
                }.get(attempt["outcome"], "EVIDENCE_CLASSIFIED")
            )
            add(
                kind="evidence_classified",
                attempt_order=order,
                strategy=strategy,
                phase="producer",
                outcome=evidence_outcome,
                reason=evidence_reason,
                subjects=(strategy, str(evidence["sha256"])),
                parent_before=producer_after,
                parent_after=producer_after,
            )
        elif attempt["producer_status"] == "completed":
            add(
                kind="evidence_classified",
                attempt_order=order,
                strategy=strategy,
                phase="producer",
                outcome=attempt["outcome"],
                reason="EVIDENCE_NOT_RETAINED",
                subjects=(strategy, attempt["producer_worker_result_sha256"]),
                parent_before=producer_after,
                parent_after=producer_after,
            )
        attempt_after = producer_after
        if checker_started:
            checker_observation = by_role.get(f"checker_worker_observation_{order:06d}")
            if checker_observation is None or ledger_index >= len(ledgers):
                _fail("checker observation or ledger is absent")
            checker_after = str(ledgers[ledger_index]["sha256"])
            ledger_index += 1
            add(
                kind="checker_completed",
                attempt_order=order,
                strategy=strategy,
                phase="checker",
                outcome=status_outcomes.get(attempt["checker_status"], "failed"),
                reason=attempt["checker_reason_code"],
                subjects=(
                    strategy,
                    attempt["checker_worker_result_sha256"],
                    str(checker_observation["sha256"]),
                ),
                parent_before=producer_after,
                parent_after=checker_after,
            )
            attempt_after = checker_after
            decision = by_role.get(f"checker_decision_{order:06d}")
            certificate = by_role.get(f"checker_certificate_{order:06d}")
            if decision is not None and certificate is not None:
                add(
                    kind="checker_decided",
                    attempt_order=order,
                    strategy=strategy,
                    phase="checker",
                    outcome=("success" if attempt["outcome"] == "success" else attempt["outcome"]),
                    reason="CHECKER_DECIDED",
                    subjects=(
                        strategy,
                        str(decision["sha256"]),
                        str(certificate["sha256"]),
                    ),
                    parent_before=checker_after,
                    parent_after=checker_after,
                )
            elif decision is not None or certificate is not None:
                _fail("checker decision and certificate presence differs")
        add(
            kind="transition_selected",
            attempt_order=order,
            strategy=strategy,
            phase="transition",
            outcome=attempt["outcome"],
            reason="TRANSITION_SELECTED",
            subjects=(strategy, attempt["transition_sha256"]),
            parent_before=attempt_after,
            parent_after=attempt_after,
        )
        current_parent = attempt_after
    if ledger_index != len(ledgers) or current_parent != final:
        _fail("event ledger closure differs")
    add(
        kind="run_closed",
        attempt_order=None,
        strategy=portfolio["selected_strategy_sha256"],
        phase="run",
        outcome="closed",
        reason=portfolio["reason_code"],
        subjects=(portfolio_identity, logical, final),
        parent_before=final,
        parent_after=final,
    )
    return events


def _worker_request_identity(
    *,
    planning_result: bytes,
    parent_budget: bytes,
    strategy: dict[str, Any],
    binding: dict[str, Any],
    phase: str,
    arguments: list[str],
    artifacts: list[tuple[str, bytes]],
) -> str:
    family_name = binding[f"{phase}_family"]
    families = {
        "sympy": "sympy",
        "enumeration": "python_enumeration",
        "smt": "smt",
        "external": "external_process",
    }
    identity = strategy["strategy_sha256"][:16]
    request = {
        "schema": "mathhead.isolated-worker-request.v1",
        "planning_result_sha256": _sha(planning_result),
        "strategy_sha256": strategy["strategy_sha256"],
        "descriptor_sha256": strategy["descriptor_sha256"],
        "family": families[family_name],
        "protocol": "raw_stdout_v1",
        "executable_sha256": binding[f"{phase}_executable_sha256"],
        "arguments": arguments,
        "artifact_bindings": [
            {"role": role, "sha256": _sha(raw), "bytes": len(raw)} for role, raw in artifacts
        ],
        "parent_budget_sha256": _sha(parent_budget),
        "lease_id": f"lease_portfolio_{strategy['plan_order']}_{phase}_{identity}",
        "child_budget_id": f"budget_portfolio_{strategy['plan_order']}_{phase}_{identity}",
        "resource_limits": strategy["resource_request"]["requested"],
        "request_sha256": None,
        "mathematical_authority": False,
    }
    return _self_hash(request, "request_sha256")


def _verify_observation(
    *,
    observation: dict[str, Any],
    attempt: dict[str, Any],
    phase: str,
    request_identity: str,
    planning_sha256: str,
    strategy_sha256: str,
    retained_stdout: bytes | None,
    isolated_worker_sha256: str,
) -> None:
    _exact_fields(
        observation,
        {
            "schema",
            "attempt_order",
            "phase",
            "request_sha256",
            "result_identity_sha256",
            "result",
            "observation_sha256",
            "mathematical_authority",
        },
        f"{phase} worker observation",
    )
    result = observation["result"]
    if type(result) is not dict:
        _fail(f"{phase} worker result preimage is not an object")
    _exact_fields(
        result,
        {
            "schema",
            "contract_id",
            "contract_sha256",
            "status",
            "reason_code",
            "planning_result_sha256",
            "strategy_sha256",
            "capability",
            "artifacts",
            "diagnostics",
            "tree_terminated",
            "lease_reconciled",
            "mathematical_authority",
        },
        f"{phase} worker result preimage",
    )
    expected_identity = attempt[f"{phase}_worker_result_sha256"]
    if (
        observation["schema"] != WORKER_OBSERVATION_SCHEMA
        or observation["attempt_order"] != attempt["attempt_order"]
        or observation["phase"] != phase
        or observation["request_sha256"] != request_identity
        or observation["result_identity_sha256"] != expected_identity
        or observation["result_identity_sha256"] != _sha(_canonical(result))
        or observation["observation_sha256"] != _self_hash(observation, "observation_sha256")
        or observation["mathematical_authority"] is not False
        or result["schema"] != "mathhead.isolated-worker-result.v1"
        or result["contract_id"] != "MH-C-ISOLATED-WORKER-001"
        or result["contract_sha256"] != isolated_worker_sha256
        or result["planning_result_sha256"] != planning_sha256
        or result["strategy_sha256"] != strategy_sha256
        or result["status"] != attempt[f"{phase}_status"]
        or result["reason_code"] != attempt[f"{phase}_reason_code"]
        or result["capability"] is not None
        or result["diagnostics"] != []
        or type(result["tree_terminated"]) is not bool
        or type(result["lease_reconciled"]) is not bool
        or result["mathematical_authority"] is not False
    ):
        _fail(f"{phase} worker observation link differs")
    result_artifacts = result["artifacts"]
    if type(result_artifacts) is not list or len(result_artifacts) > 2:
        _fail(f"{phase} worker artifact inventory differs")
    roles = []
    for artifact in result_artifacts:
        if type(artifact) is not dict:
            _fail(f"{phase} worker artifact is not an object")
        _exact_fields(
            artifact,
            {
                "schema",
                "role",
                "media_type",
                "original_bytes",
                "retained_bytes",
                "omitted_bytes",
                "retained_sha256",
                "artifact_sha256",
                "mathematical_authority",
            },
            f"{phase} worker artifact",
        )
        if (
            artifact["schema"] != "mathhead.worker-artifact.v1"
            or artifact["role"] not in {"stdout", "stderr"}
            or artifact["media_type"] != "application/octet-stream"
            or artifact["original_bytes"] != artifact["retained_bytes"] + artifact["omitted_bytes"]
            or artifact["artifact_sha256"] != _self_hash(artifact, "artifact_sha256")
            or artifact["mathematical_authority"] is not False
        ):
            _fail(f"{phase} worker artifact identity differs")
        roles.append(artifact["role"])
    if roles not in ([], ["stdout"]):
        _fail(f"{phase} worker artifact role order differs")
    if retained_stdout is None:
        if result_artifacts:
            _fail(f"{phase} unvalidated output retained an artifact identity")
    else:
        if (
            len(result_artifacts) != 1
            or result_artifacts[0]["role"] != "stdout"
            or result_artifacts[0]["retained_bytes"] != len(retained_stdout)
            or result_artifacts[0]["retained_sha256"] != _sha(retained_stdout)
        ):
            _fail(f"{phase} retained stdout link differs")


def _verify_worker_observations(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
) -> None:
    by_role = {item["role_id"]: item for item in records}
    planning_raw = physical[by_role["planning_result"]["sha256"]]
    planning = _parse(planning_raw, "planning_result")
    portfolio = _object_by_role("portfolio_result", records, physical)
    if _is_prelaunch_invalid(portfolio):
        forbidden_roles = {
            "worker_observation",
            "validated_evidence",
            "checker_certificate",
            "checker_decision",
        }
        intermediate = [
            item
            for item in records
            if item["role"] == "reconciled_parent_budget"
            and item["role_id"] != "final_parent_budget"
        ]
        if (
            any(item["role"] in forbidden_roles for item in records)
            or intermediate
            or by_role["initial_parent_budget"]["sha256"]
            != by_role["final_parent_budget"]["sha256"]
        ):
            _fail("prelaunch-invalid audit closure differs")
        return
    strategies = {item["strategy_sha256"]: item for item in planning["strategies"]}
    bindings = {
        value["plan_order"]: value
        for value in (
            _parse(physical[item["sha256"]], str(item["role_id"]))
            for item in records
            if item["role"] == "execution_binding"
        )
    }
    artifacts_by_role = {
        item["binding_role"]: physical[item["sha256"]]
        for item in records
        if item["binding_role"] is not None
    }
    ledgers = [
        physical[item["sha256"]]
        for item in records
        if item["role"] == "reconciled_parent_budget"
        and str(item["role_id"]).startswith("reconciled_parent_budget_")
    ]
    observation_ids = {item["role_id"] for item in records if item["role"] == "worker_observation"}
    expected_ids: set[str] = set()
    current_parent = physical[by_role["initial_parent_budget"]["sha256"]]
    final_parent = physical[by_role["final_parent_budget"]["sha256"]]
    current_strategy = planning["entry_strategy_sha256"]
    ledger_index = 0
    for attempt_index, attempt in enumerate(portfolio["attempts"]):
        strategy = strategies.get(current_strategy)
        if (
            strategy is None
            or attempt["attempt_order"] != attempt_index
            or attempt["strategy_sha256"] != current_strategy
            or attempt["parent_budget_before_sha256"] != _sha(current_parent)
        ):
            _fail("worker observation strategy or parent order differs")
        binding = bindings.get(strategy["plan_order"])
        if binding is None:
            _fail("worker observation execution binding is absent")
        bound_artifacts = [
            (item["role"], artifacts_by_role[item["role"]]) for item in binding["input_artifacts"]
        ]
        producer_request = _worker_request_identity(
            planning_result=planning_raw,
            parent_budget=current_parent,
            strategy=strategy,
            binding=binding,
            phase="producer",
            arguments=binding["producer_arguments"],
            artifacts=bound_artifacts,
        )
        producer_id = f"producer_worker_observation_{attempt_index:06d}"
        expected_ids.add(producer_id)
        producer = _object_by_role(producer_id, records, physical)
        evidence_record = by_role.get(f"validated_evidence_{attempt_index:06d}")
        evidence = None if evidence_record is None else physical[evidence_record["sha256"]]
        _verify_observation(
            observation=producer,
            attempt=attempt,
            phase="producer",
            request_identity=producer_request,
            planning_sha256=_sha(planning_raw),
            strategy_sha256=current_strategy,
            retained_stdout=evidence,
            isolated_worker_sha256=manifest["isolated_worker_contract_sha256"],
        )
        if ledger_index >= len(ledgers):
            _fail("producer ledger is absent")
        current_parent = ledgers[ledger_index]
        ledger_index += 1
        if attempt["checker_worker_result_sha256"] is not None:
            if evidence is None:
                _fail("checker Evidence is absent")
            checker_artifacts = [*bound_artifacts, ("portfolio_evidence", evidence)]
            checker_request = _worker_request_identity(
                planning_result=planning_raw,
                parent_budget=current_parent,
                strategy=strategy,
                binding=binding,
                phase="checker",
                arguments=[*binding["checker_arguments"], evidence.decode("ascii")],
                artifacts=checker_artifacts,
            )
            checker_id = f"checker_worker_observation_{attempt_index:06d}"
            expected_ids.add(checker_id)
            checker = _object_by_role(checker_id, records, physical)
            decision_record = by_role.get(f"checker_decision_{attempt_index:06d}")
            certificate_record = by_role.get(f"checker_certificate_{attempt_index:06d}")
            checker_stdout = None
            if decision_record is not None and certificate_record is not None:
                checker_stdout = _canonical(
                    {
                        "certificate": _parse(
                            physical[certificate_record["sha256"]],
                            "checker_certificate",
                        ),
                        "decision": _parse(
                            physical[decision_record["sha256"]],
                            "checker_decision",
                        ),
                    }
                )
            _verify_observation(
                observation=checker,
                attempt=attempt,
                phase="checker",
                request_identity=checker_request,
                planning_sha256=_sha(planning_raw),
                strategy_sha256=current_strategy,
                retained_stdout=checker_stdout,
                isolated_worker_sha256=manifest["isolated_worker_contract_sha256"],
            )
            if ledger_index >= len(ledgers):
                _fail("checker ledger is absent")
            current_parent = ledgers[ledger_index]
            ledger_index += 1
        if attempt["parent_budget_after_sha256"] != _sha(current_parent):
            _fail("worker observation parent-after ledger differs")
        transitions = [
            item for item in strategy["transitions"] if item["outcome"] == attempt["outcome"]
        ]
        if (
            len(transitions) != 1
            or transitions[0]["transition_sha256"] != attempt["transition_sha256"]
        ):
            _fail("worker observation transition differs")
        current_strategy = (
            transitions[0]["target_strategy_sha256"]
            if transitions[0]["action"] == "fallback"
            else None
        )
    if (
        current_strategy is not None
        or ledger_index != len(ledgers)
        or current_parent != final_parent
        or observation_ids != expected_ids
    ):
        _fail("worker observation closure differs")


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
    if report["declared_budget_limits_sha256"] != _sha(_canonical(initial.get("limits"))):
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
                "producer_component_id": components.get("producer", {}).get("component_id"),
                "checker_component_id": components.get("checker", {}).get("component_id"),
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


def _verify_schema_graph(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    physical: dict[str, bytes],
    report: dict[str, Any],
    replay: dict[str, Any],
) -> None:
    schema_root = ROOT / "docs/contracts/schemas"
    schemas: dict[str, dict[str, Any]] = {}
    for name in SCHEMAS:
        path = schema_root / name
        try:
            value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
            if type(value) is not dict or type(value.get("$id")) is not str:
                _fail(f"schema resource identity differs: {path.name}")
            schemas[path.name] = value
        except (UnicodeError, ValueError, RecursionError) as exc:
            _fail(f"schema resource is invalid: {path.name}: {type(exc).__name__}")
    try:
        validate_schema_graph(schemas)
    except AuditSchemaValidationError as exc:
        _fail(f"schema graph is invalid: {exc}")

    def validate(name: str, value: object, label: str) -> None:
        schema = schemas.get(name)
        if schema is None:
            _fail(f"active schema resource is absent: {name}")
        try:
            validate_schema_instance(schema, value, schemas, label=label)
        except AuditSchemaValidationError as exc:
            _fail(f"{label} differs from resolved schema graph: {exc}")

    validate("run-audit-manifest-v3.schema.json", manifest, "manifest")
    for record in records:
        validate("run-audit-object-v2.schema.json", record, str(record["role_id"]))
        if record["role"] == "worker_observation":
            validate(
                "run-audit-worker-observation-v3.schema.json",
                _parse(physical[record["sha256"]], str(record["role_id"])),
                str(record["role_id"]),
            )
    for event in manifest["events"]:
        validate("run-audit-event-v2.schema.json", event, "event")
    validate("run-logical-report-v2.schema.json", report, "logical report")
    validate("run-audit-replay-result-v4.schema.json", replay, "replay result")


def _verify_bundle(sample: dict[str, Any], label: str) -> dict[str, object]:
    manifest_raw = _decode(sample.get("manifest"), f"{label}.manifest")
    object_values = sample.get("objects")
    if type(object_values) is not list:
        _fail(f"{label}.objects is not an array")
    objects = tuple(
        _decode(item, f"{label}.objects[{index}]") for index, item in enumerate(object_values)
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
        or manifest["manifest_sha256"] != _self_hash(manifest, "manifest_sha256")
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
    actual_sequence = [(item["role"], item["role_id"], item["binding_role"]) for item in records]
    if actual_sequence != _expected_record_sequence(records, physical):
        _fail(f"{label} semantic object record sequence differs")
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
    if raw_events != _expected_events(records, physical):
        _fail(f"{label} lifecycle event sequence differs")
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
        manifest[field] != by_role[role_id]["sha256"] for field, role_id in singleton_links.items()
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
    _verify_worker_observations(manifest, records, physical)
    if (
        replay.get("schema") != "mathhead.run-audit-replay-result.v4"
        or replay.get("contract_id") != REPLAY_CONTRACT
        or replay.get("contract_sha256") != REPLAY_SHA256
        or replay.get("status") != "complete"
        or replay.get("reason_code") != "REPLAY_COMPLETE"
        or replay.get("manifest_sha256") != _sha(manifest_raw)
        or replay.get("logical_report_sha256") != _sha(logical_raw)
        or replay.get("object_count") != len(objects)
        or replay.get("event_count") != len(raw_events)
        or replay.get("mathematical_authority") is not False
        or replay.get("replay_result_sha256") != _self_hash(replay, "replay_result_sha256")
    ):
        _fail(f"{label} replay result differs")
    _verify_schema_graph(manifest, records, physical, report, replay)
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
        repaired_event["events"][index]["previous_event_sha256"] = repaired_event["events"][
            index - 1
        ]["event_sha256"]
        repaired_event["events"][index]["event_sha256"] = _self_hash(
            repaired_event["events"][index], "event_sha256"
        )
    repaired_event["manifest_sha256"] = _self_hash(repaired_event, "manifest_sha256")
    repaired_records = json.loads(manifest_raw)
    first = repaired_records["objects"].index(
        next(item for item in repaired_records["objects"] if item["role_id"] == "portfolio_result")
    )
    second = repaired_records["objects"].index(
        next(
            item
            for item in repaired_records["objects"]
            if item["role_id"] == "initial_parent_budget"
        )
    )
    repaired_records["objects"][first], repaired_records["objects"][second] = (
        repaired_records["objects"][second],
        repaired_records["objects"][first],
    )
    for ordinal, record in enumerate(repaired_records["objects"]):
        record["ordinal"] = ordinal
        record["record_sha256"] = _self_hash(record, "record_sha256")
    repaired_records["manifest_sha256"] = _self_hash(repaired_records, "manifest_sha256")

    def reidentified_worker_rejected() -> bool:
        changed_manifest = json.loads(manifest_raw)
        changed_physical = {_sha(raw): raw for raw in objects}
        changed_records = {item["role_id"]: item for item in changed_manifest["objects"]}
        portfolio_record = changed_records["portfolio_result"]
        old_portfolio = portfolio_record["sha256"]
        portfolio = _parse(changed_physical.pop(old_portfolio), "negative.portfolio_result")
        old_worker = portfolio["attempts"][0]["producer_worker_result_sha256"]
        replacement = "0" * 64
        portfolio["attempts"][0]["producer_worker_result_sha256"] = replacement
        portfolio["attempts"][0]["attempt_sha256"] = _self_hash(
            portfolio["attempts"][0], "attempt_sha256"
        )
        portfolio["result_sha256"] = _self_hash(portfolio, "result_sha256")
        portfolio_raw = _canonical(portfolio)
        new_portfolio = _sha(portfolio_raw)
        changed_physical[new_portfolio] = portfolio_raw

        report_record = changed_records["logical_report"]
        old_report = report_record["sha256"]
        report = _parse(changed_physical.pop(old_report), "negative.logical_report")
        report["attempts"][0]["producer_worker_result_sha256"] = replacement
        report["report_sha256"] = _self_hash(report, "report_sha256")
        report_raw = _canonical(report)
        new_report = _sha(report_raw)
        changed_physical[new_report] = report_raw
        for record, raw, identity in (
            (portfolio_record, portfolio_raw, new_portfolio),
            (report_record, report_raw, new_report),
        ):
            record["sha256"] = identity
            record["byte_count"] = len(raw)
            record["record_sha256"] = _self_hash(record, "record_sha256")
        replacements = {
            old_worker: replacement,
            old_portfolio: new_portfolio,
            old_report: new_report,
        }
        previous = None
        for event in changed_manifest["events"]:
            event["subject_sha256s"] = sorted(
                {replacements.get(item, item) for item in event["subject_sha256s"]}
            )
            event["previous_event_sha256"] = previous
            event["event_sha256"] = _self_hash(event, "event_sha256")
            previous = event["event_sha256"]
        changed_manifest["portfolio_result_sha256"] = new_portfolio
        changed_manifest["logical_report_sha256"] = new_report
        changed_manifest["manifest_sha256"] = _self_hash(changed_manifest, "manifest_sha256")
        changed_manifest_raw = _canonical(changed_manifest)
        replay = _parse(_decode(sample["replay"], "negative.replay"), "replay")
        replay["manifest_sha256"] = _sha(changed_manifest_raw)
        replay["bundle_sha256"] = _sha(changed_manifest_raw)
        replay["logical_report_sha256"] = new_report
        replay["replay_result_sha256"] = _self_hash(replay, "replay_result_sha256")
        candidate = {
            "manifest": base64.b64encode(changed_manifest_raw).decode("ascii"),
            "objects": [
                base64.b64encode(changed_physical[item]).decode("ascii")
                for item in sorted(changed_physical)
            ],
            "logical_report": base64.b64encode(report_raw).decode("ascii"),
            "replay": base64.b64encode(_canonical(replay)).decode("ascii"),
        }
        try:
            _verify_bundle(candidate, "negative_worker")
        except AuditValidationError:
            return True
        return False

    checks = {
        "missing_object": rejected(manifest_raw, objects[:-1]),
        "surplus_object": rejected(manifest_raw, [*objects, b"{}\n"]),
        "reordered_objects": rejected(manifest_raw, list(reversed(objects))),
        "unknown_manifest_field": rejected(_canonical(unknown), objects),
        "repaired_event_chain": rejected(_canonical(repaired_event), objects),
        "repaired_semantic_record_order": rejected(_canonical(repaired_records), objects),
        "reidentified_worker_chain": reidentified_worker_rejected(),
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
    prelaunch = _verify_bundle(first["prelaunch"], "prelaunch")
    invalid_output = _verify_bundle(first["invalid_output"], "invalid_output")
    second_success = _verify_bundle(second["success"], "success_second")
    second_fallback = _verify_bundle(second["fallback"], "fallback_second")
    if (
        success["logical_report_sha256"] != second_success["logical_report_sha256"]
        or fallback["logical_report_sha256"] != second_fallback["logical_report_sha256"]
    ):
        _fail("fresh-process logical report differs across hash seeds")
    if prelaunch["status"] != "invalid" or prelaunch["attempts"] != 0:
        _fail("prelaunch-invalid fixture changed its closed classification")
    if invalid_output["status"] != "invalid_evidence":
        _fail("invalid-output fixture changed its closed classification")
    supported = first.get("isolation_supported")
    if type(supported) is not bool or second.get("isolation_supported") != supported:
        _fail("isolated-worker capability classification differs")
    if supported and (success["status"] != "succeeded" or fallback["attempts"] != 2):
        _fail("supported runtime fixtures did not exercise success and fallback paths")
    report: dict[str, object] = {
        "schema": REPORT_SCHEMA,
        "status": "passed",
        "contracts": contracts,
        "source": source,
        "fixtures": {
            "primary": {
                "complete": True,
                "projection_verified": True,
            },
            "fallback": {
                "complete": True,
                "projection_verified": True,
            },
            "prelaunch_invalid": {
                "complete": True,
                "unchanged_ledger_verified": True,
            },
            "invalid_output": {
                "complete": True,
                "digest_free_projection_verified": True,
            },
        },
        "negative_controls": _negative_checks(first["success"]),
        "checks": [
            "accepted-contract-and-schema-binding",
            "ambient-effect-exclusion",
            "canonical-content-closure",
            "record-and-event-self-identities",
            "contiguous-event-chain",
            "normalized-input-plan-plugin-budget-projection",
            "portfolio-attempt-and-checker-projection",
            "worker-observation-request-result-closure",
            "semantic-record-order-reconstruction",
            "resolved-json-schema-graph",
            "prelaunch-invalid-unchanged-ledger-closure",
            "invalid-output-digest-free-projection",
            "platform-terminal-closure",
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
