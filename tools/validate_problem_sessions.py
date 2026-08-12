#!/usr/bin/env python3
"""Independently validate the MH-046 pure problem-session boundary."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import problem_sessions as production  # noqa: E402


CONTRACT_ID = "MH-C-PROBLEM-SESSION-001"
CONTRACT_SHA256 = "822f72c9f41f583e4e0535e83b9dbb10954202acc820192e52eab48a5c2d9c0a"
DEFAULT_REPORT = Path("docs/sessions/reports/problem-sessions-v1.json")
REPORT_SCHEMA = "mathhead.problem-session-validation-report.v1"
SCHEMAS = {
    "problem-session-artifact-link-v1.schema.json": "562faa38159bc98c4a1fb37c107afc20b933244b7f1cd3257b63c80f849a4133",
    "problem-session-attempt-v1.schema.json": "e14f6d0a9d1711bca56bfd195430eb081a58a5718c8c987bc7823df5beeeeb4b",
    "problem-session-command-v1.schema.json": "f395dfd35e14d88b5fd8a8b92613b1fcc355f8d72332483425774e2a8feceac1",
    "problem-session-definition-v1.schema.json": "d00d200ce97494b08ed7fc1b6b7d32f805f4a6c8ec4bd20d942fa426d586bb46",
    "problem-session-event-v1.schema.json": "983be63a2ee1096b8e9f550f0c3d3a1fe49fdaab64565927b6fd66e4b2247582",
    "problem-session-invalidation-v1.schema.json": "fd8dccac3d9437dafdba236d7d40619779661bd32eebbc204da8b08500b6700b",
    "problem-session-lemma-v1.schema.json": "79a446b77cb45f80eded2af13fda66daccc7445bf817161b2eaa6ab1debd6095",
    "problem-session-obligation-state-v1.schema.json": "150c0dfb2649fceb7057cd607e17bf8910ba13ffd97c7a1449995d30847c742e",
    "problem-session-result-v1.schema.json": "4d06b76fb9cca2e646c0a7b95a49d6926b83bf70b54246a40417d9667ba9cd53",
    "problem-session-revision-v1.schema.json": "02b89fd663f6506a6d993900635acb5ac0cd2c283b2f9d0994378e2d35882311",
    "problem-session-store-head-v1.schema.json": "a5bed15dda9e8c229687f1a89ba1ca9770e17d72314d16b5de63417472f3f683",
}
ALLOWED_IMPORTS = {
    "__future__", "dataclasses", "hashlib", "json", "re", "typing", "unicodedata",
}


class ProblemSessionReportError(RuntimeError):
    """An independent contract, replay, dependency, or identity check failed."""


def _fail(detail: str) -> NoReturn:
    raise ProblemSessionReportError(detail)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode()


def _self_hash(value: dict[str, Any], field: str) -> str:
    copy = dict(value)
    copy[field] = None
    return _sha(_canonical(copy))


def _identity_checks() -> dict[str, object]:
    expected = {
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        **{
            Path("docs/contracts/schemas") / name: digest
            for name, digest in SCHEMAS.items()
        },
    }
    for path, digest in expected.items():
        if _sha((ROOT / path).read_bytes()) != digest:
            _fail(f"identity drift: {path}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed or accepted != _canonical(json.loads(accepted)):
        _fail("accepted/proposed contract canonical binding drift")
    manifest = (ROOT / "docs/contracts/manifest.toml").read_text()
    binding = (
        f'id = "{CONTRACT_ID}"\n'
        f'path = "docs/contracts/{CONTRACT_ID}.json"\n'
        f'sha256 = "{CONTRACT_SHA256}"\n'
        'state = "accepted"'
    )
    if manifest.count(binding) != 1:
        _fail("accepted manifest binding drift")
    if production.PROBLEM_SESSION_CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract binding drift")
    for name in SCHEMAS:
        schema = json.loads((ROOT / "docs/contracts/schemas" / name).read_bytes())
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail(f"schema root is not closed Draft 2020-12: {name}")
    return {
        "accepted_equals_proposed": True,
        "contract_bound": True,
        "schemas": len(SCHEMAS),
    }


def _source_checks() -> dict[str, object]:
    path = ROOT / "src/mathhead/problem_sessions.py"
    tree = ast.parse(path.read_text())
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    if not imports <= ALLOWED_IMPORTS:
        _fail(f"pure source import closure drift: {sorted(imports - ALLOWED_IMPORTS)}")
    forbidden = {"open", "exec", "eval", "__import__", "system", "run", "getenv"}
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if calls & forbidden:
        _fail(f"pure source gained forbidden effect calls: {sorted(calls & forbidden)}")
    return {"imports": sorted(imports), "sha256": _sha(path.read_bytes())}


def _fixture() -> tuple[production.ProblemSessionResult, dict[str, bytes]]:
    context = _canonical({"context_id": "ctx_validator", "schema": "mathhead.theory-context.v1"})
    analysis = _canonical({"schema": "mathhead.canonical-normalization-result.v1", "status": "normalized"})
    context_sha, analysis_sha = _sha(context), _sha(analysis)
    payloads = {context_sha: context, analysis_sha: analysis}
    context_link = production.make_session_artifact_link(
        context,
        role="context",
        artifact_schema="mathhead.theory-context.v1",
        context_sha256=context_sha,
    )
    analysis_link = production.make_session_artifact_link(
        analysis,
        role="problem_analysis",
        artifact_schema="mathhead.canonical-normalization-result.v1",
        context_sha256=context_sha,
    )
    create = production.make_problem_session_command(
        command_id="create_validator",
        kind="create_session",
        session_id="session_validator",
        context_sha256=context_sha,
        analysis_artifact_sha256s=(analysis_sha,),
        introduced_artifacts=tuple(
            sorted((context_link, analysis_link), key=lambda item: item.sha256)
        ),
    )
    def artifacts() -> tuple[bytes, ...]:
        return tuple(payloads[key] for key in sorted(payloads))

    result = production.transition_problem_session(create, (), artifacts())
    definition_payload = _canonical(
        {"definition_id": "definition_validator", "schema": "mathhead.definition-payload.v1", "v": 0}
    )
    payloads[_sha(definition_payload)] = definition_payload
    link = production.make_session_artifact_link(
        definition_payload,
        role="definition_payload",
        artifact_schema="mathhead.definition-payload.v1",
        context_sha256=context_sha,
    )
    definition = production.make_session_definition(
        record_id="definition_validator",
        generation=0,
        definition_id="definition_validator",
        primary_artifact_sha256=_sha(definition_payload),
        problem_ir_sha256=analysis_sha,
        theory_context_sha256=context_sha,
        declaration_sha256="1" * 64,
    )
    command = production.make_problem_session_command(
        command_id="put_definition_0",
        kind="put_definition",
        session_id="session_validator",
        expected_head_sha256=result.head_sha256,
        introduced_artifacts=(link,),
        record=definition,
    )
    result = production.transition_problem_session(command, result.events, artifacts())
    obligation_payload = _canonical(
        {"obligation_id": "obligation_validator", "schema": "mathhead.canonical-obligation.v1"}
    )
    payloads[_sha(obligation_payload)] = obligation_payload
    obligation_link = production.make_session_artifact_link(
        obligation_payload,
        role="obligation",
        artifact_schema="mathhead.canonical-obligation.v1",
        context_sha256=context_sha,
        reading_id="reading_validator",
    )
    obligation = production.make_session_obligation(
        record_id="obligation_validator",
        generation=0,
        obligation_id="obligation_validator",
        obligation_sha256=_sha(obligation_payload),
        context_sha256=context_sha,
        reading_id="reading_validator",
        depends_on_record_sha256s=(definition.record_sha256,),
    )
    command = production.make_problem_session_command(
        command_id="put_obligation_0",
        kind="put_obligation",
        session_id="session_validator",
        expected_head_sha256=result.head_sha256,
        introduced_artifacts=(obligation_link,),
        record=obligation,
    )
    result = production.transition_problem_session(command, result.events, artifacts())
    replacement_payload = _canonical(
        {"definition_id": "definition_validator", "schema": "mathhead.definition-payload.v1", "v": 1}
    )
    payloads[_sha(replacement_payload)] = replacement_payload
    replacement_link = production.make_session_artifact_link(
        replacement_payload,
        role="definition_payload",
        artifact_schema="mathhead.definition-payload.v1",
        context_sha256=context_sha,
    )
    replacement = production.make_session_definition(
        record_id="definition_validator",
        generation=1,
        definition_id="definition_validator",
        primary_artifact_sha256=_sha(replacement_payload),
        problem_ir_sha256=analysis_sha,
        theory_context_sha256=context_sha,
        declaration_sha256="2" * 64,
    )
    command = production.make_problem_session_command(
        command_id="put_definition_1",
        kind="put_definition",
        session_id="session_validator",
        expected_head_sha256=result.head_sha256,
        introduced_artifacts=(replacement_link,),
        record=replacement,
    )
    result = production.transition_problem_session(command, result.events, artifacts())
    if result.status != "updated":
        _fail(f"production fixture failed: {result.reason_code}")
    return result, payloads


def _verify_fixture(result: production.ProblemSessionResult, payloads: dict[str, bytes]) -> dict[str, object]:
    if result.events is None or result.artifacts is None or result.revision_value is None:
        _fail("fixture returned partial successful state")
    if tuple(_sha(item) for item in result.artifacts) != tuple(sorted(payloads)):
        _fail("fixture artifact inventory drift")
    current: dict[str, dict[str, Any]] = {}
    stale: list[str] = []
    retired: list[str] = []
    invalidation_ids: list[str] = []
    artifact_ids: set[str] = set()
    event_ids: list[str] = []
    context: str | None = None
    analysis: list[str] = []
    parent: str | None = None
    for revision, raw in enumerate(result.events):
        if raw != _canonical(json.loads(raw)):
            _fail("noncanonical event bytes")
        event = json.loads(raw)
        command = event["command"]
        if command["command_sha256"] != _self_hash(command, "command_sha256"):
            _fail("independent command identity drift")
        if event["event_sha256"] != _self_hash(event, "event_sha256"):
            _fail("independent event identity drift")
        if event["revision"] != revision or event["parent_event_sha256"] != parent:
            _fail("independent event chain drift")
        links = command["introduced_artifacts"]
        if event["introduced_artifact_sha256s"] != [item["sha256"] for item in links]:
            _fail("event introduced inventory drift")
        for link in links:
            identity = link["sha256"]
            data = payloads.get(identity)
            if data is None or len(data) != link["bytes"] or _sha(data) != identity:
                _fail("independent artifact link mismatch")
            artifact_ids.add(identity)
        kind = command["kind"]
        if kind == "create_session":
            context = command["context_sha256"]
            analysis = command["analysis_artifact_sha256s"]
        else:
            record = command["record"]
            schema = record["schema"]
            if schema not in {
                "mathhead.problem-session-definition.v1",
                "mathhead.problem-session-obligation-state.v1",
            }:
                _fail(f"unexpected fixture record schema: {schema}")
            if record["record_sha256"] != _self_hash(record, "record_sha256"):
                _fail("independent record identity drift")
            prior = current.get(record["record_id"])
            expected_targets: list[str] = []
            if prior is not None:
                expected_targets.append(prior["record_sha256"])
                expected_targets.extend(
                    item["record_sha256"]
                    for item in current.values()
                    if prior["record_sha256"] in item["depends_on_record_sha256s"]
                )
            actual_targets = [item["target_record_sha256"] for item in event["invalidations"]]
            if sorted(actual_targets) != sorted(expected_targets):
                _fail("independent invalidation closure drift")
            for item in event["invalidations"]:
                if item["invalidation_sha256"] != _self_hash(item, "invalidation_sha256"):
                    _fail("independent invalidation identity drift")
                invalidation_ids.append(item["invalidation_sha256"])
                stale.append(item["target_record_sha256"])
                current = {
                    key: value
                    for key, value in current.items()
                    if value["record_sha256"] != item["target_record_sha256"]
                }
            current[record["record_id"]] = record
        view = {
            "analysis_artifact_sha256s": analysis,
            "artifact_sha256s": sorted(artifact_ids),
            "attempts": sorted(
                (item for item in current.values() if item["schema"].endswith("attempt.v1")),
                key=lambda item: item["record_id"],
            ),
            "context_sha256": context,
            "definitions": sorted(
                (item for item in current.values() if item["schema"].endswith("definition.v1")),
                key=lambda item: item["record_id"],
            ),
            "invalidation_sha256s": invalidation_ids,
            "lemmas": sorted(
                (item for item in current.values() if item["schema"].endswith("lemma.v1")),
                key=lambda item: item["record_id"],
            ),
            "obligations": sorted(
                (item for item in current.values() if item["schema"].endswith("obligation-state.v1")),
                key=lambda item: item["record_id"],
            ),
            "retired_record_sha256s": retired,
            "revision": revision,
            "session_id": "session_validator",
            "stale_record_sha256s": stale,
        }
        if event["view_sha256"] != _sha(_canonical(view)):
            _fail("independent view identity drift")
        parent = event["event_sha256"]
        event_ids.append(parent)
    revision = json.loads(production.session_component_to_bytes(result.revision_value))
    if revision["revision_sha256"] != _self_hash(revision, "revision_sha256"):
        _fail("independent revision identity drift")
    if revision["event_sha256s"] != event_ids or revision["head_event_sha256"] != parent:
        _fail("revision event inventory drift")
    if revision["stale_record_sha256s"] != stale:
        _fail("revision stale history drift")
    return {
        "artifacts": len(payloads),
        "current_records": len(current),
        "events": len(result.events),
        "head_sha256": result.head_sha256,
        "invalidations": len(invalidation_ids),
        "revision_sha256": result.revision_value.revision_sha256,
        "stale_records": len(stale),
        "view_sha256": result.view_sha256,
    }


def _negative_checks(result: production.ProblemSessionResult) -> int:
    assert result.events is not None and result.artifacts is not None
    controls = [
        production.transition_problem_session(None, (), ()),
        production.transition_problem_session(None, result.events, result.artifacts[:-1]),
        production.transition_problem_session(None, result.events, tuple(reversed(result.artifacts))),
        production.transition_problem_session(None, result.events[:-1], result.artifacts),
        production.transition_problem_session(b"{}\n", result.events, result.artifacts),
        production.transition_problem_session(None, (result.events[0][:-1],), result.artifacts),
    ]
    if any(item.status not in {"invalid", "exhausted"} for item in controls):
        _fail("negative control produced a successful or conflicting state")
    if any(item.head_sha256 is not None or item.revision_value is not None for item in controls):
        _fail("negative control leaked partial session state")
    return len(controls)


def _report() -> dict[str, object]:
    result, payloads = _fixture()
    fixture = _verify_fixture(result, payloads)
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "fixture": fixture,
        "identity_checks": _identity_checks(),
        "mathematical_authority": False,
        "negative_controls": _negative_checks(result),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schemas": SCHEMAS,
        "source": _source_checks(),
        "status": "passed",
        "tests_sha256": _sha(
            (ROOT / "tests/problem_sessions/test_problem_sessions.py").read_bytes()
        ),
        "validator_sha256": _sha((ROOT / "tools/validate_problem_sessions.py").read_bytes()),
    }
    report["report_sha256"] = _sha(_canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = _canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"problem-sessions: report updated: {target}")
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
    except (OSError, UnicodeError, ValueError, ProblemSessionReportError) as exc:
        print(f"problem-sessions: FAIL: {exc}", file=sys.stderr)
        return 1
    fixture = report["fixture"]
    assert isinstance(fixture, dict)
    print(
        "problem-sessions: PASS "
        f"(events={fixture['events']}, artifacts={fixture['artifacts']}, "
        f"current={fixture['current_records']}, stale={fixture['stale_records']}, "
        f"invalidations={fixture['invalidations']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
