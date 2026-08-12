#!/usr/bin/env python3
"""Independently inspect the MH-046 atomic problem-session store boundary."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead.problem_session_store import (  # noqa: E402
    PROBLEM_SESSION_STORE_CONTRACT_SHA256,
    load_problem_session,
    persist_problem_session,
    recover_problem_session_store,
)
from mathhead.problem_sessions import (  # noqa: E402
    make_problem_session_command,
    make_session_artifact_link,
    make_session_definition,
)


CONTRACT_ID = "MH-C-PROBLEM-SESSION-STORE-001"
CONTRACT_SHA256 = "7637e5178767b661e6e361305090a9f7fb50d50bd5d316035283d73f970a9b82"
HEAD_SCHEMA_SHA256 = "a5bed15dda9e8c229687f1a89ba1ca9770e17d72314d16b5de63417472f3f683"
DEFAULT_REPORT = Path("docs/sessions/reports/problem-session-store-v1.json")
REPORT_SCHEMA = "mathhead.problem-session-store-validation-report.v1"
HEAD_FIELDS = {
    "artifact_sha256s",
    "event_sha256s",
    "head_event_sha256",
    "head_sha256",
    "mathematical_authority",
    "revision",
    "revision_sha256",
    "schema",
    "session_id",
    "session_key_sha256",
    "store_contract_id",
    "store_contract_sha256",
}


class ProblemSessionStoreReportError(RuntimeError):
    """An independent store identity or atomicity check failed."""


def _fail(detail: str) -> NoReturn:
    raise ProblemSessionStoreReportError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def _self_hash(value: dict[str, Any], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _identity_checks() -> dict[str, object]:
    expected = {
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path("docs/contracts/schemas/problem-session-store-head-v1.schema.json"):
            HEAD_SCHEMA_SHA256,
    }
    for path, digest in expected.items():
        if _sha((ROOT / path).read_bytes()) != digest:
            _fail(f"identity drift: {path}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed or accepted != _canonical(json.loads(accepted)):
        _fail("accepted/proposed contract canonical binding drift")
    if PROBLEM_SESSION_STORE_CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production store contract binding drift")
    manifest = (ROOT / "docs/contracts/manifest.toml").read_text()
    binding = (
        f'id = "{CONTRACT_ID}"\n'
        f'path = "docs/contracts/{CONTRACT_ID}.json"\n'
        f'sha256 = "{CONTRACT_SHA256}"\n'
        'state = "accepted"'
    )
    if manifest.count(binding) != 1:
        _fail("accepted manifest binding drift")
    return {"accepted_equals_proposed": True, "contract_bound": True, "schemas": 1}


def _source_checks() -> dict[str, object]:
    path = ROOT / "src/mathhead/problem_session_store.py"
    tree = ast.parse(path.read_text())
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            elif isinstance(node.func, ast.Name):
                calls.add(node.func.id)
    required_imports = {"os", "pathlib", "stat", "tempfile", "mathhead.problem_sessions"}
    if not required_imports <= imports:
        _fail(f"store effect imports drift: {sorted(required_imports - imports)}")
    required_calls = {"fsync", "replace", "lstat", "chmod", "resolve"}
    if not required_calls <= calls:
        _fail(f"store durability/path calls drift: {sorted(required_calls - calls)}")
    forbidden_imports = {"pickle", "subprocess", "socket", "urllib", "requests"}
    if imports & forbidden_imports:
        _fail(f"store gained forbidden imports: {sorted(imports & forbidden_imports)}")
    return {
        "effect_calls": sorted(required_calls),
        "imports": sorted(imports),
        "sha256": _sha(path.read_bytes()),
    }


def _object_path(root: Path, identity: str) -> Path:
    return root / "objects" / identity[:2] / identity[2:]


def _read_sealed(path: Path, identity: str) -> bytes:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _fail(f"stored object is not a direct single-link file: {identity}")
    if info.st_mode & 0o222:
        _fail(f"stored object remains writable: {identity}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        _fail(f"stored object ownership drift: {identity}")
    data = path.read_bytes()
    if not data or _sha(data) != identity:
        _fail(f"stored object content/path identity drift: {identity}")
    return data


def _fixture(root: Path) -> dict[str, object]:
    session_id = "session_store_validator"
    context = _canonical(
        {"context_id": "ctx_store_validator", "schema": "mathhead.theory-context.v1"}
    )
    analysis = _canonical(
        {
            "schema": "mathhead.canonical-normalization-result.v1",
            "status": "normalized",
        }
    )
    context_sha = _sha(context)
    analysis_sha = _sha(analysis)
    context_link = make_session_artifact_link(
        context,
        role="context",
        artifact_schema="mathhead.theory-context.v1",
        context_sha256=context_sha,
    )
    analysis_link = make_session_artifact_link(
        analysis,
        role="problem_analysis",
        artifact_schema="mathhead.canonical-normalization-result.v1",
        context_sha256=context_sha,
    )
    create = make_problem_session_command(
        command_id="create_store_validator",
        kind="create_session",
        session_id=session_id,
        context_sha256=context_sha,
        analysis_artifact_sha256s=(analysis_sha,),
        introduced_artifacts=tuple(
            sorted((context_link, analysis_link), key=lambda item: item.sha256)
        ),
    )
    created = persist_problem_session(root, create, tuple(sorted((context, analysis), key=_sha)))
    if created.status != "updated" or created.head_sha256 is None:
        _fail(f"initial store fixture failed: {created.reason_code}")
    create_head = created.head_sha256
    first_head_bytes = _head_path(root, session_id).read_bytes()
    retry = persist_problem_session(root, create, tuple(sorted((context, analysis), key=_sha)))
    if retry.status != "unchanged" or _head_path(root, session_id).read_bytes() != first_head_bytes:
        _fail("idempotent store retry changed committed HEAD")

    payload = _canonical(
        {"definition_id": "definition_store", "schema": "mathhead.definition-payload.v1"}
    )
    payload_sha = _sha(payload)
    link = make_session_artifact_link(
        payload,
        role="definition_payload",
        artifact_schema="mathhead.definition-payload.v1",
        context_sha256=context_sha,
    )
    record = make_session_definition(
        record_id="definition_store",
        generation=0,
        definition_id="definition_store",
        primary_artifact_sha256=payload_sha,
        problem_ir_sha256=analysis_sha,
        theory_context_sha256=context_sha,
        declaration_sha256="3" * 64,
    )
    update = make_problem_session_command(
        command_id="put_definition_store",
        kind="put_definition",
        session_id=session_id,
        expected_head_sha256=create_head,
        introduced_artifacts=(link,),
        record=record,
    )
    updated = persist_problem_session(root, update, (payload,))
    if updated.status != "updated" or updated.revision != 1:
        _fail(f"second store fixture failed: {updated.reason_code}")
    committed_head = _head_path(root, session_id).read_bytes()

    stale_record = make_session_definition(
        record_id="definition_stale",
        generation=0,
        definition_id="definition_stale",
        primary_artifact_sha256=payload_sha,
        problem_ir_sha256=analysis_sha,
        theory_context_sha256=context_sha,
        declaration_sha256="4" * 64,
    )
    stale = make_problem_session_command(
        command_id="stale_store_writer",
        kind="put_definition",
        session_id=session_id,
        expected_head_sha256=create_head,
        record=stale_record,
    )
    conflict = persist_problem_session(root, stale, ())
    if conflict.status != "conflict" or _head_path(root, session_id).read_bytes() != committed_head:
        _fail("stale writer did not preserve committed HEAD")

    session = _session_path(root, session_id)
    (session / ".writer-lock").write_bytes(b"abandoned\n")
    (session / ".mathhead-head-orphan").write_bytes(b"orphan\n")
    recovered = recover_problem_session_store(root, session_id)
    loaded = load_problem_session(root, session_id)
    if recovered.revision_value != updated.revision_value or loaded.revision_value != updated.revision_value:
        _fail("recovery/reopen differs from committed revision")
    if (session / ".writer-lock").exists() or (session / ".mathhead-head-orphan").exists():
        _fail("recovery left abandoned adapter temporaries")
    return {
        "artifacts": len(updated.artifacts or ()),
        "events": len(updated.events or ()),
        "head_event_sha256": updated.head_sha256,
        "idempotent_retry": True,
        "recovered": True,
        "revision": updated.revision,
        "session_id": session_id,
        "stale_conflict": True,
    }


def _session_path(root: Path, session_id: str) -> Path:
    key = _sha(session_id.encode())
    return root / "sessions" / key[:2] / key[2:]


def _head_path(root: Path, session_id: str) -> Path:
    return _session_path(root, session_id) / "HEAD"


def _inspect(root: Path, fixture: dict[str, object]) -> dict[str, object]:
    session_id = fixture["session_id"]
    assert isinstance(session_id, str)
    path = _head_path(root, session_id)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o222:
        _fail("committed HEAD is not a sealed single-link regular file")
    data = path.read_bytes()
    head = json.loads(data)
    if data != _canonical(head) or set(head) != HEAD_FIELDS:
        _fail("committed HEAD is not canonical and closed")
    if head["head_sha256"] != _self_hash(head, "head_sha256"):
        _fail("independent store HEAD identity drift")
    if head["schema"] != "mathhead.problem-session-store-head.v1":
        _fail("store HEAD schema drift")
    if head["store_contract_id"] != CONTRACT_ID or head["store_contract_sha256"] != CONTRACT_SHA256:
        _fail("store HEAD contract binding drift")
    if head["session_key_sha256"] != _sha(session_id.encode()):
        _fail("store session path identity drift")
    if head["mathematical_authority"] is not False:
        _fail("store HEAD claimed mathematical authority")
    event_ids = head["event_sha256s"]
    artifact_ids = head["artifact_sha256s"]
    if len(event_ids) != head["revision"] + 1 or artifact_ids != sorted(artifact_ids):
        _fail("store HEAD inventory/revision drift")
    total = 0
    events: list[dict[str, object]] = []
    for identity in (*event_ids, *artifact_ids):
        payload = _read_sealed(_object_path(root, identity), identity)
        total += len(payload)
        if identity in event_ids:
            event = json.loads(payload)
            if payload != _canonical(event) or event["event_sha256"] != _self_hash(event, "event_sha256"):
                _fail("stored event canonical/self identity drift")
            events.append(event)
    if [event["revision"] for event in events] != list(range(len(events))):
        _fail("stored event revision chain drift")
    if events[-1]["event_sha256"] != head["head_event_sha256"]:
        _fail("stored logical head differs from event chain")
    all_objects = tuple(
        sorted(
            path.name
            for fanout in (root / "objects").iterdir()
            for path in fanout.iterdir()
        )
    )
    for identity in all_objects:
        if len(identity) != 62:
            _fail("unexpected content-object path shape")
    return {
        "artifact_objects": len(artifact_ids),
        "committed_bytes": total,
        "event_objects": len(event_ids),
        "head_sha256": head["head_sha256"],
        "immutable_objects": len(all_objects),
        "revision_sha256": head["revision_sha256"],
    }


def _report() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="mathhead-session-store-validator-") as directory:
        root = Path(directory) / "store"
        fixture = _fixture(root)
        inspection = _inspect(root, fixture)
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "identity_checks": _identity_checks(),
        "inspection": inspection,
        "mathematical_authority": False,
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "source": _source_checks(),
        "status": "passed",
        "tests_sha256": _sha(
            (ROOT / "tests/problem_sessions/test_problem_sessions.py").read_bytes()
        ),
        "validator_sha256": _sha(
            (ROOT / "tools/validate_problem_session_store.py").read_bytes()
        ),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"problem-session-store: report updated: {target}")
        return
    try:
        current = target.read_bytes()
    except OSError as exc:
        _fail(f"frozen report missing: {path}: {exc}")
    if current != payload:
        _fail(f"frozen report drift: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write-report", type=Path)
    group.add_argument("--check-report", type=Path)
    args = parser.parse_args(argv)
    try:
        report = _report()
        path = args.write_report or args.check_report or DEFAULT_REPORT
        _write_or_check(report, path, write=args.write_report is not None)
    except (OSError, UnicodeError, ValueError, ProblemSessionStoreReportError) as exc:
        print(f"problem-session-store: FAIL: {exc}", file=sys.stderr)
        return 1
    fixture = report["fixture"]
    inspection = report["inspection"]
    assert isinstance(fixture, dict) and isinstance(inspection, dict)
    print(
        "problem-session-store: PASS "
        f"(revision={fixture['revision']}, events={inspection['event_objects']}, "
        f"artifacts={inspection['artifact_objects']}, objects={inspection['immutable_objects']}, "
        "retry=unchanged, stale=conflict, recovery=passed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
