#!/usr/bin/env python3
"""Independent static validator for MH-C-PROOF-SEARCH-PORTFOLIO-001.

This validator deliberately does not import the production portfolio module.
It rebinds contract and schema bytes, inspects the source AST, and emits one
stable report after the production boundary exists.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ID = "MH-C-PROOF-SEARCH-PORTFOLIO-001"
CONTRACT_PATH = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
SOURCE_PATH = ROOT / "src/mathhead/proof_search_portfolio.py"
REPORT_PATH = ROOT / "docs/planning/reports/proof-search-portfolio-v1.json"
SCHEMA_NAMES = (
    "portfolio-execution-binding-v1.schema.json",
    "proof-search-portfolio-request-v1.schema.json",
    "portfolio-checker-decision-v1.schema.json",
    "portfolio-attempt-v1.schema.json",
    "portfolio-inconclusive-v1.schema.json",
    "proof-search-portfolio-result-v1.schema.json",
)
SCHEMA_SHA256S = {
    "mathhead.portfolio-execution-binding.v1": "ab39704148ac4de4489dc68b08b726a696a7794db4543b891ad311ec5b594e65",
    "mathhead.proof-search-portfolio-request.v1": "61d8d774612de377715e881806a3de8c57a03ee631c50c24400d322ff15a32bd",
    "mathhead.portfolio-checker-decision.v1": "88ab41ac83589290879d390bf4c711583b0366297b2435b73d0208a7ce09f15c",
    "mathhead.portfolio-attempt.v1": "fc12eb424c86d938282fed47ae814f03b9970b32642ccaee3c7226086abf0158",
    "mathhead.portfolio-inconclusive.v1": "4a2a98d58dfb4182b96b4bcafc01fd95292a1da9e7e8cb29eaa8d36cb784b8c1",
    "mathhead.proof-search-portfolio-result.v1": "336d3b09259e119cd37fa3ffcf2405a6806827adc59edecab4c3dc29030fb99c",
}
RESOURCE_DIMENSIONS = (
    "wall_time_us", "cpu_time_us", "memory_bytes", "solver_calls",
    "generated_objects", "proof_bytes", "evidence_bytes", "output_bytes",
    "diagnostic_bytes", "nesting_depth",
)


class PortfolioValidationError(RuntimeError):
    pass


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw)
    if type(value) is not dict:
        raise PortfolioValidationError(f"object required: {path}")
    return value, raw


def _self_hash(value: dict[str, Any], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


_CHILD = r'''import base64, json, tempfile
from pathlib import Path
from tests.proof_search_portfolio.fixtures import FallbackPortfolioFixture, PortfolioFixture
from mathhead.proof_search_portfolio import (
    proof_search_portfolio_budget_bytes,
    proof_search_portfolio_result_bytes,
    proof_search_portfolio_selected_bytes,
    proof_search_portfolio_semantic_bytes,
    run_portfolio,
)

def enc(value):
    return base64.b64encode(value).decode("ascii")

root = Path.cwd()

def capture(fixture):
  with tempfile.TemporaryDirectory(dir=root) as directory:
    result = run_portfolio(
        fixture.request,
        fixture.plan_bytes,
        fixture.parent,
        fixture.descriptors if hasattr(fixture, "descriptors") else (fixture.descriptor,),
        fixture.bindings if hasattr(fixture, "bindings") else (fixture.binding,),
        tuple(raw for _, raw in fixture.input_pairs),
        fixture.executable_paths,
        directory,
    )
    return {
        "request": enc(fixture.request),
        "plan": enc(fixture.plan_bytes),
        "parent": enc(fixture.parent),
        "descriptors": [enc(item) for item in (fixture.descriptors if hasattr(fixture, "descriptors") else (fixture.descriptor,))],
        "bindings": [enc(item) for item in (fixture.bindings if hasattr(fixture, "bindings") else (fixture.binding,))],
        "artifacts": [enc(raw) for _, raw in fixture.input_pairs],
        "result": enc(proof_search_portfolio_result_bytes(result)),
        "semantic": enc(proof_search_portfolio_semantic_bytes(result)),
        "final_parent": enc(proof_search_portfolio_budget_bytes(result)),
        "selected_evidence": enc(proof_search_portfolio_selected_bytes(result, "evidence")) if result.status == "succeeded" else "",
        "selected_certificate": enc(proof_search_portfolio_selected_bytes(result, "certificate")) if result.status == "succeeded" else "",
    }

primary = PortfolioFixture()
payload = capture(primary)
payload["checker_envelope"] = enc(primary.envelope)
payload["fallback"] = capture(FallbackPortfolioFixture())
print(json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")))
'''


def _runtime_sample(seed: str) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    import_roots = (str(ROOT / "src"), str(ROOT))
    inherited_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        (*import_roots, inherited_pythonpath)
        if inherited_pythonpath
        else import_roots
    )
    completed = subprocess.run(
        [sys.executable, "-c", _CHILD],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", "replace").strip()
        raise PortfolioValidationError(f"runtime fixture failed: {detail}")
    try:
        value = json.loads(completed.stdout)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PortfolioValidationError("runtime fixture output is not JSON") from exc
    if type(value) is not dict:
        raise PortfolioValidationError("runtime fixture output must be an object")
    return value


def _canonical_object(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PortfolioValidationError(f"{name} is not JSON") from exc
    if type(value) is not dict or raw != _canonical(value):
        raise PortfolioValidationError(f"{name} is not canonical")
    return value


def _verify_ledger(events: object, invocation_count: int) -> None:
    if type(events) is not list:
        raise PortfolioValidationError("parent ledger events are not an array")
    expected_kinds = [kind for _ in range(invocation_count) for kind in ("reserve", "sample", "reconcile")]
    if (
        [item.get("sequence") for item in events] != list(range(len(events)))
        or [item.get("kind") for item in events] != expected_kinds
    ):
        raise PortfolioValidationError("parent ledger event sequence differs")
    leases: set[str] = set()
    child_ids: set[str] = set()
    for offset in range(0, len(events), 3):
        reserve, _, reconcile = events[offset:offset + 3]
        lease = reserve["lease_id"]
        child_id = reserve["child_budget_id"]
        if lease in leases or child_id in child_ids or reconcile["lease_id"] != lease:
            raise PortfolioValidationError("lease identity was reused or mismatched")
        leases.add(lease)
        child_ids.add(child_id)
        usage = reconcile["child_usage"]
        observed_names = {"memory_bytes": "memory_peak_bytes", "nesting_depth": "nesting_peak"}
        for name in RESOURCE_DIMENSIONS:
            observed = usage[observed_names.get(name, name)]
            if (
                observed + reconcile["refund"][name] != reserve["allocation"][name]
                or reconcile["overrun"][name] != 0
            ):
                raise PortfolioValidationError(f"ledger arithmetic differs for {name}")


def _verify_runtime(sample: dict[str, Any]) -> dict[str, Any]:
    request_raw = _decode(sample["request"])
    plan_raw = _decode(sample["plan"])
    parent_raw = _decode(sample["parent"])
    descriptor_raws = tuple(_decode(item) for item in sample["descriptors"])
    binding_raws = tuple(_decode(item) for item in sample["bindings"])
    artifact_raws = tuple(_decode(item) for item in sample["artifacts"])
    result_raw = _decode(sample["result"])
    final_parent_raw = _decode(sample["final_parent"])
    evidence_raw = _decode(sample["selected_evidence"])
    certificate_raw = _decode(sample["selected_certificate"])
    envelope_raw = _decode(sample["checker_envelope"])
    request = _canonical_object(request_raw, "request")
    plan = _canonical_object(plan_raw, "plan")
    result = _canonical_object(result_raw, "result")
    final_parent = _canonical_object(final_parent_raw, "final parent budget")

    if request["request_sha256"] != _self_hash(request, "request_sha256"):
        raise PortfolioValidationError("request identity was not independently reconstructed")
    if request["planning_result_sha256"] != _sha(plan_raw) or request["parent_budget_sha256"] != _sha(parent_raw):
        raise PortfolioValidationError("request plan or parent binding differs")
    if request["descriptor_sha256s"] != sorted(_sha(item) for item in descriptor_raws):
        raise PortfolioValidationError("request descriptor closure differs")
    if request["binding_sha256s"] != [_sha(item) for item in binding_raws]:
        raise PortfolioValidationError("request binding closure differs")
    expected_artifacts = [
        {"role": item["role"], "sha256": _sha(raw), "bytes": len(raw)}
        for item, raw in zip(request["artifact_bindings"], artifact_raws)
    ]
    if request["artifact_bindings"] != expected_artifacts:
        raise PortfolioValidationError("request artifact closure differs")

    strategies = plan["strategies"]
    if plan["status"] != "planned" or not strategies or plan["entry_strategy_sha256"] != strategies[0]["strategy_sha256"]:
        raise PortfolioValidationError("runtime plan is not one exact reachable graph")
    if len(binding_raws) != len(strategies):
        raise PortfolioValidationError("runtime binding count differs from plan")
    for index, (raw, strategy) in enumerate(zip(binding_raws, strategies)):
        binding = _canonical_object(raw, f"binding {index}")
        if binding["binding_sha256"] != _self_hash(binding, "binding_sha256"):
            raise PortfolioValidationError("binding identity differs")
        expected = (
            binding["plan_order"] == strategy["plan_order"] == index
            and binding["strategy_sha256"] == strategy["strategy_sha256"]
            and binding["descriptor_sha256"] == strategy["descriptor_sha256"]
            and binding["producer_component_id"] == strategy["producer_component_id"]
            and binding["checker_component_id"] == strategy["checker_component_id"]
            and binding["producer_component_id"] != binding["checker_component_id"]
        )
        if not expected:
            raise PortfolioValidationError("binding and strategy identities differ")

    if result["result_sha256"] != _self_hash(result, "result_sha256"):
        raise PortfolioValidationError("result identity was not independently reconstructed")
    if (
        result["request_sha256"] != request["request_sha256"]
        or result["planning_result_sha256"] != _sha(plan_raw)
        or result["initial_parent_budget_sha256"] != _sha(parent_raw)
        or result["final_parent_budget_sha256"] != _sha(final_parent_raw)
        or result["mathematical_authority"] is not False
    ):
        raise PortfolioValidationError("terminal result input or ledger bindings differ")
    attempts = result["attempts"]
    if result["status"] == "unsupported":
        if (
            result["mathematical_verdict"] != "inconclusive"
            or result["authority_tier"] != "none"
            or len(attempts) != 1
            or attempts[0]["outcome"] != "unsupported"
            or attempts[0]["producer_status"] != "unsupported"
            or attempts[0]["checker_status"] != "not_started"
            or len(result["inconclusive_outcomes"]) != 1
            or final_parent_raw != parent_raw
            or evidence_raw
            or certificate_raw
        ):
            raise PortfolioValidationError("unsupported containment did not fail closed")
        attempt = attempts[0]
        if attempt["attempt_sha256"] != _self_hash(attempt, "attempt_sha256"):
            raise PortfolioValidationError("unsupported attempt identity differs")
        strategy = strategies[0]
        transition = next(item for item in strategy["transitions"] if item["outcome"] == "unsupported")
        if transition["transition_sha256"] != attempt["transition_sha256"]:
            raise PortfolioValidationError("unsupported transition differs")
        return {
            "semantic": _decode(sample["semantic"]),
            "producer_identity": attempt["producer_worker_result_sha256"],
            "checker_identity": None,
        }
    evidence = _canonical_object(evidence_raw, "selected Evidence")
    certificate = _canonical_object(certificate_raw, "selected Certificate")
    envelope = _canonical_object(envelope_raw, "checker envelope")
    if (
        result["status"] != "succeeded"
        or result["mathematical_verdict"] != "proved"
        or result["authority_tier"] != "checker_attestation"
    ):
        raise PortfolioValidationError("checked terminal result fields differ")
    if len(attempts) != 1 or result["inconclusive_outcomes"]:
        raise PortfolioValidationError("successful runtime attempt inventory differs")
    for index, attempt in enumerate(attempts):
        if attempt["attempt_sha256"] != _self_hash(attempt, "attempt_sha256") or attempt["attempt_order"] != index:
            raise PortfolioValidationError("attempt identity or order differs")
        strategy = next(item for item in strategies if item["strategy_sha256"] == attempt["strategy_sha256"])
        transition = next(item for item in strategy["transitions"] if item["outcome"] == attempt["outcome"])
        if transition["transition_sha256"] != attempt["transition_sha256"] or transition["action"] != "succeed":
            raise PortfolioValidationError("attempt did not follow its exact planner transition")
        if attempt["parent_budget_before_sha256"] != _sha(parent_raw) or attempt["parent_budget_after_sha256"] != _sha(final_parent_raw):
            raise PortfolioValidationError("attempt ledger chain differs")

    decision = envelope["decision"]
    if decision["decision_sha256"] != _self_hash(decision, "decision_sha256"):
        raise PortfolioValidationError("checker decision identity differs")
    if envelope["certificate"] != certificate:
        raise PortfolioValidationError("selected Certificate differs from checker output")
    if (
        evidence["outcome"]["status"] != "produced"
        or evidence["extensions"] != {"org.mathhead.portfolio.claim": "proved"}
        or certificate["verdict"]["status"] != "verified"
        or certificate["verdict"]["authority"] != "checker_attested"
        or certificate["subject"] != evidence["subject"]
        or certificate["evidence"]["evidence_sha256"] != _sha(evidence_raw)
        or certificate["checker"]["component_id"] == evidence["producer"]["component_id"]
        or decision["agreement"] is not True
        or decision["reason_code"] != "CHECKER_AGREED"
        or result["selected_evidence_sha256"] != _sha(evidence_raw)
        or result["selected_certificate_sha256"] != _sha(certificate_raw)
        or result["selected_checker_decision_sha256"] != decision["decision_sha256"]
    ):
        raise PortfolioValidationError("checked Evidence/Certificate promotion chain differs")

    _verify_ledger(final_parent["events"], 2)
    if result_raw.find(str(ROOT).encode()) >= 0:
        raise PortfolioValidationError("machine path entered canonical result bytes")
    return {
        "semantic": _decode(sample["semantic"]),
        "producer_identity": attempts[0]["producer_worker_result_sha256"],
        "checker_identity": attempts[0]["checker_worker_result_sha256"],
    }


def _verify_fallback(sample: dict[str, Any]) -> dict[str, Any]:
    request_raw = _decode(sample["request"])
    plan_raw = _decode(sample["plan"])
    parent_raw = _decode(sample["parent"])
    descriptor_raws = tuple(_decode(item) for item in sample["descriptors"])
    binding_raws = tuple(_decode(item) for item in sample["bindings"])
    artifact_raws = tuple(_decode(item) for item in sample["artifacts"])
    result_raw = _decode(sample["result"])
    final_parent_raw = _decode(sample["final_parent"])
    evidence_raw = _decode(sample["selected_evidence"])
    certificate_raw = _decode(sample["selected_certificate"])
    request = _canonical_object(request_raw, "fallback request")
    plan = _canonical_object(plan_raw, "fallback plan")
    result = _canonical_object(result_raw, "fallback result")
    final_parent = _canonical_object(final_parent_raw, "fallback final parent")
    strategies = plan["strategies"]

    if (
        request["request_sha256"] != _self_hash(request, "request_sha256")
        or request["planning_result_sha256"] != _sha(plan_raw)
        or request["parent_budget_sha256"] != _sha(parent_raw)
        or request["descriptor_sha256s"] != sorted(_sha(item) for item in descriptor_raws)
        or request["binding_sha256s"] != [_sha(item) for item in binding_raws]
        or len(request["artifact_bindings"]) != len(artifact_raws)
    ):
        raise PortfolioValidationError("fallback request closure differs")
    for binding, raw in zip(request["artifact_bindings"], artifact_raws):
        if binding != {"role": binding["role"], "sha256": _sha(raw), "bytes": len(raw)}:
            raise PortfolioValidationError("fallback artifact closure differs")
    if len(strategies) != 2 or len(binding_raws) != 2 or plan["entry_strategy_sha256"] != strategies[0]["strategy_sha256"]:
        raise PortfolioValidationError("fallback graph shape differs")
    for index, (raw, strategy) in enumerate(zip(binding_raws, strategies)):
        binding = _canonical_object(raw, f"fallback binding {index}")
        if (
            binding["binding_sha256"] != _self_hash(binding, "binding_sha256")
            or binding["plan_order"] != strategy["plan_order"]
            or strategy["plan_order"] != index
            or binding["strategy_sha256"] != strategy["strategy_sha256"]
            or binding["descriptor_sha256"] != strategy["descriptor_sha256"]
            or binding["producer_component_id"] != strategy["producer_component_id"]
            or binding["checker_component_id"] != strategy["checker_component_id"]
            or binding["producer_component_id"] == binding["checker_component_id"]
        ):
            raise PortfolioValidationError("fallback binding identity differs")
    if (
        result["result_sha256"] != _self_hash(result, "result_sha256")
        or result["request_sha256"] != request["request_sha256"]
        or result["planning_result_sha256"] != _sha(plan_raw)
        or result["initial_parent_budget_sha256"] != _sha(parent_raw)
        or result["final_parent_budget_sha256"] != _sha(final_parent_raw)
        or result["preference_policy"] != "planner_order_no_sound_witness_declaration"
        or result["mathematical_authority"] is not False
    ):
        raise PortfolioValidationError("fallback terminal identity differs")

    attempts = result["attempts"]
    inconclusive = result["inconclusive_outcomes"]
    if result["status"] == "unsupported":
        if (
            not attempts
            or any(item["outcome"] != "unsupported" for item in attempts)
            or len(inconclusive) != len(attempts)
            or evidence_raw
            or certificate_raw
            or final_parent_raw != parent_raw
        ):
            raise PortfolioValidationError("fallback unsupported containment did not fail closed")
        return {
            "semantic": _decode(sample["semantic"]),
            "worker_identities": tuple(item["producer_worker_result_sha256"] for item in attempts),
        }
    if (
        result["status"] != "succeeded"
        or result["mathematical_verdict"] != "refuted"
        or result["authority_tier"] != "checker_attestation"
        or result["selected_strategy_sha256"] != strategies[1]["strategy_sha256"]
        or len(attempts) != 2
        or [item["outcome"] for item in attempts] != ["invalid_evidence", "success"]
        or attempts[0]["checker_status"] != "not_started"
        or attempts[1]["checker_status"] != "completed"
        or len(inconclusive) != 1
    ):
        raise PortfolioValidationError("fallback classification or inventory differs")
    for index, attempt in enumerate(attempts):
        if attempt["attempt_order"] != index or attempt["attempt_sha256"] != _self_hash(attempt, "attempt_sha256"):
            raise PortfolioValidationError("fallback attempt identity differs")
        transition = next(item for item in strategies[index]["transitions"] if item["outcome"] == attempt["outcome"])
        if transition["transition_sha256"] != attempt["transition_sha256"]:
            raise PortfolioValidationError("fallback transition identity differs")
        if index == 0 and (transition["action"] != "fallback" or transition["target_strategy_sha256"] != strategies[1]["strategy_sha256"]):
            raise PortfolioValidationError("fallback edge differs")
        if index == 1 and transition["action"] != "succeed":
            raise PortfolioValidationError("fallback terminal edge differs")
    if (
        attempts[0]["parent_budget_before_sha256"] != _sha(parent_raw)
        or attempts[0]["parent_budget_after_sha256"] != attempts[1]["parent_budget_before_sha256"]
        or attempts[1]["parent_budget_after_sha256"] != _sha(final_parent_raw)
    ):
        raise PortfolioValidationError("fallback ledger chain differs")
    record = inconclusive[0]
    if (
        record["inconclusive_sha256"] != _self_hash(record, "inconclusive_sha256")
        or record["attempt_order"] != 0
        or record["strategy_sha256"] != attempts[0]["strategy_sha256"]
        or record["outcome"] != attempts[0]["outcome"]
        or record["reason_code"] != "EVIDENCE_INVALID"
    ):
        raise PortfolioValidationError("fallback inconclusive record differs")

    evidence = _canonical_object(evidence_raw, "fallback selected Evidence")
    certificate = _canonical_object(certificate_raw, "fallback selected Certificate")
    if (
        evidence["extensions"] != {"org.mathhead.portfolio.claim": "refuted"}
        or evidence["outcome"]["status"] != "produced"
        or certificate["verdict"]["status"] != "verified"
        or certificate["verdict"]["authority"] != "checker_attested"
        or certificate["subject"] != evidence["subject"]
        or certificate["evidence"]["evidence_sha256"] != _sha(evidence_raw)
        or certificate["checker"]["component_id"] == evidence["producer"]["component_id"]
        or result["selected_evidence_sha256"] != _sha(evidence_raw)
        or result["selected_certificate_sha256"] != _sha(certificate_raw)
        or result["selected_checker_decision_sha256"] != attempts[1]["checker_decision_sha256"]
    ):
        raise PortfolioValidationError("fallback checked refutation chain differs")
    _verify_ledger(final_parent["events"], 3)
    if result_raw.find(str(ROOT).encode()) >= 0:
        raise PortfolioValidationError("machine path entered fallback result bytes")
    return {
        "semantic": _decode(sample["semantic"]),
        "worker_identities": tuple(
            identity
            for attempt in attempts
            for identity in (
                attempt["producer_worker_result_sha256"],
                attempt["checker_worker_result_sha256"],
            )
            if identity is not None
        ),
    }


def validate() -> dict[str, object]:
    contract, contract_raw = _load(CONTRACT_PATH)
    if contract["contract_id"] != CONTRACT_ID or contract_raw != _canonical(contract):
        raise PortfolioValidationError("accepted contract binding differs")
    schemas: list[dict[str, str]] = []
    for name in SCHEMA_NAMES:
        schema, raw = _load(ROOT / "docs/contracts/schemas" / name)
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise PortfolioValidationError(f"schema is not a closed object: {name}")
        schema_name = schema.get("properties", {}).get("schema", {}).get("const")
        if type(schema_name) is not str or _sha(raw) != SCHEMA_SHA256S.get(schema_name):
            raise PortfolioValidationError(f"schema content identity differs: {name}")
        schemas.append({"path": f"docs/contracts/schemas/{name}", "sha256": _sha(raw)})
    source = SOURCE_PATH.read_bytes()
    tree = ast.parse(source, filename=str(SOURCE_PATH))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "make_portfolio_execution_binding",
        "make_proof_search_portfolio_request",
        "parse_portfolio_execution_binding",
        "parse_proof_search_portfolio_request",
        "parse_portfolio_checker_decision",
        "parse_proof_search_portfolio_result",
        "proof_search_portfolio_result_bytes",
        "validate_proof_search_portfolio_result",
        "run_portfolio",
    }
    if not required <= functions.keys():
        raise PortfolioValidationError("public portfolio surface is incomplete")
    run_arguments = [argument.arg for argument in functions["run_portfolio"].args.args]
    if run_arguments != [
        "request", "planning_result", "parent_budget", "descriptors", "bindings",
        "artifacts", "executable_paths", "workspace_root", "cancel_event",
    ]:
        raise PortfolioValidationError("run_portfolio signature drifted")
    forbidden = {"eval", "exec", "__import__"}
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    if calls & forbidden:
        raise PortfolioValidationError("dynamic execution entered portfolio source")
    imports = sorted(
        {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
    )
    if any(name in imports for name in ("subprocess", "multiprocessing", "importlib", "random", "time")):
        raise PortfolioValidationError("portfolio bypasses the isolated-worker boundary")
    source_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "supervise_worker"
    ]
    if len(source_calls) != 1:
        raise PortfolioValidationError("isolated supervisor call site is not singular")
    constants = {
        target.id: node.value.value
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        for target in (node.target,)
    }
    if constants.get("PORTFOLIO_CONTRACT_ID") != CONTRACT_ID:
        raise PortfolioValidationError("source contract ID differs")
    first_sample = _runtime_sample("1")
    second_sample = _runtime_sample("8675309")
    first = _verify_runtime(first_sample)
    second = _verify_runtime(second_sample)
    first_fallback = _verify_fallback(first_sample["fallback"])
    second_fallback = _verify_fallback(second_sample["fallback"])
    if (
        first["semantic"] != second["semantic"]
        or first["producer_identity"] != second["producer_identity"]
        or first["checker_identity"] != second["checker_identity"]
        or first_fallback != second_fallback
    ):
        raise PortfolioValidationError("fresh-process semantic result identity differs")
    return {
        "schema": "mathhead.proof-search-portfolio-report.v1",
        "contract": {"id": CONTRACT_ID, "sha256": _sha(contract_raw)},
        "schemas": schemas,
        "source": {"path": "src/mathhead/proof_search_portfolio.py", "sha256": _sha(source)},
        "checks": [
            {"id": "contract-binding", "status": "passed"},
            {"id": "closed-schemas", "status": "passed"},
            {"id": "public-surface", "status": "passed"},
            {"id": "isolated-worker-only", "status": "passed"},
            {"id": "request-manifest-closure", "status": "passed"},
            {"id": "plan-transition-reconstruction", "status": "passed"},
            {"id": "fallback-inconclusive-inventory", "status": "passed"},
            {"id": "planner-order-preference", "status": "passed"},
            {"id": "ledger-conservation", "status": "passed"},
            {"id": "checked-promotion-chain", "status": "passed"},
            {"id": "fresh-process-determinism", "status": "passed"},
        ],
    }


def main() -> int:
    try:
        report = validate()
        rendered = _canonical(report)
        if "--write-report" in sys.argv:
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_bytes(rendered)
        elif REPORT_PATH.read_bytes() != rendered:
            raise PortfolioValidationError("frozen report is stale")
    except (OSError, UnicodeError, json.JSONDecodeError, SyntaxError, PortfolioValidationError) as exc:
        print(f"proof-search-portfolio: FAIL: {exc}", file=sys.stderr)
        return 1
    print("proof-search-portfolio: PASS (closed execution, checked promotion, conserved ledgers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
