#!/usr/bin/env python3
"""Independently validate the MH-C-CAPABILITY-REGISTRY-001 routing boundary."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any, NoReturn, Sequence


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for entry in (SRC, ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from mathhead import capability_registry as production  # noqa: E402
from tests.capability_registry.fixtures import (  # noqa: E402
    RouteFixture,
    canonical,
    plugin_bytes,
    sha,
)


CONTRACT_ID = "MH-C-CAPABILITY-REGISTRY-001"
CONTRACT_SHA256 = "52cc70945a4e83115c756e5b0a72724676f0e52a89e56c06a0fa8bd42c0e0413"
DEFAULT_REPORT = Path("docs/routing/reports/capability-registry-v1.json")
REPORT_SCHEMA = "mathhead.capability-registry-validation-report.v1"
SCHEMAS = {
    "capability-availability-v1.schema.json": "aea788ecdee20497bb485c371b07a220707dabf1548bdc930e8b6c66877b52e1",
    "capability-candidate-v1.schema.json": "cc5c231bc11021e155b6390b2682ee63c4c6b2a3d30807f24a9c5d4ae31a75ed",
    "capability-cost-derivation-v1.schema.json": "f4de59ae5cff8d9e096e42f0bc4d044f611997be5df5ae95f5a47f40d7e9d915",
    "capability-incompatibility-v1.schema.json": "53780cc2e9d3e2fec418c6d04ad417d6920f3d4e12cf953b2bafca864d5054f2",
    "capability-registry-entry-v1.schema.json": "a20d3bcc4dd5bd5988eac60b6000ea8e92299f2aa13275f77a2306fb68dd8b3c",
    "capability-registry-v1.schema.json": "37e03e97fcd736b3c75e0c8c33f3d82c735dc57c4463ead8af9d331704761fbc",
    "capability-route-request-v1.schema.json": "cdf7dd11d0f1048c018c3472f7f0237ac3713db5edbbd1851761ab7388c4cc82",
    "capability-route-result-v1.schema.json": "11c23f4822be4e531e28bf66f47940fdeb389222305f04162c67ced66e2e49ec",
}
DOMAIN_THEORIES = {
    "boolean": "org.mathhead.theory.logic",
    "complex": "org.mathhead.theory.analysis",
    "graph": "org.mathhead.theory.graph",
    "integer": "org.mathhead.theory.arithmetic",
    "modular": "org.mathhead.theory.arithmetic",
    "polynomial": "org.mathhead.theory.algebra",
    "rational": "org.mathhead.theory.arithmetic",
    "real": "org.mathhead.theory.analysis",
    "set": "org.mathhead.theory.set",
}


class CapabilityRegistryReportError(RuntimeError):
    """An independent identity, replay, fragment, routing, or cost check failed."""


def _fail(detail: str) -> NoReturn:
    raise CapabilityRegistryReportError(detail)


def _load(data: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"invalid JSON for {label}: {exc}")
    if not isinstance(value, dict) or canonical(value) != data:
        _fail(f"noncanonical object for {label}")
    return value


def _self_hash(value: dict[str, Any], field: str) -> str:
    basis = copy.deepcopy(value)
    basis[field] = None
    return sha(canonical(basis))


def _identity_checks() -> dict[str, object]:
    paths = {
        Path(f"docs/contracts/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        Path(f"docs/contracts/proposed/{CONTRACT_ID}.json"): CONTRACT_SHA256,
        **{Path("docs/contracts/schemas") / name: digest for name, digest in SCHEMAS.items()},
    }
    for path, expected in paths.items():
        if sha((ROOT / path).read_bytes()) != expected:
            _fail(f"identity drift: {path}")
    accepted = (ROOT / f"docs/contracts/{CONTRACT_ID}.json").read_bytes()
    proposed = (ROOT / f"docs/contracts/proposed/{CONTRACT_ID}.json").read_bytes()
    if accepted != proposed or accepted != canonical(json.loads(accepted)):
        _fail("accepted/proposed canonical binding drift")
    if production.CONTRACT_SHA256 != CONTRACT_SHA256 or production.SCHEMA_SHA256S != SCHEMAS:
        _fail("production contract or schema binding drift")
    for name in SCHEMAS:
        schema = json.loads((ROOT / "docs/contracts/schemas" / name).read_bytes())
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema" or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            _fail(f"schema root is not closed Draft 2020-12: {name}")
    return {"accepted_equals_proposed": True, "contract_bound": True, "schemas": 8}


def _source_checks() -> dict[str, object]:
    path = ROOT / "src/mathhead/capability_registry.py"
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
    forbidden_calls = {"open", "exec", "eval", "__import__", "system", "popen", "getenv", "entry_points"}
    if calls & forbidden_calls:
        _fail(f"pure source gained effect calls: {sorted(calls & forbidden_calls)}")
    return {"imports": sorted(imports), "sha256": sha(path.read_bytes())}


def _walk(value: object) -> tuple[set[str], set[str], set[str], set[str], int, int, int]:
    domains: set[str] = set()
    expressions: set[str] = set()
    relations: set[str] = set()
    quantifiers: set[str] = set()
    quantifier_count = 0
    quantifier_depth = 0
    expression_nodes = 0
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, list):
            stack.extend((child, depth) for child in reversed(item))
            continue
        if not isinstance(item, dict):
            continue
        domain = item.get("domain")
        if isinstance(domain, dict):
            if domain.get("kind") == "builtin" and isinstance(domain.get("name"), str):
                domains.add(domain["name"])
            elif domain.get("kind") == "modular":
                domains.add("integer")
        kind = item.get("kind")
        if kind == "quantified":
            quantifier_count += 1
            depth += 1
            quantifier_depth = max(quantifier_depth, depth)
            quantifier = item.get("quantifier")
            if isinstance(quantifier, str):
                quantifiers.add(quantifier)
        if kind == "relation" and isinstance(item.get("relation"), dict):
            relation_kind = item["relation"].get("kind")
            if isinstance(relation_kind, str):
                relations.add(f"org.mathhead.relation.{relation_kind.replace('_', '-')}")
        elif isinstance(kind, str) and (
            "operands" in item
            or kind in {"equal", "not_equal", "less", "less_equal", "greater", "greater_equal", "member", "not_member", "divides", "congruent"}
        ):
            relations.add(f"org.mathhead.relation.{kind.replace('_', '-')}")
        elif isinstance(kind, str) and (
            "variable" in item
            or "arguments" in item
            or "operands" in item
            or kind in {"literal", "variable", "apply", "add", "multiply", "power", "negate"}
        ):
            expressions.add(f"org.mathhead.expression.{kind.replace('_', '-')}")
            expression_nodes += 1
        stack.extend((child, depth) for child in reversed(tuple(item.values())))
    return domains, expressions, relations, quantifiers, quantifier_count, quantifier_depth, expression_nodes


def _degree(value: object) -> int:
    if not isinstance(value, dict):
        return 0
    kind = value.get("kind")
    if kind == "variable":
        return 1
    if kind in {"literal", "integer", "rational"}:
        return 0
    if kind in {"add", "subtract", "negate"}:
        children = value.get("operands", value.get("arguments", []))
        return max((_degree(item) for item in children), default=0) if isinstance(children, list) else 0
    if kind in {"multiply", "product"}:
        children = value.get("operands", value.get("arguments", []))
        return sum(_degree(item) for item in children) if isinstance(children, list) else 0
    if kind == "power" and isinstance(value.get("exponent"), int) and not isinstance(value["exponent"], bool) and value["exponent"] >= 0:
        return _degree(value.get("base")) * value["exponent"]
    return max((_degree(item) for item in value.values()), default=0)


def _independent_fragment(fixture: RouteFixture) -> dict[str, Any]:
    normalization = _load(
        fixture.payloads[fixture.request_fields["normalization_result_sha256"]],
        "normalization",
    )
    reading = next(
        item for item in normalization["candidates"]
        if item["reading_id"] == fixture.request_fields["reading_id"]
    )
    obligation = next(
        item for item in reading["obligations"]
        if item["semantic_sha256"] == fixture.request_fields["obligation_semantic_sha256"]
    )
    dependencies = set(obligation["dependency_semantic_sha256s"]) | {
        obligation["statement_semantic_sha256"], obligation["local_context_semantic_sha256"]
    }
    forms = [item for item in reading["normal_forms"] if item["semantic_sha256"] in dependencies]
    domains: set[str] = set()
    expressions: set[str] = set()
    relations: set[str] = set()
    quantifiers: set[str] = set()
    variables: set[str] = set()
    count = depth = nodes = degree = 0
    for form in forms:
        found = _walk(form["value"])
        domains |= found[0]
        expressions |= found[1]
        relations |= found[2]
        quantifiers |= found[3]
        count = max(count, found[4])
        depth = max(depth, found[5])
        if form["form_kind"] == "expression":
            nodes += found[6]
            degree = max(degree, _degree(form["value"]))
        if form["form_kind"] == "variable":
            variables.add(form["semantic_sha256"])
    statement = obligation["statement_normal_form"]
    found = _walk(statement)
    domains |= found[0]
    expressions |= found[1]
    relations |= found[2]
    quantifiers |= found[3]
    count = max(count, found[4])
    depth = max(depth, found[5])
    nodes = max(nodes, found[6])
    degree = max(degree, _degree(statement))
    if not quantifiers:
        quantifiers.add("none")
    theories = {DOMAIN_THEORIES.get(domain, f"org.mathhead.theory.{domain}") for domain in domains}
    if not theories:
        theories.add("org.mathhead.theory.logic")
    exact = bool(domains) and domains <= {"boolean", "integer", "modular", "polynomial", "rational", "set"}
    features = set(theories)
    if exact:
        features.add("org.mathhead.feature.exact-arithmetic")
    value = {
        "schema": "mathhead.capability-fragment.v1",
        "theories": sorted(theories),
        "domains": sorted(domains),
        "quantifiers": sorted(quantifiers),
        "expression_kinds": sorted(expressions),
        "relation_kinds": sorted(relations),
        "polynomial_degree": degree,
        "quantifier_count": count,
        "quantifier_depth": depth,
        "variables": len(variables),
        "expression_nodes": nodes,
        "goals": 1,
        "ambiguous": False,
        "exact_arithmetic": exact,
        "theory_features": sorted(features),
        "fragment_sha256": None,
        "mathematical_authority": False,
    }
    value["fragment_sha256"] = _self_hash(value, "fragment_sha256")
    return value


def _descriptor_checks(descriptors: tuple[bytes, ...]) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {}
    for data in descriptors:
        value = _load(data, "descriptor")
        replay = copy.deepcopy(value["replay"])
        replay.pop("descriptor_basis_sha256")
        basis = copy.deepcopy(value)
        basis["replay"] = replay
        if value["replay"]["descriptor_basis_sha256"] != sha(canonical(basis)):
            _fail("descriptor replay basis drift")
        parsed[sha(data)] = value
    if list(parsed) != sorted(parsed):
        parsed = {digest: parsed[digest] for digest in sorted(parsed)}
    return parsed


def _route_fixture() -> tuple[dict[str, Any], dict[str, object]]:
    fixture = RouteFixture()
    fragment = _independent_fragment(fixture)
    shape = SimpleNamespace(
        domains=tuple(fragment["domains"]),
        quantifiers=tuple(fragment["quantifiers"]),
        expression_kinds=tuple(fragment["expression_kinds"]),
        relation_kinds=tuple(fragment["relation_kinds"]),
        polynomial_degree=fragment["polynomial_degree"],
        quantifier_depth=fragment["quantifier_depth"],
        variables=fragment["variables"],
        theory_features=tuple(fragment["theory_features"]),
    )
    accepted = plugin_bytes(shape, suffix="validator", base_cost=7, priority=20)

    def reject(value: dict[str, Any]) -> None:
        value["capabilities"][0]["fragment"].update(
            domains=["real"],
            required_theory_features=["org.mathhead.feature.unavailable"],
        )

    rejected = plugin_bytes(shape, suffix="rejected", base_cost=1, priority=999, mutation=reject)
    descriptors = tuple(sorted((accepted, rejected), key=sha))
    parsed_descriptors = _descriptor_checks(descriptors)
    availability = production.make_capability_availability(
        platform="linux",
        python_version="3.12",
        available_descriptor_sha256s=tuple(sorted(parsed_descriptors)),
    )
    request = production.make_capability_route_request(
        **fixture.request_fields,
        availability=availability,
    )
    result = production.route_capabilities(request, descriptors, fixture.artifacts)
    raw = production.capability_route_result_bytes(result)
    value = _load(raw, "route result")
    if value["fragment"] != fragment:
        _fail("independently derived fragment drift")
    registry = value["registry"]
    if registry["descriptor_sha256s"] != sorted(parsed_descriptors):
        _fail("registry descriptor projection drift")
    if registry["registry_sha256"] != _self_hash(registry, "registry_sha256"):
        _fail("registry identity drift")
    for entry in registry["entries"]:
        descriptor = parsed_descriptors[entry["descriptor_sha256"]]
        capability_ids = [item["capability_id"] for item in descriptor["capabilities"]]
        if entry["capability_ids"] != capability_ids or entry["entry_sha256"] != _self_hash(entry, "entry_sha256"):
            _fail("registry entry projection drift")
    if len(value["candidates"]) != 1 or len(value["incompatibilities"]) != 1:
        _fail("candidate/incompatibility completeness drift")
    candidate = value["candidates"][0]
    descriptor = parsed_descriptors[candidate["descriptor_sha256"]]
    model = descriptor["capabilities"][0]["cost_model"]
    terms = {
        "base": model["base"],
        "variable_term": model["per_variable"] * fragment["variables"],
        "expression_node_term": model["per_expression_node"] * fragment["expression_nodes"],
        "quantifier_term": model["per_quantifier"] * fragment["quantifier_count"],
        "goal_term": model["per_goal"] * fragment["goals"],
        "ambiguity_term": model["ambiguity_surcharge"] if fragment["ambiguous"] else 0,
    }
    total = sum(terms.values())
    cost = candidate["cost"]
    if any(cost[name] != amount for name, amount in terms.items()) or cost["unsaturated_total"] != total or cost["estimated_cost"] != min(total, model["maximum"]) or cost["cost_sha256"] != _self_hash(cost, "cost_sha256"):
        _fail("independent cost derivation drift")
    if candidate["candidate_sha256"] != _self_hash(candidate, "candidate_sha256"):
        _fail("candidate identity drift")
    incompatibility = value["incompatibilities"][0]
    if incompatibility["reason_codes"] != ["DOMAIN_MISMATCH", "FEATURE_REQUIRED"] or incompatibility["incompatibility_sha256"] != _self_hash(incompatibility, "incompatibility_sha256"):
        _fail("independent incompatibility projection drift")
    if value["selected_candidate_sha256"] != candidate["candidate_sha256"] or value["result_sha256"] != _self_hash(value, "result_sha256"):
        _fail("route selection or identity drift")
    return value, {
        "candidate_sha256": candidate["candidate_sha256"],
        "descriptors": len(descriptors),
        "estimated_cost": cost["estimated_cost"],
        "fragment_sha256": fragment["fragment_sha256"],
        "incompatibilities": 1,
        "registry_sha256": registry["registry_sha256"],
        "result_sha256": value["result_sha256"],
        "status": value["status"],
    }


def _negative_checks() -> int:
    fixture = RouteFixture()
    fragment = _independent_fragment(fixture)
    shape = SimpleNamespace(
        domains=tuple(fragment["domains"]), quantifiers=tuple(fragment["quantifiers"]),
        expression_kinds=tuple(fragment["expression_kinds"]), relation_kinds=tuple(fragment["relation_kinds"]),
        polynomial_degree=fragment["polynomial_degree"], quantifier_depth=fragment["quantifier_depth"],
        variables=fragment["variables"], theory_features=tuple(fragment["theory_features"]),
    )
    descriptor = plugin_bytes(shape, suffix="negative")
    availability = production.make_capability_availability(
        platform="linux", python_version="3.12", available_descriptor_sha256s=(sha(descriptor),)
    )
    request = production.make_capability_route_request(**fixture.request_fields, availability=availability)
    controls = (
        production.route_capabilities(request.rstrip(b"\n"), (descriptor,), fixture.artifacts),
        production.route_capabilities(request, (descriptor,), fixture.artifacts[:-1]),
        production.route_capabilities(request, (descriptor, descriptor[:-1]), fixture.artifacts),
        production.route_capabilities(request, (descriptor,), (*fixture.artifacts, fixture.artifacts[-1])),
    )
    if any(item.status not in {"invalid", "exhausted"} or item.registry is not None for item in controls):
        _fail("negative control leaked a partial or successful route")
    return len(controls)


def _fingerprint() -> str:
    value, _ = _route_fixture()
    return sha(canonical(value))


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
            _fail(f"determinism child failed for hash seed {seed}: {completed.stderr.strip()}")
        fingerprints.append(completed.stdout.strip())
    if len(set(fingerprints)) != 1:
        _fail("hash-seed determinism drift")
    return {"hash_seeds": 2, "result_bytes_sha256": fingerprints[0]}


def _report() -> dict[str, object]:
    _, fixture = _route_fixture()
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
        "tests_sha256": sha((ROOT / "tests/capability_registry/test_capability_registry.py").read_bytes()),
        "validator_sha256": sha((ROOT / "tools/validate_capability_registry.py").read_bytes()),
    }
    report["report_sha256"] = sha(canonical(report))
    return report


def _write_or_check(report: dict[str, object], path: Path, *, write: bool) -> None:
    target = ROOT / path
    payload = canonical(report)
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        print(f"capability-registry: report updated: {target}")
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
    except (OSError, UnicodeError, ValueError, CapabilityRegistryReportError) as exc:
        print(f"capability-registry: FAIL: {exc}", file=sys.stderr)
        return 1
    fixture = report["fixture"]
    assert isinstance(fixture, dict)
    print(
        "capability-registry: PASS "
        f"(descriptors={fixture['descriptors']}, status={fixture['status']}, "
        f"cost={fixture['estimated_cost']}, negatives={report['negative_controls']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
