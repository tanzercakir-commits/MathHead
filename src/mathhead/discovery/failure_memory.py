"""
mathhead.discovery.failure_memory — negative knowledge: remember dead ends (roadmap Track Y).

A discovery engine that forgets its failures re-walks them. This records every closed branch — a
REFUTED conjecture, a solver TIMEOUT, a USELESS lemma, a dead-end transform (Y0) — under a canonical
FINGERPRINT (Y1) so the identical dead end is never re-attempted, and distills REUSABLE LESSONS from
the record (Y2): e.g. "these conjectures all died to the same minimal counterexample," which tells the
engine to test new look-alike conjectures against that witness FIRST.

Deterministic and pure: fingerprints are content hashes, the store is an ordinary dict. Nothing here
proves anything — it is an efficiency-and-memory layer beside the judge, not part of the trust base.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

KINDS = ("refuted_conjecture", "timeout", "useless_lemma", "dead_end")


def _canonical_statement(statement: str) -> str:
    """Whitespace-normalize a statement so trivially-different spellings share a fingerprint."""
    return " ".join(str(statement).split())


def fingerprint(kind: str, statement: str) -> str:
    """Canonical content fingerprint of an attempt (Y1) — identical dead ends collide by design."""
    if kind not in KINDS:
        raise ValueError(f"unknown failure kind {kind!r}; known: {KINDS}")
    payload = f"{kind}|{_canonical_statement(statement)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _signature(detail: dict) -> str:
    """A stable string for a counterexample / cause — the basis for clustering lessons (Y2)."""
    ce = (detail or {}).get("counterexample", detail or {})
    return json.dumps(ce, sort_keys=True, default=str)


@dataclass
class AttemptRecord:
    fingerprint: str
    kind: str
    statement: str
    detail: dict = field(default_factory=dict)


class FailureMemory:
    """A canonicalized store of closed branches. `record` is idempotent per fingerprint; `seen` lets
    the loop skip a dead end it has already walked."""

    def __init__(self) -> None:
        self._by_fp: dict = {}

    def record(self, kind: str, statement: str, detail: dict | None = None) -> str:
        fp = fingerprint(kind, statement)
        if fp not in self._by_fp:            # idempotent — first write wins, deterministic
            self._by_fp[fp] = AttemptRecord(fp, kind, statement, dict(detail or {}))
        return fp

    def seen(self, kind: str, statement: str) -> bool:
        return fingerprint(kind, statement) in self._by_fp

    def records(self, kind: str | None = None) -> list:
        rs = list(self._by_fp.values())
        return [r for r in rs if r.kind == kind] if kind else rs

    def summary(self) -> dict:
        out: dict = {}
        for r in self._by_fp.values():
            out[r.kind] = out.get(r.kind, 0) + 1
        return out

    def lessons(self) -> list:
        """Y2 — reusable lessons: cluster refuted conjectures by the WITNESS that killed them. A
        witness that refutes many conjectures is a high-value probe to try first on new ones."""
        clusters: dict = {}
        for r in self._by_fp.values():
            if r.kind != "refuted_conjecture":
                continue
            clusters.setdefault(_signature(r.detail), []).append(r.statement)
        lessons = [
            {"witness": sig, "refutes": len(stmts), "statements": sorted(stmts)}
            for sig, stmts in clusters.items()
        ]
        # most broadly-applicable lesson first (then by witness for determinism)
        return sorted(lessons, key=lambda le: (-le["refutes"], le["witness"]))


def populate_from_refutations(memory: FailureMemory, results) -> int:
    """Record the refuted items from an iterable of (statement, RefutationResult|dict). Returns how
    many NEW dead ends were learned (already-seen ones are skipped — the whole point)."""
    learned = 0
    for statement, res in results:
        status = getattr(res, "status", None) or (res or {}).get("status")
        if status != "refuted":
            continue
        detail = getattr(res, "detail", None)
        if detail is None:
            detail = (res or {}).get("counterexample", res if isinstance(res, dict) else {})
        if not memory.seen("refuted_conjecture", statement):
            memory.record("refuted_conjecture", statement, {"counterexample": detail})
            learned += 1
    return learned
