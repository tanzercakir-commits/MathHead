"""
mathhead.discovery.congruence — DERIVE the residue principle from the factor theorem (roadmap M:
shrink the kernel's trusted base).

Every kernel ADR carries the same honest caveat: RESIDUE (exhaust residues 0..m−1 ⇒ m | p(n) ∀n) is
a TRUSTED PRIMITIVE, not derived from deeper axioms. This module removes that caveat for the modular
fragment by DERIVING RESIDUE, and it does so using the kernel's OWN `PolyIdentity` rule — no new
trusted machinery.

The derivation, for a claim `m | p(n) ∀n`:
  * For each residue r ∈ {0,…,m−1}, the FACTOR THEOREM gives p(x) − p(r) = (x − r)·q_r(x) with an
    integer quotient q_r — verified EXACTLY as a kernel PolyIdentity (this is the universal step; it
    holds for ALL x, so for all integers n).
  * For any integer n with n ≡ r (mod m): m | (n − r), hence m | (n − r)·q_r(n) = p(n) − p(r).
  * The residue check gives m | p(r). So m | (p(n) − p(r)) + p(r) = p(n).
Ranging r over all residues covers every integer n.

Trusted base after this: the factor theorem (checked via PolyIdentity — exact polynomial arithmetic)
and elementary integer divisibility (m | a ∧ m | b ⇒ m | a+b; m | a ⇒ m | a·k). Residue-exhaustion is
no longer a black box — it is a THEOREM about the factor theorem. An independent checker re-verifies
the whole derivation without the kernel.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .kernel import Identity, KernelError, _norm, check


def _eval(poly: tuple, x: int) -> int:
    v = 0
    for c in reversed(poly):
        v = v * x + c
    return v


def _sub_const(poly: tuple, c: int) -> tuple:
    p = list(poly)
    p[0] -= c
    return tuple(p)


def _mul_x_minus_r(q: tuple, r: int) -> tuple:
    """(x − r)·q(x) as an exact integer coefficient tuple."""
    xq = (0, *q)                                   # x·q
    n = max(len(xq), len(q))
    xq = xq + (0,) * (n - len(xq))
    rq = tuple(r * c for c in q) + (0,) * (n - len(q))
    return tuple(xq[i] - rq[i] for i in range(n))


def factor_quotient(poly: tuple, r: int) -> tuple:
    """Synthetic division: quotient q with p(x) − p(r) = (x − r)·q(x). (Remainder is p(r)−p(r)=0.)"""
    pr = _eval(poly, r)
    high = list(_sub_const(poly, pr))[::-1]        # p(x) − p(r), high→low; has a root at x=r
    q = [high[0]]
    for c in high[1:]:
        q.append(c + r * q[-1])
    q.pop()                                        # drop the (zero) remainder
    return tuple(q[::-1])


@dataclass
class FactorStep:
    r: int
    residue_value: int          # p(r) mod m (must be 0)
    quotient: tuple             # q_r with p(x)−p(r) = (x−r)q_r(x)
    kernel_verified: bool       # the PolyIdentity p(x)−p(r) = (x−r)q_r(x) was kernel-checked


@dataclass
class ResidueDerivation:
    poly: tuple
    m: int
    steps: list = field(default_factory=list)
    verified: bool = False
    trust_base: str = "factor theorem (PolyIdentity) + elementary integer divisibility"


def derive_residue(poly: tuple, m: int) -> ResidueDerivation:
    """Derive `m | p(n) ∀n` from the factor theorem. Each residue class contributes a kernel-checked
    factor identity plus a residue value; `verified` iff all residues vanish AND every factor identity
    checks."""
    poly = _norm(poly)
    if m < 1:
        return ResidueDerivation(poly, m, [], False)
    steps, all_zero = [], True
    for r in range(m):
        rv = _eval(poly, r) % m
        if rv != 0:
            all_zero = False
        q = factor_quotient(poly, r)
        lhs = _sub_const(poly, _eval(poly, r))     # p(x) − p(r)
        rhs = _mul_x_minus_r(q, r)                  # (x − r)·q_r(x)
        try:
            check(Identity(lhs, rhs))               # the universal step, via the kernel's own rule
            kv = True
        except KernelError:
            kv = False
        steps.append(FactorStep(r, rv, q, kv))
    verified = all_zero and all(s.kernel_verified for s in steps)
    return ResidueDerivation(poly, m, steps, verified)


def check_residue_derivation(d: ResidueDerivation) -> bool:
    """INDEPENDENT re-check (no kernel): recompute each quotient, re-verify the factor identity by
    exact polynomial reconstruction, and re-check every residue value. Returns True iff the derivation
    genuinely establishes `m | p(n) ∀n`."""
    if d.m < 1 or len(d.steps) != d.m:
        return False
    for r in range(d.m):
        if _eval(d.poly, r) % d.m != 0:            # residue must vanish
            return False
        q = factor_quotient(d.poly, r)
        # reconstruct (x − r)·q(x) + p(r) and require it equals p(x) exactly
        recon = _mul_x_minus_r(q, r)
        recon = list(recon) + [0] * (len(d.poly) - len(recon))
        recon[0] += _eval(d.poly, r)
        target = list(d.poly) + [0] * (len(recon) - len(d.poly))
        if [recon[i] if i < len(recon) else 0 for i in range(len(target))] != target:
            return False
    return True


def residue_is_derivable(poly: tuple, m: int) -> bool:
    """True iff `m | p(n) ∀n` is derivable from the factor theorem AND the independent checker agrees."""
    d = derive_residue(poly, m)
    return d.verified and check_residue_derivation(d)


# --- CRT derived from Bézout (m1|x ∧ m2|x ∧ gcd=1 ⇒ m1·m2|x) ----------------------------------

def _bezout(a: int, b: int) -> tuple:
    """Extended Euclid: (g, s, t) with s·a + t·b = g = gcd(a, b)."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


@dataclass
class CRTDerivation:
    m1: int
    m2: int
    s: int                      # Bézout coefficients with s·m1 + t·m2 = 1
    t: int
    verified: bool = False
    trust_base: str = "Bézout (extended Euclid) + elementary integer divisibility"


def derive_crt(m1: int, m2: int) -> CRTDerivation:
    """Derive `m1 | x ∧ m2 | x ⇒ m1·m2 | x` (for coprime m1, m2) from Bézout: with s·m1 + t·m2 = 1,
    x = x·(s·m1 + t·m2) = s·m1·x + t·m2·x, and each term is divisible by m1·m2 (using m2|x resp.
    m1|x), so m1·m2 | x."""
    g, s, t = _bezout(m1, m2)
    verified = (g == 1) and (s * m1 + t * m2 == 1)
    return CRTDerivation(m1, m2, s, t, verified)


def check_crt_derivation(d: CRTDerivation) -> bool:
    """INDEPENDENT re-check: the Bézout identity holds and the moduli are genuinely coprime."""
    from math import gcd
    return gcd(d.m1, d.m2) == 1 and (d.s * d.m1 + d.t * d.m2 == 1)


def crt_chain_is_derivable(moduli: list) -> bool:
    """True iff every pair of the (prime-power) moduli has a verified Bézout CRT derivation — so the
    whole composite modulus is CRT-derivable from Bézout."""
    ms = list(moduli)
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            d = derive_crt(ms[i], ms[j])
            if not (d.verified and check_crt_derivation(d)):
                return False
    return True
