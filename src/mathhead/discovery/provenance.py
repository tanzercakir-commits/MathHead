"""
mathhead.discovery.provenance — proof-artifact provenance & replay for the kernel (roadmap M4/M5).

Given a kernel proof TERM (kernel.py), this derives the honest provenance an auditor wants:

  * axioms_used(term) — the EXACT set of inference rules / primitive facts a theorem rests on (M5):
    every RESIDUE(m) leaf and each CRT composition. Nothing hidden — if a theorem leaned on the
    residue-exhaustion primitive at modulus 8, it says RESIDUE(m=8).
  * proof_hash(term)  — a deterministic content hash of the CANONICAL proof term plus the kernel
    version (M4): the same proof ⇒ the same hash across processes; a kernel-version bump changes it.
  * replay(term)      — re-run the kernel and confirm it mints the same theorem with the same hash
    (M4): deterministic proof replay, the reproducibility guarantee.

These are derived METADATA: they never mint a Theorem (only kernel.check does). They let a proof be
stored, shared, de-duplicated, and re-verified later — an audit trail, not part of the trusted core.
"""
from __future__ import annotations

import hashlib

from .kernel import CRT, Residue, SumInduction, Theorem, _norm, _norm_q, check

KERNEL_VERSION = "1.0"


def _canonical(term) -> tuple:
    """Order-independent canonical form of a proof term (CRT premises sorted) — the basis for hashing
    and de-duplication. RESIDUE and CRT canonical tuples start with distinct tags, so a mixed list is
    always safely comparable."""
    if isinstance(term, Residue):
        return ("RESIDUE", int(term.modulus), _norm(term.poly))
    if isinstance(term, CRT):
        return ("CRT", tuple(sorted(_canonical(p) for p in term.parts)))
    if isinstance(term, SumInduction):
        return ("SUM", _norm_q(term.f_poly), _norm_q(term.g_poly))
    raise TypeError(f"not a proof term: {type(term).__name__}")


def axioms_used(term) -> frozenset:
    """The set of rules / primitive facts the proof depends on — the full axiom list (M5)."""
    out: set = set()

    def walk(t) -> None:
        if isinstance(t, Residue):
            out.add(f"RESIDUE(m={int(t.modulus)})")
        elif isinstance(t, CRT):
            out.add("CRT")
            for p in t.parts:
                walk(p)
        elif isinstance(t, SumInduction):
            out.add("SUM_INDUCTION")
        else:
            raise TypeError(f"not a proof term: {type(t).__name__}")

    walk(term)
    return frozenset(out)


def proof_hash(term) -> str:
    """Deterministic 16-hex content hash of the canonical term + kernel version (M4). Same proof ⇒
    same hash, in any process; changing KERNEL_VERSION invalidates stored artifacts."""
    payload = f"{KERNEL_VERSION}|{_canonical(term)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def replay(term) -> Theorem:
    """Deterministic proof replay: re-run the kernel on the stored term and return the theorem it
    mints (M4). A caller confirms reproducibility by checking the theorem and `proof_hash` match."""
    return check(term)
