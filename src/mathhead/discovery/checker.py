"""
mathhead.discovery.checker — a small INDEPENDENT proof checker (roadmap M1–M3 spirit).

Don't trust the prover — check the proof. The strategy layer (induction / CRT / residue) could have
a bug; this checker RE-VERIFIES a proof tree by an orthogonal, minimal, stdlib-only method and
rejects anything it cannot confirm.

For a modular-polynomial claim the check is COMPLETE: re-evaluate the polynomial at every residue
mod m (independent of HOW the proof was found — even an induction/Z3 proof is re-checked this way).
For a CRT node it also checks the REASONING: the prime-power moduli must be pairwise coprime and
multiply to the goal's modulus, and every lemma must itself check out.

This is the discovery engine's version of MathHead's independent certificate checker: the search
may be clever or buggy, but it cannot fool this.
"""
from __future__ import annotations

import math
import re
from functools import reduce


def _modulus_of(claim: str):
    m = re.search(r"%\s*(\d+)\s*==\s*0", claim)
    return int(m.group(1)) if m else None


def _residue_ok(fn, m) -> bool:
    """Complete stdlib check: fn(r) ≡ 0 (mod m) for every residue r ⇒ true for all integers n."""
    return m is not None and m > 0 and all(fn(r) % m == 0 for r in range(m))


def check_proof(node, fn):
    """Independently verify a ProofNode against fn. Returns (ok: bool, detail: dict)."""
    m = _modulus_of(node.claim)
    if node.method == "CRT":
        lemma_ms = [_modulus_of(c.claim) for c in node.children]
        if any(x is None for x in lemma_ms) or m is None:
            return False, {"reason": "unparsable modulus"}
        coprime = all(math.gcd(a, b) == 1
                      for i, a in enumerate(lemma_ms) for b in lemma_ms[i + 1:])
        product_ok = reduce(lambda x, y: x * y, lemma_ms, 1) == m
        kids_ok = all(check_proof(c, fn)[0] for c in node.children)
        return (coprime and product_ok and kids_ok,
                {"coprime": coprime, "product_ok": product_ok, "lemma_moduli": lemma_ms})
    return _residue_ok(fn, m), {"residues_checked": m}


def independently_verify(fn, m: int) -> bool:
    """Complete, independent check that fn(n) ≡ 0 (mod m) for all integers n (stdlib only)."""
    return _residue_ok(fn, m)
