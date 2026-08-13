#!/usr/bin/env python3
"""Independently validate the MH-055 pure safe-cache boundary."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys
import tomllib
from types import MappingProxyType
from typing import NoReturn


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/mathhead/safe_cache.py"
REPORT = ROOT / "docs/planning/reports/safe-cache-v2.json"
CONTRACT_ID = "MH-C-SAFE-CACHE-002"
CONTRACT_SHA256 = "35cd004a1ed91f2c3969a6b295722b8099ee9fc36f3fc15170d5d1082d2bfab4"
SCHEMAS = {
    "safe-cache-request-v2.schema.json": "3ad6e7111ceb0c6336315a0bbbe6950e60abd2331e9ce0c9dbb52e60f285a18a",
    "safe-cache-entry-v2.schema.json": "ce1100b9326d04a07c4f22286f28814f1a3bcef9091ca7b13f6ee9ebd57f9234",
    "safe-cache-decision-result-v2.schema.json": "30df479781c7f022da8ffaee8686118fa7613b6e49f522da88362db46f48965d",
}
REPORT_SCHEMA = "mathhead.safe-cache-validation-report.v2"


class SafeCacheValidationFailure(RuntimeError):
    pass


def _fail(detail: str) -> NoReturn:
    raise SafeCacheValidationFailure(detail)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def _self_hash(value: dict[str, object], field: str) -> str:
    preimage = dict(value)
    preimage[field] = None
    return _sha(_canonical(preimage))


def _contract_and_schema_checks() -> dict[str, object]:
    accepted = ROOT / "docs/contracts" / f"{CONTRACT_ID}.json"
    proposed = ROOT / "docs/contracts/proposed" / f"{CONTRACT_ID}.json"
    raw = accepted.read_bytes()
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text())
    entries = {
        str(item["id"]): item
        for item in manifest.get("contracts", [])
        if item.get("state") == "accepted"
    }
    if (
        _sha(raw) != CONTRACT_SHA256
        or raw != proposed.read_bytes()
        or raw != _canonical(json.loads(raw))
        or entries.get(CONTRACT_ID, {}).get("sha256") != CONTRACT_SHA256
    ):
        _fail("accepted pure cache contract binding drift")
    schemas: dict[str, str] = {}
    for name, digest in SCHEMAS.items():
        path = ROOT / "docs/contracts/schemas" / name
        value = json.loads(path.read_bytes())
        if (
            _sha(path.read_bytes()) != digest
            or value.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or value.get("type") != "object"
            or value.get("additionalProperties") is not False
            or set(value.get("required", [])) != set(value.get("properties", {}))
        ):
            _fail(f"closed schema binding drift: {name}")
        schemas[name] = digest
    return {"contract": {"id": CONTRACT_ID, "sha256": CONTRACT_SHA256}, "schemas": schemas}


def _inventory_checks(module: object) -> dict[str, int]:
    request_schema = json.loads(
        (ROOT / "docs/contracts/schemas/safe-cache-request-v2.schema.json").read_text()
    )
    manifest = tomllib.loads((ROOT / "docs/contracts/manifest.toml").read_text())
    manifest_by_id = {
        str(item["id"]): ROOT / str(item["path"])
        for item in manifest.get("contracts", [])
    }
    contract_ids = request_schema["$defs"]["contract_bindings"]["propertyNames"]["enum"]
    contracts = {item: _sha(manifest_by_id[item].read_bytes()) for item in contract_ids}
    schema_ids = request_schema["$defs"]["schema_bindings"]["propertyNames"]["enum"]
    by_schema: dict[str, Path] = {}
    for path in (ROOT / "docs/contracts/schemas").glob("*.schema.json"):
        value = json.loads(path.read_text())
        schema_uri = value.get("$id")
        if type(schema_uri) is str:
            derived = (
                "mathhead."
                + schema_uri.rsplit("/", 1)[-1]
                .removesuffix(".schema.json")
                .replace("-v", ".v")
            )
            by_schema[derived] = path
        schema = value.get("properties", {}).get("schema", {}).get("const")
        if type(schema) is str:
            by_schema[schema] = path
    schemas = {item: _sha(by_schema[item].read_bytes()) for item in schema_ids}
    implementations = {
        role: _sha((ROOT / path).read_bytes())
        for role, path in {
            "capability_registry": "src/mathhead/capability_registry.py",
            "deterministic_planner": "src/mathhead/deterministic_planner.py",
            "isolated_worker": "src/mathhead/isolated_worker.py",
            "proof_search_portfolio": "src/mathhead/proof_search_portfolio.py",
            "trust_transition": "src/mathhead/kernel/trust_transitions.py",
        }.items()
    }
    configurations = {
        role: _sha((ROOT / path).read_bytes())
        for role, path in {
            "capability_registry_report": "docs/routing/reports/capability-registry-v1.json",
            "deterministic_planner_report": "docs/planning/reports/deterministic-planner-v1.json",
            "isolated_worker_report": "docs/planning/reports/isolated-worker-v1.json",
            "proof_search_portfolio_report": "docs/planning/reports/proof-search-portfolio-v1.json",
        }.items()
    }
    configurations["trust_transition_policy"] = (
        "1a26d41f546f4a9334442fc7ef7d83eccffef56ed1f7a46d4209c748fb1c4b93"
    )
    for name, expected in (
        ("CONTRACT_BINDINGS", contracts),
        ("SCHEMA_BINDINGS", schemas),
        ("IMPLEMENTATION_BINDINGS", implementations),
        ("CONFIGURATION_BINDINGS", configurations),
    ):
        if getattr(module, name) != expected:
            _fail(f"compiled {name} drift")
    if tuple(map(len, (contracts, schemas, implementations, configurations))) != (
        20, 65, 5, 5
    ):
        _fail("compiled provenance inventory count differs")
    provenance = {
        "schema": "mathhead.run-execution-provenance.v1",
        "dependency_contracts": contracts,
        "dependency_schemas": schemas,
        "implementation_bindings": implementations,
        "configuration_bindings": configurations,
        "trust_policy_sha256": configurations["trust_transition_policy"],
        "provenance_sha256": None,
        "mathematical_authority": False,
    }
    expected_provenance = _sha(_canonical(provenance))
    if module._expected_execution_provenance_sha256() != expected_provenance:
        _fail("current expected provenance null-own identity differs")
    return {
        "contracts": len(contracts), "schemas": len(schemas),
        "implementations": len(implementations), "configurations": len(configurations),
    }


def _source_checks() -> dict[str, object]:
    tree = ast.parse(SOURCE.read_text())
    imports: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    forbidden_imports = {
        "os", "pathlib", "subprocess", "multiprocessing", "socket", "time",
        "random", "importlib", ".cache", ".discovery",
    }
    forbidden_calls = {
        "execute_audited_run", "supervise_worker", "run_proof_search_portfolio",
        "Popen", "run", "system", "open", "getenv", "entry_points",
    }
    if imports & forbidden_imports or calls & forbidden_calls:
        _fail("pure source imports or calls an effect/producer surface")
    source = SOURCE.read_bytes()
    return {
        "path": "src/mathhead/safe_cache.py",
        "sha256": _sha(source),
        "imports_checked": len(imports),
        "calls_checked": len(calls),
    }


def _cache_inputs(audited: object) -> tuple[object, ...]:
    bundle = audited.bundle
    manifest = json.loads(bundle.manifest)
    objects = {_sha(raw): raw for raw in bundle.objects}
    by_role: dict[str, list[dict[str, object]]] = {}
    for record in manifest["objects"]:
        by_role.setdefault(str(record["role"]), []).append(record)

    def one(role: str) -> bytes:
        records = by_role[role]
        if len(records) != 1:
            _fail(f"runtime fixture role differs: {role}")
        return objects[str(records[0]["sha256"])]

    request = json.loads(one("portfolio_request"))
    return (
        one("planning_request"), one("capability_route_result"),
        one("portfolio_request"), one("planning_result"), one("initial_parent_budget"),
        tuple(objects[str(item["sha256"])] for item in by_role["plugin_descriptor"]),
        tuple(objects[str(item["sha256"])] for item in by_role["execution_binding"]),
        tuple(objects[str(item["sha256"])] for item in request["artifact_bindings"]),
    )


def _runtime_checks(module: object) -> dict[str, object]:
    from tests.run_audit.fixtures import single_bundle, success_bundle

    results: dict[str, object] = {}
    for claim in ("proved", "refuted"):
        audited = success_bundle(claim=claim)
        current = _cache_inputs(audited)
        miss = module.decide_safe_cache(*current, None)
        hit = module.decide_safe_cache(*current, audited.bundle)
        if (
            (miss.status, miss.reason_code) != ("miss", "CACHE_CANDIDATE_ABSENT")
            or (hit.status, hit.reason_code) != ("hit", "CACHE_HIT")
            or miss.lookup_key_sha256 != hit.lookup_key_sha256
            or hit.entry is None
            or module.parse_safe_cache_decision(module.safe_cache_decision_bytes(hit)) != hit
            or module.parse_safe_cache_entry(module.safe_cache_entry_bytes(hit.entry)) != hit.entry
        ):
            _fail(f"{claim} fixture did not produce one exact hit")
        results[claim] = {
            "lookup_key_sha256": hit.lookup_key_sha256,
            "fresh_hit_verified": True,
            "entry_codec_verified": True,
            "decision_codec_verified": True,
        }
    ineligible_fixture = single_bundle(evidence_status="unsupported")
    ineligible = module.decide_safe_cache(
        *_cache_inputs(ineligible_fixture), ineligible_fixture.bundle
    )
    invalid = module.decide_safe_cache(
        b"{}\n", *_cache_inputs(success_bundle())[1:], None
    )
    audited = success_bundle()
    current = _cache_inputs(audited)
    original_implementations = module.IMPLEMENTATION_BINDINGS
    changed = dict(original_implementations)
    changed["capability_registry"] = "f" * 64
    module.IMPLEMENTATION_BINDINGS = MappingProxyType(changed)
    try:
        old_candidate = module.decide_safe_cache(*current, audited.bundle)
    finally:
        module.IMPLEMENTATION_BINDINGS = original_implementations
    if (
        (ineligible.status, ineligible.reason_code)
        != ("ineligible", "CACHE_OUTCOME_INELIGIBLE")
        or (invalid.status, invalid.reason_code, invalid.lookup_key_sha256)
        != ("invalid", "CACHE_CURRENT_REQUEST_INVALID", None)
        or (old_candidate.status, old_candidate.reason_code)
        != ("invalid", "CACHE_IMPLEMENTATION_MISMATCH")
    ):
        _fail("closed non-hit classifications differ")
    return {
        "eligible": results,
        "ineligible_outcome_verified": True,
        "invalid_current_verified": True,
        "old_provenance_candidate_rejected": True,
        "mathematical_authority": False,
    }


def _report() -> dict[str, object]:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    import mathhead.safe_cache as module

    report: dict[str, object] = {
        "schema": REPORT_SCHEMA, "status": "passed",
        "binding": _contract_and_schema_checks(),
        "inventory": _inventory_checks(module),
        "source": _source_checks(), "runtime": _runtime_checks(module),
        "checks": [
            "accepted-contract-and-closed-schema-binding",
            "compiled-contract-schema-source-configuration-inventory",
            "pure-effect-free-source-closure", "current-request-before-replay",
            "absent-candidate-miss", "fresh-proved-hit", "fresh-refuted-hit",
            "closed-ineligible-outcome", "canonical-entry-and-decision-codecs",
            "zero-cache-metadata-authority",
        ],
        "mathematical_authority": False, "report_sha256": None,
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
    except (SafeCacheValidationFailure, OSError, ValueError, SyntaxError) as exc:
        print(f"safe-cache: FAIL: {exc}", file=sys.stderr)
        return 1
    print("safe-cache: PASS (closed key, fresh replay, eligible checked reuse only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
