"""
mathhead.discovery.serialize — object serialization + content-hash + reproducible ordering (N3).

A generic, deterministic serializer over the discovery object model. Because every object is a frozen
`MathObject` dataclass with tuple/frozenset fields, one canonicaliser handles all five domains
(Graph, Permutation, Partition, SetPartition, …): it sorts sets, recurses into tuples, and emits a
stable JSON structure. From that come a content HASH (dedup / storage keys) and a reproducible SORT
(so any collection of objects has a canonical, process-independent order).

Deterministic and stdlib-only.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import fields, is_dataclass


def _canon(v):
    """Canonicalise a field value: sets → sorted lists, tuples/lists → lists (recursively)."""
    if isinstance(v, (frozenset, set)):
        return sorted((_canon(x) for x in v), key=repr)
    if isinstance(v, (tuple, list)):
        return [_canon(x) for x in v]
    return v


def serialize(obj) -> dict:
    """A canonical, JSON-able dict for any discovery object: {kind, data}."""
    if not is_dataclass(obj):
        raise TypeError(f"not a dataclass object: {type(obj).__name__}")
    data = {f.name: _canon(getattr(obj, f.name)) for f in fields(obj)}
    return {"kind": type(obj).__name__, "data": data}


def content_hash(obj) -> str:
    """Deterministic 16-hex content hash — same object ⇒ same hash, in any process."""
    payload = json.dumps(serialize(obj), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def reproducible_sort(objs) -> list:
    """A canonical, process-independent ordering of any collection of objects (by content hash)."""
    return sorted(objs, key=content_hash)


def deduplicate(objs) -> list:
    """Drop content-duplicate objects, preserving first-seen order (deterministic)."""
    seen, out = set(), []
    for o in objs:
        h = content_hash(o)
        if h not in seen:
            seen.add(h)
            out.append(o)
    return out
