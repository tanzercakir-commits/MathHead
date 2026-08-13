from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from mathhead.run_audit import RunAuditBundle, _bundle_from_replayed_bytes


_DATA = Path(__file__).with_name("data")
_FILES = {
    "proved": "audited-proved-v5.json",
    "refuted": "audited-refuted-v5.json",
}
_FILE_SHA256 = {
    "proved": "0dc6738f375a5666f7619e390689890894740737aafff4f6a52b05fd090cc540",
    "refuted": "7db24815e977195770ebaaf929be1581eb7ad5bc9d0066c0bf9e1bf936bbdf78",
}

EXPECTED_LOOKUP_KEYS = {
    "proved": "0f6543fa2d4aed0403828781b2276c7a7718309f886f9b06b5959eaabae82873",
    "refuted": "f94fe0796ec7c0488435bae8e94406dd448e4490a4536ca15a9886267ec457b6",
}


@dataclass(frozen=True, slots=True)
class AuditedCacheFixture:
    claim: str
    bundle: RunAuditBundle


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate fixture field: {key}")
        value[key] = item
    return value


def success_bundle(*, claim: str = "proved") -> AuditedCacheFixture:
    if claim not in _FILES:
        raise ValueError("portable audited fixture claim is unsupported")
    raw = (_DATA / _FILES[claim]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != _FILE_SHA256[claim]:
        raise ValueError("portable audited fixture bytes differ")
    value = json.loads(raw, object_pairs_hook=_pairs)
    if (
        type(value) is not dict
        or set(value) != {"claim", "manifest", "objects", "schema"}
        or value["schema"] != "mathhead.safe-cache-audited-fixture.v1"
        or value["claim"] != claim
        or type(value["manifest"]) is not str
        or type(value["objects"]) is not list
        or any(type(item) is not str for item in value["objects"])
        or raw
        != (
            json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n"
        ).encode("ascii")
    ):
        raise ValueError("portable audited fixture shape differs")
    manifest = base64.b64decode(value["manifest"], validate=True)
    objects = tuple(base64.b64decode(item, validate=True) for item in value["objects"])
    bundle = _bundle_from_replayed_bytes(manifest, objects)
    return AuditedCacheFixture(claim=claim, bundle=bundle)


__all__ = ["AuditedCacheFixture", "EXPECTED_LOOKUP_KEYS", "success_bundle"]
