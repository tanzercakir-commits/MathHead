from __future__ import annotations

import hashlib
import json

from mathhead.safe_cache import decide_safe_cache
from tests.run_audit.fixtures import success_bundle


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

    request = json.loads(one("portfolio_request"))
    return (
        one("planning_request"), one("capability_route_result"),
        one("portfolio_request"), one("planning_result"),
        one("initial_parent_budget"),
        tuple(objects[item["sha256"]] for item in by_role["plugin_descriptor"]),
        tuple(objects[item["sha256"]] for item in by_role["execution_binding"]),
        tuple(objects[item["sha256"]] for item in request["artifact_bindings"]),
    )


result: dict[str, str] = {}
for claim in ("proved", "refuted"):
    audited = success_bundle(claim=claim)
    decision = decide_safe_cache(*cache_inputs(audited), None)
    if decision.status != "miss" or decision.lookup_key_sha256 is None:
        raise SystemExit("fresh process did not reconstruct one key")
    result[claim] = decision.lookup_key_sha256
print(json.dumps(result, sort_keys=True, separators=(",", ":")))
