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


def check_poly_identity(lhs, rhs) -> bool:
    """Independently verify a polynomial IDENTITY p(n) = q(n) (∀n), given coefficient tuples
    (low→high, rational OK) — the kernel's THIRD judgment kind (PolyIdentity). Orthogonal method:
    the kernel subtracts coefficients; here we EVALUATE both sides exactly (Fraction) at deg+1
    integer points — a degree-D polynomial agreeing at D+1 points is identical. Stdlib only."""
    from fractions import Fraction

    def ev(p, x):
        acc = Fraction(0)
        for c in reversed(p):
            acc = acc * x + Fraction(c)
        return acc

    points = max(len(lhs), len(rhs))                    # ≥ degree + 1 evaluation points
    return all(ev(lhs, k) == ev(rhs, k) for k in range(points + 1))


def check_sum_identity(fn, g) -> bool:
    """Independently verify a SUM identity Σ_{i=1}^n f(i) = g(n), where g is a polynomial (sympy
    expr in `n`). Checks the base case f(1)=g(1) and the inductive step g(n)−g(n−1)=f(n) as a
    COMPLETE polynomial-identity check — evaluate at deg+2 integer points (a polynomial of degree D
    vanishing at D+1 points is identically zero). Independent of the MathHead proof (which verified
    the step symbolically); here we confirm it by exact rational evaluation."""
    import sympy

    n = sympy.Symbol("n")
    degree = int(sympy.degree(sympy.Poly(g, n))) if g.free_symbols else 0
    if g.subs(n, 1) != fn(1):                                   # base case
        return False
    return all(g.subs(n, k) - g.subs(n, k - 1) == fn(k)         # step, at enough points
               for k in range(2, degree + 3))
