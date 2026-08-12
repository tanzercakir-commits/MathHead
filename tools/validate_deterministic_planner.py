#!/usr/bin/env python3
"""Independently validate MH-C-DETERMINISTIC-PLANNER-001 output."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import deterministic_planner as production  # noqa: E402
from tests.deterministic_planner.fixtures import PlannerFixture  # noqa: E402


CONTRACT_ID = "MH-C-DETERMINISTIC-PLANNER-001"
CONTRACT_SHA256 = "72e3c39ea40c599cd709fff590a72bfd096450adbb80689ce934342c3aaaa124"
DEFAULT_REPORT = Path("docs/planning/reports/deterministic-planner-v1.json")
REPORT_SCHEMA = "mathhead.deterministic-planner-validation-report.v1"
INTEGER_MAXIMUM = 9_007_199_254_740_991
RESOURCE_DIMENSIONS = (
    "wall_time_us",
    "cpu_time_us",
    "memory_bytes",
    "solver_calls",
    "generated_objects",
    "proof_bytes",
    "evidence_bytes",
    "output_bytes",
    "diagnostic_bytes",
    "nesting_depth",
)
OUTCOMES = (
    "success",
    "unsupported",
    "exhausted",
    "cancelled",
    "producer_error",
    "ambiguous",
    "truncated",
    "checker_inconclusive",
    "checker_disagreement",
    "verifier_failure",
    "invalid_evidence",
)
RETRY_TERMINALS = {
    "unsupported": "unsupported",
    "producer_error": "failed",
    "ambiguous": "ambiguous",
    "truncated": "truncated",
    "checker_inconclusive": "inconclusive",
    "checker_disagreement": "disagreement",
    "invalid_evidence": "invalid_evidence",
}
STOP_TERMINALS = {
    "success": ("succeed", "succeeded"),
    "exhausted": ("stop", "exhausted"),
    "cancelled": ("stop", "cancelled"),
    "verifier_failure": ("stop", "verifier_failed"),
}
SCHEMAS = {
    "planning-policy-v1.schema.json": "fa0855768cb0445ab1f8ae67fe55a3851a500603a5757a9da099fe06a653b8f5",
    "planning-request-v1.schema.json": "2d8dff59cec10037f59506102c26f41eca21c0b963c968bcf2366b8dfcbff15a",
    "planning-prerequisite-v1.schema.json": "54dd128e23ed57fcf3996fae61c221dd918dfee72c9bb0f160927bf62c5a0499",
    "planning-evidence-expectation-v1.schema.json": "126c85466c7c0bcda1bf7b10f4a9cdeeacfd8597e1e04b24a08f4c2f39ed34ae",
    "planning-resource-request-v1.schema.json": "8f5833b632b99ddf626a7d1fdef03986310636466b34d2cd0633501ca8d94c91",
    "planning-transition-v1.schema.json": "2f63a40d420c823e5de9eb7fd4af4385dda801af296524ea0063a111a5dbb3f9",
    "planning-strategy-v1.schema.json": "ca712e4c5f17b58d476537d4658c35c558841378cf7a084ac53cff026a15e1c8",
    "planning-result-v1.schema.json": "f2e916f669f028eafca56551897e66371114a01f9aa2502e929d0aae90ff30be",
}


class DeterministicPlannerReportError(RuntimeError):
    """An independent planning identity or graph check failed."""


def _fail(detail: str) -> NoReturn:
    raise DeterministicPlannerReportError(detail)


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
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON for {label}: {exc}")
    if not isinstance(value, dict) or _canonical(value) != data:
        _fail(f"noncanonical object for {label}")
    return value


def _self_hash(value: dict[str, Any], field: str) -> str:
    basis = copy.deepcopy(value)
    basis[field] = None
    return _sha(_canonical(basis))


def _identity_checks() -> dict[str, object]:
    paths = {
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        **{Path("docs/contracts/schemas") / name: digest for name, digest in SCHEMAS.items()},
    }
    for path, expected in paths.items():
        if _sha((ROOT / path).read_bytes()) != expected:
            _fail(f"identity drift: {path}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed or accepted != _canonical(json.loads(accepted)):
        _fail("accepted and proposed contract byte binding drift")
    if production.CONTRACT_SHA256 != CONTRACT_SHA256:
        _fail("production contract binding drift")
    expected_bindings = {
        "mathhead.planning-policy.v1": SCHEMAS["planning-policy-v1.schema.json"],
        "mathhead.planning-request.v1": SCHEMAS["planning-request-v1.schema.json"],
        "mathhead.planning-prerequisite.v1": SCHEMAS[
            "planning-prerequisite-v1.schema.json"
        ],
        "mathhead.planning-evidence-expectation.v1": SCHEMAS[
            "planning-evidence-expectation-v1.schema.json"
        ],
        "mathhead.planning-resource-request.v1": SCHEMAS[
            "planning-resource-request-v1.schema.json"
        ],
        "mathhead.planning-transition.v1": SCHEMAS[
            "planning-transition-v1.schema.json"
        ],
        "mathhead.planning-strategy.v1": SCHEMAS[
            "planning-strategy-v1.schema.json"
        ],
        "mathhead.planning-result.v1": SCHEMAS["planning-result-v1.schema.json"],
    }
    if production.SCHEMA_SHA256S != expected_bindings:
        _fail("production schema binding drift")
    for name in SCHEMAS:
        schema = json.loads((ROOT / "docs/contracts/schemas" / name).read_bytes())
        if (
            schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
        ):
            _fail(f"schema root is not closed Draft 2020-12: {name}")
    return {"accepted_equals_proposed": True, "contract_bound": True, "schemas": 8}


def _source_checks() -> dict[str, object]:
    path = ROOT / "src/mathhead/deterministic_planner.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    allowed = {"__future__", "dataclasses", "hashlib", "json", "mathhead", "re", "typing", "unicodedata"}
    if not imports <= allowed:
        _fail(f"pure source import closure drift: {sorted(imports - allowed)}")
    forbidden = {
        "open",
        "exec",
        "eval",
        "__import__",
        "system",
        "popen",
        "getenv",
        "entry_points",
        "sleep",
    }
    if calls & forbidden:
        _fail(f"pure source gained effect calls: {sorted(calls & forbidden)}")
    return {"imports": sorted(imports), "sha256": _sha(path.read_bytes())}


def _saturated_multiply(value: int, factor: int) -> tuple[int, bool]:
    if value > INTEGER_MAXIMUM // factor:
        return INTEGER_MAXIMUM, True
    return value * factor, False


def _saturated_add(value: int, increment: int) -> tuple[int, bool]:
    if value > INTEGER_MAXIMUM - increment:
        return INTEGER_MAXIMUM, True
    return value + increment, False


def _resource_request(candidate: dict[str, Any], fragment: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    cost = candidate["cost"]["estimated_cost"]
    plus_one, add_saturated = _saturated_add(cost, 1)
    wall, wall_saturated = _saturated_multiply(cost, 1_000)
    cpu, cpu_saturated = _saturated_multiply(cost, 1_000)
    memory, memory_saturated = _saturated_multiply(plus_one, 1_024)
    proof, proof_saturated = _saturated_multiply(cost, 16)
    evidence, evidence_saturated = _saturated_multiply(cost, 16)
    output, output_saturated = _saturated_multiply(cost, 16)
    diagnostic, diagnostic_saturated = _saturated_multiply(cost, 4)
    nesting, nesting_saturated = _saturated_add(fragment["quantifier_depth"], 1)
    requested = {
        "wall_time_us": wall,
        "cpu_time_us": cpu,
        "memory_bytes": memory,
        "solver_calls": 1 if "solver" in candidate["effect_kinds"] else 0,
        "generated_objects": cost,
        "proof_bytes": proof,
        "evidence_bytes": evidence,
        "output_bytes": output,
        "diagnostic_bytes": min(diagnostic, 4_096),
        "nesting_depth": nesting,
    }
    flags = {
        "wall_time_us": wall_saturated,
        "cpu_time_us": cpu_saturated,
        "memory_bytes": add_saturated or memory_saturated,
        "solver_calls": False,
        "generated_objects": False,
        "proof_bytes": proof_saturated,
        "evidence_bytes": evidence_saturated,
        "output_bytes": output_saturated,
        "diagnostic_bytes": diagnostic_saturated,
        "nesting_depth": nesting_saturated,
    }
    value = {
        "schema": "mathhead.planning-resource-request.v1",
        "estimated_cost": cost,
        "requested": requested,
        "saturated_dimensions": [name for name in RESOURCE_DIMENSIONS if flags[name]],
        "fits_parent": all(requested[name] <= limits[name] for name in RESOURCE_DIMENSIONS),
        "resource_request_sha256": None,
        "mathematical_authority": False,
    }
    value["resource_request_sha256"] = _self_hash(value, "resource_request_sha256")
    return value


def _prerequisite(
    kind: str,
    digest: str,
    contract_id: str | None = None,
    artifact_schema: str | None = None,
) -> dict[str, Any]:
    value = {
        "schema": "mathhead.planning-prerequisite.v1",
        "kind": kind,
        "object_sha256": digest,
        "contract_id": contract_id,
        "artifact_schema": artifact_schema,
        "prerequisite_sha256": None,
        "mathematical_authority": False,
    }
    value["prerequisite_sha256"] = _self_hash(value, "prerequisite_sha256")
    return value


def _descriptor_parts(
    descriptor: dict[str, Any], candidate: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    operation = next(
        item for item in descriptor["operations"] if item["operation"] == candidate["operation"]
    )
    return operation, descriptor["components"], descriptor["compatibility"]


def _prerequisites(
    candidate: dict[str, Any],
    descriptor: dict[str, Any],
    route_request: dict[str, Any],
    route_digest: str,
) -> list[dict[str, Any]]:
    operation, components, compatibility = _descriptor_parts(descriptor, candidate)
    result = [
        _prerequisite("route", route_digest),
        _prerequisite("session_head", candidate["session_head_sha256"]),
        _prerequisite(
            "context", candidate["session_context_sha256"], artifact_schema="mathhead.theory-context.v1"
        ),
        _prerequisite(
            "normalization",
            candidate["normalization_result_sha256"],
            artifact_schema="mathhead.canonical-normalization-result.v1",
        ),
        _prerequisite(
            "obligation",
            route_request["obligation_artifact_sha256"],
            artifact_schema="mathhead.canonical-obligation.v1",
        ),
    ]
    compatibility_contracts = {
        item["contract_id"]: (item["sha256"], item["schema"])
        for item in compatibility["contracts"]
    }
    needed = set(operation["request_contract_ids"]) | set(operation["response_contract_ids"])
    contract_refs = {
        (contract_id, *compatibility_contracts[contract_id]) for contract_id in needed
    }
    for role in ("producer", "checker"):
        component = components[role]
        contract_refs.add(
            (component["contract_id"], component["contract_sha256"], None)
        )
    for contract_id, digest, schema in sorted(contract_refs):
        result.append(_prerequisite("contract", digest, contract_id, schema))
    for digest in sorted(candidate["dependency_descriptor_sha256s"]):
        result.append(
            _prerequisite(
                "descriptor_dependency", digest, artifact_schema="mathhead.theory-plugin.v1"
            )
        )
    return result


def _expectation(candidate: dict[str, Any], descriptor: dict[str, Any]) -> dict[str, Any]:
    operation, _components, _compatibility = _descriptor_parts(descriptor, candidate)
    authority = operation["authority"]
    value = {
        "schema": "mathhead.planning-evidence-expectation.v1",
        "operation_authority": authority,
        "producer_component_id": candidate["producer_component_id"],
        "checker_component_id": candidate["checker_component_id"],
        "evidence_contract_sha256": production.EVIDENCE_CONTRACT_SHA256,
        "certificate_contract_sha256": production.CERTIFICATE_CONTRACT_SHA256,
        "evidence_format": candidate["evidence_format"],
        "certificate_format": candidate["certificate_format"],
        "independent_check_required": authority == "producer_report",
        "expectation_sha256": None,
        "mathematical_authority": False,
    }
    value["expectation_sha256"] = _self_hash(value, "expectation_sha256")
    return value


def _transitions(next_strategy_sha256: str | None) -> list[dict[str, Any]]:
    result = []
    for outcome in OUTCOMES:
        if outcome in STOP_TERMINALS:
            action, terminal = STOP_TERMINALS[outcome]
            target = None
        elif next_strategy_sha256 is not None:
            action, terminal, target = "fallback", None, next_strategy_sha256
        else:
            action, terminal, target = "stop", RETRY_TERMINALS[outcome], None
        value = {
            "schema": "mathhead.planning-transition.v1",
            "outcome": outcome,
            "action": action,
            "target_strategy_sha256": target,
            "terminal_state": terminal,
            "transition_sha256": None,
            "mathematical_authority": False,
        }
        value["transition_sha256"] = _self_hash(value, "transition_sha256")
        result.append(value)
    return result


def _strategy(
    *,
    plan_order: int,
    route_order: int,
    candidate: dict[str, Any],
    descriptor: dict[str, Any],
    fragment: dict[str, Any],
    route_request: dict[str, Any],
    route_digest: str,
    limits: dict[str, int],
    next_strategy_sha256: str | None,
) -> dict[str, Any]:
    value = {
        "schema": "mathhead.planning-strategy.v1",
        "plan_order": plan_order,
        "route_order": route_order,
        "candidate_sha256": candidate["candidate_sha256"],
        "descriptor_sha256": candidate["descriptor_sha256"],
        "plugin_id": candidate["plugin_id"],
        "plugin_version": candidate["plugin_version"],
        "capability_id": candidate["capability_id"],
        "capability_kind": candidate["capability_kind"],
        "operation": candidate["operation"],
        "component_id": candidate["component_id"],
        "producer_component_id": candidate["producer_component_id"],
        "checker_component_id": candidate["checker_component_id"],
        "session_head_sha256": candidate["session_head_sha256"],
        "session_context_sha256": candidate["session_context_sha256"],
        "normalization_result_sha256": candidate["normalization_result_sha256"],
        "obligation_semantic_sha256": candidate["obligation_semantic_sha256"],
        "fragment_sha256": candidate["fragment_sha256"],
        "dependency_descriptor_sha256s": candidate["dependency_descriptor_sha256s"],
        "effect_kinds": candidate["effect_kinds"],
        "replay_mode": candidate["replay_mode"],
        "priority": candidate["priority"],
        "estimated_cost": candidate["cost"]["estimated_cost"],
        "cost_sha256": candidate["cost"]["cost_sha256"],
        "prerequisites": _prerequisites(
            candidate, descriptor, route_request, route_digest
        ),
        "evidence_expectation": _expectation(candidate, descriptor),
        "resource_request": _resource_request(candidate, fragment, limits),
        "transitions": _transitions(next_strategy_sha256),
        "strategy_sha256": None,
        "mathematical_authority": False,
    }
    value["strategy_sha256"] = _self_hash(value, "strategy_sha256")
    return value


def _expected_result(
    request: dict[str, Any],
    route: dict[str, Any],
    route_bytes: bytes,
    descriptors: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    indexed = list(enumerate(route["candidates"]))
    if request["policy"]["mode"] == "deterministic_first":
        replay_rank = {"deterministic": 0, "seeded": 1, "recorded": 2}
        indexed.sort(key=lambda pair: (replay_rank[pair[1]["replay_mode"]], pair[0]))
    strategies: list[dict[str, Any]] = []
    next_identity = None
    route_digest = _sha(route_bytes)
    for plan_order in range(len(indexed) - 1, -1, -1):
        route_order, candidate = indexed[plan_order]
        strategy = _strategy(
            plan_order=plan_order,
            route_order=route_order,
            candidate=candidate,
            descriptor=descriptors[candidate["descriptor_sha256"]],
            fragment=route["fragment"],
            route_request=request["route_request"],
            route_digest=route_digest,
            limits=request["resource_limits"],
            next_strategy_sha256=next_identity,
        )
        strategies.insert(0, strategy)
        next_identity = strategy["strategy_sha256"]
    value = {
        "schema": "mathhead.planning-result.v1",
        "contract_id": CONTRACT_ID,
        "contract_sha256": CONTRACT_SHA256,
        "capability_registry_contract_sha256": production.CAPABILITY_REGISTRY_CONTRACT_SHA256,
        "resource_budget_contract_sha256": production.RESOURCE_BUDGET_CONTRACT_SHA256,
        "engine_result_contract_sha256": production.ENGINE_RESULT_CONTRACT_SHA256,
        "evidence_contract_sha256": production.EVIDENCE_CONTRACT_SHA256,
        "certificate_contract_sha256": production.CERTIFICATE_CONTRACT_SHA256,
        "theory_plugin_contract_sha256": production.THEORY_PLUGIN_CONTRACT_SHA256,
        "status": "planned",
        "reason_code": "PLANNED",
        "diagnostic": "",
        "planning_request_sha256": request["request_sha256"],
        "route_result_sha256": request["route_result_sha256"],
        "policy_sha256": request["policy"]["policy_sha256"],
        "entry_strategy_sha256": strategies[0]["strategy_sha256"],
        "strategies": strategies,
        "result_sha256": None,
        "mathematical_authority": False,
    }
    value["result_sha256"] = _self_hash(value, "result_sha256")
    return value


def _fixture() -> tuple[dict[str, Any], dict[str, object]]:
    fixture = PlannerFixture()
    descriptor_tuple = fixture.descriptors(3)
    request_bytes, route_bytes, descriptors_raw, artifacts = fixture.planning_inputs(
        descriptor_tuple
    )
    result = production.plan_strategies(
        request_bytes, route_bytes, descriptors_raw, artifacts
    )
    result_bytes = production.planning_result_bytes(result)
    request = _load(request_bytes, "planning request")
    route = _load(route_bytes, "route result")
    actual = _load(result_bytes, "planning result")
    if request["policy"]["policy_sha256"] != _self_hash(
        request["policy"], "policy_sha256"
    ):
        _fail("policy identity drift")
    if request["request_sha256"] != _self_hash(request, "request_sha256"):
        _fail("planning request identity drift")
    if request["route_result_sha256"] != _sha(route_bytes):
        _fail("route byte binding drift")
    descriptors = {_sha(data): _load(data, "descriptor") for data in descriptors_raw}
    expected = _expected_result(request, route, route_bytes, descriptors)
    if actual != expected:
        _fail("independent complete planning reconstruction drift")
    if [item["route_order"] for item in actual["strategies"]] != list(
        range(len(actual["strategies"]))
    ):
        _fail("registry order drift")
    for index, strategy in enumerate(actual["strategies"]):
        if [item["outcome"] for item in strategy["transitions"]] != list(OUTCOMES):
            _fail("transition coverage or order drift")
        targets = {
            item["target_strategy_sha256"]
            for item in strategy["transitions"]
            if item["action"] == "fallback"
        }
        expected_targets = (
            {actual["strategies"][index + 1]["strategy_sha256"]}
            if index + 1 < len(actual["strategies"])
            else set()
        )
        if targets != expected_targets:
            _fail("fallback reachability drift")
    return actual, {
        "candidates": len(route["candidates"]),
        "entry_strategy_sha256": actual["entry_strategy_sha256"],
        "result_sha256": actual["result_sha256"],
        "status": actual["status"],
        "strategies": len(actual["strategies"]),
        "transitions": sum(len(item["transitions"]) for item in actual["strategies"]),
    }


def _negative_checks() -> int:
    fixture = PlannerFixture()
    descriptors = fixture.descriptors(2)
    inputs = fixture.planning_inputs(descriptors)
    request, route, descriptor_tuple, artifacts = inputs
    controls = [
        production.plan_strategies(request.rstrip(b"\n"), route, descriptor_tuple, artifacts),
        production.plan_strategies(request, route, descriptor_tuple, artifacts[:-1]),
        production.plan_strategies(request, route, descriptor_tuple[:-1], artifacts),
    ]
    low_limits = {name: 0 for name in RESOURCE_DIMENSIONS}
    controls.append(production.plan_strategies(*fixture.planning_inputs(limits=low_limits)))
    controls.append(
        production.plan_strategies(
            *fixture.planning_inputs(descriptors, maximum_strategies=1)
        )
    )
    if any(
        item.status not in {"invalid", "exhausted"}
        or item.strategies
        or item.result_sha256 is not None
        for item in controls
    ):
        _fail("negative control leaked a partial or reusable plan")
    return len(controls)


def _fingerprint() -> str:
    value, _fixture_data = _fixture()
    return _sha(_canonical(value))


def _determinism_checks() -> dict[str, object]:
    fingerprints = []
    for seed in ("1", "8675309"):
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        completed = subprocess.run(
            [sys.executable, __file__, "--fingerprint"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode:
            _fail(
                f"determinism child failed for hash seed {seed}: {completed.stderr.strip()}"
            )
        fingerprints.append(completed.stdout.strip())
    if len(set(fingerprints)) != 1:
        _fail("hash-seed determinism drift")
    return {"hash_seeds": 2, "result_bytes_sha256": fingerprints[0]}


def _report() -> dict[str, object]:
    _value, fixture = _fixture()
    report: dict[str, object] = {
        "contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256},
        "determinism": _determinism_checks(),
        "fixture": fixture,
        "identity_checks": _identity_checks(),
        "mathematical_authority": False,
        "negative_controls": _negative_checks(),
        "report_sha256": "",
        "schema": REPORT_SCHEMA,
        "schemas": SCHEMAS,
        "source": _source_checks(),
        "status": "passed",
        "tests_sha256": _sha(
            (ROOT / "tests/deterministic_planner/test_deterministic_planner.py").read_bytes()
        ),
        "validator_sha256": _sha(
            (ROOT / "tools/validate_deterministic_planner.py").read_bytes()
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
        print(f"deterministic-planner: report updated: {target}")
        return
    if not target.is_file() or target.read_bytes() != payload:
        _fail(f"frozen report drift or missing: {path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write-report", type=Path)
    group.add_argument("--check-report", type=Path)
    group.add_argument("--fingerprint", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.fingerprint:
            print(_fingerprint())
            return 0
        report = _report()
        path = args.write_report or args.check_report or DEFAULT_REPORT
        _write_or_check(report, path, write=args.write_report is not None)
    except (OSError, UnicodeError, ValueError, DeterministicPlannerReportError) as exc:
        print(f"deterministic-planner: FAIL: {exc}", file=sys.stderr)
        return 1
    fixture = report["fixture"]
    assert isinstance(fixture, dict)
    print(
        "deterministic-planner: PASS "
        f"(strategies={fixture['strategies']}, transitions={fixture['transitions']}, "
        f"negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
